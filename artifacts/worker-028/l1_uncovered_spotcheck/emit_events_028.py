#!/usr/bin/env python3
"""Emit worker-028 outbox events + checkpoint for L1 uncovered-row spot check #6.

Fail-closed: every hash is re-measured from disk before anything is emitted; the
ledger must still hash to the frozen pin and the artifact must record a stable
run. Appends three protocol events (artifact, status, review) to
comms/outbox/worker-028.jsonl and writes the worker checkpoint to
runtime/state/. No gate verdict, no node completion, no validation_status=passed.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PIN = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
FREEZE_SHA = "219d1d64b2fd2e4390b22bfff43047b73572e81f6e9c621ba528bcbd1accf4fe"
CENSUS_SHA = "77b0f1ed19c373727a14d3b44cdfea7dd8cab79714048acd0650a5e6245675ec"
ART = ROOT / "artifacts/worker-028/l1_uncovered_spotcheck/uncovered_spotcheck_028.json"
RUNNER = ROOT / "artifacts/worker-028/l1_uncovered_spotcheck/run_uncovered_spotcheck_028.py"
FREEZE = ROOT / "artifacts/worker-028/l1_uncovered_spotcheck/sample_freeze_028.json"
CENSUS = ROOT / "artifacts/worker-028/l1_independence_census/independence_census.json"
REV2 = ROOT / "artifacts/literature/reviews/L1-spotcheck-rev2.json"
LEDGER = ROOT / "ledger/citation_audit.csv"
OUTBOX = ROOT / "comms/outbox/worker-028.jsonl"
CKPT = ROOT / "runtime/state/w028_l1uncovered_checkpoint_1.json"
CKPT_LOG = ROOT / "runtime/state/w028_l1uncovered_checkpoints.jsonl"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN",
             "AF-WCC-SCALAR-SPH"]
CST = timezone(timedelta(hours=8))


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ts = datetime.now(CST).isoformat(timespec="seconds")
    tag = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    ledger_sha = sha(LEDGER)
    art_sha = sha(ART)
    run_sha = sha(RUNNER)
    freeze_sha = sha(FREEZE)
    census_sha = sha(CENSUS)
    rev2_sha = sha(REV2)
    art = json.loads(ART.read_text(encoding="utf-8"))
    failures = []
    if ledger_sha != PIN:
        failures.append(f"ledger drift: {ledger_sha} != {PIN}")
    if freeze_sha != FREEZE_SHA:
        failures.append("freeze hash drift")
    if census_sha != CENSUS_SHA:
        failures.append("census hash drift")
    if art.get("inputs", {}).get("ledger/citation_audit.csv", {}).get("stable_during_run") is not True:
        failures.append("artifact records an unstable ledger run")
    if art.get("hard_failures"):
        failures.append(f"artifact carries hard failures: {art['hard_failures']}")
    if failures:
        print(json.dumps({"abort": "refusing to emit", "failures": failures}, indent=1),
              file=sys.stderr)
        return 2

    ev_art = f"w28-l1unc-art-{tag}"
    ev_status = f"w28-l1unc-status-{tag}"
    ev_review = f"w28-l1unc-review-{tag}"
    refs = [
        f"artifacts/worker-028/l1_uncovered_spotcheck/uncovered_spotcheck_028.json#{art_sha[:12]}",
        f"artifacts/worker-028/l1_uncovered_spotcheck/run_uncovered_spotcheck_028.py#{run_sha[:12]}",
        f"artifacts/worker-028/l1_uncovered_spotcheck/sample_freeze_028.json#{freeze_sha[:12]}",
        f"artifacts/worker-028/l1_independence_census/independence_census.json#{census_sha[:12]}",
        f"artifacts/literature/reviews/L1-spotcheck-rev2.json#{rev2_sha[:12]}",
        f"ledger/citation_audit.csv#{ledger_sha[:12]}",
    ]
    summary_short = (
        "Independent L1 re-fetch spot check #6 (worker-028): the 9 ledger rows no hash-bound "
        "check at ledger sha 315c19145065 had ever sampled, pre-frozen in "
        "sample_freeze_028.json before any fetch. 9/9 fetched live (arXiv/Crossref/INSPIRE): "
        "4 MATCH, 5 PARTIAL, 0 MISMATCH, 0 FETCH_FAILED; sampled union is now 97/97 rows. "
        "Census falsifier #2 is recorded: artifacts/literature/reviews/L1-spotcheck-rev2.json "
        "was not enumerated and covers row 59 (independent subagent, pass), so the corrected "
        "prior union was 88 rows with 9 uncovered, not 87/10.")
    falsifier = (
        "Re-running run_uncovered_spotcheck_028.py against a different ledger sha unbinds every "
        "row; a fetched primary source contradicting a MATCH row falsifies that row; the census "
        "correction is falsified if L1-spotcheck-rev2.json is shown not to bind 315c19145065 or "
        "not to cover SRC-059; PARTIAL rows (SRC-060/068/076/087/088) are not cleared until a "
        "source carrying the quoted text is checked.")

    events = [
        {
            "actor": "worker-028",
            "artifact_type": "l1_refetch_spotcheck",
            "class_ids": CLASS_IDS,
            "created_at": ts,
            "event_id": ev_art,
            "event_type": "artifact",
            "evidence_refs": refs,
            "falsifier": falsifier,
            "gate": "G-LIT",
            "node_id": "L1",
            "non_claims": [
                "spot check on 9 residual rows; not a ledger-wide verdict",
                "no gate verdict or node completion is set by this worker",
                "the census correction measures enumeration completeness, not citation truth",
            ],
            "path": "artifacts/worker-028/l1_uncovered_spotcheck/uncovered_spotcheck_028.json",
            "sha256": art_sha,
            "summary": summary_short,
            "validation_status": "unverified",
        },
        {
            "actor": "worker-028",
            "class_ids": CLASS_IDS,
            "created_at": ts,
            "event_id": ev_status,
            "event_type": "status",
            "evidence_refs": refs,
            "gate": "G-LIT",
            "hours": 0.5,
            "next_falsifier": (
                "Countersign or refute by re-running the runner at the pinned ledger sha; "
                "clear SRC-060 with a source carrying the quoted text; re-run the census "
                "enumeration over the full artifacts tree (not only l1_spotcheck/ shapes)."),
            "node_id": "L1",
            "outcome": {
                "FETCH_FAILED": 0,
                "MATCH": 4,
                "MISMATCH": 0,
                "PARTIAL": 5,
                "residual_rows": 9,
                "union_rows_sampled_after_this_check": 97,
                "union_rows_with_successful_fetch": 97,
            },
            "status": "active",
            "summary": (
                "Bounded worker task complete, awaiting lead/controller adjudication: L1 residual "
                "coverage closed at ledger sha 315c19145065. The 9 rows never sampled by any "
                "hash-bound check are now fetched and reported; sampled union 97/97. One row "
                "(SRC-060) is metadata-only and stays PARTIAL; the census miss (row 59 covered by "
                "L1-spotcheck-rev2.json) is corrected to prior union 88/uncovered 9. No "
                "validation_status=passed claimed."),
        },
        {
            "actor": "worker-028",
            "artifact_sha256": art_sha,
            "created_at": ts,
            "event_id": ev_review,
            "event_type": "review",
            "evidence_refs": refs,
            "findings": [
                "9 residual rows re-fetched live and compared: 4 MATCH, 5 PARTIAL, 0 MISMATCH, "
                "0 FETCH_FAILED; sampled union at ledger sha 315c19145065 is now 97/97 rows "
                "(prior union 88 after the census correction below).",
                "PARTIAL breakdown: SRC-060 fetched only as Crossref metadata (no abstract), so "
                "its excerpt is not content-verifiable; SRC-068/SRC-087/SRC-088 excerpts are "
                "truncated record-style descriptors and SRC-076's is a repository blurb, so each "
                "only approximately matches the fetched abstract (partial, not match).",
                "SRC-079 (arXiv:2606.27658, ledger year 2026) resolved live with matching "
                "title/author/year/excerpt, so the newest-looking row is not a dangling id.",
                "SRC-076 ledger fetched_at 2026-09-12T00:45 is future-dated relative to the run "
                "time (clock-discipline finding in the CF-14 class) and its evidence_excerpt "
                "opens 'Lehigh University abstract:', a third-party repository blurb.",
                "Census correction: artifacts/literature/reviews/L1-spotcheck-rev2.json "
                "(sha256 11db40b9f1c8) binds ledger/citation_audit.csv to 315c19145065 and "
                "records SRC-059 as fetched by an independent subagent (verdict pass); the "
                "census path enumeration missed it, so corrected prior coverage is 88/97 with 9 "
                "uncovered, not 87/10.",
                "Process note for the controller: the G-LIT audit's 22-file count likewise does "
                "not enumerate artifacts/literature/reviews/L1-spotcheck-rev2.json; the "
                "independence count is unaffected (still >=3) but the coverage bookkeeping is.",
                "Self-review limitation: reviewer and spot checker are the same actor; this is a "
                "measurement of the sample, not an independent second verdict. Recommend "
                "lead-literature or lead-audit countersign before citing as gate evidence.",
            ],
            "gate": "G-LIT",
            "hard_failures": [],
            "node_id": "L1",
            "reviewer": "worker-028",
            "score": 4,
            "target_id": ("artifacts/worker-028/l1_uncovered_spotcheck/"
                          f"uncovered_spotcheck_028.json#{art_sha[:12]}"),
            "verdict": "accept",
        },
    ]

    with open(OUTBOX, "a", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    checkpoint = {
        "assignment": ("self-selected (no worker-028 inbox assignment): G-LIT/L1 recorded 10 "
                       "ledger rows never sampled by any re-fetch spot check at sha "
                       "315c19145065; the controller per-file count does not measure coverage"),
        "at": ts,
        "authority": ("no gate verdict, no node completion, no validation_status=passed; "
                      "lead/controller adjudicate"),
        "checkpoint": 1,
        "class_ids": CLASS_IDS,
        "controls": ("PASS: freeze hash, ledger pin before/after, census + rev2 pins, "
                     "citation_id->row map, census union recompute, missed-row set exactly "
                     "{59}, corrected uncovered == frozen sample; comparator negative control "
                     "reached MISMATCH"),
        "delta": ("closed the last sampled-coverage gap of L1: 9 residual rows re-fetched live "
                  "(4 MATCH, 5 PARTIAL, 0 MISMATCH, 0 FETCH_FAILED), sampled union 97/97; "
                  "recorded that census falsifier #2 fired (L1-spotcheck-rev2.json missed, "
                  "row 59 covered) giving corrected prior coverage 88/97"),
        "falsifiers": [
            "ledger/citation_audit.csv no longer hashes to 315c19145065 (all bindings void);",
            "a fetched primary source contradicting a MATCH row falsifies that row;",
            "the census correction is void if L1-spotcheck-rev2.json does not bind the pin or "
            "does not cover SRC-059;",
            "PARTIAL rows SRC-060/068/076/087/088 are uncleared until a source carrying the "
            "quoted text is checked.",
        ],
        "gate": "G-LIT",
        "hours_spent_estimate": 0.5,
        "next": [
            "lead-literature: clear SRC-060 with a source carrying the quoted text (Crossref "
            "carries no abstract); decide whether record-style excerpts are acceptable as "
            "evidence for SRC-068/076/087/088",
            "controller: extend the l1_spotchecks() enumeration beyond worker l1_spotcheck/ "
            "shapes (artifacts/literature/reviews/ was missed)",
            "lead-literature / astra-lead-audit: countersign the census correction before it is "
            "cited as gate evidence (self-authored review)",
        ],
        "node_id": "L1",
        "not_claimed": [
            "No gate verdict; this is a bounded re-fetch sample plus an enumeration correction.",
            "No gate-wide coverage claim beyond ledger/citation_audit.csv at the frozen sha.",
            "class_mapping topical consistency is not a class-binding verdict.",
        ],
        "numerics_lock": "respected: no N1 work, no numerics/spherical_solver/",
        "outbox_events": [ev_art, ev_status, ev_review],
        "pins": {
            "artifacts/literature/reviews/L1-spotcheck-rev2.json": rev2_sha,
            "artifacts/worker-028/l1_independence_census/independence_census.json": census_sha,
            "artifacts/worker-028/l1_uncovered_spotcheck/run_uncovered_spotcheck_028.py": run_sha,
            "artifacts/worker-028/l1_uncovered_spotcheck/sample_freeze_028.json": freeze_sha,
            "artifacts/worker-028/l1_uncovered_spotcheck/uncovered_spotcheck_028.json": art_sha,
            "ledger/citation_audit.csv": ledger_sha,
        },
        "results": {
            "FETCH_FAILED": 0,
            "MATCH": 4,
            "MISMATCH": 0,
            "PARTIAL": 5,
            "census_corrected_prior_union": 88,
            "census_missed_rows": [59],
            "residual_rows_sampled_here": 9,
            "union_rows_sampled_after_this_check": 97,
            "union_rows_with_successful_fetch": 97,
        },
        "worker": "worker-028",
    }
    CKPT.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    with open(CKPT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(checkpoint, sort_keys=True) + "\n")
    print(json.dumps({"events": [ev_art, ev_status, ev_review],
                      "outbox": str(OUTBOX.relative_to(ROOT)),
                      "checkpoint": str(CKPT.relative_to(ROOT)),
                      "artifact_sha256": art_sha,
                      "ledger_sha256": ledger_sha,
                      "runner_sha256": run_sha}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
