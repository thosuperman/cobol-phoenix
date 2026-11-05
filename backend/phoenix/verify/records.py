"""Encode/decode COBOL records using the IR layout and the shared runtime."""

from __future__ import annotations

import itertools
import re
from decimal import Decimal

from ..cobol import ir
from ..codegen import phoenix_runtime as rt

_SUB_RE = re.compile(r"^([A-Z0-9-]+)(?:\(([\d ,]+)\))?$")


def make_field(it: ir.DataItem, region: rt.Region) -> rt.Field:
    common = (region, it.offset, it.size, it.name, tuple(it.dims), it.occurs)
    kw = {"filler": it.is_filler, "redefines": bool(it.redefines)}
    pic = it.picture
    if it.children or pic is None:
        return rt.Group(*common, **kw)
    if pic.category == "numeric":
        num = {"digits": pic.digits, "scale": pic.scale, "signed": pic.signed}
        if it.usage == "COMP-3":
            return rt.Packed(*common, **num, **kw)
        if it.usage in ("COMP", "COMP-5", "INDEX"):
            return rt.Binary(*common, **num, native=it.usage != "COMP", **kw)
        return rt.Numeric(*common, **num, sign_separate=it.sign_separate, sign_leading=it.sign_leading, **kw)
    if pic.category == "numeric-edited":
        return rt.Edited(*common, digits=pic.digits, scale=pic.scale, signed=pic.signed, picture=pic.expanded, blank_when_zero=it.blank_when_zero, **kw)
    if pic.category == "alphanumeric-edited":
        return rt.AlnumEdited(*common, picture=pic.expanded, **kw)
    return rt.Alnum(*common, justified=it.justified, **kw)


class RecordCodec:
    def __init__(self, root: ir.DataItem) -> None:
        self.root = root
        self.region = rt.Region(root.name, root.size)
        self.fields: dict[str, rt.Field] = {}
        self.items: dict[str, ir.DataItem] = {}
        self.by_name: dict[str, str] = {}
        stack = [root]
        while stack:
            it = stack.pop()
            f = make_field(it, self.region)
            self.fields[it.id] = f
            self.items[it.id] = it
            if not it.is_filler:
                self.by_name.setdefault(it.name, it.id)
            stack.extend(it.children)
        for iid, f in self.fields.items():
            f.children = [self.fields[c.id] for c in self.items[iid].children]

    def reset(self) -> None:
        self.region.buf[:] = b" " * self.root.size
        rt.initialize(self.fields[self.root.id], fillers=True)

    def field(self, key: str) -> rt.Field:
        """Resolve 'NAME' or 'NAME(1)' / 'NAME(1, 2)'."""
        m = _SUB_RE.match(key.upper().replace(" ", ""))
        if not m:
            raise KeyError(key)
        name, subs = m.group(1), m.group(2)
        iid = self.by_name.get(name)
        if iid is None:
            raise KeyError(f"{key}: no such field in {self.root.name}")
        f = self.fields[iid]
        if subs:
            return f.at(*[int(x) for x in subs.split(",")])
        return f

    def encode(self, values: dict[str, object]) -> str:
        self.reset()
        for key, value in values.items():
            f = self.field(key)
            if isinstance(f, rt.NumericBase) and not isinstance(f, rt.Edited):
                if isinstance(value, str) and value.startswith("raw:"):
                    f.set_raw(value[4:].encode("latin-1").ljust(f.size)[: f.size])
                else:
                    f.store(Decimal(str(value)))
            else:
                rt.move(str(value), f)
        return self.region.buf.decode("latin-1")

    def decode(self, text: str) -> list[dict]:
        """Return every non-FILLER elementary occurrence with raw text and value."""
        self.region.buf[:] = text.encode("latin-1", "replace")[: self.root.size].ljust(self.root.size, b" ")
        out = []
        for iid, it in self.items.items():
            if it.children or it.is_filler:
                continue
            f = self.fields[iid]
            ranges = [range(1, n + 1) for _, n in it.dims]
            for subs in itertools.product(*ranges) if ranges else [()]:
                view = f.at(*subs) if subs else f
                raw = view.text()
                entry = {
                    "field": it.name + (f"({', '.join(map(str, subs))})" if subs else ""),
                    "offset": view._pos(),
                    "size": it.size,
                    "raw": raw,
                    "kind": view.kind,
                    "loc": f"{it.loc.file}:{it.loc.line}",
                }
                if isinstance(view, rt.NumericBase) and not isinstance(view, rt.Edited):
                    entry["value"] = str(view.value) if rt.is_numeric_class(view) or not isinstance(view, rt.Numeric) else None
                    entry["scale"] = view.scale
                out.append(entry)
        out.sort(key=lambda e: e["offset"])
        return out
