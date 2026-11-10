<!-- Draft upstream issue for alebarberis/sigscores. Not filed. Sigshell findings: z-cols, z-robust. -->
# `zStandardisation` is wrong for `by = "cols"` and for `robust = TRUE`

In `zStandardisationForMatrix`:

- `by = "cols"`: `sweep(x, 2, center, "-") / scale` (`R/4-data-preprocessing.R:683`) divides a matrix by a per-column vector; R recycles it down the rows, so each column is divided by a mix of scales.
- `robust = TRUE`: the robust branches standardise (`:659`, `:675`) and the shared line after them (`:667`, `:683`) standardises again.

## Reproduction

```r
library(sigscores)  # installed from alebarberis/sigscores at 40f55c5
x <- matrix(c(2, 4, 6, 8, 10,
              1, 3, 5, 9, 11,
              7, 7, 2, 4, 12),
            nrow = 5, dimnames = list(paste0("g", 1:5), paste0("S", 1:3)))
sig <- c("g1", "g3", "g4", "g5")
round(zStandardisation(x, by = "cols") - scale(x), 3)            # not zero
ctr <- matrixStats::rowMedians(x); s <- matrixStats::rowMads(x, center = ctr)
round(zStandardisation(x, robust = TRUE, by = "rows") - (x - ctr) / s, 3)   # not zero
round(zStandardisation(x, robust = TRUE, by = "rows") - ((x - ctr) / s - ctr) / s, 3)  # zero: applied twice
```

## What happens

Largest difference from `scale(x)` by columns: 0.391. The robust result equals the robust standardisation applied twice.

## Expected

Use `sweep(sweep(x, 2, center, "-"), 2, scale, "/")`, and remove the inner standardisation lines in the robust branches.

## Evidence from `Rscript findings/reproduce.R <id>` in the Sigshell repo

- `z-cols`: max |pkg - scale(x)| by cols: 0.391 | by rows vs t(scale(t(x))): 0
- `z-robust`: equals single standardisation: FALSE | equals applying it twice: TRUE

Environment: sigscores 0.1.0 at commit 40f55c5, R 4.4.1 on aarch64-apple-darwin20, GSVA 2.0.7, matrixStats 1.5.0.
