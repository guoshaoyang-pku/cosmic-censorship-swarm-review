#!/usr/bin/env python3
"""W011-F1-VIS-STRICT-01 - write the independent review and emit validated outbox events.

Writes:
  reviews/F1-review-011-visibility-strictness.json   (review artifact)
  comms/outbox/worker-011.jsonl                      (append, only with --emit)
  runtime/state/w011_checkpoint_3.json               (only with --emit)
  runtime/state/w011_checkpoints.jsonl               (append, only with --emit)

Every event is validated with research_map.schemas.validate_event BEFORE it is
appended, so an invalid event can never reach the controller's ingest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "artifacts/worker-011/f1_visibility_strictness_adjudication"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")

F1 = ROOT / "schemas/af_wcc_vacuum.yaml"
TAX = ROOT / "research_map/formulation_taxonomy.yaml"
CHECKER = ART / "run_adjudication.py"
REPORT = ART / "report.json"
REVIEW = ROOT / "reviews/F1-review-011-visibility-strictness.json"
W037 = ROOT / "artifacts/worker-037/f1_visibility_equivalence_adjudication/report.json"
W061 = ROOT / "artifacts/worker-061/f1_rev12_gate/REVIEW.json"
R040 = ROOT / "reviews/F1-review-040-rev12.json"
R088 = ROOT / "reviews/F1-review-088-rev12.json"
OUTBOX = ROOT / "comms/outbox/worker-011.jsonl"
CKPT = ROOT / "runtime/state/w011_checkpoint_3.json"
CKPT_LOG = ROOT / "runtime/state/w011_checkpoints.jsonl"

sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TASK_ID = "W011-F1-VIS-STRICT-01"
PIN_F1 = "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"
PIN_TAX = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build_review(report: dict, hashes: dict) -> dict:
    ruling = report["ruling"]
    hf = ruling["hard_failure"]
    checks = report["checks_summary"]
    return {
        "schema_version": "1.0",
        "record_id": "RV-W011-F1-VIS-STRICT-01",
        "task_id": TASK_ID,
        "actor": "worker-011",
        "reviewer": "worker-011",
        "reviewer_role": "independent_worker_reviewer",
        "created_at": NOW,
        "node_id": "F1",
        "target_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "gate": "G-FORM",
        "artifact": "schemas/af_wcc_vacuum.yaml",
        "artifact_path": "schemas/af_wcc_vacuum.yaml",
        "artifact_revision": 12,
        "artifact_sha256": PIN_F1,
        "reviewed_sha256": PIN_F1,
        "canonical_taxonomy_sha256": PIN_TAX,
        "counts_as_full_schema_verdict": False,
        "counts_as_independent_second_verdict": False,
        "scope": (
            "Adjudication of the domains.D5 (L72) strictness claim and the visibility.definition (L213) "
            "misclassification sentence at the frozen rev12 hash, plus the status of the cited support. "
            "NOT a full-schema verdict and not a gate verdict."
        ),
        "verdict": ruling["verdict_recommendation"],
        "score": ruling["score_recommendation"],
        "score_basis": (
            "The operative visibility predicate is the correct single-q tail form and the rev12 repairs "
            "otherwise stand, but the canonical class definition asserts a false mathematical relation "
            "('strictly STRONGER') about its own central predicate and cites a withdrawn blocker as "
            "independent confirmation."
        ),
        "hard_failures": [
            {
                "id": hf["id"],
                "severity": "blocking",
                "name": hf["name"],
                "finding": hf["finding"],
                "why_blocking": hf["why_blocking"],
                "evidence_refs": hf["evidence_refs"],
                "falsifier": hf["falsifier"],
            }
        ],
        "non_blocking_findings": ruling["non_blocking_findings"],
        "positive_checks": ruling["positive_checks"],
        "minimal_fix": ruling["minimal_fix"],
        "checks_summary": checks,
        "machine_evidence": {
            "exhaustive_preorders_n_le_5": report["machine_check"][
                "exhaustive_preorders_n_le_5"
            ],
            "fixed_seed_sampled_n_6_8": report["machine_check"]["fixed_seed_sampled"],
            "controls": report["controls"],
            "preorder_counts_match_oeis_A000798": checks[
                "X10_preorder_counts_match_oeis_A000798"
            ],
        },
        "evidence_refs": [
            f"schemas/af_wcc_vacuum.yaml#sha256:{PIN_F1[:12]}",
            f"research_map/formulation_taxonomy.yaml#sha256:{PIN_TAX[:12]}",
            f"artifacts/worker-011/f1_visibility_strictness_adjudication/report.json#sha256:{hashes['report'][:12]}",
            f"artifacts/worker-011/f1_visibility_strictness_adjudication/run_adjudication.py#sha256:{hashes['checker'][:12]}",
            f"artifacts/worker-037/f1_visibility_equivalence_adjudication/report.json#sha256:{hashes['w037'][:12]}",
            f"artifacts/worker-061/f1_rev12_gate/REVIEW.json#sha256:{hashes['w061'][:12]}",
            f"reviews/F1-review-040-rev12.json#sha256:{hashes['r040'][:12]}",
            f"reviews/F1-review-088-rev12.json#sha256:{hashes['r088'][:12]}",
        ],
        "falsifier": report["falsifier"],
        "next_falsifier": report["next_falsifier"],
        "authority_note": report["authority_note"],
        "limitations": report["limitations"],
        "claims_completion": False,
    }


def build_events(report: dict, review: dict, hashes: dict) -> list[dict]:
    hf = report["ruling"]["hard_failure"]
    claim_statement = (
        f"At schemas/af_wcc_vacuum.yaml#cce9c60146d6 (F1 rev12, class AF-WCC-VAC-GEN), the "
        f"domains.D5/visibility assertion that whole-curve single-q containment gamma([0,T)) subset "
        f"J^-(q) is 'strictly STRONGER' than the tail predicate exists t0: gamma([t0,T)) subset J^-(q), "
        f"and the L213 claim that the whole-curve reading 'would misclassify a geodesic that starts in "
        f"the exterior and ends inside the black-hole region', are both FALSE under the schema's "
        f"declared standard causal past: LEMMA-W011-1 proves tail <=> whole by past-closure of J^-(q) "
        f"(tail => whole because gamma([0,t0]) subset J^-(q) whenever gamma(t0) in J^-(q)). Independent "
        f"machine check: all 7331 preorders on <=5 labelled points, every causal chain, every q "
        f"(534214 tail/q evaluations, 0 divergences), fixed-seed samples at n=6,7,8 (6200 models, "
        f"4105578 evaluations, 0 divergences); the enumerator reproduces OEIS A000798. Teeth controls "
        f"diverge only when past-closure or causality is dropped (cover-reachability: 56046 "
        f"divergences; non-causal sequences: 29400). The sole recorded strictness witness violates "
        f"past-closure (a preceq b, b in J^-(q), a not in J^-(q)) and disappears under the standard "
        f"past. The L72 citation 'independently confirmed by worker-037 W037V2-F1' is stale: worker-037 "
        f"withdrew W037V2-F1 as a critical blocker. Recommendation: revise F1 before any accept at "
        f"this hash; the operative tail predicate itself is sound and unchanged. This is an "
        f"evidence/model claim about an artifact, not a physics theorem."
    )
    review_finding_lines = [
        f"{hf['id']} (blocking): {report['ruling']['hard_failure']['name']}",
        *[
            f"{f['id']} ({f['severity']}): {f['name']}"
            for f in report["ruling"]["non_blocking_findings"]
        ],
        *report["ruling"]["positive_checks"],
    ]
    return [
        {
            "event_id": f"w011-{NOW.replace(':', '').replace('-', '')}-task-status",
            "event_type": "status",
            "created_at": NOW,
            "actor": "worker-011",
            "node_id": "F1",
            "gate": "G-FORM",
            "class_id": "AF-WCC-VAC-GEN",
            "class_ids": ["AF-WCC-VAC-GEN"],
            "status": "active",
            "hours": 0.4,
            "task_id": TASK_ID,
            "summary": (
                "No assignment card exists in comms/inbox/worker-011.jsonl. Took one bounded "
                "class-bound task: W011-F1-VIS-STRICT-01 = independent adjudication of the F1 rev12 "
                "visibility strictness claim at cce9c60146d6, chosen because two accepts at that hash "
                "(worker-061 4.5, worker-088 4.0) cite the sentence as a repair while worker-040 "
                "HF-040-04 and worker-037 record it as false/non-sequitur. Result: hard failure "
                "HF-011-01 (false strictness claim) -> recommendation revise 3.5. Does not claim node "
                "completion or any gate verdict."
            ),
            "evidence_refs": [
                "schemas/af_wcc_vacuum.yaml#sha256:cce9c60146d6",
                f"reviews/F1-review-011-visibility-strictness.json#sha256:{hashes['review'][:12]}",
                f"artifacts/worker-011/f1_visibility_strictness_adjudication/report.json#sha256:{hashes['report'][:12]}",
            ],
            "next_falsifier": report["next_falsifier"],
        },
        {
            "event_id": f"w011-{NOW.replace(':', '').replace('-', '')}-art-checker",
            "event_type": "artifact",
            "created_at": NOW,
            "actor": "worker-011",
            "node_id": "F1",
            "gate": "G-FORM",
            "class_id": "AF-WCC-VAC-GEN",
            "artifact_type": "checker",
            "path": "artifacts/worker-011/f1_visibility_strictness_adjudication/run_adjudication.py",
            "sha256": hashes["checker"],
            "validation_status": "unverified",
            "task_id": TASK_ID,
            "note": (
                "Deterministic: pinned hashes, exhaustive preorder enumeration (OEIS A000798 positive "
                "control), two teeth controls, prior-witness arithmetic reproduction, before/after "
                "drift guard. Writes only its own report.json."
            ),
        },
        {
            "event_id": f"w011-{NOW.replace(':', '').replace('-', '')}-art-report",
            "event_type": "artifact",
            "created_at": NOW,
            "actor": "worker-011",
            "node_id": "F1",
            "gate": "G-FORM",
            "class_id": "AF-WCC-VAC-GEN",
            "artifact_type": "audit_report",
            "path": "artifacts/worker-011/f1_visibility_strictness_adjudication/report.json",
            "sha256": hashes["report"],
            "validation_status": "unverified",
            "task_id": TASK_ID,
            "note": "10/10 checks pass; equivalence 0 divergences; controls have teeth; HF-011-01.",
        },
        {
            "event_id": f"w011-{NOW.replace(':', '').replace('-', '')}-art-review",
            "event_type": "artifact",
            "created_at": NOW,
            "actor": "worker-011",
            "node_id": "F1",
            "gate": "G-FORM",
            "class_id": "AF-WCC-VAC-GEN",
            "artifact_type": "review_verdict",
            "path": "reviews/F1-review-011-visibility-strictness.json",
            "sha256": hashes["review"],
            "validation_status": "unverified",
            "task_id": TASK_ID,
            "note": "Targeted independent review, revise 3.5, bound to cce9c60146d6.",
        },
        {
            "event_id": f"w011-{NOW.replace(':', '').replace('-', '')}-review-f1",
            "event_type": "review",
            "created_at": NOW,
            "actor": "worker-011",
            "node_id": "F1",
            "gate": "G-FORM",
            "class_id": "AF-WCC-VAC-GEN",
            "class_ids": ["AF-WCC-VAC-GEN"],
            "target_id": "F1",
            "reviewer": "worker-011",
            "verdict": "revise",
            "score": 3.5,
            "artifact": "schemas/af_wcc_vacuum.yaml",
            "artifact_sha256": PIN_F1,
            "reviewed_sha256": PIN_F1,
            "counts_as_full_schema_verdict": False,
            "counts_as_independent_second_verdict": False,
            "hard_failures": [
                {
                    "id": hf["id"],
                    "severity": "blocking",
                    "name": hf["name"],
                    "falsifier": hf["falsifier"],
                }
            ],
            "findings": review_finding_lines,
            "evidence_refs": review["evidence_refs"],
            "falsifier": report["falsifier"],
            "next_falsifier": report["next_falsifier"],
        },
        {
            "event_id": f"w011-{NOW.replace(':', '').replace('-', '')}-claim-strictness",
            "event_type": "claim",
            "created_at": NOW,
            "actor": "worker-011",
            "node_id": "F1",
            "gate": "G-FORM",
            "class_id": "AF-WCC-VAC-GEN",
            "class_ids": ["AF-WCC-VAC-GEN"],
            "conclusion_type": "formal_model",
            "statement": claim_statement,
            "assumptions": [
                "J^-(q) is the schema's declared standard causal past, hence past-closed; the schema writes 'the causal past J^-(q)' (L72) and 'causal relation' (witness_protocol step 4) and declares no non-standard reading.",
                "D4 supplies future-directed causal (in particular causal) curves; the lemma does not use geodesicity, inextendibility, or finite affine length.",
                "The finite preorder models are models of the causal-relation core (reflexive, transitive, past-closed downsets), not of the full Lorentzian schema.",
                "Pins: F1 = cce9c60146d6, canonical taxonomy = 0abb9ed8a961; a later F1 revision voids this adjudication.",
            ],
            "falsifier": report["falsifier"],
            "evidence_refs": review["evidence_refs"],
            "artifact_refs": [
                f"reviews/F1-review-011-visibility-strictness.json#sha256:{hashes['review'][:12]}",
                f"artifacts/worker-011/f1_visibility_strictness_adjudication/report.json#sha256:{hashes['report'][:12]}",
            ],
            "task_id": TASK_ID,
            "claims_completion": False,
        },
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", action="store_true", help="append events + checkpoint")
    args = ap.parse_args()

    report = json.loads(REPORT.read_text())
    hashes = {
        "checker": sha(CHECKER),
        "report": sha(REPORT),
        "f1": sha(F1),
        "tax": sha(TAX),
        "w037": sha(W037),
        "w061": sha(W061),
        "r040": sha(R040),
        "r088": sha(R088),
    }
    if hashes["f1"] != PIN_F1 or hashes["tax"] != PIN_TAX:
        print("PIN MISMATCH: F1 or taxonomy moved; re-run run_adjudication.py first.")
        return 2

    review = build_review(report, hashes)
    REVIEW.write_text(json.dumps(review, indent=1) + "\n", encoding="utf-8")
    hashes["review"] = sha(REVIEW)

    events = build_events(report, review, hashes)
    for e in events:
        validate_event(e)

    checkpoint = {
        "checkpoint": 3,
        "at": NOW,
        "worker": "worker-011",
        "hours_spent_estimate": 0.4,
        "supersedes": None,
        "assignment": "W011-F1-VIS-STRICT-01 (self-selected; no worker-011 inbox card)",
        "node_id": "F1",
        "gate": "G-FORM",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "status": {
            "delivered": True,
            "validation_status": "unverified",
            "verdict": "revise",
            "score": 3.5,
            "target_sha256": PIN_F1,
            "hard_failure": "HF-011-01",
            "counts_as_full_schema_verdict": False,
            "no_completion_claim": (
                "worker cannot set done/passed or a gate verdict; this is one bounded task completion"
            ),
        },
        "artifacts": {
            "reviews/F1-review-011-visibility-strictness.json": {"sha256": hashes["review"]},
            "artifacts/worker-011/f1_visibility_strictness_adjudication/report.json": {
                "sha256": hashes["report"]
            },
            "artifacts/worker-011/f1_visibility_strictness_adjudication/run_adjudication.py": {
                "sha256": hashes["checker"]
            },
        },
        "inputs_pinned": {
            "schemas/af_wcc_vacuum.yaml": PIN_F1,
            "research_map/formulation_taxonomy.yaml": PIN_TAX,
        },
        "falsifier": report["falsifier"],
        "next_falsifier": report["next_falsifier"],
    }

    print(json.dumps({
        "emit": args.emit,
        "review_sha256": hashes["review"],
        "report_sha256": hashes["report"],
        "checker_sha256": hashes["checker"],
        "events": len(events),
        "event_types": [e["event_type"] for e in events],
        "validation": "all events valid",
    }, indent=1))

    if not args.emit:
        return 0

    with OUTBOX.open("a", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
    CKPT.write_text(json.dumps(checkpoint, indent=1) + "\n", encoding="utf-8")
    with CKPT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "checkpoint": 3,
            "at": NOW,
            "worker": "worker-011",
            "task": TASK_ID,
            "node_id": "F1",
            "gate": "G-FORM",
            "verdict": "revise",
            "score": 3.5,
            "target_sha256": PIN_F1,
            "review_file": "reviews/F1-review-011-visibility-strictness.json",
            "review_sha256": hashes["review"],
        }) + "\n")
    print(f"appended {len(events)} events to {OUTBOX.relative_to(ROOT)}; checkpoint written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
