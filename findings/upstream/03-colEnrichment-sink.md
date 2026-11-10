<!-- Draft upstream issue for alebarberis/sigscores. Not filed. Sigshell findings: gsva-sink. -->
# A GSVA error leaves R's output switched off for the rest of the session

`colEnrichment` calls `sink(nullfile())` before `GSVA::gsva` and `sink()` after it (`R/3-stats-functions.R:1710`, `:1714`) with no `on.exit`. If GSVA errors, `computeScores` catches the error (`R/5-scorers.R:1196-1210`), the second `sink()` never runs, and everything printed afterwards in that R session goes to the null device.

## Reproduction

```r
library(sigscores)  # installed from alebarberis/sigscores at 40f55c5
x <- matrix(c(2, 4, 6, 8, 10,
              1, 3, 5, 9, 11,
              7, 7, 2, 4, 12),
            nrow = 5, dimnames = list(paste0("g", 1:5), paste0("S", 1:3)))
sig <- c("g1", "g3", "g4", "g5")
r <- computeSigScores(x, i = sig, scores = c("mean", "zscore"), args = list(zscore = list(minSize = 10)))
message("sinks open: ", sink.number())   # 1: stdout is still diverted (message() writes to stderr)
print("hello")                            # prints nothing
sink()                                    # restores output
```

## What happens

`sink.number()` is 1 after the call (the print of it is itself swallowed, so `message()` is used); the zscore column is NA; nothing printed afterwards appears.

## Expected

Register `on.exit(sink(), add = TRUE)` immediately after `sink(nullfile())`, or use `utils::capture.output`.

## Evidence from `Rscript findings/reproduce.R <id>` in the Sigshell repo

- `gsva-sink`: sink depth before 0 after 1 | zscore column all NA: TRUE | line 1710: sink(nullfile())

Environment: sigscores 0.1.0 at commit 40f55c5, R 4.4.1 on aarch64-apple-darwin20, GSVA 2.0.7, matrixStats 1.5.0.
