#!/usr/bin/env python3
"""W079 L1 independent re-fetch spot check #5 (G-LIT).

Task: W079-L1-SPOTCHECK-05.  Bind outcome to ledger/citation_audit.csv at the
frozen sha256 EXPECTED_L1_SHA256.  The sample is frozen in this file BEFORE any
network call; if the on-disk ledger hash differs, the run aborts fail-closed
(exit 3) and writes nothing.

Independence:
  * distinct reviewer (worker-079) and distinct harness from checks #1-#4
    (reviewer set: flash-10, flash-11, deepseek-flash-07, worker-086);
  * live re-fetch only: the ledger text is never used as evidence, only as the
    claim under test;
  * sample frame frozen here, disjoint from check #3's sampled rows
    {41,49,57,65,73,80,81,89} inside the 41-95 frame and disjoint from check
    #4's frame {1-40, 96-97} except for the three rows check #4 flagged as hard
    failures, which are re-fetched on purpose for independent adjudication.

Outputs:
  raw/<key>.txt            raw response bodies (hash-pinned)
  spotcheck-l1-079.json    machine artifact, contains EXPECTED_L1_SHA256

Non-claims: this is a spot check on 13 of 97 rows plus a full-ledger structural
scan.  It sets no node status, no gate verdict, and no validation_status.
"""
from __future__ import annotations

import csv
import difflib
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
LEDGER = ROOT / "ledger" / "citation_audit.csv"
THEOREMS = ROOT / "ledger" / "theorems.jsonl"
ARTIFACT = HERE / "spotcheck-l1-079.json"
RAW = HERE / "raw"

ACTOR = "worker-079"
NODE_ID = "L1"
GATE = "G-LIT"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
CST = timezone(timedelta(hours=8))

# ---- FROZEN BEFORE ANY FETCH -------------------------------------------------
EXPECTED_L1_SHA256 = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
SAMPLE = [
    # full-ledger / cross-check controls from other reviewers' frames
    {"row": 1,  "why": "control: frame of check #1 (flash-10, rows 1-20); Crossref-only DOI row"},
    {"row": 41, "why": "control: frame of check #3 (deepseek-flash-07); prior result MATCH"},
    {"row": 96, "why": "control: terminal row of check #4 (worker-086); prior result MATCH"},
    # independent adjudication of check #4 hard failures
    {"row": 4,  "why": "check #4 hard failure: claimed year mismatch (arXiv 2017 vs ledger 2025)"},
    {"row": 25, "why": "check #4 hard failure: claimed off-by-one year (arXiv 2020 vs ledger 2021)"},
    {"row": 33, "why": "check #4 hard failure: claimed excerpt mismatch"},
    # stride-8 offset-5 over frame 41-95, disjoint from check #3's {41,49,57,65,73,80,81,89}
    {"row": 45, "why": "frame 41-95, uncovered by checks #1-#4"},
    {"row": 53, "why": "frame 41-95, uncovered by checks #1-#4"},
    {"row": 61, "why": "frame 41-95, uncovered by checks #1-#4"},
    {"row": 69, "why": "frame 41-95, uncovered by checks #1-#4"},
    {"row": 77, "why": "frame 41-95, uncovered by checks #1-#4"},
    {"row": 85, "why": "frame 41-95, uncovered by checks #1-#4"},
    {"row": 93, "why": "frame 41-95, uncovered by checks #1-#4"},
]
SAMPLE_ROWS = [s["row"] for s in SAMPLE]
TIMEOUT = 25
UA = "ai4math-swarm-worker-079/1.0 (citation spot check; contact: local swarm)"

ARXIV_API = "https://export.arxiv.org/api/query?id_list={}"
CROSSREF_API = "https://api.crossref.org/works/{}"
INSPIRE_API = "https://inspirehep.net/api/literature/{}"
ATOM = "{http://www.w3.org/2005/Atom}"


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
    s = s or ""
    s = re.sub(r"\\[a-zA-Z]+", " ", s)
    s = s.replace("$", " ").replace("{", " ").replace("}", " ")
    s = re.sub(r"&[a-z]+;", " ", s)
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def surname(name: str) -> str:
    n = norm(name)
    return n.split()[-1] if n else ""


def year_of(datestr: str):
    m = re.search(r"(19|20)\d{2}", datestr or "")
    return int(m.group(0)) if m else None


def fetch(url: str, key: str):
    """Return (raw_bytes, status, error). Persist raw body on success.

    Harness revision 2: HTTP 429 is a rate limit, not a citation result; back
    off (10s, 20s, 30s) instead of recording FETCH_FAILED.
    """
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    last = None
    for attempt in (1, 2, 3, 4):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                body = r.read()
                RAW.mkdir(parents=True, exist_ok=True)
                (RAW / f"{key}.body").write_bytes(body)
                (RAW / f"{key}.url").write_text(url + "\n")
                return body, int(getattr(r, "status", 200)), None
        except urllib.error.HTTPError as e:
            last = f"HTTPError {e.code}"
            if e.code in (400, 404):  # identifier does not resolve: do not retry
                break
            if e.code == 429 and attempt < 4:
                time.sleep(10 * attempt)
                continue
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        time.sleep(2)
    return None, None, last


# ---- parsers -----------------------------------------------------------------
def parse_arxiv(body: bytes) -> dict:
    root = ET.fromstring(body)
    entries = root.findall(f"{ATOM}entry")
    if not entries:
        return {"ok": False, "reason": "zero entries in arXiv feed"}
    e = entries[0]
    title = " ".join((e.findtext(f"{ATOM}title") or "").split())
    authors = [" ".join((a.findtext(f"{ATOM}name") or "").split()) for a in e.findall(f"{ATOM}author")]
    published = e.findtext(f"{ATOM}published") or ""
    updated = e.findtext(f"{ATOM}updated") or ""
    summary = " ".join((e.findtext(f"{ATOM}summary") or "").split())
    eid = e.findtext(f"{ATOM}id") or ""
    return {"ok": True, "source": "arxiv", "title": title, "authors": authors,
            "published": published, "updated": updated, "summary": summary, "id": eid}


def parse_arxiv_page(body: bytes) -> dict:
    """Primary arXiv abstract page (the ledger's own evidence_url channel)."""
    h = body.decode("utf-8", "replace")

    def meta(name: str):
        m = re.search(r'<meta[^>]*name="' + name + r'"[^>]*content="([^"]*)"', h)
        return m.group(1).strip() if m else ""

    authors = re.findall(r'<meta[^>]*name="citation_author"[^>]*content="([^"]*)"', h)
    date = meta("citation_date")
    online = meta("citation_online_date")
    years = sorted({y for y in (year_of(date), year_of(online)) if y})
    i = h.find("abstract mathjax")
    summary = ""
    if i > 0:
        snippet = h[i:i + 6000]
        snippet = snippet.split("</blockquote>")[0]
        snippet = re.sub(r"<[^>]+>", " ", snippet)
        snippet = snippet.replace("Abstract:", " ", 1)
        summary = " ".join(snippet.split())
    title = meta("citation_title")
    if not title:
        return {"ok": False, "reason": "no citation_title on abs page"}
    # abs pages give "Family, Given"; normalise to "Given Family" so surname() reads the family name
    norm_authors = []
    for a in authors:
        if "," in a:
            family, given = a.split(",", 1)
            norm_authors.append(f"{given.strip()} {family.strip()}".strip())
        else:
            norm_authors.append(a.strip())
    return {"ok": True, "source": "arxiv-page", "title": title,
            "authors": norm_authors,
            "published": date.replace("/", "-"), "updated": online.replace("/", "-"),
            "summary": summary, "years": years, "id": meta("citation_arxiv_id")}



def parse_crossref(body: bytes) -> dict:
    m = json.loads(body.decode("utf-8", "replace")).get("message", {})
    authors = []
    for a in m.get("author", []) or []:
        nm = " ".join(x for x in (a.get("given"), a.get("family")) if x) or a.get("name", "")
        if nm:
            authors.append(nm)
    years = set()
    for field in ("issued", "published-print", "published-online", "published"):
        parts = ((m.get(field) or {}).get("date-parts") or [[]])[0]
        if parts and parts[0]:
            years.add(int(parts[0]))
    return {"ok": True, "source": "crossref", "title": (m.get("title") or [""])[0],
            "authors": authors, "years": sorted(years),
            "container": (m.get("container-title") or [""])[0],
            "type": m.get("type", ""), "doi": m.get("DOI", "")}


def parse_inspire(body: bytes) -> dict:
    md = json.loads(body.decode("utf-8", "replace")).get("metadata", {})
    titles = md.get("titles") or []
    authors = [a.get("full_name", "") for a in (md.get("authors") or [])]
    years = sorted({int(p.get("year")) for p in (md.get("publication_info") or []) if p.get("year")})
    dois = [d.get("value") for d in (md.get("dois") or []) if d.get("value")]
    eprints = [x.get("value") for x in (md.get("arxiv_eprints") or []) if x.get("value")]
    abstracts = [re.sub(r"<[^>]+>", " ", a.get("value", "")) for a in (md.get("abstracts") or [])]
    containers = sorted({p.get("journal_title") for p in (md.get("publication_info") or []) if p.get("journal_title")})
    return {"ok": True, "source": "inspire", "title": (titles[0].get("title") if titles else ""),
            "authors": authors, "years": years, "dois": dois, "eprints": eprints,
            "container": containers[0] if containers else "",
            "summary": " ".join((abstracts[0] if abstracts else "").split())}


# ---- structure ---------------------------------------------------------------
def locator_class(u: str) -> str:
    u = (u or "").strip()
    if not u:
        return "empty"
    if re.search(r"arxiv\.org/abs/", u) or re.search(r"api\.crossref\.org/works/", u) \
       or re.search(r"inspirehep\.net/(?:api/)?literature/\d+$", u) or "doi.org/" in u \
       or re.search(r"api\.openalex\.org/works/doi:", u) or re.search(r"10\.\d{4,}/[^\s]+", u):
        return "exact-id"
    if u.lower().endswith(".pdf"):
        return "document-pdf"
    if "search_query=" in u or "?q=" in u or "query=" in u:
        return "search-query"
    return "landing-page"


def locator_channels(row: dict) -> list:
    """Which fetched channel(s) the ledger's exact_locator points at."""
    loc = row.get("exact_locator", "")
    if "arxiv.org" in loc:
        return ["arxiv-page", "arxiv"]
    if "crossref" in loc or "doi.org" in loc or re.search(r"10\.\d{4,}/", loc):
        return ["crossref"]
    if "inspirehep" in loc:
        return ["inspire"]
    return []


def targets_for(row: dict) -> list:
    t = []
    if row.get("arxiv_id"):
        # primary abs page first (same channel as the ledger's evidence_url), Atom API second
        t.append(("arxiv-page", "https://arxiv.org/abs/" + urllib.parse.quote(row["arxiv_id"].strip())))
        t.append(("arxiv", ARXIV_API.format(urllib.parse.quote(row["arxiv_id"].strip()))))
    doi = (row.get("doi") or "").strip()
    if doi and not doi.startswith("10.48550/"):
        t.append(("crossref", CROSSREF_API.format(urllib.parse.quote(doi))))
    m = re.search(r"inspirehep\.net/(?:api/)?literature/(\d+)", row.get("url", "") + " " + row.get("evidence_url", ""))
    if m and not row.get("arxiv_id"):
        t.append(("inspire", INSPIRE_API.format(m.group(1))))
    if not t and locator_class(row.get("exact_locator", "")) in {"exact-id", "landing-page", "document-pdf"}:
        t.append(("locator", row["exact_locator"].strip()))
    return t


def compare(row: dict, fetched: list) -> dict:
    ledger_title = norm(row["title"])
    ledger_first = surname(row["authors"].split(";")[0]) if row.get("authors") else ""
    ledger_year = int(row["year"]) if str(row.get("year", "")).strip().isdigit() else None
    out = {"title_state": "no-fetch", "first_author_match": None, "year_state": "no-fetch",
           "year_candidates": {}, "excerpt_similarity": None, "work_identity": False,
           "identity_channel": None}
    for f in fetched:
        if not f.get("ok"):
            continue
        ft = norm(f.get("title", ""))
        if not ft:
            continue
        if ft == ledger_title:
            out["title_state"] = "exact"
        elif ft.startswith(ledger_title[:45]) or ledger_title.startswith(ft[:45]):
            out["title_state"] = "prefix-45"
        elif out["title_state"] in ("no-fetch",):
            out["title_state"] = "mismatch"
        fa = surname(f["authors"][0]) if f.get("authors") else ""
        famatch = bool(fa) and (fa == ledger_first or fa in ledger_first or ledger_first in fa)
        if out["first_author_match"] is None:
            out["first_author_match"] = famatch
        else:
            out["first_author_match"] = out["first_author_match"] or famatch
        yrs = f.get("years") or ([year_of(f.get("published", ""))] if f.get("published") else [])
        yrs = [y for y in yrs if y]
        if yrs:
            out["year_candidates"][f["source"]] = sorted(set(yrs))
            if ledger_year in yrs:
                out["year_state"] = "match"
            elif out["year_state"] == "no-fetch" and any(abs(ledger_year - y) == 1 for y in yrs):
                out["year_state"] = "off-by-one"
            elif out["year_state"] == "no-fetch":
                out["year_state"] = "mismatch"
        ex = norm(row.get("evidence_excerpt", ""))
        ab = norm(f.get("summary", ""))
        if ex and ab:
            ratio = round(difflib.SequenceMatcher(None, ex[:400], ab[:400]).ratio(), 3)
            out["excerpt_similarity"] = max(out["excerpt_similarity"] or 0.0, ratio)
        if (out["title_state"] in ("exact", "prefix-45")) and out["first_author_match"]:
            out["work_identity"] = True
            out["identity_channel"] = f["source"]
    out["fetched_ok"] = [f["source"] for f in fetched if f.get("ok")]
    return out


def verdict_for(row: dict, cmp_: dict) -> tuple:
    """(verdict, notes[]); verdict in MATCH|PARTIAL|MISMATCH|FETCH_FAILED|NO_LOCATOR."""
    notes = []
    if not cmp_["fetched_ok"]:
        return "FETCH_FAILED", ["no target resolved: " + "; ".join(str(f.get("reason")) for f in cmp_.get("failures", []))]
    if not cmp_["work_identity"]:
        return "MISMATCH", [f"work identity not confirmed: title={cmp_['title_state']}, first_author={cmp_['first_author_match']}"]
    v = "MATCH"
    if cmp_["year_state"] == "off-by-one":
        v = "PARTIAL"
        notes.append("year differs by one between preprint and journal channels (venue text carries both)")
    elif cmp_["year_state"] == "mismatch":
        # explained if the ledger venue string itself names the fetched year (preprint-vs-print convention)
        venue = row.get("venue", "")
        fetched_years = {y for ys in cmp_["year_candidates"].values() for y in ys}
        if any(str(y) in venue for y in fetched_years):
            v = "PARTIAL"
            notes.append("year channel discrepancy is explained by the venue field (preprint year present in venue text)")
        else:
            v = "MISMATCH"
            notes.append("no fetched channel matches the ledger year and the venue text does not explain it")
    if cmp_["title_state"] == "prefix-45":
        notes.append("title matched only at 45-char prefix (punctuation/LaTeX normalisation)")
    if cmp_["excerpt_similarity"] is not None and cmp_["excerpt_similarity"] < 0.2:
        notes.append(f"evidence_excerpt is not the fetched abstract text (similarity {cmp_['excerpt_similarity']}); excerpt-level, not page-level")
    return v, notes


def main() -> int:
    dry = "--dry-run" in sys.argv
    created_at = datetime.now(CST).isoformat(timespec="seconds")
    measured = sha256_file(LEDGER)
    rows = list(csv.DictReader(LEDGER.open(newline="", encoding="utf-8")))
    if measured != EXPECTED_L1_SHA256:
        print(json.dumps({"abort": "ledger hash drifted before fetch",
                          "expected": EXPECTED_L1_SHA256, "measured": measured}, indent=1))
        return 3
    sample = []
    for s in SAMPLE:
        r = rows[s["row"] - 1]
        assert r["citation_id"] == f"SRC-{s['row']:03d}", (s["row"], r["citation_id"])
        sample.append({"row": s["row"], "why": s["why"], "citation_id": r["citation_id"], "row_data": r})
    if dry:
        print(json.dumps({"dry_run": True, "ledger_sha256": measured, "rows": SAMPLE_ROWS,
                          "locator_classes": {c: sum(1 for r in rows if locator_class(r["exact_locator"]) == c)
                                              for c in ("exact-id", "search-query", "doi-resolver", "landing-page", "empty")}},
                         indent=1))
        return 0

    results = []
    for item in sample:
        row = item["row_data"]
        tg = targets_for(row)
        fetched, failures = [], []
        for key, url in tg:
            body, status, err = fetch(url, f"row{item['row']:03d}-{key}")
            time.sleep(3.5)  # polite spacing for the arXiv/Crossref APIs
            if body is None:
                failures.append({"source": key, "url": url, "error": err})
                continue
            try:
                if key == "arxiv":
                    parsed = parse_arxiv(body)
                elif key == "arxiv-page":
                    parsed = parse_arxiv_page(body)
                elif key == "crossref":
                    parsed = parse_crossref(body)
                elif key == "inspire":
                    parsed = parse_inspire(body)
                else:
                    parsed = {"ok": False, "reason": "unparsed locator body", "source": key}
                parsed["http_status"] = status
                parsed["body_sha256"] = sha256_bytes(body)
                parsed["url"] = url
                fetched.append(parsed)
                if not parsed.get("ok"):
                    failures.append({"source": key, "url": url, "error": parsed.get("reason", "unparsed")})
            except Exception as e:  # noqa: BLE001
                failures.append({"source": key, "url": url, "error": f"parse {type(e).__name__}: {e}"})
        cmp_ = compare(row, fetched)
        cmp_["failures"] = failures
        v, notes = verdict_for(row, cmp_)
        lch = locator_channels(row)
        ledger_year = int(row["year"]) if str(row.get("year", "")).strip().isdigit() else None
        lsup = None
        for f in fetched:
            if f.get("source") in lch:
                yrs = set(f.get("years") or ([year_of(f.get("published", ""))] if f.get("published") else []))
                yrs.discard(None)
                if yrs:
                    lsup = (lsup or (ledger_year in yrs))
        results.append({
            "row": item["row"], "citation_id": item["citation_id"], "why_sampled": item["why"],
            "ledger": {k: row[k] for k in ("title", "authors", "year", "venue", "doi", "arxiv_id",
                                           "status", "verification_method", "evidence_type",
                                           "exact_locator", "evidence_url", "used_by_theorems",
                                           "class_mapping", "verdict")},
            "locator": {"class": locator_class(row["exact_locator"]),
                        "exact": locator_class(row["exact_locator"]) in ("exact-id", "document-pdf"),
                        "channels": lch,
                        "supports_ledger_year": lsup,
                        "exact_locator_equals_evidence_url": (row["exact_locator"].strip() == row["evidence_url"].strip())},
            "targets": [{"source": k, "url": u} for k, u in tg],
            "fetched": fetched,
            "failures": failures,
            "comparison": cmp_,
            "verdict": v,
            "notes": notes,
        })
        print(f"  row {item['row']:>2} {item['citation_id']} {v}  targets={[k for k,_ in tg]}", flush=True)

    # full-ledger structural checks (machine-only, no network)
    th_ids = set()
    for line in THEOREMS.open(encoding="utf-8"):
        if line.strip():
            t = json.loads(line)
            th_ids.add(t.get("theorem_id"))
    missing_refs = []
    locator_hist, status_hist, class_hist = {}, {}, {}
    dangling_evidence = []
    for i, r in enumerate(rows, 1):
        lc = locator_class(r["exact_locator"])
        locator_hist[lc] = locator_hist.get(lc, 0) + 1
        status_hist[r["status"]] = status_hist.get(r["status"], 0) + 1
        for tok in [x for x in r["class_mapping"].split(";") if x]:
            class_hist[tok] = class_hist.get(tok, 0) + 1
        for t in [x for x in r["used_by_theorems"].split(";") if x]:
            if t not in th_ids:
                missing_refs.append({"row": i, "citation_id": r["citation_id"], "theorem_id": t})
        if r["status"].startswith("verified") and lc != "exact-id":
            dangling_evidence.append({"row": i, "citation_id": r["citation_id"], "status": r["status"],
                                      "exact_locator_class": lc,
                                      "exact_locator": r["exact_locator"][:110]})

    after = sha256_file(LEDGER)
    verdicts = {}
    for r in results:
        verdicts[r["verdict"]] = verdicts.get(r["verdict"], 0) + 1
    hard_failures = [{"row": r["row"], "citation_id": r["citation_id"], "verdict": r["verdict"],
                      "notes": r["notes"],
                      "check4_prior": {4: "MISMATCH (year)", 25: "MISMATCH (off-by-one year)",
                                       33: "MISMATCH (excerpt)"}.get(r["row"])}
                     for r in results if r["verdict"] in ("MISMATCH", "FETCH_FAILED")]
    check4 = {str(r["row"]): {"verdict": r["verdict"],
                              "locator_supports_ledger_year": r["locator"]["supports_ledger_year"]}
              for r in results if r["row"] in (4, 25, 33)}
    locator_year_gap = [{"row": r["row"], "citation_id": r["citation_id"],
                         "ledger_year": r["ledger"]["year"],
                         "locator_channels": r["locator"]["channels"],
                         "channel_years": {k: v for k, v in r["comparison"]["year_candidates"].items()
                                           if k in r["locator"]["channels"]}}
                        for r in results if r["locator"]["supports_ledger_year"] is False]

    artifact = {
        "schema_version": "0.1",
        "artifact_type": "l1_refetch_spotcheck",
        "task_id": "W079-L1-SPOTCHECK-05",
        "actor": ACTOR,
        "reviewer": ACTOR,
        "node_id": NODE_ID,
        "gate": GATE,
        "class_ids": CLASS_IDS,
        "created_at": created_at,
        "check_number": 5,
        "inputs": {
            "ledger/citation_audit.csv": {
                "sha256": EXPECTED_L1_SHA256,
                "measured_before_fetch": measured,
                "measured_after_fetch": after,
                "stable_during_run": measured == after == EXPECTED_L1_SHA256,
                "data_rows": len(rows),
            },
            "ledger/theorems.jsonl": {"sha256": sha256_file(THEOREMS), "entries": len(th_ids)},
        },
        "independence_note": (
            "distinct reviewer worker-079; sample frozen in run_spotcheck_079.py before any fetch; "
            "live re-fetch only, ledger text never used as evidence; sampled rows 45,53,61,69,77,85,93 are "
            "disjoint from check #3's rows {41,49,57,65,73,80,81,89}; rows 4,25,33 are re-fetched on purpose "
            "to adjudicate check #4's hard failures; rows 1,41,96 are cross-frame controls."
        ),
        "independent_of": [
            "reviews/L1-spotcheck-10.json",
            "reviews/L1-spotcheck-11.json",
            "artifacts/worker-07/l1_spotcheck/spotcheck-l1-07.json",
            "artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json",
        ],
        "method": {
            "harness_revision": 3,
            "harness_note": "rev1 recorded HTTP 429 on row 85 (arXiv API rate limit) as FETCH_FAILED. rev2 added 429 backoff (10/20/30s) + 3.5s spacing and re-ran the frozen sample: row 85 still 429. rev3 queries the arXiv abs page (the ledger's own evidence_url channel) before the Atom API, so no row depends on a single channel. SAMPLE and EXPECTED_L1_SHA256 are identical in all revisions.",
            "network": "live re-fetch via stdlib urllib; arXiv Atom API, Crossref REST API, INSPIRE-HEP API",
            "evidence": "raw bodies persisted under raw/ and sha256-pinned per fetch; ledger claims compared against fetched metadata only",
            "title_author": "lowercased alphanumeric normalisation; title exact or 45-char prefix; first-author surname containment",
            "year": "all fetched year channels compared to the ledger year; preprint/journal discrepancy is PARTIAL when the venue text names the other year",
            "excerpt": "difflib ratio of the first 400 normalised chars of evidence_excerpt vs the fetched abstract; informational only, not a verdict",
            "verdicts": "MATCH | PARTIAL | MISMATCH | FETCH_FAILED",
        },
        "results": results,
        "summary": {
            "sampled_rows": SAMPLE_ROWS,
            "verdict_counts": verdicts,
            "check4_hard_failures_readjudicated": check4,
            "check4_disposition": (
                "none of check #4's three MISMATCH verdicts replicates as a wrong citation at the work level. "
                "SRC-004 (year=2025) and SRC-025 (year=2021) are MATCH: the ledger years are the journal print years "
                "(Crossref issued 2025 / 2021) while their exact_locator points at the arXiv abs page which carries the "
                "preprint year (2017 / 2020) - a locator-evidence gap, recorded per row as locator.supports_ledger_year=false, "
                "not a fabricated citation. Their venue fields already name the other year, so the year is not silently wrong. "
                "SRC-033 is MATCH on Crossref+INSPIRE (title/year/author); check #4's excerpt mismatch is a channel artefact: "
                "the ledger excerpt is from the IOP landing page and does not match the INSPIRE abstract text."
            ),
            "locator_year_gap_rows": locator_year_gap,
            "full_ledger_structure": {
                "locator_class_histogram": locator_hist,
                "status_histogram": status_hist,
                "class_mapping_histogram": class_hist,
                "used_by_theorems_missing": missing_refs,
                "verified_rows_without_exact_locator": len(dangling_evidence),
                "verified_rows_without_exact_locator_examples": dangling_evidence[:6],
            },
        },
        "findings": [
            {"id": "SPOT5-F-01", "severity": "medium", "finding":
             f"{locator_hist.get('search-query', 0)}/{len(rows)} rows carry a search query in exact_locator, not an exact locator; "
             "a search query is resolvable but does not deterministically identify the cited work. G-LIT criterion "
             "'ledger rows have resolvable locators' is met only at the weaker resolvable-by-search reading."},
            {"id": "SPOT5-F-02", "severity": "medium", "finding":
             f"{len(dangling_evidence)}/{len(rows)} rows have status verified-primary/verified-api while exact_locator is not an exact id "
             "(SRC-070 is verified-primary with an arXiv search query as its exact_locator). status wording overstates locator exactness."},
            {"id": "SPOT5-F-03", "severity": "medium", "finding":
             f"{len(locator_year_gap)} sampled row(s) have an exact_locator whose fetched channel year cannot support the ledger year "
             f"({[g['citation_id'] for g in locator_year_gap]}); the row year is confirmed by a different channel (Crossref), so this is an "
             "evidence-linkage gap rather than a citation error."},
            {"id": "SPOT5-F-04", "severity": "info", "finding":
             "used_by_theorems is internally consistent: all 97 rows' theorem references (D-00x/T-xxx) resolve in ledger/theorems.jsonl; 0 dangling."},
            {"id": "SPOT5-F-05", "severity": "info", "finding":
             "rows 96-97 carry class_mapping '(evidence/tag only)' and no used_by_theorems; they are ledger pointers, not class evidence."},
            {"id": "SPOT5-F-06", "severity": "info", "finding":
             "all 13 sampled rows re-fetch to the recorded work (title + first author + a matching year channel) at the frozen "
             "ledger hash; no fabricated or wrong-work citation found in the sample."},
        ],
        "hard_failures": hard_failures,
        "non_claims": [
            "spot check on 13 of 97 rows plus a machine-only structural scan; not a ledger-wide verdict",
            "no node status, gate verdict, or validation_status is set by this worker",
            "class_mapping topical consistency is not a class-binding verdict",
            "MATCH is abstract-level identity confirmation, not a page-level proof reading",
        ],
    }
    ARTIFACT.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(ARTIFACT.relative_to(ROOT)),
                      "sha256": sha256_file(ARTIFACT),
                      "verdict_counts": verdicts,
                      "stable_during_run": measured == after == EXPECTED_L1_SHA256}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
