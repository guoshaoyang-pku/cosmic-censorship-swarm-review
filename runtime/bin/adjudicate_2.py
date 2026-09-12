#!/usr/bin/env python3
"""Astra adjudication round 2: N0 replication disagreement."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "research_map"))
import comms  # noqa: E402

E = []


def ev(**kw):
    kw.setdefault("event_id", f"astra-adj2-{len(E):02d}-{kw['event_type']}")
    kw.setdefault("created_at", comms.now())
    kw.setdefault("actor", "astra")
    E.append(kw)


ev(event_type="gate", gate_id="G-NUM", scope="N0", verdict="pending",
   criteria="order reproduced by >=2 methodologically independent schemes AND replication artifact clean AND protocol reviewed by audit",
   evidence_refs=[
       "runtime/state/controller_verification/N0_adjudication.md",
       "runtime/state/controller_verification/n0_replication_astra_run.json#sha256:7adab492",
       "runtime/state/controller_verification/n0_flatwave_astra_run.json#sha256:21284d98"])
ev(event_type="blocker", node_id="N0",
   description="Controller-run replication: cnfem order -0.0773 (self-test false, drift 1.0e+01) yields top-level verdict ORDER DISAGREES; cnfd 'own-energy' self-check false at drift 6.6e-8; harness invariant functional is leapfrog-specific. Order reproduced by lffd 1.9958 and cnfd 1.9935, so the order claim survives; the replication artifact does not.",
   needed_to_unblock="cnfem root cause fixed or formally excluded with evidence; scheme-appropriate invariant functional; clean re-run; protocol reviewed by audit.",
   evidence_refs=["runtime/state/controller_verification/N0_adjudication.md"])
ev(event_type="assignment", node_id="N0", assignee="deepseek-flash-13",
   artifact="numerics/tests/replication_triage.md", gate="G-NUM", class_id="AF-WCC-SCALAR-SPH",
   evidence_refs=["runtime/state/controller_verification/N0_adjudication.md",
                  "runtime/state/controller_verification/n0_replication_astra_run.json",
                  "numerics/tests/flat_wave_replication.py"],
   falsifier="Triage closes cnfem by deleting it, or the invariant gate is relaxed until cnfem passes.",
   acceptance="Root cause for cnfem (order ~0, drift 1e1) with a minimal reproduction; fix or exclusion justified at implementation level; invariant check made scheme-appropriate or relabelled; clean re-run JSON with hashes.",
   budget_agent_hours=3, expected_information_gain="Either a correct FEM replication (strengthening N0) or a documented harness defect; both are gate-relevant.",
   stop_rule="Stop at root cause + clean re-run, or 3 agent-hours, whichever first; report blocker rather than deleting the scheme.",
   task="Controller reproduced your ORDER DISAGREES verdict. Adjudication: order is reproduced by lffd+cnfd; cnfem is an implementation defect until proven otherwise. Triage it.")
ev(event_type="assignment", node_id="N0", assignee="deepseek-flash-14",
   artifact="numerics/protocol/scheme_independence_review.md", gate="G-NUM", class_id="AF-WCC-SCALAR-SPH",
   evidence_refs=["numerics/protocol/convergence_demo.py", "runtime/state/controller_verification/N0_adjudication.md"],
   falsifier="A non-leapfrog scheme passes the leapfrog-functional gate on the same configuration.",
   acceptance="Review of the energy-drift threshold used by the candidate and of the scheme-dependence finding; states what the protocol must require from an independent scheme (scheme-appropriate functional, order fit method, uncertainty).",
   budget_agent_hours=2, expected_information_gain="Prevents replication from being judged by a functional that only the reference scheme can satisfy.",
   stop_rule="Submit review with hashes; do not edit other workers' artifacts.",
   task="Protocol review, not code. Address the scheme-specific invariant finding and the 6.6e-8 vs 3.4e-15 drift gap.")
ev(event_type="status", node_id="N0", status="active", hours=0,
   summary="CONTROLLER ADJUDICATION: N0 order reproduced by lffd+cnfd; cnfem implementation defect; G-NUM stays pending; replication artifact not clean; N1 still locked",
   evidence_refs=["runtime/state/controller_verification/N0_adjudication.md"],
   next_falsifier="A clean replication run in which every reported scheme has a passing self-test.")
ev(event_type="assignment", node_id="N0", assignee="astra-lead-numerics",
   artifact="numerics/tests/n0_gate_proposal.json", gate="G-NUM", class_id="AF-WCC-SCALAR-SPH",
   evidence_refs=["runtime/state/controller_verification/N0_adjudication.md"],
   falsifier="Proposal asks for G-NUM pass while the replication artifact is unclean.",
   acceptance="Integrate workers 13/14 reports; propose G-NUM verdict to Astra with artifact hashes; also re-check the stale binding_status PROVISIONAL now that research_map/formulation_taxonomy.yaml exists on disk.",
   budget_agent_hours=2, expected_information_gain="Single adjudicated numerics verdict instead of three overlapping reports.",
   stop_rule="Propose or hold; do not self-pass the gate. N1 stays queued.",
   task="Adjudicate the N0 replication dispute and re-run the class-binding check against the now-present F0 artifact.")


def main():
    n = 0
    for e in E:
        t = e.get("assignee")
        if t:
            comms.send(t, e)
        r = comms.append_event(e)
        n += 1 if r.get("accepted") else 0
    print(f"adjudication-2 events: {n}/{len(E)} accepted")


if __name__ == "__main__":
    main()
