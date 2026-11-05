---
inclusion: always
---

# Security model

- Uploaded code is **data**. The backend never executes it. Only the sandbox runner compiles
  and runs COBOL, in a container with `network_mode: none`, read-only root FS, dropped
  capabilities, `no-new-privileges`, memory/CPU/PID limits, per-process rlimits and timeouts.
- ZIP import: max archive size, max member count, max uncompressed size, compression ratio
  check, no absolute paths, no `..`, no symlinks, allow-listed extensions only.
- Generated Python is produced from sanitised identifiers and `repr()`-escaped literals; it
  runs in a subprocess with `python -I`, a timeout and a scrubbed environment.
- Secrets only from environment variables (`.env` is git-ignored; `.env.example` documents keys).
- LLM providers receive only the snippet being explained, never file system access.
- CORS restricted to `PHOENIX_CORS_ORIGINS`.
