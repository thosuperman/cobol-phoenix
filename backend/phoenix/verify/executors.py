"""Sandboxed GnuCOBOL executors.

The backend never compiles or runs COBOL itself. It materialises a job
directory and hands it to one of these executors:

* ``docker``  - one throw-away container per job (local development)
* ``queue``   - a file-queue consumed by the runner sidecar (Docker Compose)
* ``disabled``- no runtime; every case is NOT_VERIFIABLE
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CobolCase:
    id: str
    stdin: str


@dataclass
class CobolJob:
    sources: dict[str, str]  # relative path -> content (programs, copybooks, harness)
    compile_units: list[str]  # relative paths compiled (main first)
    copybook_dirs: list[str]
    cases: list[CobolCase]
    free_format: bool = False
    fixed_datetime: str = "2026/01/01 00:00:00"
    timeout_s: float = 5.0


@dataclass
class CobolCaseResult:
    id: str
    stdout: str
    stderr: str
    rc: int | None
    timed_out: bool
    duration_ms: int


@dataclass
class CobolResult:
    available: bool
    executor: str
    cobc_version: str = ""
    compiled: bool = False
    compile_log: str = ""
    compile_command: str = ""
    cases: list[CobolCaseResult] = field(default_factory=list)
    error: str | None = None


class Executor:
    name = "base"

    def available(self) -> tuple[bool, str]:
        raise NotImplementedError

    def run(self, job: CobolJob) -> CobolResult:
        raise NotImplementedError


def _materialise(job: CobolJob, job_dir: Path) -> None:
    src = job_dir / "src"
    for rel, content in job.sources.items():
        p = (src / rel).resolve()
        if not str(p).startswith(str(src.resolve())):
            raise ValueError(f"unsafe source path {rel!r}")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="latin-1")
    spec = {
        "sources": job.compile_units,
        "copybook_dirs": job.copybook_dirs,
        "compile_flags": ["-free"] if job.free_format else [],
        "env": {"COB_CURRENT_DATE": job.fixed_datetime},
        "timeout_s": job.timeout_s,
        "cases": [{"id": c.id, "stdin": c.stdin} for c in job.cases],
    }
    (job_dir / "job.json").write_text(json.dumps(spec))


def _parse_result(executor: str, data: dict) -> CobolResult:
    if "error" in data:
        return CobolResult(available=True, executor=executor, error=data["error"])
    comp = data.get("compile") or {}
    res = CobolResult(
        available=True,
        executor=executor,
        cobc_version=data.get("cobc_version", ""),
        compiled=bool(comp.get("ok")),
        compile_log=(comp.get("stderr", "") + comp.get("stdout", ""))[-8000:],
        compile_command=comp.get("command", ""),
    )
    for c in data.get("cases", []):
        res.cases.append(
            CobolCaseResult(c.get("id"), c.get("stdout", ""), c.get("stderr", ""), c.get("rc"), bool(c.get("timed_out")), int(c.get("duration_ms", 0)))
        )
    return res


class DisabledExecutor(Executor):
    name = "disabled"

    def available(self) -> tuple[bool, str]:
        return False, "COBOL execution is disabled (PHOENIX_COBOL_EXECUTOR=disabled)"

    def run(self, job: CobolJob) -> CobolResult:
        return CobolResult(available=False, executor=self.name, error=self.available()[1])


class DockerExecutor(Executor):
    """Runs each job in a fresh, network-less, resource-limited container."""

    name = "docker"

    def __init__(self, image: str, work_dir: Path, docker_bin: str = "docker", memory: str = "1g", cpus: str = "1.0") -> None:
        self.image = image
        self.work_dir = work_dir
        self.docker_bin = docker_bin
        self.memory = memory
        self.cpus = cpus

    def available(self) -> tuple[bool, str]:
        if shutil.which(self.docker_bin) is None:
            return False, "docker CLI not found"
        try:
            r = subprocess.run([self.docker_bin, "image", "inspect", self.image], capture_output=True, timeout=20, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, f"docker unavailable: {exc}"
        if r.returncode != 0:
            return False, f"runner image {self.image} not found (run `make runner-image`)"
        return True, f"docker image {self.image}"

    def command(self, job_dir: Path) -> list[str]:
        return [
            self.docker_bin, "run", "--rm",
            "--network", "none",
            "--memory", self.memory, "--memory-swap", self.memory,
            "--cpus", self.cpus,
            "--pids-limit", "128",
            "--read-only",
            "--tmpfs", "/tmp:rw,exec,nosuid,size=256m",  # nosec B108 - path inside the sandbox container
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--user", "10001:10001",
            "-v", f"{job_dir}:/job:rw",
            self.image, "oneshot", "/job",
        ]  # fmt: skip

    def run(self, job: CobolJob) -> CobolResult:
        ok, why = self.available()
        if not ok:
            return CobolResult(available=False, executor=self.name, error=why)
        job_dir = self.work_dir / f"job-{uuid.uuid4().hex[:12]}"
        job_dir.mkdir(parents=True)
        job_dir.chmod(0o777)  # container user 10001 must write result.json
        try:
            _materialise(job, job_dir)
            budget = 120 + job.timeout_s * max(1, len(job.cases))
            try:
                r = subprocess.run(self.command(job_dir), capture_output=True, timeout=budget, check=False)
            except subprocess.TimeoutExpired:
                return CobolResult(available=True, executor=self.name, error="sandbox exceeded its overall time budget")
            result_file = job_dir / "result.json"
            if not result_file.exists():
                return CobolResult(
                    available=True, executor=self.name, error=f"runner produced no result (rc={r.returncode}): {r.stderr.decode('latin-1')[-2000:]}"
                )
            return _parse_result(self.name, json.loads(result_file.read_text()))
        finally:
            shutil.rmtree(job_dir, ignore_errors=True)


class QueueExecutor(Executor):
    """Hands jobs to the runner sidecar through a shared directory."""

    name = "queue"

    def __init__(self, queue_dir: Path, wait_s: float = 600.0) -> None:
        self.queue_dir = queue_dir
        self.wait_s = wait_s

    def available(self) -> tuple[bool, str]:
        hb = self.queue_dir / ".runner-heartbeat"
        if not self.queue_dir.exists():
            return False, f"queue directory {self.queue_dir} missing"
        if hb.exists() and time.time() - hb.stat().st_mtime < 30:
            return True, hb.read_text().strip() or "runner sidecar"
        return False, "runner sidecar heartbeat not found (is the runner service up?)"

    def run(self, job: CobolJob) -> CobolResult:
        ok, why = self.available()
        if not ok:
            return CobolResult(available=False, executor=self.name, error=why)
        job_dir = self.queue_dir / f"job-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"
        job_dir.mkdir(parents=True)
        try:
            _materialise(job, job_dir)
            (job_dir / "READY").write_text("")
            deadline = time.time() + self.wait_s
            while time.time() < deadline:
                if (job_dir / "DONE").exists():
                    return _parse_result(self.name, json.loads((job_dir / "result.json").read_text()))
                time.sleep(0.2)
            return CobolResult(available=True, executor=self.name, error="timed out waiting for the runner sidecar")
        finally:
            shutil.rmtree(job_dir, ignore_errors=True)


def make_executor(kind: str, *, image: str, work_dir: Path, queue_dir: Path) -> Executor:
    if kind == "docker":
        return DockerExecutor(image, work_dir)
    if kind == "queue":
        return QueueExecutor(queue_dir)
    return DisabledExecutor()
