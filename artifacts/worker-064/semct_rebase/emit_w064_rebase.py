#!/usr/bin/env python3
"""Emit W064-SEMCT-REBASE-01 checkpoint + protocol events (idempotent).

Writes:
  runtime/state/w064_rebase_checkpoint.json
  runtime/state/w064_checkpoints.jsonl            (append, dedup by checkpoint_id)
  comms/outbox/worker-064.jsonl                   (append, dedup by event_id)

Every event is validated against research_map/schemas.py before it is written.
No canonical research-map file is modified.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
ART = REPO / "artifacts" / "worker-064" / "semct_rebase"
OUTBOX = REPO / "comms" / "outbox" / "worker-064.jsonl"
CKPT = REPO / "runtime" / "state" / "w064_rebase_checkpoint.json"
CKPT_LOG = REPO / "runtime" / "state" / "w064_checkpoints.jsonl"
CST = timezone(timedelta(hours=8))
TASK_ID = "W064-SEMCT-REBASE-01"

sys.path.insert(0, str(REPO))
from research_map.schemas import validate_event  # noqa: E402


def now():
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(Path(p).relative_to(REPO))


def main():
    rep = json.loads((ART / "report.json").read_text())
    patch = json.loads((ART / "rebase_patch.json").read_text())
    created = now()

    files = ["report.json", "rebase_patch.json", "manifest_rebased.json", "README.md",
             "semct_rebase_audit.py",
             "rebased_controls/control_comment_only_composite.yaml",
             "rebased_controls/control_conforming_base.yaml",
             "rebased_controls/control_quoted_forbidden_phrase.yaml"]
    hashes = {f: sha(ART / f) for f in files}
    ev = {f: f"{rel(ART / f)}#{hashes[f][:12]}" for f in files}
    snapshot_note = {"inputs": {k: v["sha256"] for k, v in rep["snapshot"].items()}}

    findings = rep["findings"]
    fids = [f["id"] for f in findings]

    # ---------------- events ----------------
    events = []
    for f in files:
        events.append({
            "event_id": f"w064-rebase-01-artifact-{Path(f).stem}",
            "event_type": "artifact", "created_at": created, "actor": "worker-064",
            "node_id": "A1", "class_ids": rep["class_ids"], "gate": "G-AUDIT",
            "artifact_type": "audit_deliverable", "path": rel(ART / f), "sha256": hashes[f],
            "validation_status": "unverified",
            "summary": f"W064-SEMCT-REBASE-01 deliverable: {f}",
            "falsifier": ("Any byte difference from this sha256, or a re-run of "
                          "semct_rebase_audit.py at the pinned snapshot producing different verdicts, "
                          "falsifies the corresponding finding."),
        })
    events.append({
        "event_id": "w064-rebase-01-claim",
        "event_type": "claim", "created_at": created, "actor": "worker-064",
        "node_id": "A1", "gate": "G-AUDIT",
        "class_id": ";".join(rep["class_ids"]),
        "conclusion_type": "numerical_evidence",
        "statement": (
            "At the pinned snapshot (WCC cce9c60146d6, C2 5476a3f2c6bc, C0 55d0a1ea9bda; suite "
            "manifest b2e8bd17892b; gate 000e09e46b2f; KEY_MANIFEST 014e2d301978): (1) the three "
            "frozen controls fail the structural gate on R22 (top-level revised_at_unused absent "
            "from KEY_MANIFEST) and R28 (misplaced finite_codimension_complement->residual_comeager "
            "transfers row in transfer_failures); (2) the rebase of those controls by two "
            "text-preserving edits (nest revised_at_unused under extensions:; delete the 8-line "
            "misplaced row) makes all three pass structural + semantic baseline + hardened; (3) the "
            "full suite with rebased controls and refreshed pins executes with mutants 32/32 "
            "structural, 11/32 baseline, 32/32 hardened, frozen controls accepted=True; (4) "
            "valid_for_calibration remains false only because the adopted semantic auditor rejects "
            "canonical WCC on R03 (binder '(q,t0)' absent from formal sentence); (5) the negative "
            "control with rebased bytes and pre-rebase control pins still exits 2 with exactly 3 "
            "control sha mismatches."),
        "assumptions": [
            "the canonical paths schemas/*.yaml and schemas/semantic_contract_tests/manifest.json are the binding inputs at measurement time",
            "the worker-local repo view copied at P5 is a faithful snapshot of those bytes (hashes recorded)",
            "the runner's integrity semantics (exit 2 = missing/tampered fixture, exit 3 = a control rejected) define the suite state",
            "nesting revised_at_unused under extensions: is semantics-preserving for the control's role (the mutation corpus is untouched)",
        ],
        "falsifier": ("Re-run semct_rebase_audit.py at the pinned bytes: a control failing other than "
                      "R22/R28, a rebased control rejected by any stage, a sensitivity mutant not "
                      "rejected, different mutant counts, or WCC accepted by both semantic stages "
                      "falsifies the corresponding clause."),
        "evidence_refs": [ev["report.json"], ev["rebase_patch.json"],
                          ev["rebased_controls/control_conforming_base.yaml"]],
        "artifact_refs": [rel(ART / "report.json"), rel(ART / "rebase_patch.json")],
        "not_claimed": rep["not_claimed"],
    })
    events.append({
        "event_id": "w064-rebase-01-review",
        "event_type": "review", "created_at": created, "actor": "worker-064",
        "reviewer": "worker-064", "target_id": "schemas/semantic_contract_tests",
        "node_id": "A1", "class_ids": rep["class_ids"], "gate": "G-AUDIT",
        "verdict": "revise", "score": 3.0,
        "hard_failures": [
            "HF-REBASE-1: three frozen controls fail structural on R22 (revised_at_unused) and R28 (misplaced transfers row); ADJ-CONTROL-STALENESS",
            "HF-REBASE-2: adopted semantic auditor rejects canonical WCC with R03 'binder (q,t0) absent from formal sentence' (baseline and hardened), so valid_for_calibration cannot become true",
            "HF-REBASE-3: runner reports blocking_adjudication=[] while valid_for_calibration=false for a conforming-canonical rejection",
        ],
        "findings": [f"{f['id']}: {f['statement'][:400]}" for f in findings],
        "falsifier": ("A run at the pinned bytes in which rebased controls fail a stage, a sensitivity "
                      "mutant is not rejected, WCC is accepted by both semantic stages, or the "
                      "negative control no longer detects stale control pins falsifies the "
                      "corresponding hard failure."),
        "evidence_refs": [ev["report.json"], ev["rebase_patch.json"], ev["manifest_rebased.json"]],
    })
    events.append({
        "event_id": "w064-rebase-01-blocker",
        "event_type": "blocker", "created_at": created, "actor": "worker-064",
        "node_id": "A1", "class_ids": rep["class_ids"], "gate": "G-AUDIT",
        "description": (
            "ADJ-CONTROL-STALENESS has a verified ready-to-apply repair (rebase_patch.json: 2 edits "
            "per control + pin refresh) and is no longer the binding cause of suite validity. The "
            "residual binding cause is canonical WCC vs the adopted semantic auditor: R03 'binder "
            "(q,t0) absent from formal sentence' at WCC cce9c60146d6. Separately, the runner labels "
            "this state blocking_adjudication=[] while valid_for_calibration=false."),
        "needed_to_unblock": [
            "owner astra-lead-formulation applies rebase_patch.json (rebased_controls/* + manifest pin refresh)",
            "owner lead-formulation / semantic-auditor owner resolves WCC R03 at cce9c60146d6 (or records why the semantic stage is excluded from the control basis)",
            "runner owner emits a conforming-canonical adjudication id or the failing fixture list instead of an empty blocking_adjudication",
            "a worker re-runs run_contract_tests.py to certify exit 0 with valid_for_calibration=true",
        ],
        "falsifier": ("A run in which rebased controls and current canonical bytes produce exit 0 with "
                      "valid_for_calibration=true falsifies this blocker."),
        "evidence_refs": [ev["report.json"], ev["rebase_patch.json"],
                          ev["rebased_controls/control_quoted_forbidden_phrase.yaml"]],
    })
    events.append({
        "event_id": "w064-rebase-01-status",
        "event_type": "status", "created_at": created, "actor": "worker-064",
        "node_id": "A1", "class_ids": rep["class_ids"], "gate": "G-AUDIT",
        "status": "active", "hours": 0.6,
        "summary": (
            "W064-SEMCT-REBASE-01 complete at worker level (no inbox card existed for worker-064): "
            "independent rebase + machine verification of the semantic contract suite's frozen "
            "control basis at a pinned, drift-free snapshot. Verdict REBASE_READY / VALIDITY_FALSE. "
            "Rebased controls pass all three stages, sensitivity mutants still rejected, suite "
            "mutants reproduce 32/11/32, control pin tampering still caught; the only remaining "
            "validity blocker is canonical WCC semantic R03. No canonical file modified; node stays "
            "active and no gate is touched."),
        "next_falsifier": ("After the lead applies rebase_patch.json and resolves WCC R03, re-run "
                           "run_contract_tests.py; expect exit 0, valid_for_calibration=true, frozen "
                           "controls 3/3 accepted, canonical controls 3/3 accepted, and unchanged "
                           "32/11/32 mutant counts. Any deviation falsifies the repair."),
        "evidence_refs": [ev["report.json"], ev["rebase_patch.json"], ev["manifest_rebased.json"],
                          ev["README.md"]],
        "not_claimed": rep["not_claimed"],
    })

    # validate all events before writing anything
    outbox_ids = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                try:
                    outbox_ids.add(json.loads(line)["event_id"])
                except Exception:
                    pass
    new_ev = []
    for e in events:
        e.setdefault("class_ids", rep["class_ids"])
        validate_event(e)
        if e["event_id"] not in outbox_ids:
            new_ev.append(e)
    with OUTBOX.open("a") as fh:
        for e in new_ev:
            fh.write(json.dumps(e) + "\n")

    # ---------------- checkpoint ----------------
    ckpt = {
        "checkpoint_id": f"w064-rebase-ckpt-{created.replace(':', '').replace('+', 'p')}",
        "task_id": TASK_ID,
        "actor": "worker-064",
        "instance_id": rep["instance_id"],
        "created_at": created,
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_ids": rep["class_ids"],
        "status": "worker_task_complete_no_node_transition",
        "verdict": "REBASE_READY_VALIDITY_FALSE",
        "snapshot_hashes": {k: v["sha256"] for k, v in rep["snapshot"].items()},
        "canonical_drift_during_window": {k: v["changed"] for k, v in rep["drift"].items()},
        "artifacts": {rel(ART / f): hashes[f] for f in files},
        "results": {
            "controls_before": {k: {"structural_rules": v["structural"]["failed_rules"]}
                                for k, v in rep["baseline"]["controls"].items()},
            "controls_after": {k: {s: v2["verdict"] for s, v2 in v.items()}
                               for k, v in rep["rebased_control_verdicts"].items()},
            "sensitivity_all_rejected": all(v["pass"] for v in rep["sensitivity"].values()),
            "suite_S0_exit": rep["suite_simulations"]["S0_unmodified"]["exit"],
            "suite_S0_integrity_errors": len(rep["suite_simulations"]["S0_unmodified"].get("integrity_errors", [])),
            "suite_S1_exit": rep["suite_simulations"]["S1_rebased_controls_pins_refreshed"]["exit"],
            "suite_S1_summary": rep["suite_simulations"]["S1_rebased_controls_pins_refreshed"]["summary"],
            "suite_S1_validity": rep["suite_simulations"]["S1_rebased_controls_pins_refreshed"]["validity"],
            "suite_S2_exit": rep["suite_simulations"]["S2_stale_control_pins_negative_control"]["exit"],
            "suite_S2_integrity_errors": rep["suite_simulations"]["S2_stale_control_pins_negative_control"].get("integrity_errors", []),
            "suite_S3_alternative_structural_accepted": {k: v["accepted"] for k, v in rep["suite_simulations"]["S3_alternative_delete_key"].items()},
            "residual_blocker_wcc_r03": rep["baseline"]["canonical"]["schemas/af_wcc_vacuum.yaml"]["semantic_baseline"]["failed_rules"],
        },
        "finding_ids": fids,
        "evidence_refs": [ev["report.json"], ev["rebase_patch.json"], ev["manifest_rebased.json"],
                          ev["rebased_controls/control_conforming_base.yaml"]],
        "falsifier": ("Re-run semct_rebase_audit.py at the pinned snapshot: controls failing other than "
                      "R22/R28, a rebased control rejected by any stage, a sensitivity mutant not "
                      "rejected, changed mutant counts, a negative control that no longer catches "
                      "stale control pins, or WCC accepted by both semantic stages falsifies the "
                      "corresponding result."),
        "next_falsifier": ("After the lead applies rebase_patch.json and resolves WCC R03, re-run "
                           "run_contract_tests.py; expect exit 0 and valid_for_calibration=true with "
                           "unchanged 32/11/32 mutant counts."),
        "not_claimed": rep["not_claimed"],
        "outbox": "comms/outbox/worker-064.jsonl",
        "outbox_event_ids": [e["event_id"] for e in events],
    }
    CKPT.write_text(json.dumps(ckpt, indent=1) + "\n")
    existing = set()
    if CKPT_LOG.exists():
        for line in CKPT_LOG.read_text().splitlines():
            if line.strip():
                try:
                    existing.add(json.loads(line)["checkpoint_id"])
                except Exception:
                    pass
    if ckpt["checkpoint_id"] not in existing:
        with CKPT_LOG.open("a") as fh:
            fh.write(json.dumps(ckpt) + "\n")
    print(json.dumps({"events_written": len(new_ev), "events_total": len(events),
                      "checkpoint": str(CKPT), "artifacts": len(files)}, indent=1))


if __name__ == "__main__":
    main()
