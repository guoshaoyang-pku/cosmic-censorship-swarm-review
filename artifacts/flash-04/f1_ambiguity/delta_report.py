#!/usr/bin/env python3
"""Delta report: r3 (7a3e1f93 worker draft) -> frozen rev4 (f512af5f).

The lead asked for "deltas only" after the freeze. This compares the two bound
runner reports per test and classifies each row:

* closed        - was open, now determinate
* reclassified  - still open, but the reason/strength changed (e.g. accepted obligation)
* renamed       - same status, deciding path moved to a rev4 field
* unchanged     - no change

Output: `frozen_rev4_delta_report.json`.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE / "r3_7a3e1f93_report.json"
NEW = HERE / "ambiguity_report.json"
OUT = HERE / "frozen_rev4_delta_report.json"


def digest(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main() -> int:
    old = json.loads(OLD.read_text())
    new = json.loads(NEW.read_text())
    old_rows = {r["test_id"]: r for r in old["rows"]}
    new_rows = {r["test_id"]: r for r in new["rows"]}
    if set(old_rows) != set(new_rows):
        raise SystemExit("test sets differ between baseline and frozen reports")

    deltas = []
    counts = {"closed": 0, "finding_closed": 0, "reclassified": 0, "renamed": 0,
              "unchanged": 0, "opened": 0, "still_open": 0}
    still_open = []
    for tid in sorted(new_rows):
        o, n = old_rows[tid], new_rows[tid]
        kind = None
        if o["open"] and not n["open"]:
            kind = "closed"
        elif not o["open"] and n["open"]:
            kind = "opened"
        elif o["open"] and n["open"]:
            kind = "reclassified" if (
                o["falsifier_strength"] != n["falsifier_strength"]
                or o["why_open"] != n["why_open"]) else "unchanged"
        elif (o["falsifier_strength"] != "decided"
              and n["falsifier_strength"].startswith("decided")):
            kind = "finding_closed"
        elif o["resolved_path"] != n["resolved_path"] or o["falsifier_strength"] != n["falsifier_strength"]:
            kind = "renamed"
        else:
            kind = "unchanged"
        counts[kind] += 1
        if n["open"]:
            still_open.append(tid)
            counts["still_open"] += 1
        if kind != "unchanged":
            deltas.append({
                "test_id": tid,
                "kind": kind,
                "open_before": o["open"],
                "open_after": n["open"],
                "strength_before": o["falsifier_strength"],
                "strength_after": n["falsifier_strength"],
                "field_before": o["resolved_path"],
                "field_after": n["resolved_path"],
                "schema_open_expected_after": n["schema_open_expected"],
                "expectation_match_after": n["expectation_match"],
            })

    report = {
        "report": "f1_rev4_delta",
        "baseline": {
            "path": str(OLD.relative_to(HERE.parents[2])),
            "schema_sha256": old["schema_sha256"],
            "tests_sha256": old["tests_sha256"],
            "open": old["summary"]["open_findings"],
            "attack_findings": old["summary"]["attack_findings"],
        },
        "frozen": {
            "path": str(NEW.relative_to(HERE.parents[2])),
            "schema_sha256": new["schema_sha256"],
            "tests_sha256": new["tests_sha256"],
            "schema_drift": new["schema_drift"],
            "open": new["summary"]["open_findings"],
            "attack_findings": new["summary"]["attack_findings"],
            "structural": new["summary"]["structural"],
            "schema_unresolved_items": new.get("schema_unresolved_items", []),
        },
        "counts": counts,
        "still_open": still_open,
        "deltas": deltas,
        "closure_note": ("The four closures are rule/field changes: AMB-07 set-level membership "
                         "ruling, AMB-08 slice narrowed to R^3, AMB-09 ambient= data space, "
                         "AMB-10 alias-frozen tokens. The four remaining rows are declared "
                         "obligations (AMB-01/02/03/15), not silent gaps."),
        "non_claim": ("Delta accounting only; it does not verify the rulings or the physics. "
                      "frozen schema sha256 is the FROZEN.json pin at comparison time; the "
                      "23:33:37 message cited 17873b9d, superseded by f512af5f."),
    }
    report["report_digest"] = digest(report)
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("counts:", json.dumps(counts))
    print("still_open:", still_open)
    for d in deltas:
        print(f"  {d['test_id']}: {d['kind']:13s} open {d['open_before']}->{d['open_after']} "
              f"{d['strength_before']} -> {d['strength_after']}")
    print("digest:", report["report_digest"][:16])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
