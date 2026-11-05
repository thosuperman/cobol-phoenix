# Architecture (submission summary)

![Pipeline](assets/diagrams/pipeline.svg)

```mermaid
flowchart LR
    UI[Next.js workspace] -- /api --> API[FastAPI]
    API --> P[Lexer · COPY · Parser] --> IR[(Normalized IR)]
    IR --> A[Graph · complexity · rules]
    IR --> G[Python/FastAPI generator + phoenix_runtime]
    G --> V[Verification: cases · harness · diff · mutation]
    V -- job queue --> R[GnuCOBOL runner<br/>no network · read-only · no caps]
    V -- subprocess --> PY[Generated Python]
    API --- DB[(SQLite / PostgreSQL)]
```

- **Deterministic core:** parsing, rules and generation never call an LLM; optional explanations are advisory.
- **Byte-accurate runtime:** every record is a `bytearray`; items are typed views, so REDEFINES, group moves and CALL BY REFERENCE match COBOL.
- **Differential proof:** identical bytes go into GnuCOBOL (via a generated harness) and Python; outputs are decoded with the record layout and compared field by field.
- **Isolation:** COBOL only runs in the runner container; generated Python runs in a scrubbed subprocess.

Full detail: `docs/architecture.md`, `docs/verification.md`, `SECURITY.md`.
