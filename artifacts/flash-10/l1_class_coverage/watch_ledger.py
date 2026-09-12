#!/usr/bin/env python3
"""Keep ledger/class_coverage.csv in sync with the live L0 ledger (worker flash-10).

Polls ledger/theorems.jsonl + ledger/citation_audit.csv. When their combined hash is unchanged
across two consecutive polls (i.e. writers have quiesced), it re-runs the deterministic builder and
validator, appends a checkpoint line, and re-emits the outbox events if the CSV content changed.

Safe to interrupt: the builder writes atomically, and this script never edits the ledger.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LOG = ROOT / "runtime" / "logs" / "w10-ledger-rebuild.log"
CKPT = ROOT / "runtime" / "state" / "checkpoint_log.jsonl"
CSV = ROOT / "ledger" / "class_coverage.csv"
SUMMARY = HERE / "coverage_summary.json"
CST = timezone(timedelta(hours=8))
MAX_SECONDS = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
POLL = 40


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(f"{now()} {msg}\n")


def digest() -> str:
    h = hashlib.sha256()
    for p in [ROOT / "ledger" / "theorems.jsonl", ROOT / "ledger" / "citation_audit.csv"]:
        h.update(p.read_bytes() if p.exists() else b"")
    return h.hexdigest()[:16]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(cmd: list[str]) -> tuple[bool, str]:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def checkpoint(csv_hash: str, totals: dict, inputs: dict, event: str) -> None:
    line = json.dumps({
        "checkpoint_id": f"w10-watch-{datetime.now(CST).strftime('%H%M%S')}",
        "at": now(), "worker": "deepseek-flash-10", "node_id": "L1", "gate": "G-LIT",
        "status": "auto_refresh", "artifacts": {"ledger/class_coverage.csv": csv_hash},
        "coverage_totals": totals, "inputs": inputs, "claims_completion": False,
        "next_falsifier": "Re-run on the next stable ledger snapshot; a covered-cell change falsifies the headline finding unless re-derived.",
        "outbox_event": event,
    }) + "\n"
    with CKPT.open("a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(line)
        fcntl.flock(f, fcntl.LOCK_UN)


def main() -> int:
    log(f"watcher start max_seconds={MAX_SECONDS} poll={POLL}s")
    start = time.time()
    last_seen, pending_since, pending_hash = None, None, None
    last_csv_hash, last_emit = None, 0.0
    while time.time() - start < MAX_SECONDS:
        try:
            h = digest()
        except Exception as e:  # noqa: BLE001 - ledger may be mid-write
            log(f"digest error (writer active?): {e}")
            time.sleep(POLL)
            continue
        if h != last_seen:
            last_seen, pending_hash, pending_since = h, h, time.time()
        elif pending_hash == h and pending_since and (time.time() - pending_since) >= POLL:
            log(f"stable snapshot {h}, rebuilding")
            ok, out = run(["python3", "artifacts/flash-10/l1_class_coverage/build_ledger_class_coverage.py"])
            if not ok:
                log(f"BUILD FAILED: {out[-500:]}")
            else:
                vok, vout = run(["python3", "artifacts/flash-10/l1_class_coverage/validate_class_coverage.py"])
                csv_hash = sha(CSV) if CSV.exists() else "missing"
                log(f"rebuilt csv={csv_hash[:16]} validate={'ok' if vok else 'FAILED'}")
                s = json.loads(SUMMARY.read_text())
                event = "none"
                if csv_hash != last_csv_hash and (time.time() - last_emit > 900):
                    eok, eout = run(["python3", "artifacts/flash-10/l1_class_coverage/emit_outbox_events.py"])
                    event = "emitted" if eok else f"emit_failed: {eout[-200:]}"
                    last_emit = time.time()
                checkpoint(csv_hash, s["coverage_totals"], s["inputs"], event)
                last_csv_hash = csv_hash
            pending_hash, pending_since = None, None
        time.sleep(POLL)
    log("watcher stop (window elapsed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
