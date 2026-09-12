#!/usr/bin/env python3
"""Emit worker-020's hash-bound outbox events for W020-N0-FIXEDDT-VERIFY-01.

Appends one JSON object per line to comms/outbox/deepseek-flash-20.jsonl.
Every artifact event carries path + sha256 + validation_status; every evidence_ref is
`path#sha256-prefix`.  Worker events do not set gate verdicts, validation_status=passed or
node status=done.

  python3 emit_events.py pre
  # ... research_map/checkpoint.py ...
  python3 emit_events.py post runtime/state/checkpoints/ckpt-<stamp>.json
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUTBOX = REPO / "comms" / "outbox" / "deepseek-flash-20.jsonl"
TASK = "W020-N0-FIXEDDT-VERIFY-01"
CLASS_ID = "AF-WCC-SCALAR-SPH"
NODE = "N0"
GATE = "G-NUM"
ACTOR = "deepseek-flash-20"
TO = ["astra", "astra-lead-numerics", "astra-lead-audit"]
TARGET = "numerics/protocol/temporal_subdominance_control.json"
TARGET_SHA = "334f5b71e0d53ab6ed1f3b7133abca541a36dafc9a5cfb4f62f0655839dd964b"
FROZEN = "numerics/tests/flat_wave_replication.py"
FROZEN_SHA = "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422"

ARTIFACTS = {
    "report": ("verify_fixed_dt_control.json", "verification_report"),
    "tool": ("verify_fixed_dt_control.py", "verification_tool"),
    "log": ("verify_fixed_dt_control.log", "run_log"),
    "readme": ("README.md", "readme"),
}

FALSIFIER = (
    "Void if: (i) either pinned input re-hashes differently; (ii) a fresh re-run at frozen "
    "module 8ade1cdc163e reproduces any filed fixed-dt B row outside 1e-9 relative; (iii) a "
    "filed B ladder fit order falls outside |p-2|<=0.3; (iv) a filed derived statistic differs "
    "from this script's recomputation by more than 1e-9 relative; or (v) the mutation control "
    "is not detected."
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def append(events):
    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    prefix = ""
    if OUTBOX.exists() and OUTBOX.stat().st_size:
        with OUTBOX.open("rb") as fh:
            fh.seek(-1, 2)
            if fh.read(1) != b"\n":
                prefix = "\n"
    with OUTBOX.open("a", encoding="utf-8") as fh:
        fh.write(prefix)
        for e in events:
            fh.write(json.dumps(e, sort_keys=True) + "\n")
    return [e["event_id"] for e in events]


def main() -> int:
    phase = sys.argv[1] if len(sys.argv) > 1 else "pre"
    stamp = time.strftime("%Y%m%dT%H%M%S%z")
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    if phase == "pre":
        report = json.loads((HERE / "verify_fixed_dt_control.json").read_text())
        verdict = report["verdict"]
        b_orders = verdict["fixed_dt_ladder_orders"]
        events = []
        for key, (name, atype) in ARTIFACTS.items():
            path = HERE / name
            events.append({
                "event_id": f"w020c-{stamp}-n0-fixeddt-art-{key}",
                "event_type": "artifact",
                "created_at": now,
                "actor": ACTOR,
                "node_id": NODE,
                "class_id": CLASS_ID,
                "gate": GATE,
                "group_id": "numerics",
                "task_id": TASK,
                "artifact_type": atype,
                "path": str(path.relative_to(REPO)),
                "sha256": sha256(path),
                "validation_status": "unverified",
                "evidence_refs": [f"{TARGET}#{TARGET_SHA[:12]}", f"{FROZEN}#{FROZEN_SHA[:12]}"],
                "falsifier": FALSIFIER,
                "to": TO,
                "note": "worker evidence only; no gate verdict and no node completion",
            })
        events.append({
            "event_id": f"w020c-{stamp}-n0-fixeddt-claim",
            "event_type": "claim",
            "created_at": now,
            "actor": ACTOR,
            "node_id": NODE,
            "class_id": CLASS_ID,
            "gate": GATE,
            "group_id": "numerics",
            "task_id": TASK,
            "conclusion_type": "numerical_evidence",
            "statement": (
                "At target numerics/protocol/temporal_subdominance_control.json#334f5b71e0d5 "
                "(generator ee14a3caf086) and frozen instrument " + FROZEN + "#8ade1cdc163e, an "
                "independent fresh-process re-run reproduces every filed fixed-dt ladder B row "
                "and temporal-sweep row at 0.0 relative deviation, and the four-rung fixed-dt "
                "ladders at dt=1e-3 and dt=5e-4 give order 2 inside |p-2|<=0.3 for all three "
                "schemes (dt=1e-3: lffd 2.000626, cnfd 1.996292, cnfem 2.003704; dt=5e-4: lffd "
                "2.000109, cnfd 1.999013, cnfem 2.000945). Two defects in the target's own "
                "admissibility rule application: rule_b is one-sided as pre-registered, so "
                "negative excess (temporal-spatial cancellation) passes without bound "
                "(symmetric |excess| at dr=0.05: cnfd 1.258, cnfem 0.723, lffd 0.236); and the "
                "written rule names dr=0.2 while the filed check reports the worst over "
                "[0.2, 0.05] (immaterial to pass/fail). The order-2 spatial conclusion is "
                "supported by the protocol-compliant fixed-dt ladders B; the constant-CFL "
                "ladder A should be cited only as a labelled mixed-order supporting control."
            ),
            "assumptions": [
                "the frozen module 8ade1cdc163e is the canonical measurement instrument and is "
                "imported read-only under a hash guard",
                "the filed run is deterministic (no RNG); bitwise determinism was re-checked on "
                "six points",
                "the target artifact and its generator were not modified by this verification",
                "same shared axes as the frozen module (psi=r*phi, Dirichlet box, Taylor start, "
                "Gaussian pulse) are not re-tested here",
            ],
            "artifact_refs": [
                "artifacts/worker-020/n0_fixed_dt_control_verify/verify_fixed_dt_control.json",
                "artifacts/worker-020/n0_fixed_dt_control_verify/verify_fixed_dt_control.py",
                "artifacts/worker-020/n0_fixed_dt_control_verify/README.md",
            ],
            "evidence_refs": [
                f"{TARGET}#{TARGET_SHA[:12]}",
                f"{FROZEN}#{FROZEN_SHA[:12]}",
                "artifacts/worker-020/n0_fixed_dt_control_verify/verify_fixed_dt_control.json"
                f"#{sha256(HERE / 'verify_fixed_dt_control.json')[:12]}",
                "artifacts/worker-020/n0_fixed_dt_control_verify/README.md"
                f"#{sha256(HERE / 'README.md')[:12]}",
            ],
            "falsifier": FALSIFIER,
            "next_falsifier": (
                "A target revision that restates rule_b symmetrically and is re-verified at its "
                "new hash; or a fixed-dt B ladder that fails |p-2|<=0.3 on re-run; or a lead "
                "disposition that cites ladder A instead of B for the spatial order."
            ),
            "acceptance_tests": [
                "python3 artifacts/worker-020/n0_fixed_dt_control_verify/"
                "verify_fixed_dt_control.py --json-out /tmp/w020_recheck.json -> exit 0 and "
                "fresh_rerun_ok=true",
                "independent re-read: sha256 of the target and frozen module equal the pins",
            ],
            "to": TO,
        })
        ids = append(events)
        print(json.dumps({"phase": "pre", "event_ids": ids}, indent=2))
        return 0

    if phase == "post":
        ckpt = Path(sys.argv[2]).resolve()
        events = [{
            "event_id": f"w020c-{stamp}-n0-fixeddt-status",
            "event_type": "status",
            "created_at": now,
            "actor": ACTOR,
            "node_id": NODE,
            "class_id": CLASS_ID,
            "gate": GATE,
            "group_id": "numerics",
            "task_id": TASK,
            "status": "active",
            "claims_completion": True,
            "hours": 1.0,
            "summary": (
                "COMPLETION CLAIM (worker may not set done). " + TASK + " finished at worker "
                "level: independent fresh-process verification of the lead's fixed-dt N0 "
                "control at target 334f5b71e0d5, instrument 8ade1cdc163e. Verdict "
                "VERIFIED_WITH_ONE_RULE_DEFECT: all filed statistics recompute, all B and C "
                "rows reproduce at 0.0 relative deviation, fixed-dt ladders give order 2 in "
                "band for all three schemes at dt=1e-3 and 5e-4, controls and bitwise "
                "determinism pass; rule_b is one-sided (finding RB1) and names dr=0.2 while the "
                "filed check uses the worst over [0.2, 0.05] (RB2, immaterial). No canonical "
                "path was edited; no gate verdict and no node completion claimed."
            ),
            "evidence_refs": [
                "artifacts/worker-020/n0_fixed_dt_control_verify/verify_fixed_dt_control.json"
                f"#{sha256(HERE / 'verify_fixed_dt_control.json')[:12]}",
                "artifacts/worker-020/n0_fixed_dt_control_verify/README.md"
                f"#{sha256(HERE / 'README.md')[:12]}",
                f"{TARGET}#{TARGET_SHA[:12]}",
                f"{FROZEN}#{FROZEN_SHA[:12]}",
                f"{ckpt.relative_to(REPO)}#{sha256(ckpt)[:12]}",
            ],
            "next_falsifier": FALSIFIER,
            "checkpoint": {
                "path": str(ckpt.relative_to(REPO)),
                "sha256": sha256(ckpt),
                "note": "official checkpoint taken after this task's outbox events were emitted; "
                        "worker events remain pending application by the controller",
            },
            "to": TO,
        }]
        ids = append(events)
        print(json.dumps({"phase": "post", "event_ids": ids, "checkpoint": str(ckpt)}, indent=2))
        return 0

    raise SystemExit(f"unknown phase {phase!r}")


if __name__ == "__main__":
    raise SystemExit(main())
