#!/usr/bin/env python3
"""W48-GFORM-COVERAGE-DRIFT-RECOUNT-01 — independent recount of G-FORM review coverage.

Class binding: F1=AF-WCC-VAC-GEN, F2a=AF-SCC-C2-VAC-GEN, F2b=AF-SCC-C0-VAC-GEN.

Question. The controller's advisory scan (`astra_lifecycle.review_coverage`) is the source of the
published gate reason "coverage F1 4 accepts, F2a 3, F2b 0". This instrument:

  R1  re-implements that scan byte-for-byte in semantics (TARGET_ALIASES / _targets_in_review /
      _explicit_pins / prefix-12 match) and re-runs it against the LIVE reviews/*.json corpus at a
      pinned instant, then reconciles every pass-06 coverage entry against the live bytes.
  R2  runs a documented EXTENDED binding rule (path#hash and alias@hash targets, dict-valued
      reviewed_sha256, extra explicit binding keys) to measure how much coverage the controller's
      target normalization and pin extraction miss.
  R2e additionally treats `evidence_refs` path#sha256 citations as binding evidence (sensitivity
      probe only, never the headline number).

Read-only: writes nothing outside --out. No gate verdict, no node transition, no canonical write.
Deterministic: same inputs + same --now => byte-identical report.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REVIEWS = ROOT / "reviews"

TARGETS = {
    "F1": {
        "artifact": "schemas/af_wcc_vacuum.yaml",
        "sha256": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
        "class_id": "AF-WCC-VAC-GEN",
    },
    "F2a": {
        "artifact": "schemas/af_scc_c2_vacuum.yaml",
        "sha256": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
        "class_id": "AF-SCC-C2-VAC-GEN",
    },
    "F2b": {
        "artifact": "schemas/af_scc_c0_vacuum.yaml",
        "sha256": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
        "class_id": "AF-SCC-C0-VAC-GEN",
    },
}
FROZEN = {
    "artifact": "artifacts/formulation/FROZEN.json",
    "sha256": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
}
INSTRUMENT = "research_map/astra_lifecycle.py"
PASS06_REPORT = "runtime/state/controller_verification/lifecycle_20260912-010117.json"

VERDICT_KINDS = ("accept", "revise", "reject", "inconclusive")
# exact copy of astra_lifecycle.TARGET_ALIASES
TARGET_ALIASES = {
    "F0": "F0", "F1": "F1", "F2A": "F2a", "F2B": "F2b", "F2": "F2b",
    "L0": "L0", "L1": "L1",
    "AF-WCC-VAC-GEN": "F1",
    "AF-SCC-C2-VAC-GEN": "F2a",
    "AF-SCC-C0-VAC-GEN": "F2b",
}
PATH_TO_TARGET = {v["artifact"]: k for k, v in TARGETS.items()}
CLASS_TO_TARGET = {v["class_id"]: k for k, v in TARGETS.items()}
HEX12 = re.compile(r"[0-9a-fA-F]{12,64}")
# R2 explicit binding keys (documented, closed set; prose is never harvested)
BINDING_KEYS = {
    "artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256", "target_sha256",
    "pinned_sha256", "pin_sha256", "artifact_hash", "target_hash", "reviewed_hash",
    "pinned_hash", "declared_sha256", "measured_sha256",
}
NEST_KEYS = {"target", "artifact", "pins", "binding", "bindings", "targets", "inputs",
             "reviewed", "reviewed_bytes", "frozen_pin", "frozen_rev29_pin", "bind_chain"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------- R1: exact controller semantics
def r1_targets(d: dict) -> set:
    out = set()
    for key in ("target_id", "target", "target_subnode"):
        v = d.get(key)
        if isinstance(v, str):
            out.add(v)
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                if isinstance(v.get(k2), str):
                    out.add(v[k2])
    norm = set()
    for t in out:
        norm.add(TARGET_ALIASES.get(t, TARGET_ALIASES.get(t.upper(), t)))
    return norm


def r1_pins(d: dict) -> list:
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


def matches(pins, target_sha: str):
    """Controller predicate; returns (matched, exact64)."""
    exact = any(p == target_sha for p in pins)
    hit = any(p.startswith(target_sha[:12]) or target_sha.startswith(p[:12]) for p in pins)
    return hit, exact


# ---------------------------------------------------------------- R2: extended binding rule
def _tokens(text: str):
    """Candidate target identifiers from one string: split fragments/@, commas, plus."""
    text = text.strip().strip('"').strip("'")
    head = text.split("#")[0]
    at_parts = [p for p in head.split("@")]
    parts = []
    for p in at_parts:
        parts.extend(re.split(r"[,;+]", p))
    parts.append(head)
    return [p.strip() for p in parts if p.strip()]


def r2_targets(d: dict) -> set:
    cands = []
    for key in ("target_id", "target", "target_subnode", "node_id", "class_id",
                "artifact_path", "artifact"):
        v = d.get(key)
        if isinstance(v, str):
            cands.append(v)
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id", "path",
                       "artifact", "class_id"):
                if isinstance(v.get(k2), str):
                    cands.append(v[k2])
    for key in ("class_ids", "node_ids"):
        v = d.get(key)
        if isinstance(v, list):
            cands.extend(x for x in v if isinstance(x, str))
    out = set()
    for c in cands:
        for tok in _tokens(c):
            up = tok.upper()
            if tok in TARGET_ALIASES:
                out.add(TARGET_ALIASES[tok])
            elif up in TARGET_ALIASES:
                out.add(TARGET_ALIASES[up])
            if tok in CLASS_TO_TARGET:
                out.add(CLASS_TO_TARGET[tok])
            if tok in PATH_TO_TARGET:
                out.add(PATH_TO_TARGET[tok])
            for path, t in PATH_TO_TARGET.items():
                if tok == path or tok == Path(path).name or tok.endswith("/" + path):
                    out.add(t)
        # whole-string forms: path#hash, alias@hash, 'F1,F2a,F2b@...' handled by _tokens
        if "af_wcc_vacuum" in c:
            out.add("F1")
        if "af_scc_c2_vacuum" in c:
            out.add("F2a")
        if "af_scc_c0_vacuum" in c:
            out.add("F2b")
    return {t for t in out if t in TARGETS}


def _hex_tokens(value) -> list:
    if isinstance(value, str):
        return [m.group(0).lower() for m in HEX12.finditer(value)]
    if isinstance(value, dict):
        acc = []
        for v in value.values():
            acc.extend(_hex_tokens(v))
        return acc
    if isinstance(value, list):
        acc = []
        for v in value:
            acc.extend(_hex_tokens(v))
        return acc
    return []


def r2_pins(d: dict, include_evidence: bool = False) -> list:
    pins = []

    def walk(o, depth=0):
        if depth > 4:
            return
        if isinstance(o, dict):
            for k, v in o.items():
                kl = str(k).lower()
                if kl in BINDING_KEYS:
                    pins.extend(_hex_tokens(v))
                if kl in NEST_KEYS:
                    walk(v, depth + 1)
        elif isinstance(o, list):
            for v in o:
                walk(v, depth + 1)

    walk(d)
    # a target string that itself carries a fragment hash is an explicit pin
    for key in ("target_id", "target", "target_subnode"):
        v = d.get(key)
        if isinstance(v, str) and ("#" in v or "@" in v):
            pins.extend(m.group(0).lower() for m in HEX12.finditer(v))
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "path", "artifact"):
                vv = v.get(k2)
                if isinstance(vv, str) and ("#" in vv or "@" in vv):
                    pins.extend(m.group(0).lower() for m in HEX12.finditer(vv))
            pins.extend(_hex_tokens(v.get("pin_sha256")) + _hex_tokens(v.get("sha256")))
    if include_evidence:
        for ev in (d.get("evidence_refs") or []):
            pins.extend(m.group(0).lower() for m in HEX12.finditer(str(ev)))
    # dedupe, keep deterministic order
    seen, out = set(), []
    for p in pins:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


# ---------------------------------------------------------------- scan harness
def scan(records, targets_fn, pins_fn, include_evidence=False):
    """records: list of (name, data, mtime_iso). Returns per-target coverage dict."""
    cov = {t: {"verdicts": [], "accepts": [], "full_accepts": [], "scoped_accepts": [],
               "distinct_full_accept_reviewers": [], "exact64_full_accepts": []}
           for t in TARGETS}
    for name, d, mtime in records:
        if not isinstance(d, dict):
            continue
        v = str(d.get("verdict", "")).lower()
        if v not in VERDICT_KINDS:
            continue
        reviewer = str(d.get("reviewer") or d.get("actor") or "?")
        full = d.get("counts_as_full_schema_verdict") is not False
        pins = pins_fn(d, include_evidence) if pins_fn is r2_pins else pins_fn(d)
        tg = targets_fn(d)
        for t in sorted(tg):
            if t not in TARGETS:  # controller: if t not in cov: continue
                continue
            h = TARGETS[t]["sha256"]
            ok, exact = matches(pins, h)
            if not ok:
                continue
            entry = {"file": name, "reviewer": reviewer, "verdict": v,
                     "counts_as_full_schema_verdict": full, "created_at": d.get("created_at"),
                     "mtime": mtime, "exact64": exact}
            cov[t]["verdicts"].append(entry)
            if v == "accept":
                cov[t]["accepts"].append(entry)
                (cov[t]["full_accepts"] if full else cov[t]["scoped_accepts"]).append(entry)
                if exact and full:
                    cov[t]["exact64_full_accepts"].append(entry)
    for c in cov.values():
        c["distinct_full_accept_reviewers"] = sorted({e["reviewer"] for e in c["full_accepts"]})
        c["two_distinct_full_accepts"] = len(c["distinct_full_accept_reviewers"]) >= 2
    return cov


def load_records():
    recs, corpus = [], {}
    for fp in sorted(REVIEWS.glob("*.json")):
        try:
            raw = fp.read_bytes()
            d = json.loads(raw)
        except Exception:
            continue
        mtime = datetime.fromtimestamp(fp.stat().st_mtime).strftime("%Y-%m-%dT%H:%M:%S%z")
        recs.append((fp.name, d, mtime))
        corpus[fp.name] = {"sha256": hashlib.sha256(raw).hexdigest(),
                           "bytes": len(raw), "mtime": mtime}
    return recs, corpus


def corpus_digest(corpus: dict) -> str:
    lines = [f"{k}\t{v['sha256']}\t{v['bytes']}\t{v['mtime']}" for k, v in sorted(corpus.items())]
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


# ---------------------------------------------------------------- reconciliation
def entry_key(e):
    return (e["file"], e["reviewer"], e["verdict"])


def reconcile(pass06_cov, live_cov, corpus):
    out = {}
    for t in TARGETS:
        p6_entries = pass06_cov.get(t, {}).get("full_accepts", [])
        live = live_cov[t]["full_accepts"]
        live_by_file = {e["file"]: e for e in live}
        still, demoted, missing = [], [], []
        for e in p6_entries:
            f = e["file"]
            if f in live_by_file:
                still.append({"pass06": e, "live": live_by_file[f]})
            else:
                info = corpus.get(f)
                cur = None
                if info is not None:
                    # verdict of the live file (any verdict kind)
                    rec = next((d for n, d, m in RECORDS_CACHE if n == f), None)
                    cur = str((rec or {}).get("verdict", "")).lower() if rec else None
                row = {"pass06": e, "file_present": info is not None,
                       "current_verdict": cur,
                       "current_sha256": (info or {}).get("sha256"),
                       "current_mtime": (info or {}).get("mtime")}
                (demoted if info is not None else missing).append(row)
        live_keys = {entry_key(e) for e in live}
        p6_keys = {entry_key(e) for e in p6_entries}
        new = [e for e in live if entry_key(e) not in p6_keys]
        out[t] = {
            "pass06_full_accepts": p6_entries,
            "live_full_accepts": live,
            "still_counted": still,
            "no_longer_rateable_as_full_accept": demoted,
            "file_missing": missing,
            "new_since_pass06": new,
            "pass06_still_reproducible": len(demoted) == 0 and len(missing) == 0,
            "live_distinct_full_accept_reviewers": live_cov[t]["distinct_full_accept_reviewers"],
        }
    return out


# ---------------------------------------------------------------- controls
def synthetic(name, d, mtime):
    return (name, d, mtime)


def run_controls(now_iso):
    f1, f2a, f2b = (TARGETS[t]["sha256"] for t in ("F1", "F2a", "F2b"))
    rev12 = "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"
    c = {}

    def counts(recs, target):
        return [e["file"] for e in scan(recs, r2_targets, r2_pins)[target]["full_accepts"]]

    def counts_r1(recs, target):
        return [e["file"] for e in scan(recs, r1_targets, r1_pins)[target]["full_accepts"]]

    # C1 path#hash target: R2 counts, R1 does not (the normalization gap, deterministic)
    rec = synthetic("CTRL-path-target.json",
                    {"verdict": "accept", "reviewer": "ctrl", "class_id": "AF-WCC-VAC-GEN",
                     "target_id": f"schemas/af_wcc_vacuum.yaml#{f1}",
                     "artifact_sha256": f1}, now_iso)
    c["C1_path_target_R2_counts"] = {"expected": True, "observed": "CTRL-path-target.json" in counts([rec], "F1")}
    c["C1_path_target_R1_misses"] = {"expected": True, "observed": "CTRL-path-target.json" not in counts_r1([rec], "F1")}

    # C2 dict-valued reviewed_sha256: R2 counts, R1 drops (the _explicit_pins defect)
    rec = synthetic("CTRL-dict-pin.json",
                    {"verdict": "accept", "reviewer": "ctrl",
                     "target_id": "AF-SCC-C0-VAC-GEN",
                     "reviewed_sha256": {"schemas/af_scc_c0_vacuum.yaml": f2b}}, now_iso)
    c["C2_dict_pin_R2_counts"] = {"expected": True, "observed": "CTRL-dict-pin.json" in counts([rec], "F2b")}
    c["C2_dict_pin_R1_misses"] = {"expected": True, "observed": "CTRL-dict-pin.json" not in counts_r1([rec], "F2b")}

    # C3 stale pin must not count under either rule
    rec = synthetic("CTRL-stale-pin.json",
                    {"verdict": "accept", "reviewer": "ctrl", "target_id": "F1",
                     "artifact_sha256": rev12}, now_iso)
    c["C3_stale_pin_excluded"] = {"expected": True,
                                  "observed": counts([rec], "F1") == [] and counts_r1([rec], "F1") == []}

    # C4 prose mention with a mismatched explicit pin must NOT count under R2
    rec = synthetic("CTRL-mention-only.json",
                    {"verdict": "accept", "reviewer": "ctrl", "target_id": "F2b",
                     "artifact_sha256": f2a,
                     "summary": f"the bytes {f2b} were read"}, now_iso)
    naive = f2b in json.dumps(rec)
    c["C4_prose_mention_not_counted"] = {"expected": True,
                                         "observed": (counts([rec], "F2b") == [] and naive)}

    # C5 cross-target isolation: an F2a pin must not count as F2b
    rec = synthetic("CTRL-cross-target.json",
                    {"verdict": "accept", "reviewer": "ctrl", "target_id": "F2b",
                     "artifact_sha256": f2a}, now_iso)
    c["C5_cross_target_isolated"] = {"expected": True, "observed": counts([rec], "F2b") == []}

    # C6 exact-64 flag: a 12-hex prefix pin matches but is not exact64
    rec = synthetic("CTRL-prefix-pin.json",
                    {"verdict": "accept", "reviewer": "ctrl", "target_id": "F1",
                     "artifact_sha256": f1[:12]}, now_iso)
    r = scan([rec], r2_targets, r2_pins)["F1"]
    c["C6_prefix_matches_but_not_exact64"] = {
        "expected": True,
        "observed": len(r["full_accepts"]) == 1 and r["exact64_full_accepts"] == []}
    return c


# ---------------------------------------------------------------- main
RECORDS_CACHE = []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", required=True, help="fixed ISO timestamp for determinism")
    ap.add_argument("--out", default="report.json")
    ap.add_argument("--skip-controls", action="store_true")
    args = ap.parse_args()

    global RECORDS_CACHE
    inputs = {
        INSTRUMENT: sha256_file(ROOT / INSTRUMENT),
        PASS06_REPORT: sha256_file(ROOT / PASS06_REPORT),
        FROZEN["artifact"]: sha256_file(ROOT / FROZEN["artifact"]),
    }
    for t in TARGETS:
        inputs[TARGETS[t]["artifact"]] = sha256_file(ROOT / TARGETS[t]["artifact"])

    recs, corpus = load_records()
    RECORDS_CACHE = recs
    digest_before = corpus_digest(corpus)

    r1 = scan(recs, r1_targets, r1_pins)
    r2 = scan(recs, r2_targets, r2_pins)
    r2e = scan(recs, r2_targets, r2_pins, include_evidence=True)

    pass06_raw = json.loads((ROOT / PASS06_REPORT).read_text())
    pass06_cov = pass06_raw["review_coverage"]
    rec = reconcile(pass06_cov, r1, corpus)

    controls = {} if args.skip_controls else run_controls(args.now)
    recs2, corpus2 = load_records()
    digest_after = corpus_digest(corpus2)
    controls["C7_input_stability"] = {
        "expected": True,
        "observed": digest_before == digest_after,
        "corpus_sha256_before": digest_before,
        "corpus_sha256_after": digest_after,
    }

    # C8: import the controller's own scanner and require byte-equal classification with R1.
    oracle_counts = None
    try:
        sys.path.insert(0, str(ROOT / "research_map"))
        import astra_lifecycle as al  # noqa: E402
        oracle = al.review_coverage({t: {"sha256": TARGETS[t]["sha256"]} for t in TARGETS})
        oracle_counts = {t: {"full_accepts": sorted(e["file"] for e in oracle[t]["full_accepts"]),
                             "verdicts": sorted(e["file"] for e in oracle[t]["verdicts"])}
                         for t in TARGETS}
        same = all(oracle_counts[t]["full_accepts"] == sorted(e["file"] for e in r1[t]["full_accepts"])
                   and oracle_counts[t]["verdicts"] == sorted(e["file"] for e in r1[t]["verdicts"])
                   for t in TARGETS)
        controls["C8_controller_oracle_agrees_R1"] = {
            "expected": True, "observed": bool(same),
            "oracle": oracle_counts,
            "note": "oracle re-reads reviews/ live; valid only because C7 held for this run"}
    except Exception as exc:  # pragma: no cover - environment dependent
        controls["C8_controller_oracle_agrees_R1"] = {
            "expected": True, "observed": None, "skipped": f"{type(exc).__name__}: {exc}"}

    body = {
        "task_id": "W48-GFORM-COVERAGE-DRIFT-RECOUNT-01",
        "worker": "worker-048",
        "created_at": args.now,
        "gate": "G-FORM",
        "node_id": "F1/F2a/F2b",
        "class_ids": [TARGETS[t]["class_id"] for t in ("F1", "F2a", "F2b")],
        "authority": ("no gate verdict, no node transition, no validation_status=passed, "
                      "no canonical write; worker events cannot promote"),
        "inputs_manifest": inputs,
        "target_pins": TARGETS,
        "frozen_pin": FROZEN,
        "pass06": {
            "report": PASS06_REPORT,
            "report_sha256": inputs[PASS06_REPORT],
            "at": pass06_raw.get("at"),
            "coverage": {t: {"full_accepts": pass06_cov.get(t, {}).get("full_accepts", []),
                             "distinct": pass06_cov.get(t, {}).get("distinct_accept_reviewers", [])}
                         for t in TARGETS},
        },
        "live_R1": r1,
        "live_R2": r2,
        "live_R2e_evidence_bound": r2e,
        "reconciliation_R1_vs_pass06": rec,
        "review_corpus": {"files": len(corpus), "sha256": digest_before},
        "corpus_manifest": corpus,
        "controls": controls,
        "summary": {
            "R1_live_full_accept_counts": {t: len(r1[t]["full_accepts"]) for t in TARGETS},
            "R1_live_distinct_reviewers": {t: r1[t]["distinct_full_accept_reviewers"] for t in TARGETS},
            "R2_live_full_accept_counts": {t: len(r2[t]["full_accepts"]) for t in TARGETS},
            "R2_live_distinct_reviewers": {t: r2[t]["distinct_full_accept_reviewers"] for t in TARGETS},
            "R2e_live_full_accept_counts": {t: len(r2e[t]["full_accepts"]) for t in TARGETS},
            "pass06_full_accept_counts": {t: len(pass06_cov.get(t, {}).get("full_accepts", []))
                                          for t in TARGETS},
            "pass06_reproducible": {t: rec[t]["pass06_still_reproducible"] for t in TARGETS},
            "R2_minus_R1_full_accepts": {t: len(r2[t]["full_accepts"]) - len(r1[t]["full_accepts"])
                                         for t in TARGETS},
            "F2b_two_distinct_full_accepts_R2": r2["F2b"]["two_distinct_full_accepts"],
            "controller_oracle_full_accepts": oracle_counts,
        },
        "falsifier": (
            "At the bytes recorded in inputs_manifest.json and the review corpus digest: "
            "(a) any R1 entry that differs from a re-run of research_map/astra_lifecycle.py::"
            "review_coverage on the same corpus at the same instant; (b) any pass-06 full-accept "
            "file that is counted by R1 at the live bytes and that this report lists as demoted or "
            "missing; (c) any R2 full-accept that does not satisfy the documented binding rule "
            "(explicit binding key or target-string fragment, never prose); (d) any control that "
            "does not flip as declared; (e) a corpus whose digest is unchanged but whose per-file "
            "map differs from corpus_manifest. A later write to a review file is not a falsifier - "
            "it is a new revision to re-run against."),
        "limits": [
            "advisory recount of an advisory controller scan; not a schema semantics review",
            "R2e is a sensitivity probe; headline numbers are R1 (controller-equivalent) and R2",
            "author independence is reported as distinct reviewer ids only; no authorship inference",
            "review files are not frozen by any pin, so the live corpus is a moving target",
        ],
    }
    out = ROOT / "artifacts/worker-048/gform_coverage_recount" / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(body, indent=1, sort_keys=True) + "\n")
    print(json.dumps(body["summary"], indent=1))
    ctl = body["controls"]
    bad = [k for k, v in ctl.items()
           if v.get("observed") is None and "skipped" not in v
           or (v.get("observed") is not None and v.get("expected") != v.get("observed"))]
    print("controls:", "ALL_PASS" if not bad else f"FAIL {bad}")
    print("report_sha256:", sha256_file(out))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
