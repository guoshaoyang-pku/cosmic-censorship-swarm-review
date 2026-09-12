#!/usr/bin/env python3
"""W047-REC37-TOKEN-CROSSWALK-01 builder (deterministic, read-only on canonical paths).

Builds the REC-37 candidate crosswalk artifact from hash-pinned bytes:
  runtime/state/controller_verification/astra-lifecycle-08-decisions.json#8f6f3cf82187, REC-37:
  "F0 field_vocabulary.conclusion_type.allowed lists alias forms (strong_cosmic_censorship_C2/_C0)
   while VOCAB_ALIASES.json declares scc_c2/scc_c0_future_inextendibility canonical and rule_spec
   R11 requires the canonical token; ... discharged by a pinned crosswalk artifact plus a
   consistency check against the registry mapping, never by a write to
   research_map/formulation_taxonomy.yaml (which voids G-F0)."

The builder writes ``crosswalk.json`` (non-canonical candidate; proposed pin target
``artifacts/formulation/VOCAB_CROSSWALK.json``). It never edits a canonical path and never
sets a node status, validation_status or gate verdict.

Extraction is intentionally literal (YAML path -> value) and sorted, so the output bytes are a
pure function of the pinned input bytes. The checker (check_rec37_crosswalk_047.py) re-derives
the same table with an independent implementation and is the artifact that fails closed.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "crosswalk.json"

PINS = {
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/formulation/VOCAB_ALIASES.json": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "artifacts/formulation/rule_spec.json": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/evidence/taxonomy_consistency.json": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
}

CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
KINDS = ["conclusion_type", "genericity_kind"]


def sha256_file(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def load(rel: str):
    text = (ROOT / rel).read_text(encoding="utf-8")
    if rel.endswith(".json"):
        return json.loads(text)
    return yaml.safe_load(text)


def canon(registry: dict, kind: str, token):
    """Registry mapping: canonical key -> itself; listed alias -> its canonical; else None.

    ``unresolved`` is the F0-declared sentinel for a not-yet-owned axis; it is not a token and
    is therefore reported as kind ``sentinel`` rather than as an unmapped token.
    """
    if token is None:
        return None, "absent"
    if token == "unresolved" and kind == "genericity_kind":
        return None, "sentinel"
    if kind not in registry:
        return None, "unmapped"
    for canonical, aliases in registry[kind].items():
        if token == canonical:
            return canonical, "canonical"
        if token in aliases:
            return canonical, "alias"
    return None, "unmapped"


def surface(path, rel, yaml_path, class_id, kind, token, role):
    canonical, token_kind = canon(REG, kind, token)
    return {
        "path": path,
        "sha256": PINS[rel],
        "yaml_path": yaml_path,
        "class_id": class_id,
        "kind": kind,
        "token": token,
        "canonical": canonical,
        "token_kind": token_kind,
        "role": role,
    }


def main() -> int:
    bad = [p for p, h in PINS.items() if sha256_file(p) != h]
    if bad:
        print("PIN DRIFT, refusing to build:", bad, file=sys.stderr)
        return 2

    global REG
    REG = load("artifacts/formulation/VOCAB_ALIASES.json")
    f0 = load("research_map/formulation_taxonomy.yaml")
    sup = load("artifacts/formulation/formulation_taxonomy.yaml")
    rule = load("artifacts/formulation/rule_spec.json")
    schemas = {
        "AF-WCC-VAC-GEN": load("schemas/af_wcc_vacuum.yaml"),
        "AF-SCC-C2-VAC-GEN": load("schemas/af_scc_c2_vacuum.yaml"),
        "AF-SCC-C0-VAC-GEN": load("schemas/af_scc_c0_vacuum.yaml"),
    }

    surfaces = []
    for kind in KINDS:
        allowed = (f0.get("field_vocabulary", {}).get(kind, {}) or {}).get("allowed", [])
        for i, tok in enumerate(allowed):
            surfaces.append(surface("F0 taxonomy", "research_map/formulation_taxonomy.yaml",
                                    f"field_vocabulary.{kind}.allowed[{i}]", None, kind, tok, "allowed_list"))
    for cid in CLASSES:
        cls = f0["classes"].get(cid, {})
        surfaces.append(surface("F0 taxonomy", "research_map/formulation_taxonomy.yaml",
                                f"classes.{cid}.axes.conclusion_type", cid, "conclusion_type",
                                (cls.get("axes") or {}).get("conclusion_type"), "value"))
        surfaces.append(surface("F0 taxonomy", "research_map/formulation_taxonomy.yaml",
                                f"classes.{cid}.conclusion.type", cid, "conclusion_type",
                                (cls.get("conclusion") or {}).get("type"), "value"))
        surfaces.append(surface("F0 taxonomy", "research_map/formulation_taxonomy.yaml",
                                f"classes.{cid}.axes.genericity_kind", cid, "genericity_kind",
                                (cls.get("axes") or {}).get("genericity_kind"), "value"))

        sc = sup["class_contracts"].get(cid, {})
        surfaces.append(surface("F0 supplement", "artifacts/formulation/formulation_taxonomy.yaml",
                                f"class_contracts.{cid}.conclusion_type", cid, "conclusion_type",
                                sc.get("conclusion_type"), "value"))
        frozen = ((sup.get("axis_registry", {}) or {}).get("genericity_axis", {}) or {}).get("frozen", {}) or {}
        surfaces.append(surface("F0 supplement", "artifacts/formulation/formulation_taxonomy.yaml",
                                f"axis_registry.genericity_axis.frozen.{cid}", cid, "genericity_kind",
                                frozen.get(cid), "value"))

        if cid in schemas:
            sd = schemas[cid]
            surfaces.append(surface("class schema", f"schemas/{ 'af_wcc_vacuum' if cid=='AF-WCC-VAC-GEN' else ('af_scc_c2_vacuum' if cid=='AF-SCC-C2-VAC-GEN' else 'af_scc_c0_vacuum')}.yaml",
                                    "conclusion.conclusion_type", cid, "conclusion_type",
                                    (sd.get("conclusion") or {}).get("conclusion_type"), "value"))
            surfaces.append(surface("class schema", f"schemas/{ 'af_wcc_vacuum' if cid=='AF-WCC-VAC-GEN' else ('af_scc_c2_vacuum' if cid=='AF-SCC-C2-VAC-GEN' else 'af_scc_c0_vacuum')}.yaml",
                                    "genericity.kind", cid, "genericity_kind",
                                    (sd.get("genericity") or {}).get("kind"), "value"))

        surfaces.append(surface("rule_spec", "artifacts/formulation/rule_spec.json",
                                f"vocabularies.class_conclusion_type.{cid}", cid, "conclusion_type",
                                (rule.get("vocabularies", {}) or {}).get("class_conclusion_type", {}).get(cid), "vocabulary"))
    for i, tok in enumerate((rule.get("vocabularies", {}) or {}).get("genericity_kind", [])):
        surfaces.append(surface("rule_spec", "artifacts/formulation/rule_spec.json",
                                f"vocabularies.genericity_kind[{i}]", None, "genericity_kind", tok, "vocabulary"))

    per_class = {}
    for cid in CLASSES:
        entry = {}
        for kind in KINDS:
            vals = {}
            for s in surfaces:
                if s["class_id"] == cid and s["kind"] == kind and s["role"] == "value":
                    vals[s["yaml_path"]] = {"surface": s["path"], "token": s["token"],
                                            "canonical": s["canonical"], "token_kind": s["token_kind"]}
            # Comparison key: the registry canonical when one exists, else the raw sentinel/absent state.
            keys = set()
            for v in vals.values():
                if v["canonical"]:
                    keys.add(("canonical", v["canonical"]))
                elif v["token_kind"] == "sentinel":
                    keys.add(("sentinel", v["token"]))
                elif v["token_kind"] == "unmapped":
                    keys.add(("unmapped", v["token"]))
            entry[kind] = {"surfaces": vals,
                           "distinct_canonicals": sorted(k for t, k in keys if t == "canonical"),
                           "comparison_keys": sorted([list(k) for k in keys]),
                           "unmapped_tokens": sorted(k for t, k in keys if t == "unmapped"),
                           "agreement": len(keys) <= 1}
        per_class[cid] = entry

    # REC-37 alias entries on the frozen F0 surface (the entries that must be crosswalked).
    f0_alias_entries = {}
    unmapped_f0_entries = {}
    alias_map = {k: {a: c for c, al in REG[k].items() for a in al} for k in KINDS}
    for kind in KINDS:
        allowed = (f0.get("field_vocabulary", {}).get(kind, {}) or {}).get("allowed", [])
        f0_alias_entries[kind] = {
            tok: canon(REG, kind, tok)[0] for tok in allowed if canon(REG, kind, tok)[1] == "alias"
        }
        unmapped_f0_entries[kind] = {
            tok: {
                "status": "unmapped_in_registry",
                "token_kind": canon(REG, kind, tok)[1],
                "anagram_alias_candidates": {a: alias_map[kind][a] for a in alias_map[kind]
                                             if sorted(a) == sorted(tok)},
                "requires": "naming adjudication before any registry-mapping consistency check treats this F0 entry as an alias",
            }
            for tok in allowed if canon(REG, kind, tok)[1] in ("unmapped",)
        }

    literal_f0 = {}
    for cid, spath in [("AF-WCC-VAC-GEN", "schemas/af_wcc_vacuum.yaml"),
                       ("AF-SCC-C2-VAC-GEN", "schemas/af_scc_c2_vacuum.yaml"),
                       ("AF-SCC-C0-VAC-GEN", "schemas/af_scc_c0_vacuum.yaml")]:
        tok = ((schemas[cid].get("conclusion") or {}).get("conclusion_type"))
        allowed = (f0.get("field_vocabulary", {}).get("conclusion_type", {}) or {}).get("allowed", [])
        literal_f0[cid] = {"schema_token": tok, "f0_allowed_list": allowed,
                           "literal_membership": tok in allowed,
                           "schema_path": spath}

    crosswalk = {
        "schema_version": "rec37-token-crosswalk/v1",
        "artifact_kind": "conclusion_and_genericity_token_crosswalk",
        "candidate_status": ("NON_CANONICAL CANDIDATE. Proposed pin target artifacts/formulation/VOCAB_CROSSWALK.json. "
                             "Adoption is an owner write and moves formulation bytes; it voids current G-FORM/G-F0 review "
                             "verdicts bound to the old manifest and is therefore the lead-formulation decision."),
        "authority_ruling": {
            "id": "REC-37",
            "record": "runtime/state/controller_verification/astra-lifecycle-08-decisions.json#8f6f3cf82187",
            "ruling": ("class schemas keep scc_* canonical tokens; HF-075-F2a/F2b-VOCAB are alias-vs-canonical "
                       "presentation conflicts discharged by a pinned crosswalk artifact plus a consistency check "
                       "against the registry mapping; never by a write to research_map/formulation_taxonomy.yaml."),
        },
        "policy": ("canonical token first; accepted aliases are equivalent for consistency checks only and must never "
                   "appear in a new canonical artifact (artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534)"),
        "mode": "registry_canonical_mapping",
        "pins": {p: PINS[p] for p in sorted(PINS)},
        "canonical_tokens": {k: sorted(REG[k]) for k in KINDS},
        "alias_map": alias_map,
        "rejected_ambiguous_tokens": REG.get("rejected_ambiguous_tokens", {}),
        "f0_alias_entries": f0_alias_entries,
        "unmapped_f0_entries": unmapped_f0_entries,
        "per_class": per_class,
        "surfaces": surfaces,
        "registry_vs_literal": {
            "registry_mode": "schema token must be the exact VOCAB_ALIASES canonical key; F0 alias entries compare through the registry mapping",
            "literal_mode": "schema token must appear literally in F0 field_vocabulary.<kind>.allowed (assertion-incorrect for rev5 F0; recorded for contrast only)",
            "literal_membership_at_pins": literal_f0,
            "note": ("F0 rev5 is frozen by REC-11/G-F0 and may not be rewritten; the alias forms in F0 are the adjudicated "
                     "state (REC-37, AMB-10 precedent for genericity_kind). "
                     "F-TC-1: F0 field_vocabulary.genericity_kind.allowed carries 'dense_open' while the registry alias is "
                     "'open_dense' (of open_dense_escape); under the registry mapping 'dense_open' is unmapped and is "
                     "recorded under unmapped_f0_entries rather than silently normalized."),
        },
        "sentinels": {
            "unresolved": ("F0 field_vocabulary.genericity_kind.allowed sentinel and F0 scalar-class axis value; not a class "
                           "token and not in VOCAB_ALIASES; no canonicalization is asserted for it"),
        },
        "falsifier": ("Falsified at these pins if (a) any pinned sha256 differs on re-measure; (b) a class schema declares a "
                      "conclusion_type or genericity.kind that is an alias form rather than the VOCAB_ALIASES canonical key; "
                      "(c) the F0 field_vocabulary alias entries do not resolve through the registry to the canonical tokens "
                      "declared by the corresponding class schema; (d) the C0 and C2 canonicals collapse to one token on any "
                      "surface; (e) a rejected_ambiguous_token appears in a value position; (f) rule_spec R11's "
                      "class_conclusion_type vocabulary disagrees with a class schema; or (g) an F0 entry that is unmapped in "
                      "the registry is silently treated as an alias instead of being recorded under unmapped_f0_entries. "
                      "A later canonical write is not a falsifier: it voids the pins and requires re-measurement."),
        "adoption": {
            "proposed_crosswalk_path": "artifacts/formulation/VOCAB_CROSSWALK.json",
            "proposed_checker_path": "artifacts/formulation/tools/check_token_crosswalk.py",
            "source_candidate": "artifacts/worker-047/rec37_token_crosswalk/crosswalk.json",
            "steps": [
                "owner copies crosswalk.json to the proposed crosswalk path and the checker to the proposed tools path",
                "owner rebinds FROZEN rev30 per-file pins to include both new files and re-emits the three mirror pairs",
                "owner runs the checker in registry mode at the new pins and records exit 0 in the rev14 evidence",
                "F0 strong_* alias entries and rule_spec R11 stay unchanged; no F0 taxonomy write",
            ],
            "must_not": ("write research_map/formulation_taxonomy.yaml (voids G-F0), normalize the F0 alias list, or substitute the "
                         "alias tokens into the class schemas (forbidden by the alias policy and failed by rule_spec R11)"),
            "voids": "the byte move voids every G-FORM verdict bound to FROZEN rev29/rev13; r3 re-runs at the new pins",
        },
        "authority_limits": ("Worker artifact. No canonical file was edited; no node status, validation_status=passed or gate "
                             "verdict is claimed. Adoption and pinning belong to astra-lead-formulation inside the authorized "
                             "rev14 (REC-36 item 4)."),
    }
    OUT.write_text(json.dumps(crosswalk, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"written": str(OUT), "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
                      "surfaces": len(surfaces)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
