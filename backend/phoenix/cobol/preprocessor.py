"""COPY statement expansion.

Copybook tokens keep their *own* file name and line numbers, so every IR node
built from them cites the copybook as evidence. Supported:

    COPY name [OF|IN library] [SUPPRESS] [REPLACING {==a== | word | literal} BY {==b== | word | literal} ...].

``REPLACE`` statements and ``COPY ... REPLACING LEADING/TRAILING`` are reported
as unsupported.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .diagnostics import Diagnostic, Severity
from .lexer import TK, SourceFormat, Token, tokenize

MAX_DEPTH = 10


@dataclass(slots=True)
class CopyEvent:
    name: str
    file: str  # file containing the COPY statement
    line: int
    resolved: str | None  # resolved copybook path (project relative)
    replacing: bool = False


@dataclass
class PreprocessResult:
    tokens: list[Token]
    copies: list[CopyEvent] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


# resolver(name) -> (path, text, format) | None
Resolver = Callable[[str], "tuple[str, str, SourceFormat | None] | None"]


def _replacement_operand(toks: list[Token], i: int) -> tuple[list[Token], int]:
    t = toks[i]
    if t.kind == TK.PSEUDO:
        return list(t.inner), i + 1
    return [t], i + 1


def _norm(t: Token) -> tuple[str, str]:
    return (t.kind.value, t.value.upper() if t.kind in (TK.WORD,) else t.value)


def _apply_replacing(tokens: list[Token], pairs: list[tuple[list[Token], list[Token]]]) -> list[Token]:
    if not pairs:
        return tokens
    out: list[Token] = []
    i = 0
    n = len(tokens)
    while i < n:
        for old, new in pairs:
            m = len(old)
            if m and i + m <= n and all(_norm(tokens[i + k]) == _norm(old[k]) for k in range(m)):
                anchor = tokens[i]
                for nt in new:
                    out.append(Token(nt.kind, nt.value, anchor.file, anchor.line, anchor.col, nt.hex, nt.inner, anchor.copied_from))
                i += m
                break
            if m == 1 and old[0].kind == TK.WORD and tokens[i].kind == TK.WORD:
                # partial word replacement (e.g. ==:PFX:== tags) inside a word
                ov = old[0].value.upper()
                tv = tokens[i].value.upper()
                if ov.startswith(":") and ov in tv and len(new) == 1:
                    t = tokens[i]
                    nv = tv.replace(ov, new[0].value.upper())
                    out.append(Token(t.kind, nv, t.file, t.line, t.col, copied_from=t.copied_from))
                    i += 1
                    break
        else:
            out.append(tokens[i])
            i += 1
    return out


def expand_copies(
    file: str,
    tokens: list[Token],
    resolver: Resolver,
    _depth: int = 0,
    _stack: tuple[str, ...] = (),
) -> PreprocessResult:
    res = PreprocessResult(tokens=[])
    i = 0
    n = len(tokens)
    while i < n:
        t = tokens[i]
        if t.is_word("REPLACE") and (i == 0 or tokens[i - 1].kind == TK.PERIOD):
            res.diagnostics.append(
                Diagnostic(Severity.WARNING, "PP003", "REPLACE statement is not supported and was ignored", t.file, t.line)
            )
            while i < n and tokens[i].kind != TK.PERIOD:
                i += 1
            i += 1
            continue
        if not t.is_word("COPY"):
            res.tokens.append(t)
            i += 1
            continue
        # --- parse COPY statement
        start = t
        i += 1
        if i >= n:
            break
        name_tok = tokens[i]
        name = name_tok.value
        i += 1
        if i < n and tokens[i].is_word("OF", "IN"):
            i += 2
        if i < n and tokens[i].is_word("SUPPRESS"):
            i += 1
        pairs: list[tuple[list[Token], list[Token]]] = []
        has_replacing = False
        if i < n and tokens[i].is_word("REPLACING"):
            has_replacing = True
            i += 1
            while i < n and tokens[i].kind != TK.PERIOD:
                if tokens[i].is_word("LEADING", "TRAILING"):
                    res.diagnostics.append(
                        Diagnostic(Severity.WARNING, "PP004", "COPY REPLACING LEADING/TRAILING is not supported", tokens[i].file, tokens[i].line)
                    )
                    i += 1
                old, i = _replacement_operand(tokens, i)
                if i < n and tokens[i].is_word("BY"):
                    i += 1
                if i >= n:
                    break
                new, i = _replacement_operand(tokens, i)
                pairs.append((old, new))
        if i < n and tokens[i].kind == TK.PERIOD:
            i += 1
        resolved = resolver(name)
        ev = CopyEvent(name=name, file=start.file, line=start.line, resolved=resolved[0] if resolved else None, replacing=has_replacing)
        res.copies.append(ev)
        if resolved is None:
            res.diagnostics.append(Diagnostic(Severity.ERROR, "PP001", f"copybook {name!r} not found", start.file, start.line))
            continue
        path, text, fmt = resolved
        if path in _stack or _depth >= MAX_DEPTH:
            res.diagnostics.append(Diagnostic(Severity.ERROR, "PP002", f"recursive or too deep COPY of {name!r}", start.file, start.line))
            continue
        ctoks, cdiags, _ = tokenize(path, text, fmt)
        for ct in ctoks:
            ct.copied_from = f"{start.file}:{start.line}"
        res.diagnostics.extend(cdiags)
        sub = expand_copies(path, ctoks, resolver, _depth + 1, _stack + (path,))
        res.copies.extend(sub.copies)
        res.diagnostics.extend(sub.diagnostics)
        res.tokens.extend(_apply_replacing(sub.tokens, pairs))
    return res
