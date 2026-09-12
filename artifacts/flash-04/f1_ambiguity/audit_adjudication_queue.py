#!/usr/bin/env python3
"""Cross-check the F1 ambiguity suite against F1's own `adjudication_queue`.

The schema author consumed an earlier 16-test version of the suite and recorded
per-probe decisions in `adjudication_queue`.  This script checks, against the
frozen snapshot:

* coverage: which suite tests appear in the queue, which do not;
* leaf agreement: does the queue's `deciding_leaf` equal the suite's
  `deciding_field` (or one of its alternates);
* queue-only items (tests referenced by the queue that the suite does not have);
* duplicate queue entries.

Output: `adjudication_crosscheck.json` (deterministic except for no timestamps).
Exit codes: 0 cross-check ran; 2 suite/queue unreadable or queue malformed.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TESTS = ROOT / "schemas" / "f1_falsifier_tests.jsonl"
SNAPSHOT = HERE / "schema_snapshots" / "af_wcc_vacuum.f512af5f.yaml"
OUT = HERE / "adjudication_crosscheck.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    try:
        import yaml
    except ImportError:
        print("pyyaml required", file=sys.stderr)
        return 2
    if not TESTS.exists() or not SNAPSHOT.exists():
        print("suite or snapshot missing", file=sys.stderr)
        return 2
    tests = [json.loads(line) for line in TESTS.read_text().splitlines() if line.strip()]
    doc = yaml.safe_load(SNAPSHOT.read_text())
    queue = doc.get("adjudication_queue")
    if not isinstance(queue, dict):
        print("snapshot has no adjudication_queue", file=sys.stderr)
        return 2
    # rev3 used items[]; rev4 uses open_rows[] plus adjudication_ref
    raw_entries = queue.get("items")
    queue_format = "items"
    if not isinstance(raw_entries, list):
        raw_entries = queue.get("open_rows")
        queue_format = "open_rows"
    if not isinstance(raw_entries, list):
        raw_entries = []
        queue_format = "none"
    items: dict[str, dict] = {}
    duplicates = []
    for entry in raw_entries:
        if not isinstance(entry, dict) or not entry.get("test"):
            continue
        tid = entry["test"]
        if tid in items:
            duplicates.append(tid)
        items[tid] = entry

    rows = []
    for t in tests:
        tid = t["test_id"]
        qi = items.get(tid)
        field = t.get("deciding_field")
        alternates = t.get("deciding_field_alternates") or []
        if qi is None:
            rows.append({
                "test_id": tid,
                "in_queue": False,
                "suite_leaf": field,
                "queue_leaf": None,
                "leaf_match": None,
                "leaf_match_via_alternate": False,
                "queue_decision": None,
                "queue_review_question": None,
                "action": ("add_to_queue" if t.get("schema_open_expected")
                           else "not_required_control"),
            })
            continue
        leaf = qi.get("deciding_leaf")
        match = leaf == field
        via_alt = (not match) and leaf in alternates
        rows.append({
            "test_id": tid,
            "in_queue": True,
            "suite_leaf": field,
            "queue_leaf": leaf,
            "leaf_match": match,
            "leaf_match_via_alternate": bool(via_alt),
            "queue_decision": qi.get("schema_decision"),
            "queue_review_question": qi.get("review_question"),
            "action": "" if (match or via_alt) else "name_both_leaves",
        })

    suite_ids = {t["test_id"] for t in tests}
    queue_only = sorted(set(items) - suite_ids)
    summary = {
        "suite_tests": len(tests),
        "queue_items": len(items),
        "queue_duplicate_ids": sorted(set(duplicates)),
        "in_queue": sum(1 for r in rows if r["in_queue"]),
        "exact_leaf_match": sum(1 for r in rows if r["leaf_match"]),
        "alternate_leaf_match": sum(1 for r in rows if r["leaf_match_via_alternate"]),
        "leaf_mismatch": sum(1 for r in rows if r["in_queue"] and not r["leaf_match"]
                             and not r["leaf_match_via_alternate"]),
        "suite_tests_not_in_queue": [r["test_id"] for r in rows if not r["in_queue"]],
        "queue_only_tests": queue_only,
        "actions": {r["test_id"]: r["action"] for r in rows if r["action"]},
    }
    report = {
        "checker": "f1_adjudication_crosscheck",
        "version": "0.1.0",
        "author": "deepseek-flash-04",
        "suite_path": str(TESTS.relative_to(ROOT)),
        "suite_sha256": sha256_file(TESTS),
        "snapshot_path": str(SNAPSHOT.relative_to(ROOT)),
        "snapshot_sha256": sha256_file(SNAPSHOT),
        "queue_format": queue_format,
        "queue_note": queue.get("note"),
        "adjudication_ref": queue.get("adjudication_ref"),
        "summary": summary,
        "rows": rows,
        "non_claim": ("Coverage/attribution check only. It does not judge whether a queue decision is "
                      "physically correct; those decisions remain A1 adjudication items."),
    }
    report["report_digest"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"crosscheck: suite={summary['suite_tests']} queue={summary['queue_items']} "
          f"in_queue={summary['in_queue']} exact={summary['exact_leaf_match']} "
          f"alt={summary['alternate_leaf_match']} mismatch={summary['leaf_mismatch']}")
    print(f"not_in_queue={summary['suite_tests_not_in_queue']}")
    print(f"actions={summary['actions']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
