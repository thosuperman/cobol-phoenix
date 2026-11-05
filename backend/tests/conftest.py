from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "backend" / "phoenix" / "samples" / "phoenix-mutual"
CORPUS = Path(os.environ.get("PHOENIX_CORPUS_DIR", ROOT / "corpus" / "repos"))
RUNNER_IMAGE = os.environ.get("PHOENIX_RUNNER_IMAGE", "cobol-phoenix-runner:latest")


def sample_sources() -> dict[str, str]:
    from phoenix.cobol.project import SOURCE_EXTS

    return {str(p.relative_to(SAMPLE)): p.read_text() for p in SAMPLE.rglob("*") if p.suffix.lower() in SOURCE_EXTS}


def docker_runner_available() -> bool:
    if os.environ.get("PHOENIX_COBOL_EXECUTOR", "docker") != "docker" or shutil.which("docker") is None:
        return False
    try:
        return subprocess.run(["docker", "image", "inspect", RUNNER_IMAGE], capture_output=True, timeout=20, check=False).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def pytest_collection_modifyitems(config, items):
    has_cobol = docker_runner_available()
    for item in items:
        if "cobol" in item.keywords and not has_cobol:
            item.add_marker(pytest.mark.skip(reason=f"GnuCOBOL sandbox unavailable (docker image {RUNNER_IMAGE}); run `make runner-image`"))
        if "corpus" in item.keywords and not CORPUS.exists():
            item.add_marker(pytest.mark.skip(reason=f"external corpus not fetched ({CORPUS}); run scripts/fetch-corpus.sh"))


@pytest.fixture
def sample_parse():
    from phoenix.cobol.project import parse_project

    return parse_project(sample_sources())


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    monkeypatch.setenv("PHOENIX_DATA_DIR", str(tmp_path / "data"))
    from phoenix import config, db

    config.get_settings.cache_clear()
    db.reset_for_tests()
    import importlib

    import phoenix.api.main as main
    import phoenix.services as services

    services._parse_cache.clear()
    importlib.reload(main)
    from fastapi.testclient import TestClient

    with TestClient(main.app) as client:
        yield client
    db.reset_for_tests()
    config.get_settings.cache_clear()
