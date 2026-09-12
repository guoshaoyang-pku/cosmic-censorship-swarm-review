#!/usr/bin/env bash
set -u
ROOT=/data3/guoshaoyang/workdir/ai4math-swarm
OUT=$ROOT/runtime/state/overnight_watch.jsonl
mkdir -p "$ROOT/runtime/state"
while :; do
 ts=$(date --iso-8601=seconds)
 names=$(tmux ls 2>/dev/null | cut -d: -f1 || true)
 project_tmux=$(printf '%s\n' "$names" | awk '/^(controller-|astra-controller|lead-(formulation|literature|numerics|audit)-|worker-(formulation|literature|numerics|audit)-)/{n++} END{print n+0}')
 controller=$(printf '%s\n' "$names" | awk '/^controller-|^astra-controller/{n++} END{print n+0}')
 leads=$(printf '%s\n' "$names" | awk '/^lead-(formulation|literature|numerics|audit)-/{n++} END{print n+0}')
 workers=$(printf '%s\n' "$names" | awk '/^worker-(formulation|literature|numerics|audit)-/{n++} END{print n+0}')
 counts=$(tail -1 "$ROOT/runtime/state/counts.tsv" 2>/dev/null || true)
 artifacts=$(echo "$counts" | sed -n 's/.*artifacts=\([0-9]*\).*/\1/p'); : ${artifacts:=0}
 quota=$(cat "$ROOT/runtime/state/quota_circuit_until" 2>/dev/null || echo 0)
 cp=$(ls -1t "$ROOT/runtime/state/checkpoints"/ckpt-*.json 2>/dev/null | head -1 || true)
 comms=$(wc -l < "$ROOT/comms/inbox/astra.jsonl" 2>/dev/null || echo 0)
 printf '{"ts":"%s","sessions":%s,"project_tmux":%s,"controller":%s,"leads":%s,"workers":%s,"artifacts":%s,"comms":%s,"quota_until":%s,"checkpoint":"${cp##*/}"}\n' "$ts" "$project_tmux" "$controller" "$leads" "$workers" "$artifacts" "$comms" "$quota" >> "$OUT"
 sleep 300
done
