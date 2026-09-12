#!/usr/bin/env bash
set -u
ROOT=/data3/guoshaoyang/workdir/ai4math-swarm
BASE=$ROOT/runtime; INST=$BASE/instances; STATE=$BASE/state
mkdir -p "$INST" "$STATE"
CIRCUIT="$STATE/quota_circuit_until"
launch(){
  role=$1; slot=$2; prompt=$3; key="$role-$slot"
  tmux has-session -t "$key" 2>/dev/null && return 0
  stamp=$(date +%Y%m%dT%H%M%S); id="$key-$stamp-$$"; d="$INST/$id"; mkdir -p "$d"
  printf '%s\n' "$prompt" > "$d/prompt.txt"
  printf '{"id":"%s","role":"%s","slot":"%s","started_at":"%s"}\n' "$id" "$role" "$slot" "$(date -Is)" > "$d/meta.json"
  tmux new-session -d -s "$key" "echo start id=$id ts=$(date -Is) >> '$d/trajectory.log'; '$HOME/workdir/lean_poincare/bin/dsh_fixed.sh' --profile headless '$prompt' > '$d/stdout.log' 2> '$d/stderr.log'; rc=\$?; echo \$rc > '$d/exit_code'; echo exit id=$id rc=\$rc ts=\$(date -Is) >> '$d/trajectory.log'"
  echo "$(date -Is) launch $key $id" >> "$STATE/supervisor.log"
}
quota_seen(){ find "$INST" -type f -name stderr.log -mmin -2 -print0 2>/dev/null | xargs -0 grep -lq "QUOTA: Insufficient Balance" 2>/dev/null; }
set_circuit(){ until=$(( $(date +%s) + 900 )); echo "$until" > "$CIRCUIT"; echo "$(date -Is) quota_circuit_open=900 until=$until" >> "$STATE/supervisor.log"; }
controller='You are Astra controller. Read ASTRA_HANDOFF.md and research_map.json. Consume comms and artifacts, maintain DAG and gates, issue bounded assignments, record hashes and validation. Keep numerics gated. One independent lifecycle then exit.'
lead='You are a group lead. Read handoff/map and comms. Review artifacts, consume queue, emit structured events and checkpoints, report blockers. One independent lifecycle then exit.'
worker='You are a bounded execution worker. Read handoff/map and comms. Take one class-bound task, emit valid JSON with IDs evidence hash falsifier, checkpoint, then exit.'
while :; do
  now=$(date +%s); until=0; [ -f "$CIRCUIT" ] && until=$(cat "$CIRCUIT" 2>/dev/null || echo 0)
  if [ "$until" -gt "$now" ] 2>/dev/null; then sleep 60; continue; fi
  if [ -f "$CIRCUIT" ]; then
    rm -f "$CIRCUIT"; launch controller 01 "$controller probe=quota"; sleep 35
    if quota_seen; then set_circuit; tmux kill-session -t controller-01 2>/dev/null || true; continue; fi
  fi
  launch controller 01 "$controller"
  for g in formulation literature numerics audit; do launch lead-$g 01 "$lead group=$g"; done
  for n in $(seq -w 1 100); do launch worker "$n" "$worker worker=$n"; done
  echo "$(date -Is) sessions=$(tmux ls 2>/dev/null | egrep "^(controller-|lead-|worker-)" | wc -l) leads=$(tmux ls 2>/dev/null | grep -c "^lead-") workers=$(tmux ls 2>/dev/null | grep -c "^worker-") artifacts=$(find "$ROOT/artifacts" -type f 2>/dev/null | wc -l)" >> "$STATE/counts.tsv"
  sleep 20; quota_seen && set_circuit
done
