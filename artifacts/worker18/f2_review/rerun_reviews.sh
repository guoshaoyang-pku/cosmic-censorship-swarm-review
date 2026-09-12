#!/usr/bin/env bash
# Re-run the worker-18 F2 review evidence pipeline against whatever is on disk now.
# Use after a freeze or any schema revision. It refreshes machine evidence and prints the new
# pins; the narrative review files (reviews/F2a-review-18.json, F2b-review-18.json) still need
# their line references checked by hand if line numbers moved.
#
# Usage: bash artifacts/worker18/f2_review/rerun_reviews.sh
set -u
cd "$(dirname "$0")/../../.." || exit 2
echo "== pins at $(date '+%F %T %z') =="
sha256sum schemas/af_scc_c2_vacuum.yaml schemas/af_scc_c0_vacuum.yaml schemas/af_scc_regularities.yaml

echo "== probe self-test =="
python3 artifacts/worker18/f2_review/f2_class_probe.py --selftest >/dev/null && echo "selftest OK" || echo "selftest FAILED"

echo "== cross-class probe on current revisions =="
python3 artifacts/worker18/f2_review/f2_class_probe.py \
  --c2 schemas/af_scc_c2_vacuum.yaml \
  --c0 schemas/af_scc_c0_vacuum.yaml \
  --report artifacts/worker18/f2_review/probe_report.json || true

echo "== canonical binding gates =="
python3 artifacts/formulation/tools/check_class_schema.py schemas/af_scc_c2_vacuum.yaml \
  > artifacts/worker18/f2_review/f2a_binding_gate.txt 2>&1 || true
python3 artifacts/formulation/tools/check_class_schema.py schemas/af_scc_c0_vacuum.yaml \
  > artifacts/worker18/f2_review/f2b_binding_gate.txt 2>&1 || true
cat artifacts/worker18/f2_review/f2a_binding_gate.txt
cat artifacts/worker18/f2_review/f2b_binding_gate.txt

echo "== sibling lints (evidence only) =="
python3 artifacts/worker-06/check_class_binding.py schemas/af_scc_c0_vacuum.yaml --check-filename \
  --json artifacts/worker18/f2_review/w06_c0_gate_report.json >/dev/null 2>&1 || true
python3 artifacts/worker-05/check_f2_integration.py --report \
  --out artifacts/worker18/f2_review/worker05_integration_report.json 2>&1 | tail -6 || true

echo "== aggregator pin check =="
python3 artifacts/worker18/f2_review/check_aggregator_pins.py || true

echo "== review pin status (exit 1 = a review is stale and must be re-issued) =="
python3 artifacts/worker18/f2_review/verify_reviews_current.py \
  --json artifacts/worker18/f2_review/review_pin_status.json || true
echo "== done =="
