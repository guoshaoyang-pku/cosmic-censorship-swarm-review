#!/usr/bin/env python3
"""Emit the W087-GFORM-INDEP-04 upward events to comms/outbox/worker-087.jsonl.

Re-runnable: refuses to append an event_id that already exists in the outbox. Validates
every event against research_map/schemas.py before writing. The controller owns ingest
into research_map/events.jsonl; this script only writes the outbox and the local
events_emitted.json record.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TASK = "W087-GFORM-INDEP-04"
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
OUTBOX = ROOT / "comms" / "outbox" / "worker-087.jsonl"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    now = datetime.now(CST).isoformat(timespec="seconds")
    tag = "w087-20260912T0058"
    rep = HERE / "report.json"
    ins = HERE / "audit_gform_independence.py"
    rd = HERE / "README.md"
    rep_sha, ins_sha, rd_sha = sha(rep), sha(ins), sha(rd)
    report = json.loads(rep.read_text())
    digest = report["verdict_digest_sha256"]
    evidence = [
        f"artifacts/worker-087/gform_independence/report.json#{rep_sha[:12]}",
        f"artifacts/worker-087/gform_independence/audit_gform_independence.py#{ins_sha[:12]}",
        f"artifacts/worker-087/gform_independence/README.md#{rd_sha[:12]}",
        "artifacts/formulation/FROZEN.json#3d9e3d77fd87",
        "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
        "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
        "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
        "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
    ]
    common = {"event_type": "artifact", "created_at": now, "actor": "worker-087",
              "node_id": "F1", "gate": "G-FORM", "class_id": CLASSES[0], "class_ids": CLASSES,
              "task_id": TASK}
    events = [
        {**common, "event_id": f"{tag}-artifact-instrument", "artifact_type": "audit_instrument",
         "path": "artifacts/worker-087/gform_independence/audit_gform_independence.py",
         "sha256": ins_sha, "validation_status": "unverified",
         "note": ("Standalone G-FORM accept-independence and freeze-state instrument: strict target binding, "
                  "primary-hash binding, one verdict per reviewer, character-shingle + evidence-channel "
                  "clustering, manifest/mirror/announcement re-measure, 8 fail-closed controls, exit 0 criteria "
                  "met / 3 gap or transition / 2 moving target / 4 control failure."),
         "evidence_refs": evidence},
        {**common, "event_id": f"{tag}-artifact-report", "artifact_type": "gform_independence_and_freeze_report",
         "path": "artifacts/worker-087/gform_independence/report.json",
         "sha256": rep_sha, "validation_status": "unverified",
         "note": (f"Snapshot {report['created_at']}. State REPINNED_ANNOUNCEMENT_PENDING: rev-28 -> rev-13 rewrite "
                  f"(F1 d9cebb94, F2a e9a27996, F2b b2ab6acb), FROZEN rev29 (3d9e3d77) internally consistent with "
                  f"aligned authoring mirrors and refreshed f0_binding evidence pins, but 0/3 accepted-stream "
                  f"owner artifact announcements for the new canonical hashes. Rev-28 coverage (void) F1 1 / F2a 1 "
                  f"/ F2b 2 clusters; rev-13 coverage F1 0 / F2a 2 / F2b 1. Verdict digest {digest[:12]}."),
         "evidence_refs": evidence},
        {**common, "event_id": f"{tag}-claim-rev29-announce", "event_type": "claim",
         "conclusion_type": "formal_model",
         "statement": (
             f"Artifact/provenance measurement at the accepted-stream snapshot {report['created_at']} "
             "(worker-087, W087-GFORM-INDEP-04). (1) The three canonical G-FORM schemas were rewritten at "
             "2026-09-12T00:53:20-00:53:40 to declared revision 13: F1 d9cebb9404b2, F2a e9a27996dfd3, "
             "F2b b2ab6acb2bbe. FROZEN.json was re-pinned to revision 29 (sha 3d9e3d77fd87, frozen_at "
             "2026-09-12T00:55:02+08:00); its entries match disk with 0 canonical and 0 authoring mismatches, "
             "the authoring mirrors are byte-aligned for all three, and each schema's "
             "f0_binding.consistency_evidence_sha256 now equals the measured evidence sha 9e335e9ba1bf. "
             "(2) No owner artifact event in the accepted stream announces any of the three new canonical "
             "hashes (0/3); the re-pin is recorded only inside the manifest rev29_delta, so the accepted-stream "
             "publication act required by PROTOCOL rule 2 / CF-19 is outstanding. (3) Under strict target "
             "binding, primary-hash binding, one-verdict-per-reviewer and the full-schema/advisory split, the "
             "rev-28 pins held effective independent full-schema accept clusters F1 1 (worker-061), F2a 1 "
             "(worker-089), F2b 2 (worker-089, worker-098): the G-FORM two-independent-accepts criterion was "
             "not met there, and those verdicts are void after the 00:53 rewrite. The controller's 00:43 audit "
             "credited F1 to worker-088, but worker-088's own amended review at 00:39:02 is a revise (3.5). "
             "(4) At the rev-13 bytes the current tally is F1 0, F2a 2 (worker-017, worker-072), F2b 1 "
             "(worker-061); the criterion is not yet met at the new hash either. Instrument controls 8/8, "
             f"deterministic digest {digest}. This is a provenance/coverage measurement, not a schema review; "
             "no gate verdict, node status or validation_status=passed is claimed."),
         "assumptions": [
             "the accepted stream plus outbox records are the published verdict record; outbox copies are pre-ingest equivalents",
             "a review binds only the revision named by its primary declared hash field (a rev-13 review is not a rev-28 verdict)",
             "reviews whose target is another review or a derived checkpoint, or that declare counts_as_full_schema_verdict=false, are advisory and do not count toward the gate criterion",
             "the 0.6 shingle-Jaccard and evidence-channel signature rule is a stated dedup rule, not a claim about reviewer psychology",
             "the owner of a canonical path is the only actor that can announce its new bytes; no canonical byte was written by this worker"],
         "falsifier": report["falsifier"],
         "evidence_refs": evidence,
         "artifact_refs": [f"artifacts/worker-087/gform_independence/report.json#{rep_sha[:12]}",
                           f"artifacts/worker-087/gform_independence/audit_gform_independence.py#{ins_sha[:12]}"],
         "next_falsifier": ("an accepted-stream owner artifact event for each rev-13 canonical hash; or two fresh "
                            "independent full-schema accepts at F1 d9cebb94 and F2b b2ab6acb")},
        {**common, "event_id": f"{tag}-blocker-f1", "event_type": "blocker", "class_id": CLASSES[0],
         "description": ("F1 at the rev-13 bytes d9cebb9404b2 has 0 full-schema accepts (bound positions: 1 "
                         "accept advisory/non-full, 1 inconclusive, 3 revise), and no accepted-stream artifact "
                         "event announces schemas/af_wcc_vacuum.yaml sha d9cebb9404b2. Its rev-28 accept "
                         "(worker-061 at cce9c601) is void because the bytes moved."),
         "needed_to_unblock": ("owner artifact event for schemas/af_wcc_vacuum.yaml#d9cebb9404b2, then two "
                               "independent full-schema accepts bound to that hash"),
         "evidence_refs": evidence},
        {**common, "event_id": f"{tag}-blocker-f2b", "event_type": "blocker", "class_id": CLASSES[2],
         "description": ("F2b at the rev-13 bytes b2ab6acb2bbe has 1 full-schema accept (worker-061) and 3 "
                         "revise positions; rev-29 re-pin announcement for schemas/af_scc_c0_vacuum.yaml sha "
                         "b2ab6acb2bbe is absent from the accepted stream. One more independent full-schema "
                         "accept is needed at the new hash."),
         "needed_to_unblock": ("owner artifact event for schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe, then one "
                               "independent full-schema accept bound to that hash"),
         "evidence_refs": evidence},
        {**common, "event_id": f"{tag}-status-exit", "event_type": "status", "status": "active", "hours": 1.0,
         "summary": (f"W087-GFORM-INDEP-04 complete: bounded class-bound task self-assigned from the live G-FORM "
                     f"coverage gap (no inbox card). Deliverables under artifacts/worker-087/gform_independence/ "
                     f"(instrument {ins_sha[:12]}, report {rep_sha[:12]}, README {rd_sha[:12]}, sha256 sidecars). "
                     f"Verdict REPINNED_ANNOUNCEMENT_PENDING: rev-28->rev-13 rewrite, FROZEN rev29 internally "
                     f"consistent with aligned mirrors and refreshed evidence pins, but 0/3 owner announcements "
                     f"in the accepted stream; rev-28 coverage void (F1 1 / F2a 1 / F2b 2 clusters) and rev-13 "
                     f"coverage short (F1 0 / F2a 2 / F2b 1). Controls 8/8, three consecutive runs stable "
                     f"(digest {digest[:12]}). Worker cannot set status=done, validation_status=passed or any "
                     f"gate verdict; blockers {tag}-blocker-f1 and {tag}-blocker-f2b record the gaps."),
         "evidence_refs": evidence,
         "next_falsifier": ("owner artifact announcement for each rev-13 canonical hash; fresh full-schema accepts "
                            "at F1 d9cebb94 and F2b b2ab6acb; or a re-run changing a cluster count or the freeze "
                            "state")},
    ]

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text(errors="replace").splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    existing.add(json.loads(line).get("event_id"))
                except ValueError:
                    pass
    for ev in events:
        validate_event(ev)
        if ev["event_id"] in existing:
            raise SystemExit(f"refusing duplicate event_id {ev['event_id']}")
    with OUTBOX.open("a") as f:
        for ev in events:
            f.write(json.dumps(ev, sort_keys=True) + "\n")
    emitted = {
        "at": now, "outbox": "comms/outbox/worker-087.jsonl", "task_id": TASK,
        "event_ids": [ev["event_id"] for ev in events],
        "event_sha256": [hashlib.sha256(json.dumps(ev, sort_keys=True).encode()).hexdigest()[:12] for ev in events],
        "pins": {"instrument": ins_sha, "report": rep_sha, "readme": rd_sha, "verdict_digest": digest},
    }
    (HERE / "events_emitted.json").write_text(json.dumps(emitted, indent=1, sort_keys=True) + "\n")
    print(json.dumps(emitted, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
