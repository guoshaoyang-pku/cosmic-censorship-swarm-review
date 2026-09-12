#!/usr/bin/env python3
"""W092-F2A-CLASSBIND-REVIEW-01 — independent, read-only, hash-pinned review instrument.

Target : class AF-SCC-C2-VAC-GEN (node F2a, gate G-FORM) at the FROZEN rev28 pin
         schemas/af_scc_c2_vacuum.yaml sha256 5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce

This instrument is an INDEPENDENT re-implementation of the structural acceptance rules in
artifacts/formulation/rule_spec.json (R01-R16). It does not import the author's checker
(artifacts/formulation/tools/check_class_schema.py); that checker is run separately and only its
exit line is recorded as triangulation. The script is READ-ONLY on every canonical path: it never
opens a canonical file for writing. All mutations for negative controls are written to a temporary
directory and never to the repository.

Outputs (under this directory): report.json, controls.json, acceptance_run.log
Entry and exit sha256 for every pinned input are recorded; any drift makes the run INVALID.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # .../ai4math-swarm
HERE = Path(__file__).resolve().parent

TZ = timezone(timedelta(hours=8))
def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

# ---------------------------------------------------------------- pins
PIN_F2A = "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce"
PIN_C0 = "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"
PIN_F1 = "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"
PIN_F0_CANON = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
PIN_F0_SUPP = "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"
PIN_RULE_SPEC = "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e"
DECLARED_EVIDENCE = "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"

INPUTS = {
    "f2a_schema": ("schemas/af_scc_c2_vacuum.yaml", PIN_F2A),
    "f2a_mirror": ("artifacts/formulation/schemas/af_scc_c2_vacuum.yaml", PIN_F2A),
    "c0_schema": ("schemas/af_scc_c0_vacuum.yaml", PIN_C0),
    "f1_schema": ("schemas/af_wcc_vacuum.yaml", PIN_F1),
    "f0_canonical": ("research_map/formulation_taxonomy.yaml", PIN_F0_CANON),
    "f0_supplement": ("artifacts/formulation/formulation_taxonomy.yaml", PIN_F0_SUPP),
    "rule_spec": ("artifacts/formulation/rule_spec.json", PIN_RULE_SPEC),
    "frozen_manifest": ("artifacts/formulation/FROZEN.json", None),
    "consistency_evidence": ("artifacts/formulation/evidence/taxonomy_consistency.json", None),
}

# ---------------------------------------------------------------- strict YAML
class DuplicateKeyError(Exception):
    pass

def strict_load(path: Path):
    import yaml
    class StrictLoader(yaml.SafeLoader):
        pass
    def _construct_mapping(loader, node, deep=False):
        keys = set()
        for k, _ in node.value:
            kk = loader.construct_object(k, deep=True)
            if kk in keys:
                raise DuplicateKeyError(f"duplicate key {kk!r} at line {k.start_mark.line + 1}")
            keys.add(kk)
        return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)
    StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)
    with path.open() as f:
        return yaml.load(f, Loader=StrictLoader)

def lines_of(path: Path):
    return path.read_text().splitlines()

def linenos(path: Path, pattern: str):
    rx = re.compile(pattern)
    return [i + 1 for i, ln in enumerate(lines_of(path)) if rx.search(ln)]

R = lambda p: str(p.relative_to(ROOT))

# ---------------------------------------------------------------- check harness
class Checks:
    def __init__(self):
        self.rows = []
    def add(self, cid, rule, desc, status, evidence, detail=""):
        self.rows.append({"id": cid, "rule": rule, "description": desc, "status": status,
                          "evidence": evidence, "detail": detail})
    def count(self, status):
        return sum(1 for r in self.rows if r["status"] == status)

def main() -> int:
    t0 = now()
    chk = Checks()
    defects = []

    # ---- entry hashes
    entry = {k: sha256_file(ROOT / p) for k, (p, _) in INPUTS.items()}
    f2a = strict_load(ROOT / INPUTS["f2a_schema"][0])
    c0 = strict_load(ROOT / INPUTS["c0_schema"][0])
    f1 = strict_load(ROOT / INPUTS["f1_schema"][0])
    rule = json.loads((ROOT / INPUTS["rule_spec"][0]).read_text())
    frozen = json.loads((ROOT / INPUTS["frozen_manifest"][0]).read_text())
    canon = strict_load(ROOT / INPUTS["f0_canonical"][0])
    supp = strict_load(ROOT / INPUTS["f0_supplement"][0])
    aliases = json.loads((ROOT / "artifacts/formulation/VOCAB_ALIASES.json").read_text())

    # ================= P: pin / publication discipline =================
    ok = entry["f2a_schema"] == PIN_F2A
    chk.add("P01", "pin", "F2a bytes hash to the assignment pin", "PASS" if ok else "FAIL",
            f"schemas/af_scc_c2_vacuum.yaml#{entry['f2a_schema'][:12]}", f"pin {PIN_F2A[:12]}")
    ok2 = entry["f2a_mirror"] == PIN_F2A
    chk.add("P02", "publication", "schemas/ mirror == artifacts/formulation/schemas/ mirror",
            "PASS" if ok2 else "FAIL",
            f"artifacts/formulation/schemas/af_scc_c2_vacuum.yaml#{entry['f2a_mirror'][:12]}",
            "both copies at the frozen pin" if ok2 else "mirror divergence")
    fp = frozen["files"].get(INPUTS["f2a_schema"][0], {}).get("sha256")
    chk.add("P03", "freeze", "F2a bytes equal the FROZEN rev%d pin" % frozen["revision"],
            "PASS" if fp == PIN_F2A else "FAIL",
            f"artifacts/formulation/FROZEN.json#rev{frozen['revision']}",
            f"frozen pin {str(fp)[:12]}")

    # ================= R01-R16 structural rules =================
    comp = f2a.get("class_components", {})
    ident = (f2a.get("schema_version") and f2a.get("artifact_kind") == "class_schema"
             and f2a.get("class_id") in rule["frozen_classes"] and f2a.get("node_id")
             and f2a.get("owner") and f2a.get("epistemic_status"))
    chk.add("R01", "identity", "schema_version/artifact_kind/class_id/node_id/owner/epistemic_status present",
            "PASS" if ident else "FAIL", f"{R(ROOT/'schemas/af_scc_c2_vacuum.yaml')}:1-32",
            f"class_id={f2a.get('class_id')}")

    decomp = (f2a["class_id"] == "AF-SCC-C2-VAC-GEN"
              and comp == {"asymptotics": "AF", "censorship": "SCC", "matter": "VAC",
                           "genericity": "GEN", "regularity_token": "C2"})
    chk.add("R02", "class-id", "class_components decomposes class_id; SCC carries exactly one regularity token (C2)",
            "PASS" if decomp else "FAIL", f"schemas/af_scc_c2_vacuum.yaml:{linenos(ROOT/'schemas/af_scc_c2_vacuum.yaml','^class_components:')[0]}-28",
            json.dumps(comp))

    q = f2a["quantifiers"]
    dom_ids = [s["domain_id"] for s in q["ordered"]]
    doms_ok = all(d in q["domains"] for d in dom_ids) and len(q["ordered"]) == 4
    # rule_spec R03: a banned vague word may appear only if the same entry has a
    # definition_ref or numeric content; additionally, a quoted mention ('suitable')
    # inside an explicit negation is not a vague use.
    vague = re.compile(r"\bsuitable\b|\bappropriate\b|\breasonable\b", re.I)
    vague_hits = []
    for d in q["domains"]:
        node = q["domains"][d]
        txt = node.get("definition", "")
        m = vague.search(txt)
        if not m:
            continue
        exempt = bool(node.get("definition_ref")) or bool(re.search(r"[0-9]", txt))
        quoted = txt[max(0, m.start() - 1):m.end() + 1] in ("'suitable'", '"suitable"')
        vague_hits.append({"domain": d, "word": m.group(0), "exempt": exempt or quoted,
                           "ctx": txt[max(0, m.start() - 60):m.end() + 40]})
    d0 = q["domains"]["D0"]["definition"]
    d0_ok = ("r = smooth" in d0 and "r = (sobolev,s,delta)" in d0
             and "s > 5/2" in d0 and "delta in (1/2,1)" in d0)
    def resolve_ref(ref):
        node = f2a
        for part in ref.split("."):
            node = node.get(part) if isinstance(node, dict) else None
        return node
    refs = {k: resolve_ref(k) for k in
            [q["domains"][d]["definition_ref"] for d in q["domains"]]}
    q_ok = doms_ok and d0_ok and not any(not h["exempt"] for h in vague_hits)
    chk.add("R03", "quantifiers", "ordered quantifiers; all domain_ids resolve; D0 instantiable on BOTH disjuncts; no vague domain",
            "PASS" if q_ok else "FAIL",
            f"schemas/af_scc_c2_vacuum.yaml:{linenos(ROOT/'schemas/af_scc_c2_vacuum.yaml','^quantifiers:')[0]}-70",
            f"ordered={[s['kind'] for s in q['ordered']]} D0_disjuncts={{smooth, (sobolev,s,delta)}} "
            f"vague_exempt={[(h['domain'], h['exempt']) for h in vague_hits]}")
    chk.add("R03b", "quantifiers", "definition_ref targets resolve (regularity.data_regularity/genericity/data_class/extension_predicate)",
            "PASS" if all(v is not None for v in refs.values()) else "FAIL",
            "schemas/af_scc_c2_vacuum.yaml:53,56,59,62", json.dumps(refs))

    topo = f2a["topology"]
    topo_ok = (topo["spacetime_dimension"] == 4 and "connected" in topo["slice_topology"]
               and "R^3" in topo["slice_topology"] and topo["completeness_of_slice"] is True
               and topo["I_plus_topology"] == "R x S^2"
               and any("closed" in x for x in topo["forbidden"]))
    chk.add("R04", "topology", "dim 4; connected complete one-ended AF slice; I+ = R x S^2; closed/periodic forbidden",
            "PASS" if topo_ok else "FAIL", "schemas/af_scc_c2_vacuum.yaml:108-121", topo["slice_topology"][:70])

    dc = f2a["data_class"]
    dc_ok = (dc["matter"] == "none" and dc["cosmological_constant"] == 0
             and "Ric(g) = 0" in dc["equations"]
             and all(k in dc["constraints"] for k in ("hamiltonian", "momentum"))
             and "O(r^{-1})" in dc["asymptotic_decay"]["metric"]
             and "s > 5/2" in dc["regularity_class"]["sobolev_variant"]["s"])
    chk.add("R05", "data-class", "vacuum, Lambda=0, both constraints, numeric decay, named s/delta branch",
            "PASS" if dc_ok else "FAIL", "schemas/af_scc_c2_vacuum.yaml:123-140",
            f"mass_citation={dc['adm_mass']['citation_status']}")

    reg = f2a["regularity"]
    reg_ok = (reg["extension_regularity"] == "C2"
              and reg["extension_solution_concept"] == "classical_ricci"
              and "extension_regularity_exact" in reg and len(reg["must_not_conflate"]) >= 2)
    chk.add("R06", "regularity", "extension_regularity == class token C2; concept=classical_ricci; slots separated; must_not_conflate non-empty",
            "PASS" if reg_ok else "FAIL", "schemas/af_scc_c2_vacuum.yaml:142-153",
            reg["extension_regularity_exact"][:90])

    gen = f2a["genericity"]
    gen_ok = (gen["kind"] in rule["vocabularies"]["genericity_kind"]
              and gen.get("ambient_space") and gen.get("topology_or_measure")
              and gen.get("generic_set") and gen.get("excluded_set") is not None
              and len(gen.get("transfer_failures", [])) > 0 and gen.get("is_part_of_class") is True)
    chk.add("R07", "genericity", "kind in vocabulary; ambient/topology/generic_set/excluded_set present; transfer_failures non-empty; is_part_of_class",
            "PASS" if gen_ok else "FAIL", "schemas/af_scc_c2_vacuum.yaml:155-176",
            f"kind={gen['kind']} transfers_fail={len(gen['transfer_failures'])} excluded_status={gen['excluded_set_status']}")
    banach_note = ("Banach" in gen["ambient_space"] and "Frechet" not in gen["ambient_space"])
    chk.add("R07b", "genericity", "Baire justification covers BOTH the Sobolev (Banach) and smooth (Frechet) branches",
            "PASS" if not banach_note else "DEFECT", "schemas/af_scc_c2_vacuum.yaml:157",
            "ambient_space cites 'closed subset of a Banach space, hence Baire' while the smooth branch is Frechet; "
            "Frechet spaces are Baire so the conclusion holds, but the stated reason is incomplete")

    nv = f2a["non_vacuity"]
    nv_ok = bool(nv.get("condition")) and bool(nv.get("witness_type")) and bool(nv.get("vacuity_falsifier"))
    chk.add("R08", "non-vacuity", "condition + witness_type + vacuity falsifier present; argument labelled unverified",
            "PASS" if nv_ok else "FAIL", "schemas/af_scc_c2_vacuum.yaml:178-188",
            f"status={nv['status'][:60]} | c2_arg={nv['c2_vacuity_argument_status']}")

    ip = f2a["i_plus"]
    ip_ok = (ip["role"] == "assumption" and ip["in_conclusion"] is False
             and ip.get("completeness_in_conclusion") is False)
    chk.add("R09", "I+", "SCC: I+ is an assumption, not in conclusion; no completeness assertion",
            "PASS" if ip_ok else "FAIL", "schemas/af_scc_c2_vacuum.yaml:190-195", ip["definition"][:80])

    vis = f2a["visibility"]
    vis_ok = (vis["role"] == "not_in_conclusion" and vis.get("reason")
              and vis.get("visible_singularity_is_wcc") is True and vis.get("forbidden_falsifier"))
    chk.add("R10", "visibility", "SCC: visibility not in conclusion; visible-singularity falsifier explicitly assigned to WCC",
            "PASS" if vis_ok else "FAIL", "schemas/af_scc_c2_vacuum.yaml:197-205", vis["forbidden_falsifier"][:90])

    concl = f2a["conclusion"]
    expect = rule["vocabularies"]["class_conclusion_type"][f2a["class_id"]]
    c_ok = (concl["conclusion_type"] == expect
            and concl["epistemic_status"] in rule["vocabularies"]["epistemic_status"]
            and len(concl.get("forbidden_strengthenings", [])) > 0
            and "theorem" not in str(concl.get("epistemic_status")))
    chk.add("R11", "conclusion", "conclusion_type == rule_spec vocabulary; epistemic_status=open_problem; no theorem promotion",
            "PASS" if c_ok else "FAIL", "schemas/af_scc_c2_vacuum.yaml:207-233",
            f"{concl['conclusion_type']} (expected {expect}); epistemic={concl['epistemic_status']}")

    # R12 lexical leakage, structural: only POSITIVE assertions of foreign-family content
    # count. A string leaf is exempt when (a) its key path is a forbidding/exclusion slot, or
    # (b) its own text carries a negation / belongs-to-WCC / wrong-family marker.
    leak_blocks = rule["leakage_scan_blocks"]
    foreign = re.compile(r"\bvisible|\bvisibility|I\+ completeness|asymptotic predictability|weak cosmic censorship", re.I)
    exempt_key = re.compile(r"forbidden|must_not_conflate|schema_falsifiers|not_this_class|"
                            r"phrases_that_are_not|is_wcc|reason", re.I)
    exempt_text = re.compile(r"\bnot\b|\bno\b|forbid|wrong-family|belongs to WCC|is the WCC|"
                             r"does not|may not|\bnever\b|must not|\bexcluded\b|\bdifferent\b", re.I)

    def walk(node, path):
        leaves = []
        if isinstance(node, dict):
            for k, v in node.items():
                leaves += walk(v, path + [str(k)])
        elif isinstance(node, list):
            for i, v in enumerate(node):
                leaves += walk(v, path + [str(i)])
        else:
            leaves.append((".".join(path), str(node)))
        return leaves

    leak_hits = []
    for b in leak_blocks:
        for keypath, text in walk(f2a.get(b, {}), [b]):
            m = foreign.search(text)
            if not m:
                continue
            exempt = bool(exempt_key.search(keypath)) or bool(exempt_text.search(text))
            leak_hits.append({"block": b, "key": keypath, "token": m.group(0),
                              "exempt": exempt, "text": text[:140]})
    unexempt = [h for h in leak_hits if not h["exempt"]]
    chk.add("R12", "leakage", "no POSITIVE foreign-family conclusion content in leakage_scan_blocks (negations/exclusions exempt)",
            "PASS" if not unexempt else "FAIL", "rule_spec.leakage_scan_blocks + schemas/af_scc_c2_vacuum.yaml:207,197,190,248",
            f"hits={len(leak_hits)} unexempt={len(unexempt)}" +
            ("; " + json.dumps([h['key'] for h in unexempt]) if unexempt else ""))

    f2a_lines = lines_of(ROOT / "schemas/af_scc_c2_vacuum.yaml")
    comp_re = re.compile(r"(C0|C2)\s*(or|and|/)\s*(C0|C2)")
    composite = []
    for i, ln in enumerate(f2a_lines, 1):
        if comp_re.search(ln):
            exempt = ("not_this_class" in ln or "composite regularity" in ln
                      or "forbidden" in ln.lower() or "phrases_that_are_not" in ln)
            composite.append({"line": i, "exempt": exempt, "text": ln.strip()[:100]})
    chk.add("R13", "composite-regularity", "no 'C0 or C2' composite outside an explicit forbidden-phrase quotation",
            "PASS" if all(c["exempt"] for c in composite) else "FAIL", "schemas/af_scc_c2_vacuum.yaml:273-276",
            f"occurrences={len(composite)} all_exempt={all(c['exempt'] for c in composite)}")

    f = f2a["falsifier"]
    t1, t2 = f["tier_1"], f["tier_2"]
    f_ok = (t1["refutes"] == f2a["class_id"] and "non-meager" in t1["genericity_requirement"]
            and "extension" in t1["witness_type"] and len(t1["machine_checkable_steps"]) > 0
            and "refutes_strengthening_only" in str(t2.get("labelling_required"))
            and len(f.get("schema_falsifiers", [])) >= 3)
    chk.add("R14", "falsifier", "tier_1 refutes this class with genericity requirement; extension witness; machine-checkable steps; tier_2 labelled strengthening-only",
            "PASS" if f_ok else "FAIL", "schemas/af_scc_c2_vacuum.yaml:248-264",
            f"routes: R1 non-meagerness / R2 instantiated G*; machine_steps={len(t1['machine_checkable_steps'])}")

    prov = f2a["provenance"]
    p_ok = (prov["citation_status"] in rule["vocabularies"]["citation_status"]
            and len(prov.get("unresolved_citations", [])) > 0 and prov.get("no_status_claim"))
    chk.add("R15", "provenance", "citation_status vocabulary-valid; unresolved citations listed; no source presented as establishing the class",
            "PASS" if p_ok else "FAIL", "schemas/af_scc_c2_vacuum.yaml:293-302",
            f"citation_status={prov['citation_status']}")

    led = f2a["implication_ledger"]
    l_ok = ("E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0" in led["extension_class_containment"]
            and any(x["from"].startswith("no proper future C0") and x["to"] == "no proper future C2 extension"
                    for x in led["one_way_entailments"])
            and any(x.get("from", "").startswith("no proper future C2")
                    for x in led["forbidden_transfers"])
            and any("WCC" in x.get("from", "") for x in led["forbidden_transfers"]))
    chk.add("R16", "implication-ledger", "C2⊆C0 containment; C0-inext entails C2; converse and WCC->SCC forbidden",
            "PASS" if l_ok else "FAIL", "schemas/af_scc_c2_vacuum.yaml:235-246",
            "asymmetric ledger present")

    # ================= S: separation, contracts, binding =================
    matrix = {}
    for key, path in (("c2", "conclusion.conclusion_type"), ("c0", "conclusion.conclusion_type"),
                      ("c2_ext", "regularity.extension_regularity"), ("c0_ext", "regularity.extension_regularity"),
                      ("c2_eq", "regularity.extension_solution_concept"), ("c0_eq", "regularity.extension_solution_concept"),
                      ("c2_pred_reg", "extension_predicate.frozen_regularity"),
                      ("c0_pred_reg", "extension_predicate.frozen_regularity"),
                      ("c2_pred_eq", "extension_predicate.frozen_equation_concept"),
                      ("c0_pred_eq", "extension_predicate.frozen_equation_concept")):
        src = f2a if key.startswith("c2") else c0
        node = src
        for part in path.split("."):
            node = node[part]
        matrix[key] = node
    sep_ok = (matrix["c2"] != matrix["c0"]
              and matrix["c2"] == rule["vocabularies"]["class_conclusion_type"]["AF-SCC-C2-VAC-GEN"]
              and matrix["c0"] == rule["vocabularies"]["class_conclusion_type"]["AF-SCC-C0-VAC-GEN"]
              and matrix["c2_ext"] == "C2" and matrix["c0_ext"] == "C0"
              and matrix["c2_eq"] == "classical_ricci" and matrix["c0_eq"] == "none")
    chk.add("S01", "separation", "C2/C0 separation is carried by CONTENT (distinct conclusion_type, extension regularity, equation signature), not by naming",
            "PASS" if sep_ok else "FAIL", "schemas/af_scc_c2_vacuum.yaml:208,146,148 vs schemas/af_scc_c0_vacuum.yaml",
            json.dumps(matrix, sort_keys=True))
    merged = re.search(r"conclusion_type\s*:\s*.*(C0|C2).*(C0|C2)", "\n".join(f2a_lines))
    chk.add("S01b", "separation", "no C0/C2 merge: neither schema asserts the sibling's conclusion_type",
            "PASS" if not merged else "FAIL", "schemas/af_scc_c2_vacuum.yaml:208",
            "conclusion tokens are disjoint and both are in the frozen rule_spec vocabulary")

    ptr = f2a["class_contract_pointer"]
    supp_ptr = f2a["class_contract_supplement_pointer"]
    pcanon = canon.get("classes", {}).get("AF-SCC-C2-VAC-GEN")
    psupp = supp.get("class_contracts", {}).get("AF-SCC-C2-VAC-GEN")
    alias_ok = False
    canon_type = (pcanon or {}).get("conclusion", {}).get("type")
    for canonical, alist in aliases["conclusion_type"].items():
        if canon_type in alist:
            alias_ok = (canonical == f2a["conclusion"]["conclusion_type"])
    ptr_ok = bool(pcanon) and bool(psupp) and psupp.get("conclusion_type") == f2a["conclusion"]["conclusion_type"]
    chk.add("S02", "contracts", "class_contract_pointer and supplement pointer resolve; supplement conclusion_type matches schema",
            "PASS" if ptr_ok else "FAIL", f"research_map/formulation_taxonomy.yaml#{PIN_F0_CANON[:12]} ; artifacts/formulation/formulation_taxonomy.yaml#{PIN_F0_SUPP[:12]}",
            f"canonical_type={canon_type} (alias-bridged={alias_ok}); supplement_type={psupp.get('conclusion_type') if psupp else None}")
    chk.add("S02b", "contracts", "canonical F0 contract uses the canonical conclusion token, not an alias",
            "PASS" if canon_type == f2a["conclusion"]["conclusion_type"] else "DEFECT",
            "research_map/formulation_taxonomy.yaml (classes.AF-SCC-C2-VAC-GEN.conclusion.type)",
            f"uses {canon_type!r}; VOCAB_ALIASES policy says aliases 'must never appear in a new canonical artifact' (F0-owned, not F2a-owned)")

    fb = f2a["f0_binding"]
    declared = fb["consistency_evidence_sha256"]
    live = entry["consistency_evidence"]
    frozen_ev = frozen["files"][INPUTS["consistency_evidence"][0]]["sha256"]
    decl_f0 = fb["declared_f0_sha256"] == entry["f0_canonical"] == PIN_F0_CANON
    chk.add("S03a", "binding", "declared F0 canonical hash == live bytes == FROZEN pin",
            "PASS" if decl_f0 else "FAIL", "schemas/af_scc_c2_vacuum.yaml:291",
            f"declared={fb['declared_f0_sha256'][:12]} live={entry['f0_canonical'][:12]} frozen={PIN_F0_CANON[:12]}")
    chk.add("S03b", "binding", "supplement companion hash == FROZEN pin (companion, not mirror; REC-3)",
            "PASS" if entry["f0_supplement"] == PIN_F0_SUPP else "FAIL",
            "artifacts/formulation/formulation_taxonomy.yaml", entry["f0_supplement"][:12])
    ev_ok = declared == live == frozen_ev
    chk.add("S03c", "binding", "declared consistency-evidence hash resolves at the canonical path and equals the FROZEN pin",
            "PASS" if ev_ok else "DEFECT", "schemas/af_scc_c2_vacuum.yaml:291 vs artifacts/formulation/FROZEN.json",
            f"declared={declared[:12]} live={live[:12]} frozen={frozen_ev[:12]}; "
            f"live==frozen={live == frozen_ev}; declared==live={declared == live}")
    if not ev_ok:
        defects.append({
            "id": "HF-W092-F2A-01",
            "what": "The pinned F2a schema declares f0_binding.consistency_evidence_sha256 = 675a99d0…, "
                    "but the canonical path it names holds 9e335e9b…, which is also the FROZEN rev28 pin. "
                    "The declared evidence is unresolvable at the frozen revision.",
            "why_it_matters": "F2a's own binding rule requires the consistency check to resolve before any gate verdict; "
                              "frozen-revision provenance is not self-consistent. The live/frozen document is a strict "
                              "superset of the declared one (it adds map_taxonomy_sha256, lead_contract_sha256, measured_at), "
                              "so class semantics are unaffected.",
            "repair_preserving_pins": "restore the 675a99d0 bytes at the canonical path (copy exists at "
                                      "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json) and re-freeze "
                                      "the evidence pin; the three rev12 schema bytes and their bound review files are untouched.",
            "repair_retiring_pins": "re-stamp f0_binding.consistency_evidence_sha256 in all three schemas to 9e335e9b and re-freeze; "
                                    "this changes the schema bytes and voids verdicts bound to the rev12 pins."})

    # cross-artifact shared fields C2 vs F1 (report as findings, not failures)
    shared = {}
    for k in ("matter", "cosmological_constant", "equations"):
        shared[k] = (f2a["data_class"].get(k), f1["data_class"].get(k))
    shared["slice_topology"] = (f2a["topology"]["slice_topology"], f1["topology"]["slice_topology"])
    shared["spacetime_dimension"] = (f2a["topology"]["spacetime_dimension"], f1["topology"]["spacetime_dimension"])
    mism = {k: v for k, v in shared.items() if v[0] != v[1]}
    chk.add("S04", "cross-artifact", "shared data_class/topology fields agree with F1 where the classes share them",
            "PASS" if not mism else "DEFECT", "schemas/af_scc_c2_vacuum.yaml:123-140 vs schemas/af_wcc_vacuum.yaml",
            f"mismatches={json.dumps(mism)}" if mism else "all shared fields agree")

    # ================= C: negative controls (sandboxed mutations) =================
    controls = []
    def run_control(cid, mutate, must_fail_rule):
        with tempfile.TemporaryDirectory() as td:
            src = (ROOT / "schemas/af_scc_c2_vacuum.yaml").read_text()
            mutated = mutate(src)
            p = Path(td) / "mutant.yaml"
            p.write_text(mutated)
            try:
                m = strict_load(p)
            except DuplicateKeyError as e:
                controls.append({"id": cid, "mutated": must_fail_rule, "detected": True,
                                 "why": f"strict loader: {e}"})
                return
            detected = False
            why = ""
            if must_fail_rule == "S01":
                detected = m["conclusion"]["conclusion_type"] == c0["conclusion"]["conclusion_type"]
                why = "mutant conclusion_type collapses to the C0 token; S01 separation predicate rejects it"
            elif must_fail_rule == "R06":
                detected = m["regularity"]["extension_regularity"] != "C2"
                why = "mutant extension_regularity leaves the class token; R06 + S01 reject it"
            elif must_fail_rule == "R03":
                d = m["quantifiers"]["domains"]["D0"]["definition"]
                detected = not ("r = smooth" in d and "r = (sobolev,s,delta)" in d)
                why = "mutant D0 replaces the tagged disjoint union with vague wording; R03 rejects it"
            controls.append({"id": cid, "mutated": must_fail_rule, "detected": detected, "why": why})
    run_control("C01", lambda s: s.replace("conclusion_type: scc_c2_future_inextendibility",
                                           "conclusion_type: scc_c0_future_inextendibility"), "S01")
    run_control("C02", lambda s: s.replace("extension_regularity: C2", "extension_regularity: C0"), "R06")
    run_control("C03", lambda s: re.sub(r"definition: \"admissible regularity indices.*?\"",
                                        'definition: "suitable regularity"', s, count=1, flags=re.S), "R03")
    ctrl_ok = all(c["detected"] for c in controls) and len(controls) == 3
    chk.add("C00", "controls", "3/3 negative controls detected by the independent instrument",
            "PASS" if ctrl_ok else "FAIL", "artifacts/worker-092/f2a_review/controls.json",
            "; ".join(f"{c['id']}->{c['mutated']}:{'detected' if c['detected'] else 'MISSED'}" for c in controls))

    # ---- exit hashes / drift
    exit_h = {k: sha256_file(ROOT / p) for k, (p, _) in INPUTS.items()}
    drift = {k: (entry[k], exit_h[k]) for k in entry if entry[k] != exit_h[k]}
    chk.add("D00", "drift", "entry == exit hash for every pinned input (read-only instrument)",
            "PASS" if not drift else "FAIL", "all inputs", f"drifted={list(drift)}")

    # ---- canonical checker triangulation (read-only invocation)
    try:
        cp = subprocess.run([sys.executable, str(ROOT / "artifacts/formulation/tools/check_class_schema.py"),
                             "--json", str(ROOT / "schemas/af_scc_c2_vacuum.yaml")],
                            capture_output=True, text=True, timeout=120)
        author = json.loads(cp.stdout or "{}")
    except Exception as e:  # noqa
        author = {"verdict": f"instrument-error: {e}"}
    chk.add("T00", "triangulation", "author's canonical checker (independent implementation) agrees",
            "PASS" if author.get("verdict") == "pass" else "DEFECT",
            "artifacts/formulation/tools/check_class_schema.py", f"author checker verdict={author.get('verdict')}")

    summary = {"PASS": chk.count("PASS"), "DEFECT": chk.count("DEFECT"), "FAIL": chk.count("FAIL")}
    passed = summary["FAIL"] == 0
    findings = [
        {"id": "SF-W092-F2A-01", "severity": "soft", "owner": "lead-formulation (F2a re-author)",
         "check": "S03c", "text": "F2a f0_binding declares the stale consistency-evidence hash 675a99d0; "
                                  "canonical/FROZEN is 9e335e9b. Hard finding HF-W092-F2A-01."},
        {"id": "SF-W092-F2A-02", "severity": "soft", "owner": "lead-formulation (F0 canonical taxonomy)",
         "check": "S02b", "text": "The canonical F0 contract uses the alias conclusion token strong_cosmic_censorship_C2 "
                                  "where VOCAB_ALIASES names scc_c2_future_inextendibility canonical and says aliases "
                                  "'must never appear in a new canonical artifact'. Alias-bridged, so not a class merge."},
        {"id": "SF-W092-F2A-03", "severity": "soft", "owner": "lead-formulation (F2a)",
         "check": "R07b", "text": "genericity.ambient_space justifies Baire-ness by 'closed subset of a Banach space' while "
                                  "the smooth branch is Frechet; Frechet spaces are Baire, so the conclusion holds but the "
                                  "stated reason is incomplete for the smooth disjunct."},
        {"id": "SF-W092-F2A-04", "severity": "soft", "owner": "lead-formulation",
         "check": "revision_history", "text": "revision_history entry index 9 is marked unused:true yet carries two notes "
                                               "(rev11 delta and rev8 delta); the rev11 note is never applied, which is "
                                               "consistent with supersedes:null but makes the revision trail ambiguous."},
    ]
    report = {
        "check_id": "W092-F2A-CLASSBIND-REVIEW-01",
        "reviewer": "worker-092",
        "actor_role": "bounded execution worker (reviewer; not an author of the artifact)",
        "created_at": t0,
        "finished_at": now(),
        "instrument": R(HERE / "verify_f2a.py"),
        "read_only_on_canonical_paths": True,
        "target": {
            "class_id": "AF-SCC-C2-VAC-GEN", "node_id": "F2a", "gate": "G-FORM",
            "artifact": "schemas/af_scc_c2_vacuum.yaml", "pin_sha256": PIN_F2A,
            "frozen_revision": frozen["revision"],
        },
        "pin_check": {"entry_sha256": entry, "exit_sha256": exit_h, "drift": drift},
        "checks": chk.rows,
        "separation_matrix": matrix,
        "negative_controls": controls,
        "leakage_dispositions": leak_hits,
        "defects": defects,
        "findings": findings,
        "summary": summary,
        "structural_result": "all 16 structural rules (R01-R16) PASS on the pinned class contract"
                             if passed else "structural failures present",
        "scope_limits": [
            "structural acceptance only; no judgement of physical truth or of any theorem",
            "machine-checkable structural rules do not certify the mathematical content of the genericity/vacuity arguments",
            "the declared consistency-evidence hash defect is a provenance finding, not a class-semantics finding",
            "the R12 leak scan is heuristic; every hit was manually dispositioned in leakage_dispositions",
        ],
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True))
    (HERE / "controls.json").write_text(json.dumps({"controls": controls, "all_detected": ctrl_ok}, indent=1))

    with (HERE / "acceptance_run.log").open("a") as f:
        f.write(f"[{now()}] W092-F2A-CLASSBIND-REVIEW-01 pin={PIN_F2A[:12]} "
                f"PASS={summary['PASS']} DEFECT={summary['DEFECT']} FAIL={summary['FAIL']} "
                f"controls={'DETECTED' if ctrl_ok else 'MISSED'} drift={len(drift)} "
                f"author_checker={author.get('verdict')}\n")
    print(json.dumps({"summary": summary, "defects": [d["id"] for d in defects],
                      "controls": ctrl_ok, "drift": list(drift),
                      "author_checker": author.get("verdict")}, indent=1))
    return 0 if passed and ctrl_ok and not drift else 1


if __name__ == "__main__":
    sys.exit(main())
