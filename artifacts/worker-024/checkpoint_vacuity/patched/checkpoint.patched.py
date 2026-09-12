"""Astra checkpoint: ingest comms, validate map, audit evidence, account budgets, snapshot.

Writes (never mutates research_map.json):
  runtime/state/checkpoints/ckpt-<stamp>.json   full checkpoint record
  runtime/state/checkpoint_log.jsonl            one line per checkpoint
  runtime/state/current_checkpoint.json         latest record
  runtime/state/agent_hours.json                measured swarm process hours

PROPOSED fail-closed patch (worker-024, proposal only):
  - non-vacuity block: a checkpoint is DEFECTIVE (exit 1, REASON lines) when the
    event stream is absent/empty/corrupt, the map is INVALID, the class-separation
    corpus is empty, the registry scan is empty, canonical gates are missing or the
    numerics lock is absent;
  - never clobber a non-empty artifact_hashes.json with an empty scan;
  - --dry-run performs no writes (including ingest);
  - checkpoint ids carry microseconds so two runs in one second do not overwrite.

Usage: python3 research_map/checkpoint.py [--label auto] [--dry-run]
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
CANONICAL_GATES = ("G-F0", "G-FORM", "G-LIT", "G-NUM", "G-AUDIT")


def stamp() -> str:
    # microseconds: two runs in the same wall-clock second must not share a file name
    return datetime.now(CST).strftime("%Y%m%d-%H%M%S-%f")


def nonvacuity_reasons(rec: dict) -> list:
    """A record is a certificate only if the structures it certifies are present.

    Presence-driven checks cannot distinguish 'clean' from 'absent'; each reason
    here names a structure whose absence makes the record vacuous.
    """
    reasons = []
    ev = ROOT / "research_map" / "events.jsonl"
    if not ev.exists():
        reasons.append("MISSING_EVENT_STREAM")
    elif rec["events_total"] == 0:
        reasons.append("EMPTY_EVENT_STREAM")
    if rec["event_stream_errors"]:
        reasons.append("EVENT_STREAM_ERRORS")
    if rec["map_validator"] != "VALID":
        reasons.append("MAP_INVALID")
    csr = rec.get("classsep_regression") or {}
    if int(csr.get("corpus_size", 0) or 0) == 0:
        reasons.append("CLASSSEP_CORPUS_EMPTY")
    if int(rec.get("registry_scan_size", 0) or 0) == 0:
        reasons.append("REGISTRY_EMPTY")
    gates = rec.get("gates") or {}
    missing = [g for g in CANONICAL_GATES if g not in gates]
    if missing:
        reasons.append("GATES_MISSING:" + ",".join(missing))
    if not rec.get("numerics_lock"):
        reasons.append("NUMERICS_LOCK_ABSENT")
    return reasons


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


def main(label: str, dry_run: bool = False) -> dict:
    ing = comms.ingest(dry_run=dry_run, verbose=not dry_run)
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
    # never clobber a non-empty registry with an empty scan
    rec["registry_scan_size"] = len(ev.get("registry", {}))
    reg_path = ROOT / "runtime" / "state" / "artifact_hashes.json"
    prev = None
    if reg_path.exists():
        try:
            prev = json.loads(reg_path.read_text())
        except ValueError:
            prev = None
    if not ev.get("registry") and not ev["hashes"] and prev and (prev.get("registry") or prev.get("hashes")):
        rec["artifact_hashes"] = prev.get("hashes", {})
        rec["artifact_registry"] = prev.get("registry", {})
        rec["registry_source"] = "preserved-previous (fresh scan empty)"
    else:
        rec["registry_source"] = "fresh-scan"
    rec["dry_run"] = dry_run
    reasons = nonvacuity_reasons(rec)
    rec["nonvacuity"] = {"verdict": "PASS" if not reasons else "DEFECTIVE", "reasons": reasons}
    if not dry_run:
        CKDIR.mkdir(parents=True, exist_ok=True)
        path = CKDIR / f"{rec['checkpoint_id']}.json"
        path.write_text(json.dumps(rec, indent=2, sort_keys=True))
        with (ROOT / "runtime" / "state" / "checkpoint_log.jsonl").open("a") as f:
            f.write(json.dumps({k: rec[k] for k in
                                ("checkpoint_id", "created_at", "map_validator", "evidence_hard_failures",
                                 "comms", "events_pending_application", "gates", "numerics_lock",
                                 "nonvacuity")}) + "\n")
        (ROOT / "runtime" / "state" / "current_checkpoint.json").write_text(json.dumps(rec, indent=2, sort_keys=True))
        (ROOT / "runtime" / "state" / "agent_hours.json").write_text(json.dumps(rec["agents"], indent=2, sort_keys=True))
        (ROOT / "runtime" / "state" / "artifact_hashes.json").write_text(
            json.dumps({"hashes": rec["artifact_hashes"], "registry": rec["artifact_registry"]}, indent=2, sort_keys=True))
    print(json.dumps({k: rec[k] for k in ("checkpoint_id", "map_validator", "evidence_hard_failures",
                                          "classsep_regression", "nonvacuity",
                                          "comms", "events_pending_application", "gates", "numerics_lock")}, indent=2))
    for r in reasons:
        print(f"REASON {r}")
    return rec


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="auto-15min")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    _rec = main(a.label, a.dry_run)
    sys.exit(1 if _rec["nonvacuity"]["reasons"] else 0)
