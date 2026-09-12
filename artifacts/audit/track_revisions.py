#!/usr/bin/env python3
"""Track revision churn of gate-critical artifacts against the reviewed sha pins.

Appends one JSONL line per changed artifact with the old/new sha and whether the change
touches a file that has an open review. A review whose artifact sha no longer matches the
file on disk is STALE and must be re-pinned or re-run.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "artifacts" / "audit" / "checkpoints" / "revision_state.json"
LOG = ROOT / "artifacts" / "audit" / "checkpoints" / "revision_log.jsonl"
WATCH = [
    "research_map/formulation_taxonomy.yaml",
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "ledger/theorems.jsonl",
    "evaluation_rubric.yaml",
]
REVIEW_GLOB = "reviews/*review*.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "MISSING"


def pins() -> dict:
    out = {}
    for p in sorted((ROOT / "reviews").glob("*review*.json")):
        try:
            d = json.loads(p.read_text())
        except ValueError:
            continue
        tgt = d.get("target_id")
        s = d.get("artifact_sha256")
        if tgt and s:
            out.setdefault(tgt, []).append({"reviewer_file": p.name, "sha256": s})
    return out


def main() -> int:
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    current = {w: sha(ROOT / w) for w in WATCH}
    pinmap = pins()
    events = []
    for w, s in current.items():
        old = state.get(w)
        if old != s:
            events.append({"at": now, "artifact": w, "old": old, "new": s,
                           "review_pins": pinmap.get(_target_for(w), [])})
    STATE.write_text(json.dumps(current, indent=2) + "\n")
    if events:
        with open(LOG, "a") as f:
            for e in events:
                f.write(json.dumps(e, sort_keys=True) + "\n")
    stale = []
    for w, s in current.items():
        tgt = _target_for(w)
        for pin in pinmap.get(tgt, []):
            if pin["sha256"] != s:
                stale.append({"artifact": w, "review": pin["reviewer_file"],
                              "pinned": pin["sha256"][:12], "current": s[:12]})
    if stale:
        print("STALE REVIEWS:", json.dumps(stale, indent=1))
    else:
        print(f"revision watcher: {len(events)} change(s), no stale review pins")
    return 0


def _target_for(path: str) -> str:
    return {"research_map/formulation_taxonomy.yaml": "F0",
            "schemas/af_wcc_vacuum.yaml": "F1",
            "schemas/af_scc_c2_vacuum.yaml": "F2a",
            "schemas/af_scc_c0_vacuum.yaml": "F2b",
            "ledger/theorems.jsonl": "L0",
            "evaluation_rubric.yaml": "A0"}.get(path, path)


if __name__ == "__main__":
    raise SystemExit(main())
