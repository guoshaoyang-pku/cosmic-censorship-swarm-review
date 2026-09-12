#!/usr/bin/env python3
"""Append worker-08's FORM-SEP-04 v2 events (frozen revision 2) to the outbox, idempotently."""
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
ACTOR = "deepseek-flash-08"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


matrix = ART / "c2_c0_separation_matrix.json"
report = ART / "c2_c0_separation_report.md"
selftest = ART / "c2_c0_separation_selftest.json"
selftest_md = ART / "c2_c0_separation_selftest.md"
rep_c0 = ART / "repaired_baseline" / "af_scc_c0_vacuum_repaired.yaml"
rep_readme = ART / "repaired_baseline" / "README.json"
auditor = ART / "c2_c0_separation_audit.py"
frozen = REPO / "artifacts" / "formulation" / "FROZEN.json"

m = json.loads(matrix.read_text())
st = json.loads(selftest.read_text())
fail = m["hard_failures"][0]
h1 = fail["hits"][0]
prop = m["X3_propagation"]["adjacent_files_carrying_the_defect"]

events = [
    {
        "event_id": "e08-art-20260911T2336-form-sep-04-v2-frozen2",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": ACTOR,
        "group_id": "formulation",
        "node_id": "F2",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "artifact_type": "separation_audit",
        "path": "artifacts/worker08/c2_c0_separation_matrix.json",
        "sha256": sha(matrix),
        "validation_status": "unverified",
        "supersedes": "e08-art-20260911T2330-form-sep-04",
        "revision_audited": 2,
        "frozen_manifest": {"path": "artifacts/formulation/FROZEN.json", "sha256": sha(frozen)},
        "inputs": m["inputs"],
        "audit_verdict": m["verdict"],
        "hard_failure_count": len(m["hard_failures"]),
        "hard_failure_kinds": [f["kind"] for f in m["hard_failures"]],
        "X1_violations": len(m["X1_pairwise"]["expectation_violations"]),
        "X2_unjustified": m["X2_foreign_semantics"]["unjustified_count"],
        "X2b_axis_violations": len(m["X2b_conclusion_axis"]["violations"]),
        "X3_converse_assertions": len(m["X3_implication_ledger"]["converse_assertions"]),
        "X4_violations": len(m["X4_composite_regularity"]["violations"]),
        "selftest": {"path": "artifacts/worker08/c2_c0_separation_selftest.json",
                     "sha256": sha(selftest),
                     "controls_pass": st["false_positive_check"]["controls_pass"],
                     "canonical_pair_ok": st["false_positive_check"]["canonical_pair_behaves_as_expected"],
                     "in_scope_caught": st["in_scope_mutant_probe_caught"],
                     "family_scope_missed": st["family_scope_probes_missed_documented"]},
        "report": {"path": "artifacts/worker08/c2_c0_separation_report.md", "sha256": sha(report)},
        "report_selftest": {"path": "artifacts/worker08/c2_c0_separation_selftest.md",
                            "sha256": sha(selftest_md)},
        "proposed_repair_baseline": {
            "path": "artifacts/worker08/repaired_baseline/af_scc_c0_vacuum_repaired.yaml",
            "sha256": sha(rep_c0),
            "readme": {"path": "artifacts/worker08/repaired_baseline/README.json",
                       "sha256": sha(rep_readme)},
            "note": "worker-path copy only; repaired_pair self-test PASS demonstrates repair sufficiency; not canonical, not accepted",
        },
        "auditor": {"path": "artifacts/worker08/c2_c0_separation_audit.py", "sha256": sha(auditor)},
        "reproduce": "python3 artifacts/worker08/c2_c0_separation_audit.py && python3 artifacts/worker08/run_separation_selftest.py",
        "evidence_refs": [
            "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml#9aab12d5",
            "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml#684afaac",
            "artifacts/formulation/rule_spec.json#e16133d2",
            "artifacts/formulation/FROZEN.json#" + sha(frozen)[:8],
        ],
        "next_falsifier": m["next_falsifier"],
    },
    {
        "event_id": "e08-status-20260911T2336-form-sep-04-v2",
        "event_type": "status",
        "created_at": NOW,
        "actor": ACTOR,
        "group_id": "formulation",
        "node_id": "F2",
        "status": "active",
        "hours": 3.0,
        "summary": (
            "FORM-SEP-04 re-run bound to frozen revision 2 (C2 9aab12d5, C0 684afaac, rule_spec "
            "e16133d2, FROZEN.json verified). Result unchanged: exactly one hard failure, the H1 "
            "converse assertion in af_scc_c0_vacuum.yaml line 173 non_vacuity.c0_specific_note; it now "
            "directly contradicts the same file's harvested c0_specifics.conclusion_relation_to_sibling "
            "('The one-way entailment C0 => C2 ... the converse is forbidden'), so the frozen C0 file is "
            "internally inconsistent on the class-containment direction. X1/X2/X2b/X4 clean (0 violations, "
            "0 unjustified foreign mentions, 5 justified leakage-block exclusions). Self-test: controls "
            "pass, m12 caught, p03 caught (closes the lead gate's documented p03 blind spot), p01/p05 "
            "remain family-scope misses documented in the self-test. Proposed repaired baseline in my "
            "artifacts path passes the same audit (repair sufficiency). No completion claimed; revision "
            "bump + fixture regeneration + re-audit required."
        ),
        "evidence_refs": [
            "artifacts/worker08/c2_c0_separation_matrix.json#" + sha(matrix)[:8],
            "artifacts/worker08/c2_c0_separation_selftest.json#" + sha(selftest)[:8],
            "artifacts/formulation/FROZEN.json#" + sha(frozen)[:8],
        ],
        "next_falsifier": m["next_falsifier"],
    },
    {
        "event_id": "e08-blocker-20260911T2336-c0-converse-frozen2",
        "event_type": "blocker",
        "created_at": NOW,
        "actor": ACTOR,
        "group_id": "formulation",
        "node_id": "F2",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "supersedes": "e08-blocker-20260911T2330-c0-converse",
        "description": (
            "Frozen rev2 defect (unchanged from rev1): af_scc_c0_vacuum.yaml:173 "
            "non_vacuity.c0_specific_note asserts 'a C2-inextendibility proof SUBSUMES this class's "
            "conclusion', the forbidden converse under R16 (containment runs C0 => C2 only). The same "
            "revision's c0_specifics.conclusion_relation_to_sibling states the correct direction, so the "
            f"file contradicts itself. The phrase is still cloned in {len(prop)} fixture/control files: "
            + ", ".join(prop[:5]) + (" ..." if len(prop) > 5 else "")
        ),
        "needed_to_unblock": (
            "Bump to revision 3 with the one-line repair (see artifacts/worker08/repaired_baseline/ or "
            "the report's exact replacement), regenerate the cloned fixtures, re-run run_gate_tests.py, "
            "then re-run artifacts/worker08/c2_c0_separation_audit.py against the new hashes. Closure "
            "requires zero converse assertions and no fixture carrying the old phrase."
        ),
        "evidence_refs": [
            "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml#684afaac",
            "artifacts/worker08/c2_c0_separation_matrix.json#" + sha(matrix)[:8],
            "artifacts/formulation/FROZEN.json#" + sha(frozen)[:8],
        ],
        "next_falsifier": (
            "A revision-3 audit returning PASS with the repaired sentence, or a reviewer showing the "
            "sentence as written does not assert the converse (would falsify this blocker)."
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
                  "verdict": m["verdict"], "hard_failure_kinds": [f["kind"] for f in m["hard_failures"]],
                  "propagated": len(prop)}, indent=2))
