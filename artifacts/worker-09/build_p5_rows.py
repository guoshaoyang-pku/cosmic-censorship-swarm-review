#!/usr/bin/env python3
"""Worker 09 / P5: project the two P5 findings into the lead's canonical CSV schema.

Output: ledger/citation_audit_scc_flash-09.p5.csv (post-freeze addendum; does NOT touch
ledger/citation_audit.csv or the frozen theorem/citation files). The lead remains the only
writer of the canonical ledger; this file is staged for ingestion.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent      # repo root
FIND = ROOT / "artifacts/worker-09/extracted/p5_findings.json"
OUT = ROOT / "ledger/citation_audit_scc_flash-09.p5.csv"

f = json.loads(FIND.read_text())
rows = []


def excerpt(fid: str) -> str:
    r = next(x for x in f["rows"] if x["finding_id"] == fid)
    return " || ".join(r["exact_quotes"])


rows.append({
    "citation_id": "W09-025",
    "bibkey": "grant2019future",
    "title": "The future is not always open",
    "authors": "James D. E. Grant; Michael Kunzinger; Clemens Saemann; Roland Steinbauer",
    "year": "2020",
    "venue": "Letters in Mathematical Physics 110(1), 83-103; arXiv:1901.07996v2",
    "doi": "10.1007/s11005-019-01213-8",
    "arxiv_id": "1901.07996",
    "url": "https://arxiv.org/abs/1901.07996",
    "status": "verified-primary",
    "resolver_result": "resolved",
    "verification_method": "arXiv HTML v2 + ar5iv full text + Crossref DOI (worker-09 P5)",
    "evidence_type": "theorem-statement",
    "fetched_at": f["generated_at"],
    "http_status": "200",
    "exact_locator": "Theorem 2.10; Theorem 2.15; Corollary 2.16; Example 3.1 (arXiv:1901.07996v2)",
    "evidence_url": "https://arxiv.org/abs/1901.07996v2",
    "elided_quote": "False",
    "mirror_of": "",
    "evidence_excerpt": excerpt("W09-P5-001"),
    "used_by_theorems": "",
    "class_mapping": "AF-SCC-C0-VAC-GEN",
    "assessment": ("Convention caveat for extension_predicate clause (f): for continuous (non-Lipschitz) "
                   "metrics I^+ need not be open and may depend on the curve class (Thm 2.10, Thm 2.15, Ex 3.1). "
                   "No Einstein equation, no 4D AF data, no genericity statement: supports the caveat only, "
                   "not the class conclusion. Schema wording fix: 'causal structure can be degenerate' -> "
                   "'not causally plain (may exhibit bubbling)'."),
    "verdict": "verified",
    "reviewer": "deepseek-flash-09",
})

rows.append({
    "citation_id": "W09-026",
    "bibkey": "rendall2005nature",
    "title": "The nature of spacetime singularities",
    "authors": "Alan D. Rendall",
    "year": "2005",
    "venue": "100 Years of Relativity: Space-Time Structure: Einstein and Beyond (A. Ashtekar, ed.), World Scientific, 76-92; arXiv:gr-qc/0503112",
    "doi": "10.1142/9789812700988_0003",
    "arxiv_id": "gr-qc/0503112",
    "url": "https://arxiv.org/abs/gr-qc/0503112",
    "status": "verified-primary",
    "resolver_result": "resolved",
    "verification_method": "arXiv abs + ar5iv full text + Crossref DOI (worker-09 P5)",
    "evidence_type": "survey-statement",
    "fetched_at": f["generated_at"],
    "http_status": "200",
    "exact_locator": "Section 2 (extendibility/Cauchy horizon/Taub-NUT); Section 3 (RN/Kerr Cauchy horizon)",
    "evidence_url": "https://arxiv.org/abs/gr-qc/0503112",
    "elided_quote": "False",
    "mirror_of": "",
    "evidence_excerpt": excerpt("W09-P5-002"),
    "used_by_theorems": "",
    "class_mapping": "AF-SCC-C0-VAC-GEN",
    "assessment": ("Survey-level only, no numbered theorem. Supports the vocabulary and the non-vacuity/motivation "
                   "of the extension predicate (Taub-NUT: highly symmetric vacuum solution with an extendible maximal "
                   "Cauchy development) and why the class needs its genericity quantifier. Does NOT prove the class "
                   "conclusion, does NOT prove Kerr/RN AF extendibility, and its Taub-NUT extension is smooth, so it "
                   "cannot discriminate C0 from C2/H2_loc."),
    "verdict": "verified-survey-level",
    "reviewer": "deepseek-flash-09",
})

cols = ["citation_id", "bibkey", "title", "authors", "year", "venue", "doi", "arxiv_id", "url",
        "status", "resolver_result", "verification_method", "evidence_type", "fetched_at",
        "http_status", "exact_locator", "evidence_url", "elided_quote", "mirror_of",
        "evidence_excerpt", "used_by_theorems", "class_mapping", "assessment", "verdict", "reviewer"]

with OUT.open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)

h = hashlib.sha256(OUT.read_bytes()).hexdigest()
print("wrote", OUT.relative_to(ROOT), "rows", len(rows), "sha256", h)
