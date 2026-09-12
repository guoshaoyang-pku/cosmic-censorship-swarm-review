#!/usr/bin/env python3
"""Emit W082-F1-MACHINE-DEFECT-VERIFY-01 events, publish the review copy, checkpoint.

Idempotent by event_id: re-running appends nothing already present and rewrites
the checkpoint with identical content except its `at`/`checked_at` clock fields.
Every event is validated with research_map/schemas.validate_event before writing,
so the controller's `comms.py ingest` cannot reject it on schema.

Worker-082 cannot set gate verdicts, done status, or validation_status=passed.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTBOX = ROOT / "comms" / "outbox" / "worker-082.jsonl"
REVIEWS = ROOT / "reviews"
STATE = ROOT / "runtime" / "state"
ART = ROOT / "artifacts" / "worker-082" / "f1_machine_defect"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
STAMP = "w082-20260912T0029"
INSTANCE = "worker-082-20260912T002424-968807"
TARGET_SHA = "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503"
CLASS_ID = "AF-WCC-VAC-GEN"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(path: Path, n: int = 16) -> str:
    return f"{path.relative_to(ROOT)}#sha256:{sha256(path)[:n]}"


# --- publish the review record copy (byte-identical to the artifact copy) -----
ver = ART / "VERIFY-F1-082.json"
review_copy = REVIEWS / "F1-machine-verify-worker-082.json"
if not review_copy.exists() or sha256(review_copy) != sha256(ver):
    shutil.copyfile(ver, review_copy)

FILES = {
    "run_checks.py": ART / "run_checks.py",
    "evidence.json": ART / "evidence.json",
    "frozen_copy": ART / "frozen_f1_9a8bd4c96800.yaml",
    "verification_record": ver,
    "fix_proposal": ART / "FIX-PROPOSAL-082.md",
    "readme": ART / "README.md",
    "review_copy": review_copy,
}
H = {k: sha256(v) for k, v in FILES.items()}

EVIDENCE_REFS = [
    ref(FILES["evidence.json"]),
    ref(FILES["run_checks.py"]),
    ref(FILES["frozen_copy"]),
    ref(FILES["verification_record"]),
    f"research_map/formulation_taxonomy.yaml#sha256:276009f4f63dbf83",
    "artifacts/formulation/formulation_taxonomy.yaml#sha256:c8e979a1eb48969b",
]

FALSIFIER = (
    "Re-measure schemas/af_wcc_vacuum.yaml. If it is republished at a new sha256 whose top-level key set has no "
    "duplicates, whose effective revised_at and f0_binding.checked_at are not ahead of the wall clock, whose "
    "class_contract_pointer resolves inside the canonical tree to the declared F0 hash, and whose "
    "review_status.independent_reviewers is non-empty, then this verification is void and requires a re-run at the "
    f"new hash. Re-running run_checks.py against the frozen copy (sha256 {TARGET_SHA}) must reproduce duplicate "
    "revised_at at lines [8,10,12,14,16,20,23] and revised_at_unused at [26,28] with PyYAML-effective revised_at "
    "2026-09-12T00:30:00+08:00; any different artifact-derived result falsifies the evidence file."
)

HEAD = {"actor": "worker-082", "created_at": NOW, "node_id": "F1",
        "class_id": CLASS_ID, "gate": "G-FORM", "task_id": "W082-F1-MACHINE-DEFECT-VERIFY-01"}

events = [
    {**HEAD, "event_id": f"{STAMP}-task-claim", "event_type": "status", "status": "active", "hours": 0.05,
     "summary": ("Self-selected one class-bound task after reading HANDOFF.md, ASTRA_HANDOFF.md, "
                 "controller_gate_audit (00:24:40) and PROTOCOL.md: F1 has multiple hash-bound revise verdicts and "
                 "zero accepts at 9a8bd4c96800, all citing a machine-verifiable duplicate-key/binding defect class "
                 "with no reproducible record. No inbox card existed for worker-082."),
     "evidence_refs": [f"schemas/af_wcc_vacuum.yaml#sha256:{TARGET_SHA[:16]}"],
     "next_falsifier": FALSIFIER},
]

for name, path in FILES.items():
    events.append({
        **HEAD, "event_id": f"{STAMP}-artifact-{name}", "event_type": "artifact",
        "artifact_type": {"run_checks.py": "verification_script", "evidence.json": "evidence_json",
                          "frozen_copy": "frozen_reviewed_artifact", "verification_record": "verification_record",
                          "fix_proposal": "fix_proposal", "readme": "readme",
                          "review_copy": "review_record"}[name],
        "path": str(path.relative_to(ROOT)), "sha256": H[name], "validation_status": "unverified",
        "evidence_refs": EVIDENCE_REFS[:1], "falsifier": FALSIFIER,
    })

events.append({
    **HEAD, "event_id": f"{STAMP}-verify-F1", "event_type": "review",
    "reviewer": "worker-082", "target_id": "F1", "verdict": "revise", "score": 2.5,
    "artifact": "schemas/af_wcc_vacuum.yaml", "artifact_sha256": TARGET_SHA, "reviewed_sha256": TARGET_SHA,
    "counts_as_full_schema_verdict": False, "verification_type": "machine_data_integrity_and_binding",
    "hard_failures": ["W082M-02 duplicate top-level revised_at x7", "W082M-03 PyYAML last-wins discards 6 stamps",
                      "W082M-04 revised_at_unused duplicated and dead", "W082M-05 future-dated revised_at/checked_at",
                      "W082M-06 contract pointer outside canonical tree",
                      "W082M-07 review_status stale vs 9 hash-bound verdicts"],
    "findings": [
        "Machine data-integrity and binding verification only; NOT a full-schema verdict and must not be counted as a G-FORM accept.",
        "Deterministic checks W082M-01..06, 08, 09 reproduce across runs; W082M-07 is a timestamped live-corpus snapshot (9 hash-bound reviews, 0 accepts, at 00:29).",
        "D0 disjunction recorded as syntax only; the family-of-two-statements reading is inherited from worker-088 HF-088-1 and lead-audit r2, not adjudicated here.",
        "Same duplicate-revised_at defect observed in F2a (x8) and F2b (x8); F0 taxonomy clean. No verdict attached to F2a/F2b by this record.",
    ],
    "evidence_refs": EVIDENCE_REFS,
    "stop_rule": ("Owner applies FIX-PROPOSAL-082.md, republishes byte-identically, re-runs run_checks.py at the new "
                  "hash until W082M-02..07 are refuted; only then is a fresh full-schema F1 review meaningful."),
    "scope_note": ("Worker-082 cannot set done/passed or any gate verdict. Advisory fix proposal; no canonical artifact "
                   "was modified (CF-12 single-owner rule)."),
})

events.append({
    **HEAD, "event_id": f"{STAMP}-blocker-F1", "event_type": "blocker",
    "description": ("F1 schema at 9a8bd4c96800 carries six confirmed machine blocking defects: duplicate top-level "
                    "revised_at x7 (silent loss of 6 revision stamps under any YAML load), dead duplicated "
                    "revised_at_unused x2, future-dated revised_at and f0_binding.checked_at (00:30:00 vs 00:28 wall "
                    "clock), contract pointer into the authoring tree (c8e979a1) instead of canonical F0 (276009f4), "
                    "and review_status.independent_reviewers empty against 9 hash-bound verdicts (0 accepts)."),
    "needed_to_unblock": ("lead-formulation applies artifacts/worker-082/f1_machine_defect/FIX-PROPOSAL-082.md, "
                          "republishes byte-identically and records the new hash; then re-run run_checks.py (exit 0) "
                          "and request a fresh full-schema review."),
    "evidence_refs": EVIDENCE_REFS,
})

events.append({
    **HEAD, "event_id": f"{STAMP}-complete", "event_type": "status", "status": "active", "hours": 0.6,
    "summary": ("W082-F1-MACHINE-DEFECT-VERIFY-01 delivered: independent reproducible machine-defect verification of "
                "F1 at frozen sha256 9a8bd4c96800; verdict revise (data integrity), 6 blocking findings, 3 positive/"
                "scoped checks; advisory owner-routed fix proposal; no gate verdict claimed."),
    "evidence_refs": EVIDENCE_REFS,
    "next_falsifier": FALSIFIER,
})

written, skipped = 0, 0
existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                existing.add(json.loads(line)["event_id"])
            except Exception:
                pass
for ev in events:
    validate_event(ev)
with open(OUTBOX, "a", encoding="utf-8") as f:
    for ev in events:
        if ev["event_id"] in existing:
            skipped += 1
            continue
        f.write(json.dumps(ev, sort_keys=True) + "\n")
        written += 1

checkpoint = {
    "checkpoint": 2,
    "at": NOW,
    "worker": "worker-082",
    "instance": INSTANCE,
    "task_id": "W082-F1-MACHINE-DEFECT-VERIFY-01",
    "hours_spent_estimate": 0.6,
    "assignment": ("Self-selected class-bound task after reading HANDOFF.md, ASTRA_HANDOFF.md, "
                   "research_map.json (controller_gate_audit 00:24:40) and comms/PROTOCOL.md: F1 at frozen "
                   "9a8bd4c96800 has hash-bound revise verdicts and zero accepts, with the blocking defect class "
                   "machine-verifiable but lacking a reproducible record. No inbox card existed for worker-082."),
    "class_binding": {"node_id": "F1", "class_id": CLASS_ID, "gate": "G-FORM",
                      "bound_artifact": "schemas/af_wcc_vacuum.yaml"},
    "target": {"path": "schemas/af_wcc_vacuum.yaml", "sha256_measured": TARGET_SHA,
               "canonical_remeasured_at_finalize": TARGET_SHA, "hash_stable_during_task": True,
               "frozen_reviewed_copy": "artifacts/worker-082/f1_machine_defect/frozen_f1_9a8bd4c96800.yaml"},
    "status": {"verdict": "revise", "score": 2.5, "verification_type": "machine_data_integrity_and_binding",
               "counts_as_full_schema_verdict": False, "blocking_confirmed": 6, "refuted": 0,
               "hash_bound_f1_verdicts_at_0029": {"total": 9, "revise": 8, "inconclusive": 1, "accept": 0},
               "cross_artifact_observation": {"F2a b6123750b37d": "duplicate revised_at x8",
                                              "F2b 1bb78ce9b357": "duplicate revised_at x8",
                                              "F0 276009f4f63d": "clean"},
               "no_completion_claim": "worker-082 cannot set done/passed, validation_status=passed, or any gate verdict"},
    "artifacts": {str(p.relative_to(ROOT)): {"sha256": H[k]} for k, p in FILES.items()},
    "findings_summary": [
        "W082M-02/03 blocking: revised_at x7 (lines 8,10,12,14,16,20,23); PyYAML last-wins keeps 00:30:00 and silently discards 6 stamps, so revision=11 is unverifiable.",
        "W082M-04 blocking: revised_at_unused x2 (lines 26,28), dead key.",
        "W082M-05 blocking: effective revised_at and f0_binding.checked_at are 119.4 s ahead of the 00:28:00 wall clock.",
        "W082M-06 blocking: class_contract_pointer/class_contract_supplement resolve to authoring artifacts/formulation/formulation_taxonomy.yaml (c8e979a1eb48) vs declared canonical research_map/formulation_taxonomy.yaml (276009f4f63d).",
        "W082M-07 blocking (live snapshot): review_status.independent_reviewers=[] while 9 hash-bound verdicts exist at 9a8bd4c96800 (0 accepts).",
        "W082M-01/09 positive: frozen bytes bind the canonical path; all 13 required top-level slots present.",
        "W082M-08 syntax only: D0 definition and regularity.data_regularity are disjunctive under one (s,delta) binder; the family-of-two-statements reading is NOT adjudicated here.",
    ],
    "falsifier": FALSIFIER,
    "next_step_for_controller": ("Ingest comms/outbox/worker-082.jsonl and route artifacts/worker-082/f1_machine_defect/"
                                 "FIX-PROPOSAL-082.md to lead-formulation (single canonical owner). This record is one "
                                 "revise input, not an accept; G-FORM still needs the F1 revision then two independent "
                                 "full-schema accepts at the new hash."),
}
(STATE / "w082_checkpoint_2.json").write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n", encoding="utf-8")

print(f"events written={written} skipped={skipped} validated={len(events)}")
print(f"review copy: {review_copy.relative_to(ROOT)} sha256={H['review_copy']}")
print(f"checkpoint: runtime/state/w082_checkpoint_2.json")
