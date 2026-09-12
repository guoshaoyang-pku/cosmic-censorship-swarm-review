#!/usr/bin/env python3
"""Emit W043G events to comms/outbox/worker-043.jsonl and write the checkpoint.

Idempotent: an event whose event_id already appears in the outbox is skipped.
Writes only under this worker's artifact dir, comms/outbox/worker-043.jsonl and
runtime/state/.  No canonical byte is touched.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms" / "outbox" / "worker-043.jsonl"
STATE = ROOT / "runtime" / "state"
TASK = "W043G-F2B-HISTORY-CLOSURE-01"
STAMP = "2026-09-12T01:24:00+08:00"  # fixed stamp: manifest/checkpoint content is byte-deterministic


def now() -> str:
    return STAMP


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    report = json.loads((OUT / "report.json").read_text())
    raw = json.loads((OUT / "raw" / "history_frontier_raw.json").read_text())
    files = {
        "checker": OUT / "check_f2b_history_closure.py",
        "raw": OUT / "raw" / "history_frontier_raw.json",
        "report": OUT / "report.json",
        "readme": OUT / "README.md",
        "candidate_rev14": OUT / "scratch" / "candidate_rev14_closed.yaml",
        "pins_start": OUT / "raw" / "pins_start.json",
        "pins_end": OUT / "raw" / "pins_end.json",
    }
    h = {k: sha(p) for k, p in files.items()}
    manifest = {
        "task_id": TASK, "actor": "worker-043", "node_id": "F2b",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"], "gate": "G-FORM",
        "created_at": now(),
        "artifacts": {k: {"path": str(p.relative_to(ROOT)), "sha256": h[k],
                          "bytes": p.stat().st_size} for k, p in files.items()},
        "authority_note": report["authority_note"],
    }
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n")
    h["manifest"] = sha(OUT / "MANIFEST.json")

    ev = []

    def add(eid, etype, **kw):
        e = {"event_id": f"w043g-{eid}", "event_type": etype, "created_at": now(),
             "actor": "worker-043", "task_id": TASK, "gate": "G-FORM"}
        e.update(kw)
        ev.append(e)

    live = raw["candidate_census"]["live"]
    c84 = raw["candidate_census"]["w002_2edit_84b5d3fa"]
    c48 = raw["candidate_census"]["w044_rev13_48cadb72"]
    v2 = raw["closure_variants"]["V2_plus_unused_row_reorder"]

    add("status-taken", "status", node_id="F2b",
        node_ids=["F2b"], class_id="AF-SCC-C0-VAC-GEN", class_ids=["AF-SCC-C0-VAC-GEN"],
        status="active", hours=0.4,
        summary=("No inbox card exists for slot 043. Took one bounded class-bound task on the live "
                 "G-FORM critical path: audit-trail closure frontier of the staged F2b containment "
                 "repair (worker-035 F-035-01). Measured live rev13 b2ab6acb, the staged candidates "
                 "84b5d3fa/a110f8e8/48cadb72, and two minimal closure variants."),
        evidence_refs=[f"schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe"],
        next_falsifier="See report falsifier; void on any pin move.")
    add("artifact-checker", "artifact", node_id="F2b", class_id="AF-SCC-C0-VAC-GEN",
        artifact_type="instrument", path="artifacts/worker-043/w043g_f2b_history_closure/check_f2b_history_closure.py",
        sha256=h["checker"], validation_status="unverified",
        evidence_refs=[f"artifacts/worker-043/w043g_f2b_history_closure/check_f2b_history_closure.py#{h['checker'][:12]}"])
    add("artifact-raw", "artifact", node_id="F2b", class_id="AF-SCC-C0-VAC-GEN",
        artifact_type="measurement_raw", path="artifacts/worker-043/w043g_f2b_history_closure/raw/history_frontier_raw.json",
        sha256=h["raw"], validation_status="unverified",
        evidence_refs=[f"artifacts/worker-043/w043g_f2b_history_closure/raw/history_frontier_raw.json#{h['raw'][:12]}"])
    add("artifact-report", "artifact", node_id="F2b", class_id="AF-SCC-C0-VAC-GEN",
        artifact_type="report", path="artifacts/worker-043/w043g_f2b_history_closure/report.json",
        sha256=h["report"], validation_status="unverified",
        evidence_refs=[f"artifacts/worker-043/w043g_f2b_history_closure/report.json#{h['report'][:12]}"])
    add("artifact-candidate", "artifact", node_id="F2b", class_id="AF-SCC-C0-VAC-GEN",
        artifact_type="candidate_schema", path="artifacts/worker-043/w043g_f2b_history_closure/scratch/candidate_rev14_closed.yaml",
        sha256=h["candidate_rev14"], validation_status="unverified",
        evidence_refs=[f"artifacts/worker-043/w043g_f2b_history_closure/scratch/candidate_rev14_closed.yaml#{h['candidate_rev14'][:12]}",
                       "artifacts/formulation/FROZEN.json#815e08079aef"])
    add("artifact-manifest", "artifact", node_id="F2b", class_id="AF-SCC-C0-VAC-GEN",
        artifact_type="manifest", path="artifacts/worker-043/w043g_f2b_history_closure/MANIFEST.json",
        sha256=h["manifest"], validation_status="unverified",
        evidence_refs=[f"artifacts/worker-043/w043g_f2b_history_closure/MANIFEST.json#{h['manifest'][:12]}"])

    add("claim-history-frontier", "claim", node_id="F2b",
        class_id="AF-SCC-C0-VAC-GEN", conclusion_type="measurement",
        statement=("At FROZEN rev29 the containment-clean F2b candidates 84b5d3fa (worker-002/066) and "
                   "a110f8e8 (worker-022) leave revision_history byte-unchanged, so F-035-01 persists: "
                   "non-monotone timestamps, no newest-row reference to the live declared F0 hash "
                   "0abb9ed8a961, and an unused row carrying active delta notes; the worker-044 candidate "
                   "48cadb72 additionally sets revision:14 without a rev14 row and re-declares the "
                   "pre-rev13 consistency hash 675a99d0. A rev14 row plus revision/revised_at bump plus "
                   "chronological re-placement and note-clearance of the unused row closes all seven "
                   "invariants and both containment carriers (28dc0d3df53d)."),
        assumptions=["FROZEN rev29 815e0807 binds the measured canonical and mirror hashes",
                     "history coherence is required by the FROZEN change protocol (any revision bumps "
                     "revision and re-emits)"],
        falsifier=report["falsifier"],
        evidence_refs=[f"artifacts/worker-043/w043g_f2b_history_closure/report.json#{h['report'][:12]}",
                       f"artifacts/worker-043/w043g_f2b_history_closure/raw/history_frontier_raw.json#{h['raw'][:12]}",
                       "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
                       "artifacts/worker-002/f2b_containment_adjudication/candidate/af_scc_c0_vacuum.repair2edit.yaml#84b5d3fa29a6",
                       "artifacts/worker-044/f2b_rev13_integration/sandbox/schemas/af_scc_c0_vacuum.yaml#48cadb72e507"],
        artifact_refs=[f"artifacts/worker-043/w043g_f2b_history_closure/report.json#{h['report'][:12]}"])
    add("review-f2b-history", "review", node_id="F2b",
        class_id="AF-SCC-C0-VAC-GEN",
        target_id="F2b@b2ab6acb2bbe + staged repair candidates 84b5d3fa/a110f8e8/48cadb72 (audit-trail axis)",
        reviewer="worker-043", verdict="revise", score=3.5,
        counts_as_full_schema_verdict=False, gate_eligible=False,
        hard_failures=[],
        findings=[
            "W043G-R-01 CONFIRMED at live bytes: F-035-01 persists (H1 non-monotone row 8>row 9; H3 no newest-row reference to 0abb9ed8a961; H4 index 9 unused:true with two delta notes).",
            "W043G-R-02 CONFIRMED: the containment repair candidates 84b5d3fa and a110f8e8 do not touch revision_history, so a landing of containment alone leaves the recorded major finding standing.",
            "W043G-R-03 NEW: 48cadb72 (worker-044 rev13-integration) sets revision:14 with a rev13-newest history row (H2) and re-declares consistency_evidence_sha256 675a99d0 against the measured 9e335e9b (H6) while its own binding_note claims the rev13 refresh; landing it as-is regresses the rev13 evidence binding.",
            "W043G-R-04 CLOSURE: V2 28dc0d3df53d closes all seven invariants plus both containment carriers and passes the canonical structural gate; it moves the unused historical row, so the owner should choose V2 or an explicit disposition of historical rows.",
            "CONTROLS: 9/9 pre-registered matched; 14/14 pins stable entry-exit; no canonical byte modified; checker re-run deterministic.",
        ],
        evidence_refs=[f"artifacts/worker-043/w043g_f2b_history_closure/report.json#{h['report'][:12]}",
                       f"artifacts/worker-043/w043g_f2b_history_closure/scratch/candidate_rev14_closed.yaml#{h['candidate_rev14'][:12]}",
                       "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe"],
        falsifier=report["falsifier"],
        authority_note="Worker evidence only; cannot set a gate verdict, node status or validation_status; reviews the audit-trail axis of F2b, not its mathematical content.")
    add("status-complete", "status", node_id="F2b",
        node_ids=["F2b"], class_id="AF-SCC-C0-VAC-GEN", class_ids=["AF-SCC-C0-VAC-GEN"],
        status="active", hours=0.4,
        summary=("W043G-F2B-HISTORY-CLOSURE-01 complete at worker level: 7 artifacts on disk and "
                 "hash-pinned, 9/9 controls, 14/14 pins stable, canonical tree unchanged. Advisory "
                 "verdict revise 3.5 on the audit-trail axis: the containment repair alone does not "
                 "close F-035-01; 48cadb72 additionally regresses the rev13 evidence binding; V2 "
                 "28dc0d3df53d closes history + containment. Completion claim only; no node transition, "
                 "no gate verdict, no canonical byte changed."),
        evidence_refs=[f"artifacts/worker-043/w043g_f2b_history_closure/MANIFEST.json#{h['manifest'][:12]}",
                       f"artifacts/worker-043/w043g_f2b_history_closure/report.json#{h['report'][:12]}"],
        next_falsifier=report["falsifier"])

    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            try:
                seen.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                continue
    appended = 0
    with OUTBOX.open("a") as fh:
        for e in ev:
            if e["event_id"] in seen:
                continue
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            appended += 1

    STATE.mkdir(parents=True, exist_ok=True)
    ckpt = {
        "checkpoint": 1, "at": now(), "worker": "worker-043", "task_id": TASK, "gate": "G-FORM",
        "node_ids": ["F2b"], "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "status": "complete_pending_owner_ruling",
        "verdict": "revise", "score": 3.5, "hours_spent_estimate": 0.4,
        "summary": report["finding"],
        "artifacts": {k: f"{str(p.relative_to(ROOT))}#{h[k][:16]}" for k, p in files.items()},
        "reviewed_pins": {"schemas/af_scc_c0_vacuum.yaml": report["target"]["sha256"],
                          "artifacts/formulation/FROZEN.json": report["target"]["frozen_manifest_sha256"]},
        "falsifier": report["falsifier"],
        "authority_note": report["authority_note"],
    }
    (STATE / "w043g_checkpoint.json").write_text(json.dumps(ckpt, indent=1) + "\n")
    logp = STATE / "w043g_checkpoints.jsonl"
    prev = logp.read_text().splitlines() if logp.exists() else []
    last = json.loads(prev[-1]) if prev else {}
    if last.get("task_id") != TASK or last.get("verdict") != ckpt["verdict"]:
        with logp.open("a") as fh:
            fh.write(json.dumps(ckpt, ensure_ascii=False) + "\n")
    print(json.dumps({"events_appended": appended, "events_total": len(ev),
                      "manifest_sha256": h["manifest"], "checkpoint": str(STATE / "w043g_checkpoint.json")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
