#!/usr/bin/env python3
"""Emit worker-05 F2a audit events to comms/outbox/deepseek-flash-05.jsonl.

Fail-closed: re-hashes the cited artifacts and refuses to emit if a pinned hash drifted.
Validates every event with research_map/schemas.validate_event before appending.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

OUTBOX = ROOT / "comms/outbox/deepseek-flash-05.jsonl"
AUDIT = ROOT / "artifacts/worker-05/verify/f2a_candidate_audit.json"
AUDIT_MD = ROOT / "artifacts/worker-05/F2A_CANDIDATE_AUDIT.md"
HARNESS = ROOT / "artifacts/worker-05/verify/make_f2a_audit.py"
PUBLISHED_C2 = ROOT / "schemas/af_scc_c2_vacuum.yaml"
PUBLISHED_C0 = ROOT / "schemas/af_scc_c0_vacuum.yaml"
PUBLISHED_WCC = ROOT / "schemas/af_wcc_vacuum.yaml"

PINNED = {
    PUBLISHED_C2: "8dae50da1ab595577c38587c2eb9841d1b4b5d75d22adb117f917a88d6af825f",
    PUBLISHED_C0: "a8d899d2941fa5b61a536b05dd513378150121805e3684409d505b508fecec1f",
    PUBLISHED_WCC: "b65fcc0f0118980fe50b4a5eaf5fb637f4f744d0db095105fd8031db1dabcd94",
}
CST = timezone(timedelta(hours=8))


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    drift = {str(p.relative_to(ROOT)): {"pinned": v, "on_disk": sha(p)}
             for p, v in PINNED.items() if sha(p) != v}
    if drift:
        print("DRIFT DETECTED — audit invalid, re-run make_f2a_audit.py:", json.dumps(drift, indent=1))
        return 2

    h_audit, h_md, h_harness = sha(AUDIT), sha(AUDIT_MD), sha(HARNESS)
    now = datetime.now(CST)
    stamp = now.strftime("%Y%m%dT%H%M%S")
    created = now.isoformat(timespec="seconds")
    ev = f"w05-f2a-audit-{stamp}"

    art = f"artifacts/worker-05/verify/f2a_candidate_audit.json#{h_audit[:12]}"
    evidence = [
        art,
        "schemas/af_scc_c2_vacuum.yaml#8dae50da1ab5",
        "schemas/af_scc_c0_vacuum.yaml#a8d899d2941f",
        "schemas/af_wcc_vacuum.yaml#b65fcc0f0118",
        "schemas/af_scc_c2_vacuum.yaml#23fec0e9cd68 (pre-publication rev3, body superseded)",
        "artifacts/formulation/tools/check_class_schema.py#000e09e46b2f",
        "artifacts/worker18/f2_review/f2_class_probe.py#7502f79f333d",
        "reviews/F2a-review-18.json",
        "reviews/F2a-review-17.json",
    ]

    events = [
        {
            "event_id": f"{ev}-artifact",
            "event_type": "artifact",
            "created_at": created,
            "actor": "deepseek-flash-05",
            "agent_slot": "worker-05",
            "group_id": "formulation",
            "node_id": "F2a",
            "class_id": "AF-SCC-C2-VAC-GEN",
            "artifact_type": "verification_audit",
            "path": "artifacts/worker-05/verify/f2a_candidate_audit.json",
            "sha256": h_audit,
            "validation_status": "unverified",
            "companion_artifacts": {
                "summary_md": {"path": "artifacts/worker-05/F2A_CANDIDATE_AUDIT.md", "sha256": h_md},
                "harness": {"path": "artifacts/worker-05/verify/make_f2a_audit.py", "sha256": h_harness},
            },
            "evidence_refs": evidence,
            "note": ("independent closure audit of F2a: published rev9 8dae50da passes the frozen "
                     "binding gate and closes review-18 HF-A1/HF-A4; S6-C2 (forall (s,delta) D0 "
                     "family binder) and the S5 prohibition-phrase token remain; no verdict at hash"),
            "next_falsifier": ("any sha256 change to schemas/af_scc_c2_vacuum.yaml invalidates this audit; "
                               "S6 closes on a lead/reviewer ruling; S5 clears on rewording"),
        },
        {
            "event_id": f"{ev}-status",
            "event_type": "status",
            "created_at": created,
            "actor": "deepseek-flash-05",
            "agent_slot": "worker-05",
            "group_id": "formulation",
            "node_id": "F2a",
            "class_id": "AF-SCC-C2-VAC-GEN",
            "status": "active",
            "hours": 0.5,
            "summary": (
                "Bounded worker-05 audited class AF-SCC-C2-VAC-GEN. Observed the lead publish "
                "schemas/af_scc_c2_vacuum.yaml at 00:10:15 from 23fec0e9 (rev3, frozen gate FAIL "
                "R17,R18,R19,R22,R27; probe S6-C2+S7-C2) to 8dae50da (rev9, gate PASS). Independently "
                "re-ran the frozen binding gate and reviewer-18's adversarial probe on the published "
                "hash: HF-A1 (dangling extension_predicate) and HF-A4 (gate rejection) are closed; "
                "HF-A2 stays OPEN because rev9 still quantifies forall (s,delta) in D0 (probe S6-C2, "
                "family of statements; the gate does not encode S6); HF-A3 is met only as a family "
                "across the three published rev9 schemas, not as one frozen (s,delta). Probe S5-C2/S5-C0 "
                "fire on the prohibition phrase \"any 'C0 or C2' composite regularity\" under "
                "phrases_that_are_not_this_class (gate R13 exempts the key); adjudicated prohibition-only, "
                "one-line rewording clears it. No review verdict exists at 8dae50da: reviews/F2a-review-17 "
                "and -18 are pinned to the superseded rev3."
            ),
            "evidence_refs": evidence,
            "next_falsifier": (
                "a new revision at schemas/af_scc_c2_vacuum.yaml (sha change) or a reviewer verdict at "
                "8dae50da; S6 stays open until D0 is frozen to one (s,delta) or the family reading is "
                "explicitly accepted by the lead/reviewers"
            ),
        },
        {
            "event_id": f"{ev}-blocker",
            "event_type": "blocker",
            "created_at": created,
            "actor": "deepseek-flash-05",
            "agent_slot": "worker-05",
            "group_id": "formulation",
            "node_id": "F2a",
            "class_id": "AF-SCC-C2-VAC-GEN",
            "description": (
                "G-FORM cannot close F2a at published hash 8dae50da yet: (1) probe S6-C2, "
                "forall (s,delta) in D0 makes the artifact a family of class statements unless one "
                "regularity pair is frozen or the family reading is explicitly accepted; (2) no "
                "independent accept verdict exists at the published hash (both F2a verdicts are "
                "pinned to superseded rev3 23fec0e9); (3) probe S5-C2 fires on the prohibition "
                "phrase \"any 'C0 or C2' composite regularity\" although gate R13 exempts the key."
            ),
            "needed_to_unblock": (
                "lead-formulation rules on D0 (freeze one (s,delta) or record the family reading); "
                "rewording of the S5 prohibition phrase; then reviewers 17/18 (or two independent "
                "reviewers) re-issue verdicts pinned to the frozen published sha256"
            ),
            "evidence_refs": evidence,
            "next_falsifier": (
                "a D0 ruling plus two accept verdicts at one published hash closes this blocker; a "
                "further revision reopens it"
            ),
        },
    ]

    for e in events:
        validate_event(e)  # raises SchemaError on contract violation

    with OUTBOX.open("a") as fh:
        for e in events:
            fh.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"appended {len(events)} validated events to {OUTBOX.relative_to(ROOT)}")
    for e in events:
        print(" ", e["event_type"], e["event_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
