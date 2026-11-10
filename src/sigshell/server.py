"""The Sigshell MCP server: tools a biologist needs, each running sigscores in a fresh R process."""

from __future__ import annotations

import functools
import json
import time
from pathlib import Path
from typing import Annotated, Any, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import CallToolResult, ImageContent, TextContent
from pydantic import Field

from . import config, methods, rbridge, validate
from .rbridge import RCode, r_literal
from .session import Result, Session

INSTRUCTIONS = """\
Sigshell runs the sigscores R package (Barberis & Buffa 2026) for biologists who don't program.

How to work:
1. Find the user's files with find_data_files, then always run check_inputs on the matrix and signature before any analysis. Explain every problem it reports in plain language; never work around one silently.
2. Use list_methods to explain scores, transformations and null models. Prefer asking the user which scores they want over computing everything.
3. compute_scores gives one value per sample and score; test_significance compares each value with random gene sets; plot_scores and plot_null_distribution draw figures.
4. Every number you report must come from a Sigshell tool result. Never estimate, round differently or invent values.
5. When you report results, quote the provenance line the tool returns, and mention any caveat the tool reports.
6. get_r_script gives the plain R script that reproduces the session without AI.
"""

server = MCPServer(
    name="sigshell",
    title="Sigshell",
    description="Gene signature scores with the sigscores R package, for biologists.",
    instructions=INSTRUCTIONS,
    version="0.1.0",
)
session = Session()

Path_ = Annotated[str, Field(description="Path to the file. A bare file name is looked up in the Sigshell data folder (~/Sigshell/data).")]


# ---------------------------------------------------------------- helpers

def _resolve(p: str) -> Path:
    path = Path(p).expanduser()
    if not path.is_absolute():
        candidate = config.DATA_DIR / path
        path = candidate if candidate.exists() or not path.exists() else path.resolve()
    return path


def logged(fn):
    """Record every call in the session's calls.jsonl, with its outcome."""

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        started = time.time()
        try:
            result = await fn(*args, **kwargs)
        except ToolError as exc:
            session.log(fn.__name__, kwargs, started, "refused", str(exc))
            raise
        except rbridge.RError as exc:
            session.log(fn.__name__, kwargs, started, "r_error", str(exc))
            raise ToolError(f"R stopped with an error:\n{exc}") from exc
        except Exception as exc:
            session.log(fn.__name__, kwargs, started, "error", repr(exc))
            raise
        step = (result.meta or {}).get("step") if isinstance(result, CallToolResult) else None
        session.log(fn.__name__, kwargs, started, "ok", step=step)
        return result

    return wrapper


def _as_list(v: Any) -> list[Any]:
    """jsonlite writes length-1 vectors as scalars; turn them back into lists."""
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _columns(df: dict[str, Any]) -> dict[str, list[Any]]:
    return {k: _as_list(v) for k, v in df.items()}


def _fmt(v: Any) -> str:
    if v is None:
        return "NA"
    if isinstance(v, float):
        return f"{v:.6g}"
    return str(v)


def _table(columns: list[str], rows: list[list[Any]], max_rows: int = 40) -> str:
    out = ["| " + " | ".join(columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    out += ["| " + " | ".join(_fmt(v) for v in r) + " |" for r in rows[:max_rows]]
    if len(rows) > max_rows:
        out.append(f"\n({len(rows) - max_rows} more rows in the CSV file.)")
    return "\n".join(out)


def _result(text: str, structured: dict[str, Any], step: str | None = None, images: list[Path] | None = None) -> CallToolResult:
    content: list[Any] = [TextContent(type="text", text=text)]
    for img in images or []:
        import base64

        content.append(ImageContent(type="image", data=base64.b64encode(img.read_bytes()).decode(), mime_type="image/png"))
    return CallToolResult(content=content, structured_content=structured, meta={"step": step} if step else None)


async def _provenance() -> rbridge.Installation:
    try:
        return await rbridge.installation()
    except rbridge.RError as exc:
        raise ToolError(f"Sigshell can't run sigscores yet: {exc}") from exc


def _validated(matrix_file: str, signature_file: str, drop_missing_genes: bool) -> validate.Report:
    report = validate.check(_resolve(matrix_file), _resolve(signature_file))
    blocking = [p for p in report.errors if not (p.code == "missing_genes" and drop_missing_genes and report.found)]
    if blocking:
        raise ToolError("The inputs have problems that must be fixed first. Nothing was computed.\n\n" + validate.summary(report))
    return report


def _check_scores(scores: list[str], inst: rbridge.Installation) -> None:
    known = inst.ids("scores")
    if not scores:
        raise ToolError(f"Choose at least one score. list_methods describes the {len(known)} that sigscores offers.")
    unknown = [s for s in scores if s not in known]
    if unknown:
        raise ToolError(f"Unknown score ids: {', '.join(unknown)}. sigscores knows: {', '.join(known)}. (sigscores itself would drop unknown ids silently; finding typo-score.)")
    if len(set(scores)) != len(scores):
        raise ToolError("Each score can be requested once.")


def _guards(report: validate.Report, scores: list[str], transform: str, options: dict[str, Any]) -> None:
    gsva = [s for s in scores if s in methods.GSVA_SCORES]
    if gsva and (report.constant_genes or report.genes_with_na):
        what = []
        if report.constant_genes:
            what.append(f"{len(report.constant_genes)} genes with the same value in every sample (finding gsva-constant-gene)")
        if report.genes_with_na:
            what.append(f"{len(report.genes_with_na)} genes with missing values (finding gsva-na-row)")
        raise ToolError(
            f"The GSVA-based scores ({', '.join(gsva)}) are refused for this matrix: it has " + " and ".join(what) + ". "
            "In that case sigscores scores the wrong genes without any warning. Run prepare_matrix to write a copy without those genes, "
            "then use that file. The other scores are unaffected."
        )
    if gsva and report.matrix and len(report.matrix.samples) < 2:
        raise ToolError("The GSVA-based scores need at least two samples; with one, sigscores returns NA (finding one-sample).")
    if transform == "quantile" and report.genes_with_na:
        raise ToolError(
            "Quantile normalisation is refused for this matrix because some genes have missing values: sigscores then drops those rows "
            "but keeps the original row numbers, so the wrong genes are scored (finding quantile-na-rows). Run prepare_matrix first."
        )
    if transform == "z" and (options.get("by", "rows") != "rows" or options.get("robust", False)):
        raise ToolError("Only z-standardisation by rows with robust=false is offered: by='cols' and robust=true give wrong values in sigscores (findings z-cols, z-robust).")


TRANSFORM_OPTIONS = {
    "stepFunction": {"method": str, "by": str, "thr": float, "y": list},
    "quantile": {"ties_method": str},
    "z": {"by": str, "robust": bool},
}


def _transform_args(transform: str, options: dict[str, Any]) -> dict[str, Any]:
    if transform == "none":
        if options:
            raise ToolError("transform_options only apply when a transform is chosen.")
        return {}
    allowed = TRANSFORM_OPTIONS[transform]
    bad = [k for k in options if k not in allowed]
    if bad:
        raise ToolError(f"Unknown options for {transform}: {', '.join(bad)}. Allowed: {', '.join(allowed) or 'none'}.")
    out: dict[str, Any] = {}
    for k, v in options.items():
        out["ties.method" if k == "ties_method" else k] = v
    return out


def _r_inputs(step: str, matrix_rel: str, signature_rel: str, drop_missing: bool, scores: list[str], transform: str,
              targs: dict[str, Any], trim: float, weights: bool) -> str:
    lines = [
        f'SIGSHELL_STEP <- "{step}"',
        f"x <- sigshell_read_matrix({r_literal(matrix_rel)})",
        f"sig <- sigshell_read_signature({r_literal(signature_rel)})",
    ]
    if drop_missing:
        lines += ["keep <- sig$genes %in% rownames(x)  # drop_missing_genes = TRUE: score only the genes found in the matrix", "i <- sig$genes[keep]"]
    else:
        lines += ["keep <- rep(TRUE, length(sig$genes))", "i <- sig$genes"]
    per_score: dict[str, dict[str, Any]] = {s: {} for s in scores}
    if transform != "none":
        for s in scores:
            per_score[s]["transform.fun"] = RCode(f"getDataTransformer({r_literal(transform)})")
            if targs:
                per_score[s]["transform.args"] = targs
    if weights and any(s in methods.WEIGHTED for s in scores):
        lines += [
            "w <- setNames(rep(0, nrow(x)), rownames(x))  # one weight per matrix row; only signature rows are used",
            "w[i] <- sig$weights[keep]",
        ]
        for s in scores:
            if s in methods.WEIGHTED:
                per_score[s]["w"] = RCode("unname(w)")
    if "trimmedMean" in scores and trim:
        per_score["trimmedMean"]["trim"] = trim
    per_score = {k: v for k, v in per_score.items() if v}
    lines.append(f"args <- {r_literal(per_score) if per_score else 'NULL'}")
    return "\n".join(lines)


def _caveats(report: validate.Report, scores: list[str], transform: str, drop_missing: bool, weights: bool) -> list[str]:
    notes = []
    if drop_missing and report.missing:
        notes.append(f"{len(report.missing)} signature genes were not in the matrix and were left out at your request: {', '.join(report.missing[:10])}.")
    if transform != "none" and any(s in methods.TRANSFORM_AFTER_SUBSET for s in scores):
        notes.append("trimmedMean and aad apply the transformation after selecting the signature genes; the other scores transform the whole matrix first (finding transform-order).")
    if any(s in methods.WEIGHTED for s in scores) and not weights:
        notes.append("The signature file has no weights, so weightedSum equals sum and weightedMean equals mean.")
    if weights and not any(s in methods.WEIGHTED for s in scores):
        notes.append("The signature file has weights, but only weightedSum and weightedMean use them.")
    if "mode" in scores:
        notes.append("mode returns the smallest value when no value repeats, which is typical for continuous data (findings modal-tie, mode-is-min).")
    if "iqm" in scores and len(report.found) < 4:
        notes.append("iqm needs at least 4 genes and is NA otherwise (finding iqm-small).")
    return notes


def _check_same_table(report: validate.Report, res: dict[str, Any]) -> None:
    m = report.matrix
    assert m is not None
    if _as_list(res.get("genes")) != m.genes or _as_list(res.get("samples")) != m.samples:
        raise ToolError("R and Sigshell's validator read the matrix file differently (gene or sample names differ). Nothing is reported; please share the file with the Sigshell maintainers.")


def _r_failures(res: dict[str, Any]) -> list[str]:
    notes = []
    for s, why in (res.get("all_na") or {}).items():
        notes.append(f"{s} is NA for every sample. sigscores hides scorer errors (finding silent-na); calling the scorer directly gives: {why}")
    if res.get("sink_left_open"):
        notes.append("GSVA failed inside sigscores and left R's output switched off (finding gsva-sink); Sigshell switched it back on.")
    for w in _as_list(res.get("warnings")):
        notes.append(f"R warning: {w}")
    for m in _as_list(res.get("messages")):
        notes.append(f"R message: {m}")
    return notes


async def _run(step: str, tool: str, arguments: dict[str, Any], body: str) -> dict[str, Any]:
    script = session.write_step(step, tool, arguments, body)
    try:
        await rbridge.run_script(script, session.dir)
    finally:
        session.refresh_script()
    out = session.dir / "outputs" / f"{step}-result.json"
    return json.loads(out.read_text(encoding="utf-8"))


def _provenance_line(inst: rbridge.Installation, step: str) -> str:
    return f"Provenance: {inst.line}. Session {session.dir}; step script steps/{step}-*.R; replay with `Rscript session.R` in that folder."


# ---------------------------------------------------------------- tools

def data_files(base: Path) -> list[dict[str, Any]]:
    """The .csv/.tsv/.txt files under base (up to 3 levels deep), each with a guess at what it holds."""
    files = sorted(p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in (".csv", ".tsv", ".txt") and len(p.relative_to(base).parts) <= 3)
    out = []
    for p in files:
        try:
            with p.open(encoding="utf-8-sig", errors="replace") as fh:
                first = fh.readline()
        except OSError:
            first = ""
        sep = "," if p.suffix.lower() == ".csv" else "\t"
        n = len(first.split(sep))
        out.append({"name": str(p.relative_to(base)), "kb": round(p.stat().st_size / 1024, 1),
                    "kind": "matrix" if n > 2 else "signature", "sample_columns": n - 1 if n > 2 else None})
    return out


@server.tool(title="Find data files")
@logged
async def find_data_files(folder: Annotated[str | None, Field(description="Folder to list. Defaults to the Sigshell data folder, ~/Sigshell/data.")] = None) -> str:
    """List expression matrices and signature files the user can analyse."""
    base = Path(folder).expanduser() if folder else config.DATA_DIR
    if not folder:
        base.mkdir(parents=True, exist_ok=True)
    if not base.is_dir():
        raise ToolError(f"{base} is not a folder.")
    files = data_files(base)
    if not files:
        return f"No .csv, .tsv or .txt files in {base}. Ask the user to put their expression matrix and signature there."
    lines = [f"Files in {base}:"]
    for f in files:
        kind = f"looks like a matrix ({f['sample_columns']} sample columns)" if f["kind"] == "matrix" else "looks like a gene list"
        lines.append(f"- {f['name']} ({f['kb']:.1f} KB): {kind}")
    return "\n".join(lines)


@server.tool(title="Check inputs")
@logged
async def check_inputs(matrix_file: Path_, signature_file: Annotated[str | None, Field(description="Path to the signature (one gene per line). Optional.")] = None) -> CallToolResult:
    """Validate an expression matrix (genes in rows, samples in columns) and a signature before any analysis. Reports problems; fixes nothing."""
    report = validate.check(_resolve(matrix_file), _resolve(signature_file) if signature_file else None)
    structured = {
        "errors": [p.__dict__ for p in report.errors],
        "warnings": [p.__dict__ for p in report.warnings],
        "genes": len(report.matrix.genes) if report.matrix else None,
        "samples": report.matrix.samples if report.matrix else None,
        "signature_found": report.found,
        "signature_missing": report.missing,
        "signature_has_weights": bool(report.signature and report.signature.weights),
        "constant_genes": report.constant_genes,
        "genes_with_na": report.genes_with_na,
        "ready": not report.errors,
    }
    return _result(validate.summary(report), structured)


@server.tool(title="List methods")
@logged
async def list_methods() -> str:
    """Describe every score and data transformation the installed sigscores offers, and the null models for significance, with known caveats."""
    inst = await _provenance()
    out = ["Scores (ids for the `scores` argument):"]
    for row in inst.methods["scores"]:
        out.append(f"- {row['id']} ({row['name']}): {methods.SCORES.get(row['id'], '')}")
    out.append("\nData transformations (`transform`), applied before scoring:")
    for row in inst.methods["transformers"]:
        out.append(f"- {row['id']} ({row['name']}): {methods.TRANSFORMERS.get(row['id'], '')}")
    out.append("\nNull models for test_significance (`null`):")
    out += [f"- {k}: {v}" for k, v in methods.NULL_MODELS.items()]
    out += [f"- not offered: {v}" for v in methods.NOT_OFFERED.values()]
    out.append(f"\n{inst.line}.")
    return "\n".join(out)


@server.tool(title="Prepare matrix")
@logged
async def prepare_matrix(
    matrix_file: Path_,
    remove_constant_genes: Annotated[bool, Field(description="Remove genes whose value is the same in every sample.")] = False,
    remove_genes_with_missing_values: Annotated[bool, Field(description="Remove genes with any missing value.")] = False,
) -> CallToolResult:
    """Write a copy of the matrix without constant genes and/or genes with missing values. Only on the user's explicit request; the original file is untouched."""
    if not (remove_constant_genes or remove_genes_with_missing_values):
        raise ToolError("Choose what to remove: remove_constant_genes and/or remove_genes_with_missing_values.")
    report = validate.check(_resolve(matrix_file))
    if report.errors:
        raise ToolError("The matrix has problems that must be fixed first.\n\n" + validate.summary(report))
    inst = await _provenance()
    step = session.next_step()
    rel = session.stage_input(_resolve(matrix_file))
    body = "\n".join([
        f'SIGSHELL_STEP <- "{step}"',
        f"x <- sigshell_read_matrix({r_literal(rel)})",
        "has_na <- rowSums(is.na(x)) > 0",
        "constant <- !has_na & sigscores:::areRowValuesEqual(x)  # the test colEnrichment uses (R/3-stats-functions.R:1666)",
        f"drop <- {'constant' if remove_constant_genes else 'FALSE'} | {'has_na' if remove_genes_with_missing_values else 'FALSE'}",
        "y <- x[!drop, , drop = FALSE]",
        f'out <- "outputs/{step}-matrix-prepared.csv"',
        "utils::write.csv(y, out, quote = TRUE, na = \"NA\")",
        f'sigshell_save_result("{step}", list(file = out, removed = rownames(x)[drop], kept = nrow(y)))',
    ])
    args = {"matrix_file": matrix_file, "remove_constant_genes": remove_constant_genes, "remove_genes_with_missing_values": remove_genes_with_missing_values}
    res = await _run(step, "prepare_matrix", args, body)
    path = session.dir / res["file"]
    removed = _as_list(res.get("removed"))
    text = (
        f"Wrote {path} with {res['kept']} genes; removed {len(removed)}: {', '.join(removed[:15])}{' …' if len(removed) > 15 else ''}.\n"
        f"Use this file as matrix_file from now on. The original {Path(matrix_file).name} is unchanged.\n\n{_provenance_line(inst, step)}"
    )
    return _result(text, {"file": str(path), "removed": removed, "kept": res["kept"]}, step)


@server.tool(title="Compute scores")
@logged
async def compute_scores(
    matrix_file: Path_,
    signature_file: Path_,
    scores: Annotated[list[str], Field(description="Score ids, e.g. ['mean', 'median']. See list_methods.")],
    transform: Literal["none", "stepFunction", "quantile", "z"] = "none",
    transform_options: Annotated[dict[str, Any], Field(description="Options for the transform: stepFunction {method, by, thr, y}; quantile {ties_method}; z {by}.")] = {},  # noqa: B006
    trim: Annotated[float, Field(ge=0, lt=0.5, description="Fraction trimmed from each end by trimmedMean.")] = 0.0,
    na_rm: Annotated[bool, Field(description="Ignore missing values (sigscores' default).")] = True,
    drop_missing_genes: Annotated[bool, Field(description="Score only the signature genes found in the matrix. Off by default: missing genes are an error.")] = False,
) -> CallToolResult:
    """Compute summary scores of a gene signature for every sample (sigscores::computeSigScores, sampling = "none")."""
    inst = await _provenance()
    _check_scores(scores, inst)
    report = _validated(matrix_file, signature_file, drop_missing_genes)
    targs = _transform_args(transform, transform_options)
    _guards(report, scores, transform, targs)
    weights = bool(report.signature and report.signature.weights)
    step = session.next_step()
    mrel, srel = session.stage_input(_resolve(matrix_file)), session.stage_input(_resolve(signature_file))
    body = _r_inputs(step, mrel, srel, drop_missing_genes, scores, transform, targs, trim, weights) + f"""
run <- sigshell_capture(computeSigScores(x = x, i = i, scores = {r_literal(scores)}, na.rm = {r_literal(na_rm)}, args = args))
scores <- run$value
utils::write.csv(scores, "outputs/{step}-scores.csv", row.names = FALSE)
saveRDS(scores, "outputs/{step}-scores.rds")
sigshell_save_result("{step}", list(scores = scores, warnings = run$warnings, messages = run$messages,
  sink_left_open = run$sink_left_open, all_na = sigshell_explain_all_na(scores, x, i, {r_literal(na_rm)}, args),
  genes = rownames(x), samples = colnames(x), n_genes_scored = length(i)))
"""
    args = {"matrix_file": matrix_file, "signature_file": signature_file, "scores": scores, "transform": transform,
            "transform_options": transform_options, "trim": trim, "na_rm": na_rm, "drop_missing_genes": drop_missing_genes}
    res = await _run(step, "compute_scores", args, body)
    _check_same_table(report, res)
    table = _columns(res["scores"])
    samples = table["sampleID"]
    rows = [[samples[k]] + [table[s][k] for s in scores] for k in range(len(samples))]
    rid = f"r{step}"
    session.results[rid] = Result(rid, "scores", step, scores, samples, {"rds": f"outputs/{step}-scores.rds", "csv": f"outputs/{step}-scores.csv"})
    notes = _r_failures(res) + _caveats(report, scores, transform, drop_missing_genes, weights)
    text = "\n".join([
        f"Scores for {len(samples)} samples, signature of {res['n_genes_scored']} genes (result id {rid}):\n",
        _table(["sample"] + scores, rows),
        f"\nFull precision: {session.dir / f'outputs/{step}-scores.csv'}",
        *([("\nNotes:\n" + "\n".join(f"- {n}" for n in notes))] if notes else []),
        "\n" + _provenance_line(inst, step),
    ])
    structured = {"result_id": rid, "samples": samples, "scores": {s: table[s] for s in scores}, "notes": notes,
                  "n_genes_scored": res["n_genes_scored"], "provenance": {"commit": inst.commit, **inst.versions},
                  "provenance_line": inst.line, "session": str(session.dir), "step": step}
    return _result(text, structured, step)


@server.tool(title="Test significance")
@logged
async def test_significance(
    matrix_file: Path_,
    signature_file: Path_,
    scores: Annotated[list[str], Field(description="Score ids, e.g. ['mean'].")],
    null: Annotated[Literal["random_genes", "permutation", "bootstrap"], Field(description="How random scores are made; see list_methods.")] = "random_genes",
    n_repeat: Annotated[int, Field(ge=10, le=100000, description="Number of random scores per sample.")] = 1000,
    seed: Annotated[int, Field(description="Random seed, so the result can be reproduced.")] = 1,
    alternative: Annotated[Literal["greater", "less", "two.sided"], Field(description="greater: is the observed score higher than random ones? two.sided compares absolute values (finding asl-abs).")] = "greater",
    conf_level: Annotated[float, Field(gt=0.5, lt=1)] = 0.95,
    transform: Literal["none", "stepFunction", "quantile", "z"] = "none",
    transform_options: dict[str, Any] = {},  # noqa: B006
    trim: Annotated[float, Field(ge=0, lt=0.5)] = 0.0,
    na_rm: bool = True,
    drop_missing_genes: bool = False,
) -> CallToolResult:
    """Compare each sample's observed score with scores of random gene sets (sigscores::computeSigScores with sampling, then computeSignificance)."""
    inst = await _provenance()
    _check_scores(scores, inst)
    report = _validated(matrix_file, signature_file, drop_missing_genes)
    targs = _transform_args(transform, transform_options)
    _guards(report, scores, transform, targs)
    weights = bool(report.signature and report.signature.weights)
    sampling = {"random_genes": "rndsig", "permutation": "permutation", "bootstrap": "bootstrap"}[null]
    step = session.next_step()
    mrel, srel = session.stage_input(_resolve(matrix_file)), session.stage_input(_resolve(signature_file))
    na = r_literal(na_rm)
    body = _r_inputs(step, mrel, srel, drop_missing_genes, scores, transform, targs, trim, weights) + f"""
obs <- sigshell_capture(computeSigScores(x = x, i = i, scores = {r_literal(scores)}, na.rm = {na}, args = args))
set.seed({seed})
nul <- sigshell_capture(computeSigScores(x = x, i = i, scores = {r_literal(scores)}, na.rm = {na}, args = args,
                                         sampling = {r_literal(sampling)}, n.repeat = {n_repeat}L))
observed <- obs$value; random <- nul$value
saveRDS(observed, "outputs/{step}-observed.rds"); saveRDS(random, "outputs/{step}-random.rds")
signif_one <- function(...) tryCatch(list(v = computeSignificance(...), e = NA_character_), error = function(e) list(v = NULL, e = conditionMessage(e)))
rows <- list()
for (k in {r_literal(scores)}) for (s in observed$sampleID) {{
  o <- observed[[k]][observed$sampleID == s]; r <- random[[k]][random$sampleID == s]
  a <- signif_one(obs = o, rnd = r, type = "asl", alternative = {r_literal(alternative)})
  e <- signif_one(obs = o, rnd = r, type = "se")
  cs <- signif_one(obs = o, rnd = r, type = "ci", ci = "standard", conf.level = {conf_level!r})
  cp <- signif_one(obs = o, rnd = r, type = "ci", ci = "percentile", conf.level = {conf_level!r})
  pick <- function(z, nm) if (is.null(z$v)) NA_real_ else unname(z$v[nm])
  rows[[length(rows) + 1L]] <- data.frame(sample = s, score = k, observed = o, null_mean = mean(r), null_sd = stats::sd(r),
    n_random = sum(!is.na(r)), asl = if (is.null(a$v)) NA_real_ else a$v, se = if (is.null(e$v)) NA_real_ else e$v,
    ci_standard_lower = pick(cs, "lower"), ci_standard_upper = pick(cs, "upper"),
    ci_percentile_lower = pick(cp, "lower"), ci_percentile_upper = pick(cp, "upper"),
    problems = paste(stats::na.omit(c(a$e, e$e, cs$e, cp$e)), collapse = "; "), stringsAsFactors = FALSE)
}}
significance <- do.call(rbind, rows)
utils::write.csv(significance, "outputs/{step}-significance.csv", row.names = FALSE)
sigshell_save_result("{step}", list(significance = significance, observed = observed,
  warnings = unique(c(obs$warnings, nul$warnings)), messages = unique(c(obs$messages, nul$messages)),
  sink_left_open = obs$sink_left_open || nul$sink_left_open,
  all_na = sigshell_explain_all_na(observed, x, i, {na}, args),
  genes = rownames(x), samples = colnames(x), n_genes_scored = length(i)))
"""
    args = {"matrix_file": matrix_file, "signature_file": signature_file, "scores": scores, "null": null, "n_repeat": n_repeat,
            "seed": seed, "alternative": alternative, "conf_level": conf_level, "transform": transform,
            "transform_options": transform_options, "trim": trim, "na_rm": na_rm, "drop_missing_genes": drop_missing_genes}
    res = await _run(step, "test_significance", args, body)
    _check_same_table(report, res)
    sig = _columns(res["significance"])
    n = len(sig["sample"])
    cols = ["sample", "score", "observed", "null_mean", "null_sd", "asl", "ci_percentile_lower", "ci_percentile_upper"]
    rows = [[sig[c][k] for c in cols] for k in range(n)]
    rid = f"r{step}"
    samples = _as_list(res["observed"]["sampleID"])
    session.results[rid] = Result(rid, "significance", step, scores, samples, {
        "observed": f"outputs/{step}-observed.rds", "random": f"outputs/{step}-random.rds", "csv": f"outputs/{step}-significance.csv"})
    meaning = {"greater": f"fraction of the {n_repeat} random scores at least as high as the observed score",
               "less": f"fraction of the {n_repeat} random scores lower than the observed score",
               "two.sided": f"fraction of the {n_repeat} random scores whose absolute value is at least the observed absolute value (assumes random scores centred at 0; finding asl-abs)"}[alternative]
    notes = _r_failures(res) + _caveats(report, scores, transform, drop_missing_genes, weights)
    problems = [f"{sig['sample'][k]}/{sig['score'][k]}: {sig['problems'][k]}" for k in range(n) if sig["problems"][k]]
    if problems:
        notes.append("computeSignificance could not compute some values: " + "; ".join(problems[:10]))
    notes.append(f"asl is the {meaning}. With {n_repeat} random scores the smallest non-zero asl is {1 / n_repeat:.2g}; 0 means none of them reached the observed score.")
    notes.append(f"The intervals come from the random scores (null model '{null}'), so they describe the null distribution, not the uncertainty of the observed score (findings resampling-null, asl-abs). Standard intervals and SE are in the CSV.")
    text = "\n".join([
        f"Significance for {len(samples)} samples × {len(scores)} scores, null model {null} ({sampling}), {n_repeat} random scores, seed {seed}, alternative {alternative} (result id {rid}):\n",
        _table(cols, rows),
        f"\nFull table: {session.dir / f'outputs/{step}-significance.csv'}",
        "\nNotes:\n" + "\n".join(f"- {x}" for x in notes),
        "\n" + _provenance_line(inst, step),
    ])
    structured = {"result_id": rid, "significance": sig, "notes": notes, "n_genes_scored": res["n_genes_scored"],
                  "null": null, "n_repeat": n_repeat, "seed": seed, "alternative": alternative,
                  "provenance": {"commit": inst.commit, **inst.versions}, "provenance_line": inst.line,
                  "session": str(session.dir), "step": step}
    return _result(text, structured, step)


def _get_result(result_id: str) -> Result:
    if result_id not in session.results:
        known = ", ".join(session.results) or "none yet"
        raise ToolError(f"No result {result_id} in this session (results: {known}). Run compute_scores or test_significance first.")
    return session.results[result_id]


@server.tool(title="Plot scores")
@logged
async def plot_scores(
    result_id: Annotated[str, Field(description="Result id from compute_scores or test_significance, e.g. r002.")],
    kind: Annotated[Literal["heatmap", "correlation", "boxplot", "scatter"], Field(description="heatmap: samples × scores; correlation: Pearson correlation between scores; boxplot: each score across samples; scatter: each score per sample.")],
    scores: Annotated[list[str] | None, Field(description="Subset of the result's scores; default all.")] = None,
) -> CallToolResult:
    """Draw a figure from computed scores with sigscores' plotting functions. Returns the image and saves a PNG."""
    inst = await _provenance()
    res = _get_result(result_id)
    chosen = scores or res.scores
    extra = [s for s in chosen if s not in res.scores]
    if extra:
        raise ToolError(f"{result_id} has no scores {', '.join(extra)}; it has {', '.join(res.scores)}.")
    if kind == "correlation" and len(chosen) < 2:
        raise ToolError("A correlation plot needs at least two scores.")
    if kind == "correlation" and len(res.samples) < 3:
        raise ToolError("A correlation plot needs at least three samples.")
    fn = {"heatmap": "heatmapSigScores", "correlation": "heatmapCorSigScores", "boxplot": "boxplotSigScores", "scatter": "scatterplotSigScores"}[kind]
    src = res.files["rds"] if res.kind == "scores" else res.files["observed"]
    step = session.next_step()
    png = f"outputs/{step}-{kind}.png"
    body = f"""SIGSHELL_STEP <- "{step}"
d <- readRDS({r_literal(src)})
p <- {fn}(data = d, scores = {r_literal(chosen)})
grDevices::png({r_literal(png)}, width = 1800, height = 1400, res = 200)
if (inherits(p, "Heatmap")) ComplexHeatmap::draw(p) else print(p)
invisible(grDevices::dev.off())
sigshell_save_result("{step}", list(file = {r_literal(png)}))
"""
    await _run(step, "plot_scores", {"result_id": result_id, "kind": kind, "scores": chosen}, body)
    path = session.dir / png
    text = f"{kind} of {', '.join(chosen)} from {result_id}, drawn by sigscores::{fn}. Saved to {path}.\n\n{_provenance_line(inst, step)}"
    return _result(text, {"file": str(path), "function": fn, "step": step}, step, [path])


@server.tool(title="Plot null distribution")
@logged
async def plot_null_distribution(
    result_id: Annotated[str, Field(description="Result id from test_significance.")],
    sample: Annotated[str, Field(description="Sample name.")],
    score: Annotated[str, Field(description="Score id.")],
    bins: Annotated[int, Field(ge=5, le=200)] = 30,
) -> CallToolResult:
    """Histogram of the random scores for one sample and score, with the observed score as a dashed line (sigscores::histogramRndSigScores)."""
    inst = await _provenance()
    res = _get_result(result_id)
    if res.kind != "significance":
        raise ToolError(f"{result_id} comes from compute_scores; run test_significance first.")
    if sample not in res.samples or score not in res.scores:
        raise ToolError(f"{result_id} has samples {', '.join(res.samples[:10])} and scores {', '.join(res.scores)}.")
    step = session.next_step()
    png = f"outputs/{step}-null-{sample}-{score}.png"
    body = f"""SIGSHELL_STEP <- "{step}"
observed <- readRDS({r_literal(res.files['observed'])})
random <- readRDS({r_literal(res.files['random'])})
p <- histogramRndSigScores(rndata = random, data = observed, obs = {r_literal(sample)}, score = {r_literal(score)}, bins = {bins}L)
grDevices::png({r_literal(png)}, width = 1600, height = 1100, res = 200)
print(p)
invisible(grDevices::dev.off())
sigshell_save_result("{step}", list(file = {r_literal(png)}))
"""
    await _run(step, "plot_null_distribution", {"result_id": result_id, "sample": sample, "score": score, "bins": bins}, body)
    path = session.dir / png
    text = f"Random {score} scores for {sample} from {result_id}, with the observed score as a dashed line. Saved to {path}.\n\n{_provenance_line(inst, step)}"
    return _result(text, {"file": str(path), "step": step}, step, [path])


@server.tool(title="Get R script")
@logged
async def get_r_script() -> CallToolResult:
    """The plain R script that reproduces this session without AI, and where it is saved."""
    path = session.refresh_script()
    steps = session.step_files()
    text = path.read_text(encoding="utf-8")
    msg = (f"{path} replays {len(steps)} steps. Run it with `Rscript session.R` from {session.dir}; it reads the copies of the input files in inputs/.\n\n"
           f"```r\n{text}\n```") if steps else "No analysis has run in this session yet, so the script only contains the preamble."
    return _result(msg, {"path": str(path), "steps": [p.name for p in steps]})


# ---------------------------------------------------------------- resources

@server.resource("sigshell://paper", name="paper", title="Barberis & Buffa 2026 (PDF)", mime_type="application/pdf",
                 description="The sigscores paper. " + config.PAPER_CITATION)
def paper() -> bytes:
    return config.PAPER_PDF.read_bytes()


@server.resource("sigshell://paper/citation", name="citation", title="How to cite sigscores", mime_type="text/plain")
def citation() -> str:
    return config.PAPER_CITATION


@server.resource("sigshell://vignette", name="vignette", title="sigscores vignette (R Markdown)", mime_type="text/markdown",
                 description="vignettes/sigscores.Rmd at the pinned sigscores commit.")
def vignette() -> str:
    return (config.SIGSCORES_SRC / "vignettes" / "sigscores.Rmd").read_text(encoding="utf-8")


@server.resource("sigshell://callmap", name="callmap", title="sigscores call map", mime_type="text/html",
                 description="Every sigscores function: call graph, description, arguments, source, coverage, recorded runs and findings.")
def callmap() -> str:
    path = config.CALLMAP_HTML if config.CALLMAP_HTML.exists() else config.REPO_ROOT.parent / "reference" / "sigscores-call-map.html"
    return path.read_text(encoding="utf-8")


@server.resource("sigshell://findings", name="findings", title="Known issues in sigscores", mime_type="text/markdown")
def findings() -> str:
    return config.FINDINGS_MD.read_text(encoding="utf-8")


@server.resource("sigshell://session/script", name="session-script", title="R script for this session", mime_type="text/x-r")
def session_script() -> str:
    return session.refresh_script().read_text(encoding="utf-8")


def main() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main()
