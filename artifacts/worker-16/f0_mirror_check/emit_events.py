#!/usr/bin/env python3
"""Emit the W16-F0-MIRROR-VERIFY-01 events + worker checkpoint idempotently.

Writes only:
  - comms/outbox/worker-16.jsonl                (append, skips existing event_ids)
  - runtime/state/w016_checkpoint_f0mirror.json (replace)
  - runtime/state/w16_checkpoints.jsonl         (append, skips existing checkpoint_id)
  - artifacts/worker-16/CHECKPOINTS.md          (append, skips existing heading)

Run with --dry-run to print without writing.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
D = ROOT / "artifacts/worker-16/f0_mirror_check"
OUTBOX = ROOT / "comms/outbox/worker-16.jsonl"
CKPT = ROOT / "runtime/state/w016_checkpoint_f0mirror.json"
CKPT_LOG = ROOT / "runtime/state/w16_checkpoints.jsonl"
CKPT_MD = ROOT / "artifacts/worker-16/CHECKPOINTS.md"

DRY = "--dry-run" in sys.argv


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now() -> str:
    import subprocess
    return subprocess.run(["date", "-Is"], capture_output=True, text=True).stdout.strip()


def existing_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    ids = set()
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            ids.add(json.loads(line)["event_id"])
        except Exception:
            continue
    return ids


def main() -> int:
    v = json.loads((D / "verification.json").read_text())
    assert v["verdict"] == "CONFIRMED", v["verdict"]
    files = {name: {"path": f"artifacts/worker-16/f0_mirror_check/{name}",
                    "sha256": sha(D / name), "bytes": (D / name).stat().st_size}
             for name in ("verification.json", "verify_mirror_claim.py", "verification.sha256", "REPORT.md", "emit_events.py")}
    for name, meta in files.items():
        meta["evidence_ref"] = f"{meta['path']}#sha256:{meta['sha256'][:12]}"
    ckpt_id = "w16-ckpt-f0-mirror-verify-01"
    ts = now()
    # run-stable ids: a re-run of this emitter must append 0, so ids carry no timestamp

    review = {
        "event_id": "w16-F0-MIRROR-VERIFY-01-review",
        "event_type": "review",
        "created_at": ts,
        "actor": "worker-16",
        "reviewer": "worker-16",
        "target_id": "F0-MIRROR-CONFLICT",
        "target_evidence": v["target_evidence"],
        "verdict": "accept",
        "score": 4.5,
        "hard_failures": [],
        "findings": [
            {"id": "F-16MV-1", "label": "B", "severity": "blocking-for-target", "result": "CONFIRMED",
             "detail": "canonical 276009f4 (35145 b) and authoring c8e979a1 (20937 b) are different artifacts: "
                       "class_ids/classes/transfer_rules vs class_contracts/axis_registry/implication_ledger, with "
                       "no load-bearing key overlap."},
            {"id": "F-16MV-2", "label": "B", "severity": "blocking-for-target", "result": "CONFIRMED",
             "detail": "byte-identical publication in either direction destroys a frozen input: staged substitution "
                       "runs crash with KeyError 'class_contracts' (authoring<-canonical) and KeyError 'class_ids' "
                       "(canonical<-authoring); unsubstituted control exits 0 CONSISTENT."},
            {"id": "F-16MV-3", "label": "B", "severity": "blocking-for-target", "result": "CONFIRMED",
             "detail": "all three frozen schemas' class_contract_pointer resolve only in the authoring supplement, "
                       "and FROZEN rev26 pins both bytes; the supplement is load-bearing, not a duplicate tree."},
            {"id": "F-16MV-4", "label": "N", "severity": "non-blocking", "result": "OPEN",
             "detail": "accept coverage at the canonical hash is ambiguous: F0-targeted accepts exist "
                       "(astra-lead-audit, worker-040) but none carries top-level artifact_sha256==276009f4, so the "
                       "00:24:40 gate scan read 0 distinct accepts. Controller to decide whether evidence_refs-bound "
                       "accepts count; this review does not move G-F0."},
        ],
        "node_id": "F0",
        "class_ids": v["class_ids"],
        "gate": "G-F0",
        "group_id": "formulation",
        "evidence_refs": [files["verification.json"]["evidence_ref"], files["verify_mirror_claim.py"]["evidence_ref"],
                          v["target_evidence"], "artifacts/formulation/FROZEN.json#sha256:2554e276a0db",
                          "research_map/formulation_taxonomy.yaml#sha256:276009f4f63d",
                          "artifacts/formulation/formulation_taxonomy.yaml#sha256:c8e979a1eb48",
                          "research_map/research_map.json"],
        "claims_completion": False,
        "next_falsifier": v["falsifier"],
    }

    artifacts = []
    for name, atype in (("verification.json", "independent_verification_report"),
                        ("verify_mirror_claim.py", "verification_harness"),
                        ("REPORT.md", "verification_summary"),
                        ("verification.sha256", "report_digest"),
                        ("emit_events.py", "event_emitter")):
        artifacts.append({
            "event_id": f"w16-F0-MIRROR-VERIFY-01-artifact-{name.replace(chr(46), chr(45))}",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "worker-16",
            "artifact_type": atype,
            "path": files[name]["path"],
            "sha256": files[name]["sha256"],
            "bytes": files[name]["bytes"],
            "validation_status": "unverified",
            "node_id": "F0",
            "class_ids": v["class_ids"],
            "gate": "G-F0",
            "group_id": "formulation",
            "task_id": v["task_id"],
            "claims_completion": False,
            "evidence_refs": [files[name]["evidence_ref"], v["target_evidence"]],
            "summary": (f"Independent verification of F0-MIRROR-CONFLICT: {v['verdict']}; "
                        f"{sum(1 for c in v['checks'] if c['verdict'] == 'PASS')} PASS / "
                        f"{sum(1 for c in v['checks'] if c['verdict'] == 'INFO')} INFO / "
                        f"{sum(1 for c in v['checks'] if c['verdict'] == 'FAIL')} FAIL. "
                        "Read-only on all repo artifacts; substitutions staged only under worker-16."),
            "next_falsifier": v["next_falsifier"] if name == "verification.json" else v["falsifier"],
        })

    status = {
        "event_id": "w16-F0-MIRROR-VERIFY-01-status",
        "event_type": "status",
        "created_at": ts,
        "actor": "worker-16",
        "node_id": "F0",
        "status": "active",
        "hours": 0.3,
        "summary": ("CHECKPOINT: bounded self-claimed class-bound task complete (worker-level, not a gate verdict). "
                    "Independently verified the F0 mirror-conflict evidence behind leadform-blocker-0007: canonical "
                    "276009f4 vs authoring c8e979a1 are two different artifacts; both destructive publications fail "
                    "with KeyError in a staged run of the pinned checker; FROZEN rev26 pins both; schema pointers "
                    "resolve only in the supplement. Verdict CONFIRMED (13 PASS / 2 INFO / 0 FAIL; positive + negative "
                    "controls). No repo artifact was modified. G-F0 stays pending; REC-1/REC-2 remains controller "
                    "authority."),
        "evidence_refs": [files["verification.json"]["evidence_ref"], files["verify_mirror_claim.py"]["evidence_ref"],
                          files["REPORT.md"]["evidence_ref"], v["target_evidence"],
                          "artifacts/formulation/FROZEN.json#sha256:2554e276a0db",
                          "research_map/formulation_taxonomy.yaml#sha256:276009f4f63d",
                          "artifacts/formulation/formulation_taxonomy.yaml#sha256:c8e979a1eb48"],
        "class_ids": v["class_ids"],
        "gate": "G-F0",
        "group_id": "formulation",
        "task_id": v["task_id"],
        "claims_completion": False,
        "next_falsifier": v["next_falsifier"],
    }

    events = [review, *artifacts, status]
    seen = existing_ids(OUTBOX)
    new = [e for e in events if e["event_id"] not in seen]
    if not DRY:
        with OUTBOX.open("a") as f:
            for e in new:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

    ckpt = {
        "checkpoint_id": ckpt_id,
        "worker": "worker-16",
        "actor": "deepseek-flash-16",
        "pass": "bounded execution worker, worker=016 (3rd pass)",
        "checkpoint_at": ts,
        "self_claimed_task": {
            "reason": "No assignment addressed to worker-016/deepseek-flash-16 was unclaimed after 00:25; "
                      "leadform-blocker-0007 (F0 publication adjudication) was on the gate critical path with no "
                      "independent verification of its evidence.",
            "target": v["target_evidence"],
            "blocker": v["target_blocker"],
            "node_id": "F0",
            "class_ids": v["class_ids"],
            "gate": "G-F0",
        },
        "verdict": v["verdict"],
        "checks": {c["id"]: c["verdict"] for c in v["checks"]},
        "deliverables": files,
        "findings": [f["id"] + " " + f["result"] for f in review["findings"]],
        "hours_this_pass": 0.3,
        "read_only": v["read_only_statement"],
        "untouched_shared_files": [
            "research_map/formulation_taxonomy.yaml",
            "artifacts/formulation/formulation_taxonomy.yaml",
            "artifacts/formulation/evidence/taxonomy_consistency.json",
            "artifacts/formulation/FROZEN.json",
            "schemas/af_wcc_vacuum.yaml",
            "schemas/af_scc_c2_vacuum.yaml",
            "schemas/af_scc_c0_vacuum.yaml",
        ],
        "falsifier": v["falsifier"],
        "next_falsifier": v["next_falsifier"],
        "authority_note": "worker event cannot set validation_status=passed, node status=done, or a gate verdict; "
                          "REC-1/REC-2 adjudication is controller authority.",
        "emitted_event_ids": [e["event_id"] for e in events],
        "emitted_new": len(new),
        "map_snapshot_at_read": {"path": "research_map/research_map.json",
                                 "sha256": sha(ROOT / "research_map/research_map.json")[:12],
                                 "note": "re-measure before citing; controller is writing"},
    }
    if not DRY:
        CKPT.write_text(json.dumps(ckpt, indent=2) + "\n")
        log_seen = CKPT_LOG.read_text() if CKPT_LOG.exists() else ""
        if ckpt_id not in log_seen:
            with CKPT_LOG.open("a") as f:
                f.write(json.dumps({"checkpoint_at": ts, "checkpoint_id": ckpt_id, "node_id": "F0",
                                    "path": str(CKPT.relative_to(ROOT)), "task_id": v["task_id"],
                                    "task_state": "bounded independent verification complete; G-F0 unchanged",
                                    "verdict": v["verdict"], "worker": "worker-16",
                                    "sha256": sha(CKPT)}) + "\n")
        heading = "## CKPT-10 — F0 mirror-conflict independent verification (W16-F0-MIRROR-VERIFY-01)"
        if heading not in CKPT_MD.read_text():
            with CKPT_MD.open("a") as f:
                f.write(f"\n{heading}\n"
                        f"- Self-claimed bounded task: no unclaimed worker-016 assignment; verified the evidence "
                        f"behind `leadform-blocker-0007` instead of duplicating any prior pass.\n"
                        f"- Verdict **{v['verdict']}** on {v['target_evidence']}: canonical `276009f4` (35145 b) vs "
                        f"authoring `c8e979a1` (20937 b) are two different artifacts; staged substitutions crash with "
                        f"`KeyError: 'class_contracts'` / `KeyError: 'class_ids'`; control exits 0 CONSISTENT; FROZEN "
                        f"rev26 pins both; all three schema pointers resolve only in the supplement.\n"
                        f"- 13 PASS / 2 INFO / 0 FAIL with positive and negative controls. Two INFO findings: accept "
                        f"coverage at the canonical hash (evidence_refs-bound accept not counted by the 00:24:40 "
                        f"scan) and superseded lineage `565a6e505188`.\n"
                        f"- Artifacts: `f0_mirror_check/verification.json` `{files['verification.json']['sha256'][:12]}`, "
                        f"`verify_mirror_claim.py` `{files['verify_mirror_claim.py']['sha256'][:12]}`, "
                        f"`REPORT.md` `{files['REPORT.md']['sha256'][:12]}`. Read-only on all repo artifacts; no "
                        f"node completion or gate verdict claimed. REC-1/REC-2 stays controller authority.\n"
                        f"- Emitted {len(new)} new outbox events (idempotent re-run appends 0).\n")
    print(json.dumps({"dry_run": DRY, "events_total": len(events), "new_appended": len(new),
                      "event_ids": [e["event_id"] for e in events], "deliverables": files,
                      "checkpoint": ckpt_id}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
