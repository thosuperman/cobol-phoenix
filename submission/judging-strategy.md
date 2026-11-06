# Judging strategy (five equally weighted criteria)

| Criterion | What we show | Evidence |
|---|---|---|
| **Potential impact** | Modernization fails on behavioural uncertainty. Phoenix turns “does it behave the same?” into a report with field-level diffs, coverage and mutation score — usable by enterprise teams today on GnuCOBOL-compatible code. | Real insurance repo: 180/180 cases on NBUW001; unreachable rule NB-303 discovered; migration report export. |
| **Technological implementation** (rules: *how thoroughly and skillfully the project uses Kiro*) | Spec-first build with steering for domain rules; Kiro IDE executed spec tasks with a `PostTaskExec` hook running the full GnuCOBOL differential suite; plus a real parser + IR, byte-accurate runtime, sandboxed differential execution, mutation analysis and 100 automated tests. Weakest point today: breadth of Kiro features used (see MANUAL-STEPS §5). | `submission/kiro-usage.md`, `.kiro/`, `backend/tests`, `docs/verification.md`. |
| **Design** | Coherent “mainframe resurrection laboratory” UI: one workflow (Overview → Rules → Generate → Verify → Export), every number links to source evidence, honest status badges, loading/empty/error states. | Screenshots in `assets/screenshots/`. |
| **Innovation** | Evidence-backed extraction + behavioural proof instead of AI translation; fault injection to prove the verifier; coverage-guided boundary placement; traceability for every generated statement. | Verify page, fault-injection run, traceability viewer. |
| **Presentation** | A < 3 minute demo following the four acts with live, reproducible results; README and Devpost text state only measured facts. | `demo-script.md`, `demo-shot-list.md`. |

Demo priorities: (1) show the proof, (2) show the fault being caught, (3) show it on a codebase we did not write.
Avoid: overclaiming (“100% equivalent”), long code scrolling, explaining internals before showing results.
