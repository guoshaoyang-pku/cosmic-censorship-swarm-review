#!/usr/bin/env python3
"""Emit the W014-GNUM-N0-L09-CROSSVERIFY-01 events and write the checkpoint.

Idempotent: event_ids already present in the outbox are not appended again.
Appends to comms/outbox/worker-014.jsonl, mirrors to events_emitted.jsonl, writes
runtime/state/w014_lifecycle09_crossverify_checkpoint.json and appends one line to
artifacts/worker-14/checkpoints.jsonl. No gate verdict, no node status, no canonical write.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms" / "outbox" / "worker-014.jsonl"
CKPT = ROOT / "runtime" / "state" / "w014_lifecycle09_crossverify_checkpoint.json"
CPLOG = ROOT / "artifacts" / "worker-14" / "checkpoints.jsonl"

TASK = "W014-GNUM-N0-L09-CROSSVERIFY-01"
TARGET = "numerics/protocol/lifecycle09_lead_verify.json"
FALSIFIER = (
    "Re-run artifacts/worker-14/lifecycle09_crossverify/verify_l09.py at the pinned inputs. "
    "Falsified if any declared pin moves, any recomputed fit leaves |p-2|>0.3, a ladder is "
    "non-monotone, cross-scheme spread >0.25 or the per-pair R5 rule fails, a cited verdict "
    "loses its token, live taxonomy != 0abb9ed8a961 or lacks AF-WCC-SCALAR-SPH, numerics_lock "
    "!= locked or numerics/spherical_solver appears, the record's map-snapshot claim or the "
    "live G-NUM criteria/unmet state is not as reported, any control fails to fire, or any "
    "pinned input drifts pre/post. A later write to any pinned path voids the verdict for the "
    "new bytes."
)
NOT_CLAIMED = [
    "not a G-NUM gate verdict; gate authority stays Astra / lead-audit",
    "not an N0 node completion or status transition",
    "no numerics_lock release; N1 stays queued",
    "no adjudication of the contested protocol review (reviews/G-NUM-protocol-review.json)",
    "no canonical-path write; read-only over every pinned input",
    "no physics / self-gravity / WCC / SCC claim",
]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def read_ids(path: Path) -> set:
    ids = set()
    if path.exists():
        for line in path.read_text(errors="replace").splitlines():
            try:
                d = json.loads(line)
                if isinstance(d, dict) and d.get("event_id"):
                    ids.add(d["event_id"])
            except json.JSONDecodeError:
                continue
    return ids


def main() -> int:
    report = json.loads((HERE / "report.json").read_text())
    ts = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    created = datetime.now(CST).isoformat(timespec="seconds")
    hashes = {name: sha(HERE / name) for name in
              ("report.json", "verify_l09.py", "PRE_REGISTRATION.md", "README.md",
               "emit_events.py")}
    counts = report["counts"]
    ev = []

    def add(eid, etype, **kw):
        e = {"event_id": f"w014-l09x-{ts}-{eid}", "event_type": etype, "actor": "worker-014",
             "created_at": created, "class_id": "AF-WCC-SCALAR-SPH", "node_id": "N0",
             "gate": "G-NUM", "task_id": TASK}
        e.update(kw)
        ev.append(e)

    for tag, name, atype in (
            ("artifact-report", "report.json", "crossverification_report"),
            ("artifact-instrument", "verify_l09.py", "instrument"),
            ("artifact-prereg", "PRE_REGISTRATION.md", "pre_registration"),
            ("artifact-readme", "README.md", "readme")):
        add(tag, "artifact", artifact_type=atype,
            path=f"artifacts/worker-14/lifecycle09_crossverify/{name}",
            sha256=hashes[name], validation_status="unverified",
            evidence_refs=[f"artifacts/worker-14/lifecycle09_crossverify/{name}"
                           f"#{hashes[name][:12]}",
                           f"{TARGET}#{report['target']['sha256'][:12]}"],
            summary={"report.json": "28/28 checks, 12/12 controls, 0 hard failures; verdict "
                                    + report["verdict"],
                     "verify_l09.py": "read-only deterministic re-runnable verifier (sections "
                                      "A-H)",
                     "PRE_REGISTRATION.md": "predictions P1-P9 declared before measurement; P8 "
                                            "deviation documented in README",
                     "README.md": "result table, P8 deviation addendum, falsifier, non-claims"}
            [name])

    add("claim", "claim", conclusion_type="numerical_evidence_and_process_audit",
        statement=(
            "At the pinned hashes, the lifecycle-09 lead verification record "
            f"{TARGET}#{report['target']['sha256'][:12]} survives an independent read-only "
            "cross-verification: stop-rule items 1-3 are reproduced from raw rows by a separate "
            "pure-Python OLS implementation (lffd 1.999943 / cnfd 1.999864 / cnfem 1.999916, "
            "max |dp| vs declared 0.0, all 4-rung ladders monotone, all |p-2|<=0.3; cross-scheme "
            "spread 7.958116929374093e-05 <= 0.25 and every pair satisfies the protocol 3.8 R5 "
            "rule); F0 re-bind holds at live taxonomy 0abb9ed8a961 rev5 with AF-WCC-SCALAR-SPH; "
            "the three replication verdicts hash-match and carry SUPPORTED / REPRODUCED / "
            "binding-accept tokens at frozen run hash da7c36071995; the numeric lock holds. "
            "Finding L09-F1 was valid at the record's snapshot (01:16:26) and is superseded at "
            f"the live map {report['map_state']['map_sha256'][:12]} by the 01:22:04 refresh; "
            "the live criteria/unmet pair is consistent."),
        assumptions=["the pinned bytes are the verification surface",
                     "the reviewed revision is the hash declared in the events; later writes "
                     "void the verdict for the new bytes"],
        falsifier=FALSIFIER,
        evidence_refs=[f"artifacts/worker-14/lifecycle09_crossverify/report.json"
                       f"#{hashes['report.json'][:12]}",
                       f"{TARGET}#{report['target']['sha256'][:12]}",
                       "numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c",
                       "numerics/results/flat_wave_convergence_rev3.json#da7c36071995",
                       "research_map/formulation_taxonomy.yaml#0abb9ed8a961"],
        does_not_claim=NOT_CLAIMED)

    add("review", "review", target_id=TARGET, reviewer="worker-014", verdict="accept",
        score=4.0, reviewed_sha256=report["target"]["sha256"],
        hard_failures=[],
        findings=[
            "items 1-3 reproduced exactly from raw rows by an independent estimator; all three "
            "replication verdicts hash-match and keep their tokens",
            "L09-F1 was valid for the record's 01:16:26 snapshot and is superseded at the live "
            "map (controller refresh 01:22:04); live G-NUM criteria/unmet are now consistent",
            "advisory W14-L09-R1: lock_compliance.n1_status='queued' is not a live map field; "
            "verifiable only indirectly (N1 locked, no N1 production artifact)"],
        evidence_refs=[f"artifacts/worker-14/lifecycle09_crossverify/report.json"
                       f"#{hashes['report.json'][:12]}",
                       f"{TARGET}#{report['target']['sha256'][:12]}"],
        verdict_scope="worker-level independent cross-verification; not an A1 audit verdict and "
                      "not a G-NUM decision")

    add("status", "status", status="active",
        hours=0.7,
        summary=(
            "CHECKPOINT + EXIT / worker-014. One bounded class-bound task taken (no inbox card "
            f"for this slot): {TASK}, a second independent worker-level cross-verification of "
            "the lifecycle-09 N0/G-NUM lead record. Verdict "
            f"{report['verdict']}: {counts['checks_passed']}/{counts['checks']} checks, "
            f"{counts['controls_fired']}/{counts['controls_total']} controls, 0 hard failures, "
            "all 9 pins byte-stable, deterministic re-run. Advisories: L09-F1 superseded by the "
            "01:22:04 map refresh (was valid for its snapshot); lock n1_status not a map field. "
            "G-NUM stays pending: N0 accept is lead-audit-owned (astra-life04-n0-verify) and "
            "the protocol review stays contested. Worker-level only: no gate verdict, no node "
            "completion, no canonical write."),
        next_falsifier=FALSIFIER,
        evidence_refs=[f"runtime/state/w014_lifecycle09_crossverify_checkpoint.json",
                       f"artifacts/worker-14/lifecycle09_crossverify/report.json"
                       f"#{hashes['report.json'][:12]}",
                       f"{TARGET}#{report['target']['sha256'][:12]}"],
        does_not_claim=NOT_CLAIMED)

    existing = read_ids(OUTBOX)
    if any(str(e).startswith("w014-l09x-") for e in existing):
        print("w014-l09x batch already emitted; no-op (idempotent)")
        return 0
    new = [e for e in ev if e["event_id"] not in existing]
    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTBOX, "a") as f:
        for e in new:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    (HERE / "events_emitted.jsonl").write_text(
        "".join(json.dumps(e, sort_keys=True) + "\n" for e in ev))

    ckpt = {
        "actor": "worker-014", "task_id": TASK,
        "class_id": "AF-WCC-SCALAR-SPH", "node_id": "N0", "gate": "G-NUM",
        "emitted_at": created,
        "verdict": report["verdict"],
        "verdict_scope": "worker-level cross-verification at the pinned hashes only; not a "
                         "G-NUM gate verdict, not an N0 node verdict",
        "counts": counts,
        "targets": {TARGET: report["target"]["sha256"]},
        "pins_measured": {k: v["measured"] for k, v in report["pins"].items()},
        "deliverables": {f"artifacts/worker-14/lifecycle09_crossverify/{k}": v
                         for k, v in hashes.items()},
        "event_ids": [e["event_id"] for e in ev],
        "appended_event_ids": [e["event_id"] for e in new],
        "next_falsifier": FALSIFIER,
        "does_not_claim": NOT_CLAIMED,
    }
    CKPT.write_text(json.dumps(ckpt, indent=1, sort_keys=True) + "\n")
    with open(CPLOG, "a") as f:
        f.write(json.dumps({
            "at": created, "checkpoint_label": "CP15(worker-14/15)", "checkpoint": 15,
            "path": "runtime/state/w014_lifecycle09_crossverify_checkpoint.json",
            "assignment_ref": f"{TASK} (no inbox card; bounded class-bound task from the open "
                               "N0/G-NUM queue)",
            "verdict": report["verdict"],
            "outbox_events": [e["event_id"] for e in new]}, sort_keys=True) + "\n")

    print(f"events emitted: {len(new)} new / {len(ev)} total")
    for e in ev:
        print("  ", e["event_id"], e["event_type"])
    print("checkpoint:", CKPT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
