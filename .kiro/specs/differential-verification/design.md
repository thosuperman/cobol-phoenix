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
