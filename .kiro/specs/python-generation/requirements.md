# Requirements — Python generation

1. WHEN a program is selected THE GENERATOR SHALL emit a Python package containing `phoenix_runtime.py`, one logic module per program in the call tree, `schemas.py`, `main.py` (FastAPI), `cli.py`, tests, README and `traceability.json`.
2. THE GENERATOR SHALL be deterministic: the same IR produces byte-identical output.
3. THE GENERATOR SHALL map every emitted statement to its COBOL file and line range in `traceability.json`.
4. THE GENERATOR SHALL use `Decimal` arithmetic with explicit truncation/rounding per statement.
5. WHEN a statement is unsupported THE GENERATOR SHALL emit `raise UnsupportedConstruct(...)` with the source location.
6. THE GENERATED API SHALL validate requests against PICTURE constraints (length, digits, scale, sign).
7. THE GENERATED PROJECT SHALL pass its own generated tests.
8. THE GENERATOR SHALL support optional mutations (fault injection) for verification demos.
