#!/bin/bash
# Worker 06 inbox watcher: exits when an assignment/protocol appears, or after max seconds.
MAX=900; i=0
while [ $i -lt $MAX ]; do
  if ls comms/inbox/* >/dev/null 2>&1 || [ -f comms/PROTOCOL.md ]; then
    echo "WATCH_HIT at $(date -Is)"; ls -la comms/inbox/ comms/PROTOCOL.md 2>/dev/null; exit 0
  fi
  sleep 10; i=$((i+10))
done
echo "WATCH_TIMEOUT after ${MAX}s at $(date -Is)"
