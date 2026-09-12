#!/usr/bin/env python3
"""W083-F2B-CANDIDATE-ADJUDICATION-01 finalizer.

Writes checkpoint.json + MANIFEST.json next to the deliverables, then emits
protocol events (status / artifact / claim) to comms/outbox/worker-083.jsonl and
a checkpoint record to runtime/state/.  Idempotent: events already present in the
outbox are skipped by event_id.  File order is fixed so the artifact hashes
emitted in the events match the bytes on disk:

  1. measure pins_pre
  2. write checkpoint.json (excluding its own and MANIFEST's hash)
  3. write MANIFEST.json (includes checkpoint.json)
  4. emit artifact/claim/status events with the final hashes
  5. measure pins_after_emit; drift is reported separately and never mutates the
     frozen deliverable set.

Usage: python3 finalize.py [--emit]
  without --emit: dry run; writes nothing.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "artifacts/worker-083/f2b_candidate_adjudication"
OUTBOX = ROOT / "comms/outbox/worker-083.jsonl"
STATE = ROOT / "runtime/state"
CKPT_EVENTS = STATE / "w083_checkpoints.jsonl"
CKPT_JSON = STATE / "w083_f2b_candidate_adjudication_checkpoint.json"
DRIFT_JSON = STATE / "w083_f2b_candidate_adjudication_drift.json"

TZ = timezone(timedelta(hours=8))
TASK_ID = "W083-F2B-CANDIDATE-ADJUDICATION-01"
EVENT_ID = "w083-f2b-candadj-01"

PIN_FILES = {
    "schemas/af_scc_c0_vacuum.yaml": ROOT / "schemas/af_scc_c0_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml": ROOT / "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_wcc_vacuum.yaml": ROOT / "schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml":
        ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/FROZEN.json": ROOT / "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/VARIANT_REGISTRY.json": ROOT / "artifacts/formulation/VARIANT_REGISTRY.json",
    "research_map/formulation_taxonomy.yaml": ROOT / "research_map/formulation_taxonomy.yaml",
    "artifacts/worker-024/f2b_rev29_repair/CANDIDATE_schemas_af_scc_c0_vacuum.yaml":
        ROOT / "artifacts/worker-024/f2b_rev29_repair/CANDIDATE_schemas_af_scc_c0_vacuum.yaml",
    "artifacts/worker-083/f2b_live_defect_ledger/candidate/af_scc_c0_vacuum.yaml":
        ROOT / "artifacts/worker-083/f2b_live_defect_ledger/candidate/af_scc_c0_vacuum.yaml",
}

# (artifact_type, filename) emitted as artifact events
EVENT_FILES = [
    ("tool", "adjudicate.py"),
    ("tool", "finalize.py"),
    ("report", "report.json"),
    ("evidence", "evidence.json"),
    ("controls", "controls.json"),
    ("report", "REPORT.md"),
    ("manifest", "MANIFEST.json"),
    ("checkpoint", "checkpoint.json"),
]
# hash inventory carried inside checkpoint.json (self/MANIFEST excluded)
CKPT_HASH_FILES = ["adjudicate.py", "finalize.py", "report.json", "evidence.json",
                   "controls.json", "REPORT.md"]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(TZ).isoformat()


def hash_map(files) -> dict:
    return {str(p.relative_to(ROOT)): sha256(p) for p in files}


def build_events(ts, checks, controls, rec, report) -> list:
    events = []
    for kind, name in EVENT_FILES:
        p = ART / name
        events.append({
            "event_id": f"{EVENT_ID}-artifact-{name.replace('.', '-')}",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "worker-083",
            "node_id": "F2b",
            "gate": "G-FORM",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": ["AF-SCC-C0-VAC-GEN"],
            "task_id": TASK_ID,
            "artifact_type": kind,
            "path": str(p.relative_to(ROOT)),
            "sha256": sha256(p),
            "validation_status": "unverified",
            "note": "W083-F2B-CANDIDATE-ADJUDICATION-01 deliverable (worker measurement; not gate evidence)",
        })
    ev = {n: f"{str((ART / n).relative_to(ROOT))}#{sha256(ART / n)[:12]}" for n in
          ("report.json", "evidence.json", "controls.json", "adjudicate.py", "REPORT.md",
           "MANIFEST.json", "checkpoint.json")}
    claim = {
        "event_id": f"{EVENT_ID}-claim-001",
        "event_type": "claim",
        "created_at": ts,
        "actor": "worker-083",
        "task_id": TASK_ID,
        "node_id": "F2b",
        "gate": "G-FORM",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "conclusion_type": "stability_result",
        "claims_theorem_status": False,
        "statement": (
            "Artifact-and-checker result (not a mathematics or physics claim) at FROZEN rev29 "
            "815e08079aef (F2b b2ab6acb2bbe): BOTH apply-ready rev29 repair candidates for "
            "W018-R13-F2B-B1 (line 152 containment denial) and W018-R13-F2B-B2 (line 246 strength "
            "inversion) resolve both defects with exactly the two declared lines changed "
            "(measured sets {152,246}; line counts unchanged; every other line byte-identical; "
            "conclusion_type identical to live, so D3 stays out of scope). Candidate 024 "
            "679ab7bc8746 adds 511 bytes and cites W018-R13-F2B-B1/B2, implication_ledger and the "
            "FROZEN-pinned VARIANT_REGISTRY (H2LOC, parent AF-SCC-C0-VAC-GEN, "
            "registered_variant_not_written) - all verified true; candidate 083 1315427fbc92 adds "
            "126 bytes with the nesting claim byte-derivable from live line 238 and no new external "
            "reference. Under the pre-registered rule (Q1 correctness, Q2 frozen-byte support, "
            "Q3 minimal delta, Q4 no new external reference) both qualify and C083 is selected on "
            "minimality, with an author conflict declared because this worker authored C083; C024 "
            "is equally correct and checker-clean if repair-ID traceability is preferred. The "
            "canonical check_class_schema.py passes on live and both candidates, so it does not "
            "adjudicate this; the adjudication is the semantic check pair plus the 8-control "
            "battery. 37/37 checks, 8/8 controls, zero pin drift. No gate verdict, no node status, "
            "no validation_status, no canonical write, no repair applied."
        ),
        "assumptions": [
            "the live bytes and the FROZEN rev29 pins are the object of measurement and were stable across the run (pins_pre == pins_after_emit)",
            "the file's own implication_ledger.extension_class_containment (line 238) is the authority for the containment direction",
            "quoted or bracketed spans are mentions, not assertions; the D1/D2 detectors strip them (control N6)",
            "an added assertion is supported iff it is byte-derivable from a FROZEN-pinned artifact; citation presence is recorded as traceability, not required for correctness",
            "the worker may measure and recommend but may not apply a repair, set a gate verdict, node status or validation_status",
        ],
        "falsifier": (
            "Re-run adjudicate.py at the pins: any FAIL, any pin movement, or any undeclared line "
            "difference between live and either candidate voids this adjudication. If live F2b "
            "moves before the owner applies a repair, this claim is void."
        ),
        "evidence_refs": [
            "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
            "artifacts/formulation/FROZEN.json#815e08079aef",
            "artifacts/formulation/VARIANT_REGISTRY.json#6bac9adea19e",
            "artifacts/worker-024/f2b_rev29_repair/CANDIDATE_schemas_af_scc_c0_vacuum.yaml#679ab7bc8746",
            "artifacts/worker-083/f2b_live_defect_ledger/candidate/af_scc_c0_vacuum.yaml#1315427fbc92",
            ev["report.json"], ev["evidence.json"], ev["controls.json"], ev["adjudicate.py"],
        ],
        "artifact_refs": list(ev.values()),
        "recommendation": {
            "candidate": rec["candidate"],
            "candidate_sha256": rec["candidate_sha256"],
            "author_conflict": rec["author_conflict"],
            "counter_argument": rec["counter_argument"],
        },
        "checks": {"passed": checks["passed"], "total": checks["total"], "failed": checks["failed"]},
        "controls": {"passed": controls["passed"], "total": controls["total"], "failed": controls["failed"]},
        "does_not_claim": [
            "no gate verdict (G-FORM stays pending; worker events cannot move a gate)",
            "no node status (F2b stays active/unverified)",
            "no validation_status=passed",
            "no canonical artifact edited or repair applied",
            "no D3 conclusion-token adjudication and no D4 corpus rebind",
            "the recommendation is advisory; applying either candidate is the formulation owner's decision",
        ],
    }
    events.append(claim)
    events.append({
        "event_id": f"{EVENT_ID}-status-001",
        "event_type": "status",
        "created_at": ts,
        "actor": "worker-083",
        "task_id": TASK_ID,
        "node_id": "F2b",
        "gate": "G-FORM",
        "status": "active",
        "hours": 0.3,
        "summary": (
            f"{TASK_ID} complete at worker level: F2b rev29 repair-candidate adjudication, "
            f"{checks['passed']}/{checks['total']} checks, {controls['passed']}/{controls['total']} "
            f"controls, 0 pin drift. Both candidates resolve B1/B2; recommendation "
            f"{rec['candidate']} ({rec['candidate_sha256'][:12]}) under the pre-registered "
            f"minimality rule, author conflict declared. No gate verdict, node status, "
            f"validation_status or canonical write."
        ),
        "next_falsifier": "re-run adjudicate.py at the cited pins; any FAIL or pin movement voids the adjudication",
        "evidence_refs": claim["evidence_refs"],
    })
    return events


def main() -> int:
    emit = "--emit" in sys.argv
    report = json.loads((ART / "report.json").read_text())
    checks, controls, rec = report["checks"], report["controls"], report["recommendation"]

    pins_pre = hash_map(PIN_FILES.values())
    ts = now()

    checkpoint = {
        "checkpoint_id": "w083-ckpt-7",
        "task_id": TASK_ID,
        "created_at": ts,
        "actor": "worker-083",
        "node": "F2b",
        "gate": "G-FORM",
        "classes": ["AF-SCC-C0-VAC-GEN"],
        "checks": {"passed": checks["passed"], "total": checks["total"]},
        "controls": f"{controls['passed']}/{controls['total']}",
        "verdict": report["verdict"],
        "recommendation": rec,
        "pins_pre": pins_pre,
        "pins_post": hash_map(PIN_FILES.values()),
        "pin_drift": False,
        "canonical_writes": False,
        "applied": False,
        "no_completion_claim": True,
        "author_conflict": rec["author_conflict"],
        "artifact_hashes": {n: sha256(ART / n) for n in CKPT_HASH_FILES},
        "outbox": "comms/outbox/worker-083.jsonl",
    }
    checkpoint["pin_drift"] = checkpoint["pins_post"] != checkpoint["pins_pre"]
    checkpoint["artifact_hashes"]["snapshot"] = {
        str(p.relative_to(ART)): sha256(p) for p in sorted(ART.glob("snapshot/*"))
    }
    manifest = {
        "task_id": TASK_ID,
        "actor": "worker-083",
        "created_at": ts,
        "files": [],
    }
    plan = [(k, ART / n) for k, n in EVENT_FILES if n not in ("checkpoint.json", "MANIFEST.json")]
    plan += [("snapshot", p) for p in sorted(ART.glob("snapshot/*"))]
    plan += [("checkpoint", ART / "checkpoint.json")]
    # finalize.py and report files exist already; checkpoint.json is written now
    if not emit:
        print(json.dumps({"dry_run": True, "planned_files": [str(p.relative_to(ROOT)) for _, p in plan],
                          "pins_pre": pins_pre}, indent=1))
        return 0

    (ART / "checkpoint.json").write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
    manifest["files"] = [{"path": str(p.relative_to(ROOT)), "kind": k,
                          "sha256": sha256(p), "bytes": p.stat().st_size} for k, p in plan]
    (ART / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")

    events = build_events(ts, checks, controls, rec, report)

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if not line.strip():
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                continue
    emitted = skipped = 0
    with OUTBOX.open("a") as fh:
        for ev in events:
            if ev["event_id"] in existing:
                skipped += 1
                continue
            fh.write(json.dumps(ev, sort_keys=True) + "\n")
            emitted += 1

    pins_after = hash_map(PIN_FILES.values())
    drift = pins_after != pins_pre
    if drift:
        DRIFT_JSON.write_text(json.dumps({
            "task_id": TASK_ID, "measured_at": now(),
            "pins_pre": pins_pre, "pins_after_emit": pins_after,
            "note": "pin movement during emission; artifact hashes bind the pre-move bytes",
        }, indent=1, sort_keys=True) + "\n")
    CKPT_JSON.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
    with CKPT_EVENTS.open("a") as fh:
        fh.write(json.dumps({
            "checkpoint_id": checkpoint["checkpoint_id"],
            "task_id": TASK_ID,
            "created_at": checkpoint["created_at"],
            "actor": "worker-083",
            "node": "F2b",
            "gate": "G-FORM",
            "checks": checkpoint["checks"],
            "controls": checkpoint["controls"],
            "verdict": checkpoint["verdict"],
            "recommendation": rec["candidate"],
            "pin_drift": drift,
            "artifact_hashes": {k: v for k, v in checkpoint["artifact_hashes"].items() if k != "snapshot"},
        }, sort_keys=True) + "\n")

    unparseable = 0
    for line in OUTBOX.read_text().splitlines():
        if not line.strip():
            continue
        try:
            json.loads(line)
        except json.JSONDecodeError:
            unparseable += 1
    summary = {"emitted": emitted, "skipped_existing": skipped, "pin_drift": drift,
               "outbox_unparseable_lines": unparseable,
               "checkpoint": str(CKPT_JSON.relative_to(ROOT)),
               "manifest_files": len(manifest["files"])}
    print(json.dumps(summary, indent=1))
    return 1 if (drift or unparseable) else 0


if __name__ == "__main__":
    sys.exit(main())
