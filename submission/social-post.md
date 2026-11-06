# Social Blitz post (draft — rewrite in your own words before posting)

Rules: the post must **start with** `#KiroweenHackathon26`, be posted during the submission period
(by 4 Dec 2026, 2:00 pm PT), and **include your favourite thing about Kiro and how it changed the way you approached
development**. Posts are judged on original thoughts (not AI-sounding text) and on attached images/video, so write
the Kiro part yourself and attach `submission/assets/screenshots/09-fault-detected.png` or a short clip.

---

#KiroweenHackathon26 My favourite thing about Kiro: <YOUR OWN WORDS — e.g. how writing specs + steering first and
letting a PostTaskExec hook run the full GnuCOBOL test suite after every task changed how you worked>.

What I built: COBOL Phoenix turns legacy COBOL into a Python/FastAPI service and then proves it by running the
original program in a sandboxed GnuCOBOL container next to the Python.
✅ 127/127 identical cases on the insurance sample
✅ 180/180 on an independent public insurance repo
🐞 Remove one ROUNDED and the verifier flags 8 cases, down to the cent

Code: https://github.com/thosuperman/cobol-phoenix · Demo: <YouTube link>
