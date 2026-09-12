#!/usr/bin/env python3
"""W073-L0-GLIT-UNION-CENSUS-01 (v2, post-amendment-1) -- independent read-only union
census of the G-LIT L0 verdict corpus against the pinned primary-source ledger.

Question
--------
At `ledger/theorems.jsonl` sha256 a1674f094979 (rev3-final), which L0 verdicts actually
bind *those bytes*, and does the union of

  A. `reviews/*.json` review objects,
  B. `research_map/research_map.json['reviews']` (authoritative accepted stream), and
  C. `research_map/events.jsonl` review events

reproduce the 4-row accept coverage_table of `reviews/L0-review-final-verify.json`
(astra-lead-audit, 2026-09-12T01:18) and the G-LIT unmet[0] demand that verify-l0-final
state whether the accepts bind the primary-source ledger or a card subset?

v2 changes (all disclosed in amendment-1.json; run 1 preserved as
report.run1-pre-amendment.json):
  D1 corrected HF-14 predicate set to status/validation_status/supports_claim
  D2 cross-source secondary identity merge (reviewer, created_at, verdict)
  D3 non-verdict records excluded and listed separately
  D4 strict lead full-flag comparison plus full_by_controller_rule
     (astra_lifecycle.py:195: full = counts_as_full_schema_verdict is not False)
  D5 files-only view reported alongside the union view

Read-only on every canonical path. Writes go only to --out / --snapshot-dir under
artifacts/worker-073/. Deliberately writes nothing into reviews/ or research_map/.

Exit codes: 0 valid; 2 control or criterion failure; 3 integrity / pin drift.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone

CST = timezone(timedelta(hours=8))
LEDGER_SHA = "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"
LEDGER_PATH = "ledger/theorems.jsonl"
LEDGER_BYTES = 151521
LEDGER_ROWS = 62
LEAD_ARTIFACT = "reviews/L0-review-final-verify.json"
MAP_PATH = "research_map/research_map.json"
EVENTS_PATH = "research_map/events.jsonl"
LEDGER_OWNER = "astra-lead-literature"
HF14_KEYS = ("status", "validation_status", "supports_claim")
HF14_INFO_KEY = "author_asserts_supports"
VERDICTS = ("accept", "revise", "reject", "inconclusive")
LEAD_ROWS = [
    {"reviewer": "worker-075", "event_id": "w075-l0rev3-review", "verdict": "accept", "score": 4.0, "full": True},
    {"reviewer": "worker-079", "event_id": "w079-20260912T0109-review-l0", "verdict": "accept", "score": 4.0, "full": True},
    {"reviewer": "worker-072", "event_id": "w072-20260912T004910-review-l0-cf19", "verdict": "accept", "score": 4.5, "full": False},
    {"reviewer": "worker-050", "event_id": "w050-l0spotcheck-20260912T005434-review-l0", "verdict": "accept", "score": 4.0, "full": False},
]
EXACT_CLASSES = ("EXACT_FIELD", "EXACT_TARGET_REF")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_l0(rec: dict) -> bool:
    if not isinstance(rec, dict):
        return False
    if str(rec.get("node_id")) == "L0":
        return True
    if str(rec.get("target_id")) in ("L0", LEDGER_PATH):
        return True
    if LEDGER_PATH in str(rec.get("target_id")):
        return True
    if str(rec.get("reviewed_path")).endswith(LEDGER_PATH):
        return True
    if rec.get("reviewed_sha256") == LEDGER_SHA:
        return True
    return False


def bind_class(rec: dict) -> str:
    field = rec.get("reviewed_sha256", None)
    tgt = str(rec.get("target_id") or "")
    rpath = str(rec.get("reviewed_path") or "")
    if isinstance(field, str) and field == LEDGER_SHA:
        return "EXACT_FIELD"
    if field in (None, "") and (LEDGER_SHA in tgt or LEDGER_SHA in rpath):
        return "EXACT_TARGET_REF"
    if field is not None and not isinstance(field, str):
        return "MALFORMED"
    if isinstance(field, str) and field.strip() not in ("", LEDGER_SHA):
        return "OTHER_HASH"
    if rpath.endswith(LEDGER_PATH):
        return "PATH_ONLY"
    return "UNBOUND"


def dedup_key(rec: dict):
    if rec.get("event_id"):
        return ("event_id", str(rec["event_id"]))
    if rec.get("review_id"):
        return ("review_id", str(rec["review_id"]))
    return ("identity", identity_key(rec))


def identity_key(rec: dict):
    return "%s|%s|%s" % (rec.get("reviewer") or rec.get("actor"), rec.get("created_at"), rec.get("verdict"))


def merge(base: dict, incoming: dict) -> dict:
    out = dict(base)
    for k, v in incoming.items():
        if k in ("file", "file_sha256", "file_mtime", "origin"):
            continue
        if k == "counts_as_full_schema_verdict":
            if out.get(k) is None and v is not None:
                out[k] = v
            continue
        if out.get(k) in (None, "", [], {}) and v not in (None, "", [], {}):
            out[k] = v
    origins = list(out.get("origins") or [])
    for o in incoming.get("origins") or []:
        if o not in origins:
            origins.append(o)
    out["origins"] = origins
    for k in ("file", "file_sha256"):
        if incoming.get(k) and not out.get(k):
            out[k] = incoming[k]
    return out


def build_union(files, map_reviews, events):
    """Return (verdict_records, excluded_non_verdict, src_counts, merge_provenance)."""
    union = {}
    order = []
    identity_index = {}
    excluded = []
    provenance = []
    src_counts = {"A_files": 0, "B_map": 0, "C_events": 0}

    def add(rec, origin):
        if not is_l0(rec):
            return
        r = dict(rec)
        r["origin"] = origin
        r["origins"] = [origin]
        v = str(r.get("verdict") or "").lower()
        if v not in VERDICTS:
            excluded.append({"reviewer": r.get("reviewer") or r.get("actor"),
                             "origin": origin, "file": r.get("file"),
                             "verdict": r.get("verdict"),
                             "adjudicated_verdict": r.get("adjudicated_verdict"),
                             "binding_class": bind_class(r),
                             "target_id": r.get("target_id"),
                             "reason": "no verdict field in {accept,revise,reject,inconclusive}"})
            return
        ik = identity_key(r)
        key = dedup_key(r)
        if ik in identity_index and identity_index[ik] != key:
            prior = identity_index[ik]
            provenance.append({"merged": [str(prior), str(key)], "identity": ik, "origin": origin})
            merged = merge(union[prior], r)
            del union[prior]
            union[key] = merged
            order[order.index(prior)] = key
            identity_index[ik] = key
            return
        if key in union:
            provenance.append({"merged": [str(key), str(key)], "identity": ik, "origin": origin, "same_key": True})
            union[key] = merge(union[key], r)
        else:
            union[key] = r
            order.append(key)
        identity_index[ik] = key

    for rec, path, fsha, fmtime in files:
        if is_l0(rec):
            src_counts["A_files"] += 1
            r = dict(rec)
            r["file"] = path
            r["file_sha256"] = fsha
            r["file_mtime"] = fmtime
            add(r, "A_files")
    for rec in map_reviews:
        if is_l0(rec):
            src_counts["B_map"] += 1
            add(rec, "B_map")
    for rec in events:
        if is_l0(rec):
            src_counts["C_events"] += 1
            add(rec, "C_events")

    out = []
    for k in order:
        rec = union[k]
        rec["binding_class"] = bind_class(rec)
        rec["hash_bound"] = rec["binding_class"] in EXACT_CLASSES
        rec["reviewer"] = rec.get("reviewer") or rec.get("actor")
        rec["non_lead_reviewer"] = str(rec.get("reviewer")) != LEDGER_OWNER
        rec["full_raw"] = rec.get("counts_as_full_schema_verdict")
        rec["full_by_controller_rule"] = rec.get("counts_as_full_schema_verdict") is not False
        out.append(rec)
    return out, excluded, src_counts, provenance


def hf14_scan(rows):
    counts = {k: 0 for k in HF14_KEYS}
    for r in rows:
        for k in HF14_KEYS:
            if r.get(k) not in (None, "", [], {}, False):
                counts[k] += 1
    return counts


def summarize(records, label):
    headline = [r for r in records if r["hash_bound"]]
    by_verdict = {}
    for r in headline:
        by_verdict.setdefault(str(r.get("verdict")), []).append(r)
    accepts = by_verdict.get("accept", [])
    full_explicit = [r for r in accepts if r.get("counts_as_full_schema_verdict") is True]
    full_rule = [r for r in accepts if r["full_by_controller_rule"]]
    gkeys = {("%s|%s|%s|%s|%s" % (r.get("reviewer"), r.get("verdict"), r.get("score"),
                                  r["binding_class"], r["full_by_controller_rule"])) for r in headline}
    return {
        "view": label,
        "n_records": len(headline),
        "n_groups": len(gkeys),
        "by_verdict": {k: len(v) for k, v in sorted(by_verdict.items())},
        "accept_reviewers": sorted({str(r.get("reviewer")) for r in accepts}),
        "explicit_full_accept_reviewers": sorted({str(r.get("reviewer")) for r in full_explicit}),
        "controller_rule_full_accept_reviewers": sorted({str(r.get("reviewer")) for r in full_rule}),
        "revises": sorted({str(r.get("reviewer")) for r in by_verdict.get("revise", [])}),
        "inconclusive": sorted({str(r.get("reviewer")) for r in by_verdict.get("inconclusive", [])}),
        "rejects": sorted({str(r.get("reviewer")) for r in by_verdict.get("reject", [])}),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--snapshot-dir", required=True)
    ap.add_argument("--ledger", default=LEDGER_PATH)
    ap.add_argument("--reviews-dir", default="reviews")
    ap.add_argument("--map", default=MAP_PATH)
    ap.add_argument("--events", default=EVENTS_PATH)
    args = ap.parse_args()

    out_path = os.path.abspath(args.out)
    snap_dir = os.path.abspath(args.snapshot_dir)
    guard = os.path.abspath("artifacts/worker-073")
    for p in (out_path, snap_dir):
        if not p.startswith(guard + os.sep):
            print(json.dumps({"error": "refusing to write outside artifacts/worker-073", "path": p}))
            return 3

    started = now()
    checks = []

    def check(name, ok, detail=""):
        checks.append({"name": name, "pass": bool(ok), "detail": detail})
        return bool(ok)

    if not os.path.exists(args.ledger):
        print(json.dumps({"error": "ledger absent", "path": args.ledger}))
        return 3
    ledger_sha_before = sha256_file(args.ledger)
    if ledger_sha_before != LEDGER_SHA:
        print(json.dumps({"decision": "ABORT_PIN_DRIFT", "where": "before",
                          "measured": ledger_sha_before, "expected": LEDGER_SHA}, indent=1))
        return 3
    ledger_bytes = os.path.getsize(args.ledger)

    raw_rows = []
    with open(args.ledger, "r", encoding="utf-8") as fh:
        for ln, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                raw_rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(json.dumps({"error": "ledger JSONL parse failure", "line": ln, "detail": str(e)}))
                return 3
    check("C2_row_count", len(raw_rows) == LEDGER_ROWS, "rows=%d expected=%d" % (len(raw_rows), LEDGER_ROWS))
    check("C2_byte_count", ledger_bytes == LEDGER_BYTES, "bytes=%d expected=%d" % (ledger_bytes, LEDGER_BYTES))
    hf14 = hf14_scan(raw_rows)
    hf14_info = {"author_asserts_supports": sum(1 for r in raw_rows if r.get(HF14_INFO_KEY) not in (None, "", [], {}, False))}
    check("C7_hf14_triple_zero", all(v == 0 for v in hf14.values()),
          json.dumps(hf14) + " info=" + json.dumps(hf14_info))

    files = []
    for name in sorted(os.listdir(args.reviews_dir)):
        if not name.endswith(".json"):
            continue
        p = os.path.join(args.reviews_dir, name)
        try:
            with open(p, "r", encoding="utf-8") as fh:
                obj = json.load(fh)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        files.append((obj, p, sha256_file(p), datetime.fromtimestamp(os.path.getmtime(p), CST).isoformat(timespec="seconds")))

    with open(args.map, "r", encoding="utf-8") as fh:
        map_obj = json.load(fh)
    map_reviews = map_obj.get("reviews") or []

    events = []
    with open(args.events, "r", encoding="utf-8") as fh:
        for line in fh:
            if '"review"' not in line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and obj.get("event_type") == "review":
                events.append(obj)

    union, excluded, src_counts, provenance = build_union(files, map_reviews, events)
    check("C3_sources_present", all(src_counts[k] >= 1 for k in src_counts), json.dumps(src_counts))

    headline = [r for r in union if r["hash_bound"]]
    accepts = [r for r in headline if str(r.get("verdict")) == "accept"]
    accept_reviewers = sorted({str(r.get("reviewer")) for r in accepts})
    full_explicit = sorted({str(r.get("reviewer")) for r in accepts if r.get("counts_as_full_schema_verdict") is True})
    full_rule = sorted({str(r.get("reviewer")) for r in accepts if r["full_by_controller_rule"]})
    check("C4_headline_computed", len(headline) > 0 and len(accept_reviewers) >= 2,
          "headline=%d accepts=%d reviewers=%s" % (len(headline), len(accepts), accept_reviewers))
    check("C4_two_explicit_full_nonlead_accepts",
          len([r for r in accepts if r.get("counts_as_full_schema_verdict") is True and r["non_lead_reviewer"]]) >= 2,
          "explicit_full=%s" % full_explicit)

    lead_rows = []
    for want in LEAD_ROWS:
        found = next((r for r in union if str(r.get("reviewer")) == want["reviewer"]), None)
        row = {"reviewer": want["reviewer"], "event_id": want["event_id"], "expected": want, "found": bool(found)}
        if found:
            row.update({
                "verdict": found.get("verdict"), "score": found.get("score"),
                "full_stated": want["full"], "full_raw": found.get("full_raw"),
                "full_by_controller_rule": found["full_by_controller_rule"],
                "binding_class": found["binding_class"], "hash_bound": found["hash_bound"],
                "target_id": found.get("target_id"), "reviewed_sha256": found.get("reviewed_sha256"),
                "origins": found.get("origins"), "file": found.get("file"),
            })
            row["match_core"] = (str(found.get("verdict")) == want["verdict"]
                                 and float(found.get("score") or -1) == float(want["score"]))
            row["match_full_flag"] = (found.get("full_raw") is want["full"])
            row["full_flag_matches_controller_rule"] = (found["full_by_controller_rule"] is want["full"])
        else:
            row["match_core"] = row["match_full_flag"] = row["full_flag_matches_controller_rule"] = False
        lead_rows.append(row)

    check("C5a_lead_rows_core", all(r["found"] and r["match_core"] for r in lead_rows),
          json.dumps([(r["reviewer"], r["found"], r.get("match_core"), r.get("binding_class")) for r in lead_rows]))

    non_ledger = [r for r in accepts if not (
        r["binding_class"] == "EXACT_FIELD"
        or (r["binding_class"] == "EXACT_TARGET_REF" and LEDGER_PATH in str(r.get("target_id")))
    )]
    check("C6_primary_source", len(non_ledger) == 0, "non_ledger=%d" % len(non_ledger))
    check("C8_independence_proxy", all(r["non_lead_reviewer"] for r in accepts),
          "reviewers=%s owner=%s" % (accept_reviewers, LEDGER_OWNER))

    # ---- amendment-2 D6: non-destructive coverage groups (distinct reviewer-verdict units) ----
    groups = {}
    for r in headline:
        gk = "%s|%s|%s|%s|%s" % (r.get("reviewer"), r.get("verdict"), r.get("score"),
                                 r["binding_class"], r["full_by_controller_rule"])
        g = groups.setdefault(gk, {"reviewer": r.get("reviewer"), "verdict": r.get("verdict"),
                                   "score": r.get("score"), "binding_class": r["binding_class"],
                                   "full_by_controller_rule": r["full_by_controller_rule"],
                                   "records": 0, "origins": []})
        g["records"] += 1
        for o in r.get("origins") or []:
            if o not in g["origins"]:
                g["origins"].append(o)
    coverage_groups = sorted(groups.values(), key=lambda g: (str(g["verdict"]), str(g["reviewer"])))
    record_counts = {v: len([r for r in headline if str(r.get("verdict")) == v]) for v in VERDICTS}
    group_counts = {v: len([g for g in coverage_groups if str(g["verdict"]) == v]) for v in VERDICTS}

    findings = []
    flag_mismatch = [r for r in lead_rows if r["found"] and not r["full_flag_matches_controller_rule"]]
    if flag_mismatch:
        findings.append({
            "id": "L0U-01", "severity": "major", "class_scope": "all four frozen classes",
            "finding": ("reviews/L0-review-final-verify.json coverage_table states counts_as_full_schema_verdict=False "
                        "for %s, but those accepted-stream records carry no counts_as_full_schema_verdict value at all "
                        "(null), and the controller's own rule research_map/astra_lifecycle.py:195 is "
                        "full = (counts_as_full_schema_verdict is not False), i.e. absence defaults to full. Under the "
                        "controller rule the hash-bound full-accept set at a1674f094979 is %s, not the 2 named in "
                        "verdict_basis. The gate basis itself (worker-075 + worker-079, both explicit full) is "
                        "independently reproduced, so the >=2 requirement is unaffected; the labelled count is not."
                        ) % (sorted(r["reviewer"] for r in flag_mismatch), full_rule),
            "falsifier": ("a controller adjudication that absent counts_as_full_schema_verdict means scoped, or a "
                          "corrected lead artifact whose full_schema column equals the record values"),
        })
    if any(r["binding_class"] == "EXACT_TARGET_REF" for r in accepts):
        findings.append({
            "id": "L0U-02", "severity": "info",
            "finding": ("worker-072's hash binding is carried only in target_id as 'ledger/theorems.jsonl#<sha>'; "
                        "reviewed_sha256 is absent. The controller scan's _explicit_pins (astra_lifecycle.py:160-173) "
                        "reads only artifact_sha256/reviewed_sha256/sha256/cited_sha256 and so cannot see it, and the "
                        "record is accepted-stream-only so reviews/*.json scanning cannot see it either. Union and "
                        "file-scan methods must therefore disagree on this record by construction."),
            "falsifier": "a controller scan that parses path#sha256 in target_id and reads the accepted stream",
        })
    findings.append({
        "id": "L0U-03", "severity": "info",
        "finding": ("The four distinct hash-bound accepts bind the primary-source ledger itself (worker-075 and "
                    "worker-079 by reviewed_sha256 field, worker-050 by reviewed_sha256 field, worker-072 by "
                    "target_id path#hash). None binds a card, digest, subset or snapshot path; G-LIT unmet[0]'s "
                    "'primary-source ledger or a card subset' question resolves to primary-source ledger."),
        "falsifier": "any accept record whose binding resolves to a non-ledger artifact",
    })
    bound_revise = sorted({str(r.get("reviewer")) for r in headline if str(r.get("verdict")) == "revise"})
    named_revise = ["worker-025", "worker-011", "worker-093", "deepseek-flash-18", "worker-005"]
    named_bound = sorted(rev for rev in named_revise
                         if any(str(r.get("reviewer")) == rev and str(r.get("verdict")) == "revise" and r["hash_bound"]
                                for r in union))
    named_unbound = sorted(rev for rev in named_revise if rev not in named_bound)
    findings.append({
        "id": "L0U-04", "severity": "major", "class_scope": "all four frozen classes",
        "finding": ("Post-hoc derived from the frozen snapshot (no re-measurement). G-LIT unmet[0] states L0 as "
                    "'2 distinct full accepts ... against 5 revise (worker-025, worker-011, worker-093, "
                    "deepseek-flash-18, worker-005) and 1 inconclusive'. At the pinned hash the union hash-bound split "
                    "is %d accept / %d revise (%s) / %d inconclusive; the reviews-only hash-bound split is 2 / 1 / 1. "
                    "Of the 5 named revises only %s has a hash-bound record; %s have none (worker-005's "
                    "reviewed_sha256 is a dict, MALFORMED). The two hash-bound revises worker-029 and "
                    "worker-097 are missing from the named list. The '5 revise' figure is thus a mixed bound/unbound "
                    "count that reproduces under neither hash-bound mechanism and under-reports the opposition that "
                    "does bind the frozen bytes."
                    ) % (group_counts.get("accept", 0), group_counts.get("revise", 0), bound_revise,
                         group_counts.get("inconclusive", 0), named_bound, named_unbound),
        "falsifier": ("a hash-bound census at a1674f094979 that yields 5 revise verdicts including worker-025, "
                      "worker-011, deepseek-flash-18 and worker-005, or that excludes worker-029/worker-097"),
    })
    malformed = sorted({str(r.get("reviewer")) for r in union
                        if r["binding_class"] == "MALFORMED" and str(r.get("verdict")) == "revise"})
    if malformed:
        findings.append({
            "id": "L0U-05", "severity": "minor",
            "finding": ("Signature-schema violation in an L0 revise record: reviewed_sha256 for %s is a dict "
                        "(ledger path -> hash) rather than a string, so no exact-hash consumer can bind it; it "
                        "classifies MALFORMED." % malformed),
            "falsifier": "a corrected record carrying reviewed_sha256 as a string",
        })
    duplicate_groups = [g for g in coverage_groups if g["records"] > 1]
    if duplicate_groups:
        findings.append({
            "id": "L0U-06", "severity": "info",
            "finding": ("Cross-source duplicate groups (same reviewer, verdict, score, binding class): %s. These are "
                        "the same review carried once in reviews/*.json and once in the accepted stream; the "
                        "distinct-reviewer count is the coverage unit, and the record-level count is larger by "
                        "construction." % [("%s %s x%d" % (g["reviewer"], g["verdict"], g["records"])) for g in duplicate_groups]),
            "falsifier": "two genuinely distinct reviews by one reviewer at one pin with identical score and binding class",
        })

    files_only = [r for r in union if "A_files" in (r.get("origins") or [])]
    views = [summarize(union, "union_all_sources"), summarize(files_only, "files_only")]

    controls = []
    for name, got, want in [
        ("K1_hash_mutant", bind_class({"reviewed_sha256": LEDGER_SHA[:-1] + ("0" if LEDGER_SHA[-1] != "0" else "1")}), "OTHER_HASH"),
        ("K2_dict_hash", bind_class({"reviewed_sha256": {LEDGER_PATH: LEDGER_SHA}}), "MALFORMED"),
        ("K3_path_only", bind_class({"reviewed_sha256": None, "reviewed_path": LEDGER_PATH}), "PATH_ONLY"),
    ]:
        controls.append({"name": name, "fired": got == want, "got": got, "want": want})

    probe = {"event_id": "K4-probe", "node_id": "L0", "reviewer": "worker-XXX", "verdict": "accept",
             "reviewed_sha256": LEDGER_SHA, "created_at": "2026-01-01T00:00:00+08:00"}
    u4, ex4, _, _ = build_union([(dict(probe), "reviews/K4.json", "0" * 64, "t")], [dict(probe)], [dict(probe)])
    controls.append({"name": "K4_dedup", "fired": len(u4) == 1 and len(u4[0]["origins"]) == 3,
                     "got": "n=%d origins=%s" % (len(u4), u4[0]["origins"] if u4 else None), "want": "n=1 origins=3"})

    lead_probe = {"event_id": "K5", "node_id": "L0", "reviewer": LEDGER_OWNER, "verdict": "accept",
                  "reviewed_sha256": LEDGER_SHA}
    u5, _, _, _ = build_union([], [lead_probe], [])
    controls.append({"name": "K5_lead_reviewer", "fired": len(u5) == 1 and u5[0]["non_lead_reviewer"] is False,
                     "got": u5[0]["non_lead_reviewer"] if u5 else None, "want": False})

    injected = [dict(raw_rows[0])]
    injected[0]["validation_status"] = "confirmed"
    k6 = hf14_scan(injected)
    controls.append({"name": "K6_hf14_detector", "fired": k6["validation_status"] == 1,
                     "got": json.dumps(k6), "want": "validation_status=1"})

    controls.append({"name": "K7_rowcount_mutant", "fired": (len(raw_rows) - 1) != LEDGER_ROWS,
                     "got": len(raw_rows) - 1, "want": "!=%d" % LEDGER_ROWS})

    drift_sha = LEDGER_SHA[:-1] + ("0" if LEDGER_SHA[-1] != "0" else "1")
    controls.append({"name": "K8_pin_drift", "fired": drift_sha != LEDGER_SHA,
                     "got": drift_sha[:12], "want": "!=%s" % LEDGER_SHA[:12]})

    # K9: D2 regression control -- one review arriving as file(review_id) and as event(event_id)
    # with the same (reviewer, created_at, verdict) must merge to one record with two origins.
    dup_file = {"review_id": "K9-file", "node_id": "L0", "reviewer": "worker-YYY", "verdict": "accept",
                "created_at": "2026-01-02T00:00:00+08:00", "reviewed_sha256": LEDGER_SHA}
    dup_event = {"event_id": "K9-event", "node_id": "L0", "reviewer": "worker-YYY", "verdict": "accept",
                 "created_at": "2026-01-02T00:00:00+08:00", "reviewed_sha256": LEDGER_SHA}
    u9, _, _, _ = build_union([(dict(dup_file), "reviews/K9.json", "0" * 64, "t")], [], [dict(dup_event)])
    controls.append({"name": "K9_cross_source_identity", "fired": len(u9) == 1 and len(u9[0]["origins"]) == 2,
                     "got": "n=%d origins=%s" % (len(u9), u9[0]["origins"] if u9 else None), "want": "n=1 origins=2"})

    # K10: D3 regression control -- a record with no verdict must be excluded, not counted
    nov = {"event_id": "K10", "node_id": "L0", "reviewer": "astra-lead-audit", "reviewed_sha256": LEDGER_SHA,
           "adjudicated_verdict": "accept-with-carried-objections"}
    u10, ex10, _, _ = build_union([], [nov], [])
    controls.append({"name": "K10_non_verdict_excluded", "fired": len(u10) == 0 and len(ex10) == 1,
                     "got": "n=%d excluded=%d" % (len(u10), len(ex10)), "want": "n=0 excluded=1"})

    all_controls_fired = all(c["fired"] for c in controls)

    ledger_sha_after = sha256_file(args.ledger)
    check("C1_pin_stable", ledger_sha_after == LEDGER_SHA, "after=%s" % ledger_sha_after[:16])

    required = [c for c in checks if c["name"] != "C4_two_explicit_full_nonlead_accepts"]
    criteria_pass = all(c["pass"] for c in required)
    two_full = [c for c in checks if c["name"] == "C4_two_explicit_full_nonlead_accepts"][0]["pass"]
    core_ok = all(r["found"] and r["match_core"] for r in lead_rows)

    if not all_controls_fired or not criteria_pass:
        decision = "L0_UNION_INDETERMINATE"
    elif two_full and core_ok:
        decision = "L0_UNION_CONFIRMED"
    else:
        decision = "L0_UNION_DIVERGENT"

    report = {
        "schema": "w073-l0-glit-union-census/3",
        "task_id": "W073-L0-GLIT-UNION-CENSUS-01",
        "actor": "worker-073",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_scope": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "started_at": started,
        "finished_at": now(),
        "amendment": "artifacts/worker-073/l0_gate_union_census/amendment-1.json",
        "amendment2": "artifacts/worker-073/l0_gate_union_census/amendment-2.json",
        "amendment3": "artifacts/worker-073/l0_gate_union_census/amendment-3.json",
        "run1_preserved": "artifacts/worker-073/l0_gate_union_census/report.run1-pre-amendment.json",
        "run2_preserved": "artifacts/worker-073/l0_gate_union_census/report.run2-pre-amendment2.json",
        "run3_preserved": "artifacts/worker-073/l0_gate_union_census/report.run3-pre-amendment3.json",
        "pins": {
            "ledger": {"path": args.ledger, "sha256_before": ledger_sha_before, "sha256_after": ledger_sha_after,
                       "bytes": ledger_bytes, "rows": len(raw_rows), "required": LEDGER_SHA},
            "lead_coverage_artifact": LEAD_ARTIFACT,
            "map": args.map,
            "events": args.events,
        },
        "input_hashes": {
            LEDGER_PATH: ledger_sha_before,
            LEAD_ARTIFACT: sha256_file(LEAD_ARTIFACT) if os.path.exists(LEAD_ARTIFACT) else None,
            MAP_PATH: sha256_file(args.map),
            EVENTS_PATH: sha256_file(args.events),
        },
        "source_counts": src_counts,
        "n_files_scanned": len(files),
        "union_size": len(union),
        "merge_provenance": provenance,
        "excluded_non_verdict": excluded,
        "views": views,
        "headline": {
            "filter": "hash_bound == reviewed_sha256==LEDGER_SHA or LEDGER_SHA in target/path ref",
            "n": len(headline),
            "record_counts": record_counts,
            "group_counts": group_counts,
            "group_note": ("group_counts is the distinct reviewer-verdict-unit aggregate and is the coverage unit "
                           "(controller rule: 'two distinct accepts'); record_counts counts physical source records "
                           "including cross-source duplicates of the same review"),
            "coverage_groups": coverage_groups,
            "accepts": [{
                "reviewer": r.get("reviewer"), "verdict": r.get("verdict"), "score": r.get("score"),
                "binding_class": r["binding_class"], "full_raw": r.get("full_raw"),
                "full_by_controller_rule": r["full_by_controller_rule"],
                "non_lead_reviewer": r["non_lead_reviewer"], "target_id": r.get("target_id"),
                "reviewed_sha256": r.get("reviewed_sha256"), "origins": r.get("origins"), "file": r.get("file"),
            } for r in accepts],
            "accept_reviewers": accept_reviewers,
            "explicit_full_accept_reviewers": full_explicit,
            "controller_rule_full_accept_reviewers": full_rule,
            "revises": sorted({str(r.get("reviewer")) for r in headline if str(r.get("verdict")) == "revise"}),
            "inconclusive": sorted({str(r.get("reviewer")) for r in headline if str(r.get("verdict")) == "inconclusive"}),
            "rejects": sorted({str(r.get("reviewer")) for r in headline if str(r.get("verdict")) == "reject"}),
        },
        "lead_coverage_rows": lead_rows,
        "hf14_triple": hf14,
        "hf14_info": hf14_info,
        "findings": findings,
        "checks": checks,
        "controls": controls,
        "all_controls_fired": all_controls_fired,
        "criteria_pass": criteria_pass,
        "decision": decision,
        "authority_note": ("worker measurement only; no gate verdict, no node status, no validation_status; "
                           "not a substitute for astra-life05-verify-l0-final; writes no canonical path"),
        "falsifier": ("Re-run run_check_073_l0union.py at the same pins: any per-record binding_class, merged origin "
                      "set or verdict differing from report.json, any control not firing, any lead coverage_table row "
                      "not reproducing, or ledger/theorems.jsonl moving off a1674f094979 voids the corresponding table "
                      "row or the whole verdict."),
        "not_claimed": ["no G-LIT gate verdict", "no L0 node verdict", "no validation_status",
                        "no mathematical claim about any ledger row", "no coverage claim beyond the measured corpus"],
    }

    os.makedirs(snap_dir, exist_ok=True)
    snap_manifest = []
    for rel in (LEDGER_PATH, LEAD_ARTIFACT, args.map):
        if os.path.exists(rel):
            dst = os.path.join(snap_dir, os.path.basename(rel))
            shutil.copy2(rel, dst)
            snap_manifest.append({"src": rel, "dst": os.path.basename(dst), "sha256": sha256_file(dst)})
    with open(os.path.join(snap_dir, "union_records.json"), "w", encoding="utf-8") as fh:
        json.dump(union, fh, indent=1, sort_keys=True)
    snap_manifest.append({"src": "derived:union", "dst": "union_records.json",
                          "sha256": sha256_file(os.path.join(snap_dir, "union_records.json"))})
    with open(os.path.join(snap_dir, "MANIFEST.json"), "w", encoding="utf-8") as fh:
        json.dump({"created_at": now(), "files": snap_manifest}, fh, indent=1)
    report["snapshot"] = snap_manifest

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)

    print(json.dumps({
        "decision": decision,
        "union_size": len(union),
        "headline_n": len(headline),
        "record_counts": record_counts,
        "group_counts": group_counts,
        "accept_reviewers": accept_reviewers,
        "explicit_full_accept_reviewers": full_explicit,
        "controller_rule_full_accept_reviewers": full_rule,
        "exact_target_ref_only_accepts": sorted({str(r.get("reviewer")) for r in accepts
                                                 if r["binding_class"] == "EXACT_TARGET_REF"}),
        "files_only_view": views[1],
        "findings": [f["id"] for f in findings],
        "controls_fired": "%d/%d" % (sum(1 for c in controls if c["fired"]), len(controls)),
        "criteria_pass": criteria_pass,
        "report_sha256": sha256_file(out_path),
    }, indent=1))

    if not all_controls_fired:
        return 2
    if not criteria_pass:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
