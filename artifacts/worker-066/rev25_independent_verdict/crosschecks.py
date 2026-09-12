#!/usr/bin/env python3
"""W066-REV25-VERDICT-01 step 3: independent cross-checks the acceptance pipeline does not run.

Checks (all against pinned/ bytes, all deterministic):
  C1 pin integrity            every pinned file re-hashes to the snapshot manifest
  C2 frozen-manifest audit    every file declared by FROZEN rev25 matches disk
  C3 dual-tree equality       canonical vs authoring copies of the three schemas
  C4 frozen-four token census class-id fields in schemas/taxonomy/registry
  C5 conclusion vocabularies  rule_spec vs map-F0 vs authoring-F0 vs schema vs rubric
  C6 f0_binding exactness     each schema's declared_f0_sha256 == FROZEN F0 hash
  C7 duplicate YAML keys      yaml.compose level; records every duplicate with line numbers
  C8 internal contradictions  C0 must_not_conflate vs implication_ledger (line-anchored)
  C9 variant registry shape   required keys / frozen parents / uniqueness
  C10 rule-declaration gap    rule ids enforced by the gate vs declared in rule_spec
  C11 acceptance replication  summary of run_replica.py output vs the frozen report
  C12 rubric vocabulary        A0 conclusion_primary / genericity tokens vs rule_spec
Output: evidence/crosschecks.json
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
PINNED = HERE / "pinned"
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dup_keys(path: Path) -> list:
    """Return duplicate mapping keys with first/last 1-based line numbers (PyYAML compose,
    which keeps every key node; safe_load would silently last-win)."""
    node = yaml.compose(path.read_text())
    found = []

    def walk(n, where):
        if isinstance(n, yaml.MappingNode):
            seen = {}
            for k, v in n.value:
                key = str(k.value)
                line = k.start_mark.line + 1
                if key in seen:
                    found.append({"path": where, "key": key, "first_line": seen[key], "dup_line": line})
                else:
                    seen[key] = line
                walk(v, f"{where}.{key}")
        elif isinstance(n, yaml.SequenceNode):
            for i, item in enumerate(n.value):
                walk(item, f"{where}[{i}]")

    walk(node, "$")
    return found


def collect_class_ids(node, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("class_ids", "frozen_classes") and isinstance(v, list):
                out.extend([x for x in v if isinstance(x, str)])
            elif k == "parent_class" and isinstance(v, str):
                out.append(v)
            elif k == "class_id" and isinstance(v, str):
                out.append(v)
            else:
                collect_class_ids(v, out)
    elif isinstance(node, list):
        for x in node:
            collect_class_ids(x, out)
    return out


def main() -> int:
    manifest = json.loads((HERE / "pinned_manifest.json").read_text())
    now = datetime.now(CST)
    out = {"task_id": "W066-REV25-VERDICT-01", "generated_at": now.isoformat(timespec="seconds"),
           "reviewer_wall_clock": now.isoformat(timespec="seconds"), "checks": {}}

    # C1 pin integrity
    mism = [e["pinned"] for e in manifest["targets"] + manifest["gate_relative_copies"]
            if sha(HERE / e["pinned"]) != e["sha256_pinned"]]
    mism += [f"pinned/rebased_fixtures/{c['fixture']}" for c in manifest["corpus"]["fixtures"]
             if sha(PINNED / "rebased_fixtures" / c["fixture"]) != c["sha256_pinned"]]
    out["checks"]["C1_pin_integrity"] = {"ok": not mism, "mismatches": mism,
                                         "pinned_files": len(manifest["targets"]) + len(manifest["gate_relative_copies"])
                                         + len(manifest["corpus"]["fixtures"])}

    # C2 frozen-manifest audit (canonical trees, measured now)
    frozen_now = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    fmiss = []
    for p, meta in frozen_now["files"].items():
        fp = ROOT / p
        if not fp.exists():
            fmiss.append({"path": p, "reason": "missing"})
        elif sha(fp) != meta["sha256"] or (meta.get("bytes") is not None and fp.stat().st_size != meta["bytes"]):
            fmiss.append({"path": p, "reason": "hash/size mismatch", "declared": meta["sha256"],
                          "measured": sha(fp)})
    out["checks"]["C2_frozen_audit"] = {"frozen_revision": frozen_now["revision"],
                                        "frozen_frozen_at": frozen_now["frozen_at"],
                                        "files": len(frozen_now["files"]), "mismatches": fmiss,
                                        "ok": not fmiss}

    # C3 dual-tree equality
    pairs = [(f"schemas/{n}", f"artifacts/formulation/schemas/{n}")
             for n in ("af_wcc_vacuum.yaml", "af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml")]
    out["checks"]["C3_dual_tree"] = {
        "pairs": [{"a": a, "b": b, "a_sha256": sha(ROOT / a), "b_sha256": sha(ROOT / b),
                   "identical": sha(ROOT / a) == sha(ROOT / b)} for a, b in pairs]}

    # C4 frozen-four token census
    census_sources = {
        "schema_wcc": PINNED / "schemas/af_wcc_vacuum.yaml",
        "schema_c2": PINNED / "schemas/af_scc_c2_vacuum.yaml",
        "schema_c0": PINNED / "schemas/af_scc_c0_vacuum.yaml",
        "f0_map_taxonomy": PINNED / "f0/formulation_taxonomy.yaml",
        "variant_registry": PINNED / "f0/VARIANT_REGISTRY.json",
    }
    frozen_four = {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"}
    census = {}
    for name, p in census_sources.items():
        doc = yaml.safe_load(p.read_text()) if p.suffix in (".yaml", ".yml") else json.loads(p.read_text())
        ids = sorted(set(collect_class_ids(doc, [])))
        census[name] = {"ids": ids, "outside_frozen_four": sorted(set(ids) - frozen_four)}
    out["checks"]["C4_frozen_four_census"] = {"sources": census,
                                              "ok": all(not v["outside_frozen_four"] for v in census.values())}

    # C5 conclusion vocabularies
    spec = json.loads((PINNED / "tools/rule_spec.json").read_text())
    map_tax = yaml.safe_load((PINNED / "f0/formulation_taxonomy.yaml").read_text())
    auth_tax = yaml.safe_load((ROOT / "artifacts/formulation/formulation_taxonomy.yaml").read_text())
    rubric = yaml.safe_load((ROOT / "evaluation_rubric.yaml").read_text())
    rubric_ids = {c["id"]: c for c in rubric.get("frozen_classes", [])}
    vocab = {}
    for cid in spec["frozen_classes"]:
        schema_doc = yaml.safe_load((PINNED / "schemas" / {
            "AF-WCC-VAC-GEN": "af_wcc_vacuum.yaml", "AF-SCC-C2-VAC-GEN": "af_scc_c2_vacuum.yaml",
            "AF-SCC-C0-VAC-GEN": "af_scc_c0_vacuum.yaml"}.get(cid, "af_wcc_vacuum.yaml")).read_text())
        vocab[cid] = {
            "rule_spec": spec["vocabularies"]["class_conclusion_type"][cid],
            "schema_conclusion_type": (schema_doc.get("conclusion") or {}).get("conclusion_type") if schema_doc.get("class_id") == cid else None,
            "map_taxonomy_conclusion_type": (map_tax["classes"][cid].get("conclusion") or {}).get("type"),
            "authoring_taxonomy_conclusion_type": auth_tax["class_contracts"][cid].get("conclusion_type"),
            "rubric_conclusion_primary": rubric_ids.get(cid, {}).get("conclusion_primary"),
        }
        vals = {k: v for k, v in vocab[cid].items() if k != "rule_spec"}
        vocab[cid]["raw_unanimous"] = len(set(vals.values())) == 1
    out["checks"]["C5_conclusion_vocabularies"] = {
        "classes": vocab,
        "raw_unanimous_all": all(v["raw_unanimous"] for v in vocab.values()),
        "note": ("rule_spec/schema/authoring agree; map-F0 uses the VOCAB_ALIASES alias; the rubric "
                 "uses a third token set with no declared crosswalk (existing finding: A0-review-22)")}

    # C6 f0_binding exactness
    f0_decl = frozen_now["files"]["research_map/formulation_taxonomy.yaml"]["sha256"]
    bind = {}
    for name in ("af_wcc_vacuum.yaml", "af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml"):
        d = yaml.safe_load((PINNED / "schemas" / name).read_text())
        fb = d.get("f0_binding") or {}
        bind[name] = {"declared_f0_sha256": fb.get("declared_f0_sha256"),
                      "declared_f0_artifact": fb.get("declared_f0_artifact"),
                      "class_contract_supplement": fb.get("class_contract_supplement"),
                      "matches_frozen_f0": fb.get("declared_f0_sha256") == f0_decl}
    out["checks"]["C6_f0_binding"] = {"frozen_f0_sha256": f0_decl, "schemas": bind,
                                      "ok": all(v["matches_frozen_f0"] for v in bind.values())}

    # C7 duplicate YAML keys
    dups = {}
    for name in ("schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"):
        dups[name] = dup_keys(PINNED / name)
    dups["f0/formulation_taxonomy.yaml"] = dup_keys(PINNED / "f0/formulation_taxonomy.yaml")
    out["checks"]["C7_duplicate_yaml_keys"] = {"files": dups,
                                               "ok": all(len(v) == 0 for v in dups.values())}

    # C8 internal contradictions (line-anchored, C0)
    c0_lines = (PINNED / "schemas/af_scc_c0_vacuum.yaml").read_text().splitlines()
    c2_lines = (PINNED / "schemas/af_scc_c2_vacuum.yaml").read_text().splitlines()
    hits = {"c0_no_containment": None, "c0_containment_chain": None, "c2_corrected": None,
            "c2_scope_order_note": None}
    for i, line in enumerate(c0_lines, 1):
        if "No containment with C2 or C0 is asserted here" in line:
            hits["c0_no_containment"] = {"line": i, "text": line.strip()[:200]}
        if "extension_class_containment" in line:
            hits["c0_containment_chain"] = {"line": i, "text": line.strip()[:200]}
    for i, line in enumerate(c2_lines, 1):
        if "H2_loc-inextendibility ENTAILS this class" in line:
            hits["c2_corrected"] = {"line": i, "text": line.strip()[:200]}
    contradiction = bool(hits["c0_no_containment"] and hits["c0_containment_chain"])
    out["checks"]["C8_internal_contradiction_c0"] = {
        "hits": hits, "contradiction": contradiction,
        "detail": ("C0 :157 denies any containment with C2/C0 for H2_loc while C0 :244 asserts "
                   "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2; C2 :157 states the "
                   "corrected opposite and records that the earlier 'no containment' wording was wrong.")}

    # C9 variant registry shape
    reg = json.loads((PINNED / "f0/VARIANT_REGISTRY.json").read_text())
    req = ("parent_class", "variant_id", "definition", "evidence", "status")
    reg_errs = []
    parents = [p.get("class_id") for p in reg.get("parent_classes", [])]
    if set(parents) != frozen_four:
        reg_errs.append(f"parent_classes != frozen four: {parents}")
    seen = set()
    for v in reg.get("variants", []):
        for k in req:
            if not v.get(k):
                reg_errs.append(f"{v.get('parent_class')}/{v.get('variant_id')}: missing {k}")
        if v.get("parent_class") not in frozen_four:
            reg_errs.append(f"{v.get('variant_id')}: parent outside frozen four")
        if (v.get("parent_class"), v.get("variant_id")) in seen:
            reg_errs.append(f"duplicate {v.get('parent_class')}/{v.get('variant_id')}")
        seen.add((v.get("parent_class"), v.get("variant_id")))
        if not v.get("falsifier"):
            reg_errs.append(f"{v.get('variant_id')}: missing falsifier")
        if not v.get("why_separate"):
            reg_errs.append(f"{v.get('variant_id')}: missing why_separate")
    inline_variants = sorted({(v.get("parent_class"), v.get("variant_id")) for v in map_tax.get("variants", [])})
    out["checks"]["C9_variant_registry"] = {
        "version": reg.get("version"), "parents": parents, "variant_count": len(reg.get("variants", [])),
        "errors": reg_errs, "ok": not reg_errs,
        "canonical_f0_inline_variants": [f"{p}/{v}" for p, v in inline_variants],
        "registry_variants": sorted(f"{v.get('parent_class')}/{v.get('variant_id')}" for v in reg.get("variants", [])),
        "divergence": sorted(f"{v.get('parent_class')}/{v.get('variant_id')}" for v in reg.get("variants", []))
                      != sorted(f"{p}/{v}" for p, v in inline_variants)}

    # C10 rule-declaration gap
    gate_src = (PINNED / "tools/check_class_schema.py").read_text()
    enforced = sorted(set(re.findall(r'self\.fail\("(R\d\d)"', gate_src)))
    declared = [r.get("id") for r in spec.get("rules", [])]
    undeclared = sorted(set(enforced) - set(declared))
    gate_report = json.loads((ROOT / "artifacts/formulation/evidence/gate_test_report.json").read_text())
    report_rules = sorted(set(re.findall(r"R\d\d", json.dumps(gate_report))))
    out["checks"]["C10_rule_declaration_gap"] = {
        "rule_spec_version": spec.get("spec_version"), "rule_spec_rules": declared,
        "gate_enforced_rules": enforced, "undeclared_in_spec": undeclared,
        "gate_test_report_rules": report_rules,
        "spec_claim_in_manifest": next((s for s in frozen_now.get("rev7_delta", []) if "rule_spec v1.3" in s), None),
        "deliverable_claim": "artifacts/formulation/DELIVERABLE_SUMMARY.md:22 'rule_spec.json v1.3 (R01-R31)'",
        "ok": not undeclared,
    }

    # C11 acceptance replication summary
    rep = json.loads((HERE / "evidence/replica_verdicts.json").read_text())
    comp = json.loads((HERE / "evidence/acceptance_comparison.json").read_text())
    out["checks"]["C11_acceptance_replication"] = {
        "replica_verdict": rep["verdict"], "aggregates": rep["aggregates"],
        "canonical_ok": all(r["structural_pass"] and r["semantic_accept"] for r in rep["canonical"]),
        "controls_ok": all(r["structural_pass"] and r["semantic_accept"] for r in rep["controls"]),
        "agreement_with_frozen_report": comp["overall_agree"], "ok": rep["verdict"] == "PASS" and comp["overall_agree"]}

    # C12 rubric vocabulary
    rub = {}
    for cid, c in rubric_ids.items():
        rub[cid] = {"conclusion_primary": c.get("conclusion_primary"),
                    "rule_spec_token": spec["vocabularies"]["class_conclusion_type"].get(cid),
                    "match": c.get("conclusion_primary") == spec["vocabularies"]["class_conclusion_type"].get(cid)}
    gen_rubric = None
    for g in rubric.get("gates", []):
        if g.get("id") == "G-FORM":
            for crit in g.get("criteria", []):
                if "genericity type named" in crit:
                    gen_rubric = crit
    out["checks"]["C12_rubric_vocabulary"] = {
        "classes": rub, "all_match": all(v["match"] for v in rub.values()),
        "genericity_criterion": gen_rubric,
        "schema_genericity_kinds": {n: (yaml.safe_load((PINNED / "schemas" / n).read_text()).get("genericity") or {}).get("kind")
                                    for n in ("af_wcc_vacuum.yaml", "af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml")},
        "ok": all(v["match"] for v in rub.values()),
    }

    out["summary"] = {k: v.get("ok", None) for k, v in out["checks"].items()}
    (HERE / "evidence/crosschecks.json").write_text(json.dumps(out, indent=2) + "\n")
    for k, v in out["summary"].items():
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
