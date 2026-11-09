# Sigshell

A natural-language shell for biologists over the [sigscores](https://github.com/alebarberis/sigscores) R package.
Software Engineering course project by Enrico and Marco. Submission: Fri 27 Nov 2026.

## The library we wrap

- Upstream: <https://github.com/alebarberis/sigscores> (GPL-3)
- We analyse and wrap commit [`40f55c5`](https://github.com/alebarberis/sigscores/commit/40f55c5cd1ab03153be40fa25e37723fdd64bacc) (`main`, 29 Jun 2025). The [package website](https://alebarberis.github.io/sigscores) was built from this exact commit, so the code matches its documented examples.

```sh
git clone https://github.com/alebarberis/sigscores.git
cd sigscores
git checkout 40f55c5
```

We never edit sigscores itself. If we find a bug, we report it upstream.

## Working together

- `main` must always work. Work on a branch named `enrico/<topic>` or `marco/<topic>`.
- Open a pull request; the other person reviews and merges it.
- Run `git pull` before you start.

## Licence

sigscores is GPL-3. This repo stays private until we choose sigshell's own licence.
