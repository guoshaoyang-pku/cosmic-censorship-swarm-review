#!/usr/bin/env python3
"""Emit worker-066's W066-F2B-REPAIR-PREREG-01 outbox events and the runtime checkpoint.

Validates every event with research_map.schemas.validate_event before appending to
comms/outbox/worker-066.jsonl. Writes runtime/state/w066_f2b_repair_prereg_checkpoint.json
first, so the checkpoint hash can be cited by the closing status event.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
TASK = "W066-F2B-REPAIR-PREREG-01"
CLASSES = ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"]
OUTBOX = ROOT / "comms" / "outbox" / "worker-066.jsonl"
CKPT = ROOT / "runtime" / "state" / "w066_f2b_repair_prereg_checkpoint.json"

FALSIFIER = ("re-run prereg.py on the same pins: falsified if live 55d0a1ea does not yield "
             "exactly the two defect kinds, or the reference candidate 98f9ec83 produces any "
             "finding, or any of the 10 controls departs from its pre-registered expectation, "
             "or a third instance of the two defect kinds appears in C2/F1 at their pins, or "
             "re-applying the two edits to live does not reproduce 98f9ec83, or any pinned "
             "byte moves mid-run")
NEEDED = ("lead-formulation (owner): apply proposed_patch.diff or an equivalent 2-edit repair "
          "(implication_ledger.forbidden_transfers[0].reason -> 'strictly smaller extension "
          "class (E_C2 subset of E_C0)'; regularity.must_not_conflate[0] -> nesting statement "
          "with the earlier denial recorded wrong), bump revision, mirror byte-identically, "
          "re-freeze; then re-run artifacts/worker-066/f2b_repair_prereg/prereg.py and require "
          "live PASS with C2 5476a3f2 unchanged")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def main() -> int:
    art = {
        "prereg_py": "artifacts/worker-066/f2b_repair_prereg/prereg.py",
        "patch": "artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff",
        "readme": "artifacts/worker-066/f2b_repair_prereg/README.md",
        "report": "artifacts/worker-066/f2b_repair_prereg/report.json",
        "checks": "artifacts/worker-066/f2b_repair_prereg/evidence/checks.json",
        "controls": "artifacts/worker-066/f2b_repair_prereg/evidence/controls.json",
        "siblings": "artifacts/worker-066/f2b_repair_prereg/evidence/sibling_scan.json",
        "pins": "artifacts/worker-066/f2b_repair_prereg/evidence/pins.json",
        "harness_checkpoint": "artifacts/worker-066/f2b_repair_prereg/CHECKPOINT.json",
    }
    hashes = {k: sha(v) for k, v in art.items()}
    report = json.loads((ROOT / art["report"]).read_text())

    ckpt = {
        "checkpoint_id": f"w066-f2b-repair-prereg-{datetime.now(CST).strftime('%Y%m%dT%H%M%S')}",
        "task_id": TASK,
        "label": "worker-066-f2b-repair-prereg",
        "generated_at": now(),
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "verdict": report["verdict"],
        "live_pin": {"path": "schemas/af_scc_c0_vacuum.yaml",
                     "sha256": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
                     "finding_kinds": report["live_target"]["finding_kinds"]},
        "reference_candidate": {"sha256": report["reference_candidate"]["sha256"],
                                "finding_kinds": report["reference_candidate"]["finding_kinds"]},
        "siblings": report["siblings"],
        "controls_all_matched": report["controls"]["all_matched"],
        "artifacts": {**{k: {"path": v, "sha256": hashes[k]} for k, v in art.items()},
                      "runtime_checkpoint_self": "written by this script"},
        "next_falsifier": FALSIFIER,
        "boundaries": ["no canonical artifact edited", "no node status or gate moved",
                       "worker lifecycle only"],
    }
    CKPT.parent.mkdir(parents=True, exist_ok=True)
    CKPT.write_text(json.dumps(ckpt, indent=2) + "\n")
    ckpt_hash = hashlib.sha256(CKPT.read_bytes()).hexdigest()
    ts = now()

    def ev(eid, etype, **kw):
        e = {"event_id": eid, "event_type": etype, "created_at": ts, "actor": "worker-066",
             "task_id": TASK, "node_id": "F2b", "class_ids": CLASSES, **kw}
        validate_event(e)
        return e

    events = []
    events.append(ev(
        "w066-f2b-repairprereg-01-status-task", "status", class_id="AF-SCC-C0-VAC-GEN",
        status="active", hours=0.2,
        summary=("No assignment card exists in comms/inbox for worker-066. Taking ONE bounded "
                 "class-bound task: pre-registered, hash-bound repair-acceptance harness for the "
                 "open F2b containment defect at rev12 55d0a1ea (class AF-SCC-C0-VAC-GEN): exact "
                 "2-edit proposal patch + fresh checker + 10 controls, plus a family sweep of the "
                 "two defect kinds in C2/F1. Worker authority only; no canonical write, no gate."),
        evidence_refs=[f"{art['pins']}#{hashes['pins'][:12]}",
                       f"schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda"],
        next_falsifier=FALSIFIER))
    for key, note, atype in [
        ("prereg_py", "fresh order-relative checker + controls + patch generator", "code"),
        ("patch", "exact 2-edit proposal against live 55d0a1ea (proposal only)", "repair_proposal"),
        ("readme", "method, results, controls, limits, falsifier", "readme"),
        ("report", "verdict prereg_ready_live_FAILS_candidate_PASSES + acceptance booleans", "verdict"),
        ("checks", "primary runs on live/candidate + acceptance", "evidence"),
        ("controls", "10 pre-registered controls, expected vs observed, all matched", "evidence"),
        ("siblings", "C2/F1 size-premise and denial sweeps at their pins", "evidence"),
        ("pins", "pin measurements: bytes, mtime, match", "manifest"),
        ("harness_checkpoint", "artifact hash registry + next falsifier", "checkpoint"),
    ]:
        events.append(ev(f"w066-f2b-repairprereg-01-artifact-{key.replace('_', '-')}",
                         "artifact", class_id="AF-SCC-C0-VAC-GEN", artifact_type=atype,
                         path=art[key], sha256=hashes[key], validation_status="unverified",
                         note=note))
    events.append(ev(
        "w066-f2b-repairprereg-01-review", "review", reviewer="worker-066",
        target_id=("schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda96b80235294cf67079904e066c6d0fef"
                   "28e14bd2eef38f8945e6#repair-acceptance"),
        reviewed_sha256="55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
        verdict="revise", score=2.5, counts_as_full_schema_verdict=False,
        instrument="W066-F2B-REPAIR-PREREG-01 (repair-acceptance re-issue)",
        supersedes_review="w066-f2b-r12-01-review-c0 (same hash, same findings; instrument re-issued)",
        hard_failures=["W066-R12-F2B-H1", "W066-R12-F2B-H2"],
        findings=[
            "W066-R12-F2B-H1 [hard, live at 55d0a1ea] implication_ledger.forbidden_transfers[0].reason says C2 is a strictly larger extension class; the file's own chain (E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2) makes E_C2 the smallest set. The conclusion (transfer forbidden) is correct; the premise token is inverted. Reproduced by a fresh checker (run C1).",
            "W066-R12-F2B-H2 [hard, live at 55d0a1ea] regularity.must_not_conflate[0] carries the live denial 'No containment with C2 or C0 is asserted here' while :238/:240-241/:245 assert that containment. Fresh checker run C1; the sibling C2 rev12 has the corrected wording and withdraws the denial.",
            "Repair acceptance (new): the two-edit proposal (proposed_patch.diff) applied to live 55d0a1ea reproduces the reference candidate 98f9ec83 byte-exactly; that candidate yields zero findings; reverting either single edit fires exactly its own kind; 10/10 pre-registered controls matched.",
            "Family sweep (new): C2 5476a3f2 and F1 cce9c601 carry neither defect kind at their pins; C2's forbidden-transfer reasons ('the converse containment is false') are consistent with its declared chain.",
            "Not a full-schema verdict: class leakage/quantifier coverage remains the in-flight blind rev27 reviews' scope.",
        ],
        evidence_refs=[f"{art['checks']}#{hashes['checks'][:12]}",
                       f"{art['controls']}#{hashes['controls'][:12]}",
                       f"{art['siblings']}#{hashes['siblings'][:12]}",
                       f"{art['report']}#{hashes['report'][:12]}",
                       "schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda"]))
    events.append(ev(
        "w066-f2b-repairprereg-01-claim", "claim", class_id="AF-SCC-C0-VAC-GEN",
        conclusion_type="formal_model",
        statement=("At FROZEN rev27/28 pin schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda (rev12), a "
                   "freshly written checker independently reproduces exactly two text-level "
                   "containment defects (H1 inverted size premise at implication_ledger."
                   "forbidden_transfers[0].reason; H2 live containment denial at regularity."
                   "must_not_conflate[0]); the two-edit proposal in proposed_patch.diff, applied "
                   "to the live bytes, reproduces the reference candidate 98f9ec83 byte-exactly, "
                   "which yields zero findings and clears both defects; the sibling schemas C2 "
                   "5476a3f2 and F1 cce9c601 carry neither defect kind at their pins; 10/10 "
                   "pre-registered controls matched, including single-edit reverts and a reversed-"
                   "chain mutant. This is a text-consistency and binding result, not a claim about "
                   "the mathematics of C0 inextendibility."),
        assumptions=["a verdict binds bytes, not paths; all runs used pinned byte copies",
                     "the file's own extension_class_containment clause is the reference order",
                     "'extension class' means the extension set E_X as the document defines it",
                     "bracketed/quoted denials explicitly marked wrong are withdrawn, not live"],
        falsifier=FALSIFIER,
        evidence_refs=[f"{art['checks']}#{hashes['checks'][:12]}",
                       f"{art['controls']}#{hashes['controls'][:12]}",
                       f"{art['siblings']}#{hashes['siblings'][:12]}",
                       f"{art['pins']}#{hashes['pins'][:12]}",
                       "schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda",
                       "schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc"],
        artifact_refs=[f"{art['report']}#{hashes['report'][:12]}",
                       f"{art['patch']}#{hashes['patch'][:12]}",
                       f"{art['readme']}#{hashes['readme'][:12]}"]))
    events.append(ev(
        "w066-f2b-repairprereg-01-blocker", "blocker", class_id="AF-SCC-C0-VAC-GEN",
        description=("F2b at 55d0a1ea still fails repair acceptance: both containment defects are "
                     "live, and the repair has not been published. A ready-to-apply 2-edit "
                     "proposal and a re-runnable acceptance harness now exist; worker-066 cannot "
                     "write canonical paths, so the blocker persists until the owner acts."),
        needed_to_unblock=NEEDED,
        stop_rule=("repair published + revision bumped + mirror/re-freeze, then "
                   "prereg.py run yields live PASS (zero findings, C2 unchanged, controls matched)"),
        evidence_refs=[f"{art['report']}#{hashes['report'][:12]}",
                       f"{art['patch']}#{hashes['patch'][:12]}",
                       f"{art['controls']}#{hashes['controls'][:12]}",
                       "schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda"]))
    events.append(ev(
        "w066-f2b-repairprereg-01-status-complete", "status", class_id="AF-SCC-C0-VAC-GEN",
        status="active", hours=0.6,
        summary=("W066-F2B-REPAIR-PREREG-01 complete as a bounded worker lifecycle: live rev12 "
                 "fails with exactly H1+H2, reference candidate 98f9ec83 clean, siblings C2/F1 "
                 "clean, 10/10 controls matched, patch re-applies to the candidate hash exactly. "
                 "All artifacts exist and are hash-pinned; events schema-validated. This is a "
                 "completion claim, not a node/gate transition. Checkpoint follows."),
        evidence_refs=[f"{art['report']}#{hashes['report'][:12]}",
                       f"{art['controls']}#{hashes['controls'][:12]}",
                       f"schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda"],
        next_falsifier=FALSIFIER))
    events.append(ev(
        "w066-f2b-repairprereg-01-status-checkpoint", "status", class_id="AF-SCC-C0-VAC-GEN",
        status="active", hours=0.65,
        summary=("Checkpoint written to runtime/state/w066_f2b_repair_prereg_checkpoint.json "
                 f"({ckpt['checkpoint_id']}); pins re-measured unchanged after the run "
                 "(C0 55d0a1ea, C2 5476a3f2, F1 cce9c601, candidate 98f9ec83); live pin drift "
                 "none. worker-066 lifecycle complete; this event lands in the next ingest cycle."),
        evidence_refs=[f"runtime/state/w066_f2b_repair_prereg_checkpoint.json#{ckpt_hash[:12]}",
                       f"{art['pins']}#{hashes['pins'][:12]}",
                       f"{art['harness_checkpoint']}#{hashes['harness_checkpoint'][:12]}"],
        next_falsifier=FALSIFIER))

    with OUTBOX.open("a") as fh:
        for e in events:
            fh.write(json.dumps(e, sort_keys=True) + "\n")
    print(json.dumps({"checkpoint": str(CKPT), "checkpoint_sha256": ckpt_hash,
                      "events_appended": len(events), "outbox": str(OUTBOX),
                      "event_ids": [e["event_id"] for e in events]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
