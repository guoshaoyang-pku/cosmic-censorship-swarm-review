#!/usr/bin/env python3
"""Emit astra-lead-audit lifecycle-06 events and write the lifecycle checkpoint.

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


def sha(rel: str) -> str:
    p = ROOT / rel
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "ABSENT"


ARTIFACTS = {
    "evaluation/A0_detector_scope_adjudication.json": ("A0", "a0_detector_scope_adjudication"),
    "reviews/G-NUM-protocol-r4-adjudication.json": ("N0", "gnum_protocol_r4_adjudication"),
    "reviews/CLASSSEP-calibration-adjudication.json": ("A1", "classsep_calibration_adjudication"),
}
TOOLS = {
    "artifacts/audit/a0_detector_scope.py": "A0",
    "artifacts/audit/gnum_r4_adjudication.py": "N0",
    "artifacts/audit/classsep_calibration.py": "A1",
}


def load_a0() -> dict:
    return json.loads((ROOT / "evaluation/A0_detector_scope_adjudication.json").read_text())


def load_gnum() -> dict:
    return json.loads((ROOT / "reviews/G-NUM-protocol-r4-adjudication.json").read_text())


def load_cs() -> dict:
    return json.loads((ROOT / "reviews/CLASSSEP-calibration-adjudication.json").read_text())


def build_events() -> list[dict]:
    a0, gn, cs = load_a0(), load_gnum(), load_cs()
    ev: list[dict] = []

    def add(e):
        e.setdefault("actor", "astra-lead-audit")
        e.setdefault("created_at", NOW)
        ev.append(e)

    # --- artifacts ---
    for rel, (node, atype) in ARTIFACTS.items():
        add({"event_id": f"audit-l06-art-{atype}-{STAMP}", "event_type": "artifact",
             "node_id": node, "artifact_type": atype, "path": rel, "sha256": sha(rel),
             "validation_status": "unverified",
             "evidence_refs": [f"{rel}#{sha(rel)[:12]}"],
             "note": "audit-group adjudication artifact; validation_status stays unverified "
                     "until the controller or a second independent reviewer accepts it"})
    for rel, node in TOOLS.items():
        add({"event_id": f"audit-l06-tool-{Path(rel).stem}-{STAMP}", "event_type": "artifact",
             "node_id": node, "artifact_type": "calibration_tool", "path": rel,
             "sha256": sha(rel), "validation_status": "unverified",
             "evidence_refs": [f"{rel}#{sha(rel)[:12]}"],
             "note": "re-runnable measurement tool behind the adjudication"})

    # --- reviews ---
    add({"event_id": f"audit-l06-review-a0-scope-{STAMP}", "event_type": "review",
         "target_id": "A0/detector-scope", "reviewer": "astra-lead-audit",
         "verdict": "accept" if a0["falsifier_verdict"] == "pass" else "revise",
         "score": 4.5 if a0["falsifier_verdict"] == "pass" else 3.0,
         "hard_failures": [],
         "findings": [
             f"split ruling: HF-14 {a0['adjudication']['rulings']['HF-14']['before']['records']} "
             f"records -> {a0['adjudication']['rulings']['HF-14']['after_scope']['records']} "
             f"after scope (detector-scope artifact); HF-03 "
             f"{a0['adjudication']['rulings']['HF-03']['before']['records']} -> "
             f"{a0['adjudication']['rulings']['HF-03']['after_scope']['records']} records and "
             f"REMAINS a live finding on build inputs",
             "falsifier checks I1-I5 all pass; exclusion list contains no canonical ledger and "
             "no live build input; staging contributions surfaced not excluded",
         ],
         "artifact_refs": ["evaluation/A0_detector_scope_adjudication.json"],
         "evidence_refs": [f"evaluation/A0_detector_scope_adjudication.json#{sha('evaluation/A0_detector_scope_adjudication.json')[:12]}"],
         "counts_as_full_schema_verdict": True,
         "counts_as_independent_second_verdict": False,
         "note": "scope ruling only; the A0 node verdict at rubric d748a9e3574e is unchanged and "
                 "still revise"})

    add({"event_id": f"audit-l06-review-gnum-r4-{STAMP}", "event_type": "review",
         "target_id": "G-NUM-protocol", "reviewer": "astra-lead-audit",
         "verdict": gn["verdict"], "score": gn["score"], "hard_failures": [],
         "findings": [
             "operative protocol verdict at 1e6cdf04d7a2: the standing accept 4.5 is operative; "
             "worker-067 F1 and worker-081 F1' are discharged by supersession of the evidence basis",
             "24/24 independent checks pass: all 12 certification rows dt=1e-4, four rungs, "
             "recomputed LSQ orders reproduce to <=1e-9 relative, R5 delta rule holds, three "
             "schemes agree inside the 0.25 floor",
             "mechanical caveat: numerics/gates.py::_protocol_review still reports contest=true; "
             "needs a controller disposition or guard supersession rule",
         ],
         "artifact_refs": ["reviews/G-NUM-protocol-r4-adjudication.json"],
         "evidence_refs": [f"reviews/G-NUM-protocol-r4-adjudication.json#{sha('reviews/G-NUM-protocol-r4-adjudication.json')[:12]}",
                           "numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c",
                           "numerics/tests/n0_gate_proposal.json#b4192221ff7d"],
         "counts_as_full_schema_verdict": True,
         "counts_as_independent_second_verdict": False,
         "no_gate_verdict": True})

    add({"event_id": f"audit-l06-review-classsep-{STAMP}", "event_type": "review",
         "target_id": "A1/classsep-calibration", "reviewer": "astra-lead-audit",
         "verdict": "revise", "score": 3.0,
         "hard_failures": [
             "the staged candidate proposed/class_separation.py#e2d24b927ee8 is REJECTED: live "
             "hard findings rise 17->22 and labeled specificity falls 3/10->1/10 because it "
             "deletes the canonical quotation exemption",
             "the canonical detector itself is miscalibrated on prose: 17 hard findings on the "
             "live map, 0 TP / 17 FP, all metalinguistic",
         ],
         "findings": [
             "census: 27-fixture corpus PASS 17/0/10/0 for CANON, CAND and the PROSE arm; the "
             "corpus cannot discriminate the revisions",
             "live: CANON 17 FP / CAND 22 FP / PROSE 6 FP; PROSE (formulation proposal direction, "
             "sentence-scoped skips) clears 8 of 12 claims with 0 added",
             "labeled assertion-vs-mention set (16 fixtures): CANON 4/6 sens 3/10 spec, CAND 5/6 "
             "sens 1/10 spec, PROSE 4/6 sens 5/10 spec",
             "converse scan: 3 assertion-cue matches over all live claims, 0 unflagged genuine "
             "merges -> no measured false negative on the live map",
             "detector fix and claim rewrite are separated; no claim text is edited by this audit",
         ],
         "artifact_refs": ["reviews/CLASSSEP-calibration-adjudication.json"],
         "evidence_refs": [f"reviews/CLASSSEP-calibration-adjudication.json#{sha('reviews/CLASSSEP-calibration-adjudication.json')[:12]}",
                           "proposed/class_separation.py#e2d24b927ee8",
                           "research_map/class_separation.py#" + sha("research_map/class_separation.py")[:12]],
         "counts_as_full_schema_verdict": False,
         "counts_as_independent_second_verdict": False,
         "no_gate_verdict": True})

    # --- statuses ---
    add({"event_id": f"audit-l06-status-a0-{STAMP}", "event_type": "status", "node_id": "A0",
         "status": "active", "hours": 0.5,
         "summary": "A0 detector-scope blocker resolved as a SPLIT: HF-14 is a scope artifact "
                    "(586->0 records), HF-03 is a REAL live finding (218->194 records on the 11 "
                    "live sources batches + registry.jsonl). Scope predicate and before/after "
                    "lists are delivered for controller adoption; the checker is not edited by "
                    "audit (no gate self-pass). A0 node verdict remains revise 3.5 at "
                    "evaluation_rubric.yaml#d748a9e3574e.",
         "evidence_refs": [f"evaluation/A0_detector_scope_adjudication.json#{sha('evaluation/A0_detector_scope_adjudication.json')[:12]}"],
         "next_falsifier": "adopt the predicate and re-measure; if any live artifact hit vanishes "
                           "without a literature-side repair, the scope change hid a finding"})
    add({"event_id": f"audit-l06-status-n0-{STAMP}", "event_type": "status", "node_id": "N0",
         "status": "active", "hours": 1.0,
         "summary": "G-NUM C8 protocol contest adjudicated: standing accept 4.5 at protocol "
                    "1e6cdf04d7a2 is operative; F1 and F1' discharged by supersession of the "
                    "evidence basis onto the fixed-dt certification. No gate verdict set; N0 "
                    "node status explicitly not adjudicated here; numerics_lock untouched.",
         "evidence_refs": [f"reviews/G-NUM-protocol-r4-adjudication.json#{sha('reviews/G-NUM-protocol-r4-adjudication.json')[:12]}"],
         "next_falsifier": "any certification row with dt != 1e-4, or a re-measured order leaving "
                           "2.0 +/- 0.3, voids the discharge"})
    add({"event_id": f"audit-l06-status-a1-{STAMP}", "event_type": "status", "node_id": "A1",
         "status": "active", "hours": 1.5,
         "summary": "CLASSSEP calibration adjudicated with a three-arm measured census. Candidate "
                    "REJECTED (17->22 live FP); prose-precision direction ADOPT-AS-DIRECTION only "
                    "(17->6 live FP, still 6 residual). Retirement policy P1-P6 delivered: retire "
                    "the classification, never the record; raw and calibrated counts both published.",
         "evidence_refs": [f"reviews/CLASSSEP-calibration-adjudication.json#{sha('reviews/CLASSSEP-calibration-adjudication.json')[:12]}"],
         "next_falsifier": "an adopted revision that drops labeled sensitivity below the "
                           "canonical arm's 4/6, or a genuine merge assertion found among the 12 "
                           "flagged claims"})

    # --- blockers ---
    add({"event_id": f"audit-l06-b1-classsep-detector-{STAMP}", "event_type": "blocker",
         "node_id": "A1",
         "description": "The canonical class-separation detector is miscalibrated on prose: 17 "
                        "hard findings on the live map are 0 TP / 17 FP, all metalinguistic "
                        "(CASE_LABEL 4, NEGATION/NON_MERGE 7, QUOTATION/DETECTOR_SELF 4, "
                        "WINDOW_ARTIFACT 1, DETECTOR_DESCRIPTION 1). The staged candidate makes "
                        "it worse (22 FP). No adoptable revision exists yet.",
         "needed_to_unblock": "controller-owned revision of research_map/class_separation.py along "
                              "the PROSE direction closing R-a (composite-spanning negation), R-b "
                              "(clause not character window), R-c (_META coverage) and the A6 "
                              "quoted-negated-split guard; audit re-measures against the 27-fixture "
                              "corpus, the 16-fixture assertion/mention set and the live census",
         "evidence_refs": [f"reviews/CLASSSEP-calibration-adjudication.json#{sha('reviews/CLASSSEP-calibration-adjudication.json')[:12]}"]})
    add({"event_id": f"audit-l06-b2-hf03-live-{STAMP}", "event_type": "blocker",
         "node_id": "L0",
         "description": "HF-03 survives the A0 scope correction as a REAL finding: 194 citation "
                        "rows across the 11 declared live build inputs "
                        "artifacts/literature/sources/batch-*.jsonl plus the emitted "
                        "artifacts/literature/registry.jsonl lack class-scope metadata "
                        "(matter_model/cosmological_constant/dimension/symmetry/formulation). "
                        "Scoping them out would hide a genuine hard failure.",
         "needed_to_unblock": "literature lead populates source_meta scope keys on the 11 live "
                              "source batches and rebuilds registry.jsonl; re-measure with "
                              "artifacts/audit/a0_detector_scope.py",
         "evidence_refs": [f"evaluation/A0_detector_scope_adjudication.json#{sha('evaluation/A0_detector_scope_adjudication.json')[:12]}"]})
    add({"event_id": f"audit-l06-b3-staging-{STAMP}", "event_type": "blocker",
         "node_id": "L0",
         "description": "Two un-ingested staging contributions carry 12 HF-14 records and 1 HF-03 "
                        "record: artifacts/worker-07/ledger_contribution/batches/"
                        "batch-w07-theorems.jsonl and batch-w07-sources.jsonl. They are neither "
                        "canonical nor historical and must not be silently excluded.",
         "needed_to_unblock": "literature lead ingests or formally discards the worker-07 staging "
                              "batch, then re-measures",
         "evidence_refs": [f"evaluation/A0_detector_scope_adjudication.json#{sha('evaluation/A0_detector_scope_adjudication.json')[:12]}"]})
    add({"event_id": f"audit-l06-b4-gnum-guard-{STAMP}", "event_type": "blocker",
         "node_id": "N0",
         "description": "numerics/gates.py::_protocol_review still reports contest=true at "
                        "protocol 1e6cdf04d7a2 because a later accept does not rescind an earlier "
                        "revise and the guard still counts worker-081's self-withdrawn accept. "
                        "C8's substance is complete but the guard is not green.",
         "needed_to_unblock": "controller disposition recording the two dissents as discharged, or "
                              "a guard supersession rule (a later accept at the same hash "
                              "supersedes an earlier revise when the revise's subject is the "
                              "evidence basis and the evidence has been replaced)",
         "evidence_refs": [f"reviews/G-NUM-protocol-r4-adjudication.json#{sha('reviews/G-NUM-protocol-r4-adjudication.json')[:12]}",
                           "numerics/gates.py#" + sha("numerics/gates.py")[:12]]})
    add({"event_id": f"audit-l06-b5-map-moving-{STAMP}", "event_type": "blocker",
         "node_id": "A1",
         "description": "The map moved under this lifecycle from 292 to 320 claims while the "
                        "CLASSSEP census was being measured, so the claim-index labels and the "
                        "measured count bind only the recorded map sha256 "
                        "262da69798578d77. Verdicts at a moved pin are void on arrival.",
         "needed_to_unblock": "writers quiesce, FROZEN-style pin published, then the census is "
                              "re-measured; the tool is deterministic and re-runnable",
         "evidence_refs": [f"reviews/CLASSSEP-calibration-adjudication.json#{sha('reviews/CLASSSEP-calibration-adjudication.json')[:12]}"]})

    # --- direction update ---
    add({"event_id": f"audit-l06-direction-calibrated-counts-{STAMP}",
         "event_type": "direction_update", "group_id": "audit",
         "old_direction": "report the canonical detector's raw hard-failure count as the gate "
                          "input and track each new metalinguistic claim as a new hard failure",
         "new_direction": "publish two counts every tick -- classsep_hard_raw (canonical detector, "
                          "unmodified) and classsep_hard_calibrated (adopted detector) -- and "
                          "admit a claim to the retired list only by an adopted detector that "
                          "holds sensitivity >=5/6 and specificity >=9/10 on the labeled "
                          "assertion-vs-mention set with the 27-fixture corpus still PASS "
                          "17/0/10/0. G-AUDIT's hard_failure_rate uses the calibrated count with "
                          "the per-finding retirement ledger attached; a raw count with no "
                          "adopted calibration may not fail a gate.",
         "reason": "measured this lifecycle: the raw CLASSSEP count is monotone in verification "
                   "traffic, not in class leakage (10 -> 17 -> 22 across three detector revisions "
                   "at a fixed genesis defect), and every one of the 17 is a metalinguistic "
                   "mention. A count that grows when reviewers document the finding is not a "
                   "quality signal.",
         "evidence_refs": [f"reviews/CLASSSEP-calibration-adjudication.json#{sha('reviews/CLASSSEP-calibration-adjudication.json')[:12]}"],
         "budget_delta_agent_hours": 0.0,
         "next_falsifier": "a first-order C0/C2 merge assertion found on the live map, or a "
                           "calibrated count that falls while a genuine merge is present"})
    return ev


def main() -> int:
    events = build_events()
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
        "checkpoint": "lead-audit-lifecycle-06",
        "at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "actor": "astra-lead-audit",
        "node_ids": ["A0", "A1", "N0"],
        "gate": "G-AUDIT",
        "assignments_consumed": ["astra-life05-a0-detector-scope",
                                 "astra-life05-gnum-protocol-adjudication",
                                 "astra-life05-classsep-calibration"],
        "artifacts_written": {rel: sha(rel) for rel in ARTIFACTS},
        "tools_written": {rel: sha(rel) for rel in TOOLS},
        "events_emitted": [e["event_id"] for e in new],
        "events_skipped_idempotent": [e["event_id"] for e in events if e["event_id"] in existing],
        "blockers": [e["event_id"] for e in new if e["event_type"] == "blocker"],
        "gate_verdicts_set": "none (evidence + adjudication only; G-AUDIT stays pending)",
        "pins_measured": {
            "research_map/class_separation.py": sha("research_map/class_separation.py"),
            "proposed/class_separation.py": sha("proposed/class_separation.py"),
            "evaluation_rubric.yaml": sha("evaluation_rubric.yaml"),
            "numerics/CONVERGENCE_PROTOCOL.md": sha("numerics/CONVERGENCE_PROTOCOL.md"),
            "numerics/gates.py": sha("numerics/gates.py"),
            "ledger/theorems.jsonl": sha("ledger/theorems.jsonl"),
            "bench/classsep map snapshot": "262da69798578d7741e1d66dec3ed977d05c4bef296974c36063cb255bee628c",
        },
        "next_falsifier": "re-measure every pin next lifecycle; any move voids the at-pin "
                          "verdicts. The map moved 292->320 claims during this lifecycle, so the "
                          "CLASSSEP census must be re-run before it is cited.",
    }
    (ROOT / "runtime/state/lead_audit_lifecycle_06_checkpoint.json").write_text(
        json.dumps(ckpt, indent=2) + "\n")
    with (ROOT / "runtime/state/lead_audit_checkpoints.jsonl").open("a") as f:
        f.write(json.dumps(ckpt, sort_keys=True) + "\n")

    print(f"events new={len(new)} skipped={len(events)-len(new)} -> {OUTBOX.relative_to(ROOT)}")
    for e in new:
        print(f"  {e['event_type']:<16} {e['event_id']}")
    print("checkpoint -> runtime/state/lead_audit_lifecycle_06_checkpoint.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
