# How we used Kiro

> Fill in the bracketed parts after doing the remaining steps in the Kiro IDE (see `docs/kiro-dev-log.md`).
> Do not submit claims about Kiro features you did not use.

## Spec-driven development
We started with an empty repository and wrote the Kiro configuration before any code:

- **Steering** (`.kiro/steering/`): `product.md` (principles and the VERIFIED / FAILED / NOT_VERIFIABLE / UNSUPPORTED vocabulary), `architecture.md` (module boundaries: IR independent of the generator), `cobol-semantics.md` (the GnuCOBOL rules the runtime must obey), `coding-standards.md`, `testing.md`, `security.md`. `cobol-semantics.md` and `coding-standards.md` use `fileMatch` inclusion so they only load for engine / source files.
- **Specs** (`.kiro/specs/`): product requirements, COBOL analysis, Python generation and differential verification, each with EARS requirements, a design and a task list that the implementation followed in order.
- **Hooks** (`.kiro/hooks/*.json`, Kiro v1 schema): run fast backend tests on save of backend Python, run the full suite after a spec task completes (`PostTaskExec`), regenerate the sample services and run their own generated tests when the generator changes, format/lint on save, and run bandit + a secret scan when the agent stops; an agent-prompt hook re-checks the security steering whenever import or sandbox code changes.

## What it influenced
- The steering file on COBOL semantics became the checklist for the runtime; two rules were corrected when GnuCOBOL probes disagreed.
- The verification spec required a LINKAGE harness and mutation analysis — both shipped as specified, and mutation analysis later drove the coverage-guided placement improvement.
- “Never fabricate execution results” in product steering became an executor design and a dedicated test.

## What the hooks caught
- `validate-generated-code`: an unused import in generated batch-mode schemas.
- `security-check`: a bandit finding on the sandbox tmpfs path, reviewed and documented.
- `run-tests`: regressions in format auto-detection and ZIP limits before they were committed.

## In the Kiro IDE
[Describe here: opening the specs panel, executing spec tasks with Kiro, hooks firing in the Agent Hooks panel, any vibe-coding sessions, MCP if configured — with screenshots.]
