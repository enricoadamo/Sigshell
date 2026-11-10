# Replay one recorded run (fixture k) in this fresh R process and write its output as JSON.
# Usage: Rscript replay.R <k> <recorded-runs.json> <outdir>
args <- commandArgs(trailingOnly = TRUE); k <- as.integer(args[1]); fx <- args[2]; outdir <- args[3]
fx <- jsonlite::fromJSON(fx, simplifyVector = FALSE)
run <- fx$runs[[k]]
suppressPackageStartupMessages(library(sigscores))
options(width = 72, digits = 4)
eval(parse(text = paste(unlist(fx$setup), collapse = "\n")), globalenv())
n0 <- sink.number(); buf <- character()
tc <- textConnection("buf", "w", local = TRUE); sink(tc)
msgs <- character(); warns <- character(); err <- NULL
env <- new.env(parent = globalenv())
set.seed(1)
tryCatch(withCallingHandlers({
  for (e in parse(text = run$code, keep.source = FALSE)) {
    r <- withVisible(eval(e, env)); if (r$visible) print(r$value)
  }
},
warning = function(w) { warns <<- c(warns, conditionMessage(w)); invokeRestart("muffleWarning") },
message = function(m) { msgs <<- c(msgs, trimws(conditionMessage(m))); invokeRestart("muffleMessage") }),
error = function(e) err <<- conditionMessage(e))
stuck <- sink.number() - n0 - 1L
while (sink.number() > n0) sink()
close(tc)
res <- list(k = k, out = paste(buf, collapse = "\n"), warn = as.list(unique(warns)), msg = as.list(unique(msgs)), err = err, stuck = stuck)
jsonlite::write_json(res, file.path(outdir, sprintf("%03d.json", k)), auto_unbox = TRUE, null = "null")
