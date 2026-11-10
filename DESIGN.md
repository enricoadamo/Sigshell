# Sigshell design

Sigshell lets a biologist who doesn't program use the sigscores R package by asking in plain language. Claude calls a small set of MCP tools; every number comes from sigscores, run by R on the user's machine, and every session can be replayed as a plain R script without AI.

This document records what Phase 1 established about the library, then proposes the tools, the server and the user interface. Line references are to sigscores at commit `40f55c5` (`../sigscores`).

Status, 2026-11-10: Phases 1 and 2 are done. The server in `src/sigshell/` implements sections 5 and 6. Phase 3 has started: option C of section 7, the local web page, is in `src/sigshell/web.py`. The other interface options wait for decision 1 in section 9.

## 1. What Phase 1 verified

Environment, checked on 2026-11-10: macOS 26.6.2 on arm64, R 4.4.1, sigscores 0.1.0 installed from `../sigscores`, GSVA 2.0.7, matrixStats 1.5.0, ggplot2 3.5.1, ComplexHeatmap 2.22.0, uv 0.11.11, Node 26.10.0, Claude Code 2.1.280, Claude Desktop 4.23118.1.

| Check | Method | Result |
|---|---|---|
| Pin | `git -C ../sigscores log -1` | `40f55c5`, clean working tree |
| Call map vs source | Re-parsed all of `R/` and compared with the map's `LIB` | 138 of 138 functions match on source text, export status, argument names and defaults; installed bodies equal the pinned source; the 184 static call links are identical |
| Recorded runs | Replayed all 184 `RUNS` in fresh R processes with the original harness | 183 identical. Run 16 differs only in the timestamps a DEBUG logger prints; it matches once timestamps are normalised |
| Findings | `findings/reproduce.R`, one minimal case per finding, written independently of the map's snippets | 36 of 36 confirmed. The map marked 3 as "read in the source, not run" (`no-seed`, `docs-random`, `docs-generic`); all 3 are now confirmed by running. 2 new findings added (section 4) |
| Published vignette | Knitted `vignettes/sigscores.Rmd` here and compared with `articles/sigscores.html` on the `gh-pages` branch (deploy commit `cece1bf`, built from `40f55c5`) | 28 of 30 code blocks identical. The other 2 differ only in the `<bytecode: 0x…>` address printed with a function. All 1,237 printed numbers and both tables match, so macOS here reproduces the authors' Linux build |

The live site `https://alebarberis.github.io/sigscores` failed with a TLS error from this machine (curl exit 35). The `gh-pages` branch holds the same build, so it was used instead.

Nothing in the call map turned out wrong. Two parts were not re-checked and stay secondary until Phase 3 regenerates them: the external `pkg::fun` lists, and line coverage (14.5% of 1,381 lines in the map).

Fixtures written in Phase 1:

- `tests/d_recorded_runs/recorded-runs.json`: the 184 runs, each marked `exact` or `timestamps-normalised`, with `replay.R`.
- `tests/b_vignette/published-blocks.json`: the 30 published vignette blocks.

## 2. The library paths Sigshell builds on

**Entry point.** `computeSigScores` (`R/6-compute-scores.R:247`) checks `sampling` (`:268`) and takes one of three routes:

- `none`: calls `computeScores` once (`:277`).
- `permutation` and `bootstrap`: draw row orders with `sampleData` (`:294`). For each run, `forLoop` reorders the rows and restores the original row names (`:309-311`), scores, and adds `run` (`:321`).
- `rndsig` and `rndsigsub`: draw gene sets with `randomSignatures` (`:343`), then score each set (`:361`).

The repeated routes are stacked with `data.table::rbindlist` (`:387`).

**Engine.** `computeScores` (`R/5-scorers.R:1109`) does five things:

1. Coerces anything that is not a matrix into one column (`:1125-1126`) and invents missing names (`:1129-1131`).
2. Keeps only known score ids with `intersect` (`:1139`) and looks the scorers up (`:1145`).
3. Keeps only `args` whose names match a scorer (`:1158-1165`).
4. Converts gene names to row numbers with `match` (`:1174`), so unknown genes become `NA`.
5. Runs each scorer through `forLoop` (`:1190`) inside `tryCatch`, which turns any error into `NA` for every sample (`:1196-1210`), and assembles a `data.frame` (`:1234-1238`).

**Run-time links that static analysis can't see.** All of them are `do.call` sites:

- `computeScores` runs each scorer at `R/5-scorers.R:1198`.
- `forLoop` runs its `fun` at `R/2-parallel-functions.R:88` (parallel) and `:118` (serial).
- Each of the 18 scorers runs `transform.fun`, for example at `R/5-scorers.R:180` for `meanScorer`.

**Defaults** (from `formals(computeSigScores)`, `R/6-compute-scores.R:248-263`): `na.rm = TRUE`; `scores` is all 18 ids; `sampling = "none"`; `n.repeat = 10L`; `cores = 1L`; `filename = "sigscores"`, which is never used without an explicit argument (finding `outdir-filename`).

**Randomness.** There are only two `sample()` calls in `R/`: `R/0-utility-functions.R:729` (`sampleData`) and `:838` (`randomSignatures`). There is no seed argument and no `set.seed` in the package. Both draws happen in the main process before the parallel loop, so a run with `cores = 2` equals the serial run under the same `set.seed` (checked in `no-seed`).

**Behaviour no argument controls.** It's listed in `findings/reproduce.R`. The ones the server must guard against are in section 5.

## 3. Paper, documentation and code disagreements

Sources: Barberis & Buffa 2026 (sections 2.1 to 2.3 and Figure 1), the roxygen documentation in `R/`, the vignette, and the code.

| # | Topic | Paper or docs say | Code does | Evidence |
|---|---|---|---|---|
| 1 | Inherited metrics | Paper 2.1: six metrics from sigQC, including "first principal component" | No PC1 score. The 18 ids are listed at `R/0-utility-functions.R:38-57`; PLAGE, an SVD-based score from GSVA (`R/3-stats-functions.R:1705`), is the closest | `getAvailableScores()` |
| 2 | Transformation | Paper 2.1: each scorer transforms "before the computation of the scores" | `trimmedMeanScorer` and `aadScorer` subset to the signature first and then transform (`R/5-scorers.R:217-223`, `:640-645`); the other 16 transform the whole matrix first (for example `:179-186`). `transform.sub` is documented (`:35`) but read by no scorer | `transform-order`, `docs-transform-sub` |
| 3 | Resampling | Paper 2.2: data sampling "perturbs the observed data… enabling evaluation of score stability" | Rows are resampled whole and their names restored (`R/6-compute-scores.R:309-311`). Permutation therefore scores a random gene set of the same size, the same null as `rndsig`; bootstrap also allows a gene twice. None of them measures how stable the observed score is | `resampling-null` (new) |
| 4 | Inference | Paper 2.2: `computeSigScores()` "facilitates the calculation of… ASL, standard errors, and confidence intervals" | `computeSigScores` returns scores only. Inference lives in `computeSignificance` (`R/7-significance.R:36`), which no function in the package calls and the vignette never shows | call map: no callers |
| 5 | Random signatures | Paper 2.2: sets "matching the size of the original signature… from a background pool" | Size is `length(i)`, counting genes that aren't in the matrix (`R/0-utility-functions.R:818`). `rndsigsub` removes the first k rows instead of the signature's rows (`:832`). The vignette (`vignettes/sigscores.Rmd:422`) describes the intended behaviour | `rndsig-size`, `rndsigsub-wrong-rows` |
| 6 | Mode | Paper 2.1: mode is a measure of central tendency | Ties go to the smallest value (`R/3-stats-functions.R:407`). With no repeated values, as in the vignette's data and most continuous expression data, mode is the minimum | `modal-tie`, `mode-is-min` (new) |
| 7 | Significance | Paper 2.2: "following established bootstrap and resampling methodologies" | The default two-sided ASL compares absolute values, which assumes a null centred at 0 (`R/7-significance.R:131`). The percentile interval is taken from the null replicates (`:275-289`), and the standard interval is `obs ± z·SE` with SE from the null (`:335-364`), so neither is a confidence interval for the observed score | `asl-abs` |
| 8 | Figure 1 | Panels B to E | 1B (null histogram) is not in the vignette. 1C and 1D show 10 scores in a blue palette without clustering, whereas the vignette's correlation plot and heatmap show all 18, clustered, in red and blue. 1E shows all 18 scores, whereas the vignette's boxplot shows 7. The figure must come from a different run | vignette PNGs on `gh-pages` |
| 9 | Docs vs code | `sampling = "random"` (`R/6-compute-scores.R:49`); `stepFunction` gives `y[1]` above the threshold (`R/3-stats-functions.R:1830`); scorers accept gene names in `i` (`R/5-scorers.R:13`); a `genericScorer` route (`man/getScorers.Rd`); `outdir` alone saves the result (`R/6-compute-scores.R` docs) | No such option; `y[1]` is used below the threshold (`:1911`); `sum`, `mean`, `median` and `mad` reject names; no `genericScorer` exists; nothing is saved without `filename` | `docs-*`, `outdir-filename` |
| 10 | Docs vs code | `getAvailableRandomSamplers()` lists the sampling options | It omits `none`, the default (`R/0-utility-functions.R:127-132`) | `samplers-none` |

Where the paper and code agree, Sigshell follows the code: the z-score delegates to `GSVA::zscoreParam` (`R/3-stats-functions.R:1706`), which implements Lee et al. (2008) as the paper says; the three transformers are those in the paper (`R/0-utility-functions.R:90-94`).

## 4. Findings

`findings/findings.json` holds 41 findings; `findings/FINDINGS.md` lists them, and `findings/reproduce.R <id>` reproduces each one. All 41 were confirmed on 2026-11-10:

- the 36 from the call map;
- 2 found in Phase 1: `resampling-null` and `mode-is-min`;
- 3 found while building the server: `dup-signature-gene` (a gene listed twice is scored twice, `R/5-scorers.R:1174`), `dup-matrix-gene` (only the first of two same-named rows is used) and `quantile-na-rows` (quantile normalisation drops NA rows, so scorers index the wrong rows, `R/4-data-preprocessing.R:230`).

`findings/upstream/` holds 10 draft issues covering the 27 findings that need a change upstream, each with a reproduction that was run in a fresh R process. None has been filed.

## 5. Tools

The tools follow what a biologist asks, not the 74 exports. Seven exports do the science: `computeSigScores`, `computeSignificance`, the four plot functions and `histogramRndSigScores`. Lookups such as `getAvailableScores` provide names and descriptions.

| Tool | What the biologist gets | sigscores calls |
|---|---|---|
| `find_data_files` | The expression and signature files in the Sigshell data folder, so they don't have to type paths | none |
| `check_inputs` | A validation report: shape, orientation, gene IDs, missing and duplicated genes, case collisions, NA and non-numeric cells, constant genes, duplicated sample names. Problems are reported, never fixed | none (pure validation, before any R runs) |
| `list_methods` | The 18 scores, 3 transformations and 3 null models in plain language, with the caveats from the findings | `getAvailableScores`, `getAvailableDataTransformers`, `getAvailableRandomSamplers` |
| `prepare_matrix` | A new matrix file without constant genes or rows with NA, written only when the user asks; recorded in the R script | none (base R `read`/`write`) |
| `compute_scores` | One row per sample, one column per score, saved as CSV | `computeSigScores(sampling = "none")`, optionally with `getDataTransformer` |
| `test_significance` | For each sample and score: observed value, null mean and SD, ASL, standard error and both intervals, with the null model stated | `computeSigScores(sampling = …)`, `computeSignificance` |
| `plot_scores` | A heatmap, correlation heatmap, boxplot or scatter plot as an image, also saved as PNG | `heatmapSigScores`, `heatmapCorSigScores`, `boxplotSigScores`, `scatterplotSigScores` |
| `plot_null_distribution` | The random scores for one sample and score, with the observed value marked | `histogramRndSigScores` |
| `get_r_script` | The plain R script that replays the whole session without AI | none |

Guards, each from a confirmed finding. Every guard reports the problem; none fixes data silently.

- **Data frames** (`df-input`): the server always reads files into a numeric matrix in R, and `check_inputs` first confirms the file is numeric with gene IDs in the first column.
- **Missing, duplicated or case-mismatched signature genes** (`unknown-gene`, `rndsig-size`): reported. `compute_scores` and `test_significance` stop until the user either supplies a corrected signature or sets `drop_missing_genes = true`, which is written into the script.
- **Constant genes or NA rows with the GSVA-based scores** (`gsva-constant-gene`, `gsva-na-row`, `one-sample`): those four scores are refused with an explanation, and `prepare_matrix` is offered.
- **A scorer that returns NA for every sample** (`silent-na`): the server calls that scorer directly through sigscores to retrieve the real error and reports it.
- **R's output left switched off** (`gsva-sink`): every call runs in a fresh R process, so it can't leak. The server checks `sink.number()` and reports a GSVA failure when it happens.
- **`rndsigsub`** (`rndsigsub-wrong-rows`): not offered.
- **Null models** (`resampling-null`): `random_genes` (`rndsig`), `permutation` and `bootstrap` are offered and described as what they are: random-gene-set nulls.
- **Transformations with `trimmedMean` or `aad`** (`transform-order`): the result says those two transform after subsetting.
- **Two-sided ASL** (`asl-abs`): the tool's default `alternative` is `"greater"` ("is the signature higher than random sets?"), always stated in the result. `"two.sided"` stays available, with its caveat.
- **Unknown or misspelled score ids** (`typo-score`): rejected by the tool before R runs.
- **Duplicated genes** (`dup-signature-gene`, `dup-matrix-gene`): a gene listed twice in the signature, or two matrix rows with the same name, is an error in `check_inputs`.
- **Quantile normalisation with NA genes** (`quantile-na-rows`): refused until `prepare_matrix` removes them.
- **Z-standardisation by columns, or robust** (`z-cols`, `z-robust`): not offered; only `by = "rows"` with `robust = FALSE` is.
- **Hexadecimal cells:** R reads `0x1A` as 26; the validator treats anything but a decimal number, `NA` or an empty cell as an error.

## 6. Server

- **Language and SDK:** Python 3.13 via uv, `mcp` 2.3.0 pinned, `MCPServer` with the stdio transport. That SDK's newest revision is `2026-07-28`, the current revision of the spec.
- **Measured with MCP Inspector 2.14.0** (CLI, 2026-11-10): with `--protocol-era legacy` the server negotiates `2025-11-25` through the initialisation handshake; with `modern` and `auto` it answers `2026-07-28`. `tools/list --strict` reports no schema portability problems; `tools/call` and `resources/read` work in the modern era. Inspector asks for Node ≥ 26.12.1 and ran with a warning on Node 26.10.0. Which revision Claude Desktop 4.23118.1 uses can only be read from its logs once Sigshell is registered there (decision 4).
- **R bridge:** each tool call writes a self-contained R script to the session folder and runs it with `Rscript --vanilla` in a fresh process. Loading sigscores takes about 0.1 s because GSVA loads only when used. The script writes its result as JSON with full precision (`jsonlite`, `digits = NA`), plus CSV and PNG files. A fresh process per call isolates the `sink` and parallel side effects and makes every step replayable.
- **Session folder:** `~/Sigshell/sessions/<YYYYMMDD-HHMMSS>/` with:
  - `calls.jsonl`: tool, arguments, time, duration, status;
  - `steps/NNN-<tool>.R`;
  - `outputs/`;
  - `session.R`: all steps in order, runnable with `Rscript session.R`.
- **Provenance:** every result states the sigscores commit (read from `SIGSCORES_SRC` with git), the sigscores, GSVA, matrixStats, ggplot2, ComplexHeatmap and R versions, and the platform. At start-up the server checks that the installed sigscores' function bodies equal the pinned source, and refuses to run if they don't.
- **Validation** happens in Python before R runs. R then reads the file with the same rules (`read.delim`/`read.csv`, `row.names = 1`, `check.names = FALSE`) and the server checks that R saw the same dimensions and names.
- **Resources:**
  - `sigshell://paper`: the PDF, CC BY 4.0, with its citation in the description;
  - `sigshell://vignette`: `vignettes/sigscores.Rmd` from the pin;
  - `sigshell://callmap`: the regenerated call map;
  - `sigshell://findings`;
  - `sigshell://session/script`.
- **Server instructions** tell Claude to run `check_inputs` first, never to state a number that didn't come from a tool, and to quote the provenance line when reporting results.

## 7. User interface options

| Option | Works without an API key | Effort | What the biologist sees | Reproducibility |
|---|---|---|---|---|
| **A. MCP Apps views in Claude Desktop** (`ui://` resources, host renders an iframe) | Yes, with a Claude subscription. Claude Desktop supports MCP Apps according to modelcontextprotocol.io | High: HTML views, the postMessage protocol, and file input from a sandboxed iframe still to be proven | Chat plus interactive tables and plots in the conversation | Same R scripts |
| **B. Locked-down launcher around Claude Code** (`sigshell chat` starts `claude` with only this server, `--strict-mcp-config`, Bash and file edits denied, a fixed system prompt) | Yes, with a Claude subscription | Low | A terminal. File paths can be dragged in, but plots open as separate files | Same R scripts. Headless `claude -p` also suits the experiments |
| **C. Local page without AI** (`sigshell ui` serves a page on localhost) | Yes, and works offline with no Claude at all | Medium | A form with real file upload, score choices, tables, plots and a download button for the R script. No plain-language questions | Best: deterministic, same R bridge |
| **D. Claude Desktop with plain MCP tools**, packaged as a one-click Desktop Extension | Yes, with a Claude subscription | Low to medium; extension packaging for a uv-based server still to be checked | Chat with tables and plot images inline. Files are picked from the Sigshell data folder | Same R scripts |

**Recommendation: D as the main interface, plus C.**

- D meets the brief's "ask in plain language" with the least machinery, because Claude Desktop already shows images and tables.
- C covers biologists without Claude, offers real file upload (it drops files into the data folder that D reads), hosts the call map, and gives a no-AI way to download the script.
- B costs little and is needed anyway for headless experiments, so it ships as a power-user command.
- A is deferred until D works. It is the only option that needs work we can't yet prove (file input from the sandbox).

### 7.1 Option C as built

`uv run sigshell-ui` serves the page at `http://127.0.0.1:8787` (or any free port) and opens the browser. The code is in `src/sigshell/web.py` and `src/sigshell/web/`.

- **Same tools as the MCP server.** Every analysis goes through `server.call_tool`, the entry point an MCP client uses. The page therefore gets the same argument validation, guards (section 5), step scripts, session folder and provenance. `web.py` computes no numbers. It moves files and passes a fixed list of arguments per tool.
- **Steps on the page:**
  1. Data: drop a file or pick one from the data folder.
  2. Check: `check_inputs`, with `prepare_matrix` offered for constant or NA genes, and the `drop_missing_genes` choice.
  3. Scores, grouped as level, spread and GSVA-based. The GSVA group is disabled with the reason when the guard would refuse it. Then the table, the CSV and the four plots.
  4. Significance: null model, number of random scores, seed and alternative. A table with a histogram per row.
  5. Reproduce: `session.R`, and the whole session as a zip.
- **Uploads** go into the data folder (`~/Sigshell/data`), so a later Claude session sees the same files. Names are reduced to `[A-Za-z0-9._-]`. Only `.csv`, `.tsv` and `.txt` are accepted. A different file with the same name is kept: the new one gets a `-2` suffix.
- **Example data:** `r/vignette_example.R` runs the vignette's own `set.seed(5381)` and data chunks, so the page's example gives the published scores. `tests/web` checks S1 and S2 against `tests/b_vignette`.
- **Reachable only from this computer:** the page listens on 127.0.0.1 only. Any other `Host` header is refused, which blocks DNS rebinding. POST requests need an `X-Sigshell` header that another site can't send without a CORS preflight, and the server never answers preflights. Session files are served only from inside the session folder.
- **No external libraries:** plain HTML, CSS and JavaScript, so the page works offline. Light and dark follow the system setting. Checked at 1280 px and 390 px in headless Chrome.

## 8. Verification and experiments (outline)

Tests sit in `tests/`, grouped as the brief asks:

- **(a)** `a_hand`: cases computed by hand from the paper's definitions.
- **(b)** `b_vignette`: the published blocks.
- **(c)** `c_tools_vs_r`: every tool against the same call in a separate Rscript, value for value.
- **(d)** `d_recorded_runs`: the 184 fixtures.
- **(e)** `e_properties`: awkward inputs, generated with Hypothesis.
- **(f)** The same suite in GitHub Actions on Ubuntu, with R and Bioconductor installed from scratch.

Experiments 1 to 5 get a preregistration file committed before any run. Experiment 2 compares Figure 1 B to E qualitatively, because section 3 row 8 shows the figure is not the vignette's run. Experiment 3 runs `claude -p` with a fixed model under the user's subscription; if headless runs can't be made to work, the protocol is written for manual runs.

## 9. Decisions needed from Enrico

1. **Interface:** on 2026-11-10 Enrico asked for a website first, so C is built (section 7.1). Still open: D plus C as recommended in section 7, or another choice.
2. **Significance default:** `alternative = "greater"` in `test_significance` instead of sigscores' two-sided default.
3. **GSVA guard:** refuse the four GSVA-based scores when the matrix has constant or NA genes, until the user runs `prepare_matrix`.
4. **Claude Desktop registration:** may I add Sigshell to `~/Library/Application Support/Claude/claude_desktop_config.json` and restart Claude Desktop to measure which MCP revision it speaks? Until then, only MCP Inspector is used.
