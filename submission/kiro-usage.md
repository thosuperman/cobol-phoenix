# How we used Kiro

Everything below is backed by files in this repository or by Kiro's own session records. Features we did not
use are listed as such.

## Kiro surfaces
- **Kiro IDE (1.2.56)** — used for spec-task execution with hooks and steering. Seven Kiro chat sessions on this
  repository (5–6 Nov 2026).
- Kiro CLI, Kiro Web and Kiro Crew — not used.

## Spec-driven development
Before writing code we wrote four specs in `.kiro/specs/` — `product-requirements`, `cobol-analysis`,
`python-generation` and `differential-verification` — each with EARS-style `requirements.md`, a `design.md` and a
numbered `tasks.md` tied back to requirement IDs.

How we structured them for Kiro:
- **Requirements are testable statements** ("WHEN a statement is outside the supported subset THE PARSER SHALL produce an `Unsupported` node…"), so each task ends in an executable check.
- **Designs pin decisions** Kiro must not reinvent: the IR is generator-independent, storage is byte-based, the complexity formula is fixed, and statuses are VERIFIED / FAILED / NOT_VERIFIABLE / UNSUPPORTED.
- **Tasks name the files and the proof**: task text lists the modules to touch and the tests (including a GnuCOBOL differential test) that close it.

Spec tasks executed by Kiro (recorded in `.kiro/specs/*/tasks.meta.json`):

| Spec / task | Kiro runs | Result (committed in `0fcc605`) |
|---|---|---|
| `cobol-analysis` 9 — INSPECT TALLYING / REPLACING | 3 | New `Inspect` IR node, parser, data flow, generator, runtime helpers; parser/runtime/codegen tests and a GnuCOBOL differential test. Kiro deliberately refused to translate INSPECT on signed or binary items (GnuCOBOL strips the sign) and reports those as unsupported. On the external ledger corpus, 6 previously unsupported INSPECT statements became translatable. |
| `python-generation` 7 — OpenAPI request examples from fixtures | 2 | Generated `schemas.py` now carries request examples validated against PICTURE constraints (invalid fixtures are listed in the generated README rather than altered), plus a generated test that posts every example. |

Compared with prompting freely, the spec forced each change to arrive with its tests and docs: both tasks updated
`docs/cobol-support.md` / `CHANGELOG.md` and the backend suite grew from 86 to 100 tests, all passing.

## Steering
`.kiro/steering/` holds six documents. `product.md`, `architecture.md`, `security.md` and `testing.md` use
`inclusion: always`; Kiro's session records show them included in every session. `cobol-semantics.md` and
`coding-standards.md` use `fileMatch` so they load only when engine or source files are in play.

The strategy that mattered most: **put the domain rules in steering, not in prompts.** `cobol-semantics.md`
states the GnuCOBOL behaviours the runtime must reproduce (overpunch signs, truncation, ROUNDED, SIZE ERROR,
INITIALIZE, PERFORM ranges). The INSPECT task followed the same rules without being told again — including the
decision to refuse signed numeric targets rather than guess.

## Agent hooks
Four v1 hook files in `.kiro/hooks/` (format checked against the current Kiro hook documentation):

| Hook | Trigger | Action | Observed in Kiro |
|---|---|---|---|
| Run backend tests after Python edits | `PostFileSave` on `backend/**.py` | `make test-backend-fast` | — |
| **Full test suite when a spec task completes** | `PostTaskExec` | `make test` | **invoked 2×, completed** |
| Validate generated Python | `PostFileSave` on generator/parser files | `make validate-generated` (regenerates the sample services and runs *their own* generated tests + ruff) | — |
| Format/lint Python, type-check frontend | `PostFileSave` | `make fmt-py`, `make lint-frontend` | — |
| **Security checks before the agent stops** | `Stop` | `make security` (bandit + secret scan) | **invoked 3×** |
| Review upload/sandbox changes | `PostFileSave` on importer/executors | agent prompt: re-check `security.md` and update security tests | — |

The hooks make every Kiro task end with the full test suite (which includes real GnuCOBOL differential runs) and a
security scan, so a task cannot be "done" while behaviour differs from the original COBOL. During development the
same commands caught an unused import in generated code (`validate-generated`) and a bandit finding on the sandbox
tmpfs path (`security`).

## Not used
- **Custom agents, MCP servers, Kiro powers** — not configured for this project.
- **Kiro property-based testing** — not used. The project has its own Hypothesis property tests for decimal
  storage, rounding and packed decimal (`backend/tests/test_runtime.py`), written outside Kiro's PBT feature.

## Disclosure
The project was created during the submission period in an empty repository. The steering documents, specs and
hooks were written first; most of the initial implementation (engine, generator, verification, UI) was then built
outside the Kiro IDE following those specs. Kiro IDE was used afterwards for the spec tasks listed above, with the
same steering and hooks. No pre-existing code was reused; third-party COBOL repositories are only fetched as test
inputs (`corpus/manifest.json`).
