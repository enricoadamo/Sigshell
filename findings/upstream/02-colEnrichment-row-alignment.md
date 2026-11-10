<!-- Draft upstream issue for alebarberis/sigscores. Not filed. Sigshell findings: gsva-constant-gene, gsva-na-row. -->
# GSVA-based scores use the wrong genes when the matrix has constant genes or rows with NA

`colEnrichment` removes rows from `x` but updates the signature positions `rows` with indices meant for `x`:

- constant genes: `rows = rows[keep]` (`R/3-stats-functions.R:1669`) indexes the signature with a logical vector of one value per *matrix row*;
- NA rows: `rows = rows[-rmv]` (`:1659`) removes signature elements at the positions of removed *matrix rows*.

In both cases the remaining numbers then point into the shortened matrix, so `rownames(x)[rows]` (`:1691`) names different genes. All four scores (`ssgsea`, `gsva`, `plage`, `zscore`) are affected. Constant genes (for example all-zero counts) are common in real expression data.

## Reproduction

```r
library(sigscores)  # installed from alebarberis/sigscores at 40f55c5
x <- matrix(c(2, 4, 6, 8, 10,
              1, 3, 5, 9, 11,
              7, 7, 2, 4, 12),
            nrow = 5, dimnames = list(paste0("g", 1:5), paste0("S", 1:3)))
sig <- c("g1", "g3", "g4", "g5")
ref <- GSVA::gsva(GSVA::gsvaParam(x, list(gs1 = sig)), verbose = FALSE)
computeSigScores(x, i = sig, scores = "gsva")$gsva                          # equals ref
computeSigScores(rbind(gC = c(5, 5, 5), x), i = sig, scores = "gsva")$gsva   # differs, same genes

y <- x; y[2, 1] <- NA   # g2 is not in the signature
computeSigScores(y, i = sig, scores = "zscore")$zscore
as.numeric(GSVA::gsva(GSVA::zscoreParam(y[-2, ], list(gs1 = sig)), verbose = FALSE))
```

## What happens

Without the constant gene: gsva 0.333, 1, 0 (equal to calling GSVA directly). With it: -0.333, 0.833, -0.75, and GSVA reports "Duplicated gene IDs removed from gene set gs1". With the NA row: zscore -1.000, -0.513, 1.514 against -0.118, 0.175, -0.057 from GSVA directly on the same genes.

## Expected

Work with gene names throughout: convert `rows` to `rownames(x)[rows]` before removing any rows, then filter with `intersect(geneset, rownames(x))`.

## Evidence from `Rscript findings/reproduce.R <id>` in the Sigshell repo

- `gsva-constant-gene`: without constant gene all 4 equal direct GSVA: TRUE | with it, differ from direct GSVA: gsva,ssgsea,plage,zscore
- `gsva-na-row`: package: -1.0004 -0.5133 1.5137 | direct on g1,g3,g4,g5: -0.1181 0.1752 -0.0571 | via computeSigScores: -1.0004 -0.5133 1.5137

Environment: sigscores 0.1.0 at commit 40f55c5, R 4.4.1 on aarch64-apple-darwin20, GSVA 2.0.7, matrixStats 1.5.0.
