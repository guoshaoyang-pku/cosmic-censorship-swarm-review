#!/usr/bin/env python3
"""W038-F0-CONFORMANCE-01 addendum: canonical F0 moved mid-task.

Timeline (all times +08:00, measured):
  00:29:53  pins measured: F0 = 276009f4 (rev4)
  00:31:07  run manifest complete; hash stable before==after; verdict accept (11 PASS / 0 FAIL)
  00:31:41  F0 rev5 written (written_at in the file); hash 0abb9ed8; supplement also moved c8e979a1 -> d7419b4e
  00:32:03  this worker detects the move
  ~00:33    rev5 probe: declared checker 253/0/37 pass; own checker 10 PASS / 1 FAIL (IND-06 only:
            FROZEN.json rev26 still pins the superseded rev4 F0 and the old supplement)

Writes:
  artifacts/worker-038/f0_conformance/moving_target_report.json
  comms/outbox/worker-038.jsonl   (append: artifact + blocker)
  runtime/state/w038_checkpoint_3.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).replace(microsecond=0).isoformat()
STAMP = NOW.replace(":", "").replace("+", "").replace("-", "")[:15]
D = Path(__file__).resolve().parent
F0 = "research_map/formulation_taxonomy.yaml"
SUP = "artifacts/formulation/formulation_taxonomy.yaml"


def sha(p: str) -> str:
    h = hashlib.sha256()
    with (ROOT / p).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    pins = {
        F0: sha(F0),
        SUP: sha(SUP),
        "artifacts/formulation/FROZEN.json": sha("artifacts/formulation/FROZEN.json"),
        "artifacts/worker-038/f0_conformance/report.json": sha("artifacts/worker-038/f0_conformance/report.json"),
        "reviews/F0-conformance-038.json": sha("reviews/F0-conformance-038.json"),
    }
    probe = json.loads((D / "independent_checks_rev5_probe.json").read_text())
    probe_fail = [c["id"] for c in probe["checks"] if c["status"] == "FAIL"]
    frozen = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    la = frozen.get("logical_artifacts", {})

    report = {
        "task": "W038-F0-CONFORMANCE-01-ADDENDUM",
        "worker": "worker-038",
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": probe["class_ids"],
        "kind": "moving_target_addendum",
        "reviewed_revision": {
            "path": F0, "sha256": "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc",
            "revision_field": 4, "review_verdict": "accept",
            "snapshot": "artifacts/worker-038/f0_conformance/snapshots/formulation_taxonomy.276009f4f63d.yaml",
        },
        "current_revision_at_detection": {
            "path": F0, "sha256": pins[F0], "revision_field": 5,
            "written_at_field": "2026-09-12T00:31:41+08:00",
            "snapshot": "artifacts/worker-038/f0_conformance/snapshots/formulation_taxonomy.0abb9ed8a961.yaml",
        },
        "timeline": [
            {"t": "2026-09-12T00:29:53+08:00", "event": "pins measured; F0 rev4 = 276009f4"},
            {"t": "2026-09-12T00:31:07+08:00", "event": "run manifest complete; pins before==after; verdict accept (11 PASS / 0 FAIL)"},
            {"t": "2026-09-12T00:31:41+08:00", "event": "F0 rev5 written; F0 = 0abb9ed8; supplement c8e979a1 -> d7419b4e"},
            {"t": "2026-09-12T00:32:03+08:00", "event": "this worker detects the canonical-path move"},
            {"t": NOW, "event": "rev5 probe: declared checker 253/0/37 pass; own checker 10 PASS / 1 FAIL (IND-06 only)"},
        ],
        "rev5_probe": {
            "f0_sha256": pins[F0],
            "hash_stable_across_probe": probe["pins"]["before"] == probe["pins"]["after"],
            "declared_checker": json.loads((D / "worker01_validation_rev5_probe.json").read_text()),
            "independent_summary": probe["summary"],
            "independent_failed_checks": probe_fail,
            "interpretation": ("rev5 passes every content check (class ids, recomputed disjointness, "
                               "G2/G3, variants, rubric axes); the single FAIL is IND-06 because "
                               "FROZEN.json rev26 still pins the superseded F0 276009f4 and the old "
                               "supplement c8e979a1. The content fix itself (D1/D3 discharge for "
                               "AF-WCC-SCALAR-SPH, canonical schema_owner pointers) is consistent "
                               "with the check results."),
        },
        "frozen_manifest_state": {
            "path": "artifacts/formulation/FROZEN.json",
            "revision": frozen.get("revision"),
            "frozen_at": frozen.get("frozen_at"),
            "pins_f0": la.get("F0-declared-taxonomy", {}).get("sha256"),
            "pins_supplement": la.get("F0-class-contract-supplement", {}).get("sha256"),
            "measured_f0": pins[F0],
            "measured_supplement": pins[SUP],
            "drift": True,
        },
        "consequence": ("Under the controller rule that verdicts bound to superseded hashes are "
                        "advisory only, the W038 accept applies to the rev4 snapshot 276009f4 and "
                        "does NOT bind to rev5 0abb9ed8. Rev5 is not reviewable as a frozen revision "
                        "until FROZEN.json is re-emitted against it."),
        "required_next": ("lead-formulation re-freezes FROZEN.json (rev27) naming F0 0abb9ed8 and "
                          "supplement d7419b4e; then a fresh independent full-schema review of rev5 is "
                          "run, by a reviewer other than worker-038 if this worker's rev4 accept is "
                          "counted, so that G-F0 reaches two distinct accepts at one hash."),
        "falsifier": ("a reader who shows the canonical F0 hash was already 0abb9ed8 at 00:31:07 (the "
                      "rev4 run would then be mis-bound), or that FROZEN.json pins 0abb9ed8, or that "
                      "rev5 changes class semantics beyond the rev5 note, refutes the corresponding "
                      "statement in this addendum."),
        "claims_not_made": [
            "no gate verdict, no node done/passed status",
            "no verdict on rev5 (probe results are diagnostics, not a review verdict)",
            "no physics result, no theorem",
        ],
        "authority_note": "worker evidence only; controller/leads decide gate and node status",
        "evidence_refs": [
            f"{F0}#{pins[F0]}",
            f"{SUP}#{pins[SUP]}",
            f"artifacts/formulation/FROZEN.json#{pins['artifacts/formulation/FROZEN.json']}",
            f"artifacts/worker-038/f0_conformance/report.json#{pins['artifacts/worker-038/f0_conformance/report.json']}",
            f"artifacts/worker-038/f0_conformance/independent_checks_rev5_probe.json#{sha('artifacts/worker-038/f0_conformance/independent_checks_rev5_probe.json')}",
            f"reviews/F0-conformance-038.json#{pins['reviews/F0-conformance-038.json']}",
        ],
    }
    mt = D / "moving_target_report.json"
    mt.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    mt_sha = sha("artifacts/worker-038/f0_conformance/moving_target_report.json")

    evidence = report["evidence_refs"] + [f"artifacts/worker-038/f0_conformance/moving_target_report.json#{mt_sha}"]
    common = {"actor": "worker-038", "created_at": NOW, "class_ids": report["class_ids"],
              "gate": "G-F0", "node_id": "F0"}
    events = [
        dict(common, event_id=f"w038-f0-conformance-moving-target-artifact-{STAMP}",
             event_type="artifact", artifact_type="f0_moving_target_addendum",
             path="artifacts/worker-038/f0_conformance/moving_target_report.json", sha256=mt_sha,
             validation_status="unverified", evidence_refs=evidence,
             summary=("canonical F0 moved 276009f4 -> 0abb9ed8 at 00:31:41 immediately after the "
                      "W038 accept run; rev5 probe 10/11 with the only FAIL being the stale FROZEN "
                      "pin; the W038 accept is advisory on the rev4 snapshot.")),
        dict(common, event_id=f"w038-f0-conformance-moving-target-blocker-{STAMP}",
             event_type="blocker",
             description=("F0 moved mid-review: the canonical taxonomy is rev5 0abb9ed8 but "
                          "FROZEN.json rev26 still pins rev4 276009f4 and supplement c8e979a1 "
                          "(measured supplement now d7419b4e). Any verdict at 276009f4 is "
                          "superseded-hash advisory; rev5 content checks pass but the revision is "
                          "not frozen, so a binding G-F0 verdict cannot be issued yet."),
             needed_to_unblock=("lead-formulation re-emits FROZEN.json naming F0 0abb9ed8 and the "
                                "supplement d7419b4e (revision 27); then two independent reviewers "
                                "accept that frozen revision."),
             evidence_refs=evidence,
             blocker_kind="publication_drift"),
    ]
    out = ROOT / "comms/outbox/worker-038.jsonl"
    existing = set()
    for line in out.read_text(encoding="utf-8").splitlines():
        try:
            existing.add(json.loads(line).get("event_id"))
        except Exception:
            pass
    written = []
    with out.open("a", encoding="utf-8") as f:
        for ev in events:
            validate_event(ev)
            if ev["event_id"] in existing:
                continue
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
            written.append(ev["event_id"])

    files = [
        "artifacts/worker-038/f0_conformance/moving_target_report.json",
        "artifacts/worker-038/f0_conformance/independent_checks_rev5_probe.json",
        "artifacts/worker-038/f0_conformance/worker01_validation_rev5_probe.json",
        "artifacts/worker-038/f0_conformance/40_checker_rev5_probe.log",
        "artifacts/worker-038/f0_conformance/41_independent_rev5_probe.log",
        "artifacts/worker-038/f0_conformance/rev5_probe_pin_before.txt",
        "artifacts/worker-038/f0_conformance/rev5_probe_pin_after.txt",
        "artifacts/worker-038/f0_conformance/snapshots/formulation_taxonomy.0abb9ed8a961.yaml",
        "artifacts/worker-038/f0_conformance/snapshots/formulation_taxonomy_supplement.d7419b4e8963.yaml",
        "reviews/F0-conformance-038.json",
        "comms/outbox/worker-038.jsonl",
    ]
    ckpt = {
        "worker": "worker-038",
        "checkpoint": 3,
        "run": "W038-F0-CONFORMANCE-01-ADDENDUM",
        "at": NOW,
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": report["class_ids"],
        "verdicts": {
            "reviewed_rev4": {"sha256": report["reviewed_revision"]["sha256"], "verdict": "accept",
                              "binding": "advisory only (superseded hash)"},
            "rev5_probe": {"sha256": pins[F0], "declared_checker": "253/0/37 pass",
                           "independent": f"{probe['summary']['passed']} pass / {probe['summary']['failed']} fail",
                           "failed_checks": probe_fail, "binding": "diagnostic only, not a verdict"},
            "frozen_manifest": {"pins_f0": la.get("F0-declared-taxonomy", {}).get("sha256"),
                                "measured_f0": pins[F0], "drift": True},
        },
        "final_hashes": {p: sha(p) for p in files},
        "artifacts": {p: {"sha256": sha(p)} for p in files},
        "outbox_events": [
            "w038-f0-conformance-artifact-20260912T003150",
            "w038-f0-conformance-checker-20260912T003150",
            "w038-f0-conformance-review-20260912T003150",
            "w038-f0-conformance-status-20260912T003150",
        ] + written,
        "rejected_events": [],
        "next_falsifier": report["falsifier"],
        "hours_spent_estimate": 0.5,
        "numerics_lock": "respected: no N1 work, no self-gravitating solver written or run",
        "open_blockers": {
            "F0-FREEZE-DRIFT": ("FROZEN.json rev26 pins the superseded F0 276009f4 / supplement "
                                "c8e979a1; canonical files are rev5 0abb9ed8 / d7419b4e. Re-freeze "
                                "required before any binding G-F0 verdict."),
            "G-F0-SECOND-ACCEPT": ("one advisory accept exists at the rev4 hash; after re-freeze, "
                                   "two distinct accepts at the new hash are still required."),
        },
        "status": {"delivered": True, "result": "ACCEPT(rev4, advisory) + MOVING-TARGET addendum",
                   "validation_status": "unverified",
                   "no_completion_claim": "no gate verdict; F0 remains draft_unverified"},
    }
    (ROOT / "runtime/state/w038_checkpoint_3.json").write_text(
        json.dumps(ckpt, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"moving_target_report": str(mt), "sha256": mt_sha,
                      "events_written": written,
                      "checkpoint_3_sha256": sha("runtime/state/w038_checkpoint_3.json")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
