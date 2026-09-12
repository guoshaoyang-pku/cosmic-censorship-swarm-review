#!/usr/bin/env python3
"""Class-semantics fingerprint for the three frozen formulation schemas.

worker-039, W039-REV13-BINDCHAIN-01, 2026-09-12. Purpose: give an independent,
machine-recomputable reading of REC-12's falsifier — "any change to a class definition,
hypothesis, conclusion predicate or axis semantics" — for the move from the rev12 schemas to
the repaired rev13 schemas.

The tool partitions every top-level schema key into three classes:

  STRUCTURAL_CORE   the class's mathematical shape: id, components, hypotheses/quantifiers,
                    topology, data class, regularity, genericity, extension predicate,
                    conclusion predicate, non-vacuity, boundaries, implication ledger,
                    conventions, class-specific blocks, contract pointers
  ALLOWED_PROSE     fields that carry prose *about* the class rather than its shape. REC-12
                    item (3) authorizes an assertion-direction correction at exactly the F1
                    visibility lines, so these are hashed and reported separately and audited
                    by check_f1_strictness.py instead of failing the repair.
  METADATA          revision bookkeeping, timestamps, bindings, provenance, review state,
                    registries and unresolved-item queues

Digests reported per schema:
  strict_core_sha256       over the STRUCTURAL_CORE keys present in the file, minus the keys that
                           the pre-repair baseline did not measure. This is the cross-revision
                           comparable number: rev12 and rev13 are hashed over the same inputs.
  structural_extra         structural keys measured now but NOT measured at the pre-repair
                           baseline. Reported, never silently folded into a pass: a repair that
                           adds one of these needs it reviewed on its own.
  prose_sha256             over ALLOWED_PROSE_KEYS (the REC-12 item-3 surface)
  metadata_sha256          over METADATA_KEYS (bookkeeping; expected to move)

Usage:
  python3 schema_fingerprint.py SCHEMA.yaml [SCHEMA.yaml ...]     # human table
  python3 schema_fingerprint.py --json SCHEMA.yaml [...]          # machine object
Exit 0 always (this is a measurement, not a gate).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

STRUCTURAL_CORE = [
    "class_id",
    "class_components",
    "quantifiers",
    "topology",
    "i_plus",
    "data_class",
    "regularity",
    "genericity",
    "extension_predicate",
    "conclusion",
    "non_vacuity",
    "class_boundary",
    "sibling_disjoint_from",
    "implication_ledger",
    "conventions",
    "c0_specifics",
    "class_contract_pointer",
    "class_contract_supplement_pointer",
]
# Fields that carry prose assertions about the class. REC-12 item (3) corrects exactly these
# F1 lines, so their digest is reported and separately audited, not used to fail the core.
ALLOWED_PROSE_KEYS = [
    "visibility",
    "class_identity_variants",
    "falsifier",
    "anti_scope",
    "known_status",
    "scope_statement",
    "promotion_rule",
    "adjudication_queue",
    "unresolved_items",
]
# Structural keys that the pre-repair baseline did NOT measure. They are excluded from the
# cross-revision digest (so the comparison is over identical inputs) and surfaced separately.
BASELINE_UNMEASURED_STRUCTURAL = [
    "class_boundary",
    "sibling_disjoint_from",
    "implication_ledger",
    "conventions",
    "c0_specifics",
    "extension_predicate",
]
METADATA_KEYS = [
    "revision",
    "revision_history",
    "revised_at",
    "authored_at",
    "review_status",
    "epistemic_status",
    "timestamp_provenance",
    "f0_binding",
    "provenance",
    "l1_ledger_refs",
    "supersedes",
    "owner",
    "node_id",
    "artifact_kind",
    "schema_version",
]


def _canon(obj):
    """Canonical JSON text: sorted keys, no incidental whitespace, stable for equal data."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fingerprint(schema: dict, raw_bytes: bytes, path: str) -> dict:
    core = {k: schema.get(k) for k in STRUCTURAL_CORE if k in schema}
    comparable = {k: v for k, v in core.items() if k not in BASELINE_UNMEASURED_STRUCTURAL}
    prose = {k: schema.get(k) for k in ALLOWED_PROSE_KEYS if k in schema}
    mutable = {k: schema.get(k) for k in METADATA_KEYS if k in schema}
    strict_sha = _sha(_canon(comparable))
    prose_sha = _sha(_canon(prose))
    metadata_sha = _sha(_canon(mutable))
    extra = sorted(set(core) - set(comparable))
    return {
        "path": path,
        "file_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "bytes": len(raw_bytes),
        "class_id": schema.get("class_id"),
        "comparable_core_keys": sorted(comparable.keys()),
        "structural_extra": extra,
        "prose_keys_present": sorted(prose.keys()),
        "metadata_keys_present": sorted(mutable.keys()),
        "strict_core_sha256": strict_sha,
        "strict_core_sha256_12": strict_sha[:12],
        "prose_sha256": prose_sha,
        "prose_sha256_12": prose_sha[:12],
        "metadata_sha256": metadata_sha,
        "metadata_sha256_12": metadata_sha[:12],
        "_comparable_core": comparable,
        "_prose": prose,
        "_metadata": mutable,
    }


def fingerprint_file(path: str | Path) -> dict:
    p = Path(path)
    raw = p.read_bytes()
    schema = yaml.safe_load(raw.decode("utf-8"))
    if not isinstance(schema, dict):
        raise ValueError(f"{path}: not a YAML mapping")
    return fingerprint(schema, raw, str(path))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("schemas", nargs="+")
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args()
    out = [fingerprint_file(s) for s in args.schemas]
    if args.as_json:
        print(json.dumps(out, indent=2, sort_keys=True))
    else:
        for r in out:
            print(f"{r['class_id']:<22} file={r['file_sha256'][:12]} strict_core={r['strict_core_sha256_12']} "
                  f"prose={r['prose_sha256_12']} meta={r['metadata_sha256_12']} "
                  f"extra_struct={r['structural_extra']} {r['path']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # fail loud, never silently pass
        print(f"schema_fingerprint: ERROR {exc}", file=sys.stderr)
        sys.exit(2)
