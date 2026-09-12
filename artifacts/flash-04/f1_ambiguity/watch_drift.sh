#!/bin/bash
# Exit 0 when the frozen F1 pin, the frozen F1 file, or the inbound channel changes;
# exit 3 after ~2.5h with no change.
FROZEN=artifacts/formulation/FROZEN.json
SCHEMA=artifacts/formulation/schemas/af_wcc_vacuum.yaml
INBOX=comms/inbox/deepseek-flash-04.jsonl
F0=$(sha256sum "$FROZEN" | cut -d' ' -f1); S0=$(sha256sum "$SCHEMA" | cut -d' ' -f1)
I0=$(stat -c %Y "$INBOX" 2>/dev/null || echo 0)
for _ in $(seq 1 300); do
  sleep 30
  F=$(sha256sum "$FROZEN" | cut -d' ' -f1); S=$(sha256sum "$SCHEMA" | cut -d' ' -f1)
  I=$(stat -c %Y "$INBOX" 2>/dev/null || echo 0)
  if [ "$F" != "$F0" ]; then echo "FROZEN_CHANGED $F0 -> $F"; exit 0; fi
  if [ "$S" != "$S0" ]; then echo "FROZEN_SCHEMA_CHANGED $S0 -> $S"; exit 0; fi
  if [ "$I" != "$I0" ]; then echo "INBOX_CHANGED"; exit 0; fi
done
echo "NO_CHANGE_AFTER_9000s"; exit 3
