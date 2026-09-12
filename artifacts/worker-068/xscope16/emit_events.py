#!/usr/bin/env python3
"""W068-CLASSBIND-XSCOPE-16 event emitter (worker-068, bounded class-bound task).

Writes (in this order):
  1. checkpoint_final.json  - worker-local final checkpoint with the full artifact hash set,
     the emitted event-id list and the pin state re-measured at emission;
  2. runtime/state/w068_xscope16_checkpoint_<stamp>.json - runtime checkpoint;
  3. runtime/state/w068_checkpoints.jsonl - one appended worker checkpoint line;
  4. the event block, appended to comms/outbox/worker-068.jsonl (idempotent by event_id).

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
TASK_ID = "W068-CLASSBIND-XSCOPE-16"
GATE = "G-CLASSBIND (folded into G-AUDIT as calibration evidence)"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
CLASS_ID = ";".join(CLASS_IDS)

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

    files = {n: HERE / n for n in ["PREREGISTRATION.json", "run_xscope16.py", "raw_census.json",
                                   "controls.json", "report.json", "README.md", "checkpoint.json"]}
    missing = [n for n, p in files.items() if not p.exists()]
    if missing:
        print(json.dumps({"exit": 2, "reason": "MISSING_ARTIFACT", "missing": missing}))
        return 2

    H = {n: sha256_file(p) for n, p in files.items()}
    H["emitter"] = sha256_file(Path(__file__).resolve())

    raw = json.loads(files["raw_census.json"].read_text())
    rep = json.loads(files["report.json"].read_text())
    H["checkpoint_final"] = ""  # filled after writing

    # pin state re-measured at emission (recorded, not enforced: the census binds its own snapshot)
    pin_state, drift = {}, []
    for rel, meta in raw["measured_pins"].items():
        got = sha256_file(ROOT / rel)
        pin_state[rel] = got
        if got != meta["sha256"]:
            drift.append(rel)

    R = rep["result"]
    ev = []
    ev.append({
        "event_id": f"w068-x16-01-task-claim-{stamp}", "event_type": "status", "actor": "worker-068",
        "created_at": created, "task_id": TASK_ID, "node_id": "A1", "status": "active", "hours": 0.6,
        "claims_completion": False, "class_ids": CLASS_IDS, "gate": GATE, "group_id": "formulation",
        "summary": (
            "No assignment card exists in comms/inbox for worker-068 (this fleet instance). Took ONE "
            "bounded class-bound task W068-CLASSBIND-XSCOPE-16, self-selected: cross-artifact axis-level "
            "disjointness/freeze census for the four frozen classes (F0 canonical vs F0 supplement) at "
            "the pinned rev29/rev13/rev5 bytes. Read-only on every canonical path; pre-registered rules "
            "R1-R6 with 6 planted controls."),
        "evidence_refs": [f"artifacts/worker-068/xscope16/PREREGISTRATION.json#sha256:{H['PREREGISTRATION.json'][:12]}"],
        "next_falsifier": rep["falsifier"],
    })
    art_specs = [
        ("02-preregistration", "PREREGISTRATION.json", "preregistration",
         "Pre-registered question, 8 measured pins, rules R1-R6, phrase table, 6 predictions, 6 controls, falsifier and stop rule, written before the first census run."),
        ("03-runner", "run_xscope16.py", "checker",
         "Deterministic read-only census runner: fail-closed pin preflight (exit 2), R1-R6 extractors, planted-control self-test (exit 3), writes raw_census/controls/report."),
        ("04-raw-census", "raw_census.json", "census_record",
         "All extracted rows: 4 class axis maps, canonical disjointness, supplement pairwise basis prose, 6x axis cell verdicts, 5 undeclared separators, R5 registry rows, predictions."),
        ("05-controls", "controls.json", "control_record",
         "Planted-control result K1-K6: 6/6 pass, selftest exit 0."),
        ("06-report", "report.json", "report",
         "Aggregate census report: R1 EQUAL, R2 18/18 DIFFERS, R3 5 undeclared separators, R4 6/6 SUBSET, R5 3 TOKEN_DIFFERS, P1-P6 6/6 matched, 8 findings, measured pins and artifact hashes."),
        ("07-readme", "README.md", "readme",
         "One-page human summary: question, pins, method, result table, findings R5/R3, limitations, non-claims, falsifier, reproduction commands."),
        ("08-worker-checkpoint", "checkpoint.json", "worker_checkpoint",
         "Worker-local resumable checkpoint: pins, measurement, findings, artifact hashes, falsifier, stop rule."),
    ]
    for tag, name, atype, summary in art_specs:
        ev.append({
            "event_id": f"w068-x16-{tag}-{stamp}", "event_type": "artifact", "actor": "worker-068",
            "created_at": created, "task_id": TASK_ID, "node_id": "A1", "artifact_type": atype,
            "path": f"artifacts/worker-068/xscope16/{name}", "sha256": H[name],
            "validation_status": "unverified", "claims_completion": False, "class_ids": CLASS_IDS,
            "gate": GATE, "group_id": "formulation", "summary": summary,
            "evidence_refs": [f"artifacts/worker-068/xscope16/{name}#sha256:{H[name][:12]}",
                              f"research_map/formulation_taxonomy.yaml#0abb9ed8a961"],
            "next_falsifier": rep["falsifier"],
        })

    ev.append({
        "event_id": f"w068-x16-09-claim-{stamp}", "event_type": "claim", "actor": "worker-068",
        "created_at": created, "task_id": TASK_ID, "node_id": "A1", "class_id": CLASS_ID,
        "class_ids": CLASS_IDS, "gate": GATE, "group_id": "formulation", "claims_completion": False,
        "conclusion_type": "formal_model", "review_status": "unverified",
        "statement": (
            "Declaration-level artifact measurement (not a mathematics claim, not a gate verdict) at the "
            "measured pins (F0 canonical 0abb9ed8a961, F0 supplement d7419b4e8963, FROZEN rev29 815e08079aef, "
            "F1 d9cebb9404b2, F2a e9a27996dfd3, F2b b2ab6acb2bbe): the canonical disjointness table is "
            "axis-level sound at rev5 - the canonical and supplement pair sets are EQUAL (6/6 unordered "
            "pairs), all 18 declared decisive-axis cells DIFFER between the paired class descriptors "
            "(0 EQUAL, 0 MISSING_AXIS), and the supplement basis prose is a SUBSET of the canonical "
            "decisive-axis set on 6/6 pairs (no over-claim). Two measured observations: (W068-X16-R5) the "
            "supplement axis_registry.genericity_axis freezes 'residual_comeager' for the three vacuum "
            "classes while canonical axes.genericity_kind reads 'provisional_baire_residual' with status "
            "provisional_owned_by_F1/F2 (3 TOKEN_DIFFERS; SPH matches unresolved/unresolved); (W068-X16-R3) "
            "5 undeclared separators: genericity_kind on the three SPH pairs and regularity_token on the "
            "two SCC-SPH pairs. Findings are recorded, not adjudicated; 6/6 predictions matched; planted "
            "controls 6/6 pass."),
        "assumptions": [
            "The census binds the eight pinned inputs; any byte move voids it (runner preflight exit 2).",
            "Canonical disjointness separates class DESCRIPTORS, not data spaces (disjointness_scope); no data-space overlap claim is made.",
            "The supplement basis mapping is token-based via the pre-registered phrase table; unmapped phrases are ignored.",
        ],
        "falsifier": rep["falsifier"],
        "evidence_refs": [
            f"artifacts/worker-068/xscope16/report.json#sha256:{H['report.json'][:12]}",
            f"artifacts/worker-068/xscope16/raw_census.json#sha256:{H['raw_census.json'][:12]}",
            "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
            "artifacts/formulation/formulation_taxonomy.yaml#d7419b4e8963",
        ],
        "artifact_refs": [
            "artifacts/worker-068/xscope16/report.json",
            "artifacts/worker-068/xscope16/raw_census.json",
            "artifacts/worker-068/xscope16/controls.json",
        ],
    })

    ev.append({
        "event_id": f"w068-x16-10-blocker-{stamp}", "event_type": "blocker", "actor": "worker-068",
        "created_at": created, "task_id": TASK_ID, "node_id": "A1", "class_ids": CLASS_IDS,
        "gate": GATE, "group_id": "formulation", "claims_completion": False,
        "description": (
            "(1) The W068-X16-R5 genericity token divergence (supplement frozen 'residual_comeager' vs "
            "canonical 'provisional_baire_residual', 3 classes) is a cross-artifact wording/status "
            "disagreement that this worker cannot repair: any edit to research_map/formulation_taxonomy.yaml "
            "voids G-F0 and any edit to the supplement is the owner's. It is adjacent to controller finding "
            "CF-21 and needs owner/controller disposition (reconcile the token, or declare the mapping). "
            "(2) The extractor is single-executor: the census has planted controls but no second-executor "
            "replication of the R1-R6 verdicts on the same pinned bytes."),
        "needed_to_unblock": (
            "lead-formulation/controller: one accepted-stream disposition of the genericity axis token "
            "(either the supplement's frozen token is annotated as the F1/F2-owned provisional value, or the "
            "canonical axis value is refreshed - which moves the G-F0 pin and requires fresh accepts), and one "
            "non-author re-run of run_xscope16.py at the same eight pins reproducing the 6x axis table."),
        "evidence_refs": [
            f"artifacts/worker-068/xscope16/report.json#sha256:{H['report.json'][:12]}",
            "research_map/formulation_taxonomy.yaml#0abb9ed8a961:classes",
            "artifacts/formulation/formulation_taxonomy.yaml#d7419b4e8963:axis_registry.genericity_axis",
        ],
        "next_falsifier": rep["falsifier"],
    })

    ev.append({
        "event_id": f"w068-x16-11-checkpoint-{stamp}", "event_type": "status", "actor": "worker-068",
        "created_at": created, "task_id": TASK_ID, "node_id": "A1", "status": "active", "hours": 0.6,
        "claims_completion": False, "class_ids": CLASS_IDS, "gate": GATE, "group_id": "formulation",
        "summary": (
            f"CHECKPOINT (worker-068, XSCOPE-16): valid=true at the pinned bytes; R1 EQUAL; R2 18/18 DIFFERS; "
            f"R3 5 undeclared separators; R4 6/6 SUBSET; R5 3 TOKEN_DIFFERS; predictions 6/6; controls 6/6. "
            f"pin_state_at_emit drift={drift!r}. Artifact hash set and event list recorded in checkpoint_final.json."),
        "evidence_refs": [
            f"artifacts/worker-068/xscope16/checkpoint.json#sha256:{H['checkpoint.json'][:12]}",
            f"artifacts/worker-068/xscope16/report.json#sha256:{H['report.json'][:12]}",
        ],
        "next_falsifier": rep["falsifier"],
    })

    ev.append({
        "event_id": f"w068-x16-12-complete-{stamp}", "event_type": "status", "actor": "worker-068",
        "created_at": created, "task_id": TASK_ID, "node_id": "A1", "status": "active", "hours": 0.6,
        "claims_completion": False, "class_ids": CLASS_IDS, "gate": GATE, "group_id": "formulation",
        "summary": (
            "Bounded worker lifecycle complete (W068-CLASSBIND-XSCOPE-16). Artifacts and events emitted; "
            "worker exits for recycling. No node completion, validation_status=passed, or gate verdict is claimed."),
        "evidence_refs": [f"artifacts/worker-068/xscope16/README.md#sha256:{H['README.md'][:12]}"],
        "next_falsifier": rep["falsifier"],
    })

    for e in ev:
        try:
            validate_event(e)
        except Exception as ex:  # fail closed before any write
            print(json.dumps({"exit": 2, "reason": "INVALID_EVENT", "event_id": e.get("event_id"),
                              "error": str(ex)}, indent=1))
            return 2

    # idempotent append to the outbox
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                try:
                    existing.add(json.loads(line)["event_id"])
                except Exception:
                    pass
    appended = []
    with OUTBOX.open("a") as f:
        for e in ev:
            if e["event_id"] in existing:
                continue
            f.write(json.dumps(e) + "\n")
            appended.append(e["event_id"])

    event_ids = [e["event_id"] for e in ev]
    final = {
        "schema": "w068-xscope16-checkpoint-final/v1",
        "task_id": TASK_ID, "worker": "worker-068", "node_id": "A1", "gate": GATE,
        "class_ids": CLASS_IDS, "created_at": created,
        "pin_state_at_emit": pin_state, "pin_drift_at_emit": drift,
        "measurement": R,
        "artifact_hashes": {k: v for k, v in H.items() if k != "checkpoint_final"},
        "events": event_ids, "events_appended": appended,
        "falsifier": rep["falsifier"], "non_claims": rep["non_claims"],
        "status": {"delivered": True, "no_completion_claim": "worker cannot set done/passed/gate verdict",
                   "validation_status": "unverified"},
    }
    (HERE / "checkpoint_final.json").write_text(json.dumps(final, indent=1) + "\n")
    final["artifact_hashes"]["checkpoint_final"] = sha256_file(HERE / "checkpoint_final.json")

    RUNTIME.mkdir(parents=True, exist_ok=True)
    rt = RUNTIME / f"w068_xscope16_checkpoint_{stamp}.json"
    rt.write_text(json.dumps(final, indent=1) + "\n")
    with (RUNTIME / "w068_checkpoints.jsonl").open("a") as f:
        f.write(json.dumps({
            "task_id": TASK_ID, "worker": "worker-068", "at": created,
            "frozen_revision_binding": {
                "F0_canonical": raw["measured_pins"]["research_map/formulation_taxonomy.yaml"]["sha256"],
                "F0_supplement": raw["measured_pins"]["artifacts/formulation/formulation_taxonomy.yaml"]["sha256"],
                "FROZEN": raw["measured_pins"]["artifacts/formulation/FROZEN.json"]["sha256"],
            },
            "class_ids": CLASS_IDS, "measurement": R, "falsifier": rep["falsifier"],
            "events": event_ids,
            "artifacts": {f"artifacts/worker-068/xscope16/{n}": {"sha256": H[n]} for n in H if n != "checkpoint_final"},
            "status": {"delivered": True, "no_completion_claim": "worker cannot set done/passed/gate verdict",
                       "validation_status": "unverified"},
        }) + "\n")

    print(json.dumps({"exit": 0, "events": len(event_ids), "appended": len(appended),
                      "runtime_checkpoint": str(rt.relative_to(ROOT)), "pin_drift_at_emit": drift},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
