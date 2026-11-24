"""Example-based checks of the input validator; property-based checks are added in Phase 5."""

from pathlib import Path

import pytest

from sigshell import validate
from sigshell.rbridge import RCode, r_literal

GOOD = "gene,S1,S2,S3\ng1,2,1,7\ng2,4,3,7\ng3,6,5,2\ng4,8,9,4\ng5,10,11,12\n"


def write(tmp: Path, name: str, text: str) -> Path:
    p = tmp / name
    p.write_text(text, encoding="utf-8")
    return p


def codes(report: validate.Report, level: str | None = None) -> set[str]:
    return {p.code for p in report.problems if level is None or p.level == level}


def test_clean_inputs_have_no_problems(tmp_path):
    r = validate.check(write(tmp_path, "m.csv", GOOD), write(tmp_path, "s.txt", "g1\ng3\ng4\ng5\n"))
    assert r.problems == []
    assert r.found == ["g1", "g3", "g4", "g5"]
    assert r.matrix.samples == ["S1", "S2", "S3"]


@pytest.mark.parametrize("sig, code", [
    ("g1\ngX\n", "missing_genes"),
    ("g1\nG3\n", "case_mismatch"),
    ("g1\ng1\ng3\n", "duplicate_signature_genes"),
    ("g1\t2\ng3\n", "partial_weights"),
    ("g1\tx\ng3\t1\n", "bad_weights"),
    ("g1\t1e309\ng3\t1\n", "bad_weights"),
    ("g1\t1\tunused\ng3\t2\n", "signature_columns"),
    ("# only a comment\n", "signature_empty"),
])
def test_signature_problems_are_errors(tmp_path, sig, code):
    r = validate.check(write(tmp_path, "m.csv", GOOD), write(tmp_path, "s.txt", sig))
    assert code in codes(r, "error")


@pytest.mark.parametrize("matrix, code", [
    ("gene,S1,S2\ng1,1,2\ng1,3,4\n", "duplicate_genes"),
    ("gene,S1,S1\ng1,1,2\ng2,3,4\n", "duplicate_samples"),
    ("gene,S1,S2\ng1,1,abc\ng2,3,4\n", "non_numeric"),
    ("gene,S1,S2\ng1,1,Inf\ng2,3,4\n", "non_finite"),
    ("gene,S1,S2\ng1,1,1e309\ng2,3,4\n", "non_finite"),
    ("gene,S1,S2\ng1,0x1A,2\ng2,3,4\n", "non_numeric"),
    ("S1,S2\ng1,1,2\ng2,3,4\n", "matrix_ragged"),
    ("gene,S1,S2\n,1,2\ng2,3,4\n", "empty_gene_id"),
])
def test_matrix_problems_are_errors(tmp_path, matrix, code):
    assert code in codes(validate.check(write(tmp_path, "m.csv", matrix)), "error")


def test_decimal_commas_get_a_hint(tmp_path):
    r = validate.check(write(tmp_path, "m.tsv", "gene\tS1\tS2\ng1\t1,5\t2\ng2\t3\t4\n"))
    assert "decimal commas" in next(p.message for p in r.errors if p.code == "non_numeric")


def test_transposed_matrix_is_detected(tmp_path):
    t = "sample,g1,g2,g3\nS1,1,2,3\nS2,4,5,6\n"
    r = validate.check(write(tmp_path, "m.csv", t), write(tmp_path, "s.txt", "g1\ng2\n"))
    assert "transposed" in codes(r, "error")


def test_constant_and_na_genes_are_warnings(tmp_path):
    m = "gene,S1,S2\ng1,5,5\ng2,NA,1\ng3,1,2\n"
    r = validate.check(write(tmp_path, "m.csv", m))
    assert {"constant_genes", "missing_values"} <= codes(r, "warning")
    assert r.constant_genes == ["g1"] and r.genes_with_na == ["g2"]
    assert not r.errors


def test_header_and_weights_in_signature(tmp_path):
    r = validate.check(write(tmp_path, "m.csv", GOOD), write(tmp_path, "s.csv", "gene,weight\ng1,2\ng3,0.5\n"))
    assert not r.errors and r.signature.weights == [2.0, 0.5]


def test_r_literals():
    assert r_literal(["mean", "median"]) == 'c("mean", "median")'
    assert r_literal({"by": "rows", "robust": False}) == 'list(by = "rows", robust = FALSE)'
    assert r_literal([1, 2.5]) == "c(1.0, 2.5)"
    assert r_literal('a"b\\c') == '"a\\"b\\\\c"'
    assert r_literal({"my score": 1}) == "list(`my score` = 1L)"
    assert r_literal(RCode('getDataTransformer("z")')) == 'getDataTransformer("z")'
    assert r_literal(None) == "NULL"
