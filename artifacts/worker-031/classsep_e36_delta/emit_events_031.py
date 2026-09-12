#!/usr/bin/env python3
"""Emit worker-031's closed set of structured events for W031-CLASSSEP-E36-DELTA-01.

Two channels, because research_map/events.schema.json types only direction_update,
claim, artifact, review and resource_request:

  * schema-valid events (artifact x2, claim, review) -> comms/outbox/worker-031-classsep-e36.jsonl,
    each validated with jsonschema against the schema before writing;
  * lifecycle events (blocker, status), which the live outbox stream carries for every
    worker but the schema does not type -> appended to the worker's lifecycle stream
    comms/outbox/worker-031.jsonl, marked outside_event_schema=true.

Idempotent by event_id across the whole outbox. Sets no gate verdict and no node status.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms/outbox/worker-031-classsep-e36.jsonl"
LIFECYCLE_OUTBOX = ROOT / "comms/outbox/worker-031.jsonl"
SCHEMA = ROOT / "research_map/events.schema.json"
NOW = "2026-09-12T01:17:00+08:00"
STAMP = "20260912T011700"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def validate(ev: dict, schema: dict) -> tuple[bool, str]:
    import jsonschema  # optional; fall back to a manual required-field check
    try:
        jsonschema.validate(ev, schema)
        return True, ""
    except Exception as e:  # noqa: BLE001
        return False, str(e)


BASE = {"created_at": NOW, "actor": "worker-031"}
R = rel

# schema-typed events: validated against research_map/events.schema.json
EVENTS = [
    {**BASE, "event_id": f"w031-e36-{STAMP}-artifact-report", "event_type": "artifact",
     "node_id": "A1", "gate": "G-AUDIT",
     "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
     "artifact_type": "measurement_report",
     "path": "artifacts/worker-031/classsep_e36_delta/out/report.json",
     "sha256": sha256(HERE / "out/report.json"),
     "validation_status": "unverified",
     "evidence_refs": [
         "artifacts/worker-031/classsep_e36_delta/out/report.json#"
         + sha256(HERE / "out/report.json")[:12],
         "artifacts/worker-031/classsep_e36_delta/README.md#"
         + sha256(HERE / "README.md")[:12],
         "artifacts/worker-031/classsep_e36_delta/measure_e36_delta_031.py#"
         + sha256(HERE / "measure_e36_delta_031.py")[:12],
     ],
     "summary": (
         "W031-CLASSSEP-E36-DELTA-01 measured the 01:06 detector drift "
         "a8c04fc31e4a -> e36b0d644ca7 on frozen, hash-pinned corpora against the audit's "
         "pre-registered adoption bar. Verdict NO_ARM_MEETS_BAR: corpus A PASS 17/0/10/0 for "
         "both arms; sensitivity 4/6 both; specificity 3/10 -> 4/10; HIGH cue-induced FN 1 "
         "both (A04, inherited); w035 battery 13/23 both; hard findings on the r3 snapshot "
         "f344ed2aaea5 (383 claims) 19 -> 16 (labeled FP 17 -> 15, unlabeled 2 -> 1).")},
    {**BASE, "event_id": f"w031-e36-{STAMP}-artifact-instrument", "event_type": "artifact",
     "node_id": "A1", "gate": "G-AUDIT",
     "artifact_type": "measurement_instrument",
     "path": "artifacts/worker-031/classsep_e36_delta/measure_e36_delta_031.py",
     "sha256": sha256(HERE / "measure_e36_delta_031.py"),
     "validation_status": "unverified",
     "evidence_refs": [
         "artifacts/worker-031/classsep_e36_delta/measure_e36_delta_031.py#"
         + sha256(HERE / "measure_e36_delta_031.py")[:12]],
     "summary": ("Deterministic, read-only re-run: python3 "
                 "artifacts/worker-031/classsep_e36_delta/measure_e36_delta_031.py ; "
                 "controls K1-K9; exits 0/2/3.")},
    {**BASE, "event_id": f"w031-e36-{STAMP}-claim", "event_type": "claim",
     "node_id": "A1", "gate": "G-AUDIT",
     "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
     "conclusion_type": "instrument_measurement",
     "assumptions": [
         "the audit r3 adoption bar and LIVE_LABELS are taken verbatim from "
         "artifacts/audit/classsep_calibration.py / classsep_r3_adjudication.py",
         "live counts bind the cited map bytes only (r3 snapshot f344ed2aaea5, 383 claims; "
         "01:05:09 capture 5ab4bed18107, 414 claims); the live map has since grown to 483",
         "corpus A scores a fixture as detected iff findings_for_map + artifact findings are "
         "non-empty, matching the registered runner semantics",
     ],
     "statement": (
         "Artifact-and-checker measurement (not a gate verdict, not a mathematics claim): the "
         "01:06 drift e36b0d644ca7 does not reach the audit's adoption bar. Relative to "
         "a8c04fc31e4a on identical frozen inputs it is a strict precision improvement of two "
         "findings (hard 19 -> 16; labeled FP 17 -> 15; specificity 3/10 -> 4/10) with no "
         "change on any other bar axis (corpus A PASS both; sensitivity 4/6 both; HIGH "
         "cue-induced FN 1 both; battery 13/23 both). The drift is ONE physical line carrying "
         "TWO independent regex additions, each buying exactly one suppression on the frozen "
         "snapshot: (?:or\\s+describes?\\s+)?the (widened quotation exemption) suppresses the "
         "claims[276] finding; 0\\s+genuine\\s+assertions? suppresses claims[306]. Neither "
         "addition is clause-scoped: probes show '0 genuine assertions' matches inside "
         "'10 genuine assertions', the widened exemption suppresses a meta-clause that ALSO "
         "carries a genuine merge assertion in its second clause, and the A04 HIGH cue-FN is "
         "inherited unchanged. (This statement deliberately reports the over-suppression "
         "without reproducing the detector's own toxic composite, so the audit instrument "
         "reads it clean -- the previous revision of this event tripped its own subject.)"),
     "falsifier": (
         "A census in out/report.json not reproducible from its cited pins; a hard finding "
         "moving between the arms without appearing in movers_on_frozen_snapshot; a "
         "NEXT-suppressed labeled assertion that is first-order per the LIVE_LABELS criterion; "
         "or any pinned sha256 mismatching at re-run."),
     "evidence_refs": [
         "artifacts/worker-031/classsep_e36_delta/out/report.json#"
         + sha256(HERE / "out/report.json")[:12],
         "artifacts/worker-031/classsep_e36_delta/pinned/"
         "class_separation.applied.a8c04fc31e4a.py#a8c04fc31e4a",
         "artifacts/worker-031/classsep_e36_delta/pinned/"
         "class_separation.live.e36b0d644ca7.py#e36b0d644ca7",
         "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json#f344ed2aaea5",
         "artifacts/worker-095/classsep_drift_r5_verify/verdict.json#610ed35c0101",
     ]},
    {**BASE, "event_id": f"w031-e36-{STAMP}-review", "event_type": "review",
     "node_id": "A1", "gate": "G-AUDIT",
     "target_id": f"w031-e36-{STAMP}-artifact-report",
     "reviewer": "worker-031", "verdict": "accept", "score": 4.0,
     "review_scope": ("self-review of the worker deliverable only (instrument validity, pin "
                      "discipline, replayability); NOT an F1/F2 schema verdict, NOT a detector "
                      "adoption, NOT a G-AUDIT verdict"),
     "counts_as_full_schema_verdict": False,
     "hard_failures": [],
     "findings": [
         "K1 recovers BOTH additions from the single changed line and reproduces the APPLIED "
         "guard byte-for-byte; a one-addition lineage check would mis-attribute the claims[276] "
         "suppression.",
         "K2: the live detector was already back at a8c04fc31e4a when this run began; the "
         "e36b0d644ca7 bytes are scored from the pinned copy only (window 01:06:12-01:08:14).",
         "K6 expected failures are findings: P_TEN_GENUINE (substring hazard), "
         "P_ASSERTION_A04 (inherited clause-scope HIGH cue-FN), and two "
         "P_QUOTE_DESCRIBE_ASSERTION probes (widened exemption over-suppresses).",
         "K5/K7: censuses are deterministic under a double in-process run; live-map counts bind "
         "the cited snapshots only and the live map has moved to 483 claims.",
         "Self-test: the emitted events were re-scanned with the live detector; the first "
         "revision of the claim event tripped its own subject (CLASSSEP hard finding on a "
         "quoted example), so the wording reports the over-suppression without reproducing the "
         "toxic composite. Both channels now read clean.",
     ],
     "evidence_refs": [
         "artifacts/worker-031/classsep_e36_delta/out/report.json#"
         + sha256(HERE / "out/report.json")[:12],
         "artifacts/worker-031/classsep_e36_delta/SHA256SUMS"]},
]

# lifecycle events: carried by the live outbox stream for every worker, but not typed by
# research_map/events.schema.json (which admits only direction_update/claim/artifact/
# review/resource_request). Marked so no consumer mistakes them for schema-typed events.
LIFECYCLE_EVENTS = [
    {**BASE, "event_id": f"w031-e36-{STAMP}-blocker-unowned-drift", "event_type": "blocker",
     "outside_event_schema": True,
     "node_id": "A1", "gate": "G-AUDIT",
     "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
     "description": (
         "research_map/class_separation.py was written twice with no authorizing artifact "
         "event: a8c04fc31e4a -> e36b0d644ca7 at 01:06:12 and back to a8c04fc31e4a at 01:08:14. "
         "Worker-095 independently reports the same window. The e36b0d window is now measured "
         "(NO_ARM_MEETS_BAR) and the reverted bytes are already the adjudicated arm, but the "
         "canonical bytes for the 01:06 window are not bound by any event."),
     "needed_to_unblock": (
         "controller/audit records an artifact event binding the canonical detector sha256 for "
         "this window (a8c04fc31e4a is live and was the r3 APPLIED arm), states whether the "
         "write-freeze was violated, and directs the next revision to be clause/structure-scoped "
         "rather than window-scoped. No adoption on the current measurements."),
     "evidence_refs": [
         "artifacts/worker-031/classsep_e36_delta/out/report.json#"
         + sha256(HERE / "out/report.json")[:12],
         "artifacts/worker-095/classsep_drift_r5_verify/verdict.json#610ed35c0101",
         "runtime/state/checkpoint_log.jsonl#ckpt-20260912-010641"]},
    {**BASE, "event_id": f"w031-e36-{STAMP}-status", "event_type": "status",
     "outside_event_schema": True,
     "node_id": "A1", "gate": "G-AUDIT", "status": "active", "hours": 0.4,
     "summary": (
         "CHECKPOINT + EXIT. W031-CLASSSEP-E36-DELTA-01 complete at worker level: one "
         "class-bound task, eight hash-pinned deliverables, controls K1-K9 (K6 expected "
         "failures are findings), verdict NO_ARM_MEETS_BAR. No gate verdict, no node status, no "
         "validation_status, no adoption, no claim retirement, no canonical path written."),
     "next_falsifier": (
         "An adoptable revision that is clause/structure-scoped: keeps A04 firing and A01-A12 "
         "on the worker-049 corpus, keeps '10 genuine assertions' firing, clears the labeled "
         "mention FPs, and reaches 27-fixture PASS 17/0/10/0 + sensitivity >=5/6 + specificity "
         ">=9/10 + 0 HIGH cue-induced FN. Re-run this instrument or "
         "artifacts/audit/classsep_r3_adjudication.py at the candidate hash."),
     "evidence_refs": [
         "artifacts/worker-031/classsep_e36_delta/out/report.json#"
         + sha256(HERE / "out/report.json")[:12],
         "artifacts/worker-031/classsep_e36_delta/README.md#"
         + sha256(HERE / "README.md")[:12]]},
]


def main() -> int:
    schema = json.loads(SCHEMA.read_text())
    seen: set[str] = set()
    for path in list((ROOT / "comms/outbox").glob("*.jsonl")) + [OUTBOX, LIFECYCLE_OUTBOX]:
        if not path.exists():
            continue
        for line in path.read_text(errors="replace").splitlines():
            if '"event_id"' in line:
                try:
                    seen.add(json.loads(line).get("event_id"))
                except Exception:  # noqa: BLE001
                    pass
    emitted, skipped, bad = [], [], []
    for ev in EVENTS:
        ok, err = validate(ev, schema)
        if not ok:
            bad.append((ev["event_id"], err))
            continue
        if ev["event_id"] in seen:
            skipped.append(ev["event_id"])
        else:
            emitted.append(ev)
    if bad:
        print("SCHEMA INVALID (fail closed):")
        for eid, err in bad:
            print("  -", eid, err.splitlines()[0] if err else "")
        return 2
    lifecycle = [ev for ev in LIFECYCLE_EVENTS if ev["event_id"] not in seen]
    lifecycle_skipped = [ev["event_id"] for ev in LIFECYCLE_EVENTS if ev["event_id"] in seen]

    def append(path: Path, events: list) -> None:
        if not events:
            return
        with path.open("a") as fh:
            for ev in events:
                fh.write(json.dumps(ev, sort_keys=True) + "\n")

    append(OUTBOX, emitted)
    append(LIFECYCLE_OUTBOX, lifecycle)
    print(f"schema-typed emitted: {len(emitted)} skipped(idempotent): {len(skipped)} "
          f"-> {rel(OUTBOX)}")
    for ev in emitted:
        print("  +", ev["event_id"])
    for eid in skipped:
        print("  =", eid)
    print(f"lifecycle emitted: {len(lifecycle)} skipped(idempotent): {len(lifecycle_skipped)} "
          f"-> {rel(LIFECYCLE_OUTBOX)}")
    for ev in lifecycle:
        print("  +", ev["event_id"])
    for eid in lifecycle_skipped:
        print("  =", eid)
    for p in (OUTBOX, LIFECYCLE_OUTBOX):
        if p.exists():
            print("  ", rel(p), sha256(p)[:12])
    return 0


if __name__ == "__main__":
    sys.exit(main())
