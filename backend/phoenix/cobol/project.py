"""Project-level front end: classify files, resolve copybooks, parse programs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from . import ir
from .diagnostics import Diagnostic, Severity
from .lexer import SourceFormat, detect_format, tokenize
from .parser import Parser
from .preprocessor import CopyEvent, expand_copies

PROGRAM_EXTS = {".cob", ".cbl", ".cobol", ".pco", ".cob85"}
COPYBOOK_EXTS = {".cpy", ".copy", ".cbk", ".inc", ".cpb"}
SOURCE_EXTS = PROGRAM_EXTS | COPYBOOK_EXTS

_PROGRAM_RE = re.compile(r"^.{0,7}\s*(IDENTIFICATION|ID)\s+DIVISION", re.I | re.M)
_PROGRAM_ID_RE = re.compile(r"PROGRAM-ID\s*\.\s*['\"]?([A-Za-z0-9-_]+)", re.I)


@dataclass
class SourceFile:
    path: str  # project-relative posix path
    text: str
    kind: str = "unknown"  # program | copybook | other
    format: str = "fixed"
    lines: int = 0


@dataclass
class ParsedProgram:
    program: ir.Program
    copies: list[CopyEvent]
    diagnostics: list[Diagnostic]
    unsupported: list[dict]


@dataclass
class ProjectParse:
    files: list[SourceFile]
    programs: list[ParsedProgram] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def program(self, program_id: str) -> ParsedProgram | None:
        pid = program_id.upper()
        return next((p for p in self.programs if p.program.program_id == pid), None)


def classify(path: str, text: str) -> str:
    ext = PurePosixPath(path).suffix.lower()
    if _PROGRAM_RE.search(text):
        return "program"
    if ext in COPYBOOK_EXTS or ext in PROGRAM_EXTS:
        return "copybook"
    return "other"


class CopyResolver:
    def __init__(self, files: list[SourceFile], format_override: SourceFormat | None = None) -> None:
        self.by_name: dict[str, SourceFile] = {}
        self.by_stem: dict[str, SourceFile] = {}
        self.format_override = format_override
        # copybooks win over programs with the same stem
        for f in sorted(files, key=lambda f: 0 if f.kind == "copybook" else 1):
            p = PurePosixPath(f.path)
            self.by_name.setdefault(p.name.upper(), f)
            self.by_stem.setdefault(p.stem.upper(), f)

    def __call__(self, name: str):
        key = name.strip("'\"").upper()
        f = self.by_name.get(key) or self.by_stem.get(PurePosixPath(key).stem) or self.by_stem.get(key)
        if f is None:
            return None
        fmt = self.format_override or SourceFormat(f.format)
        return f.path, f.text, fmt


def load_files(raw: dict[str, str], format_override: str | None = None) -> list[SourceFile]:
    files = []
    for path in sorted(raw):
        text = raw[path]
        kind = classify(path, text)
        fmt = format_override or detect_format(text).value
        files.append(SourceFile(path=path, text=text, kind=kind, format=fmt, lines=text.count("\n") + (0 if text.endswith("\n") else 1)))
    return files


def parse_project(raw: dict[str, str], format_override: str | None = None) -> ProjectParse:
    files = load_files(raw, format_override)
    override = SourceFormat(format_override) if format_override else None
    resolver = CopyResolver(files, override)
    result = ProjectParse(files=files)
    seen_ids: dict[str, str] = {}
    for f in files:
        if f.kind != "program":
            continue
        toks, diags, fmt = tokenize(f.path, f.text, SourceFormat(f.format))
        pp = expand_copies(f.path, toks, resolver)
        parser = Parser(pp.tokens, f.path)
        programs = parser.parse_programs()
        all_diags = diags + pp.diagnostics + parser.diagnostics
        if not programs:
            result.diagnostics.append(Diagnostic(Severity.ERROR, "PRJ001", "no program could be parsed", f.path, 1))
        for prog in programs:
            prog.source_format = fmt.value
            prog.copybooks = [
                {"name": c.name, "file": c.file, "line": c.line, "resolved": c.resolved, "replacing": c.replacing}
                for c in pp.copies
                if c.file == f.path or c.file in {cc.resolved for cc in pp.copies}
            ]
            if prog.program_id in seen_ids:
                all_diags.append(
                    Diagnostic(Severity.WARNING, "PRJ002", f"PROGRAM-ID {prog.program_id} also defined in {seen_ids[prog.program_id]}", f.path, prog.loc.line)
                )
            seen_ids.setdefault(prog.program_id, f.path)
            unsupported = [u for u in parser.unsupported if prog.loc.line <= u["line"] <= prog.loc.end_line or u["file"] != f.path]
            result.programs.append(ParsedProgram(prog, pp.copies, all_diags, unsupported))
    return result
