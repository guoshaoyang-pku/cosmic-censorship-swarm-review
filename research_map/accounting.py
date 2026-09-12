"""Measured accounting for research_map.json.

Refreshes run hours, per-group measured artifacts, and controller ETA estimates from
what is on disk and what the checkpoint loop measured. Runs inside run_cycle's flock.

Measured fields are prefixed/annotated so they are never confused with claimed values.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CST = timezone(timedelta(hours=8))


def _count(p: Path, patterns=("*",)) -> int:
    if not p.exists():
        return 0
    n = 0
    for pat in patterns:
        n += sum(1 for x in p.rglob(pat) if x.is_file() and not x.name.startswith("._"))
    return n


def refresh(m: dict) -> dict:
    now = datetime.now(CST)
    run = m.setdefault("run", {})
    started = run.get("started_at")
    elapsed_h = None
    if started:
        try:
            elapsed_h = round((now - datetime.fromisoformat(started)).total_seconds() / 3600, 2)
        except ValueError:
            pass
    run["elapsed_hours_measured"] = elapsed_h

    ah = ROOT / "runtime" / "state" / "agent_hours.json"
    if ah.exists():
        try:
            d = json.loads(ah.read_text())
            run["live_agents_measured"] = d.get("live_agents")
            run["measured_agent_hours"] = d.get("measured_agent_hours")
            run["measured_at"] = d.get("measured_at")
        except ValueError:
            pass

    # per-group run-hour estimate: (workers + lead) x elapsed
    POOL = {"formulation": 6, "literature": 5, "numerics": 4, "audit": 5}
    measured_artifacts = {
        "formulation": _count(ROOT / "schemas") + (1 if (ROOT / "research_map/formulation_taxonomy.yaml").exists() else 0),
        "literature": _count(ROOT / "ledger"),
        "numerics": _count(ROOT / "numerics"),
        "audit": _count(ROOT / "reviews") + _count(ROOT / "evaluation") +
                 (1 if (ROOT / "evaluation_rubric.yaml").exists() else 0) + _count(ROOT / "artifacts/audit"),
    }
    ETA = {"formulation": (0.5, 1.5), "literature": (1.0, 3.0), "numerics": (3.0, 7.0), "audit": (0.5, 2.0)}
    for g in m.get("groups", []):
        gid = g["id"]
        if elapsed_h is not None:
            g["run_agent_hours_estimate"] = round((POOL.get(gid, 0) + 1) * elapsed_h, 2)
        if gid in measured_artifacts:
            g.setdefault("artifacts", {})
            g["artifacts"]["files_done_measured"] = measured_artifacts[gid]
            g["artifacts"]["count_basis"] = "measured on disk by controller accounting"
        lo, hi = ETA.get(gid, (g.get("eta_days_low"), g.get("eta_days_high")))
        g["eta_days_low"], g["eta_days_high"] = lo, hi
        g["eta_basis"] = "controller estimate after run-1 checkpoint; revision/review cycles in flight"

    m["updated_at"] = now.isoformat(timespec="seconds")
    return {"elapsed_hours": elapsed_h, "measured_artifacts": measured_artifacts}
