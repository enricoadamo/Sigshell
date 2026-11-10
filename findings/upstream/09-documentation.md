<!-- Draft upstream issue for alebarberis/sigscores. Not filed. Sigshell findings: docs-random, docs-step, docs-transform-sub, docs-generic, docs-char-i, samplers-none, outdir-filename, resampling-null. -->
# Documentation that disagrees with the code

- `computeSigScores` `@return` mentions `sampling = "random"` (`R/6-compute-scores.R:49`), which is not an allowed value.
- `stepFunction` documents `y[1]` for x above the threshold (`R/3-stats-functions.R:1830`); the code uses `y[1]` below it (`:1911`).
- `transform.sub` is documented for all scorers (`R/5-scorers.R:35`) and read by none.
- `?getScorers` describes a `genericScorer` that calls `computeColMeasures`; neither path exists in the scorers.
- Scorers document character `i` (`R/5-scorers.R:13`); `sum`, `mean`, `median` and `mad` fail with gene names because `matrixStats` only accepts numeric rows.
- `getAvailableRandomSamplers()` omits `"none"` (`R/0-utility-functions.R:127-132`), the default of `computeSigScores`.
- `outdir` alone saves nothing: the check uses `missing(filename)` (`R/6-compute-scores.R:394`), so the documented default `"sigscores"` is never used, and the warning says it has no default.
- The paper (section 2.2) presents permutation and bootstrap as measuring score stability; because rows keep their names restored (`R/6-compute-scores.R:309-311`), both are random-gene-set nulls like `rndsig`.

## Reproduction

```r
library(sigscores)  # installed from alebarberis/sigscores at 40f55c5
x <- matrix(c(2, 4, 6, 8, 10,
              1, 3, 5, 9, 11,
              7, 7, 2, 4, 12),
            nrow = 5, dimnames = list(paste0("g", 1:5), paste0("S", 1:3)))
sig <- c("g1", "g3", "g4", "g5")
stepFunction(c(1, 5, 9), thr = 5, y = c(10, 20, 30))   # 10 20 30
meanScorer(x, i = c("g1", "g2"))                          # error
getAvailableRandomSamplers()$id                           # no "none"
d <- file.path(tempdir(), "out"); r <- computeSigScores(x, i = sig, scores = "mean", outdir = d); list.files(d)  # empty
```

## What happens

As listed above.

## Expected

Align the documentation with the code, or the code with the documentation.

## Evidence from `Rscript findings/reproduce.R <id>` in the Sigshell repo

- `docs-random`: sampling='random': error | doc line 49: #'If \code{sampling = "random"}, \code{sampling = "bootstrap"},
- `docs-step`: x=1,5,9 thr=5 -> 10,20,30 | doc line 1830: #'y_{1}, \quad \textrm{if} \quad x > threshold \\
- `docs-transform-sub`: scorers whose body reads transform.sub: 0 of 18
- `docs-generic`: Rd mentions genericScorer: TRUE | function exists: FALSE | scorers calling computeColMeasures: 0
- `docs-char-i`: error with gene names: sum,mean,median,mad
- `samplers-none`: listed: permutation,bootstrap,rndsig,rndsigsub | computeSigScores default: none
- `outdir-filename`: outdir only -> files: 0 | warning: Output directory was provided but 'filename' is missing without default. Data won't be saved. | with filename given: sigscores.rds
- `resampling-null`: permutation and rndsig score the same 10 gene pairs, max frequency difference 0.011 | bootstrap also scores pairs with a repeated gene: TRUE | lines 6-compute-scores.R:309-311: x = x[rnd[[iloop]],,drop=F] rownames(x) = rnames

Environment: sigscores 0.1.0 at commit 40f55c5, R 4.4.1 on aarch64-apple-darwin20, GSVA 2.0.7, matrixStats 1.5.0.
