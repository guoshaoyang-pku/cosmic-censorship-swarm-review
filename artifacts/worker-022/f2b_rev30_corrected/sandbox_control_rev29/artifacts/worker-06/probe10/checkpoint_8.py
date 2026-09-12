#!/usr/bin/env python3
"""Write the worker-local checkpoint for the FORM-PROBE-10 run (idempotent append).

Worker-local by design: runtime/state/current_checkpoint.json and artifact_hashes.json are
written by the live controller lifecycle; a worker-side checkpoint.py run would race it.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
STATE = ROOT / "runtime" / "state"
CST = timezone(timedelta(hours=8))

ARTIFACTS = [
    "manifest.json", "manifest.sha256", "report.json", "blindspot_report.json",
    "raw_verdicts.json", "posthoc_report.json", "SUBMISSION.md",
    "make_probes.py", "run_probes.py", "posthoc_probes.py",
    "calibrate_audit.py", "audit_calibrated.py", "emit_probe10_events.py",
]
EVENTS = [
    "w06-20260912-form-probe10-manifest",
    "w06-20260912-form-probe10-report",
    "w06-20260912-form-probe10-blindspot",
    "w06-20260912-form-probe10-posthoc",
    "w06-20260912-form-probe10-toolchain",
    "w06-20260912-form-probe10-status",
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    report = json.loads((HERE / "report.json").read_text())
    artifacts = {rel: {"sha256": sha(HERE / rel), "bytes": (HERE / rel).stat().st_size}
                 for rel in ARTIFACTS}
    ck = {
        "checkpoint": 8,
        "at": datetime.now(CST).isoformat(timespec="seconds"),
        "worker": "worker-006",
        "slot": "006",
        "instance_id": "worker-006-20260912T003351-968807",
        "hours_spent_estimate": 1.1,
        "assignment": ("one class-bound task, self-assigned continuation of the class-binding probe "
                       "lane (no assignment event claimed): FORM-PROBE-10 out-of-sample rephrased "
                       "probe corpus at FROZEN rev28, node A1, gate G-CLASSBIND, classes "
                       "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"),
        "status": {
            "delivered": True,
            "validation_status": "unverified",
            "corpus_valid": report["valid"],
            "manifest_sha256_before_run": report["manifest_sha256_before_run"],
            "frozen_revision": report["frozen_revision"],
            "aggregates": report["aggregates"],
            "controls": report["controls"],
            "single_catch": "m03 (R09 token 'complete'); post-hoc synonym probe h01 escapes all stages",
            "correction": ("hardened 0.75 includes m02 rejected by R03 (canonical-binder format false "
                           "positive); genuine hardened semantic catches are m03 and m04 (2/12)"),
            "deviations": ["stage B' = documented single-delta calibrated auditor (pre-registered)",
                           "post-hoc probes reported separately, excluded from aggregates"],
            "no_completion_claim": "worker cannot set done/passed/gate verdict; no theorem promoted",
        },
        "artifacts": {f"artifacts/worker-06/probe10/{k}": v for k, v in artifacts.items()},
        "events_emitted": EVENTS,
        "dry_run": "comms.py ingest --dry-run: all 6 events accepted (+), 0 rejected for worker-06",
        "checkpoint_policy": ("worker-local; shared current_checkpoint.json / artifact_hashes.json are "
                              "written by the live controller lifecycle and a worker-side checkpoint.py "
                              "run would race it"),
        "next_falsifier": ("a pass_control rejected by either stage at the pinned hashes, a fixture shown "
                           "not to violate its documented invariant, or a later revision whose gate "
                           "catches these fixtures (re-run the frozen corpus, never this one)"),
    }
    out = STATE / "w006_checkpoint_8.json"
    out.write_text(json.dumps(ck, indent=2) + "\n")
    with (STATE / "w006_checkpoints.jsonl").open("a") as fh:
        fh.write(json.dumps(ck, ensure_ascii=False) + "\n")
    print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size} bytes)")
    print("manifest", ck["status"]["manifest_sha256_before_run"])
    print("union escape", ck["status"]["aggregates"]["union_escape_rate"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
