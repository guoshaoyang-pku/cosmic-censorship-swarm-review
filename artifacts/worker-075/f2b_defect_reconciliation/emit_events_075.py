#!/usr/bin/env python3
"""Emit worker-075 checkpoint + protocol events for W075-F2B-DEFECT-RECONCILIATION-09.

Appends (never rewrites) to comms/outbox/worker-075.jsonl and writes
runtime/state/w075_checkpoint_4.json plus a SHA256SUMS file in the artifact dir.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
D = ROOT / "artifacts/worker-075/f2b_defect_reconciliation"
OUTBOX = ROOT / "comms/outbox/worker-075.jsonl"
CKPT = ROOT / "runtime/state/w075_checkpoint_4.json"
TASK = "W075-F2B-DEFECT-RECONCILIATION-09"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


# final re-run of instrument + verifier so the recorded hashes are the verified bytes
for script in ("reconcile_f2b_075.py", "verify_f2b_reconciliation_075.py"):
    r = subprocess.run([sys.executable, str(D / script)], capture_output=True, text=True, cwd=str(ROOT))
    if r.returncode != 0:
        print(f"ABORT: {script} exit {r.returncode}\n{r.stdout[-800:]}\n{r.stderr[-400:]}")
        raise SystemExit(2)

rep = json.loads((D / "reconciliation.json").read_text())
ver = json.loads((D / "verification.json").read_text())
assert rep["controls_pass"] is True and ver["verdict"] == "PASS", "instrument/verifier not clean"

files = {
    "evidence_report": D / "reconciliation.json",
    "repro_script": D / "reconcile_f2b_075.py",
    "repro_script_verifier": D / "verify_f2b_reconciliation_075.py",
    "verification_report": D / "verification.json",
    "summary": D / "README.md",
    "repair_candidate_dryrun": D / "candidate/repair_spec_dryrun__af_scc_c0_vacuum.yaml",
    "control_variant": D / "candidate/control_f0token__af_scc_c0_vacuum.yaml",
}
hashes = {k: sha(p) for k, p in files.items()}

(D / "SHA256SUMS").write_text("".join(f"{h}  {rel(p)}\n" for k, p in sorted(files.items()) for h in [hashes[k]]))

ts = datetime.now().astimezone().isoformat(timespec="seconds")
compact = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
eid = f"w075-{compact}"
ref = lambda k: f"{rel(files[k])}#{hashes[k][:12]}"  # noqa: E731

events = [
    {
        "actor": "worker-075", "event_id": f"{eid}-status-start", "event_type": "status",
        "created_at": ts, "node_id": "F2b", "gate": "G-FORM",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"], "status": "active", "hours": 0.4,
        "task_id": TASK,
        "summary": ("Took one bounded class-bound task (no inbox card for slot worker-075): independent reconciliation of the four "
                    "documented F2b defects at live pins F2b b2ab6acb2bbe / F2a e9a27996dfd3 / F0 0abb9ed8a961 / FROZEN rev29 "
                    "815e08079aef. Read-only; no canonical write, no gate verdict."),
        "evidence_refs": [ref("evidence_report"), ref("summary")],
        "next_falsifier": rep["falsifier"],
    },
    {
        "actor": "worker-075", "event_id": f"{eid}-artifact-reconciliation-json", "event_type": "artifact",
        "created_at": ts, "node_id": "F2b", "gate": "G-FORM",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "artifact_type": "evidence_report", "path": rel(files["evidence_report"]), "sha256": hashes["evidence_report"],
        "validation_status": "unverified", "task_id": TASK,
        "evidence_refs": [ref("evidence_report")],
        "note": "main evidence: pins, D1-D4 verdicts, cross-ledger matrix, self-erratum, proposed repair + dryrun, controls K1-K8",
    },
    {
        "actor": "worker-075", "event_id": f"{eid}-artifact-reconcile-script", "event_type": "artifact",
        "created_at": ts, "node_id": "F2b", "gate": "G-FORM",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "artifact_type": "repro_script", "path": rel(files["repro_script"]), "sha256": hashes["repro_script"],
        "validation_status": "unverified", "task_id": TASK, "evidence_refs": [ref("evidence_report")],
    },
    {
        "actor": "worker-075", "event_id": f"{eid}-artifact-verify-script", "event_type": "artifact",
        "created_at": ts, "node_id": "F2b", "gate": "G-FORM",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "artifact_type": "repro_script", "path": rel(files["repro_script_verifier"]), "sha256": hashes["repro_script_verifier"],
        "validation_status": "unverified", "task_id": TASK, "evidence_refs": [ref("verification_report")],
        "note": "independent verifier: line-based re-derivation, 8/8 checks PASS",
    },
    {
        "actor": "worker-075", "event_id": f"{eid}-artifact-verification-json", "event_type": "artifact",
        "created_at": ts, "node_id": "F2b", "gate": "G-FORM",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "artifact_type": "verification_report", "path": rel(files["verification_report"]), "sha256": hashes["verification_report"],
        "validation_status": "unverified", "task_id": TASK, "evidence_refs": [ref("verification_report")],
    },
    {
        "actor": "worker-075", "event_id": f"{eid}-artifact-readme", "event_type": "artifact",
        "created_at": ts, "node_id": "F2b", "gate": "G-FORM",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "artifact_type": "summary", "path": rel(files["summary"]), "sha256": hashes["summary"],
        "validation_status": "unverified", "task_id": TASK, "evidence_refs": [ref("evidence_report")],
    },
    {
        "actor": "worker-075", "event_id": f"{eid}-artifact-repair-dryrun", "event_type": "artifact",
        "created_at": ts, "node_id": "F2b", "gate": "G-FORM",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "artifact_type": "repair_candidate", "path": rel(files["repair_candidate_dryrun"]), "sha256": hashes["repair_candidate_dryrun"],
        "validation_status": "unverified", "task_id": TASK, "evidence_refs": [ref("evidence_report")],
        "note": "dry-run only; NOT applied to any canonical path; D1/D2 silent there, frozen checker pass, D3 untouched",
    },
    {
        "actor": "worker-075", "event_id": f"{eid}-artifact-control-variant", "event_type": "artifact",
        "created_at": ts, "node_id": "F2b", "gate": "G-FORM",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "artifact_type": "control_variant", "path": rel(files["control_variant"]), "sha256": hashes["control_variant"],
        "validation_status": "unverified", "task_id": TASK, "evidence_refs": [ref("evidence_report")],
        "note": "canonical F2b with conclusion_type replaced by F0's declared token; frozen checker fails R11 on it",
    },
    {
        "actor": "worker-075", "event_id": f"{eid}-claim-reconciliation", "event_type": "claim",
        "created_at": ts, "node_id": "F2b", "gate": "G-FORM",
        "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "conclusion_type": "verification_result", "task_id": TASK,
        "statement": ("At live pins F2b b2ab6acb2bbe, F2a e9a27996dfd3, F0 0abb9ed8a961, VOCAB_ALIASES 46cd9f1eb534, rule_spec "
                      "40f9bb9e657b, FROZEN rev29 815e08079aef, corpus 7e44de0e3906: the four documented F2b defects all reproduce. "
                      "D1 (forbidden_transfers[0].reason calls C2 the larger extension class while the document nests E_C2 inside "
                      "E_C0) and D2 (must_not_conflate[0] denies C2/C0 containment that implication_ledger asserts) admit a minimal "
                      "direction-correct repair; the C2 sibling's repaired sentence cannot be copied verbatim because its closing "
                      "entailment clause is the C2 direction (C0 is the strongest: C0 => H2loc => C2). D3 is a real cross-artifact "
                      "canonicalization divergence that NO frozen instrument detects: the checker requires the scc_* token (R11) and "
                      "rejects F0's declared strong_* token, while every F0 allowed token is a registry alias of the schema token, so "
                      "no semantic class mismatch is demonstrated and the resolution is a gate-owner adjudication. D4 reproduces with "
                      "the frozen run_acceptance preflight itself returning False (corpus base 1bb78ce9 vs live C0 b2ab6acb). "
                      "Independent verifier PASS 8/8, instrument controls K1-K8 all pass."),
        "assumptions": [
            "the recorded pins are the live canonical bytes; any move voids these numbers until re-run",
            "F0, VOCAB_ALIASES.json and rule_spec.json are read as declarations, not edited by this task",
            "the D3 consequence options are decision inputs for the gate owner, not a worker ruling",
            "the repair candidate is a dry-run under artifacts/worker-075 only; no canonical path was written",
            "worker events cannot set status=done, validation_status=passed, or a gate verdict",
        ],
        "falsifier": rep["falsifier"],
        "evidence_refs": [ref("evidence_report"), ref("repro_script"), ref("repro_script_verifier"),
                          ref("verification_report"), ref("summary"), ref("repair_candidate_dryrun")],
        "artifact_refs": [rel(files["evidence_report"]), rel(files["repair_candidate_dryrun"])],
        "claims_theorem_status": False,
    },
    {
        "actor": "worker-075", "event_id": f"{eid}-erratum-f2b-review-scope", "event_type": "status",
        "created_at": ts, "node_id": "F2b", "gate": "G-FORM",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"], "status": "active", "hours": 0.1,
        "task_id": TASK,
        "summary": ("ERRATUM to w075-20260912T0103-review-f2b (event not edited): that review flagged D1 (HF-075-F2b-LARGER) and D3 "
                    "(HF-075-F2b-VOCAB) but did not flag D2, the must_not_conflate[0] containment denial that worker-083 D2 and "
                    "worker-097 H3b independently found. The union of independent F2b findings is three blocking defect classes, not "
                    "two; the scope gap is recorded in the reconciliation artifact."),
        "evidence_refs": [ref("evidence_report"), "artifacts/worker-083/f2b_live_defect_ledger/report.json#f75cb3789859",
                          "artifacts/worker-097/f2b_rev13_review/report.json#2b38dea6b487"],
        "next_falsifier": "Re-run the reconciliation instrument at the same pins; if D2 does not reproduce, this erratum is void.",
    },
]

with OUTBOX.open("a") as fh:
    for e in events:
        fh.write(json.dumps(e, sort_keys=True) + "\n")

ckpt = {
    "schema": "worker-checkpoint/v1", "task_id": TASK, "worker": "worker-075",
    "created_at": ts, "node_id": "F2b", "gate": "G-FORM",
    "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
    "status": "complete_worker_level",
    "hours": 0.5,
    "pins": rep["pins"],
    "defect_verdicts": {d["id"]: d["verdict"] for d in rep["defects"]},
    "controls_pass": rep["controls_pass"],
    "verifier": ver["verdict"],
    "artifacts": {k: {"path": rel(p), "sha256": hashes[k]} for k, p in files.items()},
    "events_written": [e["event_id"] for e in events],
    "next_falsifier": rep["falsifier"],
    "authority": "worker measurement only; no canonical write, no gate verdict, no node completion",
    "note": "self-erratum recorded: the 01:03 F2b review missed D2; see reconciliation.json cross_ledger_reconciliation.w075_self_erratum",
}
CKPT.write_text(json.dumps(ckpt, indent=1) + "\n")

# validate the appended lines parse and carry the required keys
required = {"status": ["event_id", "event_type", "created_at", "actor", "node_id", "status", "hours", "summary",
                       "evidence_refs", "next_falsifier"],
            "artifact": ["event_id", "event_type", "created_at", "actor", "node_id", "artifact_type", "path", "sha256",
                         "validation_status"],
            "claim": ["event_id", "event_type", "created_at", "actor", "class_id", "statement", "conclusion_type",
                      "assumptions", "falsifier", "evidence_refs"]}
n_ok = 0
for line in OUTBOX.read_text().splitlines()[-len(events):]:
    e = json.loads(line)
    missing = [k for k in required.get(e["event_type"], []) if k not in e]
    assert not missing, (e["event_id"], missing)
    n_ok += 1

print(json.dumps({"events_appended": len(events), "validated": n_ok, "checkpoint": rel(CKPT),
                  "checkpoint_sha256": sha(CKPT),
                  "artifact_hashes": hashes}, indent=1))
