#!/usr/bin/env python3
"""Candidate class-content invariance checker (worker-060) -- PROPOSAL ONLY.

Scope: the NON-conclusion-statement content axes of the AF-SCC-C2-VAC-GEN /
AF-SCC-C0-VAC-GEN class schemas.  A sibling worker (worker-068,
artifacts/worker-068/polarity12/conclusion_freeze_check.py) already has an
in-flight candidate for the conclusion-statement axis (statement_formal /
statement_natural_language / conclusion_type).  This rule set deliberately does
not duplicate that axis; it covers the axes that both canonical stages
(check_class_schema.py stage A, spec_conformance_audit.py stage B) leave
unchecked, as measured by worker-084 on FORM-HELDOUT-10:

  CI-CONTAIN  implication_ledger.extension_class_containment direction
  CI-SOB      data_class.regularity_class.sobolev_variant numeric threshold
  CI-END      topology.end_structure vs topology.slice_topology
  CI-DEV      topology.development_topology global hyperbolicity retained
  CI-EXT      extension_predicate.definition required clauses
  CI-SRC      provenance per-source status vs the frozen base
  CI-FALS     falsifier.schema_falsifiers guard set
  CI-F0       f0_binding declared hashes vs the frozen base / live bytes
  CI-EQUIV    conclusion.equivalent_rephrasings claimed equivalences
  CI-OBS      conclusion.known_obstruction preserved

Every rule compares a fixture against the PINNED canonical base of its own arm
and is structural: it never decides mathematics, class truth, or a gate verdict.
Flags are instrument findings, not verdicts.

Independent of stage A/B code: stdlib + PyYAML only.  Read-only: the script never
writes to a canonical path.

Usage:
  python3 check_class_content_invariance.py --corpus artifacts/heldout/heldout-10 --json OUT
  python3 check_class_content_invariance.py --selftest --json OUT
Exit: 0 checked; 2 usage/IO/hash error.
"""
from __future__ import annotations

import argparse
import copy
import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML required", file=sys.stderr)
    sys.exit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
RULE_IDS = [
    "CI-CONTAIN", "CI-SOB", "CI-END", "CI-DEV", "CI-EXT",
    "CI-SRC", "CI-FALS", "CI-F0", "CI-EQUIV", "CI-OBS",
]
FAMILY_OF_RULE = {
    "CI-CONTAIN": "containment-reversal",
    "CI-SOB": "sobolev-threshold-lowered",
    "CI-END": "end-structure-contradiction",
    "CI-DEV": "development-topology-weakened",
    "CI-EXT": "extension-predicate-weakened",
    "CI-SRC": "source-status-flip",
    "CI-FALS": "schema-falsifier-erasure",
    "CI-F0": "f0-binding-stale-hash",
    "CI-EQUIV": "equivalence-inflation",
    "CI-OBS": "known-obstruction-erased",
}
# foreign conclusion-family concepts that must not be sold as this class's conclusion
FOREIGN_CONCEPTS = (
    "geodesically complete", "geodesic completeness", "future geodesically complete",
    "visible singularity", "no singularity", "singularity visible",
)
STOPWORDS = {
    "that", "this", "with", "whose", "really", "bound", "statement", "class", "cited",
    "present", "already", "shown", "which", "there", "their", "other", "slots", "mode",
    "covered", "every", "internal", "failure", "new", "evidence", "direction", "never",
    "call", "subsumption", "requires", "required", "requirement", "weaker", "stronger",
}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(s) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(s))).strip().lower()


def get(obj, dotted, default=None):
    cur = obj
    for key in dotted.split("."):
        m = re.match(r"^(.+)\[(\d+)\]$", key)
        if m:
            key, idx = m.group(1), int(m.group(2))
            if not isinstance(cur, dict) or key not in cur:
                return default
            cur = cur[key]
            if not isinstance(cur, list) or idx >= len(cur):
                return default
            cur = cur[idx]
        else:
            if not isinstance(cur, dict) or key not in cur:
                return default
            cur = cur[key]
    return cur


# ---------------------------------------------------------------- rule helpers

def _num(s):
    s = norm(s).replace(" ", "")
    m = re.match(r"^(-?\d+(?:\.\d+)?)(?:/(\d+(?:\.\d+)?))?$", s)
    if not m:
        return None
    v = float(m.group(1))
    if m.group(2):
        v /= float(m.group(2))
    return v


def parse_threshold(text):
    """Return (comparator, value) from an s/delta style threshold string."""
    t = norm(text)
    words = [
        (r"strictly (?:greater|larger|bigger) than", ">"),
        (r"greater than or equal to|at least|no less than", ">="),
        (r"strictly (?:less|smaller) than", "<"),
        (r"less than or equal to|at most|no more than", "<="),
    ]
    for pat, cmp_ in words:
        m = re.search(pat + r"\s*([0-9]+(?:\.[0-9]+)?(?:\s*/\s*[0-9]+(?:\.[0-9]+)?)?)", t)
        if m:
            v = _num(m.group(1).replace(" ", ""))
            if v is not None:
                return (cmp_, v)
    m = re.search(r"([<>]=?|=)\s*([0-9]+(?:\.[0-9]+)?(?:\s*/\s*[0-9]+(?:\.[0-9]+)?)?)", t)
    if m:
        v = _num(m.group(2).replace(" ", ""))
        if v is not None:
            return (m.group(1), v)
    return None


def e_labels(text):
    """Ordered E-set labels in a containment sentence, braces stripped."""
    return [re.sub(r"[{}]", "", x).strip() for x in
            re.findall(r"E_(?:\{[^}]*\}|[A-Za-z0-9_^,\.]+)", str(text))]


def end_count(text):
    t = norm(text)
    m = re.search(r"\b(two|three|four|five|\d+)\b[\s\-]*(?:distinct\s+|asymptotically flat\s+|af\s+)*ends?\b", t)
    if m:
        word = m.group(1)
        return {"two": 2, "three": 3, "four": 4, "five": 5}.get(word, int(word) if word.isdigit() else None)
    if re.search(r"exactly one|one (?:af|asymptotically flat)?\s*end\b|one-ended|single [a-z\- ]*end", t):
        return 1
    if "more than one" in t:
        return 2
    return None


def _negated(text, pattern, window=45):
    """True iff pattern occurs inside a locally negated window."""
    t = norm(text)
    for m in re.finditer(pattern, t):
        seg = t[max(0, m.start() - window): m.end() + window]
        if re.search(r"\bnot\b|\bno\b|\bnever\b|\bwithout\b|\bnor\b|isn't|aren't|doesn't|drop|fail", seg):
            return True
    return False


def marker_words(text, min_len=5):
    return {w for w in re.findall(r"[a-z][a-z0-9\-]{%d,}" % (min_len - 1), norm(text)) if w not in STOPWORDS}


# ------------------------------------------------------------------ the rules

def rule_containment(fx, base):
    b = get(base, "implication_ledger.extension_class_containment")
    if not isinstance(b, str):
        return []  # arm has no extension-containment ledger (e.g. the WCC class)
    f = get(fx, "implication_ledger.extension_class_containment")
    if not isinstance(f, str):
        return ["CI-CONTAIN: extension_class_containment missing/not a string"]
    bl, fl = e_labels(b), e_labels(f)
    flags = []
    if bl != fl:
        flags.append(f"CI-CONTAIN: E-set order {fl} != frozen base order {bl}")
    bkind = "contains" if "contains" in norm(b) else "subset"
    fkind = "contains" if "contains" in norm(f) else "subset"
    if fkind != bkind:
        flags.append(f"CI-CONTAIN: relation kind '{fkind}' != frozen base kind '{bkind}'")
    return flags


def rule_sobolev(fx, base):
    flags = []
    for arm_path in ("data_class.regularity_class.sobolev_variant.s",
                     "data_class.regularity_class.sobolev_variant.delta"):
        bv, fv = get(base, arm_path), get(fx, arm_path)
        if bv is None:
            continue
        bp, fp = parse_threshold(bv), parse_threshold(fv)
        if bp is None:
            continue
        if fp is None:
            flags.append(f"CI-SOB: {arm_path} unparseable: {str(fv)[:80]!r}")
        elif fp != bp:
            flags.append(f"CI-SOB: {arm_path} {fp} != frozen base {bp}")
    return flags


def rule_end_structure(fx, base):
    be, bs = get(base, "topology.end_structure"), get(base, "topology.slice_topology")
    if not isinstance(be, str) and not isinstance(bs, str):
        return []
    fe, fs = get(fx, "topology.end_structure"), get(fx, "topology.slice_topology")
    flags = []
    if not isinstance(fe, str):
        return ["CI-END: topology.end_structure missing"]
    ce, cs = end_count(fe), end_count(fs)
    if ce is not None and cs is not None and ce != cs:
        flags.append(f"CI-END: end_structure says {ce} end(s) but slice_topology says {cs}")
    if be is not None and ce is not None and ce != end_count(be):
        flags.append(f"CI-END: end_structure says {ce} end(s), frozen base says {end_count(be)}")
    return flags


def rule_development(fx, base):
    b = get(base, "topology.development_topology")
    if not isinstance(b, str):
        return []
    f = get(fx, "topology.development_topology")
    if not isinstance(f, str):
        return ["CI-DEV: topology.development_topology missing"]
    flags = []
    if not re.search(r"global(?:ly)?\s+hyperbolic", norm(f)):
        flags.append("CI-DEV: development_topology does not assert global hyperbolicity")
    elif _negated(f, r"global(?:ly)?\s+hyperbolic(?:ity)?"):
        flags.append("CI-DEV: development_topology asserts global hyperbolicity only under negation")
    if "cauchy" not in norm(f):
        flags.append("CI-DEV: development_topology no longer names a Cauchy surface")
    return flags


def clause_segments(defn):
    """Map clause letter -> clause text for '(a) ... (b) ...' definitions."""
    parts = re.split(r"\((a|b|c|d|e|f)\)", str(defn))
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}


_CLAUSES = {
    "a": ("isometric embedding", r"isometric embedding", r"not\s+(?:an\s+)?isometric embedding"),
    "b": ("open, proper subset", r"\bproper\b", r"properness is not required|not required|no properness"),
    "c": ("connected", r"\bconnected\b", r"not connected|time-orientability is not"),
    "d": ("Lorentzian metric", r"lorentzian metric", r"not\s+(?:a\s+)?lorentzian|non-lorentzian"),
    "e": ("Ric = 0", r"\bric\b", r"no equation|not required"),
    "f": ("adds future points", r"adds points to the future|i\^\+\(q", r"does not add|not required"),
}


def rule_extension(fx, base):
    b = get(base, "extension_predicate.definition")
    if not isinstance(b, str):
        return []  # arm has no extension predicate (e.g. the WCC class): axis not applicable
    f = get(fx, "extension_predicate.definition")
    if not isinstance(f, str):
        return ["CI-EXT: extension_predicate.definition missing"]
    bseg, fseg = clause_segments(b), clause_segments(f)
    flags = []
    for key, (label, pat, neg) in _CLAUSES.items():
        bt = norm(bseg.get(key, ""))
        if not re.search(pat, bt) or re.search(neg, bt):
            continue  # clause not asserted (or asserted only negated) by the frozen base
        ft = norm(fseg.get(key, ""))
        if not ft:
            flags.append(f"CI-EXT: clause ({key}) '{label}' dropped from the definition")
        elif not re.search(pat, ft):
            flags.append(f"CI-EXT: required clause ({key}) '{label}' absent")
        elif re.search(neg, ft):
            flags.append(f"CI-EXT: required clause ({key}) '{label}' present only negated")
    reg = norm(get(fx, "extension_predicate.frozen_regularity") or get(base, "extension_predicate.frozen_regularity"))
    bd = norm(b)
    if reg and reg in bd and reg not in norm(f):
        flags.append(f"CI-EXT: frozen regularity '{reg}' not named in the definition")
    return flags


def rule_provenance(fx, base):
    fs, bs = get(fx, "provenance.sources"), get(base, "provenance.sources")
    if not isinstance(bs, list):
        return []
    if not isinstance(fs, list):
        return ["CI-SRC: provenance.sources missing"]
    bmap = {}
    if isinstance(bs, list):
        for s in bs:
            if isinstance(s, dict):
                bmap[norm(s.get("concept"))] = s
    top = norm(get(fx, "provenance.citation_status"))
    flags = []
    for s in fs:
        if not isinstance(s, dict):
            continue
        key, stat = norm(s.get("concept")), s.get("status")
        b = bmap.get(key)
        if stat == "verified" and (b is None or b.get("status") != "verified"):
            flags.append(f"CI-SRC: source '{key[:70]}' upgraded to verified; frozen base status="
                         f"{b.get('status') if b else '<new source>'}")
        if stat == "verified" and top != "verified" and not s.get("retrieved"):
            flags.append(f"CI-SRC: source '{key[:70]}' verified while top-level citation_status="
                         f"'{top or '<missing>'}' and no retrieval record")
    return flags


def rule_schema_falsifiers(fx, base):
    bf, ff = get(base, "falsifier.schema_falsifiers"), get(fx, "falsifier.schema_falsifiers")
    if not isinstance(bf, list) or not bf:
        return []
    if not isinstance(ff, list):
        return ["CI-FALS: falsifier.schema_falsifiers missing"]
    flags = []
    if len(ff) < len(bf):
        flags.append(f"CI-FALS: {len(ff)} guard entr(ies) < frozen base {len(bf)}")
    ftxt = " | ".join(norm(x) for x in ff)
    for i, entry in enumerate(bf):
        markers = marker_words(entry)
        if not markers:
            continue
        hit = sorted(m for m in markers if m in ftxt)
        if len(hit) < min(2, len(markers)):
            flags.append(f"CI-FALS: guard[{i}] content absent (matched {hit} of {sorted(markers)[:6]})")
    return flags


def rule_f0_binding(fx, base, live=None):
    flags = []
    for hash_field, path_field in (("declared_f0_sha256", "declared_f0_artifact"),
                                   ("consistency_evidence_sha256", "consistency_evidence")):
        bv, fv = get(base, f"f0_binding.{hash_field}"), get(fx, f"f0_binding.{hash_field}")
        if bv is None:
            continue
        if fv != bv:
            flags.append(f"CI-F0: {hash_field} {str(fv)[:16]}... != frozen base {str(bv)[:16]}...")
        if live is not None:
            p = get(fx, f"f0_binding.{path_field}")
            if isinstance(p, str):
                lp = os.path.join(ROOT, p)
                if os.path.exists(lp):
                    measured = sha256_file(lp)
                    if measured != fv:
                        flags.append(f"CI-F0: {hash_field} {str(fv)[:16]}... != live {p} {measured[:16]}...")
    return flags


def rule_equivalence(fx, base):
    b = get(base, "conclusion.equivalent_rephrasings")
    if b is None:
        return []
    fe = get(fx, "conclusion.equivalent_rephrasings")
    if fe is None:
        return []
    if not isinstance(fe, list):
        return ["CI-EQUIV: conclusion.equivalent_rephrasings not a list"]
    flags = []
    for i, e in enumerate(fe):
        if not isinstance(e, dict):
            continue
        status = norm(e.get("status"))
        if "equival" not in status or "unverified" in status:
            continue
        ph = norm(e.get("phrasing"))
        if not re.search(r"inextendib|extension", ph):
            flags.append(f"CI-EQUIV: entry[{i}] claimed equivalent but names no inextendibility/extension concept")
        for foreign in FOREIGN_CONCEPTS:
            if foreign in ph:
                flags.append(f"CI-EQUIV: entry[{i}] claimed equivalent to foreign concept '{foreign}'")
    return flags


def rule_known_obstruction(fx, base):
    b = get(base, "conclusion.known_obstruction")
    if b is None:
        return []
    f = get(fx, "conclusion.known_obstruction")
    if not isinstance(f, str):
        return ["CI-OBS: conclusion.known_obstruction missing"]
    t = norm(f)
    flags = []
    if re.search(r"no\s+(?:known\s+)?obstruction|obstruction\s+is\s+not\s+known|"
                 r"not\s+known\s+to\s+be\s+an?\s+obstruction|no\s+known\s+obstruction", t):
        flags.append("CI-OBS: known_obstruction asserts that no obstruction is known")
    if "kerr" not in t:
        flags.append("CI-OBS: known_obstruction no longer names the Kerr obstruction")
    return flags


RULES = {
    "CI-CONTAIN": rule_containment,
    "CI-SOB": rule_sobolev,
    "CI-END": rule_end_structure,
    "CI-DEV": rule_development,
    "CI-EXT": rule_extension,
    "CI-SRC": rule_provenance,
    "CI-FALS": rule_schema_falsifiers,
    "CI-F0": rule_f0_binding,
    "CI-EQUIV": rule_equivalence,
    "CI-OBS": rule_known_obstruction,
}


def check_fixture(fx, base, live=False):
    flags = {}
    for rid in RULE_IDS:
        try:
            got = RULES[rid](fx, base) if not (rid == "CI-F0" and live) else RULES[rid](fx, base, live=True)
        except Exception as exc:  # a checker crash is itself a flag
            got = [f"{rid}: rule crashed: {type(exc).__name__}: {exc}"]
        if got:
            flags[rid] = got
    return flags


# --------------------------------------------------------------- corpus runner

def run_corpus(corpus_dir, live=False):
    man = json.load(open(os.path.join(corpus_dir, "manifest.json")))
    man_sha = sha256_file(os.path.join(corpus_dir, "manifest.json"))
    bases, base_hashes = {}, {}
    for arm in ("W", "C2", "C0"):
        spec = man.get("bases", {}).get(arm)
        if not spec:
            continue
        p = spec["path"] if isinstance(spec, dict) else spec
        bs = spec.get("sha256") if isinstance(spec, dict) else None
        cand = p if os.path.exists(p) else os.path.join(ROOT, p)
        measured = sha256_file(cand)
        if bs and measured != bs:
            raise SystemExit(f"[exit2] base {p} hash drift {measured[:16]} != manifest {bs[:16]}")
        bases[arm] = yaml.safe_load(open(cand))
        base_hashes[arm] = {"path": p, "manifest_sha256": bs, "measured_sha256": measured,
                            "match": (bs is None or measured == bs)}
    rows = []
    for group, items in (("mutant", man.get("mutants", [])), ("control", man.get("controls", []))):
        for x in items:
            p = x["path"]
            cp = p if os.path.exists(p) else os.path.join(ROOT, p)
            measured = sha256_file(cp)
            if measured != x.get("sha256"):
                raise SystemExit(f"[exit2] fixture hash drift {p}: {measured[:16]} != {x['sha256'][:16]}")
            arm = x.get("arm")
            base = bases.get(arm) or bases.get("C2")
            fx = yaml.safe_load(open(cp))
            flags = check_fixture(fx, base, live=live)
            rows.append({
                "name": x.get("fixture") or os.path.basename(p),
                "mutation_id": x.get("mutation_id"),
                "group": group,
                "arm": arm,
                "class_id": x.get("class_id") or fx.get("class_id"),
                "family": x.get("family") or x.get("kind"),
                "rephrased": x.get("rephrased"),
                "path": p,
                "sha256": measured,
                "flags": flags,
                "verdict": "FLAG" if flags else "PASS",
            })
    # frozen canonicals (read from corpus bases) as the instrument-validity controls
    canon = []
    for arm, obj in bases.items():
        flags = check_fixture(obj, obj, live=live)
        canon.append({"name": f"frozen_canonical_{arm}", "group": "frozen_canonical", "arm": arm,
                      "path": man["bases"][arm]["path"] if isinstance(man["bases"][arm], dict) else man["bases"][arm],
                      "sha256": base_hashes[arm]["measured_sha256"], "flags": flags,
                      "verdict": "FLAG" if flags else "PASS"})
    return man, man_sha, base_hashes, rows + canon


def summarise(rows):
    def block(sel):
        n = len(sel)
        flagged = [r for r in sel if r["verdict"] == "FLAG"]
        return {"n": n, "flagged": len(flagged), "escaped": n - len(flagged),
                "escape_rate": round((n - len(flagged)) / n, 4) if n else None,
                "flagged_names": [r["name"] for r in flagged]}
    muts = [r for r in rows if r["group"] == "mutant"]
    informative = [r for r in muts if r["arm"] in ("C2", "C0")]
    per_rule = {rid: sum(1 for r in rows if rid in r["flags"]) for rid in RULE_IDS}
    per_family = {}
    for r in muts:
        fam = r["family"] or "?"
        d = per_family.setdefault(fam, {"n": 0, "caught": 0, "mutants": []})
        d["n"] += 1
        d["mutants"].append(r["name"])
        if r["verdict"] == "FLAG":
            d["caught"] += 1
    controls = [r for r in rows if r["group"] in ("control", "frozen_canonical")]
    return {
        "all_mutants": block(muts),
        "informative_c2c0": block(informative),
        "wcc_arm": block([r for r in muts if r["arm"] == "W"]),
        "controls": block(controls),
        "per_rule_catch_counts_all_mutants": per_rule,
        "per_family": per_family,
        "misses_informative": [r["name"] for r in informative if r["verdict"] == "PASS"],
        "false_positives_controls": [r["name"] for r in controls if r["verdict"] == "FLAG"],
    }


# ------------------------------------------------------------- fresh self-test

def fresh_corpus(base):
    """Independently worded mutants + conforming rephrases (no reuse of
    worker-084 fixture text).  Returns (name, arm, obj, expect_flag, family)."""
    out = []
    b = copy.deepcopy(base)

    def mut(name, family, edit):
        o = copy.deepcopy(base)
        edit(o)
        out.append((name, "C2", o, True, family))

    def conf(name, edit):
        o = copy.deepcopy(base)
        edit(o)
        out.append((name, "C2", o, False, "conforming-rephrase"))

    def set_contain(o, txt):
        o["implication_ledger"]["extension_class_containment"] = txt

    bl = e_labels(get(base, "implication_ledger.extension_class_containment"))
    kind = "contains" if "contains" in norm(get(base, "implication_ledger.extension_class_containment")) else "subset"

    mut("s01_contain_reversed_alt", "containment-reversal",
        lambda o: set_contain(o, "the extension sets are ordered " + " , ".join(reversed(bl)) +
                              " (largest first), so regularity is what shrinks them"))
    conf("s01c_contain_reworded", lambda o: set_contain(
        o, "the extension sets nest as " + " \u2286 ".join(bl) + " with no other relation asserted"))
    mut("s02_sobolev_lowered_alt", "sobolev-threshold-lowered",
        lambda o: o["data_class"]["regularity_class"]["sobolev_variant"].__setitem__("s", "s > 2"))
    conf("s02c_sobolev_reworded", lambda o: o["data_class"]["regularity_class"]["sobolev_variant"].__setitem__(
        "s", "s strictly greater than 5/2"))
    mut("s03_end_two_alt", "end-structure-contradiction",
        lambda o: o["topology"].__setitem__("end_structure", "the slice possesses two asymptotically flat ends"))
    conf("s03c_end_reworded", lambda o: o["topology"].__setitem__(
        "end_structure", "exactly one asymptotically flat end (the slice is one-ended)"))
    mut("s04_dev_negated_alt", "development-topology-weakened",
        lambda o: o["topology"].__setitem__(
            "development_topology", "M admits a Cauchy surface; no global hyperbolicity is assumed"))
    conf("s04c_dev_reworded", lambda o: o["topology"].__setitem__(
        "development_topology", "The development M is globally hyperbolic and Sigma is a Cauchy surface of M"))
    mut("s05_extension_clauses_dropped", "extension-predicate-weakened",
        lambda o: o["extension_predicate"].__setitem__(
            "definition", re.sub(r"\(b\).*?; \(c\)", "(b) iota(M) sits inside M'; (c)",
                                 o["extension_predicate"]["definition"], flags=re.S).rsplit("; (f)", 1)[0]))
    conf("s05c_extension_reworded", lambda o: o["extension_predicate"].__setitem__(
        "definition", "Definition. " + o["extension_predicate"]["definition"].replace(" iff: ", " if and only if: ")))
    mut("s06_source_verified_alt", "source-status-flip",
        lambda o: (o["provenance"]["sources"][-1].__setitem__("status", "verified"),
                   o["provenance"]["sources"][-1].__setitem__("identifier", "arXiv:1507.00601")))
    conf("s06c_source_reworded", lambda o: o["provenance"]["sources"].reverse())
    mut("s07_falsifiers_emptied_alt", "schema-falsifier-erasure",
        lambda o: o["falsifier"].__setitem__("schema_falsifiers",
                                             ["none: every internal failure mode is covered elsewhere"] * 4))
    conf("s07c_falsifiers_reworded", lambda o: o["falsifier"]["schema_falsifiers"].reverse())
    mut("s08_f0_hash_wrong_alt", "f0-binding-stale-hash",
        lambda o: o["f0_binding"].__setitem__("consistency_evidence_sha256", "0" * 64))
    conf("s08c_f0_timestamp_only", lambda o: o["f0_binding"].__setitem__("checked_at", "2026-09-12T02:00:00+08:00"))
    mut("s09_equiv_foreign_alt", "equivalence-inflation",
        lambda o: o["conclusion"].setdefault("equivalent_rephrasings", []).append(
            {"phrasing": "the development is future geodesically complete", "status": "equivalent by definition"}))
    conf("s09c_equiv_reworded", lambda o: o["conclusion"].setdefault("equivalent_rephrasings", []).append(
        {"phrasing": "no proper future C2 extension of the development exists", "status": "equivalent by definition"}))
    mut("s10_obstruction_erased_alt", "known-obstruction-erased",
        lambda o: o["conclusion"].__setitem__(
            "known_obstruction", "no obstruction to inextendibility is known in this class"))
    conf("s10c_obstruction_reworded", lambda o: o["conclusion"].__setitem__(
        "known_obstruction", "Kerr exact vacuum data are extendible, so the generic quantifier is required "
                             "and the excluded family must be shown meager"))
    return out


def run_fresh(base, live=False):
    rows = []
    for name, arm, obj, expect, family in fresh_corpus(base):
        flags = check_fixture(obj, base, live=live)
        got = "FLAG" if flags else "PASS"
        rows.append({"name": name, "group": "fresh_%s" % ("mutant" if expect else "conforming"),
                     "arm": arm, "family": family, "expected": "FLAG" if expect else "PASS",
                     "verdict": got, "flags": flags,
                     "agree": got == ("FLAG" if expect else "PASS")})
    caught = sum(1 for r in rows if r["expected"] == "FLAG" and r["verdict"] == "FLAG")
    total = sum(1 for r in rows if r["expected"] == "FLAG")
    fp = [r["name"] for r in rows if r["expected"] == "PASS" and r["verdict"] == "FLAG"]
    return {"rows": rows, "fresh_mutants": total, "fresh_caught": caught,
            "fresh_escape_rate": round((total - caught) / total, 4) if total else None,
            "fresh_conforming": sum(1 for r in rows if r["expected"] == "PASS"),
            "fresh_false_positives": fp}


# ----------------------------------------------------------------------- main

def compose_w068(rows, tool):
    """Union measurement with the independent in-flight conclusion-axis candidate
    (worker-068).  The tool is invoked read-only; the union is a worker-level
    composition of two candidate rule sets, not an adopted gate rule."""
    if not os.path.exists(tool):
        return {"error": f"tool not found: {tool}"}
    tool_sha = sha256_file(tool)
    base_of = {"C2": "artifacts/heldout/heldout-10/bases/af_scc_c2_vacuum.yaml",
               "C0": "artifacts/heldout/heldout-10/bases/af_scc_c0_vacuum.yaml",
               "W": "artifacts/heldout/heldout-10/bases/af_wcc_vacuum.yaml"}
    out_rows = []
    for r in rows:
        arm = r.get("arm") or "C2"
        cp = subprocess.run(
            [sys.executable, tool, "--fixture", r["path"], "--base", base_of[arm],
             "--variant", "freeze_statements", "--json"],
            capture_output=True, text=True, timeout=180)
        try:
            verdict = json.loads(cp.stdout).get("verdict")
        except Exception:
            verdict = f"ERR(exit {cp.returncode})"
        mine = r["verdict"] == "FLAG"
        theirs = verdict == "FLAG"
        out_rows.append({"name": r["name"], "group": r["group"], "arm": arm, "family": r.get("family"),
                         "mine": r["verdict"], "w068_freeze_statements": verdict,
                         "union": "FLAG" if (mine or theirs) else "PASS", "w068_exit": cp.returncode})
    def block(sel):
        n = len(sel)
        caught = sum(1 for x in sel if x["union"] == "FLAG")
        return {"n": n, "union_caught": caught, "union_escape": n - caught,
                "union_escape_rate": round((n - caught) / n, 4) if n else None}
    muts = [x for x in out_rows if x["group"] == "mutant"]
    informative = [x for x in muts if x["arm"] in ("C2", "C0")]
    controls = [x for x in out_rows if x["group"] in ("control", "frozen_canonical")]
    return {"tool": tool, "tool_sha256": tool_sha, "variant": "freeze_statements",
            "authority": "worker-level composition of two PROPOSAL rule sets; not an adopted gate rule",
            "rows": out_rows,
            "informative_c2c0": block(informative),
            "all_mutants": block(muts),
            "controls": block(controls),
            "control_false_positives": [x["name"] for x in controls if x["union"] == "FLAG"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="artifacts/heldout/heldout-10")
    ap.add_argument("--json", default=None)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--live", action="store_true", help="also compare f0_binding hashes to live bytes")
    ap.add_argument("--compose-w068", default=None,
                    help="path to worker-068 conclusion_freeze_check.py for a union measurement")
    ap.add_argument("--stamp", default=None, help="fixed run timestamp for reproducibility")
    args = ap.parse_args()

    result = {
        "artifact": "worker-060 class-content invariance candidate rule set (PROPOSAL)",
        "worker": "worker-060",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "control_class_ids": ["AF-WCC-VAC-GEN"],
        "authority": "worker measurement evidence only; no gate verdict, no theorem, no canonical write",
        "run_at": args.stamp or _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "axes": {rid: FAMILY_OF_RULE[rid] for rid in RULE_IDS},
        "generated_by": os.path.abspath(__file__),
        "generated_by_sha256": sha256_file(os.path.abspath(__file__)),
    }
    exit_code = 0

    if args.selftest:
        base = yaml.safe_load(open(os.path.join(ROOT, "artifacts/heldout/heldout-10/bases/af_scc_c2_vacuum.yaml")))
        result["fresh_corpus"] = run_fresh(base, live=args.live)
        result["selftest_only"] = True
    else:
        cdir = args.corpus if os.path.isabs(args.corpus) else os.path.join(ROOT, args.corpus)
        man, man_sha, base_hashes, rows = run_corpus(cdir, live=args.live)
        result["corpus"] = {"id": man.get("corpus_id"), "dir": os.path.relpath(cdir, ROOT),
                            "manifest_sha256": man_sha, "frozen_revision": man.get("frozen_revision"),
                            "pins": man.get("pins"), "bases": base_hashes}
        result["measurement"] = summarise(rows)
        result["rows"] = rows
        result["fresh_corpus"] = run_fresh(
            yaml.safe_load(open(os.path.join(ROOT, "artifacts/heldout/heldout-10/bases/af_scc_c2_vacuum.yaml"))),
            live=args.live)
        if args.compose_w068:
            tool = args.compose_w068 if os.path.isabs(args.compose_w068) else os.path.join(ROOT, args.compose_w068)
            result["union_with_worker068"] = compose_w068(rows, tool)
        iv = result["measurement"]["controls"]
        result["instrument_validity"] = {
            "frozen_canonicals_and_controls_all_pass": iv["flagged"] == 0,
            "control_flagged": iv["flagged_names"],
        }
        if iv["flagged"]:
            exit_code = 2
        if not result["instrument_validity"]["frozen_canonicals_and_controls_all_pass"]:
            result["invalid_reasons"] = [f"control flagged: {n}" for n in iv["flagged_names"]]

    text = json.dumps(result, indent=1, sort_keys=True, default=str)
    if args.json:
        outp = args.json if os.path.isabs(args.json) else os.path.join(ROOT, args.json)
        os.makedirs(os.path.dirname(outp), exist_ok=True)
        with open(outp, "w") as f:
            f.write(text + "\n")
    print(text if not args.json else json.dumps({
        "wrote": args.json,
        "measurement": result.get("measurement"),
        "fresh": {k: v for k, v in result.get("fresh_corpus", {}).items() if k != "rows"},
        "instrument_validity": result.get("instrument_validity"),
    }, indent=1, default=str))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
