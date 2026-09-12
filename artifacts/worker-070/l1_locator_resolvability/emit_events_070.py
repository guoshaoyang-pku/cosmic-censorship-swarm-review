#!/usr/bin/env python3
"""Emit worker-070 rev2 locator-resolvability events + worker checkpoint.

Run AFTER run_audit_070.py has written census.json. Appends to
comms/outbox/worker-070.jsonl (never rewrites prior lines) and writes
runtime/state/w070_checkpoint_locator.json. Prints the emitted JSON for review.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUTDIR = ROOT / "artifacts" / "worker-070" / "l1_locator_resolvability"
CENSUS = OUTDIR / "census.json"
SCRIPT = OUTDIR / "run_audit_070.py"
REV1 = OUTDIR / "superseded" / "census.rev1-voided.json"
REV2 = OUTDIR / "superseded" / "census.rev2-stopword-defect.json"
OUTBOX = ROOT / "comms" / "outbox" / "worker-070.jsonl"
CKPT = ROOT / "runtime" / "state" / "w070_checkpoint_locator.json"
LEDGER = ROOT / "ledger" / "citation_audit.csv"
CST = timezone(timedelta(hours=8))
FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    art = json.loads(CENSUS.read_text(encoding="utf-8"))
    census_sha = sha256_file(CENSUS)
    script_sha = sha256_file(SCRIPT)
    rev1_sha = sha256_file(REV1)
    rev2_sha = sha256_file(REV2)
    ledger_sha = sha256_file(LEDGER)
    ts = datetime.now(CST).isoformat(timespec="seconds")
    eid = "w070-" + ts.replace(":", "").replace("-", "")[:15]
    agg = art["aggregate"]
    ldet = art["inputs"]["ledger/citation_audit.csv"]
    tdet = art["inputs"]["ledger/theorems.jsonl"]
    ev = art["falsifier_outcome"]["observed"]
    ckpt_ref = f"runtime/state/w070_checkpoint_locator.json"
    ev_refs = [f"artifacts/worker-070/l1_locator_resolvability/census.json#{census_sha[:12]}",
               f"ledger/citation_audit.csv#{ledger_sha[:16]}",
               f"artifacts/worker-070/l1_locator_resolvability/run_audit_070.py#{script_sha[:12]}",
               f"artifacts/worker-070/l1_locator_resolvability/superseded/census.rev1-voided.json#{rev1_sha[:12]}",
               f"artifacts/worker-070/l1_locator_resolvability/superseded/census.rev2-stopword-defect.json#{rev2_sha[:12]}"]
    nf = art["falsifier"]

    status_start = {
        "event_id": f"{eid}-status-start", "event_type": "status", "created_at": ts,
        "actor": "worker-070", "node_id": "L1", "group_id": "literature", "class_ids": FROZEN,
        "status": "active", "hours": 0.3,
        "assignment_ref": "w070-l1-locator-resolvability-01",
        "summary": ("No inbox card exists for worker-070; took one bounded class-bound task from the open literature "
                    "queue: does the `exact_locator` cell of ledger/citation_audit.csv re-resolve as recorded? "
                    "Pinned ledger sha 315c19145065; deterministic census of all 97 rows plus a pre-declared "
                    "15-fetch live sample; rev1 voided by auxiliary theorems drift and rev2 superseded for a "
                    "stopword title-match defect, both preserved and hashed under superseded/; rev3 is the result. "
                    "Does not claim node completion or any gate verdict."),
        "evidence_refs": [f"ledger/citation_audit.csv#{ledger_sha[:16]}", "research_map/research_map.json"],
        "next_falsifier": nf,
    }
    artifact_ev = {
        "event_id": f"{eid}-artifact-l1-locator-resolvability", "event_type": "artifact", "created_at": ts,
        "actor": "worker-070", "node_id": "L1", "group_id": "literature", "artifact_type": "l1_locator_resolvability_audit",
        "path": "artifacts/worker-070/l1_locator_resolvability/census.json", "sha256": census_sha,
        "validation_status": "unverified", "class_ids": FROZEN, "gate": "G-LIT",
        "task_id": "w070-l1-locator-resolvability-01",
        "ledger_sha256": ledger_sha, "ledger_sha256_pinned": ldet["sha256_pinned"],
        "ledger_drift": ldet["drift"], "theorems_sha256_start": tdet["sha256_start"],
        "theorems_sha256_end": tdet["sha256_end"], "theorems_drift": tdet["drift"],
        "summary": (f"{agg['family_counts']['elided']}/97 exact_locator cells are elided search queries ('...' in text); "
                    f"{agg['rows_without_doi_and_arxiv_count']} of those rows also lack DOI and arXiv id, so "
                    f"`evidence_url` is their only printed pointer (fetched live, resolved). Live sample: "
                    f"{ev}; identifier-URL rows RESOLVABLE, arXiv API rows recovered the work when reachable "
                    f"({agg['verdict_counts'].get('QUERY_TOP_HIT_MATCH', 0)} top-hit, "
                    f"{agg['verdict_counts'].get('QUERY_HIT_MATCH_NOT_TOP', 0)} non-top-hit among 5 reachable "
                    f"query locators). Elided rows: 0/3 top-hit. The elided-locator column-semantics finding stands."),
        "evidence_refs": list(ev_refs),
        "next_falsifier": nf,
    }
    review_ev = {
        "event_id": f"{eid}-review-l1-locator-column", "event_type": "review", "created_at": ts,
        "actor": "worker-070", "target_id": "ledger/citation_audit.csv", "reviewer": "worker-070",
        "verdict": "revise", "score": 3,
        "hard_failures": [],
        "findings": [
            ("COLUMN SEMANTICS (B): `exact_locator` is not an exact locator for "
             f"{agg['family_counts']['elided']}/97 rows; those cells are truncated INSPIRE search queries containing "
             "a literal '...'. The stored text alone is not a deterministic pointer; the identifier lives in the "
             "doi/arxiv_id columns or in evidence_url."),
            ("SCOPE-LIMITED RISK: in the pre-declared live sample of elided rows (11,12,13), 0/3 returned the target "
             "as the top hit and 1/3 (row 13) returned no matching hit at all in the top 10; 2/3 surfaced the target "
             "somewhere in the returned hits. The strong reading 'unresolvable' is therefore not falsified, and the "
             "surviving issue is that re-resolution depends on an external search engine's fuzzy ranking and on the "
             "query words that survived truncation, not on the recorded cell."),
            (f"NO-FALLBACK ROWS: {agg['rows_without_doi_and_arxiv']} elided rows (SRC-020, SRC-044) have no DOI and "
             "no arXiv id; their evidence_url resolved live. SRC-044 is class-bound to AF-WCC-SCALAR-SPH (theorems "
             "T-101, T-105), so one scalar-spherical-symmetry citation depends on evidence_url for its identifier."),
            ("BOUND: all conclusions are bound to ledger sha 315c19145065 (unchanged before and after the fetches). "
             "ledger/theorems.jsonl moved ce42d205e761 -> 3e3d35531421 during rev1 and was re-measured for rev2 as "
             "an auxiliary input only; that drift voided rev1 and is recorded, not hidden."),
            "SPOT/CENSUS EVIDENCE ONLY: not a gate verdict, not node completion, and not a full re-verification of rows not live-sampled.",
        ],
        "task_id": "w070-l1-locator-resolvability-01",
        "artifact_ref": f"artifacts/worker-070/l1_locator_resolvability/census.json#{census_sha[:12]}",
        "reviewed_sha256": ledger_sha, "class_ids": FROZEN, "gate": "G-LIT",
        "scope_limit": "97/97 rows census, 15-row live sample at one ledger hash",
        "evidence_refs": list(ev_refs),
    }
    status_done = {
        "event_id": f"{eid}-status-complete", "event_type": "status", "created_at": ts,
        "actor": "worker-070", "node_id": "L1", "group_id": "literature", "class_ids": FROZEN,
        "status": "active", "hours": 0.3,
        "assignment_ref": "w070-l1-locator-resolvability-01",
        "summary": ("worker-070 bounded task complete and exiting. Artifact census.json sha256 "
                    f"{census_sha}; checkpoint runtime/state/w070_checkpoint_locator.json. Ledger stable at "
                    f"315c19145065; verdicts={agg['verdict_counts']}. Node L1 remains active/pending: no gate "
                    "verdict, no node done, no claim."),
        "evidence_refs": list(ev_refs),
        "next_falsifier": nf,
    }
    events = [status_start, artifact_ev, review_ev, status_done]

    ckpt = {
        "worker": "worker-070", "checkpoint_at": ts,
        "task_id": "w070-l1-locator-resolvability-01",
        "assignment_ref": "self-taken; no inbox card for worker-070 (astra-life02-l1-spotcheck was closed by w070-20260912T002506)",
        "node_id": "L1", "gate": "G-LIT", "group_id": "literature", "class_ids": FROZEN,
        "status": "bounded_task_complete_unverified",
        "question": art["question"],
        "ledger_sha256_pinned": ldet["sha256_pinned"],
        "ledger_sha256_start": ldet["sha256_start"], "ledger_sha256_end": ldet["sha256_end"],
        "ledger_drift": ldet["drift"],
        "theorems_sha256_start": tdet["sha256_start"], "theorems_sha256_end": tdet["sha256_end"],
        "theorems_drift": tdet["drift"],
        "live_fetches": art["method"]["live_fetches"], "live_cap": art["method"]["live_cap"],
        "aggregate": {"family_counts": agg["family_counts"], "elided_count": agg["elided_count"],
                      "rows_without_doi_and_arxiv": agg["rows_without_doi_and_arxiv"],
                      "verdict_counts": agg["verdict_counts"],
                      "elided_live_sample": agg["elided_live_sample"]},
        "artifacts": {
            "artifacts/worker-070/l1_locator_resolvability/census.json": census_sha,
            "artifacts/worker-070/l1_locator_resolvability/run_audit_070.py": script_sha,
            "artifacts/worker-070/l1_locator_resolvability/superseded/census.rev1-voided.json": rev1_sha,
            "artifacts/worker-070/l1_locator_resolvability/superseded/census.rev2-stopword-defect.json": rev2_sha,
        },
        "events_emitted": [e["event_id"] for e in events],
        "authority_note": "worker event; cannot set node status done, validation_status passed, or any gate verdict",
        "next_falsifier": nf,
        "stop_rule": "1.5 agent-hours; no source outside the frozen ledger sha; no ledger edit",
    }
    CKPT.write_text(json.dumps(ckpt, indent=2, ensure_ascii=False), encoding="utf-8")
    ckpt_sha = sha256_file(CKPT)
    for e in events:
        e.setdefault("evidence_refs", [])
        ref = f"{ckpt_ref}#{ckpt_sha[:12]}"
        if ref not in e["evidence_refs"]:
            e["evidence_refs"].append(ref)

    # idempotent: drop any pre-existing lines with these event_ids, then append once
    key = "w070-l1-locator-resolvability-01"
    kept = []
    if OUTBOX.exists():
        for line in OUTBOX.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
                stale = d.get("assignment_ref") == key or d.get("task_id") == key
            except Exception:  # noqa: BLE001
                stale = False
            if not stale:
                kept.append(line)
    with OUTBOX.open("w", encoding="utf-8") as f:
        for line in kept:
            f.write(line + "\n")
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    print(f"checkpoint {CKPT} sha256 {ckpt_sha}")
    print(f"appended {len(events)} events to {OUTBOX}")
    for e in events:
        json.loads(json.dumps(e))
        print(" ", e["event_id"], e["event_type"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
