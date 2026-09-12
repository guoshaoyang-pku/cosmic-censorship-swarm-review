#!/usr/bin/env python3
"""Emit the W076-F2B-LANDING-AUDIT-02 events to comms/outbox/worker-076.jsonl and write the
worker checkpoint. Idempotent: existing event_ids / checkpoint_id are skipped.

Run from the repository root (or anywhere; ROOT is resolved from this file):
    python3 artifacts/worker-076/f2b_repair_landing_audit/emit_events_and_checkpoint.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from research_map.schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
TS = datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S+08:00")
TASK_ID = "W076-F2B-LANDING-AUDIT-02"
CLASS = "AF-SCC-C0-VAC-GEN"
OUTBOX = ROOT / "comms/outbox/worker-076.jsonl"
CKPT = ROOT / "runtime/state/w076_f2b_landing_audit_checkpoint.json"
CKPT_LOG = ROOT / "runtime/state/w076_checkpoints.jsonl"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


REPORT = HERE / "report.json"
CANDIDATE = HERE / "candidate/af_scc_c0_vacuum.repair-minimal.yaml"
PROBE = HERE / "probe/f0_binding_naive_supplement_sha_probe.yaml"
README = HERE / "README.md"
SCRIPT = HERE / "audit_f2b_repair_candidates.py"

rep = json.loads(REPORT.read_text())
h_report, h_cand, h_probe, h_readme, h_script = map(sha, (REPORT, CANDIDATE, PROBE, README, SCRIPT))
summary = rep["summary"]
pins = rep["pins"]

evidence = [
    f"artifacts/worker-076/f2b_repair_landing_audit/report.json#{h_report[:12]}",
    f"artifacts/worker-076/f2b_repair_landing_audit/candidate/af_scc_c0_vacuum.repair-minimal.yaml#{h_cand[:12]}",
    f"artifacts/worker-076/f2b_repair_landing_audit/probe/f0_binding_naive_supplement_sha_probe.yaml#{h_probe[:12]}",
    f"artifacts/worker-076/f2b_repair_landing_audit/README.md#{h_readme[:12]}",
    f"artifacts/worker-076/f2b_repair_landing_audit/audit_f2b_repair_candidates.py#{h_script[:12]}",
    f"schemas/af_scc_c0_vacuum.yaml#{pins['schemas/af_scc_c0_vacuum.yaml']['sha256'][:12]}",
    f"artifacts/formulation/evidence/taxonomy_consistency.json#{pins['artifacts/formulation/evidence/taxonomy_consistency.json']['sha256'][:12]}",
    f"artifacts/formulation/FROZEN.json#{pins['artifacts/formulation/FROZEN.json']['sha256'][:12]}",
    f"research_map/formulation_taxonomy.yaml#{pins['research_map/formulation_taxonomy.yaml']['sha256'][:12]}",
    f"artifacts/formulation/formulation_taxonomy.yaml#{pins['artifacts/formulation/formulation_taxonomy.yaml']['sha256'][:12]}",
    "artifacts/worker-007/f2b_containment_repair/report.json#4fb46e82279d",
    "artifacts/worker-022/f2b_cd_repair/candidate/af_scc_c0_vacuum.repair-candidate.yaml#a110f8e875af",
    "artifacts/worker-044/f2b_rev13_integration/sandbox/schemas/af_scc_c0_vacuum.yaml#48cadb72e507",
]

NEXT_FALSIFIER = (
    "At the pinned snapshots: (a) a candidate marked NOT_PROMOTION_READY that passes every check "
    "under an independent re-implementation at the same bytes; (b) the composite passing while any "
    "changed line falls outside the classified repair slots; (c) live taxonomy_consistency.json "
    "measuring other than 9e335e9b at the declared checked_at, which voids the binding-regression "
    "finding against 48cadb72e507; (d) check_class_schema.py returning pass on the R22 probe."
)

events = [
    {
        "event_id": "w076-20260912-f2b-landing-audit-artifact-report",
        "event_type": "artifact",
        "created_at": TS,
        "actor": "worker-076",
        "node_id": "F2b",
        "class_id": CLASS,
        "class_ids": [CLASS],
        "gate": "G-FORM",
        "task_id": TASK_ID,
        "artifact_type": "f2b_repair_candidate_landing_audit",
        "path": "artifacts/worker-076/f2b_repair_landing_audit/report.json",
        "sha256": h_report,
        "validation_status": "unverified",
        "summary": (
            "Independent landing audit of the staged F2b containment repairs at live rev13 "
            "b2ab6acb2bbe. 12 checks per target, snapshots pinned, 0 pin drift, lead conformance "
            "tool run on every target. Verdicts: LIVE, worker-022 a110f8e875af, worker-044 "
            "48cadb72e507 and the worker-044 acceptance oracle 3ab16da27e7b are "
            "NOT_PROMOTION_READY; the staged composite candidate is PROMOTION_READY. Worker "
            "measurement only; no canonical write, no gate verdict, no node status."
        ),
        "evidence_refs": evidence,
        "falsifier": NEXT_FALSIFIER,
    },
    {
        "event_id": "w076-20260912-f2b-landing-audit-artifact-composite",
        "event_type": "artifact",
        "created_at": TS,
        "actor": "worker-076",
        "node_id": "F2b",
        "class_id": CLASS,
        "class_ids": [CLASS],
        "gate": "G-FORM",
        "task_id": TASK_ID,
        "artifact_type": "f2b_staged_repair_candidate_noncanonical",
        "path": "artifacts/worker-076/f2b_repair_landing_audit/candidate/af_scc_c0_vacuum.repair-minimal.yaml",
        "sha256": h_cand,
        "validation_status": "unverified",
        "summary": (
            "STAGED, NON-CANONICAL composite candidate for lead promotion: C044's line-152 wording "
            "(bracket omitted; revision_history records it), both candidates' line-246 correction "
            "('larger' -> 'smaller' extension class), revision 13 -> 14 with revision_history index "
            "12, live f0_binding.consistency_evidence_sha256 9e335e9b retained, and the "
            "binding-completeness / vocabulary-binding fields placed under the documented "
            "extensions: escape hatch (a direct f0_binding placement is rejected by R22). Passes "
            "all 12 audit checks and the lead conformance tool. Promotion is lead-owned; nothing "
            "here authorises it."
        ),
        "evidence_refs": evidence,
        "falsifier": NEXT_FALSIFIER,
    },
    {
        "event_id": "w076-20260912-f2b-landing-audit-claim",
        "event_type": "claim",
        "created_at": TS,
        "actor": "worker-076",
        "node_id": "F2b",
        "class_id": CLASS,
        "class_ids": [CLASS],
        "gate": "G-FORM",
        "task_id": TASK_ID,
        "conclusion_type": "formal_model",
        "statement": (
            "FORMAL-MODEL-LEVEL binding/byte finding (not a mathematics claim) at the pinned live "
            "F2b bytes: neither staged candidate that worker-007's containment predicate records "
            "REPAIR_OK is promotion-ready. (i) worker-022 a110f8e875af fixes both containment slots "
            "but changes bytes with revision still 13 (same-revision move, CF-27) and its line-152 "
            "bullet uses 'strictly between' as live text while declaring the phrase 'not used'. "
            "(ii) worker-044 48cadb72e507 fixes both slots, bumps revision to 14 with no "
            "revision_history entry, and reverts f0_binding.consistency_evidence_sha256 from the "
            "live 9e335e9b to the superseded 675a99d0, re-opening W007-RP-HF-01 closed by "
            "astra-life05-evidence-binding-repair. (iii) The staged composite candidate (b2ab6acb2bbe "
            "plus C044 line-152 wording, the line-246 'smaller class' correction, revision 14 + "
            "history entry, live 9e335e9b retained, extensions.binding_completeness and "
            "extensions.vocabulary_binding pinned to the live supplement d7419b4e8963 and alias "
            "registry 46cd9f1e) passes all 12 checks. The lead-owned check_class_schema.py returns "
            "pass on all five targets including live rev13, so it does not discriminate these "
            "defects; the review layer is load-bearing."
        ),
        "assumptions": [
            "the canonical-path policy remains in force: schemas/ is authoritative and the FROZEN "
            "manifest pins the reviewed bytes",
            "the audit is valid only at the snapshotted bytes; live drift voids it (pin_drift was "
            "empty before and after the recorded run)",
            "worker-007's REPAIR_OK predicate is taken as the competing claim under audit, not as "
            "evidence for it",
        ],
        "falsifier": NEXT_FALSIFIER,
        "evidence_refs": evidence,
        "artifact_refs": [
            f"artifacts/worker-076/f2b_repair_landing_audit/report.json#{h_report[:12]}",
            f"artifacts/worker-076/f2b_repair_landing_audit/candidate/af_scc_c0_vacuum.repair-minimal.yaml#{h_cand[:12]}",
        ],
    },
    {
        "event_id": "w076-20260912-f2b-landing-audit-review",
        "event_type": "review",
        "created_at": TS,
        "actor": "worker-076",
        "node_id": "F2b",
        "class_id": CLASS,
        "class_ids": [CLASS],
        "gate": "G-FORM",
        "task_id": TASK_ID,
        "target_id": (
            "artifacts/worker-022/f2b_cd_repair/candidate/af_scc_c0_vacuum.repair-candidate.yaml#a110f8e875af; "
            "artifacts/worker-044/f2b_rev13_integration/sandbox/schemas/af_scc_c0_vacuum.yaml#48cadb72e507"
        ),
        "reviewer": "worker-076",
        "verdict": "revise",
        "score": 3.0,
        "hard_failures": [
            {
                "id": "W076-F2B-LA-HF1",
                "class": CLASS,
                "severity": "major",
                "candidate": "a110f8e875af",
                "finding": "bytes differ from live b2ab6acb2bbe while revision stays 13 and no "
                           "revision_history entry is added (FROZEN same-revision move, CF-27); the "
                           "line-152 repair also contradicts itself by using 'strictly between' live "
                           "while declaring the phrase unused.",
                "repair": "bump the revision and add the revision_history entry; use a wording that "
                          "does not use the phrase it forbids (e.g. 'is not a class definition').",
                "falsifier": "the same bytes with revision > 13, a matching revision_history entry, "
                             "and no live/unused self-reference.",
            },
            {
                "id": "W076-F2B-LA-HF2",
                "class": CLASS,
                "severity": "blocking",
                "candidate": "48cadb72e507",
                "finding": "f0_binding.consistency_evidence_sha256 is reverted to the superseded "
                           "675a99d0 while the live artifacts/formulation/evidence/taxonomy_consistency.json "
                           "measures 9e335e9b; this re-opens W007-RP-HF-01 at the new hash. Revision 14 "
                           "has no revision_history entry.",
                "repair": "keep the live 9e335e9b pin and add the rev14 revision_history entry.",
                "falsifier": "a byte-set whose f0_binding declares the live evidence hash and whose "
                             "revision bump is recorded in revision_history.",
            },
        ],
        "findings": [
            "Both candidates pass worker-007's eight containment checks; the divergence is in the "
            "binding chain and the change protocol, which that predicate does not test.",
            "The lead-owned check_class_schema.py returns pass on both candidates and on live rev13; "
            "R22 is the tool's only rejection in this audit (naive class_contract_supplement_sha256 "
            "placement under f0_binding).",
            "The staged composite candidate clears both hard failures; this verdict is advisory and "
            "authorises no promotion.",
        ],
        "evidence_refs": evidence,
    },
    {
        "event_id": "w076-20260912-f2b-landing-audit-status",
        "event_type": "status",
        "created_at": TS,
        "actor": "worker-076",
        "node_id": "F2b",
        "class_id": CLASS,
        "class_ids": [CLASS],
        "gate": "G-FORM",
        "task_id": TASK_ID,
        "status": "active",
        "hours": 0.6,
        "summary": (
            "W076-F2B-LANDING-AUDIT-02 complete at worker level (one bounded class-bound task taken; "
            "no inbox card for worker-076). Independent landing audit of the staged F2b repairs at "
            "live rev13 b2ab6acb2bbe: both worker-007 REPAIR_OK candidates fail promotion for "
            "different reasons (a110f8e875af: no revision bump + line-152 self-contradiction; "
            "48cadb72e507: evidence-binding revert to 675a99d0 + unrecorded rev14), the acceptance "
            "oracle is stale, and the staged composite candidate passes all 12 checks. Recommend the "
            "lead promote the composite's slots, regenerate FROZEN, and re-review at the new hash. "
            "No canonical write, no gate verdict, no node status, no validation_status=passed."
        ),
        "evidence_refs": evidence,
        "next_falsifier": NEXT_FALSIFIER,
    },
]

# --- validate + append idempotently ---
OUTBOX.parent.mkdir(parents=True, exist_ok=True)
existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            existing.add(json.loads(line).get("event_id"))
        except json.JSONDecodeError:
            pass

written = []
with OUTBOX.open("a") as f:
    for e in events:
        validate_event(e)
        if e["event_id"] in existing:
            continue
        f.write(json.dumps(e, sort_keys=True) + "\n")
        written.append(e["event_id"])

checkpoint = {
    "checkpoint_id": f"w076-f2b-landing-audit-{TS.replace('-', '').replace(':', '').replace('+0800', '')}",
    "at": TS,
    "worker": "worker-076",
    "task_id": TASK_ID,
    "node_id": "F2b",
    "class_id": CLASS,
    "gate": "G-FORM",
    "hours": 0.6,
    "authority": "worker measurement only; no canonical write, no gate verdict, no node status",
    "pins": {k: v["sha256"] for k, v in pins.items() if not k.startswith("_")},
    "artifacts": {
        "report": f"artifacts/worker-076/f2b_repair_landing_audit/report.json#{h_report[:12]}",
        "candidate": f"artifacts/worker-076/f2b_repair_landing_audit/candidate/af_scc_c0_vacuum.repair-minimal.yaml#{h_cand[:12]}",
        "probe": f"artifacts/worker-076/f2b_repair_landing_audit/probe/f0_binding_naive_supplement_sha_probe.yaml#{h_probe[:12]}",
        "script": f"artifacts/worker-076/f2b_repair_landing_audit/audit_f2b_repair_candidates.py#{h_script[:12]}",
        "readme": f"artifacts/worker-076/f2b_repair_landing_audit/README.md#{h_readme[:12]}",
    },
    "verdicts": {k: v["verdict"] for k, v in rep["candidates"].items()},
    "promotion_ready": summary["promotion_ready"],
    "not_promotion_ready": summary["not_promotion_ready"],
    "events_emitted": written,
    "next_falsifier": NEXT_FALSIFIER,
}
CKPT.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
with CKPT_LOG.open("a") as f:
    f.write(json.dumps(checkpoint, sort_keys=True) + "\n")

print(json.dumps({"events_written": written, "outbox": str(OUTBOX.relative_to(ROOT)),
                  "checkpoint": str(CKPT.relative_to(ROOT)), "checkpoint_id": checkpoint["checkpoint_id"],
                  "report_sha256": h_report, "candidate_sha256": h_cand}, indent=2))
