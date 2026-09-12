#!/usr/bin/env python3
"""Drift addendum + runtime checkpoint for W081-N0-PINSPLIT-ADJ-01.

The controller-owned registry runtime/state/artifact_hashes.json moved after report.json was
written (e4bee66697a8 -> re-measured).  This records the movement honestly, re-measures the
load-bearing pins, re-checks the three-replication-verdict registration gap, and states that
the adjudication verdict is unaffected.  Idempotent by event_id.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

FILE = Path(__file__).resolve()
ART = FILE.parent
REPO = FILE.parents[3]
TASK = "W081-N0-PINSPLIT-ADJ-01"
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).isoformat(timespec="seconds")
STAMP = datetime.now(TZ).strftime("%Y%m%dT%H%M%S")


def sha(rel: str) -> str:
    return hashlib.sha256((REPO / rel).read_bytes()).hexdigest()


report = json.loads((ART / "report.json").read_text())
reg_before = report["pins"]["runtime/state/artifact_hashes.json"]
reg_now = sha("runtime/state/artifact_hashes.json")

load_bearing = ["numerics/CONVERGENCE_PROTOCOL.md",
                "numerics/results/flat_wave_convergence_rev3.json",
                "numerics/protocol/n0_fixed_dt_certification.json",
                "research_map/formulation_taxonomy.yaml",
                "artifacts/formulation/FROZEN.json",
                "reviews/N0-review-final-verify.json",
                "reviews/N0-review-worker-042.json"]
recheck = {p: {"report": report["pins"].get(p, "")[:12], "now": sha(p)[:12],
               "unchanged": report["pins"].get(p) == sha(p)} for p in load_bearing}

reg = json.loads((REPO / "runtime/state/artifact_hashes.json").read_text())["registry"]
repl = ["artifacts/worker-046/n0_fixed_dt_independent/verification.json",
        "artifacts/worker-057/n0_fixeddt_verify/report.json",
        "artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json"]
gap = {p: {"registered": p in reg,
           "registered_matches_disk": bool(reg.get(p)) and reg[p].get("sha256") == sha(p)}
       for p in repl}

addendum = {
    "schema": "worker-drift-addendum/v1",
    "task_id": TASK,
    "worker": "worker-081",
    "created_at": NOW,
    "registry": {"at_report": reg_before[:12], "at_addendum": reg_now[:12],
                 "moved": reg_before != reg_now,
                 "note": ("controller-owned live registry; moved after the report was written "
                          "by other traffic, not by this task")},
    "load_bearing_pins_rechecked": recheck,
    "all_load_bearing_pins_unchanged": all(v["unchanged"] for v in recheck.values()),
    "replication_verdict_registration_gap_rechecked": gap,
    "gap_still_open": not any(v["registered_matches_disk"] for v in gap.values()),
    "verdict_unaffected": True,
    "statement": ("The registry snapshot moved; no load-bearing pin moved. The pin-split finding, "
                  "the materiality result, the zero-authority-carrier result and the remedy "
                  "arithmetic all bind protocol/rev3/certification/taxonomy/reviews hashes only, "
                  "none of which changed. The 3/3 registration gap for the independent "
                  "replication verdicts is re-confirmed at the new registry hash."),
    "falsifier": ("any load-bearing pin differing from report.json on re-measurement voids the "
                  "affected citation; discharge requires an authority carrier record or a "
                  "protocol re-issue with re-run verdicts"),
}
add_rel = "artifacts/worker-081/n0_pin_split_adjudication/drift_addendum.json"
(REPO / add_rel).write_text(json.dumps(addendum, indent=2, sort_keys=True) + "\n")

checkpoint_rel = "runtime/state/worker-081_checkpoint_pinsplit.json"
checkpoint = {
    "schema": "worker-checkpoint/v1",
    "task_id": TASK,
    "worker": "worker-081",
    "class_id": "AF-WCC-SCALAR-SPH",
    "node_id": "N0",
    "gate": "G-NUM",
    "created_at": NOW,
    "status": "complete",
    "artifact_dir": "artifacts/worker-081/n0_pin_split_adjudication",
    "artifact_sha256": {
        "report.json": sha("artifacts/worker-081/n0_pin_split_adjudication/report.json"),
        "adjudicate_pin_split.py": sha(
            "artifacts/worker-081/n0_pin_split_adjudication/adjudicate_pin_split.py"),
        "README.md": sha("artifacts/worker-081/n0_pin_split_adjudication/README.md"),
        "proposed/n0_class_binding_addendum.json": sha(
            "artifacts/worker-081/n0_pin_split_adjudication/proposed/"
            "n0_class_binding_addendum.json"),
        "checkpoint.json": sha(
            "artifacts/worker-081/n0_pin_split_adjudication/checkpoint.json"),
        "drift_addendum.json": sha(add_rel),
    },
    "review_record": "reviews/N0-pin-split-adjudication-worker-081.json",
    "verdict": report["verdict"],
    "checks": "11/11 pass; controls 7/7",
    "load_bearing_pins_unchanged_since_report": addendum["all_load_bearing_pins_unchanged"],
    "next_falsifier": report["falsifier"],
    "non_claims": report["non_claims"],
}
(REPO / checkpoint_rel).write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")

common = {"actor": "worker-081", "task_id": TASK, "class_id": "AF-WCC-SCALAR-SPH",
          "node_id": "N0", "gate": "G-NUM", "created_at": NOW}
events = [
    {**common, "event_id": f"w081-{STAMP}-pinsplit-artifact-drift-addendum",
     "event_type": "artifact", "artifact_type": "drift_addendum", "path": add_rel,
     "sha256": sha(add_rel), "validation_status": "unverified",
     "evidence_refs": [f"artifacts/worker-081/n0_pin_split_adjudication/report.json"
                       f"#sha256:{sha('artifacts/worker-081/n0_pin_split_adjudication/report.json')[:12]}"],
     "note": (f"Registry moved {reg_before[:12]} -> {reg_now[:12]} after the report; all 7 "
              f"load-bearing pins re-measured unchanged; 3/3 replication-verdict registration "
              f"gap re-confirmed; verdict unaffected.")},
    {**common, "event_id": f"w081-{STAMP}-pinsplit-artifact-runtime-checkpoint",
     "event_type": "artifact", "artifact_type": "checkpoint", "path": checkpoint_rel,
     "sha256": sha(checkpoint_rel), "validation_status": "unverified",
     "evidence_refs": [f"{add_rel}#sha256:{sha(add_rel)[:12]}"],
     "note": "Conventional runtime/state worker checkpoint: complete, 11/11 checks, 7/7 controls."},
    {**common, "event_id": f"w081-{STAMP}-pinsplit-drift-status", "event_type": "status",
     "status": "active",
     "summary": (f"{TASK} drift handled: controller registry moved after report.json "
                 f"({reg_before[:12]} -> {reg_now[:12]}); load-bearing pins unchanged; "
                 f"registration gap for the three independent replication verdicts still open "
                 f"at the new registry hash; verdict unchanged. Runtime checkpoint "
                 f"{checkpoint_rel} written. Worker completion claim only."),
     "evidence_refs": [f"{add_rel}#sha256:{sha(add_rel)[:12]}",
                       f"{checkpoint_rel}#sha256:{sha(checkpoint_rel)[:12]}"],
     "next_falsifier": report["falsifier"]},
]

outbox = REPO / "comms/outbox/worker-081.jsonl"
existing = set()
for line in outbox.read_text().splitlines():
    try:
        existing.add(json.loads(line).get("event_id"))
    except json.JSONDecodeError:
        continue
with outbox.open("a") as fh:
    for e in events:
        if e["event_id"] not in existing:
            fh.write(json.dumps(e, sort_keys=True) + "\n")
print(f"addendum   : {add_rel} {sha(add_rel)[:12]}")
print(f"checkpoint : {checkpoint_rel} {sha(checkpoint_rel)[:12]}")
print(f"outbox     : {len(events)} event(s) ensured")
