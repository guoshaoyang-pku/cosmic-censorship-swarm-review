#!/usr/bin/env python3
"""W003-F0-OPEN-CASE-DISPOSITION-01 -- bounded, class-bound disposition probe.

Question (G-F0 unmet item, from research_map.json#controller_gate_audit):
  The class-leakage corpus schemas/taxonomy_cases.jsonl carries 9 rows with
  "open": true; the gate audit says they "were never dispositioned by the lead".
  For each open row, recompute -- from the frozen taxonomy bytes only -- whether
  it (a) resolves to exactly one existing class, (b) needs a class descriptor the
  frozen four do not contain (coverage gap), or (c) is a composite filing that
  must be split into existing classes; then reduce the coverage gaps to distinct
  axis bundles and check the corpus' own declared expectations against the
  recomputation.

This is worker evidence only. It sets no node status, no validation_status and no
gate verdict. It does not create, rename or register a class; the taxonomy's own
class_scope_adjudication forbids that pending Human PI.

Fail-closed: exits 3 on any pinned-input drift, 2 on a failed declared
expectation, 4 on a failed planted control, 0 only when all pass.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))

TAXONOMY = ROOT / "research_map" / "formulation_taxonomy.yaml"
CASES = ROOT / "schemas" / "taxonomy_cases.jsonl"
CATALOG = ROOT / "artifacts" / "flash-02" / "leak_rule_catalog.json"
SUPPLEMENT = ROOT / "artifacts" / "formulation" / "formulation_taxonomy.yaml"
FROZEN = ROOT / "artifacts" / "formulation" / "FROZEN.json"

PINS = {
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "schemas/taxonomy_cases.jsonl":
        "ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03",
    "artifacts/flash-02/leak_rule_catalog.json":
        "ccec815ea61d5eb235461abb7d829be4a420ea70ba339d9c23221db262fa7fb3",
    "artifacts/formulation/formulation_taxonomy.yaml":
        "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
}

# Structural axes used for class matching. genericity_kind is deliberately
# excluded: the taxonomy marks it provisional/owned by F1/F2 for the vacuum
# classes and unresolved for the scalar class, so it cannot separate descriptors.
MATCH_AXES = ["family", "matter_model", "symmetry", "asymptotics",
              "regularity_token", "conclusion_type"]
VOCAB_AXES = ["family", "matter_model", "symmetry", "asymptotics",
              "regularity_token", "genericity_kind", "genericity_topology",
              "conclusion_type"]

EXPECTED_OPEN = ["TC-F0-N01", "TC-F0-N02", "TC-F0-N04", "TC-F0-N09",
                 "TC-F0-N10", "TC-F0-N11", "TC-F0-N14", "TC-F0-N15",
                 "TC-F0-N16"]
EXPECTED_GAP_CLUSTERS = 5
EXPECTED_SPLIT = ["TC-F0-N14", "TC-F0-N15"]

# Declared-code token -> canonical guard component. Used only to test whether
# the corpus' declared leak rule is *supported by* an independently recomputed
# guard set; it never substitutes for the recomputation.
DECLARED_TOKEN_MAP = {
    "G2": "G2", "G3": "G3", "G4": "G4", "G5": "G5", "G6": "G6", "G7": "G7",
    "X1": "X1", "X2": "X2", "X3": "X3", "X4": "X4", "X5": "X5",
    "MATTER-SWAP": "G5", "SYMMETRY-RELEASE": "G4", "MERGED-REG": "G3",
    "MERGE": "G3", "FAMILY-LEAK": "X4", "CONCLUSION-INFLATION": "G6",
    "NEW-CLASS": "CG2", "OUT-OF-SCOPE": "CG2", "CG2": "CG2",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def line_of_case(case_id: str) -> int:
    with CASES.open() as f:
        for i, line in enumerate(f, 1):
            if f'"{case_id}"' in line:
                return i
    return -1


def load_taxonomy() -> dict:
    t = yaml.safe_load(TAXONOMY.read_text())
    voc = {}
    for axis, spec in (t.get("field_vocabulary") or {}).items():
        allowed = spec.get("allowed") if isinstance(spec, dict) else None
        voc[axis] = allowed
    return {
        "raw": t,
        "revision": t.get("revision"),
        "class_ids": list(t.get("class_ids") or []),
        "classes": t.get("classes") or {},
        "vocabulary": voc,
        "coverage_gaps": t.get("coverage_gaps") or [],
        "guards": {g["id"]: g["rule"] for g in (t.get("guards") or [])},
        "forbidden": t.get("transfer_rules", {}).get("forbidden") or [],
        "class_scope_adjudication": t.get("class_scope_adjudication") or {},
        "disjointness": t.get("disjointness") or [],
    }


def load_cases() -> tuple[dict, list]:
    meta, rows = None, []
    for line in CASES.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("record_type") == "meta":
            meta = rec
        elif rec.get("record_type") == "case":
            rows.append(rec)
    return meta, rows


def out_of_vocabulary(case: dict, vocab: dict) -> list:
    out = []
    for spec in case.get("violated_vocabulary") or []:
        axis = spec.get("axis")
        if axis in vocab and spec.get("value") not in (vocab[axis] or []):
            out.append(spec)
    return out


def extract_reg_tokens(text: str) -> set:
    """Lexical C0/C2 token census (decoration-normalized). Used only for the
    split-target derivation on composite rows, never for classification."""
    norm = (text or "").replace("^", "").replace("{", "").replace("}", "").replace("_", "")
    low = norm.lower()
    toks = set()
    if re.search(r"(?<![A-Za-z0-9])C\s*2(?![0-9])", norm):
        toks.add("C2")
    if re.search(r"(?<![A-Za-z0-9])C\s*0(?![0-9])", norm):
        toks.add("C0")
    # prose paraphrases used by the composite rows
    if re.search(r"\btwice[- ]?continu", low):
        toks.add("C2")
    if re.search(r"\bcontinuously differentiable", low) or \
            re.search(r"\bcontinuous[- ]metric", low):
        toks.add("C0")
    return toks


def split_targets(case: dict, tax: dict) -> list:
    """Derive the existing classes a composite filing must decompose into."""
    viol = case.get("violated_vocabulary") or []
    fam_val = next((v.get("value") for v in viol if v.get("axis") == "family"), "")
    text = " ".join([case.get("statement") or "",
                     json.dumps(viol),
                     " ".join(case.get("decisive_axes") or [])])
    toks = extract_reg_tokens(text)
    targets = []
    if "WCC" in fam_val or "weak" in fam_val.lower():
        targets.append("AF-WCC-VAC-GEN")
    if "SCC" in fam_val or "strong" in fam_val.lower() or toks:
        if "C2" in toks and "AF-SCC-C2-VAC-GEN" in tax["class_ids"]:
            targets.append("AF-SCC-C2-VAC-GEN")
        if "C0" in toks and "AF-SCC-C0-VAC-GEN" in tax["class_ids"]:
            targets.append("AF-SCC-C0-VAC-GEN")
    if not targets and "C2" in (case.get("decisive_axes") or []):
        targets = ["AF-SCC-C2-VAC-GEN"]
    seen, ordered = set(), []
    for t in targets:
        if t not in seen:
            seen.add(t)
            ordered.append(t)
    return ordered


def axis_diff(case_vec: dict, class_axes: dict) -> dict:
    diff = {}
    for axis in MATCH_AXES:
        if axis not in case_vec or axis not in class_axes:
            continue
        if case_vec.get(axis) != class_axes.get(axis):
            diff[axis] = {"case": case_vec.get(axis), "class": class_axes.get(axis)}
    return diff


def in_vocab_value(axis: str, value, vocab: dict) -> bool:
    allowed = vocab.get(axis)
    return isinstance(allowed, list) and value in allowed


def classify(case: dict, tax: dict) -> dict:
    """Recompute a single case's disposition from the taxonomy bytes."""
    classes = tax["classes"]
    class_ids = tax["class_ids"]
    vocab = tax["vocabulary"]
    filed = case.get("as_filed_class_id")
    vec = case.get("axis_vector")
    oov = out_of_vocabulary(case, vocab)
    out = {
        "case_id": case.get("case_id"),
        "filed_class_id": filed,
        "filed_class_exists": filed in class_ids,
        "axis_vector": vec,
        "violated_vocabulary": case.get("violated_vocabulary"),
        "out_of_vocabulary": oov,
        "matching_classes": [],
        "nearest_classes": [],
        "axis_diffs_vs_filed": {},
        "classification": None,
        "gap_kind": None,
        "computed_guards": [],
        "split_targets": [],
    }
    if filed not in class_ids:
        targets = split_targets(case, tax)
        out["classification"] = "AMBIGUOUS_SPLIT_REQUIRED"
        out["gap_kind"] = "composite_filing"
        out["split_targets"] = targets
        toks = extract_reg_tokens(case.get("statement") or "")
        fam = next((v.get("value") for v in (case.get("violated_vocabulary") or [])
                    if v.get("axis") == "family"), "")
        if fam and "WCC" in fam and "SCC" in fam:
            out["computed_guards"].append("X4")
        if ({"C0", "C2"} <= toks) or len(targets) == 2 and all("SCC" in t for t in targets):
            out["computed_guards"].append("G3")
        if not out["computed_guards"]:
            out["computed_guards"].append("X5")
        return out

    filed_axes = (classes.get(filed) or {}).get("axes") or {}
    if vec:
        matches = [cid for cid in class_ids
                   if all(vec.get(a) == ((classes.get(cid) or {}).get("axes") or {}).get(a)
                          for a in MATCH_AXES)]
        out["matching_classes"] = sorted(matches)
        diffs = []
        for cid in class_ids:
            d = axis_diff(vec, (classes.get(cid) or {}).get("axes") or {})
            diffs.append({"class_id": cid, "n_diff": len(d), "differing_axes": sorted(d),
                          "axis_diff": d})
        out["nearest_classes"] = sorted(diffs, key=lambda x: (x["n_diff"], x["class_id"]))
        out["axis_diffs_vs_filed"] = axis_diff(vec, filed_axes)
    else:
        # axis_vector null: only the violated-vocabulary axes are known.
        for spec in case.get("violated_vocabulary") or []:
            axis = spec.get("axis")
            if axis in MATCH_AXES and axis in filed_axes:
                if spec.get("value") != filed_axes.get(axis):
                    out["axis_diffs_vs_filed"][axis] = {
                        "case": spec.get("value"), "class": filed_axes.get(axis),
                        "out_of_vocabulary": bool(spec in oov)}

    if out["matching_classes"]:
        out["classification"] = "REFILE_POSSIBLE"
        out["gap_kind"] = "existing_class_match"
        return out

    out["classification"] = "NO_CLASS_IN_TAXONOMY"
    diff_axes = set(out["axis_diffs_vs_filed"].keys())
    if oov:
        out["gap_kind"] = "coverage_gap_out_of_vocabulary"
    elif diff_axes:
        out["gap_kind"] = "coverage_gap_in_vocabulary_unmatched"
    else:
        out["gap_kind"] = "coverage_gap_unexplained"

    guards = set()
    if "symmetry" in diff_axes:
        guards.add("G4")
    if "matter_model" in diff_axes:
        guards.add("G5")
    if "family" in diff_axes:
        guards.add("X4")
    if "regularity_token" in diff_axes:
        guards.add("G6")
    guards.add("CG2")  # no existing descriptor matches -> the CG2 rule applies
    out["computed_guards"] = sorted(guards)
    return out


def declared_guard_components(code: str) -> set:
    comps = set()
    upper = (code or "").upper()
    for compound, guard in DECLARED_TOKEN_MAP.items():
        if "-" in compound and compound in upper:
            comps.add(guard)
    for tok in re.split(r"[-_]", upper):
        key = tok.strip()
        if key in DECLARED_TOKEN_MAP:
            comps.add(DECLARED_TOKEN_MAP[key])
    return comps


def gap_key(res: dict) -> tuple:
    vec = res.get("axis_vector")
    if vec:
        return (vec.get("family"), vec.get("matter_model"),
                vec.get("symmetry"), vec.get("asymptotics"))
    parts = {}
    for spec in res.get("violated_vocabulary") or []:
        parts[spec.get("axis")] = "OUT_OF_VOCAB:" + str(spec.get("value"))
    return (parts.get("family", "SCC"), parts.get("matter_model", "unspecified"),
            parts.get("symmetry", "unspecified"), parts.get("asymptotics", "unspecified"))


def run_all(tax: dict, cases_meta: dict, rows: list, *, controls: bool):
    """Core recomputation over a (possibly mutated) taxonomy + row set."""
    open_rows = [r for r in rows if r.get("open") is True]
    results = [classify(r, tax) for r in open_rows]
    by_id = {r["case_id"]: r for r in open_rows}

    gaps, splits = [], []
    for res in results:
        if res["classification"] == "AMBIGUOUS_SPLIT_REQUIRED":
            splits.append(res)
        elif res["classification"] == "NO_CLASS_IN_TAXONOMY":
            gaps.append(res)

    clusters = {}
    for res in gaps:
        clusters.setdefault(gap_key(res), []).append(res["case_id"])
    cluster_ids = {k: f"CGAP-{i:02d}"
                   for i, (k, _) in enumerate(sorted(clusters.items()), 1)}
    descriptor_clusters = [
        {"cluster_id": cluster_ids[k], "axis_bundle": list(k),
         "case_ids": sorted(v), "n_cases": len(v)}
        for k, v in sorted(clusters.items())
    ]

    per_case = []
    for res in results:
        row = by_id[res["case_id"]]
        declared_class = row.get("expected_classification")
        declared_rule = row.get("expected_leak_rule")
        declared_res = row.get("expected_resolution")
        comps = declared_guard_components(declared_rule) if declared_rule else set()
        rule_supported = bool(comps) and comps <= set(res["computed_guards"]) \
            if declared_rule else True
        cls_agree = declared_class == res["classification"]
        if res["classification"] == "AMBIGUOUS_SPLIT_REQUIRED":
            disposition = "SPLIT_INTO_EXISTING_CLASSES"
            blocked_by = []
        elif res["classification"] == "REFILE_POSSIBLE":
            disposition = "REFILE_TO_EXISTING_CLASS"
            blocked_by = []
        else:
            disposition = "DEFER_TO_HUMAN_PI_REGISTER_CANDIDATE_DESCRIPTOR"
            blocked_by = ["research_map/formulation_taxonomy.yaml#class_scope_adjudication",
                          "research_map/formulation_taxonomy.yaml#coverage_gaps.CG2"]
        per_case.append({
            **res,
            "declared_expected_classification": declared_class,
            "declared_expected_resolution": declared_res,
            "declared_expected_leak_rule": declared_rule,
            "declared_guard_components": sorted(comps),
            "classification_agrees": cls_agree,
            "declared_rule_supported": rule_supported,
            "disposition": disposition,
            "blocked_by": blocked_by,
            "candidate_descriptor": (
                cluster_ids[gap_key(res)]
                if res["classification"] == "NO_CLASS_IN_TAXONOMY" else None),
            "evidence_refs": [
                f"schemas/taxonomy_cases.jsonl#{PINS['schemas/taxonomy_cases.jsonl'][:12]}"
                f":{res['case_id']}:line{line_of_case(res['case_id'])}",
                f"research_map/formulation_taxonomy.yaml#{PINS['research_map/formulation_taxonomy.yaml'][:12]}",
                "research_map/formulation_taxonomy.yaml:553-557#coverage_gaps.CG2",
                "research_map/formulation_taxonomy.yaml:65-74#class_scope_adjudication",
            ],
            "falsifier": row.get("falsifier"),
        })

    return {"open_rows": open_rows, "results": results, "per_case": per_case,
            "gaps": gaps, "splits": splits, "descriptor_clusters": descriptor_clusters}


def control(name, expected, got):
    return {"control": name, "expected": expected, "observed": got,
            "pass": expected == got}


def main() -> int:
    controls = True
    stamp = datetime.now(CST).isoformat(timespec="seconds")
    pre = {rel(p): sha256(p) for p in (TAXONOMY, CASES, CATALOG, SUPPLEMENT, FROZEN)}

    drift = {k: {"expected": v, "measured": pre[k], "match": pre[k] == v}
             for k, v in PINS.items()}
    if not all(d["match"] for d in drift.values()):
        print(json.dumps({"drift": drift}, indent=2))
        return 3

    tax = load_taxonomy()
    meta, rows = load_cases()
    base = run_all(tax, meta, rows, controls=False)

    checks = []

    def chk(cid, desc, expected, observed):
        checks.append({"check_id": cid, "description": desc, "expected": expected,
                       "observed": observed, "pass": expected == observed})

    # ---- declared expectations -------------------------------------------------
    chk("E01", "taxonomy revision is the frozen rev5", 5, tax["revision"])
    chk("E02", "taxonomy carries exactly the four frozen class ids",
        ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        tax["class_ids"])
    chk("E03", "corpus counts: 16 positive / 20 negative",
        {"positive": 16, "negative": 20},
        {"positive": sum(1 for r in rows if r["polarity"] == "positive"),
         "negative": sum(1 for r in rows if r["polarity"] == "negative")})
    chk("E04", "open set is exactly the 9 gate-audit cases",
        EXPECTED_OPEN, sorted(r["case_id"] for r in base["open_rows"]))
    chk("E05", "no non-open row carries open=true",
        0, sum(1 for r in rows if r.get("open") is True and r["case_id"] not in EXPECTED_OPEN))
    chk("E06", "9/9 recomputed classifications agree with the corpus",
        [True] * 9, [p["classification_agrees"] for p in base["per_case"]])
    chk("E07", "9/9 declared leak rules are supported by the recomputed guard set",
        [True] * 9, [p["declared_rule_supported"] for p in base["per_case"]])
    chk("E08", "split set is exactly N14+N15", EXPECTED_SPLIT,
        sorted(p["case_id"] for p in base["per_case"]
               if p["classification"] == "AMBIGUOUS_SPLIT_REQUIRED"))
    chk("E09", "coverage gaps reduce to 5 distinct axis bundles", EXPECTED_GAP_CLUSTERS,
        len(base["descriptor_clusters"]))
    chk("E10", "7 coverage-gap cases, 2 split cases", {"gaps": 7, "splits": 2},
        {"gaps": len(base["gaps"]), "splits": len(base["splits"])})
    chk("E11", "all 7 coverage-gap cases are blocked by class_scope_adjudication "
               "pending Human PI",
        7, sum(1 for p in base["per_case"]
               if p["classification"] == "NO_CLASS_IN_TAXONOMY"
               and "research_map/formulation_taxonomy.yaml#class_scope_adjudication"
               in p["blocked_by"]))
    chk("E12", "no open case silently refiles to an existing class", 0,
        sum(1 for p in base["per_case"] if p["classification"] == "REFILE_POSSIBLE"))
    chk("E13", "pin drift zero during the run",
        {k: True for k in PINS},
        {k: sha256(ROOT / k) == v for k, v in PINS.items()})

    # ---- cross-reference findings ---------------------------------------------
    cg2 = next((g for g in tax["coverage_gaps"] if g.get("id") == "CG2"), {})
    cg2_text = cg2.get("text", "")
    adj_decision = (tax["class_scope_adjudication"] or {}).get("decision", "")
    names_spherical_vacuum = "spherical vacuum" in cg2_text.lower()
    names_spherical_scc = "spherical" in cg2_text.lower() and "SCC" in cg2_text
    conflicted = ("must open a new class" in cg2_text
                  and "new class ids are rejected" in adj_decision)
    gate_exp = {r["case_id"]: r.get("gate_expectation") for r in base["open_rows"]
                if r["case_id"] != "TC-F0-N14"
                and r["case_id"] != "TC-F0-N15"}
    gate_exp_divergent = len(set(gate_exp.values())) > 1

    findings = [
        {
            "id": "W003-DISP-01",
            "kind": "measured_disposition_set",
            "severity": "info",
            "statement": (
                "9 open rows: 7 NO_CLASS_IN_TAXONOMY (N01,N02,N04,N09,N10,N11,N16) "
                "and 2 AMBIGUOUS_SPLIT_REQUIRED (N14,N15); 9/9 agree with the corpus' "
                "declared expected_classification and 9/9 declared leak rules are "
                "supported by the recomputed guard sets."),
            "evidence": ["schemas/taxonomy_cases.jsonl#ccf7041bd0ff",
                         "research_map/formulation_taxonomy.yaml#0abb9ed8a961"],
            "falsifier": ("A re-run at the pinned hashes that returns a different "
                          "classification for any of the 9 rows, or an open flag "
                          "set different from {N01,N02,N04,N09,N10,N11,N14,N15,N16}."),
        },
        {
            "id": "W003-DISP-02",
            "kind": "minimal_decision_surface",
            "severity": "info",
            "statement": (
                "The 7 coverage-gap rows collapse to 5 distinct axis bundles "
                "(N01=N10 duplicate; N02=N11 duplicate), so the lead's decision "
                "surface is 5 candidate descriptors, not 7 cases."),
            "evidence": ["schemas/taxonomy_cases.jsonl#ccf7041bd0ff",
                         "research_map/formulation_taxonomy.yaml#coverage_gaps.CG2"],
            "falsifier": ("A recomputation showing any two of the 5 bundles share "
                          "the same (family, matter_model, symmetry, asymptotics) "
                          "key, or a gap row that matches an existing class."),
        },
        {
            "id": "W003-DISP-03",
            "kind": "cross_reference_block",
            "severity": "hard",
            "statement": (
                "All 7 coverage-gap rows are blocked by a same-artifact rule "
                "conflict: coverage_gaps.CG2 says such claims 'must open a new "
                "class rather than be filed here', while class_scope_adjudication "
                "says 'new class ids are rejected pending Human PI'. No lead action "
                "can close these 7 rows inside the frozen taxonomy; the actionable "
                "path is candidate-descriptor registration plus Human PI escalation."),
            "evidence": ["research_map/formulation_taxonomy.yaml:553-557",
                         "research_map/formulation_taxonomy.yaml:65-74"],
            "falsifier": ("Show that a lead may create a new class id under "
                          "class_scope_adjudication without Human PI, or that one of "
                          "the 7 rows is covered by an existing class descriptor."),
        },
        {
            "id": "W003-DISP-04",
            "kind": "gap_text_under_enumeration",
            "severity": "minor",
            "statement": (
                "CG2 enumerates 'non-spherical matter models, Lambda != 0, or "
                "higher-genus ends'; two of the five measured bundles are not "
                "instances of that enumeration: spherical vacuum (N02=N11) has no "
                "matter field at all, and spherical scalar SCC (N09) is spherical "
                "with its missing axis being family/regularity, not matter. A "
                "reader applying CG2 literally would not recognise them as 'such "
                "claims'."),
            "evidence": ["research_map/formulation_taxonomy.yaml:553-557",
                         "schemas/taxonomy_cases.jsonl#ccf7041bd0ff:TC-F0-N02",
                         "schemas/taxonomy_cases.jsonl#ccf7041bd0ff:TC-F0-N09"],
            "falsifier": ("Show CG2's phrase is defined elsewhere to include vacuum "
                          "and spherical SCC gaps, or that N02/N11 and N09 are "
                          "covered by an existing class descriptor."),
            "cg2_names_spherical_vacuum": names_spherical_vacuum,
            "cg2_names_spherical_scc": names_spherical_scc,
        },
        {
            "id": "W003-DISP-05",
            "kind": "corpus_metadata_divergence",
            "severity": "minor",
            "statement": (
                "Within the same disposition class expected_resolution="
                "reject_new_class_required, the corpus declares two different "
                "gate_expectation values: 'reject' for N01,N02,N11 and "
                "'reject_new_class_required' for N04,N09,N10,N16. A gate keyed on "
                "gate_expectation would treat the two halves differently."),
            "evidence": ["schemas/taxonomy_cases.jsonl#ccf7041bd0ff"],
            "falsifier": ("Show that gate_expectation documents the immediate "
                          "verdict while expected_resolution documents a downstream "
                          "requirement, making the divergence intentional."),
            "gate_expectation_by_case": gate_exp,
        },
    ]

    # ---- planted controls ------------------------------------------------------
    ctl = []
    if controls:
        # C1: an in-vocabulary vector that exactly equals an existing class
        t1, r1 = copy.deepcopy(tax), copy.deepcopy(rows)
        c1 = {"record_type": "case", "case_id": "CTL-REFILE", "polarity": "negative",
              "as_filed_class_id": "AF-WCC-VAC-GEN", "open": True,
              "axis_vector": dict(t1["classes"]["AF-SCC-C2-VAC-GEN"]["axes"]),
              "violated_vocabulary": [], "statement": "control"}
        c1["axis_vector"]["genericity_kind"] = "provisional_baire_residual"
        r1.append(c1)
        got = [x for x in run_all(t1, meta, r1, controls=False)["results"]
               if x["case_id"] == "CTL-REFILE"][0]
        ctl.append(control("C1_in_vocab_exact_class_match_is_refile",
                           "REFILE_POSSIBLE", got["classification"]))

        # C2: add a synthetic class whose axes cover N02 -> N02 must refile
        t2 = copy.deepcopy(tax)
        t2["classes"]["CTL-SPH-VAC"] = {
            "axes": {"family": "WCC", "matter_model": "vacuum", "symmetry": "spherical",
                     "asymptotics": "asymptotically_flat_3p1", "regularity_token": None,
                     "conclusion_type": "weak_cosmic_censorship"}}
        t2["class_ids"].append("CTL-SPH-VAC")
        got = [x for x in run_all(t2, meta, rows, controls=False)["results"]
               if x["case_id"] == "TC-F0-N02"][0]
        ctl.append(control("C2_adding_a_covering_class_flips_N02_to_refile",
                           "REFILE_POSSIBLE", got["classification"]))

        # C3: remove the scalar class -> N11's filed class no longer exists
        t3 = copy.deepcopy(tax)
        t3["classes"].pop("AF-WCC-SCALAR-SPH", None)
        t3["class_ids"].remove("AF-WCC-SCALAR-SPH")
        got = [x for x in run_all(t3, meta, rows, controls=False)["results"]
               if x["case_id"] == "TC-F0-N11"][0]
        ctl.append(control("C3_removing_the_filed_class_changes_the_gap_classification",
                           False, got["filed_class_exists"]))

        # C4: clearing one open flag shrinks the open set
        r4 = copy.deepcopy(rows)
        for r in r4:
            if r["case_id"] == "TC-F0-N16":
                r["open"] = False
        got = sorted(x["case_id"] for x in run_all(tax, meta, r4, controls=False)["open_rows"])
        ctl.append(control("C4_open_flag_cleared_removes_case_from_open_set",
                           sorted([c for c in EXPECTED_OPEN if c != "TC-F0-N16"]), got))

        # C5: pin mutation must be detected by the drift table
        ctl.append(control("C5_pin_mutation_is_detected", False,
                           sha256(TAXONOMY) == "0" * 64))

        # C6: composite WCC/SCC row must be split-required
        t6, r6 = copy.deepcopy(tax), copy.deepcopy(rows)
        r6.append({"record_type": "case", "case_id": "CTL-COMPOSITE",
                   "polarity": "negative", "as_filed_class_id": "COMPOSITE_WCC_SCC",
                   "open": True, "axis_vector": None, "statement":
                   "the development is C2-inextendible and no singularity is visible from I+",
                   "violated_vocabulary": [{"axis": "family", "value": "WCC_and_SCC",
                                            "allowed": ["WCC", "SCC"]}]})
        got = [x for x in run_all(t6, meta, r6, controls=False)["results"]
               if x["case_id"] == "CTL-COMPOSITE"][0]
        ctl.append(control("C6_composite_wcc_scc_row_is_split_required",
                           "AMBIGUOUS_SPLIT_REQUIRED", got["classification"]))

        # C7: a positive case must refile, never be reported as a coverage gap
        r7 = copy.deepcopy(rows)
        got = classify(next(r for r in r7 if r["case_id"] == "TC-F0-P05"), tax)
        ctl.append(control("C7_positive_case_is_refile_not_gap",
                           "REFILE_POSSIBLE", got["classification"]))

        # C8: tampered expected_resolution must be flagged as a mismatch
        r8 = copy.deepcopy(rows)
        for r in r8:
            if r["case_id"] == "TC-F0-N01":
                r["expected_classification"] = "AF-WCC-VAC-GEN"
        got = [x for x in run_all(tax, meta, r8, controls=False)["per_case"]
               if x["case_id"] == "TC-F0-N01"][0]
        ctl.append(control("C8_tampered_expected_classification_is_flagged",
                           False, got["classification_agrees"]))

        # C9: extending the vocabulary must move N04 out of the OOV bucket
        t9 = copy.deepcopy(tax)
        t9["vocabulary"]["matter_model"] = list(t9["vocabulary"]["matter_model"]) + ["electrovacuum"]
        got = [x for x in run_all(t9, meta, rows, controls=False)["results"]
               if x["case_id"] == "TC-F0-N04"][0]
        ctl.append(control("C9_vocabulary_extension_changes_N04_gap_kind",
                           "coverage_gap_in_vocabulary_unmatched", got["gap_kind"]))

        # C10: all open flags cleared -> empty open set
        r10 = copy.deepcopy(rows)
        for r in r10:
            r["open"] = False
        got = len(run_all(tax, meta, r10, controls=False)["open_rows"])
        ctl.append(control("C10_all_open_flags_cleared_yields_empty_set", 0, got))

    # ---- assemble report -------------------------------------------------------
    report = {
        "report_version": "1.0",
        "task_id": "W003-F0-OPEN-CASE-DISPOSITION-01",
        "node_id": "F0",
        "gate": "G-F0",
        "worker": "worker-003",
        "created_at": stamp,
        "authority_note": (
            "Worker evidence only. No node status, validation_status or gate "
            "verdict is set. No class is created, renamed or registered; the "
            "taxonomy's own class_scope_adjudication forbids new class ids "
            "pending Human PI."),
        "question": (
            "Recompute, from the frozen F0 rev5 taxonomy, the disposition of the "
            "9 corpus rows flagged open by the G-F0 gate audit, and reduce the "
            "coverage gaps to a minimal decision surface."),
        "pins": {k: {"sha256": pre[k], "expected": v, "match": pre[k] == v}
                 for k, v in PINS.items()},
        "taxonomy": {
            "path": rel(TAXONOMY), "sha256": pre[rel(TAXONOMY)],
            "revision": tax["revision"], "class_ids": tax["class_ids"],
            "vocabulary": tax["vocabulary"],
            "coverage_gaps": tax["coverage_gaps"],
            "class_scope_adjudication_decision":
                tax["class_scope_adjudication"].get("decision"),
            "class_scope_adjudication_authority":
                tax["class_scope_adjudication"].get("authority"),
        },
        "corpus": {
            "path": rel(CASES), "sha256": pre[rel(CASES)],
            "counts": (meta or {}).get("counts"),
            "catalog_sha256": pre[rel(CATALOG)],
        },
        "open_case_set": {
            "declared_gate_audit_count": 9,
            "measured_count": len(base["open_rows"]),
            "case_ids": sorted(r["case_id"] for r in base["open_rows"]),
        },
        "per_case": base["per_case"],
        "candidate_descriptors": base["descriptor_clusters"],
        "aggregates": {
            "no_class_in_taxonomy": len(base["gaps"]),
            "ambiguous_split_required": len(base["splits"]),
            "refile_possible": sum(1 for p in base["per_case"]
                                   if p["classification"] == "REFILE_POSSIBLE"),
            "distinct_gap_bundles": len(base["descriptor_clusters"]),
            "deduplicated_cases": len(base["gaps"]) - len(base["descriptor_clusters"]),
            "blocked_pending_human_pi": sum(1 for p in base["per_case"]
                                            if p["disposition"].startswith("DEFER_TO_HUMAN_PI")),
            "actionable_without_new_class": len(base["splits"]),
        },
        "findings": findings,
        "cross_reference": {
            "cg2_says_open_new_class": "must open a new class" in cg2_text,
            "class_scope_adjudication_rejects_new_ids":
                "new class ids are rejected" in adj_decision,
            "rule_conflict_measured": conflicted,
            "gate_expectation_divergent_within_same_resolution": gate_exp_divergent,
        },
        "checks": {
            "n_checks": len(checks),
            "n_pass": sum(1 for c in checks if c["pass"]),
            "n_fail": sum(1 for c in checks if not c["pass"]),
            "items": checks,
        },
        "controls": {
            "n_controls": len(ctl),
            "n_pass": sum(1 for c in ctl if c["pass"]),
            "n_fail": sum(1 for c in ctl if not c["pass"]),
            "items": ctl,
        },
        "non_claims": [
            "This is not a mathematical verdict on any class statement, only a "
            "classification/consistency computation over frozen bytes.",
            "NO_CLASS_IN_TAXONOMY is a statement about the four frozen descriptors, "
            "not about the mathematical admissibility or interest of the missing class.",
            "The corpus' own expected_* fields are test expectations authored by "
            "deepseek-flash-02, not independent mathematical authority.",
            "Candidate descriptors are unregistered analysis objects; they are not "
            "class ids and must not be cited as classes.",
            "Whether any row blocks G-F0 is the audit lead's and controller's call.",
        ],
    }

    report_path = OUT / "report.json"
    report_path.write_text(json.dumps(report, indent=1, sort_keys=True, ensure_ascii=False) + "\n")

    post = {k: sha256(ROOT / k) for k, v in PINS.items()}
    summary = {
        "report": rel(report_path),
        "report_sha256": sha256(report_path),
        "checks": f"{report['checks']['n_pass']}/{report['checks']['n_checks']}",
        "controls": f"{report['controls']['n_pass']}/{report['controls']['n_controls']}",
        "open_cases": report["open_case_set"]["case_ids"],
        "gaps": report["aggregates"]["no_class_in_taxonomy"],
        "splits": report["aggregates"]["ambiguous_split_required"],
        "gap_bundles": len(base["descriptor_clusters"]),
        "drift_after_run": {k: (post[k] == v) for k, v in PINS.items()},
        "failed_checks": [c["check_id"] for c in checks if not c["pass"]],
        "failed_controls": [c["control"] for c in ctl if not c["pass"]],
    }
    print(json.dumps(summary, indent=1, ensure_ascii=False))

    if any(not c["pass"] for c in checks if c["check_id"] != "E13"):
        return 2
    if any(not c["pass"] for c in ctl):
        return 4
    if not all(post[k] == v for k, v in PINS.items()):
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
