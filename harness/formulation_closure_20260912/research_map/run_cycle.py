"""One Astra control cycle: lock -> ingest outbox -> apply events -> checkpoint.

Runs under an exclusive flock so a manual controller pass and the 15-minute loop can
never interleave a read-modify-write on research_map.json.

  python3 research_map/run_cycle.py --label auto-1
"""
from __future__ import annotations

import argparse
import fcntl
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research_map"))
import comms  # noqa: E402
import apply_events  # noqa: E402
import checkpoint  # noqa: E402
import accounting  # noqa: E402
import promote  # noqa: E402

LOCK = ROOT / "runtime" / "state" / "map.lock"


def main(label: str):
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            ing = comms.ingest(dry_run=False, verbose=True)
            applied = apply_events.main(dry_run=False)
            # measured accounting inside the same lock
            import fcntl as _f, json as _j
            mpath = ROOT / "research_map" / "research_map.json"
            _m = _j.loads(mpath.read_text())
            prom = promote.evaluate(_m)
            acct = accounting.refresh(_m)
            _tmp = mpath.with_suffix(".json.tmp"); _tmp.write_text(_j.dumps(_m, indent=2) + "\n"); _tmp.replace(mpath)
            rec = checkpoint.main(label)
            summary = {
                "label": label,
                "ingested": {k: ing[k] for k in ("accepted", "rejected", "duplicates", "files")},
                "applied": applied["applied"],
                "demoted": applied["demoted"],
                "checkpoint": rec["checkpoint_id"],
                "hard": rec["evidence_hard_failures"],
                "pending": rec["events_pending_application"],
                "elapsed_hours": acct["elapsed_hours"],
                "measured_artifacts": acct["measured_artifacts"],
                "promotion": prom,
            }
            print("CYCLE " + json.dumps(summary))
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="cycle")
    a = ap.parse_args()
    main(a.label)
