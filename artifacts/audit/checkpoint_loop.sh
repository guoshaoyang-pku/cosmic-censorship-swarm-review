#!/usr/bin/env bash
# A1 checkpoint loop: 15 ticks x 15 min = 3h45m from swarm start + ~15 min.
# Each tick re-runs the audit, snapshots the report, and appends one log line.
set -u
ROOT="/data3/guoshaoyang/workdir/ai4math-swarm"
cd "$ROOT" || exit 1
mkdir -p artifacts/audit/checkpoints
TICKS="${1:-15}"
INTERVAL="${2:-900}"
for i in $(seq 1 "$TICKS"); do
  TS=$(date +%Y%m%dT%H%M%S)
  python3 artifacts/audit/audit_run.py --quiet >> artifacts/audit/checkpoints/loop.log 2>&1
  if [ -f artifacts/audit/reports/LATEST.json ]; then
    cp artifacts/audit/reports/LATEST.json "artifacts/audit/checkpoints/ckpt-$TS.json"
    python3 - "$TS" "$i" <<'PY' >> artifacts/audit/checkpoints/checkpoint_log.jsonl
import json, sys, hashlib
from pathlib import Path
ROOT = Path('.')
ts, i = sys.argv[1], int(sys.argv[2])
r = json.loads((ROOT/'artifacts/audit/reports/LATEST.json').read_text())
map_sha = hashlib.sha256((ROOT/'research_map/research_map.json').read_bytes()).hexdigest()
inv = r.get('inventory', [])
line = {
  'checkpoint': i, 'at': ts, 'elapsed_since_swarm_start_s': r.get('elapsed_since_swarm_start_s'),
  'map_sha256_12': map_sha[:12], 'report_sha256_12': str(r.get('report_sha256'))[:12],
  'violations': r['summary']['total'], 'critical': r['summary']['critical'],
  'by_hf': r['summary']['by_hf'], 'citations': r['citation_support']['n'],
  'citation_score': r['citation_support']['score'],
  'nodes_with_artifacts': sum(1 for x in inv if x['exists']), 'nodes_total': len(inv),
  'gates': r['gates'],
}
print(json.dumps(line, sort_keys=True))
PY
  fi
  echo "[$(date -Is)] checkpoint $i/$TICKS done" >> artifacts/audit/checkpoints/loop.log
  [ "$i" -lt "$TICKS" ] && sleep "$INTERVAL"
done
echo "[$(date -Is)] checkpoint loop complete" >> artifacts/audit/checkpoints/loop.log
