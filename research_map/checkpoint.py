"""Astra checkpoint: ingest comms, validate map, audit evidence, account budgets, snapshot.

Writes (never mutates research_map.json):
  runtime/state/checkpoints/ckpt-<stamp>.json   full checkpoint record
  runtime/state/checkpoint_log.jsonl            one line per checkpoint
  runtime/state/current_checkpoint.json         latest record
  runtime/state/agent_hours.json                measured swarm process hours

Usage: python3 research_map/checkpoint.py [--label auto]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comms  # noqa: E402
from validate_map import validate_map, load, validate_events  # noqa: E402
import audit_evidence  # noqa: E402
import class_separation  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CST = timezone(timedelta(hours=8))
CKDIR = ROOT / "runtime" / "state" / "checkpoints"


def stamp() -> str:
    return datetime.now(CST).strftime("%Y%m%d-%H%M%S")


def measure_agents() -> dict:
    """Measure live swarm processes and their elapsed hours (agent-hours spent)."""
    out = {}
    try:
        ps = subprocess.run(["ps", "-eo", "pid,etime,args"], capture_output=True, text=True, timeout=20).stdout
    except Exception as e:  # pragma: no cover
        return {"error": str(e)}
    agents = {}
    for line in ps.splitlines()[1:]:
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        pid, etime, args = parts
        if "dsh_fixed.sh" not in args and "/dsh " not in args:
            continue
        m = re.search(r"\b(astra-(?:controller|lead-[\w-]+)|deepseek-flash-\d+)\b", args)
        name = m.group(0) if m else None
        if not name:
            continue
        # elapsed seconds from etime: [[dd-]hh:]mm:ss
        days = 0
        t = etime
        if "-" in t:
            d, t = t.split("-", 1)
            days = int(d)
        bits = [int(x) for x in t.split(":")]
        while len(bits) < 3:
            bits.insert(0, 0)
        secs = days * 86400 + bits[0] * 3600 + bits[1] * 60 + bits[2]
        prev = agents.get(name, 0)
        agents[name] = max(prev, secs)
    live = {k: v for k, v in agents.items() if v > 0}
    out["agents"] = {k: round(v / 3600, 3) for k, v in sorted(live.items())}
    out["live_agents"] = len(live)
    out["measured_agent_hours"] = round(sum(live.values()) / 3600, 3)
    out["measured_at"] = datetime.now(CST).isoformat(timespec="seconds")
    return out


def main(label: str) -> dict:
    ing = comms.ingest(dry_run=False, verbose=True)
    map_path = ROOT / "research_map" / "research_map.json"
    m = load(map_path)
    map_errs = validate_map(m)
    events = comms.load_events()
    applied_ids = set(m.get("applied_event_ids", []))
    pending = [e for e in events if e.get("event_id") not in applied_ids]
    ev_errs = validate_events([str(comms.EVENTS)]) if comms.EVENTS.exists() else []
    ev = audit_evidence.audit(map_path)
    csr = class_separation.regression()

    groups = {}
    for g in m.get("groups", []):
        groups[g["id"]] = {
            "status": g.get("status"),
            "spent_agent_hours": g.get("spent_agent_hours", 0),
            "budget_agent_hours": g.get("budget_agent_hours", 0),
            "active_agents": g.get("active_agents", 0),
            "nodes": {n["id"]: n.get("status") for n in g.get("nodes", [])},
        }
    gates = {g["gate_id"]: g.get("verdict") for g in m.get("gates", [])}
    rec = {
        "checkpoint_id": f"ckpt-{stamp()}",
        "label": label,
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "map_path": str(map_path.relative_to(ROOT)),
        "map_updated_at": m.get("updated_at"),
        "map_validator": "VALID" if not map_errs else "INVALID",
        "map_errors": map_errs,
        "event_stream_errors": ev_errs,
        "evidence_hard_failures": ev["hard"],
        "evidence_soft_findings": ev["soft"],
        "classsep_regression": csr,
        "artifact_hashes": ev["hashes"],
        "artifact_registry": ev.get("registry", {}),
        "gates": gates,
        "numerics_lock": m.get("numerics_lock", {}),
        "groups": groups,
        "comms": {"outbox_files_seen": ing["files"], "accepted": ing["accepted"],
                  "rejected": ing["rejected"], "duplicates": ing["duplicates"]},
        "events_total": len(events),
        "events_pending_application": len(pending),
        "pending_event_ids": [e["event_id"] for e in pending],
        "agents": measure_agents(),
        "spent_agent_hours_map": sum(g.get("spent_agent_hours", 0) for g in m.get("groups", [])),
        "budget_agent_hours_map": sum(g.get("budget_agent_hours", 0) for g in m.get("groups", [])),
    }
    CKDIR.mkdir(parents=True, exist_ok=True)
    path = CKDIR / f"{rec['checkpoint_id']}.json"
    path.write_text(json.dumps(rec, indent=2, sort_keys=True))
    with (ROOT / "runtime" / "state" / "checkpoint_log.jsonl").open("a") as f:
        f.write(json.dumps({k: rec[k] for k in
                            ("checkpoint_id", "created_at", "map_validator", "evidence_hard_failures",
                             "comms", "events_pending_application", "gates", "numerics_lock")}) + "\n")
    (ROOT / "runtime" / "state" / "current_checkpoint.json").write_text(json.dumps(rec, indent=2, sort_keys=True))
    (ROOT / "runtime" / "state" / "agent_hours.json").write_text(json.dumps(rec["agents"], indent=2, sort_keys=True))
    (ROOT / "runtime" / "state" / "artifact_hashes.json").write_text(
        json.dumps({"hashes": ev["hashes"], "registry": ev.get("registry", {})}, indent=2, sort_keys=True))
    print(json.dumps({k: rec[k] for k in ("checkpoint_id", "map_validator", "evidence_hard_failures",
                                          "classsep_regression",
                                          "comms", "events_pending_application", "gates", "numerics_lock")}, indent=2))
    return rec


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="auto-15min")
    a = ap.parse_args()
    main(a.label)
