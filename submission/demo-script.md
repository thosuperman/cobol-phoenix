# Demo video script (target 2:50, public YouTube)

Recording setup: `docker compose up --build`, browser at 1440×900, fresh data volume, sample + insurance repo
importable. No music with copyright; optional royalty-free track or none. No third-party logos.

| Time | Act | On screen | Voice-over |
|---|---|---|---|
| 0:00–0:15 | Hook | Landing page, tagline | “Billions in insurance and banking still run on COBOL. Rewriting it is easy. Proving the rewrite behaves the same is the hard part. This is COBOL Phoenix.” |
| 0:15–0:35 | I · The dead system | Import → Sample project → project overview | “We import an insurance rating system. It is parsed deterministically — no AI guessing: 3 programs, 3 copybooks, 27 business rules, and 3 file I/O statements we don’t translate, reported with their exact lines.” |
| 0:35–0:55 | II · The discovery | Dependencies graph (click RATEENG), Business rules → PM-404 | “Every edge and every rule points to real source. Here is the base-premium rule: inputs, outputs, the COMPUTE ROUNDED, cited to RATEENG lines 197 to 205.” |
| 0:55–1:20 | III · The resurrection | Generate RATEENG → API contract → Code viewer, click a traced line | “One click generates a FastAPI service with Decimal arithmetic and schemas derived from PICTURE clauses. Every Python statement maps back to its COBOL line.” |
| 1:20–1:55 | IV · The proof | Verify → Run verification → 127/127, coverage, mutation score | “Now the proof. The original program runs in a sandboxed GnuCOBOL container with no network; the Python runs beside it. 127 cases — fixtures, boundary values derived from the code, edge and random records — all identical. Mutation analysis then tests the tests and lists every fault they would miss.” |
| 1:55–2:20 | IV · Catching a fault | Generate → inject “drop ROUNDED on RR-BASE-PREMIUM” → verify → FAILED, diff 4862.05 vs 4862.04 | “Does the verifier actually catch mistakes? We inject one tiny fault — a missing ROUNDED. Eight cases fail, down to the cent, with the field and its copybook line.” |
| 2:20–2:40 | Real code | Project from mudasin1/COBOL_Sample_March_2026 → NBUW001 run 180/180 | “And not just our sample: on an independent public insurance repository, the generated underwriting service matches GnuCOBOL on 180 of 180 cases — and mutation analysis even exposed a rule that can never fire.” |
| 2:40–2:50 | Close | Export page, migration report; tagline | “Evidence for every rule, proof for every build. COBOL Phoenix — preserve the logic, rebuild the future.” |
