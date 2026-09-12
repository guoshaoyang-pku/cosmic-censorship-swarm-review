#!/usr/bin/env python3
"""rev4 delta probes: one targeted mutant per strengthened rule (R09/R12/R15/R16) plus a
geodesic-exemption control. Built deterministically from the frozen canonical schemas.

Purpose (FORM-DIFF-02 follow-up, lead message 2026-09-11T23:33:37): after frozen revision 3/4
the lead gate is stricter on R09 (negation-aware completeness), R12 (widened assertive paths),
R15 (overclaim clause), R16 (ledger direction). These probes measure which of the four
strengthenings MY independent gate implements, before and after the update.

Outputs evidence/probes/*.yaml (deterministic bytes).
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]  # evidence/ -> f1_aux_class_binding/ -> flash-11/ -> artifacts/ -> repo
SCHEMAS = REPO / "artifacts/formulation/schemas"
OUT = HERE / "probes"


def load(name: str) -> dict:
    return yaml.safe_load((SCHEMAS / name).read_text())


def dump(doc: dict, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")


def main() -> int:
    wcc = load("af_wcc_vacuum.yaml")
    scc2 = load("af_scc_c2_vacuum.yaml")

    # P1 R09: SCC i_plus asserts completeness positively (no negation word in the same string)
    d = copy.deepcopy(scc2)
    d["i_plus"]["completeness_definition"] = "every null geodesic generator of I+ is future-complete"
    dump(d, "probe_r09_scc_asserts_completeness.yaml")

    # P2 R12: SCC-style inextendibility injected into a newly-widened assertive path
    d = copy.deepcopy(wcc)
    d["non_vacuity"]["condition"] = (
        str(d["non_vacuity"]["condition"]) + " The maximal development is C^2-inextendible."
    )
    dump(d, "probe_r12_leak_in_nonvacuity_path.yaml")

    # P3 R15: provenance source presented as establishing the class conclusion
    d = copy.deepcopy(wcc)
    srcs = d["provenance"]["sources"]
    srcs[0] = dict(srcs[0])
    srcs[0]["note"] = "this work establishes the class conclusion"
    dump(d, "probe_r15_overclaim_source.yaml")

    # P4 R16: ledger asserts the forbidden converse C2 => C0
    d = copy.deepcopy(scc2)
    d["implication_ledger"]["one_way_entailments"] = list(d["implication_ledger"]["one_way_entailments"]) + [
        {"from": "no proper future C2 extension", "to": "no proper future C0 extension"}
    ]
    dump(d, "probe_r16_forbidden_converse.yaml")

    # P5 control: the canonical WCC usage "future-inextendible causal geodesic" must NOT be flagged
    dump(copy.deepcopy(wcc), "probe_r12_geodesic_control_accept.yaml")

    manifest = {
        "probes": [
            {"file": "probe_r09_scc_asserts_completeness.yaml", "expect_fail_rule": "R09"},
            {"file": "probe_r12_leak_in_nonvacuity_path.yaml", "expect_fail_rule": "R12"},
            {"file": "probe_r15_overclaim_source.yaml", "expect_fail_rule": "R15"},
            {"file": "probe_r16_forbidden_converse.yaml", "expect_fail_rule": "R16"},
            {"file": "probe_r12_geodesic_control_accept.yaml", "expect_fail_rule": None},
        ]
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("wrote", len(manifest["probes"]), "probes to", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
