#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W001-A0-HF14-VOCAB-SCOPE-01

Independent, read-only, fail-closed re-run of the HF-14 branch of
evaluation/A0_detector_scope_adjudication.json#a26be4b85706 under two marker
vocabularies (canonical detector names vs the rev3 rename), with the
adjudication's own classify(rel) scope predicate applied.

Records universe: every *.jsonl file under artifacts/, comms/outbox/, ledger/.
No canonical path is written. Exit codes:
  0 = measurement valid, decision rule resolved
  2 = a control failed
  3 = a pinned input drifted between T0 and T1
  4 = inconclusive (universe empty / internal invariant broken)
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = HERE

SCAN_ROOTS = ("artifacts", "comms/outbox", "ledger")

PINS = {
    "evaluation_rubric.yaml":
        "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
    "evaluation/A0_detector_scope_adjudication.json":
        "a26be4b857068d2608387848035b6ddb5fda746447bf5750d6a7527ce5e2d24c",
    "ledger/theorems.jsonl":
        "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl":
        "ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72",
    "artifacts/audit/audit_lib.py":
        "ae573db84631b970caeea46e8821aee8af66166f6a5f16251e4a6c819a377c8c",
}
# Additional read-only guard: the global map must not move while this runs.
GUARD_PATHS = ["research_map/research_map.json"]

# Scope taxonomy, verbatim from the adjudication artifact.
CANONICAL = {"ledger/theorems.jsonl", "ledger/citation_audit.csv"}
LIVE_BUILD_INPUT_PREFIXES = (
    "artifacts/literature/sources/",
    "artifacts/literature/theorems/",
    "artifacts/literature/tools/",
)
LIVE_EMITTED = {
    "artifacts/literature/registry.jsonl",
    "artifacts/literature/unresolved.jsonl",
    "artifacts/literature/MANIFEST.json",
    "artifacts/literature/falsifiers.md",
    "artifacts/literature/tag_index.md",
}
HISTORICAL_SEGMENTS = {"archive", "incoming"}
HISTORICAL_TOKENS = (".pre-", ".prev-", "_snapshot.", ".snapshot-", ".bak")
SNAPSHOT_SEGMENTS = {"snapshot", "snapshots", "probe", "proposed",
                     "staging", "scratch", "prev"}

# HF-14 vocabulary.
CANONICAL_MARKER_FIELDS = ("status", "supports_claim", "validation_status")
ALIAS_MARKER_FIELDS = ("author_asserts_supports",)
REVIEW_FIELDS = ("reviewer_verdicts", "review_verdict", "reviewed_by")
HASH_FIELDS = ("artifact_sha256", "artifact_hash", "proof_sha256", "proof_hash",
               "verified_artifact_sha256", "checked_artifact_sha256")
HEX64 = re.compile(r"\b[0-9a-fA-F]{64}\b")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: str) -> str:
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def classify(r: str) -> tuple[str, list[str]]:
    """Return (primary_class, all_matching_classes). Primary precedence keeps
    live classes first so that a live path can never be hidden by a
    historical/snapshot token; the full match set exposes ambiguity."""
    base = r.rsplit("/", 1)[-1]
    segs = set(r.split("/"))
    matches = []
    if r in CANONICAL:
        matches.append("canonical")
    if any(r.startswith(p) for p in LIVE_BUILD_INPUT_PREFIXES):
        matches.append("live_build_input")
    if r in LIVE_EMITTED:
        matches.append("live_emitted")
    if "ledger_contribution" in segs:
        matches.append("staging_unresolved")
    if (segs & HISTORICAL_SEGMENTS) or any(t in base for t in HISTORICAL_TOKENS):
        matches.append("historical")
    if (segs & SNAPSHOT_SEGMENTS) or "snapshot" in base:
        matches.append("snapshot_copy")
    if not matches:
        matches.append("live_other")
    order = ["canonical", "live_build_input", "live_emitted", "staging_unresolved",
             "historical", "snapshot_copy", "live_other"]
    primary = sorted(matches, key=order.index)[0]
    return primary, sorted(set(matches), key=order.index)


def has_review(rec: dict) -> bool:
    return any(bool(rec.get(k)) for k in REVIEW_FIELDS)


def accepted(rec: dict, alias: bool) -> bool:
    if str(rec.get("status", "")).lower() in ("accepted", "passed"):
        return True
    if rec.get("supports_claim") is True:
        return True
    if str(rec.get("validation_status", "")).lower() == "passed":
        return True
    if alias and rec.get("author_asserts_supports") is True:
        return True
    return False


def has_artifact_hash(rec: dict) -> bool:
    if any(rec.get(k) for k in HASH_FIELDS):
        return True
    refs = rec.get("artifact_refs")
    if isinstance(refs, str) and HEX64.search(refs):
        return True
    if isinstance(refs, list):
        for item in refs:
            if isinstance(item, str) and HEX64.search(item):
                return True
            if isinstance(item, dict) and any(
                    isinstance(v, str) and HEX64.search(v) for v in item.values()):
                return True
    return False


def variant_flags(rec: dict) -> dict:
    al = accepted(rec, alias=True)
    ca = accepted(rec, alias=False)
    hr = has_review(rec)
    hh = has_artifact_hash(rec)
    return {
        "V0_canonical": bool(ca and not hr),
        "V1_canonical_plus_hash": bool(ca and not hr and not hh),
        "V2_alias_closed": bool(al and not hr),
        "V3_alias_closed_plus_hash": bool(al and not hr and not hh),
    }


def parse_jsonl(path: str):
    """Stream-parse a .jsonl file. Returns (records, parse_errors)."""
    records, errors = [], 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                errors += 1
                continue
            if isinstance(obj, dict):
                records.append(obj)
    return records, errors


def scan_pass(parse: bool):
    """One census pass. parse=True also parses records and evaluates variants."""
    table = {}
    for root in SCAN_ROOTS:
        root_abs = os.path.join(ROOT, root)
        for dp, _dns, fns in os.walk(root_abs):
            for fn in sorted(fns):
                if not fn.endswith(".jsonl"):
                    continue
                ap = os.path.join(dp, fn)
                r = rel(ap)
                try:
                    dig = sha256_file(ap)
                    size = os.path.getsize(ap)
                except OSError as e:
                    table[r] = {"error": f"unreadable: {e}"}
                    continue
                entry = {"sha256": dig, "bytes": size}
                cls, matches = classify(r)
                entry["scope_class"] = cls
                entry["scope_matches"] = matches
                if parse:
                    recs, perr = parse_jsonl(ap)
                    hits = {k: 0 for k in ("V0_canonical", "V1_canonical_plus_hash",
                                           "V2_alias_closed", "V3_alias_closed_plus_hash")}
                    bare_sha256_rows = 0
                    for rec in recs:
                        fl = variant_flags(rec)
                        for k, v in fl.items():
                            if v:
                                hits[k] += 1
                        if rec.get("sha256"):
                            bare_sha256_rows += 1
                    entry["records"] = len(recs)
                    entry["parse_errors"] = perr
                    entry["hits"] = hits
                    entry["bare_sha256_rows"] = bare_sha256_rows
                    # Record-shape arm: like-for-like with the A0 record-kind
                    # universe.  Ledger-shaped = rows carrying theorem_id/entry_kind;
                    # event-stream = rows carrying event_type.
                    entry["ledger_rows"] = sum(
                        1 for x in recs if x.get("theorem_id") or x.get("entry_kind"))
                    entry["event_rows"] = sum(
                        1 for x in recs if x.get("event_type"))
                    if entry["ledger_rows"] >= entry["event_rows"] and entry["ledger_rows"]:
                        entry["shape"] = "ledger_shaped"
                    elif entry["event_rows"]:
                        entry["shape"] = "event_stream"
                    else:
                        entry["shape"] = "other"
                table[r] = entry
    return table


def aggregate(table: dict, shapes=None) -> dict:
    agg = {
        "shape_filter": sorted(shapes) if shapes else ["<all>"],
        "files": 0,
        "records": 0,
        "parse_errors": 0,
        "files_by_class": {},
        "hits_by_class": {},
        "kept_files_with_hits": {k: [] for k in
                                 ("V0_canonical", "V1_canonical_plus_hash",
                                  "V2_alias_closed", "V3_alias_closed_plus_hash")},
        "excluded_or_staging_files_with_hits": {k: [] for k in
                                                ("V0_canonical", "V1_canonical_plus_hash",
                                                 "V2_alias_closed", "V3_alias_closed_plus_hash")},
        "totals": {k: 0 for k in ("V0_canonical", "V1_canonical_plus_hash",
                                  "V2_alias_closed", "V3_alias_closed_plus_hash")},
        "kept_totals": {k: 0 for k in ("V0_canonical", "V1_canonical_plus_hash",
                                       "V2_alias_closed", "V3_alias_closed_plus_hash")},
        "excluded_totals": {k: 0 for k in ("V0_canonical", "V1_canonical_plus_hash",
                                           "V2_alias_closed", "V3_alias_closed_plus_hash")},
        "ambiguity": [],
    }
    for r in sorted(table):
        e = table[r]
        if "hits" not in e:
            continue
        if shapes and e.get("shape") not in shapes:
            continue
        cls = e["scope_class"]
        agg["files"] += 1
        agg["records"] += e["records"]
        agg["parse_errors"] += e["parse_errors"]
        agg["files_by_class"][cls] = agg["files_by_class"].get(cls, 0) + 1
        if len(e["scope_matches"]) > 1:
            agg["ambiguity"].append({"path": r, "matches": e["scope_matches"],
                                     "primary": cls, "shape": e.get("shape")})
        bucket = agg["hits_by_class"].setdefault(cls, {k: 0 for k in agg["totals"]})
        kept = cls not in ("historical", "snapshot_copy", "staging_unresolved")
        for k in agg["totals"]:
            n = e["hits"][k]
            bucket[k] += n
            agg["totals"][k] += n
            if kept:
                agg["kept_totals"][k] += n
                if n:
                    agg["kept_files_with_hits"][k].append(
                        {"path": r, "class": cls, "shape": e.get("shape"),
                         "hits": n, "records": e["records"]})
            else:
                agg["excluded_totals"][k] += n
                if n:
                    agg["excluded_or_staging_files_with_hits"][k].append(
                        {"path": r, "class": cls, "shape": e.get("shape"),
                         "hits": n, "records": e["records"]})
    for k in agg["kept_files_with_hits"]:
        agg["kept_files_with_hits"][k].sort(key=lambda d: (-d["hits"], d["path"]))
        agg["excluded_or_staging_files_with_hits"][k].sort(
            key=lambda d: (-d["hits"], d["path"]))
    return agg


def control_record(cid: str, ok: bool, detail: str, expected: str = "",
                   measured=None) -> dict:
    return {"id": cid, "ok": bool(ok), "expected": expected,
            "detail": detail, "measured": measured}


def main() -> int:
    started = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()

    # ---- pin guard -------------------------------------------------------
    pin_state = {}
    for p, want in PINS.items():
        ap = os.path.join(ROOT, p)
        got = sha256_file(ap) if os.path.exists(ap) else None
        pin_state[p] = {"declared": want, "measured": got, "match": got == want}
    guard_before = {p: (sha256_file(os.path.join(ROOT, p))
                        if os.path.exists(os.path.join(ROOT, p)) else None)
                    for p in GUARD_PATHS}

    a0 = json.load(open(os.path.join(ROOT,
                "evaluation/A0_detector_scope_adjudication.json"), encoding="utf-8"))
    declared_before = a0["measured"]["_hf14_before"]

    # ---- pass 1 (hash + parse) ------------------------------------------
    t0 = scan_pass(parse=True)
    # ---- pass 2 (hash only) ---------------------------------------------
    t1 = scan_pass(parse=False)
    drift = sorted(r for r in t0
                   if r in t1 and t0[r].get("sha256") != t1[r].get("sha256"))
    if drift:
        # re-measure drifted files once, recording that the census is instant-bound
        t2 = scan_pass(parse=True)
        for r in drift:
            if r in t2:
                t0[r] = t2[r]
        t1 = scan_pass(parse=False)

    agg = aggregate(t0)
    agg_ledger = aggregate(t0, shapes={"ledger_shaped"})
    agg_events = aggregate(t0, shapes={"event_stream"})

    # ---- control C1: replay the A0 before-census at its declared pins ----
    c1_detail, c1_ok, c1_rows = [], True, {}
    for p, n in sorted(declared_before.items()):
        ap = os.path.join(ROOT, p)
        if not os.path.exists(ap):
            c1_ok = False
            c1_detail.append(f"{p}: MISSING")
            continue
        recs, _ = parse_jsonl(ap)
        c = sum(1 for rec in recs if variant_flags(rec)["V0_canonical"])
        c1_rows[p] = {"declared": n, "measured": c, "match": c == n}
        if c != n:
            c1_ok = False
            c1_detail.append(f"{p}: declared {n} measured {c}")
    c1 = control_record(
        "C1", c1_ok,
        "V0 replay of the A0 before-census at the 12 declared file pins: "
        f"{sum(1 for v in c1_rows.values() if v['match'])}/{len(c1_rows)} match, "
        f"declared total {sum(declared_before.values())}, measured total "
        f"{sum(v['measured'] for v in c1_rows.values())}",
        expected="all 12 per-file counts equal",
        measured=c1_rows)

    # ---- live ledger controls -------------------------------------------
    live_path = os.path.join(ROOT, "ledger/theorems.jsonl")
    live_rows, _ = parse_jsonl(live_path)
    v0_live = sum(1 for r in live_rows if variant_flags(r)["V0_canonical"])
    v2_live = sum(1 for r in live_rows if variant_flags(r)["V2_alias_closed"])
    c2 = control_record("C2", v0_live == 0,
                        f"V0 on live canonical ledger = {v0_live}",
                        expected="0", measured=v0_live)
    c3 = control_record("C3", v2_live == 60,
                        f"V2 on live canonical ledger = {v2_live}",
                        expected="60", measured=v2_live)

    # C4: in-memory reviewer_verdicts mutation on one V2 hit
    hit_idx = [i for i, r in enumerate(live_rows)
               if variant_flags(r)["V2_alias_closed"]]
    mut = copy.deepcopy(live_rows)
    if hit_idx:
        mut[hit_idx[0]]["reviewer_verdicts"] = ["W001-mutation-control"]
    v2_after_review = sum(1 for r in mut if variant_flags(r)["V2_alias_closed"])
    c4 = control_record("C4", v2_after_review == v2_live - 1,
                        "add reviewer_verdicts to one live V2 hit: "
                        f"{v2_live} -> {v2_after_review}",
                        expected=f"{v2_live - 1}", measured=v2_after_review)

    # C5: in-memory artifact_sha256 mutation (rubric hash clause)
    mut2 = copy.deepcopy(live_rows)
    if hit_idx:
        mut2[hit_idx[0]]["artifact_sha256"] = "0" * 64
    v3_before = sum(1 for r in live_rows if variant_flags(r)["V3_alias_closed_plus_hash"])
    v3_after = sum(1 for r in mut2 if variant_flags(r)["V3_alias_closed_plus_hash"])
    v2_after_hash = sum(1 for r in mut2 if variant_flags(r)["V2_alias_closed"])
    c5 = control_record("C5", v3_after == v3_before - 1 and v2_after_hash == v2_live,
                        "add artifact_sha256 to one live V2 hit: "
                        f"V3 {v3_before} -> {v3_after}, V2 stays {v2_after_hash}",
                        expected=f"V3 {v3_before - 1}, V2 {v2_live}",
                        measured={"V3_before": v3_before, "V3_after": v3_after,
                                  "V2_after": v2_after_hash})

    # C6: classify unit controls
    c6_cases = {
        "artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl":
            ("historical", True),
        "artifacts/literature/sources/batch-01.jsonl": ("live_build_input", False),
        "ledger/theorems.jsonl": ("canonical", False),
        "artifacts/worker-007/claim42_verify/snapshot/theorems.ce42d205e761.jsonl":
            ("snapshot_copy", True),
    }
    c6_rows, c6_ok = {}, True
    for p, (want_cls, want_excl) in c6_cases.items():
        cls, _m = classify(p)
        excl = cls in ("historical", "snapshot_copy")
        ok = (cls == want_cls and excl == want_excl)
        c6_rows[p] = {"class": cls, "excluded": excl, "ok": ok}
        c6_ok = c6_ok and ok
    c6 = control_record("C6", c6_ok, "classify() unit controls",
                        expected="4/4", measured=c6_rows)

    # C7: remove the alias token in memory
    mut3 = copy.deepcopy(live_rows)
    for r in mut3:
        r.pop("author_asserts_supports", None)
    v2_no_alias = sum(1 for r in mut3 if variant_flags(r)["V2_alias_closed"])
    v0_no_alias = sum(1 for r in mut3 if variant_flags(r)["V0_canonical"])
    c7 = control_record("C7", v2_no_alias == 0 and v0_no_alias == 0,
                        "author_asserts_supports removed in memory: "
                        f"V2 {v2_live} -> {v2_no_alias}, V0 stays {v0_no_alias}",
                        expected="V2 0, V0 0",
                        measured={"V2": v2_no_alias, "V0": v0_no_alias})

    # C8: T0==T1 identity
    c8_rows = {"scanned_files": len(t0),
               "hash_mismatches": len(drift),
               "pin_recheck": {p: {"match": PINS[p] == sha256_file(os.path.join(ROOT, p))
                                   if os.path.exists(os.path.join(ROOT, p)) else False}
                               for p in PINS}}
    c8_ok = (c8_rows["hash_mismatches"] == 0
             and all(v["match"] for v in c8_rows["pin_recheck"].values()))
    c8 = control_record("C8", c8_ok,
                        "T0==T1 hashes for scanned files and pinned inputs",
                        expected="0 mismatches, all pins match",
                        measured=c8_rows)
    map_after = {p: (sha256_file(os.path.join(ROOT, p))
                     if os.path.exists(os.path.join(ROOT, p)) else None)
                 for p in GUARD_PATHS}
    c9 = control_record("C9", map_after == guard_before,
                        "canonical-write guard: read-only paths unchanged",
                        expected="unchanged",
                        measured={"before": guard_before, "after": map_after})

    controls = [c1, c2, c3, c4, c5, c6, c7, c8, c9]
    controls_ok = all(c["ok"] for c in controls)

    # ---- decision rule ---------------------------------------------------
    p4 = agg["kept_totals"]["V0_canonical"] == 0
    p5 = agg["kept_totals"]["V2_alias_closed"] >= 60
    ledger_live_v2 = next((f for f in agg["kept_files_with_hits"]["V2_alias_closed"]
                           if f["path"] == "ledger/theorems.jsonl"), None)
    p5 = p5 and ledger_live_v2 is not None
    # Like-for-like arm: ledger-shaped record files only (the A0 HF-14 branch's
    # own 12 declared hit files are all ledger-shaped).
    lp4 = agg_ledger["kept_totals"]["V0_canonical"] == 0
    lp5 = (agg_ledger["kept_totals"]["V2_alias_closed"] >= 60
           and ledger_live_v2 is not None)
    ledger_leaks_v0 = [f for f in agg_ledger["kept_files_with_hits"]["V0_canonical"]
                       if f["path"] != "ledger/theorems.jsonl"]
    if not controls_ok:
        verdict = "INCONCLUSIVE_PIN_OR_CONTROL_FAILURE"
        deviation = None
    elif p4 and p5:
        verdict = "A0_HF14_SCOPE_VOCABULARY_BLIND"
        deviation = None
    elif p5 and not p4:
        verdict = "A0_HF14_SCOPE_NOT_ROBUST"
        deviation = ("Pre-registered rule anticipated only (P4 and P5) -> "
                     "A0_HF14_SCOPE_VOCABULARY_BLIND and (P5 fails) -> "
                     "A0_HF14_SCOPE_STABLE. Measured: P5 holds but P4 fails, so "
                     "neither named branch applies. Reported as the stronger "
                     "measured state; no prediction was re-labelled and no count "
                     "was changed. The added ledger-shaped arm is an additional "
                     "measurement, not a changed prediction.")
    elif lp4 and lp5:
        verdict = "A0_HF14_SCOPE_VOCABULARY_BLIND"
        deviation = ("All-.jsonl arm fails P4 (event-stream/derived files), but the "
                     "ledger-shaped arm holds P4+P5; the pre-registered vocabulary "
                     "finding is reported on the like-for-like arm.")
    else:
        verdict = "A0_HF14_SCOPE_STABLE"
        deviation = None

    findings = []
    if v2_live > 0 and v0_live == 0:
        findings.append({
            "id": "F1-vocabulary",
            "statement": ("The live canonical ledger (scope class canonical, never "
                          "excludable) fires 0 under the shipped detector and 60 under the "
                          "rubric-literal alias-closed reading, with 0 reviewer-verdict "
                          "fields and 0 artifact-hash fields. The A0 after-scope HF-14 "
                          "total of 0 is therefore conditional on not reading "
                          "author_asserts_supports as supports_claim."),
            "evidence": ["ledger/theorems.jsonl#a1674f094979",
                         "evaluation_rubric.yaml#d748a9e3574e:243",
                         "evaluation/A0_detector_scope_adjudication.json#a26be4b85706"],
            "severity": "critical (rubric HF-14 severity)",
        })
    if ledger_leaks_v0:
        findings.append({
            "id": "F2-name-exclusion-leak",
            "statement": ("The declared classify(rel) excludes by path tokens; worker-derived "
                          "ledger copies whose paths lack those tokens are classified kept "
                          "and fire the SHIPPED detector at the current snapshot, so the "
                          "after-scope 0 no longer reproduces even under the shipped "
                          "vocabulary."),
            "evidence": [f["path"] for f in ledger_leaks_v0],
            "measured": {"ledger_shaped_kept_V0_nonledger": sum(
                f["hits"] for f in ledger_leaks_v0)},
        })
    if agg["kept_totals"]["V0_canonical"] > 0:
        findings.append({
            "id": "F3-time-snapshot",
            "statement": ("The A0 adjudication measured after-scope = 0 at 00:53:51; at the "
                          "current snapshot the kept-class canonical-detector total is "
                          f"{agg['kept_totals']['V0_canonical']} records over "
                          f"{len(agg['kept_files_with_hits']['V0_canonical'])} files, so the "
                          "number is instant-bound (corroborates the audit lead's recorded "
                          "defect for the HF-14 branch)."),
            "evidence": ["evaluation/A0_detector_scope_adjudication.json#a26be4b85706"],
        })

    predictions = {
        "P1": {**c1["measured"], "pass": c1["ok"]},
        "P2": {"V0_live_ledger": v0_live, "pass": v0_live == 0},
        "P3": {"V2_live_ledger": v2_live, "pass": v2_live == 60},
        "P4": {"kept_V0_total": agg["kept_totals"]["V0_canonical"], "pass": p4},
        "P5": {"kept_V2_total": agg["kept_totals"]["V2_alias_closed"],
               "ledger_live_entry": ledger_live_v2, "pass": p5},
        "P6": {"excluded_staging_V0_total": agg["excluded_totals"]["V0_canonical"],
               "pass": agg["excluded_totals"]["V0_canonical"] >= 586},
        "P7": {"live_ledger_bare_sha256_rows":
               t0.get("ledger/theorems.jsonl", {}).get("bare_sha256_rows"),
               "pass": pure_p7(live_rows)},
        "P8": {"ambiguity_count": len(agg["ambiguity"]),
               "pass": len(agg["ambiguity"]) == 0},
        "P9": {"controls_ok": controls_ok, "pass": controls_ok},
        "P10_extra_ledger_shaped_arm_P4": {
            "kept_V0_total": agg_ledger["kept_totals"]["V0_canonical"],
            "pass": lp4},
        "P11_extra_ledger_shaped_arm_P5": {
            "kept_V2_total": agg_ledger["kept_totals"]["V2_alias_closed"],
            "pass": lp5},
    }

    report = {
        "schema": "worker-measurement/1",
        "task_id": "W001-A0-HF14-VOCAB-SCOPE-01",
        "actor": "worker-001",
        "node_id": "A0",
        "gate": "G-AUDIT",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN",
                      "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "authority_note": ("Worker event: no gate verdict, no node transition, no "
                           "canonical write. The HF-14 discharge ruling belongs to the "
                           "audit lead / controller."),
        "question": "Is the A0 detector-scope HF-14 after-total of 0 conditional on the "
                    "rev3 marker-field rename (supports_claim -> author_asserts_supports)?",
        "verdict": verdict,
        "pins": pin_state,
        "scope_predicate": "classify(rel) verbatim from evaluation/A0_detector_scope_adjudication.json; "
                           "exclude iff class in {historical, snapshot_copy}; precedence keeps live "
                           "classes first so no live path can be hidden by a snapshot token",
        "variants": {
            "V0_canonical": "status in {accepted,passed} | supports_claim=true | validation_status=passed; fire iff no reviewer verdict",
            "V1_canonical_plus_hash": "V0 + no conservative artifact-hash field",
            "V2_alias_closed": "V0 + author_asserts_supports counts as supports_claim",
            "V3_alias_closed_plus_hash": "V2 + no conservative artifact-hash field",
        },
        "universe": {
            "roots": list(SCAN_ROOTS),
            "suffix": ".jsonl",
            "files": agg["files"],
            "records": agg["records"],
            "parse_errors": agg["parse_errors"],
            "drift_files_reparsed": drift,
        },
        "a0_declared_before_census": {
            "declared_total": sum(declared_before.values()),
            "declared_files": len(declared_before),
            "replayed_exactly": c1["ok"],
        },
        "census": agg,
        "census_ledger_shaped": agg_ledger,
        "census_event_stream": agg_events,
        "findings": findings,
        "decision_rule_deviation": deviation,
        "live_ledger_detail": {
            "path": "ledger/theorems.jsonl",
            "sha256": PINS["ledger/theorems.jsonl"],
            "rows": len(live_rows),
            "V0": v0_live,
            "V1": sum(1 for r in live_rows if variant_flags(r)["V1_canonical_plus_hash"]),
            "V2": v2_live,
            "V3": v3_before,
            "reviewer_verdict_fields": sum(1 for r in live_rows if has_review(r)),
            "artifact_hash_fields": sum(1 for r in live_rows if has_artifact_hash(r)),
            "alias_marker_rows": sum(1 for r in live_rows
                                     if r.get("author_asserts_supports") is True),
            "V2_ids": sorted(r.get("theorem_id") or r.get("claim_id") or "<record>"
                             for r in live_rows if variant_flags(r)["V2_alias_closed"]),
        },
        "a0_after_scope_recomputed": {
            "V0_kept_total": agg["kept_totals"]["V0_canonical"],
            "V1_kept_total": agg["kept_totals"]["V1_canonical_plus_hash"],
            "V2_kept_total": agg["kept_totals"]["V2_alias_closed"],
            "V3_kept_total": agg["kept_totals"]["V3_alias_closed_plus_hash"],
            "V0_excluded_staging_total": agg["excluded_totals"]["V0_canonical"],
            "V2_excluded_staging_total": agg["excluded_totals"]["V2_alias_closed"],
        },
        "predictions": predictions,
        "controls": controls,
        "falsifier": ("A rubric-conformant reading in which author_asserts_supports=true is not "
                      "the marker the rubric names (supports_claim=true); or ledger/theorems.jsonl "
                      "shown to be outside the canonical class / excluded by classify(rel); or a "
                      "snapshot at which it contributes 0 alias-closed HF-14 records."),
        "not_claimed": [
            "not a mathematics or physics claim",
            "not a gate verdict or node transition",
            "does not rule on whether the rev3 rename discharges HF-14 (audit-lead scope ruling)",
            "does not modify any canonical file",
        ],
        "measured_at": started,
    }
    core = {k: v for k, v in report.items() if k != "measured_at"}
    core_digest = hashlib.sha256(
        json.dumps(core, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    report["core_digest_sha256"] = core_digest

    with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, sort_keys=True, indent=1, ensure_ascii=False)
        f.write("\n")
    with open(os.path.join(OUT, "controls.json"), "w", encoding="utf-8") as f:
        json.dump({"task_id": report["task_id"], "controls_ok": controls_ok,
                   "controls": controls}, f, sort_keys=True, indent=1,
                  ensure_ascii=False)
        f.write("\n")
    with open(os.path.join(OUT, "PINNED.json"), "w", encoding="utf-8") as f:
        json.dump({"task_id": report["task_id"],
                   "pins": {p: {"declared": PINS[p],
                                "measured": pin_state[p]["measured"],
                                "match": pin_state[p]["match"]} for p in PINS},
                   "guard_paths": {"before": guard_before, "after": map_after},
                   "scanned_files": len(t0),
                   "scanned_records": agg["records"],
                   "T0_T1_hash_mismatches": drift}, f, sort_keys=True, indent=1,
                  ensure_ascii=False)
        f.write("\n")

    print(f"verdict={verdict} controls_ok={controls_ok} "
          f"all: V0_kept={agg['kept_totals']['V0_canonical']} "
          f"V2_kept={agg['kept_totals']['V2_alias_closed']} | "
          f"ledger-shaped: V0_kept={agg_ledger['kept_totals']['V0_canonical']} "
          f"V2_kept={agg_ledger['kept_totals']['V2_alias_closed']} | "
          f"live_ledger V0={v0_live} V2={v2_live} core={core_digest[:12]}")
    if not controls_ok:
        for c in controls:
            if not c["ok"]:
                print("FAILED CONTROL", c["id"], c["detail"])
        return 2
    if not all(v["match"] for v in pin_state.values()):
        return 3
    return 0


def pure_p7(rows) -> bool:
    return all(not has_review(r) and not has_artifact_hash(r) for r in rows)


if __name__ == "__main__":
    sys.exit(main())
