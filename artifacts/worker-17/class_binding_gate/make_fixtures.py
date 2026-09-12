#!/usr/bin/env python3
"""Deterministically generate good and mutant fixtures for class_binding_gate.py.

The mutant table is hand-declared (fixtures/EXPECTED.json). selftest_gate.py is
what checks that the gate catches each mutant; this script only writes inputs.

Run:  python3 make_fixtures.py
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"


def good_wcc_vacuum():
    return {
        "schema_version": "0.1",
        "class_id": "AF-WCC-VAC-GEN",
        "title": "Weak cosmic censorship: asymptotically flat vacuum, generic data",
        "matter_model": "vacuum",
        "quantifiers": {
            "for_all": (
                "for all initial data sets (Sigma, g, K) in the weighted class below "
                "satisfying the vacuum constraints, outside the exceptional set"
            ),
            "there_exists": (
                "there exists a maximal globally hyperbolic development (M, g) with "
                "future null infinity I+ attached"
            ),
            "counterexample_form": (
                "there exists an admissible datum whose maximal development has a "
                "singularity visible from I+, i.e. a causal curve from the singular "
                "boundary reaches I+"
            ),
            "order": "for_all data; NOT (there_exists a visible singularity)",
        },
        "topology": {
            "manifold": (
                "3+1 dimensional manifold with Cauchy surface Sigma diffeomorphic to "
                "R^3 minus a compact set; one asymptotically flat end"
            ),
            "asymptotically_flat": True,
            "i_plus": (
                "future null infinity I+ of the conformal completion, taken complete "
                "and with standard spherical topology"
            ),
            "end_count": 1,
        },
        "data_class": {
            "space": "weighted Sobolev space H^s_{-delta} with s > 3/2 and delta in (1/2, 1)",
            "weights": "-delta, delta in (1/2, 1)",
            "decay": "g - delta_euclidean in H^s_{-delta}; K in H^{s-1}_{-delta-1/2}",
        },
        "regularity_of_solution": "smooth (C^infinity) vacuum development of the data",
        "constraints": (
            "vacuum Einstein constraint equations hold on every datum: scalar "
            "constraint and momentum constraint"
        ),
        "genericity": {
            "measure_or_topology": (
                "open dense subset in the weighted H^s_{-delta} topology; complement "
                "is meagre (Baire-generic)"
            ),
            "statement": "the conclusion holds for all data outside a meagre exceptional set",
        },
        "visibility": {
            "definition": (
                "a boundary point p is visible from I+ if a future-directed causal "
                "curve reaches I+ from p"
            ),
            "visible_predicate": (
                "Vis(p) := exists a future-directed causal curve gamma from p to a "
                "point of I+"
            ),
            "conclusion_target": "no visible singularity",
        },
        "conclusion": {
            "type": "conditional_theorem",
            "statement": (
                "for generic admissible vacuum data, no singularity is visible from "
                "future null infinity I+"
            ),
            "negation": "there exist generic data with a singularity visible from I+",
        },
        "falsifier": {
            "witness_type": (
                "an explicit admissible datum (Sigma, g, K) in the weighted class "
                "meeting the stated genericity condition"
            ),
            "check": (
                "construct the maximal development, locate the singular boundary and "
                "exhibit a causal curve reaching I+"
            ),
        },
        "source_refs": [
            "Penrose 1969, Gravitational collapse: the role of general relativity",
            "Christodoulou 1999, The instability of naked singularities in the "
            "gravitational collapse of a scalar field",
        ],
        "related_classes": [
            {
                "class_id": "AF-SCC-C2-VAC-GEN",
                "relation": (
                    "distinct conclusion: C^2-inextendibility beyond the Cauchy "
                    "horizon; shares only the AF vacuum data class"
                ),
            },
            {
                "class_id": "AF-SCC-C0-VAC-GEN",
                "relation": (
                    "distinct conclusion: C^0-inextendibility; not a disjunction with "
                    "the C^2 class"
                ),
            },
        ],
    }


def good_scc_c2():
    doc = good_wcc_vacuum()
    doc["class_id"] = "AF-SCC-C2-VAC-GEN"
    doc["title"] = "Strong cosmic censorship, C^2 class: asymptotically flat vacuum, generic data"
    doc["regularity_of_solution"] = (
        "C^2 (twice continuously differentiable) vacuum development of the data"
    )
    doc["genericity"]["statement"] = (
        "the inextendibility conclusion holds for all data outside a meagre "
        "exceptional set"
    )
    doc["visibility"] = {
        "definition": (
            "a Cauchy horizon point is visible from I+ if a future-directed causal "
            "curve from it reaches I+; SCC does not require the violation to be visible"
        ),
        "cauchy_horizon": (
            "future Cauchy horizon CH+(Sigma) of the maximal development, beyond "
            "which extendibility is tested"
        ),
    }
    doc["conclusion"] = {
        "type": "conditional_theorem",
        "statement": (
            "for generic admissible vacuum data, the maximal development is "
            "C^2-inextendible beyond the Cauchy horizon"
        ),
        "inextendibility_regularity": "C2",
        "negation": (
            "there exist generic admissible data whose maximal development admits a "
            "C^2 extension beyond the Cauchy horizon"
        ),
    }
    doc["falsifier"] = {
        "witness_type": (
            "an explicit admissible datum in the weighted class whose maximal "
            "development admits a C^2 extension beyond the Cauchy horizon while "
            "meeting the genericity condition"
        ),
        "check": (
            "construct the maximal development, exhibit the extension across the "
            "Cauchy horizon and verify its differentiability class"
        ),
    }
    doc["related_classes"] = [
        {
            "class_id": "AF-WCC-VAC-GEN",
            "relation": "distinct conclusion: no visible singularity; shares the AF vacuum data class only",
        },
        {
            "class_id": "AF-SCC-C0-VAC-GEN",
            "relation": "separate regularity class; never merged as a disjunction",
        },
    ]
    return doc


def good_scc_c0():
    doc = good_scc_c2()
    doc["class_id"] = "AF-SCC-C0-VAC-GEN"
    doc["title"] = "Strong cosmic censorship, C^0 class: asymptotically flat vacuum, generic data"
    doc["regularity_of_solution"] = (
        "C^0 (continuous metric) vacuum development of the data; curvature locally "
        "square-integrable"
    )
    doc["conclusion"] = {
        "type": "conditional_theorem",
        "statement": (
            "for generic admissible vacuum data, the maximal development is "
            "C^0-inextendible beyond the Cauchy horizon"
        ),
        "inextendibility_regularity": "C0",
        "negation": (
            "there exist generic admissible data whose maximal development admits a "
            "C^0 extension beyond the Cauchy horizon"
        ),
    }
    doc["falsifier"] = {
        "witness_type": (
            "an explicit admissible datum in the weighted class whose maximal "
            "development admits a C^0 extension beyond the Cauchy horizon while "
            "meeting the genericity condition"
        ),
        "check": (
            "construct the maximal development, exhibit the continuous extension "
            "across the Cauchy horizon and verify metric continuity"
        ),
    }
    doc["related_classes"] = [
        {
            "class_id": "AF-WCC-VAC-GEN",
            "relation": "distinct conclusion: no visible singularity; shares the AF vacuum data class only",
        },
        {
            "class_id": "AF-SCC-C2-VAC-GEN",
            "relation": "separate regularity class; never merged as a disjunction",
        },
    ]
    return doc


def good_wcc_scalar_spherical():
    doc = good_wcc_vacuum()
    doc["class_id"] = "AF-WCC-SCALAR-SPH"
    doc["title"] = "Weak cosmic censorship: spherical symmetry, massless scalar field, generic data"
    doc["matter_model"] = "massless scalar field"
    doc["symmetry"] = "spherical symmetry with SO(3) orbits"
    doc["topology"]["manifold"] = (
        "spherically symmetric 3+1 spacetime; Cauchy surfaces with one asymptotically "
        "flat end, orbits SO(3)"
    )
    doc["data_class"]["space"] = (
        "spherically symmetric weighted Sobolev space H^s_{-delta} on the radial "
        "half-line, delta in (1/2, 1)"
    )
    doc["constraints"] = (
        "Einstein-scalar constraint equations hold on every datum: scalar and "
        "momentum constraints with scalar field energy density"
    )
    doc["regularity_of_solution"] = (
        "smooth (C^infinity) Einstein-scalar development of the data"
    )
    doc["related_classes"] = []
    return doc


MUTANTS = {
    "bad_unknown_class.yaml": lambda: _set(good_wcc_vacuum(), None, "class_id", "AF-SCC-VAC-GEN"),
    "bad_missing_iplus.yaml": lambda: _del(good_wcc_vacuum(), "topology", "i_plus"),
    "bad_empty_decay.yaml": lambda: _set(good_wcc_vacuum(), "data_class", "decay", ""),
    "bad_free_quantifier.yaml": lambda: _set(
        good_wcc_vacuum(), "quantifiers", "counterexample_form", "none needed"
    ),
    "bad_bare_generic.yaml": lambda: _set(
        good_wcc_vacuum(), "genericity", "measure_or_topology", "generic data"
    ),
    "bad_topology_not_af.yaml": lambda: _set(
        good_wcc_vacuum(), "topology", "asymptotically_flat", False
    ),
    "bad_data_class_bare.yaml": lambda: _set(
        good_wcc_vacuum(), "data_class", "space", "smooth functions on R^3"
    ),
    "bad_constraints_none.yaml": lambda: _set(
        good_wcc_vacuum(), None, "constraints", "none beyond the equations of motion"
    ),
    "bad_mixed_c0_c2.yaml": lambda: _set(
        good_wcc_vacuum(), None, "regularity_of_solution", "C^0 or C^2 development"
    ),
    "bad_visibility_no_predicate.yaml": lambda: _del(
        good_wcc_vacuum(), "visibility", "visible_predicate"
    ),
    "bad_wcc_conclusion_inflation.yaml": lambda: _set(
        good_wcc_vacuum(),
        "conclusion",
        "statement",
        "for generic data the maximal development is C^2-inextendible beyond the Cauchy horizon",
    ),
    "bad_falsifier_witness.yaml": lambda: _set(
        good_wcc_vacuum(), "falsifier", "witness_type", "a curvature singularity"
    ),
    "bad_source_refs_empty.yaml": lambda: _set(good_wcc_vacuum(), None, "source_refs", []),
    "bad_matter_dust.yaml": lambda: _set(good_wcc_vacuum(), None, "matter_model", "dust"),
    "bad_missing_falsifier.yaml": lambda: _del(good_wcc_vacuum(), None, "falsifier"),
    "bad_missing_source_refs.yaml": lambda: _del(good_wcc_vacuum(), None, "source_refs"),
    "bad_scc_leak_in_wcc.yaml": lambda: _set(
        good_wcc_vacuum(),
        None,
        "notes",
        "see AF-SCC-C2-VAC-GEN for the inextendibility refinement",
    ),
    "bad_disjunctive_related.yaml": lambda: _set(
        good_wcc_vacuum(),
        "related_classes.0",
        "relation",
        "C0 or C2 alternative, to be decided later",
    ),
    "bad_scc_wrong_regularity.yaml": lambda: _set(
        good_scc_c2(), "conclusion", "inextendibility_regularity", "C0"
    ),
    "bad_scc_conclusion_deflation.yaml": lambda: _set(
        good_scc_c2(),
        "conclusion",
        "statement",
        "no singularity is visible from future null infinity for generic data",
    ),
}

BAD_NOT_MAPPING = ["not", "a", "schema"]

EXPECTED = {
    "good": [
        "good_af_wcc_vacuum.yaml",
        "good_af_scc_c2.yaml",
        "good_af_scc_c0.yaml",
        "good_af_wcc_scalar_sph.yaml",
    ],
    "mutants": {
        "bad_not_mapping.yaml": ["R_PARSE"],
        "bad_unknown_class.yaml": ["R_CLASS"],
        "bad_missing_iplus.yaml": ["R_REQUIRED"],
        "bad_empty_decay.yaml": ["R_EMPTY"],
        "bad_free_quantifier.yaml": ["R_QUANTIFIERS"],
        "bad_bare_generic.yaml": ["R_GENERICITY"],
        "bad_topology_not_af.yaml": ["R_TOPOLOGY"],
        "bad_data_class_bare.yaml": ["R_DATA_CLASS"],
        "bad_constraints_none.yaml": ["R_CONSTRAINTS"],
        "bad_mixed_c0_c2.yaml": ["R_REGULARITY", "R_DISJUNCTION"],
        "bad_visibility_no_predicate.yaml": ["R_VISIBILITY"],
        "bad_wcc_conclusion_inflation.yaml": ["R_CONCLUSION"],
        "bad_falsifier_witness.yaml": ["R_FALSIFIER"],
        "bad_source_refs_empty.yaml": ["R_SOURCE_REFS"],
        "bad_matter_dust.yaml": ["R_MATTER"],
        "bad_missing_falsifier.yaml": ["R_REQUIRED"],
        "bad_missing_source_refs.yaml": ["R_REQUIRED"],
        "bad_scc_leak_in_wcc.yaml": ["R_NO_LEAK"],
        "bad_disjunctive_related.yaml": ["R_DISJUNCTION"],
        "bad_scc_wrong_regularity.yaml": ["R_CONCLUSION"],
        "bad_scc_conclusion_deflation.yaml": ["R_CONCLUSION"],
    },
}


def _set(base, container, key, value):
    doc = copy.deepcopy(base)
    if container is None:
        doc[key] = value
        return doc
    target = doc
    for part in str(container).split("."):
        target = target[int(part)] if isinstance(target, list) else target[part]
    target[key] = value
    return doc


def _del(base, container, key):
    doc = copy.deepcopy(base)
    if container is None:
        del doc[key]
        return doc
    target = doc
    for part in str(container).split("."):
        target = target[int(part)] if isinstance(target, list) else target[part]
    del target[key]
    return doc


def main():
    FIX.mkdir(parents=True, exist_ok=True)
    docs = {
        "good_af_wcc_vacuum.yaml": good_wcc_vacuum(),
        "good_af_scc_c2.yaml": good_scc_c2(),
        "good_af_scc_c0.yaml": good_scc_c0(),
        "good_af_wcc_scalar_sph.yaml": good_wcc_scalar_spherical(),
    }
    for name, doc in docs.items():
        (FIX / name).write_text(
            yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )
    for name, make in MUTANTS.items():
        (FIX / name).write_text(
            yaml.safe_dump(make(), sort_keys=False, allow_unicode=True), encoding="utf-8"
        )
    (FIX / "bad_not_mapping.yaml").write_text(
        yaml.safe_dump(BAD_NOT_MAPPING, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    (FIX / "EXPECTED.json").write_text(
        json.dumps(EXPECTED, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(docs)} good + {len(MUTANTS) + 1} mutant fixtures to {FIX}")


if __name__ == "__main__":
    main()
