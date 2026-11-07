# Resurrecting COBOL with receipts: how we built COBOL Phoenix

*Draft — review, add your own experience, then publish on a third-party platform (dev.to, Medium, Hashnode…) by 4 Dec 2026, 2:00 pm PT.*

**This post is written as part of the Kiroween 2026 hackathon.**

- **Live demo:** [cobol.beauty](https://cobol.beauty) — no login, sample and an external repository pre-loaded
- **Source code:** [github.com/thosuperman/cobol-phoenix](https://github.com/thosuperman/cobol-phoenix) (Apache-2.0)
- **Demo video:** *(add YouTube link)*

Every legacy-modernization pitch promises to “convert your COBOL”. Converting is not the problem. The problem is the
question every architect asks afterwards: **how do we know the new code behaves exactly like the old one?**
COBOL Phoenix is our answer: understand the program deterministically, generate code you can trace line by line,
and prove behaviour by running the original and the generated code side by side.

## Rule 1: no guessing in the core
We wrote a real COBOL front end in Python — a fixed/free-format lexer, a COPY … REPLACING preprocessor and a
recursive-descent parser — producing an intermediate representation where every node carries a file and line
range. Business rules, the dependency graph and the generated code are all derived from that IR. Anything outside
the supported subset (file I/O, UNSTRING, ALTER, EXEC SQL…) is reported with its location and becomes an explicit
`UnsupportedConstruct` in the generated code. Nothing is silently dropped.

## Rule 2: COBOL data is bytes
The generated Python runs on a small runtime where each record is a `bytearray` and each data item a typed view.
That single decision makes REDEFINES, group MOVEs and CALL BY REFERENCE behave like COBOL instead of like Python
dictionaries. Numbers are `Decimal`, with COBOL's truncation, ROUNDED (half away from zero), sign overpunch and
numeric-editing rules — each confirmed against GnuCOBOL with tiny probe programs.

## Rule 3: prove it
For a callable program we generate a COBOL harness that ACCEPTs each USING parameter, CALLs the program and
DISPLAYs the results; the generated Python CLI speaks the same protocol. Identical bytes go into GnuCOBOL (inside a
container with no network, a read-only filesystem and resource limits) and into Python. Outputs are decoded with the
record layout and compared field by field.

Test inputs come from fixtures plus values derived from the code itself: every comparison against a literal yields
boundary values, every 88-level and EVALUATE WHEN yields matching and non-matching values. Then we got smarter:
we trace the fixtures through the generated Python and attach each boundary value to a fixture that actually
executes the statement it came from — *coverage-guided placement*. On a public insurance repository that raised the
mutation score from 67% to over 80% without a single hand-written test.

## The best bug was our own
An edge case with the maximum vehicle value failed. GnuCOBOL printed `$04,059.41`; our runtime printed
` $4,059.41`. When significant high-order digits are truncated away, GnuCOBOL considers zero suppression already
finished. We would never have found that by reading documentation. Differential testing found it in seconds.

## Trust, measured
Passing cases are evidence, not proof, so we measure the tests themselves: mutation analysis generates single-fault
variants (drop a ROUNDED, flip a `<` to `<=`) and checks the suite catches them. In the UI you can inject one on
purpose — remove one ROUNDED and watch eight cases fail by exactly one cent. On the insurance repository the
surviving mutants pointed at a business rule that can never fire, because every plan caps the issue age below the
rule's threshold. That is the kind of finding a modernization team actually needs.

## Spec-first with Kiro
We started from an empty repository by writing Kiro steering documents (product principles, COBOL semantics,
security, testing), four specs with EARS requirements, designs and task lists, and hooks. The steering file on
COBOL semantics turned out to be the most valuable artifact: it was the checklist we tested the runtime against.

We then used Kiro IDE to execute spec tasks: support for `INSPECT … TALLYING / REPLACING`, OpenAPI request
examples generated from fixtures, and *validity-aware placement*, which re-places a boundary case when an earlier
validation rule would reject it before it reaches its target statement. Because a `PostTaskExec` hook runs the whole suite — including the differential
tests against GnuCOBOL — every Kiro task had to keep the generated Python behaviourally identical to the original.
Kiro even refused to guess GnuCOBOL's sign handling for INSPECT on signed numbers and reported those as
unsupported instead, exactly as our steering asked. *(Add your own impressions of working with Kiro here.)*

## Results
- Original sample: 127/127 cases identical to GnuCOBOL 3.2.0, 95.8% statement coverage, mutation score 31/36;
  injected fault caught (8 failing cases).
- Independent insurance repository: 180/180 on the underwriting program, 96.3% coverage, mutation score 36/43;
  generated drivers reproduce upstream golden files.
- Two more repositories: 20 programs parsed with zero errors; 365 unsupported constructs reported, not ignored.

## Try it
Open [cobol.beauty](https://cobol.beauty), click **Import sample → Generate → Verify**, then inject a fault and watch
it get caught. Or run it yourself with Docker:

```bash
git clone https://github.com/thosuperman/cobol-phoenix && cd cobol-phoenix
docker compose up --build
```

COBOL Phoenix is open source under Apache-2.0:
[github.com/thosuperman/cobol-phoenix](https://github.com/thosuperman/cobol-phoenix).
Preserve the logic. Rebuild the future.

#KiroweenHackathon26 #Kiro #COBOL #Python
