#!/usr/bin/env python3
"""Emit the DET-REV12 candidate-audit events for worker-009 to comms/outbox.

Idempotent: existing event_ids in the outbox are skipped.  All paths are bound by
recomputed sha256; nothing is trusted from the record's own hash fields.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTBOX = ROOT / "comms" / "outbox" / "worker-009.jsonl"
RECORD = ROOT / "artifacts" / "worker-009" / "detrev12" / "verification_candidates_worker-009.json"
PATCH_CSV = ROOT / "ledger" / "citation_audit_scc_candidates_worker-009.csv"
PATCH_JSONL = ROOT / "ledger" / "citation_audit_scc_candidates_worker-009.jsonl"
DRYRUN = ROOT / "artifacts" / "worker-009" / "detrev12" / "dryrun_applied_citation_audit_12row.csv"
TOOL = ROOT / "artifacts" / "worker-009" / "detrev12" / "verify_candidates.py"

CLASS_IDS = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
ASSIGNMENT = "asg-2026-09-11-L1-deepseek-flash-09-18"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    rec = json.loads(RECORD.read_text())
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    ts = now.replace("-", "").replace(":", "").replace("+", "").replace("T", "T")[:15]

    h_record = sha(RECORD)
    h_patch_csv = sha(PATCH_CSV)
    h_patch_jsonl = sha(PATCH_JSONL)
    h_dryrun = sha(DRYRUN)
    h_tool = sha(TOOL)

    ledger = "ledger/citation_audit.csv#315c19145065a5f9"
    patch7 = "ledger/citation_audit_scc_classbinding_worker-009.csv#47917e0e54bc447b"
    theorems = "ledger/theorems.jsonl#a1674f09497975cf"
    f2a = "schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc7196"
    f2b = "schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda96b8"
    frozen = "artifacts/formulation/FROZEN.json#2f358f6722d92062"
    sources = [
        "artifacts/worker-009/detrev12/src/1707_08975.tar.gz#43c124b5fad5beac",
        "artifacts/worker-009/detrev12/src/1805_08764.tar.gz#90b4104c885f4607",
        "artifacts/worker-009/detrev12/src/2609_05167.tar.gz#5561438d671ae463",
        "artifacts/worker-009/detrev12/src/gr-qc_0309115.tar.gz#80be01a4222ba815",
        "artifacts/worker-009/detrev12/src/abs_math_9901147.html#917a7cbf590eb78a",
    ]
    base_ev = [ledger, patch7, theorems, f2a, f2b, frozen] + sources

    counts = rec["counts"]
    promoted = [c["citation_id"] for c in rec["candidates"] if c["decision"] == "PROMOTE"]
    dropped = [c["citation_id"] for c in rec["candidates"] if c["decision"] == "DROP"]

    events = [
        {
            "event_id": f"w009-detrev12-{ts}-artifact-01",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-009",
            "assignment_id": ASSIGNMENT,
            "node_id": "L1",
            "gate": "G-LIT",
            "group_id": "literature",
            "class_id": CLASS_IDS[0],
            "class_ids": CLASS_IDS,
            "artifact_type": "verification_record",
            "path": str(RECORD.relative_to(ROOT)),
            "sha256": h_record,
            "validation_status": "unverified",
            "note": (
                "DET-REV12 uncovered-candidate audit: 5/5 candidates re-fetched from primary sources "
                f"and PROMOTED to class-binding corrections ({', '.join(promoted)}); 0 dropped; "
                f"{len(rec['checks'])} checks all PASS; canonical ledger untouched."
            ),
            "evidence_refs": base_ev
            + [
                f"artifacts/worker-009/detrev12/src/x1707/Price_law_revised.tex#a1220288344974e9",
                f"artifacts/worker-009/detrev12/src/x1805/revision.tex#938f172376a2a2e1",
                f"artifacts/worker-009/detrev12/src/x2609/main.tex#fbe4776ab2eed09d",
                f"artifacts/worker-009/detrev12/src/x0309115/pricelaw3.tex#e930b36f8282e585",
                "artifacts/worker-009/classbinding/verification_classbinding_rev12_worker-009.json#babf76de1b87c745",
            ],
        },
        {
            "event_id": f"w009-detrev12-{ts}-artifact-02",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-009",
            "assignment_id": ASSIGNMENT,
            "node_id": "L1",
            "gate": "G-LIT",
            "group_id": "literature",
            "class_id": CLASS_IDS[0],
            "class_ids": CLASS_IDS,
            "artifact_type": "class_binding_correction_patch",
            "path": str(PATCH_CSV.relative_to(ROOT)),
            "sha256": h_patch_csv,
            "validation_status": "unverified",
            "note": (
                "5 new machine-applicable correction rows CBC-09-008..012 (same 21-column schema as "
                "the 7-row patch); combined 12-row patch applies to the frozen canonical ledger."
            ),
            "evidence_refs": [ledger, patch7, f"artifacts/worker-009/detrev12/verification_candidates_worker-009.json#{h_record[:16]}"],
        },
        {
            "event_id": f"w009-detrev12-{ts}-artifact-03",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-009",
            "assignment_id": ASSIGNMENT,
            "node_id": "L1",
            "gate": "G-LIT",
            "group_id": "literature",
            "class_id": CLASS_IDS[0],
            "class_ids": CLASS_IDS,
            "artifact_type": "class_binding_correction_patch_jsonl",
            "path": str(PATCH_JSONL.relative_to(ROOT)),
            "sha256": h_patch_jsonl,
            "validation_status": "unverified",
            "note": "JSONL mirror of the 5-row correction proposal with class_ids, gate, node and falsifier.",
            "evidence_refs": [ledger, f"artifacts/worker-009/detrev12/verification_candidates_worker-009.json#{h_record[:16]}"],
        },
        {
            "event_id": f"w009-detrev12-{ts}-artifact-04",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-009",
            "assignment_id": ASSIGNMENT,
            "node_id": "L1",
            "gate": "G-LIT",
            "group_id": "literature",
            "class_id": CLASS_IDS[0],
            "class_ids": CLASS_IDS,
            "artifact_type": "dryrun_applied_ledger",
            "path": str(DRYRUN.relative_to(ROOT)),
            "sha256": h_dryrun,
            "validation_status": "unverified",
            "note": (
                "12-row patch dry-run on a byte-faithful copy of the frozen canonical ledger: 97x25, "
                "exactly 12 class_mapping cells changed, every other byte identical; dryrun only."
            ),
            "evidence_refs": [ledger, f"ledger/citation_audit_scc_candidates_worker-009.csv#{h_patch_csv[:16]}"],
        },
        {
            "event_id": f"w009-detrev12-{ts}-artifact-05",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-009",
            "assignment_id": ASSIGNMENT,
            "node_id": "L1",
            "gate": "G-LIT",
            "group_id": "literature",
            "class_id": CLASS_IDS[0],
            "class_ids": CLASS_IDS,
            "artifact_type": "tool",
            "path": str(TOOL.relative_to(ROOT)),
            "sha256": h_tool,
            "validation_status": "unverified",
            "note": (
                "deterministic verifier (no wall clock inside; --verified-at supplied): input binding, "
                "verbatim quote extraction + hashing, mechanical promotion rule, 12-row dry-run apply, "
                "negative control, untouched-cell check."
            ),
            "evidence_refs": [f"artifacts/worker-009/detrev12/verification_candidates_worker-009.json#{h_record[:16]}"],
        },
        {
            "event_id": f"w009-detrev12-{ts}-review-01",
            "event_type": "review",
            "created_at": now,
            "actor": "worker-009",
            "assignment_id": ASSIGNMENT,
            "node_id": "L1",
            "gate": "G-LIT",
            "group_id": "literature",
            "class_id": CLASS_IDS[0],
            "class_ids": CLASS_IDS,
            "target_id": "ledger/citation_audit_scc_candidates_worker-009.csv",
            "reviewer": "worker-009",
            "verdict": "accept",
            "score": 4.0,
            "review_scope": (
                "author self-verification of a machine-applied patch at pinned hashes; NOT an independent "
                "author review - lead-literature must still adjudicate the five verbatim quotes"
            ),
            "hard_failures": [],
            "findings": [
                f"All {len(rec['checks'])} declared checks PASS; 5/5 candidates promoted, 0 dropped.",
                "Verbatim quotes: SRC-029 thmMain = spherically symmetric Einstein-Maxwell-scalar with Lambda>0 (no C^2 extensions); SRC-033 maintheoremINTRO = linear wave on fixed subextremal RN-dS/KN-dS, Lambda>0; SRC-048 cor:RNV/cor:DLO = RN-Vaidya and EM-scalar spherical perturbations, extension class C^0 cap W^{1,s}_loc; SRC-061 int-the = Einstein-Maxwell-scalar with compactly supported scalar field; SRC-014 title/abstract = spherical gravitational collapse of a scalar field.",
                "Root causes at the frozen theorem hash a1674f09 persist: D-004 (SRC-029), D-007 (SRC-014/033), D-005 (SRC-048), D-002 (SRC-061) still carry frozen vacuum class ids; the row patch is necessary but not sufficient, the derivation must be fixed at the theorem layer or the leak returns.",
                "SRC-014 and SRC-061 retain their AF-WCC-SCALAR-SPH tag (supported by T-101/T-523/T-525 and T-516 respectively); only the SCC-side frozen vacuum binding is struck - recorded explicitly rather than deleting the whole cell.",
                "Residual: the math/9901147 e-print returned HTTP 403, so SRC-014 rests on the arXiv title/abstract page (authoritative metadata), not the full TeX; flagged in the record as refetch_note and in that candidate's falsifier.",
                "Dry run: combined 12-row patch changes exactly 12 of 97 class_mapping cells; no other cell differs; negative control with a stale old_class_mapping is refused.",
            ],
            "artifact_refs": [
                f"artifacts/worker-009/detrev12/verification_candidates_worker-009.json#{h_record[:16]}",
                f"ledger/citation_audit_scc_candidates_worker-009.csv#{h_patch_csv[:16]}",
                f"artifacts/worker-009/detrev12/dryrun_applied_citation_audit_12row.csv#{h_dryrun[:16]}",
            ],
            "evidence_refs": base_ev,
            "falsifier": rec["falsifier"],
        },
        {
            "event_id": f"w009-detrev12-{ts}-status-01",
            "event_type": "status",
            "created_at": now,
            "actor": "worker-009",
            "assignment_id": ASSIGNMENT,
            "node_id": "L1",
            "gate": "G-LIT",
            "group_id": "literature",
            "class_id": CLASS_IDS[0],
            "class_ids": CLASS_IDS,
            "status": "active",
            "hours": 1.0,
            "summary": (
                "Bounded class-bound task (worker-009, L1/G-LIT): closed the DET-REV12 uncovered-candidate "
                "surface left by the 00:43 pass. Re-fetched all five candidates from primary sources "
                "(arXiv e-prints; math/9901147 e-print 403 so its authoritative abs page was used), extracted "
                "and hashed 21 verbatim quotes with exact line numbers, and applied the declared promotion "
                "rule mechanically: 5 PROMOTE / 0 DROP. The five rows SRC-014, SRC-029, SRC-033, SRC-048, "
                "SRC-061 are non-vacuum / non-Lambda=0 and cannot carry frozen AF-SCC-C2/C0-VAC-GEN ids. "
                "Proposal CBC-09-008..012 applies with the existing 7-row patch: 12/97 class_mapping cells "
                "change, no other byte. Canonical ledger untouched; lead-literature adjudicates."
            ),
            "evidence_refs": [
                f"artifacts/worker-009/detrev12/verification_candidates_worker-009.json#{h_record[:16]}",
                f"ledger/citation_audit_scc_candidates_worker-009.csv#{h_patch_csv[:16]}",
                f"artifacts/worker-009/detrev12/dryrun_applied_citation_audit_12row.csv#{h_dryrun[:16]}",
                ledger,
                theorems,
            ]
            + sources,
            "next_falsifier": (
                "Run DET-REV12 over the 12-row dry-run ledger: it must return zero uncovered candidates on "
                "the patched rows; a surviving frozen vacuum id on SRC-014/029/033/048/061, a re-fetch "
                "showing any source is 4D Einstein vacuum Lambda=0, or a theorem-layer regeneration that "
                "reintroduces a frozen id, falsifies this pass. Independent lead-literature review of the "
                "five quote sets is still required."
            ),
        },
    ]

    seen = set()
    kept = []
    removed = 0
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                kept.append(line)
                continue
            seen.add(e.get("event_id"))
            if str(e.get("event_id", "")).startswith("w009-detrev12-"):
                removed += 1
                continue  # replaced below (same pass re-emitted at pinned hashes)
            kept.append(line)

    # fail closed if a previous detrev12 event was already ingested by the controller
    ingested_path = ROOT / "runtime" / "state" / "ingested_ids.json"
    if ingested_path.exists():
        ingested = ingested_path.read_text()
        stale = [e for e in seen if str(e).startswith("w009-detrev12-") and e in ingested]
        if stale:
            print(json.dumps({"error": "detrev12 events already ingested; refusing to rewrite", "stale": stale}))
            return 2

    new = [e for e in events if e["event_id"] not in seen]
    with OUTBOX.open("w") as f:
        for line in kept:
            f.write(line + "\n")
        for e in new:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    print(json.dumps({
        "outbox": str(OUTBOX.relative_to(ROOT)),
        "created_at": now,
        "written": len(new),
        "replaced_previous": removed,
        "event_ids": [e["event_id"] for e in new],
        "record_sha256": h_record,
        "patch_csv_sha256": h_patch_csv,
        "patch_jsonl_sha256": h_patch_jsonl,
        "dryrun_sha256": h_dryrun,
        "tool_sha256": h_tool,
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
