"""Controller event emission for the astra-lifecycle-03 pass (idempotent).

Appends hash-bound gate records, bounded assignments, resource approvals and one
direction update to the accepted event stream via comms.append_event, and mirrors
each assignment into the assignee's downward inbox. Re-running is safe: duplicate
event_ids are ignored and already-sent inbox cards are skipped.

CF-12 rule respected: every new assignment names a concrete artifact path that is
not named by another open assignment. astra-life03-close-findings is an explicit
successor that supersedes the publication-only assignments astra-life01-publish-frozen
and astra-life02-publish-f0 (their publication goals landed or folded in).

Numerics: no new N1 work. The only numerics event is a 1.0 agent-hour approval for
the C8 protocol review, which is already an open assignment on an N0-allowed node;
numerics_lock stays locked.

  python3 research_map/astra_lifecycle_03_events.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research_map"))
import comms  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")

F0_H = "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc"
F1_H = "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503"
F2A_H = "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2"
F2B_H = "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"
L0_H = "ce42d205e761"
L1_H = "315c19145065"
PROTO_H = "1e6cdf04d7a2"

GATES = [
    {
        "event_id": "astra-life03-gate-gf0", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-F0", "scope": "F0", "verdict": "pending",
        "criteria": (
            "F0 taxonomy exists; exactly the four frozen class ids; disjointness tests; two "
            "independent reviewer verdicts at one hash. WITHHELD at canonical " + F0_H[:12] + ": "
            "one full-schema verdict on record (reviews/F0-review-lead-audit-r2.json, revise 4.0); "
            "zero accepts. Publication pair is divergent (canonical " + F0_H[:12] + " vs authoring "
            "c8e979a1eb48), so a verdict is not transferable between trees until the author "
            "publishes one byte-identical revision (astra-life02-publish-f0, carried into "
            "astra-life03-close-findings). The residual review objection is FROZEN.json manifest "
            "churn plus future-dated frozen_at stamps, not class content."
        ),
        "evidence_refs": ["research_map/formulation_taxonomy.yaml",
                          "artifacts/formulation/formulation_taxonomy.yaml",
                          "reviews/F0-review-lead-audit-r2.json",
                          "artifacts/formulation/FROZEN.json",
                          "research_map/research_map.json#controller_gate_audit"],
    },
    {
        "event_id": "astra-life03-gate-gform", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-FORM", "scope": "F1,F2a,F2b", "verdict": "pending",
        "criteria": (
            "Three separate class schemas at canonical paths with exact quantifiers/topology/"
            "regularity/genericity/I+/visibility/conclusion_type; no C0/C2 merge; two independent "
            "accepts per class citing the measured sha256. Measured and aligned: F1 " + F1_H[:12] +
            ", F2a " + F2A_H[:12] + ", F2b " + F2B_H[:12] + " (canonical == authoring == FROZEN "
            "rev25 af24e9c3). Review state at these hashes: F1 accept 4.5 "
            "(reviews/F1-review-lead-audit-r2.json) plus three independent revises with concrete "
            "hard findings (reviews/F1-review-090.json, F1-review-094.json, F1-review-19.json: "
            "duplicate YAML keys / future-dated revised_at, class_contract_pointer to the authoring "
            "tree, undefined AF_{I+} symbol, quantifier contradiction); F2a accept 4.0 "
            "(reviews/F2a-review-047.json); F2b accept 4.0 (reviews/F2b-review-worker-001.json) "
            "plus revise 3.0 with hard findings (reviews/F2b-review-034.json: quantifier domain, "
            "F0 contract pointer does not resolve at the declared F0 artifact). Gate cannot pass "
            "with unresolved hash-bound hard findings."
        ),
        "evidence_refs": ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                          "schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/FROZEN.json",
                          "reviews/F1-review-lead-audit-r2.json", "reviews/F1-review-090.json",
                          "reviews/F1-review-094.json", "reviews/F1-review-19.json",
                          "reviews/F2a-review-047.json", "reviews/F2b-review-worker-001.json",
                          "reviews/F2b-review-034.json",
                          "research_map/research_map.json#controller_gate_audit"],
    },
    {
        "event_id": "astra-life03-gate-glit", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-LIT", "scope": "L0,L1", "verdict": "pending",
        "criteria": (
            "Ledger rows carry resolvable locators; verification_status honest; >=3 independent "
            "re-fetch spot checks at the measured ledger hash; unresolved citations marked "
            "unresolved; two independent reviewer verdicts. Measured L0 " + L0_H + ", L1 " + L1_H +
            ". L1 criterion is MET in count (6 independent spot checks bind " + L1_H + ": workers "
            "023/026/07/070/077/086), but L0 has zero accepts at its measured hash and the "
            "literature lead reports the remaining obstacle as reviewer latency, not artifact "
            "quality (lit-l3-20260912-010, approved at 3.0 agent-hours). Gate stays pending until "
            "two independent verdicts bind L0 " + L0_H + "."
        ),
        "evidence_refs": ["ledger/theorems.jsonl", "ledger/citation_audit.csv",
                          "reviews/L0-review-17.json", "reviews/A1-rebind-coverage.json",
                          "research_map/research_map.json#controller_gate_audit"],
    },
    {
        "event_id": "astra-life03-gate-gnum", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-NUM", "scope": "N0", "verdict": "pending",
        "criteria": (
            "Flat-space convergence order measured and independently replicated within tolerance; "
            "numerical protocol independently reviewed (criterion C8); lock guard passes. "
            "self-gravitating numerics remain locked (solver_absent=True, guard_present=True). "
            "Protocol measured " + PROTO_H + "; the recorded verdict "
            "reviews/G-NUM-protocol-review.json binds 01b2072434cd (stale), so C8 is the exact "
            "unmet requirement at the current revision. N0 replication verdict on disk is "
            "PROVISIONAL. G-NUM passing would certify N0 only; N1 stays locked until G-FORM and "
            "G-AUDIT also pass and the N0 order is measured and independently replicated."
        ),
        "evidence_refs": ["numerics/CONVERGENCE_PROTOCOL.md",
                          "reviews/G-NUM-protocol-review.json",
                          "numerics/tests/selfgravity_lock_guard.py",
                          "numerics/protocol/fixed_replication_verdict.json",
                          "research_map/research_map.json#controller_gate_audit"],
    },
    {
        "event_id": "astra-life03-gate-gaudit", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-AUDIT", "scope": "A0,A1", "verdict": "pending",
        "criteria": (
            "A0 rubric exists without a universal scalar score; A1 carries two independent "
            "full-schema verdicts per target, each citing a measured sha256. A0 measured "
            "d748a9e3574e. At the measured canonical hashes there are zero independent accepts per "
            "target for the A1 rebinding set; the current F1/F2a/F2b verdicts are a mix of accepts "
            "and hash-bound revises whose findings must be closed and re-reviewed under "
            "astra-life03-close-findings and astra-life03-verify-gform. Superseded-hash verdicts do "
            "not count."
        ),
        "evidence_refs": ["evaluation_rubric.yaml", "reviews/A1-rebind-coverage.json",
                          "runtime/state/artifact_hashes.json",
                          "research_map/research_map.json#controller_gate_audit"],
    },
]

ASSIGNMENTS = [
    {
        "event_id": "astra-life03-close-findings", "event_type": "assignment", "actor": "astra",
        "created_at": NOW, "node_id": "F0,F1,F2a,F2b", "assignee": "astra-lead-formulation",
        "artifact": ["research_map/formulation_taxonomy.yaml", "schemas/af_wcc_vacuum.yaml",
                     "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"],
        "gate": "G-FORM", "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "evidence_refs": ["reviews/F1-review-090.json", "reviews/F1-review-094.json",
                          "reviews/F1-review-19.json", "reviews/F2b-review-034.json",
                          "reviews/F0-review-lead-audit-r2.json",
                          "reviews/F1-review-lead-audit-r2.json",
                          "artifacts/formulation/FROZEN.json"],
        "acceptance": (
            "SUPERSEDES astra-life01-publish-frozen and astra-life02-publish-f0: for these four "
            "paths the publication goal has landed (F1/F2a/F2b aligned at " + F1_H[:12] + "/" +
            F2A_H[:12] + "/" + F2B_H[:12] + ") or folds in (F0 still divergent). Close the "
            "hash-bound hard findings in the listed reviews or explicitly disposition each one with "
            "a hash-bound rationale in the revision note: (a) duplicate top-level YAML keys "
            "(7x revised_at, 2x revised_at_unused) and future-dated machine-readable timestamps; "
            "(b) class_contract_pointer values that target artifacts/formulation/ or do not resolve "
            "at the declared F0 artifact -- repoint them at the canonical taxonomy "
            "research_map/formulation_taxonomy.yaml; (c) undefined AF_{I+} in "
            "conclusion.statement_formal; (d) the quantifier-domain/quantifier-contradiction "
            "findings in F1-review-19 and F2b-review-034. Publish ONE frozen revision per path so "
            "that canonical == authoring and FROZEN.json carries a single sha256 per logical "
            "artifact, revision bumped, artifact events re-emitted with the new hashes, and "
            "frozen_at stamped with wall-clock. No new class ids; semantic changes only as recorded "
            "revision deltas. F0 must additionally be published byte-identically to both trees."
        ),
        "budget_agent_hours": 2.0,
        "expected_information_gain": (
            "Removes the only substantive obstacle between the frozen rev25 schemas and a G-FORM / "
            "G-F0 verdict: unresolved hash-bound reviewer objections."),
        "falsifier": (
            "Any listed hard finding still unresolved at the new hash, a new non-frozen class id, "
            "canonical/authoring divergence after the re-freeze, or a frozen_at later than write "
            "wall-clock."),
        "stop_rule": (
            "2 agent-hours or two revision bumps; a contested finding is recorded as a disposition "
            "with evidence rather than looped on. No further semantic churn after the re-freeze."),
        "deadline": "2026-09-12T01:30:00+08:00",
        "controller_note": (
            "Canonical path stays authoritative; do not repoint the map at the authoring tree. "
            "This is a successor, not a duplicate: the two superseded assignments asked only for "
            "publication/freezing and are discharged by this scope."),
    },
    {
        "event_id": "astra-life03-verify-gform", "event_type": "assignment", "actor": "astra",
        "created_at": NOW, "node_id": "F1,F2a,F2b", "assignee": "astra-lead-audit",
        "artifact": "reviews/G-FORM-final-verify.json",
        "gate": "G-FORM", "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "evidence_refs": ["reviews/F1-review-lead-audit-r2.json", "reviews/F2a-review-047.json",
                          "reviews/F2b-review-worker-001.json", "reviews/A1-rebind-coverage.json",
                          "artifacts/formulation/FROZEN.json"],
        "acceptance": (
            "Narrow successor to astra-life01-a1-rebind for F1/F2a/F2b at the revision frozen by "
            "astra-life03-close-findings. For each class: at least two full-schema verdicts from "
            "distinct reviewers who did not author the artifact, each citing path#sha256, plus a "
            "per-class coverage table that states which existing accepts were re-pinned and which "
            "were voided by the hash move. Existing accepts (lead-audit F1 r2, worker-047 F2a, "
            "worker-001 F2b) count only if re-pinned to the new hash. Every hard finding in this "
            "pass's closure round is confirmed fixed or carried as an open objection. Output "
            "reviews/G-FORM-final-verify.json with the closing verdict and cited hashes."
        ),
        "budget_agent_hours": 2.0,
        "expected_information_gain": (
            "Makes G-FORM judgeable at one frozen hash: either two accepts per class or a concrete "
            "defect list."),
        "falsifier": (
            "A cited sha256 that is not the frozen hash, two verdicts by the same reviewer, a "
            "verdict from an author of the artifact, or an unresolved hard finding counted as "
            "accept."),
        "stop_rule": (
            "2 agent-hours; a revise verdict with a concrete defect is an acceptable outcome. If a "
            "schema changes while reviewing, stop and report a moving-target blocker instead of "
            "binding a stale hash."),
        "deadline": "2026-09-12T02:00:00+08:00",
        "controller_note": (
            "Sequenced after astra-life03-close-findings; do not spend hours on the pre-revision "
            "hashes beyond recording which current accepts are void."),
    },
    {
        "event_id": "astra-life03-verify-gf0", "event_type": "assignment", "actor": "astra",
        "created_at": NOW, "node_id": "F0", "assignee": "astra-lead-audit",
        "artifact": "reviews/G-F0-final-verify.json",
        "gate": "G-F0", "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "evidence_refs": ["research_map/formulation_taxonomy.yaml",
                          "artifacts/formulation/formulation_taxonomy.yaml",
                          "reviews/F0-review-lead-audit-r2.json",
                          "artifacts/formulation/FROZEN.json"],
        "acceptance": (
            "Narrow successor to astra-life01-a1-rebind for F0 at the revision frozen by "
            "astra-life03-close-findings. Two independent full-schema verdicts on "
            "research_map/formulation_taxonomy.yaml at the frozen hash, from reviewers who did not "
            "author it, each citing path#sha256; confirm exactly the four frozen class ids, the "
            "single-q visibility predicate, the explicit comeager quantifier, and that canonical "
            "== authoring == FROZEN pin. Output reviews/G-F0-final-verify.json."
        ),
        "budget_agent_hours": 1.5,
        "expected_information_gain": (
            "Makes G-F0 judgeable at one published hash; the F0 content objection on record is "
            "manifest clock discipline, not class semantics."),
        "falsifier": (
            "A verdict at a non-frozen hash, a verdict from an author, canonical/authoring "
            "divergence at review time, or a fifth class id treated as frozen."),
        "stop_rule": (
            "1.5 agent-hours; a revise verdict with a concrete defect is acceptable. Stop and report "
            "if the hash moves mid-review."),
        "deadline": "2026-09-12T02:00:00+08:00",
        "controller_note": (
            "Distinct output path from astra-life03-verify-gform; both are adjudicated by the audit "
            "lead and must not collapse into one verdict."),
    },
    {
        "event_id": "astra-life03-repin-claims", "event_type": "assignment", "actor": "astra",
        "created_at": NOW, "node_id": "F0,F1,A1", "assignee": "astra-lead-formulation",
        "artifact": ["schemas/taxonomy_cases.jsonl", "schemas/f1_falsifier_tests.jsonl"],
        "gate": "G-FORM", "class_id": "GLOBAL",
        "evidence_refs": ["schemas/taxonomy_cases.jsonl", "schemas/f1_falsifier_tests.jsonl",
                          "artifacts/flash-02/open_case_disposition.json",
                          "research_map/audit_evidence.py"],
        "acceptance": (
            "Two stale-pin repairs plus one claim rephrase, all downstream of the frozen classes. "
            "(1) Re-pin schemas/taxonomy_cases.jsonl from F0 66bf917b to the post-closure canonical "
            "F0 hash and re-emit its artifact event. (2) Re-pin schemas/f1_falsifier_tests.jsonl "
            "from F1 b65fcc0f / FROZEN rev13 to the post-closure F1 hash and re-emit. (3) Have the "
            "author of claims[36] (deepseek-flash-02, via the lead) emit a superseding claim that "
            "rephrases the open-case statement so the metalinguistic case labels 'TC-F0-N14 C0/C2 "
            "merge' and 'TC-F0-N15 WCC/SCC merge' are not parsed as composite-class assertions; "
            "acceptance is `python3 research_map/audit_evidence.py` reporting zero hard failures. "
            "The controller does not edit another agent's claim text (CF-4)."
        ),
        "budget_agent_hours": 1.0,
        "expected_information_gain": (
            "Clears the last evidence-audit hard failure (CF-16) and removes two downstream "
            "hash-pin drifts that would otherwise re-open after closure."),
        "falsifier": (
            "A corpus still pinned to 66bf917b / b65fcc0f, or a rephrased claim that still asserts "
            "a merged class, or an audit_evidence hard failure still firing on the new claim."),
        "stop_rule": "1 agent-hour; publish only, no semantic change to the frozen classes.",
        "deadline": "2026-09-12T01:30:00+08:00",
    },
    {
        "event_id": "astra-life03-heldout-09", "event_type": "assignment", "actor": "astra",
        "created_at": NOW, "node_id": "A1", "assignee": "astra-lead-formulation",
        "artifact": ["artifacts/heldout/heldout-09/manifest.json",
                     "artifacts/heldout/heldout-09/report.json"],
        "gate": "G-CLASSBIND",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "evidence_refs": ["artifacts/worker-16/heldout2/report.json",
                          "artifacts/formulation/evidence/heldout_rebased.json",
                          "artifacts/formulation/FROZEN.json"],
        "acceptance": (
            "Re-dispatch FORM-HELDOUT-08's measurement (union escape of the two-stage pipeline) "
            "against the revision frozen by astra-life03-close-findings, as FORM-HELDOUT-09: a "
            "fresh corpus built against the frozen bytes, manifest hashed BEFORE any stage run, "
            ">=20 mutants across >=10 leak families, >=7 controls that must pass both stages, one "
            "fresh independent executor who did NOT build the R26-R31 rules and is not worker-16, "
            "aggregates {structural_escape, semantic_escape, union_escape} plus the union escape "
            "family list, and an independent replication of the frozen result. Start only after "
            "the closure revision is frozen; if the hash moves mid-run, stop and report a "
            "moving-target blocker. Report the escape rate even if unfavorable."
        ),
        "budget_agent_hours": 3.0,
        "expected_information_gain": (
            "Replaces the rev13 out-of-sample estimate (union escape 1.0 on a superseded revision) "
            "with a measurement of the pipeline that would actually gate class binding."),
        "falsifier": (
            "A corpus built against superseded bytes, a manifest hashed after the run, "
            "format-dominated controls (any control rejected by either stage), or a union escape "
            "rate of 0 reported without the raw per-fixture verdicts."),
        "stop_rule": (
            "3 agent-hours or one complete held-out report, whichever is first; no rule edits after "
            "seeing results."),
        "deadline": "2026-09-12T02:30:00+08:00",
        "controller_note": (
            "Successor to the FORM-HELDOUT-08 assignment (worker-16, rev13) whose result is "
            "superseded; do not edit that corpus, build a new one."),
    },
]

DIRECTION_UPDATES = [
    {
        "event_id": "astra-life03-direction-formulation", "event_type": "direction_update",
        "actor": "astra", "created_at": NOW, "group_id": "formulation",
        "old_direction": ("publish/freeze churn and hash-repoint cycles across F0/F1/F2a/F2b while "
                          "waiting for reviewers"),
        "new_direction": ("close the hash-bound hard findings at the frozen rev25 hashes for F0/F1/"
                          "F2a/F2b, re-freeze once, then stop authoring on these paths; independent "
                          "verification (audit lead) and the re-dispatched out-of-sample corpus run "
                          "in parallel on the frozen bytes"),
        "reason": ("Three independent reviewers found concrete defects at the final F1 hash "
                   "(duplicate YAML keys, future-dated revised_at, authoring-tree contract pointer, "
                   "undefined AF_{I+}, quantifier contradiction) and one at F2b (quantifier domain, "
                   "unresolvable F0 pointer); the F0 content review is conformant but flags manifest "
                   "churn. More publication does not advance G-FORM/G-F0 -- finding closure does."),
        "evidence_refs": ["reviews/F1-review-090.json", "reviews/F1-review-094.json",
                          "reviews/F1-review-19.json", "reviews/F2b-review-034.json",
                          "reviews/F0-review-lead-audit-r2.json"],
        "budget_delta_agent_hours": 0.0,
    },
]

APPROVALS = [
    {
        "event_id": "astra-life03-approve-formulation-verification", "event_type": "status",
        "actor": "astra", "created_at": NOW, "node_id": "GLOBAL", "status": "active", "hours": 0.0,
        "summary": ("resource_request leadform-resource-request-2026-09-12T00:44:00+08:00: "
                    "APPROVED 6.0 agent-hours, bounded to the verification round at the final "
                    "rev25 hashes (astra-life03-close-findings 2.0h, astra-life03-verify-gform "
                    "2.0h, astra-life03-verify-gf0 1.5h, plus re-pin overhead). The two earlier "
                    "formulation requests (00:16 and 00:34) are superseded by the requester's own "
                    "final hash set and receive no separate allocation. No self-gravitating work."),
        "evidence_refs": ["comms/outbox/astra-lead-formulation.jsonl",
                          "research_map/research_map.json#resource_requests"],
        "next_falsifier": "Allocation spent on authoring churn rather than independent verification, "
                          "or a verdict citing a superseded hash.",
    },
    {
        "event_id": "astra-life03-approve-literature-review", "event_type": "status",
        "actor": "astra", "created_at": NOW, "node_id": "GLOBAL", "status": "active", "hours": 0.0,
        "summary": ("resource_request lit-l3-20260912-010: APPROVED 3.0 agent-hours for two "
                    "independent reviewers at ledger/theorems.jsonl " + L0_H + " and "
                    "ledger/citation_audit.csv " + L1_H + ", each returning accept|revise|reject "
                    "with a cited sha256 and no ledger edits. If a measured hash moves, both "
                    "verdicts are void and reviewers stop rather than chase the target."),
        "evidence_refs": ["ledger/theorems.jsonl", "ledger/citation_audit.csv",
                          "artifacts/literature/reviews/L0-rev2-disposition.md",
                          "research_map/research_map.json#resource_requests"],
        "next_falsifier": "A verdict without a cited sha256, or a reviewer editing the ledger.",
    },
    {
        "event_id": "astra-life03-approve-numerics-c8", "event_type": "status",
        "actor": "astra", "created_at": NOW, "node_id": "GLOBAL", "status": "active", "hours": 0.0,
        "summary": ("resource_request lnum-resource-request-c8-rev3-20260912T002107: APPROVED 1.0 "
                    "agent-hour for one reviewer independent of the numerics group to record "
                    "accept|revise|reject on numerics/CONVERGENCE_PROTOCOL.md " + PROTO_H + " "
                    "(criterion C8), citing the scheme-appropriate invariant functional, "
                    "resolution-aware drift criterion, order fit with uncertainty, and negative "
                    "controls. numerics_lock stays LOCKED: this is N0-allowed protocol review only, "
                    "no solver code, no N1."),
        "evidence_refs": ["numerics/CONVERGENCE_PROTOCOL.md", "reviews/G-NUM-protocol-review.json",
                          "numerics/tests/selfgravity_lock_guard.py",
                          "research_map/research_map.json#numerics_lock"],
        "next_falsifier": "Any solver/N1 artifact created, or a C8 verdict citing a superseded "
                          "protocol hash.",
    },
]


def _already_sent(agent: str, event_id: str) -> bool:
    p = ROOT / "comms" / "inbox" / f"{agent}.jsonl"
    if not p.exists():
        return False
    for line in p.read_text().splitlines():
        try:
            if json.loads(line).get("event_id") == event_id:
                return True
        except ValueError:
            continue
    return False


def main():
    for ev in GATES + ASSIGNMENTS + DIRECTION_UPDATES + APPROVALS:
        res = comms.append_event(ev)
        print(("APPENDED " if res.get("accepted") else "SKIPPED  ") + ev["event_id"] + " " + ev["event_type"])
    for a in ASSIGNMENTS:
        if _already_sent(a["assignee"], a["event_id"]):
            print(f"INBOX    already-sent <- {a['event_id']}")
            continue
        msg = {k: v for k, v in a.items()}
        msg["to"] = a["assignee"]
        msg["event_type"] = "assignment"
        path = comms.send(a["assignee"], msg)
        print(f"INBOX    {path.relative_to(ROOT)} <- {a['event_id']}")


if __name__ == "__main__":
    main()
