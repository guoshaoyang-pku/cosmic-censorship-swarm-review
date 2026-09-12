#!/usr/bin/env python3
"""W028 — supersession-aware review-accept census (bounded, independent measurement).

Task (one class-bound task, worker-028): at the controller-measured canonical hashes,
census every review file that binds to those hashes, and recompute the "distinct accept
reviewers" count after honouring explicit withdrawal/supersession and same-reviewer
later-verdict evidence. The raw advisory scan (research_map/astra_lifecycle.py
review_coverage) counts every file independently; this census reports raw vs corrected
counts and every discrepancy with file-level hash evidence.

Authority: worker measurement only. No gate verdict, no node status, no validation_status,
no ledger/schema write. Nothing outside artifacts/worker-028/ is written.

Class binding: AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH
(targets F0, F1, F2a, F2b, L0, L1 and the other measured nodes).

Usage:
  python3 artifacts/worker-028/review_accept_census/run_accept_census_028.py \
      --out artifacts/worker-028/review_accept_census/accept_census_028.json
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
CTRL = ROOT / "research_map" / "astra_lifecycle.py"
MAP = ROOT / "research_map" / "research_map.json"
A1_MATRIX = ROOT / "reviews" / "A1-rebind-coverage.json"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]


def now_iso() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_controller():
    spec = importlib.util.spec_from_file_location("astra_lifecycle_w028census", CTRL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parse_ts(value):
    if not isinstance(value, str):
        return None
    s = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=CST)
    return dt


def order_key(entry):
    """Ordering key for supersession: (created_at epoch, mtime). Clock skew (CF-14) is why
    the explicit supersedes pointer is the primary rule and this key is the fallback."""
    return (entry.get("created_at_epoch") or 0.0, entry.get("mtime") or 0.0)


def basename(value):
    if not isinstance(value, str):
        return None
    return os.path.basename(value)


def supersedes_targets(d):
    """File basenames named by a review's supersedes/withdraws field."""
    out = []
    sup = d.get("supersedes") or d.get("withdraws") or d.get("amends")
    items = sup if isinstance(sup, list) else [sup]
    for it in items:
        if isinstance(it, str):
            b = basename(it)
            if b:
                out.append(b)
        elif isinstance(it, dict):
            for k in ("path", "file", "review", "review_path"):
                b = basename(it.get(k))
                if b:
                    out.append(b)
    return out


def scan_corpus(reviews_dir: Path, measured: dict, AL) -> list:
    """Replicates AL.review_coverage's file loop, returning rich hash-bound entries.

    The reimplementation is cross-checked against AL.review_coverage on the real corpus
    (check SELF-SCAN-MATCH); on the planted corpus it is the only evaluator.
    """
    entries = []
    for rp in sorted(reviews_dir.glob("*.json")):
        try:
            d = json.loads(rp.read_text())
        except Exception:
            continue
        v = str(d.get("verdict", "")).lower()
        if v not in AL.VERDICT_KINDS:
            continue
        reviewer = str(d.get("reviewer") or d.get("actor") or "?")
        full = d.get("counts_as_full_schema_verdict") is not False
        pins = AL._explicit_pins(d)
        for t in sorted(AL._targets_in_review(d)):
            if t not in measured:
                continue
            h = (measured.get(t, {}).get("sha256") or "")
            if not h:
                continue
            if any(p.startswith(h[:12]) or h.startswith(p[:12]) for p in pins):
                entries.append({
                    "file": rp.name,
                    "rel_path": str(rp.relative_to(ROOT)) if rp.is_relative_to(ROOT) else str(rp),
                    "sha256": sha256_file(rp),
                    "bytes": rp.stat().st_size,
                    "mtime": rp.stat().st_mtime,
                    "target": t,
                    "reviewer": reviewer,
                    "verdict": v,
                    "score": d.get("score"),
                    "counts_as_full_schema_verdict": full,
                    "created_at": d.get("created_at"),
                    "created_at_parsed": parse_ts(d.get("created_at")).isoformat() if parse_ts(d.get("created_at")) else "",
                    "created_at_epoch": parse_ts(d.get("created_at")).timestamp() if parse_ts(d.get("created_at")) else 0.0,
                    "pin_matched": h[:12],
                    "supersedes": d.get("supersedes"),
                    "supersedes_files": supersedes_targets(d),
                    "assignment_ref": (d.get("assignment_ref") or "")[:300],
                    "reviewer_self_withdrawal_text": bool(
                        re.search(r"withdraw", json.dumps(d.get("supersedes") or "") + " " +
                                  str(d.get("assignment_ref") or "") + " " + str(d.get("supersedes") or ""),
                                  re.I)),
                })
    return entries


def resolve_supersessions(entries: list) -> tuple:
    """Return (withdrawn_by_file, effective_verdict_by_file)."""
    by_name = {e["file"]: e for e in entries}
    withdrawn = {}

    # Rule S1 (primary): explicit supersedes/withdraws pointer to an accept by the same
    # reviewer on the same target whose replacement is not an accept.
    for e in entries:
        for name in e["supersedes_files"]:
            a = by_name.get(name)
            if not a or a["file"] == e["file"]:
                continue
            if (a["verdict"] == "accept" and e["verdict"] != "accept"
                    and a["reviewer"] == e["reviewer"] and a["target"] == e["target"]):
                withdrawn[a["file"]] = {
                    "rule": "explicit-supersedes-path",
                    "withdrawal_file": e["file"],
                    "withdrawal_file_sha256": e["sha256"],
                    "withdrawal_verdict": e["verdict"],
                    "reason": json.dumps(e.get("supersedes"))[:400],
                }

    # Rule S2 (fallback): same reviewer + same target + same measured hash, a later
    # full-schema non-accept verdict supersedes an earlier accept. Ordering uses
    # created_at with mtime as tiebreak; treated as advisory because of known clock skew.
    groups = {}
    for e in entries:
        groups.setdefault((e["target"], e["reviewer"]), []).append(e)
    for (_t, _r), g in groups.items():
        for a in g:
            if a["verdict"] != "accept" or a["file"] in withdrawn:
                continue
            later = [e for e in g
                     if e["file"] != a["file"] and e["verdict"] != "accept"
                     and e["counts_as_full_schema_verdict"]
                     and order_key(e) > order_key(a)]
            if later:
                w = sorted(later, key=order_key)[0]
                withdrawn[a["file"]] = {
                    "rule": "same-reviewer-later-non-accept",
                    "withdrawal_file": w["file"],
                    "withdrawal_file_sha256": w["sha256"],
                    "withdrawal_verdict": w["verdict"],
                    "reason": "later full-schema non-accept verdict by the same reviewer at the same target",
                }

    effective = {e["file"]: ("withdrawn" if e["file"] in withdrawn else e["verdict"]) for e in entries}
    return withdrawn, effective


def raw_and_corrected(entries: list) -> dict:
    withdrawn, effective = resolve_supersessions(entries)
    out = {}
    for e in entries:
        t = e["target"]
        c = out.setdefault(t, {
            "raw_accept_reviewers": set(), "raw_accept_files": [],
            "corrected_accept_reviewers": set(), "corrected_accept_files": [],
            "withdrawn_accepts": [], "verdicts": [],
        })
        c["verdicts"].append({"file": e["file"], "reviewer": e["reviewer"], "verdict": e["verdict"],
                              "score": e.get("score"), "counts_as_full_schema_verdict": e["counts_as_full_schema_verdict"],
                              "created_at": e.get("created_at"), "effective": effective[e["file"]]})
        if e["verdict"] == "accept" and e["counts_as_full_schema_verdict"]:
            c["raw_accept_reviewers"].add(e["reviewer"])
            c["raw_accept_files"].append(e["file"])
            if effective[e["file"]] == "accept":
                c["corrected_accept_reviewers"].add(e["reviewer"])
                c["corrected_accept_files"].append(e["file"])
    for e in entries:
        if e["file"] in withdrawn and e["verdict"] == "accept":
            w = dict(withdrawn[e["file"]])
            w.update(target=e["target"], reviewer=e["reviewer"], withdrawn_file=e["file"],
                     withdrawn_file_sha256=e["sha256"], withdrawn_verdict=e["verdict"],
                     withdrawn_created_at=e.get("created_at"), raw_counts_as_accept=True)
            out[e["target"]]["withdrawn_accepts"].append(w)
    for t, c in out.items():
        for k in ("raw_accept_reviewers", "corrected_accept_reviewers"):
            c[k] = sorted(c[k])
        for k in ("raw_accept_files", "corrected_accept_files", "withdrawn_accepts", "verdicts"):
            c[k] = sorted(c[k], key=lambda x: (str(x.get("file") if isinstance(x, dict) else x)))
    return out


def read_a1_matrix():
    if not A1_MATRIX.is_file():
        return None
    try:
        d = json.loads(A1_MATRIX.read_text())
    except Exception:
        return None
    out = {}
    for t, c in (d.get("coverage") or {}).items():
        out[t] = {
            "measured_sha256": c.get("measured_sha256"),
            "accept_at_measured_hash": [a.get("reviewer") for a in c.get("accept_at_measured_hash", [])],
            "independent_reviewers_at_measured_hash": c.get("independent_reviewers_at_measured_hash"),
            "two_independent_verdicts": c.get("two_independent_verdicts"),
        }
    return {"path": "reviews/A1-rebind-coverage.json", "sha256": sha256_file(A1_MATRIX),
            "measured_at": d.get("measured_at"), "actor": d.get("actor"), "targets": out}


def read_gate_audit(map_obj):
    cga = (map_obj or {}).get("controller_gate_audit") or {}
    out = {}
    for gate, rec in cga.items():
        reason = rec.get("reason", "")
        hits = re.findall(r"(F0|F1|F2a|F2b|L0|L1) \[(\d+) distinct accept reviewer\(s\)(?: \['([^']*)'\])?\]", reason)
        cites = {h[0]: {"count": int(h[1]), "reviewers": [x for x in h[2].split("', '") if x]} for h in hits}
        loose = re.findall(r"(\d+) distinct accept reviewer\(s\)(?: \['([^']*)'\])?", reason)
        if not cites and loose:
            cited = [x for x in loose[0][1].split("', '") if x]
            if cited:
                cites["_gate_level"] = {"count": int(loose[0][0]), "reviewers": cited}
        out[gate] = {"checked_at": rec.get("checked_at"), "distinct_accept_citations": cites, "reason": reason}
    return out


def run_controls(AL) -> dict:
    ctrl_dir = HERE / "controls"
    spec = json.loads((ctrl_dir / "expected.json").read_text())
    reviews_dir = ctrl_dir / "reviews"
    if reviews_dir.exists():
        shutil.rmtree(reviews_dir)
    reviews_dir.mkdir(parents=True, exist_ok=True)
    for fx in spec["fixtures"]:
        (ctrl_dir / fx["file"].split("controls/", 1)[1]).write_text(json.dumps(fx["body"], indent=1))
    entries = scan_corpus(reviews_dir, spec["measured"], AL)
    cens = raw_and_corrected(entries)
    got_raw = {t: c["raw_accept_reviewers"] for t, c in cens.items()}
    got_corr = {t: c["corrected_accept_reviewers"] for t, c in cens.items()}
    got_withdrawn = sorted([{"target": c["target"] if "target" in c else t,
                             "reviewer": c["reviewer"], "withdrawn_file": c["withdrawn_file"],
                             "rule": c["rule"]}
                            for t, cc in cens.items() for c in cc["withdrawn_accepts"]],
                           key=lambda x: x["withdrawn_file"])
    exp = spec["expected"]
    exp_withdrawn = sorted(exp["withdrawn"], key=lambda x: x["withdrawn_file"])
    checks = [
        {"id": "C-RAW", "expected": exp["raw_accept_reviewers"], "observed": got_raw,
         "ok": got_raw == exp["raw_accept_reviewers"]},
        {"id": "C-CORRECTED", "expected": exp["corrected_accept_reviewers"], "observed": got_corr,
         "ok": got_corr == exp["corrected_accept_reviewers"]},
        {"id": "C-WITHDRAWN", "expected": exp_withdrawn, "observed": got_withdrawn,
         "ok": got_withdrawn == exp_withdrawn},
    ]
    scoped = sorted([e["file"] for e in entries
                     if e["verdict"] == "accept" and not e["counts_as_full_schema_verdict"]])
    scanned_files = sorted({e["file"] for e in entries})
    pinmiss_excluded = "c4-superseded-hash-accept.json" not in scanned_files
    checks.append({"id": "C-SCOPED", "expected": exp["excluded"]["scoped"], "observed": scoped,
                   "ok": scoped == sorted(exp["excluded"]["scoped"])})
    checks.append({"id": "C-PIN-MISMATCH-EXCLUDED", "expected": exp["excluded"]["pin_mismatch"],
                   "observed": [f for f in scanned_files if f.startswith("c4-")],
                   "ok": pinmiss_excluded and not [f for f in scanned_files if f.startswith("c4-")]})
    cross = {"r-c8": {"F1": "accept" if "r-c8" in got_corr.get("F1", []) else "missing"}}
    checks.append({"id": "C-CROSS-TARGET", "expected": exp["cross_target_control"], "observed": cross,
                   "ok": cross == exp["cross_target_control"]})
    return {"pre_registered_at": spec["created_at"], "reviews_dir": str(reviews_dir.relative_to(ROOT)),
            "n_fixture_files": len(spec["fixtures"]), "checks": checks,
            "passed": all(c["ok"] for c in checks)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "accept_census_028.json"))
    ap.add_argument("--reviews-dir", default="reviews")
    a = ap.parse_args()
    outp = Path(a.out)
    if not outp.is_absolute():
        outp = (ROOT / outp).resolve()
    out_rel = str(outp.relative_to(ROOT))

    AL = load_controller()
    map_sha_start, ctrl_sha_start = sha256_file(MAP), sha256_file(CTRL)
    map_obj = json.loads(MAP.read_text())
    measured = AL.measured_hashes(map_obj)
    measured_public = {t: {"artifact": v.get("artifact"), "sha256": v.get("sha256"),
                           "bytes": v.get("bytes"), "kind": v.get("kind")}
                       for t, v in sorted(measured.items())}

    reviews_dir = ROOT / a.reviews_dir
    scan_start_epoch = datetime.now(CST).timestamp()
    entries = scan_corpus(reviews_dir, measured, AL)

    # Self-check: our file loop must reproduce the controller's own advisory scan exactly.
    ctrl_raw = AL.review_coverage(measured)
    my_raw = raw_and_corrected(entries)
    raw_match, raw_detail = True, {}
    for t in sorted(measured):
        c = ctrl_raw.get(t, {})
        raw_detail[t] = {
            "controller_scan_accept_reviewers": sorted(c.get("distinct_accept_reviewers", [])),
            "census_raw_accept_reviewers": my_raw.get(t, {}).get("raw_accept_reviewers", []),
            "controller_scan_bound_verdicts": len(c.get("verdicts", [])),
            "census_bound_verdicts": len(my_raw.get(t, {}).get("verdicts", [])),
        }
        if raw_detail[t]["controller_scan_accept_reviewers"] != raw_detail[t]["census_raw_accept_reviewers"]:
            raw_match = False
        if raw_detail[t]["controller_scan_bound_verdicts"] != raw_detail[t]["census_bound_verdicts"]:
            raw_match = False

    controls = run_controls(AL)

    # Consumers of the raw scan: the audit lead's A1 binding-coverage matrix and the
    # controller's prose gate audit in the map.
    a1 = read_a1_matrix()
    gate_audit = read_gate_audit(map_obj)

    findings = []
    for t in sorted(my_raw):
        c = my_raw[t]
        if c["withdrawn_accepts"]:
            for w in c["withdrawn_accepts"]:
                findings.append({
                    "id": f"W028-CENSUS-{t}-{w['reviewer']}",
                    "severity": "major" if t in ("F1", "F2a", "F2b") else "info",
                    "class_ids": CLASS_IDS,
                    "target": t,
                    "statement": (f"raw advisory scan counts {w['reviewer']}'s accept in {w['withdrawn_file']} "
                                  f"at measured {t} hash, but the same reviewer withdrew it in "
                                  f"{w['withdrawal_file']} ({w['rule']}); corrected full-schema accepts for {t}: "
                                  f"{len(c['corrected_accept_reviewers'])} (raw {len(c['raw_accept_reviewers'])})."),
                    "evidence_refs": [
                        f"reviews/{w['withdrawn_file']}#{w['withdrawn_file_sha256'][:12]}",
                        f"reviews/{w['withdrawal_file']}#{w['withdrawal_file_sha256'][:12]}",
                        f"research_map/astra_lifecycle.py#{ctrl_sha_start[:12]}:177-213",
                        f"research_map/research_map.json#{map_sha_start[:12]}",
                    ],
                    "withdrawal_reason": w.get("reason"),
                })
    # Consumer propagation: does the audit-lead matrix carry the withdrawn accept?
    a1_propagation = []
    if a1:
        for t, rec in a1["targets"].items():
            raw = my_raw.get(t, {}).get("raw_accept_reviewers", [])
            corr = my_raw.get(t, {}).get("corrected_accept_reviewers", [])
            if rec["accept_at_measured_hash"] == raw and raw != corr:
                a1_propagation.append({"target": t, "a1_accepts": rec["accept_at_measured_hash"],
                                       "corrected_accepts": corr, "a1_two_independent_verdicts": rec["two_independent_verdicts"]})
    ga_propagation = []
    if gate_audit:
        withdrawn_reviewers = {w["reviewer"] for c in my_raw.values() for w in c["withdrawn_accepts"]}
        for gate, rec in gate_audit.items():
            for t, cit in rec["distinct_accept_citations"].items():
                if t == "_gate_level":
                    bad = sorted(set(cit["reviewers"]) & withdrawn_reviewers)
                    if bad:
                        ga_propagation.append({"gate": gate, "target": "_gate_level",
                                               "cited_reviewers": cit["reviewers"],
                                               "withdrawn_reviewers": bad})
                    continue
                raw = my_raw.get(t, {}).get("raw_accept_reviewers", [])
                corr = my_raw.get(t, {}).get("corrected_accept_reviewers", [])
                if cit["reviewers"] == raw and raw != corr:
                    ga_propagation.append({"gate": gate, "target": t, "cited_reviewers": cit["reviewers"],
                                           "corrected_reviewers": corr})
    if a1_propagation or ga_propagation:
        findings.append({
            "id": "W028-CENSUS-PROPAGATION",
            "severity": "major",
            "class_ids": CLASS_IDS,
            "statement": ("the withdrawn accept propagates into downstream accept-count consumers: "
                          f"A1 matrix {json.dumps(a1_propagation)}; controller gate audit {json.dumps(ga_propagation)}. "
                          "Consumers must count the reviewer's latest file at the same hash, not every file."),
            "evidence_refs": ([f"reviews/A1-rebind-coverage.json#{a1['sha256'][:12]}"] if a1 else []) +
                             [f"research_map/research_map.json#{map_sha_start[:12]}"],
        })
    if a1:
        sem = [{"target": t, "two_independent_verdicts": r["two_independent_verdicts"],
                "corrected_accepts": my_raw.get(t, {}).get("corrected_accept_reviewers", []),
                "independent_reviewers": r["independent_reviewers_at_measured_hash"]}
               for t, r in a1["targets"].items()
               if r["two_independent_verdicts"] and not my_raw.get(t, {}).get("corrected_accept_reviewers")]
        if sem:
            findings.append({
                "id": "W028-CENSUS-FIELD-SEMANTICS",
                "severity": "minor",
                "class_ids": CLASS_IDS,
                "statement": ("A1 matrix field two_independent_verdicts is true where corrected full-schema accepts are zero: "
                              f"{json.dumps(sem)}. The field counts distinct reviewers present at the hash, not accepting "
                              "verdicts; qualify it before citing it as accept coverage."),
                "evidence_refs": [f"reviews/A1-rebind-coverage.json#{a1['sha256'][:12]}"],
            })

    map_sha_end, ctrl_sha_end = sha256_file(MAP), sha256_file(CTRL)
    review_hashes = {e["rel_path"]: e["sha256"] for e in entries}
    review_hashes_now = {str(p.relative_to(ROOT)): sha256_file(p) for p in sorted(reviews_dir.glob("*.json"))}
    bound_changed = sorted([k for k, v in review_hashes.items() if review_hashes_now.get(k) != v])
    unbound_files = sorted(set(review_hashes_now) - set(review_hashes))
    new_since_scan = sorted([k for k in review_hashes_now
                             if (ROOT / k).stat().st_mtime > scan_start_epoch])
    stable_bound = not bound_changed
    snapshot_valid = raw_match and controls["passed"] and stable_bound

    artifact = {
        "schema": "worker-028/review-accept-census/v1",
        "artifact_id": f"w028-review-accept-census-{now_iso()}",
        "actor": "worker-028",
        "created_at": now_iso(),
        "node_id": ["F0", "F1", "F2a", "F2b", "L0", "L1"],
        "gate": ["G-FORM", "G-AUDIT", "G-F0", "G-LIT"],
        "class_ids": CLASS_IDS,
        "scope": ("supersession-aware recount of full-schema review accepts bound to the controller-measured "
                  "canonical hashes; schema content, quantifiers and physics are NOT re-derived"),
        "authority": "worker measurement only; no gate verdict, no node status, no validation_status, no file write outside artifacts/worker-028/",
        "non_claims": [
            "not a gate verdict and not a node completion",
            "not a re-review of any schema's content",
            "raw counts are the controller scan reproduced exactly; corrected counts apply withdrawal/supersession evidence",
            "clock-skew caveat: implicit same-reviewer ordering is advisory; explicit supersedes pointers are primary",
        ],
        "inputs": {
            "research_map/research_map.json": map_sha_start,
            "research_map/research_map.json@end_of_run": map_sha_end,
            "research_map/astra_lifecycle.py": ctrl_sha_start,
            "research_map/astra_lifecycle.py@end_of_run": ctrl_sha_end,
            "reviews_dir": str(reviews_dir.relative_to(ROOT)),
            "review_files_bound": review_hashes,
            "a1_matrix": {"path": a1["path"], "sha256": a1["sha256"], "measured_at": a1.get("measured_at")} if a1 else None,
            "gate_audit_checked_at": {g: r["checked_at"] for g, r in (gate_audit or {}).items()},
        },
        "method": {
            "raw_scan": "research_map/astra_lifecycle.py:176-213 review_coverage(): every reviews/*.json with a verdict whose explicit pin matches a measured hash counts independently",
            "correction_rules": {
                "S1": "explicit supersedes/withdraws pointer: same reviewer, same target, withdrawn verdict accept, replacement verdict != accept",
                "S2": "fallback: same reviewer + same target + same measured hash, a later full-schema non-accept verdict supersedes an earlier accept (created_at, mtime tiebreak; advisory under clock skew)",
                "counts_as_full_schema_verdict=false": "excluded from accept counts by the raw scan already",
                "pin_mismatch": "review bound to a non-measured hash is excluded by the raw scan already",
            },
        },
        "measured_hashes": measured_public,
        "targets": my_raw,
        "self_check_scan_match": {"ok": raw_match, "detail": raw_detail,
                                   "note": "census file loop must reproduce the controller scan exactly on the real corpus"},
        "consumers": {
            "a1_rebind_coverage": a1,
            "controller_gate_audit_citations": gate_audit,
            "propagation": {"a1": a1_propagation, "gate_audit": ga_propagation},
        },
        "controls": controls,
        "findings": findings,
        "stability": {"map_sha256_start": map_sha_start, "map_sha256_end": map_sha_end,
                      "map_changed_during_run": map_sha_start != map_sha_end,
                      "scanner_changed_during_run": ctrl_sha_start != ctrl_sha_end,
                      "bound_review_files_changed": bound_changed,
                      "unbound_review_files": unbound_files,
                      "new_review_files_since_scan": new_since_scan,
                      "scan_started_at": datetime.fromtimestamp(scan_start_epoch, CST).isoformat(timespec="seconds"),
                      "snapshot_valid": snapshot_valid, "checked_at": now_iso()},
        "falsifier": ("Re-run at a later wall clock: the census is falsified if (a) any counted accept has a later "
                      "same-reviewer, same-target, same-hash non-accept file that this census did not mark withdrawn; "
                      "(b) any withdrawal this census asserts is contradicted by the named files' bytes at the recorded "
                      "sha256; (c) the census's raw counts no longer equal research_map/astra_lifecycle.py review_coverage "
                      "at the same measured hashes; (d) the planted controls do not reproduce controls/expected.json; "
                      "(e) research_map/research_map.json or the scanner changes hash without re-issue."),
        "checkpoint_inputs": {
            "artifact_path": out_rel,
            "map_sha256": map_sha_end,
            "scanner_sha256": ctrl_sha_end,
            "review_file_hashes": review_hashes,
        },
    }
    outp.write_text(json.dumps(artifact, indent=1, sort_keys=True, default=str))
    print(json.dumps({
        "artifact": out_rel,
        "artifact_sha256": sha256_file(outp),
        "map_sha256": map_sha_end,
        "self_check_scan_match": raw_match,
        "controls_passed": controls["passed"],
        "corrected_accept_reviewers": {t: c["corrected_accept_reviewers"] for t, c in sorted(my_raw.items())},
        "raw_accept_reviewers": {t: c["raw_accept_reviewers"] for t, c in sorted(my_raw.items())},
        "withdrawn_accepts": [{"target": t, "reviewer": w["reviewer"], "file": w["withdrawn_file"],
                               "rule": w["rule"]} for t, c in sorted(my_raw.items()) for w in c["withdrawn_accepts"]],
        "findings": [{"id": f["id"], "severity": f["severity"], "statement": f["statement"][:300]} for f in findings],
        "snapshot_valid": snapshot_valid,
        "stability": {"map_changed_during_run": map_sha_start != map_sha_end,
                      "bound_review_files_changed": bound_changed,
                      "new_review_files_since_scan": new_since_scan},
    }, indent=1, default=str))
    return 0 if snapshot_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
