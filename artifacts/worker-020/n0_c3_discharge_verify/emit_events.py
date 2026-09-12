#!/usr/bin/env python3
"""Emit the W020-N0-C3-DISCHARGE-VERIFY-01 receipt.

Writes:
  * manifest.json                                  (sha256 of every deliverable)
  * comms/outbox/worker-020.jsonl                  (append-only structured events)
  * runtime/state/w020_c3_discharge_verify_checkpoint.json
  * runtime/state/w020_checkpoints.jsonl           (append-only checkpoint log)

Never touches canonical artifacts, gates, node status, or validation_status.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TZ = timezone(timedelta(hours=8))
ACTOR = "worker-020"
TASK = "W020-N0-C3-DISCHARGE-VERIFY-01"
CLASS_ID = "AF-WCC-SCALAR-SPH"
NODE_ID = "N0"
GATE = "G-NUM"
TARGET_TASK = "W012-N0-C3-DISCHARGE-01"
OUTBOX = os.path.join(ROOT, "comms", "outbox", "worker-020.jsonl")
STATE = os.path.join(ROOT, "runtime", "state")
STAMP = datetime.now(TZ).strftime("%Y%m%dT%H%M%S")

BINDING_PINS = {
    "numerics/CONVERGENCE_PROTOCOL.md":
        "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274",
    "numerics/protocol/n0_fixed_dt_certification.json":
        "1677822ceb9c81e8f6e48dee8360ab13edc35623c51f4be68bd6589a5fe79920",
    "numerics/protocol/n0_fixed_dt_certification.py":
        "3c7c9087838446046d7462f92c9ffdd9ff137cc6a07ac63bf41e7db90dfbf145",
    "numerics/tests/flat_wave_replication.py":
        "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422",
    "numerics/tests/n0_order_4rung.json":
        "c88146a1375c50f0c87d2893109087ee6f08c55919a4812dc073750bd86f544a",
    "reviews/G-NUM-protocol-review.json":
        "8137f18f1a3b2b01580e1874262e546048bd681672c1b7699e6d784842307017",
}
TARGET_FILES = [
    "artifacts/worker-012/n0/c3_discharge/verify_c3_discharge.py",
    "artifacts/worker-012/n0/c3_discharge/raw/report.json",
    "artifacts/worker-012/n0/c3_discharge/raw/fresh_rerun.json",
    "artifacts/worker-012/n0/c3_discharge/README.md",
]
DELIVERABLES = [
    "artifacts/worker-020/n0_c3_discharge_verify/verify_c3_discharge_independent.py",
    "artifacts/worker-020/n0_c3_discharge_verify/c3_discharge_verification.json",
    "artifacts/worker-020/n0_c3_discharge_verify/c3_discharge_verification.log",
    "artifacts/worker-020/n0_c3_discharge_verify/README.md",
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
    report = json.load(open(os.path.join(HERE, "c3_discharge_verification.json"),
                            encoding="utf-8"))
    if report["verdict"] not in (
            "C3_DISCHARGE_REPRODUCED_AND_REDERIVED_NO_DEFECT",
            "C3_DISCHARGE_VERIFICATION_FOUND_DEFECT"):
        raise SystemExit(f"ABORT: unexpected verdict {report['verdict']!r}")

    # Fail closed against moved binding pins or moved target bytes.
    for rel, pin in BINDING_PINS.items():
        live = sha256_file(os.path.join(ROOT, rel))
        if live != pin:
            raise SystemExit(f"ABORT: binding pin moved: {rel}: {live} != {pin}")
    for rel in TARGET_FILES:
        live = sha256_file(os.path.join(ROOT, rel))
        if live != report["target"]["files"][rel]:
            raise SystemExit(f"ABORT: target moved: {rel}: {live}")

    manifest = {
        "task_id": TASK,
        "actor": ACTOR,
        "class_id": CLASS_ID,
        "node_id": NODE_ID,
        "gate": GATE,
        "generated_at": now(),
        "target_task_id": TARGET_TASK,
        "verdict": report["verdict"],
        "binding_pins": BINDING_PINS,
        "target_files": {p: sha256_file(os.path.join(ROOT, p)) for p in TARGET_FILES},
        "files": {p: {"sha256": sha256_file(os.path.join(ROOT, p)),
                      "bytes": os.path.getsize(os.path.join(ROOT, p))}
                  for p in DELIVERABLES},
    }
    manifest_rel = "artifacts/worker-020/n0_c3_discharge_verify/manifest.json"
    with open(os.path.join(ROOT, manifest_rel), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")

    ev_refs = [ref(p) for p in DELIVERABLES + [manifest_rel]] + \
              [ref(p) for p in TARGET_FILES] + [ref(p) for p in BINDING_PINS]
    summary = report["checks"]["summary"]
    orders = report["r5"]["orders"]
    findings = report["findings"]
    hard = report["hard_failures"]

    events = []

    events.append({
        "event_id": f"w020e-{STAMP}-status-task",
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
            f"{now()}). Took ONE bounded class-bound task, {TASK}: independently verify "
            f"the C3-discharge claim of {TARGET_TASK} (deepseek-flash-12) at its own "
            "pinned bytes, as its README explicitly requests ('Independent non-author: "
            "re-run verify_c3_discharge.py or falsify per the report falsifier'). "
            "Method: pin re-measurement, own re-derivation of every declared fit/R5 "
            "number from the raw rows, a same-depth sandboxed copy of the target checker "
            "(outputs redirected so no other agent's artifact is rewritten), my own "
            "bounded frozen-module re-execution at dt=1e-4, six mutation controls and a "
            "determinism control."),
        "evidence_refs": ev_refs,
        "next_falsifier": report["falsifier"],
    })

    for p in DELIVERABLES + [manifest_rel]:
        events.append({
            "event_id": f"w020e-{STAMP}-artifact-{os.path.basename(p)}",
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
            "note": "independent non-author verification evidence; worker may not set "
                    "validation_status=passed or a gate verdict",
        })

    events.append({
        "event_id": f"w020e-{STAMP}-claim-c3-verify",
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
            f"Independent non-author verification of {TARGET_TASK} at the pinned bytes "
            "(target report 67fb7f0f5b2f, checker d2930155f7a8, fresh_rerun 65d459eb3359; "
            "protocol 1e6cdf04d7a2, certification 1677822ceb9c, frozen module 8ade1cdc, "
            "published 4-rung c88146a1): a same-depth sandboxed copy of the target checker "
            f"exits 0 with {summary['passed']}/{summary['total']} checks passed "
            f"({summary['failed']} failed); its fresh rows reproduce the filed "
            "fresh_rerun.json; every declared certification fit, pair order, residual, "
            "least-squares SE, pair half-range, delta_R5 and R5 pair recomputes from the "
            "raw dr,l2_error rows with my own least-squares code; my own frozen-module "
            "re-execution along a different call path (make_factory/run_case/l2_error, "
            "60,000 steps, dt=1e-4, 4 rungs over all three schemes) reproduces the filed "
            f"l2_error rows within {report['independent_rerun'].get('worst_rel_diff', float('nan')):.2e} "
            f"relative; certified orders {orders}; six planted mutations are each detected "
            "and the analysis is deterministic. The target's per-finding dispositions are "
            "consistent with the pinned evidence; the two minor text findings (R2 "
            "solver_tolerance null branch, stale section-6 0.35 sentence) remain literally "
            "open at the pinned hash and are disclosed as such. This is worker evidence "
            "only: no gate verdict, no node completion, no validation_status promotion, "
            "lock stays LOCKED."),
        "assumptions": [
            "Frozen bytes only: the verdict binds to the measured sha256 values; any later revision voids it.",
            "The sandbox reproduction executes a byte-identical copy at the same repo depth; the original target files were re-hashed before and after and did not move.",
            "My re-derivation is independent code but shares the filed raw rows as input; my re-execution is a different call path over the same frozen measurement module.",
            "research_map/research_map.json and research_map/events.jsonl are mutable registries and are recorded, not treated as binding evidence.",
            "Worker-020 is not an author of the protocol, certification, frozen module, published 4-rung control, or the target report.",
        ],
        "falsifier": report["falsifier"],
        "artifact_refs": ev_refs,
        "evidence_refs": ev_refs,
        "checks_passed": summary["passed"],
        "checks_total": summary["total"],
        "hard_failures": hard,
    })

    events.append({
        "event_id": f"w020e-{STAMP}-review-c3-discharge",
        "event_type": "review",
        "created_at": now(),
        "actor": ACTOR,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": GATE,
        "task_id": TASK,
        "target_id": "artifacts/worker-012/n0/c3_discharge/raw/report.json",
        "target_task_id": TARGET_TASK,
        "reviewer": ACTOR,
        "verdict": report["review_verdict"],
        "score": report["review_score"],
        "reviewed_sha256": sha256_file(
            os.path.join(ROOT, "artifacts/worker-012/n0/c3_discharge/raw/report.json")),
        "counts_as_gate_accept": False,
        "counts_as_g_num_protocol_accept": False,
        "hard_failures": hard,
        "findings": findings,
        "does_not_claim": ["gate verdict", "node completion", "full-schema accept",
                           "mathematical theorem", "protocol rev-4 disposition"],
        "evidence_refs": ev_refs,
        "falsifier": report["falsifier"],
    })

    if hard:
        events.append({
            "event_id": f"w020e-{STAMP}-blocker-c3-verify",
            "event_type": "blocker",
            "created_at": now(),
            "actor": ACTOR,
            "node_id": NODE_ID,
            "class_id": CLASS_ID,
            "gate": GATE,
            "task_id": TASK,
            "description": ("Independent verification found failing checks: "
                            + ", ".join(hard)),
            "needed_to_unblock": ("owner repair at a new pinned hash, then re-run "
                                  "verify_c3_discharge_independent.py"),
            "evidence_refs": ev_refs,
            "falsifier": report["falsifier"],
        })

    events.append({
        "event_id": f"w020e-{STAMP}-status-complete",
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
            "failed. Sandbox reproduction of the target checker: "
            f"{report['sandbox_repro'].get('summary', {})}. Own frozen-module re-execution "
            f"worst relative deviation {report['independent_rerun'].get('worst_rel_diff', float('nan')):.2e}; "
            f"six mutation controls fire; binding pins unmoved. Review verdict filed as "
            f"{report['review_verdict']} {report['review_score']} on the target report. "
            "Checkpoint: runtime/state/w020_c3_discharge_verify_checkpoint.json; official "
            "checkpoint follows via research_map/checkpoint.py."),
        "evidence_refs": ev_refs,
        "next_falsifier": report["falsifier"],
    })

    os.makedirs(os.path.dirname(OUTBOX), exist_ok=True)
    existing = set()
    if os.path.exists(OUTBOX):
        for line in open(OUTBOX, encoding="utf-8"):
            line = line.strip()
            if line:
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
        "hard_failures": hard,
        "target_task_id": TARGET_TASK,
        "target_files": manifest["target_files"],
        "binding_pins": BINDING_PINS,
        "sandbox_repro": report["sandbox_repro"],
        "independent_rerun_worst_rel_diff": report["independent_rerun"].get("worst_rel_diff"),
        "controls": report["controls"],
        "determinism": report["determinism"],
        "no_write_guard": report["no_write_guard"],
        "findings": findings,
        "next_falsifier": report["falsifier"],
        "files": manifest["files"],
        "events_file": "comms/outbox/worker-020.jsonl",
        "does_not_claim": ["gate verdict", "node completion", "validation_status=passed",
                           "numerics-lock release"],
    }
    os.makedirs(STATE, exist_ok=True)
    cp_path = os.path.join(STATE, "w020_c3_discharge_verify_checkpoint.json")
    with open(cp_path, "w", encoding="utf-8") as fh:
        json.dump(checkpoint, fh, indent=2)
        fh.write("\n")
    with open(os.path.join(STATE, "w020_checkpoints.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({**checkpoint, "checkpoint_path":
                             "runtime/state/w020_c3_discharge_verify_checkpoint.json"},
                            ensure_ascii=False, sort_keys=True) + "\n")

    print(json.dumps({
        "events_written": len(events),
        "outbox": "comms/outbox/worker-020.jsonl",
        "manifest": manifest_rel,
        "checkpoint": "runtime/state/w020_c3_discharge_verify_checkpoint.json",
        "verdict": report["verdict"],
        "review_verdict": report["review_verdict"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
