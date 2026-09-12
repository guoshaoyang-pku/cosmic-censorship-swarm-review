#!/usr/bin/env python3
"""Second-pass determinism check for W084-R03V2-SCOPE-INDEP-01.

Re-executes all 88 cells into raw_pass2/ and compares verdict, failed_rules and
doc_sha256 against the first-pass raw/ JSON. No published byte is written.
"""
from __future__ import annotations
import json, os, subprocess, sys

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
TASK = os.path.join(ROOT, "artifacts/worker-084/r03v2_scope_indep")
PUB = os.path.join(ROOT, "artifacts/worker-06/r03scope")
SPEC = os.path.join(ROOT, "artifacts/formulation/rule_spec.json")
PY = "/usr/bin/python3"

pre = json.load(open(os.path.join(TASK, "PREREGISTRATION.json")))
man = json.load(open(os.path.join(PUB, "fixture_manifest.json")))
os.makedirs(os.path.join(TASK, "raw_pass2"), exist_ok=True)

cells = []
for cname, tool in pre["method"]["candidates"].items():
    for f in man["fixtures"]:
        cells.append((cname, tool, f["fixture"], os.path.join(PUB, "fixtures", f["fixture"])))
    for cp in ("schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"):
        cells.append((cname, tool, "canonical__" + os.path.basename(cp), os.path.join(ROOT, cp)))

diffs = []
for cname, tool, key, doc in cells:
    out = os.path.join(TASK, "raw_pass2", f"{cname}__{key}.json")
    pr = subprocess.run([PY, os.path.join(ROOT, tool), doc, "--spec", SPEC, "--json", out],
                        capture_output=True, text=True, timeout=60)
    p1 = json.load(open(os.path.join(TASK, "raw", f"{cname}__{key}.json")))
    p2 = json.load(open(out))
    for field in ("verdict", "failed_rules", "doc_sha256"):
        if p1.get(field) != p2.get(field):
            diffs.append({"cell": f"{cname}__{key}", "field": field, "pass1": p1.get(field), "pass2": p2.get(field)})
    if pr.returncode != 0 and p2.get("verdict") != "reject":
        diffs.append({"cell": f"{cname}__{key}", "field": "returncode_verdict_consistency", "pass2_rc": pr.returncode, "verdict": p2.get("verdict")})

res = {"cells": len(cells), "field_diffs": diffs, "deterministic": len(diffs) == 0}
json.dump(res, open(os.path.join(TASK, "determinism.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
sys.exit(0 if res["deterministic"] else 1)
