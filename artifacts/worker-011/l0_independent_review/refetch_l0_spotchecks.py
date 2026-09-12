#!/usr/bin/env python3
"""Independent live re-fetch corroboration of the L0 spot checks (reviewer worker-011).

Re-fetches the four locators that the literature lead's independent subagent reported
(SRC-002, SRC-004, SRC-057, SRC-059) from a *different process at a different time*,
saves the raw bytes under this artifact directory, and compares the live
title/author/year against the recorded values in ledger/citation_audit.csv.

This does not re-implement the lead's tooling; it is a second, independent channel.
Writes only under artifacts/worker-011/l0_independent_review/.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import unicodedata
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
OUT = ROOT / "artifacts/worker-011/l0_independent_review/refetch"
OUT.mkdir(parents=True, exist_ok=True)
AUDIT = ROOT / "ledger/citation_audit.csv"

TARGETS = {
    "SRC-002": "https://arxiv.org/abs/1912.08478",
    "SRC-004": "https://arxiv.org/abs/1710.01722",
    "SRC-057": "https://arxiv.org/abs/1702.05715",
    "SRC-059": "https://api.crossref.org/works/10.4007/annals.2009.170.1181",
}


def fetch(url: str):
    name = re.sub(r"[^A-Za-z0-9]+", "_", url)[-70:]
    dest = OUT / f"{name}.raw"
    r = subprocess.run(
        ["curl", "-sS", "-L", "--max-time", "40", "-A",
         "worker-011-independent-verify/1.0 (research audit)", "-w", "%{http_code}", url],
        capture_output=True, text=True)
    body = r.stdout
    code = body[-3:] if body[-3:].isdigit() else "?"
    payload = body[:-3]
    dest.write_text(payload)
    return code, payload, dest


def clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def parse_arxiv(payload: str):
    title = authors = year = None
    m = re.search(r'<h1 class="title[^"]*">(.*?)</h1>', payload, re.S)
    if m:
        title = clean(re.sub(r'<span class="descriptor">.*?</span>', "", m.group(1), flags=re.S))
    m = re.search(r'<div class="authors">(.*?)</div>', payload, re.S)
    if m:
        authors = clean(m.group(1))
    m = re.search(r'\[Submitted on ([^\]<]+)\]', payload)
    if m:
        ym = re.search(r"(\d{4})", m.group(1))
        year = ym.group(1) if ym else None
    return title, authors, year


def parse_crossref(payload: str):
    try:
        msg = json.loads(payload)["message"]
    except Exception:  # noqa: BLE001
        return None, None, None
    # Crossref titles/author names may carry HTML markup and diacritics; clean here so the
    # comparison tests the record, not the encoding.
    title = clean((msg.get("title") or [None])[0] or "") or None
    authors = "; ".join(f"{a.get('family','')}" for a in msg.get("author", [])) or None
    authors = clean(authors) if authors else None
    parts = (msg.get("published-print") or msg.get("published") or {}).get("date-parts", [[None]])
    year = str(parts[0][0]) if parts and parts[0] else None
    return title, authors, year


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def main() -> int:
    audit = {r["citation_id"]: r for r in csv.DictReader(AUDIT.open())}
    results = []
    for sid, url in TARGETS.items():
        rec = audit[sid]
        code, payload, dest = fetch(url)
        raw_sha = hashlib.sha256(dest.read_bytes()).hexdigest()
        if "crossref" in url:
            live_title, live_authors, live_year = parse_crossref(payload)
        else:
            live_title, live_authors, live_year = parse_arxiv(payload)
        title_match = norm(live_title) == norm(rec["title"]) or \
            norm(rec["title"]) in norm(live_title) or norm(live_title) in norm(rec["title"])
        # author comparison: live records may carry only family names (Crossref) or the full
        # list (arXiv, with an "Authors:" descriptor); require the recorded author string to
        # contain each live author name.
        rec_norm = norm(rec["authors"])
        live_clean = re.sub(r"^\s*Authors:\s*", "", live_authors or "")
        live_names = [x.strip(" .") for x in re.split(r"[;,]", live_clean)
                      if norm(x) and norm(x) != "authors"]
        author_match = bool(live_names) and all(norm(x) in rec_norm for x in live_names)
        year_match = (str(rec["year"]) == str(live_year)) if live_year else None
        results.append({
            "source_id": sid,
            "locator": url,
            "http_status": code,
            "raw_sha256": raw_sha,
            "raw_path": str(dest.relative_to(ROOT)),
            "recorded_title": rec["title"],
            "live_title": live_title,
            "title_match": bool(title_match),
            "recorded_authors": rec["authors"],
            "live_authors": live_authors,
            "author_match": bool(author_match),
            "recorded_year": rec["year"],
            "live_year": live_year,
            "year_match": year_match,
            "recorded_evidence_type": rec["evidence_type"],
            "recorded_verdict": rec["verdict"],
        })
    ok = all(r["http_status"] == "200" and r["title_match"] and r["author_match"] for r in results)
    report = {
        "kind": "independent_live_refetch",
        "reviewer": "worker-011",
        "fetched_at": datetime.now(CST).isoformat(timespec="seconds"),
        "method": ("curl from a fresh process (worker-011) against the locators recorded in "
                   "ledger/citation_audit.csv; raw bytes retained and hashed"),
        "targets": len(results),
        "all_matched": ok,
        "contradictions": [r["source_id"] for r in results if not (r["http_status"] == "200" and r["title_match"] and r["author_match"])],
        "results": results,
    }
    dest = ROOT / "artifacts/worker-011/l0_independent_review/refetch_report.json"
    dest.write_text(json.dumps(report, indent=2) + "\n")
    print(f"independent refetch: {sum(1 for r in results if r['title_match'] and r['author_match'] and r['http_status']=='200')}/{len(results)} matched")
    for r in results:
        print(f"  {r['source_id']} HTTP {r['http_status']} title={r['title_match']} author={r['author_match']} year={r['year_match']} sha={r['raw_sha256'][:12]}")
    print(f"report: {dest.relative_to(ROOT)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
