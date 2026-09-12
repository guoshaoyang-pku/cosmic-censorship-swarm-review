#!/usr/bin/env bash
set -u
ROOT=/data3/guoshaoyang/workdir/ai4math-swarm
DASH=$HOME/workdir/lean_poincare/bin/dsh_fixed.sh
LOGS=$ROOT/runtime/logs; STATE=$ROOT/runtime/state
mkdir -p "$LOGS" "$STATE"
run_loop(){
  local name="$1"; shift; local prompt="$*"
  tmux has-session -t "$name" 2>/dev/null && return
  tmux new-session -d -s "$name" "while :; do date -Is >> '$LOGS/$name.lifecycle'; '$DASH' --profile headless '$prompt' >> '$LOGS/$name.log' 2>&1; rc=$?; echo "$(date -Is) iteration_exit=$rc" >> '$LOGS/$name.lifecycle'; sleep 2; done"
  echo "$(date -Is) started $name" >> "$STATE/supervisor.log"
}
controller='You are Astra, persistent global controller for cosmic-censorship. Read research_map/ASTRA_HANDOFF.md, research_map/research_map.json, research_map/ARCHITECTURE.md, HANDOFF.md. Consume comms and artifacts, maintain DAG/gates, assign class-bound bounded tasks, record hashes/validation/ETA. Keep numerics gated until formulation and audit pass. Each iteration: inspect new events, adjudicate, issue assignments, checkpoint, then finish the iteration. Never promote prose to theorem.'
form='You are persistent formulation lead. Read handoff/map and consume comms. Each iteration review current worker artifacts, advance F1 WCC and separate F2 C2/C0 schemas, enforce quantifiers/class binding, emit events/checkpoint, then finish.'
lit='You are persistent literature lead. Read handoff/map and consume comms. Each iteration verify primary-source theorem scope/citations, update ledger, emit artifacts/events/checkpoint, report blockers, then finish.'
num='You are persistent numerics lead. Read handoff/map and consume comms. Each iteration prepare or verify flat-space scalar-wave calibration and convergence diagnostics; keep self-gravitating work gated; emit artifacts/events/checkpoint, then finish.'
audit='You are persistent audit lead. Read handoff/map and consume comms. Each iteration red-team claims/artifacts, enforce hard-failure/class/citation/duplication gates, update ablation design, emit review/events/checkpoint, then finish.'
worker='You are a bounded execution worker in cosmic-censorship. Read handoff/map and consume comms. Each iteration take one available class-bound task; if none, inspect immediate queue and propose one artifact-backed task. Emit valid JSON event with IDs, evidence/hash and next falsifier; checkpoint; finish iteration. Never claim theorem from prose.'
run_loop astra-controller "$controller"; run_loop astra-lead-formulation "$form"; run_loop astra-lead-literature "$lit"; run_loop astra-lead-numerics "$num"; run_loop astra-lead-audit "$audit"
for n in $(seq -w 1 20); do run_loop "deepseek-flash-$n" "$worker worker=$n"; done
while :; do
 sleep 20
 sessions=$(tmux ls 2>/dev/null | awk -F: '/^(astra-controller|astra-lead-|deepseek-flash-)/{n++} END{print n+0}')
 leads=$(tmux ls 2>/dev/null | awk -F: '/^astra-lead-/{n++} END{print n+0}')
 workers=$(tmux ls 2>/dev/null | awk -F: '/^deepseek-flash-/{n++} END{print n+0}')
 artifacts=$(find "$ROOT/artifacts" -type f 2>/dev/null | wc -l)
 printf '%s sessions=%s leads=%s workers=%s artifacts=%s\n' "$(date -Is)" "$sessions" "$leads" "$workers" "$artifacts" >> "$STATE/supervisor.log"
 run_loop astra-controller "$controller"; run_loop astra-lead-formulation "$form"; run_loop astra-lead-literature "$lit"; run_loop astra-lead-numerics "$num"; run_loop astra-lead-audit "$audit"
 for n in $(seq -w 1 20); do run_loop "deepseek-flash-$n" "$worker worker=$n"; done
done
