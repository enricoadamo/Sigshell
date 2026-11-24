# Sigshell

A natural-language shell for biologists over the [sigscores](https://github.com/alebarberis/sigscores) R package.
Software Engineering course project by Enrico Adamo and Marco Riva.

## The library we wrap

- Upstream: <https://github.com/alebarberis/sigscores> (GPL-3)
- We analyse and wrap commit [`40f55c5`](https://github.com/alebarberis/sigscores/commit/40f55c5cd1ab03153be40fa25e37723fdd64bacc) (`main`, 29 Jun 2025). The [package website](https://alebarberis.github.io/sigscores) was built from this exact commit, so the code matches its documented examples.

```sh
git clone https://github.com/alebarberis/sigscores.git
cd sigscores
git checkout 40f55c5
```

We never edit sigscores itself. If we find a bug, we report it upstream.

## Working together

- `main` must always work. Work on a branch named `enrico/<topic>` or `marco/<topic>`.
- Open a pull request; the other person reviews and merges it.
- Run `git pull` before you start.

## Licence

sigscores is GPL-3. This repo stays private until we choose sigshell's own licence.

## Status

The MCP server is in `src/sigshell/` (Phases 1 and 2 of `DESIGN.md`). The first user interface is a web page that runs on your own computer (`src/sigshell/web.py`). `uv run sigshell-ui` opens it in the browser. It runs the same tools as the MCP server and works without AI. The setup guide for biologists is still to be written.

For developers, with R, sigscores (installed from `../sigscores` at commit `40f55c5`) and uv:

```sh
uv sync
uv run sigshell-server          # MCP server on stdio
uv run sigshell-ui              # web page on http://127.0.0.1:8787 (--port, --no-browser)
uv run --group dev pytest -q    # tests
npx @modelcontextprotocol/inspector --cli uv run sigshell-server --method tools/list
```

Inputs go in `~/Sigshell/data`; each session is written to `~/Sigshell/sessions/<time>/` with a `session.R` that replays it without AI. Known issues in sigscores are in `findings/FINDINGS.md`.

## Use the local workbench

1. Open `sigshell-ui` and upload a matrix (`.csv`, `.tsv`, or `.txt`) with gene IDs in the first column and samples in the remaining columns. Upload a signature with one gene ID per line and optional numeric weights in a second column.
2. Declare the matrix's expression scale. This label is recorded, not used to normalize or transform the data. Normalize raw counts before interpreting differences across samples.
3. Review the input report. Missing signature genes block scoring unless you explicitly choose to drop them; the choice resets when either input changes.
4. Select scores, compute, inspect the table and plots, and download the full precision CSV. Methods have different units and ranges, so the raw heatmap colors should only be interpreted within a method.
5. Optionally compare each observed score with random gene sets. The ASL concerns the chosen null within each sample; it is not a test of differences between sample groups.
6. Download the session ZIP. It includes the staged inputs, outputs, `session.R`, and `provenance.json` with R and package versions. Run `Rscript session.R` from the unzipped session folder to replay it.
