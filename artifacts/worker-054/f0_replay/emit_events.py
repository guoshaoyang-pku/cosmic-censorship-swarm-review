#!/usr/bin/env python3
"""Emit worker-054 outbox events for W054-F0-REPLAY-01 (self-validated before write)."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
OUT = ROOT / "comms" / "outbox" / "worker-054.jsonl"
ART = "artifacts/worker-054/f0_replay"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]


def sha(rel: str) -> str:
    h = hashlib.sha256()
    with (ROOT / rel).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ts = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    now = datetime.now(CST).isoformat(timespec="seconds")
    report = json.loads((ROOT / ART / "report.json").read_text())
    o, b = report["outcome"], report["binding"]

    h_report = sha(f"{ART}/report.json")
    h_check = sha(f"{ART}/checker_report.json")
    h_readme = sha(f"{ART}/README.md")
    h_tool = sha(f"{ART}/replay.py")
    h_cases = report["inputs"]["cases"]["snapshot_sha256"]
    h_tax = report["inputs"]["taxonomy"]["snapshot_sha256"]

    refs = [
        f"{ART}/report.json#{h_report[:12]}",
        f"{ART}/checker_report.json#{h_check[:12]}",
        f"{ART}/README.md#{h_readme[:12]}",
        f"{ART}/replay.py#{h_tool[:12]}",
        f"schemas/taxonomy_cases.jsonl#{h_cases[:12]}",
        f"research_map/formulation_taxonomy.yaml#{h_tax[:12]}",
    ]
    artifact_refs = refs[:4]
    task = {"task_id": "W054-F0-REPLAY-01", "node_id": "F0", "gate": "G-F0",
            "class_id": CLASS_IDS[0], "class_ids": CLASS_IDS}

    events = [
        {"event_id": f"w054-{ts}-artifact-report", "event_type": "artifact", "created_at": now,
         "actor": "worker-054", **task, "artifact_type": "verification_report",
         "path": f"{ART}/report.json", "sha256": h_report, "validation_status": "unverified",
         "evidence_refs": refs,
         "note": "Independent replay of the frozen F0/G-F0 corpus at the pinned canonical taxonomy snapshot; 12/12 consistency checks, checker PASS (out-of-binding replay)."},
        {"event_id": f"w054-{ts}-artifact-checker-report", "event_type": "artifact", "created_at": now,
         "actor": "worker-054", **task, "artifact_type": "machine_report",
         "path": f"{ART}/checker_report.json", "sha256": h_check, "validation_status": "unverified",
         "evidence_refs": refs,
         "note": "Raw output of artifacts/flash-02/check_taxonomy_cases.py run against byte-identical snapshot inputs."},
        {"event_id": f"w054-{ts}-artifact-readme", "event_type": "artifact", "created_at": now,
         "actor": "worker-054", **task, "artifact_type": "summary",
         "path": f"{ART}/README.md", "sha256": h_readme, "validation_status": "unverified",
         "evidence_refs": refs, "note": "One-page summary with the hash pins, scope limits and falsifier."},
        {"event_id": f"w054-{ts}-artifact-tool", "event_type": "artifact", "created_at": now,
         "actor": "worker-054", **task, "artifact_type": "tool",
         "path": f"{ART}/replay.py", "sha256": h_tool, "validation_status": "unverified",
         "evidence_refs": refs, "note": "Reproducible replay harness (snapshot, checker re-run, independent cross-check, drift check)."},
        {"event_id": f"w054-{ts}-claim-replay", "event_type": "claim", "created_at": now,
         "actor": "worker-054", **task, "conclusion_type": "formal_model",
         "statement": (
             f"At the pinned snapshot of research_map/formulation_taxonomy.yaml sha256 {h_tax} "
             f"(revision {b['current_taxonomy_revision']}, status {b['current_taxonomy_status']}; live pre-run = snapshot = "
             f"live post-run, no drift) the frozen F0/G-F0 class-leakage corpus schemas/taxonomy_cases.jsonl "
             f"sha256 {h_cases} (36 cases: 16 positive, 20 negative, 9 flagged open) replays with its own checker "
             f"artifacts/flash-02/check_taxonomy_cases.py to exit 0 / verdict PASS / errors [] / 10-of-10 mutation "
             f"controls detected / 6-of-6 class pairs disjoint; an independent local recomputation of counts, per-class "
             f"coverage, the open-case set and the pairwise differing-axis sets agrees with the checker report on all 12 "
             f"checks. This is an out-of-binding replay: the corpus meta record still declares "
             f"bound_taxonomy_sha_{b['corpus_bound_taxonomy_sha256'][:12]} (rev {b['corpus_bound_revision']}) and no re-pin "
             f"is claimed; the corpus's own next-falsifier #1 did not fire at {h_tax[:12]}."
         ),
         "assumptions": [
             "The checker verdict is taken only for the pinned snapshot bytes; later motion of the live canonical file does not retroactively change it.",
             "The corpus ground truth (expected_resolution, open flags) is the corpus author's; this replay tests resolution at new bytes, not the ground truth's correctness.",
             "The independent recomputation uses local code over the same frozen corpus and cross-checks the report's self-claims; it does not re-implement the checker's leak rules.",
             "The 36 fixtures are worker-authored synthetic strings; the result is shape/separation evidence only, not a mathematical statement about spacetimes.",
         ],
         "falsifier": report["falsifier"],
         "evidence_refs": refs, "artifact_refs": artifact_refs},
        {"event_id": f"w054-{ts}-complete", "event_type": "status", "created_at": now,
         "actor": "worker-054", **task, "status": "active", "hours": 0.4,
         "summary": (
             f"W054-F0-REPLAY-01 complete: artifacts exist on disk and are hash-pinned; report.json + checker_report.json + "
             f"README.md emitted. Corpus replayed at taxonomy {h_tax[:12]} (rev 4): checker PASS, controls 10/10, 12/12 "
             f"independent checks, no input drift; out-of-binding vs corpus-declared 565a6e505188. Worker report only: no gate "
             f"verdict, no node transition, no validation_status=passed. Checkpoint follows."
         ),
         "evidence_refs": refs, "next_falsifier": report["falsifier"]},
    ]

    for e in events:
        validate_event(e)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"wrote {len(events)} events to {OUT.relative_to(ROOT)}")
    print(f"report={h_report[:12]} checker_report={h_check[:12]} readme={h_readme[:12]} tool={h_tool[:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
