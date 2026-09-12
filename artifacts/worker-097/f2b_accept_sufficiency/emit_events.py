#!/usr/bin/env python3
"""Emit worker-097 events for W097-F2B-ACCEPT-SUFFICIENCY-01 and write the checkpoint.

Validates every event with research_map/schemas.py before appending to the outbox.
No controller ingest, no canonical write, no gate verdict, no node status promotion.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "research_map"))
import schemas  # noqa: E402

TASK_ID = "W097-F2B-ACCEPT-SUFFICIENCY-01"
_TZ = timezone(timedelta(hours=8))
_NOW = datetime.now(_TZ)
NOW = _NOW.strftime("%Y-%m-%dT%H:%M:%S+08:00")
STAMP = _NOW.strftime("%Y%m%dT%H%M%S")
OUTBOX = os.path.join(ROOT, "comms/outbox/worker-097.jsonl")
CHECKPOINT = os.path.join(ROOT, "runtime/state/w097_f2b_accept_sufficiency_checkpoint.json")

FILES = {
    "report.json": "artifacts/worker-097/f2b_accept_sufficiency/report.json",
    "check_accept_sufficiency.py": "artifacts/worker-097/f2b_accept_sufficiency/check_accept_sufficiency.py",
    "README.md": "artifacts/worker-097/f2b_accept_sufficiency/README.md",
    "PREREGISTRATION.md": "artifacts/worker-097/f2b_accept_sufficiency/PREREGISTRATION.md",
    "run_output.txt": "artifacts/worker-097/f2b_accept_sufficiency/run_output.txt",
    "SHA256SUMS.txt": "artifacts/worker-097/f2b_accept_sufficiency/SHA256SUMS.txt",
}

PINS = {
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(rel):
    return f"{rel}#sha256:{sha256(os.path.join(ROOT, rel))}"


def main():
    h = {name: sha256(os.path.join(ROOT, rel)) for name, rel in FILES.items()}
    pin_before = {rel: sha256(os.path.join(ROOT, rel)) for rel in PINS}
    pin_drift = {rel: {"expected": PINS[rel], "measured": pin_before[rel]}
                 for rel in PINS if pin_before[rel] != PINS[rel]}
    assert not pin_drift, f"pin drift before emit: {pin_drift}"

    report_ref = ref(FILES["report.json"])
    instr_ref = ref(FILES["check_accept_sufficiency.py"])
    readme_ref = ref(FILES["README.md"])
    c0_ref = f"schemas/af_scc_c0_vacuum.yaml#sha256:{PINS['schemas/af_scc_c0_vacuum.yaml']}"
    f2a_ref = f"schemas/af_scc_c2_vacuum.yaml#sha256:{PINS['schemas/af_scc_c2_vacuum.yaml']}"
    frozen_ref = f"artifacts/formulation/FROZEN.json#sha256:{PINS['artifacts/formulation/FROZEN.json']}"
    review_refs = [
        "reviews/F2b-review-rev13-worker-071.json",
        "reviews/F2b-review-worker-072-rev29.json",
        "reviews/F2b-rev13-full-090.json",
    ]
    ev = []

    ev.append({
        "event_id": f"w097-f2bacc-art-report-{STAMP}",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-097",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK_ID,
        "artifact_type": "evidence_sufficiency_audit",
        "path": FILES["report.json"],
        "sha256": h["report.json"],
        "validation_status": "unverified",
        "summary": ("Machine record: at F2b b2ab6acb2bbe both carriers (line 246 inverted containment premise, "
                    "line 152 stale containment denial) are INCONSISTENT from primary bytes and no accept at the "
                    "hash disposes of either; evidence_sufficiency=INSUFFICIENT, controls 6/6 pass."),
        "evidence_refs": [c0_ref, f2a_ref, frozen_ref],
        "next_falsifier": "An accept at b2ab6acb2bbe whose artifact or cited instrument disposes of line 246 or line 152, or bytes differing from b2ab6acb2bbe.",
    })
    ev.append({
        "event_id": f"w097-f2bacc-art-instrument-{STAMP}",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-097",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK_ID,
        "artifact_type": "audit_instrument",
        "path": FILES["check_accept_sufficiency.py"],
        "sha256": h["check_accept_sufficiency.py"],
        "validation_status": "unverified",
        "summary": ("Stdlib-only instrument: line-pinned derivation of HF-152/HF-246 and a coverage classifier over "
                    "each accept verdict plus its cited instruments; controls C1-C6."),
        "evidence_refs": [report_ref, readme_ref],
        "next_falsifier": "A control that fails on re-run, or a carrier classification that changes under the pinned hashes.",
    })
    ev.append({
        "event_id": f"w097-f2bacc-art-readme-{STAMP}",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-097",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK_ID,
        "artifact_type": "audit_summary",
        "path": FILES["README.md"],
        "sha256": h["README.md"],
        "validation_status": "unverified",
        "summary": "Human-readable audit summary with the coverage matrix, witnesses, controls and the sufficient-disposition requirement.",
        "evidence_refs": [report_ref, instr_ref],
        "next_falsifier": "A cited witness or line quote shown to misread the pinned bytes.",
    })
    ev.append({
        "event_id": f"w097-f2bacc-claim-{STAMP}",
        "event_type": "claim",
        "created_at": NOW,
        "actor": "worker-097",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK_ID,
        "conclusion_type": "stability_result",
        "statement": (
            "Record-audit result, not a mathematics verdict: at F2b schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe "
            "(FROZEN rev29 815e08079aefbc, all pins stable), the two carriers flagged by revise verdicts at the same "
            "hash are confirmed from primary bytes -- line 246 (implication_ledger.forbidden_transfers[0].reason) "
            "calls C2 a 'strictly larger extension class' while the artifact's own chain (line 239) and the F2a/supplement "
            "wording make E_C2 the innermost set (INCONSISTENT), and line 152 (regularity.must_not_conflate[0]) denies "
            "containment with C2 or C0 while lines 239/242 assert it (INCONSISTENT). Of the three accept verdicts at "
            "b2ab6acb2bbe, none disposes of either carrier: worker-071 excludes must_not_conflate from its scan by design, "
            "worker-072 excludes forbidden_transfers by regex, worker-090 checks only forbidden_transfers[*].from and never "
            "the reason text. On the record, the accept set does not discharge the live findings; evidence_sufficiency=INSUFFICIENT."
        ),
        "assumptions": [
            "The measured sha256 is the artifact identity; the audit is valid only at the pins listed in report.json.",
            "'Disposes' means the verdict artifact or a cited instrument cites the carrier line/field or its verbatim content and records a judgment; field presence alone is not a disposition.",
            "This is a worker record audit: only the controller/lead can adjudicate severity, the gate verdict, or node status.",
        ],
        "falsifier": ("An accept verdict recorded at b2ab6acb2bbe whose artifact or cited instrument contains a hash-bound "
                      "disposition of line 152 or line 246, or a byte-level re-derivation showing line 239 is not a containment "
                      "assertion, or bytes differing from b2ab6acb2bbe."),
        "evidence_refs": [report_ref, instr_ref, c0_ref, f2a_ref,
                          f"artifacts/formulation/formulation_taxonomy.yaml#sha256:{PINS['artifacts/formulation/formulation_taxonomy.yaml']}",
                          frozen_ref] + review_refs,
        "artifact_refs": [report_ref, instr_ref],
        "non_claims": [
            "no accept/revise/reject verdict on F2b",
            "no gate verdict, node status or validation_status promotion",
            "no canonical write",
        ],
    })
    ev.append({
        "event_id": f"w097-f2bacc-blocker-{STAMP}",
        "event_type": "blocker",
        "created_at": NOW,
        "actor": "worker-097",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK_ID,
        "description": (
            "G-FORM adjudication risk at F2b b2ab6acb2bbe: the two live self-contradictions (line 246 inverted containment "
            "premise, line 152 stale containment denial) are not addressed by any of the three accepts recorded at the same "
            "hash; two accept instruments exclude the carrier blocks by design/regex and the third never reads the contested "
            "reason text. Counting those accepts toward the 'two independent accepts' criterion without an explicit disposition "
            "would bind the gate to evidence that does not cover the contested fields."
        ),
        "needed_to_unblock": (
            "Either (a) the owner repairs both lines in a new revision and a fresh hash-bound review disposes of them, or "
            "(b) the lead-audit records, at b2ab6acb2bbe with cited sha256, why line 246's 'strictly larger' and line 152's "
            "denial are non-blocking despite the artifact's own containment assertions -- a full-schema accept that merely does "
            "not mention the carriers does not discharge them."
        ),
        "evidence_refs": [report_ref, instr_ref, c0_ref] + review_refs,
        "no_gate_verdict": True,
    })
    ev.append({
        "event_id": f"w097-f2bacc-status-{STAMP}",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-097",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK_ID,
        "status": "active",
        "hours": 0.35,
        "summary": (
            "CHECKPOINT + EXIT. One bounded class-bound task taken (no inbox card for worker-097): W097-F2B-ACCEPT-SUFFICIENCY-01, "
            "an evidence-sufficiency audit of the F2b rev13 accept verdicts. Result: both live carriers confirmed INCONSISTENT "
            "from primary bytes; accept coverage HF-152 {071:EXCLUDED-FROM-CHECK, 072:NONE, 090:NONE}, HF-246 {071:NONE, "
            "072:EXCLUDED-FROM-CHECK, 090:MENTION-ONLY}; evidence_sufficiency=INSUFFICIENT; controls 6/6. No F2b class verdict, "
            "no gate verdict, no node promotion, no canonical write."
        ),
        "evidence_refs": [report_ref, instr_ref, readme_ref, c0_ref],
        "next_falsifier": ("An accept at b2ab6acb2bbe that disposes of line 246 or line 152, or a byte-level re-derivation "
                           "showing line 239 is not a containment assertion."),
        "no_gate_verdict": True,
    })

    for e in ev:
        schemas.validate_event(e)

    existing = set()
    if os.path.isfile(OUTBOX):
        with open(OUTBOX, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    existing.add(json.loads(line).get("event_id"))
                except Exception:
                    continue
    new_events = [e for e in ev if e["event_id"] not in existing]
    lines = [json.dumps(e, sort_keys=True) for e in new_events]
    if lines:
        with open(OUTBOX, "a", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")

    pin_after = {rel: sha256(os.path.join(ROOT, rel)) for rel in PINS}
    drift = {rel: pin_after[rel] for rel in PINS if pin_after[rel] != PINS[rel]}

    checkpoint = {
        "schema": "worker-checkpoint/v1",
        "checkpoint_id": f"w097-f2bacc-{STAMP}",
        "task_id": TASK_ID,
        "worker": "worker-097",
        "actor": "worker-097",
        "created_at": NOW,
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "artifact_sha256": h,
        "emit_events_py_sha256": sha256(os.path.abspath(__file__)),
        "artifact_dir": "artifacts/worker-097/f2b_accept_sufficiency",
        "pins": PINS,
        "pin_drift_after_emit": drift,
        "controls_pass": True,
        "evidence_sufficiency": "INSUFFICIENT",
        "clause_verdicts": {"HF-246": "INCONSISTENT", "HF-152": "INCONSISTENT"},
        "accept_coverage": {"worker-071": {"HF-152": "EXCLUDED-FROM-CHECK", "HF-246": "NONE"},
                            "worker-072": {"HF-152": "NONE", "HF-246": "EXCLUDED-FROM-CHECK"},
                            "worker-090": {"HF-152": "NONE", "HF-246": "MENTION-ONLY"}},
        "events_emitted": [e["event_id"] for e in ev],
        "outbox": {"path": "comms/outbox/worker-097.jsonl", "lines": len(lines),
                   "sha256": sha256(OUTBOX)},
        "not_claimed": [
            "no F2b accept/revise/reject verdict",
            "no gate verdict, node status or validation_status promotion",
            "no canonical write; detector untouched",
            "no ingest (controller command)",
        ],
        "next_falsifier": "An accept at b2ab6acb2bbe that disposes of line 246 or line 152, or bytes differing from the pins.",
        "exit": "clean; all events validated by research_map/schemas.py before append; checkpoint written",
    }
    with open(CHECKPOINT, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=2, sort_keys=True)
        f.write("\n")

    print(json.dumps({"events": len(ev), "pin_drift_after_emit": drift,
                      "checkpoint": os.path.relpath(CHECKPOINT, ROOT),
                      "outbox_sha256": checkpoint["outbox"]["sha256"]}, indent=2))


if __name__ == "__main__":
    main()
