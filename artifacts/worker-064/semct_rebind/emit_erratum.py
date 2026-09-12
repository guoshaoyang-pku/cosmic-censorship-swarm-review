#!/usr/bin/env python3
"""Emit the single W064 erratum event (bytecode-cache side effect) to the outbox.

Reads and hash-checks `manifest.sha256`, validates the event with
`research_map.schemas.validate_event`, appends one line to
`comms/outbox/worker-064.jsonl`.

Usage: python3 emit_erratum.py [--dry-run]
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


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pinned = {}
    for ln in (BUNDLE / "manifest.sha256").read_text().splitlines():
        h, name = ln.split(maxsplit=1)
        pinned[name.strip()] = h
    bad = [n for n, h in pinned.items() if sha(BUNDLE / n) != h]
    if bad:
        raise SystemExit(f"FAIL: bundle hash mismatch before erratum: {bad}")
    if (REPO / "schemas/semantic_contract_tests/__pycache__").exists():
        raise SystemExit("FAIL: bytecode cache still present under the canonical suite dir")

    suite = REPO / "schemas" / "semantic_contract_tests"
    event = {
        "event_id": "w064-semct-01-erratum-bytecode-cache",
        "event_type": "artifact",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "actor": "worker-064",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "artifact_type": "erratum",
        "path": "artifacts/worker-064/semct_rebind/ERRATUM.md",
        "sha256": pinned["ERRATUM.md"],
        "validation_status": "unverified",
        "summary": (
            "Erratum to the W064-SEMCT-REBIND-01 README sentence 'the shared suite directory was never "
            "written to': importing the runner wrote a transient bytecode cache "
            "schemas/semantic_contract_tests/__pycache__/run_contract_tests.cpython-310.pyc (10301 bytes, "
            "00:27); it was removed at 00:29 and no canonical artifact changed (manifest b2e8bd17892b, "
            "observed c6b81c9c957b, runner 3be197c3729c, 35/35 fixtures unchanged). Corrected wording is in "
            "ERRATUM.md; report.json numbers, findings and falsifiers are unaffected."
        ),
        "evidence_refs": [
            f"artifacts/worker-064/semct_rebind/ERRATUM.md#{pinned['ERRATUM.md'][:12]}",
            f"artifacts/worker-064/semct_rebind/report.json#{pinned['report.json'][:12]}",
            f"schemas/semantic_contract_tests/manifest.json#{sha(suite / 'manifest.json')[:12]}",
            f"schemas/semantic_contract_tests/observed_verdicts.json#{sha(suite / 'observed_verdicts.json')[:12]}",
        ],
        "falsifier": (
            "Any canonical suite artifact differing from the hashes in report.json#fixture_integrity, or any "
            "file remaining under schemas/semantic_contract_tests/__pycache__/, falsifies this erratum."
        ),
    }
    validate_event(event)
    line = json.dumps(event, sort_keys=True) + "\n"
    if args.dry_run:
        print(line)
        print("[dry-run] erratum validated; nothing written")
        return 0
    with OUTBOX.open("a") as fh:
        fh.write(line)
    print(f"wrote erratum to {OUTBOX.relative_to(REPO)}  id={event['event_id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
