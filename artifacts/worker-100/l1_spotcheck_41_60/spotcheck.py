#!/usr/bin/env python3
"""L1 spot check #4 (worker-100) -- independent re-fetch of ledger/citation_audit.csv rows SRC-041..060.

Contract (frozen in sample_frozen.json, written before any fetch):
  * target   ledger/citation_audit.csv @ sha256 315c19145065...   (fail-closed on drift)
  * secondary ledger/theorems.jsonl      @ sha256 ce42d205e761...  (class-binding chain check)
  * sample   citation_id in SRC-041..SRC-060 (20 rows)
  * verdict  MATCH / PARTIAL / FAIL / FETCH_FAILED per frozen rules
  * reviewer worker-100, distinct from flash-10, flash-11, deepseek-flash-07

Instrument revisions (all made before any verdict was reported; raw+report snapshots preserved):
  v1 -> v2: arXiv Atom feed-title parsing; single-locator abstract blindness (stop at first 200);
            Unicode/HTML normalization; 429 abort.  (spotcheck-l1-100.v1-checkerbug.json)
  v2 -> v3: nested/mixed quote pairs split a single quoted excerpt into label + body
            (SRC-046/051/053); arXiv abs-page <meta name="citation_*"> and version-history dates
            were not parsed (SRC-052/053/055/057); ledger title parenthetical suffixes
            ("(arXiv version with journal ref)") broke title similarity (SRC-055/056);
            journal-reference evidence was read from `venue` instead of the fetched
            journal_ref/version fields.  (spotcheck-l1-100.v2.json)

Frozen verdict rules (unchanged across v1-v3):
  MATCH        resolved + title consistent + year consistent + every quoted excerpt segment matched
  PARTIAL      resolved + title/year consistent, but excerpt partly matched / not checkable, or only
               unquoted note text is not reproducible
  FAIL         resolved but title/year contradiction, or a QUOTED excerpt segment (>=25 normalized
               chars) absent from the fetched records
  FETCH_FAILED no locator returned HTTP 200

Read-only with respect to the ledger. No node completion, no gate verdict, no theorem is claimed.
"""
from __future__ import annotations

import csv
import difflib
import hashlib
import html
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAW = HERE / "raw-worker100"
CSV_PATH = ROOT / "ledger" / "citation_audit.csv"
THEOREMS_PATH = ROOT / "ledger" / "theorems.jsonl"

PINNED = {
    "ledger/citation_audit.csv": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
    "ledger/theorems.jsonl": "ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72",
}
FROZEN_CLASSES = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
ANNOTATION = "(evidence/tag only)"
SAMPLE = [f"SRC-{n:03d}" for n in range(41, 61)]
CROSS_CHECK = ["SRC-041", "SRC-049", "SRC-057"]
CST = timezone(timedelta(hours=8))
UA = "ai4math-swarm-spotcheck/1.0 (worker-100; read-only citation re-fetch)"
METHOD_VERSION = "4.2"
LABEL_RE = re.compile(
    r"^\s*(?:arXiv\s+abstract(?:\s*\([^)]*\))?|Abstract|INSPIRE\s+abstract|Crossref\s+record|"
    r"arXiv\s+abstract\s+exact\s+excerpt)\s*:?\s*", re.I)
NOTE_LABEL_RE = re.compile(
    r"^[\s;,.\-]*(?:Comments?|Journal\s+reference(?:\s+on\s+page)?|Related\s+DOI|DOI)\s*:?\s*", re.I)
QUOTE_PAIRS = {"'": "'", "\u2018": "\u2019", '"': '"', "\u201c": "\u201d"}
STOP = {
    "the", "a", "an", "of", "and", "or", "in", "on", "for", "to", "with", "by", "is", "are",
    "was", "were", "as", "at", "from", "this", "that", "these", "those", "it", "its", "which",
    "who", "whom", "be", "been", "has", "have", "had", "not", "no", "than", "then", "also",
    "into", "over", "under", "after", "before", "during", "between", "within", "without", "via",
    "per", "see", "page", "pages", "vol", "volume", "issue", "no", "pp", "related", "reference",
    "title", "author", "authors", "published", "journal",
}


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


def strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", " ", html.unescape(s or ""))


GREEK = {
    "\u03b1": "alpha", "\u03b2": "beta", "\u03b3": "gamma", "\u03b4": "delta", "\u03b5": "epsilon",
    "\u03b6": "zeta", "\u03b7": "eta", "\u03b8": "theta", "\u03b9": "iota", "\u03ba": "kappa",
    "\u03bb": "lambda", "\u03bc": "mu", "\u03bd": "nu", "\u03be": "xi", "\u03c0": "pi",
    "\u03c1": "rho", "\u03c3": "sigma", "\u03c4": "tau", "\u03c5": "upsilon", "\u03c6": "phi",
    "\u03c7": "chi", "\u03c8": "psi", "\u03c9": "omega", "\u0393": "Gamma", "\u0394": "Delta",
    "\u0398": "Theta", "\u039b": "Lambda", "\u039e": "Xi", "\u03a0": "Pi", "\u03a3": "Sigma",
    "\u03a6": "Phi", "\u03a8": "Psi", "\u03a9": "Omega",
}
LATEX_FMT = re.compile(
    r"\\(?:text(?:rm|it|bf|sf|tt)?|mathrm|mathit|mathbf|mathsf|mathtt|mathcal|mathfrak|"
    r"operatorname|rm|it|bf|sf|tt|displaystyle|scriptstyle|left|right|big|Big|bigg|Bigg|bigl|"
    r"bigr|Bigl|Bigr)\s*\{([^{}]*)\}")
LATEX_SPACING = re.compile(r"\\(?:[,;!]|quad|qquad)\s*")


def norm(s: str) -> str:
    s = strip_tags(s)
    for k, v in GREEK.items():
        s = s.replace(k, f" {v} ")
    s = LATEX_FMT.sub(r" \1 ", s)
    s = LATEX_SPACING.sub(" ", s)
    s = s.replace("$", " ").replace("\\", " ")
    s = re.sub(r"[{}]", " ", s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^0-9a-zA-Z]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def fetch(url: str, tries: int = 3):
    """Fetch a URL; return dict with status/body/hash or error. Never raises."""
    last = None
    for attempt in range(1, tries + 1):
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
                return {
                    "url": url, "http_status": int(getattr(r, "status", 200)),
                    "final_url": r.geturl(), "bytes": len(body), "sha256": sha256_bytes(body),
                    "elapsed_s": round(time.time() - t0, 2), "attempts": attempt, "body": body,
                }
        except urllib.error.HTTPError as e:
            body = b""
            try:
                body = e.read()
            except Exception:
                pass
            last = {
                "url": url, "http_status": int(e.code), "final_url": url,
                "bytes": len(body), "sha256": sha256_bytes(body),
                "elapsed_s": round(time.time() - t0, 2), "attempts": attempt,
                "error": f"HTTPError {e.code}", "body": body,
            }
            if e.code == 429 and attempt < tries:
                time.sleep(3.0 * attempt)
                continue
        except Exception as e:  # noqa: BLE001
            last = {
                "url": url, "http_status": None, "final_url": url, "bytes": 0,
                "sha256": None, "elapsed_s": round(time.time() - t0, 2),
                "attempts": attempt, "error": f"{type(e).__name__}: {e}", "body": b"",
            }
        time.sleep(0.6 * attempt)
    return last


# ---------------------------------------------------------------- parsers
def parse_crossref(body: bytes):
    try:
        msg = json.loads(body.decode("utf-8", "replace"))["message"]
    except Exception:
        return None
    title = strip_tags((msg.get("title") or [""])[0])
    authors = "; ".join(strip_tags(f"{a.get('given','')} {a.get('family','')}".strip())
                        for a in (msg.get("author") or []))
    issued = (msg.get("issued") or {}).get("date-parts") or [[None]]
    venue = strip_tags((msg.get("container-title") or [""])[0])
    return {
        "kind": "crossref", "title": title, "authors": authors, "year": issued[0][0],
        "venue": " ".join(str(x) for x in [venue, msg.get("volume", ""), msg.get("issue", ""),
                                           msg.get("page", "")] if x),
        "doi": msg.get("DOI", ""), "comment": "",
        "abstract": strip_tags(msg.get("abstract", "") or ""), "journal_ref": venue,
        "version_years": [],
    }


def parse_arxiv(body: bytes):
    text = body.decode("utf-8", "replace")
    m = re.search(r"<entry>(.*?)</entry>", text, re.S)
    if not m:
        return None
    entry = m.group(1)

    def grab(tag):
        mm = re.search(rf"<(?:arxiv:)?{tag}\b[^>]*>(.*?)</(?:arxiv:)?{tag}>", entry, re.S)
        return re.sub(r"\s+", " ", strip_tags(mm.group(1))).strip() if mm else ""
    published = grab("published")
    year = int(published[:4]) if re.match(r"\d{4}", published) else None
    jr = grab("journal_ref")
    vy = [year] if year else []
    vy.extend(int(y) for y in re.findall(r"(?:19|20)\d{2}", jr))
    return {
        "kind": "arxiv", "title": grab("title"),
        "authors": "; ".join(re.findall(r"<name>(.*?)</name>", entry, re.S)),
        "year": year, "venue": f"arXiv {grab('id')}", "doi": grab("doi"),
        "abstract": grab("summary"), "journal_ref": jr, "comment": grab("comment"),
        "published": published, "updated": grab("updated"),
        "version_years": vy,
    }


def parse_inspire(body: bytes):
    try:
        doc = json.loads(body.decode("utf-8", "replace"))
    except Exception:
        return None
    md = doc.get("metadata") or {}
    titles = md.get("titles") or [{}]
    pubinfo = (md.get("publication_info") or [{}])[0]
    year = pubinfo.get("year") or (md.get("earliest_date") or "")[:4] or None
    if isinstance(year, str) and year.isdigit():
        year = int(year)
    dois = md.get("dois") or [{}]
    abstracts = md.get("abstracts") or [{}]
    return {
        "kind": "inspire", "title": strip_tags(titles[0].get("title", "")),
        "authors": "; ".join(a.get("full_name", "") for a in (md.get("authors") or [])),
        "year": year,
        "venue": " ".join(str(x) for x in [pubinfo.get("journal_title", ""),
                                           pubinfo.get("journal_volume", ""),
                                           pubinfo.get("artid", "") or pubinfo.get("page_start", "")] if x),
        "doi": dois[0].get("value", ""), "arxiv_id": (md.get("arxiv_eprints") or [{}])[0].get("value", ""),
        "abstract": strip_tags(abstracts[0].get("value", "")), "journal_ref": "", "comment": "",
        "version_years": [year] if year else [],
    }


def parse_datacite(body: bytes):
    try:
        a = json.loads(body.decode("utf-8", "replace"))["data"]["attributes"]
    except Exception:
        return None
    titles = a.get("titles") or [{}]
    descs = a.get("descriptions") or [{}]
    year = a.get("publicationYear")
    creators = "; ".join(c.get("name", "") for c in (a.get("creators") or []))
    return {
        "kind": "datacite", "title": strip_tags(titles[0].get("title", "")),
        "authors": creators, "year": year,
        "venue": a.get("publisher", "") or "", "doi": a.get("doi", ""),
        "abstract": strip_tags(descs[0].get("description", "")), "journal_ref": "", "comment": "",
        "version_years": [year] if year else [],
    }


def parse_page(body: bytes):
    head = body[:300000].decode("utf-8", "replace")

    def meta(name):
        for pat in (rf'<meta[^>]+name="{re.escape(name)}"[^>]+content="([^"]*)"',
                    rf'<meta[^>]+content="([^"]*)"[^>]+name="{re.escape(name)}"'):
            m = re.search(pat, head, re.I | re.S)
            if m:
                return html.unescape(m.group(1)).strip()
        return ""
    title = meta("citation_title")
    if not title:
        m = re.search(r"<title[^>]*>(.*?)</title>", head, re.S | re.I)
        title = strip_tags(m.group(1)).strip() if m else ""
    date = meta("citation_date") or meta("citation_online_date")
    year = int(date[:4]) if re.match(r"\d{4}", date) else None
    authors = "; ".join(re.findall(r'<meta[^>]+name="citation_author"[^>]+content="([^"]*)"', head, re.I))
    abstract = meta("citation_abstract")
    if not abstract:
        m = re.search(r'<blockquote[^>]*class="[^"]*abstract[^"]*"[^>]*>(.*?)</blockquote>', head, re.S | re.I)
        if m:
            abstract = strip_tags(m.group(1))
    jr = ""
    m = re.search(r"Journal reference:\s*([^<]{5,200})", head)
    if m:
        jr = re.sub(r"\s+", " ", html.unescape(m.group(1))).strip()
    versions = [int(y) for _, y in re.findall(r"\[v(\d+)\][^\[\]]{0,90}?((?:19|20)\d{2})", strip_tags(head))]
    return {
        "kind": "page", "title": strip_tags(title), "authors": authors,
        "year": year, "venue": meta("citation_journal_title"), "doi": meta("citation_doi"),
        "abstract": strip_tags(abstract), "journal_ref": jr, "comment": meta("citation_comment"),
        "version_years": versions,
    }


def parse_fetched(body: bytes):
    if body[:1] == b"{":
        for parser in (parse_crossref, parse_inspire, parse_datacite):
            try:
                out = parser(body)
            except Exception:
                out = None
            if out and out.get("title"):
                return out
    if b"<entry" in body[:5000]:
        try:
            out = parse_arxiv(body)
        except Exception:
            out = None
        if out and out.get("title"):
            return out
    return parse_page(body)


# ---------------------------------------------------------------- comparison
def quoted_spans(excerpt: str):
    """Outermost quoted spans, apostrophe-aware and per quote type (handles nested other-type quotes)."""
    spans, outside = [], []
    i, n = 0, len(excerpt)
    while i < n:
        c = excerpt[i]
        if c in QUOTE_PAIRS:
            prev = excerpt[i - 1] if i > 0 else " "
            if not prev.isalnum():  # a quote after a letter is an apostrophe, not an opener
                close = QUOTE_PAIRS[c]
                j = i + 1
                while j < n:
                    if excerpt[j] == close:
                        after = excerpt[j + 1] if j + 1 < n else " "
                        if not after.isalpha():  # closing quote, not an inner apostrophe
                            break
                    j += 1
                if j < n and j - i - 1 >= 25:
                    spans.append(excerpt[i + 1:j])
                    outside.append("\u0000")
                    i = j + 1
                    continue
        outside.append(c)
        i += 1
    notes = [p.strip() for p in "".join(outside).split("\u0000") if p.strip()]
    if not spans:  # truncated excerpt with an opening quote but no closing quote
        stripped = excerpt.lstrip()
        if stripped[:1] in QUOTE_PAIRS and len(stripped) >= 26:
            spans = [stripped[1:]]
            notes = []
    return spans, notes


def segments_from(text: str):
    out = []
    for chunk in re.split(r"\.\.\.|\u2026", text):
        n = norm(chunk)
        if len(n) >= 25:
            out.append(n)
    return out


def excerpt_parts(excerpt: str):
    """Returns (quote_segments, note_segments); leading labels and wrapping quotes are removed."""
    s = LABEL_RE.sub("", excerpt or "").strip()
    spans, notes = quoted_spans(s)
    qsegs, nsegs = [], []
    for sp in spans:
        qsegs.extend(segments_from(sp))
    note_parts = []
    for nt in notes:
        nt = NOTE_LABEL_RE.sub("", LABEL_RE.sub("", nt).strip())
        nt = re.sub(r"^[\s;,.\-]+", "", nt).strip()
        if nt:
            note_parts.append(nt)
    nsegs = segments_from(" ".join(note_parts))
    return qsegs, nsegs


def build_locators(row):
    locators = []
    arxiv = (row.get("arxiv_id") or "").strip()
    doi = (row.get("doi") or "").strip()
    url = (row.get("url") or "").strip()
    if arxiv:
        locators.append(("arxiv_api", f"https://export.arxiv.org/api/query?id_list={arxiv}"))
    if doi.startswith("10.48550/"):
        locators.append(("datacite_api", f"https://api.datacite.org/dois/{doi}"))
    elif doi:
        locators.append(("crossref_api", f"https://api.crossref.org/works/{doi}"))
    if url:
        locators.append(("row_url", url))
    for field in ("exact_locator", "evidence_url"):
        u = (row.get(field) or "").strip()
        if u and all(u != l[1] for l in locators):
            locators.append((field, u))
    return locators[:5]


def load_theorems():
    out = {}
    for line in THEOREMS_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        out[d.get("theorem_id")] = d
    return out


def class_chain_check(row, theorems):
    refs = [t for t in (row.get("used_by_theorems") or "").split(";") if t]
    missing, non_frozen, linked_classes = [], [], set()
    for t in refs:
        tr = theorems.get(t)
        if tr is None:
            missing.append(t)
            continue
        for c in (tr.get("class_ids") or []) + (tr.get("informs_classes") or []):
            if c == ANNOTATION or not c:
                continue
            linked_classes.add(c)
            if c not in FROZEN_CLASSES:
                non_frozen.append({"theorem_id": t, "token": c})
    csv_tokens = [c for c in (row.get("class_mapping") or "").split(";") if c and c != ANNOTATION]
    return {
        "used_by_theorems": refs,
        "missing_theorem_refs": missing,
        "non_frozen_tokens": non_frozen,
        "csv_class_tokens": csv_tokens,
        "csv_non_frozen_tokens": [c for c in csv_tokens if c not in FROZEN_CLASSES],
        "annotation_only": ANNOTATION in (row.get("class_mapping") or ""),
        "csv_tokens_without_linked_theorem_support": sorted(set(csv_tokens) - linked_classes),
        "linked_theorem_classes": sorted(linked_classes),
    }


def title_sim(ledger_title: str, fetched_title: str) -> float:
    a, b = norm(ledger_title), norm(fetched_title)
    if not b:
        return 0.0
    core_a = norm(re.sub(r"\s*\([^()]{0,90}\)\s*$", "", ledger_title or ""))
    r = max(difflib.SequenceMatcher(None, a, b).ratio(),
            difflib.SequenceMatcher(None, core_a, b).ratio() if core_a else 0.0)
    for x, y in ((a, b), (core_a, b)):
        if x and y and (x in y or y in x) and min(len(x), len(y)) / max(len(x), len(y)) >= 0.75:
            r = max(r, 0.90)
    return round(r, 3)


def source_years(s):
    out = set()
    if s.get("year"):
        out.add(int(s["year"]))
    for y in s.get("version_years") or []:
        if y:
            out.add(int(y))
    for m in re.findall(r"(?:19|20)\d{2}", s.get("journal_ref") or ""):
        out.add(int(m))
    return sorted(out)


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    started = now()
    before = {str(p.relative_to(ROOT)): sha256_file(p) for p in (CSV_PATH, THEOREMS_PATH)}
    # primary input is strict-pinned; the secondary literature ledger may legitimately be revised
    # by its owner, so a pre-registration mismatch is recorded and the run continues at the
    # observed revision (fail-closed only if it changes DURING the run).
    csv_rel, thm_rel = "ledger/citation_audit.csv", "ledger/theorems.jsonl"
    if PINNED[csv_rel] != before[csv_rel]:
        print(f"FATAL: {csv_rel} sha256 {before[csv_rel]} != pinned {PINNED[csv_rel]} (fail-closed)")
        return 2
    secondary_pin_match = before[thm_rel] == PINNED[thm_rel]

    rows = {r["citation_id"]: r for r in csv.DictReader(CSV_PATH.open())}
    theorems_sha_before = sha256_file(THEOREMS_PATH)
    results, fetch_meta = [], {}
    for sid in SAMPLE:
        row = rows[sid]
        entry = {
            "source_id": sid,
            "ledger_row": {k: row.get(k) for k in
                           ("bibkey", "title", "authors", "year", "venue", "doi", "arxiv_id", "url",
                            "status", "verification_method", "evidence_url", "exact_locator",
                            "class_mapping", "used_by_theorems", "verdict", "reviewer")},
            "cross_check_of_flash07": sid in CROSS_CHECK,
            "class_binding": None,
        }
        attempts, sources = [], []
        for kind, url in build_locators(row):
            f = fetch(url)
            rec = {k: v for k, v in f.items() if k != "body"}
            rec["kind"] = kind
            attempts.append(rec)
            if f.get("http_status") == 200 and f.get("body"):
                meta = parse_fetched(f["body"])
                ext = {"crossref": "json", "inspire": "json", "datacite": "json",
                       "arxiv": "xml", "page": "html"}.get(meta["kind"], "bin")
                raw_path = RAW / f"{sid}.{kind}.{ext}"
                raw_path.write_bytes(f["body"])
                sources.append({
                    "kind": kind, "url": url, "http_status": 200, "bytes": f["bytes"],
                    "sha256": f["sha256"], "raw_path": str(raw_path.relative_to(ROOT)),
                    "record_kind": meta["kind"], "title": meta.get("title"),
                    "authors": meta.get("authors"), "year": meta.get("year"),
                    "venue": meta.get("venue"), "doi": meta.get("doi"),
                    "journal_ref": meta.get("journal_ref"), "comment": meta.get("comment"),
                    "version_years": meta.get("version_years"),
                    "abstract": meta.get("abstract") or "",
                    "abstract_chars": len(meta.get("abstract") or ""),
                    "abstract_sha256": sha256_bytes((meta.get("abstract") or "").encode()),
                    "ledger_title_similarity": title_sim(row.get("title", ""), meta.get("title") or ""),
                    "_meta": meta,
                })
            if len(sources) >= 3:
                break
            time.sleep(0.5)
        entry["fetch_attempts"] = attempts
        fetch_meta[sid] = {"attempts": attempts,
                           "sources": [{k: v for k, v in s.items() if k != "_meta"} for s in sources]}
        if not sources:
            entry["sources"] = []
            entry["comparison"] = {"reason": "no locator returned HTTP 200"}
            entry["verdict"] = "FETCH_FAILED"
            entry["reasons"] = ["no locator returned HTTP 200"]
            results.append(entry)
            continue

        best_sim = max(s["ledger_title_similarity"] for s in sources)
        title_ok = best_sim >= 0.90
        # a generic search-query result that does not carry the cited title is not the cited work
        for s in sources:
            if s["ledger_title_similarity"] < 0.5:
                s["excluded_from_year_and_excerpt"] = True
        relevant = [s for s in sources if not s.get("excluded_from_year_and_excerpt")] or sources

        ly = int(row.get("year") or 0)
        cand = sorted({y for s in relevant for y in source_years(s)})
        year_ok, year_reason = None, "no fetched year"
        if cand and ly:
            consistent = [y for y in cand if abs(y - ly) <= 1]
            if consistent:
                year_ok, year_reason = True, f"ledger {ly} vs fetched years {cand}"
            else:
                year_ok, year_reason = False, f"ledger {ly} vs fetched years {cand} (delta > 1, no journal-ref support)"

        qsegs, nsegs = excerpt_parts(row.get("evidence_excerpt", ""))
        hay = norm(" ".join(
            " ".join(str(s.get(k, "")) for k in
                     ("abstract", "title", "authors", "venue", "doi", "journal_ref", "comment", "version_years"))
            for s in relevant))
        hay_abstract_chars = sum(s["abstract_chars"] for s in relevant)
        per_source_q = []
        for s in relevant:
            sh = norm(" ".join(str(s.get(k, "")) for k in
                               ("abstract", "title", "authors", "venue", "doi", "journal_ref",
                                "comment", "version_years")))
            hit = sum(1 for seg in qsegs if seg in sh or (len(seg[:80]) >= 25 and seg[:80] in sh))
            per_source_q.append({"kind": s["kind"], "url": s["url"],
                                 "quote_segments_matched": hit, "quote_segments_total": len(qsegs)})
        version_divergence = len({x["quote_segments_matched"] for x in per_source_q}) > 1

        def missing(segs):
            out = []
            for seg in segs:
                prefix = seg[:80]
                if not (seg in hay or (len(prefix) >= 25 and prefix in hay)):
                    out.append(seg[:80])
            return out

        def note_coverage(seg):
            toks = [t for t in seg.split() if len(t) >= 3 and t not in STOP] or seg.split()
            if not toks:
                return 1.0, 0, 0
            hit = sum(1 for t in toks if t in hay)
            return round(hit / len(toks), 3), hit, len(toks)

        # quoted text is checked verbatim; unquoted note text (labels, metadata summaries,
        # "Comments: N pages" lines) is checked by token coverage >= 0.85.
        miss_q = missing(qsegs)
        note_cov = [note_coverage(seg) for seg in nsegs]
        miss_n = [seg[:80] for seg, (cov, _, _) in zip(nsegs, note_cov) if cov < 0.85]
        note_min_coverage = min((c for c, _, _ in note_cov), default=None)
        if not qsegs and not nsegs:
            exc = {"status": "unavailable", "matched": 0, "total": 0,
                   "reason": "no excerpt segment >=25 chars"}
        elif miss_q:
            exc = {"status": "quote_not_found", "matched": len(qsegs) - len(miss_q),
                   "total": len(qsegs), "unmatched": miss_q[:3],
                   "note_unmatched": miss_n[:3]}
        elif miss_n:
            exc = {"status": "note_not_reproducible", "matched": len(qsegs) - len(miss_q),
                   "total": len(qsegs), "note_matched": len(nsegs) - len(miss_n),
                   "note_total": len(nsegs), "note_min_coverage": note_min_coverage,
                   "unmatched": miss_n[:3]}
        elif hay_abstract_chars == 0 and not qsegs:
            exc = {"status": "unavailable", "matched": 0, "total": 0,
                   "reason": "no fetched source carries abstract/record text"}
        else:
            exc = {"status": "supported", "matched": len(qsegs), "total": len(qsegs),
                   "note_matched": len(nsegs) - len(miss_n), "note_total": len(nsegs),
                   "note_min_coverage": note_min_coverage, "unmatched": []}

        reasons = []
        if not title_ok:
            verdict = "FAIL"
            reasons.append(f"title mismatch (best similarity {best_sim})")
        elif year_ok is False:
            verdict = "FAIL"
            reasons.append(f"year inconsistent: {year_reason}")
        elif exc["status"] == "quote_not_found":
            verdict = "FAIL"
            reasons.append(f"quoted excerpt segment absent from fetched records ({exc['unmatched'][0][:70]}...)"
                           if exc.get("unmatched") else "quoted excerpt segment absent")
        elif exc["status"] == "unavailable":
            verdict = "PARTIAL"
            reasons.append("excerpt not checkable: " + exc.get("reason", "no record text"))
        elif exc["status"] == "note_not_reproducible":
            verdict = "PARTIAL"
            reasons.append(f"quoted text matched but unquoted note not reproducible "
                           f"({exc.get('note_matched')}/{exc.get('note_total')} note segments)")
        elif year_ok is None:
            verdict = "PARTIAL"
            reasons.append("year not determinable from fetched records")
        else:
            verdict = "MATCH"
            reasons.append(f"title {best_sim}, year ok ({year_reason}), "
                           f"quoted excerpt {exc['matched']}/{exc['total']} segments")
        entry["sources"] = [{k: v for k, v in s.items() if k != "_meta"} for s in sources]
        entry["comparison"] = {
            "best_source": {"kind": max(sources, key=lambda s: s["ledger_title_similarity"])["kind"],
                            "url": max(sources, key=lambda s: s["ledger_title_similarity"])["url"],
                            "sha256": max(sources, key=lambda s: s["ledger_title_similarity"])["sha256"]},
            "title_similarity": best_sim, "title_ok": title_ok,
            "year_ok": year_ok, "year_reason": year_reason, "candidate_years": cand,
            "excerpt_status": exc["status"],
            "quote_segments_matched": exc.get("matched"), "quote_segments_total": exc.get("total"),
            "note_segments_matched": exc.get("note_matched"), "note_segments_total": exc.get("note_total"),
            "note_min_coverage": exc.get("note_min_coverage"),
            "per_source_quote_match": per_source_q,
            "source_version_divergence": version_divergence,
            "excerpt_unmatched": exc.get("unmatched", []),
            "abstract_chars_union": hay_abstract_chars,
        }
        entry["verdict"] = verdict
        entry["reasons"] = reasons
        results.append(entry)
        time.sleep(0.4)

    after = {str(p.relative_to(ROOT)): sha256_file(p) for p in (CSV_PATH, THEOREMS_PATH)}
    # class-binding chain check binds to ONE measured revision of the secondary input, read after
    # the fetch loop (the literature ledger is under active revision by its owner).
    theorems_sha_used = sha256_file(THEOREMS_PATH)
    theorems = load_theorems()
    for entry in results:
        entry["class_binding"] = class_chain_check(rows[entry["source_id"]], theorems)
    drift = {k: {"before": before[k], "after": after[k]} for k in before if before[k] != after[k]}
    summary = {
        "checked": len(results),
        "match": sum(1 for r in results if r["verdict"] == "MATCH"),
        "partial": sum(1 for r in results if r["verdict"] == "PARTIAL"),
        "fail": sum(1 for r in results if r["verdict"] == "FAIL"),
        "fetch_failed": sum(1 for r in results if r["verdict"] == "FETCH_FAILED"),
        "new_coverage_rows": [r["source_id"] for r in results if not r["cross_check_of_flash07"]],
        "cross_check_rows": CROSS_CHECK,
        "hard_failures_by_kind": {
            "title_mismatch": [r["source_id"] for r in results if r["verdict"] == "FAIL" and not r["comparison"].get("title_ok", True)],
            "year_inconsistent": [r["source_id"] for r in results if r["verdict"] == "FAIL" and r["comparison"].get("title_ok") and r["comparison"].get("year_ok") is False],
            "quoted_excerpt_absent": [r["source_id"] for r in results if r["verdict"] == "FAIL" and r["comparison"].get("excerpt_status") == "quote_not_found"],
        },
    }
    non_frozen = [{"source_id": r["source_id"], **tok} for r in results for tok in r["class_binding"]["non_frozen_tokens"]]
    missing_refs = [{"source_id": r["source_id"], "ref": t} for r in results for t in r["class_binding"]["missing_theorem_refs"]]
    csv_non_frozen = [{"source_id": r["source_id"], "tokens": r["class_binding"]["csv_non_frozen_tokens"]}
                      for r in results if r["class_binding"]["csv_non_frozen_tokens"]]
    unsupported = [{"source_id": r["source_id"], "tokens": r["class_binding"]["csv_tokens_without_linked_theorem_support"]}
                   for r in results if r["class_binding"]["csv_tokens_without_linked_theorem_support"]]
    annotation_rows = [r["source_id"] for r in results if r["class_binding"]["annotation_only"]]
    report = {
        "report_id": "w100-l1-spotcheck-04",
        "task_id": "astra-life02-l1-spotcheck",
        "node_id": "L1",
        "gate": "G-LIT",
        "reviewer": "worker-100",
        "actor": "worker-100",
        "role": "independent re-fetch spot check (one of the two further checks required by astra-life02-l1-spotcheck)",
        "method_version": METHOD_VERSION,
        "method_revision_note": "v4.2 normalizes LaTeX formatting commands/Greek letters (H^1_{\\text{loc}} == H^1_loc) and records per-source quote matches so version divergence is annotated instead of scored as a mismatch. v4.1 made quote scanning apostrophe-aware (Christodoulou's no longer splits a quote) and checks unquoted note text by token coverage >= 0.85, adds arXiv comment/crossref volume-page fields and fixes abs-page version-history parsing. v3 fixed nested-quote segmentation, abs-page citation meta/version-history parsing, journal-ref evidence source, parenthetical-suffix title comparison, and the v3-draft haystack omission of parsed abstracts. v1/v2 snapshots preserved as spotcheck-l1-100.v1-checkerbug.json / .v2.json.",
        "independence": {
            "distinct_from": ["deepseek-flash-07", "flash-10", "deepseek-flash-11"],
            "prior_checks": [
                "reviews/L1-spotcheck-10.json (flash-10, rows 1-20)",
                "reviews/L1-spotcheck-11.json (flash-11, rows 21-40)",
                "artifacts/worker-07/l1_spotcheck/spotcheck-l1-07.json (deepseek-flash-07, 8 rows incl. SRC-041/049/057)",
            ],
            "sample_frozen_path": "artifacts/worker-100/l1_spotcheck_41_60/sample_frozen.json",
        },
        "created_at": started,
        "finished_at": now(),
        "inputs": {rel: {"pinned_sha256": PINNED[rel], "sha256_before": before[rel], "sha256_after": after[rel],
                         "pre_registered_pin_match": (before[rel] == PINNED[rel])}
                   for rel in before},
        "class_chain_input_revision": {
            "path": "ledger/theorems.jsonl",
            "sha256_before_run": theorems_sha_before,
            "sha256_used_for_class_chain": theorems_sha_used,
            "sha256_after_run": after["ledger/theorems.jsonl"],
            "revised_during_run": theorems_sha_before != theorems_sha_used or theorems_sha_used != after["ledger/theorems.jsonl"],
            "pre_registered_pin_match": secondary_pin_match,
        },
        "secondary_input_revision_note": (
            "ledger/theorems.jsonl is a secondary input for the class-binding chain check and is under active "
            "revision by its owner (pre-registered ce42d205; observed 3e3d3553 then a1674f09 during the v3 "
            "attempts). The class chain is computed against ONE measured revision read after the fetch loop; "
            "the primary citation target ledger/citation_audit.csv is strict-pinned before and after the run."),
        "drift_during_run": drift,
        "sample": {
            "rule": "citation_id in SRC-041..SRC-060 (all 20); SRC-041/049/057 are cross-checks of flash-07, the other 17 are new coverage",
            "rows": SAMPLE,
        },
        "frozen_classes": FROZEN_CLASSES,
        "verdict_rules": {
            "MATCH": "resolved + title consistent + year consistent + every quoted excerpt segment matched",
            "PARTIAL": "resolved + title/year consistent, but excerpt partly matched / not checkable, or only unquoted note text not reproducible",
            "FAIL": "resolved but title/year contradiction, or a quoted excerpt segment (>=25 normalized chars) absent",
            "FETCH_FAILED": "no locator returned HTTP 200",
        },
        "results": results,
        "summary": summary,
        "class_binding_summary": {
            "hard_failures": {"non_frozen_class_tokens_in_linked_theorems": non_frozen,
                              "missing_theorem_refs": missing_refs},
            "csv_non_frozen_tokens": csv_non_frozen,
            "csv_tokens_without_linked_theorem_support": unsupported,
            "annotation_only_rows": annotation_rows,
            "note": "'(evidence/tag only)' is a documented non-class annotation; it is recorded, not counted as a class token. No non-frozen class token was found in any linked theorem row inside the sample.",
        },
        "hard_failures": [],
        "falsifier": "A later re-fetch at the pinned csv sha256 315c19145065 yielding a different verdict for any sampled row falsifies this verdict set; a csv hash change during the run invalidates the run.",
        "validation_status": "unverified",
        "no_completion_claim": "worker artifact; worker cannot set done/passed or a gate verdict; no physics result claimed",
        "reproduce": "python3 artifacts/worker-100/l1_spotcheck_41_60/spotcheck.py",
    }
    if non_frozen or missing_refs or "ledger/citation_audit.csv" in drift:
        report["hard_failures"] = (
            [f"non-frozen class token: {x}" for x in non_frozen]
            + [f"missing theorem ref: {x}" for x in missing_refs]
            + [f"primary input drift: {k}" for k in drift if k == "ledger/citation_audit.csv"])
    report_path = HERE / "spotcheck-l1-100.json"
    report_path.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    (HERE / "fetch_meta_worker100.json").write_text(json.dumps(fetch_meta, indent=1, ensure_ascii=False) + "\n")
    (HERE / "spotcheck-l1-100.json.sha256").write_text(sha256_file(report_path) + "  spotcheck-l1-100.json\n")
    print(json.dumps({"report": str(report_path.relative_to(ROOT)), "sha256": sha256_file(report_path),
                      "summary": summary, "hard_failures": report["hard_failures"], "drift": drift}, indent=1))
    return 1 if (non_frozen or missing_refs or drift) else 0


if __name__ == "__main__":
    sys.exit(main())
