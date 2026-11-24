"""Every finding in findings/findings.json is still reproduced by findings/reproduce.R.

Each finding runs in its own fresh R process and must print CONFIRMED. The server's guards rest
on these findings (DESIGN.md section 5), so a finding that stops reproducing means a guard must be
checked again. Skipped when R or the pinned sigscores is not available.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess

import pytest

from sigshell import config, rbridge

FINDINGS = config.REPO_ROOT / "findings"
IDS = [f["id"] for f in json.loads((FINDINGS / "findings.json").read_text(encoding="utf-8"))["findings"]]


def _r_available() -> bool:
    try:
        asyncio.run(rbridge.installation())
    except rbridge.RError:
        return False
    return True


pytestmark = pytest.mark.skipif(not _r_available(), reason="R with the pinned sigscores is not available")


def _reproduce(*args: str) -> str:
    env = os.environ | {"SIGSCORES_SRC": str(config.SIGSCORES_SRC)}
    done = subprocess.run([config.find_rscript(), "--vanilla", str(FINDINGS / "reproduce.R"), *args],
                          cwd=config.REPO_ROOT, env=env, capture_output=True, text=True, timeout=300, check=False)
    return done.stdout


def test_every_finding_has_a_reproduction():
    assert sorted(_reproduce("--list").split()) == sorted(IDS)


@pytest.mark.parametrize("finding", IDS)
def test_finding_is_confirmed(finding):
    line = _reproduce(finding).strip().splitlines()[-1]
    fid, verdict, evidence = line.split("\t", 2)
    assert (fid, verdict) == (finding, "CONFIRMED"), evidence
