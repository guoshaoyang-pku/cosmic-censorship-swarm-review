#!/usr/bin/env python3
"""W026-L1-SPOTCHECK-05 post-fetch analyzer.

No network. Re-derives both the literal pre-registered metric and the disclosed
offset-aware amendment from the already-hashed raw bodies, then writes the final
spotcheck-l1-026.json. The literal run output is preserved at
spotcheck-l1-026.literal-preregistered.json.
"""
from __future__ import annotations

import csv
import difflib
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
LEDGER = ROOT / "ledger" / "citation_audit.csv"
PRE = HERE / "preregistration.json"
LITERAL = HERE / "spotcheck-l1-026.literal-preregistered.json"
OUT = HERE / "spotcheck-l1-026.json"
PIN = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
CST = timezone(timedelta(hours=8))


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = s.lower()
    s = re.sub(r"^(wiley|ams|aps|arxiv|springer|inspire|crossref)\s+(abstract|excerpt)\s*:?\s*", "", s)
    s = re.sub(r"^[a-z0-9 .\-()/]{0,40}(abstract|excerpt)\s*:?\s*", "", s)
    s = re.sub(r"\$[^$]*\$", " ", s)
    s = re.sub(r"\\[a-z]+", " ", s)
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    s = s.strip(" '\"\u2026.")
    return re.sub(r"\s+", " ", s).strip()


def best_window(a: str, b: str, w: int = 200, step: int = 10) -> float:
    if not a or not b:
        return 0.0
    if len(b) <= w:
        return round(difflib.SequenceMatcher(None, a[:w], b).ratio(), 4)
    best = 0.0
    for i in range(0, len(b) - w + 1, step):
        r = difflib.SequenceMatcher(None, a[:w], b[i:i + w]).ratio()
        if r > best:
            best = r
    # ensure the tail is covered
    r = difflib.SequenceMatcher(None, a[:w], b[-w:]).ratio()
    return round(max(best, r), 4)


def main() -> int:
    pre = json.loads(PRE.read_text())
    lit = json.loads(LITERAL.read_text())
    rows = {i: r for i, r in enumerate(csv.DictReader(LEDGER.open()), 1)}
    ledger_after = sha(LEDGER.read_bytes())

    results, raw_integrity = [], []
    for e in lit["results"]:
        rn, cid = e["row"], e["citation_id"]
        r = rows[rn]
        f = e.get("fetched") or {}
        raw_path = e.get("raw_path")
        rb = (ROOT / raw_path).read_bytes()
        measured = sha(rb)
        raw_integrity.append({
            "row": rn, "citation_id": cid, "raw_path": raw_path,
            "sha256_measured_now": measured, "sha256_recorded_at_fetch": e.get("raw_sha256"),
            "match": measured == e.get("raw_sha256"),
        })
        lex, fab = norm(r["evidence_excerpt"]), norm(f.get("abstract", ""))
        first400 = round(difflib.SequenceMatcher(None, lex[:400], fab[:400]).ratio(), 4) if fab else None
        bw = best_window(lex, fab) if fab else None
        contained = bool(lex) and lex[:200] in fab
        ly = int(r["year"]) if r["year"].isdigit() else None
        fy = f.get("year")
        yd = (fy - ly) if (fy is not None and ly is not None) else None
        first_last = (r["authors"] or "").split(";")[0].strip().split()[-1].lower()
        fam = bool(first_last) and any(first_last in a.lower() for a in (f.get("authors") or []))
        title_sim = round(difflib.SequenceMatcher(None, norm(r["title"]), norm(f.get("title", ""))).ratio(), 4)
        locator_search = ("search_query=" in (r["exact_locator"] or "")) or ("?q=" in (r["exact_locator"] or ""))

        excerpt_testable = bool(fab)
        excerpt_supported = bool(excerpt_testable and (contained or (bw or 0) >= 0.85))
        base_ok = title_sim >= 0.95 and fam and (yd is not None and abs(yd) <= 1)

        # amended verdict (disclosed post-fetch rule)
        if e["verdict"] == "FETCH_FAILED":
            amended = "FETCH_FAILED"
        elif title_sim < 0.85 or not fam:
            amended = "MISMATCH"
        elif not excerpt_testable:
            amended = "PARTIAL"  # title/author/year verified; excerpt not testable from this locator
        elif not excerpt_supported:
            amended = "MISMATCH"
        elif base_ok:
            amended = "MATCH"
        else:
            amended = "PARTIAL"

        reason = {
            "MATCH": "title/author/year within convention and ledger excerpt is a verbatim (possibly elided) fragment of the fetched abstract",
            "PARTIAL": "title/author resolve to the same work but a declared condition is unmet (%s)" % (
                "|year_delta|>1: journal-vs-preprint year convention" if (yd is not None and abs(yd) > 1)
                else "excerpt not testable: source record carries no abstract" if not excerpt_testable
                else "other"),
            "MISMATCH": "identifier resolves to a different work, author mismatch, or excerpt unsupported",
            "FETCH_FAILED": "no locator resolved with HTTP 200",
        }[amended]

        results.append({
            "row": rn, "citation_id": cid, "class_mapping": r.get("class_mapping", ""),
            "used_by_theorems": r.get("used_by_theorems", ""),
            "ledger": {"title": r["title"], "authors": r["authors"], "year": ly,
                       "venue": r["venue"], "doi": r["doi"], "arxiv_id": r["arxiv_id"],
                       "exact_locator": r["exact_locator"], "verdict_column": r["verdict"],
                       "evidence_excerpt": r["evidence_excerpt"]},
            "fetched": {"kind": f.get("kind"), "title": f.get("title"), "authors": f.get("authors"),
                        "year": fy, "venue": f.get("venue"), "doi": f.get("doi"),
                        "abstract_present": bool(fab), "raw_path": raw_path,
                        "raw_sha256": measured, "locator_used": e.get("locator_used"),
                        "http_status": e.get("http_status")},
            "comparison": {"title_similarity": title_sim, "first_author_match": fam, "year_delta": yd,
                           "literal_first400_ratio": first400, "amended_best_window_ratio": bw,
                           "excerpt_contained_full": contained, "excerpt_testable": excerpt_testable,
                           "excerpt_supported": excerpt_supported,
                           "locator_is_search_query": locator_search},
            "verdict_preregistered_literal": e["verdict"],
            "verdict": amended, "verdict_reason": reason,
        })

    lit_summary = lit["summary"]
    summary = {
        "checked": len(results),
        "MATCH": sum(1 for x in results if x["verdict"] == "MATCH"),
        "PARTIAL": sum(1 for x in results if x["verdict"] == "PARTIAL"),
        "MISMATCH": sum(1 for x in results if x["verdict"] == "MISMATCH"),
        "FETCH_FAILED": sum(1 for x in results if x["verdict"] == "FETCH_FAILED"),
        "matched_under_preregistered_literal_rule": lit_summary["MATCH"],
        "literal_rule_MISMATCH_reclassified": sum(
            1 for x in results if x["verdict_preregistered_literal"] == "MISMATCH" and x["verdict"] != "MISMATCH"),
        "locator_quality_notes": [{"citation_id": x["citation_id"], "row": x["row"],
                                   "exact_locator_kind": "search_query"} for x in results
                                  if x["comparison"]["locator_is_search_query"]],
        "year_convention_notes": [{"citation_id": x["citation_id"], "row": x["row"],
                                   "ledger_year": x["ledger"]["year"], "fetched_year": x["fetched"]["year"],
                                   "year_delta": x["comparison"]["year_delta"],
                                   "note": "fetched year is the arXiv/preprint year while the ledger year is the journal year; both are named in the ledger venue"}
                                  for x in results if x["comparison"]["year_delta"] not in (None, 0, -1, 1)],
        "excerpt_not_testable": [{"citation_id": x["citation_id"], "row": x["row"],
                                  "why": "Crossref record for this DOI carries no abstract field (publisher deposits none); excerpt support is untestable from this locator, not contradicted"}
                                 for x in results if not x["comparison"]["excerpt_testable"]],
    }

    hard = [{"citation_id": x["citation_id"], "row": x["row"], "verdict": x["verdict"],
             "comparison": x["comparison"]} for x in results if x["verdict"] == "MISMATCH"]

    findings = [
        "Independent replication of worker-086's SRC-025 MISMATCH is NOT reproduced: the ledger excerpt is a verbatim mid-abstract fragment (amended best-window ratio 0.915; literal fixed-offset ratio 0.0025). The mismatch is an instrument artifact of comparing the first 400 characters at a fixed offset against an excerpt that begins after the abstract's opening and carries a label prefix.",
        "All 9 sampled rows store a search-query string in exact_locator rather than an exact identifier; the exact identifier had to be taken from the doi/arxiv_id columns. Combined with worker-086's 5 flagged rows this is 14 rows at ledger sha 315c19145065. This is a column-semantics finding, not a bibliographic error: the verification_method values (arxiv-api/inspirehep-api) are consistent with query-based verification.",
        "No bibliographic MISMATCH survives in the sample: 6 MATCH, 3 PARTIAL, 0 MISMATCH, 0 FETCH_FAILED. The 3 PARTIAL cases are 2 rows whose publisher record deposits no abstract (SRC-031, SRC-034: excerpt untestable from the Crossref locator) and 1 row where the ledger year is the journal year 2017 while the arXiv primary record is 2014 (SRC-028), explicitly a convention gap rather than an error.",
        "The pre-registered fixed-offset excerpt metric produced 2 false-positive MISMATCHes out of 9 (SRC-025, SRC-028); both were refuted by an offset-aware read of the same hashed raw bodies before this artifact was emitted. Any mechanical reuse of first-400 similarity as an excerpt-support test should require an offset/window search.",
    ]

    out = {
        "schema_version": "0.2",
        "artifact_type": "l1_refetch_spotcheck",
        "task_id": "W026-L1-SPOTCHECK-05",
        "node_id": "L1", "gate": "G-LIT", "class_ids": pre["sampling_rule"]["class_coverage"],
        "actor": "worker-026", "reviewer": "worker-026", "created_at": now(), "check_number": 5,
        "independent_of": pre["independence"]["independent_of"],
        "independence_note": pre["independence"]["why_this_frame"],
        "inputs": {
            "ledger/citation_audit.csv": {
                "sha256_before_fetch": lit["inputs"]["ledger/citation_audit.csv"]["sha256_before_fetch"],
                "sha256_after_fetch": ledger_after,
                "pinned": PIN, "drifted_during_fetch": ledger_after != PIN,
            },
            "artifacts/worker-026/l1_spotcheck/preregistration.json": {"sha256": sha(PRE.read_bytes())},
            "artifacts/worker-026/l1_spotcheck/check_spotcheck_026.py": {
                "sha256": "3d427394403f1028bf7e85b79991e5073b4d97e0cbdb9fef5c280d4813f2ad63",
                "role": "pre-registered fetch+literal-compare script (frozen before fetch)"},
            "artifacts/worker-026/l1_spotcheck/analyze_spotcheck_026.py": {
                "sha256": sha(Path(__file__).read_bytes()), "role": "post-fetch analyzer, no network"},
            "artifacts/worker-026/l1_spotcheck/spotcheck-l1-026.literal-preregistered.json": {
                "sha256": sha(LITERAL.read_bytes()), "role": "unmodified literal-rule run output"},
        },
        "raw_integrity": {"all_match": all(x["match"] for x in raw_integrity), "files": raw_integrity},
        "method": pre["method"]["primary_locator_policy"] + " " + pre["method"]["normalisation"],
        "rule_amendment": {
            "declared_before_fetch": pre["method"]["verdict_rule"]["MISMATCH"] + " | " + pre["method"]["verdict_rule"]["MATCH"],
            "applied_after_fetch_without_new_fetches": True,
            "amendment": "Excerpt support is decided by the best-aligned 200-char window ratio over the full normalised fetched abstract (>= 0.85) or full containment, instead of the fixed first-400-char offset ratio alone. Reason: the ledger excerpts begin after the abstract's opening sentence and carry a label prefix, so a fixed-offset ratio understates support for a genuine verbatim fragment.",
            "effect": [
                "SRC-025: MISMATCH -> MATCH (best-window 0.915; title 0.9862; author ok; year_delta -1)",
                "SRC-028: MISMATCH -> PARTIAL (best-window 0.995; title 1.0; author ok; year_delta -3 is journal-2017 vs arXiv-2014 convention, so the |year_delta|<=1 MATCH gate is correctly unmet)",
                "SRC-040: PARTIAL -> MATCH (best-window 0.95; all other MATCH gates met)",
            ],
            "direction_of_effect": "reduces claimed ledger defects (2 literal MISMATCHes -> 0); the literal pre-registered verdicts and their summary are preserved verbatim in the literal-preregistered artifact and per-row below",
        },
        "verdict_rule": {
            "MATCH": "title_similarity >= 0.95 AND first_author_match AND |year_delta| <= 1 AND excerpt_supported",
            "PARTIAL": "resolves to the same work (title >= 0.85, author ok) but a declared condition is unmet, including excerpt untestable from this locator",
            "MISMATCH": "title < 0.85 or author mismatch or excerpt tested and unsupported",
            "FETCH_FAILED": "no locator resolved with HTTP 200",
        },
        "results": results,
        "summary": summary,
        "literal_rule_summary": lit_summary,
        "literal_rule_hard_failures": lit["hard_failures"],
        "hard_failures": hard,
        "findings": findings,
        "valid": (ledger_after == PIN) and summary["FETCH_FAILED"] == 0
                 and all(x["match"] for x in raw_integrity),
        "void_reason": None if (ledger_after == PIN) else "ledger sha256 changed during the window; check VOID",
        "non_claims": pre["non_claims"],
    }
    OUT.write_text(json.dumps(out, indent=2, sort_keys=True))
    print("sha256", sha(OUT.read_bytes()))
    print(json.dumps({"valid": out["valid"], "summary": summary, "raw_integrity": out["raw_integrity"]["all_match"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
