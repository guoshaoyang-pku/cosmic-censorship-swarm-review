#!/usr/bin/env python3
"""Emit ERRATUM-01 + a status notice + checkpoint 2 for worker-028 spot check #6.

The spot-check artifact (sha 44e356c6fd3c) reports
summary.union_rows_with_successful_fetch = 97. That figure combines 9 rows this
worker fetched live with 88 prior rows whose own hash-bound checks declare a
non-FETCH_FAILED outcome; the census bound checks contain zero declared
FETCH_FAILED outcomes, but this worker did not re-fetch those 88 rows. The
measurement is unchanged and the artifact is NOT rewritten; this erratum binds
the semantics so the number cannot be read as a ledger-wide independent re-fetch.

Fail-closed: artifact, freeze, census and ledger hashes are re-measured and must
match before anything is written.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "research_map"))
from schemas import SchemaError, validate_event  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
PIN = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
ART_SHA = "44e356c6fd3ca3386edea4d9383cf6c28e2b656b1e900e62b403897f291dfa5e"
CENSUS_SHA = "77b0f1ed19c373727a14d3b44cdfea7dd8cab79714048acd0650a5e6245675ec"
ART = ROOT / "artifacts/worker-028/l1_uncovered_spotcheck/uncovered_spotcheck_028.json"
ERRATUM = ROOT / "artifacts/worker-028/l1_uncovered_spotcheck/ERRATUM-01.json"
CENSUS = ROOT / "artifacts/worker-028/l1_independence_census/independence_census.json"
LEDGER = ROOT / "ledger/citation_audit.csv"
OUTBOX = ROOT / "comms/outbox/worker-028.jsonl"
CKPT = ROOT / "runtime/state/w028_l1uncovered_checkpoint_2.json"
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
    ledger_sha, art_sha, census_sha = sha(LEDGER), sha(ART), sha(CENSUS)
    failures = []
    if ledger_sha != PIN:
        failures.append(f"ledger drift: {ledger_sha}")
    if art_sha != ART_SHA:
        failures.append(f"artifact drift: {art_sha}")
    if census_sha != CENSUS_SHA:
        failures.append(f"census drift: {census_sha}")
    if failures:
        print(json.dumps({"abort": "refusing to emit erratum", "failures": failures},
                         indent=1), file=sys.stderr)
        return 2

    ts = datetime.now(CST).isoformat(timespec="seconds")
    tag = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    census = json.loads(CENSUS.read_text(encoding="utf-8"))
    declared_failed = sorted({r for c in census["bound_checks"]
                              for k, v in (c.get("outcomes") or {}).items()
                              if "FAIL" in k.upper() for r in (c.get("rows") or [])})
    erratum = {
        "actor": "worker-028",
        "artifact_type": "l1_spotcheck_erratum",
        "class_ids": CLASS_IDS,
        "corrects": (f"artifacts/worker-028/l1_uncovered_spotcheck/"
                     f"uncovered_spotcheck_028.json#{ART_SHA[:12]}"),
        "created_at": ts,
        "erratum_number": 1,
        "evidence_refs": [
            f"artifacts/worker-028/l1_uncovered_spotcheck/uncovered_spotcheck_028.json#{ART_SHA[:12]}",
            f"artifacts/worker-028/l1_independence_census/independence_census.json#{CENSUS_SHA[:12]}",
            f"ledger/citation_audit.csv#{PIN[:12]}",
        ],
        "falsifier": ("a bound check artifact that declares FETCH_FAILED, or lacks any primary "
                      "fetch, for one of the 88 prior rows falsifies the 97 figure; the 9 rows "
                      "fetched in this run stand on their own recorded HTTP evidence."),
        "gate": "G-LIT",
        "no_artifact_rewrite": ("the spot-check artifact remains at sha 44e356c6fd3c; this "
                                "erratum adds semantics, it does not change measurements"),
        "node_id": "L1",
        "precise_semantics": {
            "census_declared_failed_rows": declared_failed,
            "meaning": ("summary.union_rows_with_successful_fetch = 97 means 9 rows fetched live "
                        "by this worker (HTTP 200 primary sources recorded in the artifact) plus "
                        "88 prior rows whose own hash-bound checks declare a non-FETCH_FAILED "
                        "outcome for them; the census bound checks contain zero declared "
                        "FETCH_FAILED outcomes"),
            "not_meaning": ("this worker did not re-fetch the 88 prior rows; 97 is not a "
                            "ledger-wide independent re-fetch count"),
        },
        "statement": ("Definition of the field summary.union_rows_with_successful_fetch in "
                      "uncovered_spotcheck_028.json: 9 independently re-fetched here + 88 taken "
                      "as declared-successful by their own hash-bound check artifacts."),
    }
    ERRATUM.write_text(json.dumps(erratum, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    erratum_sha = sha(ERRATUM)
    event = {
        "actor": "worker-028",
        "class_ids": CLASS_IDS,
        "created_at": ts,
        "erratum_ref": f"artifacts/worker-028/l1_uncovered_spotcheck/ERRATUM-01.json#{erratum_sha[:12]}",
        "event_id": f"w28-l1unc-erratum-{tag}",
        "event_type": "status",
        "evidence_refs": [
            f"artifacts/worker-028/l1_uncovered_spotcheck/ERRATUM-01.json#{erratum_sha[:12]}",
            f"artifacts/worker-028/l1_uncovered_spotcheck/uncovered_spotcheck_028.json#{ART_SHA[:12]}",
            f"ledger/citation_audit.csv#{PIN[:12]}",
        ],
        "gate": "G-LIT",
        "hours": 0.05,
        "next_falsifier": erratum["falsifier"],
        "node_id": "L1",
        "status": "active",
        "summary": ("Erratum, no measurement change: union_rows_with_successful_fetch=97 in the "
                    "spot-check artifact means 9 rows fetched live here + 88 declared-successful "
                    "by their own hash-bound checks (zero declared FETCH_FAILED); it is not a "
                    "ledger-wide independent re-fetch. Artifact stays at sha 44e356c6fd3c."),
    }
    try:
        validate_event(event)
    except SchemaError as e:
        print(json.dumps({"abort": "erratum event invalid", "reason": str(e)}, indent=1),
              file=sys.stderr)
        return 2
    with open(OUTBOX, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")

    checkpoint = {
        "assignment": ("erratum to the worker-028 L1 uncovered-row spot check #6; no new "
                       "measurement, semantic binding only"),
        "at": ts,
        "authority": ("no gate verdict, no node completion, no validation_status=passed; "
                      "lead/controller adjudicate"),
        "checkpoint": 2,
        "class_ids": CLASS_IDS,
        "controls": ("PASS: ledger pin, artifact sha 44e356c6fd3c and census sha 77b0f1ed19c3 "
                     "re-measured; zero declared FETCH_FAILED rows across the census bound "
                     "checks recomputed"),
        "delta": ("union_rows_with_successful_fetch=97 bound to its precise semantics (9 fetched "
                  "here + 88 declared); artifact unchanged; erratum event emitted"),
        "falsifiers": [erratum["falsifier"]],
        "gate": "G-LIT",
        "hours_spent_estimate": 0.05,
        "next": [
            "controller: accept the erratum as semantic binding only; no artifact re-pin needed",
            "lead-literature / astra-lead-audit: countersign the spot check and census correction",
        ],
        "node_id": "L1",
        "not_claimed": [
            "No gate verdict.",
            "No re-fetch of the 88 prior rows was performed here.",
        ],
        "numerics_lock": "respected: no N1 work, no numerics/spherical_solver/",
        "outbox_events": [event["event_id"]],
        "pins": {
            "artifacts/worker-028/l1_independence_census/independence_census.json": census_sha,
            "artifacts/worker-028/l1_uncovered_spotcheck/ERRATUM-01.json": erratum_sha,
            "artifacts/worker-028/l1_uncovered_spotcheck/uncovered_spotcheck_028.json": art_sha,
            "ledger/citation_audit.csv": ledger_sha,
        },
        "results": {
            "declared_fetch_failed_rows": declared_failed,
            "rows_fetched_here": 9,
            "rows_taken_as_declared": 88,
            "union_rows_with_successful_fetch": 97,
        },
        "worker": "worker-028",
    }
    CKPT.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    with open(CKPT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(checkpoint, sort_keys=True) + "\n")
    print(json.dumps({"erratum": str(ERRATUM.relative_to(ROOT)),
                      "erratum_sha256": erratum_sha,
                      "event_id": event["event_id"],
                      "checkpoint": str(CKPT.relative_to(ROOT))}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
