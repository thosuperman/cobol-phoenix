# Changelog

## 1.0.0 — 2026-11-05 (Kiroween 2026 submission)

### Added
- Deterministic COBOL front end: fixed/free format lexer, COPY … REPLACING preprocessor, recursive-descent parser, normalized IR with source locations, byte-accurate data layout.
- Analysis: dependency graph (COPY, CALL, PERFORM, record usage), documented complexity heuristic, business-rule extraction from paragraphs and source annotations, unsupported-construct reporting.
- Python generation: one class per program on the vendored `phoenix_runtime` (Decimal, COBOL MOVE/editing/sign/rounding semantics), FastAPI app, Pydantic schemas from PICTURE clauses, CLI, tests, README, Dockerfile, `traceability.json`.
- Differential verification: GnuCOBOL sandbox runner (docker / queue executors), LINKAGE harness generation, IR-derived boundary/edge/random cases with coverage-guided placement, field-level comparison, statement coverage, rule status, mutation analysis and fault injection.
- FastAPI backend with secure import (files, ZIP, GitHub, local), SQLite/PostgreSQL persistence, Alembic, report exports.
- Next.js workspace: landing, dashboard, import, overview, source explorer, dependency graph, rules, generation, code/traceability viewer, verification dashboard, exports.
- Original Phoenix Mutual sample project with GnuCOBOL-captured expected output; external corpus manifest and regression tests.
- Docker Compose deployment (frontend, backend, network-less runner), optional AWS single-host guide.
- Kiro steering, specs and v1 hooks.

### Fixed during development (found by differential testing / hooks)
- Floating-insertion editing when significant high-order digits are truncated.
- ACCEPT at end of input moves spaces.
- Unused import in generated batch-mode schemas.
