#!/usr/bin/env python3
"""Emit the W042 N0 second-review verdict, checkpoint and outbox events.

Re-measures every reviewed path, refuses to write if any hash moved since
report.json was produced (fail-closed), then writes:
  reviews/N0-review-worker-042.json
  runtime/state/worker-042_N0_checkpoint.json
  one appended line per event in comms/outbox/worker-042.jsonl

Worker authority: this cannot set a gate verdict or node status.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/worker-042/n0_stoprule_verify"
REPORT = OUT / "report.json"
CHECKER = OUT / "verify_n0_stoprule.py"
README = OUT / "README.md"
VERDICT = ROOT / "reviews/N0-review-worker-042.json"
CHECKPOINT = ROOT / "runtime/state/worker-042_N0_checkpoint.json"
OUTBOX = ROOT / "comms/outbox/worker-042.jsonl"
TASK = "W042-N0-STOPRULE-INDEP-VERDICT-01"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(rel: str, h: str) -> str:
    return f"{rel}#sha256:{h[:12]}"


def main() -> int:
    report = json.loads(REPORT.read_text())
    now = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")

    # fail closed on any hash move since the report was generated
    moved = []
    for rel, pinned in report["reviewed_hashes"].items():
        cur = sha(ROOT / rel)
        if cur != pinned:
            moved.append({"path": rel, "pinned": pinned, "measured": cur})
    if moved:
        blocker = {
            "event_id": "w042-n0-stoprule-01-blocker",
            "event_type": "blocker",
            "created_at": now,
            "actor": "worker-042",
            "node_id": "N0",
            "gate": "G-NUM",
            "class_id": "AF-WCC-SCALAR-SPH",
            "task_id": TASK,
            "description": "reviewed hash moved after report generation; verdict withheld (fail-closed)",
            "needed_to_unblock": "re-run the checker at the new hashes and re-review",
            "evidence_refs": [ref(str(REPORT.relative_to(ROOT)), sha(REPORT))],
            "moved": moved,
        }
        with OUTBOX.open("a") as fh:
            fh.write(json.dumps(blocker) + "\n")
        print("BLOCKER: hash moved, verdict withheld")
        return 2

    rep_h, chk_h, rd_h = sha(REPORT), sha(CHECKER), sha(README)
    ev = [
        ref("artifacts/worker-042/n0_stoprule_verify/report.json", rep_h),
        ref("artifacts/worker-042/n0_stoprule_verify/verify_n0_stoprule.py", chk_h),
        ref("artifacts/worker-042/n0_stoprule_verify/README.md", rd_h),
        ref("numerics/CONVERGENCE_PROTOCOL.md", report["reviewed_hashes"]["numerics/CONVERGENCE_PROTOCOL.md"]),
        ref("numerics/protocol/n0_fixed_dt_certification.json",
            report["reviewed_hashes"]["numerics/protocol/n0_fixed_dt_certification.json"]),
        ref("numerics/results/flat_wave_convergence_rev3.json",
            report["reviewed_hashes"]["numerics/results/flat_wave_convergence_rev3.json"]),
        ref("research_map/formulation_taxonomy.yaml",
            report["reviewed_hashes"]["research_map/formulation_taxonomy.yaml"]),
        ref("artifacts/worker-046/n0_fixed_dt_independent/verification.json",
            report["reviewed_hashes"]["artifacts/worker-046/n0_fixed_dt_independent/verification.json"]),
        ref("artifacts/worker-057/n0_fixeddt_verify/report.json",
            report["reviewed_hashes"]["artifacts/worker-057/n0_fixeddt_verify/report.json"]),
        ref("artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json",
            report["reviewed_hashes"]["artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json"]),
    ]

    falsifier = [
        "a document with binding authority (controller/Astra adjudication) showing the N0 class "
        "binding is carried by numerics/results/flat_wave_convergence_rev3.json rather than the "
        "protocol of record discharges HF-042-N0-1 at the measured hashes",
        "a protocol re-issued at a new hash whose section 1 names 0abb9ed8a961, with the C8 and N0 "
        "verdicts re-run at that new hash, removes the basis of this revise",
        "any invariant check in the report failing on a re-run at the same measured hashes, or any "
        "reported fit/order value that does not reproduce, falsifies the corresponding finding",
        "a file appearing under numerics/spherical_solver/, or any reviewed path hashing differently "
        "from the report, voids the affected citation and requires a re-review",
    ]
    non_claims = [
        "not a gate verdict; workers cannot pass G-NUM or set N0 status",
        "no reviewed artifact was edited; writes are under artifacts/worker-042/, reviews/ and "
        "runtime/state/ plus this worker's own outbox",
        "binds only to the measured hashes in the report; a moved hash voids the affected citation",
        "no other N0 review verdict file was read before this verdict was written (blind second review)",
        "numerical convergence evidence only; no claim about self-gravity, WCC or SCC",
    ]

    verdict = {
        "review_id": "N0-review-worker-042",
        "target_id": "N0",
        "target_path": "numerics/CONVERGENCE_PROTOCOL.md",
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "class_ids": ["AF-WCC-SCALAR-SPH"],
        "task_id": TASK,
        "reviewer": "worker-042",
        "actor": "worker-042",
        "created_at": now,
        "verdict": "revise",
        "score": 3.5,
        "reviewed_sha256": report["reviewed_hashes"]["numerics/CONVERGENCE_PROTOCOL.md"],
        "reviewed_hashes": report["reviewed_hashes"],
        "blind": True,
        "stop_rule_adjudication": report["stop_rule_adjudication"],
        "hard_failures": report["hard_failures"],
        "findings": report["findings"],
        "lock_guard": report["lock_guard"],
        "evidence_refs": ev,
        "falsifier": falsifier,
        "non_claims": non_claims,
        "verdict_basis": ("all 38 invariant checks in the report pass; the revise is carried by "
                          "HF-042-N0-1 (binding-document split for stop-rule item 2) and findings "
                          "F-042-N0-1/2/4"),
    }
    VERDICT.write_text(json.dumps(verdict, indent=1, sort_keys=True) + "\n")
    v_h = sha(VERDICT)

    checkpoint = {
        "checkpoint_id": f"w042-n0-stoprule-{now}",
        "created_at": now,
        "worker": "worker-042",
        "task": TASK,
        "node_id": "N0",
        "gate": "G-NUM",
        "class_ids": ["AF-WCC-SCALAR-SPH"],
        "role": "second blind independent review of the N0 stop rule (lead-audit HF-03)",
        "verdict": "revise",
        "score": 3.5,
        "stop_rule_adjudication": report["stop_rule_adjudication"],
        "inputs_pinned": {rel: {"measured_sha256": h} for rel, h in report["reviewed_hashes"].items()},
        "hash_stability_during_review": report["hash_stability"],
        "outputs": {
            "verdict": {"path": "reviews/N0-review-worker-042.json", "sha256": v_h},
            "report": {"path": "artifacts/worker-042/n0_stoprule_verify/report.json", "sha256": rep_h},
            "checker": {"path": "artifacts/worker-042/n0_stoprule_verify/verify_n0_stoprule.py",
                        "sha256": chk_h},
            "readme": {"path": "artifacts/worker-042/n0_stoprule_verify/README.md", "sha256": rd_h},
        },
        "checks": {"total": len(report["checks"]),
                   "failed": [c["check_id"] for c in report["checks"] if not c["pass"]]},
        "observations": report["observations"],
        "registry_checked_at": report["registry_checked_at"],
        "rerun_command": "python3 artifacts/worker-042/n0_stoprule_verify/verify_n0_stoprule.py",
        "authority": ("worker events cannot set status=done, validation_status=passed or a gate "
                      "verdict; N0/G-NUM authority stays with Astra and the group leads"),
    }
    CHECKPOINT.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
    ck_h = sha(CHECKPOINT)

    common = {"created_at": now, "actor": "worker-042", "task_id": TASK, "node_id": "N0",
              "gate": "G-NUM", "class_id": "AF-WCC-SCALAR-SPH", "class_ids": ["AF-WCC-SCALAR-SPH"]}
    review_event = dict(common, event_id="w042-n0-stoprule-01-review", event_type="review",
                        reviewer="worker-042", target_id="N0",
                        target_path="numerics/CONVERGENCE_PROTOCOL.md",
                        reviewed_revision=3, counts_as_node_verdict=True,
                        verdict="revise", score=3.5,
                        reviewed_sha256=report["reviewed_hashes"]["numerics/CONVERGENCE_PROTOCOL.md"],
                        reviewed_hashes=report["reviewed_hashes"],
                        hard_failures=report["hard_failures"], findings=report["findings"],
                        stop_rule_adjudication=report["stop_rule_adjudication"],
                        lock_guard=report["lock_guard"],
                        evidence_refs=ev + [ref("reviews/N0-review-worker-042.json", v_h)],
                        falsifier=falsifier, non_claims=non_claims)
    artifact_event = dict(common, event_id="w042-n0-stoprule-01-artifact", event_type="artifact",
                          artifact_type="independent_verification_report",
                          path="artifacts/worker-042/n0_stoprule_verify/report.json",
                          sha256=rep_h, validation_status="unverified",
                          artifact_refs=[{"path": "reviews/N0-review-worker-042.json", "sha256": v_h},
                                         {"path": "artifacts/worker-042/n0_stoprule_verify/verify_n0_stoprule.py",
                                          "sha256": chk_h},
                                         {"path": "runtime/state/worker-042_N0_checkpoint.json",
                                          "sha256": ck_h}],
                          evidence_refs=ev, falsifier=falsifier[:2])
    status_event = dict(common, event_id="w042-n0-stoprule-01-complete", event_type="status",
                        status="active", hours=0.4,
                        summary=("W042-N0-STOPRULE-INDEP-VERDICT-01 complete at worker level: second "
                                 "blind N0 review, verdict revise 3.5 at protocol "
                                 "1e6cdf04d7a2; report/checker/README/verdict/checkpoint are on disk "
                                 "and hash-pinned; stop-rule items 1 and 3 independently reproduced, "
                                 "item 2 open per HF-042-N0-1. Not a gate verdict and not a node "
                                 "transition."),
                        evidence_refs=ev + [ref("reviews/N0-review-worker-042.json", v_h),
                                            ref("runtime/state/worker-042_N0_checkpoint.json", ck_h)],
                        next_falsifier=falsifier[0])
    with OUTBOX.open("a") as fh:
        for e in (review_event, artifact_event, status_event):
            fh.write(json.dumps(e, sort_keys=True) + "\n")

    print(json.dumps({"verdict": "revise", "score": 3.5, "verdict_sha256": v_h,
                      "checkpoint_sha256": ck_h, "report_sha256": rep_h, "checker_sha256": chk_h,
                      "events": [review_event["event_id"], artifact_event["event_id"],
                                 status_event["event_id"]]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
