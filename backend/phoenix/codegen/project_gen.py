"""Assemble a complete, executable Python/FastAPI project from parsed programs."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..analysis.dataflow import program_access
from ..cobol import ir
from ..cobol.project import ProjectParse
from .program_gen import GeneratedModule, Mutation, ProgramGenerator, class_name, module_name, py_ident

RUNTIME_PATH = Path(__file__).with_name("phoenix_runtime.py")
GENERATOR_VERSION = "1.0.0"


class GenerationError(Exception):
    pass


@dataclass
class InterfaceLeaf:
    name: str
    py: str
    attr: str
    kind: str  # alnum | numeric | edited | group
    size: int
    digits: int = 0
    scale: int = 0
    signed: bool = False
    picture: str = ""
    role: str = "both"  # input | output | both
    loc: str = ""


@dataclass
class InterfaceTable:
    name: str
    py: str
    attr: str
    occurs: int
    children: list = field(default_factory=list)
    loc: str = ""


@dataclass
class InterfaceParam:
    name: str
    py: str
    region: str
    root_attr: str
    size: int
    display_only: bool
    inputs: list = field(default_factory=list)  # leaves/tables
    outputs: list = field(default_factory=list)


@dataclass
class Interface:
    entry: str
    mode: str  # linkage | main
    params: list[InterfaceParam] = field(default_factory=list)


@dataclass
class GeneratedProject:
    name: str
    entry: str
    files: dict[str, str]
    modules: list[GeneratedModule]
    interface: Interface
    traceability: list[dict]
    unsupported: list[dict]
    call_tree: list[str]
    mutation: str | None = None


def call_tree(pp: ProjectParse, entry: str) -> tuple[list[str], list[str]]:
    """Programs reachable by static CALL "literal" from entry; returns (found, missing)."""
    order: list[str] = []
    missing: list[str] = []
    stack = [entry.upper()]
    while stack:
        pid = stack.pop(0)
        if pid in order:
            continue
        prog = pp.program(pid)
        if prog is None:
            if pid not in missing:
                missing.append(pid)
            continue
        order.append(pid)
        for par in prog.program.paragraphs:
            for s in ir.walk_statements(par.statements):
                if isinstance(s, ir.Call) and isinstance(s.program, ir.Literal):
                    stack.append(s.program.value.strip().upper())
    return order, missing


def _is_display_only(item: ir.DataItem) -> bool:
    stack = [item]
    while stack:
        x = stack.pop()
        if x.usage not in ("DISPLAY",):
            return False
        stack.extend(x.children)
    return True


def build_interface(prog: ir.Program, mod: GeneratedModule) -> Interface:
    if not prog.using:
        return Interface(entry=prog.program_id, mode="main")
    index = prog.item_index()
    total, _ = program_access(prog)
    reads, writes = total.reads, total.writes
    iface = Interface(entry=prog.program_id, mode="linkage")
    used_py: set[str] = set()

    def uniq(base: str) -> str:
        n, k = base, 2
        while n in used_py:
            n = f"{base}_{k}"
            k += 1
        used_py.add(n)
        return n

    def leaf(it: ir.DataItem, role: str) -> InterfaceLeaf:
        pic = it.picture
        kind = "alnum"
        if pic is not None and pic.category == "numeric":
            kind = "numeric"
        elif pic is not None and pic.category == "numeric-edited":
            kind = "edited"
        elif it.children or pic is None:
            kind = "group"
        return InterfaceLeaf(
            name=it.name, py=py_ident(it.name), attr=mod.attr_of[it.id], kind=kind, size=it.size,
            digits=pic.digits if pic else 0, scale=pic.scale if pic else 0, signed=pic.signed if pic else False,
            picture=pic.raw if pic else "", role=role, loc=f"{it.loc.file}:{it.loc.line}",
        )  # fmt: skip

    def build(node: ir.DataItem, want: set[str], role: str):
        out = []
        for ch in node.children:
            if ch.is_filler or ch.redefines:
                continue
            if ch.occurs and ch.children:
                sub = build(ch, want, role)
                if sub:
                    out.append(InterfaceTable(ch.name, py_ident(ch.name), mod.attr_of[ch.id], ch.occurs, sub, f"{ch.loc.file}:{ch.loc.line}"))
            elif ch.children:
                out.extend(build(ch, want, role))
            elif ch.id in want:
                if ch.occurs:
                    lf = leaf(ch, role)
                    out.append(InterfaceTable(ch.name, py_ident(ch.name), mod.attr_of[ch.id], ch.occurs, [lf], lf.loc))
                else:
                    out.append(leaf(ch, role))
        return out

    for uid in prog.using:
        root = index[uid]
        param = InterfaceParam(
            name=root.name, py=uniq(py_ident(root.name)), region=mod.region_of[root.id], root_attr=mod.attr_of[root.id],
            size=root.size, display_only=_is_display_only(root),
        )  # fmt: skip
        if root.children:
            param.inputs = build(root, reads, "input")
            param.outputs = build(root, writes, "output")
        else:
            if root.id in reads:
                param.inputs = [leaf(root, "input")]
            if root.id in writes:
                param.outputs = [leaf(root, "output")]
        iface.params.append(param)
    return iface


def _camel(s: str) -> str:
    return "".join(w.capitalize() for w in re.split(r"[^0-9A-Za-z]+", s) if w)


class SchemaWriter:
    """Writes Pydantic models for the interface."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self.models: set[str] = set()

    def field_decl(self, lf: InterfaceLeaf, for_input: bool) -> str:
        desc = f"COBOL {lf.name}" + (f" PIC {lf.picture}" if lf.picture else "") + f" ({lf.loc})"
        if lf.kind == "numeric":
            cons = [f"max_digits={lf.digits}", f"decimal_places={lf.scale}"]
            if not lf.signed:
                cons.append("ge=0")
            c = ", ".join(cons) if for_input else ""
            return f"    {lf.py}: Decimal = Field(default=Decimal(0){', ' + c if c else ''}, description={desc!r})"
        c = f", max_length={lf.size}" if for_input else ""
        return f"    {lf.py}: str = Field(default=''{c}, description={desc!r})"

    def model(self, name: str, nodes: list, for_input: bool) -> str:
        body: list[str] = []
        for n in nodes:
            if isinstance(n, InterfaceTable):
                sub = self.model(f"{name}{_camel(n.name)}Item", n.children, for_input)
                lim = f", max_length={n.occurs}" if for_input else ""
                body.append(
                    f"    {n.py}: list[{sub}] = Field(default_factory=list{lim}, description={('COBOL ' + n.name + ' OCCURS ' + str(n.occurs) + ' (' + n.loc + ')')!r})"
                )
            else:
                body.append(self.field_decl(n, for_input))
        cls = name
        k = 2
        while cls in self.models:
            cls = f"{name}{k}"
            k += 1
        self.models.add(cls)
        self.lines.append(f"class {cls}(BaseModel):")
        self.lines.append("    model_config = ConfigDict(extra='forbid')" if for_input else "    model_config = ConfigDict(extra='ignore')")
        self.lines.extend(body or ["    pass"])
        self.lines.append("")
        self.lines.append("")
        return cls


def generate_project(pp: ProjectParse, entry: str, project_name: str, mutation: Mutation | None = None, fixtures: list[dict] | None = None) -> GeneratedProject:
    entry = entry.upper()
    if pp.program(entry) is None:
        raise GenerationError(f"program {entry} not found")
    order, missing = call_tree(pp, entry)
    sources = {f.path: f.text.splitlines() for f in pp.files}
    modules: list[GeneratedModule] = []
    for pid in order:
        prog = pp.program(pid).program
        mut = mutation if (mutation and mutation.file in {prog.file} | {c["resolved"] for c in prog.copybooks if c.get("resolved")}) else None
        if mutation and mut is None and pid == entry:
            mut = mutation
        modules.append(ProgramGenerator(prog, sources, mut).generate())
    entry_prog = pp.program(entry).program
    entry_mod = modules[0]
    iface = build_interface(entry_prog, entry_mod)
    pkg = py_ident(project_name)
    files: dict[str, str] = {}
    files["app/__init__.py"] = f'"""Generated by COBOL Phoenix {GENERATOR_VERSION} from {entry}."""\n'
    files["app/phoenix_runtime.py"] = RUNTIME_PATH.read_text()
    reg_lines = ['"""Registry of translated programs (PROGRAM-ID -> class)."""', ""]
    for m in modules:
        files[f"app/programs/{m.module}.py"] = m.source
        reg_lines.append(f"from .{m.module} import {m.class_name}")
    reg_lines += ["", "REGISTRY = {"] + [f"    {m.program_id!r}: {m.class_name}," for m in modules] + ["}", ""]
    files["app/programs/__init__.py"] = "\n".join(reg_lines)
    files["app/interface.json"] = json.dumps(asdict(iface), indent=2)
    files["app/schemas.py"] = _schemas(iface)
    files["app/service.py"] = _service(iface, entry_mod)
    files["app/main.py"] = _main(iface, project_name)
    files["app/cli.py"] = CLI_TEMPLATE
    traceability = []
    for m in modules:
        for t in m.trace:
            traceability.append(
                {
                    "python_file": f"app/programs/{m.module}.py",
                    "python_start": t.py_start,
                    "python_end": t.py_end,
                    "cobol_file": t.file,
                    "cobol_start": t.line,
                    "cobol_end": t.end_line,
                    "construct": t.kind,
                    "paragraph": t.paragraph,
                    "program": m.program_id,
                }
            )
    files["traceability.json"] = json.dumps(traceability, indent=1)
    cases = fixtures or []
    files["tests/cases.json"] = json.dumps({"entry": entry, "mode": iface.mode, "source": "fixtures", "cases": cases}, indent=2)
    files["tests/__init__.py"] = ""
    files["tests/test_cases.py"] = TEST_CASES_TEMPLATE
    files["tests/test_api.py"] = _test_api(iface)
    files["requirements.txt"] = "fastapi==0.115.12\npydantic==2.11.4\nuvicorn==0.34.2\nhttpx==0.28.1\npytest==8.3.5\n"
    files["pytest.ini"] = "[pytest]\ntestpaths = tests\n"
    files["Dockerfile"] = DOCKERFILE_TEMPLATE
    unsupported = [dict(u, program=m.program_id) for m in modules for u in m.unsupported]
    files["README.md"] = _readme(project_name, entry, order, missing, iface, modules, unsupported, mutation)
    del pkg
    return GeneratedProject(
        name=project_name, entry=entry, files=files, modules=modules, interface=iface, traceability=traceability,
        unsupported=unsupported, call_tree=order, mutation=mutation.id if mutation else None,
    )  # fmt: skip


# ---------------------------------------------------------------- templates
def _schemas(iface: Interface) -> str:
    sw = SchemaWriter()
    head = [
        '"""Pydantic request/response models derived from the COBOL record layouts."""',
        "",
        "from __future__ import annotations",
        "",
        "from decimal import Decimal",
        "",
        "from pydantic import BaseModel, ConfigDict, Field",
        "",
        "",
    ]
    base = _camel(iface.entry)
    if iface.mode == "main":
        sw.lines += [
            f"class {base}Request(BaseModel):",
            "    model_config = ConfigDict(extra='forbid')",
            "    stdin_lines: list[str] = Field(default_factory=list, max_length=10000, description='Lines read by ACCEPT statements')",
            "",
            "",
            f"class {base}Response(BaseModel):",
            "    stdout: str",
            "    status: str",
            "",
        ]
        return "\n".join(head + sw.lines)
    req_fields, resp_fields = [], []
    for p in iface.params:
        if p.inputs:
            m = sw.model(f"{base}{_camel(p.name)}Input", p.inputs, True)
            req_fields.append(f"    {p.py}: {m} = Field(default_factory={m}, description={('USING parameter ' + p.name)!r})")
        if p.outputs:
            m = sw.model(f"{base}{_camel(p.name)}Output", p.outputs, False)
            resp_fields.append(f"    {p.py}: {m}")
    sw.lines += [f"class {base}Request(BaseModel):", "    model_config = ConfigDict(extra='forbid')"] + (req_fields or ["    pass"]) + ["", ""]
    sw.lines += [f"class {base}Response(BaseModel):", "    status: str = Field(description='completed | stopped (STOP RUN)')"] + resp_fields + [""]
    return "\n".join(head + sw.lines)


def _service(iface: Interface, mod: GeneratedModule) -> str:
    base = _camel(iface.entry)
    return f'''"""Service layer: request -> COBOL record bytes -> translated program -> response."""

from __future__ import annotations

import datetime as dt
import json
import os
from decimal import Decimal
from pathlib import Path

from . import phoenix_runtime as rt
from .programs import REGISTRY
from .schemas import {base}Request, {base}Response

ENTRY = {iface.entry!r}
INTERFACE = json.loads((Path(__file__).with_name("interface.json")).read_text())


def today() -> dt.datetime:
    fixed = os.environ.get("PHOENIX_FIXED_DATETIME")
    return dt.datetime.strptime(fixed, "%Y%m%d%H%M%S") if fixed else dt.datetime.now()


def _set(prog, nodes, data, subs=()):
    for n in nodes:
        key = n["py"]
        if "occurs" in n:
            for k, item in enumerate((data or {{}}).get(key, []) or []):
                _set(prog, n["children"], item, subs + (k + 1,))
            continue
        if data is None or key not in data:
            continue
        f = getattr(prog, n["attr"])
        f = f.at(*subs) if subs else f
        value = data[key]
        if n["kind"] == "numeric":
            f.store(Decimal(str(value)))
        else:
            rt.move(str(value), f)


def _get(prog, nodes, subs=()):
    out = {{}}
    for n in nodes:
        if "occurs" in n:
            out[n["py"]] = [_get(prog, n["children"], subs + (k + 1,)) for k in range(n["occurs"])]
            continue
        f = getattr(prog, n["attr"])
        f = f.at(*subs) if subs else f
        if n["kind"] == "numeric":
            out[n["py"]] = f.value
        else:
            out[n["py"]] = f.text().rstrip(" ")
    return out


def new_context(stdin_lines=None) -> rt.RunContext:
    return rt.RunContext(stdin_lines=stdin_lines, today=today(), registry=REGISTRY)


def execute(req: {base}Request) -> {base}Response:
    ctx = new_context()
    if INTERFACE["mode"] == "main":
        ctx.stdin = list(req.stdin_lines)
        prog = ctx.program(ENTRY)
        status = "completed"
        try:
            prog.run()
        except rt.StopRun:
            status = "stopped"
        return {base}Response(stdout=ctx.output(), status=status)
    prog = ctx.program(ENTRY)
    data = req.model_dump()
    regions = []
    for p in INTERFACE["params"]:
        region = rt.Region(p["name"], p["size"])
        getattr(prog, p["region"]).bind(region.buf, 0)
        rt.initialize(getattr(prog, p["root_attr"]), fillers=True)
        _set(prog, p["inputs"], data.get(p["py"]))
        regions.append(rt.Group(region, 0, region.size, p["name"]))
    status = "completed"
    try:
        prog.call(*regions)
    except rt.StopRun:
        status = "stopped"
    payload = {{"status": status}}
    for p in INTERFACE["params"]:
        getattr(prog, p["region"]).bind(regions[INTERFACE["params"].index(p)].region.buf, 0)
        if p["outputs"]:
            payload[p["py"]] = _get(prog, p["outputs"])
    return {base}Response(**payload)
'''


def _main(iface: Interface, project_name: str) -> str:
    base = _camel(iface.entry)
    slug = iface.entry.lower().replace("_", "-")
    return f'''"""FastAPI application exposing the translated COBOL capability."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI

from . import service
from .schemas import {base}Request, {base}Response

app = FastAPI(
    title={(project_name + " (generated by COBOL Phoenix)")!r},
    version="1.0.0",
    description="Python translation of COBOL program {iface.entry}. Every function maps back to COBOL source lines (see /api/v1/traceability).",
)

ROOT = Path(__file__).resolve().parent.parent


@app.get("/health")
def health() -> dict:
    return {{"status": "ok", "program": service.ENTRY}}


@app.post("/api/v1/{slug}/execute", response_model={base}Response)
def execute(req: {base}Request) -> {base}Response:
    """Run {iface.entry} with the given inputs."""
    return service.execute(req)


@app.get("/api/v1/traceability")
def traceability() -> list[dict]:
    return json.loads((ROOT / "traceability.json").read_text())
'''


def _test_api(iface: Interface) -> str:
    slug = iface.entry.lower().replace("_", "-")
    return f"""from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["program"] == {iface.entry!r}


def test_execute_with_defaults() -> None:
    r = client.post("/api/v1/{slug}/execute", json={{}})
    assert r.status_code == 200, r.text
    assert r.json()["status"] in ("completed", "stopped")


def test_rejects_unknown_fields() -> None:
    r = client.post("/api/v1/{slug}/execute", json={{"not_a_cobol_field": 1}})
    assert r.status_code == 422


def test_traceability_is_exposed() -> None:
    r = client.get("/api/v1/traceability")
    assert r.status_code == 200
    assert len(r.json()) > 0
"""


def _readme(
    name: str,
    entry: str,
    order: list[str],
    missing: list[str],
    iface: Interface,
    modules: list[GeneratedModule],
    unsupported: list[dict],
    mutation: Mutation | None,
) -> str:
    slug = entry.lower().replace("_", "-")
    lines = [
        f"# {name}",
        "",
        f"Python/FastAPI translation of COBOL program **{entry}**, generated by COBOL Phoenix {GENERATOR_VERSION}.",
        "",
    ]
    if mutation:
        lines += [f"> **WARNING:** this build contains a deliberately injected fault (`{mutation.id}`: {mutation.detail}) for verification demos.", ""]
    lines += [
        "## Programs",
        "",
        "| PROGRAM-ID | Module | Statements traced |",
        "|---|---|---|",
    ]
    for m in modules:
        lines.append(f"| {m.program_id} | `app/programs/{m.module}.py` | {len(m.trace)} |")
    if missing:
        lines += ["", f"Called programs not found in the project (calls will raise `ProgramNotFound`): {', '.join(missing)}"]
    lines += [
        "",
        "## Run",
        "",
        "```bash",
        "pip install -r requirements.txt",
        "uvicorn app.main:app --port 8080",
        "pytest",
        "```",
        "",
        f"`POST /api/v1/{slug}/execute` — interface mode: **{iface.mode}**.",
        "",
        "## Semantics",
        "",
        "* Numbers are `decimal.Decimal`; COBOL truncation, ROUNDED (half away from zero) and sign rules are implemented in `app/phoenix_runtime.py`.",
        "* Storage is byte based, so REDEFINES, group moves and CALL BY REFERENCE behave like COBOL.",
        "* `traceability.json` maps every generated statement to its COBOL file and line range.",
        "",
        "## Unsupported constructs",
        "",
    ]
    if unsupported:
        lines += ["These statements raise `UnsupportedConstruct` if executed:", "", "| Program | Location | Construct | Reason |", "|---|---|---|---|"]
        for u in unsupported:
            lines.append(f"| {u['program']} | {u['file']}:{u['line']} | {u['construct']} | {u['reason']} |")
    else:
        lines.append("None — every statement in the call tree was translated.")
    lines += [
        "",
        "## Verification",
        "",
        "`tests/cases.json` contains the differential cases; when produced by a verification run, expected outputs come from the original program executed by GnuCOBOL.",
        "",
    ]
    return "\n".join(lines)


CLI_TEMPLATE = '''"""Batch runner used by COBOL Phoenix differential verification.

Reads a JSON list of cases from stdin and writes JSON results to stdout.
Only depends on the standard library and the generated program modules.

    python -m app.cli --entry PROG --mode harness|main [--date YYYYMMDDHHMMSS] [--trace]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import traceback
from pathlib import Path

from . import phoenix_runtime as rt
from .programs import REGISTRY

PROGRAMS_DIR = str(Path(__file__).resolve().parent / "programs")
END_MARK = "*PHOENIX-END*"


def run_case(entry: str, mode: str, stdin: str, today: dt.datetime) -> dict:
    lines = stdin.split("\\n")
    if lines and lines[-1] == "":
        lines.pop()
    ctx = rt.RunContext(stdin_lines=[] if mode == "harness" else lines, today=today, registry=REGISTRY)
    status = "ok"
    error = None
    try:
        prog = ctx.program(entry)
        if mode == "harness":
            regions = []
            for i, name in enumerate(prog.LINKAGE):
                linkage = getattr(prog, name)
                region = rt.Region(linkage.name, linkage.size)
                raw = lines[i] if i < len(lines) else ""
                region.buf[:] = raw.encode("latin-1", "replace")[: region.size].ljust(region.size, b" ")
                regions.append(rt.Group(region, 0, region.size, linkage.name))
            stopped = False
            try:
                prog.call(*regions)
            except rt.StopRun:
                stopped = True
            if not stopped:
                for g in regions:
                    ctx.write(g.region.buf.decode("latin-1"))
                ctx.write(END_MARK)
        else:
            prog.run()
    except rt.UnsupportedConstruct as exc:
        status, error = "unsupported", str(exc)
    except Exception as exc:  # noqa: BLE001 - reported as runtime error behaviour
        status, error = "error", f"{type(exc).__name__}: {exc}"
        traceback.print_exc(file=sys.stderr)
    return {"stdout": ctx.output(), "status": status, "error": error}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entry", required=True)
    ap.add_argument("--mode", choices=["harness", "main"], required=True)
    ap.add_argument("--date", default=None)
    ap.add_argument("--trace", action="store_true")
    args = ap.parse_args()
    today = dt.datetime.strptime(args.date, "%Y%m%d%H%M%S") if args.date else dt.datetime.now()
    cases = json.load(sys.stdin)
    results = []
    for case in cases:
        executed: set = set()

        def tracer(frame, event, arg):
            if frame.f_code.co_filename.startswith(PROGRAMS_DIR):
                if event == "line":
                    executed.add((Path(frame.f_code.co_filename).name, frame.f_lineno))
                return tracer
            return None

        if args.trace:
            sys.settrace(tracer)
        try:
            res = run_case(args.entry, args.mode, case.get("stdin", ""), today)
        finally:
            sys.settrace(None)
        res["id"] = case.get("id")
        if args.trace:
            res["lines"] = sorted([f, n] for f, n in executed)
        results.append(res)
    json.dump(results, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

TEST_CASES_TEMPLATE = '''"""Regression cases. When produced by COBOL Phoenix verification, expected
outputs are the actual outputs of the original COBOL program (GnuCOBOL)."""

import datetime as dt
import json
from pathlib import Path

import pytest

from app.cli import run_case

DATA = json.loads((Path(__file__).with_name("cases.json")).read_text())
CASES = DATA.get("cases", [])
TODAY = dt.datetime.strptime(DATA.get("date", "20260101000000"), "%Y%m%d%H%M%S")


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES] or None)
def test_case(case: dict) -> None:
    res = run_case(DATA["entry"], DATA["mode"], case["stdin"], TODAY)
    assert res["status"] in ("ok",), res["error"]
    if case.get("expected_stdout") is not None:
        assert res["stdout"] == case["expected_stdout"]


def test_cases_present() -> None:
    assert DATA["entry"]
'''

DOCKERFILE_TEMPLATE = """FROM python:3.13-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
USER 10001
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
"""


def write_project(gp: GeneratedProject, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for rel, content in gp.files.items():
        p = out_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


__all__ = ["generate_project", "write_project", "GeneratedProject", "GenerationError", "call_tree", "class_name", "module_name"]
