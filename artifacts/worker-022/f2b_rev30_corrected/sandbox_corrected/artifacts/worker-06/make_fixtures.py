#!/usr/bin/env python3
"""Generate the W06 class-binding fixture corpus (synthetic structural controls).

Every fixture is SYNTHETIC. The positive fixtures are structurally complete templates,
not mathematical endorsements; the negative fixtures are deliberately malformed
structural variants used to prove the gate has discriminating power (the null control
for the F1/F2 formulation gate). Re-run this script to regenerate fixtures/.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "fixtures"

WCC_SLOTS = {
    "quantifiers": ("For all admissible asymptotically flat vacuum initial data sets (Sigma, g, K) "
                    "and for every maximal globally hyperbolic development (M, g), there exists no "
                    "singular point visible from future null infinity."),
    "topology": ("Smooth 4-manifold M with an asymptotically flat end; Sigma is a complete Riemannian "
                 "3-manifold with finitely many asymptotically flat ends."),
    "data_class": ("Admissible weighted Sobolev initial data with (g - delta) in H^s_{-tau} and K in "
                   "H^{s-1}_{-tau-1}, s > 5/2, tau > 1/2; no symmetry assumed."),
    "genericity": ("Holds on an open dense subset of the admissible data class in the weighted Sobolev "
                   "topology (Baire-generic)."),
    "future_null_infinity": ("Future null infinity I+ is complete and the conformal boundary is attached "
                             "as in the standard asymptotically flat definition."),
    "visibility": ("No element of the singular set is visible from I+; every incomplete causal geodesic is "
                   "hidden from future null infinity."),
    "conclusion_type": "asymptotic_predictability",
    "statement": ("If the maximal development is future geodesically incomplete, the incompleteness is "
                  "confined behind an event horizon and cannot be observed from I+."),
}

SCC_SLOTS = {
    "topology": ("Smooth 4-manifold M with an asymptotically flat end; the maximal globally hyperbolic "
                 "development is a globally hyperbolic manifold with Cauchy surface Sigma."),
    "data_class": ("Admissible weighted Sobolev vacuum initial data; no symmetry assumed; data are "
                   "generic in the class below."),
    "genericity": ("Generic means an open dense subset of the admissible data class in the weighted "
                   "Sobolev topology (residual in the Baire sense)."),
    "future_null_infinity": ("Future null infinity I+ is complete; the conformal boundary is regular "
                             "where the extension is claimed to fail."),
    "visibility": ("The failure of extendibility is not visible from I+ in the sense that no observer at "
                   "future null infinity sees a singularity; the statement is about the interior."),
    "statement": ("For all admissible initial data in the class and every maximal globally hyperbolic "
                  "development, there exists no extension of the stated regularity across the Cauchy "
                  "horizon."),
}


def fixture(fid, expected, purpose, intended_check, body):
    return {"_meta": {"fixture_id": fid, "expected": expected, "purpose": purpose,
                      "intended_failing_check": intended_check, "synthetic": True,
                      "not_a_mathematical_claim": True},
            **body}


FIXTURES = []

# ---------------- positives ----------------
FIXTURES.append(fixture(
    "pos01_af_wcc_vac_gen", "pass",
    "structurally complete WCC vacuum schema template",
    None,
    {"class_id": "AF-WCC-VAC-GEN", "map_node": "F1",
     "declared_artifact": "schemas/af_wcc_vacuum.yaml", **WCC_SLOTS}))

FIXTURES.append(fixture(
    "pos02_af_scc_c2_vac_gen", "pass",
    "structurally complete SCC C2 schema template",
    None,
    {"class_id": "AF-SCC-C2-VAC-GEN", "map_node": "F2",
     "declared_artifact": "schemas/af_scc_regularities.yaml", "regularity": "C2",
     "conclusion_type": "inextendibility_c2", **SCC_SLOTS}))

FIXTURES.append(fixture(
    "pos03_af_scc_c0_vac_gen", "pass",
    "structurally complete SCC C0 schema template",
    None,
    {"class_id": "AF-SCC-C0-VAC-GEN", "map_node": "F2",
     "declared_artifact": "schemas/af_scc_regularities.yaml", "regularity": "C0",
     "conclusion_type": "inextendibility_c0", **SCC_SLOTS}))

FIXTURES.append(fixture(
    "pos04_af_wcc_scalar_sph", "pass",
    "structurally complete WCC massless-scalar spherical schema template",
    None,
    {"class_id": "AF-WCC-SCALAR-SPH",
     "conclusion_type": "visible_from_i+",
     "quantifiers": ("For every admissible spherically symmetric massless scalar field initial data set, "
                     "there exists a unique maximal development; the singular set is hidden from I+."),
     "topology": "Spherically symmetric asymptotically flat 4-manifold; Cauchy surfaces are 3-manifolds.",
     "data_class": "Admissible spherically symmetric scalar field initial data with weighted Sobolev "
                   "regularity.",
     "genericity": "Open dense subset of the spherically symmetric admissible data class.",
     "future_null_infinity": "Future null infinity I+ is complete.",
     "visibility": "Any singularity is not visible from future null infinity.",
     "statement": "Sub-extremal data disperse; super-critical data form a hidden singularity."}))

# ---------------- negatives ----------------
FIXTURES.append(fixture(
    "neg01_composite_regularity", "fail",
    "SCC schema declaring 'C0 or C2' as one regularity selector",
    "no_composite_regularity_string",
    {"class_id": "AF-SCC-C2-VAC-GEN", "map_node": "F2",
     "declared_artifact": "schemas/af_scc_regularities.yaml", "regularity": "C0 or C2",
     "conclusion_type": "inextendibility_c2", **SCC_SLOTS}))

FIXTURES.append(fixture(
    "neg02_wcc_with_scc_conclusion", "fail",
    "WCC class carrying an SCC inextendibility conclusion",
    "conclusion_family_match",
    {"class_id": "AF-WCC-VAC-GEN", "map_node": "F1",
     "declared_artifact": "schemas/af_wcc_vacuum.yaml",
     **{**WCC_SLOTS, "conclusion_type": "inextendibility_of_maximal_development"}}))

FIXTURES.append(fixture(
    "neg03_scc_with_visibility_conclusion", "fail",
    "SCC class carrying a WCC visibility conclusion",
    "conclusion_family_match",
    {"class_id": "AF-SCC-C0-VAC-GEN", "map_node": "F2",
     "declared_artifact": "schemas/af_scc_regularities.yaml", "regularity": "C0",
     "conclusion_type": "visible_from_i+", **SCC_SLOTS}))

FIXTURES.append(fixture(
    "neg04_missing_visibility_slot", "fail",
    "required visibility slot absent",
    "required_slots",
    {"class_id": "AF-WCC-VAC-GEN", "map_node": "F1",
     "declared_artifact": "schemas/af_wcc_vacuum.yaml",
     "quantifiers": WCC_SLOTS["quantifiers"], "topology": WCC_SLOTS["topology"],
     "data_class": WCC_SLOTS["data_class"], "genericity": WCC_SLOTS["genericity"],
     "future_null_infinity": WCC_SLOTS["future_null_infinity"],
     "conclusion_type": "asymptotic_predictability", "statement": "Incompleteness is confined."}))

FIXTURES.append(fixture(
    "neg05_genericity_unqualified", "fail",
    "genericity asserted but never qualified (no open dense / residual / measure)",
    "genericity_qualified",
    {"class_id": "AF-WCC-VAC-GEN", "map_node": "F1",
     "declared_artifact": "schemas/af_wcc_vacuum.yaml", **{**WCC_SLOTS, "genericity": "assume generic data"}}))

FIXTURES.append(fixture(
    "neg06_class_artifact_mismatch", "fail",
    "SCC class declared against the F1 WCC artifact path",
    "declared_artifact_matches",
    {"class_id": "AF-SCC-C2-VAC-GEN", "map_node": "F1",
     "declared_artifact": "schemas/af_wcc_vacuum.yaml", "regularity": "C2",
     "conclusion_type": "inextendibility_c2", **SCC_SLOTS}))

FIXTURES.append(fixture(
    "neg07_theorem_without_artifact", "fail",
    "conclusion_type=theorem without artifact_refs (fluent-text promotion)",
    "theorem_requires_artifact_refs",
    {"class_id": "AF-WCC-VAC-GEN", "map_node": "F1",
     "declared_artifact": "schemas/af_wcc_vacuum.yaml", **{**WCC_SLOTS, "conclusion_type": "theorem"}}))

FIXTURES.append(fixture(
    "neg08_quantifier_hole", "fail",
    "only an existential quantifier; no universal over admissible data",
    "quantifier_completeness",
    {"class_id": "AF-WCC-VAC-GEN", "map_node": "F1",
     "declared_artifact": "schemas/af_wcc_vacuum.yaml",
     "quantifiers": ("There exists admissible initial data for which some development has an incomplete "
                     "causal geodesic."),
     "topology": WCC_SLOTS["topology"], "data_class": WCC_SLOTS["data_class"],
     "genericity": WCC_SLOTS["genericity"], "future_null_infinity": WCC_SLOTS["future_null_infinity"],
     "visibility": WCC_SLOTS["visibility"], "conclusion_type": "asymptotic_predictability",
     "statement": "A single example is asserted."}))

FIXTURES.append(fixture(
    "neg09_two_class_ids", "fail",
    "two class ids in one schema (class conflation)",
    "single_class_id",
    {"class_id": "AF-WCC-VAC-GEN", "class": "AF-SCC-C0-VAC-GEN", "map_node": "F1",
     "declared_artifact": "schemas/af_wcc_vacuum.yaml", **WCC_SLOTS}))

FIXTURES.append(fixture(
    "neg10_cross_domain_contamination", "fail",
    "base-repo Erdos #64 language leaked into a cosmic-censorship schema",
    "no_cross_domain_contamination",
    {"class_id": "AF-WCC-VAC-GEN", "map_node": "F1",
     "declared_artifact": "schemas/af_wcc_vacuum.yaml",
     "quantifiers": ("For all admissible data there exists a counterexample: a cubic graph of minimum "
                     "degree at least 3 with no cycle of length 2^k."),
     "topology": WCC_SLOTS["topology"], "data_class": WCC_SLOTS["data_class"],
     "genericity": WCC_SLOTS["genericity"], "future_null_infinity": WCC_SLOTS["future_null_infinity"],
     "visibility": WCC_SLOTS["visibility"], "conclusion_type": "asymptotic_predictability",
     "statement": "Wrong domain entirely."}))

FIXTURES.append(fixture(
    "neg11_scc_two_regularities", "fail",
    "SCC schema carrying both C0 and C2 regularity selectors",
    "regularity_selector",
    {"class_id": "AF-SCC-C0-VAC-GEN", "map_node": "F2",
     "declared_artifact": "schemas/af_scc_regularities.yaml", "regularity": "C0",
     "extension_regularity": "C2", "conclusion_type": "inextendibility_c0", **SCC_SLOTS}))

FIXTURES.append(fixture(
    "neg12_wcc_with_regularity_selector", "fail",
    "WCC class carrying an SCC-style regularity selector",
    "regularity_selector",
    {"class_id": "AF-WCC-VAC-GEN", "map_node": "F1",
     "declared_artifact": "schemas/af_wcc_vacuum.yaml", "regularity": "C2", **WCC_SLOTS}))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for fx in FIXTURES:
        path = OUT / f"{fx['_meta']['fixture_id']}.json"
        path.write_text(json.dumps(fx, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {len(FIXTURES)} fixtures to {OUT}")


if __name__ == "__main__":
    main()
