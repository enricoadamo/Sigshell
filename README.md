# Sigshell

Sigshell is a **local web app** for scoring gene signatures with the existing
[`sigscores`](https://github.com/alebarberis/sigscores) R package. A researcher
uploads a gene expression matrix and a signature, checks the input report,
chooses scoring methods, inspects the results, and downloads a replayable R
script. The scientific calculations run in the unmodified R package. The web
page needs no AI client or account.

Software Engineering project by Enrico Adamo and Marco Riva.

## Requirements and installation

Use macOS or Linux with Python 3.12 or newer, [uv](https://docs.astral.sh/uv/),
Git, and R 4.4 or newer. The first installation needs internet access. Sigshell
checks that the installed R package matches the clean `sigscores` source at
commit `40f55c5cd1ab03153be40fa25e37723fdd64bacc`.

Put the two repositories side by side. From their parent directory:

```sh
git clone https://github.com/alebarberis/sigscores.git sigscores
git -C sigscores checkout --detach 40f55c5cd1ab03153be40fa25e37723fdd64bacc
```

Install the R dependencies and the pinned package:

```sh
Rscript -e 'install.packages(c("BiocManager", "data.table", "doParallel", "foreach", "matrixStats", "ggplot2", "circlize", "psych", "jsonlite"), repos="https://cloud.r-project.org"); BiocManager::install(c("GSVA", "ComplexHeatmap"), ask=FALSE, update=FALSE)'
R CMD INSTALL sigscores
```

From the `Sigshell` directory, start the page:

```sh
uv sync --frozen
uv run sigshell-ui
```

Open the localhost address printed in the terminal, normally
<http://127.0.0.1:8787>. Keep the terminal open while using the page. If the
`sigscores` checkout is elsewhere, set `SIGSCORES_SRC` to its absolute path
before starting Sigshell. Input files and sessions are stored under
`~/Sigshell` by default; set `SIGSHELL_HOME` to change that location.

## First analysis

1. Click **Try the example from the sigscores vignette**, or upload a `.csv`,
   `.tsv`, or `.txt` matrix and a signature. Matrix rows are genes, columns are
   samples, and the first column contains gene IDs. The signature has one gene
   ID per line, optionally followed by a weight.
2. Declare the expression scale and read the input report. Sigshell records
   this scale; it does not normalize the matrix automatically.
3. Choose **Recommended start: mean + median**, compute, and inspect the table
   and plots. In the synthetic example, sample S1 has mean **666.55** and
   median **736.5**.
4. Open **Reproduce** to view `session.R` or download the session ZIP. Run
   `Rscript session.R` from inside the extracted session to repeat the analysis
   with the same R package.

The example is synthetic and has no biological interpretation. Significance
tests compare a sample's score with a chosen random-gene null; they do not
compare clinical groups.

## Code and checks

`src/sigshell/web.py` serves the page and `src/sigshell/web/` holds its HTML,
CSS, and JavaScript. Python validates inputs, launches a fresh R process for
each analysis, and records the inputs, outputs, versions, and R script. The web
page currently uses the MCP Python SDK **internally** to dispatch analysis
calls; this release exposes only the web app. No MCP client is needed.

Run the focused web and validator tests with:

```sh
uv run --group dev pytest -q
```

The R-backed example test runs when the pinned `sigscores` installation is
available. The [one-page report](report.pdf) explains the engineering choices.
A short video demonstration will accompany the course submission separately.

## Licence and citation

Sigshell is licensed under GPL-3.0-or-later; see [LICENSE](LICENSE).
`sigscores` is a separate GPL-3 R package by Alessandro Barberis. If you
publish results, cite Barberis A and Buffa FM, *Bioinformatics Advances*
(2026), DOI: [10.1093/bioadv/vbag021](https://doi.org/10.1093/bioadv/vbag021).
