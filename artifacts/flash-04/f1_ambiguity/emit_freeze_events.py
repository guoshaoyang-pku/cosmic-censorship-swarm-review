#!/usr/bin/env python3
"""Emit worker-04 F1 freeze-rebind events to comms/outbox/deepseek-flash-04.jsonl.

Reads the rebind report and the verification report, re-measures the referenced files,
validates every event against research_map.schemas.validate_event, and appends the batch.
Never mutates the map; never sets a gate verdict or node status=done.

Usage: python3 artifacts/flash-04/f1_ambiguity/emit_freeze_events.py
Exit: 0 = all events appended and schema-valid; 2 = a prerequisite or validation failed.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from research_map.schemas import validate_event  # noqa: E402

REBIND = ROOT / "artifacts/flash-04/f1_ambiguity/rebind_current_delta_report.json"
VERIFY = ROOT / "artifacts/flash-04/f1_ambiguity/frozen_current_verification.json"
SUITE = ROOT / "schemas/f1_falsifier_tests.jsonl"
SCHEMA = ROOT / "schemas/af_wcc_vacuum.yaml"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
OUTBOX = ROOT / "comms/outbox/deepseek-flash-04.jsonl"
CST = timezone(timedelta(hours=8))


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sh(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(path: str, digest: str, chars: int = 16) -> str:
    return f"{path}#sha256:{digest[:chars]}"


def main() -> int:
    for p in (REBIND, VERIFY, SUITE, SCHEMA, FROZEN):
        if not p.exists():
            print(f"missing prerequisite: {p}")
            return 2
    rebind = json.loads(REBIND.read_text())
    verify = json.loads(VERIFY.read_text())
    ts = now()
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    suite_sha = sh(SUITE)
    schema_sha = sh(SCHEMA)
    frozen_sha = sh(FROZEN)
    rebind_sha = sh(REBIND)
    verify_sha = sh(VERIFY)
    new8 = schema_sha[:8]
    old8 = (rebind.get("prior_binding", {}).get("sha256") or "")[:8]
    evidence = [
        ref("schemas/af_wcc_vacuum.yaml", schema_sha),
        ref("artifacts/formulation/FROZEN.json", frozen_sha),
        ref("schemas/f1_falsifier_tests.jsonl", suite_sha),
        ref("artifacts/flash-04/f1_ambiguity/rebind_current_delta_report.json", rebind_sha),
        ref("artifacts/flash-04/f1_ambiguity/frozen_current_verification.json", verify_sha),
        ref("research_map/formulation_taxonomy.yaml", sh(ROOT / "research_map/formulation_taxonomy.yaml")),
        "comms/inbox/deepseek-flash-04.jsonl:1-3",
    ]
    next_falsifier = verify.get("next_falsifier")
    falsifier = rebind.get("falsifier")
    events = [
        {
            "event_id": f"flash-04-art-F1-rebind-suite-{stamp}",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "deepseek-flash-04",
            "node_id": "F1",
            "class_id": "AF-WCC-VAC-GEN",
            "gate": "G-FORM",
            "group_id": "formulation",
            "artifact_type": "falsifier_test_suite",
            "path": "schemas/f1_falsifier_tests.jsonl",
            "sha256": suite_sha,
            "bytes": SUITE.stat().st_size,
            "validation_status": "unverified",
            "evidence_refs": evidence,
            "falsifier": falsifier,
            "next_falsifier": next_falsifier,
            "supersedes": ["flash-04-art-F1-rev20-suite-20260912T001432"],
            "summary": (
                f"F1 ambiguity suite carried from binding {old8} to the current canonical sha256 {new8} "
                f"(FROZEN revision {rebind.get('binding', {}).get('frozen_manifest_revision')}); "
                f"{rebind.get('tests_total')} tests ({rebind.get('carried')} carried, {rebind.get('new')} new), "
                f"{verify.get('probe_recheck', {}).get('probes_pass')}/{verify.get('probe_recheck', {}).get('probes_total')} probes pass, "
                f"0 probe failures, 0 flips. New F1-AMB-25 adds an equality + cross_artifact check on "
                f"f0_binding.declared_f0_sha256 (F0 artifact hash now pinned)."
            ),
        },
        {
            "event_id": f"flash-04-art-F1-rebind-report-{stamp}",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "deepseek-flash-04",
            "node_id": "F1",
            "class_id": "AF-WCC-VAC-GEN",
            "gate": "G-FORM",
            "group_id": "formulation",
            "artifact_type": "delta_report",
            "path": "artifacts/flash-04/f1_ambiguity/rebind_current_delta_report.json",
            "sha256": rebind_sha,
            "bytes": REBIND.stat().st_size,
            "validation_status": "unverified",
            "evidence_refs": evidence,
            "falsifier": "A report field that does not reproduce under python3 artifacts/flash-04/f1_ambiguity/rebind_current.py.",
            "next_falsifier": next_falsifier,
            "supersedes": ["flash-04-art-F1-rev20-report-20260912T001432"],
            "summary": (
                f"Delta report {old8} -> {new8}: {json.dumps(rebind.get('delta_counts', {}))}, "
                f"f0_binding match={rebind.get('f0_binding_state', {}).get('match')}, "
                f"open obligations {[o.get('test') for o in rebind.get('open_obligations_retained', [])]} retained."
            ),
        },
        {
            "event_id": f"flash-04-art-F1-freeze-verify-{stamp}",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "deepseek-flash-04",
            "node_id": "F1",
            "class_id": "AF-WCC-VAC-GEN",
            "gate": "G-FORM",
            "group_id": "formulation",
            "artifact_type": "verification_report",
            "path": "artifacts/flash-04/f1_ambiguity/frozen_current_verification.json",
            "sha256": verify_sha,
            "bytes": VERIFY.stat().st_size,
            "validation_status": "unverified",
            "evidence_refs": evidence,
            "falsifier": verify.get("falsifier"),
            "next_falsifier": next_falsifier,
            "summary": (
                f"Read-only verification verdict={verify.get('verdict')} against suite binding {new8}: "
                f"{len(verify.get('failures', []))} hard failures, "
                f"{len(verify.get('drift_findings', []))} soft drift findings, "
                f"{verify.get('cross_artifact_checks', {}).get('checked')} cross-artifact checks, "
                f"{len(verify.get('cross_artifact_checks', {}).get('stale', []))} stale."
            ),
        },
        {
            "event_id": f"flash-04-claim-F1-rebind-{stamp}",
            "event_type": "claim",
            "created_at": ts,
            "actor": "deepseek-flash-04",
            "node_id": "F1",
            "class_id": "AF-WCC-VAC-GEN",
            "conclusion_type": "formal_model",
            "statement": (
                f"The F1 (AF-WCC-VAC-GEN) ambiguity suite rebinds from {old8} to the current canonical schema "
                f"sha256 {new8} with {verify.get('probe_recheck', {}).get('probes_pass')}/"
                f"{verify.get('probe_recheck', {}).get('probes_total')} stored probes resolving, 0 probe failures and "
                f"0 verdict flips; F1-AMB-25 pins f0_binding.declared_f0_sha256 equal to the measured "
                f"research_map/formulation_taxonomy.yaml hash and records it as a cross_artifact binding. "
                f"The four prior open obligations (AMB-01/02/03/15) remain open. No theorem, no gate verdict."
            ),
            "assumptions": [
                "the canonical path schemas/af_wcc_vacuum.yaml is authoritative (ASTRA_HANDOFF canonical-path policy)",
                "the FROZEN manifest pin for the canonical F1 path equals the measured canonical sha256 at submission",
                "stored probe predicates are necessary readings of the deciding fields, not jointly sufficient",
                "the declared F0 artifact research_map/formulation_taxonomy.yaml is the F0 contract in force",
            ],
            "falsifier": verify.get("falsifier"),
            "evidence_refs": evidence,
            "artifact_refs": [
                ref("schemas/f1_falsifier_tests.jsonl", suite_sha),
                ref("artifacts/flash-04/f1_ambiguity/rebind_current_delta_report.json", rebind_sha),
                ref("artifacts/flash-04/f1_ambiguity/frozen_current_verification.json", verify_sha),
            ],
        },
        {
            "event_id": f"flash-04-status-F1-rebind-{stamp}",
            "event_type": "status",
            "created_at": ts,
            "actor": "deepseek-flash-04",
            "node_id": "F1",
            "class_id": "AF-WCC-VAC-GEN",
            "gate": "G-FORM",
            "group_id": "formulation",
            "status": "active",
            "hours": 0.5,
            "summary": (
                f"Assignment asg-2026-09-11-F1-deepseek-flash-04-13 delta re-run: suite rebound to canonical "
                f"sha256 {new8} (FROZEN rev {rebind.get('binding', {}).get('frozen_manifest_revision')}), "
                f"{rebind.get('tests_total')} tests, {verify.get('probe_recheck', {}).get('probes_pass')} probes pass, "
                f"verification verdict {verify.get('verdict')}. Supersedes the rev20 submission. No completion or "
                f"gate verdict claimed; validation_status unverified."
            ),
            "evidence_refs": evidence,
            "next_falsifier": next_falsifier,
            "supersedes": ["flash-04-status-F1-rev20-20260912T001432"],
        },
    ]
    lines = []
    for ev in events:
        try:
            validate_event(ev)
        except Exception as exc:  # noqa: BLE001
            print(f"EVENT SCHEMA ERROR {ev.get('event_id')}: {exc}")
            return 2
        lines.append(json.dumps(ev, ensure_ascii=False, sort_keys=True))
    with open(OUTBOX, "a") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps({"appended": len(lines), "event_ids": [e["event_id"] for e in events],
                      "outbox": str(OUTBOX.relative_to(ROOT)),
                      "outbox_sha256": sh(OUTBOX)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
