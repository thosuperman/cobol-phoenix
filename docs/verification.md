# Differential verification

## Status values

| Status | Meaning |
|---|---|
| `VERIFIED` | Both GnuCOBOL and the generated Python ran the case; outputs are identical byte-for-byte (and therefore field-by-field) |
| `FAILED` | Both ran; at least one output field (or control flow / error behaviour) differs |
| `NOT_VERIFIABLE` | The original program could not be executed (no executor, compile error, timeout, binary USING records). Nothing is compared and nothing is assumed |
| `UNSUPPORTED` | The Python run reached a construct outside the supported subset |

Rule statuses add `NOT_EXERCISED` (no compared case executed the rule) and `NOT_RUN` (no run yet). A rule is
`FAILED` only when a failing case executed it **and** the differing fields include one of the rule's outputs (or
the difference cannot be attributed to fields).

## Test case generation (deterministic)

1. **Fixtures** — `phoenix-fixtures.json` in the project or entered in the UI.
2. **Boundary values** from the IR for every input field: `X op literal` → literal −1 ulp / = / +1 ulp;
   `X op Y` where Y receives literal MOVEs → those literals ±1 ulp; 88-level values and THRU bounds;
   `EVALUATE X WHEN literal`; non-matching values.
3. **Edge values** — zero, maximum, negative maximum, SPACES.
4. **Seeded random combinations** (`random.Random(20261031)`).
5. **Coverage-guided placement** — fixtures are first run through the generated Python with line tracing; each
   boundary value is applied to a fixture that executes the statement it was derived from; table-element values
   are applied to every occurrence.
6. **Validity-aware placement** — an earlier validation rule can still reject a placed boundary case before it
   reaches its statement S (sample: `PR-DRIVER-AGE = 21` on a fixture with `PR-YEARS-LICENSED = 20` exits with
   reason 107 before the age-band `EVALUATE` at `cobol/RATEENG.cbl:137`). Each boundary case is therefore traced
   through the generated Python (never the uploaded COBOL; subprocess with a timeout, results cached by stdin).
   If it misses S, the search tries (a) the other fixtures that execute S, in fixture order, then (b) the
   preferred fixture with *guard fields* adjusted: input fields read by IF / EVALUATE / PERFORM UNTIL statements
   that ran before S on the failing run, set only to values the candidate collector produced, one field at a
   time and then in pairs. At most 24 newly traced inputs per boundary value. The description records the
   fixture and every adjusted field (`… [on fixture young-sports-monthly]`, `… [on fixture F; PR-YEARS-LICENSED=2]`).
   When the search is exhausted, the original placement is kept and annotated `[target S not reached]`. The search
   has no randomness. Without a generated project or a working trace, placement is exactly step 5. Seeded random
   cases are unchanged.

Both runtimes share a fixed clock (`COB_CURRENT_DATE` for GnuCOBOL).

## Mutation analysis

Mutation operators applied to the generated code (one site at a time): drop `ROUNDED`, `<`↔`<=`, `>`↔`>=`,
`+`↔`-` in COMPUTE, constant ± one unit in the last place. A mutant is *killed* when any case's output differs
from the reference (GnuCOBOL output when available). Survivors are reported: they indicate untested behaviour or
equivalent mutants (e.g. ROUNDED on an exact sum). The same mechanism powers the **fault injection** demo.

Validity-aware placement raised the sample RATEENG score from 30/36 to 31/36: `relop@cobol/RATEENG.cbl:138`
(`PR-DRIVER-AGE < 21` → `<=`) is now killed by the `PR-DRIVER-AGE = 21` case, which reaches the age band.
`relop@cobol/RATEENG.cbl:128` (`UNTIL WS-ST-SUB > 8` → `>=`) still survives, and placement cannot fix it. The
mutant only differs for the 8th state-table entry (AZ). The only AZ fixture is rejected at the vehicle-class check,
and the collector derives no PR-STATE candidates from the VALUE-initialised `ST-CODE` table. This is a known gap.

## Evidence produced (actual runs, GnuCOBOL 3.2.0)

| Target | Cases | Result | Statement coverage | Mutation score |
|---|---|---|---|---|
| Sample `RATEENG` | 127 | 127 VERIFIED | 95.8% | 31/36 (4 equivalent survivors, 1 untested boundary: `relop@cobol/RATEENG.cbl:128`) |
| Sample `PREMCALC` (batch, `fixtures/policies.txt`) | 1 | VERIFIED; output equals `expected-output.txt` | 92.0% | — |
| Sample `RATEENG` with injected fault (drop ROUNDED on RR-BASE-PREMIUM) | 127 | 115 VERIFIED, **12 FAILED** | 95.8% | — |
| Corpus `NBUW001` (mudasin1/COBOL_Sample_March_2026) | 180 | 180 VERIFIED | 96.3% | 36/43 |
| Corpus drivers DRIVENBUW / DRIVESVC / DRIVECLM | 3 | Python output equals upstream golden files | — | — |

The claim generated for every report: *“N of M cases produced identical outputs … This is evidence for these
inputs only, not a proof of equivalence for all inputs.”*

## Bugs found during development

* Mutation analysis reused stale bytecode: mutants were run one after another in one workspace with
  `python -E` (which ignores `PYTHONDONTWRITEBYTECODE`); two equal-size mutants written within the same second
  could execute the previous mutant's cached `.pyc`, making scores timing-dependent (sample RATEENG showed 33/36
  locally and 30/36 on the slower server). Fixed with `python -B` and a cache-free workspace copy; regression test
  `test_mutants_evaluated_in_sequence_match_isolated_runs`. Correct scores at that point: RATEENG 30/36, NBUW001 36/43 (RATEENG is 31/36 with validity-aware placement).

### Found by differential testing

* Floating-insertion editing (`$$$,$$9.99`) when high-order digits are truncated: GnuCOBOL prints `$04,059.41`
  for 104,059.41; the first runtime version printed ` $4,059.41`. Found by an edge case (maximum vehicle value),
  fixed in `phoenix_runtime.edit`, now covered by a unit test.
* ACCEPT at end of input: GnuCOBOL moves spaces to the receiver (confirmed with a probe program); the runtime was
  changed accordingly.
