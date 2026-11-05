# Phoenix Mutual — auto premium rating (sample COBOL project)

An **original** COBOL application written for COBOL Phoenix so the product can be
demonstrated without downloading third-party code. It models a small insurer's
nightly auto-premium rating batch.

| File | Purpose |
|---|---|
| `cobol/PREMCALC.cbl` | Batch driver: reads 45-byte policy records from SYSIN, CALLs `RATEENG`, prints a report and totals |
| `cobol/RATEENG.cbl` | Rating engine (LINKAGE `USING POLICY-REC RATE-RESULT`): validation, state rate table, age/vehicle/coverage/deductible factors, risk points, discounts, minimum premium, installments |
| `cobol/AUDITLOG.cbl` | Audit trail writer using file I/O and `INSPECT` — intentionally outside the supported subset, to show how unsupported constructs are reported |
| `copy/POLICY.cpy`, `copy/RATERES.cpy`, `copy/RATETAB.cpy` | Copybooks (request, result, REDEFINES/OCCURS rate table) |
| `fixtures/policies.txt` | 13 policy records + `END` |
| `fixtures/expected-output.txt` | Output of `PREMCALC < policies.txt` captured from **GnuCOBOL 3.2.0** (`COB_CURRENT_DATE=2026/01/01 09:30:00`) |
| `phoenix-fixtures.json` | Fixtures COBOL Phoenix uses for differential verification of `RATEENG` and `PREMCALC` |

Business rules are annotated in the source with `PM-nnn:` comments; COBOL Phoenix
extracts them as evidence-backed rules.

## Constructs exercised

COPY, REDEFINES, OCCURS, 88-levels (single and multiple values), COMP-3, numeric-edited
PICTUREs (`ZZZ,ZZ9.99`, `$$$,$$9.99`), MOVE, COMPUTE ROUNDED with ON SIZE ERROR, ADD,
DIVIDE ... GIVING ROUNDED, IF/ELSE with abbreviated combined conditions
(`IF AGE < 16 OR > 99`), NOT NUMERIC class tests, EVALUATE TRUE, EVALUATE ... ALSO ...
with ANY, EVALUATE ... WHEN a THRU b, PERFORM, PERFORM THRU with GO TO an exit paragraph,
PERFORM VARYING ... UNTIL ... OR, PERFORM UNTIL, CALL ... USING, INITIALIZE, SET ... TO TRUE,
STRING ... DELIMITED BY SIZE, reference modification, ACCEPT, DISPLAY, GOBACK, STOP RUN.

A real legacy quirk is preserved on purpose: `WS-PREM-EDIT PIC $$$,$$9.99` cannot hold
six integer digits, so policy `PM00000013` shows `$39,618.74` in its message while the
premium field holds `139,618.74`. Both GnuCOBOL and the generated Python reproduce it.

## Run it with GnuCOBOL

```bash
cobc -x -I copy -o premcalc cobol/PREMCALC.cbl cobol/RATEENG.cbl
./premcalc < fixtures/policies.txt | diff - fixtures/expected-output.txt
```

## License

Copyright 2026 COBOL Phoenix authors. Licensed under the Apache License, Version 2.0
(see `LICENSE`). The fictional company "Phoenix Mutual" and all data are invented.
