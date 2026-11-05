# Shot list

1. Landing hero (2 s hold on tagline).
2. Import page → “Sample project” tab → click *Import sample project*.
3. Overview: stat tiles, Programs table, Unsupported constructs chart (hover AUDITLOG entries).
4. Dependencies: click `RATEENG`, inspector shows COPY/CALL edges with line numbers.
5. Business rules: search “premium”, open `PM-404 Base Premium`, scroll to *Source evidence* highlight.
6. Generate: select `RATEENG`, click *Generate RATEENG*, show API contract + `schemas.py`.
7. Code viewer: click a ● line in `rateeng.py`; COBOL origin pane highlights the matching lines.
8. Verify: check *Include mutation analysis*, *Run verification*, show progress, then 127/127 banner, coverage tile, chart, mutation card.
9. Open one case: side-by-side raw outputs.
10. Generate → *Inject a deliberate fault* → “drop ROUNDED on RR-BASE-PREMIUM” → *Generate faulty build & verify* → *Run verification*.
11. FAILED banner; case detail diff table (RR-BASE-PREMIUM 4862.05 vs 4862.04).
12. Dashboard → corpus project (imported earlier from GitHub) → Verify → NBUW001 run 180/180 → mutation survivors (NB-303 lines 251–252).
13. Export page → Migration report preview.
14. End card: logo + tagline + repository URL.

Pre-recording checklist: import the corpus project beforehand (Import → GitHub → first preset, ref `be70080fb7a6079d54de71e441342a5f699ef4ea`), paste `corpus/fixtures/nbuw001-fixtures.json` under key `NBUW001` in Verify → Test fixtures, generate NBUW001 and run verification once so the result is ready.
