#!/usr/bin/env python3
"""Pin schemas/taxonomy_cases.jsonl to the CURRENT content hash of the taxonomy.

Why this exists: during the run the taxonomy changed content twice, once without a revision
bump (revision stayed at 2, sha moved 347c924b -> dac2853c). A revision number is therefore
NOT a binding identity; the sha256 is. This script is idempotent and is re-run at every
checkpoint when the taxonomy hash moves.

It updates:
  - the meta record's taxonomy_ref {revision, sha256}
  - every case's binding_status -> bound_taxonomy_sha_<12 hex>
and reports whether it changed anything. It never edits axis vectors: if the axis vocabulary
itself changes, check_taxonomy_cases.py must fail and the cases must be re-authored, not patched.
"""
import hashlib
import json
from pathlib import Path

import yaml

TAX = Path("research_map/formulation_taxonomy.yaml")
CASES = Path("schemas/taxonomy_cases.jsonl")

sha = hashlib.sha256(TAX.read_bytes()).hexdigest()
rev = yaml.safe_load(TAX.read_text()).get("revision")
lines = [l for l in CASES.read_text().splitlines() if l.strip()]
out, changed = [], 0
for line in lines:
    c = json.loads(line)
    if c.get("record_type") == "meta":
        ref = c.get("taxonomy_ref", {})
        if ref.get("sha256") != sha or ref.get("revision") != rev:
            changed += 1
        c["taxonomy_ref"] = {"path": str(TAX), "revision": rev, "sha256": sha,
                             "status": yaml.safe_load(TAX.read_text()).get("status")}
    else:
        bs = f"bound_taxonomy_sha_{sha[:12]}"
        if c.get("binding_status") != bs:
            changed += 1
        c["binding_status"] = bs
    out.append(json.dumps(c, ensure_ascii=False))
CASES.write_text("\n".join(out) + "\n")
print(f"taxonomy revision={rev} sha256={sha}")
print(f"pin updated in {changed} records")
