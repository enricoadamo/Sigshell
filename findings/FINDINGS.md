# Findings about sigscores

Bugs, behaviour no argument controls, and places where the paper, documentation and code disagree, found while building Sigshell against sigscores commit `40f55c5`.

All 41 were confirmed on 2026-11-10 (R 4.4.1, macOS arm64) by `Rscript findings/reproduce.R <id>`, run from this repository with `SIGSCORES_SRC` pointing at the pinned checkout. The data is in `findings/findings.json`; draft issues for the upstream repository are in `findings/upstream/` and have not been filed.

The reproductions use the tiny inputs from `findings/reproduce.R`: `x` is a 5 × 3 matrix (genes g1 to g5, samples S1 to S3), `sig <- c("g1", "g3", "g4", "g5")` and `v` is column S1 as a named vector.

| Severity | Kind | Finding | Where | Upstream draft |
|---|---|---|---|---|
| High | Bug | [A constant gene anywhere before the signature corrupts all four GSVA scores](#gsva-constant-gene) | `R/3-stats-functions.R:1669` | [02-colEnrichment-row-alignment.md](upstream/02-colEnrichment-row-alignment.md) |
| High | Bug | [A row with NA moves the GSVA gene set onto different genes](#gsva-na-row) | `R/3-stats-functions.R:1659` | [02-colEnrichment-row-alignment.md](upstream/02-colEnrichment-row-alignment.md) |
| High | Bug | [If GSVA fails, R's printed output stays switched off](#gsva-sink) | `R/3-stats-functions.R:1710` | [03-colEnrichment-sink.md](upstream/03-colEnrichment-sink.md) |
| High | Bug | [Quantile normalisation drops rows with NA, so scorers index the wrong rows](#quantile-na-rows) | `R/4-data-preprocessing.R:230` | [04-quantile-na-rows.md](upstream/04-quantile-na-rows.md) |
| High | Bug | [`rndsigsub` excludes the wrong genes](#rndsigsub-wrong-rows) | `R/0-utility-functions.R:832` | [01-rndsigsub-excludes-wrong-rows.md](upstream/01-rndsigsub-excludes-wrong-rows.md) |
| High | Bug | [`zStandardisation(by = "cols")` scales incorrectly](#z-cols) | `R/4-data-preprocessing.R:683` | [05-zStandardisation-matrix.md](upstream/05-zStandardisation-matrix.md) |
| High | Bug | [`robust = TRUE` standardises a matrix twice](#z-robust) | `R/4-data-preprocessing.R:667` | [05-zStandardisation-matrix.md](upstream/05-zStandardisation-matrix.md) |
| High | Hidden behaviour | [A data frame input gives a wrong result with no error](#df-input) | `R/5-scorers.R:1125` | [08-silent-failures.md](upstream/08-silent-failures.md) |
| High | Hidden behaviour | [A scorer that fails becomes a column of NA, with no message](#silent-na) | `R/5-scorers.R:1196` | [08-silent-failures.md](upstream/08-silent-failures.md) |
| High | Hidden behaviour | [Two scorers transform after subsetting; the other 16 transform first](#transform-order) | `R/5-scorers.R:217` |  |
| Medium | Bug | [`computeSE(na.rm = TRUE)` still returns NA](#computeSE-na) | `R/7-significance.R:181` | [07-computeSE-na-rm.md](upstream/07-computeSE-na-rm.md) |
| Medium | Bug | [`summation` always errors when `i` is given](#summation-i) | `R/3-stats-functions.R:176` | [06-summation-i.md](upstream/06-summation-i.md) |
| Medium | Docs differ | [`outdir` alone saves nothing, despite `filename` having a default](#outdir-filename) | `R/6-compute-scores.R:394` | [09-documentation.md](upstream/09-documentation.md) |
| Medium | Docs differ | [Permutation and bootstrap are random-gene-set nulls, not a measure of score stability](#resampling-null) | `R/6-compute-scores.R:309` | [09-documentation.md](upstream/09-documentation.md) |
| Medium | Hidden behaviour | [The default two-sided p-value compares absolute values](#asl-abs) | `R/7-significance.R:131` |  |
| Medium | Hidden behaviour | [A gene listed twice in the signature is counted twice](#dup-signature-gene) | `R/5-scorers.R:1174` | [08-silent-failures.md](upstream/08-silent-failures.md) |
| Medium | Hidden behaviour | [An open connection given to `createLogger` is discarded](#logger-con) | `R/0-utility-functions.R:966` | [10-logger.md](upstream/10-logger.md) |
| Medium | Hidden behaviour | [With one sample, the GSVA scores are always NA](#one-sample) | `R/3-stats-functions.R:1666` |  |
| Medium | Hidden behaviour | [Random signatures count genes that aren't in the matrix](#rndsig-size) | `R/0-utility-functions.R:818` | [08-silent-failures.md](upstream/08-silent-failures.md) |
| Medium | Hidden behaviour | [A misspelled score id is dropped with no warning](#typo-score) | `R/5-scorers.R:1139` | [08-silent-failures.md](upstream/08-silent-failures.md) |
| Medium | Hidden behaviour | [An unknown gene becomes an NA row number and disappears under the default `na.rm`](#unknown-gene) | `R/5-scorers.R:1174` | [08-silent-failures.md](upstream/08-silent-failures.md) |
| Medium | Hidden behaviour | [The exported `gsva`, `ssgsea`, `plage` and `zscore` always return NA](#vector-stubs) | `R/3-stats-functions.R:813` |  |
| Low | Bug | [`logAll` never prints](#logall) | `R/1-log-functions.R:163` | [10-logger.md](upstream/10-logger.md) |
| Low | Bug | [A pool of one gene is treated as `1:n`](#pool-of-one) | `R/0-utility-functions.R:838` | [01-rndsigsub-excludes-wrong-rows.md](upstream/01-rndsigsub-excludes-wrong-rows.md) |
| Low | Bug | [Three setters overwrite the connection instead](#setters) | `R/1-log-functions.R:141` | [10-logger.md](upstream/10-logger.md) |
| Low | Docs differ | [Four scorers reject gene names in `i` when called directly](#docs-char-i) | `R/5-scorers.R:13` | [09-documentation.md](upstream/09-documentation.md) |
| Low | Docs differ | [The docs describe a `genericScorer` and `computeColMeasures` route that the scorers don't take](#docs-generic) | `man/getScorers.Rd` | [09-documentation.md](upstream/09-documentation.md) |
| Low | Docs differ | [The docs mention `sampling = "random"`, which doesn't exist](#docs-random) | `R/6-compute-scores.R:49` | [09-documentation.md](upstream/09-documentation.md) |
| Low | Docs differ | [The docs for `stepFunction` reverse `y`](#docs-step) | `R/3-stats-functions.R:1830` | [09-documentation.md](upstream/09-documentation.md) |
| Low | Docs differ | [`transform.sub` is documented but does nothing](#docs-transform-sub) | `R/5-scorers.R:35` | [09-documentation.md](upstream/09-documentation.md) |
| Low | Docs differ | [`getAvailableRandomSamplers` leaves out `none`](#samplers-none) | `R/0-utility-functions.R:127` | [09-documentation.md](upstream/09-documentation.md) |
| Low | Hidden behaviour | [Custom scorer names are rewritten](#custom-names) | `R/5-scorers.R:1234` |  |
| Low | Hidden behaviour | [Some numbers come from dependencies' defaults](#dep-defaults) | `R/3-stats-functions.R:748` |  |
| Low | Hidden behaviour | [`dirExists` creates the folder](#dirExists-creates) | `R/0-utility-functions.R:994` |  |
| Low | Hidden behaviour | [If two matrix rows share a gene name, only the first is scored](#dup-matrix-gene) | `R/5-scorers.R:1174` |  |
| Low | Hidden behaviour | [Duplicate sample names are an error](#dup-samples) | `R/5-scorers.R:1236` |  |
| Low | Hidden behaviour | [IQM is NA for fewer than 4 values](#iqm-small) | `R/3-stats-functions.R:674` |  |
| Low | Hidden behaviour | [Mode ties go to the smallest value](#modal-tie) | `R/3-stats-functions.R:407` |  |
| Low | Hidden behaviour | [On data without repeated values, mode is the minimum](#mode-is-min) | `R/3-stats-functions.R:407` |  |
| Low | Hidden behaviour | [There is no seed argument](#no-seed) | `R/0-utility-functions.R:729` |  |
| Low | Hidden behaviour | [`cores` above 1 prints foreach's debugging output](#parallel-verbose) | `R/2-parallel-functions.R:85` |  |

<a id="gsva-constant-gene"></a>
## A constant gene anywhere before the signature corrupts all four GSVA scores

`gsva-constant-gene` · High · Bug · `R/3-stats-functions.R:1669` · functions: `colEnrichment`, `gsvaScorer`, `ssgseaScorer`, `plageScorer`, `zscoreScorer`, `colGsva`, `colSsgsea`, `colPlage`, `colZscore` · first found in: call map (2026-11-09)

`rows = rows[keep]` indexes the signature with a logical vector of one value per gene in the matrix. The positions then point into a smaller matrix. A gene with the same value in every sample (an all-zero gene, for example) changes which genes are scored. This is common in real expression data.

```r
sig <- c("g1", "g3", "g4", "g5")
computeSigScores(x, i = sig, scores = "gsva")
computeSigScores(rbind(gC = c(5, 5, 5), x), i = sig, scores = "gsva")
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): without constant gene all 4 equal direct GSVA: TRUE | with it, differ from direct GSVA: gsva,ssgsea,plage,zscore

<a id="gsva-na-row"></a>
## A row with NA moves the GSVA gene set onto different genes

`gsva-na-row` · High · Bug · `R/3-stats-functions.R:1659` · functions: `colEnrichment` · first found in: call map (2026-11-09)

`rows = rows[-rmv]` uses positions of removed matrix rows as positions in the signature, and the remaining numbers then point into the shortened matrix. The same kind of mismatch as the constant-gene bug.

```r
y <- x; y[2, 1] <- NA
sigscores:::colEnrichment(y, rows = c(1, 3, 4, 5), method = "zscore")
GSVA::gsva(GSVA::zscoreParam(exprData = y[-2, ], geneSets = list(gs1 = sig)), verbose = FALSE)
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): package: -1.0004 -0.5133 1.5137 | direct on g1,g3,g4,g5: -0.1181 0.1752 -0.0571 | via computeSigScores: -1.0004 -0.5133 1.5137

<a id="gsva-sink"></a>
## If GSVA fails, R's printed output stays switched off

`gsva-sink` · High · Bug · `R/3-stats-functions.R:1710` · functions: `colEnrichment`, `computeSigScores`, `computeScores` · first found in: call map (2026-11-09)

`sink(nullfile())` runs before GSVA and `sink()` after it, with no `on.exit`. If GSVA errors, `computeScores` catches the error and carries on, and everything printed afterwards in that R session disappears. A shell that wraps this library would be directly affected.

```r
r <- computeSigScores(x, i = sig, scores = c("mean", "zscore"), args = list(zscore = list(minSize = 10)))
sink.number()
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): sink depth before 0 after 1 | zscore column all NA: TRUE | line 1710: sink(nullfile())

<a id="quantile-na-rows"></a>
## Quantile normalisation drops rows with NA, so scorers index the wrong rows

`quantile-na-rows` · High · Bug · `R/4-data-preprocessing.R:230` · functions: `quantileNormalizationForMatrix`, `quantileNormalization`, `computeScores` · first found in: Sigshell Phase 1-2 (2026-11-10)

With the default `na.rm = TRUE`, `quantileNormalizationForMatrix` removes rows containing NA (line 230). Scorers then apply the original row numbers to the shorter matrix: the signature lands on different genes or out of range, and the scores become wrong or NA without a message.

```r
y <- x; y[2, 1] <- NA
q <- getDataTransformer("quantile")
computeSigScores(y, i = c("g4", "g5"), scores = "mean", args = list(mean = list(transform.fun = q)))
colMeans(q(y)[c("g4", "g5"), ])
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): after quantile normalisation the matrix has 4 rows (g2 dropped by R/4-data-preprocessing.R:230); mean of g4,g5: NA NA NA | correct values: 9.5 9.5 8 | warnings: 0

<a id="rndsigsub-wrong-rows"></a>
## `rndsigsub` excludes the wrong genes

`rndsigsub-wrong-rows` · High · Bug · `R/0-utility-functions.R:832` · functions: `randomSignatures`, `computeSigScores`, `getIndex` · first found in: call map (2026-11-09)

`randomSignatures` subtracts `getIndex(updateSig(x, i))` from the row numbers, but those are positions inside `i`, not rows of `x`. A signature of k genes therefore removes the first k rows of the matrix. Real signature genes stay in the pool. The roxygen example hides this because its signature is the first 10 rows.

```r
y <- matrix(1:12, nrow = 6, dimnames = list(paste0("g", 1:6), c("S1", "S2")))
table(unlist(randomSignatures(y, i = c("g5", "g6"), n = 200, exclude = TRUE)))
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): rows drawn: 3-20 | signature rows 19,20 drawn: TRUE | rows 1,2 drawn: FALSE

<a id="z-cols"></a>
## `zStandardisation(by = "cols")` scales incorrectly

`z-cols` · High · Bug · `R/4-data-preprocessing.R:683` · functions: `zStandardisation`, `zStandardisationForMatrix` · first found in: call map (2026-11-09)

`sweep(...) / scale` divides a matrix by a vector with one value per column. R recycles down the rows, so each sample's values are divided by a mix of scales. There is no warning.

```r
round(zStandardisation(x, by = "cols") - scale(x), 3)
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): max |pkg - scale(x)| by cols: 0.391 | by rows vs t(scale(t(x))): 0

<a id="z-robust"></a>
## `robust = TRUE` standardises a matrix twice

`z-robust` · High · Bug · `R/4-data-preprocessing.R:667` · functions: `zStandardisation`, `zStandardisationForMatrix` · first found in: call map (2026-11-09)

The robust branch standardises at lines 659 and 675, and the shared line after it (667 or 683) does it again.

```r
ctr <- matrixStats::rowMedians(x); s <- matrixStats::rowMads(x, center = ctr)
round(zStandardisation(x, robust = TRUE, by = "rows") - (x - ctr) / s, 3)
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): equals single standardisation: FALSE | equals applying it twice: TRUE

<a id="df-input"></a>
## A data frame input gives a wrong result with no error

`df-input` · High · Hidden behaviour · `R/5-scorers.R:1125` · functions: `computeScores`, `computeSigScores` · first found in: call map (2026-11-09)

`computeScores` only accepts a real matrix. A data frame is turned into a list-matrix with one column, every scorer fails, and the failures are hidden. You get one row of NA. `read.csv` returns a data frame, so biologists will hit this.

```r
computeSigScores(as.data.frame(x), i = c("g1", "g3"), scores = "mean")
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): rows: 1 | mean: NA | warnings: 0

<a id="silent-na"></a>
## A scorer that fails becomes a column of NA, with no message

`silent-na` · High · Hidden behaviour · `R/5-scorers.R:1196` · functions: `computeScores`, `computeSigScores` · first found in: call map (2026-11-09)

Each scorer runs inside `tryCatch`, and the handler returns NA for every sample without logging the error. A real failure looks the same as missing data.

```r
computeSigScores(x, scorers = list(bad = function(...) stop("boom")))
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): all NA: TRUE | warnings: 0 | messages: 0

<a id="transform-order"></a>
## Two scorers transform after subsetting; the other 16 transform first

`transform-order` · High · Hidden behaviour · `R/5-scorers.R:217` · functions: `trimmedMeanScorer`, `aadScorer`, `meanScorer`, `computeScores` · first found in: call map (2026-11-09)

`trimmedMeanScorer` and `aadScorer` subset to the signature and then transform. The others transform the whole matrix first. With a data-dependent transformer such as quantile normalisation, scores are not comparable across these groups.

```r
q <- getDataTransformer("quantile")
meanScorer(x, i = c(1, 5), transform.fun = q)
trimmedMeanScorer(x, i = c(1, 5), trim = 0, transform.fun = q)
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): scorers that subset before transform: trimmedMean,aad | mean: 6.333 6.333 8.5 | trimmedMean trim=0: 7.167 7.167 7.167

<a id="computeSE-na"></a>
## `computeSE(na.rm = TRUE)` still returns NA

`computeSE-na` · Medium · Bug · `R/7-significance.R:181` · functions: `computeSE`, `computeStandardCI`, `computeSignificance` · first found in: call map (2026-11-09)

`na.rm` only reaches the mean. The sum of squared deviations and `n` still include the NA.

```r
sigscores:::computeSE(c(1, 2, NA), na.rm = TRUE)
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): computeSE(c(1,2,NA), na.rm=TRUE) = NA | sd(c(1,2)) = 0.7071

<a id="summation-i"></a>
## `summation` always errors when `i` is given

`summation-i` · Medium · Bug · `R/3-stats-functions.R:176` · functions: `summation`, `computeVectorMeasure` · first found in: call map (2026-11-09)

Line 176 subsets `w`, which doesn't exist in this function. The exported function fails for any `i`.

```r
summation(v, i = 1:2)
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): result: object 'w' not found

<a id="outdir-filename"></a>
## `outdir` alone saves nothing, despite `filename` having a default

`outdir-filename` · Medium · Docs differ · `R/6-compute-scores.R:394` · functions: `computeSigScores`, `dirExists` · first found in: call map (2026-11-09)

The check uses `missing(filename)`, so the default is never used. You get a warning that says the argument has no default, and the folder is created anyway. The docs say the data will be stored if `outdir` is provided.

```r
d <- file.path(tempdir(), "sigout")
r <- computeSigScores(x, i = sig, scores = "mean", outdir = d)
list.files(d)
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): outdir only -> files: 0 | warning: Output directory was provided but 'filename' is missing without default. Data won't be saved. | with filename given: sigscores.rds

<a id="resampling-null"></a>
## Permutation and bootstrap are random-gene-set nulls, not a measure of score stability

`resampling-null` · Medium · Docs differ · `R/6-compute-scores.R:309` · functions: `computeSigScores`, `sampleData` · first found in: Sigshell Phase 1-2 (2026-11-10)

The paper (section 2.2) says data sampling evaluates "score stability under data variability". `computeSigScores` reorders whole rows and then restores the row names (lines 309-311), so the signature names land on random rows: permutation scores a random gene set of the same size, exactly like `rndsig`, and bootstrap does the same with replacement. None of them resamples the observed signature's values.

```r
y <- matrix(c(1,10,100,1000,10000, 2,20,200,2000,20000), nrow = 5, dimnames = list(paste0("g",1:5), c("S1","S2")))
set.seed(1); p <- computeSigScores(y, i = c("g1","g2"), scores = "sum", sampling = "permutation", n.repeat = 4000)
set.seed(1); r <- computeSigScores(y, i = c("g1","g2"), scores = "sum", sampling = "rndsig", n.repeat = 4000)
round(rbind(permutation = prop.table(table(p$sum[p$sampleID == "S1"])), rndsig = prop.table(table(r$sum[r$sampleID == "S1"]))), 3)
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): permutation and rndsig score the same 10 gene pairs, max frequency difference 0.011 | bootstrap also scores pairs with a repeated gene: TRUE | lines 6-compute-scores.R:309-311: x = x[rnd[[iloop]],,drop=F] rownames(x) = rnames

<a id="asl-abs"></a>
## The default two-sided p-value compares absolute values

`asl-abs` · Medium · Hidden behaviour · `R/7-significance.R:131` · functions: `computeASL`, `computeSignificance` · first found in: call map (2026-11-09)

`abs(rnd) >= abs(obs)` assumes the null distribution is centred at zero. For scores that are always positive it behaves like the one-sided `greater` test. A value far below zero counts as extreme as one far above it.

```r
sigscores:::computeASL(5, c(-6, 4, 5, 6))
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): ASL(5; -6,4,5,6) = 0.75 (-6 counted as extreme) | on positive values two.sided == greater: TRUE | line 131: 'two.sided' = abs(rnd) >= abs(obs),

<a id="dup-signature-gene"></a>
## A gene listed twice in the signature is counted twice

`dup-signature-gene` · Medium · Hidden behaviour · `R/5-scorers.R:1174` · functions: `computeScores`, `computeSigScores` · first found in: Sigshell Phase 1-2 (2026-11-10)

`match` keeps duplicates, so every copy is scored as a separate row. The mean of g1, g3 changes when g1 is listed twice. `updateSig`, which removes duplicates, is not on this path.

```r
computeSigScores(x, i = c("g1", "g3"), scores = "mean")
computeSigScores(x, i = c("g1", "g1", "g3"), scores = "mean")
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): mean of g1,g3: 4 3 4.5 | with g1 listed twice: 3.3333 2.3333 5.3333 | R/5-scorers.R:1174: i = match(table = rownames(x), x = i)

<a id="logger-con"></a>
## An open connection given to `createLogger` is discarded

`logger-con` · Medium · Hidden behaviour · `R/0-utility-functions.R:966` · functions: `openCon`, `createLogger`, `computeSigScores` · first found in: call map (2026-11-09)

`openCon` replaces the logger's connection with one opened from `path`. With no path the connection becomes NULL, so nothing reaches yours.

```r
out <- character(); tc <- textConnection("out", "w")
r <- computeSigScores(x, i = sig, scores = "mean", logger = createLogger(con = tc, verbose = FALSE))
close(tc); out
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): lines written to given connection: 0 | lines written when path given: 1

<a id="one-sample"></a>
## With one sample, the GSVA scores are always NA

`one-sample` · Medium · Hidden behaviour · `R/3-stats-functions.R:1666` · functions: `colEnrichment`, `areRowValuesEqual` · first found in: call map (2026-11-09)

With a single column every gene counts as constant, so all genes are removed and the function returns NA.

```r
sigscores:::colEnrichment(x[, 1, drop = FALSE], rows = 1:3, method = "zscore")
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): colEnrichment: NA | via computeSigScores: NA NA NA NA

<a id="rndsig-size"></a>
## Random signatures count genes that aren't in the matrix

`rndsig-size` · Medium · Hidden behaviour · `R/0-utility-functions.R:818` · functions: `randomSignatures`, `computeSigScores` · first found in: call map (2026-11-09)

The random set has `length(i)` genes, including unknown ones. The observed score only uses genes that exist, so the two are computed from different numbers of genes.

```r
lengths(randomSignatures(x, i = c("g1", "gX"), n = 1))
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): signature with 1 known + 1 unknown gene -> random set size 2

<a id="typo-score"></a>
## A misspelled score id is dropped with no warning

`typo-score` · Medium · Hidden behaviour · `R/5-scorers.R:1139` · functions: `computeScores`, `computeSigScores`, `getScorers` · first found in: call map (2026-11-09)

`computeScores` uses `intersect`, so `meen` vanishes. Only if every id is wrong do you get an error. The warning in `getScorers` is never reached from `computeSigScores`.

```r
computeSigScores(x, i = c("g1", "g3"), scores = c("mean", "meen"))
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): columns: sampleID,mean | warnings: 0 | all ids wrong: error

<a id="unknown-gene"></a>
## An unknown gene becomes an NA row number and disappears under the default `na.rm`

`unknown-gene` · Medium · Hidden behaviour · `R/5-scorers.R:1174` · functions: `computeScores`, `computeSigScores` · first found in: call map (2026-11-09)

`match` gives NA for the unknown gene. With the default `na.rm = TRUE` the score is computed from the other genes, with no message.

```r
computeSigScores(x, i = c("g1", "g3", "gX"), scores = "mean")
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): same as without gX: TRUE | warnings: 0 | na.rm=FALSE all NA: TRUE

<a id="vector-stubs"></a>
## The exported `gsva`, `ssgsea`, `plage` and `zscore` always return NA

`vector-stubs` · Medium · Hidden behaviour · `R/3-stats-functions.R:813` · functions: `ssgsea`, `gsva`, `plage`, `zscore`, `enrichment`, `computeVectorMeasure` · first found in: call map (2026-11-09)

They share their names with real scores, but the vector versions are placeholders. The Details section of their documentation does say so.

```r
c(gsva(v), ssgsea(v), plage(v), zscore(v))
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): NA NA NA NA

<a id="logall"></a>
## `logAll` never prints

`logall` · Low · Bug · `R/1-log-functions.R:163` · functions: `logAll`, `getLogLevels` · first found in: call map (2026-11-09)

`getLogLevels` never includes ALL. No exported function reaches it.

```r
sigscores:::logAll(createLogger(level = "ALL"), message = "hello", sep = "\n")
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): logAll printed lines: 0 | logInfo printed lines: 1

<a id="pool-of-one"></a>
## A pool of one gene is treated as `1:n`

`pool-of-one` · Low · Bug · `R/0-utility-functions.R:838` · functions: `randomSignatures` · first found in: call map (2026-11-09)

`sample(x = out, ...)` with a single number draws from 1 to that number, which can include the signature. It only happens when the signature covers all genes but one.

```r
y <- matrix(1:10, nrow = 5, dimnames = list(paste0("g", 1:5), c("S1", "S2")))
randomSignatures(y, i = paste0("g", 1:4), n = 2, exclude = TRUE)
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): pool after exclusion: 5 | asked for 4 genes, got: 1,4,5,3

<a id="setters"></a>
## Three setters overwrite the connection instead

`setters` · Low · Bug · `R/1-log-functions.R:141` · functions: `setVerbose`, `setPath`, `setLevel` · first found in: call map (2026-11-09)

All three bodies say `object$con = value`. No exported function reaches them.

```r
str(unclass(sigscores:::setVerbose(createLogger(), FALSE)))
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): after setVerbose(FALSE): verbose = TRUE , con = FALSE | after setLevel('DEBUG'): level = INFO

<a id="docs-char-i"></a>
## Four scorers reject gene names in `i` when called directly

`docs-char-i` · Low · Docs differ · `R/5-scorers.R:13` · functions: `sumScorer`, `meanScorer`, `medianScorer`, `madScorer` · first found in: call map (2026-11-09)

The docs allow names, but `sum`, `mean`, `median` and `mad` pass `i` to `matrixStats`, which only accepts numbers. It works through `computeSigScores`, which converts names first.

```r
meanScorer(x, i = c("g1", "g2"))
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): error with gene names: sum,mean,median,mad

<a id="docs-generic"></a>
## The docs describe a `genericScorer` and `computeColMeasures` route that the scorers don't take

`docs-generic` · Low · Docs differ · `man/getScorers.Rd` · functions: `getScorers`, `getScorer`, `computeColMeasures` · first found in: call map (2026-11-09)

There is no `genericScorer` function, and the scorers call `matrixStats` or the vector functions directly.

```r
exists("genericScorer", asNamespace("sigscores"))
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): Rd mentions genericScorer: TRUE | function exists: FALSE | scorers calling computeColMeasures: 0

<a id="docs-random"></a>
## The docs mention `sampling = "random"`, which doesn't exist

`docs-random` · Low · Docs differ · `R/6-compute-scores.R:49` · functions: `computeSigScores` · first found in: call map (2026-11-09)

The allowed values are none, permutation, bootstrap, rndsig and rndsigsub.

```r
computeSigScores(x, sampling = "random")
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): sampling='random': error | doc line 49: #'If \code{sampling = "random"}, \code{sampling = "bootstrap"},

<a id="docs-step"></a>
## The docs for `stepFunction` reverse `y`

`docs-step` · Low · Docs differ · `R/3-stats-functions.R:1830` · functions: `stepFunction`, `stepFunctionForVector` · first found in: call map (2026-11-09)

The formula gives `y[1]` when x is above the threshold. The code at lines 1911 to 1913 uses `y[1]` when x is below.

```r
stepFunction(c(1, 5, 9), thr = 5, y = c(10, 20, 30))
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): x=1,5,9 thr=5 -> 10,20,30 | doc line 1830: #'y_{1}, \quad \textrm{if} \quad x > threshold \\

<a id="docs-transform-sub"></a>
## `transform.sub` is documented but does nothing

`docs-transform-sub` · Low · Docs differ · `R/5-scorers.R:35` · functions: `meanScorer`, `sumScorer`, `trimmedMeanScorer` · first found in: call map (2026-11-09)

None of the 18 scorers read it.

```r
"transform.sub" %in% all.names(body(sigscores::meanScorer))
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): scorers whose body reads transform.sub: 0 of 18

<a id="samplers-none"></a>
## `getAvailableRandomSamplers` leaves out `none`

`samplers-none` · Low · Docs differ · `R/0-utility-functions.R:127` · functions: `getAvailableRandomSamplers`, `computeSigScores` · first found in: call map (2026-11-09)

It is the default in `computeSigScores`.

```r
getAvailableRandomSamplers()$id
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): listed: permutation,bootstrap,rndsig,rndsigsub | computeSigScores default: none

<a id="custom-names"></a>
## Custom scorer names are rewritten

`custom-names` · Low · Hidden behaviour · `R/5-scorers.R:1234` · functions: `computeScores` · first found in: call map (2026-11-09)

`data.frame` makes column names syntactically valid, so `my score` becomes `my.score`.

```r
colnames(computeSigScores(x, scorers = list("my score" = getScorer("mean"))))
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): sampleID,my.score

<a id="dep-defaults"></a>
## Some numbers come from dependencies' defaults

`dep-defaults` · Low · Hidden behaviour · `R/3-stats-functions.R:748` · functions: `MAD`, `madScorer`, `colMADs`, `colEnrichment` · first found in: call map (2026-11-09)

`MAD` multiplies by 1.4826, the default of `stats::mad`. Quartile-based scores use the default quantile type. The GSVA methods use the defaults of `GSVA` 2.0.7, which are shown on `colEnrichment`.

```r
c(MAD = MAD(c(1, 2, 9)), raw = median(abs(c(1, 2, 9) - 2)))
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): MAD(1,2,9) = 1.4826 | raw median abs dev = 1 | type arg for quantile in midhinge/iqr: FALSE

<a id="dirExists-creates"></a>
## `dirExists` creates the folder

`dirExists-creates` · Low · Hidden behaviour · `R/0-utility-functions.R:994` · functions: `dirExists` · first found in: call map (2026-11-09)

It also returns whether a path was given, not whether the folder existed. The docs do describe this; the name doesn't.

```r
d <- file.path(tempdir(), "a", "b"); sigscores:::dirExists(d); dir.exists(d)
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): returned TRUE | folder now exists: TRUE

<a id="dup-matrix-gene"></a>
## If two matrix rows share a gene name, only the first is scored

`dup-matrix-gene` · Low · Hidden behaviour · `R/5-scorers.R:1174` · functions: `computeScores` · first found in: Sigshell Phase 1-2 (2026-11-10)

`match` returns the first matching row. `read.csv` refuses duplicate row names, but a matrix built in R can have them, and nothing warns.

```r
y <- x; rownames(y)[2] <- "g1"
computeSigScores(y, i = c("g1", "g3"), scores = "mean")
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): matrix rows 1 and 2 are both g1; scoring g1,g3 uses only the first g1 row: TRUE | no warning

<a id="dup-samples"></a>
## Duplicate sample names are an error

`dup-samples` · Low · Hidden behaviour · `R/5-scorers.R:1236` · functions: `computeScores` · first found in: call map (2026-11-09)

They become row names of the result, which must be unique.

```r
y <- x; colnames(y) <- c("S1", "S1", "S3"); computeSigScores(y, scores = "mean")
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): duplicate row.names: S1

<a id="iqm-small"></a>
## IQM is NA for fewer than 4 values

`iqm-small` · Low · Hidden behaviour · `R/3-stats-functions.R:674` · functions: `IQM`, `iqmScorer`, `colIQMs` · first found in: call map (2026-11-09)

Small signatures give NA with no message.

```r
IQM(c(1, 2, 3))
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): IQM(1:3) = NA | IQM(1:4) = 2.5

<a id="modal-tie"></a>
## Mode ties go to the smallest value

`modal-tie` · Low · Hidden behaviour · `R/3-stats-functions.R:407` · functions: `modalValue`, `modeScorer`, `colModes` · first found in: call map (2026-11-09)

`which.max` on a sorted table picks the first maximum. With no repeated values the mode is simply the smallest value.

```r
modalValue(c(3, 3, 1, 1, 2))
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): tie 3,3,1,1,2 -> 1 | no repeats 9,4,7 -> 4

<a id="mode-is-min"></a>
## On data without repeated values, mode is the minimum

`mode-is-min` · Low · Hidden behaviour · `R/3-stats-functions.R:407` · functions: `modalValue`, `modeScorer` · first found in: Sigshell Phase 1-2 (2026-11-10)

Ties go to the smallest value (finding modal-tie). The vignette's data has no repeated values, so its `mode` column is each sample's lowest signature value; most continuous expression data behaves the same way.

```r
set.seed(5381L, kind = "Mersenne-Twister", normal.kind = "Inversion")
xv <- matrix(sample(1000), nrow = 100, dimnames = list(paste0("g", 1:100), paste0("S", 1:10)))
sv <- rownames(xv)[sample(100, 20)]
identical(computeSigScores(xv, i = sv, scores = "mode")$mode, as.numeric(apply(xv[sv, ], 2, min)))
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): vignette data has no repeated values; mode equals the signature minimum in all 10 samples: TRUE

<a id="no-seed"></a>
## There is no seed argument

`no-seed` · Low · Hidden behaviour · `R/0-utility-functions.R:729` · functions: `sampleData`, `randomSignatures`, `computeSigScores` · first found in: call map (2026-11-09)

Both draws use R's global random state, in the main process. Call `set.seed` before `computeSigScores` to reproduce a run.

```r
set.seed(1); a <- sampleData(x, "permutation", 1); set.seed(1); b <- sampleData(x, "permutation", 1); identical(a, b)
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): same seed same draw: TRUE | any seed argument: FALSE | parallel run equals serial run under same seed: TRUE

<a id="parallel-verbose"></a>
## `cores` above 1 prints foreach's debugging output

`parallel-verbose` · Low · Hidden behaviour · `R/2-parallel-functions.R:85` · functions: `forLoop`, `computeSigScores` · first found in: call map (2026-11-09)

`forLoop` defaults to `verbose = TRUE` and no caller changes it. In parallel runs, foreach's progress messages are printed.

```r
r <- computeSigScores(x, i = sig, scores = "mean", sampling = "permutation", n.repeat = 2, cores = 2)
```

Evidence (2026-11-10, sigscores 40f55c5, R 4.4.1, macOS arm64): lines printed: 14 | first: discovered package(s): 
