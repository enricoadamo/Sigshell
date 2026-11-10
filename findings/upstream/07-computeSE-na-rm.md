<!-- Draft upstream issue for alebarberis/sigscores. Not filed. Sigshell findings: computeSE-na. -->
# `computeSE(na.rm = TRUE)` still returns NA

`na.rm` is passed only to `mean` (`R/7-significance.R:173`); the sum of squares (`:181`) and `n` (`:176`) still include the NA. This propagates to `computeSignificance(type = "se")` and to standard confidence intervals.

## Reproduction

```r
library(sigscores)
sigscores:::computeSE(c(1, 2, NA), na.rm = TRUE)
```

## What happens

NA, where `sd(c(1, 2))` is 0.707.

## Expected

Drop NA from `rnd` first when `na.rm = TRUE`.

## Evidence from `Rscript findings/reproduce.R <id>` in the Sigshell repo

- `computeSE-na`: computeSE(c(1,2,NA), na.rm=TRUE) = NA | sd(c(1,2)) = 0.7071

Environment: sigscores 0.1.0 at commit 40f55c5, R 4.4.1 on aarch64-apple-darwin20, GSVA 2.0.7, matrixStats 1.5.0.
