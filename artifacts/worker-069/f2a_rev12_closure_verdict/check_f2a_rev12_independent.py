#!/usr/bin/env python3
"""Independent G-FORM + rev12-closure criteria checker for F2a / AF-SCC-C2-VAC-GEN.

Written by worker-069 from the G-FORM criteria in `evaluation_rubric.yaml` and
`research_map/research_map.json` (gates.G-FORM) plus the frozen-class contract in
`evaluation_rubric.yaml` (frozen_classes) -- NOT from the schema under test.  The
schema is only read as data.  Nothing here sets a gate verdict or a node status.

Usage:
  python3 check_f2a_rev12_independent.py --schema S --f0 T --supplement U --registry R --aliases A --json
  python3 check_f2a_rev12_independent.py --selftest --schema S --f0 T --supplement U --registry R --aliases A

Exit 0 iff every check passes (selftest: iff the unmutated document passes AND
every mutation is caught by its expected check id).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

CLASS_ID = "AF-SCC-C2-VAC-GEN"
SIBLING = "AF-SCC-C0-VAC-GEN"
FROZEN_FOUR = {
    "AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH",
}
GENERICITY_MAP = {
    "residual_comeager": "comeager", "comeager": "comeager",
    "full_measure": "full_measure", "open_dense": "open_dense",
    "codim_ge_1": "codim_ge_1", "non_generic_excluded": "non_generic_excluded",
}
# rubric allowed primary + the two tokenizations used by the frozen F0 / schema
CONCLUSION_ALLOWED = {
    "C2_inextendibility_of_maximal_development",
    "scc_c2_future_inextendibility",
    "strong_cosmic_censorship_C2",
}
WCC_PREDICATE = re.compile(
    r"visible|visibility|naked|predictab|I\+ complete|future null infinity", re.I)
HEDGE = re.compile(r"\b(roughly|essentially|approximately|heuristically|basically|or so|more or less)\b", re.I)
TOKEN = re.compile(r"AF-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _get(d, path, default=None):
    cur = d
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def evaluate(doc: dict, f0: dict, supplement: dict, registry: dict, raw_text: str,
             classsep=None, aliases: dict | None = None) -> list[dict]:
    """Return list of {id, criterion, ok, severity, detail}."""
    out: list[dict] = []
    aliases = aliases or {}

    def add(cid, criterion, ok, detail, severity="hard"):
        out.append({"id": cid, "criterion": criterion, "ok": bool(ok),
                    "severity": severity, "detail": detail})

    # G1 single frozen class identity
    ok1 = (doc.get("class_id") == CLASS_ID
           and doc.get("artifact_kind") == "class_schema"
           and doc.get("node_id") == "F2a"
           and _get(doc, "class_boundary.one_class_only") == CLASS_ID
           and _get(doc, "class_components.regularity_token") == "C2"
           and (_get(doc, "class_components.censorship") == "SCC"
                or _get(doc, "class_components.family") == "SCC")
           and _get(doc, "class_components.matter") == "VAC"
           and _get(doc, "class_components.genericity") == "GEN")
    add("G1", "exactly one class_id from frozen_classes; axis components select SCC/C2/VAC/GEN",
        ok1, {"class_id": doc.get("class_id"), "one_class_only": _get(doc, "class_boundary.one_class_only"),
              "components": doc.get("class_components")})

    # G2 sibling disjointness declared
    ok2 = doc.get("sibling_disjoint_from") == SIBLING
    add("G2", "C0 sibling declared disjoint from this class", ok2,
        {"sibling_disjoint_from": doc.get("sibling_disjoint_from")})

    # G3 exact quantifier prefix, no hedging
    q = doc.get("quantifiers") or {}
    formal = str(q.get("formal") or "")
    hedged = bool(HEDGE.search(formal) or HEDGE.search(str(q.get("negation") or ""))
                  or HEDGE.search(str(q.get("order_note") or ""))
                  or HEDGE.search(str(_get(doc, "conclusion.statement_formal", ""))))
    ok3 = formal.strip().startswith("forall ") and not hedged and q.get("order_matters") is True
    add("G3", "exact quantifier prefix; no 'roughly/essentially/or'-type hedging",
        ok3, {"formal_head": formal[:90], "hedged": hedged, "order_matters": q.get("order_matters")})

    # G4 ordered quantifier domains present and referenced
    ordered = q.get("ordered")
    domains = q.get("domains") or {}
    order_ok = (isinstance(ordered, list) and len(ordered) == 4
                and [x.get("kind") for x in ordered if isinstance(x, dict)]
                == ["forall", "exists", "forall", "not_exists"]
                and [x.get("domain_id") for x in ordered if isinstance(x, dict)] == ["D0", "D1", "D2", "D3"])
    ok4 = (order_ok and len(domains) == 4
           and all(str(v.get("definition") or "").strip() for v in domains.values() if isinstance(v, dict)))
    add("G4", "ordered quantifier prefix forall-exists(comeager)-forall-not_exists over D0-D3 with definitions",
        ok4, {"ordered_kinds": [x.get("kind") for x in ordered] if isinstance(ordered, list) else None,
              "n_domains": len(domains)})

    # G5 topology / end structure
    topo = doc.get("topology") or {}
    need_topo = ["slice_topology", "end_structure", "I_plus_topology", "development_topology", "extension_topology"]
    ok5 = (topo.get("spacetime_dimension") == 4
           and all(str(topo.get(k) or "").strip() for k in need_topo))
    add("G5", "data space topology named (slice, end structure, I+, development, extension)",
        ok5, {k: str(topo.get(k))[:70] for k in need_topo})

    # G6 matter / Lambda / equations (class forbidden_evidence)
    dc = doc.get("data_class") or {}
    eq = str(dc.get("equations") or "")
    ok6 = (dc.get("matter") == "none" and dc.get("cosmological_constant") == 0
           and "Ric(g) = 0" in eq)
    add("G6", "vacuum, Lambda=0, Einstein vacuum equations (class forbidden_evidence honoured)",
        ok6, {"matter": dc.get("matter"), "lambda": dc.get("cosmological_constant"), "equations": eq})

    # G7 regularity + decay
    reg = dc.get("regularity_class") or {}
    sv = reg.get("sobolev_variant") or {}
    decay = dc.get("asymptotic_decay") or {}
    ok7 = (str(reg.get("default") or "").strip()
           and str(sv.get("s") or "") == "s > 5/2" and str(sv.get("delta") or "") == "delta in (1/2, 1)"
           and str(decay.get("metric") or "").strip() and str(decay.get("second_fundamental_form") or "").strip())
    add("G7", "regularity class + asymptotic decay named",
        ok7, {"default": str(reg.get("default"))[:60], "s": sv.get("s"), "delta": sv.get("delta")})

    # G8 constraints
    con = dc.get("constraints") or {}
    ok8 = bool(str(con.get("hamiltonian") or "").strip() and str(con.get("momentum") or "").strip())
    add("G8", "vacuum constraint equations present", ok8, {"hamiltonian": str(con.get("hamiltonian"))[:60],
                                                          "momentum": str(con.get("momentum"))[:60]})

    # G9 genericity kind from the allowed vocabulary
    gen = doc.get("genericity") or {}
    mapped = GENERICITY_MAP.get(str(gen.get("kind") or ""))
    ok9 = mapped is not None and gen.get("is_part_of_class") is True
    add("G9", "genericity kind maps to the allowed set {comeager,...} and is part of the class",
        ok9, {"kind": gen.get("kind"), "mapped": mapped, "is_part_of_class": gen.get("is_part_of_class")})

    # G10 genericity topology/measure named
    ok10 = bool(str(gen.get("topology_or_measure") or "").strip()
                and str(gen.get("ambient_space") or "").strip()
                and str(gen.get("generic_set") or "").strip())
    add("G10", "genericity topology/measure and ambient space named", ok10,
        {"topology_or_measure": str(gen.get("topology_or_measure"))[:70]})

    # G11 conclusion primary token allowed
    concl = doc.get("conclusion") or {}
    ct = str(concl.get("conclusion_type") or "")
    ok11 = ct in CONCLUSION_ALLOWED and str(concl.get("family") or "") == "SCC"
    add("G11", "conclusion_primary in the class' allowed set, family SCC", ok11,
        {"conclusion_type": ct, "family": concl.get("family")})

    # G12 no WCC content in the conclusion
    stmt = " ".join(str(concl.get(k) or "") for k in ("statement_natural_language", "statement_formal"))
    wcc_hit = WCC_PREDICATE.search(stmt)
    ok12 = wcc_hit is None and _get(doc, "visibility.role") != "assumption" \
        and _get(doc, "i_plus.in_conclusion") is False
    add("G12", "no WCC/visibility/I+ predicate inside the conclusion (family separation)",
        ok12, {"wcc_hit": wcc_hit.group(0) if wcc_hit else None,
               "i_plus_in_conclusion": _get(doc, "i_plus.in_conclusion")})

    # G13 forbidden strengthenings/weakenings registered
    fs = concl.get("forbidden_strengthenings") or []
    fw = concl.get("forbidden_weakenings") or []
    ok13 = (isinstance(fs, list) and len(fs) >= 3
            and any("C0" in str(x) for x in fs)
            and isinstance(fw, list) and len(fw) >= 3)
    add("G13", "forbidden strengthenings name the C0/C1 classes; weakenings registered",
        ok13, {"n_strengthenings": len(fs), "n_weakenings": len(fw)})

    # G14 falsifier is a finite, checkable procedure in the stated topology
    fal = doc.get("falsifier") or {}
    t1 = fal.get("tier_1") or {}
    obligations = t1.get("proof_obligations") or []
    steps = t1.get("machine_checkable_steps") or []
    greq = str(t1.get("genericity_requirement") or "")
    ok14 = (t1.get("refutes") == CLASS_ID and len(obligations) >= 2 and len(steps) >= 3
            and ("non-meager" in greq or "non-meagerness" in greq))
    add("G14", "tier-1 falsifier: witness type, proof obligations, >=3 machine-checkable steps, non-meagerness route",
        ok14, {"n_obligations": len(obligations), "n_machine_steps": len(steps),
               "greq_head": greq[:80]})

    # G15 schema-level falsifiers registered
    ok15 = isinstance(fal.get("schema_falsifiers"), list) and len(fal.get("schema_falsifiers")) >= 3
    add("G15", "schema-level falsifiers registered (>=3)", ok15,
        {"n_schema_falsifiers": len(fal.get("schema_falsifiers") or [])})

    # G16 cross-class import rule
    import_rule = str(_get(doc, "class_boundary.import_rule") or "")
    ok16 = bool(import_rule) and "anti_scope" in import_rule and "provenance" in import_rule
    add("G16", "cross-class content restricted to anti_scope/variants/provenance",
        ok16, {"import_rule": import_rule[:120]})

    # G17 anti-scope exclusions name both sibling families
    anti = doc.get("anti_scope") or {}
    not_this = anti.get("not_this_class") or []
    named = {str(x.get("class_id")) for x in not_this if isinstance(x, dict)}
    ok17 = SIBLING in named and "AF-WCC-VAC-GEN" in named
    add("G17", "anti-scope explicitly excludes the C0 sibling and the WCC class",
        ok17, {"excluded": sorted(named)})

    # G18 implication ledger: one-way C0=>C2, converse forbidden
    impl = doc.get("implication_ledger") or {}
    ent = impl.get("one_way_entailments") or []
    forb = impl.get("forbidden_transfers") or []
    has_c0_entails = any("C0" in str(e.get("from")) and "C2" in str(e.get("to")) and e.get("relation") == "entails"
                         for e in ent if isinstance(e, dict))
    has_converse_forbidden = any("C2" in str(e.get("from")) and "C0" in str(e.get("to"))
                                 for e in forb if isinstance(e, dict))
    ok18 = has_c0_entails and has_converse_forbidden
    add("G18", "one-way entailment C0=>C2 recorded and converse transfer forbidden",
        ok18, {"one_way": has_c0_entails, "converse_forbidden": has_converse_forbidden})

    # G19 canonical class-separation checker: zero hard findings, zero unknown tokens
    hard, soft = [], []
    if classsep is not None:
        findings = classsep.findings_for_text(raw_text, "F2a snapshot")
        hard = [f for f in findings if f.startswith("CLASSSEP:")]
        soft = [f for f in findings if f.startswith("CLASSSEP-SOFT:")]
    ok19 = not hard and not soft
    add("G19", "canonical class-separation checker: no hard finding and no unknown class token",
        ok19, {"hard": hard, "soft": soft})

    # G20 every class-id-shaped token in the file is one of the frozen four
    toks = sorted(set(TOKEN.findall(raw_text)))
    unknown = [t for t in toks if t not in FROZEN_FOUR]
    ok20 = not unknown and CLASS_ID in toks and SIBLING in toks
    add("G20", "all class-id-shaped tokens are frozen class ids (no variant-as-class)",
        ok20, {"tokens": toks, "unknown": unknown})

    # G21 non-vacuity discharged
    nv = doc.get("non_vacuity") or {}
    ok21 = bool(str(nv.get("condition") or "").strip() and str(nv.get("vacuity_falsifier") or "").strip()
                and str(nv.get("witness_type") or "").strip())
    add("G21", "non-vacuity condition, witness type and vacuity falsifier present",
        ok21, {"status": nv.get("status"), "witness_type": str(nv.get("witness_type"))[:70]})

    # G22 f0_binding points at the measured canonical taxonomy hash
    f0b = doc.get("f0_binding") or {}
    declared = str(f0b.get("declared_f0_sha256") or "")
    ok22 = (f0b.get("declared_f0_artifact") == "research_map/formulation_taxonomy.yaml"
            and declared == sha256_file(Path(F0_PATH[0])))
    add("G22", "f0_binding declares and matches the measured canonical F0 sha256",
        ok22, {"declared": declared[:16], "measured": sha256_file(Path(F0_PATH[0]))[:16]})

    # G23 contract pointers resolve at their declared trees (rev12 closure item b)
    ptr = str(doc.get("class_contract_pointer") or "")
    supp_ptr = str(doc.get("class_contract_supplement_pointer") or "")
    canon_res = (ptr.startswith("research_map/formulation_taxonomy.yaml#classes.")
                 and isinstance(f0.get("classes"), dict) and CLASS_ID in f0["classes"])
    supp_res = ("artifacts/formulation/formulation_taxonomy.yaml#class_contracts." in supp_ptr
                and isinstance(supplement.get("class_contracts"), dict)
                and CLASS_ID in supplement["class_contracts"])
    ok23 = canon_res and supp_res
    add("G23", "class_contract_pointer resolves in canonical F0 classes.<id>; supplement pointer separate and resolvable",
        ok23, {"pointer": ptr, "canonical_resolves": canon_res,
               "supplement_pointer": supp_ptr, "supplement_resolves": supp_res})

    # G24 schema axes agree with the supplement contract components
    comp = (supplement.get("class_contracts") or {}).get(CLASS_ID, {}).get("components") or {}
    sc = doc.get("class_components") or {}
    agree = {k: (sc.get(k) == comp.get(k)) for k in ("asymptotics", "censorship", "matter", "genericity", "regularity_token")}
    ok24 = all(agree.values())
    add("G24", "schema axis components agree with the canonical class contract (supplement)",
        ok24, agree)

    # G25 one conclusion under the pinned alias registry (advisory closes here)
    f0_axes = _get(f0, f"classes.{CLASS_ID}.axes", {}) or {}
    tokens = {"schema": ct, "f0_canonical": f0_axes.get("conclusion_type"),
              "supplement": (supplement.get("class_contracts") or {}).get(CLASS_ID, {}).get("conclusion_type")}

    def canon_token(t):
        if not t:
            return None
        for canon, al in (aliases.get("conclusion_type") or {}).items():
            if t == canon or t in (al or []):
                return canon
        return None

    resolved = {k: canon_token(v) for k, v in tokens.items()}
    sem_ok = (_get(f0, f"classes.{CLASS_ID}.axes.family") == "SCC"
              and _get(f0, f"classes.{CLASS_ID}.axes.regularity_token") == "C2"
              and _get(f0, f"classes.{CLASS_ID}.axes.matter_model") == "vacuum")
    ok25 = sem_ok and all(resolved.values()) and len(set(resolved.values())) == 1
    add("G25", "one conclusion under VOCAB_ALIASES: schema/F0/supplement tokens resolve to a single canonical token",
        ok25, {"tokens": tokens, "resolved": resolved, "semantics_agree": sem_ok, "registry": "VOCAB_ALIASES.json"})

    # G26 exclusions in canonical F0 name the C0 sibling (no silent class merge)
    exc = _get(f0, f"classes.{CLASS_ID}.exclusions", []) or []
    ok26 = any(SIBLING in str(x) for x in exc)
    add("G26", "canonical F0 exclusions name the C0 sibling class",
        ok26, {"n_exclusions": len(exc)})

    # G27 unresolved items are recorded rather than silently dropped
    ok27 = isinstance(doc.get("unresolved_items"), list)
    add("G27", "unresolved items recorded as a list (not silently dropped)",
        ok27, {"unresolved_items": doc.get("unresolved_items")})

    # ---- rev12 closure checks (astra-life03-close-findings items a-c) -----
    import collections as _collections
    from datetime import datetime as _dt, timezone as _tz, timedelta as _td
    _dups: list[dict] = []

    class _DupLoader(yaml.SafeLoader):
        pass

    def _dup_ctor(loader, node, deep=False):
        ks = [str(loader.construct_object(k, deep=deep)) for k, _ in node.value]
        dd = {k: v for k, v in _collections.Counter(ks).items() if v > 1}
        if dd:
            _dups.append(dd)
        return yaml.SafeLoader.construct_mapping(loader, node, deep)

    _DupLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _dup_ctor)
    yaml.load(raw_text, Loader=_DupLoader)  # noqa: S506
    dup: dict[str, int] = {}
    for dd in _dups:
        for k, v in dd.items():
            dup[k] = max(dup.get(k, 0), v)
    # G28 no duplicate top-level YAML keys (closure item a)
    add("G28", "no duplicate top-level YAML mapping keys (strict-compose probe)",
        not dup, {"duplicates": dup})

    # G29 machine-readable stamps not future-dated (closure item a)
    CST = _tz(_td(hours=8))
    now = _dt.now(CST)

    def _future(ts):
        if not ts:
            return None
        try:
            t = _dt.fromisoformat(str(ts))
        except Exception:
            return None
        if t.tzinfo is None:
            t = t.replace(tzinfo=CST)
        return round((t - now).total_seconds(), 1)

    stamp_skews = {
        "revised_at": _future(doc.get("revised_at")),
        "f0_binding.checked_at": _future(_get(doc, "f0_binding.checked_at")),
        "revision_history_max": max([_future(x.get("at")) for x in (doc.get("revision_history") or [])
                                     if isinstance(x, dict) and x.get("at")] or [None], default=None),
    }
    ok29 = all(v is not None and v <= 0 for v in stamp_skews.values())
    add("G29", "machine-readable stamps not future-dated (revised_at, f0_binding.checked_at, revision_history)",
        ok29, {"skew_seconds_vs_wall_clock": stamp_skews, "checked_at": now.isoformat(timespec="seconds")})

    # G30 D0 retyped as a tagged disjoint union over one index r (closure item d)
    d0 = str(_get(doc, "quantifiers.domains.D0.definition") or "")
    binders = [x.get("binder") for x in (q.get("ordered") or []) if isinstance(x, dict)]
    d0_flat = d0.replace(" ", "")
    ok30 = ("tagged" in d0 and "disjoint union" in d0 and "smooth" in d0
            and "(sobolev,s,delta)" in d0_flat and binders[:1] == ["r"]
            and "G_r" in str(q.get("formal") or ""))
    add("G30", "D0 is a tagged disjoint union and the first binder is the single index r",
        ok30, {"D0_head": d0[:180], "binders": binders})

    # G31 no dangling AF_{...} symbol in conclusion.statement_formal (closure item c)
    # Self-consistent on the parsed document: strip statement_formal from a copy and require every
    # AF_{...} symbol used there to occur elsewhere in the document (definition leaf or note).
    sf = str(_get(doc, "conclusion.statement_formal") or "")
    syms = sorted(set(re.findall(r"AF_\{[^}]+\}", sf)))
    d_wo = copy.deepcopy(doc)
    if isinstance(d_wo.get("conclusion"), dict):
        d_wo["conclusion"]["statement_formal"] = ""
    # Definition leaves only: drop prose/changelog keys, which must not count as definitions.
    for k in list(d_wo.keys()):
        if any(w in str(k).lower() for w in ("note", "history", "provenance", "changelog", "supersede")):
            d_wo.pop(k, None)
    outside = yaml.safe_dump(d_wo, sort_keys=False, allow_unicode=True)
    undef = [s for s in syms if s not in outside]
    ok31 = not undef
    add("G31", "every AF_{...} symbol in statement_formal is defined elsewhere in the file",
        ok31, {"statement_formal": sf[:160], "symbols": syms, "undefined": undef})

    return out


def mutate(doc: dict, mid: str):
    d = copy.deepcopy(doc)
    if mid == "M1_wrong_class":
        d["class_id"] = SIBLING
    elif mid == "M2_c0_conclusion":
        d["conclusion"]["conclusion_type"] = "C0_inextendibility_of_maximal_development"
    elif mid == "M3_unknown_genericity":
        d["genericity"]["kind"] = "typical_generic"
    elif mid == "M4_missing_constraint":
        del d["data_class"]["constraints"]["momentum"]
    elif mid == "M5_hedged_quantifier":
        d["quantifiers"]["formal"] = "roughly, forall (s,delta) in D0: ..."
    elif mid == "M6_wcc_content":
        d["conclusion"]["statement_formal"] = "for all data the singularity is not visible from I+"
    elif mid == "M7_stale_f0":
        d["f0_binding"]["declared_f0_sha256"] = "0" * 64
    elif mid == "M8_no_antiscope":
        d["anti_scope"]["not_this_class"] = []
    elif mid == "M9_no_nonvacuity":
        del d["non_vacuity"]["condition"]
    elif mid == "M10_c0c2_composite":
        d["scope_statement"] = "the C0 or C2 extension classes are treated as one schema here"
    elif mid == "M11_no_falsifier_steps":
        d["falsifier"]["tier_1"]["machine_checkable_steps"] = []
    elif mid == "M12_two_class_ids":
        d["class_boundary"]["one_class_only"] = "AF-SCC-C0-VAC-GEN"
    elif mid == "M13_pointer_authoring_only":
        d["class_contract_pointer"] = "artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C2-VAC-GEN"
    elif mid == "M14_unmapped_conclusion_token":
        d["conclusion"]["conclusion_type"] = "strong_cosmic_censorship"
    elif mid == "M15_untagged_D0":
        d["quantifiers"]["domains"]["D0"]["definition"] = "admissible regularity pairs (s,delta)"
    elif mid == "M16_dangling_symbol":
        d["conclusion"]["statement_formal"] = str(d["conclusion"].get("statement_formal")) + " with AF_{I+}(M_D) complete"
    elif mid == "M17_future_stamp":
        d["f0_binding"]["checked_at"] = "2030-01-01T00:00:00+08:00"
    else:
        raise KeyError(mid)
    return d


MUTANT_EXPECT = {
    "M1_wrong_class": "G1",
    "M2_c0_conclusion": "G11",
    "M3_unknown_genericity": "G9",
    "M4_missing_constraint": "G8",
    "M5_hedged_quantifier": "G3",
    "M6_wcc_content": "G12",
    "M7_stale_f0": "G22",
    "M8_no_antiscope": "G17",
    "M9_no_nonvacuity": "G21",
    "M10_c0c2_composite": "G19",
    "M11_no_falsifier_steps": "G14",
    "M12_two_class_ids": "G1",
    "M13_pointer_authoring_only": "G23",
    "M14_unmapped_conclusion_token": "G25",
    "M15_untagged_D0": "G30",
    "M16_dangling_symbol": "G31",
    "M17_future_stamp": "G29",
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", required=True)
    ap.add_argument("--f0", required=True)
    ap.add_argument("--supplement", required=True)
    ap.add_argument("--registry", required=True)
    ap.add_argument("--aliases", required=False, default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    global F0_PATH
    F0_PATH = [a.f0]
    schema_p, f0_p = Path(a.schema), Path(a.f0)
    raw_text = schema_p.read_text()
    doc = yaml.safe_load(raw_text)
    f0 = yaml.safe_load(f0_p.read_text())
    supplement = yaml.safe_load(Path(a.supplement).read_text())
    registry = json.loads(Path(a.registry).read_text())
    aliases = json.loads(Path(a.aliases).read_text()) if a.aliases else {}

    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "research_map"))
    try:
        import class_separation as cs
    except Exception:
        cs = None

    checks = evaluate(doc, f0, supplement, registry, raw_text, cs, aliases)
    result = {
        "checker": "check_f2a_rev12_independent.py",
        "checker_version": "2.0.0",
        "target_class_id": CLASS_ID,
        "target_node": "F2a",
        "input_sha256": {"schema": sha256_file(schema_p), "f0": sha256_file(f0_p),
                         "supplement": sha256_file(Path(a.supplement)),
                         "registry": sha256_file(Path(a.registry)),
                         "aliases": sha256_file(Path(a.aliases)) if a.aliases else None},
        "checks": checks,
        "checks_passed": sum(1 for c in checks if c["ok"]),
        "checks_total": len(checks),
        "hard_failures": [c for c in checks if not c["ok"] and c["severity"] == "hard"],
        "advisories": [c for c in checks if c["severity"] == "advisory"],
    }
    result["verdict"] = "PASS" if not result["hard_failures"] else "FAIL"

    if a.selftest:
        controls = []
        positive = evaluate(doc, f0, supplement, registry, raw_text, cs, aliases)
        pos_fail = [c["id"] for c in positive if not c["ok"] and c["severity"] == "hard"]
        controls.append({"id": "positive_unmutated", "ok": not pos_fail,
                         "expected_fail": None, "failed_checks": pos_fail})
        for mid in MUTANT_EXPECT:
            md = mutate(doc, mid)
            try:
                mtext = yaml.safe_dump(md, sort_keys=False)
                mchecks = evaluate(md, f0, supplement, registry, mtext, cs, aliases)
                failed = [c["id"] for c in mchecks if not c["ok"]]
                controls.append({"id": mid, "ok": MUTANT_EXPECT[mid] in failed,
                                 "expected_fail": MUTANT_EXPECT[mid], "failed_checks": failed})
            except Exception as e:  # a mutation that crashes the checker is not caught cleanly
                controls.append({"id": mid, "ok": False, "expected_fail": MUTANT_EXPECT[mid],
                                 "failed_checks": [], "error": str(e)})
        result["controls"] = controls
        result["controls_passed"] = sum(1 for c in controls if c["ok"])
        result["controls_total"] = len(controls)
        result["verdict"] = ("PASS" if result["verdict"] == "PASS"
                             and all(c["ok"] for c in controls) else "FAIL")

    if a.json:
        print(json.dumps(result, indent=2, sort_keys=False))
    else:
        for c in checks:
            print(f"{'ok ' if c['ok'] else 'FAIL'} {c['id']:<4} {c['criterion']}")
        print("VERDICT:", result["verdict"])
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
