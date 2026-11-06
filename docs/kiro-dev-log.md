# Kiro development log (factual)

This log records what the `.kiro/` artifacts are, when they were created, how they were used, and what they
influenced or caught. It deliberately distinguishes what has happened from what still has to be done in the
Kiro IDE. Nothing here claims Kiro features that were not used.

## Timeline

| Date (2026) | Event |
|---|---|
| Nov 5 | Empty workspace; repository initialised (fresh project, created during the submission period). |
| Nov 5 | **Steering** written first: `product.md`, `architecture.md`, `coding-standards.md`, `cobol-semantics.md`, `testing.md`, `security.md` (front-matter `inclusion: always` / `fileMatch`). |
| Nov 5 | **Specs** written before implementation: `product-requirements`, `cobol-analysis`, `python-generation`, `differential-verification` — each with EARS-style `requirements.md`, `design.md`, `tasks.md`. |
| Nov 5 | **Hooks** written. The hook format was checked against the current Kiro documentation (kiro.dev “Hooks”, v1 schema: `.kiro/hooks/*.json` with `version: "v1"`, `trigger`, `matcher`, `action`) instead of the older `.kiro.hook` `when/then` format. Triggers used: `PostFileSave`, `PostTaskExec`, `Stop`. |
| Nov 5 | Implementation followed the spec task lists in order (analysis → generation → verification → API → UI → deployment). Task checkboxes were updated as tasks completed. |

## How each artifact shaped the implementation

* **`cobol-semantics.md`** fixed the runtime rules up front (byte-based storage, overpunch signs, `byte & 0x0F`
  digit reads, ROUNDED = half away from zero, truncation, SIZE ERROR leaves the receiver unchanged). Each rule was
  then confirmed with GnuCOBOL probe programs; two rules were corrected from evidence (ACCEPT at EOF moves spaces;
  floating `$` editing when high-order digits are truncated).
* **`product.md`** defined the status vocabulary (`VERIFIED / FAILED / NOT_VERIFIABLE / UNSUPPORTED`) and the
  “never fabricate execution results” principle, which became the `DisabledExecutor` behaviour and a test
  (`test_disabled_executor_never_fabricates_results`).
* **`security.md`** produced the importer limits and the runner hardening; `test_security.py` maps 1:1 to its bullets.
* **`differential-verification` spec** required a harness for LINKAGE programs and mutation analysis; both exist as specified.
* **`cobol-analysis` design** fixed the complexity formula before any code; the UI and reports show that exact formula.

## Hook commands and what they caught

The hook *commands* are Makefile targets, so they run identically from Kiro and from a terminal. During this
development session they were run from the terminal:

| Hook | Command | Result / issues caught |
|---|---|---|
| `run-tests.json` (PostFileSave on backend Python) | `make test-backend-fast` | regressions in lexer format detection and ZIP limit handling were caught and fixed before commit |
| `run-tests.json` (PostTaskExec) | `make test` | full suite (86 backend tests before the Kiro tasks, 100 after), frontend type-check + build |
| `validate-generated-code.json` | `make validate-generated` | caught an unused `Decimal` import in generated batch-mode `schemas.py` (ruff F401) — fixed in the generator |
| `check-formatting.json` | `make fmt-py`, `make lint-frontend` | formatting / type errors (e.g. a removed lucide brand icon) |
| `security-check.json` (Stop) | `make security` | bandit B108 on the sandbox tmpfs path — reviewed, documented as a false positive (`# nosec B108` with reason) |

## Kiro IDE sessions (5–6 Nov 2026)

Source: `.kiro/specs/*/tasks.meta.json` and Kiro's local session records for this workspace.

| What | Evidence |
|---|---|
| Kiro IDE 1.2.56 opened on the repository; 7 chat sessions | Kiro session records |
| Steering `product`, `architecture`, `security`, `testing` (always) included in sessions | `steering_inclusion` events |
| `cobol-analysis` task 9 (INSPECT) executed 3 times across 3 sessions | `tasks.meta.json` |
| `python-generation` task 7 (OpenAPI examples) executed 2 times across 2 sessions | `tasks.meta.json` |
| Hook "Full test suite when a spec task completes" (`run-tests.json`, `PostTaskExec`) invoked 2×, status completed | `ContextualHookInvoked` events |
| Hook "Security checks before the agent stops" (`security-check.json`, `Stop`) invoked 3× | hook events |
| Result reviewed, full suite re-run (100 tests passing) and committed as `0fcc605` | git history |

Not used: Kiro CLI / Web / Crew, custom agents, MCP, Kiro powers, Kiro's property-based testing feature.
