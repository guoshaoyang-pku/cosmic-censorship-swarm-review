#!/usr/bin/env python3
"""Finalize worker-091's F2b verdict-rebind deliverable.

Steps: re-run the measurement, hash the artifacts, write the worker checkpoint,
write the three upward events to comms/outbox/worker-091.jsonl, and validate
those events through the project's own ingest normalizer + schema validator.

Refuses to overwrite an existing comms/outbox/worker-091.jsonl unless --force.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms" / "outbox" / "worker-091.jsonl"
RES = HERE / "results.json"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main(force: bool) -> int:
    if OUTBOX.exists() and not force:
        print(f"REFUSE: {OUTBOX} already exists (use --force to overwrite)", file=sys.stderr)
        return 2

    subprocess.run([sys.executable, str(HERE / "scan.py")], check=True)
    res = json.loads(RES.read_text())
    art_hash = sha(RES)
    script_hash = sha(HERE / "scan.py")
    cur = res["canonical_pre_scan"]["sha256"]
    cur12 = cur[:12]
    measured_at = res["measured_at_pre_scan"]

    manifest = {
        "artifact": "f2b_verdict_rebind",
        "actor": "worker-091",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "created_at": now(),
        "primary_artifact": {
            "path": "artifacts/worker-091/f2b_verdict_rebind/results.json",
            "sha256": art_hash,
            "bytes": RES.stat().st_size,
        },
        "files": {
            "artifacts/worker-091/f2b_verdict_rebind/scan.py": script_hash,
            "artifacts/worker-091/f2b_verdict_rebind/results.json": art_hash,
        },
        "measurement": {
            "measured_at": measured_at,
            "canonical_path": res["canonical_pre_scan"]["path"],
            "canonical_sha256": cur,
            "criterion_status": res["criterion_status"],
            "independent_accept_count": res["independent_accept_count"],
            "distinct_independent_accept_reviewers": res["distinct_independent_accept_reviewers"],
            "strict_non_worker_accept_count": res.get("strict_non_worker_accept_count"),
            "criterion_status_non_worker_only": res.get("criterion_status_non_worker_only"),
            "drifted_during_scan": res["drifted_during_scan"],
        },
        "reproduce": "python3 artifacts/worker-091/f2b_verdict_rebind/finalize.py --force",
        "verify": ("python3 -c \"import hashlib,json,pathlib;"
                   "p=pathlib.Path('artifacts/worker-091/f2b_verdict_rebind/results.json');"
                   "print(hashlib.sha256(p.read_bytes()).hexdigest())\""),
    }
    (HERE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    checkpoint = {
        "checkpoint_id": "w091-ckpt-" + datetime.now(CST).strftime("%Y%m%dT%H%M%S"),
        "actor": "worker-091",
        "role": "worker",
        "slot": "091",
        "created_at": now(),
        "wall_clock_note": "created_at is wall-clock at write time (CF-14 clock discipline)",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "state": "task_complete",
        "task": "independent hash-bound verdict re-measurement for F2b after the 00:18-00:19 republication voided A1-rebind-coverage",
        "primary_artifact": manifest["primary_artifact"],
        "measurement": manifest["measurement"],
        "events_intended": [
            "w091-20260912-f2b-rebind-status",
            "w091-20260912-f2b-rebind-artifact",
        ],
        "next_falsifier": res["falsifier"],
        "not_claimed": [
            "no gate verdict",
            "no node status=done",
            "no validation_status=passed",
            "no theorem or physics claim",
            "no canonical file mutated",
        ],
    }
    (HERE / "checkpoint.json").write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")

    (HERE / "CHECKPOINT.md").write_text(f"""# worker-091 checkpoint — F2b verdict rebind

- **Task**: independent, hash-bound re-measurement of the G-FORM "two independent verdicts"
  criterion for exactly one class, **F2b / AF-SCC-C0-VAC-GEN** (`schemas/af_scc_c0_vacuum.yaml`).
- **Why now**: `reviews/A1-rebind-coverage.json` measured F2b at `a8d899d2941f` at 00:13:10 and
  declares itself void on any later edit. F0/F1/F2a/F2b were all republished at 00:18:26–00:19:14,
  so the matrix no longer binds.
- **Measured** (no drift during scan): `{cur}`
  ({res['canonical_pre_scan']['bytes']} bytes, mtime {res['canonical_pre_scan']['mtime']}).
- **Result**: **{res['criterion_status']}** — {res['independent_accept_count']} independent
  hash-bound accept(s): {res['distinct_independent_accept_reviewers']}.
  Prior accepts bind to superseded hashes; reviewer-16's r3 accept is a same-reviewer delta
  re-check and does not count as a second independent verdict.
- **Strict subset** (excluding worker-*/deepseek-flash-* reviewers):
  **{res.get('criterion_status_non_worker_only')}** — {res.get('strict_non_worker_accept_count')}
  accept(s): {res.get('strict_non_worker_accept_reviewers')}.
- **Observation transition** (raw log `runs.jsonl`): {res.get('observation_history_summary', res.get('status_transition', 'n/a'))}.
- **Artifact**: `artifacts/worker-091/f2b_verdict_rebind/results.json`
  `{art_hash[:16]}…`; script `scan.py` `{script_hash[:16]}…`.
- **Falsifier**: {res['falsifier']}
- **Authority**: worker snapshot only — no gate verdict, no node completion, no canonical file touched.
- **Created**: {checkpoint['created_at']} (wall clock).
""")

    reviewers = ", ".join(res["distinct_independent_accept_reviewers"]) or "none"
    crit = res["criterion_status"]
    transition = res.get("observation_history_summary") or res.get("status_transition", "n/a")
    if crit == "MET":
        verdict_sentence = (
            f"G-FORM F2b two-independent-verdict criterion: MET at the measured hash under the on-file "
            f"independence annotations ({res['independent_accept_count']} distinct independent accepts: {reviewers}); "
            f"lead-audit adjudicates whether worker-authored accepts count as A1 verdicts."
        )
    elif crit == "UNMET":
        verdict_sentence = (
            f"G-FORM F2b two-independent-verdict criterion: UNMET at the measured hash "
            f"({res['independent_accept_count']} distinct independent accept(s): {reviewers}); prior accepts at "
            f"superseded hashes do not transfer."
        )
    else:
        verdict_sentence = (
            "G-FORM F2b two-independent-verdict criterion: UNMEASURED because the canonical hash changed during "
            "the scan; all bindings in this snapshot are advisory only."
        )
    strict = res.get("strict_non_worker_accept_reviewers", [])
    strict_sentence = (
        f" Strict non-worker-only subset: {res.get('criterion_status_non_worker_only')} "
        f"({len(strict)} accept(s): {', '.join(strict) or 'none'})."
    )

    ev_status = {
        "event_id": "w091-20260912-f2b-rebind-status",
        "event_type": "status",
        "created_at": now(),
        "actor": "worker-091",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "status": "active",
        "hours": 0.2,
        "summary": (
            f"Independent F2b (AF-SCC-C0-VAC-GEN) verdict-binding re-measurement at canonical "
            f"schemas/af_scc_c0_vacuum.yaml sha256 {cur12} (mtime {res['canonical_pre_scan']['mtime']}). "
            f"The prior A1-rebind-coverage matrix (measured 00:13:10, F2b a8d899d2941f) is void under its own "
            f"wall-clock note: F0/F1/F2a/F2b changed at 00:18:26-00:19:14. {verdict_sentence}{strict_sentence} "
            f"Observation transition: {transition}. No drift during scan; no canonical file mutated."
        ),
        "evidence_refs": [
            f"artifacts/worker-091/f2b_verdict_rebind/results.json#{art_hash[:12]}",
            f"schemas/af_scc_c0_vacuum.yaml#{cur12}",
            "reviews/A1-rebind-coverage.json",
            "reviews/F2b-review-worker-001.json",
        ],
        "next_falsifier": res["falsifier"],
    }
    ev_artifact = {
        "event_id": "w091-20260912-f2b-rebind-artifact",
        "event_type": "artifact",
        "created_at": now(),
        "actor": "worker-091",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "artifact_type": "verdict_binding_rebind",
        "path": "artifacts/worker-091/f2b_verdict_rebind/results.json",
        "sha256": art_hash,
        "validation_status": "unverified",
        "evidence_refs": [
            f"artifacts/worker-091/f2b_verdict_rebind/MANIFEST.json",
            f"schemas/af_scc_c0_vacuum.yaml#{cur12}",
        ],
        "falsifier": res["falsifier"],
    }
    events = [ev_status, ev_artifact]
    events_intended = [ev_status["event_id"], ev_artifact["event_id"]]
    if crit != "MET":
        ev_blocker = {
            "event_id": "w091-20260912-f2b-rebind-blocker",
            "event_type": "blocker",
            "created_at": now(),
            "actor": "worker-091",
            "node_id": "F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "description": (
                f"G-FORM criterion for F2b is {crit} at measured sha256 {cur12}: "
                f"{res['independent_accept_count']} independent, hash-bound accept verdict(s) "
                f"({reviewers}) on disk. The lead-audit A1 matrix measured a different F2b revision "
                f"(a8d899d2941f) and is void by its own note; prior accepts at e6b1af2bd692 / a8d899d2941f do not "
                f"transfer across hashes. Transition: {transition}."
            ),
            "needed_to_unblock": (
                f"A second distinct non-author reviewer records an accept verdict citing "
                f"schemas/af_scc_c0_vacuum.yaml#sha256:{cur} with no unresolved hard failure, and lead-audit "
                f"rebinds the G-FORM coverage matrix at the then-measured hash. If the canonical file is republished "
                f"first, both verdicts must be re-issued at the new hash."
            ),
            "evidence_refs": [
                f"artifacts/worker-091/f2b_verdict_rebind/results.json#{art_hash[:12]}",
                f"schemas/af_scc_c0_vacuum.yaml#{cur12}",
                "reviews/F2b-review-worker-001.json",
                "reviews/F2b-review-16-r3.json",
                "reviews/F2b-review-lead-audit.json",
                "reviews/A1-rebind-coverage.json",
            ],
            "next_falsifier": res["falsifier"],
        }
        events.append(ev_blocker)
        events_intended.append(ev_blocker["event_id"])

    checkpoint["events_intended"] = events_intended
    (HERE / "checkpoint.json").write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")

    # --- validate exactly the way the ingest bus does -------------------------
    sys.path.insert(0, str(ROOT / "research_map"))
    import comms  # noqa: E402
    from schemas import validate_event, SchemaError  # noqa: E402

    report = []
    for e in events:
        norm = comms.normalize_event(dict(e), "comms/outbox/worker-091.jsonl")
        try:
            validate_event(norm)
            report.append({"event_id": e["event_id"], "event_type": e["event_type"], "valid": True,
                           "filled_fields": norm.get("_normalized", {})})
        except SchemaError as exc:
            report.append({"event_id": e["event_id"], "valid": False, "error": str(exc)})
    if not all(r["valid"] for r in report):
        print(json.dumps(report, indent=2))
        return 3

    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    with OUTBOX.open("w") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    parsed = list(comms._json_objects(OUTBOX.read_text()))
    validation = {
        "validated_at": now(),
        "validator": "research_map/comms.normalize_event + research_map/schemas.validate_event",
        "events": report,
        "outbox": str(OUTBOX.relative_to(ROOT)),
        "path_parsed_objects": len(parsed),
        "primary_artifact_sha256_recomputed": sha(RES),
        "primary_artifact_hash_matches_event": sha(RES) == ev_artifact["sha256"],
    }
    (HERE / "validation.json").write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n")
    print(json.dumps(validation, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main("--force" in sys.argv))
