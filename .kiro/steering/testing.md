---
inclusion: always
---

# Testing

- `make test` runs everything: backend pytest, runner tests, frontend type-check/build.
- Backend tests live in `backend/tests`; they must be deterministic (fixed dates via
  `COB_CURRENT_DATE`, seeded random generators, Hypothesis with `derandomize=True`).
- Tests that need GnuCOBOL are marked `@pytest.mark.cobol` and skip with an explicit reason
  when no executor is available — they never fake a pass.
- Tests against the external corpus are marked `@pytest.mark.corpus` and read the
  repositories fetched by `scripts/fetch-corpus.sh` (pinned SHAs in `corpus/manifest.json`).
  The external code is never committed to this repository.
- Every new COBOL construct needs: a parser test, a runtime semantics test and (when
  executable) a differential test against GnuCOBOL.
- Generated projects must pass their own generated pytest suite (`validate-generated-code` hook).
