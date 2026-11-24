"""Drive Sigshell's MCP server over stdio the way Claude does, with a fixed list of calls and no AI.

It runs the sigscores vignette example from start to finish, writes what a client sees for each
call to transcript.md, then replays the session's session.R with plain Rscript in a fresh copy and
checks that it writes the same tables, byte for byte.

Usage, from the repository root (needs R and the pinned sigscores):
    uv run python examples/run_example.py <output folder>
"""

from __future__ import annotations

import asyncio
import filecmp
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from sigshell import config

MATRIX, SIGNATURE = "vignette-matrix.csv", "vignette-signature.txt"


def _text(result) -> str:
    parts = []
    for c in result.content:
        if getattr(c, "type", None) == "text":
            parts.append(c.text)
        elif getattr(c, "type", None) == "image":
            parts.append(f"[image: {c.mime_type}, {len(c.data) * 3 // 4} bytes]")
    return "\n".join(parts)


def _structured(result) -> dict:
    return getattr(result, "structured_content", None) or getattr(result, "structuredContent", None) or {}


async def run(out: Path) -> Path:
    data, sessions = out / "data", out / "sessions"
    data.mkdir(parents=True)
    rscript = config.find_rscript()
    subprocess.run([rscript, "--vanilla", str(config.R_DIR / "vignette_example.R")], cwd=data, check=True)

    env = {"SIGSHELL_HOME": str(out), "SIGSHELL_DATA": str(data), "SIGSHELL_SESSIONS": str(sessions),
           "SIGSCORES_SRC": str(config.SIGSCORES_SRC)}
    if os.environ.get("SIGSHELL_RSCRIPT"):
        env["SIGSHELL_RSCRIPT"] = os.environ["SIGSHELL_RSCRIPT"]
    params = StdioServerParameters(command=sys.executable, args=["-m", "sigshell.server"], env=env, cwd=str(config.REPO_ROOT))

    log = ["# Sigshell over MCP: the sigscores vignette example", "",
           "Every call below went to `sigshell-server` over stdio, as an MCP client such as Claude sends it.",
           "The text is what the client received; images are listed by size.", ""]
    async with Client(params, read_timeout_seconds=1800) as client:
        tools = await client.list_tools()
        log += ["## Tools offered", "", ", ".join(f"`{t.name}`" for t in tools.tools), ""]

        async def call(name: str, args: dict) -> dict:
            result = await client.call_tool(name, args)
            failed = bool(getattr(result, "is_error", None) or getattr(result, "isError", None))
            log.extend([f"## `{name}`", "", "```json", json.dumps(args, indent=2), "```", "",
                        "**Error:**" if failed else "**Result:**", "", _text(result), ""])
            if failed:
                raise SystemExit(f"{name} failed:\n{_text(result)}")
            return _structured(result)

        inputs = {"matrix_file": MATRIX, "signature_file": SIGNATURE}
        await call("find_data_files", {})
        await call("check_inputs", inputs)
        scores = await call("compute_scores", inputs | {
            "scores": ["mean", "median", "midrange", "iqm", "mad", "ssgsea", "gsva", "plage", "zscore"],
            "expression_scale": "other"})
        for kind in ("heatmap", "correlation", "boxplot", "scatter"):
            await call("plot_scores", {"result_id": scores["result_id"], "kind": kind})
        sig = await call("test_significance", inputs | {
            "scores": ["mean", "median"], "null": "random_genes", "n_repeat": 1000, "seed": 1, "expression_scale": "other"})
        await call("plot_null_distribution", {"result_id": sig["result_id"], "sample": "S1", "score": "mean"})
        await call("get_r_script", {})

    (out / "transcript.md").write_text("\n".join(log), encoding="utf-8")
    (session,) = [p for p in sessions.iterdir() if p.is_dir()]
    return session


def replay(session: Path, out: Path) -> list[str]:
    """Run session.R in a copy without outputs/ and compare every table it writes."""
    copy = out / "replay"
    shutil.copytree(session, copy, ignore=shutil.ignore_patterns("outputs"))
    (copy / "outputs").mkdir()
    subprocess.run([config.find_rscript(), "--vanilla", "session.R"], cwd=copy, check=True, capture_output=True)
    tables = sorted(p.name for p in (session / "outputs").glob("*.csv"))
    differ = [name for name in tables if not filecmp.cmp(session / "outputs" / name, copy / "outputs" / name, shallow=False)]
    shutil.rmtree(copy)
    print(f"session.R rewrote {len(tables)} tables; identical: {len(tables) - len(differ)}; different: {differ or 'none'}")
    return differ


def main() -> None:
    out = Path(sys.argv[1]).resolve()
    if out.exists():
        raise SystemExit(f"{out} already exists.")
    session = asyncio.run(run(out))
    print(f"Session written to {session}")
    if replay(session, out):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
