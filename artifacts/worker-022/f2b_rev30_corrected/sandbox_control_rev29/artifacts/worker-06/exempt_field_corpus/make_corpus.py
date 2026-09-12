#!/usr/bin/env python3
"""FORM-EXEMPT-09 corpus generator (worker-06).

Targets the documented residual blind spot from FORM-HELDOUT-07 / FROZEN rev11:
"prose leaks in the exempt explanatory fields, which neither stage scans by design"
(comms/inbox/worker-06.jsonl line 7).

Every mutant is derived from ONE frozen canonical base (FROZEN rev18) by replacing
exactly one string that lives in an unscanned or key-exempt field. The injected text
asserts (not negates, not prescribes) content the frozen class contract forbids; the
field it hides in is not reached by the rule that should catch it. Each mutant names
the invariant (rule id) it violates and the rule that would catch the same sentence
if it sat in a scanned field.

The manifest is written and hashed BEFORE any gate is run. The generator performs no
measurement.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
FIX = OUT / "fixtures"
CANON = ROOT / "artifacts" / "formulation" / "schemas"

BASES = {
    "c0": {"file": "af_scc_c0_vacuum.yaml", "class_id": "AF-SCC-C0-VAC-GEN",
           "frozen_sha256_prefix": "bdb23f76b895",
           "path": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"},
    "c2": {"file": "af_scc_c2_vacuum.yaml", "class_id": "AF-SCC-C2-VAC-GEN",
           "frozen_sha256_prefix": "e9fcefe6e595",
           "path": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"},
    "wcc": {"file": "af_wcc_vacuum.yaml", "class_id": "AF-WCC-VAC-GEN",
            "frozen_sha256_prefix": "f962c117ba11",
            "path": "artifacts/formulation/schemas/af_wcc_vacuum.yaml"},
}

# family -> (invariant refs, the rule that catches this text in a SCANNED field)
FAMILIES = {
    "X1_wcc_content_in_scc": (
        ["R12 leakage_scan_blocks", "FROZEN rev10 class separation: no WCC content in an SCC class"],
        "R12 (foreign-token scan) if placed in conclusion/visibility.definition/i_plus/falsifier"),
    "X2_merged_regularity": (
        ["R13 composite regularity ban", "rule_spec R13: no composite regularity outside a forbidden-phrase quotation"],
        "R13 (composite scan) if placed in any non-exempt field"),
    "X3_sibling_regularity_substitution": (
        ["R18 frozen_regularity must equal the class token", "R31 foreign-regularity scan"],
        "R31 if placed in extension_predicate.definition or an assertive path"),
    "X4_c0_curvature_hypothesis": (
        ["R29 C0 class carries no curvature-based hypothesis"],
        "R29 if placed in any non-exempt field"),
    "X5_theorem_promotion": (
        ["R20 no theorem promotion without a proof artifact", "R11 conclusion not labelled theorem"],
        "R20 if placed in conclusion.statement_*"),
    "X6_quantifier_order_substitution": (
        ["R27 comeager-set quantifier must precede the data quantifier", "rule_spec R03 order_matters=true"],
        "R27 if the formal ordered block is changed"),
    "X7_iplus_completeness_in_scc": (
        ["R09 SCC i_plus.role=assumption and no completeness assertion"],
        "R09 if placed in i_plus.definition/required_properties/completeness_definition"),
    "X8_matter_in_vac": (
        ["R05 matter must be none for VAC", "R05/R12 foreign matter token"],
        "R05 (matter field) / R12 if placed in an assertive path"),
    "X9_multi_end_slice": (
        ["R04 exactly one AF end declared", "R04 slice_topology two/multiple-ends rejection"],
        "R04 if placed in topology.slice_topology"),
    "X10_foreign_content_in_extensions": (
        ["R26 extensions is a key-allowlist escape hatch only; content rules still apply"],
        "R12 if placed in an assertive path; R13 catches composite wording in extensions"),
    "X11_transfer_truth_table_inversion": (
        ["R28 canonical truth table: full_measure -> residual_comeager is no_transfer"],
        "R28 if written as a transfer_holds row with pair=[full_measure,residual_comeager]"),
    "X12_scc_content_in_wcc": (
        ["R12 no SCC token in a WCC class", "INEXTENDIB_NON_GEODESIC conditional"],
        "R12 if placed in conclusion/visibility/i_plus/falsifier"),
    "X13_genericity_kind_substitution": (
        ["R21 genericity.kind must be the frozen default residual_comeager"],
        "R21 if genericity.kind is changed"),
    "X14_source_conclusion_overclaim": (
        ["R15 no source presented as establishing the class conclusion"],
        "R15 if placed in provenance.sources[*].concept and phrased with the R15 regex"),
}

# name, base, dotted path, injected prose, family, rephrased (no canonical forbidden token)
MUTANTS = [
    ("m01_c0_wcc_in_visibility_reason", "c0", "visibility.reason",
     "The visible singularity is resolved by weak cosmic censorship, so no Cauchy horizon forms in the generic development.",
     "X1_wcc_content_in_scc", False),
    ("m02_c2_wcc_in_visibility_reason", "c2", "visibility.reason",
     "Weak cosmic censorship guarantees that the Cauchy horizon stays hidden from I+ for generic data.",
     "X1_wcc_content_in_scc", False),
    ("m03_c0_merged_regularity_warning", "c0", "genericity.class_change_warning",
     "The class covers the continuous or twice-differentiable extension class; the distinction is bookkeeping.",
     "X2_merged_regularity", False),
    ("m04_wcc_merged_regularity_warning", "wcc", "genericity.class_change_warning",
     "Data whose development is C0 or C2 inextendible are excluded from this class.",
     "X2_merged_regularity", False),
    ("m05_c2_sibling_regularity_why", "c2", "extension_predicate.why_future_not_two_sided",
     "A merely continuous extension is the intended reading; the twice-differentiable requirement is optional.",
     "X3_sibling_regularity_substitution", True),
    ("m06_c0_sibling_regularity_why", "c0", "extension_predicate.why_bare_metric",
     "Twice-differentiable extensions are also covered; C^{1,1} metrics are admitted in the definition.",
     "X3_sibling_regularity_substitution", False),
    ("m07_c0_curvature_hypothesis_falsifier", "c0", "non_vacuity.vacuity_falsifier",
     "The class is non-vacuous only if the Kretschmann scalar is bounded on the maximal development.",
     "X4_c0_curvature_hypothesis", False),
    ("m08_c0_theorem_promotion_provenance", "c0", "provenance.no_status_claim",
     "We prove the theorem for all generic data; the proof is this artifact.",
     "X5_theorem_promotion", False),
    ("m09_c0_quantifier_order_note", "c0", "quantifiers.order_note",
     "For every datum there exists a comeager set of extensions, so the comeager quantifier may follow the data quantifier.",
     "X6_quantifier_order_substitution", True),
    ("m10_c0_iplus_completeness_reason", "c0", "visibility.reason",
     "I+ is complete in the conclusion, and generic data have complete future null infinity.",
     "X7_iplus_completeness_in_scc", True),
    ("m11_c0_matter_in_gauge", "c0", "data_class.gauge",
     "A small amount of scalar-field matter is permitted; the vacuum restriction is a convenience.",
     "X8_matter_in_vac", False),
    ("m12_c0_multi_end_development", "c0", "topology.development_topology",
     "The slice may have two asymptotically flat ends; the second end is suppressed in the generic case.",
     "X9_multi_end_slice", False),
    ("m13_c0_foreign_in_extensions", "c0", "extensions.note",
     "The visible singularity is hidden from I+, which is the standard weak-censorship statement for this setting.",
     "X10_foreign_content_in_extensions", True),
    ("m14_c2_transfer_inversion_falsifier", "c2", "non_vacuity.vacuity_falsifier",
     "Full measure transfers to residual comeager, so the measure-theoretic formulation implies this class.",
     "X11_transfer_truth_table_inversion", True),
    ("m15_wcc_scc_inextendibility_warning", "wcc", "genericity.class_change_warning",
     "This class requires inextendibility as a continuous Lorentzian manifold of the development.",
     "X12_scc_content_in_wcc", False),
    ("m16_wcc_kind_substitution_falsifier", "wcc", "non_vacuity.vacuity_falsifier",
     "The operative genericity is the open dense escape class, not the residual comeager class.",
     "X13_genericity_kind_substitution", True),
    ("m17_c0_kind_substitution_warning", "c0", "genericity.class_change_warning",
     "The open dense escape notion is the operative class here; residual comeager is only a default.",
     "X13_genericity_kind_substitution", True),
    ("m18_c0_source_overclaim_subsumption", "c0", "implication_ledger.subsumption_note",
     "The cited theorem settles the censorship question for this class, so the implication is proved.",
     "X14_source_conclusion_overclaim", True),
]

# (name, base, path, value, why it is legitimate)
POSITIVE_CONTROLS = [
    ("p01_c0_inclass_reason", "c0", "visibility.reason",
     "Visibility from I+ is the WCC predicate, not part of this conclusion; no visible-singularity "
     "falsifier belongs to this SCC class.",
     "in-class, negated/prescriptive phrasing inside the same exempt field as m01/m10"),
    ("p02_c2_inclass_why", "c2", "extension_predicate.why_future_not_two_sided",
     "A two-sided formulation would be a strictly different class; this class fixes the future direction only.",
     "in-class restatement inside the same why_ field as m05"),
]

NEGATIVE_CONTROLS = [
    ("n01_c0_negated_merge", "c0", "genericity.class_change_warning",
     "This is NOT the C0 or C2 merged class; the two regularities are separate frozen classes.",
     "composite tokens under explicit negation inside the same exempt field as m03"),
    ("n02_wcc_negated_foreign", "wcc", "genericity.class_change_warning",
     "SCC-style inextendibility of the development is not asserted here; this class is about visible singularities.",
     "SCC token under explicit negation inside the same exempt field as m15"),
]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def set_path(doc, dotted: str, value):
    parts = []
    for seg in dotted.split("."):
        m = re.match(r"^([^\[]+)(?:\[(\d+)\])?$", seg)
        if not m:
            raise ValueError(f"bad path segment {seg!r}")
        parts.append((m.group(1), int(m.group(2)) if m.group(2) is not None else None))
    cur = doc
    for key, idx in parts[:-1]:
        if key not in cur:            # allow creating a fresh allowlisted container (`extensions`)
            cur[key] = {}
        cur = cur[key]
        if idx is not None:
            cur = cur[idx]
    key, idx = parts[-1]
    if idx is None:
        cur[key] = value
    else:
        cur[key][idx] = value


def dump_yaml(doc) -> str:
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True,
                          default_flow_style=False, width=1000)


def main():
    FIX.mkdir(parents=True, exist_ok=True)
    for old in FIX.glob("*.yaml"):
        old.unlink()

    base_docs, base_meta = {}, {}
    for key, meta in BASES.items():
        raw = (CANON / meta["file"]).read_bytes()
        h = sha256_bytes(raw)
        assert h.startswith(meta["frozen_sha256_prefix"]), (key, h)
        base_docs[key] = yaml.safe_load(raw)
        base_meta[key] = {"path": meta["path"], "class_id": meta["class_id"],
                          "sha256": h, "frozen_rev": 18}

    entries = []

    def emit(kind, name, base, doc):
        text = dump_yaml(doc)
        p = FIX / f"{name}.yaml"
        p.write_text(text)
        entries.append({"name": name, "kind": kind, "base": base,
                        "file": f"fixtures/{name}.yaml",
                        "sha256": sha256_bytes(text.encode()),
                        "bytes": len(text.encode())})

    # controls: round-trip of each frozen canonical base (format control)
    for key in ("c0", "c2", "wcc"):
        emit("control_roundtrip", f"rt_{key}", key, base_docs[key])
    # conforming and negated-phrase controls
    for name, base, path, value, why in POSITIVE_CONTROLS:
        doc = yaml.safe_load(dump_yaml(base_docs[base]))
        set_path(doc, path, value)
        emit("control_positive", name, base, doc)
        entries[-1]["why_legitimate"] = why
    for name, base, path, value, why in NEGATIVE_CONTROLS:
        doc = yaml.safe_load(dump_yaml(base_docs[base]))
        set_path(doc, path, value)
        emit("control_negative", name, base, doc)
        entries[-1]["why_legitimate"] = why
    # mutants
    for name, base, path, value, family, rephrased in MUTANTS:
        doc = yaml.safe_load(dump_yaml(base_docs[base]))
        set_path(doc, path, value)
        emit("mutant", name, base, doc)
        inv, should = FAMILIES[family]
        entries[-1].update({"family": family, "field": path, "injected_text": value,
                            "class_id": BASES[base]["class_id"],
                            "invariant_refs": inv,
                            "would_be_caught_by": should,
                            "rephrased_no_canonical_token": rephrased})

    manifest = {
        "artifact": "FORM-EXEMPT-09-CORPUS-MANIFEST",
        "owner": "worker-06",
        "assignment": "exempt-field held-out corpus (successor to FORM-HELDOUT-07)",
        "created_at_before_measurement": "2026-09-12T00:20:00+08:00",
        "design": ("each mutant = one frozen canonical base with exactly one string replaced "
                   "inside a field that is key-exempt or outside every scanned path; the injected "
                   "text asserts content the frozen class contract forbids; no mutant is authored "
                   "by looking at a gate implementation's regex"),
        "bases": base_meta,
        "counts": {
            "mutants": sum(1 for e in entries if e["kind"] == "mutant"),
            "families": len({e["family"] for e in entries if e["kind"] == "mutant"}),
            "rephrased": sum(1 for e in entries if e["kind"] == "mutant" and e["rephrased_no_canonical_token"]),
            "controls": sum(1 for e in entries if e["kind"].startswith("control")),
        },
        "fixtures": entries,
    }
    body = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    (OUT / "manifest.json").write_text(body)
    (OUT / "manifest.sha256").write_text(sha256_bytes(body.encode()) + "  manifest.json\n")
    print(json.dumps({"manifest_sha256": sha256_bytes(body.encode()),
                      "fixtures": len(entries),
                      "mutants": manifest["counts"]["mutants"],
                      "families": manifest["counts"]["families"],
                      "controls": manifest["counts"]["controls"]}, indent=2))


if __name__ == "__main__":
    main()
