#!/usr/bin/env bash
set -euo pipefail
ROOT=/data3/guoshaoyang/workdir/ai4math-swarm
RUNTIME=$ROOT/runtime; LOGS=$RUNTIME/logs; STATE=$RUNTIME/state
mkdir -p "$LOGS" "$STATE" "$ROOT/comms/inbox" "$ROOT/comms/outbox" "$ROOT/artifacts"
DASH=$HOME/workdir/lean_poincare/bin/dsh_fixed.sh
[[ -x $DASH ]] || { echo "missing dsh wrapper: $DASH" >&2; exit 2; }
python3 "$ROOT/research_map/validate_map.py" > "$STATE/map_validation.txt"
echo "$(date -Is)" > "$STATE/started_at"
start() {
  local name=$1 prompt=$2
  if tmux has-session -t "$name" 2>/dev/null; then echo "already running $name"; return; fi
  tmux new-session -d -s "$name" "cd '$ROOT' && '$DASH' --profile headless '$prompt' 2>&1 | tee '$LOGS/$name.log'; echo \$? > '$STATE/$name.exit'"
  echo "$name" >> "$STATE/processes"
}
start astra-controller "You are Astra, global controller for the cosmic-censorship research swarm. Read research_map/ASTRA_HANDOFF.md, research_map/research_map.json, research_map/ARCHITECTURE.md, HANDOFF.md. Treat research_map.json as sole global state. Coordinate leads and workers via comms/inbox and comms/outbox. Assign class-bound tasks with artifacts, gates, evidence refs, falsifiers. Keep self-gravitating numerics blocked until formulation and audit gates pass. Record status, claims, artifacts, blockers, direction updates, resource requests, agent-hours, hashes, validation, ETA. Checkpoint every 15 minutes; run four hours; never promote fluent text to theorem."
start astra-lead-formulation "You are formulation group lead. Read the handoff and map. Deliver F1 WCC vacuum schema and F2 separate SCC C2/C0 schemas with exact quantifiers, topology, regularity, genericity, I+, visibility, conclusion type. Review workers, write artifacts/formulation and structured comms/outbox events, report blockers and falsifiers. Run four hours with checkpoints."
start astra-lead-literature "You are literature group lead. Read the handoff and map. Build a primary-source theorem ledger for WCC/SCC with exact scope, assumptions, citation links, unresolved items and falsifiers. Write artifacts/literature and structured comms/outbox events. Run four hours with checkpoints; reject uncertain citations."
start astra-lead-numerics "You are numerics group lead. Read the handoff and map. Prepare flat-space scalar-wave calibration, convergence tests and invariant diagnostics only. Do not launch self-gravitating production before formulation and audit gates pass. Write artifacts/numerics and structured blocker events. Run four hours with checkpoints."
start astra-lead-audit "You are audit group lead. Read the handoff and map. Red-team formulation and literature outputs; enforce class binding, citation support, hard-failure, duplication and information-gain metrics. Design four-arm matched-budget ablation. Write artifacts/audit and structured comms/outbox events. Run four hours with checkpoints."
for n in $(seq -w 1 20); do start "deepseek-flash-$n" "You are execution worker $n in the cosmic-censorship research swarm. Read the handoff and map. Work only on a class-bound task assigned by a group lead; if no assignment exists, inspect the immediate queue and propose one artifact-backed task without claiming completion. Emit status, claim, artifact, blocker or resource_request JSON in comms/outbox with node/class IDs, evidence refs and next falsifier. Use DeepSeek Flash breadth only; preserve exact scope and report failures. Run up to four hours with checkpoints."; done
echo "started $(wc -l < "$STATE/processes") sessions"
