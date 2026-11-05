"""COBOL Phoenix sandbox runner.

Compiles and executes COBOL sources with GnuCOBOL inside an isolated container.
The runner never talks to the network and only touches the job directory it is
given plus a private scratch directory.

Modes
-----
``oneshot <job_dir>``  process a single job directory and exit (docker executor)
``serve <queue_dir>``  poll a queue directory for jobs (compose sidecar executor)

Job directory layout (written by the backend)::

    job.json          job description (see ``JobSpec`` below)
    src/...           COBOL sources and copybooks (relative paths only)
    READY             marker created last by the backend (serve mode only)

The runner writes ``result.json`` and then a ``DONE`` marker.
"""

from __future__ import annotations

import json
import os
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

MAX_CASES = 500
MAX_OUTPUT_BYTES = 256 * 1024
COMPILE_TIMEOUT_S = 90
DEFAULT_CASE_TIMEOUT_S = 5
MAX_CASE_TIMEOUT_S = 20


def _safe_rel(path: str) -> str:
    p = Path(path)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(f"unsafe path in job: {path!r}")
    return str(p)


def _limits(cpu_s: int, mem_mb: int):
    def _limit_child() -> None:  # pragma: no cover - runs in child process
        os.setsid()
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s))
        resource.setrlimit(resource.RLIMIT_AS, (mem_mb * 1024 * 1024, mem_mb * 1024 * 1024))
        _common_limits()

    return _limit_child


def _common_limits() -> None:  # pragma: no cover - runs in child process
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024 * 1024, 16 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    try:
        resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
    except (ValueError, OSError):
        pass


def _run(cmd: list[str], cwd: Path, stdin: bytes, timeout: float, env: dict[str, str], cpu_s: int = 10, mem_mb: int = 256) -> dict:
    start = time.monotonic()
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        preexec_fn=_limits(cpu_s, mem_mb),
    )
    timed_out = False
    try:
        out, err = proc.communicate(stdin, timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        out, err = proc.communicate()
    return {
        "rc": proc.returncode,
        "stdout": out[:MAX_OUTPUT_BYTES].decode("latin-1"),
        "stderr": err[:MAX_OUTPUT_BYTES].decode("latin-1"),
        "timed_out": timed_out,
        "duration_ms": int((time.monotonic() - start) * 1000),
    }


def cobc_version() -> str:
    try:
        out = subprocess.run(["cobc", "--version"], capture_output=True, timeout=10, check=False)
        return out.stdout.decode("latin-1").splitlines()[0]
    except Exception as exc:  # noqa: BLE001
        return f"unavailable: {exc}"


def process_job(job_dir: Path) -> dict:
    spec = json.loads((job_dir / "job.json").read_text())
    sources = [_safe_rel(s) for s in spec["sources"]]
    copy_dirs = [_safe_rel(d) for d in spec.get("copybook_dirs", [])]
    cases = spec.get("cases", [])[:MAX_CASES]
    case_timeout = min(float(spec.get("timeout_s", DEFAULT_CASE_TIMEOUT_S)), MAX_CASE_TIMEOUT_S)
    flags = [f for f in spec.get("compile_flags", []) if f in ALLOWED_FLAGS]
    result: dict = {"cobc_version": cobc_version(), "compile": None, "cases": []}

    with tempfile.TemporaryDirectory(prefix="phx-") as tmp:
        work = Path(tmp)
        shutil.copytree(job_dir / "src", work / "src")
        env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": str(work),
            "TMPDIR": str(work),
            "LANG": "C",
        }
        for key, value in spec.get("env", {}).items():
            if key in ALLOWED_ENV:
                env[key] = str(value)
        cmd = ["cobc", "-x", "-o", "prog", *flags]
        for d in copy_dirs:
            cmd += ["-I", f"src/{d}"]
        cmd += [f"src/{s}" for s in sources]
        comp = _run(cmd, work, b"", COMPILE_TIMEOUT_S, env, cpu_s=COMPILE_TIMEOUT_S, mem_mb=2048)
        comp["command"] = " ".join(cmd)
        comp["ok"] = comp["rc"] == 0 and (work / "prog").exists()
        result["compile"] = comp
        if not comp["ok"]:
            return result
        for case in cases:
            run_dir = work / "run" / str(len(result["cases"]))
            run_dir.mkdir(parents=True)
            for name, content in case.get("files", {}).items():
                (run_dir / _safe_rel(name)).write_text(content, encoding="latin-1")
            res = _run([str(work / "prog")], run_dir, case.get("stdin", "").encode("latin-1"), case_timeout, env)
            res["id"] = case.get("id")
            res["files_out"] = {}
            for name in case.get("collect_files", []):
                fp = run_dir / _safe_rel(name)
                if fp.exists():
                    res["files_out"][name] = fp.read_bytes()[:MAX_OUTPUT_BYTES].decode("latin-1")
            result["cases"].append(res)
    return result


ALLOWED_FLAGS = {"-free", "-fixed", "-std=default", "-std=ibm", "-std=mf", "-std=cobol2014", "-O", "-O2"}
ALLOWED_ENV = {"COB_CURRENT_DATE", "COB_SET_DEBUG"}


def handle(job_dir: Path) -> None:
    try:
        result = process_job(job_dir)
    except Exception as exc:  # noqa: BLE001
        result = {"error": f"{type(exc).__name__}: {exc}"}
    tmp = job_dir / "result.json.tmp"
    tmp.write_text(json.dumps(result))
    tmp.rename(job_dir / "result.json")
    (job_dir / "DONE").write_text("")


def serve(queue: Path) -> None:
    version = cobc_version()
    print(f"phoenix-runner serving {queue} ({version})", flush=True)
    last_beat = 0.0
    while True:
        if time.time() - last_beat > 5:
            try:
                (queue / ".runner-heartbeat").write_text(f"runner sidecar: {version}")
                last_beat = time.time()
            except OSError:
                pass
        for job in sorted(queue.iterdir()) if queue.exists() else []:
            if (job / "READY").exists() and not (job / "DONE").exists() and not (job / "CLAIMED").exists():
                (job / "CLAIMED").write_text(str(os.getpid()))
                handle(job)
        time.sleep(0.25)


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "oneshot":
        handle(Path(argv[1]))
        return 0
    if len(argv) == 2 and argv[0] == "serve":
        serve(Path(argv[1]))
        return 0
    if argv == ["version"]:
        print(cobc_version())
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
