#!/usr/bin/env python3
"""F0/G-F0 corpus rebind compatibility check: canonical taxonomy vs frozen authoring tree.

Assignment : asg-2026-09-11-F0-deepseek-flash-02-11 (node F0, gate G-F0, actor deepseek-flash-02)
Artifact   : schemas/taxonomy_cases.jsonl (pinned to research_map/formulation_taxonomy.yaml)
Purpose    : astra-pathpol-00 will copy the frozen authoring tree
             (artifacts/formulation/) onto the canonical paths. The frozen taxonomy uses a
             different container shape and different axis-value tokens than canonical rev3.
             This script answers one bounded question with controls:

               Does the F0 corpus still verify if the frozen revision is published,
                and under exactly which token map?

It does NOT edit any canonical artifact. It writes a machine-checkable report only.

Measured facts this script is designed to detect (each has a control, so a PASS here is not
vacuous):
  * structural: the existing checker's load_taxonomy() cannot parse the frozen file
    (frozen has class_contracts/axis_registry, canonical checker requires classes/field_vocabulary)
  * lexical   : frozen axis-value tokens differ from canonical vocabulary on >=3 axes
  * precedence: frozen components.genericity is the non-authoritative token "GEN" on all four
    classes, while axis_registry.genericity_axis.frozen is authoritative and says
    AF-WCC-SCALAR-SPH = unresolved (matching canonical). A naive components-first projection
    silently changes the scalar class's genericity.

Falsifier: the projected frozen revision differs from canonical rev3 on any of the 7 corpus axes
for any of the 4 classes, OR the mapped corpus run produces a nonzero error delta against the
canonical baseline. Either outcome refutes "rebind-safe with this token map".

Usage:
  python3 artifacts/flash-02/rebind_frozen_check.py \
      --canonical research_map/formulation_taxonomy.yaml \
      --frozen artifacts/formulation/formulation_taxonomy.yaml \
      --cases schemas/taxonomy_cases.jsonl \
      --catalog artifacts/flash-02/leak_rule_catalog.json \
      --checker artifacts/flash-02/check_taxonomy_cases.py \
      --report artifacts/flash-02/frozen_rebind_report.json
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[2]

AXES = ["family", "matter_model", "symmetry", "asymptotics", "regularity_token",
        "genericity_kind", "conclusion_type"]

# canonical taxonomy document, set by main(); the projection inherits its field_vocabulary
CANONICAL_DOC: dict = {}

# --- documented token maps: frozen-authoring token -> canonical vocabulary value ------------
# Source column is named so a reviewer can check every mapping against the frozen file.
FAMILY = {  # components.censorship -> axes.family
    "WCC": "WCC",
    "SCC": "SCC",
}
MATTER = {  # components.matter -> axes.matter_model
    "VAC": "vacuum",
    "vacuum": "vacuum",
    "massless scalar field": "massless_scalar_field",
    "massless_scalar_field": "massless_scalar_field",
}
ASYMPTOTICS = {  # components.asymptotics -> axes.asymptotics
    "AF": "asymptotically_flat_3p1",
    "asymptotically_flat_3p1": "asymptotically_flat_3p1",
}
REGULARITY = {  # components.regularity_token -> axes.regularity_token (none == null)
    "none": None,
    None: None,
    "C2": "C2",
    "C0": "C0",
    "C1": "C1",
    "C1_1": "C1_1",
    "H2_loc": "H2_loc",
    "C_infinity": "C_infinity",
}
GENERICITY = {  # axis_registry.genericity_axis.frozen -> axes.genericity_kind (authoritative)
    "residual_comeager": "provisional_baire_residual",
    "provisional_baire_residual": "provisional_baire_residual",
    "unresolved": "unresolved",
    "baire_residual": "baire_residual",
    "dense_open": "dense_open",
    "measure_one": "measure_one",
}
CONCLUSION = {  # class_contracts.<cid>.conclusion_type -> axes.conclusion_type
    "weak_cosmic_censorship": "weak_cosmic_censorship",
    "scc_c2_future_inextendibility": "strong_cosmic_censorship_C2",
    "scc_c0_future_inextendibility": "strong_cosmic_censorship_C0",
    "strong_cosmic_censorship_C2": "strong_cosmic_censorship_C2",
    "strong_cosmic_censorship_C0": "strong_cosmic_censorship_C0",
}
NAIVE_COMPONENT_GENERICITY = {  # non-authoritative shorthand present in components.genericity
    "GEN": "provisional_baire_residual",
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(p: Path) -> str:
    try:
        rel = p.resolve().relative_to(ROOT.resolve())
    except ValueError:
        rel = p
    return f"{rel}#{sha256_file(p)[:12]}"


def load_yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text())


def load_checker(path: Path):
    spec = importlib.util.spec_from_file_location("f0_checker", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def canonical_axes(doc: dict) -> dict:
    return {cid: dict(cls["axes"]) for cid, cls in doc["classes"].items()}


def canonical_vocab(doc: dict) -> dict:
    return {ax: list(spec.get("allowed", [])) for ax, spec in doc["field_vocabulary"].items()}


def project_frozen(doc: dict, mode: str) -> dict:
    """Project the frozen authoring taxonomy into the canonical checker's taxonomy shape.

    mode:
      mapped     - documented token map, authoritative genericity registry  (the proposal)
      naive_values - field names renamed, values passed through verbatim     (trap A)
      naive_genericity - full token map except components.genericity         (trap B)
    """
    if mode not in {"mapped", "naive_values", "naive_genericity"}:
        raise ValueError(f"unknown mode {mode!r}")
    classes, provenance = {}, {}
    for cid in doc["frozen_classes"]:
        contract = doc["class_contracts"][cid]
        comp = contract["components"]
        if mode == "naive_values":
            axes = {
                "family": comp["censorship"],
                "matter_model": comp["matter"],
                "symmetry": comp.get("symmetry", "none_assumed"),
                "asymptotics": comp["asymptotics"],
                "regularity_token": comp.get("regularity_token"),
                "genericity_kind": comp["genericity"],
                "conclusion_type": contract["conclusion_type"],
            }
            src = {k: "components (verbatim)" for k in AXES}
        else:
            gen_token = (comp["genericity"] if mode == "naive_genericity"
                         else doc["axis_registry"]["genericity_axis"]["frozen"][cid])
            axes = {
                "family": FAMILY[comp["censorship"]],
                "matter_model": MATTER[comp["matter"]],
                "symmetry": comp.get("symmetry", "none_assumed"),
                "asymptotics": ASYMPTOTICS[comp["asymptotics"]],
                "regularity_token": REGULARITY[comp.get("regularity_token")],
                "genericity_kind": NAIVE_COMPONENT_GENERICITY.get(gen_token, gen_token)
                if mode == "naive_genericity" else GENERICITY[gen_token],
                "conclusion_type": CONCLUSION[contract["conclusion_type"]],
            }
            src = {
                "family": "components.censorship",
                "matter_model": "components.matter",
                "symmetry": "components.symmetry",
                "asymptotics": "components.asymptotics",
                "regularity_token": "components.regularity_token",
                "genericity_kind": ("components.genericity" if mode == "naive_genericity"
                                    else "axis_registry.genericity_axis.frozen"),
                "conclusion_type": "class_contracts.conclusion_type",
            }
        classes[cid] = axes
        provenance[cid] = src
    return {
        "class_ids": list(doc["frozen_classes"]),
        "classes": classes,
        "vocab": canonical_vocab(CANONICAL_DOC),  # inherited by design; recorded in report
        "guards": {},
        "allowed_transfers": [],
        "forbidden_transfers": [],
        "doc": doc,
        "projection_provenance": provenance,
    }


def run_corpus(checker, cases, taxonomy, catalog) -> dict:
    errors, counts, cov, kinds, pending = checker.check_corpus(cases, taxonomy, catalog)
    return {"errors": list(errors), "counts": counts, "coverage": cov,
            "leak_kinds": kinds, "semantic_pending": list(pending)}


def deltas(base: dict, other: dict) -> dict:
    base_by_case = {}
    for e in base["errors"]:
        base_by_case.setdefault(e.split(":", 1)[0], []).append(e)
    out = {}
    for e in other["errors"]:
        cid = e.split(":", 1)[0]
        if e not in base["errors"]:
            out.setdefault(cid, []).append(e)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical", default="research_map/formulation_taxonomy.yaml")
    ap.add_argument("--frozen", default="artifacts/formulation/formulation_taxonomy.yaml")
    ap.add_argument("--cases", default="schemas/taxonomy_cases.jsonl")
    ap.add_argument("--catalog", default="artifacts/flash-02/leak_rule_catalog.json")
    ap.add_argument("--checker", default="artifacts/flash-02/check_taxonomy_cases.py")
    ap.add_argument("--report", default="artifacts/flash-02/frozen_rebind_report.json")
    a = ap.parse_args()

    cpath, fpath = Path(a.canonical), Path(a.frozen)
    cases_path, catalog_path, checker_path = Path(a.cases), Path(a.catalog), Path(a.checker)
    global CANONICAL_DOC
    CANONICAL_DOC = load_yaml(cpath)
    frozen_doc = load_yaml(fpath)
    checker = load_checker(checker_path)
    cases_meta, cases = checker.load_cases(cases_path)
    catalog = json.loads(catalog_path.read_text())

    errors = []
    controls = []

    # ---- baseline: canonical taxonomy on canonical corpus --------------------------------
    can_axes = canonical_axes(CANONICAL_DOC)
    tax_canonical = checker.load_taxonomy(cpath)
    base = run_corpus(checker, cases, tax_canonical, catalog)
    if base["errors"]:
        errors.append(f"BASELINE_NOT_CLEAN: {len(base['errors'])} errors")

    # ---- structural compatibility: can the existing checker read the frozen file? --------
    structural = {"checker_can_parse_frozen": False, "exception": None}
    try:
        checker.load_taxonomy(fpath)
        structural["checker_can_parse_frozen"] = True
    except Exception as e:  # noqa: BLE001 - the exception type is the measurement
        structural["exception"] = {"type": type(e).__name__, "message": str(e)}
        structural["missing_expected_keys"] = [
            k for k in ("classes", "field_vocabulary") if k not in frozen_doc
        ]
        structural["frozen_keys_instead"] = sorted(frozen_doc.keys())

    # ---- axis comparison: canonical vs projected frozen ----------------------------------
    projections = {}
    for mode in ("mapped", "naive_values", "naive_genericity"):
        proj = project_frozen(frozen_doc, mode)
        runs = run_corpus(checker, cases, proj, catalog)
        diff = deltas(base, runs)
        axis_cmp = {}
        for cid in sorted(can_axes):
            row = {}
            for ax in AXES:
                cval = can_axes[cid].get(ax)
                pval = proj["classes"].get(cid, {}).get(ax)
                row[ax] = {"canonical": cval, "projected": pval, "equal": cval == pval}
            axis_cmp[cid] = row
        projections[mode] = {
            "class_ids": proj["class_ids"],
            "axis_comparison": axis_cmp,
            "classes_axis_equal": sorted(cid for cid, row in axis_cmp.items()
                                         if all(v["equal"] for v in row.values())),
            "classes_axis_divergent": sorted(
                cid for cid, row in axis_cmp.items()
                if not all(v["equal"] for v in row.values())),
            "corpus_run": {"errors_total": len(runs["errors"]),
                           "counts": runs["counts"],
                           "coverage": runs["coverage"]},
            "delta_error_count": sum(len(v) for v in diff.values()),
            "delta_cases": sorted(diff),
            "delta_errors": [e for cid in sorted(diff) for e in diff[cid]],
            "projection_provenance": proj["projection_provenance"],
        }

    mapped = projections["mapped"]
    naive_values = projections["naive_values"]
    naive_gen = projections["naive_genericity"]

    # ---- controls ------------------------------------------------------------------------
    # C1 identity: the canonical run is deterministic and clean (guards against a vacuous PASS)
    base2 = run_corpus(checker, cases, tax_canonical, catalog)
    controls.append({
        "control_id": "C1_baseline_deterministic_clean",
        "expected": "0 errors on both runs; no false divergence",
        "observed": {"run1_errors": len(base["errors"]), "run2_errors": len(base2["errors"]),
                     "identical": base["errors"] == base2["errors"]},
        "passed": base["errors"] == base2["errors"] == [],
    })

    # C2 mutation: a one-class token flip must be detected (comparator is non-vacuous)
    mut = copy.deepcopy(frozen_doc)
    mut["class_contracts"]["AF-WCC-VAC-GEN"]["components"]["censorship"] = "SCC"
    mut_proj = project_frozen(mut, "mapped")
    mut_div = [cid for cid in can_axes
               if mut_proj["classes"][cid] != can_axes[cid]]
    mut_run = run_corpus(checker, cases, mut_proj, catalog)
    mut_delta = deltas(base, mut_run)
    controls.append({
        "control_id": "C2_token_flip_detected",
        "expected": "AF-WCC-VAC-GEN family divergence + nonzero corpus deltas for its cases",
        "observed": {"divergent_classes": sorted(mut_div),
                     "delta_error_count": sum(len(v) for v in mut_delta.values()),
                     "delta_cases": sorted(mut_delta)[:6]},
        "passed": mut_div == ["AF-WCC-VAC-GEN"] and sum(len(v) for v in mut_delta.values()) > 0,
    })

    # C3 coverage: removing all positives of one class must fail the checker (it is executing)
    dropped = [c for c in cases
               if not (c.get("polarity") == "positive"
                       and c.get("class_id") == "AF-WCC-SCALAR-SPH")]
    drop_run = run_corpus(checker, dropped, tax_canonical, catalog)
    drop_cov = [e for e in drop_run["errors"] if "COVERAGE" in e and "SCALAR" in e]
    controls.append({
        "control_id": "C3_dropped_class_coverage_detected",
        "expected": "COVERAGE error naming AF-WCC-SCALAR-SPH",
        "observed": {"coverage_errors": drop_cov[:3],
                     "positive_counts": drop_run["counts"]},
        "passed": bool(drop_cov) and drop_run["counts"]["positive"] == 12,
    })

    # C4 precedence trap: components-first genericity must change exactly the scalar class
    GLOBAL_ERROR_KEYS = {"COVERAGE", "TAXONOMY", "CONTROL_FAILED", "BASELINE_NOT_CLEAN"}
    scalar_cases = {c["case_id"] for c in cases
                    if c.get("class_id") == "AF-WCC-SCALAR-SPH"
                    or c.get("as_filed_class_id") == "AF-WCC-SCALAR-SPH"}
    trap_all = set(naive_gen["delta_cases"])
    trap_delta_cases = trap_all - GLOBAL_ERROR_KEYS
    trap_scalar_coverage = any(
        "COVERAGE" in e and "SCALAR" in e for e in naive_gen["delta_errors"])
    controls.append({
        "control_id": "C4_component_genericity_precedence_trap",
        "expected": ("components-first projection changes scalar-class axis; scalar cases fail "
                     "and scalar positive coverage collapses"),
        "observed": {"divergent_classes": naive_gen["classes_axis_divergent"],
                     "delta_cases": sorted(trap_delta_cases),
                     "global_errors": sorted(trap_all & GLOBAL_ERROR_KEYS),
                     "scalar_coverage_collapse": trap_scalar_coverage,
                     "delta_confined_to_scalar_cases": trap_delta_cases <= scalar_cases},
        "passed": naive_gen["classes_axis_divergent"] == ["AF-WCC-SCALAR-SPH"]
        and bool(trap_delta_cases) and trap_delta_cases <= scalar_cases
        and trap_scalar_coverage,
    })

    # C5 structural break is real and is what publication would hit
    controls.append({
        "control_id": "C5_structural_break_observed",
        "expected": "checker.load_taxonomy(frozen) raises on missing 'classes'",
        "observed": structural,
        "passed": (not structural["checker_can_parse_frozen"])
        and (structural.get("exception") or {}).get("type") == "KeyError",
    })

    controls_all = all(c["passed"] for c in controls)
    if not controls_all:
        errors.append("CONTROL_FAILED: " + ", ".join(
            c["control_id"] for c in controls if not c["passed"]))

    # ---- verdict -------------------------------------------------------------------------
    mapped_clean = (mapped["classes_axis_divergent"] == []
                    and mapped["delta_error_count"] == 0)
    if base["errors"]:
        verdict = "BASELINE_BROKEN"
    elif not mapped_clean:
        verdict = "REBIND_REQUIRES_CASE_FIXES"
    elif not structural["checker_can_parse_frozen"]:
        verdict = "REBIND_SAFE_ONLY_WITH_DOCUMENTED_TOKEN_MAP"
    else:
        verdict = "REBIND_SAFE_AS_IS"

    required_actions = [
        "Publish the token map together with the frozen taxonomy; canonical vocabulary values "
        "remain the only values written into schemas/taxonomy_cases.jsonl.",
        "Do NOT project genericity from class_contracts.<cid>.components.genericity; the "
        "authoritative source is axis_registry.genericity_axis.frozen (scalar class = unresolved).",
        "Use an adapter (this script's project_frozen(..., mode='mapped')) or keep the canonical "
        "tree in the checker's shape; the existing checker cannot parse the frozen container.",
        "After the canonical copy, re-run check_taxonomy_cases.py against the new canonical file "
        "and record a new taxonomy_ref.sha256/revision + rebind_note in the corpus meta. "
        "Silent patching is forbidden (corpus rebind_note).",
    ]

    report = {
        "report_version": "1.0",
        "measured_at": datetime.now(CST).isoformat(timespec="seconds"),
        "actor": "deepseek-flash-02",
        "node_id": "F0",
        "gate": "G-F0",
        "assignment_event_id": "asg-2026-09-11-F0-deepseek-flash-02-11",
        "artifact_under_maintenance": str(cases_path),
        "verdict": verdict,
        "structural_compatibility": structural,
        "baseline_corpus_run": {"errors_total": len(base["errors"]), "counts": base["counts"]},
        "projections": projections,
        "controls": controls,
        "controls_all_passed": controls_all,
        "errors": errors,
        "required_actions": required_actions,
        "falsifier": ("A projected frozen revision differs from canonical rev3 on any of the 7 "
                      "corpus axes for any of the 4 classes, or the mapped corpus run yields a "
                      "nonzero error delta against the canonical baseline. Either refutes "
                      "rebind-safety with this token map."),
        "evidence_refs": [ref(cpath), ref(fpath), ref(cases_path), ref(catalog_path),
                          ref(checker_path)],
        "hashes": {"canonical_taxonomy_sha256": sha256_file(cpath),
                   "frozen_taxonomy_sha256": sha256_file(fpath),
                   "cases_sha256": sha256_file(cases_path),
                   "catalog_sha256": sha256_file(catalog_path),
                   "checker_sha256": sha256_file(checker_path)},
        "limitations": [
            "The projection inherits the canonical field_vocabulary because the frozen "
            "axis_registry covers 5 axes, not the 7 corpus axes; axis-vector equality is measured "
            "per class, vocabulary equality is asserted from the canonical tree.",
            "This report is a machine check of artifact compatibility, not a physics claim; it "
            "does not move any node status or gate verdict.",
        ],
    }

    out = Path(a.report)
    out.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n")
    print(f"verdict: {verdict}")
    print(f"controls_all_passed: {controls_all}")
    print(f"mapped: divergent={mapped['classes_axis_divergent']} "
          f"delta_errors={mapped['delta_error_count']}")
    print(f"naive_values: delta_errors={naive_values['delta_error_count']}")
    print(f"naive_genericity: divergent={naive_gen['classes_axis_divergent']} "
          f"delta_errors={naive_gen['delta_error_count']}")
    print(f"structural: parseable={structural['checker_can_parse_frozen']} "
          f"exception={(structural.get('exception') or {}).get('type')}")
    print(f"report: {out} sha256={sha256_file(out)[:16]}")
    return 0 if (controls_all and not errors) else 1


if __name__ == "__main__":
    raise SystemExit(main())
