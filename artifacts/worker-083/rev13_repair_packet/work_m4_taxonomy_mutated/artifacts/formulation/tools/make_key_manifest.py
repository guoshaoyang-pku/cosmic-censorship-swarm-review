#!/usr/bin/env python3
"""Generate the canonical key allowlist from the frozen schemas (defends R22).
Any key not present here is an unknown-key rejection unless placed under `extensions:`."""
import json, yaml
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
FILES = ["artifacts/formulation/schemas/af_wcc_vacuum.yaml",
         "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
         "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"]
keys = set()
def walk(n):
    if isinstance(n, dict):
        for k, v in n.items():
            keys.add(str(k)); walk(v)
    elif isinstance(n, list):
        for v in n: walk(v)
for f in FILES:
    walk(yaml.safe_load((ROOT/f).read_text()))
out = {"generated_from": FILES, "rule": "R22", "allowed_keys": sorted(keys),
       "escape_hatch": "place deliberately new fields under a top-level `extensions:` mapping; its subtree is exempt",
       "caveat": "flat allowlist, not path-sensitive: a key is allowed anywhere if it appears somewhere in the frozen set"}
(ROOT/"artifacts/formulation/KEY_MANIFEST.json").write_text(json.dumps(out, indent=2)+"\n")
print(f"manifest: {len(keys)} keys")
