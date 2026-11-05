"""Deterministic IR -> Python translation of one COBOL program.

Every emitted statement is recorded in a traceability map
(python line range -> COBOL file and line range).
"""

from __future__ import annotations

import keyword
import re
from dataclasses import dataclass, field

from ..cobol import ir

RESERVED_ATTRS = {
    "ctx", "perform", "run", "call", "call_program", "run_procedure", "exit_program", "region",
    "self", "rt", "D", "PROGRAM_ID", "PARAGRAPHS", "SECTIONS", "LINKAGE", "INITIAL",
}  # fmt: skip

FIG_PY = {"ZERO": "rt.ZEROS", "SPACE": "rt.SPACES", "HIGH-VALUE": "rt.HIGH_VALUES", "LOW-VALUE": "rt.LOW_VALUES", "QUOTE": "rt.QUOTES"}

RELOP_PY = {"=": "==", "<>": "!=", "<": "<", "<=": "<=", ">": ">", ">=": ">="}


def py_ident(name: str) -> str:
    s = re.sub(r"[^0-9a-zA-Z]", "_", name.lower()).strip("_") or "x"
    if s[0].isdigit():
        s = "n" + s
    if keyword.iskeyword(s) or s in RESERVED_ATTRS:
        s = s + "_"
    return s


def para_method(name: str) -> str:
    return "p_" + "".join(c if c.isalnum() else "_" for c in name.lower())


def class_name(pid: str) -> str:
    return "Program" + "".join(w.capitalize() for w in re.split(r"[^0-9A-Za-z]+", pid) if w)


def module_name(pid: str) -> str:
    s = re.sub(r"[^0-9a-z]", "_", pid.lower())
    return ("p_" + s) if s[0].isdigit() else s


@dataclass
class Mutation:
    """A single deliberate fault for mutation analysis / demo."""

    id: str
    kind: str  # rounding | relop | arith | literal
    file: str
    line: int
    detail: str
    ordinal: int = 0  # n-th matching site on that line


@dataclass
class TraceEntry:
    py_start: int
    py_end: int
    file: str
    line: int
    end_line: int
    kind: str
    paragraph: str


@dataclass
class GeneratedModule:
    program_id: str
    module: str
    class_name: str
    source: str
    trace: list[TraceEntry] = field(default_factory=list)
    unsupported: list[dict] = field(default_factory=list)
    attr_of: dict[str, str] = field(default_factory=dict)  # item id -> attribute
    region_of: dict[str, str] = field(default_factory=dict)  # root id -> region attribute
    mutations_applied: list[str] = field(default_factory=list)


class ProgramGenerator:
    def __init__(self, prog: ir.Program, sources: dict[str, list[str]], mutation: Mutation | None = None) -> None:
        self.p = prog
        self.sources = sources
        self.mutation = mutation
        self.lines: list[str] = []
        self.trace: list[TraceEntry] = []
        self.unsupported: list[dict] = []
        self.index = prog.item_index()
        self.attr: dict[str, str] = {}
        self.cond_attr: dict[str, str] = {}
        self.region: dict[str, str] = {}
        self.used_names: set[str] = set()
        self.cur_para = ""
        self.tmp = 0
        self.mut_counter: dict[tuple[str, int, str], int] = {}
        self.applied: list[str] = []
        self.loop_depth = 0
        self.mut_scope = False  # literal/arith mutations only inside COMPUTE expressions

    # ------------------------------------------------------------ naming
    def _unique(self, base: str) -> str:
        name = base
        k = 2
        while name in self.used_names:
            name = f"{base}_{k}"
            k += 1
        self.used_names.add(name)
        return name

    def _assign_names(self) -> None:
        for root in self.p.data:
            if root.is_constant:
                continue
            target_root = root
            if root.redefines:
                target_root = next((r for r in self.p.data if r.name == root.redefines), root)
            if target_root is root:
                self.region[root.id] = self._unique("r_" + py_ident(root.name))
            else:
                self.region[root.id] = self.region[target_root.id]
        for it in self.p.iter_items():
            if it.is_constant:
                continue
            base = py_ident(it.name if not it.is_filler else f"filler_{it.loc.line}")
            self.attr[it.id] = self._unique(base)
            for c in it.conditions:
                self.cond_attr[f"{it.id}::{c.name}"] = self._unique("c_" + py_ident(c.name))

    # ------------------------------------------------------------ emission helpers
    def emit(self, indent: int, text: str) -> int:
        self.lines.append("    " * indent + text)
        return len(self.lines)

    def src_text(self, loc: ir.Loc) -> str:
        lines = self.sources.get(loc.file)
        if not lines or loc.line - 1 >= len(lines):
            return ""
        raw = lines[loc.line - 1]
        body = raw[7:72] if len(raw) > 7 and self.p.source_format == "fixed" else raw
        return " ".join(body.split())[:90]

    def where(self, loc: ir.Loc) -> str:
        return f"{loc.file}:{loc.line}" + (f"-{loc.end_line}" if loc.end_line != loc.line else "")

    # ------------------------------------------------------------ module
    def generate(self) -> GeneratedModule:
        self._assign_names()
        p = self.p
        cls = class_name(p.program_id)
        e = self.emit
        e(0, f'"""Python translation of COBOL program {p.program_id}.')
        e(0, "")
        e(0, f"Source: {p.file} (lines {p.loc.line}-{p.loc.end_line})")
        e(0, "Generated deterministically by COBOL Phoenix. Do not edit by hand:")
        e(0, "regenerate from the COBOL source and re-run differential verification.")
        e(0, '"""')
        e(0, "")
        e(0, "from __future__ import annotations")
        e(0, "")
        e(0, "from decimal import Decimal as D")
        e(0, "")
        e(0, "from .. import phoenix_runtime as rt")
        e(0, "")
        e(0, "")
        e(0, f"class {cls}(rt.Program):")
        e(1, f"PROGRAM_ID = {p.program_id!r}")
        e(1, f"INITIAL = {p.is_initial!r}")
        paras = tuple(par.name for par in p.paragraphs)
        e(1, "PARAGRAPHS = (")
        for name in paras:
            e(2, f"{name!r},")
        e(1, ")")
        secs = {}
        for s in p.sections:
            if s.paragraphs:
                secs[s.name] = (s.paragraphs[0], s.paragraphs[-1])
        e(1, f"SECTIONS = {secs!r}")
        linkage_regions = tuple(self.region[u] for u in p.using if u in self.region)
        e(1, f"LINKAGE = {linkage_regions!r}")
        e(0, "")
        e(1, "def __init__(self, ctx: rt.RunContext) -> None:")
        self._emit_data()
        e(2, "super().__init__(ctx)")
        e(2, "self._init_storage()")
        e(0, "")
        self._emit_init_storage()
        for par in p.paragraphs:
            e(0, "")
            self._emit_paragraph(par)
        src = "\n".join(self.lines) + "\n"
        return GeneratedModule(
            program_id=p.program_id,
            module=module_name(p.program_id),
            class_name=cls,
            source=src,
            trace=self.trace,
            unsupported=self.unsupported,
            attr_of=dict(self.attr),
            region_of=dict(self.region),
            mutations_applied=self.applied,
        )

    # ------------------------------------------------------------ data division
    def _emit_data(self) -> None:
        e = self.emit
        sizes: dict[str, int] = {}
        for root in self.p.data:
            if root.is_constant:
                continue
            reg = self.region[root.id]
            sizes[reg] = max(sizes.get(reg, 0), root.size)
        emitted_regions: set[str] = set()
        current_section = None
        for root in self.p.data:
            if root.is_constant:
                continue
            if root.section != current_section:
                current_section = root.section
                e(2, f"# --- {current_section} SECTION")
            reg = self.region[root.id]
            if reg not in emitted_regions:
                emitted_regions.add(reg)
                linkage = root.section == "LINKAGE"
                e(2, f"self.{reg} = rt.Region({root.name!r}, {sizes[reg]}{', linkage=True' if linkage else ''})")
            for it in self._walk(root):
                self._emit_field(it, reg)
            for it in self._walk(root):
                if it.children:
                    kids = ", ".join(f"self.{self.attr[c.id]}" for c in it.children if c.id in self.attr)
                    e(2, f"self.{self.attr[it.id]}.children = [{kids}]")
        # condition names
        for it in self.p.iter_items():
            for c in it.conditions:
                key = f"{it.id}::{c.name}"
                vals = ", ".join(f"({self._cond_value(v.low)}, {self._cond_value(v.high) if v.high else 'None'})" for v in c.values)
                e(2, f"self.{self.cond_attr[key]} = rt.Condition(self.{self.attr[it.id]}, [{vals}])  # {self.where(c.loc)}")

    def _walk(self, root: ir.DataItem):
        stack = [root]
        while stack:
            it = stack.pop()
            yield it
            stack.extend(reversed(it.children))

    def _cond_value(self, lit: ir.Literal) -> str:
        if lit.kind == "number":
            return f"D({lit.value!r})"
        if lit.kind == "figurative":
            return FIG_PY[lit.value]
        return repr(lit.value)

    def _emit_field(self, it: ir.DataItem, reg: str) -> None:
        a = self.attr[it.id]
        common = f"self.{reg}, {it.offset}, {it.size}, {it.name!r}, {tuple(it.dims)!r}, {it.occurs}"
        flags = []
        if it.is_filler:
            flags.append("filler=True")
        if it.redefines:
            flags.append("redefines=True")
        fl = (", " + ", ".join(flags)) if flags else ""
        where = self.where(it.loc)
        pic = it.picture
        if it.children or (pic is None and it.usage == "DISPLAY"):
            ctor = f"rt.Group({common}{fl})"
        elif it.usage in ("COMP-1", "COMP-2", "POINTER"):
            ctor = f"rt.Group({common}{fl})"
            self.unsupported.append({"construct": f"USAGE {it.usage}", "file": it.loc.file, "line": it.loc.line, "reason": "stored as raw bytes"})
        elif it.usage == "INDEX":
            ctor = f"rt.Binary({common}, digits=9, signed=True, native=True{fl})"
        elif pic.category == "numeric":
            num = f"digits={pic.digits}, scale={pic.scale}, signed={pic.signed}"
            if it.usage == "COMP-3":
                ctor = f"rt.Packed({common}, {num}{fl})"
            elif it.usage in ("COMP", "COMP-5"):
                ctor = f"rt.Binary({common}, {num}{', native=True' if it.usage == 'COMP-5' else ''}{fl})"
            else:
                ss = f", sign_separate={it.sign_separate}, sign_leading={it.sign_leading}" if (it.sign_separate or it.sign_leading) else ""
                ctor = f"rt.Numeric({common}, {num}{ss}{fl})"
        elif pic.category == "numeric-edited":
            ctor = f"rt.Edited({common}, digits={pic.digits}, scale={pic.scale}, signed={pic.signed}, picture={pic.expanded!r}, blank_when_zero={it.blank_when_zero}{fl})"
        elif pic.category == "alphanumeric-edited":
            ctor = f"rt.AlnumEdited({common}, picture={pic.expanded!r}{fl})"
        else:
            j = ", justified=True" if it.justified else ""
            ctor = f"rt.Alnum({common}{j}{fl})"
        pic_txt = f" PIC {pic.raw}" if pic else ""
        self.emit(2, f"self.{a} = {ctor}  # {where} {it.level:02d} {it.name}{pic_txt}")

    def _emit_init_storage(self) -> None:
        e = self.emit
        e(1, "def _init_storage(self) -> None:")
        e(2, '"""Initial WORKING-STORAGE state: type defaults, then VALUE clauses."""')
        any_ = False
        for root in self.p.data:
            if root.is_constant or root.section == "LINKAGE" or root.redefines:
                continue
            any_ = True
            e(2, f"rt.initialize(self.{self.attr[root.id]}, fillers=True)")
        for it in self.p.iter_items():
            if it.is_constant or it.section == "LINKAGE" or it.value is None:
                continue
            any_ = True
            val = self._literal_move(it.value)
            target = f"self.{self.attr[it.id]}"
            if it.dims:
                loops = [f"_i{k}" for k in range(len(it.dims))]
                for k, (_, count) in enumerate(it.dims):
                    e(2 + k, f"for {loops[k]} in range(1, {count + 1}):")
                e(2 + len(it.dims), f"rt.move({val}, {target}[{', '.join(loops)}])  # {self.where(it.loc)}")
            else:
                e(2, f"rt.move({val}, {target})  # {self.where(it.loc)}")
        if not any_:
            e(2, "pass")

    def _literal_move(self, lit: ir.Literal) -> str:
        if lit.kind == "number":
            return f"rt.lit({lit.value!r})"
        if lit.kind == "figurative":
            return FIG_PY[lit.value] if not lit.all else FIG_PY[lit.value]
        if lit.all:
            return f"rt.AllOf({lit.value!r})"
        return repr(lit.value)

    # ------------------------------------------------------------ procedure
    def _emit_paragraph(self, par: ir.Paragraph) -> None:
        self.cur_para = par.name
        e = self.emit
        e(1, f"def {para_method(par.name)}(self) -> None:")
        e(2, f'"""{par.name} - {self.where(par.loc)}"""')
        if not par.statements:
            e(2, "pass")
            return
        self._emit_block(par.statements, 2)

    def _emit_block(self, stmts: list[ir.Stmt], ind: int) -> None:
        if not stmts:
            self.emit(ind, "pass")
            return
        for s in stmts:
            self._emit_stmt(s, ind)

    def _emit_stmt(self, s: ir.Stmt, ind: int) -> None:
        start = len(self.lines) + 1
        self.emit(ind, f"# {self.where(s.loc)}: {self.src_text(s.loc)}")
        handler = getattr(self, f"_st_{type(s).__name__.lower()}", None)
        try:
            if handler is None:
                self._unsupported(s, ind, f"{type(s).__name__} not supported by the generator")
            else:
                handler(s, ind)
        except _GenUnsupported as exc:
            # roll back partial output of this statement
            del self.lines[start:]
            self._unsupported(s, ind, str(exc))
        end = len(self.lines)
        self.trace.append(TraceEntry(start + 1, end, s.loc.file, s.loc.line, s.loc.end_line, s.kind, self.cur_para))

    def _unsupported(self, s: ir.Stmt, ind: int, reason: str) -> None:
        verb = getattr(s, "verb", "") or s.kind
        self.unsupported.append({"construct": verb, "file": s.loc.file, "line": s.loc.line, "reason": reason})
        self.emit(ind, f"raise rt.UnsupportedConstruct({verb!r}, {self.where(s.loc)!r})")

    # ---------------- expressions
    def ref(self, r: ir.Ref) -> str:
        if r.special == "LENGTH OF":
            it = self.index.get(r.item or "")
            if it is None:
                raise _GenUnsupported("LENGTH OF unresolved item")
            return f"D({it.size * max(1, it.occurs) if not r.subscripts else it.size})"
        if r.special:
            raise _GenUnsupported(f"special register {r.special}")
        if r.item is None:
            raise _GenUnsupported(f"unresolved reference {r.name}")
        it = self.index[r.item]
        if it.is_constant:
            if it.value is None:
                raise _GenUnsupported(f"constant {r.name} without VALUE")
            return self._literal_move(it.value)
        base = f"self.{self.attr[r.item]}"
        if r.subscripts:
            base += "[" + ", ".join(self.subscript(x) for x in r.subscripts) + "]"
        if r.refmod:
            ln = self.num(r.refmod.length) if r.refmod.length is not None else "None"
            base = f"rt.RefMod({base}, {self.num(r.refmod.start)}, {ln})"
        return base

    def subscript(self, e: ir.Expr) -> str:
        if isinstance(e, ir.Literal) and e.kind == "number":
            return str(int(e.decimal))
        if isinstance(e, ir.Ref):
            return self.ref(e)
        return f"int({self.num(e)})"

    def is_numeric_expr(self, e) -> bool:
        if isinstance(e, ir.Literal):
            return e.kind == "number" or (e.kind == "figurative" and e.value == "ZERO")
        if isinstance(e, ir.BinOp | ir.Neg):
            return True
        if isinstance(e, ir.FuncCall):
            return e.name not in ("TRIM", "UPPER-CASE", "LOWER-CASE", "REVERSE", "CONCATENATE", "CURRENT-DATE", "WHEN-COMPILED", "CHAR")
        if isinstance(e, ir.Ref):
            if e.refmod:
                return False
            if e.special == "LENGTH OF":
                return True
            it = self.index.get(e.item or "")
            if it is None:
                return False
            if it.is_constant:
                return it.value is not None and it.value.kind == "number"
            return it.is_numeric and not it.children and not it.is_edited
        return False

    def num(self, e) -> str:
        """Python expression producing a Decimal."""
        if isinstance(e, ir.Literal):
            if e.kind == "number":
                return f"D({self._mut_literal(e)!r})"
            if e.kind == "figurative" and e.value == "ZERO":
                return "D(0)"
            raise _GenUnsupported(f"non-numeric literal {e.value!r} in arithmetic")
        if isinstance(e, ir.Ref):
            r = self.ref(e)
            if self.is_numeric_expr(e) and not (e.item and self.index[e.item].is_constant):
                return f"{r}.value"
            return f"rt.num({r})"
        if isinstance(e, ir.Neg):
            return f"(-{self.num(e.operand)})"
        if isinstance(e, ir.BinOp):
            op = self._mut_arith(e.op, e)
            left, right = self.num(e.left), self.num(e.right)
            if op == "/":
                return f"rt.div({left}, {right})"
            if op == "**":
                return f"rt.power({left}, {right})"
            return f"({left} {op} {right})"
        if isinstance(e, ir.FuncCall):
            return f"rt.num({self.func(e)})"
        raise _GenUnsupported(f"expression {type(e).__name__}")

    def operand(self, e) -> str:
        """Python expression for an operand used by MOVE/DISPLAY/compare."""
        if isinstance(e, ir.Literal):
            if e.kind == "number":
                return f"rt.lit({e.value!r})"
            if e.kind == "figurative":
                return FIG_PY[e.value]
            if e.all:
                return f"rt.AllOf({e.value!r})"
            return repr(e.value)
        if isinstance(e, ir.Ref):
            return self.ref(e)
        if isinstance(e, ir.FuncCall):
            return self.func(e)
        return self.num(e)

    def func(self, f: ir.FuncCall) -> str:
        args = ", ".join(self.operand(a) for a in f.args)
        kw = f", keywords={tuple(f.keywords)!r}" if f.keywords else ""
        return f"rt.fn({f.name!r}{', ' + args if args else ''}{kw}, ctx=self.ctx)"

    def has_div(self, e) -> bool:
        if isinstance(e, ir.BinOp):
            return e.op in ("/", "**") or self.has_div(e.left) or self.has_div(e.right)
        if isinstance(e, ir.Neg):
            return self.has_div(e.operand)
        if isinstance(e, ir.FuncCall):
            return e.name in ("MOD", "REM") or any(self.has_div(a) for a in e.args)
        return False

    # ---------------- conditions
    def cond(self, c) -> str:
        if isinstance(c, ir.Rel):
            op = self._mut_relop(c.op, c)
            if self.is_numeric_expr(c.left) and self.is_numeric_expr(c.right):
                return f"{self.num(c.left)} {RELOP_PY[op]} {self.num(c.right)}"
            return f"rt.cmp({self.operand(c.left)}, {self.operand(c.right)}) {RELOP_PY[op]} 0"
        if isinstance(c, ir.CondRef):
            r = c.ref
            if r.cond is None:
                if r.item:  # identifier used as a condition (should not happen)
                    raise _GenUnsupported(f"{r.name} is not a condition name")
                raise _GenUnsupported(f"unresolved condition {r.name}")
            subs = ", ".join(self.subscript(x) for x in r.subscripts)
            return f"self.{self.cond_attr[r.cond]}.test({subs})"
        if isinstance(c, ir.ClassCond):
            if c.cls == "NUMERIC":
                inner = f"rt.is_numeric_class({self.operand(c.operand)})"
            elif c.cls in ("POSITIVE", "NEGATIVE", "ZERO"):
                op = {"POSITIVE": ">", "NEGATIVE": "<", "ZERO": "=="}[c.cls]
                inner = f"{self.num(c.operand)} {op} 0"
            elif c.cls.startswith("ALPHABETIC"):
                pred = {"ALPHABETIC": "isalpha", "ALPHABETIC-LOWER": "islower", "ALPHABETIC-UPPER": "isupper"}[c.cls]
                inner = f"all(ch == ' ' or ch.{pred}() for ch in rt.text_of({self.operand(c.operand)}))"
            else:
                raise _GenUnsupported(f"class condition {c.cls}")
            return f"(not {inner})" if c.negated else inner
        if isinstance(c, ir.Not):
            return f"(not {self.cond(c.operand)})"
        if isinstance(c, ir.And):
            return f"({self.cond(c.left)} and {self.cond(c.right)})"
        if isinstance(c, ir.Or):
            return f"({self.cond(c.left)} or {self.cond(c.right)})"
        raise _GenUnsupported(f"condition {type(c).__name__}")

    # ---------------- mutation hooks
    def _mut_site(self, kind: str, loc: ir.Loc | None) -> bool:
        m = self.mutation
        if m is None or m.kind != kind or loc is None:
            return False
        key = (loc.file, loc.line, kind)
        n = self.mut_counter.get(key, 0)
        self.mut_counter[key] = n + 1
        if loc.file == m.file and loc.line == m.line and n == m.ordinal:
            self.applied.append(m.id)
            return True
        return False

    def _mut_relop(self, op: str, c: ir.Rel) -> str:
        loc = getattr(c.left, "loc", None) or getattr(c.right, "loc", None)
        if op in ("<", "<=", ">", ">=") and self._mut_site("relop", loc):
            return {"<": "<=", "<=": "<", ">": ">=", ">=": ">"}[op]
        return op

    def _mut_arith(self, op: str, e: ir.BinOp) -> str:
        loc = _expr_loc(e)
        if op in ("+", "-") and self.mut_scope and self._mut_site("arith", loc):
            return "-" if op == "+" else "+"
        return op

    def _mut_literal(self, lit: ir.Literal) -> str:
        if self.mut_scope and self._mut_site("literal", lit.loc):
            from decimal import Decimal

            v = Decimal(lit.value)
            exp = v.as_tuple().exponent
            step = Decimal(1).scaleb(exp if isinstance(exp, int) else 0)
            return str(v + step)
        return lit.value

    def _rounded(self, t: ir.Target, loc: ir.Loc) -> bool:
        if t.rounded and self._mut_site("rounding", loc):
            return False
        return t.rounded

    # ---------------- statements
    def _st_move(self, s: ir.Move, ind: int) -> None:
        src = self.operand(s.source)
        for t in s.targets:
            self.emit(ind, f"rt.move({src}, {self.ref(t)})")

    def _stores(self, s, targets: list[ir.Target], value_for, ind: int, has_size_error: bool) -> None:
        for t in targets:
            r = self.ref(t.ref)
            rounded = self._rounded(t, s.loc)
            val = value_for(r)
            args = f"{val}" + (", rounded=True" if rounded else "")
            if has_size_error:
                self.emit(ind, f"if not {r}.store({args}, size_error=True):")
                self.emit(ind + 1, "_size_error = True")
            else:
                self.emit(ind, f"{r}.store({args})")

    def _arith_common(self, s, expr_py: str | None, targets, value_for, ind: int, may_raise: bool) -> None:
        on, off = s.on_size_error, s.not_on_size_error
        has_se = on is not None or off is not None
        e = self.emit
        if has_se:
            e(ind, "_size_error = False")
        body_ind = ind
        if may_raise:
            e(ind, "try:")
            if expr_py is not None:
                e(ind + 1, f"_v = {expr_py}")
            else:
                e(ind + 1, "pass")
            e(ind, "except rt.SizeError:")
            e(ind + 1, "_size_error = True" if has_se else "pass  # size error without ON SIZE ERROR: receiver unchanged")
            e(ind, "else:")
            body_ind = ind + 1
        elif expr_py is not None:
            e(ind, f"_v = {expr_py}")
        self._stores(s, targets, value_for, body_ind, has_se)
        if has_se:
            if on is not None:
                e(ind, "if _size_error:")
                self._emit_block(on, ind + 1)
                if off is not None:
                    e(ind, "else:")
                    self._emit_block(off, ind + 1)
            else:
                e(ind, "if not _size_error:")
                self._emit_block(off or [], ind + 1)

    def _st_compute(self, s: ir.Compute, ind: int) -> None:
        self.mut_scope = True
        try:
            expr = self.num(s.expr)
        finally:
            self.mut_scope = False
        self._arith_common(s, expr, s.targets, lambda r: "_v", ind, self.has_div(s.expr))

    def _st_arith(self, s: ir.Arith, ind: int) -> None:
        ops = [self.num(o) for o in s.operands]
        if not ops:
            raise _GenUnsupported("arithmetic statement without operands")
        total = ops[0] if len(ops) == 1 else "(" + " + ".join(ops) + ")"
        may_raise = False
        if s.op == "ADD":
            if s.giving:
                expr = total if s.base is None else f"({total} + {self.num(s.base)})"
                vf = lambda r: "_v"  # noqa: E731
            else:
                expr = total
                vf = lambda r: f"{r}.value + _v"  # noqa: E731
        elif s.op == "SUBTRACT":
            if s.giving:
                expr = f"({self.num(s.base)} - {total})"
                vf = lambda r: "_v"  # noqa: E731
            else:
                expr = total
                vf = lambda r: f"{r}.value - _v"  # noqa: E731
        elif s.op == "MULTIPLY":
            if s.giving:
                expr = f"({ops[0]} * {self.num(s.base)})"
                vf = lambda r: "_v"  # noqa: E731
            else:
                expr = ops[0]
                vf = lambda r: f"_v * {r}.value"  # noqa: E731
        elif s.op == "DIVIDE":
            may_raise = True
            if s.giving:
                if s.divide_by:
                    expr = f"rt.div({ops[0]}, {self.num(s.base)})"
                else:
                    expr = f"rt.div({self.num(s.base)}, {ops[0]})"
                vf = lambda r: "_v"  # noqa: E731
            else:
                # DIVIDE a INTO b: b = b / a (division evaluated per target)
                expr = ops[0]
                if s.on_size_error is None and s.not_on_size_error is None:
                    for t in s.targets:
                        r = self.ref(t.ref)
                        rounded = ", rounded=True" if self._rounded(t, s.loc) else ""
                        self.emit(ind, "try:")
                        self.emit(ind + 1, f"{r}.store(rt.div({r}.value, {expr}){rounded})")
                        self.emit(ind, "except rt.SizeError:")
                        self.emit(ind + 1, "pass  # division by zero: receiver unchanged")
                    return
                raise _GenUnsupported("DIVIDE INTO with SIZE ERROR phrase")
        else:
            raise _GenUnsupported(s.op)
        if s.remainder is not None:
            if not (s.op == "DIVIDE" and s.giving and len(s.targets) == 1):
                raise _GenUnsupported("REMAINDER requires DIVIDE ... GIVING with one receiver")
            q = self.ref(s.targets[0].ref)
            rem = self.ref(s.remainder)
            dividend = ops[0] if s.divide_by else self.num(s.base)
            divisor = self.num(s.base) if s.divide_by else ops[0]
            self._arith_common(s, expr, s.targets, vf, ind, may_raise)
            self.emit(ind, "try:")
            self.emit(ind + 1, f"_q, _ = {q}.fit(rt.div({dividend}, {divisor}))")
            self.emit(ind + 1, f"{rem}.store({dividend} - _q * {divisor})")
            self.emit(ind, "except rt.SizeError:")
            self.emit(ind + 1, "pass")
            return
        self._arith_common(s, expr, s.targets, vf, ind, may_raise)

    def _st_if(self, s: ir.If, ind: int) -> None:
        self.emit(ind, f"if {self.cond(s.cond)}:")
        self._emit_block(s.then, ind + 1)
        if s.orelse:
            self.emit(ind, "else:")
            self._emit_block(s.orelse, ind + 1)

    def _when_match(self, subjects, line: list[ir.WhenObject]) -> str:
        parts = []
        for subj, obj in zip(subjects, line, strict=False):
            if obj.kind == "any":
                continue
            if subj in ("TRUE", "FALSE"):
                if obj.kind == "cond":
                    c = self.cond(obj.cond)
                    parts.append(c if subj == "TRUE" else f"(not {c})")
                elif obj.kind in ("true", "false"):
                    parts.append("True" if (obj.kind == "true") == (subj == "TRUE") else "False")
                else:
                    raise _GenUnsupported("EVALUATE TRUE with a value object")
                continue
            if isinstance(subj, ir.Rel | ir.CondRef | ir.ClassCond | ir.Not | ir.And | ir.Or):
                c = self.cond(subj)
                if obj.kind == "true":
                    parts.append(c)
                elif obj.kind == "false":
                    parts.append(f"(not {c})")
                else:
                    raise _GenUnsupported("condition subject with value object")
                continue
            numeric = self.is_numeric_expr(subj)
            sv = self.num(subj) if isinstance(subj, ir.BinOp | ir.Neg) else self.operand(subj)
            if obj.kind == "value":
                if numeric and self.is_numeric_expr(obj.value):
                    m = f"{self.num(subj)} == {self.num(obj.value)}"
                else:
                    m = f"rt.cmp({sv}, {self.operand(obj.value)}) == 0"
            elif obj.kind == "range":
                m = f"(rt.cmp({sv}, {self.operand(obj.value)}) >= 0 and rt.cmp({sv}, {self.operand(obj.high)}) <= 0)"
            elif obj.kind == "cond":
                m = self.cond(obj.cond)
            else:
                raise _GenUnsupported(f"WHEN object {obj.kind} for value subject")
            parts.append(f"(not {m})" if obj.negated else m)
        return " and ".join(parts) if parts else "True"

    def _st_evaluate(self, s: ir.Evaluate, ind: int) -> None:
        first = True
        other: ir.When | None = None
        for w in s.whens:
            if w.other:
                other = w
                if w.objects:
                    # WHEN a WHEN OTHER (objects before OTHER) - treat as OTHER
                    pass
                continue
            test = " or ".join(f"({self._when_match(s.subjects, line)})" for line in w.objects) or "False"
            self.emit(ind, f"{'if' if first else 'elif'} {test}:  # WHEN {self.where(w.loc)}")
            self._emit_block(w.body, ind + 1)
            first = False
        if other is not None:
            if first:
                self._emit_block(other.body, ind)
            else:
                self.emit(ind, f"else:  # WHEN OTHER {self.where(other.loc)}")
                self._emit_block(other.body, ind + 1)
        elif first:
            self.emit(ind, "pass")

    def _perform_call(self, s: ir.Perform) -> str:
        if s.thru:
            return f"self.perform({s.target!r}, {s.thru!r})"
        return f"self.perform({s.target!r})"

    def _perform_body(self, s: ir.Perform, ind: int) -> None:
        if s.target is not None:
            self.emit(ind, self._perform_call(s))
        else:
            self.loop_depth += 1
            self._emit_block(s.body or [], ind)
            self.loop_depth -= 1

    def _st_perform(self, s: ir.Perform, ind: int) -> None:
        e = self.emit
        if s.varying:
            self._varying(s, 0, ind)
            return
        if s.times is not None:
            e(ind, f"for _ in range(max(0, int({self.num(s.times)}))):")
            self._perform_body(s, ind + 1)
            return
        if s.until is not None:
            if s.test_after:
                e(ind, "while True:")
                self._perform_body(s, ind + 1)
                e(ind + 1, f"if {self.cond(s.until)}:")
                e(ind + 2, "break")
            else:
                e(ind, f"while not ({self.cond(s.until)}):")
                self._perform_body(s, ind + 1)
            return
        if s.target is not None:
            e(ind, self._perform_call(s))
        else:
            # inline PERFORM without loop: body runs once (EXIT PERFORM needs a loop)
            e(ind, "for _ in range(1):")
            self._perform_body(s, ind + 1)

    def _varying(self, s: ir.Perform, k: int, ind: int) -> None:
        v = s.varying[k]
        var = self.ref(v.var)
        e = self.emit
        e(ind, f"{var}.store({self.num(v.start)})")
        e(ind, f"while not ({self.cond(v.until)}):")
        if k + 1 < len(s.varying):
            self._varying(s, k + 1, ind + 1)
        else:
            self._perform_body(s, ind + 1)
        e(ind + 1, f"{var}.store({var}.value + {self.num(v.by)})")

    def _st_call(self, s: ir.Call, ind: int) -> None:
        if isinstance(s.program, ir.Literal):
            name = repr(s.program.value.strip())
        else:
            name = self.operand(s.program)
        args = []
        content = []
        for i, a in enumerate(s.using):
            if a.mode == "VALUE":
                raise _GenUnsupported("CALL BY VALUE")
            args.append(self.operand(a.expr))
            if a.mode == "CONTENT" or not isinstance(a.expr, ir.Ref):
                content.append(i)
        if s.returning is not None:
            raise _GenUnsupported("CALL RETURNING")
        c = f", content={tuple(content)!r}" if content else ""
        call = f"self.call_program({name}{', ' + ', '.join(args) if args else ''}{c})"
        if s.on_exception is not None or s.not_on_exception is not None:
            self.emit(ind, "try:")
            self.emit(ind + 1, call)
            self.emit(ind, "except rt.ProgramNotFound:")
            self._emit_block(s.on_exception or [], ind + 1)
            if s.not_on_exception:
                self.emit(ind, "else:")
                self._emit_block(s.not_on_exception, ind + 1)
        else:
            self.emit(ind, call)

    def _st_stoprun(self, s, ind: int) -> None:
        self.emit(ind, "raise rt.StopRun()")

    def _st_goback(self, s, ind: int) -> None:
        self.emit(ind, "raise rt.Goback()")

    def _st_exit(self, s: ir.Exit, ind: int) -> None:
        if s.what == "":
            self.emit(ind, "pass  # EXIT")
        elif s.what == "PARAGRAPH":
            self.emit(ind, "return  # EXIT PARAGRAPH")
        elif s.what == "PROGRAM":
            self.emit(ind, "self.exit_program()")
        elif s.what == "PERFORM" and self.loop_depth > 0:
            self.emit(ind, "break  # EXIT PERFORM")
        elif s.what == "PERFORM CYCLE" and self.loop_depth > 0:
            raise _GenUnsupported("EXIT PERFORM CYCLE")
        else:
            raise _GenUnsupported(f"EXIT {s.what}")

    def _st_goto(self, s: ir.GoTo, ind: int) -> None:
        names = {p.name for p in self.p.paragraphs} | {sec.name for sec in self.p.sections}
        if s.target not in names:
            raise _GenUnsupported(f"GO TO unknown target {s.target}")
        self.emit(ind, f"raise rt.GoTo({s.target!r})")

    def _st_continue(self, s, ind: int) -> None:
        self.emit(ind, "pass  # CONTINUE")

    def _st_display(self, s: ir.Display, ind: int) -> None:
        ops = ", ".join(self.operand(o) for o in s.operands)
        adv = ", advance=False" if s.no_advancing else ""
        if s.upon in ("SYSERR", "STDERR"):
            self.emit(ind, f"pass  # DISPLAY UPON {s.upon} (stderr) is not part of the compared output")
            return
        self.emit(ind, f"rt.display(self.ctx{', ' + ops if ops else ''}{adv})")

    def _st_accept(self, s: ir.Accept, ind: int) -> None:
        src = f", {s.source!r}" if s.source else ""
        self.emit(ind, f"rt.accept(self.ctx, {self.ref(s.target)}{src})")

    def _st_initialize(self, s: ir.Initialize, ind: int) -> None:
        for t in s.targets:
            self.emit(ind, f"rt.initialize({self.ref(t)})")

    def _st_setstmt(self, s: ir.SetStmt, ind: int) -> None:
        for t in s.targets:
            if s.mode == "TRUE":
                if not t.cond:
                    raise _GenUnsupported(f"SET {t.name} TO TRUE: not a condition name")
                subs = ", ".join(self.subscript(x) for x in t.subscripts)
                self.emit(ind, f"self.{self.cond_attr[t.cond]}.set_true({subs})")
            elif s.mode == "TO":
                self.emit(ind, f"{self.ref(t)}.store({self.num(s.value)})")
            elif s.mode in ("UP", "DOWN"):
                r = self.ref(t)
                op = "+" if s.mode == "UP" else "-"
                self.emit(ind, f"{r}.store({r}.value {op} {self.num(s.value)})")
            else:
                raise _GenUnsupported(f"SET mode {s.mode}")

    def _st_stringstmt(self, s: ir.StringStmt, ind: int) -> None:
        parts = ", ".join(f"({self.operand(p.expr)}, {self.operand(p.delimiter) if p.delimiter is not None else 'None'})" for p in s.parts)
        ptr = f", pointer={self.ref(s.pointer)}" if s.pointer else ""
        call = f"rt.string_into({self.ref(s.into)}, [{parts}]{ptr})"
        if s.on_overflow is None and s.not_on_overflow is None:
            self.emit(ind, call)
            return
        self.emit(ind, f"if {call}:")
        self._emit_block(s.on_overflow or [], ind + 1)
        if s.not_on_overflow:
            self.emit(ind, "else:")
            self._emit_block(s.not_on_overflow, ind + 1)

    def _st_unsupported(self, s: ir.Unsupported, ind: int) -> None:
        self._unsupported(s, ind, s.reason)


class _GenUnsupported(Exception):
    pass


def _expr_loc(e) -> ir.Loc | None:
    if isinstance(e, ir.Literal | ir.Ref | ir.FuncCall):
        return e.loc
    if isinstance(e, ir.BinOp):
        return _expr_loc(e.left) or _expr_loc(e.right)
    if isinstance(e, ir.Neg):
        return _expr_loc(e.operand)
    return None


def mutation_candidates(prog: ir.Program) -> list[Mutation]:
    """Enumerate deterministic mutation sites (same order the generator visits them)."""
    out: list[Mutation] = []
    counters: dict[tuple[str, int, str], int] = {}

    def add(kind: str, loc: ir.Loc | None, detail: str) -> None:
        if loc is None:
            return
        key = (loc.file, loc.line, kind)
        n = counters.get(key, 0)
        counters[key] = n + 1
        out.append(Mutation(id=f"{kind}@{loc.file}:{loc.line}#{n}", kind=kind, file=loc.file, line=loc.line, detail=detail, ordinal=n))

    def visit_expr(e) -> None:
        if isinstance(e, ir.BinOp):
            if e.op in ("+", "-"):
                add("arith", _expr_loc(e), f"replace '{e.op}' with '{'-' if e.op == '+' else '+'}'")
            visit_expr(e.left)
            visit_expr(e.right)
        elif isinstance(e, ir.Neg):
            visit_expr(e.operand)
        elif isinstance(e, ir.Literal) and e.kind == "number":
            add("literal", e.loc, f"change literal {e.value} by one unit in the last place")

    def visit_cond(c) -> None:
        if isinstance(c, ir.Rel):
            if c.op in ("<", "<=", ">", ">="):
                flipped = {"<": "<=", "<=": "<", ">": ">=", ">=": ">"}[c.op]
                add("relop", getattr(c.left, "loc", None) or getattr(c.right, "loc", None), f"replace '{c.op}' with '{flipped}'")
        elif isinstance(c, ir.Not):
            visit_cond(c.operand)
        elif isinstance(c, ir.And | ir.Or):
            visit_cond(c.left)
            visit_cond(c.right)

    for par in prog.paragraphs:
        for s in ir.walk_statements(par.statements):
            if isinstance(s, ir.Compute):
                visit_expr(s.expr)
                for t in s.targets:
                    if t.rounded:
                        add("rounding", s.loc, f"drop ROUNDED on {t.ref.name}")
            elif isinstance(s, ir.Arith):
                for t in s.targets:
                    if t.rounded:
                        add("rounding", s.loc, f"drop ROUNDED on {t.ref.name}")
            elif isinstance(s, ir.If):
                visit_cond(s.cond)
            elif isinstance(s, ir.Evaluate):
                for w in s.whens:
                    for line in w.objects:
                        for o in line:
                            if o.cond is not None:
                                visit_cond(o.cond)
            elif isinstance(s, ir.Perform):
                if s.until is not None:
                    visit_cond(s.until)
                for v in s.varying:
                    visit_cond(v.until)
    return out
