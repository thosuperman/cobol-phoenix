# Design — Differential verification

## Executors
| Executor | Where | Isolation |
|---|---|---|
| `queue` | Docker Compose; backend writes `jobs/<id>/READY`, runner sidecar polls | runner: `network_mode: none`, read-only root, `cap_drop: ALL`, `no-new-privileges`, mem/cpu/pids limits, tmpfs scratch, rlimits per process |
| `docker` | Local dev; backend runs `docker run --rm --network none --memory 512m --cpus 1 --pids-limit 128 --read-only --cap-drop ALL -v job:/job` | one container per job, only that job mounted |
| `disabled` | no runtime | every case `NOT_VERIFIABLE` |

## Harness
For a program with `PROCEDURE DIVISION USING p1 p2 ...` the harness declares records with the
same layout (copied from the IR's resolved data items), reads one line per parameter with
`ACCEPT`, `CALL "<prog>" USING ...`, then `DISPLAY` each parameter on its own line, followed
by a sentinel `*PHOENIX-END*`. The Python side performs the identical protocol in `cli.py`.

## Comparison
Output lines are split per parameter and decoded with the record layout. Each elementary field is
compared; numeric fields record both values and the decimal difference. Raw-byte mismatches in
FILLER are reported but flagged as `filler`.

## Determinism
`COB_CURRENT_DATE` is set for GnuCOBOL; the Python runtime receives the same fixed date.

## Validity-aware placement
Coverage-guided placement (task 8) picks a fixture that executes the boundary's source statement S,
but the modified case can be rejected earlier (sample: `PR-DRIVER-AGE = 21` on a fixture with
`PR-YEARS-LICENSED = 20` exits with reason 107 before the EVALUATE at `cobol/RATEENG.cbl:137`).

**Callback.** `generate_cases(..., reaches=None)` takes `reaches(inputs, key) -> bool`, a
`PythonTracer` instance built in `services.py` from the existing traced `run_python(..., trace=True)`
+ `coverage_map(trace)`. It encodes `inputs` to stdin, runs the generated Python (our deterministic
code, subprocess + timeout), and returns whether `key` is in the executed statement keys. Results
(the full key set) are cached by encoded stdin, so a stdin is traced at most once per generation.
Optional `prefetch(list[inputs])` traces many inputs in one subprocess batch: the preferred
placements are prefetched up front, and each search's candidates are batched. `reaches` may raise
`TraceUnavailable`, which disables the search for the rest of the generation.

**Search order** for each boundary value with statement key S (stop at first case that reaches S):
1. Preferred fixture (task 8 choice).
2. Other fixtures whose coverage contains S, in fixture order.
3. Guard-field adjustments on the preferred fixture. Guard fields = input fields read
   (`stmt_access().reads`) by IF / EVALUATE / PERFORM UNTIL statements in S's source file that
   executed on the failing run and whose source line precedes S's line, excluding the boundary
   field itself; ordered by statement line, then item id. Try each guard's collected candidates in
   collector order, one field at a time, then pairs of guard fields (first candidate of each pair
   order).
4. Bound: `PLACEMENT_MAX_ATTEMPTS = 24` traced runs per boundary value (cache hits do not count;
   the preferred placement is attempt 1 unless its stdin was already traced). On exhaustion keep
   the original placement and append `[target S not reached]`.

**Determinism.** No randomness in the search; iteration is over fixture order, sorted ids and
collector order; the cache is keyed by stdin. Random cases (seeded) are unaffected.

**Fallback.** `reaches is None` (no generated project, Python run fails, or tracing unavailable) →
behaviour identical to task 8. The search uses only the generated Python, so it works with the
`disabled` executor; COBOL verification status is unaffected.

**Descriptions.** While the search is active, every boundary case records `[on fixture X]`,
including the default fixture; e.g. `PR-DRIVER-AGE = 21 — equal to 21 (cobol/RATEENG.cbl:137)
[on fixture F2; PR-YEARS-LICENSED=3]`.

**Measured result.** On the sample RATEENG, `relop@cobol/RATEENG.cbl:138` is killed (score
30/36 → 31/36). Known gap (accepted): `relop@cobol/RATEENG.cbl:128` survives; the mutant only
differs for the 8th state-table entry (AZ), and the collector derives no PR-STATE candidates from
the VALUE-initialised ST-CODE table.
