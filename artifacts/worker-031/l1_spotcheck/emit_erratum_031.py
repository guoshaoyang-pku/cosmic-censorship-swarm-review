#!/usr/bin/env python3
"""Emit ERRATUM-01 for the worker-031 L1 spot check and append the correction event.

Why: the spot-check artifact was written from lifecycle_20260912-001746 (count 2), but
by lifecycle_20260912-002155 the controller had already measured 15 binding spot checks.
The ordinality claim ("3rd") and the accidental status=done event are corrected here.
The measured content of the spot check (MATCH x2, controls, raw byte hashes) is unchanged.

Reproduce:
    python3 artifacts/worker-031/l1_spotcheck/emit_erratum_031.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
sys.path.insert(0, str(ROOT / "research_map"))


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> dict:
    from astra_lifecycle import l1_spotchecks  # exact controller scan, not a re-implementation
    from schemas import validate_event

    art = HERE / "spotcheck-l1-031.json"
    art_sha = sha256_file(art)
    ref_lc = ROOT / "runtime/state/controller_verification/lifecycle_20260912-001746.json"
    cur_lc = ROOT / "runtime/state/controller_verification/lifecycle_20260912-002155.json"
    hits = l1_spotchecks("315c19145065")
    now = datetime.now(CST).isoformat(timespec="seconds")

    erratum = {
        "schema_version": "0.1",
        "artifact_type": "l1_spotcheck_erratum",
        "erratum_id": "artifacts/worker-031/l1_spotcheck/ERRATUM-01.json",
        "erratum_of": f"artifacts/worker-031/l1_spotcheck/spotcheck-l1-031.json#{art_sha[:12]}",
        "node_id": "L1",
        "gate": "G-LIT",
        "actor": "worker-031",
        "created_at": now,
        "corrections": [
            {
                "correction_id": "W031-E1",
                "field": "ordinality (check_number / status summary sentence)",
                "was": ("check_number=5 and 'This is the 3rd binding spot check at this hash required by G-LIT', "
                        "computed from lifecycle_20260912-001746.json (00:17:46), which measured 2."),
                "corrected_to": (f"One additional independent spot check, not the third. The controller lifecycle "
                                 f"lifecycle_20260912-002155.json (00:21:55, before this artifact was published) already "
                                 f"measured 15 matching files; the exact controller scan l1_spotchecks('315c19145065') "
                                 f"matches {len(hits)} files at erratum time."),
                "materiality": "none for the measured verdicts; the artifact's checks, controls and byte hashes are unchanged.",
                "evidence_refs": [
                    "runtime/state/controller_verification/lifecycle_20260912-001746.json",
                    "runtime/state/controller_verification/lifecycle_20260912-002155.json",
                ],
            },
            {
                "correction_id": "W031-E2",
                "field": "event authority",
                "was": ("event worker-031-l1-spotcheck-status-20260912T002247 carried status=done, ingested at 00:22:48 "
                        "before it could be overwritten; workers have no authority to promote node status."),
                "corrected_to": ("RETRACTED. Superseded by worker-031-l1-spotcheck-status-20260912T002256 (status=active). "
                                 "No node transition is claimed. apply_events.py's authority guard would keep L1 active "
                                 "regardless; the retraction is explicit so no completion claim is attributed to worker-031."),
                "materiality": "record hygiene; measured L1 status remained 'active' in research_map.json.",
                "evidence_refs": ["research_map/events.jsonl", "research_map/apply_events.py:250-256"],
            },
        ],
        "unchanged_claims": [
            "SRC-094 (row 94, AF-WCC-SCALAR-SPH, arXiv:0711.4620) -> MATCH",
            "SRC-091 (row 91, AF-SCC-C0-VAC-GEN;AF-WCC-VAC-GEN, arXiv:2606.28008) -> MATCH, with exact_locator search-query finding",
            "two negative controls PASS; ledger/citation_audit.csv unchanged at 315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
        ],
        "process_observation": {
            "observation_id": "W031-O1",
            "detail": ("At least 15 independent worker artifacts answer the same one-line G-LIT spot-check criterion "
                       f"(controller count 15 at 00:21:55; {len(hits)} matching files at erratum time). This is duplication "
                       "the audit lead's duplication metric should see; it is not a defect of any single check."),
            "matched_files": hits,
        },
        "falsifier": ("If lifecycle_20260912-002155.json does not record 15 spot checks, or l1_spotchecks('315c19145065') "
                      "does not match the listed files at the recorded time, this erratum is wrong."),
        "gate_verdict_claimed": False,
        "node_status_claimed": False,
    }
    out = HERE / "ERRATUM-01.json"
    out.write_text(json.dumps(erratum, indent=2, sort_keys=True))
    erratum_sha = sha256_file(out)

    events = [
        {
            "event_id": f"worker-031-l1-spotcheck-erratum-{datetime.now(CST).strftime('%Y%m%dT%H%M%S')}",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-031",
            "node_id": "L1",
            "gate": "G-LIT",
            "artifact_type": "l1_spotcheck_erratum",
            "path": "artifacts/worker-031/l1_spotcheck/ERRATUM-01.json",
            "sha256": erratum_sha,
            "validation_status": "unverified",
            "evidence_refs": [f"artifacts/worker-031/l1_spotcheck/spotcheck-l1-031.json#{art_sha[:12]}"],
            "falsifier": erratum["falsifier"],
        },
        {
            "event_id": f"worker-031-l1-spotcheck-correction-{datetime.now(CST).strftime('%Y%m%dT%H%M%S')}",
            "event_type": "status",
            "created_at": now,
            "actor": "worker-031",
            "node_id": "L1",
            "group_id": "literature",
            "gate": "G-LIT",
            "status": "active",
            "hours": 0.1,
            "class_ids": ["AF-WCC-SCALAR-SPH", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN"],
            "task_status": "correction only; worker-031 bounded task complete; no node promotion",
            "summary": ("CORRECTION to worker-031 spot-check status events. (1) The summary sentence '3rd binding spot check' "
                        "is withdrawn: lifecycle_20260912-002155.json (00:21:55, before publication) already measured 15; this "
                        "artifact is one additional independent check. (2) Event worker-031-l1-spotcheck-status-20260912T002247 "
                        "(status=done) is RETRACTED as outside worker authority; superseded by ...002256 (active). Measured "
                        "content unchanged: SRC-094/SRC-091 both MATCH at citation_audit.csv sha256 315c19145065, controls pass, "
                        "raw fetched bytes hashed. See ERRATUM-01.json."),
            "evidence_refs": [
                "artifacts/worker-031/l1_spotcheck/ERRATUM-01.json",
                "runtime/state/controller_verification/lifecycle_20260912-002155.json",
                "artifacts/worker-031/l1_spotcheck/spotcheck-l1-031.json#819fbd62a0bb",
            ],
            "next_falsifier": erratum["falsifier"],
        },
    ]
    outbox = ROOT / "comms/outbox/worker-031.jsonl"
    with outbox.open("a") as f:
        for e in events:
            validate_event(e)
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(json.dumps({"erratum": str(out.relative_to(ROOT)), "sha256": erratum_sha,
                      "spotcheck_files_matched": len(hits)}, indent=2))
    return erratum


if __name__ == "__main__":
    main()
