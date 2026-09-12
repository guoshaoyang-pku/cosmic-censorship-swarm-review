#!/usr/bin/env python3
"""Deterministically build the negative + adversarial fixture corpus.

Reads the four ACCEPT fixtures in fixtures/ and writes:
  fixtures/bad_*.yaml            -- one targeted violation each (must REJECT)
  fixtures/adv_*.yaml            -- adversarial cases expected to ESCAPE (falsifier evidence)
  fixtures/EXPECTATIONS.json     -- machine-readable expected verdicts

Every fixture is derived from a named base document; re-running this script
reproduces identical bytes (no RNG, sorted keys disabled, fixed field order).
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"


def load(name: str) -> dict:
    return yaml.safe_load((FIX / name).read_text(encoding="utf-8"))


def dump(doc: dict, name: str) -> None:
    (FIX / name).write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")


def main() -> int:
    wcc = load("good_af_wcc_vac_gen.yaml")
    scc2 = load("good_af_scc_c2_vac_gen.yaml")
    scc0 = load("good_af_scc_c0_vac_gen.yaml")
    scalar = load("good_af_wcc_scalar_sph.yaml")

    expectations: dict[str, dict] = {}

    def bad(name: str, base: dict, mutate, codes: list[str]) -> None:
        doc = copy.deepcopy(base)
        mutate(doc)
        dump(doc, name)
        expectations[name] = {"verdict": "REJECT", "must_include": codes, "base": None}

    def adv(name: str, base: dict, mutate, note: str) -> None:
        doc = copy.deepcopy(base)
        mutate(doc)
        dump(doc, name)
        expectations[name] = {"verdict": "ACCEPT", "kind": "expected_escape", "must_include": [], "note": note}

    # --- one violation per check -------------------------------------------------
    def m1(d): del d["class_id"]
    bad("bad_01_missing_class_id.yaml", wcc, m1, ["CLASS_ID"])

    def m2(d): d["class_id"] = "AF-WCC-VAC-GEN-EXTRA"
    bad("bad_02_unknown_class_id.yaml", wcc, m2, ["CLASS_ID"])

    def m3(d): d["conclusion"]["statement"] = "the maximal development is C^0 or C^2 inextendible"
    bad("bad_03_c0_or_c2.yaml", scc2, m3, ["CONJUNCTION"])

    def m4(d): d["quantifiers"]["forall"] = "for all suitable asymptotically flat vacuum data"
    bad("bad_04_vague_quantifiers.yaml", wcc, m4, ["QUANTIFIERS"])

    def m5(d): del d["topology"]
    bad("bad_05_missing_topology.yaml", wcc, m5, ["TOPOLOGY"])

    def m6(d): del d["data_class"]
    bad("bad_06_missing_data_class.yaml", wcc, m6, ["DATA_CLASS"])

    def m7(d): d["genericity"] = {"kind": "generic", "parameter_space": ""}
    bad("bad_07_bare_generic.yaml", wcc, m7, ["GENERICITY"])

    def m8(d): del d["i_plus"]
    bad("bad_08_missing_iplus.yaml", wcc, m8, ["I_PLUS"])

    def m9(d): d["conclusion"]["type"] = "remark"
    bad("bad_09_bad_conclusion_type.yaml", wcc, m9, ["CONCLUSION_TYPE"])

    def m10(d): d["conclusion"]["statement"] = "the maximal development is C^2-inextendible"
    bad("bad_10_wcc_concludes_inextendibility.yaml", wcc, m10, ["SCOPE_SEPARATION"])

    def m11(d): d["conclusion"]["statement"] = "no naked singularity is visible from future null infinity"
    bad("bad_11_scc_concludes_visibility.yaml", scc2, m11, ["SCOPE_SEPARATION"])

    def m12(d): d["matter"] = "vacuum Einstein equations plus a scalar field with potential V(phi)"
    bad("bad_12_vacuum_with_scalar_matter.yaml", wcc, m12, ["MATTER"])

    def m13(d):
        d["inextendibility"]["regularity"] = "C^0"
        d["inextendibility"]["statement"] = "the maximal development is C^0-inextendible"
    bad("bad_13_scc_c2_with_c0_extension.yaml", scc2, m13, ["INEXTENDIBILITY"])

    def m14(d): d["data_class"]["regularity"] = "regular enough"
    bad("bad_14_no_regularity_symbol.yaml", wcc, m14, ["DATA_CLASS"])

    # empty / garbage documents (null controls; no base needed)
    (FIX / "bad_15_empty.yaml").write_text("", encoding="utf-8")
    expectations["bad_15_empty.yaml"] = {"verdict": "REJECT", "must_include": ["DOC_SHAPE"], "base": None}
    (FIX / "bad_16_garbage.yaml").write_text("this is not a schema\n", encoding="utf-8")
    expectations["bad_16_garbage.yaml"] = {"verdict": "REJECT", "must_include": ["DOC_SHAPE"], "base": None}

    # --- adversarial cases: expected to escape, reported honestly ----------------
    # adv_01 from the first campaign ("cannot be isometrically embedded ...") was
    # caught after lexicon hardening and is now locked as bad_17.
    def b17(d):
        d["conclusion"]["statement"] = (
            "the maximal development cannot be isometrically embedded into any larger "
            "C^2 Lorentzian manifold"
        )
    bad("bad_17_paraphrased_scc_leak.yaml", wcc, b17, ["SCOPE_SEPARATION"])

    vacuous = {
        "class_id": "AF-WCC-VAC-GEN",
        "quantifiers": {"forall": "for all x", "exists": "there exists y"},
        "topology": {"dimension": 4, "manifold": "a 4-dimensional Lorentzian manifold"},
        "data_class": {"regularity": "C^2", "weighted_norm": "weight w", "decay": "decay"},
        "matter": "vacuum",
        "genericity": {"kind": "open dense", "parameter_space": "the space"},
        "i_plus": {"visibility": "visible from I+"},
        "conclusion": {"type": "theorem", "statement": "for all x, no singularity is visible from I+"},
    }
    dump(vacuous, "adv_02_vacuous_wellformed.yaml")
    expectations["adv_02_vacuous_wellformed.yaml"] = {
        "verdict": "ACCEPT",
        "kind": "expected_escape",
        "must_include": [],
        "note": "all required sections present but content is tautological; presence checks cannot detect vacuity",
    }

    def a3(d):
        d["future_regularity"] = "the maximal development is C^2-inextendible"
    adv(
        "adv_03_alias_smuggling.yaml",
        wcc,
        a3,
        "SCC content smuggled into an unrecognised field; linter scans only declared sections",
    )

    def a4(d):
        d["conclusion"]["statement"] = "distant observers remain unaware of the collapse"
    adv(
        "adv_04_residual_wcc_paraphrase.yaml",
        scc2,
        a4,
        "WCC conclusion paraphrase absent from the v2 lexicon; documents residual lexical incompleteness",
    )

    def a5(d):
        d["conclusion"]["statement"] = "the development is maximal with respect to C^2 embeddings"
    adv(
        "adv_05_residual_scc_paraphrase.yaml",
        wcc,
        a5,
        "SCC conclusion paraphrase absent from the v2 lexicon; documents residual lexical incompleteness",
    )

    (FIX / "EXPECTATIONS.json").write_text(json.dumps(expectations, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    n_bad = sum(1 for k in expectations if k.startswith("bad_"))
    n_adv = sum(1 for k in expectations if k.startswith("adv_"))
    print(f"wrote {n_bad} negative fixtures, {n_adv} adversarial fixtures, EXPECTATIONS.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
