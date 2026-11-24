# Using the local workbench

1. Start `uv run sigshell-ui` and open its printed localhost address.
2. Upload a `.csv` matrix or a tab-separated `.tsv`/`.txt` matrix. Genes go in
   rows, samples in columns, with gene IDs in the first column. Upload a
   signature with one gene ID per line; an optional numeric weight may follow
   each gene after a tab or comma.
3. Declare the matrix scale and review the input report. Sigshell records the
   scale as context; it does not normalize the data. For raw counts, normalize
   appropriately before comparing samples.
4. Choose scoring methods. **Recommended start: mean + median** is a simple
   first comparison. The app will explain when a method needs cleaner input.
5. Compute and inspect the table, notes, and plots. Download the full precision
   CSV or RDS. Methods may have different units, so do not compare heatmap colors
   across methods as though they were on one common scale.
6. Optional: test a score against random gene sets. Choose the null model, number
   of random scores, and seed. The achieved significance level refers to that
   null within one sample; it is not a comparison between sample groups. The
   intervals describe the null scores, not uncertainty in the observed score.
7. Open **Reproduce** to inspect `session.R` or download the whole session ZIP.
   Unzip it and run `Rscript session.R` from inside that folder with the same
   sigscores and R environment. The ZIP includes staged inputs, outputs, and
   `provenance.json`.

The **Try the example from the sigscores vignette** button generates synthetic
data with seed 5381. Its 100 genes and 20-gene signature are for checking the
workflow, not for biological interpretation. Sigshell never changes an uploaded
file in place; explicit matrix preparation writes a new copy.
