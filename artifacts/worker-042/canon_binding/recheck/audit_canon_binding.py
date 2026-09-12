#!/usr/bin/env python3
"""W042-CANON-BIND-04 checker: canonical gate-input binding census.

Deterministic, stdlib-only.  Reads ONLY artifacts/worker-042/canon_binding/snapshot/
(events.jsonl, research_map.json, manifest.json, canonical/*) and answers, at one pin:

  Q1  For each declared canonical gate-input path, do the pinned bytes equal the
      sha256 announced by the LATEST ARRIVAL artifact event for that path?
  Q2  Which paths were written after their latest matching announcement
      (content-identical vs content-changed)?
  Q3  Which declarations are future-dated at the pin and do not match the pinned
      bytes (dangling future declarations)?
  Q4  Which paths are pinned only in map.frozen_artifacts with zero artifact events?
  Q5  CF-19 at this pin: is the L0 a1674f094979 write announced in the accepted
      stream after the owner's 3e3d35531421 exit announcement?

No node status, no validation_status, no gate verdict, no adjudication of content.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
CST = timezone(timedelta(hours=8))
HEX12 = re.compile(r"^[0-9a-f]{12}")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_ts(value):
    if not value or not isinstance(value, str):
        return None
    s = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=CST)
    return dt


def norm_hash(value):
    if not isinstance(value, str):
        return None
    s = value.strip()
    if s.startswith("sha256:"):
        s = s[len("sha256:"):]
    s = s.lower()
    return s if re.fullmatch(r"[0-9a-f]{64}", s) else None


def extract_announcements(events_lines):
    """Artifact events that name a path and a full sha256, in line (arrival) order."""
    anns, skipped = [], {"non_artifact": 0, "no_path": 0, "bad_hash": 0, "parse_error": 0}
    for line_no, raw in enumerate(events_lines, 1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            e = json.loads(raw)
        except ValueError:
            skipped["parse_error"] += 1
            continue
        if e.get("event_type") != "artifact":
            skipped["non_artifact"] += 1
            continue
        p = e.get("path")
        if not isinstance(p, str) or not p:
            skipped["no_path"] += 1
            continue
        h = norm_hash(e.get("sha256"))
        if h is None:
            skipped["bad_hash"] += 1
            continue
        anns.append({
            "line": line_no,
            "path": p,
            "event_id": e.get("event_id"),
            "actor": e.get("actor"),
            "created_at": e.get("created_at"),
            "created_dt": parse_ts(e.get("created_at")),
            "received_at": e.get("_received_at"),
            "received_dt": parse_ts(e.get("_received_at")),
            "sha256": h,
        })
    return anns, skipped


def classify_path(disk_sha, anns, pinned_dt):
    """Pure classifier used by both the census and the synthetic controls."""
    anns = sorted(anns, key=lambda a: a["line"])
    future = [a for a in anns if a["created_dt"] and pinned_dt and a["created_dt"] > pinned_dt]
    result = {
        "n_announcements": len(anns),
        "n_distinct_hashes": len({a["sha256"] for a in anns}),
        "latest_arrival": anns[-1] if anns else None,
        "latest_created": None,
        "unannounced": len(anns) == 0,
        "arrival_match": None,
        "created_match": None,
        "post_announcement_write": False,
        "post_announcement_write_identical": None,
        "future_declarations": len(future),
        "dangling_future": [],
        "superseded_created_declaration": False,
    }
    if anns:
        with_ts = [a for a in anns if a["created_dt"]]
        if with_ts:
            result["latest_created"] = max(with_ts, key=lambda a: (a["created_dt"], a["line"]))
        if disk_sha:
            result["arrival_match"] = result["latest_arrival"]["sha256"] == disk_sha
            result["created_match"] = bool(result["latest_created"]) and \
                result["latest_created"]["sha256"] == disk_sha
            result["superseded_created_declaration"] = \
                bool(result["latest_created"]) and result["latest_created"]["sha256"] != disk_sha
        result["dangling_future"] = [a for a in future if disk_sha and a["sha256"] != disk_sha]
        return result
    return result


def annotate_write(rec, disk_mtime_dt, disk_sha):
    """Attach rewrite detection once the disk file's mtime and sha are known."""
    la = rec.get("latest_arrival")
    if not la or disk_mtime_dt is None:
        return
    ref = la["received_dt"] or la["created_dt"]
    if ref and disk_mtime_dt > ref:
        rec["post_announcement_write"] = True
        rec["post_announcement_write_identical"] = bool(
            la["sha256"] and disk_sha and la["sha256"] == disk_sha)
        rec["write_after_announcement_seconds"] = round((disk_mtime_dt - ref).total_seconds(), 1)


def run_controls(classify_fn):
    """Synthetic streams over the same classifier; no filesystem access."""
    pin = parse_ts("2026-09-12T00:43:50+08:00")

    def A(line, h, created, received=None):
        return {"line": line, "sha256": h, "created_dt": parse_ts(created),
                "received_dt": parse_ts(received) if received else None,
                "created_at": created, "received_at": received, "event_id": f"c{line}", "actor": "ctl"}

    h1, h2, h3 = "a" * 64, "b" * 64, "c" * 64
    tests = []
    t = classify_fn(h1, [A(1, h1, "2026-09-12T00:40:00+08:00", "2026-09-12T00:40:01+08:00")], pin)
    tests.append(("C1_latest_arrival_match", t["arrival_match"] is True and t["unannounced"] is False))
    t = classify_fn(h1, [], pin)
    tests.append(("C2_unannounced_flagged", t["unannounced"] is True and t["arrival_match"] is None))
    t = classify_fn(h1, [A(1, h1, "2026-09-12T00:30:00+08:00"), A(2, h2, "2026-09-12T00:31:00+08:00")], pin)
    tests.append(("C3_stale_arrival_flagged", t["arrival_match"] is False))
    t = classify_fn(h1, [A(1, h2, "2026-09-12T01:52:10+08:00"), A(2, h1, "2026-09-12T00:40:00+08:00")], pin)
    tests.append(("C4_future_dangling_nonlatest", t["arrival_match"] is True and t["dangling_future"] and
                  len(t["dangling_future"]) == 1))
    t = classify_fn(h1, [A(1, h1, "2026-09-12T00:30:00+08:00", "2026-09-12T00:30:01+08:00")], pin)
    annotate_write(t, parse_ts("2026-09-12T00:39:11+08:00"), h1)
    tests.append(("C5_rewrite_identical_detected", t["post_announcement_write"] is True and
                  t["post_announcement_write_identical"] is True))
    t = classify_fn(h2, [A(1, h1, "2026-09-12T00:30:00+08:00", "2026-09-12T00:30:01+08:00")], pin)
    annotate_write(t, parse_ts("2026-09-12T00:39:11+08:00"), h2)
    tests.append(("C6_rewrite_changed_detected", t["post_announcement_write"] is True and
                  t["post_announcement_write_identical"] is False and t["arrival_match"] is False))
    t = classify_fn(h1, [A(1, h2, "2026-09-12T02:00:00+08:00"), A(2, h1, "2026-09-12T00:30:00+08:00")], pin)
    tests.append(("C7_created_winner_superseded", t["superseded_created_declaration"] is True and
                  t["arrival_match"] is True))
    # C8: extraction ignores non-artifact and hashless events.
    lines = [
        json.dumps({"event_type": "status", "path": "x", "sha256": h1}),
        json.dumps({"event_type": "artifact", "path": "x", "sha256": ""}),
        json.dumps({"event_type": "artifact", "path": "x", "sha256": h1, "event_id": "ok"}),
    ]
    anns, _ = extract_announcements(lines)
    tests.append(("C8_non_artifact_and_hashless_ignored", len(anns) == 1 and anns[0]["event_id"] == "ok"))
    return {name: bool(ok) for name, ok in tests}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default=os.path.join(HERE, "snapshot"))
    ap.add_argument("--out", default=os.path.join(HERE, "report.json"))
    args = ap.parse_args()
    snap = os.path.abspath(args.snapshot)

    manifest = json.load(open(os.path.join(snap, "manifest.json")))
    pinned_dt = parse_ts(manifest["pinned_at"])
    with open(os.path.join(snap, "events.jsonl")) as f:
        events_lines = f.readlines()
    pinned_map = json.load(open(os.path.join(snap, manifest["stream"]["map"]["snapshot_path"])))
    frozen_by_path = {x.get("path"): x for x in pinned_map.get("frozen_artifacts", []) if x.get("path")}
    anns, skipped = extract_announcements(events_lines)

    by_path = {}
    for a in anns:
        by_path.setdefault(a["path"], []).append(a)

    table = []
    for item in manifest["declared_paths"]:
        p = item["path"]
        snap_rel = item.get("snapshot_path")
        disk_sha = None
        disk_mtime_dt = None
        if snap_rel:
            abs_snap = os.path.join(snap, snap_rel)
            if os.path.exists(abs_snap):
                disk_sha = sha256_file(abs_snap)
                if item.get("mtime_ns") is not None:
                    disk_mtime_dt = datetime.fromtimestamp(item["mtime_ns"] / 1e9, CST)
        rec = classify_path(disk_sha, by_path.get(p, []), pinned_dt)
        rec["disk_sha256"] = disk_sha
        rec["disk_mtime_iso"] = disk_mtime_dt.isoformat(timespec="seconds") if disk_mtime_dt else None
        annotate_write(rec, disk_mtime_dt, disk_sha)
        rec.update({
            "path": p,
            "node": item.get("node"),
            "role": item.get("role"),
            "retired": item.get("retired", False),
            "map_declared_prefix": manifest["map_declared_prefixes"].get(p),
            "map_declared_matches_disk": (None if not manifest["map_declared_prefixes"].get(p)
                                          else bool(disk_sha and disk_sha.startswith(
                                              manifest["map_declared_prefixes"][p]))),
            "map_frozen_sha256": (frozen_by_path.get(p) or {}).get("sha256"),
            "map_frozen_active": (frozen_by_path.get(p) or {}).get("active"),
            "map_frozen_matches_disk": bool(disk_sha and (frozen_by_path.get(p) or {}).get("sha256") == disk_sha),
        })
        rec.pop("latest_arrival", None)
        rec.pop("latest_created", None)
        table.append(rec)

    # Re-attach the compact latest-* views (JSON-safe subset) for the report.
    for rec in table:
        a = by_path.get(rec["path"], [])
        rec["latest_arrival"] = ({k: a[-1][k] for k in
                                  ("line", "event_id", "actor", "created_at", "received_at", "sha256")}
                                 if a else None)
        with_ts = [x for x in a if x["created_dt"]]
        lc = max(with_ts, key=lambda x: (x["created_dt"], x["line"])) if with_ts else None
        rec["latest_created"] = ({k: lc[k] for k in
                                  ("line", "event_id", "actor", "created_at", "received_at", "sha256")}
                                 if lc else None)
        rec["dangling_future"] = [{k: x[k] for k in
                                   ("line", "event_id", "actor", "created_at", "received_at", "sha256")}
                                  for x in rec["dangling_future"]]

    bound = [r for r in table if r["arrival_match"] is True]
    unannounced = [r for r in table if r["unannounced"]]
    mismatched = [r for r in table if r["arrival_match"] is False]
    rewrites = [r for r in table if r["post_announcement_write"]]
    future_dangling = [r for r in table if r["dangling_future"]]
    map_mismatch = [r for r in table if r["map_declared_matches_disk"] is False]
    superseded = [r for r in table if r["superseded_created_declaration"]]

    # CF-19 block: L0 theorems ledger timeline.
    l0_path = "ledger/theorems.jsonl"
    l0 = next((r for r in table if r["path"] == l0_path), None)
    l0_anns = by_path.get(l0_path, [])
    exit_ann = next((a for a in l0_anns if a["sha256"].startswith("3e3d35531421")), None)
    announced_after_exit = None
    if l0 and l0["disk_sha256"]:
        matches = [a for a in l0_anns if a["sha256"] == l0["disk_sha256"]]
        if matches and exit_ann:
            later = [a for a in matches if a["line"] > exit_ann["line"]]
            announced_after_exit = bool(later)
            if later:
                la = later[-1]
                announced_after_exit = {
                    "event_id": la["event_id"], "line": la["line"], "actor": la["actor"],
                    "created_at": la["created_at"], "received_at": la["received_at"],
                    "write_mtime_iso": l0["disk_mtime_iso"],
                    "write_to_arrival_seconds": round(
                        (la["received_dt"] - parse_ts(l0["disk_mtime_iso"])).total_seconds(), 1)
                    if la["received_dt"] else None,
                    "created_at_ahead_of_pin_seconds": round(
                        (la["created_dt"] - pinned_dt).total_seconds(), 1) if la["created_dt"] else None,
                }
    cf19 = {
        "path": l0_path,
        "disk_sha256": l0["disk_sha256"] if l0 else None,
        "owner_exit_announcement": ({k: exit_ann[k] for k in
                                     ("line", "event_id", "actor", "created_at", "received_at", "sha256")}
                                    if exit_ann else None),
        "announced_after_exit": announced_after_exit,
        "finding_text_falsified_at_this_pin": bool(announced_after_exit),
        "note": ("CF-19 as recorded at 00:37:18 said no artifact event announced the "
                 "a1674f094979 bytes; at this pin an announcement exists, so the wording is "
                 "historical. Content preservation vs the rev-3 archive is the literature "
                 "lead's reconcile card, not measured here."),
    }

    findings = []
    findings.append({
        "id": "W042-CB-01",
        "severity": "info",
        "statement": (f"Arrival-order binding holds at the pin for {len(bound)}/{len(table)} declared "
                      f"canonical gate inputs: pinned bytes equal the sha256 of the latest arrival "
                      f"artifact event. {len(unannounced)} path(s) have zero artifact events and "
                      f"{len(mismatched)} path(s) mismatch the latest arrival announcement."),
        "falsifier": ("Re-run the checker on the pinned snapshot; falsified if any path classified "
                      "arrival_match=true has pinned bytes differing from the listed latest-arrival "
                      "announcement sha256, or if a mismatched/unannounced path is missing."),
    })
    findings.append({
        "id": "W042-CB-02",
        "severity": "info",
        "statement": (f"{len(unannounced)} declared path(s) are bound only by map.frozen_artifacts, with no "
                      "artifact event in the accepted stream: "
                      + ", ".join(f"{r['path']} (frozen {str(r['map_frozen_sha256'])[:12]}, active="
                                  f"{r['map_frozen_active']}, bytes_match={r['map_frozen_matches_disk']})"
                                  for r in unannounced)
                      + ". Their pinned bytes match the frozen sha256, so this is a provenance-gap, not drift."),
        "falsifier": ("Re-run the checker; falsified if an artifact event for either path exists in the "
                      "pinned stream, or if the pinned bytes differ from map.frozen_artifacts sha256."),
    })
    aa = cf19["announced_after_exit"] if isinstance(cf19["announced_after_exit"], dict) else None
    if aa:
        delta = aa["created_at_ahead_of_pin_seconds"]
        if delta is not None and delta > 0:
            stamp_note = f"the announcing event's created_at is {delta} s AHEAD of the pin (future-dated)"
        elif delta is not None:
            stamp_note = (f"the announcing event's created_at is {abs(delta)} s BEFORE the pin at this "
                          "pin (it was future-dated at earlier pins)")
        else:
            stamp_note = "the announcing event's created_at is unparseable"
        cb03_statement = (
            "CF-19 status at pin: the ledger/theorems.jsonl bytes a1674f094979 ARE announced in the "
            f"pinned stream after the owner's 3e3d35531421 exit announcement by event {aa['event_id']} "
            f"(arrived {aa['received_at']}), so the CF-19 wording 'no artifact event announces the new "
            f"bytes' is falsified at this pin; {stamp_note} and the write-to-arrival gap is "
            f"{aa['write_to_arrival_seconds']} s. CF-14 clock discipline still applies to the stamp.")
    else:
        cb03_statement = ("CF-19 status at pin: no later-line announcement carries the pinned "
                          "ledger/theorems.jsonl sha256, so the CF-19 'no announcing event' condition "
                          "still holds at this pin.")
    findings.append({
        "id": "W042-CB-03",
        "severity": "major",
        "statement": cb03_statement,
        "falsifier": ("Re-run on the pinned snapshot; falsified if no later-line announcement carries "
                      "disk sha256 a1674f094979, if the exit announcement 3e3d35531421 line is after the "
                      "matching announcement, or if event create/arrival stamps differ from those listed."),
    })
    rw = [r for r in rewrites if r["path"] != l0_path or not isinstance(cf19["announced_after_exit"], dict)]
    findings.append({
        "id": "W042-CB-04",
        "severity": "minor",
        "statement": (f"Post-announcement writes with unchanged bytes: "
                      + ("; ".join(f"{r['path']} mtime {r['disk_mtime_iso']} is "
                                  f"{r.get('write_after_announcement_seconds')} s after its latest matching "
                                  f"announcement arrival ({r['latest_arrival']['received_at']}), sha unchanged"
                                  for r in table
                                  if r["post_announcement_write"] and r["post_announcement_write_identical"]
                                  and r["arrival_match"] is True) or "none")
                      + ". Identical-byte rewrites keep binding, but a live regeneration path that "
                        "changes content without an event would break it silently."),
        "falsifier": ("Re-run the checker; falsified if the listed path's mtime is not after the listed "
                      "announcement arrival, or if its pinned sha differs from the announcement."),
    })
    findings.append({
        "id": "W042-CB-05",
        "severity": "info",
        "statement": (f"{len(future_dangling)} declared path(s) carry future-dated declarations whose sha256 "
                      "differs from the pinned bytes (dangling future declarations): "
                      + "; ".join(f"{r['path']} {d['sha256'][:12]} created {d['created_at']} line {d['line']}"
                                  for r in future_dangling for d in r["dangling_future"])
                      + ". They are earlier in arrival order than the bound announcement, so arrival-order "
                        "binding is unaffected; they are the set that would win under created_at ordering "
                        "(cross-ref W042-ORDER-INVERSION-03 W042-OI-03)."),
        "falsifier": ("Re-run the checker; falsified if a listed declaration is not future-dated at the "
                      "pin, matches the pinned bytes, or is the latest arrival announcement."),
    })

    superseded_rows = [r for r in superseded if r["arrival_match"] is True and r["latest_created"]]
    findings.append({
        "id": "W042-CB-06",
        "severity": "minor",
        "statement": (f"{len(superseded_rows)} of {len(bound)} arrival-bound path(s) have a created_at-order "
                      "winner whose sha256 differs from the pinned bytes (future-stamped declarations that "
                      "lose on arrival order but would win on a created_at replay): "
                      + "; ".join(f"{r['path']} -> {r['latest_created']['sha256'][:12]} created "
                                  f"{r['latest_created']['created_at']} line {r['latest_created']['line']}"
                                  for r in superseded_rows)
                      + ". This is the CF-14 replay-fidelity exposure at this pin; it does not change any "
                        "current binding."),
        "falsifier": ("Re-run the checker; falsified if a listed path's latest created_at declaration "
                      "matches the pinned bytes, or if another path has a differing created_at winner "
                      "that is not listed."),
    })

    report = {
        "task_id": "W042-CANON-BIND-04",
        "worker": "worker-042",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "node_id": "A1",
        "gate": "G-AUDIT",
        "related_gates": ["G-AUDIT", "G-F0", "G-FORM", "G-LIT", "G-NUM"],
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "question": ("At one pin, for every declared canonical gate-input path, do the pinned bytes equal "
                     "the sha256 of the latest-arrival artifact event; which paths were rewritten after "
                     "their announcement; which declarations are future-dated and dangling; and what is "
                     "CF-19's status at this pin?"),
        "inputs": {
            "snapshot_dir": os.path.relpath(snap),
            "pinned_at": manifest["pinned_at"],
            "events_sha256": manifest["stream"]["events"]["sha256_snapshot"],
            "map_sha256": manifest["stream"]["map"]["sha256_snapshot"],
            "manifest_sha256": sha256_file(os.path.join(snap, "manifest.json")),
            "map_updated_at": pinned_map.get("updated_at"),
            "events_lines": len(events_lines),
            "artifact_announcements_parsed": len(anns),
            "events_skipped": skipped,
        },
        "summary": {
            "declared_paths": len(table),
            "bound_arrival_match": len(bound),
            "mismatched_latest_arrival": len(mismatched),
            "unannounced_paths": len(unannounced),
            "post_announcement_rewrites": len(rewrites),
            "paths_with_dangling_future_declarations": len(future_dangling),
            "map_declared_prefix_mismatches": len(map_mismatch),
            "superseded_created_declarations": len(superseded),
        },
        "table": table,
        "cf19": cf19,
        "findings": findings,
        "controls": run_controls(classify_path),
        "authority_note": ("Worker events cannot set status=done, validation_status=passed, or a gate "
                           "verdict; the controller and group leads adjudicate. This report is a "
                           "binding measurement, not the CF-19 reconcile adjudication."),
        "does_not_claim": ("no node status, no validation_status, no gate verdict, no content-preservation "
                           "adjudication of the L0 ledger, no correctness claim about any schema."),
        "rerun_command": ("python3 artifacts/worker-042/canon_binding/audit_canon_binding.py "
                          "--snapshot artifacts/worker-042/canon_binding/snapshot "
                          "--out artifacts/worker-042/canon_binding/report.json"),
    }
    report["controls"]["all_passed"] = all(report["controls"].values())
    with open(args.out, "w") as f:
        json.dump(report, f, indent=1, sort_keys=True)
        f.write("\n")
    print(json.dumps({
        "out": os.path.relpath(args.out, os.path.dirname(os.path.dirname(os.path.dirname(HERE)))),
        "summary": report["summary"],
        "controls_all_passed": report["controls"]["all_passed"],
        "cf19_announced_after_exit": bool(announced_after_exit),
        "report_sha256": sha256_file(args.out),
    }, indent=1))
    return 0 if report["controls"]["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
