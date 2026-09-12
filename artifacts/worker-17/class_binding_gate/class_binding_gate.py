#!/usr/bin/env python3
"""Class-binding acceptance gate (FORM ONLY) for cosmic-censorship formulation schemas.

Proposed by execution worker 17 (flash-17) under nodes F1/F2, formulation group.
See ../PROPOSAL.md for scope, acceptance tests, stop rule, and falsifier.

WHAT IT DECIDES
    Given one schema document (YAML or JSON), is it a *well-formed, class-bound
    specification* for exactly ONE of the frozen classes
        AF-WCC-VAC-GEN, AF-WCC-SCALAR-SPH, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN
    with exact quantifiers, topology, weighted data class, regularity, genericity,
    I+, visibility, a non-inflated conclusion type, a witness-shaped falsifier,
    source refs, and no cross-class leakage?

WHAT IT DOES NOT DECIDE
    Whether the formulation is physically correct; whether any theorem is true;
    whether F1/F2 are complete; whether a schema is *sufficient* for a proof.
    A PASS is a statement about form and separation only. This is deliberate:
    the gate is a filter for the review queue, not an oracle.

Design notes
    * Rules are named R_* and reported per JSON path, so a failing schema names the
      exact slot to fix.
    * Cross-class references are legal only inside `related_classes` and
      `source_refs`; every other subtree is scanned for leakage tokens.
      This encodes ASTRA_HANDOFF hard decision 1 (keep classes separate) and the
      ban on "C0 or C2" in any form.
    * The gate is independent of any particular schema text: it is exercised by
      good/mutant fixtures in fixtures/ with expected codes in selftest_gate.py.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is present in this workspace
    yaml = None

CLASS_IDS = (
    "AF-WCC-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
)
FAMILY = {
    "AF-WCC-VAC-GEN": "WCC",
    "AF-WCC-SCALAR-SPH": "WCC",
    "AF-SCC-C2-VAC-GEN": "SCC",
    "AF-SCC-C0-VAC-GEN": "SCC",
}
SCC_REGULARITY = {"AF-SCC-C2-VAC-GEN": "C2", "AF-SCC-C0-VAC-GEN": "C0"}
ALLOWED_CONCLUSION_TYPES = {
    "theorem",
    "conditional_theorem",
    "stability_result",
    "numerical_evidence",
    "formal_model",
    "open_problem",
}
RULE_CODES = (
    "R_PARSE",
    "R_CLASS",
    "R_REQUIRED",
    "R_EMPTY",
    "R_QUANTIFIERS",
    "R_TOPOLOGY",
    "R_DATA_CLASS",
    "R_CONSTRAINTS",
    "R_REGULARITY",
    "R_GENERICITY",
    "R_VISIBILITY",
    "R_CONCLUSION",
    "R_FALSIFIER",
    "R_SOURCE_REFS",
    "R_MATTER",
    "R_NO_LEAK",
    "R_DISJUNCTION",
)

CORE_SLOTS = (
    "schema_version",
    "class_id",
    "matter_model",
    "quantifiers",
    "topology",
    "data_class",
    "regularity_of_solution",
    "constraints",
    "genericity",
    "visibility",
    "conclusion",
    "falsifier",
    "source_refs",
)

BASE_PATHS = (
    "schema_version",
    "class_id",
    "matter_model",
    "quantifiers.for_all",
    "quantifiers.there_exists",
    "quantifiers.counterexample_form",
    "topology.manifold",
    "topology.asymptotically_flat",
    "topology.i_plus",
    "data_class.space",
    "data_class.weights",
    "data_class.decay",
    "regularity_of_solution",
    "constraints",
    "genericity.measure_or_topology",
    "genericity.statement",
    "visibility.definition",
    "conclusion.type",
    "conclusion.statement",
    "falsifier.witness_type",
    "falsifier.check",
)

# Subtree roots that may legitimately mention other classes: the class-relation
# table and the provenance list. Everything else is spec text and is scanned.
LEAK_EXEMPT_ROOTS = frozenset({"class_id", "related_classes", "source_refs"})

RE_DISJUNCTION = re.compile(
    r"\bC\s*\^?\s*0\s*(?:or|/|\|)\s*C\s*\^?\s*2\b"
    r"|\bC\s*\^?\s*2\s*(?:or|/|\|)\s*C\s*\^?\s*0\b",
    re.I,
)
RE_C0 = re.compile(r"\bC\s*\^?\s*0\b")
RE_C2 = re.compile(r"\bC\s*\^?\s*2\b")
RE_SCC = re.compile(r"AF-SCC|strong[\s_-]*cosmic[\s_-]*censorship|inextendib", re.I)
RE_WCC = re.compile(r"AF-WCC|weak[\s_-]*cosmic[\s_-]*censorship", re.I)
RE_WEIGHTED = re.compile(r"\bH\b|H\s*\^|weight|\bdelta\b|δ", re.I)
RE_GENERIC = re.compile(
    r"measure|full|open|dense|residual|baire|meagre|meager|generic set", re.I
)
RE_WITNESS = re.compile(r"\bdata\b|\bdatum\b|initial data set", re.I)
RE_VISIBLE_CONCLUSION = re.compile(r"visible|predictab|asymptotic", re.I)
RE_INEXT_CONCLUSION = re.compile(r"inextendib", re.I)
RE_CONSTRAINT = re.compile(r"constraint", re.I)


def _get(doc, dotted):
    """Return (exists, value) for a dotted path."""
    cur = doc
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return False, None
    return True, cur


def _is_empty(value):
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict, tuple)):
        return len(value) == 0
    return False


def _leaves(obj, path=()):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from _leaves(value, path + (str(key),))
    elif isinstance(obj, (list, tuple)):
        for index, value in enumerate(obj):
            yield from _leaves(value, path + (str(index),))
    else:
        yield path, obj


def _as_text(value):
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:  # pragma: no cover
        return str(value)


def load_document(path):
    """Parse YAML or JSON. Raises on malformed input; caller maps to R_PARSE."""
    text = Path(path).read_text(encoding="utf-8")
    if yaml is None:  # pragma: no cover
        return json.loads(text)
    return yaml.safe_load(text)


def check(doc, source="<memory>"):
    """Return a list of violations (empty list means the document passes)."""
    violations = []

    def add(code, message, path=""):
        violations.append(
            {"code": code, "message": message, "path": path, "source": source}
        )

    if not isinstance(doc, dict):
        add("R_PARSE", f"top-level document is {type(doc).__name__}, expected a mapping")
        return violations

    class_id = doc.get("class_id")
    if class_id not in CLASS_IDS:
        add(
            "R_CLASS",
            f"class_id {class_id!r} is not exactly one frozen class of {list(CLASS_IDS)}; "
            "an umbrella id such as AF-SCC-VAC-GEN is rejected",
            "class_id",
        )
        return violations
    family = FAMILY[class_id]

    # --- presence and emptiness ------------------------------------------------
    for slot in CORE_SLOTS:
        if slot not in doc:
            add("R_REQUIRED", f"missing required top-level slot {slot!r}", slot)
    for dotted in BASE_PATHS:
        exists, value = _get(doc, dotted)
        if not exists:
            add("R_REQUIRED", f"missing required slot {dotted!r}", dotted)
        elif _is_empty(value):
            add("R_EMPTY", f"required slot {dotted!r} is empty", dotted)

    # --- matter model and symmetry --------------------------------------------
    exists, matter = _get(doc, "matter_model")
    if exists and not _is_empty(matter):
        text = _as_text(matter).lower()
        if class_id == "AF-WCC-SCALAR-SPH":
            if "scalar" not in text:
                add(
                    "R_MATTER",
                    f"AF-WCC-SCALAR-SPH requires a scalar matter model, got {matter!r}",
                    "matter_model",
                )
            exists_sym, symmetry = _get(doc, "symmetry")
            if not exists_sym:
                add("R_REQUIRED", "AF-WCC-SCALAR-SPH requires 'symmetry'", "symmetry")
            elif _is_empty(symmetry) or "spherical" not in _as_text(symmetry).lower():
                add(
                    "R_MATTER",
                    "AF-WCC-SCALAR-SPH requires spherical symmetry",
                    "symmetry",
                )
        elif text.strip() != "vacuum":
            add(
                "R_MATTER",
                f"class {class_id} is a vacuum class; matter_model must be 'vacuum', "
                f"got {matter!r}",
                "matter_model",
            )

    # --- quantifiers -----------------------------------------------------------
    exists, quantifiers = _get(doc, "quantifiers")
    if exists and not isinstance(quantifiers, dict):
        add("R_QUANTIFIERS", "quantifiers must be a mapping", "quantifiers")
    elif exists:
        for key in ("for_all", "there_exists"):
            value = quantifiers.get(key)
            if not _is_empty(value) and len(_as_text(value).strip()) < 8:
                add(
                    "R_QUANTIFIERS",
                    f"quantifiers.{key} is too short to be exact: {value!r}",
                    f"quantifiers.{key}",
                )
        counterexample = quantifiers.get("counterexample_form")
        if not _is_empty(counterexample) and not RE_WITNESS.search(
            _as_text(counterexample)
        ):
            add(
                "R_QUANTIFIERS",
                "quantifiers.counterexample_form must name a witness-shaped object "
                "(data/datum) that a finite check could exhibit",
                "quantifiers.counterexample_form",
            )

    # --- topology / I+ ---------------------------------------------------------
    exists, asymptotically_flat = _get(doc, "topology.asymptotically_flat")
    if exists and asymptotically_flat is not True:
        add(
            "R_TOPOLOGY",
            "topology.asymptotically_flat must be the boolean true",
            "topology.asymptotically_flat",
        )
    exists, i_plus = _get(doc, "topology.i_plus")
    if exists and not _is_empty(i_plus) and len(_as_text(i_plus).strip()) < 12:
        add(
            "R_TOPOLOGY",
            "topology.i_plus is too short to identify the object (state completeness/"
            "regularity of future null infinity)",
            "topology.i_plus",
        )

    # --- weighted data class ---------------------------------------------------
    exists, space = _get(doc, "data_class.space")
    if exists and not _is_empty(space) and not RE_WEIGHTED.search(_as_text(space)):
        add(
            "R_DATA_CLASS",
            "data_class.space must name a weighted Sobolev-type space "
            "(weight/delta/fall-off must appear)",
            "data_class.space",
        )

    # --- regularity ------------------------------------------------------------
    exists, regularity = _get(doc, "regularity_of_solution")
    if exists and not _is_empty(regularity):
        text = _as_text(regularity)
        if RE_DISJUNCTION.search(text):
            add(
                "R_REGULARITY",
                "regularity_of_solution must not be a C0-or-C2 disjunction",
                "regularity_of_solution",
            )
        if len(text.strip()) < 4:
            add(
                "R_REGULARITY",
                "regularity_of_solution is too short to be exact",
                "regularity_of_solution",
            )

    # --- constraints -----------------------------------------------------------
    exists, constraints = _get(doc, "constraints")
    if (
        exists
        and not _is_empty(constraints)
        and not RE_CONSTRAINT.search(_as_text(constraints))
    ):
        add(
            "R_CONSTRAINTS",
            "constraints must name the constraint equations",
            "constraints",
        )

    # --- genericity ------------------------------------------------------------
    exists, genericity = _get(doc, "genericity")
    if exists and not isinstance(genericity, dict):
        add("R_GENERICITY", "genericity must be a mapping", "genericity")
    elif exists:
        notion = genericity.get("measure_or_topology")
        if not _is_empty(notion) and not RE_GENERIC.search(_as_text(notion)):
            add(
                "R_GENERICITY",
                "genericity.measure_or_topology must name a measure/topology notion "
                "(open dense, full measure, residual/Baire, ...); bare 'generic' is rejected",
                "genericity.measure_or_topology",
            )

    # --- visibility: class-specific -------------------------------------------
    if family == "WCC":
        exists, predicate = _get(doc, "visibility.visible_predicate")
        if not exists:
            add(
                "R_VISIBILITY",
                "WCC schema requires visibility.visible_predicate",
                "visibility.visible_predicate",
            )
        elif _is_empty(predicate):
            add(
                "R_VISIBILITY",
                "visibility.visible_predicate is empty",
                "visibility.visible_predicate",
            )
    else:
        exists, horizon = _get(doc, "visibility.cauchy_horizon")
        if not exists:
            add(
                "R_VISIBILITY",
                "SCC schema requires visibility.cauchy_horizon",
                "visibility.cauchy_horizon",
            )
        elif _is_empty(horizon):
            add(
                "R_VISIBILITY",
                "visibility.cauchy_horizon is empty",
                "visibility.cauchy_horizon",
            )

    # --- conclusion: type, statement, no inflation -----------------------------
    exists, conclusion_type = _get(doc, "conclusion.type")
    if (
        exists
        and not _is_empty(conclusion_type)
        and conclusion_type not in ALLOWED_CONCLUSION_TYPES
    ):
        add(
            "R_CONCLUSION",
            f"conclusion.type {conclusion_type!r} not in {sorted(ALLOWED_CONCLUSION_TYPES)}",
            "conclusion.type",
        )
    exists, statement = _get(doc, "conclusion.statement")
    if exists and not _is_empty(statement):
        text = _as_text(statement)
        if family == "WCC":
            if not RE_VISIBLE_CONCLUSION.search(text):
                add(
                    "R_CONCLUSION",
                    "WCC conclusion.statement must state no singularity visible from I+ "
                    "(or future asymptotic predictability)",
                    "conclusion.statement",
                )
            if RE_INEXT_CONCLUSION.search(text):
                add(
                    "R_CONCLUSION",
                    "WCC conclusion.statement must not assert inextendibility "
                    "(SCC conclusion inflation)",
                    "conclusion.statement",
                )
            if _get(doc, "conclusion.inextendibility_regularity")[0]:
                add(
                    "R_CONCLUSION",
                    "WCC schema must not carry conclusion.inextendibility_regularity",
                    "conclusion.inextendibility_regularity",
                )
        else:
            if not RE_INEXT_CONCLUSION.search(text):
                add(
                    "R_CONCLUSION",
                    "SCC conclusion.statement must assert inextendibility beyond the "
                    "Cauchy horizon",
                    "conclusion.statement",
                )
            exists_reg, conclusion_regularity = _get(
                doc, "conclusion.inextendibility_regularity"
            )
            if not exists_reg:
                add(
                    "R_CONCLUSION",
                    "SCC schema requires conclusion.inextendibility_regularity",
                    "conclusion.inextendibility_regularity",
                )
            elif (
                _as_text(conclusion_regularity).strip().upper().replace("^", "")
                != SCC_REGULARITY[class_id]
            ):
                add(
                    "R_CONCLUSION",
                    f"class {class_id} requires inextendibility regularity "
                    f"{SCC_REGULARITY[class_id]}, got {conclusion_regularity!r}",
                    "conclusion.inextendibility_regularity",
                )

    # --- falsifier -------------------------------------------------------------
    exists, witness = _get(doc, "falsifier.witness_type")
    if exists and not _is_empty(witness) and not RE_WITNESS.search(_as_text(witness)):
        add(
            "R_FALSIFIER",
            "falsifier.witness_type must be a datum in the data class",
            "falsifier.witness_type",
        )
    exists, falsifier_check = _get(doc, "falsifier.check")
    if (
        exists
        and not _is_empty(falsifier_check)
        and len(_as_text(falsifier_check).strip()) < 12
    ):
        add(
            "R_FALSIFIER",
            "falsifier.check is too short to be a check",
            "falsifier.check",
        )

    # --- source refs -----------------------------------------------------------
    exists, refs = _get(doc, "source_refs")
    if exists:
        if not isinstance(refs, list) or not refs:
            add(
                "R_SOURCE_REFS",
                "source_refs must be a non-empty list",
                "source_refs",
            )
        else:
            empty_entries = [i for i, ref in enumerate(refs) if _is_empty(ref)]
            if empty_entries:
                add(
                    "R_SOURCE_REFS",
                    f"source_refs entries {empty_entries} are empty",
                    "source_refs",
                )

    # --- leakage scan ----------------------------------------------------------
    for path, value in _leaves(doc):
        if not isinstance(value, str) or not value.strip():
            continue
        root = path[0] if path else ""
        where = ".".join(path)
        text = value
        if RE_DISJUNCTION.search(text):
            add(
                "R_DISJUNCTION",
                "a 'C0 or C2' disjunction is forbidden anywhere in a schema "
                f"(hard decision 1): {text[:120]!r}",
                where,
            )
        if root in LEAK_EXEMPT_ROOTS:
            continue
        if family == "WCC":
            if RE_SCC.search(text):
                add(
                    "R_NO_LEAK",
                    "SCC token in a WCC schema outside related_classes/source_refs: "
                    f"{text[:120]!r}",
                    where,
                )
            if RE_C0.search(text) or RE_C2.search(text):
                add(
                    "R_NO_LEAK",
                    "C0/C2 regularity token in a WCC schema outside "
                    f"related_classes/source_refs: {text[:120]!r}",
                    where,
                )
        else:
            if RE_WCC.search(text):
                add(
                    "R_NO_LEAK",
                    "WCC token in an SCC schema outside related_classes/source_refs: "
                    f"{text[:120]!r}",
                    where,
                )
            if class_id == "AF-SCC-C2-VAC-GEN" and RE_C0.search(text):
                add(
                    "R_NO_LEAK",
                    "C0 token in the C2 class outside related_classes/source_refs: "
                    f"{text[:120]!r}",
                    where,
                )
            if class_id == "AF-SCC-C0-VAC-GEN" and RE_C2.search(text):
                add(
                    "R_NO_LEAK",
                    "C2 token in the C0 class outside related_classes/source_refs: "
                    f"{text[:120]!r}",
                    where,
                )

    return violations


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Form-only class-binding acceptance gate for formulation schemas."
    )
    parser.add_argument("paths", nargs="+", help="schema documents (YAML or JSON)")
    parser.add_argument(
        "--json", action="store_true", help="emit the machine-readable report"
    )
    args = parser.parse_args(argv)

    reports = []
    for path in args.paths:
        try:
            doc = load_document(path)
        except Exception as exc:  # noqa: BLE001 - any parse failure is R_PARSE
            violation = {
                "code": "R_PARSE",
                "message": f"{type(exc).__name__}: {exc}",
                "path": "",
                "source": path,
            }
            reports.append(
                {"source": path, "class_id": None, "ok": False, "violations": [violation]}
            )
            continue
        violations = check(doc, source=path)
        reports.append(
            {
                "source": path,
                "class_id": doc.get("class_id") if isinstance(doc, dict) else None,
                "ok": not violations,
                "violations": violations,
            }
        )

    overall_ok = all(report["ok"] for report in reports)
    if args.json:
        print(json.dumps({"overall_ok": overall_ok, "reports": reports}, indent=2))
    else:
        for report in reports:
            tag = "PASS" if report["ok"] else "FAIL"
            print(f"{tag} {report['source']} (class_id={report['class_id']})")
            for violation in report["violations"]:
                print(
                    f"  {violation['code']} {violation['path']}: {violation['message']}"
                )
        print(f"overall: {'PASS' if overall_ok else 'FAIL'}")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
