#!/usr/bin/env python3
"""Emit the W050-WCC-LOCATOR-REPAIR-01 checkpoint and outbox events.

Runs after resolution.json exists.  Re-measures every hash at emission time and
refuses to emit an event whose sha256 does not match the bytes on disk.  Every
event is validated with research_map/schemas.py before it is appended.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
sys.path.insert(0, os.path.join(ROOT, "research_map"))
from schemas import validate_event  # noqa: E402

TZ = timezone(timedelta(hours=8))
ART = "artifacts/worker-050/wcc_locator_resolution"
OUTBOX = os.path.join(ROOT, "comms/outbox/worker-050.jsonl")
STATE = os.path.join(ROOT, "runtime/state")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha(p: str) -> str:
    return sha256_file(os.path.join(ROOT, p))


now = datetime.now(TZ).replace(microsecond=0).isoformat()
stamp = now.replace(":", "").replace("-", "").replace("+", "p")

artifacts = {
    f"{ART}/resolution.json": sha(f"{ART}/resolution.json"),
    f"{ART}/fetch_evidence.json": sha(f"{ART}/fetch_evidence.json"),
    f"{ART}/resolve_wcc_locators.py": sha(f"{ART}/resolve_wcc_locators.py"),
    f"{ART}/README.md": sha(f"{ART}/README.md"),
}
inputs = {
    "ledger/citation_audit.csv": sha("ledger/citation_audit.csv"),
    "ledger/theorems.jsonl": sha("ledger/theorems.jsonl"),
    "research_map/formulation_taxonomy.yaml": sha("research_map/formulation_taxonomy.yaml"),
    "schemas/af_wcc_vacuum.yaml": sha("schemas/af_wcc_vacuum.yaml"),
}
LEDGER_SHA = inputs["ledger/citation_audit.csv"]
PIN = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
assert LEDGER_SHA == PIN, f"ledger moved: {LEDGER_SHA} != {PIN}"

res = json.load(open(os.path.join(ROOT, f"{ART}/resolution.json")))
counts = res["counts"]

base_refs = [
    f"ledger/citation_audit.csv#{LEDGER_SHA[:12]}",
    f"ledger/theorems.jsonl#{inputs['ledger/theorems.jsonl'][:12]}",
    f"{ART}/resolution.json#{artifacts[f'{ART}/resolution.json'][:12]}",
    f"{ART}/fetch_evidence.json#{artifacts[f'{ART}/fetch_evidence.json'][:12]}",
]

events = [
    {
        "event_id": f"w050-{stamp}-artifact-resolution",
        "event_type": "artifact",
        "created_at": now,
        "actor": "worker-050",
        "node_id": "L1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-LIT",
        "artifact_type": "class_bound_locator_repair_map",
        "path": f"{ART}/resolution.json",
        "sha256": artifacts[f"{ART}/resolution.json"],
        "validation_status": "unverified",
        "artifact_refs": [f"{ART}/resolution.json#sha256:{artifacts[f'{ART}/resolution.json']}"],
        "evidence_refs": base_refs,
        "summary": (
            "AF-WCC-VAC-GEN locator-resolvability repair map at frozen L1 sha 315c19145065: "
            f"{counts['rows_in_class']} class rows classified, {counts['weak_locator_rows']} have a "
            f"non-row-specific exact_locator, {counts['repair_confirmed']} proposed replacements "
            "live-fetched HTTP 200 with matching title, 0 failed."
        ),
        "falsifier": res["next_falsifier"],
        "authority_note": "decision support only; the canonical ledger is lead-owned and was not edited",
    },
    {
        "event_id": f"w050-{stamp}-artifact-fetchevidence",
        "event_type": "artifact",
        "created_at": now,
        "actor": "worker-050",
        "node_id": "L1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-LIT",
        "artifact_type": "live_fetch_evidence",
        "path": f"{ART}/fetch_evidence.json",
        "sha256": artifacts[f"{ART}/fetch_evidence.json"],
        "validation_status": "unverified",
        "artifact_refs": [f"{ART}/fetch_evidence.json#sha256:{artifacts[f'{ART}/fetch_evidence.json']}"],
        "evidence_refs": [f"ledger/citation_audit.csv#{LEDGER_SHA[:12]}"],
        "summary": (
            "7 live fetch records for the 6 weak AF-WCC-VAC-GEN locators (SRC-041 has two candidates). "
            "6 HTTP 200 with matching titles; the SRC-041 DOI candidate returned HTTP 403 at the "
            "publisher landing page and is recorded as unverified, not as repaired."
        ),
        "falsifier": "Any recorded HTTP status or title that a re-fetch at the same locator does not reproduce.",
    },
    {
        "event_id": f"w050-{stamp}-artifact-runner",
        "event_type": "artifact",
        "created_at": now,
        "actor": "worker-050",
        "node_id": "L1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-LIT",
        "artifact_type": "reproducible_runner",
        "path": f"{ART}/resolve_wcc_locators.py",
        "sha256": artifacts[f"{ART}/resolve_wcc_locators.py"],
        "validation_status": "unverified",
        "artifact_refs": [f"{ART}/resolve_wcc_locators.py#sha256:{artifacts[f'{ART}/resolve_wcc_locators.py']}"],
        "evidence_refs": [f"{ART}/README.md#sha256:{artifacts[f'{ART}/README.md']}"],
        "summary": "Deterministic classifier/assembler; pins the ledger sha256 and exits 3 if the ledger moves.",
        "falsifier": "Re-run produces a different table from the same inputs, or exits 3, or the pinned hash is not the measured ledger hash.",
    },
    {
        "event_id": f"w050-{stamp}-review-l1-locators",
        "event_type": "review",
        "created_at": now,
        "actor": "worker-050",
        "reviewer": "worker-050",
        "target_id": "L1",
        "node_id": "L1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-LIT",
        "verdict": "revise",
        "score": 3.5,
        "reviewed_sha256": LEDGER_SHA,
        "artifact_sha256": artifacts[f"{ART}/resolution.json"],
        "hard_failures": [],
        "review_scope": (
            "exact_locator field resolvability for the 12 AF-WCC-VAC-GEN rows only; content, quotes, "
            "verdict and reviewer columns are out of scope"
        ),
        "findings": [
            {
                "id": "W050-B1",
                "severity": "B",
                "finding": (
                    "6 of 12 AF-WCC-VAC-GEN rows carry a non-row-specific exact_locator (5 truncated "
                    "INSPIRE API queries, 1 arXiv API search query), so the G-LIT criterion 'ledger rows "
                    "have resolvable locators' fails under the strict reading for half of this class. The "
                    "underlying works are verified: each proposed replacement returned HTTP 200 with a "
                    "matching title."
                ),
                "evidence": [
                    f"{ART}/resolution.json#{artifacts[f'{ART}/resolution.json'][:12]}",
                    f"ledger/citation_audit.csv#{LEDGER_SHA[:12]}",
                ],
                "falsifier": "A row classified weak whose exact_locator is in fact row-specific and resolvable (F2).",
            },
            {
                "id": "W050-N1",
                "severity": "N",
                "finding": (
                    "SRC-041 has an evidence_url (DOI) that cannot be machine-verified from this session "
                    "(HTTP 403 bot challenge at the publisher); the row's `url` field is the verified "
                    "candidate. The ledger should state which field is the locator of record."
                ),
                "evidence": [f"{ART}/fetch_evidence.json#{artifacts[f'{ART}/fetch_evidence.json'][:12]}"],
                "falsifier": "A fetch of the DOI landing page returning 200 with the cited record.",
            },
        ],
        "conditions": [
            "Binds only ledger/citation_audit.csv sha256 " + LEDGER_SHA + "; a ledger revision voids this verdict.",
            "Not a full-ledger verdict: 85 non-WCC rows were not classified in this pass.",
            "This is one worker verdict; it cannot move node status or a gate.",
        ],
        "artifact_refs": [f"{ART}/resolution.json#sha256:{artifacts[f'{ART}/resolution.json']}"],
        "evidence_refs": base_refs,
        "falsifier": res["next_falsifier"],
    },
    {
        "event_id": f"w050-{stamp}-status-locators",
        "event_type": "status",
        "created_at": now,
        "actor": "worker-050",
        "node_id": "L1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-LIT",
        "status": "active",
        "hours": 0.5,
        "summary": (
            "No assignment card exists in comms/inbox for worker-050. Took one bounded class-bound task, "
            "W050-WCC-LOCATOR-REPAIR-01: locator-resolvability repair map for the 12 AF-WCC-VAC-GEN rows "
            "of frozen L1 sha 315c19145065. Result: 6 direct rows, 6 weak rows, 6/6 replacements "
            "live-verified HTTP 200 with matching titles, 0 failed; verdict revise 3.5 with one B finding "
            "on locator hygiene. No ledger edit, no gate verdict, no node completion claimed."
        ),
        "artifact": f"{ART}/resolution.json",
        "artifact_refs": [f"{ART}/resolution.json#sha256:{artifacts[f'{ART}/resolution.json']}"],
        "evidence_refs": base_refs,
        "next_falsifier": res["next_falsifier"],
    },
]

for ev in events:
    validate_event(ev)
    if ev["event_type"] == "artifact":
        disk = sha(ev["path"])
        assert disk == ev["sha256"], f"hash mismatch for {ev['path']}: {disk} != {ev['sha256']}"

with open(OUTBOX, "a") as fh:
    for ev in events:
        fh.write(json.dumps(ev, ensure_ascii=False, sort_keys=True) + "\n")

checkpoint = {
    "worker": "worker-050",
    "instance": "worker-050-20260912T002403-968807",
    "task_id": "W050-WCC-LOCATOR-REPAIR-01",
    "task": "class-bound locator-resolvability repair map for AF-WCC-VAC-GEN rows of frozen L1",
    "checkpoint_at": now,
    "node_ids": ["L1"],
    "class_ids": ["AF-WCC-VAC-GEN"],
    "gate": ["G-LIT"],
    "inputs": inputs,
    "artifacts": artifacts,
    "verdict": "REPAIR_MAP_CONFIRMED_6_OF_6_WEAK_ROWS",
    "counts": counts,
    "events_emitted": [e["event_id"] for e in events],
    "falsifier": res["next_falsifier"],
    "scope_limit": res["scope_limit"],
    "no_completion_claim": (
        "worker cannot set node status done, validation_status passed, or a gate verdict; "
        "L1 and the canonical ledger remain lead-owned"
    ),
    "next_step": (
        "astra-lead-literature may merge the 6 proposed exact_locator values into the next ledger "
        "revision; re-run resolve_wcc_locators.py if the ledger hash moves"
    ),
}
cp_path = os.path.join(STATE, f"w050_checkpoint_locator_repair.json")
with open(cp_path, "w") as fh:
    json.dump(checkpoint, fh, indent=1, sort_keys=True, ensure_ascii=False)
    fh.write("\n")
with open(os.path.join(STATE, "w050_checkpoints.jsonl"), "a") as fh:
    fh.write(json.dumps(checkpoint, ensure_ascii=False, sort_keys=True) + "\n")

print("emitted", len(events), "events to", OUTBOX)
print("checkpoint", cp_path)
for e in events:
    print(" -", e["event_id"])
