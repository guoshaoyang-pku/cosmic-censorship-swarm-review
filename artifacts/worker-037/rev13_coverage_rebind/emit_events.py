#!/usr/bin/env python3
"""Emit W037-REV13-COVERAGE-REBIND-01 deliverables: SHA256SUMS, checkpoint, outbox events.

Self-rejects (per PROTOCOL rule 5): every event is validated with research_map/schemas.py
before it is appended, and duplicate event_ids already present in the outbox are skipped.
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
from schemas import validate_event, SchemaError  # noqa: E402

TASK = "W037-REV13-COVERAGE-REBIND-01"
ACTOR = "worker-037"
NODE = "L1"
GATE = "G-LIT"
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
CLASS_ID = ";".join(CLASSES)
OUTBOX = ROOT / "comms" / "outbox" / f"{ACTOR}.jsonl"
STATE = ROOT / "runtime" / "state"
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).replace(microsecond=0)
STAMP = NOW.strftime("%Y%m%dT%H%M%S")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def main() -> int:
    report_p = HERE / "report.json"
    report_md = HERE / "REPORT.md"
    controls_p = HERE / "controls.json"
    report = json.loads(report_p.read_text())
    p3 = report["part3_coverage_rebuild"]
    p1 = report["part1_pin_census"]

    # ---- SHA256SUMS over every file in this artifact directory except itself ----
    files = sorted(p for p in HERE.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    sums_p = HERE / "SHA256SUMS"
    sums_p.write_text("".join(f"{sha256(p)}  {rel(p)}\n" for p in files), encoding="utf-8")

    hashes = {rel(p): sha256(p) for p in files}

    # ---- checkpoint ----
    checkpoint = {
        "schema": "worker-037/checkpoint/v1",
        "checkpoint_id": f"w037-rev13-coverage-rebind-{STAMP}",
        "task_id": TASK,
        "actor": ACTOR,
        "created_at": NOW.isoformat(),
        "node_id": NODE,
        "gate": GATE,
        "class_ids": CLASSES,
        "authority": "worker-level measurement evidence only; no gate verdict, node status, "
                     "validation_status promotion, or canonical-path write",
        "declared_live_pins": report["declared_live_pins"],
        "inputs_stable_during_run": report["inputs_stable"],
        "key_measurements": {
            "declared_pins_scanned": p1["n_declared_pins"],
            "declared_pins_by_status": p1["by_status"],
            "superseded_gate_input_pins": len(p1["gate_input_pins_superseded"]),
            "conformance_readings_stable_rev12_to_rev13": {
                k: v["reading_counts_same"] for k, v in report["part2_conformance_reread"]["field_diff"].items()},
            "matrix_rebuild_matches_live": p3["matrix_rebuild_matches_live"],
            "matrix_sha_live": p3["live_matrix"]["sha256"],
            "matrix_sha_rebuilt": p3["run"]["out_csv_sha256"],
            "declared_covered_counts": {k: v["covered"] for k, v in p3["declared_counts"].items()},
            "rebuilt_covered_counts": {k: v["covered"] for k, v in p3["rebuilt_counts"].items()},
            "control_c1_covered_total": report["part4_controls"]["C1_augmented_status_key"]["covered_total"],
            "control_c4_covered_total": report["part4_controls"]["C4_mutation_drops_covered"]["covered_total"],
        },
        "artifact_hashes": hashes,
        "falsifier": ("a superseded pin that actually resolves; a live-ledger rebuild equal to "
                      "abbaee54a5a3 or non-zero covered under the unmodified builder; a live ledger "
                      "row carrying a status key; C1/C4 failing to move counts; input drift during "
                      "the run window"),
        "next_falsifier": ("re-run rebind_census.py after the owner rebuilds the coverage matrix at "
                           "the live ledger: the finding is discharged if matrix_rebuild_matches_live "
                           "is true and the published covered counts equal the rebuilt ones, or if "
                           "the A0/BL-9 vocabulary ruling is recorded and the builder is re-keyed"),
    }
    STATE.mkdir(parents=True, exist_ok=True)
    ckpt_p = STATE / "w037_rev13_coverage_rebind_checkpoint.json"
    ckpt_p.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ckpt_sha = sha256(ckpt_p)

    # ---- events ----
    does_not_claim = [
        "gate verdict", "node status", "validation_status promotion",
        "authority to edit canonical artifacts", "A0/BL-9 vocabulary ruling",
        "that the 21 covered cells are mathematically unsupported",
        "class re-adjudication", "review verdict on any artifact",
    ]
    evidence_refs = [
        f"{rel(report_p)}#{hashes[rel(report_p)][:12]}",
        f"{rel(report_md)}#{hashes[rel(report_md)][:12]}",
        f"{rel(controls_p)}#{hashes[rel(controls_p)][:12]}",
        "ledger/theorems.jsonl#a1674f094979",
        "ledger/class_coverage.csv#abbaee54a5a3",
        "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
        "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
        "artifacts/formulation/FROZEN.json#815e08079aef",
    ]
    events = []

    for label, path in (("report.json", report_p), ("REPORT.md", report_md), ("controls.json", controls_p)):
        events.append({
            "event_id": f"w037-rev13cov-{STAMP}-artifact-{label.replace('.', '_')}",
            "event_type": "artifact", "actor": ACTOR, "created_at": NOW.isoformat(),
            "task_id": TASK, "node_id": NODE, "gate": GATE, "class_id": CLASS_ID,
            "class_ids": CLASSES, "artifact_type": "report" if label.endswith(".json") else "report_md",
            "path": rel(path), "sha256": hashes[rel(path)], "validation_status": "unverified",
            "evidence_refs": evidence_refs,
            "summary": f"{TASK} artifact: {label}",
        })
    events.append({
        "event_id": f"w037-rev13cov-{STAMP}-artifact-SHA256SUMS",
        "event_type": "artifact", "actor": ACTOR, "created_at": NOW.isoformat(),
        "task_id": TASK, "node_id": NODE, "gate": GATE, "class_id": CLASS_ID,
        "class_ids": CLASSES, "artifact_type": "checksums", "path": rel(sums_p),
        "sha256": sha256(sums_p), "validation_status": "unverified",
        "evidence_refs": evidence_refs, "summary": f"{TASK} artifact: SHA256SUMS",
    })

    events.append({
        "event_id": f"w037-rev13cov-{STAMP}-claim",
        "event_type": "claim", "actor": ACTOR, "created_at": NOW.isoformat(),
        "task_id": TASK, "node_id": NODE, "gate": GATE, "class_id": CLASS_ID, "class_ids": CLASSES,
        "conclusion_type": "formal_model",
        "statement": (
            "Artifact-and-ledger measurement, not a mathematics claim. At pins F1 d9cebb9404b2 / "
            "F2a e9a27996dfd3 / F2b b2ab6acb2bbe / FROZEN rev29 815e08079aef / ledger a1674f094979: "
            "(1) 15 declared pins in artifacts/flash-10/l1_class_coverage are superseded gate-input "
            "pins, but the WCC and C2 conformance readings are unchanged from their rev12 baselines "
            "(11 and 10 bound, 0 discharging), so the repair is a re-pin, not re-adjudication; "
            "(2) the published ledger/class_coverage.csv and coverage_summary.json do not reproduce "
            "at the live ledger: the unmodified builder yields covered 0/0/0/0 versus the published "
            "7/3/3/8, because the live ledger carries no `status` key on any of its 62 rows while "
            "the builder predicate requires status=='accepted'; (3) a positive control that adds "
            "only that key to a copy of the live ledger reproduces the published 21 covered cells "
            "exactly, isolating the cause to the ledger vocabulary rename, and a mutation control "
            "returns 0. The 21 published covered cells therefore cite an evidence token "
            "(`ledger_theorem_covered`) the live ledger cannot license; whether the nearest live "
            "token carries acceptance force is an A0/BL-9 ruling this worker does not make."),
        "assumptions": [
            "The declared pins and the live bytes are the object of measurement; no canonical path "
            "was written and no third-party artifact was modified.",
            "The coverage builder's frozen predicate is the instrument of record for the published "
            "matrix; the census re-runs it unmodified with output redirected.",
            "artifacts/flash-10/l1_class_coverage is the L1 class-coverage/conformance evidence "
            "family for the three frozen classes the L1 node declares; AF-WCC-SCALAR-SPH rows are "
            "reported as an observation only.",
            "A ledger row's coverage status is what the frozen builder predicate computes from the "
            "row's vocabulary fields, not what any prose summary asserts.",
        ],
        "falsifier": (
            "Falsified by: (a) any pin classified SUPERSEDED that actually resolves to its declared "
            "hash; (b) a live-ledger rebuild under the unmodified builder that equals abbaee54a5a3 "
            "or yields a non-zero covered count; (c) one or more live ledger rows carrying a `status` "
            "key; (d) controls C1/C4 failing to move covered counts to 21/0 respectively; (e) any "
            "declared input changing during the run window (inputs_stable=false)."),
        "artifact_refs": [
            f"{rel(report_p)}#{hashes[rel(report_p)][:12]}",
            f"{rel(controls_p)}#{hashes[rel(controls_p)][:12]}",
            f"{rel(sums_p)}#{sha256(sums_p)[:12]}",
        ],
        "evidence_refs": evidence_refs + [f"runtime/state/{ckpt_p.name}#{ckpt_sha[:12]}"],
        "does_not_claim": does_not_claim,
    })

    events.append({
        "event_id": f"w037-rev13cov-{STAMP}-blocker",
        "event_type": "blocker", "actor": ACTOR, "created_at": NOW.isoformat(),
        "task_id": TASK, "node_id": NODE, "gate": GATE, "class_id": CLASS_ID, "class_ids": CLASSES,
        "blocker_id": "W037-BL-COVERAGE-REBIND",
        "description": (
            "The L1 class-coverage evidence cannot be cited at the live bytes without owner action: "
            "15 declared pins in artifacts/flash-10/l1_class_coverage point at superseded schema/"
            "ledger hashes (content readings unchanged), and the published ledger/class_coverage.csv "
            "+ coverage_summary.json (covered 7/3/3/8) do not reproduce at ledger a1674f094979 "
            "(unmodified rebuild: 0/0/0/0; 21 rows change) because the live ledger has no `status` "
            "key. Workers cannot write canonical paths or rule the vocabulary question."),
        "needed_to_unblock": (
            "lead-literature (canonical-path owner): (1) re-pin the WCC/C2 conformance outputs to "
            "d9cebb9404b2 / e9a27996dfd3 + ledger a1674f094979 and re-emit artifact events; "
            "(2) rebuild and re-publish ledger/class_coverage.csv + coverage_summary.json at the "
            "live ledger, or withdraw the current counts from citation until then; "
            "(3) A0/BL-9: rule whether content_status=verified + author_asserts_supports carries "
            "acceptance force given review_status=not_independently_reviewed on all 62 rows; "
            "(4) after either branch, re-run this census (matrix_rebuild_matches_live must read true)."),
        "evidence_refs": evidence_refs + [f"runtime/state/{ckpt_p.name}#{ckpt_sha[:12]}"],
    })

    events.append({
        "event_id": f"w037-rev13cov-{STAMP}-status",
        "event_type": "status", "actor": ACTOR, "created_at": NOW.isoformat(),
        "task_id": TASK, "node_id": NODE, "gate": GATE, "class_id": CLASS_ID, "class_ids": CLASSES,
        "status": "active", "hours": 0.9,
        "summary": (
            f"{TASK} complete at worker level (task status only; worker events cannot set node/gate "
            f"state). One bounded class-bound task self-selected from the post-rev13 L1/G-LIT path; "
            f"no inbox card existed for worker-037. Measured: {p1['n_declared_pins']} declared pins "
            f"({p1['by_status']['ALIGNED']} aligned / {p1['by_status']['SUPERSEDED']} superseded); "
            f"conformance readings content-stable rev12->rev13; published coverage counts "
            f"7/3/3/8 do not rebuild at the live ledger (0/0/0/0); cause isolated to the missing "
            f"`status` key by controls C1 (reproduces 21) and C4 (returns 0). Canonical bytes "
            f"unchanged; inputs stable during the run; checkpoint written."),
        "evidence_refs": evidence_refs + [f"runtime/state/{ckpt_p.name}#{ckpt_sha[:12]}"],
        "next_falsifier": checkpoint["next_falsifier"],
        "does_not_claim": does_not_claim,
    })

    # ---- self-reject, dedup, append ----
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                continue
    appended = 0
    for ev in events:
        try:
            validate_event(ev)
        except SchemaError as e:
            print(f"SELF-REJECT {ev['event_id']}: {e}", file=sys.stderr)
            return 2
        if ev["event_id"] in existing:
            print(f"skip duplicate {ev['event_id']}")
            continue
        with OUTBOX.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        appended += 1
    print(f"appended {appended}/{len(events)} events to {rel(OUTBOX)}")
    print(f"checkpoint {rel(ckpt_p)} sha256 {ckpt_sha}")
    print(f"SHA256SUMS {rel(sums_p)} sha256 {sha256(sums_p)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
