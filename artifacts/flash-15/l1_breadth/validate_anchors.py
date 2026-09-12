#!/usr/bin/env python3
"""AT1-AT4 checker for artifacts/flash-15/l1_breadth/anchors.jsonl (proposal-support packet)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FROZEN = {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"}
ROLE = {"supporting", "falsifier", "boundary_case", "open"}
STATUS = {"verified_primary", "partial", "unresolved", "rejected"}
MATCH = {"exact", "narrower", "broader", "mismatch"}


def main() -> int:
    rows = [json.loads(l) for l in (HERE / "anchors.jsonl").read_text().splitlines() if l.strip()]
    errs = []
    classes, statuses = set(), {}
    for r in rows:
        rid = r.get("row_id", "?")
        if r.get("class_id") not in FROZEN:
            errs.append(f"{rid}: AT1 class_id not frozen")
        classes.add(r.get("class_id"))
        if r.get("result_role") not in ROLE:
            errs.append(f"{rid}: AT1 bad result_role")
        if r.get("scope_match") not in MATCH:
            errs.append(f"{rid}: AT1 bad scope_match")
        if r.get("verification_status") not in STATUS:
            errs.append(f"{rid}: AT3 bad verification_status")
        statuses[r.get("verification_status")] = statuses.get(r.get("verification_status"), 0) + 1
        ids = r.get("identifiers") or {}
        fetched = r.get("fetched") or {}
        if not ids or not fetched.get("retrieved_at") or not fetched.get("url"):
            errs.append(f"{rid}: AT2 provenance incomplete")
        if not r.get("scope_quote"):
            errs.append(f"{rid}: AT2 empty scope_quote")
        # AT1 regularity/class consistency
        cid, reg = r.get("class_id", ""), r.get("regularity", "")
        if "-C0-" in cid and reg not in ("C0", "n/a"):
            errs.append(f"{rid}: AT1 regularity {reg} leaks into C0 class")
        if "-C2-" in cid and reg not in ("C2", "n/a"):
            errs.append(f"{rid}: AT1 regularity {reg} leaks into C2 class")
        # AT4 falsifier completeness
        if r.get("result_role") == "supporting" and not r.get("falsifier"):
            errs.append(f"{rid}: AT4 supporting row without falsifier")
    # AT4 every class has a falsifier or boundary_case row
    per_class = {c: [] for c in FROZEN}
    for r in rows:
        per_class.setdefault(r["class_id"], []).append(r["result_role"])
    for c, roles in per_class.items():
        if c in FROZEN and not ({"falsifier", "boundary_case"} & set(roles)):
            errs.append(f"{c}: AT4 no falsifier/boundary_case row")
    print(json.dumps({
        "rows": len(rows), "classes_covered": sorted(classes), "by_status": statuses,
        "by_class": {c: len(v) for c, v in sorted(per_class.items())},
        "errors": errs, "verdict": "PASS" if not errs else "FAIL",
    }, indent=2))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
