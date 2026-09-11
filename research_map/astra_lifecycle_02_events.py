"""Controller event emission for the astra-lifecycle-02 pass (idempotent).

Appends hash-bound gate verdicts and bounded assignments to the accepted event
stream via comms.append_event, and mirrors each assignment into the assignee's
downward inbox. Re-running is safe: duplicate event_ids are ignored.

Assignments issued here respect the CF-12 rule: no two open assignments may name
the same canonical path. Existing open assignments (astra-life01-*) are not
duplicated; this pass only adds work that is not already covered.

  python3 research_map/astra_lifecycle_02_events.py
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
DEADLINE_EARLY = "2026-09-12T01:00:00+08:00"
DEADLINE_LATE = "2026-09-12T01:30:00+08:00"

GATES = [
    {
        "event_id": "astra-life02-gate-gf0", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-F0", "scope": "F0", "verdict": "pending",
        "criteria": ("taxonomy exists; exactly 4 class ids; disjointness tests; 2 independent "
                     "reviewer verdicts. WITHHELD at canonical 565a6e505188: one accept on record "
                     "(lead-audit, conditional) and it is not enough without a second independent "
                     "verdict; F0 is dual-tree divergent (authoring 01e7f841643c unpublished); "
                     "2 class-separation soft flags await disposition."),
        "evidence_refs": ["research_map/formulation_taxonomy.yaml",
                          "artifacts/formulation/formulation_taxonomy.yaml",
                          "reviews/F0-review-lead-audit.json",
                          "reviews/A1-rebind-coverage.json",
                          "runtime/state/artifact_hashes.json"],
    },
    {
        "event_id": "astra-life02-gate-gform", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-FORM", "scope": "F1,F2a,F2b", "verdict": "pending",
        "criteria": ("three class schemas at canonical paths with exact quantifiers/topology/"
                     "regularity/genericity/I+/visibility/conclusion_type; no C0/C2 merge; 2 "
                     "independent accepts citing the measured sha256. WITHHELD at published "
                     "b65fcc0f0118 / 8dae50da1ab5 / a8d899d2941f: publication is aligned "
                     "(canonical == authoring == FROZEN rev20), but zero full-schema verdicts bind "
                     "to these hashes yet and one class-separation soft flag on F1 awaits disposition."),
        "evidence_refs": ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                          "schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/FROZEN.json",
                          "reviews/A1-rebind-coverage.json", "runtime/state/artifact_hashes.json"],
    },
    {
        "event_id": "astra-life02-gate-glit", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-LIT", "scope": "L0,L1", "verdict": "pending",
        "criteria": ("ledger rows have resolvable locators; verification_status honest; >=3 "
                     "independent re-fetch spot checks; unresolved marked unresolved. WITHHELD: L0 "
                     "at ce42d205e761 carries three revise verdicts and no accept at that hash; L1 "
                     "at 315c19145065 has one current spot check (flash-07) and needs two more "
                     "independent ones."),
        "evidence_refs": ["ledger/theorems.jsonl", "ledger/citation_audit.csv",
                          "artifacts/worker-07/l1_spotcheck/spotcheck-l1-07.json",
                          "reviews/L0-review-17.json", "reviews/A1-rebind-coverage.json"],
    },
    {
        "event_id": "astra-life02-gate-gnum", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-NUM", "scope": "N0", "verdict": "pending",
        "criteria": ("flat-space convergence order measured AND independently replicated within "
                     "tolerance; protocol reviewed; lock guard passes. WITHHELD: the lead N0 "
                     "proposal is pass_conditional with C1-C7 on artifact-backed evidence and C8 "
                     "unmet -- reviews/G-NUM-protocol-review.json binds 01b2072434cd while the "
                     "protocol is at 3345e17d2be3 rev2; replication verdict remains PROVISIONAL."),
        "evidence_refs": ["artifacts/numerics/n0/n0_gate_proposal_lead.json",
                          "numerics/tests/n0_gate_proposal.json",
                          "numerics/CONVERGENCE_PROTOCOL.md",
                          "reviews/G-NUM-protocol-review.json",
                          "numerics/tests/selfgravity_lock_guard.py"],
    },
    {
        "event_id": "astra-life02-gate-gaudit", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-AUDIT", "scope": "A0,A1", "verdict": "pending",
        "criteria": ("rubric exists without a universal scalar score; A1 has 2 independent "
                     "verdicts per target with cited sha256. WITHHELD: A1-rebind-coverage at "
                     "00:11:39 shows 0 independent full-schema verdicts at the measured canonical "
                     "hashes for F0/F1/F2a/F2b/L0; F2b soft flags disposed, F0/F1 flags open; "
                     "future-dated event timestamps (CF-14) remain unadjudicated."),
        "evidence_refs": ["evaluation_rubric.yaml", "reviews/A1-rebind-coverage.json",
                          "reviews/F2b-softflag-disposition-review.json",
                          "runtime/state/artifact_hashes.json"],
    },
]

ASSIGNMENTS = [
    {
        "event_id": "astra-life02-publish-f0", "event_type": "assignment", "actor": "astra",
        "created_at": NOW, "node_id": "F0", "assignee": "astra-lead-formulation",
        "artifact": "research_map/formulation_taxonomy.yaml",
        "gate": "G-F0", "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "evidence_refs": ["research_map/formulation_taxonomy.yaml",
                          "artifacts/formulation/formulation_taxonomy.yaml",
                          "artifacts/formulation/FROZEN.json",
                          "reviews/F0-review-lead-audit.json",
                          "runtime/state/artifact_hashes.json"],
        "acceptance": ("Narrow successor to astra-life01-publish-frozen (F1/F2a/F2b landed "
                       "byte-identically at 00:10:15). For F0 only: publish ONE frozen revision so "
                       "that research_map/formulation_taxonomy.yaml and "
                       "artifacts/formulation/formulation_taxonomy.yaml are byte-identical, and so "
                       "FROZEN.json carries a single sha256 for that logical artifact (mirror entry "
                       "equal to it). Re-emit the canonical artifact event with the canonical "
                       "sha256 and stamp frozen_at with wall-clock. Acceptance test: "
                       "`python3 research_map/audit_evidence.py` reports 0 dual-tree divergence "
                       "findings; if the accepted canonical 565a6e505188 is superseded, say so "
                       "explicitly so the F0 accept can be re-reviewed at the new hash."),
        "budget_agent_hours": 1.0,
        "expected_information_gain": ("Removes the last publication divergence; G-F0 then needs "
                                      "only a second independent accept at a stable hash."),
        "falsifier": ("Any remaining canonical/authoring byte difference, two different hashes for "
                      "one logical artifact in FROZEN.json, or a frozen_at later than write time."),
        "stop_rule": ("1 agent-hour or 2 revision bumps; never hand-merge canonical and authoring "
                      "bytes -- publish one over the other."),
        "deadline": DEADLINE_EARLY,
        "controller_note": ("FORM-MAP-PATCH-002 stays superseded: do not repoint map paths at the "
                            "authoring tree. Canonical is authoritative and reviewers bind there. "
                            "The F0 accept on record cites 565a6e505188 and is conditional on a "
                            "second verdict."),
    },
    {
        "event_id": "astra-life02-softflag-f0f1", "event_type": "assignment", "actor": "astra",
        "created_at": NOW, "node_id": "A1", "assignee": "astra-lead-audit",
        "artifact": "reviews/A1-rebind-coverage.json",
        "gate": "G-AUDIT", "class_id": "GLOBAL",
        "evidence_refs": ["reviews/F2b-softflag-disposition-review.json",
                          "schemas/af_wcc_vacuum.yaml",
                          "research_map/formulation_taxonomy.yaml",
                          "runtime/bin/classsep_regression.py"],
        "acceptance": ("Extend the F2b soft-flag disposition method to the two remaining flagged "
                       "revisions: F0 canonical 565a6e505188 (AF-WCC-VAC-GEN-SET, AF-SCC-C0-CH-VAC) "
                       "and F1 canonical b65fcc0f0118 (AF-WCC-VAC-GEN-SET, unless F0/F1 are "
                       "republished first, in which case dispose at the republished hashes). For "
                       "each: either calibrate the checker to the candidate/variant annotation, or "
                       "record a documented blind spot with the checker regression numbers; state "
                       "the scope limit and do not count it as a full-schema verdict."),
        "budget_agent_hours": 1.5,
        "expected_information_gain": ("Clears the last class-separation soft flags so G-FORM/G-AUDIT "
                                      "reasons reduce to verdict rebinding alone."),
        "falsifier": ("A soft flag left without disposition, or a disposition that claims proof of "
                      "absence beyond the checker's measured sensitivity."),
        "stop_rule": ("1.5 agent-hours; no new checker corpus beyond the standing 27-case regression."),
        "deadline": DEADLINE_EARLY,
        "controller_note": ("Successor to the F2b disposition, not a duplicate of "
                            "astra-life01-a1-rebind: this covers only the F0/F1 flags. The full "
                            "per-target verdict rebinding stays with astra-life01-a1-rebind."),
    },
    {
        "event_id": "astra-life02-n0-c8", "event_type": "assignment", "actor": "astra",
        "created_at": NOW, "node_id": "N0", "assignee": "astra-lead-audit",
        "artifact": "reviews/G-NUM-protocol-review.json",
        "gate": "G-NUM", "class_id": "AF-WCC-SCALAR-SPH",
        "evidence_refs": ["numerics/CONVERGENCE_PROTOCOL.md",
                          "artifacts/numerics/n0/n0_gate_proposal_lead.json",
                          "reviews/G-NUM-protocol-review.json",
                          "numerics/tests/flat_wave_replication.py"],
        "acceptance": ("Re-issue astra-n0add-02 at the current protocol revision: an independent "
                       "verdict (accept|revise|reject) on numerics/CONVERGENCE_PROTOCOL.md pinned "
                       "to sha256 3345e17d2be3, citing the scheme-appropriate invariant functional, "
                       "resolution-aware drift criterion, order fit with uncertainty, and negative "
                       "controls. This is criterion C8 of the lead N0 gate proposal; the recorded "
                       "verdict binds the stale hash 01b2072434cd and cannot count."),
        "budget_agent_hours": 1.0,
        "expected_information_gain": ("Closes the single unmet criterion of the N0 proposal so "
                                      "G-NUM can be adjudicated on measured convergence."),
        "falsifier": ("A verdict whose cited sha256 is not 3345e17d2be3, or one that re-uses the "
                      "stale review without re-checking the protocol."),
        "stop_rule": ("1 agent-hour. A revise verdict with a concrete defect is an acceptable "
                      "outcome; do not pass the protocol to unblock numerics."),
        "deadline": DEADLINE_LATE,
        "controller_note": ("G-NUM passing would certify N0 only. N1 stays locked until G-FORM and "
                            "G-AUDIT also pass and the N0 order is measured and independently "
                            "replicated. No self-gravitating code may be written."),
    },
    {
        "event_id": "astra-life02-n0-c8-refresh", "event_type": "assignment", "actor": "astra",
        "created_at": NOW, "node_id": "N0", "assignee": "astra-lead-audit",
        "artifact": "reviews/G-NUM-protocol-review.json",
        "gate": "G-NUM", "class_id": "AF-WCC-SCALAR-SPH",
        "evidence_refs": ["numerics/CONVERGENCE_PROTOCOL.md",
                          "reviews/G-NUM-protocol-review.json",
                          "artifacts/numerics/n0/n0_gate_proposal_lead.json"],
        "acceptance": ("Moving-target refresh of astra-life02-n0-c8: numerics/CONVERGENCE_PROTOCOL.md "
                       "was revised to revision 3 (measured 1e6cdf04d7a2 at 00:15:51) after that "
                       "assignment was written. Re-issue the C8 verdict against the protocol hash "
                       "measured at review time; as of issue that is 1e6cdf04d7a2. If the protocol "
                       "changes again while you review, stop and report a moving-target blocker "
                       "instead of binding a stale hash. Same artifact and owner as astra-n0add-02 "
                       "and astra-life02-n0-c8."),
        "budget_agent_hours": 1.0,
        "expected_information_gain": ("Closes C8 against the current protocol revision, not a "
                                      "superseded pin."),
        "falsifier": ("A verdict citing 3345e17d2be3 or 01b2072434cd as the reviewed revision, or a "
                      "review that does not re-measure the protocol hash."),
        "stop_rule": "1 agent-hour; a revise verdict with concrete defects is acceptable.",
        "deadline": DEADLINE_LATE,
        "controller_note": ("Supersedes the hash pin in astra-life02-n0-c8; criterion C8 itself is "
                            "unchanged. G-NUM passing still does not release N1."),
    },
    {
        "event_id": "astra-life02-l1-spotcheck", "event_type": "assignment", "actor": "astra",
        "created_at": NOW, "node_id": "L1", "assignee": "astra-lead-literature",
        "artifact": "ledger/citation_audit.csv",
        "gate": "G-LIT", "class_id": "GLOBAL",
        "evidence_refs": ["ledger/citation_audit.csv",
                          "artifacts/worker-07/l1_spotcheck/spotcheck-l1-07.json",
                          "reviews/L1-spotcheck-10.json", "reviews/L1-spotcheck-11.json"],
        "acceptance": ("Two further independent re-fetch spot checks binding L1 sha256 "
                       "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9, by "
                       "reviewers distinct from deepseek-flash-07 and from each other: each records "
                       "the fetched source hash, the comparison verdict (MATCH/PARTIAL/FAIL), the "
                       "locator, and re-hashes the ledger after the fetch. Two more checks bring "
                       "the current-hash total to three (the required >=3)."),
        "budget_agent_hours": 1.5,
        "expected_information_gain": ("Completes the L1 criterion independently of the L0 revision, "
                                      "so G-LIT reduces to the L0 accept at its next revision."),
        "falsifier": ("A spot check whose ledger hash is not 315c19145065, or two checks by the "
                      "same reviewer, or a check without a fetched-source hash."),
        "stop_rule": ("1.5 agent-hours; do not re-fetch sources outside the frozen 95-source scope."),
        "deadline": DEADLINE_LATE,
        "controller_note": ("Distinct from astra-life01-l0-revise (theorems.jsonl): this touches "
                            "only the citation ledger and does not collide with it."),
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
    for ev in GATES + ASSIGNMENTS:
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
