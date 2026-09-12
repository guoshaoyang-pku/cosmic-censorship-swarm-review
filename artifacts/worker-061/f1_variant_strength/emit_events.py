#!/usr/bin/env python3
"""Append the W061-F1-VARSTRENGTH-05 events to comms/outbox/worker-061.jsonl.

Every event is checked against research_map.schemas.validate_event before it is written;
the file is appended, never rewritten.  Hashes are measured at write time.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
from research_map.schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
TAG = "w061-varstrength-20260912T0055"
OUTBOX = os.path.join(ROOT, "comms/outbox/worker-061.jsonl")


def sha256(rel: str) -> str:
    h = hashlib.sha256()
    with open(os.path.join(ROOT, rel), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


A = "artifacts/worker-061/f1_variant_strength"
H = {
    "f1": sha256("schemas/af_wcc_vacuum.yaml"),
    "f2b": sha256("schemas/af_scc_c0_vacuum.yaml"),
    "registry": sha256("artifacts/formulation/VARIANT_REGISTRY.json"),
    "set_delta": sha256("artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"),
    "ch_delta": sha256("artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json"),
    "frozen": sha256("artifacts/formulation/FROZEN.json"),
    "probe": sha256(f"{A}/probe_variant_strength.py"),
    "output": sha256(f"{A}/probe_output.json"),
    "review_json": sha256(f"{A}/REVIEW.json"),
    "review_md": sha256(f"{A}/REVIEW.md"),
    "checkpoint": sha256(f"{A}/CHECKPOINT.json"),
}

FALSIFIER = (
    "On the pins F1 cce9c60146d6 / F2b 55d0a1ea9bda / registry 5eb42f9a384a / SET delta "
    "45b9b6a8d192 / CH delta c28795b0fdfc, this revise is falsified by any one of: (a) a proof that "
    "in every admissible asymptotically flat completion the family of witnessing points on I+ is "
    "down-directed (then S=>T and the omega certificate is inadmissible, making the two readings "
    "equivalent); (b) a canonical convention under which 'X is strictly stronger than predicate P' "
    "means 'the negation of X is stronger than the negation of P' (then F1:234 is consistent and only "
    "the delta's 'implied by, and strictly stronger than' remains a defect); (c) the labels being "
    "repaired to an explicit two-level statement. Re-measure any of the six pinned files: a byte "
    "change voids the verdict."
)

EV = []

EV.append({
    "event_id": f"{TAG}-status-start",
    "event_type": "status",
    "created_at": NOW,
    "actor": "worker-061",
    "task_id": "W061-F1-VARSTRENGTH-05",
    "node_id": "F1",
    "class_id": "AF-WCC-VAC-GEN;AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "status": "active",
    "hours": 0.5,
    "summary": "No inbox card for worker-061. Took one bounded class-bound task: independent machine-checked "
               "adjudication of the variant strictness-direction text named by astra-life05-evidence-binding-repair "
               "item (3) -- F1 SET (AF-WCC-VAC-GEN) and F2b CH (AF-SCC-C0-VAC-GEN) at the pinned rev12 bytes. "
               "Probe written to run only on pinned copies, with four fail-closed mutant controls.",
    "evidence_refs": [f"schemas/af_wcc_vacuum.yaml#sha256:{H['f1'][:12]}",
                      f"schemas/af_scc_c0_vacuum.yaml#sha256:{H['f2b'][:12]}",
                      f"artifacts/formulation/VARIANT_REGISTRY.json#sha256:{H['registry'][:12]}"],
    "next_falsifier": FALSIFIER,
})

EV.append({
    "event_id": f"{TAG}-claim",
    "event_type": "claim",
    "created_at": NOW,
    "actor": "worker-061",
    "task_id": "W061-F1-VARSTRENGTH-05",
    "node_id": "F1",
    "class_id": "AF-WCC-VAC-GEN;AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "conclusion_type": "formal_model",
    "statement": (
        "At pins schemas/af_wcc_vacuum.yaml cce9c60146d6 (rev12), schemas/af_scc_c0_vacuum.yaml "
        "55d0a1ea9bda (rev12), VARIANT_REGISTRY.json 5eb42f9a384a, AF-WCC-VAC-GEN.variant-SET.delta.json "
        "45b9b6a8d192 and AF-SCC-C0-VAC-GEN.variant-CH.delta.json c28795b0fdfc: (1) the SET predicate "
        "(whole curve contained in union_{q in I+} J^-(q)) is strictly WEAKER than the canonical single-q "
        "tail predicate -- T=>S holds (389 preorders / 154452 finite cases, 0 violations; also forced by "
        "past-closure) and S=>T fails on an explicit omega-chain whose escape certificate verifies "
        "3660/3660 (q_j, t0) pairs, so F1:234's predicate-level label 'strictly STRONGER' and the SET "
        "delta's 'implied by, and strictly stronger than, the single-q tail predicate' are defective "
        "(HF-W061-VAR-01/02); (2) the SAME record's negation-level claim and the registry/delta class-level "
        "'strictly STRONGER than AF-WCC-VAC-GEN' are direction-correct (not-S => not-T, 0 violations), so a "
        "blanket inversion of every 'strictly STRONGER' token would repair one level and break the other; "
        "(3) F2b:291 and the CH registry/delta 'strictly WEAKER' are direction-consistent (broad => CH, "
        "E_CH subset E_all) -- the support clause is a soft pronoun/conditionality defect, not an inversion; "
        "(4) F1:215's 'B-containment is strictly stronger' is correct and strict. worker-076 "
        "W076-GFORM-VIS-STRENGTH-03 is CONFIRMED at the predicate level and refined at the class level. "
        "No canonical artifact was edited; worker evidence only."
    ),
    "assumptions": [
        "the six pinned copies are byte-identical to the live canonical bytes at review time (all pin checks true); any later byte change voids the verdict",
        "causal past J^-(q) is modelled as the down-set of a preorder and gamma as a future-directed chain; this is the order-theoretic content of the definitions",
        "the omega-chain is an abstract causal-order countermodel; its realisability by an admissible asymptotically flat vacuum completion is NOT decided here",
        "predicate-level and negation/class-level comparisons are reported separately; the review does not choose a corpus-wide convention",
    ],
    "falsifier": FALSIFIER,
    "evidence_refs": [
        f"schemas/af_wcc_vacuum.yaml#sha256:{H['f1'][:12]}",
        f"schemas/af_scc_c0_vacuum.yaml#sha256:{H['f2b'][:12]}",
        f"artifacts/formulation/VARIANT_REGISTRY.json#sha256:{H['registry'][:12]}",
        f"artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json#sha256:{H['set_delta'][:12]}",
        f"artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json#sha256:{H['ch_delta'][:12]}",
        f"{A}/probe_output.json#sha256:{H['output'][:12]}",
        f"{A}/REVIEW.json#sha256:{H['review_json'][:12]}",
        f"{A}/CHECKPOINT.json#sha256:{H['checkpoint'][:12]}",
    ],
})

for eid, role, rel, key, note in [
    ("artifact-probe", "rerunnable_probe", f"{A}/probe_variant_strength.py", "probe",
     "Independent implementation; reads only pinned/ copies; emits probe_output.json. Four mutant controls are evaluated in-run."),
    ("artifact-output", "machine_probe_output", f"{A}/probe_output.json", "output",
     "Finite preorder corpus, omega escape certificate, level-indexed classifications of every pinned strength token, CH support-clause model, control matrix."),
    ("artifact-review", "independent_review_json", f"{A}/REVIEW.json", "review_json",
     "Verdict revise 4.0; 2 hard failures; 6 findings. Worker evidence, not a gate verdict and not a node completion claim."),
    ("artifact-reviewmd", "independent_review_markdown", f"{A}/REVIEW.md", "review_md",
     "Human-readable form of REVIEW.json with pins, controls and falsifier."),
    ("artifact-checkpoint", "checkpoint_json", f"{A}/CHECKPOINT.json", "checkpoint",
     "Hash ledger for all 11 emitted artifacts; byte-identical copy at runtime/state/w061_f1_variant_strength_checkpoint.json."),
]:
    EV.append({
        "event_id": f"{TAG}-{eid}",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-061",
        "task_id": "W061-F1-VARSTRENGTH-05",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "artifact_type": role,
        "path": rel,
        "sha256": H[key],
        "validation_status": "unverified",
        "note": note,
    })

EV.append({
    "event_id": f"{TAG}-review-f1",
    "event_type": "review",
    "created_at": NOW,
    "actor": "worker-061",
    "task_id": "W061-F1-VARSTRENGTH-05",
    "reviewer": "worker-061",
    "target_id": "F1",
    "node_id": "F1",
    "class_id": "AF-WCC-VAC-GEN",
    "gate": "G-FORM",
    "artifact": "schemas/af_wcc_vacuum.yaml",
    "artifact_sha256": H["f1"],
    "reviewed_sha256": H["f1"],
    "verdict": "revise",
    "score": 4.0,
    "hard_failures": [
        "HF-W061-VAR-01 (F1 SET predicate-level label inverted): schemas/af_wcc_vacuum.yaml:234 asserts variant SET is 'strictly STRONGER than this class's single-q tail predicate', but T=>S holds unconditionally (0/154452 violations) and S=>T fails on the omega chain (escape certificate 3660/3660). The single-q tail predicate is strictly stronger; SET is strictly weaker. The same field's support clause is the correct not-S=>not-T implication, i.e. it contradicts the predicate-level label.",
        "HF-W061-VAR-02 (SET delta self-contradiction): changes[visibility.definition].to says the SET predicate 'is implied by, and strictly stronger than, the single-q tail predicate' -- the two conjuncts cannot both hold under any level convention.",
    ],
    "findings": [
        "F-W061-VAR-01 (level indexing; repair guidance): the variant's NEGATION/CLASS-level label is correct and must NOT be flipped. not-S => not-T (0 violations); the omega chain has not-T true with not-S false. Registry strength (class target) and the delta negation change ('strictly stronger than the single-q negation') are consistent as written. A blanket inversion of every 'strictly STRONGER' token would repair the predicate label and break the class label.",
        "F-W061-VAR-02 (worker-076 corroboration): W076-GFORM-VIS-STRENGTH-03's direction is confirmed at the predicate level by an independent corpus and an independent escape certificate; worker-076's 'line 215 forces the opposite direction' reproduces (line 215 is correct and strict). Its scope is predicate-level.",
        "F-W061-VAR-03 (F2b CH positive control, soft): schemas/af_scc_c0_vacuum.yaml:291 and the CH registry/delta 'strictly WEAKER' are direction-consistent (broad => CH). The support clause is imprecise -- a non-conditional refutation of CH DOES refute the broad class; the sentence is saved only by the word 'conditional' and 'it' has an ambiguous antecedent (flash-19 F0-19-05 family). Do not flip CH.",
        "F-W061-VAR-04 (falsifier status): the record's equivalence falsifier is REFUTED by the omega chain, so it does not fire and supplies no support for either label. Divergence D1 remains real at the predicate level.",
        "F-W061-VAR-05 (ESC-2): option (A) cannot be justified as 'the two readings are equivalent'; option (C) needs the two-level statement (SET predicate strictly weaker; SET-variant negation strictly stronger). This review fixes directions only, not the option.",
    ],
    "evidence_refs": [f"{A}/REVIEW.json#sha256:{H['review_json'][:12]}",
                      f"{A}/probe_output.json#sha256:{H['output'][:12]}",
                      f"schemas/af_wcc_vacuum.yaml#sha256:{H['f1'][:12]}"],
    "next_falsifier": FALSIFIER,
    "no_gate_verdict": True,
    "no_node_status": True,
})

EV.append({
    "event_id": f"{TAG}-review-f2b",
    "event_type": "review",
    "created_at": NOW,
    "actor": "worker-061",
    "task_id": "W061-F1-VARSTRENGTH-05",
    "reviewer": "worker-061",
    "target_id": "F2b",
    "node_id": "F2b",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "artifact": "schemas/af_scc_c0_vacuum.yaml",
    "artifact_sha256": H["f2b"],
    "reviewed_sha256": H["f2b"],
    "verdict": "accept",
    "score": 4.0,
    "hard_failures": [],
    "findings": [
        "SCOPED: this verdict covers ONLY the variant-CH strictness axis on the CH record (schemas/af_scc_c0_vacuum.yaml:283-293, VARIANT_REGISTRY.json:74, CH delta), not the full schema; the blind full-schema F2b round remains the binding coverage.",
        "F-W061-VAR-03 (soft precision): 'strictly WEAKER than this frozen class' is direction-consistent with broad => CH. The support clause 'a subset of extensions suffices to refute it, so a conditional refutation of variant CH does NOT refute the frozen broad class' is imprecise: for a non-conditional refutation, refuting CH does refute the broad class (R_CH subset R_B); the sentence is saved only by the word 'conditional', and 'it' has an ambiguous antecedent (flash-19 F0-19-05 family). Repair as 'parent => CH; the converse fails', with no pronoun.",
    ],
    "evidence_refs": [f"schemas/af_scc_c0_vacuum.yaml#sha256:{H['f2b'][:12]}",
                      f"artifacts/formulation/VARIANT_REGISTRY.json#sha256:{H['registry'][:12]}",
                      f"artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json#sha256:{H['ch_delta'][:12]}",
                      f"{A}/probe_output.json#sha256:{H['output'][:12]}"],
    "next_falsifier": "Re-measure the three pinned CH records; any change voids this scoped accept. Falsified if broad => CH fails (an AF development has a CH-crossing extension but no extension at all), or if a non-conditional refutation of CH is shown not to refute the broad class.",
    "no_gate_verdict": True,
    "no_node_status": True,
})

EV.append({
    "event_id": f"{TAG}-final",
    "event_type": "status",
    "created_at": NOW,
    "actor": "worker-061",
    "task_id": "W061-F1-VARSTRENGTH-05",
    "node_id": "F1",
    "class_id": "AF-WCC-VAC-GEN;AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "status": "active",
    "hours": 0.5,
    "summary": "Bounded class-bound task complete: probe + probe_output + REVIEW.json/.md + CHECKPOINT.json (copy at "
               "runtime/state/w061_f1_variant_strength_checkpoint.json) + SHA256SUMS; claim, 5 artifact events and 2 "
               "reviews emitted. Verdicts: F1 revise 4.0 (2 hard failures: SET predicate label inverted; SET delta "
               "self-contradictory) and a scoped F2b CH accept 4.0 with one soft precision finding. Direct input to "
               "astra-life05-evidence-binding-repair item (3): flip only the predicate-level token, keep the class-level "
               "token, fix the delta's mixed wording. No node status, validation_status or gate verdict is claimed "
               "(worker authority rule).",
    "evidence_refs": [f"{A}/REVIEW.json#sha256:{H['review_json'][:12]}",
                      f"{A}/CHECKPOINT.json#sha256:{H['checkpoint'][:12]}",
                      f"{A}/probe_output.json#sha256:{H['output'][:12]}",
                      f"comms/outbox/worker-061.jsonl#{TAG}-review-f1"],
    "next_falsifier": FALSIFIER,
})

for e in EV:
    validate_event(e)

with open(OUTBOX, "a", encoding="utf-8") as f:
    for e in EV:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")

print(json.dumps({"appended": len(EV), "outbox": OUTBOX, "now": NOW,
                  "events": [e["event_id"] for e in EV]}, indent=1))
