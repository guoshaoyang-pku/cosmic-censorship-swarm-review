#!/usr/bin/env python3
"""Validate VARIANT_REGISTRY.json v2 against the frozen canonical schemas.

Schema (astra-classscope-02): every non-frozen reading is a VARIANT of a frozen parent class
with keys {parent_class, variant_id, definition, evidence, status}. Only the frozen four class
ids may appear in any `class_ids` field. Exit 0/1.
"""
import hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
REG = json.loads((ROOT/"artifacts/formulation/VARIANT_REGISTRY.json").read_text())
MAN = json.loads((ROOT/"artifacts/formulation/FROZEN.json").read_text())
errs = []

FROZEN = {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"}
REQUIRED = ("parent_class", "variant_id", "definition", "evidence", "status")

# --- parent classes: the frozen four only, with declared canonical artifacts ---
parents = {p["class_id"]: p for p in REG.get("parent_classes", [])}
if set(parents) != FROZEN:
    errs.append(f"parent_classes must be exactly the frozen four: {sorted(set(parents) ^ FROZEN)}")
canon_path = {
    "AF-WCC-VAC-GEN": "schemas/af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": "schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": "schemas/af_scc_c0_vacuum.yaml",
}
for cid, path in canon_path.items():
    p = parents.get(cid, {})
    if p.get("canonical_artifact") != path:
        errs.append(f"{cid}: canonical_artifact mismatch ({p.get('canonical_artifact')!r} != {path!r})")
    if path not in MAN["files"]:
        errs.append(f"{cid}: canonical artifact {path} not in FROZEN manifest")
    if not (ROOT/path).exists():
        errs.append(f"{cid}: canonical artifact {path} missing from disk")

# --- variants: required keys, unique ids, valid parent links, evidence + falsifier ---
variants = REG.get("variants", [])
seen = set()
for v in variants:
    for k in REQUIRED:
        if not v.get(k):
            errs.append(f"variant {v.get('parent_class')}/{v.get('variant_id')}: missing {k}")
    pc, vid = v.get("parent_class"), v.get("variant_id")
    if pc not in FROZEN:
        errs.append(f"variant {vid}: parent_class {pc!r} is not one of the frozen four")
    if (pc, vid) in seen:
        errs.append(f"duplicate variant ({pc}, {vid})")
    seen.add((pc, vid))
    if not v.get("falsifier"):
        errs.append(f"variant {pc}/{vid}: missing falsifier")
    if not v.get("why_separate"):
        errs.append(f"variant {pc}/{vid}: missing why_separate")
    dref = v.get("delta_ref")
    if dref and not (ROOT/dref).exists():
        errs.append(f"variant {pc}/{vid}: delta_ref missing on disk: {dref}")
if not variants:
    errs.append("registry has no variants")

# --- no new class ids anywhere in a `class_ids` field ---
extra_ids = []
def scan(node, path="$"):
    if isinstance(node, dict):
        for k, val in node.items():
            if k == "class_ids":
                vals = val if isinstance(val, list) else [val]
                for x in vals:
                    if x not in FROZEN:
                        extra_ids.append(f"{path}.{k}: {x!r}")
            else:
                scan(val, f"{path}.{k}")
    elif isinstance(node, list):
        for i, val in enumerate(node):
            scan(val, f"{path}[{i}]")
scan(REG)
if extra_ids:
    errs.append(f"non-frozen class id(s) in a class_ids field: {extra_ids[:5]}")

# --- strength consistency with the frozen containment chain ---
by_id = {(v.get("parent_class"), v.get("variant_id")): v for v in variants}
h2 = by_id.get(("AF-SCC-C0-VAC-GEN", "H2LOC"), {})
if "between C2 and C0" not in h2.get("strength", ""):
    errs.append("variant H2LOC strength must place it between C2 and C0")
tw = by_id.get(("AF-SCC-C2-VAC-GEN", "TWOSIDED"), {})
if "STRONGER" not in tw.get("strength", ""):
    errs.append("variant TWOSIDED must be marked stronger")
chv = by_id.get(("AF-SCC-C0-VAC-GEN", "CH"), {})
if "WEAKER" not in chv.get("strength", ""):
    errs.append("variant CH must be marked weaker than its parent")
# SET is level-split (rev14 item 5): the visibility PREDICATE is strictly weaker than the
# parent's, while the class-level conclusion predicate (no set-visible singularity) is strictly
# STRONGER. The substring test this replaces ("STRONGER" in strength) passed only because the
# rev13 erratum text happened to contain the word 'STRONGER' inside "corrected from 'strictly
# STRONGER'"; it asserted the wrong level and would have passed a flat, level-confused label.
setv = by_id.get(("AF-WCC-VAC-GEN", "SET"), {})
sset = setv.get("strength", "")
pi, ci = sset.find("predicate-level"), sset.find("class-level")
if pi < 0 or ci < 0 or ci < pi:
    errs.append("variant SET strength must carry level-qualified wording with a 'predicate-level' "
                "marker before a 'class-level' marker")
else:
    if "WEAKER" not in sset[pi:ci]:
        errs.append("variant SET predicate-level label must be strictly WEAKER than the parent "
                    "predicate (the parent's single-q tail predicate entails the union reading)")
    if "STRONGER" not in sset[ci:]:
        errs.append("variant SET class-level subject must be strictly STRONGER (a weaker visibility "
                    "predicate makes 'no visible singularity' harder to satisfy)")
    if sset.startswith("strictly weaker than AF-WCC-VAC-GEN"):
        errs.append("variant SET strength carries the flat one-level label 'strictly weaker than "
                    "AF-WCC-VAC-GEN', which is a level error")

out = {"registry": "artifacts/formulation/VARIANT_REGISTRY.json", "version": REG.get("version"),
       "parent_classes": sorted(parents), "variants": [f"{p}/{v}" for p, v in sorted(seen)],
       "variant_count": len(variants), "class_ids_frozen_four_only": not extra_ids,
       "valid": not errs, "errors": errs}
(ROOT/"artifacts/formulation/evidence/variant_registry_check.json").write_text(json.dumps(out, indent=2)+"\n")
print(("VALID" if not errs else "INVALID") + f": {len(parents)} parent classes, {len(variants)} variants")
for e in errs: print("  " + e)
sys.exit(0 if not errs else 1)
