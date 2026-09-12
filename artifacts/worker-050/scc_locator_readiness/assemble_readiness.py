#!/usr/bin/env python3
"""W050-SCC-LOCATOR-READINESS-02: deterministic assembler (no network).

Consumes the frozen L1 ledger and a live-fetch observation file, and emits a
class-bound readiness map for the SCC classes:

  * for every row whose class_mapping contains AF-SCC-C2-VAC-GEN or
    AF-SCC-C0-VAC-GEN, classify `exact_locator` under the strict per-row reading;
  * for every weak row, propose the row-specific replacement locator from the
    ledger's own candidate columns (evidence_url -> url -> doi -> arxiv_id);
  * require a live fetch with HTTP 200 and a matching title before a proposal is
    called CONFIRMED;
  * certify that each proposed replacement is globally unique in the table under
    exact_locator/evidence_url/url, and report any collision instead of hiding it;
  * roll the result up per class composition.

Authority: decision support for the G-LIT criterion "ledger rows have resolvable
locators" (blocker BL-4).  NOT a ledger edit, NOT a gate verdict, NOT a
validation_status.  The canonical ledger remains owned by astra-lead-literature.

Falsifiers:
  F1 a proposed locator that does not return the cited work (title mismatch)
     voids that row's CONFIRMED verdict;
  F2 a row classified weak whose exact_locator is in fact a row-specific
     resolvable locator voids the classification for that row;
  F3 any change to ledger/citation_audit.csv away from the pinned sha256 voids
     the whole table (the runner exits 3);
  F4 a live re-fetch of a proposed locator returning HTTP != 200 or a different
     record voids the row;
  F5 a proposed replacement that collides with another row's locator voids the
     "per-row" reading for that proposal.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import unicodedata
import re
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))
PINNED_LEDGER_SHA256 = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
SCC_CLASSES = ("AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN")
WEAK_CLASSES = {"search_query", "truncated", "non_url", "empty"}
FIELDS = ("exact_locator", "evidence_url", "url")


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


def proposals_for(row: dict) -> list[tuple[str, str]]:
    """Ordered (value, source_field) candidate replacements for a weak row."""
    cands: list[tuple[str, str]] = []
    ev = (row.get("evidence_url") or "").strip()
    if ev:
        cands.append((ev, "evidence_url"))
    url = (row.get("url") or "").strip()
    if url and url not in [c for c, _ in cands]:
        cands.append((url, "url"))
    doi = (row.get("doi") or "").strip()
    if doi and doi.lower().startswith("10."):
        cands.append(("https://doi.org/" + doi, "doi"))
    ax = (row.get("arxiv_id") or "").strip()
    if ax:
        cands.append(("https://arxiv.org/abs/" + ax, "arxiv_id"))
    return cands


def record_locator_ok(value: str) -> bool:
    v = (value or "").strip()
    if not v.startswith(("http://", "https://")):
        return False
    if "..." in v:
        return False
    return not classify(v) == "search_query"


def collisions(rows: list[dict], cid: str, proposal: str) -> dict:
    out: dict[str, list[str]] = {}
    for r in rows:
        if r["citation_id"] == cid:
            continue
        for f in FIELDS:
            if (r.get(f) or "").strip() == proposal:
                out.setdefault(f, []).append(r["citation_id"])
    return out


def shared_locator_count(rows: list[dict], cid: str, locator: str) -> int:
    loc = (locator or "").strip()
    if not loc:
        return 0
    return sum(1 for r in rows if r["citation_id"] != cid and (r.get("exact_locator") or "").strip() == loc)


def class_bucket(class_mapping: str) -> str:
    toks = [t for t in (class_mapping or "").split(";") if t]
    scc = [t for t in toks if t in SCC_CLASSES]
    other = [t for t in toks if t not in SCC_CLASSES]
    if set(scc) == set(SCC_CLASSES) and not other:
        return "SCC-both-pure"
    if set(scc) == set(SCC_CLASSES):
        return "SCC-both+mixed"
    if scc == ["AF-SCC-C2-VAC-GEN"] and not other:
        return "SCC-C2-only"
    if scc == ["AF-SCC-C0-VAC-GEN"] and not other:
        return "SCC-C0-only"
    return "SCC+mixed"


def assemble(rows: list[dict], fetches: list[dict], ledger_sha: str, evidence_sha: str, measured_at: str) -> dict:
    ev_index = {(e["citation_id"], e.get("fetched_locator")): e for e in fetches}
    scc_rows = [r for r in rows if set(t.strip() for t in (r.get("class_mapping") or "").split(";")) & set(SCC_CLASSES)]
    out_rows = []
    counts = {"rows_in_scope": len(scc_rows), "direct_rows": 0, "weak_rows": 0,
              "confirmed": 0, "failed_title_mismatch": 0, "failed_proposal_collision": 0,
              "unverified": 0, "no_candidate": 0,
              "proposal_collisions": 0, "current_locator_shared": 0}
    bucket_counts: dict[str, dict] = {}

    for r in sorted(scc_rows, key=lambda x: x["citation_id"]):
        cid = r["citation_id"]
        loc = r.get("exact_locator") or ""
        cls = classify(loc)
        weak = cls in WEAK_CLASSES
        bucket = class_bucket(r.get("class_mapping") or "")
        counts["weak_rows" if weak else "direct_rows"] += 1
        shared = shared_locator_count(rows, cid, loc)
        if weak and shared:
            counts["current_locator_shared"] += 1

        rec = {
            "citation_id": cid,
            "bibkey": r.get("bibkey"),
            "title": r.get("title"),
            "class_mapping": r.get("class_mapping"),
            "class_bucket": bucket,
            "status": r.get("status"),
            "verification_method": r.get("verification_method"),
            "current_exact_locator": loc,
            "classification": cls,
            "needs_repair": weak,
            "current_locator_shared_by_other_rows": shared,
            "proposed_exact_locator": None,
            "proposal_source_field": None,
            "proposal_is_record_locator": None,
            "proposal_collisions": {},
            "proposal_global_unique": None,
            "fetch": None,
            "repair_verdict": "NO_ACTION_NEEDED" if not weak else None,
        }
        if weak:
            cands = proposals_for(r)
            chosen = next(((v, f) for v, f in cands if record_locator_ok(v)), None)
            if chosen is None:
                rec["repair_verdict"] = "NO_CANDIDATE"
                counts["no_candidate"] += 1
            else:
                proposal, field = chosen
                ev = ev_index.get((cid, proposal))
                coll = collisions(rows, cid, proposal)
                rec.update({
                    "proposed_exact_locator": proposal,
                    "proposal_source_field": field,
                    "proposal_is_record_locator": record_locator_ok(proposal),
                    "proposal_collisions": coll,
                    "proposal_global_unique": not coll,
                    "fetch": ev,
                })
                if coll:
                    # A deterministic table property outranks a network observation:
                    # a colliding replacement fails the per-row reading even if it fetches 200.
                    counts["proposal_collisions"] += 1
                    counts["failed_proposal_collision"] += 1
                    rec["repair_verdict"] = "FAIL_PROPOSAL_COLLISION"
                elif ev is None:
                    rec["repair_verdict"] = "UNVERIFIED_NO_FETCH"
                    counts["unverified"] += 1
                elif ev.get("http_status") != 200:
                    rec["repair_verdict"] = "UNVERIFIED_HTTP_%s" % ev.get("http_status")
                    counts["unverified"] += 1
                elif not ev.get("title_match"):
                    rec["repair_verdict"] = "FAIL_TITLE_MISMATCH"
                    counts["failed_title_mismatch"] += 1
                else:
                    rec["repair_verdict"] = "CONFIRMED"
                    counts["confirmed"] += 1
        out_rows.append(rec)
        b = bucket_counts.setdefault(bucket, {"rows": 0, "weak": 0, "confirmed": 0, "unverified": 0, "failed": 0})
        b["rows"] += 1
        if weak:
            b["weak"] += 1
            if rec["repair_verdict"] == "CONFIRMED":
                b["confirmed"] += 1
            elif rec["repair_verdict"].startswith("UNVERIFIED") or rec["repair_verdict"] == "NO_CANDIDATE":
                b["unverified"] += 1
            else:
                b["failed"] += 1

    artifact = {
        "artifact_id": "W050-SCC-LOCATOR-READINESS-02",
        "artifact_type": "class_bound_locator_readiness_map",
        "actor": "worker-050",
        "created_at": measured_at,
        "class_id": ";".join(SCC_CLASSES),
        "node_id": "L1",
        "gate": "G-LIT",
        "authority": (
            "decision support for the G-LIT criterion 'ledger rows have resolvable locators' and "
            "for blocker BL-4 (exact_locator column semantics); NOT a ledger edit, NOT a gate "
            "verdict, NOT a validation_status. The canonical ledger remains owned by "
            "astra-lead-literature; a lead must merge any patch."
        ),
        "inputs": {
            "ledger/citation_audit.csv": {
                "sha256_measured": ledger_sha,
                "sha256_pinned": PINNED_LEDGER_SHA256,
                "matches_pin": ledger_sha == PINNED_LEDGER_SHA256,
            },
            "artifacts/worker-050/scc_locator_readiness/fetch_evidence.json": {
                "sha256_measured": evidence_sha,
                "note": "live HTTP observations; a missing observation is UNVERIFIED, never a pass",
            },
        },
        "method": (
            "read-only; weak rows are those whose exact_locator is a query/truncated/non-URL string "
            "under the strict per-row reading. Replacement proposed from the ledger's own "
            "evidence_url (fallbacks url -> doi -> arxiv_id), accepted only with HTTP 200 and a "
            "normalised title match, and only if the replacement is globally unique across the "
            "table's exact_locator/evidence_url/url columns."
        ),
        "scope_limit": (
            "Only rows whose class_mapping contains %s are in scope. The 6 WCC-class weak rows "
            "repaired in W050-WCC-LOCATOR-REPAIR-01 are not re-opened here. Only the exact_locator "
            "FIELD is under test; quoted evidence, verdict and reviewer columns are not "
            "re-adjudicated, and no mathematical content is verified." % " or ".join(SCC_CLASSES)
        ),
        "counts": counts,
        "per_class_bucket": bucket_counts,
        "falsifiers": [
            "F1: any proposed locator that does not return the cited work (title mismatch) voids that row's CONFIRMED verdict.",
            "F2: a row classified weak whose exact_locator is in fact a row-specific resolvable locator voids the classification for that row.",
            "F3: any change to ledger/citation_audit.csv away from the pinned sha256 voids the whole table; re-run fetch_locators.py then assemble_readiness.py against the new bytes.",
            "F4: a live re-fetch of a proposed locator returning HTTP != 200 or a different record voids the row.",
            "F5: a proposed replacement that collides with another row's locator voids the per-row reading for that proposal.",
        ],
        "next_falsifier": (
            "Re-fetch every proposed locator; any non-200 or title mismatch, any collision, or any "
            "ledger hash change invalidates the corresponding row or the whole table."
        ),
        "rows": out_rows,
    }
    return artifact


def selftest() -> int:
    base = [
        {"citation_id": "T-1", "bibkey": "a", "title": "Alpha paper", "class_mapping": "AF-SCC-C2-VAC-GEN",
         "exact_locator": 'search_query=all:"alpha"', "evidence_url": "https://example.org/rec/1", "url": "",
         "doi": "", "arxiv_id": "", "status": "verified-api", "verification_method": "x"},
        {"citation_id": "T-2", "bibkey": "b", "title": "Beta paper", "class_mapping": "AF-SCC-C0-VAC-GEN",
         "exact_locator": "https://example.org/rec/2", "evidence_url": "https://example.org/rec/2", "url": "",
         "doi": "", "arxiv_id": "", "status": "verified-api", "verification_method": "x"},
        {"citation_id": "T-3", "bibkey": "c", "title": "Gamma paper", "class_mapping": "AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN",
         "exact_locator": "search_query=all:\"gamma\"", "evidence_url": "https://example.org/rec/1", "url": "",
         "doi": "", "arxiv_id": "", "status": "verified-api", "verification_method": "x"},
        {"citation_id": "T-4", "bibkey": "d", "title": "Delta paper", "class_mapping": "AF-SCC-C2-VAC-GEN",
         "exact_locator": "...truncated...", "evidence_url": "https://example.org/rec/4", "url": "",
         "doi": "", "arxiv_id": "", "status": "verified-api", "verification_method": "x"},
    ]
    fetches = [
        {"citation_id": "T-1", "fetched_locator": "https://example.org/rec/1", "http_status": 200, "title_match": True},
        {"citation_id": "T-4", "fetched_locator": "https://example.org/rec/4", "http_status": 403, "title_match": False},
    ]
    art = assemble(base, fetches, PINNED_LEDGER_SHA256, "0" * 64, "2026-01-01T00:00:00+08:00")
    by = {r["citation_id"]: r for r in art["rows"]}
    assert by["T-1"]["classification"] == "search_query", by["T-1"]["classification"]
    assert by["T-2"]["classification"] == "direct_record_locator"
    assert by["T-3"]["classification"] == "search_query"
    assert by["T-4"]["classification"] == "truncated"
    # T-1 proposal rec/1 is already T-2's exact_locator -> collision must be reported.
    assert by["T-1"]["proposal_global_unique"] is False, by["T-1"]
    assert by["T-1"]["repair_verdict"] == "FAIL_PROPOSAL_COLLISION", by["T-1"]["repair_verdict"]
    # T-3 same collision.
    assert by["T-3"]["repair_verdict"] == "FAIL_PROPOSAL_COLLISION", by["T-3"]["repair_verdict"]
    # T-4 fetch is non-200 -> unverified, never confirmed.
    assert by["T-4"]["repair_verdict"] == "UNVERIFIED_HTTP_403", by["T-4"]["repair_verdict"]
    assert art["counts"]["confirmed"] == 0, art["counts"]
    assert art["counts"]["weak_rows"] == 3 and art["counts"]["direct_rows"] == 1, art["counts"]
    # record_locator_ok rejects query strings and elisions.
    assert record_locator_ok("https://example.org/x") is True
    assert record_locator_ok('https://example.org/search?q="x"') is False
    assert record_locator_ok("https://example.org/x...") is False
    assert record_locator_ok("doi:10.1/x") is False
    # uniqueness held when no other row carries the string.
    ok = assemble(
        [dict(base[0], citation_id="U-1", evidence_url="https://example.org/unique")],
        [{"citation_id": "U-1", "fetched_locator": "https://example.org/unique", "http_status": 200, "title_match": True}],
        PINNED_LEDGER_SHA256, "0" * 64, "2026-01-01T00:00:00+08:00",
    )
    assert ok["rows"][0]["repair_verdict"] == "CONFIRMED", ok["rows"][0]
    assert ok["counts"]["confirmed"] == 1
    print("SELFTEST PASS: classifier, collision detection, verdict fail-closed, uniqueness")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger")
    ap.add_argument("--fetch-evidence")
    ap.add_argument("--out")
    ap.add_argument("--timestamp", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not (args.ledger and args.fetch_evidence and args.out):
        ap.error("--ledger, --fetch-evidence and --out are required unless --selftest")

    ledger_sha = sha256_file(args.ledger)
    evidence_sha = sha256_file(args.fetch_evidence)
    rows = list(csv.DictReader(open(args.ledger, newline="")))
    evidence = json.load(open(args.fetch_evidence))
    measured_at = args.timestamp or datetime.now(TZ).replace(microsecond=0).isoformat()
    artifact = assemble(rows, evidence.get("fetches", []), ledger_sha, evidence_sha, measured_at)
    with open(args.out, "w") as fh:
        json.dump(artifact, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    c = artifact["counts"]
    print("scope=%d weak=%d confirmed=%d unverified=%d failed=%d collisions=%d pin_ok=%s"
          % (c["rows_in_scope"], c["weak_rows"], c["confirmed"], c["unverified"],
             c["failed_title_mismatch"] + c["failed_proposal_collision"],
             c["proposal_collisions"], ledger_sha == PINNED_LEDGER_SHA256))
    return 0 if ledger_sha == PINNED_LEDGER_SHA256 else 3


if __name__ == "__main__":
    sys.exit(main())
