#!/usr/bin/env python3
"""Emit the W002 claim36-supersession events to the outbox (idempotent, append-only).

Appends to comms/outbox/deepseek-flash-02.jsonl:
  * one `artifact` event per frozen deliverable (path + sha256 + validation_status)
  * the `claim` event, verbatim from emitted_claim.json
  * task-scoped `status` checkpoint and exit events

It also writes CHECKPOINT.json in the artifact directory and mirrors it to
runtime/state/w002_claim36_retire_checkpoint.json (+ .jsonl history). It writes no
canonical file and does not run ingest/apply: the controller owns the map.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
STATE = ROOT / "runtime/state"
OUTBOX = ROOT / "comms/outbox/deepseek-flash-02.jsonl"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).replace(microsecond=0)
RUN = json.loads((OUT / "report.json").read_text())["run_id"]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(Path(p).resolve().relative_to(ROOT))


report = json.loads((OUT / "report.json").read_text())
claim = json.loads((OUT / "emitted_claim.json").read_text())
cf = report["counterfactual"]

# ---- checkpoint (frozen before emission so it can be cited in a status event)
artifacts = [
    ("instrument_claim36_supersede", OUT / "rephrase_claim36.py"),
    ("claim36_snapshot_pre_supersede", OUT / "snapshot_claim36.json"),
    ("claim36_proposed_payload", OUT / "proposed_claim.json"),
    ("claim36_measurement_report", OUT / "report.json"),
    ("claim36_emitted_payload", OUT / "emitted_claim.json"),
]
artifact_hashes = {rel(p): sha256_file(p) for _, p in artifacts}

checkpoint = {
    "checkpoint_id": f"w002-claim36-supersede-{NOW.isoformat()}",
    "actor": "worker-002",
    "agent_id": "deepseek-flash-02",
    "task": "W002-F0-CLAIM36-SUPERSEDE: author-side supersession of claims[36] (astra-life03-repin-claims item 3; CF-16)",
    "node_id": "F0",
    "gate": "G-F0",
    "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
    "measured_at": NOW.isoformat(),
    "verdict": report["verdict"],
    "old_claim_event_id": report["old_claim"]["event_id"],
    "new_claim_event_id": report["new_claim"]["event_id"],
    "map_sha256_at_run": report["inputs"]["research_map/research_map.json"],
    "counterfactual": {
        "live_hard_total": cf["live_hard_total"],
        "claim36_attributed": cf["findings_attributed_to_claim36"],
        "after_retire_claim36_only": cf["after_retire_claim36_only"],
        "after_retire_plus_rephrase": cf["after_retire_plus_rephrased_claim"],
        "append_only_plus_rephrase": cf["append_only_plus_rephrased_claim"],
        "candidate_hard_total": cf["candidate_hard_total"],
        "candidate_clears_live": cf["candidate_clears_live"],
        "acceptance_of_astra-life03-repin-claims": cf["acceptance_of_astra-life03-repin-claims"],
    },
    "artifacts": artifact_hashes,
    "falsifier": report["falsifier"],
    "next_falsifier": report["next_falsifier"],
    "authority_note": "Worker event; cannot set node status=done, validation_status=passed, or a gate verdict. No canonical file was written.",
    "rollback": "Delete artifacts/flash-02/claim36_supersede/ and the matching outbox events; no canonical file was written.",
}
(OUT / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
(STATE / "w002_claim36_retire_checkpoint.json").write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
with (STATE / "w002_claim36_retire_checkpoints.jsonl").open("a") as f:
    f.write(json.dumps({**checkpoint, "checkpoint_artifact_sha256": sha256_file(OUT / "CHECKPOINT.json")},
                       sort_keys=True) + "\n")

# ---- regenerate SHA256SUMS to cover CHECKPOINT.json too
hlines = [f"{sha256_file(p)}  {p.name}" for p in sorted(OUT.glob("*")) if p.is_file() and p.name != "SHA256SUMS"]
(OUT / "SHA256SUMS").write_text("\n".join(hlines) + "\n")

# ---- events
events = []
for i, (atype, p) in enumerate(artifacts + [("checkpoint", OUT / "CHECKPOINT.json"),
                                            ("bundle_hashes", OUT / "SHA256SUMS")], 1):
    events.append({
        "event_id": f"flash02-claim36supersede-artifact-{i:04d}-{RUN}",
        "event_type": "artifact",
        "created_at": NOW.isoformat(),
        "actor": "deepseek-flash-02",
        "node_id": "F0",
        "gate": "G-F0",
        "class_id": ";".join(checkpoint["class_ids"]),
        "artifact_type": atype,
        "path": rel(p),
        "sha256": sha256_file(p),
        "validation_status": "unverified",
        "summary": "W002 claim36 supersession deliverable; worker submission only, no gate verdict.",
        "evidence_refs": [f"{rel(p)}#{sha256_file(p)[:12]}"],
    })
events.append(claim)

cp_sha = sha256_file(OUT / "CHECKPOINT.json")
events.append({
    "event_id": f"flash02-claim36supersede-status-checkpoint-{RUN}",
    "event_type": "status",
    "created_at": NOW.isoformat(),
    "actor": "deepseek-flash-02",
    "node_id": "F0",
    "gate": "G-F0",
    "class_id": ";".join(checkpoint["class_ids"]),
    "status": "active",
    "hours": 0.25,
    "summary": (
        "CHECKPOINT W002-F0-CLAIM36-SUPERSEDE (task-level status; node F0 remains done/passed and this "
        "worker event cannot move it). Rephrased superseding claim emitted for "
        f"{report['old_claim']['event_id']} -> {report['new_claim']['event_id']}; the new statement and claim "
        "object yield 0 class_separation findings under the live detector (positive control flags, vs-form and "
        f"negation-guard controls clean). Measured counterfactual: live hard total {cf['live_hard_total']}, "
        f"claim36-attributed {cf['findings_attributed_to_claim36']}, after retiring only claim36 "
        f"{cf['after_retire_claim36_only']}, append-only with the rephrase {cf['append_only_plus_rephrased_claim']}, "
        f"staged candidate detector {cf['candidate_hard_total']} (does not clear). Author-side rewording alone "
        "does NOT meet the astra-life03-repin-claims acceptance; the remaining findings need the CF-16 "
        "claims-retirement policy / detector calibration (astra-life05-classsep-calibration, audit lead). No "
        "canonical file was written; map sha unchanged during the run."
    ),
    "evidence_refs": [
        f"artifacts/flash-02/claim36_supersede/CHECKPOINT.json#{cp_sha[:12]}",
        f"artifacts/flash-02/claim36_supersede/report.json#{artifact_hashes['artifacts/flash-02/claim36_supersede/report.json'][:12]}",
        f"artifacts/flash-02/claim36_supersede/emitted_claim.json#{artifact_hashes['artifacts/flash-02/claim36_supersede/emitted_claim.json'][:12]}",
    ],
    "next_falsifier": report["next_falsifier"],
})
events.append({
    "event_id": f"flash02-claim36supersede-status-exit-{RUN}",
    "event_type": "status",
    "created_at": NOW.isoformat(),
    "actor": "deepseek-flash-02",
    "node_id": "F0",
    "gate": "G-F0",
    "class_id": ";".join(checkpoint["class_ids"]),
    "status": "active",
    "hours": 0.1,
    "summary": (
        "Bounded task complete; exiting cleanly. Card astra-life03-repin-claims: items 1-2 were already landed "
        "by the rebind-r2 repair (corpus ccf7041bd0ff, F1 tests bound cce9c60146d6); item 3 (author-side "
        "superseding claim for the open-case statement) is delivered here. Acceptance 'audit_evidence zero hard "
        "failures' is not reachable by author-side rewording alone and is routed to the CF-16 calibration; "
        "see report.json counterfactual. No completion, validation or gate status is claimed."
    ),
    "evidence_refs": [
        f"artifacts/flash-02/claim36_supersede/CHECKPOINT.json#{cp_sha[:12]}",
        f"artifacts/flash-02/claim36_supersede/emitted_claim.json#{artifact_hashes['artifacts/flash-02/claim36_supersede/emitted_claim.json'][:12]}",
    ],
    "next_falsifier": report["next_falsifier"],
})

# ---- idempotent append
existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            existing.add(json.loads(line)["event_id"])
        except Exception:
            continue
appended = []
with OUTBOX.open("a") as f:
    for ev in events:
        if ev["event_id"] in existing:
            continue
        f.write(json.dumps(ev, sort_keys=True) + "\n")
        appended.append(ev["event_id"])

print(json.dumps({
    "run_id": RUN,
    "outbox": rel(OUTBOX),
    "events_total": len(events),
    "appended": appended,
    "checkpoint_sha256": cp_sha,
    "claim_event_id": claim["event_id"],
    "new_statement_sha256": report["new_claim"]["statement_sha256"],
}, indent=1))
sys.exit(0)
