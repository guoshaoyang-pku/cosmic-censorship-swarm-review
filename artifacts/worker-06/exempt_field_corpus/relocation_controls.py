#!/usr/bin/env python3
"""FORM-EXEMPT-09 leak-criterion validation (worker-06) -- POST-HOC control.

Purpose: the FORM-EXEMPT-09 report claims the 18 injected sentences are real
class-contract leaks that escape only because their field is unscanned/exempt.
This control re-locates each sentence into a field that IS scanned by the
canonical gate. If the relocated sentence is caught, the leak criterion is
confirmed and the escape is attributable to the exempt field. If it is NOT
caught even in a scanned field, the family is a gate gap (R12/R15/R28 narrower
than the rule_spec text), which is reported as such.

Run AFTER the main corpus measurement; it does not modify the main manifest or
report. Its own manifest is hashed before its run.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml

import make_corpus as mc

OUT = Path(__file__).resolve().parent
FIX = OUT / "relocation_fixtures"
ROOT = mc.ROOT
GATE = ROOT / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
AUDITOR = ROOT / "artifacts" / "worker-06" / "spec_conformance_audit.py"

# name, base, target path (scanned), source mutant whose text is re-located,
# expected: "caught" | "probe" (uncertain), expected_rule_or_reason
CASES = [
    ("r01_wcc_text_in_conclusion", "c0", "conclusion.statement_natural_language",
     "m01_c0_wcc_in_visibility_reason", "caught", "R12 foreign WCC token in an assertive path"),
    ("r02_merge_text_in_conclusion", "c0", "conclusion.statement_natural_language",
     "m03_c0_merged_regularity_warning", "caught", "R13 composite regularity"),
    ("r03_c2_sibling_in_ep_definition", "c2", "extension_predicate.definition",
     "m05_c2_sibling_regularity_why", "caught", "R31 foreign regularity in extension_predicate"),
    ("r04_c0_sibling_in_ep_definition", "c0", "extension_predicate.definition",
     "m06_c0_sibling_regularity_why", "caught", "R31 foreign regularity in extension_predicate"),
    ("r05_curvature_in_nonvacuity_condition", "c0", "non_vacuity.condition",
     "m07_c0_curvature_hypothesis_falsifier", "caught", "R29 C0 curvature hypothesis"),
    ("r06_theorem_in_conclusion", "c0", "conclusion.statement_natural_language",
     "m08_c0_theorem_promotion_provenance", "caught", "R20 theorem promotion"),
    ("r07_iplus_complete_in_iplus_definition", "c0", "i_plus.definition",
     "m10_c0_iplus_completeness_reason", "caught", "R09 SCC completeness assertion"),
    ("r08_two_ends_in_slice_topology", "c0", "topology.slice_topology",
     "m12_c0_multi_end_development", "caught", "R04 two/multiple ends in slice_topology"),
    ("r09_foreign_in_conclusion", "c0", "conclusion.statement_natural_language",
     "m13_c0_foreign_in_extensions", "caught", "R12 foreign SCC-family token"),
    ("r10_scc_text_in_wcc_visibility", "wcc", "visibility.definition",
     "m15_wcc_scc_inextendibility_warning", "caught", "R12 INEXTENDIB_NON_GEODESIC"),
    ("r11_kind_substitution_field", "c0", "genericity.kind",
     "m17_c0_kind_substitution_warning", "caught", "R21 frozen genericity kind"),
    ("r12_matter_text_in_conclusion", "c0", "conclusion.statement_natural_language",
     "m11_c0_matter_in_gauge", "probe", "R12 has no implemented matter/asymptotic token"),
    ("r13_transfer_text_in_conclusion", "c2", "conclusion.statement_natural_language",
     "m14_c2_transfer_inversion_falsifier", "probe", "R28 scans transfer row containers only"),
    ("r14_overclaim_in_source_concept", "c0", "provenance.sources[0].concept",
     "m18_c0_source_overclaim_subsumption", "probe", "R15 regex may be narrower than the spec"),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    FIX.mkdir(parents=True, exist_ok=True)
    for old in FIX.glob("*.yaml"):
        old.unlink()
    main_manifest = json.loads((OUT / "manifest.json").read_text())
    texts = {m["name"]: m["injected_text"] for m in main_manifest["fixtures"] if m["kind"] == "mutant"}

    base_docs = {}
    for key, meta in mc.BASES.items():
        base_docs[key] = yaml.safe_load((mc.CANON / meta["file"]).read_bytes())

    entries = []
    for name, base, path, src, expected, why in CASES:
        doc = yaml.safe_load(mc.dump_yaml(base_docs[base]))
        mc.set_path(doc, path, texts[src])
        text = mc.dump_yaml(doc)
        (FIX / f"{name}.yaml").write_text(text)
        entries.append({"name": name, "base": base, "target_field": path,
                        "source_mutant": src, "injected_text": texts[src],
                        "expected": expected, "expected_rule_or_reason": why,
                        "file": f"relocation_fixtures/{name}.yaml",
                        "sha256": sha(FIX / f"{name}.yaml")})
    mbody = json.dumps({"artifact": "FORM-EXEMPT-09-RELOCATION-MANIFEST", "owner": "worker-06",
                        "note": ("post-hoc leak-criterion control; written after the main run, "
                                 "before this control run; main corpus manifest/hash unchanged"),
                        "cases": entries}, indent=2, ensure_ascii=False) + "\n"
    (OUT / "relocation_manifest.json").write_text(mbody)
    (OUT / "relocation_manifest.sha256").write_text(sha(OUT / "relocation_manifest.json") + "  relocation_manifest.json\n")

    rows = []
    for e in entries:
        p = OUT / e["file"]
        proc = subprocess.run([sys.executable, str(GATE), "--json", str(p)], capture_output=True, text=True)
        rep = json.loads(proc.stdout)
        caught = rep["verdict"] == "fail"
        row = dict(e)
        row.update({"structural_verdict": rep["verdict"], "structural_failed_rules": rep["failed_rules"],
                    "structural_caught": caught,
                    "criterion": ("confirmed" if caught else
                                  ("gate_gap" if e["expected"] == "probe" else "CRITERION_FAILED"))})
        rows.append(row)

    confirmed = sum(1 for r in rows if r["criterion"] == "confirmed")
    gaps = [r["name"] for r in rows if r["criterion"] == "gate_gap"]
    crit_fail = [r["name"] for r in rows if r["criterion"] == "CRITERION_FAILED"]
    report = {"artifact": "FORM-EXEMPT-09-RELOCATION-REPORT", "owner": "worker-06",
              "gate_sha256": sha(GATE), "manifest_sha256": sha(OUT / "relocation_manifest.json"),
              "criterion_confirmed": confirmed, "n_cases": len(rows),
              "gate_gaps": gaps, "criterion_failed": crit_fail,
              "note": ("a CRITERION_FAILED row means the injected sentence was expected to be caught in a "
                       "scanned field but was not; the family's escape is then a gate gap, not an exempt-field "
                       "artifact, and is reported as such"),
              "cases": rows}
    body = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    (OUT / "relocation_report.json").write_text(body)
    print(json.dumps({"report_sha256": hashlib.sha256(body.encode()).hexdigest(),
                      "criterion_confirmed": confirmed, "n_cases": len(rows),
                      "gate_gaps": gaps, "criterion_failed": crit_fail,
                      "rows": [{r["name"]: (r["structural_verdict"], r["structural_failed_rules"])} for r in rows]},
                     indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
