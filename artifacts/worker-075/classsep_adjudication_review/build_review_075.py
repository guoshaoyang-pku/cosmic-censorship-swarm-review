#!/usr/bin/env python3
"""Build the worker-075 review artifact for the r3 CLASSSEP adjudication from the
measured reproduction (raw_measurements.json + per_fixture_census.json).

Writes:
  reviews/CLASSSEP-calibration-adjudication-review.json   (the card deliverable)
  artifacts/worker-075/classsep_adjudication_review/report.json  (compact 5-check report)

Read-only on every reviewed/canonical/proposed/schema/ledger file.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RAW = HERE / "raw_measurements.json"
PERFX = HERE / "per_fixture_census.json"
SCRIPT = HERE / "repro_classsep_r3_review_075.py"
REVIEW = ROOT / "reviews/CLASSSEP-calibration-adjudication-review.json"
REPORT = HERE / "report.json"

ARMS = ["APPLIED", "PRE", "STAGED", "PROSEFIX"]
LABELED_CLAIMS = [36, 94, 96, 97, 101, 112, 144, 152, 180, 192, 276, 306]
UNLABELED_CLAIMS = [327, 336]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(p: Path) -> str:
    return f"{p.relative_to(ROOT).as_posix()}#{sha256(p)[:12]}"


def main() -> int:
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    raw = json.loads(RAW.read_text())
    perfx = json.loads(PERFX.read_text())
    m = raw["measurements"]
    a, b, c, d = (m["corpus_a_27fixtures"], m["corpus_b_live"],
                  m["corpus_c_assertion_mention"], m["corpus_d_worker049_cue_fn"])
    bdet = raw["corpus_b_live_detail"]["APPLIED"]
    cmp_ = raw["comparison"]
    att = raw["attribution"]
    freeze = raw["freeze"]

    arm_table = {}
    for arm in ARMS:
        arm_table[arm] = {
            "corpus_a_27fixtures": {k: a[arm][k] for k in ("tp", "fp", "tn", "fn", "verdict")},
            "corpus_b_live_hard": {k: b[arm][k] for k in ("hard_total", "tp", "fp", "unlabeled_count",
                                                          "claims_flagged", "claims_in_map")},
            "corpus_c_sens_spec": {"sensitivity": c[arm]["sensitivity"],
                                   "specificity": c[arm]["specificity"],
                                   "tp": c[arm]["tp"], "fn": c[arm]["fn"],
                                   "fp": c[arm]["fp"], "tn": c[arm]["tn"]},
            "corpus_d_cue_fn": {"cue_induced_fn_total": d[arm]["cue_induced_fn_total"],
                                "cue_induced_fn_high_confidence":
                                    d[arm]["cue_induced_fn_high_confidence"],
                                "adversarial_cleared": d[arm]["adversarial_cleared"],
                                "worker035_battery":
                                    f"{d[arm]['worker035_battery']['passed']}/{d[arm]['worker035_battery']['total']}"},
            "meets_adoption_bar": m["decision"]["per_arm"][arm]["meets_bar"],
        }

    report = {
        "artifact": "worker-075-classsep-r3-adjudication-review-report",
        "created_at": now,
        "reviewer": "worker-075",
        "target": {"path": "reviews/CLASSSEP-calibration-adjudication.json",
                   "sha256": raw["target_sha256"]},
        "verdict": "accept",
        "score": 4.0,
        "hard_failures": [],
        "pins": raw["pins"],
        "freeze": freeze,
        "checks": {
            "i_27fixture_regression": {
                "result": "PASS 17TP/0FP/10TN/0FN on all four arms",
                "per_arm": {arm: a[arm]["verdict"] for arm in ARMS},
                "mismatch_vs_declared": 0,
            },
            "ii_applied_live_census": {
                "snapshot_sha256": "f344ed2aaea58e4d21c46c1d919e2476b860da4b757b9fbc948d3649bac7c749",
                "claims_in_snapshot": b["APPLIED"]["claims_in_map"],
                "hard_total": b["APPLIED"]["hard_total"],
                "labeled_metalinguistic_fp": b["APPLIED"]["fp"],
                "unlabeled": [{"claim_index": u["claim_index"],
                               "auto_mechanism": u["auto_mechanism"]} for u in bdet["unlabeled"]],
                "tp": b["APPLIED"]["tp"],
                "arithmetic": "17 labeled FP (12 claims, 17 finding-ordinals) + 2 unlabeled "
                              "DETECTOR_SELF meta-claims (claims[327],[336]) = 19 hard",
                "no_genuine_first_order_assertion": True,
            },
            "iii_adoption_bar": {
                "bar": {"corpus_a": "PASS 17/0/10/0", "sensitivity": ">=5/6",
                        "specificity": ">=9/10", "cue_fn_high": 0},
                "per_arm": m["decision"]["per_arm"],
                "adoptable_arms": m["decision"]["adoptable_arms"],
                "decision_choice_reproduced": m["decision"]["choice"],
            },
            "iv_attribution": att,
            "v_detector_freeze": freeze,
        },
        "comparison": {"declared_cells": cmp_["n_cells"], "mismatches": cmp_["n_mismatch"],
                       "mismatch_list": cmp_["mismatches"]},
        "reproduction": {"script": ref(SCRIPT), "raw": ref(RAW), "per_fixture": ref(PERFX)},
    }
    REPORT.write_text(json.dumps(report, indent=1) + "\n")

    review = {
        "artifact": "CLASSSEP-calibration-adjudication-review",
        "schema": "astra-worker/review/v1",
        "assignment": "astra-life07-classsep-adjudication-review",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": "GLOBAL",
        "class_ids_scanned": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN",
                              "AF-WCC-SCALAR-SPH"],
        "target_id": "CLASSSEP-calibration-adjudication",
        "target_artifact": "reviews/CLASSSEP-calibration-adjudication.json",
        "target_sha256": "7714ffd5b467c506bc8a8736ba1626a9f8a9211092e5313e74c77a4ccb51cec1",
        "reviewer": "worker-075",
        "actor": "worker-075",
        "created_at": now,
        "verdict": "accept",
        "score": 4.0,
        "hard_failures": [],
        "findings": [
            {"id": "W075-CAR-01",
             "check": "pins",
             "result": "pass",
             "text": "14/14 cited pins reproduce before and after the review: adjudication "
                     "7714ffd5 (sha256 7714ffd5b467c506bc8a8736ba1626a9f8a9211092e5313e74c77a4ccb51cec1), "
                     "r3 script fc92f4eac503, snapshot f344ed2aaea5, calibration module 8f2efd262f97, "
                     "w049 harness 6e5306aafe7b, w049 corpus 9eb2ea9e2743, w035 battery ef881c3aa6ef, "
                     "w07 results d69ad58468be, void evidence e36b0d644ca7, CF-29 forensics b573dcfdcc20, "
                     "and the four arms APPLIED a8c04fc31e4a / PRE c266dbceca87 / STAGED e2d24b927ee8 / "
                     "PROSEFIX dc8aa0de3869. No hash moved during the review."},
            {"id": "W075-CAR-02",
             "check": "i",
             "result": "pass",
             "text": "27-fixture regression reproduces 17TP/0FP/10TN/0FN PASS on all four arms "
                     "(per-fixture classes in per_fixture_census.json; 0 mismatches vs the declared "
                     "per-fixture census). The registered corpus cannot discriminate the revisions, so "
                     "it cannot license an adoption by itself."},
            {"id": "W075-CAR-03",
             "check": "ii",
             "result": "pass",
             "text": "APPLIED live census on the frozen snapshot f344ed2aaea5 (383 claims) is 19 hard = "
                     "17 labeled metalinguistic FP over 12 claims (finding-ordinals on 112/192/276 "
                     "included) + 2 unlabeled DETECTOR_SELF meta-claims claims[327] and claims[336]; "
                     "0 TP. Every one of the 19 findings was read in context by this reviewer: none is a "
                     "first-order assertion by the claim that C0 and C2 are one class. The two unlabeled "
                     "hits are meta-claims about the audit and its detector, matching the card's "
                     "DETECTOR_SELF description."},
            {"id": "W075-CAR-04",
             "check": "iii",
             "result": "pass",
             "text": "Per-arm sens/spec reproduced exactly: APPLIED 4/6-3/10, PRE 4/6-1/10, "
                     "STAGED 5/6-1/10, PROSEFIX 4/6-10/10; worker-035 battery 13/23, 11/23, 11/23, "
                     "23/23; cue-induced HIGH FN 1, 0, 0, 10. No arm meets sens>=5/6 AND spec>=9/10 "
                     "AND 27-fixture PASS AND 0 HIGH cue-induced FN; adoptable_arms = [] and decision "
                     "(c) is re-derived from the pre-registered bar."},
            {"id": "W075-CAR-05",
             "check": "iv",
             "result": "pass",
             "text": "Attribution correction CONFIRMED: the 10/10 HIGH (11/12 total) cue-carrying "
                     "suppression belongs to PROSEFIX dc8aa0de3869, not to STAGED e2d24b92. STAGED has "
                     "0 cue-induced FN and reaches 5/6 sensitivity only with specificity 1/10; its "
                     "rejection rests on the FP axis. PROSEFIX's 23/23 battery does not rescue it: it "
                     "suppresses genuine assertions."},
            {"id": "W075-CAR-06",
             "check": "v",
             "result": "pass",
             "text": "Detector freeze holds: research_map/class_separation.py is a8c04fc31e4a before "
                     "and after the review (mtime 2026-09-12T01:08:14+08:00, the mechanical restore), "
                     "byte-distinct from the preserved void e36b0d644ca7 at the CF-29 evidence path. "
                     "This review wrote no detector, schema, ledger or claim byte; it ran only its own "
                     "script under artifacts/worker-075/classsep_adjudication_review/ and this review "
                     "artifact."},
            {"id": "W075-CAR-07",
             "check": "scope",
             "result": "carried",
             "text": "Carried scope limits, none of which changes the verdict: (a) the hard count binds "
                     "the frozen snapshot f344ed2aaea5 only - the live map has grown past 383 claims and "
                     "its later findings are outside this census; (b) the unauthorized in-round detector "
                     "excursion to e36b0d644ca7 (01:06:12, restored 01:08:14) is a recorded, separately "
                     "adjudicated instrument-drift item (CF-29 / REC-29 / REC-38, worker-017 "
                     "B17-CS-01/02) and is not re-litigated here; (c) the LIVE_LABELS ground truth is "
                     "audit-authored - this review reproduced the counts and independently read all 19 "
                     "findings, but the label set remains the adjudication author's criterion, not this "
                     "reviewer's."},
        ],
        "checks": report["checks"],
        "per_fixture_tp_fp_fn_census": perfx,
        "arm_table": arm_table,
        "comparison_with_declared": {"declared_cells_compared": cmp_["n_cells"],
                                     "mismatches": cmp_["n_mismatch"],
                                     "mismatch_list": cmp_["mismatches"],
                                     "converse_scan_reproduced": True},
        "attribution_correction": att,
        "independence_basis": "worker-075 is a non-author of the reviewed adjudication "
                              "(author: astra-lead-audit), of the four detector arms, of the five "
                              "corpora, of the frozen snapshot, and of the FROZEN manifests. No "
                              "verdict text or number was reused from worker-017/030/045/098; all "
                              "numbers were re-measured from the primary bytes at the cited hashes. "
                              "Prior worker-075 outputs concern F1/F2a/F2b reviews, an L0 review and a "
                              "REC-38 closure check, none of which authored the reviewed artifact.",
        "authority_note": "Worker verdict only: this sets no gate verdict, no node status and no "
                          "validation_status. G-AUDIT remains pending; the controller and group leads "
                          "own gate movement.",
        "no_gate_self_pass": True,
        "falsifier": "Void if any of the 14 cited pins moves; if any arm's 27-fixture corpus fails; "
                     "if a genuine first-order C0/C2 merge assertion is found in "
                     "claims[36,94,96,97,101,112,144,152,180,192,276,306,327,336]; if any arm meets "
                     "sens>=5/6 AND spec>=9/10 AND 27-fixture PASS AND 0 HIGH cue-induced FN; or if "
                     "research_map/class_separation.py is written so the live detector is no longer "
                     "a8c04fc31e4a before the controller folds this review.",
        "evidence_refs": [],  # filled below
        "stop_rule_observed": "All cited hashes reproduced, so the review proceeded; nothing was "
                              "repaired. Read-only throughout.",
    }

    review["evidence_refs"] = [
        ref(ROOT / "reviews/CLASSSEP-calibration-adjudication.json"),
        ref(ROOT / "artifacts/audit/classsep_r3_adjudication.py"),
        ref(ROOT / "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json"),
        ref(ROOT / "artifacts/audit/classsep_calibration.py"),
        ref(ROOT / "research_map/class_separation.py"),
        ref(ROOT / "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py"),
        ref(ROOT / "proposed/class_separation.py"),
        ref(ROOT / "artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py"),
        ref(ROOT / "artifacts/worker-049/classsep_fn_audit/run_fn_audit_049.py"),
        ref(ROOT / "artifacts/worker-049/classsep_fn_audit/corpus.json"),
        ref(ROOT / "artifacts/worker-049/classsep_prose_fix/worker035_controls.json"),
        ref(ROOT / "artifacts/worker-07/class_separation_falsification/results.json"),
        ref(ROOT / "runtime/state/controller_verification/class_separation.e36b0d644ca.evidence.py"),
        ref(ROOT / "runtime/state/controller_verification/cf29-detector-write-forensics.json"),
        ref(SCRIPT), ref(RAW), ref(PERFX), ref(REPORT),
    ]

    REVIEW.write_text(json.dumps(review, indent=1) + "\n")
    print(f"wrote {REVIEW.relative_to(ROOT)} sha256={sha256(REVIEW)}")
    print(f"wrote {REPORT.relative_to(ROOT)} sha256={sha256(REPORT)}")
    print(f"verdict={review['verdict']} score={review['score']} cells={cmp_['n_cells']} "
          f"mismatches={cmp_['n_mismatch']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
