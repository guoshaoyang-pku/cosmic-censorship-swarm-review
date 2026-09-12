#!/usr/bin/env python3
"""Hash-bound successor generator for taxonomy_consistency.json (worker-05, F2a).

Why this exists
---------------
HF-B1: every class schema declares `f0_binding.consistency_evidence` and the rule
"if the declared F0 artifact changes hash, this binding must be refreshed and the
consistency check re-run before any gate verdict".  The live evidence file
(`artifacts/formulation/evidence/taxonomy_consistency.json`, sha256 9e335e9b...)
records the two compared paths and `consistent: true` but **no sha256 of either
compared file**, so its bytes are identical for every revision of the taxonomy:
it cannot witness which revision it checked and cannot discharge the refresh rule.
The durable binding checker (check_class_binding_drift.py) hard-fails that as B7.

This generator emits the minimal successor: the same record plus
  - `map_taxonomy_sha256`, `lead_contract_sha256` (top-level, measured), and
  - `input_sha256` {path: measured sha256} for both compared files, and
  - `binding` {declared_f0_artifact, declared_f0_sha256, refresh_rule}.
Bytes are deterministic (sorted keys, no timestamp), so two runs over unchanged
inputs are byte-identical and any input revision change moves the record hash.

No canonical write: `--out` chooses the destination; this tool never writes the
canonical evidence path unless the caller points it there.

Usage:
  python3 gen_hashbound_consistency_evidence.py \
      --canonical research_map/formulation_taxonomy.yaml \
      --supplement artifacts/formulation/formulation_taxonomy.yaml \
      --template artifacts/formulation/evidence/taxonomy_consistency.json \
      --out artifacts/worker-05/verify/taxonomy_consistency_hashbound.json
Exit 0 on emit, 2 on usage/parse error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]

CANONICAL_REL = "research_map/formulation_taxonomy.yaml"
SUPPLEMENT_REL = "artifacts/formulation/formulation_taxonomy.yaml"
TEMPLATE_REL = "artifacts/formulation/evidence/taxonomy_consistency.json"

ALIAS_POLICY = (
    "canonical token first; accepted aliases are equivalent for consistency "
    "checks only and must never appear in a new canonical artifact"
)
REFRESH_RULE = (
    "if either input in input_sha256 changes, regenerate this record and re-run "
    "the F0 class-binding check before any gate verdict"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def class_sets(canonical: dict, supplement: dict):
    classes = set((canonical.get("classes") or {}).keys())
    contracts = set((supplement.get("class_contracts") or {}).keys())
    declared_ids = set(canonical.get("class_ids") or [])
    return classes, contracts, declared_ids


def build_record(root: Path, canonical: Path, supplement: Path, template: Path | None) -> dict:
    canon_doc = load_yaml(canonical) or {}
    supp_doc = load_yaml(supplement) or {}
    canon_sha = sha256_file(canonical)
    supp_sha = sha256_file(supplement)
    canon_rel = rel(root, canonical)
    supp_rel = rel(root, supplement)

    rec: dict = {}
    if template is not None and template.exists():
        loaded = json.loads(template.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            rec = loaded

    classes, contracts, declared_ids = class_sets(canon_doc, supp_doc)
    errors: list[str] = []
    divergences: list[str] = []
    for cid in sorted(classes - contracts):
        divergences.append(f"canonical class {cid!r} has no class_contract entry")
    for cid in sorted(contracts - classes):
        divergences.append(f"class_contract {cid!r} has no canonical class entry")
    for cid in sorted(classes - declared_ids):
        errors.append(f"canonical classes key {cid!r} is absent from class_ids")
    for cid in sorted(declared_ids - classes):
        errors.append(f"class_ids entry {cid!r} is absent from classes")
    rec["map_taxonomy"] = canon_rel
    rec["lead_contract"] = supp_rel
    rec["map_taxonomy_sha256"] = canon_sha
    rec["lead_contract_sha256"] = supp_sha
    rec["input_sha256"] = {canon_rel: canon_sha, supp_rel: supp_sha}
    rec["consistent"] = not errors and not divergences
    rec["errors"] = sorted(errors)
    rec["contract_divergences"] = sorted(divergences)
    rec.setdefault("notes", [])
    rec["notes"] = sorted(set(rec["notes"]) | {
        "hash-bound successor: input_sha256 records the measured revision of both "
        "compared files so the record is revision-sensitive (HF-B1)"
    }) if rec["notes"] else [
        "hash-bound successor: input_sha256 records the measured revision of both "
        "compared files so the record is revision-sensitive (HF-B1)"
    ]
    rec["classes_compared"] = sorted(classes & contracts)
    rec["alias_policy"] = rec.get("alias_policy") or ALIAS_POLICY
    rec["binding"] = {
        "record_schema": "hashbound-taxonomy-consistency/1",
        "declared_f0_artifact": canon_rel,
        "declared_f0_sha256": canon_sha,
        "refresh_rule": REFRESH_RULE,
    }
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--canonical", default=CANONICAL_REL)
    ap.add_argument("--supplement", default=SUPPLEMENT_REL)
    ap.add_argument("--template", default=TEMPLATE_REL)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    canonical = root / args.canonical
    supplement = root / args.supplement
    template = root / args.template if args.template else None
    for path in (canonical, supplement):
        if not path.exists():
            print(f"input missing: {path}", file=sys.stderr)
            return 2
    rec = build_record(root, canonical, supplement, template)
    text = json.dumps(rec, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    out = Path(args.out)
    if not out.is_absolute():
        out = root / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(json.dumps({
        "out": str(out),
        "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        "map_taxonomy_sha256": rec["map_taxonomy_sha256"],
        "lead_contract_sha256": rec["lead_contract_sha256"],
        "consistent": rec["consistent"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
