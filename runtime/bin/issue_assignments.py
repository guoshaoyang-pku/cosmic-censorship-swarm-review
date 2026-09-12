#!/usr/bin/env python3
"""Astra run-1 assignment fan-out. Emits validated `assignment` events to agent inboxes
and to research_map/events.jsonl. Idempotent: re-running skips duplicate event_ids.

Every task card is class-bound and carries: artifact, gate, evidence_refs, falsifier,
acceptance, budget, EIG, stop rule. Self-gravitating numerics stay locked.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "research_map"))
import comms  # noqa: E402

RUN = "run-2026-09-11T23:15+08:00"
DEADLINE = "2026-09-12T03:15+08:00"
LOCK = ("numerics_lock is LOCKED: no self-gravitating solver, no N1 work. "
        "N0 flat-space calibration only. Do not create numerics/spherical_solver/.")

COMMON = {
    "run_id": RUN,
    "deadline": DEADLINE,
    "evidence_rule": "artifact + sha256 + reviewer verdict; fluent text is never a theorem",
}

TASKS = [
    # ---------------- lead-formulation ----------------
    dict(assignee="astra-lead-formulation", node_id="F0", gate="G-F0",
         artifact="research_map/formulation_taxonomy.yaml",
         class_id="AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
         evidence_refs=["research_map/ASTRA_HANDOFF.md:30", "research_map/research_map.json:26"],
         falsifier="A class in the file cannot be distinguished from another on a concrete test case, or a class lacks an explicit exclusion list.",
         acceptance="File exists; parses; exactly the 4 class ids above; each has hypotheses, exclusions, conclusion_type, and one positive + one negative test case; provenance marks it reconstructed-from-handoff (unverified) until reviewers accept.",
         budget_agent_hours=5, eig="Restores the F0 artifact that the map previously marked done without evidence; F1/F2/L0 all depend on it.",
         stop_rule="Stop when the 4 classes have disjoint hypotheses and reviewers 16/17 return verdicts.",
         extra={"task": "Materialize the formulation taxonomy artifact. The map claims F0 done at 18h but no file exists. Rebuild from the handoff: 4 separate classes, never merged."}),

    dict(assignee="astra-lead-formulation", node_id="F1", gate="G-FORM",
         artifact="schemas/af_wcc_vacuum.yaml",
         class_id="AF-WCC-VAC-GEN",
         evidence_refs=["research_map/ASTRA_HANDOFF.md:38", "research_map/ARCHITECTURE.md:46"],
         falsifier="Two competent readers disagree whether a given asymptotically flat vacuum spacetime satisfies the schema; or the conclusion type entails SCC rather than WCC.",
         acceptance="Schema declares, as separate machine-readable fields: exact quantifiers; topology (globally hyperbolic AF 3+1, I+/I-/i0); weighted data class with named s, delta; genericity (open dense, named topology); visibility definition at I+; conclusion_type=weak_cosmic_censorship; explicit non-goals.",
         budget_agent_hours=6, eig="Fixes the class boundary that every downstream theorem and numerical test binds to.",
         stop_rule="Stop at a frozen schema revision with reviewer verdicts; freeze the sha256 in the map.",
         extra={"task": "Own the F1 artifact; integrate workers 03 and 04; reject any field that leaks SCC content."}),

    dict(assignee="astra-lead-formulation", node_id="F2", gate="G-FORM",
         artifact="schemas/af_scc_regularities.yaml",
         class_id="AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
         evidence_refs=["research_map/ASTRA_HANDOFF.md:39", "research_map/ASTRA_HANDOFF.md:30"],
         falsifier="The file uses 'C0 or C2' anywhere, or one regularity class inherits the other's conclusion type.",
         acceptance="Two clearly separated sections (C2, C0), each with its own hypotheses, metric regularity, conclusion_type and known obstruction; a machine-checkable lint proves no merged class string.",
         budget_agent_hours=6, eig="Prevents the single most likely scope error in the portfolio: treating low-regularity SCC as C2 SCC.",
         stop_rule="Stop when F2a and F2b each have an independent reviewer (18) and the lint passes.",
         extra={"task": "Integrate workers 05 (C2) and 06 (C0); keep them in separate files if separation is cleaner."}),

    # ---------------- lead-literature ----------------
    dict(assignee="astra-lead-literature", node_id="L0", gate="G-LIT",
         artifact="ledger/theorems.jsonl",
         class_id="AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
         evidence_refs=["research_map/ASTRA_HANDOFF.md:40"],
         falsifier="A ledger row cites a source that cannot be located, or states a theorem more strongly than the source does.",
         acceptance=">=15 rows; each row: source (authors, year, title, DOI/arXiv), theorem as quoted, assumptions, class_id, what it does NOT prove, verification_status in {unverified, abstract-read, full-text, page-checked}, falsifier.",
         budget_agent_hours=7, eig="Turns the literature draft into a primary-source ledger and exposes which classes are actually covered.",
         stop_rule="Stop when every row has a locator and the class column is non-empty; unresolved citations stay marked unresolved.",
         extra={"task": "Own L0 and integrate workers 07-11. Never upgrade verification_status without a locator check."}),

    dict(assignee="astra-lead-literature", node_id="L1", gate="G-LIT",
         artifact="ledger/citation_audit.csv",
         class_id="AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
         evidence_refs=["research_map/ASTRA_HANDOFF.md:41"],
         falsifier="A DOI/arXiv id resolves to a different paper, or the cited theorem is in a different regularity class than mapped.",
         acceptance="One row per ledger source with locator, resolver result, exact theorem number/page, class mapping, verdict, and reviewer.",
         budget_agent_hours=6, eig="Citation support is a first-class metric; this is the gate that stops citation inflation.",
         stop_rule="Stop when every L0 row has an audit row; mark unresolved rather than guessing.",
         extra={"task": "Own L1 verification; workers 08/09 fetch and 19 spot-checks."}),

    # ---------------- lead-numerics ----------------
    dict(assignee="astra-lead-numerics", node_id="N0", gate="G-NUM",
         artifact="numerics/tests/flat_wave.py",
         class_id="AF-WCC-SCALAR-SPH",
         evidence_refs=["research_map/ASTRA_HANDOFF.md:42", "research_map/research_map.json:45"],
         falsifier="Measured convergence order is below the declared order minus tolerance, or the exact-solution residual does not shrink with resolution.",
         acceptance="Runs headless; compares against a closed-form flat-space scalar-wave solution; reports measured order; self-test fails closed; N1 lock guard present.",
         budget_agent_hours=8, eig="Calibrates the code path and the convergence protocol before any self-gravitating run; the cheap part of the critical path.",
         stop_rule="Stop when worker 12's implementation and worker 13's independent replication agree on measured order within tolerance.",
         extra={"task": "Own N0 only. " + LOCK}),

    dict(assignee="astra-lead-numerics", node_id="N1", gate="G-NUM",
         artifact="numerics/blockers.md",
         class_id="AF-WCC-SCALAR-SPH",
         evidence_refs=["research_map/ASTRA_HANDOFF.md:31"],
         falsifier="The file proposes a self-gravity run, or claims a release condition that a required gate does not actually satisfy.",
         acceptance="Precise unblock checklist: G-FORM pass, G-AUDIT pass, N0 order measured + replicated, protocol reviewed; plus a statement that no self-gravitating code has been written.",
         budget_agent_hours=2, eig="Makes the lock auditable instead of an instruction agents can ignore.",
         stop_rule="Stop when the checklist maps 1:1 to map gates and the guard test enforces it.",
         extra={"task": "Write the blocker/unblock contract only. " + LOCK}),

    # ---------------- lead-audit ----------------
    dict(assignee="astra-lead-audit", node_id="A0", gate="G-AUDIT",
         artifact="evaluation_rubric.yaml",
         class_id="GLOBAL",
         evidence_refs=["research_map/ARCHITECTURE.md:46", "research_map/ASTRA_HANDOFF.md:34"],
         falsifier="The rubric contains a universal scalar score, or a task type whose verifier is fluency review.",
         acceptance="Per-task-type verifier definitions (schema, literature, numerics, formal); hard-failure list; no universal scalar score; every acceptance test machine-checkable or reviewer-adjudicated with named evidence.",
         budget_agent_hours=6, eig="Restores the A0 artifact the map marked done without evidence; gates depend on it.",
         stop_rule="Stop when reviewers 17/19 accept and the map hashes the frozen file.",
         extra={"task": "Own A0 materialization. " + LOCK}),

    dict(assignee="astra-lead-audit", node_id="A1", gate="G-AUDIT",
         artifact="reviews/",
         class_id="AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
         evidence_refs=["research_map/ASTRA_HANDOFF.md:42"],
         falsifier="A review verdict exists without a cited artifact sha256, or two 'independent' reviews are the same text.",
         acceptance="For each of F0,F1,F2a,F2b,L0: two reviewers, independent verdicts with artifact sha256, class-leakage check, conclusion-inflation check, hard-failure list, score 0-5.",
         budget_agent_hours=7, eig="This is the gate that decides whether formulation output may be promoted; it is the highest-value review in the run.",
         stop_rule="Stop when each target has 2 verdicts or is explicitly marked inconclusive.",
         extra={"task": "Own the A1 queue; assign reviewers 17-19; enforce independence."}),

    dict(assignee="astra-lead-audit", node_id="A2", gate="G-AUDIT",
         artifact="evaluation/ablation_design.yaml",
         class_id="GLOBAL",
         evidence_refs=["HANDOFF.md:52", "research_map/ARCHITECTURE.md:51"],
         falsifier="Arms are not matched on tokens and wall-clock, or the primary metric is a universal scalar score.",
         acceptance="4 arms (strong model, self-consistency, independent cheap agents, cheap+coordinator) with matched token and wall-clock budgets, pre-registered metrics (accepted-claim rate, hard-failure rate, citation support, duplication, reviewer agreement, novel accepted coverage, cost/accepted claim, per-class coverage), and a null baseline.",
         budget_agent_hours=5, eig="Prevents a swarm-advantage claim with no matched-budget control.",
         stop_rule="Design only this run; execution waits for G-FORM and G-AUDIT.",
         extra={"task": "Design + dry-run the harness on synthetic data; do not spend model budget on arms yet."}),

    # ---------------- workers: formulation ----------------
    dict(assignee="deepseek-flash-01", node_id="F0", gate="G-F0",
         artifact="research_map/formulation_taxonomy.yaml", class_id="GLOBAL",
         evidence_refs=["research_map/ASTRA_HANDOFF.md:30"], falsifier="Class overlap on a test case.",
         acceptance="Main author of the taxonomy file; 4 classes; disjointness table.",
         budget_agent_hours=4, eig="Foundation artifact.", stop_rule="Submit artifact event with sha256.",
         extra={"task": "Draft formulation_taxonomy.yaml. No claims of theorem status."}),
    dict(assignee="deepseek-flash-02", node_id="F0", gate="G-F0",
         artifact="schemas/taxonomy_cases.jsonl", class_id="GLOBAL",
         evidence_refs=["research_map/ASTRA_HANDOFF.md:30"], falsifier="A case cannot be classified under exactly one class.",
         acceptance=">=8 positive and >=8 negative cases covering the 4 classes; each case names the class and the decisive hypothesis.",
         budget_agent_hours=4, eig="Machine-checkable class separation.", stop_rule="Submit with sha256; flag ambiguous cases as open.",
         extra={"task": "Adversarial test cases for class leakage."}),
    dict(assignee="deepseek-flash-03", node_id="F1", gate="G-FORM",
         artifact="schemas/af_wcc_vacuum.yaml", class_id="AF-WCC-VAC-GEN",
         evidence_refs=["research_map/ASTRA_HANDOFF.md:38"], falsifier="Ambiguous quantifier/topology field.",
         acceptance="Main author; exact quantifiers, topology, weighted data class, genericity, I+, visibility, conclusion_type.",
         budget_agent_hours=4, eig="Core schema.", stop_rule="Submit draft + list of fields you could not pin down.",
         extra={"task": "Draft F1. Mark unresolved fields explicitly instead of inventing precision."}),
    dict(assignee="deepseek-flash-04", node_id="F1", gate="G-FORM",
         artifact="schemas/f1_falsifier_tests.jsonl", class_id="AF-WCC-VAC-GEN",
         evidence_refs=["research_map/ASTRA_HANDOFF.md:38"], falsifier="A test that no schema field can decide.",
         acceptance=">=10 ambiguity tests: spacetime description + does it satisfy F1? + which field decides.",
         budget_agent_hours=4, eig="Falsifier suite for F1.", stop_rule="Submit with sha256.",
         extra={"task": "Attack worker 03's schema. Try to construct a spacetime where WCC-hypothesis fields are ambiguous."}),
    dict(assignee="deepseek-flash-05", node_id="F2", gate="G-FORM",
         artifact="schemas/af_scc_c2_vacuum.yaml", class_id="AF-SCC-C2-VAC-GEN",
         evidence_refs=["research_map/ASTRA_HANDOFF.md:39"], falsifier="C2 conclusion reused for C0 data.",
         acceptance="C2-only schema: metric regularity C2, conclusion_type for SCC at C2, known obstructions, non-goals.",
         budget_agent_hours=4, eig="Separates the strongest SCC class.", stop_rule="Submit with sha256.",
         extra={"task": "C2 only. Never write 'C0 or C2'."}),
    dict(assignee="deepseek-flash-06", node_id="F2", gate="G-FORM",
         artifact="schemas/af_scc_c0_vacuum.yaml", class_id="AF-SCC-C0-VAC-GEN",
         evidence_refs=["research_map/ASTRA_HANDOFF.md:39"], falsifier="C0 schema assumes C2 control or inherits the C2 conclusion.",
         acceptance="C0-only schema: metric regularity C0, what fails at C0, weaker conclusion_type, explicit non-goals, leakage test vs C2.",
         budget_agent_hours=4, eig="Separates the low-regularity SCC class.", stop_rule="Submit with sha256.",
         extra={"task": "C0 only. Never write 'C0 or C2'."}),

    # ---------------- workers: literature ----------------
    dict(assignee="deepseek-flash-07", node_id="L0", gate="G-LIT",
         artifact="ledger/theorems.jsonl", class_id="GLOBAL",
         evidence_refs=["research_map/ASTRA_HANDOFF.md:40"], falsifier="A row without a locator.",
         acceptance="Skeleton schema + >=10 filled rows with locators and explicit non-claims.",
         budget_agent_hours=4, eig="Ledger skeleton.", stop_rule="Submit with sha256; unresolved stays unresolved.",
         extra={"task": "Build ledger/theorems.jsonl. One JSON object per line."}),
    dict(assignee="deepseek-flash-08", node_id="L1", gate="G-LIT",
         artifact="ledger/citation_audit.csv", class_id="AF-WCC-VAC-GEN",
         evidence_refs=["research_map/ASTRA_HANDOFF.md:41"], falsifier="DOI resolves to a different work.",
         acceptance="Verify WCC-side sources: Penrose 1969; Christodoulou 1999; Dafermos-Rodnianski; Ringstrom; and 2+ more. Locator + exact theorem + class mapping + verdict.",
         budget_agent_hours=4, eig="Primary-source support for WCC.", stop_rule="Fetch each locator; record HTTP/DOI result; mark failures.",
         extra={"task": "Web-verify WCC citations. Record failed lookups as unresolved, never as verified."}),
    dict(assignee="deepseek-flash-09", node_id="L1", gate="G-LIT",
         artifact="ledger/citation_audit.csv", class_id="AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
         evidence_refs=["research_map/ASTRA_HANDOFF.md:41"], falsifier="Theorem quoted in the wrong regularity class.",
         acceptance="Verify SCC-side sources: Dafermos; Luk-Oh; Choptuik; Eardley-Gundlach; Gundlach-Martin-Garcia; and 2+ more, with exact theorem numbers and class mapping.",
         budget_agent_hours=4, eig="Primary-source support for SCC classes.", stop_rule="Record resolver results; unresolved list is a valid output.",
         extra={"task": "Web-verify SCC citations. Distinguish C0 from C2 explicitly."}),
    dict(assignee="deepseek-flash-10", node_id="L1", gate="G-LIT",
         artifact="ledger/class_coverage.csv", class_id="GLOBAL",
         evidence_refs=["research_map/ARCHITECTURE.md:22"], falsifier="A class claimed covered with no source that states its conclusion type.",
         acceptance="Matrix source x class with covered/partial/none and the exact theorem that covers it.",
         budget_agent_hours=4, eig="Shows where the portfolio is actually open.", stop_rule="Submit with sha256.",
         extra={"task": "Map each ledger source to the 4 classes; empty cells are the interesting output."}),
    dict(assignee="deepseek-flash-11", node_id="L1", gate="G-LIT",
         artifact="ledger/counterexamples.jsonl", class_id="GLOBAL",
         evidence_refs=["research_map/ASTRA_HANDOFF.md:30"], falsifier="A 'counterexample' that violates a hypothesis excluded by the class schema.",
         acceptance=">=6 known solutions/spacetimes that show genericity or hypothesis necessity; each with source, which hypothesis it violates, which class it bounds.",
         budget_agent_hours=4, eig="Bounds what each class can claim.", stop_rule="Submit with sha256.",
         extra={"task": "Collect hypothesis-violating examples (negative mass, non-AF, non-generic data, etc.)."}),

    # ---------------- workers: numerics (N0 only) ----------------
    dict(assignee="deepseek-flash-12", node_id="N0", gate="G-NUM",
         artifact="numerics/tests/flat_wave.py", class_id="AF-WCC-SCALAR-SPH",
         evidence_refs=["research_map/research_map.json:45"], falsifier="No measured convergence order.",
         acceptance="Headless test: closed-form solution, 3+ resolutions, measured order, asserts order >= declared - tol, exit code reflects pass/fail.",
         budget_agent_hours=4, eig="Code calibration.", stop_rule="Run it; submit stdout + sha256.",
         extra={"task": "Implement flat-space scalar-wave convergence test only. " + LOCK}),
    dict(assignee="deepseek-flash-13", node_id="N0", gate="G-NUM",
         artifact="numerics/tests/flat_wave_replication.py", class_id="AF-WCC-SCALAR-SPH",
         evidence_refs=["research_map/research_map.json:45"], falsifier="Replication shares the same discretization bug as worker 12.",
         acceptance="Independent scheme (different stencil/method) reproducing the same measured order; documents differences from worker 12.",
         budget_agent_hours=4, eig="Independent numerical replication.", stop_rule="Submit both orders; disagreement is a finding.",
         extra={"task": "Replicate N0 with a different method. " + LOCK}),
    dict(assignee="deepseek-flash-14", node_id="N0", gate="G-NUM",
         artifact="numerics/protocol/convergence_protocol.md", class_id="AF-WCC-SCALAR-SPH",
         evidence_refs=["research_map/ARCHITECTURE.md:46"], falsifier="Protocol cannot detect a wrong order.",
         acceptance="Self-convergence (Richardson), exact-solution residual, constraint/invariant diagnostics, failure criteria, resolution ladder, reporting table.",
         budget_agent_hours=4, eig="Makes convergence auditable before self-gravity.", stop_rule="Submit with sha256.",
         extra={"task": "Write the protocol/audit spec; include a worked example with synthetic data. " + LOCK}),
    dict(assignee="deepseek-flash-15", node_id="N1", gate="G-NUM",
         artifact="numerics/tests/selfgravity_lock_guard.py", class_id="AF-WCC-SCALAR-SPH",
         evidence_refs=["research_map/ASTRA_HANDOFF.md:31"], falsifier="Guard passes while a self-gravity artifact exists.",
         acceptance="Test fails if numerics/spherical_solver/ exists or if any N1+ artifact is present while numerics_lock.state==locked; reads the map file.",
         budget_agent_hours=4, eig="Machine-enforces the controller lock.", stop_rule="Run the guard; submit stdout + sha256.",
         extra={"task": "Implement the lock guard test. " + LOCK}),

    # ---------------- workers: audit ----------------
    dict(assignee="deepseek-flash-16", node_id="A0", gate="G-AUDIT",
         artifact="evaluation_rubric.yaml", class_id="GLOBAL",
         evidence_refs=["research_map/ASTRA_HANDOFF.md:34"], falsifier="Any universal scalar score.",
         acceptance="Main author: per-task-type verifiers, hard failures, evidence requirements, no universal scalar score.",
         budget_agent_hours=4, eig="Evaluation gate artifact.", stop_rule="Submit with sha256.",
         extra={"task": "Draft the rubric. Every acceptance line must name its evidence type."}),
    dict(assignee="deepseek-flash-17", node_id="A1", gate="G-AUDIT",
         artifact="reviews/F0-F1-review-17.json", class_id="GLOBAL",
         evidence_refs=["research_map/ASTRA_HANDOFF.md:42"], falsifier="Verdict without artifact sha256.",
         acceptance="Independent review of F0 and F1: class leakage, conclusion inflation, ambiguity; verdict + score + hard failures + cited sha256.",
         budget_agent_hours=4, eig="Second-reviewer independence.", stop_rule="Submit one review event per target.",
         extra={"task": "Review F0/F1 artifacts when they appear; do not accept fluent text as evidence."}),
    dict(assignee="deepseek-flash-18", node_id="A1", gate="G-AUDIT",
         artifact="reviews/F2-review-18.json", class_id="AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
         evidence_refs=["research_map/ASTRA_HANDOFF.md:39"], falsifier="C0 and C2 verdicts share reasoning or conclusion type.",
         acceptance="Adversarial review of F2a/F2b: hunt 'C0 or C2' leakage, conclusion inheritance; verdict + score + cited sha256.",
         budget_agent_hours=4, eig="Protects the most error-prone class split.", stop_rule="Two separate verdicts, one per regularity.",
         extra={"task": "Try to prove the C0 and C2 schemas are the same class. If you cannot, say so."}),
    dict(assignee="deepseek-flash-19", node_id="L0", gate="G-LIT",
         artifact="reviews/L0-review-19.json", class_id="GLOBAL",
         evidence_refs=["research_map/ASTRA_HANDOFF.md:41"], falsifier="Spot-checked row has a fabricated locator.",
         acceptance="Independently re-fetch >=3 random ledger rows; report resolver result vs row claim; verdict.",
         budget_agent_hours=4, eig="Detects citation fabrication.", stop_rule="Submit verdict with the exact fetched locators.",
         extra={"task": "Audit literature rows by re-fetching. Report mismatches verbatim."}),
    dict(assignee="deepseek-flash-20", node_id="A2", gate="G-AUDIT",
         artifact="evaluation/ablation_harness.py", class_id="GLOBAL",
         evidence_refs=["HANDOFF.md:52"], falsifier="Harness compares arms at unequal token budget.",
         acceptance="Harness enforces matched token+wall-clock budgets, logs per-arm metrics, runs on synthetic data end-to-end.",
         budget_agent_hours=4, eig="Makes the later ablation claim honest.", stop_rule="Dry-run only; no model calls.",
         extra={"task": "Build the ablation harness; execute with synthetic/dummy proposers only."}),
]


def main():
    sent = 0
    for i, t in enumerate(TASKS):
        eid = f"asg-{RUN.split('run-')[1][:10]}-{t['node_id']}-{t['assignee']}-{i:02d}"
        ev = {
            "event_id": eid,
            "event_type": "assignment",
            "created_at": comms.now(),
            "actor": "astra",
            "node_id": t["node_id"],
            "assignee": t["assignee"],
            "artifact": t["artifact"],
            "gate": t["gate"],
            "evidence_refs": t["evidence_refs"],
            "falsifier": t["falsifier"],
            "class_id": t["class_id"],
            "acceptance": t["acceptance"],
            "budget_agent_hours": t["budget_agent_hours"],
            "expected_information_gain": t["eig"],
            "stop_rule": t["stop_rule"],
            "run_id": RUN,
            "deadline": DEADLINE,
            **({"task": t["extra"]["task"]} if t.get("extra", {}).get("task") else {}),
        }
        comms.send(t["assignee"], ev)
        res = comms.append_event(ev)
        if res.get("accepted"):
            sent += 1
    print(f"assignments issued: {sent} new / {len(TASKS)} total")


if __name__ == "__main__":
    main()
