#!/usr/bin/env python3
"""W056-L1-SPOTCHECK-05 — independent live re-fetch spot check of ledger/citation_audit.csv.

Task: the third independent re-fetch spot check binding to the frozen L1 hash
      315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9
      (G-LIT criterion: ">=3 independent re-fetch spot checks").

Independence:
  * different actor (worker-056), own sampler, own comparators, live fetches;
  * sampling rule frozen in this file BEFORE any fetch (constant SAMPLE below);
  * frame 41-95 rows chosen to be disjoint from check #3 (flash-07: 41,49,57,65,73,80,81,89);
  * rows 4,25,33 are an independent re-test of check #4's (worker-086) three MISMATCH hard failures;
  * the ledger text is never used as evidence; only fetched primary/registry metadata is.

Verdict rule, declared before fetch (differences from check #4 are deliberate and stated):
  FETCH_FAILED  no successful live fetch for the row.
  MISMATCH      title state == mismatch, OR first-author surname absent from fetched authors,
                OR |ledger_year - fetched_year| > 1 for every fetched year candidate.
  PARTIAL       otherwise, if any of: title not exact, year off by 1 (issue/online convention),
                locator is a search query rather than an exact locator, or the ledger quote
                scores as a topical summary (< 0.6 similarity) against the fetched abstract.
  MATCH         title exact, author match, a fetched year equals the ledger year, exact locator,
                and no topical-summary quote finding.
  A missing or non-comparable quote (no abstract in the fetched record, no ledger quote) is
  recorded as an unassessed quote class, NOT escalated: a row is MISMATCH only if title,
  author or year fail, and PARTIAL only for the reasons listed above (this is where this
  check deliberately differs from check #4, which escalated quote/venue conventions).

Re-run:
  python3 artifacts/worker-056/l1_spotcheck/run_spotcheck_056.py
  # writes spotcheck-l1-056.json next to this file, raw fetch bodies under raw/
Fail-closed:
  exits 2 without fetching if the ledger hash != the frozen pin, or if the file drifts during fetch.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import time
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LEDGER = ROOT / "ledger" / "citation_audit.csv"
OUT = HERE / "spotcheck-l1-056.json"
RAW = HERE / "raw"
CST = timezone(timedelta(hours=8))

# ---- frozen before fetch ---------------------------------------------------
FROZEN_LEDGER_SHA = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
SAMPLE = [1, 4, 25, 33, 40, 45, 53, 61, 69, 77, 85, 93, 96]
SAMPLING_RULE = {
    "frozen_before_fetch": True,
    "S1_stride41_95_offset4": "every 8th data row of frame 41-95 starting at 45 -> 45,53,61,69,77,85,93 "
                              "(disjoint from check #3 rows 41,49,57,65,73,80,81,89)",
    "S2_boundary40": "row 40: last row of the 1-40 frame boundary, never sampled by checks #3/#4",
    "S3_retest_check4_hard_failures": "rows 4,25,33 re-fetched independently to test whether check #4's MISMATCH verdicts reproduce",
    "S4_control1": "row 1 (check #4 MATCH) as an instrument control",
    "S5_terminal96": "row 96, terminal frame, independent re-fetch",
    "sampled_rows": SAMPLE,
}
# ---------------------------------------------------------------------------

NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(s: str) -> str:
    import html as _html
    import unicodedata
    s = _html.unescape(s or "").lower()
    s = s.replace("λ", "lambda").replace("Λ", "lambda")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\\[a-z]+", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def fetch(url: str) -> dict:
    """Live fetch; raw body cached under raw/ and hashed. Never raises.

    Retries throttle/transient failures (429/5xx) up to 3 attempts with backoff, so a
    FETCH_FAILED verdict means the source is unreachable, not that we were rate-limited.
    """
    key = sha256_bytes(url.encode())[:16]
    last = None
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "w056-l1-spotcheck/1.0 (independent re-fetch; worker-056)",
                "Accept": "application/json, application/atom+xml, text/xml, */*",
            })
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read()
                code = r.status
            RAW.mkdir(parents=True, exist_ok=True)
            (RAW / f"{key}.body").write_bytes(body)
            return {"url": url, "http_status": code, "bytes": len(body), "attempts": attempt,
                    "sha256": sha256_bytes(body), "raw": f"raw/{key}.body", "error": None}
        except Exception as e:  # noqa: BLE001
            last = e
            code = getattr(e, "code", None)
            if attempt < 3 and (code in (429, 500, 502, 503, 504) or code is None):
                time.sleep(6 * attempt)
                continue
            break
    return {"url": url, "http_status": getattr(last, "code", None), "bytes": 0, "attempts": 3,
            "sha256": None, "raw": None, "error": f"{type(last).__name__}: {last}"}


def arxiv_meta(body: bytes) -> dict | None:
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return None
    entry = root.find("a:entry", NS)
    if entry is None:
        return None
    title = " ".join((entry.findtext("a:title", "", NS) or "").split())
    if not title or title.lower().startswith("error"):
        return None
    authors = [(a.findtext("a:name", "", NS) or "").strip() for a in entry.findall("a:author", NS)]
    published = entry.findtext("a:published", "", NS) or ""
    summary = " ".join((entry.findtext("a:summary", "", NS) or "").split())
    return {
        "source": "arxiv-api",
        "title": title,
        "authors": authors,
        "year": int(published[:4]) if published[:4].isdigit() else None,
        "published": published,
        "journal_ref": entry.findtext("arxiv:journal_ref", "", NS) or "",
        "doi": entry.findtext("arxiv:doi", "", NS) or "",
        "comment": entry.findtext("arxiv:comment", "", NS) or "",
        "abstract": summary,
        "id": entry.findtext("a:id", "", NS) or "",
    }


def arxiv_html_meta(body: bytes) -> dict | None:
    """Fallback primary fetch: arxiv.org/abs/<id> HTML citation_* meta tags.

    Used only when the export API is throttled (HTTP 429); still a live primary fetch.
    """
    import html as _html
    text = body.decode("utf-8", "replace")

    def meta(name: str) -> str:
        m = re.search(r'<meta[^>]*name="' + name + r'"[^>]*content="([^"]*)"', text, re.I)
        return _html.unescape(m.group(1)).strip() if m else ""

    title = meta("citation_title")
    if not title:
        return None
    authors = [_html.unescape(a).strip() for a in
               re.findall(r'<meta[^>]*name="citation_author"[^>]*content="([^"]*)"', text, re.I)]
    date = meta("citation_date")
    online = meta("citation_online_date")
    abstract = meta("citation_abstract")
    if not abstract:
        m = re.search(r'<blockquote[^>]*class="abstract[^"]*"[^>]*>(.*?)</blockquote>', text, re.S)
        if m:
            abstract = " ".join(re.sub(r"<[^>]+>", " ", _html.unescape(m.group(1))).split())
    def fix_author(a: str) -> str:
        a = _html.unescape(a).strip()
        if "," in a:  # arXiv meta uses "Family, Given"
            fam, _, given = a.partition(",")
            return f"{given.strip()} {fam.strip()}".strip()
        return a

    years = [int(x[:4]) for x in (date, online) if x[:4].isdigit()]
    return {
        "source": "arxiv-abs-html",
        "title": title,
        "authors": [fix_author(a) for a in authors],
        "year": max(years) if years else None,
        "years": sorted(set(years)),
        "published": date,
        "journal_ref": meta("citation_journal_title"),
        "doi": meta("citation_doi"),
        "comment": "",
        "abstract": abstract,
        "id": meta("citation_arxiv_id"),
    }


def crossref_meta(body: bytes) -> dict | None:
    try:
        d = json.loads(body)
    except ValueError:
        return None
    msg = d.get("message") or {}
    if not msg:
        return None
    titles = msg.get("title") or []
    authors = []
    for a in msg.get("author", []):
        name = " ".join(x for x in [a.get("given"), a.get("family")] if x).strip()
        if name:
            authors.append(name)
    years = []
    for key in ("issued", "published-print", "published-online", "created"):
        parts = (msg.get(key) or {}).get("date-parts") or []
        if parts and parts[0] and parts[0][0]:
            years.append(int(parts[0][0]))
    return {
        "source": "crossref-api",
        "title": (titles[0] if titles else "") or "",
        "authors": authors,
        "year": min(years) if years else None,
        "years": sorted(set(years)),
        "container": (msg.get("container-title") or [""])[0],
        "volume": msg.get("volume") or "",
        "page": msg.get("page") or "",
        "type": msg.get("type") or "",
        "doi": msg.get("DOI") or "",
    }


def title_state(ledger_title: str, fetched_title: str) -> str:
    a, b = norm(ledger_title), norm(fetched_title)
    if not a or not b:
        return "no-fetch-title"
    if a == b:
        return "exact"
    if len(a) >= 20 and (a.startswith(b) or b.startswith(a)):
        return "prefix"
    r = SequenceMatcher(None, a, b).ratio()
    return "close" if r >= 0.85 else "mismatch"


def surname(name: str) -> str:
    parts = norm(name).split()
    return parts[-1] if parts else ""


def author_state(ledger_authors: str, fetched_authors: list[str]) -> tuple[str, list[str], str]:
    first = (ledger_authors or "").split(";")[0].strip()
    s = surname(first)
    fetched_surnames = [surname(a) for a in fetched_authors]
    return ("match" if s and s in fetched_surnames else "mismatch"), fetched_surnames, s


def year_state(ledger_year: str, fetched_years: list[int]) -> tuple[str, list[int]]:
    try:
        ly = int(ledger_year)
    except (TypeError, ValueError):
        return "no-ledger-year", fetched_years
    if not fetched_years:
        return "no-fetch-year", fetched_years
    if ly in fetched_years:
        return "match", fetched_years
    if any(abs(ly - y) == 1 for y in fetched_years):
        return "off-by-one", fetched_years
    return "mismatch", fetched_years


def locator_kind(row: dict) -> str:
    """exact = URL of the specific work page; search_query = API/query URL that may match many works."""
    loc = (row.get("exact_locator") or "").strip()
    if not loc:
        return "absent"
    low = loc.lower()
    if any(s in low for s in ("api/query", "search_query", "inspirehep.net/api",
                              "?q=", "&q=", "sortby=", "/search?")):
        return "search_query"
    if "doi.org/10." in low or re.search(r"/(abs|pdf|articles|article|works|record)/", low):
        return "exact"
    return "other"


def quote_note(row: dict, abstract: str) -> dict:
    q = (row.get("evidence_excerpt") or "").strip()
    if not q:
        return {"similarity_first400": None, "class": "no-ledger-quote"}
    if not abstract:
        # registry/primary record carried no abstract: the quote is unassessed, not wrong
        return {"similarity_first400": None, "class": "no-fetch-abstract"}
    r = SequenceMatcher(None, q[:400].lower(), abstract[:400].lower()).ratio()
    cls = "verbatim" if r >= 0.9 else ("near" if r >= 0.6 else "topical-summary")
    return {"similarity_first400": round(r, 3), "class": cls}


def main() -> int:
    if not LEDGER.is_file():
        print("FAIL: ledger missing", file=sys.stderr)
        return 2
    sha_before = sha256_file(LEDGER)
    if sha_before != FROZEN_LEDGER_SHA:
        print(f"FAIL-CLOSED: ledger sha {sha_before} != frozen pin {FROZEN_LEDGER_SHA}; no fetch performed",
              file=sys.stderr)
        return 2
    with LEDGER.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 97:
        print(f"FAIL-CLOSED: expected 97 data rows, found {len(rows)}; no fetch performed", file=sys.stderr)
        return 2

    results = []
    for n in SAMPLE:
        row = rows[n - 1]
        cid = row.get("citation_id")
        arx = (row.get("arxiv_id") or "").strip()
        doi = (row.get("doi") or "").strip()
        fetches, metas = [], []
        if arx:
            f = fetch("https://export.arxiv.org/api/query?id_list=" + urllib.parse.quote(arx))
            fetches.append(f)
            if f["sha256"]:
                m = arxiv_meta((RAW / f["raw"].split("/")[-1]).read_bytes())
                if m:
                    metas.append(m)
            if not any(m["source"] == "arxiv-api" for m in metas):
                # export API throttled/unavailable -> live primary fallback, the abs page
                f = fetch("https://arxiv.org/abs/" + urllib.parse.quote(arx))
                fetches.append(f)
                if f["sha256"]:
                    m = arxiv_html_meta((RAW / f["raw"].split("/")[-1]).read_bytes())
                    if m:
                        metas.append(m)
        if doi:
            f = fetch("https://api.crossref.org/works/" + urllib.parse.quote(doi))
            fetches.append(f)
            if f["sha256"]:
                m = crossref_meta((RAW / f["raw"].split("/")[-1]).read_bytes())
                if m:
                    metas.append(m)
        if not fetches:
            f = fetch("https://api.crossref.org/works?query.bibliographic=" +
                      urllib.parse.quote(row.get("title", "")[:200]) + "&rows=1")
            fetches.append(f)
            if f["sha256"]:
                m = crossref_meta((RAW / f["raw"].split("/")[-1]).read_bytes())
                if m:
                    metas.append(m)

        # Prefer the journal/registry record for year+venue; arXiv for title/authors/abstract.
        primary = next((m for m in metas if m["source"] == "crossref-api"), None) or \
                  next((m for m in metas if m["source"] in ("arxiv-api", "arxiv-abs-html")), None)
        arx_meta = next((m for m in metas if m["source"] in ("arxiv-api", "arxiv-abs-html")), None)

        if primary is None:
            verdict = "FETCH_FAILED"
            tstate, astate, ystate, qnote, kind = "no-fetch", "no-fetch", "no-fetch", {}, locator_kind(row)
            fetched_years, fetched_surnames, abstract = [], [], ""
        else:
            tstate = title_state(row.get("title", ""), primary.get("title", ""))
            astate, fetched_surnames, _ = author_state(row.get("authors", ""), primary.get("authors", []))
            years = sorted(set(([primary["year"]] if primary.get("year") else []) +
                               (primary.get("years") or []) +
                               ([arx_meta["year"]] if arx_meta and arx_meta.get("year") else [])))
            ystate, fetched_years = year_state(row.get("year", ""), years)
            abstract = (arx_meta or {}).get("abstract", "") or ""
            qnote = quote_note(row, abstract)
            kind = locator_kind(row)
            if tstate == "mismatch" or astate == "mismatch" or ystate == "mismatch":
                verdict = "MISMATCH"
            elif (tstate != "exact" or ystate != "match" or kind != "exact"
                  or qnote.get("class") == "topical-summary"):
                verdict = "PARTIAL"
            else:
                verdict = "MATCH"

        results.append({
            "row": n,
            "citation_id": cid,
            "bibkey": row.get("bibkey"),
            "class_mapping": row.get("class_mapping"),
            "used_by_theorems": row.get("used_by_theorems"),
            "ledger": {k: row.get(k) for k in ("title", "authors", "year", "venue", "doi", "arxiv_id",
                                               "status", "verdict", "exact_locator")},
            "fetched": metas,
            "fetches": fetches,
            "states": {"title": tstate, "author": astate, "year": ystate,
                       "locator": kind, "quote": qnote.get("class")},
            "quote_check": qnote,
            "fetched_years": fetched_years,
            "fetched_author_surnames": fetched_surnames,
            "verdict": verdict,
        })
        print(f"  row {n:3d} {cid} -> {verdict} (title={tstate} author={astate} year={ystate} locator={kind})",
              file=sys.stderr)

    sha_after = sha256_file(LEDGER)
    counts: dict[str, int] = {}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    summary = {"checked": len(results), **{k: counts.get(k, 0) for k in
               ("MATCH", "PARTIAL", "MISMATCH", "FETCH_FAILED")},
               "locator_quality_notes": [{"citation_id": r["citation_id"],
                                          "exact_locator_kind": r["states"]["locator"]}
                                         for r in results if r["states"]["locator"] != "exact"]}
    hard = []
    for r in results:
        if r["verdict"] == "MISMATCH":
            primary = next((m for m in r["fetched"] if m["source"] == "crossref-api"), None) or \
                      (r["fetched"][0] if r["fetched"] else {})
            hard.append({"row": r["row"], "citation_id": r["citation_id"], "verdict": "MISMATCH",
                         "states": r["states"], "ledger_year": r["ledger"]["year"],
                         "fetched_years": r["fetched_years"],
                         "fetched_title": primary.get("title"),
                         "fetched_authors": primary.get("authors")})
    check4 = {4: "MISMATCH", 25: "MISMATCH", 33: "MISMATCH", 1: "MATCH"}
    retest = [{"row": r["row"], "check4_verdict": check4[r["row"]], "check5_verdict": r["verdict"],
               "states": r["states"]} for r in results if r["row"] in check4]

    out = {
        "schema_version": "0.1",
        "artifact_type": "l1_refetch_spotcheck",
        "task_id": "W056-L1-SPOTCHECK-05",
        "check_number": 5,
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "actor": "worker-056",
        "reviewer": "worker-056",
        "created_at": now(),
        "independence_note": ("Own sampler, own comparators, own live fetches. Frame 41-95 rows are disjoint from check #3; "
                              "rows 4/25/33 are an independent re-test of check #4's hard failures; row 1 is an instrument control; "
                              "ledger text was never used as evidence."),
        "independent_of": [
            "reviews/L1-spotcheck-10.json",
            "reviews/L1-spotcheck-11.json",
            "artifacts/worker-07/l1_spotcheck/spotcheck-l1-07.json",
            "artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json",
        ],
        "inputs": {
            "ledger/citation_audit.csv": {
                "frozen_pin": FROZEN_LEDGER_SHA,
                "sha256_before": sha_before,
                "sha256_after": sha_after,
                "stable_during_fetch": sha_before == sha_after,
                "data_rows": len(rows),
                "frame": "rows 40,45,53,61,69,77,85,93 (41-95) + rows 1,4,25,33 (1-40) + row 96 (terminal)",
            },
            "runner": {"path": "artifacts/worker-056/l1_spotcheck/run_spotcheck_056.py",
                       "sha256": sha256_file(Path(__file__).resolve())},
        },
        "sampling_rule": SAMPLING_RULE,
        "method": {
            "network": "live re-fetch, worker-056, stdlib urllib only",
            "arxiv_rows": "https://export.arxiv.org/api/query?id_list=<id> (Atom)",
            "doi_rows": "https://api.crossref.org/works/<doi> (registry metadata)",
            "raw_bodies": "cached under artifacts/worker-056/l1_spotcheck/raw/, sha256 in each fetch record",
            "title_compare": "case/punctuation/LaTeX-normalised exact, then prefix, then SequenceMatcher >= 0.85 = close",
            "author_compare": "first ledger author surname present in fetched author list",
            "year_compare": "ledger year vs union of Crossref issued/print/online/created years and arXiv v1 year",
            "quote_compare": "first-400-char SequenceMatcher against fetched abstract; topical summaries are a note, not a hard failure",
            "verdicts": "MATCH | PARTIAL | MISMATCH | FETCH_FAILED",
        },
        "summary": summary,
        "hard_failures": hard,
        "check4_retest": retest,
        "results": results,
        "non_claims": [
            "No gate verdict is set or proposed by this artifact; G-LIT remains pending with the controller.",
            "No ledger file was modified; the frozen hash is asserted before and after.",
            "Excerpt similarity is a quote-quality signal only; it is not treated as a citation hard failure.",
            "Class mapping topical consistency is not a scope verdict.",
        ],
        "falsifier": ("Any sampled row whose ledger title/author/year is not reproducible from a live fetch at hash "
                      "315c19145065, or ledger drift during the fetch window (voids the check). Each RETEST row's check5 "
                      "verdict is falsified by a re-fetch at the same row that contradicts it."),
        "frozen_pin_respected": sha_before == FROZEN_LEDGER_SHA and sha_before == sha_after,
    }
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2))
    print("wrote", OUT)
    return 0 if out["frozen_pin_respected"] else 2


if __name__ == "__main__":
    sys.exit(main())
