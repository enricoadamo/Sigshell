"""Plain-language descriptions of what sigscores offers, with the caveats Sigshell found.

The ids and full names come from sigscores itself (getAvailableScores and friends, run by
r/check_install.R); this module only adds explanations.
"""

SCORES = {
    "sum": "Adds the signature genes' values in each sample. Grows with the number of genes.",
    "weightedSum": "Adds the signature genes' values after multiplying each by its weight (from the signature file). Without weights it equals sum.",
    "mean": "Average of the signature genes' values in each sample.",
    "trimmedMean": "Average after dropping a fraction of the lowest and highest values (option trim, default 0, which equals the mean). Transforms after selecting the signature genes.",
    "weightedMean": "Average weighted by the signature file's weights. Without weights it equals mean.",
    "median": "Middle value of the signature genes in each sample.",
    "mode": "Most frequent value; ties go to the smallest value. On continuous data with no repeated values this is simply the minimum.",
    "midrange": "Average of the lowest and highest value.",
    "midhinge": "Average of the first and third quartiles.",
    "trimean": "Average of the median and the midhinge.",
    "iqr": "Interquartile range: third quartile minus first. Measures spread, not level.",
    "iqm": "Mean of the middle half of the sorted values. NA when fewer than 4 genes.",
    "mad": "Median absolute deviation, multiplied by 1.4826 (the default of R's stats::mad). Measures spread.",
    "aad": "Mean absolute deviation around the median. Measures spread. Transforms after selecting the signature genes.",
    "ssgsea": "Single-sample gene set enrichment score, computed by GSVA. Depends on the whole matrix, not only the signature genes.",
    "gsva": "Gene set variation analysis score, computed by GSVA. Depends on the whole matrix.",
    "plage": "PLAGE: first singular vector of the signature genes, computed by GSVA. Its sign is arbitrary, so it can correlate negatively with the other scores.",
    "zscore": "Combined z-score of Lee et al. (2008), computed by GSVA.",
}

GSVA_SCORES = ("ssgsea", "gsva", "plage", "zscore")
TRANSFORM_AFTER_SUBSET = ("trimmedMean", "aad")
WEIGHTED = ("weightedSum", "weightedMean")

TRANSFORMERS = {
    "stepFunction": "Replaces each value with -1, 0 or 1 depending on whether it is below, equal to or above a threshold. By default the threshold is each gene's median across samples (options: method, by, thr, y).",
    "quantile": "Quantile normalisation: makes every sample's distribution identical (options: ties_method). Refused when any gene has missing values, because sigscores then scores the wrong rows.",
    "z": "Z-standardisation of each gene across samples: subtract the mean, divide by the standard deviation. Only by='rows' with robust=false is offered: the other settings are wrong in sigscores.",
}

NULL_MODELS = {
    "random_genes": "Scores random gene sets of the same size as the signature, drawn from all genes in the matrix (sigscores sampling = 'rndsig').",
    "permutation": "Shuffles which gene name belongs to which row, then scores the signature (sigscores sampling = 'permutation'). This is statistically the same null as random_genes.",
    "bootstrap": "Like permutation but rows are drawn with replacement, so a random set can contain a gene twice (sigscores sampling = 'bootstrap'). It does not measure the uncertainty of the observed score.",
}

NOT_OFFERED = {
    "rndsigsub": "Random gene sets excluding the signature's genes. Not offered: sigscores excludes the first rows of the matrix instead of the signature's genes.",
}
