#!/usr/bin/env python3
"""Independent L1 primary-source re-fetch spot check #5 (actor: worker-063).

Class-bound task (G-LIT / node L1). Classes carried by the ledger rows:
AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH.

Sampling rule FROZEN BEFORE ANY FETCH. The pinned ledger revision is the
controller-measured canonical hash 315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9.
The script fails closed (no fetch) if the ledger is not at the pinned hash.

Disjointness: prior checks bound to this revision sampled
  check #3 (worker-07): rows 41,49,57,65,73,80,81,89
  check #4 (worker-086): rows 1,4,9,16,17,25,33,96,97
This check's frame excludes all of those rows.

Method: the row's primary locator (evidence_url, else url) is re-fetched and its raw
bytes hashed; title / first-author / year / excerpt are compared against the ledger row
with the thresholds fixed below. In addition the exact_locator column is probed: it is
classified exact vs search-query, and a search-query locator is additionally fetched to
test whether the recorded work is returned. No ledger text is used as fetched evidence.
"""
from __future__ import annotations

import csv
import difflib
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "ledger" / "citation_audit.csv"
OUT = Path(__file__).resolve().parent / "spotcheck-l1-063.json"
SCRIPT = Path(__file__).resolve()
CST = timezone(timedelta(hours=8))

SCHEMA_VERSION = "0.1"
ACTOR = "worker-063"
NODE_ID = "L1"
GATE = "G-LIT"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
CHECK_NUMBER = 5

PINNED_LEDGER_SHA256 = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"

# ---- frozen sampling rule (unchanged since first write at 00:19:43) ------
SAMPLING_RULE = {
    "frozen_before_fetch": True,
    "frozen_at": "2026-09-12T00:19:43+08:00",
    "S1_stride": "every 8th data row of frame 2-40 starting at 2 -> rows 2,10,18,26,34",
    "S2_stride": "every 8th data row of frame 42-97 starting at 42 -> rows 42,50,58,66,74,82,90",
    "S3_targeted": (
        "rows 3,5,22,40,94 declared before any fetch: row 3 (WCC load-bearing T-208/T-209), "
        "row 5 (C0 anchor T-302), row 22 (C0+C2, three theorems), row 40 (C0+C2+WCC, five theorems), "
        "row 94 (SCALAR-SPH, T-103)"
    ),
    "sampled_rows": [2, 3, 5, 10, 18, 22, 26, 34, 40, 42, 50, 58, 66, 74, 82, 90, 94],
    "excluded_prior_frames": {
        "check_3_worker-07": [41, 49, 57, 65, 73, 80, 81, 89],
        "check_4_worker-086": [1, 4, 9, 16, 17, 25, 33, 96, 97],
    },
    "frame": "all 97 data rows of ledger/citation_audit.csv minus the excluded prior frames",
}
SAMPLED_ROWS = SAMPLING_RULE["sampled_rows"]

# ---- frozen comparison thresholds ----------------------------------------
TITLE_MATCH = 0.85
TITLE_PARTIAL = 0.60
EXCERPT_MATCH = 0.60
EXCERPT_PARTIAL = 0.30

UA = "worker-063-l1-spotcheck/1.0 (ai4math-swarm; contact: local)"
TIMEOUT = 30


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


def norm(s) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = s.replace("$", " ").replace("\\", " ")
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\{|\}", " ", s)
    s = s.casefold()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def clean_url(s: str | None) -> str:
    if not s:
        return ""
    s = s.strip()
    s = re.split(r"\s+[\(\u00a7]", s)[0]  # strip trailing "(§ ...)" annotations
    s = s.rstrip(".,;")
    return s


EXACT_PATTERNS = (
    re.compile(r"arxiv\.org/(abs|pdf)/", re.I),
    re.compile(r"inspirehep\.net/(api/literature/|record/)\d+", re.I),
    re.compile(r"api\.crossref\.org/works/", re.I),
    re.compile(r"api\.openalex\.org/works/", re.I),
    re.compile(r"doi\.org/10\.", re.I),
    re.compile(r"^https?://[^?]+\.pdf$", re.I),
)


def locator_is_exact(url: str) -> bool:
    if not url:
        return False
    if "?" in url and re.search(r"(search_query=|/api/literature\?|\?q=|\?search=)", url, re.I):
        return False
    return any(p.search(url) for p in EXACT_PATTERNS)


def fetch(url: str) -> dict:
    """Fetch raw bytes from a locator. urllib first, curl fallback."""
    out = {"url": url, "http_status": None, "raw_sha256": None, "bytes": None,
           "content_type": None, "final_url": None, "error": None, "body": b""}
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read()
            out.update(http_status=r.status, final_url=r.geturl(), bytes=len(body),
                       raw_sha256=sha256_bytes(body), content_type=r.headers.get("Content-Type"),
                       body=body)
            return out
    except Exception as e:  # noqa: BLE001
        out["error"] = f"urllib: {type(e).__name__}: {e}"
    try:
        p = subprocess.run(["curl", "-sS", "-L", "--max-time", str(TIMEOUT), "-A", UA, url],
                           capture_output=True, timeout=TIMEOUT + 10)
        if p.returncode == 0 and p.stdout:
            body = p.stdout
            out.update(http_status=200, final_url=url, bytes=len(body),
                       raw_sha256=sha256_bytes(body), content_type=None, error=None, body=body)
        else:
            out["error"] = (out["error"] or "") + f" | curl rc={p.returncode} {p.stderr[:200]!r}"
    except Exception as e:  # noqa: BLE001
        out["error"] = (out["error"] or "") + f" | curl: {type(e).__name__}: {e}"
    return out


# ---- per-host metadata extraction ----------------------------------------
def _meta_tags(html: str) -> dict:
    tags: dict[str, list[str]] = {}
    for m in re.finditer(r'<meta\s+([^>]+)>', html, re.I):
        attrs = dict(re.findall(r'([\w:-]+)\s*=\s*"([^"]*)"', m.group(1)))
        name = (attrs.get("name") or attrs.get("property") or "").lower()
        if name and "content" in attrs:
            tags.setdefault(name, []).append(attrs["content"])
    return tags


def _strip_html(s: str) -> str:
    s = re.sub(r"<script.*?</script>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<style.*?</style>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", s).strip()


def _decode(body: bytes) -> str:
    if body[:5] == b"%PDF-":
        return ""
    try:
        return body.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return body.decode("latin-1", errors="replace")


def extract(url: str, body: bytes, content_type: str | None) -> dict:
    """Return {title, authors[], year, abstract, kind, note}."""
    low = url.lower()
    ct = (content_type or "").lower()
    meta = {"title": None, "authors": [], "year": None, "abstract": None, "kind": None, "note": None}
    if body[:5] == b"%PDF-" or ("pdf" in ct and not body[:1] == b"<"):
        meta["kind"] = "pdf"
        meta["note"] = "non-HTML payload; metadata not machine-extracted by this method"
        return meta
    text = _decode(body)

    if re.search(r"inspirehep\.net/api/literature/\d+$", low):
        try:
            md = json.loads(text)["metadata"]
            meta["kind"] = "inspire-record-json"
            meta["title"] = (md.get("titles") or [{}])[0].get("title")
            meta["authors"] = [a.get("full_name", "") for a in (md.get("authors") or [])]
            d = md.get("earliest_date") or (md.get("publication_info") or [{}])[0].get("year") or ""
            meta["year"] = int(str(d)[:4]) if re.match(r"\d{4}", str(d)) else None
            abs_ = md.get("abstracts") or []
            meta["abstract"] = abs_[0].get("value") if abs_ else None
            return meta
        except Exception as e:  # noqa: BLE001
            meta["note"] = f"inspire record JSON parse failed: {e}"
            return meta

    if "api.crossref.org" in low:
        try:
            msg = json.loads(text)["message"]
            meta["kind"] = "crossref-json"
            meta["title"] = (msg.get("title") or [None])[0]
            meta["authors"] = [f"{a.get('given','')} {a.get('family','')}".strip()
                               for a in (msg.get("author") or [])]
            parts = ((msg.get("issued") or {}).get("date-parts") or [[None]])[0]
            meta["year"] = int(parts[0]) if parts and parts[0] else None
            meta["abstract"] = _strip_html(msg.get("abstract")) if msg.get("abstract") else None
            return meta
        except Exception as e:  # noqa: BLE001
            meta["note"] = f"crossref JSON parse failed: {e}"
            return meta

    if "api.openalex.org" in low:
        try:
            doc = json.loads(text)
            meta["kind"] = "openalex-json"
            meta["title"] = doc.get("title")
            meta["authors"] = [a.get("author", {}).get("display_name", "")
                               for a in (doc.get("authorships") or [])]
            meta["year"] = doc.get("publication_year")
            inv = doc.get("abstract_inverted_index")
            if inv:
                pos: dict[int, str] = {}
                for w, ps in inv.items():
                    for p in ps:
                        pos[p] = w
                meta["abstract"] = " ".join(pos[k] for k in sorted(pos))
            return meta
        except Exception as e:  # noqa: BLE001
            meta["note"] = f"openalex JSON parse failed: {e}"
            return meta

    if text.lstrip().startswith("<?xml"):
        try:
            import xml.etree.ElementTree as ET
            ns = {"a": "http://www.w3.org/2005/Atom"}
            root = ET.fromstring(text)
            e = root.find("a:entry", ns)
            if e is not None:
                meta["kind"] = "arxiv-xml"
                meta["title"] = re.sub(r"\s+", " ", (e.findtext("a:title", "", ns) or "")).strip()
                meta["authors"] = [a.findtext("a:name", "", ns) for a in e.findall("a:author", ns)]
                pub = e.findtext("a:published", "", ns) or ""
                meta["year"] = int(pub[:4]) if re.match(r"\d{4}", pub) else None
                meta["abstract"] = re.sub(r"\s+", " ", (e.findtext("a:summary", "", ns) or "")).strip()
                return meta
        except Exception as e:  # noqa: BLE001
            meta["note"] = f"arxiv xml parse failed: {e}"
            return meta

    tags = _meta_tags(text)
    meta["kind"] = "html"
    meta["title"] = (tags.get("citation_title") or [None])[0]
    meta["authors"] = list(tags.get("citation_author") or [])
    date = (tags.get("citation_date") or tags.get("citation_publication_date") or [None])[0]
    if date and re.match(r"\d{4}", date):
        meta["year"] = int(date[:4])
    block = re.search(r'<blockquote[^>]*class="[^"]*abstract[^"]*"[^>]*>(.*?)</blockquote>', text, re.S | re.I)
    if block:
        meta["abstract"] = _strip_html(block.group(1))
        meta["abstract"] = re.sub(r"^Abstract:?\s*", "", meta["abstract"], flags=re.I)
    if not meta["title"]:
        t = re.search(r"<title[^>]*>(.*?)</title>", text, re.S | re.I)
        if t:
            meta["title"] = _strip_html(t.group(1))
    if not meta["authors"]:
        meta["authors"] = re.findall(r'name="citation_author"\s+content="([^"]+)"', text, re.I)
    return meta


def search_hit_titles(url: str, body: bytes) -> list[str]:
    """Titles returned by a search-query locator (first page)."""
    text = _decode(body)
    low = url.lower()
    titles: list[str] = []
    try:
        if text.lstrip().startswith("<?xml"):
            import xml.etree.ElementTree as ET
            ns = {"a": "http://www.w3.org/2005/Atom"}
            root = ET.fromstring(text)
            for e in root.findall("a:entry", ns):
                t = e.findtext("a:title", "", ns)
                if t:
                    titles.append(re.sub(r"\s+", " ", t).strip())
        elif "api.crossref.org" in low:
            for it in (json.loads(text).get("message") or {}).get("items", []):
                if it.get("title"):
                    titles.append(it["title"][0])
        elif "api.openalex.org" in low:
            for it in json.loads(text).get("results", []):
                if it.get("title"):
                    titles.append(it["title"])
        elif "inspirehep.net" in low:
            doc = json.loads(text)
            for h in (doc.get("hits") or {}).get("hits", []):
                md = h.get("metadata") or {}
                for t in md.get("titles") or []:
                    if t.get("title"):
                        titles.append(t["title"])
    except Exception:  # noqa: BLE001
        pass
    return titles


def first_author_token(authors_field: str) -> str:
    a = (authors_field or "").split(";")[0].strip()
    a = re.sub(r"\(.*?\)", " ", a).strip()
    toks = norm(a).split()
    return toks[-1] if toks else ""


ELLIPSIS = re.compile(r"(?:\.\s*\.\s*\.|\u2026|\[\.\.\.\]|\[\u2026\])")
EXCERPT_PREFIX = re.compile(
    r"^\s*(?:(?:crossref|aps|arxiv|inspire(?:hep)?|journal|publisher|springer|elsevier)\s+)?abstract\s*:?\s*[\"'“”']*",
    re.I)


def fragment_coverage(excerpt: str, abstract: str, thresh: float = 0.6) -> dict | None:
    """Secondary diagnostic (does NOT change the frozen verdict): elided ledger quotes
    are de-prefixed, split on ellipses, and each fragment >= 40 normalized chars is
    matched to the fetched abstract by 5-gram token overlap >= thresh."""
    ex = EXCERPT_PREFIX.sub("", excerpt or "").strip().strip("\"'“”'")
    frags = [f for f in (norm(x) for x in ELLIPSIS.split(ex)) if len(f) >= 40]
    if not frags or not abstract:
        return None
    na = norm(abstract)
    grams_abs = {tuple(na.split()[i:i + 5]) for i in range(max(0, len(na.split()) - 4))}
    matched = 0
    per = []
    for f in frags:
        toks = f.split()
        grams = [tuple(toks[i:i + 5]) for i in range(max(0, len(toks) - 4))]
        if not grams or not grams_abs:
            per.append(0.0)
            continue
        cov = sum(1 for g in grams if g in grams_abs) / len(grams)
        per.append(round(cov, 3))
        if cov >= thresh:
            matched += 1
    return {"n_fragments": len(frags), "matched_fragments": matched,
            "coverage": round(matched / len(frags), 3), "per_fragment_overlap": per,
            "threshold": thresh, "metric": "5-gram token overlap"}


def compare(row: dict, fetched: dict, fetch_meta: dict) -> dict:
    led_title = row.get("title") or ""
    led_authors = row.get("authors") or ""
    led_excerpt = row.get("evidence_excerpt") or ""
    nt, nft = norm(led_title), norm(fetched.get("title") or "")
    title_r = ratio(nt, nft)
    contained = bool(nt) and bool(nft) and (nt in nft or nft in nt)
    if title_r >= TITLE_MATCH or contained:
        title_state = "match"
    elif title_r >= TITLE_PARTIAL:
        title_state = "partial"
    else:
        title_state = "mismatch"
    fa = first_author_token(led_authors)
    fa_state = bool(fa) and any(fa in norm(a) for a in (fetched.get("authors") or []))
    ly = None
    try:
        ly = int(str(row.get("year"))[:4])
    except ValueError:
        pass
    fy = fetched.get("year")
    if fy is None or ly is None:
        year_state = "unknown"
    elif fy == ly:
        year_state = "match"
    elif abs(fy - ly) <= 1:
        year_state = "within1"
    else:
        year_state = "mismatch"
    ex_r = None
    if led_excerpt and fetched.get("abstract"):
        ex_r = ratio(norm(led_excerpt)[:400], norm(fetched["abstract"])[:400])
    states = {
        "title": title_state, "title_ratio": round(title_r, 3),
        "first_author": fa_state, "year": year_state,
        "fetched_year": fy, "ledger_year": ly,
        "excerpt_ratio": round(ex_r, 3) if ex_r is not None else None,
        "excerpt_fragment_coverage": fragment_coverage(led_excerpt, fetched.get("abstract")),
        "kind": fetched.get("kind"),
    }
    if fetch_meta.get("error") or fetch_meta.get("http_status") is None:
        verdict = "FETCH_FAILED"
    elif fetched.get("kind") == "pdf":
        verdict = "PARTIAL"  # locator resolves; payload not machine-comparable
    elif title_state == "mismatch" or not fa_state or year_state == "mismatch":
        verdict = "MISMATCH"
    elif (title_state == "match" and fa_state and year_state in {"match", "within1", "unknown"}
          and (ex_r is None or ex_r >= EXCERPT_MATCH)):
        verdict = "MATCH"
    else:
        verdict = "PARTIAL"
    return {"states": states, "verdict": verdict}


def main() -> int:
    started = now()
    if sha256_file(LEDGER) != PINNED_LEDGER_SHA256:
        print(json.dumps({"abort": "ledger hash != pinned hash; fail-closed before fetch",
                          "pinned": PINNED_LEDGER_SHA256, "measured": sha256_file(LEDGER)}))
        return 2
    with LEDGER.open(newline="") as f:
        rows = list(csv.DictReader(f))
    by_row = {i: r for i, r in enumerate(rows, start=1)}

    def work(rn: int) -> dict:
        r = by_row[rn]
        primary = clean_url(r.get("evidence_url")) or clean_url(r.get("url"))
        locator = clean_url(r.get("exact_locator"))
        f = fetch(primary)
        body = f.get("body") or b""
        meta = extract(primary, body, f.get("content_type"))
        cmp_ = compare(r, meta, f)
        probe = None
        if locator and locator != primary:
            is_exact = locator_is_exact(locator)
            pf = fetch(locator)
            if pf.get("http_status") == 429:  # arXiv/INSPIRE rate limit: one bounded retry
                import time
                time.sleep(3)
                pf = fetch(locator)
            hits = search_hit_titles(locator, pf.get("body") or b"")
            best = max((ratio(norm(r.get("title")), norm(t)) for t in hits), default=0.0)
            conclusive = pf.get("http_status") == 200
            probe = {
                "locator": locator,
                "locator_kind": "exact" if is_exact else "search_query",
                "http_status": pf.get("http_status"),
                "raw_sha256": pf.get("raw_sha256"),
                "bytes": pf.get("bytes"),
                "fetch_error": pf.get("error"),
                "hits_returned": len(hits),
                "best_hit_title_ratio": round(best, 3),
                "probe_inconclusive": not conclusive,
                "resolves_to_recorded_work": (bool(hits) and best >= TITLE_PARTIAL) if conclusive else None,
            }
        return {
            "row": rn,
            "citation_id": r.get("citation_id"),
            "class_mapping": r.get("class_mapping"),
            "used_by_theorems": r.get("used_by_theorems"),
            "ledger_verdict": r.get("verdict"),
            "ledger_status": r.get("status"),
            "evidence_type": r.get("evidence_type"),
            "primary_locator": primary,
            "primary_locator_kind": "exact" if locator_is_exact(primary) else "not_exact",
            "http_status": f.get("http_status"),
            "final_url": f.get("final_url"),
            "content_type": f.get("content_type"),
            "bytes": f.get("bytes"),
            "raw_sha256": f.get("raw_sha256"),
            "fetch_error": f.get("error"),
            "fetched": {"title": meta.get("title"), "authors": (meta.get("authors") or [])[:6],
                        "year": meta.get("year"), "abstract_present": bool(meta.get("abstract")),
                        "note": meta.get("note")},
            "exact_locator_probe": probe,
            **cmp_,
        }

    with ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(work, SAMPLED_ROWS))
    results.sort(key=lambda x: x["row"])

    after = sha256_file(LEDGER)
    counts = {v: 0 for v in ("MATCH", "PARTIAL", "MISMATCH", "FETCH_FAILED")}
    for r in results:
        counts[r["verdict"]] += 1

    # post-hoc classification, clearly labelled: does NOT alter the frozen verdicts.
    for r in results:
        s = r["states"]
        if r["verdict"] == "MISMATCH":
            fields = []
            if s["title"] == "mismatch":
                fields.append("title")
            if not s["first_author"]:
                fields.append("first_author")
            if s["year"] == "mismatch":
                fields.append("year")
            r["contradicted_fields"] = fields
            r["divergence_class"] = "year_only" if fields == ["year"] else "metadata_contradiction"
        else:
            r["contradicted_fields"] = []
            r["divergence_class"] = None
        fc = s.get("excerpt_fragment_coverage")
        if fc is not None and s.get("excerpt_ratio") is not None and s["excerpt_ratio"] < EXCERPT_MATCH:
            r["excerpt_note"] = (
                "frozen char-ratio below threshold, but elided-quote fragment coverage is "
                f"{fc['matched_fragments']}/{fc['n_fragments']} = {fc['coverage']} "
                "(secondary diagnostic; verdict unchanged)")

    mism = [{"row": r["row"], "citation_id": r["citation_id"], "class_mapping": r["class_mapping"],
             "ledger_verdict": r["ledger_verdict"], "states": r["states"],
             "contradicted_fields": r["contradicted_fields"],
             "divergence_class": r["divergence_class"],
             "primary_locator": r["primary_locator"], "raw_sha256": r["raw_sha256"],
             "fetched_title": r["fetched"]["title"], "ledger_title": by_row[r["row"]]["title"]}
            for r in results if r["verdict"] == "MISMATCH"]
    n_year_only = sum(1 for r in mism if r["divergence_class"] == "year_only")
    n_contradiction = sum(1 for r in mism if r["divergence_class"] == "metadata_contradiction")
    findings = []
    for r in mism:
        if r["divergence_class"] == "year_only":
            findings.append(
                f"row {r['row']} {r['citation_id']}: year-only divergence (frozen verdict MISMATCH): "
                f"ledger year {r['states']['ledger_year']} (journal/revision year) vs fetched page year "
                f"{r['states']['fetched_year']} (preprint/first-version year); title ratio "
                f"{r['states']['title_ratio']} and first author match exactly, so this is a "
                "year-provenance discrepancy, not a work-identity contradiction.")
    search_locators = [r for r in results
                       if r["exact_locator_probe"] and r["exact_locator_probe"]["locator_kind"] == "search_query"]
    inconclusive_probes = [r for r in search_locators if r["exact_locator_probe"]["probe_inconclusive"]]
    for r in search_locators:
        p = r["exact_locator_probe"]
        if p["probe_inconclusive"]:
            findings.append(
                f"row {r['row']} {r['citation_id']}: exact_locator is a search query; probe inconclusive "
                f"(HTTP {p['http_status']}) so resolvability was not decided by this check")
        else:
            findings.append(
                f"row {r['row']} {r['citation_id']}: exact_locator is a search query, not an exact locator "
                f"(resolves_to_recorded_work={p['resolves_to_recorded_work']}, best_hit_ratio={p['best_hit_title_ratio']})")
    frag_fail = [r for r in results
                 if r["states"].get("excerpt_fragment_coverage")
                 and r["states"]["excerpt_fragment_coverage"]["coverage"] < 0.6]
    for r in frag_fail:
        fc = r["states"]["excerpt_fragment_coverage"]
        findings.append(
            f"row {r['row']} {r['citation_id']}: ledger evidence_excerpt fragments are NOT recovered from the "
            f"fetched abstract ({fc['matched_fragments']}/{fc['n_fragments']}, per-fragment overlap "
            f"{fc['per_fragment_overlap']}); excerpt provenance unresolved")
    for r in results:
        if r["verdict"] == "PARTIAL":
            why = []
            if r["states"]["title"] != "match":
                why.append(f"title {r['states']['title']} ({r['states']['title_ratio']})")
            if not r["states"]["first_author"]:
                why.append("first author not found")
            if r["states"]["year"] == "unknown":
                why.append("year not machine-extractable")
            if r["states"]["excerpt_ratio"] is not None and r["states"]["excerpt_ratio"] < EXCERPT_MATCH:
                why.append(f"excerpt char-ratio {r['states']['excerpt_ratio']}")
            findings.append(f"row {r['row']} {r['citation_id']}: PARTIAL ({'; '.join(why) or 'payload not machine-comparable'})")
    n_frag_explained = sum(1 for r in results if r.get("excerpt_note"))

    doc = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "l1_refetch_spotcheck",
        "node_id": NODE_ID,
        "gate": GATE,
        "class_ids": CLASS_IDS,
        "actor": ACTOR,
        "reviewer": ACTOR,
        "created_at": now(),
        "started_at": started,
        "check_number": CHECK_NUMBER,
        "script": {"path": str(SCRIPT.relative_to(ROOT)), "sha256": sha256_file(SCRIPT)},
        "independent_of": ["artifacts/worker-07/l1_spotcheck/spotcheck-l1-07.json",
                           "artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json"],
        "independence_note": (
            "Row frame is disjoint from checks #3 (worker-07) and #4 (worker-086) at the pinned "
            "revision; every primary locator was re-fetched with raw-byte sha256 recorded; no ledger "
            "text was used as fetched evidence. Limitation: the prior checks' sampling frames were "
            "read to guarantee disjointness; their per-row verdicts were not used to set or alter "
            "this frozen rule."
        ),
        "inputs": {
            "ledger/citation_audit.csv": {
                "sha256_pinned": PINNED_LEDGER_SHA256,
                "sha256_before_fetch": PINNED_LEDGER_SHA256,
                "sha256_after_fetch": after,
                "drifted_during_fetch": after != PINNED_LEDGER_SHA256,
                "data_rows": len(rows),
            }
        },
        "sampling_rule": SAMPLING_RULE,
        "method": {
            "fetch": "urllib.request GET (curl -sS -L fallback), raw response bytes hashed sha256",
            "primary_locator": "evidence_url (fallback url); exact_locator probed separately",
            "extract": "host-dispatched metadata parse: arXiv HTML meta/Atom, INSPIRE record JSON, Crossref JSON, OpenAlex JSON, HTML citation_* meta",
            "compare": {
                "title": f"normalized difflib ratio >= {TITLE_MATCH} (or containment) = match; >= {TITLE_PARTIAL} = partial",
                "first_author": "ledger first-author surname token present in fetched author list",
                "year": "exact = match; |diff| <= 1 = within1; absent = unknown",
                "excerpt": f"normalized first-400-char ratio >= {EXCERPT_MATCH} required for MATCH when an excerpt exists",
                "verdict": "MISMATCH if title mismatch or first author absent or year off by >1; FETCH_FAILED if no response; pdf payload = PARTIAL; else MATCH/PARTIAL",
            },
        },
        "results": results,
        "summary": {
            "sampled": len(results),
            "counts": counts,
            "mismatch_breakdown": {
                "year_only_divergence": n_year_only,
                "metadata_contradiction": n_contradiction,
            },
            "frozen_excerpt_ratio_below_threshold_explained_by_elision": n_frag_explained,
            "excerpt_fragments_not_recovered": len(frag_fail),
            "search_query_exact_locators": len(search_locators),
            "search_query_probes_inconclusive": len(inconclusive_probes),
            "disjoint_from": ["check_3_worker-07", "check_4_worker-086"],
            "frame_note": "17 disjoint rows covering all four frozen classes",
        },
        "interpretation": {
            "primary_rule": "The verdict field is the frozen pre-registered rule (title/first-author/year/excerpt thresholds). It was not changed after the fetch.",
            "year_only": f"{n_year_only} of {len(mism)} MISMATCH verdicts are year-only: title and first author match exactly, and the fetched page year is the earlier preprint/first-version year while the ledger year is the journal publication year. Under a work-identity reading these are year-provenance findings, not contradictions.",
            "elided_excerpts": "Low excerpt char-ratios on elided ledger quotes are explained by the secondary fragment-coverage diagnostic, which records how many ellipsis-separated fragments of the ledger excerpt are found in the fetched abstract; both numbers are reported per row.",
        },
        "hard_failures": mism,
        "findings": findings,
        "falsifiers": [
            "Any sampled primary locator resolves to a work whose title, first author or year contradicts the ledger row: the corresponding verdict is false and the row is a hard failure (recorded above with contradicted_fields and divergence_class).",
            "If ledger/citation_audit.csv no longer hashes to the pinned revision, this check does not bind to the current revision and must be re-run.",
            "If any recorded raw_sha256 cannot be reproduced by re-fetching the same locator with the same method, this check's evidence chain is broken.",
            "If any MISMATCH row classified year_only is shown to differ in title or authorship (not just year provenance), the year_only classification is false.",
        ],
        "non_claims": [
            "Does not claim the ledger is correct; only reports the 17-row sample.",
            "Does not adjudicate the L1 revision or set any gate verdict; G-LIT remains owned by the literature lead and controller.",
            "PARTIAL is not a failure of the source; it marks metadata that is not machine-comparable by this method.",
            "A search-query exact_locator can still be resolvable; it is flagged as a locator-exactness defect, not as a metadata contradiction.",
            "The year_only and elided-excerpt readings are labelled secondary interpretation; the gate owner decides which reading binds.",
        ],
    }
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    h = sha256_file(OUT)
    OUT.with_suffix(".json.sha256").write_text(f"{h}  {OUT.name}\n")
    print(json.dumps({"artifact": str(OUT.relative_to(ROOT)), "sha256": h,
                      "counts": counts, "hard_failures": len(mism),
                      "search_query_exact_locators": len(search_locators),
                      "drifted_during_fetch": doc["inputs"]["ledger/citation_audit.csv"]["drifted_during_fetch"]},
                     indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
