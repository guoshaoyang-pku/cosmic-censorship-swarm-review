#!/usr/bin/env python3
"""W012-GNUM-C4-REGISTRY-VERIFY-01 — checkpoint writer + outbox emitter.

Builds runtime/state/worker-012_n0_c4_registry_verify_checkpoint.json from the on-disk
artifact hashes, then appends the task's events to comms/outbox/worker-012.jsonl.

Dry-run by default; pass --write to actually write. Idempotence guard: refuses to append an
event_id that already exists in the outbox.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TASK = "W012-GNUM-C4-REGISTRY-VERIFY-01"
CLASS_ID = "AF-WCC-SCALAR-SPH"
OUTBOX = ROOT / "comms/outbox/worker-012.jsonl"
CHECKPOINT = ROOT / "runtime/state/worker-012_n0_c4_registry_verify_checkpoint.json"
CLOSURE = "numerics/protocol/lifecycle08_stoprule_closure_verify.json"
CLOSURE_SHA = "88ec0bf298cbc4de6ae2a6d3038961d404f1c43a64cbaa92f29b6ad6cce77f75"

ARTIFACTS = ["PRE_REGISTRATION.md", "verify_c4_registry.py", "report.json", "README.md"]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    hashes = {a: sha256(HERE / a) for a in ARTIFACTS}
    hashes["emit_events.py"] = sha256(Path(__file__).resolve())
    report = json.loads((HERE / "report.json").read_text())
    now = datetime.now(CST)
    stamp = now.strftime("%Y%m%dT%H%M%S%z")
    iso = now.isoformat(timespec="seconds")

    falsifier = report["falsifier"]
    ev = []
    ev.append({
        "event_id": f"w012-c4reg-{stamp}-status-start",
        "event_type": "status", "created_at": iso, "actor": "worker-012",
        "task_id": TASK, "class_id": CLASS_ID, "node_id": "N0", "gate": "G-NUM",
        "status": "active", "hours": 0.05,
        "summary": ("Took ONE bounded class-bound task W012-GNUM-C4-REGISTRY-VERIFY-01: independent, "
                    "read-only reconciliation of the PROTOCOL rule 2 (C4) registration gap in the N0 "
                    "stop-rule evidence (lead-audit B-N0-R2-1 six-path list vs lifecycle-08 closure "
                    "four-path residual), plus the registry-root mechanism and a controller remediation "
                    "set. Pre-registered before measurement; no canonical write."),
        "evidence_refs": [f"artifacts/worker-012/n0_c4_registry_verify/PRE_REGISTRATION.md#{hashes['PRE_REGISTRATION.md'][:12]}",
                          f"artifacts/worker-012/n0_c4_registry_verify/report.json#{hashes['report.json'][:12]}"],
        "next_falsifier": falsifier,
    })
    for kind, name in (("prereg", "PRE_REGISTRATION.md"), ("instrument", "verify_c4_registry.py"),
                       ("report", "report.json"), ("readme", "README.md")):
        ev.append({
            "event_id": f"w012-c4reg-{stamp}-artifact-{kind}",
            "event_type": "artifact", "created_at": iso, "actor": "worker-012",
            "task_id": TASK, "class_id": CLASS_ID, "node_id": "N0", "gate": "G-NUM",
            "artifact_type": kind,
            "path": f"artifacts/worker-012/n0_c4_registry_verify/{name}",
            "sha256": hashes[name], "validation_status": "unverified",
        })
    ev.append({
        "event_id": f"w012-c4reg-{stamp}-claim-registry",
        "event_type": "claim", "created_at": iso, "actor": "worker-012",
        "task_id": TASK, "class_id": CLASS_ID, "node_id": "N0", "gate": "G-NUM",
        "conclusion_type": "formal_model",
        "statement": (
            "Artifact-and-checker result (not a mathematics claim, not a gate verdict) at the pinned "
            f"registry runtime/state/artifact_hashes.json#{report['pins']['runtime/state/artifact_hashes.json']['sha256'][:16]} "
            f"and research_map/audit_evidence.py#{report['pins']['research_map/audit_evidence.py']['sha256'][:16]}: "
            "of the N0 C4 paths, 8 are registered-match, 3 worker replication-verdict artifacts "
            "(worker-046/057/081) are unregistered-structural because the registry scan roots exclude "
            "artifacts/worker-*, and research_map/formulation_taxonomy.yaml is declared-only (matching "
            "sha256 in `hashes`, absent from `registry`). The lead-audit B-N0-R2-1 six-path list is "
            "superseded for its three numerics/* entries (now registered-match); the live registry-only "
            "residual is 4, reproducing the lifecycle-08 closure list. Controller remediation set is in "
            "the report; no write was made."),
        "assumptions": [
            "the registry file was byte-stable before/after the run (pin recorded)",
            "registry membership + measured sha256 equality is the C4 test; `hashes` vs `registry` authority is the controller's call (both readings reported)",
            "read-only: only the task directory, one checkpoint and this outbox were written",
        ],
        "falsifier": [falsifier,
                      "a classification bucket changing at the same pins (e.g. a worker-046/057/081 artifact appearing as registered-match)"],
        "evidence_refs": [
            f"artifacts/worker-012/n0_c4_registry_verify/report.json#{hashes['report.json'][:12]}",
            f"artifacts/worker-012/n0_c4_registry_verify/PRE_REGISTRATION.md#{hashes['PRE_REGISTRATION.md'][:12]}",
            f"runtime/state/artifact_hashes.json#{report['pins']['runtime/state/artifact_hashes.json']['sha256'][:12]}",
            f"research_map/audit_evidence.py#{report['pins']['research_map/audit_evidence.py']['sha256'][:12]}",
            f"{CLOSURE}#{CLOSURE_SHA[:12]}",
            "reviews/N0-review-final-verify.json#18a0c0d0e77f",
        ],
        "artifact_refs": [f"artifacts/worker-012/n0_c4_registry_verify/report.json#{hashes['report.json'][:12]}"],
        "not_a_gate_verdict": True,
    })
    ev.append({
        "event_id": f"w012-c4reg-{stamp}-review-closure-registration",
        "event_type": "review", "created_at": iso, "actor": "worker-012",
        "task_id": TASK, "class_id": CLASS_ID, "node_id": "N0", "gate": "G-NUM",
        "reviewer": "worker-012", "verdict": "accept", "score": 4.0,
        "target_id": f"{CLOSURE}#{CLOSURE_SHA[:12]}",
        "reviewed_sha256": CLOSURE_SHA,
        "hard_failures": [],
        "counts_as_full_schema_verdict": False,
        "counts_as_gate_verdict": False,
        "counts_as_node_verdict": False,
        "authority_note": ("Worker review event; it cannot set node status, validation_status or a gate "
                           "verdict. N0 stays active, G-NUM pending, numerics_lock LOCKED."),
        "findings": [
            ("F1 scope: this verdict covers only the closure's registration.residual_unregistered field at "
             f"{CLOSURE_SHA[:12]}, independently reconciled against the live registry; it is not a review of the "
             "closure's arithmetic or of the N0 node."),
            ("F2 residual confirmed: registry-only reading gives exactly the closure's 4 paths (3 structural "
             "worker-046/057/081 verdict artifacts + research_map/formulation_taxonomy.yaml declared-only); "
             "0 registered-mismatch, 0 missing-file."),
            ("F3 gap mechanism: research_map/audit_evidence.py registry roots are schemas, ledger, numerics, "
             "reviews, evaluation, artifacts/numerics, runtime/state/controller_verification (+ root "
             "evaluation_rubric.yaml); artifacts/worker-* and research_map/ are unreachable, so the three "
             "structural paths cannot be registered by any checkpoint run without a root extension or an "
             "explicit registration."),
            ("F4 count reconciliation: the lead-audit B-N0-R2-1 six-path list is superseded for its three "
             "numerics/* entries (numerics/CONVERGENCE_PROTOCOL.md, numerics/gates.py, "
             "numerics/results/flat_wave_convergence.json are now registered-match); acting on six today "
             "would over-report."),
            ("F5 rule-2 section ambiguity: PROTOCOL rule 2 does not say whether `hashes` or `registry` is "
             "authoritative; taxonomy satisfies the sentence only in `hashes`. Controller should record the "
             "reading (report.reconciliation.rule2_readings)."),
            ("F6 lock guard: numerics_lock.state locked, numerics/spherical_solver absent, no N1 artifact in "
             "the reviewed evidence; all five in-memory controls fired; classification deterministic across "
             "two processes."),
        ],
        "evidence_refs": [
            f"artifacts/worker-012/n0_c4_registry_verify/report.json#{hashes['report.json'][:12]}",
            f"artifacts/worker-012/n0_c4_registry_verify/README.md#{hashes['README.md'][:12]}",
            f"runtime/state/artifact_hashes.json#{report['pins']['runtime/state/artifact_hashes.json']['sha256'][:12]}",
            f"research_map/audit_evidence.py#{report['pins']['research_map/audit_evidence.py']['sha256'][:12]}",
            f"{CLOSURE}#{CLOSURE_SHA[:12]}",
        ],
        "next_falsifier": falsifier,
    })
    ev.append({
        "event_id": f"w012-c4reg-{stamp}-status-complete",
        "event_type": "status", "created_at": iso, "actor": "worker-012",
        "task_id": TASK, "class_id": CLASS_ID, "node_id": "N0", "gate": "G-NUM",
        "status": "done", "hours": 0.35,
        "worker_task_complete": True, "node_status_unchanged": True,
        "summary": ("CHECKPOINT + worker-level task completion (not a node done and not a gate verdict). "
                    "W012-GNUM-C4-REGISTRY-VERIFY-01 delivered: RESIDUAL_RECONCILED_STRUCTURAL, 12 paths "
                    "classified, 3 structural + 1 declared-only residual, 0 mismatch, five controls fired, "
                    "lock guard passes, cross-process deterministic. N0 stays active, G-NUM pending, "
                    "numerics_lock LOCKED; no canonical artifact, map, registry or detector written."),
        "evidence_refs": [
            f"artifacts/worker-012/n0_c4_registry_verify/report.json#{hashes['report.json'][:12]}",
            f"runtime/state/worker-012_n0_c4_registry_verify_checkpoint.json",
            f"runtime/state/artifact_hashes.json#{report['pins']['runtime/state/artifact_hashes.json']['sha256'][:12]}",
        ],
        "next_falsifier": falsifier,
    })

    checkpoint = {
        "schema": "worker-012/n0-c4-registry-verify/checkpoint/v1",
        "task_id": TASK, "worker": "worker-012",
        "checkpointed_at": iso,
        "verdict": report["verdict"],
        "node_id": "N0", "gate": "G-NUM", "class_id": CLASS_ID,
        "counts": report["counts"],
        "residual_registry_only": report["reconciliation"]["rule2_readings"]["registry_only"],
        "residual_registry_union_hashes": report["reconciliation"]["rule2_readings"]["registry_union_hashes"],
        "registry_pin": {"path": "runtime/state/artifact_hashes.json",
                          "sha256": report["pins"]["runtime/state/artifact_hashes.json"]["sha256"],
                          "checked_at_field_present": report["registry_checked_at"] is not None},
        "audit_evidence_pin": report["pins"]["research_map/audit_evidence.py"]["sha256"],
        "registry_roots": report["registry_root_mechanism"]["roots"],
        "controls_all_pass": all(v for k, v in report["controls"].items() if k.startswith("C")),
        "lock_guard": report["lock_guard"],
        "artifacts": {f"artifacts/worker-012/n0_c4_registry_verify/{k}": v for k, v in hashes.items()},
        "events": [e["event_id"] for e in ev] + [f"w012-c4reg-{stamp}-artifact-checkpoint"],
        "next_falsifier": falsifier,
        "authority_note": ("worker checkpoint; no gate verdict, no node transition, no lock release. "
                           "N0 stays active, G-NUM pending."),
    }

    if not args.write:
        print(json.dumps({"checkpoint": checkpoint, "events": ev}, indent=1))
        return 0

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                continue
    dup = [e["event_id"] for e in ev + [{"event_id": f"w012-c4reg-{stamp}-artifact-checkpoint"}]
           if e["event_id"] in existing]
    if dup:
        print(f"REFUSING duplicate event_ids: {dup}", file=sys.stderr)
        return 2

    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
    ckpt_sha = sha256(CHECKPOINT)
    ckpt_ev = {
        "event_id": f"w012-c4reg-{stamp}-artifact-checkpoint",
        "event_type": "artifact", "created_at": iso, "actor": "worker-012",
        "task_id": TASK, "class_id": CLASS_ID, "node_id": "N0", "gate": "G-NUM",
        "artifact_type": "checkpoint",
        "path": "runtime/state/worker-012_n0_c4_registry_verify_checkpoint.json",
        "sha256": ckpt_sha, "validation_status": "unverified",
    }
    ev.insert(len(ev) - 1, ckpt_ev)
    ev[-1].setdefault("evidence_refs", []).append(
        f"runtime/state/worker-012_n0_c4_registry_verify_checkpoint.json#{ckpt_sha[:12]}")
    with OUTBOX.open("a") as f:
        for e in ev:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(json.dumps({"wrote_checkpoint": str(CHECKPOINT.relative_to(ROOT)),
                      "checkpoint_sha256": ckpt_sha,
                      "appended_events": [e["event_id"] for e in ev]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
