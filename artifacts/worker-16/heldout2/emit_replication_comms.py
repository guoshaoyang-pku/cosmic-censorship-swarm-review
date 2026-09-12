#!/usr/bin/env python3
"""Emit the worker-16 second-pass replication checkpoint + comms events (FORM-HELDOUT-08).

Idempotent by event_id: re-running does not duplicate outbox lines.
Run:  python3 artifacts/worker-16/heldout2/emit_replication_comms.py
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")

CHECKPOINT = ROOT / "runtime" / "state" / "w16_checkpoint_heldout2.json"
CKPT_LOG = ROOT / "runtime" / "state" / "w16_checkpoints.jsonl"
OUTBOX = ROOT / "comms" / "outbox" / "worker-16.jsonl"

ART = {
    "manifest": ("artifacts/worker-16/heldout2/manifest.json",
                 "1c8fa8888226ea19d94c3646a7e16412011162c06ae8da210fe9efc3fc53ada1"),
    "report": ("artifacts/worker-16/heldout2/report.json",
               "87f20491800343a0701b08c6c2741c3561d105181f1a89893d685aac49267279"),
    "raw": ("artifacts/worker-16/heldout2/raw_verdicts.json",
            "84c1b87953f5d7285f2f544b2809eec799dbe1e7e82c816a2fc52aaa83a20d5f"),
    "repro": ("artifacts/worker-16/heldout2/verify/reproduce.json",
              "d88588dcd246ecf5d9d475fee323d4e28ed65204fce51a68540fc7c99f28277e"),
    "script": ("artifacts/worker-16/heldout2/verify_independent.py",
               "3f8d77761ebabec0fd79695fe8e7aa53e86f9435435785d3afc6802ff4fef000"),
    "struct": ("artifacts/formulation/tools/check_class_schema.py",
               "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff"),
    "sem": ("artifacts/worker-06/spec_conformance_audit.py",
            "c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec"),
    "wcc_base": ("artifacts/worker-16/heldout2/bases/af_wcc_vacuum.yaml",
                 "f962c117ba11598f9d5c778cb015809961a371339612b52808c2b9c3446abe96"),
    "c2_base": ("artifacts/worker-16/heldout2/bases/af_scc_c2_vacuum.yaml",
                "e9fcefe6e59555ba210d1440e5a0a5d4659cf7e6a859b63b60fda8b4066cbcb0"),
    "c0_base": ("artifacts/worker-16/heldout2/bases/af_scc_c0_vacuum.yaml",
                "bdb23f76b89540e82e4a8a3feb12637eb646af54466f624cf6ba2fef5a94bf90"),
}
REFS = [f"{p}#sha256:{h[:12]}" for p, h in ART.values()]


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main() -> int:
    ckpt_sha = sha(CHECKPOINT)
    checkpoint = json.loads(CHECKPOINT.read_text())

    artifact_event = {
        "event_id": "w16-heldout2-replication-artifact-20260912T0019",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "deepseek-flash-16",
        "to": ["astra", "lead-formulation", "lead-audit"],
        "node_id": "A1",
        "task_id": "FORM-HELDOUT-08",
        "group_id": "formulation",
        "gate": "G-CLASSBIND",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "artifact_type": "independent_replication",
        "path": ART["repro"][0],
        "sha256": ART["repro"][1],
        "validation_status": "unverified",
        "claims_completion": False,
        "evidence_refs": REFS + [f"runtime/state/w16_checkpoint_heldout2.json#sha256:{ckpt_sha[:12]}"],
        "next_falsifier": ("Any fixture or stage-tool byte change retires these verdicts; re-run "
                           "verify_independent.py and require replication_ok=true. A domain reviewer "
                           "classifying any escaped mutant as a legitimate formulation forces that "
                           "family out of the deliverable list."),
        "summary": ("Independent replication of FORM-HELDOUT-08: both bound stage tools re-run on all "
                    "29 mutants + 7 controls. manifest unchanged since freeze (1c8fa8888226), 0 tampered "
                    "fixtures, 0 verdict mismatches, 0 control mismatches, aggregates and the 21-family "
                    "escape list reproduced exactly, controls 7/7 accepted by both stages. Frozen result "
                    "stands: structural 1.0, semantic 1.0, union escape 1.0, union caught 0. No frozen "
                    "file modified; no completion or gate verdict claimed."),
    }
    status_event = {
        "event_id": "w16-heldout2-status-ckpt7-20260912T0019",
        "event_type": "status",
        "created_at": NOW,
        "actor": "deepseek-flash-16",
        "to": ["astra", "lead-formulation", "lead-audit"],
        "node_id": "A1",
        "task_id": "FORM-HELDOUT-08",
        "group_id": "formulation",
        "gate": "G-CLASSBIND",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "status": "active",
        "hours": 0.2,
        "claims_completion": False,
        "summary": ("CHECKPOINT 7 (worker-16 second pass, bounded execution worker). FORM-HELDOUT-08 "
                    "deliverable verified rather than re-authored: manifest 1c8fa8888226 + report "
                    "87f204918003 + raw verdicts 84c1b87953f5 are on disk, events ingested, and the whole "
                    "measurement was independently re-run in this pass (verify/reproduce.json d88588dcd246, "
                    "replication_ok=true). Measurement: 29 mutants / 21 families / 22 rephrased; structural "
                    "escape 1.0, semantic escape 1.0, union escape 1.0, union caught 0; 7/7 controls pass "
                    "both stages; the 21 escaped families are the deliverable. Node A1 stays active pending "
                    "lead review; worker cannot set done/passed. Budget: 0.2 h this pass, well inside the "
                    "3 h stop rule."),
        "evidence_refs": REFS + [f"runtime/state/w16_checkpoint_heldout2.json#sha256:{ckpt_sha[:12]}"],
        "next_falsifier": ("A union escape rate of 0 on a corrected corpus falsifies the 1.0 estimate; a "
                           "rule rejecting a legitimate formulation (false positive) is an equal-value "
                           "finding and must be reported with the exact path."),
    }

    # append checkpoint log line (idempotent by checkpoint_id)
    log_lines = []
    if CKPT_LOG.exists():
        log_lines = [json.loads(l) for l in CKPT_LOG.read_text().splitlines() if l.strip()]
    if not any(r.get("checkpoint_id") == checkpoint["checkpoint_id"] for r in log_lines):
        with CKPT_LOG.open("a") as f:
            f.write(json.dumps({
                "checkpoint_id": checkpoint["checkpoint_id"],
                "checkpoint_at": checkpoint["checkpoint_at"],
                "worker": checkpoint["worker"],
                "path": "runtime/state/w16_checkpoint_heldout2.json",
                "sha256": ckpt_sha,
                "task_id": "FORM-HELDOUT-08",
                "node_id": "A1",
                "task_state": checkpoint["task_state"],
                "replication_ok": checkpoint["replication"]["replication_ok"],
                "union_escape": checkpoint["measurement"]["union_escape"],
                "hours_this_pass": checkpoint["hours_this_pass"],
            }, sort_keys=True) + "\n")

    existing = {json.loads(l).get("event_id") for l in OUTBOX.read_text().splitlines() if l.strip()}
    written = []
    with OUTBOX.open("a") as f:
        for ev in (artifact_event, status_event):
            if ev["event_id"] in existing:
                continue
            f.write(json.dumps(ev, sort_keys=True) + "\n")
            written.append(ev["event_id"])
    print("checkpoint sha256:", ckpt_sha)
    print("appended outbox events:", written if written else "(already present)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
