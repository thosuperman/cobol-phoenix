"""Data-flow facts derived from the IR: which data items each statement reads/writes."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..cobol import ir


@dataclass
class Access:
    reads: set[str] = field(default_factory=set)
    writes: set[str] = field(default_factory=set)
    conds: set[str] = field(default_factory=set)  # 88-level keys tested


def expr_refs(e, out: set[str], conds: set[str] | None = None) -> None:
    if isinstance(e, ir.Ref):
        if e.item:
            out.add(e.item)
        if e.cond and conds is not None:
            conds.add(e.cond)
        for s in e.subscripts:
            expr_refs(s, out, conds)
        if e.refmod:
            expr_refs(e.refmod.start, out, conds)
            if e.refmod.length:
                expr_refs(e.refmod.length, out, conds)
    elif isinstance(e, ir.BinOp):
        expr_refs(e.left, out, conds)
        expr_refs(e.right, out, conds)
    elif isinstance(e, ir.Neg):
        expr_refs(e.operand, out, conds)
    elif isinstance(e, ir.FuncCall):
        for a in e.args:
            expr_refs(a, out, conds)


def cond_refs(c, out: set[str], conds: set[str]) -> None:
    if isinstance(c, ir.Rel):
        expr_refs(c.left, out, conds)
        expr_refs(c.right, out, conds)
    elif isinstance(c, ir.CondRef):
        if c.ref.cond:
            conds.add(c.ref.cond)
            out.add(c.ref.cond.split("::")[0])
        for s in c.ref.subscripts:
            expr_refs(s, out, conds)
    elif isinstance(c, ir.ClassCond):
        expr_refs(c.operand, out, conds)
    elif isinstance(c, ir.Not):
        cond_refs(c.operand, out, conds)
    elif isinstance(c, (ir.And, ir.Or)):
        cond_refs(c.left, out, conds)
        cond_refs(c.right, out, conds)


def _is_cond(x) -> bool:
    return isinstance(x, (ir.Rel, ir.CondRef, ir.ClassCond, ir.Not, ir.And, ir.Or))


def stmt_access(s: ir.Stmt) -> Access:
    """Direct (non-nested) reads/writes of one statement."""
    a = Access()
    r, w, c = a.reads, a.writes, a.conds

    def target(ref: ir.Ref) -> None:
        if ref.item:
            w.add(ref.item)
        for sub in ref.subscripts:
            expr_refs(sub, r, c)

    if isinstance(s, ir.Move):
        expr_refs(s.source, r, c)
        for t in s.targets:
            target(t)
    elif isinstance(s, ir.Compute):
        expr_refs(s.expr, r, c)
        for t in s.targets:
            target(t.ref)
    elif isinstance(s, ir.Arith):
        for e in s.operands:
            expr_refs(e, r, c)
        if s.base is not None:
            expr_refs(s.base, r, c)
        for t in s.targets:
            target(t.ref)
            if not s.giving and t.ref.item:
                r.add(t.ref.item)
        if s.remainder:
            target(s.remainder)
    elif isinstance(s, ir.If):
        cond_refs(s.cond, r, c)
    elif isinstance(s, ir.Evaluate):
        for subj in s.subjects:
            if isinstance(subj, str):
                continue
            if _is_cond(subj):
                cond_refs(subj, r, c)
            else:
                expr_refs(subj, r, c)
        for wh in s.whens:
            for line in wh.objects:
                for o in line:
                    if o.value is not None:
                        expr_refs(o.value, r, c)
                    if o.high is not None:
                        expr_refs(o.high, r, c)
                    if o.cond is not None:
                        cond_refs(o.cond, r, c)
    elif isinstance(s, ir.Perform):
        if s.times is not None:
            expr_refs(s.times, r, c)
        if s.until is not None:
            cond_refs(s.until, r, c)
        for v in s.varying:
            target(v.var)
            r.add(v.var.item or "")
            expr_refs(v.start, r, c)
            expr_refs(v.by, r, c)
            cond_refs(v.until, r, c)
    elif isinstance(s, ir.Call):
        for arg in s.using:
            expr_refs(arg.expr, r, c)
            if arg.mode == "REFERENCE" and isinstance(arg.expr, ir.Ref) and arg.expr.item:
                w.add(arg.expr.item)
    elif isinstance(s, ir.Display):
        for e in s.operands:
            expr_refs(e, r, c)
    elif isinstance(s, ir.Accept):
        target(s.target)
    elif isinstance(s, ir.Initialize):
        for t in s.targets:
            target(t)
    elif isinstance(s, ir.SetStmt):
        for t in s.targets:
            if t.cond:
                w.add(t.cond.split("::")[0])
                c.add(t.cond)
            else:
                target(t)
        if s.value is not None:
            expr_refs(s.value, r, c)
    elif isinstance(s, ir.StringStmt):
        for p in s.parts:
            expr_refs(p.expr, r, c)
            if p.delimiter is not None:
                expr_refs(p.delimiter, r, c)
        target(s.into)
        if s.pointer:
            target(s.pointer)
            r.add(s.pointer.item or "")
    r.discard("")
    return a


def elementary_closure(item_ids: set[str], index: dict[str, ir.DataItem]) -> set[str]:
    """Expand group ids to all elementary descendants (and keep elementary ids)."""
    out: set[str] = set()
    for iid in item_ids:
        it = index.get(iid)
        if it is None:
            continue
        stack = [it]
        while stack:
            x = stack.pop()
            if x.children:
                stack.extend(x.children)
            else:
                out.add(x.id)
    return out


def program_access(prog: ir.Program) -> tuple[Access, dict[str, Access]]:
    """Whole-program and per-paragraph access sets (elementary item ids)."""
    index = prog.item_index()
    total = Access()
    per: dict[str, Access] = {}
    for p in prog.paragraphs:
        pa = Access()
        for s in ir.walk_statements(p.statements):
            a = stmt_access(s)
            pa.reads |= a.reads
            pa.writes |= a.writes
            pa.conds |= a.conds
        pa.reads = elementary_closure(pa.reads, index)
        pa.writes = elementary_closure(pa.writes, index)
        per[p.name] = pa
        total.reads |= pa.reads
        total.writes |= pa.writes
        total.conds |= pa.conds
    return total, per
