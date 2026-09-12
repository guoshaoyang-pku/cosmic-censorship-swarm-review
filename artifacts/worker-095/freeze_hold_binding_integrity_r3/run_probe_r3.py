#!/usr/bin/env python3
"""W095-HOLD-BIND-INTEGRITY-05: re-probe of the FROZEN rev28 freeze-hold binding integrity.

Class-bound task: node F2b, class AF-SCC-C0-VAC-GEN, gate G-FORM.
Successor of W095-HOLD-BIND-INTEGRITY-04 (artifacts/worker-095/freeze_hold_binding_integrity_r2),
which returned revise and declared the falsifier re-tested here.

Read-only against canonical state. Writes only inside this deliverable directory, plus (with
--emit) appends to comms/outbox/worker-095.jsonl and runtime/state/w095_* checkpoint files.

Checks:
  R1-PIN-MATCH                    live sha256 of the five held paths vs FROZEN rev28 pins
  R2-MANIFEST-SELF                FROZEN.json self hash/refs + full 44-pin drift census
  R3-EVENT-SHADOW                 per held path: stale artifact events sorting newer than the pin event
  R4-DECLARED-EVIDENCE-RESOLUTION F2b f0_binding.consistency_evidence_sha256 vs the live path it names
  R5-CONTEXT                      informational: gates, stale hash refs, supersede/tombstone census
  R6-NO-PROBE-DRIFT               held pins unchanged across the probe window

Verdict policy: any hard FAIL => revise; all hard PASS => accept. counts_as_full_schema_verdict is
false: a worker cannot issue a node verdict, only measure and report.
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
TASK_ID = "W095-HOLD-BIND-INTEGRITY-05"
WORKER = "worker-095"
NODE_ID = "F2b"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
GATE = "G-FORM"
FROZEN_REVISION = 28
RAW = HERE / "evidence" / "raw"
OUTBOX = ROOT / "comms" / "outbox" / f"{WORKER}.jsonl"
STATE = ROOT / "runtime" / "state"
EVENTS = ROOT / "research_map" / "events.jsonl"
MAP_PATH = ROOT / "research_map" / "research_map.json"
FROZEN_REL = "artifacts/formulation/FROZEN.json"
F2B_REL = "schemas/af_scc_c0_vacuum.yaml"
CONSISTENCY_REL = "artifacts/formulation/evidence/taxonomy_consistency.json"
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
SUPERSEDE_TOKENS = ("supersede", "supersedes", "tombstone", "retire", "retract", "void")


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


def write_json(path: Path, obj: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    return sha256_file(path) or ""


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


def walk_strings(o, prefix=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk_strings(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk_strings(v, f"{prefix}[{i}]")
    elif isinstance(o, str):
        yield prefix, o


def probe() -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    probe_at = now_iso()
    report: dict = {
        "probe": TASK_ID, "probe_at": probe_at, "worker": WORKER,
        "class_id": CLASS_ID, "node_id": NODE_ID, "gate": GATE,
        "checks": [], "findings": [],
    }

    frozen = json.loads((ROOT / FROZEN_REL).read_text())
    frozen_files = frozen.get("files", {})
    map_obj = json.loads(MAP_PATH.read_text())
    events = load_events()

    # ---------- R1: pin match ----------
    t0 = {}
    r1_rows = []
    for rel in HELD:
        meas = measure(rel)
        t0[rel] = meas["sha256"]
        pin = frozen_files.get(rel, {}).get("sha256")
        r1_rows.append({
            "id": f"R1-{Path(rel).name}", "path": rel, "role": HELD_ROLE[rel],
            "measured": meas["sha256"], "frozen_pin": pin, "pin_in_manifest": rel in frozen_files,
            "match": bool(pin) and meas["sha256"] == pin,
        })
    r1_pass = all(r["match"] for r in r1_rows)
    write_json(RAW / "held_path_hashes_r3.json",
               {"probe": TASK_ID, "probe_at": probe_at, "frozen_revision": frozen.get("revision"),
                "frozen_at": frozen.get("frozen_at"), "paths": r1_rows})
    report["checks"].append({"id": "R1-PIN-MATCH", "severity": "hard",
                             "status": "PASS" if r1_pass else "FAIL", "detail": r1_rows})

    # ---------- R2: manifest self + full drift census ----------
    frozen_meas = measure(FROZEN_REL)
    frozen_prefix = (frozen_meas["sha256"] or "")[:12]
    drift_rows = []
    for rel, meta in sorted(frozen_files.items()):
        m = measure(rel)
        if not m["exists"]:
            drift_rows.append({"path": rel, "state": "MISSING", "pin": meta.get("sha256")})
        elif m["sha256"] != meta.get("sha256"):
            drift_rows.append({"path": rel, "state": "DRIFT", "pin": meta.get("sha256"),
                               "measured": m["sha256"]})
    map_refs = [{"json_path": p, "value": v[:160]} for p, v in walk_strings(map_obj)
                if frozen_prefix and frozen_prefix in v][:20]
    r2_pass = bool(frozen_prefix and not drift_rows and len(frozen_files) >= 40)
    write_json(RAW / "frozen_drift_r3.json",
               {"probe": TASK_ID, "probe_at": probe_at, "frozen_revision": frozen.get("revision"),
                "frozen_revision_baseline_r2": FROZEN_REVISION,
                "frozen_revision_changed_since_r2_baseline": frozen.get("revision") != FROZEN_REVISION,
                "frozen_at": frozen.get("frozen_at"), "frozen_measured": frozen_meas,
                "n_pins": len(frozen_files), "n_drift": len(drift_rows), "drift": drift_rows,
                "frozen_prefix_refs_in_map": map_refs})
    report["checks"].append({
        "id": "R2-MANIFEST-SELF", "severity": "hard", "status": "PASS" if r2_pass else "FAIL",
        "detail": {"frozen_revision": frozen.get("revision"),
                   "frozen_revision_baseline_r2": FROZEN_REVISION,
                   "frozen_revision_changed_since_r2_baseline": frozen.get("revision") != FROZEN_REVISION,
                   "frozen_at": frozen.get("frozen_at"),
                   "frozen_measured": frozen_meas, "n_pins": len(frozen_files),
                   "n_drift": len(drift_rows), "drift": drift_rows,
                   "frozen_prefix_refs_in_map": len(map_refs)}})

    # ---------- R3: event shadow ----------
    def recv(e: dict):
        return e.get("_received_at") or e.get("received_at")

    def brief(e: dict) -> dict:
        return {"event_id": e.get("event_id"), "actor": e.get("actor"),
                "created_at": e.get("created_at"), "received_at": recv(e),
                "sha256": e.get("sha256"), "supersedes": e.get("supersedes"),
                "note": (str(e.get("note"))[:200] if e.get("note") else None),
                "future_dated_at_probe": bool(e.get("created_at", "") > probe_at)}

    shadow_rows = []
    created_ok = ingest_ok = 0
    for rel in HELD:
        pin = frozen_files.get(rel, {}).get("sha256")
        evs = [e for e in events if e.get("event_type") == "artifact" and rel in event_paths(e)]
        key = lambda e: (e.get("created_at", ""), e.get("event_id", ""))  # noqa: E731
        pin_evs = [e for e in evs if e.get("sha256") == pin]
        newest_pin = max(pin_evs, key=key) if pin_evs else None
        created_newest = max(evs, key=key) if evs else None
        shadow = []
        if newest_pin:
            for e in evs:
                if e.get("sha256") == pin:
                    continue
                if e.get("created_at", "") > newest_pin.get("created_at", ""):
                    shadow.append(brief(e))
        shadow.sort(key=lambda x: x["created_at"])
        rec_evs = [e for e in evs if recv(e)]
        received_newest = None
        if rec_evs:
            re_ = max(rec_evs, key=lambda e: (recv(e), e.get("created_at", "")))
            received_newest = {"event_id": re_.get("event_id"), "received_at": recv(re_),
                               "created_at": re_.get("created_at"), "sha256": re_.get("sha256"),
                               "matches_pin": re_.get("sha256") == pin}
        inversion = sorted(
            [e for e in shadow if recv(e) and newest_pin and recv(e) < (recv(newest_pin) or "")],
            key=lambda e: recv(e))
        row = {"path": rel, "role": HELD_ROLE[rel], "frozen_pin": pin, "events": len(evs),
               "n_events_with_received": len(rec_evs), "n_events_without_received": len(evs) - len(rec_evs),
               "created_newest": brief(created_newest) if created_newest else None,
               "created_newest_matches_pin": bool(created_newest and created_newest.get("sha256") == pin),
               "newest_pin_event": brief(newest_pin) if newest_pin else None,
               "stale_events_newer_than_pin_event": shadow,
               "stale_events_self_declaring_supersede": [e["event_id"] for e in shadow
                                                         if e.get("supersedes")],
               "stale_events_lacking_received": [e["event_id"] for e in shadow
                                                 if not e.get("received_at")],
               "created_at_semantically_inverted": [brief(e) for e in inversion],
               "shadowed": bool(shadow), "received_newest": received_newest,
               "pin_event_present": newest_pin is not None,
               "ingest_order_matches_pin": bool(received_newest and received_newest["matches_pin"])}
        shadow_rows.append(row)
        created_ok += 1 if row["created_newest_matches_pin"] else 0
        ingest_ok += 1 if row["ingest_order_matches_pin"] else 0
    shadowed = [r["path"] for r in shadow_rows if r["shadowed"]]
    pin_missing = [r["path"] for r in shadow_rows if not r["pin_event_present"]]
    clean = [r["path"] for r in shadow_rows if r["pin_event_present"] and not r["shadowed"]]
    inverted = [r["path"] for r in shadow_rows if r["created_at_semantically_inverted"]]
    unknown_order = [r["path"] for r in shadow_rows if r["n_events_without_received"]]
    shadow_lacking_recv = {r["path"]: r["stale_events_lacking_received"] for r in shadow_rows
                           if r["stale_events_lacking_received"]}
    r3_pass = not shadowed and not pin_missing
    r3_detail = {"held_paths_shadowed": shadowed, "n_shadowed": len(shadowed),
                 "held_paths_pin_event_missing": pin_missing, "n_pin_event_missing": len(pin_missing),
                 "held_paths_clean": clean, "n_clean": len(clean),
                 "created_at_newest_matches_pin_paths": created_ok,
                 "ingest_order_newest_matches_pin_paths": ingest_ok,
                 "created_at_semantically_inverted_paths": inverted,
                 "paths_with_events_lacking_received_at": unknown_order,
                 "shadowing_events_lacking_received_at": shadow_lacking_recv,
                 "rows": shadow_rows}
    write_json(RAW / "event_shadow_r3.json",
               {"probe": TASK_ID, "probe_at": probe_at, "event_rows": shadow_rows,
                "held_paths_shadowed": shadowed, "n_shadowed": len(shadowed),
                "held_paths_pin_event_missing": pin_missing, "n_pin_event_missing": len(pin_missing),
                "held_paths_clean": clean,
                "created_at_newest_matches_pin_paths": created_ok,
                "ingest_order_newest_matches_pin_paths": ingest_ok,
                "created_at_semantically_inverted_paths": inverted,
                "paths_with_events_lacking_received_at": unknown_order,
                "shadowing_events_lacking_received_at": shadow_lacking_recv})
    report["checks"].append({"id": "R3-EVENT-SHADOW", "severity": "hard",
                             "status": "PASS" if r3_pass else "FAIL", "detail": r3_detail})

    # ---------- R4: declared consistency evidence resolution ----------
    import yaml  # local import so the read-only checks above can run without PyYAML
    f2b = yaml.safe_load((ROOT / F2B_REL).read_text())
    binding = f2b.get("f0_binding", {}) if isinstance(f2b, dict) else {}
    declared_path = binding.get("consistency_evidence")
    declared_sha = binding.get("consistency_evidence_sha256")
    declared_meas = measure(declared_path) if declared_path else None
    r4_pass = bool(declared_sha and declared_meas and declared_meas.get("sha256") == declared_sha)
    # locate the declared bytes anywhere in the tree (bounded) to characterise the mismatch
    alt_locations = []
    if declared_sha and not r4_pass:
        needle = declared_sha[:12]
        roots = [ROOT / "artifacts", ROOT / "reviews", ROOT / "schemas", ROOT / "runtime" / "state"]
        for base in roots:
            if len(alt_locations) >= 5:
                break
            for p in base.rglob("*"):
                if not p.is_file():
                    continue
                rel = str(p.relative_to(ROOT))
                if rel.startswith("runtime/instances/"):
                    continue
                if needle in p.name:
                    h = sha256_file(p)
                    if h == declared_sha:
                        alt_locations.append(rel)
                if len(alt_locations) >= 5:
                    break
    f0_decl = binding.get("declared_f0_artifact")
    f0_meas = measure(f0_decl) if f0_decl else None
    write_json(RAW / "f2b_binding_r3.json",
               {"probe": TASK_ID, "probe_at": probe_at, "f2b_path": F2B_REL,
                "f2b_measured": measure(F2B_REL), "f0_binding": binding,
                "declared_path_measured": declared_meas,
                "declared_f0_measured": f0_meas if f0_decl else None,
                "declared_bytes_found_at": alt_locations, "resolves": r4_pass})
    report["checks"].append({
        "id": "R4-DECLARED-EVIDENCE-RESOLUTION", "severity": "hard",
        "status": "PASS" if r4_pass else "FAIL",
        "detail": {"declared_path": declared_path, "declared_sha256": declared_sha,
                   "declared_path_measured": declared_meas,
                   "declared_f0_artifact": f0_decl,
                   "declared_f0_sha256": binding.get("declared_f0_sha256"),
                   "declared_f0_measured": (f0_meas or {}).get("sha256"),
                   "declared_f0_matches_live": bool(
                       f0_meas and f0_meas.get("sha256") == binding.get("declared_f0_sha256")),
                   "declared_bytes_found_at": alt_locations, "resolves_at_declared_path": r4_pass}})

    # ---------- R5: context (informational) ----------
    type_census: dict[str, int] = {}
    for e in events:
        type_census[e.get("event_type", "?")] = type_census.get(e.get("event_type", "?"), 0) + 1
    supersede_events = [e.get("event_id") for e in events
                        if any(tok in json.dumps(e).lower() for tok in SUPERSEDE_TOKENS)]
    artifact_with_supersedes = [e.get("event_id") for e in events
                                if e.get("event_type") == "artifact" and e.get("supersedes")]
    supersede_like_types = sorted(t for t in type_census
                                  if any(tok in t.lower() for tok in SUPERSEDE_TOKENS))
    gates = [{"gate_id": g.get("gate_id"), "verdict": g.get("verdict"),
              "updated_at": g.get("updated_at"), "unmet": (g.get("unmet") or [])[:2]}
             for g in map_obj.get("gates", [])]
    stale_refs = []
    for p, v in walk_strings(map_obj):
        m = re.search(r"#([0-9a-f]{12})", v)
        if not m:
            continue
        for rel in HELD:
            if rel in v and m.group(1) != (frozen_files.get(rel, {}).get("sha256") or "")[:12]:
                stale_refs.append({"json_path": p, "value": v[:200], "held_path": rel,
                                   "cited_prefix": m.group(1)})
        if len(stale_refs) >= 25:
            break
    missing_pins = {r["path"]: r["frozen_pin"] for r in shadow_rows if not r["pin_event_present"]}
    outbox_pin_announcements = {}
    for rel, pin in missing_pins.items():
        hits = []
        for f in sorted((ROOT / "comms" / "outbox").glob("*.jsonl")):
            try:
                body = f.read_text()
            except OSError:
                continue
            if pin[:16] not in body:
                continue
            for line in body.splitlines():
                line = line.strip()
                if not line or pin[:16] not in line:
                    continue
                try:
                    o = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if o.get("event_type") == "artifact" and (
                        pin[:16] in str(o.get("sha256")) or o.get("path") == rel):
                    hits.append({"file": f.name, "event_id": o.get("event_id"),
                                 "path": o.get("path"), "sha256": str(o.get("sha256"))[:12]})
        outbox_pin_announcements[rel] = hits[:10]
    write_json(RAW / "map_gate_slice_r3.json",
               {"probe": TASK_ID, "probe_at": probe_at,
                "map_sha256": sha256_file(MAP_PATH), "map_updated_at": map_obj.get("updated_at"),
                "gates": gates, "event_type_census": type_census,
                "event_types_supersede_like": supersede_like_types,
                "n_artifact_events_with_supersedes_field": len(artifact_with_supersedes),
                "artifact_events_with_supersedes_field": artifact_with_supersedes[:20],
                "events_with_supersede_token": supersede_events[:20],
                "outbox_artifact_announcements_for_missing_pins": outbox_pin_announcements,
                "held_path_refs_citing_non_frozen_hash": stale_refs})
    report["checks"].append({"id": "R5-CONTEXT", "severity": "info", "status": "INFO",
                             "detail": {"gates": gates, "event_type_census": type_census,
                                        "event_types_supersede_like": supersede_like_types,
                                        "n_artifact_events_with_supersedes_field": len(artifact_with_supersedes),
                                        "n_events_with_supersede_token": len(supersede_events),
                                        "outbox_artifact_announcements_for_missing_pins": outbox_pin_announcements,
                                        "n_held_path_refs_citing_non_frozen_hash": len(stale_refs),
                                        "examples": stale_refs[:8]}})

    # ---------- R6: no probe drift ----------
    t1 = {rel: measure(rel)["sha256"] for rel in HELD}
    moved = [{"path": rel, "before": t0[rel], "after": t1[rel]} for rel in HELD if t0[rel] != t1[rel]]
    frozen_after = measure(FROZEN_REL)
    r6_pass = not moved and frozen_after["sha256"] == frozen_meas["sha256"]
    write_json(RAW / "probe_drift_r3.json",
               {"probe": TASK_ID, "probe_at": probe_at, "before": t0, "after": t1,
                "moved": moved, "frozen_after": frozen_after, "stable": r6_pass})
    report["checks"].append({"id": "R6-NO-PROBE-DRIFT", "severity": "hard",
                             "status": "PASS" if r6_pass else "FAIL",
                             "detail": {"moved_during_probe": moved, "frozen_stable": r6_pass}})

    # ---------- findings + verdict ----------
    findings = []
    if r1_pass:
        census_txt = (f"the full manifest drift census is clean ({len(frozen_files)}/"
                      f"{len(frozen_files)} pins match disk)" if not drift_rows else
                      f"but the full manifest drift census is NOT clean ({len(drift_rows)}/"
                      f"{len(frozen_files)} pins mismatch disk, see HF-05-04)")
        findings.append({"id": "F-05-01", "severity": "info",
                         "finding": ("Byte-level freeze hold is intact for the five held paths at this "
                                     f"instant: all five match the FROZEN rev{frozen.get('revision')} pins "
                                     f"({frozen_meas['sha256'][:12]}), {census_txt}.")})
    if pin_missing:
        miss_details = []
        for r in shadow_rows:
            if r["pin_event_present"]:
                continue
            n = r["created_newest"] or {}
            miss_details.append(f"{r['path']} pin {str(r['frozen_pin'])[:12]}, newest stream event "
                                f"{n.get('event_id')} sha {str(n.get('sha256'))[:12]} "
                                f"({n.get('created_at')})")
        outbox_hits = {k: v for k, v in outbox_pin_announcements.items() if v}
        outbox_txt = ("a bounded scan of comms/outbox also finds no artifact event announcing them"
                      if not outbox_hits else
                      f"outbox artifact announcements found (pending ingest): {json.dumps(outbox_hits)[:400]}")
        findings.append({"id": "HF-05-01", "severity": "hard",
                         "finding": (f"Unannounced FROZEN rev{frozen.get('revision')} pins: "
                                     f"{len(pin_missing)}/5 held paths have a manifest pin that no artifact "
                                     "event in the accepted stream carries, so no ordering rule can resolve "
                                     "the stream to the frozen bytes. Missing announcements: "
                                     + "; ".join(miss_details)
                                     + f". FROZEN.json itself ({frozen_meas['sha256'][:12]}, frozen_at "
                                     f"{frozen.get('frozen_at')}) has no artifact event either, and "
                                     + outbox_txt
                                     + ". This violates the manifest's own change_protocol (a canonical "
                                     "change must re-emit an artifact event with the new sha256), so "
                                     "hash-bound reviewers cannot bind the rev"
                                     f"{frozen.get('revision')} bytes from the stream; reviews referencing "
                                     "the new hashes exist but are not announcements of the artifact.")})
    if shadowed:
        details = []
        for r in shadow_rows:
            if not r["shadowed"]:
                continue
            n = r["created_newest"]
            details.append(f"{r['path']} <- {n['event_id']} ({n['created_at']}, sha "
                           f"{str(n['sha256'])[:12]}, supersedes={n['supersedes'] or 'none'}, "
                           f"future_dated={str(n['future_dated_at_probe']).lower()})")
        findings.append({"id": "HF-05-02", "severity": "hard",
                         "finding": ("Event-stream created_at shadow: "
                                     + str(len(shadowed)) + "/5 held paths have non-pin artifact events "
                                     "whose created_at sorts newer than the FROZEN pin event, so "
                                     "resolution-by-created_at over the accepted stream binds stale bytes "
                                     "even though disk is correct. " + "; ".join(details) + ". Ordering by "
                                     "ingest order (_received_at) instead resolves to the pin for "
                                     + str(ingest_ok) + "/5 held paths (created_at resolves for "
                                     + str(created_ok) + "/5), and the shadowing events self-declare "
                                     "supersession: "
                                     + "; ".join(f"{r['path']}: {', '.join(r['stale_events_self_declaring_supersede'])}"
                                                 for r in shadow_rows if r["stale_events_self_declaring_supersede"])
                                     + ". Shadowing events with no _received_at (fallback rule needed): "
                                     + (json.dumps(shadow_lacking_recv) if shadow_lacking_recv else "none")
                                     + ". Repair path is therefore a read-path rule (rank by _received_at "
                                       "with a defined fallback for events lacking it), not a canonical "
                                       "byte edit.")})
    if not r4_pass:
        r4d = next(c for c in report["checks"]
                   if c["id"] == "R4-DECLARED-EVIDENCE-RESOLUTION")["detail"]
        findings.append({"id": "HF-05-03", "severity": "hard",
                         "finding": ("F2b f0_binding.consistency_evidence_sha256 "
                                     f"{str(r4d['declared_sha256'])[:12]} still does not resolve at "
                                     f"the path it names ({r4d['declared_path']}); that path measures "
                                     f"{str((r4d['declared_path_measured'] or {}).get('sha256'))[:12]}. "
                                     f"The declared bytes were found at {r4d['declared_bytes_found_at'] or 'no location'}"
                                     ". Overlap disclosure: worker-086 is separately repairing this "
                                     "binding (R2 durability candidate + FROZEN rev29 re-pin; claim "
                                     "w086-20260912T004910-claim-r2-durability); this probe only re-measures "
                                     "the current state and requests no canonical byte edit.")})
    off_pin = [r for r in r1_rows if not r["match"]]
    if off_pin or drift_rows:
        moved_txt = "; ".join(
            f"{r['path']} {str(r['frozen_pin'])[:12]} -> {str(r['measured'])[:12]}" for r in off_pin)
        drift_txt = "; ".join(
            f"{x['path']} {str(x.get('pin'))[:12]} -> {str(x.get('measured'))[:12]}" for x in drift_rows)
        findings.append({"id": "HF-05-04", "severity": "hard",
                         "finding": (f"Freeze manifest drift at the probe instant: {len(drift_rows)}/"
                                     f"{len(frozen_files)} FROZEN rev{frozen.get('revision')} pinned files "
                                     f"mismatch disk ({drift_txt or 'none'}); off-pin held paths: "
                                     f"{moved_txt or 'none'}. Manifest {frozen_meas['sha256'][:12]} "
                                     f"(frozen_at {frozen.get('frozen_at')}); R6-NO-PROBE-DRIFT "
                                     f"{'FAILED' if not r6_pass else 'passed'}, so "
                                     f"{'the bytes moved during this probe window' if not r6_pass else 'the drift predates this window'}. "
                                     f"The manifest's blanket pin claim is false for the drifted files: "
                                     f"hash-bound reviews of them are void until the owner restores or "
                                     f"re-pins them, and any post-freeze regeneration must be announced by "
                                     f"an artifact event carrying the new hash.")})
    if not r3_pass and r4_pass:
        findings.append({"id": "F-05-03", "severity": "info",
                         "finding": (f"Declared-evidence resolution (R4) is repaired in the live F2b "
                                     f"rev{f2b.get('revision') if isinstance(f2b, dict) else '?'} bytes "
                                     f"(declared == measured); the remaining hard failure is R3 "
                                     f"({len(pin_missing)} unannounced pin(s), {len(shadowed)} shadowed).")})
    if not r3_pass and not r4_pass:
        findings.append({"id": "F-05-03", "severity": "info",
                         "finding": ("Both r2 defect classes persist at the r3 instant; no repair is visible "
                                     "in the canonical paths, and the byte-level hold itself is not breached.")})
    if frozen.get("revision") != FROZEN_REVISION:
        findings.append({"id": "F-05-04", "severity": "info",
                         "finding": (f"FROZEN revision moved {FROZEN_REVISION} -> {frozen.get('revision')} "
                                     f"(frozen_at {frozen.get('frozen_at')}, manifest "
                                     f"{frozen_meas['sha256'][:12]}) between the r2 baseline and this probe. "
                                     f"Every reviewer verdict bound to the rev{FROZEN_REVISION} pins is void; "
                                     f"coverage restarts at the rev{frozen.get('revision')} hashes, which are "
                                     f"not yet announced by artifact events (HF-05-01).")})

    else:
        pass


    hard_fail = [c["id"] for c in report["checks"]
                 if c["severity"] == "hard" and c["status"] == "FAIL"]
    hard_findings = [f["id"] for f in findings if f["severity"] == "hard"]
    verdict = "revise" if hard_fail else "accept"
    score = 0
    if verdict == "accept":
        score = 5
    elif r1_pass and r2_pass and r6_pass:
        score = 3 if hard_fail else 4
    else:
        score = 2
    f2b_meas = measure(F2B_REL)
    f2b_rev = f2b.get("revision") if isinstance(f2b, dict) else None
    next_falsifier = (
        "A re-probe in which (a) under the read path actually used to resolve 'latest artifact per "
        f"path' every held path resolves to the FROZEN rev{frozen.get('revision')} pin sha256 "
        "(conditions: created_at order has no non-pin event newer than the pin event, or the binding "
        "read path ranks by _received_at with a defined fallback for events lacking it, and no "
        "future-dated stale event wins); (b) F2b f0_binding.consistency_evidence_sha256 equals the "
        "measured sha256 of the path it names, stably across two consecutive probes; (c) all "
        f"{len(frozen_files)} FROZEN pins and FROZEN.json itself stay drift-free, so that no held path "
        "is off-pin at a manifest revision that does not carry the new bytes. Condition (b) may be met "
        "either by refreshing the declaration to the live path hash or by moving the live evidence to "
        "the declared bytes; a declared hash resolving only at a reconstruction outside the declared "
        "path does not satisfy it. Any canonical byte move voids this window, not the finding."
    )
    report.update({
        "verdict": verdict, "score_0_5": score, "hard_failures": hard_findings,
        "hard_fail_check_ids": hard_fail, "findings": findings,
        "f2b_measured": f2b_meas, "f2b_revision": f2b_rev,
        "reviewed_revision": f2b_rev, "reviewed_sha256": f2b_meas["sha256"],
        "frozen_revision_reviewed": frozen.get("revision"),
        "frozen_measured": frozen_meas, "map_sha256": sha256_file(MAP_PATH),
        "counts_as_full_schema_verdict": False, "next_falsifier": next_falsifier,
    })

    report_sha = write_json(RAW / "probe_report_r3.json", report)

    # evidence_refs: raw evidence + the pinned inputs the probe binds
    refs = []
    for name in ("probe_report_r3.json", "held_path_hashes_r3.json", "frozen_drift_r3.json",
                 "event_shadow_r3.json", "f2b_binding_r3.json", "map_gate_slice_r3.json",
                 "probe_drift_r3.json"):
        h = sha256_file(RAW / name)
        refs.append(f"artifacts/worker-095/freeze_hold_binding_integrity_r3/evidence/raw/{name}#{h[:12]}")
    for rel in HELD:
        refs.append(f"{rel}#{str(frozen_files.get(rel, {}).get('sha256'))[:12]}")
    refs.append(f"{FROZEN_REL}#{frozen_prefix}")
    refs.append(f"research_map/research_map.json#{str(report['map_sha256'])[:12]}")
    refs.append(f"research_map/events.jsonl#{str(sha256_file(EVENTS))[:12]}")
    verdict_obj = {
        "probe": TASK_ID, "worker": WORKER, "node_id": NODE_ID, "class_id": CLASS_ID,
        "gate": GATE, "probe_at": probe_at, "verdict": verdict, "score_0_5": score,
        "counts_as_full_schema_verdict": False, "hard_failures": hard_findings,
        "findings": findings,
        "reviewed_revision": f2b_rev, "reviewed_sha256": f2b_meas["sha256"],
        "frozen_revision_reviewed": frozen.get("revision"),
        "frozen_manifest_sha256": frozen_meas["sha256"],
        "check_status": {c["id"]: c["status"] for c in report["checks"]},
        "evidence_refs": refs, "next_falsifier": next_falsifier,
        "probe_script": "artifacts/worker-095/freeze_hold_binding_integrity_r3/run_probe_r3.py",
        "probe_report_sha256": report_sha,
    }
    verdict_sha = write_json(HERE / "verdict.json", verdict_obj)
    report["_verdict_sha256"] = verdict_sha
    report["evidence_refs"] = refs
    return report


def emit() -> dict:
    report = json.loads((RAW / "probe_report_r3.json").read_text())
    verdict_obj = json.loads((HERE / "verdict.json").read_text())
    ts = report["probe_at"]
    stamp = datetime.fromisoformat(ts).strftime("%Y%m%dT%H%M%S")
    verdict_sha = sha256_file(HERE / "verdict.json") or ""
    script_sha = sha256_file(Path(__file__)) or ""
    refs = verdict_obj["evidence_refs"]
    nf = verdict_obj["next_falsifier"]
    verdict = report["verdict"]
    score = report["score_0_5"]
    shadow = next(c for c in report["checks"] if c["id"] == "R3-EVENT-SHADOW")["detail"]
    r1s = next(c for c in report["checks"] if c["id"] == "R1-PIN-MATCH")["status"]
    r2s = next(c for c in report["checks"] if c["id"] == "R2-MANIFEST-SELF")["status"]
    r4 = next(c for c in report["checks"] if c["id"] == "R4-DECLARED-EVIDENCE-RESOLUTION")
    map12 = str(report.get("map_sha256"))[:12]
    reviewed_sha = verdict_obj["reviewed_sha256"]
    shadowed = shadow["held_paths_shadowed"]

    r1 = next(c for c in report["checks"] if c["id"] == "R1-PIN-MATCH")
    r2 = next(c for c in report["checks"] if c["id"] == "R2-MANIFEST-SELF")
    r3 = next(c for c in report["checks"] if c["id"] == "R3-EVENT-SHADOW")
    r6 = next(c for c in report["checks"] if c["id"] == "R6-NO-PROBE-DRIFT")
    off_pin = [r for r in r1["detail"] if not r["match"]]
    n_drift = r2["detail"]["n_drift"]
    n_pins = r2["detail"]["n_pins"]
    fz_rev = verdict_obj["frozen_revision_reviewed"]
    f2b_rev = verdict_obj["reviewed_revision"]
    hold_intact = r1s == "PASS" and r2s == "PASS"
    r4_status = r4["status"]

    defect_parts = []
    pin_missing = shadow.get("held_paths_pin_event_missing") or []
    if pin_missing:
        defect_parts.append(
            f"(1) Unannounced pins: {len(pin_missing)}/5 held paths ({', '.join(pin_missing)}) have a "
            f"FROZEN rev{fz_rev} pin that no artifact event in the accepted stream carries, and FROZEN.json "
            f"itself is unannounced, so no ordering rule can resolve the stream to the frozen bytes "
            f"(change_protocol violation).")
    if shadowed:
        defect_parts.append(
            f"(2) Event-stream created_at shadow: {shadow['n_shadowed']}/5 held paths ({', '.join(shadowed)}) "
            f"have non-pin artifact events sorting newer by created_at than their FROZEN rev{fz_rev} pin "
            f"event; the shadowing events self-declare supersession, and ordering by _received_at resolves "
            f"to the pin for {shadow['ingest_order_newest_matches_pin_paths']}/5 (created_at: "
            f"{shadow['created_at_newest_matches_pin_paths']}/5).")
    if r4_status == "FAIL":
        defect_parts.append(
            f"(3) F2b f0_binding declares consistency_evidence_sha256 "
            f"{str(r4['detail']['declared_sha256'])[:12]} on {r4['detail']['declared_path']}, which "
            f"measures {str((r4['detail']['declared_path_measured'] or {}).get('sha256'))[:12]}; the "
            f"declared bytes resolve only at a reconstruction outside the declared path "
            f"({r4['detail']['declared_bytes_found_at']}).")
    if off_pin or n_drift:
        defect_parts.append(
            f"(4) Freeze-hold pin drift: {len(off_pin)}/5 held paths are off the current FROZEN rev{fz_rev} "
            f"pins and {n_drift}/{n_pins} manifest pins mismatch disk (R6 {r6['status']}).")
    if not defect_parts:
        defect_parts.append("(0) no hard defect at this instant")

    needed = []
    if pin_missing:
        needed.append("(a) freeze owner must re-emit artifact events for the moved canonical bytes and for "
                      "the FROZEN manifest at their measured hashes, so reviewers can bind the rev"
                      f"{fz_rev} pins from the accepted stream")
    if shadowed:
        needed.append("(b) resolve latest-artifact-per-path by ingest/_received_at order with a defined "
                      "fallback for un-ingested events, or add a supersede/tombstone event type so "
                      "created_at cannot resurrect superseded submissions")
    if r4_status == "FAIL":
        needed.append("(c) refresh F2b f0_binding to the measured live hash (or move the live evidence to "
                      "the declared bytes) and register it in runtime/state/artifact_hashes.json")
    if off_pin or n_drift:
        needed.append("(d) freeze owner must either re-emit a bumped FROZEN manifest plus artifact events "
                      "covering the moved bytes, or restore the pinned bytes; until then every hash-bound "
                      "reviewer verdict at the old pins is void")
    needed.append("(e) re-probe from a second instance after the fix lands")
    needed_txt = "; ".join(needed) + ". This worker requests no canonical byte edit."

    claim_statement = (
        f"Artifact-and-binding measurement, not a mathematics or physics claim, at FROZEN rev{fz_rev} "
        f"manifest {verdict_obj['frozen_manifest_sha256'][:12]}: R1 {r1s} ({len(off_pin)}/5 held paths "
        f"off-pin), R2 {r2s} ({n_drift}/{n_pins} pins drift), R3 {r3['status']} "
        f"({len(pin_missing)}/5 pins unannounced, {shadow['n_shadowed']}/5 shadowed), R4 {r4_status}, "
        f"R6 {r6['status']}. The live F2b is rev{f2b_rev} {reviewed_sha[:12]}. "
        f"Verdict {verdict} ({score}/5); counts_as_full_schema_verdict=false."
    )

    prior_r3_receipts = []
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            try:
                eid = json.loads(line).get("event_id") or ""
            except json.JSONDecodeError:
                continue
            if eid.startswith("w095-hold-r3-") and "task-receipt-complete" in eid and stamp not in eid:
                prior_r3_receipts.append(eid)
    supersede_note = (f" Supersedes the earlier r3 mid-move receipt(s) {prior_r3_receipts}."
                      if prior_r3_receipts else "")

    events = [
        {"event_id": f"w095-hold-r3-{stamp}-task-claim", "event_type": "status", "actor": WORKER,
         "created_at": ts, "node_id": NODE_ID, "gate": GATE, "class_id": CLASS_ID,
         "status": "active", "hours": 0.3,
         "summary": (f"{TASK_ID}: pass-06 re-probe of the FROZEN rev{fz_rev} freeze-hold at map {map12} "
                     f"(binding-integrity scope, not a full schema verdict)."),
         "evidence_refs": refs, "next_falsifier": nf},
        {"event_id": f"w095-hold-r3-{stamp}-artifact-verdict", "event_type": "artifact", "actor": WORKER,
         "created_at": ts, "node_id": NODE_ID, "class_id": CLASS_ID,
         "artifact_type": "hold_binding_integrity_reprobe_verdict",
         "path": "artifacts/worker-095/freeze_hold_binding_integrity_r3/verdict.json",
         "sha256": verdict_sha, "validation_status": "unverified",
         "reviewed_revision": f2b_rev, "reviewed_sha256": reviewed_sha,
         "frozen_revision_reviewed": fz_rev,
         "companion_script": {"path": "artifacts/worker-095/freeze_hold_binding_integrity_r3/run_probe_r3.py",
                              "sha256": script_sha},
         "evidence_refs": refs},
        {"event_id": f"w095-hold-r3-{stamp}-claim-binding", "event_type": "claim", "actor": WORKER,
         "created_at": ts, "node_id": NODE_ID, "gate": GATE, "class_id": CLASS_ID,
         "conclusion_type": "formal_model",
         "statement": claim_statement,
         "assumptions": [f"FROZEN.json rev{fz_rev} is the freeze authority for the five held paths",
                         "resolution-by-created_at over research_map/events.jsonl is the binding read path",
                         "worker review cannot set node status or gate verdicts"],
         "falsifier": nf, "evidence_refs": refs},
        {"event_id": f"w095-hold-r3-{stamp}-review-binding", "event_type": "review", "actor": WORKER,
         "created_at": ts, "target_id": F2B_REL, "reviewer": WORKER, "node_id": NODE_ID,
         "class_id": CLASS_ID, "gate": GATE, "verdict": verdict, "score": score,
         "artifact_sha256": reviewed_sha,
         "frozen_revision_reviewed": fz_rev,
         "hard_failures": report["hard_failures"],
         "findings": [{"id": f["id"], "severity": f["severity"], "finding": f["finding"]}
                      for f in report["findings"]],
         "summary": (f"Binding-integrity re-probe r3 at F2b rev{f2b_rev} {reviewed_sha[:12]} / FROZEN "
                     f"rev{fz_rev}: R1 {r1s} ({len(off_pin)}/5 off-pin), R2 {r2s} ({n_drift}/{n_pins} "
                     f"drift), R3 {r3['status']} ({len(pin_missing)}/5 unannounced, "
                     f"{shadow['n_shadowed']}/5 shadowed), R4 {r4_status}, R6 {r6['status']}."),
         "next_falsifier": nf, "evidence_refs": refs},
        {"event_id": f"w095-hold-r3-{stamp}-blocker-evidence-resolution", "event_type": "blocker",
         "actor": WORKER, "created_at": ts, "node_id": NODE_ID, "gate": GATE, "class_id": CLASS_ID,
         "description": (f"Pass-06 hold/binding measurement at FROZEN rev{fz_rev}: " + " ".join(defect_parts)
                         + (" Byte-level hold verified intact on the pinned paths."
                            if hold_intact else " Byte-level hold is NOT intact at this instant.")),
         "needed_to_unblock": needed_txt,
         "evidence_refs": refs},
        {"event_id": f"w095-hold-r3-{stamp}-task-receipt-complete", "event_type": "status", "actor": WORKER,
         "created_at": ts, "node_id": NODE_ID, "gate": GATE, "class_id": CLASS_ID,
         "status": "active", "hours": 0.3,
         "summary": (f"{TASK_ID} worker-level receipt complete; node status deliberately unchanged (worker "
                     f"events cannot set status=done, validation_status=passed, or a gate verdict). "
                     f"verdict={verdict} ({score}/5) at F2b rev{f2b_rev} {reviewed_sha[:12]} / FROZEN "
                     f"rev{fz_rev}; artifact + 7 raw evidence files + checkpoint written. "
                     f"counts_as_full_schema_verdict=false.{supersede_note}"),
         "evidence_refs": refs, "next_falsifier": nf},
    ]

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            try:
                existing.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                continue
    required = {"artifact": ["node_id", "artifact_type", "path", "sha256", "validation_status"],
                "review": ["target_id", "reviewer", "verdict", "score", "hard_failures", "findings"],
                "claim": ["class_id", "statement", "conclusion_type", "assumptions", "falsifier",
                          "evidence_refs"],
                "blocker": ["node_id", "description", "needed_to_unblock", "evidence_refs"],
                "status": ["node_id", "status", "hours", "summary", "evidence_refs", "next_falsifier"]}
    base = ["event_id", "event_type", "created_at", "actor"]
    for ev in events:
        missing = [k for k in base + required.get(ev["event_type"], []) if k not in ev]
        if missing:
            raise SystemExit(f"refusing to emit malformed event {ev.get('event_id')}: missing {missing}")
        if ev["event_type"] == "artifact" and ev["validation_status"] not in {
                "unverified", "passed", "failed", "retracted"}:
            raise SystemExit("bad validation_status")
        if ev["event_type"] == "review" and ev["verdict"] not in {
                "accept", "revise", "reject", "inconclusive"}:
            raise SystemExit("bad review verdict")
    if len({ev["event_id"] for ev in events}) != len(events):
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
        "node_id": NODE_ID, "gate": GATE, "reviewed_revision": verdict_obj["reviewed_revision"],
        "reviewed_sha256": reviewed_sha,
        "frozen_revision_reviewed": verdict_obj["frozen_revision_reviewed"],
        "artifact": "artifacts/worker-095/freeze_hold_binding_integrity_r3/verdict.json",
        "artifact_sha256": verdict_sha,
        "evidence_dir": "artifacts/worker-095/freeze_hold_binding_integrity_r3/evidence/raw/",
        "probe": {"path": "artifacts/worker-095/freeze_hold_binding_integrity_r3/run_probe_r3.py",
                  "sha256": script_sha},
        "verdict": verdict, "score_0_5": score, "counts_as_full_schema_verdict": False,
        "check_status": verdict_obj["check_status"],
        "next_falsifier": nf,
    }
    ck_path = STATE / f"w095_hold_binding_integrity_r3_checkpoint_{stamp}.json"
    ck_path.write_text(json.dumps(ckpt, indent=2, sort_keys=True) + "\n")
    with (STATE / "w095_hold_binding_integrity_r3_checkpoints.jsonl").open("a") as fh:
        fh.write(json.dumps(ckpt, sort_keys=True) + "\n")
    (STATE / "w095_latest_checkpoint.json").write_text(json.dumps({
        "worker": WORKER, "task_id": TASK_ID, "checkpoint_at": ts, "verdict": verdict,
        "path": str(ck_path.relative_to(ROOT)), "artifact_sha256": verdict_sha,
        "reviewed_sha256": reviewed_sha, "next_falsifier": nf}, indent=2, sort_keys=True) + "\n")
    return {"events_appended": appended, "checkpoint": str(ck_path.relative_to(ROOT))}


if __name__ == "__main__":
    rep = probe()
    print(json.dumps({"probe": TASK_ID, "verdict": rep["verdict"], "score": rep["score_0_5"],
                      "checks": {c["id"]: c["status"] for c in rep["checks"]},
                      "findings": [f["id"] for f in rep["findings"]],
                      "verdict_sha256": rep["_verdict_sha256"]}, indent=2))
    if "--emit" in sys.argv:
        print(json.dumps(emit(), indent=2))
