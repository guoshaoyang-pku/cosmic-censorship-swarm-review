#!/usr/bin/env bash
# W038-F0-CONFORMANCE-01 run manifest: every command, its output file and its exit code.
# Re-running is idempotent and overwrites the outputs in this directory only.
set -u
cd "$(dirname "$0")/../../.." || exit 99   # repo root: artifacts/worker-038/f0_conformance -> repo
D=artifacts/worker-038/f0_conformance
M="$D/run_manifest.txt"
: > "$M"

run() {
  local name="$1"; shift
  echo "### CMD: $*" >> "$M"
  "$@" > "$D/$name.log" 2>&1
  local rc=$?
  echo "$name exit=$rc" >> "$M"
  return 0
}

echo "run_at=$(date -Is)" >> "$M"
echo "### PINS (sha256 at run time)" >> "$M"
sha256sum research_map/formulation_taxonomy.yaml artifacts/formulation/formulation_taxonomy.yaml \
  evaluation_rubric.yaml artifacts/formulation/FROZEN.json \
  artifacts/worker-01/validate_taxonomy.py \
  artifacts/worker-038/f0_conformance/check_f0_independent.py >> "$M"

run 10_checker_selftest python3 artifacts/worker-01/validate_taxonomy.py --self-test
run 20_checker_main python3 artifacts/worker-01/validate_taxonomy.py --json "$D/worker01_validation.json"
run 30_independent python3 artifacts/worker-038/f0_conformance/check_f0_independent.py --root . --json-out "$D/independent_checks.json"

echo "### PINS_AFTER" >> "$M"
sha256sum research_map/formulation_taxonomy.yaml artifacts/formulation/formulation_taxonomy.yaml \
  evaluation_rubric.yaml artifacts/formulation/FROZEN.json \
  artifacts/worker-01/validate_taxonomy.py \
  artifacts/worker-038/f0_conformance/check_f0_independent.py >> "$M"
echo DONE >> "$M"
