"""Sigshell's local web page: the MCP server's tools behind a form instead of a chat.

`sigshell-ui` serves the page at http://127.0.0.1:<port>. Every analysis goes through
`server.call_tool`, the same entry point an MCP client uses, so the page gets the same
argument validation, guards, R step scripts, session folder and provenance. This module
computes no numbers: it only moves files and passes arguments through.

The page is reachable only from this computer. Requests with any Host other than
127.0.0.1 or localhost are refused (this blocks DNS rebinding). POST requests must carry an
X-Sigshell header, which a page on another site can't send without a CORS preflight that
this server never answers.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import re
import socket
import threading
import webbrowser
import zipfile
from pathlib import Path
from typing import Any

import uvicorn
from mcp.server.mcpserver.exceptions import ToolError
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import config, methods, rbridge, server
from .session import Session

STATIC = Path(__file__).resolve().parent / "web"
SPREAD_SCORES = ("iqr", "mad", "aad")
INPUT_SUFFIXES = (".csv", ".tsv", ".txt")
MAX_UPLOAD_BYTES = 500 * 1024 * 1024

# The arguments the page may pass to each tool. Anything else is dropped before validation.
TOOLS: dict[str, tuple[str, ...]] = {
    "check_inputs": ("matrix_file", "signature_file"),
    "prepare_matrix": ("matrix_file", "remove_constant_genes", "remove_genes_with_missing_values"),
    "compute_scores": ("matrix_file", "signature_file", "scores", "transform", "trim", "na_rm", "drop_missing_genes"),
    "test_significance": ("matrix_file", "signature_file", "scores", "null", "n_repeat", "seed", "alternative", "conf_level",
                          "transform", "trim", "na_rm", "drop_missing_genes"),
    "plot_scores": ("result_id", "kind", "scores"),
    "plot_null_distribution": ("result_id", "sample", "score", "bins"),
    "get_r_script": (),
}

# One analysis at a time: the session numbers its steps in order, and R runs one step at a time anyway.
_lock = asyncio.Lock()


# ---------------------------------------------------------------- helpers

def _error(message: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


def _from_page(request: Request) -> bool:
    return request.headers.get("x-sigshell") == "1"


def _clean(message: str) -> str:
    """Drop the SDK's wrapper text and pydantic's documentation links from an error message."""
    message = re.sub(r"^Error executing tool \w+: ", "", message)
    return "\n".join(ln for ln in message.splitlines() if "errors.pydantic.dev" not in ln).strip()


def _session_url(path: str | Path) -> str | None:
    """The /files/ URL of a file in the session folder, or None if it lies outside it."""
    base = server.session.started
    if base is None:
        return None
    p = Path(path)
    p = p if p.is_absolute() else base / p
    try:
        rel = p.resolve().relative_to(base.resolve())
    except ValueError:
        return None
    return "/files/" + rel.as_posix()


def _step_files(step: str | None) -> list[dict[str, str]]:
    """The output files a step wrote (CSV, RDS, PNG), for download links."""
    base = server.session.started
    if not step or base is None:
        return []
    out = []
    for p in sorted((base / "outputs").glob(f"{step}-*")):
        if p.name.endswith("-result.json"):
            continue
        out.append({"name": p.name, "url": _session_url(p) or ""})
    return out


def _safe_name(filename: str) -> str:
    name = Path(filename.replace("\\", "/")).name
    stem, suffix = Path(name).stem, Path(name).suffix.lower()
    if suffix not in INPUT_SUFFIXES:
        raise ValueError(
            f"{name or 'This file'}: Sigshell reads .csv (comma-separated) and .tsv or .txt (tab-separated) files. "
            "If the table is in Excel, use File > Save As > CSV first."
        )
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-") or "file"
    return stem + suffix


def _store(folder: Path, name: str, data: bytes) -> str:
    """Save data as folder/name. A different file with that name is kept: the new one gets a -2, -3, … suffix."""
    folder.mkdir(parents=True, exist_ok=True)
    stem, suffix = Path(name).stem, Path(name).suffix
    k = 1
    while True:
        candidate = folder / (name if k == 1 else f"{stem}-{k}{suffix}")
        if not candidate.exists():
            candidate.write_bytes(data)
            return candidate.name
        if candidate.read_bytes() == data:
            return candidate.name
        k += 1


def _callmap_path() -> Path | None:
    for p in (config.CALLMAP_HTML, config.REPO_ROOT.parent / "reference" / "sigscores-call-map.html"):
        if p.exists():
            return p
    return None


def _score_group(score_id: str) -> str:
    if score_id in methods.GSVA_SCORES:
        return "gsva"
    return "spread" if score_id in SPREAD_SCORES else "level"


# ---------------------------------------------------------------- endpoints

async def index(request: Request) -> Response:
    return FileResponse(STATIC / "index.html", headers={
        "Cache-Control": "no-store",
        "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'",
    })


async def status(request: Request) -> JSONResponse:
    out: dict[str, Any] = {
        "data_dir": str(config.DATA_DIR),
        "session": str(server.session.started) if server.session.started else None,
        "callmap": _callmap_path() is not None,
        "paper": config.PAPER_PDF.exists(),
        "citation": config.PAPER_CITATION,
    }
    try:
        inst = await rbridge.installation()
    except rbridge.RError as exc:
        return JSONResponse({**out, "ok": False, "error": str(exc)})
    return JSONResponse({**out, "ok": True, "provenance": inst.line, "commit": inst.commit})


async def list_methods(request: Request) -> JSONResponse:
    try:
        inst = await rbridge.installation()
    except rbridge.RError as exc:
        return _error(f"Sigshell can't run sigscores yet: {exc}", 503)
    scores = [{"id": r["id"], "name": r["name"], "description": methods.SCORES.get(r["id"], ""), "group": _score_group(r["id"]),
               "weighted": r["id"] in methods.WEIGHTED} for r in inst.methods["scores"]]
    transformers = [{"id": r["id"], "name": r["name"], "description": methods.TRANSFORMERS.get(r["id"], "")}
                    for r in inst.methods["transformers"]]
    nulls = [{"id": k, "description": v} for k, v in methods.NULL_MODELS.items()]
    return JSONResponse({"scores": scores, "transformers": transformers, "null_models": nulls,
                         "not_offered": list(methods.NOT_OFFERED.values())})


async def list_files(request: Request) -> JSONResponse:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    return JSONResponse({"data_dir": str(config.DATA_DIR), "files": server.data_files(config.DATA_DIR)})


async def upload(request: Request) -> JSONResponse:
    if not _from_page(request):
        return _error("Uploads are only accepted from the Sigshell page.", 403)
    if int(request.headers.get("content-length") or 0) > MAX_UPLOAD_BYTES:
        return _error(f"The file is larger than {MAX_UPLOAD_BYTES // 2**20} MB.", 413)
    form = await request.form(max_files=1, max_fields=1)
    try:
        item = form.get("file")
        if item is None or isinstance(item, str):
            return _error("No file was sent.")
        try:
            name = _safe_name(item.filename or "")
        except ValueError as exc:
            return _error(str(exc))
        data = await item.read()
    finally:
        await form.close()
    if not data.strip():
        return _error(f"{name} is empty.")
    stored = _store(config.DATA_DIR, name, data)
    return JSONResponse({"name": stored, "renamed": stored != name})


async def example(request: Request) -> JSONResponse:
    """Write the sigscores vignette's simulated matrix and signature into the data folder, generated by R."""
    if not _from_page(request):
        return _error("Only the Sigshell page can do this.", 403)
    names = {"matrix": "vignette-matrix.csv", "signature": "vignette-signature.txt"}
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not all((config.DATA_DIR / n).exists() for n in names.values()):
        try:
            await rbridge.run_script(config.R_DIR / "vignette_example.R", config.DATA_DIR, timeout=120)
        except rbridge.RError as exc:
            return _error(f"R could not write the example data: {exc}", 503)
    return JSONResponse(names)


async def call(request: Request) -> JSONResponse:
    name = request.path_params["name"]
    if name not in TOOLS:
        return _error(f"Unknown tool {name}.", 404)
    if not _from_page(request):
        return _error("Analyses can only be started from the Sigshell page.", 403)
    try:
        body = await request.json()
    except ValueError:
        return _error("The request was not valid JSON.")
    if not isinstance(body, dict):
        return _error("The request must be a JSON object.")
    arguments = {k: v for k, v in body.items() if k in TOOLS[name] and v is not None}
    async with _lock:
        try:
            result = await server.server.call_tool(name, arguments)
        except ToolError as exc:
            return _error(_clean(str(exc)), 422)
        except Exception as exc:  # noqa: BLE001 - shown to the user, who can report it
            cause = exc.__cause__ or exc
            return _error(f"Sigshell hit an unexpected error ({type(cause).__name__}): {_clean(str(cause))}", 500)
    text = "\n".join(c.text for c in result.content if getattr(c, "type", None) == "text")
    data = result.structured_content or {}
    step = (result.meta or {}).get("step")
    out: dict[str, Any] = {"text": text, "data": data, "step": step, "files": _step_files(step),
                           "session": str(server.session.started) if server.session.started else None}
    if isinstance(data.get("file"), str):
        out["url"] = _session_url(data["file"])
    if name == "get_r_script" and isinstance(data.get("path"), str):
        out["script"] = Path(data["path"]).read_text(encoding="utf-8")
    return JSONResponse(out)


async def new_session(request: Request) -> JSONResponse:
    if not _from_page(request):
        return _error("Only the Sigshell page can do this.", 403)
    async with _lock:
        server.session = Session()
    return JSONResponse({"session": None})


async def session_file(request: Request) -> Response:
    base = server.session.started
    if base is None:
        return _error("Nothing has run in this session yet.", 404)
    path = (base / request.path_params["path"]).resolve()
    if not path.is_relative_to(base.resolve()) or not path.is_file():
        return _error("No such file in this session.", 404)
    if path.name == "session.R":
        server.session.refresh_script()
    return FileResponse(path, headers={"Cache-Control": "no-store"})


async def session_zip(request: Request) -> Response:
    base = server.session.started
    if base is None:
        return _error("Nothing has run in this session yet.", 404)
    server.session.refresh_script()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(base.rglob("*")):
            if p.is_file():
                z.write(p, (Path(f"sigshell-session-{base.name}") / p.relative_to(base)).as_posix())
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="sigshell-session-{base.name}.zip"'})


async def callmap(request: Request) -> Response:
    path = _callmap_path()
    if path is None:
        return _error("The call map is not in this copy of Sigshell.", 404)
    return FileResponse(path, media_type="text/html")


async def paper(request: Request) -> Response:
    if not config.PAPER_PDF.exists():
        return _error("The paper is not in this copy of Sigshell.", 404)
    return FileResponse(config.PAPER_PDF, media_type="application/pdf")


app = Starlette(
    routes=[
        Route("/", index),
        Route("/api/status", status),
        Route("/api/methods", list_methods),
        Route("/api/files", list_files),
        Route("/api/upload", upload, methods=["POST"]),
        Route("/api/example", example, methods=["POST"]),
        Route("/api/tool/{name}", call, methods=["POST"]),
        Route("/api/new-session", new_session, methods=["POST"]),
        Route("/files/{path:path}", session_file),
        Route("/session.zip", session_zip),
        Route("/callmap", callmap),
        Route("/paper", paper),
        Mount("/static", StaticFiles(directory=STATIC), name="static"),
    ],
    middleware=[Middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])],
)


# ---------------------------------------------------------------- command line

def _port(preferred: int) -> int:
    """The preferred port if it is free on 127.0.0.1, otherwise any free one."""
    for candidate in (preferred, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", candidate))
            except OSError:
                continue
            return s.getsockname()[1]
    raise SystemExit("No free port on 127.0.0.1.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="sigshell-ui", description="Serve the Sigshell page on this computer.")
    parser.add_argument("--port", type=int, default=8787, help="port to use if it is free (default 8787)")
    parser.add_argument("--no-browser", action="store_true", help="don't open the page in the browser")
    args = parser.parse_args(argv)
    port = _port(args.port)
    url = f"http://127.0.0.1:{port}/"
    print(f"Sigshell is running at {url}\nInput files go in {config.DATA_DIR}\nPress Ctrl+C to stop.", flush=True)
    if not args.no_browser:
        threading.Timer(1.0, webbrowser.open, [url]).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
