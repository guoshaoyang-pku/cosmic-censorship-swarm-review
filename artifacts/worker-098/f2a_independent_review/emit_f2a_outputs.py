#!/usr/bin/env python3
"""Emit worker-098 checkpoint + comms outbox events for W098-F2A-INDEP-VERDICT-01."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
HERE = ROOT / "artifacts/worker-098/f2a_independent_review"
STATE = ROOT / "runtime/state"
CST = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(CST).replace(microsecond=0).isoformat()


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ts = now_iso()
    evidence_p = HERE / "f2a_independent_evidence.json"
    verdict_p = HERE / "f2a_independent_verdict.json"
    evidence = json.loads(evidence_p.read_text())
    verdict = json.loads(verdict_p.read_text())
    target_sha = evidence["reviewed_sha256"]
    short = target_sha[:12]
    assert verdict["reviewed_sha256"] == target_sha, "verdict/evidence hash mismatch"

    artifacts = {
        str(evidence_p.relative_to(ROOT)): sha(evidence_p),
        str(verdict_p.relative_to(ROOT)): sha(verdict_p),
        str((HERE / "verify_f2a.py").relative_to(ROOT)): sha(HERE / "verify_f2a.py"),
        str((HERE / "af_scc_c2_vacuum.snapshot.yaml").relative_to(ROOT)):
            sha(HERE / "af_scc_c2_vacuum.snapshot.yaml"),
        str((HERE / "gate_report_f2a_4f97273ef440.json").relative_to(ROOT)):
            sha(HERE / "gate_report_f2a_4f97273ef440.json"),
    }

    # ---------------- checkpoint ----------------
    checkpoint = {
        "worker": "worker-098",
        "checkpoint": 1,
        "checkpoint_at": ts,
        "task_id": "W098-F2A-INDEP-VERDICT-01",
        "assignment_source": "self-taken (no inbox card for worker-098; fleet launched 00:16:57)",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "verdict": verdict["verdict"],
        "score": verdict["score"],
        "hard_failures": verdict["hard_failures"],
        "reviewed_sha256": target_sha,
        "canonical_path": evidence["canonical_path"],
        "canonical_hash_at_end": evidence["canonical_hash_at_end"],
        "drift_during_review": evidence["drift_during_review"],
        "stage_results": {
            "canonical_gate": evidence["stage_1_canonical_gate"]["verdict"],
            "classsep_hard_findings": len(evidence["stage_2_class_separation"]["hard_findings"]),
            "contract_checks_ok": (
                f"{sum(1 for c in evidence['stage_3_contract_checks'] if c['ok'])}"
                f"/{len(evidence['stage_3_contract_checks'])}"),
            "mutation_controls_detected": (
                f"{sum(1 for c in evidence['stage_4_controls'] if c['detected'])}"
                f"/{len(evidence['stage_4_controls'])}"),
        },
        "artifacts": artifacts,
        "events_emitted": [],
        "authority": ("no gate verdict, no node completion, no self-pass; F2a/G-FORM remain "
                      "with controller + lead-formulation"),
        "numerics_lock": "respected: no N1 work, no numerics/spherical_solver/",
        "scope_limit": evidence["scope_limit"],
        "next_falsifier": evidence["next_falsifier"],
        "hours_spent_estimate": 0.5,
    }

    # ---------------- outbox events ----------------
    events = [
        {
            "event_id": f"w098-f2a-claim-{ts}",
            "event_type": "status",
            "created_at": ts,
            "actor": "worker-098",
            "node_id": "F2a",
            "class_id": "AF-SCC-C2-VAC-GEN",
            "status": "active",
            "hours": 0.1,
            "summary": ("No assignment card exists in comms/inbox for worker-098 (fleet launched "
                        "00:16:57). Took one bounded class-bound task: W098-F2A-INDEP-VERDICT-01 = "
                        "independent full-schema verification of F2a AF-SCC-C2-VAC-GEN at canonical "
                        f"sha256 {short}, using three independent stages plus mutation controls. "
                        "Does not claim node completion or any gate verdict."),
            "evidence_refs": [f"schemas/af_scc_c2_vacuum.yaml#{short}",
                              "research_map/ASTRA_HANDOFF.md:18-34", "comms/PROTOCOL.md"],
            "next_falsifier": evidence["next_falsifier"],
        },
        {
            "event_id": f"w098-f2a-art-evidence-{ts}",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "worker-098",
            "node_id": "F2a",
            "class_id": "AF-SCC-C2-VAC-GEN",
            "artifact_type": "review_evidence",
            "path": str(evidence_p.relative_to(ROOT)),
            "sha256": artifacts[str(evidence_p.relative_to(ROOT))],
            "validation_status": "unverified",
            "evidence_refs": [f"schemas/af_scc_c2_vacuum.yaml#{short}"],
            "next_falsifier": evidence["next_falsifier"],
        },
        {
            "event_id": f"w098-f2a-art-verdict-{ts}",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "worker-098",
            "node_id": "F2a",
            "class_id": "AF-SCC-C2-VAC-GEN",
            "artifact_type": "review_record",
            "path": str(verdict_p.relative_to(ROOT)),
            "sha256": artifacts[str(verdict_p.relative_to(ROOT))],
            "validation_status": "unverified",
            "evidence_refs": [f"schemas/af_scc_c2_vacuum.yaml#{short}"],
            "next_falsifier": evidence["next_falsifier"],
        },
        {
            "event_id": f"w098-f2a-review-{ts}",
            "event_type": "review",
            "created_at": ts,
            "actor": "worker-098",
            "reviewer": "worker-098",
            "target_id": "F2a",
            "class_id": "AF-SCC-C2-VAC-GEN",
            "verdict": verdict["verdict"],
            "score": verdict["score"],
            "reviewed_sha256": target_sha,
            "hard_failures": verdict["hard_failures"],
            "findings": verdict["findings"],
            "evidence_refs": verdict["evidence_refs"],
            "artifact_refs": [str(evidence_p.relative_to(ROOT))],
            "scope_limit": verdict["scope_limit"],
            "next_falsifier": verdict["next_falsifier"],
        },
        {
            "event_id": f"w098-f2a-done-{ts}",
            "event_type": "status",
            "created_at": ts,
            "actor": "worker-098",
            "node_id": "F2a",
            "class_id": "AF-SCC-C2-VAC-GEN",
            "status": "active",
            "completion_claim": True,
            "hours": 0.4,
            "summary": (f"W098-F2A-INDEP-VERDICT-01 bounded task complete at {short}: verdict "
                        f"{verdict['verdict']} score {verdict['score']}. Canonical gate pass, 0 "
                        "class-separation hard findings, 22/22 contract+cross-field checks, 5/5 "
                        "mutation controls detected, no drift during review. This is a completion "
                        "claim for the bounded task only, not node completion, not a gate verdict; "
                        "lead/controller must bind or reject."),
            "evidence_refs": [f"artifacts/worker-098/f2a_independent_review/f2a_independent_evidence.json#{artifacts[str(evidence_p.relative_to(ROOT))][:12]}",
                              f"schemas/af_scc_c2_vacuum.yaml#{short}"],
            "next_falsifier": evidence["next_falsifier"],
        },
    ]
    checkpoint["events_emitted"] = [e["event_id"] for e in events]

    # ---------------- write ----------------
    STATE.mkdir(parents=True, exist_ok=True)
    cp_path = STATE / "w098_checkpoint_1.json"
    cp_path.write_text(json.dumps(checkpoint, indent=1) + "\n")
    (STATE / "w098_latest_checkpoint.json").write_text(json.dumps(checkpoint, indent=1) + "\n")
    with (STATE / "w098_checkpoints.jsonl").open("a") as fh:
        fh.write(json.dumps(checkpoint) + "\n")

    outbox = ROOT / "comms/outbox/worker-098.jsonl"
    with outbox.open("a") as fh:
        for e in events:
            fh.write(json.dumps(e) + "\n")

    # ---------------- self-validation ----------------
    ok = True
    for e in events:
        for req in ("event_id", "event_type", "created_at", "actor"):
            if not e.get(req):
                print(f"SCHEMA FAIL: {e.get('event_id')} missing {req}")
                ok = False
    for line in outbox.read_text().splitlines():
        try:
            o = json.loads(line)
        except Exception as ex:
            print("OUTBOX PARSE FAIL:", ex)
            ok = False
            continue
        for req in ("event_id", "event_type", "created_at", "actor"):
            if not o.get(req):
                print("OUTBOX SCHEMA FAIL:", o)
                ok = False
    print(json.dumps({
        "outbox": str(outbox.relative_to(ROOT)),
        "events_appended": len(events),
        "checkpoint": str(cp_path.relative_to(ROOT)),
        "artifacts": artifacts,
        "self_validation": "PASS" if ok else "FAIL",
    }, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
