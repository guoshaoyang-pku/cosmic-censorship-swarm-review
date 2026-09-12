#!/usr/bin/env python3
"""Emit the drift addendum: one claim + one checkpoint status. Validated before writing."""
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


rep = json.loads((OUT / "addendum_report.json").read_text())
base = json.loads((OUT / "report.json").read_text())
ART = [
    "artifacts/worker-066/f2b_accept_disposition/addendum.py",
    "artifacts/worker-066/f2b_accept_disposition/addendum_report.json",
    "artifacts/worker-066/f2b_accept_disposition/evidence/addendum_drift.json",
    "artifacts/worker-066/f2b_accept_disposition/evidence/addendum_controls.json",
]
h = {a: sha(a) for a in ART}
ck_id = f"w066-f2b-accept-disposition-addendum-{STAMP}"
checkpoint = {
    "checkpoint_id": ck_id,
    "task_id": rep["task_id"],
    "actor": "worker-066", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
    "created_at": NOW,
    "supersedes_referent": rep["supersedes_referent"],
    "accepts_then": rep["accepts_then"], "accepts_now": rep["accepts_now"],
    "clean_then": len(rep["clean_then"]), "clean_now": len(rep["clean_now"]),
    "drift": rep["drift"], "controls": {"n": len(rep["controls"]),
                                        "matched": sum(c["matched"] for c in rep["controls"])},
    "artifacts": h, "pins_entry": rep["pins_entry"], "pins_exit": rep["pins_exit"],
    "next_falsifier": rep["falsifier"],
}
(OUT / "CHECKPOINT_ADDENDUM.json").write_text(json.dumps(checkpoint, indent=1, sort_keys=True))
rs = ROOT / "runtime" / "state" / "w066_f2b_accept_disposition_addendum_checkpoint.json"
rs.write_text(json.dumps(checkpoint, indent=1, sort_keys=True))
ck = sha(str(rs.relative_to(ROOT)))

E = "artifacts/worker-066/f2b_accept_disposition/evidence"
AR = "artifacts/worker-066/f2b_accept_disposition/addendum_report.json"
drift = rep["drift"][0]

events = [
    {
        "event_id": f"w066-f2b-acceptdisp-{STAMP}-05-addendum-claim",
        "event_type": "claim", "created_at": NOW, "actor": "worker-066",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "node_id": "F2b", "gate": "G-FORM", "task_id": rep["task_id"],
        "conclusion_type": "formal_model",
        "statement": (
            "Addendum to W066-F2B-ACCEPT-DISPOSITION-01 (measurement, not a gate verdict): between "
            "the pin instant and the first emission, " + drift["file"] + " moved "
            + drift["sha256_at_pin"][:12] + " (" + drift["verdict_at_pin"] + ") -> "
            + drift["sha256_now"][:12] + " (" + drift["verdict_now"] + ") at the SAME bound bytes "
            + base["target"]["sha256"][:12] + ", and the rewritten verdict now files a blocking "
            "hard failure on carrier regularity.must_not_conflate[0] (line 152). The pinned copy "
            "still reproduces the original accept classification, so the base event set remains "
            "valid and bound. At both instants the clean-accept count for AF-SCC-C0-VAC-GEN is 0: "
            "4 accepts then (090, 052, 071, 072), 3 accepts now (090, 052, 071), none disposing "
            "either live normative carrier. This is direct evidence that accept verdicts on these "
            "bytes are unstable and that coverage must be assessed by disposition, not count."
        ),
        "assumptions": [
            "the base event set binds its pinned copies; this addendum does not rewrite it",
            "review files may move; a later move is a new revision to re-measure, not a falsifier of the base audit",
            "the disposition classifier is the same instrument as the base audit (22/22 controls there, 10/10 here)",
        ],
        "falsifier": rep["falsifier"],
        "evidence_refs": [
            f"{AR}#{h[AR][:12]}",
            f"{E}/addendum_drift.json#{h[f'{E}/addendum_drift.json'][:12]}",
            f"{E}/addendum_controls.json#{h[f'{E}/addendum_controls.json'][:12]}",
            "artifacts/worker-066/f2b_accept_disposition/report.json#" + sha("artifacts/worker-066/f2b_accept_disposition/report.json")[:12],
            "schemas/af_scc_c0_vacuum.yaml#" + base["target"]["sha256"][:12],
            "reviews/F2b-review-worker-072-rev29.json#" + drift["sha256_now"][:12],
        ],
        "artifact_refs": [f"{AR}#{h[AR][:12]}", f"CHECKPOINT_ADDENDUM.json#{ck}"],
    },
    {
        "event_id": f"w066-f2b-acceptdisp-{STAMP}-06-addendum-checkpoint",
        "event_type": "status", "created_at": NOW, "actor": "worker-066",
        "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN"], "gate": "G-FORM", "task_id": rep["task_id"],
        "status": "active", "hours": 0.9,
        "summary": (
            "Drift addendum checkpoint " + ck_id + ": worker-072 accept->revise at unchanged bound "
            "bytes, clean-accept count 0 at both instants, 10/10 controls, pins stable. worker-066 "
            "lifecycle complete; no canonical write, no gate or node transition."
        ),
        "evidence_refs": [
            f"runtime/state/w066_f2b_accept_disposition_addendum_checkpoint.json#{ck}",
            f"artifacts/worker-066/f2b_accept_disposition/CHECKPOINT_ADDENDUM.json#{ck}",
            f"{AR}#{h[AR][:12]}",
            "schemas/af_scc_c0_vacuum.yaml#" + base["target"]["sha256"][:12],
        ],
        "next_falsifier": rep["falsifier"],
    },
]

for e in events:
    schemas.validate_event(e)
outbox = ROOT / "comms" / "outbox" / "worker-066.jsonl"
existing = outbox.read_text() if outbox.is_file() else ""
added = [e for e in events if e["event_id"] not in existing]
with outbox.open("a") as f:
    for e in added:
        f.write(json.dumps(e, sort_keys=True) + "\n")
print(json.dumps({"checkpoint_sha256": ck[:12], "validated": len(events),
                  "appended": len(added), "ids": [e["event_id"] for e in events]}, indent=1))
