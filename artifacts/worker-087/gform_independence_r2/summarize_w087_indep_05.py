#!/usr/bin/env python3
"""W087-GFORM-INDEP-05: derive the per-class adjudication summary from the frozen
instrument report and the snapshot manifest.

Deterministic: reads only snapshot_run3/report.json and snapshot/MANIFEST.json, writes
summary.json next to them. No live-tree input is read, so the summary inherits the
snapshot's byte-fixed corpus.

Usage: python3 summarize_w087_indep_05.py --dir <r2-dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
CLASSES = {
    "F1": "AF-WCC-VAC-GEN",
    "F2a": "AF-SCC-C2-VAC-GEN",
    "F2b": "AF-SCC-C0-VAC-GEN",
}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    a = ap.parse_args()
    d = Path(a.dir).resolve()
    rep = json.loads((d / "snapshot_run3" / "report.json").read_text())
    man = json.loads((d / "snapshot" / "MANIFEST.json").read_text())
    run_digests = []
    for i in (1, 2, 3):
        r = json.loads((d / f"snapshot_run{i}" / "report.json").read_text())
        run_digests.append(r["verdict_digest_sha256"])
    digests_equal = len(set(run_digests)) == 1

    per_class = {}
    for node, cid in CLASSES.items():
        c = rep["coverage_at_measured_pins"][node]
        per_class[node] = {
            "node_id": node,
            "class_id": cid,
            "path": c["path"],
            "sha256": c["sha256"],
            "effective_independent_full_schema_accept_clusters": c["effective_accept_clusters"],
            "criterion_two_independent_accepts": c["criterion_two_independent_accepts"],
            "full_schema_accept_reviewers": c["full_schema_accept_reviewers"],
            "advisory_accept_reviewers": c.get("advisory_accept_reviewers", []),
            "distinct_reviewers_bound": c["distinct_reviewers_bound"],
            "cluster_members": [
                {"cluster_id": cl["cluster_id"], "reviewers": cl["reviewers"], "event_ids": cl["event_ids"]}
                for cl in c["accept_clusters"]
            ],
        }
    gap = [n for n, v in per_class.items() if not v["criterion_two_independent_accepts"]]
    summary = {
        "task_id": "W087-GFORM-INDEP-05",
        "actor": "worker-087",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "artifact_type": "coverage_measurement",
        "gate": "G-FORM",
        "node_ids": ["F1", "F2a", "F2b"],
        "class_ids": list(CLASSES.values()),
        "question": ("At the post-repair canonical bytes (schemas rev13, FROZEN rev29), which of "
                     "F1/F2a/F2b meet the G-FORM criterion 'two independent full-schema accepts', "
                     "after reviewer-identity, verdict-text and evidence-channel dedup?"),
        "measurement_basis": {
            "snapshot_started_at": man["snapshot_started_at"],
            "snapshot_finished_at": man["snapshot_finished_at"],
            "snapshot_manifest_digest_sha256": man["manifest_digest_sha256"],
            "snapshot_files": man["n_files"],
            "snapshot_pins_match_live_at_snapshot_close": man["all_snapshot_pins_match_live"],
            "corpus_records_loaded": rep["corpus"]["records_loaded"],
            "review_docs_indexed": rep["corpus"]["review_docs_indexed"],
            "instrument": "audit_gform_independence.py",
            "instrument_sha256": sha256_file(d / "audit_gform_independence.py"),
            "report_sha256": sha256_file(d / "snapshot_run3" / "report.json"),
            "verdict_digest_sha256": rep["verdict_digest_sha256"],
            "runs_on_snapshot": 3,
            "three_run_digests": run_digests,
            "three_run_digests_equal": digests_equal,
        },
        "pins": {
            "F1": rep["pins_measured_at_start"]["F1"],
            "F2a": rep["pins_measured_at_start"]["F2a"],
            "F2b": rep["pins_measured_at_start"]["F2b"],
            "FROZEN": rep["frozen_manifest_measured_at_start"],
            "FROZEN_revision": rep["freeze_state"]["manifest"]["declared_revision"],
            "taxonomy_consistency_evidence": rep["freeze_state"]["evidence_artifact"]["measured_sha256"],
        },
        "freeze_state": {
            "state": rep["freeze_state"]["state"],
            "freeze_intact": rep["freeze_state"]["freeze_intact"],
            "mirrors_aligned": rep["freeze_state"]["mirrors_aligned"],
            "internal_consistency": rep["freeze_state"]["internal_consistency"],
            "evidence_pins_refreshed": rep["freeze_state"]["evidence_pins_refreshed"],
            "owner_announcements_present": rep["freeze_state"]["owner_announcements_present"],
            "repin_complete": rep["freeze_state"]["repin_complete"],
        },
        "per_class": per_class,
        "gate_level_criterion_met": len(gap) == 0,
        "remaining_gap_classes": gap,
        "remaining_gap": {
            "node_id": "F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "path": "schemas/af_scc_c0_vacuum.yaml",
            "sha256": per_class["F2b"]["sha256"],
            "current_effective_accept_clusters": per_class["F2b"]["effective_independent_full_schema_accept_clusters"],
            "needed": ("one more full-schema accept bound to the primary hash of "
                       "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe from a reviewer other than "
                       "worker-061 whose findings text and evidence channels form an independent "
                       "cluster under the declared clustering rule"),
        },
        "held_out_not_counted": {
            "reason": ("the F2b gap is not filled by rev-28-bound verdicts or by reviews of a sandbox "
                       "copy/derived document; those are void or advisory"),
            "historical_rev28_f2b_accepts": rep["coverage_at_rev28_pins"]["F2b"]["full_schema_accept_reviewers"],
            "historical_rev28_f1_accepts": rep["coverage_at_rev28_pins"]["F1"]["full_schema_accept_reviewers"],
            "historical_rev28_f2a_accepts": rep["coverage_at_rev28_pins"]["F2a"]["full_schema_accept_reviewers"],
        },
        "controls": {
            "ok": rep["controls_ok"],
            "passed": sum(1 for c in rep["controls"].values() if c) if isinstance(rep["controls"], dict) else None,
            "total": len(rep["controls"]) if isinstance(rep["controls"], dict) else None,
        },
        "falsifiers": [
            ("F2b gap falsified by a new full-schema accept bound to "
             "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe from a reviewer other than worker-061 in a "
             "separate independence cluster (no shared findings text or evidence channel)."),
            ("The whole measurement is void if any of the three snapshot pins no longer matches the "
             "live canonical bytes, or if FROZEN.json is not revision 29 / sha 815e08079aef, or if an "
             "owner artifact event announcing a measured canonical hash is absent from the accepted stream."),
            ("Criterion-met findings for F1/F2a are falsified if two counted clusters are shown to share "
             "an instrument, review document or verdict text, or if a hash-bound verdict excluded by the "
             "harvest is shown to name the schema directly at the reported revision."),
            ("Reproducibility falsifier: re-run audit_gform_independence.py against "
             "snapshot/ and compare verdict_digest_sha256; a different digest falsifies the summary."),
        ],
        "authority": ("Worker evidence only. Cannot set node status=done, validation_status=passed or any "
                      "gate verdict; issues no review verdict on the schemas themselves. Read-only against "
                      "every canonical input."),
    }
    (d / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    print(json.dumps({
        "summary": str(d / "summary.json"),
        "gate_level_criterion_met": summary["gate_level_criterion_met"],
        "remaining_gap_classes": gap,
        "clusters": {k: v["effective_independent_full_schema_accept_clusters"] for k, v in per_class.items()},
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
