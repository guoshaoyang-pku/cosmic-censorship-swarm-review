#!/usr/bin/env python3
"""W041-F2A-PIN-RCA-01 — controlled experiment on the F2a consistency-evidence pin.

Question: is `f0_binding.consistency_evidence_sha256` (declared 675a99d0... in
schemas/af_scc_c2_vacuum.yaml @ 5476a3f2c6bc) a stable pin, and if not, why?

The live path artifacts/formulation/evidence/taxonomy_consistency.json is owned by
lead-formulation, so this script NEVER writes it.  Everything runs in ./sim/.

Pre-registered predictions (fixed before execution):
  P1 determinism   : two runs on identical inputs -> byte-identical output,
                     sha256 == measured live 9e335e9b.
  P2 sensitivity   : mutating one checkable contract field changes the output
                     (positive control; output is not a constant).
  P3 non-reproduc. : declared 675a99d0 is NOT the output of the current inputs.
  P4 rewrite-on-run: each invocation rewrites the output path (source lines 79-80),
                     demonstrated in the sandbox by mtime advance, hash unchanged.

Falsifier for the diagnosis: any of P1 false (nondeterministic), or P3 false
(declared pin reproducible from current inputs) kills the "derived-output pin is
stale-by-construction" claim.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
HERE = f"{ROOT}/artifacts/worker-041/f2a_pin_rca"
SIM = f"{HERE}/sim"
TZ = timezone(timedelta(hours=8))
LIVE_EVID = f"{ROOT}/artifacts/formulation/evidence/taxonomy_consistency.json"
DECLARED = "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for c in iter(lambda: fh.read(65536), b""):
            h.update(c)
    return h.hexdigest()


def build_sandbox(name):
    """Mirror the minimal tree so parents[3] resolves to the sandbox root."""
    s = f"{SIM}/{name}"
    if os.path.exists(s):
        shutil.rmtree(s)
    os.makedirs(f"{s}/artifacts/formulation/tools", exist_ok=True)
    os.makedirs(f"{s}/artifacts/formulation/evidence", exist_ok=True)
    os.makedirs(f"{s}/research_map", exist_ok=True)
    shutil.copy(f"{ROOT}/artifacts/formulation/tools/check_taxonomy_consistency.py",
                f"{s}/artifacts/formulation/tools/check_taxonomy_consistency.py")
    shutil.copy(f"{ROOT}/artifacts/formulation/VOCAB_ALIASES.json",
                f"{s}/artifacts/formulation/VOCAB_ALIASES.json")
    shutil.copy(f"{ROOT}/research_map/formulation_taxonomy.yaml",
                f"{s}/research_map/formulation_taxonomy.yaml")
    shutil.copy(f"{ROOT}/artifacts/formulation/formulation_taxonomy.yaml",
                f"{s}/artifacts/formulation/formulation_taxonomy.yaml")
    return s


def run(s):
    r = subprocess.run(
        [sys.executable, f"{s}/artifacts/formulation/tools/check_taxonomy_consistency.py"],
        capture_output=True, text=True,
    )
    out = f"{s}/artifacts/formulation/evidence/taxonomy_consistency.json"
    return r.returncode, r.stdout.strip(), r.stderr.strip(), out


def mutate_conclusion_type(s):
    """Positive control: change one contract conclusion_type token."""
    p = f"{s}/artifacts/formulation/formulation_taxonomy.yaml"
    txt = open(p).read()
    old = "scc_c2_future_inextendibility"
    assert old in txt, "mutation anchor not found"
    open(p, "w").write(txt.replace(old, "scc_c2_future_inextendibility_MUTATED", 1))
    return old


def main():
    now = datetime.now(TZ)
    live_hash = sha256(LIVE_EVID)
    res = {"task_id": "W041-F2A-PIN-RCA-01", "reviewer": "worker-041",
           "class_id": "AF-SCC-C2-VAC-GEN", "node_id": "F2a",
           "measured_at": now.isoformat(), "live_evidence_sha256": live_hash,
           "declared_pin_in_schema": DECLARED,
           "live_inputs": {
               "research_map/formulation_taxonomy.yaml": sha256(f"{ROOT}/research_map/formulation_taxonomy.yaml"),
               "artifacts/formulation/formulation_taxonomy.yaml": sha256(f"{ROOT}/artifacts/formulation/formulation_taxonomy.yaml"),
               "artifacts/formulation/VOCAB_ALIASES.json": sha256(f"{ROOT}/artifacts/formulation/VOCAB_ALIASES.json"),
               "artifacts/formulation/tools/check_taxonomy_consistency.py": sha256(f"{ROOT}/artifacts/formulation/tools/check_taxonomy_consistency.py"),
           }, "experiments": {}}

    # P1 + P4: two runs, identical inputs
    s = build_sandbox("p1_determinism")
    rc1, so1, se1, out = run(s)
    h1 = sha256(out)
    m1 = os.path.getmtime(out)
    rc2, so2, se2, out2 = run(s)
    h2 = sha256(out2)
    m2 = os.path.getmtime(out2)
    res["experiments"]["P1_P4_determinism_and_rewrite"] = {
        "run1": {"exit": rc1, "stdout": so1, "sha256": h1, "mtime": m1},
        "run2": {"exit": rc2, "stdout": so2, "sha256": h2, "mtime": m2},
        "byte_identical": h1 == h2,
        "rewritten_on_run": m2 > m1,
        "reproduces_live_hash": h1 == live_hash,
        "sandbox_output": json.load(open(out)),
    }

    # P2: sensitivity positive control
    s2 = build_sandbox("p2_sensitivity")
    anchor = mutate_conclusion_type(s2)
    rc3, so3, se3, out3 = run(s2)
    h3 = sha256(out3)
    res["experiments"]["P2_sensitivity"] = {
        "mutation": f"conclusion_type {anchor} -> {anchor}_MUTATED",
        "exit": rc3, "stdout": so3, "sha256": h3,
        "hash_changed": h3 != live_hash,
        "output_changed": h3 != h1,
    }

    # P3: declared pin reproducible?
    res["experiments"]["P3_declared_pin_reproducible"] = {
        "declared": DECLARED,
        "reproduced_by_current_inputs": DECLARED in (h1, h2, h3),
        "current_output_sha256": h1,
    }

    res["conclusion"] = {
        "evidence_is_deterministic_function_of_inputs": h1 == h2,
        "evidence_is_input_sensitive": h3 != h1,
        "declared_pin_matches_current_output": DECLARED == live_hash,
        "current_correct_pin_value": live_hash,
        "mechanism": ("check_taxonomy_consistency.py:79-80 rewrites "
                      "artifacts/formulation/evidence/taxonomy_consistency.json on every run; "
                      "the output is a pure function of the two taxonomy trees, VOCAB_ALIASES.json "
                      "and the checker bytes, so any taxonomy edit moves the evidence hash and "
                      "stales every schema pin that names it"),
        "re_stamp_is_a_fixpoint_until_next_taxonomy_edit": True,
    }
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
