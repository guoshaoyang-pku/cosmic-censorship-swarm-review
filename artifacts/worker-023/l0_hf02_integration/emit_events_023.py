#!/usr/bin/env python3
"""Idempotent emitter for the W023-L0-HF02-INTEG-01 completion events.

Appends the artifact / claim / review / blocker / status events to
`comms/outbox/worker-023.jsonl`, skipping any event_id already present.
No canonical file is edited. Run after `run_integration_023.py` and
`verify_report_023.py` have produced their artifacts.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
ART = REPO / "artifacts/worker-023/l0_hf02_integration"
OUTBOX = REPO / "comms/outbox/worker-023.jsonl"
TASK = "W023-L0-HF02-INTEG-01"
STAMP = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
TAG = datetime.now().strftime("%Y%m%dT%H%M%S")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(rel: str, n: int = 12) -> str:
    return f"{rel}#{sha(REPO / rel)[:n]}"


REPORT = "artifacts/worker-023/l0_hf02_integration/report.json"
VERIFICATION = "artifacts/worker-023/l0_hf02_integration/verification.json"
MANIFEST = "artifacts/worker-023/l0_hf02_integration/manifest.json"
WIRING = "artifacts/worker-023/l0_hf02_integration/runner_wiring.diff"
DRIVER = "artifacts/worker-023/l0_hf02_integration/run_integration_023.py"
VERIFIER = "artifacts/worker-023/l0_hf02_integration/verify_report_023.py"
README = "artifacts/worker-023/l0_hf02_integration/README.md"

PATCH = "artifacts/worker-093/l0_rev3_review/proposed_hf02_disjunction_patch.diff"
PATCHED_LIB = "artifacts/worker-093/l0_rev3_review/patched_audit_lib.py"
LEDGER = "ledger/theorems.jsonl"

CLASS_IDS = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN"]
EV = {
    "node_id": "L0",
    "gate": "G-LIT",
    "class_id": "AF-SCC-C2-VAC-GEN",
    "class_ids": CLASS_IDS,
    "task_id": TASK,
}


def build() -> list[dict]:
    report = json.loads((ART / "report.json").read_text())
    claim = {
        **EV, "actor": "worker-023", "created_at": STAMP,
        "event_id": f"w23-integ-{TAG}-claim",
        "event_type": "claim",
        "conclusion_type": "formal_model",
        "statement": (
            "At the pinned bytes (ledger a1674f094979, audit_lib ae573db84631, audit_run 3b27dd3fef7f), "
            "the worker-093 HF-02 ledger-disjunction branch integrates end-to-end: the diff applies "
            "byte-faithfully and one wiring line in audit_run.py is sufficient. On the frozen 62-row ledger "
            "the canonical runner flags 0 of the 8 dual-class rows; the wired runner flags exactly "
            "{D-004,D-005,T-303,T-305,T-402,T-515,T-526,T-528} as critical HF-02 and adds no other violation "
            "(8 added, 0 removed, identical under trimmed and partial full-map variants, digest-identical on "
            "rerun, 15/15 controls). The 093 diff alone is inert because it ships no call site; landing it "
            "also flips the derived G-AUDIT verdict pending to fail, so the code repair must land together "
            "with the ledger repair or a rubric amendment."),
        "assumptions": [
            "The frozen sandbox mirrors only the files the ledger scan reads; full-map absolute verdicts are "
            "not interpretable and only within-variant deltas are used.",
            "The 8-row membership is taken from the bytes at ledger a1674f094979, not from any prior review.",
            "Worker-level evidence only: no node status, no gate verdict, no validation_status=passed.",
        ],
        "falsifier": report["falsifier"],
        "evidence_refs": [ref(REPORT), ref(VERIFICATION), ref(LEDGER), ref(PATCH), ref(PATCHED_LIB)],
        "artifact_refs": [ref(REPORT), ref(MANIFEST), ref(WIRING), ref(DRIVER), ref(VERIFIER)],
    }
    artifact_report = {
        **EV, "actor": "worker-023", "created_at": STAMP,
        "event_id": f"w23-integ-{TAG}-artifact-report",
        "event_type": "artifact",
        "artifact_type": "integration_report",
        "path": REPORT, "sha256": sha(REPO / REPORT), "validation_status": "unverified",
        "summary": ("End-to-end integration test of the HF-02 ledger-disjunction branch in the canonical "
                    "audit runner: 14/14 checks, 15/15 controls, delta 8+/0- in both map variants."),
        "falsifier": report["falsifier"],
        "evidence_refs": [ref(MANIFEST), ref(VERIFICATION), ref(WIRING)],
    }
    artifact_verification = {
        **EV, "actor": "worker-023", "created_at": STAMP,
        "event_id": f"w23-integ-{TAG}-artifact-verification",
        "event_type": "artifact",
        "artifact_type": "independent_verification",
        "path": VERIFICATION, "sha256": sha(REPO / VERIFICATION), "validation_status": "unverified",
        "summary": ("Independent re-derivation of every integration assertion from raw evidence plus "
                    "re-execution of the frozen scenarios: 28/28 checks pass."),
        "falsifier": "Any raw audit report changing its violation digest, or a re-executed frozen scenario "
                     "differing from the recorded digest, falsifies the verification.",
        "evidence_refs": [ref(REPORT), ref(VERIFIER)],
    }
    review = {
        **EV, "actor": "worker-023", "created_at": STAMP,
        "event_id": f"w23-integ-{TAG}-review",
        "event_type": "review",
        "target_id": ref(PATCH),
        "reviewer": "worker-023",
        "verdict": "accept",
        "score": 4.0,
        "hard_failures": [],
        "findings": [
            "F1 integration verified: byte-faithful apply, one wiring line sufficient, exactly the 8 dual-class "
            "rows flagged, nothing else added or removed, deterministic on rerun.",
            "F2 major instrument: the diff ships no call site, so P-CODE alone is inert; a landing package must "
            "include the one-line wiring recorded in runner_wiring.diff.",
            "F3 minor instrument: audit_run.py:142-143 G-FORM branch is a constant-False expression and can "
            "never leave pending.",
            "F4 consequence: landing P-CODE at ledger a1674f094979 flips the derived G-AUDIT verdict to fail; "
            "the code repair and the ledger repair or rubric amendment must land together.",
        ],
        "evidence_refs": [ref(REPORT), ref(VERIFICATION), ref(WIRING), ref(PATCH)],
    }
    blocker = {
        **EV, "actor": "worker-023", "created_at": STAMP,
        "event_id": f"w23-integ-{TAG}-blocker",
        "event_type": "blocker",
        "description": ("P-CODE landing is not ready as a one-file change: (a) the diff has no call site, so "
                        "without the runner wiring it is inert; (b) at the current ledger, landing it flips "
                        "the derived G-AUDIT verdict to fail; (c) live canonical bytes are still "
                        "audit_lib ae573db84 / audit_run 3b27dd3fe, so the measured integration is a sandbox "
                        "result, not a canonical state."),
        "needed_to_unblock": ("Lead/controller decision and ownership: land the 093 diff plus the one-line "
                              "wiring as one change, paired with the ledger repair (move the 8 rows' "
                              "multi-class coverage to informs_classes) or a rubric amendment exempting the "
                              "record surface; re-run the canonical audit after landing and expect no HF-02 "
                              "ledger-disjunction entries."),
        "evidence_refs": [ref(REPORT), ref(WIRING), ref(VERIFICATION), ref(LEDGER)],
    }
    status = {
        **EV, "actor": "worker-023", "created_at": STAMP,
        "event_id": f"w23-integ-{TAG}-status-exit",
        "event_type": "status",
        "status": "active",
        "hours": 0.5,
        "summary": ("One bounded class-bound task complete (W023-L0-HF02-INTEG-01), checkpoint written, "
                    "exiting. Task self-selected from the open HF-02 blocker at L0; no inbox card existed. "
                    "Integration-verified on frozen inputs; worker level only: no node status, no gate "
                    "verdict, no validation_status=passed."),
        "evidence_refs": [ref(REPORT), ref(VERIFICATION), ref(MANIFEST)],
        "next_falsifier": report["falsifier"],
    }
    return [artifact_report, artifact_verification, claim, review, blocker, status]


def main() -> int:
    existing = set()
    if OUTBOX.is_file():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    existing.add(json.loads(line).get("event_id"))
                except ValueError:
                    pass
    events = build()
    written = 0
    with open(OUTBOX, "a") as f:
        for e in events:
            if e["event_id"] in existing:
                print(f"skip existing {e['event_id']}")
                continue
            f.write(json.dumps(e, sort_keys=True) + "\n")
            written += 1
            print(f"wrote {e['event_type']:8s} {e['event_id']}")
    print(f"{written} new event(s) -> {OUTBOX.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
