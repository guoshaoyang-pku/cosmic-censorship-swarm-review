#!/usr/bin/env bash
set -u
ROOT=/data3/guoshaoyang/workdir/ai4math-swarm
DASH=$HOME/workdir/lean_poincare/bin/dsh_fixed.sh
RUNTIME=$ROOT/runtime; LOGS=$RUNTIME/logs; STATE=$RUNTIME/state
mkdir -p "$LOGS" "$STATE"
start() {
  local name="$1"; shift; local prompt="$*"
  tmux has-session -t "$name" 2>/dev/null && return 0
  rm -f "$STATE/$name.exit"
  tmux new-session -d -s "$name" "cd '$ROOT' && '$DASH' --profile headless '$prompt' 2>&1 | tee -a '$LOGS/$name.log'; rc=\$?; echo \$rc > '$STATE/$name.exit'; echo "$(date -Is) $name exit=\$rc" >> '$STATE/supervisor.log'"
  echo "$(date -Is) started $name" >> "$STATE/supervisor.log"
}
controller='You are Astra, persistent global controller for the cosmic-censorship research swarm. Read ASTRA_HANDOFF.md, research_map.json, ARCHITECTURE.md, HANDOFF.md. Consume comms, maintain DAG and gates, assign class-bound tasks with artifacts and falsifiers, record hashes and validation. Keep numerics gated until formulation and audit pass. Checkpoint every 15 minutes; never promote prose to theorem.'
form='You are persistent formulation lead. Read handoff and map, consume comms, review artifacts, maintain F1 WCC and separate F2 C2/C0 schemas, enforce exact quantifiers and class binding, emit structured events and checkpoints. Continue until controller ends run.'
lit='You are persistent literature lead. Read handoff and map, consume comms, verify primary-source theorem scope and citations, maintain ledger, emit artifacts/events/checkpoints, report blockers precisely.'
num='You are persistent numerics lead. Read handoff and map, consume comms, prepare auditable flat-space scalar-wave calibration and convergence tests, keep self-gravitating production blocked until formulation and audit pass, emit artifacts/events/checkpoints.'
audit='You are persistent audit lead. Read handoff and map, consume comms, red-team claims and artifacts, enforce hard-failure/class-binding/citation/duplication gates, maintain matched-budget ablation design, emit reviews/events/checkpoints.'
worker='You are persistent breadth worker in the cosmic-censorship research swarm. Read handoff and map, consume assignments in comms, work only on a class-bound task, emit valid JSON events with IDs, evidence, hashes and falsifiers, never claim theorem completion from prose. Complete bounded tasks with checkpoints and exit cleanly for recycling.'
start astra-controller "$controller"
start astra-lead-formulation "$form"; start astra-lead-literature "$lit"; start astra-lead-numerics "$num"; start astra-lead-audit "$audit"
for n in $(seq -w 1 20); do start "deepseek-flash-$n" "$worker $n"; done
while :; do
  sleep 30
  start astra-controller "$controller"
  start astra-lead-formulation "$form"; start astra-lead-literature "$lit"; start astra-lead-numerics "$num"; start astra-lead-audit "$audit"
  for n in $(seq -w 1 20); do start "deepseek-flash-$n" "$worker $n"; done
  sessions=$(tmux ls 2>/dev/null | awk -F: '/^(astra-controller|astra-lead-|deepseek-flash-)/{n++} END{print n+0}')
  leads=$(tmux ls 2>/dev/null | awk -F: '/^astra-lead-/{n++} END{print n+0}')
  workers=$(tmux ls 2>/dev/null | awk -F: '/^deepseek-flash-/{n++} END{print n+0}')
  artifacts=$(find "$ROOT/artifacts" -type f 2>/dev/null | wc -l)
  printf '%s sessions=%s leads=%s workers=%s artifacts=%s\n' "$(date -Is)" "$sessions" "$leads" "$workers" "$artifacts" >> "$STATE/supervisor.log"
done
