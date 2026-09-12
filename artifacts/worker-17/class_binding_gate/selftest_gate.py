#!/usr/bin/env python3
"""Self-test for class_binding_gate.py: proves the gate has teeth on mutants.

Asserts, on deterministically generated fixtures in fixtures/:
  1. every good fixture PASSES with zero violations;
  2. every mutant fixture FAILS, with the hand-declared expected code present
     (a mutant that slips through is reported as a silent mutant);
  3. the mutant suite exercises every rule code the gate implements
     (an unexercised rule is reported as uncovered).

Writes selftest_report.json next to this file and exits non-zero on any failure.
This is the evidence artifact for the acceptance test in ../PROPOSAL.md.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import class_binding_gate as gate  # noqa: E402  (path set above)

FIX = HERE / "fixtures"
REPORT = HERE / "selftest_report.json"


def codes_for(name):
    doc = gate.load_document(FIX / name)
    violations = gate.check(doc, source=name)
    return sorted({v["code"] for v in violations}), violations


def main():
    expected = json.loads((FIX / "EXPECTED.json").read_text(encoding="utf-8"))
    failures = []
    rows = []
    observed_union = set()

    for name in expected["good"]:
        codes, violations = codes_for(name)
        ok = not violations
        rows.append({"fixture": name, "kind": "good", "observed": codes, "ok": ok})
        if not ok:
            failures.append(f"{name}: expected zero violations, got {codes}")

    for name, declared in sorted(expected["mutants"].items()):
        codes, _ = codes_for(name)
        observed_union.update(codes)
        missing = sorted(set(declared) - set(codes))
        ok = bool(codes) and not missing
        rows.append(
            {
                "fixture": name,
                "kind": "mutant",
                "expected": sorted(declared),
                "observed": codes,
                "ok": ok,
            }
        )
        if not codes:
            failures.append(f"{name}: SILENT MUTANT - no violation raised")
        elif missing:
            failures.append(f"{name}: expected codes {missing} not observed in {codes}")

    uncovered = sorted(set(gate.RULE_CODES) - observed_union)
    if uncovered:
        failures.append(f"uncovered rule codes (no mutant exercises them): {uncovered}")

    report = {
        "gate": "class_binding_gate.py",
        "fixtures": str(FIX),
        "good_count": len(expected["good"]),
        "mutant_count": len(expected["mutants"]),
        "rule_codes_implemented": list(gate.RULE_CODES),
        "rule_codes_exercised": sorted(observed_union),
        "uncovered_rule_codes": uncovered,
        "silent_mutants": [
            row["fixture"]
            for row in rows
            if row["kind"] == "mutant" and not row["observed"]
        ],
        "passed": not failures,
        "failures": failures,
        "rows": rows,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    width = max(len(row["fixture"]) for row in rows) if rows else 0
    print(f"{'fixture'.ljust(width)}  kind    result  observed")
    for row in rows:
        result = "ok" if row["ok"] else "FAIL"
        print(
            f"{row['fixture'].ljust(width)}  {row['kind']:<6}  {result:<6}  "
            f"{','.join(row['observed']) or '-'}"
        )
    print(
        f"\ngood: {report['good_count']}  mutants: {report['mutant_count']}  "
        f"rules exercised: {len(observed_union)}/{len(gate.RULE_CODES)}"
    )
    if failures:
        print("\nFAILURES")
        for failure in failures:
            print(f"  - {failure}")
        print(f"\nwrote {REPORT}")
        return 1
    print(f"\nSELFTEST PASS - wrote {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
