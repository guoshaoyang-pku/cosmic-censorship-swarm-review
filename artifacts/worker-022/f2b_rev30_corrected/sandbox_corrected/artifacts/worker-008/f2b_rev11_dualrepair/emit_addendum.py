#!/usr/bin/env python3
"""W008-F2B-DUALREPAIR-01 — append addendum events (rev12/rev27 binding) and
checkpoint v2.  Appends to comms/outbox/worker-008-f2b.jsonl; validates every
event with research_map.schemas.validate_event.
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
SLUG = TS.replace("-", "").replace(":", "").replace("+08:00", "")
ACTOR, NODE, CLASS = "worker-008", "F2b", "AF-SCC-C0-VAC-GEN"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(p, h, n=12):
    return f"{p}#{h[:n]}"


add = json.loads((ROOT / "evidence" / "rev12_addendum.json").read_text())
c0 = add["bases"]["c0"]
c2 = add["bases"]["c2"]
cand = add["candidate_rev12"]
drift = add["frozen_drift"]
path_add = "artifacts/worker-008/f2b_rev11_dualrepair/evidence/rev12_addendum.json"
path_cand = "artifacts/worker-008/f2b_rev11_dualrepair/candidate_rev12/af_scc_c0_vacuum.yaml"
sha_add, sha_cand = sha(ROOT / "evidence" / "rev12_addendum.json"), sha(ROOT / "candidate_rev12" / "af_scc_c0_vacuum.yaml")
f_prev = add["canonical_rev12_audit"]["findings"][0]["file"] if add["canonical_rev12_audit"]["findings"] else ""
FALSIFIER = add["falsifier"]
EVID = [ref(c0["path"], c0["sha256"]), ref(c2["path"], c2["sha256"]), ref(path_add, sha_add),
        ref(path_cand, sha_cand), "schemas/af_scc_c0_vacuum.yaml:245", "schemas/af_scc_c0_vacuum.yaml:151"]

events = [
    {
        "event_id": f"w008-f2b-{SLUG}-artifact-addendum",
        "event_type": "artifact", "created_at": TS, "actor": ACTOR,
        "node_id": NODE, "class_id": CLASS, "gate": "G-FORM",
        "artifact_type": "review_evidence", "path": path_add, "sha256": sha_add,
        "validation_status": "unverified", "evidence_refs": EVID,
        "summary": f"Rev12/rev27 re-measurement: canonical C0 {c0['sha256'][:12]} still FAILs with the "
                   f"same 2 finding kinds (size premise at forbidden_transfers[0].reason, denial at "
                   f"must_not_conflate[0]); C2 {c2['sha256'][:12]}; chain concordant; FROZEN "
                   f"rev {drift['frozen_revision']} pins exactly these hashes "
                   f"(authoring mirror aligned: {drift['authoring_mirror_aligned']}).",
        "falsifier": FALSIFIER,
    },
    {
        "event_id": f"w008-f2b-{SLUG}-artifact-candidate-rev12",
        "event_type": "artifact", "created_at": TS, "actor": ACTOR,
        "node_id": NODE, "class_id": CLASS, "gate": "G-FORM",
        "artifact_type": "repair_candidate", "path": path_cand, "sha256": sha_cand,
        "validation_status": "unverified", "evidence_refs": EVID,
        "summary": "Same byte-minimal 2-edit repair rebased onto rev12: exactly the two declared leaf "
                   "paths change, binding fields untouched; audits PASS where rev12 FAILs; single-defect "
                   "reverts fail one kind each (ctl1 size_premise_inverted, ctl2 false_containment_denial).",
        "falsifier": FALSIFIER,
    },
    {
        "event_id": f"w008-f2b-{SLUG}-claim-rev12",
        "event_type": "claim", "created_at": TS, "actor": ACTOR,
        "node_id": NODE, "class_id": CLASS, "gate": "G-FORM",
        "conclusion_type": "formal_model",
        "statement": (
            f"Addendum to w008-f2b rev11 finding. At the current frozen hashes C0 {c0['sha256']} and C2 "
            f"{c2['sha256']} (FROZEN rev {drift['frozen_revision']}, {drift['frozen_at']}), the rev12 "
            "rework changed the pointers, quantifier typing and revision_history but left both "
            "containment inconsistencies in place at new line numbers: "
            "implication_ledger.forbidden_transfers[0].reason calls C2 'a strictly larger extension "
            "class' although the same file's chain (line 238) makes E_C2 the smallest extension set; "
            "regularity.must_not_conflate[0] (line 151) still asserts 'No containment with C2 or C0 is "
            "asserted here' while the ledger asserts that nesting. The chain itself is concordant across "
            f"C0 and C2. A 2-edit candidate (sha256 {sha_cand}) audits PASS at the rev12 hashes with "
            "minimality verified and both single-defect controls failing for exactly one kind. "
            "Consistency finding only: no class is claimed true, refuted or closed; no gate verdict."),
        "assumptions": [
            "canonical path policy: schemas/*.yaml is authoritative and the authoring mirror is aligned at measurement time",
            "the file's own extension_class_containment sentence is the reference order; the order is not re-derived from regularity definitions",
            "the rev11/rev26 binding of the earlier events remains valid as a historical snapshot; this claim rebinds the same finding to rev12/rev27",
            "unverified artifacts; a G-FORM reviewer verdict is required before any promotion",
        ],
        "artifact_refs": [ref(path_add, sha_add), ref(path_cand, sha_cand)],
        "evidence_refs": EVID,
        "falsifier": FALSIFIER,
    },
    {
        "event_id": f"w008-f2b-{SLUG}-blocker-rev12",
        "event_type": "blocker", "created_at": TS, "actor": ACTOR,
        "node_id": NODE, "class_id": CLASS, "gate": "G-FORM",
        "description": (
            "Update to the rev11 blocker at the current freeze: the two F2b containment-consistency "
            f"defects persist in FROZEN rev {drift['frozen_revision']} (C0 {c0['sha256'][:12]}, C2 "
            f"{c2['sha256'][:12]}) at implication_ledger.forbidden_transfers[0].reason (line 245) and "
            "regularity.must_not_conflate[0] (line 151). The rev12 rework closed other findings but not "
            "these; the earlier rev11/rev26 blocker binding is now historical."),
        "needed_to_unblock": (
            f"lead-formulation: apply the two wording edits from {path_cand}#{sha_cand[:12]} (or "
            "equivalent), bump revision/revised_at, publish the authoring mirror byte-identically and "
            f"re-freeze; then re-run audit_dual_defect.py at the new hashes and confirm FAIL->PASS with "
            "the C2 chain unchanged. Reviewer: dispose in the G-FORM corpus at the frozen hash."),
        "evidence_refs": EVID,
        "stop_rule": "Repair + re-freeze + re-run to PASS; or a reviewer rules the two sentences "
                     "non-normative prose at the bound hash.",
    },
    {
        "event_id": f"w008-f2b-{SLUG}-status-rev12",
        "event_type": "status", "created_at": TS, "actor": ACTOR,
        "node_id": NODE, "class_id": CLASS, "gate": "G-FORM",
        "status": "active", "hours": 0.3,
        "summary": (
            f"Addendum complete: rev12/rev27 re-measurement (C0 {c0['sha256'][:12]}) confirms both "
            "defects persist in the current freeze; rev12-rebased 2-edit candidate "
            f"{sha_cand[:12]} PASSes with minimality and single-defect controls verified. Checkpoint "
            "runtime/state/worker-008_f2b_dualrepair_checkpoint_rev12.json. No node done, no gate "
            "verdict, no theorem."),
        "evidence_refs": EVID,
        "next_falsifier": add["falsifier"],
        "completion_scope": "worker lifecycle only; completion of one audit+rebase task, not a node done "
                            "and not a gate verdict.",
    },
]

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
with open(out, "a") as fh:
    for e in events:
        fh.write(json.dumps(e, sort_keys=True) + "\n")

instances = sorted((REPO / "runtime" / "instances").glob("worker-008-*"))
checkpoint = {
    "checkpoint_id": f"worker-008-f2b-dualrepair-rev12-{SLUG}",
    "worker": ACTOR, "instance": instances[-1].name if instances else None,
    "created_at": TS, "task_id": "W008-F2B-DUALREPAIR-01", "phase": "rev12-addendum",
    "node_id": NODE, "class_id": CLASS, "gate": "G-FORM", "status": "complete",
    "verdict": "rev12 canonical FAIL / rev12 candidate PASS",
    "bases": add["bases"], "frozen_drift": drift,
    "canonical_rev12_audit": add["canonical_rev12_audit"],
    "candidate_rev12": add["candidate_rev12"], "controls_rev12": add["controls_rev12"],
    "artifacts": {path_add: sha_add, path_cand: sha_cand,
                  "artifacts/worker-008/f2b_rev11_dualrepair/evidence/report.json":
                      sha(ROOT / "evidence" / "report.json"),
                  "artifacts/worker-008/f2b_rev11_dualrepair/audit_dual_defect.py":
                      sha(ROOT / "audit_dual_defect.py")},
    "outbox": str(out.relative_to(REPO)),
    "blocking": ["lead-formulation must repair the two sentences at the current frozen revision and "
                 "re-freeze; re-run the checker to PASS"],
    "next_falsifier": add["falsifier"],
    "completion_scope": "worker lifecycle only; no node done and no gate verdict",
}
cp = REPO / "runtime" / "state" / "worker-008_f2b_dualrepair_checkpoint_rev12.json"
cp.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
with open(REPO / "artifacts" / "worker-008" / "checkpoints.jsonl", "a") as fh:
    fh.write(json.dumps(checkpoint, sort_keys=True) + "\n")
print(json.dumps({"events_appended": len(events), "outbox": str(out.relative_to(REPO)),
                  "checkpoint": str(cp.relative_to(REPO)), "timestamp": TS, "validation": "LOCAL-SCHEMA-OK"},
                 indent=1))
