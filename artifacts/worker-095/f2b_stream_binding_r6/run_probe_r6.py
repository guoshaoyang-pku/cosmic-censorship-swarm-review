#!/usr/bin/env python3
"""W095-F2B-STREAM-BINDING-R6-VERIFY-01 -- accepted-stream binding integrity for the held F2b pin.

Class-bound task: node F2b, class AF-SCC-C0-VAC-GEN, gate G-FORM.  READ-ONLY probe:
no canonical byte is written; all outputs go under this artifact directory.

Successor to W095-HOLD-BIND-INTEGRITY-06 (freeze_hold_binding_integrity_r4/), whose
next_falsifier condition (a) is still open at the stream level:

  "the read path that resolves 'latest artifact per path' is declared in the repo and
   every held path resolves to the FROZEN pin under it, including for events that carry
   no _received_at and for events whose agent-declared created_at is future-dated"

r4 measured the 5 held paths under three ordering rules and found the created_at shadow.
It did NOT measure (i) whether the future-dated events are already APPLIED to
research_map.json, or (ii) where the future-dated block came from and when it was written.

Checks
  R1 PIN-MATCH        live sha256 of the 5 held paths + F2b mirror vs FROZEN rev29 pins
  R2 F2B-RESOLUTION   latest artifact event per rule (file order / _received_at / created_at)
                      for schemas/af_scc_c0_vacuum.yaml and its mirror
  R3 FUTURE-COHORT    every event whose created_at is after the pinned probe instant:
                      line, actor, type, outbox provenance, applied status, map materialization
  R4 BLOCK-PROVENANCE provenance + write-time of the deepseek-flash-06 future block
  R5 APPLIED-EFFECTS  which cohort events are in applied_event_ids and in the live map arrays
  R6 CONTROLS         benign/mutant sandbox streams; double-run determinism
  R7 NO-PROBE-DRIFT   input hashes re-measured at probe end
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RAW = HERE / "evidence" / "raw"
SANDBOX = HERE / "sandbox"
CST = timezone(timedelta(hours=8))

FROZEN = ROOT / "artifacts" / "formulation" / "FROZEN.json"
EVENTS = ROOT / "research_map" / "events.jsonl"
MAP = ROOT / "research_map" / "research_map.json"
TAXONOMY = ROOT / "research_map" / "formulation_taxonomy.yaml"
OUTBOX = ROOT / "comms" / "outbox"

HELD = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
]
F2B_PATHS = [
    "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
]
# the future-dated block identified by r4's HF-06-02 (lines in events.jsonl)
BLOCK_IDS = [
    "w06-20260912T0115-f2b-rev6",
    "w06-20260912T0115-f2b-status",
    "w06-20260912T0115-a1-corpus-rev6",
    "w06-20260912T0115-a1-gateruns-rev6",
    "w06-20260912T0115-a1-blindspot-rev6",
    "w06-20260912T0115-a1-claim-adopted",
    "w06-20260912T0115-a1-blocker-freeze",
    "w06-20260912T0125-freeze-resolved",
    "w06-20260912T0125-replication",
    "w06-20260912T0135-submission",
    "w06-20260912T0150-heldout-corpus",
    "w06-20260912T0150-heldout-report",
    "w06-20260912T0150-heldout-status",
    "w06-20260912T0150-heldout-claim",
    "w06-20260912T0200-freeze-observation",
]


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


def parse_ts(value):
    if not isinstance(value, str):
        return None
    try:
        t = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=CST)


def load_stream(path: Path):
    out = []
    for lineno, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        if not line.strip():
            continue
        try:
            out.append((lineno, json.loads(line)))
        except ValueError:
            continue
    return out


def outbox_index():
    """event_id -> {file, file_mtime, claimed created_at} over every outbox file."""
    idx = {}
    if not OUTBOX.exists():
        return idx
    for p in sorted(x for x in OUTBOX.rglob("*") if x.is_file() and not x.name.startswith("._")):
        try:
            text = p.read_text(errors="replace")
        except OSError:
            continue
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=CST).isoformat(timespec="seconds")
        for line in text.splitlines():
            line = line.strip()
            if not (line.startswith("{") and line.endswith("}")):
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue
            eid = e.get("event_id")
            if eid and eid not in idx:
                idx[eid] = {"file": str(p.relative_to(ROOT)), "file_mtime": mtime,
                            "created_at": e.get("created_at")}
    return idx


def map_locations(node, event_id, path="$", hits=None):
    """JSON paths in the map where event_id occurs (bounded, exact string match)."""
    if hits is None:
        hits = []
    if isinstance(node, dict):
        for k, v in node.items():
            map_locations(v, event_id, f"{path}.{k}", hits)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            map_locations(v, event_id, f"{path}[{i}]", hits)
    elif isinstance(node, str) and node == event_id:
        hits.append(path)
    return hits


def resolve_latest(stream, path, pin_sha, probe_at):
    """Latest artifact event naming `path` under each ordering rule."""
    evs = [(i, e) for i, e in stream
           if e.get("event_type") == "artifact" and e.get("path") == path]
    out = {"path": path, "pin_sha256": pin_sha, "n_artifact_events": len(evs), "rules": {}}

    def rec(rule, ev, line):
        return {"rule": rule, "event_id": ev.get("event_id"), "line": line,
                "sha256": ev.get("sha256"), "created_at": ev.get("created_at"),
                "_received_at": ev.get("_received_at"),
                "future_dated": bool(parse_ts(ev.get("created_at")) and
                                     parse_ts(ev.get("created_at")) > probe_at),
                "resolves_to_pin": ev.get("sha256") == pin_sha}

    if evs:
        i, e = evs[-1]
        out["rules"]["file_order_last"] = rec("file_order_last", e, i)
        ingested = [(i, e) for i, e in evs if e.get("_received_at")]
        if ingested:
            i, e = max(ingested, key=lambda t: str(t[1].get("_received_at")))
            out["rules"]["received_at_max"] = rec("received_at_max", e, i)
        else:
            out["rules"]["received_at_max"] = None
        dated = [(i, e) for i, e in evs if parse_ts(e.get("created_at"))]
        if dated:
            i, e = max(dated, key=lambda t: parse_ts(t[1]["created_at"]))
            out["rules"]["created_at_max"] = rec("created_at_max", e, i)
        else:
            out["rules"]["created_at_max"] = None
        # fail-closed rule proposed by r4: received_at first, then file order; created_at
        # never confers precedence.
        if ingested:
            i, e = max(ingested, key=lambda t: str(t[1].get("_received_at")))
        else:
            i, e = evs[-1]
        out["rules"]["fail_closed_received_then_file"] = rec("fail_closed_received_then_file", e, i)
    out["all_rules_resolve_to_pin"] = all(
        r is not None and r["resolves_to_pin"] for r in out["rules"].values())
    return out


def future_shadow(stream, path, pin_sha, probe_at):
    hits = []
    for i, e in evs_iter_artifact(stream, path):
        c = parse_ts(e.get("created_at"))
        if c and c > probe_at and e.get("sha256") != pin_sha:
            hits.append({"event_id": e.get("event_id"), "line": i,
                         "created_at": e.get("created_at"), "sha256": e.get("sha256"),
                         "_received_at": e.get("_received_at")})
    return hits


def evs_iter_artifact(stream, path):
    for i, e in stream:
        if e.get("event_type") == "artifact" and e.get("path") == path:
            yield i, e


def control_run(probe_at):
    """Instrument controls on synthetic sandbox streams (never touches canonical bytes)."""
    pin = "a" * 64
    stale = "b" * 64
    benign = [
        {"event_id": "ctl-benign-1", "event_type": "artifact", "created_at": "2026-09-12T00:10:00+08:00",
         "_received_at": "2026-09-12T00:10:05+08:00", "path": "schemas/af_scc_c0_vacuum.yaml", "sha256": pin},
        {"event_id": "ctl-benign-2", "event_type": "artifact", "created_at": "2026-09-12T00:11:00+08:00",
         "_received_at": "2026-09-12T00:11:02+08:00", "path": "schemas/af_scc_c0_vacuum.yaml", "sha256": pin},
    ]
    mutant = benign + [
        {"event_id": "ctl-mutant-shadow", "event_type": "artifact",
         "created_at": "2026-09-12T04:00:00+08:00", "path": "schemas/af_scc_c0_vacuum.yaml",
         "sha256": stale, "supersedes": "schemas/af_scc_c0_vacuum.yaml@" + pin[:12]},
    ]
    res = {}
    for name, rows in (("benign", benign), ("mutant", mutant)):
        stream = list(enumerate(rows, 1))
        r = resolve_latest(stream, "schemas/af_scc_c0_vacuum.yaml", pin, probe_at)
        res[name] = {
            "shadow_events": future_shadow(stream, "schemas/af_scc_c0_vacuum.yaml", pin, probe_at),
            "created_at_max_sha": (r["rules"].get("created_at_max") or {}).get("sha256"),
            "fail_closed_sha": (r["rules"].get("fail_closed_received_then_file") or {}).get("sha256"),
        }
    res["benign_detected"] = len(res["benign"]["shadow_events"]) == 0 and \
        res["benign"]["fail_closed_sha"] == pin
    res["mutant_detected"] = len(res["mutant"]["shadow_events"]) == 1 and \
        res["mutant"]["created_at_max_sha"] == stale and \
        res["mutant"]["fail_closed_sha"] == pin
    return res


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    SANDBOX.mkdir(parents=True, exist_ok=True)
    probe_dt = datetime.now(CST)
    probe_at = probe_dt.isoformat(timespec="seconds")

    inputs_start = {
        "artifacts/formulation/FROZEN.json": digest_or_none(FROZEN),
        "research_map/events.jsonl": digest_or_none(EVENTS),
        "research_map/research_map.json": digest_or_none(MAP),
        "research_map/formulation_taxonomy.yaml": digest_or_none(TAXONOMY),
    }
    for h in HELD:
        inputs_start[h] = digest_or_none(ROOT / h)
    inputs_start["artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"] = \
        digest_or_none(ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml")

    manifest = json.loads(FROZEN.read_text())
    pins = manifest.get("files", {})
    frozen_rev = manifest.get("revision")
    stream = load_stream(EVENTS)
    ob_idx = outbox_index()
    applied = set(json.loads(MAP.read_text()).get("applied_event_ids") or [])
    map_doc = json.loads(MAP.read_text())

    report = {
        "probe": "W095-F2B-STREAM-BINDING-R6-VERIFY-01",
        "worker": "worker-095",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "probe_at": probe_at,
        "frozen_revision_reviewed": frozen_rev,
        "frozen_manifest_sha256": inputs_start["artifacts/formulation/FROZEN.json"],
        "stream_lines": len(stream),
        "checks": {},
        "scope_note": "artifact-and-stream binding measurement; not a schema-content verdict and "
                      "not a gate verdict",
    }

    # ---------------- R1: held pins vs disk ----------------
    r1 = {"pins": {}}
    for h in HELD + ["artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"]:
        pin = (pins.get(h) or {}).get("sha256")
        live = digest_or_none(ROOT / h)
        r1["pins"][h] = {"pin": pin, "live": live, "match": pin is not None and pin == live}
    r1["n_match"] = sum(1 for v in r1["pins"].values() if v["match"])
    r1["n_checked"] = len(r1["pins"])
    report["checks"]["R1-PIN-MATCH"] = "PASS" if r1["n_match"] == r1["n_checked"] else "FAIL"
    report["r1_pin_match"] = r1

    # ---------------- R2: F2b resolution per rule ----------------
    r2 = {}
    for p in F2B_PATHS:
        pin = (pins.get(p) or {}).get("sha256")
        r2[p] = resolve_latest(stream, p, pin, probe_dt)
        r2[p]["shadow_events"] = future_shadow(stream, p, pin, probe_dt)
    r2_pass = all(v["all_rules_resolve_to_pin"] for v in r2.values())
    report["checks"]["R2-F2B-RESOLUTION"] = "PASS" if r2_pass else "FAIL"
    report["r2_f2b_resolution"] = r2

    # ---------------- R3: future-dated cohort ----------------
    cohort = []
    for i, e in stream:
        c = parse_ts(e.get("created_at"))
        if not c or c <= probe_dt:
            continue
        eid = e.get("event_id")
        prov = ob_idx.get(eid)
        locs = map_locations(map_doc, eid) if eid else []
        cohort.append({
            "line": i, "event_id": eid, "actor": e.get("actor"),
            "event_type": e.get("event_type"), "created_at": e.get("created_at"),
            "seconds_ahead": int((c - probe_dt).total_seconds()),
            "_received_at": e.get("_received_at"),
            "in_outbox": bool(prov), "outbox_file": (prov or {}).get("file"),
            "outbox_mtime": (prov or {}).get("file_mtime"),
            "applied": eid in applied,
            "map_locations": locs,
            "map_content_locations": [l for l in locs
                                      if not l.startswith("$.applied_event_ids")],
            "path": e.get("path"), "sha256": e.get("sha256"),
        })
    cohort.sort(key=lambda r: r["created_at"])
    by_actor = {}
    by_type = {}
    for r in cohort:
        by_actor[r["actor"]] = by_actor.get(r["actor"], 0) + 1
        by_type[r["event_type"]] = by_type.get(r["event_type"], 0) + 1
    r3 = {
        "probe_at": probe_at,
        "cutoff_note": "membership is created_at > probe_at; block members whose claimed "
                       "created_at the wall clock has already passed fall out of this filter "
                       "(R4 selects the block by event_id instead)",
        "n_future_dated": len(cohort),
        "n_applied": sum(1 for r in cohort if r["applied"]),
        "n_without_received_at": sum(1 for r in cohort if not r["_received_at"]),
        "n_absent_from_all_outboxes": sum(1 for r in cohort if not r["in_outbox"]),
        "n_materialized_in_map": sum(1 for r in cohort if r["map_locations"]),
        "n_with_map_content_locations": sum(1 for r in cohort if r["map_content_locations"]),
        "by_actor": by_actor,
        "by_type": by_type,
        "cohort": cohort,
    }
    report["checks"]["R3-FUTURE-COHORT"] = "INFO (measured)"
    report["r3_future_cohort"] = {k: v for k, v in r3.items() if k != "cohort"}
    (RAW / "future_cohort_r6.json").write_text(json.dumps(r3, indent=1) + "\n")

    # ---------------- R4: block provenance + write-time ----------------
    # select the block by event id from the stream, independently of the moving
    # created_at > probe_at cutoff (the 01:15:00-01:15:06 members are already past it)
    block = []
    for i, e in stream:
        if e.get("event_id") not in BLOCK_IDS:
            continue
        eid = e.get("event_id")
        prov = ob_idx.get(eid) or {}
        locs = map_locations(map_doc, eid)
        block.append({
            "line": i, "event_id": eid, "actor": e.get("actor"),
            "event_type": e.get("event_type"), "created_at": e.get("created_at"),
            "_received_at": e.get("_received_at"),
            "in_outbox": bool(prov), "outbox_file": prov.get("file"),
            "outbox_mtime": prov.get("file_mtime"),
            "applied": eid in applied,
            "map_locations": locs,
            "map_content_locations": [l for l in locs
                                      if not l.startswith("$.applied_event_ids")],
            "path": e.get("path"), "sha256": e.get("sha256"),
        })
    first_recv_line = next((i for i, e in stream if e.get("_received_at")), None)
    block_lines = sorted(r["line"] for r in block)
    ob_files = sorted({r["outbox_file"] for r in block if r["outbox_file"]})
    block_created = sorted(r["created_at"] for r in block)
    prewritten = [r for r in block if r["outbox_mtime"] and r["created_at"]
                  and r["outbox_mtime"] < r["created_at"]]
    max_lead_s = None
    if prewritten:
        max_lead_s = max(int((parse_ts(r["created_at"]) - parse_ts(r["outbox_mtime"])).total_seconds())
                         for r in prewritten)
    r4 = {
        "block_ids_requested": len(BLOCK_IDS),
        "block_ids_found": len(block),
        "block_lines_min": min(block_lines) if block_lines else None,
        "block_lines_max": max(block_lines) if block_lines else None,
        "block_created_min": min(block_created) if block_created else None,
        "block_created_max": max(block_created) if block_created else None,
        "first_line_with_received_at": first_recv_line,
        "first_received_at_value": next((e.get("_received_at") for _, e in stream
                                         if e.get("_received_at")), None),
        "block_inside_unstamped_prefix": bool(
            block_lines and first_recv_line and max(block_lines) < first_recv_line),
        "outbox_files": ob_files,
        "outbox_mtimes": sorted({r["outbox_mtime"] for r in block if r["outbox_mtime"]}),
        "written_before_claimed_time": bool(block) and len(prewritten) == len(block),
        "n_written_before_claimed_time": len(prewritten),
        "max_lead_seconds": max_lead_s,
        "all_applied": all(r["applied"] for r in block) if block else None,
        "all_without_received_at": all(not r["_received_at"] for r in block) if block else None,
        "n_applied": sum(1 for r in block if r["applied"]),
        "n_materialized_in_map": sum(1 for r in block if r["map_locations"]),
        "n_with_map_content_locations": sum(1 for r in block if r["map_content_locations"]),
        "referenced_artifacts_exist": {},
    }
    for p in ["artifacts/worker-06/frozen_gate_run.json", "artifacts/worker-06/canonical_gate_run.json",
              "artifacts/worker-06/blindspot_report.json", "artifacts/worker-06/heldout_corpus/report.json",
              "artifacts/worker-06/heldout_corpus/manifest.json"]:
        r4["referenced_artifacts_exist"][p] = (ROOT / p).is_file()
    report["checks"]["R4-BLOCK-PROVENANCE"] = "INFO (measured)"
    report["r4_block_provenance"] = r4
    (RAW / "block_provenance_r6.json").write_text(json.dumps({**r4, "block": block}, indent=1) + "\n")

    # ---------------- R5: applied effects on the live map ----------------
    # look the headline event up in the block (not the moving future-cohort cutoff)
    rev6 = next((r for r in block if r["event_id"] == "w06-20260912T0115-f2b-rev6"), None)
    rev6_frozen = None
    if rev6:
        rev6_frozen = {
            "claims_it_names": rev6["path"],
            "declared_sha256": rev6["sha256"],
            "frozen_pin_for_that_path": (pins.get(rev6["path"]) or {}).get("sha256"),
            "declared_equals_pin": rev6["sha256"] == (pins.get(rev6["path"]) or {}).get("sha256"),
            "supersedes": next((e.get("supersedes") for _, e in stream
                                if e.get("event_id") == rev6["event_id"]), None),
            "map_locations": rev6["map_locations"],
            "map_content_locations": rev6["map_content_locations"],
        }
    r5 = {
        "cohort_events_applied": sorted(r["event_id"] for r in cohort if r["applied"]),
        "cohort_events_in_map_content": sorted(
            r["event_id"] for r in cohort if r["map_content_locations"]),
        "block_events_in_map_content": sorted(
            r["event_id"] for r in block if r["map_content_locations"]),
        "rev6_f2b_event": rev6_frozen,
    }
    report["checks"]["R5-APPLIED-EFFECTS"] = "INFO (measured)"
    report["r5_applied_effects"] = r5
    (RAW / "applied_effects_r6.json").write_text(json.dumps(r5, indent=1) + "\n")

    # ---------------- R6: controls + determinism ----------------
    controls = control_run(probe_dt)
    pass1 = {p: resolve_latest(stream, p, (pins.get(p) or {}).get("sha256"), probe_dt)
             for p in F2B_PATHS}
    pass2 = {p: resolve_latest(stream, p, (pins.get(p) or {}).get("sha256"), probe_dt)
             for p in F2B_PATHS}
    controls["double_run_identical"] = (json.dumps(pass1, sort_keys=True) ==
                                        json.dumps(pass2, sort_keys=True))
    controls["canonical_untouched_by_probe"] = True
    r6_pass = controls["benign_detected"] and controls["mutant_detected"] and \
        controls["double_run_identical"]
    report["checks"]["R6-CONTROLS"] = "PASS" if r6_pass else "FAIL"
    report["r6_controls"] = controls
    (RAW / "controls_r6.json").write_text(json.dumps(controls, indent=1) + "\n")

    # ---------------- R7: no probe drift ----------------
    # canonical pins must not move inside the window; the stream/map legitimately move with
    # traffic, so their movement is reported as an INFO frame note, not a failure.
    CANONICAL_KEYS = ["artifacts/formulation/FROZEN.json",
                      "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"] + HELD
    inputs_end = {k: digest_or_none(ROOT / k) for k in inputs_start}
    canon_drift = {k: {"start": inputs_start[k], "end": inputs_end[k]}
                   for k in CANONICAL_KEYS if inputs_start[k] != inputs_end[k]}
    stream_movement = {k: {"start": inputs_start[k], "end": inputs_end[k]}
                       for k in ("research_map/events.jsonl", "research_map/research_map.json")
                       if inputs_start[k] != inputs_end[k]}
    report["checks"]["R7-NO-PROBE-DRIFT"] = "PASS" if not canon_drift else "FAIL"
    report["r7_drift"] = canon_drift
    report["r7_stream_movement"] = stream_movement

    (RAW / "instant_pins_r6.json").write_text(json.dumps(
        {"probe_at": probe_at, "inputs_start": inputs_start, "inputs_end": inputs_end,
         "frozen_revision": frozen_rev, "stream_lines": len(stream)}, indent=1) + "\n")
    (RAW / "f2b_resolution_r6.json").write_text(json.dumps(r2, indent=1) + "\n")

    hard = []
    if report["checks"]["R1-PIN-MATCH"] != "PASS":
        hard.append("HF-R6-00: a held path is off its FROZEN rev29 pin")
    if report["checks"]["R2-F2B-RESOLUTION"] != "PASS":
        hard.append("HF-R6-02: F2b held path does not resolve to the pin under every rule")
    if r3["n_future_dated"] and r3["n_applied"]:
        hard.append("HF-R6-01: the pinned accepted-stream snapshot contains future-dated events "
                    f"and they are applied to the sole global state ({r3['n_applied']}/"
                    f"{r3['n_future_dated']} of the cohort at {probe_at})")
    if block and r4["block_inside_unstamped_prefix"] and r4["written_before_claimed_time"]:
        hard.append("HF-R6-03: the deepseek-flash-06 future block sits inside the unstamped prefix "
                    "and its outbox was written hours before its claimed created_at")
    report["hard_failures"] = hard
    report["verdict"] = "revise" if hard else "accept"
    report["next_falsifier"] = (
        "Withdrawn if, under a read path declared in the repo: (a) every held path and the F2b "
        "mirror resolve to the FROZEN rev29 pin, with events lacking _received_at and events whose "
        "created_at is future-dated unable to confer precedence; (b) no event whose created_at "
        "post-dates the probe instant is applied to research_map.json or materialized in its "
        "claims/reviews while contending a frozen pin; (c) the deepseek-flash-06 block is either "
        "re-timestamped to its write time or excluded from pin resolution; (d) a re-probe from a "
        "second instance at the same pinned inputs reproduces these counts. Any canonical byte "
        "move voids this window, not the finding."
    )

    (RAW / "probe_report_r6.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({
        "probe": report["probe"], "probe_at": probe_at,
        "checks": report["checks"], "verdict": report["verdict"],
        "hard_failures": hard,
        "f2b_created_at_sha": (r2[F2B_PATHS[0]]["rules"].get("created_at_max") or {}).get("sha256"),
        "f2b_pin": (pins.get(F2B_PATHS[0]) or {}).get("sha256"),
        "future_dated": r3["n_future_dated"], "applied": r3["n_applied"],
        "block": {"found": len(block), "inside_prefix": r4["block_inside_unstamped_prefix"],
                  "written_before_claimed": r4["written_before_claimed_time"]},
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
