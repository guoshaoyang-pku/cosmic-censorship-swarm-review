#!/usr/bin/env python3
"""Independent L1 re-fetch spot check #4 (worker-086), gate G-LIT.

Pre-registered frame and sampling rule are declared in the emitted report and
frozen here before any network fetch.  Fail-closed: if ledger/citation_audit.csv
does not hash to the pinned frozen sha256 the script exits 2 without fetching.

Method per row: re-fetch the primary source from the DOI (Crossref REST API) or
the arXiv id (arXiv abstract page), never from ledger text.  Compare fetched
title / first author / year / venue / abstract against the ledger row and its
`evidence_excerpt` verbatim.  Stdlib only.
"""
import csv
import difflib
import hashlib
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

REPO = "/data3/guoshaoyang/workdir/ai4math-swarm"
CSV_REL = "ledger/citation_audit.csv"
CSV_SHA_PIN = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
OUT = REPO + "/artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json"

# --- pre-registered selection (declared before any fetch) -------------------
# Frame: data rows 1-40 were last spot-checked at earlier csv hashes
# (flash-10 rows 1-20 @ old sha, flash-11 rows 21-40 @ fe4b48bb) so they are not
# binding at the frozen sha; rows 96-97 have never been checked at any sha.
# Worker-07 owns rows 41-95 at the frozen sha and is not duplicated here.
# S1 stride: every 8th row of 1-40 starting at 1 -> 1, 9, 17, 25, 33.
# S2 terminal: rows 96, 97.
# S3 targeted augmentation declared pre-fetch: row 4 (SRC-004, load-bearing for
# both SCC classes and the subject of the disputed L0 conditional binding) and
# row 16 (SRC-016, the only AF-WCC-SCALAR-SPH row inside 1-40).
TARGETS = [1, 4, 9, 16, 17, 25, 33, 96, 97]
SAMPLING_RULE = {
    "frozen_before_fetch": True,
    "S1_stride": "every 8th data row of frame 1-40 starting at 1 -> rows 1,9,17,25,33",
    "S2_terminal": "rows 96,97 (never checked at any csv sha)",
    "S3_targeted_augmentation": (
        "row 4 (SRC-004: load-bearing C0+C2 source whose L0 binding is contested) "
        "and row 16 (SRC-016: only AF-WCC-SCALAR-SPH row in 1-40), declared before any fetch"
    ),
    "excluded": "rows 41-95 (worker-07 spot check #3 at this sha)",
    "sampled_rows": TARGETS,
}
UA = "ai4math-swarm-worker-086/1.0 (spot-check; contact: local swarm)"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
            return {"ok": True, "http_status": r.status, "url": r.geturl(),
                    "bytes": len(body), "seconds": round(time.time() - t0, 2), "body": body}
    except urllib.error.HTTPError as e:
        return {"ok": False, "http_status": e.code, "url": url,
                "seconds": round(time.time() - t0, 2), "error": "HTTPError: %s" % e}
    except Exception as e:  # noqa: BLE001 - network failure must be recorded, not raised
        return {"ok": False, "http_status": None, "url": url,
                "seconds": round(time.time() - t0, 2), "error": "%s: %s" % (type(e).__name__, e)}


TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def strip_tags(s):
    return WS_RE.sub(" ", html.unescape(TAG_RE.sub(" ", s))).strip()


def norm(s):
    return WS_RE.sub(" ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())).strip()


def parse_arxiv(body):
    out = {}
    m = re.search(r'<h1 class="title mathjax">(.*?)</h1>', body, re.S)
    if m:
        out["title"] = re.sub(r"^Title:\s*", "", strip_tags(m.group(1)))
    m = re.search(r'<blockquote class="abstract mathjax">(.*?)</blockquote>', body, re.S)
    if m:
        out["abstract"] = re.sub(r"^Abstract:\s*", "", strip_tags(m.group(1)))
    m = re.search(r'<div class="authors">(.*?)</div>', body, re.S)
    if m:
        out["authors"] = [a.strip() for a in re.split(r",|;| and ", strip_tags(m.group(1))) if a.strip()]
    m = re.search(r"\[Submitted on ([^\]<]+)", strip_tags(body))
    if m:
        out["submitted"] = m.group(1).strip()
    m = re.search(r'<td class="tablecell subjects">(.*?)</td>', body, re.S)
    if m:
        out["subjects"] = strip_tags(m.group(1))
    m = re.search(r'<span class="primary-subject">(.*?)</span>', body, re.S)
    if m:
        out["primary_subject"] = strip_tags(m.group(1))
    return out


def parse_crossref(body):
    d = json.loads(body)["message"]
    out = {
        "title": (d.get("title") or [""])[0],
        "authors": [a.get("family") or a.get("name", "") for a in d.get("author", [])],
        "container_title": (d.get("container-title") or [""])[0],
        "type": d.get("type"),
        "DOI": d.get("DOI"),
        "abstract": strip_tags(d.get("abstract", "")) if d.get("abstract") else "",
    }
    for key in ("issued", "published-print", "published-online", "published"):
        dp = (d.get(key) or {}).get("date-parts") or [[None]]
        if dp and dp[0] and dp[0][0]:
            out[key] = dp[0]
    return out


def compare(row, fetched, kind):
    """Return (verdict, comparison dict). MISMATCH beats PARTIAL beats MATCH."""
    comp = {}
    lt, ft = norm(row["title"]), norm(fetched.get("title", ""))
    if not ft:
        comp["title"] = "fetched_title_absent"
        title_ok = False
    elif lt == ft:
        comp["title"] = "exact"
        title_ok = True
    elif lt[:45] and (lt[:45] in ft or ft[:45] in lt):
        comp["title"] = "prefix-45"
        title_ok = True
    else:
        ratio = difflib.SequenceMatcher(None, lt, ft).ratio()
        comp["title"] = "similarity=%.2f" % ratio
        title_ok = ratio > 0.85
    la = [norm(x) for x in row["authors"].split(";") if x.strip()]
    fa = [norm(x) for x in fetched.get("authors", [])]
    first_ledger = la[0].split()[-1] if la else ""
    comp["first_author_ledger"] = first_ledger
    comp["fetched_authors"] = fetched.get("authors", [])
    author_ok = bool(first_ledger) and any(first_ledger in a or a in first_ledger for a in fa)
    comp["first_author_match"] = author_ok

    years = set()
    for key in ("issued", "published-print", "published-online", "published"):
        if fetched.get(key):
            years.add(fetched[key][0])
    if fetched.get("submitted"):
        m = re.search(r"(\d{4})", fetched["submitted"])
        if m:
            years.add(int(m.group(1)))
    ledger_year = int(row["year"])
    comp["ledger_year"] = ledger_year
    comp["fetched_years"] = sorted(years)
    if not years:
        comp["year"] = "no_fetched_year"
        year_state = "partial"
    elif ledger_year in years:
        comp["year"] = "exact"
        year_state = "match"
    elif any(abs(ledger_year - y) == 1 for y in years):
        comp["year"] = "off-by-one (issue vs online-first convention)"
        year_state = "partial"
    else:
        comp["year"] = "no_year_within_1"
        year_state = "mismatch"

    venue = norm(fetched.get("container_title", ""))
    ledger_venue = norm(row["venue"])
    if venue and venue.split()[0] in ledger_venue:
        comp["venue"] = "container-title token present"
        venue_state = "match"
    elif kind == "arxiv" and "arxiv" in ledger_venue:
        comp["venue"] = "arXiv locator present in ledger venue"
        venue_state = "match"
    else:
        comp["venue"] = "container-title=%r not a token of ledger venue" % fetched.get("container_title", "")
        venue_state = "partial"

    excerpt = row["evidence_excerpt"] or ""
    excerpt = re.sub(r'^Abstract:\s*', "", excerpt).strip().strip('"').strip()
    abst = fetched.get("abstract", "") or ""
    if not excerpt:
        comp["excerpt"] = "no ledger excerpt"
        exc_state = "partial"
    elif not abst:
        comp["excerpt"] = "no fetched abstract (metadata-only fetch)"
        exc_state = "partial"
    else:
        ratio = difflib.SequenceMatcher(None, norm(excerpt)[:400], norm(abst)[:400]).ratio()
        comp["excerpt_similarity_first400"] = round(ratio, 3)
        if ratio > 0.55:
            exc_state = "match"
        elif ratio > 0.30:
            exc_state = "partial"
        else:
            exc_state = "mismatch"

    states = {"match": 0, "partial": 1, "mismatch": 2}
    if not title_ok or not author_ok:
        verdict = "MISMATCH"
    elif "mismatch" in (year_state, exc_state):
        verdict = "MISMATCH"
    elif "partial" in (year_state, venue_state, exc_state):
        verdict = "PARTIAL"
    else:
        verdict = "MATCH"
    comp["states"] = {"title": title_ok, "author": author_ok, "year": year_state,
                      "venue": venue_state, "excerpt": exc_state}
    return verdict, comp


def main():
    csv_path = REPO + "/" + CSV_REL
    pre_sha = sha256_file(csv_path)
    if pre_sha != CSV_SHA_PIN:
        print("FAIL-CLOSED: %s sha256=%s != pinned %s" % (CSV_REL, pre_sha, CSV_SHA_PIN), file=sys.stderr)
        return 2
    with open(csv_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) != 97:
        print("FAIL-CLOSED: expected 97 data rows, found %d" % len(rows), file=sys.stderr)
        return 2

    results = []
    for n in TARGETS:
        row = rows[n - 1]
        arxiv_id, doi = row["arxiv_id"].strip(), row["doi"].strip()
        if arxiv_id:
            kind, fetch_url = "arxiv", "https://arxiv.org/abs/" + arxiv_id
        else:
            kind, fetch_url = "crossref", "https://api.crossref.org/works/" + urllib.parse.quote(doi)
        fetched_raw = get(fetch_url)
        rec = {
            "row": n,
            "citation_id": row["citation_id"],
            "class_mapping": row["class_mapping"],
            "used_by_theorems": row["used_by_theorems"],
            "ledger": {
                "title": row["title"], "authors": row["authors"], "year": row["year"],
                "venue": row["venue"], "doi": doi, "arxiv_id": arxiv_id,
                "exact_locator": row["exact_locator"], "evidence_url": row["evidence_url"],
                "evidence_excerpt": row["evidence_excerpt"],
                "ledger_locator_kind": ("search_query" if "api/query" in row["exact_locator"]
                                        or "api/literature?q=" in row["exact_locator"] else "direct"),
            },
            "locator_kind": kind,
            "locator_used": fetch_url,
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            "fetch": fetched_raw,
        }
        body = fetched_raw.get("body")
        del rec["fetch"]["body"]
        if not fetched_raw["ok"]:
            rec["fetched"] = None
            rec["comparison"] = {"error": fetched_raw.get("error"), "http_status": fetched_raw.get("http_status")}
            rec["verdict"] = "FETCH_FAILED"
        else:
            fetched = parse_arxiv(body) if kind == "arxiv" else parse_crossref(body)
            if kind == "arxiv" and not fetched.get("title"):
                rec["fetched"] = fetched
                rec["comparison"] = {"error": "arXiv page has no title element (likely withdrawn/absent); " + fetch_url}
                rec["verdict"] = "MISMATCH"
            else:
                verdict, comp = compare(row, fetched, kind)
                rec["fetched"] = {
                    "title": fetched.get("title", ""),
                    "authors": fetched.get("authors", []),
                    "container_title": fetched.get("container_title", ""),
                    "years": {k: v for k, v in fetched.items() if isinstance(v, list) and k != "authors"},
                    "submitted": fetched.get("submitted"),
                    "abstract_head": (fetched.get("abstract", "") or "")[:600],
                }
                rec["comparison"] = comp
                rec["verdict"] = verdict
        results.append(rec)

    post_sha = sha256_file(csv_path)
    counts = {v: sum(1 for r in results if r["verdict"] == v)
              for v in ("MATCH", "PARTIAL", "MISMATCH", "FETCH_FAILED")}
    hard = [{"citation_id": r["citation_id"], "row": r["row"], "verdict": r["verdict"],
             "detail": r["comparison"]} for r in results if r["verdict"] in ("MISMATCH", "FETCH_FAILED")]
    locator_notes = [{"citation_id": r["citation_id"], "exact_locator_kind": r["ledger"]["ledger_locator_kind"]}
                     for r in results if r["ledger"]["ledger_locator_kind"] != "direct"]
    report = {
        "schema_version": "1.0",
        "artifact_type": "l1_refetch_spotcheck",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "actor": "worker-086",
        "reviewer": "worker-086",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "check_number": 4,
        "independent_of": ["reviews/L1-spotcheck-10.json", "reviews/L1-spotcheck-11.json",
                           "artifacts/worker-07/l1_spotcheck/spotcheck-l1-07.json"],
        "independence_note": ("fresh sample, disjoint from rows 41-95 owned by spot check #3; "
                              "rows 1-40 were last checked at earlier csv hashes and are not binding at the frozen sha"),
        "inputs": {CSV_REL: {"sha256": pre_sha, "data_rows": len(rows),
                             "frame": "data rows 1-40 at frozen sha + terminal rows 96-97",
                             "sha256_after_fetches": post_sha,
                             "stable_during_run": pre_sha == post_sha}},
        "sampling_rule": SAMPLING_RULE,
        "method": {
            "network": "live re-fetch, worker-086, stdlib urllib; ledger text never used as evidence",
            "arxiv_rows": "https://arxiv.org/abs/<id> (title/authors/abstract/submitted parsed from the page)",
            "doi_rows": "https://api.crossref.org/works/<doi> (registry metadata, not the ledger)",
            "verdicts": "MATCH | PARTIAL (convention/locator-quality only) | MISMATCH (work or claim differs) | FETCH_FAILED",
            "class_mapping_check": "abstract read for topical consistency only; not a scope verdict",
        },
        "results": results,
        "summary": {"checked": len(results), **counts,
                    "locator_quality_notes": locator_notes},
        "hard_failures": hard,
        "findings": [
            "SRC-009 locator is an arXiv API search query, not a citable exact locator",
            "SRC-016/SRC-017/SRC-033 exact_locator entries are INSPIRE search queries, not exact locators",
        ] if locator_notes else [],
        "non_claims": ["spot check on 9 of 97 rows; not a ledger-wide verdict",
                       "no gate or node status is set by this worker",
                       "class_mapping topical consistency is not a class-binding verdict"],
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(json.dumps({"out": OUT, "summary": report["summary"], "hard_failures": [h["citation_id"] for h in hard]},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
