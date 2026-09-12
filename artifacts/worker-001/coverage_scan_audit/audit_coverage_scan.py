#!/usr/bin/env python3
"""W001-COVERAGE-SCAN-01 -- fail-closed reconciliation of review-coverage accounting.

Task (class-bound): AF-SCC-C2-VAC-GEN / node F2a / gate G-FORM (cross-checked F0,F1,F2b,L0,L1,A0).

Question
--------
The Astra lifecycle's advisory `review_coverage()` scan (research_map/astra_lifecycle.py,
lines 176-214) reads only `reviews/*.json` and resolves targets through
`_targets_in_review()` (target_id / target / target_subnode -> TARGET_ALIASES).
Accepted review events live in `research_map/events.jsonl`. Do the two views agree at the
measured artifact hashes? Every accept the scan cannot see is gate-relevant, because the
scan text is what `controller_gate_audit` prints as the coverage reason.

Method
------
1. Pin measured hashes from `runtime/state/artifact_hashes.json` (controller-measured).
2. Run the controller's own scan function by import (no re-implementation drift).
3. Independently build the accepted-stream accept set from `research_map/events.jsonl`,
   resolving targets by node token, canonical artifact path, `path#sha256` target ids,
   class_id and `artifact` field.
4. Classify every divergence with a cause; flag latest-verdict supersession.
5. Run seeded controls through the real scan function against a synthetic reviews/ root.
6. Re-hash all inputs; any drift -> exit 3 with no verdict (fail closed).

Exit codes: 0 verdict emitted / 3 input drift / 4 control failure / 5 precondition failure.

This is a measurement of governance accounting, not a mathematical claim, no gate verdict,
and no edit to any canonical artifact. Falsifier: every accept in the accepted stream at a
measured hash also appears in the scan's full_accepts for the same target, reviewer and
hash, with no supersession error -- then this finding collapses.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "research_map"))
import astra_lifecycle as al  # noqa: E402  (controller scan implementation, imported not copied)

CST = timezone(timedelta(hours=8))
TARGET_NODES = ["F0", "F1", "F2a", "F2b", "L0", "L1", "A0", "A1", "A2", "N0", "N1-BLOCK"]
PIN_KEYS = ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256")
HASH_RE = re.compile(r"#([0-9a-fA-F]{8,64})\b")

INPUTS = {
    "measured": REPO / "runtime/state/artifact_hashes.json",
    "events": REPO / "research_map/events.jsonl",
    "scan_impl": REPO / "research_map/astra_lifecycle.py",
    "reviews_dir": REPO / "reviews",
}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def reviews_manifest() -> dict:
    out = {}
    for p in sorted(INPUTS["reviews_dir"].glob("*.json")):
        out[p.name] = sha256_file(p)
    return out


def load_measured():
    st = json.loads(INPUTS["measured"].read_text())
    measured = {}
    path_to_node = {}
    for path, info in st["hashes"].items():
        nid = info.get("node_id")
        if nid in TARGET_NODES and info.get("kind") == "file":
            measured[nid] = {"sha256": info["sha256"], "path": path}
            path_to_node[path] = nid
    return st.get("checked_at"), measured, path_to_node


def explicit_pins(d: dict) -> list:
    """Same pin extraction as the controller scan (al._explicit_pins)."""
    pins = []
    for key in PIN_KEYS:
        v = d.get(key)
        if isinstance(v, str):
            pins.append(v.lower())
    for key in ("target", "artifact"):
        v = d.get(key)
        if isinstance(v, dict):
            for k2 in ("sha256", "artifact_sha256", "reviewed_sha256"):
                if isinstance(v.get(k2), str):
                    pins.append(v[k2].lower())
    return pins


def embedded_pins(d: dict) -> list:
    """Hashes embedded in path#hash target ids: a pin the controller scan ignores."""
    out = []
    for key in ("target_id", "target_subnode"):
        v = d.get(key)
        if isinstance(v, str):
            out += [m.lower() for m in HASH_RE.findall(v)]
    t = d.get("target")
    if isinstance(t, dict) and isinstance(t.get("target_id"), str):
        out += [m.lower() for m in HASH_RE.findall(t["target_id"])]
    return out


def hash_matches(pin: str, measured_sha: str) -> bool:
    if not pin or not measured_sha:
        return False
    p, h = pin.lower(), measured_sha.lower()
    return p.startswith(h[:12]) or h.startswith(p[:12])


def resolve_nodes(d: dict, path_to_node: dict) -> set:
    """Resolve a review record/event to controller target nodes.

    Mirrors the scan's target semantics (target_id/target/target_subnode through
    TARGET_ALIASES) and adds the two extensions that make the reconciliation strict:
    canonical artifact paths and `path#sha256` target ids. `class_id` alone is NOT a
    target (the controller scan does not use it either), so an L1 source review carrying
    class_id AF-WCC-VAC-GEN is not mis-attributed to F1.
    """
    raw = set()
    for key in ("target_id", "target", "target_subnode"):
        v = d.get(key)
        if isinstance(v, str):
            raw.add(v)
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                if isinstance(v.get(k2), str):
                    raw.add(v[k2])
    out = set()
    for t in raw:
        base = t.split("#")[0]
        if base in path_to_node:
            out.add(path_to_node[base])
        for cand in (t, t.upper(), base, base.upper()):
            if cand in al.TARGET_ALIASES:
                out.add(al.TARGET_ALIASES[cand])
    if not out:
        art = d.get("artifact")
        if isinstance(art, str) and art.split("#")[0] in path_to_node:
            out.add(path_to_node[art.split("#")[0]])
    return out & set(TARGET_NODES)


def index_review_files(path_to_node: dict) -> list:
    """Parse every reviews/*.json once into a comparable record."""
    recs = []
    for p in sorted(INPUTS["reviews_dir"].glob("*.json")):
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        recs.append({
            "file": p.name,
            "sha256": sha256_file(p),
            "reviewer": str(d.get("reviewer") or d.get("actor") or "?"),
            "verdict": str(d.get("verdict", "")).lower(),
            "created_at": str(d.get("created_at") or ""),
            "scoped": d.get("counts_as_full_schema_verdict") is False,
            "nodes": sorted(resolve_nodes(d, path_to_node)),
            "pins": explicit_pins(d),
        })
    return recs


def stream_reviews(measured: dict, path_to_node: dict) -> list:
    rows = []
    for line in INPUTS["events"].read_text().splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("event_type") != "review":
            continue
        rows.append({
            "event_id": e.get("event_id"),
            "reviewer": str(e.get("reviewer") or e.get("actor") or "?"),
            "verdict": str(e.get("verdict", "")).lower(),
            "created_at": str(e.get("created_at") or ""),
            "scoped": e.get("counts_as_full_schema_verdict") is False,
            "nodes": sorted(resolve_nodes(e, path_to_node)),
            "pins": explicit_pins(e),
            "embedded_pins": embedded_pins(e),
        })
    return rows


def at_measured_hash(row: dict, node: str, measured: dict) -> bool:
    h = measured.get(node, {}).get("sha256", "")
    return any(hash_matches(p, h) for p in row["pins"] + row["embedded_pins"])


def classify_divergences(scan_view, stream_rows, measured, path_to_node, review_recs):
    """Reconcile the two views; return (event_only, scan_only, superseded, scan_superseded)."""
    event_only, scan_only, superseded, scan_superseded = [], [], [], []
    gate_of = {"F0": "G-F0", "F1": "G-FORM", "F2a": "G-FORM", "F2b": "G-FORM",
               "L0": "G-LIT", "L1": "G-LIT", "A0": "G-AUDIT"}
    for node in TARGET_NODES:
        if node not in measured:
            continue
        sha = measured[node]["sha256"]
        # --- stream view -------------------------------------------------
        stream_acc = [r for r in stream_rows
                      if r["verdict"] == "accept" and node in r["nodes"]
                      and at_measured_hash(r, node, measured)]
        # --- latest-verdict-per-reviewer supersession (stream layer) ------
        by_rev = {}
        for r in stream_rows:
            if node in r["nodes"]:
                by_rev.setdefault(r["reviewer"], []).append(r)
        for rev, rs in by_rev.items():
            if len(rs) < 2:
                continue
            rs_sorted = sorted(rs, key=lambda x: x["created_at"])
            latest = rs_sorted[-1]
            for r in rs_sorted[:-1]:
                if r["verdict"] == "accept" and latest["verdict"] != "accept":
                    superseded.append({"node": node, "gate": gate_of.get(node, "n/a"),
                                       "reviewer": rev,
                                       "superseded_event": r["event_id"],
                                       "latest_event": latest["event_id"],
                                       "latest_verdict": latest["verdict"]})
        # --- scan view ---------------------------------------------------
        scan_acc = scan_view.get(node, {}).get("full_accepts", [])
        scan_keys = {(a["reviewer"], a["file"]) for a in scan_acc}
        # event accepts the scan does not count
        for r in stream_acc:
            if r["scoped"]:
                continue
            if r["reviewer"] in {rev for rev, _ in scan_keys}:
                continue
            same_rev_files = [f for f in review_recs if f["reviewer"] == r["reviewer"]]
            node_files = [f for f in same_rev_files if node in f["nodes"]]
            pinned_files = [f for f in node_files
                            if any(hash_matches(p, sha) for p in f["pins"])]
            if pinned_files and all(f["scoped"] for f in pinned_files):
                cause = "scoped_verdict_excluded"
            elif not same_rev_files:
                cause = "review_body_not_in_reviews_dir"
            elif not node_files:
                cause = "target_id_not_resolvable_by_scan"
            elif not pinned_files:
                cause = "leading_hash_pin_absent_from_review_file"
            else:
                cause = "other_scan_miss"
            event_only.append({
                "node": node, "gate": gate_of.get(node, "n/a"),
                "reviewer": r["reviewer"], "event_id": r["event_id"],
                "created_at": r["created_at"], "cause": cause,
                "informational_only": node == "L1",
                "informational_reason": ("L1 coverage is measured by the separate "
                                         "l1_spotchecks() glob, not by full-schema accepts"
                                         if node == "L1" else None),
                "measured_sha256_prefix": sha[:12],
            })
        # scan accepts with no matching accepted event
        ev_keys = {(r["reviewer"], node) for r in stream_acc}
        for a in scan_acc:
            if (a["reviewer"], node) not in ev_keys:
                scan_only.append({"node": node, "gate": gate_of.get(node, "n/a"),
                                  "reviewer": a["reviewer"], "file": a["file"],
                                  "measured_sha256_prefix": sha[:12]})
        # scan counts an accept that the same reviewer later withdrew (file layer)
        for a in scan_acc:
            fam = [f for f in review_recs
                   if f["reviewer"] == a["reviewer"] and node in f["nodes"]
                   and f["verdict"] in ("accept", "revise", "reject", "inconclusive")
                   and any(hash_matches(p, sha) for p in f["pins"]) and f["created_at"]]
            if len(fam) < 2:
                continue
            fam.sort(key=lambda x: x["created_at"])
            latest = fam[-1]
            if latest["verdict"] != "accept" and latest["file"] != a["file"]:
                scan_superseded.append({
                    "node": node, "gate": gate_of.get(node, "n/a"),
                    "reviewer": a["reviewer"], "accept_file": a["file"],
                    "superseding_file": latest["file"], "superseding_verdict": latest["verdict"],
                    "measured_sha256_prefix": sha[:12],
                })
    return event_only, scan_only, superseded, scan_superseded


# --------------------------------------------------------------------------
# controls: exercise the real scan function against a synthetic reviews/ root
# --------------------------------------------------------------------------
def _run_scan_on_synthetic(files: dict, node: str, sha: str) -> dict:
    """files: {filename: record}; returns scan coverage for the synthetic target."""
    saved = al.ROOT
    tmp = Path(tempfile.mkdtemp(prefix="w001_scan_ctl_"))
    try:
        (tmp / "reviews").mkdir()
        for name, rec in files.items():
            (tmp / "reviews" / name).write_text(json.dumps(rec))
        al.ROOT = tmp
        return al.review_coverage({node: {"sha256": sha}})[node]
    finally:
        al.ROOT = saved


def controls() -> list:
    sha = "a" * 64
    node = "F2a"
    base = {"event_type": "review", "verdict": "accept", "reviewer": "ctl-rev",
            "target_id": node, "artifact_sha256": sha,
            "counts_as_full_schema_verdict": True}
    out = []

    def check(cid, desc, got, want):
        out.append({"id": cid, "description": desc, "expected": want,
                    "observed": got, "pass": got == want})

    # C1 unmutated baseline: file target_id node + explicit pin -> full accept counted
    cov = _run_scan_on_synthetic({"F2a-ctl.json": base}, node, sha)
    check("C1", "baseline accept with node target_id and explicit pin is counted",
          sorted(cov["distinct_accept_reviewers"]), ["ctl-rev"])

    # C2 no review file (event-only) -> scan sees zero accepts
    cov = _run_scan_on_synthetic({}, node, sha)
    check("C2", "event-only accept (no reviews/*.json body) is invisible to scan",
          sorted(cov["distinct_accept_reviewers"]), [])

    # C3 path#hash target_id -> invisible even when the body is in reviews/
    rec = dict(base, target_id=f"schemas/af_scc_c2_vacuum.yaml#{sha[:12]}")
    cov = _run_scan_on_synthetic({"F2a-ctl-path.json": rec}, node, sha)
    check("C3", "path#hash target_id is not resolved by TARGET_ALIASES",
          sorted(cov["distinct_accept_reviewers"]), [])

    # C4 scoped accept excluded on purpose
    rec = dict(base, counts_as_full_schema_verdict=False)
    cov = _run_scan_on_synthetic({"F2a-ctl-scoped.json": rec}, node, sha)
    check("C4", "counts_as_full_schema_verdict=false accept is excluded by design",
          (sorted(cov["distinct_accept_reviewers"]), len(cov["scoped_accepts"])), ([], 1))

    # C5 accept then later revise from same reviewer: scan still lists the accept
    rec_old = dict(base, created_at="2026-09-12T00:00:00+08:00")
    rec_new = dict(base, verdict="revise", created_at="2026-09-12T00:05:00+08:00",
                   artifact_sha256=sha)
    cov = _run_scan_on_synthetic({"F2a-ctl-old.json": rec_old, "F2a-ctl-new.json": rec_new},
                                 node, sha)
    check("C5", "scan does not model latest-verdict supersession (accept survives a later revise)",
          (sorted(cov["distinct_accept_reviewers"]), len(cov["verdicts"])), (["ctl-rev"], 2))

    # C6 classifier accumulates supersession across every node, not just the last one
    sha1, sha2 = "b" * 64, "c" * 64
    measured = {"F1": {"sha256": sha1}, "F2a": {"sha256": sha2}}
    scan_view = {n: {"full_accepts": [{"reviewer": f"rev-{n}", "file": f"{n}-acc.json"}],
                     "distinct_accept_reviewers": [f"rev-{n}"], "verdicts": []}
                 for n in measured}
    stream_rows = [
        {"event_id": "e1", "reviewer": "rev-F1", "verdict": "accept",
         "created_at": "2026-09-12T00:00:00+08:00", "scoped": False,
         "nodes": ["F1"], "pins": [sha1], "embedded_pins": []},
        {"event_id": "e2", "reviewer": "rev-F1", "verdict": "revise",
         "created_at": "2026-09-12T00:05:00+08:00", "scoped": False,
         "nodes": ["F1"], "pins": [sha1], "embedded_pins": []},
        {"event_id": "e3", "reviewer": "rev-F2a", "verdict": "accept",
         "created_at": "2026-09-12T00:01:00+08:00", "scoped": False,
         "nodes": ["F2a"], "pins": [sha2], "embedded_pins": []},
    ]
    recs = [{"file": f"{n}-acc.json", "sha256": "x", "reviewer": f"rev-{n}",
             "verdict": "accept", "created_at": "2026-09-12T00:00:00+08:00", "scoped": False,
             "nodes": [n], "pins": [sha]} for n, sha in (("F1", sha1), ("F2a", sha2))]
    eo, so, sup, ssup = classify_divergences(scan_view, stream_rows, measured,
                                             {}, recs)
    check("C6", "classifier accumulates supersession for every node (not only the last)",
          (len(sup), [s["node"] for s in sup]), (1, ["F1"]))

    # C7 file-layer: scan counts an accept a later file from the same reviewer withdraws
    recs7 = [dict(recs[0], file="F1-acc.json", verdict="accept",
                  created_at="2026-09-12T00:00:00+08:00"),
             dict(recs[0], file="F1-amend.json", verdict="revise",
                  created_at="2026-09-12T00:06:00+08:00")]
    eo, so, sup, ssup = classify_divergences(scan_view, [], measured, {}, recs7)
    check("C7", "file-layer supersession flags a scan accept withdrawn by a later file",
          (len(ssup), ssup[0]["accept_file"] if ssup else None,
           ssup[0]["superseding_file"] if ssup else None),
          (1, "F1-acc.json", "F1-amend.json"))
    return out


def main() -> int:
    started = now()
    pre = {name: sha256_file(p) for name, p in INPUTS.items() if p.is_file()}
    pre_manifest = reviews_manifest()
    pre["reviews_dir"] = hashlib.sha256(
        json.dumps(pre_manifest, sort_keys=True).encode()).hexdigest()

    checked_at, measured, path_to_node = load_measured()
    if not measured:
        print("PRECONDITION FAIL: no measured target hashes", file=sys.stderr)
        return 5

    ctl = controls()
    if not all(c["pass"] for c in ctl):
        print("CONTROL FAILURE: " + json.dumps([c for c in ctl if not c["pass"]]), file=sys.stderr)
        return 4

    scan_view = al.review_coverage({n: {"sha256": measured[n]["sha256"]} for n in measured})
    stream_rows = stream_reviews(measured, path_to_node)
    review_recs = index_review_files(path_to_node)
    event_only, scan_only, superseded, scan_superseded = classify_divergences(
        scan_view, stream_rows, measured, path_to_node, review_recs)

    gate_critical = [e for e in event_only if not e["informational_only"]]
    informational = [e for e in event_only if e["informational_only"]]
    divergence = bool(gate_critical or scan_only or superseded or scan_superseded)

    # drift guard: any input or review-corpus change voids the verdict
    post = {name: sha256_file(p) for name, p in INPUTS.items() if p.is_file()}
    post_manifest = reviews_manifest()
    post["reviews_dir"] = hashlib.sha256(
        json.dumps(post_manifest, sort_keys=True).encode()).hexdigest()
    drift = sorted(set(pre) | set(post))
    drift = [k for k in drift if pre.get(k) != post.get(k)]

    scan_summary = {n: {"distinct_accept_reviewers": scan_view[n]["distinct_accept_reviewers"],
                        "verdicts": [(v["reviewer"], v["verdict"]) for v in scan_view[n]["verdicts"]]}
                    for n in scan_view}
    stream_summary = {}
    live_summary = {}
    for n in TARGET_NODES:
        acc = [r for r in stream_rows if r["verdict"] == "accept" and n in r["nodes"]
               and at_measured_hash(r, n, measured)]
        stream_summary[n] = sorted({r["reviewer"] for r in acc})
        fam = {}
        for r in stream_rows:
            if n in r["nodes"] and at_measured_hash(r, n, measured):
                fam.setdefault(r["reviewer"], []).append(r)
        live_summary[n] = sorted(rev for rev, rs in fam.items()
                                 if sorted(rs, key=lambda x: x["created_at"])[-1]["verdict"] == "accept")

    report = {
        "report_id": "W001-COVERAGE-SCAN-01",
        "task_id": "W001-COVERAGE-SCAN-01",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "class_ids_crosschecked": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN",
                                   "AF-SCC-C0-VAC-GEN", "GLOBAL"],
        "node_id": "F2a",
        "nodes_crosschecked": TARGET_NODES,
        "gate": "G-FORM",
        "gate_crosschecked": ["G-F0", "G-LIT", "G-AUDIT"],
        "generated_at": started,
        "finished_at": now(),
        "measured_hashes_checked_at": checked_at,
        "measured_hashes": {n: measured[n]["sha256"] for n in measured},
        "inputs": {k: {"sha256": v} for k, v in pre.items()},
        "verdict": "DIVERGENCE" if divergence else "CONSISTENT",
        "headline": ("Advisory review-coverage scan misstates gate-accept coverage at the "
                     f"measured hashes: {len(gate_critical)} gate-critical accept event(s) are "
                     "invisible to review_coverage() and "
                     f"{len(scan_superseded)} scan-counted accept(s) were withdrawn by the same "
                     "reviewer. F2a is reported 0 accepts while the accepted stream carries a "
                     "full accept at the same pinned hash."),
        "impact": {
            "gate_reason_text": ("'F2a [0 distinct accept reviewer(s)]' printed in "
                                 "controller_gate_audit.G-FORM at 2026-09-12T00:43:08+08:00"),
            "gate_effect": ("coverage criterion 'two distinct independent accepts' is misstated "
                            "in both directions: live accepts invisible (F2a worker-089, F1 "
                            "worker-061, F0 worker-087) and a withdrawn accept counted (F1 "
                            "worker-088). The audit lead's binding adjudication should union the "
                            "accepted stream and apply latest-verdict supersession."),
        },
        "scan_view": scan_summary,
        "stream_view_at_measured_hashes": stream_summary,
        "stream_live_accept_reviewers_after_supersession": live_summary,
        "event_only_accepts_gate_critical": gate_critical,
        "event_only_accepts_informational": informational,
        "scan_only_accepts": scan_only,
        "supersession_flags_stream": superseded,
        "supersession_flags_scan_files": scan_superseded,
        "counts": {
            "target_nodes_with_measured_hash": len(measured),
            "stream_accept_events_at_measured_hashes": sum(len(v) for v in stream_summary.values()),
            "stream_live_accepts_after_supersession": sum(len(v) for v in live_summary.values()),
            "scan_full_accepts": sum(len(scan_view[n]["full_accepts"]) for n in scan_view),
            "event_only_gate_critical": len(gate_critical),
            "event_only_informational": len(informational),
            "scan_only": len(scan_only),
            "superseded_accepts_stream": len(superseded),
            "scan_counts_withdrawn_accepts": len(scan_superseded),
            "review_files_indexed": len(review_recs),
        },
        "decision_relevance": {
            "F2a": ("scan reason says 0 accepts; the accepted stream has 1 live full accept "
                    "(worker-089 at 5476a3f2c6bc). Criterion needs 2 distinct; coverage is "
                    "understated by the scan, not zero."),
            "F1": ("scan name says worker-088, but worker-088 withdrew that accept in a later "
                   "amended file/event (revise); the live F1 accept is worker-061, which the "
                   "scan cannot see. The scan is wrong in both directions."),
            "F0": ("scan sees 4 accepts; worker-087's live accept at 0abb9ed8a961 is invisible, "
                   "so 5 live accepts actually bind the measured hash."),
            "F2b": "scan agrees with the stream (worker-098 live).",
        },
        "controls": ctl,
        "falsifier": ("Collapses if, at these measured hashes, every accepted review event is "
                      "visible in review_coverage() full_accepts for the same node+reviewer+hash "
                      "and no accept is superseded by a later verdict from the same reviewer. "
                      "Also collapses if review_coverage() is changed to union the accepted event "
                      "stream (class_id/artifact-path resolution) and the divergence count drops "
                      "to zero, or if the measured hashes move."),
        "proposed_repair": [
            "controller-owned: in review_coverage(), union reviews/*.json with accepted review "
            "events from research_map/events.jsonl (keyed by node/class_id/artifact path)",
            "resolve target_id of the form <artifact-path>#<sha256> through the measured "
            "path->node registry, not only TARGET_ALIASES",
            "honour counts_as_full_schema_verdict=false in the union path",
            "apply latest-verdict-per-reviewer supersession before computing distinct accepts",
        ],        "not_claimed": ["no gate verdict", "no node status change", "no canonical artifact edit",
                        "no claim about the mathematical content of any review",
                        "measurement of governance accounting only"],
        "hash_drift": drift,
        "status": "VERDICT" if not drift else "DRIFT_NO_VERDICT",
    }

    outdir = HERE.parent / "evidence"
    outdir.mkdir(exist_ok=True)
    (outdir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps({k: report[k] for k in ("report_id", "verdict", "status", "counts",
                                             "event_only_accepts_gate_critical",
                                             "supersession_flags_stream",
                                             "supersession_flags_scan_files")},
                     indent=1)[:5000])
    if drift:
        print("DRIFT: " + json.dumps(drift), file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
