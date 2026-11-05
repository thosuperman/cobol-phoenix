# Security

## Reporting a vulnerability

Please report vulnerabilities privately to the maintainers (GitHub security advisory on this repository). Do not
open a public issue for undisclosed vulnerabilities. We aim to respond within 5 working days.

## Threat model and controls

COBOL Phoenix processes untrusted source code. The core rule: **uploaded code is data**.

| Threat | Control |
|---|---|
| Path traversal / absolute paths in uploads or archives | `safe_relpath` rejects `..`, absolute and drive paths, NUL bytes and unusual characters |
| Symlinks, encrypted archives | rejected |
| Zip bombs / oversized imports | max upload size, max uncompressed size, max members, per-file size, compression-ratio limit |
| Binary payloads | allow-listed extensions only; files containing NUL bytes rejected |
| Executing uploaded COBOL on the host | never: only the runner container compiles/runs COBOL — no network, read-only root FS, all capabilities dropped, `no-new-privileges`, memory/CPU/PID limits, RLIMIT_CPU/AS/FSIZE/NOFILE/NPROC and wall-clock timeouts, scrubbed environment |
| Code injection through generated Python | identifiers sanitised (`py_ident`), literals emitted with `repr()`, tested with hostile literals; generated code runs in a subprocess with `-E -s`, a scrubbed environment and a timeout |
| Local file disclosure | local-directory import disabled by default and confined to `PHOENIX_LOCAL_IMPORT_ROOT`; file-serving endpoints resolve paths inside the project directory only |
| SSRF via GitHub import | only `owner/name` accepted; downloads only from `codeload.github.com`; size-capped stream; can be disabled |
| LLM data exposure | optional; the provider receives only the rule facts and cited snippet, never file system access; output labelled advisory and never used as evidence or code |
| Secrets | environment variables only; `.env` git-ignored; `make security` runs bandit and a secret scan |
| Cross-origin abuse | CORS restricted to `PHOENIX_CORS_ORIGINS`; security headers on the frontend |

### Residual risks

* In the Compose `queue` mode the runner shares the job volume across jobs; a malicious program could read other
  pending jobs in that volume (it has no network and no access to the database or backend code). The `docker`
  executor (one container per job, only that job mounted) gives stronger isolation for multi-tenant use.
* The backend has no authentication; deploy it on a trusted network or behind an authenticating proxy.
