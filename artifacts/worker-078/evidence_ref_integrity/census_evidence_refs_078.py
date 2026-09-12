#!/usr/bin/env python3
"""W078-EVIDENCE-REF-INTEGRITY-01 -- accepted-stream evidence-reference integrity census.

Read-only, deterministic, fail-closed.  Answers one question:

    Of the hash-bound evidence references the accepted stream and the live map still
    carry, how many still resolve to the bytes they name at a single measured instant,
    and which non-resolving classes are hazards rather than expected history?

Scope binding: formulation classes AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN /
AF-SCC-C0-VAC-GEN and nodes F0/F1/F2a/F2b/A0/A1 under gates G-F0/G-FORM/G-AUDIT.

Rules (pre-registered):
  R1 form        `path#<hex 4..64>` and `path#sha256:<hex 4..64>` are hash refs.
                 `path#<non-hex>` is an ANCHOR (e.g. #controller_gate_audit).
                 `path:<int>[-<int>]` is a LINE ref.  Anything else is BARE.
  R2 status      RESOLVED iff the live file's sha256 starts with the prefix;
                 DRIFTED iff the file exists and differs; MISSING iff path absent;
                 DIR_EXISTS iff the target is a directory (hash not applicable);
                 LINE_OK / LINE_OOR for line refs; ANCHOR / EXISTS for the rest.
  R3 hazard      a DRIFTED target is bucketed: MUTABLE_IN_PLACE_REVIEW (reviews/**,
                 no history guarantee), EXPECTED_APPEND (events.jsonl, outbox,
                 ingested_ids), CONTROLLER_STATE (runtime/state/**), SUPERSEDED_PIN
                 (canonical/declared rev trees), WORKING_ARTIFACT (artifacts/**),
                 OTHER.
  R3b misbinding a DRIFTED review ref whose prefix resolves on a *different* live path
                 is reclassified MISBOUND_SUBJECT_HASH: the emitter appended the
                 reviewed artifact's hash to the review path, so the ref never named
                 the review's own bytes.  Only refs whose prefix resolves nowhere are
                 counted as MUTABLE_IN_PLACE_REVIEW (the strict hazard).
  R4 instant     events.jsonl, research_map.json and the reviews/ manifest are
                 measured at T0 and T1.  Any move => instant_stable=false and the
                 census is advisory for the T0 pin only.
  R5 controls    fixture controls C1-C9 plus real-world control C10 (the worker-072
                 superseded F2b accept must classify DRIFTED).  One wrong control => exit 2.
  R6 reproducibility  (a) `--compare-table` gives a live stability report: every ref
                 whose target bytes are unchanged between two runs must keep its
                 classification.  (b) `--fixture-determinism DIR` runs the whole
                 pipeline twice over a frozen synthetic root and requires identical
                 normalized digests.

Exit: 0 census valid; 2 control failure; 3 instant drift (binding void); 4 input missing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
HASHREF = re.compile(r"^(?P<path>[^#\s]+)#(?P<prefix>sha256:)?(?P<hex>[0-9a-fA-F]{4,64})$")
LINEREF = re.compile(r"^(?P<path>[^:\s]+):(?P<a>\d+)(?:-(?P<b>\d+))?$")
ANCHOR = re.compile(r"^[^#\s]+#[^#\s]*$")
MAX_HASH_BYTES = 256 * 1024 * 1024

SCOPE_NODES = {"F0", "F1", "F2a", "F2b", "A0", "A1"}
SCOPE_GATES = {"G-F0", "G-FORM", "G-AUDIT"}
SCOPE_CLASSES = {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"}
VOLATILE_KEYS = ("generated_at", "runtime_seconds", "instants", "measured_at", "mtime_ns",
                 "normalized_digest", "controls", "stability", "determinism_fixture")


def sha256_file(p: Path) -> str | None:
    h = hashlib.sha256()
    try:
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def digest_text(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def tree_manifest(root: Path, sub: str) -> dict:
    base = root / sub
    rows = []
    if base.exists():
        for p in sorted(x for x in base.rglob("*") if x.is_file() and not x.name.startswith("._")):
            rows.append((str(p.relative_to(root)), sha256_file(p)))
    h = hashlib.sha256()
    for rel, d in rows:
        h.update(f"{rel}\0{d}\n".encode())
    return {"count": len(rows), "digest": h.hexdigest()}


def instant(root: Path) -> dict:
    ev = root / "research_map/events.jsonl"
    mp = root / "research_map/research_map.json"
    fz = root / "artifacts/formulation/FROZEN.json"
    out = {"measured_at": datetime.now(CST).isoformat(timespec="seconds")}
    for name, p in (("events", ev), ("map", mp), ("frozen", fz)):
        st = p.stat() if p.exists() else None
        out[name] = {"path": str(p.relative_to(root)), "sha256": sha256_file(p),
                     "bytes": st.st_size if st else None, "mtime_ns": st.st_mtime_ns if st else None}
    rm = tree_manifest(root, "reviews")
    out["reviews_manifest"] = {"count": rm["count"], "digest": rm["digest"]}
    return out


def classify_target(rel: str) -> str:
    if rel.startswith("reviews/"):
        return "REVIEW"
    if rel in ("research_map/events.jsonl", "runtime/state/ingested_ids.json") or rel.startswith("comms/outbox/"):
        return "ACCEPTED_LOG"
    if rel.startswith("runtime/state/"):
        return "CONTROLLER_STATE"
    if rel.startswith(("schemas/", "research_map/", "artifacts/formulation/", "numerics/")):
        return "DECLARED_TREE"
    if rel.startswith("artifacts/"):
        return "WORKING_ARTIFACT"
    if rel.startswith("comms/"):
        return "COMMS"
    return "OTHER"


def hazard_bucket(rel: str) -> str:
    return {"REVIEW": "MUTABLE_IN_PLACE_REVIEW", "ACCEPTED_LOG": "EXPECTED_APPEND",
            "CONTROLLER_STATE": "CONTROLLER_STATE", "DECLARED_TREE": "SUPERSEDED_PIN",
            "WORKING_ARTIFACT": "WORKING_ARTIFACT", "COMMS": "EXPECTED_APPEND"}.get(classify_target(rel), "OTHER")


def parse_ref(ref: str) -> dict:
    ref = ref.strip()
    m = HASHREF.match(ref)
    if m:
        return {"form": "HASH", "path": m.group("path"), "prefix": m.group("hex").lower(),
                "prefix_len": len(m.group("hex")), "sha256_label": bool(m.group("prefix"))}
    m = LINEREF.match(ref)
    if m:
        return {"form": "LINE", "path": m.group("path"), "line_a": int(m.group("a")),
                "line_b": int(m.group("b")) if m.group("b") else int(m.group("a"))}
    if ANCHOR.match(ref):
        return {"form": "ANCHOR", "path": ref.split("#", 1)[0]}
    return {"form": "BARE", "path": ref}


def measure_ref(root: Path, ref: str, hash_cache: dict) -> dict:
    info = parse_ref(ref)
    path = info["path"]
    p = root / path
    row = {**info, "raw": ref, "target_bucket": classify_target(path)}
    if not p.exists():
        row["status"] = {"HASH": "MISSING", "LINE": "MISSING",
                         "ANCHOR": "ANCHOR_ABSENT", "BARE": "ABSENT"}[info["form"]]
        return row
    if p.is_dir():
        row["status"] = "DIR_EXISTS"
        return row
    if info["form"] == "HASH":
        key = str(p)
        if key not in hash_cache:
            st = p.stat()
            hash_cache[key] = ((sha256_file(p), st.st_size) if st.st_size <= MAX_HASH_BYTES else (None, st.st_size))
        digest, size = hash_cache[key]
        row["live_sha256"] = digest
        row["bytes"] = size
        if digest is None:
            row["status"] = "TOO_LARGE"
        elif digest.startswith(info["prefix"]):
            row["status"] = "RESOLVED"
        else:
            row["status"] = "DRIFTED"
            row["hazard"] = hazard_bucket(path)
        return row
    if info["form"] == "LINE":
        try:
            n = sum(1 for _ in p.open("rb"))
        except OSError:
            row["status"] = "MISSING"
            return row
        row["line_count"] = n
        row["status"] = "LINE_OK" if info["line_b"] <= n else "LINE_OOR"
        return row
    if info["form"] == "ANCHOR":
        row["status"] = "ANCHOR"
        return row
    row["status"] = "EXISTS"
    return row


def load_citations(events_path: Path) -> tuple[dict, int]:
    by_ref: dict[str, dict] = {}
    n_events = 0
    with events_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            n_events += 1
            refs = []
            for k in ("evidence_refs", "artifact_refs"):
                v = e.get(k)
                if isinstance(v, list):
                    refs += [x for x in v if isinstance(x, str) and x.strip()]
            if not refs:
                continue
            nodes = {e.get("node_id")} if isinstance(e.get("node_id"), str) else set(str(x) for x in (e.get("node_id") or []) if x)
            classes = set()
            if isinstance(e.get("class_id"), str):
                classes = {c.strip() for c in re.split(r"[;,]", e["class_id"]) if c.strip()}
            gates = {e.get("gate")} if isinstance(e.get("gate"), str) else set()
            scoped = bool((nodes & SCOPE_NODES) or (gates & SCOPE_GATES) or (classes & SCOPE_CLASSES))
            for r in refs:
                d = by_ref.setdefault(r, {"cited_event_count": 0, "event_ids": [], "event_types": set(),
                                          "actors": set(), "nodes": set(), "classes": set(), "gates": set(),
                                          "scoped": False, "first": e.get("created_at"), "last": e.get("created_at")})
                d["cited_event_count"] += 1
                if len(d["event_ids"]) < 10:
                    d["event_ids"].append(e.get("event_id"))
                if e.get("event_type"):
                    d["event_types"].add(e["event_type"])
                if e.get("actor"):
                    d["actors"].add(e["actor"])
                d["nodes"] |= nodes
                d["classes"] |= classes
                d["gates"] |= gates
                d["scoped"] = d["scoped"] or scoped
                ca = e.get("created_at")
                if ca:
                    d["first"] = min(d["first"] or ca, ca)
                    d["last"] = max(d["last"] or ca, ca)
    return by_ref, n_events


def load_map_decisions(map_path: Path) -> dict:
    m = json.loads(map_path.read_text())
    gates = [{"gate_id": g.get("gate_id"), "verdict": g.get("verdict"),
              "evidence_refs": [r for r in (g.get("evidence_refs") or []) if isinstance(r, str)]}
             for g in m.get("gates", [])]
    reviews = [{"event_id": r.get("event_id"), "reviewer": r.get("reviewer"), "verdict": r.get("verdict"),
                "target_id": r.get("target_id"), "node_id": r.get("node_id"),
                "evidence_refs": [x for x in (r.get("evidence_refs") or []) if isinstance(x, str)]}
               for r in m.get("reviews", [])]
    claims = [{"event_id": c.get("event_id"), "actor": c.get("actor"), "class_id": c.get("class_id"),
               "node_id": c.get("node_id"), "conclusion_type": c.get("conclusion_type"),
               "evidence_refs": [x for x in (c.get("evidence_refs") or []) if isinstance(x, str)]}
              for c in m.get("claims", [])]
    return {"gates": gates, "reviews": reviews, "claims": claims}


def decision_slice(name: str, records: list, table_by_raw: dict) -> dict:
    n_refs = n_distinct = 0
    status_counts: dict[str, int] = {}
    bad = []
    for rec in records:
        for r in rec["evidence_refs"]:
            n_refs += 1
            row = table_by_raw.get(r)
            if row is None:
                continue
            n_distinct += 1
            status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
            if row["status"] in ("DRIFTED", "MISSING", "TOO_LARGE"):
                bad.append({"ref": r, "status": row["status"], "hazard": row.get("hazard"),
                            "target_bucket": row["target_bucket"],
                            "record": {k: rec.get(k) for k in ("gate_id", "event_id", "reviewer", "verdict",
                                                               "target_id", "actor", "class_id") if rec.get(k)}})
    return {"slice": name, "citations": n_refs, "distinct_refs": n_distinct,
            "status_counts": dict(sorted(status_counts.items())), "non_resolving": bad}


def fixture_controls(root: Path, out_dir: Path) -> list:
    fx = out_dir / "fixtures"
    fx.mkdir(parents=True, exist_ok=True)
    good = fx / "good.txt"
    good.write_text("control-payload-alpha\n")
    d = sha256_file(good)
    (fx / "adir").mkdir(exist_ok=True)
    controls = [
        ("C1", f"artifacts/worker-078/evidence_ref_integrity/fixtures/good.txt#{d[:12]}", "RESOLVED"),
        ("C2", f"artifacts/worker-078/evidence_ref_integrity/fixtures/good.txt#{'0'*12}", "DRIFTED"),
        ("C3", f"artifacts/worker-078/evidence_ref_integrity/fixtures/absent.txt#{d[:8]}", "MISSING"),
        ("C4", f"artifacts/worker-078/evidence_ref_integrity/fixtures/good.txt#{d[:4]}", "RESOLVED"),
        ("C5", "artifacts/worker-078/evidence_ref_integrity/fixtures/good.txt#zzzz-not-hex", "ANCHOR"),
        ("C6", f"artifacts/worker-078/evidence_ref_integrity/fixtures/good.txt#sha256:{d[:10]}", "RESOLVED"),
        ("C7", f"artifacts/worker-078/evidence_ref_integrity/fixtures/adir#{d[:8]}", "DIR_EXISTS"),
        ("C8", "artifacts/worker-078/evidence_ref_integrity/fixtures/good.txt:1", "LINE_OK"),
        ("C9", "artifacts/worker-078/evidence_ref_integrity/fixtures/good.txt:999", "LINE_OOR"),
    ]
    cache: dict = {}
    res = []
    for cid, ref, expect in controls:
        row = measure_ref(root, ref, cache)
        res.append({"id": cid, "ref": ref, "expected": expect, "observed": row["status"],
                    "pass": row["status"] == expect})
    return res


def normalize(report: dict) -> str:
    def strip(o):
        if isinstance(o, dict):
            return {k: strip(v) for k, v in o.items() if k not in VOLATILE_KEYS}
        if isinstance(o, list):
            return [strip(x) for x in o]
        return o
    return digest_text(json.dumps(strip(report), sort_keys=True, separators=(",", ":")).encode())


def run_census(root: Path, events_path: Path, map_path: Path, out_dir: Path) -> tuple[dict, dict, list]:
    inst_start = instant(root)
    citations, n_events = load_citations(events_path)
    by_raw: dict[str, dict] = {}
    hash_cache: dict = {}
    for ref in sorted(citations):
        row = measure_ref(root, ref, hash_cache)
        d = citations[ref]
        row.update({"cited_event_count": d["cited_event_count"], "cited_event_ids": d["event_ids"],
                    "event_types": sorted(d["event_types"]), "actors": sorted(d["actors"]),
                    "nodes": sorted(x for x in d["nodes"] if x), "classes": sorted(d["classes"]),
                    "gates": sorted(d["gates"]), "scoped": d["scoped"],
                    "first_cited": d["first"], "last_cited": d["last"]})
        by_raw[ref] = row

    # R3b: separate subject-hash misbinding from true in-place review rewrites.
    live_by_hash = {}
    for row in by_raw.values():
        if row["status"] == "RESOLVED" and row.get("live_sha256"):
            live_by_hash.setdefault(row["live_sha256"], row["path"])
    for row in by_raw.values():
        if row["status"] == "DRIFTED" and row.get("hazard") == "MUTABLE_IN_PLACE_REVIEW":
            for live_hash, owner in live_by_hash.items():
                if owner != row["path"] and live_hash.startswith(row["prefix"]):
                    row["hazard"] = "MISBOUND_SUBJECT_HASH"
                    row["misbound_to"] = owner
                    break

    status_dist: dict[str, int] = {}
    hazard_dist: dict[str, int] = {}
    for row in by_raw.values():
        status_dist[row["status"]] = status_dist.get(row["status"], 0) + 1
        if row["status"] == "DRIFTED":
            hazard_dist[row["hazard"]] = hazard_dist.get(row["hazard"], 0) + 1
    scoped_rows = [r for r in by_raw.values() if r["scoped"]]
    scoped_status: dict[str, int] = {}
    scoped_hazard: dict[str, int] = {}
    for row in scoped_rows:
        scoped_status[row["status"]] = scoped_status.get(row["status"], 0) + 1
        if row["status"] == "DRIFTED":
            scoped_hazard[row["hazard"]] = scoped_hazard.get(row["hazard"], 0) + 1

    decisions = load_map_decisions(map_path)
    gate_slice = [decision_slice("gate:" + g["gate_id"], [g], by_raw) for g in decisions["gates"]]
    review_slice = decision_slice("map.reviews", decisions["reviews"], by_raw)
    claim_slice = decision_slice("map.claims", decisions["claims"], by_raw)

    ctrl072 = [r for r in by_raw if r.startswith("reviews/F2b-review-worker-072-rev29.json#7487f310")]
    c10_pass = bool(ctrl072) and all(by_raw[r]["status"] == "DRIFTED" for r in ctrl072)
    controls = fixture_controls(root, out_dir)
    controls.append({"id": "C10",
                     "ref": sorted(ctrl072)[0] if ctrl072 else "reviews/F2b-review-worker-072-rev29.json#7487f310(absent)",
                     "expected": "DRIFTED",
                     "observed": by_raw[sorted(ctrl072)[0]]["status"] if ctrl072 else "REF_NOT_IN_STREAM",
                     "pass": c10_pass, "note": "real-world control: superseded in-place F2b accept (worker-072)"})
    controls_pass = all(c["pass"] for c in controls)
    review_hazards = sorted(r["raw"] for r in by_raw.values()
                            if r["status"] == "DRIFTED" and r["hazard"] == "MUTABLE_IN_PLACE_REVIEW")
    review_hazards_scoped = sorted(r["raw"] for r in by_raw.values()
                                   if r["status"] == "DRIFTED" and r["hazard"] == "MUTABLE_IN_PLACE_REVIEW" and r["scoped"])
    misbound = sorted(r["raw"] for r in by_raw.values()
                      if r["status"] == "DRIFTED" and r["hazard"] == "MISBOUND_SUBJECT_HASH")
    misbound_scoped = sorted(r["raw"] for r in by_raw.values()
                             if r["status"] == "DRIFTED" and r["hazard"] == "MISBOUND_SUBJECT_HASH" and r["scoped"])

    inst0 = instant(root)
    internal_drift = []
    if inst_start["events"]["sha256"] != inst0["events"]["sha256"]:
        internal_drift.append("research_map/events.jsonl")
    if inst_start["map"]["sha256"] != inst0["map"]["sha256"]:
        internal_drift.append("research_map/research_map.json")
    if inst_start["reviews_manifest"]["digest"] != inst0["reviews_manifest"]["digest"]:
        internal_drift.append("reviews/**")
    report = {
        "schema": "worker-078/evidence-ref-integrity/v1",
        "task_id": "W078-EVIDENCE-REF-INTEGRITY-01",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "node_id": "F0,F1,F2a,F2b,A0,A1",
        "gate": "G-FORM;G-AUDIT;G-F0",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "scope": {"nodes": sorted(SCOPE_NODES), "gates": sorted(SCOPE_GATES), "classes": sorted(SCOPE_CLASSES)},
        "pins": {"events_sha256": inst0["events"]["sha256"], "map_sha256": inst0["map"]["sha256"],
                 "frozen_sha256": inst0["frozen"]["sha256"],
                 "reviews_manifest_digest": inst0["reviews_manifest"]["digest"],
                 "reviews_file_count": inst0["reviews_manifest"]["count"]},
        "headline": {
            "events_parsed": n_events, "distinct_refs": len(by_raw),
            "ref_citations": sum(r["cited_event_count"] for r in by_raw.values()),
            "status_distinct": dict(sorted(status_dist.items())),
            "hazard_distinct_drifted": dict(sorted(hazard_dist.items())),
            "scoped_distinct_refs": len(scoped_rows),
            "scoped_status_distinct": dict(sorted(scoped_status.items())),
            "scoped_hazard_distinct_drifted": dict(sorted(scoped_hazard.items())),
            "mutable_in_place_review_refs": len(review_hazards),
            "mutable_in_place_review_refs_scoped": len(review_hazards_scoped),
            "misbound_subject_hash_refs": len(misbound),
            "misbound_subject_hash_refs_scoped": len(misbound_scoped),
            "resolved_fraction_distinct": round(status_dist.get("RESOLVED", 0) / max(1, len(by_raw)), 4),
        },
        "decision_slices": {"gates": gate_slice, "map_reviews": review_slice, "map_claims": claim_slice},
        "review_byte_hazards": {"all": review_hazards, "scoped": review_hazards_scoped},
        "real_world_controls": {"worker_072_superseded_accept_refs": sorted(ctrl072),
                                "worker_072_citations": sum(by_raw[r]["cited_event_count"] for r in ctrl072),
                                "classification": "DRIFTED" if c10_pass else "CONTROL_FAILED"},
        "controls": controls, "controls_pass": controls_pass,
        "instant_stable_internal": not internal_drift, "instant_drift_internal": internal_drift,
        "falsifier": ("FALSIFIED by: (a) any control C1-C10 changing classification on a byte-identical "
                      "re-run; (b) a live path reported DRIFTED while its live sha256 starts with the cited "
                      "prefix; (c) a reference reported RESOLVED whose cited prefix is absent from the live "
                      "bytes; (d) a reported count not matching the per-ref binding_table.json it was computed "
                      "from; (e) t0/t1 instant drift not reported."),
        "non_claims": ["No gate verdict, no node transition, no validation_status=passed, no canonical write.",
                       "DRIFTED is not by itself a defect: EXPECTED_APPEND (events.jsonl, outbox) and "
                       "SUPERSEDED_PIN (old revisions) are history. The strict hazard class is "
                       "MUTABLE_IN_PLACE_REVIEW: bytes cited as binding that were rewritten with no history copy.",
                       "The census is advisory for its measured pin only; any later write voids it."],
    }
    table = {"schema": "worker-078/evidence-ref-integrity/table/v1", "pins": report["pins"],
             "rows": [by_raw[r] for r in sorted(by_raw)]}
    return report, table, controls


def compare_tables(prev: dict, cur: dict) -> dict:
    p = {r["raw"]: r for r in prev["rows"]}
    c = {r["raw"]: r for r in cur["rows"]}
    both = sorted(set(p) & set(c))
    unchanged = [r for r in both if p[r].get("live_sha256") and p[r].get("live_sha256") == c[r].get("live_sha256")]
    bytes_moved = [r for r in both if p[r].get("live_sha256") and c[r].get("live_sha256")
                   and p[r]["live_sha256"] != c[r]["live_sha256"]]
    status_changed = [{"ref": r, "prev": p[r]["status"], "cur": c[r]["status"]}
                      for r in unchanged if p[r]["status"] != c[r]["status"]]
    status_changed_any = [{"ref": r, "prev": p[r]["status"], "cur": c[r]["status"]}
                          for r in both if p[r]["status"] != c[r]["status"]]
    return {
        "schema": "worker-078/evidence-ref-integrity/stability/v1",
        "task_id": "W078-EVIDENCE-REF-INTEGRITY-01",
        "prev_pins": prev["pins"], "cur_pins": cur["pins"],
        "rows_prev": len(p), "rows_cur": len(c), "rows_both": len(both),
        "rows_unchanged_bytes": len(unchanged), "rows_bytes_moved": len(bytes_moved),
        "status_changed_on_unchanged_bytes": status_changed,
        "status_changed_all": status_changed_any,
        "stable_subset_agreement": (len(unchanged) - len(status_changed)) / max(1, len(unchanged)),
        "verdict": "STABLE" if not status_changed else "UNSTABLE",
        "note": ("Live targets move under continuing traffic; the audit question is whether every ref whose "
                 "bytes are unchanged keeps its classification. status_changed_all lists moves caused by "
                 "target-byte changes (expected, not a defect)."),
    }


def build_fixture_root(det_dir: Path) -> Path:
    root = det_dir / "det_root"
    if root.exists():
        shutil.rmtree(root)
    (root / "research_map").mkdir(parents=True)
    (root / "artifacts/formulation").mkdir(parents=True)
    (root / "reviews").mkdir(parents=True)
    (root / "corpus").mkdir(parents=True)
    a = root / "corpus/a.txt"
    a.write_text("alpha\nbeta\ngamma\n")
    b = root / "corpus/b.txt"
    b.write_text("payload-b\n")
    rev = root / "reviews/one.json"
    rev.write_text('{"reviewer":"fixture","verdict":"accept"}\n')
    da, db, dr = sha256_file(a), sha256_file(b), sha256_file(rev)
    root.joinpath("artifacts/formulation/FROZEN.json").write_text('{"revision":1}')
    events = [
        {"event_id": "fx-1", "event_type": "claim", "created_at": "2026-01-01T00:00:00+08:00", "actor": "fx",
         "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
         "evidence_refs": [f"corpus/a.txt#{da[:12]}", f"corpus/b.txt#{'0'*12}", "corpus/absent.txt#abcd1234",
                           f"reviews/one.json#{dr[:8]}", "corpus/a.txt:2", "corpus/a.txt:99",
                           "corpus/a.txt#not-a-hash", "research_map/events.jsonl#deadbeef"]},
        {"event_id": "fx-2", "event_type": "artifact", "created_at": "2026-01-01T00:01:00+08:00", "actor": "fx",
         "node_id": "F0", "class_id": "AF-WCC-VAC-GEN", "gate": "G-F0",
         "evidence_refs": [f"corpus/a.txt#sha256:{da[:10]}", f"corpus/b.txt#{db[:8]}"]},
    ]
    root.joinpath("research_map/events.jsonl").write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in events))
    m = {"gates": [{"gate_id": "G-FORM", "verdict": "pending",
                    "evidence_refs": [f"corpus/a.txt#{da[:12]}", f"corpus/b.txt#{'0'*12}"]}],
         "reviews": [{"event_id": "fx-r1", "reviewer": "fixture", "verdict": "accept",
                      "evidence_refs": [f"reviews/one.json#{dr[:8]}"]}],
         "claims": [{"event_id": "fx-1", "class_id": "AF-SCC-C0-VAC-GEN",
                     "evidence_refs": ["corpus/absent.txt#abcd1234"]}]}
    root.joinpath("research_map/research_map.json").write_text(json.dumps(m))
    return root


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    ap.add_argument("--json-out", required=True)
    ap.add_argument("--table-out", required=True)
    ap.add_argument("--controls-out", required=True)
    ap.add_argument("--events", default="research_map/events.jsonl")
    ap.add_argument("--map", default="research_map/research_map.json")
    ap.add_argument("--compare-table", default=None, help="previous binding_table.json for a stability report")
    ap.add_argument("--stability-out", default=None)
    ap.add_argument("--fixture-determinism", default=None, help="dir for the frozen end-to-end determinism fixture")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    out_dir = Path(args.json_out).resolve().parent
    t0_wall = time.time()
    events_path = root / args.events
    map_path = root / args.map
    for p in (events_path, map_path):
        if not p.exists():
            print(f"FAIL input missing: {p}")
            return 4

    report, table, controls = run_census(root, events_path, map_path, out_dir)
    controls_pass = report["controls_pass"]

    if args.fixture_determinism:
        det_root = build_fixture_root(Path(args.fixture_determinism).resolve())
        d1, _, _ = run_census(det_root, det_root / "research_map/events.jsonl",
                              det_root / "research_map/research_map.json", out_dir)
        d2, _, _ = run_census(det_root, det_root / "research_map/events.jsonl",
                              det_root / "research_map/research_map.json", out_dir)
        d1["normalized_digest"] = normalize(d1)
        d2["normalized_digest"] = normalize(d2)
        report["determinism_fixture"] = {
            "root": "artifacts/worker-078/evidence_ref_integrity/determinism/det_root",
            "run1_normalized": d1["normalized_digest"], "run2_normalized": d2["normalized_digest"],
            "equal": d1["normalized_digest"] == d2["normalized_digest"],
            "events": d1["headline"]["events_parsed"], "distinct_refs": d1["headline"]["distinct_refs"],
            "status_distinct": d1["headline"]["status_distinct"],
        }
        if not report["determinism_fixture"]["equal"]:
            controls_pass = False

    inst1 = instant(root)
    stable = (report["pins"]["events_sha256"] == inst1["events"]["sha256"]
              and report["pins"]["map_sha256"] == inst1["map"]["sha256"]
              and report["pins"]["reviews_manifest_digest"] == inst1["reviews_manifest"]["digest"])
    drift = []
    if report["pins"]["events_sha256"] != inst1["events"]["sha256"]:
        drift.append("research_map/events.jsonl")
    if report["pins"]["map_sha256"] != inst1["map"]["sha256"]:
        drift.append("research_map/research_map.json")
    if report["pins"]["reviews_manifest_digest"] != inst1["reviews_manifest"]["digest"]:
        drift.append("reviews/**")
    report["instant_stable"] = stable and report["instant_stable_internal"]
    report["instant_drift"] = sorted(set(drift) | set(report["instant_drift_internal"]))
    report["instants"] = {"t0_measured_at": report["generated_at"], "t1_reviews_count": inst1["reviews_manifest"]["count"]}
    report["runtime_seconds"] = round(time.time() - t0_wall, 3)
    report["normalized_digest"] = normalize(report)
    Path(args.json_out).write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    Path(args.table_out).write_text(json.dumps(table, sort_keys=True) + "\n")
    Path(args.controls_out).write_text(json.dumps({"controls": controls, "pass": controls_pass}, indent=1, sort_keys=True) + "\n")

    if args.compare_table and args.stability_out:
        prev = json.loads(Path(args.compare_table).read_text())
        stab = compare_tables(prev, table)
        Path(args.stability_out).write_text(json.dumps(stab, indent=1, sort_keys=True) + "\n")
        print(f"stability verdict={stab['verdict']} agreement={stab['stable_subset_agreement']:.4f} "
              f"unchanged={stab['rows_unchanged_bytes']} moved={stab['rows_bytes_moved']}")

    h = report["headline"]
    print(f"events={h['events_parsed']} distinct_refs={h['distinct_refs']} "
          f"resolved={h['status_distinct'].get('RESOLVED',0)} drifted={h['status_distinct'].get('DRIFTED',0)} "
          f"missing={h['status_distinct'].get('MISSING',0)} review_hazards={h['mutable_in_place_review_refs']} "
          f"(scoped {h['mutable_in_place_review_refs_scoped']}) controls={'PASS' if controls_pass else 'FAIL'} "
          f"stable={stable} normalized={report['normalized_digest'][:16]}")
    if not controls_pass:
        return 2
    if not report["instant_stable"]:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
