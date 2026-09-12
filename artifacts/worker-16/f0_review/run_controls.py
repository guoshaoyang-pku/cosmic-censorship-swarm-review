#!/usr/bin/env python3
"""Controls for the F0 review checker (worker-16).

Two controls, both required before the three FAIL checks are believed:

  P1 positive sensitivity: take the pinned taxonomy, repair exactly the three
     defects the checker reports (D1 set-based residue, missing comeager binding,
     legacy schema_owner pointers) and re-run the checker on the patched fixture.
     Requirement: 0 FAIL checks on the fixture. If the checker still fails, it is
     over-firing and the review's FAILs are not attributable to the defects.

  N1 negative drift: run the checker against the pinned taxonomy with a wrong
     --pin. Requirement: exit code 2 and no results file written (fail-closed).

Writes artifacts/worker-16/f0_review/controls.json and exits non-zero if either
control does not behave as specified.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TAX = "research_map/formulation_taxonomy.yaml"
PINNED = "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc"
FIXTURE = os.path.join(HERE, "control_fixture_repaired.yaml")
FIXTURE_RESULTS = os.path.join(HERE, "control_fixture_results.json")
DRIFT_RESULTS = os.path.join(HERE, "control_drift_results.json")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def patch(text: str) -> str:
    # B-16F0-1: replace the demoted set-based reading in the scalar class conclusion
    old = ("every future-inextendible causal\n        geodesic contained in J-(I+) is complete; equivalently, the singularities "
           "that form are\n        hidden behind an event horizon and no singularity is visible from I+.")
    new = ("for every admissible (s,delta) there is a comeager set G_{s,delta} of data such that for every\n"
           "        data set in G_{s,delta}, every future-inextendible causal geodesic of finite affine length visible\n"
           "        from I+ under the single-q TAIL predicate (the same predicate as AF-WCC-VAC-GEN) is complete.")
    assert old in text, "control patch anchor 1 not found"
    text = text.replace(old, new)
    # B-16F0-3: repoint the two legacy schema_owner pointers
    text = text.replace("F2 (artifact schemas/af_scc_regularities.yaml, section C2)",
                        "F2a (artifact schemas/af_scc_c2_vacuum.yaml)")
    text = text.replace("F2 (artifact schemas/af_scc_regularities.yaml, section C0)",
                        "F2b (artifact schemas/af_scc_c0_vacuum.yaml)")
    return text


def main() -> int:
    measured = sha256_file(TAX)
    assert measured == PINNED, f"source taxonomy drifted: {measured}"

    with open(TAX) as f:
        fixed = patch(f.read())
    with open(FIXTURE, "w") as f:
        f.write(fixed)
    fixture_sha = sha256_file(FIXTURE)

    p1 = subprocess.run(
        [sys.executable, os.path.join(HERE, "check_f0.py"),
         "--tax", FIXTURE, "--pin", fixture_sha, "--out", FIXTURE_RESULTS],
        capture_output=True, text=True)
    fixture = json.load(open(FIXTURE_RESULTS)) if os.path.exists(FIXTURE_RESULTS) else {}
    p1_ok = p1.returncode == 0 and fixture.get("summary", {}).get("fail") == 0

    if os.path.exists(DRIFT_RESULTS):
        os.remove(DRIFT_RESULTS)
    n1 = subprocess.run(
        [sys.executable, os.path.join(HERE, "check_f0.py"),
         "--pin", "0" * 64, "--out", DRIFT_RESULTS],
        capture_output=True, text=True)
    n1_ok = n1.returncode == 2 and not os.path.exists(DRIFT_RESULTS)

    out = {
        "source_taxonomy": TAX,
        "source_sha256": measured,
        "P1_positive_sensitivity": {
            "requirement": "repaired fixture yields 0 FAIL checks (exit 0)",
            "fixture": FIXTURE,
            "fixture_sha256": fixture_sha,
            "exit_code": p1.returncode,
            "summary": fixture.get("summary"),
            "remaining_failures": [c["id"] for c in fixture.get("checks", []) if c["status"] == "FAIL"],
            "result": "PASS" if p1_ok else "FAIL",
        },
        "N1_negative_drift_fail_closed": {
            "requirement": "wrong --pin exits 2 and writes no results file",
            "exit_code": n1.returncode,
            "stderr": n1.stderr.strip(),
            "results_file_written": os.path.exists(DRIFT_RESULTS),
            "result": "PASS" if n1_ok else "FAIL",
        },
    }
    out["result"] = "PASS" if (p1_ok and n1_ok) else "FAIL"
    with open(os.path.join(HERE, "controls.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1)[:2000])
    return 0 if out["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
