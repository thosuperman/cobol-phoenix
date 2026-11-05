# Requirements — COBOL Phoenix (product level)

## Introduction
COBOL Phoenix imports a COBOL code base, analyses it deterministically, extracts business
rules with source evidence, generates a Python/FastAPI implementation of a selected program
and verifies behavioural equivalence against the original program executed by GnuCOBOL.

## Requirement 1 — Project import
**User story:** As a modernization engineer, I want to import COBOL sources so that I can analyse them.
1. WHEN a user uploads a ZIP archive THE SYSTEM SHALL extract only allow-listed source files after validating size, member count, compression ratio and paths.
2. WHEN a user uploads individual `.cob/.cbl/.cpy/.cob` files THE SYSTEM SHALL store them as a project.
3. WHEN a user selects the bundled sample THE SYSTEM SHALL import it without network access.
4. WHEN an archive contains a path traversal, symlink or oversized member THE SYSTEM SHALL reject the import with a descriptive error.
5. THE SYSTEM SHALL NOT execute uploaded code during import or analysis.

## Requirement 2 — Analysis and evidence
1. WHEN a project is analysed THE SYSTEM SHALL classify files as programs or copybooks and resolve COPY statements.
2. THE SYSTEM SHALL report every unsupported construct with file and line.
3. THE SYSTEM SHALL display a dependency graph of programs, copybooks, CALL targets and paragraphs.
4. THE SYSTEM SHALL compute a complexity score using documented heuristics.
5. Every business rule SHALL cite an existing file and a valid line range.

## Requirement 3 — Generation
1. WHEN a user generates a program THE SYSTEM SHALL produce an executable Python project with business logic, Pydantic schemas, FastAPI endpoints, tests, README and a traceability map.
2. THE SYSTEM SHALL use `Decimal` for numeric computation.
3. THE SYSTEM SHALL let the user download the project as a ZIP.

## Requirement 4 — Verification
1. WHEN GnuCOBOL is available THE SYSTEM SHALL execute the original program in a sandbox and the generated Python on identical inputs and compare outputs field by field.
2. WHEN GnuCOBOL is not available THE SYSTEM SHALL mark cases `NOT_VERIFIABLE` and SHALL NOT fabricate results.
3. WHEN a fault is deliberately injected THE SYSTEM SHALL detect the mismatch and report it as `FAILED`.
4. THE SYSTEM SHALL produce a verification report with totals, differences and source references.

## Requirement 5 — Export
1. THE SYSTEM SHALL export the generated project, business rule documentation, dependency graph JSON, migration report, verification report and traceability mapping.

## Requirement 6 — Real corpus
1. THE SYSTEM SHALL be validated against at least two independent external COBOL repositories, recorded in a manifest with commit SHA and license.
