#!/bin/bash
# flash-04 assignment watcher: exits 0 when an assignment-looking file appears for flash-04
# or any group lead writes to comms/inbox/outbox; exits 3 after DURATION seconds.
DURATION=${1:-10800}
END=$(( $(date +%s) + DURATION ))
while [ "$(date +%s)" -lt "$END" ]; do
  found=$(find comms/inbox -type f -name '*.json' 2>/dev/null | head -5)
  if [ -n "$found" ]; then
    echo "ASSIGNMENT_FILES:"; echo "$found"; exit 0
  fi
  # sideways lead packets mentioning flash-04 or assignment
  hit=$(grep -rlE 'flash-04|"assignment"|"assign"' comms/outbox 2>/dev/null | head -5)
  if [ -n "$hit" ]; then echo "LEAD_PACKETS:"; echo "$hit"; exit 0; fi
  sleep 20
done
echo "NO_ASSIGNMENT_AFTER_${DURATION}s"; exit 3
