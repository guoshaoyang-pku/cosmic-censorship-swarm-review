#!/usr/bin/env python3
"""W072-F1-REVIEW-REV13-01 instrument: independent, from-scratch conformance checks for
schemas/af_wcc_vacuum.yaml (class AF-WCC-VAC-GEN, node F1, gate G-FORM).

Written by worker-072 without reading any other reviewer's F1 verdict text.
The harness helpers are re-used from my own F2a instrument
(artifacts/worker-072/f2a_review/check_f2a.py, disclosed in the review); the F1
check set below is new and F1-specific (WCC conclusion, 6-link quantifier chain,
tail/equivalent visibility predicate, rev13 strictness-direction repair).
It does not import research_map/class_separation.py, artifacts/formulation/tools/
check_class_schema.py or artifacts/worker-06/spec_conformance_audit.py.

Design rules (CF-16 metalinguistic-mention discipline):
  * Assertion sites only. Class-id / composite-token / SCC-token scans read the
    specification slots (class_id, scope_statement, quantifiers, conclusion
    statements, visibility/i_plus conclusion fields). anti_scope, forbidden_*,
    must_not_conflate and revision_history are mention sites and are checked for
    the *required mention* instead.
  * Every FAIL is bound to a measured sha256.
  * Duplicate YAML keys are a hard defect.

Usage:
  python3 check_f1.py --json report.json [--root ROOT]
  python3 check_f1.py --controls --json report.json [--root ROOT]
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone, timedelta

import yaml

CST = timezone(timedelta(hours=8))
CLASS_ID = "AF-WCC-VAC-GEN"
SIBLING_C2 = "AF-SCC-C2-VAC-GEN"
SIBLING_C0 = "AF-SCC-C0-VAC-GEN"
NODE_ID = "F1"
EXPECTED_F0_SHA = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
REV12_PIN = "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"
SCHEMA_CANON = "schemas/af_wcc_vacuum.yaml"
SCHEMA_AUTHOR = "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
TAXONOMY_CANON = "research_map/formulation_taxonomy.yaml"
TAXONOMY_SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
EVIDENCE = "artifacts/formulation/evidence/taxonomy_consistency.json"
FROZEN = "artifacts/formulation/FROZEN.json"
ALLOWED_DELTA_PATHS = {
    "revision", "revised_at", "revision_history",
    "f0_binding.consistency_evidence_sha256", "f0_binding.checked_at", "f0_binding.binding_note",
    "visibility.definition", "quantifiers.domains.D5.definition",
    "class_identity_variants.[0].relation",
}


def now() -> str:
    return datetime.now(CST).replace(microsecond=0).isoformat()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class DupTrackingLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys instead of silently merging."""

    def __init__(self, stream):
        super().__init__(stream)
        self.dup_keys: list[str] = []


def _construct_mapping(loader: DupTrackingLoader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            loader.dup_keys.append(str(key))
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


DupTrackingLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def parse_yaml(path: str):
    text = open(path, "r", encoding="utf-8").read()
    loader = DupTrackingLoader(io.StringIO(text))
    node = loader.get_single_node()
    doc = loader.construct_document(node) if node is not None else None
    return doc, loader.dup_keys, text


def resolve(doc, dotted: str):
    cur = doc
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None, False
    return cur, True


def as_list(x) -> list:
    return x if isinstance(x, list) else []


COMPOSITE_RE = re.compile(r"\bC\s*0\s*(?:or|/|,|&|\+)\s*C\s*2\b|\bC\s*2\s*(?:or|/|,|&|\+)\s*C\s*0\b", re.I)
CLASS_TOKEN_RE = re.compile(r"\bAF-[A-Z0-9]+(?:-[A-Z0-9]+)+\b")
SCC_TOKEN_RE = re.compile(r"strong cosmic censorship|\bSCC\b|(?:development|spacetime|solution)\b[^.]{0,60}?\binextendib", re.I)


def assertion_sites(doc: dict) -> dict:
    """Specification slots: class-id/scope/conclusion tokens count as assertions here."""
    q = doc.get("quantifiers") or {}
    concl = doc.get("conclusion") or {}
    vis = doc.get("visibility") or {}
    ip = doc.get("i_plus") or {}
    sites = {
        "class_id": doc.get("class_id"),
        "scope_statement": doc.get("scope_statement"),
        "quantifiers.formal": q.get("formal"),
        "quantifiers.negation": q.get("negation"),
        "quantifiers.negation_normal_form": q.get("negation_normal_form"),
        "conclusion.conclusion_type": concl.get("conclusion_type"),
        "conclusion.family": concl.get("family"),
        "conclusion.statement_natural_language": concl.get("statement_natural_language"),
        "conclusion.statement_formal": concl.get("statement_formal"),
        "visibility.definition": vis.get("definition"),
        "visibility.negation_conclusion": vis.get("negation_conclusion"),
        "i_plus.definition": ip.get("definition"),
    }
    for did, d in (q.get("domains") or {}).items():
        if isinstance(d, dict):
            sites[f"quantifiers.domains.{did}.definition"] = d.get("definition")
    return {k: v for k, v in sites.items() if isinstance(v, str)}


def flat_diff(a, b, prefix="") -> list:
    """Return the dotted key paths whose scalar/list value differs between two docs."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            out += flat_diff(a.get(k), b.get(k), f"{prefix}{k}.")
    elif isinstance(a, list) and isinstance(b, list):
        if a != b:
            if len(a) == len(b):
                for i, (x, y) in enumerate(zip(a, b)):
                    if x != y:
                        out += flat_diff(x, y, f"{prefix}[{i}].")
            else:
                out.append(prefix.rstrip("."))
    elif a != b:
        out.append(prefix.rstrip("."))
    return out


def delta_check(root: str) -> dict:
    """Verify the rev12 -> rev13 change set is exactly the carded F1 repair + evidence refresh."""
    before_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pins", "af_wcc_vacuum.rev12.yaml")
    before_sha = sha256_file(before_path) if os.path.exists(before_path) else None
    before, _, _ = parse_yaml(before_path)
    after, _, _ = parse_yaml(os.path.join(root, SCHEMA_CANON))
    after_sha = sha256_file(os.path.join(root, SCHEMA_CANON))
    changed = flat_diff(after, before)
    unexpected = [c for c in changed if c not in ALLOWED_DELTA_PATHS]
    f0b = after.get("f0_binding") or {}
    hist = as_list(after.get("revision_history"))
    note = " ".join(str(e.get("notes", "")) for e in hist if isinstance(e, dict))
    ok = (before_sha == REV12_PIN and after_sha is not None and after_sha != REV12_PIN
          and not unexpected
          and after.get("revision") == before.get("revision", 0) + 1
          and f0b.get("declared_f0_sha256") == (before.get("f0_binding") or {}).get("declared_f0_sha256")
          and "rev13" in note and "9e335e9ba1bf" in note and "strictly WEAKER" in note)
    return {
        "before_path": "artifacts/worker-072/f1_review/pins/af_wcc_vacuum.rev12.yaml",
        "before_sha256": before_sha, "before_pin_ok": before_sha == REV12_PIN,
        "after_sha256": after_sha, "revision_before": before.get("revision"), "revision_after": after.get("revision"),
        "changed_paths": changed, "unexpected_changed_paths": unexpected,
        "declared_f0_unchanged": f0b.get("declared_f0_sha256") == (before.get("f0_binding") or {}).get("declared_f0_sha256"),
        "status": "PASS" if ok else "FAIL",
    }


def run_checks(root: str) -> dict:
    p = lambda rel: os.path.join(root, rel)
    measured = {}
    for rel in (SCHEMA_CANON, SCHEMA_AUTHOR, TAXONOMY_CANON, TAXONOMY_SUPP, EVIDENCE, FROZEN):
        measured[rel] = sha256_file(p(rel)) if os.path.exists(p(rel)) else None

    doc, dup_keys, _ = parse_yaml(p(SCHEMA_CANON))
    taxonomy, tax_dups, _ = parse_yaml(p(TAXONOMY_CANON))
    supp, supp_dups, _ = parse_yaml(p(TAXONOMY_SUPP))

    checks = []

    def add(cid, desc, ok, detail, ev):
        checks.append({"id": cid, "description": desc, "status": "PASS" if ok else "FAIL",
                       "detail": detail, "evidence": ev})

    sre = f"{SCHEMA_CANON}#{(measured[SCHEMA_CANON] or '?')[:12]}"
    sre_a = f"{SCHEMA_AUTHOR}#{(measured[SCHEMA_AUTHOR] or '?')[:12]}"
    tre = f"{TAXONOMY_CANON}#{(measured[TAXONOMY_CANON] or '?')[:12]}"
    eve = f"{EVIDENCE}#{(measured[EVIDENCE] or '?')[:12]}"
    fre = f"{FROZEN}#{(measured[FROZEN] or '?')[:12]}"

    sites = assertion_sites(doc)
    q = doc.get("quantifiers") or {}
    concl = doc.get("conclusion") or {}
    gen = doc.get("genericity") or {}
    vis = doc.get("visibility") or {}
    ip = doc.get("i_plus") or {}
    f0 = doc.get("f0_binding") or {}
    fal = doc.get("falsifier") or {}

    # C01 mirror pair published byte-identically
    ok = measured[SCHEMA_CANON] is not None and measured[SCHEMA_CANON] == measured[SCHEMA_AUTHOR]
    add("C01_MIRROR_PAIR", "canonical and authoring copies are byte-identical (mirror pair)",
        ok, f"canon={str(measured[SCHEMA_CANON])[:12]} author={str(measured[SCHEMA_AUTHOR])[:12]}", [sre, sre_a])

    # C02 singular class id / node id in assertion sites
    found_tokens = sorted({m for s in sites.values() for m in CLASS_TOKEN_RE.findall(s)})
    ok = (doc.get("class_id") == CLASS_ID and doc.get("node_id") == NODE_ID
          and found_tokens == [CLASS_ID])
    add("C02_CLASS_ID_SINGULAR", "class_id/node_id match the class and no other class-id token occurs in specification slots",
        ok, f"class_id={doc.get('class_id')} node_id={doc.get('node_id')} assertion_tokens={found_tokens}", [sre])

    # C03 no composite regularity; siblings registered as not-this-class
    comp = {k: COMPOSITE_RE.search(v).group(0) for k, v in sites.items() if COMPOSITE_RE.search(v)}
    anti = [x.get("class_id") for x in as_list((doc.get("anti_scope") or {}).get("not_this_class")) if isinstance(x, dict)]
    phrases = " | ".join((doc.get("anti_scope") or {}).get("phrases_that_are_not_this_class") or [])
    ok = (not comp) and (SIBLING_C0 in anti) and (SIBLING_C2 in anti) and ("C0 or C2" in phrases)
    add("C03_NO_COMPOSITE_REGULARITY", "no C0/C2 composite in a specification slot; both SCC sibling classes and the composite phrase registered as not-this-class",
        ok, f"composite_hits={comp} anti_scope_class_ids={anti} composite_phrase_registered={'C0 or C2' in phrases}", [sre])

    # C04 conclusion type / family / no SCC content in the conclusion text
    ctext = " ".join(str(concl.get(k, "")) for k in ("statement_natural_language", "statement_formal", "conclusion_type"))
    bad = [t for t in ("inextendib", "C0", "C2", "SCC") if t.lower() in ctext.lower()]
    ok = (concl.get("conclusion_type") == "weak_cosmic_censorship" and concl.get("family") == "WCC" and not bad)
    add("C04_CONCLUSION_TYPE_WCC", "conclusion_type is weak_cosmic_censorship, family WCC, and the conclusion statement carries no SCC/inextendibility content",
        ok, f"type={concl.get('conclusion_type')} family={concl.get('family')} scc_tokens={bad}", [sre])

    # C05 I+ and visibility are conclusion-side, in_conclusion true
    ok = (ip.get("role") == "conclusion" and ip.get("in_conclusion") is True
          and vis.get("role") == "conclusion" and vis.get("in_conclusion") is True)
    add("C05_IPLUS_VISIBILITY_IN_CONCLUSION", "I+ and visibility both carry role=conclusion and in_conclusion=true",
        ok, f"i_plus.role={ip.get('role')} in_conclusion={ip.get('in_conclusion')} visibility.role={vis.get('role')} in_conclusion={vis.get('in_conclusion')}", [sre])

    # C06 quantifier shape/order (6 links, generic set chosen before data)
    ordered = as_list(q.get("ordered"))
    got = [(str(e.get("kind")), str(e.get("binder")), str(e.get("domain_id"))) for e in ordered if isinstance(e, dict)]
    want = [("forall", "r", "D0"), ("exists", "G_r", "D1"), ("forall", "(Sigma,h,K)", "D2"),
            ("exists", "(Mtilde,gtilde,Omega)", "D3"), ("forall", "gamma", "D4"), ("not_exists", "(q,t0)", "D5")]
    ok = (got == want and q.get("order_matters") is True
          and bool(q.get("negation")) and bool(q.get("negation_normal_form"))
          and "forall-exists(comeager)-forall-exists-forall-not-exists" in str(q.get("quantifier_class")))
    add("C06_QUANTIFIER_SHAPE", "6-link ordered chain forall-exists(comeager)-forall-exists-forall-not-exists, order_matters=true, negation and normal form present",
        ok, f"ordered={got}", [sre])

    # C07 domains D0-D5 resolve
    domains = q.get("domains") or {}
    missing, unresolved = [], []
    for did in ("D0", "D1", "D2", "D3", "D4", "D5"):
        d = domains.get(did)
        if not isinstance(d, dict) or not d.get("definition"):
            missing.append(did)
            continue
        ref = str(d.get("definition_ref", ""))
        _, found = resolve(doc, ref)
        if not found:
            unresolved.append(f"{did}:{ref}")
    ok = not missing and not unresolved
    add("C07_DOMAINS_RESOLVE", "D0-D5 each carry a definition whose definition_ref resolves inside the document",
        ok, f"missing={missing} unresolved_refs={unresolved}", [sre])

    # C08 topology
    topo = doc.get("topology") or {}
    slice_txt = str(topo.get("slice_topology")) + " " + str(topo.get("end_structure"))
    ok = (str(topo.get("spacetime_dimension")) == "4"
          and "R^3" in slice_txt and "one AF end" in slice_txt
          and "R x S^2" in str(topo.get("I_plus_topology"))
          and bool(as_list(topo.get("forbidden"))) and bool(topo.get("development_topology")))
    add("C08_TOPOLOGY", "4D, one-ended AF slice R^3, I+ topology R x S^2, forbidden list nonempty, development topology declared",
        ok, f"dim={topo.get('spacetime_dimension')} end={topo.get('end_structure')} I+={topo.get('I_plus_topology')} forbidden_n={len(as_list(topo.get('forbidden')))}", [sre])

    # C09 genericity (comeager, Baire, no self-claiming variant, honest unresolved status)
    variants = as_list(gen.get("variants"))
    bad_variants = [v.get("kind") for v in variants if isinstance(v, dict) and v.get("is_this_class") is not False]
    ok = (gen.get("kind") == "residual_comeager"
          and "Baire" in str(gen.get("ambient_space"))
          and bool(gen.get("class_change_warning"))
          and not bad_variants
          and bool(as_list(gen.get("transfer_failures"))) and bool(as_list(gen.get("transfer_holds")))
          and str(gen.get("excluded_set_status")) == "unresolved"
          and bool(gen.get("membership_ruling")))
    add("C09_GENERICITY", "residual/comeager genericity on a Baire constraint space, class-change warning, no variant claiming to be this class, excluded-set status honestly unresolved",
        ok, f"kind={gen.get('kind')} self_claiming_variants={bad_variants} excluded_set_status={gen.get('excluded_set_status')} baire={'Baire' in str(gen.get('ambient_space'))}", [sre])

    # C10 I+ conclusion role and forbidden weakenings
    fw_ip = " | ".join(as_list(ip.get("forbidden_weakenings")))
    ok = (str(ip.get("asymptotically_simple", "")).upper().startswith("NOT ASSUMED")
          and bool(ip.get("completeness_definition"))
          and "replacing completeness by mere existence of I+" in fw_ip
          and bool(ip.get("k_is_a_class_parameter")))
    add("C10_IPLUS_ROLE_AND_WEAKENINGS", "asymptotic simplicity not assumed, completeness defined, existence-only weakening forbidden, k declared a class parameter",
        ok, f"asymptotically_simple={str(ip.get('asymptotically_simple'))[:20]} forbidden_weakenings={len(as_list(ip.get('forbidden_weakenings')))}", [sre])

    # C11 visibility tail predicate, not B-containment
    vd, vn = str(vis.get("definition", "")), str(vis.get("negation_conclusion", ""))
    ok = (vis.get("predicate_name") == "visible_singularity_from_I_plus"
          and "TAIL" in vd and "J^-(q)" in vd
          and "EQUIVALENT" in vd
          and "NOT contained in J^-(q)" in vn
          and "B-containment is strictly stronger" in vn)
    add("C11_VISIBILITY_TAIL_PREDICATE", "visibility is the single-q TAIL predicate stated equivalent to whole-curve containment; its negation is not replaced by B-containment",
        ok, f"predicate={vis.get('predicate_name')} tail={'TAIL' in vd} equivalent={'EQUIVALENT' in vd} b_containment_note={'B-containment is strictly stronger' in vn}", [sre])

    # C12 rev13 strictness-direction repair
    civ = as_list(doc.get("class_identity_variants"))
    rel = str(civ[0].get("relation", "")) if civ and isinstance(civ[0], dict) else ""
    rel_core = re.sub(r"\[\s*rev\d+[^\]]*\]", "", rel)  # strip metalinguistic rev-note mentions
    d5 = str((domains.get("D5") or {}).get("definition", ""))
    d5_core = re.sub(r"\[\s*rev\d+[^\]]*\]", "", d5)
    hist_note = " ".join(str(e.get("notes", "")) for e in as_list(doc.get("revision_history")) if isinstance(e, dict))
    ok = ("strictly WEAKER" in rel_core and "strictly STRONGER" not in rel_core
          and "EQUIVALENT" in d5_core and "NOT a weakening" in d5_core
          and "strictly STRONGER" in hist_note and "rev13" in hist_note)
    add("C12_STRICTNESS_DIRECTION", "rev13 direction repair: variant SET is strictly WEAKER than the class predicate; D5 states whole/tail EQUIVALENCE and that the tail reading is NOT a weakening",
        ok, f"variant_relation_core={rel_core[:80]!r} d5_equivalent={'EQUIVALENT' in d5_core} d5_not_weakening={'NOT a weakening' in d5_core} history_mentions_correction={'strictly STRONGER' in hist_note}", [sre])

    # C13 F0 hash binding (declared taxonomy + consistency evidence vs measured bytes)
    declared_ev = str(f0.get("consistency_evidence_sha256"))
    ev_ok = declared_ev == measured[EVIDENCE]
    tax_ok = str(f0.get("declared_f0_sha256")) == measured[TAXONOMY_CANON]
    paths_ok = os.path.exists(p(str(f0.get("declared_f0_artifact", "")))) and os.path.exists(p(str(f0.get("consistency_evidence", ""))))
    ok = tax_ok and ev_ok and paths_ok
    add("C13_F0_HASH_BINDING", "declared F0 sha256 and consistency_evidence_sha256 both equal the measured live bytes, and both bound paths exist",
        ok, f"declared_f0={str(f0.get('declared_f0_sha256'))[:12]} measured_f0={str(measured[TAXONOMY_CANON])[:12]} declared_ev={declared_ev[:12]} measured_ev={str(measured[EVIDENCE])[:12]} paths_exist={paths_ok}",
        [sre, tre, eve])

    # C14 contract pointers resolve to this class
    ptr = str(doc.get("class_contract_pointer", ""))
    sptr = str(doc.get("class_contract_supplement_pointer", ""))
    canonical_ok = CLASS_ID in (taxonomy.get("classes") or {})
    supplement_ok = CLASS_ID in ((supp or {}).get("class_contracts") or {})
    ok = ptr.startswith(TAXONOMY_CANON + "#classes.") and sptr.startswith(TAXONOMY_SUPP + "#class_contracts.") \
        and canonical_ok and supplement_ok
    add("C14_CONTRACT_POINTERS", "canonical and supplement pointers resolve to this class in their respective trees",
        ok, f"canonical_resolves={canonical_ok} supplement_resolves={supplement_ok} ptr={ptr} sptr={sptr}", [sre, tre])

    # C15 falsifier completeness
    t1 = fal.get("tier_1") or {}
    t2 = fal.get("tier_2") or {}
    gen_req = str(t1.get("genericity_requirement", ""))
    ok = (t1.get("refutes") == CLASS_ID
          and "NON-MEAGER" in gen_req.upper()
          and bool(as_list(t1.get("proof_obligations"))) and bool(as_list(t1.get("machine_checkable_steps")))
          and "forall AF vacuum data" in str(t2.get("refutes", ""))
          and bool(as_list(fal.get("schema_falsifiers"))))
    add("C15_FALSIFIER", "tier-1 falsifier names the class and requires a non-meagerness argument; tier-2 is labelled as refuting only the for-all-data strengthening; schema falsifiers present",
        ok, f"tier1_refutes={t1.get('refutes')} non_meager_required={'NON-MEAGER' in gen_req.upper()} tier2={str(t2.get('refutes'))[:44]}", [sre])

    # C16 forbidden strengthenings/weakenings coverage
    fs = " | ".join(as_list(concl.get("forbidden_strengthenings")))
    fw = " | ".join(as_list(concl.get("forbidden_weakenings")))
    needed = {
        "scc_inextendibility_as_strengthening": ("inextendibility" in fs and "SCC" in fs),
        "no_bh_formation": "black-hole region non-empty" in fs,
        "no_geodesic_completeness_M": "geodesic completeness of M" in fs,
        "no_all_data": "ALL data" in fs,
        "keep_I+_completeness": "dropping I+ completeness" in fs or "I+ completeness" in fw,
        "keep_generic_quantifier": "there exist data" in fw,
        "keep_no_visible_singularity": "no singularity" in fw,
    }
    missing_needed = [k for k, v in needed.items() if not v]
    ok = not missing_needed
    add("C16_FORBIDDEN_TRANSFERS", "conclusion registers the required forbidden strengthenings/weakenings (SCC content, BH formation, all-data, I+ completeness, visibility strength)",
        ok, f"missing={missing_needed}", [sre])

    # C17 honesty: open problem, promotion rule, unresolved items and citations declared
    prov = doc.get("provenance") or {}
    ok = (doc.get("epistemic_status") == "open_problem"
          and concl.get("epistemic_status") == "open_problem"
          and bool(doc.get("promotion_rule"))
          and bool(as_list(doc.get("unresolved_items")))
          and bool(as_list(prov.get("unresolved_citations")))
          and bool(prov.get("no_status_claim"))
          and bool(as_list(doc.get("l1_ledger_refs"))))
    add("C17_HONESTY_UNRESOLVED", "schema stays open_problem with a promotion rule, declares unresolved items/citations and makes no status claim",
        ok, f"status={doc.get('epistemic_status')} unresolved_items={len(as_list(doc.get('unresolved_items')))} unresolved_citations={len(as_list(prov.get('unresolved_citations')))} no_status_claim={bool(prov.get('no_status_claim'))}", [sre])

    # C18 review hygiene (no self-certified independent review)
    rs = doc.get("review_status") or {}
    ok = rs.get("verdict") == "pending" and not as_list(rs.get("independent_reviewers"))
    add("C18_REVIEW_HYGIENE", "schema does not self-certify an independent review (verdict pending, reviewer list empty)",
        ok, f"verdict={rs.get('verdict')} independent_reviewers={rs.get('independent_reviewers')}", [sre])

    # C19 duplicate YAML keys
    ok = not dup_keys and not tax_dups and not supp_dups
    add("C19_NO_DUPLICATE_KEYS", "no duplicate mapping keys in the schema, canonical taxonomy or supplement",
        ok, f"schema_dups={dup_keys} taxonomy_dups={tax_dups} supplement_dups={supp_dups}", [sre])

    # C20 canonical taxonomy stability at the G-F0-frozen bytes
    ok = measured[TAXONOMY_CANON] == EXPECTED_F0_SHA
    add("C20_F0_FROZEN_STABILITY", "canonical taxonomy still measures 0abb9ed8a961 (G-F0-frozen; not written by this review)",
        ok, f"measured={str(measured[TAXONOMY_CANON])[:12]}", [tre])

    # C21 FROZEN rev29 binding and self-consistency
    frozen = json.load(open(p(FROZEN), "r", encoding="utf-8")) if os.path.exists(p(FROZEN)) else {}
    pins = frozen.get("files") or {}
    mism = []
    for rel, meta in pins.items():
        fp = p(rel)
        if not os.path.exists(fp):
            mism.append((rel, "MISSING"))
        elif sha256_file(fp) != meta.get("sha256"):
            mism.append((rel, "HASH"))
    key_ok = all(pins.get(k, {}).get("sha256") == measured[k]
                 for k in (SCHEMA_CANON, SCHEMA_AUTHOR, TAXONOMY_CANON, TAXONOMY_SUPP, EVIDENCE))
    ok = (frozen.get("revision") == 29 and not mism and key_ok)
    add("C21_FROZEN_REV29_BINDING", "FROZEN revision 29 pins the reviewed schema bytes and every one of its file pins matches the live bytes",
        ok, f"frozen_revision={frozen.get('revision')} pin_count={len(pins)} mismatches={mism[:5]} key_pins_ok={key_ok}", [fre, sre])

    # C22 delta rev12 -> rev13 semantic scope
    delta = delta_check(root)
    add("C22_DELTA_REV12_REV13", "rev12 -> rev13 change set is exactly the carded strictness-direction repair + evidence-binding refresh",
        delta["status"] == "PASS",
        f"rev {delta['revision_before']} -> {delta['revision_after']}; changed={delta['changed_paths']}; unexpected={delta['unexpected_changed_paths']}",
        [f"{SCHEMA_CANON}#{str(delta['after_sha256'])[:12]}", f"{delta['before_path']}#{str(delta['before_sha256'])[:12]}"])

    # C23 order/scoping note: generic set chosen before data
    note = str(q.get("order_note", ""))
    ok = ("chosen before" in note and "may not depend on" in note)
    add("C23_QUANTIFIER_SCOPE_NOTE", "order_note fixes the comeager set before the data quantifier and forbids data-dependent G_r",
        ok, f"order_note={note[:90]!r}", [sre])

    # C24 SCC leakage scan on assertion sites
    leaks = {k: SCC_TOKEN_RE.search(v).group(0) for k, v in sites.items() if SCC_TOKEN_RE.search(v)}
    ok = not leaks
    add("C24_NO_SCC_LEAKAGE", "no SCC/inextendibility token in a specification slot (conclusion block, quantifiers, visibility, I+ definition)",
        ok, f"leaks={leaks}", [sre])

    fail = [c for c in checks if c["status"] == "FAIL"]
    return {
        "instrument": "check_f1.py",
        "instrument_version": "1.0.0",
        "task_id": "W072-F1-REVIEW-REV13-01",
        "worker": "worker-072",
        "generated_at": now(),
        "root": root,
        "measured_sha256": measured,
        "delta_rev12_rev13": delta,
        "checks": checks,
        "summary": {"PASS": sum(c["status"] == "PASS" for c in checks),
                    "FAIL": len(fail), "INFO": sum(c["status"] == "INFO" for c in checks),
                    "failed_ids": [c["id"] for c in fail]},
    }


def run_controls(root: str) -> dict:
    """Mutation controls: each mutation must trip its target check on a sandboxed copy."""
    src = os.path.join(root, SCHEMA_CANON)
    doc, _, text = parse_yaml(src)
    base = run_checks(root)
    base_status = {c["id"]: c["status"] for c in base["checks"]}
    controls = []
    sandbox = tempfile.mkdtemp(prefix="w072-f1-", dir=os.path.dirname(os.path.abspath(__file__)))
    copy_rels = (TAXONOMY_CANON, TAXONOMY_SUPP, EVIDENCE, FROZEN)

    def with_sandbox(mutation_text: str, name: str):
        d = os.path.join(sandbox, name)
        for rel in copy_rels:
            dst = os.path.join(d, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(os.path.join(root, rel), "rb") as f_in, open(dst, "wb") as f_out:
                f_out.write(f_in.read())
        for rel in (SCHEMA_CANON, SCHEMA_AUTHOR):
            dst = os.path.join(d, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "w", encoding="utf-8") as f:
                f.write(mutation_text)
        return d

    def run_one(name, target, mutation_text):
        d = with_sandbox(mutation_text, name)
        res = run_checks(d)
        st = {c["id"]: c["status"] for c in res["checks"]}
        return {"control": name, "target_check": target,
                "status": "PASS" if st.get(target) == "FAIL" else "FAIL",
                "detail": f"{target}={st.get(target)} failed_ids={res['summary']['failed_ids']}"}

    text_muts = [
        ("K1_class_id_swap", "C02_CLASS_ID_SINGULAR",
         lambda t: t.replace("class_id: AF-WCC-VAC-GEN", "class_id: AF-SCC-C2-VAC-GEN")),
        ("K2_conclusion_type_scc", "C04_CONCLUSION_TYPE_WCC",
         lambda t: t.replace("conclusion_type: weak_cosmic_censorship", "conclusion_type: strong_cosmic_censorship")),
        ("K9_scc_leak_in_statement", "C24_NO_SCC_LEAKAGE",
         lambda t: t.replace(
             'statement_formal: "forall r in D0 exists G_r comeager forall D in G_r: AF_{I+}(M_D) and complete(I+_D) and not exists visible_singularity_from_I_plus(M_D)"',
             'statement_formal: "forall r in D0 exists G_r comeager forall D in G_r: AF_{I+}(M_D) and complete(I+_D) and the development is future C2 inextendible"')),
    ]
    dict_muts = [
        ("K3_iplus_not_conclusion", "C05_IPLUS_VISIBILITY_IN_CONCLUSION",
         lambda d: d["i_plus"].__setitem__("in_conclusion", False)),
        ("K4_quantifier_order_reversed", "C06_QUANTIFIER_SHAPE",
         lambda d: d["quantifiers"]["ordered"].reverse()),
        ("K5_visibility_setbased", "C11_VISIBILITY_TAIL_PREDICATE",
         lambda d: d["visibility"].__setitem__("definition", "gamma is visible from I+ iff gamma is contained in the union of J^-(q) over all q in I+.")),
        ("K6_variant_strength_flipped", "C12_STRICTNESS_DIRECTION",
         lambda d: d["class_identity_variants"][0].__setitem__("relation", "strictly STRONGER than this class's single-q tail predicate")),
        ("K7_f0_hash_zeroed", "C13_F0_HASH_BINDING",
         lambda d: d["f0_binding"].__setitem__("declared_f0_sha256", "0" * 64)),
        ("K8_falsifier_removed", "C15_FALSIFIER",
         lambda d: d["falsifier"].pop("tier_1", None)),
        ("K10_excluded_set_resolved", "C09_GENERICITY",
         lambda d: d["genericity"].__setitem__("excluded_set_status", "resolved")),
    ]

    for name, target, mut in text_muts:
        mt = mut(text)
        if mt == text:
            controls.append({"control": name, "target_check": target, "status": "ERROR",
                             "detail": "mutation did not apply (anchor text not found)"})
            continue
        controls.append(run_one(name, target, mt))

    for name, target, mut in dict_muts:
        dm = copy.deepcopy(doc)
        mut(dm)
        controls.append(run_one(name, target, yaml.safe_dump(dm, sort_keys=False, allow_unicode=True)))

    # K11 duplicate key appended to raw text
    controls.append(run_one("K11_duplicate_key", "C19_NO_DUPLICATE_KEYS",
                            text + "\nclass_id: AF-SCC-C0-VAC-GEN\n"))

    # K12 clean re-dump determinism control (compare semantic checks; the byte-pin
    # checks C21/C22 must move when the schema bytes change and are excluded here)
    clean = yaml.safe_dump(copy.deepcopy(doc), sort_keys=False, allow_unicode=True)
    d = with_sandbox(clean, "K12_clean_redump")
    res = run_checks(d)
    st = {c["id"]: c["status"] for c in res["checks"]}
    byte_bound = {"C21_FROZEN_REV29_BINDING", "C22_DELTA_REV12_REV13"}
    same = all(st.get(cid) == base_status.get(cid) for cid in base_status if cid not in byte_bound)
    controls.append({"control": "K12_clean_redump_determinism", "target_check": "IDENTITY",
                     "status": "PASS" if same else "FAIL",
                     "detail": f"semantic_statuses_identical={same} (C21/C22 byte-bound excluded) failed_ids={res['summary']['failed_ids']}"})

    esc = [c for c in controls if c["status"] != "PASS"]
    return {"controls_dir": sandbox, "controls": controls,
            "summary": {"PASS": sum(c["status"] == "PASS" for c in controls),
                        "ESCAPED": len(esc), "escaped": [c["control"] for c in esc]}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    ap.add_argument("--json", default=None)
    ap.add_argument("--controls", action="store_true")
    args = ap.parse_args()
    out = run_checks(args.root)
    if args.controls:
        out["controls_run"] = run_controls(args.root)
    out["instrument_sha256"] = sha256_file(os.path.abspath(__file__))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1, sort_keys=False)
            f.write("\n")
    print(json.dumps(out["summary"], indent=1))
    if args.controls:
        print(json.dumps(out["controls_run"]["summary"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
