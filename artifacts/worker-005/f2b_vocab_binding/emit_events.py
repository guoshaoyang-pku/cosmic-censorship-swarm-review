#!/usr/bin/env python3
"""Emit W005-F2B-VOCAB-BIND-01 outbox events and the worker checkpoint.

Idempotent on event_id: existing ids are skipped. Appends only to this worker's own
outbox (comms/outbox/worker-005.jsonl) and writes one checkpoint under runtime/state/.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DIR = ROOT / "artifacts/worker-005/f2b_vocab_binding"
OUTBOX = ROOT / "comms/outbox/worker-005.jsonl"
STATE = ROOT / "runtime/state"
CREATED = "2026-09-12T00:42:00+08:00"
ACTOR = "worker-005"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
NODE = "F2b"
GATE = "G-FORM"
TASK = "W005-F2B-VOCAB-BIND-01"
EV = "w005-f2bvocab-20260912T0042"

REQ = {
    "artifact": ["node_id", "artifact_type", "path", "sha256", "validation_status"],
    "review": ["target_id", "reviewer", "verdict", "score", "hard_failures", "findings"],
    "claim": ["class_id", "statement", "conclusion_type", "assumptions", "falsifier", "evidence_refs"],
    "blocker": ["node_id", "description", "needed_to_unblock", "evidence_refs"],
    "status": ["node_id", "status", "summary"],
}
EVREF = re.compile(r"^[^\s#]+\.(ya?ml|json|jsonl|md|csv|py|txt)(#([0-9a-f]{6,64})|:\d+(-\d+)?)$")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def validate(ev: dict) -> None:
    for k in ("event_id", "event_type", "created_at", "actor"):
        assert ev.get(k), f"missing base field {k}"
    for k in REQ[ev["event_type"]]:
        assert k in ev, f"{ev['event_id']} missing {k}"
    for r in ev.get("evidence_refs", []):
        assert EVREF.match(r), f"{ev['event_id']} bad evidence_ref {r!r}"
    if ev["event_type"] == "artifact":
        assert re.fullmatch(r"[0-9a-f]{64}", ev["sha256"]), ev["event_id"]


def main() -> int:
    h = {
        "checker": sha(DIR / "check_f2b_vocab_binding.py"),
        "report": sha(DIR / "report.json"),
        "selftest": sha(DIR / "selftest.json"),
        "scan": sha(DIR / "SCAN.md"),
    }
    report = json.loads((DIR / "report.json").read_text())
    st = json.loads((DIR / "selftest.json").read_text())
    pins = report["pins"]
    f2b_pin = pins["schemas/af_scc_c0_vacuum.yaml"]
    f0_pin = pins["research_map/formulation_taxonomy.yaml"]
    al_pin = pins["artifacts/formulation/VOCAB_ALIASES.json"]
    ce_pin = pins["artifacts/formulation/evidence/taxonomy_consistency.json"]
    frozen = pins["artifacts/formulation/FROZEN.json"]
    frozen_sha = sha(ROOT / "artifacts/formulation/FROZEN.json")

    ev = [
        {
            "event_id": f"{EV}-artifact-checker", "event_type": "artifact", "created_at": CREATED,
            "actor": ACTOR, "agent_slot": ACTOR, "node_id": NODE, "class_id": CLASS_ID, "gate": GATE,
            "artifact_type": "checker", "path": "artifacts/worker-005/f2b_vocab_binding/check_f2b_vocab_binding.py",
            "sha256": h["checker"], "validation_status": "unverified",
            "evidence_refs": [f"artifacts/worker-005/f2b_vocab_binding/check_f2b_vocab_binding.py#{h['checker'][:12]}"],
            "note": "independent stdlib+PyYAML instrument, strict duplicate-key loader, read-only on canonical artifacts; 9 checks, 9/9 planted mutants caught, always-accept and always-reject controls both differ from baseline",
        },
        {
            "event_id": f"{EV}-artifact-report", "event_type": "artifact", "created_at": CREATED,
            "actor": ACTOR, "agent_slot": ACTOR, "node_id": NODE, "class_id": CLASS_ID, "gate": GATE,
            "artifact_type": "report", "path": "artifacts/worker-005/f2b_vocab_binding/report.json",
            "sha256": h["report"], "validation_status": "unverified", "measured_at": report["measured_at"],
            "verdict": report["verdict"],
            "evidence_refs": [
                f"artifacts/worker-005/f2b_vocab_binding/report.json#{h['report'][:12]}",
                f"schemas/af_scc_c0_vacuum.yaml#{f2b_pin[:12]}",
                f"research_map/formulation_taxonomy.yaml#{f0_pin[:12]}",
                f"artifacts/formulation/VOCAB_ALIASES.json#{al_pin[:12]}",
                f"artifacts/formulation/evidence/taxonomy_consistency.json#{ce_pin[:12]}",
            ],
            "note": "literal_vocab_binding_fail__no_class_leakage: P4/P5 literal token membership fail, P6 alias companion unbound, P9 consistency-evidence pin stale; P3/P7/P8 pass so no C2/WCC merge or conclusion inflation",
        },
        {
            "event_id": f"{EV}-artifact-selftest", "event_type": "artifact", "created_at": CREATED,
            "actor": ACTOR, "agent_slot": ACTOR, "node_id": NODE, "class_id": CLASS_ID, "gate": GATE,
            "artifact_type": "test_evidence", "path": "artifacts/worker-005/f2b_vocab_binding/selftest.json",
            "sha256": h["selftest"], "validation_status": "unverified",
            "evidence_refs": [f"artifacts/worker-005/f2b_vocab_binding/selftest.json#{h['selftest'][:12]}",
                              f"artifacts/worker-005/f2b_vocab_binding/check_f2b_vocab_binding.py#{h['checker'][:12]}"],
            "note": f"baseline matches expected {st['baseline_matches_expected']}; mutants_all_pass {st['mutants_all_pass']}; all_checks_discriminated {st['all_checks_discriminated']}",
        },
        {
            "event_id": f"{EV}-artifact-scan", "event_type": "artifact", "created_at": CREATED,
            "actor": ACTOR, "agent_slot": ACTOR, "node_id": NODE, "class_id": CLASS_ID, "gate": GATE,
            "artifact_type": "report", "path": "artifacts/worker-005/f2b_vocab_binding/SCAN.md",
            "sha256": h["scan"], "validation_status": "unverified",
            "evidence_refs": [f"artifacts/worker-005/f2b_vocab_binding/SCAN.md#{h['scan'][:12]}"],
            "note": "human-readable scan: pins, check table, findings, falsifier, authority limits",
        },
        {
            "event_id": f"{EV}-review-f2b", "event_type": "review", "created_at": CREATED,
            "actor": ACTOR, "agent_slot": ACTOR, "node_id": NODE, "class_id": CLASS_ID, "gate": GATE,
            "target_id": NODE, "reviewer": ACTOR, "artifact": "schemas/af_scc_c0_vacuum.yaml",
            "artifact_sha256": f2b_pin, "verdict": "revise", "score": 3.0,
            "hard_failures": report["hard_failures"],
            "findings": "Independent vocab-binding audit at F2b rev12 55d0a1ea9bda (frozen pin match, canonical F0 rev5 0abb9ed8a961, alias companion 46cd9f1e, consistency evidence 9e335e9b). Class semantics pass: the conclusion token canonicalises to exactly one class (scc_c0_future_inextendibility), family SCC, I+ not in conclusion, C0=>C2 one-way row present with no converse entailment. Binding fails literally and is why the verdict is revise: (1) the declared conclusion token scc_c0_future_inextendibility is not in the bound F0 field_vocabulary.conclusion_type.allowed list (which holds only strong_cosmic_censorship_C0), (2) genericity.kind residual_comeager is not in the F0 genericity_kind allowed list (provisional_baire_residual), (3) F2b does not reference artifacts/formulation/VOCAB_ALIASES.json anywhere, so the alias equivalence that would resolve (1) and (2) is unbound at the artifact level, and (4) f0_binding.consistency_evidence_sha256 cites 675a99d0d25b while disk and FROZEN rev28 pin 9e335e9ba1bf (corroborates worker-092). No class merge, no conclusion inflation, no C2/WCC leakage was measured.",
            "independence": {
                "reviewer_is_author": False,
                "same_model_family": True,
                "conflict_note": "worker-005 and the F2b author deepseek-flash-05 are both DeepSeek Flash slots; this is an advisory class-bound audit, not the independent accept G-FORM requires",
            },
            "evidence_refs": [
                f"artifacts/worker-005/f2b_vocab_binding/report.json#{h['report'][:12]}",
                f"schemas/af_scc_c0_vacuum.yaml#{f2b_pin[:12]}",
                f"research_map/formulation_taxonomy.yaml#{f0_pin[:12]}",
                f"artifacts/formulation/VOCAB_ALIASES.json#{al_pin[:12]}",
                f"artifacts/formulation/FROZEN.json#{frozen_sha[:12]}",
            ],
        },
        {
            "event_id": f"{EV}-claim-vocab", "event_type": "claim", "created_at": CREATED,
            "actor": ACTOR, "agent_slot": ACTOR, "node_id": NODE, "class_id": CLASS_ID, "gate": GATE,
            "conclusion_type": "measurement",
            "statement": (
                f"At the measured instant {report['measured_at']} the class-bound vocabulary of schemas/af_scc_c0_vacuum.yaml "
                f"(sha256 {f2b_pin}) is literally outside the field_vocabulary of the F0 artifact it binds "
                f"(research_map/formulation_taxonomy.yaml sha256 {f0_pin}): conclusion.conclusion_type "
                "'scc_c0_future_inextendibility' is not in conclusion_type.allowed "
                "['weak_cosmic_censorship','strong_cosmic_censorship_C2','strong_cosmic_censorship_C0'], and "
                "genericity.kind 'residual_comeager' is not in genericity_kind.allowed "
                "['baire_residual','dense_open','measure_one','provisional_baire_residual','unresolved']. "
                "The frozen companion artifacts/formulation/VOCAB_ALIASES.json (sha256 " + al_pin + ") declares the F2b "
                "tokens canonical and the F0 tokens their accepted aliases, so the two vocabularies are equivalent for "
                "consistency checks only, but F2b contains no reference to that companion at any path or sha256, so the "
                "equivalence is unbound inside the class artifact. Ancillary evidence defect: f0_binding."
                "consistency_evidence_sha256 cites 675a99d0d25b2b37 while disk and FROZEN rev28 both pin "
                f"{ce_pin}. Class semantics measured clean: the token canonicalises to exactly one class (C0), family SCC, "
                "I+ not in conclusion, and the C0=>C2 one-way entailment matches F0 T1/X1 with no converse entailment."
            ),
            "assumptions": [
                "the pins in this claim are instant-bound; any write to F2b, F0, VOCAB_ALIASES.json or taxonomy_consistency.json after the measured instant makes this measurement historical",
                "FROZEN.json revision 28 is the freeze authority and its pin for schemas/af_scc_c0_vacuum.yaml matches the measured bytes",
                "the alias policy 'canonical token first; accepted aliases are equivalent for consistency checks only' is the intended cross-artifact vocabulary rule",
                "a checker that consumes only the two artifacts F2b binds (F0 + F2b) has no way to resolve the token, which is what makes the defect machine-visible even though the semantics are equivalent",
            ],
            "falsifier": report["falsifier"],
            "evidence_refs": [
                f"artifacts/worker-005/f2b_vocab_binding/report.json#{h['report'][:12]}",
                f"artifacts/worker-005/f2b_vocab_binding/check_f2b_vocab_binding.py#{h['checker'][:12]}",
                f"schemas/af_scc_c0_vacuum.yaml#{f2b_pin[:12]}",
                f"research_map/formulation_taxonomy.yaml#{f0_pin[:12]}",
                f"artifacts/formulation/VOCAB_ALIASES.json#{al_pin[:12]}",
                f"artifacts/formulation/evidence/taxonomy_consistency.json#{ce_pin[:12]}",
            ],
        },
        {
            "event_id": f"{EV}-blocker-vocab", "event_type": "blocker", "created_at": CREATED,
            "actor": ACTOR, "agent_slot": ACTOR, "node_id": NODE, "class_id": CLASS_ID, "gate": GATE,
            "description": (
                "F2b (AF-SCC-C0-VAC-GEN) cannot close a binding verdict on class vocabulary at rev12 55d0a1ea9bda: "
                "its declared conclusion_type and genericity.kind use the VOCAB_ALIASES canonical tokens while the "
                "bound F0 rev5 allowed-lists carry only the alias forms, and F2b binds no reference to "
                "artifacts/formulation/VOCAB_ALIASES.json; additionally f0_binding.consistency_evidence_sha256 is "
                "stale (675a99d0d25b2b37 vs 9e335e9ba1bfcf77 on disk and in FROZEN rev28). Class semantics are NOT "
                "blocked: separation, single-class resolution and the C0=>C2 direction all pass."
            ),
            "needed_to_unblock": (
                "owner of record lead-formulation / author deepseek-flash-05: choose ONE vocabulary source for F2b and bind it. "
                "(a) Add the alias-file canonical tokens scc_c0_future_inextendibility and residual_comeager to F0 "
                "field_vocabulary allowed-lists (or switch F2b to the F0 alias forms strong_cosmic_censorship_C0 / "
                "provisional_baire_residual), AND (b) either register artifacts/formulation/VOCAB_ALIASES.json in "
                "f0_binding with its measured sha256 so the equivalence is bound, or make the chosen tokens literal members "
                "of the bound F0 lists, AND (c) refresh f0_binding.consistency_evidence_sha256 to the FROZEN rev28 pin "
                "9e335e9ba1bfcf77. Then re-run the checker; P4/P5/P6/P9 must flip to pass."
            ),
            "next_falsifier": "python3 artifacts/worker-005/f2b_vocab_binding/check_f2b_vocab_binding.py --report; if P4, P5, P6 or P9 still fail, or any pin drifts, this blocker stands",
            "evidence_refs": [
                f"artifacts/worker-005/f2b_vocab_binding/report.json#{h['report'][:12]}",
                f"artifacts/worker-005/f2b_vocab_binding/SCAN.md#{h['scan'][:12]}",
                f"schemas/af_scc_c0_vacuum.yaml#{f2b_pin[:12]}",
                f"research_map/formulation_taxonomy.yaml#{f0_pin[:12]}",
                f"artifacts/formulation/VOCAB_ALIASES.json#{al_pin[:12]}",
                f"artifacts/formulation/evidence/taxonomy_consistency.json#{ce_pin[:12]}",
            ],
        },
    ]

    seen = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                seen.add(json.loads(line).get("event_id"))
    new = [e for e in ev if e["event_id"] not in seen]
    for e in new:
        validate(e)

    checkpoint = {
        "schema": "worker-checkpoint/v1",
        "checkpoint_id": f"w005-f2b-vocab-binding-{report['measured_at']}",
        "agent": ACTOR, "slot": "005", "task_id": TASK,
        "class_id": CLASS_ID, "node_id": NODE, "gate": GATE,
        "task_source": "no inbox card exists for worker-005 (instance worker-005-20260912T003452-968807); one bounded class-bound task taken from map and comms",
        "measured_at": report["measured_at"],
        "pins": pins,
        "deliverables": {
            "artifacts/worker-005/f2b_vocab_binding/check_f2b_vocab_binding.py": h["checker"],
            "artifacts/worker-005/f2b_vocab_binding/report.json": h["report"],
            "artifacts/worker-005/f2b_vocab_binding/selftest.json": h["selftest"],
            "artifacts/worker-005/f2b_vocab_binding/SCAN.md": h["scan"],
        },
        "verdict": report["verdict"],
        "hard_failures": report["hard_failures"],
        "controls": {"baseline_matches_expected": st["baseline_matches_expected"],
                     "mutants_all_pass": st["mutants_all_pass"],
                     "all_checks_discriminated": st["all_checks_discriminated"]},
        "outbox_events": [e["event_id"] for e in ev],
        "not_blocked": "class separation P3/P7/P8 pass; no C2/WCC merge or conclusion inflation measured",
        "next_falsifier": "re-run the checker after the owner repair; P4/P5/P6/P9 must flip to pass or the blocker stands",
        "authority": "worker checkpoint; cannot set node status=done, validation_status=passed, or a gate verdict",
        "written_at": CREATED,
    }
    STATE.mkdir(parents=True, exist_ok=True)
    ck = STATE / "worker-005_f2b_vocab_binding_checkpoint.json"
    ck.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
    ck_sha = sha(ck)

    closing = {
        "event_id": f"{EV}-status-exit", "event_type": "status", "created_at": CREATED,
        "actor": ACTOR, "agent_slot": ACTOR, "node_id": NODE, "class_id": CLASS_ID, "gate": GATE,
        "status": "active", "hours": 0.15,
        "summary": (
            f"One bounded class-bound task complete; checkpointed; exiting cleanly. Task {TASK} (AF-SCC-C0-VAC-GEN / F2b / G-FORM): "
            f"independent vocab-binding audit at frozen rev12 F2b {f2b_pin[:12]} against F0 rev5 {f0_pin[:12]} and VOCAB_ALIASES {al_pin[:12]}. "
            "Deliverables artifacts/worker-005/f2b_vocab_binding/ (checker with 9/9 mutants caught and both degenerate controls differing from baseline, "
            "report.json, selftest.json, SCAN.md). Verdict literal_vocab_binding_fail__no_class_leakage: P4/P5 literal token membership fail, "
            "P6 alias companion unbound, P9 consistency-evidence pin stale; P3/P7/P8 pass. Worker cannot set status=done, validation_status=passed, "
            "or gate verdicts; events await controller ingest."
        ),
        "evidence_refs": [
            f"runtime/state/worker-005_f2b_vocab_binding_checkpoint.json#{ck_sha[:12]}",
            f"artifacts/worker-005/f2b_vocab_binding/report.json#{h['report'][:12]}",
            f"artifacts/worker-005/f2b_vocab_binding/check_f2b_vocab_binding.py#{h['checker'][:12]}",
            f"artifacts/worker-005/f2b_vocab_binding/selftest.json#{h['selftest'][:12]}",
            f"artifacts/worker-005/f2b_vocab_binding/SCAN.md#{h['scan'][:12]}",
        ],
        "next_falsifier": "re-run the checker after the owner repair; P4/P5/P6/P9 must flip to pass or the blocker stands",
    }
    validate(closing)
    new.append(closing)

    with OUTBOX.open("a") as fh:
        for e in new:
            fh.write(json.dumps(e, sort_keys=True, ensure_ascii=False) + "\n")

    print(json.dumps({"appended_events": [e["event_id"] for e in new],
                      "checkpoint": str(ck), "checkpoint_sha256": ck_sha,
                      "deliverables": h}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
