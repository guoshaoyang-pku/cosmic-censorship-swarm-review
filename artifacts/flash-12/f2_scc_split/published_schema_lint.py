#!/usr/bin/env python3
"""Read-only separation lint for the published SCC C^2 / C^0 schemas.

Independent A1-support check by deepseek-flash-12 (node F2 domain, no completion claim).
It does NOT replace the G-FORM reviewers 17/18, and it does not judge physics.

Checks:
  S1 class ids are the two frozen SCC classes, distinct
  S2/S3 each document's conclusion carries exactly its own regularity token (C^2 / C^0) and
        no composite token ("C0 or C2", "C2/C0", ...) anywhere in its conclusion subtree
  S4 visibility role is excluded from both conclusions
  S5 no POSITIVE visibility / I+-completeness assertion inside the conclusion subtree.
     Mentions inside explicit forbidden / anti-scope / non-goal / unresolved blocks are
     skipped: naming WCC content in order to forbid it is correct, not leakage.  This
     mirrors the audit-regex false positive found earlier on the map label "AF-SCC C2/C0 split".
  S6 the C^0 document records the one-way implication to the C^2 class
  S7 unresolved citations remain marked unresolved in both documents

Usage: python3 published_schema_lint.py
Writes artifacts/flash-12/f2_scc_split/published_schema_lint.json
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
C2_PATH = REPO / "schemas" / "af_scc_c2_vacuum.yaml"
C0_PATH = REPO / "schemas" / "af_scc_c0_vacuum.yaml"

C0 = r"C\s*\^?\s*\{?\s*0\s*\}?"
C2 = r"C\s*\^?\s*\{?\s*2\s*\}?"
JOIN = r"(?:or|and|/|,|\\cup|∪)"
COMPOSITE = re.compile(rf"(?:{C0}\s*{JOIN}\s*{C2})|(?:{C2}\s*{JOIN}\s*{C0})", re.I)
VISIBILITY = re.compile(r"visible from I\+|I\+\s+complete|asymptotic predictability", re.I)
SKIP_KEY = re.compile(r"forbidden|anti_scope|non_goal|must_not|unresolved|why_absent|excluded|"
                      r"not_in_conclusion|no_go|open_status|neighbouring|known_obstruction", re.I)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def walk(obj, path=""):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[{i}]")


def main() -> int:
    c2 = yaml.safe_load(C2_PATH.read_text())
    c0 = yaml.safe_load(C0_PATH.read_text())
    checks = []

    def rec(cid, ok, detail):
        checks.append({"id": cid, "status": "pass" if ok else "fail", "detail": detail})

    rec("S1.class_ids",
        c2.get("class_id") == "AF-SCC-C2-VAC-GEN" and c0.get("class_id") == "AF-SCC-C0-VAC-GEN",
        f"{c2.get('class_id')} / {c0.get('class_id')}")

    c2_concl = json.dumps(c2.get("conclusion", {}), default=str)
    c0_concl = json.dumps(c0.get("conclusion", {}), default=str)
    c2_ext = str(c2.get("conclusion", {}).get("extension_class", ""))
    c0_ext = str(c0.get("regularity", {}).get("extension_regularity", ""))
    rec("S2.c2_regularity", "C^2" in c2_ext and not COMPOSITE.search(c2_concl),
        f"extension_class={c2_ext!r} composite_in_conclusion={bool(COMPOSITE.search(c2_concl))}")
    rec("S3.c0_regularity", c0_ext.upper().replace("^", "").startswith("C0") and not COMPOSITE.search(c0_concl),
        f"extension_regularity={c0_ext!r} composite_in_conclusion={bool(COMPOSITE.search(c0_concl))}")

    rec("S4.visibility_roles",
        c2.get("visibility", {}).get("role") == "not_used_in_conclusion"
        and c0.get("visibility", {}).get("role") in {"not_in_conclusion", "not_used_in_conclusion"},
        f"{c2.get('visibility', {}).get('role')} / {c0.get('visibility', {}).get('role')}")

    positive_hits = [(p, s) for p, s in walk(c0.get("conclusion", {}), "conclusion")
                     if VISIBILITY.search(s) and not SKIP_KEY.search(p)]
    composite_hits = [(p, s) for p, s in walk(c0.get("conclusion", {}), "conclusion")
                      if COMPOSITE.search(s) and not SKIP_KEY.search(p)]
    rec("S5.no_positive_visibility_in_c0_conclusion", not positive_hits and not composite_hits,
        f"positive_visibility_hits={len(positive_hits)} composite_hits={len(composite_hits)} "
        f"(forbidden/anti-scope blocks are skipped by design)")

    ledger = json.dumps(c0.get("implication_ledger", c0.get("class_components", {})), default=str)
    rec("S6.c0_refers_to_c2", "AF-SCC-C2-VAC-GEN" in ledger or "C2" in ledger, ledger[:120])

    rec("S7.citations_unresolved",
        bool(c2.get("unresolved_citations")) and bool(c0.get("unresolved_items")),
        f"c2_unresolved={len(c2.get('unresolved_citations', []))} "
        f"c0_unresolved={len(c0.get('unresolved_items', []))}")

    out = {
        "lint": "artifacts/flash-12/f2_scc_split/published_schema_lint.py",
        "checked_at": datetime.now(CST).isoformat(timespec="seconds"),
        "schemas": {str(C2_PATH.relative_to(REPO)): sha(C2_PATH),
                    str(C0_PATH.relative_to(REPO)): sha(C0_PATH)},
        "checks": checks,
        "failed": [c for c in checks if c["status"] == "fail"],
        "verdict": "pass" if all(c["status"] == "pass" for c in checks) else "fail",
        "scope": ("read-only separation lint by deepseek-flash-12; not a substitute for G-FORM "
                  "reviewers 17/18, not a physics review, no node completion claim"),
        "design_note": ("lexical lints must exclude forbidden/anti-scope blocks from leakage scans; "
                        "the first version of S5 false-positived on the explicit "
                        "conclusion.forbidden_strengthenings entry 'I+ completeness ... (WCC content)'"),
    }
    (HERE / "published_schema_lint.json").write_text(json.dumps(out, indent=2, sort_keys=True))
    print(json.dumps({"verdict": out["verdict"], "failed": out["failed"],
                      "schemas": out["schemas"]}, indent=2))
    return 0 if out["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
