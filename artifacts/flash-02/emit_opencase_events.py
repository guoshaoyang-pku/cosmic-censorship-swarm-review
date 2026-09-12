#!/usr/bin/env python3
"""Emit the four F0 open-case disposition events to comms/outbox/deepseek-flash-02.jsonl.

Idempotent by event_id: re-running appends nothing if the ids are already present.
Usage: python3 artifacts/flash-02/emit_opencase_events.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTBOX = ROOT / "comms" / "outbox" / "deepseek-flash-02.jsonl"
STAMP = "20260912T0015"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
CORPUS_SHA = "b9699119bbabf01489f851b6dfa0c05a56f457c031e4e69992b8f57c30c489a2"
TAX_SHA = "565a6e505188d6c28050500924b9b66b1440a4c9b069567c772f414f19e02800"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    disp = ROOT / "artifacts/flash-02/open_case_disposition.json"
    report = ROOT / "artifacts/flash-02/open_case_disposition_check_report.json"
    disp_sha, report_sha = sha256(disp), sha256(report)
    errs = json.loads(report.read_text())["errors"]
    assert errs == [], f"checker report has errors: {errs}"

    base = {
        "actor": "deepseek-flash-02",
        "created_at": "2026-09-12T00:15:00+08:00",
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": CLASS_IDS,
        "assignment_event_id": "asg-2026-09-11-F0-deepseek-flash-02-11",
        "claims_theorem_status": False,
    }
    events = [
        dict(base, **{
            "event_id": f"flash02-opencase-artifact-0008-{STAMP}",
            "event_type": "artifact",
            "artifact_type": "open_case_disposition_matrix",
            "path": "artifacts/flash-02/open_case_disposition.json",
            "sha256": disp_sha,
            "validation_status": "unverified",
            "note": (
                "Adjudication-ready disposition matrix for the 9 corpus cases with open=true "
                "(the open item in gate G-F0 unmet #4). One row per open case, exactly one "
                "disposition token each: 7 NEW_CLASS_REQUEST_DEFERRED_TO_HUMAN_PI (bound to a "
                "frozen parent class per astra-classscope-02, which rejects new class ids "
                "pending Human PI), 1 SPLIT_REQUIRED, 1 SPLIT_AND_BRIDGE_REQUIRED. 0 new class "
                "ids created; rows are input for the formulation lead, not adjudications."
            ),
            "evidence_refs": [
                f"schemas/taxonomy_cases.jsonl#{CORPUS_SHA[:12]}",
                f"research_map/formulation_taxonomy.yaml#{TAX_SHA[:12]}",
                f"artifacts/flash-02/open_case_disposition.json#{disp_sha[:12]}",
            ],
        }),
        dict(base, **{
            "event_id": f"flash02-opencase-artifact-0009-{STAMP}",
            "event_type": "artifact",
            "artifact_type": "open_case_disposition_check_report",
            "path": "artifacts/flash-02/open_case_disposition_check_report.json",
            "sha256": report_sha,
            "validation_status": "unverified",
            "note": (
                "Deterministic checker PASS: bijection corpus-open(9) <-> rows(9), every "
                "disposition token in the declared enum, zero AF-* tokens outside the frozen "
                "four, zero frozen-class matches on independent axis recomputation (7 axis "
                "rows) and 0/4 out-of-vocabulary rows falsely in vocabulary, all rule/gap refs "
                "resolve against the pinned taxonomy, 8/8 mutation controls detected."
            ),
            "evidence_refs": [
                f"artifacts/flash-02/open_case_disposition.json#{disp_sha[:12]}",
                f"artifacts/flash-02/open_case_disposition_check_report.json#{report_sha[:12]}",
                f"schemas/taxonomy_cases.jsonl#{CORPUS_SHA[:12]}",
                f"research_map/formulation_taxonomy.yaml#{TAX_SHA[:12]}",
            ],
        }),
        dict(base, **{
            "event_id": f"flash02-opencase-claim-0010b-{STAMP}",
            "event_type": "claim",
            "conclusion_type": "stability_result",
            "class_id": ";".join(CLASS_IDS),
            "statement": (
                "Artifact-and-checker result (not a mathematics or physics claim): the 9 "
                "open=true cases in schemas/taxonomy_cases.jsonl map bijectively to exactly one "
                "disposition each under the pinned taxonomy - 7 deferred new-class requests and "
                "2 split dispositions - with 0 new class ids introduced and 0/9 rows matching a "
                "frozen class on recomputation. The 7 deferred requests are blocked on Human PI "
                "by class_scope_adjudication.directive=astra-classscope-02; the 2 split rows "
                "(TC-F0-N14 C0/C2 merge, TC-F0-N15 WCC/SCC merge) need no new class and are "
                "decidable by the formulation lead now."
            ),
            "assumptions": [
                "The pinned taxonomy 565a6e50 rev3 and corpus b9699119 are the current "
                "canonical bytes; both may move and would require a re-pin.",
                "The corpus open=true flags are the authoritative list of undispositioned "
                "cases; the gate text's '9 taxonomy cases remain open' matches that list.",
                "A worker may propose dispositions but may not adjudicate them or create "
                "class ids (comms/PROTOCOL.md rule 5, astra-classscope-02).",
            ],
            "falsifier": (
                "Any open corpus case missing from the matrix, any case resolving to two "
                "dispositions, any AF-* token in the matrix outside the frozen four, any row "
                "whose axis vector equals a frozen class under independent recomputation, or "
                "any of the 8 checker controls not detected."
            ),
            "evidence_refs": [
                f"artifacts/flash-02/open_case_disposition.json#{disp_sha[:12]}",
                f"artifacts/flash-02/open_case_disposition_check_report.json#{report_sha[:12]}",
                f"schemas/taxonomy_cases.jsonl#{CORPUS_SHA[:12]}",
                f"research_map/formulation_taxonomy.yaml#{TAX_SHA[:12]}",
            ],
            "artifact_refs": [
                "artifacts/flash-02/open_case_disposition.json",
                "artifacts/flash-02/open_case_disposition_check_report.json",
                "schemas/taxonomy_cases.jsonl",
            ],
        }),
        dict(base, **{
            "event_id": f"flash02-opencase-status-0011-{STAMP}",
            "event_type": "status",
            "status": "active",
            "hours": 0.35,
            "summary": (
                "One class-bound F0 task executed and closed: disposition matrix for the 9 "
                "open taxonomy cases. Every row carries bound_parent_class_ids from the frozen "
                "four, a single disposition token, taxonomy rule/gap refs and its own "
                "falsifier; the checker recomputes class separation rather than trusting the "
                "corpus labels, passes with 0 errors and detects 8/8 mutation controls. No "
                "node status, validation status, or gate verdict is claimed; the 7 deferred "
                "new-class requests are explicitly routed to the formulation lead and Human PI."
            ),
            "evidence_refs": [
                f"artifacts/flash-02/open_case_disposition.json#{disp_sha[:12]}",
                f"artifacts/flash-02/open_case_disposition_check_report.json#{report_sha[:12]}",
                f"schemas/taxonomy_cases.jsonl#{CORPUS_SHA[:12]}",
                f"research_map/formulation_taxonomy.yaml#{TAX_SHA[:12]}",
            ],
            "next_falsifier": (
                "A corpus revision adds or removes an open case without a matching matrix "
                "revision, the taxonomy directive changes away from astra-classscope-02, or a "
                "reviewer finds an open case that the matrix classifies under a frozen class."
            ),
            "completion_claim": False,
        }),
    ]

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                try:
                    existing.add(json.loads(line)["event_id"])
                except Exception:
                    pass
    fresh = [e for e in events if e["event_id"] not in existing]
    with OUTBOX.open("a") as f:
        for e in fresh:
            f.write(json.dumps(e) + "\n")
    print(json.dumps({"appended": len(fresh), "skipped_existing": len(events) - len(fresh),
                      "event_ids": [e["event_id"] for e in fresh]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
