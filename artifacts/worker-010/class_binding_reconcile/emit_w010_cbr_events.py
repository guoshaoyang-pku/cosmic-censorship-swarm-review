#!/usr/bin/env python3
"""Append worker-010's class-binding reconciliation evidence to comms/outbox/worker-010.jsonl.

Bounded task W010-CBR-01: class-binding / coverage-matrix reconciliation at the
live pins (ledger a1674f094979, matrix abbaee54a5a3, class contracts cce9c60146d6 /
5476a3f2c6bc / 55d0a1ea9bda / 0abb9ed8a961).  Appends four events (2 artifacts,
1 claim, 1 status); never rewrites existing lines.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms/outbox/worker-010.jsonl"
CST = timezone(timedelta(hours=8))


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ev(path: str) -> str:
    return f"{path}#{sha256(ROOT / path)[:12]}"


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def main() -> int:
    now = datetime.now(CST).isoformat(timespec="seconds")
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    run_id = "run-2026-09-11T23:15+08:00"

    report_path = HERE / "binding_reconcile_audit.json"
    script_path = HERE / "binding_reconcile_audit.py"
    verify_path = HERE / "verify_binding_reconcile.json"
    verify_script = HERE / "verify_binding_reconcile.py"
    report = json.loads(report_path.read_text())
    verify = json.loads(verify_path.read_text())
    s = report["summary"]

    ledger_snap = "artifacts/worker-010/class_binding_reconcile/snapshots/theorems.a1674f094979.jsonl"
    matrix_snap = "artifacts/worker-010/class_binding_reconcile/snapshots/class_coverage.abbaee54a5a3.csv"
    c0_snap = "artifacts/worker-010/class_binding_reconcile/snapshots/af_scc_c0_vacuum.b2ab6acb2bbe.yaml"
    c2_snap = "artifacts/worker-010/class_binding_reconcile/snapshots/af_scc_c2_vacuum.e9a27996dfd3.yaml"
    wcc_snap = "artifacts/worker-010/class_binding_reconcile/snapshots/af_wcc_vacuum.d9cebb9404b2.yaml"
    f0_snap = "artifacts/worker-010/class_binding_reconcile/snapshots/formulation_taxonomy.0abb9ed8a961.yaml"
    drift_rec = "artifacts/worker-010/class_binding_reconcile/drift_w010_cbr.json"

    refs = [
        ev(rel(report_path)), ev(rel(script_path)), ev(rel(verify_path)), ev(rel(verify_script)),
        ev("ledger/theorems.jsonl"), ev("ledger/class_coverage.csv"),
        ev("schemas/af_scc_c0_vacuum.yaml"), ev("schemas/af_scc_c2_vacuum.yaml"),
        ev("schemas/af_wcc_vacuum.yaml"), ev("research_map/formulation_taxonomy.yaml"),
        ev(ledger_snap), ev(matrix_snap), ev(c0_snap), ev(c2_snap), ev(wcc_snap), ev(f0_snap),
        ev(drift_rec),
    ]

    role_conflicts = [f for f in report["direction_findings"] if f["role_conflict"]]
    overlap = sorted({f["theorem_id"] + "|" + f["class_id"] for f in report["direction_findings"]}
                     & set(verify["binding_disagreement_ids"]))
    robust = sorted({f["theorem_id"] + "|" + f["class_id"] for f in report["direction_findings"]}
                    - set(verify["binding_disagreement_ids"]))

    summary_line = (
        f"W010-CBR-01 class-binding / coverage reconciliation at ledger a1674f094979, matrix abbaee54a5a3, "
        f"contracts d9cebb9404b2/e9a27996dfd3/b2ab6acb2bbe/0abb9ed8a961 (rev13 schema bytes: only the "
        f"f0_binding consistency hash moved from rev12, no class-semantics change). Structural: {s['n_ledger_entries']} ledger "
        f"entries, {s['n_bound_entries']} bound, {s['n_bindings']} (entry,class) bindings, 0 unknown class ids; "
        f"{s['n_assessed_cells']} covered/partial matrix cells, each with >=1 bound entry (0 phantom cells, "
        f"0 orphan bindings); 0 role over-grades against the ledger's own conclusion_type; {s['n_multi_class_entries']} "
        f"entries bound to more than one class. Scale warning: {s['cell_to_entry_ratio_global']} matrix cells per bound "
        f"entry, so cell counts are not evidence counts. Direction: the audit's conservative forms flag "
        f"{s['n_bindings_contrary_or_both']} bindings whose own assertion text is the negation-side of the class "
        f"conclusion; {len(role_conflicts)} of those carry a support-grade matrix role (T-301/T-303/T-402/T-526 on C0, "
        f"T-303/T-401/T-402/T-526 on C2, T-102 on WCC-SCALAR-SPH); the independent probe brackets the count at 23. "
        f"Actionable reading: those cells document the open/contrary landscape, not support for the class conclusion."
    )
    falsifier = (
        "Recompute from the same pins and produce either (i) one covered/partial matrix cell with no ledger entry "
        "bound to that (source,class) pair, (ii) one bound entry whose class_id is not one of the four frozen ids, "
        "(iii) one matrix role graded support-grade while the ledger entries in that cell carry a strictly weaker "
        "conclusion_type, or (iv) one round-trip mismatch between the frozen snapshots and the live files. Any one "
        "falsifies the reconciliation; the direction flags additionally fail if a quoted binding sentence does not "
        "carry the negation-side form the audit attributes to it."
    )

    events = [
        {
            "event_id": f"w010-{stamp}-cbr-artifact-report",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-010",
            "run_id": run_id,
            "node_id": "L1",
            "gate": "G-LIT",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": report["class_ids"],
            "artifact_type": "class_binding_reconciliation_audit",
            "path": rel(report_path),
            "sha256": sha256(report_path),
            "bytes": report_path.stat().st_size,
            "validation_status": "unverified",
            "claims_completion": False,
            "summary": summary_line,
            "evidence_refs": refs,
            "falsifier": falsifier,
        },
        {
            "event_id": f"w010-{stamp}-cbr-artifact-verify",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-010",
            "run_id": run_id,
            "node_id": "L1",
            "gate": "G-LIT",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": report["class_ids"],
            "artifact_type": "verification_report",
            "path": rel(verify_path),
            "sha256": sha256(verify_path),
            "bytes": verify_path.stat().st_size,
            "validation_status": "unverified",
            "claims_completion": False,
            "summary": (
                f"Independent second implementation + labeled sensitivity probe: fixtures "
                f"{verify['fixture_agreement']} (all_pass={verify['fixture_all_pass']}); cross-implementation "
                f"binding agreement {verify['binding_cross_implementation_agreement']}; audit flags "
                f"{verify['binding_audit_contrary_count']} contrary-side bindings, independent probe "
                f"{verify['binding_independent_contrary_count']}, intersection "
                f"{verify['binding_contrary_intersection_count']}, union {verify['binding_contrary_union_count']}. "
                f"Robust (flagged by the audit, not reclassified by the probe): {', '.join(robust) if robust else 'none'}. "
                f"Bracketed disagreements: {', '.join(overlap) if overlap else 'none'}. The structural reconciliation "
                f"is implementation-independent; the direction flags are lexical and bracketed."
            ),
            "evidence_refs": [ev(rel(verify_path)), ev(rel(verify_script)), ev(rel(report_path)),
                              ev("ledger/theorems.jsonl"), ev("ledger/class_coverage.csv"),
                              ev("artifacts/worker-010/class_binding_reconcile/relation_fixtures.json")
                              if (ROOT / "artifacts/worker-010/class_binding_reconcile/relation_fixtures.json").exists()
                              else refs[0]],
            "falsifier": ("A fixture the labeled ground truth says is support/contrary/neutral and the independent "
                          "implementation classifies otherwise, or a live file whose bytes differ from its frozen "
                          "snapshot."),
        },
        {
            "event_id": f"w010-{stamp}-cbr-claim",
            "event_type": "claim",
            "created_at": now,
            "actor": "worker-010",
            "run_id": run_id,
            "node_id": "L1",
            "gate": "G-LIT",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": report["class_ids"],
            "conclusion_type": "open_problem",
            "statement": (
                "At ledger/theorems.jsonl a1674f094979 and ledger/class_coverage.csv abbaee54a5a3, class binding is "
                "internally consistent: 34 of 62 entries carry one or more of the four frozen class ids, giving 42 "
                "(entry,class) bindings with 0 unregistered class tokens; all 84 covered/partial matrix cells map to "
                ">=1 bound entry and every bound entry appears in the matrix, so there are no phantom cells and no "
                "orphan bindings; no matrix role outranks the conclusion_type of the ledger entries it covers. Two "
                "measurements qualify the class coverage as evidence: (1) the matrix has 2.47 cells per bound entry "
                "(C0 28 cells / 11 entries), so cell counts overstate independent binding by ~2.5x; (2) a conservative "
                "lexical reading finds 12 (entry,class) bindings whose own assertion text is the negation-side of the "
                "class conclusion (extension exists / naked singularity exists), 9 of them carrying a support-grade "
                "matrix role, and an independent second implementation brackets this at 23 while agreeing on 18/18 "
                "labeled fixtures. The overlap set (T-301, T-303, T-402, T-526 on AF-SCC-C0-VAC-GEN; T-303, T-402, "
                "T-526 on AF-SCC-C2-VAC-GEN; T-102 on AF-WCC-SCALAR-SPH) should be read as documentation of the "
                "open/contrary landscape and must not be counted as evidence for the class conclusions. This is a "
                "ledger/matrix state measurement, not a mathematical result and not a reviewer verdict."
            ),
            "assumptions": [
                "class_ids and conclusion_type are inherited from the ledger as written; this audit does not re-adjudicate them",
                "the coverage matrix role vocabulary is not defined in-repo; the audit declares its reading (role->grade) and applies it uniformly",
                "direction flags are lexical (assertion fields label+statement_exact only, caveats kept separate); the quoted sentence is the evidence",
                "the four class contracts are read from their schemas/F0 at the pinned hashes (rev13 bytes, frozen 00:53:39) and are not modified",
                "live class-schema drifts during the task (rev12->rev13 at 00:53:20) are recorded in drift_w010_cbr.json; the audited bytes are the frozen snapshots",
            ],
            "evidence_refs": refs,
            "artifact_refs": [ev(rel(report_path)), ev(rel(verify_path))],
            "expected_information_gain": (
                "Gives A1/G-LIT readers a single reconciled binding register at the live pins, separates 'the class has "
                "coverage' from 'the class has evidence', and flags the exact cells whose support-grade role is attached "
                "to a contrary-side binding, so no gate verdict can cite those cells as support."
            ),
            "falsifier": falsifier,
        },
        {
            "event_id": f"w010-{stamp}-cbr-status",
            "event_type": "status",
            "created_at": now,
            "actor": "worker-010",
            "run_id": run_id,
            "node_id": "L1",
            "gate": "G-LIT",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": report["class_ids"],
            "status": "active",
            "hours": 0.9,
            "summary": summary_line,
            "evidence_refs": [ev(rel(report_path)), ev(rel(verify_path)), ev("ledger/theorems.jsonl"),
                              ev("ledger/class_coverage.csv"), ev("schemas/af_scc_c0_vacuum.yaml")],
            "next_falsifier": (
                "An independent reviewer binding any of the 9 flagged cells to support-grade evidence, or a re-run of "
                "the audit against a later ledger/matrix revision that changes the binding counts; either moves the "
                "class state rather than this measurement."
            ),
        },
    ]

    lines = [json.dumps(e, ensure_ascii=False) for e in events]
    for line in lines:
        json.loads(line)
    with OUTBOX.open("a", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
    print(f"appended {len(lines)} events to {OUTBOX.relative_to(ROOT)}")
    for e in events:
        print(" ", e["event_id"], "|", e["event_type"], "|", e.get("sha256", "")[:12])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
