#!/usr/bin/env python3
"""Astra round 4: consolidated F0/F1 revision directive + checker-calibration finding."""
from __future__ import annotations
import hashlib, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "research_map"))
import comms  # noqa: E402


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


F0_H = sha(ROOT / "research_map/formulation_taxonomy.yaml")
F1_H = sha(ROOT / "schemas/af_wcc_vacuum.yaml")
E = []


def ev(**k):
    k.setdefault("event_id", f"astra-dir1-{len(E):02d}-{k['event_type']}")
    k.setdefault("created_at", comms.now())
    k.setdefault("actor", "astra")
    E.append(k)


ev(event_type="gate", gate_id="G-F0", scope="F0", verdict="pending",
   criteria="one canonical F0 with hash-carrying artifact event; single conclusion vocabulary; 2 independent accept verdicts",
   evidence_refs=["reviews/F0-review-17.json", "reviews/F0-review-19.json"])
ev(event_type="gate", gate_id="G-FORM", scope="F1,F2a,F2b", verdict="pending",
   criteria="no predicate mismatch inside a schema; no unproved 'equivalently'; conclusion vocabulary bound to F0; 2 independent accepts per class",
   evidence_refs=["reviews/F0-F1-review-17.json"])

# controller-recorded hashes of the frozen revisions (closes "no sha256 artifact event")
ev(event_type="artifact", node_id="F0", artifact_type="yaml", path="research_map/formulation_taxonomy.yaml",
   sha256=F0_H, validation_status="unverified",
   note="controller-recorded hash of frozen revision 2 (a82f249c); not a validation")
ev(event_type="artifact", node_id="F1", artifact_type="yaml", path="schemas/af_wcc_vacuum.yaml",
   sha256=F1_H, validation_status="unverified",
   note="controller-recorded hash of frozen revision 2 (f15ea523); not a validation")

LEAD_TASK = f"""CONSOLIDATED REVISION DIRECTIVE (G-F0 + G-FORM). Two independent reviewers returned revise
(17: F0 3.0, F1 3.5; 19: F0 revise). Frozen revisions: F0 {F0_H[:12]}, F1 {F1_H[:12]}.
F0 required before re-review:
 R1 designate exactly ONE canonical F0 = research_map/formulation_taxonomy.yaml; the artifacts/formulation copy must be
    marked superseded (or kept only as a remediation appendix) and must not carry class semantics anyone binds to.
 R2 resolve the WCC predicate divergence: pick ONE conclusion predicate; delete unproved 'equivalently'; if the
    black-hole-region clause is kept, attach proof/source and reconcile it with the non-goal list.
 R3 freeze ONE conclusion-type vocabulary and make F1/F2/A0 reference it; keep truth status separate.
 R4 label author-run checks as self-checks; independent verdicts are required (already have two).
 R5 fix the AF-SCC-C2 exclusion mislabel: C0 is a STRONGER conclusion at LOWER regularity.
 R6 fix guard G3 to normalize C^{{0}} / C^0 / braces / superscripts before matching, plus a normalization test.
 R7 if the F0-R file survives, fix its own ban violation (bare 'C2 or C0' label in the implication ledger).
 R8 move unmarked literature claims to known_obstruction with unresolved_pending_L0_L1.
 R9 mark the genericity axis value as provisional until F1/F2 freeze it.
F1 required before re-review:
 R10 one curve class in both conclusion.statement and i_plus.visibility.curve_class; no unproved 'equivalently'.
 R11 fix the linter token-role rule; a checker false positive must not choose the statement. Report before/after
     false-positive counts and record the rule change.
 R12 split definition from equivalence claim in visibility; add to unresolved if unproved.
 R13 declare I- and i0 or record the acceptance-line deviation.
Procedure: write the new revision, emit an artifact event with the new sha256; Astra supersedes the freeze on
receipt and re-dispatches reviews. Do not edit a frozen revision silently (hard audit failure)."""

ev(event_type="assignment", node_id="F0", assignee="astra-lead-formulation",
   artifact="research_map/formulation_taxonomy.yaml", gate="G-F0",
   class_id="AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
   evidence_refs=["reviews/F0-F1-review-17.json", "reviews/F0-review-19.json"],
   falsifier="A revised F0 that still lets two readers bind different WCC predicates, or a checker-driven statement change.",
   acceptance="R1-R13 addressed point by point with a revision note mapping each item to a line; new sha256 emitted; reviewers re-dispatched by Astra.",
   budget_agent_hours=4, expected_information_gain="G-F0 and G-FORM are the critical path; both are one revision away.",
   stop_rule="One consolidated revision; do not open new classes; if an item cannot be met, record it as unresolved with the reason.",
   task=LEAD_TASK)

ev(event_type="assignment", node_id="A1", assignee="astra-lead-audit",
   artifact="evaluation/checker_calibration.csv", gate="G-AUDIT", class_id="GLOBAL",
   evidence_refs=["reviews/F0-F1-review-17.json", "artifacts/worker-17/class_binding_gate/README.md",
                  "artifacts/formulation/tools/check_class_schema.py"],
   falsifier="Every checker reports zero false positives on labeled fixtures, or no checker influenced any artifact text.",
   acceptance="Per-checker TP/FP/FN on labeled fixtures, including at least one real-artifact run; a policy line stating checkers flag but never author; the F1 statement-drift case documented as a worked example.",
   budget_agent_hours=3, expected_information_gain="Prevents automated linters from silently rewriting formulation claims - a fleet-wide failure mode already observed once.",
   stop_rule="One calibration table + policy; no edits to formulation artifacts.",
   task="Reviewer-17 reports their own class-binding gate produced 22 shape + 4 leak false positives and zero true positives on the real F1 artifact, and that an F1 statement was altered to satisfy a linter. Quantify this across checkers and set the policy.")

ev(event_type="status", node_id="GLOBAL", status="active", hours=0,
   summary="CONTROLLER FINDING: tool-driven formulation drift. A class-binding linter's false positive caused an F1 conclusion predicate to diverge from the F0 canonical wording. Policy: checkers may flag, never author; statement changes require a named human/lead decision and a recorded reason.",
   evidence_refs=["reviews/F0-F1-review-17.json", "schemas/af_wcc_vacuum.yaml#conclusion.f0_equivalent_form"],
   next_falsifier="A future artifact revision whose rationale cites a linter verdict rather than a mathematical reason.")

n = 0
for e in E:
    t = e.get("assignee")
    if t:
        comms.send(t, e)
    r = comms.append_event(e)
    n += 1 if r.get("accepted") else 0
print(f"directive events: {n}/{len(E)}")
