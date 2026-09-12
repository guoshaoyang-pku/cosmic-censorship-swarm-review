#!/usr/bin/env python3
"""W050-L0-INDEPENDENT-SPOTCHECK-04 -- two-pass stability comparison.

Compares fetch_evidence.json (pass 1) with fetch_evidence_recheck.json (pass 2) row by row:
same matched locator, same status, same fetched title, same title verdict. Writes
recheck_summary.json. Exit 0 if every row is stable and pins held in both passes, 1 otherwise,
3 if either evidence file records pin drift.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
L0_PIN = "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"
L1_PIN = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    a = json.loads((OUT / "fetch_evidence.json").read_text())
    b = json.loads((OUT / "fetch_evidence_recheck.json").read_text())
    if a["pins"].get("pin_drift_after_fetch") or b["pins"].get("pin_drift_after_fetch"):
        print("pin drift recorded inside an evidence file", file=sys.stderr)
        return 3

    rows = []
    for ra, rb in zip(a["records"], b["records"]):
        stable = (
            ra["verdict"] == rb["verdict"]
            and ra["matched_locator"] == rb["matched_locator"]
            and ra["locators_tried"][-1]["http_status"] == rb["locators_tried"][-1]["http_status"]
            and ra["locators_tried"][-1]["fetched_title"] == rb["locators_tried"][-1]["fetched_title"]
        )
        rows.append(
            {
                "theorem_id": ra["theorem_id"],
                "class_id": ra["class_id"],
                "source_id": ra["source_id"],
                "pass1_verdict": ra["verdict"],
                "pass2_verdict": rb["verdict"],
                "matched_locator": ra["matched_locator"],
                "matched_locator_field": ra["matched_locator_field"],
                "pass1_primary_http": ra["locators_tried"][0]["http_status"],
                "pass1_final_http": ra["locators_tried"][-1]["http_status"],
                "pass2_final_http": rb["locators_tried"][-1]["http_status"],
                "pass1_title": ra["locators_tried"][-1]["fetched_title"],
                "pass1_jaccard": ra["locators_tried"][-1]["title_comparison"]["jaccard"],
                "pass2_jaccard": rb["locators_tried"][-1]["title_comparison"]["jaccard"],
                "stable": stable,
            }
        )

    pins_now = {"L0_current": sha256(ROOT / "ledger" / "theorems.jsonl"), "L1_current": sha256(ROOT / "ledger" / "citation_audit.csv")}
    pins_held = pins_now["L0_current"] == L0_PIN and pins_now["L1_current"] == L1_PIN
    summary = {
        "task_id": "W050-L0-INDEPENDENT-SPOTCHECK-04",
        "artifact_type": "two_pass_refetch_comparison",
        "class_id": ";".join(sorted({r["class_id"] for r in rows})),
        "node_id": "L0",
        "gate": "G-LIT",
        "actor": "worker-050",
        "input_sha256": {
            "fetch_evidence.json": sha256(OUT / "fetch_evidence.json"),
            "fetch_evidence_recheck.json": sha256(OUT / "fetch_evidence_recheck.json"),
        },
        "pins": {"L0": L0_PIN, "L1": L1_PIN, "ledger_pins_held_at_compare": pins_held},
        "counts": {
            "rows_compared": len(rows),
            "stable_rows": sum(1 for r in rows if r["stable"]),
            "unstable_rows": sum(1 for r in rows if not r["stable"]),
            "rows_resolved_both_passes": sum(1 for r in rows if r["pass1_verdict"] == "match" and r["pass2_verdict"] == "match"),
            "primary_locator_non_200_rows": sum(1 for r in rows if r["pass1_primary_http"] != 200),
        },
        "rows": rows,
        "falsifier": (
            "F1: any per-row instability between the two passes (locator, status or title) voids the "
            "stability claim for that row; F2: L0 or L1 hash movement at compare time voids the table; "
            "F3: an ordered 1:1 reproduction by compare_rechecks.py fails."
        ),
    }
    (OUT / "recheck_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print("stable:", summary["counts"]["stable_rows"], "/", len(rows),
          "| resolved both passes:", summary["counts"]["rows_resolved_both_passes"],
          "| pins held:", pins_held)
    return 0 if summary["counts"]["unstable_rows"] == 0 and pins_held else 1


if __name__ == "__main__":
    raise SystemExit(main())
