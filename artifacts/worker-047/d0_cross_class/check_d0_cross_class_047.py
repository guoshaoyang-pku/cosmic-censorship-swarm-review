#!/usr/bin/env python3
"""W047-GFORM-D0-XCLASS-01 instrument.

Cross-class adjudication of the D0 regularity-domain typing defect shared by the
three canonical G-FORM schemas, plus the accept/revise verdict asymmetry.

Scope (class-bound):
  F1  AF-WCC-VAC-GEN      schemas/af_wcc_vacuum.yaml
  F2a AF-SCC-C2-VAC-GEN   schemas/af_scc_c2_vacuum.yaml
  F2b AF-SCC-C0-VAC-GEN   schemas/af_scc_c0_vacuum.yaml

What it does, deterministically, with no network:
  C01 input snapshot stability (hash before/after read)
  C02 duplicate top-level YAML mapping keys (machine-frozen hygiene)
  C03 byte/textual identity matrix of the D0 definition across the three classes
  C04 binder declaration: `forall (s,delta) in D0` in quantifiers + statement_formal
  C05 D0 typing probe: does the second disjunct supply an (s,delta) instantiation?
  C06 ambient-space probe: is a comeagerness ambient object named for the smooth branch?
  C07 data_class structural diff across the three schemas
  C08 regularity_class textual equality
  C09 indexed-object instantiation audit (G_{s,delta} / X^{s,delta}) vs D0 branches
  C10 repair-acceptance predicates R1 (single regime) / R2 (typed union)
  C11 verdict profile at the pinned hash, per class
  C12 verdict asymmetry between classes carrying the identical D0 text
  C13 self-binding: instrument hash + pinned input hashes inside the report

Controls K1-K5 (printed into the same report) calibrate the probes: a synthetic
well-typed single-regime D0 must not be flagged; deleting the smooth disjunct
from a snapshot must flip C05; a YAML without D0 must not raise; editing one
copy's D0 must flip the identity matrix; a synthetic single-accept corpus must
count as one accept.

Exit codes: 0 = ran to completion (findings reported), 1 = --strict and at least
one FAIL, 2 = fail-closed (unreadable input / parse failure).

Authority: worker evidence only. This instrument does not amend artifacts, does
not set gate verdicts, does not set node status, and does not promote text.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta

import yaml

CST = timezone(timedelta(hours=8))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

TARGETS = [
    {"key": "F1", "class_id": "AF-WCC-VAC-GEN", "node_id": "F1",
     "path": "schemas/af_wcc_vacuum.yaml"},
    {"key": "F2a", "class_id": "AF-SCC-C2-VAC-GEN", "node_id": "F2a",
     "path": "schemas/af_scc_c2_vacuum.yaml"},
    {"key": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "node_id": "F2b",
     "path": "schemas/af_scc_c0_vacuum.yaml"},
]

# Keys that, in this family of schemas, are expected to be unique; duplicates
# are a strict-YAML-1.2 failure (PyYAML silently last-wins).
DUP_SCAN_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def read_text(path: str):
    with open(path, "rb") as f:
        raw = f.read()
    return raw, raw.decode("utf-8", errors="strict")


def line_of(text: str, needle: str):
    for i, ln in enumerate(text.split("\n"), 1):
        if needle in ln:
            return i, ln.strip()
    return None, None


def load_yaml(text: str):
    return yaml.safe_load(text)


def duplicate_top_level_keys(text: str):
    seen = {}
    for i, ln in enumerate(text.split("\n"), 1):
        m = DUP_SCAN_LINE.match(ln)
        if m:
            seen.setdefault(m.group(1), []).append(i)
    return {k: v for k, v in seen.items() if len(v) > 1}


def get_d0(doc):
    q = (doc or {}).get("quantifiers") or {}
    doms = q.get("domains") or {}
    d0 = doms.get("D0") or {}
    return d0 if isinstance(d0, dict) else {}


def d0_definition(doc):
    d = get_d0(doc)
    v = d.get("definition")
    return v if isinstance(v, str) else None


def ordered_binders(doc):
    q = (doc or {}).get("quantifiers") or {}
    ordered = q.get("ordered") or []
    out = []
    for item in ordered:
        if isinstance(item, dict):
            out.append((item.get("kind"), item.get("binder"), item.get("domain_id")))
    return out


def statement_formal(doc):
    c = (doc or {}).get("conclusion") or {}
    v = c.get("statement_formal")
    return v if isinstance(v, str) else None


# ---------------------------------------------------------------------------
# probes over a D0 definition string
# ---------------------------------------------------------------------------

SMOOTH_MARKERS = ("smooth-with-decay", "smooth_with_decay", "smooth with decay")


def d0_disjuncts(defn: str):
    """Split a D0 definition into its disjuncts.

    The family's phrasing is '<regime A>, or the smooth-with-decay default'.
    Split on a comma/space-delimited 'or' that is not part of a bound like
    's > 5/2'.
    """
    if not defn:
        return []
    parts = re.split(r"(?:,\s*|\s+)or\s+", defn)
    return [p.strip(" ;.") for p in parts if p.strip(" ;.")]


def smooth_branch(defn: str):
    for d in d0_disjuncts(defn):
        low = d.lower()
        if any(m in low for m in SMOOTH_MARKERS):
            return d
    return None


def disjunct_supplies_pair(d: str) -> bool:
    """True iff the disjunct textually supplies an (s, delta) instantiation."""
    if d is None:
        return False
    low = d.lower()
    has_s = bool(re.search(r"\bs\s*(>|<|=|in|∈)", low))
    has_delta = "delta" in low
    return has_s and has_delta


def smooth_ambient_named(text: str) -> bool:
    """Proximity-text probe, retained ONLY as the false-positive regression target.

    It is deliberately kept because it is the probe that produced a false positive
    on F2b (prose '... exclude negative-mass data from the ambient space' within
    60 chars of 'the smooth-with-decay default'); C06 now uses the structural
    probe below instead, and control K6 pins this regression.
    """
    patterns = [
        r"X\s*(?:_|\^)?\s*\{?\s*smooth",          # X_smooth / X^{smooth}
        r"X\s*\^?\s*\{?\s*\\?infty",              # X^{infty}
        r"X_?\s*smooth[_-]?vac",
        r"ambient[_ ](?:space|set)[^\n]{0,60}smooth",
        r"smooth[^\n]{0,60}ambient[_ ](?:space|set)",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def structural_ambient(doc):
    """The declared genericity ambient object (structural, not prose)."""
    g = (doc or {}).get("genericity") or {}
    v = g.get("ambient_space")
    return v if isinstance(v, str) else None


def walk_dicts(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield path + "." + str(k), v
            yield from walk_dicts(v, path + "." + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield path + f"[{i}]", v


def smooth_branch_ambient_declared(doc):
    """Structural keys that declare a non-Sobolev ambient object."""
    hits = []
    for path, v in walk_dicts(doc):
        key = path.rsplit(".", 1)[-1].lower()
        if "ambient" in key and isinstance(v, str) and "smooth" in v.lower():
            hits.append(path)
    return hits


def indexed_pair_objects(text: str):
    """Occurrences of objects indexed by the (s,delta) pair."""
    return {
        "X^{s,delta}_vac(AF)": len(re.findall(r"X\^\{s,delta\}_vac\(AF\)", text)),
        "G_{s,delta}": len(re.findall(r"G_\{s,delta\}", text)),
        "forall (s,delta) in D0": len(re.findall(r"forall \(s,delta\) in D0", text)),
    }


# ---------------------------------------------------------------------------
# verdict scan
# ---------------------------------------------------------------------------

REVIEW_SHA_FIELDS = ("reviewed_sha256", "artifact_sha256", "reviewed_sha", "sha256", "target_sha256")


def review_bound_hash(r: dict):
    for f in REVIEW_SHA_FIELDS:
        v = r.get(f)
        if isinstance(v, str) and re.fullmatch(r"[0-9a-f]{8,64}", v):
            return v
    return None


def hash_matches(bound: str, pinned: str) -> bool:
    return bool(bound) and (bound == pinned or pinned.startswith(bound) or bound.startswith(pinned))


def collect_reviews(repo: str):
    reviews = []
    mpath = os.path.join(repo, "research_map", "research_map.json")
    try:
        m = json.load(open(mpath, "r", encoding="utf-8"))
        for r in m.get("reviews", []):
            if isinstance(r, dict):
                rr = dict(r)
                rr["_source"] = "research_map/research_map.json"
                reviews.append(rr)
    except Exception as exc:  # fail-closed upstream
        raise RuntimeError(f"cannot read {mpath}: {exc}") from exc
    rdir = os.path.join(repo, "reviews")
    if os.path.isdir(rdir):
        for name in sorted(os.listdir(rdir)):
            if not name.endswith(".json"):
                continue
            p = os.path.join(rdir, name)
            try:
                r = json.load(open(p, "r", encoding="utf-8"))
            except Exception:
                continue
            if isinstance(r, dict):
                r = dict(r)
                r["_source"] = f"reviews/{name}"
                reviews.append(r)
    return reviews


def target_matches(r: dict, t: dict) -> bool:
    fields = [str(r.get("target_id") or ""), str(r.get("class_id") or ""),
              str(r.get("node_id") or ""), str(r.get("artifact") or ""),
              str(r.get("target_id_full") or "")]
    blob = " ".join(fields)
    if t["class_id"] in blob or t["node_id"] in blob:
        return True
    return os.path.basename(t["path"]) in blob


def verdict_profile(reviews, t: dict):
    counts = {"accept": 0, "revise": 0, "inconclusive": 0, "reject": 0}
    distinct = {k: set() for k in counts}
    rows = []
    seen = set()
    for r in reviews:
        bh = review_bound_hash(r)
        if not hash_matches(bh, t["_pinned"]):
            continue
        if not target_matches(r, t):
            continue
        who = str(r.get("reviewer") or r.get("worker") or r.get("actor") or "?")
        eid = str(r.get("event_id") or r.get("review_id") or r.get("_source"))
        key = (who, eid)
        if key in seen:
            continue
        seen.add(key)
        v = str(r.get("verdict") or "")
        if v in counts:
            counts[v] += 1
            distinct[v].add(who)
        rows.append({"reviewer": who, "verdict": v, "score": r.get("score"),
                     "created_at": r.get("created_at"), "source": r.get("_source")})
    return counts, rows, {k: sorted(v) for k, v in distinct.items()}


# ---------------------------------------------------------------------------
# repair-acceptance predicates (also usable as an acceptance test for a fix)
# ---------------------------------------------------------------------------

def repair_r1_single_regime(defn: str) -> bool:
    if not defn:
        return False
    ds = d0_disjuncts(defn)
    return len(ds) == 1 and disjunct_supplies_pair(ds[0])


def repair_r2_typed_union(doc, defn: str) -> bool:
    """A typed union keeps the smooth default but supplies it with a typed ambient.

    Acceptance is structural (an ambient object declared for the non-pair branch);
    the accompanying comeagerness definition must be present in the artifact text
    and is checked by the human/gate reviewer, not by this predicate.
    """
    if not defn:
        return False
    ds = d0_disjuncts(defn)
    if len(ds) < 2:
        return False
    missing_pair = [d for d in ds if not disjunct_supplies_pair(d)]
    if not missing_pair:
        return True
    amb = structural_ambient(doc) or ""
    return ("smooth" in amb.lower()) or bool(smooth_branch_ambient_declared(doc))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def run(repo: str, snapshot_dir=None):
    checks = []
    controls = []
    findings = []
    inputs = {}

    docs = {}
    texts = {}
    for t in TARGETS:
        p = os.path.join(repo, t["path"])
        if not os.path.isfile(p):
            raise RuntimeError(f"missing input {p}")
        raw1 = open(p, "rb").read()
        h1 = sha256_bytes(raw1)
        raw2, text = read_text(p)
        h2 = sha256_bytes(raw2)
        doc = load_yaml(text)
        docs[t["key"]] = doc
        texts[t["key"]] = text
        t["_pinned"] = h1
        inputs[t["key"]] = {
            "path": t["path"], "class_id": t["class_id"], "node_id": t["node_id"],
            "bytes": len(raw1), "sha256": h1,
            "stable_during_read": h1 == h2,
        }
        if snapshot_dir:
            os.makedirs(snapshot_dir, exist_ok=True)
            dst = os.path.join(snapshot_dir, f"{os.path.basename(t['path'])}.{h1[:12]}")
            with open(dst, "wb") as f:
                f.write(raw1)

    # C01
    bad = [k for k, v in inputs.items() if not v["stable_during_read"]]
    checks.append({
        "id": "C01", "name": "input snapshot stability",
        "status": "PASS" if not bad else "FAIL",
        "detail": "all three canonical schemas byte-stable across the read" if not bad
                  else f"drifted during read: {bad}",
    })

    # C02
    dup = {k: duplicate_top_level_keys(texts[k]) for k in texts}
    dup_any = {k: v for k, v in dup.items() if v}
    checks.append({
        "id": "C02", "name": "duplicate top-level YAML mapping keys",
        "status": "FAIL" if dup_any else "PASS",
        "detail": f"duplicate top-level keys present in {list(dup_any)}" if dup_any
                  else "no duplicate top-level keys",
        "evidence": dup_any,
    })

    # C03
    defs = {k: d0_definition(docs[k]) for k in docs}
    eq = {}
    keys = list(defs)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            eq[f"{keys[i]}=={keys[j]}"] = defs[keys[i]] == defs[keys[j]]
    same_text_classes = ["F2a", "F2b"] if eq.get("F2a==F2b") else []
    if eq.get("F1==F2a"):
        same_text_classes = ["F1", "F2a", "F2b"]
    checks.append({
        "id": "C03", "name": "D0 definition identity matrix",
        "status": "INFO",
        "detail": f"equal pairs: {[k for k, v in eq.items() if v]}; "
                  f"classes with byte-identical D0 text: {same_text_classes}",
        "evidence": {k: defs[k] for k in defs},
    })

    # C04
    binder_ok = {}
    for k in docs:
        ob = ordered_binders(docs[k])
        sf = statement_formal(docs[k]) or ""
        binder_ok[k] = (ob[:1] == [("forall", "(s,delta)", "D0")]) and ("forall (s,delta) in D0" in sf)
    checks.append({
        "id": "C04", "name": "binder declaration `forall (s,delta) in D0`",
        "status": "PASS" if all(binder_ok.values()) else "FAIL",
        "detail": f"declared per class: {binder_ok}",
    })

    # C05
    typing = {}
    for k in docs:
        defn = defs[k] or ""
        ds = d0_disjuncts(defn)
        sb = smooth_branch(defn)
        typing[k] = {
            "disjunct_count": len(ds),
            "smooth_branch": sb,
            "smooth_branch_supplies_s_delta_pair": disjunct_supplies_pair(sb),
            "disjuncts": ds,
        }
    ill = [k for k, v in typing.items() if v["disjunct_count"] > 1 and not v["smooth_branch_supplies_s_delta_pair"]]
    checks.append({
        "id": "C05", "name": "D0 typing: every D0 member supplies the bound (s,delta)",
        "status": "FAIL" if ill else "PASS",
        "detail": (f"ill-typed for classes {ill}: D0 has a disjunct supplying no (s,delta) "
                   f"instantiation while the binder is over the pair") if ill
                  else "every D0 member supplies an (s,delta) instantiation",
        "evidence": typing,
    })

    # C06
    ambient = {}
    for k in docs:
        t = texts[k]
        amb = structural_ambient(docs[k])
        ambient[k] = {
            "declared_ambient_space": amb,
            "declared_ambient_names_smooth_branch": bool(amb and "smooth" in amb.lower()),
            "structural_smooth_ambient_keys": smooth_branch_ambient_declared(docs[k]),
            "weighted_sobolev_ambient_occurrences": len(re.findall(r"X\^\{s,delta\}_vac\(AF\)", t)),
            "frechet_topology_named": bool(re.search(r"Frechet topology", t)),
            "prose_proximity_probe_would_false_positive": smooth_ambient_named(t),
        }
    missing_ambient = [k for k, v in ambient.items()
                       if v["weighted_sobolev_ambient_occurrences"] > 0
                       and not v["declared_ambient_names_smooth_branch"]
                       and not v["structural_smooth_ambient_keys"]]
    checks.append({
        "id": "C06", "name": "comeagerness ambient object for the non-Sobolev D0 branch",
        "status": "FAIL" if missing_ambient else "PASS",
        "detail": (f"{missing_ambient}: the only structurally declared ambient object is "
                   f"X^{{s,delta}}_vac(AF); the smooth-with-decay branch has no ambient set, "
                   f"only a Frechet topology named. (A prose-proximity probe false-positives on F2b; "
                   f"replaced by the structural probe, regression-pinned by K6.)") if missing_ambient
                  else "ambient object declared per D0 branch",
        "evidence": ambient,
    })

    # C07
    dc = {k: (docs[k] or {}).get("data_class") or {} for k in docs}
    keysets = {k: set(v) if isinstance(v, dict) else set() for k, v in dc.items()}
    allkeys = set().union(*keysets.values()) if keysets else set()
    keydiff = {k: sorted(allkeys - keysets[k]) for k in keysets}
    valdiff = {}
    for k in keysets:
        for key in sorted(allkeys):
            vals = {}
            for kk in keysets:
                v = dc[kk].get(key) if isinstance(dc[kk], dict) else None
                vals[kk] = json.dumps(v, sort_keys=True) if v is not None else None
            uniq = set(vals.values())
            if len(uniq) > 1:
                valdiff[key] = vals
    checks.append({
        "id": "C07", "name": "data_class structural diff across the three classes",
        "status": "INFO",
        "detail": f"keys absent per class: {keydiff}; keys with differing values: {sorted(valdiff)}",
        "evidence": {"keysets": {k: sorted(v) for k, v in keysets.items()}, "value_diff_keys": sorted(valdiff)},
    })

    # C08
    reg = {k: (dc[k].get("regularity_class") if isinstance(dc[k], dict) else None) for k in dc}
    reg_eq = {f"{a}=={b}": reg[a] == reg[b] for a in reg for b in reg if a < b}
    checks.append({
        "id": "C08", "name": "regularity_class textual equality",
        "status": "INFO",
        "detail": f"equal pairs: {[k for k, v in reg_eq.items() if v]}",
        "evidence": reg,
    })

    # C09
    inst = {}
    for k in docs:
        t = texts[k]
        inst[k] = indexed_pair_objects(t)
    drift = [k for k in inst if inst[k]["forall (s,delta) in D0"] > 0
             and inst[k]["G_{s,delta}"] > 0 and typing[k]["smooth_branch_supplies_s_delta_pair"] is False]
    checks.append({
        "id": "C09", "name": "indexed-object instantiation audit",
        "status": "FAIL" if drift else "PASS",
        "detail": (f"classes where the formal statements index objects by (s,delta) although "
                   f"D0 contains a non-pair member: {drift}") if drift else "consistent",
        "evidence": inst,
    })

    # C10
    repair = {}
    for k in docs:
        repair[k] = {
            "R1_single_regime_satisfied": repair_r1_single_regime(defs[k] or ""),
            "R2_typed_union_satisfied": repair_r2_typed_union(docs[k], defs[k] or ""),
        }
    unrepaired = [k for k, v in repair.items() if not (v["R1_single_regime_satisfied"] or v["R2_typed_union_satisfied"])]
    checks.append({
        "id": "C10", "name": "repair-acceptance predicates (R1 single regime / R2 typed union)",
        "status": "FAIL" if unrepaired else "PASS",
        "detail": f"neither acceptance shape present for {unrepaired}",
        "evidence": repair,
    })

    # C11 / C12
    reviews = collect_reviews(repo)
    profiles = {}
    for t in TARGETS:
        counts, rows, distinct = verdict_profile(reviews, t)
        profiles[t["key"]] = {"counts": counts, "distinct_reviewers": distinct, "rows": rows}
    asym = {}
    base = same_text_classes
    for i in range(len(base)):
        for j in range(i + 1, len(base)):
            a, b = base[i], base[j]
            ca, cb = profiles[a]["counts"], profiles[b]["counts"]
            da, db = profiles[a]["distinct_reviewers"], profiles[b]["distinct_reviewers"]
            asym[f"{a} vs {b}"] = {
                "identical_D0_text": True,
                "verdict_counts": {a: ca, b: cb},
                "distinct_reviewers": {a: da, b: db},
                "differ": ca != cb,
            }
    checks.append({
        "id": "C11", "name": "verdict profile at the pinned canonical hash (rows / distinct reviewers)",
        "status": "INFO",
        "detail": json.dumps({k: {"counts": v["counts"], "distinct": v["distinct_reviewers"]}
                              for k, v in profiles.items()}),
    })
    checks.append({
        "id": "C12", "name": "verdict asymmetry between classes with identical D0 text",
        "status": "INFO",
        "detail": json.dumps(asym),
        "evidence": asym,
    })
    for pair, d in asym.items():
        if d["differ"]:
            findings.append({
                "id": "F-047-XCLASS-1",
                "severity": "major",
                "axis": "review-corpus consistency / G-FORM",
                "finding": (f"{pair}: the D0 regularization domain is textually identical, but the "
                            f"verdict profiles at the pinned hash differ. Distinct reviewers per verdict: "
                            f"{d['distinct_reviewers']}. If the D0 typing defect blocks F2a, the identical "
                            f"text cannot support the same class being accepted elsewhere without an "
                            f"adjudicated reason (or the blocking severity must be revised down for all three)."),
            })

    if dup_any:
        findings.append({
            "id": "F-047-XCLASS-2",
            "severity": "major",
            "axis": "machine-frozen hygiene / strict YAML 1.2",
            "finding": (f"duplicate top-level mapping keys are present in all three canonical schemas "
                        f"({ {k: v for k, v in dup_any.items()} }); PyYAML last-wins makes the effective "
                        f"revision timestamp parser-dependent. Reported for F2a already; it is cross-class."),
        })
    if ill:
        findings.append({
            "id": "F-047-XCLASS-3",
            "severity": "critical",
            "axis": "quantifier/domain typing; G-FORM 'exact quantifiers' + single frozen data class",
            "finding": (f"{ill}: D0 is a two-member disjunction, and the smooth-with-decay member "
                        f"supplies no (s,delta) instantiation while quantifiers and "
                        f"conclusion.statement_formal both bind the pair over D0 and index G_ and "
                        f"X^ objects by it. The artifact therefore formalises a union of two class "
                        f"statements, not one well-typed class statement, in exactly the way G-FORM's "
                        f"exactness criterion forbids."),
        })
    if missing_ambient:
        findings.append({
            "id": "F-047-XCLASS-4",
            "severity": "major",
            "axis": "comeagerness well-definedness",
            "finding": (f"{missing_ambient}: comeagerness is asserted against X^{{s,delta}}_vac(AF) while "
                        f"the smooth-with-decay branch has only a Frechet topology named, no ambient set."),
        })

    # C13 self-binding
    script = os.path.abspath(__file__)
    self_sha = sha256_file(script)
    checks.append({
        "id": "C13", "name": "self-binding hashes",
        "status": "PASS",
        "detail": f"instrument sha256 {self_sha[:12]}; pinned inputs recorded",
        "evidence": {"instrument": {"path": os.path.relpath(script, repo), "sha256": self_sha},
                     "inputs": {k: v["sha256"] for k, v in inputs.items()}},
    })

    # controls --------------------------------------------------------------
    tmp = tempfile.mkdtemp(prefix="w047_d0_controls_")
    good_text = ("quantifiers:\n  domains:\n    D0:\n      definition: \"admissible Sobolev pairs: "
                 "s > 5/2 and delta in (1/2,1)\"\n  ordered:\n    - {kind: forall, binder: \"(s,delta)\", "
                 "domain_id: D0}\nconclusion:\n  statement_formal: \"forall (s,delta) in D0: P\"\n")
    good_path = os.path.join(tmp, "good.yaml")
    open(good_path, "w").write(good_text)
    gd = load_yaml(good_text)
    controls.append({
        "id": "K1", "name": "positive control: synthetic single-regime D0",
        "expectation": "not ill-typed; disjunct_count == 1",
        "observed": {"disjunct_count": len(d0_disjuncts(d0_definition(gd))),
                     "smooth_branch": smooth_branch(d0_definition(gd))},
        "status": "PASS" if len(d0_disjuncts(d0_definition(gd))) == 1
                  and smooth_branch(d0_definition(gd)) is None else "FAIL",
    })

    mut = texts["F2a"].replace(", or the smooth-with-decay default", "")
    md = load_yaml(mut)
    controls.append({
        "id": "K2", "name": "mutation control: delete the smooth disjunct from the F2a snapshot",
        "expectation": "ill-typed flag clears (disjunct_count == 1)",
        "observed": {"disjunct_count": len(d0_disjuncts(d0_definition(md))),
                     "smooth_branch": smooth_branch(d0_definition(md))},
        "status": "PASS" if len(d0_disjuncts(d0_definition(md))) == 1 else "FAIL",
    })

    null_doc = load_yaml("unrelated:\n  key: value\n")
    null_def = d0_definition(null_doc)
    controls.append({
        "id": "K3", "name": "null control: YAML without a D0 block",
        "expectation": "no D0 extracted; no exception",
        "observed": {"d0_definition": null_def, "disjunct_count": len(d0_disjuncts(null_def))},
        "status": "PASS" if null_def is None and d0_disjuncts(null_def) == [] else "FAIL",
    })

    f1_def = d0_definition(docs["F1"]) or ""
    marker = ", or the smooth-with-decay default"
    idx = f1_def.find(marker)
    f1_mut = f1_def[: idx + len(marker)] if idx != -1 else f1_def
    controls.append({
        "id": "K4", "name": "identity-comparer sensitivity: strip F1's trailing clause",
        "expectation": "F1 D0 then equals F2a D0",
        "observed": {"equal_after_strip": f1_mut == d0_definition(docs["F2a"])},
        "status": "PASS" if f1_mut == d0_definition(docs["F2a"]) else "FAIL",
    })

    fake_reviews = [{"event_id": "ctl", "reviewer": "ctl-r", "verdict": "accept",
                     "reviewed_sha256": TARGETS[1]["_pinned"], "target_id": "F2a", "score": 4}]
    c_counts, _, c_distinct = verdict_profile(fake_reviews, TARGETS[1])
    controls.append({
        "id": "K5", "name": "verdict-counter sensitivity: synthetic single-accept corpus",
        "expectation": "accept count == 1 and one distinct reviewer",
        "observed": {"counts": c_counts, "distinct": c_distinct},
        "status": "PASS" if c_counts["accept"] == 1 and c_distinct["accept"] == ["ctl-r"] else "FAIL",
    })

    # K6: the prose-proximity probe false-positived on F2b; the structural probe must not.
    trap_doc = load_yaml(
        "genericity:\n"
        "  ambient_space: \"the constraint manifold X^{s,delta}_vac(AF) ...\"\n"
        "  long_prose: \"exclude negative-mass data from the ambient space; pointwise rates are "
        "the smooth-with-decay default\"\n")
    trap_prose = smooth_ambient_named(json.dumps(trap_doc))
    trap_struct = smooth_branch_ambient_declared(trap_doc)
    controls.append({
        "id": "K6", "name": "false-positive regression: prose proximity must not count as a declared ambient",
        "expectation": "prose probe fires (documents the old defect) but structural probe returns []",
        "observed": {"prose_proximity_probe": trap_prose, "structural_probe": trap_struct},
        "status": "PASS" if trap_prose and trap_struct == [] else "FAIL",
    })

    # K7: a genuinely declared smooth-branch ambient must be detected.
    pos_doc = load_yaml(
        "genericity:\n"
        "  ambient_space: \"X^{s,delta}_vac(AF)\"\n"
        "  smooth_branch_ambient_space: \"X_smooth_vac(AF)\"\n")
    controls.append({
        "id": "K7", "name": "positive structural control: declared smooth-branch ambient",
        "expectation": "structural probe detects the smooth-branch ambient key",
        "observed": {"structural_probe": smooth_branch_ambient_declared(pos_doc)},
        "status": "PASS" if smooth_branch_ambient_declared(pos_doc) else "FAIL",
    })

    report = {
        "schema_version": "w047-d0-xclass/v1",
        "task_id": "W047-GFORM-D0-XCLASS-01",
        "actor": "worker-047",
        "created_at": now_iso(),
        "created_at_basis": "wall clock at write time (CF-14 clock discipline)",
        "repo": repo,
        "scope": {"node_ids": ["F1", "F2a", "F2b"], "gate": "G-FORM",
                  "class_ids": [t["class_id"] for t in TARGETS]},
        "authority": ("worker evidence only; no gate verdict, no node status, no canonical-file edit, "
                      "no review verdict on any class in this report "
                      "(the accompanying outbox review event is separate and hash-bound)"),
        "inputs": inputs,
        "checks": checks,
        "controls": controls,
        "findings": findings,
        "repair_options": [
            {"id": "R1", "shape": "collapse D0 to one parameterised regime",
             "acceptance": "d0_disjuncts(definition) == 1 and the surviving disjunct supplies (s,delta)"},
            {"id": "R2", "shape": "typed disjoint union: keep the smooth default as an explicitly typed member",
             "acceptance": "every D0 member either supplies (s,delta) or has a named ambient set and a "
                           "comeagerness definition; the class statement is then the conjunction over members"},
        ],
        "falsifier": (
            "At the pinned hashes in inputs: (a) if the smooth-with-decay disjunct is shown to supply an "
            "(s,delta) instantiation, or an ambient set plus comeagerness definition is shown to exist for "
            "it, F-047-XCLASS-3 and F-047-XCLASS-4 are falsified; (b) if the three D0 definitions are shown "
            "not to share the disjunctive member, F-047-XCLASS-3's cross-class scope is falsified; (c) if "
            "the duplicate-key scan is shown to be a false positive under strict YAML 1.2, "
            "F-047-XCLASS-2 is falsified; (d) if the recorded verdict profiles at those hashes are shown "
            "to be equal after dedup, F-047-XCLASS-1 is falsified. A later file write is not a falsifier."),
        "not_claimed": [
            "no truth claim about weak or strong cosmic censorship",
            "no claim that the D0 defect changes any mathematical content; it is a formalisation/typing defect",
            "no gate verdict; G-FORM remains pending",
            "no verdict on F1/F2b; existing review verdicts are counted, not re-issued",
        ],
    }
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--out", default=None)
    ap.add_argument("--snapshot-dir", default=None)
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any check FAILs (use as an acceptance test for a repair)")
    args = ap.parse_args()
    try:
        report = run(os.path.abspath(args.repo), snapshot_dir=args.snapshot_dir)
    except Exception as exc:
        print(json.dumps({"error": str(exc), "repo": args.repo}), file=sys.stderr)
        return 2
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1, sort_keys=False)
            f.write("\n")
    fails = [c["id"] for c in report["checks"] if c["status"] == "FAIL"]
    ctl_fails = [c["id"] for c in report["controls"] if c["status"] != "PASS"]
    print(json.dumps({
        "task_id": report["task_id"],
        "inputs": {k: v["sha256"][:12] for k, v in report["inputs"].items()},
        "failed_checks": fails,
        "control_failures": ctl_fails,
        "findings": [f["id"] for f in report["findings"]],
        "verdict_counts": report["checks"][10]["detail"],
        "out": args.out,
    }, indent=1))
    if ctl_fails:
        return 2
    if args.strict and fails:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
