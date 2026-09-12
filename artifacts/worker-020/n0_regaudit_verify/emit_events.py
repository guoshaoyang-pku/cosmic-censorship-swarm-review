#!/usr/bin/env python3
"""Emit the W020-N0-REGAUDIT-VERIFY-01 receipt.

Writes:
  * manifest.json                                       (sha256 of every deliverable/pin)
  * comms/outbox/worker-020.jsonl                       (append-only structured events)
  * runtime/state/w020_regaudit_verify_checkpoint.json
  * runtime/state/w020_checkpoints.jsonl                (append-only checkpoint log)

Every event is validated with research_map.schemas.validate_event before it is
written.  Fails closed if any binding pin has moved or any event id already
exists.  Never touches canonical artifacts, gates, node status, validation_status
or the numerics lock.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)

from research_map.schemas import validate_event  # noqa: E402

TZ = timezone(timedelta(hours=8))
ACTOR = "worker-020"
TASK = "W020-N0-REGAUDIT-VERIFY-01"
CLASS_ID = "AF-WCC-SCALAR-SPH"
NODE_ID = "N0"
GATE = "G-NUM"
TARGET_TASK = "LNUM-LIFECYCLE-06/N0-REGISTRATION-DRIFT-AUDIT"

OUTBOX = os.path.join(ROOT, "comms", "outbox", "worker-020.jsonl")
STATE = os.path.join(ROOT, "runtime", "state")
STAMP = datetime.now(TZ).strftime("%Y%m%dT%H%M%S")

BINDING_PINS = {
    "numerics/protocol/n0_registration_drift_audit.json":
        "22edbcc61df7dc7cd574fb43e4ef6c09ae12f89f1ebe34869b00a5b27384c632",
    "numerics/N0_CLASS_BINDING_AUTHORITY.json":
        "effd20b0ea094a8dfd4f686e62c49b1667622337efd6a7c154f7fadae0b98419",
    "numerics/protocol/n0_fixed_dt_certification.json":
        "1677822ceb9c81e8f6e48dee8360ab13edc35623c51f4be68bd6589a5fe79920",
    "numerics/CONVERGENCE_PROTOCOL.md":
        "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274",
    "numerics/results/flat_wave_convergence_rev3.json":
        "da7c360719950f7ef6be2624391dee464f8c818a0be74ec44f0f8c70d2b28ac3",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "numerics/gates.py":
        "fcd1d70991b6eade4aa993dc49b6103e338f68320aabb955d97da5a8f55d996e",
}
TARGET_FILES = [
    "artifacts/worker-046/n0_fixed_dt_independent/verification.json",
    "artifacts/worker-057/n0_fixeddt_verify/report.json",
    "artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json",
]
DELIVERABLES = [
    "artifacts/worker-020/n0_regaudit_verify/verify_regaudit_independent.py",
    "artifacts/worker-020/n0_regaudit_verify/regaudit_verification.json",
    "artifacts/worker-020/n0_regaudit_verify/regaudit_verification.log",
    "artifacts/worker-020/n0_regaudit_verify/README.md",
]
SNAPSHOTS = [
    "artifacts/worker-020/n0_regaudit_verify/snapshots/target_22edbcc61df7.json",
    "artifacts/worker-020/n0_regaudit_verify/snapshots/authority_effd20b0ea09.json",
    "artifacts/worker-020/n0_regaudit_verify/snapshots/certification_1677822ceb9c.json",
    "artifacts/worker-020/n0_regaudit_verify/snapshots/protocol_1e6cdf04d7a2.md",
    "artifacts/worker-020/n0_regaudit_verify/snapshots/rev3_da7c36071995.json",
    "artifacts/worker-020/n0_regaudit_verify/snapshots/taxonomy_0abb9ed8a961.yaml",
    "artifacts/worker-020/n0_regaudit_verify/snapshots/artifact_hashes_4affd733210b.json",
    "artifacts/worker-020/n0_regaudit_verify/snapshots/research_map_5ab4bed18107.json",
]


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(rel: str, short: int = 12) -> str:
    return f"{rel}#{sha256_file(os.path.join(ROOT, rel))[:short]}"


def main() -> int:
    report_path = os.path.join(HERE, "regaudit_verification.json")
    report = json.load(open(report_path, encoding="utf-8"))
    if report["verdict"] != "REGAUDIT_CENSUS_AND_ORDER_REFIT_INDEPENDENTLY_REPRODUCED":
        raise SystemExit(f"ABORT: unexpected verdict {report['verdict']!r}")
    if report["review_verdict"] != "accept" or report["checks"]["failed"] != 0:
        raise SystemExit("ABORT: report is not a clean accept")

    # Fail closed against moved binding pins / moved targets.
    for rel, pin in BINDING_PINS.items():
        live = sha256_file(os.path.join(ROOT, rel))
        if live != pin:
            raise SystemExit(f"ABORT: binding pin moved: {rel}: {live} != {pin}")
    if sha256_file(os.path.join(ROOT, report["target"]["path"])) != report["target"]["measured_sha256"]:
        raise SystemExit("ABORT: target moved since verification")
    if sha256_file(os.path.join(ROOT, report["companion"]["path"])) != report["companion"]["measured_sha256"]:
        raise SystemExit("ABORT: companion moved since verification")
    for rel in TARGET_FILES:
        row = next(r for r in report["replication_verdicts"] if r["path"] == rel)
        if sha256_file(os.path.join(ROOT, rel)) != row["disk_sha256"]:
            raise SystemExit(f"ABORT: replication verdict moved: {rel}")

    manifest = {
        "task_id": TASK,
        "actor": ACTOR,
        "slot": "020",
        "class_id": CLASS_ID,
        "node_id": NODE_ID,
        "gate": GATE,
        "generated_at": now(),
        "target_task_id": TARGET_TASK,
        "verdict": report["verdict"],
        "review_verdict": report["review_verdict"],
        "review_score": report["review_score"],
        "checks": report["checks"] | {"items": None},
        "binding_pins": BINDING_PINS,
        "target_files": {p: sha256_file(os.path.join(ROOT, p)) for p in TARGET_FILES},
        "files": {p: {"sha256": sha256_file(os.path.join(ROOT, p)),
                      "bytes": os.path.getsize(os.path.join(ROOT, p))}
                  for p in DELIVERABLES},
        "snapshots": {p: {"sha256": sha256_file(os.path.join(ROOT, p)),
                          "bytes": os.path.getsize(os.path.join(ROOT, p))}
                      for p in SNAPSHOTS if os.path.exists(os.path.join(ROOT, p))},
        "findings": report["findings"],
        "falsifier": report["falsifier"],
    }
    del manifest["checks"]["items"]
    manifest_rel = "artifacts/worker-020/n0_regaudit_verify/manifest.json"
    with open(os.path.join(ROOT, manifest_rel), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")

    ev_refs = [ref(p) for p in DELIVERABLES + [manifest_rel]] + \
              [ref(p) for p in BINDING_PINS]
    summary = report["checks"]
    xs = report["order_refit"]["cross_scheme"]["max_pairwise_abs_diff"]

    events = []

    events.append({
        "event_id": f"w020f-{STAMP}-status-task",
        "event_type": "status",
        "created_at": now(),
        "actor": ACTOR,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": GATE,
        "task_id": TASK,
        "status": "active",
        "hours": 0.5,
        "summary": (
            "No assignment card exists in comms/inbox for worker-020 (fleet instance "
            f"{now()}). Took ONE bounded class-bound task, {TASK}: independent non-author "
            "verification of the numerics lead's lifecycle-06 registration-drift audit "
            "numerics/protocol/n0_registration_drift_audit.json#22edbcc61df7 and its "
            "companion class-binding authority record numerics/N0_CLASS_BINDING_AUTHORITY.json"
            "#effd20b0ea09 (whose own review_request asks for an independent review at that "
            "hash). Method: frozen snapshots, own hashing/registry census over all 13 declared "
            "pins, own closed-form least-squares re-derivation of every fit/SE/residual/pair "
            "order/delta_R5 from the raw rows (numpy.polyfit cross-check), replication-verdict "
            "and A1..A6 binding re-checks, a fresh read-only numerics/gates.py run, six "
            "planted-defect controls, determinism and pin-before/after guards."),
        "evidence_refs": ev_refs,
        "next_falsifier": report["falsifier"],
    })

    for p in DELIVERABLES + [manifest_rel]:
        events.append({
            "event_id": f"w020f-{STAMP}-artifact-{os.path.basename(p)}",
            "event_type": "artifact",
            "created_at": now(),
            "actor": ACTOR,
            "node_id": NODE_ID,
            "class_id": CLASS_ID,
            "gate": GATE,
            "task_id": TASK,
            "artifact_type": ("verification_tool" if p.endswith(".py") else
                              "verification_report" if p.endswith(".json") else
                              "run_log" if p.endswith(".log") else
                              "readme" if p.endswith(".md") else "evidence"),
            "path": p,
            "sha256": sha256_file(os.path.join(ROOT, p)),
            "bytes": os.path.getsize(os.path.join(ROOT, p)),
            "validation_status": "unverified",
            "evidence_refs": [ref(p)],
            "note": ("independent non-author verification evidence; worker may not set "
                     "validation_status=passed or a gate verdict"),
        })

    for p in SNAPSHOTS:
        if os.path.exists(os.path.join(ROOT, p)):
            events.append({
                "event_id": f"w020f-{STAMP}-artifact-snap-{os.path.basename(p)}",
                "event_type": "artifact",
                "created_at": now(),
                "actor": ACTOR,
                "node_id": NODE_ID,
                "class_id": CLASS_ID,
                "gate": GATE,
                "task_id": TASK,
                "artifact_type": "frozen_snapshot",
                "path": p,
                "sha256": sha256_file(os.path.join(ROOT, p)),
                "bytes": os.path.getsize(os.path.join(ROOT, p)),
                "validation_status": "unverified",
                "evidence_refs": [ref(p)],
                "note": "byte-identical frozen input snapshot at the measured hash",
            })

    events.append({
        "event_id": f"w020f-{STAMP}-claim-regaudit",
        "event_type": "claim",
        "created_at": now(),
        "actor": ACTOR,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
        "gate": GATE,
        "task_id": TASK,
        "conclusion_type": "numerical_evidence",
        "statement": (
            "Independent non-author verification of the N0 registration-drift audit at "
            "22edbcc61df7 and the companion authority record at effd20b0ea09: all 13 declared "
            "pins re-measured with my own hashing/registry code (10 match, 3 genuinely "
            "unregistered but present at declared disk hashes, 0 mismatch, 0 missing); every "
            "declared fixed-dt fit order, pair order, least-squares SE, residual and delta_R5 "
            "re-derives bitwise (absolute difference 0.0) from the raw dr/l2_error rows of "
            f"n0_fixed_dt_certification.json; cross-scheme max |dp| = {xs:.6e} <= 0.25; all "
            "fits inside |p-2| <= 0.3; lock stays LOCKED with N1_BLOCKED / "
            "production_allowed=false and no solver path present; the A1..A6 binding claims "
            "hold against live taxonomy/carrier/protocol bytes; 115/115 checks pass and six "
            "planted mutations each fire. One soft finding (companion published_at is "
            "future-dated versus its mtime, same class as the audit's ANOM-1 but not listed) "
            "and one inherited-open registration gap re-measured and left with its owner. "
            "Worker evidence only: no gate verdict, no node completion, no validation_status "
            "promotion, no lock release."),
        "assumptions": [
            "Frozen bytes only: the verdict binds to the measured sha256 values; any later revision voids it.",
            "My census/registry code and my least-squares re-derivation are independent re-implementations; the audit generator numerics/protocol/audit_registration_drift.py was not imported.",
            "My re-derivation shares the filed raw rows as input; a re-execution of the measurement module is not repeated here (worker-020 verified that module separately in W020-N0-C3-DISCHARGE-VERIFY-01).",
            "runtime/state/artifact_hashes.json and research_map/research_map.json are mutable registries recorded, not treated as binding pins.",
            "Worker-020 is not an author of the audit, the authority record, the certification, the frozen module or the three replication verdicts.",
        ],
        "falsifier": report["falsifier"],
        "artifact_refs": ev_refs,
        "evidence_refs": ev_refs,
        "checks_passed": summary["passed"],
        "checks_total": summary["total"],
        "hard_failures": report["hard_failures"],
    })

    events.append({
        "event_id": f"w020f-{STAMP}-review-regaudit",
        "event_type": "review",
        "created_at": now(),
        "actor": ACTOR,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": GATE,
        "task_id": TASK,
        "target_id": report["target"]["path"],
        "target_task_id": TARGET_TASK,
        "reviewer": ACTOR,
        "verdict": report["review_verdict"],
        "score": report["review_score"],
        "reviewed_sha256": report["target"]["measured_sha256"],
        "counts_as_gate_accept": False,
        "counts_as_g_num_protocol_accept": False,
        "hard_failures": report["hard_failures"],
        "findings": report["findings"],
        "does_not_claim": ["gate verdict", "node completion", "full-schema accept",
                           "mathematical theorem", "protocol contest disposition"],
        "evidence_refs": ev_refs,
        "falsifier": report["falsifier"],
    })

    events.append({
        "event_id": f"w020f-{STAMP}-review-authority",
        "event_type": "review",
        "created_at": now(),
        "actor": ACTOR,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": GATE,
        "task_id": TASK,
        "target_id": report["companion"]["path"],
        "target_task_id": TARGET_TASK,
        "reviewer": ACTOR,
        "verdict": report["review_verdict"],
        "score": report["review_score"],
        "reviewed_sha256": report["companion"]["measured_sha256"],
        "counts_as_gate_accept": False,
        "counts_as_g_num_protocol_accept": False,
        "hard_failures": report["hard_failures"],
        "findings": [f for f in report["findings"] if f["id"] in ("F1", "F2", "F5")],
        "does_not_claim": ["gate verdict", "node completion", "controller ratification",
                           "class-binding adjudication"],
        "evidence_refs": ev_refs,
        "falsifier": report["falsifier"],
    })

    events.append({
        "event_id": f"w020f-{STAMP}-status-complete",
        "event_type": "status",
        "created_at": now(),
        "actor": ACTOR,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": GATE,
        "task_id": TASK,
        "status": "active",
        "hours": 0.5,
        "summary": (
            f"{TASK} complete at worker level (completion claim only: workers cannot set "
            f"done/passed or a gate verdict). Verdict {report['verdict']}; "
            f"{summary['passed']}/{summary['total']} checks passed, {summary['failed']} "
            f"failed; six mutation controls fire; binding pins unmoved. Review filed as "
            f"{report['review_verdict']} {report['review_score']} on both the audit "
            f"22edbcc61df7 and the companion authority record effd20b0ea09. Soft finding: "
            "companion published_at is future-dated vs its mtime (ANOM-1 class, not listed). "
            "Inherited open: three replication verdicts still unregistered "
            "(lnum-blocker-80ea3e6b3923ea78ccac), re-measured not re-filed. Checkpoint: "
            "runtime/state/w020_regaudit_verify_checkpoint.json; official checkpoint follows "
            "via research_map/checkpoint.py."),
        "evidence_refs": ev_refs,
        "next_falsifier": report["falsifier"],
    })

    # ---- validate every event against the canonical schema ----------------
    for e in events:
        try:
            validate_event(dict(e))
        except Exception as exc:
            raise SystemExit(f"ABORT: event {e.get('event_id')} fails schema: {exc}")

    existing = set()
    if os.path.exists(OUTBOX):
        for line in open(OUTBOX, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                continue
    dupes = [e["event_id"] for e in events if e["event_id"] in existing]
    if dupes:
        raise SystemExit(f"ABORT: event ids already emitted: {dupes}")
    with open(OUTBOX, "a", encoding="utf-8") as fh:
        for e in events:
            fh.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")

    checkpoint = {
        "task_id": TASK,
        "actor": ACTOR,
        "slot": "020",
        "class_id": CLASS_ID,
        "node_id": NODE_ID,
        "gate": GATE,
        "created_at": now(),
        "verdict": report["verdict"],
        "review_verdict": report["review_verdict"],
        "review_score": report["review_score"],
        "checks": summary,
        "hard_failures": report["hard_failures"],
        "target_task_id": TARGET_TASK,
        "target": report["target"],
        "companion": report["companion"],
        "pin_census": report["pin_census"],
        "cross_scheme_max_abs_diff": xs,
        "controls": report["controls"],
        "determinism": report["determinism"],
        "no_write_guard": report["no_write_guard"],
        "lock_compliance": report["lock_compliance"],
        "findings": report["findings"],
        "binding_pins": BINDING_PINS,
        "target_files": manifest["target_files"],
        "next_falsifier": report["falsifier"],
        "files": manifest["files"],
        "snapshots": manifest["snapshots"],
        "events_file": "comms/outbox/worker-020.jsonl",
        "does_not_claim": ["gate verdict", "node completion", "validation_status=passed",
                           "numerics-lock release", "controller ratification"],
    }
    os.makedirs(STATE, exist_ok=True)
    cp_path = os.path.join(STATE, "w020_regaudit_verify_checkpoint.json")
    with open(cp_path, "w", encoding="utf-8") as fh:
        json.dump(checkpoint, fh, indent=2)
        fh.write("\n")
    with open(os.path.join(STATE, "w020_checkpoints.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({**checkpoint, "checkpoint_path":
                             "runtime/state/w020_regaudit_verify_checkpoint.json"},
                            ensure_ascii=False, sort_keys=True) + "\n")

    print(json.dumps({
        "events_written": len(events),
        "outbox": "comms/outbox/worker-020.jsonl",
        "manifest": manifest_rel,
        "checkpoint": "runtime/state/w020_regaudit_verify_checkpoint.json",
        "verdict": report["verdict"],
        "review_verdict": report["review_verdict"],
        "review_score": report["review_score"],
        "checks": summary,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
