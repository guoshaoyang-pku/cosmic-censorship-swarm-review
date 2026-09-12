#!/usr/bin/env python3
"""L1 independent re-fetch spot check #4, reviewer worker-006.

Assignment: astra-life02-l1-spotcheck (node L1, gate G-LIT), which requires a spot
check that binds ledger/citation_audit.csv sha256 315c1914... and records the
fetched-source hash, the comparison verdict, the locator, and re-hashes the ledger
after the fetch.

Frozen sample rule (declared BEFORE any fetch; see sample_freeze.json):
  rows of ledger/citation_audit.csv such that
    (a) citation_id not in the covered set of spots #1-#3
        {SRC-002,004,006,009,011,014,022,024,025,031,041,049,057,065,073,080,081,089},
    (b) class_mapping contains AF-SCC-C0-VAC-GEN or AF-SCC-C2-VAC-GEN,
    (c) used_by_theorems intersects {T-304,T-305,T-401,T-526,T-527},
    (d) arxiv_id is non-empty.
  Selection is deterministic; it yields 8 rows.

Fail-closed:
  * abort if the csv sha256 != PIN,
  * abort if the csv changes between the pre-fetch and post-fetch hash,
  * a row counts as fetch_failed (never as MATCH) if the page is not a 200 with an
    abstract marker.

Fetch: curl -sSL https://arxiv.org/abs/<arxiv_id>  (the row's evidence_url form);
the sha256 recorded is that of the raw response bytes. This is an abstract/metadata
level check, not a page-level proof check.
"""
from __future__ import annotations

import csv
import hashlib
import html as html_mod
import json
import re
import subprocess
import sys
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
CSV_PATH = ROOT / "ledger" / "citation_audit.csv"
PIN = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
COVERED = {"SRC-002", "SRC-004", "SRC-006", "SRC-009", "SRC-011", "SRC-014",
           "SRC-022", "SRC-024", "SRC-025", "SRC-031", "SRC-041", "SRC-049",
           "SRC-057", "SRC-065", "SRC-073", "SRC-080", "SRC-081", "SRC-089"}
SCC = {"AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"}
THEO = {"T-304", "T-305", "T-401", "T-526", "T-527"}
CST = timezone(timedelta(hours=8))
RAW = HERE / "raw"
FREEZE = HERE / "sample_freeze.json"
REPORT = HERE / "spotcheck-006.json"
SAMPLE_RULE = ("uncovered by spots #1-#3 AND class_mapping contains AF-SCC-C0-VAC-GEN or "
               "AF-SCC-C2-VAC-GEN AND used_by_theorems intersects {T-304,T-305,T-401,T-526,T-527} "
               "AND arxiv_id non-empty; deterministic, sorted by citation_id")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def norm_text(s: str) -> str:
    s = html_mod.unescape(s)
    s = re.sub(r"\$[^$]*\$", lambda m: " " + m.group(0).strip("$") + " ", s)
    s = re.sub(r"\\(mathrm|text|mathcal|mathbf|mathbb|operatorname|displaystyle|tfrac|frac)", " ", s)
    s = s.replace("\\", " ").replace("{", " ").replace("}", " ").replace("^", " ").replace("_", " ")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def tokens(s: str):
    return norm_text(s).split()


def strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html_mod.unescape(s)).strip()


def parse_abs_page(page: str) -> dict:
    out = {}
    m = re.search(r'<h1 class="title[^"]*">(.*?)</h1>', page, re.S)
    if m:
        out["title"] = re.sub(r"^Title:\s*", "", strip_tags(m.group(1))).strip()
    m = re.search(r'<div class="authors">(.*?)</div>', page, re.S)
    if m:
        out["authors"] = re.sub(r"^Authors:\s*", "", strip_tags(m.group(1))).strip()
    m = re.search(r'<blockquote class="abstract[^"]*">(.*?)</blockquote>', page, re.S)
    if m:
        out["abstract"] = re.sub(r"^Abstract:\s*", "", strip_tags(m.group(1))).strip()
    m = re.search(r'<meta name="citation_date" content="([^"]+)"', page)
    if m:
        out["citation_date"] = m.group(1)
    m = re.search(r"\[v1\]\s*</a>\s*([^<]+)", page) or re.search(r"\[v1\]\s*([A-Z][a-z]{2}, [^<]+)", page)
    if m:
        out["v1_date"] = m.group(1).strip()
    # submission history spans (robust fallback)
    hist = re.findall(r"\[v(\d+)\]\s*(?:</a>)?\s*([A-Z][a-z]{2}, \d{1,2} [A-Z][a-z]{2} \d{4})", page)
    if hist:
        out["versions"] = [{"v": v, "date": d} for v, d in hist]
    return out


def excerpt_core(excerpt: str) -> str:
    s = excerpt.strip()
    s = re.sub(r"^Abstract:\s*", "", s)
    s = re.sub(r"^[‘'\"“]+", "", s)
    s = re.sub(r"[’'\"”]+$", "", s)
    s = re.split(r"\.\.\.|\u2026", s)[0]
    return s.strip()


def first_author_surname(authors: str) -> str:
    a = re.split(r";|,| and ", authors.strip())[0].strip()
    parts = [p for p in a.split() if p]
    return parts[-1] if parts else ""


def main() -> int:
    raw = CSV_PATH.read_bytes()
    pre = sha_bytes(raw)
    if pre != PIN:
        print(f"FAIL-CLOSED: csv sha256 {pre} != pin {PIN}")
        return 2
    rows = list(csv.DictReader(raw.decode("utf-8").splitlines()))

    if FREEZE.exists():
        freeze = json.loads(FREEZE.read_text())
        if freeze.get("csv_sha256") != PIN:
            print("FAIL-CLOSED: existing freeze has a different pin")
            return 2
        ids = freeze["sample_ids"]
    else:
        ids = sorted(r["citation_id"] for r in rows
                     if r["citation_id"] not in COVERED
                     and (set(r["class_mapping"].split(";")) & SCC)
                     and (set(x.strip() for x in r["used_by_theorems"].split(";")) & THEO)
                     and r["arxiv_id"])
        freeze = {"task_id": "astra-life02-l1-spotcheck", "reviewer": "worker-006",
                  "frozen_at": now(), "csv_path": "ledger/citation_audit.csv",
                  "csv_sha256": PIN, "sample_rule": SAMPLE_RULE,
                  "covered_by_spots_1_3": sorted(COVERED), "sample_ids": ids,
                  "note": "sample fixed before any fetch; raw responses hashed on receipt"}
        FREEZE.write_text(json.dumps(freeze, indent=2) + "\n")
        print(f"froze sample ({len(ids)} rows) at {freeze['frozen_at']}: {ids}")

    by_id = {r["citation_id"]: r for r in rows}
    RAW.mkdir(parents=True, exist_ok=True)
    results = []
    for cid in ids:
        r = by_id[cid]
        aid = r["arxiv_id"].strip()
        url = f"https://arxiv.org/abs/{aid}"
        dest = RAW / f"{cid}_{aid}.html"
        proc = subprocess.run(["curl", "-sSL", "-m", "45", "-A",
                               "ai4math-swarm-spotcheck/1.0 (research verification)",
                               "-o", str(dest), "-w", "%{http_code} %{size_download} %{url_effective}", url],
                              capture_output=True, text=True)
        parts = (proc.stdout or "").split()
        http = parts[0] if parts else "000"
        nbytes = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        effective = parts[2] if len(parts) > 2 else url
        fetched_at = now()
        page = dest.read_text(errors="replace") if dest.exists() else ""
        fsha = sha_bytes(dest.read_bytes()) if dest.exists() else None
        parsed = parse_abs_page(page) if http == "200" else {}
        ok = http == "200" and bool(parsed.get("abstract")) and bool(parsed.get("title"))
        row = {"citation_id": cid, "arxiv_id": aid, "locator": url,
               "effective_url": effective, "http_status": http, "bytes": nbytes,
               "fetched_at": fetched_at, "fetched_sha256": fsha,
               "ledger_title": r["title"], "ledger_authors": r["authors"],
               "ledger_year": r["year"], "ledger_excerpt": r["evidence_excerpt"],
               "ledger_used_by": r["used_by_theorems"], "ledger_classes": r["class_mapping"]}
        if not ok:
            row.update({"verdict": "FETCH_FAILED",
                        "notes": f"http={http} bytes={nbytes}; no abstract marker parsed"})
            results.append(row)
            time.sleep(1.5)
            continue
        row["fetched_title"] = parsed.get("title")
        row["fetched_authors"] = parsed.get("authors")
        row["fetched_v1_date"] = parsed.get("v1_date") or parsed.get("citation_date")
        row["fetched_abstract"] = parsed.get("abstract")
        title_match = norm_text(parsed["title"]) == norm_text(r["title"])
        surname = first_author_surname(r["authors"])
        author_match = norm_text(surname) in norm_text(parsed.get("authors", ""))
        core = excerpt_core(r["evidence_excerpt"])
        lt, ft = tokens(core), tokens(parsed.get("abstract", ""))
        k = min(12, len(lt))
        lead = lt[:k]
        contiguous = any(ft[i:i + len(lead)] == lead for i in range(0, max(0, len(ft) - len(lead) + 1)))
        present = sum(1 for t in lt if t in set(ft)) / max(1, len(lt))
        if contiguous:
            grounding = "GROUNDED"
        elif present >= 0.8:
            grounding = "PARTIAL"
        else:
            grounding = "NOT_GROUNDED"
        if title_match and author_match and grounding == "GROUNDED":
            verdict = "MATCH"
        elif author_match and not title_match and grounding == "GROUNDED":
            verdict = "PARTIAL"
        elif not author_match:
            verdict = "FAIL"
        else:
            verdict = "PARTIAL"
        row.update({"fetched_title": parsed.get("title"), "title_match": title_match,
                    "first_author_match": author_match,
                    "ledger_year_vs_fetched": f"{r['year']} vs {row['fetched_v1_date']}",
                    "excerpt_grounding": grounding,
                    "excerpt_token_present_frac": round(present, 4),
                    "excerpt_lead12_contiguous": contiguous,
                    "verdict": verdict,
                    "notes": ("abstract-level token comparison; version/year columns may follow "
                              "journal vs preprint convention")})
        results.append(row)
        time.sleep(1.5)

    post = sha_bytes(CSV_PATH.read_bytes())
    stable = post == PIN
    summary = {"checked": len(results),
               "match": sum(1 for r in results if r["verdict"] == "MATCH"),
               "partial": sum(1 for r in results if r["verdict"] == "PARTIAL"),
               "fail": sum(1 for r in results if r["verdict"] == "FAIL"),
               "fetch_failed": sum(1 for r in results if r["verdict"] == "FETCH_FAILED")}
    report = {
        "task_id": "astra-life02-l1-spotcheck", "reviewer": "worker-006",
        "artifact": "artifacts/worker-006/l1_spotcheck/spotcheck-006.json",
        "created_at": now(),
        "target": {"path": "ledger/citation_audit.csv", "sha256": PIN,
                   "sha256_after_fetch": post, "stable_during_fetch": stable},
        "sample_rule": SAMPLE_RULE, "sample_frozen_at": freeze["frozen_at"],
        "sample_size": len(results), "fetch_method":
            "curl -sSL https://arxiv.org/abs/<arxiv_id>; sha256 of raw response bytes",
        "comparison_method": ("abstract/metadata level: normalized title equality; first-author "
                              "surname containment; excerpt lead-token contiguity/presence; "
                              "no page-level full-text check"),
        "scope_note": ("one independent re-fetch spot check (reviewer worker-006, distinct from "
                       "deepseek-flash-07) binding csv sha256 " + PIN[:12] + "; it does not set a "
                       "gate verdict and does not promote any theorem"),
        "summary": summary, "results": results,
        "falsifier": ("a re-fetch of any pinned locator that resolves to a different work, or an "
                      "excerpt not grounded in the fetched abstract, turns the corresponding MATCH "
                      "into FAIL; a csv hash that is not " + PIN[:12] + " voids the check; a "
                      "page-level check contradicting a MATCH also falsifies it"),
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"summary": summary, "csv_stable": stable,
                      "verdicts": {r["citation_id"]: r["verdict"] for r in results}}, indent=1))
    return 0 if stable else 3


if __name__ == "__main__":
    sys.exit(main())
