# Contributing

1. `make setup`, then `make dev-backend` and `make dev-frontend`.
2. Read `.kiro/steering/` — especially `cobol-semantics.md` and `security.md` — before changing the engine.
3. Work spec-first: add or update requirements/tasks in `.kiro/specs/<area>/` for non-trivial changes.
4. Every new COBOL construct needs a parser test, a runtime semantics test and, where executable, a differential
   test against GnuCOBOL. Never mark a construct as supported without a test that proves it.
5. Run `make lint test validate-generated security` before opening a pull request.
6. Use Conventional Commits (`feat(parser): …`, `fix(runtime): …`).

Do not commit third-party COBOL code; add external repositories to `corpus/manifest.json` with a pinned commit
and their license instead.
