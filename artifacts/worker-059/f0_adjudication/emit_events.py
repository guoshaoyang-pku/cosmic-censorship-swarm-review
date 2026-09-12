#!/usr/bin/env python3
"""Emit and schema-validate the W059-F0-ADJUDICATE-01 event batch.

Appends to comms/outbox/worker-059.jsonl. Every event is checked with the canonical
research_map.schemas.validate_event before it is written; event_ids are checked for
duplicates against the existing outbox and runtime/state/ingested_ids.json.
"""
from __future__ import annotations
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
D = ROOT / "artifacts/worker-059/f0_adjudication"
OUT = ROOT / "comms/outbox/worker-059.jsonl"
REVIEWED = "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc"
CLASSES = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p: str):
    return json.loads((D / p).read_text())


report = load("adjudication_report.json")
review = load("review_F0_276009f4.json")
checkpoint = load("checkpoint_w059_f0adj.json")
review_p = "artifacts/worker-059/f0_adjudication/review_F0_276009f4.json"
report_p = "artifacts/worker-059/f0_adjudication/adjudication_report.json"
checks_p = "artifacts/worker-059/f0_adjudication/adjudication_checks.json"
blind_p = "artifacts/worker-059/f0_adjudication/blindspot_test/blindspot_result.json"
ckpt_p = "artifacts/worker-059/f0_adjudication/checkpoint_w059_f0adj.json"
hashes = {**report["artifact_hashes"], **load("hashes.json")["files"]}
for p in (review_p, report_p, checks_p, blind_p, ckpt_p):
    hashes[p] = sha(ROOT / p)

t = datetime.now(CST)
stamp = t.strftime("%Y%m%dT%H%M")
now = t.isoformat(timespec="seconds")
prefix = f"w059-f0adj-{stamp}"

hard = [f"{h['id']}: {h['statement']}" for h in review["hard_failures"]]
findings = [f"{f['id']}: {f['statement']}" for f in review["findings"]]
next_f = review["next_falsifier"]

events = [
    {
        "event_id": f"{prefix}-task-claim",
        "event_type": "status",
        "created_at": now,
        "actor": "worker-059",
        "node_id": "F0",
        "group_id": "formulation",
        "class_id": CLASSES,
        "gate": "G-F0",
        "status": "active",
        "hours": 0.3,
        "summary": (
            "One bounded class-bound task taken without an inbox card: W059-F0-ADJUDICATE-01 = "
            "independent adjudication of the F0 accept/revise split at canonical sha256 276009f4. "
            "W082-F-01/F-02 substantiated by own checker, controlled mutant experiment and AST "
            "coverage: the AF-WCC-SCALAR-SPH conclusion quantifies bare 'generic data' while its "
            "H4 says the notion is unresolved, asserts an unsourced 'equivalently' the sibling WCC "
            "class explicitly disclaims, and the D3 'each class' resolution is measurable-false; "
            "check_taxonomy_consistency.py cannot detect a D3 regression in that class. Verdict "
            "revise 3.0. Does not claim node completion or any gate verdict."
        ),
        "evidence_refs": [f"{review_p}#{hashes[review_p][:12]}", f"{checks_p}#{hashes[checks_p][:12]}"],
        "next_falsifier": next_f,
    },
    {
        "event_id": f"{prefix}-artifact-review",
        "event_type": "artifact",
        "created_at": now,
        "actor": "worker-059",
        "node_id": "F0",
        "group_id": "formulation",
        "class_id": CLASSES,
        "gate": "G-F0",
        "artifact_type": "independent_review",
        "path": review_p,
        "sha256": hashes[review_p],
        "validation_status": "unverified",
        "reviewed_sha256": REVIEWED,
        "evidence_refs": [f"{report_p}#{hashes[report_p][:12]}"],
        "falsifier": next_f,
    },
    {
        "event_id": f"{prefix}-artifact-report",
        "event_type": "artifact",
        "created_at": now,
        "actor": "worker-059",
        "node_id": "F0",
        "group_id": "formulation",
        "class_id": CLASSES,
        "gate": "G-F0",
        "artifact_type": "adjudication_evidence",
        "path": report_p,
        "sha256": hashes[report_p],
        "validation_status": "unverified",
        "reviewed_sha256": REVIEWED,
        "evidence_refs": [f"{blind_p}#{hashes[blind_p][:12]}", f"{review_p}#{hashes[review_p][:12]}"],
        "falsifier": next_f,
    },
    {
        "event_id": f"{prefix}-artifact-checks",
        "event_type": "artifact",
        "created_at": now,
        "actor": "worker-059",
        "node_id": "F0",
        "group_id": "formulation",
        "class_id": CLASSES,
        "gate": "G-F0",
        "artifact_type": "independent_measurement",
        "path": checks_p,
        "sha256": hashes[checks_p],
        "validation_status": "unverified",
        "reviewed_sha256": REVIEWED,
        "evidence_refs": [f"artifacts/worker-059/f0_adjudication/snapshot/f0.276009f4f63d.yaml#{REVIEWED[:12]}"],
        "falsifier": "Re-running adjudicate_f0.py at 276009f4 must reproduce the recorded booleans; any different output falsifies this evidence file.",
    },
    {
        "event_id": f"{prefix}-artifact-blindspot",
        "event_type": "artifact",
        "created_at": now,
        "actor": "worker-059",
        "node_id": "F0",
        "group_id": "formulation",
        "class_id": CLASSES,
        "gate": "G-F0",
        "artifact_type": "controlled_experiment",
        "path": blind_p,
        "sha256": hashes[blind_p],
        "validation_status": "unverified",
        "reviewed_sha256": REVIEWED,
        "evidence_refs": ["artifacts/formulation/tools/check_taxonomy_consistency.py#de356d999ea3"],
        "falsifier": "If the scalar-mutant tree exits non-zero or the C2/C0 positive control exits zero on re-run, the blind-spot finding is falsified.",
    },
    {
        "event_id": f"{prefix}-review-f0",
        "event_type": "review",
        "created_at": now,
        "actor": "worker-059",
        "reviewer": "worker-059",
        "target_id": "F0",
        "target_path": "research_map/formulation_taxonomy.yaml",
        "node_id": "F0",
        "class_id": CLASSES,
        "gate": "G-F0",
        "reviewed_sha256": REVIEWED,
        "artifact": review_p,
        "sha256": hashes[review_p],
        "verdict": "revise",
        "score": 3.0,
        "counts_as_independent_verdict": True,
        "counts_as_full_schema_verdict": True,
        "counts_as_independent_second_verdict": False,
        "adjudicates": ["worker-040 accept 4.0", "worker-082 revise 3.5"],
        "hard_failures": hard,
        "findings": findings,
        "evidence_refs": [
            f"{checks_p}#{hashes[checks_p][:12]}",
            f"{blind_p}#{hashes[blind_p][:12]}",
            f"{report_p}#{hashes[report_p][:12]}",
        ],
        "next_falsifier": next_f,
    },
    {
        "event_id": f"{prefix}-blocker-binding",
        "event_type": "blocker",
        "created_at": now,
        "actor": "worker-059",
        "node_id": "F0",
        "group_id": "formulation",
        "class_id": CLASSES,
        "gate": "G-F0",
        "description": (
            "A binding accept at F0 276009f4 is not available at this hash: (1) "
            "class_scope_adjudication D3 is recorded resolved but is measurable-false for "
            "AF-WCC-SCALAR-SPH, whose conclusion quantifies bare 'generic data' against its own H4 "
            "and the file's genericity_kind rule; (2) that conclusion asserts an unsourced "
            "'equivalently... hidden behind an event horizon' that AF-WCC-VAC-GEN explicitly "
            "declines to assert (HF-06, candidate consequence C1); (3) the CONSISTENT certification "
            "cited by the accept cannot detect a D3 regression in that class. The structural "
            "surface (4 ids, 6/6 disjointness, class-separation) is independently green."
        ),
        "needed_to_unblock": (
            "Give the scalar conclusion the same quantifier discipline as the three vacuum classes "
            "or an explicit conditional on the unresolved genericity notion; move the "
            "horizon/visibility 'equivalently' to candidate_consequences with status unresolved and "
            "the HF-06 disclaimer; repair D3 to enumerate which classes bind the quantifier; extend "
            "check_taxonomy_consistency.py to iterate class_ids (it currently names only the C2/C0 "
            "pair); publish the F0 mirror byte-identically; then hold F0 stable for a full review "
            "window so two independent accepts can bind one hash."
        ),
        "evidence_refs": [
            f"{review_p}#{hashes[review_p][:12]}",
            f"{blind_p}#{hashes[blind_p][:12]}",
            f"{checks_p}#{hashes[checks_p][:12]}",
        ],
        "expected_information_gain": "high: removes the accept/revise split and unblocks G-F0/G-AUDIT on F0.",
    },
    {
        "event_id": f"{prefix}-status-checkpoint",
        "event_type": "status",
        "created_at": now,
        "actor": "worker-059",
        "node_id": "F0",
        "group_id": "formulation",
        "class_id": CLASSES,
        "gate": "G-F0",
        "status": "active",
        "hours": 0.5,
        "checkpoint_id": checkpoint["checkpoint_id"],
        "summary": (
            "W059-F0-ADJUDICATE-01 complete: independent adjudication of F0 at canonical sha256 "
            "276009f4 (no drift at finalize 00:29:04). Verdict revise 3.0; W082-F-01/F-02 "
            "substantiated; W040 accept not safe as a binding accept. Green baseline independently "
            "reproduced (strict parse, 4 ids, 6/6 disjointness, class completeness, classsep clean, "
            "validate_taxonomy 253/253, classsep_regression FP/FN 0). Artifacts under "
            "artifacts/worker-059/f0_adjudication/; worker-level checkpoint "
            "checkpoint_w059_f0adj.json. No global state mutated; no node completion or gate verdict "
            "claimed."
        ),
        "evidence_refs": [
            f"{review_p}#{hashes[review_p][:12]}",
            f"{ckpt_p}#{hashes[ckpt_p][:12]}",
            f"{report_p}#{hashes[report_p][:12]}",
            "research_map/formulation_taxonomy.yaml#276009f4f63d",
        ],
        "next_falsifier": next_f,
    },
]

existing = set()
if OUT.exists():
    for line in OUT.read_text().splitlines():
        if line.strip():
            existing.add(json.loads(line)["event_id"])
seen_path = ROOT / "runtime/state/ingested_ids.json"
if seen_path.exists():
    existing |= set(json.loads(seen_path.read_text()))

for e in events:
    validate_event(e)
    if e["event_id"] in existing:
        raise SystemExit(f"duplicate event_id: {e['event_id']}")

with OUT.open("a") as fh:
    for e in events:
        fh.write(json.dumps(e, ensure_ascii=False) + "\n")
print(f"appended {len(events)} schema-valid events to {OUT}")
for e in events:
    print(" ", e["event_id"], e["event_type"])
