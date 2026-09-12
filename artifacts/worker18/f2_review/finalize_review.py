#!/usr/bin/env python3
"""Add the aggregator and cross-instrument addenda to reviews/F2-review-18.json (+ .md).

Run after write_review.py. Keeps the addenda reproducible instead of hand-patching JSON.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REVIEW = ROOT / "reviews" / "F2-review-18.json"
MD = ROOT / "reviews" / "F2-review-18.md"
PIN = ROOT / "artifacts/worker18/f2_review/aggregator_pin_check.json"
W05 = ROOT / "artifacts/worker18/f2_review/worker05_integration_report.json"
W06 = ROOT / "artifacts/worker18/f2_review/w06_c0_gate_report.json"
AGG = ROOT / "schemas/af_scc_regularities.yaml"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    review = json.loads(REVIEW.read_text())
    pin = json.loads(PIN.read_text())
    w05 = json.loads(W05.read_text())
    w06 = json.loads(W06.read_text())
    review["aggregator_addendum"] = {
        "path": "schemas/af_scc_regularities.yaml",
        "sha256": sha(AGG),
        "purpose": "verify that the F2 index pins the two reviewed component files and defines no conclusion of its own",
        "pin_check_report": "artifacts/worker18/f2_review/aggregator_pin_check.json",
        "pin_check_sha256": sha(PIN),
        "pin_check_verdict": pin["verdict"],
        "checks": pin["checks"],
        "note": ("P1-P5 pass: both component ids appear once each, pinned sha256 match disk, the "
                 "aggregator carries no conclusion object and no merged class token. The C0 "
                 "sidecar mismatch is recorded in the aggregator's component revision_note and is "
                 "NOT resolved by it."),
    }
    c0_checks = [c for c in w05.get("component_findings", [])]
    review["cross_instrument_addendum"] = {
        "purpose": ("record that the independent separation lints disagree with this review's "
                    "structural probe on the C0 component, and that the C0 schema's own declared "
                    "leakage test does not pass"),
        "w05_integration_lint": {
            "report": "artifacts/worker18/f2_review/worker05_integration_report.json",
            "sha256": sha(W05),
            "script": "artifacts/worker-05/check_f2_integration.py",
            "verdict": w05.get("component_verdict"),
            "c0_failures": [f["id"] for f in c0_checks
                            if f.get("verdict") == "fail" and "C0" in str(f.get("detail"))],
            "note": ("aggregator A1-A7 pass and the C2 component passes C1/C2/C4/C5; the C0 "
                     "component fails C1 (six class-id leaves including anti_scope.not_this_class), "
                     "C2 (raw regularity tokens, polarity-blind), C4 (composite strings: the YAML "
                     "comment at line 5 quoting the task text, and the must_not_conflate line 159) "
                     "and C5 (sibling gate)."),
        },
        "w06_sibling_gate": {
            "report": "artifacts/worker18/f2_review/w06_c0_gate_report.json",
            "sha256": sha(W06),
            "script": "artifacts/worker-06/check_class_binding.py",
            "rules": "artifacts/worker-06/class_binding_rules.json",
            "verdict": w06.get("verdict"),
            "failing_check": [c for c in w06.get("checks", []) if c.get("verdict") == "fail"],
            "note": ("the C0 schema declares this gate as its own leakage test with "
                     "expected_verdict 'pass' (leakage_test_vs_c2); the gate returns fail on the "
                     "single_class_id rule. C2 passes the sibling gate."),
        },
        "reviewer_position": ("both failing lints are polarity-blind/raw-text-based; the C0 "
                              "occurrences are separation statements, so the semantic content is "
                              "not merged. But G-FORM's stop rule requires the machine lint to "
                              "pass, so the artifact must be revised (rename exclusion keys, drop "
                              "the task-quote comment, rephrase the must_not_conflate line) or the "
                              "w05/w06 rules amended with polarity handling and an anti-scope "
                              "whitelist. Reviewer 18 has no authority to amend another worker's "
                              "gate; this is escalated to lead-formulation/Astra."),
    }
    review["class_discrimination_witness"] = {
        "question": ("Assignment: try to prove the C0 and C2 schemas are the same class. "
                     "Disproof-by-witness: exhibit one datum whose maximal development satisfies "
                     "one class's conclusion and falsifies the other's."),
        "witness_type": ("a generic asymptotically flat vacuum datum whose maximal development "
                         "admits a proper future extension with continuous (C^0) metric but no "
                         "proper future C^2 extension (weak-null-singularity Cauchy horizon)"),
        "separates": {
            "falsifies": "AF-SCC-C0-VAC-GEN conclusion (a continuous extension exists)",
            "leaves_intact": "AF-SCC-C2-VAC-GEN conclusion (the existing extension is not C^2)",
        },
        "why_valid": ("the two schemas' own implication ledger runs C0-inextendibility => "
                      "C2-inextendibility one way only; a model of C2-inextendibility that is not "
                      "a model of C0-inextendibility shows the classes are not the same statement"),
        "status": ("conditional_expected, not verified: Dafermos-Luk (arXiv:1710.01722) prove the "
                   "continuous extension and predict generically singular C^0-metric horizons, "
                   "conditional on Kerr exterior stability; no generic AF vacuum witness is "
                   "constructed in this repository"),
        "what_would_collapse_the_classes": ("if no generic datum admits a C^0-but-not-C^2 "
                                            "extension, every datum satisfies both conclusions or "
                                            "neither, and the two classes would be only nominally "
                                            "distinct (different regularity demanded, same truth "
                                            "value on all data)"),
        "evidence_refs": ["https://arxiv.org/abs/1710.01722",
                          "schemas/af_scc_c0_vacuum.yaml#0150bfdf",
                          "schemas/af_scc_c2_vacuum.yaml#21df6f7f"],
    }
    REVIEW.write_text(json.dumps(review, indent=2))
    w = review["class_discrimination_witness"]
    lines = MD.read_text().rstrip().splitlines()
    lines += ["", "## Discrimination witness (answer to the collapse question)", "",
              f"**Witness type:** {w['witness_type']}.", "",
              f"- falsifies: {w['separates']['falsifies']}",
              f"- leaves intact: {w['separates']['leaves_intact']}",
              f"- why valid: {w['why_valid']}",
              f"- status: {w['status']}",
              f"- what would collapse the classes: {w['what_would_collapse_the_classes']}", "",
              "## Aggregator addendum (schemas/af_scc_regularities.yaml)", "",
              f"- aggregator sha256: `{review['aggregator_addendum']['sha256']}`",
              f"- pin check: `{review['aggregator_addendum']['pin_check_report']}` "
              f"({review['aggregator_addendum']['pin_check_verdict']})"]
    for c in review["aggregator_addendum"]["checks"]:
        lines.append(f"- {c['id']}: {'pass' if c['pass'] else 'FAIL'} {c.get('observed')}")
    lines += ["", "## Cross-instrument addendum", "",
              "| instrument | C2 | C0 |", "|---|---|---|",
              "| worker-18 structural probe (this review) | pass | pass on separation; hard on sidecar |",
              f"| worker-05 integration lint | pass | **fail** ({', '.join(review['cross_instrument_addendum']['w05_integration_lint']['c0_failures'])}) |",
              f"| worker-06 sibling gate (declared by the C0 schema) | pass | **fail** |", "",
              review["cross_instrument_addendum"]["reviewer_position"], ""]
    MD.write_text("\n".join(lines) + "\n")
    print(json.dumps({"review": str(REVIEW), "review_sha256": sha(REVIEW),
                      "md_sha256": sha(MD)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
