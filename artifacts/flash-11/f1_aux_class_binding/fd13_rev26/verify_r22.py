#!/usr/bin/env python3
"""Deterministic reproduction of the frozen-rev27 R22 rejection, offline.

The live KEY_MANIFEST moved while FD-13 was being rebased (fce91948 -> 014e2d30), so the
transient head state is re-created here from preserved bytes:

  env A: canonical tool 000e09e4 + rule_spec 40f9bb9e + KEY_MANIFEST fce91948 (rev26/27)
  env B: canonical tool 000e09e4 + rule_spec 40f9bb9e + KEY_MANIFEST 014e2d30 (post-move)

against the FROZEN rev27 / schema-rev12 byte copies in diskhead_canonical/ (cce9c601,
5476a3f2, 55d0a1ea). Writes rev27_r22_repro.json. Read-only w.r.t. the shared tree.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BIND = HERE.parent
REPO = BIND.parents[2]

CANON_BASE = REPO / "artifacts/formulation/tools/check_class_schema.py"
RULE_SPEC = REPO / "artifacts/formulation/rule_spec.json"
KM_OLD = HERE / "patched/KEY_MANIFEST.json"            # copied when it was fce91948
KM_NEW = HERE / "key_manifest_014e2d30.json"           # snapshot taken after the move
SCHEMA_DIR = HERE / "diskhead_canonical"

EXPECT = {
    CANON_BASE: "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    RULE_SPEC: "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    KM_OLD: "fce91948ba3a59a5bd34c8bcb03202ee479a95dbc3e4d6c327a0c4d1a9170d33",
    KM_NEW: "014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a",
    SCHEMA_DIR / "canonical_af_wcc_vacuum.yaml":
        "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    SCHEMA_DIR / "canonical_af_scc_c2_vacuum.yaml":
        "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    SCHEMA_DIR / "canonical_af_scc_c0_vacuum.yaml":
        "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


problems = [f"{p}: {sha256_file(p) if p.exists() else 'MISSING'} != {want}"
            for p, want in EXPECT.items() if not p.exists() or sha256_file(p) != want]
if problems:
    raise SystemExit("BINDING ABORT: " + "; ".join(problems))


def make_env(name: str, km: Path) -> Path:
    env = HERE / f"rev27_env_{name}"
    (env / "tools").mkdir(parents=True, exist_ok=True)
    (env / "tools/check_class_schema.py").write_bytes(CANON_BASE.read_bytes())
    (env / "rule_spec.json").write_bytes(RULE_SPEC.read_bytes())
    (env / "KEY_MANIFEST.json").write_bytes(km.read_bytes())
    return env


def run(env: Path, fixture: Path) -> dict:
    proc = subprocess.run([sys.executable, str(env / "tools/check_class_schema.py"),
                           str(fixture), "--json"],
                          cwd=env / "tools", capture_output=True, text=True, timeout=90)
    try:
        payload = json.loads(proc.stdout.strip())
    except json.JSONDecodeError:
        return {"verdict": "crash", "rule_ids": [], "failures": [],
                "detail": (proc.stderr.strip().splitlines() or [""])[-1][:160]}
    return {"verdict": "accept" if payload.get("verdict") == "pass" else "reject",
            "rule_ids": payload.get("failed_rules", []),
            "failures": payload.get("failures", payload.get("failed_checks", []))}


out: dict = {
    "artifact": "Frozen-rev27 R22 rejection, deterministic offline reproduction (unverified)",
    "task_id": "FORM-DIFF-02",
    "node_id": "F1",
    "gate": "G-CLASSBIND",
    "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "why": ("the live KEY_MANIFEST moved (fce91948 -> 014e2d30) during the FD-13 rev27 rebase, so "
            "the head state could not be re-measured in place; preserved bytes make it reproducible"),
    "binding": {(str(p.relative_to(REPO)) if p.is_relative_to(REPO) else str(p)): sha256_file(p)
                for p in EXPECT},
    "envs": [],
}
for name, km in (("km_fce91948", KM_OLD), ("km_014e2d30", KM_NEW)):
    env = make_env(name, km)
    rows = []
    for fx in sorted(SCHEMA_DIR.glob("canonical_*.yaml")):
        rows.append({"fixture": fx.name, "sha256": sha256_file(fx), **run(env, fx)})
    out["envs"].append({"env": name, "key_manifest_sha256": sha256_file(km), "rows": rows})

old, new = out["envs"]
out["interpretation"] = {
    "with_fce91948": ("ALL three FROZEN rev27 schemas are rejected at R22: the frozen revision's "
                      "gate does not accept its own schemas -> FD-13 is MASKED at this state"),
    "with_014e2d30": ("all three accepted" if all(r["verdict"] == "accept" for r in new["rows"])
                      else "still rejected: " + json.dumps({r["fixture"]: r["rule_ids"] for r in new["rows"]})),
    "note": "offline reproduction only; the live head may have moved again - re-measure before citing",
}
(HERE / "rev27_r22_repro.json").write_text(json.dumps(out, indent=1, sort_keys=True))
for e in out["envs"]:
    print(e["env"], e["key_manifest_sha256"][:12],
          [(r["fixture"].replace("canonical_", "").replace(".yaml", ""), r["verdict"], r["rule_ids"])
           for r in e["rows"]])
print("interpretation:", json.dumps(out["interpretation"], indent=1)[:600])
