## The simulated data of the sigscores vignette (vignettes/sigscores.Rmd at commit 40f55c5,
## chunks set_seed, create_data and create_data_signature), written to the working directory.
## Same seed and same calls, so the scores match the published vignette.
set.seed(seed = 5381L, kind = "Mersenne-Twister", normal.kind = "Inversion")
nc = 10
nr = 100
x = matrix(
  data = sample(x = nr*nc),
  nrow = nr,
  ncol = nc,
  dimnames = list(paste0("g", seq_len(nr)), paste0("S", seq_len(nc)))
)
ng = 20
signature = rownames(x)[sample(x = seq_len(nr), size = ng)]
utils::write.csv(x, "vignette-matrix.csv")
writeLines(signature, "vignette-signature.txt")
