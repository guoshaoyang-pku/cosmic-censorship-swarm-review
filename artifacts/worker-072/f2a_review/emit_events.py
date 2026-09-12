#!/usr/bin/env python3
"""Append W072-F2A-REVIEW-01 events to comms/outbox/worker-072.jsonl and write the checkpoint.

Every event is validated with research_map/schemas.py before it is appended.
Authority: worker evidence only — no node done, no validation_status passed, no gate verdict.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "research_map"))
import schemas  # noqa: E402

ART = "artifacts/worker-072/f2a_review"
SCHEMA = "schemas/af_scc_c2_vacuum.yaml"
TAX = "research_map/formulation_taxonomy.yaml"
SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
EVID = "artifacts/formulation/evidence/taxonomy_consistency.json"
OUTBOX = "comms/outbox/worker-072.jsonl"
CKPT = "runtime/state/w072_f2a_review_checkpoint_1.json"
CKPT_LOG = "runtime/state/w072_f2a_review_checkpoints.jsonl"
TASK = "W072-F2A-REVIEW-01"
CLASSES = ["AF-SCC-C2-VAC-GEN"]


def now() -> str:
    return datetime.now(CST).replace(microsecond=0).isoformat()


def sh(rel: str) -> str:
    h = hashlib.sha256()
    with open(os.path.join(ROOT, rel), "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def ref(rel: str, n: int = 12) -> str:
    return f"{rel}#{sh(rel)[:n]}"


def main() -> int:
    ts = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    report = json.load(open(os.path.join(ROOT, ART, "report.json")))
    counts = report["summary"]
    ctrl = report["controls_run"]["summary"]
    schema_sha = sh(SCHEMA)
    report_sha = sh(f"{ART}/report.json")
    instr_sha = sh(f"{ART}/check_f2a.py")
    review_path = "reviews/F2a-review-worker-072-rev13.json"
    review_sha = sh(review_path)
    man_sha = sh(f"{ART}/MANIFEST.json")
    readme_sha = sh(f"{ART}/README.md")
    pin_sha = sh(f"{ART}/pins/af_scc_c2_vacuum.rev12.yaml")
    ctrl_sha = sh(f"{ART}/controls/controls_summary.json")
    ev = [        {
            "event_id": f"w072-{ts}-artifact-instrument",
            "event_type": "artifact", "created_at": now(), "actor": "worker-072",
            "task_id": TASK, "node_id": "F2a", "class_id": CLASSES[0], "class_ids": CLASSES,
            "artifact_type": "review_instrument",
            "path": f"{ART}/check_f2a.py", "sha256": instr_sha,
            "validation_status": "unverified",
            "gate": "G-FORM",
            "summary": "From-scratch F2a/G-FORM conformance instrument (21 checks, 9 mutation controls); does not import the canonical detector or the owner checker.",
            "evidence_refs": [f"{ART}/check_f2a.py#{instr_sha[:12]}"],
            "falsifier": "A check that does not detect its paired mutation, or a clean re-dump that changes the check statuses.",
        },
        {
            "event_id": f"w072-{ts}-artifact-report",
            "event_type": "artifact", "created_at": now(), "actor": "worker-072",
            "task_id": TASK, "node_id": "F2a", "class_id": CLASSES[0], "class_ids": CLASSES,
            "artifact_type": "conformance_report",
            "path": f"{ART}/report.json", "sha256": report_sha,
            "validation_status": "unverified",
            "gate": "G-FORM",
            "summary": f"F2a rev13 run: {counts['PASS']} PASS / {counts['FAIL']} FAIL / {counts['INFO']} INFO; controls {ctrl['PASS']} pass, {ctrl['ESCAPED']} escaped; rev12->rev13 delta is the six carded non-semantic paths only.",
            "evidence_refs": [f"{ART}/report.json#{report_sha[:12]}", f"{SCHEMA}#{schema_sha[:12]}",
                              f"{ART}/pins/af_scc_c2_vacuum.rev12.yaml#{pin_sha[:12]}"],
            "falsifier": "Re-run check_f2a.py --controls: a hash other than e9a27996dfd3, a FAIL on a clean run, a delta path outside the six named non-semantic paths, or a control escape.",
        },
        {
            "event_id": f"w072-{ts}-artifact-pin",
            "event_type": "artifact", "created_at": now(), "actor": "worker-072",
            "task_id": TASK, "node_id": "F2a", "class_id": CLASSES[0], "class_ids": CLASSES,
            "artifact_type": "pinned_input",
            "path": f"{ART}/pins/af_scc_c2_vacuum.rev12.yaml", "sha256": pin_sha,
            "validation_status": "unverified",
            "gate": "G-FORM",
            "summary": "Byte-pinned rev12 F2a (5476a3f2c6bc), equal to the lead repair report's declared pre-repair pin; used only as the delta baseline.",
            "evidence_refs": [f"{ART}/pins/af_scc_c2_vacuum.rev12.yaml#{pin_sha[:12]}",
                              "artifacts/formulation/evidence/evidence_binding_repair_rev29_report.json"],
            "falsifier": "The pin hashing other than 5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce, or not matching the lead's declared pre-repair pin.",
        },
        {
            "event_id": f"w072-{ts}-artifact-controls",
            "event_type": "artifact", "created_at": now(), "actor": "worker-072",
            "task_id": TASK, "node_id": "F2a", "class_id": CLASSES[0], "class_ids": CLASSES,
            "artifact_type": "control_evidence",
            "path": f"{ART}/controls/controls_summary.json", "sha256": ctrl_sha,
            "validation_status": "unverified",
            "gate": "G-FORM",
            "summary": "Mutation controls K1-K9: injected composite regularity, C0 conclusion type, F0 hash mismatch, self-claiming variant, I+ in conclusion, reversed quantifiers, removed falsifier, duplicate key, clean re-dump determinism; 9/9 trip, 0 escaped.",
            "evidence_refs": [f"{ART}/controls/controls_summary.json#{ctrl_sha[:12]}", f"{ART}/report.json#{report_sha[:12]}"],
            "falsifier": "Re-run the control suite: any mutation that does not trip its target check.",
        },
        {
            "event_id": f"w072-{ts}-artifact-review",
            "event_type": "artifact", "created_at": now(), "actor": "worker-072",
            "task_id": TASK, "node_id": "F2a", "class_id": CLASSES[0], "class_ids": CLASSES,
            "artifact_type": "review_verdict",
            "path": review_path, "sha256": review_sha,
            "validation_status": "unverified",
            "gate": "G-FORM",
            "summary": "Discoverable review verdict: accept 4.5 at schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3, revision 13, hard_failures []; three non-blocking findings (evidence-document byte-attribution, declarative scope limit, FROZEN rev28 not yet rev29).",
            "evidence_refs": [f"{review_path}#{review_sha[:12]}", f"{SCHEMA}#{schema_sha[:12]}", f"{ART}/report.json#{report_sha[:12]}"],
            "falsifier": "A re-measure of the schema differing from e9a27996dfd3; a review field that does not match report.json; a gate treated as moved by this file.",
        },
        {
            "event_id": f"w072-{ts}-artifact-manifest",
            "event_type": "artifact", "created_at": now(), "actor": "worker-072",
            "task_id": TASK, "node_id": "F2a", "class_id": CLASSES[0], "class_ids": CLASSES,
            "artifact_type": "manifest",
            "path": f"{ART}/MANIFEST.json", "sha256": man_sha,
            "validation_status": "unverified",
            "gate": "G-FORM",
            "summary": "sha256 of every deliverable (instrument, report, README, rev12 pin, controls summary, review verdict).",
            "evidence_refs": [f"{ART}/MANIFEST.json#{man_sha[:12]}", f"{ART}/README.md#{readme_sha[:12]}"],
            "falsifier": "Any listed file hashing differently from its MANIFEST entry.",
        },
        {
            "event_id": f"w072-{ts}-review-f2a",
            "event_type": "review", "created_at": now(), "actor": "worker-072",
            "task_id": TASK, "node_id": "F2a", "node_ids": ["F2a"],
            "class_id": CLASSES[0], "class_ids": CLASSES,
            "target_id": f"{SCHEMA}#{schema_sha[:12]}",
            "reviewer": "worker-072",
            "gate": "G-FORM",
            "verdict": "accept", "score": 4.5, "hard_failures": [],
            "counts_as_full_schema_verdict": True,
            "findings": [
                "W072F2A-01: 20/20 conformance checks PASS at rev13; 9/9 mutation controls trip.",
                "W072F2A-02: rev12->rev13 change set is exactly the carded evidence-binding refresh; no class-semantics path moved.",
                "W072F2A-03 (non-blocking): the live consistency evidence document pins the compared paths but not their bytes (worker-047 CB-2), outside the four repair items.",
                "W072F2A-04 (non-blocking): structural/declarative scope only; no mathematics, citation or adjudication verdict.",
                "W072F2A-05 (advisory): FROZEN.json is still revision 28, so the r3 round cannot yet bind rev29 pins; any further schema write voids this verdict.",
            ],
            "evidence_refs": [f"{review_path}#{review_sha[:12]}", f"{SCHEMA}#{schema_sha[:12]}",
                              f"{ART}/report.json#{report_sha[:12]}", f"{EVID}#{sh(EVID)[:12]}"],
            "falsifier": "A re-measure differing from e9a27996dfd3; a FAIL on a clean re-run; a delta path outside the six named non-semantic paths; a control escape.",
            "independence": "Not an author of F2a, F0, the supplement, VARIANT_REGISTRY, FROZEN.json or the rev29 repair tool; own instrument; no other F2a verdict text read before the verdict.",
        },
        {
            "event_id": f"w072-{ts}-claim-f2a-conformance",
            "event_type": "claim", "created_at": now(), "actor": "worker-072",
            "task_id": TASK, "node_id": "F2a", "node_ids": ["F2a"],
            "class_id": CLASSES[0], "class_ids": CLASSES,
            "conclusion_type": "formal_model",
            "statement": ("Artifact-conformance result, not a mathematics claim. At pins "
                          f"{SCHEMA}#{schema_sha[:12]} (revision 13), {TAX}#{sh(TAX)[:12]}, "
                          f"{SUPP}#{sh(SUPP)[:12]}, {EVID}#{sh(EVID)[:12]} and the pinned rev12 baseline "
                          f"{ART}/pins/af_scc_c2_vacuum.rev12.yaml#{pin_sha[:12]}: a from-scratch, "
                          "independent instrument returns 20 PASS / 0 FAIL / 1 INFO on the G-FORM criteria for F2a "
                          "(singular class id, no C0/C2 composite in specification slots, frozen conclusion_type/family, "
                          "I+/visibility roles, ordered quantifier chain with resolving domains, 4D one-ended topology, "
                          "comeager genericity with class-change warning, frozen C2/classical-Ricci/future extension predicate, "
                          "declared F0 hash binding, resolving contract pointers, declared==measured consistency-evidence "
                          "binding, complete tier-1/tier-2 falsifier, one-way C0=>C2 implication with the converse forbidden, "
                          "no duplicate YAML keys, F0 frozen stability); 9/9 mutation controls trip and 0 escape; and the "
                          "rev12 (5476a3f2c6bc) -> rev13 (e9a27996dfd3) change set is exactly revision, revised_at, "
                          "revision_history, f0_binding.consistency_evidence_sha256, f0_binding.checked_at and "
                          "f0_binding.binding_note, with no class-semantics path moved. This is a statement about the "
                          "artifact bytes and their consistency, not about the truth, provability or citations of the class."),
            "assumptions": [
                "The G-FORM criteria are read as stated in the map gate and the carded repair acceptance.",
                "The rev12 baseline copy is valid because its sha256 equals the lead repair report's declared pre-repair pin 5476a3f2c6bc.",
                "Byte stability of the schema across the review window is claimed only up to the final measurement recorded in report.json.",
            ],
            "evidence_refs": [f"{review_path}#{review_sha[:12]}", f"{ART}/report.json#{report_sha[:12]}",
                              f"{SCHEMA}#{schema_sha[:12]}", f"{ART}/pins/af_scc_c2_vacuum.rev12.yaml#{pin_sha[:12]}"],
            "falsifier": "Re-run check_f2a.py --controls at the pinned paths: a different schema hash, a FAIL on a clean run, a delta path outside the six named non-semantic paths, or a control escape falsifies this claim.",
        },
        {
            "event_id": f"w072-{ts}-status-exit",
            "event_type": "status", "created_at": now(), "actor": "worker-072",
            "task_id": TASK, "node_id": "F2a", "node_ids": ["F2a"],
            "class_id": CLASSES[0], "class_ids": CLASSES,
            "status": "active", "hours": 0.25, "gate": "G-FORM",
            "summary": ("Checkpoint w072-f2a-review-ckpt-1: W072-F2A-REVIEW-01 complete at worker level (completion claim for the "
                        "bounded deliverable only, not a node transition and not a gate verdict). One class-bound task delivered: "
                        f"independent non-author conformance review of F2a at {SCHEMA}#{schema_sha[:12]}, accept 4.5, "
                        "20 PASS / 0 FAIL / 1 INFO, 9/9 controls. Bounded execution worker exiting for recycling."),
            "evidence_refs": [f"{review_path}#{review_sha[:12]}", f"{CKPT}#pending",
                              f"{ART}/report.json#{report_sha[:12]}", f"{SCHEMA}#{schema_sha[:12]}"],
            "next_falsifier": ("Re-measure " + SCHEMA + ": a hash other than " + schema_sha[:12] + " voids the verdict. "
                               "FROZEN.json is still revision 28; the r3 round needs rev29 published with matching pins before "
                               "any binding coverage exists."),
            "claims_completion": False,
        },
    ]

    ckpt = {
        "checkpoint_id": "w072-f2a-review-ckpt-1",
        "created_at": now(), "actor": "worker-072", "task_id": TASK,
        "class_id": CLASSES[0], "class_ids": CLASSES,
        "node_ids": ["F2a"], "gate": "G-FORM", "status": "active", "hours": 0.25,
        "question": "Does F2a (AF-SCC-C2-VAC-GEN) satisfy the G-FORM schema criteria at its live bytes, and is the rev12->rev13 repair semantics-preserving for this class?",
        "pins": {
            SCHEMA: schema_sha,
            f"{ART}/pins/af_scc_c2_vacuum.rev12.yaml": pin_sha,
            TAX: sh(TAX), SUPP: sh(SUPP), EVID: sh(EVID),
        },
        "artifacts": {
            "instrument": {"path": f"{ART}/check_f2a.py", "sha256": instr_sha},
            "report": {"path": f"{ART}/report.json", "sha256": report_sha},
            "readme": {"path": f"{ART}/README.md", "sha256": readme_sha},
            "manifest": {"path": f"{ART}/MANIFEST.json", "sha256": man_sha},
            "controls": {"path": f"{ART}/controls/controls_summary.json", "sha256": ctrl_sha},
            "review": {"path": review_path, "sha256": review_sha},
        },
        "result_digest": report_sha,
        "checks": {"pass": counts["PASS"], "fail": counts["FAIL"], "info": counts["INFO"],
                   "failed_ids": counts["failed_ids"],
                   "controls_pass": ctrl["PASS"], "controls_escaped": ctrl["ESCAPED"]},
        "verdict": {"value": "accept", "score": 4.5, "hard_failures": [],
                    "binding_authority": "audit lead adjudicates G-FORM coverage; Astra records the gate"},
        "findings": [f["id"] + ": " + f["finding"][:200] for f in json.load(open(os.path.join(ROOT, review_path)))["findings"]],
        "non_blocking": ["W072F2A-03 consistency evidence pins paths not bytes", "W072F2A-04 declarative scope only",
                         "W072F2A-05 FROZEN.json still revision 28"],
        "falsifier": "Re-run check_f2a.py --controls: a schema hash other than " + schema_sha[:12] + ", a FAIL on a clean run, a delta path outside the six named non-semantic paths, or a control escape.",
        "authority": "worker evidence only; no node done, no validation_status, no gate verdict, no theorem",
    }
    with open(os.path.join(ROOT, CKPT), "w", encoding="utf-8") as f:
        json.dump(ckpt, f, indent=1)
        f.write("\n")
    with open(os.path.join(ROOT, CKPT_LOG), "a", encoding="utf-8") as f:
        f.write(json.dumps({k: ckpt[k] for k in ("checkpoint_id", "created_at", "actor", "task_id", "class_id",
                                                 "node_ids", "gate", "status", "hours", "result_digest", "verdict")},
                           ensure_ascii=False) + "\n")
    ckpt_sha = sh(CKPT)
    ev[-1]["evidence_refs"][1] = f"{CKPT}#{ckpt_sha[:12]}"
    lines = []
    for e in ev:
        schemas.validate_event(e)
        lines.append(json.dumps(e, ensure_ascii=False))
    with open(os.path.join(ROOT, OUTBOX), "a", encoding="utf-8") as f:
        for ln in lines:
            f.write(ln + "\n")

    # final validity re-scan of the whole outbox
    total = bad = 0
    for ln in open(os.path.join(ROOT, OUTBOX), encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        total += 1
        try:
            schemas.validate_event(json.loads(ln))
        except Exception as ex:
            bad += 1
            print("INVALID outbox line:", ex)
    print(json.dumps({"appended": len(lines), "outbox_lines": total, "invalid": bad,
                      "checkpoint": CKPT, "checkpoint_sha256_prefix": sh(CKPT)[:12],
                      "review": review_path, "verdict": "accept", "score": 4.5,
                      "schema_sha256": schema_sha}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
