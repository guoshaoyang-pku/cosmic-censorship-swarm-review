#!/usr/bin/env python3
"""Emit W064-SEMCT-REBIND-01 events to comms/outbox/worker-064.jsonl.

Self-checking: every referenced artifact hash is re-measured and compared with
`manifest.sha256` before any event is written; each event is validated with
`research_map.schemas.validate_event`.  Append-only; event ids are unique.

Usage: python3 emit_events.py [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BUNDLE = Path(__file__).resolve().parent
REPO = BUNDLE.parents[2]
sys.path.insert(0, str(REPO))
from research_map.schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
OUTBOX = REPO / "comms" / "outbox" / "worker-064.jsonl"
TASK = "W064-SEMCT-REBIND-01"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
CLASS_JOINED = ";".join(CLASS_IDS)
NODE = "A1"
GATE = "G-AUDIT"
FALSIFIER = (
    "Re-run semct_rebind_audit.py + determinism_check.py: run A exit != 2, an integrity-error "
    "count != 3, any mutant/frozen-control sha mismatch, run B stage counts differing from "
    "32/11/32, any frozen control accepted by both adopted stages, any current canonical schema "
    "rejected by a stage, or any of the 38 test ids differing on the second run falsifies the "
    "corresponding clause."
)
NOT_CLAIMED = ["no gate verdict", "no node completion", "no mathematical verdict on any schema",
               "no modification of any canonical artifact", "no bytes outside the measured rev25 snapshot"]


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_manifest() -> dict[str, str]:
    lines = (BUNDLE / "manifest.sha256").read_text().splitlines()
    pinned = {}
    for ln in lines:
        h, name = ln.split(maxsplit=1)
        pinned[name.strip()] = h
    bad = [n for n, h in pinned.items() if sha(BUNDLE / n) != h]
    if bad:
        raise SystemExit(f"FAIL: bundle hash mismatch before emission: {bad}")
    return pinned


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pinned = check_manifest()
    ts = now()
    ref = lambda name: f"artifacts/worker-064/semct_rebind/{name}#{pinned[name][:12]}"  # noqa: E731

    events = [
        {
            "event_id": "w064-semct-01-artifact-report",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "worker-064",
            "node_id": NODE,
            "gate": GATE,
            "class_ids": CLASS_IDS,
            "artifact_type": "semantic_contract_suite_rebind_audit",
            "path": "artifacts/worker-064/semct_rebind/report.json",
            "sha256": pinned["report.json"],
            "validation_status": "unverified",
            "summary": (
                "Independent rebind audit of schemas/semantic_contract_tests at rev25: canonical manifest is "
                "unexecutable (exit 2, exactly 3 stale conforming-canonical pins); after rebinding only those "
                "3 pins the suite runs and reproduces 00:14:40 exactly (structural 32/32, baseline 11/32, "
                "hardened 32/32, 0 escapes); validity stays false on ADJ-CONTROL-STALENESS."
            ),
            "evidence_refs": [ref("original_run.json"), ref("rebound_observed.json"), ref("determinism_check.json")],
            "falsifier": FALSIFIER,
        },
        {
            "event_id": "w064-semct-01-artifact-original-run",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "worker-064",
            "node_id": NODE,
            "gate": GATE,
            "class_ids": CLASS_IDS,
            "artifact_type": "suite_integrity_failure_record",
            "path": "artifacts/worker-064/semct_rebind/original_run.json",
            "sha256": pinned["original_run.json"],
            "validation_status": "unverified",
            "summary": (
                "Run A (canonical manifest, unmodified): exit 2 INTEGRITY_FAILURE with exactly 3 sha-mismatch "
                "errors (C0 1bb78ce9b357 != a8d899d2941f; C2 b6123750b37d != 8dae50da1ab5; F1 9a8bd4c96800 "
                "!= b65fcc0f0118); no observed_verdicts.json written; 32/32 mutants and 3/3 frozen controls "
                "byte-intact."
            ),
            "evidence_refs": [ref("report.json"), ref("rebind_patch.json")],
            "falsifier": "A re-run of run A with exit != 2 or an integrity-error count != 3 falsifies this record.",
        },
        {
            "event_id": "w064-semct-01-artifact-rebound-run",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "worker-064",
            "node_id": NODE,
            "gate": GATE,
            "class_ids": CLASS_IDS,
            "artifact_type": "semantic_contract_suite_run",
            "path": "artifacts/worker-064/semct_rebind/rebound_observed.json",
            "sha256": pinned["rebound_observed.json"],
            "validation_status": "unverified",
            "summary": (
                "Run B (worker-local manifest, 3 pins rebound): exit 3, 38 targets run; mutants structural "
                "32/32, semantic baseline 11/32, hardened 32/32; escapes 0; hardened-only 0; frozen controls "
                "0/3 accepted by both adopted stages (all R28-only structural rejects); canonical C0/C2/F1 "
                "3/3 accepted by all three stages; valid_for_calibration=false (ADJ-CONTROL-STALENESS)."
            ),
            "evidence_refs": [ref("rebound_run.json"), ref("manifest_rebound.json"), ref("report.json")],
            "falsifier": "Any per-fixture observed verdict in a re-run differing from this file falsifies the run record.",
        },
        {
            "event_id": "w064-semct-01-artifact-rebind-patch",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "worker-064",
            "node_id": NODE,
            "gate": GATE,
            "class_ids": CLASS_IDS,
            "artifact_type": "manifest_rebind_patch",
            "path": "artifacts/worker-064/semct_rebind/rebind_patch.json",
            "sha256": pinned["rebind_patch.json"],
            "validation_status": "unverified",
            "summary": (
                "Minimal repair: replace exactly 3 conforming_canonical_controls[].sha256 pins in "
                "schemas/semantic_contract_tests/manifest.json (C0->1bb78ce9b357, C2->b6123750b37d, "
                "F1->9a8bd4c96800). Fixtures, controls, rules, expected verdicts and run_record untouched; "
                "canonical manifest NOT modified by this worker."
            ),
            "evidence_refs": [ref("manifest_rebound.json"), ref("report.json")],
            "falsifier": "Any additional field differing between manifest_rebound.json and the canonical manifest beyond the 3 pins and the worker_rebind record falsifies minimality.",
        },
        {
            "event_id": "w064-semct-01-artifact-determinism",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "worker-064",
            "node_id": NODE,
            "gate": GATE,
            "class_ids": CLASS_IDS,
            "artifact_type": "determinism_control",
            "path": "artifacts/worker-064/semct_rebind/determinism_check.json",
            "sha256": pinned["determinism_check.json"],
            "validation_status": "unverified",
            "summary": "Second independent run of the rebound suite: exit 3, 38/38 test ids identical, 0 differences in per-fixture observed records, summary, validity, or stage hashes.",
            "evidence_refs": [ref("rebound_observed_2.json"), ref("rebound_observed.json")],
            "falsifier": "Any entry appearing in the second run's differences list invalidates the single-run numbers.",
        },
        {
            "event_id": "w064-semct-01-review-suite",
            "event_type": "review",
            "created_at": ts,
            "actor": "worker-064",
            "target_id": "schemas/semantic_contract_tests/manifest.json#b2e8bd17892b",
            "reviewer": "worker-064",
            "verdict": "revise",
            "score": 3,
            "node_id": NODE,
            "gate": GATE,
            "class_ids": CLASS_IDS,
            "hard_failures": [
                "HF-SEMCT-1: run_contract_tests.py exits 2 INTEGRITY_FAILURE on the canonical manifest; the three conforming_canonical_controls pins predate the 00:19:14 republish and no calibration output is produced.",
                "HF-SEMCT-2: the 00:14:40 run_record numbers are bound to schema bytes no longer at the canonical paths; they cannot be cited for rev25 until rebound and re-run.",
                "HF-SEMCT-3: valid_for_calibration is false at rev25 (3/3 frozen controls rejected by structural R28); ADJ-CONTROL-STALENESS is unresolved.",
            ],
            "findings": [
                "Positive: the mutated corpus and frozen controls are byte-intact (35/35 pins match); the defect is pin staleness only.",
                "Positive: after the 3-pin rebind the suite runs and reproduces every 00:14:40 number exactly, with identical stage tool hashes and a clean second-run determinism control.",
                "Positive: current canonical C0/C2/F1 are accepted by all three stages (structural, semantic baseline, proposed hardened).",
                "Numeric: structural 32/32, semantic baseline 11/32, hardened 32/32; 0 adopted-stage escapes; 0 hardened-only catches; 20 rephrased mutants, 32 leak families.",
                "Note: run A wrote no observed_verdicts.json, so the canonical suite's last recorded run remains 00:14:40 and is stale with respect to canonical bytes.",
            ],
            "evidence_refs": [ref("report.json"), ref("original_run.json"), ref("rebound_observed.json"), ref("determinism_check.json")],
            "falsifier": FALSIFIER,
        },
        {
            "event_id": "w064-semct-01-claim",
            "event_type": "claim",
            "created_at": ts,
            "actor": "worker-064",
            "node_id": NODE,
            "gate": GATE,
            "class_id": CLASS_JOINED,
            "conclusion_type": "numerical_evidence",
            "statement": (
                "At the frozen rev25 bytes (C0 1bb78ce9b357, C2 b6123750b37d, F1 9a8bd4c96800; stage tools "
                "check_class_schema.py 000e09e46b2f and spec_conformance_audit.py c79d8ab8440a unchanged since "
                "00:14:40): (1) schemas/semantic_contract_tests/manifest.json pins all three "
                "conforming_canonical_controls to superseded bytes, so the suite exits 2 with exactly 3 "
                "integrity errors and produces no calibration output; (2) after replacing only those 3 sha256 "
                "pins the suite runs to completion and reproduces the 00:14:40 numbers exactly - structural "
                "32/32 mutants caught, semantic baseline 11/32, proposed hardened 32/32, 0 adopted-stage "
                "escapes, 0 hardened-only catches, 38/38 test ids identical on an independent second run; "
                "(3) validity.valid_for_calibration remains false because all 3 frozen controls are rejected "
                "by the structural stage on R28 only while all 3 current canonical schemas are accepted by "
                "all three stages (ADJ-CONTROL-STALENESS unresolved)."
            ),
            "assumptions": [
                "the canonical paths schemas/*.yaml and schemas/semantic_contract_tests/manifest.json are the binding inputs at measurement time",
                "the runner's own integrity semantics (exit 2 = missing/tampered fixture or no verdict) define 'unexecutable'",
                "byte-identity of the copied fixture tree to the canonical fixture tree was established by the manifest's own pinned sha256 values",
            ],
            "evidence_refs": [ref("report.json"), ref("original_run.json"), ref("rebound_observed.json"), ref("rebind_patch.json"), ref("determinism_check.json")],
            "artifact_refs": ["artifacts/worker-064/semct_rebind/report.json"],
            "falsifier": FALSIFIER,
            "not_claimed": NOT_CLAIMED,
        },
        {
            "event_id": "w064-semct-01-blocker",
            "event_type": "blocker",
            "created_at": ts,
            "actor": "worker-064",
            "node_id": NODE,
            "gate": GATE,
            "class_ids": CLASS_IDS,
            "description": (
                "The semantic contract suite - G-AUDIT calibration evidence for the three frozen classes - is "
                "currently unusable at rev25 for two mechanical reasons, both measured: (a) the canonical "
                "manifest pins the three conforming_canonical_controls to pre-00:19:14 bytes, so the runner "
                "exits 2 INTEGRITY_FAILURE before producing any output; (b) after rebinding, "
                "ADJ-CONTROL-STALENESS still forces valid_for_calibration=false because the three frozen "
                "controls are rejected by structural R28 only. The mutant corpus itself is intact and the "
                "mutant numbers are unaffected."
            ),
            "needed_to_unblock": (
                "(1) owner astra-lead-formulation applies the 3-pin rebind from rebind_patch.json (or "
                "republishes the canonical schemas at the pinned bytes); (2) owner astra-lead-formulation "
                "resolves ADJ-CONTROL-STALENESS by rebasing the three frozen controls to the current "
                "canonical layout or by pinning the calibration gate revision; (3) a worker re-runs this "
                "audit harness to certify an exit-0, valid_for_calibration=true window with updated pins."
            ),
            "evidence_refs": [ref("report.json"), ref("original_run.json"), ref("rebound_observed.json"), ref("rebind_patch.json")],
            "falsifier": "A run in which the canonical manifest executes (exit 0 or 3) and valid_for_calibration=true falsifies this blocker.",
        },
        {
            "event_id": "w064-semct-01-status",
            "event_type": "status",
            "created_at": ts,
            "actor": "worker-064",
            "node_id": NODE,
            "gate": GATE,
            "class_ids": CLASS_IDS,
            "status": "active",
            "hours": 0.5,
            "summary": (
                "W064-SEMCT-REBIND-01 complete at worker level (no inbox card existed for worker-064). One "
                "class-bound task taken: independent rebind audit + full re-run of the semantic contract "
                "suite at rev25. Verdict REBIND_REQUIRED / VALIDITY_FALSE; reproduces worker-059's exit-2 "
                "observation and gives the exact 3-pin cause plus a determinism-controlled set of rev25 "
                "numbers. No canonical file modified; status stays active and no gate is touched."
            ),
            "evidence_refs": [ref("report.json"), ref("rebound_observed.json"), ref("determinism_check.json")],
            "next_falsifier": (
                "After the lead applies the pin patch and resolves ADJ-CONTROL-STALENESS, re-run "
                "semct_rebind_audit.py and determinism_check.py; expect run A exit 0, "
                "valid_for_calibration=true, frozen controls 3/3 accepted, and unchanged 32/11/32 mutant "
                "counts. Any deviation falsifies the repair."
            ),
            "not_claimed": NOT_CLAIMED,
        },
    ]

    for e in events:
        validate_event(e)

    payload = "".join(json.dumps(e, sort_keys=True) + "\n" for e in events)
    if args.dry_run:
        print(payload)
        print(f"[dry-run] {len(events)} events validated; nothing written")
        return 0
    with OUTBOX.open("a") as fh:
        fh.write(payload)
    print(f"wrote {len(events)} validated events to {OUTBOX.relative_to(REPO)}")
    print("ids:", ", ".join(e["event_id"] for e in events))
    return 0


if __name__ == "__main__":
    sys.exit(main())
