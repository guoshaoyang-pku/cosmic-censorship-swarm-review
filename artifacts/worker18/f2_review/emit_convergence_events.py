#!/usr/bin/env python3
"""Emit the worker-18 convergence events v2 to comms/outbox (astra-conv-03 deliverable).

v2 supersedes the 00:08 v1 events, which pinned the pre-rev20 schema hashes that moved
mid-review. Builds event JSON files under artifacts/worker18/events/, validates each with
research_map/schemas.py, then appends via artifacts/worker18/emit.py.

Usage: python3 artifacts/worker18/f2_review/emit_convergence_events.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FR = ROOT / "artifacts" / "worker18" / "f2_review"
EV = ROOT / "artifacts" / "worker18" / "events"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event, SchemaError  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")


def sha(p: str) -> str:
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


PINS = json.loads((FR / "convergence_pins.json").read_text())
CONV = PINS["artifact"] + "#" + PINS["sha256"][:12]
C2 = PINS["targets"]["AF-SCC-C2-VAC-GEN"]["path"] + "#" + PINS["targets"]["AF-SCC-C2-VAC-GEN"]["sha256"][:12]
C0 = PINS["targets"]["AF-SCC-C0-VAC-GEN"]["path"] + "#" + PINS["targets"]["AF-SCC-C0-VAC-GEN"]["sha256"][:12]
GATE = "artifacts/worker18/f2_review/convergence_canonical_gate.txt#" + PINS["evidence"]["artifacts/worker18/f2_review/convergence_canonical_gate.txt"][:12]
PROBE = "artifacts/worker18/f2_review/convergence_probe_report.json#" + PINS["evidence"]["artifacts/worker18/f2_review/convergence_probe_report.json"][:12]
W06 = "artifacts/worker18/f2_review/w06_c0_frozen_report.json#" + PINS["evidence"]["artifacts/worker18/f2_review/w06_c0_frozen_report.json"][:12]
VF = "artifacts/worker18/f2_review/convergence_verify_frozen.txt#" + PINS["evidence"]["artifacts/worker18/f2_review/convergence_verify_frozen.txt"][:12]
FROZEN = "artifacts/formulation/FROZEN.json#" + PINS["frozen_manifest"]["sha256"][:12]
SEMESC = "artifacts/formulation/evidence/semantic_escape_rebased.json#" + sha("artifacts/formulation/evidence/semantic_escape_rebased.json")[:12]
VARREG = "artifacts/formulation/evidence/variant_registry_check.json#" + sha("artifacts/formulation/evidence/variant_registry_check.json")[:12]

EVENTS = [
    {
        "event_id": "w18-review-20260912-conv-F2a-accept-v2",
        "event_type": "review",
        "created_at": NOW,
        "actor": "deepseek-flash-18",
        "node_id": "A1",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "target_id": "F2a",
        "target_path": C2.split("#")[0],
        "target_sha256": PINS["targets"]["AF-SCC-C2-VAC-GEN"]["sha256"],
        "reviewer": "deepseek-flash-18",
        "verdict": "accept",
        "score": 4,
        "hard_failures": [],
        "assignment_event_id": "astra-conv-03",
        "supersedes": "w18-review-20260912-conv-F2a-accept",
        "b_n_policy": "B blocks accept; N is backlog; revise only with >=1 B.",
        "findings": [
            {"label": "N-A1", "severity": "non_blocking", "finding": "probe S5-C2 token is inside the anti_scope ban list (line 277); canonical gate PASS"},
            {"label": "N-A2", "severity": "non_blocking", "finding": "(s,delta) uniformity binder (lines 45/49/215) needs an explicit one-line note"},
            {"label": "N-A3", "severity": "non_blocking", "finding": "tier_1.machine_checkable_steps (line 257) over-labelled (carried)"},
            {"label": "N-A4", "severity": "non_blocking", "finding": "TWOSIDED variant entry in anti_scope reuses this class's own id; label with parent_class/variant_id fields"},
        ],
        "delta_vs_draft": "HF-A1/HF-A2/HF-A3/HF-A4 resolved; rev20 re-pin e9fcefe6 -> 8dae50da; no B finding.",
        "evidence_refs": [CONV, C2, GATE, PROBE],
        "next_falsifier": "Any asserted C0 conclusion in this file, a non-ban-list collapse-probe hit, or a canonical-gate FAIL at 8dae50da.",
    },
    {
        "event_id": "w18-review-20260912-conv-F2b-accept-v2",
        "event_type": "review",
        "created_at": NOW,
        "actor": "deepseek-flash-18",
        "node_id": "A1",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "target_id": "F2b",
        "target_path": C0.split("#")[0],
        "target_sha256": PINS["targets"]["AF-SCC-C0-VAC-GEN"]["sha256"],
        "reviewer": "deepseek-flash-18",
        "verdict": "accept",
        "score": 4,
        "hard_failures": [],
        "assignment_event_id": "astra-conv-03",
        "supersedes": "w18-review-20260912-conv-F2b-accept",
        "b_n_policy": "B blocks accept; N is backlog; revise only with >=1 B.",
        "findings": [
            {"label": "N-B1", "severity": "non_blocking", "finding": "node_id F2b vs map F2 waits on FORM-MAP-PATCH-002 (map-side)"},
            {"label": "N-B2", "severity": "non_blocking", "finding": "w06/probe composite-regularity hits are prohibition contexts at lines 154/280"},
            {"label": "N-B3", "severity": "non_blocking", "finding": "(s,delta) uniformity binder (lines 46/50/217) needs an explicit one-line note"},
            {"label": "N-B4", "severity": "non_blocking", "finding": "tier_1 machine-checkable steps (line 260) over-labelled (carried from F-B3)"},
            {"label": "N-B5", "severity": "non_blocking", "finding": "H2LOC/DISTRIBUTIONAL variant entries in anti_scope reuse this class's own id; label with parent_class/variant_id fields"},
        ],
        "delta_vs_draft": "HF-B1 resolved; HF-B2 downgraded to N (map patch pending); Q1 answered; Q2 resolved; Q3 carried as N; rev19/rev20 re-pin bdb23f76 -> 94aaa95a -> a8d899d2.",
        "evidence_refs": [CONV, C0, GATE, W06],
        "next_falsifier": "A non-negated C2-inextendibility assertion in this file, a non-ban-list collapse-probe hit, or a canonical-gate FAIL at a8d899d2.",
    },
    {
        "event_id": "w18-artifact-20260912-convergence18-v2",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "deepseek-flash-18",
        "node_id": "A1",
        "class_id": "GLOBAL",
        "artifact_type": "review",
        "path": PINS["artifact"],
        "sha256": PINS["sha256"],
        "validation_status": "unverified",
        "assignment_event_id": "astra-conv-03",
        "supersedes": "w18-artifact-20260912-convergence18",
        "summary": (
            "Assigned deliverable reviews/convergence-18.json v2, re-pinned after the mid-review rev20 "
            "churn: F2a accept 4/5 (0 B, 4 N) at C2 8dae50da rev9; F2b accept 4/5 (0 B, 5 N) at C0 "
            "a8d899d2 rev9; collapse attempt not_supported; reasoning jaccard 0.215; all six draft hard "
            "failures resolved or downgraded."
        ),
        "evidence_refs": [CONV, C2, C0, FROZEN],
        "next_falsifier": "Re-hash either target; a moved hash makes this file stale and it must be re-issued.",
    },
    {
        "event_id": "w18-status-20260912-convergence-delivered-v2",
        "event_type": "status",
        "created_at": NOW,
        "actor": "deepseek-flash-18",
        "node_id": "A1",
        "class_id": "GLOBAL",
        "status": "active",
        "hours": 0.6,
        "summary": (
            "astra-conv-03 delivered as v2: reviews/convergence-18.json (sha256 " + PINS["sha256"][:16] + "). "
            "v1 was invalidated mid-review by the lead's rev19->rev20 schema rewrite; v2 is re-pinned to "
            "FROZEN revision 20 with F2a/F2b accept 4/5, zero blocking findings, B/N labels on every "
            "finding. Machine evidence re-run on rev9: canonical gate PASS x3, 26-probe collapse suite "
            "not_supported with fixture self-test OK, w06 sibling report captured (3 over-broad checks). "
            "Backlog: N-X1 two residual evidence drifts, N-X2 w06 exemptions, N-X3 map patch pending, "
            "N-A4/N-B5 variant-entry labelling. No node completion, no gate verdict, no theorem claimed."
        ),
        "evidence_refs": [CONV, GATE, PROBE, W06, VF],
        "next_falsifier": (
            "A blocking finding on either rev9 hash (asserted cross-class token, conclusion import, or "
            "canonical-gate FAIL); otherwise re-run the convergence_pins checks before reusing any verdict."
        ),
    },
    {
        "event_id": "w18-blocker-20260912-frozen-manifest-drift-v2",
        "event_type": "blocker",
        "created_at": NOW,
        "actor": "deepseek-flash-18",
        "node_id": "F2",
        "class_id": "GLOBAL",
        "description": (
            "FROZEN revision 20 has two residual evidence drifts: semantic_escape_rebased.json (manifest "
            "497aac5e, disk 6a67ce9e) and variant_registry_check.json (manifest cb19d3d1, disk 164a9a84); "
            "verify_frozen.py exits 1. All three canonical schemas are bound at their disk hashes and the "
            "two reviewed F2 targets are stable, but the manifest as a whole cannot be cited until the "
            "evidence entries are re-frozen."
        ),
        "needed_to_unblock": (
            "astra-lead-formulation refreshes the two evidence files into the manifest (or re-freezes) "
            "and re-runs artifacts/formulation/tools/verify_frozen.py to exit 0; then N-X1 closes."
        ),
        "evidence_refs": [FROZEN, SEMESC, VARREG, VF],
        "supersedes": "w18-blocker-20260912-frozen-manifest-drift",
        "next_falsifier": "verify_frozen.py exit 0 at a manifest revision whose evidence map matches disk.",
    },
]


def main() -> int:
    EV.mkdir(parents=True, exist_ok=True)
    rc = 0
    for ev in EVENTS:
        try:
            validate_event(ev)
        except SchemaError as e:
            print(f"REJECT schema {ev['event_id']}: {e}")
            rc = 1
            continue
        p = EV / f"{ev['event_id']}.json"
        p.write_text(json.dumps(ev, indent=1) + "\n")
        r = subprocess.run([sys.executable, str(ROOT / "artifacts/worker18/emit.py"), str(p)],
                           cwd=ROOT, capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip())
        if r.returncode != 0:
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
