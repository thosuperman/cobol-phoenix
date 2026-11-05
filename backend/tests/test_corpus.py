"""Regression tests against the external COBOL corpus (see corpus/manifest.json).

The repositories are not vendored; scripts/fetch-corpus.sh clones them at the
pinned commits into corpus/repos/.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from phoenix.analysis.project_analysis import analyze
from phoenix.cobol.project import SOURCE_EXTS, parse_project
from phoenix.codegen.project_gen import generate_project, write_project
from tests.conftest import CORPUS, ROOT

pytestmark = pytest.mark.corpus
MANIFEST = json.loads((ROOT / "corpus" / "manifest.json").read_text())


def load(entry):
    root = CORPUS / entry["dir"] / entry.get("subdir", "")
    raw = {str(p.relative_to(root)): p.read_text(encoding="latin-1") for p in root.rglob("*") if p.suffix.lower() in SOURCE_EXTS and ".git" not in p.parts}
    return parse_project(raw, entry.get("format"))


@pytest.mark.parametrize("entry", MANIFEST["repositories"], ids=lambda e: e["dir"])
def test_corpus_parses_without_errors_and_reports_unsupported(entry):
    pp = load(entry)
    a = analyze(pp)
    assert a["overview"]["programs"] == entry["expected"]["programs"]
    assert a["overview"]["errors"] == 0, [d for d in a["diagnostics"] if d["severity"] == "error"][:5]
    assert a["overview"]["unsupported_constructs"] == entry["expected"]["unsupported_constructs"]


@pytest.mark.parametrize("driver,golden", [("DRIVENBUW", "nb_issue_ok.out"), ("DRIVESVC", "svc_billing_mode_ok.out"), ("DRIVECLM", "clm_approve_ok.out")])
def test_insurance_drivers_reproduce_upstream_golden_files(driver, golden, tmp_path):
    entry = MANIFEST["repositories"][0]
    pp = load(entry)
    gp = generate_project(pp, driver, driver.lower())
    assert not gp.unsupported
    write_project(gp, tmp_path)
    r = subprocess.run(
        [sys.executable, "-m", "app.cli", "--entry", driver, "--mode", "main", "--date", "20260101093000"],
        input='[{"id":"g","stdin":""}]',
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    out = json.loads(r.stdout)[0]
    expected = (CORPUS / entry["dir"] / "tests" / "expected" / golden).read_text()
    assert out["status"] == "ok" and out["stdout"] == expected


@pytest.mark.cobol
def test_nbuw001_differential_against_gnucobol(tmp_path):
    from phoenix.services import build_cases
    from phoenix.verify.engine import verify
    from phoenix.verify.executors import DockerExecutor
    from tests.conftest import RUNNER_IMAGE

    entry = MANIFEST["repositories"][0]
    pp = load(entry)
    gp = generate_project(pp, "NBUW001", "nbuw001")
    write_project(gp, tmp_path / "g")
    fixtures = json.loads((ROOT / "corpus" / "fixtures" / "nbuw001-fixtures.json").read_text())
    cases = build_cases(pp, "NBUW001", fixtures, 220)
    (tmp_path / "jobs").mkdir()
    rep = verify(pp, gp, tmp_path / "g", cases, DockerExecutor(RUNNER_IMAGE, tmp_path / "jobs"))
    s = rep["summary"]
    assert s["failed"] == 0 and s["verified"] == s["total"] and s["total"] > 100


del Path
