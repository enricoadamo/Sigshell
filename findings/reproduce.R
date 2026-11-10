# Reproduce every Sigshell finding about sigscores with a minimal case.
# Usage: Rscript findings/reproduce.R <finding-id>   (or --list)
# Prints: id <TAB> CONFIRMED | NOT-AS-STATED | UNCLEAR <TAB> evidence
# SIGSCORES_SRC points at the pinned sigscores checkout (default ../sigscores), used to quote source lines.
suppressPackageStartupMessages(library(sigscores))
SRC <- Sys.getenv("SIGSCORES_SRC", "../sigscores")
x <- matrix(c(2,4,6,8,10, 1,3,5,9,11, 7,7,2,4,12), nrow = 5, dimnames = list(paste0("g", 1:5), paste0("S", 1:3)))
sig <- c("g1", "g3", "g4", "g5"); v <- c(g1 = 2, g2 = 4, g3 = 6, g4 = 8, g5 = 10)
quiet <- function(e) { w <- character(); m <- character()
  val <- withCallingHandlers(e, warning = function(c) { w <<- c(w, conditionMessage(c)); invokeRestart("muffleWarning") }, message = function(c) { m <<- c(m, conditionMessage(c)); invokeRestart("muffleMessage") })
  list(val = val, w = w, m = m) }
direct <- function(mat, genes, method) { p <- switch(method, gsva = GSVA::gsvaParam(mat, list(gs1 = genes)), ssgsea = GSVA::ssgseaParam(mat, list(gs1 = genes)), plage = GSVA::plageParam(mat, list(gs1 = genes)), zscore = GSVA::zscoreParam(mat, list(gs1 = genes)))
  as.numeric(suppressMessages(GSVA::gsva(p, verbose = FALSE))) }
src <- function(file, line) trimws(readLines(file.path(SRC, file), warn = FALSE)[line])
F <- list(
 "rndsigsub-wrong-rows" = function() { y <- matrix(1:40, nrow = 20, dimnames = list(paste0("g", 1:20), c("S1", "S2"))); set.seed(1)
   t <- sort(unique(unlist(randomSignatures(y, i = c("g19", "g20"), n = 500, exclude = TRUE))))
   list(ok = all(19:20 %in% t) && !any(1:2 %in% t), ev = paste("rows drawn:", paste(range(t), collapse = "-"), "| signature rows 19,20 drawn:", all(19:20 %in% t), "| rows 1,2 drawn:", any(1:2 %in% t))) },
 "gsva-constant-gene" = function() { xc <- rbind(gC = c(5, 5, 5), x); d <- sapply(c("gsva", "ssgsea", "plage", "zscore"), function(m) {
     a <- quiet(computeSigScores(xc, i = sig, scores = m))$val[[m]]; ref <- direct(x, sig, m); base <- quiet(computeSigScores(x, i = sig, scores = m))$val[[m]]
     c(base_ok = isTRUE(all.equal(base, ref)), wrong = !isTRUE(all.equal(a, ref))) })
   list(ok = all(d["base_ok", ]) && all(d["wrong", ]), ev = paste("without constant gene all 4 equal direct GSVA:", all(d["base_ok", ]), "| with it, differ from direct GSVA:", paste(colnames(d)[d["wrong", ]], collapse = ","))) },
 "gsva-na-row" = function() { y <- x; y[2, 1] <- NA; a <- quiet(sigscores:::colEnrichment(y, rows = c(1, 3, 4, 5), method = "zscore"))$val; ref <- direct(y[-2, ], sig, "zscore")
   viaTop <- quiet(computeSigScores(y, i = sig, scores = "zscore"))$val$zscore
   list(ok = !isTRUE(all.equal(as.numeric(a), ref)), ev = paste("package:", paste(round(a, 4), collapse = " "), "| direct on g1,g3,g4,g5:", paste(round(ref, 4), collapse = " "), "| via computeSigScores:", paste(round(viaTop, 4), collapse = " "))) },
 "gsva-sink" = function() { n0 <- sink.number(); r <- computeSigScores(x, i = sig, scores = c("mean", "zscore"), args = list(zscore = list(minSize = 10))); n1 <- sink.number(); while (sink.number() > n0) sink()
   list(ok = n1 == n0 + 1 && all(is.na(r$zscore)), ev = paste("sink depth before", n0, "after", n1, "| zscore column all NA:", all(is.na(r$zscore)), "| line 1710:", src("R/3-stats-functions.R", 1710))) },
 "z-cols" = function() { d <- max(abs(zStandardisation(x, by = "cols") - scale(x))); r <- max(abs(zStandardisation(x, by = "rows") - t(scale(t(x)))))
   list(ok = d > 1e-8 && r < 1e-12, ev = paste("max |pkg - scale(x)| by cols:", signif(d, 3), "| by rows vs t(scale(t(x))):", signif(r, 3))) },
 "z-robust" = function() { ctr <- matrixStats::rowMedians(x); s <- matrixStats::rowMads(x, center = ctr); once <- (x - ctr) / s; twice <- (once - ctr) / s
   p <- zStandardisation(x, robust = TRUE, by = "rows"); list(ok = max(abs(p - once)) > 1e-8 && max(abs(p - twice)) < 1e-12, ev = paste("equals single standardisation:", max(abs(p - once)) < 1e-12, "| equals applying it twice:", max(abs(p - twice)) < 1e-12)) },
 "silent-na" = function() { q <- quiet(computeSigScores(x, scorers = list(bad = function(...) stop("boom")))); o <- capture.output(print(q$val))
   list(ok = all(is.na(q$val$bad)) && !length(q$w) && !length(q$m) && !any(grepl("boom", o)), ev = paste("all NA:", all(is.na(q$val$bad)), "| warnings:", length(q$w), "| messages:", length(q$m))) },
 "transform-order" = function() { q <- getDataTransformer("quantile"); ids <- getAvailableScores()$id; i <- c(1, 5)
   post <- sapply(ids, function(id) { f <- getScorer(id); b <- body(f); s <- paste(deparse(b), collapse = " "); regexpr("x\\[i, , drop = F\\]", s) > 0 && regexpr("x\\[i, , drop = F\\]", s) < regexpr("do.call", s) })
   a <- meanScorer(x, i = i, transform.fun = q); b <- trimmedMeanScorer(x, i = i, trim = 0, transform.fun = q)
   list(ok = identical(names(post)[post], c("trimmedMean", "aad")) && !isTRUE(all.equal(as.numeric(a), as.numeric(b))), ev = paste("scorers that subset before transform:", paste(names(post)[post], collapse = ","), "| mean:", paste(round(a, 3), collapse = " "), "| trimmedMean trim=0:", paste(round(b, 3), collapse = " "))) },
 "df-input" = function() { q <- quiet(computeSigScores(as.data.frame(x), i = c("g1", "g3"), scores = "mean")); list(ok = nrow(q$val) == 1 && is.na(q$val$mean) && !length(q$w), ev = paste("rows:", nrow(q$val), "| mean:", q$val$mean, "| warnings:", length(q$w))) },
 "typo-score" = function() { q <- quiet(computeSigScores(x, i = c("g1", "g3"), scores = c("mean", "meen"))); e <- tryCatch({ computeSigScores(x, scores = "meen"); "no error" }, error = function(e) "error")
   list(ok = identical(colnames(q$val), c("sampleID", "mean")) && !length(q$w) && e == "error", ev = paste("columns:", paste(colnames(q$val), collapse = ","), "| warnings:", length(q$w), "| all ids wrong:", e)) },
 "unknown-gene" = function() { a <- quiet(computeSigScores(x, i = c("g1", "g3", "gX"), scores = "mean")); b <- computeSigScores(x, i = c("g1", "g3"), scores = "mean"); c <- computeSigScores(x, i = c("g1", "g3", "gX"), scores = "mean", na.rm = FALSE)
   list(ok = identical(a$val, b) && !length(a$w) && all(is.na(c$mean)), ev = paste("same as without gX:", identical(a$val, b), "| warnings:", length(a$w), "| na.rm=FALSE all NA:", all(is.na(c$mean)))) },
 "summation-i" = function() { e <- tryCatch(summation(v, i = 1:2), error = function(e) conditionMessage(e)); list(ok = identical(e, "object 'w' not found"), ev = paste("result:", e)) },
 "outdir-filename" = function() { d <- file.path(tempdir(), "so1"); q <- quiet(computeSigScores(x, i = sig, scores = "mean", outdir = d)); d2 <- file.path(tempdir(), "so2"); computeSigScores(x, i = sig, scores = "mean", outdir = d2, filename = "sigscores")
   list(ok = dir.exists(d) && !length(list.files(d)) && length(q$w) == 1 && identical(list.files(d2), "sigscores.rds"), ev = paste("outdir only -> files:", length(list.files(d)), "| warning:", trimws(q$w), "| with filename given:", list.files(d2))) },
 "computeSE-na" = function() { a <- sigscores:::computeSE(c(1, 2, NA), na.rm = TRUE); list(ok = is.na(a), ev = paste("computeSE(c(1,2,NA), na.rm=TRUE) =", a, "| sd(c(1,2)) =", round(sd(c(1, 2)), 4))) },
 "logger-con" = function() { out <- character(); tc <- textConnection("out", "w", local = TRUE); r <- computeSigScores(x, i = sig, scores = "mean", logger = createLogger(con = tc, verbose = FALSE)); close(tc)
   f <- tempfile(fileext = ".log"); r <- computeSigScores(x, i = sig, scores = "mean", logger = createLogger(path = f, verbose = FALSE)); list(ok = !length(out) && length(readLines(f)) > 0, ev = paste("lines written to given connection:", length(out), "| lines written when path given:", length(readLines(f)))) },
 "vector-stubs" = function() { a <- c(gsva(v), ssgsea(v), plage(v), zscore(v)); list(ok = all(is.na(a)), ev = paste(a, collapse = " ")) },
 "asl-abs" = function() { a <- sigscores:::computeASL(5, c(-6, 4, 5, 6)); pos <- c(4, 5, 6, 7); list(ok = a == 0.75 && sigscores:::computeASL(5, pos) == sigscores:::computeASL(5, pos, "greater"), ev = paste("ASL(5; -6,4,5,6) =", a, "(-6 counted as extreme) | on positive values two.sided == greater:", sigscores:::computeASL(5, pos) == sigscores:::computeASL(5, pos, "greater"), "| line 131:", src("R/7-significance.R", 131))) },
 "rndsig-size" = function() { set.seed(1); n <- lengths(randomSignatures(x, i = c("g1", "gX"), n = 1, exclude = FALSE)); list(ok = n == 2, ev = paste("signature with 1 known + 1 unknown gene -> random set size", n)) },
 "one-sample" = function() { a <- sigscores:::colEnrichment(x[, 1, drop = FALSE], rows = 1:3, method = "zscore"); b <- quiet(computeSigScores(x[, 1, drop = FALSE], i = sig, scores = c("gsva", "ssgsea", "plage", "zscore")))$val
   list(ok = is.na(a) && all(is.na(b[1, -1])), ev = paste("colEnrichment:", a, "| via computeSigScores:", paste(unlist(b[1, -1]), collapse = " "))) },
 "parallel-verbose" = function() { o <- capture.output(r <- computeSigScores(x, i = sig, scores = "mean", sampling = "permutation", n.repeat = 2, cores = 2)); list(ok = any(grepl("numValues|exporting", o)), ev = paste("lines printed:", length(o), "| first:", o[1])) },
 "no-seed" = function() { set.seed(1); a <- sampleData(x, "permutation", 1); set.seed(1); b <- sampleData(x, "permutation", 1); c <- sampleData(x, "permutation", 1)
   has <- any(grepl("seed", unlist(lapply(c("computeSigScores", "sampleData", "randomSignatures"), function(f) names(formals(get(f)))))))
   set.seed(7); s1 <- computeSigScores(x, i = sig, scores = "mean", sampling = "rndsig", n.repeat = 3); set.seed(7); s2 <- suppressWarnings({ capture.output(z <- computeSigScores(x, i = sig, scores = "mean", sampling = "rndsig", n.repeat = 3, cores = 2)); z })
   list(ok = identical(a, b) && !identical(a, c) && !has, ev = paste("same seed same draw:", identical(a, b), "| any seed argument:", has, "| parallel run equals serial run under same seed:", isTRUE(all.equal(s1[order(s1$run, s1$sampleID), "mean"], s2[order(s2$run, s2$sampleID), "mean"])))) },
 "pool-of-one" = function() { y <- matrix(1:10, nrow = 5, dimnames = list(paste0("g", 1:5), c("S1", "S2"))); set.seed(1); r <- randomSignatures(y, i = paste0("g", 5), n = 50, exclude = TRUE); y2 <- y
   pool <- setdiff(1:5, sigscores:::getIndex(sigscores:::updateSig(y, paste0("g", 1:4)))); r4 <- tryCatch(randomSignatures(y, i = paste0("g", 1:4), n = 2, exclude = TRUE), error = function(e) conditionMessage(e))
   list(ok = length(pool) == 1 && is.list(r4) && all(lengths(r4) == 4), ev = paste("pool after exclusion:", paste(pool, collapse = ","), "| asked for 4 genes, got:", paste(r4[[1]], collapse = ","))) },
 "dirExists-creates" = function() { d <- file.path(tempdir(), "a", "b"); r <- sigscores:::dirExists(d); list(ok = isTRUE(r) && dir.exists(d), ev = paste("returned", r, "| folder now exists:", dir.exists(d))) },
 "custom-names" = function() { n <- colnames(computeSigScores(x, scorers = list("my score" = getScorer("mean")))); list(ok = identical(n, c("sampleID", "my.score")), ev = paste(n, collapse = ",")) },
 "dup-samples" = function() { y <- x; colnames(y) <- c("S1", "S1", "S3"); e <- tryCatch({ computeSigScores(y, scores = "mean"); "no error" }, error = function(e) conditionMessage(e)); list(ok = grepl("duplicate row.names", e), ev = e) },
 "iqm-small" = function() { list(ok = is.na(IQM(c(1, 2, 3))) && !is.na(IQM(c(1, 2, 3, 4))), ev = paste("IQM(1:3) =", IQM(c(1, 2, 3)), "| IQM(1:4) =", IQM(c(1, 2, 3, 4)))) },
 "modal-tie" = function() { list(ok = modalValue(c(3, 3, 1, 1, 2)) == 1 && modalValue(c(9, 4, 7)) == 4, ev = paste("tie 3,3,1,1,2 ->", modalValue(c(3, 3, 1, 1, 2)), "| no repeats 9,4,7 ->", modalValue(c(9, 4, 7)))) },
 "dep-defaults" = function() { a <- MAD(c(1, 2, 9)); list(ok = isTRUE(all.equal(a, 1.4826)) && !"constant" %in% names(formals(MAD)), ev = paste("MAD(1,2,9) =", a, "| raw median abs dev = 1 | type arg for quantile in midhinge/iqr:", any(grepl("type", deparse(body(midhinge)))))) },
 "docs-random" = function() { e <- tryCatch({ computeSigScores(x, sampling = "random"); "no error" }, error = function(e) "error"); list(ok = e == "error" && grepl('sampling = "random"', src("R/6-compute-scores.R", 49), fixed = TRUE), ev = paste("sampling='random':", e, "| doc line 49:", src("R/6-compute-scores.R", 49))) },
 "docs-step" = function() { a <- stepFunction(c(1, 5, 9), thr = 5, y = c(10, 20, 30)); list(ok = identical(a, c(10, 20, 30)) && grepl("x > threshold", src("R/3-stats-functions.R", 1830)), ev = paste("x=1,5,9 thr=5 ->", paste(a, collapse = ","), "| doc line 1830:", src("R/3-stats-functions.R", 1830))) },
 "docs-transform-sub" = function() { u <- sapply(getAvailableScores()$id, function(id) "transform.sub" %in% all.names(body(getScorer(id)))); list(ok = !any(u), ev = paste("scorers whose body reads transform.sub:", sum(u), "of", length(u))) },
 "docs-generic" = function() { rd <- paste(readLines(file.path(SRC, "man/getScorers.Rd")), collapse = " "); ex <- exists("genericScorer", asNamespace("sigscores"), inherits = FALSE)
   uses <- sapply(getAvailableScores()$id, function(id) "computeColMeasures" %in% all.names(body(getScorer(id)))); list(ok = grepl("genericScorer", rd) && !ex && !any(uses), ev = paste("Rd mentions genericScorer:", grepl("genericScorer", rd), "| function exists:", ex, "| scorers calling computeColMeasures:", sum(uses))) },
 "docs-char-i" = function() { r <- sapply(getAvailableScores()$id, function(id) tryCatch({ suppressMessages(getScorer(id)(x, i = c("g1", "g2", "g3"))); "works" }, error = function(e) "error")); list(ok = identical(names(r)[r == "error"], c("sum", "mean", "median", "mad")), ev = paste("error with gene names:", paste(names(r)[r == "error"], collapse = ","))) },
 "samplers-none" = function() { a <- getAvailableRandomSamplers()$id; d <- eval(formals(computeSigScores)$sampling); list(ok = !"none" %in% a && d[1] == "none", ev = paste("listed:", paste(a, collapse = ","), "| computeSigScores default:", d[1])) },
 "setters" = function() { l <- createLogger(); a <- sigscores:::setVerbose(l, FALSE); b <- sigscores:::setLevel(l, "DEBUG"); c <- sigscores:::setPath(l, "p"); list(ok = isFALSE(a$con) && isTRUE(a$verbose) && b$level == "INFO" && identical(b$con, "DEBUG") && identical(c$con, "p"), ev = paste("after setVerbose(FALSE): verbose =", a$verbose, ", con =", a$con, "| after setLevel('DEBUG'): level =", b$level)) },
 "resampling-null" = function() { y <- matrix(c(1,10,100,1000,10000, 2,20,200,2000,20000), nrow = 5, dimnames = list(paste0("g",1:5), c("S1","S2")))
   s1 <- function(m) { set.seed(1); r <- computeSigScores(y, i = c("g1","g2"), scores = "sum", sampling = m, n.repeat = 4000); r$sum[r$sampleID == "S1"] }
   p <- s1("permutation"); g <- s1("rndsig"); b <- s1("bootstrap"); tp <- prop.table(table(p)); tg <- prop.table(table(g))
   d <- max(abs(tp - tg[names(tp)])); list(ok = identical(names(tp), names(tg)) && length(tp) == 10 && d < 0.03 && 20000 %in% b, ev = paste("permutation and rndsig score the same 10 gene pairs, max frequency difference", round(d, 3), "| bootstrap also scores pairs with a repeated gene:", 20000 %in% b, "| lines 6-compute-scores.R:309-311:", src("R/6-compute-scores.R", 309), src("R/6-compute-scores.R", 311))) },
 "mode-is-min" = function() { set.seed(5381L, kind = "Mersenne-Twister", normal.kind = "Inversion"); xv <- matrix(sample(1000), nrow = 100, ncol = 10, dimnames = list(paste0("g", 1:100), paste0("S", 1:10))); sv <- rownames(xv)[sample(100, 20)]
   m <- computeSigScores(xv, i = sv, scores = "mode")$mode; mn <- apply(xv[sv, ], 2, min); list(ok = !any(duplicated(as.vector(xv))) && identical(as.numeric(m), as.numeric(mn)), ev = paste("vignette data has no repeated values; mode equals the signature minimum in all", length(m), "samples:", identical(as.numeric(m), as.numeric(mn)))) },
 "logall" = function() { o <- capture.output(sigscores:::logAll(createLogger(level = "ALL"), message = "hello", sep = "\n")); o2 <- capture.output(sigscores:::logInfo(createLogger(level = "ALL"), message = "hello", sep = "\n")); list(ok = !length(o) && length(o2) == 1, ev = paste("logAll printed lines:", length(o), "| logInfo printed lines:", length(o2))) }
)
id <- commandArgs(trailingOnly = TRUE)[1]
if (identical(id, "--list")) { cat(names(F), sep = "\n"); quit() }
r <- tryCatch(F[[id]](), error = function(e) list(ok = NA, ev = paste("CHECK ERRORED:", conditionMessage(e))))
while (sink.number() > 0) sink()
cat(sprintf("%s\t%s\t%s\n", id, if (is.na(r$ok)) "UNCLEAR" else if (r$ok) "CONFIRMED" else "NOT-AS-STATED", r$ev))
