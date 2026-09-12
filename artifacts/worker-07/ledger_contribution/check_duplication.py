#!/usr/bin/env python3
"""Duplication detector for the L0 theorem ledger.

Why: A0/A2 measure duplication and novel accepted coverage.  The ledger now has
rows from two authors (literature lead, worker-07) covering overlapping results;
without a detector the same claim is counted twice in citation_audit.csv's
used_by_theorems and in any coverage metric.

Method (read-only, deterministic):
  * pair score = source overlap + class overlap + statement token Jaccard
  * flag a pair as PROBABLE_DUPLICATE when sources overlap >= 0.5 and
    (classes overlap >= 0.5 or one row is DEFINITIONS-only), or token Jaccard >= 0.35
  * flag as POSSIBLE_SUPERSESSION when a provisional/unresolved row shares a source
    with an accepted row and the accepted row's label covers the same result
  * union-find clusters the flagged pairs
It never edits rows; it writes a report and exits 1 when a cluster has no
declared `overlaps`/`superseded_by` annotation, which is the actionable state.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIT = ROOT / "artifacts" / "literature"
LEDGER = ROOT / "ledger" / "theorems.jsonl"
REPORT = Path(__file__).resolve().parent / "duplication_report.json"
CST = timezone(timedelta(hours=8))
STOP = {"the", "a", "an", "of", "for", "and", "or", "in", "on", "to", "with", "the",
        "is", "are", "that", "this", "by", "from", "as", "at", "it", "its", "be"}
WORD = re.compile(r"[a-z0-9^]+")


def toks(s: str) -> set[str]:
    return {w for w in WORD.findall((s or "").lower()) if w not in STOP and len(w) > 2}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a | b) else 0.0


def overlap(a, b) -> float:
    a, b = set(a), set(b)
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def read_rows() -> list[dict]:
    if not LEDGER.exists():
        print(f"no ledger at {LEDGER}")
        sys.exit(2)
    return [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]


def read_sources() -> dict:
    out = {}
    for p in sorted((LIT / "sources").glob("batch-*.jsonl")):
        for l in p.read_text().splitlines():
            if l.strip():
                s = json.loads(l)
                out[s["source_id"]] = s
    return out


def canonical_key(s: dict) -> str:
    """Same work under two source_ids must compare equal: prefer arXiv id, then DOI, then title."""
    ax = (s.get("arxiv_id") or "").strip().lower()
    if ax:
        return "arxiv:" + re.sub(r"v\d+$", "", ax)
    doi = (s.get("doi") or "").strip().lower()
    if doi:
        return "doi:" + doi
    return "title:" + re.sub(r"[^a-z0-9]+", " ", (s.get("title") or "").lower()).strip()



def main() -> int:
    rows = read_rows()
    sources = read_sources()
    key = {sid: canonical_key(s) for sid, s in sources.items()}
    # duplicate source records: same work registered under multiple source_ids
    by_key: dict[str, list[str]] = {}
    for sid, k in key.items():
        by_key.setdefault(k, []).append(sid)
    dup_sources = {k: sorted(v) for k, v in by_key.items() if len(v) > 1}
    text = {r["theorem_id"]: toks(r.get("statement_exact", "") + " " + r.get("label", ""))
            for r in rows}
    pairs, clusters = [], []
    parent = {r["theorem_id"]: r["theorem_id"] for r in rows}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    def skey_set(r):
        return {key.get(s, "id:" + s) for s in r.get("source_ids", [])}

    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows[i], rows[j]
            so = overlap(skey_set(a), skey_set(b))          # compares WORKS, not ids
            co = overlap(a.get("class_ids", []), b.get("class_ids", []))
            tj = jaccard(text[a["theorem_id"]], text[b["theorem_id"]])
            defs = set(a.get("class_ids", [])) == {"DEFINITIONS"} or set(b.get("class_ids", [])) == {"DEFINITIONS"}
            if not ((so >= 0.5 and (co >= 0.5 or defs)) or tj >= 0.35):
                continue
            statuses = {a["status"], b["status"]}
            sup = ("accepted" in statuses and
                   ({"provisional", "unresolved"} & statuses) and so >= 0.5 and co >= 0.5)
            # Tiering: a shared source + shared class is necessary but not sufficient for
            # duplication -- two rows about different papers in one programme (e.g. T-201/T-202)
            # are complementary.  Text similarity decides the tier; low-similarity pairs are
            # sent to review rather than asserted as duplicates.
            if sup and tj >= 0.15:
                kind, tier = "SUPERSESSION_CANDIDATE", "ACTIONABLE"
            elif so >= 0.5 and co >= 0.5 and tj >= 0.25:
                kind, tier = "STRONG_DUPLICATE_CANDIDATE", "ACTIONABLE"
            elif tj >= 0.45:
                kind, tier = "STRONG_DUPLICATE_CANDIDATE", "ACTIONABLE"
            else:
                kind, tier = "REVIEW_SAME_WORK_OR_PROGRAMME", "REVIEW"
            pairs.append({"a": a["theorem_id"], "b": b["theorem_id"], "kind": kind, "tier": tier,
                          "work_overlap": round(so, 2), "class_overlap": round(co, 2),
                          "token_jaccard": round(tj, 2),
                          "a_status": a["status"], "b_status": b["status"]})
            if tier == "ACTIONABLE":
                union(a["theorem_id"], b["theorem_id"])

    groups: dict[str, list[str]] = {}
    for r in rows:
        groups.setdefault(find(r["theorem_id"]), []).append(r["theorem_id"])
    status = {r["theorem_id"]: r["status"] for r in rows}
    unannotated = []
    for members in groups.values():
        if len(members) < 2:
            continue
        clusters.append(sorted(members))
        for m in members:
            row = next(r for r in rows if r["theorem_id"] == m)
            if not (row.get("overlaps") or row.get("superseded_by")):
                unannotated.append(m)

    actionable = [p for p in pairs if p["tier"] == "ACTIONABLE"]
    review = [p for p in pairs if p["tier"] == "REVIEW"]
    report = {
        "detector": "worker-07 ledger duplication detector v2.1 (canonical work keys, tiered)",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "rows": len(rows),
        "sources": len(sources),
        "duplicate_source_records": dup_sources,
        "duplicate_source_record_count": len(dup_sources),
        "flagged_pairs": len(pairs),
        "actionable_pairs": len(actionable),
        "review_pairs": len(review),
        "clusters": clusters,
        "cluster_count": len(clusters),
        "unannotated_members": unannotated,
        "pairs": pairs,
        "status_by_row": status,
        "precision_caveat": ("Shared work + shared class is necessary but not sufficient for "
                             "duplication (different papers in one programme are complementary). "
                             "REVIEW pairs require human adjudication; only ACTIONABLE pairs demand "
                             "overlaps/superseded_by annotations."),
        "verdict": ("NO ACTIONABLE CLUSTERS" if not clusters
                    else f"{len(actionable)} actionable pair(s) in {len(clusters)} cluster(s); "
                         f"{len(unannotated)} member(s) lack overlaps/superseded_by annotation; "
                         f"{len(review)} pair(s) queued for review"),
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"rows {len(rows)}  sources {len(sources)}  "
          f"duplicate source records {len(dup_sources)}  flagged pairs {len(pairs)} "
          f"(actionable {len(actionable)}, review {len(review)})  clusters {len(clusters)}")
    for k, v in dup_sources.items():
        print(f"  DUPLICATE SOURCE: {k} -> {v}")
    for c in clusters:
        print("  cluster:", " ".join(f"{m}[{status[m][:4]}]" for m in c))
    for p in pairs:
        if p["tier"] == "ACTIONABLE":
            print(f"    {p['kind']:<28} {p['a']:<9} {p['b']:<9} work={p['work_overlap']} "
                  f"cls={p['class_overlap']} tok={p['token_jaccard']}")
    print(f"actionable cluster members lacking annotation: {unannotated}")
    print(f"review-tier pairs (same work/programme, adjudicate manually): {len(review)}")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    return 1 if unannotated else 0


if __name__ == "__main__":
    sys.exit(main())
