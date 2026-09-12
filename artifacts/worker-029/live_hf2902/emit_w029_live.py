#!/usr/bin/env python3
"""
W029-LIVE-HF2902-04 — event emission, checkpoint, outbox append.

Validates every event against research_map/schemas.py before writing anything.
Fails closed if a canonical path moves between the snapshot and emission, because
then the measurement is superseded and must not be published as current.
Idempotent on event_id.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event, SchemaError  # noqa: E402

TZ = timezone(timedelta(hours=8))
NOW_DT = datetime.now(TZ)
NOW = NOW_DT.isoformat(timespec="seconds")
STAMP = NOW_DT.strftime("%Y%m%dT%H%M%S")
HERE = Path(__file__).resolve().parent
REL = "artifacts/worker-029/live_hf2902"
TASK = "W029-LIVE-HF2902-04"
NODE = "F1,F2a,F2b"
CLASSES = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"
GATE = "G-FORM"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


report = json.loads((HERE / "report.json").read_text())
evidence = json.loads((HERE / "evidence.json").read_text())
core = json.loads((HERE / "report_core.json").read_text())
manifest = json.loads((HERE / "snapshot_manifest.json").read_text())

FILES = {
    "checker": (f"{REL}/check_live_hf2902.py", "checker_code"),
    "report": (f"{REL}/report.json", "audit_report"),
    "evidence": (f"{REL}/evidence.json", "evidence"),
    "core": (f"{REL}/report_core.json", "deterministic_core"),
    "readme": (f"{REL}/REVIEW.md", "summary"),
    "manifest": (f"{REL}/snapshot_manifest.json", "snapshot_manifest"),
    "snapshotter": (f"{REL}/snapshot_live_hf2902.py", "snapshot_script"),
}
measured = {k: sha(HERE / Path(rel).name) for k, (rel, _) in FILES.items()}

# ---- fail closed on live drift -------------------------------------------------
drift = {}
ok = True
for name, meta in manifest["files"].items():
    live = ROOT / meta["source_path"]
    h = sha(live) if live.exists() else None
    drift[meta["source_path"]] = {"snapshot_sha256": meta["sha256"], "live_sha256_at_emission": h, "match": h == meta["sha256"]}
    ok &= h == meta["sha256"]
for tag, meta in manifest["ledgers"].items():
    live = ROOT / meta["source_path"]
    h = sha(live) if live.exists() else None
    drift[f"ledger:{tag}"] = {"snapshot_sha256": meta["sha256"], "live_sha256_at_emission": h, "match": h == meta["sha256"]}
    ok &= h == meta["sha256"]
if not ok:
    print("LIVE DRIFT AT EMISSION — refusing to publish a stale pin. Drift:")
    print(json.dumps({k: v for k, v in drift.items() if not v["match"]}, indent=2))
    sys.exit(1)

hashes = core["measured_hashes"]
F1H = hashes["af_wcc_vacuum.yaml"]
F2AH = hashes["af_scc_c2_vacuum.yaml"]
F2BH = hashes["af_scc_c0_vacuum.yaml"]
LIVE_LEDGER = core["ledger"]["live_sha256"]
REV3_LEDGER = core["ledger"]["rev3_sha256"]
PRE_LEDGER = core["ledger"]["pre_rev3_sha256"]
summary = report["summary"]
FALSIFIER = report["falsifier"]
SCORE = report["score"]

HARD_FAILURE = {
    "id": "HF-29-02",
    "check_id": "C2-HF-29-02-live-ledger",
    "severity": "hard",
    "finding": (
        "HF-29-02 survives the CF-19 ledger rewrite. At the live bytes %d of 15 l1_ledger_refs rows "
        "assert citation_status='verified_by_L1' while the live ledger/theorems.jsonl @%s records "
        "verification_status='abstract-read' and review_status='not_independently_reviewed' for every "
        "row (61 abstract-read + 1 unverified, 0 independently reviewed). The token appears in no "
        "ledger generation (pre-rev3 %s, rev3 %s, live %s). ledger/citation_audit.csv verifies citation "
        "metadata, not independent reading. Affected: F1 T-204/T-208; F2a T-401/T-402/T-514/T-520; "
        "F2b D-002/T-301/T-302/T-515/T-528."
        % (summary["overclaim_rows"], LIVE_LEDGER[:12], PRE_LEDGER[:12], REV3_LEDGER[:12], LIVE_LEDGER[:12])
    ),
    "evidence": [
        f"{REL}/evidence.json#{measured['evidence'][:12]}",
        f"ledger/theorems.jsonl#{LIVE_LEDGER[:12]}",
        f"schemas/af_wcc_vacuum.yaml#{F1H[:12]}",
        f"schemas/af_scc_c2_vacuum.yaml#{F2AH[:12]}",
        f"schemas/af_scc_c0_vacuum.yaml#{F2BH[:12]}",
    ],
    "falsifier": (
        "Show a live ledger row whose verification_status/review_status records independent L1 "
        "verification for one of the 11 cited ids, or show the 11 citation_status values revised to the "
        "ledger vocabulary."
    ),
}

FINDINGS = [
    {"id": "W029L-01", "check_id": "C1", "severity": "pass",
     "finding": "The three class schemas and the canonical taxonomy are byte-identical to the rev12 pins; no duplicate mapping keys; the ledger is the only canonical input that moved."},
    {"id": "W029L-02", "check_id": "C2", "severity": "hard",
     "finding": "11 of 15 l1_ledger_refs rows over-claim citation_status=verified_by_L1 against the live ledger; the token exists in no ledger generation."},
    {"id": "W029L-03", "check_id": "C3", "severity": "pass",
     "finding": "The 11 cited rows carry verification_status=abstract-read in the pre-rev3, rev3 and live generations; no generation records independent review, so CF-19 did not repair or alter the finding."},
    {"id": "W029L-04", "check_id": "C5", "severity": "pass",
     "finding": "Comparator controls pass 5/5, so C2 is not a vacuous failure: exact match and conservative downgrade are honest; over-claim and missing-row are caught."},
]

EVENTS = [
    *[
        {
            "event_id": f"w029L-{STAMP}-artifact-{k}",
            "event_type": "artifact", "created_at": NOW, "actor": "worker-029",
            "node_id": NODE, "class_id": CLASSES, "gate": GATE, "task_id": TASK,
            "artifact_type": atype, "path": rel, "sha256": measured[k],
            "validation_status": "unverified",
            "note": "Read-only re-binding of HF-29-02 to the live bytes; snapshots under the same directory.",
        }
        for k, (rel, atype) in FILES.items()
    ],
    {
        "event_id": f"w029L-{STAMP}-review-hf2902-live",
        "event_type": "review", "created_at": NOW, "actor": "worker-029",
        "reviewer": "worker-029", "target_id": NODE, "class_id": CLASSES, "gate": GATE,
        "artifact_path": "schemas/af_wcc_vacuum.yaml;schemas/af_scc_c2_vacuum.yaml;schemas/af_scc_c0_vacuum.yaml",
        "reviewed_sha256": f"{F1H};{F2AH};{F2BH}",
        "verdict": report["verdict"], "score": SCORE,
        "hard_failures": [HARD_FAILURE], "findings": FINDINGS,
        "evidence_refs": [
            f"{REL}/report.json#{measured['report'][:12]}",
            f"{REL}/evidence.json#{measured['evidence'][:12]}",
            f"ledger/theorems.jsonl#{LIVE_LEDGER[:12]}",
        ],
        "falsifier": FALSIFIER,
    },
    {
        "event_id": f"w029L-{STAMP}-claim-hf2902-live",
        "event_type": "claim", "created_at": NOW, "actor": "worker-029",
        "node_id": NODE, "class_id": CLASSES, "gate": GATE, "task_id": TASK,
        "conclusion_type": "numerical_evidence",
        "artifact_refs": [
            f"{REL}/report.json#{measured['report'][:12]}",
            f"{REL}/evidence.json#{measured['evidence'][:12]}",
            f"{REL}/check_live_hf2902.py#{measured['checker'][:12]}",
            f"{REL}/REVIEW.md#{measured['readme'][:12]}",
        ],
        "statement": (
            "Deterministic re-binding of HF-29-02 to the live bytes: F1 %s / F2a %s / F2b %s and the "
            "canonical F0 taxonomy are byte-identical to the rev12 pins (C1), so the ledger is the only "
            "moved input. The live ledger/theorems.jsonl %s (CF-19 rewrite at 00:35:19) still records "
            "verification_status='abstract-read' and review_status='not_independently_reviewed' for "
            "every cited row (62 rows: 61 abstract-read + 1 unverified, 0 independently reviewed), and "
            "11 of 15 l1_ledger_refs rows assert citation_status='verified_by_L1', a token absent from "
            "all three ledger generations (pre-rev3 %s, rev3 %s, live %s). The 11 rows are "
            "evidence-invariant across the three generations (C3). 5 of 6 checks PASS; exactly one hard "
            "check FAILS (C2); comparator controls pass 5/5 (C5). Verdict revise, score 2.0. Worker "
            "evidence only; no gate verdict, node status, or validation_status is claimed."
        ) % (F1H[:12], F2AH[:12], F2BH[:12], LIVE_LEDGER[:12], PRE_LEDGER[:12], REV3_LEDGER[:12], LIVE_LEDGER[:12]),
        "assumptions": [
            "The verdict binds only to the snapshot bytes under artifacts/worker-029/live_hf2902/; all seven canonical paths were re-measured matching at emission.",
            "Honesty rule (unchanged from W029-REV12-CLOSURE-03): a citation_status is honest iff it equals the ledger row's verification_status, or is a conservative downgrade (unresolved/unverified vs unverified/abstract-read); a missing row or an undefined token is not honest.",
            "Because the four formulation inputs are byte-identical to the rev12 pins, only the ledger-consuming check C2 needed re-derivation; HF-29-01 and HF-29-03 remain closed at the unchanged schema bytes.",
            "A missing review_status field in the pre-rev3 generation is field-presence drift, not independent review.",
            "A worker review is evidence only and cannot set a gate verdict, a node status, or validation_status.",
        ],
        "falsifier": FALSIFIER,
        "evidence_refs": [
            f"schemas/af_wcc_vacuum.yaml#{F1H}", f"schemas/af_scc_c2_vacuum.yaml#{F2AH}",
            f"schemas/af_scc_c0_vacuum.yaml#{F2BH}", f"ledger/theorems.jsonl#{LIVE_LEDGER}",
            f"artifacts/literature/archive/theorems.rev3-handpatch-20260912T003026.jsonl#{REV3_LEDGER}",
            f"artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl#{PRE_LEDGER}",
            f"{REL}/evidence.json#{measured['evidence'][:12]}",
        ],
    },
    {
        "event_id": f"w029L-{STAMP}-blocker-hf2902-live",
        "event_type": "blocker", "created_at": NOW, "actor": "worker-029",
        "node_id": NODE, "class_id": CLASSES, "gate": GATE, "task_id": TASK,
        "description": HARD_FAILURE["finding"], "severity": "high",
        "needed_to_unblock": (
            "Formulation-side, one of: (i) set citation_status on the 11 rows (F1 T-204/T-208; F2a "
            "T-401/T-402/T-514/T-520; F2b D-002/T-301/T-302/T-515/T-528) to the ledger vocabulary "
            "(abstract-read), consistent with the same schemas' citation_status: unverified footer; or "
            "(ii) record genuine independent L1 verification in ledger/theorems.jsonl and re-pin the "
            "ledger hash. The CF-19 live ledger %s did not change the citation-evidence level of any "
            "cited row, so the L0 freeze reconciliation does not by itself close HF-29-02."
            % LIVE_LEDGER[:12]
        ),
        "evidence_refs": [
            f"{REL}/evidence.json#{measured['evidence'][:12]}", f"ledger/theorems.jsonl#{LIVE_LEDGER[:12]}",
            f"schemas/af_scc_c0_vacuum.yaml#{F2BH[:12]}", f"schemas/af_wcc_vacuum.yaml#{F1H[:12]}",
            f"schemas/af_scc_c2_vacuum.yaml#{F2AH[:12]}",
        ],
        "stop_rule": (
            "No further re-binding from this worker until a schema citation_status value changes or the "
            "live ledger hash changes; either voids this measurement and needs a fresh snapshot. The fix "
            "is owned by astra-lead-formulation / astra-lead-literature."
        ),
    },
    {
        "event_id": f"w029L-{STAMP}-status-complete",
        "event_type": "status", "created_at": NOW, "actor": "worker-029",
        "node_id": NODE, "class_id": CLASSES, "gate": GATE, "task_id": TASK,
        "status": "active", "hours": 0.4,
        "summary": (
            "W029-LIVE-HF2902-04 complete at worker level: one bounded class-bound re-binding of HF-29-02 "
            "to the live bytes. Schema/taxonomy pins unchanged from rev12; live ledger %s still "
            "abstract-read / not_independently_reviewed for all cited rows; 11 of 15 l1_ledger_refs "
            "over-claim verified_by_L1; 5/6 checks PASS, one hard FAIL (C2); verdict revise 2.0. No "
            "canonical artifact edited. This is a completion claim, not a node transition. Checkpoint: "
            "runtime/state/w029_live_hf2902_checkpoint.json."
        ) % LIVE_LEDGER[:12],
        "evidence_refs": [
            f"{REL}/report.json#{measured['report'][:12]}", f"{REL}/evidence.json#{measured['evidence'][:12]}",
            f"{REL}/REVIEW.md#{measured['readme'][:12]}",
        ],
        "next_falsifier": FALSIFIER,
    },
]

errors = []
for ev in EVENTS:
    try:
        validate_event(dict(ev))
    except SchemaError as ex:
        errors.append(f"{ev['event_id']}: {ex}")
if errors:
    print("VALIDATION FAILED — nothing written:")
    for e in errors:
        print(" ", e)
    sys.exit(1)
print(f"validated {len(EVENTS)} events OK")

checkpoint = {
    "checkpoint_id": f"w029L-ckpt-{STAMP}",
    "worker": "worker-029",
    "task_id": TASK,
    "created_at": NOW,
    "node_id": NODE,
    "class_ids": CLASSES.split(";"),
    "gate": GATE,
    "status": "complete",
    "kind": "artifact_and_checker_measurement",
    "is_theorem": False,
    "verdict": report["verdict"],
    "score": SCORE,
    "summary": summary,
    "schema_pins_unchanged_from_rev12": core["schema_pins_unchanged_from_rev12"],
    "ledger_hashes": core["ledger"],
    "reviewed_sha256": f"{F1H};{F2AH};{F2BH}",
    "snapshot_is_live_at_emission": True,
    "live_paths_rechecked_at_emission": drift,
    "artifacts": {k: {"path": rel, "sha256": measured[k]} for k, (rel, _) in FILES.items()},
    "event_ids": [e["event_id"] for e in EVENTS],
    "outbox": "comms/outbox/worker-029.jsonl",
    "note": "worker-scoped checkpoint; did not run research_map/checkpoint.py (controller-owned, mutates shared state)",
}
ckpt = ROOT / "runtime/state/w029_live_hf2902_checkpoint.json"
ckpt.write_text(json.dumps(checkpoint, indent=2) + "\n")
print("checkpoint written:", ckpt.relative_to(ROOT), sha(ckpt)[:12])

outbox = ROOT / "comms/outbox/worker-029.jsonl"
existing = set()
for line in outbox.read_text().splitlines():
    if line.strip():
        try:
            existing.add(json.loads(line).get("event_id"))
        except json.JSONDecodeError:
            pass
new = [e for e in EVENTS if e["event_id"] not in existing]
with outbox.open("a") as f:
    for e in new:
        f.write(json.dumps(e) + "\n")
print(f"outbox appended {len(new)} events ({len(EVENTS) - len(new)} already present)")
print("final hashes:", json.dumps(measured, indent=1))
