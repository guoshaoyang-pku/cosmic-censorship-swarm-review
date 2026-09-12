#!/usr/bin/env python3
"""W099 L1 spot check #4 (G-LIT): independent re-fetch of 7 ledger rows.

Class-bound task, node L1, gate G-LIT. Bounded execution worker worker-099.
Independent of spots #1 (deepseek-flash-10, rows 1-20), #2 (deepseek-flash-11, rows 21-40)
and #3 (deepseek-flash-07, rows 41-95); reviewer distinct from all three.

Frozen sample (declared before any fetch):

  S1 uncovered rows : 96, 97  -- the only data rows never sampled by spots #1-#3.
  S2 hash-rebind    : rows == 5 (mod 10) in 1..40 -> 5, 15, 25, 35. Spots #1/#2 bound
                      older csv hashes, so these rows are re-fetched at the current
                      pinned hash 315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9.
  S3 class augment  : row 14 -- deterministic pre-fetch rule "lowest-index row in 1..40
                      whose class_mapping contains both AF-SCC-C2-VAC-GEN and
                      AF-WCC-SCALAR-SPH"; needed so the check covers all four classes.

The run is fail-closed: it aborts before fetching if the ledger sha256 differs from the
pin, and it re-hashes the ledger after fetching and records any drift.

Outputs (write-once, hashed):
  artifacts/worker-099/l1_spotcheck/spotcheck-l1-099.json
  artifacts/worker-099/l1_spotcheck/spotcheck-l1-099.json.sha256
  artifacts/worker-099/l1_spotcheck/fetched/<citation_id>.<source>.json   (raw bodies)

No node status, gate verdict, or ledger edit is claimed by this script.
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
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
ACTOR = "worker-099"
CHECK_NUMBER = 4

EXPECTED_LEDGER_SHA256 = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
LEDGER_REL = "ledger/citation_audit.csv"
THEOREMS_REL = "ledger/theorems.jsonl"

SAMPLED_ROWS = [
    (5, "S2", "hash-rebind every 10th row (1..40)"),
    (14, "S3", "class augmentation: lowest-index row in 1..40 with AF-SCC-C2-VAC-GEN + AF-WCC-SCALAR-SPH"),
    (15, "S2", "hash-rebind every 10th row (1..40)"),
    (25, "S2", "hash-rebind every 10th row (1..40)"),
    (35, "S2", "hash-rebind every 10th row (1..40)"),
    (96, "S1", "uncovered by spots #1-#3"),
    (97, "S1", "uncovered by spots #1-#3"),
]

CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]

UA = {"User-Agent": "ai4math-swarm-worker-099/0.1 (L1 spot check #4; read-only; contact: local swarm)"}
LANDING_UA = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/120.0 Safari/537.36 ai4math-swarm-worker-099/0.1")}
HOST_MIN_INTERVAL = {"export.arxiv.org": 4.0, "arxiv.org": 3.0, "api.crossref.org": 2.0,
                     "inspirehep.net": 1.0, "api.openalex.org": 1.0, "doi.org": 2.0,
                     "link.springer.com": 2.0}
LAST_CALL: dict = {}

QC_RANK = {"grounded_in_abstract": 3, "close_paraphrase": 2, "not_found_in_abstract": 1}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / LEDGER_REL).exists():
            return parent
    raise SystemExit(f"could not locate repo root ({LEDGER_REL})")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = s.encode("ascii", "ignore").decode()
    s = re.sub(r"\$([^$]*)\$", r" \1 ", s)  # keep inline-math content
    s = re.sub(r"\\[a-zA-Z]+", " ", s)
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def families(names) -> set:
    out = set()
    for n in names:
        n = norm(n)
        if n:
            out.add(n.split()[-1])
    return out


# ---------------------------------------------------------------- fetchers

def http_get(url: str, attempts: int = 5, ua: dict | None = None):
    host = urllib.parse.urlparse(url).netloc
    delay = HOST_MIN_INTERVAL.get(host, 1.0)
    last_err = None
    for k in range(attempts):
        wait = delay - (time.time() - LAST_CALL.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers=ua or UA)
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                LAST_CALL[host] = time.time()
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            LAST_CALL[host] = time.time()
            last_err = e
            if e.code in (429, 500, 502, 503, 504) and k < attempts - 1:
                ra = e.headers.get("Retry-After") if e.headers else None
                back = float(ra) if (ra and str(ra).isdigit()) else min(60.0, 6.0 * (2 ** k))
                time.sleep(back)
                continue
            raise
        except Exception as e:  # noqa: BLE001 - network errors retried
            LAST_CALL[host] = time.time()
            last_err = e
            if k < attempts - 1:
                time.sleep(min(30.0, 4.0 * (2 ** k)))
                continue
            raise
    raise last_err


def parse_arxiv(body: bytes):
    text = body.decode("utf-8", "replace")
    entries = re.findall(r"<entry>(.*?)</entry>", text, re.S)
    if not entries:
        return None
    e = entries[0]

    def tag(t):
        m = re.search(rf"<{t}[^>]*>(.*?)</{t}>", e, re.S)
        return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""

    published = tag("published")
    return {
        "source": "arxiv_api",
        "title": tag("title"),
        "authors": [re.sub(r"\s+", " ", a).strip() for a in re.findall(r"<name>(.*?)</name>", e, re.S)],
        "year": published[:4] if published else "",
        "published": published,
        "abstract": tag("summary"),
        "doi": tag("doi"),
        "arxiv_version": tag("id").rsplit("/", 1)[-1],
    }


def parse_arxiv_abs(body: bytes):
    """Parse the arXiv abstract page (the row's primary locator when it is arxiv.org/abs/...)."""
    text = body.decode("utf-8", "replace")

    def meta(name):
        m = re.search(rf'<meta\s+name="{name}"\s+content="([^"]*)"', text, re.I)
        return m.group(1).strip() if m else ""

    title = meta("citation_title")
    authors = [a.strip() for a in re.findall(r'<meta\s+name="citation_author"\s+content="([^"]*)"', text, re.I)]
    date = meta("citation_date")
    m = re.search(r'<blockquote class="abstract[^"]*">(.*?)</blockquote>', text, re.S)
    abstract = ""
    if m:
        abstract = re.sub(r"<[^>]+>", " ", m.group(1))
        abstract = re.sub(r"\s+", " ", abstract).strip()
    if not title:
        return None
    return {
        "source": "arxiv_abs_page",
        "title": title,
        "authors": authors,
        "year": date[:4] if date else "",
        "published": date,
        "abstract": abstract,
        "doi": meta("citation_doi"),
        "arxiv_version": meta("citation_arxiv_id"),
    }


def parse_crossref(body: bytes):
    doc = json.loads(body.decode("utf-8", "replace"))
    m = doc.get("message") or {}
    title = (m.get("title") or [""])[0]
    authors = []
    for a in m.get("author") or []:
        authors.append(" ".join(x for x in (a.get("given"), a.get("family")) if x))
    year = ""
    for key in ("published-print", "published", "issued", "created"):
        dp = ((m.get(key) or {}).get("date-parts") or [[None]])[0]
        if dp and dp[0]:
            year = str(dp[0])
            break
    abstract = re.sub(r"<[^>]+>", " ", m.get("abstract") or "")
    return {
        "source": "crossref_api",
        "title": title,
        "authors": authors,
        "year": year,
        "published": year,
        "abstract": re.sub(r"\s+", " ", abstract).strip(),
        "doi": m.get("DOI", ""),
        "journal_ref": (m.get("container-title") or [""])[0],
    }


def parse_inspire(body: bytes):
    doc = json.loads(body.decode("utf-8", "replace"))
    md = doc.get("metadata") or {}
    titles = md.get("titles") or [{}]
    authors = [a.get("full_name", "") for a in (md.get("authors") or [])]
    abstracts = md.get("abstracts") or []
    year = ""
    for key in ("earliest_date", "preprint_date"):
        v = md.get(key)
        if isinstance(v, str) and len(v) >= 4:
            year = v[:4]
            break
    if not year:
        for pi in md.get("publication_info") or []:
            if pi.get("year"):
                year = str(pi["year"])
                break
    return {
        "source": "inspirehep_api",
        "title": titles[0].get("title", ""),
        "authors": authors,
        "year": year,
        "published": (md.get("earliest_date") or "")[:10],
        "abstract": re.sub(r"\s+", " ", (abstracts[0].get("value", "") if abstracts else "")).strip(),
        "doi": ((md.get("dois") or [{}])[0].get("value", "")),
    }


def parse_openalex(body: bytes):
    """OpenAlex work record; abstract is an inverted index when available."""
    doc = json.loads(body.decode("utf-8", "replace"))
    inv = doc.get("abstract_inverted_index") or {}
    pos = {}
    for w, idxs in inv.items():
        for i in idxs:
            pos[i] = w
    abstract = " ".join(pos[i] for i in sorted(pos)) if pos else ""
    authors = [a.get("author", {}).get("display_name", "") for a in (doc.get("authorships") or [])]
    year = doc.get("publication_year")
    return {
        "source": "openalex_api",
        "title": doc.get("title") or doc.get("display_name") or "",
        "authors": authors,
        "year": str(year) if year else "",
        "published": str(year) if year else "",
        "abstract": abstract,
        "doi": (doc.get("doi") or "").replace("https://doi.org/", ""),
    }


def parse_landing_page(body: bytes):
    """Generic publisher/DOI landing page: meta tags plus common abstract containers."""
    text = body.decode("utf-8", "replace")

    def meta(name):
        m = re.search(rf'<meta\s+name="{name}"\s+content="([^"]*)"', text, re.I)
        if not m:
            m = re.search(rf'<meta\s+property="{name}"\s+content="([^"]*)"', text, re.I)
        return m.group(1).strip() if m else ""

    title = meta("citation_title") or meta("og:title") or meta("dc.title")
    authors = [a.strip() for a in re.findall(r'<meta\s+name="citation_author"\s+content="([^"]*)"', text, re.I)]
    abstract = ""
    for pat in (r'<div[^>]*id="Abs1-content"[^>]*>(.*?)</div>',
                r'<section[^>]*data-title="Abstract"[^>]*>(.*?)</section>',
                r'<div[^>]*class="[^"]*abstract[^"]*"[^>]*>(.*?)</div>'):
        m = re.search(pat, text, re.S | re.I)
        if m:
            abstract = re.sub(r"<[^>]+>", " ", m.group(1))
            break
    if not abstract:
        abstract = meta("description") or meta("og:description") or meta("dc.description")
    abstract = re.sub(r"\s+", " ", abstract).strip()
    return {
        "source": "doi_landing_page",
        "title": title,
        "authors": authors,
        "year": (meta("citation_date") or meta("citation_publication_date") or "")[:4],
        "published": meta("citation_date") or meta("citation_publication_date"),
        "abstract": abstract,
        "doi": meta("citation_doi"),
    }


def sources_for_row(row: dict):
    out = []
    arxiv_id = (row.get("arxiv_id") or "").strip()
    doi = (row.get("doi") or "").strip()
    url = (row.get("url") or "").strip()
    if arxiv_id:
        out.append(("arxiv_api", f"https://export.arxiv.org/api/query?id_list={arxiv_id}", parse_arxiv))
    if doi:
        out.append(("crossref_api", f"https://api.crossref.org/works/{doi}", parse_crossref))
    m = re.match(r"https?://inspirehep\.net/api/literature/(\d+)", url)
    if m:
        out.append(("inspirehep_api", f"https://inspirehep.net/api/literature/{m.group(1)}", parse_inspire))
    return out


# ---------------------------------------------------------------- comparison

LABEL_RE = re.compile(
    r"^\s*(?:arxiv\s+abstract(?:\s*\(exact excerpt\))?|springer\s+abstract|"
    r"international\s+press\s+abstract|crossref\s+record|abstract|excerpt)\s*[:\-]\s*",
    re.I,
)


def strip_quotes(s: str) -> str:
    s = s.strip()
    for lq, rq in (('"', '"'), ("'", "'"), ("\u201c", "\u201d"), ("\u2018", "\u2019")):
        if s.startswith(lq) and s.endswith(rq) and len(s) > 2:
            s = s[1:-1].strip()
    return s


METADATA_LABEL_RE = re.compile(
    r"\s*\b(?:journal[- ]ref|journal reference|journal|venue|doi|arxiv(?:\s*id)?|publisher|comments|url)\s*[:\-]",
    re.I,
)


def clean_excerpt(evidence_excerpt: str) -> str:
    """Drop the leading source label, wrapping quotes, trailing ellipsis, and any
    journal-ref/venue metadata tail that some ledger excerpts append to the quote."""
    q = strip_quotes(LABEL_RE.sub("", (evidence_excerpt or "").strip()))
    q = re.sub(r"[\u2026]\s*$", "", q)
    m = METADATA_LABEL_RE.search(q)
    if m and m.start() > 40:
        q = q[:m.start()].strip()
    return q


def quote_check(evidence_excerpt: str, abstract: str) -> str:
    if not abstract:
        return "no_abstract_available"
    if not evidence_excerpt:
        return "not_checked"
    q = clean_excerpt(evidence_excerpt)
    segs = [s for s in re.split(r"\s*(?:\.\.\.|\u2026)\s*", q) if len(norm(s).split()) >= 3]
    if not segs:
        return "not_found_in_abstract"
    a = norm(abstract)
    hits = 0
    for s in segs:
        toks = norm(s).split()
        found = " ".join(toks) in a and len(toks) >= 6
        if not found and len(toks) >= 7:  # tolerate a mid-word truncation at segment end
            found = " ".join(toks[:-1]) in a
        if found:
            hits += 1
    if hits / len(segs) >= 0.8 and hits >= 1:
        return "grounded_in_abstract"
    sm = difflib.SequenceMatcher(None, norm(q), a)
    if sm.ratio() >= 0.6:
        return "close_paraphrase"
    return "not_found_in_abstract"


NEG_TOKENS = {"not", "no", "never", "cannot", "neither", "nor", "without", "fails", "fail"}
ANTONYM_PAIRS = [{"past", "future"}, {"before", "after"}, {"increase", "decrease"},
                 {"increases", "decreases"}, {"upper", "lower"}, {"positive", "negative"},
                 {"inside", "outside"}, {"ingoing", "outgoing"}]


def quote_contradiction(evidence_excerpt: str, abstract: str) -> list:
    """Material mismatches between the quoted ledger text and the fetched abstract.

    Reproducible token-diff rule, applied only when the quote is >=15 tokens and at least
    35% of it aligns to the abstract:
      * an aligned replace where one side carries one member of an antonym pair and the
        other side carries the other member (e.g. past/future, before/after);
      * an unaligned gap of >=3 tokens containing a negation token (a denial present in
        the source but omitted from the quote, or added by the quote).
    Returns [] when nothing material is detected.
    """
    q = norm(clean_excerpt(evidence_excerpt)).split()
    a = norm(abstract).split()
    if len(q) < 15 or not a:
        return []
    sm = difflib.SequenceMatcher(None, q, a, autojunk=False)
    matched = sum(b.size for b in sm.get_matching_blocks())
    if matched / len(q) < 0.35:
        return []
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        qs, as_ = q[i1:i2], a[j1:j2]
        if tag == "replace":
            for pair in ANTONYM_PAIRS:
                if (pair & set(qs)) and (pair & set(as_)) and (pair & set(qs)) != (pair & set(as_)):
                    out.append({"kind": "antonym_replace",
                                "ledger_span": " ".join(qs)[:140],
                                "source_span": " ".join(as_)[:140]})
        if tag in ("insert", "delete", "replace") and len(qs) >= 3 and (set(qs) & NEG_TOKENS):
            # two or more numerals in a short diff gap marks a reference/venue/numbering
            # artifact rather than prose negation, so it is not reported
            if sum(t.isdigit() for t in qs) < 2:
                out.append({"kind": "negation_in_quote_not_in_source",
                            "ledger_span": " ".join(qs)[:140], "source_span": " ".join(as_)[:140]})
        if tag in ("insert", "delete", "replace") and len(as_) >= 3 and (set(as_) & NEG_TOKENS):
            if sum(t.isdigit() for t in as_) < 2:
                out.append({"kind": "negation_in_source_omitted_by_quote",
                            "ledger_span": " ".join(qs)[:140], "source_span": " ".join(as_)[:140]})
    seen, uniq = set(), []
    for d in out:
        k = (d["kind"], d["ledger_span"], d["source_span"])
        if k not in seen:
            seen.add(k)
            uniq.append(d)
    return uniq


def alignment_stats(evidence_excerpt: str, abstract: str) -> dict:
    """How much of the quote aligns token-for-token to the abstract (0..1) and how many
    quote tokens differ. Discloses whether a non-grounded row is a small-span divergence
    or a wholesale mismatch."""
    q = norm(clean_excerpt(evidence_excerpt)).split()
    a = norm(abstract).split()
    if not q or not a:
        return {"quote_tokens": len(q), "aligned_fraction": 0.0, "differing_tokens": len(q)}
    matched = sum(b.size for b in difflib.SequenceMatcher(None, q, a, autojunk=False).get_matching_blocks())
    return {"quote_tokens": len(q), "aligned_fraction": round(matched / len(q), 4),
            "differing_tokens": len(q) - matched}


def title_verdict(ledger_title: str, fetched_title: str) -> str:
    a, b = norm(ledger_title), norm(fetched_title)
    if not a or not b:
        return "missing"
    if a == b or a in b or b in a:
        return "strong"
    r = difflib.SequenceMatcher(None, a, b).ratio()
    if r >= 0.9:
        return "strong"
    if r >= 0.6:
        return "weak"
    return "mismatch"


ABSTRACT_PREF = ["arxiv_api", "arxiv_abs_page", "arxiv_api_v1", "arxiv_abs_page_v1",
                 "inspirehep_api", "openalex_api", "doi_landing_page", "crossref_api"]


def compare_row(row: dict, sources: list) -> dict:
    parsed = [s["parsed"] for s in sources if s.get("parsed")]
    by = {}
    for p in parsed:
        by[p["source"]] = p

    # journal metadata preferred from Crossref, then INSPIRE, then arXiv
    meta = by.get("crossref_api") or by.get("inspirehep_api") or by.get("arxiv_api") or {}
    years = sorted({int(p["year"]) for p in parsed if str(p.get("year", "")).isdigit()})

    qc_by_source = {}
    contradictions_by_source = {}
    alignment_by_source = {}
    for name in ABSTRACT_PREF:
        if by.get(name, {}).get("abstract"):
            q = quote_check(row.get("evidence_excerpt", ""), by[name]["abstract"])
            qc_by_source[name] = q
            if q in {"close_paraphrase", "not_found_in_abstract"}:
                alignment_by_source[name] = alignment_stats(row.get("evidence_excerpt", ""), by[name]["abstract"])
                con = quote_contradiction(row.get("evidence_excerpt", ""), by[name]["abstract"])
                if con:
                    contradictions_by_source[name] = con
    best_src, qc = None, "no_abstract_available"
    for name in ABSTRACT_PREF:
        q = qc_by_source.get(name)
        if q is None:
            continue
        if best_src is None or QC_RANK.get(q, 0) > QC_RANK.get(qc, 0):
            best_src, qc = name, q
    abstract = by[best_src]["abstract"] if best_src else ""
    contradiction = []
    for name in ABSTRACT_PREF:
        for d in contradictions_by_source.get(name, []):
            if d not in contradiction:
                contradiction.append(d)

    tv = title_verdict(row.get("title", ""), meta.get("title", ""))
    led_fam = families(re.split(r"[;,]| and ", row.get("authors", "")))
    fet_fam = set()
    for p in parsed:
        fet_fam |= families(p.get("authors") or [])
    author_ok = bool(led_fam & fet_fam)
    ledger_year = int(row["year"]) if str(row.get("year", "")).isdigit() else None
    year_ok = bool(ledger_year is not None and ledger_year in years)
    year_note = None
    if not year_ok and ledger_year is not None and years:
        if any(abs(ledger_year - y) <= 1 for y in years):
            year_ok = True
            year_note = (f"ledger year {ledger_year} vs fetched {years}: within 1 year "
                         f"(preprint/journal convention)")
        else:
            year_note = f"ledger year {ledger_year} vs fetched {years}: unexplained"
    if qc == "no_abstract_available" and (row.get("evidence_type") == "metadata" or tv == "strong"):
        qc = "metadata_record_consistent"

    verdict = "MATCH"
    if tv == "mismatch" or not author_ok:
        verdict = "MISMATCH"
    elif qc != "grounded_in_abstract" and contradiction:
        verdict = "FAIL"
    elif tv == "weak" or not year_ok or qc in {"close_paraphrase", "not_found_in_abstract", "metadata_record_mismatch"}:
        verdict = "PARTIAL"

    return {
        "fetched": {
            "title": meta.get("title", ""),
            "authors": meta.get("authors", []),
            "year": meta.get("year", ""),
            "source_years": years,
            "source_titles": {k: v.get("title", "") for k, v in by.items()},
            "abstract_source": best_src,
            "abstract_head": abstract[:300],
        },
        "comparison": {
            "title_verdict": tv,
            "author_ok": author_ok,
            "ledger_families": sorted(led_fam),
            "fetched_families": sorted(fet_fam),
            "year_ok": year_ok,
            "ledger_year": row.get("year", ""),
            "fetched_years": years,
            "year_note": year_note,
            "quote_check": qc,
            "quote_check_by_source": qc_by_source,
            "alignment_by_source": alignment_by_source,
            "quote_contradiction": contradiction,
            "quote_contradiction_by_source": contradictions_by_source,
        },
        "verdict": verdict,
    }


def fetch_into(rec: dict, root: Path, fetched_dir: Path, row: dict, source: str, url: str, parser,
               version_fallback: bool = False, attempts: int = 5, ua: dict | None = None):
    entry = {"source": source, "locator_used": url}
    if version_fallback:
        entry["version_fallback"] = True
    try:
        status, body = http_get(url, attempts=attempts, ua=ua)
    except Exception as exc:  # noqa: BLE001 - recorded as evidence
        entry["error"] = f"{type(exc).__name__}: {exc}"
        rec["sources"].append(entry)
        return
    raw_path = fetched_dir / f"{row.get('citation_id','row')}.{source}.json"
    raw_path.write_bytes(body)
    entry.update({"http_status": status, "bytes": len(body), "sha256": sha256_bytes(body),
                  "raw_path": str(raw_path.relative_to(root))})
    try:
        parsed = parser(body)
        if isinstance(parsed, dict):
            parsed["source"] = source  # keep the label unique per fetched source
        entry["parsed"] = parsed
    except Exception as exc:  # noqa: BLE001
        entry["parse_error"] = f"{type(exc).__name__}: {exc}"
    rec["sources"].append(entry)


def main() -> int:
    root = repo_root()
    ledger = root / LEDGER_REL
    outdir = root / "artifacts" / "worker-099" / "l1_spotcheck"
    fetched_dir = outdir / "fetched"
    outdir.mkdir(parents=True, exist_ok=True)
    fetched_dir.mkdir(parents=True, exist_ok=True)

    sha_before = sha256_file(ledger)
    if sha_before != EXPECTED_LEDGER_SHA256:
        print(f"FAIL-CLOSED: {LEDGER_REL} sha256={sha_before} != pinned {EXPECTED_LEDGER_SHA256}")
        return 2

    with open(ledger, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    n_rows = len(rows)
    theorems_sha = sha256_file(root / THEOREMS_REL) if (root / THEOREMS_REL).exists() else None

    results = []
    for lineno, rule, why in SAMPLED_ROWS:
        if not (1 <= lineno <= n_rows):
            results.append({"row": lineno, "verdict": "MISMATCH", "error": "row out of frame"})
            continue
        row = rows[lineno - 1]
        rec = {
            "row": lineno,
            "citation_id": row.get("citation_id", ""),
            "bibkey": row.get("bibkey", ""),
            "class_mapping": row.get("class_mapping", ""),
            "used_by_theorems": row.get("used_by_theorems", ""),
            "sample_rule": rule,
            "sample_reason": why,
            "ledger": {
                "title": row.get("title", ""),
                "authors": row.get("authors", ""),
                "year": row.get("year", ""),
                "venue": row.get("venue", ""),
                "doi": row.get("doi", ""),
                "arxiv_id": row.get("arxiv_id", ""),
                "evidence_type": row.get("evidence_type", ""),
                "verdict_recorded": row.get("verdict", ""),
                "evidence_excerpt": row.get("evidence_excerpt", ""),
            },
            "sources": [],
            "fetched_at": now(),
        }
        for source, url, parser in sources_for_row(row):
            fetch_into(rec, root, fetched_dir, row, source, url, parser,
                       attempts=2 if source.startswith("arxiv_api") else 5)
        # arXiv API is rate-limited swarm-wide; the abs page is the row's own locator and a
        # bounded fallback when the API returns 429 after retries.
        arxiv_id = (row.get("arxiv_id") or "").strip()
        if arxiv_id and re.match(r"^[\w.\-/]+$", arxiv_id) and not any(
                s.get("parsed") and s["source"] in ("arxiv_api", "arxiv_abs_page") for s in rec["sources"]):
            fetch_into(rec, root, fetched_dir, row, "arxiv_abs_page",
                       f"https://arxiv.org/abs/{arxiv_id}", parse_arxiv_abs)
        rec.update(compare_row(row, rec["sources"]))

        # bounded extra evidence, fetched only while the excerpt is not yet grounded
        doi = (row.get("doi") or "").strip()
        extra_note = []
        if rec["comparison"]["quote_check"] != "grounded_in_abstract" and doi:
            fetch_into(rec, root, fetched_dir, row, "openalex_api",
                       f"https://api.openalex.org/works/doi:{doi}", parse_openalex)
            rec.update(compare_row(row, rec["sources"]))
            extra_note.append("openalex_api fetched (published-version abstract when available)")
        if rec["comparison"]["quote_check"] != "grounded_in_abstract" and doi:
            fetch_into(rec, root, fetched_dir, row, "doi_landing_page",
                       f"https://doi.org/{doi}", parse_landing_page, ua=LANDING_UA)
            rec.update(compare_row(row, rec["sources"]))
            extra_note.append("doi_landing_page fetched (publisher abstract container)")

        # arXiv version fallback: only if still not groundable
        if (arxiv_id and rec["comparison"]["quote_check"] != "grounded_in_abstract"
                and re.match(r"^[\w.\-/]+$", arxiv_id) and not arxiv_id.endswith("v1")):
            fetch_into(rec, root, fetched_dir, row, "arxiv_api_v1",
                       f"https://export.arxiv.org/api/query?id_list={arxiv_id}v1", parse_arxiv,
                       version_fallback=True, attempts=2)
            if not any(s.get("parsed") and s["source"] == "arxiv_api_v1" for s in rec["sources"]):
                fetch_into(rec, root, fetched_dir, row, "arxiv_abs_page_v1",
                           f"https://arxiv.org/abs/{arxiv_id}v1", parse_arxiv_abs,
                           version_fallback=True)
            rec.update(compare_row(row, rec["sources"]))
            extra_note.append("arXiv v1 fetched as version fallback")
        if extra_note:
            rec["extra_evidence_note"] = "; ".join(extra_note)
        results.append(rec)

    sha_after = sha256_file(ledger)
    summary = {
        "checked": len(results),
        "MATCH": sum(1 for r in results if r.get("verdict") == "MATCH"),
        "PARTIAL": sum(1 for r in results if r.get("verdict") == "PARTIAL"),
        "FAIL": sum(1 for r in results if r.get("verdict") == "FAIL"),
        "MISMATCH": sum(1 for r in results if r.get("verdict") == "MISMATCH"),
        "FETCH_FAILED": sum(1 for r in results if r.get("verdict") == "FETCH_FAILED"),
        "quote_grounding": {},
    }
    for r in results:
        qc = (r.get("comparison") or {}).get("quote_check")
        if qc:
            summary["quote_grounding"][qc] = summary["quote_grounding"].get(qc, 0) + 1

    hard_failures = []
    if sha_after != sha_before:
        hard_failures.append({
            "id": "W099-L1S4-HF-01",
            "severity": "high",
            "finding": f"{LEDGER_REL} drifted during fetch ({sha_before} -> {sha_after}); row-to-hash binding void for this run",
        })
    for r in results:
        if r.get("verdict") in {"MISMATCH", "FAIL"}:
            cmp_ = r.get("comparison") or {}
            identity_ok = (cmp_.get("title_verdict") == "strong" and cmp_.get("author_ok")
                           and cmp_.get("year_ok"))
            hard_failures.append({
                "id": f"W099-L1S4-HF-{r['citation_id']}",
                "severity": "high",
                "finding": (f"{r['citation_id']} row {r['row']}: "
                            f"{'excerpt-level' if identity_ok else 'identity+excerpt'} contradiction with the "
                            f"fetched source (verdict {r['verdict']}; title/author/year "
                            f"{'match' if identity_ok else 'do not all match'})"),
                "quote_contradiction": cmp_.get("quote_contradiction", []),
            })

    classes_covered = sorted({c for r in results for c in (r.get("class_mapping") or "").split(";") if c in CLASS_IDS})

    findings = [
        {"id": "W099-L1S4-F-01", "severity": "info",
         "finding": f"{summary['MATCH']}/{summary['checked']} sampled locators re-fetch to the recorded work; "
                    f"{summary['PARTIAL']} partial, {summary['FAIL']} fail, {summary['MISMATCH']} mismatch, "
                    f"{summary['FETCH_FAILED']} fetch failure."},
        {"id": "W099-L1S4-F-02", "severity": "info",
         "finding": "Abstract/metadata-level check only; verification_status=abstract-read remains the honest level for the checked rows."},
        {"id": "W099-L1S4-F-03", "severity": "info",
         "finding": f"quote grounding: {json.dumps(summary['quote_grounding'], sort_keys=True)}"},
    ]
    for r in results:
        cmp_ = r.get("comparison") or {}
        if cmp_.get("quote_contradiction"):
            findings.append({
                "id": f"W099-L1S4-F-{r['citation_id']}-CON",
                "severity": "high",
                "finding": (f"{r['citation_id']} row {r['row']}: ledger excerpt is contradicted by the fetched "
                            f"source(s) {sorted(cmp_.get('quote_contradiction_by_source', {}))} at "
                            f"{len(cmp_['quote_contradiction'])} span(s); quote_check={cmp_.get('quote_check')}; "
                            f"alignment={json.dumps(cmp_.get('alignment_by_source', {}), sort_keys=True)}"),
                "quote_contradiction": cmp_["quote_contradiction"],
            })
        elif cmp_.get("quote_check") in {"close_paraphrase", "not_found_in_abstract"}:
            findings.append({
                "id": f"W099-L1S4-F-{r['citation_id']}",
                "severity": "medium",
                "finding": (f"{r['citation_id']} row {r['row']}: ledger excerpt not verbatim-groundable in the fetched "
                            f"abstract ({cmp_['quote_check']}); title/author/year " +
                            ("match" if cmp_.get("title_verdict") == "strong" and cmp_.get("author_ok") else "do not all match")),
            })
        if cmp_.get("year_note"):
            findings.append({
                "id": f"W099-L1S4-F-{r['citation_id']}-Y",
                "severity": "info",
                "finding": f"{r['citation_id']} row {r['row']}: {cmp_['year_note']}",
            })

    artifact = {
        "schema_version": "0.1",
        "artifact_type": "l1_spotcheck",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": CLASS_IDS,
        "actor": ACTOR,
        "reviewer": ACTOR,
        "created_at": now(),
        "check_number": CHECK_NUMBER,
        "independent_of": [
            "reviews/L1-spotcheck-10.json",
            "reviews/L1-spotcheck-11.json",
            "artifacts/worker-07/l1_spotcheck/spotcheck-l1-07.json",
        ],
        "independence_note": (
            "Sampled rows 96-97 (uncovered by #1-#3) plus rows 5,15,25,35 (==5 mod 10 in 1..40, "
            "re-bound to the current csv hash) plus row 14 (pre-declared four-class augmentation). "
            "All locators were re-fetched from the primary APIs; no ledger text was used as evidence."
        ),
        "inputs": {
            LEDGER_REL: {
                "sha256": sha_before,
                "data_rows": n_rows,
                "checked_frame": "data rows 5,14,15,25,35,96,97 of 1..%d" % n_rows,
                "sha256_after_fetch": sha_after,
                "drifted_during_fetch": sha_after != sha_before,
            },
            THEOREMS_REL: {"sha256_seen": theorems_sha, "note": "read-only observation, not adjudicated"},
        },
        "sampling_rule": {
            "frozen_before_fetch": True,
            "frame": f"{LEDGER_REL} data rows 1..{n_rows} at pinned sha256 {EXPECTED_LEDGER_SHA256}",
            "S1_uncovered": "rows 96,97 - the only data rows never sampled by spots #1 (1-20), #2 (21-40), #3 (41-95)",
            "S2_hash_rebind": "rows == 5 (mod 10) in 1..40 -> 5,15,25,35; spots #1/#2 bound older csv hashes, so these rows are re-fetched at the current pinned hash",
            "S3_class_augmentation": "row 14 - lowest-index row in 1..40 whose class_mapping contains both AF-SCC-C2-VAC-GEN and AF-WCC-SCALAR-SPH; required for four-class coverage",
            "sampled_rows": [r for r, _, _ in SAMPLED_ROWS],
            "class_coverage_expected": {
                "AF-WCC-VAC-GEN": [35],
                "AF-SCC-C0-VAC-GEN": [5, 35],
                "AF-SCC-C2-VAC-GEN": [14, 25],
                "AF-WCC-SCALAR-SPH": [14],
            },
        },
        "method": (
            "per row: re-fetch the primary API locator(s) implied by the row's own ids "
            "(arxiv_id -> export.arxiv.org /api/query?id_list=; doi -> api.crossref.org/works/; "
            "inspirehep.net/api/literature/<recid> when the row's url is an INSPIRE record URL); "
            "raw body hashed and stored under fetched/; 429/5xx retried with backoff and per-host pacing; "
            "when the arXiv export API stays rate-limited, the row's own arxiv.org/abs/ page is fetched as "
            "the bounded fallback source; "
            "title compared after case/punctuation/LaTeX normalisation, authors by family name, year "
            "against the journal (Crossref) record when available, quote grounding token-level against "
            "the fetched abstract (elisions split on '...', mid-word truncation tolerated on the final "
            "token, inline LaTeX kept as content). While the excerpt is not yet grounded the script "
            "fetches, in order, the OpenAlex record (published-version abstract when available), the "
            "DOI landing page's abstract container, and arXiv v1; the artifact records every fetched "
            "source and which one grounds the quote. A quote that is not grounded but aligns to the "
            "source abstract (>=35% of the quote) is diffed token-wise; antonym replaces "
            "(past/future, before/after, ...) or negation spans present on one side only are recorded "
            "as quote_contradiction and make the row verdict FAIL."
        ),
        "results": results,
        "summary": summary,
        "classes_covered": classes_covered,
        "classes_missing": [c for c in CLASS_IDS if c not in classes_covered],
        "hard_failures": hard_failures,
        "findings": findings,
        "falsifiers": [
            "Re-running this script at the same pinned csv sha256 returns a different per-row verdict set (non-reproducible fetch evidence).",
            "Any sampled locator resolves to a work whose title/author/year contradicts the row: the corresponding MATCH verdict is false and the row is a hard failure.",
            "Any recorded quote_contradiction is shown to be a normalisation artifact (the ledger excerpt is verbatim in the source after correct normalisation): the FAIL verdict flips to PARTIAL.",
            "A row outside this 7-row sample is later found to have a fabricated locator, which would falsify only the sample-level no-error claim, not the per-row results above.",
        ],
        "non_claims": [
            "Does not claim the ledger is citation-clean outside the 7 sampled rows.",
            "Does not promote any theorem, class, or gate; validation_status is unverified.",
            "Does not edit the ledger or the audit CSV (read-only run).",
        ],
        "reproduce": "python3 artifacts/worker-099/l1_spotcheck/run_spotcheck.py",
    }

    blob = json.dumps(artifact, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    out = outdir / "spotcheck-l1-099.json"
    out.write_text(blob, encoding="utf-8")
    (outdir / "spotcheck-l1-099.json.sha256").write_text(
        f"{sha256_bytes(blob.encode('utf-8'))}  spotcheck-l1-099.json\n", encoding="utf-8"
    )

    print(json.dumps({"artifact": str(out), "sha256": sha256_bytes(blob.encode("utf-8")),
                      "summary": summary, "classes_covered": classes_covered,
                      "hard_failures": hard_failures}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
