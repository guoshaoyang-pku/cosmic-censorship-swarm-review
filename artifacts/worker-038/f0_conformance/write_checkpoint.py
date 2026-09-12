#!/usr/bin/env python3
"""Write runtime/state/w038_checkpoint_2.json for W038-F0-CONFORMANCE-01.

Binds the delivered artifact set by measured sha256 at checkpoint time. Worker
evidence only; records no done/passed status and no gate verdict.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).replace(microsecond=0).isoformat()

FILES = [
    "artifacts/worker-038/f0_conformance/README.md",
    "artifacts/worker-038/f0_conformance/check_f0_independent.py",
    "artifacts/worker-038/f0_conformance/run.sh",
    "artifacts/worker-038/f0_conformance/run_manifest.txt",
    "artifacts/worker-038/f0_conformance/worker01_validation.json",
    "artifacts/worker-038/f0_conformance/independent_checks.json",
    "artifacts/worker-038/f0_conformance/report.json",
    "artifacts/worker-038/f0_conformance/build_report.py",
    "artifacts/worker-038/f0_conformance/emit_events.py",
    "artifacts/worker-038/f0_conformance/10_checker_selftest.log",
    "artifacts/worker-038/f0_conformance/20_checker_main.log",
    "artifacts/worker-038/f0_conformance/30_independent.log",
    "artifacts/worker-038/f0_conformance/snapshots/SHA256SUMS",
    "artifacts/worker-038/f0_conformance/snapshots/formulation_taxonomy.276009f4f63d.yaml",
    "artifacts/worker-038/f0_conformance/snapshots/formulation_taxonomy_supplement.c8e979a1eb48.yaml",
    "artifacts/worker-038/f0_conformance/snapshots/evaluation_rubric.d748a9e3574e.yaml",
    "artifacts/worker-038/f0_conformance/snapshots/validate_taxonomy.2cc8ee04023e.py",
    "reviews/F0-conformance-038.json",
    "comms/outbox/worker-038.jsonl",
]


def sha(p: str) -> str:
    h = hashlib.sha256()
    with (ROOT / p).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    artifacts = {p: {"sha256": sha(p)} for p in FILES}
    rep = json.loads((ROOT / "artifacts/worker-038/f0_conformance/report.json").read_text())
    ckpt = {
        "worker": "worker-038",
        "checkpoint": 2,
        "run": "W038-F0-CONFORMANCE-01",
        "at": NOW,
        "assignment": ("self-assigned from the controller pass-03 unmet list: G-F0 has 0 independent "
                       "accepts at canonical 276009f4f63d after the rev26 role-separation adjudication; "
                       "no other agent had issued a post-rev26 full-schema F0 verdict."),
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": rep["class_ids"],
        "reviewed_revision": rep["reviewed_revision"],
        "verdicts": {
            "declared_checker": {"path": "artifacts/worker-01/validate_taxonomy.py",
                                 "exit_code": 0, "checks_passed": 253, "checks_failed": 0,
                                 "cases_checked": 37, "verdict": "pass",
                                 "note": "author-family tooling; one input, not the independent verdict"},
            "independent_checker": {"path": "artifacts/worker-038/f0_conformance/check_f0_independent.py",
                                    "exit_code": 0, "passed": 11, "failed": 0, "notes": 2},
            "verdict": "accept",
            "verdict_scope": rep["verdict_scope"],
        },
        "final_hashes": {
            "report.json": artifacts["artifacts/worker-038/f0_conformance/report.json"]["sha256"],
            "independent_checks.json": artifacts["artifacts/worker-038/f0_conformance/independent_checks.json"]["sha256"],
            "review_file": artifacts["reviews/F0-conformance-038.json"]["sha256"],
            "outbox": artifacts["comms/outbox/worker-038.jsonl"]["sha256"],
            "canonical_f0": rep["reviewed_revision"]["sha256"],
        },
        "artifacts": artifacts,
        "outbox_events": [
            "w038-f0-conformance-artifact-20260912T003150",
            "w038-f0-conformance-checker-20260912T003150",
            "w038-f0-conformance-review-20260912T003150",
            "w038-f0-conformance-status-20260912T003150",
        ],
        "rejected_events": [],
        "next_falsifier": rep["falsifier"],
        "hours_spent_estimate": 0.4,
        "numerics_lock": ("respected: no N1 work, no self-gravitating solver written or run; this run "
                          "touched only F0 taxonomy/audit artifacts"),
        "open_blockers": {
            "G-F0-SECOND-ACCEPT": ("G-F0 needs two distinct independent accepts at 276009f4f63d; this "
                                   "checkpoint supplies one advisory full-schema accept. The second "
                                   "must come from a different reviewer."),
            "G-FORM-HASH-FINDINGS": ("open on F1/F2a/F2b (duplicate revised_at keys, future-dated "
                                     "checked_at, class_contract_pointer canonicality, undefined "
                                     "AF_{I+}, quantifier/tail inconsistency) and is not addressed "
                                     "by this checkpoint."),
        },
        "status": {
            "delivered": True,
            "result": "ACCEPT (worker advisory)",
            "validation_status": "unverified",
            "no_completion_claim": ("worker cannot set done/passed/gate verdict; F0 remains "
                                    "draft_unverified; no theorem, no physics result"),
        },
    }
    out = ROOT / "runtime/state/w038_checkpoint_2.json"
    out.write_text(json.dumps(ckpt, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(out), "sha256": sha("runtime/state/w038_checkpoint_2.json"),
                      "verdict": ckpt["verdicts"]["verdict"],
                      "final_hashes": ckpt["final_hashes"]}, indent=1))


if __name__ == "__main__":
    main()
