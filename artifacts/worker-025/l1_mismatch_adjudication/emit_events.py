#!/usr/bin/env python3
"""Phase 3: checkpoint + upward events for W025-L1-MISMATCH-ADJ-01.

Writes:
  runtime/state/w025_l1_adj_checkpoint_<ts>.json      bounded-task checkpoint
  runtime/state/w025_l1_adj_checkpoints.jsonl         append-only checkpoint log
  comms/outbox/worker-025.jsonl                       status / artifact / review / status-final

Every event is validated with research_map.schemas.validate_event before it is appended.
No node status=done, no validation_status=passed, no gate verdict is claimed (worker authority).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

CST = timezone(timedelta(hours=8))
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
from research_map.schemas import validate_event  # noqa: E402

OUTBOX = os.path.join(ROOT, "comms", "outbox", "worker-025.jsonl")
STATE = os.path.join(ROOT, "runtime", "state")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def h(relpath: str) -> str:
    p = os.path.join(ROOT, relpath)
    hh = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            hh.update(chunk)
    return hh.hexdigest()


def main() -> int:
    ts = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    report = json.load(open(os.path.join(HERE, "report.json"), encoding="utf-8"))
    files = {
        "report.json": "artifacts/worker-025/l1_mismatch_adjudication/report.json",
        "README.md": "artifacts/worker-025/l1_mismatch_adjudication/README.md",
        "controls.json": "artifacts/worker-025/l1_mismatch_adjudication/controls.json",
        "report.firstpass.json": "artifacts/worker-025/l1_mismatch_adjudication/report.firstpass.json",
        "frozen_inputs.json": "artifacts/worker-025/l1_mismatch_adjudication/freeze/frozen_inputs.json",
        "frozen_rows.json": "artifacts/worker-025/l1_mismatch_adjudication/freeze/frozen_rows.json",
        "adjudicate.py": "artifacts/worker-025/l1_mismatch_adjudication/adjudicate.py",
        "freeze_inputs.py": "artifacts/worker-025/l1_mismatch_adjudication/freeze_inputs.py",
        "SHA256SUMS": "artifacts/worker-025/l1_mismatch_adjudication/SHA256SUMS",
        "fetch_manifest.json": "artifacts/worker-025/l1_mismatch_adjudication/raw/fetch_manifest.json",
    }
    shas = {k: h(v) for k, v in files.items()}
    ledger_sha = report["inputs"]["ledger/citation_audit.csv"]["sha256_frozen"]
    spot4_sha = report["inputs"]["artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json"]["sha256"]
    d = lambda name: files[name] + "#" + shas[name][:12]  # noqa: E731

    evidence_refs = [
        d("report.json"), d("README.md"), d("controls.json"), d("report.firstpass.json"),
        d("frozen_inputs.json"), d("frozen_rows.json"),
        "ledger/citation_audit.csv#" + ledger_sha[:12],
        "artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json#" + spot4_sha[:12],
    ]

    status_active = {
        "event_id": f"w025-l1-adj-{ts}-status-active",
        "event_type": "status",
        "created_at": now(),
        "actor": "worker-025",
        "node_id": "L1",
        "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-LIT",
        "status": "active",
        "hours": 0.4,
        "summary": (
            "Bounded task W025-L1-MISMATCH-ADJ-01 (no inbox card for worker-025; took the open "
            "astra-life02-l1-spotcheck queue item with a distinct sampling rule). Pre-registered the "
            "frozen ledger revision " + ledger_sha[:12] + " and the four adjudicated rows before any fetch, "
            "then live-fetched the declared DOI of the three rows spot check #4 scored MISMATCH "
            "(SRC-004, SRC-025, SRC-033) plus controls. All three declared DOIs resolve to the exact "
            "works the ledger cites (title/author/year/container/volume/pages/DOI match); the MISMATCH "
            "verdicts are version-of-record false positives (arXiv preprint year vs journal year). "
            "3/3 controls discriminating and passed; ledger stable across the fetch window."
        ),
        "evidence_refs": evidence_refs,
        "next_falsifier": report["falsifier"],
        "task_id": "W025-L1-MISMATCH-ADJ-01",
        "completion_scope": "worker lifecycle only; not a node done / gate verdict",
    }

    artifact_evt = {
        "event_id": f"w025-l1-adj-{ts}-artifact",
        "event_type": "artifact",
        "created_at": now(),
        "actor": "worker-025",
        "node_id": "L1",
        "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-LIT",
        "artifact_type": "l1_doi_mismatch_adjudication",
        "path": files["report.json"],
        "sha256": shas["report.json"],
        "validation_status": "unverified",
        "supporting_artifacts": {name: {"path": files[name], "sha256": shas[name]} for name in files},
        "inputs_frozen": {
            "ledger/citation_audit.csv": ledger_sha,
            "artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json": spot4_sha,
        },
        "summary": report["answer"],
        "falsifier": report["falsifier"],
        "evidence_refs": evidence_refs,
    }

    review_evt = {
        "event_id": f"w025-l1-adj-{ts}-review-spotcheck4-mismatch",
        "event_type": "review",
        "created_at": now(),
        "actor": "worker-025",
        "node_id": "L1",
        "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-LIT",
        "target_id": "L1-spotcheck-4:verdicts[SRC-004,SRC-025,SRC-033]",
        "reviewer": "worker-025",
        "reviewer_independence": (
            "not an author of spotcheck-l1-086.json, of ledger/citation_audit.csv, or of any of the "
            "three rows; adjudication used live Crossref/arXiv fetches, not the ledger text as evidence"
        ),
        "verdict": "reject",
        "score": 2.0,
        "hard_failures": [],
        "findings": [
            "SRC-004 (AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN): declared DOI 10.4007/annals.2025.202.2.1 resolves to Annals of Mathematics 202(2) 2025 with an exact title match -> DOI_MATCH; spot check #4's MISMATCH is a version-of-record artifact (it fetched arXiv:1710.01722, submitted 2017).",
            "SRC-025 (AF-SCC-C2-VAC-GEN): declared DOI 10.1007/s00220-020-03923-w resolves to Communications in Mathematical Physics 382, 1263-1341 (2021) with an exact title match -> DOI_MATCH; spot check #4 fetched arXiv:2001.11156 v1 (2020).",
            "SRC-033 (AF-SCC-C2-VAC-GEN): declared DOI 10.1088/1361-6382/aadbcf resolves to Classical and Quantum Gravity 35(19), 195010 (2018) with an exact title match -> DOI_MATCH; spot check #4's MISMATCH came from an excerpt/quote comparison against the Crossref record, not from work identity.",
            "Controls: mutated SRC-004 DOI resolved to a different article and was rejected; synthetic wrong title was rejected; the positive control row (SRC-001) matched. The comparator discriminates.",
            "The spot check itself (live re-fetch, raw bodies, frozen ledger sha) remains a valid independent L1 check; only these three dispositions are rejected. The locator-quality findings it made (SRC-009/016/017/033 exact_locator are search queries) are untouched and still open.",
            "Disposition sought: literature lead re-dispositions the three rows away from hard-failure; remaining G-LIT blockers are L0 acceptance and locator quality, not these rows.",
        ],
        "evidence_refs": evidence_refs,
        "artifact_refs": [files["report.json"], files["controls.json"], files["report.firstpass.json"]],
        "falsifier": report["falsifier"],
        "non_claims": [
            "metadata identity only; theorem-to-class scope binding for the dependent rows is not verified here",
            "no gate verdict, no node status, no ledger write",
        ],
    }

    status_final = {
        "event_id": f"w025-l1-adj-{ts}-status-final",
        "event_type": "status",
        "created_at": now(),
        "actor": "worker-025",
        "node_id": "L1",
        "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-LIT",
        "status": "active",
        "hours": 0.5,
        "summary": (
            "W025-L1-MISMATCH-ADJ-01 complete and bounded. Deliverable: DOI-side adjudication of the "
            "three MISMATCH hard failures in L1 spot check #4; all three refuted at metadata level "
            "(DOI_MATCH), controls passed, ledger stable at " + ledger_sha[:12] + ". Self-caught and "
            "recorded a first-pass comparator false positive (Greek Lambda vs 'Lambda') in "
            "report.firstpass.json. Checkpoint: runtime/state/w025_l1_adj_checkpoint_" + ts + ".json. "
            "No node done, no validation passed, no gate verdict; exiting for recycling."
        ),
        "evidence_refs": evidence_refs,
        "next_falsifier": report["falsifier"],
        "task_id": "W025-L1-MISMATCH-ADJ-01",
        "completion_scope": "worker lifecycle only; this event is a completion claim, not a node done / gate verdict (per Astra notice 23:23, item 5)",
    }

    events = [status_active, artifact_evt, review_evt, status_final]
    for e in events:
        validate_event(e)

    checkpoint = {
        "worker": "worker-025",
        "checkpoint_at": now(),
        "task_id": "W025-L1-MISMATCH-ADJ-01",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "verdict": "MISMATCH_VERDICTS_REFUTED",
        "status": report["status"],
        "ledger_sha256_frozen": ledger_sha,
        "ledger_sha256_after_fetches": report["inputs"]["ledger/citation_audit.csv"]["sha256_after_fetches"],
        "spot4_artifact_sha256": spot4_sha,
        "artifacts": {files[name]: shas[name] for name in files},
        "per_row": {cid: {"verdict": report["results"][cid]["verdict"],
                          "adjudication": report["answer"][cid]} for cid in ["SRC-004", "SRC-025", "SRC-033"]},
        "controls_passed": report["all_controls_passed"],
        "events_emitted": [e["event_id"] for e in events],
        "next_falsifier": report["falsifier"],
        "non_claims": report["limitations"],
    }
    ck_path = os.path.join(STATE, f"w025_l1_adj_checkpoint_{ts}.json")
    with open(ck_path, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=1, sort_keys=True)
        f.write("\n")
    with open(os.path.join(STATE, "w025_l1_adj_checkpoints.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(checkpoint, sort_keys=True) + "\n")

    with open(OUTBOX, "a", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    print(json.dumps({
        "checkpoint": os.path.relpath(ck_path, ROOT),
        "outbox": os.path.relpath(OUTBOX, ROOT),
        "events": [e["event_id"] for e in events],
        "all_validated": True,
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
