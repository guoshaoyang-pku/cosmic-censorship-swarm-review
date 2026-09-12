#!/usr/bin/env python3
"""W026-L1-SPOTCHECK-05: independent L1 re-fetch spot check.

Reads the frozen preregistration.json, fetches the primary locator for each
declared row, hashes raw bodies, compares against the ledger's bibliographic
claim with the pre-declared thresholds, and writes spotcheck-l1-026.json.

Fail-closed: the ledger sha256 must equal the preregistered value at every read.
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
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
LEDGER = ROOT / "ledger" / "citation_audit.csv"
PRE = HERE / "preregistration.json"
OUT = HERE / "spotcheck-l1-026.json"
PIN_SHA = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
CST = timezone(timedelta(hours=8))
UA = "ai4math-swarm-worker-026/1.0 (spotcheck; mailto:worker-026@example.invalid)"
ARXIV_API = "https://export.arxiv.org/api/query?id_list={id}&max_results=1"
CROSSREF_API = "https://api.crossref.org/works/{doi}"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def measure_ledger() -> str:
    return hashlib.sha256(LEDGER.read_bytes()).hexdigest()


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = s.lower()
    s = re.sub(r"^(wiley|ams|aps|arxiv|springer|inspire|crossref)\s+(abstract|excerpt)\s*:?\s*", "", s)
    s = re.sub(r"^[a-z0-9 .\-()/]{0,40}(abstract|excerpt)\s*:?\s*", "", s)
    s = re.sub(r"\$[^$]*\$", " ", s)
    s = re.sub(r"\\[a-z]+", " ", s)
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-")
    s = s.strip(" '\"….")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def sim(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def curl(url: str) -> tuple[int, bytes]:
    p = subprocess.run(
        ["curl", "-sS", "-L", "--max-time", "45", "-A", UA, "-w", "\n%{http_code}", url],
        capture_output=True,
    )
    body = p.stdout
    if body.endswith(b"\n") or True:
        # last line is the http code
        idx = body.rfind(b"\n")
        code = body[idx + 1:].strip() if idx >= 0 else b""
        raw = body[:idx] if idx >= 0 else b""
    try:
        status = int(code)
    except ValueError:
        status = 0
    if status != 200:
        return status, body
    return status, raw


def parse_arxiv(raw: bytes) -> dict:
    ns = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(raw)
    entry = root.find("a:entry", ns)
    if entry is None:
        return {}
    title = " ".join((entry.findtext("a:title", "", ns) or "").split())
    authors = [a.findtext("a:name", "", ns) for a in entry.findall("a:author", ns)]
    published = entry.findtext("a:published", "", ns) or ""
    summary = " ".join((entry.findtext("a:summary", "", ns) or "").split())
    journal = entry.findtext("arxiv:journal_ref", "", ns)
    doi = entry.findtext("arxiv:doi", "", ns)
    return {"kind": "arxiv", "title": title, "authors": authors,
            "year": int(published[:4]) if published[:4].isdigit() else None,
            "venue": journal or "", "abstract": summary, "doi": doi}


def parse_crossref(raw: bytes) -> dict:
    d = json.loads(raw.decode("utf-8", "replace"))["message"]
    title = " ".join((d.get("title") or [""])[0].split())
    authors = []
    for a in d.get("author", []) or []:
        authors.append(" ".join(x for x in [a.get("given"), a.get("family")] if x))
    issued = (d.get("issued", {}).get("date-parts") or [[None]])[0]
    year = issued[0] if issued else None
    venue = " ".join((d.get("container-title") or [""])[0].split())
    abstract = d.get("abstract") or ""
    abstract = re.sub(r"<[^>]+>", " ", abstract)
    return {"kind": "crossref", "title": title, "authors": authors, "year": year,
            "venue": venue, "abstract": " ".join(abstract.split()), "doi": d.get("DOI", "")}


def main() -> int:
    pre = json.loads(PRE.read_text())
    rows = list(csv.DictReader(LEDGER.open()))
    by_row = {i: r for i, r in enumerate(rows, start=1)}
    sampled = pre["sampling_rule"]["sampled_rows"]

    before = measure_ledger()
    if before != PIN_SHA:
        print(json.dumps({"status": "VOID", "reason": "ledger hash before fetch != preregistered",
                          "measured": before, "pinned": PIN_SHA}, indent=2))
        return 2

    RAW.mkdir(parents=True, exist_ok=True)
    results = []
    for rn in sampled:
        r = by_row[rn]
        cid = r["citation_id"]
        arxiv_id = (r.get("arxiv_id") or "").strip()
        doi = (r.get("doi") or "").strip()
        entry = {
            "row": rn, "citation_id": cid, "class_mapping": r.get("class_mapping", ""),
            "used_by_theorems": r.get("used_by_theorems", ""),
            "ledger_claim": {"title": r["title"], "authors": r["authors"], "year": int(r["year"]) if r["year"].isdigit() else None,
                             "venue": r["venue"], "doi": doi, "arxiv_id": arxiv_id,
                             "exact_locator": r["exact_locator"], "verdict_column": r["verdict"],
                             "status_column": r["status"]},
            "fetched": None, "locator_used": None, "raw_sha256": None, "http_status": None,
        }
        fetches = []
        if arxiv_id:
            fetches.append(("primary", ARXIV_API.format(id=arxiv_id), "arxiv", f"{cid}.arxiv.xml"))
        elif doi:
            fetches.append(("primary", CROSSREF_API.format(doi=doi), "crossref", f"{cid}.crossref.json"))
        else:
            entry["fetch_note"] = "no arxiv_id and no doi in the ledger row"
        if arxiv_id and doi and not doi.startswith("10.48550/arXiv."):
            fetches.append(("secondary", CROSSREF_API.format(doi=doi), "crossref", f"{cid}.crossref.json"))

        for role, url, kind, fname in fetches:
            status, raw = curl(url)
            if status != 200:
                fetches_note = {"role": role, "url": url, "http_status": status, "bytes": len(raw)}
                entry.setdefault("fetch_attempts", []).append(fetches_note)
                continue
            (RAW / fname).write_bytes(raw)
            h = sha256_bytes(raw)
            try:
                parsed = parse_arxiv(raw) if kind == "arxiv" else parse_crossref(raw)
            except Exception as e:  # noqa: BLE001
                parsed = {"parse_error": str(e)}
            rec = {"role": role, "kind": kind, "url": url, "http_status": status,
                   "bytes": len(raw), "raw_path": str((RAW / fname).relative_to(ROOT)),
                   "raw_sha256": h, "parsed": parsed}
            entry.setdefault("fetch_attempts", []).append(rec)
            if role == "primary":
                entry["fetched"] = parsed
                entry["locator_used"] = url
                entry["raw_sha256"] = h
                entry["raw_path"] = rec["raw_path"]
                entry["http_status"] = status

        # compare
        f = entry.get("fetched") or {}
        if not f or entry.get("http_status") != 200:
            entry["verdict"] = "FETCH_FAILED"
            entry["comparison"] = {}
        else:
            lt, ft = norm(r["title"]), norm(f.get("title", ""))
            title_similarity = round(sim(lt, ft), 4)
            first_ledger = (r["authors"] or "").split(";")[0].strip()
            first_last = first_ledger.split()[-1].lower() if first_ledger else ""
            authors_fetched = [a.lower() for a in (f.get("authors") or [])]
            first_author_match = bool(first_last) and any(first_last in a for a in authors_fetched)
            ly = int(r["year"]) if r["year"].isdigit() else None
            fy = f.get("year")
            year_delta = (fy - ly) if (fy is not None and ly is not None) else None
            lex = norm(r["evidence_excerpt"])
            fab = norm(f.get("abstract", ""))
            excerpt_similarity = round(sim(lex[:400], fab[:400]), 4)
            contained = bool(lex) and lex[:200] in fab
            locator_is_search = ("search_query=" in (r["exact_locator"] or "")) or ("?q=" in (r["exact_locator"] or ""))
            entry["comparison"] = {
                "title_similarity": title_similarity, "first_author_match": first_author_match,
                "year_delta": year_delta, "excerpt_similarity_first400": excerpt_similarity,
                "excerpt_contained": contained, "locator_is_search_query": locator_is_search,
            }
            if title_similarity >= 0.95 and first_author_match and (year_delta is not None and abs(year_delta) <= 1) and (excerpt_similarity >= 0.60 or contained):
                v = "MATCH"
            elif title_similarity < 0.85:
                v = "MISMATCH"
            elif excerpt_similarity < 0.25 and fab:
                v = "MISMATCH"
            elif not first_author_match:
                v = "MISMATCH"
            else:
                v = "PARTIAL"
            entry["verdict"] = v
        results.append(entry)

    after = measure_ledger()
    drifted = after != PIN_SHA

    hard = [{"citation_id": e["citation_id"], "row": e["row"], "verdict": e["verdict"],
             "comparison": e.get("comparison")} for e in results if e["verdict"] == "MISMATCH"]
    summary = {
        "checked": len(results),
        "MATCH": sum(1 for e in results if e["verdict"] == "MATCH"),
        "PARTIAL": sum(1 for e in results if e["verdict"] == "PARTIAL"),
        "MISMATCH": sum(1 for e in results if e["verdict"] == "MISMATCH"),
        "FETCH_FAILED": sum(1 for e in results if e["verdict"] == "FETCH_FAILED"),
        "locator_quality_notes": [
            {"citation_id": e["citation_id"], "row": e["row"], "exact_locator_kind": "search_query",
             "note": "ledger exact_locator is a search query, not an exact identifier; verdict was taken from the DOI/arXiv id instead"}
            for e in results if (e.get("comparison") or {}).get("locator_is_search_query")
        ],
    }
    out = {
        "schema_version": "0.1",
        "artifact_type": "l1_refetch_spotcheck",
        "task_id": "W026-L1-SPOTCHECK-05",
        "node_id": "L1", "gate": "G-LIT", "actor": "worker-026", "reviewer": "worker-026",
        "created_at": now(), "check_number": 5,
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "independence_note": pre["independence"]["why_this_frame"],
        "independent_of": pre["independence"]["independent_of"],
        "inputs": {
            "ledger/citation_audit.csv": {
                "sha256_before_fetch": before, "sha256_after_fetch": after,
                "drifted_during_fetch": drifted, "pinned": PIN_SHA,
            },
            "artifacts/worker-026/l1_spotcheck/preregistration.json": {
                "sha256": sha256_bytes(PRE.read_bytes()),
            },
        },
        "method": pre["method"]["primary_locator_policy"] + " " + pre["method"]["normalisation"],
        "verdict_rule": pre["method"]["verdict_rule"],
        "results": results, "summary": summary, "hard_failures": hard,
        "non_claims": pre["non_claims"],
        "valid": (not drifted) and summary["FETCH_FAILED"] == 0,
        "void_reason": None if not drifted else "ledger sha256 changed during the fetch window; check VOID (fail-closed)",
    }
    OUT.write_text(json.dumps(out, indent=2, sort_keys=True))
    p = subprocess.run(["sha256sum", str(OUT)], capture_output=True, text=True)
    print(p.stdout.strip())
    print(json.dumps({"valid": out["valid"], "summary": summary, "drifted": drifted}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
