# Design — product level

See `.kiro/steering/architecture.md` for the component diagram.

## Key decisions
| Decision | Rationale |
|---|---|
| Deterministic parser for a documented subset instead of an LLM | Reproducibility and auditable evidence |
| Byte-level runtime (`phoenix_runtime`) | Faithful REDEFINES, group MOVE, ACCEPT/DISPLAY and CALL BY REFERENCE |
| Generic COBOL *harness* for LINKAGE programs | Lets any callable subprogram be differentially tested: the harness ACCEPTs each USING parameter, CALLs the program and DISPLAYs every parameter |
| File-queue sidecar executor in Compose | Sandbox needs no Docker socket and no network |
| SQLite default, SQLAlchemy models portable to PostgreSQL | Zero-cost local start |
| Next.js frontend talking only to the backend API | No fake data; one source of truth |

## Pages
Landing, Dashboard, Import, Project overview, Source explorer, Dependency graph, Business
rules, Generation workspace, Generated code viewer, Verification dashboard, Export/report.
