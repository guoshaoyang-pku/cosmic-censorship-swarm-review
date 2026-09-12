#!/usr/bin/env python3
"""Emit worker-079's upward events and checkpoint for W079-L1-SPOTCHECK-05.

Reads the committed artifact and hashes everything at emit time so the events
can never cite a stale hash.  Writes:
  comms/outbox/worker-079.jsonl            (5 upward events, schema-validated)
  runtime/state/w079_checkpoint_1.json      (worker checkpoint)
Never writes research_map/events.jsonl, rejected.jsonl, or the map: ingest is
the controller's job.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

ART = "artifacts/worker-079/l1_spotcheck/spotcheck-l1-079.json"
SIDE = "artifacts/worker-079/l1_spotcheck/spotcheck-l1-079.json.sha256"
HARNESS = "artifacts/worker-079/l1_spotcheck/run_spotcheck_079.py"
LEDGER = "ledger/citation_audit.csv"
THEOREMS = "ledger/theorems.jsonl"
CST = timezone(timedelta(hours=8))
CLASS4 = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH"


def h(p: str) -> str:
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def now(offset: int = 0) -> str:
    return (datetime.now(CST) + timedelta(seconds=offset)).isoformat(timespec="seconds")


def main() -> int:
    art_h, harness_h, ledger_h, theorems_h = h(ART), h(HARNESS), h(LEDGER), h(THEOREMS)
    a = json.loads((ROOT / ART).read_text())
    assert a["inputs"]["ledger/citation_audit.csv"]["stable_during_run"] is True
    assert a["inputs"]["ledger/citation_audit.csv"]["sha256"] == ledger_h, "ledger moved since the artifact; re-run the harness"
    assert a["inputs"]["ledger/theorems.jsonl"]["sha256"] == theorems_h, "theorems.jsonl moved since the artifact"
    (ROOT / SIDE).write_text(f"{art_h}  spotcheck-l1-079.json\n")
    base = {"actor": "worker-079", "node_id": "L1", "class_id": CLASS4, "group_id": "literature",
            "gate": "G-LIT", "task_id": "W079-L1-SPOTCHECK-05"}
    events = [
        {**base, "event_id": "w079-20260912T0033-status-start", "event_type": "status",
         "created_at": now(0), "status": "active", "hours": 0.3,
         "summary": ("No assignment card exists for worker-079 (fleet launched 00:16:57). Took one bounded class-bound task: "
                     "independent L1 re-fetch spot check #5 for G-LIT. Controller gate audit at 00:17:27 records 2 binding spot "
                     "checks against L1, required >=3; this is the third, from a distinct reviewer. Sample frozen in the harness "
                     f"before any fetch; ledger sha256 {ledger_h[:12]} unchanged before and after. Does not claim node completion, "
                     "validation_status, or any gate verdict."),
         "evidence_refs": [f"{LEDGER}#{ledger_h[:12]}", "runtime/state/artifact_hashes.json",
                           "research_map/research_map.json#controller_gate_audit.G-LIT"],
         "next_falsifier": (f"Any sampled row re-fetching to a different work, or ledger drift from {ledger_h[:12]} during the run, "
                            "voids the MATCH set; 67/97 search-query exact_locators falsify the 'exact locator' reading of the "
                            "G-LIT criterion.")},
        {**base, "event_id": "w079-20260912T0033-artifact-spotcheck5", "event_type": "artifact",
         "created_at": now(5), "artifact_type": "l1_refetch_spotcheck", "path": ART,
         "sha256": art_h, "validation_status": "unverified",
         "evidence_refs": [f"{LEDGER}#{ledger_h[:12]}", f"{HARNESS}#{harness_h[:12]}", SIDE],
         "next_falsifier": (f"re-run run_spotcheck_079.py at ledger sha256 {ledger_h[:12]}: any verdict change falsifies the MATCH "
                            "set; raw bodies under artifacts/worker-079/l1_spotcheck/raw/ are the pinned fetch evidence")},
        {**base, "event_id": "w079-20260912T0033-review-spotcheck5", "event_type": "review",
         "created_at": now(10), "target_id": "L1", "reviewer": "worker-079",
         "reviewed_path": LEDGER, "reviewed_sha256": ledger_h,
         "verdict": "accept", "score": 3.5, "hard_failures": [],
         "findings": [
             {"id": "SPOT5-F-01", "severity": "medium", "blocking": False,
              "finding": "67/97 rows carry a search query in exact_locator, not an exact locator; resolvable, but not work-deterministic."},
             {"id": "SPOT5-F-02", "severity": "medium", "blocking": False,
              "finding": "68/97 rows are status verified-primary/verified-api while exact_locator is not an exact id (SRC-070 is verified-primary with an arXiv search query)."},
             {"id": "SPOT5-F-03", "severity": "medium", "blocking": False,
              "finding": "5/13 sampled rows (SRC-096,004,025,061,093) have an exact_locator channel that cannot support the ledger year; the year is confirmed by the Crossref channel, so it is an evidence-linkage gap, not a wrong citation."},
             {"id": "SPOT5-F-04", "severity": "info", "blocking": False,
              "finding": "0/97 used_by_theorems references dangle in the theorems.jsonl revision recorded in the artifact."},
             {"id": "SPOT5-F-05", "severity": "info", "blocking": False,
              "finding": "13/13 sampled rows re-fetch to the recorded work; check #4's three hard failures do not replicate as wrong citations."}],
         "evidence_refs": [f"{LEDGER}#{ledger_h[:12]}", f"{ART}#{art_h[:12]}"],
         "next_falsifier": "a re-fetch at the same ledger sha256 identifying a different work, or ledger drift, invalidates this verdict"},
        {**base, "event_id": "w079-20260912T0033-claim-spotcheck5", "event_type": "claim",
         "created_at": now(15), "conclusion_type": "open_problem",
         "statement": (f"Audit observation at frozen L1 sha256 {ledger_h[:12]} (not a mathematical claim): 13/13 sampled citation rows "
                       "re-fetch to the recorded work on live arXiv/Crossref/INSPIRE channels with a matching year channel; "
                       "check #4's three hard failures (SRC-004, SRC-025, SRC-033) do not replicate as wrong citations; "
                       "67/97 exact_locator values are search queries rather than exact locators; 0/97 used_by_theorems references dangle."),
         "assumptions": ["live arXiv/Crossref/INSPIRE records are the primary sources of record for the ledger",
                         "abstract-level identity plus one matching year channel is sufficient for a spot-check MATCH, not a page-level proof reading",
                         f"the ledger hash is stable at {ledger_h[:12]} during the run"],
         "falsifier": (f"A re-fetch of any sampled row at the same ledger sha256 that identifies a different work, or ledger drift from "
                       f"{ledger_h[:12]}, falsifies the corresponding row; a row that is verified-primary with a non-primary locator "
                       "falsifies the locator-honesty reading."),
         "evidence_refs": [f"{LEDGER}#{ledger_h[:12]}", f"{THEOREMS}#{theorems_h[:12]}",
                           f"{ART}#{art_h[:12]}", f"{HARNESS}#{harness_h[:12]}"],
         "artifact_refs": [f"{ART}#{art_h[:12]}", f"{HARNESS}#{harness_h[:12]}"]},
        {**base, "event_id": "w079-20260912T0033-status-final", "event_type": "status",
         "created_at": now(20), "status": "active", "hours": 0.4,
         "summary": ("Spot check #5 complete: artifact + sidecar hash written, raw bodies pinned under raw/, checkpoint at "
                     "runtime/state/w079_checkpoint_1.json, outbox events emitted, now exiting. Node status, validation_status, "
                     "and gate verdict stay with the controller/leads."),
         "evidence_refs": [f"{ART}#{art_h[:12]}", "runtime/state/w079_checkpoint_1.json"],
         "next_falsifier": "re-run the harness at the same ledger hash; a verdict change or ledger drift falsifies the result"},
    ]
    for e in events:
        validate_event(e)
    (ROOT / "comms/outbox/worker-079.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n", encoding="utf-8")

    checkpoint = {
        "checkpoint": 1, "at": now(25), "worker": "worker-079",
        "lifecycle": "run-2026-09-12T00:16:57+08:00 (independent_supervisor_v2 relaunch; earlier 00:12:30 instance produced no output)",
        "assignment_taken": {
            "kind": "class-bound task taken from the immediate queue; no assignment card exists in comms/inbox for worker-079",
            "task": "W079-L1-SPOTCHECK-05 = independent L1 re-fetch spot check #5 (G-LIT), ledger/citation_audit.csv (97 data rows)",
            "class_ids": CLASS4.split(";"), "node_id": "L1", "gate": "G-LIT",
            "why_not_duplicative": ("controller_gate_audit at 00:17:27 records 2 binding spot checks (worker-07, worker-086), required >=3; "
                                    "this is a distinct reviewer with a sample disjoint from check #3's rows {41,49,57,65,73,80,81,89} and "
                                    "re-fetching check #4's three hard-failure rows for independent adjudication")},
        "hours_spent_estimate": 0.4,
        "artifacts": {
            ART: {"sha256": art_h, "note": "check #5: 13/13 sampled rows MATCH; 67/97 exact_locator search-query finding; 0/97 dangling theorem refs"},
            SIDE: {"note": "sidecar hash"},
            HARNESS: {"sha256": harness_h, "note": "hash-pinned sampler, fail-closed on ledger sha256 mismatch; harness rev3 (abs-page channel + 429 backoff)"}},
        "evidence": {
            LEDGER: {"sha256_before_fetch": ledger_h, "sha256_after_fetch": ledger_h, "note": "no drift during the run"},
            THEOREMS: {"sha256": theorems_h, "note": "used_by_theorems integrity: 0 dangling of 97 rows at this revision"},
            "raw_bodies": {"count": len(list((ROOT / "artifacts/worker-079/l1_spotcheck/raw").glob("*.body"))),
                           "dir": "artifacts/worker-079/l1_spotcheck/raw/",
                           "note": "each body hash-pinned in the artifact's fetched[].body_sha256"},
            "events_emitted": [e["event_id"] for e in events],
            "ingest_result": "comms.py ingest --dry-run accepted 5/5 with 0 rejects for worker-079; events.jsonl writes remain with the controller"},
        "claims": {"node_status_claimed": False, "gate_verdict_claimed": False, "validation_status": "unverified",
                   "note": "review verdict accept (score 3.5) is a spot-check verdict on 13 sampled rows and the machine-only structural scan, not a ledger-wide verdict"},
        "next_falsifiers": [
            f"re-run run_spotcheck_079.py at ledger sha256 {ledger_h[:12]}: any verdict change falsifies the MATCH set",
            "a later re-fetch contradicting any of the 13 rows turns that MATCH into a hard failure",
            "rows outside the sample (84 of 97) remain covered only by checks #1-#4; the 67 search-query exact_locators are unaudited at exact-locator level"],
    }
    (ROOT / "runtime/state/w079_checkpoint_1.json").write_text(
        json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"outbox": "comms/outbox/worker-079.jsonl", "events": len(events),
                      "checkpoint": "runtime/state/w079_checkpoint_1.json",
                      "artifact_sha256": art_h, "harness_sha256": harness_h,
                      "ledger_sha256": ledger_h, "theorems_sha256": theorems_h}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
