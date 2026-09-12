#!/usr/bin/env python3
"""W068-FORM-REV13-REMEASURE-14 event emitter + final checkpoint (worker-068).

Appends the task's upward events to comms/outbox/worker-068.jsonl and writes
checkpoint_final.json with the full artifact hash set and the emitted event-id list.
Worker events only: no gate verdict, no node status, no validation_status=passed.

Usage: python3 emit_events.py
Exit 0 emitted; 2 precondition failure.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms" / "outbox" / "worker-068.jsonl"
TASK = "W068-FORM-REV13-REMEASURE-14"
ACTOR = "worker-068"
NODE = "A1"
GATE = "G-CLASSBIND (folded into G-AUDIT as calibration evidence)"
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
GROUP = "formulation"
ARTIFACTS = [
    ("preregistration", "artifacts/worker-068/rev13remeasure14/PREREGISTRATION.json",
     "preregistration"),
    ("corpus_manifest", "artifacts/worker-068/rev13remeasure14/manifest.json", "manifest"),
    ("corpus_builder", "artifacts/worker-068/rev13remeasure14/build_rev13_corpus.py", "builder"),
    ("measurement_runner", "artifacts/worker-068/rev13remeasure14/run_rev13_remeasure.py", "runner"),
    ("raw_stage_verdicts", "artifacts/worker-068/rev13remeasure14/raw_verdicts.json", "raw"),
    ("measurement_report", "artifacts/worker-068/rev13remeasure14/report.json", "report"),
    ("readme", "artifacts/worker-068/rev13remeasure14/README.md", "readme"),
    ("worker_checkpoint", "artifacts/worker-068/rev13remeasure14/checkpoint.json", "checkpoint"),
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    missing = [rel for _, rel, _ in ARTIFACTS if not (ROOT / rel).exists()]
    if missing:
        print(json.dumps({"verdict": "PRECONDITION_FAILED", "missing": missing}, indent=1))
        return 2
    rep = json.loads((HERE / "report.json").read_text())
    ck = json.loads((HERE / "checkpoint.json").read_text())
    hashes = {rel: sha256_file(ROOT / rel) for _, rel, _ in ARTIFACTS}
    now = datetime.now(CST)
    t = lambda sec: (now + timedelta(seconds=sec)).isoformat(timespec="seconds")  # noqa: E731
    eid = lambda tag: f"w068-r14-{tag}-20260912T{now.strftime('%H%M%S')}"  # noqa: E731

    v = ck["verdict"]
    events = []
    events.append({
        "event_id": eid("01-status-task"), "event_type": "status", "created_at": t(0),
        "actor": ACTOR, "node_id": NODE, "class_ids": CLASSES, "gate": GATE, "group_id": GROUP,
        "task_id": TASK, "status": "active", "hours": 0.7,
        "summary": (
            "Took ONE bounded class-bound task (no inbox card): pre-registered re-measurement of "
            "the four mutation-isolated FORM-HELDOUT-08 definition-site escapes against the "
            "published rev13 / FROZEN-rev29 pins, with arm-informativeness and control checks. "
            "Read-only on canonical paths; worker evidence only."
        ),
        "evidence_refs": ["research_map/ASTRA_HANDOFF.md", "comms/PROTOCOL.md"],
        "next_falsifier": rep["falsifier"],
    })
    for i, (atype, rel, tag) in enumerate(ARTIFACTS, start=2):
        events.append({
            "event_id": eid(f"{i:02d}-artifact-{tag}"), "event_type": "artifact",
            "created_at": t(i), "actor": ACTOR, "node_id": NODE, "class_ids": CLASSES,
            "gate": GATE, "group_id": GROUP, "task_id": TASK, "artifact_type": atype,
            "path": rel, "sha256": hashes[rel], "validation_status": "unverified",
            "evidence_refs": [f"{rel}#{hashes[rel][:12]}"],
            "summary": f"{TASK} deliverable: {Path(rel).name}",
        })
    claim_id = eid("11-claim-rev13-escapes")
    events.append({
        "event_id": claim_id, "event_type": "claim", "created_at": t(11), "actor": ACTOR,
        "node_id": NODE, "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": CLASSES, "gate": GATE,
        "group_id": GROUP, "task_id": TASK, "conclusion_type": "formal_model",
        "statement": (
            "Artifact-and-checker measurement (not a mathematical claim, not a gate verdict): at "
            "the rev13 pin F1 d9cebb9404b2 / F2a e9a27996dfd3 / F2b b2ab6acb2bbe, FROZEN rev29 "
            "815e08079aefbc, stage A check_class_schema.py 000e09e46b2f + KEY_MANIFEST "
            "014e2d301978, stage B spec_conformance_audit.py c79d8ab8440a + rule_spec "
            "40f9bb9e657b, the C0 arm is informative (base and identity control accepted by both "
            "stages) and all THREE transplanted C0 definition-site mutations escape both stages: "
            "iso_m04 data_class.adm_mass.sign, iso_m16 "
            "implication_ledger.extension_class_containment, iso_m29 "
            "quantifiers.domains.D2.definition (each fixture differs from the rev13 base in "
            "exactly the declared leaf). The W arm is non-informative at rev13 because stage B "
            "rejects the untouched F1 rev13 base on R03 (binder '(q,t0)' absent from formal "
            "sentence, the recorded HF-071R3-01 instrument/wording mismatch); iso_m25 is "
            "untestable_by_protocol, not caught. All identity and formatting controls are "
            "accepted in the informative arms; secondary proposal-only R-CAND-D evaluation: "
            "freeze_contract_min and freeze_defsites_min flag 4/4 mutations and 0/6 controls, "
            "freeze_conclusion flags 0/4. Measured snapshot valid: no drift, no stage anomaly."
        ),
        "assumptions": [
            "The rev13 canonical bytes measured at snapshot time are the intended target; any "
            "later write to a pinned path voids the measurement at that path.",
            "The four mutation labels are worker-068 constructions; an independent adjudication "
            "of the W068-R14-F4 leaf witnesses is required before the escape counts are cited "
            "as detector false negatives.",
            "Stage A 'pass' and stage B 'accept' are the acceptance predicates of the two "
            "pinned class-binding instruments; neither decides mathematics.",
            "A class arm is informative only if its base and identity control are accepted by "
            "both stages.",
        ],
        "artifact_refs": [f"{rel}#{hashes[rel][:12]}" for _, rel, _ in ARTIFACTS
                          if rel.endswith(("report.json", "raw_verdicts.json",
                                           "PREREGISTRATION.json", "manifest.json"))],
        "evidence_refs": [
            f"schemas/af_scc_c0_vacuum.yaml#{rep['pins']['schemas']['C0'][:12]}",
            f"schemas/af_scc_c2_vacuum.yaml#{rep['pins']['schemas']['C2'][:12]}",
            f"schemas/af_wcc_vacuum.yaml#{rep['pins']['schemas']['W'][:12]}",
            f"artifacts/worker-068/rev13remeasure14/raw_verdicts.json#{hashes['artifacts/worker-068/rev13remeasure14/raw_verdicts.json'][:12]}",
            f"artifacts/worker-068/rev13remeasure14/report.json#{hashes['artifacts/worker-068/rev13remeasure14/report.json'][:12]}",
        ],
        "falsifier": rep["falsifier"],
        "next_falsifier": (
            "An independent adjudication that a W068-R14-F4 witness is a permissible rewording; "
            "a stage-B pass on the untouched F1 rev13 base (makes the W arm informative); or any "
            "pinned-hash change voids or corrects the affected row on re-run."
        ),
    })
    events.append({
        "event_id": eid("12-blocker-label-adjudication"), "event_type": "blocker",
        "created_at": t(12), "actor": ACTOR, "node_id": NODE, "class_ids": CLASSES,
        "gate": GATE, "group_id": GROUP, "task_id": TASK,
        "description": (
            "Two items block promotion of this calibration datapoint. (1) The escape corpus is "
            "author-built: worker-068 labelled m04/m16/m29 as class-contract violations; an "
            "independent reviewer must adjudicate the W068-R14-F4 witnesses before the 3/3 "
            "escape count is cited as a detector false negative. (2) The W/F1 arm cannot be "
            "measured by this protocol at rev13: stage B rejects the untouched F1 rev13 base on "
            "R03 (HF-071R3-01), so iso_m25 is untestable, not caught. The C0 escapes themselves "
            "are hash-bound at b2ab6acb2bbe and remain open under the pinned stages."
        ),
        "needed_to_unblock": (
            "Independent reviewer: adjudicate the four leaf witnesses in raw_verdicts.json "
            "(genuine violation vs permissible rewording) and record the corrected counts. "
            "Schema owner / audit lead: resolve R03 (HF-071R3-01) or declare the F1 "
            "definition-axis unmeasured at rev13. Controller: bind this measurement to G-AUDIT's "
            "class-binding calibration item at the cited detector hash."
        ),
        "evidence_refs": [
            f"artifacts/worker-068/rev13remeasure14/raw_verdicts.json#{hashes['artifacts/worker-068/rev13remeasure14/raw_verdicts.json'][:12]}",
            f"artifacts/worker-068/rev13remeasure14/report.json#{hashes['artifacts/worker-068/rev13remeasure14/report.json'][:12]}",
            f"schemas/af_wcc_vacuum.yaml#{rep['pins']['schemas']['W'][:12]}",
        ],
        "next_falsifier": (
            "An accepted independent adjudication or a stage-B F1 base pass closes the "
            "corresponding item; a pinned-hash change voids the measurement at that path."
        ),
    })
    events.append({
        "event_id": eid("13-status-complete"), "event_type": "status", "created_at": t(13),
        "actor": ACTOR, "node_id": NODE, "class_ids": CLASSES, "gate": GATE, "group_id": GROUP,
        "task_id": TASK, "status": "active", "hours": 0.7,
        "summary": (
            "W068-FORM-REV13-REMEASURE-14 complete at worker level: valid snapshot measurement, "
            "C0 arm informative with 3/3 transplanted definition-site escapes at rev13, W arm "
            "non-informative (R03 on the F1 base), controls accepted in informative arms, no "
            "drift. Primary artifact report.json; open items carried by the blocker above. No "
            "node completion, validation_status=passed or gate verdict is claimed."
        ),
        "evidence_refs": [
            f"artifacts/worker-068/rev13remeasure14/report.json#{hashes['artifacts/worker-068/rev13remeasure14/report.json'][:12]}",
            f"artifacts/worker-068/rev13remeasure14/checkpoint.json#{hashes['artifacts/worker-068/rev13remeasure14/checkpoint.json'][:12]}",
        ],
        "next_falsifier": rep["falsifier"],
    })

    with OUTBOX.open("a", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False, sort_keys=False) + "\n")

    final = {
        "schema": "worker-068/rev13remeasure14/checkpoint-final/v1",
        "task_id": TASK, "actor": ACTOR, "created_at": t(14),
        "status": "measurement_complete_events_emitted",
        "verdict": v,
        "artifact_sha256": hashes,
        "emitted_event_ids": [e["event_id"] for e in events],
        "claim_event_id": claim_id,
        "blocker_event_id": eid("12-blocker-label-adjudication"),
        "outbox": "comms/outbox/worker-068.jsonl",
        "falsifier": rep["falsifier"],
        "non_claims": rep["non_claims"],
    }
    (HERE / "checkpoint_final.json").write_text(json.dumps(final, indent=1) + "\n")
    confirm = {
        "event_id": eid("15-checkpoint-confirm"), "event_type": "status", "created_at": t(15),
        "actor": ACTOR, "node_id": NODE, "class_ids": CLASSES, "gate": GATE, "group_id": GROUP,
        "task_id": TASK, "status": "active",
        "summary": (
            "Post-checkpoint confirmation: worker-local final checkpoint written to "
            "artifacts/worker-068/rev13remeasure14/checkpoint_final.json with the full artifact "
            "hash set and the emitted event-id list; the 15-minute global cycle ingests these "
            "outbox events. Worker exits for recycling."
        ),
        "evidence_refs": [
            "artifacts/worker-068/rev13remeasure14/checkpoint_final.json",
        ],
    }
    with OUTBOX.open("a", encoding="utf-8") as f:
        f.write(json.dumps(confirm, ensure_ascii=False, sort_keys=False) + "\n")
    print(json.dumps({
        "verdict": "EVENTS_EMITTED", "events": len(events) + 1,
        "outbox": str(OUTBOX.relative_to(ROOT)),
        "checkpoint_final": "artifacts/worker-068/rev13remeasure14/checkpoint_final.json",
        "claim_event_id": claim_id,
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
