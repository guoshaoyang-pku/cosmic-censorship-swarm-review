#!/usr/bin/env python3
"""W062-GFORM-R03V2-SCOPE-REPLICATION-01 -- freeze predictions BEFORE running candidates.

Run order enforced by file hashes: make_fixtures.py -> preregister.py -> run_replication.py.
PREREGISTRATION.json is written here and is read (never rewritten) by the harness.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")


def sha256_path(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


PRED = {
    "ctrl_canonical_wcc.yaml": {"frozen": "reject", "cand_r03v2": "accept",
                                "cand_004": "accept", "cand_E3": "accept"},
    "ctrl_canonical_f2a.yaml": {"frozen": "accept", "cand_r03v2": "accept",
                                "cand_004": "accept", "cand_E3": "accept"},
    "ctrl_canonical_f2b.yaml": {"frozen": "accept", "cand_r03v2": "accept",
                                "cand_004": "accept", "cand_E3": "accept"},
    "pos_for_which.yaml": {"frozen": "reject", "cand_r03v2": "accept",
                           "cand_004": "accept", "cand_E3": "accept"},
    "pos_interval_words.yaml": {"frozen": "reject", "cand_r03v2": "accept",
                                "cand_004": "accept", "cand_E3": "accept"},
    "pos_long_span_40.yaml": {"frozen": "reject", "cand_r03v2": "accept",
                              "cand_004": "accept", "cand_E3": "accept"},
    # the four adversarial families: cand_r03v2 predicted to ACCEPT all four scope errors
    "neg_free_in_restriction.yaml": {"frozen": "reject", "cand_r03v2": "accept",
                                     "cand_004": "accept", "cand_E3": "accept"},
    "neg_free_predicate.yaml": {"frozen": "reject", "cand_r03v2": "accept",
                                "cand_004": "accept", "cand_E3": "accept"},
    "neg_wrong_clause_cobind.yaml": {"frozen": "reject", "cand_r03v2": "accept",
                                     "cand_004": "accept", "cand_E3": "accept"},
    "neg_head_paren_aside.yaml": {"frozen": "reject", "cand_r03v2": "accept",
                                  "cand_004": "accept", "cand_E3": "accept"},
    "edge_span_79.yaml": {"frozen": "reject", "cand_r03v2": "accept",
                          "cand_004": "accept", "cand_E3": "accept"},
    "edge_span_80.yaml": {"frozen": "reject", "cand_r03v2": "accept",
                          "cand_004": "accept", "cand_E3": "accept"},
    "edge_span_81.yaml": {"frozen": "reject", "cand_r03v2": "reject",
                          "cand_004": "accept", "cand_E3": "accept"},
    "edge_span_120.yaml": {"frozen": "reject", "cand_r03v2": "reject",
                           "cand_004": "accept", "cand_E3": "accept"},
}

PINS = {
    "schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/rule_spec.json":
        "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/worker-06/spec_conformance_audit.py":
        "c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec",
    "artifacts/worker-004/f1_r03_repair/patched/spec_conformance_audit.py":
        "645eb16a006061a63a19772dff0a01d1c5f68131cd30aeaec3fa4094c01334d3",
    "artifacts/worker-064/r03_cause/work/cand_E3/artifacts/worker-06/spec_conformance_audit.py":
        "3f69bc1eb27adf3a3318b893364018112fa8eff0ee312c7fe825dd579cfc5703",
    "artifacts/worker-06/r03v2/audit_r03v2.py":
        "e41a4b23a840fc7f671068fc876f2e36539fe3d9581fbfe23ce3da9ca624ed46",
    "artifacts/worker-06/r03topic_placeholder": None,
}
PINS.pop("artifacts/worker-06/r03topic_placeholder")


def main() -> None:
    manifest = json.loads((HERE / "fixture_manifest.json").read_text())
    fixture_names = [f["fixture"] for f in manifest["fixtures"]]
    missing = [n for n in fixture_names if n not in PRED]
    extra = [n for n in PRED if n not in fixture_names]
    if missing or extra:
        raise SystemExit(f"FAIL: prediction/fixture mismatch missing={missing} extra={extra}")

    measured = {rel: sha256_path(ROOT / rel) for rel in PINS}
    pin_mismatch = {k: {"declared": v, "measured": measured[k]}
                    for k, v in PINS.items() if measured[k] != v}
    if pin_mismatch:
        raise SystemExit(f"FAIL-CLOSED: pin mismatch before preregistration: {pin_mismatch}")

    prereg = {
        "task_id": "W062-R03V2-SCOPE-REPLICATION-01",
        "worker": "worker-062",
        "created_at": NOW,
        "node_id": "A1",
        "gate": "G-FORM/G-CLASSBIND",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "question": ("Does cand_r03v2 (e41a4b23a840, binder-head co-binding span=80) stay "
                     "scope-safe on a fresh independently authored held-out corpus that targets "
                     "the under-rejection residue its own docstring admits, and does this harness "
                     "reproduce W006-R03-SCOPE-01 cell-for-cell on worker-006's pinned corpus?"),
        "target_claim": {
            "target_id": "W006-R03-SCOPE-01 claim at artifact report e81f7818d026",
            "reviewed_sha256": "e81f7818d0264e2b7052fccc9ef1890915ba4313543a412efc50badabbbe6049",
            "claim_excerpt": ("cand_r03v2 has FP 0 / FN 0 on the same corpus and accepts all three "
                              "live canonicals ... on this evidence the scope-aware half of the "
                              "lead's option A-prime is already implemented by R03-v2 and no "
                              "additional grouping requirement is needed to pass this corpus."),
        },
        "hypotheses": {
            "H1_reproduce": ("This harness reproduces worker-006's raw verdicts cell-for-cell on "
                             "all 76 cells (4 tools x 19 fixtures); any mismatch is a harness or "
                             "reference defect and makes the result inconclusive."),
            "H2_span": ("cand_r03v2 accepts at distance 79 and 80 and rejects at 81 and 120 "
                        "(strict > span failure), so the declared span=80 boundary is exact."),
            "H3_underreject": ("cand_r03v2 accepts all four fresh scope-error families "
                               "(free-in-restriction, free-predicate, wrong-clause co-binding, "
                               "head-parenthesised aside) because it only requires the binder "
                               "identifiers to occur in order inside SOME quantifier clause head, "
                               "not to be introduced by the declaring entry's clause. This "
                               "falsifies the generalisation of the target claim beyond the "
                               "W006 corpus, while leaving the corpus-scoped measurement intact."),
            "H4_positives": ("cand_r03v2 accepts all three fresh correct renderings, so its FN=0 "
                             "half survives on this corpus."),
        },
        "predicted_cells": PRED,
        "predicted_summary": {
            "part_a_cells_expected_to_match_reference": 76,
            "cand_r03v2_FP_on_scored_negatives": 4,
            "cand_r03v2_FN_on_scored_positives": 0,
            "cand_004_FP_on_scored_negatives": 4,
            "cand_E3_FP_on_scored_negatives": 4,
            "frozen_FP_on_scored_negatives": 0,
            "frozen_FN_on_scored_positives": 3,
        },
        "decision_rule": {
            "replicate-confirmed": ("Part A 76/76 AND cand_r03v2 FP=0 AND FN=0 AND prediction "
                                    "deviations <= 5% of Part B cells"),
            "generalisation-falsified": ("Part A 76/76 AND (cand_r03v2 FP>0 OR FN>0) on Part B"),
            "inconclusive": "any pin drift, any tool error cell, or Part A mismatch",
        },
        "stop_rule": ("Stop and emit a blocker with no verdict if any pin moves pre/post, if a "
                      "tool errors on a fixture, or if the target claim's report hash "
                      "e81f7818d026 is not on disk unchanged."),
        "pins": PINS,
        "pins_measured_at_preregistration": measured,
        "hashes": {
            "make_fixtures.py": sha256_path(HERE / "make_fixtures.py"),
            "run_replication.py": sha256_path(HERE / "run_replication.py"),
            "fixture_manifest.json": sha256_path(HERE / "fixture_manifest.json"),
        },
        "fixture_hashes": {f["fixture"]: f["sha256"] for f in manifest["fixtures"]},
        "not_claimed": ["no gate verdict", "no node completion", "no adoption recommendation",
                        "no canonical or frozen write", "no theorem"],
    }
    (HERE / "PREREGISTRATION.json").write_text(json.dumps(prereg, indent=1) + "\n")
    print("PREREGISTRATION.json written")
    print("pins verified:", len(measured))
    print("predicted cells:", len(PRED), "fixtures x", len(PRED["ctrl_canonical_wcc.yaml"]), "tools")


if __name__ == "__main__":
    main()
