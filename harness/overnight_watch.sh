#!/usr/bin/env bash
set -u
ROOT=/data3/guoshaoyang/workdir/ai4math-swarm
OUT=$ROOT/runtime/state/overnight_watch.jsonl
while :; do
 ts=$(date -Is)
 ctrl=$(tmux ls 2>/dev/null | grep -c '^controller-' || true)
 leads=$(tmux ls 2>/dev/null | grep -c '^lead-' || true)
 workers=$(tmux ls 2>/dev/null | grep -E '^worker-[0-9]{3}:' | wc -l)
 artifacts=$(find $ROOT/artifacts -type f 2>/dev/null | wc -l)
 comms=$(find $ROOT/comms/outbox -type f 2>/dev/null | wc -l)
 instances=$(find $ROOT/runtime/instances -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
 form=$(find $ROOT/artifacts/formulation -type f -mmin -10 2>/dev/null | wc -l)
 audit=$(find $ROOT/artifacts/audit -type f -mmin -10 2>/dev/null | wc -l)
 printf '{"ts":"%s","controller":%s,"leads":%s,"workers":%s,"artifacts":%s,"comms":%s,"instances":%s,"formulation_recent":%s,"audit_recent":%s}\n' "$ts" "$ctrl" "$leads" "$workers" "$artifacts" "$comms" "$instances" "$form" "$audit" >> "$OUT"
 sleep 300
done
