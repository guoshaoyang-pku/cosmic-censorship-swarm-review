#!/usr/bin/env python3
"""Emit the correction status: restore disclosure + ref redirect. Validated before writing."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "research_map"))
import schemas  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
STAMP = datetime.now(CST).strftime("%Y%m%dT%H%M%S")


def sha(rel: str) -> str:
    h = hashlib.sha256()
    with (ROOT / rel).open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


RESTORED = {
    "artifacts/worker-066/f2b_accept_disposition/report.json": "a82623db025e8b14b266ed9c171ddfa83c63cbc66525c02894f7eaa23a175696",
    "artifacts/worker-066/f2b_accept_disposition/evidence/accepts.json": "63e18044807d61c6466b356ff68df5e700e14abc25583fd81fdef2d3803faafc",
    "artifacts/worker-066/f2b_accept_disposition/evidence/carriers.json": "a6a9352f533f9960063d2380e81415ecee78ea528c0110b970314f4072c6a1d8",
    "artifacts/worker-066/f2b_accept_disposition/evidence/checks.json": "7a18e9059b3a638ba9c5a5c1dcced1d0e50d8cc2b6dc56f756508bd763badb87",
    "artifacts/worker-066/f2b_accept_disposition/evidence/controls.json": "70d6ff0ed2ec8021a099b5bf702ab9b9f02f41c8633bc6ded1ca8cf6102a1c45",
}
verify = {rel: sha(rel) == want for rel, want in RESTORED.items()}
assert all(verify.values()), verify

CORR = {
    "checkpoint_id": f"w066-f2b-accept-disposition-correction-{STAMP}",
    "task_id": "W066-F2B-ACCEPT-DISPOSITION-01-CORRECTION",
    "actor": "worker-066", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
    "created_at": NOW,
    "what_happened": (
        "A determinism re-run of audit.py at ~01:16 overwrote report.json and evidence/*.json "
        "with the later-instant census, which broke five evidence refs of the base event set "
        "w066-f2b-acceptdisp-20260912T011504-*. The pin-instant artifacts were reconstructed in a "
        "sandbox from the pinned review copies plus the review corpus minus the three post-pin "
        "files, using the UNCHANGED audit.py, and the regeneration reproduced the cited hashes "
        "byte-exactly; those bytes are restored at the canonical paths."
    ),
    "restored_and_verified": RESTORED,
    "verification_method": "artifacts/worker-066/f2b_accept_disposition/restore_base.py "
                           "(sandbox mirror; rc=0; 5/5 hashes MATCH)",
    "superseded_ref_redirect": {
        "ref": "artifacts/worker-066/f2b_accept_disposition/report.json#03e5c2de5d42",
        "cited_by": "w066-f2b-acceptdisp-20260912T011554-05-addendum-claim",
        "successor": "artifacts/worker-066/f2b_accept_disposition/evidence/instant-011604/report.json#03e5c2de5d42",
        "note": "same bytes, preserved before restoration; the unversioned path now carries the "
                "pin-instant report (a82623db) that the base event set cites",
    },
    "state_moved_on": [
        "reviews/F2b-direction-crossverify-worker-100.json (01:15:22)",
        "reviews/F2b-remedy-crossverify-worker-100.json (01:15:29)",
        "reviews/F2b-rev30-h2-direction-053.json (01:15:56)",
        "these bind the H2 direction question at or after the pin; they are OUTSIDE this audit's "
        "instant and are not classified here",
    ],
    "invariant": "clean-accept count for AF-SCC-C0-VAC-GEN is 0 at every instant measured "
                 "(4 accepts at 01:15:04, 3 at 01:15:54)",
    "next_falsifier": "Re-run restore_base.py: falsified if any restored artifact hash differs; or "
                      "if evidence/instant-011604/report.json is not 03e5c2de; or if a base event "
                      "ref no longer resolves.",
}
(OUT / "CHECKPOINT_CORRECTION.json").write_text(json.dumps(CORR, indent=1, sort_keys=True))
rs = ROOT / "runtime" / "state" / "w066_f2b_accept_disposition_correction.json"
rs.write_text(json.dumps(CORR, indent=1, sort_keys=True))
ck = sha(str(rs.relative_to(ROOT)))

event = {
    "event_id": f"w066-f2b-acceptdisp-{STAMP}-07-correction-status",
    "event_type": "status", "created_at": NOW, "actor": "worker-066",
    "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": ["AF-SCC-C0-VAC-GEN"],
    "gate": "G-FORM", "task_id": CORR["task_id"], "status": "active", "hours": 0.95,
    "summary": (
        "Correction/disclosure: a determinism re-run overwrote the pin-instant base artifacts at "
        "~01:16, breaking five evidence refs of the base event set; the bytes were reconstructed "
        "from the pinned corpus with the unchanged instrument and restored byte-exactly (5/5 "
        "hashes verified). One addendum ref (report.json#03e5c2de) is redirected to the preserved "
        "copy at evidence/instant-011604/report.json#03e5c2de. Audit result unchanged: 0 clean "
        "accepts at every instant. Three post-pin direction reviews landed and are outside this "
        "audit's instant. No canonical write, no gate or node transition."
    ),
    "evidence_refs": [
        f"runtime/state/w066_f2b_accept_disposition_correction.json#{ck}",
        f"artifacts/worker-066/f2b_accept_disposition/CHECKPOINT_CORRECTION.json#{ck}",
        "artifacts/worker-066/f2b_accept_disposition/report.json#a82623db025e",
        "artifacts/worker-066/f2b_accept_disposition/evidence/accepts.json#63e18044807d",
        "artifacts/worker-066/f2b_accept_disposition/evidence/instant-011604/report.json#03e5c2de",
        "artifacts/worker-066/f2b_accept_disposition/restore_base.py#" + sha("artifacts/worker-066/f2b_accept_disposition/restore_base.py")[:12],
        "schemas/af_scc_c0_vacuum.yaml#" + sha("schemas/af_scc_c0_vacuum.yaml")[:12],
    ],
    "next_falsifier": CORR["next_falsifier"],
}
schemas.validate_event(event)
outbox = ROOT / "comms" / "outbox" / "worker-066.jsonl"
existing = outbox.read_text() if outbox.is_file() else ""
if event["event_id"] not in existing:
    with outbox.open("a") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")
    print("appended", event["event_id"])
else:
    print("already present", event["event_id"])
