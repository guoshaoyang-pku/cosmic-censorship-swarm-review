#!/usr/bin/env python3
"""W024-APPLY-EVENTS-AUTHORITY-01: bounded authority-enforcement matrix.

Question (instrument claim, not a class-semantics claim): at the pinned revision of
research_map/apply_events.py, can a non-authority agent move authority state
(node done, validation_status=passed, gate verdict, resource-request decision,
budget, kill/revive, direction) by writing JSON into its own outbox file?

Method: a disposable sandbox under this artifact directory contains byte-identical
copies of the five canonical modules and a copy of the canonical map.  Every case is
driven end-to-end through the real pipeline:

    comms/outbox/<source>.jsonl  ->  python3 research_map/comms.py ingest
                                 ->  research_map/events.jsonl
                                 ->  python3 research_map/apply_events.py
                                 ->  sandbox map (inspected)

The canonical tree is never written.  Every canonical input is hash-pinned at start
and re-hashed at end; a drift sets pins_stable=false in the report.

Usage:  python3 drive_authority_matrix.py [--skip-patched]
"""
from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
BASE = Path(__file__).resolve().parent
SWARM = Path(__file__).resolve().parents[3]
CANON_RM = SWARM / "research_map"
MODULES = ["apply_events.py", "comms.py", "schemas.py", "validate_map.py", "class_separation.py"]
SANDBOX = BASE / "sandbox"
PRISTINE = BASE / "sandbox_pristine"
PATCHDIR = BASE / "patched"

# canonical inputs pinned by this audit
PINNED = {
    "research_map/apply_events.py": CANON_RM / "apply_events.py",
    "research_map/comms.py": CANON_RM / "comms.py",
    "research_map/schemas.py": CANON_RM / "schemas.py",
    "research_map/validate_map.py": CANON_RM / "validate_map.py",
    "research_map/class_separation.py": CANON_RM / "class_separation.py",
    "research_map/research_map.json": CANON_RM / "research_map.json",
    "runtime/bin/classsep_regression.py": SWARM / "runtime/bin/classsep_regression.py",
    "schemas/af_wcc_vacuum.yaml": SWARM / "schemas/af_wcc_vacuum.yaml",
}
# symlinked read-only into each sandbox so on-disk artifact checks resolve
LINK_DIRS = ["schemas", "ledger", "numerics", "reviews", "evaluation"]
LINK_FILES = ["evaluation_rubric.yaml"]


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure_pins() -> dict:
    pins = {"sha256": {label: sha256(p) for label, p in PINNED.items()},
            "budget": {}, "measured_at": now()}
    m0 = json.loads((CANON_RM / "research_map.json").read_text())
    for g in m0["groups"]:
        pins["budget"][g["id"]] = g.get("budget_agent_hours")
    return pins


PINS = measure_pins()


def build_pristine() -> None:
    if PRISTINE.exists():
        shutil.rmtree(PRISTINE)
    (PRISTINE / "research_map").mkdir(parents=True)
    (PRISTINE / "comms/outbox").mkdir(parents=True)
    (PRISTINE / "comms/inbox").mkdir(parents=True)
    (PRISTINE / "runtime/state").mkdir(parents=True)
    (PRISTINE / "runtime/bin").mkdir(parents=True)
    for m in MODULES:
        shutil.copy2(CANON_RM / m, PRISTINE / "research_map" / m)
    shutil.copy2(CANON_RM / "research_map.json", PRISTINE / "research_map/research_map.json")
    shutil.copy2(SWARM / "runtime/bin/classsep_regression.py", PRISTINE / "runtime/bin/classsep_regression.py")
    for d in LINK_DIRS:
        os.symlink(SWARM / d, PRISTINE / d)
    for f in LINK_FILES:
        os.symlink(SWARM / f, PRISTINE / f)
    # F0 canonical (research_map/formulation_taxonomy.yaml) is read by reconcile_structure
    os.symlink(SWARM / "research_map/formulation_taxonomy.yaml",
               PRISTINE / "research_map/formulation_taxonomy.yaml")


def reset_sandbox() -> None:
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    shutil.copytree(PRISTINE, SANDBOX, symlinks=True)


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=SANDBOX, capture_output=True, text=True, timeout=300)


def load_map(path: Path) -> dict:
    return json.loads(path.read_text())


def node(m: dict, nid: str) -> dict:
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            if n["id"] == nid:
                return n
    raise KeyError(nid)


def group(m: dict, gid: str) -> dict:
    return next(g for g in m["groups"] if g["id"] == gid)


def gate(m: dict, gid: str) -> dict:
    return next(g for g in m["gates"] if g["gate_id"] == gid)


# ---------------------------------------------------------------- case machinery
def ev_status(actor, nid, status, summary="no summary provided", **kw):
    d = {"event_id": kw.pop("event_id"), "event_type": "status", "created_at": now(), "actor": actor,
         "node_id": nid, "status": status, "hours": kw.pop("hours", 0.0), "summary": summary,
         "evidence_refs": kw.pop("evidence_refs", []), "next_falsifier": kw.pop("next_falsifier", "unspecified")}
    d.update(kw)
    return d


def ev_gate(actor, gid, verdict, **kw):
    d = {"event_id": kw.pop("event_id"), "event_type": "gate", "created_at": now(), "actor": actor,
         "gate_id": gid, "scope": kw.pop("scope", "F1,F2a,F2b"), "verdict": verdict,
         "criteria": kw.pop("criteria", "matrix probe"), "evidence_refs": kw.pop("evidence_refs", [])}
    d.update(kw)
    return d


def ev_artifact(actor, nid, path, digest, vstatus, **kw):
    d = {"event_id": kw.pop("event_id"), "event_type": "artifact", "created_at": now(), "actor": actor,
         "node_id": nid, "artifact_type": "schema", "path": path, "sha256": digest,
         "validation_status": vstatus}
    d.update(kw)
    return d


def ev_kill(actor, target, reason, **kw):
    d = {"event_id": kw.pop("event_id"), "event_type": "kill", "created_at": now(), "actor": actor,
         "target_id": target, "reason": reason}
    d.update(kw)
    return d


def ev_budget(actor, gid, delta, reason, **kw):
    d = {"event_id": kw.pop("event_id"), "event_type": "budget", "created_at": now(), "actor": actor,
         "group_id": gid, "delta_agent_hours": delta, "reason": reason}
    d.update(kw)
    return d


def ev_dir(actor, gid, old, new, reason, **kw):
    d = {"event_id": kw.pop("event_id"), "event_type": "direction_update", "created_at": now(), "actor": actor,
         "group_id": gid, "old_direction": old, "new_direction": new, "reason": reason,
         "evidence_refs": kw.pop("evidence_refs", []), "budget_delta_agent_hours": kw.pop("delta", 0)}
    d.update(kw)
    return d


def ev_assign(actor, nid, assignee, **kw):
    d = {"event_id": kw.pop("event_id"), "event_type": "assignment", "created_at": now(), "actor": actor,
         "node_id": nid, "assignee": assignee, "artifact": "schemas/af_wcc_vacuum.yaml",
         "gate": "G-FORM", "evidence_refs": [], "falsifier": "matrix probe falsifier",
         "class_id": "AF-WCC-VAC-GEN", "acceptance": "matrix probe acceptance",
         "budget_agent_hours": 0.5, "expected_information_gain": "matrix probe eig",
         "stop_rule": "one probe", "deadline": None}
    d.update(kw)
    return d


CASES: list[dict] = [
    # ---- forged authority: worker outbox file, declared actor is an authoritative id
    dict(id="F1", kind="forged_authority", source="worker-024.jsonl",
         spec="ASTRA_HANDOFF: worker events cannot set status=done. A declared actor that disagrees "
              "with the source file must not acquire authority.",
         expected_patched="F1 not done; completion claim or rejection recorded",
         events=[ev_status("astra", "F1", "done", event_id="f1-forged-done",
                           summary="forged authority probe: done", evidence_refs=["reviews/F1-review-088-rev12.json"],
                           class_ids=["AF-WCC-VAC-GEN"])],
         check=lambda m, r: (node(m, "F1")["status"] == "done",
                             f"F1.status={node(m,'F1')['status']}")),
    dict(id="F2", kind="forged_authority", source="worker-024.jsonl",
         spec="ASTRA_HANDOFF: worker events cannot set a gate verdict. Gate authority requires the "
              "declared actor AND a source file that backs it.",
         expected_patched="G-FORM verdict stays pending; gate proposal recorded",
         events=[ev_gate("astra-lead-audit", "G-FORM", "pass", event_id="f2-forged-gate",
                         evidence_refs=["schemas/af_wcc_vacuum.yaml"], class_ids=["AF-WCC-VAC-GEN"])],
         check=lambda m, r: (gate(m, "G-FORM")["verdict"] == "pass",
                             f"G-FORM.verdict={gate(m,'G-FORM')['verdict']}")),
    dict(id="F3", kind="forged_authority", source="worker-024.jsonl",
         spec="ASTRA_HANDOFF: workers cannot set validation_status=passed; only authority actors can, "
              "and the source file must match.",
         expected_patched="F1.validation_status stays unverified",
         events=[ev_artifact("astra", "F1", "schemas/af_wcc_vacuum.yaml", PINS["sha256"]["schemas/af_wcc_vacuum.yaml"],
                             "passed", event_id="f3-forged-passed", class_ids=["AF-WCC-VAC-GEN"])],
         check=lambda m, r: (node(m, "F1").get("validation_status") == "passed",
                             f"F1.validation_status={node(m,'F1').get('validation_status')}")),
    dict(id="F4", kind="unchecked_event", source="worker-024.jsonl",
         spec="PROTOCOL/PROTOCOL.md: Astra sends budget/gate changes; a resource-request decision is a "
              "controller decision. apply_events hardcodes decision_by=astra from a summary string.",
         expected_patched="resource request stays pending; unauthorized decision recorded",
         events=[ev_status("worker-024", "N0", "active",
                           summary="resource_request flash20-20260911T2324-resource-N0-review: APPROVED",
                           event_id="f4-self-approve", class_ids=["AF-WCC-SCALAR-SPH"])],
         check=lambda m, r: (next(x for x in m["resource_requests"]
                                  if x.get("event_id") == "flash20-20260911T2324-resource-N0-review")["status"] == "approved",
                             "rr.status=" + next(x for x in m["resource_requests"]
                                                 if x.get("event_id") == "flash20-20260911T2324-resource-N0-review")["status"])),
    dict(id="F5", kind="unchecked_event", source="worker-024.jsonl",
         spec="PROTOCOL: kill/revive are downward controller messages. apply_one has no actor check.",
         expected_patched="N0 status unchanged; unauthorized kill recorded",
         events=[ev_kill("worker-024", "N0", "unauthorized kill probe", event_id="f5-kill",
                         class_ids=["AF-WCC-SCALAR-SPH"])],
         check=lambda m, r: (node(m, "N0")["status"] == "killed", f"N0.status={node(m,'N0')['status']}")),
    dict(id="F6", kind="unchecked_event", source="worker-024.jsonl",
         spec="PROTOCOL: budget is a downward controller message. apply_one has no actor check and "
              "accepts negative deltas.",
         expected_patched="numerics budget unchanged",
         events=[ev_budget("worker-024", "numerics", 100.0, "unauthorized budget probe",
                           event_id="f6-budget", class_ids=["AF-WCC-SCALAR-SPH"])],
         check=lambda m, r: (group(m, "numerics")["budget_agent_hours"] == r["pre_group_budget"]["numerics"] + 100.0,
                             f"numerics.budget={group(m,'numerics')['budget_agent_hours']} pre={r['pre_group_budget']['numerics']}")),
    dict(id="F7", kind="unchecked_event", source="worker-024.jsonl",
         spec="PROTOCOL: direction_update comes from the group lead. apply_one has no actor check.",
         expected_patched="audit direction unchanged",
         events=[ev_dir("worker-024", "audit", "old", "UNAUTHORIZED-REWRITE", "direction probe",
                        event_id="f7-direction", delta=5.0)],
         check=lambda m, r: (group(m, "audit")["direction"] == "UNAUTHORIZED-REWRITE",
                             f"audit.direction={group(m,'audit')['direction']!r}")),
    dict(id="F8", kind="unchecked_event", source="worker-024.jsonl",
         spec="PROTOCOL: assignments are issued by Astra/leads. apply_one appends any actor's assignment.",
         expected_patched="assignment not appended",
         events=[ev_assign("worker-024", "F1", "worker-024", event_id="f8-self-assign")],
         check=lambda m, r: (any(a.get("event_id") == "f8-self-assign" for a in m["assignments"]),
                             f"assignment_present={any(a.get('event_id')=='f8-self-assign' for a in m['assignments'])}")),
    dict(id="F9", kind="status_scope", source="worker-024.jsonl",
         spec="A non-authority actor must not move a node out of a terminal state.",
         expected_patched="F1 stays done",
         pre=lambda m: node(m, "F1").update({"status": "done", "validation_status": "unverified",
                                             "evidence_refs": ["reviews/F1-review-088-rev12.json"]}),
         events=[ev_status("worker-024", "F1", "active", summary="unauthorized demotion",
                           event_id="f9-demote", class_ids=["AF-WCC-VAC-GEN"])],
         check=lambda m, r: (node(m, "F1")["status"] == "active", f"F1.status={node(m,'F1')['status']}")),
    dict(id="F10", kind="status_scope", source="worker-024.jsonl",
         spec="A worker may not set another agent's node to blocked/killed/rejected (no ownership check).",
         expected_patched="L0 status unchanged",
         events=[ev_status("worker-024", "L0", "blocked", summary="unauthorized block",
                           event_id="f10-block", class_ids=["AF-WCC-VAC-GEN"])],
         check=lambda m, r: (node(m, "L0")["status"] == "blocked", f"L0.status={node(m,'L0')['status']}")),
    dict(id="F11", kind="write_integrity", source="astra.jsonl",
         spec="apply_events computes validate_map(m) errors but writes the map unconditionally.",
         expected_patched="refuse write; exit nonzero; map_errors non-empty",
         pre=lambda m: m["groups"][0]["nodes"].append(copy.deepcopy(node(m, "F1"))),  # duplicate node id
         events=[ev_status("astra", "F2a", "active", summary="benign authority event on invalid map",
                           event_id="f11-invalid-map", class_ids=["AF-SCC-C2-VAC-GEN"])],
         check=lambda m, r: (bool(r["map_errors"]) and r["rc"] == 0
                             and node(m, "F2a").get("last_status", {}).get("summary") ==
                             "benign authority event on invalid map",
                             f"rc={r['rc']} map_errors={len(r['map_errors'])} "
                             f"f2a_last_status={node(m,'F2a').get('last_status',{}).get('summary')!r}")),
    dict(id="F12", kind="provenance", source="worker-024.jsonl",
         spec="A well-formed forged event leaves no source provenance: _source_file is only set when "
              "normalize_event fills a field, so an impersonation can be unattributable.",
         expected_patched="actor_claimed recorded and _source_file present",
         events=[ev_status("astra", "F2b", "done", summary="forged with canonical field spellings",
                           event_id="f12-no-provenance", evidence_refs=["schemas/af_scc_c0_vacuum.yaml"],
                           next_falsifier="unspecified")],
         check=lambda m, r: (not r["event_has_source_file"],
                             f"_source_file_present={r['event_has_source_file']}; actor_claimed={r['event_actor_claimed']}")),
    dict(id="F13", kind="write_integrity", source="astra.jsonl",
         spec="The only authority pathway to done is a status event, but apply_one never copies the "
              "event's evidence onto the node, so the promoted map fails validate_map "
              "('done node has no evidence_refs') and is still written.",
         expected_patched="refuse write; F1 stays active",
         events=[ev_status("astra", "F1", "done", summary="authority promotion without node evidence",
                           event_id="f13-done-invalid", evidence_refs=["reviews/F1-review-088-rev12.json"],
                           class_ids=["AF-WCC-VAC-GEN"])],
         check=lambda m, r: (node(m, "F1")["status"] == "done" and bool(r["map_errors"]) and r["rc"] == 0,
                             f"F1.status={node(m,'F1')['status']} map_errors={len(r['map_errors'])} rc={r['rc']}")),
    # ---- controls: guards that do work (expected no violation) and a happy path
    dict(id="C1", kind="control_guard", source="worker-024.jsonl",
         spec="Control: an undeclared worker actor cannot set done; the guard must keep working.",
         expected_patched="F1 not done; completion claim recorded",
         events=[ev_status("worker-024", "F1", "done", summary="raw worker done probe",
                           event_id="c1-raw-done", evidence_refs=["reviews/F1-review-088-rev12.json"],
                           class_ids=["AF-WCC-VAC-GEN"])],
         check=lambda m, r: (node(m, "F1")["status"] == "done", f"F1.status={node(m,'F1')['status']}")),
    dict(id="C2", kind="control_guard", source="worker-024.jsonl",
         spec="Control: an undeclared worker actor cannot set a gate verdict.",
         expected_patched="G-FORM stays pending; proposal recorded",
         events=[ev_gate("worker-024", "G-FORM", "pass", event_id="c2-raw-gate")],
         check=lambda m, r: (gate(m, "G-FORM")["verdict"] == "pass",
                             f"G-FORM.verdict={gate(m,'G-FORM')['verdict']}")),
    dict(id="C3", kind="control_guard", source="worker-024.jsonl",
         spec="Control: an undeclared worker actor cannot set validation_status=passed.",
         expected_patched="F1 stays unverified",
         events=[ev_artifact("worker-024", "F1", "schemas/af_wcc_vacuum.yaml",
                             PINS["sha256"]["schemas/af_wcc_vacuum.yaml"], "passed",
                             event_id="c3-raw-passed", class_ids=["AF-WCC-VAC-GEN"])],
         check=lambda m, r: (node(m, "F1").get("validation_status") == "passed",
                             f"F1.validation_status={node(m,'F1').get('validation_status')}")),
    dict(id="C4", kind="control_happy", source="astra.jsonl",
         spec="Control: the intended authority path (source file astra.jsonl, actor astra) must still work "
              "on a properly provisioned node (artifact on disk, node-level evidence_refs present).",
         expected_patched="F1 done",
         pre=lambda m: node(m, "F1").update({"evidence_refs": ["reviews/F1-review-088-rev12.json"]}),
         events=[ev_status("astra", "F1", "done", summary="authority happy path",
                           event_id="c4-auth-done", evidence_refs=["reviews/F1-review-088-rev12.json"],
                           class_ids=["AF-WCC-VAC-GEN"])],
         check=lambda m, r: (node(m, "F1")["status"] != "done", f"F1.status={node(m,'F1')['status']}")),
    dict(id="H1", kind="control_healthy", source=None,
         spec="Control: no events, canonical map: apply_events must run clean.",
         expected_patched="rc 0, no map errors, no demotions",
         events=[],
         check=lambda m, r: (r["rc"] != 0 or bool(r["map_errors"]) or bool(r["demoted"]),
                             f"rc={r['rc']} map_errors={len(r['map_errors'])} demoted={r['demoted']}")),
]

# ------------------------------------------------------------------ patched code
COMMS_PATCH_ANCHOR = """            accepted.append(doc)
            seen.add(eid)"""

COMMS_PATCH_NEW = """            # ---- W024 proposed authority binding (proposal only) --------------
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
            seen.add(eid)"""

COMMS_HEADER_PATCH = '''CST = timezone(timedelta(hours=8))

# W024 proposed: sources that may carry authority, and explicit non-canonical aliases.
KNOWN_AGENT = re.compile(r"^(astra|astra-lead-(formulation|literature|numerics|audit)|"
                         r"deepseek-flash-\\d{1,3}|worker-\\d{1,3})$")
SOURCE_ACTOR_ALIASES = {"lead-literature.events": "astra-lead-literature"}'''

APPLY_PATCH_ANCHOR = """AUTHORITY = {"astra", "lead-formulation", "lead-literature", "lead-numerics", "lead-audit",
             "astra-lead-formulation", "astra-lead-literature", "astra-lead-numerics", "astra-lead-audit"}"""

APPLY_PATCH_NEW = """AUTHORITY = {"astra", "lead-formulation", "lead-literature", "lead-numerics", "lead-audit",
             "astra-lead-formulation", "astra-lead-literature", "astra-lead-numerics", "astra-lead-audit"}


def _source_role(ev) -> str:
    src = str(ev.get("_source_file", ""))
    if not src:
        return ""
    name = Path(src).name
    if name.endswith(".jsonl"):
        return name[: -len(".jsonl")]
    return name.split(".")[0]


def is_authority(ev) -> bool:
    \"\"\"W024 proposed: authority requires actor in AUTHORITY, a source that backs it,
    and no declared/actual actor mismatch.\"\"\"
    actor = str(ev.get("actor", ""))
    if actor not in AUTHORITY:
        return False
    if ev.get("actor_claimed"):
        return False
    role = _source_role(ev)
    if not role:
        return False  # no provenance -> no authority
    if role == actor:
        return True
    return SOURCE_ACTOR_ALIASES.get(role) == actor


SOURCE_ACTOR_ALIASES = {"lead-literature.events": "astra-lead-literature"}"""


def build_patched(comms_src: str, apply_src: str):
    c = comms_src.replace(COMMS_HEADER_PATCH.split("\n\n", 1)[0] + "\n", COMMS_HEADER_PATCH + "\n", 1)
    assert c != comms_src, "comms header anchor not found"
    c2 = c.replace(COMMS_PATCH_ANCHOR, COMMS_PATCH_NEW, 1)
    assert c2 != c, "comms ingest anchor not found"
    a = apply_src.replace(APPLY_PATCH_ANCHOR, APPLY_PATCH_NEW, 1)
    assert a != apply_src, "apply HEADER anchor not found"

    # gate the decision matcher
    a2 = a.replace(
        '        if "resource_request" in summary and ("APPROVED" in summary or "DENIED" in summary):',
        '        if (is_authority(ev) and "resource_request" in summary\n'
        '                and ("APPROVED" in summary or "DENIED" in summary)):', 1)
    assert a2 != a, "rr anchor not found"
    # gate kill/revive, budget, direction_update, assignment
    a3 = a2.replace(
        '    elif t == "direction_update":\n        for g in m["groups"]:',
        '    elif t == "direction_update":\n'
        '        if not is_authority(ev):\n'
        '            m.setdefault("authority_proposals", []).append(\n'
        '                {**ev, "status": "unauthorized", "received_at": now()})\n'
        '            applied.append(eid); return\n'
        '        for g in m["groups"]:', 1)
    a4 = a3.replace(
        '    elif t == "budget":\n        for g in m["groups"]:',
        '    elif t == "budget":\n'
        '        if not is_authority(ev):\n'
        '            m.setdefault("authority_proposals", []).append(\n'
        '                {**ev, "status": "unauthorized", "received_at": now()})\n'
        '            applied.append(eid); return\n'
        '        for g in m["groups"]:', 1)
    a5 = a4.replace(
        '    elif t == "assignment":\n        known = {a.get("event_id") for a in m["assignments"]}',
        '    elif t == "assignment":\n'
        '        if not is_authority(ev):\n'
        '            m.setdefault("authority_proposals", []).append(\n'
        '                {**ev, "status": "unauthorized", "received_at": now()})\n'
        '            applied.append(eid); return\n'
        '        known = {a.get("event_id") for a in m["assignments"]}', 1)
    a6 = a5.replace(
        '    elif t in {"kill", "revive"}:\n        g, n = idx.get(ev["target_id"], (None, None))',
        '    elif t in {"kill", "revive"}:\n'
        '        if not is_authority(ev):\n'
        '            m.setdefault("authority_proposals", []).append(\n'
        '                {**ev, "status": "unauthorized", "received_at": now()})\n'
        '            applied.append(eid); return\n'
        '        g, n = idx.get(ev["target_id"], (None, None))', 1)
    assert a3 != a2 and a4 != a3 and a5 != a4 and a6 != a5, "unchecked-event anchors not found"
    # status: no non-authority movement; assignee-only progress; CF-25 preserved
    a7 = a6.replace(
        '''            if st == "done" and actor not in AUTHORITY:
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
                n["status"] = st''',
        '''            auth = is_authority(ev)
            assignee = any(x.get("node_id") == ev["node_id"] and x.get("assignee") == actor
                           for x in m.get("assignments", []))
            if not (auth or assignee):
                n.setdefault("status_proposals", []).append(
                    {"at": ev.get("created_at"), "by": actor, "proposed_status": st,
                     "reason": "actor is neither authority nor assignee (W024 authority binding)"})
                applied.append(eid); return
            if st == "done" and not auth:
                # a cheap agent may not promote; record the claim, keep the node honest
                n.setdefault("completion_claims", []).append(
                    {"at": ev.get("created_at"), "by": actor, "summary": ev.get("summary"),
                     "evidence_refs": ev.get("evidence_refs", [])})
                st = "active" if n.get("status") not in {"blocked", "killed", "done"} else n.get("status")
            # pass-05 controller repair (CF-25), retained: a node promoted to done on
            # artifact + review evidence is not demoted by a later worker status event.
            if n.get("status") == "done" and not auth:
                n.setdefault("status_events_ignored", []).append(
                    {"at": ev.get("created_at"), "by": actor, "rejected_status": st,
                     "reason": "node is done (promoted with artifact + review evidence); worker "
                               "status events cannot demote it"})
            elif n.get("status") in {"done", "killed"} and not auth and st != n.get("status"):
                n.setdefault("status_proposals", []).append(
                    {"at": ev.get("created_at"), "by": actor, "proposed_status": st,
                     "reason": "non-authority actor may not move a terminal node"})
            else:
                n["status"] = st''', 1)
    assert a7 != a6, "status authority anchor not found"
    # refuse to write an invalid map
    a8 = a7.replace(
        '''    errs = validate_map(m)
    if demoted:''',
        '''    errs = validate_map(m)
    if errs and not force:
        print(json.dumps({"refused": True, "reason": "map invalid; refusing to write",
                          "map_errors": errs[:20], "applied": len(applied),
                          "skipped": len(skipped), "events_total": len(events)}, indent=2))
        return {"refused": True, "map_errors": errs, "applied": len(applied),
                "skipped": len(skipped), "demoted": demoted, "events_total": len(events)}
    if demoted:''', 1)
    assert a8 != a7, "validate anchor not found"
    a9 = a8.replace("def main(dry_run=False):", "def main(dry_run=False, force=False):", 1)
    a10 = a9.replace('    ap.add_argument("--report", action="store_true")',
                     '    ap.add_argument("--report", action="store_true")\n'
                     '    ap.add_argument("--force", action="store_true")', 1)
    a11 = a10.replace("    main(dry_run=a.dry_run)",
                      "    rc = main(dry_run=a.dry_run, force=a.force)\n"
                      "    sys.exit(2 if isinstance(rc, dict) and rc.get(\"refused\") else 0)", 1)
    assert a11 != a10 and a9 != a8, "main signature anchors"
    return c2, a11


# ------------------------------------------------------------------- case runner
def run_case(case: dict, patched: bool) -> dict:
    reset_sandbox()
    if patched:
        shutil.copy2(PATCHDIR / "comms.py", SANDBOX / "research_map/comms.py")
        shutil.copy2(PATCHDIR / "apply_events.py", SANDBOX / "research_map/apply_events.py")
    # outbox
    if case["source"]:
        (SANDBOX / "comms/outbox" / case["source"]).write_text(
            "\n".join(json.dumps(e, sort_keys=True) for e in case["events"]) + "\n")
    # optional pre-state
    mpath = SANDBOX / "research_map/research_map.json"
    if case.get("pre"):
        m0 = load_map(mpath)
        case["pre"](m0)
        mpath.write_text(json.dumps(m0, indent=2) + "\n")
    m_pre = load_map(mpath)
    before = sha256(mpath)
    rec = {"id": case["id"], "kind": case["kind"], "source": case["source"],
           "spec_expected": case["spec"], "expected_patched": case["expected_patched"],
           "pre_group_budget": {g["id"]: g.get("budget_agent_hours") for g in m_pre["groups"]},
           "pre_direction": {g["id"]: g.get("direction") for g in m_pre["groups"]},
           "event_ids": [e["event_id"] for e in case["events"]]}
    # stage 1: ingest (real pipeline)
    ing = run([sys.executable, "research_map/comms.py", "ingest"])
    rec["ingest"] = {"rc": ing.returncode, "stdout": ing.stdout.strip()[-600:], "stderr": ing.stderr.strip()[-300:]}
    ev_path = SANDBOX / "research_map/events.jsonl"
    evs = [json.loads(l) for l in ev_path.read_text().splitlines() if l.strip()] if ev_path.exists() else []
    ev = next((e for e in evs if e["event_id"] == case["events"][0]["event_id"]), None) if case["events"] else None
    rec["event_accepted"] = ev is not None
    rec["event_actor"] = ev.get("actor") if ev else None
    rec["event_actor_claimed"] = (ev or {}).get("actor_claimed")
    rec["event_has_source_file"] = "_source_file" in (ev or {})
    rec["event_source_file"] = (ev or {}).get("_source_file")
    # stage 2: apply
    ap = run([sys.executable, "research_map/apply_events.py"])
    rec["rc"] = ap.returncode
    rec["apply_stdout"] = ap.stdout.strip()[-900:]
    try:
        out = json.loads(ap.stdout)
    except ValueError:
        out = {}
    rec["map_errors"] = out.get("map_errors", [])
    rec["demoted"] = out.get("demoted", [])
    rec["refused"] = out.get("refused", False)
    after = sha256(mpath)
    rec["map_sha_before"] = before
    rec["map_sha_after"] = after
    rec["map_written"] = before != after
    m = load_map(mpath)
    violated, observed = case["check"](m, rec)
    rec["observed"] = observed
    rec["violation"] = bool(violated)
    rec["harness_ok"] = rec["event_accepted"] or case["source"] is None
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-patched", action="store_true")
    a = ap.parse_args()

    pins = measure_pins()

    build_pristine()
    canonical = [run_case(c, patched=False) for c in CASES]
    # revision drift recheck: apply_events.py is a live file; if it moved during the
    # matrix, re-measure the same cases against the new bytes and report both pins.
    recheck_pins = measure_pins()
    drifted = recheck_pins["sha256"] != pins["sha256"]
    recheck = []
    if drifted:
        build_pristine()
        recheck = [run_case(c, patched=False) for c in CASES]

    patched_recs, patches = [], {}
    if not a.skip_patched:
        PATCHDIR.mkdir(parents=True, exist_ok=True)
        # build the proposal against the snapshotted bytes actually measured
        comms_src = (PRISTINE / "research_map/comms.py").read_text()
        apply_src = (PRISTINE / "research_map/apply_events.py").read_text()
        try:
            pc, pa = build_patched(comms_src, apply_src)
            (PATCHDIR / "comms.py").write_text(pc)
            (PATCHDIR / "apply_events.py").write_text(pa)
            diff = []
            for name, old, new in (("comms.py", comms_src, pc), ("apply_events.py", apply_src, pa)):
                diff += list(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                                  fromfile=f"a/research_map/{name}", tofile=f"b/research_map/{name}"))
            (BASE / "proposed_authority_patch.diff").write_text("".join(diff))
            patched_recs = [run_case(c, patched=True) for c in CASES]
            patches = {"verified": True,
                       "patch_base_apply_events_sha256": sha256(PRISTINE / "research_map/apply_events.py"),
                       "still_violated": [r["id"] for r in patched_recs
                                          if r["violation"] and not r["id"].startswith("C") and r["id"] != "H1"],
                       "controls_ok": all((not r["violation"]) for r in patched_recs
                                          if r["id"].startswith("C") or r["id"] == "H1"),
                       "harness_rejected": [r["id"] for r in patched_recs if not r["harness_ok"]]}
        except AssertionError as e:
            patches = {"verified": False, "error": f"patch anchors no longer match the live revision: {e}",
                       "note": "canonical measurement above is unaffected"}

    end_pins = {label: sha256(p) for label, p in PINNED.items()}
    pins_stable = end_pins == pins["sha256"]
    violations = [r["id"] for r in canonical if r["violation"]]
    controls = [r["id"] for r in canonical if r["id"].startswith("C") or r["id"] == "H1"]
    controls_fail = [r["id"] for r in canonical if r["id"] in controls and r["violation"]]
    prior = sorted(BASE.glob("report.rev-*.json"))
    rep = {
        "task_id": "W024-APPLY-EVENTS-AUTHORITY-01",
        "node_id": "A1", "gate": "G-AUDIT",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "actor": "worker-024", "created_at": now(),
        "pins": pins, "pins_stable": pins_stable, "end_pins": end_pins,
        "revision_drift_during_run": drifted,
        "drift_recheck_pins": recheck_pins if drifted else None,
        "drift_recheck": recheck,
        "drift_recheck_violations": [r["id"] for r in recheck if r["violation"]] if drifted else None,
        "prior_revision_reports": [{"path": str(p.relative_to(BASE)), "sha256": sha256(p)} for p in prior],
        "method": ("end-to-end: outbox file -> comms.py ingest -> events.jsonl -> apply_events.py -> sandbox map; "
                   "canonical tree never written; sandbox modules are byte-identical copies of the pinned revisions"),
        "canonical_revision": {"apply_events.py": pins["sha256"]["research_map/apply_events.py"],
                               "comms.py": pins["sha256"]["research_map/comms.py"],
                               "schemas.py": pins["sha256"]["research_map/schemas.py"],
                               "validate_map.py": pins["sha256"]["research_map/validate_map.py"],
                               "research_map.json": pins["sha256"]["research_map/research_map.json"]},
        "cases": canonical,
        "summary": {
            "cases": len(canonical), "authority_violations": violations,
            "violation_count": len(violations),
            "controls": controls, "controls_unexpected": controls_fail,
            "harness_rejected_events": [r["id"] for r in canonical if not r["harness_ok"]],
            "repaired_at_this_revision": ["F9"],
            "forged_authority_violations": [r["id"] for r in canonical if r["kind"] == "forged_authority" and r["violation"]],
            "unchecked_event_violations": [r["id"] for r in canonical if r["kind"] == "unchecked_event" and r["violation"]],
            "status_scope_violations": [r["id"] for r in canonical if r["kind"] == "status_scope" and r["violation"]],
            "write_integrity_violations": [r["id"] for r in canonical if r["kind"] == "write_integrity" and r["violation"]],
            "provenance_violations": [r["id"] for r in canonical if r["kind"] == "provenance" and r["violation"]],
        },
        "patched_run": patched_recs,
        "patch_verification": patches,
        "falsifier": ("Re-run drive_authority_matrix.py at research_map/apply_events.py#"
                      + pins["sha256"]["research_map/apply_events.py"][:12]
                      + " with a fresh sandbox: the claim is falsified if any listed case fails to reproduce "
                        "(no authority-state move) or if any control C1-C4/H1 deviates; patched claim is falsified "
                        "if any non-control case still violates or any control breaks."),
        "authority_note": ("worker report: no gate verdict, no node transition, no validation_status=passed, "
                           "no canonical file modified; patch is a proposal verified on sandbox copies only"),
    }
    (BASE / "report.json").write_text(json.dumps(rep, indent=2) + "\n")
    print(json.dumps({"violations": violations, "controls_unexpected": controls_fail,
                      "harness_rejected": rep["summary"]["harness_rejected_events"],
                      "pins_stable": pins_stable, "drifted": drifted,
                      "drift_recheck_violations": rep["drift_recheck_violations"],
                      "patched": patches,
                      "still_violated_patched": patches.get("still_violated")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
