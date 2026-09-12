#!/usr/bin/env python3
"""W072-F2A-REVIEW-01 instrument: independent, from-scratch conformance checks for
schemas/af_scc_c2_vacuum.yaml (class AF-SCC-C2-VAC-GEN, node F2a, gate G-FORM).

Written by worker-072 without reading any other reviewer's verdict text for F2a.
It does not import research_map/class_separation.py, artifacts/formulation/tools/
check_class_schema.py, or artifacts/worker-06/spec_conformance_audit.py: every check
below is implemented here from the frozen G-FORM criteria in the map plus the
schema's own declared contract.

Design rules (learned from the CF-16 metalinguistic-mention findings):
  * Assertion sites only. Class-id tokens and composite-token checks scan the
    specification slots (scope_statement, quantifiers, conclusion statements,
    class_id). anti_scope / forbidden_* / must_not_conflate / implication_ledger
    are mention sites and are checked for the *required mention* instead.
  * Duplicate YAML keys are a hard defect (PyYAML keeps the last silently).
  * Every FAIL is bound to a measured sha256.

Usage:
  python3 check_f2a.py --json report.json [--root ROOT]
  python3 check_f2a.py --controls --json report.json [--root ROOT]
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
CLASS_ID = "AF-SCC-C2-VAC-GEN"
SIBLING_C0 = "AF-SCC-C0-VAC-GEN"
NODE_ID = "F2a"
EXPECTED_F0_SHA = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
REV12_PIN = "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce"
ALLOWED_DELTA_PATHS = {
    "revision", "revised_at", "revision_history",
    "f0_binding.consistency_evidence_sha256", "f0_binding.checked_at", "f0_binding.binding_note",
}

SCHEMA_CANON = "schemas/af_scc_c2_vacuum.yaml"
SCHEMA_AUTHOR = "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
TAXONOMY_CANON = "research_map/formulation_taxonomy.yaml"
TAXONOMY_SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
EVIDENCE = "artifacts/formulation/evidence/taxonomy_consistency.json"


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


def assertion_sites(doc: dict) -> dict:
    q = doc.get("quantifiers") or {}
    sites = {
        "class_id": doc.get("class_id"),
        "scope_statement": doc.get("scope_statement"),
        "quantifiers.formal": q.get("formal"),
        "quantifiers.negation": q.get("negation"),
        "quantifiers.negation_normal_form": q.get("negation_normal_form"),
        "conclusion.statement_natural_language": (doc.get("conclusion") or {}).get("statement_natural_language"),
        "conclusion.statement_formal": (doc.get("conclusion") or {}).get("statement_formal"),
    }
    for did, d in (q.get("domains") or {}).items():
        if isinstance(d, dict):
            sites[f"quantifiers.domains.{did}.definition"] = d.get("definition")
    return {k: v for k, v in sites.items() if isinstance(v, str)}


COMPOSITE_RE = re.compile(r"\bC\s*0\s*(?:or|/|,|&|\+)\s*C\s*2\b|\bC\s*2\s*(?:or|/|,|&|\+)\s*C\s*0\b", re.I)
CLASS_TOKEN_RE = re.compile(r"\bAF-[A-Z0-9]+(?:-[A-Z0-9]+)+\b")


def flat_diff(a, b, prefix="") -> list:
    """Return the dotted key paths whose scalar/list value differs between two docs."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            out += flat_diff(a.get(k), b.get(k), f"{prefix}{k}.")
    elif isinstance(a, list) and isinstance(b, list):
        if a != b:
            out.append(prefix.rstrip("."))
    elif a != b:
        out.append(prefix.rstrip("."))
    return out


def delta_check(root: str) -> dict:
    """Verify the rev12 -> rev13 change set is exactly the carded evidence-binding refresh."""
    before_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pins", "af_scc_c2_vacuum.rev12.yaml")
    before_sha = sha256_file(before_path) if os.path.exists(before_path) else None
    before, _, _ = parse_yaml(before_path)
    after, _, _ = parse_yaml(os.path.join(root, SCHEMA_CANON))
    after_sha = sha256_file(os.path.join(root, SCHEMA_CANON))
    changed = flat_diff(before, after)
    unexpected = [c for c in changed if c not in ALLOWED_DELTA_PATHS]
    f0b = after.get("f0_binding") or {}
    hist = as_list(after.get("revision_history"))
    last = hist[-1] if hist else {}
    note = str(last.get("notes", ""))
    ok = (before_sha == REV12_PIN and after_sha is not None and after_sha != REV12_PIN
          and not unexpected
          and after.get("revision") == before.get("revision", 0) + 1
          and f0b.get("declared_f0_sha256") == before.get("f0_binding", {}).get("declared_f0_sha256")
          and "rev13" in note and "9e335e9ba1bf" in note)
    return {
        "before_path": "artifacts/worker-072/f2a_review/pins/af_scc_c2_vacuum.rev12.yaml",
        "before_sha256": before_sha, "before_pin_ok": before_sha == REV12_PIN,
        "after_sha256": after_sha, "revision_before": before.get("revision"), "revision_after": after.get("revision"),
        "changed_paths": changed, "unexpected_changed_paths": unexpected,
        "declared_f0_unchanged": f0b.get("declared_f0_sha256") == before.get("f0_binding", {}).get("declared_f0_sha256"),
        "status": "PASS" if ok else "FAIL",
    }


def run_checks(root: str) -> dict:
    p = lambda rel: os.path.join(root, rel)
    measured = {}
    for rel in (SCHEMA_CANON, SCHEMA_AUTHOR, TAXONOMY_CANON, TAXONOMY_SUPP, EVIDENCE):
        measured[rel] = sha256_file(p(rel)) if os.path.exists(p(rel)) else None

    doc, dup_keys, _ = parse_yaml(p(SCHEMA_CANON))
    taxonomy, tax_dups, _ = parse_yaml(p(TAXONOMY_CANON))
    supp, supp_dups, _ = parse_yaml(p(TAXONOMY_SUPP))
    evidence = json.load(open(p(EVIDENCE), "r", encoding="utf-8"))

    checks = []

    def add(cid, desc, ok, detail, ev):
        checks.append({"id": cid, "description": desc, "status": "PASS" if ok else "FAIL",
                       "detail": detail, "evidence": ev})

    sre = f"{SCHEMA_CANON}#{(measured[SCHEMA_CANON] or '?')[:12]}"
    tre = f"{TAXONOMY_CANON}#{(measured[TAXONOMY_CANON] or '?')[:12]}"

    # C01 mirror pair published byte-identically
    ok = measured[SCHEMA_CANON] is not None and measured[SCHEMA_CANON] == measured[SCHEMA_AUTHOR]
    add("C01_MIRROR_PAIR", "canonical and authoring copies are byte-identical (mirror pair)",
        ok, f"canon={measured[SCHEMA_CANON]} author={measured[SCHEMA_AUTHOR]}", [sre])

    # C02 singular class id / node id
    sites = assertion_sites(doc)
    found_tokens = sorted({m for s in sites.values() for m in CLASS_TOKEN_RE.findall(s)})
    ok = (doc.get("class_id") == CLASS_ID and doc.get("node_id") == NODE_ID
          and found_tokens == [CLASS_ID])
    add("C02_CLASS_ID_SINGULAR", "class_id/node_id match the class and no other class-id token occurs in specification slots",
        ok, f"class_id={doc.get('class_id')} node_id={doc.get('node_id')} assertion_tokens={found_tokens}",
        [sre])

    # C03 no composite regularity; sibling registered in anti_scope
    comp = {k: COMPOSITE_RE.search(v).group(0) for k, v in sites.items() if COMPOSITE_RE.search(v)}
    anti = [x.get("class_id") for x in as_list((doc.get("anti_scope") or {}).get("not_this_class")) if isinstance(x, dict)]
    phrases = " | ".join((doc.get("anti_scope") or {}).get("phrases_that_are_not_this_class") or [])
    ok = (not comp) and (SIBLING_C0 in anti) and ("C0 or C2" in phrases)
    add("C03_NO_COMPOSITE_REGULARITY", "no C0/C2 composite in a specification slot; sibling C0 class and the composite phrase are registered as not-this-class",
        ok, f"composite_hits={comp} anti_scope_class_ids={anti} composite_phrase_registered={'C0 or C2' in phrases}", [sre])

    # C04 conclusion type / family / no WCC content
    concl = doc.get("conclusion") or {}
    ctext = " ".join(str(concl.get(k, "")) for k in ("statement_natural_language", "statement_formal", "conclusion_type"))
    bad = [t for t in ("I+", "visibility", "WCC", "predictab") if t.lower() in ctext.lower()]
    ok = (concl.get("conclusion_type") == "scc_c2_future_inextendibility"
          and concl.get("family") == "SCC" and not bad)
    add("C04_CONCLUSION_TYPE", "conclusion_type is the frozen SCC/C2 token, family SCC, and the conclusion text carries no WCC/I+/visibility content",
        ok, f"type={concl.get('conclusion_type')} family={concl.get('family')} wcc_tokens={bad}", [sre])

    # C05 I+ and visibility roles
    ip = doc.get("i_plus") or {}
    vis = doc.get("visibility") or {}
    ok = (ip.get("role") == "assumption" and ip.get("in_conclusion") is False
          and ip.get("completeness_in_conclusion") is False
          and vis.get("role") == "not_in_conclusion")
    add("C05_WCC_NOT_CONCLUDED", "I+ is an assumption only and visibility is not in the conclusion",
        ok, f"i_plus.role={ip.get('role')} in_conclusion={ip.get('in_conclusion')} completeness_in_conclusion={ip.get('completeness_in_conclusion')} visibility.role={vis.get('role')}",
        [sre])

    # C06 quantifier shape/order
    q = doc.get("quantifiers") or {}
    ordered = as_list(q.get("ordered"))
    got = [(str(e.get("kind")), str(e.get("binder")), str(e.get("domain_id"))) for e in ordered if isinstance(e, dict)]
    want = [("forall", "r", "D0"), ("exists", "G_r", "D1"), ("forall", "(Sigma,h,K)", "D2"),
            ("not_exists", "(M',g',iota)", "D3")]
    ok = (got == want and q.get("order_matters") is True
          and bool(q.get("negation")) and bool(q.get("negation_normal_form"))
          and "forall-exists(comeager)-forall-not-exists" in str(q.get("quantifier_class")))
    add("C06_QUANTIFIER_SHAPE", "ordered quantifier chain, order_matters=true, negation normal form and quantifier class string present",
        ok, f"ordered={got}", [sre])

    # C07 domains resolve
    domains = q.get("domains") or {}
    missing, unresolved = [], []
    for did in ("D0", "D1", "D2", "D3"):
        d = domains.get(did)
        if not isinstance(d, dict) or not d.get("definition"):
            missing.append(did)
            continue
        ref = str(d.get("definition_ref", ""))
        _, found = resolve(doc, ref)
        if not found:
            unresolved.append(f"{did}:{ref}")
    ok = not missing and not unresolved
    add("C07_DOMAINS_RESOLVE", "D0-D3 each carry a definition whose definition_ref resolves inside the document",
        ok, f"missing={missing} unresolved_refs={unresolved}", [sre])

    # C08 topology
    topo = doc.get("topology") or {}
    ok = (str(topo.get("spacetime_dimension")) == "4"
          and "R^3" in str(topo.get("slice_topology")) and "one AF end" in str(topo.get("slice_topology")) + str(topo.get("end_structure"))
          and "R x S^2" in str(topo.get("I_plus_topology"))
          and bool(as_list(topo.get("forbidden"))) and bool(topo.get("extension_topology")))
    add("C08_TOPOLOGY", "4D, one-ended AF slice R^3, I+ topology R x S^2, forbidden list nonempty, extension topology declared",
        ok, f"dim={topo.get('spacetime_dimension')} end={topo.get('end_structure')} I+={topo.get('I_plus_topology')} forbidden_n={len(as_list(topo.get('forbidden')))}",
        [sre])

    # C09 genericity
    gen = doc.get("genericity") or {}
    variants = as_list(gen.get("variants"))
    bad_variants = [v.get("kind") for v in variants if isinstance(v, dict) and v.get("is_this_class") is not False]
    ok = (gen.get("kind") == "residual_comeager"
          and "X^r_vac(AF)" in str(gen.get("ambient_space"))
          and bool(gen.get("class_change_warning"))
          and not bad_variants
          and bool(as_list(gen.get("transfer_failures"))) and bool(as_list(gen.get("transfer_holds"))))
    add("C09_GENERICITY", "residual/comeager genericity on X^r_vac(AF) with class-change warning and no variant claiming to be this class",
        ok, f"kind={gen.get('kind')} self_claiming_variants={bad_variants} warnings={bool(gen.get('class_change_warning'))}",
        [sre])

    # C10 extension predicate
    ext = doc.get("extension_predicate") or {}
    definition = str(ext.get("definition", ""))
    clauses = [c for c in ("(a)", "(b)", "(c)", "(d)", "(e)", "(f)") if c in definition]
    ok = (ext.get("frozen_regularity") == "C2" and ext.get("frozen_equation_concept") == "classical_ricci"
          and ext.get("frozen_direction") == "future" and len(clauses) == 6)
    add("C10_EXTENSION_PREDICATE", "frozen C2 / classical_ricci / future predicate with clauses (a)-(f)",
        ok, f"regularity={ext.get('frozen_regularity')} equation={ext.get('frozen_equation_concept')} direction={ext.get('frozen_direction')} clauses={clauses}",
        [sre])

    # C11 F0 hash binding
    f0 = doc.get("f0_binding") or {}
    ok = (str(f0.get("declared_f0_sha256")) == EXPECTED_F0_SHA
          and measured[TAXONOMY_CANON] == EXPECTED_F0_SHA
          and os.path.exists(p(str(f0.get("declared_f0_artifact", "")))))
    add("C11_F0_HASH_BINDING", "declared F0 sha256 equals the measured canonical taxonomy hash (the G-F0-frozen artifact)",
        ok, f"declared={str(f0.get('declared_f0_sha256'))[:12]} measured={(measured[TAXONOMY_CANON] or '?')[:12]}",
        [sre, tre])

    # C12 contract pointers resolve
    ptr = str(doc.get("class_contract_pointer", ""))
    sptr = str(doc.get("class_contract_supplement_pointer", ""))
    canonical_ok = CLASS_ID in (taxonomy.get("classes") or {})
    supplement_ok = CLASS_ID in (((supp or {}).get("class_contracts")) or {})
    ok = ptr.startswith(TAXONOMY_CANON + "#classes.") and sptr.startswith(TAXONOMY_SUPP + "#class_contracts.") \
        and canonical_ok and supplement_ok
    add("C12_CONTRACT_POINTERS", "canonical and supplement pointers resolve to this class in their respective trees",
        ok, f"canonical_resolves={canonical_ok} supplement_resolves={supplement_ok} ptr={ptr}",
        [sre, tre, f"{TAXONOMY_SUPP}#{(measured[TAXONOMY_SUPP] or '?')[:12]}"])

    # C13 consistency evidence binding (the field the pass-05 repair must refresh)
    declared_ev = str(f0.get("consistency_evidence_sha256"))
    ok = declared_ev == measured[EVIDENCE]
    add("C13_CONSISTENCY_EVIDENCE_BINDING", "declared consistency_evidence_sha256 equals the measured on-disk consistency evidence hash",
        ok, f"declared={declared_ev[:12]} measured={(measured[EVIDENCE] or '?')[:12]}",
        [sre, f"{EVIDENCE}#{(measured[EVIDENCE] or '?')[:12]}"])

    # C14 falsifier completeness
    fal = doc.get("falsifier") or {}
    t1 = fal.get("tier_1") or {}
    t2 = fal.get("tier_2") or {}
    ok = (t1.get("refutes") == CLASS_ID and bool(t1.get("genericity_requirement"))
          and bool(as_list(t1.get("proof_obligations"))) and bool(as_list(t1.get("machine_checkable_steps")))
          and t2.get("refutes") == "only the strictly stronger class 'forall AF vacuum data'"
          and bool(as_list(fal.get("schema_falsifiers"))))
    add("C14_FALSIFIER", "tier-1 falsifier names the class and its genericity route; tier-2 is labelled as refuting only the strengthening",
        ok, f"tier1_refutes={t1.get('refutes')} genericity_requirement={bool(t1.get('genericity_requirement'))} tier2={str(t2.get('refutes'))[:40]}",
        [sre])

    # C15 forbidden strengthenings/weakenings coverage
    fs = " | ".join(as_list(concl.get("forbidden_strengthenings")))
    fw = " | ".join(as_list(concl.get("forbidden_weakenings")))
    needed = {
        "C0_or_C1_or_H2loc": ("C0" in fs and "H2_loc" in fs),
        "two_sided": "two-sided" in fs,
        "all_data": "for ALL AF vacuum data" in fs,
        "global_hyperbolicity_of_extension": "global hyperbolicity" in fs,
        "I+_completeness/WCC": ("I+ completeness" in fs or "asymptotic predictability" in fs),
        "weak_extension_ric": ("Ric = 0" in fw or "satisfy Ric" in fw),
        "drop_generic": "generic" in fw,
    }
    missing_needed = [k for k, v in needed.items() if not v]
    ok = not missing_needed
    add("C15_FORBIDDEN_TRANSFERS", "conclusion registers the required forbidden strengthenings/weakenings",
        ok, f"missing={missing_needed}", [sre])

    # C16 implication direction
    ledger = doc.get("implication_ledger") or {}
    entails = [e for e in as_list(ledger.get("one_way_entailments")) if isinstance(e, dict)]
    ent_c0 = any(e.get("from") == "no proper future C0 extension" and "C2" in str(e.get("to")) for e in entails)
    forb = [e for e in as_list(ledger.get("forbidden_transfers")) if isinstance(e, dict)]
    forb_rev = any(str(e.get("from")) == "no proper future C2 extension" and "C0" in str(e.get("to")) for e in forb)
    cb = str((doc.get("class_boundary") or {}).get("one_way_implication", ""))
    ok = ent_c0 and forb_rev and ("E(C0) entails E(C2)" in cb) and ("converse is forbidden" in cb) \
        and ("no WCC <-> SCC transfer" in str(ledger.get("cross_family")))
    add("C16_IMPLICATION_DIRECTION", "one-way C0=>C2 entailment with the converse forbidden and no WCC-SCC transfer licensed",
        ok, f"c0_entails_c2={ent_c0} converse_forbidden={forb_rev} boundary_text={bool(cb)}", [sre])

    # C17 review hygiene (no self-certified independent review)
    rs = doc.get("review_status") or {}
    ok = rs.get("verdict") == "pending" and not as_list(rs.get("independent_reviewers"))
    add("C17_REVIEW_HYGIENE", "schema does not self-certify an independent review (verdict pending, reviewer list empty)",
        ok, f"verdict={rs.get('verdict')} independent_reviewers={rs.get('independent_reviewers')}", [sre])

    # C18 duplicate YAML keys
    ok = not dup_keys and not tax_dups and not supp_dups
    add("C18_NO_DUPLICATE_KEYS", "no duplicate mapping keys in the schema, canonical taxonomy or supplement",
        ok, f"schema_dups={dup_keys} taxonomy_dups={tax_dups} supplement_dups={supp_dups}", [sre])

    # C19 canonical taxonomy stability at the G-F0-frozen bytes
    ok = measured[TAXONOMY_CANON] == EXPECTED_F0_SHA
    add("C19_F0_FROZEN_STABILITY", "canonical taxonomy still measures 0abb9ed8a961 (G-F0-frozen; not written by this review)",
        ok, f"measured={(measured[TAXONOMY_CANON] or '?')[:12]}", [tre])

    # C20 evidence document shape (recorded, not a gate criterion)
    has_pins = bool(re.search(r"[0-9a-f]{12,}", json.dumps(evidence)))
    shas = re.findall(r"[0-9a-f]{64}", json.dumps(evidence))
    cons = evidence.get("consistent", evidence.get("result"))
    checks.append({"id": "C20_EVIDENCE_DOC_SHAPE", "description": "recorded: live consistency evidence carries the compared-tree hashes and a comparator timestamp",
                   "status": "INFO" if not (shas and has_pins) else "PASS",
                   "detail": f"consistent_flag={cons} sha256_tokens={len(shas)} pin_tokens={has_pins}",
                   "evidence": [f"{EVIDENCE}#{(measured[EVIDENCE] or '?')[:12]}"]})

    fail = [c for c in checks if c["status"] == "FAIL"]
    delta = delta_check(root)
    checks.append({
        "id": "C21_DELTA_SEMANTIC_INVARIANCE",
        "description": "rev12 -> rev13 change set is exactly the carded evidence-binding refresh; no class-semantics path moved",
        "status": delta["status"],
        "detail": f"rev {delta['revision_before']} -> {delta['revision_after']}; changed={delta['changed_paths']}; unexpected={delta['unexpected_changed_paths']}",
        "evidence": [f"{SCHEMA_CANON}#{(delta['after_sha256'] or '?')[:12]}",
                     f"{delta['before_path']}#{(delta['before_sha256'] or '?')[:12]}"],
    })
    fail = [c for c in checks if c["status"] == "FAIL"]
    return {
        "instrument": "check_f2a.py",
        "instrument_version": "1.0.0",
        "task_id": "W072-F2A-REVIEW-01",
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
    sandbox = tempfile.mkdtemp(prefix="w072-f2a-", dir=os.path.dirname(os.path.abspath(__file__)))

    def with_sandbox(mutation_text: str, name: str):
        d = os.path.join(sandbox, name)
        for rel in (TAXONOMY_CANON, TAXONOMY_SUPP, EVIDENCE):
            dst = os.path.join(d, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(os.path.join(root, rel), "rb") as f_in, open(dst, "wb") as f_out:
                f_out.write(f_in.read())
        # keep the published mirror pair consistent inside the sandbox
        for rel in (SCHEMA_CANON, SCHEMA_AUTHOR):
            dst = os.path.join(d, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "w", encoding="utf-8") as f:
                f.write(mutation_text)
        return d

    muts = [
        ("K1_composite_regularity", "C03_NO_COMPOSITE_REGULARITY",
         lambda t: t.replace(
             'statement_natural_language: "Generic asymptotically flat vacuum initial data have a maximal development that is future-inextendible as a C2 vacuum solution."',
             'statement_natural_language: "Generic data are future-inextendible as a C0 or C2 vacuum solution."')),
        ("K2_conclusion_type_c0", "C04_CONCLUSION_TYPE",
         lambda t: t.replace("conclusion_type: scc_c2_future_inextendibility",
                             "conclusion_type: scc_c0_future_inextendibility")),
    ]
    # dict-level mutations, re-dumped
    dict_muts = [
        ("K3_f0_hash_mismatch", "C11_F0_HASH_BINDING",
         lambda d: d["f0_binding"].__setitem__("declared_f0_sha256", "0" * 64)),
        ("K4_variant_claims_class", "C09_GENERICITY",
         lambda d: d["genericity"]["variants"][0].__setitem__("is_this_class", True)),
        ("K5_iplus_in_conclusion", "C05_WCC_NOT_CONCLUDED",
         lambda d: d["i_plus"].__setitem__("in_conclusion", True)),
        ("K6_quantifier_order_reversed", "C06_QUANTIFIER_SHAPE",
         lambda d: d["quantifiers"]["ordered"].reverse()),
        ("K7_falsifier_removed", "C14_FALSIFIER",
         lambda d: d["falsifier"].pop("tier_1", None)),
    ]

    for name, target, mut in muts:
        mt = mut(text)
        if mt == text:
            controls.append({"control": name, "target_check": target, "status": "ERROR",
                             "detail": "mutation did not apply (anchor text not found)"})
            continue
        d = with_sandbox(mt, name)
        res = run_checks(d)
        st = {c["id"]: c["status"] for c in res["checks"]}
        controls.append({"control": name, "target_check": target,
                         "status": "PASS" if st.get(target) == "FAIL" else "FAIL",
                         "detail": f"{target}={st.get(target)} failed_ids={res['summary']['failed_ids']}"})

    for name, target, mut in dict_muts:
        dm = copy.deepcopy(doc)
        mut(dm)
        mt = yaml.safe_dump(dm, sort_keys=False, allow_unicode=True)
        d = with_sandbox(mt, name)
        res = run_checks(d)
        st = {c["id"]: c["status"] for c in res["checks"]}
        controls.append({"control": name, "target_check": target,
                         "status": "PASS" if st.get(target) == "FAIL" else "FAIL",
                         "detail": f"{target}={st.get(target)} failed_ids={res['summary']['failed_ids']}"})

    # K8 duplicate key appended to raw text
    dup_text = text + "\nclass_id: AF-SCC-C0-VAC-GEN\n"
    d = with_sandbox(dup_text, "K8_duplicate_key")
    res = run_checks(d)
    st = {c["id"]: c["status"] for c in res["checks"]}
    controls.append({"control": "K8_duplicate_key", "target_check": "C18_NO_DUPLICATE_KEYS",
                     "status": "PASS" if st.get("C18_NO_DUPLICATE_KEYS") == "FAIL" else "FAIL",
                     "detail": f"C18={st.get('C18_NO_DUPLICATE_KEYS')} failed_ids={res['summary']['failed_ids']}"})

    # K9 clean re-dump determinism control
    clean = yaml.safe_dump(copy.deepcopy(doc), sort_keys=False, allow_unicode=True)
    d = with_sandbox(clean, "K9_clean_redump")
    res = run_checks(d)
    st = {c["id"]: c["status"] for c in res["checks"]}
    same = all(st.get(cid) == base_status.get(cid) for cid in base_status)
    controls.append({"control": "K9_clean_redump_determinism", "target_check": "IDENTITY",
                     "status": "PASS" if same else "FAIL",
                     "detail": f"statuses_identical={same} failed_ids={res['summary']['failed_ids']}"})

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
