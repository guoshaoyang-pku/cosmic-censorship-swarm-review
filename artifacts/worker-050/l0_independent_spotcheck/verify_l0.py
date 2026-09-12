#!/usr/bin/env python3
"""W050-L0-INDEPENDENT-SPOTCHECK-04 -- static consistency checker.

Independent worker measurement at frozen pins:
  L0 = ledger/theorems.jsonl      sha256 a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28
  L1 = ledger/citation_audit.csv  sha256 315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9

Checks (each recorded with an id, inputs, result and falsifier):
  C1 pins stable across the run (start vs end; drift -> exit 3)
  C2 every L0 source_id resolves to exactly one L1 citation_id
  C3 L1 used_by_theorems back-reference mentions the L0 theorem_id for every cited source
  C4 verification-status vocabulary is honoured and no row overstates reading depth relative
     to the L1 evidence_type of ALL its sources
  C5 unresolved gaps are marked unresolved (non-empty `unresolved`; metadata-only rows must
     flag the statement-retrieval gap)
  C6 class coverage census over the four frozen class ids
  C7 deterministic class-stratified spot-check sample (2 rows per class, per-record locator)

Exit codes: 0 all checks pass; 2 at least one check failed; 3 pin drift (fail closed).
Output: static_report.json next to this script.

This is a worker measurement, not a gate verdict and not a ledger edit.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter, OrderedDict, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

L0_PATH = ROOT / "ledger" / "theorems.jsonl"
L1_PATH = ROOT / "ledger" / "citation_audit.csv"
L0_PIN = "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"
L1_PIN = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
CLASSES = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
VERIFICATION_STATUS_VOCAB = {"unverified", "abstract-read", "full-text-read", "formally-verified"}
READING_DEPTH = {"unverified": 0, "abstract-read": 1, "full-text-read": 2, "formally-verified": 3}
EVIDENCE_DEPTH = {"metadata": 0, "abstract": 1, "full-text": 2}
CST = timezone(timedelta(hours=8))

# A locator that points at one record rather than at a search result set.
PER_RECORD_PATTERNS = [
    re.compile(r"^https?://arxiv\.org/(abs|pdf)/", re.I),
    re.compile(r"^https?://(www\.)?inspirehep\.net/(api/)?literature/\d+", re.I),
    re.compile(r"^https?://(dx\.)?doi\.org/", re.I),
    re.compile(r"^https?://api\.openalex\.org/works/", re.I),
    re.compile(r"^https?://(www\.)?ncbi\.nlm\.nih\.gov/", re.I),
]
SEARCH_QUERY_MARKERS = ("api/query", "api/literature?q=", "search_query=", "?q=", "/search")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_per_record(url: str) -> bool:
    if not url or any(m in url for m in SEARCH_QUERY_MARKERS):
        return False
    return any(p.match(url) for p in PER_RECORD_PATTERNS)


def load_l0():
    return [json.loads(line) for line in L0_PATH.read_text().splitlines() if line.strip()]


def load_l1():
    with open(L1_PATH, newline="") as fh:
        return list(csv.DictReader(fh))


def select_sample(rows, cit):
    """2 rows per class in file order; for each row the first source with a per-record locator."""
    sample, used_rows = [], set()
    for cls in CLASSES:
        picked = 0
        for row in rows:
            if cls not in (row.get("class_ids") or []):
                continue
            if row["theorem_id"] in used_rows:
                continue
            chosen = None
            for sid in row.get("source_ids", []):
                rec = cit.get(sid)
                if not rec:
                    continue
                for field in ("evidence_url", "url", "exact_locator"):
                    url = (rec.get(field) or "").strip()
                    if is_per_record(url):
                        chosen = {
                            "theorem_id": row["theorem_id"],
                            "class_id": cls,
                            "class_ids": row.get("class_ids"),
                            "label": row.get("label"),
                            "content_status": row.get("content_status"),
                            "verification_status": row.get("verification_status"),
                            "source_id": sid,
                            "locator_field": field,
                            "locator": url,
                            "l1_title": rec.get("title"),
                            "l1_status": rec.get("status"),
                            "l1_evidence_type": rec.get("evidence_type"),
                            "l1_http_status": rec.get("http_status"),
                        }
                        break
                if chosen:
                    break
            if not chosen:
                continue
            sample.append(chosen)
            used_rows.add(row["theorem_id"])
            picked += 1
            if picked == 2:
                break
    return sample


def main() -> int:
    checks = OrderedDict()
    l0_start, l1_start = sha256(L0_PATH), sha256(L1_PATH)
    pin_drift = {"L0": l0_start != L0_PIN, "L1": l1_start != L1_PIN}

    rows, cit_rows = load_l0(), load_l1()
    cit = {r["citation_id"]: r for r in cit_rows}

    # C2 source resolution
    unresolved = []
    for row in rows:
        for sid in row.get("source_ids", []):
            if sid not in cit:
                unresolved.append({"theorem_id": row["theorem_id"], "source_id": sid})
    checks["C2_source_ids_resolve"] = {
        "result": "pass" if not unresolved else "fail",
        "citations_in_l1": len(cit_rows),
        "unresolved": unresolved,
        "falsifier": "Any L0 source_id absent from the pinned L1 citation ledger voids C2.",
    }

    # C3 back-reference
    backref_missing = []
    for row in rows:
        for sid in row.get("source_ids", []):
            rec = cit.get(sid)
            if not rec:
                continue
            used = [t.strip() for t in (rec.get("used_by_theorems") or "").split(";") if t.strip()]
            if row["theorem_id"] not in used:
                backref_missing.append({"theorem_id": row["theorem_id"], "source_id": sid, "used_by": used})
    checks["C3_l1_back_reference"] = {
        "result": "pass" if not backref_missing else "fail",
        "missing": backref_missing,
        "falsifier": "Any cited L1 row whose used_by_theorems omits the citing L0 theorem_id voids C3.",
    }

    # C4 status honesty
    bad_vocab, overstated = [], []
    for row in rows:
        vs = row.get("verification_status")
        if vs not in VERIFICATION_STATUS_VOCAB:
            bad_vocab.append({"theorem_id": row["theorem_id"], "verification_status": vs})
            continue
        depths = [
            EVIDENCE_DEPTH.get(cit[s]["evidence_type"], -1)
            for s in row.get("source_ids", [])
            if s in cit
        ]
        if depths and READING_DEPTH[vs] > max(depths):
            overstated.append(
                {
                    "theorem_id": row["theorem_id"],
                    "verification_status": vs,
                    "max_source_evidence_type": max(depths),
                    "source_ids": row.get("source_ids"),
                }
            )
    checks["C4_status_honesty"] = {
        "result": "pass" if not bad_vocab and not overstated else "fail",
        "status_census": dict(Counter(r.get("verification_status") for r in rows)),
        "out_of_vocabulary": bad_vocab,
        "overstated_rows": overstated,
        "falsifier": "Any row whose verification_status exceeds the deepest L1 evidence_type among its cited sources (or is outside the declared vocabulary) voids C4.",
    }

    # C5 unresolved marking
    no_unresolved, metadata_unflagged = [], []
    for row in rows:
        unres = row.get("unresolved")
        has = bool(unres) if isinstance(unres, list) else bool(str(unres or "").strip())
        if not has:
            no_unresolved.append(row["theorem_id"])
        src_types = [cit[s]["evidence_type"] for s in row.get("source_ids", []) if s in cit]
        if src_types and all(t == "metadata" for t in src_types):
            blob = json.dumps(unres)
            if not re.search(r"retriev|statement|wording|abstract|metadata|body|transcri", blob, re.I):
                metadata_unflagged.append(row["theorem_id"])
    checks["C5_unresolved_marked"] = {
        "result": "pass" if not no_unresolved and not metadata_unflagged else "fail",
        "rows_without_unresolved_field": no_unresolved,
        "metadata_only_rows_without_retrieval_gap_flag": metadata_unflagged,
        "falsifier": "A row with no unresolved entry, or a metadata-only row that does not flag a statement-retrieval gap, voids C5.",
    }

    # C6 class coverage
    coverage = defaultdict(list)
    for row in rows:
        for cls in row.get("class_ids") or []:
            if cls in CLASSES:
                coverage[cls].append(row["theorem_id"])
    checks["C6_class_coverage"] = {
        "result": "pass" if all(coverage[c] for c in CLASSES) else "fail",
        "coverage": {c: len(coverage[c]) for c in CLASSES},
        "uncovered_classes": [c for c in CLASSES if not coverage[c]],
        "falsifier": "Any frozen class id with zero L0 rows voids the class-stratified reading of C7.",
    }

    # C7 sample selection
    sample = select_sample(rows, cit)
    checks["C7_spotcheck_sample"] = {
        "result": "pass" if len(sample) == 8 else "fail",
        "sample_size": len(sample),
        "per_class": dict(Counter(s["class_id"] for s in sample)),
        "falsifier": "Fewer than two per-record locators per class, or a non-deterministic sample, voids C7.",
    }

    # C1 re-measure at the end
    l0_end, l1_end = sha256(L0_PATH), sha256(L1_PATH)
    pin_drift["L0_end"] = l0_end != L0_PIN
    pin_drift["L1_end"] = l1_end != L1_PIN
    checks["C1_pins"] = {
        "result": "pass" if not any(pin_drift.values()) else "fail",
        "L0": {"path": str(L0_PATH.relative_to(ROOT)), "pin": L0_PIN, "start": l0_start, "end": l0_end},
        "L1": {"path": str(L1_PATH.relative_to(ROOT)), "pin": L1_PIN, "start": l1_start, "end": l1_end},
        "drift": {k: v for k, v in pin_drift.items() if v},
        "falsifier": "Any L0 or L1 hash difference from the pin at read time voids every check.",
    }

    all_pass = all(c["result"] == "pass" for c in checks.values())
    report = {
        "task_id": "W050-L0-INDEPENDENT-SPOTCHECK-04",
        "artifact_type": "independent_l0_static_consistency_report",
        "class_id": ";".join(CLASSES),
        "node_id": "L0",
        "gate": "G-LIT",
        "actor": "worker-050",
        "deterministic": True,
        "generated_at": now(),
        "pins": {"L0": L0_PIN, "L1": L1_PIN},
        "counts": {
            "l0_rows": len(rows),
            "l1_rows": len(cit_rows),
            "l0_class_rows": {c: len(coverage[c]) for c in CLASSES},
            "content_status": dict(Counter(r.get("content_status") for r in rows)),
            "verification_status": dict(Counter(r.get("verification_status") for r in rows)),
            "review_status": dict(Counter(r.get("review_status") for r in rows)),
            "l1_evidence_type": dict(Counter(r["evidence_type"] for r in cit_rows)),
            "l1_verdict": dict(Counter(r["verdict"] for r in cit_rows)),
            "l1_reviewer": dict(Counter(r["reviewer"] for r in cit_rows)),
            "l1_exact_locator_search_query": sum(
                1 for r in cit_rows if any(m in (r.get("exact_locator") or "") for m in SEARCH_QUERY_MARKERS)
            ),
        },
        "checks": checks,
        "spotcheck_sample": sample,
        "verdict": "static_checks_pass" if all_pass else "static_checks_fail",
        "scope_limit": (
            "Static consistency only: it does not re-derive any mathematics and does not re-fetch "
            "sources (see fetch_l0_sample.py for the live pass). Binds only to the two pinned hashes."
        ),
    }
    (OUT / "static_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    if any(pin_drift.values()):
        print("PIN DRIFT", pin_drift, file=sys.stderr)
        return 3
    print("static checks:", "PASS" if all_pass else "FAIL", "| rows:", len(rows), "| sample:", len(sample))
    for name, c in checks.items():
        print(f"  {name}: {c['result']}")
    return 0 if all_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
