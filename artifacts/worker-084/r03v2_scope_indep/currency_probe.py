#!/usr/bin/env python3
"""POST-HOC currency probe for W084-R03V2-SCOPE-INDEP-01.

Not part of the pre-registered 88-cell reproduction. Between the adjudicated run
and event emission the live C2/C0 canonical schemas were replaced (rev14 write at
2026-09-12T01:25:42). This probe re-runs the four candidates on the NEW live
C2/C0 bytes so the adjudication can state whether cand_r03v2 still accepts the
current canonicals, or whether a same-revision re-validation is required.
Outputs go to currency/, result to currency_check.json. No byte is written to
the subject or to any canonical path.
"""
from __future__ import annotations
import datetime, hashlib, json, os, subprocess, sys

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
TASK = os.path.join(ROOT, "artifacts/worker-084/r03v2_scope_indep")
SPEC = os.path.join(ROOT, "artifacts/formulation/rule_spec.json")
PY = "/usr/bin/python3"
os.makedirs(os.path.join(TASK, "currency"), exist_ok=True)

pre = json.load(open(os.path.join(TASK, "PREREGISTRATION.json")))
docs = {
    "live_c2_c1013e48": "schemas/af_scc_c2_vacuum.yaml",
    "live_c0_c4d17fe6": "schemas/af_scc_c0_vacuum.yaml",
    "live_wcc_d9cebb94": "schemas/af_wcc_vacuum.yaml",
}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


res = {"probe": "post-hoc currency check (not pre-registered)", "created_at": datetime.datetime.now().astimezone().replace(microsecond=0).isoformat(),
       "reason": "live C2/C0 canonical schemas were replaced by the rev14 write at 2026-09-12T01:25:42 after the adjudicated 88-cell run; R03-relevant quantifiers.formal is unchanged but the full documents moved",
       "frozen_manifest_at_probe": {"path": "artifacts/formulation/FROZEN.json", "sha256": sha(os.path.join(ROOT, "artifacts/formulation/FROZEN.json")), "revision": json.load(open(os.path.join(ROOT, "artifacts/formulation/FROZEN.json")))["revision"]},
       "docs": {}, "cells": {}}
for k, rel in docs.items():
    res["docs"][k] = {"path": rel, "sha256": sha(os.path.join(ROOT, rel)), "mtime": datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(ROOT, rel))).astimezone().replace(microsecond=0).isoformat()}
for cname, tool in pre["method"]["candidates"].items():
    res["cells"][cname] = {}
    for k, rel in docs.items():
        out = os.path.join(TASK, "currency", f"{cname}__{k}.json")
        pr = subprocess.run([PY, os.path.join(ROOT, tool), os.path.join(ROOT, rel), "--spec", SPEC, "--json", out],
                            capture_output=True, text=True, timeout=60)
        d = json.load(open(out))
        res["cells"][cname][k] = {"returncode": pr.returncode, "verdict": d.get("verdict"), "failed_rules": d.get("failed_rules", []),
                                  "failed_detail": {c.get("rule"): c.get("detail") for c in d.get("checks", []) if c.get("verdict") == "fail"}}
json.dump(res, open(os.path.join(TASK, "currency_check.json"), "w"), indent=1, sort_keys=True)
print(json.dumps({c: {k: v["verdict"] + (":" + ",".join(v["failed_rules"]) if v["failed_rules"] else "") for k, v in cells.items()} for c, cells in res["cells"].items()}, indent=1))
