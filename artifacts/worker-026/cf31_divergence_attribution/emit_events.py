#!/usr/bin/env python3
"""Emit W026-CF31-DIVERGENCE-ATTRIBUTION-01 events to comms/outbox/worker-026.jsonl.

Idempotent: an event_id already present in the outbox is skipped. Appends one JSON object per
line, per comms/PROTOCOL.md. Worker events do not set status=done, validation_status=passed or
any gate verdict.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms" / "outbox" / "worker-026.jsonl"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).replace(microsecond=0).isoformat()
TAG = "w026-cf31-20260912T0121"
TASK = "W026-CF31-DIVERGENCE-ATTRIBUTION-01"


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref(name: str) -> str:
    return f"artifacts/worker-026/cf31_divergence_attribution/{name}#{sha(HERE / name)[:12]}"


def load_events() -> list[dict]:
    if not OUTBOX.exists():
        return []
    out = []
    for line in OUTBOX.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def main() -> int:
    rep = json.loads((HERE / "report.json").read_text())
    man = json.loads((HERE / "MANIFEST.json").read_text())
    ctl = json.loads((HERE / "controls.json").read_text())
    rea = json.loads((HERE / "reanchor.json").read_text())
    f2b = rep["mutation_census_summary"]
    flip = next(h for h in json.loads((HERE / "mutation_census.json").read_text())["flips"]
                if h["review"] == "F2b-review-worker-072-rev29.json")

    base = {"actor": "worker-026", "created_at": NOW, "node_id": "F2b",
            "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM"}
    ev = []

    ev.append({**base, "event_id": f"{TAG}-task-claim", "event_type": "status", "status": "active",
               "hours": 0.4,
               "summary": (f"{TASK} taken: no assignment card exists in comms/inbox/worker-026.jsonl in "
                           "this fleet wave, so ONE bounded class-bound task was taken from the live "
                           "critical path (CF-31, G-FORM F2b coverage-count divergence). Read-only "
                           "attribution of the divergence MECHANISM; does not write the lead-audit "
                           "binding table reviews/G-FORM-final-verify-r3.json and does not adjudicate "
                           "which count is gate-correct."),
               "evidence_refs": ["comms/PROTOCOL.md",
                                 "research_map/research_map.json#controller_findings",
                                 ref("REPORT.md")],
               "next_falsifier": rep["falsifier"]})

    for name in ["REPORT.md", "report.json", "attribute.py", "corpus_manifest.json", "lattice.json",
                 "mutation_census.json", "snapshot_replay.json", "controls.json", "reanchor.json",
                 "MANIFEST.json", "CHECKPOINT.json", "SHA256SUMS"]:
        ev.append({**base, "event_id": f"{TAG}-artifact-{name.replace('.', '_')}",
                   "event_type": "artifact", "artifact_type": "worker_report",
                   "path": f"artifacts/worker-026/cf31_divergence_attribution/{name}",
                   "sha256": sha(HERE / name), "validation_status": "unverified",
                   "summary": f"{TASK} deliverable: {name}",
                   "evidence_refs": [ref("MANIFEST.json")]})

    ev.append({**base, "event_id": f"{TAG}-claim", "event_type": "claim",
               "class_ids": rep["class_ids"], "conclusion_type": "formal_model",
               "statement": (
                   "Artifact-and-instrument result (not a mathematics claim). CF-31's F2b "
                   "coverage-count divergence has two independent, byte-proven causes and is NOT a "
                   "simple 'one method is wrong'. (1) TEMPORAL IN-PLACE REWRITE: "
                   "reviews/F2b-review-worker-072-rev29.json exists in two byte-states under one "
                   f"filename - accept (sha256 {flip['copy_sha256'][:12]}, {flip['copy_bytes']} B, "
                   f"preserved at {flip['copy']}) and revise (sha256 {flip['live_sha256'][:12]}, "
                   f"{flip['live_bytes']} B, mtime {flip['live_mtime_iso']}), same declared "
                   "created_at, no revision marker. Replaying the corpus from preserved bytes "
                   "reproduces 3/4 persisted controller scans exactly, including "
                   "astra-lifecycle-08-open (4 accepts incl. worker-072) and astra-lifecycle-08-final "
                   "(3 accepts), so this single rewrite fully explains the controller's own 4->3 "
                   "move. (2) METHOD-C TARGET BLIND SPOT: astra_lifecycle.py::_targets_in_review "
                   "reads only target_id/target/target_subnode, so reviews identifying their node by "
                   "a top-level node_id, or by a 'path#hash' target_id, are invisible to the "
                   "controller scan (control C14), biasing counts downward. (3) The lead's stated "
                   "'0 accept / 7 revise' is NOT reproducible from surviving bytes: 0 of 96 tested "
                   "census-rule combinations reproduce it at live bytes or at a corpus reconstructed "
                   "at the lead's census instant (01:13). corpus_manifest digest "
                   f"{rep['corpus']['corpus_digest'][:12]}, {rep['corpus']['files']} files. Controls "
                   f"{ctl['passed']}/{ctl['total']} pass including the C0 anchor against both the "
                   f"measurement-time instrument 548329414083 and the post-move instrument "
                   f"{rea['instrument_sha256_now'][:12]}. NO gate verdict is set here."),
               "assumptions": [
                   "the controller scan semantics are those of astra_lifecycle.review_coverage at pin 548329414083 (behaviourally reproduced at b155313797c0)",
                   "a preserved copy's mtime is a lower bound on its revision's age (declared rule; one replay miss is attributed to it)",
                   "reviews/*.json is the complete review corpus at measurement time",
                   "this worker is not an author of any F2b artifact and has not written reviews/, schemas/ or research_map/"],
               "falsifier": rep["falsifier"],
               "artifact_refs": [ref("report.json"), ref("mutation_census.json"),
                                 ref("snapshot_replay.json"), ref("lattice.json"),
                                 ref("controls.json"), ref("reanchor.json")],
               "evidence_refs": [
                   flip["copy"], "reviews/F2b-review-worker-072-rev29.json",
                   "runtime/state/controller_verification/lifecycle_20260912-011239.json",
                   "runtime/state/controller_verification/lifecycle_20260912-011626.json",
                   "reviews/W048-GFORM-COVERAGE-RECOUNT-01.json",
                   "comms/outbox/astra-lead-formulation.jsonl#lead-form-20260912T0113-107"]})

    ev.append({**base, "event_id": f"{TAG}-review-instrument", "event_type": "review",
               "target_id": "research_map/astra_lifecycle.py::review_coverage",
               "reviewer": "worker-026", "verdict": "revise", "score": 3.0,
               "hard_failures": [
                   "_targets_in_review ignores a top-level node_id, so a review that names its node only there is invisible to the coverage scan (demonstrated by control C14)"],
               "findings": [
                   f"target-extraction blind spot (top-level node_id and path#hash target_id)",
                   f"review-corpus mutability: {f2b['verdict_flips']} verdict flips across {f2b['copies_scanned']} preserved copies of live review files",
                   "counts are not snapshot-stable: the same instrument published F2b 0, then 2, then 3, then 4, then 3 across five consecutive passes on a mutating corpus"],
               "evidence_refs": [ref("report.json"), ref("lattice.json"), ref("mutation_census.json"),
                                 "runtime/state/controller_verification/lifecycle_20260912-011626.json"],
               "summary": ("Advisory worker review of the coverage instrument, not of a schema and not "
                           "of a verdict. The instrument is not wrong in its arithmetic - it "
                           "reproduces exactly and the reimplementation matches it (C0) - but its "
                           "target extraction is incomplete and its inputs are mutable under fixed "
                           "names. No gate verdict; the instrument is frozen by REC-29/CF-29 and this "
                           "review does not authorise any write to it.")})

    ev.append({**base, "event_id": f"{TAG}-blocker-adjudication", "event_type": "blocker",
               "description": (
                   "CF-31 cannot be closed from surviving bytes alone. The lead's published F2b "
                   "'0 accept / 7 revise' at b2ab6acb2bbe is not reproducible by any of 96 tested "
                   "census-rule combinations on the live corpus or on a corpus reconstructed at the "
                   "lead's 01:13 census instant (0 matches); the unbound any-revision F2b count is 32 "
                   "revise / 12 accept, also not 7. The controller's 4 and 3 ARE reproducible at "
                   "their own instants, but only the 3 is reproducible from live bytes - the 4 "
                   "requires the preserved pre-rewrite accept bytes. Separately, "
                   "research_map/astra_lifecycle.py was rewritten at 01:21:29 DURING this task "
                   "(548329414083 -> b155313797c0); review_coverage is behaviourally unchanged "
                   "(re-anchor C0 passes) but the move is unauthorised-until-recorded in the "
                   "CF-26/CF-29 sense. astra-life05-verify-gform-r3 cannot publish a binding table "
                   "that reconciles the two counts without the lead's per-file list."),
               "needed_to_unblock": (
                   "astra-lead-formulation publishes the per-file census list behind 'F2b 0 accept / "
                   "7 revise' (filename, reviewer, verdict, reviewed_sha256, verdict mtime) so it can "
                   "be diffed against the controller verdict set; and the controller records the "
                   "01:21:29 astra_lifecycle.py move as a finding (hash-pinned) or voids it."),
               "evidence_refs": [ref("report.json"), ref("lattice.json"), ref("reanchor.json"),
                                 "reviews/W048-GFORM-COVERAGE-RECOUNT-01.json",
                                 "runtime/state/controller_verification/lifecycle_20260912-011626.json"]})

    ev.append({**base, "event_id": f"{TAG}-status-complete", "event_type": "status",
               "status": "active", "hours": 0.4,
               "summary": (f"CHECKPOINT + EXIT. {TASK} complete at worker level: ONE bounded "
                           "class-bound task, "
                           f"{ctl['passed']}/{ctl['total']} controls, canonical tree untouched "
                           "(schemas/af_*_vacuum.yaml unchanged at d9cebb9404b2/e9a27996dfd3/"
                           "b2ab6acb2bbe; reviews/, research_map/ not written by this worker). "
                           "Verdict TEMPORAL_INPLACE_REWRITE__PLUS_METHOD_C_TARGET_BLINDSPOT. "
                           "Worker checkpoint runtime/state/w026_cf31_divergence_checkpoint.json. "
                           "No gate verdict, no node status, no validation_status promotion - "
                           "promotion is the controller's/lead's."),
               "evidence_refs": [ref("report.json"), ref("CHECKPOINT.json"), ref("MANIFEST.json"),
                                 "runtime/state/w026_cf31_divergence_checkpoint.json"],
               "next_falsifier": rep["falsifier"]})

    seen = {e.get("event_id") for e in load_events()}

    # ERRATUM: finalize.py may be re-run after an emission, which changes the three META files
    # (MANIFEST.json / CHECKPOINT.json / SHA256SUMS) while their previously emitted artifact events
    # are already ingested. The tag is derived from the current MANIFEST.json hash, so each
    # distinct manifest state produces exactly one erratum and re-running with a stable manifest is
    # a no-op. No measurement ever changes in an erratum.
    etag = f"w026-cf31r-{sha(HERE / 'MANIFEST.json')[:12]}"
    ev.append({**base, "event_id": f"{etag}-erratum", "event_type": "status", "status": "active",
               "hours": 0.0,
               "summary": ("ERRATUM (no measurement changed): the three META files "
                           "MANIFEST.json / CHECKPOINT.json / SHA256SUMS were rewritten by a "
                           "finalize.py re-run after their artifact events had been ingested, so the "
                           "event-cited sha256 for those three was stale. Corrected hashes are "
                           "re-emitted under tag " + etag + ". report.json, mutation_census.json, "
                           "snapshot_replay.json, lattice.json, controls.json, reanchor.json, "
                           "corpus_manifest.json, attribute.py and REPORT.md are UNCHANGED and their "
                           "originally emitted hashes still verify."),
               "evidence_refs": [ref("SHA256SUMS"), ref("MANIFEST.json"), ref("CHECKPOINT.json")],
               "next_falsifier": rep["falsifier"]})
    for name in ["MANIFEST.json", "CHECKPOINT.json", "SHA256SUMS"]:
        ev.append({**base, "event_id": f"{etag}-artifact-{name.replace('.', '_')}",
                   "event_type": "artifact", "artifact_type": "worker_report",
                   "path": f"artifacts/worker-026/cf31_divergence_attribution/{name}",
                   "sha256": sha(HERE / name), "validation_status": "unverified",
                   "summary": f"{TASK} deliverable (erratum hash): {name}",
                   "evidence_refs": [ref("SHA256SUMS")]})

    added = 0
    with OUTBOX.open("a") as fh:
        for e in ev:
            if e["event_id"] in seen:
                continue
            fh.write(json.dumps(e, sort_keys=False) + "\n")
            added += 1
    print(json.dumps({"outbox": str(OUTBOX.relative_to(ROOT)), "emitted": added,
                      "skipped_existing": len(ev) - added, "total_events": len(ev)},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
