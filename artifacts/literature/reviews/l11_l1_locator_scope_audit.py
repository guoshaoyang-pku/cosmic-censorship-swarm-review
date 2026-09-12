#!/usr/bin/env python3
"""L11 independent read-only audit: L1 locator-column scope under controller ruling REC-6.

Question (gate-blocking for the L1 half of G-LIT):
  Worker-025's independent revise (reviews/L1-locator-adjudication-025.json, 3.0) reports that
  71/97 `exact_locator` values in ledger/citation_audit.csv are not record locators.
  Controller ruling REC-6 (astra-life04-verify-l0-rev3 card) states: "evidence_url is the
  locator column". So the scope question is whether the L1 evidence-binding criterion is
  evaluated on `exact_locator` (revise-bound) or on `evidence_url` (possibly satisfied).

This script measures BOTH columns with one explicit predicate and reports, per row, whether a
record-shaped anchor exists. It is deterministic and offline: no network, no writes outside its
own output paths, no ledger write, no map write.

Reproduce:  python3 artifacts/literature/reviews/l11_l1_locator_scope_audit.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "ledger" / "citation_audit.csv"
ACCEPTANCE = ROOT / "artifacts" / "literature" / "L0_L1_ACCEPTANCE.md"
OUT_JSON = ROOT / "artifacts" / "literature" / "reviews" / "L1-locator-scope-L11-machine.json"

PINS = {
    "ledger/citation_audit.csv": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
    "artifacts/literature/L0_L1_ACCEPTANCE.md": "fde5600b45a58698d1cb4e625127bcd54952dc9eaf17a47449329cccc28806c5",
}

# --- predicate -------------------------------------------------------------------------------
# A RECORD-shaped locator identifies one bibliographic record (record page, DOI, arXiv abs,
# or an API record endpoint carrying an id). Anything else is not a record locator.
RE_RECORD_ENDPOINT = re.compile(
    r"(inspirehep\.net/api/literature/\d+)"
    r"|(api\.crossref\.org/works/10\.\d{4,9}/)"
    r"|(api\.openalex\.org/works/doi:)"
    r"|(api\.semanticscholar\.org/(paper|graph)/)"
)
RE_ARXIV_ABS = re.compile(r"arxiv\.org/(abs|pdf)/\d{4}\.\d{4,5}")
RE_DOI = re.compile(r"(doi\.org/10\.\d{4,9}/)|(^10\.\d{4,9}/)")
RE_DISCOVERY = re.compile(r"(api/query)|(\?q=)|(/search)|(search\?)|(query\?)", re.I)
RE_METADATA_ENDPOINT = re.compile(r"(api\.)|(/api/)|(export\.arxiv\.org)", re.I)


def classify(value: str) -> str:
    v = (value or "").strip()
    if not v:
        return "ABSENT"
    if "..." in v:
        return "TRUNCATED"
    if RE_DISCOVERY.search(v):
        return "DISCOVERY_QUERY"
    if RE_RECORD_ENDPOINT.search(v):
        return "RECORD_ENDPOINT"
    if RE_ARXIV_ABS.search(v):
        return "RECORD_PAGE"
    if RE_DOI.search(v):
        return "DOI"
    if RE_METADATA_ENDPOINT.search(v):
        return "METADATA_ENDPOINT"
    return "RECORD_PAGE"


RECORD_CLASSES = {"RECORD_PAGE", "RECORD_ENDPOINT", "DOI"}
NON_RECORD_CLASSES = {"TRUNCATED", "DISCOVERY_QUERY", "METADATA_ENDPOINT"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    measured = {
        "ledger/citation_audit.csv": sha256(LEDGER),
        "artifacts/literature/L0_L1_ACCEPTANCE.md": sha256(ACCEPTANCE),
    }
    pin_match = {k: measured[k] == v for k, v in PINS.items()}

    with LEDGER.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    exact = Counter()
    evid = Counter()
    per_row = []
    for r in rows:
        ex = classify(r.get("exact_locator", ""))
        ev = classify(r.get("evidence_url", ""))
        alts = {
            "url": classify(r.get("url", "")),
            "doi": classify(r.get("doi", "")),
            "arxiv_id": classify(r.get("arxiv_id", "")),
        }
        anchors = {k: v for k, v in alts.items() if v in RECORD_CLASSES}
        exact[ex] += 1
        evid[ev] += 1
        per_row.append(
            {
                "citation_id": r["citation_id"],
                "evidence_type": r.get("evidence_type", ""),
                "verification_method": r.get("verification_method", ""),
                "exact_locator_class": ex,
                "evidence_url_class": ev,
                "alternative_record_anchors": anchors,
                "evidence_url_record_shaped": ev in RECORD_CLASSES,
                "any_record_anchor": (ev in RECORD_CLASSES) or bool(anchors),
                "exact_locator_is_record": ex in RECORD_CLASSES,
            }
        )

    n = len(rows)
    exact_non_record = sum(v for k, v in exact.items() if k in NON_RECORD_CLASSES)
    evid_non_record = sum(v for k, v in evid.items() if k in NON_RECORD_CLASSES)
    evid_absent = evid.get("ABSENT", 0)
    evid_record = sum(v for k, v in evid.items() if k in RECORD_CLASSES)
    any_anchor = sum(1 for x in per_row if x["any_record_anchor"])
    rows_evidence_url_is_only_defect = [
        x["citation_id"]
        for x in per_row
        if x["evidence_url_record_shaped"] is False and x["any_record_anchor"] is True
    ]

    rep = {
        "schema_version": "0.1",
        "artifact_kind": "read-only-audit",
        "actor": "astra-lead-literature",
        "lifecycle": "L11",
        "node_id": "L1",
        "gate": "G-LIT",
        "pins_declared": PINS,
        "pins_measured": measured,
        "pins_match": pin_match,
        "rows": n,
        "predicate": {
            "record_shaped": sorted(RECORD_CLASSES),
            "non_record": sorted(NON_RECORD_CLASSES),
            "exact_locator_classes": dict(exact),
            "evidence_url_classes": dict(evid),
        },
        "counts": {
            "exact_locator_non_record": exact_non_record,
            "exact_locator_record": n - exact_non_record,
            "evidence_url_record": evid_record,
            "evidence_url_non_record": evid_non_record,
            "evidence_url_absent": evid_absent,
            "any_record_anchor": any_anchor,
            "rows_with_no_record_anchor": n - any_anchor,
            "rows_where_evidence_url_not_record_but_alt_anchor_exists": len(
                rows_evidence_url_is_only_defect
            ),
        },
        "rows_with_no_record_anchor": [
            x["citation_id"] for x in per_row if not x["any_record_anchor"]
        ],
        "rows_evidence_url_not_record_but_alt_anchor": rows_evidence_url_is_only_defect,
        "row_detail": per_row,
        "not_claimed": [
            "gate verdict",
            "node status",
            "validation_status",
            "ledger or acceptance-note write",
            "HF-02 class-leakage adjudication",
            "HF-03 unsupported-citation finding",
        ],
    }
    OUT_JSON.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({k: rep[k] for k in ("pins_match", "rows", "counts", "predicate")}, indent=1))
    print("wrote", OUT_JSON.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
