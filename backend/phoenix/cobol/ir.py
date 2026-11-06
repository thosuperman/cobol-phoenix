"""Normalized intermediate representation (IR).

The IR is independent of any code generator. Every node that originates from
source carries a :class:`Loc` pointing to a real file and line range.
All nodes are plain dataclasses and serialise to JSON via :func:`to_jsonable`.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class Loc:
    file: str
    line: int
    end_line: int

    def span(self, other: Loc | None) -> Loc:
        if other is None or other.file != self.file:
            return self
        return Loc(self.file, min(self.line, other.line), max(self.end_line, other.end_line))


# ---------------------------------------------------------------- data division
@dataclass(slots=True)
class Picture:
    raw: str
    category: str  # alphanumeric | alphabetic | numeric | numeric-edited | alphanumeric-edited
    size: int  # display length in characters
    digits: int = 0  # numeric digit positions (incl. P scaling digits)
    scale: int = 0  # digits right of the implied/actual decimal point
    signed: bool = False
    expanded: str = ""  # picture with repetitions expanded, e.g. 9(3)V99 -> 999V99
    p_scaling: int = 0  # P positions (unsupported for generation)


@dataclass(slots=True)
class ConditionValue:
    low: Literal
    high: Literal | None = None


@dataclass(slots=True)
class ConditionName:
    name: str
    values: list[ConditionValue]
    loc: Loc
    parent: str = ""  # qualified id of the parent item


@dataclass
class DataItem:
    id: str  # unique id within program, e.g. "WS-POLICY-MASTER-REC.PM-CONTROL-AREA.PM-POLICY-ID"
    level: int
    name: str  # upper-case; "FILLER" for fillers
    loc: Loc
    section: str  # WORKING-STORAGE | LINKAGE | FILE | LOCAL-STORAGE
    picture: Picture | None = None
    usage: str = "DISPLAY"  # DISPLAY | COMP | COMP-3 | COMP-5 | INDEX | POINTER | COMP-1 | COMP-2
    value: Literal | None = None
    occurs: int = 0
    occurs_min: int = 0
    occurs_depending: str | None = None
    indexed_by: list[str] = field(default_factory=list)
    redefines: str | None = None
    sign_separate: bool = False
    sign_leading: bool = False
    justified: bool = False
    blank_when_zero: bool = False
    is_filler: bool = False
    external: bool = False
    children: list[DataItem] = field(default_factory=list)
    conditions: list[ConditionName] = field(default_factory=list)
    # layout (filled by layout pass)
    offset: int = 0  # byte offset within the record (01/77 root)
    size: int = 0  # bytes of ONE occurrence
    record: str = ""  # id of the 01/77 root
    parent: str | None = None
    # list of (stride, max) for each OCCURS dimension, outermost first
    dims: list[tuple[int, int]] = field(default_factory=list)
    is_constant: bool = False  # level 78

    @property
    def is_group(self) -> bool:
        return bool(self.children) or (self.picture is None and self.usage not in ("COMP-1", "COMP-2", "INDEX", "POINTER"))

    @property
    def is_numeric(self) -> bool:
        if self.usage in ("COMP", "COMP-3", "COMP-5", "COMP-1", "COMP-2", "INDEX"):
            return True
        return self.picture is not None and self.picture.category == "numeric"

    @property
    def is_edited(self) -> bool:
        return self.picture is not None and self.picture.category.endswith("edited")


@dataclass
class FileControl:
    name: str
    assign: str
    organization: str
    access: str
    status: str | None
    loc: Loc
    record: str | None = None


# ---------------------------------------------------------------- expressions
@dataclass(slots=True)
class Literal:
    kind: str  # number | string | figurative
    value: str  # number text, string value or figurative name (ZERO, SPACE, ...)
    all: bool = False  # ALL "x"
    loc: Loc | None = None

    @property
    def decimal(self) -> Decimal:
        return Decimal(self.value)


@dataclass(slots=True)
class RefMod:
    start: Expr
    length: Expr | None


@dataclass(slots=True)
class Ref:
    name: str
    qualifiers: list[str] = field(default_factory=list)
    subscripts: list[Expr] = field(default_factory=list)
    refmod: RefMod | None = None
    item: str | None = None  # resolved DataItem id
    cond: str | None = None  # resolved 88-level (qualified "<parent>::<name>")
    special: str | None = None  # RETURN-CODE, LENGTH OF ...
    loc: Loc | None = None


@dataclass(slots=True)
class BinOp:
    op: str  # + - * / **
    left: Expr
    right: Expr


@dataclass(slots=True)
class Neg:
    operand: Expr


@dataclass(slots=True)
class FuncCall:
    name: str
    args: list[Expr]
    keywords: list[str] = field(default_factory=list)  # e.g. TRAILING for TRIM
    loc: Loc | None = None


Expr = Literal | Ref | BinOp | Neg | FuncCall


# ---------------------------------------------------------------- conditions
@dataclass(slots=True)
class Rel:
    left: Expr
    op: str  # = <> < <= > >=
    right: Expr


@dataclass(slots=True)
class CondRef:
    ref: Ref


@dataclass(slots=True)
class ClassCond:
    operand: Expr
    cls: str  # NUMERIC ALPHABETIC ALPHABETIC-LOWER ALPHABETIC-UPPER POSITIVE NEGATIVE ZERO
    negated: bool = False


@dataclass(slots=True)
class Not:
    operand: Cond


@dataclass(slots=True)
class And:
    left: Cond
    right: Cond


@dataclass(slots=True)
class Or:
    left: Cond
    right: Cond


Cond = Rel | CondRef | ClassCond | Not | And | Or


# ---------------------------------------------------------------- statements
@dataclass
class Stmt:
    loc: Loc
    kind: str = ""


@dataclass
class Target:
    ref: Ref
    rounded: bool = False


@dataclass
class Move(Stmt):
    source: Expr = None  # type: ignore[assignment]
    targets: list[Ref] = field(default_factory=list)
    kind: str = "MOVE"


@dataclass
class Compute(Stmt):
    targets: list[Target] = field(default_factory=list)
    expr: Expr = None  # type: ignore[assignment]
    on_size_error: list[Stmt] | None = None
    not_on_size_error: list[Stmt] | None = None
    kind: str = "COMPUTE"


@dataclass
class Arith(Stmt):
    """ADD / SUBTRACT / MULTIPLY / DIVIDE normalised.

    op: ADD | SUBTRACT | MULTIPLY | DIVIDE
    form: TO / FROM / BY / INTO / GIVING
    For non-GIVING forms each target t becomes ``t = t <op> operands``.
    For GIVING forms each target becomes ``t = <expr over operands>``.
    """

    op: str = ""
    operands: list[Expr] = field(default_factory=list)
    base: Expr | None = None  # the TO/FROM/BY/INTO operand when GIVING is used
    targets: list[Target] = field(default_factory=list)
    giving: bool = False
    divide_by: bool = False  # DIVIDE a BY b (a is dividend)
    remainder: Ref | None = None
    on_size_error: list[Stmt] | None = None
    not_on_size_error: list[Stmt] | None = None
    kind: str = "ARITH"


@dataclass
class If(Stmt):
    cond: Cond = None  # type: ignore[assignment]
    then: list[Stmt] = field(default_factory=list)
    orelse: list[Stmt] = field(default_factory=list)
    kind: str = "IF"


@dataclass
class WhenObject:
    kind: str  # any | true | false | value | range | cond
    value: Expr | None = None
    high: Expr | None = None
    cond: Cond | None = None
    negated: bool = False


@dataclass
class When:
    objects: list[list[WhenObject]]  # one list (per ALSO subject) per WHEN line
    body: list[Stmt]
    loc: Loc
    other: bool = False


@dataclass
class Evaluate(Stmt):
    subjects: list[Expr | Cond | str] = field(default_factory=list)  # "TRUE"/"FALSE" strings or expr/cond
    whens: list[When] = field(default_factory=list)
    kind: str = "EVALUATE"


@dataclass
class Varying:
    var: Ref
    start: Expr
    by: Expr
    until: Cond


@dataclass
class Perform(Stmt):
    target: str | None = None  # paragraph/section name (out-of-line)
    thru: str | None = None
    times: Expr | None = None
    until: Cond | None = None
    test_after: bool = False
    varying: list[Varying] = field(default_factory=list)
    body: list[Stmt] | None = None  # inline perform
    kind: str = "PERFORM"


@dataclass
class CallArg:
    expr: Expr
    mode: str = "REFERENCE"  # REFERENCE | CONTENT | VALUE


@dataclass
class Call(Stmt):
    program: Expr = None  # type: ignore[assignment]
    using: list[CallArg] = field(default_factory=list)
    returning: Ref | None = None
    on_exception: list[Stmt] | None = None
    not_on_exception: list[Stmt] | None = None
    kind: str = "CALL"


@dataclass
class StopRun(Stmt):
    kind: str = "STOP_RUN"


@dataclass
class Goback(Stmt):
    kind: str = "GOBACK"


@dataclass
class Exit(Stmt):
    what: str = ""  # "" (no-op EXIT) | PARAGRAPH | SECTION | PROGRAM | PERFORM | PERFORM CYCLE
    kind: str = "EXIT"


@dataclass
class GoTo(Stmt):
    target: str = ""
    kind: str = "GOTO"


@dataclass
class Continue(Stmt):
    kind: str = "CONTINUE"


@dataclass
class Display(Stmt):
    operands: list[Expr] = field(default_factory=list)
    no_advancing: bool = False
    upon: str | None = None
    kind: str = "DISPLAY"


@dataclass
class Accept(Stmt):
    target: Ref = None  # type: ignore[assignment]
    source: str = ""  # "" (stdin) | DATE | DATE YYYYMMDD | DAY | DAY YYYYDDD | TIME | DAY-OF-WEEK
    kind: str = "ACCEPT"


@dataclass
class Initialize(Stmt):
    targets: list[Ref] = field(default_factory=list)
    kind: str = "INITIALIZE"


@dataclass
class SetStmt(Stmt):
    mode: str = ""  # TRUE | TO | UP | DOWN
    targets: list[Ref] = field(default_factory=list)
    value: Expr | None = None
    kind: str = "SET"


@dataclass
class StringPart:
    expr: Expr
    delimiter: Expr | None  # None = SIZE


@dataclass
class StringStmt(Stmt):
    parts: list[StringPart] = field(default_factory=list)
    into: Ref = None  # type: ignore[assignment]
    pointer: Ref | None = None
    on_overflow: list[Stmt] | None = None
    not_on_overflow: list[Stmt] | None = None
    kind: str = "STRING"


@dataclass
class Inspect(Stmt):
    """INSPECT in the supported subset (one clause, ALL <literal>, no BEFORE/AFTER).

    mode TALLYING: ``counter`` is incremented by the number of non-overlapping
    occurrences of ``pattern`` in ``target`` (scanned left to right).
    mode REPLACING: every non-overlapping occurrence of ``pattern`` is replaced
    by ``replacement`` (same length; a figurative replacement is repeated to the
    pattern length).
    """

    mode: str = ""  # TALLYING | REPLACING
    target: Ref = None  # type: ignore[assignment]
    pattern: Literal = None  # type: ignore[assignment]
    counter: Ref | None = None
    replacement: Literal | None = None
    kind: str = "INSPECT"


@dataclass
class Unsupported(Stmt):
    verb: str = ""
    reason: str = ""
    category: str = ""  # file-io | sql | cics | statement | clause
    text: str = ""
    kind: str = "UNSUPPORTED"


# ---------------------------------------------------------------- structure
@dataclass
class Paragraph:
    name: str
    section: str | None
    loc: Loc
    statements: list[Stmt] = field(default_factory=list)
    comments: list[tuple[int, str]] = field(default_factory=list)


@dataclass
class Section:
    name: str
    loc: Loc
    paragraphs: list[str] = field(default_factory=list)


@dataclass
class Program:
    program_id: str
    file: str
    loc: Loc
    source_format: str = "fixed"
    is_initial: bool = False
    data: list[DataItem] = field(default_factory=list)  # 01/77/78 roots in declaration order
    files: list[FileControl] = field(default_factory=list)
    using: list[str] = field(default_factory=list)  # data item ids
    returning: str | None = None
    paragraphs: list[Paragraph] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    copybooks: list[dict[str, Any]] = field(default_factory=list)
    special_names: dict[str, str] = field(default_factory=dict)

    # convenience indexes (not serialised)
    def iter_items(self):
        stack = list(reversed(self.data))
        while stack:
            it = stack.pop()
            yield it
            stack.extend(reversed(it.children))

    def item_index(self) -> dict[str, DataItem]:
        return {it.id: it for it in self.iter_items()}


def walk_statements(stmts: list[Stmt]):
    """Yield every statement, recursing into nested blocks."""
    for s in stmts:
        yield s
        if isinstance(s, If):
            yield from walk_statements(s.then)
            yield from walk_statements(s.orelse)
        elif isinstance(s, Evaluate):
            for w in s.whens:
                yield from walk_statements(w.body)
        elif isinstance(s, Perform) and s.body:
            yield from walk_statements(s.body)
        elif isinstance(s, Compute | Arith):
            yield from walk_statements(s.on_size_error or [])
            yield from walk_statements(s.not_on_size_error or [])
        elif isinstance(s, Call):
            yield from walk_statements(s.on_exception or [])
            yield from walk_statements(s.not_on_exception or [])
        elif isinstance(s, StringStmt):
            yield from walk_statements(s.on_overflow or [])
            yield from walk_statements(s.not_on_overflow or [])


def to_jsonable(obj: Any) -> Any:
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        d = {"_t": type(obj).__name__}
        for f in dataclasses.fields(obj):
            d[f.name] = to_jsonable(getattr(obj, f.name))
        return d
    if isinstance(obj, list | tuple):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return str(obj)
    return obj
