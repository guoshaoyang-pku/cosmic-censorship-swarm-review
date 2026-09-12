#!/bin/bash
# worker-14 checkpoint watcher: appends a record when the inbox grows, the
# outbox changes, or every 15 minutes; bounded to 4 hours.
cd /data3/guoshaoyang/workdir/ai4math-swarm
LOG=artifacts/worker-14/checkpoints.jsonl
END=$((SECONDS+14400))
last_inbox=$(wc -l < comms/inbox/deepseek-flash-14.jsonl 2>/dev/null || echo 0)
last_outbox=$(ls comms/outbox 2>/dev/null | wc -l)
hb=0
while [ $SECONDS -lt $END ]; do
  sleep 60
  n=$(wc -l < comms/inbox/deepseek-flash-14.jsonl 2>/dev/null || echo 0)
  o=$(ls comms/outbox 2>/dev/null | wc -l)
  hb=$((hb+1))
  if [ "$n" != "$last_inbox" ] || [ "$o" != "$last_outbox" ] || [ $hb -ge 15 ]; then
    printf '{"ts":"%s","checkpoint":"watch","inbox_lines":%s,"outbox_files":%s,"hb":%s}\n' \
      "$(date -Is)" "$n" "$o" "$hb" >> "$LOG"
    last_inbox=$n; last_outbox=$o; hb=0
  fi
done
echo "watcher finished at $(date -Is)" >> "$LOG"
