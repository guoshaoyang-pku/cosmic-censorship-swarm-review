#!/usr/bin/env python3
"""Emit W015-N1-GUARD-FAILCLOSED-01 upward events (validated, idempotent, no future timestamps)."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
OUTBOX = REPO / "comms" / "outbox" / "deepseek-flash-15.jsonl"
CST = timezone(timedelta(hours=8))
sys.path.insert(0, str(REPO))
from research_map.schemas import validate_event  # noqa: E402


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


NOW = datetime.now(CST).isoformat()
STAMP = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
P = {
    "report": f"artifacts/flash-15/n1_guard_failclosed/report.json",
    "harness": f"artifacts/flash-15/n1_guard_failclosed/guard_fixtures.py",
    "proposal": f"artifacts/flash-15/n1_guard_failclosed/repaired_proposal.selfgravity_lock_guard.py",
    "readme": f"artifacts/flash-15/n1_guard_failclosed/README.md",
    "rawsums": f"artifacts/flash-15/n1_guard_failclosed/raw/SHA256SUMS.txt",
    "checkpoint": f"artifacts/flash-15/checkpoints/checkpoint-11.json",
}
H = {k: sha(REPO / v) for k, v in P.items()}
GUARD = "numerics/tests/selfgravity_lock_guard.py"
GUARD_H = sha(REPO / GUARD)
MAP_H = sha(REPO / "research_map" / "research_map.json")
EV = []


def add(e):
    validate_event(e)
    EV.append(e)


add({
    "event_id": f"w015-n1guard-artifact-report-{STAMP}",
    "event_type": "artifact",
    "created_at": NOW,
    "actor": "deepseek-flash-15",
    "node_id": "N1",
    "class_id": "AF-WCC-SCALAR-SPH",
    "class_ids": ["AF-WCC-SCALAR-SPH"],
    "gate": "G-NUM",
    "artifact_type": "guard_failclosed_report",
    "path": P["report"],
    "sha256": H["report"],
    "validation_status": "unverified",
    "task_id": "W015-N1-GUARD-FAILCLOSED-01",
    "note": "12-fixture battery: canonical rev1 fails open on 7 fixtures with a planted self-gravity "
            "artifact while returning PASS/exit 0; staged rev2 fail-closed on all 12; live tree PASS "
            "for both. Not a gate verdict; no canonical file written.",
    "evidence_refs": [f"{GUARD}#{GUARD_H[:12]}", f"{P['report']}#{H['report'][:12]}",
                      f"{P['rawsums']}#{H['rawsums'][:12]}"],
})

add({
    "event_id": f"w015-n1guard-artifact-proposal-{STAMP}",
    "event_type": "artifact",
    "created_at": NOW,
    "actor": "deepseek-flash-15",
    "node_id": "N1",
    "class_id": "AF-WCC-SCALAR-SPH",
    "class_ids": ["AF-WCC-SCALAR-SPH"],
    "gate": "G-NUM",
    "artifact_type": "guard_repair_proposal",
    "path": P["proposal"],
    "sha256": H["proposal"],
    "validation_status": "unverified",
    "task_id": "W015-N1-GUARD-FAILCLOSED-01",
    "note": "STAGED, NOT APPLIED. Revision 2 of the lock guard: state allowlists + normalization, "
            "ERROR/exit 2 for absent block / empty state / unknown token / locked-with-no-locked-nodes, "
            "main() maps ERROR->2, extended --self-test. Target stays at rev1 7535ec84.",
    "evidence_refs": [f"{GUARD}#{GUARD_H[:12]}", f"{P['proposal']}#{H['proposal'][:12]}",
                      f"{P['report']}#{H['report'][:12]}"],
})

add({
    "event_id": f"w015-n1guard-artifact-harness-{STAMP}",
    "event_type": "artifact",
    "created_at": NOW,
    "actor": "deepseek-flash-15",
    "node_id": "N1",
    "class_id": "AF-WCC-SCALAR-SPH",
    "class_ids": ["AF-WCC-SCALAR-SPH"],
    "gate": "G-NUM",
    "artifact_type": "verification_harness",
    "path": P["harness"],
    "sha256": H["harness"],
    "validation_status": "unverified",
    "task_id": "W015-N1-GUARD-FAILCLOSED-01",
    "note": "stdlib-only, re-runnable fixture battery; temp-dir fixtures only, never writes numerics/.",
    "evidence_refs": [f"{P['harness']}#{H['harness'][:12]}", f"{P['rawsums']}#{H['rawsums'][:12]}"],
})

add({
    "event_id": f"w015-n1guard-artifact-rawsums-{STAMP}",
    "event_type": "artifact",
    "created_at": NOW,
    "actor": "deepseek-flash-15",
    "node_id": "N1",
    "class_id": "AF-WCC-SCALAR-SPH",
    "class_ids": ["AF-WCC-SCALAR-SPH"],
    "gate": "G-NUM",
    "artifact_type": "evidence_bundle",
    "path": P["rawsums"],
    "sha256": H["rawsums"],
    "validation_status": "unverified",
    "task_id": "W015-N1-GUARD-FAILCLOSED-01",
    "note": "SHA256SUMS over report, harness, proposal, README and all 24 raw rev1/rev2 fixture logs.",
    "evidence_refs": [f"{P['rawsums']}#{H['rawsums'][:12]}"],
})

add({
    "event_id": f"w015-n1guard-artifact-checkpoint-{STAMP}",
    "event_type": "artifact",
    "created_at": NOW,
    "actor": "deepseek-flash-15",
    "node_id": "N1",
    "class_id": "AF-WCC-SCALAR-SPH",
    "class_ids": ["AF-WCC-SCALAR-SPH"],
    "gate": "G-NUM",
    "artifact_type": "checkpoint",
    "path": P["checkpoint"],
    "sha256": H["checkpoint"],
    "validation_status": "unverified",
    "task_id": "W015-N1-GUARD-FAILCLOSED-01",
    "note": "Checkpoint 11 for this slot: pins, headline, findings+falsifiers, artifact hashes.",
    "evidence_refs": [f"{P['checkpoint']}#{H['checkpoint'][:12]}"],
})

add({
    "event_id": f"w015-n1guard-review-w074f3-{STAMP}",
    "event_type": "review",
    "created_at": NOW,
    "actor": "deepseek-flash-15",
    "reviewer": "deepseek-flash-15",
    "target_id": "W074-F3",
    "target_kind": "audit_finding",
    "class_id": "AF-WCC-SCALAR-SPH",
    "class_ids": ["AF-WCC-SCALAR-SPH"],
    "node_id": "N1",
    "gate": "G-NUM",
    "verdict": "accept",
    "score": 4.0,
    "hard_failures": [],
    "findings": [
        "W074-F3 CONFIRMED at the canonical revision-1 bytes (7535ec84): a solver-bearing map with "
        "missing/miscased numerics_lock.state yields PASS/exit 0 (independent fixtures E/F/G/H/L; "
        "7/12 battery fixtures reproduce an open defect).",
        "Repair half now exists as a staged fail-closed revision 2; applying it is lead-numerics/astra "
        "authority and would invalidate the rev1 hash 7535ec84 cited by reviews/G-NUM-protocol-review.json.",
        "Scope limit: W074's reverse probe (a truly released lock must PASS) is preserved by rev2 "
        "(fixture D) and is reported as lock_enforced=false rather than silently passing.",
    ],
    "evidence_refs": [f"{GUARD}#{GUARD_H[:12]}", f"{P['report']}#{H['report'][:12]}",
                      f"{P['proposal']}#{H['proposal'][:12]}"],
    "falsifier": "Void if rev1 does not exit 0/PASS on a temp root with numerics_lock absent/miscased "
                 "and numerics/spherical_solver/ planted (see raw/E..L logs), or if the staged rev2 "
                 "fails any required fixture in report.json.",
})

add({
    "event_id": f"w015-n1guard-review-guard-{STAMP}",
    "event_type": "review",
    "created_at": NOW,
    "actor": "deepseek-flash-15",
    "reviewer": "deepseek-flash-15",
    "target_id": GUARD,
    "target_kind": "instrument",
    "class_id": "AF-WCC-SCALAR-SPH",
    "class_ids": ["AF-WCC-SCALAR-SPH"],
    "node_id": "N1",
    "gate": "G-NUM",
    "verdict": "revise",
    "score": 2.5,
    "hard_failures": ["HF-15-G1 lock-state fail-open (E/F/G/H/L)", "HF-15-G2 vacuous locked lock (J/K)"],
    "findings": [
        "HF-15-G1 blocking: PASS/exit 0 with a planted solver whenever state is not exactly 'locked'.",
        "HF-15-G2 blocking: locked_nodes=[] empties the blocked set; declared N1+ artifacts reached "
        "via depends_on are never checked.",
        "HF-15-G3 advisory: main() would map a returned ERROR verdict to exit 0.",
        "Positive: fixtures A/B/I and the live-tree run are already correct; rev2 keeps them unchanged.",
    ],
    "evidence_refs": [f"{GUARD}#{GUARD_H[:12]}", f"{P['report']}#{H['report'][:12]}",
                      f"{P['proposal']}#{H['proposal'][:12]}"],
    "falsifier": "Void if any of fixtures E/F/G/H/L exits non-zero on rev1, or if a locked-but-empty "
                 "lock with a declared N1+ artifact exits non-zero on rev1.",
})

add({
    "event_id": f"w015-n1guard-claim-{STAMP}",
    "event_type": "claim",
    "created_at": NOW,
    "actor": "deepseek-flash-15",
    "class_id": "AF-WCC-SCALAR-SPH",
    "class_ids": ["AF-WCC-SCALAR-SPH"],
    "node_id": "N1",
    "gate": "G-NUM",
    "conclusion_type": "formal_model",
    "statement": "Instrument measurement at pinned bytes (canonical guard "
                 "numerics/tests/selfgravity_lock_guard.py#7535ec84, live map "
                 f"research_map/research_map.json#{MAP_H[:12]}, rev1 --self-test exit 0): the "
                 "canonical G-NUM lock guard fails open. With numerics/spherical_solver/ planted in "
                 "a temp root it returns verdict PASS and exit 0 for numerics_lock.state in "
                 "{absent block, '', 'Locked', 'LOCKED', 'frozen'}, and it returns PASS for a locked "
                 "lock with locked_nodes=[] even when the declared transitive N1+ artifact "
                 "numerics/results/n2.json is present. 7 of 12 battery fixtures reproduce an open "
                 "defect. The staged revision-2 proposal satisfies all 12 required semantics "
                 "(FAIL->1, ERROR->2, PASS->0) and both revisions PASS/exit 0 on the live tree.",
    "assumptions": [
        "The map's numerics_lock block is the sole authority for the lock state (as stated in the guard's own docstring).",
        "A lock guard must not certify PASS when it cannot parse the state, or when a locked lock blocks no node.",
        "Temp-root fixtures are faithful models of the live tree for the guard's read-only semantics.",
    ],
    "falsifier": "Re-run artifacts/flash-15/n1_guard_failclosed/guard_fixtures.py; the claim is void "
                 "if rev1 exits non-zero on any of E/F/G/H/J/K/L, or if any rev2 (verdict, exit) pair "
                 "differs from report.json.expected_rev2_failclosed.",
    "artifact_refs": [f"{P['report']}#{H['report'][:12]}", f"{P['proposal']}#{H['proposal'][:12]}",
                      f"{P['harness']}#{H['harness'][:12]}"],
    "evidence_refs": [f"{GUARD}#{GUARD_H[:12]}", f"{P['rawsums']}#{H['rawsums'][:12]}",
                      f"research_map/research_map.json#{MAP_H[:12]}"],
})

add({
    "event_id": f"w015-n1guard-status-{STAMP}",
    "event_type": "status",
    "created_at": NOW,
    "actor": "deepseek-flash-15",
    "node_id": "N1",
    "class_id": "AF-WCC-SCALAR-SPH",
    "class_ids": ["AF-WCC-SCALAR-SPH"],
    "gate": "G-NUM",
    "status": "active",
    "hours": 0.3,
    "summary": "No card in inbox for this slot; took W015-N1-GUARD-FAILCLOSED-01 from the live N1/G-NUM "
               "queue: independently reproduced the repair half of W074-F3 on the canonical guard "
               "(rev1 7535ec84) and staged a fail-closed revision 2. Battery PASS: 7/12 fixtures show "
               "rev1 PASS/exit 0 with a planted self-gravity artifact (state absent/empty/miscased/unknown; "
               "vacuous locked_nodes), rev2 matches all 12 required semantics, live tree PASS/exit 0 for "
               "both with numerics/spherical_solver absent. Full battery + raw logs + checkpoint hashed "
               "and emitted. No canonical file written; no gate verdict or node transition claimed.",
    "next_falsifier": "Lead-numerics applies (or rejects) the staged rev2 at numerics/tests/"
                      "selfgravity_lock_guard.py; if applied, the new hash must be re-measured and the "
                      "G-NUM protocol review's rev1 hash 7535ec84 re-bound. Separately: an independent "
                      "non-author must re-run the battery; a single fixture whose rev2 (verdict, exit) "
                      "differs voids HF-15-G4.",
    "evidence_refs": [f"{GUARD}#{GUARD_H[:12]}", f"{P['report']}#{H['report'][:12]}",
                      f"{P['checkpoint']}#{H['checkpoint'][:12]}", f"{P['proposal']}#{H['proposal'][:12]}"],
    "no_completion_claimed": True,
})

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        try:
            existing.add(json.loads(line)["event_id"])
        except Exception:
            pass
new = [e for e in EV if e["event_id"] not in existing]
with OUTBOX.open("a") as fh:
    for e in new:
        fh.write(json.dumps(e, ensure_ascii=False) + "\n")
print(json.dumps({"emitted": len(new), "skipped_existing": len(EV) - len(new),
                  "report_sha256": H["report"], "checkpoint_sha256": H["checkpoint"]}, indent=1))
