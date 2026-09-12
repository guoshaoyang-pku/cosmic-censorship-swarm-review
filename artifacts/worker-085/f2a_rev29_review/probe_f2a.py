#!/usr/bin/env python3
"""W085-F2A-REV29-REVIEW-01 read-only probe.

Independent non-author G-FORM review instrument for schemas/af_scc_c2_vacuum.yaml at the
FROZEN rev29 pin.  Read-only: it opens canonical files for reading, writes only inside its own
artifact directory (probe.json).  It never writes a canonical path.

Exit: 0 measurement complete, 1 a check raised unexpectedly, 2 usage/input error.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent

CANON = {
    "schemas/af_scc_c2_vacuum.yaml": ROOT / "schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml": ROOT / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_wcc_vacuum.yaml": ROOT / "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml": ROOT / "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/FROZEN.json": ROOT / "artifacts/formulation/FROZEN.json",
    "research_map/formulation_taxonomy.yaml": ROOT / "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml": ROOT / "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/evidence/taxonomy_consistency.json": ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json",
    "artifacts/formulation/VOCAB_ALIASES.json": ROOT / "artifacts/formulation/VOCAB_ALIASES.json",
    "artifacts/formulation/VARIANT_REGISTRY.json": ROOT / "artifacts/formulation/VARIANT_REGISTRY.json",
    "artifacts/formulation/tools/check_class_schema.py": ROOT / "artifacts/formulation/tools/check_class_schema.py",
    "artifacts/worker-06/spec_conformance_audit.py": ROOT / "artifacts/worker-06/spec_conformance_audit.py",
    "entry_hashes.json": ROOT / "entry_hashes.json",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate mapping keys."""


def _no_dup(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dup)


def load(path: Path):
    return yaml.load(path.read_text(), Loader=StrictLoader)


def measure_pins() -> dict:
    return {k: sha256(p) for k, p in CANON.items() if p.exists()}


def check_binding(schema: dict) -> dict:
    b = schema["f0_binding"]
    out = {"declared": {}, "pointers": {}, "refresh_rule_satisfied": None}
    for field in ("declared_f0_sha256", "consistency_evidence_sha256"):
        declared = b.get(field)
        target = b.get("declared_f0_artifact") if field == "declared_f0_sha256" else b.get("consistency_evidence")
        measured = sha256(ROOT / target) if target and (ROOT / target).exists() else None
        out["declared"][field] = {
            "target": target,
            "declared": declared,
            "measured": measured,
            "status": "resolved" if declared == measured else "mismatch",
        }
    # pointer resolution inside the declared F0 and the supplement
    f0 = load(CANON["research_map/formulation_taxonomy.yaml"])
    sup = load(CANON["artifacts/formulation/formulation_taxonomy.yaml"])
    cp = schema.get("class_contract_pointer", "")
    sp = schema.get("class_contract_supplement_pointer", "")
    cid = schema["class_id"]

    def resolve(ptr: str, doc):
        if "#" not in ptr:
            return {"pointer": ptr, "status": "unresolvable(no-fragment)"}
        path_part, frag = ptr.split("#", 1)
        node = doc
        for part in frag.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return {"pointer": ptr, "status": f"dangling({part})"}
        return {"pointer": ptr, "status": "resolved", "node_type": type(node).__name__}

    out["pointers"]["class_contract_pointer"] = resolve(cp, f0)
    out["pointers"]["class_contract_supplement_pointer"] = resolve(sp, sup)
    # refresh rule: F0 declared hash == measured F0 hash
    out["refresh_rule_satisfied"] = (
        out["declared"]["declared_f0_sha256"]["status"] == "resolved"
    )
    return out


def _canonical_of(axis: str, value, vocab: dict):
    for canon, aliases in vocab[axis].items():
        if value == canon or value in aliases:
            return canon
    return None


def check_vocabulary(schema: dict) -> dict:
    """Reference rule: the schema's axis token must be alias-equivalent to the F0 per-class
    axis value.  A per-class mismatch is the defect; alias-vs-canonical spelling is a policy
    question about which artifact is stale, recorded but not by itself a class-statement change.
    """
    f0 = load(CANON["research_map/formulation_taxonomy.yaml"])
    vocab = load(CANON["artifacts/formulation/VOCAB_ALIASES.json"])
    cid = schema["class_id"]
    f0_axes = f0["classes"][cid]["axes"]
    out = {"class_id": cid, "axes": {}}
    for axis, schema_key in (("conclusion_type", ("conclusion", "conclusion_type")),
                             ("genericity_kind", ("genericity", "kind"))):
        schema_val = schema[schema_key[0]][schema_key[1]]
        f0_val = f0_axes.get(axis)
        can_schema = _canonical_of(axis, schema_val, vocab)
        can_f0 = _canonical_of(axis, f0_val, vocab)
        out["axes"][axis] = {
            "schema_value": schema_val,
            "f0_class_axis_value": f0_val,
            "equivalent_under_alias_policy": can_schema is not None and can_schema == can_f0,
            "vocab_canonical": can_schema,
            "schema_holds_alias": can_schema is not None and schema_val != can_schema,
            "f0_holds_alias": can_f0 is not None and f0_val != can_f0,
            "f0_field_vocabulary_allowed": f0.get("field_vocabulary", {}).get(axis, {}).get("allowed"),
            "schema_value_in_f0_allowed": schema_val in (f0.get("field_vocabulary", {}).get(axis, {}).get("allowed") or []),
            "alias_policy_note": vocab.get("policy"),
        }
    return out


def _strip_mentions(text: str) -> str:
    """Remove quoted/bracketed spans so a historical *mention* of a denial is not read as a
    live assertion (the assertion-vs-mention lesson from the CLASSSEP adjudication)."""
    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = re.sub(r"'[^']*'", " ", text)
    text = re.sub(r'"[^"]*"', " ", text)
    return text


def check_containment(schema: dict) -> dict:
    text = json.dumps(schema.get("implication_ledger", {}), sort_keys=True)
    b = schema.get("class_boundary", {})
    reg = json.dumps(schema.get("regularity", {}), sort_keys=True)
    # canonical order smallest -> largest extension set
    order = ["E_C2", "E_{C^1,1}", "E_H2loc", "E_C0"]
    pos = {t: text.find(t) for t in order}
    declared = [t for t in order if pos[t] >= 0]
    seen = [t for t in order if pos[t] >= 0]
    strictly_ordered = all(
        text.find(seen[i]) < text.find(seen[i + 1]) for i in range(len(seen) - 1)
    )
    raw_spans = [
        m.group(0)
        for m in re.finditer(
            r"[^.]*no containment[^.]*\.|E_C2[^.]*strictly (?:larger|bigger)[^.]*\.",
            reg + " " + json.dumps(b, sort_keys=True) + " " + text,
            re.I,
        )
    ]
    live_spans = [
        m.group(0)
        for m in re.finditer(
            r"[^.]*no containment[^.]*\.|E_C2[^.]*strictly (?:larger|bigger)[^.]*\.",
            _strip_mentions(reg + " " + json.dumps(b, sort_keys=True) + " " + text),
            re.I,
        )
    ]
    return {
        "containment_tokens_present_small_to_large": seen,
        "lexical_order_small_to_large": strictly_ordered,
        "containment_denial_raw_spans": raw_spans,
        "containment_denial_live_spans": live_spans,
        "forbidden_transfers_reasons": [
            t.get("reason", "") for t in schema.get("implication_ledger", {}).get("forbidden_transfers", [])
        ],
    }


ASSERTED = ["quantifiers", "conclusion", "extension_predicate", "topology", "data_class",
            "regularity", "genericity", "non_vacuity", "conventions"]


def check_leakage(schema: dict) -> dict:
    foreign = {
        "WCC": ["weak_cosmic_censorship", "visible_from_i+", "asymptotic_predictab",
                "AF-WCC-VAC-GEN", "visibility_from_I+"],
        "C0_token": ["scc_c0_future_inextendibility", "AF-SCC-C0-VAC-GEN"],
        "merged_regularity": [r"c\s*\^?\s*0\s*(?:or|and|/)\s*c\s*\^?\s*2"],
    }
    hits = {}
    for block in ASSERTED:
        blob = json.dumps(schema.get(block, {}), sort_keys=True)
        for fam, toks in foreign.items():
            for tok in toks:
                for m in re.finditer(tok, blob, re.I):
                    hits.setdefault(f"{block}:{fam}", []).append(m.group(0))
    flags = {
        "i_plus_in_conclusion": schema.get("i_plus", {}).get("in_conclusion"),
        "i_plus_completeness_in_conclusion": schema.get("i_plus", {}).get("completeness_in_conclusion"),
        "visibility_role": schema.get("visibility", {}).get("role"),
        "visibility_role_is_not_in_conclusion": schema.get("visibility", {}).get("role") == "not_in_conclusion",
    }
    return {"asserted_foreign_token_hits": hits, "flags": flags}


def check_inflation(schema: dict) -> dict:
    concl = schema.get("conclusion", {})
    assertoric = " ".join([
        str(concl.get("statement_natural_language", "")),
        str(concl.get("statement_formal", "")),
        " ".join(str(r.get("phrasing", "")) for r in concl.get("equivalent_rephrasings", [])),
    ]).lower()
    words = ["theorem", "proved", "established", "counterexample", "refuted"]
    return {
        "assertoric_words_present": [w for w in words if w in assertoric],
        "promotion_rule_text_present": "theorem" in str(concl.get("claim_promotion", "")).lower(),
        "epistemic_status": concl.get("epistemic_status"),
        "top_level_epistemic_status": schema.get("epistemic_status"),
        "promotion_rule_present": bool(schema.get("promotion_rule")),
        "claims_theorem_status": schema.get("claims_theorem_status", None),
    }


def check_falsifier(schema: dict) -> dict:
    f = schema.get("falsifier", {})
    t1 = f.get("tier_1", {})
    t2 = f.get("tier_2", {})
    return {
        "tier_1_refutes": t1.get("refutes"),
        "tier_1_witness_type_present": bool(t1.get("witness_type")),
        "tier_1_machine_steps": len(t1.get("machine_checkable_steps", [])),
        "tier_1_non_machine_step_present": bool(t1.get("non_machine_checkable_step")),
        "tier_1_genericity_requirement_present": bool(t1.get("genericity_requirement")),
        "tier_2_labelling": t2.get("labelling_required"),
        "schema_falsifiers": len(f.get("schema_falsifiers", [])),
    }


def run_controls() -> dict:
    """Mutation controls on in-memory copies.  Each control must trip its detector."""
    base = load(CANON["schemas/af_scc_c2_vacuum.yaml"])
    results = {}

    def clone(d):
        return json.loads(json.dumps(d))

    # C1 vocabulary: substitute a foreign conclusion token (per-class reference)
    c = clone(base)
    c["conclusion"]["conclusion_type"] = "weak_cosmic_censorship"
    v = check_vocabulary(c)
    results["C1_foreign_conclusion_token"] = {
        "equivalent": v["axes"]["conclusion_type"]["equivalent_under_alias_policy"],
        "detected": v["axes"]["conclusion_type"]["equivalent_under_alias_policy"] is False,
    }
    # C2 binding: corrupt declared F0 hash in memory (hash resolution must mismatch)
    c = clone(base)
    c["f0_binding"]["declared_f0_sha256"] = "0" * 64
    results["C2_corrupt_f0_hash"] = {"detected": check_binding(c)["declared"]["declared_f0_sha256"]["status"] == "mismatch"}
    # C3 containment denial: inject a live (unquoted) denial span
    c = clone(base)
    c["regularity"]["must_not_conflate"].append("No containment with C2 is asserted here.")
    c2 = check_containment(c)
    results["C3_live_containment_denial_injection"] = {"detected": bool(c2["containment_denial_live_spans"])}
    # C6 mention-only denial: quoted historical mention must NOT trip the live detector
    c = clone(base)
    c["regularity"]["must_not_conflate"].append("[historical: 'No containment with C2 is asserted here' was wrong]")
    c6 = check_containment(c)
    results["C6_quoted_mention_false_positive_control"] = {
        "live_detected": bool(c6["containment_denial_live_spans"]),
        "raw_detected": bool(c6["containment_denial_raw_spans"]),
        "expected_live": False,
    }
    # C4 leakage flag: mark I+ in conclusion
    c = clone(base)
    c["i_plus"]["in_conclusion"] = True
    results["C4_iplus_in_conclusion"] = {"detected": check_leakage(c)["flags"]["i_plus_in_conclusion"] is True}
    # C5 falsifier: remove machine-checkable steps
    c = clone(base)
    c["falsifier"]["tier_1"]["machine_checkable_steps"] = []
    results["C5_empty_machine_steps"] = {"detected": check_falsifier(c)["tier_1_machine_steps"] == 0}
    return results


def main() -> int:
    out = {"probe": "W085-F2A-REV29-REVIEW-01", "read_only": True, "t0_pins": measure_pins()}
    schema = load(CANON["schemas/af_scc_c2_vacuum.yaml"])
    mirror = load(CANON["artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"])
    out["canonical_mirror_byte_identical"] = (
        out["t0_pins"]["schemas/af_scc_c2_vacuum.yaml"]
        == out["t0_pins"]["artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"]
    )
    out["schema_identity"] = {
        "class_id": schema.get("class_id"),
        "node_id": schema.get("node_id"),
        "revision": schema.get("revision"),
        "conclusion_type": schema.get("conclusion", {}).get("conclusion_type"),
        "regularity_token": schema.get("class_components", {}).get("regularity_token"),
        "strict_parse": "ok (no duplicate keys)",
    }
    out["f0_binding"] = check_binding(schema)
    out["vocabulary"] = check_vocabulary(schema)
    out["containment"] = check_containment(schema)
    out["leakage"] = check_leakage(schema)
    out["inflation"] = check_inflation(schema)
    out["falsifier"] = check_falsifier(schema)
    # cross-artifact shared fields
    f2b = load(CANON["schemas/af_scc_c0_vacuum.yaml"])
    out["cross_artifact"] = {
        "D0_equal_F2a_F2b": schema["quantifiers"]["domains"]["D0"] == f2b["quantifiers"]["domains"]["D0"],
        "data_class_key_sets_equal": sorted(schema["data_class"].keys()) == sorted(f2b["data_class"].keys()),
        "extension_predicate_regularity": schema["extension_predicate"]["frozen_regularity"],
        "extension_predicate_equation": schema["extension_predicate"]["frozen_equation_concept"],
        "F2b_c0_negation_present": "No containment with C2" in json.dumps(f2b.get("regularity", {})),
    }
    # declared-hash sidecar layer (global, factual record only)
    side = {}
    for p in sorted((ROOT / "schemas").glob("*.sha256")):
        declared = p.read_text().split()[0]
        target = ROOT / "schemas" / p.read_text().split()[-1]
        side[str(p.relative_to(ROOT))] = {
            "declared": declared,
            "target": str(target.relative_to(ROOT)),
            "measured": sha256(target) if target.exists() else None,
            "status": "resolved" if target.exists() and sha256(target) == declared else "mismatch",
        }
    eh = load(CANON["entry_hashes.json"])
    eh_rows = {}
    for rel, declared in eh.items():
        t = ROOT / rel
        measured = sha256(t) if t.exists() else None
        eh_rows[rel] = {"declared": declared, "measured": measured,
                        "status": "resolved" if declared == measured else "mismatch"}
    out["declared_hash_sidecars"] = side
    out["entry_hashes_disagreements"] = {k: v for k, v in eh_rows.items() if v["status"] == "mismatch"}
    out["controls"] = run_controls()
    out["t1_pins"] = measure_pins()
    out["pin_drift"] = {k: [out["t0_pins"][k], out["t1_pins"][k]] for k in out["t0_pins"] if out["t0_pins"][k] != out["t1_pins"][k]}
    (HERE / "probe.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "probe": out["probe"],
        "pin_drift": out["pin_drift"],
        "mirror_identical": out["canonical_mirror_byte_identical"],
        "f0_declared_resolved": out["f0_binding"]["declared"]["declared_f0_sha256"]["status"],
        "consistency_evidence_resolved": out["f0_binding"]["declared"]["consistency_evidence_sha256"]["status"],
        "pointers": {k: v["status"] for k, v in out["f0_binding"]["pointers"].items()},
        "vocab": {k: {"schema": v["schema_value"], "f0": v["f0_class_axis_value"],
                       "equivalent": v["equivalent_under_alias_policy"],
                       "schema_holds_alias": v["schema_holds_alias"],
                       "f0_holds_alias": v["f0_holds_alias"],
                       "schema_in_f0_allowed": v["schema_value_in_f0_allowed"]}
                  for k, v in out["vocabulary"]["axes"].items()},
        "containment_live_denials": len(out["containment"]["containment_denial_live_spans"]),
        "containment_raw_mentions": len(out["containment"]["containment_denial_raw_spans"]),
        "leakage_hits": len(out["leakage"]["asserted_foreign_token_hits"]),
        "inflation_words": out["inflation"]["assertoric_words_present"],
        "controls": out["controls"],
        "entry_hashes_mismatches": len(out["entry_hashes_disagreements"]),
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"PROBE ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
