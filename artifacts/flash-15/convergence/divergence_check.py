#!/usr/bin/env python3
"""P2 convergence evidence for reviews/convergence-15.json (worker 15 / deepseek-flash-15).

Mechanically records, at a fixed moment:
  1. the published canonical target hash (schemas/af_scc_c2_vacuum.yaml) and the frozen
     manifest entry for AF-SCC-C2-VAC-GEN (FROZEN.json rev19),
  2. the frozen gate tool verdict on each of the two files (raw stdout also written to disk),
  3. presence/absence of each B finding raised in this review, re-checked on the reviewed hash,
  4. resolution status of the nine hard failures raised by the same reviewer in the prior round
     (reviews/F2a-review-15.json) on the reviewed hash.

Read-only with respect to every canonical artifact. Writes only under artifacts/flash-15/.
Usage: python3 divergence_check.py   (prints JSON to stdout)
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/flash-15/convergence"
CST = timezone(timedelta(hours=8))

CANON = ROOT / "schemas/af_scc_c2_vacuum.yaml"
FROZEN = ROOT / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
MANIFEST = ROOT / "artifacts/formulation/FROZEN.json"
GATE = ROOT / "artifacts/formulation/tools/check_class_schema.py"
RULE_SPEC = ROOT / "artifacts/formulation/rule_spec.json"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p: Path):
    return yaml.safe_load(p.read_text())


def gate_run(target: Path, log_name: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(GATE), str(target)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    (OUT / log_name).write_text(proc.stdout + proc.stderr)
    rules = []
    for line in (proc.stdout + proc.stderr).splitlines():
        line = line.strip()
        if line.startswith("R") and ":" in line:
            rules.append(line.split(":", 1)[0])
    return {
        "target": str(target.relative_to(ROOT)),
        "exit_code": proc.returncode,
        "failed_rules": rules,
        "raw_log": f"artifacts/flash-15/convergence/{log_name}",
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    canon, frozen = load(CANON), load(FROZEN)
    manifest = json.loads(MANIFEST.read_text())
    c2_key = "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
    c2_manifest = manifest["files"][c2_key]

    # --- B findings on the reviewed hash ---------------------------------------------
    q = canon["quantifiers"]
    b_checks = {
        "B1_extension_predicate_block_absent": {
            "referenced_at_lines": [76, 209],
            "key_present": "extension_predicate" in canon,
            "occurrences_in_text": CANON.read_text().count("extension_predicate"),
        },
        "B2_undefined_domains_in_statement_formal": {
            "statement_formal": canon["conclusion"]["statement_formal"],
            "quantifiers_formal": q["formal"],
            "defined_domain_keys": sorted(q["domains"].keys()),
            "uses_D0": "D0" in canon["conclusion"]["statement_formal"],
            "uses_D_gen_superscript": "D_gen^" in canon["conclusion"]["statement_formal"],
            "D0_defined": "D0" in q["domains"],
            "D_gen_defined_in_quantifiers": "D_gen" in q["domains"],
        },
        "B3_frozen_gate_rejects_reviewed_hash": gate_run(CANON, "gate_run_canonical_rev3.txt"),
        "B5_frozen_revision_reintroduces_family_quantifier": {
            "frozen_path": c2_key,
            "frozen_sha256": sha256(FROZEN),
            "frozen_quantifiers_formal": frozen["quantifiers"]["formal"],
            "frozen_D0_definition": frozen["quantifiers"]["domains"]["D0"]["definition"],
            "frozen_gate_verdict": gate_run(FROZEN, "gate_run_frozen_rev8.txt"),
        },
    }

    # --- prior-round HF resolution on the reviewed hash -------------------------------
    prior = {
        "HF-1_quantifiers_ordered": "ordered" in q and bool(q["ordered"]),
        "HF-2_topology_complete": all(
            k in canon["topology"] for k in ("spacetime_dimension", "slice_topology",
                                             "conformal_boundary", "forbidden")
        ),
        "HF-3_regularity_block": "regularity" in canon and "must_not_conflate" in canon["regularity"],
        "HF-4_genericity_canonical_keys": all(
            k in canon["genericity"] for k in ("ambient_space", "topology_or_measure",
                                               "generic_set", "excluded_set",
                                               "transfer_failures", "is_part_of_class")
        ),
        "HF-5_conclusion_type_matches_vocabulary": (
            canon["conclusion"]["conclusion_type"]
            == canon["vocabulary_alignment"]["conclusion_type"]
            == "scc_c2_future_inextendibility"
        ),
        "HF-6_i_plus_and_visibility_roles": (
            canon["i_plus"]["role"] == "assumption"
            and canon["i_plus"]["in_conclusion"] is False
            and canon["visibility"]["role"] == "not_in_conclusion"
        ),
        "HF-7_tier1_tier2_falsifier": "tier_1" in canon["falsifier"] and "tier_2" in canon["falsifier"],
        "HF-8_provenance_and_implication_ledger": (
            "citation_status" in canon["provenance"] and "implication_ledger" in canon
        ),
        "HF-9_identity_block": (
            canon.get("artifact_kind") == "class_schema"
            and "owner" in canon
            and all(k in canon.get("class_components", {}) for k in
                    ("asymptotics", "censorship", "matter", "genericity", "regularity_token"))
        ),
    }

    # --- hash / path divergence --------------------------------------------------------
    evidence = {
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "reviewer": "deepseek-flash-15",
        "assignment": "astra-conv-05",
        "target_class": "AF-SCC-C2-VAC-GEN",
        "published_canonical": {
            "path": "schemas/af_scc_c2_vacuum.yaml",
            "sha256": sha256(CANON),
            "bytes": CANON.stat().st_size,
            "internal_revision": canon.get("revision"),
            "contract_spec_version": canon.get("contract_binding", {}).get("spec_version"),
        },
        "frozen_manifest_entry": {
            "path": c2_key,
            "sha256": sha256(FROZEN),
            "manifest_sha256": c2_manifest["sha256"],
            "bytes": FROZEN.stat().st_size,
            "internal_revision": frozen.get("revision"),
            "manifest_revision": manifest["revision"],
            "match": sha256(FROZEN) == c2_manifest["sha256"],
        },
        "divergence": {
            "same_artifact": sha256(CANON) == sha256(FROZEN),
            "canonical_covers_frozen": sha256(CANON) == c2_manifest["sha256"],
            "path_rule": "P5: canonical paths stay schemas/ + research_map/; authoring tree mirrors at publish",
        },
        "gate_tool": {
            "path": "artifacts/formulation/tools/check_class_schema.py",
            "sha256": sha256(GATE),
            "rule_spec_sha256": sha256(RULE_SPEC),
        },
        "b_findings": b_checks,
        "prior_round_HF_resolution_on_reviewed_hash": prior,
        "prior_round_HF_resolved_count": sum(1 for v in prior.values() if v),
        "prior_round_HF_total": len(prior),
    }
    (OUT / "divergence_check.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
