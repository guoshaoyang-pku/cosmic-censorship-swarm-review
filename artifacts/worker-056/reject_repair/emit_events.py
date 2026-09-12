#!/usr/bin/env python3
"""W056-REJECT-REPAIR-01 — emit the task's protocol events (worker-056).

Emits upward events to `comms/outbox/worker-056.jsonl` only. Idempotent: re-running
skips any event_id already present in the outbox. After writing, it runs the pre-flight
gate on its own outbox file and fails loudly if anything it just emitted would be
rejected — the instrument applies to itself.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms" / "outbox" / "worker-056.jsonl"
CST = timezone(timedelta(hours=8))
TS = "2026-09-12T01:15:30+08:00"
EID = f"w056-{TS.replace(':', '').replace('-', '')[:15]}-rrp"  # stable, idempotent prefix
CKPT = "runtime/state/w056_checkpoint_5.json"
CLASS = "AF-WCC-VAC-GEN"
NODE = "A1"
GATE = "G-AUDIT"

FALSIFIER = (
    "FALSE if any of: (a) a candidate in recovery_bundle.jsonl is rejected by "
    "research_map/schemas.py::validate_event at the pinned hash, or is accepted with a "
    "conclusion_type in the strong set {theorem, conditional_theorem, stability_result, "
    "counterexample, formal_model} (conclusion inflation); (b) preflight_event.py flags any "
    "event drawn from the pinned accepted events.jsonl snapshot (false positive); (c) "
    "run_reject_repair_056.py --check returns FAIL, or two runs at the same pins disagree; "
    "(d) a pinned input hash moves without a drift entry in report.json; (e) some event_id "
    "classified NET_LOST_* is later accepted under that same id without re-emission, which "
    "would refute the terminal-loss mechanism at comms.py:303/313; (f) any file under a "
    "canonical path is shown to have been written by this task."
)


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    report = json.loads((HERE / "report.json").read_text())
    census = report["census"]
    arts = ["README.md", "PATCH_PROPOSAL.md", "preflight_event.py", "repair_map.json",
            "recovery_bundle.jsonl", "reemission_manifest.json", "report.json",
            "run_reject_repair_056.py", "emit_events.py"]
    sha_map = {a: sha(HERE / a) for a in arts}
    ckpt_sha = sha(ROOT / CKPT) if (ROOT / CKPT).is_file() else "pending"

    ev = []

    ev.append({
        "event_id": f"{EID}-take",
        "event_type": "status",
        "actor": "worker-056",
        "created_at": TS,
        "node_id": NODE,
        "node_ids": [NODE, "F1"],
        "class_id": CLASS,
        "class_ids": [CLASS],
        "gate": GATE,
        "status": "active",
        "hours": 0.4,
        "summary": (
            "W056-REJECT-REPAIR-01 taken: one bounded class-bound task on the reject-stream "
            "loss. Division of labour checked first — worker-097 reject_audit (00:45-00:48) "
            "already MEASURED the stream read-only, so this task does the repair half only: "
            "recovery bundle, pre-flight gate, ingest patch proposal. No canonical write."
        ),
        "evidence_refs": [CKPT, "artifact:README.md"],
        "next_falsifier": FALSIFIER,
    })

    for a in arts:
        ev.append({
            "event_id": f"{EID}-art-{a.replace('.', '-').replace('_', '-')}",
            "event_type": "artifact",
            "actor": "worker-056",
            "created_at": TS,
            "node_id": NODE,
            "node_ids": [NODE],
            "class_id": CLASS,
            "class_ids": [CLASS],
            "gate": GATE,
            "artifact_type": "reject_repair_artifact",
            "path": f"artifacts/worker-056/reject_repair/{a}",
            "sha256": sha_map[a],
            "validation_status": "unverified",
            "summary": f"W056-REJECT-REPAIR-01 artifact {a}",
            "evidence_refs": [f"artifacts/worker-056/reject_repair/{a}#{sha_map[a][:12]}",
                              CKPT],
            "next_falsifier": FALSIFIER,
        })

    ev.append({
        "event_id": f"{EID}-claim",
        "event_type": "claim",
        "actor": "worker-056",
        "created_at": TS,
        "node_id": NODE,
        "node_ids": [NODE],
        "class_id": CLASS,
        "class_ids": [CLASS],
        "gate": GATE,
        "conclusion_type": "numerical_evidence",
        "statement": (
            f"Measured at pinned snapshot sha256 {report['snapshot']['sha256'][:12]}: "
            f"comms/rejected.jsonl holds {census['reject_rows']} rows for "
            f"{census['distinct_event_ids']} distinct events; "
            f"{census['classification_distinct']['NET_LOST_STILL_INVALID']} are terminally "
            f"suppressed and still invalid, of which "
            f"{census['net_lost_still_invalid_by_reason']['claim: invalid conclusion_type']} "
            "are claim events rejected solely on an out-of-vocabulary conclusion_type "
            "(schemas.py:46 allows 7 values). Because comms.py:313 adds a rejected event_id "
            "to the seen set consulted before validation at comms.py:303, rejection is "
            "terminal and the emitting worker is never notified. 48 such events were repaired "
            "to numerical_evidence or open_problem under invariant I1 and pass the real "
            "validator; 6 further lost events are not claims and 12 are unrecoverable "
            "because raw is truncated at 600 chars (comms.py:316) and the source has moved."
        ),
        "assumptions": [
            "the reject log and the outbox sources are read from byte-pinned snapshots "
            "(raw/rejected.snapshot.jsonl, raw/sources/, raw/events.snapshot.jsonl), not live files",
            "classification uses the pinned research_map/schemas.py::validate_event and "
            "comms.py::normalize_event at the hashes recorded in report.json.pins",
            "a repair is semantics-preserving only if it targets numerical_evidence or "
            "open_problem; mapping is by explicit table then by measurement/finding rule tier",
            "counts are a measurement at one snapshot; the reject log is append-only and still growing",
        ],
        "artifact_refs": [
            f"artifacts/worker-056/reject_repair/recovery_bundle.jsonl#{sha_map['recovery_bundle.jsonl'][:12]}",
            f"artifacts/worker-056/reject_repair/repair_map.json#{sha_map['repair_map.json'][:12]}",
            f"artifacts/worker-056/reject_repair/report.json#{sha_map['report.json'][:12]}",
            f"artifacts/worker-056/reject_repair/preflight_event.py#{sha_map['preflight_event.py'][:12]}",
        ],
        "evidence_refs": [
            f"artifacts/worker-056/reject_repair/report.json#{sha_map['report.json'][:12]}",
            f"artifacts/worker-056/reject_repair/recovery_bundle.jsonl#{sha_map['recovery_bundle.jsonl'][:12]}",
            f"artifacts/worker-056/reject_repair/reemission_manifest.json#{sha_map['reemission_manifest.json'][:12]}",
            "artifacts/worker-056/reject_repair/raw/rejected.snapshot.jsonl#"
            + report["snapshot"]["sha256"][:12],
            "artifacts/worker-056/reject_repair/raw/events.snapshot.jsonl#"
            + report["events_snapshot"]["sha256"][:12],
            "research_map/comms.py:303",
            "research_map/comms.py:313",
            "research_map/comms.py:316",
            "research_map/schemas.py:46",
            "artifacts/worker-097/reject_audit/PRE_REGISTRATION.md",
            CKPT,
        ],
        "next_falsifier": FALSIFIER,
    })

    ev.append({
        "event_id": f"{EID}-blocker",
        "event_type": "blocker",
        "actor": "worker-056",
        "created_at": TS,
        "node_id": NODE,
        "node_ids": [NODE],
        "class_id": CLASS,
        "class_ids": [CLASS],
        "gate": GATE,
        "description": (
            "Ingest reject path is terminal and lossy: comms.py:313 adds a rejected event_id "
            "to seen, which comms.py:303 consults before validation, so a rejected event can "
            "never be accepted under that id even after the validator is fixed; comms.py:316 "
            "stores only raw[:600], so repair depends on the source outbox file still "
            "containing the id. Measured: 12 of 80 distinct rejected events are already "
            "unrecoverable this way, and 54 are terminally suppressed. The emitting worker "
            "receives no notification."
        ),
        "needed_to_unblock": (
            "A controller ruling on the proposed minimal patch in "
            "artifacts/worker-056/reject_repair/PATCH_PROPOSAL.md (write the full payload to a "
            "rejected_events/ sidecar and expose a preflight subcommand), recorded as an "
            "authorizing event per the CF-26 precedent. Worker-056 has NOT applied the patch."
        ),
        "evidence_refs": [
            f"artifacts/worker-056/reject_repair/PATCH_PROPOSAL.md#{sha_map['PATCH_PROPOSAL.md'][:12]}",
            f"artifacts/worker-056/reject_repair/report.json#{sha_map['report.json'][:12]}",
            "research_map/comms.py:303",
            "research_map/comms.py:313",
            "research_map/comms.py:316",
            CKPT,
        ],
        "next_falsifier": FALSIFIER,
    })

    ev.append({
        "event_id": f"{EID}-final",
        "event_type": "status",
        "actor": "worker-056",
        "created_at": TS,
        "node_id": NODE,
        "node_ids": [NODE, "F1"],
        "class_id": CLASS,
        "class_ids": [CLASS],
        "gate": GATE,
        "status": "active",
        "hours": 0.4,
        "summary": (
            "W056-REJECT-REPAIR-01 delivered: 48 round-trip-validated recovery candidates "
            "(all mapped only to numerical_evidence/open_problem), a reusable pre-flight gate, "
            "a re-emission manifest for 8 verbatim-valid suppressed events, and a proposed "
            "(unapplied) ingest patch. Controls C1-C7 pass; --check reproduces from pins. "
            "No node completion, no gate verdict, no canonical write; re-emission left to the "
            "original actors or the controller."
        ),
        "evidence_refs": [
            f"artifacts/worker-056/reject_repair/README.md#{sha_map['README.md'][:12]}",
            f"artifacts/worker-056/reject_repair/report.json#{sha_map['report.json'][:12]}",
            CKPT,
        ],
        "next_falsifier": FALSIFIER,
    })

    existing = set()
    if OUTBOX.is_file():
        for line in OUTBOX.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except ValueError:
                pass

    # End-to-end demonstration of the repair path on this worker's OWN claim:
    # w056-20260912T0100-claim was terminally rejected at 00:58:20 for
    # conclusion_type='calibration_result' (it is candidate #? in recovery_bundle.jsonl).
    # Re-emitting another actor's claim would misattribute it; re-emitting our own is
    # legitimate, so this is the one candidate emitted rather than merely bundled.
    own = "w056-20260912T0100-claim"
    if OUTBOX.is_file():
        for line in OUTBOX.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("event_id") != own:
                continue
            fixed = dict(d)
            fixed["conclusion_type"] = "numerical_evidence"
            fixed["conclusion_type_repaired_from"] = d.get("conclusion_type")
            fixed["event_id"] = f"{own}-recovered-056"
            fixed["_repair"] = {
                "instrument": "W056-REJECT-REPAIR-01",
                "mapping_tier": "explicit",
                "mapping_rationale": "a calibration outcome is a measured result",
                "invariant": "I1: targets restricted to numerical_evidence|open_problem",
                "original_event_id": own,
                "original_reject_reason": "claim: invalid conclusion_type",
                "note": "self-repair of this worker's own terminally rejected claim",
            }
            ev.append(fixed)
            break

    written = 0
    batch = []
    with OUTBOX.open("a") as f:
        for e in ev:
            if e["event_id"] in existing:
                continue
            f.write(json.dumps(e, sort_keys=True) + "\n")
            batch.append(e)
            written += 1

    print(f"emitted {written} new events ({len(ev) - written} already present) -> {OUTBOX}")

    # Self-application control, precise: the events THIS script just wrote must all pass.
    # The whole-outbox scan is reported for information only — it still contains the
    # historical w056-20260912T0100-claim, which is terminally in the seen set and is
    # kept deliberately as the provenance record of the defect being repaired here.
    batch_file = HERE / "raw" / "last_emitted.jsonl"
    batch_file.write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in batch))
    if not batch:
        print("preflight(this batch): nothing new emitted — idempotent re-run, nothing to check")
        return 0
    rb = subprocess.run([sys.executable, str(HERE / "preflight_event.py"), str(batch_file)],
                        capture_output=True, text=True)
    rb_tail = [l for l in rb.stdout.splitlines() if l.startswith("checked=")]
    print("preflight(this batch):", rb_tail[-1] if rb_tail else rb.stdout.strip()[-300:])

    r = subprocess.run([sys.executable, str(HERE / "preflight_event.py"), str(OUTBOX)],
                       capture_output=True, text=True)
    r_tail = [l for l in r.stdout.splitlines() if l.startswith("checked=")]
    print("preflight(whole outbox, informational):", r_tail[-1] if r_tail else "-")

    if rb.returncode != 0:
        print("FAIL: pre-flight rejected an event this script emitted", file=sys.stderr)
        print(rb.stdout[-2000:], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
