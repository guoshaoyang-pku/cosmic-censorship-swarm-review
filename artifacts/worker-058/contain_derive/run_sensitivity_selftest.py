#!/usr/bin/env python3
"""W058-CONTAIN-DERIVE-04 sensitivity self-test.

Stages mutant trees under _scratch/ and runs the frozen derive_containment.py against each.
Every expectation is asserted; the harness fails closed if any mutation does not apply
byte-exactly or if any case diverges.  The M1 case is the pre-registered acceptance test:
the two recorded C0 repairs (inversion + stale denial) make the unmodified checker PASS.

Usage: python3 run_sensitivity_selftest.py
Exit 0 = all expectations met, 1 = any divergence.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SCRATCH = os.path.join(HERE, "_scratch")
CHECKER = os.path.join(HERE, "derive_containment.py")

INPUTS = [
    "schemas/af_scc_c0_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/VARIANT_REGISTRY.json",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/FROZEN.json",
]


def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def stage(name: str) -> str:
    root = os.path.join(SCRATCH, name)
    if os.path.isdir(root):
        shutil.rmtree(root)
    for rel in INPUTS:
        dst = os.path.join(root, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(ROOT, rel), dst)
    return root


def patch(root: str, rel: str, old: str, new: str, count: int = 1) -> None:
    p = os.path.join(root, rel)
    t = open(p, encoding="utf-8").read()
    if t.count(old) < count:
        raise AssertionError(f"mutation anchor not found ({t.count(old)}x): {old[:80]!r} in {rel}")
    t2 = t.replace(old, new, count)
    assert t2 != t
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(t2)


def run(root: str, require_frozen: bool) -> dict:
    out = os.path.join(root, "result.json")
    cmd = [sys.executable, CHECKER, "--root", root, "--out", out]
    if not require_frozen:
        cmd.append("--no-require-frozen-match")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if not os.path.exists(out):
        raise AssertionError(f"checker produced no output (rc={proc.returncode}): {proc.stderr[-400:]}")
    return json.load(open(out, encoding="utf-8"))


def codes(result: dict, severity: str) -> set[str]:
    key = "hard_findings" if severity == "hard" else "advisories"
    return {f["code"] for f in result.get(key, [])}


def link_status(result: dict) -> dict[str, str]:
    return {l["link_id"]: l["status"] for l in result["chain"]["links"]}


def main() -> int:
    os.makedirs(SCRATCH, exist_ok=True)
    cases, failures = [], []

    def check(name, result, expect_verdict=None, expect_hard=None, expect_adv=None,
              expect_links=None, expect_frozen_match=None):
        obs = {
            "verdict": result["verdict"],
            "hard_codes": sorted(codes(result, "hard")),
            "advisory_codes": sorted(codes(result, "advisory")),
            "link_status": link_status(result),
            "frozen_match": result["inputs"]["frozen_match"],
        }
        exp = {
            "verdict": expect_verdict,
            "hard_codes": sorted(expect_hard) if expect_hard is not None else None,
            "advisory_codes": sorted(expect_adv) if expect_adv is not None else None,
            "link_status": expect_links,
            "frozen_match": expect_frozen_match,
        }
        ok = True
        if expect_verdict is not None and obs["verdict"] != expect_verdict:
            ok = False
        if expect_hard is not None and set(obs["hard_codes"]) != set(expect_hard):
            ok = False
        if expect_adv is not None and set(obs["advisory_codes"]) != set(expect_adv):
            ok = False
        if expect_links is not None and obs["link_status"] != expect_links:
            ok = False
        if expect_frozen_match is not None and obs["frozen_match"] != expect_frozen_match:
            ok = False
        cases.append({"case": name, "expected": exp, "observed": obs, "met": ok})
        if not ok:
            failures.append(name)
        print(f"{'PASS' if ok else 'FAIL'}  {name}: verdict={obs['verdict']} "
              f"hard={obs['hard_codes']} adv={obs['advisory_codes']} links={obs['link_status']}")
        return ok

    DERIVED = {"L1": "derived", "L2": "derived", "L3": "derived"}

    # ---- CANON: bind the real bytes, require the FROZEN pins to match ----------
    canon = run(stage("CANON_canonical"), require_frozen=True)
    check("CANON_canonical", canon, expect_verdict="FAIL",
          expect_hard={"class_size_predicate_inverted"},
          expect_adv={"stale_containment_denial"}, expect_links=DERIVED,
          expect_frozen_match=True)

    # ---- CTRL: byte-identical copy (determinism / no copy sensitivity) ---------
    ctrl = run(stage("CTRL_byte_copy"), require_frozen=True)
    check("CTRL_byte_copy", ctrl, expect_verdict=canon["verdict"],
          expect_hard=codes(canon, "hard"), expect_adv=codes(canon, "advisory"),
          expect_links=link_status(canon), expect_frozen_match=True)

    # ---- M1: pre-registered acceptance -- both recorded repairs ----------------
    m1 = stage("M1_both_repairs")
    patch(m1, "schemas/af_scc_c0_vacuum.yaml",
          "C2 is a strictly larger extension class", "C2 is a strictly smaller extension class")
    patch(m1, "schemas/af_scc_c0_vacuum.yaml",
          "No containment with C2 or C0 is asserted here;",
          "Containment with C2 and C0 is declared in implication_ledger;")
    r1 = run(m1, require_frozen=False)
    check("M1_both_repairs", r1, expect_verdict="PASS", expect_hard=set(), expect_adv=set(),
          expect_links=DERIVED, expect_frozen_match=False)

    # ---- M1a: only the inversion repaired; denial persists ---------------------
    m1a = stage("M1a_inversion_only")
    patch(m1a, "schemas/af_scc_c0_vacuum.yaml",
          "C2 is a strictly larger extension class", "C2 is a strictly smaller extension class")
    r1a = run(m1a, require_frozen=False)
    check("M1a_inversion_only", r1a, expect_verdict="PASS", expect_hard=set(),
          expect_adv={"stale_containment_denial"}, expect_links=DERIVED,
          expect_frozen_match=False)
    # NOTE: advisory-only results do not fail the checker's exit code; M1a is the
    # "repair A landed, repair B still open" state.

    # ---- M1b: only the denial scoped; inversion persists -----------------------
    m1b = stage("M1b_denial_only")
    patch(m1b, "schemas/af_scc_c0_vacuum.yaml",
          "No containment with C2 or C0 is asserted here;",
          "Containment with C2 and C0 is declared in implication_ledger;")
    r1b = run(m1b, require_frozen=False)
    check("M1b_denial_only", r1b, expect_verdict="FAIL",
          expect_hard={"class_size_predicate_inverted"}, expect_adv=set(),
          expect_links=DERIVED, expect_frozen_match=False)

    # ---- M2: C0 chain reordered (direction word now contradicts order) ---------
    m2 = stage("M2_chain_reordered_C0")
    patch(m2, "schemas/af_scc_c0_vacuum.yaml",
          "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2",
          "E_C0 contains E_{C^1,1} contains E_H2loc contains E_C2")
    r2 = run(m2, require_frozen=False)
    check("M2_chain_reordered_C0", r2, expect_verdict="FAIL",
          expect_hard={"chain_declaration_not_canonical", "class_size_predicate_inverted"},
          expect_adv={"stale_containment_denial"},
          expect_links=DERIVED, expect_frozen_match=False)

    # ---- M3: C2 structured chain fully reversed --------------------------------
    m3 = stage("M3_chain_reversed_C2")
    patch(m3, "schemas/af_scc_c2_vacuum.yaml",
          'extension_class_containment: "E_C2 subset of E_{C^1,1} subset of E_H2loc '
          'subset of E_C0',
          'extension_class_containment: "E_C0 subset of E_H2loc subset of E_{C^1,1} '
          'subset of E_C2')
    r3 = run(m3, require_frozen=False)
    check("M3_chain_reversed_C2", r3, expect_verdict="FAIL",
          expect_hard={"chain_declaration_not_canonical", "class_size_predicate_inverted",
                       "subset_assertion_reversed"},
          expect_adv={"stale_containment_denial"}, expect_links=DERIVED,
          expect_frozen_match=False)

    # ---- M4: H2LOC definition stripped of the continuity conjunct --------------
    m4 = stage("M4_h2loc_continuity_stripped")
    patch(m4, "artifacts/formulation/VARIANT_REGISTRY.json",
          "extension class: continuous metric with Riemann tensor in L^2_loc (H2_loc).",
          "extension class: Riemann tensor in L^2_loc (H2_loc).")
    r4 = run(m4, require_frozen=False)
    check("M4_h2loc_continuity_stripped", r4, expect_verdict="FAIL",
          expect_hard={"class_size_predicate_inverted", "containment_link_under_justified"},
          expect_adv={"stale_containment_denial"},
          expect_links={"L1": "derived", "L2": "derived", "L3": "under_justified"},
          expect_frozen_match=False)

    # ---- M5: fresh inversion planted inside C2 ---------------------------------
    m5 = stage("M5_planted_inversion_C2")
    patch(m5, "schemas/af_scc_c2_vacuum.yaml",
          '{from: "no proper future C2 extension", to: "no proper future C0 extension", '
          'reason: "the converse containment is false"}',
          '{from: "no proper future C2 extension", to: "no proper future C0 extension", '
          'reason: "C2 is a strictly larger extension class, so C2-inextendibility is '
          'strictly weaker"}')
    r5 = run(m5, require_frozen=False)
    check("M5_planted_inversion_C2", r5, expect_verdict="FAIL",
          expect_hard={"class_size_predicate_inverted"}, expect_adv=None,
          expect_links=DERIVED, expect_frozen_match=False)

    # ---- M6: F0 vocabulary regression (re-introduce the 'hence also' claim) ----
    m6 = stage("M6_f0_vocab_regression")
    patch(m6, "research_map/formulation_taxonomy.yaml",
          "It does NOT forbid C^{1,1} or H^2_loc extensions",
          "It also forbids C^{1,1} and H^2_loc extensions")
    r6 = run(m6, require_frozen=False)
    check("M6_f0_vocab_regression", r6, expect_verdict="FAIL",
          expect_hard={"class_size_predicate_inverted",
                       "f0_meaning_C2_claims_larger_classes_forbidden"},
          expect_adv={"stale_containment_denial"}, expect_links=DERIVED,
          expect_frozen_match=False)

    # ---- M7: FROZEN pin altered -> drift must be reported ----------------------
    m7 = stage("M7_frozen_pin_altered")
    p = os.path.join(m7, "artifacts/formulation/FROZEN.json")
    fz = json.load(open(p, encoding="utf-8"))
    fz["files"]["schemas/af_scc_c0_vacuum.yaml"]["sha256"] = "0" * 64
    json.dump(fz, open(p, "w", encoding="utf-8"), indent=1)
    r7 = run(m7, require_frozen=False)
    check("M7_frozen_pin_altered_flag_off", r7, expect_verdict="FAIL",
          expect_hard={"class_size_predicate_inverted"}, expect_adv=None, expect_links=None,
          expect_frozen_match=False)
    r7b = run(m7, require_frozen=True)
    check("M7_frozen_pin_altered_flag_on", r7b, expect_verdict="FAIL",
          expect_hard={"class_size_predicate_inverted", "frozen_pin_drift"}, expect_adv=None,
          expect_links=None, expect_frozen_match=False)

    all_met = not failures
    result = {
        "artifact": "w058_containment_derivation_sensitivity",
        "task_id": "W058-CONTAIN-DERIVE-04",
        "worker": "worker-058",
        "generated_at": __import__("datetime").datetime.now().astimezone().isoformat(
            timespec="seconds"),
        "checker": "artifacts/worker-058/contain_derive/derive_containment.py",
        "checker_sha256": hashlib.sha256(open(CHECKER, "rb").read()).hexdigest(),
        "cases": cases,
        "cases_total": len(cases),
        "cases_met": sum(1 for c in cases if c["met"]),
        "failures": failures,
        "all_expectations_met": all_met,
        "acceptance_case": "M1_both_repairs: the two recorded C0 repairs make the unmodified "
                           "checker PASS (hard=0) with all three links still derived",
        "falsifier": "any mutant above that the checker reports with the canonical verdict, or "
                     "any canonical verdict that differs from the bound-byte expectation",
    }
    out = os.path.join(HERE, "sensitivity_selftest.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1)
        fh.write("\n")
    print(f"\n{result['cases_met']}/{result['cases_total']} met; "
          f"all_expectations_met={all_met}; written {out}")
    return 0 if all_met else 1


if __name__ == "__main__":
    sys.exit(main())
