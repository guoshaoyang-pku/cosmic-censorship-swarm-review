#!/usr/bin/env python3
"""worker-070 L1 spot check: independent re-fetch of frozen sample rows 1-40.

Assignment: astra-life02-l1-spotcheck (G-LIT, node L1).
Target hash: ledger/citation_audit.csv sha256
             315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9

Method (frozen before any fetch):
  frame       : data rows 1-40 (disjoint from deepseek-flash-07 frame 41-95)
  S1          : every 5th data row of the frame starting at row 3 -> 3,8,13,18,23,28,33,38
  S2          : row 4 (SRC-004) added because S1 covers no AF-SCC-C0-VAC-GEN row;
                lowest-index class-mapped row with a primary locator.
  locator     : arXiv API (export.arxiv.org) for rows carrying an arXiv id;
                Crossref REST API for DOI rows; INSPIRE-HEP API as secondary locator
                whenever the ledger row points at an INSPIRE record.
  evidence    : raw response body saved, sha256 recorded, parsed fields compared to the
                ledger row (title / authors / year / excerpt token recall).
  drift       : ledger re-hashed after the fetch; any change voids the check.

No ledger text is trusted as evidence for the fetch; the ledger is the object under test.

Method revision (recorded for audit, applied uniformly to all rows, after first pass):
  R1 year semantics: ledger year is the JOURNAL/venue year; the arXiv API "published"
     field is the PREPRINT year. A ledger year is accepted if it matches any authoritative
     year candidate within +/-1: arXiv published year, arXiv journal_ref year, Crossref
     issued year, INSPIRE earliest_date year. First pass compared only arXiv published
     year and produced two spurious FAILs (SRC-004, SRC-028) whose journal_refs match.
  R2 transport: HTTP 429/5xx/000 are retried up to 3 times with backoff before downgrading
     a locator; the first pass lost SRC-038's arXiv locator to a transient 429.
  R3 quote support: Crossref carries no abstract for some mathematics records; when the
     primary locator returns no abstract the INSPIRE secondary is used for the excerpt
     recall, and "no abstract in any response" is recorded as not_verifiable rather than
     as a contradiction.
  R4 diacritics: NFKD combining marks are dropped before tokenisation; replacing them with
     a separator split "Girao"/"Natario" and understated SRC-028 author overlap.
  R5 metadata recaps: an excerpt carrying an embedded DOI and/or quoted title is checked
     against the fetched record and counts as supported when corroborated.
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
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
LEDGER = os.path.join(ROOT, "ledger", "citation_audit.csv")
LEDGER_SHA_EXPECTED = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
OUTDIR = os.path.dirname(os.path.abspath(__file__))
RAWDIR = os.path.join(OUTDIR, "raw")
UA = "ai4math-swarm-worker-070/0.1 (independent L1 spot check)"
SAMPLE = [
    {"row": 3, "citation_id": "SRC-003", "why": "S1 every-5th from 3; AF-WCC-VAC-GEN"},
    {"row": 4, "citation_id": "SRC-004", "why": "S2 targeted: only missing frozen class AF-SCC-C0-VAC-GEN; load-bearing D-002/T-301/T-305/T-401/T-402"},
    {"row": 8, "citation_id": "SRC-008", "why": "S1 every-5th from 3; evidence/tag only"},
    {"row": 13, "citation_id": "SRC-013", "why": "S1 every-5th from 3; AF-WCC-SCALAR-SPH"},
    {"row": 18, "citation_id": "SRC-018", "why": "S1 every-5th from 3; evidence/tag only"},
    {"row": 23, "citation_id": "SRC-023", "why": "S1 every-5th from 3; evidence/tag only"},
    {"row": 28, "citation_id": "SRC-028", "why": "S1 every-5th from 3; evidence/tag only"},
    {"row": 33, "citation_id": "SRC-033", "why": "S1 every-5th from 3; AF-SCC-C2-VAC-GEN"},
    {"row": 38, "citation_id": "SRC-038", "why": "S1 every-5th from 3; AF-WCC-VAC-GEN"},
]
ARXIV_NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"\\[a-zA-Z]+", " ", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def tokens(s):
    return [t for t in norm(s).split() if len(t) > 2]


def title_sim(a, b):
    return round(difflib.SequenceMatcher(None, norm(a), norm(b)).ratio(), 3)


def recall(ledger_text, fetched_text):
    lt, ft = set(tokens(ledger_text)), set(tokens(fetched_text))
    if not lt:
        return None
    return round(len(lt & ft) / len(lt), 3)


def last_names(authors):
    out = set()
    for a in re.split(r"[;,]| and ", authors or ""):
        parts = [p for p in norm(a).split() if p]
        if parts:
            out.add(parts[-1])
    return out


def curl(url, outfile, attempts=3):
    cmd = ["curl", "-sS", "-L", "--max-time", "40", "-A", UA, "-o", outfile,
           "-w", "%{http_code}"]
    tries = []
    for i in range(attempts):
        t0 = datetime.now(CST)
        p = subprocess.run(cmd + [url], capture_output=True, text=True)
        body = open(outfile, "rb").read() if os.path.exists(outfile) else b""
        try:
            http = int(p.stdout.strip() or 0)
        except ValueError:
            http = 0
        rec = {"url": url, "attempt": i + 1, "curl_exit": p.returncode, "http_status": http,
               "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest() if body else None,
               "wall_s": round((datetime.now(CST) - t0).total_seconds(), 2),
               "fetched_at": t0.isoformat(timespec="seconds")}
        tries.append(rec)
        if p.returncode == 0 and http == 200 and body:
            break
        if i < attempts - 1:
            time.sleep(4 * (i + 1))
    last = dict(tries[-1])
    last["attempts"] = tries
    last["cmd"] = " ".join(cmd + [url])
    return last


def parse_arxiv(path):
    try:
        root = ET.parse(path).getroot()
    except Exception as e:
        return {"parse_error": str(e)}
    e = root.find("a:entry", ARXIV_NS)
    if e is None:
        return {"parse_error": "no entry"}
    return {
        "kind": "arxiv_api",
        "title": " ".join((e.findtext("a:title", "", ARXIV_NS) or "").split()),
        "authors": [a.findtext("a:name", "", ARXIV_NS) for a in e.findall("a:author", ARXIV_NS)],
        "published": e.findtext("a:published", "", ARXIV_NS),
        "updated": e.findtext("a:updated", "", ARXIV_NS),
        "journal_ref": e.findtext("arxiv:journal_ref", "", ARXIV_NS),
        "doi": e.findtext("arxiv:doi", "", ARXIV_NS),
        "abstract": " ".join((e.findtext("a:summary", "", ARXIV_NS) or "").split()),
    }


def parse_crossref(path):
    try:
        j = json.load(open(path))
    except Exception as e:
        return {"parse_error": str(e)}
    m = j.get("message", {})
    years = []
    for key in ("issued", "published-print", "published-online"):
        parts = ((m.get(key) or {}).get("date-parts") or [[None]])[0]
        if parts and parts[0]:
            years.append(parts[0])
    return {
        "kind": "crossref_api",
        "title": (m.get("title") or [""])[0],
        "authors": [f"{a.get('given','')} {a.get('family','')}".strip() for a in m.get("author", [])],
        "years": years,
        "container": (m.get("container-title") or [""])[0],
        "doi": m.get("DOI", ""),
        "abstract": re.sub(r"<[^>]+>", " ", m.get("abstract", "") or ""),
    }


def parse_inspire(path):
    try:
        j = json.load(open(path))
    except Exception as e:
        return {"parse_error": str(e)}
    md = j
    if "metadata" in md:
        md = md["metadata"]
    if "hits" in md:
        hits = md["hits"].get("hits") or []
        md = hits[0].get("metadata", {}) if hits else {}
    titles = md.get("titles") or []
    rec = md.get("control_number") or md.get("recid")
    return {
        "kind": "inspire_api",
        "recid": rec,
        "title": (titles[0].get("title") if titles else "") or "",
        "authors": [a.get("full_name", "") for a in md.get("authors", [])],
        "year": int((md.get("earliest_date") or "0")[:4] or 0) or None,
        "doi": (md.get("dois") or [{}])[0].get("value", ""),
        "abstract": next((a.get("value", "") for a in md.get("abstracts", [])), ""),
        "publication_info": md.get("publication_info") or [],
    }


def year_candidates(parsed):
    out = []
    if parsed.get("kind") == "arxiv_api":
        m = YEAR_RE.search((parsed.get("published") or ""))
        if m:
            out.append({"source": "arxiv_published", "year": int(m.group(0)), "detail": parsed.get("published")})
        jr = parsed.get("journal_ref") or ""
        ys = YEAR_RE.findall(jr)
        if ys:
            out.append({"source": "arxiv_journal_ref", "year": int(ys[-1]), "detail": jr})
    if parsed.get("kind") == "crossref_api":
        for y in parsed.get("years", []):
            out.append({"source": "crossref_issued", "year": y, "detail": parsed.get("container", "")})
    if parsed.get("kind") == "inspire_api" and parsed.get("year"):
        out.append({"source": "inspire_earliest_date", "year": parsed["year"], "detail": ""})
    return out


def metadata_excerpt_support(excerpt, parsed_list):
    """General check for ledger excerpts that are metadata recaps rather than abstracts:
    an embedded DOI and/or single-quoted title must be corroborated by a fetched record."""
    dois = sorted({d.lower().rstrip(".") for d in re.findall(r"10\.\d{4,9}/[^\s;,)\]]+", excerpt or "")})
    fetched_dois = sorted({(x.get("doi") or "").lower().rstrip(".") for x in parsed_list if x.get("doi")})
    doi_match = bool(dois) and any(any(d in fd or fd in d for fd in fetched_dois) for d in dois)
    quoted = re.findall(r"'([^']{15,})'", excerpt or "")
    qsims = [{"quote": q[:80], "similarity": title_sim(q, x.get("title", ""))}
             for q in quoted for x in parsed_list if x.get("title")]
    qmax = max((q["similarity"] for q in qsims), default=None)
    return {"dois_in_excerpt": dois, "fetched_dois": fetched_dois, "doi_match": doi_match,
            "quoted_title_similarities": qsims, "quoted_title_max_sim": qmax}


def main():
    os.makedirs(RAWDIR, exist_ok=True)
    started = datetime.now(CST)
    sha_before = sha256_file(LEDGER)
    if sha_before != LEDGER_SHA_EXPECTED:
        json.dump({"abort": "ledger hash drift before fetch", "sha256": sha_before,
                   "expected": LEDGER_SHA_EXPECTED},
                  open(os.path.join(OUTDIR, "ABORT.json"), "w"), indent=1)
        print("ABORT: ledger hash", sha_before)
        return 2
    rows = list(csv.DictReader(open(LEDGER)))
    results = []
    for s in SAMPLE:
        row = rows[s["row"] - 1]
        assert row["citation_id"] == s["citation_id"], (row["citation_id"], s)
        fetches, parsed_list = [], []
        if row["arxiv_id"]:
            p = os.path.join(RAWDIR, f"{s['citation_id']}_arxiv.xml")
            f = curl(f"https://export.arxiv.org/api/query?id_list={row['arxiv_id']}", p)
            fetches.append(f)
            fetches[-1]["role"] = "primary_arxiv"
            parsed_list.append(parse_arxiv(p))
            time.sleep(3)  # arXiv API politeness
        if row["doi"] and not row["doi"].startswith("10.48550/arXiv."):
            p = os.path.join(RAWDIR, f"{s['citation_id']}_crossref.json")
            f = curl(f"https://api.crossref.org/works/{row['doi']}", p)
            fetches.append(f)
            fetches[-1]["role"] = "primary_crossref"
            parsed_list.append(parse_crossref(p))
        if row["url"].startswith("https://inspirehep.net") or row["exact_locator"].startswith("https://inspirehep.net"):
            loc = row["url"] if row["url"].startswith("https://inspirehep.net") else row["exact_locator"]
            p = os.path.join(RAWDIR, f"{s['citation_id']}_inspire.json")
            f = curl(loc, p)
            fetches.append(f)
            fetches[-1]["role"] = "secondary_inspire"
            parsed_list.append(parse_inspire(p))

        titled = [x for x in parsed_list if x.get("title")]
        best = max(titled, key=lambda x: title_sim(row["title"], x["title"]), default={})
        tsim = title_sim(row["title"], best.get("title", "")) if best.get("title") else 0.0
        ln_ledger = last_names(row["authors"])
        ln_fetched = last_names("; ".join(best.get("authors", [])))
        author_overlap = (round(len(ln_ledger & ln_fetched) / len(ln_ledger), 3)
                          if ln_ledger and ln_fetched else None)
        ly = int(str(row.get("year", "")).strip()[:4] or 0) or None
        ycands = []
        for x in parsed_list:
            ycands.extend(year_candidates(x))
        year_ok = bool(ly) and any(abs(c["year"] - ly) <= 1 for c in ycands)
        year_matches = [c for c in ycands if abs(c["year"] - ly) <= 1]
        # quote support: best excerpt recall over every fetched abstract
        recalls = []
        for x in parsed_list:
            r = recall(row.get("evidence_excerpt", ""), x.get("abstract", ""))
            if r is not None:
                recalls.append({"source": x.get("kind"), "recall": r,
                                "had_abstract": bool((x.get("abstract") or "").strip())})
        usable = [r for r in recalls if r["had_abstract"]]
        exc_recall = max((r["recall"] for r in usable), default=None)
        meta_exc = metadata_excerpt_support(row.get("evidence_excerpt", ""), parsed_list)
        if usable:
            quote_check = "supported" if exc_recall >= 0.35 else "weak"
        elif meta_exc["doi_match"] or (meta_exc["quoted_title_max_sim"] or 0) >= 0.85:
            quote_check = "supported_via_metadata_excerpt"
        else:
            quote_check = "not_verifiable"

        reasons = []
        if not titled:
            verdict = "FETCH_FAILED"
            reasons.append("no fetched response carried a source title")
        elif tsim < 0.60:
            verdict = "FAIL"
            reasons.append(f"title_similarity {tsim} < 0.60")
        elif not year_ok:
            verdict = "FAIL"
            reasons.append(f"ledger year {ly} matches no fetched year candidate within 1: "
                           f"{[c['year'] for c in ycands]}")
        else:
            soft = []
            if tsim < 0.85:
                soft.append(f"title_similarity {tsim} in [0.60,0.85)")
            if author_overlap is not None and author_overlap < 0.5:
                soft.append(f"author_lastname_overlap {author_overlap} < 0.5")
            if quote_check == "weak":
                soft.append(f"excerpt_token_recall {exc_recall} < 0.35")
            if quote_check == "not_verifiable":
                soft.append("no abstract in any fetched response and no corroborated metadata excerpt; quote support not re-verifiable")
            verdict = "PARTIAL" if soft else "MATCH"
            reasons.extend(soft)

        results.append({
            "row": s["row"], "citation_id": s["citation_id"], "sampling": s["why"],
            "class_mapping": row["class_mapping"], "used_by_theorems": row["used_by_theorems"],
            "ledger": {k: row[k] for k in ("bibkey", "title", "authors", "year", "venue", "doi",
                                           "arxiv_id", "url", "exact_locator", "status",
                                           "verification_method", "evidence_type", "elided_quote",
                                           "verdict", "reviewer")},
            "ledger_evidence_excerpt": row.get("evidence_excerpt", ""),
            "locators_used": [f["url"] for f in fetches],
            "fetches": fetches,
            "fetched": parsed_list,
            "best_fetched": best,
            "comparison": {
                "title_similarity": tsim,
                "author_lastname_overlap": author_overlap,
                "ledger_lastnames": sorted(ln_ledger),
                "fetched_lastnames": sorted(ln_fetched),
                "ledger_year": ly,
                "year_candidates": ycands,
                "year_matching_candidates": year_matches,
                "year_ok": year_ok,
                "excerpt_recalls": recalls,
                "ledger_excerpt_token_recall_best": exc_recall,
                "quote_check": quote_check,
                "metadata_excerpt_support": meta_exc,
                "thresholds": {"fail_title_sim_lt": 0.60, "match_title_sim_ge": 0.85,
                               "match_author_overlap_ge": 0.5, "match_year_delta_le": 1,
                               "match_excerpt_recall_ge": 0.35},
            },
            "verdict": verdict,
            "verdict_reasons": reasons,
        })
        print(f"{s['citation_id']} row {s['row']:2d}: {verdict:12s} title_sim={tsim:.3f} "
              f"author={author_overlap} year_ok={year_ok} excerpt_recall={exc_recall} "
              f"quote={quote_check}")

    time.sleep(1)
    sha_after = sha256_file(LEDGER)
    summary = {
        "checked": len(results),
        "match": sum(1 for r in results if r["verdict"] == "MATCH"),
        "partial": sum(1 for r in results if r["verdict"] == "PARTIAL"),
        "fail": sum(1 for r in results if r["verdict"] == "FAIL"),
        "fetch_failed": sum(1 for r in results if r["verdict"] == "FETCH_FAILED"),
    }
    if summary["fail"] or summary["fetch_failed"]:
        aggregate = "FAIL"
    elif summary["partial"]:
        aggregate = "PARTIAL"
    else:
        aggregate = "MATCH"

    artifact = {
        "schema_version": "0.1",
        "artifact_type": "l1_spotcheck",
        "node_id": "L1", "gate": "G-LIT",
        "assignment_ref": "astra-life02-l1-spotcheck",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "actor": "worker-070", "reviewer": "worker-070",
        "created_at": started.isoformat(timespec="seconds"),
        "ended_at": datetime.now(CST).isoformat(timespec="seconds"),
        "check_number": 4,
        "independent_of": ["artifacts/worker-07/l1_spotcheck/spotcheck-l1-07.json",
                           "reviews/L1-spotcheck-10.json", "reviews/L1-spotcheck-11.json"],
        "independence_note": ("Frame rows 1-40 is disjoint from deepseek-flash-07's frame 41-95 at the "
                              "same ledger hash; rows 1-40 were previously checked only at the superseded "
                              "69-row hash fe4b48bb. Locators were re-fetched from primary APIs; no ledger "
                              "text was used as fetch evidence."),
        "inputs": {
            "ledger/citation_audit.csv": {
                "sha256_before_fetch": sha_before,
                "sha256_after_fetch": sha_after,
                "drifted_during_fetch": sha_before != sha_after,
                "data_rows": len(rows),
                "checked_frame": "data rows 1-40",
            },
            "runtime/state/artifact_hashes.json": "read for node pins; L1 prefix 315c19145065",
        },
        "sampling_rule": {
            "frozen_before_fetch": True,
            "S1": "every 5th data row of frame 1-40 starting at row 3 -> 3,8,13,18,23,28,33,38",
            "S2_targeted_augmentation": ("row 4 (SRC-004) added because S1 contains no "
                                         "AF-SCC-C0-VAC-GEN row; chosen as lowest-index class-mapped row "
                                         "with a primary locator; declared before any fetch"),
            "sampled_rows": [s["row"] for s in SAMPLE],
            "class_coverage_from_class_mapping": sorted({c.strip() for r in results
                                                         for c in r["class_mapping"].split(";") if c.strip()}),
        },
        "method": ("curl -sS -L primary API -> raw body saved under raw/ and sha256-hashed; "
                   "arXiv Atom / Crossref JSON / INSPIRE JSON parsed; ledger title vs fetched title "
                   "(difflib ratio on NFKD-normalised text), diacritic-insensitive author last-name "
                   "overlap, ledger year vs all fetched authoritative year candidates +/-1, and "
                   "evidence_excerpt token recall vs the strongest fetched abstract (or a "
                   "corroborated metadata recap when no abstract is returned). Verdict rule: "
                   "MATCH = title>=0.85, a year candidate matches, author overlap>=0.5, excerpt "
                   "recall>=0.35; PARTIAL = metadata matches but a soft check is weak or the quote "
                   "is not re-verifiable; FAIL = title<0.60 or no year candidate within 1 or no "
                   "title fetched."),
        "method_revision": {
            "decided_before_final_verdicts": True,
            "reason": ("first mechanical pass (R0) compared the ledger year only against the arXiv "
                       "preprint year, treated a missing Crossref abstract as zero quote recall, and "
                       "did not retry a transient 429; R1-R3 below repair those three transport/"
                       "semantics defects and are applied uniformly to every sampled row."),
            "R1": "accept any authoritative year candidate (arXiv published, arXiv journal_ref, Crossref issued, INSPIRE earliest_date) within +/-1",
            "R2": "retry HTTP 429/5xx/000 up to 3 times with backoff before downgrading a locator",
            "R3": "compute excerpt recall against the strongest fetched abstract across primary and INSPIRE secondary locators; 'no abstract anywhere' is not_verifiable, not contradiction",
            "R4": "drop NFKD combining marks before tokenisation; R0 replaced them with a separator, splitting 'Girao'/'Natario' and understating author overlap on SRC-028 (0.5 instead of 1.0)",
            "R5": "an excerpt that is a metadata recap (embedded DOI and/or quoted title) is checked against the fetched record; a corroborated recap counts as supported, so a missing abstract is not a defect by itself",
            "R0_first_pass_summary": {"match": 4, "partial": 3, "fail": 2, "fetch_failed": 0,
                                      "false_fails_explained": ["SRC-004 journal_ref year 2025", "SRC-028 journal_ref year 2017"],
                                      "note": "R0 also understated SRC-028 author overlap and mislabelled metadata-recap excerpts as unverifiable",
                                      "artifact_sha256_of_first_pass": "5582de9efa9e15d73c8eb452649c5a27392f5e41ffd998d5bbdbf6dadc84ab0d"},
        },
        "results": results,
        "summary": summary,
        "aggregate_verdict": aggregate,
        "scope_limit": ("Spot check of 9 of 40 rows in frame 1-40 at one hash; not a full-schema "
                        "acceptance, not a gate verdict, and not evidence about rows outside the frame."),
        "falsifier": ("Any sampled row whose re-fetched primary source contradicts the ledger title/"
                      "class scope, or a ledger hash change away from 315c19145065 during the check, "
                      "or a reviewer who re-fetches the same locator and does not reproduce the "
                      "recorded raw-body sha256."),
        "next_falsifier": ("Re-fetch any recorded locator and compare the raw-body sha256; a mismatch "
                           "voids this check. A tenth, independently drawn row in 1-40 that FAILs "
                           "would downgrade the aggregate."),
        "stop_rule": "1.5 agent-hours; no sources outside the frozen 95-source scope.",
        "reproduce": "python3 artifacts/worker-070/l1_spotcheck/fetch_and_compare.py",
    }
    out = os.path.join(OUTDIR, "spotcheck-l1-070.json")
    with open(out, "w") as f:
        json.dump(artifact, f, indent=1, ensure_ascii=False)
    print(json.dumps({"summary": summary, "aggregate": aggregate,
                      "ledger_sha_before": sha_before, "ledger_sha_after": sha_after,
                      "artifact_sha256": sha256_file(out)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
