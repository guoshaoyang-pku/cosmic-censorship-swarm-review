#!/usr/bin/env bash
set -u
ROOT=/data3/guoshaoyang/workdir/ai4math-swarm
OUT=$ROOT/runtime/state/metrics.jsonl
while :; do
  ts=$(date -Is)
  sessions=$(tmux ls 2>/dev/null | awk -F: "/astra-|deepseek-flash-/ {n++} END{print n+0}")
  controller=$(tmux ls 2>/dev/null | awk -F: "/^astra-controller:/ {n++} END{print n+0}")
  leads=$(tmux ls 2>/dev/null | awk -F: "/^astra-lead-/ {n++} END{print n+0}")
  workers=$(tmux ls 2>/dev/null | awk -F: "/^deepseek-flash-/ {n++} END{print n+0}")
  dsh=$(pgrep -af "$ROOT.*dsh" | wc -l)
  artifacts=$(find $ROOT/artifacts -type f 2>/dev/null | wc -l)
  comms=$(find $ROOT/comms -type f 2>/dev/null | wc -l)
  checkpoints=$(find $ROOT -iname "checkpoint*" -type f 2>/dev/null | wc -l)
  printf "{\"ts\":\"%s\",\"sessions\":%s,\"controller\":%s,\"leads\":%s,\"workers\":%s,\"dsh\":%s,\"artifacts\":%s,\"comms\":%s,\"checkpoints\":%s}\n" "$ts" "$sessions" "$controller" "$leads" "$workers" "$dsh" "$artifacts" "$comms" "$checkpoints" >> $OUT
  sleep 30
done
