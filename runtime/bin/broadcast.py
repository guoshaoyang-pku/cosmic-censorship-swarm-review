#!/usr/bin/env python3
"""Astra broadcast: one controller notice to every live agent inbox."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "research_map"))
import comms  # noqa: E402

AGENTS = ["astra-lead-formulation", "astra-lead-literature", "astra-lead-numerics", "astra-lead-audit"] + \
         [f"deepseek-flash-{i:02d}" for i in range(1, 21)]

NOTICE = (
    "CONTROLLER NOTICE 2026-09-11T23:23+08:00. "
    "(1) Your assignment card is in comms/inbox/<agent>.jsonl, issued 23:19; read it before proposing more work. "
    "(2) Sole global state research_map.json now carries gates G-F0/G-FORM/G-LIT/G-NUM/G-AUDIT, numerics_lock=locked, "
    "30 assignments, canonical artifact paths, and measured artifact hashes. Re-read it; earlier audits that found "
    "'no gates/lock/class_id' are superseded. "
    "(3) F0/A0 evidence gap adjudicated: F0 taxonomy draft exists at research_map/formulation_taxonomy.yaml "
    "(worker-01, draft_unverified) and awaits 2 independent reviews; the A0 rubric draft exists only at "
    "artifacts/audit/evaluation_rubric.yaml, canonical path is evaluation_rubric.yaml. "
    "(4) Write artifacts to your assigned canonical path. A submission elsewhere is recorded as drift, never completion. "
    "(5) Authority: a worker event cannot set node status=done, validation_status=passed, or a gate verdict. "
    "Those are recorded as completion_claims/gate_proposals and will not move the map. "
    "(6) Every artifact event must carry path + sha256 + validation_status; evidence_refs must be path#sha256-prefix. "
    "(7) numerics_lock remains LOCKED: N0 flat-space only; do not create numerics/spherical_solver/. "
    "(8) The project rule stands: fluent text is never promoted to theorem."
)


def main():
    n = 0
    for agent in AGENTS:
        ev = {
            "event_id": f"astra-notice-2323-{agent}",
            "event_type": "status",
            "created_at": comms.now(),
            "actor": "astra",
            "node_id": "GLOBAL",
            "status": "active",
            "hours": 0,
            "summary": NOTICE,
            "evidence_refs": ["research_map/research_map.json", "comms/inbox/", "comms/PROTOCOL.md"],
            "next_falsifier": "An agent acts on stale map state (pre-23:22) or writes outside its assigned canonical path.",
        }
        comms.send(agent, ev)
        res = comms.append_event(ev)
        n += 1 if res.get("accepted") else 0
    print(f"broadcast: {n}/{len(AGENTS)} accepted")


if __name__ == "__main__":
    main()
