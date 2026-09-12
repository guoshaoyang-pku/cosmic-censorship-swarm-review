"""Comms bus for the cosmic-censorship swarm.

Contract (see comms/PROTOCOL.md):
  upward   : comms/outbox/<agent>.jsonl   (or any *.jsonl / *.json / *.md)
  downward : comms/inbox/<agent>.jsonl    (written by Astra only)

This module ingests outbox traffic, validates it against schemas.validate_event,
deduplicates by event_id, appends accepted events to research_map/events.jsonl and
records rejects (with reasons) in comms/rejected.jsonl. It never mutates
research_map.json; Astra applies accepted events to the sole global state.

Usage:
  python3 research_map/comms.py ingest            # ingest everything new
  python3 research_map/comms.py ingest --dry-run
  python3 research_map/comms.py pending           # accepted-but-unapplied events
  python3 research_map/comms.py send <agent> <json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schemas import validate_event, SchemaError  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUTBOX = ROOT / "comms" / "outbox"
INBOX = ROOT / "comms" / "inbox"
EVENTS = ROOT / "research_map" / "events.jsonl"
REJECTS = ROOT / "comms" / "rejected.jsonl"
SEEN = ROOT / "runtime" / "state" / "ingested_ids.json"
CST = timezone(timedelta(hours=8))

# W024 proposed: sources that may carry authority, and explicit non-canonical aliases.
KNOWN_AGENT = re.compile(r"^(astra|astra-lead-(formulation|literature|numerics|audit)|"
                         r"deepseek-flash-\d{1,3}|worker-\d{1,3})$")
SOURCE_ACTOR_ALIASES = {"lead-literature.events": "astra-lead-literature"}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def _json_objects(text: str):
    """Extract JSON objects from jsonl, a JSON array, or fenced blocks in markdown."""
    text = text.strip()
    if not text:
        return
    # whole-file JSON
    try:
        doc = json.loads(text)
        if isinstance(doc, dict):
            yield doc
            return
        if isinstance(doc, list):
            for d in doc:
                if isinstance(d, dict):
                    yield d
            return
    except ValueError:
        pass
    # fenced blocks
    for block in re.findall(r"```(?:json)?\s*(.*?)```", text, re.S):
        try:
            doc = json.loads(block.strip())
        except ValueError:
            continue
        if isinstance(doc, dict):
            yield doc
        elif isinstance(doc, list):
            for d in doc:
                if isinstance(d, dict):
                    yield d
    # line-delimited objects (also catches one-object-per-line inside fenced blocks)
    for line in text.splitlines():
        line = line.strip().rstrip(",")
        if not (line.startswith("{") and line.endswith("}")):
            continue
        try:
            doc = json.loads(line)
        except ValueError:
            continue
        if isinstance(doc, dict):
            yield doc


def _load_seen() -> set:
    if SEEN.exists():
        try:
            return set(json.loads(SEEN.read_text()))
        except ValueError:
            return set()
    return set()


def _save_seen(ids: set):
    SEEN.parent.mkdir(parents=True, exist_ok=True)
    SEEN.write_text(json.dumps(sorted(ids), indent=0))


def _stable_id(raw: str) -> str:
    return "auto-" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def outbox_files():
    if not OUTBOX.exists():
        return []
    return sorted(p for p in OUTBOX.rglob("*") if p.is_file() and not p.name.startswith("._"))


def _first(doc, *keys, default=None):
    for k in keys:
        if k in doc and doc[k] is not None:
            return doc[k]
    return default


def normalize_event(doc: dict, source: str) -> dict:
    """Map common worker key spellings onto the canonical event schema.

    Only *non-semantic* fields are defaulted (hours=0, evidence_refs=[], ...).
    Semantic cores (claim statement/conclusion, artifact path, gate verdict) are
    never invented; when absent the event is rejected. Records provenance in
    `_normalized` so the controller can see what was filled and from where.
    """
    t = doc.get("event_type")
    filled: dict[str, str] = {}
    out = dict(doc)

    def take(target, *keys, default=_first):
        if target in out and out[target] is not None:
            return
        v = _first(out, *keys)
        if v is None:
            return
        out[target] = v
        filled[target] = next(k for k in keys if k in out and out[k] is v)

    def default(target, value, why="defaulted"):
        if target not in out or out[target] is None:
            out[target] = value
            filled[target] = why

    take("class_id", "class_ids", "class")
    if isinstance(out.get("class_id"), list):
        out["class_ids"] = out["class_id"]
        out["class_id"] = out["class_id"][0] if out["class_id"] else ""
    take("node_id", "node", "node_ids", "target_node")
    if isinstance(out.get("node_id"), list):
        out["node_id"] = out["node_id"][0] if out["node_id"] else ""
    take("group_id", "group")
    take("evidence_refs", "evidence", "refs", "evidence_paths")
    take("hours", "hours_spent", "agent_hours", "spent_agent_hours")
    take("actor", "_source_actor")

    if t == "status":
        if not out.get("node_id"):
            out["node_id"] = "GLOBAL"
            filled["node_id"] = "defaulted-global (availability/proposal note)"
        take("status", "node_status", "state")
        if out.get("status") not in {"queued", "active", "blocked", "done", "rejected", "killed"}:
            if str(out.get("status", "")).lower() in {"blocked", "failed", "error", "stalled"}:
                out["status"] = "blocked"
            elif str(out.get("status", "")).lower() in {"done", "complete", "completed", "finished"}:
                out["status"] = "done"
            else:
                out["status"] = "active"
                filled["status"] = "defaulted-active"
        take("summary", "note", "description", "message")
        default("summary", "no summary provided", "defaulted-empty")
        default("hours", 0.0)
        default("evidence_refs", [])
        take("next_falsifier", "falsifier", "next_test")
        default("next_falsifier", "unspecified")
    elif t == "blocker":
        take("description", "blocker", "issue", "summary", "note")
        if not out.get("description") and isinstance(out.get("blockers"), list):
            parts = []
            for b in out["blockers"]:
                if isinstance(b, dict):
                    parts.append(str(b.get("detail") or b.get("description") or b.get("blocker") or b))
                    if not out.get("needed_to_unblock") and (b.get("needed_to_unblock") or b.get("resolution")):
                        out["needed_to_unblock"] = b.get("needed_to_unblock") or b.get("resolution")
                else:
                    parts.append(str(b))
            if parts:
                out["description"] = "; ".join(parts)
                filled["description"] = "joined from blockers[]"
        take("needed_to_unblock", "unblock", "needed", "resolution", "required")
        default("needed_to_unblock", "unspecified")
        default("evidence_refs", [])
        default("node_id", "")
    elif t == "artifact":
        take("path", "artifact_path", "file", "artifact")
        take("artifact_type", "kind", "type")
        default("artifact_type", "file")
        take("sha256", "hash", "checksum", "sha")
        take("validation_status", "validation", "verdict")
        if out.get("validation_status") not in {"unverified", "passed", "failed", "retracted"}:
            out["validation_status"] = "unverified"
            filled["validation_status"] = "defaulted-unverified"
        if out.get("sha256") is None:
            p = ROOT / str(out.get("path", ""))
            if p.is_file():
                h = hashlib.sha256()
                with p.open("rb") as f:
                    for chunk in iter(lambda: f.read(1 << 20), b""):
                        h.update(chunk)
                out["sha256"] = h.hexdigest()
                filled["sha256"] = "computed-on-disk"
            else:
                out["sha256"] = "unverified"
                filled["sha256"] = "defaulted-unverified"
    elif t == "claim":
        take("statement", "claim", "text", "summary")
        take("conclusion_type", "claim_type", "conclusion")
        default("conclusion_type", "open_problem", "defaulted-conservative")
        take("assumptions", "hypotheses")
        default("assumptions", [])
        take("falsifier", "next_falsifier")
        default("falsifier", "unspecified")
        default("evidence_refs", [])
    elif t == "review":
        take("target_id", "target", "node_id", "artifact")
        take("reviewer", "actor", "reviewer_id")
        take("verdict", "decision", "result")
        score = _first(out, "score", "rating")
        if score is None:
            out["score"] = 0
            filled["score"] = "missing-score-0"
        else:
            try:
                out["score"] = float(score)
            except (TypeError, ValueError):
                out["score"] = 0
        take("hard_failures", "failures")
        default("hard_failures", [])
        take("findings", "notes", "summary")
        default("findings", "no findings text")
    elif t == "resource_request":
        take("requested_agents", "agents", "n_agents")
        default("requested_agents", 0)
        take("requested_agent_hours", "agent_hours", "hours")
        default("requested_agent_hours", 0)
        take("justification", "reason", "summary", "note")
        default("justification", "unspecified")
        take("expected_information_gain", "eig", "information_gain")
        default("expected_information_gain", "unspecified")
        take("stop_rule", "stopping_rule")
        default("stop_rule", "unspecified")
    elif t == "direction_update":
        take("old_direction", "old")
        default("old_direction", "unspecified")
        take("new_direction", "new", "direction")
        default("new_direction", "unspecified")
        take("reason", "justification", "summary")
        default("reason", "unspecified")
        default("evidence_refs", [])
        default("budget_delta_agent_hours", 0)
    elif t == "gate":
        take("gate_id", "gate")
        take("scope", "node_id", "group_id")
        default("scope", "unspecified")
        take("verdict", "result", "status")
        take("criteria", "acceptance", "rule")
        default("criteria", "unspecified")
        default("evidence_refs", [])
    elif t == "budget":
        default("delta_agent_hours", 0)
        take("reason", "justification", "summary")
        default("reason", "unspecified")
    elif t == "priority_change":
        take("old_priority", "old")
        take("new_priority", "new")
        take("reason", "justification")
        default("reason", "unspecified")
    elif t in {"kill", "revive"}:
        take("target_id", "node_id", "target")
        take("reason", "justification")
        default("reason", "unspecified")

    if filled:
        out["_normalized"] = filled
        out["_source_file"] = str(source)
    return out


def ingest(dry_run: bool = False, verbose: bool = True) -> dict:
    seen = _load_seen()
    accepted, rejected, duplicates = [], [], []
    for path in outbox_files():
        try:
            text = path.read_text(errors="replace")
        except OSError as e:
            rejected.append({"source": str(path), "reason": f"unreadable: {e}"})
            continue
        for doc in _json_objects(text):
            if not isinstance(doc, dict):
                continue
            raw = json.dumps(doc, sort_keys=True)
            eid = doc.get("event_id") or _stable_id(raw)
            doc.setdefault("event_id", eid)
            if eid in seen:
                duplicates.append(eid)
                continue
            doc.setdefault("created_at", now())
            doc.setdefault("actor", path.stem)
            doc["_received_at"] = now()  # controller arrival time; agent created_at may be unreliable
            doc = normalize_event(doc, path.relative_to(ROOT))
            try:
                validate_event(doc)
            except SchemaError as e:
                seen.add(eid)  # one reject per unique message; avoids re-rejecting every cycle
                rejected.append({"source": str(path.relative_to(ROOT)), "event_id": eid,
                                 "event_type": doc.get("event_type"), "reason": str(e),
                                 "raw": raw[:600], "rejected_at": now()})
                continue
            # ---- W024 proposed authority binding (proposal only) --------------
            # The declared actor must be backed by the source outbox file (stem or a
            # controller-registered alias).  A mismatch is preserved for audit as
            # actor_claimed and the event is downgraded to an unattributed actor, so
            # apply_events' actor-string authority test can never be forged.
            stem = path.stem
            src_role = SOURCE_ACTOR_ALIASES.get(stem, stem)
            if not KNOWN_AGENT.match(src_role):
                src_role = "unattributed:" + stem
            if doc.get("actor") != src_role:
                doc["actor_claimed"] = doc.get("actor")
                doc["actor"] = "unattributed:" + stem
            doc["_source_file"] = str(path.relative_to(ROOT))
            # -------------------------------------------------------------------
            accepted.append(doc)
            seen.add(eid)
    if not dry_run:
        EVENTS.parent.mkdir(parents=True, exist_ok=True)
        with EVENTS.open("a") as f:
            for e in accepted:
                f.write(json.dumps(e, sort_keys=True) + "\n")
        if rejected or duplicates:
            REJECTS.parent.mkdir(parents=True, exist_ok=True)
            with REJECTS.open("a") as f:
                for r in rejected:
                    f.write(json.dumps(r, sort_keys=True) + "\n")
        _save_seen(seen)
    result = {"accepted": len(accepted), "rejected": len(rejected), "duplicates": len(duplicates),
              "files": len(outbox_files()), "accepted_events": accepted, "dry_run": dry_run}
    if verbose:
        print(json.dumps({k: v for k, v in result.items() if k != "accepted_events"}, indent=2))
        for e in accepted:
            print(f"  + {e['event_type']:<16} {e.get('node_id') or e.get('group_id') or e.get('gate_id') or e.get('target_id') or '-'}  {e['event_id']}")
        for r in rejected:
            print(f"  ! REJECT {r['source']} {r.get('event_type')}: {r['reason']}")
    return result


def append_event(event: dict) -> dict:
    """Astra/leads may append a single pre-validated event."""
    validate_event(event)
    seen = _load_seen()
    if event["event_id"] in seen:
        return {"accepted": False, "reason": "duplicate"}
    with EVENTS.open("a") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")
    seen.add(event["event_id"])
    _save_seen(seen)
    return {"accepted": True, "event_id": event["event_id"]}


def load_events() -> list:
    if not EVENTS.exists():
        return []
    out = []
    for line in EVENTS.read_text().splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def send(agent: str, message: dict):
    """Downward channel: Astra (or a lead) writes to an agent inbox."""
    INBOX.mkdir(parents=True, exist_ok=True)
    path = INBOX / f"{agent}.jsonl"
    with path.open("a") as f:
        f.write(json.dumps(message, sort_keys=True) + "\n")
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("ingest")
    p.add_argument("--dry-run", action="store_true")
    sub.add_parser("pending")
    s = sub.add_parser("send")
    s.add_argument("agent")
    s.add_argument("json")
    a = ap.parse_args()
    if a.cmd == "ingest":
        ingest(dry_run=a.dry_run)
    elif a.cmd == "pending":
        evs = load_events()
        print(json.dumps([e for e in evs if not e.get("applied_to_map")], indent=2))
    elif a.cmd == "send":
        print(send(a.agent, json.loads(a.json)))
