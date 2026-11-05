# Design — Python generation

## Generated layout
```
<name>/
  README.md  requirements.txt  traceability.json  pytest.ini
  app/phoenix_runtime.py   # vendored runtime (storage, numeric/alnum views, arithmetic, editing)
  app/programs/<prog>.py   # one class per COBOL program
  app/schemas.py           # Pydantic request/response models derived from records
  app/service.py           # encode request -> records -> run program -> decode response
  app/main.py              # FastAPI app: POST /api/v1/<program>/execute, GET /health
  app/cli.py               # batch mode used by differential verification
  tests/test_api.py  tests/test_cases.py  tests/cases.json
```

## Program translation
- Each COBOL program → class `Program_<ID>(Program)`; data items → `Field` attributes bound to
  record buffers; paragraphs → methods `p_<name>`; paragraph order list drives fall-through and
  PERFORM THRU via `self.perform(start, end)`.
- `EXIT PARAGRAPH` → `return` (inside the paragraph method). `GOBACK` → `raise Goback`.
  `STOP RUN` → `raise StopRun`.
- Expressions → `Decimal` expressions built from `field.value`; stores via
  `field.store(value, rounded=..., size_error=...)`.
- Conditions → runtime `compare()` / `cond.is_true()`.
- Mutation operators: `rounding` (ROUNDED → truncate), `relop` (`<` ↔ `<=`, `>` ↔ `>=`),
  `arith` (`+` ↔ `-`), `literal` (numeric literal + 1 ULP).
