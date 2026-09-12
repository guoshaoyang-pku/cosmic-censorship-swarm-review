#!/usr/bin/env python3
"""Independent L1 uncovered-row re-fetch spot check #6 (worker-028), revision 1.

Bounded task: the 9 rows of ledger/citation_audit.csv that no re-fetch spot check
bound to ledger sha256 315c19145065 has ever sampled, pre-frozen in
artifacts/worker-028/l1_uncovered_spotcheck/sample_freeze_028.json
(sha256 219d1d64b2fd2e4390b22bfff43047b73572e81f6e9c621ba528bcbd1accf4fe) before
any fetch. Reports MATCH / PARTIAL / MISMATCH / FETCH_FAILED per row.

The sample is the residue of the worker-028 independence census
(artifacts/worker-028/l1_independence_census/independence_census.json,
sha256 77b0f1ed19c373727a14d3b44cdfea7dd8cab79714048acd0650a5e6245675ec):
the census listed 10 uncovered rows, but its own falsifier #2 fired --
artifacts/literature/reviews/L1-spotcheck-rev2.json binds the same ledger sha
and contains an independent-subagent re-fetch of SRC-059 (row 59) that the
census path enumeration missed. The residual sample excludes row 59. This run
therefore both (a) closes the last sampled-coverage gap and (b) corrects the
census count, with the correction itself controlled.

Instrument: same comparator family as spot check #5 (worker-028, revision 3),
whose controls are documented in its docstring. Additions here: a pre-frozen
sample file loaded and hash-checked before the first network call, a
citation_id -> row-index mapping control, an in-memory negative control that
must be classified MISMATCH by the same compare() path used on live data, and a
generic primary-source fetch used only for rows that would otherwise stay
metadata-only (so an INSPIRE record can content-check SRC-076 instead of
leaving it not_available).

No gate verdict, no node completion, no validation_status=passed, no ledger
edits. Raw response bytes are hashed; the ledger hash is re-checked after all
fetches and any drift aborts fail-closed.
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
ART = ROOT / "artifacts" / "worker-028" / "l1_uncovered_spotcheck" / "uncovered_spotcheck_028.json"
FREEZE = ROOT / "artifacts" / "worker-028" / "l1_uncovered_spotcheck" / "sample_freeze_028.json"
CENSUS = ROOT / "artifacts" / "worker-028" / "l1_independence_census" / "independence_census.json"
REV2 = ROOT / "artifacts" / "literature" / "reviews" / "L1-spotcheck-rev2.json"

PIN = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
FREEZE_SHA = "219d1d64b2fd2e4390b22bfff43047b73572e81f6e9c621ba528bcbd1accf4fe"
CENSUS_SHA = "77b0f1ed19c373727a14d3b44cdfea7dd8cab79714048acd0650a5e6245675ec"
SAMPLE = [51, 52, 60, 63, 68, 76, 79, 87, 88]
CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
CST = timezone(timedelta(hours=8))
UA = "l1-spotcheck-worker-028/0.3 (independent citation verification; stdlib urllib)"
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
    a, b = norm(a)[:400], norm(b)[:400]
    if not a or not b:
        return 0.0
    return round(difflib.SequenceMatcher(None, a, b, autojunk=False).ratio(), 4)


def http_get(url: str, timeout: int = 40, tries: int = 2, delay: float = 2.5):
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


def _parse_generic_body(body: bytes) -> dict:
    """Best-effort title/authors/abstract/years from a JSON API or an HTML page."""
    text = body.decode("utf-8", "replace")
    out: dict = {}
    stripped = text.lstrip()
    if stripped[:1] in "[{":
        try:
            j = json.loads(text)
        except Exception:  # noqa: BLE001
            j = None
        if isinstance(j, dict):
            md = j.get("metadata") if isinstance(j.get("metadata"), dict) else j
            t = md.get("titles")
            if isinstance(t, list) and t and isinstance(t[0], dict):
                out["title"] = t[0].get("title", "")
            if not out.get("title") and isinstance(md.get("title"), list) and md["title"]:
                out["title"] = md["title"][0]
            if not out.get("title") and isinstance(md.get("title"), str):
                out["title"] = md["title"]
            ab = md.get("abstracts")
            if isinstance(ab, list) and ab and isinstance(ab[0], dict):
                out["abstract"] = re.sub(r"<[^>]+>", " ", ab[0].get("value", ""))
            if not out.get("abstract") and isinstance(md.get("abstract"), str):
                out["abstract"] = re.sub(r"<[^>]+>", " ", md["abstract"])
            au = md.get("authors")
            names = []
            if isinstance(au, list):
                for a in au:
                    if isinstance(a, dict):
                        names.append(a.get("full_name") or a.get("name") or
                                     f"{a.get('given','')} {a.get('family','')}".strip())
                    elif isinstance(a, str):
                        names.append(a)
            out["authors"] = [n for n in names if n]
            dates = []
            for k in ("earliest_date", "date", "published"):
                v = md.get(k)
                if isinstance(v, str) and v[:4].isdigit():
                    dates.append(int(v[:4]))
            for pi in (md.get("publication_info") or []):
                if isinstance(pi, dict) and isinstance(pi.get("year"), int):
                    dates.append(pi["year"])
            out["years"] = sorted(set(dates))
    if not out.get("title"):
        def meta(name: str) -> str:
            m = re.search(rf'<meta\s+(?:name|property)="{re.escape(name)}"\s+'
                          r'content="([^"]*)"', text, re.I)
            return m.group(1) if m else ""

        out["title"] = meta("citation_title") or meta("og:title")
        if not out.get("title"):
            m = re.search(r"<title[^>]*>(.*?)</title>", text, re.S | re.I)
            out["title"] = " ".join(m.group(1).split()) if m else ""
        out["authors"] = re.findall(
            r'<meta\s+name="citation_author"\s+content="([^"]*)"', text, re.I)
        m = re.search(r'<blockquote class="abstract[^"]*">(.*?)</blockquote>', text, re.S)
        ab = re.sub(r"<[^>]+>", " ", m.group(1)) if m else (
            meta("description") or meta("og:description"))
        out["abstract"] = " ".join(ab.split())
        d = meta("citation_date") or meta("citation_online_date")
        out["years"] = [int(d[:4])] if d[:4].isdigit() else []
    return out


def fetch_generic(url: str) -> dict:
    out = {"kind": "generic-page", "url": url, "ok": False}
    try:
        body, status, secs = http_get(url)
        parsed = _parse_generic_body(body)
        out.update({"http_status": status, "bytes": len(body),
                    "sha256": hashlib.sha256(body).hexdigest(), "seconds": secs,
                    "ok": bool(parsed.get("title") or parsed.get("abstract"))})
        out.update(parsed)
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def surname(name: str) -> str:
    n = norm(name)
    return n.split()[-1] if n else ""


def ledger_surnames(field: str) -> list[str]:
    return [surname(a) for a in re.split(r";| and |,", field or "") if surname(a)]


def author_candidates(authors: list[str]) -> set[str]:
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


def negative_control() -> dict:
    """The same compare() path must call a deliberately wrong row MISMATCH."""
    fake_row = {
        "title": "Quantum foam in the interior of a totally different paper",
        "authors": "Nobody, A.; Also Nobody, B.",
        "year": "1900",
        "evidence_excerpt": "This abstract is entirely fabricated and must not match.",
    }
    fake_fetch = {
        "kind": "synthetic-control", "ok": True,
        "title": "Naked Singularities for the Einstein Vacuum Equations: The Exterior Solution",
        "authors": ["Igor Rodnianski", "Yakov Shlapentokh-Rothman"],
        "abstract": "In this work we initiate the mathematical study of naked singularities "
                    "for the Einstein vacuum equations.",
        "years": [2019],
    }
    res = compare(fake_row, [fake_fetch])
    return {"verdict": res["verdict"], "states": res["states"],
            "pass": res["verdict"] == "MISMATCH"}


def main() -> int:
    # --- pre-fetch gates: freeze integrity, ledger pin, census/rev2 reconciliation
    before = sha_file(LEDGER)
    if before != PIN:
        print(json.dumps({"abort": "ledger hash drift before fetch", "expected": PIN,
                          "measured": before}), file=sys.stderr)
        return 2
    freeze_sha = sha_file(FREEZE)
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    if freeze_sha != FREEZE_SHA:
        print(json.dumps({"abort": "sample freeze hash mismatch", "expected": FREEZE_SHA,
                          "measured": freeze_sha}), file=sys.stderr)
        return 2
    if freeze["sampled_rows"] != SAMPLE or freeze["ledger"]["sha256"] != PIN:
        print(json.dumps({"abort": "sample freeze does not match script",
                          "freeze_rows": freeze["sampled_rows"]}), file=sys.stderr)
        return 2
    rows = list(csv.DictReader(open(LEDGER, newline="", encoding="utf-8")))
    if len(rows) != 97:
        print(json.dumps({"abort": "unexpected data row count", "n": len(rows)}), file=sys.stderr)
        return 2

    census_sha = sha_file(CENSUS)
    census = json.loads(CENSUS.read_text(encoding="utf-8"))
    rev2_sha = sha_file(REV2)
    rev2 = json.loads(REV2.read_text(encoding="utf-8"))
    ctrl: dict = {}
    ctrl["freeze_integrity"] = freeze_sha == FREEZE_SHA
    ctrl["census_pin_match"] = census.get("ledger", {}).get("sha256_at_end") == PIN
    ctrl["rev2_pin_match"] = rev2.get("binding", {}).get("ledger/citation_audit.csv") == PIN
    ctrl["census_artifact_hash"] = census_sha == CENSUS_SHA
    all_rows = set(range(1, len(rows) + 1))
    id_to_row = {r["citation_id"]: i + 1 for i, r in enumerate(rows)}
    ctrl["citation_id_row_mapping"] = all(
        rows[i - 1]["citation_id"] == f"SRC-{i:03d}" for i in range(1, len(rows) + 1))
    census_union: set[int] = set()
    for c in census["bound_checks"]:
        census_union |= set(c.get("rows") or [])
    ctrl["census_union_recomputes"] = (all_rows - census_union) == set(
        census["counts"]["uncovered_rows"])
    rev2_rows = {id_to_row[x["source_id"]] for x in rev2["results"]}
    corrected_union = census_union | rev2_rows
    corrected_uncovered = all_rows - corrected_union
    ctrl["census_missed_rev2_rows"] = sorted(rev2_rows - census_union)
    ctrl["census_missed_rows_are_exactly_59"] = sorted(rev2_rows - census_union) == [59]
    ctrl["corrected_uncovered_matches_freeze"] = corrected_uncovered == set(SAMPLE)
    neg = negative_control()
    ctrl["comparator_negative_control"] = neg
    bool_keys = ["freeze_integrity", "census_pin_match", "rev2_pin_match",
                 "census_artifact_hash", "citation_id_row_mapping",
                 "census_union_recomputes", "census_missed_rows_are_exactly_59",
                 "corrected_uncovered_matches_freeze"]
    hard_ctrl = [k for k in bool_keys if ctrl.get(k) is not True]
    if hard_ctrl or not neg["pass"]:
        print(json.dumps({"abort": "pre-fetch control failure", "failed": hard_ctrl,
                          "negative_control": neg}), file=sys.stderr)
        return 2

    reconciliation = {
        "census": {"path": str(CENSUS.relative_to(ROOT)), "sha256": census_sha,
                   "uncovered_rows": census["counts"]["uncovered_rows"],
                   "union_rows_covered": census["counts"]["union_rows_covered"]},
        "missed_artifact": {"path": str(REV2.relative_to(ROOT)), "sha256": rev2_sha,
                            "ledger_pin": rev2["binding"]["ledger/citation_audit.csv"],
                            "rows": sorted(rev2_rows),
                            "census_missed_rows": sorted(rev2_rows - census_union),
                            "missed_row_evidence": {
                                x["source_id"]: {"fetched_by": x.get("fetched_by"),
                                                 "verdict": x.get("verdict")}
                                for x in rev2["results"]
                                if id_to_row[x["source_id"]] in (rev2_rows - census_union)}},
        "corrected_union_rows_covered": len(corrected_union),
        "corrected_uncovered_rows": sorted(corrected_uncovered),
        "correction": ("census falsifier #2 fired: an on-disk hash-bound re-fetch spot check "
                       "was not enumerated; row 59 is covered by an independent-subagent check, "
                       "so the residual uncovered set is 9 rows, not 10"),
    }

    # --- live re-fetch of the frozen sample
    results, hard_failures, findings = [], [], []
    for r in SAMPLE:
        row = rows[r - 1]
        entry = {"row": r, "citation_id": row["citation_id"],
                 "class_mapping": row.get("class_mapping", ""),
                 "ledger": {k: row.get(k, "") for k in
                            ("title", "authors", "year", "venue", "doi", "arxiv_id",
                             "exact_locator", "evidence_url", "evidence_excerpt",
                             "used_by_theorems", "verdict", "fetched_at")},
                 "fetches": [], "fetch_ok": False}
        fetches = []
        if row.get("arxiv_id"):
            fetches.append(fetch_arxiv(row["arxiv_id"].strip()))
            time.sleep(2.0)
        doi = (row.get("doi") or "").strip()
        if doi and not doi.lower().startswith("10.48550/"):
            fetches.append(fetch_crossref(doi))
        seen_hosts = {urllib.parse.urlsplit(f["url"]).netloc for f in fetches if f.get("ok")}
        target = (row.get("evidence_url") or row.get("exact_locator") or "").strip()
        if target.startswith("http") and not any(
                f.get("ok") and f.get("abstract") for f in fetches):
            host = urllib.parse.urlsplit(target).netloc
            if host not in seen_hosts:
                fetches.append(fetch_generic(target))
                time.sleep(1.5)
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
                            "fetched records; needs a source carrying the quoted text")
        if str(row.get("fetched_at", "")) > now():
            findings.append(f"{row['citation_id']} ledger fetched_at {row['fetched_at']} is "
                            "future-dated at run time (clock-discipline finding, CF-14 class)")
        results.append(entry)
        time.sleep(2.0)

    after = sha_file(LEDGER)
    stable = after == before
    summary = {"checked": len(results), "MATCH": 0, "PARTIAL": 0, "MISMATCH": 0,
               "FETCH_FAILED": 0}
    for e in results:
        summary[e["verdict"]] += 1
    sampled_union = corrected_union | set(SAMPLE)
    fetched_rows = corrected_union | {e["row"] for e in results if e["fetch_ok"]}
    artifact = {
        "schema_version": "0.1",
        "artifact_type": "l1_refetch_spotcheck",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": CLASS_IDS,
        "actor": "worker-028",
        "reviewer": "worker-028",
        "created_at": now(),
        "check_number": 6,
        "revision": 1,
        "purpose": ("close the last sampled-coverage gap of the L1 re-fetch corpus at ledger "
                    "sha 315c19145065: the 9 rows no prior check ever sampled; the sample was "
                    "frozen before any fetch and excludes row 59, which the census missed"),
        "independent_of": [str(REV2.relative_to(ROOT))] + [
            c["path"] for c in census["bound_checks"] if c.get("rows")],
        "independence_note": (
            "fresh residual sample disjoint from the census-enumerated union at the frozen sha; "
            "locators re-fetched live from arXiv/Crossref/INSPIRE; ledger text never used as "
            "evidence; separate actor and separate script; sample pre-registered on disk "
            "before the first network call."),
        "inputs": {
            "ledger/citation_audit.csv": {
                "sha256": before,
                "sha256_before_fetches": before,
                "sha256_after_fetches": after,
                "stable_during_run": stable,
                "data_rows": len(rows),
                "checked_rows": SAMPLE,
            },
            "sample_freeze": {"path": str(FREEZE.relative_to(ROOT)), "sha256": freeze_sha,
                              "frozen_before_fetch": True,
                              "frozen_at": freeze["created_at"],
                              "selection_rule": freeze["selection_rule"]},
        },
        "sampling_rule": {
            "frozen_before_fetch": True,
            "rule": ("residue of the census uncovered set at sha 315c19145065 after excluding "
                     "row 59, which the census missed in "
                     "artifacts/literature/reviews/L1-spotcheck-rev2.json"),
            "sampled_rows": SAMPLE,
            "disjoint_from_prior_checks": True,
            "prior_checked_union": sorted(census_union),
        },
        "census_reconciliation": reconciliation,
        "controls": {"pre_fetch": ctrl, "ledger_stable_during_run": stable},
        "method": {
            "arxiv_rows": "https://export.arxiv.org/api/query?id_list=<id> (Atom entry), "
                          "fallback https://arxiv.org/abs/<id> citation meta tags on API 429",
            "doi_rows": "https://api.crossref.org/works/<doi> (registry metadata; skipped "
                        "for 10.48550 arXiv DataCite DOIs, arXiv used instead)",
            "generic_rows": ("ledger evidence_url fetched live only when no successful source "
                             "carries an abstract (JSON API fields or citation meta tags)"),
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
        "summary": dict(summary, **{
            "prior_union_rows_covered": len(corrected_union),
            "residual_rows_sampled_here": len(SAMPLE),
            "union_rows_sampled_after_this_check": len(sampled_union),
            "union_rows_with_successful_fetch": len(fetched_rows),
            "ledger_rows": len(rows),
        }),
        "hard_failures": hard_failures,
        "findings": findings,
        "falsifiers": [
            "re-running this script against a different ledger sha invalidates the binding",
            "a fetched primary source whose title/author/year/excerpt does not match the "
            "ledger row falsifies that row's 'verified' status",
            "if the ledger hash changed during the run the artifact is void (fail-closed)",
            "the census correction is falsified by a re-run that shows L1-spotcheck-rev2.json "
            "does not bind sha 315c19145065 or does not cover SRC-059",
            "PARTIAL rows are not cleared: they need a content check against a source that "
            "carries the quoted text (journal PDF or full text)",
        ],
        "non_claims": [
            f"spot check on {len(results)} residual rows; not a ledger-wide verdict",
            "no gate or node status is set by this worker",
            "class_mapping topical consistency is not a class-binding verdict",
            "the census correction measures enumeration completeness, not citation truth",
        ],
        "reproduce": ("python3 artifacts/worker-028/l1_uncovered_spotcheck/"
                      "run_uncovered_spotcheck_028.py"),
    }
    ART.parent.mkdir(parents=True, exist_ok=True)
    ART.write_text(json.dumps(artifact, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (ART.parent / "uncovered_spotcheck_028.json.sha256").write_text(
        hashlib.sha256(ART.read_bytes()).hexdigest() + "  uncovered_spotcheck_028.json\n",
        encoding="utf-8")
    print(json.dumps({"artifact": str(ART.relative_to(ROOT)),
                      "artifact_sha256": sha_file(ART), "pin": PIN, "stable": stable,
                      "sample_freeze_sha256": freeze_sha,
                      "census_correction": reconciliation["correction"],
                      "summary": artifact["summary"],
                      "findings": findings}, indent=1))
    if not stable:
        print("FAIL-CLOSED: ledger drifted during run", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
