# Feature list

| # | Feature | Where to see it |
|---|---|---|
| 1 | Secure import: files, ZIP (traversal/symlink/bomb/size checks), GitHub at pinned ref, local dir (opt-in) | Import page |
| 2 | License detection on import, shown on the project header | Project header |
| 3 | Deterministic parser for a documented subset, fixed + free format auto-detection | Overview → diagnostics |
| 4 | Unsupported constructs reported with file:line, never silently ignored | Overview → Unsupported constructs |
| 5 | Documented complexity heuristic per program and project | Overview → Programs |
| 6 | Dependency graph (COPY, CALL, PERFORM, record usage) with source-linked inspector | Dependencies |
| 7 | Source explorer with highlighting, outline and deep links | Source |
| 8 | Business rules from paragraphs and annotations, with inputs/outputs/conditions/calculations/decision tables | Business rules |
| 9 | Deterministic explanation; optional provider-agnostic LLM explanation labelled advisory | Business rules → Explain |
| 10 | Python/FastAPI project generation with Pydantic schemas from PICTURE clauses | Generate |
| 11 | Python ↔ COBOL traceability split view | Generated code viewer |
| 12 | ZIP download of the generated project (tests, README, Dockerfile, traceability) | Generate / Export |
| 13 | Differential verification vs sandboxed GnuCOBOL; field-level diffs; side-by-side raw outputs | Verify |
| 14 | IR-derived boundary values, edge values, seeded random cases, coverage-guided placement | Verify → cases |
| 15 | Statement coverage and rule verification status | Verify, Business rules |
| 16 | Mutation analysis (test-suite strength) | Verify → Mutation analysis |
| 17 | Fault injection demo | Generate → Inject a deliberate fault |
| 18 | Editable fixtures (`phoenix-fixtures.json`) | Verify → Test fixtures |
| 19 | Exports: migration report, verification report (MD/JSON), rules (MD/JSON), graph, traceability | Export |
| 20 | Docker Compose deployment with network-less sandbox; Alembic migrations | `docker compose up --build` |
