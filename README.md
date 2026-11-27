# Sigshell

Sigshell is a **local web app** for scoring gene signatures with the existing
[`sigscores`](https://github.com/alebarberis/sigscores) R package. A researcher
uploads a gene expression matrix and a signature, checks the input report,
chooses scoring methods, inspects the results, and downloads a replayable R
script. The scientific calculations run in the unmodified R package. The web
page needs no AI client or account.

Software Engineering project by Enrico Adamo and Marco Riva.

**Video presentation:** [Watch the Sigshell demo on Google Drive](https://drive.google.com/file/d/1hUFc5M0SS9gC6_y2PmTo9pnkLJcxHFCU/view?usp=sharing).

## Install prerequisites

Sigshell runs on macOS or Linux. Install [Git](https://git-scm.com/downloads/),
[R 4.4 or newer](https://cran.r-project.org/), and
[uv](https://docs.astral.sh/uv/getting-started/installation/) using the linked
instructions. We tested with R 4.4.1. The first setup needs internet access.
Open a **new terminal** after installing them and check:

```sh
git --version
R --version
Rscript --version
uv --version
```

Each command should print a version. If a command says it was not found, finish
installing that program and open a new terminal. Sigshell also needs Python
3.12 or newer. uv can install a compatible version for you:

```sh
uv python install 3.13
```

If Python is already installed, `python3 --version` shows its version; the uv
command above is still safe to run.

## Quick start

The commands below create `~/sigshell-work` and put **both** repositories in
it. Run them in order in a terminal. The `sigscores` checkout must stay at the
specified commit because Sigshell checks its code against the installed R
package. Git may say `detached HEAD` after the checkout command; that is
expected here.

```sh
mkdir -p ~/sigshell-work
cd ~/sigshell-work
git clone https://github.com/alebarberis/sigscores.git sigscores
git -C sigscores checkout --detach 40f55c5cd1ab03153be40fa25e37723fdd64bacc
git clone https://github.com/enricoadamo/Sigshell.git Sigshell
```

Install the R packages. These two `Rscript` commands can take several minutes
on the first run:

```sh
Rscript -e 'install.packages(
  c("BiocManager", "data.table", "doParallel", "foreach",
    "matrixStats", "ggplot2", "circlize", "psych", "jsonlite"),
  repos = "https://cloud.r-project.org"
)'
Rscript -e 'BiocManager::install(
  c("GSVA", "ComplexHeatmap"),
  ask = FALSE, update = FALSE
)'
R CMD INSTALL sigscores
```

Start the web app:

```sh
cd Sigshell
uv sync --python 3.13 --frozen
uv run sigshell-ui
```

Open the localhost address printed in the terminal, normally
<http://127.0.0.1:8787>. The green **Ready** line should identify `sigscores`
commit `40f55c5` and the R version. Keep this terminal open while using the
page. Input files and sessions are stored under `~/Sigshell` by default.

If you keep the `sigscores` checkout somewhere other than next to `Sigshell`,
set its absolute path **before** starting the app:

```sh
export SIGSCORES_SRC="/absolute/path/to/sigscores"
uv run sigshell-ui
```

To store Sigshell's data elsewhere, use the same pattern with
`export SIGSHELL_HOME="/absolute/path/to/my-data-folder"`.

### If the page does not say Ready

The page still opens and shows the reason it cannot score yet:

- **“Rscript was not found”**: install R, open a new terminal, and restart the
  app.
- **“The sigscores source was not found”**: check that `sigscores` and
  `Sigshell` are side by side, or set `SIGSCORES_SRC` as shown above.
- **“sigscores ... is at commit ...”**: return to `~/sigshell-work`, run the
  checkout command from Quick start again, then run `R CMD INSTALL sigscores`.
- **“The sigscores checkout ... has local changes”**: use an unmodified copy of
  the pinned source. If you need your edits, keep them in a separate checkout.
- **“The sigscores R package is not installed”** or **“differs from the pinned
  source”**: run `R CMD INSTALL sigscores` from `~/sigshell-work`, then restart
  Sigshell.

Press **Ctrl+C** in the app's terminal to stop it. On later days, you only need:

```sh
cd ~/sigshell-work/Sigshell
uv run sigshell-ui
```

If you used a custom `SIGSCORES_SRC` or `SIGSHELL_HOME`, export it again in the
new terminal before the last command.

## First analysis: no files to prepare

1. Click **Try the example from the sigscores vignette**. Sigshell writes
   `vignette-matrix.csv` and `vignette-signature.txt` into `~/Sigshell/data`
   and selects them for you. The input check should show **100 genes, 10
   samples, and 20 matching signature genes**.
2. Declare the expression scale, read the input report, and choose
   **Recommended start: mean + median**. Sigshell records the scale; it does
   not normalize the values automatically.
3. Compute and inspect the table and plots. Sample S1 should have mean
   **666.55** and median **736.5**.
4. Open **Reproduce** to view `session.R` or download the session ZIP. Run
   `Rscript session.R` from inside the extracted session to repeat the analysis
   with the same R package.

For your own data, upload a `.csv`, `.tsv`, or `.txt` expression matrix and a
signature. Matrix rows are genes, columns are samples, and the first column
contains gene IDs. The signature has one gene ID per line, optionally followed
by a weight.

The example is synthetic and has no biological interpretation. Significance
tests compare a sample's score with a chosen random-gene null; they do not
compare clinical groups.

Quantile normalisation is available for the summary methods, but is not offered
with the four GSVA-based methods: it can create constant rows after validation
and trigger a gene-alignment bug in the pinned package. Choose no transformation
to use those methods. The upstream package is unchanged.

Session exports retain every attempted R step and its status in `steps.json`.
The replay script includes only successfully completed steps, so a failed
attempt does not prevent later successful analyses from being reproduced.

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

## Licence and citation

Sigshell is licensed under GPL-3.0-or-later; see [LICENSE](LICENSE).
`sigscores` is a separate GPL-3 R package by Alessandro Barberis. If you
publish results, cite Barberis A and Buffa FM, *Bioinformatics Advances*
(2026), DOI: [10.1093/bioadv/vbag021](https://doi.org/10.1093/bioadv/vbag021).
