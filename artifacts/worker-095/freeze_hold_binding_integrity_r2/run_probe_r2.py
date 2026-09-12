#!/usr/bin/env python3
"""W095-HOLD-BIND-INTEGRITY-04 — pass-05 re-probe of the FROZEN rev28 freeze-hold.

Class-bound task: node F2b, class AF-SCC-C0-VAC-GEN, gate G-FORM.
Re-tests the falsifier stated in W095-HOLD-BIND-INTEGRITY-03 (pass-04, 00:42:09):
  (a) newest-by-created_at artifact event for every held path carries the rev28 pin,
  (b) all five held paths still measure their rev28 pins with zero drift,
  (c) F2b's declared consistency-evidence hash resolves on its declared canonical path.

Read-only with respect to canonical inputs. Writes only under
artifacts/worker-095/freeze_hold_binding_integrity_r2/ and (with --emit)
appends protocol events + a worker checkpoint. Idempotent on event_id.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TASK_ID = "W095-HOLD-BIND-INTEGRITY-04"
WORKER = "worker-095"
NODE_ID = "F2b"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
GATE = "G-FORM"
REVIEWED_REVISION = 12
REVIEWED_SHA = "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"
FROZEN_REVISION = 28
RAW = HERE / "evidence" / "raw"
OUTBOX = ROOT / "comms" / "outbox" / f"{WORKER}.jsonl"
STATE = ROOT / "runtime" / "state"
EVENTS = ROOT / "research_map" / "events.jsonl"
FROZEN_PATH = "artifacts/formulation/FROZEN.json"
F2B_PATH = "schemas/af_scc_c0_vacuum.yaml"
CONSISTENCY_PATH = "artifacts/formulation/evidence/taxonomy_consistency.json"
PRIOR_VERDICT_PATH = "artifacts/worker-095/freeze_hold_binding_integrity/verdict.json"
HELD = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
]
HELD_ROLE = {
    "schemas/af_wcc_vacuum.yaml": "class_schema WCC (F1)",
    "schemas/af_scc_c2_vacuum.yaml": "class_schema SCC-C2 (F2a)",
    "schemas/af_scc_c0_vacuum.yaml": "class_schema SCC-C0 (F2b)",
    "research_map/formulation_taxonomy.yaml": "declared F0 taxonomy",
    "artifacts/formulation/formulation_taxonomy.yaml": "F0 class-contract supplement",
}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def measure(rel: str) -> dict:
    p = ROOT / rel
    h = sha256_file(p)
    out = {"path": rel, "sha256": h, "exists": h is not None}
    if h is not None:
        st = p.stat()
        out["bytes"] = st.st_size
        out["mtime"] = datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(timespec="seconds")
    return out


def write_json(rel_to_here: Path, obj: dict) -> str:
    rel_to_here.parent.mkdir(parents=True, exist_ok=True)
    rel_to_here.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    return sha256_file(rel_to_here)


def find_hash_refs(obj, needle: str, prefix: str = "", out=None, limit: int = 30) -> list:
    if out is None:
        out = []
    if len(out) >= limit:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            find_hash_refs(v, needle, f"{prefix}.{k}" if prefix else str(k), out, limit)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            find_hash_refs(v, needle, f"{prefix}[{i}]", out, limit)
    elif isinstance(obj, str) and needle in obj:
        out.append({"json_path": prefix, "value": obj[:160]})
    return out


def load_events() -> list[dict]:
    rows = []
    for line in EVENTS.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def event_paths(d: dict) -> list[str]:
    vals = []
    for key in ("path", "artifact"):
        v = d.get(key)
        if isinstance(v, str):
            vals.append(v)
        elif isinstance(v, list):
            vals.extend([x for x in v if isinstance(x, str)])
    return vals


def probe() -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    probe_at = now_iso()
    report: dict = {"probe": TASK_ID, "probe_at": probe_at, "class_id": CLASS_ID,
                    "node_id": NODE_ID, "gate": GATE, "checks": [], "findings": []}

    # ---------- R1: pin match ----------
    frozen = json.loads((ROOT / FROZEN_PATH).read_text())
    frozen_files = frozen.get("files", {})
    r1_rows = []
    for rel in HELD:
        meas = measure(rel)
        pin = frozen_files.get(rel, {}).get("sha256")
        r1_rows.append({
            "id": f"R1-{Path(rel).name}", "path": rel, "role": HELD_ROLE[rel],
            "measured": meas["sha256"], "frozen_pin": pin,
            "pin_in_manifest": rel in frozen_files, "match": bool(pin) and meas["sha256"] == pin,
        })
    r1_pass = all(r["match"] for r in r1_rows)
    report["checks"].append({"id": "R1-PIN-MATCH", "severity": "hard", "status": "PASS" if r1_pass else "FAIL",
                             "detail": r1_rows})

    # ---------- R2: FROZEN manifest self-consistency ----------
    frozen_meas = measure(FROZEN_PATH)
    frozen_prefix = (frozen_meas["sha256"] or "")[:12]
    map_obj = json.loads((ROOT / "research_map/research_map.json").read_text())
    map_sha = sha256_file(ROOT / "research_map/research_map.json")
    reg = json.loads((ROOT / "runtime/state/artifact_hashes.json").read_text())
    reg_blob = json.dumps(reg)
    map_refs = find_hash_refs(map_obj, frozen_prefix)
    r2_pass = bool(
        frozen_prefix
        and frozen.get("revision") == FROZEN_REVISION
        and all(rel in frozen_files for rel in HELD)
        and map_refs
    )
    report["checks"].append({
        "id": "R2-MANIFEST-SELF", "severity": "hard", "status": "PASS" if r2_pass else "FAIL",
        "detail": {
            "frozen_revision": frozen.get("revision"), "frozen_at": frozen.get("frozen_at"),
            "frozen_measured": frozen_meas, "declared_refs_in_map": map_refs,
            "registry_has_frozen": FROZEN_PATH in reg.get("registry", {}),
            "frozen_prefix_in_registry": frozen_prefix in reg_blob,
        },
    })

    # ---------- R3: event-stream shadow re-test (falsifier condition (a)) ----------
    events = load_events()
    event_stream_sha = sha256_file(EVENTS)
    r3_rows = []
    shadowed = []
    for rel in HELD:
        pin = frozen_files.get(rel, {}).get("sha256")
        hits = [(i, d) for i, d in enumerate(events)
                if d.get("event_type") == "artifact" and rel in event_paths(d)]
        if not hits:
            r3_rows.append({"path": rel, "events": 0, "stream_newest": None,
                            "created_newest": None, "shadowed": None, "note": "no artifact events"})
            continue
        stream_i, stream_ev = hits[-1]
        created_i, created_ev = sorted(
            hits, key=lambda t: (str(t[1].get("created_at", "")), t[0]))[-1]

        def brief(t):
            i, d = t
            return {"stream_index": i, "event_id": d.get("event_id"), "created_at": d.get("created_at"),
                    "received_at": d.get("_received_at"), "sha256": d.get("sha256"),
                    "actor": d.get("actor"), "matches_pin": d.get("sha256") == pin}

        stale_newer = [
            {"event_id": d.get("event_id"), "created_at": d.get("created_at"),
             "received_at": d.get("_received_at"), "sha256": d.get("sha256")}
            for i, d in hits
            if str(d.get("created_at", "")) > str(stream_ev.get("created_at", "")) and d.get("sha256") != pin
        ]
        is_shadow = bool(created_ev.get("sha256") != pin)
        if is_shadow:
            shadowed.append(rel)
        r3_rows.append({
            "path": rel, "events": len(hits), "frozen_pin": pin,
            "stream_newest": brief((stream_i, stream_ev)),
            "created_newest": brief((created_i, created_ev)),
            "shadowed": is_shadow, "stale_events_newer_than_pin_event": stale_newer,
        })
    r3_pass = not shadowed
    report["checks"].append({
        "id": "R3-EVENT-SHADOW", "severity": "hard", "status": "PASS" if r3_pass else "FAIL",
        "detail": {"held_paths_shadowed": shadowed, "rows": r3_rows,
                   "event_stream_events": len(events), "event_stream_sha256": event_stream_sha,
                   "tombstone_or_supersede_event_types_present": any(
                       d.get("event_type") in ("tombstone", "supersede") for d in events)},
    })

    # ---------- R4: declared consistency-evidence resolution (falsifier condition (c)) ----------
    import yaml  # noqa: E402  (PyYAML available; schema is YAML)

    f2b = yaml.safe_load((ROOT / F2B_PATH).read_text())
    binding = (f2b or {}).get("f0_binding", {}) or {}
    declared_hash = binding.get("consistency_evidence_sha256")
    declared_path = binding.get("consistency_evidence")
    declared_meas = measure(declared_path) if declared_path else None
    reg_has_declared = bool(declared_hash) and declared_hash in reg_blob
    pin_meas = measure(CONSISTENCY_PATH)
    # where else does the declared hash resolve? (bounded scan of the known pinned dir + top-level search)
    alt_resolutions = []
    pinned_dir = ROOT / "artifacts/worker-086/gform_rev12/pinned"
    if pinned_dir.is_dir():
        for p in sorted(pinned_dir.glob("*")):
            h = sha256_file(p)
            if h == declared_hash:
                alt_resolutions.append({"path": str(p.relative_to(ROOT)), "sha256": h})
    declared_prefix = (declared_hash or "")[:12]
    map_decl_refs = find_hash_refs(map_obj, declared_prefix) if declared_prefix else []
    pinned_prefix = (pin_meas.get("sha256") or "")[:12]
    map_pin_refs = find_hash_refs(map_obj, pinned_prefix) if pinned_prefix else []
    r4_pass = bool(declared_path and declared_meas and declared_hash
                   and declared_meas.get("sha256") == declared_hash)
    report["checks"].append({
        "id": "R4-DECLARED-EVIDENCE-RESOLUTION", "severity": "hard",
        "status": "PASS" if r4_pass else "FAIL",
        "detail": {
            "declared_path": declared_path, "declared_sha256": declared_hash,
            "declared_path_measured": declared_meas,
            "declared_path_matches_declaration": r4_pass,
            "declared_hash_resolves_at": alt_resolutions,
            "declared_hash_in_registry": reg_has_declared,
            "declared_hash_refs_in_map": map_decl_refs,
            "frozen_consistency_evidence": pin_meas,
            "frozen_pin_refs_in_map": map_pin_refs,
            "declared_f0_sha256": binding.get("declared_f0_sha256"),
            "declared_f0_measured": measure(binding.get("declared_f0_artifact", "")),
            "binding_checked_at": binding.get("checked_at"),
        },
    })

    # ---------- R5: gate coverage context (informational) ----------
    gate_audit = (map_obj.get("controller_gate_audit", {}) or {}).get(GATE, {})
    accepts = []
    for rv in map_obj.get("reviews", []) or []:
        if not isinstance(rv, dict):
            continue
        tgt = rv.get("target_id") or rv.get("target")
        if rv.get("verdict") == "accept" and (
                tgt in (F2B_PATH, NODE_ID) or rv.get("node_id") == NODE_ID):
            accepts.append({"reviewer": rv.get("reviewer"), "target_id": tgt,
                            "checked_at": rv.get("checked_at") or rv.get("created_at"),
                            "artifact_sha256": rv.get("artifact_sha256")})
    report["checks"].append({
        "id": "R5-GATE-COVERAGE-CONTEXT", "severity": "info", "status": "INFO",
        "detail": {"map_sha256": map_sha, "map_updated_at": map_obj.get("updated_at"),
                   "gate_audit_checked_at": gate_audit.get("checked_at"),
                   "gate_audit_reason": gate_audit.get("reason"),
                   "f2b_accepts_in_map": accepts},
    })

    # ---------- R6: no drift during probe ----------
    r6_rows = []
    for rel in HELD + [FROZEN_PATH]:
        after = measure(rel)
        r6_rows.append({"path": rel, "sha256": after["sha256"]})
    r6_pass = all(
        after["sha256"] == (frozen_files.get(r["path"], {}).get("sha256") if r["path"] != FROZEN_PATH else frozen_meas["sha256"])
        for after, r in zip(r6_rows, [{"path": p} for p in HELD] + [{"path": FROZEN_PATH}])
    )
    report["checks"].append({"id": "R6-NO-PROBE-DRIFT", "severity": "hard",
                             "status": "PASS" if r6_pass else "FAIL", "detail": r6_rows})

    # ---------- findings ----------
    if not r1_pass:
        report["findings"].append({"id": "W095R2-HF-1", "severity": "hard",
                                   "finding": "A held path no longer measures its FROZEN rev28 pin."})
    if shadowed:
        report["findings"].append({
            "id": "W095R2-HF-2", "severity": "hard",
            "finding": (f"Event-stream shadow persists at pass-05: for {len(shadowed)} of 5 held paths the "
                        f"newest artifact event by created_at is a stale submission, not the rev28 pin event. "
                        f"Shadowed: {', '.join(shadowed)}. No tombstone/supersede event type exists in the "
                        f"accepted stream, so the shadow cannot be cleared by an event."),
            "evidence": "evidence/raw/event_stream_slice_r2.json#event_rows"})
    if not r4_pass:
        report["findings"].append({
            "id": "W095R2-HF-3", "severity": "hard",
            "finding": (f"F2b f0_binding declares consistency_evidence_sha256 {str(declared_hash)[:12]} on path "
                        f"{declared_path}, but that path measures {str(pin_meas.get('sha256'))[:12]}. The declared "
                        f"hash resolves only at a reconstruction outside the declared path "
                        f"({', '.join(a['path'] for a in alt_resolutions) or 'nowhere'}). "
                        f"Declaration, path and bytes do not agree."),
            "evidence": "evidence/raw/f2b_declaration_r2.json#f0_binding"})
    if r1_pass and r6_pass:
        report["findings"].append({"id": "W095R2-P-1", "severity": "positive",
                                   "finding": "Byte-level hold intact: all five held paths and FROZEN.json measured "
                                              "their rev28 pins before and after the probe (zero drift)."})

    if not r1_pass or not r6_pass:
        verdict, score = "reject", 1
    elif shadowed or not r4_pass:
        verdict, score = "revise", 3
    else:
        verdict, score = "accept", 4
    report["verdict"] = verdict
    report["score_0_5"] = score

    # ---------- raw evidence files ----------
    write_json(RAW / "held_path_hashes_r2.json", {
        "probe": TASK_ID, "probe_at": probe_at, "frozen_revision": FROZEN_REVISION,
        "frozen_at": frozen.get("frozen_at"), "frozen_measured": frozen_meas, "paths": r1_rows})
    write_json(RAW / "event_stream_slice_r2.json", {
        "probe": TASK_ID, "probe_at": probe_at, "event_stream_sha256": event_stream_sha,
        "events_total": len(events), "held_paths_shadowed": shadowed, "event_rows": r3_rows})
    write_json(RAW / "f2b_declaration_r2.json", {
        "probe": TASK_ID, "probe_at": probe_at, "schema": F2B_PATH,
        "schema_measured": measure(F2B_PATH), "f0_binding": binding,
        "declared_path_measured": declared_meas,
        "declared_hash_resolves_at": alt_resolutions})
    write_json(RAW / "map_gate_slice_r2.json", {
        "probe": TASK_ID, "probe_at": probe_at, "map_sha256": map_sha,
        "map_updated_at": map_obj.get("updated_at"), "gate": GATE,
        "gate_audit": gate_audit, "f2b_accepts": accepts,
        "frozen_prefix_refs": map_refs, "declared_hash_refs": map_decl_refs,
        "frozen_consistency_evidence_refs": map_pin_refs})
    write_json(RAW / "probe_report_r2.json", report)

    # evidence refs (hash the raw files just written)
    ev = {name: sha256_file(RAW / name) for name in
          ("held_path_hashes_r2.json", "event_stream_slice_r2.json", "f2b_declaration_r2.json",
           "map_gate_slice_r2.json", "probe_report_r2.json")}
    script_sha = sha256_file(Path(__file__))
    prior_sha = sha256_file(ROOT / PRIOR_VERDICT_PATH)
    evidence_refs = [f"{PRIOR_VERDICT_PATH}#{(prior_sha or '')[:12]}"]
    for name, h in ev.items():
        evidence_refs.append(f"artifacts/worker-095/freeze_hold_binding_integrity_r2/evidence/raw/{name}#{(h or '')[:12]}")
    evidence_refs += [
        f"{FROZEN_PATH}#{(frozen_meas['sha256'] or '')[:12]}",
        f"{F2B_PATH}#{REVIEWED_SHA[:12]}",
        f"{CONSISTENCY_PATH}#{(pin_meas.get('sha256') or '')[:12]}",
    ]
    evidence_refs += [f"{a['path']}#{a['sha256'][:12]}" for a in alt_resolutions]
    # Live append-only files (research_map.json, events.jsonl) are deliberately NOT cited by
    # hash here: they move as traffic lands, so a live hash prefix would not re-resolve. Their
    # measured-at-probe hashes are carried inside the immutable raw slices above.

    next_falsifier = (
        "A re-probe in which (a) for every held path the newest artifact event by created_at carries the "
        "FROZEN rev28 pin sha256, and (b) F2b f0_binding.consistency_evidence_sha256 equals the measured "
        "sha256 of the path it names, with (c) all five pins and FROZEN.json still drift-free. "
        "Condition (b) is met either by refreshing the declaration to the live path hash or by moving the "
        "live evidence to the declared bytes; the declared hash resolving only at a reconstruction does not satisfy it."
    )
    verdict_obj = {
        "task_id": TASK_ID, "worker": WORKER, "node_id": NODE_ID, "class_id": CLASS_ID, "gate": GATE,
        "probe_at": probe_at, "reviewed_revision": REVIEWED_REVISION, "reviewed_sha256": REVIEWED_SHA,
        "frozen_revision_reviewed": FROZEN_REVISION,
        "verdict": verdict, "score_0_5": score, "counts_as_full_schema_verdict": False,
        "scope_note": ("Binding-integrity re-probe of the rev28 freeze-hold at map "
                       f"{(map_sha or '')[:12]}; not an adjudication of F2b schema content (see "
                       "reviews/F2b-f0-binding-077.json for content hard findings)."),
        "checks": report["checks"], "findings": report["findings"],
        "evidence_refs": evidence_refs, "next_falsifier": next_falsifier,
        "artifact": "artifacts/worker-095/freeze_hold_binding_integrity_r2/verdict.json",
        "probe_script": {"path": "artifacts/worker-095/freeze_hold_binding_integrity_r2/run_probe_r2.py",
                         "sha256": script_sha},
    }
    verdict_sha = write_json(HERE / "verdict.json", verdict_obj)
    verdict_obj["_verdict_sha256"] = verdict_sha
    report["verdict_sha256"] = verdict_sha

    readme = f"""# W095-HOLD-BIND-INTEGRITY-04 (pass-05 re-probe)

Class-bound task: node `F2b`, class `AF-SCC-C0-VAC-GEN`, gate `G-FORM`.
Re-tests the falsifier of W095-HOLD-BIND-INTEGRITY-03 at map `{(map_sha or '')[:12]}` (updated {map_obj.get('updated_at')}).

Verdict: **{verdict}** (score {score}/5). `counts_as_full_schema_verdict=false`.

- R1 pin match: {'PASS' if r1_pass else 'FAIL'} (all five held paths at FROZEN rev28 pins)
- R2 manifest self: {'PASS' if r2_pass else 'FAIL'} (FROZEN.json measured {(frozen_meas['sha256'] or '')[:12]})
- R3 event shadow: {'PASS' if r3_pass else 'FAIL'} (shadowed: {', '.join(shadowed) or 'none'})
- R4 declared evidence resolution: {'PASS' if r4_pass else 'FAIL'} (declared {str(declared_hash)[:12]} vs measured {(pin_meas.get('sha256') or '')[:12]})
- R5 gate coverage: info (see evidence/raw/map_gate_slice_r2.json)
- R6 no probe drift: {'PASS' if r6_pass else 'FAIL'}

Raw evidence: `evidence/raw/`. Reproduce: `python3 run_probe_r2.py` (append `--emit`
to re-emit outbox events/checkpoint; event_ids are idempotent).
"""
    (HERE / "README.md").write_text(readme)

    report["_evidence_hashes"] = ev
    report["_verdict_sha256"] = verdict_sha
    report["_script_sha256"] = script_sha
    report["_evidence_refs"] = evidence_refs
    next_falsifier = next_falsifier
    return report


def emit() -> dict:
    report = json.loads((RAW / "probe_report_r2.json").read_text())
    verdict_obj = json.loads((HERE / "verdict.json").read_text())
    ts = report["probe_at"]
    stamp = datetime.fromisoformat(ts).strftime("%Y%m%dT%H%M%S")
    verdict_sha = sha256_file(HERE / "verdict.json")
    script_sha = sha256_file(Path(__file__))
    refs = verdict_obj["evidence_refs"]
    next_falsifier = verdict_obj["next_falsifier"]
    verdict = report["verdict"]
    score = report["score_0_5"]
    shadow_row = next(c for c in report["checks"] if c["id"] == "R3-EVENT-SHADOW")
    shadowed = shadow_row["detail"]["held_paths_shadowed"]
    r4 = next(c for c in report["checks"] if c["id"] == "R4-DECLARED-EVIDENCE-RESOLUTION")["detail"]
    r1 = next(c for c in report["checks"] if c["id"] == "R1-PIN-MATCH")
    map_sha12 = (next(c for c in report["checks"]
                      if c["id"] == "R5-GATE-COVERAGE-CONTEXT")["detail"].get("map_sha256") or "")[:12]
    hard_failures = [f["id"] for f in report["findings"] if f["severity"] == "hard"]

    events = [
        {"event_id": f"w095-hold-r2-{stamp}-task-claim", "event_type": "status", "actor": WORKER,
         "created_at": ts, "node_id": NODE_ID, "gate": GATE, "class_id": CLASS_ID,
         "status": "active", "hours": 0.3,
         "summary": (f"{TASK_ID}: pass-05 re-probe of the FROZEN rev28 freeze-hold at map "
                     f"{map_sha12} (binding-integrity scope, not a full schema verdict)."),
         "evidence_refs": refs, "next_falsifier": next_falsifier},
        {"event_id": f"w095-hold-r2-{stamp}-artifact-verdict", "event_type": "artifact", "actor": WORKER,
         "created_at": ts, "node_id": NODE_ID, "class_id": CLASS_ID,
         "artifact_type": "hold_binding_integrity_reprobe_verdict",
         "path": "artifacts/worker-095/freeze_hold_binding_integrity_r2/verdict.json",
         "sha256": verdict_sha, "validation_status": "unverified",
         "reviewed_revision": REVIEWED_REVISION, "reviewed_sha256": REVIEWED_SHA,
         "frozen_revision_reviewed": FROZEN_REVISION,
         "companion_script": {"path": "artifacts/worker-095/freeze_hold_binding_integrity_r2/run_probe_r2.py",
                              "sha256": script_sha},
         "evidence_refs": refs},
        {"event_id": f"w095-hold-r2-{stamp}-review-binding", "event_type": "review", "actor": WORKER,
         "created_at": ts, "target_id": F2B_PATH, "reviewer": WORKER, "node_id": NODE_ID,
         "class_id": CLASS_ID, "gate": GATE, "verdict": verdict, "score": score,
         "artifact_sha256": REVIEWED_SHA, "frozen_revision_reviewed": FROZEN_REVISION,
         "hard_failures": hard_failures,
         "findings": [{"id": f["id"], "severity": f["severity"], "finding": f["finding"]}
                      for f in report["findings"]],
         "summary": (f"Binding-integrity re-probe at rev12/FROZEN rev28: R1 pin match "
                     f"{r1['status']}, R3 event shadow {shadow_row['status']} "
                     f"({len(shadowed)}/5 held paths shadowed), R4 declared evidence resolution "
                     f"{next(c for c in report['checks'] if c['id'] == 'R4-DECLARED-EVIDENCE-RESOLUTION')['status']}."),
         "next_falsifier": next_falsifier, "evidence_refs": refs},
        {"event_id": f"w095-hold-r2-{stamp}-blocker-evidence-resolution", "event_type": "blocker", "actor": WORKER,
         "created_at": ts, "node_id": NODE_ID, "gate": GATE, "class_id": CLASS_ID,
         "description": (f"Two evidence-resolution defects persist at pass-05. (1) Event-stream shadow: "
                         f"{len(shadowed)}/5 held paths have a stale future-dated artifact event that sorts newest "
                         f"by created_at ahead of the rev28 pin event ({', '.join(shadowed)}); the accepted stream "
                         f"has no tombstone/supersede event type, so resolution-by-created_at still binds stale "
                         f"bytes. (2) F2b f0_binding declares consistency_evidence_sha256 "
                         f"{str(r4.get('declared_sha256'))[:12]} on {r4.get('declared_path')}, but that path "
                         f"measures {str((r4.get('declared_path_measured') or {}).get('sha256'))[:12]}; the declared "
                         f"hash resolves only at a reconstruction outside the declared path. Byte-level hold is "
                         f"intact ({r1['status']}), so this is a resolution/declaration defect, not a FROZEN breach."),
         "needed_to_unblock": ("(a) rank artifact events by ingest/_received_at order (or reject created_at > "
                               "_received_at) when resolving 'latest' per path, and/or emit tombstone/supersede "
                               "events for the stale submissions; (b) refresh F2b f0_binding to the measured live "
                               "path hash (or move the live evidence to the declared bytes) and register the "
                               "consistency evidence in runtime/state/artifact_hashes.json. No canonical byte edit "
                               "is requested; the hold stays in force."),
         "evidence_refs": refs},
        {"event_id": f"w095-hold-r2-{stamp}-task-receipt-complete", "event_type": "status", "actor": WORKER,
         "created_at": ts, "node_id": NODE_ID, "gate": GATE, "class_id": CLASS_ID,
         "status": "active", "hours": 0.3,
         "summary": (f"{TASK_ID} worker-level receipt complete; node status deliberately unchanged (worker events "
                     f"cannot set status=done, validation_status=passed, or a gate verdict). "
                     f"verdict={verdict} at F2b rev12 {REVIEWED_SHA[:12]} / FROZEN rev28; "
                     f"artifact + 5 raw evidence files + checkpoint written. counts_as_full_schema_verdict=false."),
         "evidence_refs": refs, "next_falsifier": next_falsifier},
    ]

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            try:
                existing.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                continue

    # Reject own output before sending (PROTOCOL rule 5): required fields per event type.
    required = {
        "artifact": ["node_id", "artifact_type", "path", "sha256", "validation_status"],
        "review": ["target_id", "reviewer", "verdict", "score", "hard_failures", "findings"],
    }
    base = ["event_id", "event_type", "created_at", "actor"]
    for ev in events:
        missing = [k for k in base + required.get(ev["event_type"], []) if k not in ev]
        if missing:
            raise SystemExit(f"refusing to emit malformed event {ev.get('event_id')}: missing {missing}")
        if ev["event_id"] in existing:
            continue
    known_ids = {ev["event_id"] for ev in events}
    if len(known_ids) != len(events):
        raise SystemExit("duplicate event_id inside emission batch")

    appended = 0
    with OUTBOX.open("a") as fh:
        for ev in events:
            if ev["event_id"] in existing:
                continue
            fh.write(json.dumps(ev, sort_keys=True) + "\n")
            appended += 1

    ckpt = {
        "worker": WORKER, "task_id": TASK_ID, "checkpoint_at": ts, "class_id": CLASS_ID,
        "node_id": NODE_ID, "gate": GATE, "reviewed_revision": REVIEWED_REVISION,
        "reviewed_sha256": REVIEWED_SHA, "frozen_revision_reviewed": FROZEN_REVISION,
        "artifact": "artifacts/worker-095/freeze_hold_binding_integrity_r2/verdict.json",
        "artifact_sha256": verdict_sha,
        "evidence_dir": "artifacts/worker-095/freeze_hold_binding_integrity_r2/evidence/raw/",
        "probe": {"path": "artifacts/worker-095/freeze_hold_binding_integrity_r2/run_probe_r2.py",
                  "sha256": script_sha},
        "verdict": verdict, "score_0_5": score, "counts_as_full_schema_verdict": False,
        "next_falsifier": next_falsifier,
    }
    ck_path = STATE / f"w095_hold_binding_integrity_r2_checkpoint_{stamp}.json"
    ck_path.write_text(json.dumps(ckpt, indent=2, sort_keys=True) + "\n")
    with (STATE / "w095_hold_binding_integrity_r2_checkpoints.jsonl").open("a") as fh:
        fh.write(json.dumps(ckpt, sort_keys=True) + "\n")
    return {"events_appended": appended, "checkpoint": str(ck_path.relative_to(ROOT))}


if __name__ == "__main__":
    rep = probe()
    print(json.dumps({"probe": TASK_ID, "verdict": rep["verdict"], "score": rep["score_0_5"],
                      "checks": {c["id"]: c["status"] for c in rep["checks"]},
                      "findings": [f["id"] for f in rep["findings"]],
                      "verdict_sha256": rep["_verdict_sha256"]}, indent=2))
    if "--emit" in sys.argv:
        print(json.dumps(emit(), indent=2))
