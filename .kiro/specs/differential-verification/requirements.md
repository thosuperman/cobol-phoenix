# Requirements — Differential verification

1. THE SYSTEM SHALL build test cases from (a) fixtures shipped with the project, (b) boundary values derived from comparisons with literals and 88-level values in the IR, and (c) seeded random valid records.
2. WHEN the program under test has a LINKAGE SECTION THE SYSTEM SHALL generate a COBOL harness that ACCEPTs each USING parameter, CALLs the program and DISPLAYs every parameter.
3. THE SYSTEM SHALL execute COBOL only through a sandbox executor with no network, CPU/memory/PID limits, timeouts and only the job directory mounted.
4. THE SYSTEM SHALL execute the generated Python in a subprocess with a timeout.
5. THE SYSTEM SHALL compare raw output and decoded fields (numeric by value and scale, alphanumeric exactly) and classify each case VERIFIED / FAILED / NOT_VERIFIABLE / UNSUPPORTED.
6. THE SYSTEM SHALL record COBOL source lines exercised by each case (via Python trace mapped through traceability) to derive rule verification status.
7. THE SYSTEM SHALL support mutation analysis: run the suite against mutated generated code and report which mutants were detected.
8. THE REPORT SHALL never state full equivalence; it states the cases executed and their coverage.
9. Validity-aware placement (boundary case built for COBOL statement S; "executes S" is checked by tracing the generated Python, never the uploaded COBOL, with the same line tracing as `fixture_coverage()`):
   1. WHEN a boundary case placed on its preferred fixture does not execute S, THE SYSTEM SHALL rebuild the case on each other fixture that executes S, in fixture order, until one executes S.
   2. IF no fixture yields a case that executes S, THEN THE SYSTEM SHALL adjust guard fields (input fields read by conditions executed before S on the failing run) using only values the CandidateCollector produced for those fields, until a case executes S.
   3. IF no attempt executes S within 24 attempts per boundary value, THEN THE SYSTEM SHALL keep the original placement and record in the case that the target statement was not reached.
   4. THE SYSTEM SHALL record in the case description the fixture used and every adjusted field with its value.
   5. THE SYSTEM SHALL produce identical cases for the same IR, fixtures and seed.
   6. IF tracing of the generated Python is unavailable, THEN THE SYSTEM SHALL place boundary cases exactly as in requirement 1 (coverage-guided placement).
