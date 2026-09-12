#!/usr/bin/env python3
"""W017-CLASSSEP-R3-ADJUDICATION-REVIEW-01 — drift table + reviewer claim table.

Read-only. Writes drift.json and live_claim_table.json under
artifacts/worker-017/classsep_adjudication_review/.
"""
from __future__ import annotations

import difflib
import hashlib
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
HERE = Path(__file__).resolve().parent
PIN_A8 = ROOT / "artifacts/worker-032/classsep-prose-01/pinned/class_separation.a8c04fc31e4a.py"
PIN_PRE = ROOT / "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py"
LIVE = ROOT / "research_map/class_separation.py"
FROZEN = ROOT / "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json"
LABELS = [36, 94, 96, 97, 101, 112, 127, 144, 152, 180, 187, 192, 276, 306, 327, 336]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def live(mod, frozen):
    per = {}
    for x in mod.findings_for_map(frozen):
        mo = re.search(r"claims\[(\d+)\]", x)
        if mo and not x.startswith("CLASSSEP-SOFT:"):
            per.setdefault(int(mo.group(1)), []).append(x)
    return per


def main():
    a8, pre, lv = load(PIN_A8, "a8"), load(PIN_PRE, "pre"), load(LIVE, "lv")
    frozen = json.loads(FROZEN.read_text())
    pa, pp, pl = live(a8, frozen), live(pre, frozen), live(lv, frozen)

    diff = list(difflib.unified_diff(PIN_A8.read_text().splitlines(), LIVE.read_text().splitlines(),
                                     "a8c04fc31e4a", "e36b0d644ca7", lineterm="", n=1))
    dropped = sorted(set(pa) - set(pl))
    added = sorted(set(pl) - set(pa))
    counts = {"a8c04fc3": {str(k): len(v) for k, v in sorted(pa.items())},
              "c266dbec": {str(k): len(v) for k, v in sorted(pp.items())},
              "e36b0d64": {str(k): len(v) for k, v in sorted(pl.items())}}
    summary = {}
    for name, per in (("c266dbec", pp), ("a8c04fc3", pa), ("e36b0d64", pl)):
        summary[name] = {"hard": sum(len(v) for v in per.values()), "claims": len(per)}
    # the one HIGH cue-induced FN fixture under both adjudicated and live bytes
    a04 = "The detector flagged this once; C0 and C2 are one class."
    a04_fired = {"a8c04fc3": bool(a8.findings_for_text(a04, "A04")),
                 "e36b0d64": bool(lv.findings_for_text(a04, "A04"))}

    table = []
    for i in LABELS:
        st = frozen["claims"][i].get("statement") if i < len(frozen.get("claims", [])) else None
        if not isinstance(st, str):
            st = str(st)
        table.append({"claim_index": i,
                      "flag_a8c04fc3": [x[:400] for x in pa.get(i, [])],
                      "flag_e36b0d64": [x[:400] for x in pl.get(i, [])],
                      "label_in_adjudication": {36: "CASE_LABEL", 94: "CASE_LABEL", 96: "CASE_LABEL",
                                                97: "CASE_LABEL", 101: "NEGATION", 112: "DETECTOR_DESCRIPTION+QUOTATION",
                                                127: "NON_MERGE_COMPOUND", 144: "WINDOW_ARTIFACT", 152: "NEGATION",
                                                180: "NEGATION", 187: "QUOTATION", 192: "DETECTOR_SELF",
                                                276: "QUOTATION", 306: "UNLABELED/QUOTATION",
                                                327: "UNLABELED/DETECTOR_SELF", 336: "UNLABELED/DETECTOR_SELF"}[i],
                      "reviewer_class": None, "statement": st})

    drift = {
        "schema": "worker-017/classsep-drift-table/v1",
        "created_at": "2026-09-12T01:10:00+08:00",
        "canonical_path": "research_map/class_separation.py",
        "hashes": {"frozen_active_pin_c266dbec": sha(PIN_PRE), "adjudicated_APPLIED_a8c04fc3": sha(PIN_A8),
                   "live_canonical_e36b0d64": sha(LIVE)},
        "live_mtime": "2026-09-12T01:06:12+08:00",
        "one_hunk_diff": diff,
        "live_hard_by_bytes": summary,
        "per_claim_counts": counts,
        "findings_dropped_by_drift": {str(k): len(pa[k]) - len(pl.get(k, [])) for k in dropped},
        "claims_dropped": dropped, "claims_added": added,
        "corpus_c_specificity": {"a8c04fc3": "3/10", "e36b0d64": "4/10"},
        "A04_clause_FN_fired": a04_fired,
        "decision_recheck_live": "no arm meets the adoption bar at e36b0d64 either "
                                 "(APPLIED spec 4/10, D cue FN 1 HIGH; STAGED spec 1/10; PROSEFIX 10 HIGH FN)",
        "authorizing_events": ["human-pi-detector-fix-20260912T0100 (inbox, assignee astra-lead-audit)",
                               "astra-detector-fix-0105 (inbox, assignee astra-lead-audit)"],
        "no_event_with_e36b0d64_at_measurement": True,
        "adjudication_binds": "a8c04fc3; audited at snapshot f344ed2a; filed 01:03:24; write 01:06:12",
    }
    (HERE / "drift.json").write_text(json.dumps(drift, indent=1) + "\n")
    (HERE / "live_claim_table.json").write_text(json.dumps(table, indent=1) + "\n")
    print("drift sha256", sha(HERE / "drift.json"))
    print("table sha256", sha(HERE / "live_claim_table.json"))
    print("summary", json.dumps(summary))
    print("dropped", dropped, "added", added)
    print("A04 fired", a04_fired)
    print("flag counts per claim a8:", {k: len(v) for k, v in sorted(pa.items())})
    print("flag counts per claim lv:", {k: len(v) for k, v in sorted(pl.items())})


if __name__ == "__main__":
    main()
