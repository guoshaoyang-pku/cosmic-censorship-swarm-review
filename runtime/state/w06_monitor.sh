#!/bin/bash
# 30-min monitor: log new inbox lines for worker-06 and hash changes of key artifacts.
SNAP=/tmp/w06_hashes_prev.txt
KEY="schemas/af_scc_c0_vacuum.yaml artifacts/formulation/FROZEN.json artifacts/formulation/tools/check_class_schema.py artifacts/formulation/schemas/af_scc_c0_vacuum.yaml artifacts/worker-06/blindspot_report.json"
sha256sum $KEY > $SNAP 2>/dev/null
IN0=$(cat comms/inbox/worker-06.jsonl comms/inbox/deepseek-flash-06.jsonl 2>/dev/null | wc -l)
for i in $(seq 1 30); do
  sleep 60
  IN1=$(cat comms/inbox/worker-06.jsonl comms/inbox/deepseek-flash-06.jsonl 2>/dev/null | wc -l)
  if [ "$IN1" != "$IN0" ]; then
    echo "INBOX_NEW at $(date -Is): $IN0 -> $IN1"
    tail -n $((IN1-IN0)) comms/inbox/worker-06.jsonl comms/inbox/deepseek-flash-06.jsonl 2>/dev/null | head -20
    IN0=$IN1
  fi
  sha256sum $KEY > /tmp/w06_hashes_now.txt 2>/dev/null
  if ! diff -q $SNAP /tmp/w06_hashes_now.txt >/dev/null; then
    echo "HASH_CHANGE at $(date -Is):"; diff $SNAP /tmp/w06_hashes_now.txt | head -20
    cp /tmp/w06_hashes_now.txt $SNAP
  fi
done
echo "MONITOR_DONE at $(date -Is)"
