#!/usr/bin/env python3
"""Checker for schemas/taxonomy_cases.jsonl (F0 / G-F0, assignment asg-...-flash-02-11).

What this validates
-------------------
1. Structure and vocabulary of every case against research_map/formulation_taxonomy.yaml.
2. Positives resolve to exactly ONE class by axis vector.
3. Negatives do NOT resolve to their filed class (axis cases), or carry a named,
   vocabulary-level / textual / semantic leak witness (out_of_vocabulary, lexical, semantic).
4. Coverage: >= 8 positives and >= 8 negatives, every class represented in both polarities.
5. Pairwise class disjointness on the taxonomy axis vectors (else nothing could be unique).
6. Negative controls ("run the null first"): mutated corpora must be REJECTED. If a control
   escapes, the checker itself is declared untrustworthy and exits nonzero.

This checker adjudicates corpus properties and axis-level classification only. It does NOT
adjudicate semantics, mathematical truth, or class membership of any physical statement.

Usage:
  python3 artifacts/flash-02/check_taxonomy_cases.py \
      --taxonomy research_map/formulation_taxonomy.yaml \
      --cases schemas/taxonomy_cases.jsonl \
      --catalog artifacts/flash-02/leak_rule_catalog.json \
      --report artifacts/flash-02/taxonomy_cases_check_report.json
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import sys
from pathlib import Path

import yaml

AXES = ["family", "matter_model", "symmetry", "asymptotics", "regularity_token",
        "genericity_kind", "conclusion_type"]
POSITIVE_REQUIRED = ["case_id", "polarity", "class_id", "as_filed_class_id", "statement",
                     "decisive_hypothesis", "decisive_axes", "axis_vector", "violated_vocabulary",
                     "expected_verdict", "expected_classification", "expected_leak_rule",
                     "leak_kind", "gate_expectation", "expected_resolution", "open",
                     "falsifier", "evidence_refs", "binding_status"]
NEGATIVE_REQUIRED = [f for f in POSITIVE_REQUIRED if f != "class_id"] + ["class_id"]
SEMANTIC_MIN_PENDING = 1


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_axes(d: dict) -> tuple:
    return tuple((k, d.get(k)) for k in AXES)


def load_taxonomy(path: Path) -> dict:
    doc = yaml.safe_load(path.read_text())
    classes = {}
    vocab = {}
    for cid, cls in doc["classes"].items():
        classes[cid] = dict(cls["axes"])
    for axis, spec in doc["field_vocabulary"].items():
        vocab[axis] = list(spec.get("allowed", []))
    return {
        "class_ids": list(doc["class_ids"]),
        "classes": classes,
        "vocab": vocab,
        "guards": {g["id"]: g["rule"] for g in doc.get("guards", [])},
        "allowed_transfers": [t["id"] for t in doc.get("transfer_rules", {}).get("allowed", [])],
        "forbidden_transfers": [t["id"] for t in doc.get("transfer_rules", {}).get("forbidden", [])],
        "doc": doc,
    }


def load_cases(path: Path):
    meta, cases = None, []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError as e:
            raise SystemExit(f"{path}:{i}: invalid JSON: {e}")
        if obj.get("record_type") == "meta":
            meta = obj
        else:
            cases.append(obj)
    if meta is None:
        raise SystemExit(f"{path}: missing meta record")
    return meta, cases


def resolve(axes, taxonomy):
    if axes is None:
        return []
    return sorted(cid for cid, a in taxonomy["classes"].items() if norm_axes(a) == norm_axes(axes))


def in_vocabulary(axes, vocab):
    bad = []
    if axes is None:
        return [("axis_vector", None, "missing")]
    for k in AXES:
        if k not in axes:
            bad.append((k, None, "missing"))
            continue
        v = axes[k]
        allowed = vocab.get(k, [])
        if v not in allowed:
            bad.append((k, v, allowed))
    return bad


def check_corpus(cases, taxonomy, catalog) -> list:
    errors = []
    seen = {}
    classes = taxonomy["classes"]
    vocab = taxonomy["vocab"]
    rules = {r.get("rule_id"): r for r in catalog["rules"]}

    if len(set(classes)) != 4:
        errors.append(f"TAXONOMY: expected 4 classes, found {len(classes)}")
    if len({norm_axes(a) for a in classes.values()}) != len(classes):
        errors.append("TAXONOMY: two classes share an identical axis vector (nothing is uniquely classifiable)")

    counts = {"positive": 0, "negative": 0}
    cov = {"positive": {c: 0 for c in classes}, "negative": {c: 0 for c in classes}}
    kinds = {}
    pending_semantic = []

    for c in cases:
        cid = c.get("case_id", "<no-id>")
        if cid in seen:
            errors.append(f"DUPLICATE_CASE_ID: {cid}")
            continue
        seen[cid] = True
        pol = c.get("polarity")
        if pol not in ("positive", "negative"):
            errors.append(f"{cid}: BAD_POLARITY {pol!r}")
            continue
        counts[pol] += 1
        required = POSITIVE_REQUIRED if pol == "positive" else NEGATIVE_REQUIRED
        for f in required:
            if f not in c:
                errors.append(f"{cid}: MISSING_FIELD {f}")

        # exactly one declared gate resolution per case (oracle property)
        res = str(c.get("expected_resolution", ""))
        prefixes = ["unique_class:", "reject_misfiled:target=", "reject_new_class_required",
                    "reject_split_required", "reject_leak:"]
        if len([p for p in prefixes if res.startswith(p)]) != 1:
            errors.append(f"{cid}: BAD_EXPECTED_RESOLUTION {res!r}")
        if not isinstance(c.get("open"), bool):
            errors.append(f"{cid}: BAD_OPEN_FLAG {c.get('open')!r}")

        # vocabulary
        if c.get("axis_vector") is not None:
            bad = in_vocabulary(c["axis_vector"], vocab)
            for k, v, allowed in bad:
                errors.append(f"{cid}: VOCAB axis {k}={v!r} allowed={allowed}")

        if pol == "positive":
            av = c.get("axis_vector")
            r = resolve(av, taxonomy)
            if len(r) != 1:
                errors.append(f"{cid}: POSITIVE_NOT_SINGLE_CLASS resolve={r}")
            else:
                cov["positive"][r[0]] += 1
                if c.get("class_id") != r[0]:
                    errors.append(f"{cid}: POSITIVE_CLASS_MISMATCH class_id={c.get('class_id')} resolve={r[0]}")
                if c.get("as_filed_class_id") != r[0]:
                    errors.append(f"{cid}: POSITIVE_FILED_MISMATCH as_filed={c.get('as_filed_class_id')}")
                if c.get("expected_classification") != r[0]:
                    errors.append(f"{cid}: POSITIVE_EXPECTATION_MISMATCH expected={c.get('expected_classification')}")
            if c.get("expected_verdict") != "accept":
                errors.append(f"{cid}: POSITIVE_VERDICT {c.get('expected_verdict')!r}")
            if c.get("expected_leak_rule") is not None or c.get("leak_kind") != "none":
                errors.append(f"{cid}: POSITIVE_CARRIES_LEAK")
            if r and res != f"unique_class:{r[0]}":
                errors.append(f"{cid}: EXPECTED_RESOLUTION_MISMATCH {res!r} != unique_class:{r[0]}")
            if c.get("open") is not False:
                errors.append(f"{cid}: POSITIVE_MARKED_OPEN")
            continue

        # negatives
        if c.get("expected_verdict") != "reject":
            errors.append(f"{cid}: NEGATIVE_VERDICT {c.get('expected_verdict')!r}")
        rule_id = c.get("expected_leak_rule")
        if rule_id not in rules:
            errors.append(f"{cid}: UNKNOWN_LEAK_RULE {rule_id!r}")
        kind = c.get("leak_kind")
        kinds[kind] = kinds.get(kind, 0) + 1
        filed = c.get("as_filed_class_id")
        av = c.get("axis_vector")
        r = resolve(av, taxonomy)
        if filed in classes:
            cov["negative"][filed] += 1
        elif isinstance(c.get("expected_classification"), str) and c["expected_classification"] in classes:
            cov["negative"][c["expected_classification"]] += 1
        else:
            for x in r:
                cov["negative"][x] += 1

        if kind == "axis":
            if av is None:
                errors.append(f"{cid}: AXIS_CASE_MISSING_AXIS_VECTOR")
            elif r == [filed]:
                errors.append(f"{cid}: NEGATIVE_CLEAN_MEMBER resolves to filed class {filed}")
            exp = c.get("expected_classification")
            if exp in classes and r != [exp]:
                errors.append(f"{cid}: AXIS_EXPECTATION_MISMATCH expected={exp} resolve={r}")
            if exp == "NO_CLASS_IN_TAXONOMY" and r != []:
                errors.append(f"{cid}: AXIS_EXPECTATION_MISMATCH expected no class, resolve={r}")
            if exp == "NO_CLASS_IN_TAXONOMY":
                if res != "reject_new_class_required" or c.get("open") is not True:
                    errors.append(f"{cid}: EXPECTED_RESOLUTION_MISMATCH {res!r} open={c.get('open')!r}")
            elif exp in classes:
                if res != f"reject_misfiled:target={exp}" or c.get("open") is not False:
                    errors.append(f"{cid}: EXPECTED_RESOLUTION_MISMATCH {res!r} open={c.get('open')!r}")
        elif kind == "out_of_vocabulary":
            if res != "reject_new_class_required" or c.get("open") is not True:
                errors.append(f"{cid}: EXPECTED_RESOLUTION_MISMATCH {res!r} open={c.get('open')!r}")
            vv = c.get("violated_vocabulary")
            if not vv:
                errors.append(f"{cid}: OUT_OF_VOCAB_NO_VIOLATION")
            else:
                for e in vv:
                    if e.get("axis") not in AXES:
                        errors.append(f"{cid}: OUT_OF_VOCAB_BAD_AXIS {e.get('axis')!r}")
                    if e.get("value") in (vocab.get(e.get("axis"), []) or []):
                        errors.append(f"{cid}: OUT_OF_VOCAB_VALUE_IS_ALLOWED {e.get('axis')}={e.get('value')!r}")
        elif kind == "lexical":
            if av is not None and filed in classes and r != [filed]:
                errors.append(f"{cid}: LEXICAL_CASE_AXES_NOT_CLEAN resolve={r}")
            pat = c.get("text_pattern") or (rules.get(rule_id, {}) or {}).get("pattern")
            if not pat:
                errors.append(f"{cid}: LEXICAL_NO_PATTERN")
            elif not re.search(pat, c.get("statement", "")):
                errors.append(f"{cid}: LEXICAL_PATTERN_NOT_PRESENT {pat!r}")
            if res != f"reject_leak:{rule_id}" or c.get("open") is not False:
                errors.append(f"{cid}: EXPECTED_RESOLUTION_MISMATCH {res!r} open={c.get('open')!r}")
        elif kind == "semantic":
            if not c.get("semantic_witness"):
                errors.append(f"{cid}: SEMANTIC_NO_WITNESS")
            if av is not None and filed in classes and r != [filed] and not c.get("violated_vocabulary"):
                errors.append(f"{cid}: SEMANTIC_AXES_NOT_CLEAN_OR_VIOLATION resolve={r}")
            if av is None and not c.get("violated_vocabulary"):
                errors.append(f"{cid}: SEMANTIC_NO_AXIS_AND_NO_VIOLATION")
            for tok in c.get("forbidden_tokens_absent", []) or []:
                if tok.lower() in c.get("statement", "").lower():
                    errors.append(f"{cid}: PARAPHRASE_TOKEN_PRESENT {tok!r}")
            if str(c.get("expected_classification", "")).startswith("AMBIGUOUS"):
                if res != "reject_split_required" or c.get("open") is not True:
                    errors.append(f"{cid}: EXPECTED_RESOLUTION_MISMATCH {res!r} open={c.get('open')!r}")
            else:
                if res != f"reject_leak:{rule_id}" or c.get("open") is not False:
                    errors.append(f"{cid}: EXPECTED_RESOLUTION_MISMATCH {res!r} open={c.get('open')!r}")
            pending_semantic.append(cid)
        else:
            errors.append(f"{cid}: BAD_LEAK_KIND {kind!r}")

    # coverage
    if counts["positive"] < 8:
        errors.append(f"COVERAGE: positive cases {counts['positive']} < 8")
    if counts["negative"] < 8:
        errors.append(f"COVERAGE: negative cases {counts['negative']} < 8")
    for c in classes:
        if cov["positive"][c] < 2:
            errors.append(f"COVERAGE: class {c} has {cov['positive'][c]} positive cases (<2)")
        if cov["negative"][c] < 2:
            errors.append(f"COVERAGE: class {c} has {cov['negative'][c]} negative cases (<2)")
    if len(pending_semantic) < SEMANTIC_MIN_PENDING:
        errors.append("COVERAGE: no semantic-leak cases present")
    return errors, counts, cov, kinds, pending_semantic


def mutate(cases, control_id):
    """Return a mutated copy of the corpus for control control_id."""
    import copy
    m = copy.deepcopy(cases)
    if control_id == "C1_positive_axis_flip":
        for c in m:
            if c["case_id"] == "TC-F0-P01":
                c["axis_vector"]["matter_model"] = "massless_scalar_field"
        return m
    if control_id == "C2_negative_clean_member":
        for c in m:
            if c["case_id"] == "TC-F0-N03":
                c["as_filed_class_id"] = "AF-SCC-C2-VAC-GEN"
        return m
    if control_id == "C3_drop_class_coverage":
        return [c for c in m if not (c.get("polarity") == "positive"
                                     and c.get("class_id") == "AF-WCC-SCALAR-SPH")]
    if control_id == "C4_duplicate_case_id":
        for c in m:
            if c["case_id"] == "TC-F0-P02":
                c["case_id"] = "TC-F0-P01"
        return m
    if control_id == "C5_unknown_leak_rule":
        for c in m:
            if c["case_id"] == "TC-F0-N05":
                c["expected_leak_rule"] = "NOT-A-RULE"
        return m
    if control_id == "C6_bad_vocabulary_value":
        for c in m:
            if c["case_id"] == "TC-F0-P05":
                c["axis_vector"]["family"] = "SCC_MAYBE"
        return m
    if control_id == "C7_semantic_without_witness":
        for c in m:
            if c["case_id"] == "TC-F0-N08":
                c["semantic_witness"] = ""
        return m
    if control_id == "C8_lexical_pattern_absent":
        for c in m:
            if c["case_id"] == "TC-F0-N05":
                c["statement"] = "No forbidden token here."
        return m
    if control_id == "C9_bad_expected_resolution":
        for c in m:
            if c["case_id"] == "TC-F0-P01":
                c["expected_resolution"] = "unique_class:AF-SCC-C2-VAC-GEN"
        return m
    if control_id == "C10_negative_wrong_resolution_kind":
        for c in m:
            if c["case_id"] == "TC-F0-N03":
                c["expected_resolution"] = "reject_leak:G4-SYMMETRY-RELEASE"
        return m
    raise ValueError(control_id)


CONTROLS = [
    ("C1_positive_axis_flip", "POSITIVE_NOT_SINGLE_CLASS"),
    ("C2_negative_clean_member", "NEGATIVE_CLEAN_MEMBER"),
    ("C3_drop_class_coverage", "COVERAGE"),
    ("C4_duplicate_case_id", "DUPLICATE_CASE_ID"),
    ("C5_unknown_leak_rule", "UNKNOWN_LEAK_RULE"),
    ("C6_bad_vocabulary_value", "VOCAB"),
    ("C7_semantic_without_witness", "SEMANTIC_NO_WITNESS"),
    ("C8_lexical_pattern_absent", "LEXICAL_PATTERN_NOT_PRESENT"),
    ("C9_bad_expected_resolution", "EXPECTED_RESOLUTION_MISMATCH"),
    ("C10_negative_wrong_resolution_kind", "EXPECTED_RESOLUTION_MISMATCH"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--taxonomy", default="research_map/formulation_taxonomy.yaml")
    ap.add_argument("--cases", default="schemas/taxonomy_cases.jsonl")
    ap.add_argument("--catalog", default="artifacts/flash-02/leak_rule_catalog.json")
    ap.add_argument("--report", default="artifacts/flash-02/taxonomy_cases_check_report.json")
    a = ap.parse_args()

    tpath, cpath, kpath = Path(a.taxonomy), Path(a.cases), Path(a.catalog)
    taxonomy = load_taxonomy(tpath)
    meta, cases = load_cases(cpath)
    catalog = json.loads(kpath.read_text())
    if catalog.get("taxonomy_ref", {}).get("sha256") != sha256_file(tpath):
        print("WARN: catalog taxonomy_ref.sha256 differs from the taxonomy file on disk")

    errors, counts, cov, kinds, pending = check_corpus(cases, taxonomy, catalog)

    controls = []
    ok_controls = True
    for cid, expected in CONTROLS:
        try:
            mutated = mutate(cases, cid)
            merr, *_ = check_corpus(mutated, taxonomy, catalog)
        except Exception as e:  # control construction itself failed -> checker problem
            merr = [f"CONTROL_EXCEPTION {e}"]
        detected = any(expected in e for e in merr)
        ok_controls = ok_controls and detected
        controls.append({"control_id": cid, "expected_error": expected,
                         "detected": detected, "errors": merr[:4]})

    # pairwise disjointness of the four class axis vectors
    pairs = []
    for a1, a2 in itertools.combinations(sorted(taxonomy["classes"]), 2):
        diff = [k for k in AXES if taxonomy["classes"][a1].get(k) != taxonomy["classes"][a2].get(k)]
        pairs.append({"pair": [a1, a2], "differing_axes": diff, "ok": len(diff) > 0})
    disjoint_ok = all(p["ok"] for p in pairs)

    verdict = "PASS" if (not errors and ok_controls and disjoint_ok) else "FAIL"
    report = {
        "report_version": "1.0",
        "artifact_id": "artifacts/flash-02/taxonomy_cases_check_report.json",
        "node_id": meta.get("node_id"),
        "gate": meta.get("gate"),
        "assignment_event_id": meta.get("assignment_event_id"),
        "verdict": verdict,
        "claims_theorem_status": False,
        "taxonomy": {"path": str(tpath), "sha256": sha256_file(tpath),
                     "revision": (taxonomy["doc"].get("revision")),
                     "status": (taxonomy["doc"].get("status"))},
        "cases": {"path": str(cpath), "sha256": sha256_file(cpath)},
        "catalog": {"path": str(kpath), "sha256": sha256_file(kpath)},
        "counts": counts,
        "coverage": cov,
        "leak_kinds": kinds,
        "semantic_cases_requiring_review": pending,
        "open_cases": [c["case_id"] for c in cases if c.get("open") is True],
        "open_case_rule": "open=true means the case is a decidable gate input that exposes an open taxonomy gap (CG2) or requires a split; the formulation lead must adjudicate, not a worker.",
        "machine_verified": {
            "axis_cases": kinds.get("axis", 0),
            "out_of_vocabulary_cases": kinds.get("out_of_vocabulary", 0),
            "lexical_cases": kinds.get("lexical", 0),
        },
        "disjointness": {"ok": disjoint_ok, "pairs": pairs},
        "controls": controls,
        "controls_all_detected": ok_controls,
        "errors": errors,
        "reproduction": "python3 artifacts/flash-02/check_taxonomy_cases.py",
    }
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    Path(a.report).write_text(json.dumps(report, indent=2) + "\n")

    print(f"verdict: {verdict}")
    print(f"cases: {counts['positive']} positive / {counts['negative']} negative; "
          f"kinds={kinds}")
    print(f"coverage positives: {cov['positive']}")
    print(f"coverage negatives: {cov['negative']}")
    print(f"controls detected: {sum(c['detected'] for c in controls)}/{len(controls)}")
    if errors:
        print("errors:")
        for e in errors[:40]:
            print("  -", e)
    print(f"report: {a.report}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
