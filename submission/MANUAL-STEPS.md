# Remaining manual steps

Deadline: **4 December 2026, 2:00 pm Pacific Time** (no extensions). Judging runs 16 Dec 2026 – 29 Jan 2027, so the
application URL must stay up until then. Source: https://kiroween.devpost.com/rules (checked 6 Nov 2026).

## 1. Push the latest commits (needs your OK)
Local commits are ahead of `origin/main`. Review `git log origin/main..main`, then `git push`.

## 2. Application URL — DONE
Live at https://cobol-phoenix.kiriwake.jp (AWS Lightsail `small_3_0`, USD 12/month, **ap-southeast-1 / Singapore**, static IP 18.143.208.222,
Route 53 A record in `kiriwake.jp`, HTTPS via Caddy/Let's Encrypt). Keep it running until judging ends
(29 Jan 2027). Singapore was chosen because the ProxyGrid `cleanupOrphans` Lambda deletes unknown Lightsail
instances in Tokyo and Seoul. Visitors can delete projects; re-seed with *Import sample* if needed.
SSH: `ssh -i ~/.ssh/cobol-phoenix-lightsail ubuntu@18.143.208.222`. Update: copy or pull the code into
`/opt/cobol-phoenix`, then `sudo docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml up -d --build`.

## 3. Upload the demo video (YouTube, public)
- File: `submission/video/cobol-phoenix-demo.mp4` (< 3 min), subtitles `submission/video/cobol-phoenix-demo.srt`.
- Title: *COBOL Phoenix — From Mainframe to Modern (Kiroween 2026)*; description: `submission/video-description.md`.
- Visibility **Public**; no third-party music is used.
- Add the link to README §6 and Devpost.

## 4. Devpost form
| Field | Source |
|---|---|
| Name / tagline | COBOL Phoenix — "From Mainframe to Modern. Preserve the Logic. Rebuild the Future." |
| Category | **Resurrection** |
| Bonus categories | Best Demo is automatic; add the Blog and Social Blitz links only if you publish them. Startup, Student, Ghost of Kiroween Past and Kiro Crew do not apply unless you qualify yourself. |
| Description | `submission/devpost-description.md` (fill in *Try it*) |
| Kiro write-up | `submission/kiro-usage.md` |
| Testing instructions | `submission/testing-instructions.md` (+ credentials if you add basic auth) |
| Repository | https://github.com/thosuperman/cobol-phoenix (public, Apache-2.0 detected, `.kiro/` at root) |
| Video | your YouTube link |
| Images | `submission/assets/screenshots/*.png`, logo `submission/assets/logo/cobol-phoenix-logo.svg` |

## 5. Strengthen Kiro usage (recommended before the deadline)
Judges score "how thoroughly and skillfully the project uses Kiro" and may disqualify insufficient use. Today Kiro
executed two spec tasks. Good candidates for more Kiro work (each already fits the existing specs):
- `UNSTRING … DELIMITED BY … INTO …` support (common in the ledger corpus);
- `SEARCH` / `SEARCH ALL` on OCCURS tables;
- try Kiro's property-based testing on the runtime requirements, or an MCP server (e.g. GitHub) — then update
  `submission/kiro-usage.md` with what you actually did.

## 6. Optional bonus posts (publish yourself, during the submission period)
- Blog (`submission/blog-post.md`): publish on a third-party platform; it already states it was written as part of
  the Kiroween 2026 hackathon; add your own Kiro impressions.
- Social Blitz (`submission/social-post.md`): starts with `#KiroweenHackathon26`; write your favourite thing about
  Kiro in your own words; attach a screenshot or clip.

## 7. Optional repository polish (GitHub settings)
Set the repository description ("Evidence-backed COBOL → Python modernization, proven against GnuCOBOL"), topics
(`cobol`, `gnucobol`, `legacy-modernization`, `fastapi`, `kiro`, `kiroween`) and, after deployment, the website URL.
