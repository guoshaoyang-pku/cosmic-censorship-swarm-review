#!/usr/bin/env python3
"""W48-F1-REV13-CLOSURE-RERUN-01 — emit validated upward events for worker-048.

Idempotent: events are keyed by fixed event_id and appended to
comms/outbox/worker-048.jsonl only if absent. Every event is checked with
research_map.schemas.validate_event before it is written; a validation failure
aborts the whole emission (fail-closed) so no partial invalid traffic lands.

Usage: python3 emit_events.py [--outbox comms/outbox/worker-048.jsonl]
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

D = Path(__file__).resolve().parent
REL = D.relative_to(ROOT)
TASK = "W48-F1-REV13-CLOSURE-RERUN-01"
CLASS = "AF-WCC-VAC-GEN"
NODE = "F1"
GATE = "G-FORM"
SCHEMA_SHA = "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"
FROZEN_SHA = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
CST = datetime.timezone(datetime.timedelta(hours=8))


def now() -> str:
    return datetime.datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


FILES = [
    ("check_f1_closure_rev13.py", "closure_checker"),
    ("report.json", "closure_rerun_report"),
    ("report_run2.json", "closure_rerun_report_replicate"),
    ("checker_v1_crash.json", "instrument_defect_evidence"),
    ("checker_diff.patch", "instrument_hardening_diff"),
    ("inputs_manifest.json", "input_drift_manifest"),
    ("review_coverage_probe.py", "review_coverage_probe_tool"),
    ("review_coverage_probe.json", "review_coverage_probe_output"),
    ("README.md", "closure_rerun_summary"),
]
REVIEW_FILE = ROOT / "reviews/F1-review-worker-048-rev13-closure.json"

FALSIFIER = ("At the bytes recorded in inputs_manifest.json: (a) any PASS closure check that fails on "
             "an independent re-implementation at those bytes; (b) C5 passing once symbol_definitions is "
             "added or the recognised binding keys include predicate_abbreviation and completeness_definition; "
             "(c) any control that does not flip as declared; (d) a controller disposition already recorded at "
             "snapshot time that closes C4 otherwise than REC-3; (e) a review_coverage probe at the same "
             "instant returning different counts from the files then on disk. A later write to the live files "
             "is not a falsifier - it is a new revision to re-run against.")


def build() -> list[dict]:
    ts = now()
    arts = []
    ev = []
    for name, kind in FILES:
        p = D / name
        s = sha(p)
        arts.append(f"{REL}/{name}#{s[:12]}")
        ev.append({
            "event_id": f"w48-rev13rerun-artifact-{name.replace('.', '-')}",
            "event_type": "artifact", "created_at": ts, "actor": "worker-048",
            "node_id": NODE, "class_id": CLASS, "gate": GATE, "task_id": TASK,
            "artifact_type": kind, "path": f"{REL}/{name}", "sha256": s,
            "validation_status": "unverified",
            "summary": {
                "check_f1_closure_rev13.py": "hardened copy of checker b8fd03f8f983 (dict/list/str hash-field flattening); 9 checks + 6 controls",
                "report.json": "run1 at rev13 d9cebb9404b2: verdict revise; C1/C2/C3/C6 PASS, C4 UNRESOLVED (criterion superseded by REC-3), C5 FAIL, C7/C8 PASS, C9 FAIL advisory; controls 6/6",
                "report_run2.json": "run2 replicate 01:00:40: identical verdicts and controls; live review corpus grew 3->5 hash-bound files",
                "checker_v1_crash.json": "reproduced TypeError: unhashable type 'dict' at check_c9_review_status in pinned checker b8fd03f8f983",
                "checker_diff.patch": "39-line diff b8fd03f8f983 -> 38bdaaee (hash-field normalisation only; no check-semantics change)",
                "inputs_manifest.json": "five pinned input hashes re-measured after the run; drift_detected=false",
                "review_coverage_probe.py": "standalone reproduction of astra_lifecycle.review_coverage at the rev13 pins",
                "review_coverage_probe.json": "probe 01:01:12: F1 3 accepts (045/075/085) + 3 revises (002/073/029-scoped); F2a 3 accepts; F2b 0 accepts",
                "README.md": "human-readable verdict, per-check delta vs 9a8bd4c96800, advisories, controls, falsifier, reproduce",
            }[name],
            "evidence_refs": [f"{REL}/{name}#{s[:12]}", f"schemas/af_wcc_vacuum.yaml#{SCHEMA_SHA[:12]}",
                              f"artifacts/formulation/FROZEN.json#{FROZEN_SHA[:12]}"],
            "falsifier": FALSIFIER,
        })
    rev_sha = sha(REVIEW_FILE) if REVIEW_FILE.exists() else None
    review_ref = f"reviews/{REVIEW_FILE.name}#{rev_sha[:12]}" if rev_sha else "reviews/(missing)"
    ev.append({
        "event_id": "w48-rev13rerun-artifact-review-file",
        "event_type": "artifact", "created_at": ts, "actor": "worker-048",
        "node_id": NODE, "class_id": CLASS, "gate": GATE, "task_id": TASK,
        "artifact_type": "hash_bound_review_verdict", "path": f"reviews/{REVIEW_FILE.name}",
        "sha256": rev_sha, "validation_status": "unverified",
        "summary": "hash-bound F1 review file (scoped: counts_as_full_schema_verdict=false) so the controller review_coverage scan can bind the closure verdict",
        "evidence_refs": [review_ref, f"schemas/af_wcc_vacuum.yaml#{SCHEMA_SHA[:12]}"],
        "falsifier": FALSIFIER,
    })
    ev.append({
        "event_id": "w48-rev13rerun-status-start",
        "event_type": "status", "created_at": ts, "actor": "worker-048",
        "node_id": NODE, "class_id": CLASS, "gate": GATE, "task_id": TASK,
        "status": "active", "hours": 0.3,
        "summary": ("Took ONE bounded class-bound task from the live queue: W48-F1-REV13-CLOSURE-RERUN-01 = "
                    "re-execute the pre-registered F1 closure preflight (b8fd03f8f983, 9 checks + 6 controls) at the "
                    "just-landed rev13 d9cebb9404b2 / FROZEN rev29 815e08079aef, answering whether rev13 closed the "
                    "C1/C2/C5/C6 defects the earlier preflight made blocking. Read-only wrt shared artifacts; writes "
                    "only artifacts/worker-048/ plus one reviews/ verdict file. Not a gate verdict, not a node completion."),
        "evidence_refs": [f"{REL}/report.json#{sha(D/'report.json')[:12]}", f"schemas/af_wcc_vacuum.yaml#{SCHEMA_SHA[:12]}"],
        "next_falsifier": FALSIFIER,
    })
    ev.append({
        "event_id": "w48-rev13rerun-claim",
        "event_type": "claim", "created_at": ts, "actor": "worker-048",
        "node_id": NODE, "class_id": CLASS, "class_ids": [CLASS], "gate": GATE, "task_id": TASK,
        "conclusion_type": "formal_model",
        "statement": ("FORMAL-MODEL-LEVEL closure finding (not a theorem, not a numerical result) at the rev13 bytes "
                      "schemas/af_wcc_vacuum.yaml#d9cebb9404b2 (FROZEN rev29 815e08079aef; inputs drift-free): of the four "
                      "defects the earlier W48-F1-CLOSURE-PREFLIGHT-01 made blocking, C1 (duplicate revised_at keys), C2 "
                      "(future-dated timestamps) and C6 (whole-curve vs TAIL containment) are closed at rev13, and C3 is "
                      "closed by repointing class_contract_pointer to research_map/formulation_taxonomy.yaml#classes."
                      "AF-WCC-VAC-GEN (the supplement-side fragment is now the dangling side; expected under REC-3). C5 does "
                      "not close: complete(I+_D) still has no symbol->definition binding of any recognised kind and AF_{I+} "
                      "is bound only by i_plus.predicate_abbreviation, which the frozen C5 binding-key whitelist does not "
                      "recognise; a one-line symbol_definitions map, or audit-lead adjudication extending the recognised "
                      "keys, clears it. C4's frozen byte-identity criterion is superseded by controller REC-3 (F0 companion "
                      "pair; byte-identity not a publication requirement) while FROZEN.f0_mirror_adjudication_request.status "
                      "is stale metadata. C7/C8 pass; C9 remains advisory (review_status.independent_reviewers=[]; the "
                      "controller's _explicit_pins also ignores dict-valued hash bindings, hiding 2 hash-bound F1 revises). "
                      "Instrument: pinned checker b8fd03f8f983 cannot complete at rev13 (TypeError on dict-valued "
                      "reviewed_sha256, reproduced in checker_v1_crash.json); the hardened copy 38bdaaee preserves all check "
                      "semantics, is deterministic across two runs and passes 6/6 mutation controls. Advisory corpus probe at "
                      "01:01:12 found F1 3 distinct full accepts (worker-045/075/085) + 3 revises, F2a 3 accepts, F2b 0 accepts."),
        "assumptions": [
            "the report's inputs map is the bytes the checker read; inputs_manifest.json re-measures them after the run and drift_detected=false",
            "the frozen C5 criterion (b8fd03f8f983) is the operative closure criterion; whether predicate_abbreviation/completeness_definition should count is an audit-lead adjudication, not a worker decision",
            "REC-3 (astra-lifecycle-04 decisions, ruling 0) is a recorded controller disposition for the F0 companion pair",
            "the review-coverage probe is an advisory scan of a live corpus at one instant, not a gate verdict",
        ],
        "falsifier": FALSIFIER,
        "evidence_refs": arts + [review_ref, f"schemas/af_wcc_vacuum.yaml#{SCHEMA_SHA[:12]}",
                                 f"artifacts/formulation/FROZEN.json#{FROZEN_SHA[:12]}",
                                 "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
                                 "runtime/state/controller_verification/astra-lifecycle-04-decisions.json"],
        "artifact_refs": [f"{REL}/report.json#{sha(D/'report.json')[:12]}",
                          f"{REL}/report_run2.json#{sha(D/'report_run2.json')[:12]}",
                          f"{REL}/README.md#{sha(D/'README.md')[:12]}"],
    })
    ev.append({
        "event_id": "w48-rev13rerun-review",
        "event_type": "review", "created_at": ts, "actor": "worker-048",
        "target_id": f"schemas/af_wcc_vacuum.yaml#{SCHEMA_SHA}",
        "node_id": NODE, "class_id": CLASS, "gate": GATE, "task_id": TASK,
        "reviewer": "worker-048", "verdict": "revise", "score": 3.5,
        "counts_as_full_schema_verdict": False,
        "review_kind": "pre-registered closure-criteria re-run at rev13; not a full semantic schema review",
        "summary": "C1/C2/C3/C6 closed; C5 still fails under the frozen criterion; C4 criterion superseded by REC-3; controls 6/6; verdict revise.",
        "hard_failures": [{"id": "W48-F1R13-HF-1", "check": "C5",
                           "claim": "conclusion.statement_formal symbols AF_{I+} and complete lack machine-readable bindings the frozen C5 helper recognises"}],
        "findings": [{"id": "W48-F1R13-CLOSED", "severity": "info", "check": "C1,C2,C3,C6"},
                     {"id": "W48-F1R13-A2", "severity": "advisory", "check": "C4"},
                     {"id": "W48-F1R13-A3", "severity": "advisory", "check": "C9"},
                     {"id": "W48-F1R13-A1", "severity": "instrument", "check": "checker-v1"}],
        "falsifier": FALSIFIER,
        "evidence_refs": [review_ref, f"{REL}/report.json#{sha(D/'report.json')[:12]}",
                          f"{REL}/report_run2.json#{sha(D/'report_run2.json')[:12]}",
                          f"schemas/af_wcc_vacuum.yaml#{SCHEMA_SHA[:12]}",
                          f"artifacts/formulation/FROZEN.json#{FROZEN_SHA[:12]}"],
    })
    ev.append({
        "event_id": "w48-rev13rerun-status-complete",
        "event_type": "status", "created_at": ts, "actor": "worker-048",
        "node_id": NODE, "class_id": CLASS, "gate": GATE, "task_id": TASK,
        "status": "active", "hours": 0.3,
        "summary": ("W48-F1-REV13-CLOSURE-RERUN-01 complete at worker level: 10 artifacts hash-pinned (hardened checker 38bdaaee, "
                    "run1 report, run2 replicate, v1-crash reproduction, 39-line diff, drift-free inputs manifest, coverage probe, "
                    "README, hash-bound review file); 6/6 controls pass; two runs identical. Verdict revise (C5 residual; C4 "
                    "criterion superseded by REC-3; C9 advisory). Not a gate verdict, no node transition, no canonical write; "
                    "worker events cannot set done/passed. Checkpoint runtime/state/w048_f1_rev13_closure_rerun_checkpoint.json."),
        "evidence_refs": [f"{REL}/report.json#{sha(D/'report.json')[:12]}", review_ref],
        "next_falsifier": FALSIFIER,
    })
    return ev


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outbox", default=str(ROOT / "comms/outbox/worker-048.jsonl"))
    a = ap.parse_args()
    outbox = Path(a.outbox)
    events = build()
    for e in events:  # fail-closed: validate all before writing any
        validate_event(e)
    existing = set()
    if outbox.exists():
        for line in outbox.read_text().splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    existing.add(json.loads(line).get("event_id"))
                except ValueError:
                    pass
    appended, skipped = [], []
    with outbox.open("a") as f:
        for e in events:
            if e["event_id"] in existing:
                skipped.append(e["event_id"])
                continue
            f.write(json.dumps(e, sort_keys=True) + "\n")
            appended.append(e["event_id"])
    receipt = {"task_id": TASK, "validated": len(events), "appended": appended, "skipped_duplicates": skipped,
               "outbox": str(outbox), "emitted_at": now()}
    (D / "emitted_events.json").write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
