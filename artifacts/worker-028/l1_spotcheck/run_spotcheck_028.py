#!/usr/bin/env python3
"""Independent L1 re-fetch spot check #5 (worker-028), revision 3.

Bounded task: re-fetch primary locators for a pre-frozen sample of rows of
ledger/citation_audit.csv at the frozen sha256 and report MATCH / PARTIAL /
MISMATCH / FETCH_FAILED. No gate verdict, no node completion, no ledger edits.

Sample: every 8th data row of frame 1-97 starting at row 5
        -> 5,13,21,29,37,45,53,61,69,77,85,93
disjoint from the union of rows already checked at this hash by spot checks
#3 (worker-07: 41,49,57,65,73,80,81,89) and #4 (worker-086:
1,4,9,16,17,25,33,96,97). The sample was frozen before any fetch.

v2/v3 revision note (instrument control): v1 of this script was discarded before
emitting any event because its excerpt comparator used difflib.SequenceMatcher
with autojunk=True on character sequences (ratio collapses to ~0.0-0.1 on long
strings), compared ledger years only against the arXiv submission year, did not
fold accents in author names, and treated a missing Crossref abstract as a
content mismatch. v2 fixes: autojunk=False + containment test, union of years
across all successfully fetched sources, NFKD accent folding, surname matching,
Crossref-metadata-only rows classified PARTIAL (content excerpt not independently
verifiable), arXiv abs-page fallback on API 429, retry/backoff. v3 fixes the
author control: the arXiv abs page returns 'Family, Given' while Crossref returns
'Given Family' and v2 checked only the first successful source, producing three
false author MISMATCHes; v3 tests the first ledger author surname against the
union of all fetched sources in both name orders. Each revision was driven by a
control row with independently known metadata, not by a desired outcome.
Discarded outputs were overwritten and never sent upward.

Method: live network fetch of the primary locator (arXiv API for rows with an
arXiv id, Crossref API for DOI-only rows); ledger text is never used as
evidence. Raw response bytes are hashed. The ledger hash is re-checked after
all fetches; any drift aborts fail-closed.
"""
from __future__ import annotations

import csv
import difflib
import hashlib
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "ledger" / "citation_audit.csv"
ART = ROOT / "artifacts" / "worker-028" / "l1_spotcheck" / "spotcheck-l1-028.json"
PIN = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
SAMPLE = [5, 13, 21, 29, 37, 45, 53, 61, 69, 77, 85, 93]
PRIOR_UNION = [1, 4, 9, 16, 17, 25, 33, 41, 49, 57, 65, 73, 80, 81, 89, 96, 97]
CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
CST = timezone(timedelta(hours=8))
UA = "l1-spotcheck-worker-028/0.2 (independent citation verification; stdlib urllib)"
EXCERPT_MATCH, EXCERPT_PARTIAL = 0.50, 0.30


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def sim(a: str, b: str) -> float:
    """Character similarity with autojunk disabled (v1 bug: autojunk collapses)."""
    a, b = norm(a)[:400], norm(b)[:400]
    if not a or not b:
        return 0.0
    return round(difflib.SequenceMatcher(None, a, b, autojunk=False).ratio(), 4)


def http_get(url: str, timeout: int = 45, tries: int = 3, delay: float = 4.0):
    last = None
    t0 = time.time()
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body, status = r.read(), r.status
            return body, status, round(time.time() - t0, 2)
        except Exception as exc:  # noqa: BLE001 - retried, then surfaced
            last = exc
            if i < tries - 1:
                time.sleep(delay * (i + 1))
    raise last


def clean_excerpt(s: str) -> tuple[str, str]:
    """Return (cleaned_quote, kind)."""
    raw = (s or "").strip()
    if re.match(r"^INSPIRE recid \d+", raw, flags=re.I):
        return raw, "record-line"
    c = re.sub(r"^(?:[A-Za-z][A-Za-z ]{0,20})?abstract\s*:\s*", "", raw, flags=re.I)
    c = re.sub(r"^\W+", "", c).strip().strip("\"'").strip()
    return c, "quote"


def excerpt_state(excerpt: str, abstract: str) -> tuple[str, dict]:
    quote, kind = clean_excerpt(excerpt)
    info = {"excerpt_kind": kind, "quote_head": quote[:100]}
    if not abstract:
        info["reason"] = "fetched source carries no abstract (metadata-only record)"
        return "not_available", info
    if kind == "record-line":
        info["reason"] = "ledger excerpt is a bibliographic record pointer, not quotable evidence"
        return "record-line", info
    q, ab = norm(quote), norm(abstract)
    if not q:
        return "unverifiable", info
    if len(q) >= 60 and q[:120] in ab:
        info["test"] = "containment_first120"
        return "match", info
    scores = [sim(q[:400], ab[:400]), sim(q[-250:], ab[-400:])]
    info["similarity"] = max(scores)
    info["test"] = "sequence_similarity_autojunk_false"
    best = max(scores)
    return ("match" if best >= EXCERPT_MATCH else
            "partial" if best >= EXCERPT_PARTIAL else "mismatch"), info


def fetch_arxiv(aid: str) -> dict:
    url = "https://export.arxiv.org/api/query?id_list=" + urllib.parse.quote(aid)
    out = {"kind": "arxiv-api", "url": url, "ok": False}
    try:
        body, status, secs = http_get(url)
        out.update({"http_status": status, "bytes": len(body),
                    "sha256": hashlib.sha256(body).hexdigest(), "seconds": secs})
        ns = {"a": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(body)
        e = root.find("a:entry", ns)
        if e is None:
            raise ValueError("no entry")
        title = " ".join((e.findtext("a:title", default="", namespaces=ns)).split())
        authors = [x.findtext("a:name", default="", namespaces=ns)
                   for x in e.findall("a:author", ns)]
        summary = " ".join((e.findtext("a:summary", default="", namespaces=ns)).split())
        published = e.findtext("a:published", default="", namespaces=ns)
        out.update({"ok": bool(title), "title": title,
                    "authors": [a for a in authors if a], "abstract": summary,
                    "years": [int(published[:4])] if published[:4].isdigit() else [],
                    "container_title": "arXiv", "via": "api"})
    except Exception as exc:  # noqa: BLE001
        out["api_error"] = f"{type(exc).__name__}: {exc}"
        # fallback: abs page (works when the API is rate-limiting)
        try:
            url2 = "https://arxiv.org/abs/" + urllib.parse.quote(aid)
            body, status, secs = http_get(url2)
            html = body.decode("utf-8", "replace")
            def meta(name):
                m = re.search(rf'<meta\s+name="{name}"\s+content="([^"]*)"', html)
                return m.group(1) if m else ""
            title = meta("citation_title")
            authors = re.findall(r'<meta\s+name="citation_author"\s+content="([^"]*)"', html)
            m = re.search(r'<blockquote class="abstract[^"]*">(.*?)</blockquote>', html, re.S)
            abstract = re.sub(r"<[^>]+>", " ", m.group(1)) if m else ""
            date = meta("citation_date") or meta("citation_online_date")
            out.update({"kind": "arxiv-abs-page", "url": url2, "http_status": status,
                        "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                        "seconds": secs, "ok": bool(title), "title": title,
                        "authors": authors,
                        "abstract": " ".join(abstract.split()),
                        "years": [int(date[:4])] if date[:4].isdigit() else [],
                        "container_title": "arXiv", "via": "abs-page"})
        except Exception as exc2:  # noqa: BLE001
            out["error"] = f"api: {out['api_error']}; abs-page: {type(exc2).__name__}: {exc2}"
    return out


def fetch_crossref(doi: str) -> dict:
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    out = {"kind": "crossref", "url": url, "ok": False}
    try:
        body, status, secs = http_get(url)
        out.update({"http_status": status, "bytes": len(body),
                    "sha256": hashlib.sha256(body).hexdigest(), "seconds": secs})
        msg = json.loads(body)["message"]
        years = []
        for key in ("issued", "published", "published-online", "published-print"):
            dp = (msg.get(key) or {}).get("date-parts") or []
            if dp and dp[0] and isinstance(dp[0][0], int):
                years.append(dp[0][0])
        out.update({
            "ok": True, "title": (msg.get("title") or [""])[0],
            "authors": [f"{a.get('given','')} {a.get('family','')}".strip()
                        for a in (msg.get("author") or [])],
            "abstract": re.sub(r"<[^>]+>", " ", msg.get("abstract") or ""),
            "years": sorted(set(years)),
            "container_title": (msg.get("container-title") or [""])[0],
        })
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def surname(name: str) -> str:
    n = norm(name)
    return n.split()[-1] if n else ""


def ledger_surnames(field: str) -> list[str]:
    return [surname(a) for a in re.split(r";| and |,", field or "") if surname(a)]


def author_candidates(authors: list[str]) -> set[str]:
    """Candidate surnames across 'Given Family' and 'Family, Given' formats."""
    out: set[str] = set()
    for a in authors or []:
        n = norm(a)
        if not n:
            continue
        toks = n.split()
        out.add(toks[-1])
        if "," in a:
            out.add(toks[0])
    return out


def author_state(row: dict, fetches: list[dict]) -> bool:
    """First ledger author surname must occur in the union of all fetched sources
    (the arXiv abs page returns 'Family, Given'; Crossref returns 'Given Family')."""
    led = ledger_surnames(row.get("authors", ""))
    got: set[str] = set()
    for f in fetches:
        if f.get("ok"):
            got |= author_candidates(f.get("authors") or [])
    return bool(led) and led[0] in got


def compare(row: dict, fetches: list[dict]) -> dict:
    ok_fetches = [f for f in fetches if f.get("ok")]
    primary = ok_fetches[0]
    all_years = sorted({y for f in ok_fetches for y in (f.get("years") or [])})
    ledger_year = int(row["year"]) if str(row.get("year", "")).isdigit() else None
    states: dict = {}
    states["title"] = bool(primary.get("title")) and (
        norm(row["title"]) == norm(primary["title"])
        or norm(row["title"])[:45] == norm(primary["title"])[:45]
        or sim(row["title"], primary["title"]) > 0.90)
    states["author"] = author_state(row, fetches)
    if ledger_year is None or not all_years:
        states["year"] = None
    elif ledger_year in all_years:
        states["year"] = "exact"
    elif min(abs(ledger_year - y) for y in all_years) == 1:
        states["year"] = "off-by-one"
    else:
        states["year"] = "mismatch"
    states["years_fetched"] = all_years
    # excerpt: prefer a fetched source that carries an abstract
    with_abs = next((f for f in ok_fetches if f.get("abstract")), None)
    if with_abs is None:
        states["excerpt"], states["excerpt_info"] = "not_available", {
            "reason": "no successfully fetched source carries an abstract (metadata-only)"}
    else:
        states["excerpt"], states["excerpt_info"] = excerpt_state(
            row.get("evidence_excerpt", ""), with_abs.get("abstract", ""))
        states["excerpt_source"] = with_abs["kind"]
    hard = (not states["title"]) or (not states["author"]) or states["year"] == "mismatch" \
        or states["excerpt"] == "mismatch"
    soft = states["year"] == "off-by-one" or states["excerpt"] in (
        "partial", "not_available", "record-line", "unverifiable")
    return {"states": states, "verdict": "MISMATCH" if hard else
            "PARTIAL" if soft else "MATCH"}


def main() -> int:
    before = sha_file(LEDGER)
    if before != PIN:
        print(json.dumps({"abort": "ledger hash drift before fetch", "expected": PIN,
                          "measured": before}), file=sys.stderr)
        return 2
    rows = list(csv.DictReader(open(LEDGER, newline="", encoding="utf-8")))
    if len(rows) != 97:
        print(json.dumps({"abort": "unexpected data row count", "n": len(rows)}), file=sys.stderr)
        return 2
    assert not (set(SAMPLE) & set(PRIOR_UNION)), "sample not disjoint from prior checks"

    results, hard_failures, findings = [], [], []
    for r in SAMPLE:
        row = rows[r - 1]
        entry = {"row": r, "citation_id": row["citation_id"],
                 "class_mapping": row.get("class_mapping", ""),
                 "ledger": {k: row.get(k, "") for k in
                            ("title", "authors", "year", "venue", "doi", "arxiv_id",
                             "exact_locator", "evidence_url", "evidence_excerpt",
                             "used_by_theorems", "verdict")},
                 "fetches": [], "fetch_ok": False}
        fetches = []
        if row.get("arxiv_id"):
            fetches.append(fetch_arxiv(row["arxiv_id"].strip()))
            time.sleep(3.0)  # arXiv API rate courtesy
        doi = (row.get("doi") or "").strip()
        if doi and not doi.lower().startswith("10.48550/"):
            fetches.append(fetch_crossref(doi))
        ok = [f for f in fetches if f.get("ok")]
        entry["fetches"] = fetches
        if not ok:
            entry["verdict"] = "FETCH_FAILED"
        else:
            entry["fetch_ok"] = True
            entry["primary_source"] = ok[0]["kind"]
            entry["comparison"] = compare(row, fetches)
            entry["verdict"] = entry["comparison"]["verdict"]
            if entry["verdict"] == "MISMATCH":
                hard_failures.append({
                    "citation_id": row["citation_id"], "row": r,
                    "class_mapping": row.get("class_mapping", ""),
                    "primary_source": ok[0]["kind"],
                    "detail": entry["comparison"]["states"]})
        if not str(row.get("exact_locator", "")).startswith("http"):
            findings.append(f"{row['citation_id']} exact_locator is not a direct URL: "
                            f"{row.get('exact_locator','')[:70]!r}")
        _q, _kind = clean_excerpt(row.get("evidence_excerpt", ""))
        if _kind == "record-line":
            findings.append(f"{row['citation_id']} evidence_excerpt is a bibliographic "
                            "record pointer, not quotable evidence")
        if entry.get("comparison", {}).get("states", {}).get("excerpt") == "not_available":
            findings.append(f"{row['citation_id']} excerpt not content-verifiable from the "
                            "fetched metadata; needs a source carrying the quoted text")
        results.append(entry)

    after = sha_file(LEDGER)
    stable = after == before
    summary = {"checked": len(results), "MATCH": 0, "PARTIAL": 0, "MISMATCH": 0,
               "FETCH_FAILED": 0}
    for e in results:
        summary[e["verdict"]] += 1
    artifact = {
        "schema_version": "0.1",
        "artifact_type": "l1_refetch_spotcheck",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": CLASS_IDS,
        "actor": "worker-028",
        "reviewer": "worker-028",
        "created_at": now(),
        "check_number": 5,
        "revision": 3,
        "revision_note": ("v1/v2 were discarded before any event: v1's excerpt comparator "
                          "used SequenceMatcher autojunk=True on character sequences and "
                          "compared year only against the arXiv submission year; v2 checked "
                          "authors only in the first fetched source, so 'Family, Given' "
                          "abs-page names produced three false MISMATCHes. v3 tests authors "
                          "against the union of all fetched sources in both name orders. "
                          "Discarded outputs were overwritten and never sent upward; the "
                          "script docstring lists every revision."),
        "independent_of": [
            "artifacts/worker-07/l1_spotcheck/spotcheck-l1-07.json",
            "artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json",
        ],
        "independence_note": (
            "fresh stride sample disjoint from the union of rows checked by spot "
            "checks #3 (worker-07) and #4 (worker-086) at the frozen sha; locators "
            "re-fetched live from arXiv/Crossref, ledger text never used as evidence; "
            "separate actor and separate script."),
        "inputs": {
            "ledger/citation_audit.csv": {
                "sha256": before,
                "sha256_before_fetches": before,
                "sha256_after_fetches": after,
                "stable_during_run": stable,
                "data_rows": len(rows),
                "checked_frame": f"data rows {SAMPLE}",
            }
        },
        "sampling_rule": {
            "frozen_before_fetch": True,
            "rule": "every 8th data row of frame 1-97 starting at row 5",
            "sampled_rows": SAMPLE,
            "disjoint_from_prior_checks": True,
            "prior_checked_union": PRIOR_UNION,
        },
        "method": {
            "arxiv_rows": "https://export.arxiv.org/api/query?id_list=<id> (Atom entry), "
                          "fallback https://arxiv.org/abs/<id> citation meta tags on API 429",
            "doi_rows": "https://api.crossref.org/works/<doi> (registry metadata; skipped "
                        "for 10.48550 arXiv DataCite DOIs, arXiv used instead)",
            "network": "live re-fetch from the primary APIs; raw body sha256 recorded; "
                       "stdlib urllib, no cached or ledger content used as evidence; "
                       "retry/backoff on 429/5xx",
            "comparison": ("normalised title equality/prefix/similarity (SequenceMatcher "
                           "autojunk=False); first ledger author surname present in the "
                           "union of fetched author lists (NFKD accent folding, both "
                           "'Given Family' and 'Family, Given' orders); ledger year against "
                           "the union of date-parts from all successful sources "
                           "(exact/off-by-one); excerpt containment test then similarity "
                           f"(match >= {EXCERPT_MATCH}, partial >= {EXCERPT_PARTIAL})"),
            "verdicts": "MATCH | PARTIAL (convention / metadata-only / excerpt quality) | "
                        "MISMATCH (work or claim differs) | FETCH_FAILED",
        },
        "results": results,
        "summary": summary,
        "hard_failures": hard_failures,
        "findings": findings,
        "falsifiers": [
            "re-running this script against a different ledger sha invalidates the binding",
            "a fetched primary source whose title/author/year/excerpt does not match the "
            "ledger row falsifies that row's 'verified' status",
            "if the ledger hash changed during the run the artifact is void (fail-closed)",
            "PARTIAL rows are not cleared: they need a content check against a source that "
            "carries the quoted text (journal PDF or arXiv full text)",
        ],
        "non_claims": [
            f"spot check on {len(results)} of 97 rows; not a ledger-wide verdict",
            "no gate or node status is set by this worker",
            "class_mapping topical consistency is not a class-binding verdict",
        ],
        "reproduce": "python3 artifacts/worker-028/l1_spotcheck/run_spotcheck_028.py",
    }
    ART.parent.mkdir(parents=True, exist_ok=True)
    ART.write_text(json.dumps(artifact, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (ART.parent / "spotcheck-l1-028.json.sha256").write_text(
        hashlib.sha256(ART.read_bytes()).hexdigest() + "  spotcheck-l1-028.json\n",
        encoding="utf-8")
    print(json.dumps({"artifact": str(ART.relative_to(ROOT)),
                      "artifact_sha256": sha_file(ART), "pin": PIN, "stable": stable,
                      "summary": summary}, indent=1))
    if not stable:
        print("FAIL-CLOSED: ledger drifted during run", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
