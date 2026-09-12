#!/usr/bin/env python3
"""Append worker-08's FORM-SEP-04 v3 closure events (post-repair, C0 revision 4)."""
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


matrix = ART / "c2_c0_separation_matrix.json"
report = ART / "c2_c0_separation_report.md"
selftest = ART / "c2_c0_separation_selftest.json"
selftest_md = ART / "c2_c0_separation_selftest.md"
auditor = ART / "c2_c0_separation_audit.py"
frozen = REPO / "artifacts" / "formulation" / "FROZEN.json"
m = json.loads(matrix.read_text())
st = json.loads(selftest.read_text())

events = [
    {
        "event_id": "e08-art-20260911T2348-form-sep-04-v3-closure",
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
        "supersedes": "e08-art-20260911T2336-form-sep-04-v2-frozen2",
        "revision_audited": 4,
        "frozen_manifest": {"path": "artifacts/formulation/FROZEN.json", "sha256": sha(frozen),
                            "revision": 4},
        "inputs": m["inputs"],
        "audit_verdict": m["verdict"],
        "hard_failure_count": 0,
        "X1_violations": 0, "X1_annotation_drift_flags": 1,
        "X2_unjustified": 0, "X2b_axis_violations": 0,
        "X3_converse_assertions": 0, "X4_violations": 0,
        "post_repair_residuals": m["post_repair_residuals"],
        "selftest": {"path": "artifacts/worker08/c2_c0_separation_selftest.json", "sha256": sha(selftest),
                     "controls_pass": st["false_positive_check"]["controls_pass"],
                     "canonical_pair_ok": st["false_positive_check"]["canonical_pair_behaves_as_expected"],
                     "in_scope_caught": st["in_scope_mutant_probe_caught"],
                     "family_scope_missed": st["family_scope_probes_missed_documented"]},
        "report": {"path": "artifacts/worker08/c2_c0_separation_report.md", "sha256": sha(report)},
        "report_selftest": {"path": "artifacts/worker08/c2_c0_separation_selftest.md",
                            "sha256": sha(selftest_md)},
        "auditor": {"path": "artifacts/worker08/c2_c0_separation_audit.py", "sha256": sha(auditor)},
        "reproduce": "python3 artifacts/worker08/c2_c0_separation_audit.py && python3 artifacts/worker08/run_separation_selftest.py",
        "evidence_refs": [
            "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml#" + m["inputs"]["artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"][:8],
            "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml#" + m["inputs"]["artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"][:8],
            "artifacts/formulation/rule_spec.json#" + m["inputs"]["artifacts/formulation/rule_spec.json"][:8],
            "artifacts/formulation/FROZEN.json#" + sha(frozen)[:8],
        ],
        "next_falsifier": (
            "Any later edit that reintroduces a C2 => C0 assertion, moves the conclusion axis, or merges "
            "the regularity tokens reopens the failure; re-run this audit and require X3 converse = 0."
        ),
    },
    {
        "event_id": "e08-status-20260911T2348-form-sep-04-closure",
        "event_type": "status",
        "created_at": NOW,
        "actor": "deepseek-flash-08",
        "group_id": "formulation",
        "node_id": "F2",
        "status": "active",
        "hours": 4.0,
        "summary": (
            "FORM-SEP-04 closure checkpoint. Blocker e08-blocker-20260911T2336-c0-converse-frozen2 is "
            "FALSIFIED as repaired: af_scc_c0_vacuum.yaml revision 4 (188e5131) now reads 'a "
            "C2-inextendibility proof does NOT subsume this class's conclusion ... the implication runs "
            "C0 => C2 only', with worker-08 credited in the schema text. Post-repair audit verdict PASS: "
            "X1 0, X2 0 unjustified, X2b 0, X3 converse 0, X4 0; one annotation-drift flag "
            "(data_class.adm_mass.locator/hypotheses_reconciliation) and two residuals: 2 novel_mutants "
            "still carry the pre-repair sentence (n02, n07), and FROZEN rev4 predates the 23:35:18 gate "
            "tooling update so tool hashes no longer match the manifest (re-freeze on next cycle). "
            "Self-test: controls pass, canonical pair passes, m12 and p03 caught, p01/p05 remain "
            "documented family-scope misses. No completion claimed; F2/G-CLASSBIND verdict belongs to "
            "lead-formulation. L1 shards submitted separately."
        ),
        "evidence_refs": [
            "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml#" + m["inputs"]["artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"][:8],
            "artifacts/worker08/c2_c0_separation_matrix.json#" + sha(matrix)[:8],
        ],
        "next_falsifier": (
            "A reviewer finds a placement where the C2 conclusion is satisfied by a C0-only extension "
            "class or vice versa, or the two stale novel_mutants are promoted as corpus evidence."
        ),
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
                  "verdict": m["verdict"], "residuals": m["post_repair_residuals"]}, indent=2))
