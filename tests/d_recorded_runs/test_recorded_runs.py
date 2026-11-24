"""Replay the 184 recorded runs of the call map in fresh R processes and compare with what was recorded.

Each run goes through replay.R (the original harness: options(width = 72, digits = 4), set.seed(1),
one fresh Rscript per run). Printed output, warnings, messages, errors and leftover sinks must all
match. Run 16 prints logger timestamps, so its times are normalised before comparing.
Skipped when R or the pinned sigscores is not available.
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from sigshell import config, rbridge

HERE = Path(__file__).parent
FIXTURE = HERE / "recorded-runs.json"
RUNS = json.loads(FIXTURE.read_text(encoding="utf-8"))["runs"]
TIME = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+")


def _r_available() -> bool:
    try:
        asyncio.run(rbridge.installation())
    except rbridge.RError:
        return False
    return True


pytestmark = pytest.mark.skipif(not _r_available(), reason="R with the pinned sigscores is not available")


@pytest.fixture(scope="module")
def replayed(tmp_path_factory) -> dict[int, dict]:
    out = tmp_path_factory.mktemp("replay")
    rscript = config.find_rscript()

    def one(k: int) -> None:
        subprocess.run([rscript, "--vanilla", str(HERE / "replay.R"), str(k), str(FIXTURE), str(out)],
                       cwd=out, capture_output=True, timeout=300, check=False)

    with ThreadPoolExecutor() as pool:
        list(pool.map(one, range(1, len(RUNS) + 1)))
    results = {}
    for k in range(1, len(RUNS) + 1):
        f = out / f"{k:03d}.json"
        results[k] = json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
    return results


@pytest.mark.parametrize("k", range(1, len(RUNS) + 1), ids=[f"{k:03d}-{r['fn']}" for k, r in enumerate(RUNS, 1)])
def test_run_matches_the_recording(replayed, k):
    rec, got = RUNS[k - 1], replayed[k]
    assert got is not None, "replay.R wrote no result"
    out, expected = got["out"], rec["out"]
    if rec["compare"] == "timestamps-normalised":
        out, expected = TIME.sub("<time>", out), TIME.sub("<time>", expected)
    assert out == expected
    assert got["warn"] == rec["warn"]
    assert got["msg"] == rec["msg"]
    assert got["err"] == rec["err"]
    assert got["stuck"] == rec["stuck"]
