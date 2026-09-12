#!/usr/bin/env python3
"""Emit reviews/L0-review-032.json + comms/outbox/worker-032.jsonl + checkpoint.

Run after artifacts/worker-032/l0_review/run_checks.py.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TARGET_LEDGER = "ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72"
TARGET_AUDIT = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# Hard guard: never bind a verdict to bytes that moved after the checks ran.
_ledger_now = sha(ROOT / "ledger/theorems.jsonl")
_audit_now = sha(ROOT / "ledger/citation_audit.csv")
if _ledger_now != TARGET_LEDGER or _audit_now != TARGET_AUDIT:
    print("ABORT: frozen target moved after checks; re-run run_checks.py", file=sys.stderr)
    print(json.dumps({"ledger_now": _ledger_now, "audit_now": _audit_now}, indent=1), file=sys.stderr)
    raise SystemExit(2)

report_path = ROOT / "artifacts/worker-032/l0_review/report.json"
runner_path = ROOT / "artifacts/worker-032/l0_review/run_checks.py"
report = json.loads(report_path.read_text())
report_sha = sha(report_path)
runner_sha = sha(runner_path)
ts = now()
review_id = f"w032-l0-{ts}"

review = {
    "review_id": review_id,
    "reviewer": "worker-032",
    "actor": "worker-032",
    "node_id": "L0",
    "targets": [
        {
            "target_id": "L0",
            "artifact": "ledger/theorems.jsonl",
            "artifact_sha256": TARGET_LEDGER,
            "rows": 62,
        },
        {
            "target_id": "L1",
            "artifact": "ledger/citation_audit.csv",
            "artifact_sha256": TARGET_AUDIT,
            "rows": 97,
            "scope": "spot-check binding, registry resolution and class mapping only; not a full L1 content review",
        },
    ],
    "created_at": ts,
    "purpose": (
        "Independent blind review at the frozen L0/L1 hashes requested by the literature lead's "
        "blocker lit-l3-20260912-007 (BL-1). G-LIT records 0 independent accepts at this hash. "
        "This review recomputes the three astra-life01-l0-revise acceptance criteria from the pinned "
        "bytes and adds three reviewer-owned locator re-fetches that are disjoint from the four in "
        "artifacts/literature/reviews/L1-spotcheck-rev2.json."
    ),
    "b_n_policy": (
        "B = a finding that blocks accept. N = backlog; it does not block. Verdict is revise only if "
        "at least one B finding is recorded. N-C5/N-C6 are carried backlog, already dispositioned by "
        "the lead as rev-3 work pending a controller decision; they do not touch class tokens, "
        "citations, or unresolved marking and therefore do not block the three acceptance criteria."
    ),
    "assignment_ref": ["astra-indep-1-L0-L1-literature", "astra-life01-l0-revise", "lit-l3-20260912-007"],
    "independence": {
        "author_of_target": False,
        "targets_authored_by": "astra-lead-literature",
        "prior_verdicts_at_this_hash": 0,
        "exposure": (
            "Read handoff/map, comms/outbox/astra-lead-literature.jsonl (BL-1/BL-2/BL-3), "
            "artifacts/literature/reviews/L0-rev2-disposition.md and L1-spotcheck-rev2.json before "
            "designing the checks. The disposition is the lead's self-assessment and was treated as a "
            "hypothesis to falsify, not as evidence; every number below is recomputed from the pinned "
            "bytes by artifacts/worker-032/l0_review/run_checks.py."
        ),
        "kish_ess": {
            "verdicts_in_this_file": 2,
            "independent_reviewers": 1,
            "ess_estimate": 1.0,
            "note": (
                "One reviewer produced the L0 and the L1-binding verdict; the shared reviewer caps ESS. "
                "G-LIT still needs a second distinct independent reviewer at these hashes."
            ),
        },
        "instrument_correction": (
            "The first automated pass raised a false B finding because ledger/citation_audit.csv keys "
            "sources as `citation_id`, not `source_id`. The check was corrected to accept either key and "
            "re-run before any verdict was emitted. Recorded so the false blocker is not re-derived."
        ),
    },
    "frozen_binding": {
        "ledger/theorems.jsonl": TARGET_LEDGER,
        "ledger/citation_audit.csv": TARGET_AUDIT,
        "pins_match_declared": report["target_pins_match_declared"],
        "hash_stable_during_review": report["hash_stable_during_review"],
        "support_pins": report["pins_before"],
        "machine_evidence": f"artifacts/worker-032/l0_review/report.json#{report_sha[:12]}",
        "runner": f"artifacts/worker-032/l0_review/run_checks.py#{runner_sha[:12]}",
    },
    "checks": {
        "C1_class_token_binding": {
            "result": report["checks"]["C1_class_token_census"]["verdict"],
            "detail": (
                "49 class tokens across class_ids+informs_classes: AF-WCC-VAC-GEN 11, AF-SCC-C0-VAC-GEN 14, "
                "AF-SCC-C2-VAC-GEN 14, AF-WCC-SCALAR-SPH 10; 0 tokens outside the frozen four; 0 class-like "
                "tokens in ledger_tags. Matches the disposition's census."
            ),
        },
        "C2_unresolved_marking": {
            "result": report["checks"]["C2_unresolved_marking"]["verdict"],
            "detail": "62/62 rows carry a non-empty unresolved list with no empty entries.",
        },
        "C3_source_resolution": {
            "result": report["checks"]["C3_source_resolution"]["verdict"],
            "detail": (
                "97 registry rows with 97 unique ids; every source_id in all 62 rows resolves in both "
                "registry.jsonl and citation_audit.csv (keyed there as citation_id); 0 dangling."
            ),
        },
        "C4_spotcheck_binding": {
            "result": report["checks"]["C4_spotcheck_binding"]["verdict"],
            "detail": (
                "L1-spotcheck-rev2.json (sha 11db40b9f1c8) binds both frozen hashes; 4 independent targets "
                "recounted (SRC-002/004/057/059) plus 4 lead-corroborating and 2 Crossref checks; verdicts "
                "6 pass / 1 partial / 1 pass-with-caveat; >=3 independent criterion met."
            ),
        },
        "C5_status_discipline": {
            "result": report["checks"]["C5_conclusion_and_status_discipline"]["verdict"],
            "detail": (
                "0 accepted rows with verification_status=unverified; 0 rows claiming full-text/page-checked "
                "without full-text registry evidence. 30 theorem-typed rows carry no artifact_refs (N-C5)."
            ),
        },
        "C6_evidence_depth": {
            "result": "observation_only",
            "detail": "registry evidence 84 abstract / 12 metadata / 1 full-text; 0/62 and 0/97 rows carry source_meta (N-C6).",
        },
        "C7_T301_residual": {
            "result": "scope_caveat",
            "detail": report["checks"]["C7_T301_residual"],
        },
        "C8_independent_refetch": {
            "result": "3 MATCH / 1 not independently re-verified (PDF tool limitation)",
            "detail": report["checks"]["C8_independent_refetch"]["results"],
        },
    },
    "verdicts": [
        {
            "target_id": "L0",
            "artifact": "ledger/theorems.jsonl",
            "artifact_sha256": TARGET_LEDGER,
            "verdict": "accept",
            "score": 4,
            "blocking_findings": [],
            "non_blocking_findings": ["N-C5", "N-C6", "N-C7"],
            "scope_of_accept": (
                "class-token binding, unresolved marking, source resolution, status discipline, spot-check "
                "binding count, and three reviewer-owned locator re-fetches, all at the pinned hash. This "
                "accept does NOT certify mathematical correctness of any statement, full-text theorem scope "
                "for the 84 abstract-level sources, or source_meta completeness."
            ),
        },
        {
            "target_id": "L1",
            "artifact": "ledger/citation_audit.csv",
            "artifact_sha256": TARGET_AUDIT,
            "verdict": "accept",
            "score": 4,
            "blocking_findings": [],
            "non_blocking_findings": [],
            "scope_of_accept": (
                "binding of the spot-check evidence to this hash and resolution of every ledger source_id "
                "against this audit. Not a full review of the 97 audit rows' evidence depth or assessment "
                "columns."
            ),
        },
    ],
    "findings": [
        {
            "label": "N-C5",
            "severity": "non_blocking",
            "finding": (
                "30 rows carry conclusion_type=theorem with no artifact_refs. This is the flash-17 HF-01 "
                "claim-vocabulary collision; the A0 rubric detector is claim-scoped (evaluation_rubric.yaml:174) "
                "and does not fire on ledger rows. The lead disposition defers it to a bounded rev 3 pending a "
                "controller decision. It changes no class token, citation, or unresolved marking."
            ),
            "owner": "astra-lead-literature / controller decision",
            "falsifier": "a row where conclusion_type=theorem is used to assert a node/gate completion, or a controller ruling that the rubric's claim-scoped detector must also bind ledger rows.",
        },
        {
            "label": "N-C6",
            "severity": "non_blocking",
            "finding": (
                "0/62 ledger and 0/97 registry rows carry source_meta (matter_model, cosmological_constant, "
                "dimension, symmetry, formulation); registry evidence depth is 84 abstract / 12 metadata / "
                "1 full-text, so most source bodies are abstract-level. Deferred as rev-3 work (BL-2) and "
                "constrained by paywalled primaries (BL-3)."
            ),
            "owner": "astra-lead-literature / human-pi for library access",
            "falsifier": "a class-scope or genericity claim in a ledger row that cannot be decided from its recorded evidence level.",
        },
        {
            "label": "N-C7",
            "severity": "non_blocking",
            "finding": (
                "T-301 retains class_ids=[AF-SCC-C0-VAC-GEN] while conclusion_type=conditional_theorem and the "
                "data assumptions are interior/local (flash-16 residual). does_not_imply and scope_caveats are "
                "populated, so it is a scope caveat rather than a class-token defect at this hash."
            ),
            "owner": "astra-lead-literature / astra-lead-formulation",
            "falsifier": "a downstream claim that cites T-301 as an unconditional C0 refutation for all generic AF vacuum data.",
        },
    ],
    "not_claimed": [
        "no gate verdict (G-LIT remains with the controller)",
        "no node completion or status=done",
        "no theorem, counterexample, or numerical result",
        "no edit to the ledger, registry, audit, or map",
    ],
    "evidence_refs": [
        f"ledger/theorems.jsonl#{TARGET_LEDGER[:12]}",
        f"ledger/citation_audit.csv#{TARGET_AUDIT[:12]}",
        f"artifacts/worker-032/l0_review/report.json#{report_sha[:12]}",
        f"artifacts/worker-032/l0_review/run_checks.py#{runner_sha[:12]}",
        "artifacts/literature/reviews/L1-spotcheck-rev2.json#11db40b9f1c8",
        "artifacts/literature/registry.jsonl",
        "artifacts/literature/reviews/L0-rev2-disposition.md",
        "comms/outbox/astra-lead-literature.jsonl#lit-l3-20260912-007",
    ],
    "next_falsifier": (
        "Re-hash both targets; if either moves, this review is void and must not be counted. A blocking "
        "finding is one that would break a class token, a citation resolution, the unresolved marking, or "
        "the >=3 independent spot-check requirement at the new hash. A second distinct reviewer at "
        "ce42d205/315c1914 is still required before G-LIT can be judged."
    ),
}

review_path = ROOT / "reviews/L0-review-032.json"
review_path.write_text(json.dumps(review, indent=1, ensure_ascii=False) + "\n")
review_sha = sha(review_path)

events = [
    {
        "event_id": "w032-20260912T0026-art-l0-review-evidence",
        "event_type": "artifact",
        "created_at": ts,
        "actor": "worker-032",
        "node_id": "L0",
        "artifact_type": "l0_independent_review_evidence",
        "path": "artifacts/worker-032/l0_review/report.json",
        "sha256": report_sha,
        "validation_status": "unverified",
        "evidence_refs": [f"ledger/theorems.jsonl#{TARGET_LEDGER[:12]}", f"ledger/citation_audit.csv#{TARGET_AUDIT[:12]}"],
        "class_ids": review["targets"][0].get("class_ids", ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]),
    },
    {
        "event_id": "w032-20260912T0026-art-l0-review",
        "event_type": "artifact",
        "created_at": ts,
        "actor": "worker-032",
        "node_id": "L0",
        "artifact_type": "independent_review",
        "path": "reviews/L0-review-032.json",
        "sha256": review_sha,
        "validation_status": "unverified",
        "evidence_refs": [f"artifacts/worker-032/l0_review/report.json#{report_sha[:12]}",
                           f"ledger/theorems.jsonl#{TARGET_LEDGER[:12]}",
                           f"ledger/citation_audit.csv#{TARGET_AUDIT[:12]}"],
    },
    {
        "event_id": "w032-20260912T0026-review-l0",
        "event_type": "review",
        "created_at": ts,
        "actor": "worker-032",
        "node_id": "L0",
        "target_id": f"L0:ledger/theorems.jsonl#{TARGET_LEDGER[:12]}",
        "reviewer": "worker-032",
        "verdict": "accept",
        "score": 4,
        "hard_failures": [],
        "findings": [
            "N-C5 30 theorem-typed rows without artifact_refs (deferred rev-3 backlog)",
            "N-C6 source_meta absent 0/62; evidence depth 84 abstract/12 metadata/1 full-text",
            "N-C7 T-301 retains C0 class_ids with interior/local data assumptions (scope caveat)",
            "C8 three reviewer-owned re-fetches (SRC-001/003/009) all MATCH at title/author/year level",
        ],
        "evidence_refs": [f"reviews/L0-review-032.json#{review_sha[:12]}",
                           f"artifacts/worker-032/l0_review/report.json#{report_sha[:12]}",
                           f"ledger/theorems.jsonl#{TARGET_LEDGER[:12]}",
                           f"ledger/citation_audit.csv#{TARGET_AUDIT[:12]}"],
        "scope": review["verdicts"][0]["scope_of_accept"],
        "independence": "not an author; 0 prior verdicts at this hash; single-reviewer ESS=1, a second reviewer is still required",
    },
    {
        "event_id": "w032-20260912T0026-claim-l0",
        "event_type": "claim",
        "created_at": ts,
        "actor": "worker-032",
        "node_id": "L0",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "conclusion_type": "formal_model",
        "statement": (
            "At ledger/theorems.jsonl sha256 ce42d205e761 and ledger/citation_audit.csv sha256 315c19145065, "
            "independently recomputed: (1) all 49 class tokens in class_ids+informs_classes are within the frozen "
            "four, 0 extension tokens, 0 class-like tokens in ledger_tags; (2) 62/62 rows carry a non-empty "
            "unresolved list; (3) every source_id in all 62 rows resolves in the 97-row registry and the 97-row "
            "audit; (4) the four independent spot-check targets in L1-spotcheck-rev2.json (sha 11db40b9f1c8) bind "
            "both frozen hashes; (5) 0 accepted rows have verification_status=unverified and 0 overstate their "
            "registry evidence; (6) three reviewer-owned re-fetches disjoint from that file's independent set "
            "(SRC-001, SRC-003, SRC-009) return MATCH at title/author/year level. The three "
            "astra-life01-l0-revise acceptance criteria are met at this hash, subject to a second independent "
            "reviewer; this is not a gate verdict."
        ),
        "assumptions": [
            "the frozen hashes did not move during the review (re-measured at the end: stable)",
            "re-fetch verification is title/author/year-level and does not cover full-text theorem scope",
            "ledger rows are the unit of review; no physics/mathematical correctness is asserted",
        ],
        "falsifier": review["next_falsifier"],
        "evidence_refs": [f"reviews/L0-review-032.json#{review_sha[:12]}",
                           f"artifacts/worker-032/l0_review/report.json#{report_sha[:12]}",
                           f"ledger/theorems.jsonl#{TARGET_LEDGER[:12]}",
                           f"ledger/citation_audit.csv#{TARGET_AUDIT[:12]}"],
        "artifact_refs": [f"reviews/L0-review-032.json#{review_sha[:12]}",
                           f"artifacts/worker-032/l0_review/report.json#{report_sha[:12]}"],
    },
    {
        "event_id": "w032-20260912T0026-status-l0",
        "event_type": "status",
        "created_at": ts,
        "actor": "worker-032",
        "node_id": "L0",
        "class_id": "AF-WCC-VAC-GEN",
        "status": "active",
        "hours": 0.6,
        "summary": (
            "Delivered W032-L0-BLIND-REVIEW-01: independent accept verdicts for L0 (ledger ce42d205) and the "
            "L1 spot-check binding (audit 315c1914), with 0 blocking findings and 3 non-blocking backlog items; "
            "3 reviewer-owned re-fetch checks all MATCH. Second independent reviewer at the same hashes is still "
            "required. No gate verdict, no node completion, no ledger edit."
        ),
        "evidence_refs": [f"reviews/L0-review-032.json#{review_sha[:12]}",
                           f"artifacts/worker-032/l0_review/report.json#{report_sha[:12]}",
                           f"ledger/theorems.jsonl#{TARGET_LEDGER[:12]}",
                           f"ledger/citation_audit.csv#{TARGET_AUDIT[:12]}"],
        "next_falsifier": review["next_falsifier"],
    },
]

for ev in events:
    validate_event(ev)
with (ROOT / "comms/outbox/worker-032.jsonl").open("a") as f:
    for ev in events:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")

checkpoint = {
    "checkpoint": 1,
    "at": ts,
    "worker": "worker-032",
    "run": "independent fleet 2026-09-12T00:16:57",
    "assignment": "W032-L0-BLIND-REVIEW-01 (self-claimed; no inbox card existed; BL-1 requested it)",
    "node_id": "L0",
    "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
    "hours_spent_estimate": 0.6,
    "status": {
        "delivered": True,
        "validation_status": "unverified",
        "verdict": "accept (scope-limited; B-count 0, N-count 3)",
        "second_reviewer_still_required": True,
        "no_completion_claim": "worker cannot set done/passed/gate verdict; no theorem or physics result",
    },
    "artifacts": {
        "reviews/L0-review-032.json": {"sha256": review_sha},
        "artifacts/worker-032/l0_review/report.json": {"sha256": report_sha},
        "artifacts/worker-032/l0_review/run_checks.py": {"sha256": runner_sha},
    },
    "pins": {
        "ledger/theorems.jsonl": report["pins_after"]["ledger/theorems.jsonl"],
        "ledger/citation_audit.csv": report["pins_after"]["ledger/citation_audit.csv"],
        "artifacts/formulation/rule_spec.json": report["pins_after"]["artifacts/formulation/rule_spec.json"],
        "research_map/formulation_taxonomy.yaml": report["pins_after"]["research_map/formulation_taxonomy.yaml"],
        "hash_stable_during_review": report["hash_stable_during_review"],
    },
    "outbox_events": [e["event_id"] for e in events],
    "open_items": {
        "N-C5": "30 theorem-typed rows without artifact_refs (rev-3 backlog)",
        "N-C6": "source_meta absent; 84/97 sources abstract-level; paywalled primaries",
        "N-C7": "T-301 C0 class binding with interior/local data assumptions",
    },
    "next_falsifier": review["next_falsifier"],
}
ck = ROOT / "runtime/state/w32_checkpoint_1.json"
ck.write_text(json.dumps(checkpoint, indent=1, ensure_ascii=False) + "\n")
print(json.dumps({"review_sha256": review_sha, "report_sha256": report_sha,
                  "runner_sha256": runner_sha, "events": [e["event_id"] for e in events],
                  "checkpoint": str(ck)}, indent=1))
