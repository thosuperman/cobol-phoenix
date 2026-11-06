# Testing instructions for judges

## Fastest path (hosted)
Open https://cobol.beauty — no login. The dashboard already contains the sample project and the external insurance repository with completed verification runs. To try the workflow yourself: **Import sample** → **Generate** → **Verify**, then **Inject a deliberate fault** as described below.

## Run it yourself (Docker only)
```bash
git clone https://github.com/thosuperman/cobol-phoenix cobol-phoenix && cd cobol-phoenix
docker compose up --build
```
Open http://localhost:3000 → **Import sample** → tabs **Business rules** → **Generate** (*Generate RATEENG*) →
**Verify** (*Run verification*, with mutation analysis). Expect 127/127 VERIFIED.
Then **Generate → Inject a deliberate fault** → “drop ROUNDED on RR-BASE-PREMIUM” → *Generate faulty build & verify*
→ *Run verification*. Expect FAILED cases with `RR-BASE-PREMIUM` differing by 0.01.

Optional — external repository: **Import → GitHub repository → first preset** (ref
`be70080fb7a6079d54de71e441342a5f699ef4ea`); in **Verify → Test fixtures** paste
`{"NBUW001": <contents of corpus/fixtures/nbuw001-fixtures.json>}` and save; **Generate NBUW001**; **Run verification**.

## Automated tests (developer machine)
```bash
make setup             # Python 3.13 venv, npm deps, GnuCOBOL runner image
make corpus            # optional: fetch external repositories at pinned commits
make test-backend      # 100 tests; GnuCOBOL tests skip with a reason if the runner image is missing
make test-frontend     # tsc + next build
make validate-generated
make dev-backend & make dev-frontend & make e2e   # Playwright demo workflow
```

Expected: all backend tests pass (cobol + corpus tests require Docker and the fetched corpus), frontend build
succeeds, generated projects pass their own tests, the e2e workflow passes.
