<!-- Draft upstream issue for alebarberis/sigscores. Not filed. Sigshell findings: silent-na, df-input, typo-score, unknown-gene, dup-signature-gene, rndsig-size. -->
# Several input mistakes give a result instead of an error

These are design choices rather than coding errors, but each produces numbers without telling the user anything went wrong:

- any scorer error becomes NA for every sample (`R/5-scorers.R:1196-1210`), with the message discarded;
- a data frame is converted to a one-column list matrix (`:1125-1126`), every scorer then fails, and the result is one row of NA;
- unknown score ids are dropped by `intersect` (`:1139`);
- unknown genes become NA row numbers (`:1174`) and are ignored under the default `na.rm = TRUE`;
- a gene listed twice in `i` is scored twice (`:1174`);
- random signatures have `length(i)` genes, including genes not in `x` (`R/0-utility-functions.R:818`), so they are larger than the scored signature.

## Reproduction

```r
library(sigscores)  # installed from alebarberis/sigscores at 40f55c5
x <- matrix(c(2, 4, 6, 8, 10,
              1, 3, 5, 9, 11,
              7, 7, 2, 4, 12),
            nrow = 5, dimnames = list(paste0("g", 1:5), paste0("S", 1:3)))
sig <- c("g1", "g3", "g4", "g5")
computeSigScores(x, scorers = list(bad = function(...) stop("boom")))   # NA, no message
computeSigScores(as.data.frame(x), i = c("g1", "g3"), scores = "mean")  # one row: S1, NA
computeSigScores(x, i = c("g1", "g3"), scores = c("mean", "meen"))     # meen dropped silently
computeSigScores(x, i = c("g1", "g3", "gX"), scores = "mean")          # gX ignored silently
computeSigScores(x, i = c("g1", "g1", "g3"), scores = "mean")          # g1 counted twice
lengths(randomSignatures(x, i = c("g1", "gX"), n = 1, exclude = FALSE)) # 2 genes
```

## What happens

No warning or error in any of the six calls.

## Expected

Warn (or error) on unknown score ids, unknown or duplicated genes and non-matrix input, and keep scorer error messages (for example as an attribute, or with `warning()` in the handler).

## Evidence from `Rscript findings/reproduce.R <id>` in the Sigshell repo

- `silent-na`: all NA: TRUE | warnings: 0 | messages: 0
- `df-input`: rows: 1 | mean: NA | warnings: 0
- `typo-score`: columns: sampleID,mean | warnings: 0 | all ids wrong: error
- `unknown-gene`: same as without gX: TRUE | warnings: 0 | na.rm=FALSE all NA: TRUE
- `dup-signature-gene`: mean of g1,g3: 4 3 4.5 | with g1 listed twice: 3.3333 2.3333 5.3333 | R/5-scorers.R:1174: i = match(table = rownames(x), x = i)
- `rndsig-size`: signature with 1 known + 1 unknown gene -> random set size 2

Environment: sigscores 0.1.0 at commit 40f55c5, R 4.4.1 on aarch64-apple-darwin20, GSVA 2.0.7, matrixStats 1.5.0.
