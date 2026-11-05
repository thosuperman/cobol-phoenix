# Submission checklist

## Product (verified in this session)
- [x] Starts locally (`make dev-*`) and with `docker compose up --build` (stack healthy; 127/127 run through the sidecar)
- [x] Sample project import, analysis, unsupported constructs reported
- [x] Dependency graph, business rules with real source references
- [x] Python/FastAPI generation; generated project runs and passes its own tests; ZIP download
- [x] Original COBOL executed in an isolated GnuCOBOL environment (no network confirmed)
- [x] Differential tests compare actual COBOL and Python outputs; injected fault detected
- [x] Real external repositories: insurance (180/180 NBUW001, golden files reproduced), banking, ledger
- [x] Automated tests pass (86 backend, frontend build, e2e)
- [x] `.kiro/` committed (steering, specs, hooks); Apache-2.0 LICENSE; README and docs
- [x] Screenshots in `assets/screenshots/`; logo and diagram in `assets/`
- [x] No secrets committed (`make security`)
- [x] No deployment claims (cloud deployment not performed)

## Manual steps before submitting (author)
- [ ] Use Kiro IDE on this repository as described in `docs/kiro-dev-log.md` and complete `kiro-usage.md`
- [ ] Create the public GitHub repository and push (with `.kiro/`)
- [ ] Record and upload the demo video (< 3 min, public YouTube); add link to README and Devpost
- [ ] Optional: deploy (see `docs/deployment.md`) and add the URL
- [ ] Fill the Devpost form from `devpost-description.md`; add screenshots
- [ ] Review and publish `blog-post.md` / `social-post.md` yourself (bonus prizes); verify the official Kiro handle
- [ ] Confirm the hackathon's eligibility rules and category (Resurrection) on the official rules page
