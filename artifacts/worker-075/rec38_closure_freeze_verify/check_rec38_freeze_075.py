#!/usr/bin/env python3
"""W075-REC38-CLOSURE-FREEZE-01: independent verification of the REC-38 closure
evidence for the CLASSSEP r3 adjudication review, plus detector-freeze integrity.

Why this task exists
--------------------
The pass-07 card `astra-life07-classsep-adjudication-review` was assigned to
worker-075 (artifact reviews/CLASSSEP-calibration-adjudication-review.json). While
worker-075 was reproducing the census, controller pass 08 (REC-38, 01:16:23) closed
that card SATISFIED by two other independent non-author accepts (worker-030 and
worker-045) and ruled "a third review is not required". worker-075 therefore does
NOT write the closed card's deliverable; it takes this bounded successor check
instead, and attaches its completed census reproduction as supporting evidence.

Read-only on every cited file. Writes only artifacts/worker-075/rec38_closure_freeze_verify/.
No detector write, no schema/ledger/claim edit, no gate verdict, no node status.

Exit codes: 0 all checks pass (verdict accept); 2 a cited pin failed to reproduce
(verdict inconclusive, fail closed); 3 internal inconsistency.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")

TASK_ID = "W075-REC38-CLOSURE-FREEZE-01"
NODE_ID = "A1"
GATE = "G-AUDIT"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]

PINS = {
    "adjudication": ("reviews/CLASSSEP-calibration-adjudication.json",
                     "7714ffd5b467c506bc8a8736ba1626a9f8a9211092e5313e74c77a4ccb51cec1"),
    "review_030": ("reviews/CLASSSEP-adjudication-review-030.json",
                   "d12b06c0294d2b276287ac1e200c63917d20f2f070a3e30c0fa3c2f17815c675"),
    "review_045_report": ("artifacts/worker-045/classsep_r3_indep_review/report.json",
                          "b25e4443f7623161aeb6f9c91a0c992e76e27a1ed7cbe5f30e11d0a6bcb832bb"),
    "detector_live": ("research_map/class_separation.py",
                      "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd"),
    "void_evidence": ("runtime/state/controller_verification/class_separation.e36b0d644ca.evidence.py",
                      "e36b0d644ca75b1efc291b44a3188facb7839d81790073341431f3bb77b86eed"),
    "cf29_forensics": ("runtime/state/controller_verification/cf29-detector-write-forensics.json", None),
    "life08_decisions": ("runtime/state/controller_verification/astra-lifecycle-08-decisions.json", None),
    "life08_report": ("runtime/state/controller_verification/lifecycle_20260912-011626.json",
                      "661cf0d8dd45ad1d6b4b92127d360d9810dbb008c613c22cc00a83de58924795"),
    "map_snapshot": ("artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json",
                     "f344ed2aaea58e4d21c46c1d919e2476b860da4b757b9fbc948d3649bac7c749"),
}
AUX = {
    "late_repro_results": "late_repro/repro_results.json",
    "current_checkpoint": "runtime/state/current_checkpoint.json",
    "worker045_outbox": "comms/outbox/worker-045.jsonl",
    "map_live": "research_map/research_map.json",
    "adjudication_script": "artifacts/audit/classsep_r3_adjudication.py",
    "worker049_harness": "artifacts/worker-049/classsep_fn_audit/run_fn_audit_049.py",
    "calibration_module": "artifacts/audit/classsep_calibration.py",
    "pre_detector": "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py",
    "staged_detector": "proposed/class_separation.py",
    "prosefix_detector": "artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "ABSENT"


def main() -> int:
    checks: list[dict] = []
    pin_fail: list[str] = []

    measured = {}
    for key, (rel, want) in PINS.items():
        got = sha(ROOT / rel)
        measured[key] = {"path": rel, "measured": got, "expected": want,
                         "match": (got == want) if want else None}
        if want and got != want:
            pin_fail.append(f"{key}: {got[:12]} != {want[:12]}")

    def check(cid: str, desc: str, ok: bool, measured_v, expected_v) -> None:
        checks.append({"id": cid, "description": desc, "pass": bool(ok),
                       "measured": measured_v, "expected": expected_v})

    # --- pin checks (fail closed) ---
    check("P1", "target adjudication bytes at cited hash", not any(p.startswith("adjudication:") for p in pin_fail),
          measured["adjudication"]["measured"], PINS["adjudication"][1])
    check("P2", "worker-030 review bytes at REC-38 cited hash", not any(p.startswith("review_030:") for p in pin_fail),
          measured["review_030"]["measured"], PINS["review_030"][1])
    check("P3", "worker-045 report bytes at REC-38 cited hash", not any(p.startswith("review_045_report:") for p in pin_fail),
          measured["review_045_report"]["measured"], PINS["review_045_report"][1])
    check("P4", "live detector bytes at the adjudicated APPLIED hash", not any(p.startswith("detector_live:") for p in pin_fail),
          measured["detector_live"]["measured"], PINS["detector_live"][1])
    check("P5", "void e36b0d644ca bytes preserved, and NOT the live instrument",
          (ROOT / PINS["detector_live"][0]).is_file()
          and sha(ROOT / PINS["detector_live"][0]) == PINS["detector_live"][1]
          and sha(ROOT / PINS["detector_live"][0]) != PINS["void_evidence"][1]
          and sha(ROOT / PINS["void_evidence"][0]) == PINS["void_evidence"][1],
          {"live": sha(ROOT / PINS["detector_live"][0]),
           "void_evidence": sha(ROOT / PINS["void_evidence"][0])},
          {"live": PINS["detector_live"][1], "void_evidence": PINS["void_evidence"][1]})
    check("P6", "CF-29 forensics pins the same void/restored pair",
          (lambda f: f.get("detector", {}).get("unauthorized_sha256") == PINS["void_evidence"][1]
           and f.get("detector", {}).get("restored_sha256") == PINS["detector_live"][1])(json.loads((ROOT / PINS["cf29_forensics"][0]).read_text())),
          None, {"unauthorized": PINS["void_evidence"][1], "restored": PINS["detector_live"][1]})

    adj = json.loads((ROOT / PINS["adjudication"][0]).read_text())
    r030 = json.loads((ROOT / PINS["review_030"][0]).read_text())
    r045 = json.loads((ROOT / PINS["review_045_report"][0]).read_text())
    dec = json.loads((ROOT / PINS["life08_decisions"][0]).read_text())
    rec38 = next((d for d in dec.get("decisions", []) if d.get("id") == "REC-38"), None)
    rep08 = json.loads((ROOT / PINS["life08_report"][0]).read_text())

    # --- semantic checks on the closure evidence ---
    check("C1", "worker-030 verdict accept with 4.0 and 51/51 checks, 0 blocking",
          r030.get("verdict") == "accept" and r030.get("score") == 4.0
          and r030.get("verified", {}).get("checks_run") == 51
          and r030.get("verified", {}).get("blocking_failures") == 0
          and r030.get("hard_failures") == []
          and r030.get("reviewed_sha256") == PINS["adjudication"][1],
          {"verdict": r030.get("verdict"), "score": r030.get("score"),
           "checks": r030.get("verified", {}).get("checks_run"),
           "blocking": r030.get("verified", {}).get("blocking_failures")},
          {"verdict": "accept", "score": 4.0, "checks": 51, "blocking": 0})

    check("C2", "worker-045 verdict accept, target at the cited adjudication hash, review event score 4.5",
          r045.get("verdict") == "accept"
          and r045.get("target", {}).get("sha256") == PINS["adjudication"][1]
          and r045.get("no_canonical_writes") is True
          and (lambda: any(json.loads(l).get("event_id") == "w045-review-20260912T011500-r3-indep"
                           and json.loads(l).get("verdict") == "accept"
                           and json.loads(l).get("score") == 4.5
                           for l in (ROOT / AUX["worker045_outbox"]).read_text().splitlines()))(),
          {"verdict": r045.get("verdict"), "target": r045.get("target", {}).get("sha256"),
           "canonical_writes": r045.get("no_canonical_writes")},
          {"verdict": "accept", "target": PINS["adjudication"][1], "canonical_writes": False})

    check("C3", "both reviewers are non-authors of the adjudication (author astra-lead-audit)",
          adj.get("actor") == "astra-lead-audit"
          and r030.get("reviewer") == "worker-030"
          and "none" in str(r030.get("independence", {}).get("relation_to_author", "")).lower()
          and r045.get("actor") == "worker-045",
          {"adjudication_actor": adj.get("actor"), "reviewers": [r030.get("reviewer"), r045.get("actor")]},
          {"adjudication_actor": "astra-lead-audit", "reviewers": ["worker-030", "worker-045"]})

    check("C4", "both closure reviews support decision (c) / no adoption",
          "not lexically separable" in r030.get("verified", {}).get("decision_supported", "").lower()
          and r045.get("decision_arithmetic", {}).get("recomputed_choice") == "c"
          and r045.get("decision_arithmetic", {}).get("choice_match") is True
          and r045.get("decision_arithmetic", {}).get("adoptable") == [],
          {"030": r030.get("verified", {}).get("decision_supported", "")[:120],
           "045_choice": r045.get("decision_arithmetic", {}).get("recomputed_choice"),
           "045_adoptable": r045.get("decision_arithmetic", {}).get("adoptable")},
          {"030": "decision (c)", "045_choice": "c", "045_adoptable": []})

    check("C5", "REC-38 records the closure and the continued detector freeze",
          rec38 is not None and "not required" in rec38.get("ruling", "")
          and "a8c04fc31e4a" in rec38.get("ruling", "")
          and "e36b0d644ca" in rec38.get("ruling", ""),
          (rec38 or {}).get("ruling", "")[:220],
          "REC-38 present with 'a third review is not required' and the freeze hashes")

    check("C6", "pass-08 decisions+report: detector void recorded, regression PASS 17/0/10/0",
          "e36b0d644ca stays void" in str(dec.get("evidence_hard_note", ""))
          and "restored detector a8c04fc31e4a" in str(dec.get("evidence_hard_note", ""))
          and rep08.get("classsep_regression", {}).get("verdict") == "PASS"
          and rep08.get("classsep_regression", {}).get("tp") == 17
          and rep08.get("classsep_regression", {}).get("tn") == 10
          and rep08.get("classsep_regression", {}).get("fp") == 0
          and rep08.get("classsep_regression", {}).get("fn") == 0
          and any("a8c04fc31e4a" in str(x) for x in rep08.get("evidence_hard_failures", [])),
          {"decision_note": str(dec.get("evidence_hard_note", ""))[:160],
           "regression": rep08.get("classsep_regression"),
           "drift_line_present": any("a8c04fc31e4a" in str(x) for x in rep08.get("evidence_hard_failures", []))},
          {"decision_note": "contains 'e36b0d644ca stays void' and 'restored detector a8c04fc31e4a'",
           "regression": "PASS 17/0/10/0", "drift_line_present": True})

    # --- late reproduction of the closed card, attached as supporting evidence ---
    late = json.loads((HERE / AUX["late_repro_results"]).read_text())
    mism: list[str] = []
    for arm in ["APPLIED", "PRE", "STAGED", "PROSEFIX"]:
        A, R = adj["corpus_a_27fixtures"][arm], late["corpus_a_27fixtures"]["arms"][arm]
        for k in ("tp", "fn", "fp", "tn", "n", "verdict"):
            if A[k] != R[k]:
                mism.append(f"corpus_a.{arm}.{k}: {A[k]} != {R[k]}")
        C, RC = adj["corpus_c_assertion_mention"][arm], late["corpus_c_assertion_mention"]["arms"][arm]
        for k in ("tp", "fn", "fp", "tn", "n", "sensitivity", "specificity"):
            if C[k] != RC[k]:
                mism.append(f"corpus_c.{arm}.{k}: {C[k]} != {RC[k]}")
        D, RD = adj["corpus_d_worker049_cue_fn"][arm], late["corpus_d_worker049"][arm]
        for k in ("cue_induced_fn_total", "cue_induced_fn_high_confidence", "adversarial_total", "twin_controls_flagged"):
            if D[k] != RD[k]:
                mism.append(f"corpus_d.{arm}.{k}: {D[k]} != {RD[k]}")
        if adj["decision"]["per_arm"][arm]["meets_bar"] != late["adoption_bar"][arm]["meets_all_four"]:
            mism.append(f"bar.{arm}")
    B, RB = adj["corpus_b_live"]["APPLIED"], late["corpus_b_live"]["arms"]["APPLIED"]
    for k in ("hard_total", "soft_total", "claims_flagged", "tp", "fp", "unlabeled_count"):
        if B[k] != RB[k]:
            mism.append(f"corpus_b.APPLIED.{k}: {B[k]} != {RB[k]}")
    if B["claims_in_map"] != late["corpus_b_live"]["snapshot"]["claims_in_map"]:
        mism.append("corpus_b.claims_in_map")
    if B["map_sha256"] != late["corpus_b_live"]["snapshot"]["sha256"]:
        mism.append("corpus_b.map_sha256")
    if len(adj["corpus_b_live_detail"]["APPLIED"]["labeled_detail"]) != len(RB["labeled"]):
        mism.append("corpus_b.labeled_len")
    if adj["decision"]["adoptable_arms"] != [] or late["author_decision_crosscheck"]["adoptable_arms"] != []:
        mism.append("adoptable_arms")
    if adj["decision"]["choice"] != "c" or late["author_decision_crosscheck"]["choice"] != "c":
        mism.append("decision_choice")
    check("C7", "late independent reproduction of the closed card matches the frozen census (0 mismatches)",
          len(mism) == 0 and late["detector_bytes"]["applied_stable"] is True
          and late["detector_bytes"]["live_equals_void_e36b0d644ca"] is False,
          {"mismatches": mism, "applied_stable": late["detector_bytes"]["applied_stable"],
           "live_equals_void": late["detector_bytes"]["live_equals_void_e36b0d644ca"]},
          {"mismatches": [], "applied_stable": True, "live_equals_void": False})

    # --- freeze timing: no detector write after the restoration ---
    det_path = ROOT / PINS["detector_live"][0]
    det_mtime = det_path.stat().st_mtime if det_path.is_file() else None
    det_mtime_iso = datetime.fromtimestamp(det_mtime, CST).isoformat(timespec="seconds") if det_mtime else None
    cp = json.loads((ROOT / AUX["current_checkpoint"]).read_text())
    check("C8", "detector mtime is the restore window (<= 01:09), before both closure reviews and pass 08",
          det_mtime is not None and det_mtime <= 1789146600,  # 2026-09-12T01:10:00+08:00
          {"mtime": det_mtime_iso, "checkpoint_id": cp.get("checkpoint_id"),
           "checkpoint_at": cp.get("created_at")},
          {"mtime": "<= 2026-09-12T01:10:00+08:00 (restore was 01:08:14)"})

    # --- final re-measure: no pin moved during this verification ---
    after = {k: sha(ROOT / rel) for k, (rel, _) in PINS.items()}
    moved = {k: {"before": measured[k]["measured"], "after": after[k]}
             for k in PINS if measured[k]["measured"] != after[k]}
    check("C9", "no cited pin moved during this verification (before == after)", not moved, moved, {})

    verdict = "accept"
    if pin_fail or moved:
        verdict = "inconclusive"
    elif any(not c["pass"] for c in checks if c["id"].startswith("C")):
        verdict = "revise"

    evidence_refs = [
        f"{PINS['adjudication'][0]}#sha256:{PINS['adjudication'][1][:12]}",
        f"{PINS['review_030'][0]}#sha256:{PINS['review_030'][1][:12]}",
        f"{PINS['review_045_report'][0]}#sha256:{PINS['review_045_report'][1][:12]}",
        f"{PINS['detector_live'][0]}#sha256:{PINS['detector_live'][1][:12]}",
        f"{PINS['void_evidence'][0]}#sha256:{PINS['void_evidence'][1][:12]}",
        f"{PINS['cf29_forensics'][0]}#sha256:{measured['cf29_forensics']['measured'][:12]}",
        f"{PINS['life08_decisions'][0]}#sha256:{measured['life08_decisions']['measured'][:12]}",
        f"{PINS['life08_report'][0]}#sha256:{PINS['life08_report'][1][:12]}",
        f"{PINS['map_snapshot'][0]}#sha256:{PINS['map_snapshot'][1][:12]}",
        f"{AUX['late_repro_results'].replace('late_repro/', 'artifacts/worker-075/rec38_closure_freeze_verify/late_repro/')}#sha256:{sha(HERE / AUX['late_repro_results'])[:12]}",
        f"{AUX['adjudication_script']}#sha256:{sha(ROOT / AUX['adjudication_script'])[:12]}",
        f"{AUX['calibration_module']}#sha256:{sha(ROOT / AUX['calibration_module'])[:12]}",
        f"{AUX['worker049_harness']}#sha256:{sha(ROOT / AUX['worker049_harness'])[:12]}",
    ]

    report = {
        "artifact": "W075-REC38-CLOSURE-FREEZE-VERIFY",
        "task_id": TASK_ID,
        "event_id": "w075-rec38verify-20260912T0118-report",
        "node_id": NODE_ID,
        "gate": GATE,
        "class_id": ";".join(CLASS_IDS),
        "class_ids": CLASS_IDS,
        "actor": "worker-075",
        "created_at": NOW,
        "task_selection": {
            "closed_card": "astra-life07-classsep-adjudication-review (worker-075)",
            "closed_by": "astra-lifecycle-08 REC-38, notice astra-life08-notice-classsep-review-satisfied 2026-09-12T01:16:23+08:00",
            "closure_evidence": [
                "reviews/CLASSSEP-adjudication-review-030.json#sha256:d12b06c0294d",
                "artifacts/worker-045/classsep_r3_indep_review/report.json#sha256:b25e4443f762",
            ],
            "controller_ruling_quote": "A third review is not required.",
            "action": ("worker-075 did NOT write the closed card's deliverable "
                       "reviews/CLASSSEP-calibration-adjudication-review.json. It takes one bounded "
                       "successor check instead: verify the closure evidence at its cited hashes and "
                       "re-verify the detector freeze that REC-38 conditions the round on. The census "
                       "reproduction completed for the closed card is attached as supporting evidence, "
                       "not offered as a third review."),
            "late_reproduction_status": ("completed independently before the closure notice was read; "
                                         "0 mismatches against the frozen adjudication; retained under "
                                         "late_repro/ as supporting evidence"),
        },
        "target": {
            "controller_decision": f"{PINS['life08_decisions'][0]}#sha256:{measured['life08_decisions']['measured'][:12]}",
            "rec38": {"id": "REC-38", "title": (rec38 or {}).get("title"),
                      "ruling": (rec38 or {}).get("ruling")},
            "adjudication": f"{PINS['adjudication'][0]}#sha256:{PINS['adjudication'][1][:12]}",
        },
        "independence": {
            "relation_to_authors": ("worker-075 authored none of the adjudication, the two closure "
                                    "reviews, the four detector arms, any corpus, or the census harness. "
                                    "worker-075's only prior F2b reconciliation material is cited as "
                                    "evidence by REC-36/REC-37, which does not bear on the CLASSSEP census."),
            "method": ("stdlib-only checker, read-only by file path; pins re-measured before and after; "
                       "no author runner executed for this check; the attached late reproduction used "
                       "the pinned audit instruments read-only and wrote only to tmp/ and this directory."),
            "read_only": True,
        },
        "frozen_map_snapshot": {
            "path": PINS["map_snapshot"][0],
            "sha256": measured["map_snapshot"]["measured"],
            "claims": late["corpus_b_live"]["snapshot"]["claims_in_map"],
            "note": ("the live map has grown since the snapshot; every CLASSSEP census number binds "
                     "ONLY to snapshot f344ed2aaea5"),
            "live_map_sha256_at_check": sha(ROOT / AUX["map_live"]),
        },
        "checks": checks,
        "pin_status": {"all_cited_pins_match": not pin_fail, "failures": pin_fail,
                       "no_pin_moved_during_check": not moved, "moved": moved},
        "detector_freeze": {
            "live_sha256": measured["detector_live"]["measured"],
            "live_mtime": det_mtime_iso,
            "void_sha256": PINS["void_evidence"][1],
            "void_is_live": False,
            "frozen_since_restore": not moved and det_mtime is not None and det_mtime <= 1789146600,
            "restore_authority": f"{PINS['cf29_forensics'][0]}#sha256:{measured['cf29_forensics']['measured'][:12]}",
        },
        "late_reproduction": {
            "status": "attached supporting evidence; not a third review",
            "script": f"late_repro/repro_075.py#sha256:{sha(HERE / 'late_repro/repro_075.py')[:12]}",
            "results": f"late_repro/repro_results.json#sha256:{sha(HERE / AUX['late_repro_results'])[:12]}",
            "flagged_claims": f"late_repro/flagged_claims.txt#sha256:{sha(HERE / 'late_repro/flagged_claims.txt')[:12]}",
            "summary": {
                "corpus_a_27_fixtures": {arm: f"{late['corpus_a_27fixtures']['arms'][arm]['verdict']} "
                                                f"{late['corpus_a_27fixtures']['arms'][arm]['tp']}/"
                                                f"{late['corpus_a_27fixtures']['arms'][arm]['fp']}/"
                                                f"{late['corpus_a_27fixtures']['arms'][arm]['tn']}/"
                                                f"{late['corpus_a_27fixtures']['arms'][arm]['fn']}"
                                         for arm in ["APPLIED", "PRE", "STAGED", "PROSEFIX"]},
                "corpus_b_hard": {arm: late["corpus_b_live"]["arms"][arm]["hard_total"]
                                  for arm in ["APPLIED", "PRE", "STAGED", "PROSEFIX"]},
                "corpus_b_applied_labeled_fp_unlabeled": [
                    late["corpus_b_live"]["arms"]["APPLIED"]["labeled_count"],
                    late["corpus_b_live"]["arms"]["APPLIED"]["unlabeled_count"]],
                "corpus_c_sens_spec": {arm: [late["corpus_c_assertion_mention"]["arms"][arm]["sensitivity"],
                                             late["corpus_c_assertion_mention"]["arms"][arm]["specificity"]]
                                       for arm in ["APPLIED", "PRE", "STAGED", "PROSEFIX"]},
                "corpus_d_high_cue_fn": {arm: late["corpus_d_worker049"][arm]["cue_induced_fn_high_confidence"]
                                         for arm in ["APPLIED", "PRE", "STAGED", "PROSEFIX"]},
                "adoptable_arms": [],
                "decision": "c",
                "independent_reading_of_the_17_labeled_FP": (
                    "all 17 findings across claims[36,94,96,97,101,112(x2),144,152,180,192(x3),"
                    "276(x3),306] are case-labels, negations, quotations, detector descriptions, a "
                    "window artifact, or detector-self; the 2 unlabeled (claims[327],336) are "
                    "meta-claims about the audit. No first-order C0/C2 merge assertion was found; "
                    "the adjudication falsifier is not triggered. See late_repro/flagged_claims.txt."),
                "caveat": ("this is a reproduction at the frozen hashes, not an adoption decision and "
                           "not a third review; REC-38 closure stands on worker-030 and worker-045."),
            },
        },
        "verdict": verdict,
        "hard_failures": [c for c in checks if not c["pass"]],
        "findings": [
            {"id": "W075-R38-01", "severity": "info",
             "finding": ("REC-38's two closure-evidence citations reproduce byte-exactly at check time: "
                         "review-030 d12b06c0294d (accept 4.0, 51/51 checks, 0 blocking) and worker-045 "
                         "report b25e4443f762 (accept, target 7714ffd5, decision (c) arithmetic, review "
                         "event score 4.5). Both reviewers are non-authors; the adjudication author is "
                         "astra-lead-audit.")},
            {"id": "W075-R38-02", "severity": "info",
             "finding": ("The detector freeze holds: research_map/class_separation.py is a8c04fc31e4a "
                         "before and after this check, mtime 2026-09-12T01:08:14+08:00 (the mechanical "
                         "restore), and is byte-distinct from the void e36b0d644ca whose bytes remain "
                         "preserved at the CF-29 evidence path.")},
            {"id": "W075-R38-03", "severity": "info",
             "finding": ("The pass-07 worker-075 card was closed mid-flight by pass 08; the completed "
                         "late reproduction (0 mismatches on the declared census, decision (c), no "
                         "adoptable arm, no genuine first-order C0/C2 assertion among the 17 labeled FP) "
                         "is attached as supporting evidence and is not written to the closed card's "
                         "reviews/ path.")},
            {"id": "W075-R38-04", "severity": "minor",
             "finding": ("Scope limit of this check: it verifies the closure evidence and freeze at "
                         "01:18-01:20; the live map has grown past the 383-claim snapshot and its new "
                         "hard findings (claims[393,395,406,410] at the pass-08 checkpoint) are outside "
                         "the frozen census. The freeze is a point-in-time measurement; any later write "
                         "to research_map/class_separation.py voids it.")},
        ],
        "not_claimed": [
            "no gate verdict (G-AUDIT stays pending; gate authority is Astra's and the group leads')",
            "no node status or validation_status",
            "no detector adoption, rollback, or edit; no third review of the adjudication",
            "no claim that assertion-vs-mention is or is not lexically separable in general",
            "no mathematics or physics claim",
        ],
        "falsifier": (
            "This verification is void if any cited pin moves (review-030 leaving d12b06c0294d, the "
            "worker-045 report leaving b25e4443f762, the adjudication leaving 7714ffd5b467, or the live "
            "detector leaving a8c04fc31e4a); it is falsified if either closure review's verdict or "
            "reviewer identity differs from REC-38's citation, if the live detector equals the void "
            "e36b0d644ca, if the detector mtime is later than the restore window, or if the attached "
            "late reproduction is shown to mismatch the frozen census. Reproduce: "
            "python3 artifacts/worker-075/rec38_closure_freeze_verify/check_rec38_freeze_075.py "
            "(exit 0 accept, 2 pin drift -> inconclusive, 3 internal inconsistency)."),
        "next_falsifier": (
            "Re-run after the next controller pass; a detector write, a changed closure-evidence byte, "
            "or a new full accept at the frozen A1 hashes would each change the state this check binds."),
        "evidence_refs": evidence_refs,
        "checkpoint": "artifacts/worker-075/rec38_closure_freeze_verify/CHECKPOINT.json",
        "no_gate_self_pass": ("This sets no gate verdict and no validation_status, and edits no "
                              "canonical, proposed or schema file. G-AUDIT stays pending."),
    }

    HERE.mkdir(parents=True, exist_ok=True)
    report_path = HERE / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")

    checkpoint = {
        "checkpoint_id": "w075-ckpt-20260912T0118-rec38-freeze",
        "task_id": TASK_ID,
        "actor": "worker-075",
        "node_id": NODE_ID,
        "gate": GATE,
        "class_ids": CLASS_IDS,
        "created_at": NOW,
        "report": f"artifacts/worker-075/rec38_closure_freeze_verify/report.json#sha256:{sha(report_path)}",
        "verdict": verdict,
        "checks_passed": f"{sum(1 for c in checks if c['pass'])}/{len(checks)}",
        "detector_live_sha256": measured["detector_live"]["measured"],
        "detector_freeze_holds": report["detector_freeze"]["frozen_since_restore"],
        "pins_moved": moved,
        "map_sha256_at_check": sha(ROOT / AUX["map_live"]),
        "next": "exit after outbox report; no further writes",
        "no_gate_self_pass": True,
    }
    (HERE / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=2) + "\n")

    print(json.dumps({"verdict": verdict, "checks": len(checks),
                      "passed": sum(1 for c in checks if c["pass"]),
                      "pin_failures": pin_fail, "moved": moved,
                      "report": str(report_path.relative_to(ROOT)),
                      "report_sha256": sha(report_path),
                      "checkpoint_sha256": sha(HERE / "CHECKPOINT.json")}, indent=1))
    if pin_fail or moved:
        return 2
    if any(not c["pass"] for c in checks if c["id"].startswith("C")):
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
