#!/usr/bin/env python3
"""Emit W048-F1-PROVENANCE-ANCHOR-CENSUS-01 events to comms/outbox/worker-048.jsonl.

Validates every event against research_map/schemas.py before appending. Worker authority
only: no status=done, no validation_status=passed, no gate verdict.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TASK = "W048-F1-PROVENANCE-ANCHOR-CENSUS-01"
OUTBOX = ROOT / "comms" / "outbox" / "worker-048.jsonl"
HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")

DELIVERABLES = [
    ("PREREGISTRATION.json", "preregistration"),
    ("census_f1_provenance.py", "instrument"),
    ("report.json", "census_report"),
    ("census.tsv", "census_rows"),
    ("README.md", "readme"),
    ("inputs_manifest.json", "inputs_manifest"),
    ("evidence/determinism.json", "determinism_record"),
    ("SHA256SUMS", "hash_manifest"),
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    hashes = {}
    for rel, _kind in DELIVERABLES:
        p = HERE / rel
        if not p.is_file():
            print(f"MISSING {p}", file=sys.stderr)
            return 3
        hashes[rel] = sha256_file(p)

    report = json.loads((HERE / "report.json").read_text(encoding="utf-8"))
    class_id = report["class_id"]
    gate = "G-FORM"
    evidence_refs = [
        f"artifacts/worker-048/f1_provenance_anchor_census/report.json#{hashes['report.json'][:12]}",
        f"artifacts/worker-048/f1_provenance_anchor_census/PREREGISTRATION.json#{hashes['PREREGISTRATION.json'][:12]}",
        f"artifacts/worker-048/f1_provenance_anchor_census/evidence/determinism.json#{hashes['evidence/determinism.json'][:12]}",
        "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
        "ledger/theorems.jsonl#a1674f094979",
        "ledger/citation_audit.csv#315c19145065",
        "artifacts/literature/registry.jsonl#ea02d1943fda",
        "artifacts/literature/FORMULATION_ANCHORS.md#d952d136f880",
    ]
    falsifier = report["falsifier"]

    events = []
    events.append({
        "event_id": "w048-f1anchor-20260912T0130-status-start",
        "event_type": "status", "created_at": NOW, "actor": "worker-048",
        "node_id": "F1", "class_id": class_id, "gate": gate, "status": "active",
        "hours": 0.1,
        "summary": (f"{TASK} taken: no inbox card exists for worker-048 in this fleet wave, so ONE "
                    "bounded class-bound task was self-selected from the live G-FORM/G-LIT critical "
                    "path: a pre-registered, read-only census of F1's eight declared provenance "
                    "citation obligations against the frozen L0/L1 literature artifacts. Read-only "
                    "at six pins; no canonical write."),
        "evidence_refs": evidence_refs,
        "next_falsifier": falsifier,
    })
    for rel, kind in DELIVERABLES:
        events.append({
            "event_id": f"w048-f1anchor-20260912T0130-artifact-{rel.replace('/', '_').replace('.', '_')}",
            "event_type": "artifact", "created_at": NOW, "actor": "worker-048",
            "node_id": "F1", "class_id": class_id, "gate": gate,
            "artifact_type": kind, "path": f"artifacts/worker-048/f1_provenance_anchor_census/{rel}",
            "sha256": hashes[rel], "validation_status": "unverified",
            "summary": f"{TASK} deliverable: {rel}",
            "evidence_refs": evidence_refs,
        })
    events.append({
        "event_id": "w048-f1anchor-20260912T0130-claim",
        "event_type": "claim", "created_at": NOW, "actor": "worker-048",
        "node_id": "F1", "class_id": class_id, "gate": gate,
        "conclusion_type": "formal_model",
        "statement": (
            "At the frozen pins (F1 d9cebb9404b2, L0 ledger a1674f094979, L1 citation audit "
            "315c19145065, registry ea02d1943fda) a pre-registered predicate census with two "
            "byte-identical runs confirms 0 L0 and 0 L1 hits for F1's weighted-Sobolev "
            "(s>5/2, delta in (1/2,1)), positive-mass-rigidity and predictability-equivalence "
            "obligations, and finds one anchor-grade evidence hit for the fifth F1 provenance "
            "obligation (known WCC status for generic AF data) at SRC-001 (DOI 10.5802/crmeca.284, "
            "class_mapping AF-WCC-VAC-GEN, ledger row D-001), plus one metadata-only mention for "
            "MGHD existence/uniqueness at D-008. Machine measurement, not a mathematics claim."),
        "assumptions": [
            "read-only at the six declared pins; no canonical artifact written",
            "predicates, grades and controls pre-registered in PREREGISTRATION.json before the run",
            "anchor_grade requires a statement/subject/title/evidence match plus a record identifier",
            "positive control 'cauchy horizon' reproduces 27 L0 / 30 L1; nonsense predicate 0 hits",
        ],
        "falsifier": falsifier,
        "evidence_refs": evidence_refs,
    })
    events.append({
        "event_id": "w048-f1anchor-20260912T0130-status-complete",
        "event_type": "status", "created_at": NOW, "actor": "worker-048",
        "node_id": "F1", "class_id": class_id, "gate": gate, "status": "active",
        "hours": 0.5,
        "summary": (f"{TASK} complete at worker level: one bounded class-bound task, 8 hash-pinned "
                    "deliverables, 5/5 control groups pass, two runs byte-identical. BL-11's "
                    "zero-hit claim is confirmed for its three named items; O5 is shown to have an "
                    "anchor candidate already in the frozen ledger (SRC-001/D-001). Not a gate "
                    "verdict, no node transition, no validation_status, no canonical write."),
        "evidence_refs": evidence_refs,
        "next_falsifier": ("At the next non-frozen L0/L1 revision or F1 revision: re-run the census at "
                           "the new pins; it is falsified if a newly bound source changes any zero-hit "
                           "row, or if F1 binds O5 to D-001 and the binding is shown to overstate a "
                           "review-level open-status statement."),
    })

    for e in events:
        validate_event(dict(e))
    with OUTBOX.open("a", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"appended {len(events)} events to {OUTBOX}")
    for e in events:
        print(" ", e["event_id"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
