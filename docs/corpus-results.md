# External corpus results

Repositories are fetched by `scripts/fetch-corpus.sh` at the commits pinned in `corpus/manifest.json` into
`corpus/repos/` (git-ignored). Their code is not copied into this repository. Licenses: the insurance and banking
repositories contain no license file (all rights reserved by default) and are used only as local test inputs; the
ledger repository is MIT. None of their Python bridges, generated code or AI features were used.

## Upstream build & test in the sandbox (GnuCOBOL 3.2.0, `cobol-phoenix-runner` image)

| Repository @ commit | Upstream build | Upstream tests |
|---|---|---|
| mudasin1/COBOL_Sample_March_2026 @ `be70080` | `make all` — 3 drivers compiled | `make test` — 3/3 golden files OK |
| achalc/cobol-bank-demo @ `5a85e52` | `make build` — 2 programs compiled | `test.sh` — 53 passed, 0 failed |
| albertdobmeyer/cobol-legacy-ledger @ `4ec2a1f` | `scripts/build.sh` — 10/10 programs compiled (with `-free`); payroll: 7/8 compile, `RISKCHK.cob` fails: *unknown device 'STANDARD-INPUT'; not defined in SPECIAL-NAMES* | `bin/SMOKETEST` — `SMOKE-TEST|PASS` |

## COBOL Phoenix analysis (automated in `backend/tests/test_corpus.py`)

| Repository | Programs | Parse errors | Unsupported constructs reported |
|---|---|---|---|
| Insurance | 6 | 0 | 0 |
| Banking | 2 | 0 | 159 (WRITE 64, CLOSE 38, OPEN 37, READ 19, INSPECT 1) |
| Ledger (`COBOL-BANKING/`) | 18 | 0 | 206 (OPEN 64, READ 39, CLOSE 38, WRITE 21, ACCEPT FROM COMMAND-LINE/ENVIRONMENT 20, UNSTRING 10, ALTER 5, INSPECT 1 (CONVERTING in `DISPUTE.cob`; the 6 `INSPECT … TALLYING … FOR ALL` in `RISKCHK.cob` are now parsed), GO TO DEPENDING 2, REPORT SECTION, INITIATE, TERMINATE, SD, SORT, RETURN) |

Parser limitations surfaced by the corpus and fixed during development: READ … AT END / NOT AT END phrases
inside inline PERFORMs, free-format auto-detection (tokens crossing column 72), `:TAG:` pseudo-text words,
ACCEPT FROM COMMAND-LINE/ENVIRONMENT reported as unsupported instead of parse errors.

## Migration unit: NBUW001 (new business underwriting)

* Selected because it is a self-contained CALLable capability (LINKAGE: `WS-POLICY-MASTER-REC` 963 bytes,
  `LK-UW-RESULT-CODE`, `LK-UW-ERROR-MSG`) with eligibility, rating and premium rules (NB-101 … NB-1001).
* Generated: `ProgramNbuw001` (215 statements traced, 0 unsupported) and `POST /api/v1/nbuw001/execute`.
* Fixtures: `corpus/fixtures/nbuw001-fixtures.json` (12 scenarios written for this project from reading the
  source, including the upstream driver's golden case).
* Differential run: 180/180 VERIFIED, 207/215 statements executed (96.3%), result codes 00, 02, 12–26 exercised.
* Mutation analysis: 36/43 killed. Survivors: NB-303 lines 251–252 (unreachable — every plan caps the issue age
  at ≤ 60, so “age > 60” can never be true after validation), line 365 and the ROUNDED on exact sums at 406/415
  (equivalent mutants), and ROUNDED at 366/386, whose rounding no current input exercises.
* The generated Python of the three upstream drivers reproduces `tests/expected/*.out` byte-for-byte.
