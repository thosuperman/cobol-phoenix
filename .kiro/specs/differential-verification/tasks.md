# Tasks — Differential verification

- [x] 1. Executors: queue, docker, disabled (_Req 3_)
- [x] 2. Harness generator for LINKAGE programs (_Req 2_)
- [x] 3. Test case generation: fixtures, boundaries, seeded random (_Req 1_)
- [x] 4. Python execution with line tracing (_Req 4, 6_)
- [x] 5. Field-level comparison and status classification (_Req 5_)
- [x] 6. Mutation analysis (_Req 7_)
- [x] 7. Reports (JSON + Markdown) (_Req 8_)
- [x] 8. Coverage-guided boundary placement (fixtures traced through generated Python; boundaries attached to fixtures that execute the source statement) (_Req 1_)
- [x] 9. Validity-aware placement: re-check each placed boundary case with traced Python; fall back to other fixtures, then to guard-field adjustments from collected candidates; deterministic and bounded; tests in backend/tests/test_verification.py; docs/verification.md mutation scores re-measured (_Req 1, 7, 9_)
