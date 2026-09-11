"""Controller event emission for the astra-lifecycle-01 pass (idempotent).

Appends hash-bound gate verdicts and four bounded assignments to the accepted
event stream via comms.append_event, and mirrors each assignment into the
assignee's downward inbox. Re-running is safe: duplicate event_ids are ignored.

  python3 research_map/astra_lifecycle_events.py
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
DEADLINE = "2026-09-12T01:30:00+08:00"

GATES = [
    {
        "event_id": "astra-life01-gate-gf0", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-F0", "scope": "F0", "verdict": "pending",
        "criteria": ("formulation_taxonomy.yaml exists; exactly 4 separate class ids; disjointness "
                     "tests; 2 independent reviewer verdicts. WITHHELD: the canonical taxonomy was "
                     "revised after every verdict on record and no accept binds to the measured "
                     "canonical sha256."),
        "evidence_refs": ["research_map/formulation_taxonomy.yaml",
                          "reviews/F0-review-17.json", "reviews/F0-review-19.json",
                          "artifacts/formulation/FROZEN.json",
                          "runtime/state/artifact_hashes.json"],
    },
    {
        "event_id": "astra-life01-gate-gform", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-FORM", "scope": "F1,F2a,F2b", "verdict": "pending",
        "criteria": ("all three class schemas exist at canonical paths with exact quantifiers/"
                     "topology/regularity/genericity/I+/visibility/conclusion_type; no C0/C2 merge; "
                     "2 independent accepts with cited sha256. WITHHELD: canonical/authoring "
                     "publication divergence plus only revise verdicts at current canonical hashes."),
        "evidence_refs": ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                          "schemas/af_scc_c0_vacuum.yaml",
                          "artifacts/formulation/proposals/map_patch_F0_F1_F2.json",
                          "runtime/state/artifact_hashes.json"],
    },
    {
        "event_id": "astra-life01-gate-glit", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-LIT", "scope": "L0,L1", "verdict": "pending",
        "criteria": ("ledger rows have resolvable locators; verification_status honest; >=3 "
                     "independent re-fetch spot checks; unresolved marked unresolved. WITHHELD: L0 "
                     "has three revise verdicts and no accept at the current ledger hash; the audit "
                     "still flags a non-frozen class token in the ledger."),
        "evidence_refs": ["ledger/theorems.jsonl", "ledger/citation_audit.csv",
                          "reviews/L0-review-17.json", "reviews/L0-review-lead-audit.json",
                          "runtime/state/artifact_hashes.json"],
    },
    {
        "event_id": "astra-life01-gate-gnum", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-NUM", "scope": "N0", "verdict": "pending",
        "criteria": ("flat-space convergence order measured AND independently replicated within "
                     "tolerance; protocol reviewed; lock guard passes. WITHHELD: the replication "
                     "verdict on disk is PROVISIONAL; awaiting the hash-pinned N0 gate proposal."),
        "evidence_refs": ["numerics/tests/flat_wave.py", "numerics/tests/flat_wave_replication.py",
                          "numerics/protocol/fixed_replication_verdict.json",
                          "numerics/protocol/scheme_independence_review.md",
                          "numerics/tests/selfgravity_lock_guard.py"],
    },
    {
        "event_id": "astra-life01-gate-gaudit", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-AUDIT", "scope": "A0,A1", "verdict": "pending",
        "criteria": ("evaluation_rubric.yaml exists without a universal scalar score; A1 has 2 "
                     "independent verdicts per formulation/literature target with cited sha256. "
                     "WITHHELD: A1 verdicts do not yet bind to the current canonical hashes; two "
                     "class-separation soft flags on F2b await disposition."),
        "evidence_refs": ["evaluation_rubric.yaml", "reviews/",
                          "schemas/af_scc_c0_vacuum.yaml", "runtime/state/artifact_hashes.json"],
    },
]

ASSIGNMENTS = [
    {
        "event_id": "astra-life01-publish-frozen", "event_type": "assignment", "actor": "astra",
        "created_at": NOW, "node_id": "F1", "assignee": "astra-lead-formulation",
        "artifact": ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                     "schemas/af_scc_c0_vacuum.yaml", "research_map/formulation_taxonomy.yaml"],
        "gate": "G-FORM", "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "evidence_refs": ["artifacts/formulation/FROZEN.json",
                          "artifacts/formulation/proposals/map_patch_F0_F1_F2.json",
                          "runtime/state/artifact_hashes.json",
                          "research_map/audit_evidence.py:121-135"],
        "acceptance": ("Publish the FROZEN revision byte-identically to the four canonical paths; "
                       "re-emit one artifact event per canonical path with the canonical sha256; "
                       "reconcile artifacts/formulation/FROZEN.json so "
                       "`python3 artifacts/formulation/tools/verify_frozen.py` exits 0 against the "
                       "canonical hashes. Acceptance test: `python3 research_map/audit_evidence.py` "
                       "reports 0 dual-tree divergence findings."),
        "budget_agent_hours": 2.0,
        "expected_information_gain": ("Unblocks G-F0/G-FORM: reviewers can bind verdicts to stable "
                                      "canonical bytes instead of superseded drafts."),
        "falsifier": ("Any canonical file whose bytes differ from the frozen manifest hash, or a "
                      "FROZEN.json revision that lists an authoring-only path as canonical."),
        "stop_rule": ("2 agent-hours or 3 revision bumps. If a revision changes mid-publication, "
                      "re-freeze and restart the whole publication; never hand-merge."),
        "deadline": DEADLINE,
        "controller_note": ("Canonical-path policy (controller decision, 2026-09-12): the canonical "
                            "path is authoritative (schemas/*.yaml, research_map/formulation_taxonomy.yaml); "
                            "artifacts/formulation/** is the authoring tree and must be published "
                            "byte-identically before review verdicts bind. FORM-MAP-PATCH-002 is "
                            "superseded: do not repoint the map at the authoring tree."),
    },
    {
        "event_id": "astra-life01-a1-rebind", "event_type": "assignment", "actor": "astra",
        "created_at": NOW, "node_id": "A1", "assignee": "astra-lead-audit",
        "artifact": ["reviews/"],
        "gate": "G-AUDIT", "class_id": "GLOBAL",
        "evidence_refs": ["reviews/F0-review-17.json", "reviews/F1-review-16.json",
                          "reviews/F2a-review-18.json", "reviews/F2b-review-18.json",
                          "reviews/L0-review-17.json", "evaluation_rubric.yaml"],
        "acceptance": ("After PUBLISH-FROZEN-01 lands, provide for each target F0, F1, F2a, F2b, L0 "
                       "at least two verdicts from distinct reviewers who did not author the "
                       "artifact, each citing the measured canonical sha256 (path#sha256-prefix). "
                       "Re-check A0 conformance at the rubric hash. Dispose of the two class-separation "
                       "soft flags on F2b (candidate-variant tokens at schemas/af_scc_c0_vacuum.yaml:316-317) "
                       "by checker calibration or a documented blind spot."),
        "budget_agent_hours": 3.0,
        "expected_information_gain": ("Turns A1 from aggregate prose into per-target, hash-bound "
                                      "acceptance evidence sufficient for G-AUDIT/G-FORM."),
        "falsifier": ("Any verdict whose cited sha256 does not equal the measured canonical sha256, or "
                      "two verdicts on one target from the same reviewer."),
        "stop_rule": ("3 agent-hours; do not open new review targets beyond F0/F1/F2a/F2b/L0/A0."),
        "deadline": DEADLINE,
        "controller_note": ("Verdicts at superseded hashes (7a3e1f93, 23fec0e9, e6b1af2b, 66bf917b, "
                            "5fb8bf3a) are advisory only and cannot be counted."),
    },
    {
        "event_id": "astra-life01-l0-revise", "event_type": "assignment", "actor": "astra",
        "created_at": NOW, "node_id": "L0", "assignee": "astra-lead-literature",
        "artifact": "ledger/theorems.jsonl",
        "gate": "G-LIT", "class_id": "GLOBAL",
        "evidence_refs": ["ledger/theorems.jsonl", "reviews/L0-review-17.json",
                          "reviews/L0-review-lead-audit.json", "reviews/L0-review-16.json",
                          "runtime/state/artifact_hashes.json"],
        "acceptance": ("New L0 revision at the canonical path addressing the three revise verdicts "
                       "(lead-audit 3.0, flash-16 3.5, flash-17 2.5): every class_ids token is one of "
                       "the frozen four or is explicitly tagged as a non-class ledger tag; every "
                       "unresolved citation is marked unresolved with what would resolve it; and >=3 "
                       "independent re-fetch spot checks bind to the new ledger hash."),
        "budget_agent_hours": 3.0,
        "expected_information_gain": ("Removes the last tooling-visible class-token violation in the "
                                      "ledger and makes G-LIT judgeable at one hash."),
        "falsifier": ("audit_evidence.py still reports CLASSSEP-SOFT extension tokens in L0, or any "
                      "row whose verification_status overstates its locator evidence."),
        "stop_rule": ("3 agent-hours; no new sources beyond the frozen 95-source scope."),
        "deadline": DEADLINE,
        "controller_note": ("L0's last status summary claims '4-class compliant with 0 extension "
                            "tokens'; the audit contradicts it. Fix the artifact, not the summary."),
    },
    {
        "event_id": "astra-life01-n0-proposal", "event_type": "assignment", "actor": "astra",
        "created_at": NOW, "node_id": "N0", "assignee": "astra-lead-numerics",
        "artifact": "numerics/tests/n0_gate_proposal.json",
        "gate": "G-NUM", "class_id": "AF-WCC-SCALAR-SPH",
        "evidence_refs": ["numerics/tests/flat_wave.py", "numerics/tests/flat_wave_replication.py",
                          "numerics/protocol/fixed_replication_verdict.json",
                          "numerics/protocol/scheme_independence_review.md",
                          "numerics/tests/replication_triage.md",
                          "numerics/tests/selfgravity_lock_guard.py"],
        "acceptance": ("Hash-pinned n0_gate_proposal.json integrating the flash-13 triage, the "
                       "flash-14 scheme-independence review and the PROVISIONAL fixed replication "
                       "verdict into a measured order + replication tolerance claim. State explicitly "
                       "which scheme's order is being certified and which invariant functional was "
                       "used. Lock guard must pass and no N1+ artifact may exist."),
        "budget_agent_hours": 2.0,
        "expected_information_gain": ("Lets Astra adjudicate G-NUM on measured convergence rather "
                                      "than on scheme-dependent harness numbers."),
        "falsifier": ("Any numerics/spherical_solver file, any N1 node moved to active, or an order "
                      "claim not backed by a run artifact whose sha256 is recorded."),
        "stop_rule": ("2 agent-hours. If the two schemes cannot agree within the stated tolerance, "
                      "propose a fail with the disagreement quantified; do not lower the tolerance."),
        "deadline": DEADLINE,
        "controller_note": ("numerics_lock stays LOCKED regardless of this proposal; only G-FORM + "
                            "G-AUDIT pass plus measured+replicated N0 order releases N1."),
    },
]


def main():
    for ev in GATES + ASSIGNMENTS:
        res = comms.append_event(ev)
        print(("APPENDED " if res.get("accepted") else "SKIPPED  ") + ev["event_id"] + " " + ev["event_type"])
    for a in ASSIGNMENTS:
        msg = {k: v for k, v in a.items()}
        msg["to"] = a["assignee"]
        msg["event_type"] = "assignment"
        path = comms.send(a["assignee"], msg)
        print(f"INBOX    {path.relative_to(ROOT)} <- {a['event_id']}")


if __name__ == "__main__":
    main()
