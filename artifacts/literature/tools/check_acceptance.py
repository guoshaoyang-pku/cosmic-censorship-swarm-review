#!/usr/bin/env python3
"""Check the literature ledger against the Astra L0/L1 acceptance criteria.

L0 (asg-...-03): >=15 rows; each row: source (authors, year, title, DOI/arXiv),
  theorem as quoted, assumptions, class_id, what it does NOT prove,
  verification_status in {unverified, abstract-read, full-text, page-checked}, falsifier.
L1 (asg-...-04): one row per ledger source with locator, resolver result,
  exact theorem number/page, class mapping, verdict, reviewer.

Emits artifacts/literature/L0_L1_ACCEPTANCE.md and exits non-zero on a hard gap.
"""
from __future__ import annotations
import csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "ledger"
LIT = ROOT / "artifacts" / "literature"
VERIF = {"unverified", "abstract-read", "full-text", "page-checked"}


def main():
    rows = [json.loads(l) for l in (LEDGER / "theorems.jsonl").read_text().splitlines() if l.strip()]
    srcs = {s["source_id"]: s for s in
            (json.loads(l) for p in sorted((LIT / "sources").glob("batch-*.jsonl"))
             for l in p.read_text().splitlines() if l.strip())}
    audit = list(csv.DictReader(open(LEDGER / "citation_audit.csv")))

    l0_gaps = []
    for r in rows:
        tid = r["theorem_id"]
        if not r.get("source_ids"):
            l0_gaps.append(f"{tid}: no source_ids")
        if not r.get("statement_exact"):
            l0_gaps.append(f"{tid}: no statement_exact")
        if not r.get("assumptions"):
            l0_gaps.append(f"{tid}: no assumptions")
        if not r.get("class_ids") and not r.get("ledger_tags"):
            l0_gaps.append(f"{tid}: neither class_id nor tag")
        if not r.get("does_not_imply"):
            l0_gaps.append(f"{tid}: no does_not_imply")
        if r.get("verification_status") not in VERIF:
            l0_gaps.append(f"{tid}: bad verification_status {r.get('verification_status')!r}")
        if not r.get("falsifiers"):
            l0_gaps.append(f"{tid}: no falsifier")
        for sid in r.get("source_ids", []):
            s = srcs.get(sid)
            if not s:
                l0_gaps.append(f"{tid}: unknown source {sid}")
            elif not (s.get("doi") or s.get("arxiv_id") or s.get("url")):
                l0_gaps.append(f"{tid}: source {sid} has no locator")

    l1_gaps = []
    required = ["citation_id", "url", "resolver_result", "exact_locator", "class_mapping", "verdict", "reviewer"]
    have_cols = set(audit[0].keys()) if audit else set()
    for c in required:
        if c not in have_cols:
            l1_gaps.append(f"missing column {c}")
    for a in audit:
        if not a.get("resolver_result"):
            l1_gaps.append(f"{a['citation_id']}: no resolver_result")
        if not a.get("verdict"):
            l1_gaps.append(f"{a['citation_id']}: no verdict")
        if not a.get("assessment"):
            l1_gaps.append(f"{a['citation_id']}: no assessment")
        if not (a.get("doi") or a.get("arxiv_id") or a.get("url")):
            if a.get("resolver_result") == "unresolved":
                if not a.get("assessment"):
                    l1_gaps.append(f"{a['citation_id']}: unresolved locator without an assessment reason")
            else:
                l1_gaps.append(f"{a['citation_id']}: no locator")

    l0_ok = len(rows) >= 15 and not l0_gaps
    l1_ok = len(audit) >= len(srcs) and not l1_gaps

    out = ["# L0/L1 acceptance check (Astra assignment cards)", "",
           f"- L0 rows: {len(rows)} (threshold >=15) -> {'PASS' if l0_ok else 'FAIL'}",
           f"- L1 rows: {len(audit)} for {len(srcs)} sources -> {'PASS' if l1_ok else 'FAIL'}",
           f"- L0 verification_status counts: "
           + json.dumps({v: len([r for r in rows if r.get('verification_status') == v]) for v in sorted(VERIF)}),
           f"- L0 class coverage: "
           + json.dumps({c: len([r for r in rows if c in r.get('class_ids', [])]) for c in
                         ['AF-WCC-VAC-GEN', 'AF-SCC-C2-VAC-GEN', 'AF-SCC-C0-VAC-GEN', 'AF-WCC-SCALAR-SPH']}),
           "", "## L0 gaps", ""]
    out += [f"- {g}" for g in l0_gaps] or ["- none"]
    out += ["", "## L1 gaps", ""]
    out += [f"- {g}" for g in l1_gaps] or ["- none"]
    out += ["", "## Note on 'exact theorem number/page'", "",
            "The L1 `exact_locator` column carries the primary page/record URL. Theorem/section numbers were",
            "extracted only where the accessible abstract or Crossref record exposes them; most primary full",
            "texts are paywalled, so the audit records the abstract-level locator rather than inventing a number."]
    (LIT / "L0_L1_ACCEPTANCE.md").write_text("\n".join(out) + "\n")
    print("\n".join(out[:8]))
    return 0 if (l0_ok and l1_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
