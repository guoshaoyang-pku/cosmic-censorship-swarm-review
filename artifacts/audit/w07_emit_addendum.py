#!/usr/bin/env python3
"""Lifecycle-07 post-report addendum: the live map moved again after the census.

Idempotent. Appends one blocker to comms/outbox/astra-lead-audit.jsonl and updates the
lifecycle-07 checkpoint's binding note. Writes no canonical artifact.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTBOX = ROOT / "comms/outbox/astra-lead-audit.jsonl"
CKPT = ROOT / "runtime/state/lead_audit_lifecycle_07_checkpoint.json"
SNAP = "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json"
NOW = datetime.now().astimezone().isoformat(timespec="seconds")
STAMP = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
EID = "audit-l07-b7-map-moved-post-census-20260912T010517"


def main() -> int:
    m = json.loads((ROOT / "research_map/research_map.json").read_text())
    snap = json.loads((ROOT / SNAP).read_text())
    n_now, n_snap = len(m.get("claims", [])), len(snap.get("claims", []))
    ev = {
        "event_id": EID, "event_type": "blocker", "node_id": "A1",
        "actor": "astra-lead-audit", "created_at": NOW,
        "description": f"Post-census movement: research_map/research_map.json grew "
                       f"{n_snap} -> {n_now} claims (+{n_now - n_snap}) between the frozen "
                       f"snapshot (f344ed2aaea5, taken 01:03:24) and this addendum, updated_at "
                       f"{m.get('updated_at')}. The r3 census binds ONLY the snapshot; no live "
                       f"count in reviews/CLASSSEP-calibration-adjudication.json may be quoted "
                       f"against the current map bytes. The detector itself did not move "
                       f"(a8c04fc31e4a unchanged), so the corpus-bound parts of decision (c) "
                       f"(27-fixture, assertion/mention, worker-049, worker-035) are unaffected.",
        "needed_to_unblock": "writers quiesce at a published pin; then re-run "
                             "artifacts/audit/classsep_r3_adjudication.py to refresh the live "
                             "census against the new bytes",
        "evidence_refs": [f"{SNAP}#f344ed2aaea5",
                          "research_map/research_map.json#" + __import__("hashlib").sha256(
                              (ROOT / "research_map/research_map.json").read_bytes()).hexdigest()[:12],
                          "reviews/CLASSSEP-calibration-adjudication.json"],
    }
    existing = set()
    if OUTBOX.is_file():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    existing.add(json.loads(line).get("event_id"))
                except ValueError:
                    pass
    if EID not in existing:
        with OUTBOX.open("a") as f:
            f.write(json.dumps(ev, sort_keys=True) + "\n")
        print("appended", EID)
    else:
        print("already present", EID)

    ck = json.loads(CKPT.read_text())
    ck["live_census_binding"]["post_census_map_sha256"] = ev["evidence_refs"][1]
    ck["live_census_binding"]["post_census_claims"] = n_now
    ck["live_census_binding"]["post_census_note"] = (
        f"map moved {n_snap} -> {n_now} claims AFTER the census; live counts bind the snapshot "
        f"only (see {EID})")
    ck["blockers"] = list(dict.fromkeys(ck["blockers"] + [EID]))
    ck["events_emitted"] = list(dict.fromkeys(ck["events_emitted"] + [EID]))
    ck["addendum_at"] = NOW
    CKPT.write_text(json.dumps(ck, indent=2) + "\n")
    print("checkpoint updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
