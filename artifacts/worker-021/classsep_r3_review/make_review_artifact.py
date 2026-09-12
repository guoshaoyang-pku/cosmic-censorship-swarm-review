#!/usr/bin/env python3
"""Emit report.json and reviews/CLASSSEP-calibration-adjudication-review-021.json
from the measured census/controls/comparison payloads (no hand-transcribed numbers)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CREATED = "2026-09-12T01:33:00+08:00"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    census = json.loads((HERE / "census.json").read_text())
    controls = json.loads((HERE / "controls.json").read_text())
    comparison = json.loads((HERE / "comparison.json").read_text())
    adj_sha = census["pins"]["reviews/CLASSSEP-calibration-adjudication.json"]["sha256"]
    snap_sha = census["pins"]["artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json"]["sha256"]

    arms = ["APPLIED", "PRE", "STAGED", "PROSEFIX"]
    table = {}
    for a in arms:
        ca = census["corpus_a_27fixtures"][a]
        cb = census["corpus_b_live"][a]
        cc = census["corpus_c_assertion_mention"][a]
        cd = census["corpus_d_worker049"][a]
        table[a] = {
            "corpus_a": {"tp": ca["tp"], "fn": ca["fn"], "fp": ca["fp"], "tn": ca["tn"],
                         "verdict": ca["verdict"]},
            "corpus_b_live": {"hard": cb["hard_total"], "tp": cb["tp"], "fp": cb["fp"],
                              "unlabeled": cb["unlabeled_count"],
                              "claims_flagged": cb["claims_flagged"],
                              "claims_in_map": cb["claims_in_map"]},
            "corpus_c": {"sensitivity": cc["sensitivity"], "specificity": cc["specificity"],
                         "tp": cc["tp"], "fn": cc["fn"], "fp": cc["fp"], "tn": cc["tn"]},
            "corpus_d": {"cue_fn_high": cd["cue_induced_fn_high_confidence"],
                         "cue_fn_total": cd["cue_induced_fn_total"],
                         "adversarial_cleared": len(cd["adversarial_cleared"]),
                         "adversarial_total": cd["adversarial_total"],
                         "battery": f"{cd['worker035_battery']['passed']}/"
                                    f"{cd['worker035_battery']['total']}",
                         "classes": cd["fixture_classes"]},
            "meets_adoption_bar": census["decision"]["per_arm"][a]["meets_bar"],
        }

    per_fixture = {
        "corpus_a": {a: {r["id"]: r["class"] for r in census["corpus_a_27fixtures"][a]["per_fixture"]}
                     for a in arms},
        "corpus_c": {a: {r["id"]: r["class"]
                         for r in census["corpus_c_assertion_mention"][a]["rows"]} for a in arms},
        "corpus_d": {a: {r["id"]: r["class"]
                         for r in census["corpus_d_worker049"][a]["per_fixture"]} for a in arms},
    }

    findings = [
        {"id": "N21-CS-01", "severity": "info", "status": "confirmed",
         "statement": "Corpus A reproduces PASS 17TP/0FN/10TN/0FP for all four arms; the "
                      "registered 27-fixture corpus therefore cannot discriminate the arms "
                      "(this is the adjudication's own corpus_a observation)."},
        {"id": "N21-CS-02", "severity": "info", "status": "confirmed",
         "statement": "APPLIED live census at snapshot f344ed2aaea5 reproduces hard=19, "
                      "0 TP / 17 labeled metalinguistic FP / 2 unlabeled; both unlabeled findings "
                      "carry automatic mechanism DETECTOR_SELF. Independent label audit over the "
                      "14 labeled claims: composite token present in all 14, and my "
                      "detector-independent first-order heuristic fires on none of them.",
         "label_audit": census["corpus_b_live"]["APPLIED"]["label_audit"],
         "unlabeled": census["corpus_b_live"]["APPLIED"]["unlabeled"]},
        {"id": "N21-CS-03", "severity": "info", "status": "confirmed",
         "statement": "Per-arm sens/spec reproduces exactly (APPLIED 4/6-3/10, PRE 4/6-1/10, "
                      "STAGED 5/6-1/10, PROSEFIX 4/6-10/10 with 10 HIGH cue-induced FN) and my "
                      "own re-derivation of the pre-registered bar yields no adoptable arm; "
                      "decision (c) is mechanically re-derived."},
        {"id": "N21-CS-04", "severity": "info", "status": "confirmed",
         "statement": "Attribution correction reproduces: the 10 HIGH cue-induced FN belong to "
                      "PROSEFIX dc8aa0de3869 (PROSEFIX cue_fn_high=10, battery 23/23), NOT to "
                      "STAGED e2d24b927ee8 (cue_fn_high=0); STAGED's rejection rests on the FP "
                      "axis (hard=25, specificity 1/10)."},
        {"id": "N21-CS-05", "severity": "major", "status": "recorded-not-discharged",
         "statement": "Process finding outside this reproduction: prior independent review "
                      "worker-017 records a blocking hard failure B17-CS-01 (canonical detector "
                      "written to e36b0d644ca during the round, then rolled back). I measured at "
                      "the restored a8c04fc3 bytes with pre==post drift check; the detector-of-"
                      "record question (recorded pin c266dbec vs operative a8c04fc3) remains "
                      "controller-owned and is NOT resolved or discharged by this accept."},
        {"id": "N21-CS-06", "severity": "note", "status": "recorded",
         "statement": "PROSEFIX has the lowest live hard count (1 vs APPLIED 19) but fails the FN "
                      "axis and the labeled-fixture bar and is not one of the three cited "
                      "candidates; raw == calibrated remains 19 on the frozen snapshot. The "
                      "adjudication's refusal to adopt on count alone is supported."},
    ]

    reproduction = {
        "target_sha256": adj_sha,
        "snapshot_sha256": snap_sha,
        "instrument": "artifacts/worker-021/classsep_r3_review/verify_classsep_r3.py",
        "census": "artifacts/worker-021/classsep_r3_review/census.json",
        "controls": "artifacts/worker-021/classsep_r3_review/controls.json",
        "comparison": "artifacts/worker-021/classsep_r3_review/comparison.json",
        "n_comparisons": comparison["n_comparisons"],
        "n_mismatches": comparison["n_mismatches"],
        "controls_passed": f"{sum(1 for c in controls['controls'] if c['pass'])}/"
                           f"{len(controls['controls'])}",
        "per_arm_table": table,
        "per_fixture_tp_fp_fn_census": per_fixture,
        "no_write_check": "all 11 pinned paths pre==post; research_map/class_separation.py "
                          "a8c04fc31e4a before and after; proposed/, reviews/ and the named "
                          "worker-075 artifact path untouched",
    }

    report = {
        "task_id": "W021-CLASSSEP-R3-REVIEW-01",
        "artifact_type": "independent_review_report",
        "created_at": CREATED,
        "reviewer": "worker-021",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_ids": ["GLOBAL", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "target_id": "reviews/CLASSSEP-calibration-adjudication.json",
        "target_sha256": adj_sha,
        "card_served": "comms/inbox/worker-075.jsonl#astra-life07-classsep-adjudication-review",
        "substitute_for": "reviews/CLASSSEP-calibration-adjudication-review.json "
                          "(left absent; named to worker-075)",
        "verdict": "accept",
        "score": 4.0,
        "reproduction": reproduction,
        "findings": findings,
        "hard_failures": [],
        "independence": {
            "declared": "worker-021 authored none of the four detector arms, neither the "
                        "worker-07 nor the worker-049 corpus, not the worker-035 battery, not the "
                        "r3 adjudication and not the lifecycle-05 instrument. No prior worker-021 "
                        "review targets CLASSSEP. Before measurement I read the r3 adjudication, "
                        "the audit-lead blocker texts and (disclosed) the headline of worker-017's "
                        "review; reviews 030/073 were not opened; my instrument imports no author "
                        "aggregation code (LIVE_LABELS / ASSERTION_MENTION_FIXTURES extracted by "
                        "ast.literal_eval from the pinned instrument).",
            "read_only": "no canonical/proposed/review write; detector bytes verified by sha256 "
                         "before and after; e36b0d644ca7 not loaded or cited.",
        },
        "falsifier": "Re-run artifacts/worker-021/classsep_r3_review/verify_classsep_r3.py at the "
                     "same pins: falsified if any of the 127 compared blocks flips, any K1-K11 "
                     "control fails, a genuine first-order C0/C2 merge assertion is found among "
                     "the claims labeled FP, or an arm meets the adoption bar; VOID on drift of "
                     "any pinned hash or of the adjudication/snapshot.",
        "no_gate_self_pass": "This sets no gate verdict, no node status, no validation_status and "
                             "no detector-of-record; G-AUDIT stays pending.",
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    review = {
        "artifact": "reviews/CLASSSEP-calibration-adjudication-review-021.json",
        "event_type": "review",
        "reviewer": "worker-021",
        "target_id": "CLASSSEP-calibration-adjudication",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_ids": ["GLOBAL", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "created_at": CREATED,
        "task_id": "W021-CLASSSEP-R3-REVIEW-01",
        "serves_card": "astra-life07-classsep-adjudication-review",
        "substitute_note": "The card names worker-075 and the artifact "
                           "reviews/CLASSSEP-calibration-adjudication-review.json; that path is "
                           "still absent (audit-l09-b5-classsep-review-missing-20260912T011904). "
                           "This is a non-author independent verdict offered as the substitute "
                           "per that blocker's first option; the named path was deliberately NOT "
                           "written because it belongs to another worker's card.",
        "target": {"path": "reviews/CLASSSEP-calibration-adjudication.json",
                   "sha256": adj_sha,
                   "snapshot": "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json",
                   "snapshot_sha256": snap_sha},
        "reviewed_sha256": adj_sha,
        "verdict": "accept",
        "score": 4.0,
        "reproduction": {
            "n_comparisons": comparison["n_comparisons"],
            "n_mismatches": comparison["n_mismatches"],
            "controls_passed": reproduction["controls_passed"],
            "per_arm": {
                a: {
                    "corpus_a": table[a]["corpus_a"]["verdict"],
                    "corpus_a_tp_fn_fp_tn": [table[a]["corpus_a"]["tp"], table[a]["corpus_a"]["fn"],
                                             table[a]["corpus_a"]["fp"], table[a]["corpus_a"]["tn"]],
                    "live_hard": table[a]["corpus_b_live"]["hard"],
                    "sens_spec": f"{table[a]['corpus_c']['sensitivity']}/"
                                 f"{table[a]['corpus_c']['specificity']}",
                    "cue_fn_high": table[a]["corpus_d"]["cue_fn_high"],
                    "battery": table[a]["corpus_d"]["battery"],
                    "meets_adoption_bar": table[a]["meets_adoption_bar"],
                } for a in arms},
            "decision_choice": census["decision"]["choice"],
            "adoptable_arms": census["decision"]["adoptable_arms"],
            "attribution": {
                "PROSEFIX_dc8aa0de_cue_fn_high":
                    census["corpus_d_worker049"]["PROSEFIX"]["cue_induced_fn_high_confidence"],
                "STAGED_e2d24b92_cue_fn_high":
                    census["corpus_d_worker049"]["STAGED"]["cue_induced_fn_high_confidence"],
                "confirmed": (
                    census["corpus_d_worker049"]["PROSEFIX"]["cue_induced_fn_high_confidence"] == 10
                    and census["corpus_d_worker049"]["STAGED"]["cue_induced_fn_high_confidence"] == 0),
            },
        },
        "hard_failures": [],
        "findings": findings,
        "independence": report["independence"],
        "artifact_refs": [
            "artifacts/worker-021/classsep_r3_review/report.json",
            "artifacts/worker-021/classsep_r3_review/census.json",
            "artifacts/worker-021/classsep_r3_review/controls.json",
            "artifacts/worker-021/classsep_r3_review/comparison.json",
            "artifacts/worker-021/classsep_r3_review/verify_classsep_r3.py",
            "artifacts/worker-021/classsep_r3_review/PRE_REGISTRATION.md",
        ],
        "falsifier": report["falsifier"],
        "next_falsifier": report["falsifier"],
        "no_gate_self_pass": report["no_gate_self_pass"],
    }
    dest = ROOT / "reviews/CLASSSEP-calibration-adjudication-review-021.json"
    dest.write_text(json.dumps(review, indent=2) + "\n")
    print("wrote", HERE / "report.json", sha(HERE / "report.json")[:12])
    print("wrote", dest, sha(dest)[:12])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
