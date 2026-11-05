# COBOL Phoenix — From Mainframe to Modern. Preserve the Logic. Rebuild the Future.

## Inspiration
Insurers and banks still price policies and post ledgers in COBOL. The logic is correct and valuable — but the
people who wrote it are gone, and every modernization project stalls on the same question: *does the new system
behave exactly like the old one?* Translating COBOL line by line, by hand or with an LLM, produces code nobody can
trust without months of parallel runs. We wanted a tool that makes that question answerable on day one.

## What it does
COBOL Phoenix is a modernization workspace in four acts:

1. **The dead system — import.** Upload files or a ZIP, or import a public GitHub repository at a pinned commit. Uploaded code is treated as data and is never executed during import or analysis.
2. **The discovery — understand.** A deterministic parser builds an intermediate representation with byte-accurate data layouts, a dependency graph (COPY, CALL, PERFORM, record usage) and business rules. Every rule cites a real file and line range; unsupported constructs are reported, never silently dropped.
3. **The resurrection — generate.** Pick a capability and get an executable Python/FastAPI project: Decimal business logic, Pydantic schemas derived from PICTURE clauses, endpoint, CLI, tests, README and a traceability map from every Python statement back to its COBOL lines.
4. **The proof — verify.** The original program runs in a network-less GnuCOBOL container and the generated Python in a subprocess, on the same inputs: fixtures, boundary values derived from the IR, edge values and seeded random records. Outputs are compared field by field. Mutation analysis measures how strong the test suite is, and you can inject a fault on purpose to watch the verifier catch it.

## Real results (all from actual executions, GnuCOBOL 3.2.0)
- **Original sample (Phoenix Mutual auto rating):** `RATEENG` — 127/127 cases identical, 95.0% statement coverage, 33/36 mutants killed (the 3 survivors are equivalent mutants). Injecting “drop ROUNDED on RR-BASE-PREMIUM” makes 8 cases FAIL, e.g. 4862.05 vs 4862.04. The batch `PREMCALC` reproduces the GnuCOBOL report byte-for-byte — including a legacy truncation quirk (`$39,618.74` for 139,618.74).
- **External insurance repository** (mudasin1/COBOL_Sample_March_2026): 0 parse errors; the generated Python of all three upstream test drivers reproduces the upstream golden files byte-for-byte; the migration unit `NBUW001` (eligibility, rating, premium) passes **180/180** differential cases with 96.3% statement coverage. Mutation analysis exposed an unreachable rule (NB-303 can never fire because all plans cap issue age at ≤ 60).
- **Two more independent repositories** (banking demo; legacy ledger in free format): 20 programs, 0 parse errors, 367 unsupported constructs (file I/O, ALTER, REPORT SECTION, SORT, …) reported with locations.
- Differential testing also found a bug in our own runtime (floating `$` editing when high-order digits are truncated) — exactly the kind of subtle behaviour the product exists to catch.

## How we built it
- **Engine (Python 3.13):** fixed/free-format lexer, COPY … REPLACING preprocessor, recursive-descent parser, IR dataclasses with source locations, data-flow analysis, rule extraction.
- **Generator:** deterministic templates on a vendored runtime (`phoenix_runtime`) that implements COBOL storage as bytes (REDEFINES, group moves and CALL BY REFERENCE behave like COBOL), zoned/packed/binary numerics, numeric editing, truncation and ROUNDED rules, with a 64-digit truncating Decimal context.
- **Verification:** a generated COBOL harness for LINKAGE programs, a file-queue sandbox runner (no network, read-only root FS, no capabilities, rlimits), coverage-guided boundary placement (fixtures are traced through the generated Python, then each boundary value is attached to a fixture that executes its source statement), field-level diffs, mutation analysis.
- **Product:** FastAPI + SQLAlchemy + Alembic backend; Next.js 16, React 19, Tailwind 4, React Flow and Recharts frontend; Docker Compose deployment.
- **Kiro:** steering documents, four specs and v1 hooks drove the build (see the Kiro usage section).

## What makes it different
Not “AI translates COBOL”. Evidence-backed understanding, deterministic generation, and **behavioural proof against the original runtime** — with honest statuses (`NOT_VERIFIABLE` when COBOL cannot run, never a fake pass) and an explicit claim that passing cases are evidence for those inputs, not a proof for all inputs.

## Challenges
Matching GnuCOBOL exactly: sign overpunch bytes, pretty-display of signed numerics, division-by-zero semantics, alphanumeric-to-numeric moves, ACCEPT at end of input and floating insertion editing all had to be confirmed with probe programs. Making generic test generation reach deep rules (riders) led to coverage-guided placement.

## What's next
File I/O adapters (sequential/indexed files mapped to repositories), CICS/SQL boundary detection with stubs, IBM dialect options (TRUNC, NUMPROC), CI integration that keeps the differential suite running while COBOL remains authoritative.

## Built with
python · fastapi · pydantic · sqlalchemy · alembic · gnucobol · docker · next.js · react · typescript · tailwindcss · react-flow · recharts · hypothesis · playwright · kiro
