# CLAUDE.md

Context for Claude Code in this repo. Project overview: @README.md

## Who and what

Sigshell is a natural-language shell for biologists over the sigscores R package. It's a Software Engineering course project by Enrico Adamo (Python side) and Marco Riva (R side).

## Current phase: the user interface

- Phase 1 (verifying sigscores) and Phase 2 (the MCP server in `src/sigshell/`) are done. `DESIGN.md` records both.
- Phase 3 is the interface. On 10 Nov Enrico asked for a local web page first (option C in `DESIGN.md` section 7). The page is `src/sigshell/web.py`, started with `uv run sigshell-ui`. It runs the MCP tools through `server.call_tool`, so put new behaviour in the tools, not in the page. The other decisions in `DESIGN.md` section 9 are still open: don't act on them without asking.
- The design is in `DESIGN.md`. Read it before changing the server, and keep it up to date when the design changes.

## The library

- Location: `../sigscores`, a clone of <https://github.com/alebarberis/sigscores> checked out at `40f55c5` (`main`, 29 Jun 2025). The package website was built from this commit. If the folder is missing or at another commit, say so before analysing anything.
- **Read-only.** Never edit, reformat or commit anything in `../sigscores`. If you find a bug, describe it so we can report it upstream.
- Facts checked in the raw source on 9 Nov:
  - 9 files in `R/`, layered by the `Collate` order in DESCRIPTION:
    - 0 utilities, 1 logging, 2 parallel, 3 statistics, 4 preprocessing
    - 5 scorers, 6 `computeSigScores`
    - 7 significance, 8 plots
  - 74 exported functions in `NAMESPACE`.
  - The vignette (`vignettes/sigscores.Rmd`) calls 9 exports: `computeSigScores`, `getAvailableScores`, `getScorer`, `getAvailableDataTransformers`, `getDataTransformer`, `createLogger`, `boxplotSigScores`, `heatmapSigScores`, `heatmapCorSigScores`.
  - `computeSignificance` is exported but not used in the vignette. It was refactored and exported in June 2025.
  - The only upstream test file is `tests/testthat/test-5-scorers.R`.
  - Licence: GPL-3 (declared in DESCRIPTION; there is no LICENSE file).
  - Other branches are `develop` (behind `main`), `master` (2022, diverged) and `legacy-0.0.0.9000`. Use `main` at `40f55c5` only.

## How to help us analyse it

We want to understand the library ourselves, not be handed a summary.

- Work from the outside in:
  1. DESCRIPTION and NAMESPACE
  2. the vignette source (`knitr::purl`)
  3. what calls what (`codetools::findGlobals`, `flow::flow_view`, `pkgnet::CreatePackageReport`)
  4. coverage (`covr::package_coverage`)
  5. one function at a time
- Base every claim about a function on the source: cite `R/<file>.R:<line>` and give the R call that would confirm it. If you haven't read it in the source or seen it in R output, say it's unverified.
- Take arguments and defaults from `formals()` and the code, not from the roxygen docs. Point out every place where the docs and the code disagree.
- When we study a function, help us write a prediction on a tiny input (a few genes × a few samples) **before** running it. Don't give the answer first unless we ask.
- Watch for behaviour that no argument controls: defaults inside the function body, defaults of dependencies such as GSVA, `options()`, behaviour that depends on the input's type, and randomness.

## Working rules

- Don't create files (notes, docs, scripts) unless asked. Keep the repo minimal.
- Every number Sigshell shows must come from sigscores, run by R. Each guard in `server.py` comes from a confirmed finding in `findings/`. Don't add a guard without a finding, and don't remove one without checking the finding again.
- Run the tests with `uv run --group dev pytest -q`.
- Don't commit, push or create branches unless asked. Branches are `enrico/<topic>` or `marco/<topic>`; `main` must always work; the other person reviews each pull request.
- Run R with `Rscript -e '...'`, or ask us to run it in RStudio. Check `R --version` and `packageVersion("sigscores")` instead of assuming them.
- sigscores is installed from the pinned source with `R CMD INSTALL ../sigscores`.
