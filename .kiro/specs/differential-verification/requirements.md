# Requirements — Differential verification

1. THE SYSTEM SHALL build test cases from (a) fixtures shipped with the project, (b) boundary values derived from comparisons with literals and 88-level values in the IR, and (c) seeded random valid records.
2. WHEN the program under test has a LINKAGE SECTION THE SYSTEM SHALL generate a COBOL harness that ACCEPTs each USING parameter, CALLs the program and DISPLAYs every parameter.
3. THE SYSTEM SHALL execute COBOL only through a sandbox executor with no network, CPU/memory/PID limits, timeouts and only the job directory mounted.
4. THE SYSTEM SHALL execute the generated Python in a subprocess with a timeout.
5. THE SYSTEM SHALL compare raw output and decoded fields (numeric by value and scale, alphanumeric exactly) and classify each case VERIFIED / FAILED / NOT_VERIFIABLE / UNSUPPORTED.
6. THE SYSTEM SHALL record COBOL source lines exercised by each case (via Python trace mapped through traceability) to derive rule verification status.
7. THE SYSTEM SHALL support mutation analysis: run the suite against mutated generated code and report which mutants were detected.
8. THE REPORT SHALL never state full equivalence; it states the cases executed and their coverage.
