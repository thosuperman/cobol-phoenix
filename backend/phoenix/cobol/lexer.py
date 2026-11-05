"""Source reading and tokenisation for the supported COBOL subset.

The lexer is deliberately simple and deterministic:

* fixed format: columns 1-6 sequence area (ignored), column 7 indicator
  (``*``/``/`` comment, ``-`` continuation, ``D`` debug line treated as comment),
  columns 8-72 program text, 73+ ignored;
* free format: whole line, ``*>`` starts a comment;
* every token carries the file and line it came from (copybook tokens keep the
  copybook's own coordinates).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

from .diagnostics import Diagnostic, Severity


class SourceFormat(StrEnum):
    FIXED = "fixed"
    FREE = "free"


class TK(StrEnum):
    WORD = "WORD"
    NUMBER = "NUMBER"
    STRING = "STRING"
    PICTURE = "PICTURE"
    PSEUDO = "PSEUDO"
    PERIOD = "PERIOD"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    OP = "OP"
    COLON = "COLON"


@dataclass(slots=True)
class Token:
    kind: TK
    value: str
    file: str
    line: int
    col: int = 0
    # For STRING tokens: was it a hex literal (value already decoded)
    hex: bool = False
    # Pseudo-text tokens carry their inner token list
    inner: list[Token] = field(default_factory=list)
    # True when the token was produced by COPY expansion
    copied_from: str | None = None

    @property
    def upper(self) -> str:
        return self.value.upper() if self.kind == TK.WORD else self.value

    def is_word(self, *words: str) -> bool:
        return self.kind == TK.WORD and self.value.upper() in words

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<{self.kind}:{self.value!r}@{self.file}:{self.line}>"


_FIXED_INDICATORS = set(" *-/dD$")
_DIRECTIVE_RE = re.compile(r"^\s*>>\s*SOURCE(\s+FORMAT)?(\s+IS)?\s+(FREE|FIXED)", re.I)


def detect_format(text: str) -> SourceFormat:
    """Heuristically decide between fixed and free reference format."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return SourceFormat.FIXED
    for ln in lines[:50]:
        m = _DIRECTIVE_RE.match(ln) or _DIRECTIVE_RE.match(ln[7:] if len(ln) > 7 else "")
        if m:
            return SourceFormat(m.group(3).lower())
    fixed_votes = 0
    free_votes = 0
    for ln in lines:
        seq = ln[:6]
        ind = ln[6] if len(ln) > 6 else " "
        if seq.strip() and not seq.strip().isdigit():
            free_votes += 1
            continue
        if ind not in _FIXED_INDICATORS:
            free_votes += 1
            continue
        body = ln[7:]
        if len(ln) > 72 and ln[72:].strip() and not ln[6:].lstrip().startswith("*>") and ind not in "*/":
            # Text beyond column 72 is legal only as identification area; long
            # code lines strongly suggest free format.
            if "*>" not in ln[:72]:
                free_votes += 1
                continue
        if body or ind != " ":
            fixed_votes += 1
    return SourceFormat.FREE if free_votes > max(2, fixed_votes // 20) else SourceFormat.FIXED


@dataclass(slots=True)
class LogicalLine:
    file: str
    line: int
    text: str  # program text (area A+B for fixed format)
    col_offset: int  # column of text[0] in the physical line (1-based)
    continuation: bool = False


def logical_lines(file: str, text: str, fmt: SourceFormat, diags: list[Diagnostic]) -> list[LogicalLine]:
    out: list[LogicalLine] = []
    for n, raw in enumerate(text.splitlines(), start=1):
        raw = raw.replace("\t", "    ").rstrip("\r\n")
        stripped = raw.strip()
        if fmt == SourceFormat.FIXED:
            if len(raw) < 7:
                continue
            ind = raw[6]
            body = raw[7:72]
            if body.lstrip().startswith(">>") or raw[:7].lstrip().startswith(">>"):
                continue  # compiler directive
            if ind in "*/":
                continue
            if ind in "dD":
                continue  # debugging line, compiled only WITH DEBUGGING MODE
            if ind == "$":
                continue
            out.append(LogicalLine(file, n, body, 8, continuation=(ind == "-")))
        else:
            if stripped.startswith(">>") or stripped.startswith("*>"):
                continue
            if stripped.startswith("*") and raw[:1] == "*":
                continue
            out.append(LogicalLine(file, n, raw, 1))
    return out


_WORD_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
_NUM_RE = re.compile(r"[+-]?(\d+(\.\d+)?|\.\d+)")


class Lexer:
    def __init__(self, file: str, text: str, fmt: SourceFormat | None = None) -> None:
        self.file = file
        self.text = text
        self.format = fmt or detect_format(text)
        self.diagnostics: list[Diagnostic] = []
        self.tokens: list[Token] = []

    # ------------------------------------------------------------------
    def tokenize(self) -> list[Token]:
        lines = logical_lines(self.file, self.text, self.format, self.diagnostics)
        pending_string: Token | None = None  # literal awaiting continuation
        pending_quote = ""
        pseudo: Token | None = None
        pseudo_buf: list[tuple[str, int, int]] = []
        expect_picture = False
        for ll in lines:
            s = ll.text
            i = 0
            if ll.continuation and pending_string is not None:
                # Continuation of an alphanumeric literal: resume after the
                # first quote on the continuation line.
                j = 0
                while j < len(s) and s[j] == " ":
                    j += 1
                if j < len(s) and s[j] in "\"'":
                    j += 1
                    val, end, closed = self._scan_string_body(s, j, pending_quote)
                    pending_string.value += val
                    i = end
                    if closed:
                        self.tokens.append(pending_string)
                        pending_string = None
                else:
                    self.tokens.append(pending_string)
                    pending_string = None
            elif pending_string is not None:
                # Unterminated literal without continuation: GnuCOBOL pads to col 72.
                self.tokens.append(pending_string)
                self._diag(Severity.WARNING, "LEX001", "unterminated alphanumeric literal", pending_string.line)
                pending_string = None
            if self.format == SourceFormat.FIXED and pending_string is None:
                # Strip floating comments in fixed format.
                s = self._strip_inline_comment(s)
            elif self.format == SourceFormat.FREE:
                s = self._strip_inline_comment(s)
            n = len(s)
            while i < n:
                c = s[i]
                col = ll.col_offset + i
                if pseudo is not None:
                    end = s.find("==", i)
                    if end == -1:
                        pseudo_buf.append((s[i:], ll.line, col))
                        i = n
                        continue
                    pseudo_buf.append((s[i:end], ll.line, col))
                    pseudo.inner = self._lex_fragment(pseudo_buf)
                    pseudo.value = " ".join(t.value for t in pseudo.inner)
                    self.tokens.append(pseudo)
                    pseudo = None
                    pseudo_buf = []
                    i = end + 2
                    continue
                if c in " ,;" and not (c in ",;" and i + 1 < n and s[i + 1] not in " "):
                    i += 1
                    continue
                if c in ",;":
                    i += 1
                    continue
                if expect_picture:
                    j = i
                    while j < n and s[j] != " ":
                        j += 1
                    pic = s[i:j]
                    trailing_period = False
                    if pic.endswith(".") and (j >= n or s[j] == " "):
                        pic = pic[:-1]
                        trailing_period = True
                    if pic.upper() == "IS":
                        self.tokens.append(Token(TK.WORD, pic, self.file, ll.line, col))
                        i = j
                        continue
                    self.tokens.append(Token(TK.PICTURE, pic, self.file, ll.line, col))
                    if trailing_period:
                        self.tokens.append(Token(TK.PERIOD, ".", self.file, ll.line, col + len(pic)))
                    expect_picture = False
                    i = j
                    continue
                if s.startswith("==", i):
                    pseudo = Token(TK.PSEUDO, "", self.file, ll.line, col)
                    pseudo_buf = []
                    i += 2
                    continue
                if c in "\"'" or (c in "xXzZnN" and i + 1 < n and s[i + 1] in "\"'"):
                    hexlit = c in "xX"
                    if c not in "\"'":
                        i += 1
                    q = s[i]
                    val, end, closed = self._scan_string_body(s, i + 1, q)
                    tok = Token(TK.STRING, val, self.file, ll.line, col)
                    if hexlit:
                        try:
                            tok.value = bytes.fromhex(val).decode("latin-1")
                            tok.hex = True
                        except ValueError:
                            self._diag(Severity.ERROR, "LEX002", f"invalid hexadecimal literal X'{val}'", ll.line)
                    i = end
                    if closed:
                        self.tokens.append(tok)
                    else:
                        if self.format == SourceFormat.FIXED:
                            # literal continues on next line: it implicitly
                            # extends with spaces up to column 72
                            tok.value = val + " " * max(0, 65 - len(ll.text))
                        pending_string = tok
                        pending_quote = q
                    continue
                if c == ".":
                    if i + 1 < n and s[i + 1].isdigit() and (i == 0 or s[i - 1] in " (+-*/="):
                        m = _NUM_RE.match(s, i)
                        assert m
                        self.tokens.append(Token(TK.NUMBER, m.group(0), self.file, ll.line, col))
                        i = m.end()
                        continue
                    self.tokens.append(Token(TK.PERIOD, ".", self.file, ll.line, col))
                    i += 1
                    continue
                if c == "(":
                    self.tokens.append(Token(TK.LPAREN, "(", self.file, ll.line, col))
                    i += 1
                    continue
                if c == ")":
                    self.tokens.append(Token(TK.RPAREN, ")", self.file, ll.line, col))
                    i += 1
                    continue
                if c == ":":
                    self.tokens.append(Token(TK.COLON, ":", self.file, ll.line, col))
                    i += 1
                    continue
                if c in "+-" and i + 1 < n and (s[i + 1].isdigit() or (s[i + 1] == "." and i + 2 < n and s[i + 2].isdigit())):
                    prev = self.tokens[-1] if self.tokens else None
                    # A sign directly attached to digits is part of the literal
                    # unless it follows an operand without a separating space.
                    if i == 0 or s[i - 1] in " (=":
                        if not (prev and prev.kind in (TK.NUMBER, TK.RPAREN) and s[i - 1] != " " ):
                            m = _NUM_RE.match(s, i)
                            assert m
                            end = m.end()
                            if end >= n or not (s[end] in _WORD_CHARS and s[end] not in "-"):
                                self.tokens.append(Token(TK.NUMBER, m.group(0), self.file, ll.line, col))
                                i = end
                                continue
                if c in "+-*/=<>&":
                    if s.startswith("**", i):
                        op = "**"
                    elif s.startswith(">=", i) or s.startswith("<=", i) or s.startswith("<>", i):
                        op = s[i : i + 2]
                    else:
                        op = c
                    self.tokens.append(Token(TK.OP, op, self.file, ll.line, col))
                    i += len(op)
                    continue
                if c in _WORD_CHARS or ord(c) >= 0x80:
                    j = i
                    while j < n and (s[j] in _WORD_CHARS or ord(s[j]) >= 0x80):
                        j += 1
                    # decimal numbers: 123.45
                    word = s[i:j]
                    if word.isdigit() and j + 1 < n and s[j] == "." and s[j + 1].isdigit():
                        k = j + 1
                        while k < n and s[k].isdigit():
                            k += 1
                        self.tokens.append(Token(TK.NUMBER, s[i:k], self.file, ll.line, col))
                        i = k
                        continue
                    kind = TK.NUMBER if word.isdigit() else TK.WORD
                    self.tokens.append(Token(kind, word, self.file, ll.line, col))
                    if kind == TK.WORD and word.upper() in ("PIC", "PICTURE"):
                        expect_picture = True
                    i = j
                    continue
                self._diag(Severity.WARNING, "LEX003", f"unexpected character {c!r}", ll.line)
                i += 1
        if pending_string is not None:
            self.tokens.append(pending_string)
        return self.tokens

    # ------------------------------------------------------------------
    @staticmethod
    def _scan_string_body(s: str, i: int, q: str) -> tuple[str, int, bool]:
        buf = []
        n = len(s)
        while i < n:
            if s[i] == q:
                if i + 1 < n and s[i + 1] == q:
                    buf.append(q)
                    i += 2
                    continue
                return "".join(buf), i + 1, True
            buf.append(s[i])
            i += 1
        return "".join(buf), i, False

    @staticmethod
    def _strip_inline_comment(s: str) -> str:
        q = ""
        i = 0
        while i < len(s):
            c = s[i]
            if q:
                if c == q:
                    q = ""
            elif c in "\"'":
                q = c
            elif s.startswith("*>", i):
                return s[:i]
            i += 1
        return s

    def _lex_fragment(self, parts: list[tuple[str, int, int]]) -> list[Token]:
        out: list[Token] = []
        for text, line, col in parts:
            sub = Lexer(self.file, " " * 7 + text if self.format == SourceFormat.FIXED else text, self.format)
            sub_tokens = sub.tokenize()
            for t in sub_tokens:
                t.line = line
                t.col = col
            out.extend(sub_tokens)
        return out

    def _diag(self, sev: Severity, code: str, msg: str, line: int) -> None:
        self.diagnostics.append(Diagnostic(sev, code, msg, self.file, line))


def tokenize(file: str, text: str, fmt: SourceFormat | None = None) -> tuple[list[Token], list[Diagnostic], SourceFormat]:
    lx = Lexer(file, text, fmt)
    toks = lx.tokenize()
    return toks, lx.diagnostics, lx.format
