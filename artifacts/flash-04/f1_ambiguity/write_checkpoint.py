#!/usr/bin/env python3
"""Write the worker-04 checkpoint for the F1 freeze rebind.

Writes runtime/state/w04_checkpoint_f1_<sha8>.json, appends runtime/state/w04_checkpoints.jsonl,
and appends a checkpoint row to artifacts/flash-04/f1_ambiguity/CHECKPOINTS.md.

Usage: python3 artifacts/flash-04/f1_ambiguity/write_checkpoint.py
Exit: 0 = checkpoint written; 2 = prerequisite missing.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REBIND = ROOT / "artifacts/flash-04/f1_ambiguity/rebind_current_delta_report.json"
VERIFY = ROOT / "artifacts/flash-04/f1_ambiguity/frozen_current_verification.json"
SUITE = ROOT / "schemas/f1_falsifier_tests.jsonl"
CANON = ROOT / "schemas/af_wcc_vacuum.yaml"
AUTH = ROOT / "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
F0 = ROOT / "research_map/formulation_taxonomy.yaml"
CP_MD = ROOT / "artifacts/flash-04/f1_ambiguity/CHECKPOINTS.md"
CST = timezone(timedelta(hours=8))


def sh(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    for p in (REBIND, VERIFY, SUITE, CANON, AUTH, FROZEN, F0):
        if not p.exists():
            print(f"missing prerequisite: {p}")
            return 2
    rebind = json.loads(REBIND.read_text())
    verify = json.loads(VERIFY.read_text())
    new_sha = sh(CANON)
    new8 = new_sha[:8]
    ts = datetime.now(CST).isoformat(timespec="seconds")
    cp_id = f"w04-cp15-f1-{new8}"
    artifacts = {
        "schemas/f1_falsifier_tests.jsonl": sh(SUITE),
        "artifacts/flash-04/f1_ambiguity/rebind_current_delta_report.json": sh(REBIND),
        "artifacts/flash-04/f1_ambiguity/frozen_current_verification.json": sh(VERIFY),
        "artifacts/flash-04/f1_ambiguity/rebind_current.py": sh(ROOT / "artifacts/flash-04/f1_ambiguity/rebind_current.py"),
        "artifacts/flash-04/f1_ambiguity/verify_freeze_current.py": sh(ROOT / "artifacts/flash-04/f1_ambiguity/verify_freeze_current.py"),
        "artifacts/flash-04/f1_ambiguity/emit_freeze_events.py": sh(ROOT / "artifacts/flash-04/f1_ambiguity/emit_freeze_events.py"),
        "schemas/af_wcc_vacuum.yaml": new_sha,
        "artifacts/formulation/schemas/af_wcc_vacuum.yaml": sh(AUTH),
        "artifacts/formulation/FROZEN.json": sh(FROZEN),
        "research_map/formulation_taxonomy.yaml": sh(F0),
    }
    checkpoint = {
        "checkpoint_id": cp_id,
        "created_at": ts,
        "actor": "deepseek-flash-04",
        "assignment": "asg-2026-09-11-F1-deepseek-flash-04-13",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "status": "active",
        "hours": 0.5,
        "binding": {
            "path": "schemas/af_wcc_vacuum.yaml",
            "sha256": new_sha,
            "frozen_revision": rebind.get("binding", {}).get("frozen_manifest_revision"),
            "schema_internal_revision": rebind.get("binding", {}).get("schema_internal_revision"),
        },
        "prior_binding": {"sha256": rebind.get("prior_binding", {}).get("sha256")},
        "canonical_path": {"measured": new_sha, "authoring_measured": sh(AUTH), "matches": sh(AUTH) == new_sha},
        "f0_binding": rebind.get("f0_binding_state"),
        "artifacts": artifacts,
        "results": {
            "tests_total": rebind.get("tests_total"),
            "carried": rebind.get("carried"),
            "new": rebind.get("new"),
            "probe_failures": len(rebind.get("probe_failures", [])),
            "probe_flips": len(rebind.get(f"probe_flips_vs_{str(rebind.get('prior_binding', {}).get('sha256'))[:8]}", [])),
            "delta_counts": rebind.get("delta_counts"),
            "verification_verdict": verify.get("verdict"),
            "verification_hard_failures": verify.get("failures"),
            "verification_drift_findings": [d.get("id") for d in verify.get("drift_findings", [])],
            "probes_pass": verify.get("probe_recheck", {}).get("probes_pass"),
            "probes_total": verify.get("probe_recheck", {}).get("probes_total"),
            "open_obligations": [o.get("test") for o in rebind.get("open_obligations_retained", [])],
        },
        "events_emitted": "see comms/outbox/deepseek-flash-04.jsonl entries with created_at >= " + ts,
        "next_falsifier": verify.get("next_falsifier"),
        "reproduce": "python3 artifacts/flash-04/f1_ambiguity/rebind_current.py && python3 artifacts/flash-04/f1_ambiguity/verify_freeze_current.py",
        "does_not_claim": [
            "G-FORM verdict",
            "node F1 done",
            "theorem or counterexample",
            "closure of AMB-01/02/03/15",
            "independent audit of the rebind",
        ],
    }
    cp_dir = ROOT / "runtime/state"
    (cp_dir / f"w04_checkpoint_f1_{new8}.json").write_text(json.dumps(checkpoint, indent=1, ensure_ascii=False) + "\n")
    with open(cp_dir / "w04_checkpoints.jsonl", "a") as f:
        f.write(json.dumps(checkpoint, ensure_ascii=False, sort_keys=True) + "\n")
    row = (f"| {ts[11:16]} | CP15 rebind {new8} | suite rebound {str(rebind.get('prior_binding', {}).get('sha256'))[:8]} -> {new8}; "
           f"{rebind.get('tests_total')} tests ({rebind.get('new')} new); "
           f"{verify.get('probe_recheck', {}).get('probes_pass')}/{verify.get('probe_recheck', {}).get('probes_total')} probes pass; "
           f"verdict {verify.get('verdict')}; F0 cross-artifact match={rebind.get('f0_binding_state', {}).get('match')} |\n")
    with open(CP_MD, "a") as f:
        f.write(row)
    print(json.dumps({"checkpoint": cp_id, "path": str((cp_dir / f'w04_checkpoint_f1_{new8}.json').relative_to(ROOT)),
                      "checkpoint_sha256": sh(cp_dir / f"w04_checkpoint_f1_{new8}.json"),
                      "checkpoints_jsonl_sha256": sh(cp_dir / "w04_checkpoints.jsonl"),
                      "checkpoints_md_sha256": sh(CP_MD)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
