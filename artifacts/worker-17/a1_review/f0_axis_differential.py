#!/usr/bin/env python3
"""Supplementary differential: does F1 revision 2 actually agree with F0's axes?

F1's f0_consistency block claims axes_match: true and H1-H5 satisfied. This is an
independent machine check of that claim, using F0 (research_map/formulation_taxonomy.yaml)
as the reference and mapping F1's wording onto F0's axis vocabulary.

Writes f0_axis_differential.json. Not a gate: disagreements in wording are recorded as
wording_mismatch, not as class leakage.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
F0_PATH = ROOT / "research_map" / "formulation_taxonomy.yaml"
F1_PATH = ROOT / "schemas" / "af_wcc_vacuum.yaml"
OUT = HERE / "f0_axis_differential.json"
CID = "AF-WCC-VAC-GEN"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    f0 = yaml.safe_load(F0_PATH.read_text())
    f1 = yaml.safe_load(F1_PATH.read_text())
    axes = f0["classes"][CID]["axes"]
    text = F1_PATH.read_text().lower()

    rows = [
        {"axis": "class_id", "f0": CID, "f1": f1.get("class_id"),
         "agree": f1.get("class_id") == CID},
        {"axis": "family", "f0": axes["family"], "f1": f1["conclusion"].get("family"),
         "agree": axes["family"] == "WCC" and f1["conclusion"].get("family") == "weak_cosmic_censorship"},
        {"axis": "matter_model", "f0": axes["matter_model"], "f1": f1.get("matter", "")[:60],
         "agree": axes["matter_model"] == "vacuum" and "vacuum" in str(f1.get("matter", "")).lower()},
        {"axis": "symmetry", "f0": axes["symmetry"], "f1": f1["topology"].get("symmetry"),
         "agree": axes["symmetry"] == "none_assumed" and "none" in str(f1["topology"].get("symmetry", "")).lower()},
        {"axis": "asymptotics", "f0": axes["asymptotics"],
         "f1": f1["topology"].get("asymptotics", "")[:60],
         "agree": "asymptotically flat" in str(f1["topology"].get("asymptotics", "")).lower()},
        {"axis": "regularity_token", "f0": axes["regularity_token"],
         "f1": "absent (WCC has no extension-regularity token)",
         "agree": axes["regularity_token"] is None and "extension-regularity" in text},
        {"axis": "genericity_kind", "f0": axes["genericity_kind"],
         "f1": f1["genericity"].get("kind", "")[:60],
         "agree": axes["genericity_kind"] == "baire_residual"
                  and "baire" in str(f1["genericity"].get("kind", "")).lower()},
        {"axis": "conclusion_type", "f0": axes["conclusion_type"],
         "f1": f"conclusion.type={f1['conclusion'].get('type')!r}, family={f1['conclusion'].get('family')!r}",
         "agree": f1["conclusion"].get("family") == axes["conclusion_type"]
                  and f1["conclusion"].get("type") == axes["conclusion_type"]},
    ]

    hypotheses = {
        "H1": {"claim": "3+1 dimensional; Lambda = 0",
               "checked": f1["topology"].get("spacetime_dimension") == 4
                          and "cosmological constant" in text,
               "evidence": "topology.spacetime_dimension=4; matter excludes a cosmological constant"},
        "H2": {"claim": "vacuum, T=0",
               "checked": "vacuum" in str(f1.get("matter", "")).lower(),
               "evidence": "matter: vacuum Einstein equations"},
        "H3": {"claim": "constraints, one AF end, MGHD",
               "checked": bool(f1["data_class"].get("constraints"))
                          and "one asymptotically flat end" in str(f1["topology"].get("initial_slice_topology", ""))
                          and bool(f1.get("premise", {}).get("development")),
               "evidence": "data_class.constraints; topology.initial_slice_topology; premise.development"},
        "H4": {"claim": "genericity owned by F1",
               "checked": bool(f1["genericity"].get("kind")) and bool(f1["genericity"].get("topology_name")),
               "evidence": f"genericity.status={f1['genericity'].get('genericity_status')}"},
        "H5": {"claim": "no symmetry assumed",
               "checked": "none" in str(f1["topology"].get("symmetry", "")).lower(),
               "evidence": "topology.symmetry: none assumed"},
    }

    f1_claim = f1.get("f0_consistency", {}).get("axes_match")
    axis_agree = all(r["agree"] for r in rows)
    result = {
        "check": "F1 revision 2 vs F0 AF-WCC-VAC-GEN axes",
        "f0": {"path": "research_map/formulation_taxonomy.yaml", "sha256": sha256(F0_PATH)},
        "f1": {"path": "schemas/af_wcc_vacuum.yaml", "sha256": sha256(F1_PATH),
               "revision": f1.get("revision")},
        "f1_self_claim_axes_match": f1_claim,
        "independent_axes_match": axis_agree,
        "self_claim_verified": bool(f1_claim) == axis_agree,
        "axis_rows": rows,
        "hypotheses": hypotheses,
        "hypotheses_all_checked": all(h["checked"] for h in hypotheses.values()),
        "wording_mismatch": [r["axis"] for r in rows if not r["agree"]],
        "note": ("conclusion_type is a vocabulary mismatch, not a semantic one: F0 uses "
                 "'weak_cosmic_censorship' as the conclusion_type while F1 records type=open_problem "
                 "plus family=weak_cosmic_censorship. Recorded here, reported in the review."),
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("independent_axes_match", "f1_self_claim_axes_match",
                                             "self_claim_verified", "hypotheses_all_checked",
                                             "wording_mismatch")}, indent=2))
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
