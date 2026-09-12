#!/usr/bin/env bash
ROOT=/data3/guoshaoyang/workdir/ai4math-swarm
D="$1"
cd "$ROOT" || exit 99
run() {
  local name="$1"; shift
  echo "### CMD: $*" >> "$D/exit_codes.txt"
  "$@" > "$D/$name.log" 2>&1
  echo "$name exit=$?" >> "$D/exit_codes.txt"
}
: > "$D/exit_codes.txt"
run 01_flat_wave_selftest python3 numerics/tests/flat_wave.py --selftest
run 02_flat_wave_all python3 numerics/tests/flat_wave.py --all --json-out "$D/02_flat_wave_all.json"
run 03_flat_wave_lockguard python3 numerics/tests/flat_wave.py --lock-guard
run 04_replication_selftest python3 numerics/tests/flat_wave_replication.py --selftest
run 05_replication_all python3 numerics/tests/flat_wave_replication.py --all --json-out "$D/05_replication_all.json"
run 06_replication_harness python3 numerics/tests/flat_wave_replication.py --harness
run 07_lead_calibration_selftest python3 numerics/tests/lead_calibration.py --selftest
run 08_lead_calibration_all python3 numerics/tests/lead_calibration.py --all --json-out "$D/08_lead_calibration_all.json"
run 09_selfgravity_lock_guard python3 numerics/tests/selfgravity_lock_guard.py
run 10_gates_check python3 -m numerics.gates --check --pretty
run 11_validate_map python3 research_map/validate_map.py
sha256sum numerics/tests/flat_wave.py numerics/tests/flat_wave_replication.py numerics/tests/lead_calibration.py numerics/tests/selfgravity_lock_guard.py numerics/gates.py numerics/CONVERGENCE_PROTOCOL.md > "$D/sha256_artifacts.txt" 2>&1
echo DONE >> "$D/exit_codes.txt"
