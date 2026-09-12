#!/usr/bin/env python3
"""Measured census of independent review verdicts binding the frozen L0 ledger.

Read-only. Scans every outbox JSONL/JSON event, selects review events that bind
ledger/theorems.jsonl at the announced rev-3 hash, and classifies each as an L0
content verdict or as out-of-scope for the L0 gate census (packet / builder /
detector / spot-check / L1 / formulation reviews). Emits JSON on stdout.

No map write, no ledger write, no gate verdict. The census is decision input for
the controller; it is not an accept and does not count toward any gate.

Inclusion predicate (L0 content verdict), all required:
  1. event_type == "review"
  2. binds the hash: artifact_sha256 / reviewed_sha256 == A, or an evidence_ref
     carries "ledger/theorems.jsonl#a1674f09", or target_id carries the prefix
  3. reviews the ledger as a whole: base target_id (before ":") in
     {"L0", "L1", "L0,L1", "L1,L0"} or starts with "ledger/theorems.jsonl"
  4. not a sample spot check, a builder/tooling review, or another object's review

Independence: reviewer must not be the ledger author (astra-lead-literature).
"full_schema_basis" is the reviewer's own attestation where present, else the
manager-side target/path check; it is reported, not upgraded.
"""
from __future__ import annotations

import glob
import json
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
A = "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"
P = "a1674f09"
CST = timezone(timedelta(hours=8))

INCLUDE_TARGETS = ("L0", "L1", "L0,L1", "L1,L0")


def first_event_per_id():
    seen, sources = {}, {}
    files = sorted(glob.glob(os.path.join(ROOT, "comms/outbox/**/*.jsonl"), recursive=True))
    files += sorted(glob.glob(os.path.join(ROOT, "comms/outbox/**/*.json"), recursive=True))
    for f in files:
        try:
            txt = open(f, errors="replace").read()
        except OSError:
            continue
        for ln in txt.splitlines():
            ln = ln.strip().rstrip(",")
            if not (ln.startswith("{") and ln.endswith("}")):
                continue
            try:
                e = json.loads(ln)
            except ValueError:
                continue
            if not isinstance(e, dict) or e.get("event_type") != "review":
                continue
            eid = e.get("event_id")
            if not eid or eid in seen:
                continue
            seen[eid] = e
            sources[eid] = os.path.relpath(f, ROOT)
    return seen, sources


def base_target(e):
    return str(e.get("target_id") or "").split(":")[0].strip()


def binds_hash(e):
    if e.get("artifact_sha256") == A or e.get("reviewed_sha256") == A:
        return True
    for r in e.get("evidence_refs") or []:
        if "ledger/theorems.jsonl#" + P in str(r):
            return True
    return P in str(e.get("target_id", ""))


def l0_scope(e):
    bt = base_target(e)
    return bt in INCLUDE_TARGETS or bt.startswith("ledger/theorems.jsonl")


def exclusion_reason(e):
    if not l0_scope(e):
        return "target is not the L0 ledger"
    eid = str(e.get("event_id") or "").lower()
    art = str(e.get("artifact") or "").lower()
    tgt = str(e.get("target_id") or "").lower()
    attested = e.get("counts_as_full_schema_verdict") is True or e.get("counts_as_full_ledger_verdict") is True
    if ("spotcheck" in eid or "spot check" in eid or "spotcheck" in art) and not attested:
        return "sample spot check, not a ledger-wide verdict"
    if "build_literature" in tgt or "build_literature" in art:
        return "builder/tooling review, not ledger content"
    return None


def full_schema_basis(e):
    if e.get("counts_as_full_schema_verdict") is True or e.get("counts_as_full_ledger_verdict") is True:
        return "attested"
    ev = " ".join(str(x) for x in (e.get("evidence_refs") or []))
    if any(k in ev for k in ("l0_rev", "l0_cf19", "l0rev", "l0_rev3")):
        return "target+instrument-path"
    return "target-only"


def main():
    seen, sources = first_event_per_id()
    rows = []
    for eid, e in seen.items():
        if not binds_hash(e):
            continue
        reason = exclusion_reason(e)
        inc = reason is None
        rows.append({
            "event_id": eid,
            "created_at": e.get("created_at"),
            "actor": e.get("actor"),
            "target_id": e.get("target_id"),
            "verdict": e.get("verdict"),
            "score": e.get("score"),
            "hard_failures": e.get("hard_failures"),
            "counts_as_full_schema_verdict": e.get("counts_as_full_schema_verdict"),
            "counts_toward_gate_accept": e.get("counts_toward_gate_accept"),
            "full_schema_basis": full_schema_basis(e),
            "l0_content_verdict": inc,
            "exclusion_reason": reason,
            "scope_note": e.get("scope"),
            "source_file": sources[eid],
            "reviewer_is_ledger_author": e.get("actor") == "astra-lead-literature",
        })
    rows.sort(key=lambda r: (r["created_at"] or "", r["event_id"] or ""))
    l0 = [r for r in rows if r["l0_content_verdict"]]
    out = {
        "schema": "astra/literature/l0-verdict-census/v1",
        "actor": "astra-lead-literature",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "target": {"path": "ledger/theorems.jsonl", "sha256": A},
        "scan": {
            "roots": ["comms/outbox/**/*.jsonl", "comms/outbox/**/*.json"],
            "review_events_citing_target": len(rows),
            "l0_content_verdicts": len(l0),
            "scan_script": "artifacts/literature/reviews/l0_verdict_census.py",
        },
        "counts": {
            "accept": sum(1 for r in l0 if r["verdict"] == "accept"),
            "revise": sum(1 for r in l0 if r["verdict"] == "revise"),
            "reject": sum(1 for r in l0 if r["verdict"] == "reject"),
            "inconclusive": sum(1 for r in l0 if r["verdict"] == "inconclusive"),
            "distinct_reviewers": sorted({r["actor"] for r in l0}),
            "accept_reviewers": sorted({r["actor"] for r in l0 if r["verdict"] == "accept"}),
            "accept_reviewers_attested_full_schema": sorted(
                {r["actor"] for r in l0 if r["verdict"] == "accept" and r["full_schema_basis"] == "attested"}),
        },
        "l0_content_verdicts": l0,
        "out_of_scope_reviews": [r for r in rows if not r["l0_content_verdict"]],
        "authority": "not an accept, not a gate verdict, not a node status; counts_toward_gate_accept=false",
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
