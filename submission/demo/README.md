# Sigshell demonstration material

These files use the synthetic example in the sigscores vignette. The matrix has
100 genes and 10 samples; the signature contains 20 sampled genes. The seed is
5381. The numbers are arbitrary and should not be interpreted biologically.

- `vignette-matrix.csv` and `vignette-signature.txt`: inputs suitable for the
  browser upload fields. The same inputs can be generated with the page's
  **Try the example from the sigscores vignette** button.
- `workbench.png`: screenshot of the local browser interface.
- `sample-session/outputs/001-scores.csv`: per-sample mean and median scores.
  S1 is 666.55 and 736.5; S2 is 614 and 623.
- `sample-session/outputs/002-boxplot.png`: a plot made through the page.
- `sample-session/session.R`, `inputs/`, `steps/`, and `provenance.json`: a
  replayable session. With the pinned R dependencies installed, run
  `Rscript session.R` from inside `sample-session/`.

The separately shared video demo is at:
https://drive.google.com/file/d/1ICPxVu_TY1JgsI8G86Ytw-A2lHF6SIvg/view?usp=sharing

Before submitting the link, open it in a private browser window to verify that
the course staff can view it. The video shows the same vignette example.
