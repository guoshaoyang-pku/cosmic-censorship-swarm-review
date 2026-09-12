#!/usr/bin/env python3
"""Astra round 3: dispatch independent A1 reviews of the landed formulation artifacts."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "research_map"))
import comms  # noqa: E402

F0 = "research_map/formulation_taxonomy.yaml#sha256:a82f249c6725"
F1 = "schemas/af_wcc_vacuum.yaml#sha256:f15ea52380d2"
F2B = "schemas/af_scc_c0_vacuum.yaml#sha256:54917ccd8772"

COMMON_ACCEPT = (
    "Verdict cites the artifact sha256; checks (a) class leakage, (b) conclusion inflation, "
    "(c) assumption completeness, (d) decidable falsifier, (e) any field two readers would "
    "disagree on. Emit a review event with verdict, score 0-5, hard_failures, findings. "
    "Do not reuse another reviewer's text; if you agree, name the artifact lines that decided it."
)

REVIEWS = [
    ("deepseek-flash-17", "F0", "reviews/F0-review-17.json", F0, "G-F0",
     "Reconstruct-from-handoff provenance is not disclosed, or the disjointness relation fails on a case from schemas/taxonomy_cases.jsonl."),
    ("deepseek-flash-19", "F0", "reviews/F0-review-19.json", F0, "G-F0",
     "Two classes share a conclusion_type without a decisive axis separating them, or an exclusion list is empty."),
    ("deepseek-flash-16", "F1", "reviews/F1-review-16.json", F1, "G-FORM",
     "A field is ambiguous enough that two readers disagree whether a spacetime satisfies F1, or the conclusion entails SCC."),
    ("deepseek-flash-17", "F1", "reviews/F1-review-17.json", F1, "G-FORM",
     "Genericity is asserted without a named topology/quantifier, or visibility at I+ is not defined independently of the conclusion."),
    ("deepseek-flash-18", "F2", "reviews/F2b-review-18.json", F2B, "G-FORM",
     "C0 schema inherits C2 control, or its conclusion_type is not distinguishable from the C2 conclusion."),
    ("deepseek-flash-16", "F2", "reviews/F2b-review-16.json", F2B, "G-FORM",
     "The C0 regularity claim is not falsifiable, or the file imports a C2 assumption silently."),
]


def main():
    n = 0
    for i, (who, node, art, target, gate, fals) in enumerate(REVIEWS):
        ev = {
            "event_id": f"astra-rev-{i:02d}-{who}",
            "event_type": "assignment",
            "created_at": comms.now(),
            "actor": "astra",
            "node_id": node,
            "assignee": who,
            "artifact": art,
            "gate": gate,
            "class_id": {"F0": "GLOBAL", "F1": "AF-WCC-VAC-GEN", "F2": "AF-SCC-C0-VAC-GEN"}[node],
            "evidence_refs": [target, "comms/PROTOCOL.md", "research_map/ASTRA_HANDOFF.md:42"],
            "falsifier": fals,
            "acceptance": COMMON_ACCEPT,
            "budget_agent_hours": 1.0,
            "expected_information_gain": "Two independent verdicts per formulation target is the G-F0/G-FORM gate requirement.",
            "stop_rule": "One review event per target; inconclusive is a valid verdict; do not fix the artifact you review.",
            "task": (f"Independent A1 review of {target}. Write {art}. Read the artifact from disk and hash it "
                     f"yourself before citing. You may not be its author. Report hard_failures as a list; "
                     f"score 0-5; verdict accept|revise|reject|inconclusive."),
        }
        comms.send(who, ev)
        r = comms.append_event(ev)
        n += 1 if r.get("accepted") else 0
    print(f"review assignments: {n}/{len(REVIEWS)} accepted")


if __name__ == "__main__":
    main()
