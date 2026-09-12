#!/usr/bin/env python3
"""W098-CLASSSEP-MENTION-SCOPE-01 emission correction.

`w098-cms-20260912T0100-complete2` (and its summary line) attributed the 0-hard result to the
current live-map hash at emit time; the 0 was measured at the pinned map 262da6979857 (claims
320) and the liveness frontier f344ed2aaea5 already shows 1 growth-family residual. This script
writes the authoritative final checkpoint 3 with the corrected attribution and appends an
idempotent correction status event. No canonical writes.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
STATE = ROOT / "runtime/state"
OUTBOX = ROOT / "comms/outbox/worker-098.jsonl"
TASK = "W098-CLASSSEP-MENTION-SCOPE-01"
AT = "2026-09-12T01:06:00+08:00"
PREFIX = "w098-cms-20260912T0100"
CLASS_ID = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"

report = json.loads((HERE / "report.json").read_text())
liveness = json.loads((HERE / "raw/liveness_recheck.json").read_text())
ck2 = json.loads((STATE / "w098_classsep_mention_scope_checkpoint_2.json").read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


ck3_path = STATE / "w098_classsep_mention_scope_checkpoint_3.json"
ck3 = dict(ck2)
ck3.update({
    "checkpoint": 3, "at": AT,
    "supersedes": "runtime/state/w098_classsep_mention_scope_checkpoint_2.json",
    "attribution_correction": {
        "event_id": f"{PREFIX}-complete2",
        "issue": ("its summary read 'live-map hard 17->0 at <map sha at emit time>', but the 0-hard "
                  "acceptance measurement binds the PINNED map, not the map current at emit time"),
        "pinned_map_sha256": report["drift"]["live_map_sha256"],
        "pinned_map_claims": report["drift"]["live_map_claims"],
        "pinned_map_result": {"v3": report["arms"]["candidate_v3_6f1a24c441fb"]["map_live_hard"],
                              "live": report["arms"]["live_a8c04fc31e4a"]["map_live_hard"],
                              "staged": report["arms"]["staged_e2d24b927ee8"]["map_live_hard"]},
        "liveness_map_sha256": liveness["live_map_sha256"],
        "liveness_map_claims": liveness["live_map_claims"],
        "liveness_result": {"v3": liveness["arms"]["v3"]["map_hard"],
                            "live": liveness["arms"]["live"]["map_hard"],
                            "staged": liveness["arms"]["staged"]["map_hard"],
                            "v1": liveness["arms"]["v1"]["map_hard"],
                            "v2": liveness["arms"]["v2"]["map_hard"]},
        "correct_reading": ("A9 (0 hard) holds at the pinned map " + report["drift"]["live_map_sha256"][:12]
                            + f" (claims={report['drift']['live_map_claims']}); on the later liveness frontier "
                            + liveness["live_map_sha256"][:12] + f" (claims={liveness['live_map_claims']}) v3 has "
                            + str(liveness["arms"]["v3"]["map_hard"]) + " hard finding(s) from a new "
                            "detector-discussion claim (claims[327])."),
    },
})
ck3["artifacts"] = {str(p.relative_to(ROOT)): sha(p) for p in [
    HERE / "pre_registration.json", HERE / "README.md", HERE / "build_candidate.py",
    HERE / "build_manifest.json", HERE / "build_candidate_v2.py", HERE / "build_manifest_v2.json",
    HERE / "build_candidate_v3.py", HERE / "build_manifest_v3.json",
    HERE / "candidate_class_separation.py", HERE / "candidate_class_separation.v2.py",
    HERE / "candidate_class_separation.v3.py", HERE / "run_battery.py", HERE / "run_battery_final.py",
    HERE / "liveness_recheck.py", HERE / "raw/candidate_battery.json",
    HERE / "raw/candidate_battery_final.json", HERE / "raw/liveness_recheck.json",
    HERE / "report.json", HERE / "emit_events.py",
]}
ck3_path.write_text(json.dumps(ck3, indent=2, sort_keys=True))

event = {
    "event_id": f"{PREFIX}-attribution-correction", "event_type": "status", "created_at": AT,
    "actor": "worker-098", "task_id": TASK, "node_id": "A1", "gate": "G-AUDIT",
    "class_id": CLASS_ID, "status": "active",
    "summary": ("Attribution correction for " + f"{PREFIX}-complete2" + ": the 0-hard v3 result binds the pinned "
                "map " + report["drift"]["live_map_sha256"][:12] + f" (claims={report['drift']['live_map_claims']}), "
                "not the map current at emission. On the liveness frontier " + liveness["live_map_sha256"][:12]
                + f" (claims={liveness['live_map_claims']}) v3 = {liveness['arms']['v3']['map_hard']} hard, live = "
                f"{liveness['arms']['live']['map_hard']}, staged = {liveness['arms']['staged']['map_hard']}; the "
                "residual is claims[327] (worker-049), a post-composite meta-noun construction. Final worker "
                "checkpoint: " + str(ck3_path.relative_to(ROOT)) + "."),
    "evidence_refs": [f"{ck3_path.relative_to(ROOT)}#{sha(ck3_path)[:12]}",
                      f"{Path('artifacts/worker-098/classsep_mention_scope/report.json')}#{sha(HERE / 'report.json')[:12]}",
                      f"{Path('artifacts/worker-098/classsep_mention_scope/raw/liveness_recheck.json')}#{sha(HERE / 'raw/liveness_recheck.json')[:12]}"],
    "next_falsifier": report["falsifier"],
}
existing = set()
for line in OUTBOX.read_text().splitlines():
    if line.strip():
        try:
            existing.add(json.loads(line).get("event_id"))
        except json.JSONDecodeError:
            pass
added = 0
with OUTBOX.open("a") as fh:
    if event["event_id"] not in existing:
        fh.write(json.dumps(event, sort_keys=True) + "\n")
        added = 1
print(json.dumps({"events_added": added, "checkpoint": str(ck3_path.relative_to(ROOT)),
                  "pinned_map": report["drift"]["live_map_sha256"][:12],
                  "liveness_map": liveness["live_map_sha256"][:12],
                  "v3_pinned_hard": report["arms"]["candidate_v3_6f1a24c441fb"]["map_live_hard"],
                  "v3_liveness_hard": liveness["arms"]["v3"]["map_hard"]}, indent=2))
