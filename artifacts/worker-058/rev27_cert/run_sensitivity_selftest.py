#!/usr/bin/env python3
"""Sensitivity self-test for W058-REV27-CERT-03 `check_rev12_delta.py`.

Builds mutant trees under `_scratch/` from the live canonical SCC pair and checks that the
delta certificate reports exactly the expected hard checks on each. Calibration targets:

  CTRL_byte_identical  identical copy  -> same verdict as canonical, no extra hard checks
  MUT_dup_key          duplicate YAML key planted           -> C1_duplicate_keys
  MUT_future_stamp     future revised_at planted            -> C2_wall_clock
  MUT_dangling_pointer class_contract_pointer target removed -> C3_pointer
  MUT_stale_pair       pair-typed regularity binder planted -> C4_stale_pair_binder
  MUT_ok_repair        both pre-registered repairs applied  -> PASS, zero hard checks
  MUT_frozen_pin_drift FROZEN pin altered                   -> D5_frozen_pin
  BASE_rev26           rev26 snapshot (M0)                  -> HF-1 + MINOR-1 open, C1 fails on both files

Also asserts that the acceptance checker `sweep_scc_order_frozen_copy.py` is byte-identical to
the tool recorded in the W058-REPAIR-CERT-02 events (sha256 ff4fba42...).
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SCRATCH = os.path.join(HERE, "_scratch")
CHECKER = os.path.join(HERE, "check_rev12_delta.py")
SWEEP = os.path.join(HERE, "sweep_scc_order_frozen_copy.py")
BASELINE = os.path.join(ROOT, "artifacts", "worker-058", "repair_cert", "_scratch", "M0_canonical")
SWEEP_RECORDED_SHA = "ff4fba42f4f07d9a056f2edfa687824815c056daf79ae2498fc4a1f6233c7bf3"
C0 = "schemas/af_scc_c0_vacuum.yaml"
C2 = "schemas/af_scc_c2_vacuum.yaml"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_tree(name, c0_text=None, c2_text=None, frozen=None):
    tree = os.path.join(SCRATCH, name)
    if os.path.exists(tree):
        shutil.rmtree(tree)
    os.makedirs(os.path.join(tree, "schemas"))
    os.makedirs(os.path.join(tree, "artifacts", "formulation"))
    os.makedirs(os.path.join(tree, "research_map"))
    if c0_text is None:
        c0_text = open(os.path.join(ROOT, C0), encoding="utf-8").read()
    if c2_text is None:
        c2_text = open(os.path.join(ROOT, C2), encoding="utf-8").read()
    open(os.path.join(tree, C0), "w", encoding="utf-8").write(c0_text)
    open(os.path.join(tree, C2), "w", encoding="utf-8").write(c2_text)
    # pointer-resolution targets must be present for a mutant root to be comparable
    shutil.copy(os.path.join(ROOT, "research_map", "formulation_taxonomy.yaml"),
                os.path.join(tree, "research_map", "formulation_taxonomy.yaml"))
    shutil.copy(os.path.join(ROOT, "artifacts", "formulation", "formulation_taxonomy.yaml"),
                os.path.join(tree, "artifacts", "formulation", "formulation_taxonomy.yaml"))
    if frozen is not None:
        with open(os.path.join(tree, "artifacts", "formulation", "FROZEN.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(frozen, fh)
    return tree


def run_checker(root, out_name):
    out = os.path.join(SCRATCH, out_name)
    proc = subprocess.run([sys.executable, CHECKER, "--root", root, "--out", out,
                           "--mutant", os.path.basename(root)],
                          capture_output=True, text=True)
    payload = json.load(open(out, encoding="utf-8")) if os.path.exists(out) else None
    return payload, proc.returncode, (proc.stderr or "").strip()[-300:]


def hard_checks(payload):
    return sorted({f["check"] for f in payload.get("hard_findings") or []})


def main():
    os.makedirs(SCRATCH, exist_ok=True)
    c0 = open(os.path.join(ROOT, C0), encoding="utf-8").read()
    c2 = open(os.path.join(ROOT, C2), encoding="utf-8").read()
    results, expectations = [], []

    # tool identity: the pre-registered acceptance checker must be unmodified
    tool_sha = sha256(SWEEP)
    expectations.append({
        "case": "sweep_tool_identity", "expect": [SWEEP_RECORDED_SHA], "got": [tool_sha],
        "met": tool_sha == SWEEP_RECORDED_SHA,
        "note": "frozen copy must equal the W058-REPAIR-CERT-02 recorded tool"})

    # canonical
    canon, rc_canon, err_canon = run_checker(ROOT, "cert_canonical.json")
    canon_hard = hard_checks(canon)
    expectations.append({
        "case": "CANONICAL_rev27", "expect": ["D6_HF1_open", "D6_MINOR1_open"],
        "got": canon_hard, "met": canon_hard == ["D6_HF1_open", "D6_MINOR1_open"],
        "sweep_verdict": (canon.get("delta", {}).get("sweep_now") or {}).get("verdict"),
        "note": "both pending C0 repairs must remain visible"})

    # CTRL byte-identical copy (no FROZEN manifest -> pin binding absent)
    tree = build_tree("CTRL_byte_identical")
    ctrl, _, err = run_checker(tree, "cert_ctrl.json")
    ctrl_hard = hard_checks(ctrl)
    expectations.append({
        "case": "CTRL_byte_identical", "expect": canon_hard, "got": ctrl_hard,
        "met": ctrl_hard == canon_hard,
        "note": "identical bytes must give an identical hard set"})

    # MUT duplicate key
    tree = build_tree("MUT_dup_key", c0_text=c0 + "\nrevision: 12\n")
    mut, _, err = run_checker(tree, "cert_mut_dup.json")
    got = hard_checks(mut)
    expectations.append({
        "case": "MUT_dup_key", "expect_subset": ["C1_duplicate_keys"], "got": got,
        "met": "C1_duplicate_keys" in got and "D6_HF1_open" in got,
        "note": "planted duplicate top-level key must be caught"})

    # MUT future timestamp
    tree = build_tree("MUT_future_stamp",
                      c0_text=c0.replace('revised_at: "2026-09-12T00:31:41+08:00"',
                                         'revised_at: "2027-01-01T00:00:00+08:00"'))
    mut, _, err = run_checker(tree, "cert_mut_future.json")
    got = hard_checks(mut)
    expectations.append({
        "case": "MUT_future_stamp", "expect_subset": ["C2_wall_clock"], "got": got,
        "met": "C2_wall_clock" in got, "note": "future-dated revised_at must be caught"})

    # MUT dangling pointer
    tree = build_tree("MUT_dangling_pointer",
                      c0_text=c0.replace(
                          "class_contract_pointer: research_map/formulation_taxonomy.yaml#classes.AF-SCC-C0-VAC-GEN",
                          "class_contract_pointer: research_map/formulation_taxonomy.yaml#classes.AF-SCC-NOPE"))
    mut, _, err = run_checker(tree, "cert_mut_pointer.json")
    got = hard_checks(mut)
    expectations.append({
        "case": "MUT_dangling_pointer", "expect_subset": ["C3_pointer"], "got": got,
        "met": "C3_pointer" in got, "note": "unresolvable class_contract_pointer must be caught"})

    # MUT stale pair-typed binder
    tree = build_tree("MUT_stale_pair",
                      c0_text=c0.replace(
                          '  ordered:\n    - {kind: forall, binder: "r", domain_id: D0}',
                          '  ordered:\n    - {kind: forall, binder: "(s,delta)", domain_id: D0}'))
    mut, _, err = run_checker(tree, "cert_mut_stale.json")
    got = hard_checks(mut)
    expectations.append({
        "case": "MUT_stale_pair", "expect_subset": ["C4_stale_pair_binder"], "got": got,
        "met": "C4_stale_pair_binder" in got,
        "note": "pre-rev12 pair-typed binder must be caught"})

    # MUT ok: both pre-registered mechanical repairs applied
    rep_c0 = c0.replace("C2 is a strictly larger extension class",
                        "C2 is a strictly smaller extension class")
    rep_c0 = rep_c0.replace('  forbidden_strengthenings:\n',
                            '  forbidden_strengthenings:\n    - "replacing future by two-sided direction"\n', 1)
    rep_c0 = rep_c0.replace('    - "replacing future by two-sided direction"\n  claim_promotion:',
                            '  claim_promotion:')
    tree = build_tree("MUT_ok_repair", c0_text=rep_c0)
    mut, _, err = run_checker(tree, "cert_mut_ok.json")
    got = hard_checks(mut)
    sweep_verdict = (mut.get("delta", {}).get("sweep_now") or {}).get("verdict")
    expectations.append({
        "case": "MUT_ok_repair", "expect": [], "got": got,
        "met": got == [] and sweep_verdict == "PASS",
        "sweep_verdict": sweep_verdict,
        "note": "both repairs must make the unmodified sweep PASS and leave zero hard checks"})

    # MUT frozen pin drift
    with open(os.path.join(ROOT, "artifacts", "formulation", "FROZEN.json"), encoding="utf-8") as fh:
        frozen = json.load(fh)
    frozen["files"][C0]["sha256"] = "0" * 64
    tree = build_tree("MUT_frozen_pin_drift", frozen=frozen)
    mut, _, err = run_checker(tree, "cert_mut_pin.json")
    got = hard_checks(mut)
    expectations.append({
        "case": "MUT_frozen_pin_drift", "expect_subset": ["D5_frozen_pin"], "got": got,
        "met": "D5_frozen_pin" in got, "note": "measured-vs-manifest pin drift must be caught"})

    # BASE rev26 (pre-rev12): duplicates + both repairs open
    if os.path.exists(os.path.join(BASELINE, C0)):
        base, _, err = run_checker(BASELINE, "cert_base.json")
        base_hard = hard_checks(base)
        base_c1 = base.get("rev12_claim_checks", {}).get("C1_duplicate_revised_at_collapsed", {})
        expectations.append({
            "case": "BASE_rev26",
            "expect_subset": ["C1_duplicate_keys", "C4_stale_pair_binder", "C3_pointer",
                              "D6_HF1_open", "D6_MINOR1_open"],
            "got": base_hard,
            "met": {"C1_duplicate_keys", "C4_stale_pair_binder", "D6_HF1_open",
                    "D6_MINOR1_open"}.issubset(set(base_hard))
                   and base_c1.get("status") == "failed",
            "note": "pre-rev12 bytes must fail duplicate-key and stale-pair checks and keep both "
                    "repairs open; C3_pointer is expected here only because the M0 snapshot root is "
                    "partial (taxonomy file absent by construction)"})
    else:
        expectations.append({"case": "BASE_rev26", "met": False, "got": [],
                             "note": "baseline snapshot missing"})

    all_met = all(e.get("met") for e in expectations)
    payload = {
        "artifact": "W058-REV27-CERT-03 sensitivity self-test",
        "worker": "worker-058",
        "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "task_id": "W058-REV27-CERT-03",
        "node_id": "F2b",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "checker": os.path.relpath(CHECKER, ROOT),
        "checker_sha256": sha256(CHECKER),
        "sweep_tool": os.path.relpath(SWEEP, ROOT),
        "sweep_tool_sha256": tool_sha,
        "sweep_tool_recorded_sha256": SWEEP_RECORDED_SHA,
        "canonical_hard_checks": canon_hard,
        "cases": expectations,
        "cases_met": sum(1 for e in expectations if e.get("met")),
        "cases_total": len(expectations),
        "all_expectations_met": all_met,
    }
    out = os.path.join(HERE, "sensitivity_selftest.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
        fh.write("\n")
    print("sensitivity self-test: %d/%d met, all_expectations_met=%s"
          % (payload["cases_met"], payload["cases_total"], all_met))
    for e in expectations:
        print("  %-22s met=%-5s got=%s%s" % (e["case"], e.get("met"), e.get("got"),
                                             "" if e.get("met") else "  <-- FAIL"))
    return 0 if all_met else 1


if __name__ == "__main__":
    sys.exit(main())
