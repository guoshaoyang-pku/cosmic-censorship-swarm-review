#!/usr/bin/env python3
"""Deterministic, idempotent emitter for W078-F0-SET-STRENGTH-ADJ-01.

Writes one JSON object per line to comms/outbox/worker-078.jsonl and nothing else.
Event ids are fixed (wall-clock independent); re-running appends only missing ids.
Every event is validated against research_map/schemas.validate_event before writing,
so no line can land in comms/rejected.jsonl.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, "research_map"))
from schemas import validate_event  # noqa: E402

OUTBOX = os.path.join(ROOT, "comms", "outbox", "worker-078.jsonl")
BUNDLE = "artifacts/worker-078/f0_set_strength_adjudication"
STAMP = "2026-09-12T01:06:00+08:00"
EID = "w078-f0set-20260912T0106"
PIN = "research_map/formulation_taxonomy.yaml#0abb9ed8a961"


def sha(rel: str) -> str:
    h = hashlib.sha256()
    with open(os.path.join(ROOT, rel), "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def build() -> list:
    h_script = sha(f"{BUNDLE}/adjudicate_f0_set_strength.py")
    h_report = sha(f"{BUNDLE}/report.json")
    h_rerun = sha(f"{BUNDLE}/report_rerun.json")
    h_controls = sha(f"{BUNDLE}/controls.json")
    h_readme = sha(f"{BUNDLE}/README.md")
    h_sums = sha(f"{BUNDLE}/snapshot/SHA256SUMS.txt")
    h_ckpt = sha("runtime/state/w078_checkpoint_7_f0_set_strength.json")
    ev = []
    ev.append({
        "event_id": f"{EID}-task-claim", "event_type": "status", "created_at": STAMP, "actor": "worker-078",
        "node_id": "F0", "status": "active", "hours": 0.6, "task_id": "W078-F0-SET-STRENGTH-ADJ-01",
        "class_id": "AF-WCC-VAC-GEN", "gate": "G-F0",
        "summary": ("No assignment card in comms/inbox/worker-078.jsonl. Took ONE bounded class-bound task: independent "
                    "adjudication of the SET-variant strength direction in the G-F0-passed frozen F0 taxonomy, after "
                    "W099-FORM-DIRECTION-CENSUS-01 flagged research_map/formulation_taxonomy.yaml:200 INVERTED and left it "
                    "unadjudicated. Method: pin-then-verify, entailment engine on the artifacts' own causal-order axioms "
                    "(exhaustive finite models + omega-chain witness), mention-aware clause census, drift-voiding binding. "
                    "Read-only on canonical paths."),
        "evidence_refs": [PIN, "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json#64b8d6394a04",
                          "artifacts/formulation/VARIANT_REGISTRY.json#6bac9adea19e",
                          "artifacts/worker-076/gform_strictness_reconcile/probe_result.json#3707d6e1e96c"],
        "next_falsifier": ("Any pinned input drifts (voids the binding), or a model satisfies SET while failing SINGLEQ, "
                           "or the omega-chain escape check fails, or either canonical clause is shown non-assertive."),
    })
    for eid, atype, rel, h, note in [
        ("artifact-harness", "verifier_code", f"{BUNDLE}/adjudicate_f0_set_strength.py", h_script,
         "Deterministic entailment engine + mention-aware census + 4 fixture controls + drift-voiding pin harness."),
        ("artifact-report", "audit_report", f"{BUNDLE}/report.json", h_report,
         "Primary evidence: verdict revise; L1/L2 0 violations; omega-chain separation; two ASSERTIVE_INVERTED canonical clauses."),
        ("artifact-rerun", "audit_report", f"{BUNDLE}/report_rerun.json", h_rerun,
         "Byte-identical re-execution at the same --generated-at (cmp clean)."),
        ("artifact-controls", "controls", f"{BUNDLE}/controls.json", h_controls,
         "4/4 fixture controls pass; entailment controls: 0 violations, omega separated, naive-truncation artefact detected."),
        ("artifact-readme", "summary", f"{BUNDLE}/README.md", h_readme,
         "Method, lemmas, clause table, G-F0 option costs, falsifier, limits."),
        ("artifact-snapshot", "artifact_snapshot", f"{BUNDLE}/snapshot/SHA256SUMS.txt", h_sums,
         "Byte-exact pinned copies of all 8 inputs with sha256."),
        ("artifact-checkpoint", "checkpoint", "runtime/state/w078_checkpoint_7_f0_set_strength.json", h_ckpt,
         "Worker checkpoint: task, result, pins, controls, artifacts, event ids, non-claims, falsifier."),
    ]:
        ev.append({
            "event_id": f"{EID}-{eid}", "event_type": "artifact", "created_at": STAMP, "actor": "worker-078",
            "node_id": "F0", "class_id": "AF-WCC-VAC-GEN", "gate": "G-F0",
            "task_id": "W078-F0-SET-STRENGTH-ADJ-01",
            "artifact_type": atype, "path": rel, "sha256": h, "validation_status": "unverified", "note": note,
            "evidence_refs": [PIN, f"{rel}#{h[:12]}"],
        })
    ev.append({
        "event_id": f"{EID}-claim-direction", "event_type": "claim", "created_at": STAMP, "actor": "worker-078",
        "node_id": "F0", "class_id": "AF-WCC-VAC-GEN", "gate": "G-F0",
        "task_id": "W078-F0-SET-STRENGTH-ADJ-01", "conclusion_type": "counterexample",
        "statement": ("At the pinned bytes, the single-q TAIL visibility predicate (F1 rev13 class predicate) entails the "
                      "SET/union reading and not conversely: the omega-chain x_i<=q_j iff i<=j satisfies SET with no single q "
                      "covering any tail. Hence the SET/union reading is strictly WEAKER. The canonical F0 taxonomy asserts "
                      "the inverse at variants[0].definition:94-95 and in AF-WCC-VAC-GEN.conclusion.text:200; :94-95 is "
                      "additionally self-contradictory because its own gloss is the contrapositive that proves the inverse."),
        "assumptions": ["<= is reflexive and transitive and J^-(q)={x:x<=q}; gamma is a causal chain",
                        "the artifacts' own definitions of SINGLEQ (F1 rev13) and SET (variant registry) are the subjects",
                        "pins bind only the measured sha256 values recorded in report.json"],
        "falsifier": ("A model satisfying SET and failing SINGLEQ; a finite chain separating them; a failed omega escape "
                      "check; a non-assertive reading of :94-95/:200; or pin drift."),
        "artifact_refs": [f"{BUNDLE}/report.json#{h_report[:12]}", f"{BUNDLE}/adjudicate_f0_set_strength.py#{h_script[:12]}",
                          f"{BUNDLE}/snapshot/SHA256SUMS.txt#{h_sums[:12]}"],
        "evidence_refs": [PIN, "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
                          "artifacts/formulation/VARIANT_REGISTRY.json#6bac9adea19e",
                          "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json#64b8d6394a04",
                          f"{BUNDLE}/report.json#{h_report[:12]}"],
    })
    ev.append({
        "event_id": f"{EID}-review-f0-set-strength", "event_type": "review", "created_at": STAMP, "actor": "worker-078",
        "reviewer": "worker-078", "node_id": "F0", "class_id": "AF-WCC-VAC-GEN", "gate": "G-F0",
        "task_id": "W078-F0-SET-STRENGTH-ADJ-01",
        "target_id": f"{PIN}#set-strength-clauses-94-95-200",
        "reviewed_sha256": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
        "verdict": "revise", "score": 3.0,
        "hard_failures": ["W078-F0SET-1 research_map/formulation_taxonomy.yaml:200 asserts SET strictly stronger (inverted)",
                          "W078-F0SET-2 research_map/formulation_taxonomy.yaml:94-95 label contradicts its own gloss (self-inconsistent)"],
        "findings": [
            "L1 SINGLEQ=>SET 0/38664 violations; L2 SET=>SINGLEQ 0 violations on all finite chains; L3 omega-chain separation machine-checked (240/240 escapes, stable N=8/16/32). The SET/union reading is strictly weaker.",
            "Clause census: canonical :94-95 and :198-202 ASSERTIVE_INVERTED; authoring mirror :174-178 is a historical D1 ledger record (MENTION_HISTORICAL).",
            "Cross-artifact: F1 rev13, VARIANT_REGISTRY.json 6bac9ade and the registered SET delta 64b8d639 all state the corrected direction; canonical F0 is the sole outlier and contradicts its own variants block.",
            "G-F0 impact recorded as two costed options (erratum vs repair + FROZEN rev30 + re-acceptance); no claim that G-F0 must be re-opened.",
            "Scope: strength-direction semantics only; physical admissibility of the omega-chain family is outside this verdict (worker-076's open obligation). No gate verdict, no node status."],
        "evidence_refs": [PIN, f"{BUNDLE}/report.json#{h_report[:12]}", f"{BUNDLE}/report_rerun.json#{h_rerun[:12]}",
                          f"{BUNDLE}/controls.json#{h_controls[:12]}", "artifacts/formulation/VARIANT_REGISTRY.json#6bac9adea19e",
                          "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json#64b8d6394a04"],
        "falsifier": ("See report.json falsifier (a)-(f). Falsified by any SET-without-SINGLEQ model, by a finite-chain "
                      "separation, or by showing either canonical clause non-assertive at the pinned hash."),
        "counts_toward_gate_accept": False,
        "scope_note": ("Worker advisory review of clauses inside a frozen, already-passed gate; sets no verdict on G-F0 "
                       "and does not re-open it."),
    })
    ev.append({
        "event_id": f"{EID}-blocker-gf0-disposition", "event_type": "blocker", "created_at": STAMP, "actor": "worker-078",
        "node_id": "F0", "class_id": "AF-WCC-VAC-GEN", "gate": "G-F0",
        "task_id": "W078-F0-SET-STRENGTH-ADJ-01",
        "description": ("The G-F0-passed frozen canonical taxonomy carries two operative clauses asserting the inverted "
                        "SET strength direction (:94-95 and :200), the first self-contradictory. Confirming pieces say the "
                        "opposite direction. Repair moves the hash and, by the recorded controller rule, voids G-F0; the "
                        "erratum path preserves the pass but leaves a false strength relation in the frozen taxonomy."),
        "needed_to_unblock": ("A controller disposition: OPT-A erratum/finding on the frozen hash, or OPT-B repair "
                              "(:94-95, :200 -> 'strictly weaker') with FROZEN rev30 and G-F0 re-acceptance. Minimal repair "
                              "text and both costed options are in report.json gate_impact."),
        "evidence_refs": [PIN, f"{BUNDLE}/report.json#{h_report[:12]}",
                          "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json#64b8d6394a04",
                          "artifacts/formulation/VARIANT_REGISTRY.json#6bac9adea19e"],
    })
    ev.append({
        "event_id": f"{EID}-status-final", "event_type": "status", "created_at": STAMP, "actor": "worker-078",
        "node_id": "F0", "status": "done", "hours": 0.6, "task_id": "W078-F0-SET-STRENGTH-ADJ-01",
        "class_id": "AF-WCC-VAC-GEN", "gate": "G-F0",
        "summary": ("W078-F0-SET-STRENGTH-ADJ-01 complete at worker level (completion claim only; not a node transition and "
                    "not a gate verdict). One class-bound task delivered: the SET/union reading is strictly weaker than the "
                    "single-q tail predicate (L1/L2 exhaustive, L3 omega witness), and the frozen canonical F0 taxonomy "
                    "asserts the inverse at :94-95 and :200, with :94-95 self-contradictory. 4/4 fixture controls, byte-identical "
                    "rerun, zero pin drift. Canonical artifacts untouched; G-F0 not re-opened; worker exits now."),
        "evidence_refs": [PIN, f"{BUNDLE}/report.json#{h_report[:12]}", f"{BUNDLE}/controls.json#{h_controls[:12]}",
                          f"{BUNDLE}/README.md#{h_readme[:12]}", f"{BUNDLE}/snapshot/SHA256SUMS.txt#{h_sums[:12]}"],
        "next_falsifier": ("Re-run adjudicate_f0_set_strength.py at the same pins: any SET-without-SINGLEQ model, any "
                           "finite-chain separation, a failed omega escape check, a non-assertive reading of :94-95/:200, or "
                           "pin drift falsifies the verdict (drift voids the binding)."),
        "artifact": f"{BUNDLE}/", "completion_scope": "worker lifecycle only; not a node done / gate verdict",
        "node_status_effect": "none",
    })
    return ev


def main() -> int:
    events = build()
    existing = set()
    if os.path.exists(OUTBOX):
        for line in open(OUTBOX, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                pass
    todo = [e for e in events if e["event_id"] not in existing]
    for e in todo:
        validate_event(e)  # fail closed before writing anything
    with open(OUTBOX, "a", encoding="utf-8") as f:
        for e in todo:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"emitted {len(todo)}/{len(events)} events to {os.path.relpath(OUTBOX, ROOT)}; "
          f"{len(events) - len(todo)} already present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
