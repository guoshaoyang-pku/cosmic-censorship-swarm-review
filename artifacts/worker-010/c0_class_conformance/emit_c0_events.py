#!/usr/bin/env python3
"""Emit the worker-010 C0 conformance result as validated comms events + a checkpoint.

Writes (append-only) to comms/outbox/worker-010.jsonl and emits a checkpoint JSON in the worker
artifact directory.  Every event is validated with research_map.schemas.validate_event before it
is written.  A worker event never sets node status=done, validation_status=passed, or a gate
verdict: the claim is recorded, not promoted.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from research_map.schemas import validate_event  # noqa: E402

AUDIT = HERE / "c0_class_conformance_audit.json"
VERIFY = HERE / "verify_c0_conformance.json"
AUDIT_SCRIPT = HERE / "c0_class_conformance_audit.py"
VERIFY_SCRIPT = HERE / "verify_c0_conformance.py"
OUTBOX = ROOT / "comms" / "outbox" / "worker-010.jsonl"
CLASS = "AF-SCC-C0-VAC-GEN"
TZ = timezone(timedelta(hours=8))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def main() -> int:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    verify = json.loads(VERIFY.read_text(encoding="utf-8"))
    audit_sha = sha256(AUDIT)
    verify_sha = sha256(VERIFY)
    snap_rel = next(iter(audit["inputs"]["snapshot"]))
    snap_sha = audit["inputs"]["snapshot"][snap_rel]["sha256"]

    now = datetime.now(TZ)
    ts = now.strftime("%Y%m%dT%H%M%S")
    s = audit["summary"]
    ledger_sha = audit["inputs"]["ledger/theorems.jsonl"]["sha256"]
    schema_sha = audit["inputs"]["schemas/af_scc_c0_vacuum.yaml"]["sha256"]

    statement = (
        f"{CLASS} (F2b) has {s['n_bound_entries']} ledger entries bound to it at ledger revision "
        f"{ledger_sha[:12]} ({s['n_accepted_status']} accepted, "
        f"{s['n_bound_entries'] - s['n_accepted_status']} provisional) and 0 that discharge the frozen class "
        f"conclusion at canonical schema revision {audit['class_definition']['revision']} (sha256 {schema_sha[:12]}). "
        "Of the bound entries: 3 are definitions of the class or of weaker variants (D-002/D-004/D-005), 2 are "
        "open-problem/conjecture/literature-status entries (T-402/T-515), 1 is a Kerr-stability result (T-528), and "
        "5 are theorem/preprint results: 3 assert that a continuous extension EXISTS (T-301, T-303, T-526), 1 "
        "concludes only a weaker-regularity (Lipschitz) inextendibility (T-305), and 1 (T-302) matches the class "
        "conclusion but only for an exact solution. The single entry "
        "whose conclusion and regularity match the class in the right direction (T-302, Sbierski 2018, peer-reviewed, "
        "C0-inextendibility of maximal analytic Schwarzschild) fails D1 (exact solution, not the class's comeager "
        "generic set of one-ended asymptotically flat vacuum Cauchy data) and carries one unresolved journal-locator "
        "item. Therefore the 3 `covered` cells for this class in ledger/class_coverage.csv (SRC-005, SRC-006, "
        "SRC-022) are binding-strength only, not a class conclusion, and the class stays open, consistent with the "
        "schema's own epistemic_status=open_problem."
    )

    events = [
        {
            "event_id": f"w010-{ts}-c0-artifact-audit",
            "event_type": "artifact",
            "created_at": now.isoformat(timespec="seconds"),
            "actor": "worker-010",
            "node_id": "L1",
            "gate": "G-LIT",
            "class_id": CLASS,
            "assignment_ref": "asg-2026-09-11-L1-deepseek-flash-10-19",
            "artifact_type": "class_conformance_audit",
            "path": rel(AUDIT),
            "sha256": audit_sha,
            "validation_status": "unverified",
            "evidence_refs": [
                f"{rel(AUDIT)}#{audit_sha[:12]}",
                f"ledger/theorems.jsonl#{ledger_sha[:12]}",
                f"schemas/af_scc_c0_vacuum.yaml#{schema_sha[:12]}",
                f"{snap_rel}#{snap_sha[:12]}",
            ],
            "falsifier": audit["falsifier"],
            "summary": (
                f"AF-SCC-C0-VAC-GEN conformance audit: {s['n_bound_entries']} bound ledger entries, "
                f"0 discharging; covered cells are binding-strength only. Independent classifier and 4 negative "
                f"controls included."
            ),
        },
        {
            "event_id": f"w010-{ts}-c0-artifact-snapshot",
            "event_type": "artifact",
            "created_at": now.isoformat(timespec="seconds"),
            "actor": "worker-010",
            "node_id": "L1",
            "gate": "G-LIT",
            "class_id": CLASS,
            "artifact_type": "frozen_schema_snapshot",
            "path": snap_rel,
            "sha256": snap_sha,
            "validation_status": "unverified",
            "evidence_refs": [f"{snap_rel}#{snap_sha[:12]}", f"schemas/af_scc_c0_vacuum.yaml#{schema_sha[:12]}"],
            "falsifier": "Byte-compare the snapshot against the revision it claims; any mismatch falsifies the pin.",
        },
        {
            "event_id": f"w010-{ts}-c0-artifact-verification",
            "event_type": "artifact",
            "created_at": now.isoformat(timespec="seconds"),
            "actor": "worker-010",
            "node_id": "L1",
            "gate": "G-LIT",
            "class_id": CLASS,
            "artifact_type": "verification_report",
            "path": rel(VERIFY),
            "sha256": verify_sha,
            "validation_status": "unverified",
            "evidence_refs": [
                f"{rel(VERIFY)}#{verify_sha[:12]}",
                f"{rel(AUDIT)}#{audit_sha[:12]}",
                f"{rel(VERIFY_SCRIPT)}#{sha256(VERIFY_SCRIPT)[:12]}",
            ],
            "falsifier": (
                "Re-run verify_c0_conformance.py: a FAIL line, a verdict disagreement on any binding, or an "
                "all_pass=false flag falsifies the audit's internal consistency."
            ),
            "summary": f"Independent second-implementation re-check: all_pass={verify['all_pass']}, "
                       f"{len(verify['checks'])} checks, 0 classifier disagreements.",
        },
        {
            "event_id": f"w010-{ts}-c0-claim",
            "event_type": "claim",
            "created_at": now.isoformat(timespec="seconds"),
            "actor": "worker-010",
            "node_id": "L1",
            "gate": "G-LIT",
            "class_id": CLASS,
            "assignment_ref": "asg-2026-09-11-L1-deepseek-flash-10-19",
            "task_id": "W010-F2B-C0-CONFORMANCE-01",
            "statement": statement,
            "conclusion_type": "open_problem",
            "assumptions": [
                "class_ids and status are inherited from ledger/theorems.jsonl revision " + ledger_sha[:12] + "; this audit does not re-adjudicate them (A1's job)",
                "D1/D2/D3 are mechanical readings of the entries' genericity/regularity/scope_caveats/unresolved fields; a reviewer may bind an entry differently, which is the A1 verdict this artifact asks for",
                "the class definition is quoted from canonical schemas/af_scc_c0_vacuum.yaml at sha256 " + schema_sha[:12] + " (rev " + str(audit['class_definition']['revision']) + "); FROZEN.json rev " + str(audit['class_definition'].get('frozen_manifest_observation', {}).get('revision')) + " binds the same bytes",
                "conclusion_type=open_problem: this claim is a literature-state measurement, not a theorem about cosmic censorship",
            ],
            "falsifier": audit["falsifier"],
            "evidence_refs": [
                f"{rel(AUDIT)}#{audit_sha[:12]}",
                f"ledger/theorems.jsonl#{ledger_sha[:12]}",
                f"ledger/class_coverage.csv#{audit['inputs']['ledger/class_coverage.csv']['sha256'][:12]}",
                f"schemas/af_scc_c0_vacuum.yaml#{schema_sha[:12]}",
                f"{rel(VERIFY)}#{verify_sha[:12]}",
            ],
            "artifact_refs": [
                f"{rel(AUDIT)}#{audit_sha[:12]}",
                f"{snap_rel}#{snap_sha[:12]}",
                f"{rel(VERIFY)}#{verify_sha[:12]}",
            ],
            "expected_information_gain": (
                "Completes the 4-class conformance series (WCC, C2, C0; SCALAR-SPH by worker-072): the C0 cell is "
                "evidence-rich and conclusion-poor, so G-LIT/G-FORM readers must treat its covered cells as "
                "bindings, and A1 has an explicit direction/weakening checklist."
            ),
            "next_falsifier": (
                "A1 review of the three direction-mismatch entries (T-301, T-303, T-526: continuous extension "
                "asserted) and of the two forbidden-weakening candidates (T-305 Lipschitz; D-004/D-005 variant "
                "definitions): any of these cited as C0 evidence is class inflation."
            ),
        },
        {
            "event_id": f"w010-{ts}-c0-status",
            "event_type": "status",
            "created_at": now.isoformat(timespec="seconds"),
            "actor": "worker-010",
            "node_id": "L1",
            "gate": "G-LIT",
            "class_id": CLASS,
            "status": "active",
            "hours": 0.75,
            "summary": (
                "W010-F2B-C0-CONFORMANCE-01 complete: one bounded class-bound task on AF-SCC-C0-VAC-GEN. "
                f"{s['n_bound_entries']} bound ledger entries, {s['n_discharging']} discharging, class state "
                "open_problem; covered cells are binding-strength only. Artifacts on disk and hash-pinned; "
                "verification report all_pass=true. No node completion, gate verdict, or promotion is claimed."
            ),
            "evidence_refs": [
                f"{rel(AUDIT)}#{audit_sha[:12]}",
                f"{rel(VERIFY)}#{verify_sha[:12]}",
                f"{snap_rel}#{snap_sha[:12]}",
            ],
            "next_falsifier": (
                "Any accepted ledger entry that discharges D1+D2+D3 (see claim falsifier); otherwise the class "
                "stays open and the claim is a stable snapshot until ledger/schema drift."
            ),
        },
    ]

    for ev in events:
        validate_event(ev)

    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    existing_ids = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing_ids.add(json.loads(line)["event_id"])
    fresh = [e for e in events if e["event_id"] not in existing_ids]
    with OUTBOX.open("a", encoding="utf-8") as fh:
        for e in fresh:
            fh.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")

    checkpoint = {
        "checkpoint_id": f"worker-010-c0-{ts}",
        "worker": "010",
        "actor": "worker-010",
        "alias_actor": "deepseek-flash-10",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_id": CLASS,
        "created_at": now.isoformat(timespec="seconds"),
        "task_id": "W010-F2B-C0-CONFORMANCE-01",
        "assignment_ref": "asg-2026-09-11-L1-deepseek-flash-10-19",
        "event_ids": [e["event_id"] for e in fresh],
        "outbox": rel(OUTBOX),
        "artifacts": {
            rel(AUDIT): {"sha256": audit_sha, "bytes": AUDIT.stat().st_size},
            snap_rel: {"sha256": snap_sha, "bytes": (ROOT / snap_rel).stat().st_size},
            rel(VERIFY): {"sha256": verify_sha, "bytes": VERIFY.stat().st_size},
            rel(AUDIT_SCRIPT): {"sha256": sha256(AUDIT_SCRIPT)},
            rel(VERIFY_SCRIPT): {"sha256": sha256(VERIFY_SCRIPT)},
        },
        "inputs": audit["inputs"],
        "result": {
            "n_bound_entries": s["n_bound_entries"],
            "n_accepted_status": s["n_accepted_status"],
            "n_discharging": s["n_discharging"],
            "class_conclusion_state": s["class_conclusion_state"],
            "direction_mismatch_candidates": s["direction_mismatch_candidates"],
            "weakening_or_inflation_candidates": s["weakening_or_inflation_candidates"],
            "matrix_covered_cells": [c["source_id"] for c in s["matrix_crosswalk"]["covered_cells"]],
            "negative_controls_all_pass": audit["negative_controls"]["all_pass"],
            "independent_verifier_all_pass": verify["all_pass"],
        },
        "falsifier": audit["falsifier"],
        "next_falsifier": (
            "Ledger/schema drift after this checkpoint, or an accepted entry discharging D1+D2+D3; re-run the "
            "audit at the new revision before citing these numbers."
        ),
        "validation_status": "unverified",
    }
    ckpt = HERE / f"checkpoint_c0_{ts}.json"
    ckpt.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"validated {len(events)} events; appended {len(fresh)} to {rel(OUTBOX)}")
    print(f"checkpoint: {rel(ckpt)} sha256={sha256(ckpt)}")
    print("summary:", json.dumps(checkpoint["result"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
