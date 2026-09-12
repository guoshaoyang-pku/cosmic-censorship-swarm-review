#!/usr/bin/env python3
"""Emit the W010-L1-REAUDIT-03 (AF-SCC-C2-VAC-GEN rev12 addendum) events to the flash-10 outbox.

Events: report artifact, wrapper artifact, claim, status. Every event is schema-validated with
research_map.schemas.validate_event before any line is written; nothing is written on failure.
Appends one JSON object per line; never edits existing lines.
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

OUTBOX = ROOT / "comms" / "outbox" / "deepseek-flash-10.jsonl"

REPORT = HERE / "c2_class_conformance_audit.5476a3f2c6bc.json"
WRAPPER = HERE / "c2_reaudit_rev12.py"
DRIVER = HERE / "c2_class_conformance_audit.py"
REV9_REPORT = HERE / "c2_class_conformance_audit.json"
SNAP = HERE / "snapshots" / "af_scc_c2_vacuum.8dae50da1ab5.yaml"

CST = timezone(timedelta(hours=8))
CLASS = "AF-SCC-C2-VAC-GEN"
TASK_ID = "W010-L1-REAUDIT-03"
ASSIGNMENT_REF = "asg-2026-09-11-L1-deepseek-flash-10-19"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    created = datetime.now(CST).replace(microsecond=0).isoformat()
    rep = json.loads(REPORT.read_text(encoding="utf-8"))
    rep_h, wrap_h, drv_h, rev9_h, snap_h = (
        sha256(REPORT), sha256(WRAPPER), sha256(DRIVER), sha256(REV9_REPORT), sha256(SNAP))
    s = rep["summary"]
    ad = rep["revision_addendum"]
    lo = rep["ledger_status_observation"]
    changed = ad["step_drift_rev9_to_rev12"]["fields_changed_beyond_revision"]

    by_d2 = [b["theorem_id"] for b in rep["bindings"] if b["checks"]["D2_conclusion"]]
    all_fail_d3 = all(not b["checks"]["D3_evidence"] for b in rep["bindings"])

    summary = (
        f"W010-L1-REAUDIT-03 rev12 addendum: AF-SCC-C2-VAC-GEN re-derived at F2a rev12 "
        f"5476a3f2c6bc and ledger {lo['measured_ledger_sha256'][:12]} (rev9 report was bound to "
        f"F2a 8dae50da1ab5 / ledger {str(lo['rev9_report_input_ledger_sha256'])[:12]}). "
        f"Extraction-level change: {changed} (parameter renaming `(s,delta)` -> `r`, same comeager "
        f"quantifier structure) -> rev9 report's own revision falsifier fired; whether it is "
        f"semantic is F1/A1's call. Re-run: n_bound={s['n_bound_entries']}, "
        f"n_discharging={s['n_discharging']}, conclusion state '{s['class_conclusion_state']}'. "
        f"D2_conclusion holds for {by_d2} (they do conclude C2/C^{{0,1}}_loc-inextendibility), but "
        f"D1_data_class and D3_evidence fail for every binding: all 10 carry a non-generic or "
        f"unquantified data class, and at the current ledger the legacy `status: accepted` field "
        f"the driver tests no longer exists (the ledger now carries content_status "
        f"verified/provisional/rejected), so D3 fails mechanically for all 10. No completion, no "
        f"gate verdict."
    )
    next_falsifier = (
        "A further F2a revision changing statement_formal / epistemic_status / genericity / "
        "extension_regularity fields, or a class_definition sha != measured canonical sha, or a "
        "later ledger carrying an entry bound to AF-SCC-C2-VAC-GEN that satisfies D1+D2+D3 (generic "
        "residual/comeager one-ended AF vacuum Cauchy data, future C2-inextendibility, "
        "peer-reviewed/accepted-in-press, no open hypothesis) -> then n_discharging >= 1 and the "
        "class conclusion state is 'discharged', or a formulation-lead ruling that the "
        "`(s,delta)` -> `r` renaming is substantive (which would void the rev9->rev12 continuity of "
        "this reading), or an L0 ledger-schema decision that reinstates/renames the `status` field "
        "the driver's D3 test reads (which would change the D3 column for every binding)."
    )

    ev_report = {
        "event_id": f"flash-10-artifact-c2-reaudit-rev12-{stamp}",
        "event_type": "artifact",
        "created_at": created,
        "actor": "deepseek-flash-10",
        "run_id": "run-2026-09-11T23:15+08:00",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_id": CLASS,
        "class_ids": [CLASS],
        "assignment_ref": ASSIGNMENT_REF,
        "task_id": TASK_ID,
        "artifact_type": "json",
        "path": str(REPORT.relative_to(ROOT)),
        "sha256": rep_h,
        "bytes": REPORT.stat().st_size,
        "validation_status": "unverified",
        "claims_completion": False,
        "supersedes": {
            "path": str(REV9_REPORT.relative_to(ROOT)),
            "sha256": rev9_h,
            "reason": ad["supersedes_reason"],
        },
        "evidence_refs": rep["evidence_refs"] + [f"{WRAPPER.relative_to(ROOT)}#{wrap_h[:12]}"],
        "inputs": rep["inputs"],
        "falsifier": rep["falsifier"],
        "next_falsifier": next_falsifier,
        "summary": summary,
    }

    ev_wrapper = {
        "event_id": f"flash-10-artifact-c2-reaudit-rev12-driver-{stamp}",
        "event_type": "artifact",
        "created_at": created,
        "actor": "deepseek-flash-10",
        "run_id": "run-2026-09-11T23:15+08:00",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_id": CLASS,
        "class_ids": [CLASS],
        "assignment_ref": ASSIGNMENT_REF,
        "task_id": TASK_ID,
        "artifact_type": "python",
        "path": str(WRAPPER.relative_to(ROOT)),
        "sha256": wrap_h,
        "bytes": WRAPPER.stat().st_size,
        "validation_status": "unverified",
        "claims_completion": False,
        "evidence_refs": [
            f"{WRAPPER.relative_to(ROOT)}#{wrap_h[:12]}",
            f"{DRIVER.relative_to(ROOT)}#{drv_h[:12]}",
            f"{REV9_REPORT.relative_to(ROOT)}#{rev9_h[:12]}",
            f"{SNAP.relative_to(ROOT)}#{snap_h[:12]}",
        ],
        "falsifier": next_falsifier,
        "summary": (
            "Revision-addendum wrapper: imports the unmodified rev9 C2 driver "
            f"({DRIVER.name} {drv_h[:12]}), redirects only OUT to the rev12-prefixed file, and adds "
            "the step-drift / ledger-drift / input-stability record plus the honest post-rewrite "
            "driver pin (the driver's embedded self-hash predates the addendum rewrite). The rev9 "
            "report is preserved byte-identical."
        ),
    }

    ev_claim = {
        "event_id": f"flash-10-claim-c2-reaudit-rev12-{stamp}",
        "event_type": "claim",
        "created_at": created,
        "actor": "deepseek-flash-10",
        "run_id": "run-2026-09-11T23:15+08:00",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_id": CLASS,
        "class_ids": [CLASS],
        "assignment_ref": ASSIGNMENT_REF,
        "task_id": TASK_ID,
        "conclusion_type": "open_problem",
        "statement": (
            "AF-SCC-C2-VAC-GEN at F2a rev12 5476a3f2c6bc and ledger "
            f"{lo['measured_ledger_sha256'][:12]} has {s['n_bound_entries']} ledger entries bound to "
            "it and 0 that discharge the frozen class conclusion. D2_conclusion holds for "
            f"{by_d2}: those entries do conclude C2- or C^{{0,1}}_loc-inextendibility of the maximal "
            "development. D1_data_class fails for all 10 bindings: 4 are definitions of the class or "
            "of weaker variants (D-003/D-004/D-005/D-007), T-303 is a special high-frequency/"
            "impulsive data construction, T-526 is characteristic-interior data with genericity not "
            "quantified as open/dense, T-527 inherits T-526's curvature-blow-up hypothesis for "
            "characteristic data, T-305 and T-401 are conditional/preprint, and T-402 is a "
            "conjecture with genericity asserted but not quantified. D3_evidence fails for all 10 "
            "for two independent reasons: the legacy `status: accepted` field the driver tests no "
            "longer exists anywhere in the current 62-entry ledger (0/10 bound entries carry it, "
            "and the ledger now carries content_status verified/provisional/rejected), and the "
            "bound entries additionally carry open `unresolved` items. Therefore the 3 `covered` "
            "cells for this class in ledger/class_coverage.csv (SRC-022/080/081) are "
            "binding-strength only, not a class conclusion, and the class stays open, consistent "
            "with the schema's own claim_promotion=open_problem."
        ),
        "assumptions": [
            f"class_ids and status are inherited from ledger/theorems.jsonl revision {lo['measured_ledger_sha256'][:12]}; this audit does not re-adjudicate them (A1's job)",
            "D1/D2/D3 are mechanical readings of the entries' genericity/scope_caveats/unresolved/entry_kind/evidence_level fields; a reviewer may bind an entry differently, which is the A1 verdict this artifact asks for",
            "the class definition is quoted from canonical schemas/af_scc_c2_vacuum.yaml at sha256 5476a3f2c6bc (rev12); the rev9 snapshot 8dae50da1ab5 is preserved for the drift record",
            "the D3 `status` test is a mechanical legacy-field test; the ledger's migration to content_status is reported as a measurement, not adjudicated here",
            "conclusion_type=open_problem: this claim is a literature-state measurement, not a theorem about cosmic censorship",
        ],
        "falsifier": rep["falsifier"],
        "evidence_refs": [
            f"artifacts/flash-10/l1_class_coverage/c2_class_conformance_audit.5476a3f2c6bc.json#{rep_h[:12]}",
            f"ledger/theorems.jsonl#{lo['measured_ledger_sha256'][:12]}",
            f"ledger/class_coverage.csv#{rep['summary']['matrix_crosswalk']['matrix_sha256'][:12]}",
            f"schemas/af_scc_c2_vacuum.yaml#{rep['class_definition']['sha256'][:12]}",
            f"artifacts/flash-10/l1_class_coverage/c2_class_conformance_audit.json#{rev9_h[:12]}",
        ],
        "artifact_refs": [
            f"artifacts/flash-10/l1_class_coverage/c2_class_conformance_audit.5476a3f2c6bc.json#{rep_h[:12]}",
            f"artifacts/flash-10/l1_class_coverage/c2_class_conformance_audit.json#{rev9_h[:12]}",
        ],
        "expected_information_gain": (
            "Completes the rev12 re-audit series on the three frozen classes (WCC REAUDIT-01, C0 "
            "REAUDIT-02, C2 REAUDIT-03): each of the three cells reads 0 discharging at the current "
            "revision, so G-LIT/G-FORM readers should treat every `covered` cell in the matrix as a "
            "binding, and A1 gets a per-entry D1/D2/D3 checklist for the C2 scope queue."
        ),
        "next_falsifier": next_falsifier,
    }

    ev_status = {
        "event_id": f"flash-10-status-c2-reaudit-rev12-{stamp}",
        "event_type": "status",
        "created_at": created,
        "actor": "deepseek-flash-10",
        "run_id": "run-2026-09-11T23:15+08:00",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_id": CLASS,
        "class_ids": [CLASS],
        "assignment_ref": ASSIGNMENT_REF,
        "task_id": TASK_ID,
        "status": "active",
        "hours": 0.1,
        "summary": summary,
        "evidence_refs": [
            f"{REPORT.relative_to(ROOT)}#{rep_h[:12]}",
            f"{WRAPPER.relative_to(ROOT)}#{wrap_h[:12]}",
            f"{DRIVER.relative_to(ROOT)}#{drv_h[:12]}",
            f"{REV9_REPORT.relative_to(ROOT)}#{rev9_h[:12]}",
            f"schemas/af_scc_c2_vacuum.yaml#{rep['class_definition']['sha256'][:12]}",
            f"ledger/theorems.jsonl#{lo['measured_ledger_sha256'][:12]}",
        ],
        "next_falsifier": next_falsifier,
    }

    events = [ev_report, ev_wrapper, ev_claim, ev_status]
    errors = []
    for e in events:
        try:
            validate_event(e)
        except Exception as ex:  # SchemaError
            errors.append(f"{e['event_id']}: {ex}")
    if errors:
        for x in errors:
            print("SCHEMA FAIL:", x, file=sys.stderr)
        return 1
    if not all_fail_d3:
        print("SCHEMA/CLAIM FAIL: a binding passes D3; the claim text is invalid", file=sys.stderr)
        return 1

    with OUTBOX.open("a", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"appended {len(events)} validated events to {OUTBOX.relative_to(ROOT)}")
    for e in events:
        print(" ", e["event_type"], e["event_id"], e.get("sha256", "")[:12])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
