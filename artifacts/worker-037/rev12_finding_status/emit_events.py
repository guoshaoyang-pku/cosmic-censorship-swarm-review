#!/usr/bin/env python3
"""Emit W037-REV12-FINDING-STATUS-01 events to comms/outbox/worker-037.jsonl and write the
worker checkpoint. Idempotent: an event_id already present in the outbox is skipped.

Every event is validated with research_map.schemas.validate_event before it is written.
Worker events cannot set node status, validation_status or a gate verdict.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ART = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms/outbox/worker-037.jsonl"
STATE = ROOT / "runtime/state"
TASK_ID = "W037-REV12-FINDING-STATUS-01"
CLASSES = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"
CLASS_LIST = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
DOES_NOT_CLAIM = [
    "G-FORM pass/fail", "G-F0 pass/fail", "node completion", "theorem", "physics result",
    "authority to edit canonical artifacts", "one of the two required independent accepts",
    "reviewer verdict", "validation_status promotion",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def short(h: str) -> str:
    return h[:12]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    args = ap.parse_args()
    root = Path(args.root).resolve()
    sys.path.insert(0, str(root))
    from research_map.schemas import validate_event  # noqa: E402

    now = _dt.datetime.now().astimezone().isoformat()
    ts = _dt.datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
    report = json.loads((ART / "report.json").read_text())

    paths = {
        "report": ART / "report.json",
        "checker": ART / "measure_findings.py",
        "readme": ART / "REPORT.md",
    }
    hashes = {k: sha256(p) for k, p in paths.items()}

    pin_refs = [f"{rel}#{short(h)}" for rel, h in report["pin_set"].items()]
    core_refs = [
        f"artifacts/worker-037/rev12_finding_status/report.json#{short(hashes['report'])}",
        f"artifacts/worker-037/rev12_finding_status/measure_findings.py#{short(hashes['checker'])}",
        f"artifacts/worker-037/rev12_finding_status/REPORT.md#{short(hashes['readme'])}",
    ] + pin_refs

    events = []

    for key, node, atype in [("report", "F1,F2a,F2b", "verification_report"),
                             ("checker", "F1,F2a,F2b", "checker"),
                             ("readme", "F1,F2a,F2b", "report")]:
        events.append({
            "event_id": f"w037-rev12-finding-status-art-{key}",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-037",
            "task_id": TASK_ID,
            "node_id": node,
            "gate": "G-FORM",
            "class_id": CLASSES,
            "artifact_type": atype,
            "path": f"artifacts/worker-037/rev12_finding_status/{paths[key].name}",
            "sha256": hashes[key],
            "validation_status": "unverified",
            "evidence_refs": core_refs,
            "falsifier": report["falsifier"],
            "does_not_claim": DOES_NOT_CLAIM,
        })

    events.append({
        "event_id": "w037-rev12-finding-status-status",
        "event_type": "status",
        "created_at": now,
        "actor": "worker-037",
        "task_id": TASK_ID,
        "node_id": "F1,F2a,F2b",
        "gate": "G-FORM",
        "class_ids": CLASS_LIST,
        "status": "active",
        "hours": 0.5,
        "summary": (
            "W037-REV12-FINDING-STATUS-01 complete as a bounded worker measurement (no inbox card existed for "
            "worker-037; all live audit-r2 blind-review slots were already dispatched to other workers, so this "
            "run re-measured the stale hard findings at the FROZEN rev28 pins). 9/9 checks pass on 48 measured "
            "files, T0==T1, 0 mismatches. W037-F1 resolved (all 8 audit-r2 cards name pins equal to measured "
            "disk bytes; F0/F1/F2a/F2b each covered twice). W037-F5a resolved (D0 is a tagged disjoint union; "
            "(s,delta) scoped to the Sobolev branch). HF090-01/02/03 repairs verified by direct measurement. "
            "W037-F5b remains live as an interpretive residual only: D0 is still a two-branch tagged union, "
            "decidable per datum and identical across the three schemas -- literal 'one decidable data class' "
            "is met, strict single-branch (s,delta,norm) is not; lead B/N disposition requested. One claim "
            "(formal_model) emitted; no review verdict on F1/F2a/F2b so the blind rounds stay uncontaminated."
        ),
        "evidence_refs": core_refs,
        "next_falsifier": report["falsifier"],
        "does_not_claim": DOES_NOT_CLAIM,
    })

    events.append({
        "event_id": "w037-rev12-finding-status-claim",
        "event_type": "claim",
        "created_at": now,
        "actor": "worker-037",
        "task_id": TASK_ID,
        "node_id": "F1,F2a,F2b",
        "gate": "G-FORM",
        "class_id": CLASSES,
        "class_ids": CLASS_LIST,
        "conclusion_type": "formal_model",
        "statement": (
            "At the FROZEN rev28 pins (F1 cce9c60146d6, F2a 5476a3f2c6bc, F2b 55d0a1ea9bda, F0 0abb9ed8a961, "
            "FROZEN.json 2f358f6722d9), six previously-open hard findings re-measure as follows: W037-F1 (stale "
            "review pins) resolved -- all 8 live audit-r2 cards name pins that equal measured disk bytes, each "
            "of F0/F1/F2a/F2b covered by two; W037-F5a (an (s,delta) pair bound over a disjunctive D0) resolved "
            "-- D0 is a tagged disjoint union with the pair scoped to 'r = (sobolev,s,delta) with s > 5/2 and "
            "delta in (1/2,1)'; HF090-01 (class_contract_pointer fragment) resolved -- all three pointers "
            "resolve in the canonical taxonomy; HF090-02 (duplicate/future revised_at) resolved -- exactly one "
            "top-level revised_at per schema, not after mtime, no future timestamps; HF090-03 (AF_{I+} "
            "undefined) resolved -- defined at i_plus.predicate_abbreviation line 193 and covering the "
            "statement_formal use; W037-F5b live as an interpretive residual -- the data domain is a two-branch "
            "tagged union, decidable per datum and recorded identically across F1/F2a/F2b, so the literal 'one "
            "decidable data class' criterion is met while the strict single-branch (s,delta,norm) reading is "
            "not. This is verification evidence only: it is not a gate verdict and does not move G-FORM."
        ),
        "assumptions": [
            "The five canonical pins are exactly the FROZEN rev28 bytes measured at T0 and unchanged at T1.",
            "The live audit-r2 cards are assignment events with event_id prefix 'audit-r2-' in "
            "comms/inbox/worker-{015,035,041,046,052,071,085,091}.jsonl.",
            "A pin 'resolves' iff its 64-hex value equals a measured file hash at T0; resolution does not "
            "assert that the card's review was performed or is correct.",
            "The 'one decidable data class' criterion is read as written in the assignment cards; the strict "
            "(s,delta,norm) single-branch reading is flagged for the lead, not adjudicated here.",
            "No canonical artifact was edited; all measurement is read-only.",
        ],
        "falsifier": report["falsifier"],
        "evidence_refs": core_refs,
        "artifact_refs": [
            f"artifacts/worker-037/rev12_finding_status/report.json#{short(hashes['report'])}",
            f"artifacts/worker-037/rev12_finding_status/measure_findings.py#{short(hashes['checker'])}",
            f"artifacts/worker-037/rev12_finding_status/REPORT.md#{short(hashes['readme'])}",
        ],
        "does_not_claim": DOES_NOT_CLAIM,
    })

    for e in events:
        validate_event(e)

    outbox = root / "comms/outbox/worker-037.jsonl"
    existing = set()
    if outbox.exists():
        for line in outbox.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                continue
    written, skipped = [], []
    with open(outbox, "a") as f:
        for e in events:
            if e["event_id"] in existing:
                skipped.append(e["event_id"])
                continue
            f.write(json.dumps(e, sort_keys=True) + "\n")
            written.append(e["event_id"])

    if not written:
        print(json.dumps({"outbox": str(outbox.relative_to(root)), "written": [], "skipped": skipped,
                          "checkpoint": None, "note": "idempotent no-op; all events already present",
                          "hashes": hashes}, indent=1))
        return 0

    checkpoint = {
        "checkpoint_id": f"w037-rev12-finding-status-ckpt-{ts}",
        "actor": "worker-037",
        "task_id": TASK_ID,
        "created_at": now,
        "hours": 0.5,
        "gate": "G-FORM",
        "node_id": "F1,F2a,F2b",
        "class_ids": CLASS_LIST,
        "authority_note": "worker-level progress record only; not a gate verdict, not node completion, "
                          "not one of the two required independent accepts",
        "canonical_edits": "none - read-only on every measured path",
        "pins": report["pin_set"],
        "frozen_revision": report["frozen_revision"],
        "checks_total": report["checks_total"],
        "checks_failed": report["checks_failed"],
        "drift_stable": report["drift"]["stable"],
        "files_measured": len(report["drift"]["T0"]),
        "finding_status": report["finding_status"],
        "observations": report["observations"],
        "selftest": report["selftest"],
        "outputs": {f"artifacts/worker-037/rev12_finding_status/{p.name}": hashes[k] for k, p in paths.items()},
        "events_emitted": written,
        "events_skipped_idempotent": skipped,
        "next_falsifier": report["falsifier"],
    }
    ckpt_path = root / "runtime/state" / f"w037_checkpoint_{ts}_rev12_finding_status.json"
    ckpt_path.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
    with open(root / "runtime/state/w037_checkpoints.jsonl", "a") as f:
        f.write(json.dumps({"checkpoint_id": checkpoint["checkpoint_id"], "created_at": now,
                            "task_id": TASK_ID, "checks_failed": report["checks_failed"],
                            "path": str(ckpt_path.relative_to(root))}, sort_keys=True) + "\n")

    print(json.dumps({"outbox": str(outbox.relative_to(root)), "written": written, "skipped": skipped,
                      "checkpoint": str(ckpt_path.relative_to(root)), "hashes": hashes}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
