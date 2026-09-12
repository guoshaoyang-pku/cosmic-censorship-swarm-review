#!/usr/bin/env python3
"""Emit worker-06 events for assignment astra-w06-01 (semantic contract tests).

Writes JSON lines (one event per line) to comms/outbox/deepseek-flash-06.jsonl and
validates each against research_map/schemas.validate_event before writing.
No node completion, no gate verdict, no theorem: all statuses are unverified.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from research_map.schemas import SchemaError, validate_event  # noqa: E402

OUT = ROOT / "comms" / "outbox" / "deepseek-flash-06.jsonl"
SUITE = ROOT / "schemas" / "semantic_contract_tests"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
STAMP = datetime.now(CST).strftime("%Y%m%dT%H%M")


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def ref(p, n=12):
    return f"{p}#{sha(p)[:n]}"


ASSIGNMENT = "astra-w06-01"
CLASS_IDS = ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"]
MANIFEST = "schemas/semantic_contract_tests/manifest.json"
OBSERVED = "schemas/semantic_contract_tests/observed_verdicts.json"
RUNNER = "schemas/semantic_contract_tests/run_contract_tests.py"
README = "schemas/semantic_contract_tests/README.md"
BUILDER = "artifacts/worker-06/make_contract_tests.py"
SRC_MANIFEST = "artifacts/worker-06/semantic_fixtures/manifest.json"

events = []


def add(ev):
    ev.setdefault("actor", "deepseek-flash-06")
    ev.setdefault("created_at", NOW)
    ev.setdefault("class_ids", CLASS_IDS)
    ev.setdefault("assignment", ASSIGNMENT)
    events.append(ev)


add({
    "event_id": f"w06-{STAMP}-contract-manifest",
    "event_type": "artifact",
    "node_id": "A1",
    "artifact_type": "test_manifest",
    "path": MANIFEST,
    "sha256": sha(MANIFEST),
    "validation_status": "unverified",
    "note": ("Canonical semantic contract-test registry per assignment astra-w06-01: 32 leak mutants + 3 frozen "
             "controls + 3 conforming canonical controls, each mapped to rule(s) tested, expected verdict and "
             "observed verdict; 21 adjudication items. Gate routing: G-CLASSBIND folded into G-AUDIT calibration "
             "evidence; no new gate id. Fixtures copied byte-identically from artifacts/worker-06/semantic_fixtures/ "
             "and hash-verified on every run."),
})
add({
    "event_id": f"w06-{STAMP}-contract-observed",
    "event_type": "artifact",
    "node_id": "A1",
    "artifact_type": "gate_run_record",
    "path": OBSERVED,
    "sha256": sha(OBSERVED),
    "validation_status": "unverified",
    "note": ("Raw per-fixture per-stage verdicts for the 2026-09-12 run. structural (binding gate sha "
             "000e09e46b2f) 32/32, semantic baseline 11/32, semantic hardened 32/32; 3 current canonical schemas "
             "accepted by all stages; the 3 frozen controls are rejected by the structural stage on R28 only "
             "(corpus-base layout drift), so validity.valid_for_calibration is false pending ADJ-CONTROL-STALENESS."),
})
add({
    "event_id": f"w06-{STAMP}-contract-runner",
    "event_type": "artifact",
    "node_id": "A1",
    "artifact_type": "test_runner",
    "path": RUNNER,
    "sha256": sha(RUNNER),
    "validation_status": "unverified",
    "note": ("Runner for schemas/semantic_contract_tests/: stages structural + semantic baseline + semantic "
             "hardened; tamper check on fixture sha256; exit 2 integrity, 3 control-validity failure, 0 valid. "
             "Calibration evidence only; defines no gate."),
})
add({
    "event_id": f"w06-{STAMP}-contract-readme",
    "event_type": "artifact",
    "node_id": "A1",
    "artifact_type": "report",
    "path": README,
    "sha256": sha(README),
    "validation_status": "unverified",
    "note": "Suite documentation: run instructions, current measurement table, control-staleness blocker, full adjudication list, limits and falsifiers.",
})
add({
    "event_id": f"w06-{STAMP}-contract-builder",
    "event_type": "artifact",
    "node_id": "A1",
    "artifact_type": "generator",
    "path": BUILDER,
    "sha256": sha(BUILDER),
    "validation_status": "unverified",
    "note": "Generator that copied the frozen corpus into the canonical suite path and authored the manifest (parses H01-H17 from HARDENED_RULES.md rather than retyping).",
})

add({
    "event_id": f"w06-{STAMP}-contract-status",
    "event_type": "status",
    "node_id": "A1",
    "status": "active",
    "hours": 1.0,
    "summary": ("astra-w06-01 delivered: semantic corpus relocated to schemas/semantic_contract_tests/ with "
                "manifest (rule + expected + observed verdict per fixture), runner, README and a raw run record. "
                "Current run: structural binding gate 000e09e46b2f catches 32/32 mutants (escape 0.0000), semantic "
                "baseline 11/32 (0.6562), proposed hardened H01-H17 32/32; all 3 current canonical schemas accepted "
                "by all stages. BLOCKER: the 3 frozen controls fail the structural stage on R28 only because they "
                "embed the corpus-base layout (the finite_codimension_complement -> residual_comeager row sits in "
                "transfer_failures, while current canonical C0 puts it in transfer_holds), so the control basis is "
                "stale and validity.valid_for_calibration=false (runner exit 3); ADJ-CONTROL-STALENESS asks the lead "
                "to rebase controls or pin the gate revision. Mutation fixtures stay frozen. 21 adjudication items: "
                "1 control staleness, H01-H17 proposed-not-adopted, SEM-1..3 non-machine-checkable/out-of-scope. "
                "No node completion, no gate verdict, no theorem."),
    "evidence_refs": [ref(MANIFEST), ref(OBSERVED), ref(RUNNER), ref(SRC_MANIFEST),
                      ref("artifacts/worker-06/HARDENED_RULES.md"), ref("artifacts/formulation/tools/check_class_schema.py")],
    "next_falsifier": ("A run in which all 3 frozen controls are accepted by the structural stage at the current "
                       "gate revision, or a current canonical C0 placing that transfer row back in "
                       "transfer_failures; or any stage hash change, which invalidates the numbers until re-run."),
})

add({
    "event_id": f"w06-{STAMP}-contract-claim",
    "event_type": "claim",
    "node_id": "A1",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "conclusion_type": "formal_model",
    "statement": ("On the relocated W06 semantic contract corpus (manifest sha256 " + sha(MANIFEST)[:16] +
                  ", source corpus " + sha(SRC_MANIFEST)[:16] + "), measured 2026-09-12: the binding structural gate "
                  "(sha 000e09e46b2f) rejects 32/32 leak mutants including all 20 rephrased ones (escape 0.0000); the "
                  "semantic auditor baseline rejects 11/32 (escape 0.6562); the proposed hardened set H01-H17 rejects "
                  "32/32; all 3 current canonical schemas are accepted by all three stages. The 3 frozen corpus "
                  "controls are rejected by the structural stage on R28 only, because their embedded base layout "
                  "predates the current canonical transfer truth table; therefore the contract suite is NOT yet valid "
                  "calibration evidence for the current gate revision (validity.valid_for_calibration=false)."),
    "assumptions": [
        "fixture copies are byte-identical to the frozen source corpus and hash-verified at run time",
        "escapes are structural findings, not proof that a mutant is a legitimate formulation",
        "the hardened H01-H17 set is worker-proposed and not adopted; its catches are recorded, not claimed as gate behaviour",
    ],
    "falsifier": ("Any mutant shown to be a legitimate formulation, any stage-hash change that moves the counts, or a "
                  "run where the frozen controls pass the structural stage at the current revision."),
    "evidence_refs": [ref(MANIFEST), ref(OBSERVED), ref(SRC_MANIFEST),
                      ref("artifacts/formulation/tools/check_class_schema.py"),
                      ref("schemas/af_scc_c0_vacuum.yaml")],
})

add({
    "event_id": f"w06-{STAMP}-contract-blocker",
    "event_type": "blocker",
    "node_id": "A1",
    "description": ("Control basis stale against the current binding gate: all 3 frozen corpus controls are rejected "
                    "by check_class_schema.py (sha 000e09e46b2f) on R28 only, since their corpus-base layout "
                    "(92406957234f) keeps the finite_codimension_complement -> residual_comeager row in "
                    "transfer_failures while the current canonical C0 places it in transfer_holds. The gate is "
                    "consistent with the current canonical schema; the controls are stale. Until this is resolved the "
                    "suite cannot serve as current-revision G-AUDIT calibration evidence (runner exit 3)."),
    "needed_to_unblock": ("Lead-formulation decides ADJ-CONTROL-STALENESS: rebase the 3 control layouts to the "
                          "current canonical schemas (mutants stay frozen), or pin the calibration gate revision for "
                          "this suite, then re-run run_contract_tests.py and record the new hashes."),
    "evidence_refs": [ref(MANIFEST), ref(OBSERVED),
                      ref("artifacts/worker-06/semantic_fixtures/manifest.json"),
                      ref("schemas/af_scc_c0_vacuum.yaml"),
                      ref("artifacts/formulation/tools/check_class_schema.py")],
})

add({
    "event_id": f"w06-{STAMP}-contract-gate-proposal",
    "event_type": "gate",
    "gate_id": "G-AUDIT",
    "scope": "A1/AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-WCC-VAC-GEN",
    "verdict": "pending",
    "criteria": [
        "manifest maps every fixture to rule(s), expected verdict and observed verdict",
        "controls (frozen + conforming canonical) accepted by both stages before calibration use",
        "adjudication list names every rule needing lead decision",
        "explanation: gate verdict pending because worker cannot move a gate; proposal is calibration evidence only",
    ],
    "evidence_refs": [ref(MANIFEST), ref(OBSERVED), ref(RUNNER)],
    "note": ("Gate proposal only: worker events cannot set a gate verdict. Calibration is BLOCKED by "
             "ADJ-CONTROL-STALENESS; do not count this suite as current-revision evidence until the controls are rebased "
             "or the gate revision is pinned."),
})

lines = []
for ev in events:
    try:
        validate_event(ev)
    except SchemaError as exc:
        raise SystemExit(f"INVALID {ev['event_id']}: {exc}")
    lines.append(json.dumps(ev, sort_keys=True))

with OUT.open("a") as f:
    f.write("\n".join(lines) + "\n")
print(f"wrote {len(lines)} events to {OUT}")
for l in lines:
    print(" ", json.loads(l)["event_id"])
