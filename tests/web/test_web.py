"""The local web page (sigshell.web): its safety checks, file handling, and one run through R.

The R test compares with the published vignette (tests/b_vignette/published-blocks.json): the page's
example data must give the vignette's scores. It is skipped when R or sigscores is not available.
"""

from __future__ import annotations

import asyncio

import pytest
from starlette.testclient import TestClient

from sigshell import config, rbridge, server, web
from sigshell.session import Session

PAGE = {"X-Sigshell": "1"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(server, "session", Session(root=tmp_path / "sessions"))
    with TestClient(web.app, base_url="http://127.0.0.1") as c:
        yield c


def _upload(client, name, content):
    return client.post("/api/upload", headers=PAGE, files={"file": (name, content, "text/plain")})


def test_other_hosts_are_refused(client):
    assert client.get("/api/files", headers={"Host": "attacker.example"}).status_code == 400
    assert client.get("/api/files", headers={"Host": "localhost:8787"}).status_code == 200


def test_posts_need_the_page_header(client):
    assert client.post("/api/tool/check_inputs", json={"matrix_file": "m.csv"}).status_code == 403
    assert client.post("/api/upload", files={"file": ("m.csv", b"a")}).status_code == 403
    assert client.post("/api/example", json={}).status_code == 403
    assert client.post("/api/new-session", json={}).status_code == 403


def test_upload_sanitises_names_and_never_overwrites(client):
    first = _upload(client, "../my matrix (v2).csv", b",A\ng1,1\n").json()
    assert first == {"name": "my_matrix_v2.csv", "renamed": False}
    assert _upload(client, "my matrix (v2).csv", b",A\ng1,1\n").json()["name"] == "my_matrix_v2.csv"  # same bytes: reused
    other = _upload(client, "my matrix (v2).csv", b",A\ng1,2\n").json()
    assert other == {"name": "my_matrix_v2-2.csv", "renamed": True}
    assert (config.DATA_DIR / "my_matrix_v2.csv").read_bytes() == b",A\ng1,1\n"
    assert {f["name"] for f in client.get("/api/files").json()["files"]} == {"my_matrix_v2.csv", "my_matrix_v2-2.csv"}


def test_upload_refuses_other_formats(client):
    r = _upload(client, "table.xlsx", b"PK")
    assert r.status_code == 400 and "Save As > CSV" in r.json()["error"]
    assert _upload(client, "empty.csv", b"  \n").status_code == 400


def test_check_runs_through_the_mcp_tool(client):
    _upload(client, "m.csv", b",A,B\ng1,1,2\ng2,3,3\n")
    _upload(client, "s.txt", b"g1\ng9\n")
    r = client.post("/api/tool/check_inputs", headers=PAGE, json={"matrix_file": "m.csv", "signature_file": "s.txt", "ignored": 1})
    data = r.json()["data"]
    assert r.status_code == 200
    assert [e["code"] for e in data["errors"]] == ["missing_genes"]
    assert data["constant_genes"] == ["g2"] and data["signature_found"] == ["g1"]


def test_errors_are_plain_text(client):
    r = client.post("/api/tool/compute_scores", headers=PAGE, json={"matrix_file": "m.csv", "signature_file": "s.txt", "scores": ["mean"], "transform": "bogus"})
    assert r.status_code == 422
    assert "transform" in r.json()["error"] and "pydantic.dev" not in r.json()["error"]
    assert client.post("/api/tool/not_a_tool", headers=PAGE, json={}).status_code == 404


def test_session_files_stay_inside_the_session(client):
    _upload(client, "m.csv", b",A\ng1,1\n")
    client.post("/api/tool/check_inputs", headers=PAGE, json={"matrix_file": "m.csv"})  # starts the session folder
    assert client.get("/files/calls.jsonl").status_code == 200
    assert client.get("/files/..%2F..%2Fdata%2Fm.csv").status_code == 404
    assert client.get("/files/../../data/m.csv").status_code == 404


def _r_available() -> bool:
    try:
        asyncio.run(rbridge.installation())
    except rbridge.RError:
        return False
    return True


@pytest.mark.skipif(not _r_available(), reason="R with the pinned sigscores is not available")
def test_example_matches_the_published_vignette(client):
    names = client.post("/api/example", headers=PAGE, json={}).json()
    assert names == {"matrix": "vignette-matrix.csv", "signature": "vignette-signature.txt"}
    signature = (config.DATA_DIR / names["signature"]).read_text().split()
    assert signature[:4] == ["g12", "g41", "g23", "g59"] and len(signature) == 20  # as printed in the vignette
    r = client.post("/api/tool/compute_scores", headers=PAGE, json={
        "matrix_file": names["matrix"], "signature_file": names["signature"], "scores": ["mean", "median"]}).json()
    scores = dict(zip(r["data"]["samples"], zip(r["data"]["scores"]["mean"], r["data"]["scores"]["median"])))
    assert scores["S1"] == (666.55, 736.5) and scores["S2"] == (614, 623)  # published: S1 666.55 736.5, S2 614.00 623.0
    assert [f["name"] for f in r["files"]] == ["001-scores.csv", "001-scores.rds"]
    plot = client.post("/api/tool/plot_scores", headers=PAGE, json={"result_id": r["data"]["result_id"], "kind": "boxplot"}).json()
    assert client.get(plot["url"]).headers["content-type"] == "image/png"
    script = client.post("/api/tool/get_r_script", headers=PAGE, json={}).json()["script"]
    assert "computeSigScores" in script and "boxplotSigScores" in script
