<!-- Draft upstream issue for alebarberis/sigscores. Not filed. Sigshell findings: setters, logall, logger-con. -->
# Logger setters and `logAll` don't do what their names say

- `setVerbose`, `setPath` and `setLevel` all assign `object$con` (`R/1-log-functions.R:141-145`).
- `logAll` logs at level `ALL`, which `getLogLevels` never enables (`:163`), so it never prints.
- An open connection passed to `createLogger(con = )` is replaced by `openCon` (`R/0-utility-functions.R:966-970`), so nothing is written to it.

None of the three is reachable from an exported function except the last.

## Reproduction

```r
library(sigscores)
str(unclass(sigscores:::setVerbose(createLogger(), FALSE)))   # con = FALSE, verbose still TRUE
out <- character(); tc <- textConnection("out", "w")
x <- matrix(1:6, nrow = 3, dimnames = list(c("g1", "g2", "g3"), c("S1", "S2")))
r <- computeSigScores(x, scores = "mean", logger = createLogger(con = tc, verbose = FALSE))
close(tc); out   # character(0)
```

## What happens

As listed above.

## Expected

Assign the intended fields; keep a supplied open connection in `openCon`.

## Evidence from `Rscript findings/reproduce.R <id>` in the Sigshell repo

- `setters`: after setVerbose(FALSE): verbose = TRUE , con = FALSE | after setLevel('DEBUG'): level = INFO
- `logall`: logAll printed lines: 0 | logInfo printed lines: 1
- `logger-con`: lines written to given connection: 0 | lines written when path given: 1

Environment: sigscores 0.1.0 at commit 40f55c5, R 4.4.1 on aarch64-apple-darwin20, GSVA 2.0.7, matrixStats 1.5.0.
