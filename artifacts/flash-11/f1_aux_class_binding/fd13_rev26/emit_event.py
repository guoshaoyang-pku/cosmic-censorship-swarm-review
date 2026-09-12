#!/usr/bin/env python3
"""Emit the FD-13 rev26→rev28 rebase status event to comms/outbox/deepseek-flash-11.jsonl.

The head moved three times while this ran (FROZEN rev26 -> 27 -> 28; KEY_MANIFEST
fce91948 -> 014e2d30), so this emitter does NOT abort on head drift: it records the measured
binding from rev28fix_results.json, re-hashes every delivered artifact, and records the
current-disk hashes side by side. One JSON object per line (comms/PROTOCOL.md).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
OUTBOX = REPO / "comms/outbox/deepseek-flash-11.jsonl"
CST = timezone(timedelta(hours=8))

DELIVERED = [
    "artifacts/flash-11/f1_aux_class_binding/fd13_rev26/rev28fix_results.json",
    "artifacts/flash-11/f1_aux_class_binding/fd13_rev26/leak_rev28fix.yaml",
    "artifacts/flash-11/f1_aux_class_binding/fd13_rev26/control_rev28fix.yaml",
    "artifacts/flash-11/f1_aux_class_binding/fd13_rev26/rev12_snapshot/af_wcc_vacuum.yaml",
    "artifacts/flash-11/f1_aux_class_binding/fd13_rev26/rev12_snapshot/af_scc_c2_vacuum.yaml",
    "artifacts/flash-11/f1_aux_class_binding/fd13_rev26/rev12_snapshot/af_scc_c0_vacuum.yaml",
    "artifacts/flash-11/f1_aux_class_binding/fd13_rev26/diskhead_results.json",
    "artifacts/flash-11/f1_aux_class_binding/fd13_rev26/rev27_r22_repro.json",
    "artifacts/flash-11/f1_aux_class_binding/fd13_rev26/key_manifest_014e2d30.json",
    "artifacts/flash-11/f1_aux_class_binding/fd13_rev26/rev26_snapshot/rev26_results.json",
    "artifacts/flash-11/f1_aux_class_binding/fd13_rev26/rev26_snapshot/canonical_af_wcc_vacuum.yaml",
    "artifacts/flash-11/f1_aux_class_binding/fd13_rev26/rev26_snapshot/canonical_af_scc_c2_vacuum.yaml",
    "artifacts/flash-11/f1_aux_class_binding/fd13_rev26/rev26_snapshot/canonical_af_scc_c0_vacuum.yaml",
    "artifacts/flash-11/f1_aux_class_binding/fd13_rev26/README.md",
    "artifacts/flash-11/f1_aux_class_binding/fd13_rev26/build_and_run.py",
    "artifacts/flash-11/f1_aux_class_binding/fd13_rev26/verify_r22.py",
]
FORMULATION = ["artifacts/formulation/FROZEN.json",
               "artifacts/formulation/tools/check_class_schema.py",
               "artifacts/formulation/rule_spec.json",
               "artifacts/formulation/KEY_MANIFEST.json",
               "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
               "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
               "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
               "artifacts/flash-11/f1_aux_class_binding/check_schema.py",
               "artifacts/flash-11/f1_aux_class_binding/fd13/tools/patched_check_class_schema.py"]


def sha(p: str) -> str:
    return hashlib.sha256((REPO / p).read_bytes()).hexdigest()


missing = [p for p in DELIVERED + FORMULATION if not (REPO / p).exists()]
if missing:
    raise SystemExit("missing artifacts: " + "; ".join(missing))

res28 = json.loads((REPO / DELIVERED[0]).read_text())
res27 = json.loads((REPO / "artifacts/flash-11/f1_aux_class_binding/fd13_rev26/diskhead_results.json").read_text())
res26 = json.loads((REPO / "artifacts/flash-11/f1_aux_class_binding/fd13_rev26/rev26_snapshot/rev26_results.json").read_text())
r22 = json.loads((REPO / "artifacts/flash-11/f1_aux_class_binding/fd13_rev26/rev27_r22_repro.json").read_text())
te = res28["targeted_effect"]

measured = {c["path"]: c["disk_sha256"] for c in res28["binding"]["checks"]}
for s in res28["binding"]["schemas"]:
    measured[f"artifacts/formulation/schemas/{Path(s['path']).name}"] = s["disk_sha256"]
drift = {p: {"measured_sha256": measured.get(p), "current_disk_sha256": sha(p),
             "same": measured.get(p) == sha(p)} for p in FORMULATION}

now = datetime.now(CST)
event = {
    "event_id": f"flash11-FD13-rev28-status-{now.strftime('%Y%m%dT%H%M%S')}",
    "event_type": "status",
    "created_at": now.isoformat(timespec="seconds"),
    "actor": "deepseek-flash-11",
    "node_id": "F1",
    "group_id": "formulation",
    "gate": "G-CLASSBIND",
    "task_id": "FORM-DIFF-02",
    "assignment_event_id": "assign-FORM-DIFF-02-20260911T2331",
    "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "status": "active",
    "claims_completion": False,
    "validation_status": "unverified",
    "hours": 1.0,
    "summary": (
        "FD-13 rebase across FROZEN rev26 -> rev27 -> rev28 (head moved three times 00:24-00:35). "
        "RESULT AT REV28 (actionable; schemas rev12 cce9c601/5476a3f2/55d0a1ea, tool 000e09e4, "
        "rule_spec 40f9bb9e, KEY_MANIFEST 014e2d30): FD-13 STILL OPEN - canonical base ACCEPTS the "
        "byte-minimal leak (rev12 WCC + one appended sentence 'The maximal development is "
        "C^2-inextendible.' in non_vacuity.condition); base accepts the control and all three "
        "canonical schemas; the proposal (patched 5eaab3f8) and the independent flash-11 gate "
        f"(a89b221c) each reject {te['leaks_flash11_catch']}/{te['leaks_total']} leaks on R12 with "
        f"{te['controls_false_positive_flash11']} false positives. "
        "TRANSIENT rev27 REGRESSION, now repaired and reproduced offline: with KEY_MANIFEST "
        "fce91948 the frozen gate rejected ALL THREE of its own frozen rev12 schemas at R22 "
        "(unknown keys: at, class_contract_supplement_pointer, consistency_evidence_sha256, index, "
        "notes, predicate_abbreviation); with 014e2d30 all three accept (rev27_r22_repro.json). "
        "That window MASKED FD-13: base rejected leak and controls alike, so a naive read would "
        "have scored the defect closed. rev26 measurement (snapshot) also FD-13 OPEN. "
        "No completion claim; canonical tool untouched; schema owner binds interpretation."
    ),
    "artifact_refs": [{"path": p, "sha256": sha(p), "validation_status": "unverified"}
                      for p in DELIVERED],
    "evidence_refs": [f"artifacts/flash-11/f1_aux_class_binding/fd13_rev26/rev28fix_results.json#{sha(DELIVERED[0])[:12]}",
                      f"artifacts/flash-11/f1_aux_class_binding/fd13_rev26/rev27_r22_repro.json#2b75c22a5e50",
                      f"artifacts/flash-11/f1_aux_class_binding/fd13_rev26/diskhead_results.json#90bc62632d26",
                      f"artifacts/flash-11/f1_aux_class_binding/fd13_rev26/rev26_snapshot/rev26_results.json#41ea685ef6ca",
                      f"artifacts/flash-11/f1_aux_class_binding/fd13_rev26/README.md#{sha('artifacts/flash-11/f1_aux_class_binding/fd13_rev26/README.md')[:12]}",
                      "artifacts/formulation/tools/check_class_schema.py#000e09e46b2f",
                      "artifacts/formulation/rule_spec.json#40f9bb9e657b",
                      "artifacts/formulation/KEY_MANIFEST.json#014e2d301978",
                      "artifacts/formulation/schemas/af_wcc_vacuum.yaml#cce9c60146d6",
                      "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc",
                      "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda",
                      "artifacts/flash-11/f1_aux_class_binding/check_schema.py#a89b221c1c68",
                      "artifacts/flash-11/f1_aux_class_binding/fd13/tools/patched_check_class_schema.py#5eaab3f8f031"],
    "head_drift_at_emit": drift,
    "falsifier": (
        "FIRED IF (a) the measured rev28 canonical gate rejects the leak (FD-13 closed at rev28), or "
        "(b) it rejects the control or any canonical rev12 schema (false positive), or (c) the "
        "independent flash11 gate misses a leak or rejects a control, or (d) an asserted "
        "tool/rule_spec/KEY_MANIFEST/gate hash moves (binding abort before measurement). Measured: "
        "NOT fired at rev28 (rev28fix_results.json). Rev27's R22 wave is an environment defect "
        "(masking), not a closure. Proposal falsifier: NOT fired with the rev28 manifest."
    ),
    "falsifier_status": "not fired",
    "next_falsifier": (
        "Apply the clause-local R12 fix in the canonical tool, then re-run run_gate_tests.py: fire if "
        "the canonical test report regresses or probe_r12_leak_in_nonvacuity is still accepted. "
        "Re-measure at whatever FROZEN revision is current (the head moved rev26->28 during this "
        "run), and re-run the differential whenever KEY_MANIFEST changes: a manifest lag can make "
        "base reject the canonical schemas at R22 and silently mask the R12 differential. Second: "
        "worker-06's rephrased corpus - a leak without inextendib/extension/horizon tokens is "
        "expected to escape and must NOT be scored as closed."
    ),
    "stop_rule": ("3.0 agent-hours or canonical-schema-hash run recorded, whichever first; this was "
                  "the last queued item for FORM-DIFF-02 (total ~5.0 h, over budget; no further "
                  "work queued)."),
}

line = json.dumps(event, ensure_ascii=False, sort_keys=True)
parsed = json.loads(line)
for k in ("event_id", "event_type", "created_at", "actor", "node_id", "class_ids",
          "evidence_refs", "falsifier", "artifact_refs"):
    assert k in parsed and parsed[k], f"missing {k}"
existing = set()
for src in (OUTBOX, REPO / "research_map/events.jsonl"):
    if src.exists():
        for ln in src.read_text().splitlines():
            try:
                existing.add(json.loads(ln).get("event_id"))
            except json.JSONDecodeError:
                pass
assert parsed["event_id"] not in existing, f"duplicate event_id {parsed['event_id']}"

with OUTBOX.open("a") as f:
    f.write(line + "\n")
print(f"emitted {parsed['event_id']} ({len(line)} bytes) -> {OUTBOX.relative_to(REPO)}")
print(json.dumps({"event_id": parsed["event_id"], "artifacts": len(parsed["artifact_refs"]),
                  "evidence_refs": len(parsed["evidence_refs"]), "status": parsed["status"],
                  "head_drift_same": {k: v["same"] for k, v in drift.items()}}, indent=1))
