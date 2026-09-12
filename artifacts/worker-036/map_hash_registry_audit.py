#!/usr/bin/env python3
"""W036-MAPREG-01 -- map hash-registry drift and digest-format audit.

Why this exists
---------------
The controller's lifecycle pass (research_map/astra_lifecycle.py) fills, per node,
`artifact_sha256_measured` and a boolean `declared_hash_matches_measured`.  Those fields
are what gates and reviewers read.  Nothing independent re-measures them: worker-03's
W03-PUBLISH-CHECK-01 audits the FROZEN manifest / canonical-vs-authoring trees / verdict
bindings, but not the map's own hash registry and not runtime/state/artifact_hashes.json.

Consequence this audit tests: a node can show `declared_hash_matches_measured=false`
while the bytes on disk are exactly what the map measured -- the flag then means
"the declared event hash is old", not "the artifact drifted".  Misreading it as drift
would wrongly fail G-F0 / G-FORM.  Conversely a node can show
`declared_hash_matches_measured=true` while `artifact_sha256_measured` no longer matches
disk (live directories), which would wrongly let a review bind to a stale hash.

Second failure mode (found in the first run of this tool): a `declared_hash_matches_measured`
false can also mean the declared value is **not a sha256 at all**.  The accepted event
stream contains artifact events whose `sha256` is a 16-hex prefix zero-padded to 64 chars
(`^[0-9a-f]{16}0{48}$`).  The prefix is correct, so 12-hex citation prefixes still match,
but no full-digest equality can ever succeed.  Those events were later corrected in the
author's outbox under the *same event_id*; `comms.py` dedupes by event_id (line 303), so
the corrected copies can never be ingested.  This tool measures that trap too.

What it does
------------
1. Uses the controller's own digest algorithm (astra_lifecycle.digest): file -> sha256 of
   bytes; directory -> sha256 over sorted "<relpath>\\0<filesha>\\n" lines, skipping "._*".
2. For every node in research_map.json with an `artifact`, compares three hashes:
     declared  = node["artifact_sha256"]           (from an artifact event)
     recorded  = node["artifact_sha256_measured"]  (last controller lifecycle pass)
     fresh     = digest(artifact)                  (this run)
   and classifies: bound | declared_stale | declared_malformed | registry_stale |
   registry_stale_live_dir | unbound_no_declared | absent.
3. Re-measures runtime/state/artifact_hashes.json (checkpoint registry) against fresh.
4. Re-measures the map's `frozen_artifacts` entries that are still `active`.
5. Scans accepted artifact events in research_map/events.jsonl for digest-format defects
   and checks whether a corrected outbox copy exists but is blocked by event_id dedup.
6. Emits a JSON report and an exit code: 1 if any hard finding, else 0.

It is a measurement.  It sets no gate verdict, edits no artifact it measures, and does
not write research_map.json.

Falsifier
---------
Re-run against the same recorded `map_sha256` / `events_sha256` snapshot (see
report.snapshot) and the same wall-clock artifact state.  The report is FALSIFIED if
(a) any node classified `registry_stale` or `registry_stale_live_dir` hashes to its
recorded value on re-measure; or (b) any node classified `declared_stale` has a declared
hash equal to its fresh digest; or (c) any node classified `bound` fails either equality;
or (d) any node/event classified `declared_malformed` has a declared field that is a full
64-hex digest without the 48-zero tail; or (e) any event recorded as
`dedup_blocks_correction=true` is absent from runtime/state/ingested_ids.json or its
outbox copy does not carry a full digest.  A changed map or event stream (different
snapshot sha256) voids the classification, not the method.

Usage
-----
  python3 artifacts/worker-036/map_hash_registry_audit.py --out report.json
  python3 artifacts/worker-036/map_hash_registry_audit.py --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
DEFAULT_ROOT = Path(__file__).resolve().parents[2]
FULL64 = re.compile(r"[0-9a-f]{64}")
ZERO_PADDED_PREFIX = re.compile(r"[0-9a-f]{16}0{48}")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def digest(path: Path) -> dict:
    """Exact copy of research_map/astra_lifecycle.py:digest (controller's algorithm)."""
    if path.is_file():
        return {"kind": "file", "sha256": sha256_file(path), "bytes": path.stat().st_size}
    if path.is_dir():
        h = hashlib.sha256()
        files = sorted(x for x in path.rglob("*") if x.is_file() and not x.name.startswith("._"))
        for x in files:
            h.update(f"{x.relative_to(path)}\0{sha256_file(x)}\n".encode())
        return {"kind": "directory", "sha256": h.hexdigest(), "files": len(files),
                "bytes": sum(x.stat().st_size for x in files)}
    return {"kind": "absent", "sha256": None}


def hash_format(value) -> str:
    """Classify a declared digest value.  A 16-hex prefix + 48 zeros is a malformed digest.

    A genuine sha256 with a 48-zero tail has probability 2**-192; the prefix-check is
    therefore treated as the defect signature, not as a coincidence.
    """
    if value is None:
        return "none"
    if not isinstance(value, str):
        return "non_string"
    if FULL64.fullmatch(value):
        return "zero_padded_prefix" if ZERO_PADDED_PREFIX.fullmatch(value) else "full64"
    if re.fullmatch(r"[0-9A-Fa-f]{64}", value):
        return "full64_uppercase"
    return f"short_len{len(value)}"


def classify(kind: str, declared, recorded, fresh) -> str:
    if kind == "absent":
        return "absent"
    if hash_format(declared) == "zero_padded_prefix":
        return "declared_malformed"
    if recorded == fresh:
        if declared is None:
            return "unbound_no_declared"
        return "bound" if declared == fresh else "declared_stale"
    # recorded != fresh: the map's own measured value is behind the bytes on disk
    return "registry_stale" if kind == "file" else "registry_stale_live_dir"


def outbox_digest_index(root: Path) -> dict:
    """event_id -> list of {source, sha256, created_at} for every outbox JSON object."""
    index: dict = {}
    for path in sorted((root / "comms" / "outbox").rglob("*")):
        if not path.is_file():
            continue
        try:
            lines = path.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for ln in lines:
            ln = ln.strip()
            if not ln.startswith("{"):
                continue
            try:
                e = json.loads(ln)
            except Exception:
                continue
            if isinstance(e, dict) and e.get("event_id"):
                index.setdefault(e["event_id"], []).append({
                    "source": str(path.relative_to(root)),
                    "sha256": e.get("sha256"),
                    "created_at": e.get("created_at"),
                })
    return index


def scan_event_digests(root: Path) -> dict:
    """Find accepted artifact events whose sha256 is not a full digest; test dedup impact."""
    events_path = root / "research_map" / "events.jsonl"
    seen_path = root / "runtime" / "state" / "ingested_ids.json"
    out = {"events_scanned": 0, "artifact_events": 0, "defects": [],
           "dedup_blocks_correction": 0, "outbox_corrected": 0,
           "defects_with_later_full_revision": 0}
    if not events_path.is_file():
        return out
    seen = set()
    if seen_path.is_file():
        try:
            seen = set(json.loads(seen_path.read_text()))
        except Exception:
            seen = set()
    outbox = outbox_digest_index(root)
    artifact_seen = []
    with events_path.open(errors="replace") as f:
        for line in f:
            out["events_scanned"] += 1
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if not isinstance(e, dict) or e.get("event_type") != "artifact":
                continue
            out["artifact_events"] += 1
            artifact_seen.append(e)
            fmt = hash_format(e.get("sha256"))
            if fmt == "full64":
                continue
            copies = outbox.get(e.get("event_id"), [])
            full_copies = [c for c in copies if hash_format(c.get("sha256")) == "full64"]
            rec = {
                "_index": len(artifact_seen) - 1,
                "event_id": e.get("event_id"),
                "actor": e.get("actor"),
                "node_id": e.get("node_id"),
                "path": e.get("path"),
                "accepted_sha256": e.get("sha256"),
                "accepted_format": fmt,
                "received_at": e.get("_received_at"),
                "outbox_copies": copies,
                "outbox_full_digest_copies": len(full_copies),
                "outbox_corrected_sha256": full_copies[0]["sha256"] if full_copies else None,
                "in_ingested_ids": e.get("event_id") in seen,
                "dedup_blocks_correction": bool(full_copies) and e.get("event_id") in seen,
            }
            out["defects"].append(rec)
            if rec["outbox_corrected_sha256"]:
                out["outbox_corrected"] += 1
            if rec["dedup_blocks_correction"]:
                out["dedup_blocks_correction"] += 1
    for rec in out["defects"]:
        later = [x for x in artifact_seen[rec["_index"] + 1:]
                 if x.get("path") == rec["path"] and hash_format(x.get("sha256")) == "full64"]
        rec["later_full_digest_events"] = [
            {"event_id": x.get("event_id"), "received_at": x.get("_received_at"),
             "sha256": x.get("sha256")} for x in later]
        rec["superseded_by_later_full_digest"] = bool(later)
        del rec["_index"]
        if later:
            out["defects_with_later_full_revision"] += 1
    return out


def audit(root: Path) -> dict:
    map_path = root / "research_map" / "research_map.json"
    reg_path = root / "runtime" / "state" / "artifact_hashes.json"
    frozen_path = root / "artifacts" / "formulation" / "FROZEN.json"
    events_path = root / "research_map" / "events.jsonl"
    seen_path = root / "runtime" / "state" / "ingested_ids.json"

    m = json.loads(map_path.read_text())
    report: dict = {
        "task_id": "W036-MAPREG-01",
        "actor": "worker-036",
        "created_at": now(),
        "schema_version": "0.2",
        "question": ("Do the map's measured artifact hashes and the checkpoint hash registry "
                     "still equal the bytes on disk, and what does each "
                     "declared_hash_matches_measured flag actually mean?"),
        "snapshot": {
            "root": str(root),
            "map": str(map_path.relative_to(root)),
            "map_sha256": sha256_file(map_path),
            "map_updated_at": m.get("updated_at"),
            "artifact_hashes_path": str(reg_path.relative_to(root)),
            "artifact_hashes_sha256": sha256_file(reg_path) if reg_path.is_file() else None,
            "frozen_manifest": str(frozen_path.relative_to(root)),
            "frozen_manifest_sha256": sha256_file(frozen_path) if frozen_path.is_file() else None,
            "events": str(events_path.relative_to(root)),
            "events_sha256": sha256_file(events_path) if events_path.is_file() else None,
            "ingested_ids": str(seen_path.relative_to(root)),
            "ingested_ids_sha256": sha256_file(seen_path) if seen_path.is_file() else None,
            "method": "digest() copied from research_map/astra_lifecycle.py",
        },
        "nodes": [],
        "checkpoint_registry": [],
        "frozen_artifacts": [],
        "event_digest_scan": {},
        "summary": {},
        "findings": [],
    }

    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            art = n.get("artifact")
            if not art:
                continue
            d = digest(root / art)
            declared = n.get("artifact_sha256")
            recorded = n.get("artifact_sha256_measured")
            rec = {
                "node_id": n.get("id"),
                "group": g.get("id"),
                "class_id": n.get("class_id"),
                "artifact": art,
                "kind": d["kind"],
                "exists": d["kind"] != "absent",
                "bytes": d.get("bytes"),
                "artifact_mtime": (datetime.fromtimestamp((root / art).stat().st_mtime, CST)
                                   .isoformat(timespec="seconds")) if d["kind"] == "file" else None,
                "map_declared_sha256": declared,
                "declared_format": hash_format(declared),
                "map_measured_sha256": recorded,
                "measured_format": hash_format(recorded),
                "fresh_sha256": d["sha256"],
                "declared_matches_fresh": (declared == d["sha256"]) if declared else None,
                "map_measured_matches_fresh": (recorded == d["sha256"]) if recorded else None,
                "registry_drift": (recorded != d["sha256"]) if recorded else None,
                "map_flag_declared_hash_matches_measured": n.get("declared_hash_matches_measured"),
                "classification": classify(d["kind"], declared, recorded, d["sha256"]),
            }
            report["nodes"].append(rec)

    reg = json.loads(reg_path.read_text()) if reg_path.is_file() else {}
    for path, r in sorted((reg.get("hashes") or {}).items()):
        p = root / path
        d = digest(p)
        rec = {
            "path": path,
            "node_id": r.get("node_id"),
            "status": r.get("status"),
            "registry_sha256": r.get("sha256"),
            "registry_format": hash_format(r.get("sha256")),
            "registry_bytes": r.get("bytes"),
            "fresh_sha256": d["sha256"],
            "fresh_bytes": d.get("bytes"),
            "matches": r.get("sha256") == d["sha256"],
            "kind": d["kind"],
        }
        report["checkpoint_registry"].append(rec)

    for f in m.get("frozen_artifacts", []):
        if not f.get("active"):
            continue
        d = digest(root / f.get("path", ""))
        report["frozen_artifacts"].append({
            "path": f.get("path"),
            "node_id": f.get("node_id"),
            "frozen_sha256": f.get("sha256"),
            "frozen_format": hash_format(f.get("sha256")),
            "fresh_sha256": d["sha256"],
            "kind": d["kind"],
            "matches": f.get("sha256") == d["sha256"],
            "frozen_at": f.get("frozen_at"),
            "reason": f.get("reason"),
        })

    report["event_digest_scan"] = scan_event_digests(root)

    counts: dict = {}
    for rec in report["nodes"]:
        counts[rec["classification"]] = counts.get(rec["classification"], 0) + 1
    registry_mismatches = [r for r in report["checkpoint_registry"] if not r["matches"]]
    registry_malformed = [r for r in report["checkpoint_registry"]
                          if r["registry_format"] == "zero_padded_prefix"]
    frozen_mismatches = [r for r in report["frozen_artifacts"] if not r["matches"]]
    frozen_malformed = [r for r in report["frozen_artifacts"]
                        if r["frozen_format"] == "zero_padded_prefix"]
    malformed_nodes = [r for r in report["nodes"] if r["classification"] == "declared_malformed"]
    registry_drift_nodes = [r for r in report["nodes"] if r.get("registry_drift")]
    scan = report["event_digest_scan"]
    report["summary"] = {
        "nodes_audited": len(report["nodes"]),
        "classification_counts": counts,
        "nodes_with_registry_drift": len(registry_drift_nodes),
        "checkpoint_registry_entries": len(report["checkpoint_registry"]),
        "checkpoint_registry_mismatches": len(registry_mismatches),
        "checkpoint_registry_malformed": len(registry_malformed),
        "active_frozen_entries": len(report["frozen_artifacts"]),
        "active_frozen_mismatches": len(frozen_mismatches),
        "active_frozen_malformed": len(frozen_malformed),
        "malformed_declared_nodes": len(malformed_nodes),
        "accepted_artifact_events": scan.get("artifact_events", 0),
        "malformed_event_digests": len(scan.get("defects", [])),
        "defects_with_later_full_revision": scan.get("defects_with_later_full_revision", 0),
        "event_corrections_in_outbox": scan.get("outbox_corrected", 0),
        "corrections_dedup_blocked": scan.get("dedup_blocks_correction", 0),
        "hard_findings": 0,
        "soft_findings": 0,
    }

    F = report["findings"]

    def finding(fid, severity, scope, statement, evidence_refs, action):
        F.append({"finding_id": fid, "severity": severity, "scope": scope,
                  "statement": statement, "evidence_refs": evidence_refs, "action": action})
        report["summary"]["hard_findings" if severity == "hard" else "soft_findings"] += 1

    map_ref = f"research_map/research_map.json#{report['snapshot']['map_sha256'][:12]}"
    events_ref = f"research_map/events.jsonl#{str(report['snapshot']['events_sha256'])[:12]}"
    for rec in report["nodes"]:
        if rec["declared_format"] == "zero_padded_prefix":
            finding(
                "W036-F1", "hard", rec["node_id"],
                (f"map declared artifact_sha256 for {rec['artifact']} is "
                 f"{str(rec['map_declared_sha256'])[:16]} + 48 zeros -- a zero-padded 16-hex "
                 f"prefix, not a sha256.  Full disk digest at scan time is "
                 f"{str(rec['fresh_sha256'])[:12]}; map artifact_sha256_measured snapshot value "
                 f"is {str(rec['map_measured_sha256'])[:12]} "
                 f"(equal={rec['map_measured_matches_fresh']}).  "
                 "declared_hash_matches_measured=false here reports malformed input, not drift"),
                [f"{rec['artifact']}#{str(rec['fresh_sha256'])[:12]}", map_ref],
                "repair the declared value from a full-digest event; reject this format at ingest")
        if rec["kind"] == "file" and rec["map_measured_matches_fresh"] is False:
            finding(
                "W036-F2", "hard", rec["node_id"],
                (f"map artifact_sha256_measured {str(rec['map_measured_sha256'])[:12]} != fresh "
                 f"{str(rec['fresh_sha256'])[:12]} for {rec['artifact']}; any gate binding to the "
                 "map-recorded hash is stale"),
                [f"{rec['artifact']}#{str(rec['fresh_sha256'])[:12]}", map_ref],
                "re-measure at gate time; do not bind a verdict to the recorded hash")
        elif rec["kind"] == "directory" and rec["map_measured_matches_fresh"] is False:
            finding(
                "W036-F3", "soft", rec["node_id"],
                (f"live directory {rec['artifact']} recorded hash "
                 f"{str(rec['map_measured_sha256'])[:12]} != fresh {str(rec['fresh_sha256'])[:12]}; "
                 "the directory changes as reviews are added, so its recorded hash cannot be a "
                 "stable binding target"),
                [f"{rec['artifact']}#{str(rec['fresh_sha256'])[:12]}", map_ref],
                "bind verdicts to per-file hashes inside reviews/, not to the directory digest")
        if (rec["declared_format"] != "zero_padded_prefix"
                and rec["declared_matches_fresh"] is False
                and rec["map_measured_matches_fresh"] is True):
            finding(
                "W036-F4", "soft", rec["node_id"],
                (f"map declared artifact_sha256 {str(rec['map_declared_sha256'])[:12]} is an older "
                 f"event hash; fresh disk {str(rec['fresh_sha256'])[:12]} equals "
                 f"artifact_sha256_measured {str(rec['map_measured_sha256'])[:12]}. "
                 "declared_hash_matches_measured=false here means a stale declaration, not drift"),
                [f"{rec['artifact']}#{str(rec['fresh_sha256'])[:12]}", map_ref],
                "refresh the declared hash from the latest artifact event before citing the flag")

    for rec in scan.get("defects", []):
        action = ("validate sha256 format at ingest and provide a supersede path (new event_id "
                  "plus supersedes=old); re-emitting the same event_id is silently dropped")
        repair = ("a later full-digest revision for this path is already in the accepted stream "
                  f"({', '.join(x['event_id'] for x in rec['later_full_digest_events'][-3:])}); "
                  "applying it repairs the node binding"
                  if rec["superseded_by_later_full_digest"] else
                  "no later full-digest artifact event for this path exists in the accepted stream")
        if rec["dedup_blocks_correction"]:
            finding(
                "W036-F5", "hard", str(rec["node_id"]),
                (f"accepted artifact event {rec['event_id']} ({rec['actor']}, {rec['path']}) "
                 f"carries {rec['accepted_format']} as sha256; the outbox copy for the same "
                 f"event_id now carries the full digest "
                 f"{str(rec['outbox_corrected_sha256'])[:12]}, but the event_id is in "
                 "runtime/state/ingested_ids.json, so comms.py dedup (comms.py:303-305) will "
                 f"count the in-place correction as a duplicate forever.  {repair}"),
                [events_ref, f"{rec['outbox_copies'][0]['source']}#outbox-copy",
                 f"runtime/state/ingested_ids.json#{str(report['snapshot']['ingested_ids_sha256'])[:12]}"],
                action)
        else:
            finding(
                "W036-F6", "hard", str(rec["node_id"]),
                (f"accepted artifact event {rec['event_id']} ({rec['actor']}, {rec['path']}) "
                 f"carries {rec['accepted_format']} as sha256 and no full-digest outbox "
                 f"correction was found.  {repair}"),
                [events_ref],
                action)
    for r in registry_malformed:
        finding("W036-F7", "hard", str(r["node_id"]),
                f"checkpoint registry stores {r['registry_format']} for {r['path']}",
                [f"runtime/state/artifact_hashes.json#{str(report['snapshot']['artifact_hashes_sha256'])[:12]}"],
                "registry writer must reject non-digest values")
    for r in registry_mismatches:
        finding(
            "W036-F8", "hard", str(r["node_id"]),
            (f"checkpoint registry hash {str(r['registry_sha256'])[:12]} != fresh "
             f"{str(r['fresh_sha256'])[:12]} for {r['path']}"),
            [f"runtime/state/artifact_hashes.json#{str(report['snapshot']['artifact_hashes_sha256'])[:12]}",
             f"{r['path']}#{str(r['fresh_sha256'])[:12]}"],
            "refresh runtime/state/artifact_hashes.json at the next checkpoint")
    for r in frozen_malformed:
        finding("W036-F9", "hard", str(r["node_id"]),
                f"active frozen_artifacts entry {r['path']} pins {r['frozen_format']}",
                [map_ref], "re-pin with a full digest")
    for r in frozen_mismatches:
        finding(
            "W036-F10", "hard", str(r["node_id"]),
            (f"active frozen_artifacts entry {r['path']} pins {str(r['frozen_sha256'])[:12]} but disk "
             f"is {str(r['fresh_sha256'])[:12]}"),
            [f"{r['path']}#{str(r['fresh_sha256'])[:12]}", map_ref],
            "re-freeze or supersede the map entry; do not gate on a stale pin")

    report["falsifier"] = (
        "Re-run against the same research_map.json and events.jsonl sha256 recorded in "
        "report.snapshot.  FALSIFIED if (a) any registry_stale / registry_stale_live_dir node "
        "equals its recorded hash on re-measure; or (b) any declared_stale node's declared hash "
        "equals its fresh digest; or (c) any bound node fails either equality; or (d) any "
        "declared_malformed node's declared field is a full 64-hex digest without the 48-zero "
        "tail; or (e) any event with dedup_blocks_correction=true is absent from ingested_ids.json "
        "or its outbox copy lacks a full digest."
    )
    return report


def selftest() -> int:
    """Verify digest() agrees with a direct recomputation and hash_format separates defects."""
    import tempfile
    ok = True
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        (p / "a.txt").write_text("alpha\n")
        (p / "sub").mkdir()
        (p / "sub" / "b.txt").write_text("beta\n")
        f = digest(p / "a.txt")
        ok &= f == {"kind": "file", "sha256": hashlib.sha256(b"alpha\n").hexdigest(), "bytes": 6}
        d = digest(p)
        ha = hashlib.sha256(b"alpha\n").hexdigest()
        hb = hashlib.sha256(b"beta\n").hexdigest()
        h = hashlib.sha256()
        h.update(f"a.txt\0{ha}\n".encode())
        h.update(f"sub/b.txt\0{hb}\n".encode())
        ok &= d["sha256"] == h.hexdigest() and d["files"] == 2
        ok &= digest(p / "absent").get("kind") == "absent"
    good = "a" * 64
    bad = "a" * 16 + "0" * 48
    cases = [(good, "full64"), (bad, "zero_padded_prefix"), (None, "none"),
             ("abc123", "short_len6"), (17, "non_string"), ("A" * 64, "full64_uppercase")]
    for value, want in cases:
        got = hash_format(value)
        if got != want:
            print(f"selftest: FAIL hash_format({value!r})={got} want {want}")
            ok = False
    ok &= classify("file", bad, "a" * 64, "a" * 64) == "declared_malformed"
    ok &= classify("file", good, good, good) == "bound"
    ok &= classify("file", good[:16], good, good) == "declared_stale"
    print("selftest: PASS" if ok else "selftest: FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    report = audit(Path(args.root).resolve())
    text = json.dumps(report, indent=2, sort_keys=False) + "\n"
    if args.out:
        Path(args.out).write_text(text)
    else:
        sys.stdout.write(text)
    return 1 if report["summary"]["hard_findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
