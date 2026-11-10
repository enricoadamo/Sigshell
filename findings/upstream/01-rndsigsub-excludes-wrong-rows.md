<!-- Draft upstream issue for alebarberis/sigscores. Not filed. Sigshell findings: rndsigsub-wrong-rows, pool-of-one. -->
# `sampling = "rndsigsub"` excludes the first rows of the matrix instead of the signature's genes

`randomSignatures(exclude = TRUE)` removes `getIndex(updateSig(x, i))` from the pool of row numbers (`R/0-utility-functions.R:832`). `updateSig` stores positions *within `i`* (`:397`, `:412`), not rows of `x`, so a signature of k genes removes rows 1..k. The signature's own genes stay in the pool. The roxygen example uses `rownames(x)[1:10]`, where the two coincide.

A second, smaller problem on the same line: when one row is left in the pool, `sample(x = out, ...)` (`:838`) treats that single number n as `1:n`.

## Reproduction

```r
library(sigscores)
y <- matrix(1:40, nrow = 20, dimnames = list(paste0("g", 1:20), c("S1", "S2")))
set.seed(1)
sort(unique(unlist(randomSignatures(y, i = c("g19", "g20"), n = 500, exclude = TRUE))))
# rows 3..20 are drawn: g19 and g20 (rows 19, 20) are included, rows 1 and 2 never are

y5 <- matrix(1:10, nrow = 5, dimnames = list(paste0("g", 1:5), c("S1", "S2")))
set.seed(1)
randomSignatures(y5, i = paste0("g", 1:4), n = 2, exclude = TRUE)
# pool is row 5 only, yet 4 rows are returned, including signature rows
```

## What happens

Rows 19 and 20 never drawn, rows 1 and 2 eligible. With a pool of one row, an error (the sample is larger than the population).

## Expected

Use the row numbers of the signature in `x`, for example `match(i, rownames(x))` for character `i`, and use `out[sample.int(length(out), size)]` instead of `sample(out, size)`.

## Evidence from `Rscript findings/reproduce.R <id>` in the Sigshell repo

- `rndsigsub-wrong-rows`: rows drawn: 3-20 | signature rows 19,20 drawn: TRUE | rows 1,2 drawn: FALSE
- `pool-of-one`: pool after exclusion: 5 | asked for 4 genes, got: 1,4,5,3

Environment: sigscores 0.1.0 at commit 40f55c5, R 4.4.1 on aarch64-apple-darwin20, GSVA 2.0.7, matrixStats 1.5.0.
