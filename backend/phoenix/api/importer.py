"""Secure source import: individual files, ZIP archives, GitHub archives, local directories.

Uploaded content is treated strictly as data: nothing is executed, archives are
validated before extraction and only allow-listed text files are stored.
"""

from __future__ import annotations

import io
import re
import stat
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from ..cobol.project import SOURCE_EXTS
from ..config import Settings

EXTRA_EXTS = {".json", ".md", ".txt", ".jcl"}  # kept for context (fixtures, docs, licenses)
LICENSE_NAMES = {"license", "license.md", "license.txt", "copying", "licence", "licence.md"}
_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9._@+\- ]{1,128}$")
SKIP_DIRS = {".git", "__MACOSX", "node_modules", ".github", ".svn"}


class ImportError_(ValueError):
    """Raised for rejected imports (message is safe to show to users)."""


@dataclass
class ImportResult:
    files: dict[str, str] = field(default_factory=dict)  # relative path -> text
    skipped: list[dict] = field(default_factory=list)
    license_text: str | None = None
    license_name: str = ""
    root_prefix: str = ""

    def report(self) -> dict:
        return {"stored": len(self.files), "skipped": self.skipped[:200], "skipped_count": len(self.skipped), "license": self.license_name}


def safe_relpath(name: str) -> str:
    """Normalise an archive member / upload name to a safe relative POSIX path."""
    if "\x00" in name:
        raise ImportError_("file name contains NUL byte")
    name = name.replace("\\", "/")
    if name.startswith("/") or re.match(r"^[A-Za-z]:", name):
        raise ImportError_(f"absolute path not allowed: {name!r}")
    parts = [p for p in PurePosixPath(name).parts if p not in ("", ".")]
    if not parts:
        raise ImportError_("empty path")
    for p in parts:
        if p == "..":
            raise ImportError_(f"path traversal not allowed: {name!r}")
        if not _SAFE_SEGMENT.match(p):
            raise ImportError_(f"unsupported characters in path segment {p!r}")
    return "/".join(parts)


def detect_license(text: str) -> str:
    t = text[:4000].lower()
    for key, name in (
        ("mit license", "MIT"),
        ("permission is hereby granted, free of charge", "MIT"),
        ("apache license", "Apache-2.0"),
        ("gnu general public license", "GPL"),
        ("gnu lesser general public license", "LGPL"),
        ("mozilla public license", "MPL-2.0"),
        ("bsd", "BSD"),
        ("unlicense", "Unlicense"),
        ("creative commons", "CC"),
    ):
        if key in t:
            return name
    return "Custom (see LICENSE)"


def _decode(data: bytes, name: str, settings: Settings) -> str:
    if len(data) > settings.max_file_kb * 1024:
        raise ImportError_(f"{name}: file larger than {settings.max_file_kb} KB")
    if b"\x00" in data:
        raise ImportError_(f"{name}: binary content is not accepted")
    return data.decode("utf-8") if _is_utf8(data) else data.decode("latin-1")


def _is_utf8(data: bytes) -> bool:
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _accept(rel: str, res: ImportResult) -> bool:
    p = PurePosixPath(rel)
    if any(part in SKIP_DIRS for part in p.parts):
        res.skipped.append({"path": rel, "reason": "ignored directory"})
        return False
    ext = p.suffix.lower()
    if p.name.lower() in LICENSE_NAMES:
        return True
    if ext in SOURCE_EXTS or ext in EXTRA_EXTS:
        return True
    res.skipped.append({"path": rel, "reason": f"extension {ext or '(none)'} not imported"})
    return False


def _store(res: ImportResult, rel: str, text: str, settings: Settings) -> None:
    if len(res.files) >= settings.max_files:
        raise ImportError_(f"too many files (limit {settings.max_files})")
    if PurePosixPath(rel).name.lower() in LICENSE_NAMES and (res.license_text is None or rel.count("/") < 1):
        res.license_text = text
        res.license_name = detect_license(text)
    res.files[rel] = text


def import_uploads(items: list[tuple[str, bytes]], settings: Settings) -> ImportResult:
    res = ImportResult()
    total = 0
    for name, data in items:
        rel = safe_relpath(PurePosixPath(name.replace("\\", "/")).name)
        total += len(data)
        if total > settings.max_upload_mb * 1024 * 1024:
            raise ImportError_(f"upload exceeds {settings.max_upload_mb} MB")
        if not _accept(rel, res):
            continue
        _store(res, rel, _decode(data, rel, settings), settings)
    if not any(PurePosixPath(p).suffix.lower() in SOURCE_EXTS for p in res.files):
        raise ImportError_("no COBOL source files (.cob, .cbl, .cpy, ...) found")
    return res


def import_zip(data: bytes, settings: Settings) -> ImportResult:
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise ImportError_(f"archive exceeds {settings.max_upload_mb} MB")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ImportError_("not a valid ZIP archive")
    infos = zf.infolist()
    if len(infos) > settings.max_files * 4:
        raise ImportError_("archive contains too many entries")
    total = 0
    res = ImportResult()
    names = []
    for info in infos:
        mode = info.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise ImportError_(f"symbolic links are not allowed: {info.filename!r}")
        if info.flag_bits & 0x1:
            raise ImportError_("encrypted archives are not supported")
        rel = safe_relpath(info.filename)
        if info.is_dir():
            continue
        total += info.file_size
        if total > settings.max_uncompressed_mb * 1024 * 1024:
            raise ImportError_(f"archive expands beyond {settings.max_uncompressed_mb} MB")
        if info.compress_size and info.file_size / max(1, info.compress_size) > settings.max_compression_ratio:
            raise ImportError_(f"suspicious compression ratio for {rel!r}")
        names.append((info, rel))
    # strip a single common top-level folder (GitHub archives)
    tops = {rel.split("/", 1)[0] for _, rel in names if "/" in rel}
    prefix = ""
    if len(tops) == 1 and all("/" in rel for _, rel in names):
        prefix = tops.pop() + "/"
    res.root_prefix = prefix
    for info, rel in names:
        rel2 = rel[len(prefix) :] if prefix and rel.startswith(prefix) else rel
        if not _accept(rel2, res):
            continue
        with zf.open(info) as fh:
            content = fh.read(settings.max_file_kb * 1024 + 1)
        try:
            _store(res, rel2, _decode(content, rel2, settings), settings)
        except ImportError_ as exc:
            res.skipped.append({"path": rel2, "reason": str(exc)})
    if not any(PurePosixPath(p).suffix.lower() in SOURCE_EXTS for p in res.files):
        raise ImportError_("no COBOL source files (.cob, .cbl, .cpy, ...) found in archive")
    return res


_REPO_RE = re.compile(r"^(?:https?://github\.com/)?([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9._-]{1,100}?)(?:\.git)?/?$")
_REF_RE = re.compile(r"^[A-Za-z0-9._/-]{1,100}$")


def parse_github_repo(repo: str) -> tuple[str, str]:
    m = _REPO_RE.match(repo.strip())
    if not m:
        raise ImportError_("expected 'owner/name' or https://github.com/owner/name")
    return m.group(1), m.group(2)


def github_archive_url(owner: str, name: str, ref: str) -> str:
    if not _REF_RE.match(ref) or ".." in ref:
        raise ImportError_("invalid git ref")
    return f"https://codeload.github.com/{owner}/{name}/zip/{ref}"


def import_local_dir(path: str, settings: Settings) -> ImportResult:
    if not settings.allow_local_import or settings.local_import_root is None:
        raise ImportError_("local directory import is disabled (set PHOENIX_ALLOW_LOCAL_IMPORT and PHOENIX_LOCAL_IMPORT_ROOT)")
    root = settings.local_import_root.resolve()
    target = (root / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    if target != root and root not in target.parents:
        raise ImportError_("directory is outside the allowed import root")
    if not target.is_dir():
        raise ImportError_("directory not found")
    res = ImportResult()
    total = 0
    for p in sorted(target.rglob("*")):
        if p.is_symlink() or not p.is_file():
            continue
        rel = safe_relpath(str(p.relative_to(target)))
        if not _accept(rel, res):
            continue
        total += p.stat().st_size
        if total > settings.max_uncompressed_mb * 1024 * 1024:
            raise ImportError_("directory too large")
        _store(res, rel, _decode(p.read_bytes(), rel, settings), settings)
    if not any(PurePosixPath(p).suffix.lower() in SOURCE_EXTS for p in res.files):
        raise ImportError_("no COBOL source files found in directory")
    return res
