#!/usr/bin/env python3
"""Idempotent emitter for worker-078 W078-GF0-CRITERIA-AUDIT-01 events.

Appends status/artifact/review events to comms/outbox/worker-078.jsonl.  Event ids are
fixed, so re-running the emitter is a no-op for events that are already present (the
duplicate-emission incident recorded at w078-20260912T0030-dup-note is why this one is
id-deterministic rather than clock-derived).

Usage: python3 emit_w078_gf0_events.py [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms" / "outbox" / "worker-078.jsonl"
CREATED = "2026-09-12T00:47:00+08:00"
TASK = "W078-GF0-CRITERIA-AUDIT-01"
PIN = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def ev(eid: str, etype: str, **kw) -> dict:
    d = {"event_id": eid, "event_type": etype, "created_at": CREATED,
         "actor": "worker-078", "task_id": TASK, **kw}
    return d


def build(*, include_checkpoint: bool = True) -> list:
    """Build the event batch.  Hashes are measured at emit time, so the batch stays correct
    when the checkpoint or review body is written after the first phase."""
    events = build_primary()
    f_ckpt = "runtime/state/w078_checkpoint_5_gf0_criteria_audit.json"
    if include_checkpoint and (ROOT / f_ckpt).is_file():
        h = sha(f_ckpt)
        events.append(ev("w078-gf0crit-artifact-checkpoint", "artifact", node_id="F0",
                         class_id=";".join(CLASSES), gate="G-F0", artifact_type="checkpoint",
                         path=f_ckpt, sha256=h, validation_status="unverified",
                         note="Worker checkpoint: measured artifact hashes, binding, drift check, non-claims.",
                         evidence_refs=[f"{f_ckpt}#{h[:12]}"]))
    return events


def build_primary() -> list:
    f_report = "artifacts/worker-078/f0_criteria_audit/report.json"
    f_rerun = "artifacts/worker-078/f0_criteria_audit/report_rerun.json"
    f_code = "artifacts/worker-078/f0_criteria_audit/audit_gf0_criteria_078.py"
    f_readme = "artifacts/worker-078/f0_criteria_audit/README.md"
    f_snap = "artifacts/worker-078/f0_criteria_audit/snapshot/formulation_taxonomy.0abb9ed8a961.yaml"
    f_supp = "artifacts/worker-078/f0_criteria_audit/snapshot/formulation_taxonomy_supplement.d7419b4e8963.yaml"
    f_review = "reviews/F0-criteria-audit-078.json"
    hashes = {p: sha(p) for p in (f_report, f_rerun, f_code, f_readme, f_snap, f_supp,
                                  f_review)}
    refs = [
        f"{f_report}#{hashes[f_report][:12]}",
        f"{f_code}#{hashes[f_code][:12]}",
        f"{f_snap}#{PIN[:12]}",
    ]
    return [
        ev("w078-gf0crit-task-claim", "status", node_id="F0", class_id=";".join(CLASSES),
           gate="G-F0", status="active", hours=0.4,
           summary=("No assignment card exists in comms/inbox/worker-078.jsonl. Took ONE "
                    "bounded class-bound task: independent audit of the four G-F0 criterion "
                    "clauses at the canonical F0 hash 0abb9ed8a961 (artifact exists; exactly 4 "
                    "separate class ids; disjointness tests; 2 independent reviewer verdicts). "
                    "Pin-then-verify with drift-voiding binding, four discriminating controls, "
                    "and a pinned test-retest. Read-only on canonical paths; no gate verdict."),
           evidence_refs=["research_map/formulation_taxonomy.yaml#" + PIN[:12],
                          "research_map/research_map.json#3d45be5969ec",
                          "comms/outbox/worker-078.jsonl#w078-f0repair-status-final"],
           next_falsifier=("Live research_map/formulation_taxonomy.yaml hashes other than " + PIN
                           + " (voids the binding), or any harness check fails on the pinned bytes.")),
        ev("w078-gf0crit-artifact-harness", "artifact", node_id="F0", class_id=";".join(CLASSES),
           gate="G-F0", artifact_type="verifier_code",
           path=f_code, sha256=hashes[f_code], validation_status="unverified",
           note="12-check G-F0 criteria harness + 4 discriminating controls; independent coverage rule.",
           evidence_refs=refs),
        ev("w078-gf0crit-artifact-report", "artifact", node_id="F0", class_id=";".join(CLASSES),
           gate="G-F0", artifact_type="audit_report",
           path=f_report, sha256=hashes[f_report], validation_status="unverified",
           note="Primary evidence: accept_with_notes, 11 PASS / 1 WARN / 0 FAIL, pinned to 0abb9ed8a961.",
           evidence_refs=refs),
        ev("w078-gf0crit-artifact-rerun", "artifact", node_id="F0", class_id=";".join(CLASSES),
           gate="G-F0", artifact_type="audit_report",
           path=f_rerun, sha256=hashes[f_rerun], validation_status="unverified",
           note="Pinned test-retest: normalized (timestamp-free) report identical to report.json.",
           evidence_refs=refs),
        ev("w078-gf0crit-artifact-readme", "artifact", node_id="F0", class_id=";".join(CLASSES),
           gate="G-F0", artifact_type="summary",
           path=f_readme, sha256=hashes[f_readme], validation_status="unverified",
           note="Method, criterion-by-criterion table, notes N1/N2, five falsifiers, limits.",
           evidence_refs=refs),
        ev("w078-gf0crit-artifact-snapshot", "artifact", node_id="F0",
           class_id=";".join(CLASSES), gate="G-F0", artifact_type="artifact_snapshot",
           path=f_snap, sha256=hashes[f_snap], validation_status="unverified",
           note="Byte-exact snapshot of the audited canonical F0 revision.",
           evidence_refs=refs),
        ev("w078-gf0crit-artifact-supplement-snapshot", "artifact", node_id="F0",
           class_id=";".join(CLASSES), gate="G-F0", artifact_type="artifact_snapshot",
           path=f_supp, sha256=hashes[f_supp], validation_status="unverified",
           note="Byte-exact snapshot of the companion authoring supplement used for D1.",
           evidence_refs=refs),
        ev("w078-gf0crit-artifact-review-body", "artifact", node_id="F0",
           class_id=";".join(CLASSES), gate="G-F0", artifact_type="review_body",
           path=f_review, sha256=hashes[f_review], validation_status="unverified",
           note="Review record: verdict accept score 4.0, zero hard failures, reviewed_sha256 = pinned hash.",
           evidence_refs=refs),
        ev("w078-gf0crit-review-f0", "review", reviewer="worker-078", node_id="F0",
           target_id="F0",
           target_id_full="research_map/formulation_taxonomy.yaml#" + PIN,
           class_ids=CLASSES, gate="G-F0", verdict="accept", score=4.0,
           reviewed_sha256=PIN, verified_sha256=PIN,
           reviewed_path="research_map/formulation_taxonomy.yaml",
           counts_as_full_schema_verdict=True, counts_as_independent=True,
           binding=("snapshot-pinned at 0abb9ed8a961; live canonical re-measured equal at run "
                    "start and run end"),
           hard_failures=[],
           findings=[
               "All four G-F0 criterion clauses hold at the pinned hash: artifact exists and is "
               "byte-stable across the run; exactly the four frozen class ids with descriptors; "
               "6/6 disjointness pairs with axes in the declared 8-token field_vocabulary; 4 "
               "distinct full-accept reviewers at the same hash (deepseek-flash-18, "
               "deepseek-flash-19, worker-025, worker-038), recomputed independently and "
               "cross-checked against astra_lifecycle.review_coverage.",
               "Controls discriminate: dropped pair, fifth class id, blanked separation and "
               "unknown axis token are each rejected; pinned test-retest is identical modulo timestamps.",
               "WARN (notation only): canonical line 15 'C2/C0 provenance.schema_owner pointers' "
               "matches the frozen MERGED_RE but is not a class token; class-token scans are clean. "
               "Recommend 'the C2 and C0 ...' at the next revision.",
               "NOTE: the pass-04 G-F0 audit reason (checked_at 00:37:18) records 0 distinct accepts "
               "and cites superseded hash 66bf917bd368; a lifecycle pass should refresh it. NOTE: "
               "status is still draft_unverified and genericity Q1/Q3 remain downstream-owned; the "
               "criterion text does not require closure, but a lead/controller ruling may gate on it.",
           ],
           falsifier=("Re-run audit_gf0_criteria_078.py --pin " + PIN + "; any failed check, or a "
                      "report differing from report.json modulo timestamps, falsifies this accept. "
                      "A live F0 hash other than the pin voids the binding. Exhibit a fifth class "
                      "id, a malformed pair, or a merged-regularity class token to falsify "
                      "B1/B2/C1; show two of the four accepting reviewers non-independent to "
                      "falsify the two-reviewer criterion."),
           evidence_refs=[f"{f_review}#{hashes[f_review][:12]}",
                          f"{f_report}#{hashes[f_report][:12]}",
                          f"{f_rerun}#{hashes[f_rerun][:12]}",
                          f"{f_code}#{hashes[f_code][:12]}",
                          "reviews/F0-review-18.json", "reviews/F0-review-19.json",
                          "reviews/F0-review-025.json", "reviews/F0-conformance-038-rev28.json"]),
        ev("w078-gf0crit-status-final", "status", node_id="F0", class_id=";".join(CLASSES),
           gate="G-F0", status="active", hours=0.4,
           summary=("W078-GF0-CRITERIA-AUDIT-01 complete at worker level. G-F0 criterion audit at "
                    "pinned F0 hash 0abb9ed8a961: accept_with_notes, 11 PASS / 1 WARN / 0 FAIL; "
                    "exactly 4 separate class ids; 6/6 disjointness pairs; 4 distinct full-accept "
                    "reviewers at the same hash with two-mechanism agreement; controls discriminate; "
                    "pinned test-retest identical. One notation-only WARN on canonical line 15. "
                    "Canonical artifacts untouched; numerics lock respected; worker exits now. This "
                    "is a completion claim, not a gate verdict or node transition."),
           evidence_refs=[f"{f_report}#{hashes[f_report][:12]}",
                          f"{f_review}#{hashes[f_review][:12]}",
                          "comms/outbox/worker-078.jsonl#w078-gf0crit-artifact-checkpoint",
                          "research_map/formulation_taxonomy.yaml#" + PIN[:12]],
           next_falsifier=("Re-measure research_map/formulation_taxonomy.yaml; if it moves off "
                           "0abb9ed8a961 the audit is advisory for the pinned revision only. The "
                           "remaining G-F0 gap is a controller ruling on the stale audit reason and "
                           "on draft_unverified/genericity ownership, then the gate decision itself."),
           artifact="artifacts/worker-078/f0_criteria_audit/",
           completion_scope="worker lifecycle only; not a node done / gate verdict"),
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    events = build()
    existing = set()
    if OUTBOX.is_file():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                continue
    new = [e for e in events if e["event_id"] not in existing]
    print(json.dumps({"planned": len(events), "already_present": len(events) - len(new),
                      "to_append": len(new),
                      "ids": [e["event_id"] for e in new]}))
    if args.dry_run or not new:
        return 0
    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    with OUTBOX.open("a") as fh:
        for e in new:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
