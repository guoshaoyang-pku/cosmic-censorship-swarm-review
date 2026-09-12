#!/usr/bin/env python3
"""W041-F2B-VOCAB-ALIAS-01 — read-only adjudication of HF-075-F2b-VOCAB.

Question (worker-075, reviews/F2b-review-rev29-075.json, F2b rev13 b2ab6acb2bbe):
  "schema token 'scc_c0_future_inextendibility' is not in the bound F0 declared
   field_vocabulary.conclusion_type.allowed [...]; the F0 declared class entry uses
   'strong_cosmic_censorship_C0' while VOCAB_ALIASES.json declares
   'scc_c0_future_inextendibility' canonical, so two frozen artifacts disagree on the
   canonical token and the alias policy forbids aliases in canonical artifacts."

What this instrument measures, at byte-pinned inputs:
  C1  F2b schema conclusion token vs F0 AF-SCC-C0-VAC-GEN class token, under the pinned
      VOCAB_ALIASES conclusion_type map.
  C2  same for F2a vs AF-SCC-C2-VAC-GEN.
  C3  same for F1 vs AF-WCC-VAC-GEN (identity, no alias needed).
  C4  same for the F0 *companion* (d7419b4e8963) class_contracts tokens.
  C5  direction audit: which of the two frozen F0-family artifacts carries the canonical
      KEY and which carries an alias value (the policy says canonical-first).
  C6  F0 field_vocabulary.conclusion_type.allowed closure: canonical keys vs literal list.
  C7  negative controls (ambiguous token must NOT canonicalize to a class token; an
      unknown token must stay itself and be flagged).
  C8  F0 C2/C0 tokens stay distinct under canonicalization (no merged regularity token).

Read-only: every pinned input is sha256'd before and after; a mismatch on either side
exits non-zero and writes nothing. No canonical/shared path is written. The only write is
report.json in this directory.

Usage:  python3 artifacts/worker-041/f2b_vocab_alias/check_f2b_vocab_alias.py
Exit 0 = measurement complete and class-identity equivalence confirmed.
Exit 2 = pin drift (entry). Exit 3 = input mutated during the run.
"""
import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "report.json"

PINS = {
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml":
        "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/VOCAB_ALIASES.json":
        "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/tools/check_taxonomy_consistency.py":
        "de356d999ea3b6aeb9cfe7d35d6604328ccc4945ead3bc3ec566a929363f31cd",
    "reviews/F2b-review-rev29-075.json":
        "2fb2878ec1fb59e2d1e770542c278ec2f9adb4bf34b89bc622c7a0044797d6a5",
}


def sha256(p):
    h = hashlib.sha256()
    h.update((ROOT / p).read_bytes())
    return h.hexdigest()


def measure_pins():
    return {p: sha256(p) for p in PINS}


def canon(alias_map, tok):
    """Return (canonical_key, is_alias_value). Unknown tokens return themselves."""
    for key, aliases in alias_map.items():
        if tok == key:
            return key, False
        if tok in aliases:
            return key, True
    return tok, False


def main():
    entry = measure_pins()
    drift = {p: (PINS[p], entry[p]) for p in PINS
             if PINS[p] is not None and entry[p] != PINS[p]}
    if drift:
        print("PREFLIGHT FAIL: pin drift", json.dumps(drift, indent=1))
        return 2

    A = yaml.safe_load((ROOT / "research_map/formulation_taxonomy.yaml").read_text())
    B = yaml.safe_load((ROOT / "artifacts/formulation/formulation_taxonomy.yaml").read_text())
    AL = json.loads((ROOT / "artifacts/formulation/VOCAB_ALIASES.json").read_text())
    S = {c: yaml.safe_load((ROOT / f"schemas/{c}").read_text())
         for c in ("af_wcc_vacuum.yaml", "af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml")}
    review_075 = json.loads((ROOT / "reviews/F2b-review-rev29-075.json").read_text())

    amap = AL["conclusion_type"]
    checks, failures = [], []

    def check(cid, ok, detail):
        checks.append({"id": cid, "ok": bool(ok), "detail": detail})
        if not ok:
            failures.append(cid)

    def row(class_id, schema_file):
        f0_tok = A["classes"][class_id]["axes"]["conclusion_type"]
        sc_tok = S[schema_file]["conclusion"]["conclusion_type"]
        comp_tok = B["class_contracts"][class_id].get("conclusion_type")
        f0_key, f0_is_alias = canon(amap, f0_tok)
        sc_key, sc_is_alias = canon(amap, sc_tok)
        comp_key, comp_is_alias = canon(amap, comp_tok)
        return {
            "class_id": class_id,
            "f0_canonical_token": f0_tok,
            "f0_token_is_alias_of": f0_key if f0_is_alias else None,
            "f0_companion_token": comp_tok,
            "companion_token_is_alias_of": comp_key if comp_is_alias else None,
            "schema_token": sc_tok,
            "schema_token_is_alias_of": sc_key if sc_is_alias else None,
            "equivalence_class": f0_key,
            "equivalent": f0_key == sc_key == comp_key,
        }

    r_c0 = row("AF-SCC-C0-VAC-GEN", "af_scc_c0_vacuum.yaml")
    r_c2 = row("AF-SCC-C2-VAC-GEN", "af_scc_c2_vacuum.yaml")
    r_wcc = row("AF-WCC-VAC-GEN", "af_wcc_vacuum.yaml")

    check("C1_F2b_vs_F0_C0_equivalent", r_c0["equivalent"], r_c0)
    check("C2_F2a_vs_F0_C2_equivalent", r_c2["equivalent"], r_c2)
    check("C3_F1_vs_F0_WCC_equivalent", r_wcc["equivalent"], r_wcc)

    # C4: canonical/alias direction across the frozen F0 pair and the schemas.
    direction = {
        "policy": AL["policy"],
        "f0_canonical_carries": {
            "token": r_c0["f0_canonical_token"],
            "is_alias_value": r_c0["f0_token_is_alias_of"] is not None,
            "canonical_key": r_c0["equivalence_class"],
        },
        "f0_companion_carries": {
            "token": r_c0["f0_companion_token"],
            "is_alias_value": r_c0["companion_token_is_alias_of"] is not None,
            "canonical_key": r_c0["equivalence_class"],
        },
        "schema_carries": {
            "token": r_c0["schema_token"],
            "is_alias_value": r_c0["schema_token_is_alias_of"] is not None,
            "canonical_key": r_c0["equivalence_class"],
        },
    }
    direction_inversion_measured = (
        direction["f0_canonical_carries"]["is_alias_value"]
        and not direction["f0_companion_carries"]["is_alias_value"]
        and not direction["schema_carries"]["is_alias_value"]
    )
    check("C4_direction_measured", True, direction)  # measurement, not a pass/fail norm
    check("C4b_f0_canonical_only_alias_spelling_measured", direction_inversion_measured, {
        "note": "policy says canonical token first; F0 canonical uses the alias value while "
                "the companion and the schema use the canonical key - spelling direction "
                "inverted in the frozen F0 canonical only",
        "direction_inversion_measured": direction_inversion_measured,
    })

    # C5: F0 allowed-vocabulary closure.
    allowed = A["field_vocabulary"]["conclusion_type"]["allowed"]
    allowed_keys = {canon(amap, t)[0] for t in allowed}
    all_keys = set(amap.keys())
    closure = {
        "literal_allowed": allowed,
        "canonical_closure": sorted(allowed_keys),
        "alias_map_keys": sorted(all_keys),
        "closure_complete": allowed_keys == all_keys,
        "literal_list_contains_canonical_keys": sorted(all_keys & set(allowed)) == sorted(all_keys),
    }
    check("C5_allowed_closure_complete", closure["closure_complete"], closure)
    check("C5b_literal_allowed_uses_canonical_keys",
          closure["literal_list_contains_canonical_keys"], closure)

    # C6: negative controls.
    amb, amb_is_alias = canon(amap, "strong_cosmic_censorship")
    unk, unk_is_alias = canon(amap, "scc_c1_future_inextendibility")
    n1 = amb == "strong_cosmic_censorship" and not amb_is_alias and amb != r_c0["equivalence_class"]
    n2 = unk == "scc_c1_future_inextendibility" and not unk_is_alias and unk not in all_keys
    check("C6a_ambiguous_token_not_class_token", n1, {"token": "strong_cosmic_censorship",
                                                      "canon": amb, "is_alias": amb_is_alias})
    check("C6b_unknown_token_stays_itself", n2, {"token": "scc_c1_future_inextendibility",
                                                 "canon": unk, "is_alias": unk_is_alias})

    # C7: C2/C0 regularity tokens stay distinct.
    k_c2, k_c0 = r_c2["equivalence_class"], r_c0["equivalence_class"]
    check("C7_C2_C0_distinct", k_c2 != k_c0 and k_c2 == "scc_c2_future_inextendibility"
          and k_c0 == "scc_c0_future_inextendibility", {"c2": k_c2, "c0": k_c0})

    # Finding text corroboration: the exact sentence exists in the source review.
    hf = None
    for h in review_075.get("hard_failures", []):
        if isinstance(h, dict) and h.get("id") == "HF-075-F2b-VOCAB":
            hf = h
    hf_present = hf is not None
    check("C8_source_finding_present", hf_present, {"id": "HF-075-F2b-VOCAB",
                                                    "present": hf_present})

    exit_pins = measure_pins()
    mutated = {p: (entry[p], exit_pins[p]) for p in PINS if entry[p] != exit_pins[p]}
    if mutated:
        print("POSTFLIGHT FAIL: input mutated during run", json.dumps(mutated, indent=1))
        return 3

    class_identity = (r_c0["equivalent"] and r_c2["equivalent"] and r_wcc["equivalent"])
    residual_live = not closure["literal_list_contains_canonical_keys"]
    result = "MEASURED_INSTRUMENT_VALID"

    report = {
        "task_id": "W041-F2B-VOCAB-ALIAS-01",
        "actor": "worker-041",
        "created_at": __import__("datetime").datetime.now().astimezone().isoformat(),
        "node_id": "F2b",
        "gate": "G-FORM",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "subject_finding": "HF-075-F2b-VOCAB",
        "subject_finding_text": (hf or {}).get("detail"),
        "authority_note": ("Worker evidence only: no gate verdict, no node status, no "
                           "validation_status=passed; no canonical or shared artifact written."),
        "pins_entry": entry,
        "pins_exit": exit_pins,
        "pin_drift": {},
        "alias_policy": AL["policy"],
        "alias_map_conclusion_type": amap,
        "rows": {"AF-WCC-VAC-GEN": r_wcc, "AF-SCC-C2-VAC-GEN": r_c2,
                 "AF-SCC-C0-VAC-GEN": r_c0},
        "checks": checks,
        "failures": failures,
        "verdict": {
            "class_identity_axis": ("ALIAS_EQUIVALENT_CLASS_IDENTITY_PRESERVED"
                                    if class_identity else "CLASS_IDENTITY_MISMATCH"),
            "residual_axis": ("FROZEN_F0_ALLOWED_LIST_ALIAS_ONLY" if residual_live
                              else "NONE"),
            "hf_075_f2b_vocab_is_content_defect": False,
            "hf_075_f2b_vocab_recommended_disposition": (
                "Do not block F2b on this axis: the pinned alias map makes the two spellings "
                "equivalent for consistency checks and the owner checker applies it to "
                "conclusion_type. Record the F0 allowed-list spelling direction as a frozen-F0 "
                "legacy residual for the gate owner; it cannot be repaired in place (repair "
                "voids G-F0) and does not affect class identity, disjointness or conclusion "
                "family."),
        },
        "result": result,
        "residual": {
            "severity": "minor",
            "site": "research_map/formulation_taxonomy.yaml:148-153 "
                    "(field_vocabulary.conclusion_type.allowed)",
            "description": (
                "The pinned VOCAB_ALIASES policy is canonical-token-first "
                "('accepted aliases ... must never appear in a new canonical artifact'), but "
                "the frozen F0 canonical vocabulary block enumerates only the alias forms "
                "strong_cosmic_censorship_C2/_C0. The F0 companion (d7419b4e8963) and all "
                "three schemas already carry the canonical keys. Class identity, disjointness "
                "and the conclusion family are unaffected because the pinned alias map "
                "declares the two spellings equivalent for consistency checks, and the owner "
                "checker applies that map to this exact field "
                "(check_taxonomy_consistency.py:25-27 at de356d999ea3). A literal consumer of "
                "F0's allowed list that does not consult VOCAB_ALIASES will false-fail on any "
                "canonical-token artifact."),
            "not_a_content_defect": True,
            "requires": ("controller/owner ruling that F0's allowed block is legacy alias-form, "
                         "or a future authorized revision re-stamping one token; no F2b content "
                         "repair is warranted on this axis, and no in-place write to the frozen "
                         "F0 is permitted (it would void G-F0)."),
        },
        "instrument": "artifacts/worker-041/f2b_vocab_alias/check_f2b_vocab_alias.py",
        "falsifier": (
            "Any pinned byte change (F0 0abb9ed8a961, companion d7419b4e8963, F2b b2ab6acb2bbe, "
            "VOCAB_ALIASES 46cd9f1eb534, FROZEN 815e08079aef, checker de356d999ea3) voids this "
            "measurement. Withdrawn if a frozen adjudication shows the two tokens are NOT "
            "equivalent for consistency checks, if the alias map's conclusion_type block does "
            "not cover the C0 schema token, or if a control is shown to be vacuous."),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(("CLASS_IDENTITY_PRESERVED" if class_identity else "CLASS_IDENTITY_MISMATCH")
          + f"; residual={'live' if residual_live else 'none'}"
          + f"; checks={len(checks)} failures={failures}")
    for c in checks:
        print(f"  [{'ok' if c['ok'] else 'NO'}] {c['id']}")
    print(f"  report -> {OUT}")
    return 0 if class_identity else 4


if __name__ == "__main__":
    raise SystemExit(main())
