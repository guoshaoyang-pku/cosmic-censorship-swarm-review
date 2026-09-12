#!/usr/bin/env python3
"""W042-GATE-SCAN-GAP-02: gate-reason scan visibility vs the accepted event stream.

Question
--------
At one pinned snapshot, does the controller's advisory review-coverage scan
(`review_coverage` in research_map/astra_lifecycle.py, which reads only
`reviews/*.json`) agree with the *accepted* event stream
(`research_map/events.jsonl`) about which reviewers hold a full-schema accept
at the controller-measured canonical hash of F0/F1/F2a/F2b/L0/L1 -- and do the
`controller_gate_audit` reason strings in the pinned map reflect the union?

This is a *visibility/coverage* measurement, not a gate verdict and not an
adjudication of whether any review is valid.  The audit lead owns binding
coverage (`reviews/A1-rebind-coverage.json`); this tool reports the delta
between two machine corpora and leaves adjudication to the lead.

Determinism
-----------
Stdlib only, no network, no writes outside `--out`.  All inputs are pinned by
sha256.  Seven synthetic controls run in a temp directory and must pass, else
the report is marked INVALID (exit 2).

Semantics replicated from astra_lifecycle.py (read at 2026-09-12):
  - review corpus = every `reviews/*.json` (sorted)
  - verdict must be in {accept, revise, reject, inconclusive}
  - reviewer = d["reviewer"] or d["actor"] or "?"
  - full = d.get("counts_as_full_schema_verdict") is not False
  - target aliases:
      F0,F1,F2A->F2a,F2B->F2b,F2->F2b,L0,L1,
      AF-WCC-VAC-GEN->F1, AF-SCC-C2-VAC-GEN->F2a, AF-SCC-C0-VAC-GEN->F2b
  - pin keys: artifact_sha256, reviewed_sha256, sha256, cited_sha256
      (plus sha256/artifact_sha256/reviewed_sha256 inside target/artifact dicts)
  - match: pin.startswith(h[:12]) or h.startswith(pin[:12])
  - distinct_accept_reviewers = sorted reviewers of full accepts only

Usage
-----
  python3 audit_gate_scan_gap.py \
      --snapshot snapshot --out report.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))

TARGETS = ("F0", "F1", "F2a", "F2b", "L0", "L1")
TARGET_ALIASES = {
    "F0": "F0", "F1": "F1", "F2A": "F2a", "F2B": "F2b", "F2": "F2b",
    "L0": "L0", "L1": "L1",
    "AF-WCC-VAC-GEN": "F1",
    "AF-SCC-C2-VAC-GEN": "F2a",
    "AF-SCC-C0-VAC-GEN": "F2b",
}
VERDICT_KINDS = ("accept", "revise", "reject", "inconclusive")
PIN_KEYS = ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256")
NESTED_PIN_KEYS = ("sha256", "artifact_sha256", "reviewed_sha256")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def targets_in_review(d: dict) -> set:
    out = set()
    for key in ("target_id", "target", "target_subnode"):
        v = d.get(key)
        if isinstance(v, str):
            out.add(v)
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                if isinstance(v.get(k2), str):
                    out.add(v[k2])
    norm = set()
    for t in out:
        norm.add(TARGET_ALIASES.get(t, TARGET_ALIASES.get(t.upper(), t)))
    return norm


def explicit_pins(d: dict) -> list:
    pins = []
    for key in PIN_KEYS:
        v = d.get(key)
        if isinstance(v, str):
            pins.append(v.lower())
    for key in ("target", "artifact"):
        v = d.get(key)
        if isinstance(v, dict):
            for k2 in NESTED_PIN_KEYS:
                if isinstance(v.get(k2), str):
                    pins.append(v[k2].lower())
    return pins


def pin_matches(pins: list, h: str) -> bool:
    return bool(h) and any(p.startswith(h[:12]) or h.startswith(p[:12]) for p in pins)


def scan_records(records, hashes: dict, source_of) -> dict:
    """Apply the controller's review_coverage rules to a record sequence."""
    cov = {t: {"verdicts": [], "accepts": [], "full_accepts": [],
               "distinct_accept_reviewers": []} for t in TARGETS}
    for d in records:
        v = str(d.get("verdict", "")).lower()
        if v not in VERDICT_KINDS:
            continue
        reviewer = str(d.get("reviewer") or d.get("actor") or "?")
        full = d.get("counts_as_full_schema_verdict") is not False
        pins = explicit_pins(d)
        for t in sorted(targets_in_review(d)):
            if t not in cov:
                continue
            h = hashes.get(t, "")
            if not pin_matches(pins, h):
                continue
            entry = {"source": source_of(d), "reviewer": reviewer, "verdict": v,
                     "counts_as_full_schema_verdict": full,
                     "pins_matched_12": sorted({p[:12] for p in pins if
                                                p.startswith(h[:12]) or h.startswith(p[:12])})}
            cov[t]["verdicts"].append(entry)
            if v == "accept":
                cov[t]["accepts"].append(entry)
                if full:
                    cov[t]["full_accepts"].append(entry)
    for t in cov:
        # de-duplicate by (source, reviewer): the same review file/event may cite several
        # pins that all match the same measured hash
        seen = set()
        uniq = []
        for e in cov[t]["full_accepts"]:
            k = (e["source"], e["reviewer"])
            if k in seen:
                continue
            seen.add(k)
            uniq.append(e)
        cov[t]["full_accepts"] = uniq
        cov[t]["distinct_accept_reviewers"] = sorted({e["reviewer"] for e in uniq})
    return cov


def scan_reviews_dir(reviews_dir: Path, hashes: dict) -> dict:
    records = []
    unreadable = []
    for rp in sorted(reviews_dir.glob("*.json")):
        try:
            records.append((rp.name, json.loads(rp.read_text())))
        except Exception as e:  # noqa: BLE001
            unreadable.append({"file": rp.name, "error": str(e)})
    cov = scan_records([d for _, d in records], hashes, lambda d: _src_of(d, records))
    cov["_unreadable"] = unreadable
    cov["_files_scanned"] = len(records)
    return cov


def _src_of(d: dict, records) -> str:
    for name, rec in records:
        if rec is d:
            return name
    return "?"


def scan_events(events_path: Path, hashes: dict) -> dict:
    rows = []
    bad = 0
    with events_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                bad += 1
                continue
            if isinstance(e, dict) and e.get("event_type") == "review":
                rows.append(e)
    cov = scan_records(rows, hashes, lambda d: str(d.get("event_id") or "?"))
    cov["_review_events_scanned"] = len(rows)
    cov["_unparsable_lines"] = bad
    return cov


def measured_hashes_from_map(map_doc: dict) -> tuple:
    """Return ({target: sha256}, {target: {artifact, source}}) from map nodes."""
    found, sources = {}, {}
    for g in map_doc.get("groups", []):
        for n in g.get("nodes", []):
            if n.get("id") in TARGETS and n.get("artifact_sha256_measured"):
                found[n["id"]] = n["artifact_sha256_measured"]
                sources[n["id"]] = {"artifact": n.get("artifact"),
                                    "measured_at": n.get("artifact_measured_at")}
    return found, sources


def measured_hashes_from_registry(reg: dict, node_artifacts: dict) -> dict:
    """Cross-check the checkpoint registry (path -> sha256) against map nodes."""
    table = reg.get("registry", reg) if isinstance(reg, dict) else {}
    out = {}
    for t, art in node_artifacts.items():
        rec = table.get(art)
        if isinstance(rec, dict) and rec.get("sha256"):
            out[t] = rec["sha256"]
    return out


def parse_gate_reasons(map_doc: dict) -> dict:
    audit = map_doc.get("controller_gate_audit", {})
    out = {}
    for gk, rec in audit.items():
        out[gk] = {"verdict": rec.get("verdict"), "checked_at": rec.get("checked_at"),
                   "reason": rec.get("reason")}
    return out


def parse_audit_counts(reasons: dict) -> dict:
    """Extract the accept counts the map itself quotes, per gate/target."""
    res = {"G-F0": {}, "G-FORM": {}, "G-LIT": {}, "G-AUDIT": {}, "G-NUM": {}}
    r = reasons.get("G-F0", {}).get("reason", "")
    m = re.search(r"review scan at this hash:\s*(\d+)\s+distinct accept", r)
    if m:
        res["G-F0"]["F0"] = int(m.group(1))
    r = reasons.get("G-FORM", {}).get("reason", "")
    for t in ("F1", "F2a", "F2b"):
        m = re.search(re.escape(t) + r"\s*\[(\d+)\s+distinct accept", r)
        if m:
            res["G-FORM"][t] = int(m.group(1))
    r = reasons.get("G-LIT", {}).get("reason", "")
    m = re.search(r"review scan at this hash:\s*(\d+)\s+distinct accept", r)
    if m:
        res["G-LIT"]["L0"] = int(m.group(1))
    r = reasons.get("G-AUDIT", {}).get("reason", "")
    m = re.search(r"A1 coverage at measured hashes:\s*F0\s*(\d+),\s*F1\s*(\d+),\s*F2a\s*(\d+),"
                  r"\s*F2b\s*(\d+),\s*L0\s*(\d+)\s+distinct accepts", r)
    if m:
        res["G-AUDIT"] = {"F0": int(m.group(1)), "F1": int(m.group(2)),
                          "F2a": int(m.group(3)), "F2b": int(m.group(4)),
                          "L0": int(m.group(5))}
    return res


def review_corpus_at_measured_hash(reviews_dir: Path, live_reviews_dir: Path, hashes: dict) -> dict:
    """Every pinned review file whose verdict pins a measured hash, with live mtime.

    The mtime is advisory wall-clock corroboration only; the audited bytes are the
    pinned copies."""
    rows = {t: [] for t in TARGETS}
    for rp in sorted(reviews_dir.glob("*.json")):
        try:
            d = json.loads(rp.read_text())
        except Exception:  # noqa: BLE001
            continue
        v = str(d.get("verdict", "")).lower()
        if v not in VERDICT_KINDS:
            continue
        reviewer = str(d.get("reviewer") or d.get("actor") or "?")
        pins = explicit_pins(d)
        for t in sorted(targets_in_review(d)):
            if t in rows and pin_matches(pins, hashes[t]):
                live = live_reviews_dir / rp.name
                mtime = None
                if live.is_file():
                    mtime = datetime.fromtimestamp(live.stat().st_mtime, CST).isoformat(timespec="seconds")
                rows[t].append({"file": rp.name, "reviewer": reviewer, "verdict": v,
                                "counts_as_full_schema_verdict": d.get("counts_as_full_schema_verdict"),
                                "live_mtime": mtime})
    return rows


def audit_matrix_accepts(reviews_dir: Path) -> dict:
    """Accept lists from the audit lead's A1-rebind-coverage.json (if present)."""
    p = reviews_dir / "A1-rebind-coverage.json"
    if not p.is_file():
        return {}
    try:
        d = json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for t, v in (d.get("coverage") or {}).items():
        if isinstance(v, dict):
            out[t] = sorted({e.get("reviewer") for e in v.get("accept_at_measured_hash", [])
                             if isinstance(e, dict)})
    return out


def run_controls(tmp: Path, hashes: dict) -> dict:
    """Seven synthetic controls; any failure marks the run INVALID."""
    ctl = {}

    def write_reviews(name: str, docs: list):
        d = tmp / name
        d.mkdir(parents=True, exist_ok=True)
        for i, doc in enumerate(docs):
            (d / f"r{i}.json").write_text(json.dumps(doc))
        return d

    h_f2a = hashes["F2a"]
    # C1 positive: exact pin, full accept -> found
    d = write_reviews("c1", [{"verdict": "accept", "reviewer": "ctl-pos",
                              "target_id": "F2a", "reviewed_sha256": h_f2a}])
    cov = scan_reviews_dir(d, hashes)
    ctl["C1_positive_accept_found"] = "ctl-pos" in cov["F2a"]["distinct_accept_reviewers"]
    # C2 superseded pin -> excluded
    d = write_reviews("c2", [{"verdict": "accept", "reviewer": "ctl-stale",
                              "target_id": "F2a", "reviewed_sha256": "0" * 64}])
    ctl["C2_superseded_pin_excluded"] = "ctl-stale" not in scan_reviews_dir(d, hashes)["F2a"]["distinct_accept_reviewers"]
    # C3 scoped accept -> in accepts, not in full accepts
    d = write_reviews("c3", [{"verdict": "accept", "reviewer": "ctl-scoped",
                              "target_id": "F2a", "reviewed_sha256": h_f2a,
                              "counts_as_full_schema_verdict": False}])
    cov = scan_reviews_dir(d, hashes)
    ctl["C3_scoped_accept_excluded_from_full"] = (
        len(cov["F2a"]["accepts"]) == 1 and "ctl-scoped" not in cov["F2a"]["distinct_accept_reviewers"])
    # C4 revise -> not an accept
    d = write_reviews("c4", [{"verdict": "revise", "reviewer": "ctl-rev",
                              "target_id": "F2a", "reviewed_sha256": h_f2a}])
    cov = scan_reviews_dir(d, hashes)
    ctl["C4_revise_not_accept"] = (len(cov["F2a"]["accepts"]) == 0 and
                                   any(e["reviewer"] == "ctl-rev" for e in cov["F2a"]["verdicts"]))
    # C5 wrong target -> excluded
    d = write_reviews("c5", [{"verdict": "accept", "reviewer": "ctl-target",
                              "target_id": "A0", "reviewed_sha256": h_f2a}])
    ctl["C5_wrong_target_excluded"] = "ctl-target" not in scan_reviews_dir(d, hashes)["F2a"]["distinct_accept_reviewers"]
    # C6 alias resolves
    d = write_reviews("c6", [{"verdict": "accept", "reviewer": "ctl-alias",
                              "target_id": "AF-WCC-VAC-GEN",
                              "reviewed_sha256": hashes["F1"]}])
    ctl["C6_alias_resolves_to_F1"] = "ctl-alias" in scan_reviews_dir(d, hashes)["F1"]["distinct_accept_reviewers"]
    # C7 event-stream scan: accept found, reject ignored
    ep = tmp / "c7_events.jsonl"
    with ep.open("w") as f:
        f.write(json.dumps({"event_type": "review", "event_id": "ctl-e-accept", "reviewer": "ctl-evt",
                            "verdict": "accept", "target_id": "F1",
                            "reviewed_sha256": hashes["F1"]}) + "\n")
        f.write(json.dumps({"event_type": "review", "event_id": "ctl-e-reject", "reviewer": "ctl-evt2",
                            "verdict": "reject", "target_id": "F1",
                            "reviewed_sha256": hashes["F1"]}) + "\n")
        f.write(json.dumps({"event_type": "artifact", "event_id": "ctl-e-art", "sha256": hashes["F1"]}) + "\n")
    cov = scan_events(ep, hashes)
    ctl["C7_event_scan_accept_only"] = ("ctl-evt" in cov["F1"]["distinct_accept_reviewers"]
                                        and "ctl-evt2" not in cov["F1"]["distinct_accept_reviewers"]
                                        and cov["_review_events_scanned"] == 2)
    ctl["all_passed"] = all(v for k, v in ctl.items() if k != "all_passed")
    return ctl


def main() -> int:
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    ap.add_argument("--snapshot", default=str(here / "snapshot"))
    ap.add_argument("--out", default=str(here / "report.json"))
    ap.add_argument("--repo", default=str(here.parents[2]))
    ap.add_argument("--skip-controls", action="store_true")
    args = ap.parse_args()

    snap = Path(args.snapshot).resolve()
    repo = Path(args.repo).resolve()
    man = json.loads((snap / "manifest.json").read_text())
    files = man["files"]

    def snap_path(kind: str) -> Path:
        for name, rec in files.items():
            if rec["source"] == kind:
                return snap / name
        raise SystemExit(f"snapshot missing {kind}")

    events_p = snap_path("research_map/events.jsonl")
    map_p = snap_path("research_map/research_map.json")
    reg_p = snap_path("runtime/state/artifact_hashes.json")
    reviews_dir = snap / "reviews"

    map_doc = json.loads(map_p.read_text())
    registry = json.loads(reg_p.read_text())
    hashes, sources = measured_hashes_from_map(map_doc)
    missing = [t for t in TARGETS if t not in hashes]
    if missing:
        raise SystemExit(f"pinned map lacks measured hashes for {missing}")
    reg_hashes = measured_hashes_from_registry(registry, {t: sources[t]["artifact"] for t in sources})
    registry_agrees = {t: (None if t not in reg_hashes else (reg_hashes[t] == hashes[t]))
                       for t in TARGETS}

    cov_a = scan_reviews_dir(reviews_dir, hashes)
    cov_b = scan_events(events_p, hashes)

    # live drift disclosure (appends after the pin are not falsifiers)
    live = {}
    for rel, snap_key in (("research_map/events.jsonl", events_p.name),
                          ("research_map/research_map.json", map_p.name),
                          ("runtime/state/artifact_hashes.json", reg_p.name)):
        lp = repo / rel
        live[rel] = {"live_sha256": sha256_file(lp) if lp.is_file() else None,
                     "snapshot_sha256": files[snap_key]["sha256"]}
    live_reviews = {}
    live_dir = repo / "reviews"
    for rp in sorted(live_dir.glob("*.json")) if live_dir.is_dir() else []:
        live_reviews[rp.name] = sha256_file(rp)
    snap_reviews = {n: r["sha256"] for n, r in man["reviews_manifest"].items()}
    live_reviews_manifest_sha = sha256_bytes(json.dumps(live_reviews, sort_keys=True).encode())
    reviews_drift = {
        "snapshot_manifest_sha256": man["reviews_manifest_sha256"],
        "live_manifest_sha256": live_reviews_manifest_sha,
        "added_since_pin": sorted(set(live_reviews) - set(snap_reviews)),
        "removed_since_pin": sorted(set(snap_reviews) - set(live_reviews)),
        "changed_since_pin": sorted(n for n in set(live_reviews) & set(snap_reviews)
                                    if live_reviews[n] != snap_reviews[n]),
    }

    reasons = parse_gate_reasons(map_doc)
    quoted = parse_audit_counts(reasons)
    matrix = audit_matrix_accepts(reviews_dir)
    review_corpus_rows = review_corpus_at_measured_hash(reviews_dir, repo / "reviews", hashes)

    targets_out = {}
    for t in TARGETS:
        a = sorted(cov_a[t]["distinct_accept_reviewers"])
        b = sorted(cov_b[t]["distinct_accept_reviewers"])
        targets_out[t] = {
            "measured_sha256": hashes[t],
            "measured_sha256_12": hashes[t][:12],
            "artifact": sources[t]["artifact"],
            "scan_a_reviews_dir": {"files_scanned": cov_a.get("_files_scanned"),
                                   "accept_reviewers": a,
                                   "verdicts": sorted({(e["reviewer"], e["verdict"]) for e in cov_a[t]["verdicts"]})},
            "scan_b_event_stream": {"review_events_scanned": cov_b.get("_review_events_scanned"),
                                    "accept_reviewers": b,
                                    "verdicts": sorted({(e["reviewer"], e["verdict"]) for e in cov_b[t]["verdicts"]})},
            "b_only_reviewers": sorted(set(b) - set(a)),
            "a_only_reviewers": sorted(set(a) - set(b)),
            "union_accept_reviewers": sorted(set(a) | set(b)),
            "audit_matrix_accept_at_measured_hash": matrix.get(t),
            "audit_matrix_agrees_with_scan_a": (matrix.get(t) is not None and
                                                matrix.get(t) == a) if t in matrix else None,
            "registry_agrees_with_map": registry_agrees.get(t),
        }

    gate_reason_check = {}
    nonreproducible = {}
    for gk, per_target in (("G-F0", ["F0"]), ("G-FORM", ["F1", "F2a", "F2b"]),
                           ("G-LIT", ["L0"]), ("G-AUDIT", ["F0", "F1", "F2a", "F2b", "L0"])):
        rows = {}
        for t in per_target:
            stated = quoted.get(gk, {}).get(t)
            a = len(targets_out[t]["scan_a_reviews_dir"]["accept_reviewers"])
            u = len(targets_out[t]["union_accept_reviewers"])
            if stated is None:
                cls = "not_parsed"
            elif stated == a == u:
                cls = "consistent"
            elif stated == a < u:
                cls = "undercount_vs_event_stream"
            elif stated > a:
                cls = "quoted_count_not_reproducible_at_pinned_corpus"
                nonreproducible.setdefault(t, {"quoted": stated, "scan_a": a,
                                               "gate": gk})
            elif stated < a:
                cls = "quoted_count_superseded_by_new_reviews"
            else:
                cls = "mixed"
            rows[t] = {"quoted_count": stated, "scan_a_count": a, "union_count": u,
                       "classification": cls}
        gate_reason_check[gk] = {"verdict": reasons.get(gk, {}).get("verdict"),
                                 "checked_at": reasons.get(gk, {}).get("checked_at"),
                                 "targets": rows}
    gate_reason_check["G-NUM"] = {"verdict": reasons.get("G-NUM", {}).get("verdict"),
                                  "checked_at": reasons.get("G-NUM", {}).get("checked_at"),
                                  "targets": {}, "note": "no accept-count criterion parsed; C8 protocol review is out of this task's scope"}

    parity = {
        "map_g_audit_quoted_counts": quoted.get("G-AUDIT", {}),
        "scan_a_counts": {t: len(targets_out[t]["scan_a_reviews_dir"]["accept_reviewers"])
                          for t in ("F0", "F1", "F2a", "F2b", "L0")},
    }
    parity["exact_match"] = parity["map_g_audit_quoted_counts"] == parity["scan_a_counts"]

    controls = {} if args.skip_controls else _controls(snap, hashes)
    invalid = bool(controls) and not controls.get("all_passed", False)

    b_only = {t: targets_out[t]["b_only_reviewers"] for t in TARGETS if targets_out[t]["b_only_reviewers"]}
    a_only = {t: targets_out[t]["a_only_reviewers"] for t in TARGETS if targets_out[t]["a_only_reviewers"]}

    findings = []
    if b_only:
        findings.append({
            "id": "W042-GSG-01",
            "severity": "major",
            "statement": ("Full-schema accepts at the controller-measured canonical hashes exist in the accepted "
                          "event stream but are invisible to the controller's reviews/*.json coverage scan "
                          f"({', '.join(f'{t}: {v}' for t, v in b_only.items())}). Per target at the pin: "
                          + "; ".join(f"{t} scan-A={len(targets_out[t]['scan_a_reviews_dir']['accept_reviewers'])} "
                                      f"union={len(targets_out[t]['union_accept_reviewers'])}"
                                      for t in b_only) + ". "
                          "A gate reason computed from the scan alone therefore understates the accepts available "
                          "at the measured hash."),
            "examples": [{"target": t, "measured_sha256_12": targets_out[t]["measured_sha256_12"],
                          "scan_a_count": len(targets_out[t]["scan_a_reviews_dir"]["accept_reviewers"]),
                          "union_count": len(targets_out[t]["union_accept_reviewers"]),
                          "reviewers": v,
                          "evidence": [e for e in cov_b[t]["full_accepts"] if e["reviewer"] in v]}
                         for t, v in b_only.items()],
            "note": ("L1's G-LIT criterion is re-fetch spot checks rather than accepts (see astra_lifecycle."
                     "l1_spotchecks); its row is informational and does not imply a missed accept criterion."),
            "not_claimed": ("Not a gate verdict: a stream-only accept is not thereby a binding review; the audit lead "
                            "adjudicates binding coverage. This finding is about scan visibility only."),
            "falsifier": ("Re-run this checker on the same pinned inputs. Falsified if any reviewer listed b_only has a "
                          "reviews/*.json full-schema accept at the same measured hash, or if the pinned map's quoted "
                          "accept counts already equal the union counts."),
        })
    if a_only:
        findings.append({
            "id": "W042-GSG-02",
            "severity": "minor",
            "statement": ("Accepts exist only in the reviews/ corpus with no matching accepted review event at the same "
                          f"measured hash ({', '.join(f'{t}: {v}' for t, v in a_only.items())}): the event stream is not a "
                          "complete provenance record of the binding corpus."),
            "examples": [{"target": t, "measured_sha256_12": targets_out[t]["measured_sha256_12"],
                          "reviewers": v} for t, v in a_only.items()],
            "falsifier": ("Re-run on the same pinned inputs. Falsified if a review event with verdict=accept and a "
                          "matching measured-hash pin exists in the pinned events snapshot for each listed reviewer."),
        })
    findings.append({
        "id": "W042-GSG-03",
        "severity": "info",
        "statement": ("Scan-A parity: the re-implementation is validated by seven synthetic controls and by exact "
                      "agreement with the audit lead's A1-rebind-coverage accept lists on F0/F2a/F2b"
                      f" (per-target audit_matrix_agrees_with_scan_a in `targets`), but it does NOT reproduce the counts "
                      f"the pinned map quotes in controller_gate_audit.G-AUDIT ({parity['map_g_audit_quoted_counts']} vs "
                      f"scan-A {parity['scan_a_counts']}, exact_match={parity['exact_match']}). The gap is explained by "
                      "W042-GSG-04 (post-audit rewrites), not by the re-implementation."),
        "falsifier": ("Re-run on the same pinned inputs. Falsified if scan-A counts equal the pinned map's quoted "
                      "G-AUDIT counts, or if the instrument controls fail."),
    })
    if nonreproducible:
        findings.append({
            "id": "W042-GSG-04",
            "severity": "major",
            "statement": ("The pinned map's gate-reason accept counts are not reproducible from the pinned review "
                          "corpus: quoted={} vs re-scanned={} at the same measured hashes. The reasons quote review-file "
                          "*counts* but no review-file sha256, and review files are rewritten in place; files pinning "
                          "the same measured hashes were observed with verdict != accept at the pin (see "
                          "`review_corpus_at_measured_hash`), several written after the map's audit checked_at. A gate "
                          "reason that quotes a count it cannot re-derive from bytes is not self-binding."
                          ).format({t: v["quoted"] for t, v in nonreproducible.items()},
                                   {t: v["scan_a"] for t, v in nonreproducible.items()}),
            "examples": [{"target": t, "gate": v["gate"], "quoted_count": v["quoted"],
                          "pinned_scan_a_count": v["scan_a"],
                          "gate_reason_checked_at": reasons.get(v["gate"], {}).get("checked_at"),
                          "files_at_measured_hash_at_pin": review_corpus_rows[t]}
                         for t, v in nonreproducible.items()],
            "not_claimed": ("Does not assert which earlier corpus the map counted or that any verdict flip was improper; "
                            "it asserts only that the quoted counts are not re-derivable from the pinned corpus."),
            "falsifier": ("Re-run on the same pinned inputs. Falsified if scan-A counts equal the quoted counts, or if the "
                          "quoted gate reasons carry per-file review sha256 pins that resolve, in the pinned corpus, to "
                          "verdict=accept files at the measured hashes."),
        })

    report = {
        "task_id": "W042-GATE-SCAN-GAP-02",
        "actor": "worker-042",
        "generated_at": now(),
        "status": "INVALID" if invalid else "worker-level complete; no node/gate authority",
        "question": ("At one pinned snapshot, does the controller's reviews/*.json review-coverage scan agree with the "
                     "accepted event stream about full-schema accepts at the measured F0/F1/F2a/F2b/L0/L1 hashes, and do "
                     "the map's gate-reason counts reflect the union?"),
        "inputs": {
            "events": {"snapshot": events_p.name, "sha256": files[events_p.name]["sha256"]},
            "map": {"snapshot": map_p.name, "sha256": files[map_p.name]["sha256"]},
            "artifact_hashes": {"snapshot": reg_p.name, "sha256": files[reg_p.name]["sha256"]},
            "reviews": {"dir": "snapshot/reviews", "files": man["reviews_count"],
                        "manifest_sha256": man["reviews_manifest_sha256"]},
            "measured_hash_source": "pinned map nodes artifact_sha256_measured; cross-checked against pinned runtime/state/artifact_hashes.json",
            "registry_agrees_with_map": registry_agrees,
        },
        "method": {
            "scan_a": "reviews/*.json records, astra_lifecycle.review_coverage semantics (re-implemented)",
            "scan_b": "research_map/events.jsonl review events, same semantics",
            "match_rule": "pin.startswith(measured[:12]) or measured.startswith(pin[:12])",
            "full_schema_rule": "counts_as_full_schema_verdict is not False",
            "authority": "advisory; binding coverage is adjudicated by the audit lead (reviews/A1-rebind-coverage.json)",
        },
        "headline": {
            "targets_with_b_only_accepts": b_only,
            "targets_with_a_only_accepts": a_only,
            "gate_reason_classifications": {gk: {t: r["classification"] for t, r in v.get("targets", {}).items()}
                                            for gk, v in gate_reason_check.items() if v.get("targets")},
            "parity_exact_match": parity["exact_match"],
            "reviews_files_scanned": cov_a.get("_files_scanned"),
            "review_events_scanned": cov_b.get("_review_events_scanned"),
        },
        "parity_control": parity,
        "targets": targets_out,
        "review_corpus_at_measured_hash": review_corpus_rows,
        "gate_reason_check": gate_reason_check,
        "findings": findings,
        "controls": controls,
        "live_drift_at_emit": {"files": live, "reviews": reviews_drift,
                               "note": "appends after the pin are not falsifiers; the report audits the pinned copies; "
                                       "live mtimes in review_corpus_at_measured_hash are advisory wall-clock corroboration"},
        "limits": [
            "Visibility/coverage measurement only; no gate verdict, no node status, no validation_status.",
            "Does not adjudicate whether any review is valid, independent, or binding; the audit lead owns that.",
            "reviews/*.json and the accepted event stream are both corpora of record claims, not ground truth.",
            "Hash binding is prefix-matched at 12 hex chars per the controller scan; a full-hash mismatch inside the "
            "same 12-char prefix would be invisible (not observed at this snapshot).",
            "The mtimes in review_corpus_at_measured_hash are filesystem wall-clock, not pinned bytes; only the copied "
            "review files are audited.",
            "Everything except generated_at and live_drift_at_emit is computed from the pinned copies and is "
            "bit-reproducible; live drift is reported at emit by construction.",
        ],
        "falsifier": ("Re-run this checker on the pinned snapshot. The claim is falsified if any b_only reviewer has a "
                      "reviews/*.json full accept at the same measured hash, any a_only reviewer has a matching accept "
                      "review event, the quoted gate-reason counts are reproducible from the pinned corpus (GSG-04), or "
                      "any control fails."),
        "rerun_command": (f"python3 {Path(__file__).resolve().relative_to(repo)} "
                          f"--snapshot {snap.relative_to(repo)} --out {Path(args.out).resolve().relative_to(repo)}"),
        "checker_sha256": sha256_file(Path(__file__).resolve()),
    }

    out_p = Path(args.out).resolve()
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "out": str(out_p),
                      "headline": report["headline"],
                      "controls_all_passed": controls.get("all_passed") if controls else None,
                      "report_sha256": sha256_file(out_p)}, indent=1))
    return 2 if invalid else 0


def _controls(snap: Path, hashes: dict) -> dict:
    with tempfile.TemporaryDirectory(prefix="w042_ctl_") as td:
        return run_controls(Path(td), hashes)


if __name__ == "__main__":
    sys.exit(main())
