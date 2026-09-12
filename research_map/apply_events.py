"""Astra reconciler: apply validated comms events to the sole global state.

  python3 research_map/apply_events.py            # apply pending, reconcile structure
  python3 research_map/apply_events.py --dry-run
  python3 research_map/apply_events.py --report

Guarantees:
  - sole global state: research_map/research_map.json (atomic write via tmp+rename)
  - idempotent: an event is applied at most once (applied_event_ids in the map)
  - conservative promotion: an `artifact` event never marks a node done; only a
    reviewer `accept` + gate pass can, and only when the artifact exists on disk.
  - unbacked `done` nodes are demoted automatically and recorded as evidence gaps.
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research_map"))
import comms  # noqa: E402
from validate_map import validate_map  # noqa: E402

CST = timezone(timedelta(hours=8))
MAP = ROOT / "research_map" / "research_map.json"
# Only the controller and group leads may move a node to done or set a gate verdict.
AUTHORITY = {"astra", "lead-formulation", "lead-literature", "lead-numerics", "lead-audit",
             "astra-lead-formulation", "astra-lead-literature", "astra-lead-numerics", "astra-lead-audit"}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def node_index(m):
    idx = {}
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            idx[n["id"]] = (g, n)
    return idx


def reconcile_structure(m, events):
    """Ensure controller-owned sections exist; demote unbacked done nodes."""
    m.setdefault("run", {})
    m["run"].update({
        "run_id": "run-2026-09-11T23:15+08:00",
        "started_at": "2026-09-11T23:15:11+08:00",
        "deadline": "2026-09-12T03:15:11+08:00",
        "invocation": "astra-controller 4h",
        "checkpoint_interval_minutes": 15,
        "parallelism_authorized": 25,
    })
    m.setdefault("comms", {
        "protocol": "comms/PROTOCOL.md",
        "event_stream": "research_map/events.jsonl",
        "rejects": "comms/rejected.jsonl",
        "inbox": "comms/inbox/<agent>.jsonl",
        "outbox": "comms/outbox/<agent>.jsonl",
        "ingest": "python3 research_map/comms.py ingest",
        "controller_tools": ["validate_map.py", "audit_evidence.py", "checkpoint.py", "apply_events.py"],
    })
    m.setdefault("gates", [])
    known = {g["gate_id"] for g in m["gates"]}
    defaults = [
        dict(gate_id="G-F0", scope="F0", verdict="pending",
             criteria="formulation_taxonomy.yaml exists; exactly 4 separate class ids; disjointness tests; 2 independent reviewer verdicts",
             evidence_refs=["research_map/formulation_taxonomy.yaml", "schemas/taxonomy_cases.jsonl"], owner="lead-formulation"),
        dict(gate_id="G-FORM", scope="F1,F2a,F2b", verdict="pending",
             criteria="all three schemas exist with exact quantifiers/topology/regularity/genericity/I+/visibility/conclusion_type; no C0/C2 merge; reviewers 17,18 accept with cited sha256",
             evidence_refs=["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"], owner="lead-formulation"),
        dict(gate_id="G-LIT", scope="L0,L1", verdict="pending",
             criteria="ledger rows have resolvable locators; verification_status honest; >=3 independent re-fetch spot checks; unresolved marked unresolved",
             evidence_refs=["ledger/theorems.jsonl", "ledger/citation_audit.csv"], owner="lead-literature"),
        dict(gate_id="G-NUM", scope="N0", verdict="pending",
             criteria="flat-space convergence order measured AND independently replicated within tolerance; protocol reviewed; lock guard passes",
             evidence_refs=["numerics/tests/flat_wave.py", "numerics/tests/flat_wave_replication.py"], owner="lead-numerics"),
        dict(gate_id="G-AUDIT", scope="A0,A1", verdict="pending",
             criteria="evaluation_rubric.yaml exists without a universal scalar score; A1 has 2 independent verdicts per formulation/literature target with cited sha256",
             evidence_refs=["evaluation_rubric.yaml", "reviews/"], owner="lead-audit"),
    ]
    for d in defaults:
        if d["gate_id"] not in known:
            m["gates"].append(d)
    m.setdefault("numerics_lock", {
        "state": "locked",
        "since": "2026-09-11T23:15:11+08:00",
        "locked_nodes": ["N1"],
        "allowed_nodes": ["N0"],
        "required_gates": ["G-FORM", "G-AUDIT"],
        "additional_requirements": [
            "N0 convergence order measured and independently replicated",
            "numerical protocol reviewed by audit",
        ],
        "release_authority": "astra",
        "escalation": "human-pi",
        "note": "No self-gravitating solver code may be written or run while locked (ASTRA_HANDOFF hard decision 2).",
    })
    m.setdefault("claims", [])
    m.setdefault("reviews", [])
    m.setdefault("resource_requests", [])
    m.setdefault("assignments", [])
    m.setdefault("applied_event_ids", [])
    m.setdefault("portfolio_events", [])

    # demote unbacked done nodes
    demoted = []
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            if n.get("status") == "done":
                art = n.get("artifact")
                if not art or not (ROOT / art).exists():
                    n["status"] = "active"
                    n["validation_status"] = "unverified"
                    n["evidence_gap"] = {
                        "recorded_at": now(),
                        "detail": f"map claimed done; artifact {art!r} absent on disk; status demoted by controller",
                    }
                    demoted.append(n["id"])

    # auxiliary control nodes (not locks themselves)
    numerics = next((g for g in m.get("groups", []) if g["id"] == "numerics"), None)
    if numerics and not any(n["id"] == "N1-BLOCK" for n in numerics["nodes"]):
        numerics["nodes"].append({
            "id": "N1-BLOCK", "label": "Self-gravity unblock contract",
            "status": "queued", "hours": 0, "eta_days": 1,
            "artifact": "numerics/blockers.md", "depends_on": ["N0"],
            "class_id": "AF-WCC-SCALAR-SPH", "gate": "G-NUM",
            "evidence_refs": ["research_map/ASTRA_HANDOFF.md:31"],
            "falsifier": "Document proposes a self-gravity run, or an unblock condition not matched by a map gate.",
        })

    # F2 split (controller repair 2026-09-12): one artifact per class. The legacy
    # schemas/af_scc_regularities.yaml is a non-class aggregator, never a class artifact.
    formulation = next((g for g in m.get("groups", []) if g["id"] == "formulation"), None)
    if formulation:
        ids = {n["id"] for n in formulation["nodes"]}
        if "F2" in ids and not ({"F2a", "F2b"} & ids):
            for n in formulation["nodes"]:
                if n["id"] == "F2":
                    n["id"] = "F2a"
                    n["label"] = "AF-SCC C2 vacuum schema"
                    n["artifact"] = "schemas/af_scc_c2_vacuum.yaml"
                    n["artifact_exists"] = (ROOT / n["artifact"]).exists()
                    n.setdefault("lifecycle", []).append({
                        "at": now(), "event": "split",
                        "reason": "controller DAG repair: F2 -> F2a/F2b (one artifact per class); "
                                  "schemas/af_scc_regularities.yaml is a non-class aggregator"})
                    break
            formulation["nodes"].append({
                "id": "F2b", "label": "AF-SCC C0 vacuum schema",
                "status": "active", "validation_status": "unverified",
                "hours": 0, "eta_days": 0,
                "artifact": "schemas/af_scc_c0_vacuum.yaml",
                "artifact_exists": (ROOT / "schemas/af_scc_c0_vacuum.yaml").exists(),
                "depends_on": ["F0"], "class_id": "AF-SCC-C0-VAC-GEN"})
            m.setdefault("portfolio_events", []).append({
                "time": now(), "actor": "astra",
                "event": "split node F2 into F2a (AF-SCC-C2-VAC-GEN) and F2b (AF-SCC-C0-VAC-GEN); "
                         "legacy schemas/af_scc_regularities.yaml demoted to non-class aggregator"})

    # machine-checkable class binding on every node (reviewer-19 finding C5)
    NODE_CLASS = {
        "F0": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "F1": ["AF-WCC-VAC-GEN"],
        "F2a": ["AF-SCC-C2-VAC-GEN"],
        "F2b": ["AF-SCC-C0-VAC-GEN"],
        "L0": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "L1": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "N0": ["AF-WCC-SCALAR-SPH"],
        "N1": ["AF-WCC-SCALAR-SPH"],
        "N1-BLOCK": ["AF-WCC-SCALAR-SPH"],
        "A0": ["GLOBAL"], "A1": ["GLOBAL"], "A2": ["GLOBAL"],
    }
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            if n["id"] in NODE_CLASS:
                n["class_ids"] = NODE_CLASS[n["id"]]
                n["class_id"] = ";".join(NODE_CLASS[n["id"]])

    # canonical assigned artifact per node: a worker submission must never silently
    # replace the controller-assigned path (assignment drift control).
    CANONICAL = {
        "F0": "research_map/formulation_taxonomy.yaml",
        "F1": "schemas/af_wcc_vacuum.yaml",
        "F2a": "schemas/af_scc_c2_vacuum.yaml",
        "F2b": "schemas/af_scc_c0_vacuum.yaml",
        "L0": "ledger/theorems.jsonl",
        "L1": "ledger/citation_audit.csv",
        "N0": "numerics/tests/flat_wave.py",
        "N1": "numerics/spherical_solver/",
        "N1-BLOCK": "numerics/blockers.md",
        "A0": "evaluation_rubric.yaml",
        "A1": "reviews/",
        "A2": "evaluation/ablation.csv",
    }
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            canon = CANONICAL.get(n["id"])
            if not canon:
                continue
            cur = n.get("artifact")
            if cur and cur != canon:
                n.setdefault("artifact_submissions", []).append(
                    {"at": now(), "by": "pre-repair", "path": cur,
                     "sha256": n.get("artifact_sha256"), "validation_status": n.get("validation_status"),
                     "kind": "assignment_drift_repair"})
            n["artifact"] = canon
            n["artifact_exists"] = (ROOT / canon).exists()
            if n.get("evidence_gap") and n["artifact_exists"]:
                n["evidence_gap"]["resolved_at"] = now()
                n["evidence_gap"]["resolution"] = "declared artifact now present on disk; awaiting review/gate"
            # resolve blockers whose stated condition no longer holds
            assigned_nodes = {a.get("node_id") for a in m.get("assignments", [])}
            for b in n.get("blockers", []) or []:
                if b.get("resolved_at"):
                    continue
                text = (str(b.get("description", "")) + " " + str(b.get("needed_to_unblock", ""))).lower()
                if n["artifact_exists"] and canon.lower() in text and any(
                        w in text for w in ("does not exist", "absent", "missing", "not exist", "no artifact")):
                    b["resolved_at"] = now()
                    b["resolution"] = f"canonical artifact {canon} now present on disk; awaiting review"
                elif n["id"] in assigned_nodes and ("no assignment" in text or "no group-lead assignment" in text
                                                    or "no class-bound assignment" in text):
                    b["resolved_at"] = now()
                    b["resolution"] = "controller issued a class-bound assignment (comms/inbox); see map.assignments"
                elif any(w in text for w in ("no gates", "gates or numerics_lock", "has no gates",
                                             "no numerics_lock", "class_id on 0/10")):
                    b["resolved_at"] = now()
                    b["resolution"] = "controller added gates/numerics_lock/class_id to the map at 23:20"
    return demoted


def apply_one(m, ev, idx, applied):
    t = ev["event_type"]
    eid = ev["event_id"]
    if t == "status":
        g, n = idx.get(ev["node_id"], (None, None))
        if n:
            st = ev["status"]
            actor = str(ev.get("actor", ""))
            lock = m.get("numerics_lock", {})
            if (st == "active" and lock.get("state") == "locked"
                    and ev["node_id"] in lock.get("locked_nodes", [])):
                n.setdefault("lock_events", []).append(
                    {"at": ev.get("created_at"), "by": actor, "rejected_status": st,
                     "reason": "numerics_lock is locked; use N1-BLOCK for contract work"})
                st = "queued"
            if st == "done" and actor not in AUTHORITY:
                # a cheap agent may not promote; record the claim, keep the node honest
                n.setdefault("completion_claims", []).append(
                    {"at": ev.get("created_at"), "by": actor, "summary": ev.get("summary"),
                     "evidence_refs": ev.get("evidence_refs", [])})
                st = "active" if n.get("status") not in {"blocked", "killed"} else n.get("status")
            # pass-05 controller repair (CF-25): a node promoted to done on artifact + review
            # evidence is not demoted by a later worker status event. The 15-minute auto-cycle
            # applies traffic between controller passes, so without this guard any worker
            # "status=active" on a done node silently reverted the promotion.
            if n.get("status") == "done" and actor not in AUTHORITY:
                n.setdefault("status_events_ignored", []).append(
                    {"at": ev.get("created_at"), "by": actor, "rejected_status": st,
                     "reason": "node is done (promoted with artifact + review evidence); worker "
                               "status events cannot demote it"})
            else:
                n["status"] = st
            n["hours"] = max(n.get("hours", 0), float(ev.get("hours", 0) or 0))
            for k in ("eta_days",):
                if ev.get(k) is not None:
                    n[k] = ev[k]
            n["last_status"] = {"at": ev.get("created_at"), "by": actor, "summary": ev.get("summary"),
                                "evidence_refs": ev.get("evidence_refs", []),
                                "next_falsifier": ev.get("next_falsifier")}
        # controller decisions ride on status notices ("resource_request <id>: APPROVED ...").
        # The request id is a whitespace-delimited token and may itself contain colons
        # (e.g. leadform-resource-request-2026-09-12T00:44:00+08:00), so take the whole
        # token and strip a trailing separator rather than stopping at the first colon
        # (CF-14: the previous non-greedy matcher could not bind colon-bearing ids).
        summary = str(ev.get("summary", ""))
        if "resource_request" in summary and ("APPROVED" in summary or "DENIED" in summary):
            import re as _re
            tok = _re.search(r"resource_request\s+(\S+)", summary)
            rid_s = tok.group(1).rstrip(":,;.") if tok else None
            if rid_s:
                for r in m["resource_requests"]:
                    if r.get("event_id") == rid_s:
                        if r.get("status") == "superseded":
                            r["decision_note"] = ("ignored decision for superseded request: "
                                                  + summary[:300])
                            continue
                        r["status"] = "approved" if "APPROVED" in summary else "denied"
                        r["decision_at"] = now()
                        r["decision_by"] = "astra"
                        r["decision_note"] = summary[:400]
    elif t == "artifact":
        g, n = idx.get(ev["node_id"], (None, None))
        p = ROOT / ev["path"]
        actor = str(ev.get("actor", ""))
        if n:
            assigned = n.get("artifact")
            claimed_status = ev["validation_status"]
            if actor not in AUTHORITY and claimed_status == "passed":
                claimed_status = "unverified"
            record = {"at": ev.get("created_at"), "by": actor, "path": ev["path"],
                      "sha256": ev.get("sha256"), "validation_status": claimed_status,
                      "claimed_validation_status": ev["validation_status"],
                      "exists_on_disk": p.exists()}
            for fr in m.get("frozen_artifacts", []):
                if (fr.get("active", True) and fr["path"] == ev["path"]
                        and fr.get("sha256") != ev.get("sha256") and actor in AUTHORITY | {"deepseek-flash-01", "deepseek-flash-03", "deepseek-flash-06", "deepseek-flash-08"}):
                    fr["active"] = False
                    fr["superseded_at"] = now()
                    fr["superseded_by_event"] = eid
                    fr["superseded_note"] = "new revision received; re-dispatch reviews against the new hash"
            if assigned and ev["path"] != assigned:
                # assignment drift: keep the declared path canonical, record the submission
                n.setdefault("artifact_submissions", []).append(record)
            else:
                n["artifact"] = ev["path"]
                n["artifact_sha256"] = ev.get("sha256")
                n["validation_status"] = claimed_status
                n["artifact_exists"] = p.exists()
                if not p.exists():
                    n.setdefault("blockers", []).append(
                        {"at": now(), "kind": "artifact_missing_on_disk", "detail": ev["path"]})
    elif t == "claim":
        m["claims"].append({**ev, "promotion_status": "unpromoted",
                            "received_at": now()})
    elif t == "review":
        m["reviews"].append({**ev, "received_at": now()})
        g, n = idx.get(ev.get("target_id", ""), (None, None))
        if n:
            n.setdefault("review_verdicts", []).append(
                {"reviewer": ev["reviewer"], "verdict": ev["verdict"],
                 "score": ev["score"], "at": ev.get("created_at")})
    elif t == "blocker":
        g, n = idx.get(ev["node_id"], (None, None))
        if n:
            n.setdefault("blockers", []).append(
                {"at": ev.get("created_at"), "description": ev["description"],
                 "needed_to_unblock": ev["needed_to_unblock"], "evidence_refs": ev.get("evidence_refs", [])})
    elif t == "gate":
        actor = str(ev.get("actor", ""))
        if actor not in AUTHORITY:
            m.setdefault("gate_proposals", []).append({**ev, "status": "proposed",
                                                       "received_at": now()})
        else:
            for gate in m["gates"]:
                if gate["gate_id"] == ev["gate_id"]:
                    gate["verdict"] = ev["verdict"]
                    gate["evidence_refs"] = sorted(set(gate.get("evidence_refs", []) + ev.get("evidence_refs", [])))
                    gate["last_verdict_event"] = eid
                    gate["updated_at"] = now()
                    # Controller repair REC-40 (pass 08): an authority gate event may refresh the
                    # gate's own text fields too, so `unmet`/`criteria` text written at an older
                    # hash cannot survive a verdict event. Optional and backwards-compatible.
                    for key in ("criteria", "unmet", "controller_note", "eta", "owner"):
                        if key in ev:
                            gate[key] = ev[key]
    elif t == "direction_update":
        for g in m["groups"]:
            if g["id"] == ev["group_id"]:
                g.setdefault("direction_history", []).append(
                    {"at": now(), "old": ev["old_direction"], "new": ev["new_direction"],
                     "reason": ev["reason"], "evidence_refs": ev.get("evidence_refs", [])})
                g["direction"] = ev["new_direction"]
                g["spent_agent_hours"] = g.get("spent_agent_hours", 0) + float(ev.get("budget_delta_agent_hours", 0) or 0)
    elif t == "resource_request":
        m["resource_requests"].append({**ev, "status": "pending", "received_at": now()})
    elif t == "budget":
        for g in m["groups"]:
            if g["id"] == ev["group_id"]:
                g["budget_agent_hours"] = g.get("budget_agent_hours", 0) + float(ev["delta_agent_hours"])
                g.setdefault("budget_history", []).append({"at": now(), "delta": ev["delta_agent_hours"], "reason": ev["reason"]})
    elif t == "assignment":
        known = {a.get("event_id") for a in m["assignments"]}
        if eid not in known:
            m["assignments"].append({k: ev[k] for k in
                                     ("event_id", "node_id", "assignee", "artifact", "gate", "class_id",
                                      "acceptance", "budget_agent_hours", "expected_information_gain",
                                      "falsifier", "stop_rule", "deadline") if k in ev})
    elif t in {"kill", "revive"}:
        g, n = idx.get(ev["target_id"], (None, None))
        if n:
            n["status"] = "killed" if t == "kill" else "active"
            n.setdefault("lifecycle", []).append({"at": now(), "event": t, "reason": ev["reason"]})
    applied.append(eid)


def main(dry_run=False):
    m = json.loads(MAP.read_text())
    events = comms.load_events()
    demoted = reconcile_structure(m, events)
    idx = node_index(m)
    applied_ids = set(m.get("applied_event_ids", []))
    applied, skipped = [], []
    for ev in events:
        if ev["event_id"] in applied_ids:
            skipped.append(ev["event_id"])
            continue
        apply_one(m, ev, idx, applied)
        applied_ids.add(ev["event_id"])
    m["applied_event_ids"] = sorted(applied_ids)
    m["updated_at"] = now()
    # gate-derived promotion: never automatic for theorems; only flag consistency
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            if n.get("status") == "done":
                art = n.get("artifact")
                if not art or not (ROOT / art).exists():
                    n["status"] = "active"
                    n["validation_status"] = "unverified"
                    demoted.append(n["id"])
    errs = validate_map(m)
    if demoted:
        m["portfolio_events"].append({"time": now(), "actor": "astra", "event":
            f"demoted unbacked done nodes: {', '.join(sorted(set(demoted)))} (artifact absent on disk)"})
    if applied:
        kinds = {}
        for eid in applied:
            ev = next((e for e in events if e["event_id"] == eid), None)
            k = ev["event_type"] if ev else "event"
            kinds[k] = kinds.get(k, 0) + 1
        m["portfolio_events"].append({"time": now(), "actor": "astra", "event":
            f"applied {len(applied)} comms events: " + ", ".join(f"{k}={v}" for k, v in sorted(kinds.items()))})
    out = {"applied": len(applied), "skipped": len(skipped), "demoted": demoted,
           "map_errors": errs, "events_total": len(events)}
    if not dry_run:
        tmp = MAP.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(m, indent=2) + "\n")
        tmp.replace(MAP)
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    main(dry_run=a.dry_run)
