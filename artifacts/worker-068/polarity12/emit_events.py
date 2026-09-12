#!/usr/bin/env python3
"""W068-FORM-POLARITY-12 protocol-event emitter (worker-068).

Builds the upward events for the completed bounded task, validates every event against
research_map/schemas.py, verifies every cited artifact hash on disk, and appends the
events idempotently to comms/outbox/worker-068.jsonl (one JSON object per line).

  python3 emit_events.py                 # emit the task event set
  python3 emit_events.py --confirm-ckpt CKPT-ID --final PATH
                                         # emit the post-checkpoint confirmation event

Never sets status=done, validation_status=passed, or a gate verdict: the worker reports
`active` / `unverified` and leaves adjudication to the controller and group leads.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms" / "outbox" / "worker-068.jsonl"
sys.path.insert(0, str(ROOT / "research_map"))
import schemas  # noqa: E402

TASK = "W068-FORM-POLARITY-12"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
CLASS_ID = ";".join(CLASS_IDS)
NODE = "A1"
GATE = "G-CLASSBIND (folded into G-AUDIT as calibration evidence)"
GROUP = "formulation"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(rel: str, prefix: int = 12) -> str:
    return f"{rel}#sha256:{sha(ROOT / rel)[:prefix]}"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def read_json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text())


def load_existing_ids() -> set:
    ids = set()
    if OUTBOX.is_file():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ids.add(json.loads(line).get("event_id"))
            except Exception:
                pass
    return ids


def append_events(events: list) -> list:
    existing = load_existing_ids()
    appended = []
    for e in events:
        schemas.validate_event(e)  # raises SchemaError on malformed events
        if e["event_id"] in existing:
            continue
        OUTBOX.parent.mkdir(parents=True, exist_ok=True)
        with OUTBOX.open("a") as f:
            f.write(json.dumps(e, sort_keys=True) + "\n")
        existing.add(e["event_id"])
        appended.append(e["event_id"])
    return appended


def build_task_events() -> list:
    rel_report = "artifacts/worker-068/polarity12/report.json"
    rel_raw = "artifacts/worker-068/polarity12/raw_verdicts.json"
    rel_manifest = "artifacts/worker-068/polarity12/manifest.json"
    rel_checker = "artifacts/worker-068/polarity12/conclusion_freeze_check.py"
    rel_builder = "artifacts/worker-068/polarity12/build_corpus12.py"
    rel_runner = "artifacts/worker-068/polarity12/run_polarity12.py"
    rel_readme = "artifacts/worker-068/polarity12/README.md"
    rel_rule = "artifacts/worker-068/polarity12/candidate_rule.json"
    rel_ckpt = "artifacts/worker-068/polarity12/checkpoint.json"

    report = read_json(rel_report)
    new = report["new_corpus"]["metrics"]
    pooled = report["candidate_rule"]["union_corpora"]["freeze_statements"]["pooled"]
    pools = report["candidate_rule"]["union_corpora"]
    ev = []

    ev.append({
        "event_id": "w068-pol12-01-task-claim", "event_type": "status", "actor": "worker-068",
        "created_at": now(), "node_id": NODE, "group_id": GROUP, "gate": GATE,
        "class_ids": CLASS_IDS, "status": "active", "hours": 0.2,
        "summary": ("No assignment card exists in comms/inbox for worker-068 (this fleet instance). Took ONE bounded "
                    "class-bound task: W068-FORM-POLARITY-12 = measure whether conclusion-statement content "
                    "substitutions with no negation marker escape the two-stage pipeline on a fully pinned "
                    "three-class shadow, and evaluate a conclusion-freeze candidate rule on the new corpus and on "
                    "the union of FORM-HELDOUT-09 / FORM-POLARITY-10 / FORM-POLARITY-11. Measurement only."),
        "evidence_refs": [ref(rel_manifest), "comms/PROTOCOL.md"],
        "next_falsifier": report["next_falsifier"],
    })

    artifacts = [
        ("w068-pol12-02-manifest", rel_manifest, "corpus_manifest",
         "Manifest hashed before any stage run: 7 pinned shadow inputs, 33 fixtures with per-fixture sha256, "
         "rev11 bases, builder hash and union-corpus pins."),
        ("w068-pol12-03-report", rel_report, "measurement_report",
         "Report: valid=true; 24/27 content probes escape on the new pinned three-class shadow (12/12 "
         "substitution probes); R-CAND-F flags 24/24 new-corpus escapes and 14/14 union statement-axis "
         "escapes with 0/12 conforming-control false positives."),
        ("w068-pol12-04-raw", rel_raw, "raw_verdicts",
         "Per-fixture stage-A/stage-B verdicts with failed rules, escape flags, arm calibration and "
         "shadow/fixture hashes before and after the run."),
        ("w068-pol12-05-checker", rel_checker, "candidate_rule_implementation",
         "Standalone candidate rule R-CAND: freeze_statements / freeze_full / negation_only, PyYAML+stdlib, "
         "deterministic, CLI and importable."),
        ("w068-pol12-06-builder", rel_builder, "corpus_builder",
         "Deterministic builder: fails closed on pinned base drift, applies p1-p7 carried-over ops and s1-s4 "
         "non-negation substitution ops to conclusion fields only."),
        ("w068-pol12-07-runner", rel_runner, "measurement_runner",
         "Runner: shadow-pin and fixture-tamper checks before/after, stage subprocesses, rule evaluation on the "
         "new corpus and the union corpora, metrics and report/checkpoint emission."),
        ("w068-pol12-08-readme", rel_readme, "report_readme",
         "One-page human summary: question, pinned binding table, results, four findings, limitations, "
         "non-claims, falsifier, reproduction."),
        ("w068-pol12-09-candidate-rule", rel_rule, "candidate_rule_spec",
         "PROPOSAL ONLY (owner lead-formulation/lead-audit): rule R-CAND-F, placement options, measured "
         "catch/FP evidence, stricter and baseline variants, declared definition-axis gap W068-P12-G1."),
        ("w068-pol12-10-checkpoint-artifact", rel_ckpt, "worker_checkpoint",
         "Measurement checkpoint: manifest hash, validity, arm calibration, escape and catch counts, artifact "
         "hash set at checkpoint time."),
    ]
    for eid, rel, atype, summary in artifacts:
        ev.append({
            "event_id": eid, "event_type": "artifact", "actor": "worker-068", "created_at": now(),
            "node_id": NODE, "group_id": GROUP, "gate": GATE, "class_ids": CLASS_IDS,
            "artifact_type": atype, "path": rel, "sha256": sha(ROOT / rel), "validation_status": "unverified",
            "summary": summary,
        })

    ev.append({
        "event_id": "w068-pol12-11-claim", "event_type": "claim", "actor": "worker-068", "created_at": now(),
        "node_id": NODE, "group_id": GROUP, "gate": GATE, "class_id": CLASS_ID, "class_ids": CLASS_IDS,
        "conclusion_type": "numerical_evidence", "claims_completion": False, "review_status": "unverified",
        "statement": (
            "On a fully pinned three-class shadow (stage A 000e09e46b2f, stage B c79d8ab8440a, rule spec "
            "40f9bb9e657b, KEY_MANIFEST rev27 fce91948ba3a, archived rev11 bases W 9a8bd4c96800 / C2 "
            "b6123750b37d / C0 1bb78ce9b357) with all three identity arms accepted by both stages: 24 of 27 "
            "conclusion-content probes escape both stages, including 12/12 non-negation content-substitution "
            "probes spanning argument, quantifier-strength, quantifier-domain and object/regularity "
            "substitutions on all three classes. The candidate conclusion-freeze rule R-CAND-F flags 24/24 "
            "escaping content probes on this corpus and 14/14 conclusion-statement escapes in the union of "
            "FORM-HELDOUT-09 / FORM-POLARITY-10 / FORM-POLARITY-11, with 0/12 false positives on conforming "
            "controls; the negation-only baseline misses all 12 substitution probes. The union escape set "
            "decomposes into a conclusion-statement axis (14, all caught) and a non-statement/definitional axis "
            "(4 FORM-HELDOUT-08 references, none caught), the declared gap W068-P12-G1. This is a measurement "
            "about the pinned detector pipeline and the candidate rule, not a class-truth claim."),
        "assumptions": [
            "Escape = accepted by BOTH stages; the corpus and its labels are worker-068-built and require independent adjudication.",
            "The measurement is bound to the shadow bytes whose hashes are pinned in manifest.json; the live tree is not read.",
            "The union-corpus evaluation compares each fixture against its own corpus base (heldout3 rev11, polarity10 rev12, polarity11 own W shadow + polarity10 C2/C0) and is a re-analysis at pinned bytes.",
            "The candidate rule is a proposal: adoption, rule-id assignment and gate placement belong to lead-formulation / lead-audit.",
        ],
        "falsifier": report["falsifier"],
        "next_falsifier": report["next_falsifier"],
        "evidence_refs": [ref(rel_report), ref(rel_raw), ref(rel_manifest), ref(rel_rule)],
        "artifact_refs": [rel_report, rel_raw, rel_manifest, rel_rule],
        "measurements": {
            "new_corpus_escapes": new["stage"]["escapes"],
            "substitution_escapes": new["stage"]["substitution_probes"]["escapes"],
            "polarity_escapes": new["stage"]["polarity_probes"]["escapes"],
            "freeze_statements_new_corpus_flagged": new["candidate_rule"]["freeze_statements"]["content_probes"]["flagged"],
            "freeze_statements_union_statement_axis_caught": pooled["escapes"]["flagged"],
            "freeze_statements_union_control_fp": pooled["conforming_controls"]["flagged"],
            "negation_only_substitution_caught": new["candidate_rule"]["negation_only"]["substitution_probes"]["flagged"],
        },
    })

    ev.append({
        "event_id": "w068-pol12-12-blocker-content-gap", "event_type": "blocker", "actor": "worker-068",
        "created_at": now(), "node_id": NODE, "group_id": GROUP, "gate": GATE, "class_ids": CLASS_IDS,
        "description": (
            "(1) Definition-axis gap W068-P12-G1: the FORM-HELDOUT-08 reference escapes m04/m16/m25/m29 are "
            "accepted by both stages with conclusion statements identical to the base; their changed leaves are "
            "outside conclusion.statement_* (class_identity_variants, anti_scope, i_plus.completeness_definition). "
            "R-CAND-F catches 0/4 of them; a definition-site freeze (R-CAND-D) is unimplemented and unmeasured. "
            "(2) The candidate rule is a proposal with no independent adjudication: the 33-fixture corpus, the 24 "
            "escape labels and the 12 substitution probes are worker-068-built, and worker-068 also wrote the rule "
            "being evaluated."),
        "needed_to_unblock": (
            "Lead-formulation / lead-audit adjudication: (a) decide whether a definition-site freeze is required "
            "alongside conclusion-statement freeze, and if so assign it; (b) commission an independent executor "
            "(not worker-068) to re-run the pinned shadow and reproduce the per-probe verdicts, and an independent "
            "reviewer to adjudicate the substitution probes as genuine class-contract violations."),
        "evidence_refs": [ref(rel_report), ref(rel_raw),
                          "artifacts/worker-068/heldout3/known_leaks/escape_m25_wcc_completeness_swap.yaml",
                          ref(rel_rule)],
        "next_falsifier": (
            "A definition-freeze measurement that catches m04/m16/m25/m29; an independent re-run that rejects any "
            "substitution probe; or an independent reviewer classifying a substitution probe as a non-leak."),
    })

    ev.append({
        "event_id": "w068-pol12-13-checkpoint", "event_type": "status", "actor": "worker-068",
        "created_at": now(), "node_id": NODE, "group_id": GROUP, "gate": GATE, "class_ids": CLASS_IDS,
        "status": "active", "hours": 0.5,
        "summary": (
            "CHECKPOINT (worker-068, FORM-POLARITY-12): valid=true, no shadow/fixture drift; arm calibration 3/3; "
            "24/27 content probes escape (12/12 substitution, 12/15 polarity); known-rejected 3/3 rejected; "
            "R-CAND-F 24/24 new and 14/14 union statement-axis catches, 0/12 control false positives; "
            "negation-only 0/12 substitution catches."),
        "evidence_refs": [ref(rel_ckpt), ref(rel_report), ref(rel_raw)],
        "next_falsifier": report["next_falsifier"],
    })

    ev.append({
        "event_id": "w068-pol12-14-complete", "event_type": "status", "actor": "worker-068",
        "created_at": now(), "node_id": NODE, "group_id": GROUP, "gate": GATE, "class_ids": CLASS_IDS,
        "status": "active", "hours": 0.6, "claims_completion": False,
        "summary": (
            "Bounded worker lifecycle complete (W068-FORM-POLARITY-12). Artifacts and events emitted; worker "
            "exits for recycling. No node completion, validation_status=passed, or gate verdict is claimed; the "
            "open items are carried by w068-pol12-12-blocker-content-gap."),
        "evidence_refs": [ref(rel_readme), ref(rel_report), ref(rel_rule)],
        "next_falsifier": "See w068-pol12-12-blocker-content-gap and report.json next_falsifier.",
    })
    return ev


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm-ckpt", default=None)
    ap.add_argument("--final", default=None)
    ap.add_argument("--global-ckpt", default=None)
    a = ap.parse_args()

    if a.confirm_ckpt:
        if not a.final:
            print("--final required with --confirm-ckpt", file=sys.stderr)
            return 2
        final_rel = str(Path(a.final).resolve().relative_to(ROOT))
        e = {
            "event_id": "w068-pol12-15-checkpoint-confirm", "event_type": "status", "actor": "worker-068",
            "created_at": now(), "node_id": NODE, "group_id": GROUP, "gate": GATE, "class_ids": CLASS_IDS,
            "status": "active", "hours": 0.6,
            "summary": (f"Post-checkpoint confirmation: global checkpoint {a.confirm_ckpt} ingested this task's "
                        f"events; worker-local final checkpoint written to {final_rel} with the full artifact hash "
                        f"set and the task event-id list."),
            "evidence_refs": [ref(final_rel), ref("artifacts/worker-068/polarity12/report.json")],
            "next_falsifier": "See w068-pol12-12-blocker-content-gap.",
        }
        if a.global_ckpt:
            e["evidence_refs"].append(a.global_ckpt)
        appended = append_events([e])
        print(json.dumps({"appended": appended}, indent=2))
        return 0

    events = build_task_events()
    appended = append_events(events)
    print(json.dumps({"appended": appended, "total_built": len(events),
                      "outbox": str(OUTBOX.relative_to(ROOT))}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
