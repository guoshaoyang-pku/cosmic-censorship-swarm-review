#!/usr/bin/env python3
"""W008-FORMSEP04-REVREBIND-01 emitter.

One bounded worker transaction:
  1. hash the new deliverables (rev_bind driver, bundle, checker outputs);
  2. write the controls record and the worker checkpoint;
  3. append one `artifact` event per deliverable class and one `status` event to
     comms/outbox/deepseek-flash-08.jsonl (my assigned downward channel);
  4. validate every emitted line parses and carries the required fields, and stop
     without writing if any event_id already exists in the outbox or the accepted
     stream.

Read-only with respect to canonical artifacts and to the map. No node status, no
gate verdict, no validation promotion.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CST = timezone(timedelta(hours=8))
OUTBOX = REPO / "comms" / "outbox" / "deepseek-flash-08.jsonl"
EVENTS = REPO / "research_map" / "events.jsonl"
ART = "artifacts/worker08"
STATE = "runtime/state"
TS = datetime.now(CST)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha_rel(rel: str) -> str:
    return sha(REPO / rel)


def existing_ids() -> set[str]:
    ids: set[str] = set()
    for p in (OUTBOX, EVENTS):
        if not p.exists():
            continue
        for line in p.read_text(errors="ignore").splitlines():
            if '"event_id"' not in line:
                continue
            try:
                ids.add(json.loads(line)["event_id"])
            except Exception:
                continue
    return ids


def main() -> int:
    stamp = TS.strftime("%Y%m%dT%H%M%S%z")
    rev = json.loads((REPO / "artifacts/formulation/FROZEN.json").read_text())["revision"]
    bundle_rel = f"{ART}/rev_rebind_rev{rev}.json"
    bundle = json.loads((REPO / bundle_rel).read_text())

    pins = bundle["pins"]
    c0 = "schemas/af_scc_c0_vacuum.yaml"
    c2 = "schemas/af_scc_c2_vacuum.yaml"
    f1 = "schemas/af_wcc_vacuum.yaml"
    frozen = "artifacts/formulation/FROZEN.json"

    tool_rel = f"{ART}/rev_rebind.py"
    controls_rel = f"{ART}/rev_rebind_controls.json"
    checkpoint_rel = f"{STATE}/worker-008_rev_rebind_checkpoint.json"

    controls = {
        "record_id": "w008-formsep04-revrebind-controls",
        "task_id": "W008-FORMSEP04-REVREBIND-01",
        "assigned_task_id": "FORM-SEP-04",
        "actor": "worker-008",
        "agent_id": "deepseek-flash-08",
        "created_at": TS.isoformat(timespec="seconds"),
        "pins": {
            "F2b_c0": pins["F2b"],
            "F2a_c2": pins["F2a"],
            "F1": pins["F1"],
            "FROZEN": pins["FROZEN"],
        },
        "control_1_prerepair_sensitivity": {
            "command": f"python3 {tool_rel} --label prerepair-control",
            "expected": "FAIL",
            "observed": bundle["verdict"],
            "exit_code": 1,
            "checks": {k: v["result"] for k, v in bundle["checks"].items()},
            "X3c_violations": bundle["checks"]["form_sep_04_audit"]["X3c_violations"],
            "dual_finding_kinds": bundle["checks"]["f2b_dual_defect"]["finding_kinds"],
            "bundle": f"{bundle_rel}#{sha_rel(bundle_rel)[:12]}",
            "meaning": (
                "The harness is sensitive to the rev28 defect: it does not pass on unrepaired bytes."
            ),
        },
        "control_2_fail_closed_wrong_expect": {
            "command": (
                "python3 artifacts/worker-008/f2b_rev11_dualrepair/audit_dual_defect.py "
                "--c0 schemas/af_scc_c0_vacuum.yaml --c2 schemas/af_scc_c2_vacuum.yaml "
                "--expect-c0 deadbeef --expect-c2 deadbeef"
            ),
            "expected": "FAIL-CLOSED exit 3 with no verdict",
            "observed": "FAIL-CLOSED, exit 3, no verdict emitted",
            "meaning": (
                "The checker the harness depends on refuses to emit a verdict when its input hash "
                "binding is wrong; a PASS cannot be manufactured by re-pointing the expectation."
            ),
        },
        "control_3_repair_sensitivity": {
            "candidate_c0": (
                "artifacts/worker-008/f2b_rev11_dualrepair/candidate_rev12/af_scc_c0_vacuum.yaml"
            ),
            "candidate_c0_sha256": "98f9ec83c487d6920968f0bdf98e03974813376b6d222b617300525eb13feb1c",
            "commands": [
                "python3 artifacts/worker-008/f2b_rev11_dualrepair/audit_dual_defect.py "
                "--c2 schemas/af_scc_c2_vacuum.yaml --c0 <candidate> --expect-c0 98f9ec83c487 "
                "--expect-c2 5476a3f2c6bc --label repair-control --json <out>",
                "python3 artifacts/worker08/c2_c0_separation_audit.py --c2 schemas/af_scc_c2_vacuum.yaml "
                "--c0 <candidate> --out-json <in-repo out> --out-md <in-repo out> --label repair-control",
            ],
            "dual_checker": {"verdict": "PASS", "findings": 0},
            "form_sep_04_audit": {"verdict": "PASS", "X3c_violations": 0, "X1_violations": 0},
            "residuals": (
                "2 adjacent fixture/mutant files still carry the pre-repair sentence "
                "(n02_scc_c0_relabelled_as_c2.yaml, n07_scc_completeness_in_unscanned_i_plus_key.yaml): "
                "regenerate before reusing the corpus."
            ),
            "meaning": (
                "Both gating checkers flip to PASS on a 2-edit repair of exactly the two C0 leaf "
                "fields; the harness is not pass-blocked by its own design."
            ),
        },
        "control_4_binding": {
            "frozen_pin_binding": bundle["checks"]["frozen_pin_binding"]["result"],
            "canonical_mirror_byte_equality": bundle["checks"]["canonical_mirror_byte_equality"]["result"],
            "verify_frozen": {
                "result": bundle["checks"]["verify_frozen"]["result"],
                "output_tail": bundle["checks"]["verify_frozen"]["output_tail"],
            },
        },
        "falsifier": bundle["falsifier"],
        "authority": bundle["authority"],
    }
    (REPO / controls_rel).write_text(json.dumps(controls, indent=1, sort_keys=True) + "\n",
                                     encoding="utf-8")

    checkpoint = {
        "checkpoint_id": f"ckpt-w008-revrebind-{stamp}",
        "task_id": "W008-FORMSEP04-REVREBIND-01",
        "assigned_task_id": "FORM-SEP-04",
        "assignment_event_id": "assign-FORM-SEP-04-20260911T2331",
        "actor": "worker-008",
        "agent_id": "deepseek-flash-08",
        "node_id": "F2",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-CLASSBIND",
        "created_at": TS.isoformat(timespec="seconds"),
        "worker_hours_approx": 0.2,
        "status": "blocked-owner-repair",
        "state": {
            "frozen_revision": rev,
            "frozen_manifest_sha256": pins["FROZEN"],
            "c0_live_sha256": pins["F2b"],
            "c2_live_sha256": pins["F2a"],
            "f1_live_sha256": pins["F1"],
            "canonical_mirror_equal": bundle["checks"]["canonical_mirror_byte_equality"]["result"] == "PASS",
            "defect_present": True,
            "defect_locations": [
                "schemas/af_scc_c0_vacuum.yaml:151 regularity.must_not_conflate[0]",
                "schemas/af_scc_c0_vacuum.yaml:245 implication_ledger.forbidden_transfers[0].reason",
            ],
        },
        "blocker_ref": "w008-rev28-20260912T0037-blocker",
        "blocker_note": (
            "The binding blocker is already filed at rev28 and is not duplicated here. "
            "Rev29 does not exist as of this checkpoint; the defect is reproducible at the live bytes."
        ),
        "deliverables": {
            tool_rel: sha_rel(tool_rel),
            bundle_rel: sha_rel(bundle_rel),
            controls_rel: sha_rel(controls_rel),
            f"{ART}/form_sep_04_rev{rev}_rebind.json": sha_rel(f"{ART}/form_sep_04_rev{rev}_rebind.json"),
            f"{ART}/f2b_dual_defect_rev{rev}_rebind.json": sha_rel(f"{ART}/f2b_dual_defect_rev{rev}_rebind.json"),
        },
        "next_action": {
            "trigger": f"artifacts/formulation/FROZEN.json revision > {rev} with the two C0 leaf fields repaired",
            "command": f"python3 {tool_rel} --label post-repair",
            "acceptance": (
                "overall verdict PASS with X3c_violations 0 and dual finding_kinds []; "
                "if FAIL, emit the finding set to astra-lead-formulation rather than re-freezing again"
            ),
        },
        "next_falsifier": bundle["falsifier"],
        "authority": bundle["authority"],
    }
    (REPO / checkpoint_rel).write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n",
                                       encoding="utf-8")

    seen = existing_ids()
    ev_art = f"w008-formsep04-{stamp}-artifact-revrebind-tool"
    ev_ctl = f"w008-formsep04-{stamp}-artifact-revrebind-controls"
    ev_st = f"w008-formsep04-{stamp}-status"
    for e in (ev_art, ev_ctl, ev_st):
        if e in seen:
            print(f"refusing to write: event_id already exists: {e}", file=sys.stderr)
            return 2

    refs = [
        f"{c0}#{pins['F2b'][:12]}",
        f"{c2}#{pins['F2a'][:12]}",
        f"{frozen}#{pins['FROZEN'][:12]}",
        f"{bundle_rel}#{sha_rel(bundle_rel)[:12]}",
        f"{controls_rel}#{sha_rel(controls_rel)[:12]}",
        f"{tool_rel}#{sha_rel(tool_rel)[:12]}",
        "schemas/af_scc_c0_vacuum.yaml:151",
        "schemas/af_scc_c0_vacuum.yaml:245",
        "artifacts/worker-008/containment_direction/evidence/report.json#773858a088d3",
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
        "authority_note": (
            "Worker-level measurement only; does not set node status=done, validation_status=passed, "
            "or any gate verdict. Interpretation owned by astra-lead-formulation."
        ),
    }
    events = [
        dict(common, event_id=ev_art, event_type="artifact", artifact_type="tool",
             path=tool_rel, sha256=sha_rel(tool_rel), validation_status="unverified",
             summary=(
                 "Revision-agnostic FORM-SEP-04 re-bind driver (read-only): discovers FROZEN pins, "
                 "fails closed on pin mismatch, then runs verify_frozen + the X1-X5 separation audit "
                 "+ the F2b dual-defect checker at the live bytes; overall PASS only if all pass."
             ),
             evidence_refs=refs, falsifier=bundle["falsifier"]),
        dict(common, event_id=ev_ctl, event_type="artifact", artifact_type="evidence",
             path=controls_rel, sha256=sha_rel(controls_rel), validation_status="unverified",
             summary=(
                 "Control battery: (1) prerepair sensitivity FAIL at rev28 with exactly the known "
                 "findings, exit 1; (2) wrong-expect hash -> FAIL-CLOSED exit 3, no verdict; "
                 "(3) repaired 2-edit candidate 98f9ec83 -> dual PASS 0 findings and audit PASS X3c 0; "
                 "(4) FROZEN pin binding / mirror equality / verify_frozen all PASS."
             ),
             evidence_refs=refs, falsifier=bundle["falsifier"]),
        dict(common, event_id=ev_st, event_type="status", status="blocked", hours=0.2,
             summary=(
                 f"CHECKPOINT + EXIT. W008-FORMSEP04-REVREBIND-01: delivered the rev-agnostic re-bind "
                 f"driver and its sensitivity controls; prerepair run at FROZEN rev{rev} is FAIL "
                 f"(X3c 1, dual size_premise_inverted + false_containment_denial at C0 lines 245/151), "
                 f"as expected. No new artifact review filed and no duplicate blocker: the binding "
                 f"blocker w008-rev28-20260912T0037-blocker stands, rev29 does not exist yet. "
                 f"Next: run rev_rebind.py --label post-repair when the repaired re-freeze lands; "
                 f"acceptance is overall PASS with zero findings. Checkpoint: {checkpoint_rel}."
             ),
             evidence_refs=refs + [f"{checkpoint_rel}#{sha_rel(checkpoint_rel)[:12]}"],
             next_falsifier=bundle["falsifier"],
             checkpoint_ref=f"{checkpoint_rel}#{sha_rel(checkpoint_rel)[:12]}"),
    ]

    required = {
        "artifact": ["event_id", "event_type", "created_at", "actor", "node_id", "artifact_type",
                     "path", "sha256", "validation_status"],
        "status": ["event_id", "event_type", "created_at", "actor", "node_id", "status", "summary"],
    }
    lines = []
    for e in events:
        for k in required[e["event_type"]]:
            if not e.get(k) and e.get(k) != 0:
                print(f"event {e['event_id']} missing required field {k}", file=sys.stderr)
                return 2
        # extra loop-guard: every evidence ref must be path#sha-prefix or path:line (PROTOCOL rule 4)
        import re as _re
        for r in e["evidence_refs"]:
            if not (_re.search(r"#[0-9a-f]{6,}$", r) or _re.search(r":\d+(-\d+)?$", r)):
                print(f"event {e['event_id']} evidence_ref without hash/line pin: {r}", file=sys.stderr)
                return 2
        lines.append(json.dumps(e, sort_keys=True))

    with OUTBOX.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    # re-read and validate what landed
    got = [json.loads(x) for x in OUTBOX.read_text().splitlines()[-len(lines):]]
    print(json.dumps({
        "outbox": str(OUTBOX.relative_to(REPO)),
        "events_written": [e["event_id"] for e in got],
        "checkpoint": f"{checkpoint_rel}#{sha_rel(checkpoint_rel)[:12]}",
        "controls": f"{controls_rel}#{sha_rel(controls_rel)[:12]}",
        "tool": f"{tool_rel}#{sha_rel(tool_rel)[:12]}",
        "prerepair_verdict": bundle["verdict"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
