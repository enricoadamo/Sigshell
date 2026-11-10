## Check that the installed sigscores is the pinned source, and report versions.
## Usage: Rscript check_install.R <sigscores source dir> <output json>
args <- commandArgs(trailingOnly = TRUE)
src <- args[1]; out <- args[2]
ok <- requireNamespace("sigscores", quietly = TRUE)
mismatch <- character(); n <- 0L
if (ok) {
  ns <- asNamespace("sigscores")
  for (f in list.files(file.path(src, "R"), pattern = "[.]R$", full.names = TRUE)) {
    for (e in parse(f, keep.source = FALSE)) {
      if (!(is.call(e) && as.character(e[[1]])[1] %in% c("<-", "=") && is.name(e[[2]]))) next
      rhs <- e[[3]]
      if (!(is.call(rhs) && identical(rhs[[1]], as.name("function")))) next
      n <- n + 1L
      nm <- as.character(e[[2]])
      g <- get0(nm, envir = ns, inherits = FALSE)
      same <- is.function(g) &&
        identical(deparse(rhs[[3]]), deparse(body(g))) &&
        identical(deparse(as.list(rhs[[2]])), deparse(as.list(formals(g))))
      if (!same) mismatch <- c(mismatch, nm)
    }
  }
}
pk <- c("sigscores", "GSVA", "matrixStats", "ggplot2", "ComplexHeatmap", "circlize", "psych", "jsonlite")
methods <- if (ok) list(
  scores = sigscores::getAvailableScores(),
  transformers = sigscores::getAvailableDataTransformers(),
  samplers = sigscores::getAvailableRandomSamplers()
) else NULL
jsonlite::write_json(list(
  installed = ok, functions_checked = n, mismatched = mismatch, methods = methods,
  R = R.version.string, platform = R.version$platform,
  packages = lapply(setNames(pk, pk), function(p) if (requireNamespace(p, quietly = TRUE)) as.character(utils::packageVersion(p)) else NA)
), out, auto_unbox = TRUE, null = "null", na = "null")
