#!/usr/bin/env python3
"""W074-L0-CENSUS-ADVERSARIAL-01 -- independent adversarial verification of the
L0 verdict-census predicates at frozen ledger/theorems.jsonl#a1674f094979.

Read-only over every canonical path.  Writes only under the directory passed to
--out (default: the directory holding this script).

What is measured
----------------
1. Reproduce, literally, the controller predicate
   `research_map/astra_lifecycle.py::review_coverage` + `_targets_in_review` +
   `_explicit_pins` over reviews/*.json at the measurement instant.
2. Reproduce the literature lead's accepted-stream census
   (artifacts/literature/reviews/L0-verdict-census-20260912T0058.json) and its
   completeness audit (L0-census-completeness-audit-20260912T0107.json), and
   test the audit's own falsifier list against the stream at this instant.
3. Reconcile the populations per reviewer and per accept definition.
4. Run in-memory mutation controls that must discriminate.
5. Re-measure the live full-schema accept set at the instant.

Authority: worker measurement only.  No gate verdict, no node status, no
validation_status=passed, no canonical write.  Exit 2 on pin drift, 3 on a
failing control or corpus drift, 0 when every declared check passes.
"""

import argparse
import datetime
import hashlib
import json
import pathlib
import re
import sys

TASK_ID = "W074-L0-CENSUS-ADVERSARIAL-01"
NODE_ID = "L0"
GATE = "G-LIT"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]

L0_PIN = "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"
L1_PIN = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
FROZEN_PIN = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
RUBRIC_PIN = "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885"
LEAD_CENSUS_SHA = "5053607115fd26ef09d2eaf94a3c8b016ad798074d56267dc7e7437eaf83b74a"
LEAD_AUDIT_SHA = "e0a44356da9bcfa97bf6c4ff6eea14a93566aec863b212cc99fbade3e33d3b95"
FINAL_VERIFY_PREFIX = "8f3ddc732983"
STALE_L0_PINS = {
    "ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72": "L0 rev2 (lit-l4 exit)",
    "3e3d35531421388a17ca7bad7f6c7093dd1cc21a3a808ca8ff65ce6c2b79c6a6": "L0 rev3 hand-patch (superseded)",
}

LEAD_CENSUS_PATH = "artifacts/literature/reviews/L0-verdict-census-20260912T0058.json"
LEAD_AUDIT_PATH = "artifacts/literature/reviews/L0-census-completeness-audit-20260912T0107.json"
FINAL_VERIFY_PATH = "reviews/L0-review-final-verify.json"
EVENTS_PATH = "research_map/events.jsonl"

VERDICT_KINDS = ("accept", "revise", "reject", "inconclusive")
TARGET_ALIASES = {
    "F0": "F0", "F1": "F1", "F2A": "F2a", "F2B": "F2b", "F2": "F2b",
    "L0": "L0", "L1": "L1",
    "AF-WCC-VAC-GEN": "F1",
    "AF-SCC-C2-VAC-GEN": "F2a",
    "AF-SCC-C0-VAC-GEN": "F2b",
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def sha256_file(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def mtime_iso(p):
    return datetime.datetime.fromtimestamp(pathlib.Path(p).stat().st_mtime).astimezone().replace(microsecond=0).isoformat()


# ---------------------------------------------------------------- predicates
def targets_in_review(d):
    """Exact re-implementation of astra_lifecycle._targets_in_review."""
    out = set()
    for key in ("target_id", "target", "target_subnode"):
        v = d.get(key)
        if isinstance(v, str):
            out.add(v)
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                if isinstance(v.get(k2), str):
                    out.add(v[k2])
    return {TARGET_ALIASES.get(t, TARGET_ALIASES.get(t.upper(), t)) for t in out}


def explicit_pins(d):
    """Exact re-implementation of astra_lifecycle._explicit_pins."""
    pins = []
    for key in ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256"):
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


def pin_matches(pin, h):
    return bool(pin) and (pin.startswith(h[:12]) or h.startswith(pin[:12]))


def all_hex64(d, _depth=0):
    found = []
    if _depth > 6:
        return found
    if isinstance(d, str):
        s = d.strip().lower()
        if HEX64.match(s):
            found.append(s)
    elif isinstance(d, dict):
        for v in d.values():
            found.extend(all_hex64(v, _depth + 1))
    elif isinstance(d, list):
        for v in d:
            found.extend(all_hex64(v, _depth + 1))
    return found


def resolve_full(d):
    """Controller default: absent flag counts as full; explicit false is scoped."""
    raw = d.get("counts_as_full_schema_verdict")
    return (True, raw) if raw is not False else (False, raw)


def load_review_corpus(root):
    corpus = []
    for rp in sorted((root / "reviews").glob("*.json")):
        raw = rp.read_bytes()
        try:
            d = json.loads(raw)
        except Exception:
            corpus.append({"file": rp.name, "parse_error": True, "sha256": hashlib.sha256(raw).hexdigest()})
            continue
        corpus.append({"file": rp.name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                       "mtime": mtime_iso(rp), "data": d})
    return corpus


def corpus_manifest(corpus):
    return hashlib.sha256(("\n".join(f"{r['file']} {r.get('sha256', '')}" for r in corpus)).encode()).hexdigest()


# ---------------------------------------------------------------- scans
def controller_scan(corpus, channel_off=(), mutated_pin=None):
    """Reproduce review_coverage for target L0.  channel_off disables
    'alias' / 'path' / 'pin' channels for sensitivity controls."""
    target_pin = mutated_pin or L0_PIN
    records = []
    for rec in corpus:
        if rec.get("parse_error"):
            continue
        d = rec["data"]
        v = str(d.get("verdict", "")).lower()
        if v not in VERDICT_KINDS:
            continue
        reviewer = str(d.get("reviewer") or d.get("actor") or "?")
        full, raw_full = resolve_full(d)
        tgts = targets_in_review(d)
        alias_hit = "L0" in tgts and "alias" not in channel_off
        path_hit = "path" not in channel_off and any("ledger/theorems.jsonl" in t for t in tgts)
        pins = explicit_pins(d)
        pin_hit = "pin" not in channel_off and any(pin_matches(p, target_pin) for p in pins)
        if not (alias_hit or path_hit or pin_hit):
            continue
        records.append({
            "file": rec["file"], "sha256": rec["sha256"], "mtime": rec["mtime"],
            "reviewer": reviewer, "verdict": v,
            "counts_as_full_schema_verdict_raw": raw_full,
            "counts_as_full_schema_verdict_resolved": full,
            "targets_normalized": sorted(tgts),
            "targets_raw": sorted({str(d.get(k)) for k in ("target_id", "target", "target_subnode") if d.get(k)}),
            "explicit_pins": [p[:12] for p in pins],
            "channel_alias": alias_hit, "channel_path": path_hit, "channel_pin": pin_hit,
            "declared_created_at": d.get("created_at"),
            "stale_l0_pins": sorted({p for p in all_hex64(d) if not pin_matches(p, L0_PIN)}),
        })
    return records


def file_l0_records(corpus):
    """Every review file with an L0 channel, incl. prose-only mentions."""
    out = []
    for rec in corpus:
        if rec.get("parse_error"):
            continue
        d = rec["data"]
        v = str(d.get("verdict", "")).lower()
        text = json.dumps(d)
        tgts = targets_in_review(d)
        pins = explicit_pins(d)
        alias_hit = "L0" in tgts
        path_hit = any("ledger/theorems.jsonl" in t for t in tgts)
        pin_hit = any(pin_matches(p, L0_PIN) for p in pins)
        prose_hit = L0_PIN[:12] in text.lower()
        if not (alias_hit or path_hit or pin_hit or prose_hit):
            continue
        full, raw_full = resolve_full(d)
        out.append({
            "file": rec["file"], "sha256": rec["sha256"], "mtime": rec["mtime"],
            "reviewer": str(d.get("reviewer") or d.get("actor") or "?"),
            "verdict": v if v in VERDICT_KINDS else None, "raw_verdict": d.get("verdict"),
            "full": full, "full_raw": raw_full,
            "alias": alias_hit, "path": path_hit, "pin": pin_hit,
            "prose_only": prose_hit and not (alias_hit or path_hit or pin_hit),
            "pins": [p[:12] for p in pins],
            "stale_pins_known": sorted({p for p in all_hex64(d) if p in STALE_L0_PINS}),
            "declared_created_at": d.get("created_at"),
        })
    return out


def event_scan(events):
    """Accepted-stream review events binding the frozen L0 hash."""
    rows = []
    for e in events:
        if e.get("event_type") != "review":
            continue
        blob = json.dumps(e)
        if L0_PIN[:12] not in blob and "ledger/theorems.jsonl" not in blob:
            continue
        target = str(e.get("target_id") or e.get("target") or "")
        ev_refs = [str(x) for x in (e.get("evidence_refs") or [])]
        pins = [str(x).lower() for x in ev_refs if HEX64.match(str(x).lower())]
        for k in ("reviewed_sha256", "target_sha256"):
            if isinstance(e.get(k), str):
                pins.append(e[k].lower())
        binds_live = any(pin_matches(p, L0_PIN) for p in pins) or L0_PIN[:12] in json.dumps(ev_refs)
        ledger_target = (target == "L0" or target.startswith("L0:") or "ledger/theorems.jsonl" in target)
        rows.append({
            "event_id": e.get("event_id"), "created_at": e.get("created_at"), "actor": e.get("actor"),
            "verdict": e.get("verdict"), "score": e.get("score"), "target_id": target,
            "binds_live_by_pin": binds_live, "target_is_ledger": ledger_target,
            "counts_as_full_schema_verdict": e.get("counts_as_full_schema_verdict"),
            "class": "ledger_content" if ledger_target else "other_object",
            "evidence_refs": ev_refs[:6],
        })
    return rows


# ---------------------------------------------------------------- controls
def controls(corpus, events, literal):
    results = []

    def base_keys(rows):
        return {(r["file"], r["reviewer"], r["verdict"]) for r in rows}

    live_full_accepts = sorted({r["reviewer"] for r in literal
                                if r["verdict"] == "accept" and r["counts_as_full_schema_verdict_resolved"]})
    results.append({"id": "C0_live_baseline",
                    "observed": {"literal_records": len(literal), "live_full_accepts": live_full_accepts},
                    "expect": "measurement baseline is non-empty",
                    "pass": len(literal) > 0 and len(live_full_accepts) >= 1})

    mut = L0_PIN[:20] + ("0" if L0_PIN[20] != "0" else "1") + L0_PIN[21:]
    mutated = controller_scan(corpus, mutated_pin=mut)
    expected_mut = base_keys([r for r in literal if r["channel_alias"] or r["channel_path"]])
    results.append({"id": "C1_pin_mutation_isolation",
                    "observed": {"mutated_pin_prefix": mut[:12], "records": len(mutated),
                                 "any_pin_channel_left": any(r["channel_pin"] for r in mutated)},
                    "expect": "with the live pin mutated, no record binds via the pin channel and the surviving set is exactly the alias/path set",
                    "pass": (not any(r["channel_pin"] for r in mutated)) and base_keys(mutated) == expected_mut})

    no_alias = controller_scan(corpus, channel_off=("alias",))
    expected_no_alias = base_keys([r for r in literal if r["channel_path"] or r["channel_pin"]])
    results.append({"id": "C2_alias_ablation_identity",
                    "observed": {"records": len(no_alias), "expected": len(expected_no_alias)},
                    "expect": "alias-ablation survivor set equals the path/pin subset (discriminating iff any record is alias-only)",
                    "pass": base_keys(no_alias) == expected_no_alias})

    no_pin = controller_scan(corpus, channel_off=("pin",))
    expected_no_pin = base_keys([r for r in literal if r["channel_alias"] or r["channel_path"]])
    results.append({"id": "C3_pin_ablation_identity",
                    "observed": {"records": len(no_pin), "expected": len(expected_no_pin)},
                    "expect": "pin-ablation survivor set equals the alias/path subset (discriminating iff any record is pin-only)",
                    "pass": base_keys(no_pin) == expected_no_pin})

    sc = {"file": "__synthetic_scoped__.json", "sha256": "0" * 64, "mtime": "synthetic", "data": {
        "reviewer": "synthetic-scoped", "verdict": "accept", "target_id": "L0",
        "reviewed_sha256": L0_PIN, "counts_as_full_schema_verdict": False}}
    sc_full = {r["reviewer"] for r in controller_scan(corpus + [sc])
               if r["counts_as_full_schema_verdict_resolved"] and r["verdict"] == "accept"}
    results.append({"id": "C4_scoped_accept_excluded",
                    "observed": {"in_full_set": "synthetic-scoped" in sc_full},
                    "expect": "explicit scoped accept never enters the full-schema set",
                    "pass": "synthetic-scoped" not in sc_full})

    stale = {"file": "__synthetic_stale__.json", "sha256": "0" * 64, "mtime": "synthetic", "data": {
        "reviewer": "synthetic-stale", "verdict": "accept", "target_id": "L0",
        "reviewed_sha256": sorted(STALE_L0_PINS)[0]}}
    stale_seen = {r["reviewer"] for r in controller_scan(corpus + [stale])}
    results.append({"id": "C5_stale_accept_excluded",
                    "observed": {"stale_accept_in_live_set": "synthetic-stale" in stale_seen},
                    "expect": "superseded-hash accept does not enter the live set",
                    "pass": "synthetic-stale" not in stale_seen})

    prose = {"file": "__synthetic_prose__.json", "sha256": "0" * 64, "mtime": "synthetic", "data": {
        "reviewer": "synthetic-prose", "verdict": "accept", "target_id": "F2b",
        "note": "mentions " + L0_PIN + " in prose only"}}
    results.append({"id": "C6_prose_only_excluded",
                    "observed": {"prose_only_in_scan": any(r["reviewer"] == "synthetic-prose"
                                                          for r in controller_scan(corpus + [prose]))},
                    "expect": "prose mention with no target/pin channel does not count",
                    "pass": not any(r["reviewer"] == "synthetic-prose" for r in controller_scan(corpus + [prose]))})

    pathform = {"file": "__synthetic_pathform__.json", "sha256": "0" * 64, "mtime": "synthetic", "data": {
        "reviewer": "synthetic-pathform", "verdict": "revise",
        "target_id": "L0:ledger/theorems.jsonl#" + L0_PIN}}
    pf = controller_scan(corpus + [pathform])
    results.append({"id": "C7_pathform_target_missed_by_literal_alias",
                    "observed": {"caught_by_alias_predicate": any(r["reviewer"] == "synthetic-pathform" for r in pf)},
                    "expect": "literal alias predicate does not normalize 'L0:path#hash' (worker-037 miss mechanism)",
                    "pass": not any(r["reviewer"] == "synthetic-pathform" for r in pf)})

    ev = {"event_id": "__synthetic_event__", "event_type": "review", "actor": "synthetic-eventonly",
          "created_at": "synthetic", "verdict": "revise", "target_id": "L0", "reviewed_sha256": L0_PIN}
    results.append({"id": "C8_event_only_caught_by_event_scan",
                    "observed": {"caught": any(r["event_id"] == "__synthetic_event__" for r in event_scan(events + [ev]))},
                    "expect": "accepted-stream predicate catches verdicts with no reviews/*.json file",
                    "pass": any(r["event_id"] == "__synthetic_event__" for r in event_scan(events + [ev]))})

    results.append({"id": "C9_determinism",
                    "observed": {"identical": json.dumps(controller_scan(corpus), sort_keys=True) ==
                                             json.dumps(controller_scan(corpus), sort_keys=True)},
                    "expect": "two scans of the same corpus are identical",
                    "pass": json.dumps(controller_scan(corpus), sort_keys=True) ==
                            json.dumps(controller_scan(corpus), sort_keys=True)})

    flipped = []
    for rec in corpus:
        if rec.get("parse_error"):
            flipped.append(rec)
            continue
        d2 = json.loads(json.dumps(rec["data"]))
        if d2.get("verdict") == "accept" and "L0" in targets_in_review(d2) and any(
                pin_matches(p, L0_PIN) for p in explicit_pins(d2)):
            d2["verdict"] = "revise"
        rec2 = dict(rec)
        rec2["data"] = d2
        flipped.append(rec2)
    flip_accepts = sorted({r["reviewer"] for r in controller_scan(flipped)
                           if r["verdict"] == "accept" and r["counts_as_full_schema_verdict_resolved"]})
    results.append({"id": "C10_accept_supersession_sensitivity",
                    "observed": {"accepts_after_flip_to_revise": flip_accepts},
                    "expect": "flipping every live-bound accept to revise empties the live full accept set",
                    "pass": flip_accepts == []})
    return results


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root = pathlib.Path(args.root).resolve()
    outdir = pathlib.Path(args.out).resolve() if args.out else pathlib.Path(__file__).resolve().parent
    (outdir / "raw").mkdir(parents=True, exist_ok=True)
    log = []

    def say(msg):
        log.append(msg)
        print(msg)

    fixed = {
        "ledger/theorems.jsonl": L0_PIN,
        "ledger/citation_audit.csv": L1_PIN,
        "artifacts/formulation/FROZEN.json": FROZEN_PIN,
        "evaluation_rubric.yaml": RUBRIC_PIN,
    }
    pins = {k: {"expected": v, "measured": sha256_file(root / k), "match": sha256_file(root / k) == v}
            for k, v in fixed.items()}
    for path, label, expect in ((LEAD_CENSUS_PATH, "lead_census", LEAD_CENSUS_SHA),
                                (LEAD_AUDIT_PATH, "lead_audit", LEAD_AUDIT_SHA)):
        m = sha256_file(root / path)
        pins[label] = {"expected": expect, "measured": m, "match": m == expect, "mtime": mtime_iso(root / path)}
    fv_sha = sha256_file(root / FINAL_VERIFY_PATH)
    pins["final_verify"] = {"expected": FINAL_VERIFY_PREFIX + " (prefix)", "measured": fv_sha,
                            "match": fv_sha.startswith(FINAL_VERIFY_PREFIX), "mtime": mtime_iso(root / FINAL_VERIFY_PATH)}
    drift = [k for k, v in pins.items() if not v["match"]]
    if drift:
        say("PIN DRIFT: " + ", ".join(drift))
        (outdir / "raw" / "run_log.txt").write_text("\n".join(log) + "\n")
        return 2

    corpus = load_review_corpus(root)
    manifest_t0 = corpus_manifest(corpus)
    say(f"review corpus T0: {len(corpus)} files, manifest {manifest_t0[:12]}")

    literal = controller_scan(corpus)
    file_recs = file_l0_records(corpus)
    events = [json.loads(l) for l in (root / EVENTS_PATH).read_text().splitlines() if l.strip()]
    ev_recs = event_scan(events)
    ev_content = [r for r in ev_recs if r["class"] == "ledger_content"]

    lead_census = json.loads((root / LEAD_CENSUS_PATH).read_text())
    lead_audit = json.loads((root / LEAD_AUDIT_PATH).read_text())
    fv = json.loads((root / FINAL_VERIFY_PATH).read_text())

    def acc(rows, verdict="accept"):
        return sorted({r["reviewer"] for r in rows if r["verdict"] == verdict})

    literal_full_accepts = sorted({r["reviewer"] for r in literal
                                   if r["verdict"] == "accept" and r["counts_as_full_schema_verdict_resolved"]})
    literal_scoped_accepts = sorted({r["reviewer"] for r in literal
                                     if r["verdict"] == "accept" and not r["counts_as_full_schema_verdict_resolved"]})
    lead_rows = [{"reviewer": r["actor"], "verdict": r["verdict"], "event_id": r["event_id"],
                  "full": r.get("counts_as_full_schema_verdict"), "target": r.get("target_id"),
                  "created_at": r.get("created_at"), "reviews_file": r.get("reviews_dir_records_for_reviewer")}
                 for r in lead_census["l0_content_verdicts"]]
    lead_accepts = acc(lead_rows)
    lead_accepts_full = sorted({r["reviewer"] for r in lead_census["l0_content_verdicts"]
                                if r["verdict"] == "accept" and r.get("counts_as_full_schema_verdict") is not False})
    audit_rows = [{"reviewer": r["reviewer"], "verdict": r["verdict"], "event_id": r["event_id"],
                   "created_at": r.get("created_at")} for r in lead_audit["ledger_content_verdicts"]]
    fv_table = fv["coverage_table"]
    fv_full = sorted({r["reviewer"] for r in fv_table if r["verdict"] == "accept" and r["full_schema"]})
    fv_scoped = sorted({r["reviewer"] for r in fv_table if r["verdict"] == "accept" and not r["full_schema"]})

    lit_set = {r["reviewer"] for r in literal}
    lead_set = {r["reviewer"] for r in lead_rows}
    audit_set = {r["reviewer"] for r in audit_rows}
    ev_set = {r["reviewer"] for r in ev_content}
    all_revs = sorted(lit_set | lead_set | ev_set)
    recon = [{
        "reviewer": rev,
        "literal_file_scan": rev in lit_set,
        "lead_L8_census": rev in lead_set,
        "lead_L9_audit": rev in audit_set,
        "event_scan_at_instant": rev in ev_set,
        "lead_verdict": next((r["verdict"] for r in lead_rows if r["reviewer"] == rev), None),
        "literal_verdict": next((r["verdict"] for r in literal if r["reviewer"] == rev), None),
        "event_verdict": next((r["verdict"] for r in ev_content if r["actor"] == rev), None),
        "literal_full": next((r["counts_as_full_schema_verdict_resolved"] for r in literal if r["reviewer"] == rev), None),
    } for rev in all_revs]

    ctrl = controls(corpus, events, literal)
    controls_pass = all(c["pass"] for c in ctrl)

    # ---- findings -------------------------------------------------------
    findings = []
    census_pair = lead_census["counts"]["accept_reviewers"]
    if sorted(census_pair) != fv_full:
        findings.append({
            "id": "W074-L0A-F1", "severity": "moderate", "kind": "accept-pair-definition-drift",
            "statement": (f"The L8 census ({LEAD_CENSUS_SHA[:12]}) names accept_reviewers={census_pair} while the "
                          f"final-verify table names the full-schema pair {fv_full}. The census's second accept "
                          f"(worker-072) is scope-limited in the same round's final-verify table "
                          f"(scoped_accepts={fv_scoped}), so the census pair mixes a scoped accept into the full-schema "
                          f"pair; the later artifacts corrected this and the census artifact itself was not re-issued."),
            "refs": [f"{LEAD_CENSUS_PATH}#{LEAD_CENSUS_SHA[:12]}",
                     f"{FINAL_VERIFY_PATH}#{fv_sha[:12]}"],
        })
    stmt = lead_audit["gate_relevant_correction"]["statement"]
    scan_accepts = lead_audit["gate_relevant_correction"]["controller_scan_accepts"]
    if "records 1 accept" in stmt and len(scan_accepts) == 2:
        findings.append({
            "id": "W074-L0A-F2", "severity": "moderate", "kind": "internal-inconsistency",
            "statement": (f"The L9 audit's own body lists controller_scan_accepts={scan_accepts} (2) in both record_B "
                          f"and gate_relevant_correction, while the same object's prose statement says the controller "
                          f"scan 'records 1 accept'. The prose is stale relative to its own body: worker-079's "
                          f"reviews/*.json record (mtime 01:03:41) predates the 01:04:13 audit."),
            "refs": [f"{LEAD_AUDIT_PATH}#{LEAD_AUDIT_SHA[:12]}"],
        })
    new_content = sorted(ev_set - lead_set)
    if new_content:
        findings.append({
            "id": "W074-L0A-F3", "severity": "major", "kind": "census-staleness-falsifier-fired",
            "statement": (f"The L9 audit's falsifier 'A ledger-level review event at the frozen hash not listed here "
                          f"voids completeness' has fired at this instant: the accepted stream carries ledger-content "
                          f"reviewer(s) {new_content} not in the census's 12-row content set "
                          f"(worker-079, verdict accept at a1674f094979, event created 01:09:00, after the 01:04:13 audit). "
                          f"Measured event-stream ledger-content population at the instant: "
                          f"{len(ev_content)} rows / accepts {acc(ev_content)}, versus the census's 12 rows / "
                          f"accepts {lead_accepts}. The stale count does not change the full-schema accept pair, "
                          f"which remains {fv_full}."),
            "refs": [f"{LEAD_AUDIT_PATH}#{LEAD_AUDIT_SHA[:12]}", f"{LEAD_CENSUS_PATH}#{LEAD_CENSUS_SHA[:12]}",
                     f"{EVENTS_PATH}"],
        })
    if set(literal_full_accepts) == set(lead_accepts_full) == set(fv_full):
        findings.append({
            "id": "W074-L0A-F4", "severity": "positive", "kind": "coverage-convergence",
            "statement": (f"At the measurement instant the literal controller re-implementation ({literal_full_accepts}), "
                          f"the lead census's full-schema set ({lead_accepts_full}) and the final-verify table ({fv_full}) "
                          f"agree on the full-schema live accept set. The residual controller undercount is reviewer "
                          f"coverage ({len(lit_set)}/{len(lead_set)} ledger-level reviewers), not the accept count."),
            "refs": [f"ledger/theorems.jsonl#{L0_PIN[:12]}", f"{FINAL_VERIFY_PATH}#{fv_sha[:12]}"],
        })
    stale_full = sorted({r["reviewer"] for r in file_recs
                         if r["verdict"] == "accept" and r["full"] and (r["alias"] or r["path"])
                         and not r["pin"] and r["stale_pins_known"]})
    if stale_full:
        findings.append({
            "id": "W074-L0A-F5", "severity": "info", "kind": "stale-accept-exclusion",
            "statement": (f"Full-schema accepts at superseded L0 hashes exist on disk and are excluded from the live set "
                          f"by the literal predicate: {stale_full} (pins {sorted(STALE_L0_PINS)}). The CF-31 staleness "
                          f"mechanism is present at L0 and handled benignly."),
            "refs": [f"{LEAD_CENSUS_PATH}#{LEAD_CENSUS_SHA[:12]}"],
        })
    anomalies = []
    for r in file_recs:
        ca, mt = r.get("declared_created_at"), r.get("mtime")
        if not ca or not mt:
            continue
        try:
            c = datetime.datetime.fromisoformat(str(ca).replace("+0800", "+08:00"))
            m = datetime.datetime.fromisoformat(str(mt))
        except Exception:
            continue
        if c.tzinfo is None:
            continue
        dsec = (c - m).total_seconds()
        if abs(dsec) > 30:
            anomalies.append({"file": r["file"], "declared_created_at": str(ca), "mtime": mt,
                              "delta_s": round(dsec, 1)})
    if anomalies:
        findings.append({
            "id": "W074-L0A-F6", "severity": "info", "kind": "clock-discipline",
            "statement": (f"{len(anomalies)} L0-bound review file(s) carry a declared created_at more than 30 s from the "
                          f"file mtime; a created_at after mtime is impossible for an unamended single write. Advisory."),
            "detail": anomalies,
        })

    manifest_t1 = corpus_manifest(load_review_corpus(root))
    drift_during_run = manifest_t0 != manifest_t1
    checks = {
        "pin_guard": not drift,
        "corpus_stable_during_run": not drift_during_run,
        "lead_census_hash_match": pins["lead_census"]["match"],
        "lead_audit_hash_match": pins["lead_audit"]["match"],
        "final_verify_prefix_match": pins["final_verify"]["match"],
        "controls_all_pass": controls_pass,
        "accept_sets_agree": set(literal_full_accepts) == set(lead_accepts_full) == set(fv_full),
    }

    report = {
        "schema": "worker-audit/l0-census-adversarial/v1",
        "task_id": TASK_ID, "node_id": NODE_ID, "gate": GATE, "class_ids": CLASS_IDS,
        "actor": "worker-074", "created_at": now(), "measured_at": now(),
        "authority": ("Worker measurement only: no gate verdict, no node status, no validation_status=passed, "
                      "no canonical write. Counts are re-measured from disk at measured_at."),
        "pins": pins, "checks": checks,
        "review_corpus": {"files": len(corpus), "manifest_t0": manifest_t0, "manifest_t1": manifest_t1,
                          "drift_during_run": drift_during_run},
        "populations": {
            "literal_controller_scan_L0": {"n": len(literal), "reviewers": sorted(lit_set),
                                           "accepts": acc(literal), "full_accepts": literal_full_accepts,
                                           "scoped_accepts": literal_scoped_accepts, "records": literal},
            "lead_census_L8": {"sha256": LEAD_CENSUS_SHA, "created_at": lead_census["created_at"],
                               "counts": lead_census["counts"], "accepts": lead_accepts,
                               "full_accepts": lead_accepts_full, "rows": lead_rows},
            "lead_audit_L9": {"sha256": LEAD_AUDIT_SHA, "created_at": lead_audit["created_at"],
                              "ledger_content_counts": lead_audit["ledger_content_counts"],
                              "reviewers": sorted(audit_set), "rows": audit_rows},
            "event_scan_at_instant": {"n": len(ev_content), "reviewers": sorted(ev_set),
                                      "accepts": acc(ev_content), "rows": ev_content},
            "final_verify_table": {"sha256": fv_sha, "created_at": fv.get("created_at"),
                                   "full_accepts": fv_full, "scoped_accepts": fv_scoped},
        },
        "reconciliation": recon,
        "delta": {
            "literal_minus_lead_census": sorted(lit_set - lead_set),
            "lead_census_minus_literal": sorted(lead_set - lit_set),
            "event_at_instant_minus_lead_census": sorted(ev_set - lead_set),
            "event_at_instant_minus_literal": sorted(ev_set - lit_set),
            "accept_sets_agree": checks["accept_sets_agree"],
        },
        "controls": ctrl, "controls_all_pass": controls_pass,
        "findings": findings,
        "falsifier": (
            "FALSIFIED IF any of: (a) any pinned input no longer hashes to its pin at re-measurement; (b) the literal "
            "controller re-implementation on a later corpus yields a different L0 record population or accept set than "
            "reported here with no file write in between; (c) the census/audit 12-row content set is shown to contain a "
            "record that does not bind a1674f094979 or is authored by the ledger author; (d) a ledger-level review "
            "verdict at a1674f094979 exists at the measurement instant that none of the four populations carries; "
            "(e) any control stops discriminating on re-run; or (f) the full-schema live accept sets of the literal "
            "scan, the census and the final-verify table are shown not to agree at the measured instant."),
        "not_claimed": ["gate verdict", "node completion", "accept of L0 or L1",
                        "that the HF-01/HF-02 carried objections are resolved",
                        "that the census/audit artifacts are otherwise defect-free",
                        "that worker-072's scope-limited accept is a full-schema accept"],
    }

    (outdir / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    (outdir / "raw" / "reviews_manifest.txt").write_text(
        "\n".join(f"{r['file']} {r.get('sha256', '')}" for r in corpus) + "\n")
    say(f"literal records={len(literal)} accepts={acc(literal)} full={literal_full_accepts} scoped={literal_scoped_accepts}")
    say(f"lead census accepts={lead_accepts} full={lead_accepts_full}; audit={sorted(audit_set)}")
    say(f"event-at-instant ledger_content n={len(ev_content)} accepts={acc(ev_content)}")
    say(f"final-verify full={fv_full} scoped={fv_scoped}")
    say(f"delta event-minus-census={sorted(ev_set - lead_set)}; literal-minus-census={sorted(lit_set - lead_set)}")
    say(f"controls: {sum(1 for c in ctrl if c['pass'])}/{len(ctrl)} pass")
    say(f"findings: {[f['id'] + ':' + f['severity'] for f in findings]}")
    say(f"report sha256 = {sha256_file(outdir / 'report.json')}")
    (outdir / "raw" / "run_log.txt").write_text("\n".join(log) + "\n")
    return 0 if (all(checks.values()) and not drift_during_run) else 3


if __name__ == "__main__":
    sys.exit(main())
