#!/usr/bin/env python3
"""R3 independent review: build novel mutants not present in the formulation corpus.

All outputs are written next to this script. Sources are the canonical schemas at
artifacts/formulation/schemas/*.yaml. Run from the repo root:

    python3 artifacts/formulation/reviews/novel_mutants/_make_novel_mutants.py
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
CANON = ROOT / "artifacts" / "formulation" / "schemas"
OUT = Path(__file__).resolve().parent


def load(name):
    return yaml.safe_load((CANON / name).read_text())


def dump(doc, name):
    p = OUT / name
    p.write_text(yaml.safe_dump(doc, sort_keys=False, width=110))
    return p


# --- (a) swap class_id values between the two SCC files, bodies unchanged -----------
for src, other_cid, out_name in [
    ("af_scc_c2_vacuum.yaml", "AF-SCC-C0-VAC-GEN", "n01_scc_c2_relabelled_as_c0.yaml"),
    ("af_scc_c0_vacuum.yaml", "AF-SCC-C2-VAC-GEN", "n02_scc_c0_relabelled_as_c2.yaml"),
]:
    d = load(src)
    assert d["class_id"] != other_cid
    d["class_id"] = other_cid
    dump(d, out_name)

# --- (b) empty conclusion.forbidden_strengthenings (WCC) ---------------------------
d = load("af_wcc_vacuum.yaml")
d["conclusion"]["forbidden_strengthenings"] = []
dump(d, "n03_wcc_empty_forbidden_strengthenings.yaml")

# --- (c) "C0 or C2" inside YAML comments only (text insertion, doc unchanged) -------
raw = (CANON / "af_wcc_vacuum.yaml").read_text()
anchor = "regularity:\n"
assert raw.count(anchor) >= 1, "anchor not found"
inject = ("# NOTE (R3 probe): the extension regularity is C0 or C2 depending on the\n"
          "# branch; composite regularity C0 or C2 is intended here.\n")
# insert before the top-level regularity block (first occurrence at column 0)
lines = raw.splitlines(keepends=True)
idx = next(i for i, ln in enumerate(lines) if ln.rstrip("\n") == "regularity:")
lines[idx:idx] = [inject]
(OUT / "n04_wcc_composite_only_in_comment.yaml").write_text("".join(lines))

# --- (d) SCC-style/WCC-style meaning in an unscanned prose field --------------------
# non_vacuity.condition is NOT in check_class_schema.ASSERTIVE_PATHS and is not
# composite-scanned; put an unmistakably WCC statement into the C2 SCC schema.
d = load("af_scc_c2_vacuum.yaml")
d["non_vacuity"]["condition"] = (
    "Weak cosmic censorship must hold for this data: for a generic AF vacuum development "
    "no observer who escapes to infinity is hidden from the breakdown of asymptotic "
    "predictability, and a visible singularity is required for a counterexample; a "
    "Cauchy horizon is what the class forbids."
)
dump(d, "n05_scc_wcc_meaning_in_nonvacuity_condition.yaml")

# --- (e) EXTRA: R16 ledger with the converse entailment (keys still non-empty) ------
d = load("af_scc_c2_vacuum.yaml")
d["implication_ledger"]["one_way_entailments"] = [{
    "from": "no proper future C2 extension",
    "to": "no proper future C0 extension",
    "relation": "entails",
    "reason": "R3 probe: the CONVERSE of the intended one-way statement",
    "status": "elementary",
}]
dump(d, "n06_scc_ledger_converse_entailment.yaml")

# --- (f) EXTRA: SCC I+ completeness in a key R09 does not scan ----------------------
d = load("af_scc_c0_vacuum.yaml")
d["i_plus"]["completeness_definition"] = (
    "every generator of I+ is complete: it is defined for all values of the affine "
    "parameter, so I+ is future-complete"
)
dump(d, "n07_scc_completeness_in_unscanned_i_plus_key.yaml")

# --- (g) EXTRA: R15 clause 'no source presented as establishing the conclusion' -----
d = load("af_wcc_vacuum.yaml")
d["provenance"]["citation_status"] = "verified"
d["provenance"]["sources"] = [{
    "concept": "R3 probe: a proof that generic AF vacuum data satisfy weak cosmic censorship",
    "identifier": "arXiv:9999.99999",
    "retrieval_date": "2026-09-11",
    "establishes": "the class conclusion",
    "status": "verified",
}]
dump(d, "n08_wcc_provenance_establishes_conclusion.yaml")

print("wrote novel mutants to", OUT)
for p in sorted(OUT.glob("n0*.yaml")):
    print(" ", p.name)
