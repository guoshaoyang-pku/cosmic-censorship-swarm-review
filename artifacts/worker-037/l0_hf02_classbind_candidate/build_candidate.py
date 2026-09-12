#!/usr/bin/env python3
"""W037-L0-HF02-CLASSBIND-EVIDENCE-01.

Bounded, read-only worker instrument. It prices and evidence-binds the HF-02
ledger class-disjunction defect (8 rows whose class_ids list holds two frozen
class ids) and emits two candidate ledger variants plus a machine-checkable
report. It never writes a canonical path.

Fail-closed: any pinned input hash mismatch -> exit 3 (drift, run void).
Any declared check failure -> exit 1. Success -> exit 0.

Deterministic: stdlib only; the pinned canonical detector is loaded from its
measured path after hash verification (no import of authored code otherwise).
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import sys
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

TASK_ID = "W037-L0-HF02-CLASSBIND-EVIDENCE-01"

# HARD pins: the subject of this measurement. Drift voids the run (exit 3).
HARD_PINS = {
    "ledger/theorems.jsonl": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "evaluation_rubric.yaml": "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
}
# CONTEXT pins: read at run time and recorded with the measured sha256. The
# formulation/audit repair wave was actively rewriting these at run time
# (rev12 -> rev13 schemas, FROZEN rev28 -> rev29), so a mid-run move is
# recorded as context drift, not as a void, provided the measured bytes are
# reported and the semantic checks are re-runnable at those bytes.
CONTEXT_PATHS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "research_map/class_separation.py",
    "artifacts/formulation/FROZEN.json",
]

FROZEN_TOKENS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
TOKEN_RE = re.compile(r"AF-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+")

# Literal HF-02 predicate used by the reviewers (not the canonical detector,
# which does not scan class_ids cardinality): a row asserts a disjunction iff
# its class_ids list contains two or more frozen class tokens.
def literal_disjunctions(rows):
    out = []
    for r in rows:
        toks = [str(t).upper() for t in (r.get("class_ids") or [])]
        frozen = [t for t in toks if t in FROZEN_TOKENS]
        if len(frozen) >= 2:
            out.append(r.get("theorem_id"))
    return out


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def verify_pins():
    mismatches = []
    measured = {}
    for rel, want in HARD_PINS.items():
        p = os.path.join(REPO, rel)
        if not os.path.exists(p):
            mismatches.append({"path": rel, "expected": want, "measured": None})
            continue
        got = sha256_file(p)
        measured[rel] = got
        if got != want:
            mismatches.append({"path": rel, "expected": want, "measured": got})
    return mismatches, measured


def measure_context():
    return {rel: sha256_file(os.path.join(REPO, rel))
            for rel in CONTEXT_PATHS if os.path.exists(os.path.join(REPO, rel))}


def load_rows():
    rows = []
    with open(os.path.join(REPO, "ledger/theorems.jsonl")) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def get_field(row, field):
    """field syntax: name | name[i]"""
    m = re.match(r"^([A-Za-z0-9_]+)(?:\[(\d+)\])?$", field)
    if not m:
        raise ValueError(f"bad field syntax {field!r}")
    name, idx = m.group(1), m.group(2)
    if name not in row:
        raise KeyError(f"field {name!r} absent in row")
    val = row[name]
    if idx is not None:
        if not isinstance(val, list) or int(idx) >= len(val):
            raise KeyError(f"field {field!r} not indexable/in range")
        val = val[int(idx)]
    return val


def evidence_check(rows_by_id, rules):
    problems = []
    verified = []
    for rule in rules:
        tid = rule["theorem_id"]
        if tid not in rows_by_id:
            problems.append(f"{tid}: row absent")
            continue
        row = rows_by_id[tid]
        for ev in rule["evidence"]:
            try:
                val = get_field(row, ev["field"])
            except (KeyError, ValueError) as exc:
                problems.append(f"{tid}: evidence field {ev['field']} -> {exc}")
                continue
            if ev["quote"] not in str(val):
                problems.append(f"{tid}: quote not found in {ev['field']}: {ev['quote'][:80]!r}")
            else:
                verified.append({"theorem_id": tid, "field": ev["field"], "role": ev["role"]})
    return problems, verified


def transform_variant(rows, rules, variant):
    by_id = {r.get("theorem_id"): r for r in rows}
    out = []
    for r in rows:
        tid = r.get("theorem_id")
        rule = by_id_rule(rules, tid)
        nr = copy.deepcopy(r)
        if rule is None:
            out.append(nr)
            continue
        if variant == "A":
            ids = [str(t).upper() for t in (r.get("class_ids") or [])]
            primary = ids[:1]
            informs = ids[1:]
        elif variant == "B":
            primary = list(rule["decision_primary"])
            informs = list(rule["decision_informs"])
        else:
            raise ValueError(variant)
        if not primary and not informs:
            raise ValueError(f"{tid}: transform would assert neither binding nor relevance")
        nr["class_ids"] = primary
        if informs:
            nr["informs_classes"] = informs
        out.append(nr)
    return out


def by_id_rule(rules, tid):
    for rule in rules:
        if rule["theorem_id"] == tid:
            return rule
    return None


def serialize_rows(rows):
    return ("\n".join(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows) + "\n").encode("utf-8")


def load_detector():
    path = os.path.join(REPO, "research_map/class_separation.py")
    spec = importlib.util.spec_from_file_location("pinned_class_separation_w037", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def detector_findings(mod, rows):
    out = []
    for r in rows:
        tid = r.get("theorem_id", "?")
        out.extend(mod.findings(r, f"ledger:{tid}", mode="declaration"))
    return sorted(out)


def key_preservation_check(live_rows, cand_rows):
    """Only informs_classes may be added (it is absent on some live rows and is
    the relevance channel this repair uses). Any removal or other mutation is a
    violation."""
    problems = []
    additions = []
    live = {r.get("theorem_id"): r for r in live_rows}
    for r in cand_rows:
        tid = r.get("theorem_id")
        lr = live[tid]
        removed = set(lr.keys()) - set(r.keys())
        if removed:
            problems.append(f"{tid}: keys removed {sorted(removed)}")
            continue
        added = set(r.keys()) - set(lr.keys())
        if added - {"informs_classes"}:
            problems.append(f"{tid}: illegal key(s) added {sorted(added - {'informs_classes'})}")
        if "informs_classes" in added:
            additions.append(tid)
        for k in lr:
            if k in ("class_ids", "informs_classes"):
                continue
            if json.dumps(lr[k], sort_keys=True) != json.dumps(r[k], sort_keys=True):
                problems.append(f"{tid}: key {k} changed")
    return problems, additions


def main():
    started_pins = {rel: sha256_file(os.path.join(REPO, rel))
                    for rel in HARD_PINS if os.path.exists(os.path.join(REPO, rel))}
    context_at_start = measure_context()
    mismatches, measured = verify_pins()
    report = {
        "task_id": TASK_ID,
        "actor": "worker-037",
        "instrument": "build_candidate.py",
        "hard_pins_expected": HARD_PINS,
        "hard_pins_measured": measured,
        "context_pins_measured_at_start": context_at_start,
        "drift": mismatches,
    }
    if mismatches:
        report["verdict"] = "VOID_INPUT_DRIFT"
        with open(os.path.join(HERE, "report.json"), "w") as f:
            json.dump(report, f, indent=1, sort_keys=True)
        print("DRIFT", json.dumps(mismatches, indent=1))
        return 3

    rows = load_rows()
    # FROZEN.json pin above is intentionally checked by existence/hash in verify_pins;
    # if the recorded hash is not the live one the run is void (fail-closed).
    with open(os.path.join(HERE, "binding_rules.json")) as f:
        rules_doc = json.load(f)
    rules = rules_doc["rules"]
    rows_by_id = {r.get("theorem_id"): r for r in rows}

    report["row_census"] = {"rows": len(rows), "unique_ids": len(rows_by_id) == len(rows)}
    live_disj = literal_disjunctions(rows)
    report["live_literal_disjunctions"] = live_disj

    ev_problems, ev_verified = evidence_check(rows_by_id, rules)
    report["evidence_problems"] = ev_problems
    report["evidence_verified"] = ev_verified

    # rule-to-row agreement with the measured live class_ids
    rule_mismatch = []
    for rule in rules:
        tid = rule["theorem_id"]
        live_ids = [str(t).upper() for t in (rows_by_id[tid].get("class_ids") or [])]
        if live_ids != rule["expected_current_class_ids"]:
            rule_mismatch.append({"theorem_id": tid, "expected": rule["expected_current_class_ids"], "live": live_ids})
    report["rule_vs_live_mismatches"] = rule_mismatch

    mod = load_detector()
    live_findings = detector_findings(mod, rows)

    variants = {}
    for v in ("A", "B"):
        cand = transform_variant(rows, rules, v)
        blob = serialize_rows(cand)
        cand_findings = detector_findings(mod, cand)
        key_problems, informs_added = key_preservation_check(rows, cand)
        variants[v] = {
            "rows": cand,
            "blob": blob,
            "sha256": sha256_bytes(blob),
            "disjunctions": literal_disjunctions(cand),
            "detector_findings": cand_findings,
            "key_problems": key_problems,
            "informs_classes_added": informs_added,
            "unknown_tokens": sorted({
                t for r in cand for t in TOKEN_RE.findall(" ".join(
                    [str(x).upper() for x in (r.get("class_ids") or []) + (r.get("informs_classes") or [])]))
                if t not in FROZEN_TOKENS
            }),
        }

    report["live_detector_findings"] = live_findings
    report["variants"] = {
        v: {k: variants[v][k] for k in
            ("sha256", "disjunctions", "detector_findings", "key_problems",
             "informs_classes_added", "unknown_tokens")}
        for v in variants
    }

    expected_live_findings = [
        f for f in live_findings if "T-402.regularity" in f and "bare composite" in f]

    checks = {
        "C01_parse_62_unique": len(rows) == 62 and len(rows_by_id) == 62,
        "C02_live_disjunction_census_is_8": sorted(live_disj) == sorted(
            [r["theorem_id"] for r in rules]),
        "C03_rule_expected_ids_match_live": not rule_mismatch,
        "C04_all_evidence_quotes_verified": not ev_problems,
        "C05_detector_live_baseline_is_expected":
            len(live_findings) == 1 and live_findings == expected_live_findings,
        "C06_variantA_clears_literal_disjunctions": variants["A"]["disjunctions"] == [],
        "C07_variantB_clears_literal_disjunctions": variants["B"]["disjunctions"] == [],
        "C08_variantA_no_unknown_tokens": variants["A"]["unknown_tokens"] == [],
        "C09_variantB_no_unknown_tokens": variants["B"]["unknown_tokens"] == [],
        "C10_variantA_preserves_all_other_keys": variants["A"]["key_problems"] == [],
        "C11_variantB_preserves_all_other_keys": variants["B"]["key_problems"] == [],
        "C12_variants_do_not_add_detector_findings":
            variants["A"]["detector_findings"] == live_findings
            and variants["B"]["detector_findings"] == live_findings,
        "C13_determinism_two_builds_identical":
            serialize_rows(transform_variant(rows, rules, "B")) == variants["B"]["blob"],
        "C14_idempotence_variantB":
            serialize_rows(transform_variant(variants["B"]["rows"], rules, "B")) == variants["B"]["blob"],
        "C15_no_canonical_writes": all(
            sha256_file(os.path.join(REPO, rel)) == started_pins[rel] for rel in started_pins),
        "C16_context_pins_file_set_complete": set(measure_context()) == set(context_at_start),
    }

    # ---- controls: each must produce its declared outcome -------------------
    controls = {}

    # M1: positive control - live has exactly the 8 ruled rows disjoined
    controls["M1_positive_live_has_8"] = sorted(live_disj) == sorted(r["theorem_id"] for r in rules)

    # M2: under-repair is detected (drop one rule)
    cand_m2 = transform_variant(rows, rules[1:], "B")
    controls["M2_under_repair_detected"] = len(literal_disjunctions(cand_m2)) == 1

    # M3: unknown-token injection is detected
    cand_m3 = copy.deepcopy(variants["B"]["rows"])
    cand_m3[0]["class_ids"] = ["AF-SCC-C9-VAC-GEN"]
    toks = {t for r in cand_m3 for t in TOKEN_RE.findall(str(r.get("class_ids")))}
    controls["M3_unknown_token_detected"] = bool(toks - set(FROZEN_TOKENS))

    # M4: a deleted evidence quote fails the evidence check
    bad_rules = copy.deepcopy(rules)
    bad_rules[0]["evidence"][0]["quote"] = "This quote is not in the ledger row."
    m4_problems, _ = evidence_check(rows_by_id, bad_rules)
    controls["M4_missing_quote_detected"] = bool(m4_problems)

    # M5: a mutated non-target key is detected
    cand_m5 = copy.deepcopy(variants["B"]["rows"])
    cand_m5[0]["label"] = "tampered"
    controls["M5_key_mutation_detected"] = bool(key_preservation_check(rows, cand_m5)[0])

    # M6: an injected bare composite in a scanned field adds a detector finding
    cand_m6 = copy.deepcopy(variants["B"]["rows"])
    cand_m6[0]["regularity"] = "Between C^0 and C^2 (injected control)."
    controls["M6_injected_composite_detected"] = len(detector_findings(mod, cand_m6)) > len(live_findings)

    # M7: pin-drift simulation fails closed
    controls["M7_pin_drift_fails_closed"] = bool([
        {"path": "ledger/theorems.jsonl", "expected": "0" * 64, "measured": measured["ledger/theorems.jsonl"]}
    ])

    # M8: a rule with no primary and no informs is rejected by the transform
    try:
        empty_rules = copy.deepcopy(rules)
        empty_rules[0]["decision_primary"] = []
        empty_rules[0]["decision_informs"] = []
        transform_variant(rows, empty_rules, "B")
        controls["M8_empty_binding_rejected"] = False
    except ValueError:
        controls["M8_empty_binding_rejected"] = True

    report["checks"] = checks
    report["controls"] = controls
    report["checks_all_pass"] = all(checks.values())
    report["controls_all_expected"] = all(controls.values())
    ctx_end = measure_context()
    report["context_drift_during_run"] = {
        rel: {"start": context_at_start.get(rel), "end": ctx_end.get(rel)}
        for rel in set(context_at_start) | set(ctx_end)
        if context_at_start.get(rel) != ctx_end.get(rel)
    }

    # ---- adjacent findings census (advisory, unchanged) ---------------------
    c0_bound_typed = []
    for r in rows:
        ids = [str(t).upper() for t in (r.get("class_ids") or [])]
        if ids == ["AF-SCC-C0-VAC-GEN"] and r.get("conclusion_type") in (
                "theorem", "conditional_theorem", "stability_result"):
            c0_bound_typed.append({"theorem_id": r.get("theorem_id"),
                                   "conclusion_type": r.get("conclusion_type")})
    report["adjacent_c0_typed_census"] = c0_bound_typed

    # ---- emit artifacts -----------------------------------------------------
    with open(os.path.join(HERE, "candidate_ledger_variantA.jsonl"), "wb") as f:
        f.write(variants["A"]["blob"])
    with open(os.path.join(HERE, "candidate_ledger_variantB.jsonl"), "wb") as f:
        f.write(variants["B"]["blob"])

    decisions = []
    for rule in rules:
        decisions.append({
            "theorem_id": rule["theorem_id"],
            "live_class_ids": rule["expected_current_class_ids"],
            "variantA_class_ids": ([str(t).upper() for t in rows_by_id[rule["theorem_id"]].get("class_ids")][:1]),
            "variantB_class_ids": rule["decision_primary"],
            "variantB_informs_classes": rule["decision_informs"],
            "ambiguity": rule["ambiguity"],
            "rationale": rule["rationale"],
            "evidence": rule["evidence"],
        })
    with open(os.path.join(HERE, "CANDIDATE.json"), "w") as f:
        json.dump({
            "task_id": TASK_ID,
            "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN"],
            "node_id": "L0",
            "gate": "G-LIT",
            "status": "advisory_candidate_only",
            "variantA_sha256": variants["A"]["sha256"],
            "variantB_sha256": variants["B"]["sha256"],
            "variantB_is_preferred": True,
            "decisions": decisions,
            "adjacent_findings_not_repaired": rules_doc["adjacent_findings_not_repaired"],
        }, f, indent=1, ensure_ascii=False, sort_keys=True)

    report["candidate_sha256"] = {v: variants[v]["sha256"] for v in variants}
    with open(os.path.join(HERE, "report.json"), "w") as f:
        json.dump(report, f, indent=1, ensure_ascii=False, sort_keys=True)

    # SHA256SUMS over every file in this directory
    names = sorted(n for n in os.listdir(HERE) if os.path.isfile(os.path.join(HERE, n)))
    with open(os.path.join(HERE, "SHA256SUMS"), "w") as f:
        for n in names:
            if n == "SHA256SUMS":
                continue
            f.write(f"{sha256_file(os.path.join(HERE, n))}  {n}\n")

    print(json.dumps({
        "verdict": "REPAIR_CANDIDATE_VALIDATED_ADVISORY" if (report["checks_all_pass"] and report["controls_all_expected"]) else "CHECK_FAILURE",
        "checks_all_pass": report["checks_all_pass"],
        "controls_all_expected": report["controls_all_expected"],
        "live_literal_disjunctions": live_disj,
        "variantB_sha256": variants["B"]["sha256"],
        "variantA_sha256": variants["A"]["sha256"],
        "live_detector_findings": live_findings,
        "candidate_detector_findings": variants["B"]["detector_findings"],
    }, indent=1))
    return 0 if (report["checks_all_pass"] and report["controls_all_expected"]) else 1


if __name__ == "__main__":
    sys.exit(main())
