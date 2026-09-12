#!/usr/bin/env python3
"""Emit astra-lead-audit lifecycle-08 events and write the lifecycle-08 checkpoint.

Consumes (as records, not as authority):
  * the controller notices astra-life07-notice-classsep-r3 / astra-life07-notice-injection
    (REC-29/30/31, CF-29/CF-30) delivered to this inbox;
  * the independent review reviews/CLASSSEP-adjudication-review-017.json (worker-017).

Does NOT action the quarantined cards human-pi-detector-fix-20260912T0100,
astra-detector-fix-0105, astra-detector-patch-result-0112 (CF-30/REC-31: not authority).

Idempotent: an event whose event_id is already in the outbox is skipped.
Writes only comms/outbox/astra-lead-audit.jsonl and runtime/state/lead_audit_*.
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

ADJ = "reviews/CLASSSEP-review-adjudication-l08.json"
REVIEW017 = "reviews/CLASSSEP-adjudication-review-017.json"
REPRO = "artifacts/audit/classsep_l08_drift_repro_20260912T011100.json"
INSTRUMENT = "artifacts/audit/classsep_l08_drift_repro.py"
META = "artifacts/audit/meta_audit_fixtures_l08.json"
REGRESSION = "artifacts/audit/l08/classsep_regression_l08.txt"
AUDITOUT = "artifacts/audit/l08/audit_evidence_l08.txt"
MAPSNAP = "artifacts/audit/pins/classsep_l08b_map_snapshot_20260912T011100.json"
SUPERSEDED = ("artifacts/audit/classsep_l08_drift_repro_20260912T010856"
              ".MISLABELED-live-arm-void.json")

PINS = {
    "research_map/class_separation.py": None,
    "proposed/class_separation.py": None,
    "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py": None,
    "artifacts/worker-073/classsep_union_separability/pinned/class_separation.live.a8c04fc31e4a.py": None,
    "artifacts/worker-073/classsep_union_separability/pinned/class_separation.live.e36b0d644ca7.py": None,
    "artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py": None,
    "research_map/research_map.json": None,
    "runtime/bin/classsep_regression.py": None,
    "runtime/state/artifact_hashes.json": None,
    "runtime/state/controller_verification/cf29-detector-write-forensics.json": None,
    "runtime/state/comms_quarantine/astra-lead-audit-inbox-lines24-25-27-20260912T0112.jsonl": None,
    "evaluation_rubric.yaml": None,
    "ledger/theorems.jsonl": None,
    "artifacts/formulation/FROZEN.json": None,
    ADJ: None, REVIEW017: None, REPRO: None, INSTRUMENT: None, META: None,
    REGRESSION: None, AUDITOUT: None, MAPSNAP: None, SUPERSEDED: None,
}


def sha(rel: str) -> str:
    p = ROOT / rel
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "ABSENT"


def ref(rel: str) -> str:
    return f"{rel}#{sha(rel)[:12]}"


def build_events(pins: dict) -> list[dict]:
    ev: list[dict] = []

    def add(e):
        e.setdefault("actor", "astra-lead-audit")
        e.setdefault("created_at", NOW)
        ev.append(e)

    for rel, atype, node, note in [
        (ADJ, "review_adjudication", "A1",
         "adjudication of the independent worker-017 review; carries B17-CS-01/02 and N17-CS-01..05 "
         "dispositions; not a gate verdict and not a second independent verdict"),
        (REPRO, "independent_census_repro", "A1",
         "corrected v2 census: five declared arms + live-now, corpora A/B(l07+l08)/C/D/M, pins "
         "pre==post; reproduces the review's numbers exactly"),
        (INSTRUMENT, "audit_instrument", "A1",
         "re-runnable census instrument; read-only on canonical/proposed/corpus files"),
        (META, "meta_audit_fixtures", "A1",
         "six audit-authored clause-scope probes, kept OUT of the canonical worker-07 corpus"),
        (REGRESSION, "canonical_regression_output", "A1",
         "python3 runtime/bin/classsep_regression.py --verbose at the operative bytes: 17/17 "
         "leaks, 10/10 controls, FP 0 FN 0, PASS exit 0"),
        (AUDITOUT, "canonical_audit_output", "A1",
         "python3 research_map/audit_evidence.py: 24 hard = 23 CLASSSEP + 1 standing "
         "'frozen artifact drifted during review' c266dbec -> a8c04fc3"),
        (MAPSNAP, "frozen_map_snapshot", "A1",
         "l08 census snapshot; live counts at these bytes bind this snapshot only"),
        (SUPERSEDED, "self_correction_evidence", "A1",
         "v1 instrument output whose live arm was mislabeled; preserved renamed, never emitted, "
         "superseded by REPRO"),
        (REVIEW017, "independent_review_under_adjudication", "A1",
         "worker-017 non-author review of reviews/CLASSSEP-calibration-adjudication.json"),
    ]:
        add({"event_id": f"audit-l08-art-{Path(rel).stem[:44]}-{STAMP}", "event_type": "artifact",
             "node_id": node, "artifact_type": atype, "path": rel, "sha256": sha(rel),
             "validation_status": "unverified", "evidence_refs": [ref(rel)], "note": note})

    add({"event_id": f"audit-l08-review-review017-{STAMP}", "event_type": "review",
         "target_id": "reviews/CLASSSEP-adjudication-review-017.json",
         "reviewer": "astra-lead-audit", "verdict": "accept", "score": 4.0,
         "reviewed_sha256": sha(REVIEW017),
         "hard_failures": [
             "B17-CS-01 partially resolved: CF-29/REC-29 records the 01:06:12 write and 01:08:14 "
             "restore with before/after sha256 and void the e36b bytes; the review's falsifier also "
             "requires a named detector-of-record, which is still unmet",
             "B17-CS-02 open and escalated: the declared frozen pin c266dbec differs from the "
             "operative bytes a8c04fc3, and the canonical audit_evidence.py hard-fails on the "
             "split, so the full-audit count is 24 = 23 CLASSSEP + 1 drift",
         ],
         "findings": [
             "the review's reproduction is EXACT: every declared r3 census number reproduced on an "
             "independently written runner, 0 mismatches, 7/7 controls; this lifecycle's re-run "
             "reproduces the review in turn, including the void arm at hard 16 on the l07 snapshot",
             "N17-CS-01..05 accepted; N17-CS-04 (A04 clause-scoped FN survives the operative bytes "
             "and the void write) is carried as AUD-L08-02",
             "N17-CS-05 accepted as a limitation: corpus C is adjudicator-authored; the l08 meta "
             "probe reduces but does not remove that reliance",
         ],
         "artifact_refs": [ADJ, REPRO],
         "evidence_refs": [ref(REVIEW017), ref(ADJ), ref(REPRO),
                           ref("runtime/state/controller_verification/cf29-detector-write-forensics.json")],
         "counts_as_full_schema_verdict": False,
         "counts_as_independent_second_verdict": False,
         "no_gate_verdict": True,
         "note": "audit adjudicates a review of audit's own r3 output; it cannot be counted as the "
                 "independent verdict on that output and sets no gate verdict"})

    add({"event_id": f"audit-l08-status-a1-{STAMP}", "event_type": "status", "node_id": "A1",
         "status": "active", "hours": 1.0,
         "summary": "Lifecycle-08: independent reproduction of the worker-017 review and the "
                    "detector-of-record measurement. Canonical regression at the operative bytes "
                    "PASS 17/17 leaks + 10/10 controls. Canonical full audit: 24 hard = 23 CLASSSEP "
                    "metalinguistic findings + 1 HARD frozen-artifact drift c266dbec -> a8c04fc3. "
                    "No arm meets the adoption bar at any of the three hashes (pin c266dbec, "
                    "operative a8c04fc3, void e36b0d644ca7); decision (c) stands. Detector stable "
                    "at a8c04fc3 all round; every pin re-measured pre==post. The quarantined "
                    "detector-fix cards were NOT actioned (CF-30/REC-31). G-AUDIT stays pending.",
         "evidence_refs": [ref(ADJ), ref(REPRO), ref(AUDITOUT), ref(REGRESSION)],
         "next_falsifier": "a controller event naming the detector-of-record; re-run of "
                           "artifacts/audit/classsep_l08_drift_repro.py at those bytes; the "
                           "frozen-drift HARD failure must then disappear from audit_evidence.py"})

    add({"event_id": f"audit-l08-b1-detector-of-record-{STAMP}", "event_type": "blocker",
         "node_id": "A1",
         "description": "Detector-of-record unresolved and now measured as a standing canonical "
                        "HARD failure. research_map/research_map.json frozen_artifacts[2] is "
                        "active:true at c266dbec (frozen 23:30:20) while the live operative bytes "
                        "are a8c04fc3 (restored 01:08:14). audit_evidence.py at the 483-claim map "
                        "a5e5ec532371 reports 24 hard, 0 soft, including 'HARD frozen artifact "
                        "drifted during review: research_map/class_separation.py c266dbceca87 -> "
                        "a8c04fc31e4a'. The CLASSSEP count is therefore 19 vs 24 at the l07 "
                        "snapshot and 23 vs 30 at the l08 snapshot depending on which bytes are "
                        "meant. G-AUDIT cannot be adjudicated while the canonical audit hard-fails "
                        "on the instrument it judges.",
         "needed_to_unblock": "controller names ONE detector-of-record and, in a single recorded "
                              "event, updates frozen_artifacts[2] and the r3 APPLIED pin together "
                              "(adopt a8c04fc3 or roll back to c266dbec; either is coherent, the "
                              "split is not); then audit re-measures and requires the drift HARD "
                              "failure to disappear",
         "evidence_refs": [ref(AUDITOUT), ref(REPRO), ref("research_map/research_map.json"),
                           ref("runtime/state/controller_verification/cf29-detector-write-forensics.json")]})

    add({"event_id": f"audit-l08-b2-a04-clause-fn-{STAMP}", "event_type": "blocker",
         "node_id": "A1",
         "description": "The A04 clause-scoped FALSE NEGATIVE is introduced by the operative "
                        "bytes relative to the declared pin: pin c266dbec fires A04 "
                        "('The detector flagged this once; C0 and C2 are one class.', cue-induced "
                        "HIGH FN 0/12), operative a8c04fc3 and void e36b0d644ca7 suppress it "
                        "(1/12 each). The l08 audit-authored meta probe generalises the defect: "
                        "a8c04fc3 misses M04 and M06 (assert 1/3), the void write misses all three "
                        "genuine assertions (0/3), PROSEFIX misses M02 and M04. No measured arm "
                        "both fires A04 and clears the metalinguistic mentions.",
         "needed_to_unblock": "a non-audit writer authors a clause-scoped guard (window bounded at "
                              "the clause, not the character context); the canonical 27-fixture "
                              "corpus was NOT edited by audit and merging the meta probes into "
                              "worker-owned ground truth must be done by a non-audit writer",
         "evidence_refs": [ref(ADJ), ref(REPRO), ref(META), ref("artifacts/worker-049/classsep_fn_audit/corpus.json")]})

    add({"event_id": f"audit-l08-b3-map-growth-{STAMP}", "event_type": "blocker",
         "node_id": "A1",
         "description": "The live map is moving fast: 383 claims at the l07 snapshot "
                        "f344ed2aaea5 (01:03:24) -> 461 at the v1 l08 snapshot (01:08:56) -> 483 "
                        "at the l08b snapshot a5e5ec532371 (01:10:29). The same a8c04fc3 bytes "
                        "produce 19 CLASSSEP hard findings at 383 claims and 23 at 483, so every "
                        "live count is meaningless unless cited with the snapshot it binds.",
         "needed_to_unblock": "cite counts only against a named map snapshot; re-measure after "
                              "writers quiesce at a published pin",
         "evidence_refs": [ref(REPRO), ref(MAPSNAP), ref("research_map/research_map.json")]})

    add({"event_id": f"audit-l08-b4-quarantine-corroboration-{STAMP}", "event_type": "blocker",
         "node_id": "GLOBAL",
         "description": "Corroboration, not a new defect: the three cards that directed the audit "
                        "lead to author or freeze the detector (human-pi-detector-fix-20260912T0100, "
                        "astra-detector-fix-0105, astra-detector-patch-result-0112) are quarantined "
                        "by CF-30/REC-31 at "
                        "runtime/state/comms_quarantine/astra-lead-audit-inbox-lines24-25-27-20260912T0112.jsonl "
                        "(sha 8fadc2410046) as non-authority, and were NOT actioned; the l07 "
                        "refusal (audit-l07-b4) is upheld. Audit's own timeline independently "
                        "reproduces the CF-29 hashes: e36b0d644ca7 live at 01:07:0x, rewrite at "
                        "01:08:14, stable a8c04fc3 at 01:11:0x.",
         "needed_to_unblock": "no audit action required; recorded so the quarantine ruling is "
                              "hash-bound in the accepted stream and a genuine Human-PI directive "
                              "is re-sent as a well-formed accepted event if intended",
         "evidence_refs": [ref("runtime/state/comms_quarantine/astra-lead-audit-inbox-lines24-25-27-20260912T0112.jsonl"),
                           ref("runtime/state/controller_verification/cf29-detector-write-forensics.json"),
                           ref(ADJ)]})

    add({"event_id": f"audit-l08-b5-self-correction-{STAMP}", "event_type": "blocker",
         "node_id": "A1",
         "description": "Self-correction, no downstream impact: v1 of the l08 reproduction "
                        "(classsep_l08_drift_repro_20260912T010856.json) mislabeled its live arm "
                        "because it ran at 01:08:56, after the 01:08:14 restore, so the arm named "
                        "LIVE_E36B actually measured the restored a8c04fc3 bytes. Detected by "
                        "post-hoc hash re-measurement, preserved byte-verbatim under a MISLABELED "
                        "name, never emitted as an event, superseded by the corrected v2. The v1 "
                        "census numbers remain valid FOR a8c04fc3, so no count changes.",
         "needed_to_unblock": "none; recorded because an unlabeled mislabeled census would be a "
                              "hash-attribution hazard if cited later",
         "evidence_refs": [ref(SUPERSEDED), ref(REPRO), ref(INSTRUMENT)]})

    add({"event_id": f"audit-l08-direction-binding-{STAMP}", "event_type": "direction_update",
         "group_id": "audit",
         "old_direction": "treat the declared frozen pin as the detector for measurement purposes "
                          "and cite CLASSSEP hard counts without naming the executing bytes",
         "new_direction": "bind every classsep count to (a) the map snapshot and (b) the byte hash "
                          "that actually executed; require a named detector-of-record before any "
                          "G-AUDIT adjudication, and treat a pin/live split as a measurable HARD "
                          "failure rather than a documentation note",
         "reason": "the canonical audit_evidence.py hard-fails on the c266dbec -> a8c04fc3 split "
                   "(24 = 23 CLASSSEP + 1 drift), and the same a8c04fc3 bytes yield 19 vs 23 "
                   "CLASSSEP findings at 383 vs 483 map claims",
         "evidence_refs": [ref(AUDITOUT), ref(REPRO), ref(ADJ)],
         "budget_delta_agent_hours": 0.0,
         "next_falsifier": "a controller-recorded detector-of-record after which the drift HARD "
                           "failure disappears and the count is stable across two consecutive "
                           "audit runs"})
    return ev


def main() -> int:
    pins = {rel: sha(rel) for rel in PINS}
    events = build_events(pins)

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

    mapdoc = json.loads((ROOT / "research_map/research_map.json").read_text())
    ckpt = {
        "checkpoint": "lead-audit-lifecycle-08",
        "at": NOW, "actor": "astra-lead-audit",
        "node_ids": ["A1"], "gate": "G-AUDIT",
        "assignments_consumed": [
            "astra-life07-notice-classsep-r3 (REC-29/30/31 notice, recorded not actioned)",
            "astra-life07-notice-injection (CF-30 quarantine notice, recorded not actioned)",
            "reviews/CLASSSEP-adjudication-review-017.json (independent review, adjudicated)",
        ],
        "assignments_refused_not_actioned": [
            "human-pi-detector-fix-20260912T0100 (quarantined, CF-30/REC-31)",
            "astra-detector-fix-0105 (quarantined, CF-30/REC-31)",
            "astra-detector-patch-result-0112 (quarantined, CF-30/REC-31)",
        ],
        "artifacts_written": {ADJ: sha(ADJ), REPRO: sha(REPRO), META: sha(META),
                              REGRESSION: sha(REGRESSION), AUDITOUT: sha(AUDITOUT),
                              MAPSNAP: sha(MAPSNAP)},
        "tools_written": {INSTRUMENT: sha(INSTRUMENT)},
        "self_correction": {SUPERSEDED: sha(SUPERSEDED)},
        "events_emitted": [e["event_id"] for e in new],
        "events_skipped_idempotent": [e["event_id"] for e in events if e["event_id"] in existing],
        "blockers": [e["event_id"] for e in new if e["event_type"] == "blocker"],
        "detector_writes": "NONE. research_map/class_separation.py read-only all round, stable at "
                           "a8c04fc31e4a; no schema, ledger, corpus or proposed/ write.",
        "gate_verdicts_set": "none (G-AUDIT stays pending; review-of-review adjudication only)",
        "review_disposition": {"target": REVIEW017, "target_sha256": sha(REVIEW017),
                               "verdict": "accept", "score": 4.0,
                               "open_blocking": ["B17-CS-02/AUD-L08-01", "AUD-L08-02/N17-CS-04"],
                               "partially_resolved": ["B17-CS-01"]},
        "canonical_commands": {
            "classsep_regression": {"exit": 0, "result": "17/17 leaks, 10/10 controls, FP 0 FN 0, PASS",
                                    "output": REGRESSION, "sha256": sha(REGRESSION)},
            "audit_evidence": {"exit": 1, "result": "24 hard, 0 soft = 23 CLASSSEP + 1 frozen drift",
                               "output": AUDITOUT, "sha256": sha(AUDITOUT)},
        },
        "pins_measured": pins,
        "live_detector": {"path": "research_map/class_separation.py", "sha256": pins["research_map/class_separation.py"],
                          "declared_frozen_pin": "c266dbceca87", "operative": "a8c04fc31e4a",
                          "void": "e36b0d644ca7", "stable_all_round": True},
        "live_census_binding": {
            "l07_snapshot": {"path": "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json",
                             "sha256": sha("artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json"),
                             "claims": 383, "classsep_hard_a8c04fc3": 19},
            "l08_snapshot": {"path": MAPSNAP, "sha256": sha(MAPSNAP), "claims": 483,
                             "classsep_hard_a8c04fc3": 23},
            "live_map_at_close": {"sha256": pins["research_map/research_map.json"],
                                  "claims": len(mapdoc.get("claims", [])),
                                  "updated_at": mapdoc.get("updated_at")},
        },
        "next_falsifier": "a controller event naming the detector-of-record; re-run "
                          "artifacts/audit/classsep_l08_drift_repro.py at those bytes; the "
                          "frozen-drift HARD failure must disappear from audit_evidence.py; any "
                          "detector write while the round is open voids this record.",
    }
    (ROOT / "runtime/state/lead_audit_lifecycle_08_checkpoint.json").write_text(
        json.dumps(ckpt, indent=2) + "\n")
    with (ROOT / "runtime/state/lead_audit_checkpoints.jsonl").open("a") as f:
        f.write(json.dumps(ckpt, sort_keys=True) + "\n")

    print(f"events new={len(new)} skipped={len(events)-len(new)}")
    for e in new:
        print(f"  {e['event_type']:<16} {e['event_id']}")
    print("checkpoint -> runtime/state/lead_audit_lifecycle_08_checkpoint.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
