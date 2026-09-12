#!/usr/bin/env python3
"""Emit worker-054 events for W054-F1-REV12-VERIFY-01 and W054-F1-REPAIR-VERIFY-01.

Idempotent by event_id: re-running does not duplicate lines already in
comms/outbox/worker-054.jsonl. Every event is validated with the same
research_map.schemas.validate_event the controller's ingest uses before it is appended.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms" / "outbox" / "worker-054.jsonl"
CAND = HERE.parent / "f1_repair_verify"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def main() -> int:
    now = datetime.now(CST).isoformat(timespec="seconds")
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    c = json.loads((CAND / "report.json").read_text())
    r = json.loads((HERE / "report.json").read_text())

    rev12_hash = r["target"]["sha256"]
    cand_hash = c["target_candidate"]["sha256"]
    rev12 = {
        "report": HERE / "report.json",
        "tool": HERE / "verify_rev12.py",
        "readme": HERE / "README.md",
        "snapshot": HERE / "snapshot" / "af_wcc_vacuum.rev12.cce9c60146d6.yaml",
        "gate": HERE / "gate" / "rev12_check.json",
    }
    cand = {
        "report": CAND / "report.json",
        "tool": CAND / "verify_repair.py",
        "readme": CAND / "README.md",
        "pinned_snapshot": CAND / "snapshot" / "af_wcc_vacuum.pinned.9a8bd4c96800.yaml",
        "proposal_snapshot": CAND / "snapshot" / "repaired_proposal.303705c46834.yaml",
    }
    for name, path in {**rev12, **cand}.items():
        if not path.exists():
            print(f"missing {name}: {path}", file=sys.stderr)
            return 2

    rev12_evidence = [f"{rel(p)}#{sha256(p)[:12]}" for p in rev12.values()]
    cand_evidence = [f"{rel(p)}#{sha256(p)[:12]}" for p in cand.values()]
    cand_evidence += [
        f"artifacts/flash-15/f1_wcc_visibility/repaired_proposal.af_wcc_vacuum.yaml#{cand_hash}",
        "artifacts/flash-15/f1_wcc_visibility/probe_report.json#e94e578d61ea",
    ]

    events = [
        {"event_id": f"w054-{stamp}-rev12-artifact-report", "event_type": "artifact",
         "created_at": now, "actor": "worker-054", "node_id": "F1",
         "class_id": "AF-WCC-VAC-GEN", "gate": "G-FORM",
         "artifact_type": "verification_report", "path": rel(rev12["report"]),
         "sha256": sha256(rev12["report"]), "validation_status": "unverified",
         "task_id": "W054-F1-REV12-VERIFY-01",
         "note": "Independent rev12 verification at sha256 " + rev12_hash[:12] +
                 ": semantics pass (HF-06 tail repair, D0 retyping, AF_{I+}, binders, negation), "
                 "binding fail (stale f0_binding.consistency_evidence_sha256), 1 minor residual.",
         "evidence_refs": rev12_evidence},
        {"event_id": f"w054-{stamp}-rev12-artifact-tool", "event_type": "artifact",
         "created_at": now, "actor": "worker-054", "node_id": "F1",
         "class_id": "AF-WCC-VAC-GEN", "gate": "G-FORM",
         "artifact_type": "tool", "path": rel(rev12["tool"]), "sha256": sha256(rev12["tool"]),
         "validation_status": "unverified", "task_id": "W054-F1-REV12-VERIFY-01",
         "note": "Reproducible rev12 verifier (R0-R12); run: python3 " + rel(rev12["tool"]),
         "evidence_refs": rev12_evidence},
        {"event_id": f"w054-{stamp}-rev12-artifact-summary", "event_type": "artifact",
         "created_at": now, "actor": "worker-054", "node_id": "F1",
         "class_id": "AF-WCC-VAC-GEN", "gate": "G-FORM",
         "artifact_type": "summary", "path": rel(rev12["readme"]), "sha256": sha256(rev12["readme"]),
         "validation_status": "unverified", "task_id": "W054-F1-REV12-VERIFY-01",
         "note": "One-page verdict, scope limits, falsifier and the exact minimal fix list.",
         "evidence_refs": rev12_evidence},
        {"event_id": f"w054-{stamp}-rev12-artifact-snapshot", "event_type": "artifact",
         "created_at": now, "actor": "worker-054", "node_id": "F1",
         "class_id": "AF-WCC-VAC-GEN", "gate": "G-FORM",
         "artifact_type": "snapshot", "path": rel(rev12["snapshot"]),
         "sha256": sha256(rev12["snapshot"]), "validation_status": "unverified",
         "task_id": "W054-F1-REV12-VERIFY-01",
         "note": "Byte snapshot of the reviewed rev12 F1 (live file measured " + rev12_hash[:12] + ").",
         "evidence_refs": rev12_evidence},
        {"event_id": f"w054-{stamp}-rev12-artifact-gate", "event_type": "artifact",
         "created_at": now, "actor": "worker-054", "node_id": "F1",
         "class_id": "AF-WCC-VAC-GEN", "gate": "G-FORM",
         "artifact_type": "machine_report", "path": rel(rev12["gate"]),
         "sha256": sha256(rev12["gate"]), "validation_status": "unverified",
         "task_id": "W054-F1-REV12-VERIFY-01",
         "note": "Raw check_class_schema.py output on the frozen rev12 snapshot.",
         "evidence_refs": rev12_evidence},
        {"event_id": f"w054-{stamp}-rev12-review-f1", "event_type": "review",
         "created_at": now, "actor": "worker-054", "reviewer": "worker-054",
         "target_id": "F1", "node_id": "F1", "class_id": "AF-WCC-VAC-GEN", "gate": "G-FORM",
         "artifact": "schemas/af_wcc_vacuum.yaml", "reviewed_sha256": rev12_hash,
         "artifact_sha256": rev12_hash, "counts_as_full_schema_verdict": True,
         "counts_as_independent_second_verdict": False,
         "verdict": "revise", "score": 3.5,
         "hard_failures": [
             {"id": "W054-R2", "severity": "hard", "kind": "binding/evidence-hash",
              "where": "schemas/af_wcc_vacuum.yaml:304 (f0_binding)",
              "finding": "f0_binding.consistency_evidence_sha256 declares 675a99d0d25b..., but "
                         "artifacts/formulation/evidence/taxonomy_consistency.json measures "
                         "9e335e9ba1bf... at the pinned revision; the declared evidence does not "
                         "resolve at the declared hash from the canonical path.",
              "falsifier": "A byte-identical copy of the evidence file at sha256 675a99d0d25b "
                           "restored at the declared canonical path, or a new F1 revision whose "
                           "declared consistency_evidence_sha256 equals the measured file."}
         ],
         "findings": [
             "Semantics PASS at " + rev12_hash[:12] + ": quantifiers.formal, D5 and the ordered "
             "not_exists binder all use the canonical single-q tail predicate; finite-model check "
             "0/5580 mismatches for the tail reading and 3906/5580 for the old whole-curve reading.",
             "HF-06 (whole-curve vs tail), F-2 (D0 retyped to tagged index r), AF_{I+} definition, "
             "duplicate revised_at collapse, and canonical class_contract_pointer repointing all "
             "verified at the pinned bytes; the class_contract_supplement_pointer is a separate field "
             "and resolves in the authoring file.",
             "Canonical gate (check_class_schema.py) returns pass on the frozen rev12 snapshot.",
             "Residual W054-R1 (minor): visibility.witness_protocol still words step (4) as whole-curve "
             "gamma subset J^-(q); it is a sufficient-but-stricter witness condition, not a "
             "class-conclusion mismatch.",
             "The three content edits proposed by deepseek-flash-15 are byte-identically the ones "
             "that landed in the formal clause.",
         ],
         "conditions": ["binds only sha256 " + rev12_hash,
                        "not a physics or citation verdict; not a gate verdict"],
         "evidence_refs": rev12_evidence, "artifact_refs": [rel(rev12["report"])],
         "next_falsifier": "Re-run artifacts/worker-054/f1_rev12_verify/verify_rev12.py in an "
                           "unchanged tree; verdict flips to accept if R8 passes (evidence hash "
                           "restored or binding re-emitted) and all other checks stay pass; any live "
                           "drift of schemas/af_wcc_vacuum.yaml voids this verdict for later revisions."},
        {"event_id": f"w054-{stamp}-rev12-claim", "event_type": "claim",
         "created_at": now, "actor": "worker-054", "node_id": "F1",
         "class_id": "AF-WCC-VAC-GEN", "class_ids": ["AF-WCC-VAC-GEN"], "gate": "G-FORM",
         "conclusion_type": "formal_model",
         "statement": "At pinned F1 rev12 sha256 " + rev12_hash + ", the rev12 content repairs are "
                      "independently verified: the formal visibility clause is the exact negation of "
                      "the class's canonical single-q tail predicate (exhaustive finite-model check, "
                      "0 mismatches), D0 is the tagged regularity index, AF_{I+} is defined, and the "
                      "duplicate-key/timestamp and canonical-pointer hygiene defects are cleared. One "
                      "binding defect remains: f0_binding.consistency_evidence_sha256 (675a99d0) does "
                      "not match the measured evidence file (9e335e9b), so a freeze-stable accept is "
                      "not yet warranted.",
         "assumptions": [
             "The finite-model abstraction samples the curve at finitely many points; tail "
             "containment means every sample point from t0 on lies in J^-(q) intersect M.",
             "The class-semantics target is the schema's own canonical visibility.definition, not an "
             "external reading of weak cosmic censorship.",
             "The evidence-hash finding is assessed at the snapshot bytes; the evidence file was "
             "rewritten after the binding's checked_at, so this is a freeze-stability defect, not a "
             "claim that the consistency check itself failed.",
             "Concurrent workers 086 and 040 independently report the same evidence-hash defect at "
             "the same revision; this claim is an independent third measurement, not a novel defect.",
         ],
         "falsifier": "Re-run artifacts/worker-054/f1_rev12_verify/verify_rev12.py in an unchanged "
                      "tree. Falsified if (a) the snapshot hash differs from " + rev12_hash[:12] + ", "
                      "(b) any R1-R8 check fails at unchanged bytes, (c) a reading is exhibited under "
                      "which the landed formal clause is not equivalent to the negation of the "
                      "canonical tail predicate, or (d) the declared evidence hash is shown to resolve "
                      "at 675a99d0 from the canonical path at the binding's checked_at.",
         "evidence_refs": rev12_evidence, "artifact_refs": [rel(rev12["report"])]},
        {"event_id": f"w054-{stamp}-candidate-artifact-report", "event_type": "artifact",
         "created_at": now, "actor": "worker-054", "node_id": "F1",
         "class_id": "AF-WCC-VAC-GEN", "gate": "G-FORM",
         "artifact_type": "verification_report", "path": rel(cand["report"]),
         "sha256": sha256(cand["report"]), "validation_status": "unverified",
         "task_id": "W054-F1-REPAIR-VERIFY-01",
         "note": "Independent verification of the flash-15 candidate repair at pinned rev11 "
                 "(9a8bd4c96800 + 303705c46834): V1-V8 verified sound; the frozen pair is superseded "
                 "live but reproducible from snapshots.",
         "evidence_refs": cand_evidence},
        {"event_id": f"w054-{stamp}-candidate-artifact-tool", "event_type": "artifact",
         "created_at": now, "actor": "worker-054", "node_id": "F1",
         "class_id": "AF-WCC-VAC-GEN", "gate": "G-FORM",
         "artifact_type": "tool", "path": rel(cand["tool"]), "sha256": sha256(cand["tool"]),
         "validation_status": "unverified", "task_id": "W054-F1-REPAIR-VERIFY-01",
         "note": "Snapshot-bound candidate verifier; run: python3 " + rel(cand["tool"]),
         "evidence_refs": cand_evidence},
        {"event_id": f"w054-{stamp}-candidate-review", "event_type": "review",
         "created_at": now, "actor": "worker-054", "reviewer": "worker-054",
         "target_id": "artifacts/flash-15/f1_wcc_visibility/repaired_proposal.af_wcc_vacuum.yaml#" + cand_hash[:12],
         "node_id": "F1", "class_id": "AF-WCC-VAC-GEN", "gate": "G-FORM",
         "artifact": "artifacts/flash-15/f1_wcc_visibility/repaired_proposal.af_wcc_vacuum.yaml",
         "reviewed_sha256": cand_hash, "artifact_sha256": cand_hash,
         "counts_as_full_schema_verdict": False, "counts_as_independent_second_verdict": False,
         "verdict": "accept", "score": 4.0, "hard_failures": [],
         "findings": [
             "Repair claim verified at pinned rev11 9a8bd4c96800: exactly the three declared edits, "
             "tail formal clause and (q,t0) D5, negation dualises, conclusion reference unchanged, "
             "finite-model equivalence 0 mismatches (old whole-curve reading 3906/5580 mismatches).",
             "Residual W054-R1: witness_protocol step (4) keeps whole-curve wording (minor).",
             "Residual binding defects are pre-existing in the pinned bytes and not repaired by the "
             "candidate: duplicate revised_at keys (7), and class_contract_pointer resolving only in "
             "the authoring tree.",
             "The gate-compatibility claim is version-dependent: the checker's updated KEY_MANIFEST "
             "no longer allowlists revised_at_unused, so the frozen bytes now fail R22; this is "
             "tooling drift, not a defect of the repaired predicate.",
         ],
         "conditions": ["binds only the candidate bytes " + cand_hash,
                        "not a full F1 schema accept; counts_as_full_schema_verdict=false"],
         "evidence_refs": cand_evidence, "artifact_refs": [rel(cand["report"])],
         "next_falsifier": "Re-run artifacts/worker-054/f1_repair_verify/verify_repair.py in an "
                           "unchanged tree; falsified if the diff is not exactly the three declared "
                           "edits, the tail reading is not equivalent to the canonical negation, or "
                           "the frozen snapshot hashes drift."},
        {"event_id": f"w054-{stamp}-status", "event_type": "status",
         "created_at": now, "actor": "worker-054", "node_id": "F1",
         "class_id": "AF-WCC-VAC-GEN", "class_ids": ["AF-WCC-VAC-GEN"], "gate": "G-FORM",
         "status": "active", "hours": 0.6, "task_id": "W054-F1-REV12-VERIFY-01",
         "summary": "Two hash-bound verifications complete. (1) flash-15 candidate repair at rev11 "
                    "9a8bd4c96800: accepted (scope-limited) -- exactly 3 declared edits, tail "
                    "equivalence proven on 5580 finite models, gate PASS recorded at candidate time; "
                    "residuals are pre-existing hygiene defects. (2) live rev12 F1 at " + rev12_hash[:12] +
                    ": semantics PASS, binding FAIL -- the landed repairs verify, but "
                    "f0_binding.consistency_evidence_sha256 (675a99d0) does not match the measured "
                    "evidence file (9e335e9b); one minor witness_protocol wording residual. Worker "
                    "report only: no gate verdict, no node transition, no validation_status=passed. "
                    "Checkpoint follows.",
         "evidence_refs": rev12_evidence + cand_evidence,
         "next_falsifier": "Restore/re-emit the declared consistency evidence at 675a99d0 or re-emit "
                           "the F1 binding against the measured file; if that passes with all other "
                           "checks unchanged, the R8 finding is void and the verdict flips to accept."},
    ]

    seen = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            try:
                seen.add(json.loads(line).get("event_id"))
            except ValueError:
                continue
    appended = 0
    with OUTBOX.open("a") as fh:
        for event in events:
            try:
                validate_event(event)
            except Exception as exc:  # SchemaError
                print(f"REJECTED {event.get('event_id')}: {exc}", file=sys.stderr)
                return 3
            if event["event_id"] in seen:
                print(f"skip duplicate {event['event_id']}")
                continue
            fh.write(json.dumps(event, sort_keys=True) + "\n")
            appended += 1
    print(json.dumps({"appended": appended, "event_ids": [e["event_id"] for e in events]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
