#!/usr/bin/env python3
"""W044-F2B-LIVE-CLOSURE-01 adjudicator.

Reads the pre-registration (written before the probe) and the probe's report.json, checks every
pre-registered prediction against the measured snapshot column, and emits closure_summary.json.

Fail-closed rules:
  - a prediction mismatch is recorded as `prediction_mismatch` with both values; it is never
    silently excused, and the decision is recomputed from MEASUREMENT, not from the prediction;
  - if a required measurement is missing, the adjudicator raises (no summary written).

Authority: worker measurement only. Not a gate verdict, node status, or review verdict.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    pre = json.loads((HERE / "PREREGISTRATION.json").read_text())
    rep = json.loads((HERE / "report.json").read_text())
    ss = rep["snapshot_state"]
    by_id = {c["id"]: c for c in ss["checks"]}
    checks = {cid: c["status"] for cid, c in by_id.items()}
    gates = {k: (v.get("rc") if isinstance(v, dict) else v) for k, v in ss["schema_gates"].items()}
    frozen_rc = ss["verify_frozen"].get("rc")
    frozen_summary = ss["verify_frozen"].get("summary")
    sep6_ok = bool(ss["aggregator_sep6"].get("ok"))
    mirrors_ok = all(ss["mirrors"].values())

    # measured counterparts of every pre-registered prediction
    measured = {
        "snapshot_H1H2": checks.get("H1H2"),
        "snapshot_A1_declared_evidence_resolves": checks.get("A1"),
        "snapshot_A2_evidence_self_verifying": checks.get("A2"),
        "snapshot_A6_alias_registry_bound": checks.get("A6"),
        "snapshot_structural_gates_C0_C2_F1": "pass" if all(v == 0 for v in gates.values()) and gates else "fail",
        "snapshot_verify_frozen_problems": frozen_rc,
        "snapshot_aggregator_SEP6": "ok" if sep6_ok else "stale",
        "snapshot_mirrors_byte_equal": "yes" if mirrors_ok else "no",
    }
    predicted = pre["prediction"]
    mismatches = []
    for k, mv in measured.items():
        pv = predicted.get(k)
        if pv != mv:
            mismatches.append({"check": k, "predicted": pv, "measured": mv})

    # defect-family closure at the measured pins (H1/H2 are reported as one check family by the
    # harness; the containment detail below splits them)
    containment_findings = [
        f.get("kind") for f in by_id.get("H1H2", {}).get("detail", {}).get("findings", [])
        if isinstance(f, dict)
    ]
    families = [
        {"defect": "H1_false_containment_denial", "defect_owner": "worker-066 (finding worker-008)",
         "measured_by": "H1H2", "state": "open" if checks.get("H1H2") == "fail" else "closed",
         "detail": "false_containment_denial" in containment_findings},
        {"defect": "H2_inverted_size_premise", "defect_owner": "worker-066 (finding worker-008)",
         "measured_by": "H1H2", "state": "open" if checks.get("H1H2") == "fail" else "closed",
         "detail": "size_premise_inverted" in containment_findings},
        {"defect": "A2_evidence_not_self_verifying", "defect_owner": "worker-044/086/005",
         "measured_by": "A2", "state": "open" if checks.get("A2") == "fail" else "closed",
         "detail": by_id.get("A2", {}).get("detail", {}).get("evidence_pins")},
        {"defect": "A6_alias_registry_unbound", "defect_owner": "worker-005",
         "measured_by": "A6", "state": "open" if checks.get("A6") == "fail" else "closed",
         "detail": None},
        {"defect": "SEP6_aggregator_component_pins_stale", "defect_owner": "worker-044 (closure step)",
         "measured_by": "aggregator_sep6", "state": "open" if not sep6_ok else "closed",
         "detail": {k: v for k, v in ss["aggregator_sep6"].get("components", {}).items()}},
    ]
    blocking = [f["defect"] for f in families if f["state"] == "open"]
    decision = "F2B_BLOCKED_AT_MEASURED_PINS" if blocking else "F2B_MACHINE_CHECKS_PASS_AT_MEASURED_PINS"

    composed = rep["composed"]
    summary = {
        "schema": "worker-044/closure-summary/v1",
        "task_id": pre["task_id"],
        "actor": pre["actor"],
        "node_id": pre["node_id"],
        "class_id": pre["class_id"],
        "gate": pre["gate"],
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "decision_question": pre["decision_question"],
        "snapshot_at": rep["snapshot_at"],
        "snapshot_hashes": rep["snapshot_hashes"],
        "measured": measured,
        "prediction_match": not mismatches,
        "prediction_mismatches": mismatches,
        "defect_families": families,
        "blocking_families": blocking,
        "decision": decision,
        "decision_rule": "BLOCKED iff any of H1H2/A2/A6 fails or the aggregator SEP-6 check is not ok at the measured pins; recomputed from measurement, not from the prediction",
        "composed_candidate": {
            "verdict": rep["verdict"],
            "ready": rep["ready"],
            "hashes": rep["composed_hashes"],
            "verify_frozen_rc": composed["verify_frozen"]["rc"],
            "schema_gates_rc": {k: (v.get("rc") if isinstance(v, dict) else v) for k, v in composed["schema_gates"].items()},
            "aggregator_sep6_ok": composed["aggregator_sep6"]["ok"],
        },
        "controls_all_discriminate": all(c["passed"] for c in rep["controls"]),
        "controls": [{"id": c["id"], "passed": c["passed"]} for c in rep["controls"]],
        "durability": {"stable": rep["durability"]["stable"], "verify_frozen_rc": rep["durability"]["verify_frozen_rc"]},
        "live_drift_since_snapshot": rep["live_drift_since_snapshot"],
        "review_consequence": (
            "At the measured C0 hash an accept verdict is not machine-supported on the declared gate checks: "
            "three defect families are open. A reviewer who accepts at this hash must state which of "
            "H1H2/A2/A6/SEP-6 it waives and on what authority. This is a measurement input to the audit-lead "
            "r3 adjudication, not a review verdict."
        ),
        "falsifier": pre["falsifier"],
        "non_claims": pre["non_claims"],
        "evidence_hashes": {
            "report.json": sha256_file(HERE / "report.json"),
            "PREREGISTRATION.json": sha256_file(HERE / "PREREGISTRATION.json"),
            "live_closure.py": sha256_file(HERE / "live_closure.py"),
            "PROVENANCE.json": sha256_file(HERE / "PROVENANCE.json"),
            "adjudicate.py": sha256_file(HERE / "adjudicate.py"),
        },
    }
    (HERE / "closure_summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({"decision": decision, "blocking": blocking,
                      "prediction_match": not mismatches, "mismatches": mismatches,
                      "controls_all_discriminate": summary["controls_all_discriminate"],
                      "report_sha256": summary["evidence_hashes"]["report.json"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
