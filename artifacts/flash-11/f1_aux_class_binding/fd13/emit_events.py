#!/usr/bin/env python3
"""Append FD-13 events to comms/outbox/deepseek-flash-11.jsonl (valid JSONL, one object/line)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
OUT = REPO / "comms/outbox/deepseek-flash-11.jsonl"
BIND = REPO / "artifacts/flash-11/f1_aux_class_binding"
NOW = "2026-09-12T00:13:49+08:00"
ACTOR = "deepseek-flash-11"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]


def h(rel: str) -> str:
    return hashlib.sha256((REPO / rel).read_bytes()).hexdigest()


def prefix(rel: str, n: int = 12) -> str:
    return f"{rel}#{h(rel)[:n]}"


FD = "artifacts/flash-11/f1_aux_class_binding/fd13"
events = []


def artifact(rel: str, artifact_type: str, note: str) -> None:
    events.append({
        "event_id": f"flash11-FD13-artifact-{Path(rel).stem}-20260912T0013",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": ACTOR,
        "task_id": "FORM-DIFF-02",
        "node_id": "F1",
        "gate": "G-CLASSBIND",
        "class_ids": CLASS_IDS,
        "artifact_type": artifact_type,
        "path": rel.replace("artifacts/flash-11/f1_aux_class_binding/", "artifacts/flash-11/f1_aux_class_binding/"),
        "sha256": h(rel),
        "validation_status": "unverified",
        "evidence_refs": [prefix(rel)],
        "note": note,
    })


artifact(f"{FD}/fd13_results.json", "evidence",
         "3 gates x 7 targets (2 leaks, 4 controls, 3 canonical schemas) + 57-fixture collateral sweep")
artifact(f"{FD}/tools/patched_check_class_schema.py", "tool",
         "proposed R12 clause-local fix; base tool 000e09e4 asserted at build time")
artifact(f"{FD}/r12_proposal.diff", "patch",
         "exact unified diff of the proposal; applies to frozen rev19 tool only")
artifact(f"{FD}/leak_rev19.yaml", "fixture",
         "byte-minimal leak: frozen rev19 WCC (f962c117) + one appended sentence in non_vacuity.condition")
artifact(f"{FD}/control_rev19.yaml", "fixture",
         "legit geodesic control on the same base; must stay accepted")
artifact(f"{FD}/README.md", "documentation",
         "FD-13 finding, mechanism, minimal repro, proposal, measurements, caveats")

status = {
    "event_id": "flash11-FD13-status-20260912T0013",
    "event_type": "status",
    "created_at": NOW,
    "actor": ACTOR,
    "task_id": "FORM-DIFF-02",
    "node_id": "F1",
    "gate": "G-CLASSBIND",
    "class_ids": CLASS_IDS,
    "group_id": "formulation",
    "status": "active",
    "hours": 3.5,
    "stop_rule": "3.0 agent-hours or canonical-schema-hash run recorded, whichever first; budget exceeded by 0.5h for the targeted FD-13 re-measurement; no further work queued",
    "summary": (
        "FD-13 CLOSURE ATTEMPT (unverified draft, proposal only). Corrects "
        "flash11-FORMDIFF02-rev19-status-20260912T0008 item (3): the rev19 canonical tool ALREADY scans "
        "non_vacuity.condition (check_class_schema.py:71, sha 000e09e4), so 'add the path' was the wrong fix. "
        "Real defect = field-global scope of the R12 geodesic exemption (lines 312-314): GEODESIC.search(s) over "
        "the whole field means the legitimate words 'future geodesically incomplete' exempt the entire "
        "non_vacuity.condition value, so a later sentence 'The maximal development is C^2-inextendible.' "
        "(AF-SCC-C2-VAC-GEN content) passes. (1) Byte-minimal repro, one appended sentence, no YAML round-trip, "
        "on BOTH frozen rev19 base f962c117 and live authoring schema b65fcc0f: canonical rev19 ACCEPTS both. "
        "(2) Proposed fix = clause-local exemption (re.split on [.;]); patched tool 5eaab3f8, diff 6bc0d181. "
        "(3) Measured: base escapes 2/2, patched catches 2/2 on R12, independent flash11 catches 2/2; 0 false "
        "positives on 4 controls + 3 canonical schemas across all 3 gates. (4) Collateral: 57/57 corpus fixtures "
        "swept, 0 verdict changes, 56 identical, 1 additive delta (rev4 stale probe probe_r12_leak_in_nonvacuity "
        "gains R12 on top of its existing R28 rejection). (5) Falsifier NOT fired. Caveats: still lexical not "
        "semantic; FROZEN.json stale (schemas advanced past rev19 while tool+rule_spec byte-match); canonical "
        "tool untouched, patch is a proposal for the schema owner."
    ),
    "evidence_refs": [
        prefix(f"{FD}/fd13_results.json"),
        prefix(f"{FD}/r12_proposal.diff"),
        prefix(f"{FD}/tools/patched_check_class_schema.py"),
        prefix(f"{FD}/leak_rev19.yaml"),
        prefix(f"{FD}/control_rev19.yaml"),
        "artifacts/formulation/tools/check_class_schema.py#000e09e46b2f",
        "artifacts/formulation/rule_spec.json#40f9bb9e657b",
        prefix(f"{FD}/README.md"),
    ],
    "artifact_refs": [
        {"path": f"{FD}/fd13_results.json", "sha256": h(f"{FD}/fd13_results.json")},
        {"path": f"{FD}/tools/patched_check_class_schema.py", "sha256": h(f"{FD}/tools/patched_check_class_schema.py")},
    ],
    "falsifier": (
        "FIRED IF: (a) the patched canonical gate rejects a schema it accepted before (false positive), or "
        "(b) any leak fixture still passes the patched gate (false negative), or (c) any of the 57 corpus "
        "fixtures changes verdict for a reason other than the intended non-geodesic-inextendibility leak, or "
        "(d) the frozen base hashes 000e09e4/40f9bb9e no longer match on disk. Measured status: NOT fired."
    ),
    "next_falsifier": (
        "Apply the clause-local R12 fix in the canonical tool, then re-run run_gate_tests.py: the falsifier "
        "re-fires if the canonical test report regresses, or if probe_r12_leak_in_nonvacuity is still accepted. "
        "Second: worker-06's rephrased corpus should re-test R12 as a token scan - a leak phrased without "
        "inextendib/extension/horizon tokens must still be expected to escape and must NOT be scored as closed."
    ),
    "claims_completion": False,
}
events.append(status)

with OUT.open("a") as fh:
    for ev in events:
        fh.write(json.dumps(ev, sort_keys=True) + "\n")
print(f"appended {len(events)} events to {OUT.relative_to(REPO)}")
for ev in events:
    json.loads(json.dumps(ev))  # validity round-trip
print("all events valid JSON")
