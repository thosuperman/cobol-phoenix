import io
import stat
import zipfile

import pytest

from phoenix.api.importer import ImportError_, import_local_dir, import_uploads, import_zip, parse_github_repo, safe_relpath
from phoenix.config import Settings

S = Settings(max_upload_mb=1, max_uncompressed_mb=2, max_files=10, max_file_kb=256)
COB = b"       IDENTIFICATION DIVISION.\n       PROGRAM-ID. A.\n"


def make_zip(entries, symlink=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries:
            zf.writestr(name, data)
        if symlink:
            info = zipfile.ZipInfo(symlink)
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            zf.writestr(info, "/etc/passwd")
    return buf.getvalue()


@pytest.mark.parametrize("name", ["../evil.cob", "a/../../evil.cob", "/etc/passwd", "C:/x.cob", "a\x00b.cob"])
def test_path_traversal_rejected(name):
    with pytest.raises(ImportError_):
        safe_relpath(name)


def test_zip_with_traversal_rejected():
    with pytest.raises(ImportError_):
        import_zip(make_zip([("ok.cob", COB), ("../../x.cob", COB)]), S)


def test_zip_symlink_rejected():
    with pytest.raises(ImportError_, match="symbolic"):
        import_zip(make_zip([("ok.cob", COB)], symlink="link.cob"), S)


def test_zip_bomb_ratio_and_size_rejected():
    with pytest.raises(ImportError_):
        import_zip(make_zip([("ok.cob", COB), ("big.cob", b" " * (3 * 1024 * 1024))]), S)


def test_zip_strips_top_folder_and_skips_other_files():
    res = import_zip(
        make_zip(
            [
                ("repo-main/src/A.cob", COB),
                ("repo-main/bin/tool.exe", b"MZ"),
                ("repo-main/LICENSE", b"MIT License\nPermission is hereby granted, free of charge"),
            ]
        ),
        S,
    )
    assert set(res.files) == {"src/A.cob", "LICENSE"}
    assert res.license_name == "MIT"
    assert any(s["path"] == "bin/tool.exe" for s in res.skipped)


def test_binary_and_non_cobol_uploads_rejected():
    with pytest.raises(ImportError_):
        import_uploads([("a.cob", b"\x00\x01binary")], S)
    with pytest.raises(ImportError_, match="no COBOL"):
        import_uploads([("notes.txt", b"hello")], S)


def test_too_many_files_rejected():
    with pytest.raises(ImportError_, match="too many"):
        import_zip(make_zip([(f"f{i}.cob", COB) for i in range(20)]), S)


def test_local_import_disabled_by_default(tmp_path):
    with pytest.raises(ImportError_, match="disabled"):
        import_local_dir(str(tmp_path), S)


def test_local_import_confined_to_root(tmp_path):
    (tmp_path / "root").mkdir()
    s = Settings(allow_local_import=True, local_import_root=tmp_path / "root")
    with pytest.raises(ImportError_, match="outside"):
        import_local_dir(str(tmp_path), s)


@pytest.mark.parametrize("repo", ["mudasin1/COBOL_Sample_March_2026", "https://github.com/achalc/cobol-bank-demo"])
def test_github_repo_parsing(repo):
    owner, name = parse_github_repo(repo)
    assert owner and name


@pytest.mark.parametrize("repo", ["https://evil.example/x/y", "a/b/c", "../x", "owner/"])
def test_github_repo_parsing_rejects(repo):
    with pytest.raises(ImportError_):
        parse_github_repo(repo)


def test_cors_is_restricted():
    from phoenix.api.main import app

    mw = next(m for m in app.user_middleware if "CORS" in str(m.cls))
    assert "*" not in mw.kwargs["allow_origins"]
