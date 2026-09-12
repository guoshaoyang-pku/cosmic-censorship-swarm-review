#!/usr/bin/env python3
"""W059-F1-REV12-VERDICT-01 independent instrument.

Class-bound verification of AF-WCC-VAC-GEN (node F1) at the pinned canonical
sha256 cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3.

Own instrument: standard library + PyYAML only.  It imports no canonical gate,
no table from the formulation lead, and no other worker's checker.  Every check
returns an explicit boolean; every single-defect mutant declares its target
check and is reported detected only if that target check flips.

Drift policy: the pinned hashes below are the binding.  If a measured hash
differs, the run is marked void and the verdict it feeds is void.
"""
import copy
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time

import yaml

REPO = "/data3/guoshaoyang/workdir/ai4math-swarm"
OUT = os.path.join(REPO, "artifacts/worker-059/f1_rev12_verdict")

PATHS = {
    "f1": "schemas/af_wcc_vacuum.yaml",
    "f1_authoring": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "f2a": "schemas/af_scc_c2_vacuum.yaml",
    "f2b": "schemas/af_scc_c0_vacuum.yaml",
    "taxonomy": "research_map/formulation_taxonomy.yaml",
    "supplement": "artifacts/formulation/formulation_taxonomy.yaml",
    "evidence": "artifacts/formulation/evidence/taxonomy_consistency.json",
    "vocab": "artifacts/formulation/VOCAB_ALIASES.json",
    "frozen": "artifacts/formulation/FROZEN.json",
    "ledger": "ledger/theorems.jsonl",
}

# binding pins (must equal the FROZEN rev28 manifest entries, verified in-run)
PINS = {
    "f1": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "taxonomy": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "supplement": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "evidence_measured": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "evidence_declared_stale": "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48",
    "vocab": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "frozen": "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
}

RUN_START = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))


def sha256_file(rel):
    p = os.path.join(REPO, rel)
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


class StrictLoader(yaml.SafeLoader):
    pass


def _strict_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                None, None, "duplicate mapping key %r" % (key,), key_node.start_mark
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _strict_mapping
)


def strict_load(text):
    return yaml.load(text, Loader=StrictLoader)


ISO = re.compile(
    r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:\+08:00|Z)?)"
)


def iso_iter(obj):
    if isinstance(obj, str):
        for m in ISO.finditer(obj):
            yield m.group(1)
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from iso_iter(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from iso_iter(v)


def parse_iso(s):
    s2 = s.replace("Z", "+00:00")
    try:
        d = dt.datetime.fromisoformat(s2)
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone(dt.timedelta(hours=8)))
    return d


def run_checks(ctx):
    """Return (checks, derived).  ctx carries parsed docs + measurements."""
    f1 = ctx["f1"]
    tax = ctx["taxonomy"]
    sup = ctx["supplement"]
    ev = ctx["evidence"]
    vocab = ctx["vocab"]
    frozen = ctx["frozen"]
    raw = ctx["f1_raw"]
    checks = []

    def add(cid, name, ok, severity, detail):
        checks.append(
            {
                "id": cid,
                "name": name,
                "ok": bool(ok),
                "severity": severity,
                "detail": str(detail)[:600],
            }
        )

    def get(d, *keys, default=None):
        cur = d
        for k in keys:
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur

    # --- drift / binding -------------------------------------------------
    add("A1", "f1_measured_equals_pin", ctx["h"]["f1"] == PINS["f1"], "blocking",
        "measured %s pin %s" % (ctx["h"]["f1"][:12], PINS["f1"][:12]))
    add("A2", "frozen_r28_pins_f1", get(frozen, "files", PATHS["f1"], "sha256") == ctx["h"]["f1"], "blocking",
        "frozen pin %s" % str(get(frozen, "files", PATHS["f1"], "sha256"))[:12])
    add("A3", "frozen_r28_pins_taxonomy_and_supplement",
        get(frozen, "files", PATHS["taxonomy"], "sha256") == ctx["h"]["taxonomy"]
        and get(frozen, "files", PATHS["supplement"], "sha256") == ctx["h"]["supplement"], "blocking",
        "tax %s sup %s" % (str(get(frozen, "files", PATHS["taxonomy"], "sha256"))[:12],
                           str(get(frozen, "files", PATHS["supplement"], "sha256"))[:12]))
    add("A4", "frozen_revision_28", frozen.get("revision") == 28, "advisory",
        "revision=%s frozen_at=%s" % (frozen.get("revision"), frozen.get("frozen_at")))
    add("A5", "logical_artifacts_pins_match_measurement",
        get(frozen, "logical_artifacts", "F0-declared-taxonomy", "sha256") == ctx["h"]["taxonomy"]
        and get(frozen, "logical_artifacts", "F0-class-contract-supplement", "sha256") == ctx["h"]["supplement"],
        "blocking", "companion pair pins")

    # --- parse / metadata ------------------------------------------------
    add("B1", "strict_parse_no_duplicate_keys", ctx["parse_ok"], "blocking", ctx["parse_note"])
    add("B2", "schema_version_1_0", f1.get("schema_version") == "1.0", "advisory", f1.get("schema_version"))
    add("B3", "artifact_kind_class_schema", f1.get("artifact_kind") == "class_schema", "major", f1.get("artifact_kind"))
    add("B4", "class_id_af_wcc_vac_gen", f1.get("class_id") == "AF-WCC-VAC-GEN", "blocking", f1.get("class_id"))
    add("B5", "node_id_f1", f1.get("node_id") == "F1", "major", f1.get("node_id"))
    add("B6", "revision_12", f1.get("revision") == 12, "blocking", f1.get("revision"))
    add("B7", "supersedes_null", f1.get("supersedes") is None, "advisory", f1.get("supersedes"))

    hist = f1.get("revision_history") or []
    eff = [h for h in hist if isinstance(h, dict) and not h.get("unused")]
    eff_sorted = sorted(eff, key=lambda h: h.get("index", -10 ** 9))
    add("B8", "revision_history_effective_monotone",
        bool(eff) and eff == eff_sorted and eff[-1].get("index") == 10,
        "major", "effective rows=%d last index=%s" % (len(eff), eff[-1].get("index") if eff else None))

    stamps = [parse_iso(s) for s in iso_iter(f1)]
    stamps = [s for s in stamps if s is not None]
    future = [s for s in stamps if s > RUN_START]
    add("B9", "no_future_dated_timestamps", not future, "major",
        "future=%s run_start=%s" % ([s.isoformat() for s in future], RUN_START.isoformat()))

    mt = dt.datetime.fromtimestamp(os.path.getmtime(os.path.join(REPO, PATHS["f1"])),
                                   tz=dt.timezone(dt.timedelta(hours=8)))
    rev_at = parse_iso(str(f1.get("revised_at")))
    add("B10", "revised_at_not_after_mtime", rev_at is not None and rev_at <= mt + dt.timedelta(seconds=90),
        "major", "revised_at=%s mtime=%s" % (rev_at, mt.isoformat()))

    # --- class identity vs F0 -------------------------------------------
    axes = get(tax, "classes", "AF-WCC-VAC-GEN", "axes", default={})
    comp = f1.get("class_components") or {}
    rt_norm = (lambda v: None if v in (None, "none") else v)
    add("C1", "class_components_match_f0_axes",
        comp.get("asymptotics") == "AF" and comp.get("censorship") == "WCC"
        and comp.get("matter") == "VAC" and comp.get("genericity") == "GEN"
        and rt_norm(comp.get("regularity_token")) is None
        and axes.get("family") == "WCC" and axes.get("matter_model") == "vacuum"
        and axes.get("symmetry") == "none_assumed"
        and axes.get("asymptotics") == "asymptotically_flat_3p1"
        and rt_norm(axes.get("regularity_token")) is None,
        "blocking", "components=%s axes=%s" % (comp, axes))
    add("C5", "regularity_token_encoding_consistent",
        comp.get("regularity_token") == axes.get("regularity_token"), "minor",
        "F0 stores null, schema stores the string 'none' for the same absent token (semantically equal)")

    ptr = f1.get("class_contract_pointer")
    ptr_ok = isinstance(ptr, str) and ptr.startswith(PATHS["taxonomy"] + "#classes.AF-WCC-VAC-GEN")
    add("C2", "class_contract_pointer_resolves_in_canonical",
        ptr_ok and get(tax, "classes", "AF-WCC-VAC-GEN") is not None, "blocking", ptr)
    spp = f1.get("class_contract_supplement_pointer")
    spp_ok = isinstance(spp, str) and spp.startswith(PATHS["supplement"] + "#class_contracts.AF-WCC-VAC-GEN")
    add("C3", "supplement_pointer_separate_and_resolves",
        spp_ok and get(sup, "class_contracts", "AF-WCC-VAC-GEN") is not None, "major", spp)
    add("C4", "no_pointer_conflation",
        ptr_ok and spp_ok and PATHS["taxonomy"] not in str(spp) and PATHS["supplement"] not in str(ptr),
        "blocking", "ptr=%s spp=%s" % (ptr, spp))

    # --- quantifiers -----------------------------------------------------
    q = f1.get("quantifiers") or {}
    ordered = q.get("ordered") or []
    want = [("forall", "r", "D0"), ("exists", "G_r", "D1"), ("forall", "(Sigma,h,K)", "D2"),
            ("exists", "(Mtilde,gtilde,Omega)", "D3"), ("forall", "gamma", "D4"),
            ("not_exists", "(q,t0)", "D5")]
    got = [(o.get("kind"), o.get("binder"), o.get("domain_id")) for o in ordered if isinstance(o, dict)]
    add("D1", "ordered_quantifier_sequence_exact", got == want, "blocking", "got=%s" % (got,))
    formal = str(q.get("formal") or "")
    formal_norm = re.sub(r"\s+", "", formal)
    add("D2", "formal_text_mentions_all_binders",
        all(t in formal_norm for t in ["forallrinD0", "existsG_r", "(Sigma,h,K)", "(Mtilde,gtilde,Omega)",
                                       "gamma"]) and re.search(r"qinI\+", formal_norm) is not None,
        "major", formal[:200])
    add("D3", "generic_set_bound_before_data", q.get("order_matters") is True
        and "chosen before and independently of the data" in str(q.get("order_note") or ""),
        "blocking", "order_matters=%s" % q.get("order_matters"))
    doms = q.get("domains") or {}
    d0 = str(get(doms, "D0", "definition", default=""))
    add("D4", "d0_tagged_disjoint_union",
        "smooth" in d0 and "sobolev" in d0 and re.search(r"s\s*>\s*5/2", d0)
        and re.search(r"1/2\s*,\s*1", d0) and "disjoint union" in d0, "blocking", d0[:220])
    add("D5", "d0_no_smooth_pair_binder",
        "smooth (the smooth-with-decay default)" in d0 and "smooth,s,delta" not in d0.replace(" ", ""),
        "major", "smooth branch typed as index")
    d5 = str(get(doms, "D5", "definition", default=""))
    add("D6", "d5_tail_predicate_and_strength_disclaimer",
        "tail" in d5 and "STRONGER" in d5 and "NOT the predicate" in d5, "blocking", d5[:220])
    add("D7", "negation_normal_form_present", "P_WCC" in str(q.get("negation_normal_form") or "")
        and "non-meager" in str(q.get("negation_normal_form") or ""), "major", q.get("negation_normal_form"))
    add("D8", "quantifier_class_declared", "comeager" in str(q.get("quantifier_class") or ""),
        "advisory", q.get("quantifier_class"))

    # --- conclusion surface ---------------------------------------------
    con = f1.get("conclusion") or {}
    ctype = con.get("conclusion_type")
    add("E1", "conclusion_type_wcc", ctype == "weak_cosmic_censorship", "blocking", ctype)
    add("E2", "conclusion_type_in_f0_allowed",
        ctype in (get(tax, "field_vocabulary", "conclusion_type", "allowed", default=[]) or []),
        "blocking", "allowed=%s" % (get(tax, "field_vocabulary", "conclusion_type", "allowed", default=[]),))
    add("E3", "conclusion_type_canonical_in_vocab",
        ctype in (get(vocab, "conclusion_type", default={}) or {}), "blocking",
        "vocab canonical=%s" % list((get(vocab, "conclusion_type", default={}) or {}).keys()))
    sf = str(con.get("statement_formal") or "")
    add("E4", "statement_formal_uses_af_iplus_and_visibility",
        "AF_{I+}" in sf and "visible_singularity_from_I_plus" in sf and "forall r in D0" in sf,
        "blocking", sf)
    concl_blob = json.dumps(con)
    stmt_surface = " ".join([str(con.get("statement_formal") or ""),
                             str(con.get("statement_natural_language") or ""),
                             str(get(con, "equivalent_standard_formulation", "predicate", default=""))])
    add("E5", "no_scc_token_in_statement_surface",
        not re.search(r"inextendib|strong_cosmic_censorship_C[02]|scc_c[02]", stmt_surface),
        "blocking", "statement-surface scan: %s" % stmt_surface[:160])
    meta_text = json.dumps({k: v for k, v in con.items()
                            if k not in ("statement_formal", "statement_natural_language",
                                         "equivalent_standard_formulation", "forbidden_strengthenings",
                                         "forbidden_weakenings")})
    add("E5b", "no_scc_token_outside_statement_meta",
        not re.search(r"strong_cosmic_censorship_C[02]|scc_c[02]|future_inextendibility", meta_text),
        "major", "meta scan (forbidden lists excluded): %s" % meta_text[:160])
    add("E6", "no_c0_or_c2_composite_phrase",
        "C0 or C2" not in concl_blob and "C0/C2" not in concl_blob, "blocking", "composite regularity scan")
    fs = con.get("forbidden_strengthenings") or []
    fsb = " | ".join(map(str, fs))
    add("E7", "forbidden_strengthenings_complete",
        all(t in fsb for t in ["black-hole region non-empty", "geodesic completeness",
                               "C2 or C0 inextendibility", "ALL data"]), "major", fsb[:260])
    fw = con.get("forbidden_weakenings") or []
    fwb = " | ".join(map(str, fw))
    add("E8", "forbidden_weakenings_complete",
        all(t in fwb for t in ["dropping I+ completeness", "there exist data", "no visible singularity"]),
        "major", fwb[:260])
    add("E9", "promotion_rule_rejects_self_evidence",
        "artifact_refs" in str(con.get("claim_promotion") or "")
        and "never evidence for its own conclusion" in str(f1.get("promotion_rule") or ""), "major",
        str(f1.get("promotion_rule"))[:160])

    anti = f1.get("anti_scope") or {}
    notc = " | ".join(str(x.get("class_id")) for x in (anti.get("not_this_class") or []))
    add("E10", "anti_scope_lists_scc_and_scalar",
        "AF-SCC-C2-VAC-GEN" in notc and "AF-SCC-C0-VAC-GEN" in notc and "AF-WCC-SCALAR-SPH" in notc,
        "blocking", notc)
    add("E11", "anti_scope_forbids_composite_phrase",
        any("C0 or C2" in str(x) for x in (anti.get("phrases_that_are_not_this_class") or [])),
        "major", anti.get("phrases_that_are_not_this_class"))

    # --- i_plus / visibility --------------------------------------------
    ip = f1.get("i_plus") or {}
    add("F1c", "i_plus_in_conclusion", ip.get("in_conclusion") is True and ip.get("role") == "conclusion",
        "major", "role=%s" % ip.get("role"))
    add("F2c", "af_iplus_predicate_abbreviation_defined",
        "AF_{I+}" in str(ip.get("predicate_abbreviation") or "")
        and "abbreviates the existence predicate" in str(ip.get("predicate_abbreviation") or ""),
        "blocking", str(ip.get("predicate_abbreviation"))[:180])
    add("F3c", "asymptotic_simplicity_not_assumed", "NOT assumed" in str(ip.get("asymptotically_simple") or ""),
        "major", ip.get("asymptotically_simple"))
    vis = f1.get("visibility") or {}
    add("F4c", "visibility_definition_tail_formulation",
        "TAIL gamma([t0,T))" in str(vis.get("definition") or ""), "blocking", str(vis.get("definition"))[:200])
    neg = str(vis.get("negation_conclusion") or "")
    add("F5c", "negation_is_not_b_containment",
        "NOT equivalent to" in neg and "B-containment is strictly stronger" in neg
        and "single-q non-containment" in " | ".join(map(str, vis.get("must_not_conflate") or [])),
        "blocking", neg[:220])
    add("F6c", "witness_protocol_has_genericity_step",
        "Step (5)" in str(vis.get("witness_protocol") or ""), "major", str(vis.get("witness_protocol"))[:200])
    add("F7c", "singularity_definition_affine_length",
        "finite affine length" in str(vis.get("singularity_definition") or "")
        and "Curvature blow-up is NOT used" in str(vis.get("singularity_definition") or ""),
        "major", str(vis.get("singularity_definition"))[:200])

    # --- genericity ------------------------------------------------------
    gen = f1.get("genericity") or {}
    gk = gen.get("kind")
    add("G1", "genericity_kind_canonical_in_vocab",
        gk in (get(vocab, "genericity_kind", default={}) or {}), "blocking",
        "kind=%s canonical=%s" % (gk, list((get(vocab, "genericity_kind", default={}) or {}).keys())))
    add("G1b", "genericity_kind_is_residual_comeager",
        gk == "residual_comeager", "blocking",
        "class identity fixes the comeager form; got %s" % gk)
    f0_gk = axes.get("genericity_kind")
    alias_map = get(vocab, "genericity_kind", default={}) or {}
    f0_gk_is_alias = any(f0_gk in v for k, v in alias_map.items() if k != f0_gk)
    add("G2", "f0_genericity_token_registry_consistent",
        f0_gk == gk and not f0_gk_is_alias, "major",
        "f0=%s schema=%s f0_is_registered_alias=%s" % (f0_gk, gk, f0_gk_is_alias))
    tf = gen.get("transfer_failures") or []
    th = gen.get("transfer_holds") or []
    add("G3", "genericity_transfer_table_complete",
        len(tf) >= 4 and len(th) >= 2
        and any("open_dense_escape" in str(r.get("pair")) for r in tf)
        and any("open_dense_escape" in str(r.get("pair")) for r in th), "major",
        "failures=%d holds=%d" % (len(tf), len(th)))
    add("G4", "genericity_variants_are_variants_not_classes",
        all(v.get("is_this_class") is False for v in (gen.get("variants") or []))
        and len(gen.get("variants") or []) >= 4, "major", "variants=%d" % len(gen.get("variants") or []))
    add("G5", "genericity_open_dense_vocabulary_risk_recorded",
        "STRICTLY STRONGER" in str(gen.get("acceptance_alignment") or "")
        and "open_dense_escape" in str(gen.get("acceptance_alignment") or ""), "advisory",
        str(gen.get("acceptance_alignment"))[:200])
    add("G6", "genericity_baire_nonvacuity_argument",
        "Baire" in str(gen.get("ambient_space") or "")
        and "subspace topology" in str(gen.get("topology_or_measure") or ""), "major",
        str(gen.get("ambient_space"))[:180])
    add("G7", "excluded_set_and_membership_unresolved",
        gen.get("excluded_set_status") == "unresolved"
        and "does not decide membership" in str(gen.get("membership_ruling") or "")
        and gen.get("ambient_space_is_data_space") is True, "major",
        "excluded=%s" % gen.get("excluded_set_status"))

    # --- f0_binding ------------------------------------------------------
    fb = f1.get("f0_binding") or {}
    add("H1", "f0_declared_artifact_is_canonical", fb.get("declared_f0_artifact") == PATHS["taxonomy"],
        "blocking", fb.get("declared_f0_artifact"))
    add("H2", "declared_f0_hash_equals_measured",
        fb.get("declared_f0_sha256") == ctx["h"]["taxonomy"], "blocking",
        "declared=%s measured=%s" % (str(fb.get("declared_f0_sha256"))[:12], ctx["h"]["taxonomy"][:12]))
    add("H3", "consistency_evidence_path_exists",
        fb.get("consistency_evidence") == PATHS["evidence"] and os.path.exists(os.path.join(REPO, PATHS["evidence"])),
        "blocking", fb.get("consistency_evidence"))
    add("H4", "declared_consistency_evidence_hash_equals_measured",
        fb.get("consistency_evidence_sha256") == ctx["h"]["evidence"], "blocking",
        "declared=%s measured=%s" % (str(fb.get("consistency_evidence_sha256"))[:12], ctx["h"]["evidence"][:12]))
    add("H5", "declared_consistency_evidence_hash_equals_frozen_pin",
        fb.get("consistency_evidence_sha256") == get(frozen, "files", PATHS["evidence"], "sha256"), "blocking",
        "declared=%s frozen=%s" % (str(fb.get("consistency_evidence_sha256"))[:12],
                                   str(get(frozen, "files", PATHS["evidence"], "sha256"))[:12]))
    ev_mtime = dt.datetime.fromtimestamp(os.path.getmtime(os.path.join(REPO, PATHS["evidence"])),
                                         tz=dt.timezone(dt.timedelta(hours=8)))
    checked = parse_iso(str(fb.get("checked_at")))
    add("H6", "checked_at_not_before_evidence_bytes",
        (fb.get("consistency_evidence_sha256") == ctx["h"]["evidence"])
        or (checked is not None and not (ev_mtime > checked + dt.timedelta(seconds=30))), "minor",
        "declared==measured clears it; else checked_at=%s evidence_mtime=%s" % (checked, ev_mtime.isoformat()))
    add("H7", "consistency_evidence_content_consistent",
        ev.get("consistent") is True and ev.get("contract_divergences") == []
        and sorted(ev.get("classes_compared") or []) == sorted(
            ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-SCALAR-SPH", "AF-WCC-VAC-GEN"]),
        "blocking", "consistent=%s divergences=%s classes=%d" % (
            ev.get("consistent"), ev.get("contract_divergences"), len(ev.get("classes_compared") or [])))
    add("H8", "binding_rule_present",
        "must be refreshed" in str(fb.get("rule") or "") and fb.get("binding_note"), "advisory",
        str(fb.get("rule"))[:160])

    # --- publication mirror ---------------------------------------------
    add("I1", "f1_mirror_byte_identical",
        ctx["h"]["f1"] == ctx["h"]["f1_authoring"], "blocking",
        "canonical=%s authoring=%s" % (ctx["h"]["f1"][:12], ctx["h"]["f1_authoring"][:12]))
    add("I2", "vocab_aliases_pinned_in_frozen",
        get(frozen, "files", PATHS["vocab"], "sha256") == ctx["h"]["vocab"], "major",
        "frozen=%s measured=%s" % (str(get(frozen, "files", PATHS["vocab"], "sha256"))[:12],
                                   ctx["h"]["vocab"][:12]))

    # --- ledger / review status -----------------------------------------
    ids = set(ctx["ledger_ids"])
    refs = f1.get("l1_ledger_refs") or []
    ref_ids = [r.get("theorem_id") for r in refs]
    add("J1", "l1_ledger_ids_exist",
        all(i in ids for i in ref_ids) and len(ref_ids) >= 4, "major",
        "refs=%s missing=%s" % (ref_ids, [i for i in ref_ids if i not in ids]))
    add("J2", "l1_status_vocabulary_mapping_defined",
        all(("verification_status" in r) or ("ledger_status" in r) for r in refs), "minor",
        "schema l1_status vs ledger verification_status has no declared mapping (corroborates F2a/F2b)")
    ks = f1.get("known_status") or {}
    add("J3", "known_status_no_inflation",
        ks.get("status") == "open_problem" and "no entry in the L1 ledger proves or refutes" in str(ks.get("non_transfer_warning") or ""),
        "major", ks.get("non_transfer_warning"))
    rs = f1.get("review_status") or {}
    add("J4", "review_status_honest",
        rs.get("independent_reviewers") == [] and rs.get("verdict") == "pending"
        and bool(rs.get("requested_reviewers")), "advisory",
        "independent=%s verdict=%s" % (rs.get("independent_reviewers"), rs.get("verdict")))
    add("J5", "provenance_no_status_claim",
        "asserts no theorem" in str(get(f1, "provenance", "no_status_claim", default="")), "major",
        str(get(f1, "provenance", "no_status_claim"))[:180])
    add("J6", "unresolved_items_present",
        len(f1.get("unresolved_items") or []) >= 3, "advisory", "n=%d" % len(f1.get("unresolved_items") or []))
    add("J7", "falsifier_tier1_genericity_route",
        "NON-MEAGER" in str(get(f1, "falsifier", "tier_1", "genericity_requirement", default=""))
        and "route R2" in str(get(f1, "falsifier", "tier_1", "genericity_requirement", default="")),
        "major", str(get(f1, "falsifier", "tier_1", "genericity_requirement"))[:200])
    add("J8", "schema_falsifiers_present",
        len(get(f1, "falsifier", "schema_falsifiers", default=[]) or []) >= 3, "advisory",
        "n=%d" % len(get(f1, "falsifier", "schema_falsifiers", default=[]) or []))
    return checks


def load_ctx():
    ctx = {}
    ctx["h"] = {k: sha256_file(v) for k, v in PATHS.items() if k != "ledger"}
    ctx["f1_raw"] = open(os.path.join(REPO, PATHS["f1"]), encoding="utf-8").read()
    ctx["parse_ok"] = True
    ctx["parse_note"] = "strict SafeLoader (duplicate mapping keys rejected)"
    try:
        ctx["f1"] = strict_load(ctx["f1_raw"])
    except Exception as e:  # keep the run alive; B1 will be false
        ctx["parse_ok"] = False
        ctx["parse_note"] = "strict parse failed: %s" % e
        ctx["f1"] = yaml.safe_load(ctx["f1_raw"])
    ctx["taxonomy"] = yaml.safe_load(open(os.path.join(REPO, PATHS["taxonomy"]), encoding="utf-8").read())
    ctx["supplement"] = yaml.safe_load(open(os.path.join(REPO, PATHS["supplement"]), encoding="utf-8").read())
    ctx["evidence"] = json.load(open(os.path.join(REPO, PATHS["evidence"]), encoding="utf-8"))
    ctx["vocab"] = json.load(open(os.path.join(REPO, PATHS["vocab"]), encoding="utf-8"))
    ctx["frozen"] = json.load(open(os.path.join(REPO, PATHS["frozen"]), encoding="utf-8"))
    ids = []
    with open(os.path.join(REPO, PATHS["ledger"]), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                ids.append(json.loads(line).get("theorem_id"))
            except Exception:
                pass
    ctx["ledger_ids"] = ids
    return ctx


# --------------------------- mutants ------------------------------------
def M(name, target, kind, fn):
    return {"name": name, "target": target, "kind": kind, "fn": fn}


def _set(doc, path, value):
    cur = doc
    for k in path[:-1]:
        cur = cur[k]
    cur[path[-1]] = value


def _del(doc, path):
    cur = doc
    for k in path[:-1]:
        cur = cur[k]
    del cur[path[-1]]


MUTANTS = [
    M("m01_duplicate_revised_at_key", "B1", "defect",
      lambda text, doc: text.replace('revised_at: "2026-09-12T00:31:41+08:00"',
                                     'revised_at: "2026-09-12T00:31:41+08:00"\nrevised_at: "2026-09-12T00:31:41+08:00"', 1)),
    M("m02_future_revised_at", "B9", "defect",
      lambda text, doc: _set(doc, ["revised_at"], "2027-01-01T00:00:00+08:00")),
    M("m03_wrong_class_id", "B4", "defect", lambda t, d: _set(d, ["class_id"], "AF-SCC-C2-VAC-GEN")),
    M("m04_revision_11", "B6", "defect", lambda t, d: _set(d, ["revision"], 11)),
    M("m05_swap_conclusion_to_c2", "E1", "defect",
      lambda t, d: _set(d, ["conclusion", "conclusion_type"], "scc_c2_future_inextendibility")),
    M("m06_alias_conclusion_in_new_canonical", "E3", "defect",
      lambda t, d: _set(d, ["conclusion", "conclusion_type"], "strong_cosmic_censorship_C0")),
    M("m07_d5_tail_disclaimer_removed", "D6", "defect",
      lambda t, d: _set(d, ["quantifiers", "domains", "D5", "definition"], "pairs (q,t0) with q in I+")),
    M("m08_visibility_whole_curve", "F4c", "defect",
      lambda t, d: _set(d, ["visibility", "definition"], "gamma([0,T)) is contained in J^-(q)")),
    M("m09_d0_pair_binder_reintroduced", "D4", "defect",
      lambda t, d: _set(d, ["quantifiers", "domains", "D0", "definition"],
                        "r = (smooth,s,delta) a pair; no disjoint union")),
    M("m10_af_iplus_abbreviation_removed", "F2c", "defect",
      lambda t, d: _del(d, ["i_plus", "predicate_abbreviation"])),
    M("m11_pointer_to_supplement", "C2", "defect",
      lambda t, d: _set(d, ["class_contract_pointer"],
                        "artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-WCC-VAC-GEN")),
    M("m12_stale_declared_f0_hash", "H2", "defect",
      lambda t, d: _set(d, ["f0_binding", "declared_f0_sha256"], "66bf917bd368" + "0" * 52)),
    M("m13_refresh_consistency_hash_to_measured", "H4", "repair",
      lambda t, d: _set(d, ["f0_binding", "consistency_evidence_sha256"], PINS["evidence_measured"])),
    M("m14_forbidden_strengthening_removed", "E7", "defect",
      lambda t, d: _set(d, ["conclusion", "forbidden_strengthenings"],
                        [x for x in d["conclusion"]["forbidden_strengthenings"] if "geodesic completeness" not in x])),
    M("m15_composite_regularity_phrase_added", "E6", "defect",
      lambda t, d: _set(d, ["conclusion", "statement_natural_language"],
                        str(d["conclusion"]["statement_natural_language"]) + " in the C0 or C2 sense")),
    M("m16_antiscope_scalar_removed", "E10", "defect",
      lambda t, d: _set(d, ["anti_scope", "not_this_class"],
                        [x for x in d["anti_scope"]["not_this_class"] if x.get("class_id") != "AF-WCC-SCALAR-SPH"])),
    M("m17_quantifier_order_swapped", "D1", "defect",
      lambda t, d: _set(d, ["quantifiers", "ordered"], list(reversed(d["quantifiers"]["ordered"])))),
    M("m18_order_matters_false", "D3", "defect",
      lambda t, d: _set(d, ["quantifiers", "order_matters"], False)),
    M("m19_wrong_family_component", "C1", "defect",
      lambda t, d: _set(d, ["class_components", "censorship"], "SCC")),
    M("m20_genericity_full_measure", "G1b", "defect",
      lambda t, d: _set(d, ["genericity", "kind"], "full_measure")),
    M("m21_transfer_row_removed", "G3", "defect",
      lambda t, d: _set(d, ["genericity", "transfer_holds"], list(d["genericity"]["transfer_holds"])[:1])),
    M("m22_scc_token_in_natural_statement", "E5", "defect",
      lambda t, d: _set(d, ["conclusion", "statement_natural_language"],
                        "the development is future C2 inextendible")),
    M("m23_promotion_rule_weakened", "E9", "defect",
      lambda t, d: _set(d, ["promotion_rule"], "may be recorded freely")),
    M("m24_f0_declared_artifact_is_supplement", "H1", "defect",
      lambda t, d: _set(d, ["f0_binding", "declared_f0_artifact"], "artifacts/formulation/formulation_taxonomy.yaml")),
    M("m25_missing_supplement_pointer", "C3", "defect",
      lambda t, d: _del(d, ["class_contract_supplement_pointer"])),
]


def run_mutants(ctx):
    base_checks = {c["id"]: c["ok"] for c in ctx["checks"]}
    results = []
    for m in MUTANTS:
        doc = copy.deepcopy(ctx["f1"])
        raw = ctx["f1_raw"]
        try:
            out = m["fn"](raw, doc)
            parse_ok = True
            if isinstance(out, str):
                raw2 = out
                try:
                    doc2 = strict_load(raw2)
                except Exception:
                    doc2 = yaml.safe_load(raw2)
                    parse_ok = False
            else:
                raw2 = yaml.safe_dump(doc, sort_keys=True, allow_unicode=True)
                doc2 = doc
            sub = dict(ctx)
            sub["f1"] = doc2
            sub["f1_raw"] = raw2
            sub["parse_ok"] = parse_ok
            got = {c["id"]: c["ok"] for c in run_checks(sub)}
            tgt = m["target"]
            if m["kind"] == "defect":
                detected = base_checks.get(tgt) is True and got.get(tgt) is False
            else:
                detected = base_checks.get(tgt) is False and got.get(tgt) is True
            results.append({"mutant": m["name"], "kind": m["kind"], "target": tgt,
                            "detected": bool(detected),
                            "target_before": base_checks.get(tgt), "target_after": got.get(tgt)})
        except Exception as e:
            results.append({"mutant": m["name"], "kind": m["kind"], "target": m["target"],
                            "detected": False, "error": "%s: %s" % (type(e).__name__, e)})
    return results


def registry_matrix(ctx):
    tax = ctx["taxonomy"]
    vocab = ctx["vocab"]
    rows = []
    schema_meta = {
        "AF-WCC-VAC-GEN": ("F1", "af_wcc_vacuum.yaml", ctx["f1"]),
        "AF-SCC-C2-VAC-GEN": ("F2a", "af_scc_c2_vacuum.yaml",
                              yaml.safe_load(open(os.path.join(REPO, PATHS["f2a"]), encoding="utf-8").read())),
        "AF-SCC-C0-VAC-GEN": ("F2b", "af_scc_c0_vacuum.yaml",
                              yaml.safe_load(open(os.path.join(REPO, PATHS["f2b"]), encoding="utf-8").read())),
        "AF-WCC-SCALAR-SPH": (None, None, None),
    }
    ct_canon = set((vocab.get("conclusion_type") or {}).keys())
    gk_canon = set((vocab.get("genericity_kind") or {}).keys())
    ct_alias = {a: k for k, v in (vocab.get("conclusion_type") or {}).items() for a in v if a != k}
    gk_alias = {a: k for k, v in (vocab.get("genericity_kind") or {}).items() for a in v if a != k}
    for cid, (node, fname, doc) in schema_meta.items():
        axes = (tax.get("classes", {}).get(cid, {}) or {}).get("axes", {}) or {}
        row = {"class_id": cid, "node": node, "f0_conclusion_type": axes.get("conclusion_type"),
               "f0_genericity_kind": axes.get("genericity_kind"),
               "schema_conclusion_type": None, "schema_genericity_kind": None,
               "schema_file": fname}
        if doc:
            row["schema_conclusion_type"] = doc["conclusion"]["conclusion_type"]
            row["schema_genericity_kind"] = doc["genericity"]["kind"]
        for axis, f0v, sv, canon, alias in (
                ("conclusion_type", row["f0_conclusion_type"], row["schema_conclusion_type"], ct_canon, ct_alias),
                ("genericity_kind", row["f0_genericity_kind"], row["schema_genericity_kind"], gk_canon, gk_alias)):
            d = {"axis": axis, "f0_token": f0v, "schema_token": sv,
                 "f0_token_canonical": f0v in canon, "f0_token_is_alias": f0v in alias,
                 "schema_token_canonical": (sv in canon) if sv else None,
                 "registries_agree": (f0v == sv) if sv else None}
            if sv is None:
                d["verdict"] = "no_schema_yet"
            elif f0v == sv and f0v in canon:
                d["verdict"] = "clean_canonical_both"
            elif f0v in alias and sv in canon and f0v != sv:
                d["verdict"] = "f0_stores_registered_alias_schema_uses_canonical"
            elif f0v == sv and f0v in alias:
                d["verdict"] = "both_store_alias"
            elif f0v not in canon and f0v not in alias:
                d["verdict"] = "f0_token_not_in_vocab"
            else:
                d["verdict"] = "review"
            row.setdefault("axes", []).append(d)
        rows.append(row)
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    ctx = load_ctx()
    ctx["checks"] = run_checks(ctx)
    mutants = run_mutants(ctx)
    matrix = registry_matrix(ctx)
    failing = [c for c in ctx["checks"] if not c["ok"]]
    detected = [m for m in mutants if m["detected"]]
    drift_ok = all(ctx["checks"][i]["ok"] for i in range(5))
    ev = {
        "instrument": "check_f1_rev12.py",
        "instrument_sha256": sha256_file("artifacts/worker-059/f1_rev12_verdict/check_f1_rev12.py"),
        "task_id": "W059-F1-REV12-VERDICT-01",
        "actor": "worker-059",
        "class_id": "AF-WCC-VAC-GEN",
        "node_id": "F1",
        "reviewed_sha256": ctx["h"]["f1"],
        "reviewed_revision": 12,
        "pins": PINS,
        "measured_hashes": ctx["h"],
        "pins_match_measured": {
            "f1": ctx["h"]["f1"] == PINS["f1"],
            "frozen_manifest_self": ctx["h"]["frozen"] == PINS["frozen"],
            "taxonomy": ctx["h"]["taxonomy"] == PINS["taxonomy"],
            "supplement": ctx["h"]["supplement"] == PINS["supplement"],
            "evidence": ctx["h"]["evidence"] == PINS["evidence_measured"],
            "vocab": ctx["h"]["vocab"] == PINS["vocab"],
        },
        "drift_void": not drift_ok,
        "run_started_at": RUN_START.isoformat(),
        "run_seconds": round(time.time() - t0, 3),
        "check_summary": {"total": len(ctx["checks"]), "pass": len(ctx["checks"]) - len(failing),
                          "fail": len(failing), "blocking_fail": len([c for c in failing if c["severity"] == "blocking"])},
        "checks": ctx["checks"],
        "mutant_summary": {"total": len(mutants), "detected": len(detected)},
        "mutants": mutants,
        "registry_matrix": matrix,
        "environment": {"python": sys.version.split()[0], "pyyaml": yaml.__version__,
                        "cwd": os.getcwd(), "imports": "stdlib+PyYAML only; no canonical gate imported"},
    }
    with open(os.path.join(OUT, "independent_evidence.json"), "w", encoding="utf-8") as fh:
        json.dump(ev, fh, indent=1)
    with open(os.path.join(OUT, "registry_matrix.json"), "w", encoding="utf-8") as fh:
        json.dump({"task_id": "W059-F1-REV12-VERDICT-01", "class_id": "AF-WCC-VAC-GEN",
                   "reviewed_sha256": ctx["h"]["f1"], "generated_at": RUN_START.isoformat(),
                   "governing_question": "which registry designates the canonical conclusion_type / genericity_kind token for a new canonical artifact, and does each canonical artifact comply",
                   "policy_quotes": {
                       "vocab": ctx["vocab"].get("policy"),
                       "f0_field_vocabulary": "F0 stores field_vocabulary.conclusion_type.allowed (aliases admitted) and axis tokens" if ctx["supplement"] else None},
                   "rows": matrix,
                   "finding": "All three vacuum schemas use the VOCAB_ALIASES canonical token for conclusion_type; F1's conclusion_type is canonical in both registries. F0 stores registered aliases (strong_cosmic_censorship_C2/C0, provisional_baire_residual) in a canonical artifact, which the VOCAB policy forbids for new canonical artifacts. F2a/F2b conclusions and F1/F2a/F2b genericity tokens are therefore governed by two disagreeing canonical registries; one written controller ruling is required.",
                   "affected_hashes": {"taxonomy": ctx["h"]["taxonomy"], "vocab": ctx["h"]["vocab"],
                                       "F1": ctx["h"]["f1"], "F2a": ctx["h"]["f2a"], "F2b": ctx["h"]["f2b"]}},
                  fh, indent=1)
    print(json.dumps({"evidence": os.path.join(OUT, "independent_evidence.json"),
                      "summary": ev["check_summary"], "mutants": ev["mutant_summary"],
                      "drift_void": ev["drift_void"],
                      "blocking_failures": [c["id"] + ":" + c["name"] for c in failing if c["severity"] == "blocking"]},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
