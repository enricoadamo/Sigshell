# Sigshell

[![tests](https://github.com/enricoadamo/Sigshell/actions/workflows/tests.yml/badge.svg)](https://github.com/enricoadamo/Sigshell/actions/workflows/tests.yml)

Sigshell lets a biologist use the [sigscores](https://github.com/alebarberis/sigscores) R package without writing R. sigscores turns a gene signature into one score per sample, with 18 scoring methods (Barberis & Buffa 2026). With Sigshell you either click through a page in your browser, or ask Claude in plain language. Either way, every number is computed by sigscores in R on your own computer, and every session can be rerun as a plain R script, without Sigshell and without AI.

Software Engineering course project (20875, Fall 2026) by Enrico Adamo and Marco Riva.

## What's here

| Path | What it is |
|---|---|
| `src/sigshell/server.py` | The MCP server: 9 tools and 6 resources that an AI client such as Claude calls |
| `src/sigshell/web.py`, `web/` | The local page. It calls the same tools, so it has the same checks, and needs no AI |
| `src/sigshell/validate.py` | Input checks that run before any R code |
| `src/sigshell/rbridge.py`, `r/` | Each tool call becomes an R script, run in a fresh `Rscript` process |
| `findings/` | 41 confirmed findings about sigscores, `reproduce.R` for each, and 10 draft upstream issues |
| `callmap/` | An interactive map of sigscores' 138 functions and what calls what |
| `tests/` | The test suite (see below) |
| `examples/` | Example inputs, an example session, malformed inputs, screenshots |
| `DESIGN.md` | What we verified about sigscores, and the design |

## Setup

These steps are for macOS; Linux is the same apart from installing R. You need R, sigscores at one exact commit, and uv.

1. **R.** Install R 4.4 or later from <https://cran.r-project.org>. Then, in R:

   ```r
   install.packages(c("BiocManager", "data.table", "doParallel", "foreach", "matrixStats",
                      "ggplot2", "circlize", "psych", "jsonlite"))
   BiocManager::install(c("GSVA", "ComplexHeatmap"))
   ```

2. **sigscores at commit `40f55c5`.** Sigshell refuses to run with any other version, because its checks were written against this one. In Terminal, in the folder where you want both projects:

   ```sh
   git clone https://github.com/alebarberis/sigscores.git
   git -C sigscores checkout 40f55c5
   R CMD INSTALL sigscores
   ```

3. **uv and Sigshell.** Install uv from <https://docs.astral.sh/uv/>, then:

   ```sh
   git clone https://github.com/enricoadamo/Sigshell.git
   cd Sigshell
   uv sync
   ```

   Keep `sigscores` and `Sigshell` side by side. If sigscores is somewhere else, set `SIGSCORES_SRC` to its folder.

4. **Check.** `uv run sigshell-ui` opens the page. The line at the top says whether R and sigscores are ready, and if not, what is missing.

We developed with R 4.4.1, GSVA 2.0.7, matrixStats 1.5.0, ggplot2 3.5.1 and ComplexHeatmap 2.22.0 on macOS (arm64). The CI runs the same versions on Ubuntu 24.04.

## Use it in the browser

```sh
uv run sigshell-ui          # http://127.0.0.1:8787 (options: --port, --no-browser)
```

1. Add a matrix (`.csv`, `.tsv` or `.txt`: gene IDs in the first column, one column per sample) and a signature (one gene ID per line, optionally a weight after it). Or click **Try the example from the sigscores vignette**.
2. Say what scale the values are on. Sigshell records this and warns about raw counts. It never changes your numbers.
3. Read the check. Problems such as missing or duplicated genes stop the analysis until you fix them. Dropping missing genes is an explicit choice.
4. Choose scores and compute. You get a table, a full-precision CSV and four plots drawn by sigscores.
5. Optionally, test significance against random gene sets. The ASL compares each sample with random sets of genes; it is not a test between groups of samples.
6. Download the session as a zip.

The page only listens on 127.0.0.1 and refuses requests from other sites. Your data stays on your computer.

## Use it by asking Claude

The MCP server runs on stdio, so any MCP client can start it.

- **Claude Code:** this repository's `.mcp.json` registers it. Run `claude` in the `Sigshell` folder and approve the `sigshell` server.
- **Claude Desktop:** add this to `~/Library/Application Support/Claude/claude_desktop_config.json`, with the full path from `which uv` and the path to this folder, and restart Claude Desktop:

  ```json
  {"mcpServers": {"sigshell": {"command": "/full/path/to/uv",
                               "args": ["--directory", "/full/path/to/Sigshell", "run", "sigshell-server"]}}}
  ```

Put your files in `~/Sigshell/data` and ask, for example: *"Check vignette-matrix.csv and vignette-signature.txt, then give me the mean and median score per sample."* The server tells Claude to check inputs first and to report only numbers that came from a tool. `examples/run_example.py` drives the same server with a fixed list of calls instead of a model; `examples/vignette-session/transcript.md` shows what a client receives.

## Rerun a session without Sigshell

Each session is a folder in `~/Sigshell/sessions/` (or the zip from the page):

```
calls.jsonl        every tool call, its arguments, duration and outcome
steps/NNN-*.R      the R code of each step
inputs/            copies of the input files
outputs/           tables (CSV, RDS) and plots (PNG)
session.R          all steps in order
provenance.json    sigscores commit, R and package versions
```

`Rscript session.R`, run inside that folder, repeats the whole analysis with sigscores alone. The CI checks that it rewrites every table byte for byte.

## Tests

```sh
uv run --group dev pytest -q
```

| Folder | What it checks | Needs R |
|---|---|---|
| `tests/e_properties` | The input checks, on awkward inputs | no |
| `tests/web` | The page: host and header checks, uploads, paths; and that the example gives the published vignette scores | partly |
| `tests/d_recorded_runs` | 184 recorded calls of sigscores functions, replayed in fresh R processes, must print the same output, warnings and errors | yes |
| `tests/findings` | Each of the 41 findings is still reproduced by `findings/reproduce.R` | yes |

Tests that need R are skipped when R or the pinned sigscores is missing. The [GitHub Actions workflow](.github/workflows/tests.yml) installs everything from scratch on Ubuntu and runs all of them, then runs the example through the MCP server and replays its `session.R`.

## Findings about sigscores

While building Sigshell we found 41 behaviours of sigscores worth knowing about, from documentation that disagrees with the code to bugs that give wrong numbers without any warning. They are listed in [`findings/FINDINGS.md`](findings/FINDINGS.md), each with a minimal reproduction. When a check exists because of a finding, its message names the finding. Draft issues for the sigscores authors are in `findings/upstream/`; none has been filed yet.

## Licence and credits

Sigshell is licensed under the GNU GPL, version 3 or later ([`LICENSE`](LICENSE)).

sigscores is © Alessandro Barberis, GPL-3: <https://github.com/alebarberis/sigscores>. The call map and the test fixtures quote its source and its vignette. The paper in `resources/` is open access under CC BY 4.0:

> Barberis A, Buffa FM. Sigscores: summary scores for molecular signatures in R. *Bioinformatics Advances* 2026;6(1):vbag021. <https://doi.org/10.1093/bioadv/vbag021>

## Working together

`main` must always work. Work on a branch named `enrico/<topic>` or `marco/<topic>` and open a pull request; the other person reviews and merges it.
