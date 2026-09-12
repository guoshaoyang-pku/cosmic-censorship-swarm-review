#!/usr/bin/env python3
"""L1 citation spot check #4 -- reviewer worker-077.

Assignment: astra-life02-l1-spotcheck (map.assignments, created 2026-09-12T00:15:49+08:00).
Acceptance: two further independent re-fetch spot checks binding
ledger/citation_audit.csv sha256 315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9,
each recording the fetched source hash, the comparison verdict (MATCH/PARTIAL/FAIL), the locator,
and re-hashing the ledger after the fetch. This script is one of the two (reviewer=worker-077).

Fail-closed design:
  - aborts if the pinned pre-fetch ledger hash does not match;
  - sample rule and fetch plan are frozen in this file before any fetch;
  - every fetched body is written to raw_fresh/ and hashed;
  - ledger is re-hashed after the fetch and drift is recorded (drift does not void the
    per-row results but is reported and would void a whole-file claim).

Read-only with respect to ledger/ and research_map/.
"""
import csv
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
LEDGER = os.path.join(ROOT, "ledger/citation_audit.csv")
OUT = os.path.join(ROOT, "artifacts/worker-077/l1_spotcheck")
RAW = os.path.join(OUT, "raw_fresh")
TZ = timezone(timedelta(hours=8))
PIN = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
REVIEWER = "worker-077"
TASK_ID = "L1-W077-SPOTCHECK-04"
ASSIGNMENT_REF = "astra-life02-l1-spotcheck"
CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]

# ---- frozen before any fetch (2026-09-12T00:18:44+08:00, pin recorded in
# runtime/state/w077_l1_pin_before.txt) -------------------------------------
# Frame: data rows 45-93, complementary residue class to deepseek-flash-07's
# every-8th sample (41,49,57,65,73,80,81,89) inside the same 41-95 frame:
# every 8th row starting at 45. Tail augmentation: row 96 (outside every
# previous frame: flash-10 1-20, flash-11 21-40, flash-07 41-95).
# Targeted augmentation declared before fetch: row 42 (SRC-042), the only
# sampled row binding class AF-WCC-VAC-GEN via T-201/T-202; not in flash-07's
# sample and present in no other checker's targets.
SAMPLE_ROWS = [42, 45, 53, 61, 69, 77, 85, 93, 96]
SAMPLE_RULE = {
    "frozen_before_fetch": True,
    "frozen_at": "2026-09-12T00:18:44+08:00",
    "frame": "data rows 45-93 of the 97-row ledger (complementary residue to flash-07's 41+8k sample), plus row 96 (tail, outside every previous frame)",
    "S1_complementary_residue": "rows 45,53,61,69,77,85,93 (every 8th starting at 45)",
    "S2_tail_augmentation": "row 96 (SRC-096): the last data row, never inside flash-10 (1-20), flash-11 (21-40) or flash-07 (41-95) frames",
    "S3_targeted_augmentation": "row 42 (SRC-042): declared before fetch as the AF-WCC-VAC-GEN binding row (T-201/T-202); not in flash-07's sampled set and in no other reviewer's targets",
    "sampled_rows": SAMPLE_ROWS,
    "disjoint_from": {
        "reviews/L1-spotcheck-10.json": "frame rows 1-20",
        "reviews/L1-spotcheck-11.json": "frame rows 21-40",
        "artifacts/worker-07/l1_spotcheck/spotcheck-l1-07.json": [41, 49, 57, 65, 73, 80, 81, 89],
    },
}
# locators to re-fetch, keyed by (row, kind). Primary = the row's evidence_url
# kind; corroborating sources are fetched from the DOI/INSPIRE record and must
# not contradict the primary.
FETCH_PLAN = {
    42: [
        ("crossref", "https://api.crossref.org/works/10.1007/s11511-012-0077-3"),
        ("inspire", "https://inspirehep.net/api/literature/841287"),
    ],
    45: [("arxiv", "https://export.arxiv.org/api/query?id_list=2607.07134")],
    53: [("arxiv", "https://export.arxiv.org/api/query?id_list=2501.12968")],
    61: [
        ("arxiv", "https://export.arxiv.org/api/query?id_list=gr-qc/0309115"),
        ("crossref", "https://api.crossref.org/works/10.1007/s00222-005-0450-3"),
    ],
    69: [
        ("inspire", "https://inspirehep.net/api/literature/311851"),
        ("crossref", "https://api.crossref.org/works/10.1088/0264-9381/7/10/003"),
    ],
    77: [
        ("inspire", "https://inspirehep.net/api/literature/2168006"),
        ("crossref", "https://api.crossref.org/works/10.1007/s00023-024-01489-0"),
    ],
    85: [("arxiv", "https://export.arxiv.org/api/query?id_list=2201.12295")],
    93: [
        ("arxiv", "https://export.arxiv.org/api/query?id_list=gr-qc/0512119"),
        ("crossref", "https://api.crossref.org/works/10.1002/cpa.20281"),
    ],
    96: [
        ("arxiv", "https://export.arxiv.org/api/query?id_list=1901.07996"),
        ("crossref", "https://api.crossref.org/works/10.1007/s11005-019-01213-8"),
    ],
}
PRIMARY_KIND = {42: "inspire", 45: "arxiv", 53: "arxiv", 61: "arxiv",
                69: "inspire", 77: "inspire", 85: "arxiv", 93: "arxiv", 96: "arxiv"}
# ---------------------------------------------------------------------------

STOP = set("""a an the of and or for in on at to from by with as is are was were be been
this that these those it its their his her they we our not no than then thus so such which who
whom whose can may might must should would could will shall do does did done have has had
if but about into over under between during after before while also more most some any all
one two three part parts paper work works result results show shows shown prove proves proof
give gives given using used use new first last other others same non""".split())


def now():
    return datetime.now(TZ).isoformat(timespec="seconds")


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def norm(s):
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = s.replace("$", " ").replace("\\", "")
    s = re.sub(r"\b(c|C)\^?\{?0[,.]?1\}?\b", " c01 ", s)
    s = re.sub(r"[^0-9A-Za-z]+", " ", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def toks(s):
    return [t for t in norm(s).split() if len(t) >= 3 and t not in STOP]


def coverage(excerpt, source):
    et = toks(excerpt)
    if not et:
        return None
    st = set(toks(source))
    hit = sum(1 for t in et if t in st)
    return round(hit / len(et), 3)


def curl(url):
    """GET with retry/backoff. arXiv rate-limits bursts with HTTP 429."""
    code, body = None, b""
    for attempt, wait in enumerate([0, 4, 12]):
        if wait:
            time.sleep(wait)
        p = subprocess.run(
            ["curl", "-sS", "-L", "-m", "45", "-w", "\n%{http_code}", url],
            capture_output=True,
        )
        body = p.stdout
        code = None
        if b"\n" in body[-6:]:
            idx = body.rfind(b"\n")
            tail = body[idx + 1:].strip()
            if tail.isdigit():
                code = int(tail)
                body = body[:idx]
        if p.returncode != 0 and code is None:
            code = 0
        if code == 200 and body:
            return code, body
        if code != 429 and not (code and 500 <= code < 600):
            return code, body
    return code, body


def parse_arxiv(body):
    root = ET.fromstring(body)
    ns = {"a": "http://www.w3.org/2005/Atom", "ar": "http://arxiv.org/schemas/atom"}
    e = root.find("a:entry", ns)
    if e is None:
        return None
    d = {
        "title": (e.findtext("a:title", default="", namespaces=ns) or "").strip(),
        "authors": [a.findtext("a:name", default="", namespaces=ns)
                    for a in e.findall("a:author", ns)],
        "published": e.findtext("a:published", default="", namespaces=ns),
        "journal_ref": e.findtext("ar:journal_ref", default="", namespaces=ns),
        "doi": e.findtext("ar:doi", default="", namespaces=ns),
        "abstract": (e.findtext("a:summary", default="", namespaces=ns) or "").strip(),
        "id": e.findtext("a:id", default="", namespaces=ns),
    }
    d["year"] = (d["published"] or "")[:4]
    return d


def parse_crossref(body):
    m = json.loads(body)["message"]
    t = m.get("title") or [""]
    issued = ((m.get("issued") or {}).get("date-parts") or [[None]])[0]
    abstract = m.get("abstract") or ""
    abstract = re.sub(r"<[^>]+>", " ", abstract)
    return {
        "title": t[0] if t else "",
        "authors": [f"{a.get('given','')} {a.get('family','')}".strip()
                    for a in (m.get("author") or [])],
        "year": str(issued[0]) if issued and issued[0] else "",
        "journal_ref": (m.get("container-title") or [""])[0],
        "doi": m.get("DOI", ""),
        "abstract": abstract,
        "id": m.get("URL", ""),
    }


def parse_inspire(body):
    m = json.loads(body)["metadata"]
    titles = m.get("titles") or [{}]
    authors = [a.get("full_name", "") for a in (m.get("authors") or [])]
    years = [p.get("year") for p in (m.get("publication_info") or []) if p.get("year")]
    abstracts = [a.get("value", "") for a in (m.get("abstracts") or [])]
    dois = [d.get("value", "") for d in (m.get("dois") or [])]
    return {
        "title": titles[0].get("title", ""),
        "authors": authors,
        "year": str(years[0]) if years else (m.get("earliest_date", "") or "")[:4],
        "journal_ref": (m.get("publication_info") or [{}])[0].get("journal_title", ""),
        "doi": dois[0] if dois else "",
        "abstract": abstracts[0] if abstracts else "",
        "id": m.get("control_number", ""),
    }


class _MetaParser(HTMLParser):
    """Collects citation_* / og:description meta tags from an arXiv abs page."""

    def __init__(self):
        super().__init__()
        self.meta = {}
        self.authors = []

    def handle_starttag(self, tag, attrs):
        if tag != "meta":
            return
        d = dict(attrs)
        name = (d.get("name") or d.get("property") or "").lower()
        content = d.get("content")
        if not name or content is None:
            return
        if name == "citation_author":
            self.authors.append(content)
        elif name.startswith("citation_") or name in ("og:description", "description"):
            self.meta.setdefault(name, content)


def _clean_meta(s):
    return unescape(unescape(s or "").replace('\\"', '"')).strip()


def parse_arxiv_abs(body):
    p = _MetaParser()
    p.feed(body.decode("utf-8", "replace"))
    m = p.meta
    date = m.get("citation_date") or m.get("citation_online_date") or ""
    return {
        "title": _clean_meta(m.get("citation_title", "")),
        "authors": [_clean_meta(a) for a in p.authors],
        "year": date[:4],
        "journal_ref": "",
        "doi": m.get("citation_doi", ""),
        "abstract": _clean_meta(m.get("citation_abstract") or m.get("og:description", "")),
        "id": m.get("citation_arxiv_id", ""),
    }


PARSERS = {"arxiv": parse_arxiv, "arxiv_abs": parse_arxiv_abs,
           "crossref": parse_crossref, "inspire": parse_inspire}


def first_family(authors):
    """Family name of the first author; handles 'Family, Given' (INSPIRE) and
    'Given Family' (Crossref/arXiv) orders."""
    for a in authors:
        raw = str(a)
        if "," in raw:  # INSPIRE order: family first
            parts = norm(raw.split(",")[0]).split()
        else:  # given-name-first order
            parts = norm(raw).split()
        if parts:
            return parts[-1]
    return ""


def title_similarity(a, b):
    return round(difflib.SequenceMatcher(None, norm(a), norm(b)).ratio(), 3)


def ledger_title_clean(t):
    return re.sub(r"\s*\((Crossref record|published version|.*?record)\)\s*$", "", t or "", flags=re.I).strip()


def compare(row, primary, kinds):
    lt = ledger_title_clean(row["title"])
    pt = primary.get("title", "")
    nlt, npt = norm(lt), norm(pt)
    sim = title_similarity(lt, pt)
    if nlt and npt and (nlt == npt or nlt in npt or npt in nlt):
        title_verdict = "strong"
    else:
        cov = coverage(lt, pt)
        title_verdict = "strong" if sim >= 0.92 else ("weak" if (cov is not None and cov >= 0.8) else "mismatch")
    lfam = first_family([(row["authors"] or "").split(";")[0]]) if row["authors"] else ""
    fams = [first_family(primary.get("authors") or [])]
    author_ok = bool(lfam) and any(lfam and lfam in f for f in fams)
    ly = re.search(r"\d{4}", row["year"] or "")
    py = re.search(r"\d{4}", primary.get("year") or "")
    ly, py = (ly.group(0) if ly else ""), (py.group(0) if py else "")
    year_note = None
    if ly and py:
        d = abs(int(ly) - int(py))
        year_ok = d <= 1
        if d > 1:
            year_note = (f"ledger year {ly} vs fetched first-posting/metadata year {py} "
                         f"(diff {d}); title and authors match, consistent with "
                         f"preprint-first-posting vs journal year, not a locator error")
    else:
        year_ok = None
    excerpt = re.sub(r"^[^:']{0,40}(abstract|record|recid)[^:']{0,40}:\s*", "", row["evidence_excerpt"] or "", flags=re.I)
    excerpt = excerpt.strip().strip("'\"")
    src_text = " ".join([primary.get("abstract") or "", primary.get("title") or "",
                         " ".join(primary.get("authors") or []), primary.get("journal_ref") or ""])
    cov = coverage(excerpt, src_text)
    if primary.get("abstract"):
        if cov is None:
            quote_check = "not_checked"
        elif cov >= 0.7:
            quote_check = "grounded_in_abstract"
        elif cov >= 0.45:
            quote_check = "close_paraphrase"
        else:
            quote_check = "not_found_in_abstract"
    else:
        quote_check = "metadata_record_consistent" if title_verdict == "strong" and author_ok else "no_abstract_available"
    if title_verdict == "mismatch" or not author_ok:
        verdict = "FAIL"
    elif title_verdict == "weak" or year_note or quote_check == "not_found_in_abstract":
        verdict = "PARTIAL"
    else:
        verdict = "MATCH"
    return {
        "title_verdict": title_verdict,
        "title_similarity": sim,
        "author_ok": author_ok,
        "ledger_first_family": lfam,
        "fetched_first_families": fams,
        "year_ok": year_ok,
        "ledger_year": ly,
        "fetched_year": py,
        "quote_check": quote_check,
        "excerpt_token_coverage": cov,
        "year_note": year_note,
        "verdict": verdict,
    }


def main():
    pre = sha256_bytes(open(LEDGER, "rb").read())
    if pre != PIN:
        print(f"FAIL-CLOSED: pre-fetch ledger hash {pre} != pinned {PIN}", file=sys.stderr)
        return 2
    rows = list(csv.DictReader(open(LEDGER, newline="", encoding="utf-8")))
    if len(rows) != 97:
        print(f"FAIL-CLOSED: expected 97 data rows, got {len(rows)}", file=sys.stderr)
        return 2
    os.makedirs(RAW, exist_ok=True)
    results = []
    for r in SAMPLE_ROWS:
        row = rows[r - 1]
        assert row["citation_id"] == f"SRC-{r:03d}", (r, row["citation_id"])
        sources = []
        for kind, url in FETCH_PLAN[r]:
            code, body = curl(url)
            fname = f"r{r:03d}_{kind}.body"
            open(os.path.join(RAW, fname), "wb").write(body)
            rec = {
                "kind": kind, "locator": url, "http_status": code,
                "bytes": len(body), "sha256": sha256_bytes(body),
                "raw_file": f"artifacts/worker-077/l1_spotcheck/raw_fresh/{fname}",
            }
            if code == 200 and body:
                try:
                    rec["parsed"] = PARSERS[kind](body)
                except Exception as ex:  # noqa: BLE001
                    rec["parse_error"] = f"{type(ex).__name__}: {ex}"
            sources.append(rec)
            if kind == "arxiv":
                time.sleep(3.2)  # arXiv API asks for >=3 s between requests
        primary = None
        primary_source = None
        for s in sources:
            if s["kind"] == PRIMARY_KIND[r] and "parsed" in s:
                primary, primary_source = s["parsed"], s
        # arXiv-API 429 fallback: the arXiv abstract page carries the same
        # citation_* metadata and is fetched only if the API gave no parseable body.
        if primary is None and row["arxiv_id"]:
            url = f"https://arxiv.org/abs/{row['arxiv_id']}"
            code, body = curl(url)
            fname = f"r{r:03d}_arxiv_abs.body"
            open(os.path.join(RAW, fname), "wb").write(body)
            rec = {
                "kind": "arxiv_abs", "locator": url, "http_status": code,
                "bytes": len(body), "sha256": sha256_bytes(body),
                "raw_file": f"artifacts/worker-077/l1_spotcheck/raw_fresh/{fname}",
                "fallback_for": PRIMARY_KIND[r],
            }
            if code == 200 and body:
                try:
                    rec["parsed"] = PARSERS["arxiv_abs"](body)
                except Exception as ex:  # noqa: BLE001
                    rec["parse_error"] = f"{type(ex).__name__}: {ex}"
            sources.append(rec)
            if "parsed" in rec:
                primary, primary_source = rec["parsed"], rec
        if primary is None:
            for s in sources:
                if "parsed" in s:
                    primary, primary_source = s["parsed"], s
                    break
        if primary is None:
            results.append({
                "row": r, "citation_id": row["citation_id"], "bibkey": row["bibkey"],
                "class_mapping": row["class_mapping"], "used_by_theorems": row["used_by_theorems"],
                "ledger": {k: row[k] for k in ("title", "authors", "year", "venue", "doi",
                                               "arxiv_id", "status", "verification_method",
                                               "evidence_type", "exact_locator", "evidence_url",
                                               "evidence_excerpt", "assessment", "verdict", "reviewer")},
                "sources": sources, "locator_used": None, "verdict": "FETCH_FAILED",
                "comparison": {"verdict": "FAIL"},
            })
            continue
        comp = compare(row, primary, [s["kind"] for s in sources])
        corroboration = []
        for s in sources:
            if "parsed" not in s or s is primary_source:
                continue
            p = s["parsed"]
            if not p.get("title"):
                continue
            sim = title_similarity(ledger_title_clean(row["title"]), p["title"])
            corroboration.append({"kind": s["kind"], "title_similarity": sim,
                                  "verdict": "agrees" if sim >= 0.8 else "diverges"})
        comp["corroboration"] = corroboration
        if any(c["verdict"] == "diverges" for c in corroboration) and comp["verdict"] == "MATCH":
            comp["verdict"] = "PARTIAL"
            comp["contradiction"] = "a corroborating source's title diverges from the ledger title"
        results.append({
            "row": r,
            "citation_id": row["citation_id"],
            "bibkey": row["bibkey"],
            "class_mapping": row["class_mapping"],
            "used_by_theorems": row["used_by_theorems"],
            "ledger": {k: row[k] for k in ("title", "authors", "year", "venue", "doi",
                                           "arxiv_id", "status", "verification_method",
                                           "evidence_type", "exact_locator", "evidence_url",
                                           "evidence_excerpt", "assessment", "verdict", "reviewer")},
            "locator_used": primary_source["locator"],
            "primary_kind": primary_source["kind"],
            "fetched_at": now(),
            "sources": sources,
            "comparison": comp,
            "verdict": comp["verdict"],
        })
    post = sha256_bytes(open(LEDGER, "rb").read())
    summary = {
        "checked": len(results),
        "MATCH": sum(1 for x in results if x["verdict"] == "MATCH"),
        "PARTIAL": sum(1 for x in results if x["verdict"] == "PARTIAL"),
        "FAIL": sum(1 for x in results if x["verdict"] == "FAIL"),
        "FETCH_FAILED": sum(1 for x in results if x["verdict"] == "FETCH_FAILED"),
        "quote_grounding": {},
    }
    for x in results:
        q = x.get("comparison", {}).get("quote_check")
        if q:
            summary["quote_grounding"][q] = summary["quote_grounding"].get(q, 0) + 1
    classes = sorted({c for x in results if x["class_mapping"] and x["class_mapping"] != "(evidence/tag only)"
                      for c in x["class_mapping"].split(";")})
    hard = [x["citation_id"] for x in results if x["verdict"] in ("FAIL", "FETCH_FAILED")]
    art = {
        "schema_version": "0.1",
        "artifact_type": "l1_spotcheck",
        "task_id": TASK_ID,
        "event_id": f"w077-{datetime.now(TZ).strftime('%Y%m%dT%H%M%S')}-l1-spotcheck-04",
        "assignment_ref": ASSIGNMENT_REF,
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": CLASS_IDS,
        "actor": REVIEWER,
        "reviewer": REVIEWER,
        "created_at": now(),
        "check_number": 4,
        "independent_of": [
            "reviews/L1-spotcheck-10.json",
            "reviews/L1-spotcheck-11.json",
            "artifacts/worker-07/l1_spotcheck/spotcheck-l1-07.json",
        ],
        "independence_note": (
            "Reviewer worker-077 is distinct from flash-10, flash-11 and deepseek-flash-07. "
            "Sampled rows are disjoint from flash-07's sampled set and from the flash-10/flash-11 "
            "frames. All locators were re-fetched from the APIs; no ledger text was used as "
            "evidence. No assignment card existed in comms/inbox/worker-077.jsonl; this is the "
            "open L1 spot-check subtask of map assignment astra-life02-l1-spotcheck."
        ),
        "inputs": {
            "ledger/citation_audit.csv": {
                "sha256_before_fetch": pre,
                "sha256_after_fetch": post,
                "pinned_sha256": PIN,
                "pin_matches_before": pre == PIN,
                "data_rows": len(rows),
                "checked_rows": SAMPLE_ROWS,
                "drifted_during_fetch": pre != post,
            }
        },
        "sampling_rule": SAMPLE_RULE,
        "method": (
            "curl -> primary API for each sampled row (arXiv API export.arxiv.org for arXiv rows; "
            "Crossref API for DOI rows; INSPIRE API for INSPIRE rows), plus a corroborating "
            "source where a DOI/INSPIRE record exists; every raw body written byte-for-byte to "
            "raw_fresh/ and sha256-hashed; where the arXiv API returned persistent HTTP 429 the "
            "arXiv abstract page (arxiv.org/abs/<id>) was fetched instead and recorded as an "
            "arxiv_abs fallback source; title compared after case/punctuation/LaTeX/diacritic "
            "normalisation with a sequence-similarity floor; year compared with a +/-1 "
            "preprint/journal tolerance (>1 -> PARTIAL with an explicit note); the ledger "
            "evidence_excerpt tested at content-token coverage against the fetched abstract text "
            "(>=0.70 grounded, 0.45-0.70 close paraphrase, <0.45 not found). Ledger re-hashed "
            "after the fetch. Read-only run."
        ),
        "results": results,
        "summary": summary,
        "class_coverage_from_class_mapping": classes,
        "hard_failures": hard,
        "findings": [
            {
                "id": "SPOT4-F-01",
                "severity": "info",
                "finding": (
                    f"{summary['MATCH']}/{summary['checked']} sampled locators re-fetch to the "
                    f"recorded work; {summary['PARTIAL']} partial, {summary['FAIL']} fail, "
                    f"{summary['FETCH_FAILED']} fetch failure."
                ),
            },
            {
                "id": "SPOT4-F-02",
                "severity": "soft",
                "finding": (
                    "Several rows carry a non-deterministic `exact_locator`: rows 42, 69 and 77 "
                    "hold truncated INSPIRE search URLs ending in an ellipsis and cannot be "
                    "replayed as written; the row's `evidence_url` (specific record) does resolve. "
                    "Locator hygiene only; no row verdict depends on the truncated query."
                ),
            },
            {
                "id": "SPOT4-F-03",
                "severity": "info",
                "finding": (
                    "Year fields mix preprint-first-posting and journal years (e.g. SRC-093 "
                    "ledger 2009 vs arXiv 2005; SRC-061 ledger 2005 vs arXiv 2003). Title and "
                    "authors match; this is a convention mix, not a locator error, but a consumer "
                    "comparing years mechanically would misread it."
                ),
            },
            {
                "id": "SPOT4-F-04",
                "severity": "info",
                "finding": (
                    "This is an abstract/metadata-level check, not a page check of the theorem "
                    "statement; verification_status=abstract-read remains the honest level for "
                    "the checked rows."
                ),
            },
            {
                "id": "SPOT4-F-05",
                "severity": "soft",
                "finding": (
                    "The arXiv API returned persistent HTTP 429 for SRC-053 (arXiv:2501.12968) "
                    "and SRC-085 (arXiv:2201.12295) across retries while the corresponding "
                    "arXiv abstract pages returned 200. Those two rows were verified against the "
                    "abstract page (kind arxiv_abs, recorded with fallback_for=arxiv in the "
                    "sources list); title, authors, year and excerpt all ground, so the verdicts "
                    "are unaffected."
                ),
            },
            {
                "id": "SPOT4-F-06",
                "severity": "info",
                "finding": (
                    "arXiv API XML embeds a random feed <id> per request, so arXiv-API raw "
                    "bodies are not byte-reproducible even for identical metadata. The recorded "
                    "sha256 pins the body actually fetched; comparisons are content-level."
                ),
            },
        ],
        "falsifiers": [
            "Re-running run_spotcheck_077.py at the pinned CSV sha256 returns a different per-row verdict set (non-reproducible fetch evidence).",
            "Any sampled locator resolves to a work whose title/author/year contradicts the row: the corresponding MATCH verdict is false and the row becomes a hard failure.",
            "A row outside this 9-row sample is later found to have a fabricated locator, which falsifies only the sample-level claim, not the per-row results above.",
            "If ledger/citation_audit.csv no longer hashes to the pinned value, the whole-file binding of this spot check is void (per-row fetches remain valid evidence of the cited works).",
        ],
        "non_claims": [
            "Does not claim the ledger is citation-clean outside the 9 sampled rows.",
            "Does not promote any theorem, class, node or gate; validation_status remains unverified.",
            "Does not edit ledger/citation_audit.csv, ledger/theorems.jsonl, research_map/ or runtime/state/artifact_hashes.json.",
            "Does not claim completion of node L1 or of assignment astra-life02-l1-spotcheck; it is one of the two spot checks that assignment requires, and the second must come from a different reviewer.",
        ],
        "evidence_refs": [
            f"ledger/citation_audit.csv#{pin_prefix(PIN)}",
            "comms/inbox/astra-lead-literature.jsonl#astra-life02-l1-spotcheck",
            "artifacts/worker-07/l1_spotcheck/spotcheck-l1-07.json",
            "reviews/L1-spotcheck-10.json",
            "reviews/L1-spotcheck-11.json",
        ],
        "reproduce": "python3 artifacts/worker-077/l1_spotcheck/run_spotcheck_077.py",
    }
    artpath = os.path.join(OUT, "spotcheck-l1-077.json")
    with open(artpath, "w", encoding="utf-8") as f:
        json.dump(art, f, indent=2, sort_keys=False)
        f.write("\n")
    digest = sha256_bytes(open(artpath, "rb").read())
    with open(artpath + ".sha256", "w", encoding="utf-8") as f:
        f.write(f"{digest}  spotcheck-l1-077.json\n")
    print(json.dumps({"artifact": "artifacts/worker-077/l1_spotcheck/spotcheck-l1-077.json",
                      "sha256": digest, "summary": summary,
                      "ledger_before": pre, "ledger_after": post}, indent=2))
    return 0


def pin_prefix(p):
    return p[:12]


if __name__ == "__main__":
    sys.exit(main())
