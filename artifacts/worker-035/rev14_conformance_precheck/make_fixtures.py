#!/usr/bin/env python3
"""Labeled fixture generator + control harness for precheck.py (W035-REV14-CONFORMANCE-PRECHECK-01).

Every fixture is a copy under fixtures/ derived from the pinned rev13 snapshot. No canonical
path is written. Each mutation targets exactly one check; the harness runs precheck.py on every
fixture and compares the observed status vector with the pre-registered expectation below.
A mismatch falsifies the instrument, not the artifact.

Run:  python3 make_fixtures.py
Out:  fixtures/*.yaml, fixtures/expected.json, controls.json
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(HERE, "snapshot")
FIX = os.path.join(HERE, "fixtures")
C0_SNAP = os.path.join(SNAP, "af_scc_c0_vacuum.b2ab6acb.yaml")
C2_SNAP = os.path.join(SNAP, "af_scc_c2_vacuum.e9a27996.yaml")
C2_CANON = os.path.abspath(os.path.join(HERE, "..", "..", "..", "schemas", "af_scc_c2_vacuum.yaml"))

CHECKS = ["P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08", "P09", "P10", "P11"]
BASE = {
    "P01": "PASS", "P02": "PASS", "P03": "PASS", "P04": "FAIL", "P05": "FAIL",
    "P06": "FAIL", "P07": "OBS", "P08": "FAIL", "P09": "PASS", "P10": "OBS", "P11": "OBS",
}

D1_DENIAL = "No containment with C2 or C0 is asserted here; the informal phrase 'strictly between' is not used and must not be cited (worker-16 F2b-16-02 accepted)."
D1_FIX = ("Containment with C2 and C0 follows the ledger chain E_C0 contains E_H2loc contains "
          "E_{C^1,1} contains E_C2; the informal phrase 'strictly between' is not used and must not be cited.")


def dump(doc, path):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, sort_keys=False, allow_unicode=True, width=1000)


def load(p):
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def fix_d1(doc):
    lst = doc["regularity"]["must_not_conflate"]
    for i, e in enumerate(lst):
        if "No containment with C2 or C0" in e:
            lst[i] = D1_FIX
            return True
    return False


def fix_d2(doc):
    row = doc["implication_ledger"]["forbidden_transfers"][0]
    row["reason"] = ("C2 is a strictly smaller extension class, so C2-inextendibility is strictly "
                     "stronger and is entailed by this class's conclusion, not vice versa")
    return True


def main():
    os.makedirs(FIX, exist_ok=True)
    base = load(C0_SNAP)
    c2 = load(C2_SNAP)
    fixtures = []

    # F0 baseline: byte copy of the pinned snapshot
    with open(C0_SNAP, "rb") as f:
        raw = f.read()
    with open(os.path.join(FIX, "F0_baseline.yaml"), "wb") as f:
        f.write(raw)
    fixtures.append(("F0_baseline", "F0_baseline.yaml", C2_CANON, dict(BASE)))

    d = copy.deepcopy(base)
    assert fix_d1(d)
    dump(d, os.path.join(FIX, "F1_d1_denial_removed.yaml"))
    fixtures.append(("F1_d1_denial_removed", "F1_d1_denial_removed.yaml", C2_CANON, {**BASE, "P04": "PASS"}))

    d = copy.deepcopy(base)
    fix_d2(d)
    dump(d, os.path.join(FIX, "F2_d2_inversion_fixed.yaml"))
    fixtures.append(("F2_d2_inversion_fixed", "F2_d2_inversion_fixed.yaml", C2_CANON, {**BASE, "P05": "PASS"}))

    d = copy.deepcopy(base)
    fix_d1(d)
    fix_d2(d)
    dump(d, os.path.join(FIX, "F3_both_fixed.yaml"))
    fixtures.append(("F3_both_fixed", "F3_both_fixed.yaml", C2_CANON, {**BASE, "P04": "PASS", "P05": "PASS"}))

    d = copy.deepcopy(base)
    h = d["f0_binding"]["declared_f0_sha256"]
    d["f0_binding"]["declared_f0_sha256"] = h[:-1] + ("0" if h[-1] != "0" else "1")
    dump(d, os.path.join(FIX, "F4_chain_corrupt.yaml"))
    # corrupting the declared F0 hash is also a refresh-rule violation by construction (P03)
    fixtures.append(("F4_chain_corrupt", "F4_chain_corrupt.yaml", C2_CANON,
                     {**BASE, "P02": "FAIL", "P03": "FAIL"}))

    d = copy.deepcopy(base)
    d["class_components"]["regularity_token"] = "C2"
    dump(d, os.path.join(FIX, "F5_identity_leak.yaml"))
    fixtures.append(("F5_identity_leak", "F5_identity_leak.yaml", C2_CANON, {**BASE, "P01": "FAIL"}))

    # F6: clean C0 paired with a C2 sibling whose chain order is flipped
    c2m = copy.deepcopy(c2)
    c2m["implication_ledger"]["extension_class_containment"] = (
        "E_C0 subset of E_{C^1,1} subset of E_H2loc subset of E_C2 (control mutation: ordering flipped)"
    )
    dump(c2m, os.path.join(FIX, "F6_c2_mutated.yaml"))
    fixtures.append(("F6_crossfile_flip", "F0_baseline.yaml", os.path.join(FIX, "F6_c2_mutated.yaml"),
                     {**BASE, "P09": "FAIL"}))

    d = copy.deepcopy(base)
    fix_d1(d)
    fix_d2(d)
    for r in d["revision_history"]:
        if r.get("index") == 9:
            r["at"] = "2026-09-12T00:30:30+08:00"
            r["notes"] = []
    d["revision_history"].append({
        "index": 12, "at": "2026-09-12T00:54:00+08:00", "unused": False,
        "notes": ["control positive: names the live declared-F0 0abb9ed8a961"],
    })
    dump(d, os.path.join(FIX, "F7_revhist_fix.yaml"))
    fixtures.append(("F7_revhist_fix", "F7_revhist_fix.yaml", C2_CANON,
                     {**BASE, "P04": "PASS", "P05": "PASS", "P06": "PASS"}))

    expected = {name: {cid: exp[cid] for cid in CHECKS} for name, _, _, exp in fixtures}
    with open(os.path.join(FIX, "expected.json"), "w", encoding="utf-8") as f:
        json.dump({"instrument": "W035-REV14-CONFORMANCE-PRECHECK-01", "checks": CHECKS,
                   "expectations": expected}, f, indent=1)

    # control harness
    results, all_ok = [], True
    for name, file, c2p, exp in fixtures:
        out = os.path.join(FIX, f"{name}.report.json")
        p = subprocess.run(
            [sys.executable, os.path.join(HERE, "precheck.py"), "--file", os.path.join(FIX, file),
             "--c2", c2p, "--out", out],
            capture_output=True, text=True,
        )
        rep = json.load(open(out))
        obs = {c["id"]: c["status"] for c in rep["checks"]}
        mism = [f"{c}: expected {exp[c]} observed {obs.get(c)}" for c in CHECKS if obs.get(c) != exp[c]]
        all_ok = all_ok and not mism
        results.append({
            "fixture": name, "file": file, "c2": os.path.relpath(c2p, HERE),
            "report": os.path.relpath(out, HERE), "exit_code": p.returncode,
            "expected": {c: exp[c] for c in CHECKS},
            "observed": {c: obs.get(c) for c in CHECKS},
            "mismatches": mism, "match": not mism,
        })

    controls = {
        "instrument": "W035-REV14-CONFORMANCE-PRECHECK-01",
        "fixture_count": len(fixtures),
        "all_match": all_ok,
        "results": results,
        "self_falsifier": "any result row with match=false falsifies precheck.py or the fixture, not the artifact",
        "note": "fixtures are non-canonical copies; no canonical path was written by this harness",
    }
    with open(os.path.join(HERE, "controls.json"), "w", encoding="utf-8") as f:
        json.dump(controls, f, indent=1)
    print(json.dumps({"fixtures": len(fixtures), "all_match": all_ok,
                      "mismatches": [(r["fixture"], r["mismatches"]) for r in results if not r["match"]]}, indent=1))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
