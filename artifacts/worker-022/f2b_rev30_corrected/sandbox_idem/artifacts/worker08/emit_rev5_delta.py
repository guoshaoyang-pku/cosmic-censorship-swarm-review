#!/usr/bin/env python3
"""Rev5 delta: X3 converse count at frozen hashes + m27/m28 validation (lead-requested)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUTBOX = REPO / "comms" / "outbox" / "deepseek-flash-08.jsonl"
ART = REPO / "artifacts" / "worker08"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


matrix, report = ART / "c2_c0_separation_matrix.json", ART / "c2_c0_separation_report.md"
selftest = ART / "c2_c0_separation_selftest.json"
auditor = ART / "c2_c0_separation_audit.py"
frozen = REPO / "artifacts" / "formulation" / "FROZEN.json"
m = json.loads(matrix.read_text())
st = json.loads(selftest.read_text())
inputs = m["inputs"]
c0h = inputs["artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"]
c2h = inputs["artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"]

events = [
    {
        "event_id": "e08-art-20260911T2354-form-sep-04-rev5",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "deepseek-flash-08",
        "group_id": "formulation",
        "node_id": "F2",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "artifact_type": "separation_audit",
        "path": "artifacts/worker08/c2_c0_separation_matrix.json",
        "sha256": sha(matrix),
        "validation_status": "unverified",
        "supersedes": "e08-art-20260911T2348-form-sep-04-v3-closure",
        "frozen_revision": 5,
        "inputs": inputs,
        "X3_converse_assertions_at_rev5": len(m["X3_implication_ledger"]["converse_assertions"]),
        "audit_verdict": m["verdict"],
        "hard_failure_count": len(m["hard_failures"]),
        "frozen_manifest_mismatches": m["frozen_manifest_check"]["mismatches"],
        "new_mutant_validation": {
            "m27_prose_converse_c2_c0": "FAIL with converse_implication_asserted (caught)",
            "m28_prose_converse_reversed": "FAIL with converse_implication_asserted (caught after adding the 'follows from' entailment pattern to the scanner)",
        },
        "post_repair_residuals": m["post_repair_residuals"],
        "selftest": {"path": "artifacts/worker08/c2_c0_separation_selftest.json", "sha256": sha(selftest),
                     "controls_pass": st["false_positive_check"]["controls_pass"],
                     "in_scope_caught": st["in_scope_mutant_probe_caught"],
                     "family_scope_missed": st["family_scope_probes_missed_documented"]},
        "report": {"path": "artifacts/worker08/c2_c0_separation_report.md", "sha256": sha(report)},
        "auditor": {"path": "artifacts/worker08/c2_c0_separation_audit.py", "sha256": sha(auditor)},
        "evidence_refs": [
            "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml#" + c2h[:8],
            "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml#" + c0h[:8],
            "artifacts/formulation/FROZEN.json#" + sha(frozen)[:8],
        ],
        "next_falsifier": (
            "Reintroduce any C2 => C0 prose or move the conclusion axis; X3 converse must stay 0 at each "
            "new frozen hash."
        ),
    },
    {
        "event_id": "e08-status-20260911T2354-form-sep-04-rev5",
        "event_type": "status",
        "created_at": NOW,
        "actor": "deepseek-flash-08",
        "group_id": "formulation",
        "node_id": "F2",
        "status": "active",
        "hours": 4.4,
        "summary": (
            "Requested rev5 delta: X3 converse assertions = 0 at frozen hashes C2 " + c2h[:12] + " / C0 "
            + c0h[:12] + "; audit verdict PASS; frozen manifest now fully consistent (0 mismatches, "
            "self-entry skipped). Your two new mutants both caught by this audit: m27 directly; m28 "
            "required adding a 'follows from' entailment pattern (now in the scanner and self-test), so "
            "the prose-converse class is covered in both directions. Fixtures directory is clean; 2 "
            "novel_mutants under reviews/ (n02, n07) still carry the pre-repair sentence. No completion "
            "claimed; G-CLASSBIND remains yours."
        ),
        "evidence_refs": [
            "artifacts/worker08/c2_c0_separation_matrix.json#" + sha(matrix)[:8],
            "artifacts/worker08/c2_c0_separation_selftest.json#" + sha(selftest)[:8],
        ],
        "next_falsifier": "Same as artifact next_falsifier; or a reviewer finding the scanner's family-scope blind spots (p01/p05) matter for this gate.",
    },
]

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                existing.add(json.loads(line)["event_id"])
            except (ValueError, KeyError):
                pass
added = []
with open(OUTBOX, "a", encoding="utf-8") as fh:
    for ev in events:
        if ev["event_id"] in existing:
            continue
        fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
        added.append(ev["event_id"])
print(json.dumps({"added": added, "total_events": len(existing) + len(added),
                  "X3_converse_at_rev5": len(m["X3_implication_ledger"]["converse_assertions"]),
                  "c2": c2h[:12], "c0": c0h[:12],
                  "m27": "caught", "m28": "caught"}, indent=2))
