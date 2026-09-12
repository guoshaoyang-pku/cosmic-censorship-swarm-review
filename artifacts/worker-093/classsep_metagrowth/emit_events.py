#!/usr/bin/env python3
"""W093-CLASSSEP-METAGROWTH-01 event emitter + checkpoint writer.

Appends the task's upward events to comms/outbox/worker-093.jsonl (validated with
research_map.schemas.validate_event before write), writes manifest.json, then writes a
worker checkpoint binding artifact hashes and the outbox sha256.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
OUTBOX = REPO / "comms/outbox/worker-093.jsonl"
STATE = REPO / "runtime/state"
SCHEMAS = REPO / "research_map/schemas.py"
LIVE_MAP = REPO / "research_map/research_map.json"

ARTIFACTS = [
    ("instrument", "verify_metagrowth.py"),
    ("evidence", "report.json"),
    ("protocol", "PREREGISTRATION.md"),
    ("corpus", "preregistered_fixtures.jsonl"),
    ("control", "self_claim_statement.txt"),
    ("readme", "README.md"),
    ("instrument", "emit_events.py"),
    ("snapshot", "snapshot/map.pass05.json"),
    ("snapshot", "pinned/map.pass04.worker-035.json"),
    ("snapshot", "pinned/class_separation.c266dbce.py"),
    ("snapshot", "pinned/lifecycle-pass04.json"),
    ("snapshot", "pinned/lifecycle-pass05.json"),
    ("snapshot", "pinned/worker-035-report.json"),
]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_validator():
    spec = importlib.util.spec_from_file_location("w093_schemas", SCHEMAS)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["w093_schemas"] = mod  # dataclass needs the module registered
    spec.loader.exec_module(mod)
    return mod.validate_event


def main() -> int:
    validate_event = load_validator()
    now = datetime.now().astimezone()
    iso = now.isoformat(timespec="seconds")
    tag = now.strftime("%Y%m%dT%H%M")

    report = json.loads((HERE / "report.json").read_text())
    self_stmt = (HERE / "self_claim_statement.txt").read_text().strip()
    live_map_sha = sha256_file(LIVE_MAP)

    artifact_hashes = {}
    for kind, rel in ARTIFACTS:
        p = HERE / rel
        if not p.exists():
            print(f"MISSING ARTIFACT {rel}", file=sys.stderr)
            return 2
        artifact_hashes[rel] = {"artifact_type": kind, "sha256": sha256_file(p),
                                "bytes": p.stat().st_size}

    manifest = {
        "schema": "w093/classsep-metagrowth/manifest/v1",
        "task_id": "W093-CLASSSEP-METAGROWTH-01",
        "worker": "worker-093",
        "node_id": "A1",
        "gate_scope": ["G-AUDIT"],
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "created_at": iso,
        "verdict": report["result"]["verdict"],
        "checks_passed": sum(1 for c in report["checks"] if c["pass"]),
        "checks_total": len(report["checks"]),
        "result_headline": {
            "pass04_hard": report["growth"]["pass04_hard"],
            "pass05_hard": report["growth"]["pass05_hard"],
            "delta_hard": report["growth"]["delta_hard"],
            "delta_roots": report["growth"]["delta_roots"],
            "assertions": report["classification"]["label_counts"].get("ASSERTION", 0),
            "delta_meta_share": report["growth"]["meta_share_of_delta"],
            "self_application_predicted_findings": report["self_application"]["predicted_new_hard_findings"],
        },
        "live_map_sha256_at_emit": live_map_sha,
        "artifacts": artifact_hashes,
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    manifest_sha = sha256_file(HERE / "manifest.json")
    artifact_hashes["manifest.json"] = {"artifact_type": "manifest", "sha256": manifest_sha,
                                        "bytes": (HERE / "manifest.json").stat().st_size}

    def art_event(suffix: str, rel: str) -> dict:
        a = artifact_hashes[rel]
        return {"event_id": f"w093-metagrowth-{tag}-artifact-{suffix}",
                "event_type": "artifact", "created_at": iso, "actor": "worker-093",
                "node_id": "A1", "artifact_type": a["artifact_type"],
                "path": f"artifacts/worker-093/classsep_metagrowth/{rel}",
                "sha256": a["sha256"], "validation_status": "unverified",
                "class_ids": manifest["class_ids"], "gate_scope": ["G-AUDIT"],
                "summary": f"W093-CLASSSEP-METAGROWTH-01 {a['artifact_type']}: {rel}"}

    events = [
        {"event_id": f"w093-metagrowth-{tag}-status-start", "event_type": "status",
         "created_at": iso, "actor": "worker-093", "node_id": "A1", "status": "active",
         "hours": 0.5, "class_ids": manifest["class_ids"], "gate_scope": ["G-AUDIT"],
         "summary": ("W093-CLASSSEP-METAGROWTH-01 taken (no inbox card existed for worker-093): "
                     "measure whether the CLASSSEP hard list's growth 10 -> 17 between controller "
                     "pass-04 (map 3d45be59) and pass-05 (map 11311ab3) is first-order class "
                     "leakage, formulation-context mention, or audit-meta prose. Read-only."),
         "evidence_refs": ["artifacts/worker-093/classsep_metagrowth/PREREGISTRATION.md",
                           "runtime/state/controller_verification/lifecycle_20260912-004308.json"],
         "next_falsifier": ("any of the 17 findings independently a first-order assertion that C0 "
                            "and C2 are one class; any pinned input drift; enumeration not "
                            "reproducing the canonical list.")},
    ]
    for suffix, rel in [("harness", "verify_metagrowth.py"), ("report", "report.json"),
                        ("prereg", "PREREGISTRATION.md"), ("fixtures", "preregistered_fixtures.jsonl"),
                        ("selfclaim", "self_claim_statement.txt"), ("readme", "README.md"),
                        ("emitter", "emit_events.py"), ("manifest", "manifest.json")]:
        events.append(art_event(suffix, rel))
    events.append({
        "event_id": f"w093-metagrowth-{tag}-claim",
        "event_type": "claim", "created_at": iso, "actor": "worker-093",
        "node_id": "A1", "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "conclusion_type": "formal_model",
        "statement": self_stmt,
        "assumptions": [
            "detector pinned at research_map/class_separation.py sha256 c266dbceca87fb99",
            "pass-05 map frozen at research_map/research_map.json sha256 11311ab3600514cd (snapshot)",
            "pass-04 map frozen at sha256 3d45be5969ec388e via worker-035's snapshot of the same bytes",
            "labels are the pre-registered rule in PREREGISTRATION.md, not a semantic adjudication",
        ],
        "falsifier": report["falsifier"],
        "evidence_refs": ["artifacts/worker-093/classsep_metagrowth/report.json",
                          "artifacts/worker-093/classsep_metagrowth/PREREGISTRATION.md",
                          "artifacts/worker-093/classsep_metagrowth/manifest.json",
                          "runtime/state/controller_verification/lifecycle_20260912-003718.json",
                          "runtime/state/controller_verification/lifecycle_20260912-004308.json",
                          "artifacts/worker-035/classsep_hardfail_adjudication/report.json"],
        "artifact_refs": ["artifacts/worker-093/classsep_metagrowth/report.json",
                          "artifacts/worker-093/classsep_metagrowth/manifest.json"],
        "gate_scope": ["G-AUDIT"],
    })
    events.append({
        "event_id": f"w093-metagrowth-{tag}-blocker-meta-routing",
        "event_type": "blocker", "created_at": iso, "actor": "worker-093",
        "node_id": "A1", "class_ids": manifest["class_ids"], "gate_scope": ["G-AUDIT"],
        "description": ("CLASSSEP hard-count convergence blocker: at pass-05 all 17 hard entries are "
                        "non-assertions (0 first-order assertions), 7/7 of the growth since pass-04 "
                        "comes from three post-CF-16 verification claims (180, 187, 192) that quote or "
                        "describe the detector output, and quoting a finding string mints a new hard "
                        "entry (self-reproduction control). audit_evidence.py:106-108 routes every "
                        "non-CLASSSEP-SOFT finding to hard and claim prose is scanned with no "
                        "quotation/metalinguistic channel, so the count rises with verification "
                        "traffic and cannot converge to zero."),
        "needed_to_unblock": ("detector-owner decision (CF-4) on routing quoted/audit-meta occurrences "
                              "to a soft channel, or an explicit controller policy that a bare CLASSSEP "
                              "hard count is not a G-AUDIT criterion; this worker proposes no rule edit."),
        "evidence_refs": ["artifacts/worker-093/classsep_metagrowth/report.json",
                          "artifacts/worker-093/classsep_metagrowth/manifest.json",
                          "research_map/audit_evidence.py:106"],
    })
    events.append({
        "event_id": f"w093-metagrowth-{tag}-status-complete", "event_type": "status",
        "created_at": iso, "actor": "worker-093", "node_id": "A1", "status": "active",
        "hours": 0.6, "class_ids": manifest["class_ids"], "gate_scope": ["G-AUDIT"],
        "summary": ("W093-CLASSSEP-METAGROWTH-01 complete at worker level: one bounded class-bound "
                    "task, 11/11 pre-registered checks pass, 14/14 labeled controls, worker-035 "
                    "agreement 10/10, no input drift. Growth 10 -> 17 is 7/7 non-assertion meta "
                    "traffic from claims 180/187/192; 0/17 first-order assertions; this task's own "
                    "claim is predicted to add 3 more hard entries. No canonical file written, no "
                    "gate verdict, no node done, no validation_status=passed."),
        "evidence_refs": ["artifacts/worker-093/classsep_metagrowth/report.json",
                          "artifacts/worker-093/classsep_metagrowth/manifest.json"],
        "next_falsifier": ("re-run at the pinned detector/map bytes; a first-order assertion among "
                           "the findings, a changed delta root set, a control failure, or input drift "
                           "voids the result."),
    })

    accepted, rejected = [], []
    with OUTBOX.open("a") as fh:
        for ev in events:
            try:
                validate_event(ev)
            except Exception as e:  # noqa: BLE001
                rejected.append({"event_id": ev.get("event_id"), "error": str(e)})
                continue
            fh.write(json.dumps(ev, sort_keys=True) + "\n")
            accepted.append(ev["event_id"])
    outbox_sha = sha256_file(OUTBOX)

    ckpt = {
        "checkpoint_id": f"w093-ckpt-{tag}",
        "schema": "w093/checkpoint/v1",
        "task_id": "W093-CLASSSEP-METAGROWTH-01",
        "worker": "worker-093", "node_id": "A1",
        "class_ids": manifest["class_ids"], "gate_scope": ["G-AUDIT"],
        "created_at": iso,
        "verdict": report["result"]["verdict"],
        "checks_passed": manifest["checks_passed"], "checks_total": manifest["checks_total"],
        "live_map_sha256": live_map_sha,
        "map_pass05_pin": "11311ab3600514cd34ca7332714a4aa27b97e4fdc124f29179122e11f844974d",
        "detector_pin": "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920",
        "outbox_path": "comms/outbox/worker-093.jsonl",
        "outbox_sha256_after_append": outbox_sha,
        "artifacts": {k: v["sha256"] for k, v in artifact_hashes.items()},
        "events_accepted": accepted, "events_rejected": rejected,
        "falsifier": report["falsifier"],
        "non_claims": report["non_claims"],
    }
    ckpt_path = STATE / f"w093_checkpoint_{tag}.json"
    ckpt_path.write_text(json.dumps(ckpt, indent=1, sort_keys=True) + "\n")
    ckpt_sha = sha256_file(ckpt_path)
    with (STATE / "w093_checkpoints.jsonl").open("a") as fh:
        fh.write(json.dumps({"checkpoint_id": ckpt["checkpoint_id"], "created_at": iso,
                             "path": str(ckpt_path.relative_to(REPO)), "sha256": ckpt_sha,
                             "verdict": ckpt["verdict"], "outbox_sha256": outbox_sha,
                             "checks": f"{ckpt['checks_passed']}/{ckpt['checks_total']}"},
                            sort_keys=True) + "\n")
    print(f"events accepted: {len(accepted)}/{len(events)}  rejected: {rejected}")
    print(f"outbox sha256: {outbox_sha}")
    print(f"manifest sha256: {manifest_sha}")
    print(f"checkpoint: {ckpt_path.relative_to(REPO)} sha256 {ckpt_sha}")
    return 0 if not rejected and report["result"]["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
