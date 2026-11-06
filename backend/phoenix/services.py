"""Application services: import, analysis, generation and verification orchestration."""

from __future__ import annotations

import datetime as dt
import io
import json
import logging
import shutil
import subprocess
import threading
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath

from .analysis.dataflow import program_access
from .analysis.project_analysis import analyze as analyze_parse
from .api.importer import ImportResult
from .cobol.project import SOURCE_EXTS, ProjectParse, parse_project
from .codegen.program_gen import Mutation, mutation_candidates
from .codegen.project_gen import GenerationError, generate_project, write_project
from .config import Settings, get_settings
from .db import Generation, Project, VerificationRun, session
from .verify.engine import FIXED_DATETIME, mutation_analysis, rule_status, verify
from .verify.executors import Executor, make_executor
from .verify.records import RecordCodec
from .verify.testgen import TestCase, TraceUnavailable, encode_inputs, generate_cases

log = logging.getLogger("phoenix")
FIXTURE_FILE = "phoenix-fixtures.json"
SAMPLES_DIR = Path(__file__).parent / "samples"


class NotFound(Exception):
    pass


class Conflict(Exception):
    pass


# ---------------------------------------------------------------- storage paths
def project_src(settings: Settings, pid: str) -> Path:
    return settings.data_dir / "projects" / pid / "src"


def generation_dir(settings: Settings, gid: str) -> Path:
    return settings.data_dir / "generated" / gid


def executor(settings: Settings | None = None) -> Executor:
    s = settings or get_settings()
    work = s.data_dir / "jobs"
    work.mkdir(parents=True, exist_ok=True)
    return make_executor(s.cobol_executor, image=s.runner_image, work_dir=work.resolve(), queue_dir=s.queue_path.resolve())


# ---------------------------------------------------------------- projects
def create_project(name: str, kind: str, ref: str, res: ImportResult, description: str = "", format_override: str | None = None) -> Project:
    s = get_settings()
    fixtures: dict = {}
    if FIXTURE_FILE in res.files:
        try:
            fixtures = json.loads(res.files[FIXTURE_FILE])
        except json.JSONDecodeError:
            res.skipped.append({"path": FIXTURE_FILE, "reason": "invalid JSON"})
    with session() as db:
        p = Project(
            name=name[:200], description=description, source_kind=kind, source_ref=ref[:500], license=res.license_name,
            format_override=format_override, file_count=len(res.files), line_count=sum(t.count("\n") + 1 for t in res.files.values()),
            fixtures_json=json.dumps(fixtures), import_report_json=json.dumps(res.report()),
        )  # fmt: skip
        db.add(p)
        db.flush()
        root = project_src(s, p.id)
        for rel, text in res.files.items():
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="latin-1", errors="replace") if not _utf8ok(text) else dest.write_text(text, encoding="utf-8")
        return p


def _utf8ok(text: str) -> bool:
    try:
        text.encode("utf-8")
        return True
    except UnicodeEncodeError:
        return False


def sample_import() -> tuple[str, ImportResult, str]:
    root = SAMPLES_DIR / "phoenix-mutual"
    res = ImportResult()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = str(p.relative_to(root))
            res.files[rel] = p.read_text(encoding="utf-8")
            if p.name.upper() == "LICENSE":
                res.license_text = res.files[rel]
                res.license_name = "Apache-2.0"
    desc = "Original sample: Phoenix Mutual auto insurance premium rating (COBOL Phoenix authors, Apache-2.0)."
    return "Phoenix Mutual — Auto Premium Rating", res, desc


def get_project(pid: str) -> Project:
    with session() as db:
        p = db.get(Project, pid)
        if p is None:
            raise NotFound(f"project {pid} not found")
        return p


def list_projects() -> list[Project]:
    with session() as db:
        return list(db.query(Project).order_by(Project.created_at.desc()).all())


def delete_project(pid: str) -> None:
    s = get_settings()
    with session() as db:
        p = db.get(Project, pid)
        if p is None:
            raise NotFound(pid)
        gids = [g.id for g in p.generations]
        db.delete(p)
        db.query(VerificationRun).filter(VerificationRun.project_id == pid).delete()
    shutil.rmtree(s.data_dir / "projects" / pid, ignore_errors=True)
    for g in gids:
        shutil.rmtree(generation_dir(s, g), ignore_errors=True)


def read_sources(pid: str) -> dict[str, str]:
    root = project_src(get_settings(), pid)
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and not p.is_symlink():
            data = p.read_bytes()
            try:
                out[str(p.relative_to(root).as_posix())] = data.decode("utf-8")
            except UnicodeDecodeError:
                out[str(p.relative_to(root).as_posix())] = data.decode("latin-1")
    return out


def read_source_file(pid: str, path: str) -> str:
    root = project_src(get_settings(), pid).resolve()
    target = (root / path).resolve()
    if root not in target.parents or not target.is_file():
        raise NotFound(path)
    data = target.read_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")


_parse_cache: dict[str, tuple[str, ProjectParse]] = {}
_cache_lock = threading.Lock()


def project_parse(p: Project) -> ProjectParse:
    key = f"{p.id}:{p.analyzed_at}"
    with _cache_lock:
        hit = _parse_cache.get(p.id)
        if hit and hit[0] == key:
            return hit[1]
    raw = {k: v for k, v in read_sources(p.id).items() if PurePosixPath(k).suffix.lower() in SOURCE_EXTS}
    pp = parse_project(raw, p.format_override)
    with _cache_lock:
        _parse_cache[p.id] = (key, pp)
    return pp


def analyze_project(pid: str) -> dict:
    p = get_project(pid)
    raw = {k: v for k, v in read_sources(pid).items() if PurePosixPath(k).suffix.lower() in SOURCE_EXTS}
    pp = parse_project(raw, p.format_override)
    analysis = analyze_parse(pp)
    with session() as db:
        row = db.get(Project, pid)
        row.analysis_json = json.dumps(analysis)
        row.analyzed_at = dt.datetime.now(dt.UTC)
        key = f"{row.id}:{row.analyzed_at}"
    with _cache_lock:
        _parse_cache[pid] = (key, pp)
    return analysis


def require_analysis(pid: str) -> tuple[Project, dict]:
    p = get_project(pid)
    a = p.analysis
    if a is None:
        a = analyze_project(pid)
        p = get_project(pid)
    return p, a


def get_fixtures(pid: str) -> dict:
    return json.loads(get_project(pid).fixtures_json or "{}")


def set_fixtures(pid: str, fixtures: dict) -> dict:
    with session() as db:
        p = db.get(Project, pid)
        if p is None:
            raise NotFound(pid)
        p.fixtures_json = json.dumps(fixtures)
    return fixtures


# ---------------------------------------------------------------- rules with verification status
def rules_with_status(pid: str) -> list[dict]:
    _, a = require_analysis(pid)
    rules = a["rules"]
    with session() as db:
        runs = (
            db.query(VerificationRun)
            .join(Generation)
            .filter(VerificationRun.project_id == pid, VerificationRun.status == "completed", Generation.mutation_id.is_(None))
            .order_by(VerificationRun.created_at.desc())
            .all()
        )
        latest: dict[str, VerificationRun] = {}
        for r in runs:
            latest.setdefault(r.generation.entry, r)
        reports = [json.loads(r.report_json) for r in latest.values() if r.report_json]
    if not reports:
        return [
            {**r, "verification": {"status": "NOT_RUN", "statements": len(r["statement_keys"]), "executed": 0, "coverage_pct": 0.0, "failing_cases": 0}}
            for r in rules
        ]
    return rule_status(rules, reports)


# ---------------------------------------------------------------- generation
def mutation_list(pid: str, entry: str) -> list[dict]:
    p = get_project(pid)
    pp = project_parse(p)
    prog = pp.program(entry)
    if prog is None:
        raise NotFound(entry)
    return [m.__dict__ for m in mutation_candidates(prog.program)]


def _fixtures_for(pid: str, entry: str) -> list[dict]:
    fx = get_fixtures(pid)
    return list(fx.get(entry.upper(), []))


def create_generation(pid: str, entry: str, name: str | None, mutation_id: str | None) -> Generation:
    s = get_settings()
    p = get_project(pid)
    require_analysis(pid)
    p = get_project(pid)
    pp = project_parse(p)
    entry = entry.upper()
    if pp.program(entry) is None:
        raise NotFound(f"program {entry} not found in project")
    mutation: Mutation | None = None
    if mutation_id:
        mutation = next((m for m in mutation_candidates(pp.program(entry).program) if m.id == mutation_id), None)
        if mutation is None:
            raise NotFound(f"mutation {mutation_id} not available")
    proj_name = name or f"{entry.lower()}-service"
    fixtures = _fixtures_for(pid, entry)
    try:
        gp = generate_project(pp, entry, proj_name, mutation=mutation, fixtures=fixtures)
    except GenerationError as exc:
        raise Conflict(str(exc))
    with session() as db:
        g = Generation(
            project_id=pid, entry=entry, name=proj_name, mutation_id=mutation.id if mutation else None, mutation_detail=mutation.detail if mutation else None
        )
        db.add(g)
        db.flush()
        out = generation_dir(s, g.id)
        write_project(gp, out)
        summary = {
            "entry": entry,
            "mode": gp.interface.mode,
            "call_tree": gp.call_tree,
            "files": sorted(gp.files),
            "statements": len(gp.traceability),
            "unsupported": gp.unsupported,
            "modules": [
                {"program": m.program_id, "module": f"app/programs/{m.module}.py", "class": m.class_name, "statements": len(m.trace)} for m in gp.modules
            ],
            "endpoint": f"/api/v1/{entry.lower().replace('_', '-')}/execute",
            "fixtures": len(fixtures),
            "mutation": mutation.__dict__ if mutation else None,
            "lines_of_code": sum(v.count("\n") for k, v in gp.files.items() if k.endswith(".py") and "phoenix_runtime" not in k),
        }
        g.summary_json = json.dumps(summary)
        return g


def get_generation(gid: str) -> Generation:
    with session() as db:
        g = db.get(Generation, gid)
        if g is None:
            raise NotFound(f"generation {gid} not found")
        return g


def list_generations(pid: str) -> list[Generation]:
    with session() as db:
        return list(db.query(Generation).filter(Generation.project_id == pid).order_by(Generation.created_at.desc()).all())


def generation_project_dir(gid: str) -> Path:
    return generation_dir(get_settings(), gid)


def generation_file(gid: str, path: str) -> str:
    root = generation_project_dir(gid).resolve()
    target = (root / path).resolve()
    if root not in target.parents or not target.is_file():
        raise NotFound(path)
    return target.read_text()


def generation_zip(gid: str) -> bytes:
    g = get_generation(gid)
    root = generation_project_dir(gid)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(root.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts:
                zf.write(p, f"{g.name}/{p.relative_to(root).as_posix()}")
    return buf.getvalue()


# ---------------------------------------------------------------- verification
_pool: ThreadPoolExecutor | None = None


def pool() -> ThreadPoolExecutor:
    global _pool
    if _pool is None:
        _pool = ThreadPoolExecutor(max_workers=get_settings().worker_threads, thread_name_prefix="phoenix-verify")
    return _pool


class PythonTracer:
    """Statement keys executed by the *generated* Python (our own deterministic code, never the
    uploaded COBOL) for a harness stdin, traced in a subprocess with a timeout and cached by stdin.

    Instances are the ``reaches`` callback of ``generate_cases`` (validity-aware placement)."""

    def __init__(self, project_dir: Path, entry: str, codecs: dict[str, RecordCodec]) -> None:
        from .verify.engine import coverage_map

        self.project_dir = project_dir
        self.entry = entry
        self.codecs = codecs
        self.cmap = coverage_map(json.loads((project_dir / "traceability.json").read_text()))
        self.cache: dict[str, frozenset[str]] = {}
        self.runs = 0  # subprocess invocations

    def trace_stdins(self, stdins: list[str]) -> None:
        from .verify.engine import run_python

        todo = list(dict.fromkeys(s for s in stdins if s not in self.cache))
        if not todo:
            return
        cases = [TestCase(id=f"probe-{i}", kind="probe", description="", stdin=s) for i, s in enumerate(todo)]
        self.runs += 1
        try:
            results = {r["id"]: r for r in run_python(self.project_dir, self.entry, "harness", cases, trace=True)}
        except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
            raise TraceUnavailable(str(exc)) from exc
        if any(str(r.get("error") or "").startswith("python runner failed") for r in results.values()):
            raise TraceUnavailable("generated Python could not be traced")
        for c in cases:
            lines = results.get(c.id, {}).get("lines", [])
            self.cache[c.stdin] = frozenset(self.cmap[(f, n)] for f, n in lines if (f, n) in self.cmap)

    def keys(self, stdin: str) -> frozenset[str]:
        self.trace_stdins([stdin])
        return self.cache[stdin]

    def prefetch(self, inputs_list: list[dict]) -> None:
        self.trace_stdins([encode_inputs(self.codecs, i) for i in inputs_list])

    def __call__(self, inputs: dict, key: str) -> bool:
        return key in self.keys(encode_inputs(self.codecs, inputs))


def fixture_coverage(project_dir: Path, entry: str, fixtures: list[TestCase], tracer: PythonTracer | None = None) -> dict[str, set[str]]:
    """Run fixture cases through the generated Python (our own deterministic code)
    and return the COBOL statement keys each fixture executes."""
    if tracer is None:
        tracer = PythonTracer(project_dir, entry, {})
    tracer.trace_stdins([c.stdin for c in fixtures])
    return {c.id.removeprefix("fixture-"): set(tracer.cache[c.stdin]) for c in fixtures}


def build_cases(pp: ProjectParse, entry: str, fixtures: list[dict], max_cases: int, project_dir: Path | None = None) -> list[TestCase]:
    prog = pp.program(entry).program
    if not prog.using:
        cases = [TestCase(id=f"fixture-{f['id']}", kind="fixture", description=f.get("description", ""), stdin=f.get("stdin", "")) for f in fixtures]
        if not cases:
            cases = [TestCase(id="fixture-empty-stdin", kind="fixture", description="run with empty standard input", stdin="")]
        return cases
    index = prog.item_index()
    total, _ = program_access(prog)
    codecs = {u: RecordCodec(index[u]) for u in prog.using}
    linkage_fixtures = [f for f in fixtures if "inputs" in f]
    coverage = None
    tracer: PythonTracer | None = None
    if project_dir is not None and linkage_fixtures and (project_dir / "traceability.json").is_file():
        base_cases = generate_cases(prog, total.reads, codecs, linkage_fixtures, max_cases=len(linkage_fixtures), n_random=0)
        tracer = PythonTracer(project_dir, entry, codecs)
        try:
            coverage = fixture_coverage(project_dir, entry, [c for c in base_cases if c.kind == "fixture"], tracer)
        except TraceUnavailable:
            log.warning("generated Python could not be traced; boundary placement without coverage")
            coverage, tracer = None, None
    return generate_cases(prog, total.reads, codecs, linkage_fixtures, max_cases=max_cases, fixture_coverage=coverage, reaches=tracer)


def start_verification(gid: str, with_mutation: bool) -> VerificationRun:
    g = get_generation(gid)
    with session() as db:
        run = VerificationRun(generation_id=gid, project_id=g.project_id, status="queued", with_mutation=1 if with_mutation else 0)
        db.add(run)
        db.flush()
        rid = run.id
    pool().submit(_run_verification_safe, rid)
    return get_run(rid)


def _progress(rid: str, msg: str) -> None:
    with session() as db:
        r = db.get(VerificationRun, rid)
        if r is not None:
            r.progress = msg[:500]


def _run_verification_safe(rid: str) -> None:
    try:
        run_verification(rid)
    except Exception as exc:  # noqa: BLE001 - recorded on the run
        log.exception("verification %s failed", rid)
        with session() as db:
            r = db.get(VerificationRun, rid)
            if r:
                r.status = "error"
                r.error = f"{type(exc).__name__}: {exc}"
                r.finished_at = dt.datetime.now(dt.UTC)


def run_verification(rid: str) -> None:
    s = get_settings()
    with session() as db:
        run = db.get(VerificationRun, rid)
        run.status = "running"
        gid = run.generation_id
        with_mut = bool(run.with_mutation)
    g = get_generation(gid)
    p = get_project(g.project_id)
    pp = project_parse(p)
    fixtures = _fixtures_for(p.id, g.entry)
    cases = build_cases(pp, g.entry, fixtures, s.max_cases, project_dir=generation_dir(s, gid))
    _progress(rid, f"prepared {len(cases)} test cases")
    mutation = None
    if g.mutation_id:
        mutation = next((m for m in mutation_candidates(pp.program(g.entry).program) if m.id == g.mutation_id), None)
    gp = generate_project(pp, g.entry, g.name, mutation=mutation, fixtures=fixtures)
    out_dir = generation_dir(s, gid)
    report = verify(pp, gp, out_dir, cases, executor(s), progress=lambda m: _progress(rid, m))
    report["generation_id"] = gid
    report["mutation"] = mutation.__dict__ if mutation else None
    mut_result = None
    if with_mut and not g.mutation_id:
        ref = {c["id"]: c["cobol"]["stdout"] for c in report["cases"] if c["cobol"] and c["status"] in ("VERIFIED", "FAILED")}
        reference_kind = "gnucobol"
        if not ref:
            ref = {c["id"]: c["python"]["stdout"] for c in report["cases"]}
            reference_kind = "generated-python-baseline"
        mut_result = mutation_analysis(pp, gp, out_dir, cases, ref, limit=s.mutation_limit, progress=lambda m: _progress(rid, m))
        mut_result["reference"] = reference_kind
    if not g.mutation_id:
        _write_regression_cases(out_dir, report)
    with session() as db:
        r = db.get(VerificationRun, rid)
        r.status = "completed"
        r.progress = "done"
        r.summary_json = json.dumps(report["summary"])
        r.report_json = json.dumps(report)
        r.mutation_json = json.dumps(mut_result) if mut_result else None
        r.finished_at = dt.datetime.now(dt.UTC)


def _write_regression_cases(out_dir: Path, report: dict) -> None:
    """Store VERIFIED cases with the actual GnuCOBOL output as generated regression tests."""
    verified = [c for c in report["cases"] if c["status"] == "VERIFIED" and c["cobol"]]
    if not verified:
        return
    data = {
        "entry": report["entry"],
        "mode": report["mode"],
        "date": FIXED_DATETIME,
        "source": f"GnuCOBOL output ({report['executor'].get('cobc_version', '')}) captured by COBOL Phoenix verification",
        "cases": [{"id": c["id"], "description": c["description"], "stdin": c["stdin"], "expected_stdout": c["cobol"]["stdout"]} for c in verified],
    }
    (out_dir / "tests" / "cases.json").write_text(json.dumps(data, indent=1))


def get_run(rid: str) -> VerificationRun:
    with session() as db:
        r = db.get(VerificationRun, rid)
        if r is None:
            raise NotFound(f"run {rid} not found")
        return r


def list_runs(pid: str) -> list[tuple[VerificationRun, Generation]]:
    with session() as db:
        rows = (
            db.query(VerificationRun, Generation).join(Generation).filter(VerificationRun.project_id == pid).order_by(VerificationRun.created_at.desc()).all()
        )
        return [(r, g) for r, g in rows]


def latest_run(pid: str, include_mutants: bool = False) -> VerificationRun | None:
    for r, g in list_runs(pid):
        if r.status == "completed" and (include_mutants or g.mutation_id is None):
            return r
    return None
