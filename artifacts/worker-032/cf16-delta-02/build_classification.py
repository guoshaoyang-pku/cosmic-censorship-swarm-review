#!/usr/bin/env python3
"""Build cf16-delta-02/classification.json from pass-1 evidence + curated additions.

Provenance rule
---------------
Pass 1 (W032-CF16-DELTA-01, report.json#e9a185ba9fdfeeb2) curated a label, a
mechanism and a one-line reason for every one of the 17 findings at map
11311ab36005.  Pass 2 adjudicates the hard set at map ed28b714 under the APPLIED
detector a8c04fc31e4a.  Labels for findings present in both passes are carried
byte-for-byte; only genuinely new findings are curated here.  Every carry is
verified against the finding context hash, and the builder fails on any
uncovered post finding.

Keys are `claim_event_id|sha256(context)[:16]`, not array indices, because the
claims array is rebuilt from the event stream and the detector's occurrence
indices shift when a finding is cleared.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PASS1 = ROOT / "artifacts/worker-032/cf16-delta/report.json"
POST_DET = HERE / "pinned/class_separation.a8c04fc31e4a.post.py"
MAP = HERE / "pinned/research_map.ed28b714464e.json"
OUT = HERE / "classification.json"

# Curated additions for findings that did not exist at the pass-1 pin.
# worker-093's metagrowth claim mints three hard entries by quoting the
# detector's own output while counting first-order assertions at zero.
NEW_ENTRIES = {
    "w093-metagrowth-20260912T0049-claim": [
        {
            "label": "QUOTED_MENTION",
            "mechanism": "DETECTOR_SELF_QUOTE",
            "reason": (
                "NEW in pass 2. Quotes the detector-output strings ('composite C0/C2 asserted as one "
                "class', 'no C0/C2 merge') while stating that claim statements quote or describe them; "
                "a metalinguistic mention of the failure strings, not a class assertion."
            ),
        },
        {
            "label": "QUOTED_MENTION",
            "mechanism": "DETECTOR_SELF_QUOTE",
            "reason": (
                "NEW in pass 2. Continuation of the same quoted-output clause; the sentence counts "
                "first-order assertions and does not assert one."
            ),
        },
        {
            "label": "DETECTOR_SELF_DESCRIPTION",
            "mechanism": "DETECTOR_DESCRIPTION",
            "reason": (
                "NEW in pass 2. States '0 of 17 findings is a first-order assertion that C0 and C2 are "
                "one class' and describes quoting the detector's own finding text; reports the detector's "
                "output rather than asserting a merge."
            ),
        },
    ]
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def key(event_id: str, context: str) -> str:
    return f"{event_id}|{sha256_text(context)[:16]}"


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("post_det", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def extract_context(finding: str) -> str:
    import ast
    if ": ..." not in finding:
        return ""
    try:
        return ast.literal_eval(finding.split(": ...", 1)[1])
    except (ValueError, SyntaxError):
        return finding.split(": ...", 1)[1].strip("'")


def main() -> int:
    p1 = json.loads(PASS1.read_text())
    carried: dict[str, dict] = {}
    for r in p1["adjudication"]["rows"]:
        carried[key(r["claim_event_id"], r["context"])] = {
            "label": r["label"],
            "mechanism": r.get("mechanism", ""),
            "reason": r.get("label_reason", ""),
            "origin": "pass1-carried",
            "pass1_finding_id": r["finding_id"],
        }
    det = load_module(POST_DET)
    m = json.loads(MAP.read_text())
    post_rows = []
    for i, c in enumerate(m["claims"]):
        if not isinstance(c, dict):
            continue
        eid = str(c.get("event_id") or f"claims[{i}]")
        for f in det.findings(c, f"claims[{i}]", mode="prose"):
            post_rows.append((eid, extract_context(f)))

    entries: dict[str, dict] = {}
    problems = []
    new_used = {k: 0 for k in NEW_ENTRIES}
    for eid, ctx in post_rows:
        k = key(eid, ctx)
        if k in carried:
            entries[k] = carried[k]
        elif eid in NEW_ENTRIES and new_used[eid] < len(NEW_ENTRIES[eid]):
            entry = dict(NEW_ENTRIES[eid][new_used[eid]])
            entry["origin"] = "pass2-new"
            new_used[eid] += 1
            entries[k] = entry
        else:
            problems.append(f"uncovered post finding {k}")
    for eid, n in new_used.items():
        if n != len(NEW_ENTRIES[eid]):
            problems.append(f"curated entries unused for {eid}: {n}/{len(NEW_ENTRIES[eid])}")

    doc = {
        "task_id": "W032-CF16-DELTA-02",
        "source": {
            "pass1_report": "artifacts/worker-032/cf16-delta/report.json#e9a185ba9fdfeeb2",
            "pass1_labels_carried": sum(1 for e in entries.values() if e["origin"] == "pass1-carried"),
            "pass2_new_labels": sum(1 for e in entries.values() if e["origin"] == "pass2-new"),
        },
        "keying": "claim_event_id|sha256(+/-60 char detector context)[:16]",
        "findings_by_key": entries,
        "unflagged": p1["converse_scan"]["unflagged_rows"]
        and {
            f"{r['claim_event_id']}|{r['match']}": {
                "label": r["label"], "mechanism": r.get("mechanism", ""), "reason": r.get("label_reason", "")
            }
            for r in p1["converse_scan"]["unflagged_rows"]
        },
        "problems": problems,
    }
    OUT.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"entries": len(entries), "carried": doc["source"]["pass1_labels_carried"],
                      "new": doc["source"]["pass2_new_labels"], "problems": problems}, indent=1))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
