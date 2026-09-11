"""Controller event emission for the astra-lifecycle-05 pass (idempotent).

Emits hash-bound gate records, bounded assignments, resource decisions and the
F0 gate-promotion events at the hashes measured on disk at run time. Re-running is
safe: duplicate event_ids are skipped by the accepted stream and already-sent inbox
cards are not re-sent.

Measured at emission (fail-closed if a pinned path is absent):
  F0 canonical 0abb9ed8a961 rev5 + companion supplement d7419b4e8963 (REC-3);
  F1/F2a/F2b cce9c60146d6 / 5476a3f2c6bc / 55d0a1ea9bda (rev12, FROZEN rev28);
  L0 a1674f094979 (owner-announced rev3-final build product, REC-10 closed);
  L1 315c19145065; A0 d748a9e3574e; protocol 1e6cdf04d7a2; gates.py fcd1d70991b6;
  N0 stop-rule deliverable numerics/results/flat_wave_convergence_rev3.json.

Rulings in this batch: G-F0 PASSES on four distinct accepts at one stable hash;
  G-FORM/G-LIT/G-NUM/G-AUDIT stay pending with refreshed hash-bound reasons.
  numerics_lock stays LOCKED; no N1 work and no solver anywhere in this pass.

  python3 research_map/astra_lifecycle_05_events.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research_map"))
import comms  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")


def measure(rel: str) -> str:
    p = ROOT / rel
    if not p.is_file():
        raise SystemExit(f"FAIL-CLOSED: pinned path absent: {rel}")
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


F0 = measure("research_map/formulation_taxonomy.yaml")
F0_SUP = measure("artifacts/formulation/formulation_taxonomy.yaml")
F1 = measure("schemas/af_wcc_vacuum.yaml")
F2A = measure("schemas/af_scc_c2_vacuum.yaml")
F2B = measure("schemas/af_scc_c0_vacuum.yaml")
FROZEN = measure("artifacts/formulation/FROZEN.json")
CASES = measure("schemas/taxonomy_cases.jsonl")
CONSIST = measure("artifacts/formulation/evidence/taxonomy_consistency.json")
L0 = measure("ledger/theorems.jsonl")
L1 = measure("ledger/citation_audit.csv")
A0 = measure("evaluation_rubric.yaml")
PROTO = measure("numerics/CONVERGENCE_PROTOCOL.md")
NGATES = measure("numerics/gates.py")
N0REV3 = measure("numerics/results/flat_wave_convergence_rev3.json")

DECISIONS = "runtime/state/controller_verification/astra-lifecycle-05-decisions.json"

# ---------------------------------------------------------------- gate records
GATES = [
    {
        "event_id": "astra-life05-gate-gf0", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-F0", "scope": "F0", "verdict": "pass",
        "criteria": (
            "Declared F0 taxonomy exists at the canonical path; exactly the four frozen class ids; "
            "disjointness tests; >=2 independent reviewer verdicts at one measured hash. MET at "
            "declared taxonomy " + F0[:12] + " (rev5, bytes stable since 00:31:41) with companion "
            "supplement " + F0_SUP[:12] + " (REC-3: distinct artifacts, byte-identity not required): "
            "4 distinct independent accepts at the hash - worker-025 (4.0), worker-038 (3.5), "
            "deepseek-flash-18 (4.0), deepseek-flash-19 (4.0); 6/6 disjointness pairs; FROZEN rev28 "
            + FROZEN[:12] + " verifies 44/44 listed files. Residuals recorded, NOT gate criteria: "
            "CF-20 case-corpus rows and the three schemas' consistency_evidence pin are stale -> "
            "astra-life05-evidence-binding-repair; CF-21 AF-WCC-SCALAR-SPH axes.genericity_kind is "
            "stale against its explicit comeager conclusion (3 reviewers non-blocking, 1 major) -> "
            "recorded, no F0 write. DIRECTIVE: canonical F0 bytes " + F0[:12] + " are frozen; any "
            "write to that path voids this verdict and requires fresh accepts at the new hash."
        ),
        "evidence_refs": [
            "research_map/formulation_taxonomy.yaml#" + F0[:12],
            "artifacts/formulation/formulation_taxonomy.yaml#" + F0_SUP[:12],
            "artifacts/formulation/FROZEN.json#" + FROZEN[:12],
            "reviews/F0-review-025.json#" + F0[:12],
            "reviews/F0-conformance-038-rev28.json#" + F0[:12],
            "reviews/F0-review-18.json#" + F0[:12],
            "reviews/F0-review-19.json#" + F0[:12],
            DECISIONS,
            "research_map/research_map.json#controller_gate_audit",
        ],
    },
    {
        "event_id": "astra-life05-gate-gform", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-FORM", "scope": "F1,F2a,F2b", "verdict": "pending",
        "criteria": (
            "F1/F2a/F2b exist with exact quantifiers/topology/regularity/genericity/I+/visibility/"
            "conclusion_type, no C0/C2 merge, and 2 independent accepts per class at one measured "
            "hash. Measured rev12 " + F1[:12] + " / " + F2A[:12] + " / " + F2B[:12] + ", all three "
            "mirror-aligned, FROZEN rev28. Coverage at these hashes: F1 1 accept (worker-088) vs 4 "
            "revise (090/040/053/088-amended); F2a 0 accepts (069/034/043 revise); F2b 1 accept "
            "(worker-098) with worker-096 hard failures and worker-044/095 binding blockers. Two "
            "reproducible evidence-binding defects at the frozen bytes: (a) schemas/taxonomy_cases.jsonl "
            "36/36 rows still bound to superseded 66bf917b; (b) all three schemas declare "
            "consistency_evidence_sha256 675a99d0 while live evidence is " + CONSIST[:12] + ". The "
            "schemas' own binding rule forbids a gate verdict until refreshed. WITHHELD pending "
            "astra-life05-evidence-binding-repair (rev13 + FROZEN rev29) and astra-life05-verify-gform-r3."
        ),
        "evidence_refs": [
            "schemas/af_wcc_vacuum.yaml#" + F1[:12],
            "schemas/af_scc_c2_vacuum.yaml#" + F2A[:12],
            "schemas/af_scc_c0_vacuum.yaml#" + F2B[:12],
            "schemas/taxonomy_cases.jsonl#" + CASES[:12],
            "artifacts/formulation/evidence/taxonomy_consistency.json#" + CONSIST[:12],
            "artifacts/formulation/FROZEN.json#" + FROZEN[:12],
            "reviews/closefind-verify-094.json#" + F0[:12],
            "artifacts/worker-095/f2b_rev12_binding_integrity/verdict.json",
            DECISIONS,
            "research_map/research_map.json#controller_gate_audit",
        ],
    },
    {
        "event_id": "astra-life05-gate-glit", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-LIT", "scope": "L0,L1", "verdict": "pending",
        "criteria": (
            "Ledger rows have resolvable locators and honest verification_status; >=3 independent "
            "re-fetch spot checks; unresolved marked unresolved; 2 independent accepts at one L0 "
            "hash. L0 measured " + L0[:12] + ": the owner announced these exact bytes as rev3 FINAL "
            "at 00:44 (build product of the repaired sources; REC-10/CF-19 freeze breach closed) - "
            "0 accepts at this hash (worker-093 revise; ce42d205 and 3e3d3553 verdicts are void). "
            "L1 " + L1[:12] + " unchanged with 23 independent spot checks (>=3 met). WITHHELD pending "
            "astra-life05-verify-l0-final: two blind accepts at " + L0[:12] + "."
        ),
        "evidence_refs": [
            "ledger/theorems.jsonl#" + L0[:12],
            "ledger/citation_audit.csv#" + L1[:12],
            "artifacts/literature/tools/build_literature.py",
            "artifacts/literature/reviews/rev3-axis-split.json",
            "reviews/L0-review-093.json#" + L0[:12],
            DECISIONS,
            "research_map/research_map.json#controller_gate_audit",
        ],
    },
    {
        "event_id": "astra-life05-gate-gnum", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-NUM", "scope": "N0", "verdict": "pending",
        "criteria": (
            "Flat-space convergence order measured AND independently replicated within tolerance; "
            "protocol reviewed; lock guard passes. Lock: LOCKED, solver absent, guard present, N1 "
            "hash absent. C8: protocol " + PROTO[:12] + " carries a standing accept 4.5 and two "
            "revise verdicts on the evidence basis (evidence since re-based) -> adjudication card "
            "astra-life05-gnum-protocol-adjudication. C4 registry repair landed this pass: the "
            "controller checkpoint now registers " + PROTO[:12] + ", numerics/results/* and "
            "artifacts/numerics/*; gates.py re-pinned " + NGATES[:12] + " (the 907a88b1 ref is "
            "historical). N0 stop-rule deliverable numerics/results/flat_wave_convergence_rev3.json "
            + N0REV3[:12] + " exists with a four-rung fixed-dt certification and REPLICATED "
            "replication verdicts, but the N0 node verdict on disk is still revise 3.5; G-NUM passes "
            "only on an N0 accept at one hash (astra-life04-n0-verify). N1 remains locked regardless: "
            "release additionally requires G-FORM + G-AUDIT."
        ),
        "evidence_refs": [
            "numerics/CONVERGENCE_PROTOCOL.md#" + PROTO[:12],
            "numerics/gates.py#" + NGATES[:12],
            "numerics/results/flat_wave_convergence_rev3.json#" + N0REV3[:12],
            "reviews/G-NUM-protocol-review.json#" + PROTO[:12],
            "runtime/state/artifact_hashes.json",
            "runtime/state/controller_verification/N0_adjudication.md",
            DECISIONS,
            "research_map/research_map.json#numerics_lock",
            "research_map/research_map.json#controller_gate_audit",
        ],
    },
    {
        "event_id": "astra-life05-gate-gaudit", "event_type": "gate", "actor": "astra",
        "created_at": NOW, "gate_id": "G-AUDIT", "scope": "A0,A1", "verdict": "pending",
        "criteria": (
            "A0 rubric exists without a universal scalar score and has an independent verdict; A1 "
            "has 2 independent accepts per formulation/literature target at a cited sha256. A0 "
            "measured " + A0[:12] + " with 0 accepts (3 revise, including the lead-audit r2 and the "
            "A0 detector-scope blocker); A1 coverage at measured hashes: F0 4 accepts (criterion "
            "met), F1 1, F2a 0, F2b 1, L0 0 (need >=2 each). Evidence audit: 17 hard findings, all "
            "the CF-16 metalinguistic-mention false-positive pattern (the detector flags claims that "
            "discuss the composite token, including the audit claims about that very pattern) - "
            "astra-life05-classsep-calibration adjudicates. WITHHELD."
        ),
        "evidence_refs": [
            "evaluation_rubric.yaml#" + A0[:12],
            "reviews/A1-rebind-coverage.json",
            "reviews/A0-review-lead-audit-r2.json#" + A0[:12],
            "research_map/class_separation.py",
            "artifacts/worker-085/candidate_diff/report.json",
            "artifacts/formulation/proposals/classsep_prose_precision_patch.md",
            DECISIONS,
            "research_map/research_map.json#controller_gate_audit",
        ],
    },
]

# ---------------------------------------------------------------- assignments
CARD = dict(event_type="assignment", actor="astra", created_at=NOW)
ASSIGNMENTS = [
    {
        **CARD, "event_id": "astra-life05-evidence-binding-repair",
        "node_id": "F1,F2a,F2b", "assignee": "astra-lead-formulation",
        "artifact": ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                     "schemas/af_scc_c0_vacuum.yaml", "schemas/taxonomy_cases.jsonl",
                     "artifacts/formulation/FROZEN.json"],
        "gate": "G-FORM", "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "evidence_refs": ["schemas/taxonomy_cases.jsonl#" + CASES[:12],
                          "artifacts/formulation/evidence/taxonomy_consistency.json#" + CONSIST[:12],
                          "reviews/closefind-verify-094.json",
                          "artifacts/worker-095/f2b_rev12_binding_integrity/verdict.json",
                          "artifacts/formulation/FROZEN.json#" + FROZEN[:12]],
        "deadline": "2026-09-12T01:40:00+08:00", "budget_agent_hours": 1.5,
        "acceptance": (
            "Supersedes astra-life04-freeze-hold (rev28 artifact events are in the stream; the hold "
            "is complete) and voids the rev12 pins of astra-life04-verify-gform-r2. Repair exactly "
            "four bounded items at new bytes: (1) rebind schemas/taxonomy_cases.jsonl rows to the "
            "declared F0 rev5 " + F0[:12] + " (binding_status/meta) and re-run its checker; (2) "
            "refresh f0_binding.consistency_evidence_sha256 in all three schemas to the live "
            "artifacts/formulation/evidence/taxonomy_consistency.json " + CONSIST[:12] + " after a "
            "clean check_taxonomy_consistency.py run; (3) correct the F1 variant SET/CH strictness "
            "text at the exact lines worker-076 cites (assertion direction only); (4) publish "
            "FROZEN.json rev29 with byte-verified pins and emit artifact events for every moved "
            "path. Do NOT touch research_map/formulation_taxonomy.yaml (" + F0[:12] + " is "
            "G-F0-frozen) and do not change any class id, hypothesis, conclusion predicate or "
            "genericity semantics. Artifact + artifact events + a machine report naming every "
            "before/after sha256 is the acceptance evidence; the formulation lead's own report is "
            "not a gate verdict."
        ),
        "expected_information_gain": (
            "Makes the rev13 schema set hash-bound gate evidence instead of a self-contradictory "
            "binding chain; converts the F1/F2a/F2b review round from unjudgeable-at-current-bytes "
            "to judgeable at FROZEN rev29."),
        "falsifier": (
            "Any change to a class definition, hypothesis, conclusion predicate or axis semantics; "
            "an F0 write; a schema byte change without an artifact event; a FROZEN rev29 manifest "
            "whose listed hashes do not match live bytes."),
        "stop_rule": (
            "Stop and report if a repair requires a class-semantics change, an F0 change, or if a "
            "named file does not hash to the pinned predecessor. No gate verdict, no node "
            "completion, no re-freeze of anything outside the four named items."),
    },
    {
        **CARD, "event_id": "astra-life05-verify-gform-r3",
        "node_id": "F1,F2a,F2b", "assignee": "astra-lead-audit",
        "artifact": "reviews/G-FORM-final-verify-r3.json", "gate": "G-FORM",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "evidence_refs": ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                          "schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/FROZEN.json",
                          "astra-life05-evidence-binding-repair"],
        "deadline": "2026-09-12T02:45:00+08:00", "budget_agent_hours": 3.0,
        "acceptance": (
            "SUPERSEDES astra-life04-verify-gform-r2: its rev12 pins are void once the repair "
            "lands. Dispatch two independent non-author reviewers per class (F1, F2a, F2b) at the "
            "FROZEN rev29 pins; each verdict must measure the file hash itself, cite sha256, and "
            "check class leakage, conclusion inflation, quantifier/topology binding and the "
            "refreshed consistency-evidence binding. Accepts must be at one hash per class with "
            "bytes stable across the review window; a revise verdict must name a specific field. "
            "No gate self-pass; the audit lead assembles the coverage and Astra records the gate."
        ),
        "expected_information_gain": (
            "First binding independent verdicts at the repaired rev13 bytes; either two accepts per "
            "class (G-FORM proposable) or a hash-bound defect list."),
        "falsifier": (
            "A verdict at a superseded hash counted as binding; a review that does not cite the "
            "measured sha256; a target write while the round is open."),
        "stop_rule": (
            "Stop if FROZEN rev29 does not exist, if its pins differ from the measured bytes, or if "
            "a pinned file moves mid-round; report rather than re-review a moving target."),
    },
    {
        **CARD, "event_id": "astra-life05-verify-l0-final",
        "node_id": "L0", "assignee": "astra-lead-audit",
        "artifact": "reviews/L0-review-final-verify.json", "gate": "G-LIT", "class_id": "GLOBAL",
        "evidence_refs": ["ledger/theorems.jsonl#" + L0[:12],
                          "artifacts/literature/tools/build_literature.py",
                          "artifacts/literature/reviews/rev3-axis-split.json",
                          "reviews/L0-review-093.json#" + L0[:12]],
        "deadline": "2026-09-12T02:30:00+08:00", "budget_agent_hours": 1.5,
        "acceptance": (
            "Two independent blind verdicts at ledger/theorems.jsonl#" + L0[:12] + " (the owner-"
            "announced rev3-final build product; REC-10 reconciliation accepted). Reviewers must "
            "start from these bytes, must not reuse verdict text from ce42d205 or 3e3d3553, and must "
            "first re-run the HF-14 predicates (status / validation_status / supports_claim): all "
            "three must return 0 rows. Axes are content_status and review_status. L1 " + L1[:12] +
            " is unchanged and not re-reviewed. Two accepts at the hash make the L0 half of G-LIT "
            "proposable; no gate self-pass."
        ),
        "expected_information_gain": (
            "Converts L0 from zero binding verdicts to judgeable at one announced hash; the first "
            "independent check that the hardened builder's HF-14 guard holds on a rebuild."),
        "falsifier": (
            "A ledger write after " + L0[:12] + "; a verdict reusing pre-rebuild text; an HF-14 "
            "predicate returning a nonzero row count."),
        "stop_rule": (
            "Stop when each reviewer returns accept|revise|reject with a cited sha256, or when the "
            "L0 hash changes (both verdicts void). Reviewers must not edit the ledger or its build "
            "inputs."),
    },
    {
        **CARD, "event_id": "astra-life05-classsep-calibration",
        "node_id": "A1", "assignee": "astra-lead-audit",
        "artifact": "reviews/CLASSSEP-calibration-adjudication.json", "gate": "G-AUDIT",
        "class_id": "GLOBAL",
        "evidence_refs": ["research_map/class_separation.py",
                          "artifacts/worker-085/candidate_diff/report.json",
                          "artifacts/worker-16/audit_calibration/CANDIDATE-PATCH.md",
                          "artifacts/formulation/proposals/classsep_prose_precision_patch.md"],
        "deadline": "2026-09-12T02:30:00+08:00", "budget_agent_hours": 1.5,
        "acceptance": (
            "Adjudicate the standing 17 hard CLASSSEP findings (all the CF-16 metalinguistic-mention "
            "pattern: claims that negate, split, quote or audit the composite token) against the "
            "canonical detector research_map/class_separation.py and the staged candidate "
            "proposed/class_separation.py (e2d24b927ee8; worker-16 CANDIDATE-PATCH.md, worker-085 "
            "differential audit, formulation classsep_prose_precision_patch.md). Deliver a measured "
            "TP/FP/FN census on (a) the 27-fixture regression corpus, (b) the live hard-finding set, "
            "(c) labeled assertion-vs-mention fixtures; an explicit adopt/reject recommendation with "
            "the exact patch path + sha256 and a regression run; and a claims-retirement policy for "
            "historical metalinguistic claims. Changing the canonical gate checker is a controller-"
            "approved action: the adjudication must separate 'detector fix' from 'claim rewrite' and "
            "must not simply silence the detector. No gate self-pass."
        ),
        "expected_information_gain": (
            "Decides whether G-AUDIT's hard-failure count is a detector artifact or a real class "
            "leak, with measured error rates instead of prose."),
        "falsifier": (
            "An adopted patch that suppresses a genuine 'C0 or C2' assertion on the labeled corpus; "
            "an FP/FN count that cannot be reproduced from the artifact; a census without a "
            "per-fixture verdict."),
        "stop_rule": (
            "Stop if assertion-vs-mention cannot be separated on the labeled set; record that as the "
            "finding rather than shipping a patch. No gate verdict, no claim promotion."),
    },
    {
        **CARD, "event_id": "astra-life05-gnum-protocol-adjudication",
        "node_id": "N0", "assignee": "astra-lead-audit",
        "artifact": "reviews/G-NUM-protocol-r4-adjudication.json", "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "evidence_refs": ["numerics/CONVERGENCE_PROTOCOL.md#" + PROTO[:12],
                          "reviews/G-NUM-protocol-review.json#" + PROTO[:12],
                          "numerics/protocol/n0_fixed_dt_certification.json",
                          "numerics/tests/n0_gate_proposal.json",
                          "numerics/gates.py#" + NGATES[:12]],
        "deadline": "2026-09-12T02:15:00+08:00", "budget_agent_hours": 1.0,
        "acceptance": (
            "N0-ONLY. No solver, no self-gravity, lock stays LOCKED. Adjudicate the contest at "
            "protocol " + PROTO[:12] + ": the standing accept 4.5 (reviews/G-NUM-protocol-review.json) "
            "vs the two revise verdicts about the evidence basis (w067 F1, w081 F1'), now that the "
            "basis is re-based at numerics/protocol/n0_fixed_dt_certification.json and "
            "numerics/tests/n0_gate_proposal.json. Return an operative protocol verdict at a cited "
            "hash with explicit reasons why the re-based evidence does or does not discharge F1/F1'. "
            "Do not adjudicate by majority and do not review N0's node status here."
        ),
        "expected_information_gain": (
            "Settles whether G-NUM criterion C8 (protocol reviewed) is met at the re-based evidence "
            "or needs a further protocol revision."),
        "falsifier": (
            "An adjudication that ignores either dissent; a verdict without a cited hash; any "
            "numerics/ artifact written downstream of the lock."),
        "stop_rule": (
            "Stop if the protocol hash changes or if the re-based evidence files are absent; report "
            "the contest as unresolved rather than picking a side."),
    },
    {
        **CARD, "event_id": "astra-life05-a0-detector-scope",
        "node_id": "A0", "assignee": "astra-lead-audit",
        "artifact": "evaluation/A0_detector_scope_adjudication.json", "gate": "G-AUDIT",
        "class_id": "GLOBAL",
        "evidence_refs": ["artifacts/audit/reports/audit-20260912T003820.json",
                          "evaluation_rubric.yaml#" + A0[:12],
                          "reviews/A0-review-lead-audit-r2.json"],
        "deadline": "2026-09-12T02:00:00+08:00", "budget_agent_hours": 0.5,
        "acceptance": (
            "Resolve the A0 detector-scope blocker (literature lead, 00:44): the HF-14/HF-03 "
            "detectors report corpus-level hits on archive/, incoming/ and worker snapshot paths "
            "that are historical records, not live artifacts. Scope the detectors to canonical "
            "artifacts plus live build inputs, or define an explicit historical-marker exclusion; "
            "record the measured before/after file lists at pinned hashes. No archive patching. "
            "Coordinates with the standing astra-life04-verify-a0 rubric verdict; no gate self-pass."
        ),
        "expected_information_gain": (
            "Removes the last A0 measurement ambiguity so the A0 verdict can bind the rubric, not "
            "the archive layout."),
        "falsifier": (
            "A scope change that hides a live-artifact hit; an exclusion list that includes any "
            "canonical ledger or build input."),
        "stop_rule": (
            "Stop if scoping cannot be defined without editing a frozen record; report the list of "
            "unresolvable paths instead."),
    },
]

# ------------------------------------------------------------------- notices
NOTICES = [
    {
        "event_id": "astra-life05-approve-lit-022", "event_type": "status", "actor": "astra",
        "created_at": NOW, "node_id": "L0", "status": "active", "hours": 0.1,
        "summary": (
            "resource_request lit-l5-20260912-022: APPROVED 3.0 agent-hours for two blind L0 "
            "reviewers at ledger/theorems.jsonl#" + L0[:12] + " (re-binds the unconsumed pass-03 "
            "literature approval; lit-l5-20260912-013 is superseded by 022 and receives no second "
            "allocation). Dispatch is astra-life05-verify-l0-final."
        ),
        "evidence_refs": ["ledger/theorems.jsonl#" + L0[:12], DECISIONS],
        "next_falsifier": "A ledger write after the approval, or a reviewer reusing pre-rebuild verdict text.",
    },
    {
        "event_id": "astra-life05-form-pool-repoint", "event_type": "status", "actor": "astra",
        "created_at": NOW, "node_id": "F1", "status": "active", "hours": 0.1,
        "summary": (
            "resource_request leadform-resource-request-2026-09-12T00:44:00+08:00: APPROVED 6.0 "
            "agent-hours with the pins re-pointed. The request's rev11 hashes (9a8bd4c9/b6123750/"
            "1bb78ce9) are stale: live pins are rev12 " + F1[:12] + "/" + F2A[:12] + "/" + F2B[:12] +
            " and will move once to rev13 under astra-life05-evidence-binding-repair. The approved "
            "6.0 h is bound to astra-life05-evidence-binding-repair + astra-life05-verify-gform-r3; "
            "the request as written is superseded, not revoked."
        ),
        "evidence_refs": ["schemas/af_wcc_vacuum.yaml#" + F1[:12],
                          "schemas/af_scc_c2_vacuum.yaml#" + F2A[:12],
                          "schemas/af_scc_c0_vacuum.yaml#" + F2B[:12],
                          DECISIONS],
        "next_falsifier": "A rev11-pinned reviewer verdict counted as binding, or a second 6.0 h allocation.",
    },
    {
        "event_id": "astra-life05-decisions-notice", "event_type": "status", "actor": "astra",
        "created_at": NOW, "node_id": "A1", "status": "active", "hours": 0.1,
        "summary": (
            "astra-lifecycle-05 decisions record: " + DECISIONS + " (REC-11 G-F0 pass with frozen "
            "bytes; REC-12 evidence-binding repair + rev13/rev29; REC-13 REC-10/CF-19 closed at L0 "
            + L0[:12] + "; REC-14 registry scan-root repair (C4) and gates.py re-pin; REC-15 "
            "protocol contest adjudication; REC-16 CLASSSEP calibration; REC-17 A0 detector scope; "
            "REC-18 F0 promotion; REC-19 resource decisions). numerics_lock remains LOCKED; no N1 "
            "work, no solver."
        ),
        "evidence_refs": [DECISIONS,
                          "numerics/CONVERGENCE_PROTOCOL.md#" + PROTO[:12],
                          "numerics/gates.py#" + NGATES[:12],
                          "ledger/theorems.jsonl#" + L0[:12],
                          "research_map/formulation_taxonomy.yaml#" + F0[:12]],
        "next_falsifier": "A gate verdict or node promotion not backed by artifact + review evidence at a cited hash.",
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
    for ev in GATES + ASSIGNMENTS + NOTICES:
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
    print("pins:", json.dumps({"F0": F0[:12], "F1": F1[:12], "F2a": F2A[:12], "F2b": F2B[:12],
                               "L0": L0[:12], "L1": L1[:12], "A0": A0[:12], "proto": PROTO[:12],
                               "ngates": NGATES[:12], "N0rev3": N0REV3[:12]}))


if __name__ == "__main__":
    main()
