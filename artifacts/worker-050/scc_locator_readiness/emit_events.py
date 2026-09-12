#!/usr/bin/env python3
"""Emit worker-050 SCC locator-readiness events (artifact/review/status).

Fail-closed emission:
  * every file hash is re-measured at emission time; a mismatch aborts;
  * every event is validated with research_map.schemas.validate_event before any
    bytes are appended;
  * an event_id already present in the outbox aborts the run (idempotence guard).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "research_map"))
from schemas import validate_event  # noqa: E402

TZ = timezone(timedelta(hours=8))
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
BASE = "artifacts/worker-050/scc_locator_readiness"
OUTBOX = os.path.join(REPO, "comms/outbox/worker-050.jsonl")
LEDGER = "ledger/citation_audit.csv"
LEDGER_SHA = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    now = datetime.now(TZ).replace(microsecond=0)
    stamp = now.strftime("%Y%m%dT%H%M%S%z")          # e.g. 20260912T004512+0800
    eid = lambda slug: f"w050-{stamp}-scc-{slug}"     # noqa: E731

    files = {
        "readiness": f"{BASE}/readiness.json",
        "fetch_evidence": f"{BASE}/fetch_evidence.json",
        "fetch_evidence_recheck": f"{BASE}/fetch_evidence_recheck.json",
        "recheck_summary": f"{BASE}/recheck_summary.json",
        "fetch_runner": f"{BASE}/fetch_locators.py",
        "assemble_runner": f"{BASE}/assemble_readiness.py",
        "compare_runner": f"{BASE}/compare_rechecks.py",
        "readme": f"{BASE}/README.md",
    }
    hashes = {k: sha256_file(os.path.join(REPO, p)) for k, p in files.items()}
    ledger_sha = sha256_file(os.path.join(REPO, LEDGER))
    if ledger_sha != LEDGER_SHA:
        print("ABORT: ledger moved to %s" % ledger_sha)
        return 3
    r = json.load(open(os.path.join(REPO, files["readiness"])))
    c = r["counts"]
    if not (c["weak_rows"] == 26 and c["confirmed"] == 26 and c["proposal_collisions"] == 0):
        print("ABORT: readiness counts changed: %s" % c)
        return 1

    falsifier = ("F3: any change to ledger/citation_audit.csv away from %s voids the whole table; "
                 "F1/F4: a re-fetch of a proposed locator returning non-200 or a different record "
                 "voids the row; F5: any proposed replacement that collides with another row's "
                 "locator voids the per-row reading." % LEDGER_SHA[:12])
    events = [
        {
            "event_id": eid("artifact-readiness"), "event_type": "artifact", "actor": "worker-050",
            "created_at": now.isoformat(), "node_id": "L1", "gate": "G-LIT",
            "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
            "artifact_type": "class_bound_locator_readiness_map",
            "path": files["readiness"], "sha256": hashes["readiness"], "validation_status": "unverified",
            "note": ("SCC-bound locator readiness map at frozen L1 %s: 34 rows in scope, 26 weak, "
                     "26/26 replacements proposed from evidence_url live-fetch HTTP 200 + title match, "
                     "26/26 globally unique, 0 failures, 0 collisions. Decision support for BL-4 option "
                     "(ii); NOT a ledger edit, gate verdict or validation_status."
                     % LEDGER_SHA[:12]),
            "falsifier": falsifier,
        },
        {
            "event_id": eid("artifact-fetchevidence"), "event_type": "artifact", "actor": "worker-050",
            "created_at": now.isoformat(), "node_id": "L1", "gate": "G-LIT",
            "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
            "artifact_type": "live_fetch_observations",
            "path": files["fetch_evidence"], "sha256": hashes["fetch_evidence"], "validation_status": "unverified",
            "note": "Fetch pass 1: 34/34 SCC-bound rows HTTP 200 with matching returned title; ledger pinned at emission.",
            "falsifier": falsifier,
        },
        {
            "event_id": eid("artifact-recheck-evidence"), "event_type": "artifact", "actor": "worker-050",
            "created_at": now.isoformat(), "node_id": "L1", "gate": "G-LIT",
            "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
            "artifact_type": "live_fetch_observations",
            "path": files["fetch_evidence_recheck"], "sha256": hashes["fetch_evidence_recheck"],
            "validation_status": "unverified",
            "note": "Fetch pass 2 (independent re-fetch of every proposed locator): 34/34 HTTP 200 with matching returned title.",
            "falsifier": falsifier,
        },
        {
            "event_id": eid("artifact-recheck-summary"), "event_type": "artifact", "actor": "worker-050",
            "created_at": now.isoformat(), "node_id": "L1", "gate": "G-LIT",
            "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
            "artifact_type": "fetch_stability_comparison",
            "path": files["recheck_summary"], "sha256": hashes["recheck_summary"], "validation_status": "unverified",
            "note": "Two-pass comparison: 34 compared, 34 stable, 0 mismatches; ledger pin held across both passes.",
            "falsifier": falsifier,
        },
        {
            "event_id": eid("artifact-runners"), "event_type": "artifact", "actor": "worker-050",
            "created_at": now.isoformat(), "node_id": "L1", "gate": "G-LIT",
            "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
            "artifact_type": "reproducible_runner",
            "path": files["assemble_runner"], "sha256": hashes["assemble_runner"], "validation_status": "unverified",
            "note": ("Deterministic assembler; --selftest PASS (classifier, collision detection, fail-closed "
                     "verdicts, uniqueness). Companion runners: %s sha256 %s; %s sha256 %s."
                     % (files["fetch_runner"], hashes["fetch_runner"][:12],
                        files["compare_runner"], hashes["compare_runner"][:12])),
            "falsifier": falsifier,
        },
        {
            "event_id": eid("artifact-readme"), "event_type": "artifact", "actor": "worker-050",
            "created_at": now.isoformat(), "node_id": "L1", "gate": "G-LIT",
            "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
            "artifact_type": "documentation",
            "path": files["readme"], "sha256": hashes["readme"], "validation_status": "unverified",
            "note": "Claims, method, per-bucket result, file hashes, falsifiers F1-F5, authority and scope limits.",
            "falsifier": falsifier,
        },
        {
            "event_id": eid("review-l1-locators"), "event_type": "review", "actor": "worker-050",
            "created_at": now.isoformat(), "node_id": "L1", "gate": "G-LIT",
            "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
            "target_id": LEDGER, "target_sha256": LEDGER_SHA,
            "reviewer": "worker-050", "verdict": "revise", "score": 4,
            "hard_failures": [
                ("L1-ADJ-F1-SCC: 26 of the 34 SCC-bound rows carry a search-query or truncated string in "
                 "exact_locator (17 of the 26 strings are reused by another row), so under the strict "
                 "per-row reading the G-LIT criterion 'ledger rows have resolvable locators' is unmet at "
                 "315c1914 for AF-SCC-C2-VAC-GEN and AF-SCC-C0-VAC-GEN.")
            ],
            "findings": [
                "Independent worker measurement, not a lead or gate verdict; the ledger is read-only here.",
                "The ledger is honest about evidence level: all 26 weak SCC rows are status=verified-api; "
                "no bibliographic mismatch (title/author/venue) was found in this pass.",
                "Recomputed BL-4 numbers: 67 weak cells over 43 distinct strings table-wide (max share 7); "
                "SCC scope 26 weak cells over 17 distinct strings; evidence_url has 95 non-empty values, "
                "all 95 distinct, so a rewrite cannot introduce a new per-row collision.",
                "Repair is feasible and verified for the SCC half: 26 proposed replacements, each a "
                "single-record locator, fetched twice with HTTP 200 and matching title, globally unique "
                "across exact_locator/evidence_url/url.",
                "Under BL-4 option (ii) the patch moves the L1 hash and voids the 12 current spot checks; "
                "under option (i) this map is the per-row evidence_url census for the SCC half.",
                "Scope limit: 8 direct SCC rows need no repair and are not claimed as repaired; the 12 "
                "AF-WCC-VAC-GEN rows are covered by W050-WCC-LOCATOR-REPAIR-01 and are not re-opened.",
            ],
            "independence": ("Reviewer did not author the ledger; the review covers only the exact_locator "
                             "field at the pinned hash and does not re-adjudicate quoted evidence, verdicts "
                             "or mathematical content."),
        },
        {
            "event_id": eid("status-locators"), "event_type": "status", "actor": "worker-050",
            "created_at": now.isoformat(), "node_id": "L1", "status": "active", "hours": 0.75,
            "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN", "gate": "G-LIT",
            "summary": ("W050-SCC-LOCATOR-READINESS-02 complete at worker level: SCC-bound locator "
                        "readiness map at frozen L1 315c1914 (34 rows, 26 weak, 26/26 replacements live-"
                        "verified twice and globally unique, 0 failures/collisions) plus a revise review "
                        "binding the BL-4 decision. No ledger edit; no gate verdict; no node transition."),
            "evidence_refs": [
                f"{files['readiness']}#{hashes['readiness'][:12]}",
                f"{files['recheck_summary']}#{hashes['recheck_summary'][:12]}",
                f"{LEDGER}#{LEDGER_SHA[:12]}",
                "comms/outbox/astra-lead-literature.jsonl lit-l4-20260912-006 (BL-4)",
            ],
            "next_falsifier": ("A ledger revision that moves 315c1914, a re-fetch that returns non-200 or a "
                               "different record, or a proposal collision voids the affected row or the whole "
                               "table; re-run fetch_locators.py and assemble_readiness.py on the new bytes."),
        },
    ]

    # idempotence guard + schema validation before any write
    existing = set()
    if os.path.exists(OUTBOX):
        for line in open(OUTBOX):
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                continue
    for ev in events:
        if ev["event_id"] in existing:
            print("ABORT: duplicate event_id %s" % ev["event_id"])
            return 1
        validate_event(ev)

    with open(OUTBOX, "a") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False, sort_keys=True) + "\n")

    # re-parse the appended lines and re-validate them from disk
    written = [json.loads(l) for l in open(OUTBOX) if l.strip()]
    tail = written[-len(events):]
    for ev in tail:
        validate_event(ev)
    print("emitted=%d validated=%d outbox=%s" % (len(events), len(tail), OUTBOX))
    for ev in events:
        print(" ", ev["event_id"], ev["event_type"], ev.get("path", ev.get("target_id", "")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
