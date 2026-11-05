# Remaining manual steps (only you can do these)

Everything below needs your accounts or must genuinely be done by you. Allow ~1–2 hours.

## 1. Use Kiro on this repository (most important for judging)
Kiro is installed (`/Applications/Kiro.app`, v1.2.56).

1. Open the repo in Kiro (File → Open Folder → this directory). Confirm in the Kiro panel that **steering** files load
   (`product.md`, `architecture.md`, `testing.md`, `security.md` always; `cobol-semantics.md`, `coding-standards.md` on matching files).
2. **Hooks:** open the Agent Hooks panel — the four files in `.kiro/hooks/` (v1 format) should be listed. If Kiro shows an
   upgrade/validation badge, accept its fix and commit the result.
3. **Specs:** open *cobol-analysis* → task **9 (INSPECT support)** and click *Start task* (or ask in chat:
   “Execute task 9 of the cobol-analysis spec”). Let Kiro implement it; watch the `run-tests` and
   `validate-generated-code` hooks fire. Verify with `make test-backend` (the GnuCOBOL tests run for real).
   Optionally do *python-generation* task **7**.
4. Take 3–4 screenshots (spec panel with tasks, a hook firing, the chat executing a task) into
   `submission/assets/screenshots/kiro-*.png`.
5. Replace the bracketed section in `submission/kiro-usage.md` and the “Still to do in the Kiro IDE” list in
   `docs/kiro-dev-log.md` with what actually happened. Commit and push.

## 2. Upload the demo video
- File: `submission/video/cobol-phoenix-demo.mp4` (1:58, 1440×900, narrated with macOS text-to-speech, recorded from
  the real running app by `frontend/e2e/record-demo.spec.ts`; rebuild with `python3 scripts/build_demo_video.py`).
- YouTube → Create → Upload. Title: *COBOL Phoenix — From Mainframe to Modern (Kiroween 2026)*.
  Description: `submission/video-description.md` (timestamps match the video roughly; adjust if needed).
  Subtitles → upload `submission/video/cobol-phoenix-demo.srt`. Visibility: **Public**. Not made for kids.
- Optional: re-record narration with your own voice (`submission/video/narration.json` has the script).
- Put the link in `README.md` §6 and in Devpost.

## 3. Devpost
- Project name: COBOL Phoenix · Tagline: *From Mainframe to Modern. Preserve the Logic. Rebuild the Future.*
- Category: Resurrection (confirm on the official rules page).
- “About the project”: paste `submission/devpost-description.md`.
- Built with: python, fastapi, pydantic, sqlalchemy, gnucobol, docker, next.js, react, typescript, tailwindcss, kiro.
- Repository: https://github.com/thosuperman/cobol-phoenix · Video: your YouTube link.
- Gallery: `submission/assets/screenshots/01…10` (+ Kiro screenshots), logo `submission/assets/logo/cobol-phoenix-logo.svg`.
- Kiro usage field: `submission/kiro-usage.md` (after step 1).
- Testing instructions: `submission/testing-instructions.md`.

## 4. Bonus prizes (optional)
- Blog: edit and publish `submission/blog-post.md` (dev.to / Medium / your blog), add the “Kiro IDE experience” paragraph.
- Social: post `submission/social-post.md` (must start with `#KiroweenHackathon26`); look up and tag the official Kiro account.

## 5. Optional deployment
`docs/deployment.md` → single EC2 + Docker Compose; add the URL to README/Devpost only after you have verified it.
