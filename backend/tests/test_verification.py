"""Differential verification against real GnuCOBOL (sandboxed docker runner)."""

import time
from pathlib import Path

import pytest

from phoenix.codegen.project_gen import generate_project, write_project
from phoenix.services import build_cases
from phoenix.verify.engine import NOT_VERIFIABLE, verify
from phoenix.verify.executors import DisabledExecutor, DockerExecutor
from tests.conftest import RUNNER_IMAGE, SAMPLE


def fixtures_for(entry):
    import json

    return json.loads((SAMPLE / "phoenix-fixtures.json").read_text())[entry]


def test_disabled_executor_never_fabricates_results(sample_parse, tmp_path):
    gp = generate_project(sample_parse, "RATEENG", "r")
    write_project(gp, tmp_path)
    cases = build_cases(sample_parse, "RATEENG", fixtures_for("RATEENG"), 30)
    rep = verify(sample_parse, gp, tmp_path, cases, DisabledExecutor())
    assert rep["summary"]["verified"] == 0 and rep["summary"]["failed"] == 0
    assert all(c["status"] == NOT_VERIFIABLE and c["cobol"] is None for c in rep["cases"])
    assert "not executed" in rep["claim"]


def _wait_ok(fn):
    t = time.time()
    res = fn()
    return res, time.time() - t


@pytest.mark.cobol
def test_rateeng_matches_gnucobol_and_detects_injected_fault(sample_parse, tmp_path):
    ex = DockerExecutor(RUNNER_IMAGE, tmp_path / "jobs")
    (tmp_path / "jobs").mkdir()
    gp = generate_project(sample_parse, "RATEENG", "r")
    write_project(gp, tmp_path / "ok")
    cases = build_cases(sample_parse, "RATEENG", fixtures_for("RATEENG"), 220)
    rep = verify(sample_parse, gp, tmp_path / "ok", cases, ex)
    s = rep["summary"]
    assert s["total"] >= 100 and s["verified"] == s["total"], [c for c in rep["cases"] if c["status"] != "VERIFIED"][:2]
    assert rep["executor"]["cobc_version"].startswith("cobc (GnuCOBOL)")
    assert s["coverage_pct"] > 90
    # deliberately injected fault: drop ROUNDED on the base premium
    from phoenix.codegen.program_gen import mutation_candidates

    m = next(c for c in mutation_candidates(sample_parse.program("RATEENG").program) if c.kind == "rounding" and c.line == 198)
    bad = generate_project(sample_parse, "RATEENG", "r", mutation=m)
    write_project(bad, tmp_path / "bad")
    rep2 = verify(sample_parse, bad, tmp_path / "bad", cases, ex)
    assert rep2["summary"]["failed"] > 0
    diff_fields = {d["field"] for c in rep2["cases"] if c["status"] == "FAILED" for d in c["diffs"]}
    assert "RR-BASE-PREMIUM" in diff_fields


@pytest.mark.cobol
def test_premcalc_batch_matches_gnucobol(sample_parse, tmp_path):
    (tmp_path / "jobs").mkdir()
    gp = generate_project(sample_parse, "PREMCALC", "p")
    write_project(gp, tmp_path / "p")
    cases = build_cases(sample_parse, "PREMCALC", fixtures_for("PREMCALC"), 10)
    rep = verify(sample_parse, gp, tmp_path / "p", cases, DockerExecutor(RUNNER_IMAGE, tmp_path / "jobs"))
    assert rep["summary"]["verified"] == 1
    assert rep["cases"][0]["cobol"]["stdout"] == (SAMPLE / "fixtures" / "expected-output.txt").read_text()


del Path
