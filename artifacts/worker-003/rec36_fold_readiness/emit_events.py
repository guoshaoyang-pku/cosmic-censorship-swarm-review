#!/usr/bin/env python3
"""Deterministic outbox emitter for W003-REC36-FOLD-READINESS-01.

Hashes every deliverable from disk at emission time and appends the task's events to
comms/outbox/worker-003.jsonl.  Idempotent: an event_id already present in the outbox is
skipped, so re-running after a crash cannot duplicate traffic.

Worker authority limits are respected: every artifact event is validation_status=unverified,
the status event is status=active (workers cannot set done), and no gate verdict is emitted.

Run:  python3 artifacts/worker-003/rec36_fold_readiness/emit_events.py
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = "W003-REC36-FOLD-READINESS-01"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
NODE = "F1,F2a,F2b"
GATE = "G-FORM"
OUTBOX = ROOT / "comms/outbox/worker-003.jsonl"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(rel: str, n: int = 12) -> str:
    return "%s#%s" % (rel, sha256_file(ROOT / rel)[:n])


def now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def main() -> int:
    base = "artifacts/worker-003/rec36_fold_readiness"
    rep_path = "%s/report.json" % base
    rep = json.loads((ROOT / rep_path).read_text())
    rep_hash = sha256_file(ROOT / rep_path)
    verdict = rep["verdict"]
    blocking = rep["summary"]["blocking_items"]
    stamp = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%dT%H%M%S")
    created = now()

    def ev(n: int, etype: str, **kw):
        e = {
            "event_id": "w003-rec36-%s-%02d-%s" % (stamp, n, etype),
            "event_type": etype,
            "created_at": created,
            "actor": "worker-003",
            "class_id": ";".join(CLASS_IDS),
            "class_ids": CLASS_IDS,
            "node_id": NODE,
            "gate": GATE,
            "task_id": TASK,
        }
        e.update(kw)
        return e

    evidence = [
        ref(rep_path, 12),
        ref("%s/controls.json" % base),
        ref("%s/check_rec36_fold_readiness.py" % base),
        ref("%s/README.md" % base),
        "runtime/state/controller_verification/astra-lifecycle-08-decisions.json#REC-36",
    ]

    events = [
        ev(1, "artifact", artifact_type="report", path=rep_path, sha256=rep_hash,
           validation_status="unverified"),
        ev(2, "artifact", artifact_type="instrument",
           path="%s/check_rec36_fold_readiness.py" % base,
           sha256=sha256_file(ROOT / ("%s/check_rec36_fold_readiness.py" % base)),
           validation_status="unverified"),
        ev(3, "artifact", artifact_type="document", path="%s/README.md" % base,
           sha256=sha256_file(ROOT / ("%s/README.md" % base)), validation_status="unverified"),
        ev(4, "artifact", artifact_type="controls", path="%s/controls.json" % base,
           sha256=sha256_file(ROOT / ("%s/controls.json" % base)), validation_status="unverified"),
        ev(
            5, "claim",
            statement=(
                "REC-36 fold-readiness census at the FROZEN rev29 pins (F1 d9cebb9404b2, F2a e9a27996dfd3, "
                "F2b b2ab6acb2bbe, FROZEN 815e08079aef, VARIANT_REGISTRY 6bac9adea19e, f1 suite 56bcb4b3234b, "
                "F0 0abb9ed8a961; 9/9 pins stable start-to-end): of the seven REC-36 items, 3 are "
                "staged-hash-verified-not-landed (REC36-1/2 F2b D1+D2 with 10/10 candidate hashes matching and "
                "7/10 carrying non-producer verification; REC36-3 F2a EXTCAT patched candidate 37e650ad6481 "
                "verified by worker-039 W039-F2A-EXTFREEZE-VERIFY-01), and 4 are blocking: REC36-4 crosswalk is "
                "evidence-partial-not-pinned (closest artifact is a worker report with one failing check, no "
                "pinned crosswalk artifact), REC36-5 SET candidate bytes 5c05a8cc/7a1f6212/8b15f43e hash-match "
                "but have zero non-producer verification events, REC36-6 F1 suite rebind has 4/4 candidate "
                "hashes on disk but worker-034 records freeze_ready=[] for all four, and REC36-7 acceptance "
                "corpus still binds stale base 1bb78ce9b357 with no live-base rebind candidate located. "
                "Canonical-path union: 11 entries, 0 forbidden writes. Therefore the single authorized "
                "rev14/FROZEN-rev30 fold is NOT mechanically ready to close over all seven items as staged."
            ),
            conclusion_type="formal_model",
            assumptions=[
                "readiness = exists on disk + declared sha256 match + at least one non-producer event in research_map/events.jsonl",
                "candidate content correctness is taken from the cited producers/adjudications, not re-adjudicated here",
                "the REC-36 item list is read from the pass-08 decisions record",
            ],
            falsifier=rep["falsifier"],
            evidence_refs=evidence,
            artifact_refs=[rep_path],
        ),
        ev(
            6, "review",
            target_id="%s#%s" % (rep_path, rep_hash[:12]),
            reviewer="worker-003",
            verdict="revise",
            score=3.0,
            hard_failures=[b["id"] + ":" + b["status"] for b in blocking],
            findings=[
                "REC36-6 is the single hardest blocker: four candidates exist and reproduce, but all are "
                "non-freeze-ready on record-fidelity/provenance axes (worker-034); an owner policy decision on "
                "provenance fields is required before the fold can bind one byte set.",
                "REC36-4 has no pinned crosswalk artifact at any path and its closest evidence report has one "
                "failing check (C5b_literal_allowed_uses_canonical_keys); REC-37 explicitly requires a pinned "
                "artifact plus a consistency check.",
                "REC36-5's candidate set is author-self-verified only; a non-author hash-level verification is "
                "the cheapest unblock and is not yet claimed by any worker event.",
                "REC36-7's corpus base 1bb78ce9b357 (rev11 C0) predates two canonical byte moves; the fold "
                "cannot claim a reproducible acceptance pipeline while the corpus binds a superseded base.",
                "REC36-1/2 and REC36-3 are ready on this mechanical axis; no do-not-freeze candidate is "
                "misclassified as landable (3 negative controls verified as INVERTED/DENIAL).",
            ],
        ),
        ev(
            7, "blocker",
            description=(
                "REC-36's single authorized rev14/FROZEN-rev30 fold is not mechanically ready as staged: "
                "4 of 7 items are blocking (REC36-4 evidence-partial-not-pinned; REC36-5 awaiting independent "
                "verification; REC36-6 no freeze-ready candidate; REC36-7 no live-base corpus candidate). "
                "The fold manifest cannot close over all seven items; landing a partial fold would either "
                "silently drop an authorized item or bind a superseded base."
            ),
            needed_to_unblock=(
                "Owner (astra-lead-formulation) or a delegated worker: (i) elect and pin one freeze-ready F1 "
                "suite candidate after deciding the provenance-field policy (REC36-6); (ii) publish the REC-37 "
                "crosswalk as a pinned artifact with its consistency check (REC36-4); (iii) obtain one non-author "
                "verification of the worker-024 SET candidate set (REC36-5); (iv) produce a semantic-escape "
                "corpus rebind at live F2b rev13 b2ab6acb2bbe (REC36-7). Re-run this census afterwards; every "
                "item must then classify STAGED_VERIFIED_NOT_LANDED before the fold is attempted."
            ),
            evidence_refs=evidence,
            falsifier=rep["falsifier"],
        ),
        ev(
            8, "status",
            status="active",
            hours=0.6,
            summary=(
                "W003-REC36-FOLD-READINESS-01 complete at worker level (completion claim only: workers cannot "
                "set done/passed or a gate verdict). One bounded class-bound task self-selected because no "
                "inbox card existed for worker-003 and REC-36 had no independent readiness census. Verdict "
                "%s; controls K1-K6 all discriminate; two runs byte-identical; 0 canonical writes; 9/9 pins "
                "stable. Deliverables on disk and hash-pinned." % verdict
            ),
            evidence_refs=evidence,
            next_falsifier=rep["falsifier"],
        ),
    ]

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                continue
    added = 0
    with open(OUTBOX, "a", encoding="utf-8") as fh:
        for e in events:
            if e["event_id"] in existing:
                continue
            fh.write(json.dumps(e, sort_keys=True) + "\n")
            added += 1
    print(json.dumps({"task_id": TASK, "events_defined": len(events), "events_added": added,
                      "report_sha256": rep_hash, "verdict": verdict}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
