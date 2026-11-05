"""COBOL Phoenix HTTP API."""

from __future__ import annotations

import json
import logging
from pathlib import PurePosixPath
from typing import Annotated

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field

from .. import reports, services
from ..ai.providers import get_provider
from ..cobol.project import SOURCE_EXTS
from ..config import VERSION, get_settings
from ..db import Generation, Project, VerificationRun, init_db
from .importer import ImportError_, github_archive_url, import_local_dir, import_uploads, import_zip, parse_github_repo

log = logging.getLogger("phoenix.api")

app = FastAPI(title="COBOL Phoenix API", version=VERSION, description="Evidence-backed COBOL to Python modernization.")
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.exception_handler(services.NotFound)
def _nf(_: Request, exc: services.NotFound) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(services.Conflict)
def _cf(_: Request, exc: services.Conflict) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(ImportError_)
def _ie(_: Request, exc: ImportError_) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


# ---------------------------------------------------------------- serializers
def project_out(p: Project) -> dict:
    a = p.analysis
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "source_kind": p.source_kind,
        "source_ref": p.source_ref,
        "license": p.license,
        "format_override": p.format_override,
        "file_count": p.file_count,
        "line_count": p.line_count,
        "created_at": p.created_at.isoformat(),
        "analyzed_at": p.analyzed_at.isoformat() if p.analyzed_at else None,
        "overview": a["overview"] if a else None,
        "import_report": json.loads(p.import_report_json or "{}"),
    }


def generation_out(g: Generation) -> dict:
    return {"id": g.id, "project_id": g.project_id, "entry": g.entry, "name": g.name, "mutation_id": g.mutation_id, "mutation_detail": g.mutation_detail, "created_at": g.created_at.isoformat(), "summary": json.loads(g.summary_json or "{}")}


def run_out(r: VerificationRun, full: bool = False) -> dict:
    d = {
        "id": r.id,
        "generation_id": r.generation_id,
        "project_id": r.project_id,
        "status": r.status,
        "progress": r.progress,
        "with_mutation": bool(r.with_mutation),
        "created_at": r.created_at.isoformat(),
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        "summary": json.loads(r.summary_json or "{}"),
        "error": r.error,
    }
    if full:
        d["report"] = json.loads(r.report_json) if r.report_json else None
        d["mutation"] = json.loads(r.mutation_json) if r.mutation_json else None
    return d


# ---------------------------------------------------------------- health / dashboard
@app.get("/api/health")
def health() -> dict:
    ok, detail = services.executor().available()
    prov = get_provider(_settings)
    return {"status": "ok", "version": VERSION, "executor": {"name": _settings.cobol_executor, "available": ok, "detail": detail}, "llm": {"provider": prov.name}}


@app.get("/api/dashboard")
def dashboard() -> dict:
    projects = services.list_projects()
    out = []
    totals = {"projects": len(projects), "programs": 0, "rules": 0, "generations": 0, "runs": 0, "cases_verified": 0, "cases_failed": 0}
    recent_runs = []
    for p in projects:
        po = project_out(p)
        if po["overview"]:
            totals["programs"] += po["overview"]["programs"]
            totals["rules"] += po["overview"]["business_rules"]
        gens = services.list_generations(p.id)
        totals["generations"] += len(gens)
        runs = services.list_runs(p.id)
        totals["runs"] += len(runs)
        latest = None
        for r, g in runs:
            s = json.loads(r.summary_json or "{}")
            if r.status == "completed" and g.mutation_id is None:
                totals["cases_verified"] += s.get("verified", 0)
                totals["cases_failed"] += s.get("failed", 0)
                latest = latest or {**s, "entry": g.entry, "run_id": r.id}
            recent_runs.append({**run_out(r), "entry": g.entry, "project_name": p.name, "mutation_id": g.mutation_id})
        po["latest_verification"] = latest
        po["generations"] = len(gens)
        out.append(po)
    recent_runs.sort(key=lambda r: r["created_at"], reverse=True)
    return {"totals": totals, "projects": out, "recent_runs": recent_runs[:10]}


# ---------------------------------------------------------------- projects
@app.get("/api/projects")
def projects() -> list[dict]:
    return [project_out(p) for p in services.list_projects()]


@app.post("/api/projects/sample", status_code=201)
def import_sample() -> dict:
    name, res, desc = services.sample_import()
    p = services.create_project(name, "sample", "bundled", res, desc)
    services.analyze_project(p.id)
    return project_out(services.get_project(p.id))


def _fmt(fmt: str | None) -> str | None:
    if fmt in (None, "", "auto"):
        return None
    if fmt not in ("fixed", "free"):
        raise HTTPException(400, "format must be auto, fixed or free")
    return fmt


async def _read_limited(f: UploadFile, limit: int) -> bytes:
    data = await f.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"upload exceeds {limit // (1024 * 1024)} MB")
    return data


@app.post("/api/projects/upload", status_code=201)
async def upload(files: Annotated[list[UploadFile], File()], name: Annotated[str, Form()] = "Uploaded project", source_format: Annotated[str, Form()] = "auto") -> dict:
    limit = _settings.max_upload_mb * 1024 * 1024
    items: list[tuple[str, bytes]] = []
    if len(files) == 1 and (files[0].filename or "").lower().endswith(".zip"):
        data = await _read_limited(files[0], limit)
        res = import_zip(data, _settings)
        kind, ref = "zip", files[0].filename or ""
    else:
        for f in files:
            items.append((f.filename or "unnamed", await _read_limited(f, limit)))
        res = import_uploads(items, _settings)
        kind, ref = "upload", f"{len(items)} files"
    p = services.create_project(name.strip() or "Uploaded project", kind, ref, res, format_override=_fmt(source_format))
    services.analyze_project(p.id)
    return project_out(services.get_project(p.id))


class GithubImport(BaseModel):
    repo: str = Field(description="owner/name or https://github.com/owner/name")
    ref: str = "HEAD"
    name: str | None = None
    source_format: str = "auto"
    subdir: str | None = Field(default=None, description="optional sub-directory to import")


@app.post("/api/projects/github", status_code=201)
def import_github(body: GithubImport) -> dict:
    if not _settings.allow_github_import:
        raise HTTPException(403, "GitHub import is disabled (PHOENIX_ALLOW_GITHUB_IMPORT=false)")
    owner, repo = parse_github_repo(body.repo)
    url = github_archive_url(owner, repo, body.ref)
    limit = _settings.max_upload_mb * 1024 * 1024
    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=60) as r:
            if r.status_code != 200:
                raise HTTPException(400, f"GitHub returned HTTP {r.status_code} for {owner}/{repo}@{body.ref}")
            if not str(r.url).startswith("https://codeload.github.com/"):
                raise HTTPException(400, "unexpected redirect target")
            buf = bytearray()
            for chunk in r.iter_bytes():
                buf.extend(chunk)
                if len(buf) > limit:
                    raise HTTPException(413, "repository archive too large")
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"could not download repository: {exc}")
    res = import_zip(bytes(buf), _settings)
    if body.subdir:
        prefix = body.subdir.strip("/") + "/"
        res.files = {k[len(prefix) :]: v for k, v in res.files.items() if k.startswith(prefix)}
        if not any(PurePosixPath(k).suffix.lower() in SOURCE_EXTS for k in res.files):
            raise HTTPException(400, f"no COBOL sources under {body.subdir}")
    p = services.create_project(body.name or f"{owner}/{repo}", "github", f"https://github.com/{owner}/{repo} @ {body.ref}", res, format_override=_fmt(body.source_format))
    services.analyze_project(p.id)
    return project_out(services.get_project(p.id))


class LocalImport(BaseModel):
    path: str
    name: str | None = None
    source_format: str = "auto"


@app.post("/api/projects/local", status_code=201)
def import_local(body: LocalImport) -> dict:
    res = import_local_dir(body.path, _settings)
    p = services.create_project(body.name or PurePosixPath(body.path).name, "local", body.path, res, format_override=_fmt(body.source_format))
    services.analyze_project(p.id)
    return project_out(services.get_project(p.id))


@app.get("/api/projects/{pid}")
def project(pid: str) -> dict:
    return project_out(services.get_project(pid))


@app.delete("/api/projects/{pid}", status_code=204)
def delete_project(pid: str) -> Response:
    services.delete_project(pid)
    return Response(status_code=204)


@app.get("/api/projects/{pid}/files")
def files(pid: str) -> list[dict]:
    p, a = services.require_analysis(pid)
    return a["files"]


@app.get("/api/projects/{pid}/files/content")
def file_content(pid: str, path: str = Query(..., max_length=500)) -> dict:
    text = services.read_source_file(pid, path)
    return {"path": path, "text": text, "lines": text.count("\n") + 1}


@app.post("/api/projects/{pid}/analyze")
def analyze(pid: str) -> dict:
    services.analyze_project(pid)
    return project_out(services.get_project(pid))


@app.get("/api/projects/{pid}/analysis")
def analysis(pid: str) -> dict:
    p, a = services.require_analysis(pid)
    return {"project": project_out(p), **{k: a[k] for k in ("overview", "programs", "unsupported", "diagnostics", "files")}}


@app.get("/api/projects/{pid}/graph")
def graph(pid: str) -> dict:
    _, a = services.require_analysis(pid)
    return a["graph"]


@app.get("/api/projects/{pid}/rules")
def rules(pid: str) -> list[dict]:
    return services.rules_with_status(pid)


@app.post("/api/projects/{pid}/rules/{rule_id}/explain")
def explain(pid: str, rule_id: str) -> dict:
    rules_ = services.rules_with_status(pid)
    rule = next((r for r in rules_ if r["id"] == rule_id), None)
    if rule is None:
        raise HTTPException(404, "rule not found")
    text = services.read_source_file(pid, rule["file"]).splitlines()
    snippet = "\n".join(f"{n:5d} {text[n - 1]}" for n in range(rule["line_start"], min(rule["line_end"], len(text)) + 1))
    prov = get_provider(_settings)
    try:
        exp = prov.explain(rule, snippet)
    except Exception as exc:  # noqa: BLE001 - fall back to deterministic text
        log.warning("LLM provider failed: %s", exc)
        from ..ai.providers import DeterministicProvider

        exp = DeterministicProvider().explain(rule, snippet)
        exp.text += f" (LLM provider unavailable: {type(exc).__name__})"
    return {"rule_id": rule_id, "text": exp.text, "provider": exp.provider, "model": exp.model, "advisory": exp.advisory, "evidence": {"file": rule["file"], "line_start": rule["line_start"], "line_end": rule["line_end"]}}


@app.get("/api/projects/{pid}/fixtures")
def get_fixtures(pid: str) -> dict:
    return services.get_fixtures(pid)


@app.put("/api/projects/{pid}/fixtures")
def put_fixtures(pid: str, body: dict) -> dict:
    if not all(isinstance(v, list) for v in body.values()):
        raise HTTPException(400, "fixtures must map PROGRAM-ID to a list of cases")
    for cases in body.values():
        for c in cases:
            if not isinstance(c, dict) or "id" not in c or not ({"inputs", "stdin"} & set(c)):
                raise HTTPException(400, "each fixture needs an 'id' and either 'inputs' or 'stdin'")
    return services.set_fixtures(pid, body)


@app.get("/api/projects/{pid}/programs/{program_id}/mutations")
def mutations(pid: str, program_id: str) -> list[dict]:
    return services.mutation_list(pid, program_id)


# ---------------------------------------------------------------- generation
class GenerateBody(BaseModel):
    entry: str = Field(pattern=r"^[A-Za-z0-9_-]{1,30}$")
    name: str | None = Field(default=None, pattern=r"^[A-Za-z0-9 _.-]{1,60}$")
    mutation_id: str | None = Field(default=None, max_length=200)


@app.post("/api/projects/{pid}/generations", status_code=201)
def generate(pid: str, body: GenerateBody) -> dict:
    return generation_out(services.create_generation(pid, body.entry, body.name, body.mutation_id))


@app.get("/api/projects/{pid}/generations")
def generations(pid: str) -> list[dict]:
    return [generation_out(g) for g in services.list_generations(pid)]


@app.get("/api/generations/{gid}")
def generation(gid: str) -> dict:
    g = services.get_generation(gid)
    d = generation_out(g)
    root = services.generation_project_dir(gid)
    d["interface"] = json.loads((root / "app" / "interface.json").read_text())
    d["schemas"] = (root / "app" / "schemas.py").read_text()
    return d


@app.get("/api/generations/{gid}/file")
def generation_file(gid: str, path: str = Query(..., max_length=300)) -> dict:
    text = services.generation_file(gid, path)
    return {"path": path, "text": text}


@app.get("/api/generations/{gid}/traceability")
def traceability(gid: str) -> list[dict]:
    return json.loads(services.generation_file(gid, "traceability.json"))


@app.get("/api/generations/{gid}/download")
def download(gid: str) -> Response:
    g = services.get_generation(gid)
    data = services.generation_zip(gid)
    return Response(content=data, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{g.name}.zip"'})


class VerifyBody(BaseModel):
    mutation_analysis: bool = False


@app.post("/api/generations/{gid}/verify", status_code=202)
def start_verify(gid: str, body: VerifyBody) -> dict:
    return run_out(services.start_verification(gid, body.mutation_analysis))


@app.get("/api/runs/{rid}")
def run(rid: str) -> dict:
    return run_out(services.get_run(rid), full=True)


@app.get("/api/projects/{pid}/runs")
def runs(pid: str) -> list[dict]:
    return [{**run_out(r), "entry": g.entry, "mutation_id": g.mutation_id, "mutation_detail": g.mutation_detail} for r, g in services.list_runs(pid)]


# ---------------------------------------------------------------- exports
EXPORTS = {
    "rules.md": "text/markdown",
    "rules.json": "application/json",
    "graph.json": "application/json",
    "migration-report.md": "text/markdown",
    "verification-report.md": "text/markdown",
    "verification-report.json": "application/json",
    "traceability.json": "application/json",
}


@app.get("/api/projects/{pid}/export/{kind}")
def export(pid: str, kind: str, run_id: str | None = None, generation_id: str | None = None) -> Response:
    if kind not in EXPORTS:
        raise HTTPException(404, "unknown export")
    p, a = services.require_analysis(pid)
    po = project_out(p)
    rules_ = services.rules_with_status(pid)
    import re

    filename = re.sub(r"[^A-Za-z0-9._-]+", "_", p.name).strip("_")[:40] + f"-{kind}"
    if kind == "rules.md":
        body = reports.rules_markdown(po, rules_)
    elif kind == "rules.json":
        body = json.dumps(rules_, indent=1)
    elif kind == "graph.json":
        body = json.dumps(a["graph"], indent=1)
    elif kind == "traceability.json":
        gid = generation_id or next((g.id for g in services.list_generations(pid) if g.mutation_id is None), None)
        if gid is None:
            raise HTTPException(404, "no generation yet")
        body = services.generation_file(gid, "traceability.json")
    else:
        r = services.get_run(run_id) if run_id else services.latest_run(pid)
        report = json.loads(r.report_json) if r and r.report_json else None
        if kind == "migration-report.md":
            gens = [generation_out(g) for g in services.list_generations(pid)]
            body = reports.migration_markdown(po, a, rules_, gens, report)
        else:
            if report is None:
                raise HTTPException(404, "no completed verification run")
            mut = json.loads(r.mutation_json) if r.mutation_json else None
            body = reports.verification_markdown(po, report, mut) if kind.endswith(".md") else json.dumps({"report": report, "mutation": mut}, indent=1)
    return PlainTextResponse(body, media_type=EXPORTS[kind], headers={"Content-Disposition": f'attachment; filename="{filename}"'})
