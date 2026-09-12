#!/usr/bin/env python3
"""W008-F2B-DUALREPAIR-01 — emit outbox events and checkpoint.

Writes comms/outbox/worker-008-f2b.jsonl (artifact x4, claim, blocker, status),
validates every event with research_map.schemas.validate_event, writes
runtime/state/worker-008_f2b_dualrepair_checkpoint.json and appends to
artifacts/worker-008/checkpoints.jsonl.  Never edits a canonical artifact and
never sets a gate verdict or node done.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
sys.path.insert(0, str(REPO / "research_map"))
from schemas import validate_event, SchemaError  # noqa: E402

CST = timezone(timedelta(hours=8))
TS = datetime.now(CST).replace(microsecond=0).isoformat()
SLUG = TS.replace("-", "").replace(":", "").replace("+0800", "").replace("+08:00", "")
ACTOR = "worker-008"
NODE = "F2b"
CLASS = "AF-SCC-C0-VAC-GEN"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(p: str, h: str, n: int = 12) -> str:
    return f"{p}#{h[:n]}"


report = json.loads((ROOT / "evidence" / "report.json").read_text())
cand = report["candidate_patch"]
canon = report["inputs"]["canonical_c0"]
files = {
    "checker": ("artifacts/worker-008/f2b_rev11_dualrepair/audit_dual_defect.py",
                ROOT / "audit_dual_defect.py"),
    "report": ("artifacts/worker-008/f2b_rev11_dualrepair/evidence/report.json",
               ROOT / "evidence" / "report.json"),
    "candidate": ("artifacts/worker-008/f2b_rev11_dualrepair/candidate/af_scc_c0_vacuum.yaml",
                  ROOT / "candidate" / "af_scc_c0_vacuum.yaml"),
    "controls": ("artifacts/worker-008/f2b_rev11_dualrepair/evidence/controls_summary.json",
                 ROOT / "evidence" / "controls_summary.json"),
    "checkpoint": ("runtime/state/worker-008_f2b_dualrepair_checkpoint.json",
                   REPO / "runtime" / "state" / "worker-008_f2b_dualrepair_checkpoint.json"),
}
hashes = {k: sha(p) for k, (_, p) in files.items() if p.exists()}

common_evidence = [
    ref(canon["path"], canon["sha256"]),
    ref(report["inputs"]["canonical_c2"]["path"], report["inputs"]["canonical_c2"]["sha256"]),
    ref(files["report"][0], hashes.get("report", "")),
    ref(files["checker"][0], hashes.get("checker", "")),
    ref(files["controls"][0], hashes.get("controls", "")),
    "schemas/af_scc_c0_vacuum.yaml:251",
    "schemas/af_scc_c0_vacuum.yaml:157",
    "schemas/af_scc_c0_vacuum.yaml:244",
    "schemas/af_scc_c0_vacuum.yaml:246-248",
]

FALSIFIER = (
    "A reading under which line 251's 'C2 is a strictly larger extension class' is not a class-size "
    "premise, or a reading under which line 157's 'No containment with C2 or C0 is asserted here' is "
    "consistent with the same file's declared chain (lines 244, 246-248); or a canonical C0 hash "
    "different from the bound one at which the two findings vanish; or a candidate structural change "
    "outside the two declared YAML paths. Any of these falsifies this finding at the bound hashes. "
    "A G-FORM reviewer verdict is required before any promotion."
)

events = [
    {
        "event_id": f"w008-f2b-{SLUG}-artifact-checker",
        "event_type": "artifact", "created_at": TS, "actor": ACTOR,
        "node_id": NODE, "class_id": CLASS, "gate": "G-FORM",
        "artifact_type": "independent_checker",
        "path": files["checker"][0], "sha256": hashes["checker"],
        "validation_status": "unverified",
        "evidence_refs": common_evidence,
        "summary": "Fail-closed containment-consistency checker (CHK-1 chain concordance, CHK-2 size/"
                   "strength premises, CHK-3 false denials, CHK-4 binding integrity; exit 3 without a "
                   "verdict on hash mismatch). 6/6 synthetic selftest; 5-case control battery.",
        "falsifier": "A synthetic pair in which the checker's verdict does not follow the declared "
                     "order, or a run at a mismatched --expect that still emits a verdict.",
    },
    {
        "event_id": f"w008-f2b-{SLUG}-artifact-report",
        "event_type": "artifact", "created_at": TS, "actor": ACTOR,
        "node_id": NODE, "class_id": CLASS, "gate": "G-FORM",
        "artifact_type": "review_evidence",
        "path": files["report"][0], "sha256": hashes["report"],
        "validation_status": "unverified",
        "evidence_refs": common_evidence,
        "summary": f"Audit at canonical C0 {canon['sha256'][:12]} (FROZEN rev "
                   f"{report['frozen_binding']['frozen_revision']}, defect inside the frozen set): FAIL "
                   f"with 2 findings (size_premise_inverted line 251; false_containment_denial line 157). "
                   f"Rebased 2-edit candidate {cand['sha256'][:12]}: PASS. Controls all met.",
        "falsifier": FALSIFIER,
    },
    {
        "event_id": f"w008-f2b-{SLUG}-artifact-candidate",
        "event_type": "artifact", "created_at": TS, "actor": ACTOR,
        "node_id": NODE, "class_id": CLASS, "gate": "G-FORM",
        "artifact_type": "repair_candidate",
        "path": files["candidate"][0], "sha256": hashes["candidate"],
        "validation_status": "unverified",
        "evidence_refs": common_evidence + [ref(files["candidate"][0], hashes["candidate"])],
        "summary": "Byte-minimal wording repair rebased onto frozen rev11: exactly 2 changed leaf paths "
                   "(" + ", ".join(cand["changed_leaf_paths"]) + "); f0_binding/class_contract_pointer/"
                   "class_id/revision unchanged. Owner publishes and re-freezes; workers do not edit the "
                   "canonical path.",
        "falsifier": "Any structural change outside the two declared leaf paths, a candidate hash equal "
                     "to the canonical hash, or any binding-field drift falsifies minimality.",
    },
    {
        "event_id": f"w008-f2b-{SLUG}-artifact-controls",
        "event_type": "artifact", "created_at": TS, "actor": ACTOR,
        "node_id": NODE, "class_id": CLASS, "gate": "G-FORM",
        "artifact_type": "control_evidence",
        "path": files["controls"][0], "sha256": hashes["controls"],
        "validation_status": "unverified",
        "evidence_refs": common_evidence,
        "summary": "Control battery all met: ctl0 no-op = canonical FAIL (2 kinds); ctl1 revert only the "
                   "line-251 clause -> FAIL size_premise_inverted; ctl2 revert only the line-157 denial -> "
                   "FAIL false_containment_denial; candidate PASS; synthetic selftest 6/6.",
        "falsifier": "Any control whose observed verdict/finding set differs from its expectation, or a "
                     "candidate PASS without both single-defect reverts failing.",
    },
    {
        "event_id": f"w008-f2b-{SLUG}-claim",
        "event_type": "claim", "created_at": TS, "actor": ACTOR,
        "node_id": NODE, "class_id": CLASS, "gate": "G-FORM",
        "conclusion_type": "formal_model",
        "statement": (
            f"At the frozen canonical hashes C0 {canon['sha256']} and C2 "
            f"{report['inputs']['canonical_c2']['sha256']} (FROZEN rev "
            f"{report['frozen_binding']['frozen_revision']}), schemas/af_scc_c0_vacuum.yaml carries two "
            "text-level containment inconsistencies with its own declared chain (line 244: E_C0 contains "
            "E_H2loc contains E_{C^1,1} contains E_C2): (1) line 251, "
            "implication_ledger.forbidden_transfers[0].reason calls C2 'a strictly larger extension "
            "class' although the chain makes E_C2 the smallest extension set; the forbidden direction "
            "and the 'strictly weaker' consequent are correct, only the size premise is inverted; "
            "(2) line 157, regularity.must_not_conflate[0] asserts 'No containment with C2 or C0 is "
            "asserted here', while lines 244 and 246-248 assert that nesting. A byte-minimal candidate "
            f"(sha256 {cand['sha256']}) changing exactly those two leaf paths audits PASS where the "
            "canonical audits FAIL, under a checker whose 5-case control battery and 6/6 synthetic "
            "selftest pass. This is a consistency finding, not a mathematical result: no class is "
            "claimed true, refuted or closed, and no gate verdict is claimed."),
        "assumptions": report["assumptions"],
        "artifact_refs": [ref(files["report"][0], hashes["report"]),
                          ref(files["candidate"][0], hashes["candidate"]),
                          ref(files["checker"][0], hashes["checker"]),
                          ref(files["controls"][0], hashes["controls"])],
        "evidence_refs": common_evidence,
        "falsifier": FALSIFIER,
    },
    {
        "event_id": f"w008-f2b-{SLUG}-blocker",
        "event_type": "blocker", "created_at": TS, "actor": ACTOR,
        "node_id": NODE, "class_id": CLASS, "gate": "G-FORM",
        "description": (
            "F2b canonical rev11 (C0 1bb78ce9, inside FROZEN rev26) still carries the FORM-SEP-04 "
            "containment inversion at implication_ledger.forbidden_transfers[0].reason (line 251, "
            "'strictly larger' -> should be 'strictly smaller') and the stale denial at "
            "regularity.must_not_conflate[0] (line 157, 'No containment with C2 or C0 is asserted "
            "here'). Reported independently by deepseek-flash-08 (00:11:04, 00:23:05), worker-080, "
            "worker-058 and worker-057; unchanged at the rev26 freeze. The C2 sibling already carries "
            "the corrected wording."),
        "needed_to_unblock": (
            "lead-formulation: apply the two wording edits from the candidate at "
            f"{files['candidate'][0]}#{hashes['candidate'][:12]} (or equivalent wording), bump "
            "revision/revised_at, publish the authoring mirror byte-identically and re-freeze; then "
            "re-run audit_dual_defect.py at the new hashes and confirm FAIL->PASS with C2 unchanged. "
            "lead-audit/reviewer: dispose of the finding in the G-FORM review corpus."),
        "evidence_refs": common_evidence + [ref(files["candidate"][0], hashes["candidate"])],
        "stop_rule": "Repair + re-freeze + re-run to PASS; or a reviewer rules the two sentences "
                     "non-normative prose at the bound hash.",
    },
    {
        "event_id": f"w008-f2b-{SLUG}-status",
        "event_type": "status", "created_at": TS, "actor": ACTOR,
        "node_id": NODE, "class_id": CLASS, "gate": "G-FORM",
        "status": "active", "hours": 0.6,
        "summary": (
            "One bounded class-bound task delivered: rebased dual-defect containment-consistency audit "
            f"for AF-SCC-C0-VAC-GEN at canonical C0 {canon['sha256'][:12]} (FAIL, 2 findings) with a "
            f"byte-minimal 2-edit candidate {cand['sha256'][:12]} (PASS), 5-case control battery and 6/6 "
            "checker selftest. Artifacts under artifacts/worker-008/f2b_rev11_dualrepair/; outbox "
            "comms/outbox/worker-008-f2b.jsonl; checkpoint "
            "runtime/state/worker-008_f2b_dualrepair_checkpoint.json. No node done, no gate verdict, no "
            "theorem claimed."),
        "evidence_refs": common_evidence,
        "next_falsifier": report["next_falsifier"],
        "completion_scope": "worker lifecycle only; this is completion of one audit task, not a node done "
                            "and not a gate verdict (PROTOCOL rule 2 and the worker authority limit).",
    },
]

# validate
errors = []
for e in events:
    try:
        validate_event(e)
    except SchemaError as exc:
        errors.append({"event_id": e.get("event_id"), "error": str(exc)})
if errors:
    print(json.dumps({"verdict": "REJECTED-LOCALLY", "errors": errors}, indent=1))
    sys.exit(3)

out = REPO / "comms" / "outbox" / "worker-008-f2b.jsonl"
with open(out, "w") as fh:
    for e in events:
        fh.write(json.dumps(e, sort_keys=True) + "\n")

# checkpoint
instances = sorted((REPO / "runtime" / "instances").glob("worker-008-*"))
instance = instances[-1].name if instances else None
checkpoint = {
    "checkpoint_id": f"worker-008-f2b-dualrepair-{SLUG}",
    "worker": ACTOR, "instance": instance, "created_at": TS,
    "task_id": "W008-F2B-DUALREPAIR-01",
    "task": "Rebased dual-defect containment-consistency audit + byte-minimal repair candidate for "
            "AF-SCC-C0-VAC-GEN (F2b) at the frozen rev11/rev26 canonical hashes",
    "node_id": NODE, "class_id": CLASS, "gate": "G-FORM",
    "status": "complete",
    "verdict": report["verdict"],
    "inputs": report["inputs"],
    "frozen_binding": report["frozen_binding"],
    "artifacts": {files[k][0]: hashes[k] for k in files if k in hashes},
    "outbox": str(out.relative_to(REPO)),
    "findings": report["finding_summary"]["canonical"],
    "candidate_patch": cand,
    "controls_all_met": report["controls"] and all(c["expectation_met"] for c in report["controls"].values()),
    "blocking": ["lead-formulation must apply the two wording edits and re-freeze; re-run the checker "
                 "at the new hashes and confirm FAIL->PASS"],
    "next_falsifier": report["next_falsifier"],
    "completion_scope": "worker lifecycle only; no node done and no gate verdict",
}
cp = REPO / "runtime" / "state" / "worker-008_f2b_dualrepair_checkpoint.json"
cp.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
with open(REPO / "artifacts" / "worker-008" / "checkpoints.jsonl", "a") as fh:
    fh.write(json.dumps(checkpoint, sort_keys=True) + "\n")

print(json.dumps({"events": len(events), "outbox": str(out.relative_to(REPO)),
                  "checkpoint": str(cp.relative_to(REPO)), "validation": "LOCAL-SCHEMA-OK",
                  "timestamp": TS}, indent=1))
