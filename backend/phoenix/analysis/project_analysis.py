"""Project-level analysis: overview, dependency graph, complexity and business rules."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import PurePosixPath

from ..cobol import ir
from ..cobol.project import ProjectParse
from . import render
from .dataflow import program_access, stmt_access

# ---------------------------------------------------------------- complexity
# Documented heuristic (see docs/complexity.md and .kiro/specs/cobol-analysis/design.md)
WEIGHTS = {"statements": 1.0, "decision_points": 3.0, "paragraphs": 2.0, "calls": 4.0, "unsupported": 10.0, "data_items": 0.25}
BANDS = [(150, "Low"), (400, "Medium"), (900, "High")]


def _count_bool_ops(c) -> int:
    if isinstance(c, ir.And | ir.Or):
        return 1 + _count_bool_ops(c.left) + _count_bool_ops(c.right)
    if isinstance(c, ir.Not):
        return _count_bool_ops(c.operand)
    return 0


def program_metrics(prog: ir.Program, unsupported: int) -> dict:
    statements = decisions = calls = 0
    for par in prog.paragraphs:
        for s in ir.walk_statements(par.statements):
            statements += 1
            if isinstance(s, ir.If):
                decisions += 1 + _count_bool_ops(s.cond)
            elif isinstance(s, ir.Evaluate):
                decisions += sum(1 for w in s.whens if not w.other)
            elif isinstance(s, ir.Perform) and (s.until is not None or s.varying):
                decisions += 1
                for v in s.varying:
                    decisions += _count_bool_ops(v.until)
                if s.until is not None:
                    decisions += _count_bool_ops(s.until)
            elif isinstance(s, ir.Call):
                calls += 1
    data_items = sum(1 for _ in prog.iter_items())
    m = {
        "statements": statements,
        "decision_points": decisions,
        "paragraphs": len(prog.paragraphs),
        "calls": calls,
        "unsupported": unsupported,
        "data_items": data_items,
    }
    score = sum(m[k] * w for k, w in WEIGHTS.items())
    band = next((name for limit, name in BANDS if score < limit), "Very High")
    m["cyclomatic"] = decisions + 1
    m["score"] = round(score, 1)
    m["band"] = band
    return m


# ---------------------------------------------------------------- rules
_ANNOT_RE = re.compile(r"^\s*([A-Z][A-Z0-9]{1,8}-\d{1,5}[A-Z]?)\s*[:\-]\s*(.+)$")


def _comment_text(raw: str, fmt: str) -> str | None:
    if fmt == "fixed" and len(raw) > 6 and raw[6] in "*/":
        return raw[7:72].strip()
    s = raw.strip()
    if s.startswith("*>"):
        return s[2:].strip()
    if "*>" in raw and fmt == "free":
        return raw.split("*>", 1)[1].strip()
    return None


def _annotations(lines: list[str], start: int, end: int, fmt: str) -> list[dict]:
    out: list[dict] = []
    cur: dict | None = None
    for n in range(start, min(end, len(lines)) + 1):
        txt = _comment_text(lines[n - 1], fmt)
        if txt is None:
            cur = None if cur is None or n - cur["last"] > 1 else cur
            continue
        m = _ANNOT_RE.match(txt)
        if m:
            cur = {"id": m.group(1), "text": m.group(2).strip(), "line": n, "last": n}
            out.append(cur)
        elif cur is not None and n == cur["last"] + 1 and txt:
            cur["text"] += " " + txt
            cur["last"] = n
    return out


def _humanize(name: str) -> str:
    words = [w for w in name.split("-") if not w.isdigit()]
    return " ".join(w.capitalize() for w in words) or name


def _fields(ids: set[str], index: dict[str, ir.DataItem]) -> list[str]:
    names = sorted({index[i].name for i in ids if i in index and not index[i].is_filler})
    return names


def _collect(stmts: list[ir.Stmt], lo: int, hi: int, file: str):
    for s in ir.walk_statements(stmts):
        if s.loc.file == file and lo <= s.loc.line <= hi:
            yield s


def _rule_from_statements(
    prog: ir.Program,
    par: ir.Paragraph,
    stmts: list[ir.Stmt],
    index,
    rid: str,
    name: str,
    desc: str | None,
    lo: int,
    hi: int,
    performed_by: dict[str, list[str]],
) -> dict | None:
    conditions, calculations, assignments, decision_tables = [], [], [], []
    reads: set[str] = set()
    writes: set[str] = set()
    unsupported = []
    for s in stmts:
        a = stmt_access(s)
        reads |= a.reads
        writes |= a.writes
        if isinstance(s, ir.If):
            conditions.append({"text": render.cond(s.cond), "line": s.loc.line, "end_line": s.loc.end_line})
        elif isinstance(s, ir.Evaluate):
            rows = []
            for w in s.whens:
                actions = [render.statement(x) for x in w.body if not isinstance(x, ir.If | ir.Evaluate)][:6]
                label = "OTHER" if w.other else " | ".join(" ALSO ".join(render.when_object(o) for o in line) for line in w.objects)
                rows.append({"when": label, "actions": actions, "line": w.loc.line})
            decision_tables.append(
                {"subject": " ALSO ".join(render.subject(x) for x in s.subjects), "rows": rows, "line": s.loc.line, "end_line": s.loc.end_line}
            )
        elif isinstance(s, ir.Compute | ir.Arith):
            calculations.append({"text": render.statement(s), "line": s.loc.line, "end_line": s.loc.end_line})
        elif isinstance(s, ir.Move) and isinstance(s.source, ir.Literal):
            assignments.append({"text": render.statement(s), "line": s.loc.line})
        elif isinstance(s, ir.Unsupported):
            unsupported.append({"construct": s.verb, "line": s.loc.line, "reason": s.reason})
    if not (conditions or calculations or decision_tables):
        return None
    total_index = index
    reads_e = {r for r in reads}
    inputs = _fields(reads_e, total_index)
    outputs = _fields(writes, total_index)
    if desc is None:
        bits = []
        if decision_tables:
            bits.append(f"selects among {sum(len(t['rows']) for t in decision_tables)} cases of {', '.join(t['subject'] for t in decision_tables[:2])}")
        if conditions:
            bits.append(f"tests {len(conditions)} condition{'s' if len(conditions) != 1 else ''}")
        if calculations:
            outs = sorted({c["text"].split(" ")[1] for c in calculations if c["text"].startswith("COMPUTE")})
            bits.append("computes " + (", ".join(outs[:4]) if outs else f"{len(calculations)} arithmetic results"))
        desc = f"{_humanize(par.name)}: " + "; ".join(bits) + "."
        desc_source = "deterministic"
    else:
        desc_source = "source-comment"
    return {
        "id": rid,
        "name": name,
        "description": desc,
        "description_source": desc_source,
        "program": prog.program_id,
        "paragraph": par.name,
        "file": par.loc.file,
        "line_start": lo,
        "line_end": hi,
        "inputs": inputs,
        "outputs": outputs,
        "conditions": conditions,
        "calculations": calculations,
        "assignments": assignments[:20],
        "decision_tables": decision_tables,
        "related_paragraphs": sorted(set(performed_by.get(par.name, [])) | {s.target for s in stmts if isinstance(s, ir.Perform) and s.target}),
        "statement_keys": [f"{s.loc.file}:{s.loc.line}" for s in stmts],
        "unsupported": unsupported,
        "status": "UNSUPPORTED" if unsupported else "EXTRACTED",
    }


def extract_rules(prog: ir.Program, sources: dict[str, list[str]]) -> list[dict]:
    index = prog.item_index()
    performed_by: dict[str, list[str]] = {}
    for par in prog.paragraphs:
        for s in ir.walk_statements(par.statements):
            if isinstance(s, ir.Perform) and s.target:
                performed_by.setdefault(s.target, []).append(par.name)
    rules: list[dict] = []
    lines = sources.get(prog.file, [])
    for par in prog.paragraphs:
        if par.loc.file != prog.file:
            continue
        anns = _annotations(lines, par.loc.line, par.loc.end_line, prog.source_format)
        if anns:
            for i, a in enumerate(anns):
                lo = a["line"]
                hi = (anns[i + 1]["line"] - 1) if i + 1 < len(anns) else par.loc.end_line
                stmts = list(_collect(par.statements, lo, hi, par.loc.file))
                r = _rule_from_statements(
                    prog, par, stmts, index, f"{prog.program_id}:{a['id']}", f"{a['id']} {_humanize(par.name)}", a["text"], lo, max(hi, lo), performed_by
                )
                if r:
                    r["annotation"] = a["id"]
                    rules.append(r)
            # statements before the first annotation
            pre = [s for s in _flat(par.statements) if s.loc.line < anns[0]["line"] and s.loc.file == par.loc.file]
            r = (
                _rule_from_statements(
                    prog, par, pre, index, f"{prog.program_id}:{par.name}", _humanize(par.name), None, par.loc.line, anns[0]["line"] - 1, performed_by
                )
                if pre
                else None
            )
            if r:
                rules.append(r)
        else:
            r = _rule_from_statements(
                prog,
                par,
                list(_flat(par.statements)),
                index,
                f"{prog.program_id}:{par.name}",
                _humanize(par.name),
                None,
                par.loc.line,
                par.loc.end_line,
                performed_by,
            )
            if r:
                rules.append(r)
    rules.sort(key=lambda r: (r["file"], r["line_start"]))
    return rules


def _flat(stmts):
    return ir.walk_statements(stmts)


def _contains(parent: ir.Stmt, child: ir.Stmt) -> bool:
    for s in ir.walk_statements([parent]):
        if s is child and s is not parent:
            return True
    return False


# ---------------------------------------------------------------- graph + overview
def analyze(pp: ProjectParse) -> dict:
    sources = {f.path: f.text.splitlines() for f in pp.files}
    known_programs = {p.program.program_id for p in pp.programs}
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    programs_out = []
    all_rules: list[dict] = []
    unsupported_all: list[dict] = []
    diags_all: list[dict] = []

    for f in pp.files:
        if f.kind == "copybook":
            nodes[f"copybook:{f.path}"] = {
                "id": f"copybook:{f.path}",
                "type": "copybook",
                "label": PurePosixPath(f.path).name,
                "file": f.path,
                "line": 1,
                "lines": f.lines,
            }

    for pprog in pp.programs:
        prog = pprog.program
        pid = prog.program_id
        nid = f"program:{pid}"
        metrics = program_metrics(prog, len(pprog.unsupported))
        nodes[nid] = {
            "id": nid,
            "type": "program",
            "label": pid,
            "file": prog.file,
            "line": prog.loc.line,
            "end_line": prog.loc.end_line,
            "complexity": metrics["band"],
            "score": metrics["score"],
        }
        seen_copy = set()
        for c in prog.copybooks:
            tgt = f"copybook:{c['resolved']}" if c["resolved"] else f"missing-copybook:{c['name']}"
            if tgt not in nodes:
                nodes[tgt] = {"id": tgt, "type": "missing", "label": c["name"], "file": None, "line": None}
            src_node = nid if c["file"] == prog.file else f"copybook:{c['file']}"
            key = (src_node, tgt)
            if key in seen_copy:
                continue
            seen_copy.add(key)
            edges.append({"source": src_node, "target": tgt, "type": "copy", "file": c["file"], "line": c["line"]})
        calls = []
        for par in prog.paragraphs:
            for s in ir.walk_statements(par.statements):
                if isinstance(s, ir.Call):
                    target = s.program.value.strip().upper() if isinstance(s.program, ir.Literal) else f"(dynamic {render.expr(s.program)})"
                    calls.append({"target": target, "file": s.loc.file, "line": s.loc.line, "paragraph": par.name})
                    tnode = f"program:{target}" if target in known_programs else f"external:{target}"
                    if tnode not in nodes and not tnode.startswith("program:"):
                        nodes[tnode] = {"id": tnode, "type": "external", "label": target, "file": None, "line": None}
                    edges.append({"source": nid, "target": tnode, "type": "call", "file": s.loc.file, "line": s.loc.line})
        # paragraphs
        para_edges = []
        for par in prog.paragraphs:
            pnode = f"paragraph:{pid}:{par.name}"
            nodes[pnode] = {
                "id": pnode,
                "type": "paragraph",
                "label": par.name,
                "program": pid,
                "file": par.loc.file,
                "line": par.loc.line,
                "end_line": par.loc.end_line,
            }
            edges.append({"source": nid, "target": pnode, "type": "contains", "file": par.loc.file, "line": par.loc.line})
            for s in ir.walk_statements(par.statements):
                if isinstance(s, ir.Perform) and s.target:
                    tgt = f"paragraph:{pid}:{s.target}"
                    para_edges.append({"source": pnode, "target": tgt, "type": "perform", "file": s.loc.file, "line": s.loc.line, "thru": s.thru})
                elif isinstance(s, ir.GoTo):
                    para_edges.append({"source": pnode, "target": f"paragraph:{pid}:{s.target}", "type": "goto", "file": s.loc.file, "line": s.loc.line})
        edges.extend(e for e in para_edges if e["target"] in nodes or True)
        # data records and usage
        total, per = program_access(prog)
        index = prog.item_index()
        records = []
        for root in prog.data:
            rnode = f"record:{pid}:{root.name}"
            elems = [i for i in prog.iter_items() if i.record == root.id and not i.children]
            r_reads = sum(1 for e in elems if e.id in total.reads)
            r_writes = sum(1 for e in elems if e.id in total.writes)
            records.append(
                {
                    "name": root.name,
                    "level": root.level,
                    "section": root.section,
                    "size": root.size,
                    "file": root.loc.file,
                    "line": root.loc.line,
                    "fields": len(elems),
                    "read": r_reads,
                    "written": r_writes,
                }
            )
            if root.level in (1, 77) and (root.children or root.section == "LINKAGE"):
                nodes[rnode] = {
                    "id": rnode,
                    "type": "record",
                    "label": root.name,
                    "program": pid,
                    "file": root.loc.file,
                    "line": root.loc.line,
                    "section": root.section,
                    "size": root.size,
                }
                edges.append({"source": nid, "target": rnode, "type": "declares", "file": root.loc.file, "line": root.loc.line})
                for par in prog.paragraphs:
                    pa = per[par.name]
                    ids = {e.id for e in elems}
                    if pa.reads & ids or pa.writes & ids:
                        mode = "rw" if (pa.reads & ids and pa.writes & ids) else ("w" if pa.writes & ids else "r")
                        edges.append(
                            {"source": f"paragraph:{pid}:{par.name}", "target": rnode, "type": "uses", "mode": mode, "file": par.loc.file, "line": par.loc.line}
                        )
        rules = extract_rules(prog, sources)
        all_rules.extend(rules)
        for u in pprog.unsupported:
            unsupported_all.append(dict(u, program=pid))
        for d in pprog.diagnostics:
            dd = d.to_dict()
            dd["program"] = pid
            diags_all.append(dd)
        programs_out.append(
            {
                "program_id": pid,
                "file": prog.file,
                "line_start": prog.loc.line,
                "line_end": prog.loc.end_line,
                "source_format": prog.source_format,
                "kind": "subprogram" if prog.using else "main",
                "using": [index[u].name for u in prog.using if u in index],
                "paragraphs": [
                    {
                        "name": p.name,
                        "section": p.section,
                        "line_start": p.loc.line,
                        "line_end": p.loc.end_line,
                        "statements": sum(1 for _ in ir.walk_statements(p.statements)),
                    }
                    for p in prog.paragraphs
                ],
                "copybooks": sorted({c["name"] for c in prog.copybooks}),
                "calls": calls,
                "files": [{"name": fc.name, "assign": fc.assign, "organization": fc.organization, "line": fc.loc.line} for fc in prog.files],
                "records": records,
                "metrics": metrics,
                "rules": len(rules),
                "unsupported": len(pprog.unsupported),
                "errors": sum(1 for d in pprog.diagnostics if str(d.severity) == "error"),
                "warnings": sum(1 for d in pprog.diagnostics if str(d.severity) == "warning"),
            }
        )
    for d in pp.diagnostics:
        diags_all.append(d.to_dict())
    # de-duplicate diagnostics coming from shared copybooks
    seen = set()
    uniq_diags = []
    for d in diags_all:
        k = (d["code"], d["file"], d["line"], d["message"])
        if k not in seen:
            seen.add(k)
            uniq_diags.append(d)
    construct_counts = Counter(u["construct"] for u in unsupported_all)
    total_score = sum(p["metrics"]["score"] for p in programs_out)
    band = next((name for limit, name in [(b * max(1, len(programs_out)), n) for b, n in BANDS] if total_score < limit), "Very High")
    dep_edges = [e for e in edges if e["type"] in ("copy", "call")]
    overview = {
        "programs": len(programs_out),
        "copybooks": sum(1 for f in pp.files if f.kind == "copybook"),
        "source_files": len(pp.files),
        "source_lines": sum(f.lines for f in pp.files),
        "dependencies": len(dep_edges),
        "call_edges": sum(1 for e in edges if e["type"] == "call"),
        "copy_edges": sum(1 for e in edges if e["type"] == "copy"),
        "business_rules": len(all_rules),
        "unsupported_constructs": len(unsupported_all),
        "unsupported_by_construct": dict(construct_counts.most_common()),
        "errors": sum(1 for d in uniq_diags if d["severity"] == "error"),
        "warnings": sum(1 for d in uniq_diags if d["severity"] == "warning"),
        "complexity_score": round(total_score, 1),
        "complexity_band": band,
        "complexity_weights": WEIGHTS,
        "missing_copybooks": sorted({n["label"] for n in nodes.values() if n["type"] == "missing"}),
        "external_calls": sorted({n["label"] for n in nodes.values() if n["type"] == "external"}),
    }
    return {
        "overview": overview,
        "programs": programs_out,
        "graph": {"nodes": list(nodes.values()), "edges": edges},
        "rules": all_rules,
        "unsupported": unsupported_all,
        "diagnostics": uniq_diags,
        "files": [{"path": f.path, "kind": f.kind, "format": f.format, "lines": f.lines} for f in pp.files],
    }
