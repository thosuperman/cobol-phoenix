# Architecture

## Components

| Component | Path | Responsibility |
|---|---|---|
| Lexer | `backend/phoenix/cobol/lexer.py` | Fixed/free format detection, columns 1-6/7/8-72, continuation literals, pseudo-text, `*>` comments; every token carries file + line |
| Preprocessor | `backend/phoenix/cobol/preprocessor.py` | `COPY name [REPLACING …]`, recursion/cycle detection; copybook tokens keep the copybook's own coordinates |
| Parser | `backend/phoenix/cobol/parser.py` | Recursive descent → IR; data layout (offsets, sizes, OCCURS strides, REDEFINES); statements outside the subset become `Unsupported` nodes |
| IR | `backend/phoenix/cobol/ir.py` | Generator-independent dataclasses with `Loc(file, line, end_line)` |
| Analysis | `backend/phoenix/analysis/` | Data flow (reads/writes), dependency graph, complexity, rule extraction |
| Generator | `backend/phoenix/codegen/` | `program_gen.py` (IR → Python class per program), `project_gen.py` (FastAPI project), `phoenix_runtime.py` (vendored COBOL semantics) |
| Verification | `backend/phoenix/verify/` | Test generation, COBOL harness, executors, record codec, comparison, mutation analysis |
| API | `backend/phoenix/api/`, `services.py` | FastAPI routes, secure importer, orchestration, background verification workers |
| Runner | `runner/` | GnuCOBOL 3.2 container; compiles and runs jobs with rlimits and timeouts |
| Frontend | `frontend/` | Next.js 16 / React 19 / Tailwind 4 workspace |

## Generated program shape

Each COBOL program becomes a `rt.Program` subclass:

* every 01/77 record is a `rt.Region` (a `bytearray`); every data item is a typed view (`Numeric`, `Packed`,
  `Binary`, `Edited`, `Alnum`, `Group`) at a fixed offset, so REDEFINES and group moves are byte-exact;
* every paragraph becomes a method; `PARAGRAPHS` order drives fall-through, `perform(start, end)` implements
  PERFORM/THRU, `GoTo` exceptions implement GO TO inside the active range;
* LINKAGE regions are rebound to the caller's buffers on CALL (BY REFERENCE);
* every statement is preceded by a `# file:line: original text` comment and recorded in `traceability.json`.

## Verification flow

```
fixtures ──► generated Python (line trace) ──► fixture coverage
     │                                              │
     └─► IR candidates (boundaries, 88s, WHEN, edges) ─► coverage-guided placement ─► cases
cases ──► COBOL harness + sources ──► runner (GnuCOBOL) ──► stdout per case
cases ──► generated app.cli (subprocess, trace) ──────────► stdout per case + executed lines
both  ──► record codec ──► field-level diff ──► VERIFIED / FAILED / NOT_VERIFIABLE / UNSUPPORTED
cases ──► mutants of the generated code ──► killed / survived
```

For programs with a LINKAGE SECTION a COBOL harness is generated: it ACCEPTs one line per USING parameter,
CALLs the program and DISPLAYs every parameter, then `*PHOENIX-END*`. The generated `app/cli.py --mode harness`
implements the same protocol, so both sides receive identical bytes.

## Persistence

SQLAlchemy 2 models (`projects`, `generations`, `verification_runs`) — SQLite by default, PostgreSQL via
`PHOENIX_DATABASE_URL`. Migrations: Alembic (`backend/migrations`, run automatically by the container entrypoint;
manually `cd backend && alembic upgrade head`). Sources, generated projects and job directories live under
`PHOENIX_DATA_DIR`.
