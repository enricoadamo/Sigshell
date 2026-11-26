"""Paths and constants. Every path can be overridden with an environment variable."""

import os
import shutil
from pathlib import Path

# The sigscores commit Sigshell is built and verified against.
EXPECTED_COMMIT = "40f55c5cd1ab03153be40fa25e37723fdd64bacc"

REPO_ROOT = Path(__file__).resolve().parents[2]

# Checkout of sigscores at EXPECTED_COMMIT; used to verify the installed package and to serve the vignette.
SIGSCORES_SRC = Path(os.environ.get("SIGSCORES_SRC", REPO_ROOT.parent / "sigscores")).expanduser().resolve()

# Where the biologist keeps input files and where sessions are written.
HOME = Path(os.environ.get("SIGSHELL_HOME", Path.home() / "Sigshell")).expanduser()
DATA_DIR = Path(os.environ.get("SIGSHELL_DATA", HOME / "data")).expanduser()
SESSIONS_DIR = Path(os.environ.get("SIGSHELL_SESSIONS", HOME / "sessions")).expanduser()

PAPER_CITATION = (
    "Barberis A, Buffa FM. Sigscores: summary scores for molecular signatures in R. "
    "Bioinformatics Advances. 2026;6(1):vbag021. https://doi.org/10.1093/bioadv/vbag021. "
    "Licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)."
)
R_DIR = Path(__file__).resolve().parent / "r"

# Seconds an R step may run before it is stopped.
R_TIMEOUT = float(os.environ.get("SIGSHELL_R_TIMEOUT", "1800"))


def find_rscript() -> str | None:
    """Locate Rscript. Claude Desktop starts servers with a short PATH, so common install locations are tried too."""
    explicit = os.environ.get("SIGSHELL_RSCRIPT")
    if explicit:
        return explicit
    found = shutil.which("Rscript")
    if found:
        return found
    for candidate in (
        "/usr/local/bin/Rscript",
        "/opt/homebrew/bin/Rscript",
        "/Library/Frameworks/R.framework/Resources/bin/Rscript",
        "/usr/bin/Rscript",
    ):
        if Path(candidate).exists():
            return candidate
    return None
