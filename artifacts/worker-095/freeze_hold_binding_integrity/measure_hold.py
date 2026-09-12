#!/usr/bin/env python3
"""W095-HOLD-BIND-INTEGRITY-03 -- independent probe of the astra-life04 freeze-hold.

Task: verify, at FROZEN revision 28, the publication/binding integrity of the five
canonical paths held by astra-life04-freeze-hold, anchored on class AF-SCC-C0-VAC-GEN
(node F2b, gate G-FORM).

The probe measures bytes; it never writes any canonical artifact.  It writes only
under artifacts/worker-095/freeze_hold_binding_integrity/evidence/raw/.

Reproduce:  python3 artifacts/worker-095/freeze_hold_binding_integrity/measure_hold.py
Exit code is always 0; the verdict is in the report.
"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "evidence" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

# path -> (node, role, FROZEN pin prefix used for reporting)
HELD = {
    "schemas/af_wcc_vacuum.yaml": ("F1", "class_schema WCC", "cce9c60146d6"),
    "schemas/af_scc_c2_vacuum.yaml": ("F2a", "class_schema SCC-C2", "5476a3f2c6bc"),
    "schemas/af_scc_c0_vacuum.yaml": ("F2b", "class_schema SCC-C0", "55d0a1ea9bda"),
    "research_map/formulation_taxonomy.yaml": ("F0", "declared F0 taxonomy", "0abb9ed8a961"),
    "artifacts/formulation/formulation_taxonomy.yaml": ("F0", "class-contract supplement", "d7419b4e8963"),
}
NOW = time.strftime("%Y-%m-%dT%H:%M:%S%z")


def sha256_file(p):
    h = hashlib.sha256()
    with open(ROOT / p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure_pass():
    out = {}
    for p in HELD:
        fp = ROOT / p
        st = fp.stat()
        out[p] = {
            "sha256": sha256_file(p),
            "bytes": st.st_size,
            "mtime": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(st.st_mtime)),
            "mtime_epoch": st.st_mtime,
        }
    return out


def load_events():
    ev = []
    with open(ROOT / "research_map/events.jsonl", encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            ev.append((i, d))
    return ev


def main():
    report = {
        "probe": "W095-HOLD-BIND-INTEGRITY-03",
        "probe_at": NOW,
        "frozen_revision_reviewed": None,
        "checks": [],
        "findings": [],
        "raw": {},
    }

    frozen = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    report["frozen_revision_reviewed"] = frozen["revision"]
    pins = frozen.get("files", {})

    # ---- H8 first measurement, then a second pass for drift -------------------
    pass1 = measure_pass()
    pass2 = measure_pass()
    drift = {p: (pass1[p]["sha256"] != pass2[p]["sha256"]) for p in HELD}

    # ---- H1: measured == FROZEN rev28 pin ------------------------------------
    h1 = []
    for p, (node, role, pin) in HELD.items():
        measured = pass1[p]["sha256"]
        declared = pins.get(p, {}).get("sha256")
        h1.append({
            "id": f"H1-{node}-{Path(p).name}",
            "path": p, "role": role,
            "measured": measured, "frozen_pin": declared,
            "pass": measured == declared == pass2[p]["sha256"] if declared else False,
        })
    report["checks"].append({"id": "H1-PIN-MATCH", "pass": all(c["pass"] for c in h1),
                             "detail": h1})

    # ---- H2: no byte written after the pin event was emitted ------------------
    events = load_events()
    held_events = {}
    for idx, d in events:
        if d.get("event_type") == "artifact" and d.get("path") in HELD:
            held_events.setdefault(d["path"], []).append({
                "line": idx,
                "event_id": d.get("event_id"),
                "created_at": d.get("created_at"),
                "received_at": d.get("_received_at"),
                "sha256": d.get("sha256"),
            })
    h2 = []
    for p, (node, role, pin) in HELD.items():
        evs = held_events.get(p, [])
        pin_ev = [e for e in evs if str(e["sha256"] or "").startswith(pin)]
        latest_pin = max(pin_ev, key=lambda e: e["line"]) if pin_ev else None
        ok = latest_pin is not None
        if ok:
            # created_at is agent-reported and can be unreliable; compare epoch
            try:
                ev_epoch = time.mktime(time.strptime(latest_pin["created_at"][:19], "%Y-%m-%dT%H:%M:%S"))
            except (ValueError, TypeError):
                ev_epoch = None
            ok = ev_epoch is not None and pass1[p]["mtime_epoch"] <= ev_epoch + 1
        h2.append({"id": f"H2-{node}-{Path(p).name}", "path": p,
                   "mtime": pass1[p]["mtime"], "pin_event": latest_pin, "pass": ok})
    report["checks"].append({"id": "H2-NO-POST-EVENT-WRITE", "pass": all(c["pass"] for c in h2),
                             "detail": h2})

    # ---- H3: FROZEN.json itself is pinned by its newest artifact event --------
    frozen_disk = sha256_file("artifacts/formulation/FROZEN.json")
    fz_events = [{"line": i, "created_at": d.get("created_at"), "sha256": d.get("sha256"),
                  "event_id": d.get("event_id")}
                 for i, d in events
                 if d.get("event_type") == "artifact" and d.get("path") == "artifacts/formulation/FROZEN.json"]
    fz_latest = max(fz_events, key=lambda e: e["line"]) if fz_events else None
    h3_pass = bool(fz_latest) and str(fz_latest["sha256"] or "").startswith(frozen_disk[:12]) \
        and frozen.get("logical_artifacts", {}).get("F0-declared-taxonomy", {}).get("sha256") == pins.get("research_map/formulation_taxonomy.yaml", {}).get("sha256") \
        and frozen.get("logical_artifacts", {}).get("F0-class-contract-supplement", {}).get("sha256") == pins.get("artifacts/formulation/formulation_taxonomy.yaml", {}).get("sha256")
    report["checks"].append({"id": "H3-FROZEN-SELF", "pass": h3_pass,
                             "detail": {"measured_frozen_sha256": frozen_disk, "latest_frozen_event": fz_latest,
                                        "logical_artifacts": frozen.get("logical_artifacts")}})

    # ---- H4: map declared artifact_sha256 and runtime registry agree ----------
    rm = json.loads((ROOT / "research_map/research_map.json").read_text())
    ah = json.loads((ROOT / "runtime/state/artifact_hashes.json").read_text()).get("hashes", {})
    nodes = {}
    for g in rm.get("groups", []):
        for n in g.get("nodes", []):
            art = n.get("artifact")
            if isinstance(art, str) and art in HELD:
                nodes[art] = {"group": g.get("group_id") or g.get("id"), "status": n.get("status"),
                              "declared": n.get("artifact_sha256")}
    h4 = []
    for p, (node, role, pin) in HELD.items():
        node_dec = nodes.get(p, {}).get("declared")
        reg = (ah.get(p) or {}).get("sha256")
        if p in nodes:  # four node artifacts: map declaration and runtime registry must both agree
            ok = node_dec == pass1[p]["sha256"] and reg == pass1[p]["sha256"]
        else:  # companion supplement: no map node by design; only the FROZEN pin is required
            ok = pass1[p]["sha256"] == pins.get(p, {}).get("sha256")
        h4.append({"id": f"H4-{node}-{Path(p).name}", "path": p, "is_node_artifact": p in nodes,
                   "measured": pass1[p]["sha256"], "map_declared": node_dec, "registry": reg,
                   "pass": ok})
    report["checks"].append({"id": "H4-MAP-AND-REGISTRY", "pass": all(c["pass"] for c in h4),
                             "detail": h4})

    # ---- H5: newest-ingested artifact event carries the pin -------------------
    h5 = []
    for p, (node, role, pin) in HELD.items():
        evs = held_events.get(p, [])
        newest = max(evs, key=lambda e: e["line"]) if evs else None
        h5.append({"id": f"H5-{node}-{Path(p).name}", "path": p, "newest_event": newest,
                   "pass": bool(newest) and str(newest["sha256"] or "").startswith(pin)})
    report["checks"].append({"id": "H5-LATEST-EVENT-CARRIES-PIN", "pass": all(c["pass"] for c in h5),
                             "detail": h5})

    # ---- H6: no stale non-pin event sorts at/after the pin event by created_at
    h6 = []
    for p, (node, role, pin) in HELD.items():
        evs = held_events.get(p, [])
        pin_ev = [e for e in evs if str(e["sha256"] or "").startswith(pin)]
        if not pin_ev:
            h6.append({"id": f"H6-{node}-{Path(p).name}", "path": p, "pass": False,
                       "reason": "no pin-carrying event"})
            continue
        latest_pin = max(pin_ev, key=lambda e: e["line"])
        shadow = [e for e in evs
                  if not str(e["sha256"] or "").startswith(pin)
                  and str(e.get("created_at") or "") >= str(latest_pin.get("created_at") or "")]
        h6.append({"id": f"H6-{node}-{Path(p).name}", "path": p,
                   "pin_event": {"line": latest_pin["line"], "created_at": latest_pin["created_at"],
                                 "sha256": str(latest_pin["sha256"])[:12]},
                   "shadowing_stale_events": [
                       {"line": e["line"], "created_at": e["created_at"], "received_at": e["received_at"],
                        "sha256": str(e["sha256"])[:12], "event_id": e["event_id"]} for e in shadow],
                   "pass": not shadow})
    report["checks"].append({"id": "H6-NO-NEWER-STALE-EVENT", "pass": all(c["pass"] for c in h6),
                             "detail": h6})

    # ---- H7: F2b intra-schema bindings resolve on frozen bytes ---------------
    import yaml
    f2b = yaml.safe_load((ROOT / "schemas/af_scc_c0_vacuum.yaml").read_text())
    f0 = yaml.safe_load((ROOT / "research_map/formulation_taxonomy.yaml").read_text())
    sup = yaml.safe_load((ROOT / "artifacts/formulation/formulation_taxonomy.yaml").read_text())
    fb = f2b.get("f0_binding", {})
    ptr = f2b.get("class_contract_pointer", "")
    sup_ptr = fb.get("class_contract_supplement_pointer", "")
    ptr_ok = ptr.startswith("research_map/formulation_taxonomy.yaml#classes.") and \
        ptr.split("#", 1)[1].split(".", 1)[1] in f0.get("classes", {})
    sup_ptr_ok = sup_ptr.startswith("artifacts/formulation/formulation_taxonomy.yaml#class_contracts.") and \
        sup_ptr.split("#", 1)[1].split(".", 1)[1] in sup.get("class_contracts", {})
    declared_evidence = fb.get("consistency_evidence_sha256")
    ev_path = fb.get("consistency_evidence", "artifacts/formulation/evidence/taxonomy_consistency.json")
    canonical_evidence = sha256_file(ev_path) if (ROOT / ev_path).exists() else None
    enriched = "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json"
    enriched_sha = sha256_file(enriched) if (ROOT / enriched).exists() else None
    h7 = {
        "declared_f0_sha256": fb.get("declared_f0_sha256"),
        "frozen_f0_pin": pins.get("research_map/formulation_taxonomy.yaml", {}).get("sha256"),
        "f0_binding_pass": fb.get("declared_f0_sha256") == pins.get("research_map/formulation_taxonomy.yaml", {}).get("sha256"),
        "class_contract_pointer": ptr, "pointer_resolves": ptr_ok,
        "supplement_pointer": sup_ptr, "supplement_pointer_resolves": sup_ptr_ok,
        "declared_consistency_evidence": ev_path,
        "declared_consistency_evidence_sha256": declared_evidence,
        "canonical_evidence_measured_sha256": canonical_evidence,
        "frozen_evidence_pin": pins.get(ev_path, {}).get("sha256"),
        "canonical_path_carries_declared_hash": declared_evidence == canonical_evidence,
        "enriched_run_artifact": enriched, "enriched_run_measured_sha256": enriched_sha,
        "enriched_matches_declared": declared_evidence == enriched_sha,
    }
    h7["pass"] = bool(h7["f0_binding_pass"] and ptr_ok and sup_ptr_ok and h7["canonical_path_carries_declared_hash"])
    report["checks"].append({"id": "H7-F2B-INTRA-BINDINGS", "pass": h7["pass"], "detail": h7})

    # ---- H8: zero drift across the two passes --------------------------------
    report["checks"].append({"id": "H8-ZERO-DRIFT", "pass": not any(drift.values()),
                             "detail": {"drift": drift, "pass1": pass1, "pass2": pass2}})

    # ---- findings -------------------------------------------------------------
    if not report["checks"][5]["pass"]:
        report["findings"].append({
            "id": "F-EVENT-1", "severity": "major", "check": "H6-NO-NEWER-STALE-EVENT",
            "finding": "For F1/F2a/F2b and the canonical F0 taxonomy, the newest artifact events by "
                       "agent-reported created_at are stale rev11/rev4 declarations (created_at "
                       "2026-09-12T00:44:00+08:00, ingested 00:20:09) that shadow the actual rev12/rev5 pin "
                       "events (created_at 00:35:52). The map's current declarations are correct; a consumer "
                       "that resolves 'latest by created_at', or a reader of the accepted stream, binds the "
                       "superseded hashes. Fires the astra-life04 falsifier 'a declared hash left at rev11' in "
                       "the event stream even though the byte-level hold is intact.",
            "falsifier": "a controller re-scan in which every held path's newest-by-created_at artifact event "
                         "carries the FROZEN rev28 pin (stale future-dated events tombstoned or excluded)",
        })
    if not report["checks"][6]["pass"]:
        report["findings"].append({
            "id": "F-EVID-1", "severity": "major", "check": "H7-F2B-INTRA-BINDINGS",
            "status": "carried from W095-F2B-BIND-INTEGRITY-02, unchanged",
            "finding": "F2b rev12 declares f0_binding.consistency_evidence_sha256=675a99d0d25b (enriched run, "
                       "present at artifacts/worker-086/gform_rev12/pinned/) while the declared evidence path "
                       "artifacts/formulation/evidence/taxonomy_consistency.json measures 9e335e9ba1bf and is "
                       "the FROZEN rev28 pin. Root cause: check_taxonomy_consistency.py rewrites the canonical "
                       "path unconditionally with a summary format lacking the hash fields.",
            "falsifier": "a revision whose declared consistency-evidence hash resolves on the canonical path, "
                         "or an explicit controller disposition naming the enriched run as the evidence artifact "
                         "of record and re-pinning it",
        })
    sup_measured = pass1["artifacts/formulation/formulation_taxonomy.yaml"]["sha256"]
    sup_reg = (ah.get("artifacts/formulation/formulation_taxonomy.yaml") or {}).get("sha256")
    if not sup_reg and sup_measured == pins.get("artifacts/formulation/formulation_taxonomy.yaml", {}).get("sha256"):
        report["findings"].append({
            "id": "F-REG-1", "severity": "minor", "check": "H4-MAP-AND-REGISTRY",
            "finding": "The class-contract supplement artifacts/formulation/formulation_taxonomy.yaml is pinned "
                       "in FROZEN rev28 logical_artifacts and carries an artifact event, but has no entry in "
                       "runtime/state/artifact_hashes.json hashes (the four node artifacts do). A reviewer "
                       "resolving the supplement pin through the runtime registry gets nothing.",
            "falsifier": "an artifact_hashes.json entry for the supplement matching the FROZEN pin",
        })
    if report["checks"][0]["pass"] and report["checks"][1]["pass"] and report["checks"][2]["pass"] \
            and report["checks"][3]["pass"] and report["checks"][4]["pass"] and report["checks"][7]["pass"]:
        report["findings"].append({
            "id": "F-HOLD-1", "severity": "info", "check": "H1/H2/H3/H4/H5/H8",
            "finding": "astra-life04-freeze-hold byte-level integrity CONFIRMED at FROZEN rev28: all five held "
                       "paths measure their pins (two passes, zero drift), no held path was written after its pin "
                       "event, FROZEN.json's own bytes match its newest artifact event, the map declares the four "
                       "node pins and the runtime registry agrees, and the newest-ingested artifact event carries "
                       "the pin for all five paths.",
            "falsifier": "any held path whose bytes move, whose newest event diverges from the pin, or whose "
                         "declared hash is left stale",
        })

    report["summary"] = {
        "held_paths": len(HELD),
        "checks": len(report["checks"]),
        "passed": sum(1 for c in report["checks"] if c["pass"]),
        "failed": [c["id"] for c in report["checks"] if not c["pass"]],
        "major": sum(1 for f in report["findings"] if f["severity"] == "major"),
        "minor": sum(1 for f in report["findings"] if f["severity"] == "minor"),
        "info": sum(1 for f in report["findings"] if f["severity"] == "info"),
    }
    (OUT / "hold_probe_report.json").write_text(json.dumps(report, indent=2) + "\n")
    json.dump({p: pass1[p] for p in HELD}, open(OUT / "held_path_hashes.json", "w"), indent=2)
    json.dump(held_events, open(OUT / "event_stream_slice.json", "w"), indent=2)
    json.dump({"nodes": nodes, "registry": {p: ah.get(p) for p in HELD}}, open(OUT / "map_and_registry.json", "w"), indent=2)
    json.dump({"f2b_f0_binding": fb, "f2b_class_contract_pointer": ptr, "frozen_revision": frozen["revision"],
               "frozen_pins": {p: pins.get(p, {}).get("sha256") for p in HELD},
               "logical_artifacts": frozen.get("logical_artifacts")}, open(OUT / "f2b_and_frozen_slice.json", "w"), indent=2)
    print(json.dumps(report["summary"], indent=2))
    print("failed checks:", report["summary"]["failed"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
