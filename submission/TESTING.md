# Verification record

Checked on 24 November 2026 from the `enrico/web-ui` code at `d24e15a`, plus
the two environment-aware test changes in this submission branch. The local
system was macOS arm64 with R 4.4.1, Python 3.13, and the installed sigscores
package checked against the pinned source commit `40f55c5`.

- Fresh Python environment: `uv sync --frozen --group dev` completed.
- Full local suite: **254 passed, 2 skipped** in 81 seconds. R reported
  `parallel::detectCores() = NA`, so sigscores took its documented sequential
  path. The skipped cases assert output that exists only on its parallel path.
- Synthetic vignette example: `uv run python examples/run_example.py <output>`
  completed. Replaying the exported `session.R` rewrote both tables with
  identical bytes.
- The one-page report PDF and seven-slide presentation PDF were opened and
  checked for page count and layout.

The R/Bioconductor dependencies were already installed on this machine. A
fresh installation of that stack must still be checked on a clean machine; the
GitHub Actions workflow is intended to perform that check on Ubuntu.
