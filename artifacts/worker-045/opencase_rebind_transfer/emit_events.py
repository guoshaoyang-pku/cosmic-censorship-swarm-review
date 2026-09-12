#!/usr/bin/env python3
"""Emit the W045-OPENCASE-REBIND-TRANSFER-01 events.

Writes:
  artifacts/worker-045/opencase_rebind_transfer/checkpoint.json
  runtime/state/w045_opencase_rebind_checkpoint.json            (mirror)
  comms/outbox/worker-045.jsonl                                 (append, validated)

Self-rejects before sending: artifact existence + sha256, unique event ids vs the
outbox and the controller's ingested-id list, schema validation, class-id match.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.dirname(__file__))
while not os.path.isdir(os.path.join(ROOT, "research_map")):
    parent = os.path.dirname(ROOT)
    if parent == ROOT:
        raise SystemExit("repo root not found")
    ROOT = parent
sys.path.insert(0, ROOT)
from research_map.schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
OUT = os.path.join(ROOT, "artifacts/worker-045/opencase_rebind_transfer")
REL = "artifacts/worker-045/opencase_rebind_transfer"
OUTBOX = os.path.join(ROOT, "comms/outbox/worker-045.jsonl")
STATE = os.path.join(ROOT, "runtime/state/w045_opencase_rebind_checkpoint.json")
TASK = "W045-OPENCASE-REBIND-TRANSFER-01"
CLASS4 = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH"
NOW = datetime.now(CST).isoformat(timespec="seconds")
STAMP = datetime.now(CST).strftime("%Y%m%dT%H%M")

REPORT = "report.json"
TOOL = "run_opencase_rebind_transfer.py"
README = "README.md"
CHECKPOINT = "checkpoint.json"


def sha(p: str) -> str:
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def rel(p: str) -> str:
    return f"{REL}/{p}"


report = json.load(open(os.path.join(OUT, REPORT), encoding="utf-8"))
report_hash = sha(os.path.join(OUT, REPORT))
tool_hash = sha(os.path.join(OUT, TOOL))
readme_hash = sha(os.path.join(OUT, README))
assert report["verdict"].startswith("TRANSFER_VERIFIED"), report["verdict"]

checkpoint = {
    "task_id": TASK,
    "actor": "worker-045",
    "created_at": NOW,
    "node_id": "F0",
    "gate": "G-F0",
    "class_id": CLASS4,
    "verdict": report["verdict"],
    "pins": report["checks"]["A_pins"]["measured"],
    "open_case_ids": report["checks"]["B_open_set_identity"]["live_open_ids"],
    "disposition_census": report["checks"]["E_matrix_validity"]["disposition_census"],
    "controls": {k: v["status"] for k, v in report["controls"].items()},
    "findings": report["findings"],
    "artifacts": {
        rel(REPORT): report_hash,
        rel(TOOL): tool_hash,
        rel(README): readme_hash,
    },
    "next_falsifier": report["falsifier"],
    "authority_note": report["authority_note"],
}
with open(os.path.join(OUT, CHECKPOINT), "w", encoding="utf-8") as f:
    json.dump(checkpoint, f, indent=1, sort_keys=True)
    f.write("\n")
checkpoint_hash = sha(os.path.join(OUT, CHECKPOINT))
with open(STATE, "w", encoding="utf-8") as f:
    json.dump(checkpoint, f, indent=1, sort_keys=True)
    f.write("\n")

g = report["checks"]["G_binding_staleness"]
c = report["checks"]["C_pin_only_delta"]
b = report["checks"]["B_open_set_identity"]
e = report["checks"]["E_matrix_validity"]
f_ = report["checks"]["F_cross_source_agreement"]

artifact_common = {
    "actor": "worker-045",
    "class_id": CLASS4,
    "class_ids": CLASS4.split(";"),
    "gate": "G-F0",
    "created_at": NOW,
    "next_falsifier": report["falsifier"],
}
artifacts = [
    dict(artifact_common, event_id=f"w045-opencase-rebind-art-{STAMP}-report",
         event_type="artifact", node_id="F0",
         artifact_type="opencase_rebind_transfer_report", path=rel(REPORT),
         sha256=report_hash, validation_status="unverified",
         summary=(f"Deterministic transfer verification of the 9-open-case disposition matrix at the "
                  f"repaired corpus ccf7041bd0ff / taxonomy 0abb9ed8a961. Verdict {report['verdict']}; "
                  f"checks B-G pass; controls 5/5; content delta claim-pinned->live is binding_status only "
                  f"(36/36 rows); 0/9 open axis vectors match a frozen class; matrix 7 new-class + 2 split, "
                  f"agreeing with worker-083."),
         evidence_refs=[f"schemas/taxonomy_cases.jsonl#{report['checks']['A_pins']['measured']['corpus_live'][:12]}",
                        f"research_map/formulation_taxonomy.yaml#{report['checks']['A_pins']['measured']['taxonomy_live'][:12]}",
                        f"artifacts/flash-02/open_case_disposition.json#{report['checks']['A_pins']['measured']['matrix_flash02'][:12]}"]),
    dict(artifact_common, event_id=f"w045-opencase-rebind-art-{STAMP}-tool",
         event_type="artifact", node_id="F0",
         artifact_type="opencase_rebind_transfer_tool", path=rel(TOOL),
         sha256=tool_hash, validation_status="unverified",
         summary="Read-only stdlib+PyYAML checker: open-set identity, pin-only delta with declared CONTENT_KEYS, "
                 "axis-vector non-match vs frozen classes, matrix token/coverage validity, cross-source agreement, "
                 "binding staleness, and 5 controls (determinism, mutation, tamper, restamp invariance, drift).",
         evidence_refs=[f"{rel(TOOL)}#{tool_hash[:12]}"]),
    dict(artifact_common, event_id=f"w045-opencase-rebind-art-{STAMP}-readme",
         event_type="artifact", node_id="F0",
         artifact_type="opencase_rebind_transfer_readme", path=rel(README),
         sha256=readme_hash, validation_status="unverified",
         summary="Method, pins, measured result table, findings, falsifier, reproduce command and limitations. "
                 "States that the 7+2 disposition content transfers but remains bound to superseded bytes.",
         evidence_refs=[f"{rel(README)}#{readme_hash[:12]}"]),
    dict(artifact_common, event_id=f"w045-opencase-rebind-art-{STAMP}-checkpoint",
         event_type="artifact", node_id="F0",
         artifact_type="worker_checkpoint", path=rel(CHECKPOINT),
         sha256=checkpoint_hash, validation_status="unverified",
         summary=f"Worker checkpoint: verdict {report['verdict']}, pins, open-case ids, controls, findings, "
                 f"artifact hashes. Mirrored at runtime/state/w045_opencase_rebind_checkpoint.json.",
         evidence_refs=[f"{rel(CHECKPOINT)}#{checkpoint_hash[:12]}"]),
]

claim = {
    "actor": "worker-045",
    "event_id": f"w045-opencase-rebind-claim-{STAMP}",
    "event_type": "claim",
    "created_at": NOW,
    "node_id": "F0",
    "gate": "G-F0",
    "class_id": CLASS4,
    "class_ids": CLASS4.split(";"),
    "conclusion_type": "formal_model",
    "claims_theorem_status": False,
    "statement": (
        f"Artifact-and-checker result (not a mathematics or physics claim, not a gate verdict) at live pins "
        f"schemas/taxonomy_cases.jsonl#{report['checks']['A_pins']['measured']['corpus_live'][:12]} (post-repair), "
        f"research_map/formulation_taxonomy.yaml#{report['checks']['A_pins']['measured']['taxonomy_live'][:12]}, "
        f"artifacts/flash-02/open_case_disposition.json#{report['checks']['A_pins']['measured']['matrix_flash02'][:12]}: "
        f"(1) the repaired corpus differs from the operative claim's pinned snapshot "
        f"(artifacts/flash-02/snapshots/taxonomy_cases.pre-rebind-r2.f0c20b96.jsonl) in exactly one key across all "
        f"36 case rows, binding_status ({c['changed_case_count']}/36); zero CONTENT_KEYS differ, so the 00:42 repair "
        f"is a pure pin restamp; (2) the live open=true set equals the matrix row set exactly "
        f"({b['live_open_count']} ids, no missing/extra/duplicate); (3) {len(report['checks']['D_axis_nonmatch']['exact_matches'])}/9 "
        f"open-row axis vectors equal any frozen class axis vector, so the 7 new-class / 2 split classification is not a "
        f"nearest-class collapse; (4) the matrix is 7 NEW_CLASS_REQUEST_DEFERRED_TO_HUMAN_PI (each with "
        f"coverage_gaps.CG2) + 1 SPLIT_REQUIRED (TC-F0-N14) + 1 SPLIT_AND_BRIDGE_REQUIRED (TC-F0-N15), all tokens "
        f"declared, frozen_class_ids equal to the four taxonomy class ids, and worker-083's independently derived "
        f"matrix gives the same 7/2 family split; (5) every binding that carries the disposition is stale versus the "
        f"live bytes: matrix corpus_ref {g['matrix_corpus_ref_sha256'][:12]} != live {g['live_corpus_sha256'][:12]}, "
        f"matrix taxonomy ref and row pins {g['matrix_row_taxonomy_pins']} != live {g['live_taxonomy_sha256'][:12]}, "
        f"operative claim corpus pin {g['operative_claim_corpus_pin']} != live, and the claim has no superseder in the "
        f"map snapshot. Consequence: the disposition content transfers to the repaired corpus and needs no "
        f"re-derivation, but the matrix and the claim must be re-pinned to ccf7041bd0ff / 0abb9ed8a961 before any "
        f"G-F0 scan can bind them."),
    "assumptions": [
        "the claim-pinned snapshot is byte-exact for the corpus bytes the operative claim was computed against "
        "(its sha256 equals the f0c20b96f76d pin in that claim)",
        "the nine open=true rows are the authoritative undispositioned set (the matrix itself declares this)",
        "axis_vector fields as recorded in the corpus are the basis for frozen-class comparison; prose is not re-parsed",
        "the worker-083 matrix is independent (different actor, independently derived) and is used only for "
        "aggregate cross-checking",
    ],
    "falsifier": report["falsifier"],
    "evidence_refs": [
        f"schemas/taxonomy_cases.jsonl#{report['checks']['A_pins']['measured']['corpus_live'][:12]}",
        f"research_map/formulation_taxonomy.yaml#{report['checks']['A_pins']['measured']['taxonomy_live'][:12]}",
        f"artifacts/flash-02/open_case_disposition.json#{report['checks']['A_pins']['measured']['matrix_flash02'][:12]}",
        f"artifacts/flash-02/snapshots/taxonomy_cases.pre-rebind-r2.f0c20b96.jsonl#{report['checks']['A_pins']['measured']['corpus_claim_pin_snapshot'][:12]}",
        f"artifacts/worker-083/f0_open_case_disposition/dispositions.json#{report['checks']['A_pins']['measured']['matrix_worker083'][:12]}",
        f"{rel(REPORT)}#{report_hash[:12]}",
    ],
    "artifact_refs": [
        {"path": rel(REPORT), "sha256": report_hash},
        {"path": rel(TOOL), "sha256": tool_hash},
        {"path": rel(CHECKPOINT), "sha256": checkpoint_hash},
    ],
}

review = {
    "actor": "worker-045",
    "event_id": f"w045-opencase-rebind-review-{STAMP}",
    "event_type": "review",
    "created_at": NOW,
    "node_id": "F0",
    "gate": "G-F0",
    "class_id": CLASS4,
    "class_ids": CLASS4.split(";"),
    "target_id": "F0:flash02-opencase-claim-0010b-supersede-20260912T003552",
    "reviewer": "worker-045",
    "verdict": "revise",
    "score": 4.0,
    "hard_failures": [
        "H1 (binding): the claim and its matrix are pinned to superseded corpus/taxonomy bytes "
        f"(matrix corpus {g['matrix_corpus_ref_sha256'][:12]}, matrix taxonomy {g['matrix_taxonomy_ref_sha256'][:12]}, "
        f"claim corpus {g['operative_claim_corpus_pin']}) while the live corpus is "
        f"{g['live_corpus_sha256'][:12]} and live taxonomy {g['live_taxonomy_sha256'][:12]}; the claim is unbound from "
        f"the bytes it would gate",
    ],
    "findings": [
        "content transfer verified: the repaired corpus is a pure pin restamp (binding_status only, 36/36 rows), so the "
        "7+2 disposition matrix reproduces without re-derivation",
        f"open-set identity exact: {b['live_open_count']}/9 ids, no missing, extra or duplicate matrix rows",
        "0/9 open-row axis vectors equal a frozen class axis vector; the new-class/split classifications are not "
        "nearest-class collapse artifacts",
        "matrix token/coverage validity passes (7 CG2 new-class requests + N14 split + N15 split-and-bridge, "
        "frozen_class_ids match) and worker-083's independently derived matrix agrees at the family level",
        "no superseding claim for flash02-opencase-claim-0010b-supersede-20260912T003552 exists in the map snapshot, so "
        "the stale binding is live, not historical",
    ],
    "evidence_refs": [
        f"{rel(REPORT)}#{report_hash[:12]}",
        f"schemas/taxonomy_cases.jsonl#{report['checks']['A_pins']['measured']['corpus_live'][:12]}",
        f"artifacts/flash-02/open_case_disposition.json#{report['checks']['A_pins']['measured']['matrix_flash02'][:12]}",
    ],
    "scope_note": "Binding-and-transfer review of the disposition chain only; the class-scope decisions themselves "
                  "(new class vs split, and the deferred CG2 requests) were not re-adjudicated.",
}

status = {
    "actor": "worker-045",
    "event_id": f"w045-opencase-rebind-status-{STAMP}",
    "event_type": "status",
    "created_at": NOW,
    "node_id": "F0",
    "gate": "G-F0",
    "class_id": CLASS4,
    "class_ids": CLASS4.split(";"),
    "status": "active",
    "hours": 0.35,
    "summary": (
        f"{TASK} complete at worker level (no node/gate transition claimed, no canonical artifact edited). "
        f"VERDICT {report['verdict']}, controls 5/5. The 00:42 corpus repair is a pure pin restamp "
        f"(binding_status only across 36/36 rows), the 9 live open cases equal the matrix rows exactly, 0/9 open "
        f"axis vectors match a frozen class, the matrix is 7 CG2 new-class + N14 split + N15 split-and-bridge and "
        f"agrees with worker-083's independent matrix. All disposition bindings are stale versus live bytes "
        f"(matrix corpus b9699119bbab, matrix taxonomy 565a6e505188, claim corpus f0c20b96f76d vs live "
        f"ccf7041bd0ff / 0abb9ed8a961). Artifact {rel(REPORT)}#{report_hash[:12]}."),
    "evidence_refs": [
        f"{rel(REPORT)}#{report_hash[:12]}",
        f"{rel(CHECKPOINT)}#{checkpoint_hash[:12]}",
        f"schemas/taxonomy_cases.jsonl#{report['checks']['A_pins']['measured']['corpus_live'][:12]}",
    ],
    "next_falsifier": report["falsifier"],
}

blocker = {
    "actor": "worker-045",
    "event_id": f"w045-opencase-rebind-blocker-{STAMP}",
    "event_type": "blocker",
    "created_at": NOW,
    "node_id": "F0",
    "gate": "G-F0",
    "class_id": CLASS4,
    "class_ids": CLASS4.split(";"),
    "description": (
        "G-F0's open-case item is content-satisfied but binding-stale: the only disposition of the 9 open cases "
        f"(artifacts/flash-02/open_case_disposition.json#{report['checks']['A_pins']['measured']['matrix_flash02'][:12]}) "
        f"and the operative claim {report['operative_claim']} still pin corpus b9699119bbab / f0c20b96f76d and "
        f"taxonomy 565a6e505188, while the repaired live corpus measures ccf7041bd0ff and the live taxonomy "
        f"0abb9ed8a961. Independent transfer verification shows no content change is needed (the repair is a pure "
        f"pin restamp), so this is a re-pin + re-review action, not a re-derivation."),
    "needed_to_unblock": (
        "Owner (deepseek-flash-02 / formulation lead) re-pins the matrix corpus_ref and taxonomy refs and the claim's "
        "evidence_refs to schemas/taxonomy_cases.jsonl#ccf7041bd0ff and "
        "research_map/formulation_taxonomy.yaml#0abb9ed8a961, then a reviewer re-issues the verdict at the new bytes; "
        "no worker may edit another agent's canonical artifact."),
    "evidence_refs": [
        f"{rel(REPORT)}#{report_hash[:12]}",
        f"{rel(CHECKPOINT)}#{checkpoint_hash[:12]}",
        f"artifacts/flash-02/open_case_disposition.json#{report['checks']['A_pins']['measured']['matrix_flash02'][:12]}",
    ],
}

events = artifacts + [claim, review, status, blocker]

# ---- self-reject before sending
problems = []
for p, expected in [(rel(REPORT), report_hash), (rel(TOOL), tool_hash),
                    (rel(README), readme_hash), (rel(CHECKPOINT), checkpoint_hash)]:
    full = os.path.join(ROOT, p)
    if not os.path.exists(full):
        problems.append(f"missing artifact {p}")
    elif sha(full) != expected:
        problems.append(f"hash mismatch {p}")
    if p not in " ".join(json.dumps(e, sort_keys=True) for e in events):
        problems.append(f"artifact {p} not referenced by any event")
existing = set()
if os.path.exists(OUTBOX):
    for line in open(OUTBOX, encoding="utf-8", errors="ignore"):
        try:
            existing.add(json.loads(line).get("event_id"))
        except Exception:
            pass
ingested = set(json.load(open(os.path.join(ROOT, "runtime/state/ingested_ids.json"), encoding="utf-8")))
for e in events:
    if e["event_id"] in existing or e["event_id"] in ingested:
        problems.append(f"duplicate event_id {e['event_id']}")
    try:
        validate_event(e)
    except Exception as exc:  # schema self-check
        problems.append(f"schema {e['event_id']}: {exc}")
    if e.get("class_id") not in (CLASS4, None) and not e["class_id"].startswith("AF-"):
        problems.append(f"class binding {e['event_id']}: {e.get('class_id')}")
    if "theorem" == e.get("conclusion_type"):
        problems.append(f"theorem conclusion without authority {e['event_id']}")
if problems:
    print("SELF-REJECT:", json.dumps(problems, indent=1))
    raise SystemExit(2)

with open(OUTBOX, "a", encoding="utf-8") as f:
    for e in events:
        f.write(json.dumps(e, sort_keys=True) + "\n")
print(json.dumps({
    "emitted": len(events),
    "types": [e["event_type"] for e in events],
    "verdict": report["verdict"],
    "report": f"{rel(REPORT)}#{report_hash[:12]}",
    "checkpoint": f"{rel(CHECKPOINT)}#{checkpoint_hash[:12]}",
    "state_mirror": "runtime/state/w045_opencase_rebind_checkpoint.json",
}, indent=1))
