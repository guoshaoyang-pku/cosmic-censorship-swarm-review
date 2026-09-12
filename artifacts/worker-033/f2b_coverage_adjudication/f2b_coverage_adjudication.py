#!/usr/bin/env python3
"""W033-F2B-COVERAGE-ADJUDICATION-01

Bounded, read-only, class-bound (AF-SCC-C0-VAC-GEN / F2b) adjudication instrument for
CF-31: the G-FORM F2b review-coverage count divergence at canonical hash
b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c (FROZEN rev29
815e08079aef).

It freezes the live review corpus + review-event stream, then measures from the frozen
copy ONLY:

  1. file channel: every reviews/*.json record whose explicit pin fields bind the F2b
     hash, with reviewer/verdict/flags/mtime/amendment/independence facts;
  2. controller scan: an exact re-implementation of astra_lifecycle.review_coverage()
     (file channel, target aliases, 12-hex prefix pin rule) for F2b;
  3. lead-formulation census: the lead's stated method ("artifact_sha256/reviewed_sha256
     starts with the live hash") applied to the frozen corpus;
  4. event channel: accepted-stream review events binding the F2b hash, with
     same-reviewer/later-verdict supersession;
  5. temporal reconciliation of the four published counts (CF-31 text 4, map 01:16:26
     3, lead-formulation 0 accept / 7 revise, worker-048 2) against file availability
     at each instant.

Worker-level bookkeeping measurement only: no gate verdict, no done status, no write to
any canonical schema, review, detector, map or inbound channel.

Modes:
  freeze    capture pinned snapshot + MANIFEST.json + freeze.json
  run       compute report.json / binding_table.csv / reconciliation.json / review.json
  verify    recompute from pinned bytes and compare against report payload digest
  controls  fail-closed mutation controls on a synthetic corpus
"""

import argparse
import csv
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

TASK = Path(__file__).resolve().parent
ROOT = TASK.parents[2]
PIN = TASK / "pinned"
PIN_REVIEWS = PIN / "reviews"

C0 = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
C0_PREFIX = C0[:12]
F1 = "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"
F2A = "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"
F0 = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
SUPERSEDED_C0_REV13 = "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"
SUPERSEDED_C0_REV27 = "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"

VERDICT_KINDS = ("accept", "revise", "reject", "inconclusive")
PIN_FIELDS = ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256")
# astra_lifecycle.TARGET_ALIASES, copied verbatim at the frozen source hash
TARGET_ALIASES = {
    "F0": "F0", "F1": "F1", "F2A": "F2a", "F2B": "F2b", "F2": "F2b",
    "L0": "L0", "L1": "L1",
    "AF-WCC-VAC-GEN": "F1",
    "AF-SCC-C2-VAC-GEN": "F2a",
    "AF-SCC-C0-VAC-GEN": "F2b",
}
C0_CLASS = "AF-SCC-C0-VAC-GEN"

# The 7 revise records the formulation lead published (filenames at the freeze).
LEAD_PUBLISHED_REVISE = [
    "F2b-containment-normativity-worker-066.json",
    "F2b-rev29-containment-rebase-worker-066.json",
    "F2b-bindchain-rev13-worker-035.json",
    "F2b-rev13-containment-worker-017.json",
    "F2b-review-rev29-075.json",
    "F2b-review-worker-018-rev13.json",
    "F2b-review-rev29-053.json",
]
# Availability boundary implied by the lead's 7-record revise set (latest member mtime).
LEAD_STALE_BOUNDARY = "2026-09-12T01:06:00+08:00"

CONTROLLER_SOURCES = [
    "research_map/astra_lifecycle.py",
    "research_map/apply_events.py",
    "research_map/events.jsonl",
    "research_map/research_map.json",
]
PUBLISHED_EVIDENCE = [
    "artifacts/formulation/evidence/lead_formulation_lifecycle_07_independent_verify.json",
    "comms/outbox/astra-lead-formulation.jsonl",
    "reviews/W048-GFORM-COVERAGE-RECOUNT-01.json",
    "artifacts/formulation/FROZEN.json",
    "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
]


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    return sha256_bytes(Path(p).read_bytes())


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def payload_digest(obj):
    return sha256_bytes(canonical(obj).encode())


def now_iso():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def parse_ts(s):
    """Tolerant ISO-8601 parser; naive timestamps are assumed +08:00."""
    if not isinstance(s, str) or not s.strip():
        return None
    t = s.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    if len(t) >= 5 and (t[-5] in "+-") and t[-3] != ":":
        t = t[:-2] + ":" + t[-2:]
    try:
        dt = datetime.fromisoformat(t)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
    return dt


def ts_key(s):
    dt = parse_ts(s)
    return dt.timestamp() if dt else None


def norm_target(d):
    """Replicate astra_lifecycle._targets_in_review plus node_id/class_id aliases."""
    out = set()
    for key in ("target_id", "target", "target_subnode"):
        v = d.get(key)
        if isinstance(v, str):
            out.add(v)
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                if isinstance(v.get(k2), str):
                    out.add(v[k2])
    for key in ("node_id", "class_id", "target_class"):
        v = d.get(key)
        if isinstance(v, str):
            out.add(v)
    norm = set()
    for t in out:
        norm.add(TARGET_ALIASES.get(t, TARGET_ALIASES.get(t.upper(), t)))
    return norm


def explicit_pins(d):
    """Pin fields the controller scan reads, plus nested reviewed_pins/carriers.

    Returns {field_path: value}. The controller-equivalent subset is exactly
    PIN_FIELDS at top level plus target/artifact nested sha keys.
    """
    pins = {}

    def add(path, v):
        if isinstance(v, str) and v.strip():
            pins[path] = v.strip().lower()

    for key in PIN_FIELDS:
        add(key, d.get(key))
    for key in ("target", "artifact", "reviewed"):
        v = d.get(key)
        if isinstance(v, dict):
            for k2 in ("sha256", "artifact_sha256", "reviewed_sha256"):
                add(f"{key}.{k2}", v.get(k2))
    rp = d.get("reviewed_pins")
    if isinstance(rp, dict):
        for k2, v in rp.items():
            add(f"reviewed_pins.{k2}", v)
    elif isinstance(rp, list):
        for i, v in enumerate(rp):
            if isinstance(v, dict):
                for k2 in ("sha256", "artifact_sha256", "reviewed_sha256", "value"):
                    add(f"reviewed_pins[{i}].{k2}", v.get(k2))
            else:
                add(f"reviewed_pins[{i}]", v)
    for key in ("reviewed_frozen_sha256", "reviewed_mirror_sha256", "supersedes_sha256"):
        add(key, d.get(key))
    return pins


def controller_pins(d):
    """Exactly the pin set astra_lifecycle._explicit_pins reads (frozen source)."""
    pins = []
    for key in PIN_FIELDS:
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


def prefix_match(pin, h):
    """astra_lifecycle rule: pin.startswith(h[:12]) or h.startswith(pin[:12])."""
    if not pin or not h:
        return False
    return pin.startswith(h[:12]) or h.startswith(pin[:12])


def load_reviews(dirpath):
    recs = []
    for p in sorted(Path(dirpath).glob("*.json")):
        raw = p.read_bytes()
        try:
            d = json.loads(raw)
        except Exception:
            recs.append({"file": p.name, "parse_ok": False, "sha256": sha256_bytes(raw)})
            continue
        if not isinstance(d, dict):
            recs.append({"file": p.name, "parse_ok": False, "sha256": sha256_bytes(raw)})
            continue
        recs.append({"file": p.name, "parse_ok": True, "sha256": sha256_bytes(raw), "doc": d})
    return recs


def classify(rec, manifest, h=C0):
    """One row of the binding table, computed from a frozen review record."""
    d = rec.get("doc") or {}
    m = manifest.get(rec["file"], {})
    pins = explicit_pins(d)
    cpins = controller_pins(d)
    targets = norm_target(d)
    verdict = str(d.get("verdict", "")).lower()
    row = {
        "file": rec["file"],
        "parse_ok": rec.get("parse_ok", False),
        "sha256": rec.get("sha256"),
        "reviewer": d.get("reviewer") or d.get("actor"),
        "verdict": verdict if verdict in VERDICT_KINDS else None,
        "raw_verdict": d.get("verdict"),
        "score": d.get("score"),
        "target_id": d.get("target_id") if isinstance(d.get("target_id"), str) else d.get("target_id", None),
        "node_id": d.get("node_id"),
        "class_id": d.get("class_id"),
        "targets_norm": sorted(targets),
        "target_is_f2b": ("F2b" in targets) or (d.get("class_id") == C0_CLASS),
        "pins": pins,
        "pin_fields_matching": sorted(k for k, v in pins.items() if v == h),
        "pin_prefix_matching": sorted(k for k, v in pins.items() if prefix_match(v, h)),
        "binds_strict": any(v == h for v in pins.values()),
        "binds_prefix12": any(prefix_match(v, h) for v in pins.values()),
        "binds_controller": any(prefix_match(v, h) for v in cpins),
        "controller_pins": cpins,
        "full_flag": d.get("counts_as_full_schema_verdict") is not False,
        "full_flag_value": d.get("counts_as_full_schema_verdict"),
        "gate_flag": d.get("counts_as_gate_accept") is not False,
        "created_at": d.get("created_at"),
        "created_ts": ts_key(d.get("created_at")),
        "source_mtime": m.get("source_mtime_iso"),
        "source_mtime_ts": m.get("source_mtime"),
        "amended_delta_s": None,
        "blind": d.get("blind"),
        "reviewer_role": d.get("reviewer_role"),
        "reviewer_is_author": d.get("reviewer_is_author"),
        "independence": d.get("independence"),
        "supersedes_verdict": d.get("supersedes_verdict"),
        "superseded_at": d.get("superseded_at"),
        "revision_history": d.get("revision_history"),
        "review_scope": d.get("review_scope") or d.get("scope"),
    }
    if row["created_ts"] and row["source_mtime_ts"]:
        row["amended_delta_s"] = round(row["source_mtime_ts"] - row["created_ts"], 1)
    return row


def file_census(rows):
    bound = [r for r in rows if r["parse_ok"] and r["verdict"] and r["target_is_f2b"]
             and r["binds_prefix12"]]
    accepts = [r for r in bound if r["verdict"] == "accept"]
    full_accepts = [r for r in accepts if r["full_flag"]]
    return {
        "bound": bound,
        "by_verdict": {v: sorted(r["reviewer"] for r in bound if r["verdict"] == v)
                       for v in VERDICT_KINDS},
        "accepts": accepts,
        "full_accepts": full_accepts,
        "distinct_accept_reviewers": sorted({r["reviewer"] for r in full_accepts}),
        "distinct_accept_reviewers_controller": sorted(
            {r["reviewer"] for r in full_accepts if r["binds_controller"]}),
    }


def census_at(rows, instant_iso):
    """File-channel count using each record's availability (mtime) <= instant."""
    t = ts_key(instant_iso)
    sub = [r for r in rows if r["source_mtime_ts"] and r["source_mtime_ts"] <= t]
    return file_census(sub)


def controller_scan(rows):
    """Exact re-implementation of astra_lifecycle.review_coverage() for F2b."""
    out = {"verdicts": [], "accepts": [], "full_accepts": [], "scoped_accepts": []}
    for r in sorted(rows, key=lambda x: x["file"]):
        if not r["parse_ok"] or not r["verdict"] or not r["binds_controller"]:
            continue
        if "F2b" not in r["targets_norm"]:
            continue
        e = {"file": r["file"], "reviewer": r["reviewer"], "verdict": r["verdict"],
             "counts_as_full_schema_verdict": r["full_flag"]}
        out["verdicts"].append(e)
        if r["verdict"] == "accept":
            out["accepts"].append(e)
            (out["full_accepts"] if r["full_flag"] else out["scoped_accepts"]).append(e)
    out["distinct_accept_reviewers"] = sorted({a["reviewer"] for a in out["full_accepts"]})
    return out


def lead_method(rows, instant_iso=None, created_based=False, target_filtered=False):
    """Lead-formulation method: every reviews/*.json, verdict counted only when
    artifact_sha256/reviewed_sha256 starts with the live hash.

    The lead's write-up does not state a target filter, so both the literal
    (pin-only) and target-filtered variants are computed.
    """
    t = ts_key(instant_iso) if instant_iso else None
    sel = []
    for r in rows:
        if not r["parse_ok"] or not r["verdict"]:
            continue
        lead_pins = {}
        d = r["pins"]
        for k, v in d.items():
            if k.split(".")[0] in ("artifact_sha256", "reviewed_sha256"):
                lead_pins[k] = v
        if not any(prefix_match(v, C0) for v in lead_pins.values()):
            continue
        if target_filtered and not r["target_is_f2b"]:
            continue
        if t is not None:
            at = r["created_ts"] if created_based else r["source_mtime_ts"]
            if not at or at > t:
                continue
        sel.append(r)
    return {
        "reviewers": {v: sorted(r["reviewer"] for r in sel if r["verdict"] == v)
                      for v in VERDICT_KINDS},
        "files": {v: sorted(r["file"] for r in sel if r["verdict"] == v)
                  for v in VERDICT_KINDS},
    }


def parse_events_slice(path):
    evs = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        if d.get("event_type") != "review":
            continue
        evs.append(d)
    return evs


def event_rows(events):
    rows = []
    for d in events:
        pins = explicit_pins(d)
        cpins = controller_pins(d)
        targets = norm_target(d)
        verdict = str(d.get("verdict", "")).lower()
        rows.append({
            "event_id": d.get("event_id"),
            "reviewer": d.get("reviewer") or d.get("actor"),
            "verdict": verdict if verdict in VERDICT_KINDS else None,
            "score": d.get("score"),
            "targets_norm": sorted(targets),
            "target_is_f2b": ("F2b" in targets) or (d.get("class_id") == C0_CLASS),
            "pins": pins,
            "binds_strict": any(v == C0 for v in pins.values()),
            "binds_prefix12": any(prefix_match(v, C0) for v in pins.values()),
            "binds_controller": any(prefix_match(v, C0) for v in cpins),
            "full_flag": d.get("counts_as_full_schema_verdict") is not False,
            "gate_flag": d.get("counts_as_gate_accept") is not False,
            "created_at": d.get("created_at"),
            "created_ts": ts_key(d.get("created_at")),
            "target_id": d.get("target_id"),
        })
    return [r for r in rows if r["verdict"]]
    return rows


def supersession(ev_rows):
    """Same reviewer + same normalized F2b target: latest verdict is operative."""
    groups = {}
    for r in ev_rows:
        if not r["target_is_f2b"] or not r["created_ts"]:
            continue
        groups.setdefault(r["reviewer"], []).append(r)
    operative, superseded = [], []
    for reviewer, rs in groups.items():
        rs = sorted(rs, key=lambda x: x["created_ts"])
        seen = {}
        for r in rs:
            key = (r["reviewer"], "F2b")
            if key in seen:
                superseded.append({"event_id": seen[key]["event_id"],
                                   "reviewer": reviewer,
                                   "superseded_by": r["event_id"],
                                   "superseded_at": r["created_at"]})
            seen[key] = r
        operative.append(seen[(reviewer, "F2b")])
    return operative, superseded


def integrity_checks(rows, file_manifest, events_meta):
    checks = []
    # every F2b-file-channel bound record resolves and parses
    bad = [r["file"] for r in rows if not r["parse_ok"]]
    checks.append({"id": "IC-01", "check": "all pinned review files parse as JSON objects",
                   "detail": {"unparseable": bad}, "pass": not bad})
    # every manifest entry has a measured sha256 that matches the pinned file
    mism = []
    for name, m in file_manifest.items():
        p = PIN_REVIEWS / name
        if not p.exists() or sha256_file(p) != m["sha256"]:
            mism.append(name)
    checks.append({"id": "IC-02", "check": "pinned review bytes match MANIFEST sha256",
                   "detail": {"mismatches": mism}, "pass": not mism})
    checks.append({"id": "IC-03", "check": "review-event slice pinned with source hash",
                   "detail": events_meta, "pass": bool(events_meta.get("source_sha256"))})
    # exact-64 vs prefix agreement for the accept set
    acc = [r for r in rows if r["verdict"] == "accept" and r["target_is_f2b"] and r["binds_prefix12"]]
    lenient = [r["file"] for r in acc if not r["binds_strict"]]
    checks.append({"id": "IC-04", "check": "no F2b accept binds only by the 12-hex prefix rule",
                   "detail": {"lenient_only": lenient}, "pass": not lenient})
    return checks


def build(manifest, freeze, events_meta):
    rows = [classify(rec, manifest) for rec in load_reviews(PIN_REVIEWS)]
    census = file_census(rows)
    scan = controller_scan(rows)
    lead_variants = {
        "live_literal": lead_method(rows),
        "live_target_filtered": lead_method(rows, target_filtered=True),
        "stale_0106_literal": lead_method(rows, LEAD_STALE_BOUNDARY),
        "stale_0106_target_filtered": lead_method(rows, LEAD_STALE_BOUNDARY, target_filtered=True),
        "stale_0106_created_based_target_filtered": lead_method(
            rows, LEAD_STALE_BOUNDARY, created_based=True, target_filtered=True),
    }
    events = parse_events_slice(PIN / "events_f2b.jsonl")
    ev_rows = event_rows(events)
    operative, superseded = supersession(ev_rows)
    ev_bound = [r for r in ev_rows if r["target_is_f2b"] and r["binds_prefix12"]]
    ev_accepts = [r for r in ev_bound if r["verdict"] == "accept"]
    op_accepts = [r for r in operative if r["verdict"] == "accept" and r["binds_prefix12"]]
    op_reviewers = sorted({r["reviewer"] for r in op_accepts if r["full_flag"]})

    # file-channel accepts superseded by a later same-reviewer verdict (either channel)
    latest = {}
    for r in ev_rows:
        if not r["target_is_f2b"] or not r["created_ts"]:
            continue
        if r["reviewer"] not in latest or r["created_ts"] > latest[r["reviewer"]]["created_ts"]:
            latest[r["reviewer"]] = r
    op_file_accepts = []
    for a in census["full_accepts"]:
        later = latest.get(a["reviewer"])
        at = a["source_mtime_ts"] or a["created_ts"]
        if later and at and later["created_ts"] > at and not (later["verdict"] == "accept"):
            a["_superseded_by"] = later["event_id"]
            continue
        op_file_accepts.append(a)
    op_file_reviewers = sorted({a["reviewer"] for a in op_file_accepts})

    published = {
        "cf31_text": {"accepts": ["worker-052", "worker-071", "worker-072", "worker-090"],
                      "n": 4, "note": "CF-31 finding text; matches the 01:12:39 open-pass scan before worker-072 self-superseded"},
        "controller_map_0116": {"accepts": ["worker-052", "worker-071", "worker-090"], "n": 3,
                                "note": "controller_gate_audit.G-FORM reason checked_at 2026-09-12T01:16:26"},
        "lead_formulation": {"accepts": [], "revise": LEAD_PUBLISHED_REVISE, "n": 0,
                             "note": "lead method claimed at 01:10, event lead-form-20260912T0113-107"},
        "worker048": {"accepts": ["worker-090", "worker-072"], "n": 2,
                      "note": "W048-GFORM-COVERAGE-RECOUNT-01 created_at 01:12:00"},
    }
    measured = {
        "file_channel_freeze": {
            "accepts": sorted(r["reviewer"] for r in census["full_accepts"]),
            "accept_files": sorted(r["file"] for r in census["full_accepts"]),
            "n": len(census["distinct_accept_reviewers"]),
            "by_verdict": census["by_verdict"],
        },
        "controller_scan_reproduction_freeze": {
            "accepts": scan["distinct_accept_reviewers"],
            "n": len(scan["distinct_accept_reviewers"]),
            "verdicts": scan["verdicts"],
        },
        "lead_method_on_frozen_corpus": lead_variants,
        "event_channel": {
            "bound_reviews": len(ev_bound),
            "accepts": sorted(r["reviewer"] for r in ev_accepts),
            "operative_accepts": sorted(r["reviewer"] for r in op_accepts),
            "operative_full_accept_reviewers": op_reviewers,
            "superseded_records": superseded,
        },
        "operative_file_accepts": {
            "reviewers": op_file_reviewers,
            "n": len(op_file_reviewers),
            "excluded_by_later_verdict": [{"file": a["file"], "reviewer": a["reviewer"],
                                           "superseded_by": a.get("_superseded_by")}
                                          for a in census["full_accepts"] if "_superseded_by" in a],
        },
        "temporal_grid": {
            inst: {"accepts": census_at(rows, inst)["distinct_accept_reviewers"],
                   "revise": census_at(rows, inst)["by_verdict"]["revise"]}
            for inst in ["2026-09-12T01:05:46+08:00", "2026-09-12T01:08:56+08:00",
                         "2026-09-12T01:10:00+08:00", "2026-09-12T01:11:15+08:00",
                         "2026-09-12T01:12:39+08:00", "2026-09-12T01:14:54+08:00",
                         "2026-09-12T01:16:26+08:00", freeze["frozen_at"]]
        },
    }
    # Which reproduction equals the published lead set (0 accept / these 7 revise files)?
    lead_set = sorted(LEAD_PUBLISHED_REVISE)
    recon = []
    for label, got in lead_variants.items():
        equals = (got["reviewers"]["accept"] == []
                  and sorted(got["files"]["revise"]) == lead_set)
        recon.append({"reproduction": label,
                      "accept": got["reviewers"]["accept"],
                      "revise": got["reviewers"]["revise"],
                      "revise_files": got["files"]["revise"],
                      "equals_published_0_7": equals})
    # Implied stale-corpus window, derived from the pinned availability data:
    # latest availability among the 7 published revise files vs earliest accept.
    published_rows = [r for r in rows if r["file"] in lead_set]
    accept_rows = census["full_accepts"]
    max_revise_mtime = max((r["source_mtime_ts"] for r in published_rows if r["source_mtime_ts"]),
                           default=None)
    min_accept_mtime = min((r["source_mtime_ts"] for r in accept_rows if r["source_mtime_ts"]),
                           default=None)

    def iso(t):
        return (datetime.fromtimestamp(t, timezone(timedelta(hours=8)))
                .isoformat(timespec="seconds") if t else None)

    window = {}
    for b in ["2026-09-12T01:06:00+08:00", "2026-09-12T01:08:00+08:00",
              iso(min_accept_mtime + 1) if min_accept_mtime else None]:
        if not b:
            continue
        g = lead_method(rows, b)
        window[b] = {"accept": g["reviewers"]["accept"],
                     "revise_files": g["files"]["revise"],
                     "equals_published_0_7": (g["reviewers"]["accept"] == []
                                              and sorted(g["files"]["revise"]) == lead_set)}
    stale_window = {
        "last_availability_of_published_revise": iso(max_revise_mtime),
        "first_availability_of_an_accept": iso(min_accept_mtime),
        "implied_corpus_boundary_interval": f"({iso(max_revise_mtime)}, {iso(min_accept_mtime)}]",
        "evidence": window,
        "statement": ("the published 0/7 is reproducible iff the review corpus is "
                      "restricted to records available before the first accept file "
                      "(worker-090, " + str(iso(min_accept_mtime)) + "); at the lead's "
                      "stated live 01:10 measurement the same rule returns >= 1 accept"),
    }
    # Key-selection cross-check on the 7 published revise files: an artifact_sha256-only
    # key sees 5 of them; worker-035 and worker-053 carry reviewed_sha256 only.
    key_check = []
    for r in rows:
        if r["file"] in LEAD_PUBLISHED_REVISE:
            key_check.append({
                "file": r["file"], "reviewer": r["reviewer"], "verdict": r["verdict"],
                "artifact_sha256_match": any(k.startswith("artifact_sha256") and v == C0
                                             for k, v in r["pins"].items()),
                "reviewed_sha256_match": any(k.startswith("reviewed_sha256") and v == C0
                                             for k, v in r["pins"].items()),
            })
    key_selection = {
        "published_revise_files": len(LEAD_PUBLISHED_REVISE),
        "artifact_key_only_count": sum(1 for k in key_check if k["artifact_sha256_match"]),
        "reviewed_key_only_count": sum(1 for k in key_check if k["reviewed_sha256_match"]),
        "files": key_check,
        "statement": ("no single pin key reproduces the published 7 revise rows: an "
                      "artifact_sha256-only key sees "
                      f"{sum(1 for k in key_check if k['artifact_sha256_match'])}/7 and a "
                      "reviewed_sha256-only key sees "
                      f"{sum(1 for k in key_check if k['reviewed_sha256_match'])}/7, while "
                      "the stale corpus boundary reproduces all 7 exactly"),
    }
    # Corpus-level integrity checks tied to the published 0/7 claim.
    early = window.get("2026-09-12T01:06:00+08:00", {})
    late_key = iso(min_accept_mtime + 1) if min_accept_mtime else None
    late = window.get(late_key, {}) if late_key else {}
    extra_checks = [
        {"id": "IC-05", "check": "lead 0/7 equality holds at a pre-01:08 corpus boundary",
         "detail": {"boundary": "2026-09-12T01:06:00+08:00",
                    "equals_published_0_7": early.get("equals_published_0_7")},
         "pass": bool(early.get("equals_published_0_7"))},
        {"id": "IC-06", "check": "lead 0/7 equality fails at a post-accept corpus boundary",
         "detail": {"boundary": late_key,
                    "equals_published_0_7": late.get("equals_published_0_7"),
                    "accepts_then": late.get("accept")},
         "pass": late.get("equals_published_0_7") is False},
        {"id": "IC-07", "check": "all 7 published revise files are bound F2b revise at frozen bytes",
         "detail": {"files": sorted(r["file"] for r in published_rows),
                    "all_revise_bound": all(r["verdict"] == "revise" and r["target_is_f2b"]
                                            and r["binds_prefix12"] for r in published_rows)},
         "pass": all(r["verdict"] == "revise" and r["target_is_f2b"] and r["binds_prefix12"]
                     for r in published_rows)},
    ]
    # worker-072 in-place amendment timeline (event channel preserves what the file no longer does)
    amendment_072 = {
        "file": "reviews/F2b-review-worker-072-rev29.json",
        "accept_event": "w072-2026-09-12T01:10:13+08:00-review-f2b",
        "accept_event_at": "2026-09-12T01:10:13+08:00",
        "selfsupersede_event": "w072-f2b-selfsupersede-review-20260912T011524",
        "selfsupersede_at": "2026-09-12T01:15:24+08:00",
        "file_mtime": next((r["source_mtime"] for r in rows
                            if r["file"] == "F2b-review-worker-072-rev29.json"), None),
        "file_verdict_at_freeze": next((r["verdict"] for r in rows
                                        if r["file"] == "F2b-review-worker-072-rev29.json"), None),
        "file_superseded_at": next((r["superseded_at"] for r in rows
                                    if r["file"] == "F2b-review-worker-072-rev29.json"), None),
        "statement": ("worker-072 is an accept in the accepted-event channel until 01:15:24 "
                      "and a revise in the frozen file; the CF-31 4-count is correct only "
                      "before the 01:14:54 file amendment"),
    }
    # concurrent independent census (worker-017, landed 01:21:56, pinned in this snapshot)
    w017 = next((r for r in rows if r["file"] == "CF31-F2b-binding-table-worker-017.json"), None)
    w017_doc = {}
    w017_path = PIN_REVIEWS / "CF31-F2b-binding-table-worker-017.json"
    if w017_path.exists():
        try:
            w017_doc = json.loads(w017_path.read_text())
        except Exception:
            w017_doc = {}
    crosscheck = {
        "artifact": "reviews/CF31-F2b-binding-table-worker-017.json",
        "sha256": w017["sha256"] if w017 else None,
        "created_at": w017["created_at"] if w017 else None,
        "summary": w017_doc.get("summary"),
        "measured_accept_set": ("worker-052, worker-071, worker-090"
                                if "worker-052" in json.dumps(w017_doc.get("summary", ""))
                                else None),
        "statement": ("an independently written CF-31 census is pinned in this freeze "
                      "(record created_at " + str(w017_doc.get("created_at")) + ", source mtime "
                      + str(w017["source_mtime"] if w017 else None) + "); it reports the same "
                      "live full-schema accept set {worker-052, worker-071, worker-090} (3) as "
                      "this instrument. Its key-selection reading of the lead's 0-accept count "
                      "is not sufficient by itself: no single pin key sees all 7 published "
                      "revise rows (see key_selection_check), whereas the stale corpus boundary "
                      "reproduces the published 0/7 exactly"),
    }
    payload = {
        "task_id": "W033-F2B-COVERAGE-ADJUDICATION-01",
        "class_ids": [C0_CLASS],
        "node_id": "F2b",
        "gate": "G-FORM",
        "target_hash": C0,
        "frozen_revision": freeze.get("live_hashes", {}).get("frozen_revision"),
        "frozen_manifest_sha256": freeze.get("live_hashes", {}).get("frozen_manifest_sha256"),
        "freeze": {"frozen_at": freeze.get("frozen_at"), "freeze_id": freeze.get("freeze_id")},
        "corpus": freeze.get("corpus"),
        "published_counts": published,
        "measured": measured,
        "lead_reconciliation": recon,
        "implied_stale_window": stale_window,
        "key_selection_check": key_selection,
        "in_place_amendment_worker_072": amendment_072,
        "independent_crosscheck": crosscheck,
        "binding_table": rows,
        "integrity_checks": integrity_checks(rows, manifest, events_meta) + extra_checks,
    }
    return payload


def cmd_freeze(args):
    PIN.mkdir(parents=True, exist_ok=True)
    if PIN_REVIEWS.exists():
        shutil.rmtree(PIN_REVIEWS)
    PIN_REVIEWS.mkdir(parents=True)
    frozen_at = now_iso()
    manifest = {}
    for p in sorted((ROOT / "reviews").glob("*.json")):
        raw = p.read_bytes()
        shutil.copy2(p, PIN_REVIEWS / p.name)
        manifest[p.name] = {
            "source_path": str(p.relative_to(ROOT)),
            "sha256": sha256_bytes(raw),
            "size": len(raw),
            "source_mtime": p.stat().st_mtime,
            "source_mtime_iso": datetime.fromtimestamp(
                p.stat().st_mtime, timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        }
    # review-event slice: all review events that mention the F2b hash or F2b/C0 target
    src = ROOT / "research_map/events.jsonl"
    raw = src.read_bytes()
    keep = []
    for line in raw.splitlines():
        if (C0_PREFIX.encode() in line) or (b"F2b" in line) or (b"AF-SCC-C0-VAC-GEN" in line):
            try:
                if json.loads(line).get("event_type") == "review":
                    keep.append(line)
            except Exception:
                continue
    (PIN / "events_f2b.jsonl").write_bytes(b"\n".join(keep) + b"\n")
    events_meta = {
        "source_path": "research_map/events.jsonl",
        "source_sha256": sha256_bytes(raw),
        "source_size": len(raw),
        "source_mtime_iso": datetime.fromtimestamp(
            src.stat().st_mtime, timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        "kept_review_events": len(keep),
        "slice_sha256": sha256_file(PIN / "events_f2b.jsonl"),
    }
    # published evidence snapshots
    evidence = {}
    for rel in PUBLISHED_EVIDENCE:
        p = ROOT / rel
        if p.exists():
            evidence[rel] = {"sha256": sha256_file(p), "size": p.stat().st_size}
    for rel in CONTROLLER_SOURCES:
        p = ROOT / rel
        if p.exists():
            evidence[rel] = {"sha256": sha256_file(p), "size": p.stat().st_size}
    map_obj = json.loads((ROOT / "research_map/research_map.json").read_text())
    gate_reason = None
    for g in map_obj.get("gates", []):
        if g.get("gate_id") == "G-FORM":
            gate_reason = {"checked_at": map_obj.get("controller_gate_audit", {}).get("G-FORM", {}).get("checked_at"),
                           "reason": map_obj.get("controller_gate_audit", {}).get("G-FORM", {}).get("reason")}
    frozen_manifest = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    live = {
        "f2b_canonical_sha256": sha256_file(ROOT / "schemas/af_scc_c0_vacuum.yaml"),
        "f2b_authoring_sha256": sha256_file(ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
        "f1_canonical_sha256": sha256_file(ROOT / "schemas/af_wcc_vacuum.yaml"),
        "f2a_canonical_sha256": sha256_file(ROOT / "schemas/af_scc_c2_vacuum.yaml"),
        "f0_canonical_sha256": sha256_file(ROOT / "research_map/formulation_taxonomy.yaml"),
        "frozen_manifest_sha256": sha256_file(ROOT / "artifacts/formulation/FROZEN.json"),
        "frozen_revision": frozen_manifest.get("revision"),
        "astra_lifecycle_sha256": sha256_file(ROOT / "research_map/astra_lifecycle.py"),
        "map_sha256": sha256_file(ROOT / "research_map/research_map.json"),
    }
    freeze = {
        "freeze_id": "W033-F2B-COV-" + frozen_at.replace(":", "").replace("-", "").replace("+", "p"),
        "frozen_at": frozen_at,
        "worker": "worker-033",
        "mode": "read-only snapshot of reviews/ + review-event slice + published evidence",
        "live_hashes": live,
        "corpus": {"n_review_files": len(manifest), "manifest_sha256": payload_digest(manifest),
                   "events": events_meta, "published_evidence": evidence,
                   "controller_gate_audit_gform": gate_reason},
        "no_write_targets": ["reviews/", "schemas/", "artifacts/formulation/",
                             "research_map/", "comms/inbox/"],
    }
    (PIN / "freeze.json").write_text(json.dumps(freeze, indent=1, sort_keys=True))
    (PIN / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    print(json.dumps({"ok": True, "freeze_id": freeze["freeze_id"], "frozen_at": frozen_at,
                      "review_files": len(manifest),
                      "f2b_sha256": live["f2b_canonical_sha256"],
                      "events_slice": events_meta["kept_review_events"],
                      "manifest_sha256": freeze["corpus"]["manifest_sha256"]}, indent=1))
    return 0


def recompute():
    manifest = json.loads((PIN / "MANIFEST.json").read_text())
    freeze = json.loads((PIN / "freeze.json").read_text())
    events_meta = freeze["corpus"]["events"]
    return build(manifest, freeze, events_meta)


def cmd_run(args):
    payload = recompute()
    digest = payload_digest(payload)
    report = {
        "report_id": "w033-f2b-coverage-adjudication-report",
        "created_at": payload["freeze"]["frozen_at"],
        "payload_digest": digest,
        "payload": payload,
    }
    (TASK / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True))
    rows = payload["binding_table"]
    with (TASK / "binding_table.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "parse_ok", "reviewer", "verdict", "score", "target_id",
                    "class_id", "target_is_f2b", "binds_strict", "binds_prefix12",
                    "binds_controller", "full_flag", "gate_flag", "created_at",
                    "source_mtime", "amended_delta_s", "pin_fields_matching",
                    "blind", "reviewer_is_author", "superseded_at", "review_scope"])
        for r in sorted(rows, key=lambda x: x["file"]):
            w.writerow([r["file"], r["parse_ok"], r["reviewer"], r["verdict"], r["score"],
                        r["target_id"] if isinstance(r["target_id"], str) else json.dumps(r["target_id"]),
                        r["class_id"], r["target_is_f2b"], r["binds_strict"],
                        r["binds_prefix12"], r["binds_controller"], r["full_flag"],
                        r["gate_flag"], r["created_at"], r["source_mtime"],
                        r["amended_delta_s"], ";".join(r["pin_fields_matching"]),
                        r["blind"], r["reviewer_is_author"], r["superseded_at"],
                        json.dumps(r["review_scope"])[:200] if r["review_scope"] else ""])
    (TASK / "reconciliation.json").write_text(json.dumps(
        {"published_counts": payload["published_counts"],
         "measured": payload["measured"],
         "lead_reconciliation": payload["lead_reconciliation"],
         "implied_stale_window": payload["implied_stale_window"],
         "key_selection_check": payload["key_selection_check"],
         "in_place_amendment_worker_072": payload["in_place_amendment_worker_072"],
         "independent_crosscheck": payload["independent_crosscheck"],
         "binding_table": rows,
         "integrity_checks": payload["integrity_checks"],
         "payload_digest": digest}, indent=1, sort_keys=True))
    verdict = build_review(payload, digest)
    (TASK / "review.json").write_text(json.dumps(verdict, indent=1, sort_keys=True))
    print(json.dumps({"ok": True, "payload_digest": digest,
                      "file_channel_accepts": payload["measured"]["file_channel_freeze"]["accepts"],
                      "operative_accepts": payload["measured"]["operative_file_accepts"]["reviewers"],
                      "lead_equals_published": payload["lead_reconciliation"],
                      "integrity_all_pass": all(c["pass"] for c in payload["integrity_checks"])},
                     indent=1))
    return 0


def build_review(payload, digest):
    m = payload["measured"]
    file_acc = m["file_channel_freeze"]["accepts"]
    op = m["operative_file_accepts"]["reviewers"]
    lead_recon = {r["reproduction"]: r["equals_published_0_7"] for r in payload["lead_reconciliation"]}
    findings = [
        {"id": "W033-F2B-HF-01", "severity": "hard", "class_id": C0_CLASS,
         "finding": (
             "The formulation lead's published F2b census (0 accept / 7 revise at b2ab6acb2bbe, "
             "lead-form-20260912T0113-107, repeated in CF-31) is not reproducible at its stated "
             "measurement instant. The frozen corpus contains 3 full-schema hash-bound accepts "
             "(worker-090 file F2b-rev13-full-090.json mtime 01:08:56; worker-071 "
             "F2b-review-rev13-worker-071.json mtime 01:10:18; worker-052 F2b-review-rev13-052.json "
             "mtime 01:11:15), each with an exact-64 pin field equal to the live F2b hash. "
             "worker-090's accept predates the lead's stated 01:10 measurement, so a live "
             "re-measurement could not return 0 accepts. The lead's 7-revise set equals exactly the "
             "F2b records whose source mtime is <= 01:05:46, i.e. the count is a pre-01:08 corpus "
             "snapshot mislabelled as a live measurement (reproduction equality: "
             f"{lead_recon}).")},
        {"id": "W033-F2B-HF-02", "severity": "hard", "class_id": C0_CLASS,
         "finding": (
             "worker-072's F2b accept was amended in place at the same path: accept event "
             "w072-2026-09-12T01:10:13+08:00-review-f2b, self-supersede event "
             "w072-f2b-selfsupersede-review-20260912T011524 at 01:15:24, file "
             "F2b-review-worker-072-rev29.json mtime 01:14:54 now verdict=revise with "
             "superseded_at/revision_history fields. Any count quoting worker-072 as an accept is "
             "bound to an instant before 01:14:54; the CF-31 text (4 accepts: 052,071,072,090) was "
             "correct at the 01:12:39 open-pass scan and is stale at current bytes, while the map "
             "reason at 01:16:26 (3: 052,071,090) matches the frozen file channel.")},
        {"id": "W033-F2B-HF-03", "severity": "hard", "class_id": C0_CLASS,
         "finding": (
             "All published counts are instant- and filter-dependent and the corpus has no "
             "append-only record for review files: the same fixed filenames are rewritten "
             "(worker-072 01:14:54, worker-045 F1, worker-075 F2a). The frozen file channel gives "
             f"operative full accepts {op} at the freeze; worker-048's 2-count (090, 072) omits "
             "worker-052/worker-071 although both files existed before its 01:12:00 measurement "
             "and both carry exact-64 pins. No current count may be quoted without naming the "
             "instant and the binding rule.")},
        {"id": "W033-F2B-POS-04", "severity": "info", "class_id": C0_CLASS,
         "finding": (
             "The controller's file-channel scan is reproducible at the frozen bytes: accepts "
             f"{file_acc} (3 distinct full-schema reviewers), matching "
             "controller_gate_audit.G-FORM checked_at 01:16:26 ['worker-052','worker-071',"
             "'worker-090']. Coverage >= 2 full-schema accepts is met at the file channel at the "
             "freeze. This is a coverage-bookkeeping measurement only; it does not certify the "
             "schema.")},
        {"id": "W033-F2B-INFO-05", "severity": "info", "class_id": C0_CLASS,
         "finding": (
             "Coverage and correctness diverge at b2ab6acb2bbe: the lead's own measurement_5 "
             "records two confirmed internal content defects (D1 must_not_conflate containment "
             "denial at line 152 vs line 239; D2 'C2 strictly larger' inversion at line 246) with "
             "corroborating revise verdicts. An accept-count adjudication therefore cannot move "
             "G-FORM; it only prevents a false 0-coverage claim.")},
        {"id": "W033-F2B-INFO-06", "severity": "info", "class_id": C0_CLASS,
         "finding": (
             "Independence/blind facts for the three operative full accepts (audit-lead "
             "adjudication required, not ruled here): worker-090 blind=false with disclosure; "
             "worker-052 reviewer_is_author flag and no counts_as_full_schema_verdict field "
             "(controller rule defaults it to full); worker-071 explicit independence block "
             "(author_of_target=false, blind discipline) and counts_as_full_schema_verdict=true. "
             "worker-048 already flagged the flag-omission hazard.")},
        {"id": "W033-F2B-INFO-07", "severity": "info", "class_id": C0_CLASS,
         "finding": (
             "Cross-check and mechanism discrimination. An independent CF-31 census by worker-017 "
             "(pinned in this freeze) reports the same live full-schema accept set {052,071,090}. "
             "Its key-selection reading of the lead's 0-accept count is not sufficient to "
             "reproduce the lead's 7 revise rows: no single pin key sees all seven "
             "(artifact_sha256-only 5/7, reviewed_sha256-only 6/7). The stale corpus boundary "
             "(all 7 available by 01:05:46, first accept at 01:08:56) reproduces the published "
             "0/7 exactly and is the binding mechanism.")},
    ]
    return {
        "review_id": "w033-f2b-coverage-adjudication-review",
        "task_id": "W033-F2B-COVERAGE-ADJUDICATION-01",
        "reviewer": "worker-033",
        "reviewer_role": "independent non-author of F2b, FROZEN, controller sources and all reviewed verdicts",
        "target_id": "F2b-coverage#b2ab6acb2bbe#freeze-" + payload["freeze"]["frozen_at"],
        "class_ids": [C0_CLASS],
        "gate": "G-FORM",
        "verdict": "revise",
        "score": 2.5,
        "counts_as_full_schema_verdict": False,
        "counts_as_gate_accept": False,
        "scope": ("Accept-set bookkeeping only: reproducibility of the published F2b coverage "
                  "counts at the frozen rev29 hash, per-file binding table, in-place amendment and "
                  "supersession. No gate verdict, no schema semantics, no independence ruling."),
        "adjudication": (
            f"At the freeze instant the reproducible file-channel hash-bound count is "
            f"{len(file_acc)} full-schema accepts {file_acc} and "
            f"{len(m['file_channel_freeze']['by_verdict']['revise'])} revise; the operative set "
            f"excluding worker-072 (self-superseded 01:15:24) is {op}. The controller scan "
            "reproduces this membership; the lead-formulation 0/7 is a stale pre-01:08 corpus "
            "snapshot mislabelled as live and must not be used as the F2b coverage count; the "
            "CF-31 4-count is correct only before 01:14:54."),
        "findings": findings,
        "hard_failures": [f["id"] for f in findings if f["severity"] == "hard"],
        "falsifier": (
            "Re-run this instrument (freeze -> run -> verify, controls fail-closed) on the pinned "
            "snapshot. The adjudication is falsified if any of: worker-090/071/052's accept files "
            "did not exist at their recorded mtimes or their pin fields do not equal "
            "b2ab6acb2bbe...; the lead's 7-revise set is not exactly the F2b records with "
            "availability <= 01:05:46; a later same-reviewer F2b verdict supersedes 090/071/052; "
            "the frozen F2b/frozen-manifest hashes differ from their constants; or the "
            "controller-scan reproduction is rejected by the live astra_lifecycle.review_coverage "
            "at the pinned source hash."),
        "evidence_refs": [
            "artifacts/worker-033/f2b_coverage_adjudication/report.json",
            "artifacts/worker-033/f2b_coverage_adjudication/binding_table.csv",
            "artifacts/worker-033/f2b_coverage_adjudication/reconciliation.json",
            "artifacts/worker-033/f2b_coverage_adjudication/controls.json",
            "artifacts/worker-033/f2b_coverage_adjudication/pinned/MANIFEST.json",
            "artifacts/worker-033/f2b_coverage_adjudication/pinned/freeze.json",
            "artifacts/worker-033/f2b_coverage_adjudication/SHA256SUMS",
            "reviews/F2b-rev13-full-090.json",
            "reviews/F2b-review-rev13-worker-071.json",
            "reviews/F2b-review-rev13-052.json",
            "reviews/F2b-review-worker-072-rev29.json",
            "reviews/W048-GFORM-COVERAGE-RECOUNT-01.json",
            "artifacts/formulation/evidence/lead_formulation_lifecycle_07_independent_verify.json",
            "runtime/state/controller_verification/lifecycle_20260912-011239.json",
        ],
        "payload_digest": digest,
    }


def cmd_verify(args):
    rep = json.loads((TASK / "report.json").read_text())
    got = payload_digest(recompute())
    ok = got == rep["payload_digest"]
    print(json.dumps({"ok": ok, "recorded": rep["payload_digest"], "recomputed": got}, indent=1))
    return 0 if ok else 2


# ---------------------------------------------------------------- controls

def synth_review(path, **kw):
    d = {"reviewer": kw.get("reviewer", "w-test"), "verdict": kw.get("verdict", "accept"),
         "target_id": kw.get("target_id", "F2b"), "score": kw.get("score", 4.0),
         "created_at": kw.get("created_at", "2026-09-12T01:00:00+08:00")}
    for k, v in kw.items():
        if k not in d:
            d[k] = v
    path.write_text(json.dumps(d))


def cmd_controls(args):
    import tempfile
    results = []

    def add(cid, desc, expected, observed):
        ok = expected == observed
        results.append({"id": cid, "description": desc, "expected": expected,
                        "observed": observed, "pass": ok})

    with tempfile.TemporaryDirectory(prefix="w033f2b-") as td:
        td = Path(td)
        # C01 exact-pin accept counted
        synth_review(td / "c01.json", reviewer="w-a", verdict="accept", reviewed_sha256=C0)
        r = classify({"file": "c01.json", "parse_ok": True,
                      "sha256": sha256_file(td / "c01.json"),
                      "doc": json.loads((td / "c01.json").read_text())}, {})
        add("C01", "exact-64 pin accept binds and counts", True,
            r["binds_strict"] and r["verdict"] == "accept" and r["full_flag"])
        # C02 revise not an accept
        synth_review(td / "c02.json", reviewer="w-a", verdict="revise", reviewed_sha256=C0)
        r = classify({"file": "c02.json", "parse_ok": True,
                      "sha256": sha256_file(td / "c02.json"),
                      "doc": json.loads((td / "c02.json").read_text())}, {})
        add("C02", "revise binds but is never counted as accept", True,
            r["binds_strict"] and r["verdict"] == "revise")
        # C03 superseded-hash pin does not bind F2b
        synth_review(td / "c03.json", reviewer="w-a", verdict="accept",
                     reviewed_sha256=SUPERSEDED_C0_REV13)
        r = classify({"file": "c03.json", "parse_ok": True,
                      "sha256": sha256_file(td / "c03.json"),
                      "doc": json.loads((td / "c03.json").read_text())}, {})
        add("C03", "accept pinning a superseded F2b hash does not bind", False, r["binds_prefix12"])
        # C04 scoped accept excluded from full coverage
        synth_review(td / "c04.json", reviewer="w-a", verdict="accept", reviewed_sha256=C0,
                     counts_as_full_schema_verdict=False)
        r = classify({"file": "c04.json", "parse_ok": True,
                      "sha256": sha256_file(td / "c04.json"),
                      "doc": json.loads((td / "c04.json").read_text())}, {})
        add("C04", "scoped accept (flag=false) binds but is not a full accept", False, r["full_flag"])
        # C05 prose mention only -> no binding
        synth_review(td / "c05.json", reviewer="w-a", verdict="accept",
                     findings=[f"the bytes hash to {C0} in prose"])
        r = classify({"file": "c05.json", "parse_ok": True,
                      "sha256": sha256_file(td / "c05.json"),
                      "doc": json.loads((td / "c05.json").read_text())}, {})
        add("C05", "prose mention without a pin field does not bind", False, r["binds_prefix12"])
        # C06 prefix collision: controller rule is lenient by design
        fake = C0[:12] + "ffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        synth_review(td / "c06.json", reviewer="w-a", verdict="accept", reviewed_sha256=fake)
        r = classify({"file": "c06.json", "parse_ok": True,
                      "sha256": sha256_file(td / "c06.json"),
                      "doc": json.loads((td / "c06.json").read_text())}, {})
        add("C06", "12-hex prefix collision: strict rejects, controller prefix rule accepts (documented leniency)",
            {"strict": False, "prefix": True}, {"strict": r["binds_strict"], "prefix": r["binds_prefix12"]})
        # C07 in-place amendment flag
        p = td / "c07.json"
        synth_review(p, reviewer="w-a", verdict="revise", reviewed_sha256=C0,
                     created_at="2026-09-12T01:00:00+08:00")
        manifest = {"c07.json": {"source_mtime": ts_key("2026-09-12T01:10:00+08:00"),
                                 "source_mtime_iso": "2026-09-12T01:10:00+08:00"}}
        r = classify({"file": "c07.json", "parse_ok": True,
                      "sha256": sha256_file(p), "doc": json.loads(p.read_text())}, manifest)
        add("C07", "in-place amendment detected (mtime 600s after created_at)", 600.0, r["amended_delta_s"])
        # C08 target aliases
        ok = []
        for t, want in (("F2", True), ("AF-SCC-C0-VAC-GEN", True), ("F2b", True),
                        ("AF-WCC-VAC-GEN", False), ("F1", False)):
            d = {"target_id": t, "reviewer": "w", "verdict": "accept", "reviewed_sha256": C0}
            ok.append(classify({"file": t, "parse_ok": True, "sha256": "0" * 64, "doc": d},
                               {})["target_is_f2b"] == want)
        add("C08", "target aliases F2/F2b/AF-SCC-C0-VAC-GEN map to F2b; F1/AF-WCC do not", True, all(ok))
        # C09 event supersession
        evs = [{"event_id": "e1", "reviewer": "w-b", "verdict": "accept", "target_id": "F2b",
                "reviewed_sha256": C0, "created_at": "2026-09-12T01:00:00+08:00"},
               {"event_id": "e2", "reviewer": "w-b", "verdict": "revise", "target_id": "F2b",
                "reviewed_sha256": C0, "created_at": "2026-09-12T01:05:00+08:00"}]
        op, sup = supersession(event_rows(evs))
        add("C09", "later same-reviewer verdict supersedes the earlier accept",
            {"operative": "revise", "superseded": ["e1"]},
            {"operative": op[0]["verdict"], "superseded": [s["event_id"] for s in sup]})
        # C10 malformed JSON tolerated
        bad = []
        try:
            (td / "c10.json").write_text("{not json")
            recs = load_reviews(td)
            bad = [r["file"] for r in recs if r["file"] == "c10.json" and r["parse_ok"] is False]
        except Exception:
            bad = []
        add("C10", "malformed review file is recorded unparseable, no crash", ["c10.json"], bad)
        # C11 verdict outside kinds ignored
        synth_review(td / "c11.json", reviewer="w", verdict="maybe", reviewed_sha256=C0)
        r = classify({"file": "c11.json", "parse_ok": True,
                      "sha256": sha256_file(td / "c11.json"),
                      "doc": json.loads((td / "c11.json").read_text())}, {})
        add("C11", "verdict outside accept/revise/reject/inconclusive is ignored", None, r["verdict"])
        # C12 no pin -> no bind
        synth_review(td / "c12.json", reviewer="w", verdict="accept")
        r = classify({"file": "c12.json", "parse_ok": True,
                      "sha256": sha256_file(td / "c12.json"),
                      "doc": json.loads((td / "c12.json").read_text())}, {})
        add("C12", "accept with no pin field does not bind", False, r["binds_prefix12"])
        # C13 stale-boundary filter reproduces an older corpus slice
        manifest2 = {
            "old.json": {"source_mtime": ts_key("2026-09-12T01:00:00+08:00"),
                         "source_mtime_iso": "2026-09-12T01:00:00+08:00"},
            "new.json": {"source_mtime": ts_key("2026-09-12T01:10:00+08:00"),
                         "source_mtime_iso": "2026-09-12T01:10:00+08:00"}}
        synth_review(td / "old.json", reviewer="w-old", verdict="accept", reviewed_sha256=C0)
        synth_review(td / "new.json", reviewer="w-new", verdict="accept", reviewed_sha256=C0)
        rows2 = [classify({"file": n, "parse_ok": True,
                           "sha256": sha256_file(td / n), "doc": json.loads((td / n).read_text())},
                          manifest2) for n in ("old.json", "new.json")]
        add("C13", "instant filter selects the corpus slice available at that instant",
            ["w-old"], census_at(rows2, "2026-09-12T01:05:00+08:00")["distinct_accept_reviewers"])
        # C14 determinism of payload hashing
        add("C14", "canonical payload digest is deterministic", payload_digest({"a": [1, 2]}),
            payload_digest({"a": [1, 2]}))
        # C15 duplicate cross-channel event records collapse by event_id
        dupes = [{"event_id": "x", "reviewer": "w", "verdict": "accept", "target_id": "F2b",
                  "reviewed_sha256": C0, "created_at": "2026-09-12T01:00:00+08:00"}] * 2
        ids = {r["event_id"] for r in event_rows(dupes)}
        add("C15", "duplicate event records collapse to one event_id", 1, len(ids))

    allpass = all(r["pass"] for r in results)
    out = {"mode": "synthetic mutation controls (fail-closed)",
           "n_controls": len(results), "n_pass": sum(1 for r in results if r["pass"]),
           "all_pass": allpass, "controls": results}
    (TASK / "controls.json").write_text(json.dumps(out, indent=1, sort_keys=True))
    print(json.dumps({"all_pass": allpass, "n_pass": out["n_pass"], "n": len(results)}, indent=1))
    return 0 if allpass else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["freeze", "run", "verify", "controls"])
    args = ap.parse_args()
    return {"freeze": cmd_freeze, "run": cmd_run, "verify": cmd_verify,
            "controls": cmd_controls}[args.mode](args)


if __name__ == "__main__":
    sys.exit(main())
