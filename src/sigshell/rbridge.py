"""Run R: generate R literals, run step scripts in fresh Rscript processes, check the installation."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import config


class RError(Exception):
    """R stopped with an error, or could not be run."""


class RCode(str):
    """A fragment of R code, inserted into a script as is."""


def _name(key: str) -> str:
    import re

    return key if re.fullmatch(r"[A-Za-z.][A-Za-z0-9._]*", key) else "`" + key.replace("`", "\\`") + "`"


def r_literal(value: Any) -> str:
    """Write a Python value as R source that evaluates to the same value."""
    if isinstance(value, RCode):
        return str(value)
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return f"{value}L" if abs(value) < 2**31 else repr(float(value))
    if isinstance(value, float):
        return repr(value) if value == value else "NA_real_"
    if isinstance(value, str):
        esc = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
        return f'"{esc}"'
    if isinstance(value, dict):
        return "list(" + ", ".join(f"{_name(str(k))} = {r_literal(v)}" for k, v in value.items()) + ")"
    if isinstance(value, (list, tuple)):
        items = list(value)
        if items and all(isinstance(v, (str, bool, int, float)) and not isinstance(v, RCode) for v in items):
            kinds = {type(v) for v in items}
            if kinds <= {int, float} or len(kinds) == 1:
                return "c(" + ", ".join(r_literal(float(v) if kinds == {int, float} else v) for v in items) + ")"
        return "list(" + ", ".join(r_literal(v) for v in items) + ")"
    raise TypeError(f"cannot write {type(value).__name__} as R")


def preamble() -> str:
    return (config.R_DIR / "preamble.R").read_text(encoding="utf-8")


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("LANG", "en_US.UTF-8")
    env["SIGSCORES_SRC"] = str(config.SIGSCORES_SRC)
    return env


def _error_text(stderr: str) -> str:
    lines = [ln for ln in stderr.strip().splitlines() if ln.strip()]
    start = next((i for i, ln in enumerate(lines) if ln.startswith("Error")), None)
    tail = lines[start:] if start is not None else lines[-8:]
    return "\n".join(ln for ln in tail if not ln.startswith("Execution halted"))


async def run_script(script: Path, cwd: Path, timeout: float = config.R_TIMEOUT) -> tuple[str, str]:
    """Run an R script with Rscript in a fresh process. Raises RError on failure."""
    rscript = config.find_rscript()
    if rscript is None:
        raise RError("Rscript was not found. Install R, or set SIGSHELL_RSCRIPT to the full path of Rscript.")
    proc = await asyncio.create_subprocess_exec(
        rscript, "--vanilla", str(script), cwd=str(cwd), env=_env(),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise RError(f"R did not finish within {timeout:.0f} seconds and was stopped.")
    stdout, stderr = out.decode("utf-8", "replace"), err.decode("utf-8", "replace")
    if proc.returncode != 0:
        raise RError(_error_text(stderr) or f"R exited with status {proc.returncode}.")
    return stdout, stderr


@dataclass
class Installation:
    commit: str
    versions: dict[str, Any]
    methods: dict[str, Any]

    @property
    def line(self) -> str:
        p = self.versions["packages"]
        return (
            f"sigscores {p['sigscores']} (commit {self.commit[:7]}), {self.versions['R']} on {self.versions['platform']}; "
            f"GSVA {p['GSVA']}, matrixStats {p['matrixStats']}, ggplot2 {p['ggplot2']}, ComplexHeatmap {p['ComplexHeatmap']}"
        )

    def ids(self, kind: str) -> list[str]:
        """Ids sigscores itself lists for "scores", "transformers" or "samplers"."""
        return [row["id"] for row in self.methods[kind]]


_installation: Installation | None = None


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(config.SIGSCORES_SRC), *args], capture_output=True, text=True, check=True).stdout.strip()


async def installation() -> Installation:
    """Verify, once per server process, that R runs and the installed sigscores is the pinned commit."""
    global _installation
    if _installation is not None:
        return _installation
    src = config.SIGSCORES_SRC
    if not (src / "DESCRIPTION").exists():
        raise RError(f"The sigscores source was not found at {src}. Set SIGSCORES_SRC to a checkout of commit {config.EXPECTED_COMMIT[:7]}.")
    try:
        head = _git("rev-parse", "HEAD")
        dirty = _git("status", "--porcelain", "--untracked-files=no")
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise RError(f"Could not read the sigscores commit with git in {src}: {exc}")
    if head != config.EXPECTED_COMMIT:
        raise RError(f"sigscores at {src} is at commit {head[:7]}, but Sigshell is verified against {config.EXPECTED_COMMIT[:7]}. Check out that commit and reinstall it.")
    if dirty:
        raise RError(f"The sigscores checkout at {src} has local changes; Sigshell only runs the unmodified pinned commit.")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "install.json"
        rscript = config.find_rscript()
        if rscript is None:
            raise RError("Rscript was not found. Install R, or set SIGSHELL_RSCRIPT to the full path of Rscript.")
        proc = await asyncio.create_subprocess_exec(
            rscript, "--vanilla", str(config.R_DIR / "check_install.R"), str(src), str(out),
            env=_env(), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        _, err = await asyncio.wait_for(proc.communicate(), timeout=300)
        if proc.returncode != 0 or not out.exists():
            raise RError("R could not check the sigscores installation:\n" + _error_text(err.decode("utf-8", "replace")))
        info = json.loads(out.read_text())
    if not info["installed"]:
        raise RError(f"The sigscores R package is not installed. Install it with: R CMD INSTALL {src}")
    if info["mismatched"] or info["functions_checked"] == 0:
        raise RError(
            "The installed sigscores differs from the pinned source in: "
            + ", ".join(info["mismatched"][:10])
            + f". Reinstall it with: R CMD INSTALL {src}"
        )
    _installation = Installation(head, {"R": info["R"], "platform": info["platform"], "packages": info["packages"]}, info["methods"])
    return _installation
