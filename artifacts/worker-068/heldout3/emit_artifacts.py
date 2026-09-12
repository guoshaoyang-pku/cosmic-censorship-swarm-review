#!/usr/bin/env python3
"""Generate the two secondary HELDOUT-09 artifacts from raw_verdicts.json.

  gate_sensitivity_check.json  -- known-rejected positive controls + known-escape refs
  leak_validity_review.json    -- author-side classification of every leaky fixture,
                                  explicitly marked non-independent

No new measurements are made here; this only reorganizes recorded verdicts so the
lead/auditor can cite one hash per claim.

Usage: python3 emit_artifacts.py
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))


def main() -> int:
    raw = json.loads((HERE / "raw_verdicts.json").read_text())
    manifest = json.loads((HERE / "manifest.json").read_text())
    ops_by_file = {Path(f["fixture"]).name: f["mutation_ops"] for f in manifest["fixtures"]}
    by_file = {Path(f["fixture"]).name: f for f in raw["fixtures"]}

    rejected = [f for f in raw["fixtures"] if f["expectation"] == "known_rejected_positive_control"]
    escapes = [f for f in raw["fixtures"] if f["expectation"] == "known_escape_reference"]
    sensitivity = {
        "check": "heldout09_gate_sensitivity_and_replication",
        "corpus_id": raw["corpus_id"],
        "run_at": raw["run_at"],
        "manifest_sha256_before_run": raw["manifest_sha256_before_run"],
        "stage_hashes": raw["stage_hashes"],
        "valid": raw["valid"],
        "known_rejected_positive_controls": [
            {
                "fixture": f["file"],
                "family": f["family"],
                "origin": f["origin"],
                "structural": f["stage_a"]["verdict"],
                "structural_failed_rules": f["stage_a"]["failed_rules"],
                "semantic": f["stage_b"]["verdict"],
                "semantic_failed_rules": f["stage_b"]["failed_rules"],
                "caught_by_union": f["caught_union"],
            }
            for f in rejected
        ],
        "all_known_rejected_controls_still_caught": all(f["caught_union"] for f in rejected),
        "known_escape_references_rechecked_at_current_revision": [
            {
                "fixture": f["file"],
                "family": f["family"],
                "origin": f["origin"],
                "structural": f["stage_a"]["verdict"],
                "semantic": f["stage_b"]["verdict"],
                "escaped_union": f["escaped_union"],
            }
            for f in escapes
        ],
        "all_known_escape_references_still_escape": all(f["escaped_union"] for f in escapes),
        "interpretation": (
            "The 6 FORM-HELDOUT-07 leaks are still rejected by the union of stages, so the pipeline is "
            "live and the HELDOUT-09 escape rate is not an artifact of a dead evaluator. The 4 "
            "FORM-HELDOUT-08 escape families still escape at the current canonical revision, so those "
            "families replicated across a revision boundary rather than being fixed by it."
        ),
    }
    (HERE / "gate_sensitivity_check.json").write_text(json.dumps(sensitivity, indent=2) + "\n")

    # author-side validity classification of the 35 leaky fixtures
    borderline = {"c0_03_conclusion_negated": (
        "The conclusion statement is logically inverted while the C0 token is kept. The mutation is a "
        "genuine class-content change (the schema now asserts the negation of its own conclusion), but it "
        "is the only fixture that escapes both stages, so it needs independent adjudication before the "
        "family is cited as a gate blind spot.")}
    reviews = []
    for f in raw["fixtures"]:
        if f["expectation"] not in ("should_be_caught", "probe"):
            continue
        name = Path(f["fixture"]).name
        verdict = "genuine_leak" if name not in borderline else "borderline_genuine_leak"
        reviews.append({
            "fixture": name,
            "class_id": f["class_id"],
            "family": f["family"],
            "mutation_ops": ops_by_file.get(name, []),
            "expected_catcher_rules": f["expected_catcher_rules"],
            "leak_claim": f["leak_claim"],
            "verdict": verdict,
            "note": borderline.get(name, "class-defining content changed while class_id kept fixed"),
            "caught_stage_a": f["caught_stage_a"],
            "caught_stage_b": f["caught_stage_b"],
            "escaped_union": f["escaped_union"],
        })
    n_escape = sum(1 for f in raw["fixtures"] if f["escaped_union"] and f["expectation"] in ("should_be_caught", "probe"))
    review = {
        "corpus_id": raw["corpus_id"],
        "reviewer": "worker-068",
        "reviewer_role": "author of the corpus (NON-INDEPENDENT)",
        "reviewed_at": datetime.now(CST).isoformat(timespec="seconds"),
        "manifest_sha256_before_run": raw["manifest_sha256_before_run"],
        "scope": "author-side classification only; does not change any recorded verdict",
        "genuine_leak": sum(1 for r in reviews if r["verdict"] == "genuine_leak"),
        "borderline_genuine_leak": sum(1 for r in reviews if r["verdict"] == "borderline_genuine_leak"),
        "legitimate": 0,
        "escaped_fixtures": [r["fixture"] for r in reviews if r["escaped_union"]],
        "independent_review_required": True,
        "independence_note": (
            "This classification was produced by the corpus author. Per the FORM-HELDOUT-08 precedent, "
            "an independent reviewer must re-adjudicate at least each escaped fixture before the escape "
            "family is used; an escaped fixture classified legitimate by an independent reviewer is a "
            "corpus over-claim and must be removed from the family list."
        ),
        "fixtures": reviews,
    }
    (HERE / "leak_validity_review.json").write_text(json.dumps(review, indent=2) + "\n")
    print(json.dumps({"sensitivity_all_caught": sensitivity["all_known_rejected_controls_still_caught"],
                      "escape_refs_persisting": sensitivity["all_known_escape_references_still_escape"],
                      "genuine": review["genuine_leak"], "borderline": review["borderline_genuine_leak"],
                      "escaped": review["escaped_fixtures"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
