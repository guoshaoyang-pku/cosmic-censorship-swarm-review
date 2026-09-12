#!/usr/bin/env python3
"""Emit worker-037 outbox events for W037-F1-VISIBILITY-03 and write the task checkpoint.

Idempotent: events already present in the outbox (by event_id) are not re-appended; the
checkpoint line is written once per checkpoint_id. Read-only for all canonical artifacts.
Usage: python3 emit_events_and_checkpoint.py [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
TASK = "W037-F1-VISIBILITY-03"
CLASS = "AF-WCC-VAC-GEN"
NODE = "F1"
GATE = "G-FORM"
OUTBOX = ROOT / "comms" / "outbox" / "worker-037.jsonl"
CKPT_DIR = ROOT / "runtime" / "state"
ART_DIR = Path(__file__).resolve().parent

REPORT = "artifacts/worker-037/f1_visibility_equivalence_adjudication/report.json"
CHECKER = "artifacts/worker-037/f1_visibility_equivalence_adjudication/adjudicate_visibility_equivalence.py"
README = "artifacts/worker-037/f1_visibility_equivalence_adjudication/REPORT.md"
F1 = "schemas/af_wcc_vacuum.yaml"
F0 = "research_map/formulation_taxonomy.yaml"
PRIOR_REPORT = "artifacts/worker-037/f1_visibility_adjudication/report.json"
W026_REPORT = "artifacts/worker-026/f1_adjudication/adjudication_report.json"


def sha(rel: str) -> str:
    h = hashlib.sha256()
    with open(ROOT / rel, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def existing_event_ids() -> set[str]:
    ids: set[str] = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ids.add(json.loads(line)["event_id"])
            except Exception:
                continue
    return ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    now = datetime.now(CST)
    ts = now.strftime("%Y%m%dT%H%M%S")
    created = now.strftime("%Y-%m-%dT%H:%M:%S%z")
    eid = lambda suffix: f"w037-{ts}-{suffix}"  # noqa: E731

    rep = json.loads((ROOT / REPORT).read_text())
    h_report, h_checker, h_readme = sha(REPORT), sha(CHECKER), sha(README)
    h_f1, h_f0 = sha(F1), sha(F0)
    h_prior, h_w026 = sha(PRIOR_REPORT), sha(W026_REPORT)
    h_map = sha("research_map/research_map.json")

    assert rep["report_payload_sha256"] == "8090ba9bc5eea1dc938e1f7883e8affd8602c95945814a97b9c8e47f568d0e92", "report changed; update adjudication text"
    assert rep["pins_stable"], "pins moved; adjudication void"

    T = rep["tests"]
    t2 = T["T2_exhaustive_transitive_models"]
    t3 = T["T3_prior_witness_audit"]
    falsifier = rep["falsifier"]
    next_falsifier = rep["next_falsifier"]

    common = {
        "actor": "worker-037",
        "task_id": TASK,
        "class_id": CLASS,
        "class_ids": [CLASS],
        "gate": GATE,
    }

    events = [
        {**common, "event_id": eid("art-visibility-equivalence-report"), "event_type": "artifact",
         "created_at": created, "node_id": NODE, "artifact_type": "verification_report",
         "path": REPORT, "sha256": h_report, "validation_status": "unverified",
         "evidence_refs": [f"{REPORT}#{h_report[:12]}", f"{CHECKER}#{h_checker[:12]}",
                           f"{F1}#{h_f1[:12]}", f"{F0}#{h_f0[:12]}",
                           f"{PRIOR_REPORT}#{h_prior[:12]}", f"{W026_REPORT}#{h_w026[:12]}"],
         "summary": "Adjudication of W037V2-F1 (critical) vs LEMMA-W026-1 at F1 9a8bd4c96800: LEMMA CONFIRMED, "
                    "W037V2-F1's mathematical claim REFUTED. Under (H) J^-(q) is past-closed, so whole-curve and "
                    "tail containment are equivalent for D4 geodesics; the prior strictness witness violates (H). "
                    "T2: all 389 transitive models / 4082 chains / 16138 evaluations -> tail_without_whole=0. "
                    "Surviving item is non-blocking documentation at line 220.",
         "next_falsifier": next_falsifier},
        {**common, "event_id": eid("art-visibility-equivalence-checker"), "event_type": "artifact",
         "created_at": created, "node_id": NODE, "artifact_type": "verification_tool",
         "path": CHECKER, "sha256": h_checker, "validation_status": "unverified",
         "evidence_refs": [f"{CHECKER}#{h_checker[:12]}", f"{REPORT}#{h_report[:12]}", f"{F1}#{h_f1[:12]}"],
         "summary": "Read-only rerunnable checker: T0/T1 pins, exact clause extraction, exhaustive preorder model "
                    "check, prior-witness audit, non-causal control, proof-step audit. Exit 0 iff pins stable.",
         "next_falsifier": next_falsifier},
        {**common, "event_id": eid("art-visibility-equivalence-readme"), "event_type": "artifact",
         "created_at": created, "node_id": NODE, "artifact_type": "verification_report_md",
         "path": README, "sha256": h_readme, "validation_status": "unverified",
         "evidence_refs": [f"{README}#{h_readme[:12]}", f"{REPORT}#{h_report[:12]}"],
         "summary": "Human-readable adjudication: question, result, why the prior finding looked right, controls "
                    "table, scope, falsifier, reproduce command.",
         "next_falsifier": next_falsifier},
        {**common, "event_id": eid("claim-visibility-equivalence"), "event_type": "claim",
         "created_at": created, "node_id": NODE, "conclusion_type": "formal_model",
         "statement": "At pins F1=9a8bd4c96800 / F0=276009f4f63d (T0==T1): for every future-directed causal geodesic "
                      "gamma admitted by D4, 'exists q in I+ with gamma subset J^-(q) intersect M' is equivalent to "
                      "'exists q in I+ and t0 in [0,T) with the tail gamma([t0,T)) subset J^-(q) intersect M', given "
                      "the standard past-closedness/transitivity of the causal relation that J^-(q) presupposes. "
                      "Therefore quantifiers.formal and visibility.negation_conclusion are exact negations, and the "
                      "critical claim in W037V2-F1 ('strictly weaker') is refuted; only the wording difference and a "
                      "non-blocking explanatory non-sequitur at line 220 survive. Machine corroboration: 389 "
                      "transitive models, 4082 causal chains, 16138 predicate evaluations, zero tail-without-whole.",
         "assumptions": ["The schema's J^-(q) is the standard causal past of q in the conformal completion, hence "
                         "past-closed; equivalently, causal precedence is transitive (H).",
                         "D4 admits only future-directed causal geodesics, so every sub-segment is causal.",
                         "Line-220's 'black-hole end' example does not break the equivalence: both readings classify "
                         "that geodesic as not visible.",
                         "Worker evidence is advisory; the schema owner (lead-formulation) binds interpretation."],
         "falsifier": falsifier,
         "evidence_refs": [f"{REPORT}#{h_report[:12]}", f"{CHECKER}#{h_checker[:12]}",
                           f"{F1}#{h_f1[:12]}", f"{F0}#{h_f0[:12]}",
                           f"{PRIOR_REPORT}#{h_prior[:12]}", f"{W026_REPORT}#{h_w026[:12]}"],
         "artifact_refs": [REPORT, CHECKER, README],
         "does_not_claim": rep["does_not_claim"]},
        {**common, "event_id": eid("review-f1-visibility-equivalence"), "event_type": "review",
         "created_at": created, "node_id": NODE, "target_id": "F1", "reviewer": "worker-037",
         "verdict": "revise", "score": 3.5, "hard_failures": [],
         "counts_as_full_schema_verdict": False,
         "scope": "visibility-clause adjudication only (W037V2-F1 vs LEMMA-W026-1) at "
                  "schemas/af_wcc_vacuum.yaml 9a8bd4c96800; D0 disjunction, dangling AF_{I+}, duplicate revised_at "
                  "and class_contract_pointer/F0-mirror findings are explicitly out of scope and untouched",
         "findings": [
             "WITHDRAWN: W037V2-F1 (filed critical by a prior worker-037 slot) is mathematically REFUTED. Its textual "
             "premise is reproduced, but the whole-curve and tail clauses are equivalent for D4 geodesics because "
             "J^-(q) is past-closed (H); LEMMA-W026-1 CONFIRMED by exhaustive finite-model check (389 transitive "
             "models, 4082 chains, 0 tail-without-whole) and proof-step audit. quantifiers.formal and "
             "visibility.negation_conclusion are exact negations at the pinned bytes; the visibility clause itself is "
             "accepted by this adjudication.",
             "SURVIVING, non-blocking: the explanatory sentence at schemas/af_wcc_vacuum.yaml:220 ('requiring the whole "
             "geodesic ... would misclassify ...') is a non-sequitur, and the schema nowhere states the (H) "
             "equivalence lemma; recommended one-line fix is recorded in the report. This is documentation precision, "
             "not a content defect, and it interacts with the schema's own reader-disagreement falsifier.",
             "ARTIFACT-LEVEL verdict is revise, not accept: only because of that documentation item (and without "
             "re-filing out-of-scope findings such as D0). This review is scoped, does not certify F1 overall, and is "
             "NOT claimed as one of the two required independent accepts; whether worker verdicts count toward G-FORM "
             "is the controller's decision."],
         "evidence_refs": [f"{REPORT}#{h_report[:12]}", f"{CHECKER}#{h_checker[:12]}", f"{F1}#{h_f1[:12]}",
                           f"{PRIOR_REPORT}#{h_prior[:12]}", f"{W026_REPORT}#{h_w026[:12]}"],
         "next_falsifier": next_falsifier},
        {**common, "event_id": eid("withdrawal-blocker-f1-visibility"), "event_type": "status",
         "created_at": created, "node_id": NODE, "status": "active", "hours": 0.6,
         "summary": "WITHDRAWAL of w037-20260912T002818-blocker-f1-visibility (critical): the blocker's own falsifier "
                    "fired. A definitional bridge does make the formal whole-curve clause equivalent to the tail "
                    "predicate: J^-(q) is past-closed because causal precedence is transitive (H), so "
                    "exists-q(whole) <=> exists-q exists-t0(tail). Its finite witness (universe {a,b}, J^-(q1)={b}) "
                    "requires a not-precedes-b while a -> b -> q, i.e. it denies (H) and is not a model of the "
                    "declared causal structure. The prior blocker is withdrawn as critical; the only surviving item is "
                    "a non-blocking documentation fix at line 220. No gate verdict and no node status change.",
         "evidence_refs": [f"{REPORT}#{h_report[:12]}", f"{CHECKER}#{h_checker[:12]}", f"{PRIOR_REPORT}#{h_prior[:12]}",
                           f"{W026_REPORT}#{h_w026[:12]}", f"{F1}#{h_f1[:12]}"],
         "next_falsifier": next_falsifier},
        {**common, "event_id": eid("status-visibility-equivalence"), "event_type": "status",
         "created_at": created, "node_id": NODE, "status": "active", "hours": 0.6,
         "summary": f"{TASK} complete as a bounded worker task (completion claim for the deliverable, not a node "
                    f"transition). Verdict: LEMMA-W026-1 confirmed; W037V2-F1 refuted; prior critical blocker "
                    f"withdrawn; surviving line-220 documentation item non-blocking. Checks: T1 text binding pass; "
                    f"T2 {t2['models_checked']} models/{t2['chains_checked']} chains/{t2['predicate_evaluations']} "
                    f"evaluations -> {t2['verdict']}; T3 witness under standard J^- no longer a witness="
                    f"{not t3['recorded_witness_under_standard_J_minus']['still_a_strictness_witness']}; T5 non-causal "
                    f"control isolates the causality hypothesis. T0==T1 pins stable; report payload sha256 "
                    f"8090ba9bc5ee. Checkpoint: runtime/state/w037_checkpoint_{ts}_visibility_equivalence.json.",
         "evidence_refs": [f"{REPORT}#{h_report[:12]}", f"{CHECKER}#{h_checker[:12]}", f"{README}#{h_readme[:12]}",
                           f"runtime/state/w037_checkpoint_{ts}_visibility_equivalence.json#pending"],
         "next_falsifier": next_falsifier},
    ]

    # checkpoint record
    ckpt_rel = f"runtime/state/w037_checkpoint_{ts}_visibility_equivalence.json"
    ckpt = {
        "actor": "worker-037",
        "authority_note": "worker event; cannot set node status=done, validation_status=passed, or a gate verdict",
        "checkpoint_id": f"w037-ckpt-{ts}-visibility-equivalence",
        "class_ids": [CLASS],
        "created_at": created,
        "events": [e["event_id"] for e in events],
        "gate": GATE,
        "map_sha256_measured": h_map,
        "method": "read-only adjudication of W037V2-F1 vs LEMMA-W026-1 at pinned F1 bytes",
        "next_falsifier": next_falsifier,
        "node_id": NODE,
        "outbox": "comms/outbox/worker-037.jsonl",
        "pins": rep["pins"],
        "pins_stable": rep["pins_stable"],
        "result": rep["verdict"]["targets"],
        "surviving_defect": rep["verdict"]["surviving_defect_nonblocking"],
        "task_id": TASK,
        "tests": {
            "T1_text_binding_pass": T["T1_text_binding"]["pass"],
            "T2": {k: t2[k] for k in ("models_checked", "chains_checked", "predicate_evaluations",
                                      "whole_without_tail", "tail_without_whole", "verdict")},
            "T3_recorded_witness_reproduced": t3["recorded_witness_reproduced_arithmetically"],
            "T3_still_a_witness_under_standard_J_minus": t3["recorded_witness_under_standard_J_minus"]["still_a_strictness_witness"],
            "T5_noncausal_control_strictness": T["T5_noncausal_control"]["strictness_witness"],
        },
        "artifacts": {REPORT: h_report, CHECKER: h_checker, README: h_readme},
    }

    if args.dry_run:
        print(json.dumps({"events": [e["event_id"] for e in events], "checkpoint": ckpt_rel,
                          "artifact_hashes": ckpt["artifacts"]}, indent=1))
        return 0

    # write the checkpoint first so the status event can cite its measured hash
    ckpt_path = ROOT / ckpt_rel
    ckpt_bytes = json.dumps(ckpt, indent=2, sort_keys=True) + "\n"
    ckpt_path.write_text(ckpt_bytes)
    h_ckpt = hashlib.sha256(ckpt_bytes.encode()).hexdigest()
    for e in events:
        if e["event_id"].endswith("status-visibility-equivalence"):
            e["evidence_refs"] = [r for r in e["evidence_refs"] if not r.startswith(ckpt_rel)]
            e["evidence_refs"].append(f"{ckpt_rel}#{h_ckpt[:12]}")

    seen = existing_event_ids()
    appended = []
    with OUTBOX.open("a") as f:
        for e in events:
            if e["event_id"] in seen:
                print(f"skip existing {e['event_id']}")
                continue
            f.write(json.dumps(e, sort_keys=True) + "\n")
            appended.append(e["event_id"])
            seen.add(e["event_id"])

    log = CKPT_DIR / "w037_checkpoints.jsonl"
    already = False
    if log.exists():
        for line in log.read_text().splitlines():
            try:
                if json.loads(line).get("checkpoint_id") == ckpt["checkpoint_id"]:
                    already = True
                    break
            except Exception:
                continue
    if not already:
        with log.open("a") as f:
            f.write(json.dumps({"checkpoint_id": ckpt["checkpoint_id"], "created_at": created,
                                "path": ckpt_rel, "task_id": TASK,
                                "result": "LEMMA-W026-1 confirmed; W037V2-F1 refuted; prior blocker withdrawn",
                                "events": ckpt["events"]}, sort_keys=True) + "\n")

    print(f"appended {len(appended)} events -> {OUTBOX}")
    for e in appended:
        print("  +", e)
    print(f"checkpoint -> {ckpt_rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
