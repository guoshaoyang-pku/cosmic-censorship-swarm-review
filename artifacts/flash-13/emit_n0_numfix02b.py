#!/usr/bin/env python3
"""astra-numfix-02, part 2: register the controller-verified replication JSON (6542db93)
as an artifact event, completing the card's literal "emit an artifact event with the new
replication JSON sha256" requirement. Proposal-only; no gate verdict."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
FIXED = "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json"
REPRO = "numerics/results/flat_wave_replication.json"


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def main() -> int:
    ev = validate_event({
        "event_id": "f13-n0-numfix02-art-fixed-run",
        "event_type": "artifact", "created_at": NOW, "actor": "deepseek-flash-13",
        "node_id": "N0", "class_id": "AF-WCC-SCALAR-SPH",
        "artifact_type": "numerical_evidence", "path": FIXED, "sha256": sha(FIXED),
        "validation_status": "unverified",
        "note": ("controller-verified re-run of the fixed replication (script 8ade1cdc); the "
                 "worker-owned reproduction of the same run is " + REPRO + " sha256 " + sha(REPRO)),
        "evidence_refs": [f"{REPRO}#sha256:{sha(REPRO)[:16]}",
                          f"numerics/tests/flat_wave_replication.py#sha256:{sha('numerics/tests/flat_wave_replication.py')[:16]}"],
    })
    out = ROOT / "comms" / "outbox" / "deepseek-flash-13.jsonl"
    with out.open("a") as f:
        f.write(json.dumps(ev, sort_keys=True) + "\n")
    print(json.dumps({"event": ev["event_id"], "path": FIXED, "sha256": ev["sha256"],
                      "outbox_sha256": hashlib.sha256(out.read_bytes()).hexdigest()}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
