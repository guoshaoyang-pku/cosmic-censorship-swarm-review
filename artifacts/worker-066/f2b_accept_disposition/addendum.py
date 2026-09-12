#!/usr/bin/env python3
"""Addendum: review-byte drift across the audit instant.

reviews/F2b-review-worker-072-rev29.json was rewritten at 01:14:54, between the pin step and the
first emission: verdict accept (7487f310) -> revise (5db91bb0), and the rewritten file now files a
blocking hard failure on carrier C1-DENIAL.  This addendum re-measures at the new instant, proves
the pinned copy still reproduces the original classification, and shows the audit's result is
invariant (0 clean accepts at both instants).

Writes NEW files only, so every hash already referenced by the emitted event set stays valid.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
spec = importlib.util.spec_from_file_location("audit066", OUT / "audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

TASK = "W066-F2B-ACCEPT-DISPOSITION-01-ADDENDUM"
DRIFT_FILE = "reviews/F2b-review-worker-072-rev29.json"


def sha(rel: str) -> str:
    h = hashlib.sha256()
    with (ROOT / rel).open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


pinned = json.loads((OUT / "evidence" / "pinned_inputs.json").read_text())
then = {}
for rel, rec in pinned.items():
    if rec is None or not rel.startswith("reviews/F2b-"):
        continue
    d = json.loads((ROOT / rec["pinned_copy"]).read_text())
    then[rel] = {
        "sha256": rec["sha256"],
        "verdict": d.get("verdict"),
        "reviewer": d.get("reviewer"),
        "classification": audit.classify_accept(d) if d.get("verdict") == "accept" else None,
    }

entry = {rel: sha(rel) for rel in audit.PINS}
now_accepts, now_src = audit.discover()
live = audit.live_carrier_state()
support = audit.carrier_support([c["file"] for c in now_src])
exit_ = {rel: sha(rel) for rel in audit.PINS}

drift = []
for rel, t in sorted(then.items()):
    now_sha = sha(rel)
    if now_sha != t["sha256"]:
        d = json.loads((ROOT / rel).read_text())
        drift.append({
            "file": rel, "sha256_at_pin": t["sha256"], "sha256_now": now_sha,
            "verdict_at_pin": t["verdict"], "verdict_now": d.get("verdict"),
            "score_now": d.get("score"),
            "hard_failure_carriers_now": sorted({
                cid for cid in audit.CARRIERS
                for rec in audit.disposition_records(d)
                if audit.mentions(json.dumps(rec), cid)
                and any(k in json.dumps(rec).lower() for k in ("hard", "blocking"))
            }),
        })

accepts_then = sorted(r for r, t in then.items() if t["verdict"] == "accept")
clean_then = [r for r, t in then.items()
              if t["classification"] and all(
                  t["classification"][c]["classification"] == "DISPOSED" for c in audit.CARRIERS)]
clean_now = [a["file"] for a in now_accepts
             if all(a["classification"][c]["classification"] == "DISPOSED" for c in audit.CARRIERS)]

ctrls = []


def add(cid, expect, got):
    ctrls.append({"id": cid, "expect": expect, "got": got, "matched": expect == got})


pin_rec = pinned.get(DRIFT_FILE)
add("D1:pinned-copy-still-accept", "accept",
    json.loads((ROOT / pin_rec["pinned_copy"]).read_text()).get("verdict") if pin_rec else "no-pin")
add("D2:live-072-now-revise", "revise",
    json.loads((ROOT / DRIFT_FILE).read_text()).get("verdict"))
add("D3:072-pinned-classification-both-silent", "SILENT,SILENT",
    ",".join(then[DRIFT_FILE]["classification"][c]["classification"] for c in audit.CARRIERS))
add("D4:clean-count-zero-then", 0, len(clean_then))
add("D5:clean-count-zero-now", 0, len(clean_now))
add("D6:pins-stable-during-addendum", True, entry == exit_)
add("D7:carriers-still-live", True,
    live["C1-DENIAL"]["present"] and live["C2-PREMISE"]["present"])
add("D8:both-carriers-still-supported", True,
    len({s['source'] for s in support['C1-DENIAL']}) >= 2
    and len({s['source'] for s in support['C2-PREMISE']}) >= 2)
add("D9:drift-detected", True, len(drift) >= 1)
add("D10:no-new-accept-disposes-both", True,
    all(not all(a["classification"][c]["classification"] == "DISPOSED" for c in audit.CARRIERS)
        for a in now_accepts))

report = {
    "task_id": TASK,
    "actor": "worker-066",
    "node_id": "F2b",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "supersedes_referent": "W066-F2B-ACCEPT-DISPOSITION-01 (event set "
                           "w066-f2b-acceptdisp-20260912T011504-*)",
    "note": "The base event set stays valid and bound to its pinned copies; this addendum only "
            "records the live drift and re-measures at the later instant.",
    "accepts_then": accepts_then,
    "accepts_now": sorted(a["file"] for a in now_accepts),
    "clean_then": clean_then,
    "clean_now": clean_now,
    "drift": drift,
    "carrier_support_now": {k: len({s["source"] for s in v}) for k, v in support.items()},
    "live_carriers": {"C1-DENIAL": live["C1-DENIAL"]["present"],
                      "C2-PREMISE": live["C2-PREMISE"]["present"]},
    "controls": ctrls,
    "pins_entry": entry, "pins_exit": exit_,
    "verdict": "revise",
    "score": 2.5,
    "counts_as_full_schema_verdict": False,
    "scope": "drift addendum to the accept-disposition audit; not a gate verdict",
    "falsifier": "Re-run addendum.py at the same pins: falsified if the pinned copy of "
                 "reviews/F2b-review-worker-072-rev29.json no longer yields verdict=accept or no "
                 "longer classifies SILENT on both carriers; if the live file is not revise; if "
                 "either carrier is absent at the pinned F2b bytes; if any accept now binding "
                 "b2ab6acb2bbe disposes both carriers; or if any control departs from expectation.",
}

(OUT / "evidence" / "addendum_drift.json").write_text(json.dumps(
    {"then": then, "now_accepts": now_accepts, "drift": drift}, indent=1, sort_keys=True))
(OUT / "evidence" / "addendum_controls.json").write_text(json.dumps(
    {"n": len(ctrls), "matched": sum(c["matched"] for c in ctrls), "controls": ctrls},
    indent=1, sort_keys=True))
(OUT / "addendum_report.json").write_text(json.dumps(report, indent=1, sort_keys=True))
print(json.dumps({
    "accepts_then": len(accepts_then), "accepts_now": len(now_accepts),
    "clean_then": len(clean_then), "clean_now": len(clean_now),
    "drift": [d["file"] + f" {d['verdict_at_pin']}->{d['verdict_now']}" for d in drift],
    "controls": f"{sum(c['matched'] for c in ctrls)}/{len(ctrls)}",
    "pins_stable": entry == exit_,
}, indent=1))
raise SystemExit(0 if all(c["matched"] for c in ctrls) else 1)
