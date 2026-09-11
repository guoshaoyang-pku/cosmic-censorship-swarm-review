"""Controller event emission for the astra-lifecycle-04 pass (idempotent).

Emits hash-bound gate records, bounded assignments and one decision-record notice
for the FROZEN rev27 pins. Re-running is safe: duplicate event_ids are ignored and
already-sent inbox cards are skipped.

CF-12 rule respected: every assignment names output paths that no other open
assignment names, and each successor explicitly supersedes its stale predecessor.

Numerics: no N1 work and no solver. The two numerics assignments are N0-only
(flat space, lock-compatible); numerics_lock stays LOCKED.

  python3 research_map/astra_lifecycle_04_events.py
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

F0_H = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
F0_SUP_H = "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"
F1_H = "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"
F2A_H = "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce"
F2B_H = "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"
L0_H = "3e3d35531421388a17ca7bad7f6c7093dd1cc21a3a808ca8ff65ce6c2b79c6a6"
L1_H = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
A0_H = "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885"
PROTO_H = "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274"
DECISIONS = "runtime/state/controller_verification/astra-lifecycle-04-decisions.json"

GATES = [
    {
        "event_id": "astra-life04-gate-gf0", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-F0", "scope": "F0", "verdict": "pending",
        "criteria": (
            "Declared F0 taxonomy exists at the canonical path; exactly the four frozen class ids; "
            "disjointness tests; two independent reviewer verdicts at the measured hash. Measured "
            "declared F0 rev5 " + F0_H[:12] + " with companion supplement " + F0_SUP_H[:12] + " "
            "(REC-3: distinct artifacts, byte-identity not required). Review scan at this hash: "
            "zero accepts (verdicts at 276009f4/565a6e50/0fcc6a19 are void). WITHHELD pending two "
            "independent accepts at " + F0_H[:12] + "."
        ),
        "evidence_refs": ["research_map/formulation_taxonomy.yaml",
                          "artifacts/formulation/formulation_taxonomy.yaml",
                          "artifacts/formulation/FROZEN.json",
                          "runtime/state/controller_verification/astra-lifecycle-04-decisions.json",
                          "research_map/research_map.json#controller_gate_audit"],
    },
    {
        "event_id": "astra-life04-gate-gform", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-FORM", "scope": "F1,F2a,F2b", "verdict": "pending",
        "criteria": (
            "Three separate class schemas at canonical paths with exact quantifiers/topology/"
            "regularity/genericity/I+/visibility/conclusion_type; no C0/C2 merge; two independent "
            "accepts per class citing the measured sha256. Measured and mirror-aligned at FROZEN "
            "rev27: F1 " + F1_H[:12] + ", F2a " + F2A_H[:12] + ", F2b " + F2B_H[:12] + ". The rev27 "
            "closure repaired the duplicate revised_at keys, repointed class_contract_pointer at the "
            "canonical taxonomy, retyped D0 and defined AF_{I+}; every verdict at rev11 is void. "
            "Zero accepts at the rev12 hashes. WITHHELD pending two independent accepts per class."
        ),
        "evidence_refs": ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                          "schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/FROZEN.json",
                          "artifacts/formulation/evidence/close_findings_rev27_report.json",
                          "research_map/research_map.json#controller_gate_audit"],
    },
    {
        "event_id": "astra-life04-gate-glit", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-LIT", "scope": "L0,L1", "verdict": "pending",
        "criteria": (
            "Ledger rows carry resolvable locators (evidence_url is the locator column, REC-6); "
            "verification_status honest; >=3 independent re-fetch spot checks at the measured L1 "
            "hash; unresolved citations marked unresolved; two independent verdicts. Measured L0 rev3 "
            + L0_H[:12] + " (zero accepts; prior verdicts bound ce42d205 and are void) and L1 "
            + L1_H[:12] + " (22 independent spot checks bind, requirement met; L1 bytes unchanged). "
            "REC-4: rev-4 metadata patch only after verdicts. REC-5: abstract-level evidence is "
            "sufficient if honestly marked; T-101/T-102 stay provisional."
        ),
        "evidence_refs": ["ledger/theorems.jsonl", "ledger/citation_audit.csv",
                          "reviews/L1-spotcheck-09.json", "reviews/L0-review-18-current.json",
                          "runtime/state/controller_verification/astra-lifecycle-04-decisions.json"],
    },
    {
        "event_id": "astra-life04-gate-gnum", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-NUM", "scope": "N0", "verdict": "pending",
        "criteria": (
            "Flat-space convergence order measured AND independently replicated within tolerance; "
            "protocol reviewed (C8); lock guard passes. C8 is MET: reviews/G-NUM-protocol-review.json "
            "verdict accept 4.5 binds protocol " + PROTO_H[:12] + ". C4 registration is repaired "
            "(registry includes runtime/state/controller_verification). STILL PENDING: the N0 node "
            "verdict at the measured hashes does not exist - reviews/N0-review-lead-audit.json is "
            "revise 3.5 with open stop-rule items (4th resolution or explicit 3-level scoping, F0 "
            "re-bind, one independent replication verdict). numerics_lock stays LOCKED; G-NUM passing "
            "would certify N0 only and would not release N1 (which additionally requires G-FORM and "
            "G-AUDIT)."
        ),
        "evidence_refs": ["reviews/G-NUM-protocol-review.json",
                          "reviews/N0-review-lead-audit.json",
                          "numerics/CONVERGENCE_PROTOCOL.md",
                          "numerics/tests/selfgravity_lock_guard.py",
                          "research_map/research_map.json#numerics_lock"],
    },
    {
        "event_id": "astra-life04-gate-gaudit", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-AUDIT", "scope": "A0,A1", "verdict": "pending",
        "criteria": (
            "evaluation_rubric.yaml exists without a universal scalar score; A1 has 2 independent "
            "verdicts per formulation/literature target with cited sha256. Measured A0 rubric "
            + A0_H[:12] + " has zero accepts (three revises with hash-bound findings). A1 coverage at "
            "the measured target hashes: F0 0, F1 0, F2a 0, F2b 0, L0 1 (need >=2 each). CLASSSEP "
            "hard findings on claims[36,94,96,97,101,112,127] are metalinguistic mentions of the "
            "merged-case probes and repeat the CF-16 false-positive pattern; the audit lead's "
            "checker calibration is the assigned disposition path."
        ),
        "evidence_refs": ["evaluation_rubric.yaml", "reviews/A1-rebind-coverage.json",
                          "reviews/A0-review-lead-audit.json",
                          "artifacts/worker-002/review-ess/",
                          "research_map/class_separation.py"],
    },
]

ASSIGNMENTS = [
    {
        "event_id": "astra-life04-freeze-hold", "event_type": "assignment", "actor": "astra",
        "created_at": NOW, "node_id": "F0,F1,F2a,F2b", "assignee": "astra-lead-formulation",
        "artifact": ["artifacts/formulation/FROZEN.json", "schemas/af_wcc_vacuum.yaml",
                     "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml",
                     "research_map/formulation_taxonomy.yaml"],
        "gate": "G-FORM", "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "evidence_refs": ["artifacts/formulation/FROZEN.json",
                          "artifacts/formulation/evidence/close_findings_rev27_report.json",
                          "artifacts/formulation/evidence/f0_mirror_conflict.json",
                          "runtime/state/controller_verification/astra-lifecycle-04-decisions.json"],
        "acceptance": (
            "SUPERSEDES astra-life03-close-findings (its rev27 repair landed) and closes "
            "astra-life01-publish-frozen / astra-life02-publish-f0 (REC-3: the F0 pair is a companion "
            "pair; byte-identical publication is impossible and no longer required). Confirm the "
            "FROZEN rev27 pin set - F1 " + F1_H[:12] + ", F2a " + F2A_H[:12] + ", F2b " + F2B_H[:12] +
            ", declared F0 " + F0_H[:12] + ", supplement " + F0_SUP_H[:12] + " - by (1) emitting the "
            "missing artifact events for these five canonical paths with the FROZEN hashes and "
            "wall-clock timestamps, (2) reconciling the map's declared artifact_sha256 fields with "
            "those hashes, and (3) then HOLDING: no byte changes to the five paths until the review "
            "round completes. No semantic edits, no new class ids."
        ),
        "budget_agent_hours": 0.5,
        "expected_information_gain": (
            "Makes the rev27 bytes bindable: without an artifact event the map still declares rev11 "
            "hashes, so no reviewer verdict can be recorded against the frozen revision."),
        "falsifier": (
            "Any byte change to the five paths after the events are emitted, a FROZEN pin that does "
            "not equal the measured disk hash, or a declared hash left at rev11."),
        "stop_rule": (
            "0.5 agent-hours or one event-emission pass, whichever is first. If a semantic defect is "
            "found, report it as a blocker instead of editing."),
        "deadline": "2026-09-12T01:15:00+08:00",
        "controller_note": (
            "This is an announce-and-hold card, not an authoring card. Reviewers are dispatched in "
            "parallel on the same pins (astra-life04-verify-gform-r2 / -gf0-r2)."),
    },
    {
        "event_id": "astra-life04-verify-gform-r2", "event_type": "assignment", "actor": "astra",
        "created_at": NOW, "node_id": "F1,F2a,F2b", "assignee": "astra-lead-audit",
        "artifact": "reviews/G-FORM-final-verify-r2.json", "gate": "G-FORM",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "evidence_refs": ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                          "schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/FROZEN.json",
                          "artifacts/formulation/evidence/close_findings_rev27_report.json"],
        "acceptance": (
            "SUPERSEDES astra-life03-verify-gform (pinned to rev25, now void) and astra-life01-a1-rebind "
            "for these targets. Dispatch two independent blind reviewers per class at the FROZEN rev27 "
            "pins F1 " + F1_H[:12] + " / F2a " + F2A_H[:12] + " / F2b " + F2B_H[:12] + ", each "
            "returning accept|revise|reject with a cited sha256 and hash-bound hard failures. "
            "Reviewers must not edit the schemas. Adjudicate into reviews/G-FORM-final-verify-r2.json "
            "with the coverage table and the same-hash test: a verdict counts only if the measured "
            "hash is unchanged when the second verdict lands."
        ),
        "budget_agent_hours": 3.0,
        "expected_information_gain": (
            "Two independent accepts per class at one frozen hash is the exact G-FORM criterion; "
            "the rev12 repair has had no independent read yet."),
        "falsifier": (
            "A verdict citing rev11 or any hash other than the FROZEN rev27 pin; an accept that "
            "ignores a named hard finding still visible at that hash; a schema write during the round."),
        "stop_rule": (
            "3 agent-hours or two verdicts per class, whichever is first. If a pin moves, stop and "
            "report a moving-target blocker rather than re-reviewing."),
        "deadline": "2026-09-12T02:15:00+08:00",
    },
    {
        "event_id": "astra-life04-verify-gf0-r2", "event_type": "assignment", "actor": "astra",
        "created_at": NOW, "node_id": "F0", "assignee": "astra-lead-audit",
        "artifact": "reviews/G-F0-final-verify-r2.json", "gate": "G-F0",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
        "evidence_refs": ["research_map/formulation_taxonomy.yaml",
                          "artifacts/formulation/formulation_taxonomy.yaml",
                          "artifacts/formulation/evidence/taxonomy_consistency.json",
                          "artifacts/formulation/FROZEN.json"],
        "acceptance": (
            "SUPERSEDES astra-life03-verify-gf0 (pinned to 276009f4, now void). Dispatch two "
            "independent blind reviewers at declared F0 rev5 " + F0_H[:12] + " with the companion "
            "supplement " + F0_SUP_H[:12] + " recorded as such (REC-3). Acceptance covers the gate "
            "criteria (four separate class ids, disjointness tests) and the supplement consistency "
            "evidence; reviewers must not edit either file. Adjudicate into "
            "reviews/G-F0-final-verify-r2.json."
        ),
        "budget_agent_hours": 1.5,
        "expected_information_gain": (
            "G-F0 has had no verdict at the rev5 hash; the companion adjudication removes the "
            "false mirror-equality requirement."),
        "falsifier": (
            "A verdict pinned to 276009f4 / 565a6e50 / 0fcc6a19; a review that treats the supplement "
            "as a competing taxonomy; a fifth class id treated as frozen."),
        "stop_rule": "1.5 agent-hours or two verdicts; stop if the canonical hash moves.",
        "deadline": "2026-09-12T02:15:00+08:00",
    },
    {
        "event_id": "astra-life04-verify-l0-rev3", "event_type": "assignment", "actor": "astra",
        "created_at": NOW, "node_id": "L0", "assignee": "astra-lead-literature",
        "artifact": "reviews/L0-review-rev3-final.json", "gate": "G-LIT", "class_id": "GLOBAL",
        "evidence_refs": ["ledger/theorems.jsonl", "ledger/citation_audit.csv",
                          "artifacts/literature/reviews/L0-rev2-disposition.md",
                          "runtime/state/controller_verification/astra-lifecycle-04-decisions.json"],
        "acceptance": (
            "SUPERSEDES astra-life01-l0-revise (rev2 target) and re-points the already-approved "
            "lit-l3-20260912-010 3.0 agent-hours at the rev3 ledger " + L0_H[:12] + " (L1 citation "
            "audit " + L1_H[:12] + " unchanged; its 22 spot checks remain valid). Dispatch two "
            "independent blind reviewers, no ledger edits, each verdict citing the measured hash; "
            "adjudicate into reviews/L0-review-rev3-final.json. Controller rulings apply: REC-4 "
            "(no rev-4 patch before verdicts; after verdicts, one bounded metadata-only patch), "
            "REC-5 (abstract-level evidence is sufficient if honestly marked), REC-6 (evidence_url "
            "is the locator column)."
        ),
        "budget_agent_hours": 3.0,
        "expected_information_gain": (
            "Rev3 moved the L0 hash after rev2 verdicts; two accepts at rev3 is the remaining G-LIT "
            "criterion."),
        "falsifier": (
            "A ledger write during the round, a verdict without a cited sha256, an accept that "
            "overstates verification depth, or a rev-4 patch that changes a claim or class binding."),
        "stop_rule": (
            "3 agent-hours or two verdicts; if the hash moves, both verdicts are void and reviewers "
            "stop rather than chase."),
        "deadline": "2026-09-12T02:00:00+08:00",
    },
    {
        "event_id": "astra-life04-n0-stoprule", "event_type": "assignment", "actor": "astra",
        "created_at": NOW, "node_id": "N0", "assignee": "astra-lead-numerics",
        "artifact": "numerics/results/flat_wave_convergence_rev3.json", "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "evidence_refs": ["reviews/N0-review-lead-audit.json", "numerics/tests/flat_wave.py",
                          "numerics/CONVERGENCE_PROTOCOL.md",
                          "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json"],
        "acceptance": (
            "N0-ONLY (flat space; numerics_lock stays LOCKED; numerics/spherical_solver must remain "
            "absent). Close the N0 node review stop rule at the current hashes: (1) add a fourth "
            "resolution rung to the convergence study, or explicitly scope the claim to a 3-level "
            "observed order with a tolerance justification; (2) re-bind the class binding to declared "
            "F0 rev5 " + F0_H[:12] + "; (3) supply one independent replication verdict of the order "
            "at the frozen run hash. Report the order even if it degrades. No solver code, no N1."
        ),
        "budget_agent_hours": 2.0,
        "expected_information_gain": (
            "Converts the N0 revise verdict into judgeable evidence; N0 is the only numerics node "
            "allowed while locked."),
        "falsifier": (
            "Any file under numerics/spherical_solver, any N1 status change, or a convergence claim "
            "with fewer than four rungs and no explicit tolerance justification."),
        "stop_rule": "2 agent-hours; a named blocker with measured evidence is acceptable closure.",
        "deadline": "2026-09-12T02:30:00+08:00",
    },
    {
        "event_id": "astra-life04-n0-verify", "event_type": "assignment", "actor": "astra",
        "created_at": NOW, "node_id": "N0", "assignee": "astra-lead-audit",
        "artifact": "reviews/N0-review-final-verify.json", "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "evidence_refs": ["reviews/N0-review-lead-audit.json",
                          "numerics/results/flat_wave_convergence.json",
                          "numerics/results/flat_wave_replication.json",
                          "reviews/G-NUM-protocol-review.json"],
        "acceptance": (
            "SUPERSEDES reviews/N0-review-lead-audit.json (revise 3.5, pinned to superseded hashes) "
            "for G-NUM adjudication. One independent verdict at the post-stoprule N0 hashes, checking "
            "each stop-rule item and the lock guard; pin the reviewed hashes explicitly. N0-only: "
            "no solver, no N1, lock stays LOCKED."
        ),
        "budget_agent_hours": 1.0,
        "expected_information_gain": (
            "G-NUM needs an N0 node accept at one hash; C8 is already met at protocol " + PROTO_H[:12] + "."),
        "falsifier": (
            "A verdict at a stale hash, an accept that leaves a stop-rule item open, or any N1 "
            "artifact in the reviewed evidence."),
        "stop_rule": "1 agent-hour; a hash-bound revise is acceptable closure.",
        "deadline": "2026-09-12T03:00:00+08:00",
    },
    {
        "event_id": "astra-life04-verify-a0", "event_type": "assignment", "actor": "astra",
        "created_at": NOW, "node_id": "A0", "assignee": "astra-lead-audit",
        "artifact": "reviews/A0-review-final-verify.json", "gate": "G-AUDIT", "class_id": "GLOBAL",
        "evidence_refs": ["evaluation_rubric.yaml", "reviews/A0-review-lead-audit.json",
                          "reviews/A0-review-22.json"],
        "acceptance": (
            "One independent verdict at the measured A0 rubric " + A0_H[:12] + " (G-AUDIT criterion; "
            "the on-disk verdicts are three revises with hash-bound findings). The verdict must state "
            "whether each prior finding is resolved, unresolved, or out of scope, with a cited sha256. "
            "Do not edit evaluation_rubric.yaml."
        ),
        "budget_agent_hours": 1.0,
        "expected_information_gain": (
            "A0 has zero accepts at its measured hash; the rubric detector defects named by the audit "
            "lead need a disposition before G-AUDIT can be judged."),
        "falsifier": "A verdict without a cited hash, or a rubric edit during the round.",
        "stop_rule": "1 agent-hour; a hash-bound revise is acceptable closure.",
        "deadline": "2026-09-12T02:00:00+08:00",
    },
    {
        "event_id": "astra-life04-l0-freeze-reconcile", "event_type": "assignment", "actor": "astra",
        "created_at": NOW, "node_id": "L0", "assignee": "astra-lead-literature",
        "artifact": "reviews/L0-freeze-reconciliation.json", "gate": "G-LIT", "class_id": "GLOBAL",
        "evidence_refs": ["ledger/theorems.jsonl",
                          "artifacts/literature/archive/theorems.rev3-handpatch-20260912T003026.jsonl",
                          "artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl",
                          "artifacts/worker-073/l0_hf14_postrepair/report.json"],
        "acceptance": (
            "SUPERSEDES astra-life04-verify-l0-rev3 for the pin (that card's 3e3d3553 pin is void). "
            "The live ledger was rewritten at 00:35:19 to a1674f094979 after your L4 exit hash "
            "3e3d35531421, with no artifact event. As the canonical-path owner: (1) state whether the "
            "live bytes are yours; (2) if adopted, emit the artifact event for ledger/theorems.jsonl "
            "with the measured hash and a wall-clock timestamp and attach a content-preservation + "
            "claim-lowering diff against the rev-3 archive (the L0-rev3 repair invariants); (3) if "
            "not yours, publish the intended revision back from artifacts/literature/archive/ and "
            "report the unannounced write as an authority violation; (4) after either path, HOLD: no "
            "further ledger writes until two independent verdicts bind the reconciled hash. Record "
            "the reconciliation in reviews/L0-freeze-reconciliation.json."
        ),
        "budget_agent_hours": 0.5,
        "expected_information_gain": (
            "Restores one owned, announced, frozen L0 hash so the two-reviewer round has a stable "
            "target; without it every dispatch chases a moving ledger."),
        "falsifier": (
            "A second unannounced write, a reconciliation that cannot show claim-lowering/content "
            "preservation, or a verdict dispatched against an unfrozen hash."),
        "stop_rule": (
            "0.5 agent-hours or one reconciliation record. No claim edits; report a blocker rather "
            "than patching past a disagreement."),
        "deadline": "2026-09-12T01:30:00+08:00",
        "controller_note": (
            "CF-19. Reviewers are re-dispatched only after the reconcile hash is announced."),
    },
]

DECISION_NOTICES = [
    {
        "event_id": "astra-life04-decisions-recorded", "event_type": "status", "actor": "astra",
        "created_at": NOW, "node_id": "GLOBAL", "status": "active", "hours": 0.0,
        "summary": (
            "Pass-04 adjudications recorded in " + DECISIONS + ": REC-3 F0 pair is a companion pair, "
            "not a mirror (astra-life02-publish-f0 closed as impossible-as-written); REC-4/REC-5/REC-6 "
            "literature deferral, abstract-evidence sufficiency, and locator-column semantics; REC-7 "
            "numerics C4 registration repaired, C8 met, G-NUM pending on the N0 node verdict, lock "
            "stays LOCKED; REC-9 FROZEN rev27 pins (" + F1_H[:12] + "/" + F2A_H[:12] + "/" +
            F2B_H[:12] + "/" + F0_H[:12] + "/" + F0_SUP_H[:12] + ") are the review pins and any "
            "write voids verdicts. Tooling repairs shipped: colon-bearing resource-request ids bind "
            "in apply_events.py; publication_status supports companion pairs; the G-NUM gate reason "
            "reads the review's reviewed_sha256 and reports the N0 node verdict; the checkpoint "
            "registry covers runtime/state/controller_verification (C4). No gate verdict changed; "
            "no resource allocation beyond re-pointing the already-approved formulation/literature "
            "pools."
        ),
        "evidence_refs": [DECISIONS, "artifacts/formulation/FROZEN.json",
                          "reviews/G-NUM-protocol-review.json",
                          "research_map/research_map.json#controller_gate_audit"],
        "next_falsifier": (
            "Any gate verdict set without two independent accepts at one measured hash, or any "
            "solver/N1 artifact while numerics_lock is locked."),
    },
    {
        "event_id": "astra-life04-decisions-addendum-recl0", "event_type": "status", "actor": "astra",
        "created_at": NOW, "node_id": "L0", "status": "active", "hours": 0.0,
        "summary": (
            "REC-10 / CF-19: freeze breach on the canonical L0 ledger. The live file measured "
            "a1674f094979 (mtime 2026-09-12T00:35:19+08:00) after the literature lead's announced "
            "L4 exit hash 3e3d35531421 and with no artifact event in the accepted stream. The pin "
            "in astra-life04-verify-l0-rev3 is therefore VOID; astra-life04-l0-freeze-reconcile "
            "supersedes it and the verification round resumes only after the owner announces a "
            "reconciled, held hash. Prior L0 verdicts (worker-006 accept at 3e3d3553 and the "
            "ce42d205 round) remain void for binding."
        ),
        "evidence_refs": ["ledger/theorems.jsonl",
                          "artifacts/literature/archive/theorems.rev3-handpatch-20260912T003026.jsonl",
                          "artifacts/worker-073/l0_hf14_postrepair/report.json",
                          "runtime/state/controller_verification/astra-lifecycle-04-decisions.json"],
        "next_falsifier": (
            "A second unannounced ledger write, or a review verdict counted against a hash that was "
            "not announced by the owner."),
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
    for ev in GATES + ASSIGNMENTS + DECISION_NOTICES:
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
