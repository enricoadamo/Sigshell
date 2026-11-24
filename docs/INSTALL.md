# Install and verify Sigshell

This guide is separate from the short course report. Sigshell runs locally; the
browser page needs no account, cloud service, or AI key. The MCP server is
optional.

## Requirements

- macOS or Linux, Python 3.12 or newer, `uv`, Git, and R 4.4 or newer.
- Internet access for the first dependency installation.
- A clean checkout of `sigscores` at commit
  `40f55c5cd1ab03153be40fa25e37723fdd64bacc`, installed in R. Sigshell
  checks both the checkout and installed function bodies before running.

The tested environment was macOS arm64, R 4.4.1, sigscores 0.1.0, GSVA 2.0.7,
and Python 3.13. Other supported environments may need different Bioconductor
versions.

## Install

Place the `Sigshell` folder and the upstream checkout side by side:

```text
project/
  Sigshell/
  sigscores/
```

From `project/`, run:

```sh
git clone https://github.com/alebarberis/sigscores.git sigscores
git -C sigscores checkout --detach 40f55c5cd1ab03153be40fa25e37723fdd64bacc
```

Install the R dependencies, then the pinned package. The first command may take
some time because GSVA and ComplexHeatmap come from Bioconductor:

```sh
Rscript -e 'install.packages(c("BiocManager", "data.table", "doParallel", "foreach", "matrixStats", "ggplot2", "circlize", "psych", "jsonlite"), repos="https://cloud.r-project.org"); BiocManager::install(c("GSVA", "ComplexHeatmap"), ask=FALSE, update=FALSE)'
R CMD INSTALL sigscores
```

Then, from `project/Sigshell/`:

```sh
uv sync --frozen
uv run sigshell-ui
```

Open the localhost address printed in the terminal. The port is normally 8787;
if it is occupied, Sigshell prints a different free port. Keep the terminal
running while using the page. Press Ctrl-C to stop it.

If the upstream checkout is elsewhere, set `SIGSCORES_SRC` to its absolute path
before starting Sigshell. Set `SIGSHELL_HOME` to change where inputs and session
files are stored; its default is `~/Sigshell`.

## Smoke test

1. Confirm that the page says **Ready** and identifies sigscores commit
   `40f55c5`.
2. Click **Try the example from the sigscores vignette**. The input check should
   report 100 genes, 10 samples, and 20 matched signature genes.
3. Choose **Recommended start: mean + median** and compute. For sample S1,
   mean should be 666.55 and median 736.5. These values match the published
   vignette example.
4. Click **Boxplot**, then **Show the R script** in the Reproduce section.

For the automated suite, run `uv run --group dev pytest -q`. The suite checks
input validation, the web workflow, and the vignette values. The first-run
vignette check requires the installed R package.

## MCP client

`uv run sigshell-server` starts the stdio MCP server. The included `.mcp.json`
shows a project-local client configuration. Configure your own MCP client to
start this command in the `Sigshell` folder. The web page and MCP server share
the same analysis functions and local data folder.
