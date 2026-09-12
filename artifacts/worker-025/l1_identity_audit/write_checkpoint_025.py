#!/usr/bin/env python3
"""Write the W025-L1-IDENTITY-AUDIT-01 worker checkpoint (append-only, idempotent).

Worker-scoped only: writes runtime/state/w025_l1id_checkpoint_<stamp>.json and
appends one line to runtime/state/w025_l1id_checkpoints.jsonl. Does NOT run the
global controller checkpoint (that ingests every outbox and is not a worker action).
"""
import hashlib
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
STATE = os.path.join(ROOT, "runtime", "state")
BASE = "artifacts/worker-025/l1_identity_audit"
STAMP = "20260912T012800"
CKPT_ID = "w025-l1id-ckpt-" + STAMP


def sha(rel):
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


ARTIFACTS = [
    BASE + "/PREREGISTRATION.json",
    BASE + "/report.json",
    BASE + "/cache_manifest.json",
    BASE + "/run_identity_audit_025.py",
    BASE + "/README.md",
    BASE + "/emit_events_025.py",
    "reviews/L1-identity-audit-025.json",
]

events = []
with open(os.path.join(ROOT, "comms", "outbox", "worker-025.jsonl"), "r", encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if line:
            d = json.loads(line)
            if d.get("event_id", "").startswith("w025-l1id-"):
                events.append(d["event_id"])

record = {
    "checkpoint_id": CKPT_ID,
    "task_id": "W025-L1-IDENTITY-AUDIT-01",
    "worker": "worker-025",
    "slot": "025",
    "instance_id": "worker-025-20260912T010356-968807",
    "created_at": "2026-09-12T01:28:00+08:00",
    "assignment": "self-selected bounded class-bound task (no inbox card for worker-025): full-population identifier->record identity census for L1 at the frozen ledger hash",
    "node_id": "L1",
    "gate": "G-LIT",
    "class_ids": [
        "AF-WCC-VAC-GEN",
        "AF-SCC-C2-VAC-GEN",
        "AF-SCC-C0-VAC-GEN",
        "AF-WCC-SCALAR-SPH",
    ],
    "target_sha256_measured": sha("ledger/citation_audit.csv"),
    "ledger_sha256_measured": sha("ledger/theorems.jsonl"),
    "map_sha256_measured": sha("research_map/research_map.json"),
    "artifacts": {rel: sha(rel) for rel in ARTIFACTS},
    "report_sha256": sha(BASE + "/report.json"),
    "mode": "offline_replay",
    "result": "IDENTITY_CENSUS_CLEAN: 97/97 rows audited; 95/97 resolve at least one identifier, 59/59 dual-identifier rows resolve both channels title-compatibly; 77 clean IDENTITY_MATCH, 18 IDENTITY_MATCH_WITH_AUTHOR_YEAR_FLAG (all preprint/journal year offsets, 0 author flags), 2 NO_IDENTIFIER (INSPIRE-only, both resolve), 0 identity mismatches, 0 declared-title mismatches, 0 fetch failures. 66 DOIs at Crossref, 26 at DataCite (25 arXiv 10.48550/*, 1 thesis DOI). 10 duplicate-identifier groups. No rubric HF established; no gate or node verdict claimed; no live file written.",
    "checks": "outbox 47/47 lines schema-valid (repo validate_map.validate_events, 0 errors); 7/7 artifact hashes verified on disk; report.json byte-identical across a cache-complete fetch run and two offline replays (sha256 5bd6b3263fea)",
    "falsifier": "Re-run python3 artifacts/worker-025/l1_identity_audit/run_identity_audit_025.py --offline on the shipped 114-body cache: falsified if report.json does not re-measure to sha256 5bd6b3263feaf9ff497a1c96c2afb269e9c7cad088d1c377e1b016d1d4f3603b, if any row verdict differs, if any cached DOI/arXiv body pair for a row reported clean is shown to be two different works, or if a row reported clean has a cached record contradicting the declared authors at surname level.",
    "next_falsifier": "Owner locator-policy decision for the 2 INSPIRE-only rows and dedup decision for the 10 duplicate-identifier groups; or re-run the offline replay and obtain a different report hash or census.",
    "outbox_event_ids": sorted(events),
    "non_claims": [
        "Does not endorse evidence excerpts; worker-099's SRC-025 FAIL stands separately.",
        "Does not supersede W025-L1-LOCATOR-ADJ-01 (71/97 exact_locator values are not record locators).",
        "Does not set validation_status, status=done, or any gate verdict.",
    ],
}

blob = json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
path = os.path.join(STATE, "w025_l1id_checkpoint_%s.json" % STAMP)
with open(path, "w", encoding="utf-8") as fh:
    fh.write(blob)
print("wrote", path, "sha256", hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12])

log = os.path.join(STATE, "w025_l1id_checkpoints.jsonl")
already = set()
if os.path.exists(log):
    with open(log, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                already.add(json.loads(line)["checkpoint_id"])
if CKPT_ID in already:
    print("checkpoint already logged, not duplicating:", CKPT_ID)
else:
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
    print("appended to", log)
