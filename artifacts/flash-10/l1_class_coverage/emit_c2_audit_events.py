#!/usr/bin/env python3
"""Emit the flash-10 L1 outbox events for the AF-SCC-C2-VAC-GEN conformance audit.

Appends validated JSON lines to comms/outbox/deepseek-flash-10.jsonl.  Every event is checked
against research_map.schemas.validate_event before it is written; nothing is written on failure.
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
TZ = timezone(timedelta(hours=8))
CLASS = "AF-SCC-C2-VAC-GEN"


def h(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def main() -> int:
    now = datetime.now(TZ)
    ts = now.strftime("%Y%m%dT%H%M%S")
    ledger_h = h("ledger/theorems.jsonl")
    audit_h = h("artifacts/flash-10/l1_class_coverage/c2_class_conformance_audit.json")
    matrix_h = h("ledger/class_coverage.csv")
    summary_h = h("artifacts/flash-10/l1_class_coverage/coverage_summary.json")
    schema_h = h("schemas/af_scc_c2_vacuum.yaml")

    common = {
        "actor": "deepseek-flash-10",
        "run_id": "run-2026-09-11T23:15+08:00",
        "created_at": now.isoformat(timespec="seconds"),
        "gate": "G-LIT",
        "assignment_ref": "asg-2026-09-11-L1-deepseek-flash-10-19",
    }

    events = [
        {**common, "event_id": f"flash-10-artifact-matrix-rebuild-{ts}", "event_type": "artifact",
         "node_id": "L1", "class_id": "GLOBAL", "artifact_type": "csv", "path": "ledger/class_coverage.csv",
         "sha256": matrix_h, "bytes": (ROOT / "ledger/class_coverage.csv").stat().st_size, "rows": 388,
         "sources": 97, "validation_status": "unverified", "claims_completion": False,
         "inputs": {"ledger/theorems.jsonl": ledger_h, "ledger/citation_audit.csv": h("ledger/citation_audit.csv"),
                    "artifacts/literature/registry.jsonl": h("artifacts/literature/registry.jsonl")},
         "evidence_refs": [f"ledger/theorems.jsonl#{ledger_h[:12]}", f"ledger/class_coverage.csv#{matrix_h[:12]}",
                           f"artifacts/flash-10/l1_class_coverage/coverage_summary.json#{summary_h[:12]}"],
         "falsifier": "Re-run artifacts/flash-10/l1_class_coverage/build_ledger_class_coverage.py against ledger/theorems.jsonl at the recorded hash and obtain a different matrix hash or different per-class counts.",
         "summary": "Deterministic rebuild of the L1 matrix after ledger drift 7d78d285 -> " + ledger_h[:12] + " (388 rows = 97 sources x 4 frozen classes; covered 21 / partial 63 / none 284 / unassessed 20). Counts for all four classes, including AF-SCC-C2-VAC-GEN covered=3 (SRC-022/080/081), are unchanged; the delta is 2 new unassessed sources (SRC-096/097). validation_status=unverified pending lead-literature/A1."},

        {**common, "event_id": f"flash-10-artifact-coverage-summary-2-{ts}", "event_type": "artifact",
         "node_id": "L1", "class_id": "GLOBAL", "artifact_type": "json",
         "path": "artifacts/flash-10/l1_class_coverage/coverage_summary.json", "sha256": summary_h,
         "bytes": (ROOT / "artifacts/flash-10/l1_class_coverage/coverage_summary.json").stat().st_size,
         "validation_status": "unverified", "claims_completion": False,
         "evidence_refs": [f"artifacts/flash-10/l1_class_coverage/coverage_summary.json#{summary_h[:12]}",
                           f"ledger/class_coverage.csv#{matrix_h[:12]}"],
         "inputs": {"ledger/theorems.jsonl": ledger_h},
         "falsifier": "Any count in coverage_summary.json that does not reproduce from ledger/theorems.jsonl at the recorded hash.",
         "summary": "Counts and input hashes for the rebuilt matrix; AF-SCC-C2-VAC-GEN covered_sources=[SRC-022, SRC-080, SRC-081]."},

        {**common, "event_id": f"flash-10-artifact-c2-conformance-{ts}", "event_type": "artifact",
         "node_id": "L1", "class_id": CLASS, "artifact_type": "json",
         "path": "artifacts/flash-10/l1_class_coverage/c2_class_conformance_audit.json", "sha256": audit_h,
         "bytes": (ROOT / "artifacts/flash-10/l1_class_coverage/c2_class_conformance_audit.json").stat().st_size,
         "validation_status": "unverified", "claims_completion": False,
         "evidence_refs": [f"artifacts/flash-10/l1_class_coverage/c2_class_conformance_audit.json#{audit_h[:12]}",
                           f"ledger/theorems.jsonl#{ledger_h[:12]}", f"schemas/af_scc_c2_vacuum.yaml#{schema_h[:12]}",
                           f"ledger/class_coverage.csv#{matrix_h[:12]}"],
         "inputs": {"ledger/theorems.jsonl": ledger_h, "schemas/af_scc_c2_vacuum.yaml": schema_h,
                    "ledger/class_coverage.csv": matrix_h},
         "falsifier": "One accepted ledger entry bound to AF-SCC-C2-VAC-GEN that is generic AF vacuum Cauchy data, concludes future C2-inextendibility, and has peer-reviewed/accepted-in-press evidence with no open hypothesis.",
         "summary": "Class-bound conformance audit of every accepted ledger entry bound to AF-SCC-C2-VAC-GEN (10 entries: D-003/004/005/007, T-303, T-305, T-401, T-402, T-526, T-527) against the canonical F2a class definition at " + schema_h[:12] + ": 0 entries discharge all of D1 (generic residual one-ended AF vacuum Cauchy data) + D2 (future C2-inextendibility) + D3 (accepted, no open hypothesis, peer-reviewed/accepted-in-press). The three `covered` matrix cells are binding-strength only."},

        {**common, "event_id": f"flash-10-claim-c2-conformance-{ts}", "event_type": "claim", "node_id": "L1",
         "class_id": CLASS, "conclusion_type": "open_problem",
         "statement": ("AF-SCC-C2-VAC-GEN has 10 accepted ledger entries bound to it and 0 that discharge the frozen class "
                       "conclusion. Every theorem-strength binding is either special non-generic data (T-303, peer-reviewed, "
                       "C0-extension/non-L2-connection construction), characteristic-interior and preprint (T-526, genericity "
                       "not quantified as open/dense, ledger scope caveat says the class binding is provisional), or conditional "
                       "on a curvature-blow-up hypothesis supplied only by T-526 (T-527, accepted-in-press). The remaining bindings "
                       "are 4 definitions (D-003/004/005/007), 1 conditional preprint (T-305) and the open-problem/literature-status "
                       "entries T-401/T-402. Therefore the 3 `covered` cells for this class in ledger/class_coverage.csv "
                       "(SRC-022/080/081) are binding-strength only, not a class conclusion; the class stays open, consistent with "
                       "the canonical schema's own claim_promotion=open_problem."),
         "assumptions": ["class_ids and status are inherited from ledger/theorems.jsonl revision " + ledger_h[:12] + "; this audit does not re-adjudicate them (A1's job)",
                         "D1/D2/D3 are mechanical readings of the entries' genericity/scope_caveats/unresolved/entry_kind/evidence_level fields; a reviewer may bind an entry differently",
                         "the class definition is quoted from canonical schemas/af_scc_c2_vacuum.yaml at sha256 " + schema_h[:12] + "; the map's G-FORM gate text still names 23fec0e9, recorded as a revision-in-flight observation, not adjudicated here"],
         "falsifier": ("Produce one accepted ledger entry bound to AF-SCC-C2-VAC-GEN that (i) quantifies over generic (residual/comeagre) "
                       "one-ended asymptotically flat vacuum Cauchy data, (ii) concludes future C2-inextendibility of the maximal development, "
                       "and (iii) is peer-reviewed or accepted-in-press with no open hypothesis; then n_discharging >= 1 and this claim is falsified."),
         "evidence_refs": [f"ledger/class_coverage.csv#{matrix_h[:12]}",
                           f"artifacts/flash-10/l1_class_coverage/c2_class_conformance_audit.json#{audit_h[:12]}",
                           f"ledger/theorems.jsonl#{ledger_h[:12]}", f"schemas/af_scc_c2_vacuum.yaml#{schema_h[:12]}"],
         "artifact_refs": [f"artifacts/flash-10/l1_class_coverage/c2_class_conformance_audit.json#{audit_h[:12]}",
                           f"ledger/class_coverage.csv#{matrix_h[:12]}"],
         "expected_information_gain": "Turns the matrix's most important `covered` cell into an explicit strength verdict and gives A1 a per-entry checklist for the C2 scope queue."},

        {**common, "event_id": f"flash-10-status-c2-conformance-{ts}", "event_type": "status", "node_id": "L1",
         "class_id": CLASS, "status": "active", "hours": 0.5,
         "summary": ("Executed one class-bound task on AF-SCC-C2-VAC-GEN within the L1 assignment: rebuilt the matrix after ledger "
                     "drift (7d78d285 -> " + ledger_h[:12] + "; class counts unchanged, C2 covered=3) and ran the class-conformance "
                     "audit against the canonical F2a schema (" + schema_h[:12] + "). Result: 0/10 bound entries discharge the class "
                     "conclusion; the C2 `covered` cells are binding-strength only. No completion claimed; validation_status=unverified."),
         "evidence_refs": [f"artifacts/flash-10/l1_class_coverage/c2_class_conformance_audit.json#{audit_h[:12]}",
                           f"ledger/class_coverage.csv#{matrix_h[:12]}", f"ledger/theorems.jsonl#{ledger_h[:12]}",
                           f"schemas/af_scc_c2_vacuum.yaml#{schema_h[:12]}"],
         "next_falsifier": ("Either (a) a peer-reviewed generic AF vacuum C2-inextendibility theorem appears bound to AF-SCC-C2-VAC-GEN "
                            "(promotes the class and falsifies the claim), or (b) A1/A2 reject one of the ten bindings as class leakage "
                            "(demotes it and strengthens the gap), or (c) T-526 is peer-reviewed and F1 rules that characteristic interior "
                            "data satisfy the class's D1 data class (partially closes the gap, must then be re-audited at the new schema hash).")},
    ]

    lines = []
    for e in events:
        validate_event(e)
        lines.append(json.dumps(e, ensure_ascii=False))
    with OUTBOX.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"appended {len(lines)} validated events to {OUTBOX.relative_to(ROOT)}")
    for e in events:
        print(" ", e["event_type"], e["event_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
