"""Check an expression matrix and a signature before any R code runs.

Problems are reported, never fixed. The reading rules here mirror the R readers in
r/preamble.R, so R and Python see the same table; the server checks this after R runs.

Matrix file: .csv (comma) or .tsv/.txt (tab). The first row holds sample names; its first
cell labels the gene-ID column and may be empty. The first column holds gene IDs. Every row
has the same number of fields. Cells are numbers; "NA" or an empty cell means missing.

Signature file: one gene per line. An optional second field (tab or comma) is a weight. Blank
lines and lines starting with "#" are ignored. A first line whose first field is "gene" is a header.
"""

from __future__ import annotations

import csv
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

NUMBER = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")
NON_FINITE = {"inf", "+inf", "-inf", "infinity", "-infinity", "nan"}
MISSING = {"NA", ""}


@dataclass
class Problem:
    level: str  # "error" blocks the analysis; "warning" is reported and the analysis may go on
    code: str
    message: str


@dataclass
class Matrix:
    path: Path
    genes: list[str]
    samples: list[str]
    values: list[list[float | None]]  # rows are genes; None is missing


@dataclass
class Signature:
    path: Path
    genes: list[str]
    weights: list[float] | None


@dataclass
class Report:
    matrix: Matrix | None = None
    signature: Signature | None = None
    problems: list[Problem] = field(default_factory=list)
    found: list[str] = field(default_factory=list)  # signature genes present in the matrix, in signature order
    missing: list[str] = field(default_factory=list)
    constant_genes: list[str] = field(default_factory=list)
    genes_with_na: list[str] = field(default_factory=list)

    def add(self, level: str, code: str, message: str) -> None:
        self.problems.append(Problem(level, code, message))

    @property
    def errors(self) -> list[Problem]:
        return [p for p in self.problems if p.level == "error"]

    @property
    def warnings(self) -> list[Problem]:
        return [p for p in self.problems if p.level == "warning"]

    def has(self, code: str) -> bool:
        return any(p.code == code for p in self.problems)


def _delimiter(path: Path) -> str:
    return "," if path.suffix.lower() == ".csv" else "\t"


def _examples(items: list[str], n: int = 5) -> str:
    shown = ", ".join(items[:n])
    return shown + (f" and {len(items) - n} more" if len(items) > n else "")


def read_matrix(path: Path, report: Report) -> Matrix | None:
    if not path.exists():
        report.add("error", "matrix_not_found", f"The matrix file {path} does not exist.")
        return None
    if path.suffix.lower() not in (".csv", ".tsv", ".txt"):
        report.add("error", "matrix_format", f"{path.name}: use a .csv (comma-separated) or .tsv/.txt (tab-separated) file.")
        return None
    try:
        with path.open(newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.reader(fh, delimiter=_delimiter(path), quotechar='"'))
    except UnicodeDecodeError:
        report.add("error", "matrix_encoding", f"{path.name} is not a UTF-8 text file. Save it as CSV or tab-separated text.")
        return None
    rows = [r for r in rows if any(cell.strip() for cell in r)]
    if len(rows) < 2:
        report.add("error", "matrix_empty", f"{path.name} needs a header row of sample names and at least one gene row.")
        return None
    header, body = rows[0], rows[1:]
    width = len(header)
    if width < 2:
        other = "comma" if _delimiter(path) == "\t" else "tab"
        report.add("error", "matrix_columns", f"{path.name} has only one column. If it is {other}-separated, rename it to .{'csv' if other == 'comma' else 'tsv'}.")
        return None
    bad_width = [i + 2 for i, r in enumerate(body) if len(r) != width]
    if bad_width:
        report.add(
            "error", "matrix_ragged",
            f"Rows must all have {width} fields like the header. Lines with a different count: {_examples([str(i) for i in bad_width])}. "
            "If the header has no label for the gene-ID column, add one (it can be empty, e.g. a leading separator).",
        )
        return None
    samples = [h.strip() for h in header[1:]]
    genes = [r[0].strip() for r in body]
    values: list[list[float | None]] = []
    non_numeric: list[str] = []
    non_finite: list[str] = []
    for gi, r in enumerate(body):
        row: list[float | None] = []
        for sj, cell in enumerate(r[1:]):
            c = cell.strip()
            if c in MISSING:
                row.append(None)
            elif NUMBER.match(c):
                value = float(c)
                if math.isfinite(value):
                    row.append(value)
                else:
                    non_finite.append(f"{genes[gi]}/{samples[sj]}={c}")
                    row.append(None)
            elif c.lower() in NON_FINITE:
                non_finite.append(f"{genes[gi]}/{samples[sj]}={c}")
                row.append(None)
            else:
                non_numeric.append(f"{genes[gi]}/{samples[sj]}={c!r}")
                row.append(None)
        values.append(row)
    if non_numeric:
        decimal_comma = any(re.match(r"^'?[+-]?\d+,\d+'?$", x.split("=", 1)[1]) for x in non_numeric)
        hint = " The values look like decimal commas; save the file with decimal points." if decimal_comma else ""
        report.add("error", "non_numeric", f"{len(non_numeric)} cells are not numbers (gene/sample=value): {_examples(non_numeric)}.{hint}")
    if non_finite:
        report.add("error", "non_finite", f"{len(non_finite)} cells are infinite or NaN: {_examples(non_finite)}. Replace them with NA or real values.")
    empty_ids = [str(i + 2) for i, g in enumerate(genes) if not g]
    if empty_ids:
        report.add("error", "empty_gene_id", f"Rows without a gene ID on lines {_examples(empty_ids)}.")
    dup_genes = [g for g, n in Counter(genes).items() if n > 1 and g]
    if dup_genes:
        report.add(
            "error", "duplicate_genes",
            f"{len(dup_genes)} gene IDs appear more than once in the matrix: {_examples(dup_genes)}. "
            "sigscores would silently use only the first row of each (finding dup-matrix-gene). Collapse or rename them first.",
        )
    dup_samples = [s for s, n in Counter(samples).items() if n > 1]
    if dup_samples:
        report.add("error", "duplicate_samples", f"Sample names appear more than once: {_examples(dup_samples)}. sigscores stops on these (finding dup-samples).")
    empty_samples = [str(j + 2) for j, s in enumerate(samples) if not s]
    if empty_samples:
        report.add("error", "empty_sample_name", f"Columns without a sample name: {_examples(empty_samples)}.")
    folded = Counter(g.casefold() for g in set(genes) if g)
    collisions = sorted(g for g in set(genes) if g and folded[g.casefold()] > 1)
    if collisions:
        report.add("warning", "case_collision_matrix", f"Gene IDs that differ only in letter case: {_examples(collisions)}. Check they really are different genes.")
    return Matrix(path, genes, samples, values)


def read_signature(path: Path, report: Report) -> Signature | None:
    if not path.exists():
        report.add("error", "signature_not_found", f"The signature file {path} does not exist.")
        return None
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except UnicodeDecodeError:
        report.add("error", "signature_encoding", f"{path.name} is not a UTF-8 text file.")
        return None
    lines = [ln.strip() for ln in lines]
    lines = [ln for ln in lines if ln and not ln.startswith("#")]
    parts = [[p.strip() for p in re.split(r"[\t,]", ln)] for ln in lines]
    if parts and parts[0][0].lower() == "gene":
        parts = parts[1:]
    if not parts:
        report.add("error", "signature_empty", f"{path.name} contains no genes.")
        return None
    genes = [p[0] for p in parts]
    weights = None
    extra = [str(i + 1) for i, p in enumerate(parts) if len(p) > 2]
    if extra:
        report.add("error", "signature_columns", f"Signature lines may have only a gene ID and optional weight. Extra columns on entries {_examples(extra)}.")
    if all(len(p) >= 2 and p[1] != "" for p in parts):
        bad = [f"{p[0]}={p[1]!r}" for p in parts if not NUMBER.match(p[1]) or not math.isfinite(float(p[1]))]
        if bad:
            report.add("error", "bad_weights", f"Weights must be numbers: {_examples(bad)}.")
        else:
            weights = [float(p[1]) for p in parts]
    elif any(len(p) >= 2 and p[1] != "" for p in parts):
        report.add("error", "partial_weights", "Some signature lines have a weight and others don't. Give every gene a weight, or none.")
    dups = [g for g, n in Counter(genes).items() if n > 1]
    if dups:
        report.add(
            "error", "duplicate_signature_genes",
            f"Genes listed more than once in the signature: {_examples(dups)}. "
            "sigscores would count each copy separately, changing the score (finding dup-signature-gene). Remove the extra copies.",
        )
    return Signature(path, genes, weights)


def _constant_and_na(m: Matrix) -> tuple[list[str], list[str]]:
    constant, with_na = [], []
    for g, row in zip(m.genes, m.values):
        if any(v is None for v in row):
            with_na.append(g)
        elif len(set(row)) == 1:
            constant.append(g)
    return constant, with_na


def check(matrix_path: str | Path, signature_path: str | Path | None = None) -> Report:
    report = Report()
    m = read_matrix(Path(matrix_path).expanduser(), report)
    report.matrix = m
    if m is not None:
        report.constant_genes, report.genes_with_na = _constant_and_na(m)
        if report.genes_with_na:
            n_na = sum(v is None for row in m.values for v in row)
            report.add(
                "warning", "missing_values",
                f"{n_na} missing values in {len(report.genes_with_na)} genes ({_examples(report.genes_with_na)}). "
                "Most scores skip them (na.rm = TRUE); the four GSVA-based scores are refused until those genes are removed (finding gsva-na-row).",
            )
        if report.constant_genes:
            report.add(
                "warning", "constant_genes",
                f"{len(report.constant_genes)} genes have the same value in every sample ({_examples(report.constant_genes)}). "
                "The four GSVA-based scores are refused until these are removed (finding gsva-constant-gene).",
            )
        if len(m.samples) < 2:
            report.add("warning", "single_sample", "Only one sample: the GSVA-based scores are always NA with one sample (finding one-sample).")
    if signature_path is None:
        return report
    s = read_signature(Path(signature_path).expanduser(), report)
    report.signature = s
    if m is None or s is None:
        return report
    gene_set, sample_set = set(m.genes), set(m.samples)
    report.found = [g for g in s.genes if g in gene_set]
    report.missing = [g for g in s.genes if g not in gene_set]
    in_columns = [g for g in s.genes if g in sample_set]
    if not report.found and in_columns:
        report.add(
            "error", "transposed",
            f"The signature genes appear as column names ({_examples(in_columns)}), not as row names. "
            "The matrix looks transposed: sigscores needs genes in rows and samples in columns.",
        )
        return report
    if len(in_columns) > len(report.found):
        report.add("warning", "maybe_transposed", f"More signature genes match column names ({len(in_columns)}) than row names ({len(report.found)}). Check the matrix orientation.")
    if report.missing:
        by_fold = {}
        for g in m.genes:
            by_fold.setdefault(g.casefold(), []).append(g)
        case_hits = [f"{g} (matrix has {'/'.join(by_fold[g.casefold()])})" for g in report.missing if g.casefold() in by_fold]
        if case_hits:
            report.add(
                "error", "case_mismatch",
                f"Signature genes that match matrix genes only when ignoring letter case: {_examples(case_hits)}. "
                "Gene symbols are case-sensitive (TP53 is human, Tp53 is mouse); fix the signature file.",
            )
        plain = [g for g in report.missing if g.casefold() not in by_fold]
        if plain:
            report.add(
                "error", "missing_genes",
                f"{len(plain)} of {len(s.genes)} signature genes are not in the matrix: {_examples(plain)}. "
                "sigscores would score the rest without saying so (finding unknown-gene) and would draw random sets of the full size "
                "(finding rndsig-size). Correct the signature, or rerun with drop_missing_genes=true to score only the genes found.",
            )
    if not report.found:
        report.add("error", "no_genes_found", "None of the signature genes are in the matrix.")
    return report


def summary(report: Report) -> str:
    """Plain-language summary of a report, for the biologist and for Claude."""
    out: list[str] = []
    m, s = report.matrix, report.signature
    if m is not None:
        n_missing = sum(v is None for row in m.values for v in row)
        out.append(f"Matrix {m.path.name}: {len(m.genes)} genes (rows) x {len(m.samples)} samples (columns); {n_missing} missing values.")
    if s is not None:
        w = "with weights" if s.weights else "without weights"
        out.append(f"Signature {s.path.name}: {len(s.genes)} genes {w}; {len(report.found)} found in the matrix, {len(report.missing)} not found.")
    if report.errors:
        out.append("\nProblems that must be fixed first:")
        out += [f"- [{p.code}] {p.message}" for p in report.errors]
    if report.warnings:
        out.append("\nWarnings:")
        out += [f"- [{p.code}] {p.message}" for p in report.warnings]
    if not report.problems:
        out.append("\nNo problems found.")
    return "\n".join(out)
