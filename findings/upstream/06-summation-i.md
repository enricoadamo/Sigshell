<!-- Draft upstream issue for alebarberis/sigscores. Not filed. Sigshell findings: summation-i. -->
# `summation()` errors whenever `i` is given

`summation` subsets `w` (`R/3-stats-functions.R:176`), which is not an argument or a local variable of that function.

## Reproduction

```r
library(sigscores)
summation(c(g1 = 2, g2 = 4, g3 = 6), i = 1:2)
```

## What happens

`Error: object 'w' not found`.

## Expected

Delete line 176.

## Evidence from `Rscript findings/reproduce.R <id>` in the Sigshell repo

- `summation-i`: result: object 'w' not found

Environment: sigscores 0.1.0 at commit 40f55c5, R 4.4.1 on aarch64-apple-darwin20, GSVA 2.0.7, matrixStats 1.5.0.
