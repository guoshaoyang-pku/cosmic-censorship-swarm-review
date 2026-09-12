#!/usr/bin/env python3
"""W098-CLASSSEP-ADJ-REVIEW-01 liveness addendum: the live map moved after the review window."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms/outbox/worker-098.jsonl"
STAMP = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
NOW = datetime.now().astimezone().isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    raw = json.loads((HERE / "raw/measurements.json").read_text())
    rep = json.loads((HERE / "report.json").read_text())
    live = json.loads((ROOT / "research_map/research_map.json").read_text())
    add = {
        "schema": "worker-098/classsep-r3-adjudication-review/addendum/v1",
        "task_id": "W098-CLASSSEP-ADJ-REVIEW-01",
        "actor": "worker-098", "node_id": "A1", "gate": "G-AUDIT",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "created_at": NOW,
        "why": "the live research map advanced between the census read and event emission; the "
               "review report's closing liveness line is superseded here",
        "measurement_window": {
            "map_sha256": raw["no_write_no_gate_check"]["live_map"]["sha256"],
            "claims": raw["no_write_no_gate_check"]["live_map"]["claims"],
            "map_updated_at": raw["no_write_no_gate_check"]["live_map"]["updated_at"],
        },
        "emission_time": {
            "map_sha256": sha(ROOT / "research_map/research_map.json"),
            "claims": len(live["claims"]), "map_updated_at": live["updated_at"],
        },
        "detector_at_emission": sha(ROOT / "research_map/class_separation.py"),
        "adjudication_at_emission": sha(ROOT / "reviews/CLASSSEP-calibration-adjudication.json"),
        "gate_audit_at_emission": next(g["verdict"] for g in live["gates"]
                                       if g["gate_id"] == "G-AUDIT"),
        "effect_on_review": "none: the census binds the frozen snapshot f344ed2aaea5 and the "
                            "five hash-pinned corpora; detector and adjudication bytes are "
                            "unchanged. Expectation E12 (live != snapshot) still holds. The "
                            "review does NOT measure the hard count on the new live map; a "
                            "fresh tick is required for any live count.",
    }
    dest = HERE / "drift_addendum.json"
    dest.write_text(json.dumps(add, indent=2) + "\n")
    h = sha(dest)
    ev = [
        {"event_id": f"w098-car-{STAMP}-art-drift-addendum", "event_type": "artifact",
         "created_at": NOW, "actor": "worker-098", "node_id": "A1",
         "class_id": add["class_id"], "gate": "G-AUDIT",
         "artifact_type": "classsep_r3_adjudication_review/drift_addendum",
         "path": dest.relative_to(ROOT).as_posix(), "sha256": h,
         "validation_status": "unverified",
         "summary": "Live-map liveness addendum: 414 -> 483 claims during emission; census "
                    "unaffected (snapshot-bound).",
         "evidence_refs": [f"{dest.relative_to(ROOT).as_posix()}#{h[:12]}",
                           "artifacts/worker-098/classsep_r3_adjudication_review/report.json"
                           f"#{sha(HERE / 'report.json')[:12]}"]},
        {"event_id": f"w098-car-{STAMP}-liveness-correction", "event_type": "status",
         "created_at": NOW, "actor": "worker-098", "node_id": "A1",
         "class_id": add["class_id"], "gate": "G-AUDIT", "status": "active",
         "task_id": "W098-CLASSSEP-ADJ-REVIEW-01",
         "summary": "Liveness correction to W098-CLASSSEP-ADJ-REVIEW-01: the live map moved "
                    f"{raw['no_write_no_gate_check']['live_map']['sha256'][:12]}/414 claims -> "
                    f"{sha(ROOT / 'research_map/research_map.json')[:12]}/{len(live['claims'])} "
                    "claims during emission (G-AUDIT still pending, detector still a8c04fc3). "
                    "All census results bind the frozen snapshot f344ed2aaea5 and are unaffected; "
                    "the 19-hard residual is a snapshot figure. No gate verdict, no canonical "
                    "write, no claim retirement.",
         "evidence_refs": [f"{dest.relative_to(ROOT).as_posix()}#{h[:12]}",
                           "reviews/CLASSSEP-calibration-adjudication.json#7714ffd5b467",
                           "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json#f344ed2aaea5"],
         "next_falsifier": rep["falsifier"]},
    ]
    with OUTBOX.open("a") as f:
        for e in ev:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    # validate whole stream and hash claims
    bad = 0
    n = 0
    for ln in OUTBOX.read_text().splitlines():
        if not ln.strip():
            continue
        try:
            e = json.loads(ln)
        except json.JSONDecodeError:
            bad += 1
            continue
        n += 1
        for k in ("event_id", "event_type", "created_at", "actor"):
            if k not in e:
                bad += 1
    print(f"addendum {dest.relative_to(ROOT)} sha256={h}")
    print(f"outbox lines={n} malformed={bad}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
