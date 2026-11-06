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

Both runtimes share a fixed clock (`COB_CURRENT_DATE` for GnuCOBOL).

## Mutation analysis

Mutation operators applied to the generated code (one site at a time): drop `ROUNDED`, `<`↔`<=`, `>`↔`>=`,
`+`↔`-` in COMPUTE, constant ± one unit in the last place. A mutant is *killed* when any case's output differs
from the reference (GnuCOBOL output when available). Survivors are reported: they indicate untested behaviour or
equivalent mutants (e.g. ROUNDED on an exact sum). The same mechanism powers the **fault injection** demo.

## Evidence produced (actual runs, GnuCOBOL 3.2.0)

| Target | Cases | Result | Statement coverage | Mutation score |
|---|---|---|---|---|
| Sample `RATEENG` | 127 | 127 VERIFIED | 95.0% | 33/36 (3 equivalent survivors) |
| Sample `PREMCALC` (batch, `fixtures/policies.txt`) | 1 | VERIFIED; output equals `expected-output.txt` | 92.0% | — |
| Sample `RATEENG` with injected fault (drop ROUNDED on RR-BASE-PREMIUM) | 127 | 119 VERIFIED, **8 FAILED** | 95.0% | — |
| Corpus `NBUW001` (mudasin1/COBOL_Sample_March_2026) | 180 | 180 VERIFIED | 96.3% | 35/43 |
| Corpus drivers DRIVENBUW / DRIVESVC / DRIVECLM | 3 | Python output equals upstream golden files | — | — |

The claim generated for every report: *“N of M cases produced identical outputs … This is evidence for these
inputs only, not a proof of equivalence for all inputs.”*

## Bugs found by differential testing during development

* Floating-insertion editing (`$$$,$$9.99`) when high-order digits are truncated: GnuCOBOL prints `$04,059.41`
  for 104,059.41; the first runtime version printed ` $4,059.41`. Found by an edge case (maximum vehicle value),
  fixed in `phoenix_runtime.edit`, now covered by a unit test.
* ACCEPT at end of input: GnuCOBOL moves spaces to the receiver (confirmed with a probe program); the runtime was
  changed accordingly.
