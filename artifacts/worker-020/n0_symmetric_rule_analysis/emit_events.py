#!/usr/bin/env python3
"""W020-N0-SYMRULE-01 outbox emitter.

Appends schema-valid events for the symmetric-rule analysis to
comms/outbox/deepseek-flash-20.jsonl.  Two modes:

  main    artifacts (py/json/log/README) + claim + blocker
  status  the final status event, referencing the checkpoint taken after `main`

Every event is validated against research_map/schemas.py before it is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "research_map"))
from schemas import validate_event  # noqa: E402

OUTBOX = REPO / "comms" / "outbox" / "deepseek-flash-20.jsonl"
CST = timezone(timedelta(hours=8))

TASK = "W020-N0-SYMRULE-01"
NODE = "N0"
CLASS_ID = "AF-WCC-SCALAR-SPH"
GATE = "G-NUM"
GROUP = "numerics"
TO = ["astra", "astra-lead-numerics", "astra-lead-audit"]

TARGET = "numerics/protocol/temporal_subdominance_control.json#334f5b71e0d5"
GENERATOR = "numerics/protocol/temporal_subdominance_control.py#ee14a3caf086"
FROZEN = "numerics/tests/flat_wave_replication.py#8ade1cdc163e"

FALSIFIER = (
    "Void if: (i) any pinned input re-hashes differently; (ii) the one-sided recomputation "
    "does not reproduce the filed excess/rule_b_pass/admissible_as_spatial values; (iii) a "
    "filed sweep point is missing or non-halving; (iv) the sign-flip mutation is not "
    "detected; or (v) two core runs are not byte-identical.")

NEXT_FALSIFIER = (
    "A canonical rule_b restated two-sided and re-verified at a new hash; or an independently "
    "re-executed filed B ladder failing |p-2|<=0.3; or a disposition that quotes ladder A "
    "(constant CFL) as a spatial measurement after this evidence.")

ASSUMPTIONS = [
    "The generator's one-sided implementation is read from lines 224-229 (max of signed "
    "excess <= tolerance) and from the pre-registered rule text; no canonical file is modified.",
    "The two-sided reading |excess| <= 0.05 is a sensitivity check on the pre-registered rule, "
    "not a replacement; the 0.05 tolerance is taken from the target unchanged.",
    "No solver re-run: filed sweep rows are treated as deterministic measurements, consistent "
    "with the target's own determinism claim and W020-N0-FIXEDDT-VERIFY-01.",
    "Only dr in {0.2, 0.05} were swept; no claim is made about dr in {0.1, 0.025}.",
    "The fixed-dt bound scales with q = min(2, measured local order), so it never assumes "
    "faster temporal decay than measured.",
]

STATEMENT = (
    "At target numerics/protocol/temporal_subdominance_control.json#334f5b71e0d5 (generator "
    "ee14a3caf086) and frozen instrument 8ade1cdc163e, an independent hash-pinned re-analysis "
    "of the filed temporal sweeps shows the A-ladder (constant-CFL) admissibility verdict is "
    "one-sided-rule dependent: of 6 swept (scheme, dr) points, 4 pass the pre-registered "
    "one-sided rule (excess <= 0.05) but 0 pass the two-sided reading |excess| <= 0.05. The "
    "two schemes declared admissible, lffd and cnfem, are exactly those with negative excess "
    "(lffd -0.2359/-0.2317, cnfem -0.7233/-0.7180 at dr=0.2/0.05), i.e. temporal-spatial "
    "cancellation; cnfd has positive excess (+1.2382/+1.2582) and fails both readings. A "
    "sign-flip mutation flips the one-sided verdicts (lffd/cnfem pass->fail, cnfd fail->pass) "
    "while the two-sided verdict is invariant, 6/6 detected. Two of four A-ladder rungs "
    "(dr=0.1, 0.025) have no temporal sweep filed, so under the two-sided reading 0/4 rungs "
    "have positive temporal-subdominance evidence. The A-ladder order-2 fit itself is "
    "leave-one-out stable (max shift 0.0026), so this is an admissibility/evidence defect, not "
    "a changed number. The fixed-dt ladders B remain admissible: at both swept dr and dt=1e-3 "
    "and 5e-4 all 12 (scheme, dr, dt) cells pass the same 0.05 tolerance with conservative "
    "bound <= 1.52e-3 (>=32x margin), and their 4-rung order fits recompute to lffd "
    "2.000626/2.000109, cnfd 1.996292/1.999013, cnfem 2.003704/2.000945, all in band. "
    "Consequence: the certified order-2 claim is carried by ladder B, not by ladder A; "
    "quoting p_cfl as a spatial measurement is unsupported under the two-sided reading. "
    "Worker evidence only: no gate verdict, no node completion, no canonical edit."
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def artifact_events():
    files = [
        ("verification_tool", HERE / "analyze_symmetric_rule.py",
         "Independent re-analysis tool: hash pins, recomputation of all filed sweep and ladder "
         "statistics, one-sided vs two-sided verdicts, leave-one-out A-ladder fits, "
         "conservative fixed-dt contamination bounds, sign-flip/vacuous/determinism controls."),
        ("verification_report", HERE / "symmetric_rule_analysis.json",
         "Machine-readable result: 6 swept points (4 one-sided pass, 0 two-sided pass), "
         "12/12 fixed-dt bound cells pass, all cross-checks and controls pass."),
        ("run_log", HERE / "symmetric_rule_analysis.log",
         "Run log with pins, per-point excess and verdicts, leave-one-out fits, bound summary "
         "and control outcomes; exit 0."),
        ("readme", HERE / "README.md",
         "Findings SR-1..SR-5, method, controls, reproduction, falsifier and explicit "
         "not-claimed list."),
    ]
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S%z")
    out = []
    for i, (atype, path, note) in enumerate(files):
        rel = str(path.relative_to(REPO))
        out.append({
            "event_id": f"w020d-{stamp}-symrule-art-{i}",
            "event_type": "artifact",
            "created_at": datetime.now(CST).isoformat(timespec="seconds"),
            "actor": "deepseek-flash-20",
            "task_id": TASK,
            "node_id": NODE,
            "class_id": CLASS_ID,
            "gate": GATE,
            "group_id": GROUP,
            "artifact_type": atype,
            "path": rel,
            "sha256": sha256_file(path),
            "validation_status": "unverified",
            "note": note + " Worker evidence only; no gate verdict and no node completion.",
            "evidence_refs": [TARGET, GENERATOR, FROZEN],
            "falsifier": FALSIFIER,
            "to": TO,
        })
    return out


def claim_and_blocker(report_rel: str, report_sha: str, readme_rel: str, readme_sha: str):
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S%z")
    refs = [TARGET, GENERATOR, FROZEN,
            f"{report_rel}#{report_sha[:12]}", f"{readme_rel}#{readme_sha[:12]}"]
    claim = {
        "event_id": f"w020d-{stamp}-symrule-claim",
        "event_type": "claim",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "actor": "deepseek-flash-20",
        "task_id": TASK,
        "node_id": NODE,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
        "gate": GATE,
        "group_id": GROUP,
        "conclusion_type": "numerical_evidence",
        "statement": STATEMENT,
        "assumptions": ASSUMPTIONS,
        "falsifier": FALSIFIER,
        "next_falsifier": NEXT_FALSIFIER,
        "evidence_refs": refs,
        "artifact_refs": [report_rel, readme_rel],
        "not_claimed": [
            "no gate verdict and no gate self-pass",
            "no node completion; numerics_lock stays LOCKED and numerics/spherical_solver/ absent",
            "no physics claim; flat-space discretisation evidence only",
            "no statement that the canonical rule_b is wrong or must be changed",
            "no re-measurement of the PDE; no claim about the unswept dr=0.1/0.025 rungs",
        ],
        "to": TO,
    }
    blocker = {
        "event_id": f"w020d-{stamp}-symrule-blocker",
        "event_type": "blocker",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "actor": "deepseek-flash-20",
        "task_id": TASK,
        "node_id": NODE,
        "class_id": CLASS_ID,
        "gate": GATE,
        "group_id": GROUP,
        "description": (
            "RB1/RB2 remain unresolved in the canonical artifacts: rule_b is one-sided "
            "(max of signed excess <= 0.05) and names dr=0.2 while the filed check uses the "
            "worst over {0.2, 0.05}. Under the two-sided reading 0/6 swept points are "
            "admissible, so the filed 'admissible_as_spatial=true' verdicts for lffd and cnfem "
            "are not robust. A worker may not edit the canonical rule or the lead's target."),
        "needed_to_unblock": (
            "lead-numerics disposition at the pinned hash: either (a) restate rule_b two-sided "
            "(|excess| <= tol) and re-verify at a new hash, or (b) record an explicit "
            "justification for the one-sided form and re-scope the A-ladder verdicts, and "
            "decide which ladder the certified spatial-order claim cites (this analysis says "
            "ladder B)."),
        "evidence_refs": refs,
        "stop_rule": (
            "Stop when the lead records a hash-bound disposition on rule_b and the A-ladder "
            "verdicts; no further worker re-analysis of the same filed rows is useful."),
        "to": TO,
    }
    return [claim, blocker]


def status_event(checkpoint_path: str, checkpoint_sha: str, report_rel: str, report_sha: str):
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S%z")
    return {
        "event_id": f"w020d-{stamp}-symrule-status",
        "event_type": "status",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "actor": "deepseek-flash-20",
        "task_id": TASK,
        "node_id": NODE,
        "class_id": CLASS_ID,
        "gate": GATE,
        "group_id": GROUP,
        "status": "active",
        "hours": 0.5,
        "claims_completion": True,
        "summary": (
            "COMPLETION CLAIM (worker may not set done). W020-N0-SYMRULE-01 finished at worker "
            "level: independent hash-pinned symmetric-rule sensitivity analysis at target "
            "334f5b71e0d5. Result: 6 swept points, 4 one-sided pass, 0 two-sided pass; "
            "sign-flip control 6/6; A-ladder leave-one-out max shift 0.0026; fixed-dt ladder B "
            "12/12 cells pass the same tolerance with >=32x margin; all cross-checks and "
            "determinism pass. No canonical path edited; no gate verdict and no node "
            "completion claimed. Blocker filed for the lead's rule_b disposition."),
        "evidence_refs": [
            f"{report_rel}#{report_sha[:12]}",
            f"{checkpoint_path}#{checkpoint_sha[:12]}",
            TARGET, GENERATOR, FROZEN,
        ],
        "checkpoint": {"path": checkpoint_path, "sha256": checkpoint_sha},
        "next_falsifier": NEXT_FALSIFIER,
        "to": TO,
    }


def append(events):
    for e in events:
        validate_event(e)
    with OUTBOX.open("a") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    for e in events:
        print(e["event_id"], e["event_type"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["main", "status"], default="main")
    ap.add_argument("--checkpoint", default="")
    ap.add_argument("--checkpoint-sha", default="")
    a = ap.parse_args()

    report = HERE / "symmetric_rule_analysis.json"
    readme = HERE / "README.md"
    report_rel = str(report.relative_to(REPO))
    readme_rel = str(readme.relative_to(REPO))
    report_sha = sha256_file(report)
    readme_sha = sha256_file(readme)

    if a.mode == "main":
        ev = artifact_events() + claim_and_blocker(report_rel, report_sha, readme_rel, readme_sha)
    else:
        if not a.checkpoint or not a.checkpoint_sha:
            print("--checkpoint and --checkpoint-sha are required in status mode", file=sys.stderr)
            return 2
        ev = [status_event(a.checkpoint, a.checkpoint_sha, report_rel, report_sha)]
    append(ev)
    print(f"appended {len(ev)} events to {OUTBOX.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
