"""Write a set of broken input files and record what Sigshell does with each one.

Every case starts from the same small, made-up matrix (8 genes x 4 samples, log-scale values) and
a 3-gene hypoxia-style signature, with one problem added. For each case the script runs the same
checks the tools run before any R code: validate.check (the check_inputs tool), then the guards of
compute_scores. No R is needed. Output: examples/malformed-inputs/<case>/ and its README.md table.

Usage, from the repository root:  uv run python examples/malformed_inputs.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("SIGSHELL_HOME", tempfile.mkdtemp())  # keep the server's session folder out of ~/Sigshell

from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402

from sigshell import methods, server, validate  # noqa: E402

OUT = Path(__file__).parent / "malformed-inputs"
GENES = ["TP53", "MYC", "VEGFA", "CA9", "LDHA", "GAPDH", "ACTB", "PGK1"]
VALUES = [
    [6.12, 5.87, 6.40, 6.03], [8.41, 7.95, 8.88, 8.10], [5.31, 7.62, 4.98, 7.15], [2.05, 6.44, 1.87, 5.92],
    [9.10, 10.35, 8.97, 10.02], [11.80, 11.62, 11.95, 11.71], [12.33, 12.41, 12.18, 12.27], [7.02, 8.86, 6.91, 8.53],
]
SIG = ["VEGFA", "CA9", "LDHA"]


def matrix(genes=GENES, values=VALUES, samples=("S1", "S2", "S3", "S4"), sep=",", dec="."):
    head = sep.join(["gene", *samples])
    rows = [sep.join([g, *(str(v).replace(".", dec) for v in row)]) for g, row in zip(genes, values)]
    return "\n".join([head, *rows]) + "\n"


def replace(genes=None, values=None, **kw):
    g, v = list(GENES), [list(r) for r in VALUES]
    for k, name in (genes or {}).items():
        g[k] = name
    for (i, j), x in (values or {}).items():
        v[i][j] = x
    return matrix(g, v, **kw)


# (folder, problem as a biologist would meet it, matrix file name, matrix text, signature text, related findings)
CASES = [
    ("01-clean", "Nothing wrong (control)", "matrix.csv", matrix(), "\n".join(SIG) + "\n", []),
    ("02-missing-gene", "A signature gene is not in the matrix", "matrix.csv", matrix(), "VEGFA\nCA9\nLDHA\nBNIP3\n",
     ["unknown-gene", "rndsig-size"]),
    ("03-mouse-capitalisation", "Human signature on mouse-style gene names (Vegfa, Ca9, Ldha)", "matrix.csv",
     replace(genes={2: "Vegfa", 3: "Ca9", 4: "Ldha"}), "\n".join(SIG) + "\n", ["unknown-gene"]),
    ("04-signature-gene-twice", "A gene pasted twice into the signature", "matrix.csv", matrix(), "VEGFA\nCA9\nLDHA\nCA9\n",
     ["dup-signature-gene"]),
    ("05-two-probes-one-gene", "Two matrix rows with the same gene name (two probes)", "matrix.csv",
     replace(genes={7: "VEGFA"}), "\n".join(SIG) + "\n", ["dup-matrix-gene"]),
    ("06-decimal-comma", "Decimal commas from a spreadsheet set to Italian (5,31)", "matrix.tsv",
     matrix(sep="\t", dec=","), "\n".join(SIG) + "\n", []),
    ("07-transposed", "Samples in rows and genes in columns", "matrix.csv",
     "sample," + ",".join(GENES) + "\n" + "\n".join(f"S{j + 1}," + ",".join(str(VALUES[i][j]) for i in range(8)) for j in range(4)) + "\n",
     "\n".join(SIG) + "\n", []),
    ("08-hexadecimal-cell", "A cell that reads 0x1A", "matrix.csv", replace(values={(0, 1): "0x1A"}), "\n".join(SIG) + "\n", []),
    ("09-overflow", "A value too large for a double (1e309)", "matrix.csv", replace(values={(1, 2): "1e309"}),
     "\n".join(SIG) + "\n", []),
    ("10-all-zero-gene", "A gene with 0 in every sample", "matrix.csv", replace(values={(1, j): 0 for j in range(4)}),
     "\n".join(SIG) + "\n", ["gsva-constant-gene"]),
    ("11-missing-value", "An empty cell in one gene", "matrix.csv", replace(values={(0, 2): "NA"}), "\n".join(SIG) + "\n",
     ["gsva-na-row", "quantile-na-rows"]),
    ("12-duplicate-sample", "Two samples with the same name", "matrix.csv", matrix(samples=("S1", "S2", "S2", "S4")),
     "\n".join(SIG) + "\n", ["dup-samples"]),
    ("13-one-sample", "Only one sample", "matrix.csv", matrix(values=[[r[0]] for r in VALUES], samples=("S1",)),
     "\n".join(SIG) + "\n", ["one-sample"]),
    ("14-some-weights", "Weights given for some signature genes only", "matrix.csv", matrix(), "VEGFA\t2\nCA9\nLDHA\t1\n", []),
    ("15-extra-column", "Signature copied with a description column", "matrix.csv", matrix(),
     "VEGFA\t1\tvascular growth factor\nCA9\t1\tcarbonic anhydrase\nLDHA\t1\tlactate dehydrogenase\n", []),
    ("16-ragged-row", "A row with one value too few", "matrix.csv",
     matrix().replace("TP53,6.12,5.87,6.4,6.03", "TP53,6.12,5.87,6.4"), "\n".join(SIG) + "\n", []),
]


def outcome(mfile: Path, sfile: Path) -> tuple[validate.Report, str]:
    """What compute_scores would do: refuse everything, refuse some scores or a transform, or run."""
    try:
        report = server._validated(str(mfile), str(sfile), drop_missing_genes=False)
    except ToolError:
        return validate.check(mfile, sfile), "Nothing runs until the input is fixed"
    refused = []
    for scores, transform, label in ((sorted(methods.GSVA_SCORES), "none", "the 4 GSVA-based scores"),
                                     (["mean"], "quantile", "quantile normalisation")):
        try:
            server._guards(report, scores, transform, {})
        except ToolError:
            refused.append(label)
    return report, ("Runs, but refuses " + " and ".join(refused)) if refused else "Runs"


def main() -> None:
    rows = []
    for folder, problem, mname, mtext, stext, findings in CASES:
        d = OUT / folder
        d.mkdir(parents=True, exist_ok=True)
        (d / mname).write_text(mtext, encoding="utf-8")
        (d / "signature.txt").write_text(stext, encoding="utf-8")
        report, what = outcome(d / mname, d / "signature.txt")
        codes = [f"`{p.code}`" for p in report.errors] + [f"`{p.code}` (warning)" for p in report.warnings]
        first = (report.errors or report.warnings)
        message = first[0].message.replace("|", "\\|") if first else ""
        links = ", ".join(f"[{f}](../../findings/FINDINGS.md#{f})" for f in findings) or "–"
        rows.append(f"| [{folder}]({folder}/) | {problem} | {', '.join(codes) or 'none'} | {what} | {links} | {message} |")
    blocked = sum("Nothing runs" in r for r in rows)
    partial = sum("refuses" in r for r in rows)
    text = "\n".join([
        "# Malformed inputs",
        "",
        "Sixteen small input sets, each with one problem a biologist meets in real files, and what Sigshell does with it.",
        "The matrix is made up (8 genes x 4 samples on a log scale) and the signature is VEGFA, CA9 and LDHA.",
        "Written by `examples/malformed_inputs.py`, which runs the same checks as the `check_inputs` tool and",
        "the guards of `compute_scores` (`src/sigshell/server.py`). None of this needs R: the checks run before any R code.",
        "",
        f"Of the 15 broken cases, {blocked} stop before R runs and {partial} run with some methods refused.",
        "The findings column links to the confirmed behaviour of sigscores that the check exists for.",
        "",
        "| Case | Problem | Reported as | What compute_scores does | Related findings | First message |",
        "|---|---|---|---|---|---|",
        *rows,
        "",
    ])
    (OUT / "README.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
