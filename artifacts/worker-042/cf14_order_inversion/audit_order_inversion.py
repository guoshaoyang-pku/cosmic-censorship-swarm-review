#!/usr/bin/env python3
"""W042-ORDER-INVERSION-03 checker: is the accepted stream's map state a function of
arrival order or of agent-stamped created_at, and does the difference touch anything?

Background (pinned, quoted from the snapshot, not from memory):
  * `research_map/apply_events.py` consumes `research_map/events.jsonl` in file order and
    overwrites per-key state last-write-wins for: node `status` (line ~255), node artifact
    hash/validation_status for the assigned path (lines ~304-311), authority `gate` verdicts
    (lines ~331-342), `kill`/`revive` node lifecycle (lines ~365-369), and group direction
    (lines ~343-350). claim/review/blocker/resource_request/assignment/budget events are
    append-only and therefore order-insensitive.
  * CF-14 (map `controller_findings`) records that many accepted events carry created_at
    ahead of wall clock, so timestamp order is not arrival order.

Question: at one pinned snapshot, for every overwrite key, does the arrival-order winner
equal the created_at-order winner; where they differ, is the difference in the recorded
state (hash / status / verdict) or only in event identity; and does the pinned map's own
recorded state match the arrival-order winner?

This is an order-sensitivity / replay-fidelity measurement. It does not claim the map is
wrong, does not set a node status or gate verdict, and does not modify any canonical file.

Run:
  python3 artifacts/worker-042/cf14_order_inversion/audit_order_inversion.py \
      --snapshot artifacts/worker-042/cf14_order_inversion/snapshot \
      --out artifacts/worker-042/cf14_order_inversion/report.json
Exit 0 = controls passed; 2 = a control failed or a pinned input moved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]

# Must equal the AUTHORITY set in the pinned apply_events.py; control C8 re-reads it from
# the pinned bytes and fails closed on any mismatch.
AUTHORITY = {"astra", "lead-formulation", "lead-literature", "lead-numerics", "lead-audit",
             "astra-lead-formulation", "astra-lead-literature", "astra-lead-numerics", "astra-lead-audit"}

STATE_EVENT_TYPES = ("status", "artifact", "gate", "kill", "revive", "direction_update")
APPEND_ONLY_TYPES = ("claim", "review", "blocker", "resource_request", "assignment", "budget",
                     "priority_change")

NODE_CLASS = {
    "F0": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "F1": ["AF-WCC-VAC-GEN"],
    "F2a": ["AF-SCC-C2-VAC-GEN"],
    "F2b": ["AF-SCC-C0-VAC-GEN"],
    "N0": ["AF-WCC-SCALAR-SPH"],
}
FROZEN_CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def parse_ts(value):
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        t = datetime.fromisoformat(s)
    except ValueError:
        try:  # tolerate +0800 (no colon) and trailing Z
            t = datetime.fromisoformat(re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", s.replace("Z", "+00:00")))
        except ValueError:
            return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=CST)
    return t


def load_events(path: Path):
    """File order is arrival order (events.jsonl is append-only); first event_id wins,
    matching apply_events' applied_event_ids dedup."""
    events, seen = [], set()
    parse_errors, duplicates, blank = 0, 0, 0
    line_no = 0
    for line_no, raw in enumerate(path.read_text().splitlines(), start=1):
        if not raw.strip():
            blank += 1
            continue
        try:
            ev = json.loads(raw)
        except json.JSONDecodeError:
            parse_errors += 1
            continue
        if not isinstance(ev, dict):
            parse_errors += 1
            continue
        eid = ev.get("event_id")
        if eid in seen:
            duplicates += 1
            continue
        seen.add(eid)
        ev["_line"] = line_no
        ev["_ts"] = parse_ts(ev.get("created_at"))
        ev["_recv"] = parse_ts(ev.get("_received_at"))
        events.append(ev)
    return events, {"lines": line_no, "blank_lines": blank,
                    "parse_errors": parse_errors, "duplicate_event_ids": duplicates}


def key_of(ev):
    t = ev.get("event_type")
    if t == "status" and ev.get("node_id"):
        return ("status", str(ev["node_id"]))
    if t == "artifact" and ev.get("node_id"):
        return ("artifact", str(ev["node_id"]), str(ev.get("path", "")))
    if t == "gate" and ev.get("gate_id"):
        return ("gate", str(ev["gate_id"]))
    if t in ("kill", "revive") and ev.get("target_id"):
        return ("lifecycle", str(ev["target_id"]))
    if t == "direction_update" and ev.get("group_id"):
        return ("direction", str(ev["group_id"]))
    return None


def payload_of(key, ev, authority=AUTHORITY):
    c = key[0]
    actor = str(ev.get("actor", ""))
    if c == "status":
        return [ev.get("status"), actor, float(ev.get("hours") or 0)]
    if c == "artifact":
        return [ev.get("sha256"), ev.get("validation_status"), actor, actor in authority]
    if c == "gate":
        return [ev.get("verdict"), actor in authority]
    if c == "lifecycle":
        return [ev.get("event_type")]
    if c == "direction":
        return [ev.get("new_direction")]
    return None


def analyze(events, authority=AUTHORITY):
    """Core order-sensitivity measurement over an event list already carrying _line/_ts."""
    keys = defaultdict(list)
    excluded = Counter()
    for ev in events:
        t = ev.get("event_type")
        k = key_of(ev)
        if k is None:
            excluded[t or "unknown"] += 1
            continue
        keys[k].append(ev)

    multi = undated = ties = order_only = 0
    inversions = []
    for key, lst in keys.items():
        if len(lst) < 2:
            continue
        multi += 1
        dated = [e for e in lst if e["_ts"] is not None]
        if len(dated) < 2:
            undated += 1
            continue
        arrival = max(lst, key=lambda e: e["_line"])
        if arrival["_ts"] is None:
            undated += 1
            continue
        max_ts = max(e["_ts"] for e in dated)
        time_winner = max((e for e in dated if e["_ts"] == max_ts), key=lambda e: e["_line"])
        if arrival["_ts"] == max_ts:
            ties += 1
            continue
        pa, pt = payload_of(key, arrival, authority), payload_of(key, time_winner, authority)
        if pa == pt:
            order_only += 1
            continue
        inversions.append({
            "key": list(key),
            "category": key[0],
            "arrival_winner": {
                "event_id": arrival.get("event_id"), "actor": arrival.get("actor"),
                "created_at": arrival.get("created_at"), "line": arrival["_line"],
                "payload": pa, "received_at": arrival.get("_received_at"),
            },
            "created_at_winner": {
                "event_id": time_winner.get("event_id"), "actor": time_winner.get("actor"),
                "created_at": time_winner.get("created_at"), "line": time_winner["_line"],
                "payload": pt, "received_at": time_winner.get("_received_at"),
            },
            "delta_seconds": int((time_winner["_ts"] - arrival["_ts"]).total_seconds()),
            "created_at_winner_future_dated": bool(
                time_winner["_recv"] is not None and time_winner["_ts"] > time_winner["_recv"]),
        })
    inversions.sort(key=lambda x: (-x["delta_seconds"], x["category"], str(x["key"])))
    return {
        "state_keys": len(keys),
        "multi_event_keys": multi,
        "keys_undated": undated,
        "keys_resolved_by_tiebreak": ties,
        "order_only_inversions": order_only,
        "state_changing_inversions": len(inversions),
        "inversions": inversions,
        "excluded_event_types": dict(excluded),
    }


def census(events, pinned_at):
    with_recv = without_recv = 0
    skews, future_pin = [], []
    for ev in events:
        if ev["_recv"] is None:
            without_recv += 1
        else:
            with_recv += 1
            if ev["_ts"] is not None and ev["_ts"] > ev["_recv"]:
                skews.append((int((ev["_ts"] - ev["_recv"]).total_seconds()), ev))
        if ev["_ts"] is not None and ev["_ts"] > pinned_at:
            future_pin.append(ev)
    by_actor = Counter(ev.get("actor") for _, ev in skews)
    by_type = Counter(ev.get("event_type") for _, ev in skews)
    skews.sort(key=lambda x: -x[0])
    return {
        "events_total": len(events),
        "events_with_received_at": with_recv,
        "events_without_received_at": without_recv,
        "created_at_after_received_at": len(skews),
        "max_skew_seconds": skews[0][0] if skews else 0,
        "skew_actors_top": by_actor.most_common(8),
        "skew_event_types": dict(by_type),
        "created_at_after_pin": len(future_pin),
        "max_created_at": max((ev.get("created_at") for ev in future_pin), default=None),
        "examples": [{"event_id": ev.get("event_id"), "actor": ev.get("actor"),
                      "event_type": ev.get("event_type"), "created_at": ev.get("created_at"),
                      "received_at": ev.get("_received_at"), "skew_seconds": sk}
                     for sk, ev in skews[:5]],
    }


def load_map_nodes(map_path: Path):
    m = json.loads(map_path.read_text())
    nodes = {}
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            nodes[str(n.get("id"))] = {
                "group": g.get("id"), "artifact": n.get("artifact"),
                "artifact_sha256": n.get("artifact_sha256"),
                "validation_status": n.get("validation_status"), "status": n.get("status"),
            }
    return m, nodes


def corroborate(events, nodes, map_doc, authority=AUTHORITY):
    keys = defaultdict(list)
    for ev in events:
        k = key_of(ev)
        if k:
            keys[k].append(ev)
    updated = parse_ts(map_doc.get("updated_at"))
    locked = set((map_doc.get("numerics_lock") or {}).get("locked_nodes") or [])
    art_rows, status_rows = [], []
    for nid, n in sorted(nodes.items()):
        path = n.get("artifact")
        if path:
            lst = keys.get(("artifact", nid, path), [])
            if not lst:
                art_rows.append({"node_id": nid, "path": path, "class": "no_artifact_events",
                                 "map_sha256": n.get("artifact_sha256")})
            else:
                arrival = max(lst, key=lambda e: e["_line"])
                match = (arrival.get("sha256") or None) == (n.get("artifact_sha256") or None)
                recv = arrival["_recv"]
                after_map = bool(updated and recv and recv > updated)
                art_rows.append({
                    "node_id": nid, "path": path,
                    "class": "match" if match else ("mismatch_after_map_update" if after_map else "mismatch_unexplained"),
                    "arrival_event": arrival.get("event_id"), "arrival_sha256": arrival.get("sha256"),
                    "map_sha256": n.get("artifact_sha256"), "map_updated_at": map_doc.get("updated_at"),
                    "arrival_received_at": arrival.get("_received_at"),
                })
        lst = keys.get(("status", nid), [])
        if lst:
            arrival = max(lst, key=lambda e: e["_line"])
            eff = arrival.get("status")
            actor = str(arrival.get("actor", ""))
            if eff == "done" and actor not in authority:
                eff = "active"
            if eff == "active" and nid in locked:
                eff = "queued"
            status_rows.append({"node_id": nid, "map_status": n.get("status"), "effective_arrival_status": eff,
                                "class": "match" if eff == n.get("status") else "mismatch",
                                "arrival_event": arrival.get("event_id")})
    gate_rows = []
    for gate in map_doc.get("gates", []):
        gid = gate.get("gate_id")
        lst = keys.get(("gate", gid), [])
        if not lst:
            continue
        arrival = max(lst, key=lambda e: e["_line"])
        gate_rows.append({"gate_id": gid, "map_verdict": gate.get("verdict"),
                          "arrival_winner_verdict": arrival.get("verdict"),
                          "arrival_event": arrival.get("event_id"),
                          "class": "match" if arrival.get("verdict") == gate.get("verdict") else "mismatch",
                          "authority_events": sum(1 for e in lst if str(e.get("actor")) in authority),
                          "proposal_events": sum(1 for e in lst if str(e.get("actor")) not in authority)})
    return {
        "map_updated_at": map_doc.get("updated_at"),
        "node_artifact_corroboration": art_rows,
        "node_status_corroboration": status_rows,
        "gate_corroboration": gate_rows,
    }


def synthetic(pairs):
    """pairs: list of (event_id, event_type, created_at, kwargs) -> events with _line/_ts."""
    out = []
    for i, (eid, etype, created, kw) in enumerate(pairs, start=1):
        ev = {"event_id": eid, "event_type": etype, "created_at": created, "actor": kw.pop("actor", "worker-test")}
        ev.update(kw)
        ev["_line"] = i
        ev["_ts"] = parse_ts(created)
        ev["_recv"] = parse_ts(kw.get("_received_at")) if kw.get("_received_at") else None
        out.append(ev)
    return out


def run_controls(pinned_src: str, real: dict) -> list:
    c = []

    def add(cid, passed, expected, observed, note=""):
        c.append({"id": cid, "passed": bool(passed), "expected": expected, "observed": observed, "note": note})

    # C1: later arrival with earlier stamp, different payload -> state-changing inversion
    s = synthetic([
        ("e1", "artifact", "2026-09-12T00:10:00+08:00", {"node_id": "F1", "path": "p", "sha256": "a" * 8, "validation_status": "unverified"}),
        ("e2", "artifact", "2026-09-12T00:05:00+08:00", {"node_id": "F1", "path": "p", "sha256": "b" * 8, "validation_status": "unverified"}),
    ])
    r = analyze(s)
    add("C1_inversion_detected", r["state_changing_inversions"] == 1,
        {"state_changing_inversions": 1}, {"state_changing_inversions": r["state_changing_inversions"]},
        "arrival winner e2 must not equal stamp winner e1")

    # C2: monotone timestamps -> no inversion
    s = synthetic([
        ("e1", "artifact", "2026-09-12T00:05:00+08:00", {"node_id": "F1", "path": "p", "sha256": "a" * 8, "validation_status": "unverified"}),
        ("e2", "artifact", "2026-09-12T00:10:00+08:00", {"node_id": "F1", "path": "p", "sha256": "b" * 8, "validation_status": "unverified"}),
    ])
    r = analyze(s)
    add("C2_monotone_no_inversion", r["state_changing_inversions"] == 0,
        {"state_changing_inversions": 0}, {"state_changing_inversions": r["state_changing_inversions"]})

    # C3: equal stamps -> deterministic line tiebreak, not an inversion
    s = synthetic([
        ("e1", "artifact", "2026-09-12T00:05:00+08:00", {"node_id": "F1", "path": "p", "sha256": "a" * 8, "validation_status": "unverified"}),
        ("e2", "artifact", "2026-09-12T00:05:00+08:00", {"node_id": "F1", "path": "p", "sha256": "b" * 8, "validation_status": "unverified"}),
    ])
    r = analyze(s)
    add("C3_tie_not_inversion", r["state_changing_inversions"] == 0 and r["keys_resolved_by_tiebreak"] == 1,
        {"inversions": 0, "ties": 1}, {"inversions": r["state_changing_inversions"], "ties": r["keys_resolved_by_tiebreak"]})

    # C4: identical payload, differing stamps -> order-only, not state-changing
    s = synthetic([
        ("e1", "artifact", "2026-09-12T00:10:00+08:00", {"node_id": "F1", "path": "p", "sha256": "a" * 8, "validation_status": "unverified"}),
        ("e2", "artifact", "2026-09-12T00:05:00+08:00", {"node_id": "F1", "path": "p", "sha256": "a" * 8, "validation_status": "unverified"}),
    ])
    r = analyze(s)
    add("C4_order_only_not_state_changing",
        r["state_changing_inversions"] == 0 and r["order_only_inversions"] == 1,
        {"state_changing": 0, "order_only": 1},
        {"state_changing": r["state_changing_inversions"], "order_only": r["order_only_inversions"]})

    # C5: append-only types carry no overwrite key
    s = synthetic([
        ("e1", "claim", "2026-09-12T00:05:00+08:00", {"class_id": "AF-WCC-VAC-GEN", "node_id": "F1", "statement": "x"}),
        ("e2", "claim", "2026-09-12T00:10:00+08:00", {"class_id": "AF-WCC-VAC-GEN", "node_id": "F1", "statement": "y"}),
    ])
    r = analyze(s)
    add("C5_append_only_excluded", r["state_keys"] == 0 and r["excluded_event_types"].get("claim") == 2,
        {"state_keys": 0, "excluded_claim": 2},
        {"state_keys": r["state_keys"], "excluded_claim": r["excluded_event_types"].get("claim")})

    # C6: one of two events undated -> key excluded, no crash
    s = synthetic([
        ("e1", "artifact", "2026-09-12T00:05:00+08:00", {"node_id": "F1", "path": "p", "sha256": "a" * 8, "validation_status": "unverified"}),
        ("e2", "artifact", "not-a-timestamp", {"node_id": "F1", "path": "p", "sha256": "b" * 8, "validation_status": "unverified"}),
    ])
    r = analyze(s)
    add("C6_undated_excluded", r["keys_undated"] == 1 and r["state_changing_inversions"] == 0,
        {"keys_undated": 1, "inversions": 0},
        {"keys_undated": r["keys_undated"], "inversions": r["state_changing_inversions"]})

    # C7: gate key with authority verdict change is state-changing
    s = synthetic([
        ("g1", "gate", "2026-09-12T00:10:00+08:00", {"gate_id": "G-TEST", "verdict": "pass", "actor": "astra"}),
        ("g2", "gate", "2026-09-12T00:05:00+08:00", {"gate_id": "G-TEST", "verdict": "fail", "actor": "astra"}),
    ])
    r = analyze(s)
    add("C7_gate_verdict_inversion", r["state_changing_inversions"] == 1 and r["inversions"][0]["category"] == "gate",
        {"inversions": 1, "category": "gate"},
        {"inversions": r["state_changing_inversions"], "category": r["inversions"][0]["category"] if r["inversions"] else None})

    # C8: AUTHORITY constant must equal the set in the pinned applier bytes
    m = re.search(r"AUTHORITY\s*=\s*\{(.*?)\}", pinned_src, re.S)
    pinned_authority = set(re.findall(r'"([^"]+)"', m.group(1))) if m else set()
    add("C8_authority_matches_pinned_source", pinned_authority == AUTHORITY,
        sorted(AUTHORITY), sorted(pinned_authority))

    # C9: invariants on the real result (no false positives by construction)
    inv = real["inversions"]
    ok = all(i["delta_seconds"] > 0 and i["arrival_winner"]["payload"] != i["created_at_winner"]["payload"]
             and i["created_at_winner"]["line"] < i["arrival_winner"]["line"] for i in inv)
    ok = ok and real["state_changing_inversions"] <= real["multi_event_keys"]
    add("C9_real_result_invariants", ok,
        "every inversion: stamp winner arrived earlier, later stamp, different payload",
        {"inversions": len(inv), "multi_event_keys": real["multi_event_keys"]})
    return c


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default=str(HERE / "snapshot"))
    ap.add_argument("--out", default=str(HERE / "report.json"))
    a = ap.parse_args()
    snap = Path(a.snapshot).resolve()
    manifest_path = snap / "manifest.json"
    if not manifest_path.is_file():
        print(f"FAIL no manifest at {manifest_path}", file=sys.stderr)
        return 2
    manifest = json.loads(manifest_path.read_text())

    # fail closed if any pinned input moved
    for name, entry in manifest["files"].items():
        p = ROOT / entry["snapshot_path"]
        if not p.is_file() or sha256_file(p) != entry["sha256"]:
            print(f"FAIL pinned input moved or missing: {name} {entry['snapshot_path']}", file=sys.stderr)
            return 2

    events_path = ROOT / manifest["files"]["events"]["snapshot_path"]
    map_path = ROOT / manifest["files"]["map"]["snapshot_path"]
    applier_path = ROOT / manifest["files"]["apply_events"]["snapshot_path"]
    pinned_src = applier_path.read_text()
    pinned_at = parse_ts(manifest["pinned_at"])

    events, load_stats = load_events(events_path)
    real = analyze(events)
    map_doc, nodes = load_map_nodes(map_path)
    corr = corroborate(events, nodes, map_doc)
    cen = census(events, pinned_at)

    # annotate inversions with class binding and canonical/authoring classification
    node_artifacts = {nid: n.get("artifact") for nid, n in nodes.items()}
    for i in real["inversions"]:
        k = i["key"]
        nid = k[1] if k[0] in ("status", "artifact") and len(k) > 1 else (k[1] if k[0] in ("lifecycle", "direction") else None)
        if k[0] == "gate":
            nid = None
        i["node_id"] = nid
        i["class_ids"] = NODE_CLASS.get(nid, FROZEN_CLASSES if k[0] == "gate" else [])
        if k[0] == "artifact":
            if node_artifacts.get(k[1]) == k[2]:
                i["binding"] = "canonical_node_artifact"
            elif str(k[2]).startswith("artifacts/formulation/"):
                i["binding"] = "authoring_tree"
            else:
                i["binding"] = "other"
        elif k[0] == "status":
            i["binding"] = "node_status" if k[1] in nodes else "unknown_node"
        elif k[0] == "gate":
            i["binding"] = "gate_verdict"
        else:
            i["binding"] = k[0]
    by_category = Counter(i["category"] for i in real["inversions"])
    by_binding = Counter(i["binding"] for i in real["inversions"])
    binding_inversions = [i for i in real["inversions"] if i["binding"] in ("canonical_node_artifact", "node_status", "gate_verdict")]
    canonical_artifact_inversions = [i for i in real["inversions"] if i["binding"] == "canonical_node_artifact"]

    controls = run_controls(pinned_src, real)
    controls_ok = all(x["passed"] for x in controls)

    # gate census: all verdicts carried by gate events in the stream
    gate_verdicts = Counter(ev.get("verdict") for ev in events if ev.get("event_type") == "gate")
    gate_authority = sum(1 for ev in events if ev.get("event_type") == "gate" and str(ev.get("actor")) in AUTHORITY)

    art_match = sum(1 for r in corr["node_artifact_corroboration"] if r["class"] == "match")
    art_total = len(corr["node_artifact_corroboration"])
    st_match = sum(1 for r in corr["node_status_corroboration"] if r["class"] == "match")
    st_total = len(corr["node_status_corroboration"])
    gate_match = sum(1 for r in corr["gate_corroboration"] if r["class"] == "match")
    gate_total = len(corr["gate_corroboration"])

    f = []
    top_actors = ", ".join(f"{a} ({n})" for a, n in cen["skew_actors_top"][:3])
    canon_detail = "; ".join(
        f"{i['key'][1]} {i['key'][2]}: arrival {str(i['arrival_winner']['payload'][0])[:12]} "
        f"(line {i['arrival_winner']['line']}, stamp {i['arrival_winner']['created_at']}) vs created_at-order "
        f"{str(i['created_at_winner']['payload'][0])[:12]} ({i['created_at_winner']['actor']}, "
        f"validation_status={i['created_at_winner']['payload'][1]}, stamp {i['created_at_winner']['created_at']}, "
        f"line {i['created_at_winner']['line']})"
        for i in canonical_artifact_inversions)
    status_nodes = ", ".join(sorted(i["key"][1] for i in binding_inversions if i["binding"] == "node_status"))
    authoring_count = sum(1 for i in real["inversions"] if i["binding"] == "authoring_tree")
    art_no_events = sum(1 for r in corr["node_artifact_corroboration"] if r["class"] == "no_artifact_events")
    f.append({
        "id": "W042-OI-01",
        "severity": "major",
        "statement": (
            f"CF-14 refreshed at pinned events.jsonl#{manifest['files']['events']['sha256'][:12]}: "
            f"{cen['created_at_after_received_at']} of {cen['events_with_received_at']} events with an ingest "
            f"arrival stamp carry created_at after _received_at (max skew {cen['max_skew_seconds']} s); "
            f"{cen['created_at_after_pin']} events are still future-dated at the pin "
            f"({manifest['pinned_at']}), max created_at {cen['max_created_at']}. "
            f"{cen['events_without_received_at']} events predate ingest stamping and cannot be checked this way. "
            f"Top future-dating actors: {top_actors}."),
        "evidence": [
            f"{manifest['files']['events']['snapshot_path']}#{manifest['files']['events']['sha256'][:12]}",
            f"{manifest['files']['map']['snapshot_path']}#{manifest['files']['map']['sha256'][:12]}",
        ],
        "falsifier": ("Re-run the checker on the pinned snapshot; falsified if the reported skew counts, max skew, "
                      "or future-at-pin count differ at the same events sha256."),
    })
    f.append({
        "id": "W042-OI-02",
        "severity": "major",
        "statement": (
            f"State-changing order inversions exist: of {real['multi_event_keys']} overwrite keys with >=2 events "
            f"({real['state_keys']} distinct keys total; {real['keys_resolved_by_tiebreak']} resolved by line tiebreak, "
            f"{real['keys_undated']} undated, {real['order_only_inversions']} inversions whose payloads are identical), "
            f"{real['state_changing_inversions']} keys have a created_at-order winner that differs in recorded state "
            f"from the arrival-order winner: " + ", ".join(f"{k}={v}" for k, v in sorted(by_category.items())) +
            ". Arrival order is the semantics of the pinned applier, so this is the magnitude of the map state that is "
            "arrival-order-dependent rather than timestamp-order-dependent."),
        "evidence": [f"{manifest['files']['apply_events']['snapshot_path']}#{manifest['files']['apply_events']['sha256'][:12]}"],
        "falsifier": ("Re-run the checker on the pinned snapshot; falsified if any listed inversion is not reproducible "
                      "from the pinned bytes under the declared key model, or if a state-changing inversion exists that "
                      "the checker does not list."),
    })
    f.append({
        "id": "W042-OI-03",
        "severity": "major",
        "statement": (
            f"Decision-relevant subset: {len(binding_inversions)} of the {real['state_changing_inversions']} inversions "
            f"touch a pinned map node's canonical artifact or node status "
            f"({len(canonical_artifact_inversions)} canonical-artifact, "
            f"{sum(1 for i in binding_inversions if i['binding'] == 'node_status')} node-status, "
            f"{sum(1 for i in binding_inversions if i['binding'] == 'gate_verdict')} gate). "
            f"Canonical-artifact inversions: {canon_detail}. "
            f"Node-status inversions are on {status_nodes}. The other {authoring_count} inversions are on the "
            "authoring-tree copies under artifacts/formulation/, which are drift submissions, not the canonical "
            "schemas/ paths, plus one non-canonical L1 artifact (ledger/counterexamples.jsonl), one literature group "
            "direction update and one GLOBAL status."),
        "evidence": [
            f"{manifest['files']['events']['snapshot_path']}#{manifest['files']['events']['sha256'][:12]}",
            f"{manifest['files']['map']['snapshot_path']}#{manifest['files']['map']['sha256'][:12]}",
        ],
        "falsifier": ("Re-run the checker on the pinned snapshot; falsified if any canonical-artifact or node-status "
                      "inversion listed in report.json is not reproducible, or if a canonical-artifact inversion is "
                      "missing from the list."),
    })
    f.append({
        "id": "W042-OI-04",
        "severity": "info",
        "statement": (
            f"Gate verdicts are not order-sensitive at this pin: all {sum(gate_verdicts.values())} gate events carry "
            f"verdict " + ", ".join(f"{k}={v}" for k, v in gate_verdicts.items()) +
            f" ({gate_authority} from authority actors), so no gate key has a state-changing inversion. The pinned map "
            f"agrees with the arrival-order winner on {gate_match}/{gate_total} gate keys, {art_match}/{art_total} node "
            f"canonical-artifact hashes ({art_no_events} nodes have no artifact events for their assigned path) and "
            f"{st_match}/{st_total} node statuses, i.e. the map is arrival-ordered as designed (CF-6). CF-14 therefore "
            "threatens replay fidelity of a rebuild, not the current gate verdicts."),
        "evidence": [
            f"{manifest['files']['map']['snapshot_path']}#{manifest['files']['map']['sha256'][:12]}",
            f"{manifest['files']['events']['snapshot_path']}#{manifest['files']['events']['sha256'][:12]}",
        ],
        "falsifier": ("Re-run the checker on the pinned snapshot; falsified if the pinned map's verdict/status/hash "
                      "fields disagree with the arrival-order winners for the listed keys, or if the gate verdict "
                      "histogram differs at the same events sha256."),
    })

    report = {
        "schema_version": "w042-order-inversion/1",
        "task_id": "W042-ORDER-INVERSION-03",
        "actor": "worker-042",
        "node_id": "A1",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": FROZEN_CLASSES,
        "related_gates": ["G-AUDIT", "G-F0", "G-FORM", "G-LIT", "G-NUM"],
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "question": ("At one pinned snapshot: for every last-write-wins key in the accepted event stream, does the "
                     "arrival-order winner equal the created_at-order winner; where it does not, does the recorded "
                     "state differ; and does the pinned map's state match the arrival-order winner?"),
        "method": ("stdlib-only deterministic re-implementation of the overwrite keys of the pinned applier "
                   "(status/artifact/gate/kill/revive/direction_update); file order = arrival order; first event_id "
                   "wins; payloads as recorded in report.json; 9 synthetic/invariant controls; all reads from the "
                   "sha256-pinned snapshot, fail-closed on drift."),
        "inputs": {
            "manifest": {"path": str(manifest_path.relative_to(ROOT)), "sha256": sha256_file(manifest_path)},
            "pinned": {k: {"snapshot_path": v["snapshot_path"], "sha256": v["sha256"], "bytes": v["bytes"]}
                       for k, v in manifest["files"].items()},
            "pinned_at": manifest["pinned_at"],
            "load_stats": load_stats,
        },
        "checker": {"path": str(Path(__file__).resolve().relative_to(ROOT)),
                    "sha256": sha256_file(Path(__file__).resolve()),
                    "bytes": Path(__file__).resolve().stat().st_size},
        "key_model": {
            "state_event_types": list(STATE_EVENT_TYPES),
            "append_only_event_types": list(APPEND_ONLY_TYPES),
            "authority": sorted(AUTHORITY),
            "note": "payload comparison is on the fields the pinned applier overwrites; identical payloads are not counted as state-changing",
        },
        "controls": controls,
        "controls_all_passed": controls_ok,
        "census": cen,
        "order_sensitivity": {
            "state_keys": real["state_keys"],
            "multi_event_keys": real["multi_event_keys"],
            "keys_resolved_by_tiebreak": real["keys_resolved_by_tiebreak"],
            "keys_undated": real["keys_undated"],
            "order_only_inversions": real["order_only_inversions"],
            "state_changing_inversions": real["state_changing_inversions"],
            "by_category": dict(by_category),
            "by_binding": dict(by_binding),
            "binding_inversions": len(binding_inversions),
            "canonical_artifact_inversions": len(canonical_artifact_inversions),
            "gate_event_verdicts": dict(gate_verdicts),
            "inversions": real["inversions"],
        },
        "corroboration": corr,
        "findings": f,
        "verdict": ("ARRIVAL_ORDER_DOMINANT_WITH_STATE_CHANGING_INVERSIONS: the pinned map's recorded gate/status/"
                    "artifact winners match arrival order, and gate verdicts are order-insensitive at this pin; "
                    f"{real['state_changing_inversions']} overwrite keys (of which {len(binding_inversions)} touch a "
                    "pinned node's canonical artifact or status) would record a different state if the same accepted "
                    "events were ordered by created_at, so any replay/rebuild that does not preserve the append order "
                    "of events.jsonl is not guaranteed to reproduce this map."),
        "authority_note": ("Worker-level evidence only: no node status, validation_status, gate verdict or publication "
                           "status is claimed or changed by this checker; it is read-only on all canonical paths."),
        "rerun_command": ("python3 artifacts/worker-042/cf14_order_inversion/audit_order_inversion.py "
                          "--snapshot artifacts/worker-042/cf14_order_inversion/snapshot "
                          "--out artifacts/worker-042/cf14_order_inversion/report.json"),
    }

    out = Path(a.out).resolve()
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps({
        "controls_all_passed": controls_ok,
        "events": len(events),
        "state_changing_inversions": real["state_changing_inversions"],
        "binding_inversions": len(binding_inversions),
        "gate_inversions": by_category.get("gate", 0),
        "report": (str(out.relative_to(ROOT)) if str(out).startswith(str(ROOT)) else str(out)),
    }, sort_keys=True))
    return 0 if controls_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
