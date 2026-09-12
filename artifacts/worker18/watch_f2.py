#!/usr/bin/env python3
"""Watch F2 artifacts and worker-18 inbox for changes; exit on first change or timeout.

Writes one JSON line per detected change (or the timeout event) to
artifacts/worker18/watch_log.jsonl and exits 0. Used by worker 18 so the review pins can be
re-validated promptly instead of busy-polling.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CST = timezone(timedelta(hours=8))
WATCH = [
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml.sha256",
    "schemas/af_scc_regularities.yaml",
    "comms/inbox/deepseek-flash-18.jsonl",
    "research_map/research_map.json",
    "runtime/state/current_checkpoint.json",
    "schemas/af_scc_regularities.yaml",
]


def state():
    out = {}
    for rel in WATCH:
        p = ROOT / rel
        if p.exists():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        else:
            out[rel] = None
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=45)
    ap.add_argument("--max-minutes", type=int, default=40)
    a = ap.parse_args()
    log = ROOT / "artifacts/worker18/watch_log.jsonl"
    start = time.time()
    base = state()
    while True:
        time.sleep(a.interval)
        cur = state()
        changed = {k: (base[k], cur[k]) for k in base if base[k] != cur[k]}
        event = None
        if changed:
            event = {"event": "change", "at": datetime.now(CST).isoformat(timespec="seconds"),
                     "changes": changed, "before": base, "after": cur}
        elif (time.time() - start) / 60 >= a.max_minutes:
            event = {"event": "timeout", "at": datetime.now(CST).isoformat(timespec="seconds"),
                     "minutes": a.max_minutes, "state": cur}
        if event:
            with log.open("a") as f:
                f.write(json.dumps(event, sort_keys=True) + "\n")
            print(json.dumps(event, indent=1))
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
