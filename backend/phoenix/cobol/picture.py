"""PICTURE clause parsing and storage size computation."""

from __future__ import annotations

import re

from .ir import Picture

_REPEAT = re.compile(r"(CR|DB|.)(\((\d+)\))?", re.I)


class PictureError(ValueError):
    pass


def expand(raw: str) -> str:
    out = []
    for m in _REPEAT.finditer(raw.upper()):
        sym = m.group(1)
        count = int(m.group(3)) if m.group(3) else 1
        if sym == "(":
            raise PictureError(f"malformed PICTURE {raw!r}")
        out.append(sym * count)
    return "".join(out)


def parse_picture(raw: str) -> Picture:
    exp = expand(raw)
    if not exp:
        raise PictureError("empty PICTURE")
    up = exp
    has = set(up.replace("CR", "c").replace("DB", "d"))
    if not has <= set("AX9SVPZ*,.+-$B0/cd"):
        raise PictureError(f"unsupported PICTURE symbols in {raw!r}")
    edit_syms = set("Z*,.+-$cd")
    insert_syms = set("B0/")
    if has & set("XA"):
        if has & edit_syms:
            raise PictureError(f"invalid PICTURE {raw!r}")
        if has & insert_syms:
            cat = "alphanumeric-edited"
        elif has <= set("A"):
            cat = "alphabetic"
        else:
            cat = "alphanumeric"
        return Picture(raw=raw, category=cat, size=len(up), expanded=up)
    if has & edit_syms or (has & insert_syms):
        return _edited(raw, up)
    # numeric
    signed = up.startswith("S")
    body = up[1:] if signed else up
    if "S" in body:
        raise PictureError(f"misplaced S in {raw!r}")
    int_part, _, frac_part = body.partition("V")
    if "V" in frac_part:
        raise PictureError(f"multiple V in {raw!r}")
    p_count = body.count("P")
    digits = body.count("9")
    scale = frac_part.count("9")
    if p_count:
        # P scaling positions: on the left of 9s (fraction) or right (integer).
        if body.lstrip("V").startswith("P"):
            scale = p_count + frac_part.count("9")
        else:
            scale = -p_count
    size = digits
    return Picture(raw=raw, category="numeric", size=size, digits=digits, scale=scale, signed=signed, expanded=up, p_scaling=p_count)


def _edited(raw: str, up: str) -> Picture:
    # Display size: CR/DB occupy 2 chars each, all others one.
    size = len(up)
    signed = any(s in up for s in ("+", "-", "CR", "DB"))
    # Digit positions: 9, Z, *, plus floating insertion strings (first symbol
    # of a floating string is not a digit position).
    work = up.replace("CR", "").replace("DB", "")
    int_part, dot, frac = work.partition(".")
    digits = 0
    scale = 0
    for part_idx, part in enumerate((int_part, frac)):
        cnt = 0
        for sym in "$+-":
            n = part.count(sym)
            if n > 1:
                cnt += n - (1 if part_idx == 0 or sym not in int_part else 0)
        cnt += sum(part.count(c) for c in "9Z*")
        if part_idx == 0:
            digits += cnt
        else:
            scale = cnt
            digits += cnt
    # A floating string that started in the integer part continues into frac
    return Picture(raw=raw, category="numeric-edited", size=size, digits=digits, scale=scale, signed=signed, expanded=up)


def storage_size(pic: Picture | None, usage: str, sign_separate: bool) -> int:
    if usage == "INDEX":
        return 4
    if usage == "POINTER":
        return 8
    if usage == "COMP-1":
        return 4
    if usage == "COMP-2":
        return 8
    if pic is None:
        return 0
    if pic.category != "numeric":
        return pic.size
    if usage == "COMP-3":
        return pic.digits // 2 + 1
    if usage in ("COMP", "COMP-5"):
        d = pic.digits
        if d <= 2:
            return 1
        if d <= 4:
            return 2
        if d <= 9:
            return 4
        return 8
    return pic.digits + (1 if sign_separate and pic.signed else 0)
