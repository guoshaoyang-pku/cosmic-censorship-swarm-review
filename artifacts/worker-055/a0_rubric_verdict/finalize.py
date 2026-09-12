#!/usr/bin/env python3
"""Finalize W055-A0-RUBRIC-01: manifest, SHA256SUMS, checkpoint, outbox events.

Fail-closed: refuses to emit if any pinned input drifted since check_a0_rubric.py ran.
Writes only: this bundle, runtime/state/w055_a0_rubric_checkpoint.json,
runtime/state/w055_checkpoints.jsonl (append), comms/outbox/worker-055.jsonl (append).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

EXPECTED = {
    "evaluation_rubric.yaml":
        "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "schemas/af_wcc_vacuum.yaml":
        "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "schemas/af_scc_c2_vacuum.yaml":
        "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "schemas/af_scc_c0_vacuum.yaml":
        "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def main() -> int:
    # 1. fail closed on drift
    drift = []
    for rel, want in EXPECTED.items():
        p = ROOT / rel
        got = sha(p) if p.exists() else None
        if got != want:
            drift.append({"path": rel, "expected": want, "observed": got})
    if drift:
        print(json.dumps({"status": "REFUSED_HASH_DRIFT", "drift": drift}, indent=2))
        return 2

    report_path = HERE / "report.json"
    report = json.loads(report_path.read_text())
    if not report.get("expectations_met"):
        print(json.dumps({"status": "REFUSED_EXPECTATIONS_NOT_MET"}, indent=2))
        return 2

    # 2. snapshot manifest
    snapshot = HERE / "snapshot" / "evaluation_rubric.d748a9e3574e.yaml"
    manifest = {
        "task_id": "W055-A0-RUBRIC-01",
        "created_at": now_iso(),
        "inputs": {rel: {"sha256": sha(ROOT / rel), "bytes": (ROOT / rel).stat().st_size}
                   for rel in EXPECTED},
        "bundle": {
            "snapshot": str(snapshot.relative_to(ROOT)),
            "snapshot_sha256": sha(snapshot),
            "report.json": sha(report_path),
            "check_a0_rubric.py": sha(HERE / "check_a0_rubric.py"),
        },
        "drift_check": "PASS (all pinned inputs equal the reviewed hashes)",
    }
    (HERE / "SNAPSHOT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")

    # 3. SHA256SUMS over bundle (regenerated after manifest)
    files = sorted(p for p in HERE.rglob("*")
                   if p.is_file() and p.name != "SHA256SUMS"
                   and "stage" not in p.relative_to(HERE).parts)
    lines = [f"{sha(p)}  {p.relative_to(HERE)}" for p in files]
    (HERE / "SHA256SUMS").write_text("\n".join(lines) + "\n")

    # 4. checkpoint
    hf = report["hard_failures"]
    checkpoint = {
        "checkpoint_id": "w055-a0-rubric-verdict",
        "task_id": "W055-A0-RUBRIC-01",
        "worker": "worker-055",
        "created_at": now_iso(),
        "node_id": "A0",
        "gate": "G-AUDIT",
        "class_ids": report["class_ids"],
        "artifact_path": "evaluation_rubric.yaml",
        "artifact_sha256": EXPECTED["evaluation_rubric.yaml"],
        "verdict": report["verdict"],
        "score": report["score"],
        "hard_failure_ids": [h["id"] for h in hf],
        "scalar_adjudication": report["scalar_adjudication"]["answer"],
        "evidence_refs": [
            f"artifacts/worker-055/a0_rubric_verdict/report.json#{sha(report_path)[:12]}",
            f"artifacts/worker-055/a0_rubric_verdict/check_a0_rubric.py#{sha(HERE / 'check_a0_rubric.py')[:12]}",
            f"evaluation_rubric.yaml#{EXPECTED['evaluation_rubric.yaml'][:12]}",
            f"research_map/formulation_taxonomy.yaml#{EXPECTED['research_map/formulation_taxonomy.yaml'][:12]}",
        ],
        "falsifiers": report["falsifiers"],
        "authority": report["authority"],
        "expectations_met": True,
    }
    ckpt = ROOT / "runtime" / "state" / "w055_a0_rubric_checkpoint.json"
    ckpt.write_text(json.dumps(checkpoint, indent=2) + "\n")
    with (ROOT / "runtime" / "state" / "w055_checkpoints.jsonl").open("a") as f:
        f.write(json.dumps(checkpoint, sort_keys=True) + "\n")

    # 5. outbox events (artifact x2 + review)
    ts = now_iso().replace(":", "").replace("+0800", "+0800")
    rep_sha, inst_sha = sha(report_path), sha(HERE / "check_a0_rubric.py")
    hf_event = [{
        "id": h["id"], "severity": h["severity"], "axis": h["axis"],
        "finding": h["finding"], "machine_evidence": h["machine_evidence"],
        "falsifier": h["falsifier"],
    } for h in hf]
    events = [
        {
            "event_id": f"w055-a0-rubric-artifact-report-{ts}",
            "event_type": "artifact",
            "created_at": now_iso(),
            "actor": "worker-055",
            "node_id": "A0",
            "gate": "G-AUDIT",
            "artifact_type": "independent_review_bundle",
            "path": "artifacts/worker-055/a0_rubric_verdict/report.json",
            "sha256": rep_sha,
            "validation_status": "unverified",
            "class_ids": report["class_ids"],
            "target_sha256": EXPECTED["evaluation_rubric.yaml"],
            "evidence_refs": [
                f"artifacts/worker-055/a0_rubric_verdict/report.json#{rep_sha[:12]}",
                f"evaluation_rubric.yaml#{EXPECTED['evaluation_rubric.yaml'][:12]}",
            ],
            "falsifier": report["falsifiers"][0],
        },
        {
            "event_id": f"w055-a0-rubric-artifact-instrument-{ts}",
            "event_type": "artifact",
            "created_at": now_iso(),
            "actor": "worker-055",
            "node_id": "A0",
            "gate": "G-AUDIT",
            "artifact_type": "checker",
            "path": "artifacts/worker-055/a0_rubric_verdict/check_a0_rubric.py",
            "sha256": inst_sha,
            "validation_status": "unverified",
            "class_ids": report["class_ids"],
            "target_sha256": EXPECTED["evaluation_rubric.yaml"],
            "evidence_refs": [f"artifacts/worker-055/a0_rubric_verdict/check_a0_rubric.py#{inst_sha[:12]}"],
            "falsifier": report["falsifiers"][3],
        },
        {
            "event_id": f"w055-a0-rubric-review-{ts}",
            "event_type": "review",
            "created_at": now_iso(),
            "actor": "worker-055",
            "reviewer": "worker-055",
            "node_id": "A0",
            "target_id": "A0",
            "gate": "G-AUDIT",
            "class_ids": report["class_ids"],
            "artifact": "evaluation_rubric.yaml",
            "artifact_sha256": EXPECTED["evaluation_rubric.yaml"],
            "reviewed_sha256": EXPECTED["evaluation_rubric.yaml"],
            "counts_as_full_schema_verdict": True,
            "verdict": report["verdict"],
            "score": report["score"],
            "hard_failures": hf_event,
            "findings": [
                "RESOLVED (machine-checked): no universal scalar score. The audit spot-check token "
                "is a prohibition mention at evaluation_rubric.yaml:10-13; five staged mutants that "
                "introduce real scalar-score uses are all caught (M1-M2), and the unmutated control "
                "is clean (M0).",
                "BLOCKING HF-055-A0-1: vocabulary disconnect - A0's genericity enum and per-class "
                "conclusion_primary sets do not cover residual_comeager / weak_cosmic_censorship / "
                "scc_c2_future_inextendibility / scc_c0_future_inextendibility, so a literal "
                "G-FORM/HF-02 reading rejects all three frozen schemas.",
                "ADVISORY ADV-055-A0-1: gates[G-AUDIT] names kappa but no kappa metric exists "
                "(metrics use Kish ESS).",
                "ADVISORY ADV-055-A0-2: accepted-claim-rate and cost-per-accepted-claim metrics "
                "absent from A0.metrics.",
            ],
            "evidence_refs": [
                f"artifacts/worker-055/a0_rubric_verdict/report.json#{rep_sha[:12]}",
                f"artifacts/worker-055/a0_rubric_verdict/check_a0_rubric.py#{inst_sha[:12]}",
                f"evaluation_rubric.yaml#{EXPECTED['evaluation_rubric.yaml'][:12]}",
                f"schemas/af_wcc_vacuum.yaml#{EXPECTED['schemas/af_wcc_vacuum.yaml'][:12]}",
                f"schemas/af_scc_c2_vacuum.yaml#{EXPECTED['schemas/af_scc_c2_vacuum.yaml'][:12]}",
                f"schemas/af_scc_c0_vacuum.yaml#{EXPECTED['schemas/af_scc_c0_vacuum.yaml'][:12]}",
            ],
            "next_falsifier": report["falsifiers"][2],
            "authority_note": report["authority"],
        },
    ]
    outbox = ROOT / "comms" / "outbox" / "worker-055.jsonl"
    with outbox.open("a") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    print(json.dumps({
        "status": "FINALIZED",
        "report_sha256": rep_sha,
        "instrument_sha256": inst_sha,
        "checkpoint": str(ckpt.relative_to(ROOT)),
        "events": [e["event_id"] for e in events],
        "outbox": str(outbox.relative_to(ROOT)),
        "bundle_files": len(files) + 1,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
