#!/usr/bin/env python3
"""Emit worker-001's bounded-task events to comms/outbox/worker-001.jsonl.

Appends (never truncates) valid JSONL objects satisfying research_map/events.schema.json:
  - 2 artifact events (report.json, coupling_evidence.json) with path + sha256 +
    validation_status
  - 1 status event with node_id/class_id, evidence refs as path#sha256-prefix, hours,
    summary and next_falsifier

No ingest is run (controller-owned). No canonical artifact is written. Idempotent guard:
refuses to append an event_id that is already present.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTBOX = ROOT / "comms" / "outbox" / "worker-001.jsonl"
D = ROOT / "artifacts" / "worker-001" / "f0_genericity_audit"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")


def h(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(p: Path) -> str:
    return f"{p.relative_to(ROOT)}#{h(p)[:12]}"


report = D / "report.json"
coupling = D / "coupling_evidence.json"
diff = D / "patch_proposal.diff"
script = D / "audit_genericity_rule.py"

events = [
    {
        "event_id": "w001-f0-genericity-audit-artifact-20260912T004700+0800",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-001",
        "node_id": "F0",
        "class_id": "AF-WCC-SCALAR-SPH",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN",
                      "AF-WCC-SCALAR-SPH"],
        "artifact_type": "genericity_two_slot_coherence_audit",
        "path": str(report.relative_to(ROOT)),
        "sha256": h(report),
        "validation_status": "unverified",
        "detector": {"path": str(script.relative_to(ROOT)), "sha256": h(script)},
        "pinned": {
            "canonical": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
            "supplement": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
        },
        "evidence_refs": [ref(report), ref(script)],
    },
    {
        "event_id": "w001-f0-genericity-patch-coupling-artifact-20260912T004700+0800",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-001",
        "node_id": "F0",
        "class_id": "AF-WCC-SCALAR-SPH",
        "artifact_type": "patch_proposal_with_coupling_measurement",
        "path": str(coupling.relative_to(ROOT)),
        "sha256": h(coupling),
        "validation_status": "unverified",
        "proposed_canonical_sha256": h(D / "proposed_formulation_taxonomy.yaml"),
        "proposed_supplement_sha256": h(D / "proposed_formulation_taxonomy_supplement.yaml"),
        "diff_path": str(diff.relative_to(ROOT)),
        "diff_sha256": h(diff),
        "not_applied": True,
        "evidence_refs": [ref(coupling), ref(diff)],
    },
    {
        "event_id": "w001-f0-genericity-audit-status-20260912T004700+0800",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-001",
        "node_id": "F0",
        "class_id": "AF-WCC-SCALAR-SPH",
        "status": "active",
        "hours": 0.5,
        "claims_completion": False,
        "summary": (
            "One bounded class-bound task complete: genericity two-slot coherence audit at the "
            "pinned canonical rev5 0abb9ed8a961 / supplement d7419b4e. Verdict FINDINGS (5), "
            "detector selftest 6/6, hash-drift check clean. Artifact-content defects: "
            "(1) AF-WCC-SCALAR-SPH conflates the kind slot with the topology slot - "
            "axes.genericity_kind='unresolved' (L393) while the conclusion asserts 'For a comeager "
            "set G' (L414); comeager fixes the KIND, only the topology is unresolved. "
            "(2) genericity_topology is declared mandatory for generic-quantified claims (L144) and "
            "referenced by the T1 guard (L501) but is absent from 4/4 axes blocks, so the guard is "
            "vacuously true. Instrument findings: validate_taxonomy.py never inspects class axes "
            "keys, so 253/253 is silent on L144/L147 in both directions (measured control: adding "
            "the slot passes 253/253 unchanged - an earlier 'validator forbids the fix' reading was "
            "refuted by that run and withdrawn). Proposed coupled fix (NOT applied; FROZEN rev28, "
            "lead owns revision bumps): canonical scalar kind -> provisional_baire_residual + "
            "genericity_topology: unresolved on 4/4 classes; supplement frozen scalar -> "
            "residual_comeager + scalar_note corrected. Consistency arms measured: current PASS, "
            "canonical-only FAIL ('genericity residual_comeager vs unresolved'), coupled PASS. "
            "The patch clears 3/5 findings and passes validate_taxonomy 253/253; the 2 remaining "
            "findings are rule-text scope (lead) and instrument coverage (optional enforcement)."
        ),
        "evidence_refs": [
            ref(report), ref(coupling), ref(diff), ref(script),
            "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
            "artifacts/formulation/formulation_taxonomy.yaml#d7419b4e8963",
            "artifacts/formulation/FROZEN.json#rev28",
            "comms/PROTOCOL.md:46",
        ],
        "next_falsifier": (
            "Falsified if any of: (a) a pinned companion artifact defines genericity_kind="
            "'unresolved' as 'topology unresolved while the kind is fixed' (collapses the "
            "conflation finding); (b) a committed checker at the FROZEN revision inspects "
            "genericity_topology presence/value, or the green suite changes verdict when the slot "
            "is added (collapses the instrument finding); (c) the scalar conclusion text is shown "
            "non-assertoric at 0abb9ed8 (quoted/withdrawn), or the canonical hash no longer equals "
            "0abb9ed8 (re-run required); (d) the coupled patch fails check_taxonomy_consistency or "
            "validate_taxonomy on a fresh run (collapses the proposed fix)."
        ),
        "to": ["astra", "astra-lead-formulation", "astra-lead-audit"],
    },
]

assert all(e["event_type"] in ("artifact", "status") for e in events)
for e in events:
    for k in ("event_id", "event_type", "created_at", "actor"):
        assert e.get(k), f"missing {k}"
    if e["event_type"] == "artifact":
        for k in ("node_id", "artifact_type", "path", "sha256", "validation_status"):
            assert e.get(k), f"artifact missing {k}"

OUTBOX.parent.mkdir(parents=True, exist_ok=True)
existing = set()
if OUTBOX.is_file():
    for line in OUTBOX.read_text().splitlines():
        if line.strip():
            existing.add(json.loads(line).get("event_id"))
new = [e for e in events if e["event_id"] not in existing]
with OUTBOX.open("a") as fh:
    for e in new:
        fh.write(json.dumps(e, sort_keys=True) + "\n")
print(json.dumps({"appended": len(new), "skipped_existing": len(events) - len(new),
                  "outbox": str(OUTBOX.relative_to(ROOT))}, indent=2))
for e in new:
    print(json.dumps(e, indent=2, sort_keys=True))
