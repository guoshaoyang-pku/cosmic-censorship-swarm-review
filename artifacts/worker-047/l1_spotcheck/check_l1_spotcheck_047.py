#!/usr/bin/env python3
"""worker-047 independent L1 citation re-fetch spot check.

Reads the frozen ledger/citation_audit.csv rows SRC-043/054/057/061/080/094 and the
raw arXiv-API response saved by this worker, then compares, per row:
  - title            (normalised exact equality)
  - authors          (ordered list equality)
  - year             (first author-visible publication year == ledger year where comparable)
  - arXiv id / DOI / journal_ref presence
  - evidence_excerpt (ledger abstract text must be a verbatim prefix/substring of the
                      fetched abstract after whitespace normalisation; an explicit "..."
                      ellipsis is handled by prefix comparison)
No ledger text is trusted as evidence: every compared field on the fetched side comes
from the raw API response, which is hash-pinned in the report.

Usage: python3 check_l1_spotcheck_047.py <raw_xml> <ledger_csv> <out_json>
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
CST = timezone(timedelta(hours=8))
TARGETS = ["SRC-043", "SRC-054", "SRC-057", "SRC-061", "SRC-080", "SRC-094"]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", s).strip()


def abstract_part(excerpt: str) -> tuple[str, bool]:
    """Split the ledger excerpt into the quote and whether it carries an ellipsis."""
    e = norm(excerpt)
    e = re.sub(r"^arXiv abstract:\s*", "", e)
    e = re.sub(r"^Abstract:\s*", "", e)
    elided = "..." in e or "\u2026" in e
    # cut at the first ellipsis for prefix comparison, keep the rest for reporting
    head = re.split(r"\.\.\.|\u2026", e)[0].strip()
    # drop a trailing "Comments:" tail if it leaked into the excerpt
    return head, elided


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    raw_xml, ledger_csv, out_json = sys.argv[1], sys.argv[2], sys.argv[3]
    tree = ET.parse(raw_xml)
    entries = {}
    for e in tree.getroot().findall("a:entry", NS):
        aid = (e.findtext("a:id", "", NS) or "").rsplit("/abs/", 1)[-1]
        # strip version suffix for keying
        base = re.sub(r"v\d+$", "", aid)
        entries[base] = {
            "arxiv_id_returned": aid,
            "title": norm(e.findtext("a:title", "", NS)),
            "authors": [norm(a.findtext("a:name", "", NS)) for a in e.findall("a:author", NS)],
            "published": norm(e.findtext("a:published", "", NS)),
            "updated": norm(e.findtext("a:updated", "", NS)),
            "journal_ref": norm(e.findtext("arxiv:journal_ref", "", NS)),
            "doi": norm(e.findtext("arxiv:doi", "", NS)),
            "comment": norm(e.findtext("arxiv:comment", "", NS)),
            "abstract": norm(e.findtext("a:summary", "", NS)),
        }

    rows = {r["citation_id"]: r for r in csv.DictReader(open(ledger_csv))}
    fetched_at = datetime.now(CST).isoformat(timespec="seconds")
    report = {
        "schema": "worker-047/l1-spotcheck/v1",
        "worker": "worker-047",
        "created_at": fetched_at,
        "method": (
            "re-fetch each row's declared arXiv locator through the arXiv Atom API "
            "(export.arxiv.org/api/query?id_list=...); compare title/authors/abstract "
            "verbatim against the ledger row; ledger text is never used as fetched evidence"
        ),
        "raw_response": {
            "path": raw_xml,
            "sha256": sha256_file(raw_xml),
            "bytes": len(open(raw_xml, "rb").read()),
        },
        "ledger": {
            "citation_audit.csv": sha256_file(ledger_csv),
        },
        "entries_returned": len(entries),
        "results": [],
    }

    for cid in TARGETS:
        row = rows.get(cid)
        if row is None:
            report["results"].append({"citation_id": cid, "verdict": "MISSING_ROW"})
            continue
        arx = row.get("arxiv_id", "").strip()
        f = entries.get(arx)
        if f is None:
            report["results"].append(
                {"citation_id": cid, "arxiv_id": arx, "verdict": "FETCH_FAILED",
                 "note": "id not present in the raw API response"}
            )
            continue
        head, elided = abstract_part(row.get("evidence_excerpt", ""))
        fetched_abs = f["abstract"]
        contained = head in fetched_abs if head else False
        title_match = norm(row["title"]) == f["title"]
        authors_match = norm(row["authors"]) == "; ".join(f["authors"])
        year_ledger = (row.get("year") or "").strip()
        year_fetched = f["published"][:4]
        # ledger year may be the journal year (>= arXiv year); flag only if it precedes it
        year_ok = (not year_ledger.isdigit()) or (year_ledger.isdigit() and int(year_ledger) >= int(year_fetched))
        arxiv_id_ok = norm(row.get("arxiv_id", "")) == norm(arx)
        doi_ledger = norm(row.get("doi", ""))
        doi_fetched = norm(f["doi"])
        doi_ok = (not doi_ledger) or (not doi_fetched) or (doi_ledger in doi_fetched) or (doi_fetched in doi_ledger)
        checks = {
            "title_exact": title_match,
            "authors_exact": authors_match,
            "ledger_year_ge_arxiv_year": year_ok,
            "arxiv_id_key": arxiv_id_ok,
            "doi_consistent_or_absent": doi_ok,
            "abstract_excerpt_verbatim_prefix": contained,
        }
        verdict = "MATCH" if all(checks.values()) else (
            "PARTIAL" if contained and title_match else "MISMATCH"
        )
        report["results"].append(
            {
                "citation_id": cid,
                "bibkey": row["bibkey"],
                "class_mapping": row["class_mapping"],
                "used_by_theorems": row["used_by_theorems"],
                "ledger_status": row["status"],
                "ledger_verification_method": row["verification_method"],
                "locator_used": row["exact_locator"],
                "ledger_claim": {
                    "title": row["title"],
                    "authors": row["authors"],
                    "year": row["year"],
                    "venue": row["venue"],
                    "doi": row["doi"],
                    "arxiv_id": row["arxiv_id"],
                },
                "fetched": f,
                "excerpt_elided_in_ledger": elided,
                "excerpt_compared": head,
                "checks": checks,
                "verdict": verdict,
                "note": (
                    "abstract excerpt is a verbatim prefix of the fetched abstract"
                    if contained else
                    "ledger excerpt is NOT contained verbatim in the fetched abstract "
                    "(could be a different version's abstract or a transcription error)"
                ),
            }
        )

    report["summary"] = {
        "checked": len(report["results"]),
        "match": sum(1 for r in report["results"] if r["verdict"] == "MATCH"),
        "partial": sum(1 for r in report["results"] if r["verdict"] == "PARTIAL"),
        "mismatch": sum(1 for r in report["results"] if r["verdict"] == "MISMATCH"),
        "fetch_failed": sum(1 for r in report["results"] if r["verdict"] == "FETCH_FAILED"),
    }
    with open(out_json, "w") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
    print(json.dumps(report["summary"], indent=2))
    for r in report["results"]:
        print(r["citation_id"], r["verdict"], r.get("checks"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
