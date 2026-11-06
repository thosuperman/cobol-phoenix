# Submission checklist (Kiroween 2026 rules, checked 6 Nov 2026)

| Requirement | Status | Evidence / action |
|---|---|---|
| Project created during the submission period (from 30 Oct 2026) | DONE | first commit 5 Nov 2026, empty repository |
| Working software built using Kiro | DONE (strengthen recommended) | Kiro IDE spec tasks, hooks and steering — `submission/kiro-usage.md`; see MANUAL-STEPS §5 |
| Category identified | NEEDS MY ACTION | select **Resurrection** in the Devpost form |
| URL to the functional application | DONE | https://cobol-phoenix.kiriwake.jp (Lightsail, verified end to end) |
| Text description of features and functionality | DONE | `submission/devpost-description.md` |
| Demo video < 3 min, shows the project running | DONE | `submission/video/cobol-phoenix-demo.mp4` |
| Video public on YouTube, link in the form | NEEDS MY ACTION | upload (MANUAL-STEPS §3) |
| No third-party trademarks / copyrighted music in the video | DONE | text-to-speech narration, no music, own UI |
| Public GitHub repository | NEEDS MY ACTION | https://github.com/thosuperman/cobol-phoenix is currently **private** — make it public again |
| Open-source license detectable in About | DONE | Apache-2.0 detected by GitHub |
| `/.kiro` at the root, not git-ignored | DONE | steering (6), specs (4 + task metadata), hooks (4) |
| All source, assets and instructions to run it | DONE | README, `docker compose up --build`, Makefile |
| Kiro usage write-up | DONE | `submission/kiro-usage.md` (factual, includes what was not used) |
| Pre-existing code disclosed | DONE | disclosure section in the description and write-up |
| Third-party code/data used with authorisation | DONE | external corpus fetched only for tests, not redistributed |
| English materials | DONE | |
| Latest commits pushed | NEEDS MY ACTION | `git push` after review |
| Blog bonus | NEEDS MY ACTION (optional) | publish `submission/blog-post.md` |
| Social Blitz bonus | NEEDS MY ACTION (optional) | post `submission/social-post.md` in your own words |
| Startup / Student / Ghost of Kiroween Past / Kiro Crew bonuses | NOT APPLICABLE | unless you personally qualify |

## Verified in this session
- Backend: 100 tests passing, none skipped (GnuCOBOL differential and external-corpus tests ran for real).
- Generated projects: both sample services pass their own generated tests and ruff.
- Frontend: type-check and production build pass; Playwright demo workflow passes; no horizontal overflow at 375 px / 768 px.
- Docker Compose stack: healthy, verification through the sandbox sidecar, runner has no network.
- Hosted at https://cobol-phoenix.kiriwake.jp: RATEENG 127/127 (mutation 30/36), NBUW001 180/180 (36/43), injected fault caught (8 FAILED).
