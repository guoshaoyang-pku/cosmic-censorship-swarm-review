#!/usr/bin/env python3
"""astra-numfix-02 revision 2: fold in worker 14's §10 technical verdict (astra-numfix-03)
at the FIXED hash 6542db93, show that the new 4-rung addendum closes its R5/R5a δ condition
for the replication order fit, and re-checkpoint. Proposal-only; no gate self-pass.

Hash guard: refuses if numerics/protocol/scheme_independence_review.md moved again while
this delta was being written, so the revision can never cite content it did not read.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
ACTOR = "deepseek-flash-13"
PROPOSAL = "numerics/tests/n0_gate_proposal.json"
REVIEW = "numerics/protocol/scheme_independence_review.md"
VERDICT = "numerics/protocol/fixed_replication_verdict.json"
VERIFIER = "numerics/protocol/verify_fixed_scheme_independence.py"
ADDENDUM_JSON = "numerics/tests/n0_order_4rung.json"
REVIEW_SHA = "2fdb85b23f7d120be4eab9fb7f7ccd0b9c1cac8b2e64dcfa0eabc3ca6f22d8b8"
REV1_SHA = "22d984781cee6642b0793bd6ec7c3c7400cc8f1fe3899933d612f7a562815cd3"


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def ref(rel: str) -> str:
    return f"{rel}#sha256:{sha(rel)[:16]}"


def main() -> int:
    if sha(REVIEW) != REVIEW_SHA:
        print(f"REFUSE: review moved again ({sha(REVIEW)[:16]} != {REVIEW_SHA[:16]}); re-read first")
        return 2
    if sha(PROPOSAL) != REV1_SHA:
        print(f"REFUSE: proposal rev1 hash changed ({sha(PROPOSAL)[:16]} != {REV1_SHA[:16]})")
        return 2

    v = json.loads((ROOT / VERDICT).read_text())
    add = json.loads((ROOT / ADDENDUM_JSON).read_text())
    p = json.loads((ROOT / PROPOSAL).read_text())
    p["revision"] = 2
    p["supersedes_sha256"] = REV1_SHA
    p["created_at"] = NOW
    p["provenance"]["generated_at"] = NOW
    p["proposal"]["condition"] = (
        "lead-audit records the independent numerical-protocol review (reviews/G-NUM-protocol-review.json) "
        "at the fixed run hash 6542db93 accepting the scheme-independence evidence and R1-R5, with no new "
        "hard finding; the two format conditions of worker 14's §10 verdict are dispositioned as recorded "
        "in worker14_verdict (δ now carried by the addendum; harness functional labelled cross-check)")
    p["worker14_verdict"] = {
        "assignment": "astra-numfix-03",
        "verdict_sentence": ("scheme independence of the measured order-2 result is established for this "
                             "configuration by three independent discretisations; p = 1.9958/1.9935/1.9863 "
                             "agree within their R5 uncertainty and each conserves a family-appropriate "
                             "functional to <= 2.1e-14"),
        "q1": "YES per-scheme R1/R2; NO for the harness gate taken alone (harness/own drift ratios 5.95e6 cnfd, 4.15e5 cnfem)",
        "q2": "FIXED run as submitted carries no delta; this verification supplies delta post hoc",
        "remaining_format_conditions": {
            "condition_i_delta_in_fit_record": {
                "status": "closed for the replication order fit by this submission",
                "closed_by": ref(ADDENDUM_JSON),
                "detail": ("n0_order_4rung.json reports per-scheme delta = "
                           "max(pair-spread half-range, LSQ slope standard error) with the norm named "
                           "(L2 integral), the 4-rung set, and the fit method (R5/R5a): "
                           f"delta lffd {add['verdict']['delta']['lffd']:.3e}, "
                           f"cnfd {add['verdict']['delta']['cnfd']:.3e}, "
                           f"cnfem {add['verdict']['delta']['cnfem']:.3e}"),
            },
            "condition_ii_harness_functional_demotion": {
                "status": "relabelled in the FIXED run; acceptance-text demotion is lead-numerics/audit",
                "detail": ("FIXED run reports harness_leapfrog_energy_drift beside each own_energy_drift; "
                           "triage and proposal state the harness PASS bounds the leapfrog functional, not a "
                           "solver's own invariant. The acceptance text itself is not this worker's artifact."),
            },
        },
        "not_the_audit_review": "worker-level technical verdict; does not serve as the independent A1 audit",
        "evidence": [ref(REVIEW), ref(VERDICT), ref(VERIFIER)],
        "falsifiers_not_triggered": {"F5": "own drifts 3.4e-15/1.1e-14/2.0e-14 <= 1e-12",
                                     "F6": "max |dp| 9.45e-03 <= max(0.25, sqrt(da^2+db^2))",
                                     "F7": "harness/own ratios 5.95e6 and 4.15e5, not <= 1"},
    }
    p["protocol_state"]["worker14_technical_verdict"] = ref(VERDICT)
    p["protocol_state"]["audit_review_absent"] = (
        "reviews/G-NUM-protocol-review.json (astra-numfix-04, open); worker 14's verdict is not the A1 audit")
    p["unmet_items_after_this_submission"][0]["detail"] = (
        "worker 14's astra-numfix-03 technical verdict is recorded at the FIXED hash; the A1 audit review "
        "(astra-numfix-04, lead-audit) is still absent")
    (ROOT / PROPOSAL).write_text(json.dumps(p, indent=2, sort_keys=True) + "\n")
    ph2 = sha(PROPOSAL)

    art = validate_event({
        "event_id": "f13-n0-numfix02-art-proposal-r2",
        "event_type": "artifact", "created_at": NOW, "actor": ACTOR,
        "node_id": "N0", "class_id": "AF-WCC-SCALAR-SPH",
        "artifact_type": "gate_proposal", "path": PROPOSAL, "sha256": ph2,
        "validation_status": "unverified",
        "note": f"revision 2, supersedes {REV1_SHA}; folds in worker 14 §10 verdict and the addendum delta closure",
        "evidence_refs": [ref(REVIEW), ref(VERDICT)],
    })
    status = validate_event({
        "event_id": "f13-n0-numfix02-status-cp2",
        "event_type": "status", "created_at": NOW, "actor": ACTOR,
        "node_id": "N0", "status": "active", "hours": 1.7,
        "summary": (
            "CHECKPOINT 2 / delta on astra-numfix-02. Proposal revised to r2 "
            f"(sha256 {ph2[:16]}, supersedes {REV1_SHA[:16]}) after worker 14 published its astra-numfix-03 "
            f"verdict at the FIXED hash 6542db93 ({ref(VERDICT)}): scheme independence ESTABLISHED for this "
            "configuration (p 1.9958/1.9935/1.9863 within R5 uncertainty; own invariants <= 2.1e-14), with "
            "two format conditions. Condition (i) 'delta in the fit record' is CLOSED for the replication "
            f"order fit by the new addendum {ref(ADDENDUM_JSON)} (delta 1.8e-03/4.2e-03/5.1e-03, norm L2 "
            "named, 4 rungs, R5a). Condition (ii) harness-functional demotion is relabelled in the FIXED run; "
            "the acceptance text belongs to lead-numerics. Recommended G-NUM verdict remains pending; the only "
            "unmet gate criterion is the independent A1 audit review (astra-numfix-04), which nobody may "
            "self-review. No gate self-pass, no node completion. Checkpoint: runtime/state/w13_checkpoint_2.json."),
        "evidence_refs": [f"{PROPOSAL}#sha256:{ph2[:16]}", ref(VERDICT), ref(ADDENDUM_JSON), ref(REVIEW)],
        "next_falsifier": ("A1 audit review at 6542db93 rejects scheme independence, or worker 14's F5/F6/F7 "
                           "triggers on a re-run, or the review hash 2fdb85b2 changes again"),
    })
    out = ROOT / "comms" / "outbox" / f"{ACTOR}.jsonl"
    with out.open("a") as f:
        for e in (art, status):
            f.write(json.dumps(e, sort_keys=True) + "\n")
    cp2 = {
        "checkpoint": 2, "at": NOW, "worker": ACTOR, "run": "run-2026-09-12T00:00+08:00",
        "delta": ("revised gate proposal r2 after worker 14's astra-numfix-03 verdict; closed its R5 delta "
                  "condition for the replication order fit with the 4-rung addendum"),
        "assignments": {"astra-numfix-02": "closed (proposal r2)",
                        "astra-numfix-03": "not mine: worker 14 verdict read and incorporated"},
        "hours_spent_estimate": 1.7,
        "artifacts": {PROPOSAL: ph2[:16], ADDENDUM_JSON: sha(ADDENDUM_JSON)[:16],
                      REVIEW: sha(REVIEW)[:16], VERDICT: sha(VERDICT)[:16],
                      "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json": sha(
                          "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json")[:16]},
        "outbox_events": [art["event_id"], status["event_id"]],
        "gate_proposal": "G-NUM pending; pass-if A1 audit review at 6542db93 accepts",
        "numerics_lock": "respected: no N1 work, no numerics/spherical_solver/",
        "next": ["await the A1 audit protocol review at 6542db93",
                 "lead-numerics: demote harness functional in the acceptance text (R4 condition ii)"],
    }
    (ROOT / "runtime" / "state" / "w13_checkpoint_2.json").write_text(
        json.dumps(cp2, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"proposal_sha256": ph2, "events": [art["event_id"], status["event_id"]],
                      "checkpoint": "runtime/state/w13_checkpoint_2.json",
                      "outbox_sha256": hashlib.sha256(out.read_bytes()).hexdigest()}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
