#!/usr/bin/env python3
"""W038-A0-SELFTEST-01 — emit schema-valid outbox events + a worker checkpoint.

Reads artifacts/worker-038/a0_selftest/selftest_verification.json (produced by
run_selftest.py) and emits upward events to comms/outbox/worker-038.jsonl:

  artifact  x2  the verification record and the validator's own report (hash-bound)
  review    x1  scoped verdict on the validator *mechanism* at its pinned hash
  status    x1  node A0 execution status with evidence hashes and next falsifier
  blocker   x1  what the audit lead must still resolve

Every event is validated with research_map.schemas.validate_event before it is written;
rejects go to a worker-local file, never to the global rejected stream.

Also writes the worker checkpoint to runtime/state/w038_checkpoint_1.json and
artifacts/worker-038/a0_selftest/CHECKPOINT_1.json.

Authority: worker events cannot set status=done, validation_status=passed, or any gate verdict.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
sys.path.insert(0, str(ROOT / "research_map"))

from schemas import SchemaError, validate_event  # noqa: E402

VERIFICATION = HERE / "selftest_verification.json"
OUTBOX = ROOT / "comms" / "outbox" / "worker-038.jsonl"
REJECTS = HERE / "rejected_events.jsonl"
CHECKPOINT = ROOT / "runtime" / "state" / "w038_checkpoint_1.json"
FROZEN = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main() -> int:
    v = json.loads(VERIFICATION.read_text())
    vsha = sha256_file(VERIFICATION)
    vrel = str(VERIFICATION.relative_to(ROOT))
    ck = {c["check_id"]: c["status"] for c in v["checks"]}
    run_b = v["runs"]["run_b_absolute_out"]
    run_a = v["runs"]["run_a_relative_out"]
    rep = v.get("validator_report") or {}
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    actor = "worker-038"
    base = {"actor": actor, "created_at": now(), "class_ids": FROZEN}

    events = []

    # 1. the execution record itself
    events.append(
        {
            **base,
            "event_id": f"w038-a0-selftest-artifact-{stamp}",
            "event_type": "artifact",
            "node_id": "A0",
            "artifact_type": "a0_selftest_verification",
            "path": vrel,
            "sha256": vsha,
            "validation_status": "unverified",
            "gate": "G-AUDIT",
            "evidence_refs": [
                f"{vrel}#{vsha}",
                f"{run_b['report_path']}#{run_b['report_sha256']}"
                if run_b.get("report_path")
                else "artifacts/worker-038/a0_selftest/run_b_absolute_out/stderr.txt",
                "artifacts/worker-038/a0_selftest/run_a_relative_out/stderr.txt",
            ],
            "summary": "Declared A0 self-test executed at pinned hashes; result="
            + v["result"]
            + "; worker evidence only, no gate verdict.",
        }
    )

    # 2. the validator's own report (what the missing self-test record points at)
    if run_b.get("report_path"):
        events.append(
            {
                **base,
                "event_id": f"w038-a0-selftest-validator-report-{stamp}",
                "event_type": "artifact",
                "node_id": "A0",
                "artifact_type": "a0_validator_report",
                "path": run_b["report_path"],
                "sha256": run_b["report_sha256"],
                "validation_status": "unverified",
                "gate": "G-AUDIT",
                "evidence_refs": [vrel + "#" + vsha],
                "summary": f"audit_run.py --quiet --out <absolute> exit={run_b['exit_code']} "
                f"critical={(rep.get('summary') or {}).get('critical')} "
                f"gates={rep.get('gates')}",
            }
        )

    # 3. scoped review of the validator mechanism at its pinned hash
    validator_sha = v["measured_hashes"].get("artifacts/audit/audit_run.py")
    findings = [
        f"S2a {ck.get('S2a-relative-out-crashes')}: audit_run.py crashes with ValueError at "
        f"line 335 when --out is relative (exit={run_a['exit_code']}, no report); the default "
        f"--out is absolute, but any documented relative invocation fails after the full scan.",
        f"S7 {ck.get('S7-validator-does-not-fill-its-declared-validation-block')}: no code path "
        f"writes evaluation_rubric.yaml; validation.last_run stays "
        f"{v['self_promotion_check']['validation_last_run']!r} after a successful run, so the "
        f"rubric's line-46 rule cannot be discharged by invoking the declared validator.",
        f"S2b {ck.get('S2b-absolute-out-completes')}: with an absolute --out the validator "
        f"completes (exit={run_b['exit_code']}, report {run_b['report_path']}) and reports "
        f"{(rep.get('summary') or {}).get('total')} violations "
        f"({(rep.get('summary') or {}).get('critical')} critical); its own gate line is "
        f"{rep.get('gates')} — reported, not binding.",
        f"S1 {ck.get('S1-inputs-pinned')}: pinned inputs unchanged by both runs; "
        f"S4 {ck.get('S4-no-outbox-write-under-quiet')}: no outbox writes under --quiet; "
        f"S5 {ck.get('S5-no-self-promotion')}: no self-promotion.",
    ]
    events.append(
        {
            **base,
            "event_id": f"w038-a0-selftest-review-{stamp}",
            "event_type": "review",
            "target_id": "A0/validator-artifact",
            "target_path": "artifacts/audit/audit_run.py",
            "target_sha256": validator_sha,
            "reviewer": actor,
            "verdict": "revise",
            "score": 3.0,
            "hard_failures": [],
            "findings": findings,
            "scope": "validator mechanism only; NOT a verdict on the A0 rubric content and does "
            "not count toward the two independent full-schema A0 accepts",
            "evidence_refs": [vrel + "#" + vsha],
            "next_falsifier": "patch audit_run.py to accept relative --out and to write its run "
            "record into the rubric validation block, then re-run both invocations; if both "
            "then succeed and last_run is populated, this revise is falsified.",
        }
    )

    # 4. status
    events.append(
        {
            **base,
            "event_id": f"w038-a0-selftest-status-{stamp}",
            "event_type": "status",
            "node_id": "A0",
            "status": "active",
            "hours": 0.4,
            "summary": "Executed the declared A0 self-test that was never recorded "
            "(validation.last_run=null): run B (absolute --out) exit 0, report "
            f"{run_b.get('report_path')}; run A (relative --out) crashes, no report; "
            "rubric and all pinned inputs unmutated, no outbox writes, no self-promotion. "
            "A full independent A0 rubric verdict at d748a9e3574e is still outstanding "
            "(worker-008 static check is adjacent, not that verdict). Worker evidence only.",
            "evidence_refs": [vrel + "#" + vsha]
            + ([run_b["report_path"] + "#" + run_b["report_sha256"]] if run_b.get("report_path") else []),
            "next_falsifier": "lead-audit re-runs the declared validator on the patched tool; if "
            "the patched run record contradicts this one (different exit code, report binding, "
            "or mutation check), the corresponding check flips.",
        }
    )

    # 5. blocker
    events.append(
        {
            **base,
            "event_id": f"w038-a0-selftest-blocker-{stamp}",
            "event_type": "blocker",
            "node_id": "A0",
            "description": "The declared A0 self-test is now executed and recorded, but the "
            "mechanism is defective and the node still has no independent full-schema verdict at "
            "rubric sha256 d748a9e3574e: (a) audit_run.py crashes on a relative --out (line 335) "
            "before writing any report; (b) it never fills the rubric validation block it is "
            "declared to fill, so last_run/last_run_result/report_sha256 stay null after a "
            "successful run.",
            "needed_to_unblock": "lead-audit patches the --out handling and either writes a "
            "hash-bound run record into the rubric validation block or the controller "
            "adjudicates that this external record satisfies the self-test requirement; a "
            "non-author reviewer must then verdict A0 at d748a9e3574e for G-AUDIT.",
            "evidence_refs": [
                vrel + "#" + vsha,
                "artifacts/worker-038/a0_selftest/run_a_relative_out/stderr.txt",
                "artifacts/audit/audit_run.py#"
                + str(validator_sha),
            ],
            "requested_owner": "astra-lead-audit",
        }
    )

    # --- validate and write ---------------------------------------------------------------
    accepted, rejected = [], []
    for ev in events:
        try:
            validate_event(ev)
            accepted.append(ev)
        except SchemaError as e:
            rejected.append({**ev, "_schema_error": str(e)})
    if accepted:
        with open(OUTBOX, "a") as f:
            for ev in accepted:
                f.write(json.dumps(ev, sort_keys=True) + "\n")
    if rejected:
        REJECTS.write_text("\n".join(json.dumps(r, sort_keys=True) for r in rejected) + "\n")

    # --- checkpoint -----------------------------------------------------------------------
    artifacts = {}
    for p in [
        HERE / "run_selftest.py",
        VERIFICATION,
        HERE / "run_a_relative_out" / "stderr.txt",
        HERE / "run_b_absolute_out" / "stdout.txt",
        HERE / "run_b_absolute_out" / "stderr.txt",
        OUTBOX,
    ]:
        if p.exists():
            artifacts[str(p.relative_to(ROOT))] = {"sha256": sha256_file(p)}
    if run_b.get("report_path"):
        artifacts[run_b["report_path"]] = {"sha256": run_b["report_sha256"]}

    checkpoint = {
        "checkpoint": 1,
        "at": now(),
        "worker": actor,
        "run": "W038-A0-SELFTEST-01",
        "node_id": "A0",
        "gate": "G-AUDIT",
        "class_ids": FROZEN,
        "assignment": "worker-038 self-assigned from the controller's G-AUDIT unmet list: "
        "'A0 has no recorded reviewer verdict' + rubric validation.last_run null; verified "
        "against live worker coverage that no other agent had executed the declared validator.",
        "hours_spent_estimate": 0.5,
        "status": {
            "delivered": True,
            "validation_status": "unverified",
            "result": v["result"],
            "checks": ck,
            "no_completion_claim": "worker cannot set done/passed/gate verdict; no theorem, no "
            "physics result, no C0/C2 merge",
        },
        "verdicts": {
            "rubric_sha256": v["measured_hashes"].get("evaluation_rubric.yaml"),
            "validator_sha256": validator_sha,
            "validator_report_sha256": run_b.get("report_sha256"),
            "relative_out_exit_code": run_a["exit_code"],
            "absolute_out_exit_code": run_b["exit_code"],
        },
        "artifacts": artifacts,
        "outbox_events": [e["event_id"] for e in accepted],
        "rejected_events": [r["event_id"] for r in rejected],
        "open_blockers": {
            "A0-SELFTEST-MECHANISM": "audit_run.py relative --out crash (line 335) and the "
            "rubric validation block never being filled by the declared validator",
            "A0-INDEPENDENT-VERDICT": "no non-author full-schema verdict at d748a9e3574e",
        },
        "next_falsifier": "re-run artifacts/worker-038/a0_selftest/run_selftest.py at the same "
        "pinned hashes; any check flip or report-hash change falsifies this checkpoint.",
        "numerics_lock": "respected: no N1 work, no numerics/spherical_solver/",
    }
    CHECKPOINT.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
    (HERE / "CHECKPOINT_1.json").write_text(
        json.dumps(checkpoint, indent=1, sort_keys=True) + "\n"
    )

    print(f"accepted={len(accepted)} rejected={len(rejected)} -> {OUTBOX.relative_to(ROOT)}")
    print(f"checkpoint -> {CHECKPOINT.relative_to(ROOT)} sha256={sha256_file(CHECKPOINT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
