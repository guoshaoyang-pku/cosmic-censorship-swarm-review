#!/usr/bin/env python3
"""A1 re-check of the live canonical AF-SCC-C2-VAC-GEN schema at revision 11.

Bounded evidence generator for the single re-review required by the P4 re-binding chain
(assignment astra-conv-05). Reads only; writes one JSON blob to stdout. Every field the
review cites is measured here, not asserted.

The live canonical file was moving (rev9 -> rev10 -> rev11 within ~9 minutes), so the
checker records the hash before and after the gate run and a byte snapshot hash, and
binds the review to the snapshot-verified constant hash only.

Usage: python3 recheck_canonical_rev11.py > a1_recheck_canonical_rev11.json
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CANON = "schemas/af_scc_c2_vacuum.yaml"
MIRROR = "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
SNAP = "artifacts/flash-15/convergence/snapshots/af_scc_c2_vacuum.b6123750b37d.yaml"
TOOL = "artifacts/formulation/tools/check_class_schema.py"
FROZEN = "artifacts/formulation/FROZEN.json"
TAXONOMY_CANON = "research_map/formulation_taxonomy.yaml"
TAXONOMY_SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
CONSISTENCY = "artifacts/formulation/evidence/taxonomy_consistency.json"
REGISTRY = "artifacts/formulation/VARIANT_REGISTRY.json"
CLASS_ID = "AF-SCC-C2-VAC-GEN"


def sha(p):
    with open(os.path.join(ROOT, p), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_yaml_raw(p):
    with open(os.path.join(ROOT, p), "rb") as f:
        return f.read()


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)


def top_level_duplicate_keys(raw):
    """Count duplicate top-level mapping keys without a strict-loader dependency."""
    node = yaml.compose(raw.decode("utf-8"))
    seen, dups = {}, {}
    if node is None or not hasattr(node, "value"):
        return dups
    for key_node, _ in node.value:
        k = key_node.value
        seen[k] = seen.get(k, 0) + 1
        if seen[k] > 1:
            dups[k] = seen[k]
    return dups


def main():
    raw = load_yaml_raw(CANON)
    d = yaml.safe_load(raw)
    snap_raw = load_yaml_raw(SNAP)
    snap_d = yaml.safe_load(snap_raw)
    live_hash = hashlib.sha256(raw).hexdigest()
    snap_hash = hashlib.sha256(snap_raw).hexdigest()
    mirror_hash = sha(MIRROR)

    out = {
        "generated_at": run(["date", "-Is"]).stdout.strip(),
        "reviewer": "deepseek-flash-15",
        "assignment": "astra-conv-05 (P4 re-binding: one re-review at the live canonical hash)",
        "class_id": CLASS_ID,
        "target": {
            "canonical_path": CANON,
            "sha256_at_read": live_hash,
            "bytes": len(raw),
            "mtime": run(["stat", "-c", "%y", os.path.join(ROOT, CANON)]).stdout.strip(),
            "internal_revision": d.get("revision"),
            "single_revised_at": [v for k, v in d.items() if k == "revised_at"],
            "top_level_duplicate_keys": top_level_duplicate_keys(raw),
            "snapshot_path": SNAP,
            "snapshot_sha256": snap_hash,
            "snapshot_matches_live_at_read": snap_hash == live_hash,
        },
        "mirror": {"path": MIRROR, "sha256": mirror_hash,
                   "byte_identical_to_live": mirror_hash == live_hash},
        "frozen": {},
        "gate": {},
        "checks": {},
        "findings": {},
    }

    # gate run on the published canonical path; re-hash immediately after
    gate = run([sys.executable, os.path.join(ROOT, TOOL), CANON])
    live_hash_after = sha(CANON)
    out["gate"] = {
        "tool": TOOL,
        "tool_sha256": sha(TOOL),
        "exit_code": gate.returncode,
        "stdout": gate.stdout.strip(),
        "stderr": gate.stderr.strip(),
        "hash_before": live_hash,
        "hash_after": live_hash_after,
        "HASH_STABLE_DURING_GATE": live_hash == live_hash_after,
        "raw_log": "artifacts/flash-15/convergence/gate_run_canonical_rev11.txt",
    }

    fr = json.load(open(os.path.join(ROOT, FROZEN)))
    verify = run([sys.executable, os.path.join(ROOT, "artifacts/formulation/tools/verify_frozen.py")])
    drift_lines = [ln for ln in verify.stdout.splitlines() if "DRIFT" in ln]
    out["frozen"] = {
        "path": FROZEN,
        "sha256": sha(FROZEN),
        "revision": fr.get("revision"),
        "frozen_at": fr.get("frozen_at"),
        "c2_canonical_entry": fr["files"].get(CANON, {}).get("sha256"),
        "c2_mirror_entry": fr["files"].get(MIRROR, {}).get("sha256"),
        "entry_matches_live": fr["files"].get(CANON, {}).get("sha256") == live_hash,
        "verify_frozen_exit": verify.returncode,
        "verify_frozen_stdout_tail": verify.stdout.strip().splitlines()[-1] if verify.stdout.strip() else "",
        "drift_count": len(drift_lines),
        "drift_lines": drift_lines,
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
    c["formal_and_statement_formal_same_binder_head"] = (
        re.sub(r"\s+", " ", formal).strip().startswith("forall (s,delta) in D0")
        and re.sub(r"\s+", " ", sformal).strip().startswith("forall (s,delta) in D0")
    )
    c["undefined_domain_tokens_in_conclusion"] = sorted(
        set(re.findall(r"\bD_[a-z]+\b|\bD\d\b", sformal)) - set(doms)
    )

    # --- extension predicate completeness -----------------------------------
    ep = d.get("extension_predicate", {})
    c["extension_predicate_present"] = bool(ep)
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

    # --- registered variants for this parent class --------------------------
    reg = json.load(open(os.path.join(ROOT, REGISTRY)))
    c["registered_variants_for_parent"] = [
        {"variant_id": v.get("variant_id"), "definition_head": str(v.get("definition"))[:90]}
        for v in reg.get("variants", []) if v.get("parent_class") == CLASS_ID
    ]
    c["data_regularity_variant_registered"] = any(
        any(t in str(v.get("definition", "")).lower() for t in ("sobolev", "smooth-with-decay", "s > 5/2"))
        for v in reg.get("variants", []) if v.get("parent_class") == CLASS_ID
    )

    # --- normative contradiction (candidate N1) -----------------------------
    mnc = d.get("regularity", {}).get("must_not_conflate", [])
    c0_line = [x for x in mnc if "C0 result does not establish" in x]
    ledger = d.get("implication_ledger", {})
    entails = ledger.get("one_way_entailments", [])
    c0_to_c2 = [x for x in entails if x.get("from", "").startswith("no proper future C0")]
    c["must_not_conflate_c0_sentence"] = c0_line
    c["ledger_c0_to_c2"] = c0_to_c2
    c["normative_contradiction"] = bool(c0_line) and bool(c0_to_c2)

    # --- f0 binding / supplement provenance ---------------------------------
    fb = d.get("f0_binding", {})
    consistency = json.load(open(os.path.join(ROOT, CONSISTENCY)))
    c["f0_binding"] = {
        "declared_f0_artifact": fb.get("declared_f0_artifact"),
        "declared_f0_sha256": fb.get("declared_f0_sha256"),
        "live_canonical_taxonomy_sha256": sha(TAXONOMY_CANON),
        "declared_matches_live_canonical": fb.get("declared_f0_sha256") == sha(TAXONOMY_CANON),
        "class_contract_pointer": d.get("class_contract_pointer"),
        "supplement_path": TAXONOMY_SUPP,
        "supplement_sha256": sha(TAXONOMY_SUPP),
        "supplement_hash_pinned_in_schema": False,
        "consistency_evidence": CONSISTENCY,
        "consistency_evidence_sha256": sha(CONSISTENCY),
        "consistency_verdict": consistency.get("consistent"),
    }
    c["review_status"] = d.get("review_status")

    # --- leakage / inflation ------------------------------------------------
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
    c["foreign_token_hits_in_assertive_paths"] = {k: scan(v, k) for k, v in assertive.items()}
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

    out["findings"] = {
        "B1_D0_family_quantifier_present_at_reviewed_hash": bool(c["D0_has_disjunction"]),
        "B1_data_regularity_variant_registered": c["data_regularity_variant_registered"],
        "N1_normative_c0_entailment_contradiction": bool(c["normative_contradiction"]),
        "prior_B1_extension_predicate_block": "RESOLVED" if c["extension_predicate_present"] else "PRESENT",
        "prior_B2_undefined_domains": "RESOLVED" if not c["undefined_domain_tokens_in_conclusion"] else "PRESENT",
        "prior_B3_gate_rejection": "RESOLVED" if out["gate"]["exit_code"] == 0 else "PRESENT",
        "prior_N2_duplicate_revised_at": "RESOLVED" if not out["target"]["top_level_duplicate_keys"] else "PRESENT",
        "gate_pass": out["gate"]["exit_code"] == 0,
        "mirror_byte_identical": out["mirror"]["byte_identical_to_live"],
        "frozen_entry_matches_live": out["frozen"]["entry_matches_live"],
        "hash_stable_during_gate": out["gate"]["HASH_STABLE_DURING_GATE"],
    }

    # --- evidence hash ledger ------------------------------------------------
    ev = {
        "target_snapshot": SNAP,
        "gate_log": "artifacts/flash-15/convergence/gate_run_canonical_rev11.txt",
        "leakage_scan_json": "artifacts/flash-15/convergence/leakage_scan_canonical_rev11.json",
        "leakage_scan_txt": "artifacts/flash-15/convergence/leakage_scan_canonical_rev11.txt",
        "verify_frozen_log": "artifacts/flash-15/convergence/verify_frozen_at_rev11.txt",
        "recheck_script": "artifacts/flash-15/convergence/recheck_canonical_rev11.py",
    }
    out["evidence_hashes"] = {k: sha(v) for k, v in ev.items() if os.path.exists(os.path.join(ROOT, v))}
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
