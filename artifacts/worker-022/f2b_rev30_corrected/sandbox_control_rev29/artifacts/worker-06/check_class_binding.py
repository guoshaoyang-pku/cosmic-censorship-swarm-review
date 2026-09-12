#!/usr/bin/env python3
"""W06 class-binding gate (DRAFT, UNREVIEWED) for cosmic-censorship formulation schemas.

Scope: nodes F1 (AF-WCC-VAC-GEN) and F2 (AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN),
plus support for A1 independent review. Gate id: G-CLASSBIND.

What it does
------------
Reads a formulation schema (JSON or YAML) and checks structural class binding:
single class id from the declared class set, exactly one regularity selector for SCC
classes and none for WCC classes, no composite "C0 or C2" string, required slots
(quantifiers, topology, data_class, genericity, future_null_infinity, visibility,
conclusion_type), quantifier completeness, qualified genericity, conclusion-family
match, theorem-without-artifact guard, conclusion-inflation guard, and cross-domain
contamination guard.

What it does NOT do
-------------------
It does not decide mathematics. A "pass" means the document is structurally
class-bound under the drafted rule set; it is not evidence that the formulation is
correct, complete, or faithful to the literature. Rules are derived from
ASTRA_HANDOFF.md hard decisions and the F1/F2 queue text, and the F0 taxonomy is
absent, so re-derive before gate use.

Verdicts: pass | fail | inconclusive (fail dominates; inconclusive if no fail).
Exit code: 0 for pass, 1 for fail, 2 for inconclusive, 3 for usage/IO error.

Usage:
  python3 check_class_binding.py FILE [FILE ...] [--json OUT] [--strict]
  python3 check_class_binding.py --selftest [--json OUT]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RULES_PATH = HERE / "class_binding_rules.json"
FIXTURES = HERE / "fixtures"
CST = timezone(timedelta(hours=8))

PASS, FAIL, INCONC = "pass", "fail", "inconclusive"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_doc(path: Path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise SystemExit(f"yaml requested but PyYAML unavailable: {e}")
        return yaml.safe_load(raw), raw
    try:
        return json.loads(raw), raw
    except ValueError:
        try:
            import yaml  # type: ignore
            return yaml.safe_load(raw), raw
        except Exception:
            raise SystemExit(f"could not parse {path} as JSON or YAML")


def strip_meta(doc):
    """Remove the worker fixture metadata block; it is not part of the schema."""
    if isinstance(doc, dict):
        doc = {k: v for k, v in doc.items() if k != "_meta"}
    return doc


def walk(x, prefix=""):
    """Yield (dotted_key, value) for every scalar leaf."""
    if isinstance(x, dict):
        for k, v in x.items():
            yield from walk(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from walk(v, f"{prefix}[{i}]")
    else:
        yield prefix, x


def leaf_values(doc, key_regex: str):
    rx = re.compile(key_regex, re.I)
    return [(k, v) for k, v in walk(doc) if rx.search(k.rsplit(".", 1)[-1].split("[")[0])]


def full_path_values(doc, path_regex: str):
    """Scalar leaf values whose full dotted path matches path_regex."""
    rx = re.compile(path_regex, re.I)
    return [(p, v) for p, v in walk(doc) if rx.search(p)]


def key_paths(x, prefix=""):
    """Yield every dotted key path, including intermediate object keys."""
    if isinstance(x, dict):
        for k, v in x.items():
            path = f"{prefix}.{k}" if prefix else str(k)
            yield path
            yield from key_paths(v, path)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from key_paths(v, f"{prefix}[{i}]")


def check(check_id, verdict, detail, evidence=None):
    return {"check_id": check_id, "verdict": verdict, "detail": detail, "evidence": evidence or {}}


def run_checks(doc, rules, source_path: str | None = None, check_filename: bool = False):
    doc = strip_meta(doc)
    text = json.dumps(doc, ensure_ascii=False).lower()
    checks = []

    classes = rules["classes"]

    # 1. exactly one recognised class id.
    # Anti-scope polarities (anti_scope / not_this_class / variants / forbidden lists) are
    # whitelisted out: naming a foreign class there is the required way to EXCLUDE it
    # (worker-18 recommendation; lead integration item 1).
    exempt = re.compile(r"anti_scope|not_this_class|phrases_that_are_not|variants|forbidden|exempt|_not_this_class", re.I)
    cid_vals = [v for k, v in leaf_values(doc, r"^(class|class_id|class_name)$") if not exempt.search(k)]
    cid_vals = [str(v) for v in cid_vals]
    if len(cid_vals) != 1:
        checks.append(check("single_class_id", FAIL,
                            f"expected exactly one class id field, found {len(cid_vals)}: {cid_vals}"))
        return checks
    class_id = cid_vals[0]
    if class_id not in classes:
        checks.append(check("single_class_id", FAIL, f"class id {class_id!r} not in declared set {sorted(classes)}"))
        return checks
    rule = classes[class_id]
    checks.append(check("single_class_id", PASS, f"class id {class_id!r} (family {rule['family']})",
                        {"class_id": class_id}))

    # 2. declared map node / artifact agreement
    node_vals = [str(v) for k, v in leaf_values(doc, r"^(map_node|node_id)$")]
    art_vals = [str(v) for k, v in leaf_values(doc, r"^(declared_artifact|artifact|artifact_path)$")]
    expected_node, expected_art = rule.get("map_node"), rule.get("declared_artifact")
    allowed_arts = rule.get("declared_artifacts_allowed") or ([expected_art] if expected_art else [])
    problems = []
    if node_vals and expected_node and node_vals[0] != expected_node:
        problems.append(f"map_node {node_vals[0]!r} != declared {expected_node!r}")
    if art_vals and allowed_arts and art_vals[0] not in allowed_arts:
        problems.append(f"declared_artifact {art_vals[0]!r} not in allowed set {allowed_arts}")
    if check_filename and source_path and allowed_arts and Path(source_path).name not in [Path(a).name for a in allowed_arts]:
        problems.append(f"file {Path(source_path).name!r} is not one of the map-declared artifacts {allowed_arts}")
    checks.append(check("declared_artifact_matches",
                        FAIL if problems else PASS,
                        "; ".join(problems) if problems else "node/artifact fields agree with map declaration",
                        {"map_node": expected_node, "allowed_artifacts": allowed_arts}))

    # 3. composite regularity string anywhere
    hits = []
    for pat in rules["composite_regularity_regexes"]:
        for m in re.finditer(pat, text):
            hits.append(m.group(0))
    checks.append(check("no_composite_regularity_string", FAIL if hits else PASS,
                        f"composite regularity strings: {hits}" if hits else "no composite regularity string",
                        {"matches": hits}))

    # 4. regularity selector count vs class family
    reg_vals = [str(v) for _k, v in full_path_values(doc, r"regularity|differentiability|smoothness")]
    reg_tokens = []
    for v in reg_vals:
        reg_tokens += re.findall(r"\bc\s*\^?\s*([02])\b", v.lower())
    allowed = rule["regularity_allowed"]
    distinct = sorted(set(reg_tokens))
    if rule["family"] == "SCC":
        if len(distinct) != 1:
            checks.append(check("regularity_selector", FAIL,
                                f"SCC class must declare exactly one regularity class (C0 xor C2); found distinct tokens {distinct} from {reg_vals}"))
        elif f"C{distinct[0]}" not in allowed:
            checks.append(check("regularity_selector", FAIL,
                                f"regularity C{distinct[0]} not allowed for {class_id}; allowed {allowed}"))
        else:
            checks.append(check("regularity_selector", PASS, f"regularity C{distinct[0]} matches class",
                                {"regularity": f"C{distinct[0]}", "declarations": len(reg_tokens)}))
    else:
        if reg_tokens:
            checks.append(check("regularity_selector", FAIL,
                                f"WCC class carries an SCC-style regularity selector {reg_tokens} (class leakage)"))
        else:
            checks.append(check("regularity_selector", PASS, "no SCC-style regularity selector on WCC class"))

    # 5. required slots: explicit key wins; text fallback only where the rules allow it
    paths = list(key_paths(doc))
    missing, via_key, via_text = [], [], []
    for slot, alts in rules["required_slots"].items():
        kpat = rules.get("slot_key_regexes", {}).get(slot)
        has_key = bool(kpat) and any(re.search(kpat, p, re.I) for p in paths)
        has_text = any(a in text for a in alts)
        if slot in rules.get("require_explicit_key", []) and not has_key:
            missing.append(slot + " (explicit key required: prose mention in another field does not count)")
        elif has_key:
            via_key.append(slot)
        elif has_text:
            via_text.append(slot)
        else:
            missing.append(slot)
    checks.append(check("required_slots", FAIL if missing else PASS,
                        f"missing slots: {missing}" if missing else "all required slots present",
                        {"missing": missing, "present_by_key": via_key, "present_by_text_only": via_text}))

    # 6. quantifier completeness
    has_univ = any(t in text for t in rules["universal_tokens"])
    has_exist = any(t in text for t in rules["existential_tokens"])
    if not has_univ:
        checks.append(check("quantifier_completeness", FAIL,
                            "no universal quantifier over admissible initial data ('for all/every/any', '∀')"))
    elif not has_exist:
        checks.append(check("quantifier_completeness", FAIL,
                            "no existential failure-mode quantifier ('there exists/exist', '∃')"))
    else:
        checks.append(check("quantifier_completeness", PASS, "universal + existential quantifiers present"))

    # 7. genericity qualified
    gen_vals = [str(v).lower() for _k, v in full_path_values(doc, r"generic")]
    gen_text = " ".join(gen_vals)
    if not gen_vals:
        checks.append(check("genericity_qualified", FAIL, "no genericity field found"))
    elif any(q in gen_text for q in rules["genericity_qualifiers"]):
        checks.append(check("genericity_qualified", PASS, f"genericity carries a qualifier: {gen_vals}"))
    else:
        checks.append(check("genericity_qualified", FAIL,
                            f"genericity is unqualified (no {rules['genericity_qualifiers']}): {gen_vals}"))

    # 8. conclusion-family match (conclusion field only)
    concl_vals = [str(v).lower() for _k, v in full_path_values(doc, r"conclusion")]
    if not concl_vals:
        checks.append(check("conclusion_family_match", FAIL, "no conclusion_type field value"))
    else:
        ctext = " ".join(concl_vals)
        forbidden = [t for t in rule["conclusion_forbidden_tokens"] if t in ctext]
        if forbidden:
            checks.append(check("conclusion_family_match", FAIL,
                                f"conclusion {concl_vals} uses tokens from the other family: {forbidden}"))
        elif any(t in ctext for t in rule["conclusion_tokens"]):
            checks.append(check("conclusion_family_match", PASS, f"conclusion {concl_vals} matches family {rule['family']}"))
        else:
            checks.append(check("conclusion_family_match", INCONC,
                                f"conclusion {concl_vals} not recognised by the draft rule set; extend rules, do not accept",
                                {"conclusion_values": concl_vals}))

    # 9. theorem requires artifact refs (scoped to the declared conclusion_type field)
    concl_type_vals = [str(v).lower() for _k, v in full_path_values(doc, r"conclusion_type|conclusion\.type|conclusion_kind")]
    if any("theorem" in v for v in concl_type_vals):
        refs = [k for k, v in walk(doc) if re.search(r"artifact_refs?|proof_artifact|lean_file", k, re.I) and v]
        checks.append(check("theorem_requires_artifact_refs", PASS if refs else FAIL,
                            f"artifact refs present: {refs}" if refs else "conclusion_type=theorem with no artifact_refs (no fluent-text promotion)"))
    else:
        checks.append(check("theorem_requires_artifact_refs", PASS, "not a theorem conclusion; guard not triggered"))

    # 10. conclusion inflation guard
    infl = []
    for pat in rules["conclusion_inflation_regexes"]:
        for m in re.finditer(pat, text):
            infl.append(m.group(0))
    checks.append(check("no_conclusion_inflation", FAIL if infl else PASS,
                        f"inflation phrases: {infl}" if infl else "no prove/establish-theorem phrase",
                        {"matches": infl}))

    # 11. cross-domain contamination guard (base repo material must not leak into class schemas)
    contam = []
    for pat in rules["cross_domain_contamination_regexes"]:
        for m in re.finditer(pat, text):
            contam.append(m.group(0))
    checks.append(check("no_cross_domain_contamination", FAIL if contam else PASS,
                        f"cross-domain tokens: {sorted(set(contam))}" if contam else "no base-repo contamination tokens",
                        {"matches": sorted(set(contam))}))

    return checks


def overall(checks, strict=False):
    verdicts = [c["verdict"] for c in checks]
    if FAIL in verdicts:
        return FAIL
    if INCONC in verdicts:
        return FAIL if strict else INCONC
    return PASS


def evaluate(path: Path, rules, check_filename: bool = False):
    doc, raw = load_doc(path)
    checks = run_checks(doc, rules, source_path=str(path), check_filename=check_filename)
    verdict = overall(checks)
    return {
        "tool": "worker-06/check_class_binding.py",
        "rules_version": rules["rules_version"],
        "gate_id": rules["gate_id"],
        "generated_at": now(),
        "source": str(path),
        "doc_sha256": sha256_text(raw),
        "rules_sha256": sha256_text(RULES_PATH.read_text()),
        "verdict": verdict,
        "checks": checks,
    }


def selftest(rules, strict=False):
    fixtures = sorted(p for p in FIXTURES.glob("*.json") if not p.name.startswith("._"))
    results = []
    for p in fixtures:
        doc, _raw = load_doc(p)
        meta = doc.get("_meta", {}) if isinstance(doc, dict) else {}
        expected = meta.get("expected")
        checks = run_checks(doc, rules, source_path=str(p))
        got = overall(checks, strict=strict)
        results.append({
            "fixture": p.name,
            "fixture_id": meta.get("fixture_id"),
            "expected": expected,
            "got": got,
            "match": got == expected,
            "failed_checks": [c["check_id"] for c in checks if c["verdict"] == FAIL],
            "inconclusive_checks": [c["check_id"] for c in checks if c["verdict"] == INCONC],
        })
    negs = [r for r in results if r["expected"] == FAIL]
    poss = [r for r in results if r["expected"] == PASS]
    # Null controls: an always-accept gate must fail the negative corpus; an
    # always-reject gate must fail the positive corpus. If either control passes,
    # the fixture corpus has no discriminating power and the selftest fails.
    controls = {
        "always_accept_on_negatives": {
            "would_accept": len(negs),
            "control_outcome": "expected_FALSE_POSITIVES" if negs else "no_negatives",
            "passed": len(negs) > 0,
        },
        "always_reject_on_positives": {
            "would_reject": len(poss),
            "control_outcome": "expected_FALSE_NEGATIVES" if poss else "no_positives",
            "passed": len(poss) > 0,
        },
    }
    mismatched = [r for r in results if not r["match"]]
    ok = not mismatched and all(c["passed"] for c in controls.values())
    report = {
        "tool": "worker-06/check_class_binding.py --selftest",
        "generated_at": now(),
        "rules_version": rules["rules_version"],
        "fixtures": len(results),
        "negatives": len(negs),
        "positives": len(poss),
        "mismatches": mismatched,
        "controls": controls,
        "selftest_verdict": PASS if ok else FAIL,
        "results": results,
    }
    return report, (0 if ok else 1)


def main(argv=None):
    ap = argparse.ArgumentParser(description="W06 class-binding gate (draft, unreviewed)")
    ap.add_argument("files", nargs="*", help="schema files to check")
    ap.add_argument("--selftest", action="store_true", help="run the fixture corpus with null controls")
    ap.add_argument("--json", dest="json_out", help="write full JSON report here")
    ap.add_argument("--strict", action="store_true", help="treat inconclusive checks as failures")
    ap.add_argument("--check-filename", action="store_true",
                    help="also require the input filename to equal the map-declared artifact name")
    a = ap.parse_args(argv)

    rules = json.loads(RULES_PATH.read_text())
    if a.selftest:
        report, code = selftest(rules, strict=a.strict)
    else:
        if not a.files:
            ap.error("provide schema files or --selftest")
        reports = [evaluate(Path(f), rules, check_filename=a.check_filename) for f in a.files]
        codes = {PASS: 0, FAIL: 1, INCONC: 2}
        code = max(codes[r["verdict"]] for r in reports)
        report = reports[0] if len(reports) == 1 else {"reports": reports,
                                                       "verdict": overall([{"verdict": r["verdict"]} for r in reports], a.strict)}
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if a.json_out:
        Path(a.json_out).write_text(text + "\n")
    print(text if a.json_out else json.dumps(report, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
