#!/usr/bin/env python3
"""R03 reading controls for gate rev1.3: semantic realization vs literal substring.

Each control is a full class schema, derived from a frozen canonical schema by an explicit,
auditable quantifier-only mutation.  Nothing else in the document is touched.  The controls are
the falsification surface for the two disclosed readings of R03:

  L (literal, revision 1.2): every declared binder string occurs verbatim in quantifiers.formal.
  S (semantic, revision 1.3): the formal keyword sequence equals the declared kind sequence, and
                             every declared binder variable occurs after its own quantifier.

Expected matrix (asserted by r03_readings_audit.py):
  control                          L      S      why it exists
  c01_c2_kind_reorder              pass   FAIL   declared kinds lie about the sentence's scope
  c02_c2_clause_deleted            pass   FAIL   a whole quantifier clause deleted, vars left in body
  c03_wcc_tuple_variable_unused    FAIL   FAIL   declared pair (q,t0), sentence uses q only
  c04_c2_all_vars_placeholder      FAIL   FAIL   keyword sequence kept, every binder variable replaced
  c05_c2_alpha_rename_consistent   pass   pass   consistent alpha-rename must not be punished
  c06_c2_alpha_rename_inconsistent FAIL   FAIL   rename only in the declaration
  c07_wcc_canonical_tuple_render   FAIL   pass   THE canonical rev13 case: "(q,t0)" rendered q,t0
  c08_c2_canonical                 pass   pass   no false positive on an untouched canonical schema
  c09_c2_extra_body_keyword        pass   FAIL   an extra quantifier keyword changes the scope
  c10_c2_unbound_variable          pass   FAIL   declared variable occurs only before its quantifier

c01/c02/c09 are the under-detection cases: revision 1.2 ACCEPTS them (literal substrings all
present).  c07 is the over-detection case that motivated revision 1.3.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = HERE / "fixtures_r03"
WCC = REPO / "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
C2 = REPO / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def wcc_tail_q(doc):
    q = doc["quantifiers"]
    return q


def build():
    wcc = yaml.safe_load(WCC.read_text())
    c2 = yaml.safe_load(C2.read_text())
    controls = {}

    d = copy.deepcopy(c2)
    o = d["quantifiers"]["ordered"]
    o[0]["kind"], o[1]["kind"] = o[1]["kind"], o[0]["kind"]
    controls["c01_c2_kind_reorder"] = (
        "AF-SCC-C2-VAC-GEN", d, {"L": "pass", "S": "fail", "reason": "declared kinds swapped"})

    d = copy.deepcopy(c2)
    d["quantifiers"]["formal"] = d["quantifiers"]["formal"].replace(
        "not exists a proper future C2 vacuum extension (M',g',iota) of (M,g).",
        "(M',g',iota) is not a proper future C2 vacuum extension of (M,g).")
    controls["c02_c2_clause_deleted"] = (
        "AF-SCC-C2-VAC-GEN", d,
        {"L": "pass", "S": "fail", "reason": "quantifier clause deleted, variables left in body"})

    d = copy.deepcopy(wcc)
    d["quantifiers"]["formal"] = d["quantifiers"]["formal"].replace(
        "not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M.",
        "not exists q in I+ with gamma([0,T)) subset J^-(q) intersect M.")
    controls["c03_wcc_tuple_variable_unused"] = (
        "AF-WCC-VAC-GEN", d, {"L": "fail", "S": "fail", "reason": "t0 declared, never used"})

    d = copy.deepcopy(c2)
    d["quantifiers"]["formal"] = ("forall x in D0: exists Y subset X with Y comeager: "
                                  "forall d in Y: not exists an extension of the development.")
    controls["c04_c2_all_vars_placeholder"] = (
        "AF-SCC-C2-VAC-GEN", d,
        {"L": "fail", "S": "fail", "reason": "kind sequence kept, all declared vars replaced"})

    d = copy.deepcopy(c2)
    d["quantifiers"]["ordered"][1]["binder"] = "H_r"
    d["quantifiers"]["formal"] = d["quantifiers"]["formal"].replace("G_r", "H_r")
    controls["c05_c2_alpha_rename_consistent"] = (
        "AF-SCC-C2-VAC-GEN", d, {"L": "pass", "S": "pass", "reason": "consistent alpha-rename"})

    d = copy.deepcopy(c2)
    d["quantifiers"]["ordered"][1]["binder"] = "H_r"
    controls["c06_c2_alpha_rename_inconsistent"] = (
        "AF-SCC-C2-VAC-GEN", d, {"L": "fail", "S": "fail", "reason": "declaration-only rename"})

    controls["c07_wcc_canonical_tuple_render"] = (
        "AF-WCC-VAC-GEN", copy.deepcopy(wcc),
        {"L": "fail", "S": "pass", "reason": "frozen rev13 WCC tuple binder rendered variable-wise"})

    controls["c08_c2_canonical"] = (
        "AF-SCC-C2-VAC-GEN", copy.deepcopy(c2), {"L": "pass", "S": "pass", "reason": "untouched"})

    d = copy.deepcopy(c2)
    d["quantifiers"]["formal"] = d["quantifiers"]["formal"] + " In addition, exists a witness point."
    controls["c09_c2_extra_body_keyword"] = (
        "AF-SCC-C2-VAC-GEN", d, {"L": "pass", "S": "fail", "reason": "extra quantifier keyword"})

    d = copy.deepcopy(c2)
    d["quantifiers"]["ordered"][3]["binder"] = "M'"
    d["quantifiers"]["formal"] = ("forall r in D0: exists G_r subset X^r_vac(AF) with G_r comeager: "
                                  "forall (Sigma,h,K) in G_r, letting M' be the maximal "
                                  "development (M,g): not exists a proper future C2 vacuum "
                                  "extension of (M,g).")
    controls["c10_c2_unbound_variable"] = (
        "AF-SCC-C2-VAC-GEN", d, {"L": "pass", "S": "fail", "reason": "M' occurs before its quantifier"})

    OUT.mkdir(exist_ok=True)
    manifest = {"note": "R03 reading controls; see module docstring for the expected matrix",
                "bases": {"AF-WCC-VAC-GEN": str(WCC), "AF-SCC-C2-VAC-GEN": str(C2),
                          "base_sha256": {str(WCC): sha256_file(WCC), str(C2): sha256_file(C2)}},
                "controls": {}}
    for name, (cid, doc, exp) in controls.items():
        dst = OUT / f"{name}.yaml"
        dst.write_text(yaml.safe_dump(doc, sort_keys=False, default_flow_style=False,
                                      width=10 ** 9, allow_unicode=True))
        manifest["controls"][name] = {"class_id": cid, "path": str(dst),
                                      "sha256": sha256_file(dst), "expected": exp}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"wrote {len(controls)} controls to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(build())
