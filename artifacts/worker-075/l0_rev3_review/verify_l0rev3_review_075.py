#!/usr/bin/env python3
"""Independent re-check of report.json produced by run_l0rev3_review_075.py.

Written separately from the harness (no imports from it). Re-derives the headline numbers from
ledger/theorems.jsonl and ledger/citation_audit.csv, compares them with the report, and runs a
tamper control: a mutated copy of the report must be rejected.

Exit 0 iff every re-derived value equals the report, the inputs still hash at the pinned values,
the report's own checks are internally consistent with its verdict, and the tamper control fires.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
LEDGER = ROOT / "ledger" / "theorems.jsonl"
AUDIT = ROOT / "ledger" / "citation_audit.csv"
REPORT = HERE / "report.json"
PIN_LEDGER = "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"
PIN_AUDIT = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
MULTI_EXPECTED = {"D-004", "D-005", "T-303", "T-305", "T-402", "T-515", "T-526", "T-528"}
FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def foreign_tokens(obj, acc):
    if isinstance(obj, str):
        for m in re.findall(r"AF-[A-Z0-9-]+", obj):
            if not any(m == f or f.startswith(m) for f in FROZEN):
                acc.append(m)
    elif isinstance(obj, dict):
        for v in obj.values():
            foreign_tokens(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            foreign_tokens(v, acc)


def derive():
    rows = [json.loads(x) for x in LEDGER.read_text().splitlines() if x.strip()]
    audit = {r["citation_id"]: r for r in csv.DictReader(AUDIT.open())}
    out = {
        "ledger_sha": digest(LEDGER),
        "audit_sha": digest(AUDIT),
        "rows": len(rows),
        "unique_ids": len({r["theorem_id"] for r in rows}),
        "content_status": {},
        "review_status": {},
        "retired_axis_rows": 0,
        "multi_class": sorted(r["theorem_id"] for r in rows if len(r.get("class_ids", [])) > 1),
        "theorem_rows": sum(1 for r in rows if r.get("conclusion_type") == "theorem"),
        "theorem_rows_with_artifact_refs_field": sum(
            1 for r in rows if r.get("conclusion_type") == "theorem" and "artifact_refs" in r),
        "rows_without_unresolved": sum(1 for r in rows if not r.get("unresolved")),
        "cited_sources": len({s for r in rows for s in (r.get("source_ids") or [])}),
        "unresolved_audit_rows": sum(1 for a in audit.values()
                                     if a.get("resolver_result") != "resolved"),
        "foreign_tokens": [],
    }
    for r in rows:
        out["content_status"][r["content_status"]] = out["content_status"].get(r["content_status"], 0) + 1
        out["review_status"][r["review_status"]] = out["review_status"].get(r["review_status"], 0) + 1
        if any(k in r for k in ("status", "validation_status", "supports_claim")):
            out["retired_axis_rows"] += 1
        foreign_tokens(r, out["foreign_tokens"])
    return out


def compare(rep, d):
    problems = []
    checks = {c["id"]: c for c in rep["checks"]}
    if d["ledger_sha"] != PIN_LEDGER or d["audit_sha"] != PIN_AUDIT:
        problems.append("input hash drift")
    expectations = {
        "rows": 62, "unique_ids": 62, "theorem_rows": 30,
        "theorem_rows_with_artifact_refs_field": 0, "rows_without_unresolved": 0,
        "cited_sources": 92, "unresolved_audit_rows": 0, "retired_axis_rows": 0,
        "foreign_tokens": [],
    }
    for k, v in expectations.items():
        if d[k] != v:
            problems.append(f"derived {k}={d[k]} expected {v}")
        if rep["inputs"].get(k) is not None and rep["inputs"][k] != d[k]:
            problems.append(f"report.inputs.{k}={rep['inputs'][k]} != derived {d[k]}")
    if d["content_status"] != {"verified": 50, "provisional": 11, "rejected": 1}:
        problems.append(f"content_status={d['content_status']}")
    if d["review_status"] != {"not_independently_reviewed": 62}:
        problems.append(f"review_status={d['review_status']}")
    if set(d["multi_class"]) != MULTI_EXPECTED:
        problems.append(f"multi_class set {d['multi_class']}")
    if [m["theorem_id"] for m in rep["multi_class_rows"]] != sorted(MULTI_EXPECTED):
        problems.append("report.multi_class_rows does not match the derived set")
    if rep["theorem_rows"]["count"] != d["theorem_rows"]:
        problems.append("report.theorem_rows.count mismatch")
    if checks["C05-FROZEN-TOKENS"]["ok"] != (not d["foreign_tokens"]):
        problems.append("C05 not consistent with derived foreign tokens")
    hard_fail = [c["id"] for c in rep["checks"] if c.get("hard") and not c.get("ok")]
    if hard_fail != rep["verdict"]["hard_failures"]:
        problems.append(f"verdict.hard_failures={rep['verdict']['hard_failures']} != hard checks {hard_fail}")
    expected_verdict = "revise" if hard_fail else "accept"
    if rep["verdict"]["verdict"] != expected_verdict:
        problems.append("verdict is not derivable from the hard checks")
    if not rep.get("controls_all_pass"):
        problems.append("report says controls did not all pass")
    if not rep.get("snapshot_stable"):
        problems.append("report says snapshot was not stable")
    return problems


def selftest(rep, d):
    """Tamper control: three mutated reports must each be rejected."""
    fired = []
    for label, mutate in (
        ("count", lambda r: r["inputs"].__setitem__("rows", 61)),
        ("multi", lambda r: r["multi_class_rows"].pop()),
        ("verdict", lambda r: r["verdict"].__setitem__("verdict", "revise")),
    ):
        m = json.loads(json.dumps(rep))
        mutate(m)
        fired.append(bool(compare(m, d)))
    return fired


def main():
    if not REPORT.exists():
        print("report.json missing", file=sys.stderr)
        return 2
    rep = json.loads(REPORT.read_text())
    d = derive()
    problems = compare(rep, d)
    fired = selftest(rep, d)
    print(f"derived rows={d['rows']} theorem_rows={d['theorem_rows']} "
          f"multi_class={len(d['multi_class'])} cited={d['cited_sources']} "
          f"foreign={d['foreign_tokens']}")
    print(f"tamper control fired: {fired}")
    if problems:
        print("MISMATCH:")
        for p in problems:
            print("  -", p)
        return 1
    if not all(fired):
        print("tamper control did not fire on all mutations", file=sys.stderr)
        return 1
    print("VERIFIED: report reproduces from the pinned inputs; tamper control fires 3/3")
    return 0


if __name__ == "__main__":
    sys.exit(main())
