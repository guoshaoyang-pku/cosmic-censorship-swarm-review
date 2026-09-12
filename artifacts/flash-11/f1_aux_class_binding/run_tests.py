#!/usr/bin/env python3
"""Acceptance test for the class-binding linter (draft, unverified).

Runs every fixture in fixtures/ against check_schema.check() and compares the
result with fixtures/EXPECTATIONS.json. Adversarial fixtures are *expected to
escape* and are reported as falsifier evidence, not as suite failures.

Also runs a null control: 100 deterministic random mapping documents must all be
rejected (guards against an ACCEPT-by-default detector).

Exit status: 0 iff all non-escape expectations hold and the null control passes.
Writes evidence/results.json.
"""
from __future__ import annotations

import hashlib
import json
import platform
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import check_schema

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
EV = HERE / "evidence"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def null_control(n: int = 100, seed: int = 11) -> tuple[int, list[str]]:
    rng = random.Random(seed)
    vocab = ["class_id", "AF-WCC-VAC-GEN", "theorem", "C^2", "vacuum", "forall", "exists", 4, True, None, "", [], {}]
    escapes: list[str] = []
    for i in range(n):
        doc = {f"k{rng.randint(0, 5)}": rng.choice(vocab) for _ in range(rng.randint(1, 6))}
        res = check_schema.check(doc, f"<null-{i}>")
        if res.verdict != "REJECT":
            escapes.append(json.dumps(doc, sort_keys=True))
    return len(escapes), escapes


def main() -> int:
    expectations = json.loads((FIX / "EXPECTATIONS.json").read_text(encoding="utf-8"))
    records = []
    failures: list[str] = []
    counts = {"pass": 0, "FAIL": 0, "escape_confirmed": 0, "escape_closed": 0}

    for name in sorted(expectations):
        path = FIX / name
        exp = expectations[name]
        doc = check_schema.load_document(path)
        res = check_schema.check(doc, str(path)).to_dict()
        if exp.get("kind") == "expected_escape":
            outcome = "escape_confirmed" if res["verdict"] == "ACCEPT" else "escape_closed"
        elif exp["verdict"] == "ACCEPT":
            outcome = "pass" if res["verdict"] == "ACCEPT" else "FAIL"
        else:
            outcome = "pass" if (res["verdict"] == "REJECT" and all(c in res["failed_codes"] for c in exp.get("must_include", []))) else "FAIL"
        counts[outcome] += 1
        if outcome == "FAIL":
            failures.append(f"{name}: expected {exp['verdict']} including {exp.get('must_include')}, got {res['verdict']} {res['failed_codes']}")
        records.append(
            {
                "fixture": name,
                "base": exp.get("base"),
                "expected": exp,
                "actual_verdict": res["verdict"],
                "actual_failed_codes": res["failed_codes"],
                "outcome": outcome,
                "sha256": sha256(path),
                "note": exp.get("note", ""),
            }
        )

    n_null_escapes, null_examples = null_control()
    if n_null_escapes:
        failures.append(f"null control: {n_null_escapes}/100 random mappings escaped")

    report = {
        "artifact": "f1_aux_class_binding",
        "status": "draft-unverified",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": platform.python_version(),
        "checker_sha256": sha256(HERE / "check_schema.py"),
        "expectations_sha256": sha256(FIX / "EXPECTATIONS.json"),
        "counts": counts,
        "null_control": {"n": 100, "escapes": n_null_escapes, "examples": null_examples[:3]},
        "failures": failures,
        "records": records,
    }
    EV.mkdir(exist_ok=True)
    (EV / "results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"fixtures: {counts['pass']} pass, {counts['FAIL']} FAIL, "
          f"{counts['escape_confirmed']} escape_confirmed, {counts['escape_closed']} escape_closed")
    print(f"null control: {n_null_escapes}/100 escapes")
    for r in records:
        if r["outcome"] != "pass" or r["expected"].get("kind"):
            print(f"  {r['outcome']:18s} {r['fixture']}  {r['actual_verdict']} {r['actual_failed_codes']}")
    if failures:
        print("SUITE FAIL")
        for f in failures:
            print("  -", f)
        return 1
    print("SUITE PASS (adversarial escapes are recorded in evidence/results.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
