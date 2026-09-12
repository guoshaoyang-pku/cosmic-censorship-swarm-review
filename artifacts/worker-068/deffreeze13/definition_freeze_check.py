#!/usr/bin/env python3
"""Candidate definition-freeze rule R-CAND-D -- reference implementation (worker-068).

PROPOSAL artifact, not an adopted gate rule. It answers the successor question left open by
FORM-POLARITY-12 (gap W068-P12-G1): the four FORM-HELDOUT-08 reference escapes
(`m04 adm-mass-erasure`, `m16 containment-reversal`, `m25 completeness-definition-swap`,
`m29 data-domain-contradiction`) keep the conclusion statements identical to the frozen base
and escape both class-binding stages, so R-CAND-F (conclusion-statement freeze) cannot see
them.

R-CAND-D generalises the freeze from the conclusion statement to a DECLARED SET of
semantic definition sites. It is structural and vocabulary-free: it never decides
mathematics, class truth, or a gate verdict. A flag means only "this leaf differs from the
frozen class base in a site the freeze covers"; every semantic change therefore requires an
owner re-freeze of the class contract, exactly as with R-CAND-F.

Site classification (deterministic, path-based)
-----------------------------------------------
Every leaf path of the parsed YAML document is assigned to one group by its first path
component (indices stripped). Leaves whose path is metadata (timestamps, revision counters,
hashes, pointers, provenance, citation status, locators) go to META and are NEVER frozen by
the semantic variants; they are isolated in `freeze_meta_only` so over-freezing and
under-freezing can be measured separately.

Variants
--------
  freeze_meta_only       META only. Negative control: catches revisions/hash refreshes but no
                         semantic site; used to show whether a corpus can be caught by
                         metadata drift alone.
  freeze_conclusion      conclusion.* (equivalent surface to R-CAND-F).
  freeze_defsites_min    {quantifiers, data_class, i_plus, implication_ledger,
                         extension_predicate} -- the four sites that carry the four labelled
                         reference mutations, plus the extension predicate.
  freeze_contract_min    freeze_defsites_min plus conclusion.* (the smallest candidate that
                         covers both the statement axis of R-CAND-F and the definition axis).
  freeze_defsites_core   freeze_defsites_min plus the remaining definitional groups
                         {topology, regularity, genericity, scope_statement, c0_specifics}.
  freeze_contract_full   freeze_defsites_core plus conclusion.* (all contract content, no
                         registry/identity or metadata).
  freeze_identity        class_components / class_id / sibling_disjoint_from / anti_scope /
                         class_identity_variants.
  freeze_all_minus_meta  every non-META leaf.
  freeze_all             every leaf (META included); positive control.

The rule is independent of the formulation stage code (PyYAML + stdlib only).

Usage:
  python3 definition_freeze_check.py --fixture F.yaml --base B.yaml --variant VARIANT [--json]
  python3 definition_freeze_check.py --list-variants
Exit: 0 checked (FLAG or PASS); 2 usage/IO error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML required", file=sys.stderr)
    sys.exit(2)

# --------------------------------------------------------------------------- site taxonomy
GROUP_OF_TOP = {
    "conclusion": "CONC",
    "scope_statement": "SCOPE",
    "class_components": "IDENT",
    "class_id": "IDENT",
    "sibling_disjoint_from": "IDENT",
    "anti_scope": "IDENT",
    "class_identity_variants": "IDENT",
    "quantifiers": "QUANT",
    "extension_predicate": "EXT",
    "data_class": "DATA",
    "genericity": "GEN",
    "topology": "TOPO",
    "regularity": "REG",
    "i_plus": "IPLUS",
    "implication_ledger": "LEDGER",
    "c0_specifics": "SPEC",
}
META_TOP = {
    "schema_version", "artifact_kind", "node_id", "owner", "authored_by", "authored_at",
    "revised_at", "revised_at_unused", "timestamp_provenance", "revision", "supersedes",
    "class_contract_pointer", "class_contract_supplement_pointer", "f0_binding",
    "known_status", "adjudication_queue", "provenance", "submission", "epistemic_status",
}
META_LEAVES = {
    "citation_status", "locator", "worker_sha256", "harvested_at", "harvested_from",
    "checked_at", "declared_f0_sha256", "binding_note", "consistency_evidence_sha256",
    "_sha256", "sha256",
}
META_COMPONENTS = {"provenance", "f0_binding", "adjudication_queue"}

SEMANTIC_GROUPS = ("CONC", "SCOPE", "IDENT", "QUANT", "EXT", "DATA", "GEN", "TOPO",
                   "REG", "IPLUS", "LEDGER", "SPEC", "OTHER")

VARIANTS = {
    "freeze_meta_only": ("META",),
    "freeze_conclusion": ("CONC",),
    "freeze_defsites_min": ("QUANT", "DATA", "IPLUS", "LEDGER", "EXT"),
    "freeze_contract_min": ("QUANT", "DATA", "IPLUS", "LEDGER", "EXT", "CONC"),
    "freeze_defsites_core": ("QUANT", "DATA", "IPLUS", "LEDGER", "EXT", "TOPO", "REG",
                             "GEN", "SCOPE", "SPEC"),
    "freeze_contract_full": ("QUANT", "DATA", "IPLUS", "LEDGER", "EXT", "TOPO", "REG",
                             "GEN", "SCOPE", "SPEC", "CONC"),
    "freeze_identity": ("IDENT",),
    "freeze_all_minus_meta": tuple(SEMANTIC_GROUPS),
    "freeze_all": tuple(SEMANTIC_GROUPS) + ("META",),
}


def _strip_index(part: str) -> str:
    return re.sub(r"\[\d+\]$", "", part)


def classify(path: str) -> str:
    """Map a leaf path such as ``$.data_class.adm_mass.sign`` to a site group."""
    parts = [_strip_index(p) for p in path.lstrip("$").lstrip(".").split(".") if p]
    if not parts:
        return "META"
    if parts[0] in META_TOP or any(p in META_COMPONENTS for p in parts):
        return "META"
    if parts[-1] in META_LEAVES:
        return "META"
    return GROUP_OF_TOP.get(parts[0], "OTHER")


def canon(value):
    """Canonical, formatting-insensitive form of a YAML leaf (key order is irrelevant)."""
    if value is None:
        return ""
    if isinstance(value, str):
        text = unicodedata.normalize("NFKC", value)
        return re.sub(r"\s+", " ", text).strip()
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _walk(node, prefix, out):
    if isinstance(node, dict):
        if not node:
            out[prefix] = "{}"
        for k in sorted(node):
            _walk(node[k], f"{prefix}.{k}" if prefix else str(k), out)
    elif isinstance(node, list):
        if not node:
            out[prefix] = "[]"
        for i, v in enumerate(node):
            _walk(v, f"{prefix}[{i}]", out)
    else:
        out[prefix] = canon(node)


def leaf_map(doc) -> dict:
    out: dict = {}
    _walk(doc, "$", out)
    return out


def changed_leaves(base_doc, fixture_doc) -> list:
    """Changed leaf paths (sorted), with group and canonical values."""
    b, f = leaf_map(base_doc), leaf_map(fixture_doc)
    rows = []
    for path in sorted(set(b) | set(f)):
        if b.get(path) != f.get(path):
            rows.append({
                "path": path,
                "group": classify(path),
                "base_sha256_12": hashlib.sha256(str(b.get(path, "")).encode()).hexdigest()[:12],
                "fixture_sha256_12": hashlib.sha256(str(f.get(path, "")).encode()).hexdigest()[:12],
                "base_preview": str(b.get(path, ""))[:160],
                "fixture_preview": str(f.get(path, ""))[:160],
            })
    return rows


def check(fixture_doc: dict, base_doc: dict, variant: str) -> dict:
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant}")
    groups = set(VARIANTS[variant])
    rows = changed_leaves(base_doc, fixture_doc)
    flags = [r for r in rows if r["group"] in groups]
    by_group: dict = {}
    for r in rows:
        by_group.setdefault(r["group"], []).append(r["path"])
    return {
        "variant": variant,
        "groups": sorted(groups),
        "verdict": "FLAG" if flags else "PASS",
        "flag_count": len(flags),
        "flags": flags,
        "changed_by_group": {g: sorted(v) for g, v in sorted(by_group.items())},
        "changed_leaf_count": len(rows),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture")
    ap.add_argument("--base")
    ap.add_argument("--variant", choices=sorted(VARIANTS))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--list-variants", action="store_true")
    a = ap.parse_args()
    if a.list_variants:
        print(json.dumps({v: sorted(g) for v, g in VARIANTS.items()}, indent=2, sort_keys=True))
        return 0
    if not (a.fixture and a.base and a.variant):
        ap.error("--fixture, --base and --variant are required")
    try:
        fixture_doc = yaml.safe_load(open(a.fixture, "rb").read())
        base_doc = yaml.safe_load(open(a.base, "rb").read())
    except Exception as e:
        print(f"IO/YAML error: {e}", file=sys.stderr)
        return 2
    out = check(fixture_doc, base_doc, a.variant)
    out["fixture"] = a.fixture
    out["base"] = a.base
    print(json.dumps(out, indent=2, sort_keys=True) if a.json else out["verdict"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
