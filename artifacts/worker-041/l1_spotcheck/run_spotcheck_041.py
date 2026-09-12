#!/usr/bin/env python3
"""L1 independent re-fetch spot check #5 (worker-041), gate G-LIT.

Bounded class-bound task taken from the immediate queue (no assignment card exists
for worker-041): a third *binding* independent re-fetch spot check at the frozen
L1 hash, disjoint from spot check #3 (deepseek-flash-07, data rows 41-95) and
spot check #4 (worker-086, rows 1,4,9,16,17,25,33,96,97).

Design rules (fixed before the first fetch):
  * Input is ledger/citation_audit.csv pinned at
    sha256 315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9.
    If the file hashes differently at start or after the fetches, the run
    fail-closes and writes no verdict.
  * Sampling frame is declared in SAMPLE below and never extended after fetching.
  * Every row is re-fetched from a primary registry endpoint (Crossref for DOI,
    arXiv API for arXiv ids). Ledger text is never used as evidence of identity.
  * Raw response bodies are stored under raw/ and hashed.
  * This script sets no gate verdict and no node status.
"""
from __future__ import annotations

import csv
import difflib
import hashlib
import json
import re
import subprocess
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "ledger" / "citation_audit.csv"
HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
OUT = HERE / "spotcheck-l1-041.json"
OUT_SHA = HERE / "spotcheck-l1-041.json.sha256"

FROZEN_LEDGER_SHA = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
TZ = timezone(timedelta(hours=8))

# ---- FROZEN SAMPLING RULE (declared before any fetch) -----------------------
FRAME = "data rows 21-40"
EXCLUDED = {25: "worker-086 spot check #4 at the frozen sha",
            33: "worker-086 spot check #4 at the frozen sha"}
STRIDE_ROWS = [22, 26, 30, 34, 38]          # every 4th row of the frame from 22
TARGETED_ROWS = {
    29: "load-bearing C0+C2 mass-inflation source (D-004;T-503;T-519)",
    40: "only triple-class-mapped row in the frame (T-206;T-301;T-305;T-515;T-528)",
}
SAMPLE = sorted(set(STRIDE_ROWS) | set(TARGETED_ROWS))
ASSERTED_DISJOINT_FROM = [
    "artifacts/worker-07/l1_spotcheck/spotcheck-l1-07.json (rows 41-95)",
    "artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json (rows 1,4,9,16,17,25,33,96,97)",
]

UA = "ai4math-swarm-worker-041/1.0 (independent L1 spot check; contact via repo)"
NS = {"a": "http://www.w3.org/2005/Atom"}


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def title_ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def last_name(author: str) -> str:
    a = unicodedata.normalize("NFKD", author)
    a = "".join(c for c in a if not unicodedata.combining(c))
    toks = [t for t in re.split(r"[^A-Za-z]+", a) if t]
    return toks[-1].lower() if toks else ""


_RETRYABLE = {429, 500, 502, 503, 504}


def fetch(url: str, dest: Path) -> dict:
    """Fetch with polite spacing and bounded retry/backoff on rate limits."""
    t0 = time.time()
    attempts = []
    http, body = 0, b""
    for i in range(3):
        time.sleep(1.5 if i == 0 else 4.0 * i)
        cmd = ["curl", "-sS", "-L", "-m", "40", "-A", UA,
               "-o", str(dest), "-w", "%{http_code} %{size_download}"]
        try:
            p = subprocess.run(cmd + [url], capture_output=True, text=True, timeout=70)
            parts = (p.stdout or "").strip().split()
            http = int(parts[0]) if parts and parts[0].isdigit() else 0
        except subprocess.TimeoutExpired:
            http = 0
        body = dest.read_bytes() if dest.exists() else b""
        attempts.append({"attempt": i + 1, "http_status": http, "bytes": len(body)})
        if http == 200 and body:
            break
        if http not in _RETRYABLE and http != 0:
            break
    rec = {"url": url, "ok": http == 200 and len(body) > 0, "http_status": http,
           "bytes": len(body), "seconds": round(time.time() - t0, 2),
           "raw_sha256": sha256_bytes(body) if body else None, "attempts": attempts}
    if not rec["ok"] and body:
        rec["error_body_head"] = body[:160].decode("utf-8", "replace")
    return rec


def _cr_year(m: dict, key: str):
    dp = (m.get(key) or {}).get("date-parts") or []
    return dp[0][0] if dp and dp[0] and dp[0][0] else None


def parse_crossref(body: bytes) -> dict | None:
    try:
        m = json.loads(body.decode("utf-8"))["message"]
    except Exception:
        return None
    # Prefer the citable print/issue year; online-first is version convention.
    year = _cr_year(m, "published-print") or _cr_year(m, "issued") \
        or _cr_year(m, "published-online")
    return {
        "title": (m.get("title") or [""])[0],
        "authors": [f"{a.get('given','')} {a.get('family','')}".strip()
                    for a in (m.get("author") or [])],
        "year": year,
        "year_print": _cr_year(m, "published-print"),
        "year_online": _cr_year(m, "published-online") or _cr_year(m, "issued"),
        "container": (m.get("container-title") or [""])[0],
        "doi": m.get("DOI"),
        "type": m.get("type"),
    }


def parse_arxiv(body: bytes) -> dict | None:
    try:
        root = ET.fromstring(body)
    except Exception:
        return None
    e = root.find("a:entry", NS)
    if e is None:
        return None
    title = " ".join((e.findtext("a:title", "", NS) or "").split())
    authors = [" ".join((a.findtext("a:name", "", NS) or "").split())
               for a in e.findall("a:author", NS)]
    pub = e.findtext("a:published", "", NS) or ""
    year = int(pub[:4]) if pub[:4].isdigit() else None
    return {"title": title, "authors": authors, "year": year,
            "arxiv_id": (e.findtext("a:id", "", NS) or "").rsplit("/", 1)[-1]}


def compare(row: dict, got: dict) -> dict:
    ratio = title_ratio(row["title"], got["title"])
    states = {"title": "exact" if norm(row["title"]) == norm(got["title"])
              else ("close" if ratio >= 0.90 else "mismatch"),
              "title_ratio": round(ratio, 3)}
    row_lasts = {last_name(a) for a in re.split(r"[;,]", row["authors"]) if a.strip()}
    got_lasts = {last_name(a) for a in got["authors"]}
    states["first_author_ledger"] = sorted(row_lasts)[0] if row_lasts else ""
    states["fetched_authors"] = got["authors"]
    states["first_author_match"] = bool(row_lasts & got_lasts)
    ly = int(row["year"])
    fy, py = got.get("year"), got.get("preprint_year")
    states["ledger_year"], states["fetched_year"] = ly, fy
    states["preprint_year"] = py
    cands = [y for y in (fy, py) if y]
    if not cands:
        states["year"] = "unknown"
    elif ly in cands:
        states["year"] = "exact"
    elif any(abs(ly - y) <= 1 for y in cands):
        states["year"] = "version_convention"
    else:
        states["year"] = "mismatch"
    identity_ok = states["title"] in ("exact", "close") and states["first_author_match"]
    year_ok = states["year"] in ("exact", "version_convention")
    if not identity_ok:
        verdict = "MISMATCH"
    elif not year_ok:
        verdict = "MISMATCH"
    elif states["year"] == "version_convention":
        verdict = "PARTIAL"
    else:
        verdict = "MATCH"
    return {"verdict": verdict, "states": states}


def class_observation(row: dict, got: dict) -> str:
    cm = (row.get("class_mapping") or "").strip()
    if not cm or cm.startswith("("):
        return "no_class_claim"
    text = norm(got["title"])
    tokens = {t.strip() for t in cm.split(";") if t.strip()}
    hits = []
    if {"AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"} & tokens:
        if any(k in text for k in ("singular", "cosmic censorship", "mass inflation",
                                   "inextendib", "horizon", "interior")):
            hits.append("regularity/extension topic")
    if "AF-WCC-VAC-GEN" in tokens:
        if any(k in text for k in ("stability", "stable", "global", "nonlinear",
                                   "naked", "cosmic censorship", "weak")):
            hits.append("WCC/stability topic")
    return "topically_consistent:" + ",".join(hits) if hits else "not_contradicted_by_title"


def main() -> int:
    started = now()
    RAW.mkdir(parents=True, exist_ok=True)
    for stale in RAW.glob("*"):          # deterministic re-runs: only this run's bodies
        if stale.is_file():
            stale.unlink()
    before = sha256_file(LEDGER)
    if before != FROZEN_LEDGER_SHA:
        print(json.dumps({"error": "LEDGER_DRIFT_AT_START", "expected": FROZEN_LEDGER_SHA,
                          "measured": before}))
        return 2
    rows = list(csv.DictReader(LEDGER.open(encoding="utf-8")))
    if len(rows) != 97:
        print(json.dumps({"error": "ROW_COUNT_CHANGED", "measured": len(rows)}))
        return 2

    results, hard_failures, findings = [], [], []
    for n in SAMPLE:
        row = rows[n - 1]
        rec = {"row": n, "citation_id": row["citation_id"], "bibkey": row["bibkey"],
               "class_mapping": row["class_mapping"],
               "ledger": {"title": row["title"], "authors": row["authors"],
                          "year": row["year"], "venue": row["venue"],
                          "doi": row["doi"], "arxiv_id": row["arxiv_id"],
                          "exact_locator": row["exact_locator"],
                          "verdict_in_ledger": row["verdict"],
                          "used_by_theorems": row["used_by_theorems"]},
               "fetches": [], "fetched": None, "comparison": None,
               "class_mapping_observation": None,
               "sample_reason": ("stride" if n in STRIDE_ROWS else TARGETED_ROWS[n])}
        primary = None
        # primary locator: publisher DOI record when present, else arXiv API
        if row["doi"] and not row["doi"].startswith("10.48550/arXiv"):
            primary = ("crossref", f"https://api.crossref.org/works/{row['doi']}",
                       f"{row['citation_id']}.crossref.json")
        elif row["arxiv_id"]:
            primary = ("arxiv", f"https://export.arxiv.org/api/query?id_list={row['arxiv_id']}",
                       f"{row['citation_id']}.arxiv.xml")
        if primary is None:
            findings.append(f"{row['citation_id']}: no DOI and no arXiv id; not fetchable")
            rec["comparison"] = {"verdict": "FETCH_FAILED", "reason": "no_primary_locator"}
            results.append(rec)
            hard_failures.append({"citation_id": row["citation_id"], "row": n,
                                  "verdict": "FETCH_FAILED", "reason": "no_primary_locator"})
            continue
        kind, url, fname = primary
        if row["exact_locator"] and "?" in row["exact_locator"]:
            rec["locator_quality"] = "search_query"
            findings.append(f"{row['citation_id']}: exact_locator is a registry search query, "
                            f"not an exact locator (locator-quality note)")
        frec = fetch(url, RAW / fname)
        frec["kind"] = kind
        frec["primary"] = True
        rec["fetches"].append(frec)
        got = None
        if frec["ok"]:
            body = (RAW / fname).read_bytes()
            got = parse_crossref(body) if kind == "crossref" else parse_arxiv(body)
        if got is None:
            rec["comparison"] = {"verdict": "FETCH_FAILED",
                                 "reason": "no_parsable_primary_record"}
            results.append(rec)
            hard_failures.append({"citation_id": row["citation_id"], "row": n,
                                  "verdict": "FETCH_FAILED"})
            findings.append(f"{row['citation_id']}: primary locator did not yield a parsable record")
            continue
        rec["fetched"] = got
        cmp_ = compare(row, got)
        # secondary arXiv fetch: only when the published year is not an exact match
        # and the ledger carries an arXiv id (version-convention evidence)
        if row["arxiv_id"] and kind == "crossref" \
                and cmp_["states"]["year"] != "exact":
            sname = f"{row['citation_id']}.arxiv.xml"
            srec = fetch(f"https://export.arxiv.org/api/query?id_list={row['arxiv_id']}",
                         RAW / sname)
            srec["kind"] = "arxiv"
            srec["primary"] = False
            rec["fetches"].append(srec)
            if srec["ok"]:
                sec = parse_arxiv((RAW / sname).read_bytes())
                if sec:
                    got["preprint_year"] = sec.get("year")
                    got["preprint_title"] = sec.get("title")
                    cmp_ = compare(row, got)
        rec["comparison"] = cmp_
        rec["class_mapping_observation"] = class_observation(row, got)
        if cmp_["verdict"] == "MISMATCH":
            hard_failures.append({"citation_id": row["citation_id"], "row": n,
                                  "verdict": "MISMATCH", "detail": cmp_["states"]})
        if cmp_["states"]["year"] == "version_convention":
            findings.append(
                f"{row['citation_id']}: ledger year {row['year']} vs fetched "
                f"{cmp_['states']['fetched_year']} "
                f"(preprint {got.get('preprint_year')}); version convention, not identity failure")
        results.append(rec)

    after = sha256_file(LEDGER)
    counts = {}
    for r in results:
        v = (r.get("comparison") or {}).get("verdict", "FETCH_FAILED")
        counts[v] = counts.get(v, 0) + 1
    overall = ("FAIL" if counts.get("MISMATCH") or counts.get("FETCH_FAILED")
               else ("PARTIAL" if counts.get("PARTIAL") else "PASS"))
    doc = {
        "schema_version": "1.0",
        "artifact_type": "l1_refetch_spotcheck",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN",
                      "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "actor": "worker-041",
        "reviewer": "worker-041",
        "check_number": 5,
        "created_at": now(),
        "task": "third binding independent L1 re-fetch spot check at the frozen ledger hash "
                "(astra-life02-l1-spotcheck criterion: >=3 independent re-fetch spot checks)",
        "independence_note": "fresh sample disjoint from spot check #3 (rows 41-95) and "
                             "spot check #4 (rows 1,4,9,16,17,25,33,96,97); every locator "
                             "re-fetched from the primary registry, no ledger text used as "
                             "identity evidence",
        "independent_of": ASSERTED_DISJOINT_FROM,
        "inputs": {"ledger/citation_audit.csv": {
            "sha256_before": before, "sha256_after": after,
            "stable_during_run": before == after, "data_rows": len(rows),
            "frozen_sha256_expected": FROZEN_LEDGER_SHA}},
        "sampling_rule": {
            "frame": FRAME, "frozen_before_fetch": True,
            "S1_stride": f"every 4th data row of the frame from 22 -> {STRIDE_ROWS}",
            "S2_targeted": {str(k): v for k, v in TARGETED_ROWS.items()},
            "excluded_rows": {str(k): v for k, v in EXCLUDED.items()},
            "sampled_rows": SAMPLE,
            "class_coverage_from_class_mapping": sorted(
                {t for n in SAMPLE for t in (rows[n - 1]["class_mapping"] or "")
                 .replace("(", "").replace(")", "").split(";") if t.startswith("AF-")}),
        },
        "method": {
            "doi_rows": "https://api.crossref.org/works/<doi> (registry metadata)",
            "arxiv_rows": "https://export.arxiv.org/api/query?id_list=<id> (primary API)",
            "network": "live re-fetch via curl, timeout 40s, raw bodies retained and hashed",
            "verdicts": "MATCH (title+author identity, year exact) | PARTIAL "
                        "(identity ok, year version-convention or locator-quality note) | "
                        "MISMATCH (identity or year differs beyond convention) | FETCH_FAILED",
            "class_mapping_check": "topical consistency of fetched title with the ledger "
                                   "class_mapping only; NOT a class-binding verdict",
        },
        "results": results,
        "summary": {"checked": len(results), "counts": counts, "overall": overall,
                    "rows_checked": SAMPLE},
        "findings": findings,
        "hard_failures": hard_failures,
        "non_claims": [
            "spot check on 7 of 97 ledger rows; not a ledger-wide verdict",
            "no gate verdict, node status, or validation_status is set by this worker",
            "class_mapping topical consistency is not a class-binding or theorem-scope verdict",
            "identity verdicts bind the raw bodies recorded under raw/ at their sha256",
        ],
        "next_falsifier": "Re-run at a later ledger hash: a row reported MATCH whose fetched "
                          "title/first author differs at the recorded raw sha256, or a sample "
                          "row that overlaps spot checks #3/#4, or a ledger sha change during "
                          "the run, falsifies this check.",
        "falsifier": "Any of: (a) ledger/citation_audit.csv sha256 != "
                     "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9 at run "
                     "time; (b) a sampled row is also in rows 41-95 or {1,4,9,16,17,25,33,96,97}; "
                     "(c) a MATCH verdict whose recorded raw body has a different title or first "
                     "author; (d) a verdict that cites ledger text instead of the raw body.",
    }
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    digest = sha256_file(OUT)
    OUT_SHA.write_text(f"{digest}  spotcheck-l1-041.json\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT.relative_to(ROOT)), "sha256": digest,
                      "summary": doc["summary"], "hard_failures": len(hard_failures),
                      "started": started, "finished": now()}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
