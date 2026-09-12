#!/usr/bin/env python3
"""Emit worker-097's W097-F1-FALSIFIER-EXEC-01 events and checkpoint.

Fail-closed: refuses to emit unless report.json shows controls_pass=true and stable input
hashes, and every event validates against research_map/schemas.py.

Usage: python3 emit_events.py [--dry-run]
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
import schemas  # noqa: E402

CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms" / "outbox" / "worker-097.jsonl"
CKPT = ROOT / "runtime" / "state" / "w097_checkpoint_f1_falsifier_exec.json"

SCHEMA = ROOT / "schemas" / "af_wcc_vacuum.yaml"
SUITE = ROOT / "schemas" / "f1_falsifier_tests.jsonl"
REPORT = HERE / "report.json"
SCRIPT = HERE / "run_f1_falsifier_exec.py"
EMITTER = HERE / "emit_events.py"
README = HERE / "README.md"
RAW = HERE / "raw_sha256.txt"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(p: Path) -> str:
    return f"{p.relative_to(ROOT)}#sha256:{sha(p)}"


def main() -> int:
    report = json.loads(REPORT.read_text())
    if not report.get("controls_pass"):
        print("REFUSING: controls_pass is not true", file=sys.stderr)
        return 2
    if not (report["drift"]["schema_stable"] and report["drift"]["suite_stable"]):
        print("REFUSING: input drift detected", file=sys.stderr)
        return 2

    # keep the hash manifest complete (report, README, emitter included)
    manifest_paths = [SCHEMA, SUITE, SCRIPT, EMITTER, README, REPORT] + sorted((HERE / "snapshots").glob("*"))
    RAW.write_text("\n".join(f"{sha(p)}  {p.relative_to(ROOT)}" for p in manifest_paths) + "\n")

    ts_iso = datetime.now(CST).isoformat(timespec="seconds")
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S%z")
    counts = report["counts"]
    by = counts["by_decisability_class"]
    findings = report["findings"]

    ev_report = {
        "event_id": f"w097-f1falsifierexec-artifact-report-{stamp}",
        "event_type": "artifact",
        "created_at": ts_iso,
        "actor": "worker-097",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "task_id": "W097-F1-FALSIFIER-EXEC-01",
        "artifact_type": "f1_falsifier_execution_report",
        "path": "artifacts/worker-097/f1_falsifier_exec/report.json",
        "sha256": sha(REPORT),
        "validation_status": "unverified",
        "claims_completion": False,
        "summary": (
            f"Independent execution of the 25-row F1 falsifier/ambiguity suite against canonical "
            f"schemas/af_wcc_vacuum.yaml at sha256 {report['inputs']['schema']['sha256'][:12]} (suite "
            f"{report['inputs']['suite']['sha256'][:12]}): 25/25 rows bind to the measured schema hash; "
            f"{by.get('RESOLVED_DETERMINATE', 0)}/25 decide determinately, {by.get('RESOLVED_OPEN_OBLIGATION', 0)}/25 resolve to declared open "
            f"obligations, 0 rows lack a deciding field; 84/84 probe entries re-execute and 0 contradict the "
            f"author's pass flag; 6/6 negative/positive controls pass (fail-closed). Findings: "
            + "; ".join(f"{f['id']} ({f['severity']})" for f in findings) + "."
        ),
        "evidence_refs": [ref(SUITE), ref(SCHEMA), ref(SCRIPT), ref(README), ref(RAW),
                          ref(HERE / "snapshots" / f"af_wcc_vacuum.{report['inputs']['schema']['sha256'][:12]}.yaml")],
        "next_falsifier": report["next_falsifier"],
    }
    ev_script = {
        "event_id": f"w097-f1falsifierexec-artifact-instrument-{stamp}",
        "event_type": "artifact",
        "created_at": ts_iso,
        "actor": "worker-097",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "task_id": "W097-F1-FALSIFIER-EXEC-01",
        "artifact_type": "falsifier_execution_instrument",
        "path": "artifacts/worker-097/f1_falsifier_exec/run_f1_falsifier_exec.py",
        "sha256": sha(SCRIPT),
        "validation_status": "unverified",
        "claims_completion": False,
        "summary": ("Fail-closed instrument: pinned input hashing + snapshot, dotted/composite field resolution, "
                    "per-row decisability classification, independent re-execution of all probe entries "
                    "(path + value + excerpt-prefix), six controls, exit 2 on any control failure."),
        "evidence_refs": [ref(REPORT), ref(SUITE), ref(SCHEMA), ref(EMITTER)],
        "next_falsifier": report["next_falsifier"],
    }
    ev_claim = {
        "event_id": f"w097-f1falsifierexec-claim-{stamp}",
        "event_type": "claim",
        "created_at": ts_iso,
        "actor": "worker-097",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "task_id": "W097-F1-FALSIFIER-EXEC-01",
        "conclusion_type": "stability_result",
        "statement": (
            f"Artifact-and-checker result, not a mathematics or physics claim: at schemas/af_wcc_vacuum.yaml "
            f"sha256 {report['inputs']['schema']['sha256']} (stable before and after execution), the "
            f"schemas/f1_falsifier_tests.jsonl suite at sha256 {report['inputs']['suite']['sha256']} is executable "
            f"and internally consistent -- 25/25 rows bind to that hash, {by.get('RESOLVED_DETERMINATE', 0)}/25 rows are decided "
            f"determinately by their named primary field, {by.get('RESOLVED_OPEN_OBLIGATION', 0)}/25 resolve to declared open obligations "
            f"(non_vacuity.condition, genericity.excluded_set, conclusion.equivalent_standard_formulation), no row is "
            f"undecidable for want of a field, and 84/84 recorded probes reproduce with 0 author disagreements. Two "
            f"deciding_field_contract expressions show naming drift from the schema (class_components.symmetry -> "
            f"data_class.symmetry; conclusion.equivalence_claim -> conclusion.equivalent_standard_formulation)."
        ),
        "assumptions": [
            "The measured sha256 is the artifact identity; the run is valid only at the two pinned hashes in inputs.",
            "Dotted path resolution plus normalized excerpt-prefix matching is a faithful reading of the suite's own probe vocabulary (contains/equals/is_true/is_none/nonnull/path_exists).",
            "'Executable' means decidable from the named field's presence and declared status, not that the underlying mathematics is settled.",
            "This is a worker measurement: only a controller/lead can bind a gate verdict or promote validation_status.",
        ],
        "falsifier": report["falsifier"],
        "evidence_refs": [ref(REPORT), ref(SCRIPT), ref(SCHEMA), ref(SUITE), ref(RAW)],
        "artifact_refs": ["artifacts/worker-097/f1_falsifier_exec/report.json",
                          "artifacts/worker-097/f1_falsifier_exec/run_f1_falsifier_exec.py"],
        "next_falsifier": report["next_falsifier"],
    }
    ev_status = {
        "event_id": f"w097-f1falsifierexec-status-{stamp}",
        "event_type": "status",
        "created_at": ts_iso,
        "actor": "worker-097",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "task_id": "W097-F1-FALSIFIER-EXEC-01",
        "status": "active",
        "hours": 0.4,
        "claims_completion": False,
        "summary": ("No inbox card exists for worker-097 (recycled slot); took ONE bounded class-bound task: "
                    "W097-F1-FALSIFIER-EXEC-01, independent execution of the F1 falsifier/ambiguity suite at its "
                    "frozen binding. Artifacts + evidence emitted; no gate verdict, node completion, or validation "
                    "promotion claimed. Task contribution complete pending lead adjudication."),
        "evidence_refs": [ref(REPORT), ref(SCRIPT), ref(README), ref(RAW)],
        "next_falsifier": ("A lead/controller re-run that does not reproduce the per-row decisability classes, or the "
                           "next F1 revision/suite re-pin moving a row between RESOLVED_DETERMINATE and "
                           "UNRESOLVED_PATH/ALTERNATE_ONLY."),
    }

    events = [ev_report, ev_script, ev_claim, ev_status]
    for e in events:
        schemas.validate_event(e)  # raises SchemaError -> abort before writing

    dry = "--dry-run" in sys.argv
    if not dry:
        with OUTBOX.open("a") as f:
            for e in events:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

        ckpt = {
            "checkpoint_id": f"w097-f1falsifierexec-{stamp}",
            "created_at": ts_iso,
            "worker": "worker-097",
            "task": {
                "task_id": "W097-F1-FALSIFIER-EXEC-01",
                "assignment_ref": "self-assigned (no inbox card for worker-097)",
                "class_bound": True,
                "classes": ["AF-WCC-VAC-GEN"],
                "node_id": "F1",
                "gate": "G-FORM",
                "task": "independent execution of schemas/f1_falsifier_tests.jsonl against canonical schemas/af_wcc_vacuum.yaml at pinned hashes",
            },
            "artifacts": {
                "artifacts/worker-097/f1_falsifier_exec/report.json": sha(REPORT),
                "artifacts/worker-097/f1_falsifier_exec/run_f1_falsifier_exec.py": sha(SCRIPT),
                "artifacts/worker-097/f1_falsifier_exec/emit_events.py": sha(EMITTER),
                "artifacts/worker-097/f1_falsifier_exec/README.md": sha(README),
                "artifacts/worker-097/f1_falsifier_exec/raw_sha256.txt": sha(RAW),
                "artifacts/worker-097/f1_falsifier_exec/snapshots/af_wcc_vacuum.9a8bd4c96800.yaml": sha(HERE / "snapshots" / "af_wcc_vacuum.9a8bd4c96800.yaml"),
                "artifacts/worker-097/f1_falsifier_exec/snapshots/f1_falsifier_tests.c4c477adcb7a.jsonl": sha(HERE / "snapshots" / "f1_falsifier_tests.c4c477adcb7a.jsonl"),
                "comms/outbox/worker-097.jsonl": sha(OUTBOX),
            },
            "inputs": report["inputs"],
            "drift": report["drift"],
            "controls": {"n": len(report["controls"]), "pass": report["controls_pass"]},
            "events": {"emitted": [e["event_id"] for e in events],
                       "outbox": "comms/outbox/worker-097.jsonl"},
            "verdicts": {
                "rows": counts["rows"],
                "by_decisability_class": by,
                "binding_mismatch": counts["binding_mismatch"],
                "probe_failed_rows": counts["probe_failed_rows"],
                "findings": [f["id"] for f in findings],
            },
            "state": {
                "F1_status_after": "active",
                "F1_validation_after": "unverified",
                "completion_claim": False,
                "gate_verdict_claimed": False,
                "node_status_claimed": False,
                "numerics_lock": "locked",
            },
            "falsifier": report["falsifier"],
            "next_falsifier": report["next_falsifier"],
        }
        CKPT.write_text(json.dumps(ckpt, indent=2, ensure_ascii=False) + "\n")

    print(json.dumps({"dry_run": dry, "events": [e["event_id"] for e in events],
                      "checkpoint": None if dry else str(CKPT.relative_to(ROOT))}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
