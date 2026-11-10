<!-- Draft upstream issue for alebarberis/sigscores. Not filed. Sigshell findings: quantile-na-rows. -->
# Quantile normalisation drops rows with NA, so scorers index the wrong rows

With `na.rm = TRUE` (the default), `quantileNormalizationForMatrix` removes rows containing NA with `stats::na.omit` (`R/4-data-preprocessing.R:230`). When it is used as `transform.fun`, scorers then apply the original row numbers to the shorter matrix (for example `rows = i` in `meanScorer`, `R/5-scorers.R:183-186`). The signature lands on other genes or out of range, and the error becomes NA through `computeScores`' `tryCatch`.

## Reproduction

```r
library(sigscores)  # installed from alebarberis/sigscores at 40f55c5
x <- matrix(c(2, 4, 6, 8, 10,
              1, 3, 5, 9, 11,
              7, 7, 2, 4, 12),
            nrow = 5, dimnames = list(paste0("g", 1:5), paste0("S", 1:3)))
sig <- c("g1", "g3", "g4", "g5")
y <- x; y[2, 1] <- NA
q <- getDataTransformer("quantile")
computeSigScores(y, i = c("g4", "g5"), scores = "mean", args = list(mean = list(transform.fun = q)))$mean
colMeans(q(y)[c("g4", "g5"), ])
```

## What happens

mean of g4, g5 is NA in all samples, with no warning; the transformed values give 9.5, 9.5, 8.

## Expected

Keep the rows (normalise column-wise ignoring NA), or have the transformer return a matrix with the same row names and let scorers subset by name.

## Evidence from `Rscript findings/reproduce.R <id>` in the Sigshell repo

- `quantile-na-rows`: after quantile normalisation the matrix has 4 rows (g2 dropped by R/4-data-preprocessing.R:230); mean of g4,g5: NA NA NA | correct values: 9.5 9.5 8 | warnings: 0

Environment: sigscores 0.1.0 at commit 40f55c5, R 4.4.1 on aarch64-apple-darwin20, GSVA 2.0.7, matrixStats 1.5.0.
