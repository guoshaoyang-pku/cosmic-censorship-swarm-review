#!/usr/bin/env python3
"""Emit worker-083 JSON events + manifest + checkpoint for W083-REV29-POSTAPPLY-INTEGRITY-01.

Order: re-run probe -> MANIFEST.json -> checkpoint.json -> validate every event with
research_map.schemas.validate_event -> append to comms/outbox/worker-083.jsonl ->
write runtime/state checkpoints -> final read-only freeze sweep.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

CN = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                      # .../ai4math-swarm
sys.path.insert(0, str(ROOT))
from research_map.schemas import validate_event  # noqa: E402

TASK = "W083-REV29-POSTAPPLY-INTEGRITY-01"
CLASSES = ["AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN"]
GATE = "G-FORM"
NODE = "F2b"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(p: Path, n: int = 12) -> str:
    return f"{p.relative_to(ROOT).as_posix()}#{sha256_file(p)[:n]}"


def now() -> str:
    return datetime.now(CN).isoformat()


def main() -> int:
    # 1. fresh probe
    subprocess.run([sys.executable, str(HERE / "check_rev29_postapply_integrity.py")], check=True)
    report = json.loads((HERE / "report.json").read_text())
    ev = json.loads((HERE / "evidence.json").read_text())
    checks = {c["id"]: c for c in report["checks"]}

    # 2. checkpoint (written before MANIFEST so MANIFEST can pin it)
    checkpoint = {
        "checkpoint_id": "w083-ckpt-5",
        "task_id": TASK,
        "worker": "worker-083",
        "created_at": now(),
        "status": "active",
        "verdict": report["verdict"],
        "no_completion_claim": True,
        "snapshot": {"revision": report["snapshot_revision"], "sha256": report["snapshot_sha256"]},
        "findings": {
            "lform01_open": report["lform01_open"],
            "lform02_binding_closed": report["lform02_binding_closed"],
            "freeze_drift_measured": report["freeze_drift_measured"],
            "live_defect_present": report["live_defect_present"],
            "hard_defects": report["hard_defects"],
        },
        "checks": {k: v["status"] for k, v in checks.items()},
        "controls_ok": report["controls_ok"],
        "canonical_writes": False,
        "evidence_refs": [ref(HERE / "report.json"), ref(HERE / "evidence.json")],
    }
    (HERE / "checkpoint.json").write_text(json.dumps(checkpoint, indent=1) + "\n")

    # 3. MANIFEST (pins every deliverable except itself)
    files = sorted(p for p in HERE.rglob("*") if p.is_file()
                   and "__pycache__" not in p.parts and p.name not in {"MANIFEST.json"})
    manifest = {
        "task_id": TASK,
        "worker": "worker-083",
        "created_at": now(),
        "snapshot_revision": report["snapshot_revision"],
        "snapshot_sha256": report["snapshot_sha256"],
        "verdict": report["verdict"],
        "files": {p.relative_to(HERE).as_posix(): {"sha256": sha256_file(p), "bytes": p.stat().st_size}
                  for p in files},
    }
    (HERE / "MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n")

    # 4. events
    frozen = HERE / "snapshot/FROZEN.json"
    f2b = HERE / "snapshot/schemas/af_scc_c0_vacuum.yaml"
    drift = HERE / "snapshot/formulation_evidence/variant_delta_check.json"
    report_p, evidence_p = HERE / "report.json", HERE / "evidence.json"
    manifest_p = HERE / "MANIFEST.json"
    instrument = HERE / "check_rev29_postapply_integrity.py"
    base = [ref(frozen), ref(f2b), ref(drift), ref(report_p)]
    common = {"actor": "worker-083", "task_id": TASK, "gate": GATE, "class_id": ";".join(CLASSES),
              "class_ids": CLASSES}
    events = [
        {**common, "event_id": "w083rev29postapply01-start", "event_type": "status", "created_at": now(),
         "node_id": NODE, "status": "active", "hours": 0.1,
         "summary": "Took one bounded class-bound task (no inbox card for slot 083): post-apply integrity of FROZEN rev29. Snapshot bound at FROZEN.json#3d9e3d77 (rev29, 48 pins) plus a copy of F2b b2ab6acb2bbe.",
         "evidence_refs": base, "next_falsifier": "Any snapshot pin not hashing as cited voids the measurement."},
        {**common, "event_id": "w083rev29postapply01-claim-001", "event_type": "claim", "created_at": now(),
         "conclusion_type": "stability_result", "claims_theorem_status": False,
         "statement": "At the pinned snapshot (FROZEN rev29 sha256 3d9e3d77fd871019..., frozen_at 00:55:02, 48 pins), the L-FORM-01 directional defect is still open in the frozen F2b artifact: schemas/af_scc_c0_vacuum.yaml and its mirror, both sha256 b2ab6acb2bbe7f8690..., line 246 reason reads 'C2 is a strictly larger extension class' while the same artifact's line 239 declares E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2, i.e. C2 is strictly smaller. The rev28->rev29 delta census shows rev29 changed only revised_at, revision_history, revision and f0_binding, so the rev29 apply did not close it; the defect is still present in the live canonical file at measurement time. Separately, L-FORM-02 is closed at rev29 (binding pins evidence 9e335e9ba1bf and checker de356d99, both matching disk), and a freeze-drift incident was measured: pinned variant_delta_check.json fc6ee058 was overwritten at 00:56:03 to 0b23f0b29232 with valid:false (base-hash drift for variant CH and SET); the lead re-based the deltas and re-froze rev29 in place at 00:57:26 (live FROZEN 815e0807, 50 pins, verify_frozen exit 0). Root cause of the drift is still present: artifacts/formulation/tools/check_variant_deltas.py:33 writes the canonical evidence path unconditionally with no write guard.",
         "assumptions": ["probe reads only snapshot bytes plus read-only live hashes",
                         "the artifact's own containment line defines the required size word",
                         "worker events cannot move gates or node status"],
         "falsifier": "FALSE if any snapshot pin differs; if the frozen F2b row reads 'strictly smaller' at b2ab6acb2bbe; if the rev28 baseline 55d0a1ea row differs from the snapshot row; if the frozen binding does not pin 9e335e9ba1bf / de356d99; if the captured drift bytes do not hash 0b23f0b29232 or do not declare valid:false, or if check_variant_deltas.py has a write guard; or if the four sandbox controls do not behave as tabled.",
         "evidence_refs": base + [ref(evidence_p), ref(manifest_p)],
         "artifact_refs": [ref(report_p), ref(evidence_p), ref(instrument), ref(manifest_p)]},
    ]
    for name, atype in [("report.json", "verification_report"), ("evidence.json", "evidence"),
                        ("REPORT.md", "verification_report"), ("MANIFEST.json", "artifact_manifest"),
                        ("check_rev29_postapply_integrity.py", "instrument"),
                        ("snapshot/FROZEN.json", "pinned_input"),
                        ("snapshot/schemas/af_scc_c0_vacuum.yaml", "pinned_input"),
                        ("snapshot/formulation_evidence/variant_delta_check.json", "pinned_input"),
                        ("checkpoint.json", "checkpoint")]:
        p = HERE / name
        events.append({**common, "event_id": f"w083rev29postapply01-artifact-{name.replace('/', '-').replace('.', '-')}",
                       "event_type": "artifact", "created_at": now(), "node_id": NODE,
                       "artifact_type": atype, "path": p.relative_to(ROOT).as_posix(),
                       "sha256": sha256_file(p), "validation_status": "unverified",
                       "note": f"{TASK} deliverable: {name}"})
    events.append({**common, "event_id": "w083rev29postapply01-blocker-001", "event_type": "blocker",
                   "created_at": now(), "node_id": NODE,
                   "description": "HARD (L-FORM-01 open at rev29): frozen F2b b2ab6acb2bbe line 246 claims C2 is a 'strictly larger extension class' while the artifact's own line 239 has E_C2 strictly inside E_C0, so G-FORM accept verdicts bound to this hash would bind a directional inconsistency. Latent (freeze hygiene): artifacts/formulation/tools/check_variant_deltas.py:33 unconditionally rewrites the pinned canonical evidence artifacts/formulation/evidence/variant_delta_check.json with no write guard, which produced the measured 00:56:03 drift on the 3d9e3d77 instance of rev29 (repaired by the lead's in-place re-freeze at 00:57:26, 815e0807, 50 pins).",
                   "needed_to_unblock": "Lead-authorised one-word repair 'larger' -> 'smaller' in both frozen F2b copies plus a fresh freeze revision, then two independent accept verdicts at the new hash; and a --write/dry-run guard on check_variant_deltas.py (or its removal from the freeze set).",
                   "evidence_refs": base + [ref(manifest_p)],
                   "falsifier": "FALSE if the frozen F2b row already reads 'strictly smaller' at b2ab6acb2bbe, or if check_variant_deltas.py writes only under an explicit --write flag."})
    events.append({**common, "event_id": "w083rev29postapply01-complete", "event_type": "status",
                   "created_at": now(), "node_id": NODE, "status": "active", "hours": 0.6,
                   "summary": f"{TASK} complete as a bounded worker deliverable (not a node transition; workers cannot set done/passed). Verdict {report['verdict']}: L-FORM-01 open in both frozen F2b copies at b2ab6acb2bbe (hard), L-FORM-02 closed, freeze drift measured and repaired by the lead, latent checker write defect still pinned. 11 checks / 4 sandbox controls; canonical_writes=false.",
                   "evidence_refs": base + [ref(manifest_p), ref(HERE / 'checkpoint.json')],
                   "next_falsifier": "Re-run check_rev29_postapply_integrity.py after any freeze movement; falsified if the F2b row reads 'smaller' at b2ab6acb2bbe or if the captured drift bytes no longer match 0b23f0b29232."})

    for e in events:
        validate_event(e)
    out = ROOT / "comms/outbox/worker-083.jsonl"
    with open(out, "a") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    # 5. runtime-state checkpoint
    state = ROOT / "runtime/state"
    (state / "w083_checkpoint_5.json").write_text(json.dumps(checkpoint, indent=1) + "\n")
    with open(state / "w083_checkpoints.jsonl", "a") as f:
        f.write(json.dumps({**checkpoint, "checkpoint_sha256": sha256_file(HERE / 'checkpoint.json')}) + "\n")

    # 6. final read-only sweep
    proc = subprocess.run([sys.executable, str(ROOT / "artifacts/formulation/tools/verify_frozen.py")],
                          cwd=str(ROOT), capture_output=True, text=True)
    print(json.dumps({"events_appended": len(events), "events_validated": True,
                      "manifest_files": len(manifest["files"]), "verdict": report["verdict"],
                      "verify_frozen_exit": proc.returncode,
                      "verify_frozen_tail": proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
