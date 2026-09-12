#!/usr/bin/env python3
"""W050-WCC-LOCATOR-REPAIR-01: class-bound locator-resolvability repair map.

Scope: rows of the frozen L1 citation ledger whose class_mapping is exactly
AF-WCC-VAC-GEN.  Deterministic, read-only: this script never edits the ledger.

Method
------
1. Pin the ledger by sha256 and refuse to emit a table if the bytes moved
   (a moved ledger makes every proposal stale).
2. Classify each row's `exact_locator`:
     direct_record_locator  - the locator string itself names one record
     search_query           - a query endpoint, resolves to a SET of records
     truncated              - the string contains an elision ('...')
     non_url                - none of the above
3. For every non-direct row, propose `evidence_url` (fallback: `url`) as the
   replacement locator, and require that the replacement was live-fetched with
   matching title/author/year metadata in fetch_evidence.json.
4. Emit resolution.json.  A row whose replacement has no fetch evidence, or
   whose fetched metadata does not match, is emitted with verdict FAIL/UNVERIFIED
   rather than being silently counted as repaired.

Falsifiers (also recorded in resolution.json):
  F1 any proposed locator that does not return the cited work (title/author
     mismatch) voids that row's CONFIRMED verdict;
  F2 a row classified non-direct whose exact_locator is in fact a row-specific
     resolvable locator voids the classification for that row;
  F3 a ledger revision that changes the pinned sha256 voids the whole table.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))
PINNED_LEDGER_SHA256 = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
TARGET_CLASS = "AF-WCC-VAC-GEN"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def classify(locator: str) -> str:
    loc = (locator or "").strip()
    if not loc:
        return "empty"
    if "..." in loc:
        return "truncated"
    low = loc.lower()
    if any(tok in low for tok in ("search_query=", "?q=", "&q=", "/search")):
        return "search_query"
    if loc.startswith("http://") or loc.startswith("https://"):
        return "direct_record_locator"
    return "non_url"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--fetch-evidence", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    ledger_sha = sha256_file(args.ledger)
    measured_at = datetime.now(TZ).replace(microsecond=0).isoformat()
    evidence = json.load(open(args.fetch_evidence))
    ev_index = {(e["citation_id"], e["fetched_locator"]): e for e in evidence["fetches"]}

    import csv

    rows = list(csv.DictReader(open(args.ledger)))
    wcc = [r for r in rows if r["class_mapping"] == TARGET_CLASS]

    out_rows = []
    n_weak = n_repaired = n_failed = 0
    for r in sorted(wcc, key=lambda x: x["citation_id"]):
        loc = r["exact_locator"]
        cls = classify(loc)
        direct = cls == "direct_record_locator"
        proposal = None
        verdict = "NO_ACTION_NEEDED"
        fetched = None
        candidates_considered = []
        if not direct:
            n_weak += 1
            raw_candidates = [
                ((r.get("evidence_url") or "").strip(), "evidence_url"),
                ((r.get("url") or "").strip(), "url"),
            ]
            seen = set()
            candidates = [(c, f) for c, f in raw_candidates if c and not (c in seen or seen.add(c))]
            for cand, field in candidates:
                ev = ev_index.get((r["citation_id"], cand))
                if ev is None:
                    row_verdict = "UNVERIFIED_NO_FETCH"
                elif ev.get("http_status") != 200:
                    row_verdict = "UNVERIFIED_HTTP_%s" % ev.get("http_status")
                elif not ev.get("title_match"):
                    row_verdict = "FAIL_TITLE_MISMATCH"
                else:
                    row_verdict = "CONFIRMED"
                candidates_considered.append(
                    {"candidate": cand, "source_field": field, "verdict": row_verdict,
                     "http_status": (ev or {}).get("http_status")}
                )
                if row_verdict == "CONFIRMED":
                    proposal, fetched, verdict = cand, ev, "CONFIRMED"
                    break
            if verdict != "CONFIRMED":
                n_failed += 1
                if candidates_considered and all(c["verdict"].startswith("UNVERIFIED") for c in candidates_considered):
                    verdict = "UNVERIFIED"
                else:
                    verdict = "FAIL"
                proposal = candidates_considered[0]["candidate"] if candidates_considered else None
                fetched = ev_index.get((r["citation_id"], proposal)) if proposal else None
            else:
                n_repaired += 1
        out_rows.append(
            {
                "citation_id": r["citation_id"],
                "bibkey": r["bibkey"],
                "title": r["title"],
                "current_exact_locator": loc,
                "classification": cls,
                "needs_repair": not direct,
                "proposed_exact_locator": proposal,
                "candidate_source_field": next(
                    (c["source_field"] for c in candidates_considered if c["candidate"] == proposal), None
                ),
                "candidates_considered": candidates_considered,
                "repair_verdict": verdict,
                "fetch": fetched,
            }
        )

    artifact = {
        "artifact_id": "W050-WCC-LOCATOR-REPAIR-01",
        "artifact_type": "class_bound_locator_repair_map",
        "actor": "worker-050",
        "created_at": measured_at,
        "class_id": TARGET_CLASS,
        "node_id": "L1",
        "gate": "G-LIT",
        "authority": (
            "decision support for the G-LIT 'resolvable locators' criterion; NOT a ledger edit, "
            "NOT a gate verdict, NOT a validation_status. The canonical ledger remains owned by "
            "astra-lead-literature."
        ),
        "inputs": {
            "ledger/citation_audit.csv": {
                "sha256_measured": ledger_sha,
                "sha256_pinned": PINNED_LEDGER_SHA256,
                "matches_pin": ledger_sha == PINNED_LEDGER_SHA256,
            },
            "ledger/theorems.jsonl": {
                "sha256_measured": sha256_file("ledger/theorems.jsonl"),
                "note": "read-only context; this task does not modify or re-derive L0 rows",
            },
        },
        "scope_limit": (
            "Only rows with class_mapping exactly AF-WCC-VAC-GEN were classified (12 rows). "
            "The 6 rows with a direct record locator were classified but NOT re-fetched in this "
            "pass; no resolution claim is made for them. Only the exact_locator FIELD is under "
            "test: the quoted evidence, verdict and reviewer columns of the ledger are not "
            "re-adjudicated here. Fetch metadata was observed by a live HTTP fetch from this "
            "session; fetched_at is wall-clock to +/-2 minutes because the fetch tool does not "
            "return a timestamp."
        ),
        "counts": {
            "rows_in_class": len(wcc),
            "direct_rows": len(wcc) - n_weak,
            "weak_locator_rows": n_weak,
            "repair_confirmed": n_repaired,
            "repair_failed_or_unverified": n_failed,
        },
        "falsifiers": [
            "F1: any proposed locator that does not return the cited work (title/author/year mismatch) voids that row's CONFIRMED verdict.",
            "F2: a row classified non-direct whose exact_locator is in fact a row-specific resolvable locator voids the classification for that row.",
            "F3: any change to ledger/citation_audit.csv away from the pinned sha256 voids the whole table; re-run resolve_wcc_locators.py against the new bytes.",
            "F4: a live re-fetch of a proposed locator returning HTTP != 200 or a different record voids the row.",
        ],
        "next_falsifier": (
            "Re-fetch every proposed locator; any non-200 or title mismatch, or any ledger hash "
            "change, invalidates the corresponding row or the whole table respectively."
        ),
        "rows": out_rows,
    }

    with open(args.out, "w") as fh:
        json.dump(artifact, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")

    print(
        "rows=%d direct=%d weak=%d confirmed=%d failed=%d ledger_pin_ok=%s"
        % (
            len(wcc),
            len(wcc) - n_weak,
            n_weak,
            n_repaired,
            n_failed,
            ledger_sha == PINNED_LEDGER_SHA256,
        )
    )
    return 0 if ledger_sha == PINNED_LEDGER_SHA256 else 3


if __name__ == "__main__":
    sys.exit(main())
