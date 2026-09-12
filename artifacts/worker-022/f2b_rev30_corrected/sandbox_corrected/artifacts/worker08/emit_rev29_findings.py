#!/usr/bin/env python3
"""W008-FORMSEP04-REVREBIND-01 rev29 findings emitter (bounded, single transaction).

Writes:
  artifacts/worker08/rev29_findings.json                     (evidence record)
  runtime/state/worker-008_rev_rebind_checkpoint_rev29.json  (worker checkpoint)
  comms/outbox/deepseek-flash-08.jsonl                       (+1 artifact, +1 status)

The status event supersedes w008-formsep04-20260912T005348+0800-status, which was
written before FROZEN rev29 landed. No new blocker is filed: the persisting C0
content defect is the owner-disclosed L-FORM-01 (astra-lead-formulation,
00:57:43), and my binding blocker w008-rev28-20260912T0037-blocker still tracks it.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CST = timezone(timedelta(hours=8))
TS = datetime.now(CST)
ART = "artifacts/worker08"
STATE = "runtime/state"
OUTBOX = REPO / "comms" / "outbox" / "deepseek-flash-08.jsonl"
EVENTS = REPO / "research_map" / "events.jsonl"


def sha_rel(rel: str) -> str:
    return hashlib.sha256((REPO / rel).read_bytes()).hexdigest()


def existing_ids() -> set[str]:
    ids = set()
    for p in (OUTBOX, EVENTS):
        if not p.exists():
            continue
        for line in p.read_text(errors="ignore").splitlines():
            if '"event_id"' in line:
                try:
                    ids.add(json.loads(line)["event_id"])
                except Exception:
                    pass
    return ids


def main() -> int:
    stamp = TS.strftime("%Y%m%dT%H%M%S%z")
    frozen = json.loads((REPO / "artifacts/formulation/FROZEN.json").read_text())
    tool_rel = f"{ART}/rev_rebind.py"
    prerepair_rel = f"{ART}/rev_rebind_rev28.json"
    run1_rel = f"{ART}/rev_rebind_rev29_run1.json"
    final_rel = f"{ART}/rev_rebind_rev29.json"
    controls_rel = f"{ART}/rev_rebind_controls.json"
    findings_rel = f"{ART}/rev29_findings.json"
    checkpoint_rel = f"{STATE}/worker-008_rev_rebind_checkpoint_rev29.json"

    run1 = json.loads((REPO / run1_rel).read_text())
    final = json.loads((REPO / final_rel).read_text())
    if final["frozen_revision"] != 29 or run1["pins"]["F2b"] != final["pins"]["F2b"]:
        print("refusing: final bundle is not the stable rev29 measurement", file=sys.stderr)
        return 2

    findings = {
        "record_id": "w008-formsep04-rev29-findings",
        "task_id": "W008-FORMSEP04-REVREBIND-01",
        "assigned_task_id": "FORM-SEP-04",
        "assignment_event_id": "assign-FORM-SEP-04-20260911T2331",
        "actor": "worker-008",
        "agent_id": "deepseek-flash-08",
        "node_id": "F2",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-CLASSBIND",
        "created_at": TS.isoformat(timespec="seconds"),
        "harness": {"path": tool_rel, "sha256": sha_rel(tool_rel)},
        "final_state": {
            "frozen_revision": 29,
            "frozen_frozen_at": frozen.get("frozen_at"),
            "frozen_manifest_sha256": sha_rel("artifacts/formulation/FROZEN.json"),
            "frozen_pinned_files": len(frozen.get("files", {})),
            "schemas": {"F2b_c0": final["pins"]["F2b"], "F2a_c2": final["pins"]["F2a"],
                        "F1": final["pins"]["F1"]},
            "checks": {k: v["result"] for k, v in final["checks"].items()},
            "verdict": final["verdict"],
            "residual_is_content_only": (
                final["checks"]["frozen_pin_binding"]["result"] == "PASS"
                and final["checks"]["canonical_mirror_byte_equality"]["result"] == "PASS"
                and final["checks"]["verify_frozen"]["result"] == "PASS"
                and final["checks"]["form_sep_04_audit"]["result"] == "FAIL"
                and final["checks"]["f2b_dual_defect"]["result"] == "FAIL"
            ),
            "verify_frozen_output_tail": final["checks"]["verify_frozen"]["output_tail"],
            "form_sep_04_X3c_violations": final["checks"]["form_sep_04_audit"]["X3c_violations"],
            "form_sep_04_hard_failures": final["checks"]["form_sep_04_audit"]["hard_failures"],
            "dual_findings": final["checks"]["f2b_dual_defect"]["findings"],
        },
        "findings": [
            {
                "id": "W008-REV29-F1",
                "novelty": "corroboration of owner-disclosed L-FORM-01 (astra-lead-formulation 00:57:43) and of the earlier worker-008/080/058/060 reproductions; NOT filed as a new blocker",
                "statement": (
                    "At the final rev29 pins (C0 b2ab6acb2bbe) the two C0 containment defects persist: "
                    "regularity.must_not_conflate[0] line 152 still denies containment with C2/C0, and "
                    "implication_ledger.forbidden_transfers[0].reason line 246 still calls C2 a strictly "
                    "larger extension class. FORM-SEP-04 X3c = 1; dual checker = 3 findings / 2 kinds. "
                    "All binding checks (FROZEN pin, canonical==mirror, verify_frozen 50 files 0 problems) "
                    "PASS, so the rev29 residual is content-only: the dispatched rev29 verification round "
                    "cannot produce clean F2b accepts."
                ),
                "evidence_refs": [
                    f"{final_rel}#{sha_rel(final_rel)[:12]}",
                    f"{'artifacts/formulation/FROZEN.json'}#{sha_rel('artifacts/formulation/FROZEN.json')[:12]}",
                    "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
                    "schemas/af_scc_c0_vacuum.yaml:152",
                    "schemas/af_scc_c0_vacuum.yaml:246",
                ],
            },
            {
                "id": "W008-REV29-F2",
                "novelty": "new process observation at hash level",
                "statement": (
                    "The revision label 29 was carried by at least three distinct FROZEN manifests within "
                    "~3 minutes: frozen_at 00:54:32 (bytes not captured), frozen_at 00:55:02 "
                    "(sha 3d9e3d77fd87, 48 pins), frozen_at 00:57:26 (final, 50 pins). Against the "
                    "00:55:02 manifest verify_frozen.py failed on a moving drift set: 1 file at 00:56:31 "
                    "(evidence/variant_delta_check.json fc6ee058dd96 -> 0b23f0b29232), 3 files at 00:57:08 "
                    "(VARIANT_REGISTRY 5eb42f9a384a -> 6bac9adea19e; variant-CH delta c28795b0fdfc -> "
                    "7c165a9063c6; variant-SET delta 45b9b6a8d192 -> 64b8d6394a04), 4 files at 00:57:15 "
                    "(+ evidence_binding_repair_rev29_report f337f83e483c -> 3379bcfb8421). Consequence: a "
                    "verdict recorded as 'rev29' without a FROZEN or schema hash pin inside that window is "
                    "ambiguous. The schema hashes themselves were stable across every rev29 manifest "
                    "(b2ab6acb2bbe / e9a27996dfd3 / d9cebb9404b2), so verdicts pinned to those schema "
                    "hashes stay well-posed."
                ),
                "evidence_refs": [
                    f"{run1_rel}#{sha_rel(run1_rel)[:12]}",
                    f"{final_rel}#{sha_rel(final_rel)[:12]}",
                    "artifacts/formulation/FROZEN.json#3d9e3d77fd87",
                    f"{'artifacts/formulation/FROZEN.json'}#{sha_rel('artifacts/formulation/FROZEN.json')[:12]}",
                ],
            },
            {
                "id": "W008-REV29-F3",
                "novelty": "new process observation",
                "statement": (
                    "Freeze-breach window at the rev28 -> rev29 transition: the canonical schemas were "
                    "rewritten at 00:53:20 (C0/C2) and 00:53:40 (F1) while FROZEN.json still declared "
                    "revision 28 with the old pins (C0 55d0a1ea9bda etc.) until rev29 appeared at "
                    "00:54:32, i.e. ~72 s in which live canonical bytes did not match the declared "
                    "manifest. My own earlier bundle bytes were measured inside that window and are "
                    "therefore bound to the pre-repair rev28 pins only, not to rev29."
                ),
                "evidence_refs": [
                    f"{prerepair_rel}#{sha_rel(prerepair_rel)[:12]}",
                    "schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda",
                    "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
                ],
            },
        ],
        "controls": {
            "prerepair_sensitivity_rev28": "FAIL (X3c 1, dual 2 kinds) — harness does not pass unrepaired bytes",
            "wrong_expect_hash": "dual checker FAIL-CLOSED exit 3, no verdict",
            "repair_candidate_sensitivity": "candidate 98f9ec83 -> dual PASS 0 findings, audit PASS X3c 0",
            "rev29_reproducibility": "run1 00:56:31 and run2 00:57:08 identical finding sets (X3c 1; lines 152/152/246)",
            "controls_record": f"{controls_rel}#{sha_rel(controls_rel)[:12]}",
        },
        "recommendation": (
            "Bind the dispatched rev29 verdicts to the schema hashes b2ab6acb2bbe / e9a27996dfd3 / "
            "d9cebb9404b2, not to the revision label; keep F2b at revise until the two C0 leaf fields "
            "are repaired; re-run artifacts/worker08/rev_rebind.py --label post-content-repair after the "
            "content fix (expect overall PASS with X3c 0 and dual finding_kinds [])."
        ),
        "falsifier": (
            "A measurement at C0 b2ab6acb2bbe whose X3c count is 0 or whose dual finding set is empty; "
            "a rev29 FROZEN manifest other than the two hashes named here with no drift; or a verdict at "
            "the 00:55:02 manifest that nonetheless cites stable schema hashes. Any of these voids the "
            "corresponding finding, not the harness."
        ),
        "authority": (
            "Worker-level measurement only; no node completion, no gate verdict, no validation promotion. "
            "Interpretation owned by astra-lead-formulation; process findings for the controller audit."
        ),
    }
    (REPO / findings_rel).write_text(json.dumps(findings, indent=1, sort_keys=True) + "\n",
                                     encoding="utf-8")

    checkpoint = {
        "checkpoint_id": f"ckpt-w008-revrebind-rev29-{stamp}",
        "task_id": "W008-FORMSEP04-REVREBIND-01",
        "assigned_task_id": "FORM-SEP-04",
        "actor": "worker-008",
        "agent_id": "deepseek-flash-08",
        "node_id": "F2",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-CLASSBIND",
        "created_at": TS.isoformat(timespec="seconds"),
        "worker_hours_approx": 0.5,
        "status": "blocked-owner-content-repair",
        "state": {
            "frozen_revision": 29,
            "frozen_manifest_sha256": sha_rel("artifacts/formulation/FROZEN.json"),
            "c0_live_sha256": final["pins"]["F2b"],
            "c2_live_sha256": final["pins"]["F2a"],
            "f1_live_sha256": final["pins"]["F1"],
            "binding_checks": "PASS (pin binding, canonical==mirror, verify_frozen 50 files 0 problems)",
            "content_checks": "FAIL (X3c 1; dual 3 findings / 2 kinds at C0 lines 152, 246)",
            "binding_fixed_at_rev29": True,
            "content_repaired": False,
        },
        "blocker_refs": [
            "w008-rev28-20260912T0037-blocker",
            "lead-form-20260912T005743-91 (L-FORM-01, owner-disclosed)",
        ],
        "blocker_note": (
            "No duplicate blocker emitted. The binding part of my rev28 blocker is discharged at rev29 "
            "(pin binding and verify_frozen now pass); the content part persists and is owner-tracked."
        ),
        "deliverables": {
            tool_rel: sha_rel(tool_rel),
            prerepair_rel: sha_rel(prerepair_rel),
            run1_rel: sha_rel(run1_rel),
            final_rel: sha_rel(final_rel),
            controls_rel: sha_rel(controls_rel),
            findings_rel: sha_rel(findings_rel),
        },
        "next_action": {
            "trigger": "the two C0 leaf fields repaired and re-frozen",
            "command": f"python3 {tool_rel} --label post-content-repair",
            "acceptance": "overall PASS, X3c 0, dual finding_kinds []",
        },
        "falsifier": findings["falsifier"],
        "authority": findings["authority"],
    }
    (REPO / checkpoint_rel).write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n",
                                       encoding="utf-8")

    superseded = "w008-formsep04-20260912T005348+0800-status"
    ev_art = f"w008-formsep04-{stamp}-artifact-rev29-findings"
    ev_st = f"w008-formsep04-{stamp}-status-rev29"
    for e in (ev_art, ev_st):
        if e in existing_ids():
            print(f"event_id exists: {e}", file=sys.stderr)
            return 2

    refs = [
        f"schemas/af_scc_c0_vacuum.yaml#{final['pins']['F2b'][:12]}",
        f"schemas/af_scc_c2_vacuum.yaml#{final['pins']['F2a'][:12]}",
        f"artifacts/formulation/FROZEN.json#{sha_rel('artifacts/formulation/FROZEN.json')[:12]}",
        f"{final_rel}#{sha_rel(final_rel)[:12]}",
        f"{run1_rel}#{sha_rel(run1_rel)[:12]}",
        f"{findings_rel}#{sha_rel(findings_rel)[:12]}",
        "schemas/af_scc_c0_vacuum.yaml:152",
        "schemas/af_scc_c0_vacuum.yaml:246",
    ]
    common = {
        "created_at": TS.isoformat(timespec="seconds"),
        "actor": "worker-008",
        "agent_slot": "worker-008",
        "agent_id": "deepseek-flash-08",
        "node_id": "F2",
        "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-CLASSBIND",
        "authority_note": findings["authority"],
    }
    events = [
        dict(common, event_id=ev_art, event_type="artifact", artifact_type="evidence",
             path=findings_rel, sha256=sha_rel(findings_rel), validation_status="unverified",
             summary=(
                 "Post-repair re-bind measurement at FROZEN rev29: binding checks PASS (verify_frozen 50 "
                 "files 0 problems) but FORM-SEP-04 X3c=1 and dual=3 findings at C0 lines 152/246, so the "
                 "rev29 residual is content-only (owner-disclosed L-FORM-01). Also records the "
                 "revision-29 manifest ambiguity window (three manifests; verify_frozen drift 1->4 files) "
                 "and the 72 s rev28->29 freeze-breach window."
             ),
             evidence_refs=refs, falsifier=findings["falsifier"]),
        dict(common, event_id=ev_st, event_type="status", status="blocked", hours=0.5,
             supersedes=superseded,
             summary=(
                 f"CHECKPOINT + EXIT (supersedes {superseded}, which predated the rev29 freeze). "
                 f"Rev-agnostic harness delivered and validated at two revisions: rev28 prerepair FAIL, "
                 f"rev29 post-repair FAIL with binding checks PASS and both content checkers FAIL "
                 f"(X3c 1; lines 152/246). Binding blocker discharged; content residual is owner-tracked "
                 f"L-FORM-01, so no duplicate blocker filed. Process observations: rev29 label covered "
                 f"three FROZEN manifests within 3 min (verify_frozen drift 1->4 files on the 00:55:02 "
                 f"manifest), and a 72 s rev28->29 breach window. Next: re-run rev_rebind.py after the "
                 f"content repair; acceptance overall PASS. Checkpoint: {checkpoint_rel}."
             ),
             evidence_refs=refs + [f"{checkpoint_rel}#{sha_rel(checkpoint_rel)[:12]}",
                                   f"{controls_rel}#{sha_rel(controls_rel)[:12]}"],
             next_falsifier=findings["falsifier"],
             checkpoint_ref=f"{checkpoint_rel}#{sha_rel(checkpoint_rel)[:12]}"),
    ]

    import re as _re
    required = {
        "artifact": ["event_id", "event_type", "created_at", "actor", "node_id", "artifact_type",
                     "path", "sha256", "validation_status"],
        "status": ["event_id", "event_type", "created_at", "actor", "node_id", "status", "summary"],
    }
    lines = []
    for e in events:
        for k in required[e["event_type"]]:
            if e.get(k) in (None, ""):
                print(f"event {e['event_id']} missing {k}", file=sys.stderr)
                return 2
        for r in e["evidence_refs"]:
            if not (_re.search(r"#[0-9a-f]{6,}$", r) or _re.search(r":\d+(-\d+)?$", r)):
                print(f"event {e['event_id']} unpinned evidence_ref {r}", file=sys.stderr)
                return 2
        lines.append(json.dumps(e, sort_keys=True))
    with OUTBOX.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(json.dumps({
        "events_written": [e["event_id"] for e in events],
        "findings": f"{findings_rel}#{sha_rel(findings_rel)[:12]}",
        "checkpoint": f"{checkpoint_rel}#{sha_rel(checkpoint_rel)[:12]}",
        "final_verdict": final["verdict"],
        "residual_is_content_only": findings["final_state"]["residual_is_content_only"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
