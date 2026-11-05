#!/usr/bin/env bash
# Start a verification run for the latest non-mutant generation of a project and wait for it.
# usage: scripts/verify-run.sh <project-id> [mutation_analysis=true] [api=http://localhost:8000/api]
set -euo pipefail
PID="$1"; MUT="${2:-true}"; B="${3:-http://localhost:8000/api}"
until curl -sf "$B/health" >/dev/null; do sleep 1; done
G=$(curl -sf "$B/projects/$PID/generations" | python3 -c "import json,sys; print([g for g in json.load(sys.stdin) if not g['mutation_id']][0]['id'])")
R=$(curl -sf -X POST "$B/generations/$G/verify" -H 'Content-Type: application/json' -d "{\"mutation_analysis\":$MUT}" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
while :; do
  S=$(curl -sf "$B/runs/$R" | python3 -c "import json,sys; print(json.load(sys.stdin)['status'])")
  [ "$S" = completed ] || [ "$S" = error ] && break
  sleep 3
done
curl -sf "$B/runs/$R" | python3 -c "
import json,sys; r=json.load(sys.stdin); print(r['status'], r.get('error') or '', json.dumps(r['summary']))
m=r.get('mutation')
if m:
    print('mutation', m['killed'], '/', m['evaluated'], m['score_pct'])
    [print('  survived', x['id'], x['detail']) for x in m['mutants'] if x['status']!='killed']
"
