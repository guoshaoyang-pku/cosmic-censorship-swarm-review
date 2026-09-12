#!/usr/bin/env python3
"""Independent read-only conformance probe for F2a (AF-SCC-C2-VAC-GEN schema).

Bound to bytes, not to review prose: every check names the exact path and hashes
are re-measured at run time. No file under review is written. Deterministic, no
network. Intended as the machine evidence behind reviews/F2a-review-19.json.

Usage: python3 check_f2a_independent.py [--json]
Exit code: 0 if all HARD checks pass, 1 otherwise (soft checks never change the
exit code, they are reported for the reviewer).
"""
import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "schemas/af_scc_c2_vacuum.yaml"
SIBLING = ROOT / "schemas/af_scc_c0_vacuum.yaml"
SIBLING2 = ROOT / "schemas/af_wcc_vacuum.yaml"
F0 = ROOT / "research_map/formulation_taxonomy.yaml"
SUPPLEMENT = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
EVIDENCE = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
ALIASES = ROOT / "artifacts/formulation/VOCAB_ALIASES.json"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
SCHEMA_TOOL = ROOT / "artifacts/formulation/tools/check_class_schema.py"
CONSISTENCY_TOOL = ROOT / "artifacts/formulation/tools/check_taxonomy_consistency.py"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def dup_keys(node, path=""):
    """Return duplicate mapping keys under a yaml.compose() node tree."""
    out = []
    if isinstance(node, yaml.MappingNode):
        seen = {}
        for k, v in node.value:
            key = getattr(k, "value", None)
            if key in seen:
                out.append(f"{path}/{key}")
            seen[key] = True
            out += dup_keys(v, f"{path}/{key}")
    elif isinstance(node, yaml.SequenceNode):
        for i, v in enumerate(node.value):
            out += dup_keys(v, f"{path}[{i}]")
    return out


def main():
    checks = []

    def add(cid, hard, ok, detail):
        checks.append({"id": cid, "hard": hard, "pass": bool(ok), "detail": detail})

    raw = TARGET.read_text()
    doc = yaml.safe_load(raw)
    f0 = yaml.safe_load(F0.read_text())
    supp = yaml.safe_load(SUPPLEMENT.read_text())
    sib = yaml.safe_load(SIBLING.read_text())
    aliases = json.loads(ALIASES.read_text())
    frozen = json.loads(FROZEN.read_text())

    t_sha = sha(TARGET)
    s_sha = sha(SIBLING)
    e_sha = sha(EVIDENCE)

    # ---------------- A. binding integrity ----------------
    fb = doc.get("f0_binding", {})
    add("A1", True, fb.get("declared_f0_sha256") == sha(F0),
        f"declared_f0={str(fb.get('declared_f0_sha256'))[:12]} measured_f0={sha(F0)[:12]}")
    decl_ev = fb.get("consistency_evidence_sha256")
    add("A2", True, decl_ev == e_sha,
        f"declared_evidence={str(decl_ev)[:12]} measured_evidence={e_sha[:12]} (declared pin must resolve on disk)")
    ev = json.loads(EVIDENCE.read_text())
    embedded = [k for k in ev if "sha256" in str(k).lower()] + \
               [k for k, v in ev.items() if isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)]
    add("A3", False, bool(embedded),
        f"evidence document embeds compared-tree hashes: {sorted(set(embedded)) if embedded else 'NONE'} "
        f"(paths+boolean only: {sorted(ev.keys())})")
    files = frozen.get("files", {})
    pin = files.get("schemas/af_scc_c2_vacuum.yaml", {}).get("sha256")
    add("A4", False, pin == t_sha, f"FROZEN rev{frozen.get('revision')} pin {str(pin)[:12]} vs measured {t_sha[:12]}")

    # ---------------- B. conclusion vocabulary ----------------
    f0_allowed = f0.get("field_vocabulary", {}).get("conclusion_type", {}).get("allowed", [])
    ct = doc.get("conclusion", {}).get("conclusion_type")
    f0_axes_ct = f0["classes"]["AF-SCC-C2-VAC-GEN"]["axes"]["conclusion_type"]
    add("B1", True, ct in f0_allowed,
        f"F2a conclusion_type={ct!r} in canonical F0 allowed={f0_allowed}")
    alias = aliases.get("conclusion_type", {})
    canon = next((k for k, v in alias.items() if ct == k or ct in v), ct)
    canon_f0 = next((k for k, v in alias.items() if f0_axes_ct == k or f0_axes_ct in v), f0_axes_ct)
    add("B2", False, canon == canon_f0,
        f"alias-canonical F2a={canon} vs canonical-F0 class axes={canon_f0} (C0/C2 merge check)")
    c0_ct = sib.get("conclusion", {}).get("conclusion_type")
    wcc_ct = yaml.safe_load(SIBLING2.read_text()).get("conclusion", {}).get("conclusion_type")
    add("B3", True, ct not in (c0_ct, wcc_ct, "scc_c0_future_inextendibility", "weak_cosmic_censorship"),
        f"F2a={ct!r} distinct from C0={c0_ct!r} and WCC={wcc_ct!r}")

    # ---------------- C. structure / quantifiers ----------------
    required = ["quantifiers", "class_boundary", "conventions", "extension_predicate", "topology",
                "data_class", "regularity", "genericity", "non_vacuity", "i_plus", "visibility",
                "conclusion", "implication_ledger", "falsifier", "anti_scope"]
    missing = [k for k in required if k not in doc]
    add("C1", True, not missing, f"required slots missing={missing}")

    q = doc["quantifiers"]
    seq = [(b.get("kind"), b.get("binder"), b.get("domain_id")) for b in q.get("ordered", [])]
    expect = [("forall", "r", "D0"), ("exists", "G_r", "D1"), ("forall", "(Sigma,h,K)", "D2"),
              ("not_exists", "(M',g',iota)", "D3")]
    add("C2", True, seq == expect and q.get("order_matters") is True,
        f"ordered binders={seq} order_matters={q.get('order_matters')}")
    doms = q.get("domains", {})
    add("C3", True, all(d in doms for d in ("D0", "D1", "D2", "D3")) and
        all(doms[d].get("definition") for d in ("D0", "D1", "D2", "D3")),
        f"domains present={sorted(doms)} each with definition")
    d0 = doms.get("D0", {}).get("definition", "")
    formal = q.get("formal", "")
    add("C4", True, ("forall r in D0" in formal) and ("(s,delta) in D0" not in formal)
        and ("sobolev" in d0) and ("smooth" in d0),
        "D0 typed as one index r over {smooth} u {(sobolev,s,delta)}; no pair-typed binder")
    neg = (q.get("negation", "") + " " + q.get("negation_normal_form", "")).lower()
    add("C5", True, ("every comeager" in neg or "non-meager" in neg) and "exists proper" in neg,
        "negation is non-meagerness of the extendible set (Baire-space dual of exists-comeager-forall)")

    ep = doc["extension_predicate"]
    clauses = [c for c in ("(a)", "(b)", "(c)", "(d)", "(e)", "(f)") if c in ep.get("definition", "")]
    add("C6", True, len(clauses) == 6 and ep.get("frozen_regularity") == "C2"
        and ep.get("frozen_direction") == "future" and ep.get("frozen_equation_concept") == "classical_ricci",
        f"extension clauses={clauses} frozen=({ep.get('frozen_regularity')},{ep.get('frozen_direction')},{ep.get('frozen_equation_concept')})")
    topo = doc["topology"]
    add("C7", True, topo.get("spacetime_dimension") == 4 and "one AF end" in str(topo.get("end_structure"))
        and topo.get("I_plus_topology") and topo.get("development_topology") and topo.get("extension_topology"),
        "topology block: 4d, one AF end, I+ / development / extension topology declared")
    gen = doc["genericity"]
    add("C8", True, gen.get("kind") == "residual_comeager" and gen.get("is_part_of_class") is True
        and len(gen.get("transfer_failures", [])) >= 3 and len(gen.get("variants", [])) >= 3,
        f"genericity kind={gen.get('kind')} transfer_failures={len(gen.get('transfer_failures', []))} variants={len(gen.get('variants', []))}")
    add("C9", True, doc["i_plus"].get("in_conclusion") is False
        and doc["visibility"].get("role") == "not_in_conclusion",
        "I+ and visibility are assumptions, not in the conclusion")
    con = doc["conclusion"]
    fs = " ".join(con.get("forbidden_strengthenings", [])).lower()
    fw = " ".join(con.get("forbidden_weakenings", [])).lower()
    add("C10", True, "c0" in fs and ("wcc" in fs or "weak cosmic censorship" in fs) and "two-sided" in fs
        and "generic" in fw,
        "conclusion forbids C0/WCC/two-sided inflation and generic-quantifier dropping")
    fal = doc["falsifier"]
    t1 = fal.get("tier_1", {})
    add("C11", True, t1.get("refutes") == doc["class_id"] and t1.get("witness_type")
        and t1.get("proof_obligations") and t1.get("machine_checkable_steps")
        and t1.get("non_machine_checkable_step") and fal.get("tier_2", {}).get("labelling_required") == "refutes_strengthening_only",
        "falsifier: class-bound tier_1 with machine-checkable steps + declared non-machine step; tier_2 labelled strengthening-only")

    # ---------------- D. leakage ----------------
    con_text = " ".join([str(con.get("statement_natural_language", "")), str(con.get("statement_formal", "")),
                         str(con.get("conclusion_type", "")), str(con.get("family", "")),
                         " ".join(str(r) for r in con.get("equivalent_rephrasings", []))])
    add("D1", True, ("AF-SCC-C0-VAC-GEN" not in con_text) and ("C0" not in con_text and "C^0" not in con_text),
        "sibling C0 token absent from the positive conclusion fields")
    add("D2", True, ("visible" not in con_text.lower()) and ("I+" not in con_text)
        and ("completeness" not in con_text.lower()) and ("predictab" not in con_text.lower()),
        "WCC content (visibility / I+ completeness / predictability) absent from the conclusion fields")
    comps = "".join(str(doc["class_components"][k]) for k in ("asymptotics", "censorship", "matter", "genericity"))
    cid_sans_token = doc.get("class_id", "").replace("-", "").replace(str(doc["class_components"]["regularity_token"]), "", 1)
    add("D3", True, doc.get("class_id") == "AF-SCC-C2-VAC-GEN"
        and comps == cid_sans_token
        and doc["class_boundary"].get("one_class_only") == doc["class_id"],
        f"class_id={doc.get('class_id')} components={doc['class_components']}")
    anti = {e.get("class_id") for e in doc["anti_scope"].get("not_this_class", []) if isinstance(e, dict)}
    add("D4", True, {"AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN", "AF-WCC-SCALAR-SPH"} <= anti,
        f"anti_scope names the other frozen classes: {sorted(x for x in anti if x)}")

    # ---------------- E. hygiene ----------------
    dups = dup_keys(yaml.compose(raw))
    add("E1", True, not dups, f"yaml duplicate mapping keys={dups}")

    measured = {
        "target": {"path": "schemas/af_scc_c2_vacuum.yaml", "sha256": t_sha, "bytes": len(raw.encode())},
        "sibling_c0": {"path": "schemas/af_scc_c0_vacuum.yaml", "sha256": s_sha},
        "f0_canonical": {"path": "research_map/formulation_taxonomy.yaml", "sha256": sha(F0)},
        "f0_supplement": {"path": "artifacts/formulation/formulation_taxonomy.yaml", "sha256": sha(SUPPLEMENT)},
        "consistency_evidence": {"path": "artifacts/formulation/evidence/taxonomy_consistency.json", "sha256": e_sha},
        "frozen_manifest": {"path": "artifacts/formulation/FROZEN.json", "sha256": sha(FROZEN),
                            "revision": frozen.get("revision")},
        "schema_tool": {"path": "artifacts/formulation/tools/check_class_schema.py", "sha256": sha(SCHEMA_TOOL)},
        "consistency_tool": {"path": "artifacts/formulation/tools/check_taxonomy_consistency.py", "sha256": sha(CONSISTENCY_TOOL)},
        "aliases": {"path": "artifacts/formulation/VOCAB_ALIASES.json", "sha256": sha(ALIASES)},
    }
    hard_failed = [c["id"] for c in checks if c["hard"] and not c["pass"]]
    soft_failed = [c["id"] for c in checks if not c["hard"] and not c["pass"]]
    result = {
        "probe": "independent_f2a_conformance",
        "generated_at": None,  # stamped by caller
        "target_sha256": t_sha,
        "checks": checks,
        "hard_failed": hard_failed,
        "soft_failed": soft_failed,
        "verdict": "fail" if hard_failed else "pass",
        "measured": measured,
    }
    if "--json" in sys.argv:
        print(json.dumps(result, indent=1))
    else:
        for c in checks:
            print(f"[{'PASS' if c['pass'] else 'FAIL'}] {'HARD' if c['hard'] else 'soft'} {c['id']}: {c['detail']}")
        print(f"hard_failed={hard_failed} soft_failed={soft_failed}")
    return 1 if hard_failed else 0


if __name__ == "__main__":
    sys.exit(main())
