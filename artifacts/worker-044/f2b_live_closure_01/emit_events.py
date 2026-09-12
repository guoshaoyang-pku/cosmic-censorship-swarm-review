#!/usr/bin/env python3
"""Emit W044-F2B-LIVE-CLOSURE-01 outbox events (idempotent: skips event_ids already in the outbox).

Writes only comms/outbox/worker-044.jsonl (append). Worker events cannot set node status,
validation_status=passed or a gate verdict.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
D = Path(__file__).resolve().parent
OUT = REPO / "comms/outbox/worker-044.jsonl"
NOW = datetime.now().astimezone().isoformat(timespec="seconds")
TASK = "W044-F2B-LIVE-CLOSURE-01"
NODE, CLASS, GATE = "F2b", "AF-SCC-C0-VAC-GEN", "G-FORM"
C0_PIN = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
FROZEN_PIN = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"


def sha(rel: Path) -> str:
    return hashlib.sha256(rel.read_bytes()).hexdigest()


def ref(rel: str, n: int = 12) -> str:
    return f"{rel}#{sha(REPO / rel)[:n]}"


report = ref("artifacts/worker-044/f2b_live_closure_01/report.json")
summary = ref("artifacts/worker-044/f2b_live_closure_01/closure_summary.json")
prereg = ref("artifacts/worker-044/f2b_live_closure_01/PREREGISTRATION.json")
readme = ref("artifacts/worker-044/f2b_live_closure_01/README.md")
harness = ref("artifacts/worker-044/f2b_live_closure_01/live_closure.py")
adj = ref("artifacts/worker-044/f2b_live_closure_01/adjudicate.py")
ckpt = ref("runtime/state/w044_f2b_live_closure_01_checkpoint.json")
frozen = f"artifacts/formulation/FROZEN.json#{FROZEN_PIN[:12]}"
c0 = f"schemas/af_scc_c0_vacuum.yaml#{C0_PIN[:12]}"
s = json.loads((D / "closure_summary.json").read_text())

FALSIFIER = (
    "FALSIFIED IF any of: (a) re-running live_closure.py on the same pinned bytes yields a different "
    "snapshot status for any check; (b) any of K1-K8 fails to flip its target check; (c) the "
    "pre-registered prediction disagrees with the measured matrix on any of the eight checks; "
    "(d) verify_frozen or any structural gate is nonzero at the measured pins; (e) SEP-6 is ok at the "
    "measured pins; (f) H1H2 or A2 or A6 passes at the measured pins (each refutes the blocking "
    "decision); or (g) any pinned input differed from its recorded sha256 at snapshot time. Drift "
    "after the snapshot voids live applicability, not the snapshot measurement."
)

events = [
    {
        "event_id": "w044-20260912T0104-liveclosure-status",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-044",
        "agent_slot": "044",
        "node_id": NODE,
        "class_id": CLASS,
        "class_ids": [CLASS],
        "gate": GATE,
        "task_id": TASK,
        "status": "active",
        "node_status_effect": "none",
        "hours": 0.35,
        "summary": (
            "Took ONE bounded class-bound task with no inbox card: W044-F2B-LIVE-CLOSURE-01, a "
            "pre-registered read-only closure re-probe of F2b at the post-REC-12 pins. Snapshot "
            "2026-09-12T01:00:24+08:00, C0 b2ab6acb2bbe / FROZEN rev29 815e08079aef. Measured: "
            "H1H2 fail (false containment denial + inverted size premise), A1 pass, A2 fail "
            "(495-byte evidence pins neither input), A6 fail (alias registry unbound), SEP-6 stale "
            "(aggregator pins 1bb78ce9/b6123750 vs disk b2ab6acb/e9a27996), structural gates 0/0/0, "
            "verify_frozen 0 problems/50 files, mirrors equal. Decision F2B_BLOCKED_AT_MEASURED_PINS; "
            "8/8 pre-registered predictions matched, 0 mismatches; K1-K8 all discriminate; the "
            "re-composed R1-R9 candidate is acceptance-ready on the live base in sandbox. Worker "
            "measurement only: no gate verdict, node status or validation_status."
        ),
        "evidence_refs": [report, summary, prereg, readme, harness, adj, ckpt, c0, frozen],
        "next_falsifier": FALSIFIER,
    },
    {
        "event_id": "w044-20260912T0104-liveclosure-claim",
        "event_type": "claim",
        "created_at": NOW,
        "actor": "worker-044",
        "agent_slot": "044",
        "node_id": NODE,
        "class_id": CLASS,
        "class_ids": [CLASS],
        "gate": GATE,
        "task_id": TASK,
        "conclusion_type": "formal_model",
        "counts_as_full_schema_verdict": False,
        "counts_as_gate_accept": False,
        "statement": (
            "Instrument-and-binding measurement, not a mathematics or physics claim. At the "
            "hash-pinned post-repair snapshot (C0 b2ab6acb2bbe canonical==authoring, C2 e9a27996dfd3, "
            "F1 d9cebb9404b2, FROZEN rev29 815e08079aef, evidence 9e335e9ba1bf, aggregator "
            "94562101a816), the declared F2b machine checks give: H1H2 fail, A2 fail, A6 fail, SEP-6 "
            "stale, while A1/A3/A4b/A5b/A7/A8 pass, all three structural gates exit 0, verify_frozen "
            "reports 0 problems over 50 files, and the three mirrors are byte-equal. Therefore "
            "astra-life05-evidence-binding-repair (REC-12) closed its four bounded items but did not "
            "close the F2b defect set: a G-FORM r3 accept at b2ab6acb2bbe is not machine-supported, "
            "and the class needs a NEW bounded atomic card covering containment direction, "
            "self-verifying evidence, alias binding and aggregator re-pin. Separately, the R1-R9 "
            "composed candidate rebuilt on this live base passes 9/9 readiness checks, gates 0/0/0, "
            "SEP-6 ok, verify_frozen 0 problems and durability, with K1-K8 all discriminating."
        ),
        "assumptions": [
            "The harness check semantics are those of W044-F2B-REV13-INTEGRATION-01 (byte copy, four "
            "metadata-only patches recorded in PROVENANCE.json).",
            "All measurements are on the pinned/ bytes taken at 01:00:24; live drift immediately after "
            "the snapshot was empty.",
            "The pre-registration in PREREGISTRATION.json was fixed before the probe ran (ordering "
            "evidence: file mtimes and the correction note for the hand-typed created_at).",
            "REC-12 scope is taken from astra-lifecycle-05-decisions.json REC-12: exactly four items, "
            "no class id, hypothesis, conclusion predicate, axis semantics or F0 canonical byte change.",
        ],
        "falsifier": FALSIFIER,
        "artifact_refs": [report, summary, prereg, harness, adj, readme],
        "evidence_refs": [report, summary, prereg, c0, frozen, ckpt],
    },
    {
        "event_id": "w044-20260912T0104-liveclosure-artifact-report",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-044",
        "agent_slot": "044",
        "node_id": NODE,
        "class_id": CLASS,
        "class_ids": [CLASS],
        "gate": GATE,
        "task_id": TASK,
        "artifact_type": "closure_probe_report",
        "path": "artifacts/worker-044/f2b_live_closure_01/report.json",
        "sha256": sha(D / "report.json"),
        "validation_status": "unverified",
        "evidence_refs": [report, prereg, harness],
        "falsifier": FALSIFIER,
        "note": "Full snapshot matrix, pins, composed column, K1-K8 controls, durability, closure scan, live drift.",
    },
    {
        "event_id": "w044-20260912T0104-liveclosure-artifact-summary",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-044",
        "agent_slot": "044",
        "node_id": NODE,
        "class_id": CLASS,
        "class_ids": [CLASS],
        "gate": GATE,
        "task_id": TASK,
        "artifact_type": "closure_summary",
        "path": "artifacts/worker-044/f2b_live_closure_01/closure_summary.json",
        "sha256": sha(D / "closure_summary.json"),
        "validation_status": "unverified",
        "evidence_refs": [summary, report, prereg],
        "falsifier": FALSIFIER,
        "note": "Prediction-vs-measurement adjudication: decision F2B_BLOCKED_AT_MEASURED_PINS, 0 mismatches, evidence hashes.",
    },
    {
        "event_id": "w044-20260912T0104-liveclosure-artifact-prereg",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-044",
        "agent_slot": "044",
        "node_id": NODE,
        "class_id": CLASS,
        "class_ids": [CLASS],
        "gate": GATE,
        "task_id": TASK,
        "artifact_type": "preregistration",
        "path": "artifacts/worker-044/f2b_live_closure_01/PREREGISTRATION.json",
        "sha256": sha(D / "PREREGISTRATION.json"),
        "validation_status": "unverified",
        "evidence_refs": [prereg, summary, report],
        "falsifier": "Falsified if the file is shown not to predate the probe run, or if any prediction/basis value was edited after measurement (the created_at correction note documents the only edit).",
        "note": "Prediction, basis hashes, decision question and falsifier fixed before the probe; created_at corrected to the true file time with a note.",
    },
    {
        "event_id": "w044-20260912T0104-liveclosure-artifact-harness",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-044",
        "agent_slot": "044",
        "node_id": NODE,
        "class_id": CLASS,
        "class_ids": [CLASS],
        "gate": GATE,
        "task_id": TASK,
        "artifact_type": "verifier",
        "path": "artifacts/worker-044/f2b_live_closure_01/live_closure.py",
        "sha256": sha(D / "live_closure.py"),
        "validation_status": "unverified",
        "evidence_refs": [harness, report, ref("artifacts/worker-044/f2b_live_closure_01/PROVENANCE.json")],
        "falsifier": "Falsified if the script writes outside its own pinned/sandbox/report paths, if it is shown not to be the recorded byte copy plus the four documented metadata patches, or if a re-run on the same pinned bytes changes a check status.",
        "note": "Read-only w.r.t. canonical tree; provenance and patch list in PROVENANCE.json.",
    },
    {
        "event_id": "w044-20260912T0104-liveclosure-artifact-adjudicator",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-044",
        "agent_slot": "044",
        "node_id": NODE,
        "class_id": CLASS,
        "class_ids": [CLASS],
        "gate": GATE,
        "task_id": TASK,
        "artifact_type": "verifier",
        "path": "artifacts/worker-044/f2b_live_closure_01/adjudicate.py",
        "sha256": sha(D / "adjudicate.py"),
        "validation_status": "unverified",
        "evidence_refs": [adj, summary, prereg],
        "falsifier": "Falsified if the adjudicator can emit a non-blocked decision while a blocking family is open, or if it excuses a prediction mismatch instead of recording it.",
        "note": "Fail-closed prediction-vs-measurement adjudicator; decision recomputed from measurement only.",
    },
    {
        "event_id": "w044-20260912T0104-liveclosure-artifact-readme",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-044",
        "agent_slot": "044",
        "node_id": NODE,
        "class_id": CLASS,
        "class_ids": [CLASS],
        "gate": GATE,
        "task_id": TASK,
        "artifact_type": "report_readme",
        "path": "artifacts/worker-044/f2b_live_closure_01/README.md",
        "sha256": sha(D / "README.md"),
        "validation_status": "unverified",
        "evidence_refs": [readme, report, summary, prereg],
        "falsifier": FALSIFIER,
        "note": "Method, ordering table, measured matrix, REC-12 scope, composed column, falsifier, non-claims, credit.",
    },
    {
        "event_id": "w044-20260912T0104-liveclosure-review",
        "event_type": "review",
        "created_at": NOW,
        "actor": "worker-044",
        "agent_slot": "044",
        "node_id": NODE,
        "class_id": CLASS,
        "class_ids": [CLASS],
        "gate": GATE,
        "task_id": TASK,
        "target_id": f"schemas/af_scc_c0_vacuum.yaml#{C0_PIN[:12]}",
        "reviewer": "worker-044",
        "verdict": "revise",
        "score": 3.5,
        "counts_as_full_schema_verdict": False,
        "counts_as_gate_accept": False,
        "hard_failures": [
            "H1_false_containment_denial",
            "H2_inverted_size_premise",
            "A2_evidence_not_self_verifying",
            "A6_alias_registry_unbound",
            "SEP6_aggregator_component_pins_stale",
        ],
        "findings": [
            "Advisory machine-check verdict at the measured hash b2ab6acb2bbe, not a blind review; "
            "counts_as_full_schema_verdict=false so it must not be counted toward the two-independent-"
            "accepts criterion.",
            "H1: regularity.must_not_conflate[0] denies a containment the same file declares "
            "(E_C0 contains E_H2loc).",
            "H2: implication_ledger.forbidden_transfers H2_loc reason 'the converse containment is "
            "false', with the adjacent entry asserting C2 is strictly larger, against the file's own "
            "rank order C0 > H2loc > C1,1 > C2.",
            "A2: the declared 495-byte evidence document pins neither input it evaluated.",
            "A6: no path+sha256 binding for VOCAB_ALIASES.json.",
            "SEP-6: aggregator pins C0 1bb78ce9b357 / C2 b6123750b37d against disk b2ab6acb2bbe / "
            "e9a27996dfd3.",
            "Non-blocking checks pass: A1, A3, A4b, A5b, A7, A8, all three structural gates exit 0, "
            "verify_frozen 0 problems/50 files, mirrors byte-equal.",
        ],
        "evidence_refs": [report, summary, c0, frozen],
        "falsifier": FALSIFIER,
    },
    {
        "event_id": "w044-20260912T0104-liveclosure-blocker",
        "event_type": "blocker",
        "created_at": NOW,
        "actor": "worker-044",
        "agent_slot": "044",
        "node_id": NODE,
        "class_id": CLASS,
        "class_ids": [CLASS],
        "gate": GATE,
        "task_id": TASK,
        "description": (
            "F2b remains blocked at the landed rev13/rev29 pins after REC-12. Five machine-checkable "
            "families are open: H1 false containment denial and H2 inverted size premise in C0 "
            "(canonical and authoring); A2 the declared consistency evidence is the lean 495-byte "
            "9e335e9b document that pins neither input, so REC-12 item 2 closes the declaration pin "
            "but not the binding substance; A6 no alias-registry path+sha256 binding; SEP-6 the "
            "aggregator still pins superseded C0/C2 component hashes. The two containment defects and "
            "A6 are outside REC-12's four authorized items; REC-12 therefore cannot close them."
        ),
        "needed_to_unblock": (
            "A NEW bounded atomic repair card (owner: formulation lead; scope F1,F2a,F2b as needed) "
            "covering, in one revision: (1) the two containment edits (worker-066 patch from "
            "worker-008's finding); (2) restore the self-verifying enriched evidence document and "
            "re-declare it in all three schemas; (3) bind VOCAB_ALIASES.json by path+sha256; "
            "(4) re-pin the F2 aggregator components; (5) regenerate KEY_MANIFEST and FROZEN with "
            "byte-verified pins. The R1-R9 composed candidate in this task's prior report "
            "(artifacts/worker-044/f2b_rev13_integration/, C0 48cadb72e507) is acceptance-ready on "
            "the current live base and can serve as the worked example, subject to owner sign-off."
        ),
        "evidence_refs": [report, summary, readme, ckpt, c0, frozen, ref("schemas/af_scc_regularities.yaml")],
        "next_falsifier": FALSIFIER,
    },
]

existing: set[str] = set()
if OUT.exists():
    for line in OUT.read_text().splitlines():
        try:
            existing.add(json.loads(line)["event_id"])
        except Exception:
            continue
added = []
with OUT.open("a") as f:
    for e in events:
        if e["event_id"] in existing:
            continue
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
        added.append(e["event_id"])
print(json.dumps({"appended": added, "skipped_existing": sorted(existing & {e['event_id'] for e in events})}, indent=1))
