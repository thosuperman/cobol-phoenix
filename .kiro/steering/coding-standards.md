---
inclusion: fileMatch
fileMatchPattern: "**/*.{py,ts,tsx}"
---

# Coding standards

## Python (backend, runner, generated code)
- Python 3.13, type hints on all public functions, `from __future__ import annotations`.
- Format and lint with `ruff format` / `ruff check` (config in `backend/pyproject.toml`).
- Dataclasses for IR, Pydantic v2 models only at the API boundary.
- No `float` in arithmetic paths; use `Decimal` with an explicit context.
- No `eval`/`exec` on user-derived text. Generated identifiers are sanitised; literals are
  emitted with `repr()`.
- Errors raised to the API are `PhoenixError` subclasses with a stable `code`.

## TypeScript (frontend)
- Strict TypeScript, no `any` in exported APIs.
- All data comes from the backend API (`src/lib/api.ts`); no mock data in pages.
- Every page has loading, empty and error states.
- Components in `src/components`, pages in `src/app`.

## Commits
- Conventional Commits (`feat(parser): ...`, `fix(verify): ...`).
