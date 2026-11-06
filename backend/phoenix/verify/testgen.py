"""Deterministic differential test-case generation.

Heuristics (documented in docs/verification.md):

1. **Fixtures** shipped with the project (or entered by the user) are used verbatim.
2. **Boundary values** for every input field X derived from the IR:
   * ``X <op> literal``      -> literal - 1 ulp, literal, literal + 1 ulp
   * ``X <op> Y`` (Y not an input) -> literals MOVEd to Y, +/- 1 ulp
   * 88-level conditions on X -> every VALUE (and THRU bounds +/- 1 ulp) plus a non-matching value
   * ``EVALUATE X WHEN literal`` -> every WHEN literal plus a non-matching value
   Each value is applied one-factor-at-a-time to every fixture baseline.
3. **Edge values**: zero / maximum / negative maximum for numeric inputs, SPACES for alphanumeric inputs.
4. **Seeded random combinations** of the candidate values (``random.Random(seed)``).
5. **Coverage-guided placement**: each boundary value is applied to a fixture that executes
   the statement it was derived from.
6. **Validity-aware placement** (optional ``reaches`` callback): the placed case is traced through
   the generated Python; if it does not execute its source statement, other fixtures and then
   guard-field adjustments (collected candidates only) are tried, bounded and deterministic.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal

from ..cobol import ir
from .records import RecordCodec

PLACEMENT_MAX_ATTEMPTS = 24  # traced runs per boundary value (already-traced stdins do not count)

Inputs = dict[str, dict[str, object]]
Reaches = Callable[[Inputs, str], bool]


class TraceUnavailable(Exception):  # noqa: N818 - signal, not an error report
    """Raised by a ``reaches`` callback when the generated Python cannot be traced."""


@dataclass
class TestCase:
    id: str
    kind: str  # fixture | boundary | edge | random
    description: str
    inputs: dict[str, dict[str, object]] = field(default_factory=dict)  # param name -> field key -> value
    stdin: str = ""


def _ulp(item: ir.DataItem) -> Decimal:
    return Decimal(1).scaleb(-(item.picture.scale if item.picture else 0))


def _max(item: ir.DataItem) -> Decimal:
    p = item.picture
    return Decimal(10) ** (p.digits - p.scale) - _ulp(item)


def _fits(item: ir.DataItem, v: Decimal) -> bool:
    p = item.picture
    if v < 0 and not p.signed:
        return False
    return abs(v) <= _max(item) and v == v.quantize(_ulp(item))


class CandidateCollector:
    def __init__(self, prog: ir.Program, inputs: set[str]) -> None:
        self.prog = prog
        self.index = prog.item_index()
        self.inputs = inputs
        self.values: dict[str, list[tuple[object, str, str | None]]] = {}  # item id -> [(value, why, statement key)]
        self.current_key: str | None = None
        self.reader_keys: dict[str, set[str]] = {}  # item id -> statements that read it
        self.moved_literals: dict[str, list[ir.Literal]] = {}
        # conditional statements (IF / EVALUATE / PERFORM UNTIL|VARYING): (file, line, key, input ids read)
        self.guards: list[tuple[str, int, str, list[str]]] = []
        for par in prog.paragraphs:
            for s in ir.walk_statements(par.statements):
                if isinstance(s, ir.Move) and isinstance(s.source, ir.Literal) and s.source.kind == "number":
                    for t in s.targets:
                        if t.item:
                            self.moved_literals.setdefault(t.item, []).append(s.source)

    def add(self, iid: str, value: object, why: str) -> None:
        it = self.index.get(iid)
        if it is None or iid not in self.inputs:
            return
        if it.is_numeric:
            try:
                v = Decimal(str(value))
            except Exception:  # noqa: BLE001
                return
            if not _fits(it, v):
                return
            value = v
        else:
            value = str(value)[: it.size]
        lst = self.values.setdefault(iid, [])
        if all(not (str(x) == str(value) and k == self.current_key) for x, _w, k in lst):
            lst.append((value, why, self.current_key))

    def numeric_around(self, iid: str, lit: Decimal, why: str) -> None:
        it = self.index.get(iid)
        if it is None or not it.is_numeric:
            return
        u = _ulp(it)
        for v, tag in ((lit - u, "just below"), (lit, "equal to"), (lit + u, "just above")):
            self.add(iid, v, f"{tag} {why}")

    def visit_cond(self, c, where: str) -> None:
        if isinstance(c, ir.Rel):
            for a, b in ((c.left, c.right), (c.right, c.left)):
                if isinstance(a, ir.Ref) and a.item in self.inputs:
                    it = self.index[a.item]
                    if isinstance(b, ir.Literal):
                        if b.kind == "number" and it.is_numeric:
                            self.numeric_around(a.item, b.decimal, f"{b.value} ({where})")
                        elif b.kind == "string":
                            self.add(a.item, b.value, f"matches '{b.value}' ({where})")
                            self.add(a.item, "~" * min(it.size, 1), f"does not match '{b.value}' ({where})")
                        elif b.kind == "figurative" and b.value == "SPACE":
                            self.add(a.item, "", f"SPACES ({where})")
                            self.add(a.item, "X", f"not SPACES ({where})")
                        elif b.kind == "figurative" and b.value == "ZERO" and it.is_numeric:
                            self.numeric_around(a.item, Decimal(0), f"ZERO ({where})")
                    elif isinstance(b, ir.Ref) and b.item and self.moved_literals.get(b.item) and it.is_numeric:
                        for lit in self.moved_literals.get(b.item, []):
                            self.numeric_around(a.item, lit.decimal, f"{b.name}={lit.value} ({where})")
        elif isinstance(c, ir.CondRef) and c.ref.cond:
            parent_id, name = c.ref.cond.split("::")
            if parent_id in self.inputs:
                it = self.index[parent_id]
                cond = next(x for x in it.conditions if x.name == name)
                for v in cond.values:
                    if v.low.kind == "figurative":
                        continue
                    if it.is_numeric and v.low.kind == "number":
                        self.add(parent_id, v.low.decimal, f"88 {name} ({where})")
                        if v.high is not None:
                            self.numeric_around(parent_id, v.low.decimal, f"88 {name} low bound")
                            self.numeric_around(parent_id, v.high.decimal, f"88 {name} high bound")
                    else:
                        self.add(parent_id, v.low.value, f"88 {name} ({where})")
                if not it.is_numeric:
                    self.add(parent_id, "?", f"no 88-level of {it.name} matches")
        elif isinstance(c, ir.Not):
            self.visit_cond(c.operand, where)
        elif isinstance(c, ir.And | ir.Or):
            self.visit_cond(c.left, where)
            self.visit_cond(c.right, where)

    def collect(self) -> None:
        from ..analysis.dataflow import stmt_access

        for par in self.prog.paragraphs:
            for s in ir.walk_statements(par.statements):
                where = f"{s.loc.file}:{s.loc.line}"
                self.current_key = where
                reads = stmt_access(s).reads
                for iid in reads:
                    self.reader_keys.setdefault(iid, set()).add(where)
                if isinstance(s, ir.If | ir.Evaluate) or (isinstance(s, ir.Perform) and (s.until is not None or s.varying)):
                    self.guards.append((s.loc.file, s.loc.line, where, sorted(reads & self.inputs)))
                if isinstance(s, ir.If):
                    self.visit_cond(s.cond, where)
                elif isinstance(s, ir.Perform):
                    if s.until is not None:
                        self.visit_cond(s.until, where)
                    for v in s.varying:
                        self.visit_cond(v.until, where)
                elif isinstance(s, ir.Evaluate):
                    for subj in s.subjects:
                        if isinstance(subj, ir.Ref) and subj.item in self.inputs:
                            it = self.index[subj.item]
                            for w in s.whens:
                                for line in w.objects:
                                    o = line[0]
                                    if o.kind == "value" and isinstance(o.value, ir.Literal):
                                        if o.value.kind == "number":
                                            self.add(subj.item, o.value.decimal, f"WHEN {o.value.value} ({where})")
                                        elif o.value.kind == "string":
                                            self.add(subj.item, o.value.value, f"WHEN '{o.value.value}' ({where})")
                                        elif o.value.kind == "figurative" and o.value.value == "SPACE":
                                            self.add(subj.item, "", f"WHEN SPACES ({where})")
                            if not it.is_numeric:
                                self.add(subj.item, "?????"[: it.size], f"WHEN OTHER ({where})")
                    for w in s.whens:
                        for line in w.objects:
                            for o in line:
                                if o.cond is not None:
                                    self.visit_cond(o.cond, where)
        self.current_key = None
        for iid in sorted(self.inputs):
            it = self.index.get(iid)
            if it is None or it.children:
                continue
            if it.is_numeric and it.picture:
                self.add(iid, Decimal(0), "edge: zero")
                self.add(iid, _max(it), "edge: maximum value")
                if it.picture.signed:
                    self.add(iid, -_max(it), "edge: negative maximum")
            else:
                self.add(iid, "", "edge: SPACES")


def field_key(it: ir.DataItem, occurrence: int | None = None) -> str:
    if it.dims and occurrence is not None:
        subs = [occurrence] + [1] * (len(it.dims) - 1)
        return f"{it.name}({', '.join(map(str, subs))})"
    if it.dims:
        return f"{it.name}({', '.join('1' for _ in it.dims)})"
    return it.name


def generate_cases(
    prog: ir.Program,
    input_ids: set[str],
    codecs: dict[str, RecordCodec],
    fixtures: list[dict],
    seed: int = 20261031,
    max_cases: int = 220,
    n_random: int = 40,
    fixture_coverage: dict[str, set[str]] | None = None,
    reaches: Reaches | None = None,
) -> list[TestCase]:
    """Build linkage-mode cases. ``codecs`` maps USING root id -> codec.

    ``fixture_coverage`` (fixture id -> COBOL statement keys executed by that
    fixture in the generated Python) enables *coverage-guided placement*: each
    boundary value is applied to a fixture that actually executes the statement
    the boundary was derived from, instead of always the first fixture.

    ``reaches(inputs, key)`` (validity-aware placement) reports whether a case with
    ``inputs`` executes the COBOL statement ``key`` in the generated Python. When given,
    every boundary case is checked and, if it misses its statement, re-placed on other
    fixtures that execute it, then on the preferred fixture with guard fields adjusted to
    collected candidate values (one field, then pairs), at most ``PLACEMENT_MAX_ATTEMPTS``
    new traced inputs per boundary value. An optional ``reaches.prefetch(list[inputs])``
    lets the callback trace the preferred placements in one batch. ``reaches`` may raise
    ``TraceUnavailable``; the search is then disabled for the rest of the generation.
    """
    index = prog.item_index()
    root_of = {iid: index[iid].record for iid in input_ids if iid in index}
    root_name = {rid: index[rid].name for rid in codecs}
    col = CandidateCollector(prog, input_ids)
    col.collect()
    cases: list[TestCase] = []
    seen: set[str] = set()

    def encode(inputs: Inputs) -> str:
        return encode_inputs(codecs, inputs)

    def push(tc: TestCase) -> None:
        if len(cases) >= max_cases:
            return
        tc.stdin = encode(tc.inputs)
        if tc.stdin in seen:
            return
        seen.add(tc.stdin)
        cases.append(tc)

    baselines = fixtures or [{"id": "defaults", "description": "all inputs at their initial (INITIALIZE) values", "inputs": {}}]
    for fx in fixtures:
        push(TestCase(id=f"fixture-{fx['id']}", kind="fixture", description=fx.get("description", ""), inputs=_copy(fx.get("inputs", {}))))
    base = baselines[0]
    cov = fixture_coverage or {}

    def baseline_for(iid: str, key: str | None) -> dict:
        wanted = {key} if key else col.reader_keys.get(iid, set())
        for fx in fixtures:
            if cov.get(fx["id"], set()) & wanted:
                return fx
        return base

    def place(b: dict, assigns: list[tuple[ir.DataItem, str, object]]) -> Inputs:
        inputs = _copy(b.get("inputs", {}))
        for it, rname, value in assigns:
            _assign(inputs, rname, it, value)
        return inputs

    # (n, iid, value, why, key, preferred fixture)
    placements: list[tuple[int, str, object, str, str | None, dict]] = []
    n = 0
    for iid in sorted(col.values):
        if root_name.get(root_of.get(iid, ""), None) is None:
            continue
        for value, why, key in col.values[iid]:
            n += 1
            placements.append((n, iid, value, why, key, baseline_for(iid, key)))

    search = reaches is not None and bool(fixtures)
    traced: set[str] = set()  # stdins already traced during this generation (not counted again)
    pre = getattr(reaches, "prefetch", None)
    if search:
        if pre is not None:
            try:
                pre([place(b, [(index[iid], root_name[root_of[iid]], value)]) for _n, iid, value, _w, key, b in placements if key])
            except TraceUnavailable:
                search = False

    def find_placement(iid: str, value: object, key: str, b: dict) -> tuple[Inputs, dict, list[tuple[str, object]], bool]:
        """Return (inputs, fixture used, adjusted fields, reached)."""
        it = index[iid]
        own = (it, root_name[root_of[iid]], value)
        first = place(b, [own])
        first_stdin = encode(first)
        attempts = 0 if first_stdin in traced else 1  # the preferred placement (batched by the prefetch above)
        traced.add(first_stdin)
        if reaches(first, key):
            return first, b, [], True
        # Ordered alternatives: (inputs, fixture, adjusted fields).
        alternatives: list[tuple[Inputs, dict, list[tuple[str, object]]]] = []
        # 2. other fixtures that execute the target statement, in fixture order
        for fx in fixtures:
            if fx is not b and key in cov.get(fx["id"], set()):
                alternatives.append((place(fx, [own]), fx, []))
        # 3. guard fields: inputs read by conditions executed (on the failing run) before the target
        s_file, _, s_line = key.rpartition(":")
        guard_ids: list[str] = []
        for g_file, g_line, g_key, g_reads in sorted(col.guards, key=lambda g: (g[1], g[2])):
            if g_file != s_file or g_line >= int(s_line) or not reaches(first, g_key):
                continue
            for gid in g_reads:
                if gid != iid and gid not in guard_ids and gid in col.values and root_name.get(root_of.get(gid, ""), None):
                    guard_ids.append(gid)

        def assign(gid: str, gv: object) -> tuple[ir.DataItem, str, object]:
            return (index[gid], root_name[root_of[gid]], gv)

        firsts: dict[str, object] = {}  # first candidate of each guard field that changes the case
        for gid in guard_ids:
            for gv, _w, _k in col.values[gid]:
                cand = place(b, [assign(gid, gv), own])
                alternatives.append((cand, b, [(index[gid].name, gv)]))
                if gid not in firsts and encode(cand) != first_stdin:
                    firsts[gid] = gv
        pair_ids = [g for g in guard_ids if g in firsts]
        for i, g1 in enumerate(pair_ids):
            for g2 in pair_ids[i + 1 :]:
                cand = place(b, [assign(g1, firsts[g1]), assign(g2, firsts[g2]), own])
                alternatives.append((cand, b, [(index[g1].name, firsts[g1]), (index[g2].name, firsts[g2])]))
        # Budget: at most PLACEMENT_MAX_ATTEMPTS stdins not traced before (the failing first try counts).
        selected: list[tuple[Inputs, dict, list[tuple[str, object]]]] = []
        new: list[Inputs] = []
        for alt in alternatives:
            s = encode(alt[0])
            if s not in traced:
                if attempts >= PLACEMENT_MAX_ATTEMPTS:
                    break
                attempts += 1
                traced.add(s)
                new.append(alt[0])
            selected.append(alt)
        if new and pre is not None:
            pre(new)  # one batched trace for the whole search
        for cand, fx, adjusted in selected:
            if reaches(cand, key):
                return cand, fx, adjusted, True
        return first, b, [], False

    for n, iid, value, why, key, b in placements:
        it = index[iid]
        kind = "edge" if why.startswith("edge") else "boundary"
        if search and key and len(cases) < max_cases:
            try:
                inputs, used, adjusted, reached = find_placement(iid, value, key, b)
            except TraceUnavailable:
                search = False
            else:
                adj = "".join(f"; {name}={v!s:.20}" for name, v in adjusted)
                note = f" [on fixture {used['id']}{adj}]" + ("" if reached else f" [target {key} not reached]")
                push(TestCase(id=f"{kind}-{n:03d}", kind=kind, description=f"{it.name} = {value!s:.40} — {why}{note}", inputs=inputs))
                continue
        inputs = place(b, [(it, root_name[root_of[iid]], value)])
        on = f" [on fixture {b['id']}]" if b is not base else ""
        push(TestCase(id=f"{kind}-{n:03d}", kind=kind, description=f"{it.name} = {value!s:.40} — {why}{on}", inputs=inputs))
    rng = random.Random(seed)
    keys = sorted(col.values)
    for k in range(n_random):
        b = baselines[k % len(baselines)]
        inputs = _copy(b.get("inputs", {}))
        picked = []
        for iid in keys:
            if rng.random() < 0.5:
                continue
            it = index[iid]
            rname = root_name.get(root_of.get(iid, ""), None)
            if rname is None:
                continue
            value, _, _ = rng.choice(col.values[iid])
            occ = rng.randint(1, it.dims[0][1]) if it.dims else None
            inputs.setdefault(rname, {})[field_key(it, occ)] = value
            picked.append(f"{field_key(it, occ)}={value!s:.20}")
        push(TestCase(id=f"random-{k + 1:03d}", kind="random", description=f"seed {seed}: " + ", ".join(picked)[:300], inputs=inputs))
    return cases


def encode_inputs(codecs: dict[str, RecordCodec], inputs: Inputs) -> str:
    """Harness stdin for ``inputs``: one encoded record per USING parameter."""
    return "\n".join(codec.encode(inputs.get(codec.root.name, {})) for codec in codecs.values()) + "\n"


def _assign(inputs: Inputs, rname: str, it: ir.DataItem, value: object) -> None:
    if it.dims:
        # table element: apply to every occurrence so the value reaches
        # whichever occurrence the fixture actually uses
        for occ in range(1, it.dims[0][1] + 1):
            inputs.setdefault(rname, {})[field_key(it, occ)] = value
    else:
        inputs.setdefault(rname, {})[field_key(it)] = value


def _copy(d: dict) -> dict:
    return {k: dict(v) for k, v in d.items()}
