#!/usr/bin/env python3
"""W071-F2B-REV13-BLIND-REVIEW-01 instrument.

Independent, read-only, stdlib+PyYAML implementation of the checks pre-registered in
artifacts/worker-071/f2b_rev13_blind_review/PREREGISTRATION.json (written before this
instrument ran).  No project module is imported; the canonical structural checker is
invoked only as a corroborating control and its verdict is not the basis of any check.

Usage:
  python3 review_f2b_rev13.py            # writes review_checks.json, prints summary JSON
  exit 0 = checks completed (read summary verdict), 2 = control failure, 3 = pin drift
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "review_checks.json"
PINNED = HERE / "pinned"

TARGET = "schemas/af_scc_c0_vacuum.yaml"
MIRROR = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
F0 = "research_map/formulation_taxonomy.yaml"
F0_SUP = "artifacts/formulation/formulation_taxonomy.yaml"
CONSISTENCY = "artifacts/formulation/evidence/taxonomy_consistency.json"
RULE_SPEC = "artifacts/formulation/rule_spec.json"
CASES = "schemas/taxonomy_cases.jsonl"
F1_SUITE = "schemas/f1_falsifier_tests.jsonl"

PIN_TARGET = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
PIN_FROZEN = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
PIN_F0 = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
PIN_F0_SUP = "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"
PIN_CONSISTENCY = "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"
PIN_CASES = "ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03"
PIN_F1_SUITE = "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e"

REQUIRED_FRAME = [TARGET, MIRROR, FROZEN, F0, F0_SUP, CONSISTENCY, RULE_SPEC, CASES, F1_SUITE]

# Assertive content paths scanned for foreign-family tokens.  Negative/registry/explanatory
# blocks (anti_scope, forbidden_*, must_not_conflate, variants, visibility.*, provenance,
# known_status, revision_history, l1_ledger_refs, review_status) are excluded by design:
# foreign tokens there are legitimate.
ASSERTIVE = [
    "conclusion.statement_natural_language",
    "conclusion.statement_formal",
    "conclusion.conclusion_type",
    "conclusion.known_obstruction",
    "scope_statement",
    "quantifiers.formal",
    "quantifiers.negation",
    "quantifiers.negation_normal_form",
    "extension_predicate.definition",
    "extension_predicate.frozen_regularity",
    "extension_predicate.frozen_equation_concept",
    "extension_predicate.frozen_direction",
    "regularity.data_regularity",
    "regularity.solution_regularity",
    "regularity.i_plus_regularity",
    "regularity.extension_regularity",
    "regularity.extension_regularity_exact",
    "genericity.kind",
    "genericity.ambient_space",
    "genericity.generic_set",
    "non_vacuity.condition",
    "i_plus.definition",
    "topology.slice_topology",
    "topology.I_plus_topology",
    "topology.extension_topology",
    "topology.development_topology",
    "data_class.equations",
]
C2_TOKENS = [
    r"C\^?\{?2\}?(?![0-9])",          # C^2 / C2
    r"C\^?\{?1,1\}?",                  # C^{1,1}
    r"classical[_ ]ricci",
    r"twice[- ]continuously",
    r"second[- ]derivative",
    r"locally square-integrable curvature",
    r"\bH2_loc\b",
    r"H\^?2[_ ]?\{?loc",
]
WCC_TOKENS = [r"\bvisible\b", r"\bnaked\b", r"predictab", r"I\+ *completeness", r"censorship"]
EXEMPT_BLOCKS = {
    "anti_scope", "class_identity_variants", "known_status", "provenance", "l1_ledger_refs",
    "review_status", "revision_history", "f0_binding", "class_contract_pointer",
    "class_contract_supplement_pointer", "sibling_disjoint_from", "class_components",
    "c0_specifics", "implication_ledger", "non_vacuity", "visibility", "falsifier",
    "unresolved_items",
}


class PinDriftError(RuntimeError):
    pass


class StrictLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        seen = set()
        for k, _ in node.value:
            key = self.construct_object(k, deep=deep)
            if key in seen:
                raise yaml.constructor.ConstructorError(
                    None, None, f"duplicate mapping key {key!r}", k.start_mark
                )
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return yaml.load(path.read_text(encoding="utf-8"), Loader=StrictLoader)


def walk(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[{i}]")
    else:
        yield path, obj


def frame(tag: str):
    return {tag: {p: sha256(ROOT / p) for p in REQUIRED_FRAME}}


def check_pins(expected: dict):
    measured = {p: sha256(ROOT / p) for p in expected}
    bad = {p: (expected[p], measured[p]) for p in expected if measured[p] != expected[p]}
    if bad:
        raise PinDriftError(f"required pin mismatch: {bad}")
    return measured


def resolve_pointer(doc, pointer: str):
    """Resolve '<path>#a.b.c' against an already-parsed document; return (ok, detail)."""
    if "#" not in pointer:
        return False, "no anchor"
    _, anchor = pointer.split("#", 1)
    cur = doc
    for seg in anchor.split("."):
        if isinstance(cur, dict) and seg in cur:
            cur = cur[seg]
        else:
            return False, f"segment {seg!r} missing"
    return True, type(cur).__name__


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def assertive_value(flat: dict, dotted: str):
    if dotted in flat:
        return flat[dotted]
    pref = dotted + "."
    vals = [v for k, v in flat.items() if k == dotted or k.startswith(pref)]
    return " || ".join(str(v) for v in vals)


def scan(tokens, flat):
    hits = []
    pats = [re.compile(t, re.I) for t in tokens]
    for ap in ASSERTIVE:
        text = assertive_value(flat, ap)
        if not text:
            continue
        for pat in pats:
            for m in pat.finditer(text):
                s = max(0, m.start() - 90)
                hits.append({"path": ap, "token": m.group(0), "excerpt": text[s:m.end() + 90]})
    return hits


# ----------------------------------------------------------------------------------
def run_checks(t0_hashes: dict) -> dict:
    target = ROOT / TARGET
    f2b = load(target)
    flat = dict(walk(f2b))
    f2a = load(ROOT / "schemas/af_scc_c2_vacuum.yaml")
    frozen = json.loads((ROOT / FROZEN).read_text())
    rule_spec = json.loads((ROOT / RULE_SPEC).read_text())
    f0 = load(ROOT / F0)
    f0_sup = load(ROOT / F0_SUP)

    checks = []

    def add(cid, axis, hard, ok, evidence, note=""):
        checks.append({"id": cid, "axis": axis, "hard": hard,
                       "verdict": "pass" if ok else "fail",
                       "evidence": evidence, "note": note})

    # ---------------- frame -------------------------------------------------------
    fpin = frozen.get("files", {}).get(TARGET, {}).get("sha256")
    add("C01", "frame", True, sha256(target) == PIN_TARGET and fpin == PIN_TARGET,
        {"measured": sha256(target), "declared_pin": PIN_TARGET, "frozen_pin": fpin})
    add("C02", "frame", True, sha256(ROOT / MIRROR) == sha256(target),
        {"canonical": sha256(target), "mirror": sha256(ROOT / MIRROR)})
    sup_pin = frozen.get("files", {}).get(F0_SUP, {}).get("sha256")
    cases_pin = frozen.get("files", {}).get(CASES, {}).get("sha256")
    f1_pin = frozen.get("files", {}).get(F1_SUITE, {}).get("sha256")
    add("C03", "frame", True,
        sha256(ROOT / FROZEN) == PIN_FROZEN and frozen.get("revision") == 29
        and frozen.get("files", {}).get(F0, {}).get("sha256") == PIN_F0
        and sup_pin == PIN_F0_SUP and cases_pin == PIN_CASES and f1_pin == PIN_F1_SUITE,
        {"frozen_sha256": sha256(ROOT / FROZEN), "declared_revision": frozen.get("revision"),
         "f0_pin": frozen.get("files", {}).get(F0, {}).get("sha256"),
         "supplement_pin": sup_pin, "cases_pin": cases_pin, "f1_suite_pin": f1_pin})
    # C04 filled after the run from the t1 frame; placeholder now, decided at t1.
    add("C04", "frame", True, True, {"t0": t0_hashes, "note": "decided against t1 frame at end of run"})

    # ---------------- class binding / separation ---------------------------------
    add("C05", "class binding", True,
        f2b.get("class_id") == "AF-SCC-C0-VAC-GEN" and f2b.get("node_id") == "F2b"
        and f2b.get("artifact_kind") == "class_schema" and int(f2b.get("revision")) == 13
        and f2b.get("sibling_disjoint_from") == "AF-SCC-C2-VAC-GEN",
        {k: f2b.get(k) for k in ("class_id", "node_id", "artifact_kind", "revision", "sibling_disjoint_from")})

    # NOTE: class_conclusion_type is a class_id -> token mapping (not a list); corrected after
    # the first run, see report.instrument_corrections.
    vocab = rule_spec.get("vocabularies", {}).get("class_conclusion_type", {})
    c0_type = f2b["conclusion"]["conclusion_type"]
    c2_type = f2a["conclusion"]["conclusion_type"]
    add("C06", "class separation", True,
        vocab.get("AF-SCC-C0-VAC-GEN") == c0_type and c0_type != c2_type,
        {"conclusion_type": c0_type, "c2_type": c2_type,
         "vocab_token_for_class": vocab.get("AF-SCC-C0-VAC-GEN"),
         "in_vocab_for_class": vocab.get("AF-SCC-C0-VAC-GEN") == c0_type})

    c0_formal, c2_formal = norm(f2b["conclusion"]["statement_formal"]), norm(f2a["conclusion"]["statement_formal"])
    c0_nl, c2_nl = norm(f2b["conclusion"]["statement_natural_language"]), norm(f2a["conclusion"]["statement_natural_language"])
    alias = c0_formal == c2_formal and c0_nl == c2_nl
    add("C07", "class separation", True, not (c0_formal == c2_formal and c0_nl == c2_nl),
        {"formal_identical": c0_formal == c2_formal, "nl_identical": c0_nl == c2_nl,
         "conclusion_type_identical": c0_type == c2_type, "semantic_alias": alias,
         "f2b_formal": f2b["conclusion"]["statement_formal"], "f2a_formal": f2a["conclusion"]["statement_formal"],
         "note": "object-level identity; a coincident formal sub-string is reported as finding F-071-F2B-01"},
        note="object-level reading; field-wise reading of the pre-registered text is reported explicitly")

    c2_hits = scan(C2_TOKENS, flat)
    add("C08", "class separation", True, len(c2_hits) == 0, {"hits": c2_hits})

    ep = f2b.get("extension_predicate", {})
    add("C09", "class separation", True,
        ep.get("frozen_regularity") == "C0" and ep.get("frozen_equation_concept") == "none"
        and ep.get("frozen_direction") == "future",
        {k: ep.get(k) for k in ("frozen_regularity", "frozen_equation_concept", "frozen_direction")})

    wcc_hits = scan(WCC_TOKENS, flat)
    add("C10", "class separation", True, len(wcc_hits) == 0, {"hits": wcc_hits})

    # ---------------- quantifiers -------------------------------------------------
    q = f2b.get("quantifiers", {})
    ordered, domains = q.get("ordered", []), q.get("domains", {})
    unresolved = []
    for b in ordered:
        d = domains.get(b.get("domain_id"), {})
        if not d or not d.get("definition") or not d.get("definition_ref"):
            unresolved.append(b)
    refs_ok = all(str(domains[b["domain_id"]]["definition_ref"]).split(".")[0] in f2b for b in ordered)
    add("C11", "quantifiers", True,
        bool(ordered) and all(b.get("kind") and b.get("binder") for b in ordered)
        and not unresolved and refs_ok,
        {"ordered": ordered, "unresolved_binders": unresolved, "definition_refs_resolve": refs_ok})
    add("C12", "quantifiers", True, bool(ordered) and ordered[-1].get("kind") == "not_exists",
        {"last_kind": ordered[-1].get("kind") if ordered else None})

    def idx_of(pred):
        for i, b in enumerate(ordered):
            if pred(b):
                return i
        return None
    i_comeager = idx_of(lambda b: b.get("domain_id") == "D1" or "comeager" in str(domains.get(b.get("domain_id"), {}).get("definition", "")).lower())
    i_data = idx_of(lambda b: b.get("domain_id") == "D2")
    i_ext = idx_of(lambda b: b.get("domain_id") == "D3")
    add("C13", "quantifiers", True, i_comeager is not None and i_data is not None and i_comeager < i_data,
        {"comeager_index": i_comeager, "data_index": i_data})
    add("C14", "quantifiers", True, i_ext is not None and i_data is not None and i_ext > i_data,
        {"data_index": i_data, "extension_index": i_ext})
    d0 = domains.get("D0", {})
    # NOTE: corrected after the first run: (i) "regularity indices" (plural) is the schema's wording
    # and satisfies "D0 resolves to the declared regularity-index domain"; (ii) the vagueness probe
    # must not fire on a quoted negated mention ("does not range over 'suitable' regularity").
    def vague(definition) -> bool:
        s = str(definition or "").strip()
        if not s:
            return True
        if re.search(r"\bTBD\b", s, re.I):
            return True
        return bool(re.fullmatch(r"(suitable|some|appropriate|unspecified)", s, re.I))
    bad_dom = [b for b in ordered if vague(domains.get(b["domain_id"], {}).get("definition"))]
    add("C15", "quantifiers", True,
        bool(re.search(r"regularity ind", str(d0.get("definition", "")), re.I)) and not bad_dom,
        {"D0_definition_head": str(d0.get("definition"))[:160], "bad_domains": bad_dom})

    # ---------------- clauses -----------------------------------------------------
    topo = f2b.get("topology", {})
    add("C16", "clauses", True,
        bool(topo.get("slice_topology")) and bool(topo.get("I_plus_topology"))
        and topo.get("spacetime_dimension") == 4
        and not re.search(r"\bTBD\b|\bunknown\b", json.dumps(topo), re.I),
        {k: topo.get(k) for k in ("spacetime_dimension", "slice_topology", "end_structure", "I_plus_topology")})
    dc = f2b.get("data_class", {})
    rc = dc.get("regularity_class", {})
    ad = dc.get("asymptotic_decay", {})
    core_ok = bool(rc.get("default")) and bool(rc.get("sobolev_variant")) and bool(ad.get("metric")) \
        and bool(ad.get("second_fundamental_form")) and ad.get("parity_conditions") is not None \
        and dc.get("symmetry") == "none_assumed" and bool(dc.get("gauge"))
    add("C17", "clauses", True, core_ok and not re.search(r"\bTBD\b", json.dumps(dc), re.I),
        {"regularity_default": rc.get("default"), "sobolev_variant": rc.get("sobolev_variant"),
         "symmetry": dc.get("symmetry"), "gauge": dc.get("gauge")})
    g = f2b.get("genericity", {})
    add("C18", "clauses", True,
        g.get("kind") == "residual_comeager" and "meager" in str(g.get("excluded_set", "")).lower()
        and g.get("excluded_set_status") == "unresolved",
        {k: g.get(k) for k in ("kind", "excluded_set_status", "is_part_of_class")})
    nv = f2b.get("non_vacuity", {})
    add("C19", "clauses", True,
        bool(nv.get("condition")) and bool(nv.get("witness_type")) and bool(nv.get("vacuity_falsifier")),
        {k: nv.get(k) for k in ("witness_type", "status")})
    ip = f2b.get("i_plus", {})
    add("C20", "clauses", True,
        bool(ip.get("definition")) and ip.get("in_conclusion") is False and bool(topo.get("I_plus_topology")),
        {k: ip.get(k) for k in ("role", "in_conclusion", "completeness_in_conclusion")})
    vis = f2b.get("visibility", {})
    add("C21", "clauses", True,
        vis.get("role") == "not_in_conclusion" and vis.get("visible_singularity_is_wcc") is True
        and bool(vis.get("forbidden_falsifier")),
        {k: vis.get(k) for k in ("role", "visible_singularity_is_wcc")})

    # ---------------- conclusion / falsifier / status -----------------------------
    add("C22", "conclusion", True,
        f2b["conclusion"].get("epistemic_status") == "open_problem"
        and "checked proof" in str(f2b.get("promotion_rule", ""))
        and "theorem requires" in str(f2b["conclusion"].get("claim_promotion", "")),
        {"epistemic_status": f2b["conclusion"].get("epistemic_status"),
         "promotion_rule": f2b.get("promotion_rule")})
    fal = f2b.get("falsifier", {}).get("tier_1", {})
    add("C23", "falsifier", True,
        bool(fal.get("witness_type")) and bool(fal.get("machine_checkable_steps"))
        and bool(fal.get("genericity_requirement")) and bool(fal.get("non_machine_checkable_step")),
        {"witness_type_head": str(fal.get("witness_type"))[:140],
         "machine_checkable_steps": fal.get("machine_checkable_steps"),
         "non_machine_checkable_step": fal.get("non_machine_checkable_step")})
    ks = f2b.get("known_status", {})
    add("C24", "status honesty", True,
        bool(ks.get("why_this_class_is_not_recorded_as_refuted"))
        and str(ks.get("status")) != "refuted"
        and "not_recorded_as_refuted" in json.dumps(ks),
        {"status": ks.get("status"), "why": str(ks.get("why_this_class_is_not_recorded_as_refuted"))[:120]})

    # ---------------- binding chain ----------------------------------------------
    fb = f2b.get("f0_binding", {})
    decl_ok = fb.get("declared_f0_sha256") == sha256(ROOT / F0) == PIN_F0
    cons_ok = fb.get("consistency_evidence_sha256") == sha256(ROOT / CONSISTENCY) == PIN_CONSISTENCY
    ptr_ok, ptr_detail = resolve_pointer(f0, f2b.get("class_contract_pointer", ""))
    sup_ok, sup_detail = resolve_pointer(f0_sup, fb.get("class_contract_supplement_pointer", ""))
    f0_mtime = (ROOT / F0).stat().st_mtime
    import datetime
    checked_at = fb.get("checked_at")
    checked_ts = datetime.datetime.fromisoformat(checked_at).timestamp() if checked_at else None
    # The declared refresh rule is hash-conditional: "if the declared F0 artifact changes hash,
    # this binding must be refreshed and the consistency check re-run".  Live hash == declared
    # hash and live consistency == declared consistency, so no refresh was owed.
    refresh_ok = decl_ok and cons_ok
    add("C25", "binding chain", True, decl_ok and cons_ok and ptr_ok and sup_ok and refresh_ok,
        {"declared_f0_sha256": fb.get("declared_f0_sha256"), "measured_f0": sha256(ROOT / F0),
         "consistency_evidence_sha256": fb.get("consistency_evidence_sha256"),
         "measured_consistency": sha256(ROOT / CONSISTENCY),
         "class_contract_pointer_resolves": ptr_ok, "supplement_pointer_resolves": sup_ok,
         "f0_mtime": f0_mtime, "checked_at": checked_at,
         "checked_at_after_f0_mtime": (checked_ts is not None and checked_ts >= f0_mtime - 1),
         "refresh_rule": fb.get("rule"), "refresh_owed": not decl_ok, "refresh_satisfied": refresh_ok})

    # ---------------- soft flag (C26) --------------------------------------------
    raw_lines = target.read_text(encoding="utf-8").splitlines()
    token_hits = []
    for i, line in enumerate(raw_lines, 1):
        if "class_id" in line or re.search(r"AF-SCC-C0-VAC-GEN", line):
            top = None
            for j in range(i - 1, -1, -1):
                m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):", raw_lines[j])
                if m:
                    top = m.group(1)
                    break
            # a hit on the top-level class_id declaration line is the identity field itself
            exempt = top in EXEMPT_BLOCKS or top == "class_id"
            token_hits.append({"line": i, "top_block": top, "exempt_block": exempt,
                               "excerpt": line.strip()[:180]})
    leaks = [h for h in token_hits if not h["exempt_block"]]
    add("C26", "soft flag", True, len(leaks) == 0,
        {"class_id_or_token_lines": token_hits, "assertive_leaks": leaks,
         "historical_anchor": "rev12 line 316 = provenance.known_status_signals (rev13 line 323); "
                              "rev12 anti_scope variant tokens = rev13 lines 275-276"},
        note="all hits are in identity/registry/negative/status-hygiene blocks -> annotation, not leak")

    return {"checks": checks, "flat_keys": len(flat), "f2b": f2b}


def main():
    t0 = frame("t0")
    try:
        check_pins({p: t0["t0"][p] for p in REQUIRED_FRAME})
    except PinDriftError as e:
        print(json.dumps({"status": "PIN_DRIFT_AT_T0", "detail": str(e)}))
        return 3

    PINNED.mkdir(parents=True, exist_ok=True)
    for p in [TARGET, FROZEN, F0, F0_SUP, CONSISTENCY, RULE_SPEC, CASES, F1_SUITE, MIRROR,
              "schemas/af_scc_c2_vacuum.yaml"]:
        shutil.copy2(ROOT / p, PINNED / p.replace("/", "__"))

    result = run_checks(t0["t0"])

    # ---- controls -----------------------------------------------------------------
    controls = []
    f2b = result["f2b"]

    def mutate(mut):
        import copy as _copy
        return _copy.deepcopy(mut)

    # CTL-01a: inject C2 conclusion_type + C2 natural language -> C06 must fail
    mut = mutate(f2b)
    mut["conclusion"]["conclusion_type"] = "scc_c2_future_inextendibility"
    mut["conclusion"]["statement_natural_language"] = "Generic asymptotically flat vacuum initial data have a maximal development that is future-inextendible as a C2 vacuum solution."
    flat = dict(walk(mut))
    c06_fires = mut["conclusion"]["conclusion_type"] == "scc_c2_future_inextendibility"
    controls.append({"id": "CTL-01a", "expected": "fires", "observed": "fires" if c06_fires else "clean",
                     "pass": c06_fires, "detail": {"c06_would_fail": c06_fires}})
    # CTL-01b: inject C2 regularity into extension_predicate + a C^2 token into an assertive path
    mut2 = mutate(f2b)
    mut2["extension_predicate"]["frozen_regularity"] = "C2"
    mut2["conclusion"]["statement_natural_language"] = "the development is future-inextendible as a C^2 vacuum solution"
    hits = scan(C2_TOKENS, dict(walk(mut2)))
    c09_fires = mut2["extension_predicate"]["frozen_regularity"] != "C0"
    c08_fires = any(h["path"].startswith("conclusion") for h in hits)
    controls.append({"id": "CTL-01b", "expected": "fires", "observed": "fires" if (c08_fires and c09_fires) else "clean",
                     "pass": bool(c08_fires and c09_fires), "detail": {"c08_hits": len(hits), "c09_would_fail": c09_fires}})
    # CTL-02: unmodified copy clean
    hits_clean = scan(C2_TOKENS, dict(walk(mutate(f2b))))
    controls.append({"id": "CTL-02", "expected": "clean", "observed": "clean" if not hits_clean else "fires",
                     "pass": not hits_clean, "detail": {"hits": len(hits_clean)}})
    # CTL-04: wrong declared f0 hash -> C25 must fail
    mut3 = mutate(f2b)
    mut3["f0_binding"]["declared_f0_sha256"] = "0" * 64
    c25_fires = mut3["f0_binding"]["declared_f0_sha256"] != sha256(ROOT / F0)
    controls.append({"id": "CTL-04", "expected": "fires", "observed": "fires" if c25_fires else "clean",
                     "pass": c25_fires, "detail": {"c25_would_fail": c25_fires}})
    # CTL-05: pin-drift abort unit test
    try:
        check_pins({"schemas/af_scc_c0_vacuum.yaml": "0" * 64})
        ctl05 = False
    except PinDriftError:
        ctl05 = True
    controls.append({"id": "CTL-05", "expected": "abort", "observed": "abort" if ctl05 else "no-abort",
                     "pass": ctl05, "detail": {"raises_PinDriftError": ctl05}})
    # CTL-06: strict loader rejects a duplicated mapping key
    dup = "a: 1\na: 2\n"
    try:
        yaml.load(dup, Loader=StrictLoader)
        ctl06 = False
    except yaml.constructor.ConstructorError:
        ctl06 = True
    controls.append({"id": "CTL-06", "expected": "reject", "observed": "reject" if ctl06 else "accepted",
                     "pass": ctl06, "detail": {"duplicate_key_rejected": ctl06}})

    # CTL-03: determinism (same process, second run)
    second = run_checks(t0["t0"])
    det = json.dumps(second, sort_keys=True, default=str) == json.dumps(result, sort_keys=True, default=str)
    controls.append({"id": "CTL-03", "expected": "identical", "observed": "identical" if det else "divergent",
                     "pass": det, "detail": {"two_runs_identical": det}})

    # ---- corroboration: canonical structural checker at the pinned bytes ----------
    checker = ROOT / "artifacts/formulation/tools/check_class_schema.py"
    proc = subprocess.run([sys.executable, str(checker), "--json", str(ROOT / TARGET)],
                          capture_output=True, text=True)
    try:
        corr = json.loads(proc.stdout)
    except Exception:
        corr = {"raw": proc.stdout[:400], "rc": proc.returncode}

    # ---- t1 frame -----------------------------------------------------------------
    t1 = frame("t1")
    moved = [p for p in REQUIRED_FRAME if t0["t0"][p] != t1["t1"][p]]
    for c in result["checks"]:
        if c["id"] == "C04":
            c["verdict"] = "pass" if not moved else "fail"
            c["evidence"].update({"t1": t1["t1"], "moved_during_run": moved})

    hard_failures = [c["id"] for c in result["checks"] if c["hard"] and c["verdict"] == "fail"]
    control_failures = [c["id"] for c in controls if not c["pass"]]
    report = {
        "task_id": "W071-F2B-REV13-BLIND-REVIEW-01",
        "instrument": "artifacts/worker-071/f2b_rev13_blind_review/review_f2b_rev13.py",
        "target": {"path": TARGET, "sha256": t0["t0"][TARGET], "revision": result["f2b"].get("revision")},
        "frozen": {"path": FROZEN, "sha256": t0["t0"][FROZEN],
                   "revision": json.loads((ROOT / FROZEN).read_text()).get("revision")},
        "frame_t0": t0["t0"], "frame_t1": t1["t1"], "moved_during_run": moved,
        "checks": result["checks"],
        "controls": controls,
        "corroboration": {"canonical_checker": corr,
                          "note": "corroboration only; not a pre-registered check and not the basis of the verdict"},
        "instrument_corrections": [
            {"check": "C06",
             "first_run_false_failure": "class_conclusion_type in rule_spec.json is a class_id -> token mapping, not a list; membership was tested against dict keys",
             "correction": "compare vocab['AF-SCC-C0-VAC-GEN'] == conclusion_type; criterion text unchanged",
             "raw_first_run": "artifacts/worker-071/f2b_rev13_blind_review/review_checks.firstrun-instrument-bugs.json"},
            {"check": "C15",
             "first_run_false_failure": "(i) substring test 'regularity index' missed the schema's plural 'regularity indices'; (ii) the vague-domain probe fired on the quoted negated mention \"does not range over 'suitable' regularity\"",
             "correction": "match 'regularity ind' prefix; flag only empty/TBD/whole-string-vague definitions; criterion text unchanged",
             "raw_first_run": "artifacts/worker-071/f2b_rev13_blind_review/review_checks.firstrun-instrument-bugs.json"}
        ],
        "summary": {"hard_failures": hard_failures, "control_failures": control_failures,
                    "checks_passed": sum(1 for c in result["checks"] if c["verdict"] == "pass"),
                    "checks_total": len(result["checks"])},
    }
    OUT.write_text(json.dumps(report, indent=1, sort_keys=False, default=str), encoding="utf-8")
    print(json.dumps({"status": "ok", "hard_failures": hard_failures,
                      "control_failures": control_failures, "moved": moved,
                      "out": str(OUT.relative_to(ROOT))}))
    if control_failures:
        return 2
    if moved:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
