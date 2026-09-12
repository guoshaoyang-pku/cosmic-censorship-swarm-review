#!/usr/bin/env python3
"""Verify each variant delta applies cleanly to its frozen base (paths exist, 'from' matches)."""
import hashlib, json, sys
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[3]
def get(doc, path):
    cur = doc
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur: cur = cur[part]
        else: return None
    return cur
errs = []
files = sorted((ROOT/"artifacts/formulation/variants").glob("*.delta.json"))
for f in files:
    d = json.loads(f.read_text())
    base = ROOT/d["base"]["artifact"]
    h = hashlib.sha256(base.read_bytes()).hexdigest()
    if h != d["base"]["sha256"]:
        errs.append(f"{d['variant_id']}: base hash drift ({d['base']['sha256'][:12]} -> {h[:12]})"); continue
    doc = yaml.safe_load(base.read_text())
    for ch in d["changes"]:
        cur = get(doc, ch["path"])
        if cur is None:
            errs.append(f"{d['variant_id']}: path not found {ch['path']}")
        elif str(cur) != str(ch["from"]):
            errs.append(f"{d['variant_id']}: 'from' mismatch at {ch['path']}")
        if str(ch["from"]) == str(ch["to"]):
            errs.append(f"{d['variant_id']}: no-op change at {ch['path']}")
    if not d.get("falsifier") or not d.get("evidence_refs"):
        errs.append(f"{d['variant_id']}: missing falsifier/evidence")
out = {"deltas": [f.stem for f in files], "valid": not errs, "errors": errs}
(ROOT/"artifacts/formulation/evidence/variant_delta_check.json").write_text(json.dumps(out, indent=2)+"\n")
print(("VALID" if not errs else "INVALID") + f": {len(files)} variant deltas")
for e in errs: print("  " + e)
sys.exit(0 if not errs else 1)
