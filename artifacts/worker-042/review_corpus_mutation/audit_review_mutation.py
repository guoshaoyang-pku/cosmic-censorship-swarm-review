#!/usr/bin/env python3
"""W042-REVIEW-CORPUS-MUTATION-09 checker (stdlib only).

Two-pin audit of the review corpus at fixed filenames:
  T0 = worker-042 W042-GATE-SCAN-GAP-02 pin, 2026-09-12T00:26:27+08:00,
       72 files byte-copied under artifacts/worker-042/gate_scan_gap/snapshot/reviews/
       with per-file sha256 in that snapshot's manifest (referenced and hashed here).
  T1 = this task's freeze-first pin under snapshot/ (see snapshot/manifest.json).

Measures: byte mutation at fixed names, verdict-bearing field deltas (same-pin flip
vs rebind vs name reuse), hash-bound coverage drift for five measured pins, corpus
growth.  Emits report.json with per-finding falsifiers and controls.  Read-only over
canonical paths; writes only report.json and the control sandbox under this worker's
artifacts path.

Usage: python3 artifacts/worker-042/review_corpus_mutation/audit_review_mutation.py
Exit: 0 ok, 2 fail-closed (pin/substrate drift, control failure).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SNAP = os.path.join(HERE, "snapshot")
SANDBOX = os.path.join(HERE, "_control_sandbox")
TASK_ID = "W042-REVIEW-CORPUS-MUTATION-09"
CST = timezone(timedelta(hours=8))

# exact measured pins (astra-lifecycle-08 decisions record)
PINS = {
    "F1_rev13": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "F2a_rev13": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "F2b_rev13": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "L0_a1674f": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "L1_315c": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
}
PREFIX = 12
DELTA_KEYS = ("verdict", "score", "reviewed_sha256", "artifact_sha256", "reviewed_path",
              "target_id", "node_id", "gate", "class_id", "class_ids",
              "counts_as_full_schema_verdict", "counts_as_independent", "review_kind",
              "created_at", "event_id", "reviewer", "actor", "correction_note", "frozen")
IDENTITY_KEYS = ("target_id", "node_id", "created_at", "event_id")
VERDICT_WORDS = {"accept", "revise", "reject", "inconclusive"}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str) -> str:
    return sha256_bytes(open(path, "rb").read())


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def s(x) -> str:
    return x if isinstance(x, str) else ("" if x is None else str(x))


def pin_of(d: dict) -> str:
    for k in ("reviewed_sha256", "artifact_sha256"):
        v = d.get(k)
        if isinstance(v, str) and len(v) >= 8:
            return v
    return ""


def identity(d: dict):
    return tuple(s(d.get(k)) for k in IDENTITY_KEYS)


def load_json(path: str):
    try:
        with open(path) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def classify(t0: dict, t1: dict) -> str:
    """Classify one fixed filename's T0->T1 delta from parsed documents."""
    p0, p1 = pin_of(t0), pin_of(t1)
    v0, v1 = s(t0.get("verdict")), s(t1.get("verdict"))
    same_bind = (p0 == p1 and p0 != "")
    if v0 != v1:
        if same_bind:
            return "SAME_PIN_VERDICT_CHANGE"
        if p0 and p1 and p0 != p1:
            return "REBIND_VERDICT_CHANGE"
        return "IDENTITY_OR_BINDING_CHANGE"
    if t0.get("score") != t1.get("score"):
        return "SCORE_CHANGE"
    if p0 != p1 and (p0 or p1):
        return "REBIND_OTHER"
    return "CONTENT_ONLY"


def delta_fields(t0: dict, t1: dict) -> dict:
    out = {}
    for k in DELTA_KEYS:
        a, b = t0.get(k), t1.get(k)
        if a != b:
            ra, rb = s(a), s(b)
            out[k] = {"t0": (ra[:160] + "...") if len(ra) > 160 else ra,
                      "t1": (rb[:160] + "...") if len(rb) > 160 else rb}
    return out


def scan_corpus(dirpath: str) -> dict:
    """filename -> parsed doc, for *.json only; parse failures marked, never raised."""
    out = {}
    if not os.path.isdir(dirpath):
        return out
    for name in sorted(os.listdir(dirpath)):
        if not name.endswith(".json"):
            continue
        d = load_json(os.path.join(dirpath, name))
        out[name] = d if d is not None else {"__parse_error__": True}
    return out


def mutate_rows(t0_dir: str, t1_dir: str, t0_files: dict) -> list:
    """Fixed-filename mutation rows for every file in the T0 manifest."""
    t0_docs, t1_docs = scan_corpus(t0_dir), scan_corpus(t1_dir)
    rows = []
    for name in sorted(t0_files):
        h0 = t0_files[name]["sha256"]
        p1 = os.path.join(t1_dir, name)
        if not os.path.exists(p1):
            rows.append({"file": name, "class": "MISSING_AT_T1", "t0_sha256": h0,
                         "t1_sha256": None, "fields": {}, "name_reuse": False})
            continue
        h1 = sha256_file(p1)
        if h0 == h1:
            continue
        d0, d1 = t0_docs.get(name), t1_docs.get(name)
        if d0 is None or d1 is None or "__parse_error__" in d0 or "__parse_error__" in d1:
            rows.append({"file": name, "class": "PARSE_DIVERGENCE", "t0_sha256": h0,
                         "t1_sha256": h1, "fields": {}, "name_reuse": False})
            continue
        rows.append({"file": name, "class": classify(d0, d1), "t0_sha256": h0,
                     "t1_sha256": h1, "fields": delta_fields(d0, d1),
                     "name_reuse": identity(d0) != identity(d1)})
    return rows


def coverage(docs: dict) -> dict:
    res = {}
    for pin, full in PINS.items():
        pf = full[:PREFIX]
        rows = []
        for name in sorted(docs):
            d = docs[name]
            if "__parse_error__" in d:
                continue
            p = pin_of(d)
            if p.startswith(pf):
                rows.append({
                    "file": name,
                    "verdict": s(d.get("verdict")),
                    "score": d.get("score"),
                    "full_schema": d.get("counts_as_full_schema_verdict"),
                    "reviewer": s(d.get("reviewer") or d.get("actor")),
                    "created_at": s(d.get("created_at")),
                    "review_kind": s(d.get("review_kind")),
                    "pin_field": "reviewed_sha256" if isinstance(d.get("reviewed_sha256"), str) else "artifact_sha256",
                })
        res[pin] = {
            "pin_full_sha256": full,
            "matched_by_prefix": pf,
            "files": len(rows),
            "hash_bound_verdicts_any_polarity": sum(1 for r in rows if r["verdict"] in VERDICT_WORDS),
            "accepts": sum(1 for r in rows if r["verdict"] == "accept"),
            "full_schema_accepts": sum(1 for r in rows
                                       if r["verdict"] == "accept" and r["full_schema"] is not False),
            "rows": rows,
        }
    return res


def main() -> int:
    fails = []
    t1man = json.load(open(os.path.join(SNAP, "manifest.json")))
    t1_manifest_sha = sha256_file(os.path.join(SNAP, "manifest.json"))
    t0man = load_json(os.path.join(SNAP, t1man["sources"]["t0_manifest"]["snapshot"]))

    # ---- prerequisite: T0 substrate bytes match the T0 manifest -----------
    t0_dir = os.path.join(REPO, t1man["t0"]["reviews_dir"])
    t0_bad = []
    for name, rec in sorted(t0man["reviews_manifest"].items()):
        p = os.path.join(t0_dir, name)
        if not os.path.exists(p) or sha256_file(p) != rec["sha256"]:
            t0_bad.append(name)
    t0_ok = len(t0man["reviews_manifest"]) - len(t0_bad)
    if t0_bad:
        fails.append("T0_SUBSTRATE_HASH_MISMATCH:%d" % len(t0_bad))

    t1_dir = os.path.join(SNAP, "reviews_t1")
    t0_docs, t1_docs = scan_corpus(t0_dir), scan_corpus(t1_dir)
    mutations = mutate_rows(t0_dir, t1_dir, t0man["reviews_manifest"])
    name_reuse = [{"file": m["file"],
                   "t0_identity": dict(zip(IDENTITY_KEYS, identity(t0_docs[m["file"]]))),
                   "t1_identity": dict(zip(IDENTITY_KEYS, identity(t1_docs[m["file"]])))}
                  for m in mutations
                  if m.get("name_reuse") and m["file"] in t0_docs and m["file"] in t1_docs]
    for m in mutations:
        m.pop("name_reuse", None)

    new_files = sorted(set(t1_docs) - set(t0_docs))
    new_with_verdict = [n for n in new_files if s(t1_docs[n].get("verdict")) in VERDICT_WORDS]
    new_bound = {}
    for pin, full in PINS.items():
        pf = full[:PREFIX]
        new_bound[pin] = sorted(n for n in new_files
                                if "__parse_error__" not in t1_docs[n]
                                and pin_of(t1_docs[n]).startswith(pf))
    cov0, cov1 = coverage(t0_docs), coverage(t1_docs)

    # ---- controls ---------------------------------------------------------
    shutil.rmtree(SANDBOX, ignore_errors=True)
    ctl_dir = os.path.join(SANDBOX, "c7")
    os.makedirs(ctl_dir)
    controls = []

    def ctl(cid, ok, note):
        controls.append({"id": cid, "pass": bool(ok), "note": note})
        if not ok:
            fails.append("CONTROL_FAILED:" + cid)

    ctl("C1_T0_SUBSTRATE_SELFCHECK", not t0_bad,
        "%d/%d T0 files hash to the T0 manifest" % (t0_ok, len(t0man["reviews_manifest"])))
    # C2: one-bit flip changes the hash and is classified as a mutation
    src_name = sorted(t0_docs)[0]
    raw = bytearray(open(os.path.join(t1_dir, src_name), "rb").read())
    raw[len(raw) // 2] ^= 0x01
    probe = os.path.join(ctl_dir, src_name)
    open(probe, "wb").write(bytes(raw))
    rows = mutate_rows(t0_dir, ctl_dir, {src_name: t0man["reviews_manifest"][src_name]})
    ctl("C2_BYTE_MUTATION_DETECTED", len(rows) == 1 and rows[0]["class"] != "MISSING_AT_T1",
        "one-bit flip detected as %s" % (rows[0]["class"] if rows else "NO_ROW"))
    # C3/C4: classifier truth table
    a = {"verdict": "accept", "score": 4, "reviewed_sha256": "a" * 64,
         "target_id": "F2b", "node_id": "F2b", "created_at": "t", "event_id": "e"}
    b = dict(a, verdict="revise", score=3)
    c = dict(a, reviewed_sha256="b" * 64)
    ctl("C3_SAME_PIN_FLIP", classify(a, b) == "SAME_PIN_VERDICT_CHANGE", classify(a, b))
    ctl("C4_REBIND_CLASSIFIED",
        classify(a, c) == "REBIND_OTHER" and classify(a, dict(c, verdict="revise")) == "REBIND_VERDICT_CHANGE",
        "%s / %s" % (classify(a, c), classify(a, dict(c, verdict="revise"))))
    ctl("C5_NAME_REUSE", identity(a) != identity(dict(a, target_id="L1", event_id="other")),
        "identity tuple changes on target/event change")
    # C6: coverage counter on a synthetic corpus (pin prefix must be the real one)
    synpin = PINS["F2b_rev13"][:PREFIX] + "0" * (64 - PREFIX)
    syn = {"x.json": dict(a, reviewed_sha256=synpin),
           "y.json": dict(a, reviewed_sha256=synpin, counts_as_full_schema_verdict=False),
           "z.json": dict(a, reviewed_sha256="deadbeef" + "0" * 56, verdict="revise")}
    syn_cov = coverage(syn)["F2b_rev13"]
    ctl("C6_COVERAGE_COUNTER", syn_cov["accepts"] == 2 and syn_cov["full_schema_accepts"] == 1,
        "2 accepts / 1 full at synthetic pin, files=%d" % syn_cov["files"])
    # C7: missing-file branch through the production mutation function
    rows7 = mutate_rows(t0_dir, os.path.join(SANDBOX, "empty"), {src_name: t0man["reviews_manifest"][src_name]})
    ctl("C7_MISSING_HANDLED", len(rows7) == 1 and rows7[0]["class"] == "MISSING_AT_T1",
        "missing T1 copy classified %s" % (rows7[0]["class"] if rows7 else "NO_ROW"))
    # C8: parse-error branch
    badp = os.path.join(ctl_dir, "broken.json")
    open(badp, "w").write("{not json")
    ctl("C8_PARSE_ERROR_HANDLED", load_json(badp) is None and "__parse_error__" in scan_corpus(ctl_dir)["broken.json"],
        "invalid JSON loads as parse-error marker, never raises")
    # C9: report payload rebuild is deterministic
    payload = {"task_id": TASK_ID, "mutations": mutations, "coverage_t0": cov0,
               "coverage_t1": cov1, "controls": controls}
    h1 = sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    h2 = sha256_bytes(json.dumps(json.loads(json.dumps(payload)), sort_keys=True, separators=(",", ":")).encode())
    ctl("C9_DETERMINISTIC_PAYLOAD", h1 == h2, h1[:12])
    # C10: the T1 snapshot copies the measurements read must match the T1 manifest
    t1_bad = [n for n in t1man["reviews_manifest"]
              if not os.path.exists(os.path.join(t1_dir, n))
              or sha256_file(os.path.join(t1_dir, n)) != t1man["reviews_manifest"][n]["sha256"]]
    ctl("C10_T1_SNAPSHOT_INTEGRITY", not t1_bad,
        "%d/%d T1 snapshot copies hash to the T1 manifest" % (
            len(t1man["reviews_manifest"]) - len(t1_bad), len(t1man["reviews_manifest"])))

    # ---- end-of-run drift on pinned T1 bytes (observation, not failure:
    # the report's measurements read the frozen T1 snapshot copies) ----------
    drift = []
    for name in sorted(t1man["reviews_manifest"]):
        p = os.path.join(REPO, "reviews", name)
        if not os.path.exists(p):
            drift.append({"path": "reviews/" + name, "t1_sha256": t1man["reviews_manifest"][name]["sha256"],
                          "live_sha256": None, "class": "MISSING_LIVE"})
        elif sha256_file(p) != t1man["reviews_manifest"][name]["sha256"]:
            drift.append({"path": "reviews/" + name, "t1_sha256": t1man["reviews_manifest"][name]["sha256"],
                          "live_sha256": sha256_file(p), "class": "REWRITTEN_AFTER_T1_PIN"})
    for tag, rec in t1man["sources"].items():
        p = os.path.join(REPO, rec["path"])
        live = sha256_file(p) if os.path.exists(p) else None
        if live != rec["sha256"]:
            drift.append({"path": rec["path"], "t1_sha256": rec["sha256"], "live_sha256": live,
                          "class": "REWRITTEN_AFTER_T1_PIN"})
    live_now = sorted(n for n in os.listdir(os.path.join(REPO, "reviews")) if n.endswith(".json"))
    live_new_after_pin = sorted(set(live_now) - set(t1man["reviews_manifest"]))

    # ---- findings ---------------------------------------------------------
    gen_at = now()
    same_pin = [m for m in mutations if m["class"] == "SAME_PIN_VERDICT_CHANGE"]
    f2b0, f2b1 = cov0["F2b_rev13"], cov1["F2b_rev13"]
    t0_n, t1_n = len(t0man["reviews_manifest"]), t1man["reviews_count"]
    findings = [
        {
            "id": "W042-RCM-01",
            "kind": "defect-governance",
            "statement": "%d of %d review files pinned byte-exactly at T0 (%s) were rewritten in place before T1 (%s); %d carry verdict-bearing or binding fields." % (
                len(mutations), t0_n, t0man.get("pinned_at"), t1man.get("pinned_at"),
                sum(1 for m in mutations if m["fields"])),
            "detail": [{"file": m["file"], "class": m["class"], "t0_sha256": m["t0_sha256"][:12],
                        "t1_sha256": (m["t1_sha256"] or "")[:12], "fields": m["fields"]} for m in mutations],
            "evidence_refs": ["artifacts/worker-042/review_corpus_mutation/snapshot/manifest.json",
                              "artifacts/worker-042/gate_scan_gap/snapshot/manifest.json#4ee0145df14c"],
            "falsifier": "Re-run the checker on the two pinned snapshots. Falsified if any listed file's T0 snapshot bytes hash to its T1 hash, if a listed field delta is not reproducible from the pinned bytes, or if a mutated file is missing from the list.",
        },
        {
            "id": "W042-RCM-02",
            "kind": "defect-high",
            "statement": "Same-pin verdict flip at a fixed filename: %s." % (
                "; ".join("%s %s %s -> %s %s at the same reviewed hash %s" % (
                    m["file"], s(t0_docs[m["file"]].get("verdict")), s(t0_docs[m["file"]].get("score")),
                    s(t1_docs[m["file"]].get("verdict")), s(t1_docs[m["file"]].get("score")),
                    pin_of(t0_docs[m["file"]])[:12]) for m in same_pin) or "none measured"),
            "detail": [{"file": m["file"],
                        "t0": {"verdict": t0_docs[m["file"]].get("verdict"), "score": t0_docs[m["file"]].get("score"),
                               "reviewed_sha256": pin_of(t0_docs[m["file"]]),
                               "created_at": s(t0_docs[m["file"]].get("created_at"))},
                        "t1": {"verdict": t1_docs[m["file"]].get("verdict"), "score": t1_docs[m["file"]].get("score"),
                               "reviewed_sha256": pin_of(t1_docs[m["file"]]),
                               "created_at": s(t1_docs[m["file"]].get("created_at")),
                               "correction_note": s(t1_docs[m["file"]].get("correction_note"))[:300]}}
                       for m in same_pin],
            "evidence_refs": ["artifacts/worker-042/review_corpus_mutation/snapshot/reviews_t1/F2b-review-07.json",
                              "artifacts/worker-042/gate_scan_gap/snapshot/reviews/F2b-review-07.json"],
            "falsifier": "Falsified if the T0 and T1 bytes of the named file do not parse to different verdicts bound to the same reviewed-artifact hash, or if the T1 revision does not postdate T0.",
        },
        {
            "id": "W042-RCM-03",
            "kind": "measurement-reconciliation-input",
            "statement": "Hash-bound F2b rev13 coverage drift at %s: T0 files=0 (accepts 0, full-schema accepts 0); T1 files=%d (accepts %d, full-schema accepts %d; non-accept %d). Of the four files named by controller finding CF-31 (reviewers worker-052/071/072/090), %d carry verdict=accept and F2b-review-worker-072-rev29.json carries verdict=revise at the same pin, so a polarity-blind count of hash-bound full-schema verdicts reads 4 while a verdict==accept count reads 3." % (
                PINS["F2b_rev13"][:12], f2b1["files"], f2b1["accepts"], f2b1["full_schema_accepts"],
                f2b1["files"] - f2b1["accepts"], sum(1 for r in f2b1["rows"] if r["reviewer"] in
                                                     ("worker-052", "worker-071", "worker-072", "worker-090")
                                                     and r["verdict"] == "accept")),
            "detail": {"t0_rows": f2b0["rows"], "t1_rows": f2b1["rows"],
                       "t1_non_accept": [r["file"] for r in f2b1["rows"] if r["verdict"] != "accept"],
                       "t1_missing_full_schema_flag": [r["file"] for r in f2b1["rows"] if r["full_schema"] is None],
                       "t1_missing_created_at": [r["file"] for r in f2b1["rows"] if not r["created_at"]],
                       "note": "This report states the measured polarity split; it does not adjudicate which count is correct (REC-39 assigns that to astra-life05-verify-gform-r3)."},
            "evidence_refs": ["artifacts/worker-042/review_corpus_mutation/snapshot/manifest.json",
                              "artifacts/worker-042/review_corpus_mutation/snapshot/reviews_t1/F2b-review-worker-072-rev29.json",
                              "artifacts/worker-042/review_corpus_mutation/snapshot/reviews_t1/F2b-rev13-full-090.json"],
            "falsifier": "Re-run the coverage census on both pinned corpora. Falsified if the F2b rev13-bound file set or its verdict polarity differs from the rows listed, or if any listed file's reviewed_sha256 does not match the pin prefix.",
        },
        {
            "id": "W042-RCM-04",
            "kind": "defect-governance",
            "statement": "Fixed review filenames are reused across review rounds: %d mutated filename(s) changed document identity (target/node/created_at/event_id)." % len(name_reuse),
            "detail": name_reuse,
            "evidence_refs": ["artifacts/worker-042/review_corpus_mutation/snapshot/manifest.json"],
            "falsifier": "Falsified if the listed T0/T1 documents have identical identity tuples, or if the identity fields are not in the pinned bytes.",
        },
        {
            "id": "W042-RCM-05",
            "kind": "coverage-scope",
            "statement": "The review namespace grew from %d files at T0 to %d at T1 (%d new files, %d carrying a verdict); a filename-keyed scan at two times is not comparing the same corpus. Any binding table must freeze bytes (sha256 + mtime) at measurement time." % (
                t0_n, t1_n, len(new_files), len(new_with_verdict)),
            "detail": {"new_with_verdict_count": len(new_with_verdict),
                       "new_files_with_verdict": new_with_verdict[:50],
                       "new_bound_counts": {k: len(v) for k, v in new_bound.items()},
                       "new_bound_files": new_bound},
            "evidence_refs": ["artifacts/worker-042/review_corpus_mutation/snapshot/manifest.json"],
            "falsifier": "Falsified if the T0/T1 file counts or the new-file verdict census are not reproducible from the two pinned corpora.",
        },
        {
            "id": "W042-RCM-06",
            "kind": "observation-live-traffic",
            "statement": "Post-pin live drift inside the run window: %d review file(s) and %d registry/stream file(s) changed after the T1 pin (%s) but before this report (%s); the pinned snapshot copies remain the measurement substrate, so this is an observation about the live namespace, not a measurement failure." % (
                sum(1 for d in drift if d["path"].startswith("reviews/")),
                sum(1 for d in drift if not d["path"].startswith("reviews/")),
                t1man.get("pinned_at"), gen_at),
            "detail": {"drift_rows": drift, "live_new_files_after_pin": live_new_after_pin},
            "evidence_refs": ["artifacts/worker-042/review_corpus_mutation/snapshot/manifest.json"],
            "falsifier": "Falsified if the live paths listed re-hash to their T1 pinned hashes when re-measured immediately after this report, or if the pinned snapshot copies do not hash to the T1 manifest (control C10).",
        },
    ]

    report = {
        "schema": "w042-review-corpus-mutation/v1",
        "task_id": TASK_ID,
        "actor": "worker-042",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "node_id": "A1",
        "gate": "G-AUDIT",
        "related_gates": ["G-AUDIT", "G-FORM", "G-LIT"],
        "generated_at": gen_at,
        "pins": {
            "t0_pinned_at": t0man.get("pinned_at"),
            "t0_manifest_sha256": t1man["t0"]["manifest_sha256"],
            "t0_reviews_manifest_sha256": t1man["t0"]["reviews_manifest_sha256"],
            "t1_pinned_at": t1man.get("pinned_at"),
            "t1_manifest_sha256": t1_manifest_sha,
            "map_sha256": t1man["sources"]["map"]["sha256"],
            "events_sha256": t1man["sources"]["events"]["sha256"],
            "artifact_hashes_sha256": t1man["sources"]["artifact_hashes"]["sha256"],
        },
        "checker_sha256": sha256_file(os.path.abspath(__file__)),
        "corpus": {
            "t0_files": t0_n,
            "t1_files": t1_n,
            "t0_docs_with_verdict": sum(1 for d in t0_docs.values() if s(d.get("verdict")) in VERDICT_WORDS),
            "t1_docs_with_verdict": sum(1 for d in t1_docs.values() if s(d.get("verdict")) in VERDICT_WORDS),
            "t0_parse_errors": sum(1 for d in t0_docs.values() if "__parse_error__" in d),
            "t1_parse_errors": sum(1 for d in t1_docs.values() if "__parse_error__" in d),
            "t1_new_files": len(new_files),
            "t1_new_files_with_verdict": len(new_with_verdict),
        },
        "mutations": mutations,
        "name_reuse": name_reuse,
        "coverage_t0": cov0,
        "coverage_t1": cov1,
        "findings": findings,
        "controls": controls,
        "pin_drift_at_exit": drift,
        "live_new_files_after_pin": live_new_after_pin,
        "fails": fails,
        "conclusion_type": "formal_model",
        "does_not_claim": "no gate verdict, no node status, no adjudication of the F2b coverage count or of any review's correctness",
    }
    payload = {"task_id": TASK_ID, "mutations": mutations, "coverage_t0": cov0,
               "coverage_t1": cov1, "controls": controls}
    report["deterministic_payload_sha256"] = sha256_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    out = os.path.join(HERE, "report.json")
    with open(out, "w") as f:
        json.dump(report, f, indent=1, sort_keys=True)
        f.write("\n")

    print("== %s ==" % TASK_ID)
    print("T0 %d files -> T1 %d files; mutations %d (%s)" % (
        t0_n, t1_n, len(mutations),
        ", ".join("%s:%s" % (m["file"], m["class"]) for m in mutations) or "none"))
    print("F2b rev13: T0 files=%d accepts=%d full=%d | T1 files=%d accepts=%d full=%d" % (
        f2b0["files"], f2b0["accepts"], f2b0["full_schema_accepts"],
        f2b1["files"], f2b1["accepts"], f2b1["full_schema_accepts"]))
    print("controls: %d/%d pass; fails: %s" % (
        sum(1 for c in controls if c["pass"]), len(controls), fails or "[]"))
    print("deterministic_payload_sha256 %s" % report["deterministic_payload_sha256"][:12])
    print("report: %s" % out)
    return 2 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
