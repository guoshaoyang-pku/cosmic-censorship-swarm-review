#!/usr/bin/env python3
"""Rebased rev19 probes: regenerate the rev4 delta probes from the CURRENT frozen
canonical schemas, because the rev4-era probes were deepcopies of the then-canonical
WCC schema and inherited a structural defect (a `transfers` row inside
`transfer_failures`) that the rev19 rule R28 correctly rejects.

Goal: separate the stale-base confound from the actual R12 measurement.
  control  = current frozen WCC verbatim                -> expected accept
  leak     = current frozen WCC + R12 leak sentence     -> expected reject (R12)
  r09/r15/r16 = current frozen base + the same mutation -> expected reject (R09/R15/R16)

Deterministic output: evidence/probes_rev19/*.yaml + manifest.json.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SCHEMAS = REPO / "artifacts/formulation/schemas"
OUT = HERE / "probes_rev19"


def load(name: str) -> dict:
    return yaml.safe_load((SCHEMAS / name).read_text())


def dump(doc: dict, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")


def main() -> int:
    wcc = load("af_wcc_vacuum.yaml")
    scc2 = load("af_scc_c2_vacuum.yaml")

    dump(copy.deepcopy(wcc), "probe_r12_geodesic_control_accept.yaml")

    d = copy.deepcopy(wcc)
    d["non_vacuity"]["condition"] = (
        str(d["non_vacuity"]["condition"]) + " The maximal development is C^2-inextendible."
    )
    dump(d, "probe_r12_leak_in_nonvacuity_path.yaml")

    d = copy.deepcopy(scc2)
    d["i_plus"]["completeness_definition"] = "every null geodesic generator of I+ is future-complete"
    dump(d, "probe_r09_scc_asserts_completeness.yaml")

    d = copy.deepcopy(wcc)
    srcs = d["provenance"]["sources"]
    srcs[0] = dict(srcs[0])
    srcs[0]["note"] = "this work establishes the class conclusion"
    dump(d, "probe_r15_overclaim_source.yaml")

    d = copy.deepcopy(scc2)
    d["implication_ledger"]["one_way_entailments"] = list(d["implication_ledger"]["one_way_entailments"]) + [
        {"from": "no proper future C2 extension", "to": "no proper future C0 extension"}
    ]
    dump(d, "probe_r16_forbidden_converse.yaml")

    manifest = {
        "rebased_from": "artifacts/formulation/schemas/*.yaml at the FROZEN revision current at run time",
        "why": "rev4-era probes were deepcopies of the rev4 canonical schema and carried its transfer-container defect; R28 rejects both, confounding the R12 measurement",
        "probes": [
            {"file": "probe_r12_geodesic_control_accept.yaml", "expect_fail_rule": None},
            {"file": "probe_r12_leak_in_nonvacuity_path.yaml", "expect_fail_rule": "R12"},
            {"file": "probe_r09_scc_asserts_completeness.yaml", "expect_fail_rule": "R09"},
            {"file": "probe_r15_overclaim_source.yaml", "expect_fail_rule": "R15"},
            {"file": "probe_r16_forbidden_converse.yaml", "expect_fail_rule": "R16"},
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("wrote", len(manifest["probes"]), "rebased probes to", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
