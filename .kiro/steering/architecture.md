---
inclusion: always
---

# Architecture

```
frontend/ (Next.js, TypeScript, Tailwind)  ──HTTP /api──▶  backend/ (FastAPI)
                                                            │
                         ┌──────────────────────────────────┼─────────────────────────┐
                         ▼                                  ▼                         ▼
               phoenix.cobol (lexer, preprocessor,   phoenix.codegen           phoenix.verify
               parser, IR)                           (deterministic Python     (test generation, sandbox
               phoenix.analysis (deps, complexity,    project generator +       executors, comparison,
               rules)                                 phoenix_runtime)          mutation analysis)
                                                                                     │
                                                                     file queue / docker run
                                                                                     ▼
                                                                    runner/ (GnuCOBOL sandbox,
                                                                    no network, rlimits)
```

## Module boundaries

- `phoenix.cobol` knows nothing about Python generation. Its output is the IR
  (`phoenix.cobol.ir`), a JSON-serialisable dataclass tree with source locations.
- `phoenix.analysis` consumes IR only.
- `phoenix.codegen` consumes IR only and emits a self-contained Python project that
  depends on FastAPI/Pydantic plus the vendored `phoenix_runtime` module.
- `phoenix.verify` consumes IR + generated project + an executor. Executors:
  `queue` (compose sidecar), `docker` (one container per job), `disabled`.
- `phoenix.api` (FastAPI) orchestrates; persistence via SQLAlchemy (SQLite default,
  PostgreSQL-compatible models, Alembic migrations).

## Data flow

Projects are imported into `DATA_DIR/projects/<id>/src`. Analysis results are stored as
JSON in the DB. Generated projects live in `DATA_DIR/generated/<generation_id>/`.
Verification jobs are materialised in `DATA_DIR/jobs/<job_id>/`.
