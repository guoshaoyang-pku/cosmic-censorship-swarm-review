#!/usr/bin/env python3
"""Emit W068-FORM-HELDOUT-09-REPL protocol events + checkpoint.

Validates every event against research_map/schemas.py before appending to
comms/outbox/worker-068.jsonl (one JSON object per line, idempotent by event_id).
Writes runtime/state/w068_checkpoint_repl.json and appends to
runtime/state/w068_checkpoints.jsonl.

Never sets done/passed/gate verdict: validation_status stays "unverified".
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
REPL = ROOT / "artifacts" / "worker-068" / "heldout09r"
OUTBOX = ROOT / "comms" / "outbox" / "worker-068.jsonl"
STATE = ROOT / "runtime" / "state"
CST = timezone(timedelta(hours=8))
TASK_ID = "W068-FORM-HELDOUT-09-REPL"
CORPUS_ID = "FORM-HELDOUT-09"
CLASS_ID = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
NODE = "A1"
GATE = "G-CLASSBIND (folded into G-AUDIT as calibration evidence)"
ACTOR = "worker-068"

sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


ARTIFACTS = [
    ("replication_report.json", "replication_report"),
    ("raw_replication_verdicts.json", "replication_raw_verdicts"),
    ("control_extension_report.json", "control_extension_report"),
    ("replicate_heldout09.py", "replication_harness"),
    ("README.md", "replication_readme"),
    ("controls_ext/c05_comment_prepend.yaml", "conforming_control"),
    ("controls_ext/c06_comment_append_blank_eof.yaml", "conforming_control"),
    ("controls_ext/c07_renamed_identical_copy.yaml", "conforming_control"),
    ("controls_ext/probe_pyyaml_resorted_c0.yaml", "format_probe"),
    ("emit_repl_events.py", "replication_event_emitter"),
]


def main() -> int:
    repl = json.loads((REPL / "replication_report.json").read_text())
    ctrl = json.loads((REPL / "control_extension_report.json").read_text())
    hashes = {rel: sha256_file(REPL / rel) for rel, _ in ARTIFACTS}

    events = []

    events.append({
        "event_id": "w068-hel09r-01-task-claim",
        "event_type": "status",
        "created_at": now(),
        "actor": ACTOR,
        "node_id": NODE,
        "status": "active",
        "hours": 0.2,
        "task_id": TASK_ID,
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "summary": ("No assignment card exists in comms/inbox for worker-068 (third 00:24 fleet). "
                    "Taking one bounded class-bound task: independent replication of FORM-HELDOUT-09 "
                    "(heldout3, FROZEN rev25) plus extension of the conforming-control set from 4 to 7, "
                    "closing the two open items in astra-life03-heldout-09. Measurement only."),
        "evidence_refs": ["artifacts/worker-068/heldout3/manifest.json#sha256:72c0353ad0de",
                          "artifacts/worker-068/heldout3/report.json#sha256:9904e516a9da"],
        "next_falsifier": "Any per-fixture mismatch against the frozen raw verdicts, or content drift in the bound schemas/stages.",
    })

    for i, (rel, kind) in enumerate(ARTIFACTS, start=2):
        events.append({
            "event_id": f"w068-hel09r-{i:02d}-artifact-{kind}",
            "event_type": "artifact",
            "created_at": now(),
            "actor": ACTOR,
            "node_id": NODE,
            "artifact_type": kind,
            "path": f"artifacts/worker-068/heldout09r/{rel}",
            "sha256": hashes[rel],
            "validation_status": "unverified",
            "class_ids": CLASS_IDS,
            "task_id": TASK_ID,
            "gate": GATE,
            "summary": {
                "replication_report": "Replication report: 49 fixtures re-run, 0 mismatches, aggregates exact, controls 7/7, verdict replicated_with_manifest_supersession.",
                "replication_raw_verdicts": "Per-fixture replication verdicts with independent stage parsing and matches_frozen flags.",
                "control_extension_report": "3 added conforming controls accepted by both stages (4 -> 7) + 1 declared format probe accepted.",
                "replication_harness": "Independent replication harness; re-derives all bindings and recomputes aggregates without the original runner.",
                "replication_readme": "Human-readable method, results, supersession note, non-claims, falsifier, reproduction.",
                "conforming_control": "Extended conforming control (semantics-preserving presentational edit); accepted by both stages.",
                "format_probe": "Declared format probe (PyYAML re-serialization), reported separately, not counted as a control.",
                "replication_event_emitter": "Idempotent protocol-event and checkpoint emitter; validates every event against research_map/schemas.py.",
            }[kind],
        })

    events.append({
        "event_id": "w068-hel09r-12-claim",
        "event_type": "claim",
        "created_at": now(),
        "actor": ACTOR,
        "node_id": NODE,
        "task_id": TASK_ID,
        "class_id": CLASS_ID,
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "conclusion_type": "numerical_evidence",
        "statement": ("Independent replication of FORM-HELDOUT-09 at the bound content hashes "
                      "(WCC 9a8bd4c96800, C2 b6123750b37d, C0 1bb78ce9b357, stage A 000e09e46b2f, "
                      "stage B c79d8ab8440a, rule spec 40f9bb9e657b): all 49 fixtures re-run, 0 per-fixture "
                      "verdict/rule mismatches vs the frozen raw_verdicts.json, and the recomputed aggregates "
                      "are identical - union escape 1/35 = 0.02857, stage A 34/35, stage B 33/35, 0 false "
                      "positives. The conforming-control set is extended from 4 to 7 with three "
                      "semantics-preserving presentational controls, all accepted by both stages, and a "
                      "declared PyYAML-resort format probe is also accepted. The single union escape remains "
                      "c0_03_conclusion_negated (C0 conclusion polarity inverted while the C0 token is kept). "
                      "This is a measurement about the pipeline, not a class-truth claim."),
        "assumptions": [
            "The frozen objects under test are the two stage tools at their pinned hashes; replication re-runs them rather than re-implementing them.",
            "Acceptance = stage A verdict pass AND stage B verdict accept; escape = accepted by both.",
            "Extended controls are semantics-preserving by construction (comment, blank line, rename-only).",
            "Harness-independent replication, NOT agent-independent: the corpus was also built by worker-068.",
        ],
        "falsifier": repl["falsifier"],
        "evidence_refs": [
            f"artifacts/worker-068/heldout09r/replication_report.json#sha256:{hashes['replication_report.json'][:12]}",
            f"artifacts/worker-068/heldout09r/raw_replication_verdicts.json#sha256:{hashes['raw_replication_verdicts.json'][:12]}",
            f"artifacts/worker-068/heldout09r/control_extension_report.json#sha256:{hashes['control_extension_report.json'][:12]}",
            "artifacts/worker-068/heldout3/report.json#sha256:9904e516a9da",
            "artifacts/worker-068/heldout3/raw_verdicts.json#sha256:3fe7499bfc12",
        ],
        "artifact_refs": [
            "artifacts/worker-068/heldout09r/replication_report.json",
            "artifacts/worker-068/heldout09r/raw_replication_verdicts.json",
            "artifacts/worker-068/heldout09r/control_extension_report.json",
        ],
        "review_status": "unverified",
        "claims_completion": False,
    })

    sup = repl["manifest_supersession"]
    events.append({
        "event_id": "w068-hel09r-13-blocker",
        "event_type": "blocker",
        "created_at": now(),
        "actor": ACTOR,
        "node_id": NODE,
        "task_id": TASK_ID,
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "description": (
            "(1) Moving-target: artifacts/formulation/FROZEN.json moved from rev25/af24e9c39606 (the pin "
            "recorded by the frozen run, which measured zero drift) to rev26/2554e276a0db at 00:24:49 - an "
            "F0 publication adjudication request. Rev26 still pins the same three class schemas and both "
            "stage tools, so the class-binding measurement's content binding holds; only the manifest-hash "
            "binding is stale. (2) Open class-binding blind spot from w068-hel09-12-blocker-polarity: "
            "c0_03_conclusion_negated (C0 conclusion polarity inverted with the C0 token kept) is still "
            "accepted by both stages at the bound hashes, now independently re-confirmed by this replication."),
        "needed_to_unblock": (
            "For (1): controller/lead decides whether FORM-HELDOUT-09 binds rev25 content hashes (all intact) "
            "or is re-pinned to rev26; no content artifact needs re-measuring. For (2): an independent "
            "reviewer (not worker-068) adjudicates c0_03_conclusion_negated, and either an R11 extension "
            "compares conclusion.statement_formal polarity/content against negation_normal_form or a "
            "documented blind-spot entry is recorded."),
        "evidence_refs": [
            "artifacts/formulation/FROZEN.json#sha256:2554e276a0db",
            "artifacts/formulation/FROZEN.json#rev26_delta",
            f"artifacts/worker-068/heldout09r/replication_report.json#sha256:{hashes['replication_report.json'][:12]}",
            "artifacts/worker-068/heldout3/mutants/c0_03_conclusion_negated.yaml#sha256:1e8898ac7bad",
        ],
        "next_falsifier": ("A rev26-based re-measurement showing schema/stage drift (would invalidate the "
                           "content binding), or a gate revision that rejects c0_03_conclusion_negated."),
        "claims_completion": False,
    })

    events.append({
        "event_id": "w068-hel09r-14-checkpoint",
        "event_type": "status",
        "created_at": now(),
        "actor": ACTOR,
        "node_id": NODE,
        "status": "active",
        "hours": 0.4,
        "task_id": TASK_ID,
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "summary": ("CHECKPOINT 2 (worker-068 replication pass): 49/49 fixtures re-run, 0 mismatches, "
                    "union escape 1/35 reproduced exactly, escape-family list identical, conforming controls "
                    "4 -> 7 all accepted, format probe accepted, FROZEN rev25 -> rev26 supersession recorded."),
        "evidence_refs": [f"artifacts/worker-068/heldout09r/replication_report.json#sha256:{hashes['replication_report.json'][:12]}",
                          f"artifacts/worker-068/heldout09r/control_extension_report.json#sha256:{hashes['control_extension_report.json'][:12]}"],
        "next_falsifier": "Second-executor replication (not worker-068/16) or independent adjudication of the escaped fixture.",
        "claims_completion": False,
    })

    events.append({
        "event_id": "w068-hel09r-15-complete",
        "event_type": "status",
        "created_at": now(),
        "actor": ACTOR,
        "node_id": NODE,
        "status": "active",
        "hours": 0.5,
        "task_id": TASK_ID,
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "summary": ("Bounded worker lifecycle complete (W068-FORM-HELDOUT-09-REPL). Artifacts + events "
                    "emitted; worker exits for recycling. No node completion, validation_status=passed, or "
                    "gate verdict is claimed."),
        "evidence_refs": [f"artifacts/worker-068/heldout09r/README.md#sha256:{hashes['README.md'][:12]}",
                          f"artifacts/worker-068/heldout09r/replication_report.json#sha256:{hashes['replication_report.json'][:12]}"],
        "next_falsifier": "See w068-hel09r-13-blocker.",
        "claims_completion": False,
    })

    for ev in events:
        validate_event(ev)
    if not all("created_at" in e and "actor" in e and "event_id" in e and "event_type" in e for e in events):
        raise SystemExit("event base fields missing")

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                pass
    new = [e for e in events if e["event_id"] not in existing]
    with OUTBOX.open("a") as f:
        for e in new:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    checkpoint = {
        "checkpoint": 2,
        "at": now(),
        "worker": ACTOR,
        "task_id": TASK_ID,
        "corpus_id": CORPUS_ID,
        "node_id": NODE,
        "gate": GATE,
        "class_ids": CLASS_IDS,
        "hours_spent_estimate": 0.5,
        "status": {
            "delivered": True,
            "validation_status": "unverified",
            "no_completion_claim": "worker cannot set done/passed/gate verdict",
        },
        "frozen_revision_binding": {
            "frozen_manifest": "artifacts/formulation/FROZEN.json",
            "pinned_at_frozen_run": "af24e9c396060e6bff2b2cbf781814f587d60ba0e74fc0764918fa5757ec983b",
            "revision_at_frozen_run": 25,
            "measured_at_replication": "2554e276a0db70579ce36f7e665c9af81a1707bdc99e33758e861bec1d2df2e3",
            "revision_at_replication": 26,
            "supersession_note": "rev26 is an F0 publication adjudication request; it still pins the same three class schemas and both stage tools, so the content binding holds and only the manifest hash moved.",
            "content_hashes": {
                "schemas/af_wcc_vacuum.yaml": "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
                "schemas/af_scc_c2_vacuum.yaml": "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2",
                "schemas/af_scc_c0_vacuum.yaml": "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
                "artifacts/formulation/tools/check_class_schema.py": "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
                "artifacts/worker-06/spec_conformance_audit.py": "c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec",
                "artifacts/formulation/rule_spec.json": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
            },
        },
        "measurement": {
            "verb": "replicated_with_manifest_supersession",
            "fixtures_compared": 49,
            "per_fixture_mismatches": 0,
            "union_escape_rate": 0.02857142857142857,
            "leaky_escaped_union": 1,
            "caught_stage_a": 34,
            "caught_stage_b": 33,
            "false_positives": 0,
            "known_rejected_controls_rejected": "6/6",
            "known_escape_references_still_escaping": "4/4",
            "conforming_controls_total": 7,
            "extended_controls_accepted": ["c05", "c06", "c07"],
            "format_probe_accepted": True,
            "escape_families": ["c0-conclusion-polarity"],
            "escape_families_match": True,
            "valid": repl["valid"],
            "problems": repl["problems"],
        },
        "artifacts": {f"artifacts/worker-068/heldout09r/{rel}": {"sha256": h} for rel, h in hashes.items()},
        "events": [e["event_id"] for e in events],
        "limitations": repl["limitations"],
        "falsifier": repl["falsifier"],
        "next_falsifier": repl["next_falsifier"],
        "non_claims": [
            "Not a gate verdict and not a node transition; A1/G-CLASSBIND remain owned by the controller/leads.",
            "No claim about the truth of the formulation classes or of cosmic censorship.",
            "Harness-independent replication only, not agent-independent; the corpus was built by worker-068.",
            "Binds the pinned content hashes; a content change in the three schemas or either stage voids it.",
        ],
    }
    (STATE / "w068_checkpoint_repl.json").write_text(json.dumps(checkpoint, indent=2) + "\n")
    with (STATE / "w068_checkpoints.jsonl").open("a") as f:
        f.write(json.dumps(checkpoint, sort_keys=True) + "\n")

    print(json.dumps({"new_events": [e["event_id"] for e in new],
                      "skipped_existing": [e["event_id"] for e in events if e["event_id"] in existing],
                      "checkpoint": str(STATE / "w068_checkpoint_repl.json"),
                      "artifacts": {k: v[:12] for k, v in hashes.items()}}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
