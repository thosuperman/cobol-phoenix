## Inspiration

Banks and insurers still calculate premiums, interest and claims in COBOL written decades ago. The logic is valuable
and usually correct; the people who wrote it are gone. Every modernization project then stalls on one question:

> *Does the new system behave exactly like the old one?*

Translating COBOL line by line — by hand or with an LLM — produces code that nobody can trust without months of
parallel runs. We wanted to make that question answerable on day one, with **evidence instead of confidence**:
every business rule cited to real source lines, every generated statement traceable back to COBOL, and every build
checked against the original program actually running.

The Kiroween *Resurrection* category fit perfectly: bring a "dead" technology back to life — but prove it is the
same creature.

## What it does

COBOL Phoenix is a modernization workspace in four acts:

1. **The dead system** — import COBOL from files, a ZIP or a GitHub repository (validated, never executed on import).
2. **The discovery** — a deterministic parser builds an intermediate representation, a dependency graph and business
   rules; unsupported constructs are reported with their file and line, never silently dropped.
3. **The resurrection** — one click generates an executable Python/FastAPI project with `Decimal` arithmetic,
   Pydantic schemas derived from `PICTURE` clauses, tests, and a map from every Python statement to its COBOL lines.
4. **The proof** — the original program runs in a sandboxed GnuCOBOL container while the generated Python runs beside
   it on the same inputs; outputs are compared field by field, and mutation analysis measures how strong the tests are.

Try it at **https://cobol.beauty** — no login, the sample and an external insurance repository are pre-loaded.

## How we built it

**Spec first, with Kiro.** Before any code we wrote Kiro steering documents and four specs (product, COBOL analysis,
Python generation, differential verification) with EARS-style requirements, designs and requirement-linked tasks.
The most valuable piece was a steering file, `cobol-semantics.md`, that states the GnuCOBOL behaviours the runtime must
reproduce. Hooks turned the specs into quality gates: a `PostTaskExec` hook runs the whole suite — including real
GnuCOBOL differential tests — after every spec task, and a `Stop` hook runs a security scan. Much of the initial
implementation was written outside the Kiro IDE following those specs; Kiro IDE then executed spec tasks against the
same steering and hooks: `INSPECT` support, OpenAPI request examples, and validity-aware test placement.

**A real COBOL front end, no AI guessing.** A fixed/free-format lexer, a `COPY … REPLACING` preprocessor and a
recursive-descent parser produce an IR where every node carries a file and line range. Rules, the dependency graph and
the generated code all come from that IR.

**COBOL data is bytes.** The generated Python runs on a small runtime where each record is a `bytearray` and each data
item is a typed view, so `REDEFINES`, group `MOVE`s and `CALL … BY REFERENCE` behave like COBOL. Numbers are
`Decimal` with COBOL's rules. For a receiving field with $d$ digits of which $s$ are decimals, a store without
`ROUNDED` truncates toward zero, and `ROUNDED` rounds half away from zero:

$$
\operatorname{trunc}_s(x) = \operatorname{sgn}(x)\,\frac{\lfloor |x|\cdot 10^{s} \rfloor}{10^{s}},
\qquad
\operatorname{round}_s(x) = \operatorname{sgn}(x)\,\frac{\lfloor |x|\cdot 10^{s} + \tfrac12 \rfloor}{10^{s}}
$$

and, without `ON SIZE ERROR`, high-order digits are silently dropped: the stored integer part is
$\lfloor |x| \rfloor \bmod 10^{\,d-s}$. Intermediate results use a 64-digit truncating context, which is how
`10 / 3 * 3` ends up as `9.99` in a `9(5)V99` field — exactly as in GnuCOBOL.

**Proof by differential testing.** For a callable program we generate a COBOL harness that `ACCEPT`s each `USING`
parameter, `CALL`s the program and `DISPLAY`s the results; the generated Python CLI speaks the same protocol, so both
receive identical bytes. Test inputs come from fixtures plus values derived from the code itself: every comparison
with a literal $L$ yields $L-\varepsilon,\ L,\ L+\varepsilon$ with $\varepsilon = 10^{-s}$; every 88-level and
`EVALUATE WHEN` yields matching and non-matching values; seeded random records add combinations. Fixtures are traced
through the generated Python so each boundary is attached to a case that actually reaches its statement.

**Measuring the tests.** Passing cases are evidence, not proof, so we inject single faults into the generated code
(drop a `ROUNDED`, turn `<` into `<=`, …) and count how many the suite catches:

$$
\text{mutation score} = \frac{\text{mutants killed}}{\text{mutants evaluated}}
$$

**Product.** FastAPI + SQLAlchemy backend, Next.js 16 / React 19 / Tailwind 4 frontend, Docker Compose with a
network-less GnuCOBOL runner (read-only filesystem, no capabilities, resource limits), deployed on AWS Lightsail
behind Caddy.

**Results (all from real runs, GnuCOBOL 3.2.0):**

| Target | Cases identical | Statement coverage | Mutation score |
|---|---|---|---|
| Original sample `RATEENG` (auto insurance rating) | 127 / 127 | 95.8 % | 31 / 36 |
| `NBUW001` from an independent public insurance repository | 180 / 180 | 96.3 % | 36 / 43 |

Removing one `ROUNDED` makes 8 cases fail — down to the cent. The generated Python of that repository's three test
drivers reproduces its golden files byte for byte, and two more public repositories (banking, ledger) parse with zero
errors while 365 unsupported constructs are reported rather than ignored.

## Challenges we ran into

- **Matching GnuCOBOL exactly.** Sign overpunch bytes, how signed numbers are `DISPLAY`ed, division by zero leaving the
  receiver unchanged, alphanumeric-to-numeric moves and `ACCEPT` at end of input all had to be confirmed with small
  probe programs in the sandbox — documentation alone was not enough.
- **Our own runtime had a bug the product caught.** An edge case with the maximum vehicle value failed: GnuCOBOL printed
  `$04,059.41` where we printed ` $4,059.41`, because when significant high-order digits are truncated away GnuCOBOL
  treats zero suppression as already finished. Differential testing found in seconds what reading manuals would not.
- **A flaky mutation score.** The same code scored 33/36 on a laptop and 30/36 on the server. The cause: mutants ran
  one after another in one workspace, and Python reused a cached `.pyc` from the previous mutant when two files had the
  same size and timestamp. Running generated code with `python -B` fixed it, and a regression test now guards it.
- **Making tests reach deep rules.** Generic boundary values were often rejected by an earlier validation rule (a
  21-year-old driver "licensed for 20 years"), so the targeted rule never ran. Coverage-guided and then validity-aware
  placement solved most of these; mutation analysis showed us exactly which gaps remained — and even exposed a rule in
  the external repository that can never fire.
- **Honesty under a deadline.** It is tempting to say "behaviourally equivalent". We built the product so it cannot:
  statuses are `VERIFIED`, `FAILED`, `NOT_VERIFIABLE` or `UNSUPPORTED`, and every report says the evidence covers the
  executed inputs only.

## What we learned

- **Equivalence is a body of evidence, not a claim.** Field-level diffs, statement coverage and mutation scores
  together say far more than "the tests pass".
- **COBOL semantics live in the details** — truncation, signs and editing — and a byte-accurate model was what made
  REDEFINES, group moves and `CALL BY REFERENCE` simply work.
- **Steering beats prompting.** Writing the domain rules into Kiro steering meant Kiro's tasks followed them without
  being reminded — it even refused to guess GnuCOBOL's sign handling for `INSPECT` on signed numbers and reported those
  as unsupported, exactly as the steering asked.
- **Hooks make "done" mean done.** With the full GnuCOBOL differential suite running after every spec task, a change
  cannot be finished while behaviour differs from the original program.

## What's next

File I/O adapters (sequential and indexed files mapped to repositories), `UNSTRING` and `SEARCH`, IBM dialect options
such as `TRUNC` and `NUMPROC`, and a CI mode that keeps the differential suite running while COBOL is still the
system of record.
