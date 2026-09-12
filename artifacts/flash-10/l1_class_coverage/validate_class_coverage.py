#!/usr/bin/env python3
"""Acceptance checks for ledger/class_coverage.csv (worker flash-10, node L1, gate G-LIT).

Usage:
    python3 validate_class_coverage.py [csv]          # validate the real matrix
    python3 validate_class_coverage.py --self-test    # mutation test of this checker

Checks include structural completeness against ledger/citation_audit.csv: every audit source
must appear exactly once per frozen class, and no extra source may appear.
"""
from __future__ import annotations

import csv
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEFAULT = ROOT / "ledger" / "class_coverage.csv"
AUDIT = ROOT / "ledger" / "citation_audit.csv"

COLUMNS = ["row_id", "source_id", "citation", "authors", "year", "venue", "doi", "arxiv_id", "url",
           "audit_status", "audit_verdict", "class_id", "coverage", "role", "theorem_ids",
           "conclusion_types", "entry_kinds", "strongest_conclusion_type", "exact_theorem",
           "theorem_locator", "genericity", "regularity", "assumptions", "scope_flags", "falsifier",
           "evidence_basis", "verification_status", "ledger_bound_classes", "registry_crosscheck",
           "notes"]
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
COVERAGE = ["covered", "partial", "none", "unassessed"]
COVERED_CT = {"theorem", "counterexample"}
MERGED = re.compile(r"C\^?0\s*(or|/)\s*C\^?2|C\^?2\s*(or|/)\s*C\^?0", re.I)
TID = re.compile(r"^[A-Z]-\d{3}$")


def check(path: Path, audit_path: Path | None = AUDIT) -> list[str]:
    errs: list[str] = []
    with path.open(newline="") as f:
        rd = csv.DictReader(f)
        if rd.fieldnames != COLUMNS:
            return [f"header mismatch:\n  got      {rd.fieldnames}\n  expected {COLUMNS}"]
        rows = list(rd)
    if not rows:
        return ["no data rows"]
    seen = set()
    for r in rows:
        rid = r["row_id"]

        def bad(msg, rid=rid):
            errs.append(f"{rid}: {msg}")

        if rid in seen:
            bad("duplicate row_id")
        seen.add(rid)
        if not re.fullmatch(r"CC-\d{4}", rid or ""):
            bad(f"bad row_id format {rid!r}")
        if not re.fullmatch(r"SRC-\d{3}", r["source_id"] or ""):
            bad(f"bad source_id {r['source_id']!r}")
        if r["class_id"] not in CLASSES:
            bad(f"unknown class_id {r['class_id']!r}")
        if r["coverage"] not in COVERAGE:
            bad(f"unknown coverage {r['coverage']!r}")
        if r["coverage"] in {"covered", "partial"}:
            if len(r["exact_theorem"].strip()) < 20:
                bad("covered/partial without the exact theorem that covers it")
            if not r["evidence_basis"].startswith("ledger_theorem"):
                bad(f"covered/partial with non-ledger evidence_basis {r['evidence_basis']!r}")
        if r["coverage"] == "covered":
            if r["strongest_conclusion_type"] not in COVERED_CT:
                bad(f"covered with strongest_conclusion_type={r['strongest_conclusion_type']!r}")
            if not r["theorem_ids"].strip():
                bad("covered without theorem_ids")
            if not r["falsifier"].strip():
                bad("covered without next falsifier")
        if r["coverage"] == "none":
            if r["theorem_ids"].strip() or r["exact_theorem"].strip():
                bad("none row carries theorem content")
        if r["coverage"] == "unassessed":
            if r["role"] != "unresolved_mapping" or r["theorem_ids"].strip() \
                    or r["evidence_basis"] != "registry_only_unmapped":
                bad("unassessed row is not in the canonical unmapped form")
        FLAGS = {"spherical_symmetry", "charged_maxwell", "cosmological_constant", "extra_matter",
                 "linear_only"}
        if r["scope_flags"] != "none" and not set(r["scope_flags"].split(" | ")) <= FLAGS:
            bad(f"unknown scope_flags {r['scope_flags']!r}")
        for tid in [t.strip() for t in r["theorem_ids"].split("|") if t.strip()]:
            if not TID.fullmatch(tid):
                bad(f"bad theorem id {tid!r}")
        for col, val in r.items():
            if val and MERGED.search(val):
                bad(f"merged C^0/C^2 token in column {col}: {val[:80]!r}")

    # structural completeness against the audit registry
    if audit_path and audit_path.exists():
        want = {a["citation_id"] for a in csv.DictReader(audit_path.open(newline=""))}
        got = {r["source_id"] for r in rows}
        if want - got:
            errs.append(f"missing sources (no rows at all): {sorted(want - got)}")
        if got - want:
            errs.append(f"unknown sources not in audit registry: {sorted(got - want)}")
        pairs = Counter((r["source_id"], r["class_id"]) for r in rows)
        for sid in sorted(want):
            for cls in CLASSES:
                n = pairs.get((sid, cls), 0)
                if n != 1:
                    errs.append(f"source/class pair {sid}/{cls} appears {n} times (want exactly 1)")
    return errs


def self_test() -> int:
    if not DEFAULT.exists():
        print("SKIP self-test: real csv not built yet")
        return 0
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "cc.csv"
        rows = list(csv.DictReader(DEFAULT.open(newline="")))
        audit = AUDIT if AUDIT.exists() else None
        # synthetic covered row is unnecessary here: the real matrix has covered cells.
        assert any(r["coverage"] == "covered" for r in rows), "no covered row to mutate"

        def write(rs):
            with tmp.open("w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=COLUMNS)
                w.writeheader()
                w.writerows(rs)

        def first(pred):
            return next(i for i, r in enumerate(rows) if pred(r))

        i = first(lambda r: r["coverage"] == "covered")
        mutants = []
        m = [dict(r) for r in rows]; m[i]["class_id"] = "AF-SCC-C0ORC2"; mutants.append(("M1 unknown class id", m))
        m = [dict(r) for r in rows]; m[i]["exact_theorem"] = ""; mutants.append(("M2 covered with empty theorem", m))
        m = [dict(r) for r in rows]; m[0]["notes"] = "leaks C0 or C2"; mutants.append(("M3 merged regularity token", m))
        j = first(lambda r: r["coverage"] == "unassessed")
        m = [dict(r) for r in rows]; m[j]["theorem_ids"] = "T-999"; mutants.append(("M4 unassessed with theorem id", m))
        k = first(lambda r: r["coverage"] == "none")
        m = [dict(r) for r in rows]; m[k]["exact_theorem"] = "x" * 40; mutants.append(("M5 none with theorem content", m))
        m = [dict(r) for r in rows]; m.pop(first(lambda r: r["coverage"] == "covered")); mutants.append(("M6 missing source/class pair", m))
        m = [dict(r) for r in rows]; m[i]["strongest_conclusion_type"] = "open_problem"; mutants.append(("M7 covered by open problem", m))
        m = [dict(r) for r in rows]; m[i]["falsifier"] = ""; mutants.append(("M8 covered without falsifier", m))

        ok = True
        write([dict(r) for r in rows])
        errs = check(tmp, audit)
        print(f"[{'PASS' if not errs else 'FAIL'}] clean fixture accepted" + ("" if not errs else f": {errs[:2]}"))
        ok &= not errs
        for name, mrows in mutants:
            write(mrows)
            errs = check(tmp, audit)
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
    rows = list(csv.DictReader(path.open(newline="")))
    print(f"VALID {path}: {len(rows)} rows, sources={len({r['source_id'] for r in rows})}")
    for cls in CLASSES:
        c = Counter(r["coverage"] for r in rows if r["class_id"] == cls)
        print(f"  {cls:20s} covered={c['covered']:3d} partial={c['partial']:3d} "
              f"none={c['none']:3d} unassessed={c['unassessed']:3d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
