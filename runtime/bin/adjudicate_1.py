#!/usr/bin/env python3
"""Astra adjudication round 1: resource-request decisions, F2 re-ownership, drift corrections."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "research_map"))
import comms  # noqa: E402

E = []


def ev(**kw):
    kw.setdefault("event_id", f"astra-adj1-{len(E):02d}-{kw['event_type']}")
    kw.setdefault("created_at", comms.now())
    kw.setdefault("actor", "astra")
    E.append(kw)


# --- resource request 1: approve F2a draft to worker 08 (F2a was orphaned by drift) ---
ev(event_type="budget", group_id="formulation", delta_agent_hours=2,
   reason="approve e08-rr-F2a: 1 breadth executor, 2h, canonical schemas/af_scc_c2_vacuum.yaml")
ev(event_type="assignment", node_id="F2", assignee="deepseek-flash-08",
   artifact="schemas/af_scc_c2_vacuum.yaml", gate="G-FORM", class_id="AF-SCC-C2-VAC-GEN",
   evidence_refs=["research_map/ASTRA_HANDOFF.md:30", "research_map/ASTRA_HANDOFF.md:39",
                  "schemas/taxonomy_cases.jsonl", "research_map/formulation_taxonomy.yaml"],
   falsifier="Any field that lets a C0 datum satisfy this C2 schema, or a conclusion_type shared with the C0 schema.",
   acceptance="C2-only schema at the canonical path; exact quantifiers, topology, metric regularity C2, genericity, I+, visibility-as-inextendibility, conclusion_type; sha256 in the artifact event.",
   budget_agent_hours=2, expected_information_gain="Closes the orphaned F2a slot; F2 split is on the G-FORM critical path.",
   stop_rule="Draft + self-check, or 2 agent-hours, whichever first; emit artifact and blocker events.",
   task="RESOURCE REQUEST APPROVED. Worker 05 drifted to a pool-overlap tangent, so F2a is yours. Write schemas/af_scc_c2_vacuum.yaml only; F2b C0 stays with worker 06.")
ev(event_type="priority_change", scope="deepseek-flash-05:flash_pool_overlap",
   old_priority=1, new_priority=4,
   reason="Off-assignment tangent. F2a slot was orphaned; worker 08 now owns F2a. Worker 05 owns the F2 integration/leakage lint instead.")

# --- resource request 2: approve evidence-gate integration to worker 19, scoped ---
ev(event_type="budget", group_id="audit", delta_agent_hours=2,
   reason="approve flash19-0009: integrate artifact/evidence checks; patch staged under artifacts/audit/, Astra integrates")
ev(event_type="assignment", node_id="A1", assignee="deepseek-flash-19",
   artifact="artifacts/audit/validate_map_evidence_patch/", gate="G-AUDIT", class_id="GLOBAL",
   evidence_refs=["research_map/audit_evidence.py", "research_map/validate_map.py", "runtime/state/artifact_hashes.json"],
   falsifier="A synthetic map with a done node and missing artifact still prints VALID after the patch.",
   acceptance="Patch + >=6 labeled fixtures (done+missing artifact, done+no evidence, gate pass without evidence, lock violation, clean) with expected outcomes; runs as a test; no direct edit to research_map/*.py.",
   budget_agent_hours=2, expected_information_gain="Removes the false-VALID failure mode permanently and turns it into a regression test.",
   stop_rule="One integration attempt staged under artifacts/audit/; Astra integrates after audit-lead review.",
   task="APPROVED with scope control: stage the patch and fixtures under artifacts/audit/validate_map_evidence_patch/; do not edit research_map/ files (Astra owns those and will integrate). Note audit_evidence.py already implements the check; import it rather than duplicating.")
ev(event_type="assignment", node_id="F2", assignee="deepseek-flash-05",
   artifact="schemas/af_scc_regularities.yaml", gate="G-FORM",
   class_id="AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
   evidence_refs=["research_map/ASTRA_HANDOFF.md:30", "artifacts/worker-06/class_binding_rules.json"],
   falsifier="The aggregator file asserts a merged C0/C2 class, or a checker fixture labeled NEG passes.",
   acceptance="Aggregator that references schemas/af_scc_c2_vacuum.yaml and schemas/af_scc_c0_vacuum.yaml without merging them, plus a leakage lint consuming worker-06 rules; >=8 fixtures with expected verdicts.",
   budget_agent_hours=3, expected_information_gain="Turns the F2 split into a machine-checkable artifact instead of two documents that could drift together.",
   stop_rule="Integrate after workers 06/08 publish their files; if they are late, ship the lint + fixtures against the taxonomy and emit a blocker.",
   task="New scope: F2 integration + class-leakage lint. Freeze the flash_pool_overlap tangent and record it as one paragraph in artifacts/worker-05/.")

# --- resource request status bookkeeping is applied by apply_events; record decisions ---
for i, r in enumerate(["e08-rr-20260911T2323-f2a", "flash19-0009"]):
    ev(event_type="status", node_id="GLOBAL", status="active", hours=0,
       summary=f"resource_request {r}: APPROVED with scope control (see assignment/budget events this timestamp)",
       evidence_refs=["research_map/research_map.json#resource_requests"], next_falsifier="Requester acts outside the approved scope.")


def main():
    n = 0
    for e in E:
        target = e.get("assignee")
        if target:
            comms.send(target, e)
        res = comms.append_event(e)
        n += 1 if res.get("accepted") else 0
    print(f"adjudication events: {n}/{len(E)} accepted")


if __name__ == "__main__":
    main()
