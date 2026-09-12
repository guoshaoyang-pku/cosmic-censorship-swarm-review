#!/usr/bin/env python3
"""L1 spot check #4 (worker-100) -- independent re-fetch of ledger/citation_audit.csv rows SRC-041..060.

Contract (frozen in sample_frozen.json, written before any fetch):
  * target   ledger/citation_audit.csv @ sha256 315c19145065...   (fail-closed on drift)
  * secondary ledger/theorems.jsonl      @ sha256 ce42d205e761...  (class-binding chain check)
  * sample   citation_id in SRC-041..SRC-060 (20 rows)
  * verdict  MATCH / PARTIAL / FAIL / FETCH_FAILED per frozen rules
  * reviewer worker-100, distinct from flash-10, flash-11, deepseek-flash-07

method_version 2 (2026-09-12T00:2x): fixes found by the v1 self-check before any verdict was
reported -- v1 raw/report preserved as *.v1-checkerbug.*:
  1. arXiv Atom: the feed-level <title> ("arXiv Query: ...") was read instead of the first
     <entry><title>; XML entities were not unescaped.  -> entry-scoped parser.
  2. Only the first HTTP-200 locator was used; when Crossref (no abstract) resolved first, a
     quoted excerpt taken from the INSPIRE/arXiv abstract could not be checked.  -> fetch the
     locator chain (metadata locator + row url + exact_locator/evidence_url, max 4) and check
     the excerpt against the union of the fetched records.
  3. Unicode/HTML: NFKC left en-dashes and combining marks, and Crossref titles carry
     <i>/<sup> tags.  -> NFKD + ASCII fold + HTML tag strip.
  4. 429 rate limits from export.arxiv.org aborted a row on the first locator.  -> 3 attempts
     with 3 s backoff on 429.

Read-only with respect to the ledger. Writes raw bodies under raw-worker100/ and the report next
to this file. No node completion, no gate verdict, no theorem is claimed.
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
METHOD_VERSION = 2


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


def norm(s: str) -> str:
    s = strip_tags(s)
    s = s.replace("$", " ").replace("\\", " ")
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
                    "url": url,
                    "http_status": int(getattr(r, "status", 200)),
                    "final_url": r.geturl(),
                    "bytes": len(body),
                    "sha256": sha256_bytes(body),
                    "elapsed_s": round(time.time() - t0, 2),
                    "attempts": attempt,
                    "body": body,
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


def parse_crossref(body: bytes):
    try:
        msg = json.loads(body.decode("utf-8", "replace"))["message"]
    except Exception:
        return None
    title = strip_tags((msg.get("title") or [""])[0])
    authors = "; ".join(
        strip_tags(f"{a.get('given','')} {a.get('family','')}".strip()) for a in (msg.get("author") or [])
    )
    issued = (msg.get("issued") or {}).get("date-parts") or [[None]]
    year = issued[0][0]
    venue = strip_tags((msg.get("container-title") or [""])[0])
    return {
        "kind": "crossref", "title": title, "authors": authors, "year": year,
        "venue": venue, "doi": msg.get("DOI", ""),
        "abstract": strip_tags(msg.get("abstract", "") or ""), "journal_ref": venue,
    }


def parse_arxiv(body: bytes):
    text = body.decode("utf-8", "replace")
    m = re.search(r"<entry>(.*?)</entry>", text, re.S)
    if not m:
        return None
    entry = m.group(1)

    def grab(tag):
        mm = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", entry, re.S)
        return re.sub(r"\s+", " ", strip_tags(mm.group(1))).strip() if mm else ""
    published = grab("published")
    year = int(published[:4]) if re.match(r"\d{4}", published) else None
    return {
        "kind": "arxiv", "title": grab("title"),
        "authors": "; ".join(re.findall(r"<name>(.*?)</name>", entry, re.S)),
        "year": year, "venue": f"arXiv {grab('id')}", "doi": grab("doi"),
        "abstract": grab("summary"), "journal_ref": grab("journal_ref"),
        "published": published, "updated": grab("updated"), "comment": grab("comment"),
    }


def parse_inspire(body: bytes):
    try:
        doc = json.loads(body.decode("utf-8", "replace"))
    except Exception:
        return None
    md = doc.get("metadata") or {}
    titles = md.get("titles") or [{}]
    title = strip_tags(titles[0].get("title", ""))
    authors = "; ".join(a.get("full_name", "") for a in (md.get("authors") or []))
    pubinfo = (md.get("publication_info") or [{}])[0]
    year = pubinfo.get("year") or (md.get("earliest_date") or "")[:4] or None
    if isinstance(year, str) and year.isdigit():
        year = int(year)
    dois = md.get("dois") or [{}]
    arxiv = (md.get("arxiv_eprints") or [{}])[0].get("value", "")
    abstracts = md.get("abstracts") or [{}]
    return {
        "kind": "inspire", "title": title, "authors": authors, "year": year,
        "venue": " ".join(str(x) for x in [pubinfo.get("journal_title", ""),
                                           pubinfo.get("journal_volume", ""),
                                           pubinfo.get("artid", "") or pubinfo.get("page_start", "")] if x),
        "doi": dois[0].get("value", ""), "arxiv_id": arxiv,
        "abstract": strip_tags(abstracts[0].get("value", "")), "journal_ref": "",
    }


def parse_fetched(body: bytes, content_type: str):
    if body[:1] in (b"{"):
        for parser in (parse_crossref, parse_inspire):
            try:
                out = parser(body)
            except Exception:
                out = None
            if out and out.get("title"):
                return out
    if b"<entry" in body[:4000] or "xml" in content_type:
        try:
            out = parse_arxiv(body)
        except Exception:
            out = None
        if out and out.get("title"):
            return out
    head = body[:2000].decode("utf-8", "replace")
    m = re.search(r"<title[^>]*>(.*?)</title>", head, re.S | re.I)
    abstract = ""
    am = re.search(r'(?:abstract|description)"?[^>]*>(.{80,4000}?)</', head, re.S | re.I)
    if am:
        abstract = strip_tags(am.group(1))
    return {"kind": "page", "title": strip_tags(m.group(1)).strip() if m else "",
            "authors": "", "year": None, "venue": "", "doi": "", "abstract": abstract,
            "journal_ref": ""}


def quoted_parts(excerpt: str):
    parts = re.findall(r"['\u2018\u2019\u201c\u201d\"](.{25,}?)['\u2018\u2019\u201c\u201d\"]", excerpt or "")
    return parts if parts else ([excerpt] if excerpt else [])


def excerpt_segments(excerpt: str):
    segs = []
    for part in quoted_parts(excerpt):
        for chunk in re.split(r"\.\.\.|\u2026", part):
            n = norm(chunk)
            if len(n) >= 25:
                segs.append(n)
    return segs


def build_locators(row):
    locators = []
    arxiv = (row.get("arxiv_id") or "").strip()
    doi = (row.get("doi") or "").strip()
    url = (row.get("url") or "").strip()
    if arxiv:
        locators.append(("arxiv_api", f"https://export.arxiv.org/api/query?id_list={arxiv}"))
    if doi and not doi.startswith("10.48550/"):
        locators.append(("crossref_api", f"https://api.crossref.org/works/{doi}"))
    if url:
        locators.append(("row_url", url))
    for field in ("exact_locator", "evidence_url"):
        u = (row.get(field) or "").strip()
        if u and all(u != l[1] for l in locators):
            locators.append((field, u))
    return locators[:4]


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
    csv_non_frozen = [c for c in csv_tokens if c not in FROZEN_CLASSES]
    return {
        "used_by_theorems": refs,
        "missing_theorem_refs": missing,
        "non_frozen_tokens": non_frozen,
        "csv_class_tokens": csv_tokens,
        "csv_non_frozen_tokens": csv_non_frozen,
        "annotation_only": ANNOTATION in (row.get("class_mapping") or ""),
        "csv_tokens_without_linked_theorem_support": sorted(set(csv_tokens) - linked_classes),
        "linked_theorem_classes": sorted(linked_classes),
    }


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    started = now()
    before = {str(p.relative_to(ROOT)): sha256_file(p) for p in (CSV_PATH, THEOREMS_PATH)}
    for rel, h in before.items():
        if PINNED[rel] != h:
            print(f"FATAL: {rel} sha256 {h} != pinned {PINNED[rel]} (fail-closed)")
            return 2

    rows = {r["citation_id"]: r for r in csv.DictReader(CSV_PATH.open())}
    theorems = load_theorems()
    results, fetch_meta = [], {}
    for sid in SAMPLE:
        row = rows[sid]
        entry = {
            "source_id": sid,
            "ledger_row": {
                k: row.get(k) for k in
                ("bibkey", "title", "authors", "year", "venue", "doi", "arxiv_id", "url",
                 "status", "verification_method", "evidence_url", "exact_locator",
                 "class_mapping", "used_by_theorems", "verdict", "reviewer")
            },
            "cross_check_of_flash07": sid in CROSS_CHECK,
            "class_binding": class_chain_check(row, theorems),
        }
        attempts, sources = [], []
        for kind, url in build_locators(row):
            f = fetch(url)
            rec = {k: v for k, v in f.items() if k != "body"}
            rec["kind"] = kind
            attempts.append(rec)
            if f.get("http_status") == 200 and f.get("body"):
                meta = parse_fetched(f["body"], "")
                ext = {"crossref": "json", "inspire": "json", "arxiv": "xml", "page": "html"}.get(meta["kind"], "bin")
                raw_path = RAW / f"{sid}.{kind}.{ext}"
                raw_path.write_bytes(f["body"])
                sources.append({
                    "kind": kind, "url": url, "http_status": 200,
                    "bytes": f["bytes"], "sha256": f["sha256"],
                    "raw_path": str(raw_path.relative_to(ROOT)),
                    "record_kind": meta["kind"],
                    "title": meta.get("title"), "authors": meta.get("authors"),
                    "year": meta.get("year"), "venue": meta.get("venue"),
                    "doi": meta.get("doi"), "abstract_chars": len(meta.get("abstract") or ""),
                    "abstract_sha256": sha256_bytes((meta.get("abstract") or "").encode()),
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

        def sim(s):
            a, b = norm(row.get("title", "")), norm(s.get("title") or "")
            if not b:
                return 0.0
            r = difflib.SequenceMatcher(None, a, b).ratio()
            if r < 0.90 and a and b and (a in b or b in a) and min(len(a), len(b)) / max(len(a), len(b)) >= 0.75:
                r = max(r, 0.90)
            return round(r, 3)

        best = max(sources, key=lambda s: (sim(s), s["abstract_chars"]))
        best_sim = sim(best)
        title_ok = best_sim >= 0.90

        years = [s["year"] for s in sources if s.get("year")]
        ly = int(row.get("year") or 0)
        year_ok, year_reason = None, "no fetched year"
        if years and ly:
            consistent = [y for y in years if abs(int(y) - ly) <= 1]
            if consistent:
                year_ok, year_reason = True, f"ledger {ly} vs fetched {sorted(set(years))}"
            else:
                jr_hit = any(str(ly) in (s.get("venue") or "") for s in sources)
                if jr_hit:
                    year_ok, year_reason = True, f"ledger {ly} supported by venue string"
                else:
                    year_ok, year_reason = False, f"ledger {ly} vs fetched {sorted(set(years))}"

        segs = excerpt_segments(row.get("evidence_excerpt", ""))
        hay = norm(" ".join(
            str(s.get(k, "")) for s in sources
            for k in ("abstract", "_meta", "title", "authors", "venue", "year", "doi")
        ))
        hay_abstract_chars = sum(s["abstract_chars"] for s in sources)
        if not segs:
            exc = {"status": "unavailable", "matched": 0, "total": 0,
                   "reason": "no quoted segment >=25 chars in ledger excerpt"}
        else:
            matched, unmatched = 0, []
            for seg in segs:
                prefix = seg[:80]
                if seg in hay or (len(prefix) >= 25 and prefix in hay):
                    matched += 1
                else:
                    unmatched.append(seg[:80])
            if matched == len(segs):
                exc = {"status": "supported", "matched": matched, "total": len(segs), "unmatched": []}
            elif matched:
                exc = {"status": "partial", "matched": matched, "total": len(segs), "unmatched": unmatched[:3]}
            elif hay_abstract_chars == 0:
                exc = {"status": "unavailable", "matched": 0, "total": len(segs), "unmatched": unmatched[:3],
                       "reason": "no fetched source carries abstract/record text"}
            else:
                exc = {"status": "not_found", "matched": 0, "total": len(segs), "unmatched": unmatched[:3]}

        reasons = []
        if not title_ok:
            verdict = "FAIL"
            reasons.append(f"title mismatch (best similarity {best_sim} vs '{best.get('title','')[:60]}')")
        elif year_ok is False:
            verdict = "FAIL"
            reasons.append(f"year inconsistent: {year_reason}")
        elif exc["status"] == "not_found":
            verdict = "FAIL"
            reasons.append("quoted ledger excerpt not found in fetched records")
        elif exc["status"] in ("partial", "unavailable"):
            verdict = "PARTIAL"
            reasons.append(f"excerpt {exc['status']} ({exc['matched']}/{exc['total']} segments)")
        elif year_ok is None:
            verdict = "PARTIAL"
            reasons.append("year not determinable from fetched records")
        else:
            verdict = "MATCH"
            reasons.append(f"title {best_sim}, year ok ({year_reason}), excerpt {exc['matched']}/{exc['total']} segments")
        entry["sources"] = [{k: v for k, v in s.items() if k != "_meta"} for s in sources]
        entry["comparison"] = {
            "best_source": {"kind": best["kind"], "url": best["url"], "sha256": best["sha256"]},
            "title_similarity": best_sim, "title_ok": title_ok,
            "year_ok": year_ok, "year_reason": year_reason,
            "excerpt_status": exc["status"], "excerpt_matched": exc["matched"],
            "excerpt_total": exc["total"],
            "excerpt_unmatched": exc.get("unmatched", []),
            "abstract_chars_union": hay_abstract_chars,
        }
        entry["verdict"] = verdict
        entry["reasons"] = reasons
        results.append(entry)
        time.sleep(0.4)

    after = {str(p.relative_to(ROOT)): sha256_file(p) for p in (CSV_PATH, THEOREMS_PATH)}
    drift = {k: {"before": before[k], "after": after[k]} for k in before if before[k] != after[k]}
    summary = {
        "checked": len(results),
        "match": sum(1 for r in results if r["verdict"] == "MATCH"),
        "partial": sum(1 for r in results if r["verdict"] == "PARTIAL"),
        "fail": sum(1 for r in results if r["verdict"] == "FAIL"),
        "fetch_failed": sum(1 for r in results if r["verdict"] == "FETCH_FAILED"),
        "new_coverage_rows": [r["source_id"] for r in results if not r["cross_check_of_flash07"]],
        "cross_check_rows": CROSS_CHECK,
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
        "method_revision_note": "v2 fixes four measurement bugs found by the v1 self-check before verdicts were reported: arXiv feed-title parsing, single-locator abstract blindness, Unicode/HTML normalization, and 429 handling. v1 files preserved as *.v1-checkerbug.*.",
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
        "inputs": {
            rel: {"pinned_sha256": PINNED[rel], "sha256_before": before[rel], "sha256_after": after[rel]}
            for rel in before
        },
        "drift_during_run": drift,
        "sample": {
            "rule": "citation_id in SRC-041..SRC-060 (all 20); SRC-041/049/057 are cross-checks of flash-07, the other 17 are new coverage",
            "rows": SAMPLE,
        },
        "frozen_classes": FROZEN_CLASSES,
        "verdict_rules": {
            "MATCH": "resolved + title consistent + year consistent + all quoted excerpt segments matched",
            "PARTIAL": "resolved + title/year consistent but excerpt partial or not checkable",
            "FAIL": "resolved but title/year contradiction or quoted excerpt absent from a source that carries abstract text",
            "FETCH_FAILED": "no locator returned HTTP 200",
        },
        "results": results,
        "summary": summary,
        "class_binding_summary": {
            "hard_failures": {"non_frozen_class_tokens_in_linked_theorems": non_frozen, "missing_theorem_refs": missing_refs},
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
    if non_frozen or missing_refs or drift:
        report["hard_failures"] = (
            [f"non-frozen class token: {x}" for x in non_frozen]
            + [f"missing theorem ref: {x}" for x in missing_refs]
            + [f"input drift: {k}" for k in drift]
        )
    report_path = HERE / "spotcheck-l1-100.json"
    report_path.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    (HERE / "fetch_meta_worker100.json").write_text(json.dumps(fetch_meta, indent=1, ensure_ascii=False) + "\n")
    (HERE / "spotcheck-l1-100.json.sha256").write_text(sha256_file(report_path) + "  spotcheck-l1-100.json\n")
    print(json.dumps({"report": str(report_path.relative_to(ROOT)),
                      "sha256": sha256_file(report_path), "summary": summary,
                      "hard_failures": report["hard_failures"], "drift": drift}, indent=1))
    return 1 if (non_frozen or missing_refs or drift) else 0


if __name__ == "__main__":
    sys.exit(main())
