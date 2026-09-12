#!/usr/bin/env bash
# W038-F0-CONFORMANCE-02 rev28 recheck: same three tools as run.sh, but outputs are
# written under *_rev28 names so the rev4/rev5 evidence cited by earlier events is
# never overwritten (evidence is path#sha256; overwriting would strand those refs).
set -u
cd "$(dirname "$0")/../../.." || exit 99   # repo root
D=artifacts/worker-038/f0_conformance
M="$D/run_manifest_rev28.txt"
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
echo "### PINS_BEFORE" >> "$M"
sha256sum research_map/formulation_taxonomy.yaml artifacts/formulation/formulation_taxonomy.yaml \
  evaluation_rubric.yaml artifacts/formulation/FROZEN.json \
  artifacts/worker-01/validate_taxonomy.py \
  artifacts/worker-038/f0_conformance/check_f0_independent.py \
  artifacts/worker-038/f0_conformance/freeze_integrity_check.py >> "$M"

run 10_checker_selftest_rev28 python3 artifacts/worker-01/validate_taxonomy.py --self-test
run 20_checker_main_rev28 python3 artifacts/worker-01/validate_taxonomy.py --json "$D/worker01_validation_rev28.json"
run 30_independent_rev28 python3 artifacts/worker-038/f0_conformance/check_f0_independent.py --root . --json-out "$D/independent_checks_rev28.json"
run 40_freeze_integrity_rev28 python3 artifacts/worker-038/f0_conformance/freeze_integrity_check.py --root . --json-out "$D/freeze_integrity_rev28.json" --snapshot-dir "$D/snapshots/rev28"

echo "### PINS_AFTER" >> "$M"
sha256sum research_map/formulation_taxonomy.yaml artifacts/formulation/formulation_taxonomy.yaml \
  evaluation_rubric.yaml artifacts/formulation/FROZEN.json \
  artifacts/worker-01/validate_taxonomy.py \
  artifacts/worker-038/f0_conformance/check_f0_independent.py \
  artifacts/worker-038/f0_conformance/freeze_integrity_check.py >> "$M"
echo DONE >> "$M"
