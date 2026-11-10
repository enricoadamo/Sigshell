## ---- Sigshell preamble: run this once, from the session folder ----
## Every number below comes from sigscores. These helpers only read files, capture
## warnings and messages, and save results.
suppressPackageStartupMessages(library(sigscores))
dir.create("outputs", showWarnings = FALSE)

## Expression matrix: .csv (comma) or .tsv/.txt (tab). First row = sample names,
## first column = gene IDs, cells = numbers, "NA" or empty = missing.
sigshell_read_matrix <- function(path) {
  sep <- if (grepl("[.]csv$", path, ignore.case = TRUE)) "," else "\t"
  n <- utils::count.fields(path, sep = sep, quote = "\"", comment.char = "", blank.lines.skip = TRUE)[1]
  d <- utils::read.table(path, header = TRUE, sep = sep, quote = "\"", comment.char = "",
                         row.names = 1, check.names = FALSE, na.strings = c("NA", ""),
                         colClasses = c("character", rep("numeric", n - 1L)),
                         strip.white = TRUE, encoding = "UTF-8")
  m <- as.matrix(d)
  storage.mode(m) <- "double"
  m
}

## Signature: one gene per line, optional weight after a tab or comma; "#" lines and a
## first line starting with "gene" are skipped.
sigshell_read_signature <- function(path) {
  l <- trimws(readLines(path, warn = FALSE, encoding = "UTF-8"))
  l <- sub("^\\ufeff", "", l)
  l <- l[nzchar(l) & !startsWith(l, "#")]
  parts <- lapply(strsplit(l, "[\t,]"), trimws)
  if (length(parts) && tolower(parts[[1]][1]) == "gene") parts <- parts[-1]
  genes <- vapply(parts, `[`, "", 1)
  has_w <- length(parts) > 0 && all(vapply(parts, function(p) length(p) >= 2 && nzchar(p[2]), NA))
  list(genes = genes, weights = if (has_w) as.numeric(vapply(parts, `[`, "", 2)) else NULL)
}

## Run a sigscores call, keeping its warnings and messages, and detect the output
## sink that sigscores leaves open when GSVA fails (finding gsva-sink).
sigshell_capture <- function(expr) {
  w <- character(); m <- character(); n0 <- sink.number()
  value <- withCallingHandlers(expr,
    warning = function(c) { w <<- c(w, conditionMessage(c)); invokeRestart("muffleWarning") },
    message = function(c) { m <<- c(m, trimws(conditionMessage(c))); invokeRestart("muffleMessage") })
  left_open <- sink.number() > n0
  while (sink.number() > n0) sink()
  list(value = value, warnings = unique(trimws(w)), messages = unique(m), sink_left_open = left_open)
}

## A score that is NA for every sample usually means its scorer failed: sigscores
## replaces errors with NA (finding silent-na). Call the scorer directly, the way
## computeScores does (R/5-scorers.R:1174 and :1198), to recover the error message.
sigshell_explain_all_na <- function(scores, x, i, na.rm, args) {
  out <- list()
  for (s in setdiff(names(scores), c("sampleID", "run"))) {
    if (!all(is.na(scores[[s]]))) next
    rows <- if (is.null(i)) seq_len(nrow(x)) else match(i, rownames(x))
    r <- sigshell_capture(tryCatch({
      do.call(getScorer(s), c(list(x = x, i = rows, na.rm = na.rm), args[[s]]))
      "the scorer returned NA without raising an error"
    }, error = function(e) conditionMessage(e)))
    out[[s]] <- r$value
  }
  out
}

sigshell_save_result <- function(step, x) {
  jsonlite::write_json(x, sprintf("outputs/%s-result.json", step), auto_unbox = TRUE,
                       digits = NA, na = "null", null = "null", dataframe = "columns")
}

sigshell_versions <- function() {
  pk <- c("sigscores", "GSVA", "matrixStats", "ggplot2", "ComplexHeatmap", "circlize", "psych", "jsonlite")
  list(R = R.version.string, platform = R.version$platform,
       packages = lapply(setNames(pk, pk), function(p) if (requireNamespace(p, quietly = TRUE)) as.character(utils::packageVersion(p)) else NA))
}
