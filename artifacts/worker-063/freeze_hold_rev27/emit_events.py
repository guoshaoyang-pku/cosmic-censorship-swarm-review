#!/usr/bin/env python3
"""Emit W063-FREEZE-HOLD-REV27-01 events to comms/outbox/worker-063.jsonl (idempotent).

Validates every event with research_map/schemas.validate_event before writing, and skips any
event_id already present in the outbox.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = dt.timezone(dt.timedelta(hours=8))
OUTBOX = ROOT / "comms/outbox/worker-063.jsonl"
ART = Path(__file__).resolve().parent
REPORT = ART / "freeze_hold_audit.json"
RUNNER = ART / "run_freeze_hold_audit.py"
README = ART / "README.md"

CLASS_IDS = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH"
NODES = "F0,F1,F2a,F2b"
GATES = "G-FORM;G-F0"
STAMP = "w063-freeze-hold-rev27"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build() -> list[dict]:
    now = dt.datetime.now(CST).isoformat(timespec="seconds")
    rep_sha, run_sha, readme_sha = sha(REPORT), sha(RUNNER), sha(README)
    r = json.loads(REPORT.read_text())
    drift = r["pin_check"]["mismatches"]
    drift_txt = [f"DRIFT {m['path']}: FROZEN rev27 pin {m['pin_sha256'][:12]} != disk {m['disk_sha256'][:12]}" for m in drift]
    return [
        {
            "event_id": f"{STAMP}-artifact-report",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-063",
            "node_id": NODES,
            "gate": GATES,
            "class_id": CLASS_IDS,
            "artifact_type": "freeze_hold_audit_report",
            "path": "artifacts/worker-063/freeze_hold_rev27/freeze_hold_audit.json",
            "sha256": rep_sha,
            "validation_status": "unverified",
            "summary": (
                "Machine freeze-hold audit at 2026-09-12T00:34:29+08:00: all five canonical formulation "
                "artifacts (F0 pair, F1, F2a, F2b) were rewritten at 00:31:41-00:32:02, superseding every "
                "revision-25/26 pin; 98 review events in events.jsonl bind a superseded pin (65 revise, 22 "
                "accept, 11 inconclusive); FROZEN revision 27 already shows 5/43 pin-vs-disk DRIFT with the "
                "tree's own verify_frozen.py exiting 1; review coverage at the revision-27 canonical hashes "
                "is 0 accepts. Read-only w.r.t. every canonical/frozen path."),
            "evidence_refs": [
                f"artifacts/worker-063/freeze_hold_rev27/freeze_hold_audit.json#{rep_sha[:12]}",
                "artifacts/formulation/FROZEN.json",
                "research_map/events.jsonl",
            ],
        },
        {
            "event_id": f"{STAMP}-artifact-runner",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-063",
            "node_id": NODES,
            "gate": GATES,
            "class_id": CLASS_IDS,
            "artifact_type": "freeze_hold_audit_runner",
            "path": "artifacts/worker-063/freeze_hold_rev27/run_freeze_hold_audit.py",
            "sha256": run_sha,
            "validation_status": "unverified",
            "summary": (
                "Deterministic read-only runner: FROZEN pin-vs-disk check, cross-check with verify_frozen.py, "
                "superseded-pin verdict scan over events.jsonl, and write-patched re-runs of the three "
                "evidence-writing formulation checkers (captured bytes compared to the on-disk evidence)."),
            "evidence_refs": [f"artifacts/worker-063/freeze_hold_rev27/run_freeze_hold_audit.py#{run_sha[:12]}"],
        },
        {
            "event_id": f"{STAMP}-artifact-readme",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-063",
            "node_id": NODES,
            "gate": GATES,
            "class_id": CLASS_IDS,
            "artifact_type": "freeze_hold_audit_readme",
            "path": "artifacts/worker-063/freeze_hold_rev27/README.md",
            "sha256": readme_sha,
            "validation_status": "unverified",
            "summary": "Human-readable method, measured table, falsifier, limitations and authority note for the freeze-hold audit.",
            "evidence_refs": [f"artifacts/worker-063/freeze_hold_rev27/README.md#{readme_sha[:12]}"],
        },
        {
            "event_id": f"{STAMP}-review-frozen-rev27",
            "event_type": "review",
            "created_at": now,
            "actor": "worker-063",
            "reviewer": "worker-063",
            "target_id": f"artifacts/formulation/FROZEN.json#rev{r['frozen_manifest']['revision']}",
            "target_sha256": r["frozen_manifest"]["sha256"],
            "gate": GATES,
            "class_id": CLASS_IDS,
            "verdict": "revise",
            "score": 2.0,
            "hard_failures": drift_txt + [
                "FROZEN rev27 is not a valid freeze boundary: 5 pinned evidence/variant files were regenerated "
                "at 00:33:16-00:34:42, after frozen_at 00:32:59; verify_frozen.py exits 1."],
            "findings": [
                "3 of the 5 drifted files are deterministic checker outputs; the pinned bytes are stale relative to a fresh run of the pinned tools.",
                "The five canonical schemas/taxonomy are NOT among the 5 drifted files at T0, so the freeze pins for F0/F1/F2a/F2b themselves held during the 00:34:29 measurement window (drift_during_run = []).",
                "A manifest that is regenerated after its own frozen_at cannot serve as the freeze boundary for a verdict round.",
            ],
            "evidence_refs": [
                f"artifacts/formulation/FROZEN.json#{r['frozen_manifest']['sha256'][:12]}",
                f"artifacts/worker-063/freeze_hold_rev27/freeze_hold_audit.json#{rep_sha[:12]}",
            ],
            "authority_note": "Review of the freeze manifest only; not a schema verdict for any gate target and not a promotion.",
            "reviewer_independence": "worker-063 did not author FROZEN.json, any formulation artifact, or any checker in this tree.",
        },
        {
            "event_id": f"{STAMP}-claim",
            "event_type": "claim",
            "created_at": now,
            "actor": "worker-063",
            "node_id": NODES,
            "gate": GATES,
            "class_id": CLASS_IDS,
            "conclusion_type": "numerical_evidence",
            "statement": (
                "Measured at 2026-09-12T00:34:29+08:00: (a) the five canonical formulation artifacts changed "
                "from the revision-25/26 pins 276009f4f63d/c8e979a1eb48/9a8bd4c96800/b6123750b37d/1bb78ce9b357 "
                "to 0abb9ed8a961/d7419b4e8963/cce9c60146d6/5476a3f2c6bc/55d0a1ea9bda with mtimes "
                "00:31:41-00:32:02, so 98 review events (65 revise, 22 accept, 11 inconclusive) that cite the "
                "superseded pins are void for gate coverage; (b) FROZEN revision 27 (sha256 5fa3b3bf95f2) itself "
                "fails its own pin check with 5/43 DRIFT (KEY_MANIFEST.json, evidence/gate_test_report.json, "
                "evidence/taxonomy_consistency.json, variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json, "
                "variants/AF-WCC-VAC-GEN.variant-SET.delta.json), regenerated after frozen_at; (c) at the "
                "revision-27 canonical hashes only 6 review events exist, none an accept; (d) the new bytes are "
                "machine-green on the read-only checks: class schemas pass, taxonomy consistency CONSISTENT with "
                "0 contract-text divergences and byte-reproducible evidence, variant registry/deltas VALID; "
                "(e) the F0 canonical/authoring pair remains byte-divergent."),
            "assumptions": [
                "FROZEN.json's `files` map is the intended freeze boundary per the protocol's artifact+hash rule.",
                "Review events citing a 12-hex pin prefix are bound to that revision; a rewrite voids them.",
                "The write-patched checker runs reproduce the checkers' frozen logic; the patch only suppresses the evidence write.",
            ],
            "falsifier": (
                "Re-measure the five focus paths and show a superseded pin still matches disk at its recorded "
                "mtime; or show fewer than one review event in research_map/events.jsonl citing a superseded pin; "
                "or run artifacts/formulation/tools/verify_frozen.py and show zero drift against FROZEN revision "
                "27; or edit any focus path and show the T0 hashes still describe disk."),
            "evidence_refs": [
                f"artifacts/worker-063/freeze_hold_rev27/freeze_hold_audit.json#{rep_sha[:12]}",
                "artifacts/formulation/FROZEN.json",
                "research_map/events.jsonl",
                "reviews/A1-rebind-coverage.json",
                "research_map/ASTRA_HANDOFF.md",
            ],
            "artifact_refs": [f"artifacts/worker-063/freeze_hold_rev27/freeze_hold_audit.json#{rep_sha[:12]}"],
            "expected_information_gain": (
                "Tells the controller exactly which verdicts must be re-dispatched and that FROZEN rev27 cannot "
                "be the freeze boundary until regeneration stops and the manifest is re-emitted last."),
            "hours": 0.15,
        },
        {
            "event_id": f"{STAMP}-blocker",
            "event_type": "blocker",
            "created_at": now,
            "actor": "worker-063",
            "node_id": NODES,
            "gate": GATES,
            "class_id": CLASS_IDS,
            "description": (
                "Freeze did not hold across the revision-27 boundary: canonical F0/F1/F2a/F2b were rewritten at "
                "00:31:41-00:32:02, FROZEN rev27 (00:32:59) then drifted on 5/43 pins by 00:34:42, and 0 accepts "
                "bind the revision-27 hashes. G-FORM/G-F0 coverage measured at 00:24:40 is void at the bytes "
                "now on disk."),
            "needed_to_unblock": (
                "Stop all formulation regeneration/monitor loops; re-emit FROZEN.json last and only after the "
                "tree is quiescent; then dispatch two blind reviewers per target against the resulting single "
                "hash and accept a verdict only if the hash is unchanged when the second verdict lands."),
            "evidence_refs": [
                f"artifacts/worker-063/freeze_hold_rev27/freeze_hold_audit.json#{rep_sha[:12]}",
                "artifacts/formulation/FROZEN.json",
            ],
        },
        {
            "event_id": f"{STAMP}-status",
            "event_type": "status",
            "created_at": now,
            "actor": "worker-063",
            "node_id": NODES,
            "gate": GATES,
            "class_id": CLASS_IDS,
            "status": "active",
            "hours": 0.15,
            "summary": (
                "W063-FREEZE-HOLD-REV27-01 delivered unverified: read-only freeze-hold audit + runner + README, "
                "events emitted, hashes recorded. Result: the revision-25/26 verdict set is void (98 events, 22 "
                "accepts), FROZEN rev27 is stale on 5/43 pins, and 0 accepts bind the revision-27 hashes; the "
                "new bytes pass the read-only content checks. Node promotion and gate verdicts remain with the "
                "formulation lead/controller."),
            "evidence_refs": [
                f"artifacts/worker-063/freeze_hold_rev27/freeze_hold_audit.json#{rep_sha[:12]}",
                "runtime/state/artifact_hashes.json",
            ],
            "next_falsifier": (
                "An independent worker re-measures the five focus paths after the next freeze; if the hashes are "
                "unchanged from this report's T0 and a second accept lands at that same hash, this report's "
                "voiding claim is superseded."),
        },
    ]


def main() -> int:
    events = build()
    for e in events:
        validate_event(e)
    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                try:
                    existing.add(json.loads(line).get("event_id"))
                except json.JSONDecodeError:
                    pass
    new = [e for e in events if e["event_id"] not in existing]
    with OUTBOX.open("a") as f:
        for e in new:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(json.dumps({"validated": len(events), "appended": len(new),
                      "skipped_existing": len(events) - len(new),
                      "outbox": str(OUTBOX.relative_to(ROOT))}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
