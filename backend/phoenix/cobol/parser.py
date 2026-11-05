"""Recursive-descent parser: tokens -> IR.

Statements outside the supported subset become :class:`Unsupported` nodes with
their source range; nothing is silently dropped.
"""

from __future__ import annotations

from collections.abc import Callable

from . import ir
from .diagnostics import Diagnostic, Severity
from .lexer import TK, Token
from .picture import PictureError, parse_picture, storage_size

FIGURATIVES = {
    "ZERO": "ZERO", "ZEROS": "ZERO", "ZEROES": "ZERO",
    "SPACE": "SPACE", "SPACES": "SPACE",
    "HIGH-VALUE": "HIGH-VALUE", "HIGH-VALUES": "HIGH-VALUE",
    "LOW-VALUE": "LOW-VALUE", "LOW-VALUES": "LOW-VALUE",
    "QUOTE": "QUOTE", "QUOTES": "QUOTE",
    "NULL": "LOW-VALUE", "NULLS": "LOW-VALUE",
}  # fmt: skip

SUPPORTED_VERBS = {
    "MOVE", "COMPUTE", "ADD", "SUBTRACT", "MULTIPLY", "DIVIDE", "IF", "EVALUATE", "PERFORM",
    "CALL", "STOP", "GOBACK", "EXIT", "CONTINUE", "DISPLAY", "ACCEPT", "INITIALIZE", "SET",
    "STRING", "GO",
}  # fmt: skip

KNOWN_UNSUPPORTED = {
    "OPEN": "file-io", "CLOSE": "file-io", "READ": "file-io", "WRITE": "file-io",
    "REWRITE": "file-io", "DELETE": "file-io", "START": "file-io", "SORT": "file-io",
    "MERGE": "file-io", "RELEASE": "file-io", "RETURN": "file-io", "UNLOCK": "file-io",
    "INSPECT": "statement", "UNSTRING": "statement", "SEARCH": "statement",
    "EXEC": "embedded", "ALTER": "statement", "CANCEL": "statement", "ENTRY": "statement",
    "GENERATE": "report-writer", "INITIATE": "report-writer", "TERMINATE": "report-writer",
    "USE": "declaratives", "INVOKE": "oo", "ALLOCATE": "statement", "FREE": "statement",
    "RAISE": "statement", "RESUME": "statement", "TRANSFORM": "statement", "COMMIT": "statement",
    "ROLLBACK": "statement", "XML": "statement", "JSON": "statement", "SUPPRESS": "statement",
    "VALIDATE": "statement",
}  # fmt: skip

ALL_VERBS = SUPPORTED_VERBS | set(KNOWN_UNSUPPORTED)

SCOPE_TERMINATORS = {
    "END-IF", "END-EVALUATE", "END-PERFORM", "END-COMPUTE", "END-ADD", "END-SUBTRACT",
    "END-MULTIPLY", "END-DIVIDE", "END-CALL", "END-STRING", "END-DISPLAY", "END-ACCEPT",
    "END-READ", "END-WRITE", "END-REWRITE", "END-DELETE", "END-START", "END-SEARCH",
    "END-UNSTRING", "END-RETURN", "END-EXEC",
}  # fmt: skip

STOP_WORDS = ALL_VERBS | SCOPE_TERMINATORS | {"ELSE", "WHEN", "NOT", "ON", "SIZE", "AT", "INVALID", "OVERFLOW", "EXCEPTION", "THEN"}

RELOP_WORDS = {"EQUAL", "EQUALS", "GREATER", "LESS"}
CLASS_WORDS = {"NUMERIC", "ALPHABETIC", "ALPHABETIC-LOWER", "ALPHABETIC-UPPER", "POSITIVE", "NEGATIVE", "ZERO", "ZEROS", "ZEROES"}

SUPPORTED_FUNCTIONS = {
    "INTEGER-OF-DATE", "DATE-OF-INTEGER", "TRIM", "UPPER-CASE", "LOWER-CASE", "LENGTH",
    "MAX", "MIN", "ABS", "MOD", "REM", "INTEGER", "INTEGER-PART", "NUMVAL", "CURRENT-DATE",
    "SUM", "REVERSE", "ORD", "CHAR", "SQRT", "RANDOM", "WHEN-COMPILED", "DAY-OF-INTEGER",
    "INTEGER-OF-DAY", "MEAN", "NUMVAL-C", "TEST-NUMVAL", "CONCATENATE", "SIGN", "FACTORIAL",
}  # fmt: skip


class ParseError(Exception):
    def __init__(self, msg: str, tok: Token | None) -> None:
        super().__init__(msg)
        self.tok = tok


class NotSupported(ParseError):
    """A recognised construct that is outside the supported subset."""


class Parser:
    def __init__(self, tokens: list[Token], main_file: str) -> None:
        self.toks = tokens
        self.i = 0
        self.main_file = main_file
        self.diagnostics: list[Diagnostic] = []
        self.unsupported: list[dict] = []
        self.program: ir.Program | None = None
        self.items_by_name: dict[str, list[ir.DataItem]] = {}
        self.conds_by_name: dict[str, list[tuple[ir.ConditionName, ir.DataItem]]] = {}
        self.paragraph_names: set[str] = set()
        self.section_names: set[str] = set()

    # ------------------------------------------------------------ helpers
    def peek(self, k: int = 0) -> Token | None:
        j = self.i + k
        return self.toks[j] if j < len(self.toks) else None

    def at_end(self) -> bool:
        return self.i >= len(self.toks)

    def next(self) -> Token:
        if self.i >= len(self.toks):
            raise ParseError("unexpected end of source", self.toks[-1] if self.toks else None)
        t = self.toks[self.i]
        self.i += 1
        return t

    def at_word(self, *words: str) -> bool:
        t = self.peek()
        return t is not None and t.is_word(*words)

    def accept_word(self, *words: str) -> Token | None:
        if self.at_word(*words):
            return self.next()
        return None

    def expect_word(self, *words: str) -> Token:
        t = self.peek()
        if t is None or not t.is_word(*words):
            raise ParseError(f"expected {'/'.join(words)}, found {t.value if t else 'end of file'!r}", t)
        return self.next()

    def at_kind(self, kind: TK) -> bool:
        t = self.peek()
        return t is not None and t.kind == kind

    def accept_period(self) -> bool:
        if self.at_kind(TK.PERIOD):
            self.i += 1
            return True
        return False

    def loc(self, start: Token, end: Token | None = None) -> ir.Loc:
        end = end or start
        if end.file != start.file:
            end = start
        return ir.Loc(start.file, start.line, max(start.line, end.line))

    def last_tok(self) -> Token:
        return self.toks[max(0, self.i - 1)]

    def diag(self, sev: Severity, code: str, msg: str, tok: Token | None) -> None:
        f = tok.file if tok else self.main_file
        ln = tok.line if tok else 0
        self.diagnostics.append(Diagnostic(sev, code, msg, f, ln))

    def record_unsupported(self, construct: str, category: str, reason: str, loc: ir.Loc, text: str = "") -> None:
        self.unsupported.append(
            {"construct": construct, "category": category, "reason": reason, "file": loc.file, "line": loc.line, "end_line": loc.end_line, "text": text[:200]}
        )

    def skip_to_period(self) -> None:
        while not self.at_end() and not self.at_kind(TK.PERIOD):
            self.i += 1
        self.accept_period()

    def at_division(self) -> str | None:
        t, t2 = self.peek(), self.peek(1)
        if t and t2 and t2.is_word("DIVISION") and t.kind == TK.WORD:
            return t.value.upper()
        if t and t.is_word("END") and t2 and t2.is_word("PROGRAM"):
            return "END"
        return None

    # ------------------------------------------------------------ programs
    def parse_programs(self) -> list[ir.Program]:
        programs: list[ir.Program] = []
        while not self.at_end():
            d = self.at_division()
            if d in ("IDENTIFICATION", "ID"):
                self.items_by_name = {}
                self.conds_by_name = {}
                self.paragraph_names = set()
                self.section_names = set()
                try:
                    programs.append(self.parse_program())
                except ParseError as e:
                    self.diag(Severity.ERROR, "PAR001", str(e), e.tok)
                    # recover: skip to next IDENTIFICATION DIVISION
                    self.i += 1
                    while not self.at_end() and self.at_division() not in ("IDENTIFICATION", "ID"):
                        self.i += 1
            else:
                t = self.next()
                if not programs:
                    self.diag(Severity.ERROR, "PAR002", f"unexpected token {t.value!r} before IDENTIFICATION DIVISION", t)
                    while not self.at_end() and self.at_division() not in ("IDENTIFICATION", "ID"):
                        self.i += 1
        return programs

    def parse_program(self) -> ir.Program:
        start = self.next()
        self.expect_word("DIVISION")
        self.accept_period()
        self.expect_word("PROGRAM-ID")
        self.accept_period()
        name_tok = self.next()
        prog = ir.Program(program_id=name_tok.value.upper(), file=start.file, loc=self.loc(start))
        self.program = prog
        while not self.at_end() and not self.at_kind(TK.PERIOD) and self.at_division() is None:
            t = self.next()
            if t.is_word("INITIAL"):
                prog.is_initial = True
        self.accept_period()
        # skip remaining identification paragraphs (comment entries)
        while not self.at_end() and self.at_division() is None:
            self.i += 1
        if self.at_division() == "ENVIRONMENT":
            self.parse_environment(prog)
        if self.at_division() == "DATA":
            self.parse_data_division(prog)
        if self.at_division() == "PROCEDURE":
            self.parse_procedure_division(prog)
        end = self.last_tok()
        if self.at_division() == "END":
            self.i += 2
            if not self.at_kind(TK.PERIOD):
                self.i += 1
            self.accept_period()
            end = self.last_tok()
        prog.loc = ir.Loc(start.file, start.line, end.line if end.file == start.file else start.line)
        self.resolve_program(prog)
        return prog

    # ------------------------------------------------------------ environment
    def parse_environment(self, prog: ir.Program) -> None:
        self.i += 2
        self.accept_period()
        while not self.at_end() and self.at_division() not in ("DATA", "PROCEDURE", "END", "IDENTIFICATION", "ID"):
            t = self.peek()
            if t.is_word("SELECT"):
                self.parse_select(prog)
                continue
            if t.is_word("DECIMAL-POINT"):
                prog.special_names["DECIMAL-POINT"] = "COMMA"
                self.record_unsupported("DECIMAL-POINT IS COMMA", "clause", "comma decimal point is not supported by the generator", self.loc(t))
            if t.is_word("CURRENCY"):
                self.record_unsupported("CURRENCY SIGN", "clause", "custom currency sign is not supported", self.loc(t))
            self.i += 1

    def parse_select(self, prog: ir.Program) -> None:
        start = self.next()
        self.accept_word("OPTIONAL")
        name = self.next().value.upper()
        assign = organization = access = ""
        status = None
        while not self.at_end() and not self.at_kind(TK.PERIOD):
            t = self.next()
            if t.is_word("ASSIGN"):
                self.accept_word("TO")
                a = self.next()
                if a.is_word("DISK", "EXTERNAL", "DYNAMIC") and not self.at_kind(TK.PERIOD):
                    a = self.next()
                assign = a.value
            elif t.is_word("ORGANIZATION"):
                self.accept_word("IS")
                o = self.next().value.upper()
                if o == "LINE" and self.at_word("SEQUENTIAL"):
                    self.next()
                    o = "LINE SEQUENTIAL"
                organization = o
            elif t.is_word("ACCESS"):
                self.accept_word("MODE")
                self.accept_word("IS")
                access = self.next().value.upper()
            elif t.is_word("STATUS"):
                self.accept_word("IS")
                status = self.next().value.upper()
            elif t.is_word("LINE") and self.at_word("SEQUENTIAL"):
                self.next()
                organization = "LINE SEQUENTIAL"
        end = self.last_tok()
        self.accept_period()
        prog.files.append(ir.FileControl(name, assign, organization or "SEQUENTIAL", access or "SEQUENTIAL", status, self.loc(start, end)))

    # ------------------------------------------------------------ data division
    def parse_data_division(self, prog: ir.Program) -> None:
        self.i += 2
        self.accept_period()
        section = "WORKING-STORAGE"
        current_fd: ir.FileControl | None = None
        stack: list[ir.DataItem] = []
        while not self.at_end() and self.at_division() not in ("PROCEDURE", "END", "IDENTIFICATION", "ID"):
            t = self.peek()
            t2 = self.peek(1)
            if t.kind == TK.WORD and t2 is not None and t2.is_word("SECTION"):
                section = t.value.upper()
                self.i += 2
                self.accept_period()
                stack = []
                if section in ("SCREEN", "REPORT", "COMMUNICATION"):
                    self.record_unsupported(f"{section} SECTION", "section", f"{section} SECTION is not supported", self.loc(t))
                    while not self.at_end() and self.at_division() is None and not (self.peek(1) and self.peek(1).is_word("SECTION")):
                        self.i += 1
                continue
            if t.is_word("FD", "SD", "RD"):
                start = self.next()
                fname = self.next().value.upper()
                current_fd = next((f for f in prog.files if f.name == fname), None)
                self.skip_to_period()
                stack = []
                if start.is_word("SD", "RD"):
                    self.record_unsupported(start.value.upper(), "file-io", "sort/report file descriptions are not supported", self.loc(start))
                continue
            if t.kind == TK.NUMBER:
                item = self.parse_data_entry(section)
                if item is None:
                    continue
                if item.level == 88:
                    continue  # attached inside parse_data_entry
                if item.level in (1, 77, 78) or not stack:
                    if item.level not in (1, 77, 78):
                        self.diag(Severity.WARNING, "DAT001", f"level {item.level} item {item.name} without 01 parent", t)
                    prog.data.append(item)
                    stack = [item]
                    if current_fd and section == "FILE" and current_fd.record is None:
                        current_fd.record = item.name
                    continue
                while stack and stack[-1].level >= item.level:
                    stack.pop()
                if not stack:
                    prog.data.append(item)
                    stack = [item]
                    continue
                parent = stack[-1]
                parent.children.append(item)
                item.parent = parent.id
                stack.append(item)
                continue
            self.diag(Severity.WARNING, "DAT002", f"unexpected token {t.value!r} in DATA DIVISION", t)
            self.i += 1

        # USAGE on a group applies to its elementary subordinates
        def propagate(node: ir.DataItem, usage: str | None) -> None:
            if node.children:
                u = node.usage if node.usage != "DISPLAY" else usage
                for ch in node.children:
                    propagate(ch, u)
                node.usage = "DISPLAY"
            elif usage and node.usage == "DISPLAY" and node.picture is not None and node.picture.category == "numeric":
                node.usage = usage

        for root in prog.data:
            propagate(root, None)
        # layout + ids
        for root in prog.data:
            self._assign_ids(root, None)
            self._layout(root, 0, root.id, [])
            self._assign_dims(root, [])
        # INDEXED BY names become implicit binary integer items
        declared = {it.name for it in prog.iter_items()}
        for it in list(prog.iter_items()):
            for idx in it.indexed_by:
                if idx in declared:
                    continue
                declared.add(idx)
                pic = parse_picture("S9(9)")
                synth = ir.DataItem(id=idx, level=77, name=idx, loc=it.loc, section="WORKING-STORAGE", picture=pic, usage="COMP-5")
                synth.size = storage_size(pic, "COMP-5", False)
                synth.record = idx
                prog.data.append(synth)
        for it in prog.iter_items():
            self.items_by_name.setdefault(it.name, []).append(it)
            for c in it.conditions:
                c.parent = it.id
                self.conds_by_name.setdefault(c.name, []).append((c, it))

    def _assign_ids(self, item: ir.DataItem, parent: ir.DataItem | None) -> None:
        base = item.name if not item.is_filler else f"FILLER@{item.loc.line}"
        item.id = f"{parent.id}.{base}" if parent else base
        item.parent = parent.id if parent else None
        for c in item.children:
            self._assign_ids(c, item)

    def _layout(self, item: ir.DataItem, offset: int, record: str, dims: list[tuple[int, int]]) -> int:
        """Compute offset/size; returns size of one occurrence."""
        item.offset = offset
        item.record = record
        if item.children:
            cur = offset
            max_end = offset
            siblings: dict[str, ir.DataItem] = {}
            for c in item.children:
                if c.redefines:
                    target = siblings.get(c.redefines)
                    if target is None:
                        self.diag(Severity.ERROR, "DAT003", f"REDEFINES target {c.redefines} not found", None)
                        start = cur
                    else:
                        start = target.offset
                    sz = self._layout_child(c, start, record, dims)
                    max_end = max(max_end, start + sz * max(1, c.occurs))
                    continue
                sz = self._layout_child(c, cur, record, dims)
                cur += sz * max(1, c.occurs)
                max_end = max(max_end, cur)
                siblings[c.name] = c
            item.size = max_end - offset
        else:
            item.size = storage_size(item.picture, item.usage, item.sign_separate)
        return item.size

    def _layout_child(self, c: ir.DataItem, start: int, record: str, dims: list[tuple[int, int]]) -> int:
        return self._layout(c, start, record, dims)

    def _assign_dims(self, item: ir.DataItem, dims: list[tuple[int, int]]) -> None:
        item.dims = dims + ([(item.size, item.occurs)] if item.occurs else [])
        for ch in item.children:
            self._assign_dims(ch, item.dims)

    def parse_data_entry(self, section: str) -> ir.DataItem | None:
        start = self.next()
        try:
            level = int(start.value)
        except ValueError:
            self.skip_to_period()
            return None
        name = "FILLER"
        is_filler = True
        t = self.peek()
        if t and t.kind == TK.WORD and t.value.upper() not in (
            "PIC", "PICTURE", "VALUE", "VALUES", "OCCURS", "REDEFINES", "USAGE", "COMP", "COMP-3",
            "BINARY", "PACKED-DECIMAL", "SIGN", "JUSTIFIED", "JUST", "BLANK", "SYNC", "SYNCHRONIZED",
            "COMPUTATIONAL", "COMPUTATIONAL-3", "DISPLAY", "EXTERNAL", "GLOBAL", "INDEX",
        ):  # fmt: skip
            nt = self.next()
            if not nt.is_word("FILLER"):
                name = nt.value.upper()
                is_filler = False
        item = ir.DataItem(id="", level=level, name=name, loc=self.loc(start), section=section, is_filler=is_filler)
        if level == 66:
            self.record_unsupported("RENAMES (level 66)", "clause", "level-66 RENAMES is not supported", self.loc(start))
            self.skip_to_period()
            return None
        if level == 88:
            cond = self.parse_condition_values(name, start)
            parent = self._last_item_for_88()
            if parent is not None:
                parent.conditions.append(cond)
            else:
                self.diag(Severity.WARNING, "DAT004", f"88-level {name} without parent", start)
            return ir.DataItem(id="", level=88, name=name, loc=item.loc, section=section)
        if level == 78:
            item.is_constant = True
        while not self.at_end() and not self.at_kind(TK.PERIOD):
            t = self.next()
            u = t.value.upper() if t.kind == TK.WORD else ""
            if u in ("PIC", "PICTURE"):
                self.accept_word("IS")
                pt = self.next()
                try:
                    item.picture = parse_picture(pt.value)
                    if item.picture.p_scaling:
                        self.record_unsupported("PICTURE P scaling", "clause", "P scaling positions are not supported by the generator", self.loc(pt))
                except PictureError as e:
                    self.diag(Severity.ERROR, "DAT005", str(e), pt)
            elif u in ("VALUE", "VALUES"):
                self.accept_word("IS", "ARE")
                item.value = self.parse_literal_or_figurative()
            elif u == "OCCURS":
                n1 = self.next()
                item.occurs = int(n1.value) if n1.kind == TK.NUMBER else 1
                if self.accept_word("TO"):
                    n2 = self.next()
                    item.occurs_min = item.occurs
                    item.occurs = int(n2.value)
                self.accept_word("TIMES")
                while not self.at_end() and not self.at_kind(TK.PERIOD):
                    if self.accept_word("DEPENDING"):
                        self.accept_word("ON")
                        item.occurs_depending = self.next().value.upper()
                        self.record_unsupported("OCCURS DEPENDING ON", "clause", "variable-length tables are treated as fixed maximum size", self.loc(t))
                    elif self.at_word("ASCENDING", "DESCENDING"):
                        self.next()
                        self.accept_word("KEY")
                        self.accept_word("IS")
                        while (
                            self.peek()
                            and self.peek().kind == TK.WORD
                            and not self.at_word("INDEXED", "ASCENDING", "DESCENDING", "PIC", "PICTURE", "VALUE", "USAGE", "COMP", "COMP-3")
                        ):
                            self.next()
                    elif self.accept_word("INDEXED"):
                        self.accept_word("BY")
                        while (
                            self.peek()
                            and self.peek().kind == TK.WORD
                            and not self.at_word("PIC", "PICTURE", "VALUE", "USAGE", "ASCENDING", "DESCENDING", "COMP", "COMP-3")
                        ):
                            item.indexed_by.append(self.next().value.upper())
                    else:
                        break
            elif u == "REDEFINES":
                item.redefines = self.next().value.upper()
            elif u == "USAGE":
                self.accept_word("IS")
                item.usage = self._usage(self.next())
            elif u in (
                "COMP", "COMP-3", "COMP-4", "COMP-5", "BINARY", "PACKED-DECIMAL", "COMPUTATIONAL",
                "COMPUTATIONAL-3", "COMPUTATIONAL-4", "COMPUTATIONAL-5", "DISPLAY", "INDEX", "POINTER",
                "COMP-1", "COMP-2", "COMPUTATIONAL-1", "COMPUTATIONAL-2", "COMP-X", "COMP-N",
            ):  # fmt: skip
                item.usage = self._usage(t)
            elif u == "SIGN":
                self.accept_word("IS")
                lt = self.next()
                item.sign_leading = lt.is_word("LEADING")
                if self.accept_word("SEPARATE"):
                    item.sign_separate = True
                    self.accept_word("CHARACTER")
            elif u in ("LEADING", "TRAILING"):
                item.sign_leading = u == "LEADING"
                if self.accept_word("SEPARATE"):
                    item.sign_separate = True
                    self.accept_word("CHARACTER")
            elif u in ("JUSTIFIED", "JUST"):
                item.justified = True
                self.accept_word("RIGHT")
            elif u == "BLANK":
                self.accept_word("WHEN")
                self.next()
                item.blank_when_zero = True
            elif u in ("SYNC", "SYNCHRONIZED"):
                self.accept_word("LEFT", "RIGHT")
            elif u in ("EXTERNAL", "GLOBAL"):
                item.external = u == "EXTERNAL"
            elif u == "IS":
                continue
            else:
                self.diag(Severity.WARNING, "DAT006", f"unrecognised data clause {t.value!r} on {name}", t)
        end = self.last_tok()
        self.accept_period()
        item.loc = self.loc(start, end)
        if item.usage in ("COMP-1", "COMP-2"):
            self.record_unsupported(f"USAGE {item.usage}", "clause", "floating point usage is not supported (Decimal only)", item.loc)
        if item.usage == "POINTER":
            self.record_unsupported("USAGE POINTER", "clause", "pointers are not supported", item.loc)
        return item

    def _last_item_for_88(self) -> ir.DataItem | None:
        prog = self.program
        if not prog or not prog.data:
            return None
        node = prog.data[-1]
        while node.children:
            node = node.children[-1]
        return node

    @staticmethod
    def _usage(t: Token) -> str:
        u = t.value.upper()
        return {
            "COMPUTATIONAL": "COMP", "BINARY": "COMP", "COMP-4": "COMP", "COMPUTATIONAL-4": "COMP",
            "COMPUTATIONAL-3": "COMP-3", "PACKED-DECIMAL": "COMP-3", "COMPUTATIONAL-5": "COMP-5",
            "COMPUTATIONAL-1": "COMP-1", "COMPUTATIONAL-2": "COMP-2", "COMP-X": "COMP-5", "COMP-N": "COMP-5",
        }.get(u, u)  # fmt: skip

    def parse_condition_values(self, name: str, start: Token) -> ir.ConditionName:
        values: list[ir.ConditionValue] = []
        if self.accept_word("VALUE", "VALUES"):
            self.accept_word("IS", "ARE")
        while not self.at_end() and not self.at_kind(TK.PERIOD):
            if self.at_word("WHEN"):  # WHEN SET TO FALSE
                self.skip_to_period()
                self.i -= 1
                break
            lo = self.parse_literal_or_figurative()
            hi = None
            if self.accept_word("THRU", "THROUGH"):
                hi = self.parse_literal_or_figurative()
            values.append(ir.ConditionValue(lo, hi))
        end = self.last_tok()
        self.accept_period()
        return ir.ConditionName(name=name, values=values, loc=self.loc(start, end))

    def parse_literal_or_figurative(self) -> ir.Literal:
        t = self.next()
        all_ = False
        if t.is_word("ALL"):
            all_ = True
            t = self.next()
        if t.kind == TK.NUMBER:
            return ir.Literal("number", t.value.lstrip("+") if t.value.startswith("+") else t.value, loc=self.loc(t))
        if t.kind == TK.STRING:
            return ir.Literal("string", t.value, all=all_, loc=self.loc(t))
        if t.kind == TK.WORD and t.value.upper() in FIGURATIVES:
            return ir.Literal("figurative", FIGURATIVES[t.value.upper()], all=all_, loc=self.loc(t))
        self.diag(Severity.WARNING, "DAT007", f"unsupported literal {t.value!r}", t)
        return ir.Literal("string", t.value, loc=self.loc(t))

    # ------------------------------------------------------------ procedure division
    def parse_procedure_division(self, prog: ir.Program) -> None:
        self.i += 2
        if self.accept_word("USING"):
            while not self.at_end() and not self.at_kind(TK.PERIOD) and not self.at_word("RETURNING"):
                t = self.next()
                if t.is_word("BY", "REFERENCE", "VALUE", "CONTENT"):
                    if t.is_word("VALUE"):
                        self.record_unsupported("USING BY VALUE", "clause", "BY VALUE parameters are treated BY REFERENCE", self.loc(t))
                    continue
                prog.using.append(t.value.upper())
        if self.accept_word("RETURNING"):
            prog.returning = self.next().value.upper()
        self.accept_period()
        self._prescan_names()
        current_section: str | None = None
        current: ir.Paragraph | None = None
        if self.at_word("DECLARATIVES"):
            st = self.peek()
            while not self.at_end() and not (self.at_word("END") and self.peek(1) and self.peek(1).is_word("DECLARATIVES")):
                self.i += 1
            self.i += 2
            self.accept_period()
            self.record_unsupported("DECLARATIVES", "declaratives", "DECLARATIVES are not supported", self.loc(st, self.last_tok()))
        while not self.at_end() and self.at_division() is None:
            t = self.peek()
            t2 = self.peek(1)
            if t.kind in (TK.WORD, TK.NUMBER) and t2 is not None and t2.is_word("SECTION") and self.peek(2) and self.peek(2).kind == TK.PERIOD:
                current_section = t.value.upper()
                prog.sections.append(ir.Section(current_section, self.loc(t)))
                self.i += 3
                current = None
                continue
            if t.kind in (TK.WORD, TK.NUMBER) and t2 is not None and t2.kind == TK.PERIOD and t.value.upper() not in ALL_VERBS:
                current = ir.Paragraph(t.value.upper(), current_section, self.loc(t))
                prog.paragraphs.append(current)
                if current_section:
                    prog.sections[-1].paragraphs.append(current.name)
                self.i += 2
                continue
            if t.kind == TK.PERIOD:
                self.i += 1
                continue
            if current is None:
                # statements before first paragraph: implicit unnamed paragraph
                name = f"{current_section}-ENTRY" if current_section else "PHOENIX-MAIN-ENTRY"
                current = ir.Paragraph(name, current_section, self.loc(t))
                prog.paragraphs.append(current)
                if current_section:
                    prog.sections[-1].paragraphs.append(name)
            stmts = self.parse_sentence()
            current.statements.extend(stmts)
            current.loc = current.loc.span(self.loc(self.last_tok()))
        for sec in prog.sections:
            paras = [p for p in prog.paragraphs if p.section == sec.name]
            if paras:
                sec.loc = sec.loc.span(paras[-1].loc)

    def _prescan_names(self) -> None:
        j = self.i
        prev_period = True
        toks = self.toks
        while j < len(toks):
            t = toks[j]
            if t.is_word("DIVISION") or (t.is_word("END") and j + 1 < len(toks) and toks[j + 1].is_word("PROGRAM")):
                break
            if prev_period and t.kind in (TK.WORD, TK.NUMBER) and j + 1 < len(toks):
                n1 = toks[j + 1]
                if n1.kind == TK.PERIOD and t.value.upper() not in ALL_VERBS:
                    self.paragraph_names.add(t.value.upper())
                elif n1.is_word("SECTION"):
                    self.section_names.add(t.value.upper())
            prev_period = t.kind == TK.PERIOD
            j += 1

    def parse_sentence(self) -> list[ir.Stmt]:
        stmts = self.parse_statements(stop=set())
        if not self.accept_period():
            t = self.peek()
            if t is not None and self.at_division() is None:
                self.diag(Severity.WARNING, "PRC001", f"unexpected {t.value!r}; skipping to end of sentence", t)
                start = t
                self.skip_to_period()
                loc = self.loc(start, self.last_tok())
                stmts.append(ir.Unsupported(loc=loc, verb=start.value.upper(), reason="unparseable statement", category="statement"))
                self.record_unsupported(start.value.upper(), "statement", "unparseable statement", loc)
        return stmts

    def parse_statements(self, stop: set[str]) -> list[ir.Stmt]:
        out: list[ir.Stmt] = []
        while not self.at_end():
            t = self.peek()
            if t.kind == TK.PERIOD:
                break
            if t.kind == TK.WORD and t.value.upper() in stop:
                break
            if t.kind == TK.WORD and t.value.upper() in SCOPE_TERMINATORS | {"ELSE", "WHEN"}:
                break
            if t.kind == TK.WORD and (t.is_word("NOT") or t.is_word("ON", "AT", "INVALID", "SIZE", "OVERFLOW", "EXCEPTION")):
                break
            if self.at_division() is not None:
                break
            if t.kind != TK.WORD or t.value.upper() not in ALL_VERBS:
                if t.kind in (TK.WORD, TK.NUMBER) and self.peek(1) and self.peek(1).kind == TK.PERIOD and t.value.upper() in self.paragraph_names:
                    break  # missing period before paragraph
                self.diag(Severity.WARNING, "PRC002", f"unexpected token {t.value!r} in statement position", t)
                self.i += 1
                continue
            out.append(self.parse_statement())
        return out

    def parse_statement(self) -> ir.Stmt:
        t = self.peek()
        verb = t.value.upper()
        handler: Callable[[], ir.Stmt] | None = getattr(self, f"st_{verb.replace('-', '_').lower()}", None)
        if handler is None:
            return self.st_unsupported(KNOWN_UNSUPPORTED.get(verb, "statement"))
        save = self.i
        try:
            return handler()
        except NotSupported as e:
            self.i = save
            return self.st_unsupported("statement", reason=str(e))
        except ParseError as e:
            self.i = save
            self.diag(Severity.ERROR, "PRC003", f"cannot parse {verb}: {e}", e.tok or t)
            return self.st_unsupported("statement", reason=f"parse error: {e}")

    def st_unsupported(self, category: str, reason: str | None = None) -> ir.Stmt:
        start = self.next()
        verb = start.value.upper()
        if verb == "EXEC":
            parts = [start.value]
            while not self.at_end() and not self.at_word("END-EXEC"):
                parts.append(self.next().value)
            self.accept_word("END-EXEC")
            loc = self.loc(start, self.last_tok())
            kind = parts[1].upper() if len(parts) > 1 else "EXEC"
            reason = reason or f"embedded EXEC {kind} is not supported"
            self.record_unsupported(f"EXEC {kind}", "embedded", reason, loc, " ".join(parts))
            return ir.Unsupported(loc=loc, verb=f"EXEC {kind}", reason=reason, category="embedded", text=" ".join(parts))
        parts = [start.value]
        end_tok = f"END-{verb}"
        # 1) explicit scope terminator before the end of the sentence?
        j, depth, found = self.i, 0, -1
        while j < len(self.toks) and self.toks[j].kind != TK.PERIOD:
            tj = self.toks[j]
            if tj.is_word(verb):
                depth += 1
            elif tj.is_word(end_tok):
                if depth == 0:
                    found = j
                    break
                depth -= 1
            j += 1
        if found >= 0:
            while self.i <= found:
                parts.append(self.next().value)
        else:
            phrase = False
            while not self.at_end():
                t = self.peek()
                if t.kind == TK.PERIOD:
                    break
                if t.kind == TK.WORD:
                    u = t.value.upper()
                    if u in ("AT", "INVALID", "OVERFLOW", "EXCEPTION") or (u == "END" and verb in ("READ", "RETURN", "SEARCH")):
                        phrase = True
                    if u in ALL_VERBS and not phrase and u != verb:
                        break
                    if u in SCOPE_TERMINATORS or u in ("ELSE", "WHEN"):
                        break
                parts.append(self.next().value)
        loc = self.loc(start, self.last_tok())
        reason = reason or f"{verb} is not supported by the generator"
        self.record_unsupported(verb, category, reason, loc, " ".join(parts))
        return ir.Unsupported(loc=loc, verb=verb, reason=reason, category=category, text=" ".join(parts))

    @staticmethod
    def _inside_unsupported_phrase(parts: list[str]) -> bool:
        # e.g. "READ F AT END MOVE ..." - stop at the nested verb anyway; nested
        # imperative statements are reported with the unsupported parent.
        return False

    # ---------------- operands
    def parse_identifier(self) -> ir.Ref:
        t = self.next()
        if t.kind != TK.WORD:
            raise ParseError(f"expected identifier, found {t.value!r}", t)
        u = t.value.upper()
        if u == "LENGTH" and self.at_word("OF"):
            self.next()
            inner = self.parse_identifier()
            return ir.Ref(name=inner.name, qualifiers=inner.qualifiers, subscripts=inner.subscripts, special="LENGTH OF", loc=self.loc(t))
        if u == "ADDRESS" and self.at_word("OF"):
            raise NotSupported("ADDRESS OF is not supported", t)
        ref = ir.Ref(name=u, loc=self.loc(t))
        while self.at_word("OF", "IN"):
            self.next()
            ref.qualifiers.append(self.next().value.upper())
        if self.at_kind(TK.LPAREN):
            self._parse_subscripts_or_refmod(ref)
            if self.at_kind(TK.LPAREN):
                self._parse_subscripts_or_refmod(ref)
        if u in ("RETURN-CODE", "TALLY", "SORT-RETURN", "WHEN-COMPILED"):
            ref.special = u
        return ref

    def _parse_subscripts_or_refmod(self, ref: ir.Ref) -> None:
        save = self.i
        self.next()  # (
        first = self.parse_expr()
        if self.at_kind(TK.COLON):
            self.next()
            length = None if self.at_kind(TK.RPAREN) else self.parse_expr()
            if not self.at_kind(TK.RPAREN):
                self.i = save
                raise ParseError("malformed reference modification", self.peek())
            self.next()
            ref.refmod = ir.RefMod(first, length)
            return
        subs = [first]
        while not self.at_kind(TK.RPAREN):
            if self.at_end():
                raise ParseError("unterminated subscript", None)
            subs.append(self.parse_expr())
        self.next()
        ref.subscripts = subs

    def parse_operand(self) -> ir.Expr:
        t = self.peek()
        if t is None:
            raise ParseError("expected operand", None)
        if t.kind == TK.NUMBER:
            self.next()
            v = t.value[1:] if t.value.startswith("+") else t.value
            return ir.Literal("number", v, loc=self.loc(t))
        if t.kind == TK.STRING:
            self.next()
            return ir.Literal("string", t.value, loc=self.loc(t))
        if t.is_word("ALL"):
            self.next()
            lit = self.parse_operand()
            if isinstance(lit, ir.Literal):
                lit.all = True
            return lit
        if t.kind == TK.WORD and t.value.upper() in FIGURATIVES:
            self.next()
            return ir.Literal("figurative", FIGURATIVES[t.value.upper()], loc=self.loc(t))
        if t.is_word("FUNCTION"):
            return self.parse_function()
        if t.kind == TK.WORD:
            return self.parse_identifier()
        raise ParseError(f"unexpected {t.value!r}", t)

    def parse_function(self) -> ir.FuncCall:
        start = self.next()
        name = self.next().value.upper()
        fc = ir.FuncCall(name=name, args=[], loc=self.loc(start))
        if self.at_kind(TK.LPAREN):
            self.next()
            while not self.at_kind(TK.RPAREN):
                if self.at_end():
                    raise ParseError("unterminated function call", start)
                if self.at_word("LEADING", "TRAILING") and name == "TRIM":
                    fc.keywords.append(self.next().value.upper())
                    continue
                fc.args.append(self.parse_expr())
            self.next()
        if self.at_kind(TK.LPAREN):  # reference modification on function result
            raise NotSupported("reference modification of a function result is not supported", self.peek())
        if name not in SUPPORTED_FUNCTIONS:
            raise NotSupported(f"intrinsic FUNCTION {name} is not supported", start)
        return fc

    # ---------------- arithmetic expressions
    def parse_expr(self) -> ir.Expr:
        left = self.parse_term()
        while self.at_kind(TK.OP) and self.peek().value in ("+", "-"):
            op = self.next().value
            right = self.parse_term()
            left = ir.BinOp(op, left, right)
        return left

    def parse_term(self) -> ir.Expr:
        left = self.parse_power()
        while self.at_kind(TK.OP) and self.peek().value in ("*", "/"):
            op = self.next().value
            right = self.parse_power()
            left = ir.BinOp(op, left, right)
        return left

    def parse_power(self) -> ir.Expr:
        base = self.parse_unary()
        if self.at_kind(TK.OP) and self.peek().value == "**":
            self.next()
            exp = self.parse_power()
            return ir.BinOp("**", base, exp)
        return base

    def parse_unary(self) -> ir.Expr:
        if self.at_kind(TK.OP) and self.peek().value in ("+", "-"):
            op = self.next().value
            operand = self.parse_unary()
            return ir.Neg(operand) if op == "-" else operand
        if self.at_kind(TK.LPAREN):
            self.next()
            e = self.parse_expr()
            if not self.at_kind(TK.RPAREN):
                raise ParseError("expected ')'", self.peek())
            self.next()
            return e
        return self.parse_operand()

    # ---------------- conditions
    def parse_condition(self) -> ir.Cond:
        return self._parse_or()

    def _parse_or(self) -> ir.Cond:
        left = self._parse_and()
        while self.at_word("OR"):
            self.next()
            right = self._parse_and(abbrev_from=left)
            left = ir.Or(left, right)
        return left

    def _parse_and(self, abbrev_from: ir.Cond | None = None) -> ir.Cond:
        left = self._parse_not(abbrev_from)
        while self.at_word("AND"):
            self.next()
            right = self._parse_not(abbrev_from=left)
            left = ir.And(left, right)
        return left

    def _last_rel(self, c: ir.Cond | None) -> ir.Rel | None:
        while c is not None:
            if isinstance(c, ir.Rel):
                return c
            if isinstance(c, ir.And | ir.Or):
                c = c.right
            elif isinstance(c, ir.Not):
                c = c.operand
            else:
                return None
        return None

    def _parse_not(self, abbrev_from: ir.Cond | None = None) -> ir.Cond:
        if self.at_word("NOT"):
            # "NOT <relop>" in an abbreviated condition is handled below
            nxt = self.peek(1)
            if not (abbrev_from is not None and nxt is not None and self._is_relop_start(1)):
                self.next()
                return ir.Not(self._parse_not(abbrev_from))
        return self._parse_primary(abbrev_from)

    def _is_relop_start(self, k: int = 0) -> bool:
        t = self.peek(k)
        if t is None:
            return False
        if t.kind == TK.OP and t.value in ("=", "<", ">", "<=", ">=", "<>"):
            return True
        if t.kind == TK.WORD and t.value.upper() in RELOP_WORDS:
            return True
        if t.is_word("IS"):
            return self._is_relop_start(k + 1)
        if t.is_word("NOT"):
            return self._is_relop_start(k + 1)
        return False

    def _parse_relop(self) -> str:
        self.accept_word("IS")
        negate = bool(self.accept_word("NOT"))
        t = self.next()
        if t.kind == TK.OP:
            op = t.value
        else:
            u = t.value.upper()
            if u in ("EQUAL", "EQUALS"):
                self.accept_word("TO")
                op = "="
            elif u == "GREATER":
                self.accept_word("THAN")
                if self.at_word("OR") and self.peek(1) and self.peek(1).is_word("EQUAL"):
                    self.i += 2
                    self.accept_word("TO")
                    op = ">="
                else:
                    op = ">"
            elif u == "LESS":
                self.accept_word("THAN")
                if self.at_word("OR") and self.peek(1) and self.peek(1).is_word("EQUAL"):
                    self.i += 2
                    self.accept_word("TO")
                    op = "<="
                else:
                    op = "<"
            else:
                raise ParseError(f"expected relational operator, found {t.value!r}", t)
        if negate:
            op = {"=": "<>", "<>": "=", "<": ">=", ">=": "<", ">": "<=", "<=": ">"}[op]
        return op

    def _parse_primary(self, abbrev_from: ir.Cond | None) -> ir.Cond:
        # abbreviated combined relation: "... OR > 5" / "... OR NOT = 5"
        if abbrev_from is not None and self._is_relop_start():
            last = self._last_rel(abbrev_from)
            if last is None:
                raise ParseError("abbreviated condition without subject", self.peek())
            op = self._parse_relop()
            right = self.parse_expr()
            return ir.Rel(last.left, op, right)
        if self.at_kind(TK.LPAREN):
            save = self.i
            try:
                self.next()
                c = self.parse_condition()
                if not self.at_kind(TK.RPAREN):
                    raise ParseError("expected ')'", self.peek())
                self.next()
                if self._is_relop_start() or (self.at_kind(TK.OP) and self.peek().value in ("+", "-", "*", "/", "**")):
                    raise ParseError("arithmetic parenthesis", self.peek())
                return c
            except ParseError:
                self.i = save
        left = self.parse_expr()
        # condition-name?
        if isinstance(left, ir.Ref) and self._is_condition_name(left) and not self._is_relop_start():
            return ir.CondRef(left)
        # class / sign condition
        k = 0
        if self.at_word("IS"):
            k = 1
        neg = self.peek(k) is not None and self.peek(k).is_word("NOT")
        kk = k + (1 if neg else 0)
        t = self.peek(kk)
        if t is not None and t.kind == TK.WORD and t.value.upper() in CLASS_WORDS and not self._is_relop_start():
            self.i += kk + 1
            cls = t.value.upper()
            if cls in ("ZEROS", "ZEROES"):
                cls = "ZERO"
            return ir.ClassCond(left, cls, neg)
        if self._is_relop_start():
            op = self._parse_relop()
            right = self.parse_expr()
            return ir.Rel(left, op, right)
        # abbreviated object only: "A = 1 OR 2"
        if abbrev_from is not None:
            last = self._last_rel(abbrev_from)
            if last is not None:
                return ir.Rel(last.left, last.op, left)
        raise ParseError("expected condition", self.peek())

    def _is_condition_name(self, ref: ir.Ref) -> bool:
        return ref.name in self.conds_by_name and ref.name not in self.items_by_name

    # ---------------- size error / exception phrases
    def _parse_phrases(self, pos_words: tuple[str, ...], neg_label: str) -> tuple[list[ir.Stmt] | None, list[ir.Stmt] | None]:
        on: list[ir.Stmt] | None = None
        off: list[ir.Stmt] | None = None
        for _ in range(2):
            save = self.i
            neg = bool(self.accept_word("NOT"))
            self.accept_word("ON", "AT")
            if self.at_word(*pos_words):
                while self.at_word(*pos_words):
                    self.next()
                body = self.parse_statements(stop=set())
                if neg:
                    off = body
                else:
                    on = body
            else:
                self.i = save
                break
        return on, off

    # ---------------- statements
    def st_move(self) -> ir.Stmt:
        start = self.next()
        if self.at_word("CORRESPONDING", "CORR"):
            self.i -= 1
            return self.st_unsupported("statement", reason="MOVE CORRESPONDING is not supported")
        src = self.parse_operand()
        self.expect_word("TO")
        targets = [self.parse_identifier()]
        while self._at_identifier():
            targets.append(self.parse_identifier())
        return ir.Move(loc=self.loc(start, self.last_tok()), source=src, targets=targets)

    def _at_identifier(self) -> bool:
        t = self.peek()
        if t is None or t.kind != TK.WORD:
            return False
        u = t.value.upper()
        if u in STOP_WORDS or u in (
            "ROUNDED",
            "GIVING",
            "FROM",
            "TO",
            "BY",
            "INTO",
            "REMAINDER",
            "USING",
            "DELIMITED",
            "WITH",
            "POINTER",
            "UPON",
            "RETURNING",
            "THRU",
            "THROUGH",
            "TIMES",
            "UNTIL",
            "VARYING",
            "AFTER",
            "ALSO",
            "OR",
            "AND",
            "END",
        ):
            return False
        if u in self.paragraph_names and self.peek(1) and self.peek(1).kind == TK.PERIOD:
            return False
        return True

    def _targets(self) -> list[ir.Target]:
        out = []
        while self._at_identifier():
            ref = self.parse_identifier()
            rounded = bool(self.accept_word("ROUNDED"))
            if rounded and self.at_word("MODE"):
                self.next()
                self.accept_word("IS")
                mode = self.next().value.upper()
                if mode != "NEAREST-AWAY-FROM-ZERO":
                    raise NotSupported(f"ROUNDED MODE {mode} is not supported", self.last_tok())
            out.append(ir.Target(ref, rounded))
        return out

    def st_compute(self) -> ir.Stmt:
        start = self.next()
        targets = self._targets()
        if not (self.at_kind(TK.OP) and self.peek().value == "=") and not self.at_word("EQUAL"):
            raise ParseError("expected '=' in COMPUTE", self.peek())
        self.next()
        expr = self.parse_expr()
        on, off = self._parse_phrases(("SIZE", "ERROR"), "SIZE")
        self.accept_word("END-COMPUTE")
        return ir.Compute(loc=self.loc(start, self.last_tok()), targets=targets, expr=expr, on_size_error=on, not_on_size_error=off)

    def _operands_until(self, *words: str) -> list[ir.Expr]:
        ops = []
        while not self.at_word(*words) and not self.at_end() and not self.at_kind(TK.PERIOD):
            ops.append(self.parse_operand())
        return ops

    def st_add(self) -> ir.Stmt:
        return self._arith("ADD", "TO")

    def st_subtract(self) -> ir.Stmt:
        return self._arith("SUBTRACT", "FROM")

    def st_multiply(self) -> ir.Stmt:
        return self._arith("MULTIPLY", "BY")

    def st_divide(self) -> ir.Stmt:
        return self._arith("DIVIDE", "INTO", "BY")

    def _arith(self, op: str, *prep: str) -> ir.Stmt:
        start = self.next()
        if self.at_word("CORRESPONDING", "CORR"):
            self.i -= 1
            return self.st_unsupported("statement", reason=f"{op} CORRESPONDING is not supported")
        operands = self._operands_until(*prep, "GIVING")
        st = ir.Arith(loc=self.loc(start), op=op, operands=operands)
        if self.at_word(*prep):
            p = self.next().value.upper()
            st.divide_by = p == "BY" and op == "DIVIDE"
            if self.at_word("GIVING") or not self._has_giving_ahead():
                pass
            if self._has_giving_ahead():
                st.base = self.parse_operand()
                self.expect_word("GIVING")
                st.giving = True
                st.targets = self._targets()
            else:
                st.targets = self._targets()
        elif self.at_word("GIVING"):  # ADD a b GIVING c
            self.next()
            st.giving = True
            st.targets = self._targets()
        if op == "DIVIDE" and self.accept_word("REMAINDER"):
            st.remainder = self.parse_identifier()
        if not st.targets:
            raise ParseError(f"{op} without receiving field", self.peek())
        on, off = self._parse_phrases(("SIZE", "ERROR"), "SIZE")
        st.on_size_error, st.not_on_size_error = on, off
        self.accept_word(f"END-{op}")
        st.loc = self.loc(start, self.last_tok())
        return st

    def _has_giving_ahead(self) -> bool:
        j = self.i
        depth = 0
        while j < len(self.toks):
            t = self.toks[j]
            if t.kind == TK.LPAREN:
                depth += 1
            elif t.kind == TK.RPAREN:
                depth -= 1
            elif t.kind == TK.PERIOD:
                return False
            elif depth == 0 and t.kind == TK.WORD:
                u = t.value.upper()
                if u == "GIVING":
                    return True
                if u in STOP_WORDS or u == "ROUNDED" or u == "REMAINDER":
                    return False
            j += 1
        return False

    def st_if(self) -> ir.Stmt:
        start = self.next()
        cond = self.parse_condition()
        self.accept_word("THEN")
        then = self._imperative_or_next_sentence(stop={"ELSE"})
        orelse: list[ir.Stmt] = []
        if self.accept_word("ELSE"):
            orelse = self._imperative_or_next_sentence(stop=set())
        self.accept_word("END-IF")
        return ir.If(loc=self.loc(start, self.last_tok()), cond=cond, then=then, orelse=orelse)

    def _imperative_or_next_sentence(self, stop: set[str]) -> list[ir.Stmt]:
        if self.at_word("NEXT") and self.peek(1) and self.peek(1).is_word("SENTENCE"):
            t = self.next()
            self.next()
            loc = self.loc(t, self.last_tok())
            self.record_unsupported("NEXT SENTENCE", "statement", "NEXT SENTENCE is not supported (use CONTINUE)", loc)
            return [ir.Unsupported(loc=loc, verb="NEXT SENTENCE", reason="NEXT SENTENCE is not supported", category="statement")]
        return self.parse_statements(stop=stop)

    def st_evaluate(self) -> ir.Stmt:
        start = self.next()
        subjects: list = [self._eval_subject()]
        while self.accept_word("ALSO"):
            subjects.append(self._eval_subject())
        whens: list[ir.When] = []
        while self.at_word("WHEN"):
            wt = self.peek()
            obj_lines: list[list[ir.WhenObject]] = []
            other = False
            while self.at_word("WHEN"):
                self.next()
                if self.accept_word("OTHER"):
                    other = True
                    break
                line = [self._when_object(subjects[0])]
                for subj in subjects[1:]:
                    self.expect_word("ALSO")
                    line.append(self._when_object(subj))
                obj_lines.append(line)
            body = self.parse_statements(stop={"WHEN"})
            whens.append(ir.When(objects=obj_lines, body=body, loc=self.loc(wt, self.last_tok()), other=other))
        self.accept_word("END-EVALUATE")
        return ir.Evaluate(loc=self.loc(start, self.last_tok()), subjects=subjects, whens=whens)

    def _eval_subject(self):
        if self.at_word("TRUE", "FALSE"):
            return self.next().value.upper()
        save = self.i
        try:
            e = self.parse_expr()
            if self._is_relop_start() or (isinstance(e, ir.Ref) and self._is_condition_name(e)):
                raise ParseError("condition subject", None)
            if self.at_word("AND", "OR"):
                raise ParseError("condition subject", None)
            return e
        except ParseError:
            self.i = save
            return self.parse_condition()

    def _when_object(self, subject) -> ir.WhenObject:
        if self.accept_word("ANY"):
            return ir.WhenObject("any")
        if self.at_word("TRUE", "FALSE"):
            return ir.WhenObject(self.next().value.lower())
        if subject in ("TRUE", "FALSE"):
            return ir.WhenObject("cond", cond=self.parse_condition())
        neg = bool(self.accept_word("NOT"))
        v = self.parse_expr()
        if self.accept_word("THRU", "THROUGH"):
            hi = self.parse_expr()
            return ir.WhenObject("range", value=v, high=hi, negated=neg)
        return ir.WhenObject("value", value=v, negated=neg)

    def st_perform(self) -> ir.Stmt:
        start = self.next()
        st = ir.Perform(loc=self.loc(start))
        t = self.peek()
        if (
            t is not None
            and t.kind in (TK.WORD, TK.NUMBER)
            and t.value.upper() in (self.paragraph_names | self.section_names)
            and not t.is_word("VARYING", "UNTIL", "WITH", "TEST")
        ):
            st.target = self.next().value.upper()
            if self.accept_word("THRU", "THROUGH"):
                st.thru = self.next().value.upper()
        self._perform_options(st)
        if st.target is None:
            st.body = self.parse_statements(stop=set())
            self.expect_word("END-PERFORM")
        st.loc = self.loc(start, self.last_tok())
        return st

    def _perform_options(self, st: ir.Perform) -> None:
        if self.at_word("WITH") or self.at_word("TEST"):
            self.accept_word("WITH")
            self.expect_word("TEST")
            st.test_after = self.next().is_word("AFTER")
        if self.accept_word("UNTIL"):
            st.until = self.parse_condition()
        elif self.accept_word("VARYING"):
            st.varying.append(self._varying())
            while self.accept_word("AFTER"):
                st.varying.append(self._varying())
        else:
            t = self.peek()
            if t is not None and (
                t.kind == TK.NUMBER or (t.kind == TK.WORD and t.value.upper() not in ALL_VERBS and self.peek(1) is not None and self._times_ahead())
            ):
                st.times = self.parse_operand()
                self.expect_word("TIMES")

    def _times_ahead(self) -> bool:
        j = self.i
        # identifier [subscripts] TIMES
        depth = 0
        while j < len(self.toks):
            t = self.toks[j]
            if t.kind == TK.LPAREN:
                depth += 1
            elif t.kind == TK.RPAREN:
                depth -= 1
            elif depth == 0:
                if t.is_word("TIMES"):
                    return True
                if t.kind == TK.WORD and j > self.i and not t.is_word("OF", "IN"):
                    return False
                if t.kind == TK.PERIOD:
                    return False
            j += 1
        return False

    def _varying(self) -> ir.Varying:
        var = self.parse_identifier()
        self.expect_word("FROM")
        start = self.parse_expr()
        self.expect_word("BY")
        by = self.parse_expr()
        self.expect_word("UNTIL")
        until = self.parse_condition()
        return ir.Varying(var, start, by, until)

    def st_call(self) -> ir.Stmt:
        start = self.next()
        prog = self.parse_operand()
        st = ir.Call(loc=self.loc(start), program=prog)
        if self.accept_word("USING"):
            mode = "REFERENCE"
            while not self.at_end():
                if self.accept_word("BY"):
                    mode = self.next().value.upper()
                    continue
                if self.at_word("REFERENCE", "CONTENT", "VALUE"):
                    mode = self.next().value.upper()
                    continue
                if self.at_word("OMITTED"):
                    raise NotSupported("OMITTED arguments are not supported", self.peek())
                if not (self._at_identifier() or self.at_kind(TK.STRING) or self.at_kind(TK.NUMBER)):
                    break
                st.using.append(ir.CallArg(self.parse_operand(), mode))
        if self.accept_word("RETURNING", "GIVING"):
            st.returning = self.parse_identifier()
        on, off = self._parse_phrases(("EXCEPTION", "OVERFLOW"), "EXCEPTION")
        st.on_exception, st.not_on_exception = on, off
        self.accept_word("END-CALL")
        st.loc = self.loc(start, self.last_tok())
        return st

    def st_stop(self) -> ir.Stmt:
        start = self.next()
        if self.accept_word("RUN"):
            return ir.StopRun(loc=self.loc(start, self.last_tok()))
        self.i -= 1
        return self.st_unsupported("statement", reason="STOP literal is not supported")

    def st_goback(self) -> ir.Stmt:
        start = self.next()
        return ir.Goback(loc=self.loc(start))

    def st_exit(self) -> ir.Stmt:
        start = self.next()
        what = ""
        if self.at_word("PARAGRAPH", "SECTION", "PROGRAM"):
            what = self.next().value.upper()
        elif self.at_word("PERFORM"):
            self.next()
            what = "PERFORM CYCLE" if self.accept_word("CYCLE") else "PERFORM"
        return ir.Exit(loc=self.loc(start, self.last_tok()), what=what)

    def st_go(self) -> ir.Stmt:
        start = self.next()
        self.accept_word("TO")
        target = self.next().value.upper()
        if self.at_word("DEPENDING") or (
            self.peek()
            and self.peek().kind == TK.WORD
            and self.peek().value.upper() in self.paragraph_names
            and not (self.peek(1) and self.peek(1).kind == TK.PERIOD)
        ):
            self.i -= 1
            while self._at_identifier() or self.at_word("DEPENDING", "ON"):
                self.next()
            loc = self.loc(start, self.last_tok())
            self.record_unsupported("GO TO DEPENDING ON", "statement", "GO TO DEPENDING ON is not supported", loc)
            return ir.Unsupported(loc=loc, verb="GO TO DEPENDING", reason="GO TO DEPENDING ON is not supported", category="statement")
        return ir.GoTo(loc=self.loc(start, self.last_tok()), target=target)

    def st_continue(self) -> ir.Stmt:
        return ir.Continue(loc=self.loc(self.next()))

    def st_display(self) -> ir.Stmt:
        start = self.next()
        st = ir.Display(loc=self.loc(start))
        while not self.at_end():
            if self.at_word("UPON"):
                self.next()
                st.upon = self.next().value.upper()
                continue
            if self.at_word("WITH") or self.at_word("NO"):
                self.accept_word("WITH")
                self.expect_word("NO")
                self.expect_word("ADVANCING")
                st.no_advancing = True
                continue
            if (
                self.at_kind(TK.STRING)
                or self.at_kind(TK.NUMBER)
                or self.at_word("FUNCTION")
                or self._at_identifier()
                or (self.peek().kind == TK.WORD and self.peek().value.upper() in FIGURATIVES)
            ):
                st.operands.append(self.parse_operand())
                continue
            break
        self.accept_word("END-DISPLAY")
        st.loc = self.loc(start, self.last_tok())
        return st

    def st_accept(self) -> ir.Stmt:
        start = self.next()
        target = self.parse_identifier()
        source = ""
        if self.accept_word("FROM"):
            src = self.next().value.upper()
            if src in ("DATE", "DAY") and self.at_word("YYYYMMDD", "YYYYDDD"):
                src += " " + self.next().value.upper()
            if src not in ("DATE", "DATE YYYYMMDD", "DAY", "DAY YYYYDDD", "TIME", "DAY-OF-WEEK", "CONSOLE", "SYSIN", "STDIN"):
                raise NotSupported(f"ACCEPT FROM {src} is not supported", self.last_tok())
            if src in ("CONSOLE", "SYSIN", "STDIN"):
                src = ""
            source = src
        self._parse_phrases(("EXCEPTION",), "EXCEPTION")
        self.accept_word("END-ACCEPT")
        return ir.Accept(loc=self.loc(start, self.last_tok()), target=target, source=source)

    def st_initialize(self) -> ir.Stmt:
        save = self.i
        start = self.next()
        targets = [self.parse_identifier()]
        while self._at_identifier():
            targets.append(self.parse_identifier())
        if self.at_word("REPLACING", "WITH", "ALL", "TO"):
            self.i = save
            return self.st_unsupported("statement", reason="INITIALIZE with REPLACING/WITH FILLER is not supported")
        return ir.Initialize(loc=self.loc(start, self.last_tok()), targets=targets)

    def st_set(self) -> ir.Stmt:
        start = self.next()
        targets = []
        while self._at_identifier():
            targets.append(self.parse_identifier())
        st = ir.SetStmt(loc=self.loc(start), targets=targets)
        if self.accept_word("TO"):
            if self.at_word("TRUE"):
                self.next()
                st.mode = "TRUE"
            elif self.at_word("FALSE", "ON", "OFF", "ADDRESS", "NULL", "ENTRY"):
                raise NotSupported(f"SET ... TO {self.peek().value.upper()} is not supported", self.peek())
            else:
                st.mode = "TO"
                st.value = self.parse_expr()
        elif self.at_word("UP", "DOWN"):
            st.mode = self.next().value.upper()
            self.expect_word("BY")
            st.value = self.parse_expr()
        else:
            raise NotSupported("unsupported SET form", self.peek())
        st.loc = self.loc(start, self.last_tok())
        return st

    def st_string(self) -> ir.Stmt:
        start = self.next()
        st = ir.StringStmt(loc=self.loc(start))
        pending: list[ir.Expr] = []
        while not self.at_word("INTO"):
            if self.at_end() or self.at_kind(TK.PERIOD):
                raise ParseError("STRING without INTO", start)
            if self.accept_word("DELIMITED"):
                self.accept_word("BY")
                if self.accept_word("SIZE"):
                    delim = None
                else:
                    delim = self.parse_operand()
                for e in pending:
                    st.parts.append(ir.StringPart(e, delim))
                pending = []
                continue
            pending.append(self.parse_operand())
        for e in pending:
            st.parts.append(ir.StringPart(e, None))
        self.expect_word("INTO")
        st.into = self.parse_identifier()
        if self.accept_word("WITH") or self.at_word("POINTER"):
            self.expect_word("POINTER")
            st.pointer = self.parse_identifier()
        on, off = self._parse_phrases(("OVERFLOW",), "OVERFLOW")
        st.on_overflow, st.not_on_overflow = on, off
        self.accept_word("END-STRING")
        st.loc = self.loc(start, self.last_tok())
        return st

    # ------------------------------------------------------------ resolution
    def resolve_program(self, prog: ir.Program) -> None:
        index = prog.item_index()
        by_name: dict[str, list[ir.DataItem]] = {}
        for it in index.values():
            by_name.setdefault(it.name, []).append(it)
        conds: dict[str, list[tuple[ir.ConditionName, ir.DataItem]]] = {}
        for it in index.values():
            for c in it.conditions:
                conds.setdefault(c.name, []).append((c, it))

        def ancestors(it: ir.DataItem) -> list[str]:
            out = []
            p = it.parent
            while p:
                out.append(index[p].name)
                p = index[p].parent
            return out

        def pick(cands, quals, getter):
            if quals:
                cands = [c for c in cands if all(q in ancestors(getter(c)) or q == getter(c).name for q in quals)]
            return cands

        def res_ref(r: ir.Ref) -> None:
            if r.special and r.special != "LENGTH OF":
                pass
            elif r.name in by_name:
                cands = pick(by_name[r.name], r.qualifiers, lambda x: x)
                if len(cands) >= 1:
                    r.item = cands[0].id
                    if len(cands) > 1:
                        self.diag(Severity.WARNING, "RES002", f"ambiguous reference {r.name}; using first declaration", self._tok_for(r.loc))
                else:
                    self.diag(Severity.ERROR, "RES001", f"unresolved reference {r.name}", self._tok_for(r.loc))
            elif r.name in conds:
                cands = conds[r.name]
                if r.qualifiers:
                    cands = [c for c in cands if all(q in ancestors(c[1]) or q == c[1].name for q in r.qualifiers)] or cands
                c, parent = cands[0]
                r.cond = f"{parent.id}::{c.name}"
            elif not r.special:
                self.diag(Severity.ERROR, "RES001", f"unresolved reference {r.name}", self._tok_for(r.loc))
            for s in r.subscripts:
                res_expr(s)
            if r.refmod:
                res_expr(r.refmod.start)
                if r.refmod.length:
                    res_expr(r.refmod.length)

        def res_expr(e) -> None:
            if isinstance(e, ir.Ref):
                res_ref(e)
            elif isinstance(e, ir.BinOp):
                res_expr(e.left)
                res_expr(e.right)
            elif isinstance(e, ir.Neg):
                res_expr(e.operand)
            elif isinstance(e, ir.FuncCall):
                for a in e.args:
                    res_expr(a)

        def res_cond(c) -> None:
            if isinstance(c, ir.Rel):
                res_expr(c.left)
                res_expr(c.right)
            elif isinstance(c, ir.CondRef):
                res_ref(c.ref)
            elif isinstance(c, ir.ClassCond):
                res_expr(c.operand)
            elif isinstance(c, ir.Not):
                res_cond(c.operand)
            elif isinstance(c, ir.And | ir.Or):
                res_cond(c.left)
                res_cond(c.right)

        def res_stmt(s: ir.Stmt) -> None:
            if isinstance(s, ir.Move):
                res_expr(s.source)
                for t in s.targets:
                    res_ref(t)
            elif isinstance(s, ir.Compute):
                for t in s.targets:
                    res_ref(t.ref)
                res_expr(s.expr)
            elif isinstance(s, ir.Arith):
                for e in s.operands:
                    res_expr(e)
                if s.base is not None:
                    res_expr(s.base)
                for t in s.targets:
                    res_ref(t.ref)
                if s.remainder:
                    res_ref(s.remainder)
            elif isinstance(s, ir.If):
                res_cond(s.cond)
            elif isinstance(s, ir.Evaluate):
                for subj in s.subjects:
                    if isinstance(subj, str):
                        continue
                    if isinstance(subj, ir.Rel | ir.CondRef | ir.ClassCond | ir.Not | ir.And | ir.Or):
                        res_cond(subj)
                    else:
                        res_expr(subj)
                for w in s.whens:
                    for line in w.objects:
                        for o in line:
                            if o.value is not None:
                                res_expr(o.value)
                            if o.high is not None:
                                res_expr(o.high)
                            if o.cond is not None:
                                res_cond(o.cond)
            elif isinstance(s, ir.Perform):
                if s.times is not None:
                    res_expr(s.times)
                if s.until is not None:
                    res_cond(s.until)
                for v in s.varying:
                    res_ref(v.var)
                    res_expr(v.start)
                    res_expr(v.by)
                    res_cond(v.until)
                names = {p.name for p in prog.paragraphs} | {sec.name for sec in prog.sections}
                for tname in (s.target, s.thru):
                    if tname and tname not in names:
                        self.diag(Severity.ERROR, "RES003", f"PERFORM target {tname} not found", self._tok_for(s.loc))
            elif isinstance(s, ir.Call):
                res_expr(s.program)
                for a in s.using:
                    res_expr(a.expr)
                if s.returning:
                    res_ref(s.returning)
            elif isinstance(s, ir.Display):
                for e in s.operands:
                    res_expr(e)
            elif isinstance(s, ir.Accept):
                res_ref(s.target)
            elif isinstance(s, ir.Initialize):
                for t in s.targets:
                    res_ref(t)
            elif isinstance(s, ir.SetStmt):
                for t in s.targets:
                    res_ref(t)
                if s.value is not None:
                    res_expr(s.value)
            elif isinstance(s, ir.StringStmt):
                for p in s.parts:
                    res_expr(p.expr)
                    if p.delimiter is not None:
                        res_expr(p.delimiter)
                res_ref(s.into)
                if s.pointer:
                    res_ref(s.pointer)

        for p in prog.paragraphs:
            for s in ir.walk_statements(p.statements):
                res_stmt(s)
        resolved_using = []
        for name in prog.using:
            cands = by_name.get(name)
            if cands:
                resolved_using.append(cands[0].id)
            else:
                self.diag(Severity.ERROR, "RES004", f"USING parameter {name} not declared", None)
        prog.using = resolved_using

    def _tok_for(self, loc: ir.Loc | None) -> Token | None:
        if loc is None:
            return None
        return Token(TK.WORD, "", loc.file, loc.line)
