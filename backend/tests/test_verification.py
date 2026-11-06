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
    # project_dir: coverage-guided + validity-aware placement, as in services.run_verification
    cases = build_cases(sample_parse, "RATEENG", fixtures_for("RATEENG"), 220, project_dir=tmp_path / "ok")
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


@pytest.mark.cobol
def test_inspect_tallying_and_replacing_match_gnucobol(tmp_path):
    from phoenix.cobol.project import parse_project
    from phoenix.verify.testgen import TestCase
    from tests.conftest import INSPECT_DEMO_SOURCE, INSPECT_DEMO_STDIN

    (tmp_path / "jobs").mkdir()
    pp = parse_project({"inspdemo.cob": INSPECT_DEMO_SOURCE})
    gp = generate_project(pp, "INSPDEMO", "insp")
    assert not gp.unsupported
    write_project(gp, tmp_path / "p")
    cases = [TestCase(id=k, kind="fixture", description=f"INSPECT on {v!r}", stdin=v) for k, v in INSPECT_DEMO_STDIN.items()]
    rep = verify(pp, gp, tmp_path / "p", cases, DockerExecutor(RUNNER_IMAGE, tmp_path / "jobs"))
    assert rep["compile"]["ok"], rep["compile"]["log"]
    s = rep["summary"]
    assert s["verified"] == s["total"] == len(cases), [(c["id"], c["diffs"], c["cobol"], c["python"]) for c in rep["cases"] if c["status"] != "VERIFIED"]
    assert s["coverage_pct"] == 100.0


# ---------------------------------------------------------------- validity-aware placement
# Same shape as RATEENG: a consistency check (PM-107 style) rejects some boundary values
# before the statement they were derived from.
GUARDED_SOURCE = """       IDENTIFICATION DIVISION.
       PROGRAM-ID. GUARDED.
       DATA DIVISION.
       LINKAGE SECTION.
       01  REQ.
           05  R-AGE              PIC 9(03).
           05  R-YEARS            PIC 9(02).
       01  RES.
           05  R-OUT              PIC 9(01).
       PROCEDURE DIVISION USING REQ RES.
       MAIN-PARA.
           MOVE 0 TO R-OUT
           IF R-YEARS > R-AGE - 16
              GOBACK
           END-IF
           IF R-AGE < 21
              MOVE 1 TO R-OUT
           END-IF
           IF R-YEARS < 3
              MOVE 2 TO R-OUT
           END-IF
           GOBACK.
"""
F_OLD = {"id": "old-experienced", "description": "", "inputs": {"REQ": {"R-AGE": "40", "R-YEARS": "20"}}}
F_YOUNG = {"id": "young-novice", "description": "", "inputs": {"REQ": {"R-AGE": "19", "R-YEARS": "1"}}}


def _guarded():
    from phoenix.analysis.dataflow import program_access
    from phoenix.cobol import ir
    from phoenix.cobol.project import parse_project
    from phoenix.verify.records import RecordCodec

    prog = parse_project({"guarded.cbl": GUARDED_SOURCE}).program("GUARDED").program
    ifs = [s for p in prog.paragraphs for s in ir.walk_statements(p.statements) if isinstance(s, ir.If)]
    keys = [f"{s.loc.file}:{s.loc.line}" for s in ifs]  # consistency IF, age IF, years IF
    index = prog.item_index()
    total, _ = program_access(prog)
    return prog, total.reads, {u: RecordCodec(index[u]) for u in prog.using}, keys


class FakeReaches:
    """Deterministic model of GUARDED: the age/years IFs run unless YEARS > AGE - 16."""

    def __init__(self, keys, never: str | None = None):
        self.keys, self.never, self.seen = keys, never, []

    def executed(self, inputs):
        from decimal import Decimal

        req = inputs.get("REQ", {})
        age, years = (Decimal(str(req.get(f, "0") or "0")) for f in ("R-AGE", "R-YEARS"))
        return {self.keys[0]} if years > age - 16 else set(self.keys)

    def __call__(self, inputs, key):
        self.seen.append(repr(sorted((p, sorted((k, str(v)) for k, v in f.items())) for p, f in inputs.items())))
        return key != self.never and key in self.executed(inputs)


def _cov(fake, fixtures):
    return {f["id"]: fake.executed(f["inputs"]) for f in fixtures}


def _age21(cases):
    return next(c for c in cases if c.kind == "boundary" and c.description.startswith("R-AGE = 21 "))


def test_placement_falls_back_to_another_fixture_that_reaches_the_statement():
    from phoenix.verify.testgen import generate_cases

    prog, reads, codecs, keys = _guarded()
    fake = FakeReaches(keys)
    fixtures = [F_OLD, F_YOUNG]
    cases = generate_cases(prog, reads, codecs, fixtures, fixture_coverage=_cov(fake, fixtures), reaches=fake)
    c = _age21(cases)
    # preferred fixture old-experienced (YEARS 20 > 21 - 16) is rejected; young-novice reaches the IF
    assert c.inputs["REQ"]["R-YEARS"] == "1" and "[on fixture young-novice]" in c.description
    assert fake.executed(c.inputs) == set(keys) and "not reached" not in c.description


def test_placement_adjusts_guard_fields_with_collected_values_only():
    from phoenix.verify.testgen import CandidateCollector, generate_cases

    prog, reads, codecs, keys = _guarded()
    fake = FakeReaches(keys)
    cases = generate_cases(prog, reads, codecs, [F_OLD], fixture_coverage=_cov(fake, [F_OLD]), reaches=fake)
    col = CandidateCollector(prog, reads)
    col.collect()
    years_id = next(i for i in reads if prog.item_index()[i].name == "R-YEARS")
    collected = {str(v) for v, _w, _k in col.values[years_id]}
    c = _age21(cases)
    assert fake.executed(c.inputs) == set(keys)
    assert str(c.inputs["REQ"]["R-YEARS"]) in collected and str(c.inputs["REQ"]["R-YEARS"]) != "20"
    assert f"[on fixture old-experienced; R-YEARS={c.inputs['REQ']['R-YEARS']}]" in c.description
    for case in cases:  # every boundary case derived from the age IF now executes it
        if case.kind == "boundary" and f"({keys[1]})" in case.description:
            assert keys[1] in fake.executed(case.inputs), case.description


def test_placement_exhaustion_keeps_original_placement_and_annotates():
    from phoenix.verify.testgen import PLACEMENT_MAX_ATTEMPTS, generate_cases

    prog, reads, codecs, keys = _guarded()
    fixtures = [F_OLD, F_YOUNG]
    cov = _cov(FakeReaches(keys), fixtures)
    plain = generate_cases(prog, reads, codecs, fixtures, fixture_coverage=cov)
    fake = FakeReaches(keys, never=keys[1])
    cases = generate_cases(prog, reads, codecs, fixtures, fixture_coverage=cov, reaches=fake)
    c, p = _age21(cases), _age21(plain)
    assert c.inputs == p.inputs and c.stdin == p.stdin
    assert c.description == p.description + f" [on fixture old-experienced] [target {keys[1]} not reached]"
    targeted = sum(1 for x in plain if x.kind == "boundary" and f"({keys[1]})" in x.description)
    assert len(set(fake.seen)) <= PLACEMENT_MAX_ATTEMPTS * targeted + len(plain)


def test_placement_without_reaches_is_coverage_guided_placement():
    from phoenix.verify.testgen import generate_cases

    prog, reads, codecs, keys = _guarded()
    fixtures = [F_OLD, F_YOUNG]
    cov = _cov(FakeReaches(keys), fixtures)
    plain = generate_cases(prog, reads, codecs, fixtures, fixture_coverage=cov)
    none = generate_cases(prog, reads, codecs, fixtures, fixture_coverage=cov, reaches=None)
    always = generate_cases(prog, reads, codecs, fixtures, fixture_coverage=cov, reaches=lambda _i, _k: True)
    assert [(c.id, c.description, c.inputs, c.stdin) for c in none] == [(c.id, c.description, c.inputs, c.stdin) for c in plain]
    # a callback that accepts every preferred placement changes only the annotation
    assert [(c.id, c.inputs, c.stdin) for c in always] == [(c.id, c.inputs, c.stdin) for c in plain]
    assert not any("[target" in c.description for c in none)
    assert [c for c in none if c.kind == "random"] == [c for c in always if c.kind == "random"]


def test_placement_is_deterministic_deduplicated_and_capped():
    from phoenix.verify.testgen import generate_cases

    prog, reads, codecs, keys = _guarded()
    fixtures = [F_OLD, F_YOUNG]

    def run(max_cases=220):
        fake = FakeReaches(keys)
        return generate_cases(prog, reads, codecs, fixtures, fixture_coverage=_cov(fake, fixtures), reaches=fake, max_cases=max_cases)

    a, b = run(), run()
    assert [(c.id, c.kind, c.description, c.inputs, c.stdin) for c in a] == [(c.id, c.kind, c.description, c.inputs, c.stdin) for c in b]
    assert len({c.stdin for c in a}) == len(a)
    small = run(max_cases=7)
    assert len(small) == 7 and [c.id for c in small] == [c.id for c in a[:7]]


def test_rateeng_age_21_boundary_reaches_age_band_and_kills_relop_138(sample_parse, tmp_path):
    """Traced generated Python (no GnuCOBOL needed): PR-DRIVER-AGE = 21 is no longer rejected by PM-107."""
    import json

    from phoenix.codegen.program_gen import mutation_candidates
    from phoenix.verify import engine
    from phoenix.verify.engine import coverage_map, mutation_analysis, run_python

    gp = generate_project(sample_parse, "RATEENG", "r")
    write_project(gp, tmp_path / "p")
    cases = build_cases(sample_parse, "RATEENG", fixtures_for("RATEENG"), 220, project_dir=tmp_path / "p")
    c = next(x for x in cases if x.description.startswith("PR-DRIVER-AGE = 21 — equal to 21 (cobol/RATEENG.cbl:137)"))
    assert "not reached" not in c.description
    cmap = coverage_map(json.loads((tmp_path / "p" / "traceability.json").read_text()))
    (r,) = run_python(tmp_path / "p", "RATEENG", "harness", [c], trace=True)
    assert "cobol/RATEENG.cbl:137" in {cmap[(f, n)] for f, n in r["lines"] if (f, n) in cmap}
    ref = {x["id"]: x["stdout"] for x in run_python(tmp_path / "p", "RATEENG", "harness", cases, trace=False)}
    picked = [m for m in mutation_candidates(sample_parse.program("RATEENG").program) if m.id == "relop@cobol/RATEENG.cbl:138#0"]
    original = engine.mutation_candidates
    try:
        engine.mutation_candidates = lambda prog: picked
        res = mutation_analysis(sample_parse, gp, tmp_path / "p", cases, ref)
    finally:
        engine.mutation_candidates = original
    assert [m["status"] for m in res["mutants"]] == ["killed"]


del Path


def test_mutants_evaluated_in_sequence_match_isolated_runs(sample_parse, tmp_path):
    """Same-size mutants written within one second must not reuse stale bytecode."""
    from phoenix.codegen.program_gen import mutation_candidates
    from phoenix.verify import engine
    from phoenix.verify.engine import mutation_analysis, run_python

    gp = generate_project(sample_parse, "RATEENG", "r")
    write_project(gp, tmp_path / "p")
    cases = build_cases(sample_parse, "RATEENG", fixtures_for("RATEENG"), 220)
    ref = {r["id"]: r["stdout"] for r in run_python(tmp_path / "p", "RATEENG", "harness", cases, trace=False)}
    all_m = mutation_candidates(sample_parse.program("RATEENG").program)
    picked = [m for m in all_m if m.id in ("relop@cobol/RATEENG.cbl:138#0", "relop@cobol/RATEENG.cbl:140#0", "relop@cobol/RATEENG.cbl:142#0")]
    assert len(picked) == 3
    original = engine.mutation_candidates
    try:
        engine.mutation_candidates = lambda prog: picked
        together = {m["id"]: m["status"] for m in mutation_analysis(sample_parse, gp, tmp_path / "p", cases, ref)["mutants"]}
        alone = {}
        for m in picked:
            engine.mutation_candidates = lambda prog, m=m: [m]
            alone.update({x["id"]: x["status"] for x in mutation_analysis(sample_parse, gp, tmp_path / "p", cases, ref)["mutants"]})
    finally:
        engine.mutation_candidates = original
    assert together == alone
