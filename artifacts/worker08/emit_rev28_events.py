#!/usr/bin/env python3
"""Emit the W008-FORMSEP04-REV28-REBIND-01 events (append-only) to
comms/outbox/deepseek-flash-08.jsonl, and write the worker checkpoint.

Idempotent: skips events whose event_id already appears in the outbox or in
research_map/events.jsonl.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CST = timezone(timedelta(hours=8))
OUTBOX = REPO / "comms" / "outbox" / "deepseek-flash-08.jsonl"
EVENTS = REPO / "research_map" / "events.jsonl"
OUT = REPO / "artifacts" / "worker08" / "rev28_live"

C2 = "schemas/af_scc_c2_vacuum.yaml"
C0 = "schemas/af_scc_c0_vacuum.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
BUNDLE = "artifacts/worker08/rev28_live/form_sep_04_rev28_bundle.json"
MTX = "artifacts/worker08/c2_c0_separation_matrix.json"
MD = "artifacts/worker08/c2_c0_separation_report.md"
DUAL = "artifacts/worker08/rev28_live/f2b_dual_defect_rev28_live.json"
SELFTEST = "artifacts/worker08/c2_c0_separation_selftest.json"
AUDITOR = "artifacts/worker08/c2_c0_separation_audit.py"

PINS = {
    C2: "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    C0: "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    FROZEN: "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
    "artifacts/formulation/rule_spec.json": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/formulation/tools/check_class_schema.py": "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    # canonical deliverables of FORM-SEP-04 refreshed to the rev28 binding
    (REPO / MTX).write_bytes((OUT / "c2_c0_separation_matrix_rev28_live.json").read_bytes())
    (REPO / MD).write_bytes((OUT / "c2_c0_separation_report_rev28_live.md").read_bytes())
    hashes = {p: sha(REPO / p) for p in (BUNDLE, MTX, MD, DUAL, SELFTEST, AUDITOR)}

    now = datetime.now(CST).isoformat(timespec="seconds")
    ev_next_falsifier = (
        "Repair both C0 sentences, re-hash, re-freeze, re-run both checkers: X3c and the "
        "dual-defect checks must go to 0/PASS at the new hash, otherwise this audit is wrong. "
        "A reviewer reading either sentence as consistent with the declared chain voids the finding."
    )
    ev = [
        {
            "event_id": "w008-rev28-20260912T0037-artifact-bundle",
            "event_type": "artifact",
            "created_at": now,
            "actor": "deepseek-flash-08",
            "worker": "worker-008",
            "group_id": "formulation",
            "node_id": "F2",
            "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
            "task_id": "W008-FORMSEP04-REV28-REBIND-01",
            "assigned_task_id": "FORM-SEP-04",
            "assignment_event_id": "assign-FORM-SEP-04-20260911T2331",
            "gate": "G-CLASSBIND",
            "artifact_type": "separation_audit_bundle",
            "path": BUNDLE,
            "sha256": hashes[BUNDLE],
            "validation_status": "unverified",
            "frozen_revision": 28,
            "audit_verdict": "FAIL",
            "hard_failure_kinds": ["containment_inversion_in_ledger", "false_containment_denial", "size_premise_inverted"],
            "inputs": PINS,
            "evidence_refs": [
                f"{C2}#{PINS[C2][:12]}",
                f"{C0}#{PINS[C0][:12]}",
                f"{FROZEN}#{PINS[FROZEN][:12]}",
                f"{AUDITOR}#{hashes[AUDITOR][:12]}",
            ],
            "falsifier": "A rev28+ reading under which either flagged sentence is consistent with the declared chain E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2; a canonical C0 hash other than 55d0a1ea at which these findings vanish; or a bundle field that does not match the named artifact bytes.",
        },
        {
            "event_id": "w008-rev28-20260912T0037-artifact-matrix",
            "event_type": "artifact",
            "created_at": now,
            "actor": "deepseek-flash-08",
            "worker": "worker-008",
            "group_id": "formulation",
            "node_id": "F2",
            "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
            "task_id": "W008-FORMSEP04-REV28-REBIND-01",
            "assigned_task_id": "FORM-SEP-04",
            "gate": "G-CLASSBIND",
            "artifact_type": "separation_audit",
            "path": MTX,
            "sha256": hashes[MTX],
            "validation_status": "unverified",
            "frozen_revision": 28,
            "audit_verdict": "FAIL",
            "X1_expectation_violations": 0,
            "X2_unjustified": 0,
            "X2b_axis_violations": 0,
            "X3_converse_assertions": 0,
            "X3c_containment_inversions": 1,
            "X4_violations": 0,
            "inputs": PINS,
            "evidence_refs": [
                f"{C0}#{PINS[C0][:12]}",
                f"{C2}#{PINS[C2][:12]}",
                f"{MTX}#{hashes[MTX][:12]}",
                f"{MD}#{hashes[MD][:12]}",
                "schemas/af_scc_c0_vacuum.yaml:245",
            ],
            "falsifier": "Any placement where the C2 conclusion is satisfied by a C0-only extension class or vice versa; any Cx => Cy converse prose; any composite/foreign regularity token in an assertive conclusion field; any containment premise calling C2 larger or C0 smaller. Each reopens FAIL at the bound hash.",
        },
        {
            "event_id": "w008-rev28-20260912T0037-artifact-report",
            "event_type": "artifact",
            "created_at": now,
            "actor": "deepseek-flash-08",
            "worker": "worker-008",
            "group_id": "formulation",
            "node_id": "F2",
            "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
            "task_id": "W008-FORMSEP04-REV28-REBIND-01",
            "assigned_task_id": "FORM-SEP-04",
            "gate": "G-CLASSBIND",
            "artifact_type": "separation_audit_report",
            "path": MD,
            "sha256": hashes[MD],
            "validation_status": "unverified",
            "frozen_revision": 28,
            "evidence_refs": [f"{MTX}#{hashes[MTX][:12]}", f"{MD}#{hashes[MD][:12]}"],
            "falsifier": "A report statement not backed by the bound matrix at the named hashes.",
        },
        {
            "event_id": "w008-rev28-20260912T0037-artifact-dualdefect",
            "event_type": "artifact",
            "created_at": now,
            "actor": "deepseek-flash-08",
            "worker": "worker-008",
            "group_id": "formulation",
            "node_id": "F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
            "task_id": "W008-FORMSEP04-REV28-REBIND-01",
            "gate": "G-FORM",
            "artifact_type": "containment_consistency_audit",
            "path": DUAL,
            "sha256": hashes[DUAL],
            "validation_status": "unverified",
            "frozen_revision": 28,
            "verdict": "FAIL",
            "finding_kinds": ["false_containment_denial", "size_premise_inverted"],
            "inputs": PINS,
            "evidence_refs": [
                f"{C0}#{PINS[C0][:12]}",
                f"{C2}#{PINS[C2][:12]}",
                f"{DUAL}#{hashes[DUAL][:12]}",
                "schemas/af_scc_c0_vacuum.yaml:151",
                "schemas/af_scc_c0_vacuum.yaml:245",
            ],
            "falsifier": "Either flagged C0 sentence is consistent with the declared containment chain, or the chain itself (line 238 / C2 line 236) is wrong; the latter would invalidate the schemas' own containment claim.",
        },
        {
            "event_id": "w008-rev28-20260912T0037-status",
            "event_type": "status",
            "created_at": now,
            "actor": "deepseek-flash-08",
            "worker": "worker-008",
            "group_id": "formulation",
            "node_id": "F2",
            "status": "active",
            "hours": 0.4,
            "task_id": "W008-FORMSEP04-REV28-REBIND-01",
            "assigned_task_id": "FORM-SEP-04",
            "summary": (
                "FORM-SEP-04 re-bound from FROZEN rev25 (C2 b6123750 / C0 1bb78ce9) to the live "
                "FROZEN rev28 pair (C2 5476a3f2c6bc / C0 55d0a1ea9bda; FROZEN.json 2f358f6722d9, "
                "verify_frozen 44 pins / 0 mismatches, canonical == authoring mirror byte-for-byte). "
                "Gate run recorded (check_class_schema.py: PASS/pass, exit 0 for both). Separation "
                "axes clean: X1 expectation violations 0, X2 unjustified 0, X2b axis 0, X3 converse 0, "
                "X3 unclassified 0, X4 composite violations 0. Verdict FAIL on containment consistency: "
                "the rev12 rewrite did NOT repair the two defects requested at the rev19/rev25 bindings. "
                "(1) C0 implication_ledger.forbidden_transfers[0].reason (line 245) still calls C2 'a "
                "strictly larger extension class', contradicting the same file's line-238 chain "
                "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2 and line-248 'C0-inextendibility "
                "is stronger'; only the premise clause is inverted, the forbidden direction is correct. "
                "(2) C0 regularity.must_not_conflate[0] (line 151) still denies any containment with C2 "
                "or C0 for H2_loc, which the declared chain contradicts. Independent second checker "
                "(F2b dual-defect, fail-closed, expect-hash-guarded) reproduces both kinds at the same "
                "pins: FAIL, 3 findings. Reports only; no node completion, no gate verdict; G-CLASSBIND "
                "and G-FORM remain lead/controller-owned. Interpretation owned by astra-lead-formulation."
            ),
            "verdict": "FAIL",
            "hard_failure_kinds": ["containment_inversion_in_ledger", "false_containment_denial", "size_premise_inverted"],
            "evidence_refs": [
                f"{BUNDLE}#{hashes[BUNDLE][:12]}",
                f"{MTX}#{hashes[MTX][:12]}",
                f"{MD}#{hashes[MD][:12]}",
                f"{DUAL}#{hashes[DUAL][:12]}",
                f"{C0}#{PINS[C0][:12]}",
                f"{C2}#{PINS[C2][:12]}",
                f"{FROZEN}#{PINS[FROZEN][:12]}",
                "schemas/af_scc_c0_vacuum.yaml:151",
                "schemas/af_scc_c0_vacuum.yaml:238",
                "schemas/af_scc_c0_vacuum.yaml:245",
                "schemas/af_scc_c0_vacuum.yaml:248",
                "schemas/af_scc_c2_vacuum.yaml:236",
            ],
            "blocker_ref": "w008-rev28-20260912T0037-blocker",
            "next_falsifier": ev_next_falsifier,
        },
        {
            "event_id": "w008-rev28-20260912T0037-blocker",
            "event_type": "blocker",
            "created_at": now,
            "actor": "deepseek-flash-08",
            "worker": "worker-008",
            "group_id": "formulation",
            "node_id": "F2",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
            "description": (
                "At FROZEN revision 28 (C0 55d0a1ea9bda, C2 5476a3f2c6bc) the C0 schema carries two "
                "containment-consistency defects that survived the rev12 rewrite. Exact paths: "
                "(a) implication_ledger.forbidden_transfers[0].reason (line 245): 'C2 is a strictly "
                "larger extension class, so C2-inextendibility is strictly weaker' inverts the size "
                "premise of the file's own extension_class_containment (line 238) and one_way_entailments "
                "(line 248); the C2 schema states the same containment at line 236. (b) "
                "regularity.must_not_conflate[0] (line 151): 'No containment with C2 or C0 is asserted "
                "here' denies the H2_loc containment that line 238 declares. Both checkers agree: "
                "FORM-SEP-04 v3 FAIL (containment_inversion_in_ledger x1) and the F2b fail-closed "
                "dual-defect checker FAIL (size_premise_inverted x1 + false_containment_denial x2). "
                "Structural gate check_class_schema.py passes both schemas, so this is invisible to the "
                "structural gate alone."
            ),
            "needed_to_unblock": (
                "Lead-formulation: two wording-only repairs at the exact paths (line 151 drop/qualify "
                "the no-containment denial; line 245 'strictly larger' -> 'strictly smaller (E_C2 subset "
                "of E_C0)'), then re-hash, re-freeze (rev29), and re-run artifacts/worker08/rebind_rev28.py; "
                "FORM-SEP-04 X3c and the dual-defect checks must read 0/PASS at the new hash."
            ),
            "evidence_refs": [
                f"{BUNDLE}#{hashes[BUNDLE][:12]}",
                f"{MTX}#{hashes[MTX][:12]}",
                f"{DUAL}#{hashes[DUAL][:12]}",
                f"{C0}#{PINS[C0][:12]}",
                f"{C2}#{PINS[C2][:12]}",
                f"{FROZEN}#{PINS[FROZEN][:12]}",
                "schemas/af_scc_c0_vacuum.yaml:151",
                "schemas/af_scc_c0_vacuum.yaml:238",
                "schemas/af_scc_c0_vacuum.yaml:245",
                "schemas/af_scc_c0_vacuum.yaml:248",
                "schemas/af_scc_c2_vacuum.yaml:236",
            ],
            "falsifier": (
                "Either sentence is shown consistent with the declared chain (e.g. 'larger' is read as "
                "'higher regularity', a reading lines 151/238/248 do not support), or the declared chain "
                "is itself wrong (which would invalidate the schemas' own separation claim)."
            ),
            "stop_rule": "Repair + re-freeze + re-run both checkers; or a reviewer rules both sentences non-normative prose.",
        },
        {
            "event_id": "w008-rev28-20260912T0039-status-classbound",
            "event_type": "status",
            "created_at": now,
            "actor": "deepseek-flash-08",
            "worker": "worker-008",
            "group_id": "formulation",
            "node_id": "F2",
            "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
            "status": "active",
            "hours": 0.05,
            "task_id": "W008-FORMSEP04-REV28-REBIND-01",
            "assigned_task_id": "FORM-SEP-04",
            "summary": (
                "Class-binding addendum to w008-rev28-20260912T0037-status (same measurement, no new "
                "content): the FORM-SEP-04 status event is explicitly bound to class_ids "
                "AF-SCC-C2-VAC-GEN and AF-SCC-C0-VAC-GEN, node F2, gate G-CLASSBIND. The rev28 rebind "
                "driver (artifacts/worker08/rebind_rev28.py) ran at the four pins recorded in the "
                "bundle; verdict FAIL on containment consistency as stated there."
            ),
            "verdict": "FAIL",
            "evidence_refs": [
                f"{BUNDLE}#{hashes[BUNDLE][:12]}",
                f"{MTX}#{hashes[MTX][:12]}",
                f"{DUAL}#{hashes[DUAL][:12]}",
                f"{C0}#{PINS[C0][:12]}",
                f"{C2}#{PINS[C2][:12]}",
                f"{FROZEN}#{PINS[FROZEN][:12]}",
            ],
            "blocker_ref": "w008-rev28-20260912T0037-blocker",
            "next_falsifier": ev_next_falsifier,
        },
    ]

    seen = set()
    for p in (OUTBOX, EVENTS):
        if p.exists():
            for line in p.read_text(errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    seen.add(json.loads(line).get("event_id"))
                except Exception:
                    pass
    fresh = [e for e in ev if e["event_id"] not in seen]
    with OUTBOX.open("a") as f:
        for e in fresh:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    ckpt = {
        "checkpoint_id": "worker-008-formsep04-rev28-20260912T0039+0800-final",
        "worker": "worker-008",
        "agent_id": "deepseek-flash-08",
        "task_id": "W008-FORMSEP04-REV28-REBIND-01",
        "assigned_task_id": "FORM-SEP-04",
        "node_id": "F2",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-CLASSBIND",
        "status": "complete",
        "completion_scope": "worker lifecycle only; no node done, no gate verdict",
        "created_at": now,
        "bases": {"c0": {C0: PINS[C0]}, "c2": {C2: PINS[C2]}, "frozen": {FROZEN: PINS[FROZEN]}},
        "artifacts": hashes,
        "verdict": "FAIL",
        "hard_failure_kinds": ["containment_inversion_in_ledger", "false_containment_denial", "size_premise_inverted"],
        "events_emitted_this_run": [e["event_id"] for e in fresh],
        "events_total_for_task": [e["event_id"] for e in ev],
        "events_already_present": [e["event_id"] for e in ev if e["event_id"] in seen],
        "outbox": "comms/outbox/deepseek-flash-08.jsonl",
        "next_falsifier": ev_next_falsifier,
        "blocking": ["astra-lead-formulation must repair both C0 sentences, re-freeze, and re-run the rebind driver"],
    }
    ckp = REPO / "runtime" / "state" / "worker-008_formsep04_rev28_checkpoint_final.json"
    ckp.write_text(json.dumps(ckpt, indent=1, sort_keys=True) + "\n")
    with (REPO / "runtime" / "state" / "worker-008_checkpoints.jsonl").open("a") as f:
        f.write(json.dumps({"checkpoint_id": ckpt["checkpoint_id"], "created_at": now,
                            "task_id": ckpt["task_id"], "verdict": "FAIL",
                            "checkpoint_sha256": sha(ckp)}) + "\n")

    print(json.dumps({"emitted": [e["event_id"] for e in fresh],
                      "checkpoint": str(ckp.relative_to(REPO)), "checkpoint_sha256": sha(ckp),
                      "artifacts": hashes}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
