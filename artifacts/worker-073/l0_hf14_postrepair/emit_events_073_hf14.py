#!/usr/bin/env python3
"""Emit the W073-L0-HF14-POSTREPAIR-01 outbox events + worker checkpoint (idempotent).

Run after run_check_073.py. Appends four accepted-schema events to
comms/outbox/worker-073.jsonl (status-active, artifact, review, status-done) and writes
runtime/state/w073_hf14_postrepair_checkpoint_1.json. Re-running skips event_ids already present.
Never edits canonical artifacts.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUT = ROOT / "artifacts" / "worker-073" / "l0_hf14_postrepair"
REPORT = OUT / "report.json"
RUNNER = OUT / "run_check_073.py"
README = OUT / "README.md"
STDOUT = OUT / "run_stdout.txt"
PROBE = OUT / "raw" / "live_probe.json"
OUTBOX = ROOT / "comms" / "outbox" / "worker-073.jsonl"
CKPT = ROOT / "runtime" / "state" / "w073_hf14_postrepair_checkpoint_1.json"

CST = timezone(timedelta(hours=8))
CLASS_SCOPE = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
REV3_SHA = "3e3d35531421388a17ca7bad7f6c7093dd1cc21a3a808ca8ff65ce6c2b79c6a6"
ARCHIVE = "artifacts/literature/archive/theorems.rev3-handpatch-20260912T003026.jsonl"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    now = datetime.now(CST).isoformat(timespec="seconds")
    token = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in (REPORT, RUNNER, README, STDOUT, PROBE)}
    rep = json.loads(REPORT.read_text())
    status = rep["status"]
    assert status == "CONFIRMED_CLOSED", f"refusing to emit completion for status={status}"
    ev = {k: {"path": k, "sha256": v} for k, v in hashes.items()}

    def ref(p: Path) -> str:
        return f"{p.relative_to(ROOT)}#sha256:{sha(p)[:16]}"

    report_ref, runner_ref, stdout_ref, readme_ref = ref(REPORT), ref(RUNNER), ref(STDOUT), ref(README)
    evidence = [report_ref, runner_ref, stdout_ref, readme_ref]

    events = [
        {
            "event_id": f"w073-hf14-status-active-{token}",
            "event_type": "status",
            "created_at": now,
            "actor": "worker-073",
            "node_id": "L0",
            "gate": "G-LIT",
            "task_id": "W073-L0-HF14-POSTREPAIR-01",
            "status": "active",
            "hours": 0.4,
            "class_scope": CLASS_SCOPE,
            "summary": (
                "No inbox card exists for worker-073 (recycled slot). Took ONE bounded class-bound task: "
                "independent post-repair check of the L0 rev-3 HF-14 closure, certified at archive sha 3e3d35531421 "
                "(hash-identical to the repair record's after_sha256), with pre-repair ce42d205 as positive control. "
                "Own detector implementation from evaluation_rubric.yaml:243-252; no import of audit_lib or the lead's "
                "repair tool. Result: pre-repair R1=R2=R3=60/62; rev-3 R1=R2=R3=0; 8/8 controls pass; 0 claim-bearing "
                "delta fields; L1 source refs and class_ids intact. Moving target observed: live ledger moved "
                "3e3d3553 -> a1674f09 at 00:35:19 during this task, so the verdict is bound to the archive and the "
                "live file is recorded as an observation only."
            ),
            "evidence_refs": evidence,
            "next_falsifier": (
                "A re-run of run_check_073.py at the pinned archive hashes that fails any control, yields a nonzero "
                "rev-3 R1/R2/R3 count, finds a claim-bearing delta field, or breaks an L0->L1 source reference "
                "falsifies the HF-14 closure finding; a different archive hash voids the binding."
            ),
        },
        {
            "event_id": f"w073-hf14-artifact-{token}",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-073",
            "node_id": "L0",
            "gate": "G-LIT",
            "task_id": "W073-L0-HF14-POSTREPAIR-01",
            "artifact_type": "l0_hf14_postrepair_check",
            "path": str(REPORT.relative_to(ROOT)),
            "sha256": hashes[str(REPORT.relative_to(ROOT))],
            "validation_status": "unverified",
            "class_scope": CLASS_SCOPE,
            "summary": (
                "HF-14 exposure census (own rubric-text implementation, three readings) and rev-3 delta census at "
                "certified L0 3e3d3553 with pre-repair control ce42d205. status=CONFIRMED_CLOSED: markers 60 -> 0, "
                "R1/R2/R3 60 -> 0, controls 8/8, delta limited to acceptance-vocabulary fields, 0 claim-bearing "
                "changes, L1 refs 100% resolved. Residual: counterfactual 61 rows if renamed statuses are ruled "
                "acceptance vocabulary; 28 unbound + 8 disjunctive class rows are pre-existing BL-6."
            ),
            "reproduce": (
                "python3 artifacts/worker-073/l0_hf14_postrepair/run_check_073.py "
                "(fail-closed on certified pins; exit 0 only on CONFIRMED_CLOSED)"
            ),
            "evidence_refs": evidence,
            "falsifier": (
                "A re-run that fails any of the 8 controls, any nonzero rev-3 HF-14 reading, any claim-bearing "
                "delta field, or any unresolvable L0->L1 source id."
            ),
        },
        {
            "event_id": f"w073-hf14-review-{token}",
            "event_type": "review",
            "created_at": now,
            "actor": "worker-073",
            "node_id": "L0",
            "gate": "G-LIT",
            "reviewer": "worker-073",
            "target_id": "L0-rev3-hf14-repair",
            "reviewed_path": ARCHIVE,
            "reviewed_sha256": REV3_SHA,
            "verdict": "accept",
            "score": 4.0,
            "hard_failures": [],
            "findings": [
                {
                    "id": "HF14-073-01",
                    "severity": "info",
                    "finding": (
                        "HF-14 predicates independently return 0/62 at rev-3 3e3d3553 under all three readings "
                        "(R1 literal-weak, R2 strict, R3 any-absence); pre-repair control reproduces 60/62."
                    ),
                },
                {
                    "id": "HF14-073-02",
                    "severity": "info",
                    "finding": (
                        "Rev-3 delta is confined to acceptance vocabulary: 62 rows changed, 0 claim-bearing fields, "
                        "0 unexpected fields; statement_exact/class_ids/source_ids preserved on every row."
                    ),
                },
                {
                    "id": "HF14-073-03",
                    "severity": "revise",
                    "finding": (
                        "Moving target: ledger/theorems.jsonl moved 3e3d3553 -> a1674f09 at 00:35:19+08:00 during "
                        "this task; any verdict at 3e3d3553 is void for the live revision, and the live revision "
                        "a1674f09 (status field removed on all 62 rows) was only observed, not certified."
                    ),
                },
                {
                    "id": "HF14-073-04",
                    "severity": "info",
                    "finding": (
                        "Counterfactual exposure 61/62 if a lead rules included_unreviewed/provisional to be "
                        "acceptance vocabulary; not the detector's literal text."
                    ),
                },
            ],
            "class_scope": CLASS_SCOPE,
            "artifact_refs": [report_ref, runner_ref],
            "evidence_refs": evidence,
            "scope_note": (
                "Targeted verdict on the HF-14 closure claim and delta preservation at certified rev-3 3e3d3553 "
                "only. Not a full L0 review, not a class-binding adjudication (BL-6), not a gate verdict, and it "
                "must not be counted as a G-LIT accept."
            ),
            "counts_toward_gate_accept": False,
            "falsifier": (
                "A re-run with a control failure or any nonzero rev-3 HF-14 reading, or a claim-bearing delta field."
            ),
        },
        {
            "event_id": f"w073-hf14-status-done-{token}",
            "event_type": "status",
            "created_at": now,
            "actor": "worker-073",
            "node_id": "L0",
            "gate": "G-LIT",
            "task_id": "W073-L0-HF14-POSTREPAIR-01",
            "status": "done",
            "hours": 0.5,
            "class_scope": CLASS_SCOPE,
            "summary": (
                "Worker lifecycle complete (completion claim for the deliverable only, not a node done and not a "
                "gate verdict). One class-bound task delivered: independent HF-14 closure check at certified L0 rev-3 "
                "3e3d3553. Artifacts: report.json sha256 " + hashes[str(REPORT.relative_to(ROOT))][:16] +
                ", run_check_073.py sha256 " + hashes[str(RUNNER.relative_to(ROOT))][:16] +
                ", README.md, run_stdout.txt, raw/live_probe.json. Checkpoint: "
                "runtime/state/w073_hf14_postrepair_checkpoint_1.json. Canonical ledger and all other workers' "
                "artifacts untouched; numerics lock respected (no numerics path touched). Worker exits now."
            ),
            "evidence_refs": evidence + ["runtime/state/w073_hf14_postrepair_checkpoint_1.json"],
            "next_falsifier": (
                "Re-run artifacts/worker-073/l0_hf14_postrepair/run_check_073.py at the pinned archive hashes: any "
                "control failure or nonzero rev-3 HF-14 reading falsifies the closure; a moved archive hash voids it."
            ),
            "completion_scope": "worker lifecycle only; not a node done / gate verdict",
        },
    ]

    for e in events:
        for k in ("event_id", "event_type", "created_at", "actor"):
            assert e.get(k), f"event missing {k}: {e}"
        json.dumps(e)  # must serialise

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                try:
                    existing.add(json.loads(line).get("event_id"))
                except json.JSONDecodeError:
                    pass
    appended = 0
    with open(OUTBOX, "a") as f:
        for e in events:
            if e["event_id"] in existing:
                continue
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
            appended += 1

    # verify the appended lines re-parse
    tail = [json.loads(l) for l in OUTBOX.read_text().splitlines()[-appended:]] if appended else []
    assert len(tail) == appended

    checkpoint = {
        "worker": "worker-073",
        "checkpoint": 1,
        "at": now,
        "run": "run-2026-09-11T23:15+08:00",
        "task": "W073-L0-HF14-POSTREPAIR-01 — independent post-repair check of the L0 rev-3 HF-14 closure",
        "status": "complete",
        "verdict": "accept (targeted: HF-14 closure at 3e3d3553)",
        "certified_revision": {"path": ARCHIVE, "sha256": REV3_SHA},
        "baseline_revision": {"sha256": "ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72"},
        "artifacts": hashes,
        "summary": {
            "pre_repair_exposure_R1": 60,
            "rev3_exposure_R1": 0,
            "rev3_exposure_R2": 0,
            "rev3_exposure_R3": 0,
            "controls_passed": "8/8",
            "claim_bearing_delta_fields": 0,
            "unexpected_delta_fields": 0,
            "l1_refs_resolved": "56/56",
            "class_ids_preserved": True,
        },
        "moving_target_observation": {
            "live_ledger_first_run_sha256": REV3_SHA,
            "live_ledger_second_run_sha256": rep["live_ledger_probe"]["end"]["sha256"],
            "live_mtime": rep["live_ledger_probe"]["end"]["mtime_iso"],
            "policy": "verdict bound to the archived rev-3 bytes; live revision observed only",
        },
        "events_emitted": [e["event_id"] for e in events],
        "outbox": str(OUTBOX.relative_to(ROOT)),
        "hours_spent_estimate": 0.5,
        "next_falsifier": events[-1]["next_falsifier"],
        "numerics_lock": "respected: no numerics path touched, no solver created",
        "read_only": "canonical ledger, schemas, rubric and other workers' artifacts unmodified",
        "non_claims": (
            "Does not promote any theorem, sets no node status and no gate verdict; validation_status stays "
            "unverified. Only the controller and group leads may move node/gate status."
        ),
    }
    CKPT.write_text(json.dumps(checkpoint, indent=1) + "\n")

    print(f"appended {appended} events to {OUTBOX.relative_to(ROOT)}")
    print(f"checkpoint {CKPT.relative_to(ROOT)}")
    print(f"report sha256 {hashes[str(REPORT.relative_to(ROOT))]}")
    for k, v in hashes.items():
        print(f"  {k} {v[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
