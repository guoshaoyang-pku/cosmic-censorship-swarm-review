#!/usr/bin/env python3
"""Emit astra-lead-audit lifecycle-07 events and write the lifecycle checkpoint.

Consumes: astra-life06-classsep-detector-adjudication (operative),
          human-pi-detector-fix-20260912T0100, astra-detector-fix-0105 (conflicting).

Idempotent: an event whose event_id is already present in the outbox is skipped.
Writes only comms/outbox/astra-lead-audit.jsonl and runtime/state/lead_audit_* .
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTBOX = ROOT / "comms/outbox/astra-lead-audit.jsonl"
STAMP = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
NOW = datetime.now().astimezone().isoformat(timespec="seconds")

ADJ = "reviews/CLASSSEP-calibration-adjudication.json"
SNAP = "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json"
TOOL = "artifacts/audit/classsep_r3_adjudication.py"
SUPERSEDED = "reviews/CLASSSEP-calibration-adjudication-l05-superseded.json"

PINS = {
    "research_map/class_separation.py": None,
    "proposed/class_separation.py": None,
    "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py": None,
    "artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py": None,
    "research_map/research_map.json": None,
    "runtime/bin/classsep_regression.py": None,
    "artifacts/worker-049/classsep_fn_audit/results.json": None,
    "artifacts/worker-098/classsep_prose_shadow/drift_recheck.json": None,
    "runtime/state/controller_verification/astra-lifecycle-06-decisions.json": None,
    "evaluation_rubric.yaml": None,
    "ledger/theorems.jsonl": None,
}


def sha(rel: str) -> str:
    p = ROOT / rel
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "ABSENT"


def ref(rel: str) -> str:
    return f"{rel}#{sha(rel)[:12]}"


def build_events(adj: dict, pins: dict) -> list[dict]:
    ev: list[dict] = []

    def add(e):
        e.setdefault("actor", "astra-lead-audit")
        e.setdefault("created_at", NOW)
        ev.append(e)

    # --- artifacts ---
    for rel, atype, node, note in [
        (ADJ, "classsep_adjudication_r3", "A1",
         "operative r3 adjudication; supersedes the l05 card at the same path"),
        (SNAP, "frozen_map_snapshot", "A1",
         "byte-frozen map snapshot the live census binds; map f344ed2aaea5, 383 claims"),
        (TOOL, "calibration_tool", "A1",
         "re-runnable four-arm census tool (27-fixture, live, assertion/mention, "
         "worker-049 FN, worker-035 battery)"),
        (SUPERSEDED, "superseded_adjudication", "A1",
         "l05 card preserved before the r3 supersession at the same path"),
    ]:
        add({"event_id": f"audit-l07-art-{Path(rel).stem[:40]}-{STAMP}", "event_type": "artifact",
             "node_id": node, "artifact_type": atype, "path": rel, "sha256": sha(rel),
             "validation_status": "unverified", "evidence_refs": [ref(rel)], "note": note})

    # --- the one operative review verdict ---
    add({"event_id": f"audit-l07-review-classsep-r3-{STAMP}", "event_type": "review",
         "target_id": "A1/classsep-detector-r3", "reviewer": "astra-lead-audit",
         "verdict": "revise", "score": 3.0,
         "hard_failures": [
             "no cited arm is adoptable: APPLIED spec 3/10 + 1 HIGH cue-induced FN; PRE spec 1/10 "
             "+ battery 11/23; STAGED spec 1/10; PROSEFIX clears mentions (spec 10/10, live hard "
             "1) but suppresses 10/12 HIGH genuine assertions",
             "APPLIED a8c04fc3 suppresses a genuine first-order assertion by context-window "
             "overreach: fixture A04 'The detector flagged this once; C0 and C2 are one class.'",
         ],
         "findings": [
             "decision (c): assertion-vs-mention is not lexically separable at this window by any "
             "of the three cited candidates; residual hard count stated honestly",
             "APPLIED live hard 19 on the frozen snapshot = 17 labeled metalinguistic FP + 2 new "
             "DETECTOR_SELF meta-claims (claims[327], claims[336]); independently reproduces the "
             "controller's evidence_hard_note '19 CLASSSEP metalinguistic-mention false positives "
             "(two new hits from meta-claims about the audit)'",
             "27-fixture corpus PASS 17/0/10/0 for ALL FOUR arms: the registered corpus cannot "
             "discriminate any revision, so it cannot license an adoption",
             "attribution correction: worker-049's 10 HIGH / 11 cleared suppression belongs to "
             "artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py#dc8aa0de3869, "
             "NOT to proposed/class_separation.py#e2d24b927ee8 (measured 0 cue-induced FN)",
             "STAGED e2d24b92 reaches sensitivity 5/6 only by deleting the quotation exemption "
             "and pays spec 1/10; its rejection rests on the FP axis, not the mis-attributed FN",
         ],
         "artifact_refs": [ADJ],
         "evidence_refs": [ref(ADJ), ref(SNAP), ref(TOOL),
                           "artifacts/worker-049/classsep_fn_audit/results.json#9e1bf2043934",
                           "artifacts/worker-098/classsep_prose_shadow/drift_recheck.json#ffabb753313f",
                           ref("runtime/state/controller_verification/astra-lifecycle-06-decisions.json")],
         "counts_as_full_schema_verdict": True,
         "counts_as_independent_second_verdict": False,
         "no_gate_verdict": True,
         "note": "one verdict, author-side; needs one non-author reviewer at the frozen hashes"})

    # --- status ---
    add({"event_id": f"audit-l07-status-a1-{STAMP}", "event_type": "status", "node_id": "A1",
         "status": "active", "hours": 1.5,
         "summary": "CLASSSEP r3 adjudicated with a four-arm, five-corpus census at cited hashes. "
                    "DECISION (c): assertion-vs-mention is not lexically separable at this window. "
                    "APPLIED 19 hard (17 labeled FP + 2 new meta), sens 4/6 spec 3/10, battery "
                    "13/23, 1 HIGH cue-FN; PRE 24 hard, spec 1/10, battery 11/23, 0 cue-FN; STAGED "
                    "25 hard, sens 5/6 spec 1/10; PROSEFIX 1 hard, spec 10/10, battery 23/23, but "
                    "10 HIGH cue-FN. No adoption, no rollback-by-audit, no retirement granted; "
                    "REC-22 pin ruling stands. G-AUDIT stays pending.",
         "evidence_refs": [ref(ADJ), ref(SNAP)],
         "next_falsifier": "an adopted detector that holds 27-fixture PASS 17/0/10/0, labeled "
                           "sensitivity >=5/6, specificity >=9/10 and 0 HIGH cue-induced FN; or a "
                           "genuine first-order assertion found among the 17 labeled FP claims"})

    # --- blockers ---
    add({"event_id": f"audit-l07-b1-applied-clause-fn-{STAMP}", "event_type": "blocker",
         "node_id": "A1",
         "description": "The unadopted drift a8c04fc3 buys specificity 1/10->3/10 and battery "
                        "11/23->13/23 over PRE, but introduces 1 HIGH-confidence cue-induced FALSE "
                        "NEGATIVE: fixture A04 'The detector flagged this once; C0 and C2 are one "
                        "class.' Two independent clauses; the guard's context window matches "
                        "'detector flag' and skips the whole window, suppressing the genuine "
                        "second-clause assertion. The clause boundary is the missing unit.",
         "needed_to_unblock": "a clause-scoped guard (window bounded at the clause, not the "
                              "character context) that keeps the A04 assertion firing while still "
                              "clearing the meta-clause; re-measure with "
                              "artifacts/audit/classsep_r3_adjudication.py. Authored by a non-audit "
                              "writer while the round is open.",
         "evidence_refs": [ref(ADJ), ref("artifacts/worker-049/classsep_fn_audit/corpus.json")]})
    add({"event_id": f"audit-l07-b2-prosefix-oversuppression-{STAMP}", "event_type": "blocker",
         "node_id": "A1",
         "description": "PROSEFIX dc8aa0de is the only arm that clears the live mention FPs "
                        "(live hard 19->1, spec 10/10, battery 23/23) but it suppresses 10 of 12 "
                        "HIGH-confidence genuine assertions on the worker-049 adversarial corpus "
                        "(11 of 12 cleared). It is unadoptable and must not be shipped as the "
                        "detector; it is not one of the three cited candidates.",
         "needed_to_unblock": "a rule that keeps A01-A12 firing (or at minimum the 9 HIGH twins) "
                              "while still clearing M1-M10; the corpus shows the surface form of "
                              "assertion and mention is identical, so this needs a "
                              "structure/topology cue, not another lexical window",
         "evidence_refs": [ref(ADJ), ref("artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py")]})
    add({"event_id": f"audit-l07-b3-no-adoptable-arm-{STAMP}", "event_type": "blocker",
         "node_id": "A1",
         "description": "No cited arm meets the pre-registered adoption bar (27-fixture PASS "
                        "17/0/10/0 AND labeled sensitivity >=5/6 AND specificity >=9/10 AND 0 "
                        "HIGH cue-induced FN). Residual hard count on the live bytes is 19 at "
                        "snapshot f344ed2aaea5 (17 labeled metalinguistic FP + 2 new meta-claims). "
                        "No claim retirement is granted this round, so classsep_hard_raw == "
                        "classsep_hard_calibrated == 19 and the CF-16 finding stays live.",
         "needed_to_unblock": "either an adoptable detector revision (see B1/B2) or a controller "
                              "acceptance that the residual is a documented instrument limit; "
                              "G-AUDIT may not be failed on a raw count with no adopted calibration",
         "evidence_refs": [ref(ADJ), ref(SNAP)]})
    add({"event_id": f"audit-l07-b4-audit-author-conflict-{STAMP}", "event_type": "blocker",
         "node_id": "GLOBAL",
         "description": "Two queue items direct the AUDIT lead to author the detector fix: "
                        "human-pi-detector-fix-20260912T0100 ('make the narrowest context-aware "
                        "fix', artifact research_map/class_separation.py) and astra-detector-fix-0105 "
                        "(same). This conflicts with (i) REC-22's open-round detector-write freeze, "
                        "and (ii) the no-self-pass rule: the audit lead authored this adjudication "
                        "and cannot also author the artifact it measures. Audit did NOT write the "
                        "detector; the freeze holds and research_map/class_separation.py is "
                        "unchanged at a8c04fc3 through this round.",
         "needed_to_unblock": "controller reassigns the detector edit to a non-audit writer (the "
                              "controller owns research_map/class_separation.py), then audit "
                              "re-measures at the new hash; or explicitly closes the freeze",
         "evidence_refs": ["comms/inbox/astra-lead-audit.jsonl#human-pi-detector-fix-20260912T0100",
                           "comms/inbox/astra-lead-audit.jsonl#astra-detector-fix-0105",
                           ref("runtime/state/controller_verification/astra-lifecycle-06-decisions.json")]})
    add({"event_id": f"audit-l07-b5-map-growth-{STAMP}", "event_type": "blocker",
         "node_id": "A1",
         "description": "The live map grew 292 -> 383 claims (+91) before this round; worker-098's "
                        "and life05's live counts bind stale map snapshots and are superseded. "
                        "LIVE_LABELS covers claim indices <=306, so 2 of the 19 APPLIED hard "
                        "findings are outside the labeled set (claims[327], claims[336], both "
                        "DETECTOR_SELF meta-claims about the audit) and are reported as unlabeled "
                        "rather than silently counted FP.",
         "needed_to_unblock": "writers quiesce at a published pin; a human/author reads the two "
                              "new meta-claims and extends LIVE_LABELS; then re-run "
                              "artifacts/audit/classsep_r3_adjudication.py",
         "evidence_refs": [ref(ADJ), ref(SNAP)]})
    add({"event_id": f"audit-l07-b6-attribution-{STAMP}", "event_type": "blocker",
         "node_id": "A1",
         "description": "The assignment card astra-life06-classsep-detector-adjudication attributes "
                        "'10/10 cue-carrying genuine assertions suppressed, 9 HIGH' to "
                        "proposed/class_separation.py#e2d24b927ee8. Measured: that suppression is "
                        "dc8aa0de3869 (worker-049 prosefix); e2d24b92 clears 0 cue-carrying "
                        "assertions (0 cue-indued FN). The staged candidate's rejection is correct "
                        "but rests on the FP axis (spec 1/10), not on this FN evidence.",
         "needed_to_unblock": "controller corrects the card/record so the two staged artifacts are "
                              "not conflated in later rounds",
         "evidence_refs": [ref(ADJ), ref("artifacts/worker-049/classsep_fn_audit/results.json")]})

    # --- direction update ---
    add({"event_id": f"audit-l07-direction-separability-{STAMP}",
         "event_type": "direction_update", "group_id": "audit",
         "old_direction": "keep revising the CLASSSEP lexical detector until the live hard count "
                          "falls to zero, treating each fall as progress",
         "new_direction": "stop treating a falling raw count as progress. Publish classsep_hard_raw "
                          "and classsep_hard_calibrated every tick; with no adopted calibration "
                          "they are equal and the CF-16 finding stays live. Adopt a detector only "
                          "at 27-fixture PASS 17/0/10/0 AND sensitivity >=5/6 AND specificity "
                          ">=9/10 AND 0 HIGH cue-induced FN. The measured impossibility result -- "
                          "the only arm that clears mentions (PROSEFIX) loses 10/12 HIGH genuine "
                          "assertions -- means the next attempt must use a structure/topology cue "
                          "(clause or dependency structure), not another lexical window.",
         "reason": "four-arm census at cited hashes: APPLIED 19 hard/spec 3/10/1 HIGH cue-FN; PRE "
                   "24/spec 1/10; STAGED 25/spec 1/10; PROSEFIX 1/spec 10/10/10 HIGH cue-FN. The "
                   "27-fixture corpus PASSes for every arm, so it cannot license an adoption. The "
                   "raw count is monotone in verification traffic, not in class leakage.",
         "evidence_refs": [ref(ADJ), ref(SNAP)],
         "budget_delta_agent_hours": 0.0,
         "next_falsifier": "an adopted detector holding the full bar; or a genuine first-order "
                           "C0/C2 assertion found in a claim labeled FP in LIVE_LABELS"})
    return ev


def main() -> int:
    adj = json.loads((ROOT / ADJ).read_text())
    pins = {rel: sha(rel) for rel in PINS}
    events = build_events(adj, pins)

    existing = set()
    if OUTBOX.is_file():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except ValueError:
                continue
    new = [e for e in events if e["event_id"] not in existing]
    with OUTBOX.open("a") as f:
        for e in new:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    ckpt = {
        "checkpoint": "lead-audit-lifecycle-07",
        "at": NOW, "actor": "astra-lead-audit",
        "node_ids": ["A1"], "gate": "G-AUDIT",
        "assignments_consumed": [
            "astra-life06-classsep-detector-adjudication",
            "human-pi-detector-fix-20260912T0100",
            "astra-detector-fix-0105",
        ],
        "artifacts_written": {ADJ: sha(ADJ), SNAP: sha(SNAP), SUPERSEDED: sha(SUPERSEDED)},
        "tools_written": {TOOL: sha(TOOL)},
        "events_emitted": [e["event_id"] for e in new],
        "events_skipped_idempotent": [e["event_id"] for e in events if e["event_id"] in existing],
        "blockers": [e["event_id"] for e in new if e["event_type"] == "blocker"],
        "decision": {"choice": adj["decision"]["choice"], "text": adj["decision"]["text"],
                     "per_arm": adj["decision"]["per_arm"]},
        "detector_writes": "NONE. research_map/class_separation.py unchanged at a8c04fc3 through "
                           "this round; REC-22 open-round freeze respected.",
        "gate_verdicts_set": "none (G-AUDIT stays pending; one author-side verdict only)",
        "pins_measured": pins,
        "live_census_binding": {"snapshot": SNAP, "sha256": sha(SNAP),
                                "map_sha256": sha("research_map/research_map.json"),
                                "claims": 383,
                                "note": "live counts bind the snapshot only; the map grew "
                                        "292->383 before this round and was quiescent during it"},
        "next_falsifier": "re-measure every pin next lifecycle; an adopted detector holding "
                          "27-fixture PASS 17/0/10/0 + sens >=5/6 + spec >=9/10 + 0 HIGH "
                          "cue-induced FN; a genuine assertion inside a LIVE_LABELS FP claim; or "
                          "any detector write while the REC-22 freeze is open.",
    }
    (ROOT / "runtime/state/lead_audit_lifecycle_07_checkpoint.json").write_text(
        json.dumps(ckpt, indent=2) + "\n")
    with (ROOT / "runtime/state/lead_audit_checkpoints.jsonl").open("a") as f:
        f.write(json.dumps(ckpt, sort_keys=True) + "\n")

    print(f"events new={len(new)} skipped={len(events)-len(new)}")
    for e in new:
        print(f"  {e['event_type']:<16} {e['event_id']}")
    print("checkpoint -> runtime/state/lead_audit_lifecycle_07_checkpoint.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
