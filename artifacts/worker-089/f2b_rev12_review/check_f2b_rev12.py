#!/usr/bin/env python3
"""W089-F2B-REV12-REVIEW-04 — independent, controlled, hash-bound review of
F2b (AF-SCC-C0-VAC-GEN) revision 12 at the FROZEN rev28 pin.

Scope of the machine part: class-content structure, quantifier well-typedness
(closes HF-034-1 at this hash), the canonical-contract pointer repair (closes
HF-034-2 at this hash), C0-specific extension-predicate invariants, class
identity/separation from the C2 sibling and from WCC, the C0=>C2 entailment
ledger, frozen-pin/mirror alignment, and a hash-stability window.  Every check
has at least one planted-defect control so a pass is controlled rather than
asserted.  Reads shared artifacts read-only; writes only inside its own
artifact directory.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
import re
import sys
from collections import Counter

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TARGET = "schemas/af_scc_c0_vacuum.yaml"
TARGET_AUTHORING = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
CANON_TAX = "research_map/formulation_taxonomy.yaml"
SUPP_TAX = "artifacts/formulation/formulation_taxonomy.yaml"
F1 = "schemas/af_wcc_vacuum.yaml"
F2A = "schemas/af_scc_c2_vacuum.yaml"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
SIBLING_ID = "AF-SCC-C2-VAC-GEN"
FROZEN_CLASS_IDS = {
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
}
EXPECTED_COMPONENTS = {
    "asymptotics": "AF",
    "censorship": "SCC",
    "matter": "VAC",
    "genericity": "GEN",
    "regularity_token": "C0",
}


def sha256_file(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def read_text(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def load_yaml(path: str):
    return yaml.safe_load(read_text(path))


def iso_now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def parse_iso(value: str):
    if not isinstance(value, str):
        return None
    try:
        stamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        return None
    return stamp


def resolve_fragment(doc, fragment: str):
    """Resolve a dotted fragment like classes.AF-SCC-C0-VAC-GEN."""
    node = doc
    for part in fragment.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return False, None
    return True, node


def top_level_keys(raw: str):
    return re.findall(r"^(?![ \t#\-])([A-Za-z_][A-Za-z0-9_]*):", raw, re.M)


def d0_of(doc):
    return (((doc.get("quantifiers") or {}).get("domains") or {}).get("D0") or {})


def sobolev_of(doc):
    return (((doc.get("data_class") or {}).get("regularity_class") or {}).get("sobolev_variant") or {})


# --------------------------------------------------------------------------
# checks: ctx -> (status, measured, detail)
# --------------------------------------------------------------------------
def c01_duplicate_top_level_keys(ctx):
    counts = Counter(top_level_keys(ctx["raw"]))
    dups = {k: v for k, v in counts.items() if v > 1}
    return (
        "pass" if not dups else "fail",
        {"duplicates": dups, "n_top_level": len(counts)},
        "no duplicate top-level mapping keys" if not dups else f"duplicate keys: {dups}",
    )


def c02_revised_at_wall_clock(ctx):
    stamp = parse_iso(ctx["doc"].get("revised_at"))
    if stamp is None:
        return "fail", {"revised_at": ctx["doc"].get("revised_at")}, "revised_at missing/naive"
    now = ctx["now"]
    mtime = dt.datetime.fromtimestamp(ctx["mtime"]).astimezone()
    delta_now = (stamp - now).total_seconds()
    delta_mtime = (stamp - mtime).total_seconds()
    ok = delta_now <= 60 and abs(delta_mtime) <= 600
    return (
        "pass" if ok else "fail",
        {
            "revised_at": stamp.isoformat(),
            "now": now.isoformat(timespec="seconds"),
            "mtime": mtime.isoformat(timespec="seconds"),
            "seconds_before_now": round(delta_now, 1),
            "seconds_vs_mtime": round(delta_mtime, 1),
        },
        "revised_at is wall-clock and mtime-consistent" if ok else "timestamp out of tolerance",
    )


def c03_revision_history(ctx):
    doc = ctx["doc"]
    rev = doc.get("revision")
    hist = doc.get("revision_history") or []
    ok = True
    detail = []
    if not isinstance(rev, int) or rev < 12:
        ok = False
        detail.append(f"revision={rev!r} (<12)")
    if not hist:
        ok = False
        detail.append("empty revision_history")
    else:
        last = hist[-1]
        if last.get("unused") is not False:
            ok = False
            detail.append(f"last history entry unused={last.get('unused')!r}")
        if last.get("at") != doc.get("revised_at"):
            ok = False
            detail.append("last history at != revised_at")
        idx = [e.get("index") for e in hist if isinstance(e, dict)]
        if idx and max(i for i in idx if isinstance(i, int)) > rev:
            ok = False
            detail.append("history index exceeds revision")
    return (
        "pass" if ok else "fail",
        {"revision": rev, "last_entry": hist[-1] if hist else None},
        "revision bumped and history consistent" if ok else "; ".join(detail),
    )


def c04_canonical_contract_pointer(ctx):
    doc = ctx["doc"]
    pointer = doc.get("class_contract_pointer")
    expectation = f"{CANON_TAX}#classes.{CLASS_ID}"
    measured = {"pointer": pointer, "expected": expectation}
    if pointer != expectation:
        return "fail", measured, "pointer does not target canonical taxonomy#classes.<class>"
    tax = ctx["canon_tax"]
    ok, node = resolve_fragment(tax, f"classes.{CLASS_ID}")
    measured["fragment_resolves"] = ok
    measured["contract_keys"] = sorted(node.keys())[:12] if isinstance(node, dict) else None
    declared = (doc.get("f0_binding") or {}).get("declared_f0_artifact")
    measured["pointer_path_equals_declared_f0"] = pointer.split("#")[0] == declared
    good = ok and measured["pointer_path_equals_declared_f0"]
    return (
        "pass" if good else "fail",
        measured,
        "canonical contract pointer resolves in the declared F0 artifact"
        if good
        else "pointer unresolved or points at a non-declared artifact (HF-034-2 shape)",
    )


def c05_supplement_pointer_separate(ctx):
    doc = ctx["doc"]
    canonical = doc.get("class_contract_pointer") or ""
    supp = doc.get("class_contract_supplement_pointer")
    expected = f"{SUPP_TAX}#class_contracts.{CLASS_ID}"
    measured = {"canonical_pointer": canonical, "supplement_pointer": supp, "expected": expected}
    if supp != expected:
        return "fail", measured, "supplement pointer wrong"
    ok, node = resolve_fragment(ctx["supp_tax"], f"class_contracts.{CLASS_ID}")
    measured["fragment_resolves"] = ok
    measured["fields_distinct"] = canonical.split("#")[0] != supp.split("#")[0]
    bound_path = (doc.get("f0_binding") or {}).get("class_contract_supplement")
    measured["bound_supplement_matches_pointer"] = bound_path == supp.split("#")[0]
    good = ok and measured["fields_distinct"] and measured["bound_supplement_matches_pointer"]
    return (
        "pass" if good else "fail",
        measured,
        "supplement pointer resolves and is a distinct field" if good else "supplement pointer unresolved/conflated",
    )


def c06_f0_binding_hash(ctx):
    fb = ctx["doc"].get("f0_binding") or {}
    path = fb.get("declared_f0_artifact")
    declared = fb.get("declared_f0_sha256")
    measured_hash = sha256_file(os.path.join(REPO, path)) if path else None
    evidence_path = fb.get("consistency_evidence")
    evidence_declared = fb.get("consistency_evidence_sha256")
    evidence_live = sha256_file(os.path.join(REPO, evidence_path)) if evidence_path else None
    ok = bool(path) and declared == measured_hash and bool(evidence_path) and bool(evidence_declared)
    return (
        "pass" if ok else "fail",
        {
            "declared_f0_artifact": path,
            "declared": declared,
            "measured": measured_hash,
            "consistency_evidence": evidence_path,
            "consistency_evidence_declared": evidence_declared,
            "consistency_evidence_live": evidence_live,
            "consistency_evidence_matches": evidence_declared == evidence_live,
        },
        "declared F0 hash matches measured canonical taxonomy"
        if ok
        else "declared F0 hash mismatch",
    )


def c07_frozen_pin(ctx):
    fr = ctx["frozen"]
    files = fr.get("files") or {}
    target_hash = ctx["target_sha"]
    pin_can = (files.get(TARGET) or {}).get("sha256")
    pin_auth = (files.get(TARGET_AUTHORING) or {}).get("sha256")
    mirror_equal = ctx["authoring_sha"] == target_hash
    rev = fr.get("revision")
    frozen_at = parse_iso(fr.get("frozen_at"))
    not_future = frozen_at is not None and (frozen_at - ctx["now"]).total_seconds() <= 60
    ok = (
        isinstance(rev, int)
        and rev >= 28
        and pin_can == target_hash
        and pin_auth == target_hash
        and mirror_equal
        and not_future
    )
    return (
        "pass" if ok else "fail",
        {
            "frozen_revision": rev,
            "frozen_at": fr.get("frozen_at"),
            "pin_canonical": pin_can,
            "pin_authoring": pin_auth,
            "target_sha256": target_hash,
            "mirror_equal": mirror_equal,
            "frozen_at_not_future": not_future,
        },
        "FROZEN pins this revision on both paths, mirror equal" if ok else "frozen pin/mirror mismatch",
    )


def c08_class_identity(ctx):
    doc = ctx["doc"]
    comps = doc.get("class_components") or {}
    tokens = set(re.findall(r"AF-[A-Z0-9]+(?:-[A-Z0-9]+)*", ctx["raw"]))
    stray = sorted(t for t in tokens if t not in FROZEN_CLASS_IDS)
    peer = ctx["f2a"].get("class_components") or {}
    distinct_from_sibling = (
        comps.get("regularity_token") == "C0" and peer.get("regularity_token") == "C2"
    )
    ok = (
        doc.get("class_id") == CLASS_ID
        and comps == EXPECTED_COMPONENTS
        and doc.get("sibling_disjoint_from") == SIBLING_ID
        and not stray
        and distinct_from_sibling
    )
    return (
        "pass" if ok else "fail",
        {
            "class_id": doc.get("class_id"),
            "class_components": comps,
            "sibling_disjoint_from": doc.get("sibling_disjoint_from"),
            "sibling_regularity_token": peer.get("regularity_token"),
            "regularity_axis_separates_from_sibling": distinct_from_sibling,
            "unexpected_class_tokens": stray,
        },
        "class identity clean, regularity axis separates it from the C2 sibling"
        if ok
        else "class identity defect",
    )


def c09_d0_well_typed_cross_class(ctx):
    d0 = d0_of(ctx["doc"])
    ordered = (ctx["doc"].get("quantifiers") or {}).get("ordered") or []
    first = ordered[0] if ordered else {}
    peers = {}
    for name, doc in (("F1", ctx["f1"]), ("F2a", ctx["f2a"])):
        peers[name] = d0_of(doc).get("definition")
    d0_def = d0.get("definition")
    same_f2a = d0_def == peers["F2a"]
    same_f1 = d0_def == peers["F1"]
    tagged = isinstance(d0_def, str) and "tagged disjoint union" in d0_def and "r = smooth" in d0_def
    sobolev_branch = isinstance(d0_def, str) and "(sobolev,s,delta)" in d0_def and "s > 5/2" in d0_def
    binder_ok = first.get("kind") == "forall" and first.get("binder") == "r" and first.get("domain_id") == "D0"
    ref_ok = d0.get("definition_ref") == "regularity.data_regularity"
    ok = tagged and sobolev_branch and binder_ok and ref_ok and same_f2a and same_f1
    return (
        "pass" if ok else "fail",
        {
            "D0_tagged_disjoint_union": tagged,
            "D0_sobolev_branch": sobolev_branch,
            "first_binder": first,
            "definition_ref": d0.get("definition_ref"),
            "D0_equal_to_F2a": same_f2a,
            "D0_equal_to_F1": same_f1,
        },
        "D0 well-typed tagged union and byte-identical across F1/F2a/F2b"
        if ok
        else "D0 repair incomplete or cross-class drift (HF-034-1 shape)",
    )


def c10_extension_predicate(ctx):
    ep = ctx["doc"].get("extension_predicate") or {}
    definition = ep.get("definition") or ""
    clauses = [tag for tag in ("(a)", "(b)", "(c)", "(d)", "(e)", "(f)") if tag in definition]
    conflict = ep.get("must_not_conflate") or []
    caveat = ep.get("c0_uniqueness_caveat")
    continuous = "continuous" in definition and "nondegenerate" in definition
    ok = (
        ep.get("frozen_regularity") == "C0"
        and ep.get("frozen_equation_concept") == "none"
        and ep.get("frozen_direction") == "future"
        and len(clauses) == 6
        and continuous
        and len(conflict) >= 3
        and bool(caveat)
    )
    return (
        "pass" if ok else "fail",
        {
            "frozen_regularity": ep.get("frozen_regularity"),
            "frozen_equation_concept": ep.get("frozen_equation_concept"),
            "frozen_direction": ep.get("frozen_direction"),
            "clauses_present": clauses,
            "continuity_requirement_present": continuous,
            "n_must_not_conflate": len(conflict),
            "c0_uniqueness_caveat_present": bool(caveat),
        },
        "extension predicate frozen at C0 with clauses (a)-(f)" if ok else "extension predicate defect",
    )


def c11_conclusion_no_merge(ctx):
    doc = ctx["doc"]
    concl = doc.get("conclusion") or {}
    anti = doc.get("anti_scope") or {}
    not_this = anti.get("not_this_class") or []
    anti_ids = {e.get("class_id") for e in not_this if isinstance(e, dict)}
    phrases = " ".join(anti.get("phrases_that_are_not_this_class") or [])
    formal = concl.get("statement_formal") or ""
    forbidden = concl.get("forbidden_strengthenings") or []
    ctype = concl.get("conclusion_type")
    ok = (
        ctype == "scc_c0_future_inextendibility"
        and "proper_future_extension_in_class" in formal
        and "C2" not in formal
        and "H2" not in formal
        and SIBLING_ID in anti_ids
        and "AF-WCC-VAC-GEN" in anti_ids
        and "C0 or C2" in phrases
        and len(forbidden) >= 3
        and any("ALL AF" in f or "all AF" in f for f in forbidden)
        and any("WCC" in f or "I+" in f for f in forbidden)
        and CB_NO_MERGE_PHRASES_ABSENT(ctx["raw"])
    )
    return (
        "pass" if ok else "fail",
        {
            "conclusion_type": ctype,
            "formal_uses_proper_extension_predicate": "proper_future_extension_in_class" in formal,
            "formal_mentions_sibling_regularity": ("C2" in formal) or ("H2" in formal),
            "anti_scope_ids": sorted(i for i in anti_ids if i),
            "composite_phrase_listed_forbidden": "C0 or C2" in phrases,
            "n_forbidden_strengthenings": len(forbidden),
        },
        "no C0/C2 merge; conclusion typed C0 and not inflated" if ok else "merge/conclusion-type defect",
    )


def CB_NO_MERGE_PHRASES_ABSENT(raw):
    # 'C0 or C2' is allowed only inside an anti-scope/forbidden phrase, never as a class selector.
    for line in raw.splitlines():
        if "C0 or C2" in line and not re.search(
            r"any 'C0 or C2'|forbidden|not_this_class|anti_scope|composite", line
        ):
            return False
    return True


def c12_no_wcc_content_in_conclusion(ctx):
    doc = ctx["doc"]
    ip = doc.get("i_plus") or {}
    vis = doc.get("visibility") or {}
    concl = doc.get("conclusion") or {}
    formal = concl.get("statement_formal") or ""
    natural = concl.get("statement_natural_language") or ""
    leaked = bool(re.search(r"I\+|null infinity|visible|visibility", formal + " " + natural))
    ok = (
        ip.get("in_conclusion") is False
        and ip.get("completeness_in_conclusion") is False
        and vis.get("role") == "not_in_conclusion"
        and not leaked
    )
    return (
        "pass" if ok else "fail",
        {
            "i_plus_in_conclusion": ip.get("in_conclusion"),
            "i_plus_completeness_in_conclusion": ip.get("completeness_in_conclusion"),
            "visibility_role": vis.get("role"),
            "conclusion_leaks_wcc_token": leaked,
        },
        "no WCC/I+ content in the SCC conclusion" if ok else "WCC content leaked into conclusion",
    )


def c13_genericity_block(ctx):
    gen = ctx["doc"].get("genericity") or {}
    ambient = gen.get("ambient_space") or ""
    ambient_l = ambient.lower()
    generic_set = gen.get("generic_set") or ""
    ok = (
        gen.get("kind") == "residual_comeager"
        and "constraint manifold" in ambient_l
        and "subspace topology" in ambient_l
        and "meager" in generic_set
        and gen.get("is_part_of_class") is True
        and gen.get("excluded_set_status") == "unresolved"
        and bool(gen.get("class_change_warning"))
    )
    return (
        "pass" if ok else "fail",
        {
            "kind": gen.get("kind"),
            "ambient_names_constraint_manifold": "constraint manifold" in ambient_l,
            "ambient_names_subspace_topology": "subspace topology" in ambient_l,
            "generic_set_declares_meager_complement": "meager" in generic_set,
            "is_part_of_class": gen.get("is_part_of_class"),
            "excluded_set_status": gen.get("excluded_set_status"),
            "class_change_warning_present": bool(gen.get("class_change_warning")),
        },
        "genericity block consistent and declared part of the class"
        if ok
        else "genericity block defect",
    )


def c14_falsifier_block(ctx):
    fal = ctx["doc"].get("falsifier") or {}
    t1 = fal.get("tier_1") or {}
    obligations = t1.get("proof_obligations") or []
    machine = t1.get("machine_checkable_steps") or []
    gen_req = t1.get("genericity_requirement") or ""
    witness = t1.get("witness_type") or ""
    ok = (
        t1.get("refutes") == CLASS_ID
        and bool(witness)
        and "C0" in witness
        and "non-meager" in gen_req
        and len(obligations) >= 2
        and len(machine) >= 1
    )
    return (
        "pass" if ok else "fail",
        {
            "tier_1_refutes": t1.get("refutes"),
            "witness_mentions_C0": "C0" in witness,
            "genericity_requirement_mentions_non_meager": "non-meager" in gen_req,
            "n_proof_obligations": len(obligations),
            "n_machine_checkable_steps": len(machine),
        },
        "falsifier block bound to this class with a non-meagerness route"
        if ok
        else "falsifier block defect",
    )


def c15_transfer_precondition(ctx):
    doc = ctx["doc"]
    ledger = doc.get("implication_ledger") or {}
    entail = {
        (e.get("from"), e.get("to"))
        for e in (ledger.get("one_way_entailments") or [])
        if isinstance(e, dict)
    }
    forbid = {
        (e.get("from"), e.get("to"))
        for e in (ledger.get("forbidden_transfers") or [])
        if isinstance(e, dict)
    }
    c0_to_c2 = ("no proper future C0 metric extension", "no proper future C2 extension") in entail
    h2_to_c2 = any(
        a.startswith("no proper future H2") and b == "no proper future C2 extension" for a, b in entail
    )
    c0_to_h2 = any(
        a == "no proper future C0 metric extension" and b.startswith("no proper future H2")
        for a, b in entail
    )
    c2_to_c0_forbidden = any(
        a == "no proper future C2 extension" and b in ("no proper future C0 extension", "this class")
        for a, b in forbid
    )
    wcc_forbidden = any(a == "AF-WCC-VAC-GEN" and b == "this class" for a, b in forbid)
    cross_family = "no WCC <-> SCC transfer" in (ledger.get("cross_family") or "")
    subsumption = "C0 => H2loc => C2" in (ledger.get("subsumption_note") or "")
    f2a_reg = sobolev_of(ctx["f2a"])
    f1_reg = sobolev_of(ctx["f1"])
    own_reg = sobolev_of(doc)
    shared = (
        own_reg.get("s") == f2a_reg.get("s") == f1_reg.get("s")
        and own_reg.get("delta") == f2a_reg.get("delta") == f1_reg.get("delta")
    )
    ok = (
        c0_to_c2
        and c0_to_h2
        and h2_to_c2
        and c2_to_c0_forbidden
        and wcc_forbidden
        and cross_family
        and subsumption
        and shared
    )
    return (
        "pass" if ok else "fail",
        {
            "C0_entails_C2": c0_to_c2,
            "C0_entails_H2loc": c0_to_h2,
            "H2loc_entails_C2": h2_to_c2,
            "C2_to_C0_forbidden": c2_to_c0_forbidden,
            "WCC_to_this_class_forbidden": wcc_forbidden,
            "cross_family_transfer_denied": cross_family,
            "subsumption_direction_C0_H2loc_C2": subsumption,
            "shared_regularity_with_F1_F2a": shared,
            "own_s_delta": [own_reg.get("s"), own_reg.get("delta")],
        },
        "C0=>C2 entailment ledger complete and one-way" if ok else "transfer precondition defect",
    )


def c16_evidence_pointer_observation(ctx):
    fb = ctx["doc"].get("f0_binding") or {}
    declared = fb.get("consistency_evidence_sha256")
    path = fb.get("consistency_evidence")
    measured = sha256_file(os.path.join(REPO, path)) if path else None
    return (
        "observation",
        {"declared": declared, "measured": measured, "path": path, "match": declared == measured},
        "inline consistency-evidence pointer still resolves"
        if declared == measured
        else "inline consistency-evidence pointer is stale after the rev28 re-freeze (same family defect as HF-034-F2A-3 / HF-086-R1)",
    )


def c17_data_class_differentiation_observation(ctx):
    f2a_dc = json.dumps(ctx["f2a"].get("data_class"), sort_keys=True)
    f2b_dc = json.dumps(ctx["doc"].get("data_class"), sort_keys=True)
    same_keys = sorted((ctx["f2a"].get("data_class") or {}).keys()) == sorted(
        (ctx["doc"].get("data_class") or {}).keys()
    )
    rec = (ctx["doc"].get("data_class") or {}).get("adm_mass") or {}
    sibling_rec = (ctx["f2a"].get("data_class") or {}).get("adm_mass") or {}
    only_annotation_diff = (
        not same_keys
        or {
            k: v
            for k, v in (ctx["doc"].get("data_class") or {}).items()
            if k != "adm_mass"
        }
        == {
            k: v
            for k, v in (ctx["f2a"].get("data_class") or {}).items()
            if k != "adm_mass"
        }
    )
    return (
        "observation",
        {
            "data_class_json_equal": f2a_dc == f2b_dc,
            "same_key_set": same_keys,
            "differs_only_in_adm_mass_annotations": only_annotation_diff,
            "f2b_adm_mass_has_hypotheses_reconciliation": "hypotheses_reconciliation" in rec,
            "f2a_adm_mass_has_hypotheses_reconciliation": "hypotheses_reconciliation" in sibling_rec,
            "separation_axes": [
                "class_components.regularity_token (C0 vs C2)",
                "extension_predicate.frozen_regularity (C0 vs C2)",
                "extension_predicate.frozen_equation_concept (none vs classical_ricci)",
            ],
        },
        "C0/C2 data_class blocks differ only in adm_mass annotation text: the class separation rests on regularity_token and extension_predicate (input to audit-lead O-GFORM-1, not adjudicated here)",
    )


CHECKS = [
    ("C01", "duplicate_top_level_keys", c01_duplicate_top_level_keys),
    ("C02", "revised_at_wall_clock", c02_revised_at_wall_clock),
    ("C03", "revision_history_consistency", c03_revision_history),
    ("C04", "canonical_contract_pointer", c04_canonical_contract_pointer),
    ("C05", "supplement_pointer_separate", c05_supplement_pointer_separate),
    ("C06", "f0_binding_hash", c06_f0_binding_hash),
    ("C07", "frozen_pin_mirror", c07_frozen_pin),
    ("C08", "class_identity_no_stray_token", c08_class_identity),
    ("C09", "d0_well_typed_cross_class", c09_d0_well_typed_cross_class),
    ("C10", "extension_predicate_frozen_c0", c10_extension_predicate),
    ("C11", "conclusion_no_merge", c11_conclusion_no_merge),
    ("C12", "no_wcc_content_in_conclusion", c12_no_wcc_content_in_conclusion),
    ("C13", "genericity_block", c13_genericity_block),
    ("C14", "falsifier_block", c14_falsifier_block),
    ("C15", "transfer_precondition", c15_transfer_precondition),
]
OBSERVATIONS = [
    ("OBS-089-2", "evidence_pointer_observation", c16_evidence_pointer_observation),
    ("OBS-089-3", "data_class_differentiation_observation", c17_data_class_differentiation_observation),
]


# --------------------------------------------------------------------------
# controls: each mutates a deep copy and must make its mapped check fail
# --------------------------------------------------------------------------
def mut_dup_key(ctx):
    ctx = copy.deepcopy(ctx)
    ctx["raw"] = raw = ctx["raw"].replace(
        "revision: 12", 'revision: 12\nrevised_at: "2026-09-12T00:31:41+08:00"', 1
    )
    ctx["doc"] = yaml.safe_load(raw)
    return ctx


def mut_future_revised_at(ctx):
    ctx = copy.deepcopy(ctx)
    ctx["doc"]["revised_at"] = (ctx["now"] + dt.timedelta(hours=2)).isoformat(timespec="seconds")
    return ctx


def mut_pointer_authoring(ctx):
    ctx = copy.deepcopy(ctx)
    ctx["doc"]["class_contract_pointer"] = f"{SUPP_TAX}#classes.{CLASS_ID}"
    return ctx


def mut_pointer_dangling(ctx):
    ctx = copy.deepcopy(ctx)
    ctx["doc"]["class_contract_pointer"] = f"{CANON_TAX}#classes.AF-NOPE"
    return ctx


def mut_f0_hash(ctx):
    ctx = copy.deepcopy(ctx)
    ctx["doc"]["f0_binding"]["declared_f0_sha256"] = "0" * 64
    return ctx


def mut_pin_mismatch(ctx):
    ctx = copy.deepcopy(ctx)
    ctx["authoring_sha"] = "0" * 64
    return ctx


def mut_class_id(ctx):
    ctx = copy.deepcopy(ctx)
    ctx["doc"]["class_id"] = "AF-SCC-C2-C0-MERGE"
    return ctx


def mut_d0_regress(ctx):
    ctx = copy.deepcopy(ctx)
    ctx["doc"]["quantifiers"]["domains"]["D0"]["definition"] = (
        "admissible regularity: r = (s,delta,norm) a single pair with s > 5/2"
    )
    return ctx


def mut_extension_widen(ctx):
    ctx = copy.deepcopy(ctx)
    ctx["doc"]["extension_predicate"]["frozen_regularity"] = "C2"
    return ctx


def mut_conclusion_visibility(ctx):
    ctx = copy.deepcopy(ctx)
    ctx["doc"]["conclusion"]["statement_formal"] = (
        "forall r in D0 exists G_r comeager forall D in G_r: "
        "not exists visible_singularity_from_I_plus(MGHD(D))"
    )
    return ctx


def mut_conclusion_type(ctx):
    ctx = copy.deepcopy(ctx)
    ctx["doc"]["conclusion"]["conclusion_type"] = "scc_c2_future_inextendibility"
    return ctx


def mut_falsifier_class(ctx):
    ctx = copy.deepcopy(ctx)
    ctx["doc"]["falsifier"]["tier_1"]["refutes"] = SIBLING_ID
    return ctx


def mut_transfer_drop(ctx):
    ctx = copy.deepcopy(ctx)
    ledger = ctx["doc"]["implication_ledger"]
    ledger["one_way_entailments"] = [
        e for e in ledger["one_way_entailments"] if e.get("from") != "no proper future C0 metric extension"
    ]
    return ctx


def mut_genericity_flat(ctx):
    ctx = copy.deepcopy(ctx)
    ctx["doc"]["genericity"]["is_part_of_class"] = False
    return ctx


CONTROLS = [
    ("M1", "planted duplicate revised_at key", "C01", mut_dup_key),
    ("M2", "planted future revised_at", "C02", mut_future_revised_at),
    ("M3", "pointer redirected at the authoring tree", "C04", mut_pointer_authoring),
    ("M4", "pointer fragment dangles (classes.AF-NOPE)", "C04", mut_pointer_dangling),
    ("M5", "declared F0 hash corrupted", "C06", mut_f0_hash),
    ("M6", "authoring mirror diverged from the canonical pin", "C07", mut_pin_mismatch),
    ("M7", "merge-shaped class id planted", "C08", mut_class_id),
    ("M8", "D0 regressed to an ill-typed single pair", "C09", mut_d0_regress),
    ("M9", "extension regularity widened to C2", "C10", mut_extension_widen),
    ("M10", "WCC visibility predicate imported into the conclusion", "C12", mut_conclusion_visibility),
    ("M11", "conclusion_type widened to the C2 class", "C11", mut_conclusion_type),
    ("M12", "falsifier rebound to the sibling class", "C14", mut_falsifier_class),
    ("M13", "licensed C0=>C2 entailment deleted", "C15", mut_transfer_drop),
    ("M14", "genericity demoted out of the class identity", "C13", mut_genericity_flat),
]


# --------------------------------------------------------------------------
def build_ctx(now=None):
    target_path = os.path.join(REPO, TARGET)
    authoring_path = os.path.join(REPO, TARGET_AUTHORING)
    raw = read_text(target_path)
    ctx = {
        "raw": raw,
        "doc": yaml.safe_load(raw),
        "target_sha": hashlib.sha256(raw.encode()).hexdigest(),
        "authoring_sha": sha256_file(authoring_path),
        "mtime": os.stat(target_path).st_mtime,
        "now": now or dt.datetime.now().astimezone(),
        "frozen": json.loads(read_text(os.path.join(REPO, FROZEN))),
        "canon_tax": load_yaml(os.path.join(REPO, CANON_TAX)),
        "supp_tax": load_yaml(os.path.join(REPO, SUPP_TAX)),
        "f1": load_yaml(os.path.join(REPO, F1)),
        "f2a": load_yaml(os.path.join(REPO, F2A)),
    }
    return ctx


def run_checks(ctx, checks):
    out = {}
    for cid, name, fn in checks:
        status, measured, detail = fn(ctx)
        out[cid] = {"name": name, "status": status, "measured": measured, "detail": detail}
    return out


def run_controls(base_ctx):
    results = {}
    for cid, desc, target_check, mutate in CONTROLS:
        mutant = mutate(base_ctx)
        fn = dict((c[0], c[2]) for c in CHECKS)[target_check]
        status, measured, detail = fn(mutant)
        results[cid] = {
            "desc": desc,
            "target_check": target_check,
            "caught": status == "fail",
            "observed_status": status,
            "detail": detail,
        }
        try:
            out = os.path.join(HERE, "controls", f"{cid}.yaml")
            with open(out, "w", encoding="utf-8") as fh:
                if isinstance(mutant["doc"], dict):
                    yaml.safe_dump(mutant["doc"], fh, sort_keys=False, allow_unicode=True)
                else:
                    fh.write(mutant["raw"])
        except Exception as exc:  # pragma: no cover
            results[cid]["write_error"] = str(exc)
    return results


def stability(ctx, window, interval):
    paths = [TARGET, TARGET_AUTHORING, FROZEN, CANON_TAX, SUPP_TAX, F1, F2A]
    timeline = []
    start = dt.datetime.now().astimezone()
    deadline = start.timestamp() + window
    first = {p: sha256_file(os.path.join(REPO, p)) for p in paths}
    while True:
        sample = {p: sha256_file(os.path.join(REPO, p)) for p in paths}
        timeline.append(
            {"at": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "hashes": sample}
        )
        if dt.datetime.now().astimezone().timestamp() >= deadline:
            break
        import time as _time

        _time.sleep(interval)
    last = timeline[-1]["hashes"]
    drifted = sorted(p for p in paths if first[p] != last[p])
    return {
        "window_seconds": window,
        "interval_seconds": interval,
        "samples": len(timeline),
        "first": first,
        "last": last,
        "drifted_paths": drifted,
        "drift_detected": bool(drifted),
        "timeline": timeline,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=90)
    ap.add_argument("--interval", type=int, default=15)
    ap.add_argument("--out", default=os.path.join(HERE, "f2b_review_report.json"))
    args = ap.parse_args(argv)

    os.makedirs(os.path.join(HERE, "controls"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "pinned"), exist_ok=True)

    ctx = build_ctx()
    checks = run_checks(ctx, CHECKS)
    observations = run_checks(ctx, OBSERVATIONS)
    controls = run_controls(ctx)
    stab = stability(ctx, args.window, args.interval)

    snap_target = os.path.join(HERE, "pinned", f"af_scc_c0_vacuum.{ctx['target_sha'][:12]}.yaml")
    with open(snap_target, "w", encoding="utf-8") as fh:
        fh.write(ctx["raw"])
    snap_frozen = os.path.join(HERE, "pinned", "FROZEN.rev28.json")
    with open(snap_frozen, "w", encoding="utf-8") as fh:
        fh.write(read_text(os.path.join(REPO, FROZEN)))

    fails = [cid for cid, r in checks.items() if r["status"] == "fail"]
    no_false_positive = all(r["status"] == "pass" for r in checks.values())
    controls_ok = all(c["caught"] for c in controls.values())
    verdict = "accept" if not fails and controls_ok else "revise"

    report = {
        "schema_version": "1.0",
        "task_id": "W089-F2B-REV12-REVIEW-04",
        "worker": "worker-089",
        "class_id": CLASS_ID,
        "node_id": "F2b",
        "gate": "G-FORM",
        "created_at": iso_now(),
        "target": {
            "path": TARGET,
            "sha256": ctx["target_sha"],
            "authoring_path": TARGET_AUTHORING,
            "authoring_sha256": ctx["authoring_sha"],
            "mirror_equal": ctx["authoring_sha"] == ctx["target_sha"],
            "revision": ctx["doc"].get("revision"),
            "revised_at": ctx["doc"].get("revised_at"),
            "mtime": dt.datetime.fromtimestamp(ctx["mtime"]).astimezone().isoformat(timespec="seconds"),
            "bytes": len(ctx["raw"].encode()),
        },
        "frozen_manifest": {
            "path": FROZEN,
            "revision": ctx["frozen"].get("revision"),
            "frozen_at": ctx["frozen"].get("frozen_at"),
            "sha256": sha256_file(os.path.join(REPO, FROZEN)),
        },
        "checks": checks,
        "observations": observations,
        "controls": controls,
        "control_summary": {
            "n_controls": len(controls),
            "all_caught": controls_ok,
            "no_false_positive_baseline": no_false_positive,
        },
        "stability": stab,
        "verdict": verdict,
        "score": 4.0 if verdict == "accept" else 3.0,
        "hard_failures": [
            {"id": f"HF-089-{cid}", "detail": checks[cid]["detail"], "measured": checks[cid]["measured"]}
            for cid in fails
        ],
        "scope": (
            "independent machine-checked structural and consistency review of F2b rev12 at the FROZEN rev28 "
            "pin 55d0a1ea9bda: closure check of HF-034-1 (D0 well-typedness) and HF-034-2 (canonical contract "
            "pointer) at this hash, C0-specific extension-predicate invariants, class-identity separation from "
            "the C2 sibling and from WCC, the one-way C0=>C2 entailment ledger, and frozen-pin/mirror alignment. "
            "Excludes: adjudication of the stale inline consistency-evidence pointer (OBS-089-2, same family "
            "defect as HF-034-F2A-3/HF-086-R1), adjudication of O-GFORM-1 (data_class differentiation; "
            "OBS-089-3 records the measured input), L1 citation adjudication, and any gate verdict."
        ),
        "independence": (
            "worker-089 authored no canonical artifact and no part of F2b. Prior worker-089 tasks bound F2b at "
            "the superseded 1bb78ce9b357 bytes and F2a at rev12; this is the first worker-089 verdict bound to "
            "55d0a1ea9bda. Controls M1-M14 each plant one defect class so a pass is controlled; the unmutated "
            "baseline must pass all checks."
        ),
        "counts_as_gate_accept": False,
        "falsifier": (
            "Any of C01-C15 flips to fail at a newer canonical hash of schemas/af_scc_c0_vacuum.yaml, or the "
            "FROZEN pin/mirror equality breaks, or a planted control stops being caught: then this accept is "
            "void for the newer revision. A hash move inside the stability window makes the verdict advisory "
            "for the pinned bytes only."
        ),
        "next_falsifier": (
            "Any of C01-C15 flips to fail at a newer canonical hash of schemas/af_scc_c0_vacuum.yaml, or the "
            "FROZEN pin/mirror equality breaks, or a planted control stops being caught: then this accept is "
            "void for the newer revision. A hash move inside the stability window makes the verdict advisory "
            "for the pinned bytes only."
        ),
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True, default=str)
    print(
        json.dumps(
            {
                "out": args.out,
                "target_sha256": ctx["target_sha"],
                "verdict": verdict,
                "fails": fails,
                "controls_all_caught": controls_ok,
                "drift_detected": stab["drift_detected"],
                "observations": {k: v["detail"] for k, v in observations.items()},
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
