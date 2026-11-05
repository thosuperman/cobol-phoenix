"""Render IR expressions and conditions back to readable COBOL-like text."""

from __future__ import annotations

from ..cobol import ir


def expr(e) -> str:
    if isinstance(e, ir.Literal):
        if e.kind == "string":
            return f'"{e.value}"' if not e.all else f'ALL "{e.value}"'
        if e.kind == "figurative":
            return e.value + ("S" if e.value in ("SPACE", "ZERO") else "")
        return e.value
    if isinstance(e, ir.Ref):
        s = e.name
        if e.special == "LENGTH OF":
            s = f"LENGTH OF {s}"
        if e.qualifiers:
            s += "".join(f" OF {q}" for q in e.qualifiers)
        if e.subscripts:
            s += "(" + ", ".join(expr(x) for x in e.subscripts) + ")"
        if e.refmod:
            s += f"({expr(e.refmod.start)}:{expr(e.refmod.length) if e.refmod.length else ''})"
        return s
    if isinstance(e, ir.BinOp):
        return f"{_wrap(e.left, e.op)} {e.op} {_wrap(e.right, e.op, right=True)}"
    if isinstance(e, ir.Neg):
        return f"-{_wrap(e.operand, '*')}"
    if isinstance(e, ir.FuncCall):
        args = " ".join([expr(a) for a in e.args] + e.keywords)
        return f"FUNCTION {e.name}({args})"
    return "?"


_PREC = {"+": 1, "-": 1, "*": 2, "/": 2, "**": 3}


def _wrap(e, parent_op: str, right: bool = False) -> str:
    s = expr(e)
    if isinstance(e, ir.BinOp):
        if _PREC[e.op] < _PREC[parent_op] or (right and _PREC[e.op] == _PREC[parent_op] and parent_op in "-/"):
            return f"({s})"
    return s


def cond(c) -> str:
    if isinstance(c, ir.Rel):
        return f"{expr(c.left)} {c.op} {expr(c.right)}"
    if isinstance(c, ir.CondRef):
        return expr(c.ref)
    if isinstance(c, ir.ClassCond):
        return f"{expr(c.operand)} IS {'NOT ' if c.negated else ''}{c.cls}"
    if isinstance(c, ir.Not):
        inner = cond(c.operand)
        return f"NOT {inner}" if isinstance(c.operand, (ir.CondRef, ir.Rel)) else f"NOT ({inner})"
    if isinstance(c, ir.And):
        return f"{_cw(c.left, 'AND')} AND {_cw(c.right, 'AND')}"
    if isinstance(c, ir.Or):
        return f"{_cw(c.left, 'OR')} OR {_cw(c.right, 'OR')}"
    return "?"


def _cw(c, parent: str) -> str:
    s = cond(c)
    if isinstance(c, ir.Or) and parent == "AND":
        return f"({s})"
    return s


def when_object(o: ir.WhenObject) -> str:
    if o.kind == "any":
        return "ANY"
    if o.kind in ("true", "false"):
        return o.kind.upper()
    if o.kind == "cond":
        return cond(o.cond)
    prefix = "NOT " if o.negated else ""
    if o.kind == "range":
        return f"{prefix}{expr(o.value)} THRU {expr(o.high)}"
    return prefix + expr(o.value)


def subject(s) -> str:
    if isinstance(s, str):
        return s
    if isinstance(s, (ir.Rel, ir.CondRef, ir.ClassCond, ir.Not, ir.And, ir.Or)):
        return cond(s)
    return expr(s)


def statement(s: ir.Stmt) -> str:
    """One-line summary of an imperative statement."""
    if isinstance(s, ir.Move):
        return f"MOVE {expr(s.source)} TO {', '.join(expr(t) for t in s.targets)}"
    if isinstance(s, ir.Compute):
        tg = ", ".join(expr(t.ref) + (" ROUNDED" if t.rounded else "") for t in s.targets)
        return f"COMPUTE {tg} = {expr(s.expr)}"
    if isinstance(s, ir.Arith):
        ops = " ".join(expr(o) for o in s.operands)
        tg = ", ".join(expr(t.ref) + (" ROUNDED" if t.rounded else "") for t in s.targets)
        prep = {"ADD": "TO", "SUBTRACT": "FROM", "MULTIPLY": "BY", "DIVIDE": "BY" if s.divide_by else "INTO"}[s.op]
        if s.giving:
            base = f" {prep} {expr(s.base)}" if s.base is not None else ""
            return f"{s.op} {ops}{base} GIVING {tg}"
        return f"{s.op} {ops} {prep} {tg}"
    if isinstance(s, ir.Perform):
        if s.target:
            return f"PERFORM {s.target}" + (f" THRU {s.thru}" if s.thru else "")
        return "PERFORM (inline)"
    if isinstance(s, ir.Call):
        return f"CALL {expr(s.program)}"
    if isinstance(s, ir.SetStmt):
        return f"SET {', '.join(expr(t) for t in s.targets)} TO {'TRUE' if s.mode == 'TRUE' else expr(s.value) if s.value else s.mode}"
    if isinstance(s, ir.Unsupported):
        return f"{s.verb} (unsupported)"
    return s.kind.replace("_", " ")
