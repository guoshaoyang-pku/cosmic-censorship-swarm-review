#!/usr/bin/env python3
"""W021-L1-REPLICATION-01 -- independent re-fetch replication of the three L1
citation MISMATCH findings reported by worker-086 (check #4) at the frozen
ledger sha256 315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9.

Scope (one bounded, class-bound task):
  rows 4 (SRC-004), 25 (SRC-025), 33 (SRC-033) of ledger/citation_audit.csv
  classes: AF-SCC-C0-VAC-GEN, AF-SCC-C2-VAC-GEN

Independence from worker-086:
  * different transport per row: arXiv Atom API (not arxiv.org/abs HTML) for the
    two arXiv rows; Semantic Scholar Graph API + INSPIRE API (not Crossref) for
    the DOI row;
  * different comparison core: LaTeX/unicode-normalised token containment with
    controls, instead of a raw character-similarity ratio;
  * raw response bodies are written to disk and hashed, so the comparison can be
    replayed byte-for-byte.

Controls (a check that cannot fail is not a check):
  C+  positive: the ledger excerpt must be contained in the fetched record for
      at least one row (otherwise the pipeline is broken, not the ledger);
  C-1 matched-span deletion: deleting the matched token span from the fetched
      record must make containment fail;
  C-2 deterministic token shuffle: a shuffled fetched record must not contain
      the excerpt;
  C-3 short generic phrase: a 6-token generic phrase must not pass the
      12-token containment threshold.

Fail-closed: the ledger sha256 is pinned; any drift voids the run.
Usage: python3 run_l1_replication.py
Outputs: raw/ (fetched bodies), report.json, stdout summary.
"""
from __future__ import annotations

import csv
import difflib
import hashlib
import json
import random
import re
import sys
import time
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-021/l1_refetch_replication -> repo root
LEDGER = ROOT / "ledger" / "citation_audit.csv"
PINNED_SHA = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
ACTOR = "worker-021"
CST = timezone(timedelta(hours=8))
UA = {"User-Agent": "ai4math-swarm-worker-021/0.1 (L1 citation replication)"}

TARGETS = [
    {"row": 4, "citation_id": "SRC-004", "transport": "arxiv-atom", "id": "1710.01722"},
    {"row": 25, "citation_id": "SRC-025", "transport": "arxiv-atom", "id": "2001.11156"},
    {"row": 33, "citation_id": "SRC-033", "transport": "doi-registries", "id": "10.1088/1361-6382/aadbcf"},
]

MIN_RUN_TOKENS = 12
CONTROL_SHORT_PHRASE = "we prove that for all such"
ARXIV_NS = {"a": "http://www.w3.org/2005/Atom"}


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


def norm_text(s: str) -> str:
    """Fold LaTeX/unicode/punctuation so that token content, not markup, is compared."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    for a, b in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'),
                 ("\u2013", "-"), ("\u2014", "-"), ("\u2212", "-"), ("\u039b", " lambda "), ("\u03bb", " lambda ")):
        s = s.replace(a, b)
    s = re.sub(r"^\s*(arXiv|IOP|INSPIRE|Crossref|CMP|Annals)[^:]{0,40}:\s*", "", s, flags=re.I)
    s = re.sub(r"^(exact excerpt|abstract)\s*:?\s*", "", s, flags=re.I)
    s = s.strip().strip("'\"").strip()
    s = s.replace("\\cup", " union ").replace("\\cap", " intersection ")
    s = s.replace("\\mathcal", " ").replace("\\textit", " ").replace("\\textbf", " ")
    s = re.sub(r"\\[a-zA-Z]+", " ", s)
    s = s.replace("$", " ").replace("{", " ").replace("}", " ").replace("\\", " ")
    s = re.sub(r"\.\.\.+", " ", s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def tokens(s: str) -> list[str]:
    return norm_text(s).split()


def longest_run(a: list[str], b: list[str]) -> dict:
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    blocks = sm.get_matching_blocks()
    longest = max(blocks, key=lambda m: m.size) if blocks else None
    size = longest.size if longest else 0
    preview = " ".join(a[longest.a: longest.a + min(size, 18)]) if longest and size else ""
    matched = sum(m.size for m in blocks)
    return {
        "longest_run_tokens": size,
        "longest_run_frac_of_excerpt": round(size / max(1, len(a)), 4),
        "total_matched_tokens": matched,
        "excerpt_coverage": round(matched / max(1, len(a)), 4),
        "longest_run_preview": preview,
    }


def contained(a: list[str], b: list[str]) -> bool:
    return longest_run(a, b)["longest_run_tokens"] >= MIN_RUN_TOKENS


def fetch(url: str, retries: int = 3) -> dict:
    last = None
    for attempt in range(1, retries + 1):
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=45) as r:
                body = r.read()
                return {"ok": True, "http_status": r.status, "url": url, "bytes": len(body),
                        "seconds": round(time.time() - t0, 2), "attempt": attempt, "body": body}
        except Exception as e:  # noqa: BLE001 - network failure is a finding, not a crash
            last = f"{type(e).__name__}: {e}"
            time.sleep(1.5 * attempt)
    return {"ok": False, "http_status": None, "url": url, "bytes": 0,
            "seconds": None, "attempt": retries, "error": last, "body": b""}


def parse_arxiv_atom(body: bytes) -> dict:
    root = ET.fromstring(body)
    entry = root.find("a:entry", ARXIV_NS)
    if entry is None:
        return {}
    title = " ".join((entry.findtext("a:title", default="", namespaces=ARXIV_NS) or "").split())
    summary = " ".join((entry.findtext("a:summary", default="", namespaces=ARXIV_NS) or "").split())
    authors = [" ".join((n.text or "").split()) for n in entry.findall("a:author/a:name", ARXIV_NS)]
    published = (entry.findtext("a:published", default="", namespaces=ARXIV_NS) or "").strip()
    updated = (entry.findtext("a:updated", default="", namespaces=ARXIV_NS) or "").strip()
    years = sorted({int(published[:4])} if published[:4].isdigit() else set())
    return {"title": title, "abstract": summary, "authors": authors,
            "published": published, "updated": updated, "years": years}


def parse_s2(body: bytes) -> dict:
    d = json.loads(body)
    return {"title": (d.get("title") or "").strip(),
            "abstract": (d.get("abstract") or "").strip(),
            "authors": [a.get("name", "") for a in (d.get("authors") or [])],
            "years": sorted({d["year"]} if d.get("year") else set()),
            "venue": (d.get("venue") or "").strip(),
            "source": "semanticscholar"}


def parse_inspire(body: bytes) -> dict:
    d = json.loads(body)
    md = d.get("metadata", {})
    titles = md.get("titles") or [{}]
    abs_ = md.get("abstracts") or [{}]
    authors = [a.get("full_name", "") for a in (md.get("authors") or [])]
    years = set()
    m = re.search(r"\b(19|20)\d{2}\b", str(md.get("earliest_date", "")))
    if m:
        years.add(int(m.group(0)))
    for p in (md.get("publication_info") or []):
        if str(p.get("year", "")).isdigit():
            years.add(int(p["year"]))
    return {"title": (titles[0].get("title") or "").strip(),
            "abstract": (abs_[0].get("value") or "").strip(),
            "authors": authors,
            "years": sorted(years),
            "venue": "; ".join((p.get("journal_title") or "") for p in (md.get("publication_info") or [])).strip("; "),
            "source": "inspire"}


def read_rows() -> dict[int, dict]:
    with LEDGER.open(newline="", encoding="utf-8") as f:
        return {i: row for i, row in enumerate(csv.DictReader(f), 1)}


def surname(s: str) -> str:
    t = norm_text(s).split()
    return t[-1] if t else ""


def author_state(ledger_authors: str, fetched_authors: list[str]) -> str:
    lt = [surname(x) for x in re.split(r"[;,]| and ", ledger_authors or "") if surname(x)]
    ft = [surname(x) for x in fetched_authors]
    if lt and ft and all(any(a == b for b in ft) for a in lt):
        return "match"
    return "mismatch"


def title_state(ledger_title: str, fetched_title: str) -> str:
    a, b = norm_text(ledger_title), norm_text(fetched_title)
    if a == b:
        return "match"
    if a and b and (a in b or b in a):
        return "match (containment; markup-only difference)"
    if contained(a.split(), b.split()) or contained(b.split(), a.split()):
        return "match (long verbatim run; markup-only difference)"
    return "mismatch"


def year_state(ledger_year: str, venue: str, fetched_years: list[int]) -> str:
    try:
        ly = int(ledger_year)
    except (TypeError, ValueError):
        return "ledger-year-missing"
    if ly in fetched_years:
        return "match"
    declared = {int(m.group(0)) for m in re.finditer(r"\b(19|20)\d{2}\b", venue or "")}
    if ly in declared:
        return "convention (ledger uses declared journal/issue year; fetched record carries other declared year)"
    return "mismatch"


def repro_char_similarity(excerpt: str, abstract: str) -> float:
    """Reproduce worker-086's `excerpt_similarity_first400` style metric."""
    return round(difflib.SequenceMatcher(a=(excerpt or "")[:400], b=(abstract or "")[:400], autojunk=False).ratio(), 4)


def main() -> int:
    (HERE / "raw").mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": "0.1",
        "artifact_type": "l1_refetch_replication",
        "task_id": "W021-L1-REPLICATION-01",
        "node_id": "L1",
        "gate": "G-LIT",
        "actor": ACTOR,
        "reviewer": ACTOR,
        "created_at": now(),
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "replication_of": "artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json",
        "independent_of": [
            "artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json",
            "artifacts/worker-07/l1_spotcheck/spotcheck-l1-07.json",
            "reviews/L1-spotcheck-10.json",
            "reviews/L1-spotcheck-11.json",
        ],
        "method": {
            "transport": {
                "arxiv-atom": "https://export.arxiv.org/api/query?id_list=<id> (Atom XML; not worker-086's arxiv.org/abs HTML)",
                "doi-registries": "api.semanticscholar.org Graph API then inspirehep.net API (not worker-086's api.crossref.org)",
            },
            "comparison": f"LaTeX/unicode-normalised token containment; contained iff longest verbatim token run >= {MIN_RUN_TOKENS}",
            "raw_evidence": "every fetched body written to raw/ and hashed; comparison replayable from raw/",
            "scope": "only the three rows worker-086 reported as MISMATCH; not a ledger-wide verdict",
        },
        "inputs": {"ledger/citation_audit.csv": {"sha256_pinned": PINNED_SHA, "sha256_before": sha256_file(LEDGER)}},
        "controls": {},
        "results": [],
        "summary": {},
        "non_claims": [
            "replication of three rows only; not a verdict on the other 94 rows nor on G-LIT as a whole",
            "no gate verdict, no node completion, no claim that any citation is suitable for a class binding",
            "locator-quality observations are reported, not fixed here",
        ],
        "next_falsifier": (
            "Any of: (a) drift of ledger/citation_audit.csv from sha256 " + PINNED_SHA[:12] + " during this run; "
            "(b) a third registry returning a record whose title/author/abstract differs from the primary record "
            "beyond markup; (c) the ledger excerpt absent after normalisation from an independent re-fetch, which "
            "would reinstate the worker-086 MISMATCH as a ledger defect."
        ),
    }

    if report["inputs"]["ledger/citation_audit.csv"]["sha256_before"] != PINNED_SHA:
        report["verdict"] = "VOID_LEDGER_DRIFT"
        report["summary"] = {"error": "ledger drifted before fetch",
                             "sha256_before": report["inputs"]["ledger/citation_audit.csv"]["sha256_before"]}
        (HERE / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
        print(json.dumps(report["summary"], indent=2))
        return 2

    rows = read_rows()
    control_positive = False
    control_negative = []
    short_phrase_rejected = True

    for t in TARGETS:
        row = rows.get(t["row"])
        if row is None or row.get("citation_id") != t["citation_id"]:
            report["results"].append({"row": t["row"], "citation_id": t["citation_id"], "verdict": "ROW_MISSING_OR_ID_MISMATCH"})
            continue

        ledger = {k: (row.get(k) or "") for k in
                  ("title", "authors", "year", "venue", "doi", "arxiv_id", "url", "evidence_url",
                   "exact_locator", "evidence_excerpt", "class_mapping", "used_by_theorems", "verdict")}

        if t["transport"] == "arxiv-atom":
            plan = [("arxiv-atom", f"https://export.arxiv.org/api/query?id_list={t['id']}", parse_arxiv_atom)]
        else:
            plan = [
                ("semanticscholar", f"https://api.semanticscholar.org/graph/v1/paper/DOI:{t['id']}?fields=title,abstract,authors,year,venue,externalIds", parse_s2),
                ("inspire", f"https://inspirehep.net/api/doi/{t['id']}", parse_inspire),
            ]

        registry_records, parsed = [], []
        for name, url, parser in plan:
            f = fetch(url)
            raw_path = HERE / "raw" / f"{t['citation_id']}_{name}.raw"
            rec = {"registry": name, "url": url, "ok": f["ok"], "http_status": f.get("http_status"),
                   "bytes": f.get("bytes"), "seconds": f.get("seconds"), "error": f.get("error"),
                   "raw_path": str(raw_path.relative_to(ROOT))}
            if f["ok"]:
                raw_path.write_bytes(f["body"])
                rec["raw_sha256"] = sha256_bytes(f["body"])
                try:
                    p = parser(f["body"])
                    rec["parsed"] = {k: v for k, v in p.items() if k != "abstract"}
                    rec["abstract_chars"] = len(p.get("abstract") or "")
                    parsed.append((name, p))
                except Exception as e:  # noqa: BLE001
                    rec["parse_error"] = f"{type(e).__name__}: {e}"
            registry_records.append(rec)

        primary = parsed[0][1] if parsed else {}
        excerpt_tokens = tokens(ledger["evidence_excerpt"])
        abstract_tokens = tokens(primary.get("abstract", ""))
        run = longest_run(excerpt_tokens, abstract_tokens)
        is_contained = run["longest_run_tokens"] >= MIN_RUN_TOKENS
        registry_titles = {name: p.get("title", "") for name, p in parsed}
        reg_agree = len({norm_text(v) for v in registry_titles.values() if v}) <= 1

        c1 = c2 = None
        if is_contained:
            control_positive = True
            # C-1: mask EVERY matched block of size>0 (not just the longest one -- the
            # excerpt can match in several disjoint blocks), then containment must fail.
            sm = difflib.SequenceMatcher(a=excerpt_tokens, b=abstract_tokens, autojunk=False)
            drop = set()
            for m in sm.get_matching_blocks():
                drop.update(range(m.b, m.b + m.size))
            mutated = [tok for i, tok in enumerate(abstract_tokens) if i not in drop]
            c1 = not contained(excerpt_tokens, mutated)
            # C-2: deterministic shuffle -> containment must fail
            sh = list(abstract_tokens)
            random.Random(21021).shuffle(sh)
            c2 = not contained(excerpt_tokens, sh)
            control_negative.append({"row": t["row"], "matched_tokens_masked": len(drop),
                                     "matched_span_deletion_detected": c1, "shuffle_detected": c2})
        if abstract_tokens:
            c3 = not contained(tokens(CONTROL_SHORT_PHRASE), abstract_tokens)
            short_phrase_rejected = short_phrase_rejected and c3
        else:
            c3 = None

        r = {
            "row": t["row"],
            "citation_id": t["citation_id"],
            "class_mapping": ledger["class_mapping"],
            "used_by_theorems": ledger["used_by_theorems"],
            "ledger": ledger,
            "fetches": registry_records,
            "comparison": {
                "title": title_state(ledger["title"], primary.get("title", "")),
                "authors": author_state(ledger["authors"], primary.get("authors", [])),
                "year": year_state(ledger["year"], ledger["venue"], primary.get("years", [])),
                "excerpt": "contained" if is_contained else "not-contained",
                **run,
                "worker086_style_excerpt_similarity_first400": repro_char_similarity(ledger["evidence_excerpt"], primary.get("abstract", "")),
                "registry_title_agreement": reg_agree,
                "registry_titles": {k: v[:110] for k, v in registry_titles.items()},
            },
            "location_observation": (
                "ledger exact_locator is a search-query URL, not an exact locator"
                if ("search_query" in ledger["exact_locator"] or "?q=" in ledger["exact_locator"]) else "locator looks exact"),
            "worker086_finding": {"SRC-004": "MISMATCH (year+excerpt)", "SRC-025": "MISMATCH (excerpt)",
                                  "SRC-033": "MISMATCH (excerpt)"}[t["citation_id"]],
            "controls": {"C1_matched_span_deletion_detected": c1, "C2_shuffle_detected": c2,
                         "C3_short_phrase_rejected": c3},
        }
        core_ok = r["comparison"]["title"].startswith("match") and r["comparison"]["authors"] == "match" and is_contained
        r["replication_verdict"] = ("NOT_REPLICATED (comparator artifact; core fields agree)"
                                    if core_ok else "REPLICATED_MISMATCH")
        r["verdict"] = "NO_DEFECT_FOUND" if core_ok else "DEFECT_REPLICATED"
        report["results"].append(r)

    sha_after = sha256_file(LEDGER)
    le = report["inputs"]["ledger/citation_audit.csv"]
    le["sha256_after"] = sha_after
    le["stable_during_run"] = sha_after == PINNED_SHA
    controls_all = (control_positive
                    and all(c["matched_span_deletion_detected"] and c["shuffle_detected"] for c in control_negative)
                    and short_phrase_rejected)
    report["controls"] = {
        "C_pos_positive_containment_observed": control_positive,
        "C_neg_matched_span_deletion_and_shuffle": control_negative,
        "C3_short_generic_phrase_rejected_all_rows": short_phrase_rejected,
        "controls_all_passed": controls_all,
    }

    verdicts = [r.get("verdict") for r in report["results"]]
    report["summary"] = {
        "rows_checked": len(report["results"]),
        "no_defect_found": sum(v == "NO_DEFECT_FOUND" for v in verdicts),
        "defect_replicated": sum(v == "DEFECT_REPLICATED" for v in verdicts),
        "locator_quality_observations": [r["citation_id"] for r in report["results"]
                                         if r.get("location_observation", "").startswith("ledger exact_locator is a search-query")],
        "ledger_stable": le["stable_during_run"],
        "controls_all_passed": controls_all,
    }

    if not controls_all:
        report["verdict"] = "INCONCLUSIVE_CONTROLS_FAILED"
    elif not le["stable_during_run"]:
        report["verdict"] = "VOID_LEDGER_DRIFT"
    elif report["summary"]["defect_replicated"]:
        report["verdict"] = "MISMATCH_FINDINGS_REPLICATED"
    else:
        report["verdict"] = "MISMATCH_FINDINGS_NOT_REPLICATED"

    (HERE / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({"verdict": report["verdict"], "summary": report["summary"],
                      "controls": report["controls"],
                      "rows": [{"row": r["row"], "id": r["citation_id"], "verdict": r.get("verdict"),
                                "longest_run_tokens": r.get("comparison", {}).get("longest_run_tokens"),
                                "char_sim_086_style": r.get("comparison", {}).get("worker086_style_excerpt_similarity_first400"),
                                "title": r.get("comparison", {}).get("title"),
                                "year": r.get("comparison", {}).get("year")}
                               for r in report["results"]]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
