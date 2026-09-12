#!/usr/bin/env python3
"""Emit worker-007 claim-42 verification events to comms/outbox/worker-007.jsonl.

Idempotent-by-timestamp: each run writes a new timestamped event set; the file is
append-only.  Every event carries event_id/event_type/created_at/actor; claim events
carry class_id/statement/conclusion_type/assumptions/falsifier/evidence_refs; artifact
events carry node_id/artifact_type/path/sha256/validation_status; the review event
carries target_id/reviewer/verdict/score/hard_failures/findings.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
OUT = ROOT / "comms/outbox/worker-007.jsonl"

TASK_ID = "W007-CLAIM42-INDEP-VERIFY-01"
CLAIM_ID = "w072-20260912T001917-claim-conclusion-poor"
CLASS_ID = "AF-WCC-SCALAR-SPH"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ev(prefix: str, i: int) -> str:
    return f"w007-claim42-{prefix}-{i:02d}"


def main() -> int:
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    created = datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S+08:00")

    report = HERE / "report.json"
    checker = HERE / "verify_claim42.py"
    readme = HERE / "README.md"
    r_sha, c_sha, m_sha = sha(report), sha(checker), sha(readme)
    r_ref = f"artifacts/worker-007/claim42_verify/report.json#{r_sha[:12]}"
    c_ref = f"artifacts/worker-007/claim42_verify/verify_claim42.py#{c_sha[:12]}"
    m_ref = f"artifacts/worker-007/claim42_verify/README.md#{m_sha[:12]}"
    snap_f0 = f"artifacts/worker-007/claim42_verify/snapshot/formulation_taxonomy.276009f4f63d.yaml#276009f4f63d"
    snap_led = f"artifacts/worker-007/claim42_verify/snapshot/theorems.ce42d205e761.jsonl#ce42d205e761"

    rep = json.loads(report.read_text())
    primary = rep["primary_scan_at_pin"]

    events = [
        {
            "event_id": ev("artifact-report", 1),
            "event_type": "artifact",
            "created_at": created,
            "actor": "worker-007",
            "node_id": "L1",
            "class_id": CLASS_ID,
            "gate": "G-LIT",
            "task_id": TASK_ID,
            "artifact_type": "claim_verification_report",
            "path": "artifacts/worker-007/claim42_verify/report.json",
            "sha256": r_sha,
            "validation_status": "unverified",
            "summary": (
                "Independent verification of open map claim w072-20260912T001917-claim-conclusion-poor "
                f"at pinned hashes: verdict {rep['verdict']}; bound={primary['n_bound']}, "
                f"WCC-conclusion={primary['n_bound_wcc_conclusion']}, "
                f"H4-named={primary['n_bound_genericity_named_strict']}, "
                f"falsifier-witnesses={primary['n_qualifying_falsifier_witnesses']}, "
                "controls all pass."
            ),
            "evidence_refs": [snap_f0, snap_led, c_ref],
        },
        {
            "event_id": ev("artifact-checker", 2),
            "event_type": "artifact",
            "created_at": created,
            "actor": "worker-007",
            "node_id": "L1",
            "class_id": CLASS_ID,
            "gate": "G-LIT",
            "task_id": TASK_ID,
            "artifact_type": "independent_checker",
            "path": "artifacts/worker-007/claim42_verify/verify_claim42.py",
            "sha256": c_sha,
            "validation_status": "unverified",
            "summary": "Self-contained checker (stdlib + PyYAML; no worker-072 code); reproduces the claim's per-entry rule and runs the falsifier sweep with controls.",
            "evidence_refs": [r_ref],
        },
        {
            "event_id": ev("artifact-readme", 3),
            "event_type": "artifact",
            "created_at": created,
            "actor": "worker-007",
            "node_id": "L1",
            "class_id": CLASS_ID,
            "gate": "G-LIT",
            "task_id": TASK_ID,
            "artifact_type": "readme",
            "path": "artifacts/worker-007/claim42_verify/README.md",
            "sha256": m_sha,
            "validation_status": "unverified",
            "summary": "Method, counts, two rule-quality findings (H1 vacuity via class-id token; H2 substring hazard on 'non-spherical'), controls, falsifier, non-claims.",
            "evidence_refs": [r_ref, c_ref],
        },
        {
            "event_id": ev("claim", 4),
            "event_type": "claim",
            "created_at": created,
            "actor": "worker-007",
            "node_id": "L1",
            "class_id": CLASS_ID,
            "class_ids": [CLASS_ID],
            "gate": "G-LIT",
            "task_id": TASK_ID,
            "conclusion_type": "formal_model",
            "statement": (
                "At the pinned bytes research_map/formulation_taxonomy.yaml#276009f4f63d and "
                "ledger/theorems.jsonl#ce42d205e761, the claim w072-20260912T001917-claim-conclusion-poor "
                "is CONFIRMED by an independent token-mechanical census: 10 ledger entries are bound to "
                "AF-WCC-SCALAR-SPH, 0 carry conclusion_type=weak_cosmic_censorship, 0 name any positive "
                "genericity notion in their genericity/statement fields, and the full 62-entry ledger "
                "contains 0 falsifier witnesses and 0 unbound class-conforming WCC omission candidates. "
                "The claim's sub-assertion '5/10 mechanically in-class (H1-H3)' is reproduced exactly "
                "under worker-072's reconstructed rule, but that rule is rule-dependent and partly "
                "vacuous: its H1 column is satisfied by the class-id token SCALAR for all 10 bound "
                "entries (strict H1: 0/10), and its H2 column passes the explicitly non-spherical "
                "T-105/T-106 via substring matching. This is a statement about the artifacts, not "
                "about cosmic censorship."
            ),
            "assumptions": [
                "the reviewed bytes are the snapshot copies under artifacts/worker-007/claim42_verify/snapshot/, each re-hashed against its pin",
                "classification is token-mechanical over entry metadata, not a semantic reading of the papers",
                "the population 'bound to the class' is class_ids containing the exact token AF-WCC-SCALAR-SPH",
                "the claim's H4 clause is tested as a positive genericity notion plus topology in the entry's own genericity/statement fields, excluding negative guards; the witness sweep is insensitive to that choice because 0 bound entries contain any positive genericity token",
                "worker-072's own rule is reconstructed from its published per-entry table and reproduces that table exactly",
            ],
            "falsifier": (
                "Re-run verify_claim42.py against a later pinned revision: this verification is falsified "
                "if any ledger entry passes H1-H3, names a positive genericity notion with a topology in "
                "its genericity/statement fields, and carries conclusion_type=weak_cosmic_censorship; or "
                "if an unbound class-conforming WCC entry exists. A revision change alone supersedes - "
                "does not falsify - this verification."
            ),
            "artifact_refs": [r_ref, c_ref],
            "evidence_refs": [r_ref, c_ref, m_ref, snap_f0, snap_led],
        },
        {
            "event_id": ev("review", 5),
            "event_type": "review",
            "created_at": created,
            "actor": "worker-007",
            "node_id": "L1",
            "class_id": CLASS_ID,
            "gate": "G-LIT",
            "task_id": TASK_ID,
            "target_id": CLAIM_ID,
            "reviewer": "worker-007",
            "verdict": "accept",
            "score": 4.0,
            "hard_failures": [],
            "findings": [
                "CONFIRMED: 0/10 bound entries carry conclusion_type=weak_cosmic_censorship; 0/10 contain any positive genericity token; 0 falsifier witnesses across the 62-entry ledger; 0 omission candidates.",
                "NON-BLOCKING (rule quality): the claim's H1 column is vacuous for bound entries - the class-id token SCALAR satisfies the /scalar/ test for all 10; strict H1 (3+1 + Einstein/Lambda=0 + massless scalar content) is 0/10.",
                "NON-BLOCKING (rule quality): the H2 column passes T-105 and T-106 only through the substring inside 'non-spherical'; T-106's ledger tag is NON-SPHERICAL. A negation-guarded H2 excludes both.",
                "INDEPENDENT REPRODUCTION: the reconstructed worker-072 rule reproduces its published per-entry H1/H2/H3 table exactly (0 mismatches), giving 5/10 at the pinned hash.",
                "SCOPE: token-mechanical artifact verification only; no physics claim; worker verdict only, no node status or gate verdict.",
            ],
            "evidence_refs": [r_ref, m_ref, snap_f0, snap_led],
        },
        {
            "event_id": ev("status", 6),
            "event_type": "status",
            "created_at": created,
            "actor": "worker-007",
            "node_id": "L1",
            "class_id": CLASS_ID,
            "gate": "G-LIT",
            "task_id": TASK_ID,
            "status": "active",
            "hours": 0.6,
            "summary": (
                "W007-CLAIM42-INDEP-VERIFY-01 complete: one bounded class-bound task taken (no inbox card "
                "for worker-007). Independent verification of open claim w072-20260912T001917-claim-conclusion-poor "
                "at pinned hashes 276009f4f63d / ce42d205e761 / 315c19145065 -> CONFIRMED; 10 bound entries, "
                "0 WCC conclusions, 0 H4 namings, 0 falsifier witnesses, controls 8/8 pass, reconstructed "
                "worker-072 rule reproduced exactly (5/10). Two non-blocking rule-quality findings recorded "
                "(H1 vacuity, H2 substring hazard). Live inputs had drifted (F0 0abb9ed8a961, ledger "
                "a1674f094979); the same scan on the live ledger gives identical counts. Evidence hash-pinned; "
                "worker cannot set done/passed or a gate verdict."
            ),
            "next_falsifier": (
                "Falsified by any ledger entry that passes H1-H3, names a positive genericity notion with a "
                "topology, and carries conclusion_type=weak_cosmic_censorship; or by an unbound "
                "class-conforming WCC entry. A later revision supersedes but does not falsify."
            ),
            "evidence_refs": [r_ref, c_ref, m_ref, snap_f0, snap_led],
        },
    ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"appended {len(events)} events to {OUT.relative_to(ROOT)}")
    for e in events:
        print(" ", e["event_id"], e["event_type"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
