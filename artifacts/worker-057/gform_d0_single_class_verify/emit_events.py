#!/usr/bin/env python3
"""Emit W057-GFORM-D0-SINGLE-CLASS-VERIFY-01 events + checkpoint.

Re-reads report.json, re-verifies every pinned input on disk at emit time, and
appends one status / three artifact / one claim / one blocker event to the
worker's outbox, plus a self-contained checkpoint under runtime/state.

Refuses to emit if a pin moved or the report verdict is not the measured one.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parent
REPO = RUN_DIR.parents[2]
OUTBOX = REPO / "comms/outbox/worker-057.jsonl"
STATE = REPO / "runtime/state"
TZ = timezone(timedelta(hours=8))

report = json.loads((RUN_DIR / "report.json").read_text())
if report["verdict"] != (
    "MEASURED_SHARED_UNION_AND_PARAMETERISED_CONTRACT__NO_SINGLE_FROZEN_TRIPLE"
):
    raise SystemExit(f"refusing to emit: unexpected verdict {report['verdict']!r}")
if not all(c["pass"] for c in report["controls"]):
    raise SystemExit("refusing to emit: a control failed")

# -- re-verify pins at emit time -------------------------------------------
for path, meta in report["inputs"].items():
    if not path.endswith((".yaml", ".json")):
        continue
    got = hashlib.sha256((REPO / path).read_bytes()).hexdigest()
    if got != meta["sha256"]:
        raise SystemExit(f"PIN DRIFT at emit: {path}\n  report {meta['sha256']}\n  disk   {got}")

NOW = datetime.now(TZ).isoformat()
TASK = report["task_id"]
CLASSES = report["class_ids"]
NODES = report["node_id"]
GATE = report["gate"]


def ref(path: str) -> str:
    h = hashlib.sha256((REPO / path).read_bytes()).hexdigest()
    return f"{path}#{h[:12]}"


REPORT_JSON = "artifacts/worker-057/gform_d0_single_class_verify/report.json"
REPORT_MD = "artifacts/worker-057/gform_d0_single_class_verify/REPORT.md"
HARNESS = "artifacts/worker-057/gform_d0_single_class_verify/verify_d0_single_class.py"
SCHEMA_REFS = [
    ref("schemas/af_wcc_vacuum.yaml"),
    ref("schemas/af_scc_c2_vacuum.yaml"),
    ref("schemas/af_scc_c0_vacuum.yaml"),
]
EVID = [ref(REPORT_JSON), ref(REPORT_MD), ref(HARNESS)] + SCHEMA_REFS + [
    ref("research_map/formulation_taxonomy.yaml"),
    ref("artifacts/formulation/FROZEN.json"),
]

# Manifest is written before the events so every evidence_ref above resolves on
# disk.  report.json cannot contain its own hash, so this file is the single
# authoritative hash record for the run; the emitter re-hashes it last.
manifest = {
    "task_id": TASK,
    "actor": "worker-057",
    "created_at": NOW,
    "gate": GATE,
    "node_id": NODES,
    "class_ids": CLASSES,
    "verdict": report["verdict"],
    "controls": {c["id"]: c["pass"] for c in report["controls"]},
    "artifact_sha256": {
        p: hashlib.sha256((REPO / p).read_bytes()).hexdigest()
        for p in (
            REPORT_JSON,
            REPORT_MD,
            HARNESS,
            "artifacts/worker-057/gform_d0_single_class_verify/emit_events.py",
        )
        if (REPO / p).exists()
    },
    "input_sha256": {
        p: m["sha256"]
        for p, m in report["inputs"].items()
        if isinstance(m, dict) and m.get("sha256")
    },
    "criterion_text": report["criterion_text"],
    "verdict_scope": "byte measurement only; no gate verdict, node status or validation_status claimed",
}
MANIFEST = "artifacts/worker-057/gform_d0_single_class_verify/manifest.json"
(REPO / MANIFEST).write_text(
    json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
)
EVID = EVID + [ref(MANIFEST)]

FALSIFIER = (
    "Re-hash schemas/af_wcc_vacuum.yaml (d9cebb9404b2e79e...), "
    "schemas/af_scc_c2_vacuum.yaml (e9a27996dfd3...), "
    "schemas/af_scc_c0_vacuum.yaml (b2ab6acb2bbe...), "
    "research_map/formulation_taxonomy.yaml (0abb9ed8a961...) and "
    "artifacts/formulation/FROZEN.json, then re-run "
    "artifacts/worker-057/gform_d0_single_class_verify/verify_d0_single_class.py. "
    "The report is falsified for those hashes if any pin differs, if any control C1-C7 flips, "
    "if D0_normalized_equal_all_three becomes false or D0 stops being a tagged union over a bare "
    "index, if regularity_class_distinct_block_count_is_1 becomes true (one frozen block appears), "
    "if a definition_ref/symbols block pins a single (s,delta,norm) and registers the other branch "
    "as a variant at a named revision, or if F2a/F2b begin carrying F1's no-transfer declaration. "
    "A moved byte voids the report for the new bytes."
)

STATEMENT = (
    "At the frozen rev-29 pins F1 d9cebb9404b2 / F2a e9a27996dfd3 / F2b b2ab6acb2bbe "
    "(FROZEN.json revision 29, frozen 2026-09-12T00:57:26+08:00), the G-FORM unmet item "
    "'no single frozen data class (s,delta,norm) is shared by F1/F2a/F2b' is measured as follows. "
    "(1) The three schemas share a byte-identical D0 regularity domain: a tagged disjoint union "
    "under a single binder r, r = smooth (smooth-with-decay default) or r = (sobolev,s,delta), "
    "s > 5/2, delta in (1/2,1) - the rev-11/12 bare-disjunction defect is repaired in form. "
    "(2) D0 supplies exactly one complete (s,delta,norm) instantiation (the sobolev branch); the "
    "smooth branch supplies no (s,delta) pair and no normed space. (3) data_class.regularity_class "
    "is not identical across the three schemas: 2 distinct normalized blocks (F2a == F2b, F1 differs), "
    "and F1 alone carries data_class.excluded_data plus the declaration that smooth-data statements "
    "may not be transferred to the Sobolev variant without an approximation/stability argument. "
    "(4) The shared regularity contract is a parameterised family H^s_delta x H^{s-1}_{delta+1} with "
    "ranges, not one frozen numeric point: the norm type is shared, the numeric point is not fixed. "
    "Consequence: on the criterion's literal wording no single frozen (s,delta,norm) is present at "
    "rev 29; on the 'record the divergence' reading the union is a strictly stronger substitute "
    "(forall r in D0), not an equivalent one, and whether that satisfies the criterion is reserved "
    "to the G-FORM owner. All seven pre-registered controls pass. This is a byte measurement, not a "
    "mathematical result and not a gate verdict."
)

events = [
    {
        "event_id": "w057-d0single-20260912T0130-status-start",
        "event_type": "status",
        "actor": "worker-057",
        "created_at": NOW,
        "node_id": NODES,
        "class_id": ";".join(CLASSES),
        "class_ids": CLASSES,
        "gate": GATE,
        "status": "active",
        "task_id": TASK,
        "summary": (
            "Task self-selected from the immediate queue (no card in comms/inbox/worker-057.jsonl): "
            "measure the G-FORM 'single frozen data class (s,delta,norm)' item at the frozen rev-29 "
            "bytes after D0 was retyped as a tagged disjoint union. Read-only instrument, seven "
            "pre-registered controls, no schema modified, no gate verdict claimed."
        ),
        "evidence_refs": EVID[:3],
    },
    {
        "event_id": "w057-d0single-20260912T0130-artifact-report",
        "event_type": "artifact",
        "actor": "worker-057",
        "created_at": NOW,
        "node_id": NODES,
        "class_id": ";".join(CLASSES),
        "class_ids": CLASSES,
        "gate": GATE,
        "task_id": TASK,
        "artifact_type": "deterministic_cross_artifact_measurement",
        "path": REPORT_JSON,
        "sha256": hashlib.sha256((REPO / REPORT_JSON).read_bytes()).hexdigest(),
        "validation_status": "unverified",
        "summary": (
            "Machine report: 15 checks + 7 controls + 5 findings at the rev-29 pins. Verdict "
            "MEASURED_SHARED_UNION_AND_PARAMETERISED_CONTRACT__NO_SINGLE_FROZEN_TRIPLE; "
            "D0-01..D0-04 confirmed, D0-05 reserved to the G-FORM owner. Reviewer input only."
        ),
        "evidence_refs": EVID,
    },
    {
        "event_id": "w057-d0single-20260912T0130-artifact-reportmd",
        "event_type": "artifact",
        "actor": "worker-057",
        "created_at": NOW,
        "node_id": NODES,
        "class_id": ";".join(CLASSES),
        "class_ids": CLASSES,
        "gate": GATE,
        "task_id": TASK,
        "artifact_type": "report_markdown",
        "path": REPORT_MD,
        "sha256": hashlib.sha256((REPO / REPORT_MD).read_bytes()).hexdigest(),
        "validation_status": "unverified",
        "summary": (
            "Human-readable report with the pinned input table, the D0-01..D0-05 finding table, the "
            "changed-vs-rev11/12 section, the reserved adjudication with both precedent directions, "
            "the six-branch falsifier, and the scope statement."
        ),
        "evidence_refs": EVID,
    },
    {
        "event_id": "w057-d0single-20260912T0130-artifact-harness",
        "event_type": "artifact",
        "actor": "worker-057",
        "created_at": NOW,
        "node_id": NODES,
        "class_id": ";".join(CLASSES),
        "class_ids": CLASSES,
        "gate": GATE,
        "task_id": TASK,
        "artifact_type": "independent_verifier",
        "path": HARNESS,
        "sha256": hashlib.sha256((REPO / HARNESS).read_bytes()).hexdigest(),
        "validation_status": "unverified",
        "summary": (
            "Read-only instrument: pin check aborts on any moved byte; re-implements the comparisons "
            "from the YAML bytes instead of calling the author's checkers; every figure has a "
            "pre-registered control. Seven controls, all pass; C2 and C7 caught two over-claims in "
            "the first draft, which was corrected rather than relaxed."
        ),
        "evidence_refs": EVID,
    },
    {
        "event_id": "w057-d0single-20260912T0130-claim",
        "event_type": "claim",
        "actor": "worker-057",
        "created_at": NOW,
        "node_id": NODES,
        "class_id": ";".join(CLASSES),
        "class_ids": CLASSES,
        "gate": GATE,
        "task_id": TASK,
        "conclusion_type": "formal_model",
        "statement": STATEMENT,
        "assumptions": [
            "The five pinned files are the measured hashes in evidence_refs; a moved byte voids this claim for the new bytes.",
            "The gate criterion text is taken verbatim from research_map/research_map.json's G-FORM unmet list, not from a review quoting it.",
            "The smooth branch is read only from the tag-introducing clause of D0 ('r = smooth (the smooth-with-decay default)'); the later revision note that mentions (sobolev,s,delta) and 'Frechet for r = smooth' is not treated as an instantiation (control C6).",
            "A parenthetical '(weighted Sobolev)' annotation is not a different norm; the annotation-stripping rule is pre-registered and controlled (C7).",
            "No semantic correctness, well-posedness or physical fidelity of the class statements is assumed or decided; the measurement is over bytes and declared structure.",
            "Whether a tagged union satisfies a criterion written for a single frozen triple is a class-identity ruling reserved to the G-FORM owner; this claim reports the measurement only.",
        ],
        "falsifier": FALSIFIER,
        "evidence_refs": EVID,
    },
    {
        "event_id": "w057-d0single-20260912T0130-blocker-single-triple",
        "event_type": "blocker",
        "actor": "worker-057",
        "created_at": NOW,
        "node_id": NODES,
        "class_id": ";".join(CLASSES),
        "class_ids": CLASSES,
        "gate": GATE,
        "task_id": TASK,
        "description": (
            "HASH-BOUND, REV 29, MEASURED: G-FORM's item 'no single frozen data class (s,delta,norm) "
            "is shared by F1/F2a/F2b' is not literally instantiated at the frozen rev-29 hashes. "
            "The three schemas do share a byte-identical tagged-union D0 and an equal numeric/space "
            "contract, but (i) D0 supplies only one complete (s,delta,norm) instantiation and the "
            "smooth branch supplies none, so no single triple is frozen; (ii) the shared contract is "
            "the parameterised family H^s_delta x H^{s-1}_{delta+1} over ranges, not one numeric "
            "point; (iii) data_class.regularity_class has 2 distinct normalized blocks and F1 alone "
            "declares that smooth-data statements may not be transferred to the Sobolev variant "
            "without an approximation/stability argument (F1 line 136). The prior rev-11/12 defect "
            "('bare disjunction / family of two class statements') is repaired in form, so this is a "
            "narrower question: whether a union over a bare index satisfies a criterion written for "
            "one frozen triple."
        ),
        "needed_to_unblock": (
            "The G-FORM owner records one of: (a) a ruling that the tagged union over r satisfies the "
            "criterion, with the transfer reading it licenses stated on the union domain; or (b) a "
            "freeze decision at a named revision that instantiates one (s,delta,norm), registers the "
            "other branch as a variant, and re-pins; or (c) an explicit acceptance of the recorded "
            "divergence with the C0=>C2 transfer lemma stated separately on the shared contract. Any "
            "of the three requires no mathematics from this worker."
        ),
        "next_falsifier": FALSIFIER,
        "evidence_refs": EVID,
    },
    {
        "event_id": "w057-d0single-20260912T0130-status-complete",
        "event_type": "status",
        "actor": "worker-057",
        "created_at": NOW,
        "node_id": NODES,
        "class_id": ";".join(CLASSES),
        "class_ids": CLASSES,
        "gate": GATE,
        "task_id": TASK,
        "status": "complete",
        "hours": 0.4,
        "claims_completion": False,
        "summary": (
            "Bounded task complete: instrument written, all 7 controls pass, report emitted, blocker "
            "recorded, no schema modified, no gate verdict claimed. Checkpoint written to "
            "runtime/state/w057_checkpoint_d0single_rev29.json and appended to checkpoint_log.jsonl."
        ),
        "next_falsifier": FALSIFIER,
        "evidence_refs": EVID,
    },
]

with OUTBOX.open("a", encoding="utf-8") as fh:
    for ev in events:
        fh.write(json.dumps(ev, sort_keys=True, ensure_ascii=False) + "\n")

# -- checkpoint -------------------------------------------------------------
ckpt = {
    "agent": "worker-057",
    "task_id": TASK,
    "checkpointed_at": NOW,
    "gate": GATE,
    "node_id": NODES,
    "class_ids": CLASSES,
    "task_state": "complete",
    "claims_completion": False,
    "verdict": report["verdict"],
    "controls_passed": sum(1 for c in report["controls"] if c["pass"]),
    "controls_total": len(report["controls"]),
    "checks_true": sorted(k for k, v in report["checks"].items() if v is True),
    "checks_false": sorted(k for k, v in report["checks"].items() if v is False),
    "findings": [
        {"id": f["id"], "state": f["state"], "statement": f["statement"][:240]}
        for f in report["findings"]
    ],
    "reserved_adjudication": report["reserved_adjudication"]["question"],
    "inputs": {
        p: {"sha256": m["sha256"], "bytes": m["bytes"], "node": m["node"]}
        for p, m in report["inputs"].items()
        if isinstance(m, dict) and m.get("sha256")
    },
    "artifacts": {
        REPORT_JSON: hashlib.sha256((REPO / REPORT_JSON).read_bytes()).hexdigest(),
        REPORT_MD: hashlib.sha256((REPO / REPORT_MD).read_bytes()).hexdigest(),
        HARNESS: hashlib.sha256((REPO / HARNESS).read_bytes()).hexdigest(),
    },
    "emitted_event_ids": [e["event_id"] for e in events],
    "next_falsifier": FALSIFIER,
}
ckpt_path = STATE / "w057_checkpoint_d0single_rev29.json"
ckpt_path.write_text(json.dumps(ckpt, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
with (STATE / "checkpoint_log.jsonl").open("a", encoding="utf-8") as fh:
    fh.write(
        json.dumps(
            {
                "time": NOW,
                "agent": "worker-057",
                "task_id": TASK,
                "state": "complete",
                "verdict": report["verdict"],
                "checkpoint": str(ckpt_path.relative_to(REPO)),
                "claims_completion": False,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )

print(f"appended {len(events)} events to {OUTBOX.relative_to(REPO)}")
print(f"checkpoint -> {ckpt_path.relative_to(REPO)}")
