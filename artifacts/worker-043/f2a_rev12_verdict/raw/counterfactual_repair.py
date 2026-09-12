#!/usr/bin/env python3
"""Pre-registered acceptance test for the two W043C findings.

Applies exactly the two declared repairs (plus the re-freeze the repair protocol
requires) to a scratch copy and requires the checker to return accept / 0 FAIL:
  repair A (B-043-1): update consistency_evidence_sha256 in all three schemas
                      from the stale 675a99d0... to the hash of the repaired,
                      hash-bound consistency evidence.
  repair B (B-043-2): restore the two tree-hash fields in the frozen
                      consistency evidence: map_taxonomy_sha256 (F0 canonical)
                      and lead_contract_sha256 (F0 supplement).
  re-freeze:          update the FROZEN.json pins for every changed file
                      (P-043-1: the schema embedded hash is only correct after
                      the evidence file is itself repaired, i.e. A depends on B).

Read-only on the shared tree; writes only under a temp dir.
"""
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
CHECKER = ROOT / "artifacts/worker-043/f2a_rev12_verdict/check_f2a_rev12.py"

spec = importlib.util.spec_from_file_location("w043check", CHECKER)
ck = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ck)

STALE = "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"
SCHEMAS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]
MIRRORS = [
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
]
CONS = "artifacts/formulation/evidence/taxonomy_consistency.json"
FROZEN = "artifacts/formulation/FROZEN.json"
EXTRA = [
    "artifacts/formulation/tools/check_class_schema.py",
    "artifacts/formulation/rule_spec.json",
    "artifacts/formulation/KEY_MANIFEST.json",
    "artifacts/formulation/tools/check_taxonomy_consistency.py",
] + MIRRORS

scratch = Path(tempfile.mkdtemp(prefix="w043_counterfactual_"))
try:
    for rel in list(ck.TARGETS) + EXTRA:
        src = ROOT / rel
        if src.is_file():
            dst = scratch / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    # ---- repair B: evidence carries tree hashes again
    cons_path = scratch / CONS
    cons = json.loads(cons_path.read_text())
    cons["map_taxonomy_sha256"] = ck.TARGETS["research_map/formulation_taxonomy.yaml"][0]
    cons["lead_contract_sha256"] = ck.TARGETS["artifacts/formulation/formulation_taxonomy.yaml"][0]
    cons_path.write_text(json.dumps(cons, indent=2) + "\n")
    new_cons_sha = hashlib.sha256(cons_path.read_bytes()).hexdigest()

    # ---- repair A: embedded evidence hash -> repaired evidence hash
    for rel in SCHEMAS + MIRRORS:
        p = scratch / rel
        txt = p.read_text()
        assert STALE in txt, f"{rel}: stale hash not found"
        p.write_text(txt.replace(STALE, new_cons_sha))

    # ---- re-freeze: update pins of every changed file
    fz_path = scratch / FROZEN
    fz = json.loads(fz_path.read_text())
    changed = SCHEMAS + [r for r in MIRRORS if r in fz.get("files", {})] + [CONS]
    for rel in changed:
        b = (scratch / rel).read_bytes()
        if rel in fz["files"]:
            fz["files"][rel]["sha256"] = hashlib.sha256(b).hexdigest()
            fz["files"][rel]["bytes"] = len(b)
    fz["revision"] = fz.get("revision", 28) + 1
    fz["frozen_at"] = "2026-09-12T00:40:00+08:00"
    fz_path.write_text(json.dumps(fz, indent=1) + "\n")

    # ---- retarget pins to the repaired+refrozen set
    for rel in list(ck.TARGETS):
        b = (scratch / rel).read_bytes()
        ck.TARGETS[rel] = (hashlib.sha256(b).hexdigest(), len(b), ck.TARGETS[rel][2])

    res = ck.run_checks(scratch)
    fails = [c["check_id"] for c in res["checks"] if c["status"] == "FAIL"]
    out = {
        "repairs": {
            "B_evidence_hash_bound": "map_taxonomy_sha256 + lead_contract_sha256 restored",
            "A_embedded_consistency_hash": f"{STALE[:16]} -> {new_cons_sha[:16]} (3 schemas + mirrors)",
            "P_043_1_ordering": "A must follow B: the embedded hash must equal the repaired evidence hash",
            "refreeze": f"FROZEN revision {fz['revision']} pins updated for {len(changed)} changed files",
        },
        "verdict": res["verdict"],
        "score": res["score"],
        "n_fail": res["n_fail"],
        "fail_ids": fails,
        "R15": next(c["status"] for c in res["checks"] if c["check_id"] == "R15-consistency-binding"),
        "R16": next(c["status"] for c in res["checks"] if c["check_id"] == "R16-evidence-hash-bound"),
        "acceptance": "PASS" if res["verdict"] == "accept" and res["n_fail"] == 0 else "FAIL",
    }
    print(json.dumps(out, indent=1))
finally:
    shutil.rmtree(scratch, ignore_errors=True)
