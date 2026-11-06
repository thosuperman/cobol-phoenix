"""Regenerate the bundled sample services and run each generated project's own tests.

Used by the Kiro `validate-generated-code` hook and `make validate-generated`.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from phoenix.cobol.project import SOURCE_EXTS, parse_project  # noqa: E402
from phoenix.codegen.project_gen import generate_project, write_project  # noqa: E402

SAMPLE = ROOT / "backend" / "phoenix" / "samples" / "phoenix-mutual"


def main(out: Path) -> int:
    raw = {str(p.relative_to(SAMPLE)): p.read_text() for p in SAMPLE.rglob("*") if p.suffix.lower() in SOURCE_EXTS}
    pp = parse_project(raw)
    fixtures = json.loads((SAMPLE / "phoenix-fixtures.json").read_text())
    status = 0
    for entry in ("RATEENG", "PREMCALC"):
        gp = generate_project(pp, entry, f"{entry.lower()}-service", fixtures=fixtures.get(entry, []))
        target = out / entry.lower()
        write_project(gp, target)
        lint = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "--select", "F,E9", "app"],
            cwd=target,
            capture_output=True,
            text=True,
        )
        tests = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
            cwd=target,
            capture_output=True,
            text=True,
        )
        print(
            f"{entry}: {len(gp.traceability)} statements traced, unsupported={len(gp.unsupported)}, ruff={'ok' if lint.returncode == 0 else 'FAIL'}, tests={'ok' if tests.returncode == 0 else 'FAIL'}"
        )
        if lint.returncode or tests.returncode:
            print(lint.stdout, tests.stdout[-2000:], tests.stderr[-2000:])
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/phoenix-validate")))
