#!/usr/bin/env python3
"""W068-FORM-HELDOUT10-XAGENT-15 event emitter (worker-068, bounded class-bound task).

Writes (in this order):
  1. checkpoint_final.json  - worker-local final checkpoint with the full artifact hash set
     and the emitted event-id list;
  2. runtime/state/w068_heldout10xagent15_checkpoint_<stamp>.json - runtime checkpoint;
  3. the event block, appended to comms/outbox/worker-068.jsonl (idempotent by event_id).

Every event is validated with research_map.schemas.validate_event before anything is written;
the emitter fails closed with exit 2 on the first invalid event. Worker events never set
status=done, validation_status=passed, or a gate verdict.

Usage: python3 emit_events.py
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
OUTBOX = ROOT / "comms/outbox/worker-068.jsonl"
RUNTIME = ROOT / "runtime/state"
TASK_ID = "W068-FORM-HELDOUT10-XAGENT-15"
GATE = "G-CLASSBIND (folded into G-AUDIT as calibration evidence)"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]

sys.path.insert(0, str(ROOT))
from research_map.schemas import validate_event  # noqa: E402


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    created = now()

    prereg = HERE / "PREREGISTRATION.json"
    shadow_manifest = HERE / "manifest.json"
    builder = HERE / "build_shadow15.py"
    runner = HERE / "run_xagent15.py"
    report = HERE / "report.json"
    raw = HERE / "raw_verdicts.json"
    ckpt = HERE / "checkpoint.json"
    readme = HERE / "README.md"

    H = {
        "preregistration": sha256_file(prereg),
        "shadow_manifest": sha256_file(shadow_manifest),
        "builder": sha256_file(builder),
        "runner": sha256_file(runner),
        "report": sha256_file(report),
        "raw_verdicts": sha256_file(raw),
        "checkpoint": sha256_file(ckpt),
        "readme": sha256_file(readme),
        "emitter": sha256_file(Path(__file__).resolve()),
    }

    rep = json.loads(report.read_text())
    agg = rep["aggregates"]
    inf = rep["aggregates_informative_arms_only"]
    repl = rep["replication"]

    event_ids = [
        f"w068-x15-01-task-claim-{stamp}",
        f"w068-x15-02-artifact-prereg-{stamp}",
        f"w068-x15-03-artifact-manifest-{stamp}",
        f"w068-x15-04-artifact-builder-{stamp}",
        f"w068-x15-05-artifact-runner-{stamp}",
        f"w068-x15-06-artifact-raw-{stamp}",
        f"w068-x15-07-artifact-report-{stamp}",
        f"w068-x15-08-artifact-readme-{stamp}",
        f"w068-x15-09-artifact-checkpoint-{stamp}",
        f"w068-x15-10-claim-replication-{stamp}",
        f"w068-x15-11-blocker-open-items-{stamp}",
        f"w068-x15-12-complete-{stamp}",
        f"w068-x15-13-checkpoint-{stamp}",
        f"w068-x15-14-checkpoint-confirm-{stamp}",
        f"w068-x15-15-runtime-checkpoint-{stamp}",
    ]

    falsifier = rep["falsifier"]
    next_falsifier = rep["next_falsifier"]
    repl_summary = (f"cross-agent replication of FORM-HELDOUT-10: {repl['rows_agreeing']}/"
                    f"{repl['rows_compared']} verdict agreement; all-mutant union escape "
                    f"{agg['union_escape']} ({agg['union_caught']}/{agg['mutants']} caught); "
                    f"informative C2+C0 arms union escape {inf['union_escape']} "
                    f"({inf['union_caught']}/{inf['mutants']} caught); W arm non-informative "
                    f"(stage B R03 on the untouched F1 canonical); strict validity false with the "
                    f"same reason; all 10 pre-registered predictions matched; snapshot 53/53 "
                    f"bytes stable; no live pin drift.")

    ev = [
        {
            "event_id": event_ids[0], "event_type": "status", "created_at": created,
            "actor": "worker-068", "node_id": "A1", "status": "active", "hours": 0.2,
            "group_id": "formulation", "gate": GATE, "class_ids": CLASS_IDS,
            "task_id": TASK_ID,
            "summary": ("No assignment card exists in comms/inbox for worker-068 (this fleet "
                        "instance). Took ONE bounded class-bound task: W068-FORM-HELDOUT10-XAGENT-15 "
                        "= cross-agent (non-author) replication of the worker-084 FORM-HELDOUT-10 "
                        "rev13 escape census, to close the recorded limit that the corpus's own "
                        "independent verification shared the author's worker id. Measurement only."),
            "evidence_refs": [f"artifacts/worker-068/heldout10xagent15/PREREGISTRATION.json#sha256:{H['preregistration'][:12]}",
                              "comms/PROTOCOL.md"],
            "next_falsifier": next_falsifier,
        },
        {
            "event_id": event_ids[1], "event_type": "artifact", "created_at": created,
            "actor": "worker-068", "node_id": "A1", "group_id": "formulation", "gate": GATE,
            "class_ids": CLASS_IDS, "task_id": TASK_ID, "artifact_type": "preregistration",
            "path": "artifacts/worker-068/heldout10xagent15/PREREGISTRATION.json",
            "sha256": H["preregistration"], "validation_status": "unverified",
            "evidence_refs": [f"artifacts/worker-068/heldout10xagent15/PREREGISTRATION.json#sha256:{H['preregistration'][:12]}"],
            "summary": "Pre-registered question, pins, method, 10 predictions and falsifier, written before any stage run.",
        },
        {
            "event_id": event_ids[2], "event_type": "artifact", "created_at": created,
            "actor": "worker-068", "node_id": "A1", "group_id": "formulation", "gate": GATE,
            "class_ids": CLASS_IDS, "task_id": TASK_ID, "artifact_type": "corpus_manifest",
            "path": "artifacts/worker-068/heldout10xagent15/manifest.json",
            "sha256": H["shadow_manifest"], "validation_status": "unverified",
            "evidence_refs": [f"artifacts/worker-068/heldout10xagent15/manifest.json#sha256:{H['shadow_manifest'][:12]}"],
            "summary": "Shadow manifest, 53 pinned files: stages + KEY_MANIFEST + rule_spec, rev13 canonicals, heldout-10 bases/mutants/controls, and the worker-084 replication target. Hashed before any stage process.",
        },
        {
            "event_id": event_ids[3], "event_type": "artifact", "created_at": created,
            "actor": "worker-068", "node_id": "A1", "group_id": "formulation", "gate": GATE,
            "class_ids": CLASS_IDS, "task_id": TASK_ID, "artifact_type": "harness",
            "path": "artifacts/worker-068/heldout10xagent15/build_shadow15.py",
            "sha256": H["builder"], "validation_status": "unverified",
            "evidence_refs": [f"artifacts/worker-068/heldout10xagent15/build_shadow15.py#sha256:{H['builder'][:12]}"],
            "summary": "Fail-closed shadow builder: verifies each pinned source and corpus fixture against the pre-registration / heldout-10 manifest before copying.",
        },
        {
            "event_id": event_ids[4], "event_type": "artifact", "created_at": created,
            "actor": "worker-068", "node_id": "A1", "group_id": "formulation", "gate": GATE,
            "class_ids": CLASS_IDS, "task_id": TASK_ID, "artifact_type": "measurement_runner",
            "path": "artifacts/worker-068/heldout10xagent15/run_xagent15.py",
            "sha256": H["runner"], "validation_status": "unverified",
            "evidence_refs": [f"artifacts/worker-068/heldout10xagent15/run_xagent15.py#sha256:{H['runner'][:12]}"],
            "summary": "Independent runner: 80 stage processes on 40 fixtures, per-fixture verdict comparison against worker-084 raw verdicts, recomputed aggregates, and leaf-level mutation-isolation audit.",
        },
        {
            "event_id": event_ids[5], "event_type": "artifact", "created_at": created,
            "actor": "worker-068", "node_id": "A1", "group_id": "formulation", "gate": GATE,
            "class_ids": CLASS_IDS, "task_id": TASK_ID, "artifact_type": "raw_stage_verdicts",
            "path": "artifacts/worker-068/heldout10xagent15/raw_verdicts.json",
            "sha256": H["raw_verdicts"], "validation_status": "unverified",
            "evidence_refs": [f"artifacts/worker-068/heldout10xagent15/raw_verdicts.json#sha256:{H['raw_verdicts'][:12]}"],
            "summary": "40 fixture rows with both stage verdicts, failed_rules, per-fixture replication comparison, leaf diffs, validity and aggregates.",
        },
        {
            "event_id": event_ids[6], "event_type": "artifact", "created_at": created,
            "actor": "worker-068", "node_id": "A1", "group_id": "formulation", "gate": GATE,
            "class_ids": CLASS_IDS, "task_id": TASK_ID, "artifact_type": "measurement_report",
            "path": "artifacts/worker-068/heldout10xagent15/report.json",
            "sha256": H["report"], "validation_status": "unverified",
            "evidence_refs": [f"artifacts/worker-068/heldout10xagent15/report.json#sha256:{H['report'][:12]}"],
            "summary": repl_summary,
        },
        {
            "event_id": event_ids[7], "event_type": "artifact", "created_at": created,
            "actor": "worker-068", "node_id": "A1", "group_id": "formulation", "gate": GATE,
            "class_ids": CLASS_IDS, "task_id": TASK_ID, "artifact_type": "report",
            "path": "artifacts/worker-068/heldout10xagent15/README.md",
            "sha256": H["readme"], "validation_status": "unverified",
            "evidence_refs": [f"artifacts/worker-068/heldout10xagent15/README.md#sha256:{H['readme'][:12]}"],
            "summary": "README: question, pins, method, 40/40 replication table, isolation distribution, findings F1-F5, limits, non-claims, falsifier, reproduction.",
        },
        {
            "event_id": event_ids[8], "event_type": "artifact", "created_at": created,
            "actor": "worker-068", "node_id": "A1", "group_id": "formulation", "gate": GATE,
            "class_ids": CLASS_IDS, "task_id": TASK_ID, "artifact_type": "worker_checkpoint",
            "path": "artifacts/worker-068/heldout10xagent15/checkpoint.json",
            "sha256": H["checkpoint"], "validation_status": "unverified",
            "evidence_refs": [f"artifacts/worker-068/heldout10xagent15/checkpoint.json#sha256:{H['checkpoint'][:12]}"],
            "summary": "Run checkpoint: validity, replication counts, aggregates, prediction match, falsifier, stop rule.",
        },
        {
            "event_id": event_ids[9], "event_type": "claim", "created_at": created,
            "actor": "worker-068", "node_id": "A1", "group_id": "formulation", "gate": GATE,
            "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": CLASS_IDS, "task_id": TASK_ID,
            "conclusion_type": "numerical_evidence",
            "statement": (
                "Artifact-and-checker replication measurement (not a mathematical claim, not a gate "
                "verdict): a non-author executor (worker-068) re-ran both pinned class-binding stages "
                "from a fully pinned shadow (stage A check_class_schema.py 000e09e46b2f + KEY_MANIFEST "
                "014e2d301978 pinned in-shadow, stage B spec_conformance_audit.py c79d8ab8440a + rule "
                "spec 40f9bb9e657b; F1 d9cebb9404b2 / F2a e9a27996dfd3 / F2b b2ab6acb2bbe; FROZEN "
                "rev29 815e08079aefbc) over all 40 FORM-HELDOUT-10 fixtures authored by worker-084 and "
                "reproduced 40/40 fixture verdicts including failed_rules (3 frozen canonical + 4 "
                "authored controls + 33 mutants). Recomputed aggregates match the pinned worker-084 "
                "raw verdicts: all-mutant union escape 0.7879 (7/33 caught); informative C2+C0 arms "
                "26/26 union escape (0 caught); uninformative W arm 0/7 union escape with all seven "
                "rejections R03-only; strict validity false with the identical reason 'control "
                "af_wcc_vacuum.yaml rejected: stage B reject [R03]'. Secondary mechanical isolation "
                "audit: 22/33 mutants single-leaf, 9 two-leaf, 2 four-leaf, zero zero-change and zero "
                "base-hash mismatches. All 10 pre-registered predictions matched; 53/53 snapshot bytes "
                "were stable before and after the run and no live pinned input drifted."
            ),
            "assumptions": [
                "The pinned worker-084 heldout-10 manifest/raw verdicts are the intended replication target.",
                "Agreement requires equal stage verdicts and equal failed_rules sets on both stages.",
                "Union escape is defined as stage A pass AND stage B accept; an arm is informative only if its frozen canonical control is accepted by both stages.",
                "This is cross-agent but NON-BLIND executor replication: worker-068 read the heldout-10 report before replicating, so it does not replace blind label adjudication.",
                "The stages are mechanical class-binding instruments; neither decides mathematics or class truth.",
            ],
            "artifact_refs": [
                f"artifacts/worker-068/heldout10xagent15/PREREGISTRATION.json#sha256:{H['preregistration'][:12]}",
                f"artifacts/worker-068/heldout10xagent15/manifest.json#sha256:{H['shadow_manifest'][:12]}",
                f"artifacts/worker-068/heldout10xagent15/raw_verdicts.json#sha256:{H['raw_verdicts'][:12]}",
                f"artifacts/worker-068/heldout10xagent15/report.json#sha256:{H['report'][:12]}",
            ],
            "evidence_refs": [
                f"artifacts/heldout/heldout-10/raw/raw_verdicts.json#sha256:{rep['replication']['target_raw_verdicts_sha256'][:12]}",
                f"artifacts/worker-068/heldout10xagent15/report.json#sha256:{H['report'][:12]}",
                f"artifacts/worker-068/heldout10xagent15/raw_verdicts.json#sha256:{H['raw_verdicts'][:12]}",
                f"artifacts/worker-068/heldout10xagent15/manifest.json#sha256:{H['shadow_manifest'][:12]}",
            ],
            "falsifier": falsifier,
            "next_falsifier": next_falsifier,
        },
        {
            "event_id": event_ids[10], "event_type": "blocker", "created_at": created,
            "actor": "worker-068", "node_id": "A1", "group_id": "formulation", "gate": GATE,
            "class_ids": CLASS_IDS, "task_id": TASK_ID,
            "description": (
                "(1) Cross-agent executor independence is now supplied, but a BLIND non-author label "
                "adjudication of the heldout-10 families is still open; a replicated escape is not yet "
                "a confirmed genuine class-contract violation. (2) The W/F1 arm stays non-informative "
                "at rev13: stage B rejects the untouched F1 canonical on R03 (HF-071R3-01), so all 7 W "
                "mutants are untestable, not caught. (3) The strict corpus validity is false (H5) "
                "because of that same R03 rejection; only the informative C2/C0 arms carry signal. "
                "(4) 11/33 mutants change 2 or 4 leaves (paired-field/list families), so family labels "
                "for those should be adjudicated against the reported leaf witnesses, not assumed to "
                "be single-site."
            ),
            "needed_to_unblock": (
                "Lead-formulation / lead-audit: commission a blind non-author adjudication of the "
                "heldout-10 family labels against the leaf witnesses; resolve the F1 stage-B R03 "
                "defect (HF-071R3-01) or record the W definition axis as unmeasured at rev13; bind "
                "this cross-agent replication to G-AUDIT's class-binding calibration item at the "
                "cited detector hashes."
            ),
            "evidence_refs": [
                f"artifacts/worker-068/heldout10xagent15/report.json#sha256:{H['report'][:12]}",
                f"artifacts/worker-068/heldout10xagent15/raw_verdicts.json#sha256:{H['raw_verdicts'][:12]}",
                f"artifacts/heldout/heldout-10/raw/raw_verdicts.json#sha256:{rep['replication']['target_raw_verdicts_sha256'][:12]}",
            ],
            "next_falsifier": next_falsifier,
        },
        {
            "event_id": event_ids[11], "event_type": "status", "created_at": created,
            "actor": "worker-068", "node_id": "A1", "status": "active", "hours": 0.8,
            "group_id": "formulation", "gate": GATE, "class_ids": CLASS_IDS, "task_id": TASK_ID,
            "summary": ("Bounded worker lifecycle complete (W068-FORM-HELDOUT10-XAGENT-15). "
                        + repl_summary
                        + " Artifacts and events emitted; worker exits for recycling. No node "
                          "completion, validation_status=passed, or gate verdict is claimed; open "
                          "items are carried by w068-x15-11-blocker."),
            "evidence_refs": [f"artifacts/worker-068/heldout10xagent15/README.md#sha256:{H['readme'][:12]}",
                              f"artifacts/worker-068/heldout10xagent15/report.json#sha256:{H['report'][:12]}"],
            "next_falsifier": next_falsifier,
        },
        {
            "event_id": event_ids[12], "event_type": "status", "created_at": created,
            "actor": "worker-068", "node_id": "A1", "status": "active", "hours": 0.8,
            "group_id": "formulation", "gate": GATE, "class_ids": CLASS_IDS, "task_id": TASK_ID,
            "summary": ("CHECKPOINT (worker-068, HELDOUT10-XAGENT-15): valid=false (H5 inherited "
                        "R03 defect, pre-registered); 40/40 fixture verdict agreement with the pinned "
                        "worker-084 raw verdicts; informative C2+C0 arms 26/26 union escape; "
                        "predictions 10/10 matched; snapshot 53/53 stable; no live pin drift."),
            "evidence_refs": [f"artifacts/worker-068/heldout10xagent15/checkpoint.json#sha256:{H['checkpoint'][:12]}",
                              f"artifacts/worker-068/heldout10xagent15/report.json#sha256:{H['report'][:12]}"],
            "next_falsifier": next_falsifier,
        },
    ]

    # ---- final checkpoint (needs the event-id list) ---------------------------
    checkpoint_final = {
        "schema": "worker-068/heldout10xagent15/checkpoint-final/v1",
        "checkpoint_id": "ckpt-w068-heldout10xagent15-final",
        "created_at": created, "worker": "worker-068", "task_id": TASK_ID,
        "node_id": "A1", "gate": GATE, "class_ids": CLASS_IDS,
        "status": rep["validity"]["valid"] and "replication_complete" or
                  "replication_complete_controls_invalid",
        "valid": rep["validity"]["valid"],
        "invalid_reasons": rep["validity"]["invalid_reasons"],
        "artifact_sha256": H,
        "replication": {
            "rows_compared": repl["rows_compared"], "rows_agreeing": repl["rows_agreeing"],
            "full_agreement": repl["full_agreement"],
            "target_raw_verdicts_sha256": repl["target_raw_verdicts_sha256"],
        },
        "aggregates": agg,
        "aggregates_informative_arms_only": inf,
        "predictions_all_match": rep["predictions_all_match"],
        "isolation_distribution": rep["mutation_isolation_audit"]["changed_leaf_count_distribution"],
        "emitted_event_ids": event_ids,
        "primary_evidence_refs": [
            f"artifacts/worker-068/heldout10xagent15/report.json#sha256:{H['report'][:12]}",
            f"artifacts/worker-068/heldout10xagent15/raw_verdicts.json#sha256:{H['raw_verdicts'][:12]}",
            f"artifacts/worker-068/heldout10xagent15/manifest.json#sha256:{H['shadow_manifest'][:12]}",
        ],
        "falsifier": falsifier,
        "next_falsifier": next_falsifier,
        "stop_rule": rep["stop_rule"],
    }
    cf_path = HERE / "checkpoint_final.json"
    cf_path.write_text(json.dumps(checkpoint_final, indent=2) + "\n")
    H["checkpoint_final"] = sha256_file(cf_path)

    runtime_path = RUNTIME / f"w068_heldout10xagent15_checkpoint_{stamp}.json"
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime = dict(checkpoint_final)
    runtime["schema"] = "worker-068/heldout10xagent15/runtime-checkpoint/v1"
    runtime["runtime_checkpoint_path"] = str(runtime_path.relative_to(ROOT))
    runtime["outbox"] = "comms/outbox/worker-068.jsonl"
    runtime["worker_note"] = ("Worker lifecycle complete and exiting for recycling. These events "
                              "describe worker-068 tasks only; node status, gate verdicts and "
                              "validation_status are controller/lead authority.")
    runtime_path.write_text(json.dumps(runtime, indent=2) + "\n")
    H["runtime_checkpoint"] = sha256_file(runtime_path)

    ev.append({
        "event_id": event_ids[13], "event_type": "status", "created_at": created,
        "actor": "worker-068", "node_id": "A1", "status": "active", "hours": 0.8,
        "group_id": "formulation", "gate": GATE, "class_ids": CLASS_IDS, "task_id": TASK_ID,
        "summary": ("Post-checkpoint confirmation: worker-local final checkpoint "
                    "artifacts/worker-068/heldout10xagent15/checkpoint_final.json written with the "
                    "full artifact hash set and the emitted event-id list; the 15-minute global cycle "
                    "ingests these outbox events."),
        "evidence_refs": [f"artifacts/worker-068/heldout10xagent15/checkpoint_final.json#sha256:{H['checkpoint_final'][:12]}"],
        "next_falsifier": next_falsifier,
    })
    ev.append({
        "event_id": event_ids[14], "event_type": "status", "created_at": created,
        "actor": "worker-068", "node_id": "A1", "status": "active", "hours": 0.8,
        "group_id": "formulation", "gate": GATE, "class_ids": CLASS_IDS, "task_id": TASK_ID,
        "summary": ("Runtime checkpoint written under runtime/state for this task with the full "
                    "artifact hash set, the outbox event-id list and the claim/blocker ids; worker "
                    "lifecycle complete and exiting for recycling."),
        "evidence_refs": [f"runtime/state/{runtime_path.name}#sha256:{H['runtime_checkpoint'][:12]}",
                          f"artifacts/worker-068/heldout10xagent15/checkpoint_final.json#sha256:{H['checkpoint_final'][:12]}"],
        "next_falsifier": next_falsifier,
    })

    # ---- fail closed on schema ------------------------------------------------
    for e in ev:
        try:
            validate_event(e)
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"verdict": "SCHEMA_FAILED", "event_id": e.get("event_id"),
                              "error": str(exc)}, indent=1))
            return 2

    # ---- idempotent append ----------------------------------------------------
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:  # noqa: BLE001
                continue
    new = [e for e in ev if e["event_id"] not in existing]
    if new:
        OUTBOX.parent.mkdir(parents=True, exist_ok=True)
        with OUTBOX.open("a") as f:
            for e in new:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(json.dumps({
        "verdict": "EMITTED",
        "events_total": len(ev), "events_appended": len(new),
        "skipped_existing": len(ev) - len(new),
        "outbox": str(OUTBOX.relative_to(ROOT)),
        "checkpoint_final": f"artifacts/worker-068/heldout10xagent15/checkpoint_final.json#sha256:{H['checkpoint_final'][:12]}",
        "runtime_checkpoint": f"runtime/state/{runtime_path.name}#sha256:{H['runtime_checkpoint'][:12]}",
        "artifact_sha256": H,
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
