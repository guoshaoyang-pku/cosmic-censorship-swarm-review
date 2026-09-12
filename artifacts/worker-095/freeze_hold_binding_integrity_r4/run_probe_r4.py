#!/usr/bin/env python3
"""W095-HOLD-BIND-INTEGRITY-06 -- freeze-hold / class-binding integrity re-probe (r4).

Class-bound task: node F2b, class AF-SCC-C0-VAC-GEN, gate G-FORM.
Successor to W095-HOLD-BIND-INTEGRITY-05 (freeze_hold_binding_integrity_r3/), whose
next_falsifier had three conditions:

  (a) under the read path actually used to resolve "latest artifact per path" every held
      path resolves to the FROZEN rev29 pin sha256 (no created_at shadow, no future-dated
      win, defined fallback for events lacking _received_at);
  (b) F2b f0_binding.consistency_evidence_sha256 equals the measured sha256 of the path it
      names, stably across two consecutive probes;
  (c) all 50 FROZEN pins and FROZEN.json itself stay drift-free.

This probe re-measures (a)-(c) at the current manifest revision after the 00:57:48 ingest
of the lead-formulation rev29 pin announcements. READ-ONLY: no canonical byte is written.
Outputs evidence/raw/*.json; verdict.json is assembled by the caller from the report.

Checks
  R1 PIN-MATCH         50/50 manifest pins vs disk bytes
  R2 MANIFEST-SELF     FROZEN.json measured vs its own announcement (self-ref excluded)
  R3 ANNOUNCE          artifact event announces each held pin (HF-05-01 re-test)
  R4 ORDER-RESOLUTION  created_at-max / file-order-last / _received_at-max vs pin per path
  R5 DECLARED-EVIDENCE F2b/F2a/F1 f0_binding declared vs measured, two consecutive reads
  R6 NO-PROBE-DRIFT    input hashes re-measured at probe end
  R7 CLASS-BINDING     F2b class_id + class_contract_pointer resolves in canonical F0
  R8 MAP-CONTEXT       live map gate/node slice (informational)
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RAW = Path(__file__).resolve().parent / "evidence" / "raw"
CST = timezone(timedelta(hours=8))

FROZEN = ROOT / "artifacts" / "formulation" / "FROZEN.json"
EVENTS = ROOT / "research_map" / "events.jsonl"
MAP = ROOT / "research_map" / "research_map.json"
F2B = ROOT / "schemas" / "af_scc_c0_vacuum.yaml"
F2A = ROOT / "schemas" / "af_scc_c2_vacuum.yaml"
F1 = ROOT / "schemas" / "af_wcc_vacuum.yaml"
TAXONOMY = ROOT / "research_map" / "formulation_taxonomy.yaml"

# five held paths of the freeze-hold probe + the manifest itself
HELD = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
]
SCHEMAS = {"F2b": F2B, "F2a": F2A, "F1": F1}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def digest_or_none(path: Path):
    try:
        return sha256(path) if path.is_file() else None
    except OSError:
        return None


def parse_ts(value: str):
    try:
        t = datetime.fromisoformat(str(value))
        return t if t.tzinfo else t.replace(tzinfo=CST)
    except Exception:
        return None


def load_stream():
    """events.jsonl in file order (this is the order apply_events.py consumes)."""
    out = []
    for lineno, line in enumerate(EVENTS.read_text(errors="replace").splitlines(), 1):
        if not line.strip():
            continue
        try:
            out.append((lineno, json.loads(line)))
        except ValueError:
            continue
    return out


def artifact_events(stream, path):
    return [(i, ev) for i, ev in stream
            if ev.get("event_type") == "artifact" and ev.get("path") == path]


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    probe_at = datetime.now(CST).isoformat(timespec="seconds")
    start = {
        "FROZEN.json": digest_or_none(FROZEN),
        "events.jsonl": digest_or_none(EVENTS),
        "research_map.json": digest_or_none(MAP),
        "schemas/af_wcc_vacuum.yaml": digest_or_none(F1),
        "schemas/af_scc_c2_vacuum.yaml": digest_or_none(F2A),
        "schemas/af_scc_c0_vacuum.yaml": digest_or_none(F2B),
        "research_map/formulation_taxonomy.yaml": digest_or_none(TAXONOMY),
    }
    stream = load_stream()
    manifest = json.loads(FROZEN.read_text())
    pins = manifest.get("files", {})
    rev = manifest.get("revision")

    report = {
        "probe": "W095-HOLD-BIND-INTEGRITY-06",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "probe_at": probe_at,
        "frozen_revision": rev,
        "frozen_manifest_sha256": start["FROZEN.json"],
        "frozen_at": manifest.get("frozen_at"),
        "stream_lines": len(stream),
        "checks": {},
        "findings": [],
        "hard_failures": [],
    }

    # ---------------- R1: 50-pin drift census ----------------
    census = {"total": len(pins), "match": 0, "mismatch": [], "missing": []}
    measured = {}
    for p, meta in pins.items():
        want = meta.get("sha256")
        got = digest_or_none(ROOT / p)
        measured[p] = got
        if got is None:
            census["missing"].append(p)
        elif got == want:
            census["match"] += 1
        else:
            census["mismatch"].append({"path": p, "pin": want, "measured": got})
    census["clean"] = not census["mismatch"] and not census["missing"]
    report["checks"]["R1-PIN-MATCH"] = "PASS" if census["clean"] else "FAIL"
    (RAW / "frozen_drift_r4.json").write_text(
        json.dumps({"probe_at": probe_at, "revision": rev, "census": census},
                   indent=2, sort_keys=True))

    # ---------------- R2: manifest self + announcement ----------------
    fz_ev = [(i, ev) for i, ev in stream
             if ev.get("event_type") == "artifact"
             and ev.get("path") == "artifacts/formulation/FROZEN.json"]
    fz_pin_ann = [ev for _, ev in fz_ev
                  if str(ev.get("sha256", ""))[:12] == str(start["FROZEN.json"])[:12]]
    r2 = {
        "measured_sha256": start["FROZEN.json"],
        "declared_self_reference": manifest.get("self_reference"),
        "artifact_events_for_manifest": len(fz_ev),
        "announcements_matching_measured": [
            {"event_id": e.get("event_id"), "actor": e.get("actor"),
             "created_at": e.get("created_at"), "_received_at": e.get("_received_at")}
            for e in fz_pin_ann],
    }
    r2["pass"] = bool(fz_pin_ann)
    report["checks"]["R2-MANIFEST-SELF"] = "PASS" if r2["pass"] else "FAIL"
    (RAW / "manifest_self_r4.json").write_text(json.dumps(r2, indent=2, sort_keys=True))

    # ---------------- R3: pin announcements for held paths ----------------
    ann = {}
    for p in HELD:
        want = pins.get(p, {}).get("sha256")
        evs = artifact_events(stream, p)
        matching = [(i, ev) for i, ev in evs
                    if want and str(ev.get("sha256", "")).startswith(want[:12])]
        newest_by_created = max(evs, key=lambda x: (parse_ts(x[1].get("created_at")) or
                                                    datetime.min.replace(tzinfo=CST), x[0])) if evs else None
        ann[p] = {
            "pin": want,
            "artifact_events": len(evs),
            "announcements": [
                {"event_id": ev.get("event_id"), "actor": ev.get("actor"),
                 "created_at": ev.get("created_at"),
                 "_received_at": ev.get("_received_at"),
                 "line": i}
                for i, ev in matching],
            "announced": bool(matching),
            "newest_created_at_event": (
                {"event_id": newest_by_created[1].get("event_id"),
                 "sha256": str(newest_by_created[1].get("sha256"))[:12],
                 "created_at": newest_by_created[1].get("created_at"),
                 "actor": newest_by_created[1].get("actor"),
                 "_received_at": newest_by_created[1].get("_received_at"),
                 "line": newest_by_created[0]} if newest_by_created else None),
            "newest_created_at_is_pin": bool(
                newest_by_created and want
                and str(newest_by_created[1].get("sha256", "")).startswith(want[:12])),
        }
    unannounced = [p for p in HELD if not ann[p]["announced"]]
    r3 = {"per_path": ann, "unannounced": unannounced,
          "frozen_manifest_announced": r2["pass"]}
    r3["pass"] = not unannounced and r2["pass"]
    report["checks"]["R3-ANNOUNCE"] = "PASS" if r3["pass"] else "FAIL"
    (RAW / "pin_announcements_r4.json").write_text(json.dumps(r3, indent=2, sort_keys=True))

    # ---------------- R4: ordering resolution per held path ----------------
    order = {}
    for p in HELD:
        want = pins.get(p, {}).get("sha256")
        evs = artifact_events(stream, p)

        def is_pin(ev):
            return bool(want) and str(ev.get("sha256", "")).startswith(want[:12])

        by_file = evs[-1][1] if evs else None
        by_created = None
        if evs:
            by_created = max(evs, key=lambda x: (parse_ts(x[1].get("created_at")) or
                                                 datetime.min.replace(tzinfo=CST), x[0]))[1]
        ingested = [ev for _, ev in evs if ev.get("_received_at")]
        by_recv = max(ingested, key=lambda e: str(e.get("_received_at"))) if ingested else None
        pin_ev = (max(matching, key=lambda x: (parse_ts(x[1].get("created_at")) or
                                               datetime.min.replace(tzinfo=CST), x[0]))[1]
                  if matching else None)
        pin_at = parse_ts(pin_ev.get("created_at")) if pin_ev else None
        shadows = [{"event_id": ev.get("event_id"), "sha256": str(ev.get("sha256"))[:12],
                    "created_at": ev.get("created_at"), "_received_at": ev.get("_received_at"),
                    "line": i, "future_dated": bool(
                        parse_ts(ev.get("created_at")) and
                        parse_ts(ev.get("created_at")) > datetime.now(CST)),
                    "not_ingested": "_received_at" not in ev}
                   for i, ev in evs if not is_pin(ev) and pin_at and
                   (parse_ts(ev.get("created_at")) or datetime.min.replace(tzinfo=CST)) >= pin_at]
        shadows.sort(key=lambda s: (parse_ts(s["created_at"]) or
                                    datetime.min.replace(tzinfo=CST), s["line"]))
        order[p] = {
            "pin": want,
            "file_order_last": {"event_id": by_file.get("event_id"), "sha256": str(by_file.get("sha256"))[:12],
                                "is_pin": is_pin(by_file)} if by_file else None,
            "created_at_max": {"event_id": by_created.get("event_id"), "sha256": str(by_created.get("sha256"))[:12],
                               "is_pin": is_pin(by_created)} if by_created else None,
            "received_at_max": {"event_id": by_recv.get("event_id"), "sha256": str(by_recv.get("sha256"))[:12],
                                "is_pin": is_pin(by_recv)} if by_recv else None,
            "created_at_shadow": bool(by_created and not is_pin(by_created)),
            "newest_shadow": shadows[-1] if shadows else None,
        }
    shadowed = [p for p in HELD if order[p]["created_at_shadow"]]
    resolved_by_file = all(order[p]["file_order_last"] and order[p]["file_order_last"]["is_pin"]
                           for p in HELD)
    resolved_by_recv = all(order[p]["received_at_max"] and order[p]["received_at_max"]["is_pin"]
                           for p in HELD)
    r4 = {"per_path": order, "created_at_shadow_paths": shadowed,
          "file_order_resolves_all_to_pin": resolved_by_file,
          "received_at_resolves_all_to_pin": resolved_by_recv}
    r4["pass"] = resolved_by_file and resolved_by_recv and not shadowed
    report["checks"]["R4-ORDER-RESOLUTION"] = "PASS" if r4["pass"] else "FAIL"
    (RAW / "order_resolution_r4.json").write_text(json.dumps(r4, indent=2, sort_keys=True))

    # ---------------- R5: declared evidence resolution (two consecutive reads) ----------------
    try:
        import yaml
    except Exception as exc:  # pragma: no cover
        print(f"PyYAML required: {exc}", file=sys.stderr)
        return 2
    decl = {}
    for label, path in SCHEMAS.items():
        reads = []
        for _ in range(2):
            doc = yaml.safe_load(path.read_text())
            fb = doc.get("f0_binding") or {}
            ev_path = fb.get("consistency_evidence")
            ev_meas = digest_or_none(ROOT / ev_path) if ev_path else None
            f0_path = fb.get("declared_f0_artifact")
            f0_meas = digest_or_none(ROOT / f0_path) if f0_path else None
            reads.append({
                "class_id": doc.get("class_id"),
                "declared_f0_artifact": f0_path,
                "declared_f0_sha256": fb.get("declared_f0_sha256"),
                "measured_f0_sha256": f0_meas,
                "f0_match": bool(f0_meas and fb.get("declared_f0_sha256") == f0_meas),
                "consistency_evidence": ev_path,
                "declared_evidence_sha256": fb.get("consistency_evidence_sha256"),
                "measured_evidence_sha256": ev_meas,
                "evidence_match": bool(ev_meas and fb.get("consistency_evidence_sha256") == ev_meas),
            })
        decl[label] = {
            "read_1": reads[0], "read_2": reads[1],
            "stable_across_two_reads": reads[0] == reads[1],
            "pass": bool(reads[0]["f0_match"] and reads[0]["evidence_match"]
                         and reads[1]["f0_match"] and reads[1]["evidence_match"]
                         and reads[0] == reads[1]),
        }
    r5 = {"per_class": decl,
          "pass": all(decl[k]["pass"] for k in decl)}
    report["checks"]["R5-DECLARED-EVIDENCE"] = "PASS" if r5["pass"] else "FAIL"
    (RAW / "declared_evidence_r4.json").write_text(json.dumps(r5, indent=2, sort_keys=True))

    # ---------------- R7: F2b class binding ----------------
    f2b_doc = yaml.safe_load(F2B.read_text())
    tax = yaml.safe_load(TAXONOMY.read_text())
    pointer = f2b_doc.get("class_contract_pointer", "")
    ptr_path, _, ptr_key = pointer.partition("#")
    resolved = None
    if ptr_path and ptr_key:
        node = tax
        ok = True
        for part in ptr_key.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                ok = False
                break
        resolved = ok
    r7 = {
        "node_id": "F2b",
        "declared_class_id": f2b_doc.get("class_id"),
        "expected_class_id": "AF-SCC-C0-VAC-GEN",
        "class_id_match": f2b_doc.get("class_id") == "AF-SCC-C0-VAC-GEN",
        "class_contract_pointer": pointer,
        "pointer_target": ptr_path,
        "pointer_key": ptr_key,
        "pointer_resolves_in_canonical_f0": bool(resolved),
        "taxonomy_class_keys": sorted((tax.get("classes") or {}).keys()),
        "taxonomy_revision": tax.get("revision"),
    }
    r7["pass"] = bool(r7["class_id_match"] and r7["pointer_resolves_in_canonical_f0"])
    report["checks"]["R7-CLASS-BINDING"] = "PASS" if r7["pass"] else "FAIL"
    (RAW / "f2b_binding_r4.json").write_text(json.dumps(r7, indent=2, sort_keys=True))

    # ---------------- R8 / stream hygiene: non-ingested + future-dated cohort ----------------
    no_recv = [(i, ev) for i, ev in stream if "_received_at" not in ev]
    now = datetime.now(CST)
    future = [{"event_id": ev.get("event_id"), "actor": ev.get("actor"),
               "created_at": ev.get("created_at"), "line": i,
               "_received_at": ev.get("_received_at")}
              for i, ev in stream
              if (parse_ts(ev.get("created_at")) or now) > now]
    hygiene = {
        "stream_lines": len(stream),
        "without_received_at": len(no_recv),
        "without_received_at_lines_min": min((i for i, _ in no_recv), default=None),
        "without_received_at_lines_max": max((i for i, _ in no_recv), default=None),
        "future_dated": len(future),
        "future_dated_max_created_at": max((f["created_at"] for f in future), default=None),
        "future_dated_examples": sorted(future, key=lambda f: f["created_at"], reverse=True)[:5],
        "shadow_event_not_ingested": {
            p: order[p]["newest_shadow"]
            for p in HELD if order[p]["created_at_shadow"] and order[p]["newest_shadow"]
            and order[p]["newest_shadow"]["not_ingested"]},
    }
    report["checks"]["R9-STREAM-HYGIENE"] = "INFO"
    (RAW / "stream_hygiene_r4.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True))

    # ---------------- R8: map context ----------------
    m = json.loads(MAP.read_text())
    nodes = {}
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            if n.get("id") in ("F0", "F1", "F2a", "F2b"):
                nodes[n["id"]] = {k: n.get(k) for k in
                                  ("id", "status", "artifact", "artifact_sha256_measured",
                                   "declared_hash_matches_measured", "validation_status")}
    gate_rows = [{"gate_id": g.get("gate_id"), "scope": g.get("scope"), "verdict": g.get("verdict")}
                 for g in m.get("gates", []) if g.get("gate_id") in ("G-F0", "G-FORM")]
    applied = set(m.get("applied_event_ids", []))
    ctx = {
        "map_updated_at": m.get("updated_at"),
        "map_sha256": start["research_map.json"],
        "gate_rows": gate_rows,
        "node_rows": nodes,
        "pin_announcements_applied_to_map": {
            p: [a["event_id"] for a in ann[p]["announcements"] if a["event_id"] in applied]
            for p in HELD},
        "numerics_lock": m.get("numerics_lock"),
        "frozen_artifacts_active": [
            {"path": f.get("path"), "sha256": str(f.get("sha256"))[:12], "active": f.get("active")}
            for f in m.get("frozen_artifacts", []) if f.get("active")],
    }
    (RAW / "map_gate_slice_r4.json").write_text(json.dumps(ctx, indent=2, sort_keys=True))

    # ---------------- R6: no probe drift ----------------
    # Pinned artifacts must not move during the probe. The live stream and map grow by
    # design (traffic continues); their movement is INFO, not a hold defect.
    end = {k: digest_or_none(ROOT / k) for k in start}
    pinned_now = {p: digest_or_none(ROOT / p) for p in pins}
    pinned_drift = {p: {"pin": pins[p].get("sha256"), "measured_at_end": pinned_now[p]}
                    for p in pins if pins[p].get("sha256") != pinned_now[p]}
    live = {k: {"start": start[k], "end": end[k], "changed": start[k] != end[k]}
            for k in ("events.jsonl", "research_map.json")}
    drift = {
        "pinned_artifact_drift": pinned_drift,
        "live_input_movement": live,
        "live_input_note": ("events.jsonl and research_map.json grow while the swarm runs; "
                            "movement is expected and does not void a point-in-time probe"),
    }
    report["checks"]["R6-NO-PROBE-DRIFT"] = "PASS" if not pinned_drift else "FAIL"
    report["live_input_movement"] = live
    (RAW / "probe_drift_r4.json").write_text(
        json.dumps({"probe_at": probe_at, "drift": drift}, indent=2, sort_keys=True))

    # ---------------- findings ----------------
    if rev != 29:
        report["findings"].append({
            "id": "F-06-REV", "severity": "info",
            "finding": f"FROZEN revision is {rev} (not the rev29 window of the predecessor "
                       f"probe); the re-probe is valid at this revision."})
    report["findings"].append({
        "id": "F-06-01", "severity": "info" if r3["pass"] else "hard",
        "finding": ("HF-05-01 re-test: all five held paths and FROZEN.json now have an artifact "
                    "event in the accepted stream carrying the FROZEN pin sha256 "
                    "(lead-form-20260912T005743-00..06, ingested 00:57:48). The rev29 "
                    "change_protocol announcement gap is REPAIRED.")
        if r3["pass"] else "HF-05-01 re-test FAILED: " + str(unannounced)})
    if shadowed:
        report["findings"].append({
            "id": "HF-06-01", "severity": "hard",
            "finding": ("Resolution-by-created_at still binds stale bytes for "
                        f"{len(shadowed)}/5 held paths: "
                        + "; ".join(
                            f"{p} -> {order[p]['created_at_max']['sha256']} "
                            f"({order[p]['created_at_max']['event_id']})"
                            for p in shadowed)
                        + ". File order and _received_at order both resolve to the pin, so the "
                          "hold is intact on disk; the defect is that no single ordering rule is "
                          "declared for 'latest artifact per path' and the stream contains "
                          f"{len(no_recv)} events with no _received_at for which the recommended "
                          "fallback is undefined.")})
        report["hard_failures"].append("HF-06-01")
    if hygiene["shadow_event_not_ingested"]:
        report["findings"].append({
            "id": "HF-06-02", "severity": "hard",
            "finding": ("Future-dated, non-ingested stale artifact event shadows the F2b pin: "
                        + json.dumps(hygiene["shadow_event_not_ingested"]))})
        report["hard_failures"].append("HF-06-02")
    if not r5["pass"]:
        report["findings"].append({
            "id": "HF-06-03", "severity": "hard",
            "finding": "f0_binding declared/measured mismatch at: "
                       + ", ".join(k for k in decl if not decl[k]["pass"])})
        report["hard_failures"].append("HF-06-03")
    if not r7["pass"]:
        report["findings"].append({
            "id": "HF-06-04", "severity": "hard",
            "finding": "F2b class binding failed: " + json.dumps(r7)[:400]})
        report["hard_failures"].append("HF-06-04")
    if not census["clean"]:
        report["findings"].append({"id": "HF-06-05", "severity": "hard",
                                   "finding": f"pin drift: {census['mismatch'][:3]}"})
        report["hard_failures"].append("HF-06-05")

    report["verdict"] = "accept" if not report["hard_failures"] else "revise"
    report["counts_as_full_schema_verdict"] = False
    report["next_falsifier"] = (
        "A re-probe in which (a) the read path that resolves 'latest artifact per path' is "
        "declared in the repo and every held path resolves to the FROZEN pin under it, "
        "including for events that carry no _received_at and for events whose agent-declared "
        "created_at is future-dated (no created_at shadow on any held path); (b) F2b "
        "f0_binding declared evidence == measured evidence stably across two consecutive "
        "probes; (c) all pins and FROZEN.json remain drift-free; (d) F2b class_id is "
        "AF-SCC-C0-VAC-GEN and class_contract_pointer resolves in the canonical F0 taxonomy. "
        "Any canonical byte move voids this window, not the finding.")
    (RAW / "probe_report_r4.json").write_text(json.dumps(report, indent=2, sort_keys=True))

    print(json.dumps({k: report["checks"][k] for k in sorted(report["checks"])}, indent=2))
    print("verdict:", report["verdict"], "hard:", report["hard_failures"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
