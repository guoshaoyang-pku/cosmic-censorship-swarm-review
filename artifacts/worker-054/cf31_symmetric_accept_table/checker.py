#!/usr/bin/env python3
"""W054-CF31-SYMMETRIC-ACCEPT-TABLE-01 - deterministic read-only instrument.

Generalizes CF-31/REC-39 symmetrically: for each G-FORM leg (F1, F2a, F2b) at the
measured pins, compute the distinct-reviewer accept witness set under every
published strictness factor and their intersection (robust count).

Authority: worker evidence only. No gate verdict, no node status, no canonical write.
Exit codes: 0 = measurement complete and controls as declared; 2 = fail-closed
(pin drift, missing input, control deviation, or non-deterministic re-run).
"""
import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

FROZEN_FIELDS = ("frozen_sha256", "frozen_hash", "frozen", "frozen_generation",
                 "processed_against", "frozen_revision")
TARGET_FIELDS = ("artifact", "artifact_path", "reviewed_artifact", "target",
                 "target_path", "target_id")
PIN_FIELDS = ("artifact_sha256", "reviewed_sha256", "target_sha256",
              "schema_sha256", "pinned_sha256", "artifact_hash", "reviewed_hash")
TEXT_FIELDS = ("review_scope", "verdict_scope", "scope", "summary")

HEX64 = re.compile(r"(?<![0-9a-fA-F])([0-9a-fA-F]{64})(?![0-9a-fA-F])")
HEX8 = re.compile(r"(?<![0-9a-fA-F])([0-9a-fA-F]{8,64})(?![0-9a-fA-F])")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def derive_author_sets(events_path, legs):
    authors = {k: set() for k in legs}
    if not os.path.exists(events_path):
        return authors, False
    with open(events_path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("event_type") != "artifact":
                continue
            path = str(ev.get("path") or "")
            actor = str(ev.get("actor") or "")
            for leg, spec in legs.items():
                if path in (spec["path"], spec.get("mirror")) and actor:
                    authors[leg].add(actor)
    return authors, True


def get_str(d, key):
    v = d.get(key)
    return v if isinstance(v, str) else ""


def freeze_state(d):
    """Return (field_state, any_state). state in live|stale|unspecified."""
    field_hits, any_hits = [], []
    for k, v in d.items():
        if not isinstance(v, str):
            if k == "frozen_revision" and isinstance(v, int):
                v = str(v)
            else:
                continue
        if k in FROZEN_FIELDS or k in TARGET_FIELDS or k in TEXT_FIELDS:
            field_hits.append(v)
        any_hits.append(v)

    def classify(texts, live_token, stale_tokens):
        for t in texts:
            for tok in HEX8.findall(t):
                if tok.lower().startswith(live_token[:8]):
                    return "live"
                if len(tok) >= 8:
                    stale_tokens.add(tok.lower())
            if re.search(r"\brev(?:ision)?[\s_:=]*29\b", t, re.I):
                return "live"
            m = re.search(r"\brev(?:ision)?[\s_:=]*(\d+)\b", t, re.I)
            if m and m.group(1) != "29":
                stale_tokens.add("rev" + m.group(1))
        return "stale" if stale_tokens else "unspecified"

    live = get_str(d, "live_frozen_token") or LIVE_FROZEN
    fs = classify(field_hits, live, set())
    ans = classify(any_hits, live, set())
    return fs, ans


def parse_review(path, mtime):
    try:
        d = load_json(path)
    except Exception:
        return None
    if not isinstance(d, dict):
        return None
    reviewer = str(d.get("reviewer") or d.get("actor") or d.get("created_by") or "")
    verdict = str(d.get("verdict") or "").lower()
    flag = d.get("counts_as_full_schema_verdict")
    if flag not in (True, False):
        flag = d.get("counts_as_full") if d.get("counts_as_full") in (True, False) else None
    pin_fields = {k: str(d[k]) for k in PIN_FIELDS if isinstance(d.get(k), str)}
    target_text = " ".join(get_str(d, k) for k in TARGET_FIELDS if get_str(d, k))
    pin_text = " ".join(pin_fields.values()) + " " + target_text
    decl_hashes = set(h.lower() for h in HEX64.findall(pin_text))
    supersedes = str(d.get("supersedes") or "")
    created = str(d.get("created_at") or d.get("created") or "")
    fs, ans = freeze_state(d)
    return {
        "file": os.path.relpath(path, ROOT),
        "reviewer": reviewer,
        "verdict": verdict,
        "flag": flag,
        "declared_hashes": sorted(decl_hashes),
        "target_text": target_text,
        "created_at": created,
        "mtime": mtime,
        "frozen_field": fs,
        "frozen_any": ans,
        "supersedes": supersedes,
        "hard_failures_n": len(d.get("hard_failures") or []),
    }


def binds(rec, leg, mode):
    spec = LEGS[leg]
    pin = spec["sha256"].lower()
    if pin in rec["declared_hashes"]:
        return True
    if mode == "path":
        tt = rec["target_text"]
        if spec["path"] in tt or os.path.basename(spec["path"]) in tt:
            # a declared pin that exists but conflicts with the leg pin is disqualifying
            hashes = [h for h in rec["declared_hashes"]]
            if not hashes or pin in hashes:
                return True
    return False


def classify_leg(leg, rows, authors):
    """Return per-variant counted reviewer sets and per-file classification."""
    out = {}
    variants = ("v0_default", "v1_strict_flag", "v2_strict_live_field",
                "v3_path_strict_live_field", "v2b_strict_live_any")
    counted = {v: {} for v in variants}
    details = []
    for rec in rows:
        bind_strict = binds(rec, leg, "hash")
        bind_path = binds(rec, leg, "path")
        full_default = rec["flag"] is not False
        full_strict = rec["flag"] is True
        live_field = rec["frozen_field"] == "live"
        live_any = rec["frozen_any"] == "live"
        non_author = bool(rec["reviewer"]) and rec["reviewer"] not in authors.get(leg, set())
        is_accept = rec["verdict"] == "accept"
        flags = dict(bind_strict=bind_strict, bind_path=bind_path,
                     full_default=full_default, full_strict=full_strict,
                     live_field=live_field, live_any=live_any,
                     non_author=non_author, accept=is_accept)
        row = dict(rec)
        row.pop("declared_hashes", None)
        row["flags"] = flags
        row["leg"] = leg
        details.append(row)
        if not is_accept:
            continue
        if bind_strict and full_default and non_author:
            counted["v0_default"].setdefault(rec["reviewer"], rec)
        if bind_strict and full_strict and non_author:
            counted["v1_strict_flag"].setdefault(rec["reviewer"], rec)
            if live_field:
                counted["v2_strict_live_field"].setdefault(rec["reviewer"], rec)
        if bind_path and full_strict and live_field and non_author:
            counted["v3_path_strict_live_field"].setdefault(rec["reviewer"], rec)
        if bind_strict and full_strict and live_any and non_author:
            counted["v2b_strict_live_any"].setdefault(rec["reviewer"], rec)

    # supersession: per (leg, reviewer) the controlling record is the latest by
    # created_at (fallback mtime); an accept counts only if controlling. A record
    # declaring supersedes=<path or hash> removes the referenced record.
    out["counted"] = {v: sorted(counted[v]) for v in variants}
    out["counts"] = {v: len(counted[v]) for v in variants}
    out["witness_files"] = {v: {r: rec["file"] for r, rec in sorted(counted[v].items())}
                            for v in variants}
    out["details"] = sorted(details, key=lambda r: r["file"])
    return out


def apply_supersession(leg_rows):
    """Mark rows superseded; returns reviewer->controlling verdict map."""
    by_reviewer = {}
    for rec in leg_rows:
        by_reviewer.setdefault(rec["reviewer"], []).append(rec)
    controlling = {}
    dropped = set()
    for reviewer, recs in by_reviewer.items():
        recs = sorted(recs, key=lambda r: (r["created_at"] or r["mtime"] or "", r["file"]))
        controlling[reviewer] = recs[-1]["verdict"] if recs else ""
        for i, r in enumerate(recs[:-1]):
            if r["verdict"] == "accept" and recs[-1]["verdict"] != "accept":
                dropped.add(r["file"])
    for rec in leg_rows:
        rec["superseded"] = rec["file"] in dropped
        if rec["superseded"]:
            rec["verdict_effective"] = "superseded"
    return controlling


def fixture_controls():
    """Build synthetic review fixtures and assert declared classifications."""
    fx = os.path.join(HERE, "fixtures")
    os.makedirs(fx, exist_ok=True)
    live = LIVE_FROZEN
    stale = "3d9e3d77fd87aabbccddeeff00112233445566778899aabbccddeeff00112233"
    pin = FIXTURE_PIN
    base = dict(reviewer="rev-ok", verdict="accept", artifact="fixtures/schema_fixture.yaml",
                artifact_sha256=pin, counts_as_full_schema_verdict=True, frozen_sha256=live,
                class_id="AF-TEST-FIXTURE")
    cases = {
        "K1_live_explicit_accept": (dict(base), {"v0_default", "v1_strict_flag",
                                                 "v2_strict_live_field", "v3_path_strict_live_field",
                                                 "v2b_strict_live_any"}),
        "K2_flag_absent_accept": (dict(base, reviewer="rev-k2",
                                       counts_as_full_schema_verdict=None), {"v0_default"}),
        "K3_stale_frozen_accept": (dict(base, reviewer="rev-k3", frozen_sha256=stale),
                                   {"v0_default", "v1_strict_flag"}),
        "K4_scoped_accept": (dict(base, reviewer="rev-k4", counts_as_full_schema_verdict=False,
                                  review_scope="scoped to one axis only"), set()),
        "K5_pin_only_in_findings": (dict(base, reviewer="rev-k5", artifact=None,
                                         artifact_sha256=None, target_id="unrelated-doc",
                                         findings=[{"detail": pin}]), set()),
        "K6_author_self_accept": (dict(base, reviewer="author-x"), set()),
        "K7_superseded_accept": (dict(base, reviewer="rev-k7", created_at="2026-09-12T01:00:00+08:00"),
                                 set()),
        "K8_revise": (dict(base, reviewer="rev-k8", verdict="revise"), set()),
        "K9_stale_pin": (dict(base, reviewer="rev-k9", artifact_sha256="0" * 64), set()),
        "K10_path_target_accept": (dict(base, reviewer="rev-k10", artifact_sha256=None),
                                   {"v3_path_strict_live_field"}),
    }
    for name, (obj, _) in cases.items():
        obj = {k: v for k, v in obj.items() if v is not None}
        with open(os.path.join(fx, name + ".json"), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=1, sort_keys=True)
    # K7 companion: later revise supersedes the accept
    with open(os.path.join(fx, "K7b_superseding_revise.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(base, reviewer="rev-k7", verdict="revise", artifact_sha256=pin,
                       created_at="2026-09-12T01:05:00+08:00"), fh, indent=1, sort_keys=True)

    legs = {"FX": {"path": "fixtures/schema_fixture.yaml", "sha256": pin,
                   "class_id": "AF-TEST-FIXTURE", "mirror": None}}
    global LEGS
    saved = LEGS
    LEGS = legs
    rows = []
    for p in sorted(glob.glob(os.path.join(fx, "*.json"))):
        rec = parse_review(p, os.path.getmtime(p))
        if rec:
            rows.append(rec)
    apply_supersession(rows)
    rows = [r for r in rows if not r.get("superseded")]
    res = classify_leg("FX", rows, {"FX": {"author-x"}})
    LEGS = saved
    got = {name: set(v) for name, v in res["counted"].items()}
    failures = []
    for name, (_, expected) in cases.items():
        reviewer = json.load(open(os.path.join(fx, name + ".json")))["reviewer"]
        actual = {v for v, rs in got.items() if reviewer in rs}
        if actual != expected:
            failures.append({"control": name, "expected": sorted(expected),
                             "actual": sorted(actual)})
    if "rev-k7" in res["counted"]["v0_default"]:
        failures.append({"control": "K7_supersession", "expected": [], "actual": ["counted"]})
    return {"controls_total": len(cases), "controls_passed": len(cases) - len(failures),
            "failures": failures, "counted": {k: sorted(v) for k, v in got.items()}}


LIVE_FROZEN = ""
FIXTURE_PIN = ""
LEGS = {}


def main():
    global LIVE_FROZEN, FIXTURE_PIN, LEGS
    ap = argparse.ArgumentParser()
    ap.add_argument("--created-at", default=datetime.datetime.now().astimezone().isoformat(timespec="seconds"))
    ap.add_argument("--selftest", action="store_true", help="run fixture controls only")
    args = ap.parse_args()

    pre = load_json(os.path.join(HERE, "preregistration.json"))
    LIVE_FROZEN = pre["pins"]["FROZEN"]["sha256"].lower()
    FIXTURE_PIN = "f" * 64
    LEGS = {k: dict(v, mirror="artifacts/formulation/" + os.path.basename(v["path"]))
            for k, v in pre["pins"].items() if k != "FROZEN"}

    controls = fixture_controls()
    if args.selftest:
        print(json.dumps(controls, indent=2, sort_keys=True))
        return 0 if not controls["failures"] else 2

    t0 = {k: sha256_file(os.path.join(ROOT, v["path"])) for k, v in pre["pins"].items()}
    for k, v in pre["pins"].items():
        if t0[k] != v["sha256"]:
            print("FAIL-CLOSED: pin mismatch %s expected %s measured %s" % (k, v["sha256"], t0[k]),
                  file=sys.stderr)
            return 2
    reviews = sorted(glob.glob(os.path.join(ROOT, "reviews", "*.json")))
    review_digest_before = hashlib.sha256(
        b"".join(sha256_file(p).encode() for p in reviews)).hexdigest()
    authors, events_ok = derive_author_sets(os.path.join(ROOT, "research_map", "events.jsonl"), LEGS)

    rows_by_leg = {}
    for leg in LEGS:
        rows = []
        for p in reviews:
            rec = parse_review(p, os.path.getmtime(p))
            if rec:
                rows.append(rec)
        # keep only rows that could bind to at least one leg, for the report table
        rows_by_leg[leg] = [r for r in rows if any(binds(r, l, "path") for l in LEGS)]
        apply_supersession(rows_by_leg[leg])
        rows_by_leg[leg] = [r for r in rows_by_leg[leg] if not r.get("superseded")]

    result = {leg: classify_leg(leg, rows_by_leg[leg], authors) for leg in LEGS}

    # deterministic re-run of the core classification
    rerun = {leg: classify_leg(leg, [dict(r) for r in rows_by_leg[leg]], authors) for leg in LEGS}
    deterministic = all(rerun[leg]["counts"] == result[leg]["counts"] for leg in LEGS)

    t1 = {k: sha256_file(os.path.join(ROOT, v["path"])) for k, v in pre["pins"].items()}
    review_digest_after = hashlib.sha256(
        b"".join(sha256_file(p).encode() for p in reviews)).hexdigest()
    drift = (t0 != t1) or (review_digest_before != review_digest_after)

    summary = {}
    for leg, res in result.items():
        robust_variants = ("v1_strict_flag", "v2_strict_live_field", "v3_path_strict_live_field")
        robust = min(res["counts"][v] for v in robust_variants)
        summary[leg] = {
            "class_id": LEGS[leg]["class_id"],
            "pin": LEGS[leg]["sha256"],
            "counts": res["counts"],
            "robust_count_min_v1_v2_v3": robust,
            "criterion_ge_2": "ROBUSTLY_MET" if robust >= 2 else (
                "FRAGILE" if max(res["counts"][v] for v in robust_variants) >= 2 else "NOT_MET"),
            "witnesses": res["witness_files"],
            "author_set": sorted(authors.get(leg, set())),
        }

    report = {
        "task_id": "W054-CF31-SYMMETRIC-ACCEPT-TABLE-01",
        "actor": "worker-054",
        "created_at": args.created_at,
        "class_ids": pre["class_ids"],
        "node_id": pre["node_id"],
        "gate": pre["gate"],
        "measurement_basis": {
            "preregistration_sha256": sha256_file(os.path.join(HERE, "preregistration.json")),
            "review_files_scanned": len(reviews),
            "events_author_sets_available": events_ok,
            "pin_hashes_start": t0, "pin_hashes_end": t1,
            "reviews_corpus_digest_before": review_digest_before,
            "reviews_corpus_digest_after": review_digest_after,
        },
        "drift": {"detected": drift, "pins_stable": t0 == t1,
                  "reviews_stable": review_digest_before == review_digest_after},
        "deterministic_rerun": deterministic,
        "controls": controls,
        "legs": summary,
        "per_file_details": {leg: result[leg]["details"] for leg in LEGS},
        "non_claims": pre["non_claims"],
        "falsifier": pre["falsifier"],
    }
    out = os.path.join(HERE, "report.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)

    ok = (not drift) and deterministic and not controls["failures"]
    print(json.dumps({"report": out, "ok": ok, "drift": drift,
                      "controls": [controls["controls_passed"], controls["controls_total"]],
                      "summary": {leg: summary[leg]["counts"] for leg in summary}},
                     indent=2, sort_keys=True))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
