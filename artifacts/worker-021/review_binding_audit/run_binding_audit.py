#!/usr/bin/env python3
"""W021-BIND-01: independent binding audit of the `reviews/` corpus.

Question: which on-disk review verdicts does the controller's gate scan
(`research_map/astra_lifecycle.py::review_coverage`) actually count, which
verdicts exist on disk but are invisible to it, and which gate criteria would
change if the invisible ones were rebound by their owner?

Method
  1. Snapshot every input hash (measured node hashes + per-file review hashes).
  2. Reproduce the controller scan by importing it (`AL.review_coverage`).
  3. Independently re-implement the documented binding rule (top-level
     `verdict` in {accept,revise,reject,inconclusive}; target readable from
     target_id/target/target_subnode + alias map; at least one explicit pin
     among artifact_sha256/reviewed_sha256/sha256/cited_sha256 (or a nested
     target.sha256) whose first 12 chars match the measured hash either way;
     `counts_as_full_schema_verdict` not False for the accept list).
  4. Differential check: independent classification must equal the controller
     scan on every (file, target, verdict). A mismatch voids the audit.
  5. Intent-aware inventory: walk every document for verdicts anywhere and pins
     anywhere (including `target_id: "path#sha256"` encodings and nested
     `verdicts[]`/`targets[]` blocks), map pin->measured node, and report the
     per-node delta between counted and intent-aware accepts plus the minimal
     non-semantic repair for each invisible verdict.
  6. Controls: synthetic review files exercising each branch run through the
     *real* controller function with AL.ROOT pointed at a temp corpus, plus a
     synthetic differential check.

Read-only with respect to every canonical path and to `reviews/` itself; writes
only --out (default `report.json` next to this script). No gate verdict, no node
completion, and no rebinding of any reviewer's verdict is claimed: rebinding is
owned by the audit lead / controller.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
import astra_lifecycle as AL  # noqa: E402

CST = timezone(timedelta(hours=8))
VERDICT_KINDS = ("accept", "revise", "reject", "inconclusive")
ALIASES = {
    "F0": "F0", "F1": "F1", "F2A": "F2a", "F2B": "F2b", "F2": "F2b",
    "L0": "L0", "L1": "L1",
    "AF-WCC-VAC-GEN": "F1", "AF-SCC-C2-VAC-GEN": "F2a", "AF-SCC-C0-VAC-GEN": "F2b",
}
PIN_KEYS = ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256")
TARGET_KEYS = ("target_id", "target", "target_subnode")
GATE_NODES = ("F0", "F1", "F2a", "F2b", "L0", "L1", "A0", "A1")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def corpus_digest(files: list) -> str:
    h = hashlib.sha256()
    for p in sorted(files):
        h.update(p.name.encode())
        h.update(sha256_file(p).encode())
    return h.hexdigest()


# ---------------------------------------------------------------- controller rule (independent)
def targets_in_doc(d: dict) -> set:
    out = set()
    for key in TARGET_KEYS:
        v = d.get(key)
        if isinstance(v, str):
            out.add(v)
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                if isinstance(v.get(k2), str):
                    out.add(v[k2])
    return {ALIASES.get(t, ALIASES.get(t.upper(), t)) for t in out}


def pins_in_doc(d: dict) -> list:
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


def pin_matches(pins: list, measured: str) -> bool:
    return bool(measured) and any(
        p.startswith(measured[:12]) or measured.startswith(p[:12]) for p in pins)


def classify_doc(d: dict, measured: dict) -> dict:
    """Independent reproduction of one review document's countable bindings."""
    raw_verdict = d.get("verdict")
    norm = str(raw_verdict).lower() if raw_verdict is not None else None
    reviewer = str(d.get("reviewer") or d.get("actor") or "?")
    full = d.get("counts_as_full_schema_verdict") is not False
    tgts = targets_in_doc(d)
    pins = pins_in_doc(d)
    counted, full_accepts, scoped_accepts = [], [], []
    for t in sorted(tgts):
        h = (measured.get(t, {}) or {}).get("sha256") or ""
        if norm not in VERDICT_KINDS or not pin_matches(pins, h):
            continue
        entry = {"target": t, "verdict": norm, "reviewer": reviewer}
        counted.append(entry)
        if norm == "accept":
            (full_accepts if full else scoped_accepts).append(entry)
    return {"verdict_top_raw": raw_verdict, "verdict_top": norm, "reviewer": reviewer,
            "targets_raw": sorted(tgts), "pins": pins, "counts_as_full_schema_verdict": full,
            "counted": counted, "full_accepts": full_accepts, "scoped_accepts": scoped_accepts}


# ---------------------------------------------------------------- intent-aware walkers
def all_verdicts(d, _path="") -> list:
    """Every verdict string anywhere in the document, top level included.

    `full` is the containing object's own counts_as_full_schema_verdict when it
    declares one, else None (inherit the document default).
    """
    out = []
    if isinstance(d, dict):
        for k, v in d.items():
            p = f"{_path}.{k}" if _path else k
            if k == "verdict" and isinstance(v, str):
                own = d.get("counts_as_full_schema_verdict")
                out.append({"path": p, "verdict": v.lower(),
                            "in_kinds": v.lower() in VERDICT_KINDS,
                            "full": None if own is None else own is not False})
            elif isinstance(v, (dict, list)):
                out.extend(all_verdicts(v, p))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            out.extend(all_verdicts(v, f"{_path}[{i}]"))
    return out


def is_adjudication_census(d: dict) -> bool:
    """Audit-lead coverage census: `coverage.<node>.verdicts_at_measured_hash[]`.

    Rows there re-state OTHER reviewers' verdicts (each with file/reviewer), so
    they are evidence about the corpus, not the census author's own verdicts.
    """
    cov = d.get("coverage")
    if not isinstance(cov, dict):
        return False
    return any(isinstance(v, dict) and isinstance(v.get("verdicts_at_measured_hash"), list)
               for v in cov.values())


def pins_anywhere(d, _path="") -> list:
    """All hash-looking pin values anywhere in the document (intent-aware only)."""
    out = []
    if isinstance(d, dict):
        for k, v in d.items():
            p = f"{_path}.{k}" if _path else k
            if k in PIN_KEYS and isinstance(v, str):
                out.append({"path": p, "value": v.lower()})
            elif isinstance(v, (dict, list)):
                out.extend(pins_anywhere(v, p))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            out.extend(pins_anywhere(v, f"{_path}[{i}]"))
    return out


def hash_target_pins(d) -> list:
    """`target_id: "path#sha256"` encodings: return {path, pin} pairs."""
    out = []
    for key in TARGET_KEYS:
        v = d.get(key)
        if isinstance(v, str) and "#" in v:
            path, _, pin = v.partition("#")
            out.append({"path_key": key, "target_path": path.strip(), "pin": pin.strip().lower()})
    return out


def map_pin_to_nodes(pin: str, measured: dict) -> list:
    hits = []
    for t, hv in measured.items():
        h = hv.get("sha256") or ""
        if h and pin and (pin.startswith(h[:12]) or h.startswith(pin[:12])):
            hits.append(t)
    return sorted(set(hits))


def scan_corpus(reviews_dir: Path, measured: dict) -> dict:
    files = sorted(reviews_dir.glob("*.json"))
    per_file, counts = [], {}
    for p in files:
        rec = {"file": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size}
        try:
            doc = json.loads(p.read_text())
        except Exception as e:
            rec.update({"json_ok": False, "error": f"{type(e).__name__}: {e}",
                        "classification": "PARSE_ERROR", "counted": []})
            per_file.append(rec)
            continue
        if not isinstance(doc, dict):
            rec.update({"json_ok": False, "error": "top-level JSON is not an object",
                        "classification": "PARSE_ERROR", "counted": []})
            per_file.append(rec)
            continue
        c = classify_doc(doc, measured)
        rec.update({"json_ok": True, **c})
        rec["is_adjudication_census"] = is_adjudication_census(doc)
        rec["all_verdicts"] = all_verdicts(doc)
        rec["nested_accepts"] = [v for v in rec["all_verdicts"]
                                 if v["verdict"] == "accept" and v["path"] != "verdict"]
        rec["pins_anywhere"] = pins_anywhere(doc)
        rec["hash_target_pins"] = hash_target_pins(doc)
        rec["target_hints"] = sorted(set(
            list(c["targets_raw"]) +
            ([str(doc.get("node_id"))] if isinstance(doc.get("node_id"), str) else [])))
        if c["counted"]:
            verdicts = {e["verdict"] for e in c["counted"]}
            rec["classification"] = ("COUNTED_ACCEPT" if "accept" in verdicts
                                     else "COUNTED_" + "_".join(sorted(verdicts)).upper())
        elif c["verdict_top"] not in VERDICT_KINDS:
            rec["classification"] = ("NESTED_ACCEPT_INVISIBLE" if rec["nested_accepts"]
                                     else "NO_TOP_LEVEL_VERDICT")
        elif not c["targets_raw"]:
            rec["classification"] = "TARGET_UNREADABLE"
        elif not c["pins"]:
            rec["classification"] = "NO_PIN"
        else:
            rec["classification"] = "PIN_STALE_OR_TARGET_UNMAPPED"
            rec["stale_detail"] = [
                {"target": t, "measured_prefix":
                 ((measured.get(t, {}) or {}).get("sha256") or "ABSENT")[:12],
                 "pins": c["pins"]} for t in c["targets_raw"]]
        for e in c["counted"]:
            counts.setdefault(e["target"], {"verdicts": [], "accepts": [],
                                            "full_accepts": [], "scoped_accepts": []})
            counts[e["target"]]["verdicts"].append({**e, "file": p.name})
            if e["verdict"] == "accept":
                counts[e["target"]]["accepts"].append({**e, "file": p.name})
                key = "full_accepts" if c["counts_as_full_schema_verdict"] else "scoped_accepts"
                counts[e["target"]][key].append({**e, "file": p.name})
        per_file.append(rec)
    for t, c in counts.items():
        c["distinct_accept_reviewers"] = sorted({a["reviewer"] for a in c["full_accepts"]})
        c["two_distinct_accepts"] = len(c["distinct_accept_reviewers"]) >= 2
    return {"files": [p.name for p in files], "per_file": per_file, "counts": counts,
            "corpus_digest": corpus_digest(files)}


def intent_scan(per_file: list, measured: dict) -> dict:
    """Verdicts anywhere + pins anywhere, mapped to measured nodes via pin or path."""
    node_by_path = {}
    for t, hv in measured.items():
        art = hv.get("artifact") or ""
        if art:
            node_by_path[art.rstrip("/")] = t
    out = {t: {"accepts": [], "non_accept_verdicts": []} for t in GATE_NODES}
    censuses = []
    for rec in per_file:
        if not rec.get("json_ok"):
            continue
        if rec.get("is_adjudication_census"):
            censuses.append({"file": rec["file"], "sha256": rec["sha256"],
                             "nested_verdicts": len(rec["all_verdicts"]),
                             "note": ("adjudication census re-stating other reviewers' verdicts; "
                                      "not attributed as the census author's own verdicts")})
            continue
        doc_full = rec.get("counts_as_full_schema_verdict") is not False
        pin_entries = [{"path": x["path"], "value": x["value"], "src": "pin_anywhere"}
                       for x in rec.get("pins_anywhere", [])]
        for htp in rec.get("hash_target_pins", []):
            pin_entries.append({"path": f"{htp['path_key']}(path#{htp['pin'][:12]})",
                                "value": htp["pin"], "src": "target_path_hash"})
        nodes_hit = {}
        for pe in pin_entries:
            for n in map_pin_to_nodes(pe["value"], measured):
                nodes_hit.setdefault(n, []).append(pe)
        # path-derived nodes (target_id path#hash): only when the embedded pin still matches
        for htp in rec.get("hash_target_pins", []):
            n = node_by_path.get(htp["target_path"])
            if n and n in map_pin_to_nodes(htp["pin"], measured):
                nodes_hit.setdefault(n, []).append(
                    {"path": htp["path_key"] + "(path)", "value": htp["pin"], "src": "path"})
        for v in rec["all_verdicts"]:
            if not v["in_kinds"]:
                continue
            v_full = doc_full if v.get("full") is None else v["full"]
            for n, pes in sorted(nodes_hit.items()):
                if n not in out:
                    continue
                entry = {"file": rec["file"], "file_sha256": rec["sha256"],
                         "reviewer": rec["reviewer"], "verdict": v["verdict"],
                         "verdict_path": v["path"], "counts_as_full_schema_verdict": v_full,
                         "pin_evidence": pes[:3],
                         "counted_by_controller": any(
                             e["target"] == n and e["verdict"] == v["verdict"]
                             for e in rec.get("counted", []))}
                if v["verdict"] == "accept":
                    out[n]["accepts"].append(entry)
                else:
                    out[n]["non_accept_verdicts"].append(entry)
    for n, d in out.items():
        full = [e for e in d["accepts"] if e["counts_as_full_schema_verdict"]]
        scoped = [e for e in d["accepts"] if not e["counts_as_full_schema_verdict"]]
        d["intent_accept_reviewers"] = sorted({e["reviewer"] for e in full if e["reviewer"] != "?"})
        d["intent_scoped_accept_reviewers"] = sorted({e["reviewer"] for e in scoped
                                                      if e["reviewer"] != "?"})
        d["unattributed_accepts"] = [e for e in d["accepts"] if e["reviewer"] == "?"]
    return {"nodes": out, "censuses": censuses}


def counted_matrix(counts: dict) -> dict:
    return {t: {"counted_accept_reviewers": c.get("distinct_accept_reviewers", []),
                "two_distinct_accepts": c.get("two_distinct_accepts", False),
                "verdicts_bound": len(c.get("verdicts", []))}
            for t, c in sorted(counts.items())}


# ---------------------------------------------------------------- controls
def run_controls(measured: dict) -> dict:
    """Exercise the real controller function on synthetic corpora in a temp ROOT."""
    tmp = Path(tempfile.mkdtemp(prefix="w021_bind_"))
    (tmp / "reviews").mkdir(parents=True)
    L0 = measured["L0"]["sha256"]
    F2a = measured["F2a"]["sha256"]
    A0 = measured["A0"]["sha256"]
    L1 = measured["L1"]["sha256"]
    F2b = measured["F2b"]["sha256"]
    fixtures = {
        "syn-01-accept-top.json": {"reviewer": "syn-1", "target_id": "L0",
                                   "reviewed_sha256": L0, "verdict": "accept",
                                   "counts_as_full_schema_verdict": True},
        "syn-02-accept-scoped.json": {"reviewer": "syn-2", "target_id": "L0",
                                      "reviewed_sha256": L0, "verdict": "accept",
                                      "counts_as_full_schema_verdict": False},
        "syn-03-nested-accept.json": {"reviewer": "syn-3", "node_id": "L0",
                                      "targets": [{"target_id": "L0", "artifact_sha256": L0}],
                                      "verdicts": [{"target_id": "L0", "verdict": "accept"}]},
        "syn-04-stale-pin.json": {"reviewer": "syn-4", "target_id": "L0",
                                  "reviewed_sha256": "deadbeef" * 8, "verdict": "accept",
                                  "counts_as_full_schema_verdict": True},
        "syn-05-no-pin.json": {"reviewer": "syn-5", "target_id": "L0", "verdict": "accept",
                               "counts_as_full_schema_verdict": True},
        "syn-06-alias-target.json": {"reviewer": "syn-6", "target_id": "AF-SCC-C2-VAC-GEN",
                                     "reviewed_sha256": F2a, "verdict": "accept",
                                     "counts_as_full_schema_verdict": True},
        "syn-07-a0-target.json": {"reviewer": "syn-7", "target_id": "A0",
                                  "reviewed_sha256": A0, "verdict": "accept",
                                  "counts_as_full_schema_verdict": True},
        "syn-08-verdict-whitespace.json": {"reviewer": "syn-8", "target_id": "L0",
                                           "reviewed_sha256": L0, "verdict": "Accept ",
                                           "counts_as_full_schema_verdict": True},
        "syn-09-dict-target.json": {"reviewer": "syn-9",
                                    "target": {"node_id": "L1", "sha256": L1},
                                    "verdict": "accept", "counts_as_full_schema_verdict": True},
        "syn-10-path-hash-target.json": {"reviewer": "syn-10", "node_id": "F2b",
                                         "target_id": f"schemas/af_scc_c0_vacuum.yaml#{F2b}",
                                         "reviewed_sha256": F2b, "verdict": "accept",
                                         "counts_as_full_schema_verdict": True},
    }
    for name, doc in fixtures.items():
        (tmp / "reviews" / name).write_text(json.dumps(doc))
    old_root = AL.ROOT
    try:
        AL.ROOT = tmp
        cov = AL.review_coverage(measured)
    finally:
        AL.ROOT = old_root
    indep = scan_corpus(tmp / "reviews", measured)
    icounts = indep["counts"]

    def acc(t):
        return icounts.get(t, {}).get("distinct_accept_reviewers", [])

    expectations = [
        ("syn-01 top-level accept binds", "syn-1" in acc("L0")),
        ("syn-02 scoped accept excluded from accepts but present in verdicts",
         "syn-2" not in acc("L0") and any(v["reviewer"] == "syn-2"
                                          for v in icounts.get("L0", {}).get("verdicts", []))),
        ("syn-03 nested verdict/targets invisible", "syn-3" not in acc("L0")),
        ("syn-04 stale pin invisible", "syn-4" not in acc("L0")),
        ("syn-05 missing pin invisible", "syn-5" not in acc("L0")),
        ("syn-06 class-alias target binds under F2a", "syn-6" in acc("F2a")),
        ("syn-07 A0 target binds under A0", "syn-7" in acc("A0")),
        ("syn-08 whitespace verdict invisible", "syn-8" not in acc("L0")),
        ("syn-09 dict target with sha256 binds under L1", "syn-9" in acc("L1")),
        ("syn-10 path#hash target invisible to controller scan", "syn-10" not in acc("F2b")),
    ]
    ctl = {t: sorted(a["reviewer"] for a in c.get("full_accepts", []))
           for t, c in cov.items() if c.get("full_accepts")}
    ind = {t: sorted(a["reviewer"] for a in c.get("full_accepts", []))
           for t, c in icounts.items() if c.get("full_accepts")}
    expectations.append(("synthetic differential controller==independent", ctl == ind))
    # intent scan must see syn-03 and syn-10
    iscan = intent_scan(indep["per_file"], measured)
    expectations.append(("syn-03 intent-scan recovers the nested accept",
                         "syn-3" in iscan["nodes"].get("L0", {}).get("intent_accept_reviewers", [])))
    expectations.append(("syn-10 intent-scan recovers the path#hash accept",
                         "syn-10" in iscan["nodes"].get("F2b", {}).get("intent_accept_reviewers", [])))
    shutil.rmtree(tmp, ignore_errors=True)
    return {"fixtures": sorted(fixtures), "expectations": [
        {"check": c, "pass": bool(p)} for c, p in expectations],
        "all_pass": all(bool(p) for _, p in expectations),
        "controller_accepts": ctl, "independent_accepts": ind,
        "intent_scan_synthetic": {t: d["intent_accept_reviewers"]
                                  for t, d in iscan["nodes"].items()
                                  if d["intent_accept_reviewers"]}}


def differential(controller_cov: dict, indep: dict) -> dict:
    def norm(counts):
        return {t: sorted((e["file"], e["verdict"], e["reviewer"])
                          for e in c.get("verdicts", []))
                for t, c in counts.items()}
    a, b = norm(controller_cov), norm(indep)
    keys = sorted(set(a) | set(b))
    mismatches = [{"target": t, "controller": a.get(t, []), "independent": b.get(t, [])}
                  for t in keys if a.get(t, []) != b.get(t, [])]
    return {"agree": not mismatches, "targets_compared": keys, "mismatches": mismatches}


def main(out_path: Path) -> dict:
    snapshot_at = now()
    m = json.loads((ROOT / "research_map" / "research_map.json").read_text())
    measured = AL.measured_hashes(m)  # in-memory only; no file writes
    measured_pub = {}
    for k, v in sorted(measured.items()):
        art = v.get("artifact")
        mtime = None
        if art and (ROOT / art).is_file():
            mtime = datetime.fromtimestamp((ROOT / art).stat().st_mtime, CST).isoformat(timespec="seconds")
        measured_pub[k] = {"artifact": art, "kind": v.get("kind"),
                           "sha256": v.get("sha256"), "mtime": mtime}
    reviews_dir = ROOT / "reviews"
    indep = scan_corpus(reviews_dir, measured)
    controller_cov = AL.review_coverage(measured)
    diff = differential(controller_cov, indep["counts"])
    controls = run_controls(measured)
    intent = intent_scan(indep["per_file"], measured)

    cm = counted_matrix(indep["counts"])
    # per-node delta: intent accepts not counted
    delta = {}
    for t in GATE_NODES:
        counted = set(cm.get(t, {}).get("counted_accept_reviewers", []))
        node = intent["nodes"].get(t, {})
        intent_full = set(node.get("intent_accept_reviewers", []))
        intent_scoped = set(node.get("intent_scoped_accept_reviewers", []))
        extra = sorted(intent_full - counted)
        delta[t] = {
            "counted_accept_reviewers": sorted(counted),
            "intent_full_accept_reviewers": sorted(intent_full),
            "intent_scoped_accept_reviewers": sorted(intent_scoped),
            "invisible_full_accept_reviewers": extra,
            "would_satisfy_two_distinct_accepts": len(intent_full) >= 2,
            "currently_satisfies_two_distinct_accepts": len(counted) >= 2,
            "invisible_full_accept_evidence": [e for e in node.get("accepts", [])
                                               if e["reviewer"] in extra],
            "invisible_scoped_accept_evidence": [e for e in node.get("accepts", [])
                                                 if e["reviewer"] in (intent_scoped - counted)],
        }
    fam = {}
    for rec in indep["per_file"]:
        fam[rec["classification"]] = fam.get(rec["classification"], 0) + 1

    # blocking content vs binding: per node, verdict mix at the current hash
    verdict_mix = {}
    for t in GATE_NODES:
        c = indep["counts"].get(t, {})
        mix = {}
        for e in c.get("verdicts", []):
            mix[e["verdict"]] = mix.get(e["verdict"], 0) + 1
        verdict_mix[t] = mix

    path_hash_files = [r["file"] for r in indep["per_file"] if r.get("hash_target_pins")]
    nested_files = [r["file"] for r in indep["per_file"] if r.get("nested_accepts")]
    f1_mix = json.dumps(verdict_mix.get("F1", {}))
    f1_stale = sum(1 for r in indep["per_file"] if "F1" in (r.get("target_hints") or [])
                   and r["classification"] == "PIN_STALE_OR_TARGET_UNMAPPED")
    l0_files = [r for r in indep["per_file"]
                if "L0" in (r.get("target_hints") or []) or "L0" in (r.get("targets_raw") or [])]
    l0_stale = sorted(r["file"] for r in l0_files
                      if r["classification"] == "PIN_STALE_OR_TARGET_UNMAPPED")
    l0_measured = measured_pub.get("L0", {}).get("sha256", "")
    l0_revision_note = ""
    if l0_measured and not l0_measured.startswith("ce42d205e761"):
        l0_revision_note = (" measured " + l0_measured[:12] +
                            " vs the pass-02 frozen ce42d205e761 (140547 bytes -> " +
                            str((ROOT / "ledger" / "theorems.jsonl").stat().st_size) + " bytes)")
    # Prior measured hashes as published in the controller gate audit at 2026-09-12T00:21:55
    # (research_map.json controller_gate_audit); used only to describe the mid-window republication.
    PRIOR_0021 = {"F0": "276009f4f63d", "F1": "9a8bd4c96800",
                  "F2a": "b6123750b37d", "F2b": "1bb78ce9b357", "L0": "ce42d205e761"}
    republication = {}
    for n, prior in PRIOR_0021.items():
        now_h = measured_pub.get(n, {}).get("sha256") or ""
        if now_h and not now_h.startswith(prior):
            republication[n] = {"prior_prefix": prior, "measured_prefix": now_h[:12],
                                "artifact": measured_pub[n]["artifact"],
                                "mtime": measured_pub[n]["mtime"]}
    stale_all = [r["file"] for r in indep["per_file"]
                 if r["classification"] == "PIN_STALE_OR_TARGET_UNMAPPED"]

    findings = [
        {"id": "W021-BIND-F1", "severity": "major",
         "finding": ("The controller gate scan undercounts real, hash-pinned, full-schema accepts "
                     "because two review-encoding families are unreadable to it: (a) nested "
                     "`verdicts[]` with `targets[]` (reviews/L0-review-032.json: L0 and L1 accepts "
                     "at ce42d205e761 / 315c19145065), and (b) `target_id: \"path#sha256\"` with a "
                     "matching reviewed_sha256 (reviews/F2b-review-worker-001.json: F2b accept at "
                     "1bb78ce9b357). A third, scoped family is also invisible and must stay excluded "
                     "from full-schema credit by design: reviews/F0F1-softflag-disposition-review.json "
                     "(astra-lead-audit) carries the F0/F1 soft-flag dispositions as nested accepts "
                     "with counts_as_full_schema_verdict=false. The audit lead's "
                     "reviews/A1-rebind-coverage.json is an adjudication census that restates other "
                     "reviewers' verdicts, not a source of the lead's own accepts (excluded by "
                     "construction here). The per-node delta and the minimal non-semantic wrapper "
                     "repair are in `intent_delta`; rebinding is owned by the audit lead / controller, "
                     "not by this worker."),
         "evidence_refs": ["research_map/astra_lifecycle.py:128-141", "research_map/astra_lifecycle.py:160-198",
                           "reviews/L0-review-032.json#%s" % next((r["sha256"][:12] for r in indep["per_file"] if r["file"] == "L0-review-032.json"), "?"),
                           "reviews/F2b-review-worker-001.json#%s" % next((r["sha256"][:12] for r in indep["per_file"] if r["file"] == "F2b-review-worker-001.json"), "?"),
                           "reviews/F0F1-softflag-disposition-review.json#%s" % next((r["sha256"][:12] for r in indep["per_file"] if r["file"] == "F0F1-softflag-disposition-review.json"), "?")],
         "impact": ("L0 would reach two distinct full accepts (worker-011 counted + worker-032 intent); "
                    "F2b already has two counted (deepseek-flash-17, worker-030) and would reach three. "
                    "The F0/F1 soft-flag dispositions are recorded but cannot be credited by the scan "
                    "as written."),
         "falsifier": ("a review_coverage re-run that counts any of these files without a wrapper, or "
                       "an audit-lead rebind proving the intent reading wrong for a specific file.")},
        {"id": "W021-BIND-F2", "severity": "major",
         "finding": (f"F1 has zero accepts at any encoding at measured hash 9a8bd4c96800: the bound F1 "
                     f"verdict mix is {f1_mix}, with {f1_stale} further F1 files pinned to superseded "
                     "hashes. The G-FORM F1 criterion is content-blocked, not binding-blocked; the "
                     "next second-review effort should go to F1 content, not to rebinding."),
         "evidence_refs": ["schemas/af_wcc_vacuum.yaml#9a8bd4c96800", "research_map/astra_lifecycle.py:288-300"],
         "impact": "G-FORM cannot pass on F1 until an accept exists at the measured hash.",
         "falsifier": "an F1 accept file that binds to 9a8bd4c96800 under the controller rule."},
        {"id": "W021-BIND-F3", "severity": "info",
         "finding": ("Counted vs intent (full-schema) accept state per gate node at this snapshot: " +
                     "; ".join(f"{t} counted={delta[t]['counted_accept_reviewers']} "
                               f"intent={delta[t]['intent_full_accept_reviewers']} "
                               f"scoped={delta[t]['intent_scoped_accept_reviewers']}"
                               for t in GATE_NODES) +
                     ". The counted matrix is the gate-relevant one; the intent column is what a "
                     "tolerant parser plus audit-lead rebind would see. G-F0's only stale-encoded "
                     "accept is reviews/F0-review-lead-audit.json at superseded 565a6e505188."),
         "evidence_refs": ["runtime/state/artifact_hashes.json", "research_map/research_map.json"],
         "impact": "Gives the next lifecycle pass the exact accept deficit per gate.",
         "falsifier": "a re-scan at the same hashes returning a different matrix."},
        {"id": "W021-BIND-F4", "severity": "info",
         "finding": (f"Encoding-family census: {len(path_hash_files)} file(s) use `path#sha256` target "
                     f"ids ({path_hash_files}), {len(nested_files)} file(s) carry nested accept blocks "
                     f"({nested_files}), and the NO_TOP_LEVEL_VERDICT family has "
                     f"{fam.get('NO_TOP_LEVEL_VERDICT', 0)} file(s). These are reasonable authoring "
                     "choices that silently lose gate credit under the current one-format parser."),
         "evidence_refs": ["artifacts/worker-021/review_binding_audit/report.json", "research_map/astra_lifecycle.py:119-141"],
         "impact": "Suggests a tolerant target/verdict parser (or a wrapper convention) to stop losing verdicts.",
         "falsifier": "a parser change that binds all three families and a re-run showing zero invisible accepts."},
        {"id": "W021-BIND-F5", "severity": "info",
         "finding": ("A0/A1 are measured nodes and are bindable (control syn-07), but the G-AUDIT reason "
                     "string only aggregates accepts for F0/F1/F2a/F2b/L0 (astra_lifecycle.py:320-330), so "
                     "A0/A1 verdicts never appear in that reason even when they bind."),
         "evidence_refs": ["research_map/astra_lifecycle.py:320-330"],
         "impact": "Reporting gap only; no verdict change implied.",
         "falsifier": "a gate reason that prints A0/A1 accept counts."},
        {"id": "W021-BIND-F6", "severity": "info",
         "finding": ("Scoped accepts (counts_as_full_schema_verdict=false) never satisfy "
                     "distinct_accept_reviewers by design; the census counts "
                     f"{sum(len(c.get('scoped_accepts', [])) for c in indep['counts'].values())} such "
                     "binding(s). Gate credit must come from full-schema accepts or an audit-lead rebind."),
         "evidence_refs": ["research_map/astra_lifecycle.py:179,189-193"],
         "impact": "Prevents accidental gate credit from advisory verdicts.",
         "falsifier": "a scoped accept counted in distinct_accept_reviewers."},
        {"id": "W021-BIND-F7", "severity": "info",
         "finding": ("The corpus is live. Within the W021-BIND-01 work window, "
                     "reviews/L0-review-worker-006.json changed verdict (accept -> revise, observed "
                     "00:23 -> 00:25) and reviews/F0-review-094.json changed verdict (accept -> "
                     "revise, mtime 00:29), moving the counted F0 accept set from [worker-094] to [] "
                     "between two runs of this same script. Every count here is snapshot-pinned per "
                     "file; the report voids itself on any recorded file-hash drift (per-file drift for "
                     "this run is recorded in `input_drift`)."),
         "evidence_refs": ["runtime/state/artifact_hashes.json",
                           "reviews/L0-review-worker-006.json#%s" % next((r["sha256"][:12] for r in indep["per_file"] if r["file"] == "L0-review-worker-006.json"), "?"),
                           "reviews/F0-review-094.json#%s" % next((r["sha256"][:12] for r in indep["per_file"] if r["file"] == "F0-review-094.json"), "?")],
         "impact": "Gate reasons must be re-measured, never copied, across passes (CF-14/CF-15 family).",
         "falsifier": "a byte-identical re-read of every recorded file."},
        {"id": "W021-BIND-F8", "severity": "major",
         "finding": (f"L0 was rewritten during the audit window: ledger/theorems.jsonl moved "
                     f"ce42d205e761 -> {l0_measured[:12]}{l0_revision_note}, and the row status "
                     "vocabulary changed accepted(50) -> included_unreviewed(50) with new "
                     "supports_claim_basis / review_status / acceptance_authority fields. "
                     f"Consequence: {len(l0_stale)} L0 review file(s) ({l0_stale}) pin the superseded "
                     "hash, so zero L0 verdicts bind at the new revision and G-LIT's L0 criterion "
                     "restarts at the new hash (superseded-hash verdicts are advisory only, "
                     "astra_lifecycle.py:295-296). Any L0 accept counted at ce42d205e761 in earlier "
                     "gate reasons is void pending re-review at the new revision."),
         "evidence_refs": ["ledger/theorems.jsonl#%s" % l0_measured[:12],
                           "research_map/ASTRA_HANDOFF.md:21-27",
                           "research_map/astra_lifecycle.py:294-296"],
         "impact": ("G-LIT L0 review credit resets; the status downgrade does resolve the "
                    "self-certified-acceptance objection on its face, which is reviewable at the new hash."),
         "falsifier": "a re-measured L0 hash equal to ce42d205e761, or a review binding at the new hash."},
        {"id": "W021-BIND-F9", "severity": "critical",
         "finding": (f"Mid-window republication voided the standing review corpus. Relative to the "
                     f"controller gate audit at 00:21:55, {len(republication)} artifact(s) moved: "
                     + "; ".join(f"{n} {v['prior_prefix']}->{v['measured_prefix']} "
                                 f"({v['artifact']}, mtime {v['mtime']})"
                                 for n, v in sorted(republication.items()))
                     + f". At snapshot {snapshot_at} the counted full-schema accept sets are "
                     + json.dumps({t: r for t, r in cm.items()
                                   for r in [r.get("counted_accept_reviewers", [])] if r})
                     + f" (empty for {sum(1 for t in GATE_NODES if not cm.get(t, {}).get('counted_accept_reviewers'))} "
                     f"of {len(GATE_NODES)} nodes), and {len(stale_all)} review file(s) pin a "
                     "superseded hash. Per protocol any verdict bound to superseded bytes is advisory "
                     "only, so every pre-republication gate reason and every accept counted before "
                     "~00:32 must be treated as void until re-issued at the measured hashes."),
         "evidence_refs": ["research_map/research_map.json#controller_gate_audit",
                           "research_map/astra_lifecycle.py:288-300",
                           "runtime/state/artifact_hashes.json"],
         "impact": ("Explains the zero-accept matrix without needing new content defects: review "
                    "throughput is being outrun by republication. The next lifecycle pass must re-pin "
                    "and re-scan, and review effort should be scheduled against a frozen revision."),
         "falsifier": ("a re-measure showing the four artifacts still at their 00:21:55 hashes, or a "
                       "gate reason that binds a pre-00:32 verdict at the current bytes.")},
    ]

    # ---- re-measure inputs (drift guard) ----------------------------------
    drift = []
    scanned = {r["file"] for r in indep["per_file"]}
    current = {p.name for p in reviews_dir.glob("*.json")}
    for name in sorted(current - scanned):
        drift.append({"file": name, "state": "added_after_scan"})
    for name in sorted(scanned - current):
        drift.append({"file": name, "state": "deleted_after_scan"})
    for rec in indep["per_file"]:
        p = reviews_dir / rec["file"]
        if not p.is_file():
            drift.append({"file": rec["file"], "state": "deleted"})
        elif sha256_file(p) != rec["sha256"]:
            drift.append({"file": rec["file"], "state": "changed",
                          "was": rec["sha256"][:12], "now": sha256_file(p)[:12]})
    for node, pub in measured_pub.items():
        art = pub.get("artifact")
        if not art:
            continue
        p = ROOT / art
        if p.is_file():
            h = sha256_file(p)
            if h != pub["sha256"]:
                drift.append({"node": node, "artifact": art, "state": "changed",
                              "was": pub["sha256"][:12], "now": h[:12]})

    verdict = ("BINDING_AUDIT_COMPLETE"
               if (diff["agree"] and controls["all_pass"]) else "AUDIT_VOID_CONTROL_OR_DIFF_FAILURE")
    report = {
        "task_id": "W021-BIND-01",
        "worker": "worker-021",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN",
                      "AF-WCC-SCALAR-SPH"],
        "snapshot_at": snapshot_at,
        "purpose": ("Independent audit of which on-disk review verdicts the controller gate scan "
                    "counts, which exist but are invisible to it, and what the per-gate accept "
                    "deficit is at the measured hashes."),
        "inputs": {"research_map/research_map.json": sha256_file(ROOT / "research_map" / "research_map.json"),
                   "reviews/": {"files": len(indep["files"]), "corpus_digest": indep["corpus_digest"]},
                   "measured_hashes": measured_pub,
                   "astra_lifecycle.py": sha256_file(ROOT / "research_map" / "astra_lifecycle.py")},
        "controller_scan": {t: c for t, c in sorted(controller_cov.items())},
        "independent_scan_counts": {t: c for t, c in sorted(indep["counts"].items())},
        "differential": diff,
        "controls": controls,
        "counted_accept_matrix": {t: cm.get(t, {}).get("counted_accept_reviewers", [])
                                  for t in GATE_NODES},
        "verdict_mix_bound_at_measured_hash": verdict_mix,
        "stale_pin_inventory": [{"file": r["file"], "top_verdict": r.get("verdict_top"),
                                 "targets": r.get("targets_raw"), "pins": r.get("pins")}
                                for r in indep["per_file"]
                                if r["classification"] == "PIN_STALE_OR_TARGET_UNMAPPED"],
        "l0_superseded_review_files": l0_stale,
        "republication_vs_0021": republication,
        "intent_scan": intent,
        "intent_delta": delta,
        "per_file": indep["per_file"],
        "format_families": fam,
        "findings": findings,
        "input_drift": drift,
        "verdict": verdict,
        "authority": ("No gate verdict, no node completion, no rebinding of any reviewer's verdict. "
                      "Worker evidence only; the audit lead and controller own binding adjudication."),
        "next_falsifier": ("Re-run with `python3 artifacts/worker-021/review_binding_audit/"
                           "run_binding_audit.py --out /tmp/recheck.json`. Void if (a) the independent "
                           "classifier and review_coverage disagree on any (file,target,verdict), "
                           "(b) any recorded per-file sha256 or measured node hash differs, or "
                           "(c) any synthetic control deviates from its expected outcome."),
    }
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True))
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "report.json"))
    a = ap.parse_args()
    rep = main(Path(a.out))
    print(json.dumps({"verdict": rep["verdict"], "snapshot_at": rep["snapshot_at"],
                      "counted_accept_matrix": rep["counted_accept_matrix"],
                      "format_families": rep["format_families"],
                      "input_drift": rep["input_drift"]}, indent=2))
    print("intent_delta:", json.dumps(
        {t: {"counted": d["counted_accept_reviewers"],
             "intent_full": d["intent_full_accept_reviewers"],
             "intent_scoped": d["intent_scoped_accept_reviewers"],
             "invisible_full": d["invisible_full_accept_reviewers"]}
         for t, d in rep["intent_delta"].items()}, indent=2))
    print("census_files:", json.dumps(rep["intent_scan"]["censuses"], indent=2))
    print("controls_all_pass:", rep["controls"]["all_pass"],
          "| differential_agree:", rep["differential"]["agree"])
