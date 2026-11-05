"""Differential verification: original COBOL (GnuCOBOL sandbox) vs generated Python."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath

from ..cobol import ir
from ..cobol.project import ProjectParse
from ..codegen.program_gen import Mutation, ProgramGenerator, mutation_candidates
from ..codegen.project_gen import GeneratedProject, call_tree
from .executors import CobolCase, CobolJob, CobolResult, Executor
from .harness import HARNESS_ID, harness_source, split_harness_output
from .records import RecordCodec
from .testgen import TestCase

FIXED_DATETIME = "20260101093000"  # YYYYMMDDHHMMSS used by both runtimes
PY_TIMEOUT_S = 120

VERIFIED = "VERIFIED"
FAILED = "FAILED"
NOT_VERIFIABLE = "NOT_VERIFIABLE"
UNSUPPORTED = "UNSUPPORTED"


def cob_datetime(fixed: str = FIXED_DATETIME) -> str:
    return f"{fixed[0:4]}/{fixed[4:6]}/{fixed[6:8]} {fixed[8:10]}:{fixed[10:12]}:{fixed[12:14]}"


# ---------------------------------------------------------------- COBOL side
def build_cobol_job(pp: ProjectParse, entry: str, mode: str, cases: list[TestCase], fixed: str = FIXED_DATETIME) -> CobolJob:
    order, _missing = call_tree(pp, entry)
    prog_files: list[str] = []
    for pid in order:
        f = pp.program(pid).program.file
        if f not in prog_files:
            prog_files.append(f)
    sources = {f.path: f.text for f in pp.files if f.kind in ("program", "copybook") and (f.kind == "copybook" or f.path in prog_files)}
    copy_dirs = sorted({str(PurePosixPath(f.path).parent) for f in pp.files if f.kind in ("copybook", "program")})
    units = list(prog_files)
    if mode == "harness":
        hpath = "phoenix_harness/PHXHARNS.cob"
        sources[hpath] = harness_source(pp.program(entry).program)
        units = [hpath] + units
    free = pp.program(entry).program.source_format == "free"
    return CobolJob(
        sources=sources,
        compile_units=units,
        copybook_dirs=[d if d != "." else "" for d in copy_dirs],
        cases=[CobolCase(c.id, c.stdin) for c in cases],
        free_format=free,
        fixed_datetime=cob_datetime(fixed),
    )


# ---------------------------------------------------------------- Python side
def run_python(project_dir: Path, entry: str, mode: str, cases: list[TestCase], trace: bool = True, fixed: str = FIXED_DATETIME) -> list[dict]:
    payload = json.dumps([{"id": c.id, "stdin": c.stdin} for c in cases])
    cmd = [sys.executable, "-E", "-s", "-m", "app.cli", "--entry", entry, "--mode", mode, "--date", fixed]
    if trace:
        cmd.append("--trace")
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"}
    r = subprocess.run(cmd, input=payload, capture_output=True, text=True, cwd=project_dir, timeout=PY_TIMEOUT_S, env=env, check=False)
    if r.returncode != 0 or not r.stdout.strip():
        err = (r.stderr or "no output")[-2000:]
        return [{"id": c.id, "stdout": "", "status": "error", "error": f"python runner failed: {err}"} for c in cases]
    return json.loads(r.stdout)


# ---------------------------------------------------------------- comparison
def _num(v: str | None) -> Decimal | None:
    if v is None:
        return None
    try:
        return Decimal(v)
    except InvalidOperation:
        return None


def compare_linkage(cobol_out: str, py_out: str, codecs: list[RecordCodec]) -> tuple[bool, list[dict], str]:
    c_disp, c_params = split_harness_output(cobol_out, len(codecs))
    p_disp, p_params = split_harness_output(py_out, len(codecs))
    diffs: list[dict] = []
    note = ""
    if c_params is None and p_params is None:
        note = "both programs terminated before returning (STOP RUN or abnormal end)"
    elif c_params is None or p_params is None:
        side = "COBOL" if c_params is None else "Python"
        diffs.append({"param": "-", "field": "(control flow)", "cobol": "no return" if c_params is None else "returned", "python": "no return" if p_params is None else "returned", "note": f"{side} did not return from the CALL"})
    else:
        for codec, cl, pl in zip(codecs, c_params, p_params, strict=False):
            if cl == pl:
                continue
            cd = {e["field"]: e for e in codec.decode(cl)}
            pd = {e["field"]: e for e in codec.decode(pl)}
            for name, ce in cd.items():
                pe = pd.get(name)
                if pe is None or ce["raw"] == pe["raw"]:
                    continue
                d = {"param": codec.root.name, "field": name, "cobol": ce["raw"], "python": pe["raw"], "loc": ce["loc"], "kind": ce["kind"]}
                cv, pv = _num(ce.get("value")), _num(pe.get("value"))
                if cv is not None and pv is not None:
                    d["cobol_value"], d["python_value"], d["delta"] = str(cv), str(pv), str(pv - cv)
                diffs.append(d)
            if not diffs:
                diffs.append({"param": codec.root.name, "field": "(filler bytes)", "cobol": cl, "python": pl, "note": "difference outside named fields"})
    for i in range(max(len(c_disp), len(p_disp))):
        cl = c_disp[i] if i < len(c_disp) else None
        pl = p_disp[i] if i < len(p_disp) else None
        if cl != pl:
            diffs.append({"param": "DISPLAY", "field": f"line {i + 1}", "cobol": cl, "python": pl})
    return not diffs, diffs, note


def compare_main(cobol_out: str, py_out: str) -> tuple[bool, list[dict], str]:
    if cobol_out == py_out:
        return True, [], ""
    cl, pl = cobol_out.split("\n"), py_out.split("\n")
    diffs = []
    for i in range(max(len(cl), len(pl))):
        a = cl[i] if i < len(cl) else None
        b = pl[i] if i < len(pl) else None
        if a != b:
            diffs.append({"param": "STDOUT", "field": f"line {i + 1}", "cobol": a, "python": b})
        if len(diffs) >= 50:
            break
    return False, diffs, ""


# ---------------------------------------------------------------- coverage
def coverage_map(gp_trace: list[dict]) -> dict[tuple[str, int], str]:
    """(python module file name, python line) -> COBOL statement key."""
    out: dict[tuple[str, int], str] = {}
    for t in gp_trace:
        key = f"{t['cobol_file']}:{t['cobol_start']}"
        out[(PurePosixPath(t["python_file"]).name, t["python_start"])] = key
    return out


def statement_keys(gp_trace: list[dict]) -> dict[str, dict]:
    keys: dict[str, dict] = {}
    for t in gp_trace:
        key = f"{t['cobol_file']}:{t['cobol_start']}"
        keys.setdefault(key, {"file": t["cobol_file"], "line": t["cobol_start"], "end_line": t["cobol_end"], "construct": t["construct"], "paragraph": t["paragraph"], "program": t["program"], "python_file": t["python_file"], "python_line": t["python_start"]})
    return keys


# ---------------------------------------------------------------- orchestration
def verify(
    pp: ProjectParse,
    gp: GeneratedProject,
    project_dir: Path,
    cases: list[TestCase],
    executor: Executor,
    cobol_result: CobolResult | None = None,
    progress: Callable[[str], None] | None = None,
) -> dict:
    progress = progress or (lambda _m: None)
    entry = gp.entry
    mode = "harness" if gp.interface.mode == "linkage" else "main"
    prog = pp.program(entry).program
    index = prog.item_index()
    codecs = [RecordCodec(index[u]) for u in prog.using] if mode == "harness" else []
    started = time.time()
    display_only = all(p.display_only for p in gp.interface.params)
    if cobol_result is None:
        if mode == "harness" and not display_only:
            cobol_result = CobolResult(available=False, executor=executor.name, error="USING records contain binary/packed fields; line-based harness cannot transport them")
        else:
            progress(f"compiling and running {len(cases)} cases with GnuCOBOL ({executor.name})")
            cobol_result = executor.run(build_cobol_job(pp, entry, mode, cases))
    progress(f"running {len(cases)} cases with generated Python")
    py_results = {r["id"]: r for r in run_python(project_dir, entry, mode, cases)}
    cov = coverage_map(gp.traceability)
    stmts = statement_keys(gp.traceability)
    stmt_stats = {k: {"passed": 0, "failed": 0, "other": 0} for k in stmts}
    cobol_by_id = {c.id: c for c in cobol_result.cases}
    out_cases = []
    counts = {VERIFIED: 0, FAILED: 0, NOT_VERIFIABLE: 0, UNSUPPORTED: 0}
    for tc in cases:
        py = py_results.get(tc.id, {"stdout": "", "status": "error", "error": "missing python result"})
        executed = sorted({cov[(f, n)] for f, n in py.get("lines", []) if (f, n) in cov})
        cob = cobol_by_id.get(tc.id)
        diffs: list[dict] = []
        note = ""
        if py["status"] == "unsupported":
            status = UNSUPPORTED
            note = py.get("error") or ""
        elif not cobol_result.available or not cobol_result.compiled or cob is None:
            status = NOT_VERIFIABLE
            note = cobol_result.error or ("COBOL compilation failed" if cobol_result.available and not cobol_result.compiled else "no COBOL result")
        elif cob.timed_out:
            status = NOT_VERIFIABLE
            note = "COBOL execution timed out"
        else:
            cobol_err = cob.rc not in (0, None)
            py_err = py["status"] == "error"
            if mode == "harness":
                ok, diffs, note = compare_linkage(cob.stdout, py["stdout"], codecs)
            else:
                ok, diffs, note = compare_main(cob.stdout, py["stdout"])
            if cobol_err != py_err:
                ok = False
                diffs.append({"param": "-", "field": "(error behaviour)", "cobol": f"rc={cob.rc} {cob.stderr.strip()[:200]}", "python": py.get("error") or "completed"})
            elif cobol_err and py_err:
                note = (note + "; " if note else "") + f"both runtimes reported an error (COBOL rc={cob.rc})"
            status = VERIFIED if ok else FAILED
        counts[status] += 1
        bucket = "passed" if status == VERIFIED else "failed" if status == FAILED else "other"
        for k in executed:
            if k in stmt_stats:
                stmt_stats[k][bucket] += 1
        out_cases.append(
            {
                "id": tc.id, "kind": tc.kind, "description": tc.description, "status": status, "note": note,
                "inputs": {p: {k: str(v) for k, v in vals.items()} for p, vals in tc.inputs.items()},
                "stdin": tc.stdin,
                "cobol": None if cob is None else {"stdout": cob.stdout, "stderr": _clean_stderr(cob.stderr), "rc": cob.rc, "timed_out": cob.timed_out, "duration_ms": cob.duration_ms},
                "python": {"stdout": py["stdout"], "status": py["status"], "error": py.get("error")},
                "diffs": diffs, "executed": executed,
            }
        )  # fmt: skip
    executed_any = [k for k, v in stmt_stats.items() if v["passed"] + v["failed"] + v["other"] > 0]
    report = {
        "entry": entry,
        "mode": mode,
        "fixed_datetime": FIXED_DATETIME,
        "duration_s": round(time.time() - started, 2),
        "executor": {"name": cobol_result.executor, "available": cobol_result.available, "error": cobol_result.error, "cobc_version": cobol_result.cobc_version},
        "compile": {"ok": cobol_result.compiled, "command": cobol_result.compile_command, "log": _clean_stderr(cobol_result.compile_log)},
        "summary": {
            "total": len(cases),
            "verified": counts[VERIFIED],
            "failed": counts[FAILED],
            "not_verifiable": counts[NOT_VERIFIABLE],
            "unsupported": counts[UNSUPPORTED],
            "statements_total": len(stmts),
            "statements_executed": len(executed_any),
            "coverage_pct": round(100 * len(executed_any) / len(stmts), 1) if stmts else 0.0,
            "by_kind": _by_kind(out_cases),
        },
        "statements": [dict(v, key=k, **stmt_stats[k]) for k, v in stmts.items()],
        "cases": out_cases,
        "mutation_id": gp.mutation,
        "claim": _claim(counts, len(cases), len(executed_any), len(stmts)),
    }
    return report


def _clean_stderr(s: str) -> str:
    return "\n".join(ln for ln in (s or "").splitlines() if "libxml" not in ln)


def _by_kind(cases: list[dict]) -> dict:
    out: dict[str, dict[str, int]] = {}
    for c in cases:
        d = out.setdefault(c["kind"], {})
        d[c["status"]] = d.get(c["status"], 0) + 1
    return out


def _claim(counts: dict, total: int, executed: int, stmts: int) -> str:
    if counts[VERIFIED] == 0 and counts[FAILED] == 0:
        return "No behavioural comparison was possible: the original COBOL program was not executed."
    s = f"{counts[VERIFIED]} of {total} cases produced identical outputs in GnuCOBOL and Python"
    if counts[FAILED]:
        s += f"; {counts[FAILED]} cases differ"
    s += f". The cases executed {executed} of {stmts} translated COBOL statements. This is evidence for these inputs only, not a proof of equivalence for all inputs."
    return s


# ---------------------------------------------------------------- mutation analysis
def mutation_analysis(
    pp: ProjectParse,
    gp: GeneratedProject,
    project_dir: Path,
    cases: list[TestCase],
    reference: dict[str, str],
    limit: int = 60,
    progress: Callable[[str], None] | None = None,
) -> dict:
    """Run the suite against single-fault mutants of the entry program.

    ``reference`` maps case id -> expected stdout (COBOL output when available).
    A mutant is *killed* when at least one case output differs from the reference.
    """
    progress = progress or (lambda _m: None)
    prog = pp.program(gp.entry).program
    mode = "harness" if gp.interface.mode == "linkage" else "main"
    sources = {f.path: f.text.splitlines() for f in pp.files}
    cands = mutation_candidates(prog)
    selected = _spread(cands, limit)
    results = []
    entry_mod = gp.modules[0]
    with tempfile.TemporaryDirectory(prefix="phx-mut-") as tmp:
        work = Path(tmp) / "proj"
        shutil.copytree(project_dir, work)
        target = work / "app" / "programs" / f"{entry_mod.module}.py"
        for i, m in enumerate(selected, start=1):
            progress(f"mutant {i}/{len(selected)}: {m.id}")
            mod = ProgramGenerator(prog, sources, m).generate()
            if not mod.mutations_applied:
                results.append({**asdict(m), "status": "not-applied"})
                continue
            target.write_text(mod.source)
            outs = run_python(work, gp.entry, mode, cases, trace=False)
            killed_by = [o["id"] for o in outs if o["id"] in reference and o["stdout"] != reference[o["id"]]]
            results.append({**asdict(m), "status": "killed" if killed_by else "survived", "killed_by": killed_by[:10]})
    applied = [r for r in results if r["status"] != "not-applied"]
    killed = sum(1 for r in applied if r["status"] == "killed")
    return {
        "candidates": len(cands),
        "evaluated": len(applied),
        "killed": killed,
        "survived": len(applied) - killed,
        "score_pct": round(100 * killed / len(applied), 1) if applied else 0.0,
        "mutants": results,
    }


def _spread(cands: list[Mutation], limit: int) -> list[Mutation]:
    if len(cands) <= limit:
        return cands
    by_kind: dict[str, list[Mutation]] = {}
    for c in cands:
        by_kind.setdefault(c.kind, []).append(c)
    out: list[Mutation] = []
    while len(out) < limit:
        progressed = False
        for k in sorted(by_kind):
            if by_kind[k]:
                out.append(by_kind[k].pop(0))
                progressed = True
                if len(out) >= limit:
                    break
        if not progressed:
            break
    return out


def _diff_fields(case: dict) -> set[str] | None:
    """Names of differing fields, or None when the difference cannot be attributed."""
    names: set[str] = set()
    for d in case.get("diffs", []):
        f = d.get("field", "")
        if f.startswith("(") or d.get("param") in ("STDOUT", "DISPLAY", "-"):
            return None
        names.add(f.split("(")[0])
    return names


def rule_status(rules: list[dict], reports: list[dict]) -> list[dict]:
    """Attach verification status to extracted business rules.

    * VERIFIED      - executed by at least one VERIFIED case and not blamed by a FAILED case
    * FAILED        - executed by a FAILED case whose differing fields include one of the
                      rule's outputs (or whose difference cannot be attributed to fields)
    * NOT_EXERCISED - not executed by any compared case
    * UNSUPPORTED   - the rule contains unsupported constructs
    """
    cases = [c for rep in reports for c in rep.get("cases", [])]
    executed_by: list[tuple[set[str], str, set[str] | None]] = [(set(c.get("executed", [])), c["status"], _diff_fields(c) if c["status"] == FAILED else set()) for c in cases]
    out = []
    for r in rules:
        keys = set(r.get("statement_keys", []))
        outputs = set(r.get("outputs", []))
        executed_keys: set[str] = set()
        passed = failed = False
        failing_cases = 0
        for ex, status, dfields in executed_by:
            hit = ex & keys
            if not hit:
                continue
            executed_keys |= hit
            if status == VERIFIED:
                passed = True
            elif status == FAILED and (dfields is None or dfields & outputs):
                failed = True
                failing_cases += 1
        if r.get("unsupported"):
            st = UNSUPPORTED
        elif failed:
            st = FAILED
        elif passed:
            st = VERIFIED
        else:
            st = "NOT_EXERCISED"
        n = len(keys)
        out.append({**r, "verification": {"status": st, "statements": n, "executed": len(executed_keys), "coverage_pct": round(100 * len(executed_keys) / n, 1) if n else 0.0, "failing_cases": failing_cases}})
    return out


__all__ = ["verify", "mutation_analysis", "rule_status", "build_cobol_job", "run_python", "FIXED_DATETIME", "ir"]
