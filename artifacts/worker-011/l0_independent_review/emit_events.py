#!/usr/bin/env python3
"""Emit worker-011's L0 independent-verdict events to comms/outbox/worker-011.jsonl.

Every event is validated with research_map.schemas.validate_event BEFORE it is appended,
so an invalid event can never reach the controller's ingest. Appends only to
comms/outbox/worker-011.jsonl (this agent's own outbox) and writes nothing else.

Usage: python3 emit_events.py [--dry-run]
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
OUTBOX = ROOT / "comms/outbox/worker-011.jsonl"
ART = ROOT / "artifacts/worker-011/l0_independent_review"

sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


REVIEW = ROOT / "reviews/L0-review-011.json"
REPORT = ART / "report.json"
CHECKER = ART / "check_l0.py"
REFETCH = ART / "refetch_report.json"

REVIEW_SHA = sha(REVIEW)
REPORT_SHA = sha(REPORT)
CHECKER_SHA = sha(CHECKER)
REFETCH_SHA = sha(REFETCH)

CLAIM = {
    "event_id": "w011-20260912T0025-claim-l0",
    "event_type": "claim",
    "created_at": NOW,
    "actor": "worker-011",
    "node_id": "L0",
    "gate": "G-LIT",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
    "conclusion_type": "formal_model",
    "statement": (
        "At the frozen L0 revision ledger/theorems.jsonl#ce42d205e761 (citation audit "
        "ledger/citation_audit.csv#315c19145065, unchanged across the review window), every "
        "machine-checkable invariant in the astra-life01-l0-revise acceptance list holds: 62 rows, "
        "all class tokens frozen-four, all 92 referenced source_ids resolving in both registry and "
        "audit, all 62 rows carrying a resolving unresolved entry, no duplicates, and no accepted "
        "row resting on unverified or metadata-only evidence. The frozen class-separation detector "
        "returns one lexical flag (T-402 regularity notation), dispositioned as not a merge. Four "
        "primary locators independently re-fetched by this reviewer (not by the author) returned "
        "4/4 title+author matches. The named falsifiers do not fire; the review verdict is accept "
        "at score 4.0 with five documented residuals (HF-01 vocabulary collision, source_meta "
        "backlog, citation-audit ESS=1, HF-04 scope ambiguity, T-301 class_ids vs informs_classes). "
        "This is an evidence/model claim about an artifact; it asserts no physics theorem."
    ),
    "assumptions": [
        "The frozen bytes are ce42d205e761 for L0 and 315c19145065 for L1; a later rewrite voids the verdict.",
        "The A0 rubric HF-01 detector is claim-scoped, as measured in evaluation_rubric.yaml:174.",
        "The ledger rows are evidence records, not `claim` events; the audit verdict is scoped to the L0 acceptance criteria and schema invariants, not to the truth of the cited theorems.",
        "Independent re-fetch verifies identity/attribution of the locator, not the theorem content behind a paywall.",
    ],
    "falsifier": (
        "Re-run artifacts/worker-011/l0_independent_review/check_l0.py on the same bytes: the claim "
        "is falsified if any of C1-C15 fails, or if any of the four refetched locators no longer "
        "resolves to the recorded title/author, or if the L0 bytes change (drift)."
    ),
    "evidence_refs": [
        f"reviews/L0-review-011.json#sha256:{REVIEW_SHA[:12]}",
        f"artifacts/worker-011/l0_independent_review/report.json#sha256:{REPORT_SHA[:12]}",
        f"artifacts/worker-011/l0_independent_review/refetch_report.json#sha256:{REFETCH_SHA[:12]}",
        "ledger/theorems.jsonl#sha256:ce42d205e761",
        "ledger/citation_audit.csv#sha256:315c19145065",
    ],
    "artifact_refs": [
        f"reviews/L0-review-011.json#sha256:{REVIEW_SHA[:12]}",
        f"artifacts/worker-011/l0_independent_review/report.json#sha256:{REPORT_SHA[:12]}",
    ],
    "task_id": "W011-L0-INDEP-VERDICT-01",
    "claims_completion": False,
}

EVENTS = [
    {
        "event_id": "w011-20260912T0025-task-claim",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-011",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "status": "active",
        "hours": 0.1,
        "task_id": "W011-L0-INDEP-VERDICT-01",
        "summary": (
            "No assignment card exists in comms/inbox/worker-011.jsonl (fleet slot 011, launched "
            "00:16:56). Took one bounded class-bound task: W011-L0-INDEP-VERDICT-01 = independent "
            "full-schema verdict on the frozen L0 ledger at ce42d205e761, which the literature lead "
            "froze and explicitly opened for blind review. Chosen because the three canonical "
            "formulation schemas were rewriting every ~10s (moving target) while L0 was stable. "
            "Does not claim node completion or any gate verdict."
        ),
        "evidence_refs": [
            "ledger/theorems.jsonl#sha256:ce42d205e761",
            "ledger/citation_audit.csv#sha256:315c19145065",
            "artifacts/literature/reviews/L0-rev2-disposition.md",
        ],
        "next_falsifier": (
            "A blocking class-leakage, unresolved-source, accepted-on-unverified, or duplication "
            "defect at ce42d205, or drift of the frozen bytes during the review window."
        ),
    },
    {
        "event_id": "w011-20260912T0025-art-artifact-checker",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-011",
        "node_id": "L0",
        "gate": "G-LIT",
        "artifact_type": "checker",
        "path": "artifacts/worker-011/l0_independent_review/check_l0.py",
        "sha256": CHECKER_SHA,
        "validation_status": "unverified",
        "task_id": "W011-L0-INDEP-VERDICT-01",
        "note": "Deterministic 15-check machine audit (hash-pinned inputs, end-of-run drift guard).",
    },
    {
        "event_id": "w011-20260912T0025-art-artifact-report",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-011",
        "node_id": "L0",
        "gate": "G-LIT",
        "artifact_type": "audit_report",
        "path": "artifacts/worker-011/l0_independent_review/report.json",
        "sha256": REPORT_SHA,
        "validation_status": "unverified",
        "task_id": "W011-L0-INDEP-VERDICT-01",
        "note": "15/15 checks pass; recommendation accept; 0 hard failures; residuals C10/C11/C14/C15.",
    },
    {
        "event_id": "w011-20260912T0025-art-artifact-refetch",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-011",
        "node_id": "L0",
        "gate": "G-LIT",
        "artifact_type": "independent_refetch",
        "path": "artifacts/worker-011/l0_independent_review/refetch_report.json",
        "sha256": REFETCH_SHA,
        "validation_status": "unverified",
        "task_id": "W011-L0-INDEP-VERDICT-01",
        "note": "4/4 locators HTTP 200 with title/author match; raw responses retained beside the report.",
    },
    {
        "event_id": "w011-20260912T0025-art-artifact-review",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-011",
        "node_id": "L0",
        "gate": "G-LIT",
        "artifact_type": "review_verdict",
        "path": "reviews/L0-review-011.json",
        "sha256": REVIEW_SHA,
        "validation_status": "unverified",
        "task_id": "W011-L0-INDEP-VERDICT-01",
        "note": "Full-schema independent verdict accept 4.0, bound to ce42d205e761; counts_as_full_schema_verdict=true.",
    },
    {
        "event_id": "w011-20260912T0025-review-l0",
        "event_type": "review",
        "created_at": NOW,
        "actor": "worker-011",
        "node_id": "L0",
        "gate": "G-LIT",
        "target_id": "L0",
        "reviewer": "worker-011",
        "verdict": "accept",
        "score": 4.0,
        "artifact": "ledger/theorems.jsonl",
        "artifact_sha256": "ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72",
        "reviewed_sha256": "ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72",
        "counts_as_full_schema_verdict": True,
        "hard_failures": [],
        "findings": [
            "P1-P4 PASS: assignment criteria 1-3 and the original L0 acceptance list all measured MET at ce42d205.",
            "R1 major residual: 30 conclusion_type=theorem rows with 0 artifact_refs (rubric HF-01 is claim-scoped, so no firing; vocabulary collision).",
            "R2 major residual: 0/97 registry and 0/62 ledger rows carry source_meta (lead-audit HF-03 confirmed open, outside frozen acceptance).",
            "R3 major residual: citation_audit.csv reviewer ESS=1 (92 lead-literature / 5 astra-lead-literature).",
            "R4 major scope ambiguity: rubric HF-04 references quantity_check, absent from the L0 schema, while 46/62 rows contain a quantity.",
            "R5 medium: T-301 keeps class_ids=[AF-SCC-C0-VAC-GEN] although its own does_not_imply disclaims settling the class; recommend informs_classes in rev 3.",
            "S1 soft flag dispositioned: frozen class-separation detector's single finding is T-402 regularity notation ('between C^0 and C^2'), not a class merge.",
        ],
        "task_id": "W011-L0-INDEP-VERDICT-01",
        "evidence_refs": [
            f"reviews/L0-review-011.json#sha256:{REVIEW_SHA[:12]}",
            f"artifacts/worker-011/l0_independent_review/report.json#sha256:{REPORT_SHA[:12]}",
            f"artifacts/worker-011/l0_independent_review/refetch_report.json#sha256:{REFETCH_SHA[:12]}",
            "ledger/theorems.jsonl#sha256:ce42d205e761",
            "evaluation_rubric.yaml#sha256:d748a9e3574e",
        ],
    },
    CLAIM,
    {
        "event_id": "w011-20260912T0025-complete",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-011",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "status": "active",
        "hours": 0.6,
        "task_id": "W011-L0-INDEP-VERDICT-01",
        "summary": (
            "W011-L0-INDEP-VERDICT-01 complete: the review verdict and machine evidence exist on "
            "disk and are hash-pinned; the findings are snapshots with explicit falsifiers and a "
            "drift guard. This is a completion claim for one bounded task, not a node transition: "
            "workers cannot set done/passed or a gate verdict. Checkpoint runtime/state/"
            "w011_checkpoint_1.json follows."
        ),
        "evidence_refs": [
            f"reviews/L0-review-011.json#sha256:{REVIEW_SHA[:12]}",
            f"artifacts/worker-011/l0_independent_review/report.json#sha256:{REPORT_SHA[:12]}",
            f"artifacts/worker-011/l0_independent_review/refetch_report.json#sha256:{REFETCH_SHA[:12]}",
        ],
        "next_falsifier": (
            "Any new L0 sha256 voids the accept and requires re-review; residuals R1-R5 are the "
            "rev-3 backlog and do not block this frozen revision."
        ),
    },
]


def main() -> int:
    dry = "--dry-run" in sys.argv
    lines = []
    for e in EVENTS:
        validate_event(e)
        lines.append(json.dumps(e, ensure_ascii=False, sort_keys=True))
    if dry:
        print(f"dry-run: {len(lines)} events validate; nothing written")
        return 0
    with OUTBOX.open("a") as f:
        for line in lines:
            f.write(line + "\n")
    print(f"appended {len(lines)} validated events to {OUTBOX.relative_to(ROOT)}")
    print(f"review sha256={REVIEW_SHA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
