#!/usr/bin/env python3
"""Acceptance checks for ledger/class_coverage.csv (worker flash-10, node L1).

Usage:
    python3 validate_class_coverage.py [csv]          # validate the real matrix
    python3 validate_class_coverage.py --self-test    # mutation test of this checker

Exit 0 = all checks pass.  Exit 1 = violations (printed with row ids).
"""
from __future__ import annotations

import csv
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEFAULT = HERE / "class_coverage.registry_based.csv"

COLUMNS = ["row_id", "source_key", "citation", "authors", "year", "locator_arxiv", "locator_doi",
           "journal_ref", "local_source_path", "local_source_sha256", "class_id", "coverage", "role",
           "conclusion_type_stated", "regularity", "genericity_stated", "exact_theorem",
           "theorem_locator", "scope_match", "basis", "verification_status", "assumptions",
           "falsifier", "ledger_row_id", "notes"]
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
COVERAGE = ["covered", "partial", "none", "unassessed"]
MERGED = re.compile(r"C\^?0\s*(or|/)\s*C\^?2|C\^?2\s*(or|/)\s*C\^?0", re.I)


def check(path: Path) -> list[str]:
    errs: list[str] = []
    with path.open(newline="") as f:
        rd = csv.DictReader(f)
        got = rd.fieldnames
        if got != COLUMNS:
            return [f"header mismatch:\n  got      {got}\n  expected {COLUMNS}"]
        rows = list(rd)
    if not rows:
        return ["no data rows"]
    seen = set()
    for r in rows:
        rid = r["row_id"]
        def bad(msg: str):
            errs.append(f"{rid}: {msg}")
        if rid in seen:
            bad("duplicate row_id")
        seen.add(rid)
        if not re.fullmatch(r"CC-\d{4}", rid or ""):
            bad(f"bad row_id format {rid!r}")
        if not r["source_key"]:
            bad("empty source_key")
        if r["class_id"] not in CLASSES:
            bad(f"unknown class_id {r['class_id']!r}")
        if r["coverage"] not in COVERAGE:
            bad(f"unknown coverage {r['coverage']!r}")
        if r["coverage"] in {"covered", "partial"}:
            if len(r["exact_theorem"].strip()) < 30:
                bad("covered/partial row without a usable exact_theorem quote")
            if r["basis"] not in {"primary_abstract", "primary_local"}:
                bad(f"covered/partial row with non-primary basis {r['basis']!r}")
        if (r["coverage"] == "unassessed") != (r["verification_status"] == "unresolved"):
            bad("unassessed and verification_status=unresolved must agree exactly")
        if r["coverage"] == "covered" and r["scope_match"] != "exact":
            bad("covered row must have scope_match=exact (use partial otherwise)")
        if r["role"] in {"falsifier", "counterexample"} and not r["falsifier"].strip():
            bad("falsifier row without a next falsifier")
        if r["verification_status"] == "verified_metadata" and not (r["locator_arxiv"] or r["locator_doi"]):
            bad("verified_metadata row without arXiv id or DOI")
        if r["verification_status"] == "verified_local" and not r["local_source_sha256"]:
            bad("verified_local row without local_source_sha256")
        for col, val in r.items():
            if val and MERGED.search(val):
                bad(f"merged C^0/C^2 token in column {col}: {val[:80]!r}")
    return errs


def self_test() -> int:
    base = DEFAULT
    if not base.exists():
        print("SKIP self-test: real csv not built yet")
        return 0
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "cc.csv"
        src = base.read_text()
        rows = list(csv.DictReader(src.splitlines()))
        header = src.splitlines()[0]

        def write(rows_):
            with tmp.open("w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=COLUMNS)
                w.writeheader()
                w.writerows(rows_)

        def pick(pred):
            return next(i for i, r in enumerate(rows) if pred(r))

        # The real matrix currently has zero 'covered' cells (that is its headline result),
        # so the covered-branch rules are mutation-tested on a synthetic covered fixture
        # derived from a real partial row.
        synth = dict(rows[next(k for k, r in enumerate(rows) if r["coverage"] == "partial")])
        synth.update({"row_id": "CC-9999", "coverage": "covered", "scope_match": "exact",
                      "role": "supporting"})
        rows = rows + [synth]
        i = len(rows) - 1
        mutants = []
        rows_cov = [dict(r) for r in rows]
        i = pick(lambda r: r["coverage"] == "covered")
        rows_cov[i]["class_id"] = "AF-SCC-C0ORC2"
        mutants.append(("M1 unknown class id", rows_cov))
        rows_cov = [dict(r) for r in rows]
        rows_cov[i]["exact_theorem"] = ""
        mutants.append(("M2 covered with empty theorem", rows_cov))
        rows_cov = [dict(r) for r in rows]
        rows_cov[0]["notes"] = "this leaks C0 or C2"
        mutants.append(("M3 merged regularity token", rows_cov))
        rows_cov = [dict(r) for r in rows]
        j = pick(lambda r: r["coverage"] == "unassessed")
        rows_cov[j]["verification_status"] = "verified_metadata"
        mutants.append(("M4 unassessed marked verified", rows_cov))
        rows_cov = [dict(r) for r in rows]
        rows_cov[i]["scope_match"] = "narrower"
        mutants.append(("M5 covered with narrower scope", rows_cov))
        rows_cov = [dict(r) for r in rows]
        k = pick(lambda r: r["verification_status"] == "verified_metadata")
        rows_cov[k]["locator_arxiv"] = ""
        rows_cov[k]["locator_doi"] = ""
        mutants.append(("M6 verified without locator", rows_cov))
        rows_cov = [dict(r) for r in rows]
        rows_cov[i]["falsifier"] = ""
        rows_cov[i]["role"] = "falsifier"
        mutants.append(("M7 falsifier without next falsifier", rows_cov))

        ok = True
        write([dict(r) for r in rows])
        errs = check(tmp)
        print(f"[{'PASS' if not errs else 'FAIL'}] clean fixture accepted" + ("" if not errs else f": {errs[:2]}"))
        ok &= not errs
        for name, mrows in mutants:
            write(mrows)
            errs = check(tmp)
            caught = bool(errs)
            print(f"[{'PASS' if caught else 'FAIL'}] mutant caught: {name}"
                  + (f" -> {errs[0]}" if caught else " -> NOT CAUGHT"))
            ok &= caught
        return 0 if ok else 1


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    errs = check(path)
    if errs:
        print(f"INVALID {path}: {len(errs)} violation(s)")
        for e in errs[:40]:
            print(" -", e)
        return 1
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    print(f"VALID {path}: {len(rows)} rows")
    from collections import Counter
    for cls in CLASSES:
        c = Counter(r["coverage"] for r in rows if r["class_id"] == cls)
        print(f"  {cls:20s} covered={c['covered']:2d} partial={c['partial']:2d} "
              f"none={c['none']:2d} unassessed={c['unassessed']:2d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
