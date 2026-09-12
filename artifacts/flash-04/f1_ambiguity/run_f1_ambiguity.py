#!/usr/bin/env python3
"""Bind the F1 ambiguity suite to a schema — or show that no field can bind it.

Two binding modes:

* **contract mode** (default while `schemas/af_wcc_vacuum.yaml` is absent): for each
  test's `deciding_field` (+ alternates), report whether FORM-RULE-SPEC R01-R16
  actually *requires* that leaf.  A gate-passing schema may satisfy every rule and
  still leave the deciding leaf unspecified — that is the attack's core finding.
* **schema mode** (`--schema PATH`): resolve the deciding field in the real schema
  document and classify the value as determinate / missing / null / unresolved.

The runner never edits the schema and never promotes a node.  Exit codes:

    0  suite valid and every test structurally bound (no missing deciding leaf)
    1  suite valid, but open ambiguity findings remain (missing / undeclared leaves)
    2  suite invalid or runner self-test failure
    3  configuration error (unreadable file, wrong format)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEFAULT_TESTS = ROOT / "schemas" / "f1_falsifier_tests.jsonl"
DEFAULT_RULE_SPEC = ROOT / "artifacts" / "formulation" / "rule_spec.json"
DEFAULT_SCHEMA = ROOT / "schemas" / "af_wcc_vacuum.yaml"

REQUIRED_TEST_KEYS = (
    "test_id", "node_id", "class_id", "spacetime_description",
    "does_it_satisfy_f1", "deciding_field", "deciding_field_status",
    "falsifier_strength", "evidence_refs", "next_falsifier",
)
ALLOWED_ANSWERS = {"yes", "no", "ambiguous"}

# Leaves explicitly named by FORM-RULE-SPEC R01-R16 (rule id cited per leaf).
CONTRACT_LEAVES: dict[str, str] = {
    "schema_version": "R01", "artifact_kind": "R01", "class_id": "R01",
    "node_id": "R01", "owner": "R01", "epistemic_status": "R01",
    "quantifiers.ordered": "R03", "quantifiers.formal": "R03", "quantifiers.domains": "R03",
    "data_class.matter": "R05", "data_class.cosmological_constant": "R05",
    "data_class.constraints": "R05", "data_class.adm_mass_status": "R05",
    "data_class.asymptotic_decay": "R05", "data_class.sobolev_index": "R05",
    "data_class.weight": "R05",
    "genericity.kind": "R07", "genericity.ambient_space": "R07",
    "genericity.topology_or_measure": "R07", "genericity.generic_set": "R07",
    "genericity.excluded_set": "R07", "genericity.transfer_failures": "R07",
    "genericity.is_part_of_class": "R07",
    "non_vacuity.condition": "R08", "non_vacuity.witness_type": "R08",
    "i_plus.role": "R09", "i_plus.completeness_definition": "R09",
    "i_plus.in_conclusion": "R09",
    "visibility.role": "R10", "visibility.definition": "R10",
    "visibility.predicate": "R10", "visibility.negation_conclusion": "R10",
    "conclusion.conclusion_type": "R11", "conclusion.epistemic_status": "R11",
    "conclusion.forbidden_strengthenings": "R11",
    "falsifier.tier_1": "R14", "falsifier.tier_2": "R14",
    "falsifier.witness_type": "R14", "falsifier.machine_checkable_steps": "R14",
    "provenance.citation_status": "R15", "provenance.unresolved_citations": "R15",
    "provenance.sources": "R15",
}
# Blocks the contract requires, without pinning every leaf inside them.
CONTRACT_BLOCKS: dict[str, str] = {
    "class_components": "R02", "topology": "R04", "regularity": "R06",
    "conclusion": "R11", "falsifier": "R14", "provenance": "R15",
    "quantifiers": "R03", "data_class": "R05", "genericity": "R07",
    "non_vacuity": "R08", "i_plus": "R09", "visibility": "R10",
}

UNRESOLVED_TOKENS = {"unresolved", "tbd", "todo", "unknown", "n/a", "na", "none?", "unset",
                     "unverified", "pending", "proposed", "draft", "partial", "provisional"}
UNRESOLVED_SUBSTRINGS = ("unresolved", "unverified", "pending", "proposed", "draft",
                         "partial", "provisional", "tbd", "todo")

# Canonical contract leaf -> candidate paths in F1 revision 2.  The schema was
# authored with its own key names (class_axes, premise, i_plus.visibility, ...), so
# an exact-name checker and the schema disagree even where the semantics match.
# The mapping is part of the audit: every entry here is a name-binding finding.
FIELD_ALIASES: dict[str, list[str]] = {
    "artifact_kind": ["artifact_type"],
    "owner": ["owner_of_record"],
    "epistemic_status": ["vocabulary_alignment.epistemic_conclusion_type"],
    "quantifiers.ordered": ["quantifiers.order"],
    "quantifiers.formal": ["quantifiers.logical_form"],
    "quantifiers.domains": ["quantifiers.scope_of_universal"],
    "topology.slice_topology": ["topology.slice_topology", "topology.initial_slice_topology"],
    "class_components.symmetry": ["data_class.symmetry", "genericity.membership_ruling"],
    "topology.conformal_boundary": ["topology.asymptotics", "i_plus.name"],
    "topology.forbidden": ["class_separation.prohibitions"],
    "data_class.matter": ["matter", "class_axes.matter_model"],
    "data_class.cosmological_constant": ["matter"],
    "data_class.adm_mass_status": ["data_class.adm_mass", "data_class.mass"],
    "data_class.asymptotic_decay": ["data_class.asymptotic_decay", "data_class.decay"],
    "data_class.sobolev_index": ["data_class.regularity", "data_class.weighted_norm"],
    "data_class.weight": ["data_class.weighted_norm"],
    "regularity.data_regularity": ["data_class.regularity"],
    "regularity.solution_regularity": ["premise.regularity_of_development"],
    "regularity.extension_solution_concept": ["premise.regularity_of_development"],
    "regularity.must_not_conflate": ["unresolved"],
    "genericity.ambient_space": ["genericity.parameter_space"],
    "genericity.topology_or_measure": ["genericity.topology_name"],
    "genericity.generic_set": ["genericity.kind"],
    "genericity.excluded_set": ["genericity.known_non_generic_exceptions"],
    "genericity.is_part_of_class": ["genericity.load_bearing"],
    "non_vacuity.condition": ["data_class.mass"],
    "non_vacuity.witness_type": ["data_class.mass"],
    "i_plus.role": ["class_separation.visibility_is_a_conclusion_here"],
    "i_plus.completeness_definition": ["i_plus.defining_properties"],
    "i_plus.in_conclusion": ["class_separation.visibility_is_a_conclusion_here"],
    "visibility.role": ["class_separation.visibility_is_a_conclusion_here"],
    "visibility.definition": ["i_plus.visibility.definition"],
    "visibility.predicate": ["i_plus.visibility.definition"],
    "visibility.negation_conclusion": ["i_plus.visibility.formal_negation"],
    "conclusion.conclusion_type": ["conclusion.conclusion_type", "conclusion.family"],
    "conclusion.equivalence_claim": ["conclusion.equivalent_standard_formulation",
                                     "conclusion.statement_formal"],
    "conclusion.epistemic_status": ["conclusion.type", "vocabulary_alignment.epistemic_conclusion_type"],
    "conclusion.forbidden_strengthenings": ["conclusion.forbidden_imports"],
    "falsifier.tier_1": ["falsifier.class_level"],
    "falsifier.tier_2": ["falsifier.schema_level"],
    "falsifier.witness_type": ["falsifier.nearest_known_witness"],
    "falsifier.machine_checkable_steps": ["verification_checklist_self_run"],
    "provenance.citation_status": ["evidence_refs.primary_sources_verified_2026_09_11"],
    "provenance.unresolved_citations": ["unresolved"],
    "provenance.sources": ["evidence_refs.primary_sources_verified_2026_09_11"],
}

# Unresolved-list entries that name a field under a different spelling.
UNRESOLVED_ALIASES: dict[str, list[str]] = {
    "genericity.kind_and_ambient_space": ["genericity.kind", "genericity.ambient_space",
                                           "genericity.topology_or_measure"],
    "data_class.topology": ["topology.slice_topology"],
    "data_class.mass": ["data_class.adm_mass_status"],
    "non_vacuity.witness": ["non_vacuity.witness_type", "non_vacuity.condition"],
    "data_class.weighted_norm": ["data_class.sobolev_index", "data_class.weight"],
    "premise.future_boundary": ["visibility.definition", "topology.conformal_boundary"],
    "visibility.curve_class": ["visibility.definition", "i_plus.completeness_definition"],
    "visibility.set_vs_point": ["visibility.definition", "visibility.set_vs_point"],
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_tests(path: Path) -> list[dict]:
    rows = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{i}: {exc}") from exc
    return rows


def validate_tests(rows: list[dict]) -> list[str]:
    errors = []
    if len(rows) < 10:
        errors.append(f"acceptance requires >=10 tests, found {len(rows)}")
    seen = set()
    for r in rows:
        rid = r.get("test_id", "?")
        for k in REQUIRED_TEST_KEYS:
            if k not in r:
                errors.append(f"{rid}: missing key {k}")
        if rid in seen:
            errors.append(f"{rid}: duplicate test_id")
        seen.add(rid)
        if r.get("does_it_satisfy_f1") not in ALLOWED_ANSWERS:
            errors.append(f"{rid}: does_it_satisfy_f1={r.get('does_it_satisfy_f1')!r}")
        # deciding_field may be null by design (the declared falsifier); key must exist.
        df = r.get("deciding_field")
        if df is not None and not isinstance(df, str):
            errors.append(f"{rid}: deciding_field must be str or null")
    return errors


def resolve(doc: Any, dotted: str) -> tuple[bool, Any]:
    cur = doc
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False, None
    return True, cur


def classify_value(found: bool, value: Any) -> str:
    if not found:
        return "missing"
    if value is None:
        return "null_value"
    if isinstance(value, str):
        s = value.strip().lower()
        if s in UNRESOLVED_TOKENS or any(tok in s for tok in UNRESOLVED_SUBSTRINGS):
            return "unresolved_value"
        return "determinate"
    if isinstance(value, dict):
        if value.get("unresolved") is True:
            return "unresolved_value"
        if str(value.get("status", "")).strip().lower() in UNRESOLVED_TOKENS:
            return "unresolved_value"
        if not value:
            return "empty_value"
        return "determinate"
    if isinstance(value, (list, tuple)):
        return "empty_value" if len(value) == 0 else "determinate"
    return "determinate"


def contract_status(path: str) -> tuple[str, str]:
    """Return (status, rule) for a dotted deciding-field path under the contract."""
    if path in CONTRACT_LEAVES:
        return "leaf_required", CONTRACT_LEAVES[path]
    block = path.split(".")[0]
    if block in CONTRACT_BLOCKS:
        return "block_required_only", CONTRACT_BLOCKS[block]
    return "not_required", ""


def bind_contract(rows: list[dict], rule_spec_path: Path) -> dict:
    results = []
    for r in rows:
        candidates = [p for p in [r["deciding_field"], *r.get("deciding_field_alternates", [])] if p]
        statuses = [contract_status(p) for p in candidates]
        best = None
        for p, (st, rule) in zip(candidates, statuses):
            if st == "leaf_required":
                best = (p, st, rule)
                break
        if best is None and candidates:
            best = (candidates[0], statuses[0][0], statuses[0][1])
        results.append({
            "test_id": r["test_id"],
            "deciding_field": r["deciding_field"],
            "alternates": r.get("deciding_field_alternates", []),
            "contract_candidate": best[0] if best else None,
            "contract_status": best[1] if best else "no_candidate",
            "contract_rule": best[2] if best else "",
            "semantic_status": r["deciding_field_status"],
            "falsifier_strength": r["falsifier_strength"],
            "open": (best is None) or best[1] != "leaf_required",
            "why_open": (
                "no deciding field or alternate declared"
                if best is None else
                f"deciding leaf not required by contract ({best[1]})"
                if best[1] != "leaf_required" else ""
            ),
        })
    return {
        "mode": "contract",
        "rule_spec_path": str(rule_spec_path),
        "rule_spec_sha256": sha256_file(rule_spec_path) if rule_spec_path.exists() else None,
        "rows": results,
    }


def _extract_unresolved(doc: Any) -> list[dict]:
    out = []
    if not isinstance(doc, dict):
        return out
    for u in doc.get("unresolved", []) or []:
        if isinstance(u, dict) and u.get("field"):
            out.append({
                "field": str(u["field"]),
                "why": str(u.get("why", ""))[:240],
                "resolution_requires": str(u.get("resolution_requires", ""))[:200],
            })
    return out


def _unresolved_match(entry_field: str, paths: list[str]) -> str | None:
    for p in paths:
        if not p:
            continue
        if entry_field == p or entry_field.startswith(p + ".") or p.startswith(entry_field + "."):
            return p
        if p in UNRESOLVED_ALIASES.get(entry_field, []):
            return p
    # allow an unresolved entry to match an alias target of a deciding path
    for p in paths:
        for alias in FIELD_ALIASES.get(p, []):
            if alias == entry_field:
                return p
    return None


def _resolve_one(doc: Any, path: str):
    """Resolve one path, then its aliases. Returns (path, kind, value)."""
    found, value = resolve(doc, path)
    if found:
        return path, "exact", value
    for alias in FIELD_ALIASES.get(path, []):
        f2, v2 = resolve(doc, alias)
        if f2:
            return alias, f"alias_of:{path}", v2
    return None, "not_found", None


def bind_schema(rows: list[dict], schema_path: Path) -> dict:
    import yaml

    doc = yaml.safe_load(schema_path.read_text())
    unresolved = _extract_unresolved(doc)
    unresolved_items = [str(x) for x in (doc.get("unresolved_items") or []) if isinstance(x, str)]
    results = []
    for r in rows:
        # The primary deciding field is authoritative: an alternate is only used
        # when the primary path is absent (naming drift), never to override an
        # unresolved primary value.
        path, kind, value = (None, "not_found", None)
        primary = r.get("deciding_field")
        if primary:
            path, kind, value = _resolve_one(doc, primary)
        if path is None:
            for alt in r.get("deciding_field_alternates", []):
                path, kind, value = _resolve_one(doc, alt)
                if path is not None:
                    break
        if path is None and r.get("deciding_field_contract"):
            path, kind, value = _resolve_one(doc, r["deciding_field_contract"])
        klass = classify_value(path is not None, value)
        candidates = [p for p in
                      [r.get("deciding_field"), *r.get("deciding_field_alternates", []),
                       r.get("deciding_field_contract")]
                      if p]
        declared = None
        for entry in unresolved:
            matched = _unresolved_match(entry["field"], candidates)
            if matched:
                declared = entry
                break
        if declared is None:
            keywords = [str(k).lower() for k in (r.get("unresolved_keywords") or [])]
            if keywords:
                for item in unresolved_items:
                    if any(k in item.lower() for k in keywords):
                        declared = {"field": item[:120], "why": item, "resolution_requires": ""}
                        break
        open_flag = (klass != "determinate") or (declared is not None)
        why = []
        if klass != "determinate":
            why.append(f"deciding value is {klass}")
        if declared is not None:
            why.append(f"declared unresolved by schema ({declared['field']})")
        expectation = r.get("schema_open_expected")
        results.append({
            "test_id": r["test_id"],
            "deciding_field": r.get("deciding_field"),
            "deciding_field_contract": r.get("deciding_field_contract"),
            "alternates": r.get("deciding_field_alternates", []),
            "resolved_path": path,
            "resolution_kind": kind,
            "value_class": klass,
            "value_preview": (str(value)[:200] if value is not None else None),
            "declared_unresolved": declared is not None,
            "unresolved_entry": (declared["field"] if declared else None),
            "semantic_status": r.get("deciding_field_status"),
            "falsifier_strength": r["falsifier_strength"],
            "open": open_flag,
            "why_open": "; ".join(why),
            "schema_open_expected": expectation,
            "expectation_match": (None if expectation is None else expectation == open_flag),
        })
    return {
        "mode": "schema",
        "schema_path": str(schema_path),
        "schema_sha256": sha256_file(schema_path),
        "schema_unresolved_entries": unresolved,
        "schema_unresolved_items": unresolved_items,
        "contract_leaf_audit": audit_contract_leaves(doc),
        "rows": results,
    }


def audit_contract_leaves(doc: Any) -> dict:
    """Which FORM-RULE-SPEC leaves exist in the schema under their exact R-name?"""
    entries = []
    for leaf, rule in sorted(CONTRACT_LEAVES.items()):
        found, value = resolve(doc, leaf)
        if found:
            entries.append({"leaf": leaf, "rule": rule, "status": "present_exact",
                            "schema_path": leaf, "value_class": classify_value(True, value)})
            continue
        alias_hit = None
        for alias in FIELD_ALIASES.get(leaf, []):
            f2, v2 = resolve(doc, alias)
            if f2:
                alias_hit = (alias, v2)
                break
        if alias_hit:
            entries.append({"leaf": leaf, "rule": rule, "status": "present_via_alias",
                            "schema_path": alias_hit[0],
                            "value_class": classify_value(True, alias_hit[1])})
        else:
            entries.append({"leaf": leaf, "rule": rule, "status": "missing",
                            "schema_path": None, "value_class": None})
    counts = {s: sum(1 for e in entries if e["status"] == s)
              for s in ("present_exact", "present_via_alias", "missing")}
    return {"counts": counts, "entries": entries}


def summarize(binding: dict) -> dict:
    rows = binding["rows"]
    open_rows = [r for r in rows if r["open"]]
    structural = {
        "tests": len(rows),
        "determinate": sum(1 for r in rows if not r["open"]),
        "open": len(open_rows),
        "declared_unresolved_rows": sum(1 for r in rows if r.get("declared_unresolved")),
        "expectation_mismatches": [r["test_id"] for r in rows
                                   if r.get("expectation_match") is False],
    }
    if binding["mode"] == "contract":
        structural["leaf_required"] = sum(1 for r in rows if r.get("contract_status") == "leaf_required")
        structural["block_required_only"] = sum(1 for r in rows if r.get("contract_status") == "block_required_only")
        structural["not_required"] = sum(1 for r in rows if r.get("contract_status") == "not_required")
        structural["no_candidate"] = sum(1 for r in rows if r.get("contract_status") == "no_candidate")
    else:
        structural["contract_leaf_audit"] = binding["contract_leaf_audit"]["counts"]
    findings = [r["test_id"] for r in rows if r["falsifier_strength"] != "decided"]
    return {
        "structural": structural,
        "open_findings": [r["test_id"] for r in open_rows],
        "attack_findings": findings,
        "counterexample_candidates": [r["test_id"] for r in rows
                                      if r["falsifier_strength"] == "counterexample_candidate"],
    }


def report_digest(report: dict) -> str:
    payload = {k: v for k, v in report.items() if k != "report_digest"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def self_test() -> int:
    checks = []
    full = {
        "non_vacuity": {"condition": "nonzero ADM mass", "witness_type": "incomplete development"},
        "quantifiers": {"ordered": [{"kind": "forall"}], "domains": {"D1": "AF data"}},
        "class_components": {"symmetry": "no symmetry assumed"},
        "topology": {"slice_topology": {"connected": True}, "conformal_boundary": {"complete": True}},
        "genericity": {"kind": "baire_residual", "ambient_space": "weighted Sobolev data space"},
        "regularity": {"solution_regularity": "C^2"},
        "data_class": {"matter": "vacuum"},
        "visibility": {"definition": "causal geodesic visibility"},
        "conclusion": {"equivalence_claim": "definitional"},
    }
    cases = [
        ("determinate_str", classify_value(True, "C^2"), "determinate"),
        ("unresolved_str", classify_value(True, "unresolved"), "unresolved_value"),
        ("null_str", classify_value(True, None), "null_value"),
        ("missing", classify_value(False, None), "missing"),
        ("empty_list", classify_value(True, []), "empty_value"),
        ("nested_resolve", classify_value(*resolve(full, "genericity.kind")), "determinate"),
        ("nested_missing", classify_value(*resolve(full, "genericity.nope")), "missing"),
    ]
    for name, got, want in cases:
        checks.append((name, got == want, got, want))
    # classification must not crash on odd docs
    checks.append(("resolve_on_scalar", resolve(42, "a.b")[0] is False, None, None))
    failed = [c for c in checks if not c[1]]
    for name, ok, got, want in checks:
        print(f"self-test {name}: {'ok' if ok else 'FAIL'} (got={got!r} want={want!r})")
    return 2 if failed else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tests", default=str(DEFAULT_TESTS))
    ap.add_argument("--schema", default=None,
                    help="schema YAML to bind against; default: schema mode if "
                         f"{DEFAULT_SCHEMA} exists, else contract mode")
    ap.add_argument("--rule-spec", default=str(DEFAULT_RULE_SPEC))
    ap.add_argument("--out", default=None, help="write the JSON report here")
    ap.add_argument("--expect-sha", default=None,
                    help="expected schema sha256 prefix; a mismatch is recorded as schema_drift")
    ap.add_argument("--validate-only", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    tests_path = Path(args.tests)
    if not tests_path.exists():
        print(f"tests file not found: {tests_path}", file=sys.stderr)
        return 3
    try:
        rows = load_tests(tests_path)
    except ValueError as exc:
        print(f"invalid suite: {exc}", file=sys.stderr)
        return 2
    errors = validate_tests(rows)
    if errors:
        print("SUITE INVALID")
        for e in errors:
            print(" -", e)
        return 2
    if args.validate_only:
        print(f"SUITE VALID rows={len(rows)} sha256={sha256_file(tests_path)}")
        return 0

    schema_path = Path(args.schema) if args.schema else (DEFAULT_SCHEMA if DEFAULT_SCHEMA.exists() else None)
    if schema_path is not None:
        if not schema_path.exists():
            print(f"schema not found: {schema_path}", file=sys.stderr)
            return 3
        try:
            binding = bind_schema(rows, schema_path)
        except Exception as exc:  # malformed YAML must be a config error, not a crash
            print(f"cannot bind schema {schema_path}: {exc}", file=sys.stderr)
            return 3
    else:
        rule_spec = Path(args.rule_spec)
        if not rule_spec.exists():
            print(f"rule spec not found: {rule_spec}", file=sys.stderr)
            return 3
        binding = bind_contract(rows, rule_spec)

    summary = summarize(binding)
    drift = None
    if args.expect_sha and binding.get("mode") == "schema":
        actual = binding["schema_sha256"]
        if not actual.startswith(args.expect_sha.lower()):
            drift = {"expected_prefix": args.expect_sha, "actual_sha256": actual}
            print(f"WARNING: schema drift: expected {args.expect_sha}, bound {actual}",
                  file=sys.stderr)
    report = {
        "runner": "f1_ambiguity_runner",
        "runner_version": "0.2.0",
        "created_by": "deepseek-flash-04",
        "assignment": "asg-2026-09-11-F1-deepseek-flash-04-13",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "tests_path": str(tests_path),
        "tests_sha256": sha256_file(tests_path),
        "tests_count": len(rows),
        "schema_drift": drift,
        **binding,
        "summary": summary,
        "verdict": ("STRUCTURALLY_BOUND" if summary["structural"]["open"] == 0
                    else "OPEN_AMBIGUITY_FINDINGS"),
        "non_claim": ("Structural binding only. A determinate value does not mean the field is "
                      "semantically sufficient; rows with falsifier_strength other than 'decided' "
                      "remain open review items (gate G-FORM / A1)."),
    }
    report["report_digest"] = report_digest(report)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n")
    print(text)
    return 0 if summary["structural"]["open"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
