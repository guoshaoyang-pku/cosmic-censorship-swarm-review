#!/usr/bin/env python3
"""A1 re-check of the live canonical AF-SCC-C2-VAC-GEN schema at rev9.

Bounded evidence generator for the single re-review required by the P4 re-binding
notice (assignment astra-conv-05). Reads only; writes one JSON blob to stdout.

Usage: python3 recheck_canonical_rev9.py > a1_recheck_canonical_rev9.json
"""
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CANON = "schemas/af_scc_c2_vacuum.yaml"
MIRROR = "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
TOOL = "artifacts/formulation/tools/check_class_schema.py"
FROZEN = "artifacts/formulation/FROZEN.json"
CLASS_ID = "AF-SCC-C2-VAC-GEN"


def sha(p):
    with open(os.path.join(ROOT, p), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_yaml(p):
    import yaml
    with open(os.path.join(ROOT, p)) as f:
        return yaml.safe_load(f)


def main():
    import yaml  # noqa: F401  (fail loudly if the parser is missing)

    raw = open(os.path.join(ROOT, CANON), "rb").read()
    d = yaml.safe_load(raw)
    out = {
        "generated_at": subprocess.run(["date", "-Is"], capture_output=True, text=True).stdout.strip(),
        "reviewer": "deepseek-flash-15",
        "assignment": "astra-conv-05 (P4 re-binding: one re-review at the live canonical hash)",
        "class_id": CLASS_ID,
        "target": {
            "canonical_path": CANON,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "mtime": subprocess.run(["stat", "-c", "%y", os.path.join(ROOT, CANON)],
                                    capture_output=True, text=True).stdout.strip(),
            "internal_revision": d.get("revision"),
            "declared_revised_at": [v for k, v in d.items() if k == "revised_at"],
        },
        "mirror": {"path": MIRROR, "sha256": sha(MIRROR)},
        "frozen": {},
        "gate": {},
        "checks": {},
        "findings": {},
    }
    out["mirror"]["byte_identical"] = out["mirror"]["sha256"] == out["target"]["sha256"]

    fr = json.load(open(os.path.join(ROOT, FROZEN)))
    out["frozen"] = {
        "path": FROZEN,
        "sha256": sha(FROZEN),
        "revision": fr.get("revision"),
        "frozen_at": fr.get("frozen_at"),
        "c2_canonical_entry": fr["files"].get(CANON, {}).get("sha256"),
        "c2_mirror_entry": fr["files"].get(MIRROR, {}).get("sha256"),
        "c2_bound": fr["files"].get(CANON, {}).get("sha256") == out["target"]["sha256"]
        and fr["files"].get(MIRROR, {}).get("sha256") == out["target"]["sha256"],
    }

    tool_hash = sha(TOOL)
    proc = subprocess.run([sys.executable, os.path.join(ROOT, TOOL), CANON],
                          capture_output=True, text=True, cwd=ROOT)
    out["gate"] = {
        "tool": TOOL,
        "tool_sha256": tool_hash,
        "exit_code": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "raw_log": "artifacts/flash-15/convergence/gate_run_canonical_rev9_a1.txt",
    }

    c = out["checks"]
    # --- quantifier / domain resolution -------------------------------------
    q = d.get("quantifiers", {})
    ordered = q.get("ordered", [])
    doms = q.get("domains", {})
    used = [e.get("domain_id") for e in ordered]
    c["ordered_domain_ids_resolve"] = {k: (k in doms) for k in used}
    c["all_domains_resolve"] = all(c["ordered_domain_ids_resolve"].values())
    formal = q.get("formal", "")
    concl = d.get("conclusion", {})
    sformal = concl.get("statement_formal", "")
    c["statement_formal"] = sformal
    c["quantifiers_formal"] = formal
    c["formal_and_statement_formal_same_structure"] = (
        re.sub(r"\s+", " ", formal).strip().startswith("forall (s,delta) in D0")
        and re.sub(r"\s+", " ", sformal).strip().startswith("forall (s,delta) in D0")
    )
    c["undefined_domain_tokens_in_conclusion"] = sorted(
        set(re.findall(r"\bD_[a-z]+\b|\bD\d\b", sformal)) - set(doms)
    )

    # --- extension predicate completeness -----------------------------------
    ep = d.get("extension_predicate", {})
    c["extension_predicate_present"] = bool(ep)
    c["extension_predicate_keys"] = sorted(ep.keys()) if isinstance(ep, dict) else None
    c["extension_predicate_required_subkeys"] = {
        k: (k in ep) for k in ["name", "frozen_regularity", "frozen_equation_concept",
                               "frozen_direction", "definition", "must_not_conflate"]
    }
    defn = ep.get("definition", "") if isinstance(ep, dict) else ""
    c["extension_predicate_clauses"] = {f"({x})": (f"({x})" in defn) for x in "abcdef"}

    # --- D0 family census (candidate B1) ------------------------------------
    d0 = doms.get("D0", {}).get("definition", "")
    data_reg = d.get("regularity", {}).get("data_regularity", "")
    amb = d.get("genericity", {}).get("ambient_space", "")
    top = d.get("genericity", {}).get("topology_or_measure", "")
    c["D0_definition"] = d0
    c["D0_has_disjunction"] = " or " in d0
    c["D0_disjuncts"] = [s.strip() for s in d0.split(" or ")] if " or " in d0 else []
    c["data_regularity_field"] = data_reg
    c["data_regularity_disjunctive"] = " or " in data_reg
    c["ambient_topologies_named"] = {
        "weighted_sobolev_product": "weighted Sobolev product" in amb,
        "frechet_smooth": "Frechet topology" in top,
    }
    c["genericity_is_part_of_class"] = d.get("genericity", {}).get("is_part_of_class")

    # --- normative contradiction (candidate B2) -----------------------------
    mnc = d.get("regularity", {}).get("must_not_conflate", [])
    c0_line = [x for x in mnc if "C0 result does not establish" in x]
    ledger = d.get("implication_ledger", {})
    entails = ledger.get("one_way_entailments", [])
    c0_to_c2 = [x for x in entails if x.get("from", "").startswith("no proper future C0")]
    c["must_not_conflate_c0_sentence"] = c0_line
    c["ledger_c0_to_c2"] = c0_to_c2
    c["normative_contradiction"] = bool(c0_line) and bool(c0_to_c2)

    # --- leakage / inflation -------------------------------------------------
    def scan(obj, path=""):
        hits = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                hits += scan(v, f"{path}.{k}" if path else str(k))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                hits += scan(v, f"{path}[{i}]")
        elif isinstance(obj, str):
            for tok in ["WCC", "visible", "visibility", "predictab", "H2_loc", "C^{1,1}", "C1 ", "C0"]:
                if tok.lower() in obj.lower():
                    hits.append({"path": path, "token": tok, "text": obj[:160]})
        return hits
    assertive = {
        "quantifiers.formal": formal,
        "conclusion.statement_natural_language": concl.get("statement_natural_language", ""),
        "conclusion.statement_formal": sformal,
        "conclusion.conclusion_type": concl.get("conclusion_type", ""),
        "falsifier.tier_1": d.get("falsifier", {}).get("tier_1", {}),
        "falsifier.tier_2": d.get("falsifier", {}).get("tier_2", {}),
        "topology": d.get("topology", {}),
    }
    c["foreign_token_hits_in_assertive_paths"] = {
        k: scan(v, k) for k, v in assertive.items()
    }
    c["conclusion_type"] = concl.get("conclusion_type")
    c["i_plus_role"] = d.get("i_plus", {}).get("role")
    c["i_plus_in_conclusion"] = d.get("i_plus", {}).get("in_conclusion")
    c["visibility_role"] = d.get("visibility", {}).get("role")

    # --- falsifier decidability ---------------------------------------------
    f1 = d.get("falsifier", {}).get("tier_1", {})
    f2 = d.get("falsifier", {}).get("tier_2", {})
    c["falsifier"] = {
        "tier_1_refutes": f1.get("refutes"),
        "tier_1_has_genericity_requirement": bool(f1.get("genericity_requirement")),
        "tier_1_machine_checkable_steps": f1.get("machine_checkable_steps", []),
        "tier_1_non_machine_checkable_step": f1.get("non_machine_checkable_step"),
        "tier_2_refutes": f2.get("refutes"),
        "tier_2_labelling": f2.get("labelling_required"),
    }

    # --- binding / bookkeeping ----------------------------------------------
    fb = d.get("f0_binding", {})
    live_f0 = {"canonical": sha("research_map/formulation_taxonomy.yaml"),
               "authoring": sha("artifacts/formulation/formulation_taxonomy.yaml")}
    c["f0_binding"] = {
        "declared_sha256": fb.get("declared_f0_sha256"),
        "live_f0": live_f0,
        "declared_resolves": fb.get("declared_f0_sha256") in live_f0.values(),
        "class_contract_pointer": d.get("class_contract_pointer"),
        "pointer_is_authoring_mirror": str(d.get("class_contract_pointer", "")).startswith(
            "artifacts/formulation/"),
    }
    c["review_status"] = d.get("review_status")
    m = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", str(out["target"]["declared_revised_at"]))
    c["timestamp"] = {"declared_revised_at": m.group(1) if m else None,
                      "file_mtime": out["target"]["mtime"]}

    # --- finding disposition -------------------------------------------------
    out["findings"] = {
        "B1_D0_family_quantifier_present_at_reviewed_hash": bool(c["D0_has_disjunction"]),
        "B2_normative_c0_entailment_contradiction": bool(c["normative_contradiction"]),
        "prior_B1_extension_predicate_block": "RESOLVED" if c["extension_predicate_present"] else "PRESENT",
        "prior_B2_undefined_domains": "RESOLVED" if not c["undefined_domain_tokens_in_conclusion"] else "PRESENT",
        "prior_B3_gate_rejection": "RESOLVED" if out["gate"]["exit_code"] == 0 else "PRESENT",
        "gate_pass": out["gate"]["exit_code"] == 0,
        "mirror_and_frozen_bound": out["mirror"]["byte_identical"] and out["frozen"]["c2_bound"],
    }
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
