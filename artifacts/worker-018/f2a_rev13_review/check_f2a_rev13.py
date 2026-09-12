#!/usr/bin/env python3
"""
worker-018 independent F2a (AF-SCC-C2-VAC-GEN) review harness, run W018-R13-F2A-REVIEW-01.

Read-only, deterministic, no network, no model calls. Reviews the frozen canonical
artifacts/formulation/schemas/af_scc_c2_vacuum.yaml at FROZEN rev29 (815e08079aef).

Adversarial task (from the inbox cards): try to prove the C2 schema is the C0 schema /
that C0 conclusion content is imported; check the one-way C0=>C2 entailment, the
extension-set containment chain, quantifier/topology completeness, and the falsifier.

Every check is keyed to the frozen rule_spec (artifacts/formulation/rule_spec.json
#40f9bb9e657b, rules R01-R16) or to a named primary byte. Exit 0 = all HARD checks pass.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
CANON = ROOT / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
ALIAS = ROOT / "schemas/af_scc_c2_vacuum.yaml"
SIB_CANON = ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
SIB_ALIAS = ROOT / "schemas/af_scc_c0_vacuum.yaml"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
RULE_SPEC = ROOT / "artifacts/formulation/rule_spec.json"
REGISTRY = ROOT / "artifacts/formulation/VARIANT_REGISTRY.json"
TAXONOMY = ROOT / "research_map/formulation_taxonomy.yaml"
SUPPLEMENT = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
CONSISTENCY = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"

TARGET_SHA = "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"
SIB_SHA = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
FROZEN_SHA = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
RULE_SPEC_SHA = "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e"
REGISTRY_SHA = "6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb"
TAXONOMY_SHA = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
CONSISTENCY_SHA = "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"
CLASS_ID = "AF-SCC-C2-VAC-GEN"
SIB_CLASS_ID = "AF-SCC-C0-VAC-GEN"
FROZEN_REV = 29
ARTIFACT_REV = 13

RESULTS = []


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def rec(cid, name, status, detail, rule=None):
    """status in PASS|FAIL|WARN"""
    RESULTS.append({"id": cid, "name": name, "status": status, "rule": rule, "detail": detail})


def get(d, dotted):
    cur = d
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def ptr_resolve(pointer, base_dir=ROOT):
    """pointer format path#a.b.c ; returns (path, key_path, value, exists)"""
    path_s, _, key = pointer.partition("#")
    p = base_dir / path_s
    if not p.exists():
        return path_s, key, None, False
    doc = yaml.safe_load(p.read_text())
    cur = doc
    for part in key.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return path_s, key, None, False
    return path_s, key, cur, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).with_name("results.json")))
    args = ap.parse_args()

    pre = {str(p): sha256(p) for p in (CANON, ALIAS, SIB_CANON, SIB_ALIAS, FROZEN, RULE_SPEC, REGISTRY, TAXONOMY, SUPPLEMENT, CONSISTENCY)}

    raw = CANON.read_text()
    doc = yaml.safe_load(raw)
    sib_raw = SIB_CANON.read_text()
    sib = yaml.safe_load(sib_raw)
    frozen = json.loads(FROZEN.read_text())
    spec = json.loads(RULE_SPEC.read_text())
    registry = json.loads(REGISTRY.read_text())
    consistency = json.loads(CONSISTENCY.read_text())
    taxonomy = yaml.safe_load(TAXONOMY.read_text())

    # C01 target identity: canonical bytes, alias identity, frozen target hash
    if pre[str(CANON)] == TARGET_SHA and pre[str(ALIAS)] == TARGET_SHA:
        rec("F2A-C01", "target identity", "PASS",
            f"canonical and alias both sha256 {TARGET_SHA[:12]} (bytes {CANON.stat().st_size})")
    else:
        rec("F2A-C01", "target identity", "FAIL",
            f"canonical={pre[str(CANON)][:12]} alias={pre[str(ALIAS)][:12]} expected {TARGET_SHA[:12]}")

    # C02 FROZEN rev29 per-file pin
    pins = frozen.get("files", {})
    pin = pins.get("artifacts/formulation/schemas/af_scc_c2_vacuum.yaml", {})
    alias_pin = pins.get("schemas/af_scc_c2_vacuum.yaml", {})
    if (frozen.get("revision") == FROZEN_REV and pre[str(FROZEN)] == FROZEN_SHA
            and pin.get("sha256") == TARGET_SHA and alias_pin.get("sha256") == TARGET_SHA):
        rec("F2A-C02", "FROZEN rev29 pins this exact hash", "PASS",
            f"FROZEN.json rev{frozen.get('revision')} sha256 {FROZEN_SHA[:12]} frozen_at={frozen.get('frozen_at')} pins target + alias")
    else:
        rec("F2A-C02", "FROZEN rev29 pins this exact hash", "FAIL",
            f"frozen_rev={frozen.get('revision')} frozen_sha={pre[str(FROZEN)][:12]} pin={pin.get('sha256','')[:12]}")

    # C03 identity block (R01) + class-component reconstruction (R02)
    comp = doc.get("class_components", {})
    if comp.get("censorship") == "SCC":
        rebuilt = f"{comp.get('asymptotics')}-{comp.get('censorship')}-{comp.get('regularity_token')}-{comp.get('matter')}-{comp.get('genericity')}"
    else:
        rebuilt = f"{comp.get('asymptotics')}-{comp.get('censorship')}-{comp.get('matter')}-{comp.get('genericity')}"
    ok03 = (doc.get("schema_version") == "1.0" and doc.get("artifact_kind") == "class_schema"
            and doc.get("class_id") == CLASS_ID and doc.get("node_id") == "F2a"
            and doc.get("owner") == "lead-formulation" and doc.get("epistemic_status") == "open_problem"
            and rebuilt == CLASS_ID and comp.get("regularity_token") == "C2")
    rec("F2A-C03", "identity block and token-wise class decomposition", "PASS" if ok03 else "FAIL",
        f"class_id={doc.get('class_id')} node_id={doc.get('node_id')} rebuilt={rebuilt} token={comp.get('regularity_token')}", "R01/R02")

    # C04 conclusion type == vocabulary, xor C0, xor WCC (R11 + class separation)
    want = spec.get("vocabularies", {}).get("class_conclusion_type", {}).get(CLASS_ID)
    ct = get(doc, "conclusion.conclusion_type")
    c0_ct = get(sib, "conclusion.conclusion_type")
    c0_in_f2a = "scc_c0_future_inextendibility" in raw
    wcc_in_concl = "weak_cosmic_censorship" in json.dumps(doc.get("conclusion", {}))
    ok04 = ct == want and ct != c0_ct and not c0_in_f2a and not wcc_in_concl
    rec("F2A-C04", "conclusion type matches vocab, distinct from C0 and WCC", "PASS" if ok04 else "FAIL",
        f"F2a={ct} want={want} F2b={c0_ct} 'scc_c0_future_inextendibility' in F2a bytes={c0_in_f2a} WCC token in conclusion={wcc_in_concl}", "R11")

    # C05 quantifier formal sentence uses the ordered binders (R03)
    q = doc.get("quantifiers", {})
    ordered = q.get("ordered", [])
    kinds = [b.get("kind") for b in ordered]
    formal = q.get("formal", "")
    dom_ids = {b.get("domain_id") for b in ordered}
    ok05 = (kinds == ["forall", "exists", "forall", "not_exists"]
            and "forall r in D0" in formal and "exists G_r" in formal
            and "forall (Sigma,h,K) in G_r" in formal and "not exists a proper future C2 vacuum extension" in formal
            and dom_ids <= set(q.get("domains", {})))
    rec("F2A-C05", "quantifier order and formal sentence agree", "PASS" if ok05 else "FAIL",
        f"kinds={kinds} ordered_count={len(ordered)} all domain_id resolve={dom_ids <= set(q.get('domains', {}))}", "R03")

    # C06 domains non-vague and typed; D0 excludes 'suitable regularity'
    doms = q.get("domains", {})
    d0 = doms.get("D0", {})
    vague = re.compile(r"\bsuitable\b|\bappropriate\b|\breasonable\b", re.I)
    vague_hits = []
    for k, v in doms.items():
        text = " ".join(str(x) for x in v.values()) if isinstance(v, dict) else str(v)
        if vague.search(text) and not re.search(r"not range over|no longer|does not range", text):
            vague_hits.append(k)
        if isinstance(v, dict) and v.get("definition_ref"):
            ref = ptr_resolve("artifacts/formulation/schemas/af_scc_c2_vacuum.yaml#" + str(v["definition_ref"]))
            if not ref[3]:
                vague_hits.append(k + ":unresolved_ref")
    ok06 = len(doms) >= 4 and not vague_hits and "tagged disjoint union" in d0.get("definition", "")
    rec("F2A-C06", "quantifier domains typed, non-vague, refs resolve", "PASS" if ok06 else "FAIL",
        f"domains={list(doms)} unresolved_or_vague={vague_hits}", "R03")

    # C07 topology (R04)
    t = doc.get("topology", {})
    forb = " ".join(t.get("forbidden", [])).lower()
    ok07 = (t.get("spacetime_dimension") == 4 and "R^3" in t.get("slice_topology", "")
            and "one" in t.get("end_structure", "").lower() and t.get("completeness_of_slice") is True
            and t.get("I_plus_topology") == "R x S^2" and "closed or periodic" in forb
            and set(t.get("conformal_boundary", [])) >= {"I+ (future null infinity)", "I- (past null infinity)", "i0 (spatial infinity)"})
    rec("F2A-C07", "topology complete, closed/periodic forbidden", "PASS" if ok07 else "FAIL",
        f"dim={t.get('spacetime_dimension')} I+={t.get('I_plus_topology')} boundary={len(t.get('conformal_boundary', []))} forbidden={len(t.get('forbidden', []))}", "R04")

    # C08 data class (R05)
    dc = doc.get("data_class", {})
    dec = dc.get("asymptotic_decay", {})
    ok08 = (dc.get("matter") == "none" and dc.get("cosmological_constant") == 0
            and "Ric(g) = 0" in dc.get("equations", "")
            and set(dc.get("constraints", {})) == {"hamiltonian", "momentum"}
            and re.search(r"r\^\{-1\}", dec.get("metric", "")) and re.search(r"r\^\{-2\}", dec.get("second_fundamental_form", ""))
            and dc.get("adm_mass", {}).get("exists") is True
            and "s > 5/2" in str(get(dc, "regularity_class.sobolev_variant.s")))
    rec("F2A-C08", "data class constraints, numeric decay, ADM mass, Sobolev indices", "PASS" if ok08 else "FAIL",
        f"matter={dc.get('matter')} Lambda={dc.get('cosmological_constant')} constraints={list(dc.get('constraints', {}))} adm_exists={get(dc,'adm_mass.exists')} s={get(dc,'regularity_class.sobolev_variant.s')}", "R05")

    # C09 regularity slots separated, extension token C2, concept declared (R06)
    reg = doc.get("regularity", {})
    slots = ["data_regularity", "solution_regularity", "i_plus_regularity", "extension_regularity", "extension_solution_concept"]
    ok09 = (all(s in reg for s in slots) and reg.get("extension_regularity") == "C2"
            and reg.get("extension_solution_concept") == "classical_ricci"
            and isinstance(reg.get("must_not_conflate"), list) and len(reg["must_not_conflate"]) > 0
            and "C0" in reg.get("extension_regularity_exact", ""))
    rec("F2A-C09", "regularity slots separated; extension token exactly C2", "PASS" if ok09 else "FAIL",
        f"slots_present={[s for s in slots if s in reg]} extension={reg.get('extension_regularity')} concept={reg.get('extension_solution_concept')} mnc={len(reg.get('must_not_conflate', []))}", "R06")

    # C10 genericity (R07)
    g = doc.get("genericity", {})
    ok10 = (g.get("kind") == "residual_comeager" and bool(g.get("ambient_space"))
            and bool(g.get("topology_or_measure")) and bool(g.get("generic_set"))
            and g.get("excluded_set") is not None and len(g.get("transfer_failures", [])) >= 1
            and g.get("is_part_of_class") is True and bool(g.get("class_change_warning")))
    rec("F2A-C10", "genericity typed, transfer failures non-empty, part of class identity", "PASS" if ok10 else "FAIL",
        f"kind={g.get('kind')} transfer_failures={len(g.get('transfer_failures', []))} is_part_of_class={g.get('is_part_of_class')}", "R07")

    # C11 non-vacuity (R08)
    nv = doc.get("non_vacuity", {})
    ok11 = bool(nv.get("condition")) and bool(nv.get("witness_type")) and bool(nv.get("vacuity_falsifier"))
    rec("F2A-C11", "non-vacuity condition, witness type and falsifier declared", "PASS" if ok11 else "FAIL",
        f"witness={str(nv.get('witness_type'))[:60]}... status={nv.get('status','')[:60]}", "R08")

    # C12 I+ role for SCC family (R09)
    ip = doc.get("i_plus", {})
    ok12 = (ip.get("role") == "assumption" and ip.get("in_conclusion") is False
            and ip.get("completeness_in_conclusion") is False
            and "forbidden" in ip and len(ip["forbidden"]) >= 1)
    rec("F2A-C12", "I+ is an assumption, not in conclusion (SCC)", "PASS" if ok12 else "FAIL",
        f"role={ip.get('role')} in_conclusion={ip.get('in_conclusion')} completeness_in_conclusion={ip.get('completeness_in_conclusion')}", "R09")

    # C13 visibility role (R10)
    vis = doc.get("visibility", {})
    ok13 = (vis.get("role") == "not_in_conclusion" and bool(vis.get("reason"))
            and vis.get("visible_singularity_is_wcc") is True and "visible" in vis.get("forbidden_falsifier", ""))
    rec("F2A-C13", "visibility not in conclusion; visible singularity assigned to WCC", "PASS" if ok13 else "FAIL",
        f"role={vis.get('role')} visible_is_wcc={vis.get('visible_singularity_is_wcc')}", "R10")

    # C14 falsifier tiering (R14)
    f = doc.get("falsifier", {})
    t1, t2 = f.get("tier_1", {}), f.get("tier_2", {})
    ok14 = (t1.get("refutes") == CLASS_ID and "non-meager" in t1.get("genericity_requirement", "")
            and bool(t1.get("witness_type")) and len(t1.get("machine_checkable_steps", [])) >= 1
            and t2.get("refutes") != CLASS_ID and t2.get("labelling_required") == "refutes_strengthening_only"
            and "extension" in t1.get("witness_type", ""))
    rec("F2A-C14", "tier_1 refutes the class with genericity; tier_2 labelled strengthening-only", "PASS" if ok14 else "FAIL",
        f"t1_refutes={t1.get('refutes')} t2_refutes={t2.get('refutes')} t2_label={t2.get('labelling_required')} steps={len(t1.get('machine_checkable_steps', []))}", "R14")

    # C15 R12 leakage scan over the four frozen scan blocks, denial-tagged mentions allowed
    denial = re.compile(r"not\b|never|forbidden|wrong|must not|no transfer|does not|is not", re.I)
    foreign = {"weak_cosmic_censorship": re.compile(r"weak_cosmic_censorship", re.I),
               "I+ completeness": re.compile(r"I\+[^.]{0,80}complete|complete[^.]{0,80}I\+", re.I),
               "visible singularity": re.compile(r"visible", re.I)}
    leaks, tagged = [], []
    for block in ("conclusion", "visibility", "i_plus", "falsifier"):
        vals = []
        b = doc.get(block, {})
        if isinstance(b, dict):
            vals = [f"{k}: {v}" for k, v in b.items()]
        elif isinstance(b, list):
            vals = [str(v) for v in b]
        for s in vals:
            for name, rx in foreign.items():
                if rx.search(s):
                    if denial.search(s) or block != "conclusion":
                        tagged.append(f"{block}:{name}")
                    else:
                        leaks.append(f"{block}:{name}:{s[:70]}")
    rec("F2A-C15", "R12 foreign-family scan: no untagged leakage in scan blocks", "PASS" if not leaks else "FAIL",
        f"untagged={leaks} tagged_mentions={sorted(set(tagged))}", "R12")

    # C16 R13 composite C0/C2 regex
    comp_rx = re.compile(r"(C0|C2)\s*(or|and|/)\s*(C0|C2)")
    matches = [m.group(0) for m in comp_rx.finditer(raw)]
    phrase_field = json.dumps(get(doc, "anti_scope.phrases_that_are_not_this_class") or [])
    untagged = [m for m in matches if m not in phrase_field]
    rec("F2A-C16", "R13 no untagged composite C0/C2 regularity token", "PASS" if not untagged else "FAIL",
        f"matches={matches} untagged={untagged}", "R13")

    # C17 R16 implication ledger directions vs containment
    led = doc.get("implication_ledger", {})
    entail = led.get("one_way_entailments", [])
    forb = led.get("forbidden_transfers", [])
    e = {"C2": 0, "C^{1,1}": 1, "H2loc": 2, "C0": 3}  # smaller index = smaller extension set
    def cls_of(s):
        if "C0 extension" in s or "C0 metric" in s:
            return "C0"
        if "H2_loc" in s:
            return "H2loc"
        if "C^1,1" in s or "C^{1,1}" in s:
            return "C^{1,1}"
        if "C2" in s:
            return "C2"
        if "WCC" in s:
            return "WCC"
        return None
    bad_ent, bad_forb = [], []
    for row in entail:
        a, b = cls_of(row.get("from", "")), cls_of(row.get("to", ""))
        if a in e and b in e:
            if not (e[a] >= e[b]):  # from must be the smaller/stronger extension set
                bad_ent.append(row)
        elif a != "WCC" and b != "WCC":
            bad_ent.append(row)
    for row in forb:
        a, b = cls_of(row.get("from", "")), cls_of(row.get("to", ""))
        if a in e and b in e:
            if a == b or not (e[a] < e[b]):  # forbidden iff from-set not contained in to-set
                bad_forb.append(row)
    chain_ok = "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0" in led.get("extension_class_containment", "")
    wcc_forbidden = any("WCC" in row.get("from", "") or "WCC" in row.get("to", "") for row in forb)
    ok17 = chain_ok and wcc_forbidden and not bad_ent and not bad_forb and len(entail) >= 3
    rec("F2A-C17", "R16 ledger: containments licensed, converse and WCC transfers forbidden", "PASS" if ok17 else "FAIL",
        f"chain_recorded={chain_ok} entailments={len(entail)} forbidden={len(forb)} bad_entail={len(bad_ent)} bad_forbidden={len(bad_forb)} wcc_forbidden={wcc_forbidden}", "R16")

    # C18 R15 provenance honesty
    prov = doc.get("provenance", {})
    ok18 = (prov.get("citation_status") in spec.get("vocabularies", {}).get("citation_status", ["unverified", "verified", "n/a", "unresolved"])
            and prov.get("citation_status") != "verified"
            and len(prov.get("unresolved_citations", [])) >= 1
            and all(s.get("status") == "unresolved" for s in prov.get("sources", [])))
    rec("F2A-C18", "R15 provenance: unverified, unresolved listed, no citation overclaim", "PASS" if ok18 else "FAIL",
        f"citation_status={prov.get('citation_status')} unresolved={len(prov.get('unresolved_citations', []))} sources={len(prov.get('sources', []))}", "R15")

    # C19 F0 binding live hashes + pointer resolution (C11/C12/C13/C14 of prior rounds)
    fb = doc.get("f0_binding", {})
    tax_doc = taxonomy
    decl_ok = fb.get("declared_f0_sha256") == pre[str(TAXONOMY)] == TAXONOMY_SHA
    cons_ok = fb.get("consistency_evidence_sha256") == pre[str(CONSISTENCY)] == CONSISTENCY_SHA
    p1 = ptr_resolve(doc.get("class_contract_pointer") or "")
    p2 = ptr_resolve(doc.get("class_contract_supplement_pointer") or "")
    cons_ok2 = consistency.get("consistent") is True and consistency.get("errors") in ([], None)
    p1_ok = p1[3] and isinstance(p1[2], dict)
    p2_ok = p2[3] and isinstance(p2[2], dict)
    ok19 = decl_ok and cons_ok and p1_ok and p2_ok and cons_ok2
    rec("F2A-C19", "F0 binding live: taxonomy hash, consistency evidence, both pointers resolve", "PASS" if ok19 else "FAIL",
        f"declared==live={decl_ok} consistency_evidence==live={cons_ok} consistency.consistent={consistency.get('consistent')} classes_ptr={p1_ok} supplement_ptr={p2_ok}", "R01/R07")

    # C20 sibling separation, both directions
    sib_comp = sib.get("class_components", {})
    ok20 = (doc.get("sibling_disjoint_from") == SIB_CLASS_ID and sib.get("sibling_disjoint_from") == CLASS_ID
            and get(sib, "conclusion.conclusion_type") == "scc_c0_future_inextendibility"
            and sib_comp.get("regularity_token") == "C0" and "scc_c2_future_inextendibility" not in sib_raw
            and "C2-inextendibility does not transfer" not in raw)
    rec("F2A-C20", "F2a/F2b symmetric sibling pointers, no conclusion verbatim transfer", "PASS" if ok20 else "FAIL",
        f"F2a->{doc.get('sibling_disjoint_from')} F2b->{sib.get('sibling_disjoint_from')} C0 conclusion in F2a={c0_in_f2a} C2 conclusion in F2b={'scc_c2_future_inextendibility' in sib_raw}")

    # C21 containment chain licensing (adversarial: H2loc subset C0 requires continuity)
    h2 = next((v for v in registry.get("variants", []) if v.get("variant_id") == "H2LOC"), {})
    h2_def = h2.get("definition", "")
    h2_continuous = "continuous metric" in h2_def
    raw_chain = re.search(r"E_C2 subset of E_\{\?C\^?\{?1,1\}?\}? subset of E_H2loc subset of E_C0", raw) or \
        re.search(r"E_C2 subset of E_\{C\^1,1\} subset of E_H2loc subset of E_C0", raw)
    ok21 = h2_continuous and bool(raw_chain) and h2.get("parent_class") == SIB_CLASS_ID
    rec("F2A-C21", "containment chain licensed by registry H2LOC definition (continuity included)", "PASS" if ok21 else "FAIL",
        f"registry_H2LOC_defines_continuity={h2_continuous} chain_text_found={bool(raw_chain)} H2LOC_parent={h2.get('parent_class')} registry_strength={h2.get('strength','')[:80]}")

    # C22 chain text itself states continuity? -> WARN if it relies on registry silently
    states_cont = False
    for m in re.finditer(r"H2_?loc", raw):
        window = raw[max(0, m.start() - 150): m.end() + 150]
        if re.search(r"\bcontinuous\b", window, re.I):
            states_cont = True
            break
    rec("F2A-C22", "F2a text cites the continuity half of the H2LOC definition", "WARN" if not states_cont else "PASS",
        "F2a line 152 gives only '(locally square-integrable curvature)'; E_H2loc subset E_C0 is true only for the registry definition 'continuous metric with Riemann in L^2_loc' (VARIANT_REGISTRY.json#variants.H2LOC). Traceability nit, not a class-semantics error.")

    # C23 class_boundary one-way implication notation
    cb = doc.get("class_boundary", {})
    ow = cb.get("one_way_implication", "")
    undef = "E(C0) entails E(C2)" in ow
    rec("F2A-C23", "one-way implication notation E(...) defined and not colliding with E_Cx sets", "WARN" if undef else "PASS",
        f"class_boundary.one_way_implication={ow!r}; implication_ledger uses E_C0 for the extension SET, so E(C0)/E(C2) are overloaded. 'because every C2 extension is a C0 extension' disambiguates the intended direction (no-C0-extension => no-C2-extension).")

    # C24 registry terminology: H2LOC is a variant, not a class/node
    calls_classes = re.findall(r"[^.\n]*H2_loc[^.\n]*class[^.\n]*", raw, re.I) + re.findall(r"[^.\n]*H2_loc classes[^.\n]*", raw)
    ok24 = bool(registry.get("class_id_rule")) and len(h2) > 0
    rec("F2A-C24", "H2LOC treated as registered variant of C0, not a class id", "WARN" if calls_classes else "PASS",
        f"registry class_id_rule present={bool(registry.get('class_id_rule'))}; F2a lines calling H2_loc/C1 'classes': {len(calls_classes)}; registry says H2LOC is a variant of {SIB_CLASS_ID}. Wording-only.")

    # C25 revision bookkeeping
    rh = doc.get("revision_history", [])
    idxs = [r.get("index") for r in rh]
    unused = [r.get("index") for r in rh if r.get("unused")]
    ok25 = (doc.get("revision") == ARTIFACT_REV and idxs == list(range(1, len(rh) + 1))
            and doc.get("revised_at") == rh[-1].get("at"))
    rec("F2A-C25", "revision number and history consistent", "PASS" if ok25 else "FAIL",
        f"revision={doc.get('revision')} history_indices={idxs} revised_at_matches_last={doc.get('revised_at') == rh[-1].get('at')} unused_rows={unused}")

    # C26 review_status bookkeeping
    rs = doc.get("review_status", {})
    rec("F2A-C26", "review_status tracks assignment and independent verdicts at this hash", "WARN",
        f"requested_reviewers={rs.get('requested_reviewers')} independent_reviewers={rs.get('independent_reviewers')} verdict={rs.get('verdict')}: three accepts (017/072/075) and this verdict exist at {TARGET_SHA[:12]} but the artifact still lists none. Bookkeeping only; the map/review files are authoritative.")

    # C27 rule_spec and registry pins under FROZEN
    rp = pins.get("artifacts/formulation/rule_spec.json", {}).get("sha256")
    gp = pins.get("artifacts/formulation/VARIANT_REGISTRY.json", {}).get("sha256")
    ok27 = rp == pre[str(RULE_SPEC)] == RULE_SPEC_SHA and gp == pre[str(REGISTRY)] == REGISTRY_SHA and len(spec.get("rules", [])) == 16
    rec("F2A-C27", "frozen rule_spec R01-R16 and registry pins match live bytes", "PASS" if ok27 else "FAIL",
        f"rule_spec pin==live={rp == pre[str(RULE_SPEC)]} rules={len(spec.get('rules', []))} registry pin==live={gp == pre[str(REGISTRY)]}")

    # C28 no drift
    post = {str(p): sha256(p) for p in (CANON, ALIAS, SIB_CANON, SIB_ALIAS, FROZEN, RULE_SPEC, REGISTRY, TAXONOMY, SUPPLEMENT, CONSISTENCY)}
    drift = {k: [pre[k][:12], post[k][:12]] for k in pre if pre[k] != post[k]}
    rec("F2A-C28", "zero drift across the run", "PASS" if not drift else "FAIL", f"drift={drift}")

    hard = [r for r in RESULTS if r["status"] == "FAIL"]
    warn = [r for r in RESULTS if r["status"] == "WARN"]
    out = {
        "run": "W018-R13-F2A-REVIEW-01",
        "actor": "worker-018",
        "target": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
        "target_sha256": pre[str(CANON)],
        "sibling_sha256": pre[str(SIB_CANON)],
        "frozen_manifest_sha256": pre[str(FROZEN)],
        "rule_spec_sha256": pre[str(RULE_SPEC)],
        "measured_at": None,
        "checks_total": len(RESULTS),
        "pass": len([r for r in RESULTS if r["status"] == "PASS"]),
        "fail": len(hard),
        "warn": len(warn),
        "fail_ids": [r["id"] for r in hard],
        "warn_ids": [r["id"] for r in warn],
        "hard_failures": hard,
        "warnings": warn,
        "checks": RESULTS,
        "authority": "read-only worker harness; no network, no model calls, no canonical artifact edited",
    }
    import datetime
    out["measured_at"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("run", "target_sha256", "checks_total", "pass", "fail", "warn", "fail_ids", "warn_ids")}, indent=1))
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
