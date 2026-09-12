#!/usr/bin/env python3
"""W058-REPAIR-CERT-02 sensitivity self-test.

Pre-registered mutants live in `_scratch/<case>/schemas/` (copies of the canonical
SCC pair with string surgery). Each case asserts an outcome BEFORE the checker runs;
the harness records expectation vs observation and `all_expectations_met`.

Run:  python3 artifacts/worker-058/repair_cert/run_sensitivity_selftest.py --root .
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, "sweep_scc_order.py")
C0 = "schemas/af_scc_c0_vacuum.yaml"
C2 = "schemas/af_scc_c2_vacuum.yaml"

HF_SIZE = "class_size_predicate_inverted"
HF_STRENGTH = "strength_predicate_inverted"
HF_BUCKET = "strength_bucket_mismatch"
HF_CHAIN = "chain_concordance_failure"

WEAK_ITEM = '    - "replacing future by two-sided direction"\n'
BUCKET_ANCHOR = '    - "two-sided inextendibility (different, stronger statement)"\n'
PLANT = ('    - {class_id: AF-SCC-C0-VAC-GEN, why: "C2 is a strictly larger extension '
         'class, so C2-inextendibility is strictly stronger"}\n')


def mutate_c0(text: str, case: str) -> str:
    if case == "M1_repair_both":
        text = text.replace(
            '"C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"',
            '"C2 is a strictly smaller extension class, so C2-inextendibility is strictly weaker"')
        assert text.count(WEAK_ITEM) == 1 and text.count(BUCKET_ANCHOR) == 1
        text = text.replace(WEAK_ITEM, "")
        text = text.replace(BUCKET_ANCHOR, BUCKET_ANCHOR + WEAK_ITEM)
    elif case == "M2_plant_anti_scope_inversion":
        anchor = "anti_scope:\n  not_this_class:\n"
        assert text.count(anchor) == 1
        text = text.replace(anchor, anchor + PLANT)
    elif case == "M3_plant_variant_strength_inversion":
        old = 'relation: "strictly WEAKER than this frozen class:'
        assert text.count(old) == 1
        text = text.replace(old, 'relation: "strictly STRONGER than this frozen class:')
    elif case == "M4_truncate_c0_chain":
        old = "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2"
        assert text.count(old) >= 1
        text = text.replace(old, "E_C0 contains E_C2")
    return text


def mutate_c2(text: str, case: str) -> str:
    if case == "M6_plant_c2_bucket_mismatch":
        anchor = "  forbidden_weakenings:\n"
        assert text.count(anchor) == 1
        text = text.replace(anchor, anchor + WEAK_ITEM)
    return text


CASES = [
    {"case": "M0_canonical", "c0": None, "c2": None,
     "expect_verdict": "FAIL", "expect_located": [(HF_SIZE, "C0", "forbidden_transfers"),
                                                   (HF_BUCKET, "C0", "forbidden_weakenings")],
     "expect": "known C0 hard failure + R2-10 labelling item both visible"},
    {"case": "M1_repair_both", "c0": "M1_repair_both", "c2": None,
     "expect_verdict": "PASS", "expect_located": [], "expect_zero_hard": True,
     "expect": "applying the two proposed repairs yields PASS with zero hard findings"},
    {"case": "M2_plant_anti_scope_inversion", "c0": "M2_plant_anti_scope_inversion", "c2": None,
     "expect_verdict": "FAIL",
     "expect_located": [(HF_SIZE, "C0", "anti_scope"), (HF_STRENGTH, "C0", "anti_scope")],
     "expect": "an inversion planted outside implication_ledger is caught where planted"},
    {"case": "M3_plant_variant_strength_inversion", "c0": "M3_plant_variant_strength_inversion",
     "c2": None, "expect_verdict": "FAIL",
     "expect_located": [(HF_STRENGTH, "C0", "class_identity_variants")],
     "expect": "a variant strength inversion in class_identity_variants is caught where planted"},
    {"case": "M4_truncate_c0_chain", "c0": "M4_truncate_c0_chain", "c2": None,
     "expect_verdict": "FAIL", "expect_located": [(HF_CHAIN, "C0+C2", "")],
     "expect": "a C0 chain that disagrees with C2 fails concordance"},
    {"case": "M5_byte_identical_copy", "c0": None, "c2": None,
     "expect_verdict": "FAIL", "expect_located": [], "expect_identical_to_m0": True,
     "expect": "identical bytes give the identical verdict to M0"},
    {"case": "M6_plant_c2_bucket_mismatch", "c0": None, "c2": "M6_plant_c2_bucket_mismatch",
     "expect_verdict": "FAIL", "expect_located": [(HF_BUCKET, "C2", "forbidden_weakenings")],
     "expect": "a two-sided item planted in C2's weakening bucket is caught"},
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default=os.path.join(HERE, "sensitivity_selftest.json"))
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    scratch = os.path.join(HERE, "_scratch")
    if os.path.isdir(scratch):
        shutil.rmtree(scratch)
    os.makedirs(scratch)

    c0_raw = open(os.path.join(root, C0), encoding="utf-8").read()
    c2_raw = open(os.path.join(root, C2), encoding="utf-8").read()
    canonical = {"sha256": {C0: sha256(os.path.join(root, C0)), C2: sha256(os.path.join(root, C2))}}

    results = []
    m0_codes = None
    ok_all = True
    for case in CASES:
        cdir = os.path.join(scratch, case["case"], "schemas")
        os.makedirs(cdir)
        c0_text = mutate_c0(c0_raw, case["c0"]) if case["c0"] else c0_raw
        c2_text = mutate_c2(c2_raw, case["c2"]) if case["c2"] else c2_raw
        open(os.path.join(cdir, os.path.basename(C0)), "w", encoding="utf-8").write(c0_text)
        open(os.path.join(cdir, os.path.basename(C2)), "w", encoding="utf-8").write(c2_text)
        out = os.path.join(scratch, case["case"], "result.json")
        proc = subprocess.run(
            [sys.executable, CHECKER, "--root", os.path.join(scratch, case["case"]),
             "--mutant", "--out", out],
            capture_output=True, text=True)
        obs = json.load(open(out))
        hard = obs["hard_findings"]
        codes = sorted({f["code"] for f in hard})
        located = []
        for f in hard:
            located.append({"code": f["code"], "file": f.get("file"),
                            "yaml_path": f.get("yaml_path", "")})
        if case["case"] == "M0_canonical":
            m0_codes, m0_counts = codes, obs["counts"]
        located_ok = all(
            any(l["code"] == code and sub in (l["file"] or "")
                and ysub in (l["yaml_path"] or "")
                for l in located)
            for code, sub, ysub in case["expect_located"])
        if case.get("expect_zero_hard"):
            passed = obs["verdict"] == "PASS" and not hard
        elif case.get("expect_identical_to_m0"):
            passed = (codes == (m0_codes or []) and obs["counts"] == m0_counts)
        else:
            passed = obs["verdict"] == case["expect_verdict"] and located_ok
        ok_all = ok_all and passed
        results.append({
            "case": case["case"], "expectation": case["expect"],
            "expected_verdict": case["expect_verdict"],
            "observed_verdict": obs["verdict"],
            "observed_hard_codes": codes,
            "observed_located": located,
            "observed_counts": obs["counts"],
            "passed": passed,
        })
    payload = {
        "artifact": "W058-REPAIR-CERT-02 sensitivity self-test",
        "worker": "worker-058",
        "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "checker": os.path.relpath(CHECKER, root),
        "checker_sha256": sha256(CHECKER),
        "canonical_inputs": canonical,
        "mutant_root": os.path.relpath(scratch, root),
        "pre_registration": "expectations set before the checker was run; no expectation edited afterwards",
        "cases": results,
        "all_expectations_met": bool(ok_all),
        "falsifier": ("any case whose observed verdict/codes differ from the pre-registered "
                      "expectation falsifies the checker's calibration claim"),
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, indent=1) + "\n")
    print("all_expectations_met=%s cases=%d" % (payload["all_expectations_met"], len(results)))
    for r in results:
        print("  %-34s %-4s -> %-4s %s" % (r["case"], r["expected_verdict"],
                                           r["observed_verdict"], r["observed_hard_codes"]))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
