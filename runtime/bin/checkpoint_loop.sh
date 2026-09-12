#!/bin/bash
# Astra 15-minute checkpoint loop: 16 cycles over 4 hours.
# Each cycle: flock -> ingest outbox -> apply events to research_map.json -> checkpoint snapshot.
set -u
ROOT="/data3/guoshaoyang/workdir/ai4math-swarm"
cd "$ROOT" || exit 1
START=$(date +%s)
echo "[loop] start $(date -Iseconds) pid=$$" >> runtime/logs/astra-cycle.log
for i in $(seq 1 16); do
  echo "[loop] cycle $i begin $(date -Iseconds)" >> runtime/logs/astra-cycle.log
  python3 research_map/run_cycle.py --label "auto-$i" >> runtime/logs/astra-cycle.log 2>&1
  echo "[loop] cycle $i end $(date -Iseconds) exit=$?" >> runtime/logs/astra-cycle.log
  if [ "$i" -lt 16 ]; then sleep 900; fi
done
echo "[loop] done $(date -Iseconds) elapsed=$(( $(date +%s) - START ))s" >> runtime/logs/astra-cycle.log
