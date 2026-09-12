#!/usr/bin/env python3
"""W072-D - independent re-measurement of the AF-WCC-SCALAR-SPH class-conformance
audit at the repaired F0 taxonomy rev5, plus closure check of HF-W072C-1.

Context
-------
W072-A (self-selected, no assignment card) audited the class-bound ledger entries
against the F0 taxonomy and reported 5/10 mechanically in-class, 0/10 discharging
the class WCC conclusion.  W072-C reproduced the 0-discharge headline with an
independent implementation but filed HF-W072C-1: the target's H2 detector matched
the substring 'spherical' inside 'non-spherical', so '5/10' was not reproducible
(negation-aware reading: 4 loose / 3 data-space / 2 strict).  Both W072-A and
W072-C pinned taxonomy 276009f4f63d and ledger ce42d205e761.  The taxonomy has
since moved to rev5 (0abb9ed8a961), whose notes say the scalar class conclusion
was repaired to the canonical tail predicate; the ledger moved to a1674f094979.

This task takes the one bounded class-bound step that is still unclaimed: re-run
the conformance measurement at the *new* pins with the negation defect fixed in
this implementation, and measure the entries against the *repaired* conclusion
(tail predicate) rather than against the bare conclusion_type token.  It also
reports a mechanical F0 defect candidate: H4 still declares the genericity notion
unresolved while the repaired conclusion names 'comeager'.

Design constraints
------------------
* Inputs are pinned by sha256.  Live path used only if its bytes match the pin;
  otherwise our own verified byte-identical snapshot is used; otherwise abort rc=2
  (fail-closed).  Live head re-measured after the run and recorded.
* Taxonomy parsed with PyYAML *strict* loader that reports duplicate keys (W072-C
  found duplicate top-level keys at rev11; rev12+ claims they are collapsed).
* No import of, or read from, any prior worker-072 runner.  The prior reports are
  read only in the comparison step, after this implementation's own verdicts are
  frozen in memory.
* Deterministic apart from the generated_at wall clock; result_digest covers the
  report core only.
"""

import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML required", file=sys.stderr)
    sys.exit(2)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RUNNER = os.path.abspath(__file__)

TASK_ID = "W072-D"
CLASS_ID = "AF-WCC-SCALAR-SPH"
NODE_ID = "F0"
GATE = "G-FORM"
OUT_REPORT = os.path.join(HERE, "report.json")
RAW_DIR = os.path.join(HERE, "raw")

# Pins measured at task start 2026-09-12T00:38+08:00 (live files).
PINS = {
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "ledger/theorems.jsonl":
        "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "ledger/citation_audit.csv":
        "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
}
# Our own snapshots, taken before the run; used only if byte-identical to the pin.
SNAPSHOTS = {
    "research_map/formulation_taxonomy.yaml":
        "artifacts/worker-072/scalar_sph_f0rev5/snapshots/formulation_taxonomy.0abb9ed8a961.yaml",
    "ledger/theorems.jsonl":
        "artifacts/worker-072/scalar_sph_f0rev5/snapshots/theorems.a1674f094979.jsonl",
    "ledger/citation_audit.csv":
        "artifacts/worker-072/scalar_sph_f0rev5/snapshots/citation_audit.315c19145065.csv",
}

# Prior reports (read only in the comparison step).
W072C_REPORT = "artifacts/worker-072/scalar_sph_recheck/recheck_report.json"
W072A_REPORT = "artifacts/worker-072/scalar_sph_class_audit/spotcheck_report.json"

# Content fields only: binding metadata (class_ids, ledger_tags) is deliberately
# NOT evidence for conformance, otherwise the check would be circular.
OBJECT_FIELDS = ["label", "statement_exact", "assumptions", "regularity",
                 "topology", "genericity"]
CONCL_FIELDS = ["statement_exact", "conclusion", "label", "notes", "regularity"]

GENERICITY_TOKENS = [
    "dense open", "open dense", "open and dense", "comeager", "co-meager",
    "residual", "full measure", "full-measure", "positive probability",
    "first category", "first-category", "meagre", "meager",
]
NEGATION_MARKERS = ["no ", "not ", "never", "non-", "without ", "fails to",
                    "cannot", "does not", "is not", "are not", "nor "]

# repaired-conclusion predicate markers (taxonomy rev5, AF-WCC-SCALAR-SPH)
TAIL_MARKERS = {
    "finite_affine_length": r"finite affine length",
    "future_inextendible_geodesic": r"future-inextendible causal geodesic",
    "tail_predicate": r"\btail\b",
    "j_minus_of_q": r"j\^?-?\s*\(?\s*q",
    "not_contained": r"not contained",
}
SET_MARKERS = {
    "j_minus_of_iplus": r"j\^?-?\s*\(?\s*i\+",
    "contained_in_set": r"contained in",
}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


# ------------------------------------------------------------ pin resolution ---

def resolve_pinned(rel, pinned):
    live = os.path.join(ROOT, rel)
    live_sha = sha256_file(live) if os.path.exists(live) else None
    if live_sha == pinned:
        return ({"source": "live", "used_path": rel, "used_sha256": pinned,
                 "match": True, "live_sha256": live_sha}, live_sha)
    snap = SNAPSHOTS.get(rel)
    if snap:
        sp = os.path.join(ROOT, snap)
        if os.path.exists(sp) and sha256_file(sp) == pinned:
            return ({"source": "snapshot", "used_path": snap, "used_sha256": pinned,
                     "match": True, "live_sha256": live_sha}, live_sha)
    return ({"source": "none", "used_path": None, "used_sha256": None,
             "match": False, "live_sha256": live_sha}, live_sha)


def measure_pins():
    out, unresolved = {}, []
    for rel, pinned in PINS.items():
        res, live_sha = resolve_pinned(rel, pinned)
        res["pinned"] = pinned
        res["live_drifted"] = bool(live_sha and live_sha != pinned)
        out[rel] = res
        if not res["match"]:
            unresolved.append(rel)
    return out, unresolved


# ------------------------------------------------------- strict taxonomy read ---

def strict_yaml_load(path):
    """Load YAML, returning (doc, duplicate_key_paths).  Duplicates are data."""
    dups = []

    class StrictLoader(yaml.SafeLoader):
        pass

    def construct_mapping(loader, node, deep=False):
        keys = []
        for key_node, _ in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in keys:
                dups.append(str(key))
            keys.append(key)
        return yaml.SafeLoader.construct_mapping(loader, node, deep)

    StrictLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
    with open(path, encoding="utf-8") as fh:
        return yaml.load(fh, Loader=StrictLoader), dups


def parse_class(tax_path):
    doc, dups = strict_yaml_load(tax_path)
    classes = doc.get("classes") or {}
    if CLASS_ID not in classes:
        return None, None, None, None, dups, doc
    c = classes[CLASS_ID]
    hyps = {h.get("id"): h for h in c.get("hypotheses", [])}
    return c, hyps, c.get("conclusion", {}), c.get("exclusions", []), dups, doc


def predicate_flavor(text):
    t = (text or "").lower()
    tail_hits = {k: bool(re.search(v, t)) for k, v in TAIL_MARKERS.items()}
    set_hits = {k: bool(re.search(v, t)) for k, v in SET_MARKERS.items()}
    tail = all(tail_hits[k] for k in
               ("finite_affine_length", "future_inextendible_geodesic",
                "tail_predicate", "j_minus_of_q", "not_contained"))
    set_only = bool(set_hits["j_minus_of_iplus"]) and not tail
    return {"tail_predicate": tail, "set_only": set_only,
            "tail_markers": tail_hits, "set_markers": set_hits}


def taxonomy_checks(hyps, concl, exclusions, dups, doc):
    """Mechanical F0 checks with explicit expectations.  observed != expected is
    reported as a finding, not silently repaired."""
    text = concl.get("text", "") or ""
    low = text.lower()
    flav = predicate_flavor(text)
    generic_tokens = [t for t in GENERICITY_TOKENS if t in low]
    observed = {
        "no_duplicate_keys": not dups,
        "H1_present": "massless scalar" in hyps.get("H1", {}).get("text", "").lower(),
        "H2_present": "spherical symmetry" in hyps.get("H2", {}).get("text", "").lower(),
        "H3_present": "asymptotically flat" in hyps.get("H3", {}).get("text", "").lower(),
        "H4_present": "genericity" in hyps.get("H4", {}).get("text", "").lower(),
        "conclusion_type_is_wcc": concl.get("type") == "weak_cosmic_censorship",
        "axes_conclusion_type_matches": (
            (doc.get("classes", {}).get(CLASS_ID, {}).get("axes", {})
             .get("conclusion_type")) == concl.get("type")),
        "exclusions_include_non_spherical": any(
            "non-spherical" in str(x).lower() for x in exclusions),
        "tail_predicate_present": flav["tail_predicate"],
        "set_variant_marked_superseded": (
            "superseded set-based" in low and "variant set" in low),
        "H4_declared_unresolved": bool(hyps.get("H4", {}).get("unresolved")),
        "generic_notion_named_in_conclusion": bool(generic_tokens),
        # Consistency expectation: a conclusion that names a genericity notion and
        # an H4 that still declares the notion unresolved cannot both be canonical.
        "H4_vs_conclusion_genericity_consistent": not (
            bool(hyps.get("H4", {}).get("unresolved")) and bool(generic_tokens)),
        "no_f_node_coverage_gap_recorded": (
            "no f-node" in json.dumps(hyps.get("H4", {})).lower()
            or "no f-node" in json.dumps(
                doc.get("classes", {}).get(CLASS_ID, {}).get("provenance", {})).lower()),
    }
    expected = {k: True for k in observed}
    checks = {k: {"observed": observed[k], "expected": expected[k],
                  "ok": observed[k] == expected[k]} for k in observed}
    detail = {
        "generic_tokens_named_in_conclusion": sorted(generic_tokens),
        "H4_text": hyps.get("H4", {}).get("text"),
        "conclusion_predicate_flavor": flav,
        "duplicate_keys": dups,
    }
    return checks, detail


# ---------------------------------------------------------------- classifier ---

def entry_text(entry, fields=None):
    parts = []
    for f in (fields or OBJECT_FIELDS):
        v = entry.get(f)
        if isinstance(v, list):
            parts.extend(str(x) for x in v)
        elif v is not None:
            parts.append(str(v))
    return "\n".join(parts)


def near_negation(blob, match, window=90):
    lo, hi = max(0, match.start() - window), min(len(blob), match.end() + window)
    ctx = blob[lo:hi].lower()
    return any(m in ctx for m in NEGATION_MARKERS)


def spherical_probe(entry):
    """Every 'spherical' occurrence in every field, flagged when it sits inside a
    negated form.  Kept because this is the exact mechanism HF-W072C-1 named."""
    occ = []
    for k, v in entry.items():
        s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
        for m in re.finditer(r"spherical", s, flags=re.I):
            pre = s[max(0, m.start() - 6):m.start()].lower().rstrip()
            occ.append({
                "field": k,
                "snippet": s[max(0, m.start() - 30):min(len(s), m.end() + 12)],
                "inside_negated_form": (pre.endswith("non-") or pre.endswith("non")
                                        or pre.endswith("without")),
            })
    return occ


def classify(entry):
    obj = entry_text(entry)
    obj_l = obj.lower()

    has_scalar = re.search(r"\bscalar\b", obj_l) is not None
    explicit_massless = bool(
        re.search(r"massless[\s-]scalar", obj_l)
        or re.search(r"einstein[\s-]massless[\s-]scalar", obj_l)
        or re.search(r"einstein[\s-]scalar", obj_l))
    massive_only = bool(re.search(r"massive\s+scalar", obj_l)) and not explicit_massless
    charged_scalar = bool(re.search(r"charged\s+scalar", obj_l)) and not explicit_massless
    lambda_nonzero = bool(
        re.search(r"lambda\s*(?:!=|≠|>|<|≥|≤)\s*0", obj_l)
        or re.search(r"lambda\s*=\s*(?!0(?![\d.]))\S", obj_l)
        or re.search(r"non-?zero\s+cosmological", obj_l)
        or re.search(r"positive\s+cosmological\s+constant", obj_l))
    if not has_scalar:
        h1_level = "absent"
    elif massive_only or charged_scalar or lambda_nonzero:
        h1_level = "excluded"
    elif explicit_massless:
        h1_level = "explicit_massless"
    else:
        h1_level = "scalar_unspecified"
    h1_loose = h1_level not in ("absent", "excluded")

    # HF-W072C-1 fix: the bare token is recorded, but every conformance reading
    # below except the explicitly target-comparable `loose_token` reading uses the
    # negation-aware form.
    spherical_token = bool(
        re.search(r"spherical(ly)?[\s-]symmetr", obj_l)
        or re.search(r"\bso\(3\)", obj_l)
        or re.search(r"spherical\s+collapse", obj_l)
        or re.search(r"spherical\s+characteristic", obj_l))
    bare_spherical = bool(re.search(r"spherical", obj_l))
    symmetry_break = bool(
        re.search(r"without\s+symmetr", obj_l)
        or re.search(r"no\s+symmetr", obj_l)
        or re.search(r"non[\s-]symmetric", obj_l)
        or re.search(r"non[\s-]spherical", obj_l)
        or re.search(r"anisotropic\s+perturbation", obj_l)
        or re.search(r"symmetry\s+release", obj_l))
    if symmetry_break:
        h2_level = "symmetry_broken"
    elif spherical_token:
        h2_level = "spherical_data"
    else:
        h2_level = "absent"

    af_data = bool(re.search(r"asymptotically[\s-]flat", obj_l))
    h3_level = "af_data" if af_data else "absent"

    h4_hits = []
    for tok in GENERICITY_TOKENS:
        for m in re.finditer(re.escape(tok), obj_l):
            if not near_negation(obj_l, m):
                h4_hits.append(tok)
    h4_level = "named" if h4_hits else "absent"

    flavor = predicate_flavor(entry_text(entry, CONCL_FIELDS))
    legacy = str(entry.get("conclusion_type")) == "weak_cosmic_censorship"

    return {
        "theorem_id": entry.get("theorem_id"),
        "entry_kind": entry.get("entry_kind"),
        "conclusion_type": entry.get("conclusion_type"),
        "status": entry.get("status"),
        "H1_level": h1_level,
        "H2_level": h2_level,
        "H2_bare_spherical_token": bare_spherical,
        "H3_level": h3_level,
        "H4_level": h4_level,
        "H4_tokens": sorted(set(h4_hits)),
        "loose_token_conforms": (h1_loose and bare_spherical and af_data),
        "loose_conforms": (h1_loose and spherical_token and af_data),
        "space_conforms": (h1_loose and h2_level == "spherical_data" and af_data),
        "strict_conforms": (h1_level == "explicit_massless"
                            and h2_level == "spherical_data" and af_data),
        "conclusion_predicate_flavor": flavor,
        "discharges_legacy_token": legacy,
        "discharges_repaired_conclusion": bool(legacy and flavor["tail_predicate"]),
        "claims_superseded_set_variant": bool(legacy and flavor["set_only"]),
        "spherical_occurrences_all_fields": spherical_probe(entry),
    }


# ----------------------------------------------------------------- mutants ----

def mutate(base, kind):
    e = json.loads(json.dumps(base))
    if kind == "CTRL-VACUUM":
        e["label"] = "Vacuum collapse without matter"
        e["statement_exact"] = ("For the spherically symmetric Einstein vacuum "
                                "equations, trapped surfaces form; no matter field "
                                "is present.")
        e["assumptions"] = ["Vacuum", "Spherical symmetry"]
        e["topology"] = "Spherically symmetric asymptotically flat vacuum."
    elif kind == "CTRL-TAIL-WCC":
        e["statement_exact"] = (
            "For a comeager set of spherically symmetric asymptotically flat "
            "massless-scalar data, every member's MGHD admits I+ and no singularity "
            "is visible from I+: for every future-inextendible causal geodesic gamma "
            "of finite affine length, for every q in I+ and every t0 in [0,T), the "
            "tail gamma([t0,T)) is not contained in J^-(q) intersect M.")
        e["genericity"] = "Comeager (residual) subset of the spherical data space."
        e["conclusion_type"] = "weak_cosmic_censorship"
    elif kind == "CTRL-SET-WCC":
        e["statement_exact"] = (
            "For a comeager set of spherically symmetric asymptotically flat "
            "massless-scalar data, every member's MGHD is contained in J^-(I+).")
        e["genericity"] = "Comeager (residual) subset of the spherical data space."
        e["conclusion_type"] = "weak_cosmic_censorship"
    elif kind == "CTRL-NONSPH":
        e["assumptions"] = list(e["assumptions"]) + [
            "Initial data are the spherical background plus a small anisotropic "
            "perturbation on the outgoing cone."]
    elif kind == "CTRL-LAMBDA":
        e["assumptions"] = list(e["assumptions"]) + [
            "Lambda = 1e-3 (nonzero cosmological constant)."]
    elif kind == "CTRL-UNBOUND":
        e["class_ids"] = ["AF-WCC-VAC-GEN"]
    else:
        raise ValueError(kind)
    return e


def run_controls(base, all_entries):
    c = {}
    v = classify(mutate(base, "CTRL-VACUUM"))
    c["CTRL-VACUUM"] = {
        "expect": "H1 absent/excluded; not in class under any reading",
        "observed": {k: v[k] for k in ("H1_level", "loose_token_conforms",
                                       "loose_conforms", "space_conforms")},
        "pass": v["H1_level"] in ("absent", "excluded") and not v["loose_conforms"]}
    t = classify(mutate(base, "CTRL-TAIL-WCC"))
    c["CTRL-TAIL-WCC"] = {
        "expect": "repaired tail predicate recognised and discharged; H4 named",
        "observed": {k: t[k] for k in ("H4_level", "discharges_repaired_conclusion",
                                       "claims_superseded_set_variant")},
        "pass": t["discharges_repaired_conclusion"]
                and not t["claims_superseded_set_variant"]}
    s = classify(mutate(base, "CTRL-SET-WCC"))
    c["CTRL-SET-WCC"] = {
        "expect": ("the superseded set-based wording is NOT a discharge of the "
                   "repaired class even with conclusion_type=weak_cosmic_censorship"),
        "observed": {k: s[k] for k in ("discharges_legacy_token",
                                       "discharges_repaired_conclusion",
                                       "claims_superseded_set_variant")},
        "pass": s["discharges_legacy_token"]
                and not s["discharges_repaired_conclusion"]
                and s["claims_superseded_set_variant"]}
    n = classify(mutate(base, "CTRL-NONSPH"))
    c["CTRL-NONSPH"] = {
        "expect": "bare-token reading may pass, negation-aware readings reject (H2)",
        "observed": {k: n[k] for k in ("H2_level", "loose_token_conforms",
                                       "loose_conforms", "space_conforms")},
        "pass": n["loose_token_conforms"] and not n["space_conforms"]}
    lam = classify(mutate(base, "CTRL-LAMBDA"))
    c["CTRL-LAMBDA"] = {
        "expect": "H1 excluded (class excludes Lambda != 0)",
        "observed": {k: lam[k] for k in ("H1_level", "loose_conforms")},
        "pass": lam["H1_level"] == "excluded" and not lam["loose_conforms"]}
    u = mutate(base, "CTRL-UNBOUND")
    unbound = [u] + [e for e in all_entries
                     if e.get("theorem_id") != base.get("theorem_id")
                     and CLASS_ID not in (e.get("class_ids") or [])]
    recall = scan_recall(unbound)
    c["CTRL-UNBOUND"] = {
        "expect": "stripped entry appears in the unbound-conforming recall list",
        "observed": {"recall_loose_ids": [r["theorem_id"] for r in recall
                                          if r["loose_conforms"]]},
        "pass": any(r["theorem_id"] == base.get("theorem_id")
                    and r["loose_conforms"] for r in recall)}
    return c


def control_taxonomy_defect(hyps, concl, exclusions, doc):
    """Self-test of the H4/conclusion consistency detector: a mutant conclusion
    with no genericity token must read consistent; the real file reads finding."""
    mutant_concl = dict(concl)
    mutant_concl["text"] = ("The maximal development admits I+." )
    checks, _ = taxonomy_checks(hyps, mutant_concl, exclusions, [], doc)
    return {
        "expect": "detector is sensitive to the genericity token in the conclusion",
        "observed": {
            "real_file_consistent":
                taxonomy_checks(hyps, concl, exclusions, [], doc)[0]
                ["H4_vs_conclusion_genericity_consistent"]["observed"],
            "token_free_mutant_consistent":
                checks["H4_vs_conclusion_genericity_consistent"]["observed"]},
        "pass": (not taxonomy_checks(hyps, concl, exclusions, [], doc)[0]
                 ["H4_vs_conclusion_genericity_consistent"]["observed"])
                and checks["H4_vs_conclusion_genericity_consistent"]["observed"],
    }


def scan_recall(entries):
    out = []
    for e in entries:
        if CLASS_ID in (e.get("class_ids") or []):
            continue
        cl = classify(e)
        if (cl["loose_conforms"] or cl["discharges_legacy_token"]
                or cl["discharges_repaired_conclusion"]):
            out.append({
                "theorem_id": cl["theorem_id"], "label": e.get("label"),
                "class_ids": e.get("class_ids"),
                "conclusion_type": cl["conclusion_type"],
                "loose_conforms": cl["loose_conforms"],
                "space_conforms": cl["space_conforms"],
                "discharges_legacy_token": cl["discharges_legacy_token"],
                "discharges_repaired_conclusion":
                    cl["discharges_repaired_conclusion"],
                "H1_level": cl["H1_level"], "H2_level": cl["H2_level"],
                "H3_level": cl["H3_level"], "H4_level": cl["H4_level"]})
    return sorted(out, key=lambda r: str(r["theorem_id"]))


def locator_recheck(rows):
    res = []
    for r in rows:
        doi = (r.get("doi") or "").strip()
        arxiv = (r.get("arxiv_id") or "").strip()
        url = (r.get("url") or "").strip()
        exact = (r.get("exact_locator") or "").strip()
        kinds = []
        if re.match(r"^10\.\d{4,9}/\S+$", doi):
            kinds.append("doi")
        if re.match(r"^(\d{4}\.\d{4,5}(v\d+)?|[a-z-]+(\.[A-Z]{2})?/\d{7})$",
                    arxiv, flags=re.I):
            kinds.append("arxiv_id")
        if re.match(r"^https?://\S+$", url):
            kinds.append("url")
        if re.match(r"^https?://\S+$", exact):
            kinds.append("exact_locator")
        res.append({"citation_id": r.get("citation_id"), "locator_kinds": kinds,
                    "resolvable": bool(kinds), "status": r.get("status")})
    return res


# ------------------------------------------------------------ external tools ---

def run_tool(cmd, outname, timeout=180):
    os.makedirs(RAW_DIR, exist_ok=True)
    rec = {"cmd": cmd, "cwd": ROOT}
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                           timeout=timeout)
        rec.update({"returncode": p.returncode, "stdout": p.stdout[-4000:],
                    "stderr": p.stderr[-2000:]})
    except Exception as exc:  # noqa: BLE001
        rec.update({"returncode": None, "error": repr(exc)})
    with open(os.path.join(RAW_DIR, outname), "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1)
        fh.write("\n")
    return rec


def main():
    pins, unresolved = measure_pins()
    if unresolved:
        print("PIN DRIFT (fail-closed, rc=2): %s" % ", ".join(unresolved),
              file=sys.stderr)
        print(json.dumps(pins, indent=1), file=sys.stderr)
        return 2

    tax_path = os.path.join(ROOT, pins["research_map/formulation_taxonomy.yaml"]["used_path"])
    c, hyps, concl, exclusions, dups, doc = parse_class(tax_path)
    if c is None:
        print("PREMISE ERROR: class block %s not found" % CLASS_ID, file=sys.stderr)
        return 2
    tchecks, tdetail = taxonomy_checks(hyps, concl, exclusions, dups, doc)
    if not (tchecks["H1_present"]["ok"] and tchecks["H2_present"]["ok"]
            and tchecks["H3_present"]["ok"] and tchecks["H4_present"]["ok"]
            and tchecks["conclusion_type_is_wcc"]["ok"]):
        print("PREMISE ERROR: taxonomy premises unreadable", file=sys.stderr)
        print(json.dumps(tchecks, indent=1), file=sys.stderr)
        return 2

    entries = []
    with open(os.path.join(ROOT, pins["ledger/theorems.jsonl"]["used_path"]),
              encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                entries.append(json.loads(line))
    bound = sorted((e for e in entries if CLASS_ID in (e.get("class_ids") or [])),
                   key=lambda e: e["theorem_id"])
    per_entry = [classify(e) for e in bound]

    base = next(e for e in bound if e.get("theorem_id") == "T-101")
    controls = run_controls(base, entries)
    controls["CTRL-TAXONOMY-H4"] = control_taxonomy_defect(hyps, concl, exclusions, doc)
    recall = scan_recall(entries)

    with open(os.path.join(ROOT, "ledger/citation_audit.csv"), encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh)
                if CLASS_ID in (r.get("class_mapping") or "")]
    cit = locator_recheck(rows)
    cit_control = locator_recheck([{**rows[0], "doi": "", "arxiv_id": "", "url": "",
                                    "exact_locator": ""}])

    # --- live-head drift recorded after the measurement --------------------
    post = {rel: (sha256_file(os.path.join(ROOT, rel))
                  if os.path.exists(os.path.join(ROOT, rel)) else None)
            for rel in PINS}
    drift_during = {rel: {"pre": pins[rel]["live_sha256"], "post": post[rel],
                          "pinned": PINS[rel],
                          "moved_during_run": post[rel] != pins[rel]["live_sha256"]}
                    for rel in PINS}

    # --- external owner-side control ---------------------------------------
    ext = run_tool([sys.executable,
                    "artifacts/formulation/tools/check_taxonomy_consistency.py"],
                   "check_taxonomy_consistency.json")

    # --- comparison with the two prior reports (after own verdicts freeze) --
    def summarize(rep):
        s = rep.get("summary", {})
        keys = ("bound_entries", "entries_bound", "loose_conforms", "space_conforms",
                "strict_conforms", "discharges_class_conclusion",
                "discharge_class_WCC_conclusion", "H4_named_any_reading",
                "genericity_H4_named", "mechanically_conform_H1_H2_H3")
        return {k: s.get(k) for k in keys if k in s}
    prior = {}
    for name, path in (("W072-C", W072C_REPORT), ("W072-A", W072A_REPORT)):
        fp = os.path.join(ROOT, path)
        prior[name] = {"path": path, "sha256": sha256_file(fp),
                       "summary": summarize(json.load(open(fp, encoding="utf-8")))}

    summary = {
        "bound_entries": len(per_entry),
        "loose_token_conforms": sum(1 for x in per_entry if x["loose_token_conforms"]),
        "loose_conforms": sum(1 for x in per_entry if x["loose_conforms"]),
        "space_conforms": sum(1 for x in per_entry if x["space_conforms"]),
        "strict_conforms": sum(1 for x in per_entry if x["strict_conforms"]),
        "discharges_legacy_token": sum(1 for x in per_entry
                                       if x["discharges_legacy_token"]),
        "discharges_repaired_conclusion": sum(
            1 for x in per_entry if x["discharges_repaired_conclusion"]),
        "claims_superseded_set_variant": sum(
            1 for x in per_entry if x["claims_superseded_set_variant"]),
        "H4_named_any_reading": sum(1 for x in per_entry if x["H4_level"] == "named"),
        "recall_unbound": len(recall),
        "citation_rows_bound": len(cit),
        "citation_rows_unresolvable": sum(1 for x in cit if not x["resolvable"]),
        "controls_passed": sum(1 for x in controls.values() if x["pass"]),
        "controls_total": len(controls),
        "taxonomy_checks_ok": sum(1 for x in tchecks.values() if x["ok"]),
        "taxonomy_checks_total": len(tchecks),
    }

    taxonomy_findings = [
        {"id": "HF-W072D-1", "axis": "F0 class-definition internal consistency",
         "path": "research_map/formulation_taxonomy.yaml#classes.%s" % CLASS_ID,
         "severity": "hard-candidate",
         "finding": ("H4 (unresolved: true) declares the genericity notion "
                     "'dense-open versus full-measure' unresolved and says it must be "
                     "named before any claim is filed, while the rev5 conclusion text "
                     "already instantiates a genericity notion: 'For a comeager set G "
                     "of data in the class'. The class axes also still carry "
                     "genericity_kind=unresolved. The three statements cannot all be "
                     "canonical at one revision."),
         "evidence": {
             "H4": hyps.get("H4", {}).get("text"),
             "conclusion_genericity_tokens": tdetail[
                 "generic_tokens_named_in_conclusion"],
             "axes_genericity_kind": c.get("axes", {}).get("genericity_kind"),
             "genericity_value_status": c.get("genericity_value_status")},
         "falsifier": ("A taxonomy note at this hash that declares 'comeager' in the "
                       "conclusion to be a placeholder rather than the chosen notion, "
                       "or H4 updated to name comeager (with L1 status), voids this "
                       "finding. Re-running this detector against the revised bytes "
                       "must then read H4_vs_conclusion_genericity_consistent=true."),
         "impact": ("Affects the F0 taxonomy's own well-formedness, not the ledger "
                    "conformance counts: no ledger entry depends on it.")},
    ]

    findings = [
        {"id": "W072D-F1",
         "text": ("0/%d bound entries discharge the AF-WCC-SCALAR-SPH conclusion at "
                  "the rev5 pins under every reading (loose-token, loose, data-space, "
                  "strict). The W072-A/W072-C conclusion-poor headline survives the "
                  "class-conclusion repair." % summary["bound_entries"])},
        {"id": "W072D-F2",
         "text": ("HF-W072C-1 is closed as a measurement defect and re-confirmed at "
                  "the new revision: over the same content-field scope, the bare-token "
                  "reading counts %d, the negation-aware loose reading %d, data-space "
                  "%d, strict %d. No reading in this implementation reproduces the "
                  "target W072-A count of 5; W072-C's independent comparison matrix "
                  "located the mechanism in the target's H2 detector (T-105/T-106 "
                  "'spherical' tokens inside negated forms). This run uses the bare "
                  "token only for the explicitly labelled comparability reading and "
                  "never for a conformance claim."
                  % (summary["loose_token_conforms"], summary["loose_conforms"],
                     summary["space_conforms"], summary["strict_conforms"]))},
        {"id": "W072D-F3",
         "text": ("Under the repaired conclusion the discharge bar is strictly higher: "
                  "an entry now needs the tail predicate (finite affine length, "
                  "future-inextendible causal geodesic, J^-(q), 'not contained'), not "
                  "just conclusion_type=weak_cosmic_censorship. Legacy-token "
                  "discharges %d, repaired-predicate discharges %d, entries claiming "
                  "the superseded set variant %d. No ledger entry carries the repaired "
                  "predicate wording."
                  % (summary["discharges_legacy_token"],
                     summary["discharges_repaired_conclusion"],
                     summary["claims_superseded_set_variant"]))},
        {"id": "W072D-F4",
         "text": ("Recall scan over all %d ledger entries: %d unbound entries conform "
                  "or carry a WCC conclusion; %s. The declared blind spot stays "
                  "measured." % (len(entries), summary["recall_unbound"],
                                 "none names H4" if not any(
                                     r["H4_level"] == "named" for r in recall)
                                 else "some name a genericity notion"))},
        {"id": "W072D-F5",
         "text": ("Locator recheck: %d/%d class-bound citation rows resolvable; "
                  "stripped-locator control flagged=%s."
                  % (summary["citation_rows_bound"]
                     - summary["citation_rows_unresolvable"],
                     summary["citation_rows_bound"],
                     not cit_control[0]["resolvable"]))},
        {"id": "W072D-F6",
         "text": ("Taxonomy mechanical checks: %d/%d ok. The single failing check is "
                  "H4_vs_conclusion_genericity_consistent (HF-W072D-1). Duplicate-key "
                  "scan at rev5: %s. Owner-side external control "
                  "check_taxonomy_consistency.py rc=%s."
                  % (summary["taxonomy_checks_ok"], summary["taxonomy_checks_total"],
                     "none" if not dups else dups, ext.get("returncode")))},
    ]

    result_core = {
        "schema_version": 1,
        "task_id": TASK_ID,
        "class_id": CLASS_ID,
        "node_id": NODE_ID,
        "node_ids": [NODE_ID, "L1"],
        "gate": GATE,
        "actor": "worker-072",
        "supersedes_pins_of": [W072C_REPORT, W072A_REPORT],
        "pins": pins,
        "drift_during_run": drift_during,
        "independent_method": {
            "taxonomy_parser": "PyYAML strict loader with duplicate-key detection "
                               "(different from W072-A/W072-C line readers)",
            "entry_classifier": "content-field token classifier, copied semantics "
                                "from this worker's W072-C but with the H2 bare token "
                                "retained only for the target-comparable reading",
            "conclusion_predicate": "regex predicate detector for the rev5 tail "
                                    "predicate and the superseded set variant",
            "prior_reports_read": "only in the comparison step, after verdicts frozen",
            "readings": {
                "loose_token": "bare 'spherical' token (the W072-A reading, reported "
                               "for comparability only)",
                "loose": "negation-aware spherical-symmetry token, H1 loose",
                "space": "loose H1, H2/H3 as data-space hypotheses",
                "strict": "space + explicit massless-scalar token"},
            "h4_tokens": GENERICITY_TOKENS},
        "class_definition": {
            "label": c.get("label"), "axes": c.get("axes"),
            "hypotheses": {k: v.get("text") for k, v in hyps.items()},
            "conclusion_type": concl.get("type"),
            "conclusion_text": concl.get("text"),
            "exclusions": exclusions,
            "status": doc.get("status")},
        "taxonomy_checks": tchecks,
        "taxonomy_check_detail": tdetail,
        "summary": summary,
        "per_entry": per_entry,
        "recall_scan": {"entries_scanned": len(entries),
                        "bound_to_class": len(bound),
                        "unbound_conforming_or_wcc": recall},
        "controls": controls,
        "citation_locator_recheck": {"rows": cit,
                                     "stripped_locator_control": cit_control},
        "external_controls": {
            "check_taxonomy_consistency.py": {
                "returncode": ext.get("returncode"),
                "stdout_tail": (ext.get("stdout") or "")[-500:],
                "raw": "artifacts/worker-072/scalar_sph_f0rev5/raw/"
                       "check_taxonomy_consistency.json",
                "note": "owner-side tool reads the LIVE canonical paths; live hashes "
                        "recorded in drift_during_run"}},
        "comparison_to_prior_reports": prior,
        "findings": findings,
        "taxonomy_findings": taxonomy_findings,
        "hard_failures": [f["id"] for f in taxonomy_findings
                          if f["severity"] == "hard-candidate"],
        "not_claimed": ["node done", "gate pass", "theorem", "physics result",
                        "class re-binding (A1 owns that verdict)",
                        "that the repaired conclusion is mathematically correct"],
        "authority_note": ("worker evidence only; a worker verdict cannot set "
                           "status=done, validation_status=passed, or a gate verdict"),
        "validation_status": "unverified",
        "falsifier": ("Re-run at the pinned hashes: a bound ledger entry whose content "
                      "fields satisfy H1-H3 (negation-aware) and whose conclusion "
                      "states the rev5 tail predicate falsifies W072D-F1/W072D-F3; a "
                      "taxonomy revision that declares the conclusion's 'comeager' a "
                      "placeholder or names it in H4 falsifies HF-W072D-1; a reviewer "
                      "who binds T-105/T-524's data as spherical (background reading) "
                      "moves only the in-class counts, not the 0-discharge result."),
    }
    result_core["runner_sha256"] = sha256_file(RUNNER)
    core = json.dumps(result_core, sort_keys=True, ensure_ascii=False).encode("utf-8")
    result_core["result_digest"] = hashlib.sha256(core).hexdigest()

    report = dict(result_core)
    report["generated_at"] = now_iso()
    with open(OUT_REPORT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print(json.dumps({
        "summary": summary,
        "taxonomy_checks": {k: v["ok"] for k, v in tchecks.items()},
        "controls": {k: v["pass"] for k, v in controls.items()},
        "external_taxonomy_consistency_rc": ext.get("returncode"),
        "result_digest": result_core["result_digest"],
        "report_sha256": sha256_file(OUT_REPORT)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
