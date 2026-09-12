#!/usr/bin/env python3
"""Emit W063-SET-DIRECTION-ADJ-01 events to comms/outbox/worker-063.jsonl.

Idempotent on event_id: rows already present in the outbox are skipped.
Every row is validated with research_map.schemas.validate_event before append.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from research_map.schemas import validate_event  # noqa: E402

OUTBOX = ROOT / "comms/outbox/worker-063.jsonl"
D = "artifacts/worker-063/set_direction_adjudication"
REPORT = D + "/report.json"
REPORT_SHA = "5a9ea89dca09bc4df8d86464ddd17ca70b215736058e9bf11eb6746e24d23f86"
RUNNER = D + "/run_set_direction_063.py"
RUNNER_SHA = "1442c2ee732b8b029802ebbb3ee722fd8fd389d83bda259028bf51c2e91497b1"
README = D + "/README.md"
README_SHA = "ea1374e024346d77696dfdc64f3ffce7e06ecafa923731152f4615a36595ca8b"
CKPT = D + "/CHECKPOINT.json"
CKPT_SHA = "5bdd761069878b3ddb02276805bb9a69a890a66561a36678168a45cdcf283e63"

TS = "2026-09-12T01:01:30+08:00"
PINS = [
    "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
    "artifacts/formulation/formulation_taxonomy.yaml#d7419b4e8963",
    "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
    "artifacts/formulation/VARIANT_REGISTRY.json#6bac9adea19e",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json#64b8d6394a04",
    "artifacts/formulation/FROZEN.json#815e08079aef",
    "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
]

ROWS = [
    {
        "event_id": "w063-artifact-setdir-report-20260912T010130",
        "event_type": "artifact",
        "created_at": TS,
        "actor": "worker-063",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "artifact_type": "set_direction_adjudication_report",
        "path": REPORT,
        "sha256": REPORT_SHA,
        "validation_status": "unverified",
        "evidence_refs": PINS,
        "summary": ("Two-level adjudication of the AF-WCC-VAC-GEN variant-SET strength relation: "
                    "7 carriers extracted, 1 predicate-level conflict (F0 canonical L199-200 labels "
                    "the set-based reading 'strictly stronger'), 0 class-negation conflicts, machine-"
                    "checked logic core S=>U (0 counterexamples) + finite separating witness + "
                    "negation reversal, controls K1-K6 pass."),
    },
    {
        "event_id": "w063-artifact-setdir-runner-20260912T010130",
        "event_type": "artifact",
        "created_at": TS,
        "actor": "worker-063",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "artifact_type": "adjudication_runner",
        "path": RUNNER,
        "sha256": RUNNER_SHA,
        "validation_status": "unverified",
        "evidence_refs": [REPORT + "#" + REPORT_SHA[:12]],
        "summary": ("Frozen-before-run stdlib-only runner: pins 8 inputs by sha256, exits 3 on drift "
                    "and 2 on control failure, writes only its own --out."),
    },
    {
        "event_id": "w063-artifact-setdir-readme-20260912T010130",
        "event_type": "artifact",
        "created_at": TS,
        "actor": "worker-063",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "artifact_type": "adjudication_readme",
        "path": README,
        "sha256": README_SHA,
        "validation_status": "unverified",
        "evidence_refs": [REPORT + "#" + REPORT_SHA[:12]],
        "summary": "Human summary: carrier table with lines, two-level result, defect, falsifier, reproduction, non-claims.",
    },
    {
        "event_id": "w063-artifact-setdir-checkpoint-20260912T010130",
        "event_type": "artifact",
        "created_at": TS,
        "actor": "worker-063",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "artifact_type": "worker_checkpoint",
        "path": CKPT,
        "sha256": CKPT_SHA,
        "validation_status": "unverified",
        "evidence_refs": [REPORT + "#" + REPORT_SHA[:12]],
        "summary": "Checkpoint: exit 0, entry==exit pin verification (8/8, 0 drift), control table, claimed event_ids, next falsifier, authority note.",
    },
    {
        "event_id": "w063-claim-setdir-adj-20260912T010130",
        "event_type": "claim",
        "created_at": TS,
        "actor": "worker-063",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "hours": 0.2,
        "conclusion_type": "formal_model",
        "statement": (
            "Worker artifact-and-logic measurement, not a mathematics or physics claim, at pins F0 "
            "canonical research_map/formulation_taxonomy.yaml#0abb9ed8a961 (G-F0-passed; verified as "
            "the FROZEN rev29 815e08079aef pin and equal to live bytes), F0 companion #d7419b4e8963, "
            "F1 rev13 canonical+mirror #d9cebb9404b2, VARIANT_REGISTRY.json#6bac9adea19e, SET delta "
            "#64b8d6394a04 (rebased 00:57:02): the AF-WCC-VAC-GEN variant-SET strength disagreement "
            "is a two-level labelling defect, not a mathematics disagreement. (1) Predicate level: "
            "S (single-q tail) entails U (union/set reading) with 0 counterexamples over exhaustive "
            "finite models (n in {3,4}, |I+|=2) and the converse fails at the finite witness tail="
            "{0,1}, J^-(q0)={0}, J^-(q1)={1}; so S is strictly stronger and U strictly weaker, and "
            "F1 rev13, the registry and the SET delta are CORRECT at this level. (2) Class-assertion "
            "level: not-U entails not-S and not conversely (same witness has not-S true, not-U "
            "false), so the variant SET conclusion is strictly stronger; the delta negation clause "
            "and the companion D1 row are CORRECT at this level. (3) The single live frozen carrier "
            "that is inverted is the G-F0-passed canonical research_map/formulation_taxonomy.yaml "
            "L199-200, which applies the predicate-level label 'strictly stronger' to the set-based "
            "reading. 7 carriers, 1 predicate-level conflict, 0 class-negation conflicts; K1-K6 "
            "controls all pass; FROZEN rev29 pins resolve 50/50. This independently reproduces "
            "worker-018 HF-W018-F1-1 and localizes the repair to F0/controller, not to F1. No gate "
            "verdict, no node status."),
        "assumptions": [
            "the eight pinned files are the authoritative live bytes; any drift voids the binding (runner exits 3)",
            "S and U are read verbatim from F1 rev13 visibility.definition and class_identity_variants[SET].statement",
            "finite-model entailment is decisive for the predicate-level direction; GR-realizability of the strictness separation is the cited W076-GFORM-STRICTNESS-RECONCILE-06 T4, not re-derived",
            "class-assertion strength means the strength of the negated visibility predicate (the class conclusion), per the registry/delta framing",
        ],
        "falsifier": (
            "Derive U => S for a future-inextendible finite-affine-length causal geodesic under the "
            "class's standing assumptions (which would make S=>U non-strict or reversed and the F0 "
            "label correct), or show F0 canonical L199-200 has a live referent other than the "
            "set-based visibility reading, or drift any pinned input and re-run (exit 3 expected, "
            "binding void)."),
        "evidence_refs": PINS,
        "artifact_refs": [
            REPORT + "#" + REPORT_SHA[:12],
            RUNNER + "#" + RUNNER_SHA[:12],
            README + "#" + README_SHA[:12],
            CKPT + "#" + CKPT_SHA[:12],
        ],
        "expected_information_gain": (
            "Converts the F1 rev13 'strictly WEAKER' vs F0 'strictly stronger' contradiction into an "
            "adjudicated, two-level result with one named defective carrier, so lead-audit can decide "
            "the F0 erratum path and stop issuing F1 revises for a defect that is not in F1."),
    },
    {
        "event_id": "w063-review-f0-setdir-20260912T010130",
        "event_type": "review",
        "created_at": TS,
        "actor": "worker-063",
        "node_id": "F0",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-F0",
        "target_id": "F0@0abb9ed8a961 (research_map/formulation_taxonomy.yaml L199-200)",
        "reviewer": "worker-063",
        "verdict": "revise",
        "score": 4.0,
        "hard_failures": [{
            "id": "HF-W063-SETDIR-1",
            "severity": "blocking-for-F0-consistency",
            "carrier": "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
            "lines": "199-200",
            "statement": ("The G-F0-passed canonical taxonomy says 'The set-based reading (gamma "
                          "contained in the union of J^-(q) over all q in I+) is strictly stronger'. "
                          "At the predicate level this is inverted: the single-q tail predicate "
                          "entails the union reading (0 counterexamples, exhaustive finite models) "
                          "and not conversely (finite witness tail={0,1}, J^-(q0)={0}, J^-(q1)={1}). "
                          "The sentence is defensible only if read at the class-assertion "
                          "(negation) level, which it does not say."),
            "falsifier": "Derive U => S under the class assumptions, or show the sentence's live referent is the negated/class-level statement.",
        }],
        "findings": [
            {"id": "F-W063-SETDIR-1", "severity": "info",
             "statement": ("F1 rev13 schemas/af_wcc_vacuum.yaml#d9cebb9404b2 L235 is CORRECT at both "
                           "levels (predicate: SET strictly weaker; class conclusion: not-U strictly "
                           "stronger). No F1 revise should be issued for this finding."),
             "evidence_refs": ["schemas/af_wcc_vacuum.yaml#d9cebb9404b2"]},
            {"id": "F-W063-SETDIR-2", "severity": "major",
             "statement": ("Carrier census: 7 SET-strength carriers across 5 files. Registry "
                           "#6bac9adea19e, SET delta #64b8d6394a04 and companion D1 row #d7419b4e8963 "
                           "are all consistent with F1; only canonical F0 L199-200 carries the "
                           "predicate-level inversion."),
             "evidence_refs": [REPORT + "#" + REPORT_SHA[:12]]},
            {"id": "F-W063-SETDIR-3", "severity": "major",
             "statement": ("Repair routing: any write to research_map/formulation_taxonomy.yaml voids "
                           "G-F0 (ASTRA_HANDOFF). The controller must choose between a recorded G-F0 "
                           "erratum that reads L199-200 as class-negation-level, or a coordinated "
                           "re-freeze with G-F0 re-opened. A worker edit is out of scope."),
             "evidence_refs": ["research_map/ASTRA_HANDOFF.md"]},
            {"id": "F-W063-SETDIR-4", "severity": "info",
             "statement": ("What did not fire: no class-id leakage, no conclusion inflation, no "
                           "C0/C2 merge, and no other inverted carrier in the census; K1-K6 controls "
                           "all pass and the frozen F0 pin equals live bytes."),
             "evidence_refs": [REPORT + "#" + REPORT_SHA[:12]]},
        ],
    },
    {
        "event_id": "w063-blocker-setdir-f0-erratum-20260912T010130",
        "event_type": "blocker",
        "created_at": TS,
        "actor": "worker-063",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "description": (
            "F1 rev13 (AF-WCC-VAC-GEN) is correct at both the predicate and class-assertion level on "
            "the variant-SET strength axis, but its normative binding target, the G-F0-passed "
            "canonical research_map/formulation_taxonomy.yaml#0abb9ed8a961 L199-200, asserts the "
            "opposite predicate-level label. A blind reviewer treating the binding target as "
            "normative cannot issue a clean F1 accept until the F0 sentence is adjudicated; "
            "independently reproduced as worker-018 HF-W018-F1-1."),
        "needed_to_unblock": (
            "Controller / lead-audit adjudication recorded in the map: either (a) a G-F0 erratum "
            "declaring L199-200 to mean the class-negation-level statement (no byte change, G-F0 "
            "stays passed), or (b) coordinated re-freeze + re-review with G-F0 re-opened. No F1 "
            "schema change is requested; worker measurement only."),
        "evidence_refs": [
            REPORT + "#" + REPORT_SHA[:12],
            "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
            "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
            "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json#64b8d6394a04",
        ],
    },
    {
        "event_id": "w063-artifact-setdir-emitter-20260912T010130",
        "event_type": "artifact",
        "created_at": TS,
        "actor": "worker-063",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "artifact_type": "event_emission_harness",
        "path": D + "/emit_events_063.py",
        "sha256": "288fd4771be2311108bdecc731262a107beb7d45b794f526b7acd0181a720754",
        "validation_status": "unverified",
        "evidence_refs": [REPORT + "#" + REPORT_SHA[:12]],
        "summary": ("Idempotent emitter: validates every row with research_map.schemas.validate_event "
                    "before appending to comms/outbox/worker-063.jsonl and skips existing event_ids."),
    },
    {
        "event_id": "w063-artifact-setdir-checkpoint-v2-20260912T010130",
        "event_type": "artifact",
        "created_at": TS,
        "actor": "worker-063",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "artifact_type": "worker_checkpoint",
        "path": CKPT,
        "sha256": "244bf2a80708e6799ddbd4fc85789625bb30c211e0d21baabc550f674514859a",
        "validation_status": "unverified",
        "evidence_refs": [REPORT + "#" + REPORT_SHA[:12]],
        "summary": ("Authoritative checkpoint revision: expands claimed_event_ids to the full 10-row "
                    "set and records the self-reference note; supersedes the "
                    "w063-artifact-setdir-checkpoint-20260912T010130 hash 5bdd76106987."),
    },
    {
        "event_id": "w063-status-setdir-20260912T010130",
        "event_type": "status",
        "created_at": TS,
        "actor": "worker-063",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "status": "active",
        "hours": 0.2,
        "summary": (
            "No inbox card exists for worker-063 (fleet 2026-09-12T00:57:30). Took ONE bounded "
            "class-bound task, W063-SET-DIRECTION-ADJ-01: two-level adjudication of the "
            "AF-WCC-VAC-GEN variant-SET strength relation at F1 rev13 #d9cebb9404b2 vs F0 canonical "
            "#0abb9ed8a961. Result: predicate level S=>U with 0 counterexamples and the converse "
            "fails, so F1/registry/delta are correct; class-negation level not-U strictly stronger, "
            "companion D1 row correct; canonical F0 L199-200 is the one inverted carrier and is "
            "G-F0-frozen. 7 carriers, 1 predicate conflict, K1-K6 controls pass, entry==exit pins "
            "8/8 with 0 drift. CHECKPOINT + EXIT; node status deliberately unchanged (worker events "
            "cannot set status=done, validation_status=passed, or a gate verdict)."),
        "evidence_refs": [
            REPORT + "#" + REPORT_SHA[:12],
            CKPT + "#" + CKPT_SHA[:12],
            "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
            "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
        ],
        "next_falsifier": (
            "Derive U => S under the class assumptions (would reverse the predicate-level verdict), "
            "or show F0 L199-200 refers to the class-negation statement rather than the set-based "
            "reading (would clear HF-W063-SETDIR-1 as an erratum), or drift any pinned input and "
            "re-run (exit 3 expected)."),
    },
]


def main() -> int:
    for row in ROWS:
        validate_event(row)
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text(encoding="utf-8").splitlines():
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                pass
    fresh = [r for r in ROWS if r["event_id"] not in existing]
    with open(OUTBOX, "a", encoding="utf-8") as f:
        for r in fresh:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"validated": len(ROWS), "appended": len(fresh),
                      "skipped_existing": len(ROWS) - len(fresh),
                      "outbox": str(OUTBOX.relative_to(ROOT))}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
