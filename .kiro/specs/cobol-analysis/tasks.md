# Tasks — COBOL analysis engine

- [x] 1. Source reader with fixed/free format detection and line preservation (_Req 1, 2_)
- [x] 2. Lexer with continuation lines, literals, pseudo-text, locations (_Req 1–3_)
- [x] 3. COPY preprocessor with REPLACING, include paths and cycle detection (_Req 4, 5_)
- [x] 4. Data division parser + storage layout (_Req 6, 7_)
- [x] 5. Procedure division parser for the supported subset + Unsupported nodes (_Req 8, 9_)
- [x] 6. IR serialisation and project-level analysis (_Req 10_)
- [x] 7. Business rule extraction with evidence (_Req 11_)
- [x] 8. Parser tests on the bundled sample and the external corpus

## Next (open)
- [x] 9. Support `INSPECT <field> TALLYING <counter> FOR ALL <literal>` and `INSPECT … REPLACING ALL <literal> BY <literal>`: parse into IR, translate in `program_gen.py`, add runtime helpers, unit tests and a GnuCOBOL differential test (sample `AUDITLOG` uses TALLYING). Update `docs/cobol-support.md`. (_Req 8, 9_)
