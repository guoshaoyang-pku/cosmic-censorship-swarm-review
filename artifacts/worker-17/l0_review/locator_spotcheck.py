#!/usr/bin/env python3
"""Independent locator spot-check for the L0 review (worker-17).

Picks a fixed, pre-declared stride sample of registry source_ids and re-resolves
their locators against live Crossref / arXiv APIs, comparing the returned title
and year against the bytes on disk. Read-only over canonical artifacts.
"""
from __future__ import annotations

import difflib
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
OUT = Path(__file__).resolve().parent
REG = ROOT / "artifacts" / "literature" / "registry.jsonl"

# Pre-declared sample: every 24th source in file order (0-based 1,25,49,73,97-1)
SAMPLE_IDX = [0, 24, 48, 72, 96]


def get(url: str, timeout: int = 30) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "worker-017-l0-audit/1.0 (mailto:none@example.org)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return 0, f"ERROR: {e}"


def main() -> int:
    reg = [json.loads(l) for l in REG.read_text().splitlines() if l.strip()]
    rows = [reg[i] for i in SAMPLE_IDX]
    out: dict = {
        "check": "live locator re-resolution spot-check",
        "registry_sha256": __import__("hashlib").sha256(REG.read_bytes()).hexdigest(),
        "sample_rule": "file-order indices " + str(SAMPLE_IDX),
        "checked_at": datetime.now(CST).isoformat(timespec="seconds"),
        "sources": [],
    }
    for r in rows:
        sid = r["source_id"]
        doi = (r.get("doi") or "").strip()
        ax = (r.get("arxiv_id") or "").strip()
        rec = {"source_id": sid, "disk_title": r["title"], "disk_year": r["year"],
               "disk_status": r["status"], "disk_evidence_type": (r.get("verification") or {}).get("evidence_type")}
        if doi and not doi.startswith("10.48550/arXiv"):
            code, body = get("https://api.crossref.org/works/" + urllib.parse.quote(doi))
            rec["query"] = f"crossref:{doi}"
            rec["http"] = code
            if code == 200:
                msg = json.loads(body)["message"]
                rec["returned_title"] = (msg.get("title") or [""])[0]
                dp = (msg.get("published-print") or msg.get("published") or {}).get("date-parts", [[None]])
                rec["returned_year"] = dp[0][0]
            else:
                rec["returned_title"] = body[:200]
        elif ax:
            code, body = get(f"http://export.arxiv.org/api/query?id_list={ax}&max_results=1")
            rec["query"] = f"arxiv:{ax}"
            rec["http"] = code
            if code == 200:
                import re
                t = re.search(r"<entry>.*?<title>(.*?)</title>", body, re.S)
                d = re.search(r"<entry>.*?<published>(\d{4})-", body, re.S)
                rec["returned_title"] = " ".join(t.group(1).split()) if t else None
                rec["returned_year"] = int(d.group(1)) if d else None
            else:
                rec["returned_title"] = body[:200]
        else:
            rec["query"] = "none"
            rec["http"] = None
        if isinstance(rec.get("returned_title"), str) and rec["returned_title"]:
            rec["title_ratio"] = round(difflib.SequenceMatcher(
                None, rec["disk_title"].lower(), rec["returned_title"].lower()).ratio(), 3)
            rec["title_match_ge_0.85"] = rec["title_ratio"] >= 0.85
            rec["year_match"] = rec.get("returned_year") in (None, r["year"])
        out["sources"].append(rec)
    out["summary"] = {
        "n": len(rows),
        "http_200": sum(1 for s in out["sources"] if s.get("http") == 200),
        "title_match_ge_0.85": sum(1 for s in out["sources"] if s.get("title_match_ge_0.85")),
        "year_mismatch": [s["source_id"] for s in out["sources"] if s.get("year_match") is False],
    }
    (OUT / "locator_spotcheck.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["summary"], indent=1))
    for s in out["sources"]:
        print(s["source_id"], s.get("http"), s.get("title_ratio"), s.get("year_match"),
              "|", str(s.get("returned_title"))[:70])
    return 0


if __name__ == "__main__":

    raise SystemExit(main())
