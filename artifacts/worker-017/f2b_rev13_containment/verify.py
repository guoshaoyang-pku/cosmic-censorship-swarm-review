#!/usr/bin/env python3
"""
W017-F2B-REV13-CONTAINMENT-ADJUDICATION-01
Independent, bounded, class-bound adjudication at the FROZEN rev29 pin.

Target class : AF-SCC-C0-VAC-GEN   (node F2b, gate G-FORM)
Pinned bytes : schemas/af_scc_c0_vacuum.yaml sha256 b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c

Question (two carried containment carriers):
  H1  implication_ledger.forbidden_transfers[0].reason  ("C2 is a strictly larger extension class, ...")
  H2  regularity.must_not_conflate[0]                    ("No containment with C2 or C0 is asserted here ...")

Method: fail-closed. All inputs hash-pinned before any judgement; canonical files are never
modified (mutants are written to a sandbox copy); the canonical structural gate
(artifacts/formulation/tools/check_class_schema.py) is run on canonical + pre-registered mutants;
every check carries its own falsifier; pins are re-measured at exit and drift voids the run.

exit 0 = adjudication produced; exit 2 = pin drift / missing input (no claim).
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def abspath(rel):
    return os.path.join(ROOT, rel)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


HERE = os.path.dirname(os.path.abspath(__file__))
SANDBOX = os.path.join(HERE, "sandbox")
GATE = "artifacts/formulation/tools/check_class_schema.py"

# ---------------------------------------------------------------------------
# 1. Pins (all 64-char hashes measured 2026-09-12 by worker-017 before writing)
# ---------------------------------------------------------------------------
PINS = {
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "artifacts/worker-007/rev29_preflight/snapshot/af_scc_c0_vacuum.55d0a1ea9bda.yaml":
        "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml":
        "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/formulation/rule_spec.json":
        "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/formulation/tools/check_class_schema.py":
        "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "artifacts/formulation/evidence/taxonomy_consistency.json":
        "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
}

TARGET = "schemas/af_scc_c0_vacuum.yaml"
SIBLING = "schemas/af_scc_c2_vacuum.yaml"
REV12 = "artifacts/worker-007/rev29_preflight/snapshot/af_scc_c0_vacuum.55d0a1ea9bda.yaml"

H1_MARK = "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"
H2_MARK = "No containment with C2 or C0 is asserted here"


def measure_pins():
    return {p: sha256(abspath(p)) for p in PINS}


def line_of(text, needle):
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    return None


def yaml_block(text, key, indent=0):
    """Return the raw text of a top-level (or given-indent) block, naive but deterministic."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^ {%d}%s:" % (indent, re.escape(key)), line):
            start = i
            break
    if start is None:
        return None
    out = [lines[start]]
    for line in lines[start + 1:]:
        if re.match(r"^ {%d}\S" % indent, line):
            break
        out.append(line)
    return "\n".join(out)


def check(cid, ok, statement, evidence, falsifier, kind="semantic"):
    return {"id": cid, "kind": kind, "pass": bool(ok), "statement": statement,
            "evidence": evidence, "falsifier": falsifier}


def main():
    pins_before = measure_pins()
    drift = {p: {"expected": PINS[p], "measured": pins_before[p]}
             for p in PINS if PINS[p] != pins_before[p]}
    if drift:
        json.dump({"status": "PIN_DRIFT", "drift": drift}, sys.stdout, indent=1)
        sys.exit(2)

    f2b = open(abspath(TARGET), encoding="utf-8").read()
    f2a = open(abspath(SIBLING), encoding="utf-8").read()
    rev12 = open(abspath(REV12), encoding="utf-8").read()
    frozen = json.load(open(abspath("artifacts/formulation/FROZEN.json"), encoding="utf-8"))
    rule_spec = json.load(open(abspath("artifacts/formulation/rule_spec.json"), encoding="utf-8"))
    taxonomy = open(abspath("research_map/formulation_taxonomy.yaml"), encoding="utf-8").read()

    checks = []

    # ---- pins / manifest -------------------------------------------------
    checks.append(check(
        "CHK-01", pins_before[TARGET] == pins_before["artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"]
        and pins_before[TARGET] == PINS[TARGET],
        "canonical F2b bytes are b2ab6acb and the two canonical paths are byte-identical",
        {"schemas": pins_before[TARGET], "artifacts/formulation/schemas": pins_before["artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"]},
        "either copy differs from b2ab6acb2bbe, or the two paths diverge."))

    frozen_pin = frozen["files"]["schemas/af_scc_c0_vacuum.yaml"]["sha256"]
    checks.append(check(
        "CHK-02", frozen_pin == PINS[TARGET] and frozen.get("revision") == 29,
        "FROZEN rev29 binds F2b to the reviewed hash (gate verdicts are hash-bound)",
        {"frozen_revision": frozen.get("revision"), "frozen_sha256": frozen_pin},
        "FROZEN rev differs or binds a different F2b sha256, making the pin stale."))

    # ---- carrier presence and line identity ------------------------------
    h1_line = line_of(f2b, H1_MARK)
    h2_line = line_of(f2b, H2_MARK)
    checks.append(check(
        "CHK-03", h1_line is not None,
        "H1 carrier present verbatim at the reviewed bytes",
        {"line": h1_line, "text": H1_MARK},
        "carrier absent at b2ab6acb; the finding is void."))
    checks.append(check(
        "CHK-04", h2_line is not None,
        "H2 carrier present verbatim at the reviewed bytes",
        {"line": h2_line, "text": H2_MARK},
        "carrier absent at b2ab6acb; the finding is void."))

    checks.append(check(
        "CHK-05", H1_MARK in rev12 and H2_MARK in rev12
        and line_of(rev12, H1_MARK) is not None and line_of(rev12, H2_MARK) is not None,
        "both carriers are byte-identical at the pinned rev12 (55d0a1ea) and rev13 (b2ab6acb): the rev13 evidence-binding repair did not touch them",
        {"rev12_sha256": PINS[REV12], "rev12_h1_line": line_of(rev12, H1_MARK), "rev12_h2_line": line_of(rev12, H2_MARK)},
        "either carrier differs between the two pinned revisions; the carried-forward claim is then void."))

    # ---- H1: premise contradicts the document's own chain ---------------
    chain_line = line_of(f2b, "extension_class_containment:")
    chain = f2b.splitlines()[chain_line - 1] if chain_line else ""
    ranks = {}
    for tok, rank in (("E_C2", 0), ("E_{C^1,1}", 1), ("E_H2loc", 2), ("E_C0", 3)):
        ranks[tok] = rank
    chain_ok = ("E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2" in chain)
    checks.append(check(
        "CHK-06", chain_ok,
        "F2b's own extension_class_containment makes E_C2 the SMALLEST admissible-extension set (rank 0 of 0..3)",
        {"line": chain_line, "chain": chain.strip()},
        "the containment chain does not place E_C2 innermost; the 'larger' premise would then not be inverted."))

    h1_owe = [l for l in f2b.splitlines() if "one_way_entailments" in l]
    entail_rows = re.findall(r"E_C2 subset of E_H2loc|E_H2loc subset of E_C0|E_C2 subset of E_C0", f2b)
    checks.append(check(
        "CHK-07", len(entail_rows) >= 2,
        "the same document derives one-way entailments from the C2-innermost containment",
        {"entailment_substrings_found": entail_rows},
        "the document does not actually assert the C2-innermost containment elsewhere; H1 would be an isolated slip."))

    # the forbidden pair from/to is CORRECT (so the defect is the premise, not the prohibition)
    h1_row = f2b.splitlines()[h1_line - 1] if h1_line else ""
    pair_ok = ('from: "no proper future C2 extension"' in h1_row and 'to: "this class"' in h1_row)
    weaker_ok = "C2-inextendibility is strictly weaker" in h1_row
    checks.append(check(
        "CHK-08", pair_ok and weaker_ok,
        "H1's forbidden pair and its conclusion are CORRECT (E_C2 rank 0 < this class rank 3, so C2-inextendibility is weaker); only the stated premise is inverted",
        {"row": h1_row.strip()},
        "the from/to pair or the weaker-conclusion is itself wrong, which would make H1 a different (larger) defect."))

    checks.append(check(
        "CHK-09", ("strictly larger extension class" in h1_row) and ranks["E_C2"] == 0,
        "H1 premise calls C2 a strictly larger extension class while the file's chain makes E_C2 the smallest set: inverted premise",
        {"premise_rank_of_C2": ranks["E_C2"], "largest_rank": max(ranks.values()), "row": h1_row.strip()},
        "an extension-set reading exists under which E_C2 strictly contains E_C0 given the file's own definitions."))

    # ---- H2: denial contradicts the same document ------------------------
    h2_row = f2b.splitlines()[h2_line - 1] if h2_line else ""
    led = yaml_block(f2b, "implication_ledger")
    led_tokens = bool(led and re.search(r"E_C2", led) and re.search(r"E_C0", led))
    checks.append(check(
        "CHK-10", led_tokens and "No containment with C2 or C0 is asserted here" in h2_row,
        "H2 lives in regularity.must_not_conflate while implication_ledger in the SAME document asserts containments involving both C2 and C0",
        {"must_not_conflate_line": h2_line, "ledger_mentions_E_C2": bool(led and "E_C2" in led), "ledger_mentions_E_C0": bool(led and "E_C0" in led)},
        "the denial is scoped so narrowly that it cannot be read against the ledger (no such scoping text present); then H2 is non-blocking prose."))

    f2a_fix = "the earlier 'no containment with C2 is asserted' was wrong" in f2a
    f2a_reason = "the converse containment is false" in f2a
    checks.append(check(
        "CHK-11", f2a_fix and f2a_reason,
        "the sibling F2a (same owner, same class family) carries the corrected counterparts and records the denial wording as wrong, so F2b's wording is stale rather than intended",
        {"f2a_sibling_sha256": PINS[SIBLING], "f2a_marks_denial_wrong": f2a_fix, "f2a_forbidden_reason": f2a_reason},
        "F2a does not contain the corrected counterparts; the 'stale vs intended' reading loses its within-corpus reference."))

    # ---- normativity (required slots) ------------------------------------
    r06 = next((r for r in rule_spec["rules"] if r.get("id") == "R06"), {})
    r16 = next((r for r in rule_spec["rules"] if r.get("id") == "R16"), {})
    r06_req = "must_not_conflate is a non-empty list" in r06.get("require", "")
    r16_req = "implication_ledger records the one-way statements" in r16.get("require", "")
    checks.append(check(
        "CHK-12", r06_req and r16_req,
        "both carriers sit in slots the frozen class contract marks as required (rule_spec R06 must_not_conflate non-empty; R16 implication_ledger one-way + forbidden), so their content is normative, not optional prose",
        {"R06_require": r06.get("require"), "R16_require": r16.get("require")},
        "rule_spec R06/R16 do not require these slots, or mark them advisory; then the defects are documentation findings only."))

    # ---- f0 binding resolves (positive control on the same revision) -----
    f0b = yaml_block(f2b, "f0_binding")
    decl = re.search(r'declared_f0_sha256:\s*"([0-9a-f]{64})"', f0b or "")
    cons = re.search(r'consistency_evidence_sha256:\s*"([0-9a-f]{64})"', f0b or "")
    live_tax = sha256(abspath("research_map/formulation_taxonomy.yaml"))
    live_cons = sha256(abspath("artifacts/formulation/evidence/taxonomy_consistency.json"))
    checks.append(check(
        "CHK-13", bool(decl) and bool(cons) and decl.group(1) == live_tax and cons.group(1) == live_cons,
        "the rev13 f0_binding chain resolves against the live declared F0 and consistency evidence (the rev13 repair landed)",
        {"declared_f0_sha256": decl.group(1) if decl else None, "live": live_tax,
         "consistency_evidence_sha256": cons.group(1) if cons else None, "live_consistency": live_cons},
        "a declared binding hash does not resolve at its named path, which would be a separate blocking defect."))

    # ---- canonical gate: canonical + pre-registered mutants --------------
    os.makedirs(SANDBOX, exist_ok=True)
    base = f2b

    def repl(text, old, new, count=1):
        assert old in text, "mutant anchor missing: %r" % old[:60]
        return text.replace(old, new, count)

    def drop_line(text, needle, replacement):
        lines = text.splitlines()
        hits = 0
        for i, line in enumerate(lines):
            if needle in line:
                lines[i] = replacement
                hits += 1
        assert hits == 1, "drop_line anchor hits=%d" % hits
        return "\n".join(lines) + "\n"

    mutants = {}

    mutants["M0_canonical"] = (base, "pass")

    mutants["M1_h1_premise_repaired"] = (
        repl(base, "C2 is a strictly larger extension class", "C2 is a strictly smaller extension class"),
        "pass")

    mutants["M2_h1_conclusion_inverted"] = (
        repl(base, "so C2-inextendibility is strictly weaker", "so C2-inextendibility is strictly stronger"),
        "pass")

    mutants["M3_h1_reason_nonsense"] = (
        repl(base, "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker", "zzz"),
        "pass")

    mutants["M4_h2_denial_deleted"] = (
        repl(base, "No containment with C2 or C0 is asserted here; ", ""),
        "pass")

    mutants["M5_h2_denial_replaced_by_false_containment"] = (
        repl(base, "No containment with C2 or C0 is asserted here",
             "E_C0 is asserted to contain every C2 extension class here"),
        "pass")

    mutants["M6_must_not_conflate_emptied"] = (
        repl(base, "  must_not_conflate:\n", "  must_not_conflate: []\n  _disabled_must_not_conflate:\n"),
        "fail")

    mutants["M7_must_not_conflate_first_entry_emptied"] = (
        drop_line(base, H2_MARK, '    - ""'),
        "pass")

    mutants["M8_forbidden_row_reversed_to_required_direction"] = (
        repl(base, '- {from: "no proper future C2 extension", to: "this class", reason: "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"}',
             '- {from: "no proper future C0 extension", to: "no proper future C2 extension", reason: "inverted control"}'),
        "fail")

    mutants["M9_implication_ledger_deleted"] = (
        re.sub(r"\nimplication_ledger:\n(?:.*\n)*?(?=falsifier:)", "\n", base),
        "fail")

    mutants["M10_containment_chain_reversed"] = (
        repl(base, "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2",
             "E_C2 contains E_{C^1,1} contains E_H2loc contains E_C0"),
        "pass")

    mutants["M11_extension_regularity_removed"] = (
        re.sub(r"\n  extension_regularity: C0\n", "\n", base),
        "fail")

    gate_results = {}
    for name, (text, expected) in mutants.items():
        path = os.path.join(SANDBOX, name + ".yaml")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        proc = subprocess.run([sys.executable, abspath(GATE), "--json", path],
                              capture_output=True, text=True, cwd=ROOT)
        try:
            payload = json.loads(proc.stdout)
        except Exception:
            payload = {"raw": proc.stdout[:500], "stderr": proc.stderr[:500]}
        actual = "pass" if proc.returncode == 0 else "fail"
        gate_results[name] = {
            "expected": expected, "actual": actual, "matches_prereg": actual == expected,
            "exit_code": proc.returncode, "verdict": payload.get("verdict"),
            "failed_rules": payload.get("failed_rules"),
            "failures": payload.get("failures"),
        }
    controls_ok = all(v["matches_prereg"] for v in gate_results.values())
    checks.append(check(
        "CHK-14", controls_ok,
        "pre-registered canonical-gate mutant sweep behaves as predicted (11 mutants + canonical), including the blindness controls",
        gate_results,
        "any mutant departs from its pre-registered expectation; the blindness claim is then instrument-limited and must be restated."))
    checks.append(check(
        "CHK-15", gate_results["M0_canonical"]["actual"] == "pass"
        and gate_results["M1_h1_premise_repaired"]["actual"] == "pass"
        and gate_results["M2_h1_conclusion_inverted"]["actual"] == "pass"
        and gate_results["M3_h1_reason_nonsense"]["actual"] == "pass"
        and gate_results["M4_h2_denial_deleted"]["actual"] == "pass"
        and gate_results["M5_h2_denial_replaced_by_false_containment"]["actual"] == "pass"
        and gate_results["M10_containment_chain_reversed"]["actual"] == "pass",
        "the canonical structural gate PASSES the defective canonical file and every semantically different H1/H2 variant, including a fully inverted H1 conclusion and a reversed containment chain: a gate PASS cannot certify these two carriers",
        {k: gate_results[k]["actual"] for k in ("M0_canonical", "M1_h1_premise_repaired",
                                                "M2_h1_conclusion_inverted", "M3_h1_reason_nonsense",
                                                "M4_h2_denial_deleted",
                                                "M5_h2_denial_replaced_by_false_containment",
                                                "M10_containment_chain_reversed")},
        "the gate rejects any of the semantically defective variants, which would make the defect machine-detectable and change the disposition."))

    # ---- gate liveness controls ------------------------------------------
    checks.append(check(
        "CHK-16", gate_results["M6_must_not_conflate_emptied"]["actual"] == "fail"
        and gate_results["M8_forbidden_row_reversed_to_required_direction"]["actual"] == "fail"
        and gate_results["M9_implication_ledger_deleted"]["actual"] == "fail"
        and gate_results["M11_extension_regularity_removed"]["actual"] == "fail",
        "the same gate is alive: it rejects emptied must_not_conflate (R06), a forbidden C0=>C2 row (R16), a deleted ledger (R16), and a removed extension_regularity token (R06)",
        {k: gate_results[k]["actual"] for k in ("M6_must_not_conflate_emptied",
                                                "M8_forbidden_row_reversed_to_required_direction",
                                                "M9_implication_ledger_deleted",
                                                "M11_extension_regularity_removed")},
        "the gate misses one of these structural mutants; the liveness control fails."))

    # ---- no C0/C2 conclusion merge (full-verdict positive surface) -------
    doc = yaml.safe_load(f2b)
    reg = doc.get("regularity") or {}
    c0s = doc.get("c0_specifics") or {}
    fal = doc.get("falsifier") or {}
    concl_fields = {
        "scope_statement": doc.get("scope_statement"),
        "extension_regularity": reg.get("extension_regularity"),
        "extension_regularity_exact": reg.get("extension_regularity_exact"),
        "conclusion_relation_to_sibling": c0s.get("conclusion_relation_to_sibling"),
        "falsifier_tier1_refutes": (fal.get("tier_1") or {}).get("refutes"),
        "falsifier_tier2_refutes": (fal.get("tier_2") or {}).get("refutes"),
    }
    merge_re = re.compile(r"C0\s*(?:or|/|and)\s*C2|C2\s*(?:or|/|and)\s*C0")
    merge_hits = {k: v for k, v in concl_fields.items() if v and merge_re.search(str(v))}
    anti_scope = doc.get("anti_scope") or {}
    c2_in_anti = any(isinstance(e, dict) and e.get("class_id") == "AF-SCC-C2-VAC-GEN"
                     for e in (anti_scope.get("not_this_class") or []))
    checks.append(check(
        "CHK-17", not merge_hits and c2_in_anti,
        "no C0/C2 composite token in any conclusion-bearing field; C2 is listed under anti_scope.not_this_class (raw 'C2 or C0' occurrences at :152 and :278 are prohibitions, not conclusions)",
        {"conclusion_fields": concl_fields, "merge_hits": merge_hits, "c2_in_anti_scope": c2_in_anti},
        "a composite C0-or-C2 conclusion token or a missing C2 anti-scope entry; that would be a separate blocking defect."))

    # ---- pin stability ----------------------------------------------------
    pins_after = measure_pins()
    stable = pins_after == pins_before
    drift_after = {p: {"before": pins_before[p], "after": pins_after[p]}
                   for p in PINS if pins_before[p] != pins_after[p]}
    checks.append(check(
        "CHK-18", stable,
        "pre==post input hash stability across the whole instrument run (no in-flight pin movement)",
        {"drift": drift_after},
        "any pinned input moved during the run; the verdict is void on the moved input."))

    report = {
        "task_id": "W017-F2B-REV13-CONTAINMENT-ADJUDICATION-01",
        "worker": "worker-017",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "node_id": "F2b",
        "gate": "G-FORM",
        "target": TARGET,
        "target_sha256": pins_before[TARGET],
        "frozen_revision": frozen.get("revision"),
        "frozen_sha256": pins_before["artifacts/formulation/FROZEN.json"],
        "pins": pins_before,
        "pins_stable": stable,
        "checks": checks,
        "checks_passed": sum(1 for c in checks if c["pass"]),
        "checks_total": len(checks),
        "canonical_gate": gate_results,
        "controls_ok": controls_ok,
        "disposition": {
            "H1_inverted_premise": h1_line is not None and h1_row and "strictly larger extension class" in h1_row,
            "H2_stale_denial": h2_line is not None,
            "H1_line": h1_line, "H2_line": h2_line,
            "both_carried_from_rev12": H1_MARK in rev12 and H2_MARK in rev12,
        },
        "non_claims": ["no node completion", "no gate verdict", "no validation_status=passed",
                       "no edit to any canonical artifact", "verdict binds b2ab6acb2bbe only"],
    }
    with open(os.path.join(HERE, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=False)
    with open(os.path.join(HERE, "controls.json"), "w", encoding="utf-8") as fh:
        json.dump({"controls_ok": controls_ok, "mutants": gate_results}, fh, indent=1)
    with open(os.path.join(HERE, "pins.json"), "w", encoding="utf-8") as fh:
        json.dump({"before": pins_before, "after": pins_after, "stable": stable}, fh, indent=1)

    print(json.dumps({"checks": f"{report['checks_passed']}/{report['checks_total']}",
                      "controls_ok": controls_ok,
                      "H1_line": h1_line, "H2_line": h2_line,
                      "gate_M0": gate_results["M0_canonical"]["actual"],
                      "report_sha256": sha256(os.path.join(HERE, "report.json"))}, indent=1))
    if not stable:
        sys.exit(2)


if __name__ == "__main__":
    main()
