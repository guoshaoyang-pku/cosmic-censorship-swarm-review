#!/usr/bin/env python3
"""Astra freeze control: pin artifact revisions during review.

  python3 runtime/bin/astra_freeze.py add <path> <node_id> <reason>
  python3 runtime/bin/astra_freeze.py list
  python3 runtime/bin/astra_freeze.py check

A frozen artifact that changes on disk is a HARD audit failure: reviews cite hashes,
so silent revision drift invalidates them.
"""
from __future__ import annotations
import fcntl, hashlib, json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
MAP = ROOT / "research_map" / "research_map.json"
LOCK = ROOT / "runtime" / "state" / "map.lock"
CST = timezone(timedelta(hours=8))


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def with_lock(fn):
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            return fn()
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def add(path: str, node_id: str, reason: str):
    def _do():
        m = json.loads(MAP.read_text())
        p = ROOT / path
        if not p.is_file():
            print(f"REFUSE: {path} is not a file"); return 1
        h = sha256(p)
        fr = m.setdefault("frozen_artifacts", [])
        for f in fr:
            if f["path"] == path and f.get("active", True):
                f["active"] = False
                f["superseded_at"] = datetime.now(CST).isoformat(timespec="seconds")
        fr.append({"path": path, "node_id": node_id, "sha256": h,
                   "frozen_at": datetime.now(CST).isoformat(timespec="seconds"),
                   "reason": reason, "active": True})
        m["updated_at"] = datetime.now(CST).isoformat(timespec="seconds")
        m.setdefault("portfolio_events", []).append(
            {"time": m["updated_at"], "actor": "astra",
             "event": f"froze {path} at sha256:{h[:12]} for review ({node_id})"})
        tmp = MAP.with_suffix(".json.tmp"); tmp.write_text(json.dumps(m, indent=2) + "\n"); tmp.replace(MAP)
        print(f"frozen {path} sha256:{h[:12]} node={node_id}")
        return 0
    return with_lock(_do)


def check():
    def _do():
        m = json.loads(MAP.read_text())
        bad = []
        for f in m.get("frozen_artifacts", []):
            if not f.get("active", True):
                continue
            p = ROOT / f["path"]
            if not p.is_file():
                bad.append(f"{f['path']}: frozen but missing"); continue
            h = sha256(p)
            if h != f["sha256"]:
                bad.append(f"{f['path']}: frozen at {f['sha256'][:12]} but now {h[:12]}")
        print(json.dumps({"violations": bad}, indent=2))
        return 1 if bad else 0
    return with_lock(_do)


def lst():
    def _do():
        m = json.loads(MAP.read_text())
        for f in m.get("frozen_artifacts", []):
            print(("ACTIVE " if f.get("active", True) else "old    "),
                  f"{f['path']}  {f['sha256'][:12]}  {f['node_id']}  {f.get('reason','')[:60]}")
        return 0
    return with_lock(_do)


def supersede(path: str, reason: str):
    def _do():
        m = json.loads(MAP.read_text())
        hit = 0
        for f in m.get("frozen_artifacts", []):
            if f["path"] == path and f.get("active", True):
                f["active"] = False
                f["superseded_at"] = datetime.now(CST).isoformat(timespec="seconds")
                f["superseded_note"] = reason
                hit += 1
        m["updated_at"] = datetime.now(CST).isoformat(timespec="seconds")
        m.setdefault("portfolio_events", []).append(
            {"time": m["updated_at"], "actor": "astra",
             "event": f"superseded freeze on {path}: {reason}"})
        tmp = MAP.with_suffix(".json.tmp"); tmp.write_text(json.dumps(m, indent=2) + "\n"); tmp.replace(MAP)
        print(f"superseded {hit} freeze(s) on {path}")
        return 0
    return with_lock(_do)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "add":
        sys.exit(add(sys.argv[2], sys.argv[3], " ".join(sys.argv[4:]) or "review freeze"))
    if cmd == "supersede":
        sys.exit(supersede(sys.argv[2], " ".join(sys.argv[3:]) or "superseded by controller"))
    if cmd == "check":
        sys.exit(check())
    sys.exit(lst())
