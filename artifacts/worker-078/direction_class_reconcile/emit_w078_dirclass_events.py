#!/usr/bin/env python3
"""Emit W078-DIRCENSUS-CLASS-RECONCILE-01 events to comms/outbox/worker-078.jsonl.

Idempotent by event_id: existing ids are skipped.  Validates every event against
research_map/schemas.validate_event before appending, and re-measures every cited artifact
hash on disk so a stale hash can never be emitted.  Workers cannot set done/passed/gate
verdicts; the final status is `active` with an explicit completion-scope note.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event, SchemaError  # noqa: E402

D = "artifacts/worker-078/direction_class_reconcile"
OUTBOX = ROOT / "comms/outbox/worker-078.jsonl"
CREATED = "2026-09-12T01:21:00+08:00"
TASK = "W078-DIRCENSUS-CLASS-RECONCILE-01"
CLASS_ID = "AF-WCC-VAC-GEN"
NODE = "F0"


def sha(rel: str) -> str:
    h = hashlib.sha256()
    with (ROOT / rel).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(rel: str) -> str:
    return f"{rel}#{sha(rel)[:12]}"


EV = []
EV.append({
    "event_id": "w078-dirclass-20260912T0121-status-start", "event_type": "status",
    "created_at": CREATED, "actor": "worker-078", "node_id": NODE, "status": "active",
    "class_id": CLASS_ID, "gate": "G-F0", "hours": 0.1, "task_id": TASK,
    "summary": ("Took ONE bounded class-bound task (no assignment card exists for worker-078): "
                "W078-DIRCENSUS-CLASS-RECONCILE-01 = reconcile the W099 direction census's 3 INVERTED "
                "findings and 34 MANUAL_REVIEW residues against the W078 F0-SET adjudication at the "
                "FROZEN rev29 pins. Read-only on all canonical paths."),
    "evidence_refs": [ref(f"{D}/adjudication_table.json")],
    "next_falsifier": ("Any pin drift, any own-scan strength line outside census windows that is "
                       "OPERATIVE_INVERTED, any anchor mismatch, any fixture flip, or a truth-direction "
                       "violation voids the run."),
})
EV.append({
    "event_id": "w078-dirclass-20260912T0121-claim-reconcile", "event_type": "claim",
    "created_at": CREATED, "actor": "worker-078", "class_id": CLASS_ID, "node_id": NODE,
    "gate": "G-F0", "task_id": TASK, "conclusion_type": "formal_model",
    "statement": ("At the FROZEN rev29 pins (FROZEN 815e08079aef, F0 canonical 0abb9ed8a961, F0 "
                  "supplement d7419b4e8963, F1 d9cebb9404b2, F2a e9a27996dfd3, F2b b2ab6acb2bbe, "
                  "VARIANT_REGISTRY 6bac9adea19e; zero drift), the W099 census classification of "
                  "artifacts/formulation/formulation_taxonomy.yaml:176 as INVERTED is a false positive: "
                  "the phrase sits inside the quoted superseded f0_reading of a resolved divergence-ledger "
                  "record, so no repair is licensed there. The census is under-inclusive at canonical "
                  "research_map/formulation_taxonomy.yaml:94 (operative SET-variant definition asserting "
                  "the inverted direction), which the W078 F0-SET adjudication had already found. The "
                  "operative inverted set at these pins is exactly {F0:94-95, F0:200, F2b:245-246}, and all "
                  "34 census MANUAL_REVIEW rows resolve to NEGATIVE_SCOPE, DEFINITION, OPERATIVE_CORRECT "
                  "or PROBE_RECORD with zero new inversions. The census file also lists 3 keys (F0:141, "
                  "F2b:244, F2a:153) twice with conflicting verdicts (MANUAL_REVIEW and CORRECT)."),
    "assumptions": [
        "the 8 audited files are the gate-relevant formulation corpus at rev29; the census and the prior "
        "W078 report are measured inputs, not audited corpus",
        "the declared containment chain E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0 is the truth "
        "table for class-statement strength (lower regularity => larger extension set => stronger "
        "inexistence statement)",
        "for WCC readings, SINGLEQ (single-q tail) entails SET (union) and not conversely",
        "an anchored adjudication is a worker reading, not an instrument verdict; every anchor is "
        "verbatim in the pinned bytes or the instrument exits 5",
    ],
    "falsifier": ("Re-run reconcile_direction_classification.py at the pins: FALSIFIED if any pin drifts, "
                  "if any own-scan strength line outside census windows is OPERATIVE_INVERTED, if any "
                  "anchor stops matching, if any fixture flips, if the truth derivation reports a "
                  "violation or a surviving cover candidate, or if F0:94/F0:200/F2b:246 stop being "
                  "operative strength assertions."),
    "evidence_refs": [ref(f"{D}/report.json"), ref(f"{D}/adjudication_table.json"),
                      ref("artifacts/worker-099/form_direction_census/census.json"),
                      ref("artifacts/worker-078/f0_set_strength_adjudication/report.json")],
    "artifact_refs": [ref(f"{D}/report.json"), ref(f"{D}/adjudication_table.json")],
})
EV.append({
    "event_id": "w078-dirclass-20260912T0121-review-census", "event_type": "review",
    "created_at": CREATED, "actor": "worker-078", "reviewer": "worker-078",
    "target_id": f"artifacts/worker-099/form_direction_census/census.json#{sha('artifacts/worker-099/form_direction_census/census.json')[:12]}",
    "verdict": "revise", "score": 3.0, "counts_as_full_schema_verdict": False,
    "target_artifact": "artifacts/worker-099/form_direction_census/census.json",
    "reviewed_sha256": sha("artifacts/worker-099/form_direction_census/census.json"),
    "task_id": TASK, "class_id": CLASS_ID, "node_id": NODE,
    "hard_failures": [
        "W078-DC-1 artifacts/formulation/formulation_taxonomy.yaml:176 classified INVERTED but is a "
        "resolved divergence-ledger record (quoted f0_reading, status: resolved); false positive that "
        "would put a historical record into a repair manifest",
        "W078-DC-2 research_map/formulation_taxonomy.yaml:94 operative SET-variant inversion is absent "
        "from the census INVERTED list (it lists only F0:200); the census is under-inclusive",
        "W078-DC-3 the census lists keys F0:141, F2b:244 and F2a:153 twice with conflicting verdicts "
        "(MANUAL_REVIEW and CORRECT), so its 34/25 counts double-count those keys",
    ],
    "findings": ("The census's direction truth table and its three INVERTED *locations* are otherwise "
                 "sound: F0:200 and F2b:246 confirmed OPERATIVE_INVERTED; all 34 MANUAL_REVIEW rows "
                 "resolve non-inverted (14 NEGATIVE_SCOPE, 12 OPERATIVE_CORRECT, 2 DEFINITION after "
                 "dedup, plus the 3 collision keys adjudicated once). Automatic line-level subject "
                 "attribution is the weak point: outside the three known sites it produced 7 false "
                 "OPERATIVE_* verdicts on out-of-scope reference hits, all corrected by reading. "
                 "Recommendation: add a historical/ledger guard and a 'missing operative site' "
                 "cross-check before the census is used as a repair manifest."),
})
for name, kind in [
    (f"{D}/report.json", "audit_artifact"),
    (f"{D}/report_rerun.json", "audit_artifact"),
    (f"{D}/adjudication_table.json", "audit_artifact"),
    (f"{D}/controls.json", "audit_artifact"),
    (f"{D}/reconcile_direction_classification.py", "instrument"),
    (f"{D}/README.md", "audit_artifact"),
    (f"{D}/CHECKPOINT.json", "checkpoint"),
    (f"{D}/snapshot/SHA256SUMS.txt", "manifest"),
]:
    EV.append({
        "event_id": "w078-dirclass-20260912T0121-artifact-" + name.rsplit("/", 1)[-1].replace(".", "-"),
        "event_type": "artifact", "created_at": CREATED, "actor": "worker-078",
        "node_id": NODE, "class_id": CLASS_ID, "gate": "G-F0", "task_id": TASK,
        "artifact_type": kind, "path": name, "sha256": sha(name),
        "validation_status": "unverified",
        "summary": f"{TASK} deliverable: {name}",
    })
EV.append({
    "event_id": "w078-dirclass-20260912T0121-status-final", "event_type": "status",
    "created_at": CREATED, "actor": "worker-078", "node_id": NODE, "status": "active",
    "class_id": CLASS_ID, "gate": "G-F0", "hours": 0.7, "task_id": TASK,
    "completion_scope": "worker lifecycle only; not a node done and not a gate verdict",
    "summary": ("W078-DIRCENSUS-CLASS-RECONCILE-01 complete at worker level (completion claim only; no "
                "node transition, no gate verdict, no canonical write). One class-bound task delivered: "
                "supplement:176 = HISTORICAL_MENTION (census false positive, not repairable); canonical "
                "F0:94 = OPERATIVE_INVERTED (census under-inclusive); F2b:246 confirmed; 34/34 "
                "MANUAL_REVIEW rows non-inverted; 3 census key-verdict collisions recorded; OPT-B repair "
                "set bounded to F0:94-95, F0:200, F2b:245-246. 8/8 controls, 10/10 fixtures, "
                "byte-identical rerun, zero pin drift. Worker checkpoint: "
                "runtime/state/w078_dirclass_checkpoint_1.json. Exiting."),
    "evidence_refs": [ref(f"{D}/report.json"), ref(f"{D}/adjudication_table.json"),
                      ref(f"{D}/controls.json"), ref(f"{D}/CHECKPOINT.json"),
                      ref(f"{D}/snapshot/SHA256SUMS.txt")],
    "next_falsifier": ("Re-run the instrument at the same pins: any pin drift, anchor mismatch, fixture "
                       "flip, truth-direction violation, or missing/extra operative inverted site voids "
                       "the verdict."),
})

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                existing.add(json.loads(line)["event_id"])
            except (ValueError, KeyError):
                pass

appended, skipped = [], []
with OUTBOX.open("a") as f:
    for e in EV:
        if e["event_id"] in existing:
            skipped.append(e["event_id"])
            continue
        try:
            validate_event(e)
        except SchemaError as exc:
            print(f"SCHEMA REJECT {e['event_id']}: {exc}", file=sys.stderr)
            sys.exit(3)
        f.write(json.dumps(e, sort_keys=True) + "\n")
        appended.append(e["event_id"])
print(json.dumps({"appended": appended, "skipped": skipped, "outbox": str(OUTBOX)}, indent=1))
