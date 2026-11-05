---
inclusion: always
---

# Product: COBOL Phoenix

**Tagline:** From Mainframe to Modern. Preserve the Logic. Rebuild the Future.

COBOL Phoenix is an evidence-backed legacy modernization platform. It turns COBOL
business logic into modern Python (FastAPI) services and then *proves* the result by
running the original COBOL (GnuCOBOL, sandboxed) and the generated Python side by side.

## Principles (non-negotiable)

1. **Understand, do not transliterate.** Every artifact flows through the pipeline
   `source → lexer/preprocessor → parser → IR → analysis/rules → generator → verification`.
2. **Evidence or nothing.** Every business rule, generated function and report row cites
   a real file and a real line range. Never invent citations.
3. **Never fabricate execution results.** If GnuCOBOL is unavailable the status is
   `NOT_VERIFIABLE`. A comparison is only `VERIFIED` when both programs actually ran.
4. **Never silently drop unsupported COBOL.** Unsupported constructs are reported with
   their location, and the generator emits an explicit `UnsupportedConstruct` raise.
5. **AI is optional.** The product is fully functional with no LLM configured. LLM output
   is advisory text only and may never alter source citations or generated code.
6. **Decimal everywhere.** Financial values are `decimal.Decimal`; `float` is forbidden in
   generated business logic.

## Users

Enterprise modernization teams, mainframe/COBOL developers, architects, and engineers in
insurance and financial services.

## Status vocabulary

| Status | Meaning |
|---|---|
| `VERIFIED` | COBOL and Python both executed on the case and outputs matched byte-for-byte and field-by-field |
| `FAILED` | Both executed and at least one output field differs |
| `NOT_VERIFIABLE` | The original runtime could not be executed (no GnuCOBOL, compile error, timeout) |
| `UNSUPPORTED` | The executed path hit a construct the generator does not support |
