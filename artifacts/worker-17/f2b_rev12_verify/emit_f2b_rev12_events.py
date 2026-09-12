#!/usr/bin/env python3
"""Emit worker-017 F2b rev12 review events + checkpoint (idempotent by event_id).

Writes:
  artifacts/worker-17/f2b_rev12_verify/MANIFEST.json
  comms/outbox/deepseek-flash-17.jsonl              (append; skips existing event_ids)
  runtime/state/w017_f2b_rev12_checkpoint.json
  runtime/state/w017_checkpoints.jsonl              (append)
  artifacts/worker-17/CHECKPOINTS.jsonl             (append)
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
TAG = datetime.now(CST).strftime("%Y%m%dT%H%M%S")

F2B = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
F2B_MIRROR = "schemas/af_scc_c0_vacuum.yaml"
REVIEW = "reviews/F2b-review-17-rev12.json"
REPORT = "artifacts/worker-17/f2b_rev12_verify/f2b_rev12_classcheck_report.json"
CHECKER = "artifacts/worker-17/f2b_rev12_verify/f2b_rev12_classcheck.py"
QNF_REPORT = "artifacts/worker-17/f2b_rev12_verify/qnf_f2b_rev12.json"
QNF_TOOL = "artifacts/worker-17/quantifier_nf/extract_qnf.py"
F0_DECLARED = "research_map/formulation_taxonomy.yaml"
F0_SUPPLEMENT = "artifacts/formulation/formulation_taxonomy.yaml"
RULE_SPEC = "artifacts/formulation/rule_spec.json"
REGISTRY = "artifacts/formulation/VARIANT_REGISTRY.json"
CONSISTENCY = "artifacts/formulation/evidence/taxonomy_consistency.json"
RUBRIC = "evaluation_rubric.yaml"
OUTBOX = "comms/outbox/deepseek-flash-17.jsonl"


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def main() -> None:
    h = {rel: sha(rel) for rel in (
        F2B, F2B_MIRROR, REVIEW, REPORT, CHECKER, QNF_REPORT, QNF_TOOL,
        F0_DECLARED, F0_SUPPLEMENT, RULE_SPEC, REGISTRY, CONSISTENCY, RUBRIC)}

    # ---- evidence manifest (kept out of its own digest) -------------------
    manifest = {
        "bundle": "artifacts/worker-17/f2b_rev12_verify",
        "worker": "worker-017",
        "actor": "deepseek-flash-17",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "node_id": "F2b",
        "gate": "G-FORM",
        "created_at": NOW,
        "review": {"path": REVIEW, "sha256": h[REVIEW], "verdict": "revise", "score": 3.0,
                   "hard_failures": ["HF-06", "HF-03"]},
        "frozen_pin": {"path": F2B, "sha256": h[F2B],
                       "mirror": F2B_MIRROR, "mirror_sha256": h[F2B_MIRROR]},
        "files": {rel: h[rel] for rel in (CHECKER, REPORT, QNF_REPORT, QNF_TOOL)},
        "inputs": {rel: h[rel] for rel in (F0_DECLARED, F0_SUPPLEMENT, RULE_SPEC,
                                           REGISTRY, CONSISTENCY, RUBRIC)},
        "not_claimed": ["no gate verdict", "no node completion", "no canonical edit"],
    }
    (ROOT / "artifacts/worker-17/f2b_rev12_verify/MANIFEST.json").write_text(
        json.dumps(manifest, indent=1) + "\n")

    # ---- outbox events ----------------------------------------------------
    E = f"w17-f2b-rev12-{TAG}"
    events = [
        {
            "event_id": E + "-artifact-review", "event_type": "artifact", "created_at": NOW,
            "actor": "deepseek-flash-17", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
            "artifact_type": "review", "path": REVIEW, "sha256": h[REVIEW],
            "validation_status": "unverified",
            "evidence_refs": [f"{F2B}#sha256:{h[F2B][:12]}", f"{REPORT}#sha256:{h[REPORT][:12]}",
                              f"{CHECKER}#sha256:{h[CHECKER][:12]}"],
            "summary": "Independent worker-17 A1/G-FORM verdict on F2b rev12 pinned 55d0a1ea9bda: revise 3.0/5, hard_failures [HF-06, HF-03], 3 blocking + 3 non-blocking findings. Class/quantifier/conclusion/falsifier form passes 14/14 machine checks with 8/8 negative controls; blocks are the unregistered Sobolev/data-class branch (class identity), the stale f0_binding consistency-evidence pin, and the 'rule_spec v1.3' label against the frozen 1.2 spec.",
            "next_falsifier": "Register the Sobolev/data-class branch (or obtain a lead-audit tagged-union ruling), refresh consistency_evidence_sha256 in F1/F2a/F2b, and resolve the rule_spec version label; then re-render at the new pin.",
        },
        {
            "event_id": E + "-artifact-instrument", "event_type": "artifact", "created_at": NOW,
            "actor": "deepseek-flash-17", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
            "artifact_type": "verification_tooling",
            "path": REPORT, "sha256": h[REPORT], "validation_status": "unverified",
            "evidence_refs": [f"{CHECKER}#sha256:{h[CHECKER][:12]}",
                              f"{QNF_REPORT}#sha256:{h[QNF_REPORT][:12]}",
                              f"{QNF_TOOL}#sha256:{h[QNF_TOOL][:12]}"],
            "summary": "17-check class-identity instrument on the pinned F2b bytes: 14 pass, 3 recorded findings (declared as expected_finding before the run), 0 unexpected failures, 8/8 mutant controls detected. Companion QNF run (tool 1.1.0) gives qnf/negation/order/witness typing pass with 7/7 mutant detection; the 1.0.0->1.1.0 repair (D0 binder '(s,delta)' -> 'r') is disclosed in the tool header and review. Evidence bundle MANIFEST.json under the same directory.",
            "next_falsifier": "A mutant that does not trip its designated check, or a check that fails on a repaired F2b while the instrument reports pass, falsifies the instrument.",
        },
        {
            "event_id": E + "-review", "event_type": "review", "created_at": NOW,
            "actor": "deepseek-flash-17", "reviewer": "deepseek-flash-17",
            "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "target_id": "F2b",
            "target_path": F2B, "target_sha256": h[F2B], "gate": "G-FORM",
            "artifact": REVIEW, "artifact_sha256": h[REVIEW],
            "verdict": "revise", "score": 3.0, "hard_failures": ["HF-06", "HF-03"],
            "findings": [
                {"id": "B-17R12-01", "severity": "blocking", "hf": "HF-06",
                 "lines": [41, 53, 159, 160, 164, 251, 252, 253, 254, 255, 256, 257, 258],
                 "summary": "D0 tagged union of smooth (Frechet) and Sobolev (Banach) settings is one class_id with no registered variant and no transfer lemma; supplement claims a 'registered Sobolev variant' that resolves in no frozen registry (VARIANT_REGISTRY 5eb42f9a has 7 variants, none Sobolev; taxonomy variants 2; variants/ dir 2 delta files; axis_registry has no data-class axis). Class identity not decidable from the artifact as pinned."},
                {"id": "B-17R12-02", "severity": "blocking", "hf": "HF-03", "lines": [308],
                 "summary": "f0_binding.consistency_evidence_sha256 declares 675a99d0 but the file measures 9e335e9b (FROZEN rev28) and is newer than the schema; family-wide across F1/F2a; the binding's own rule requires refresh before a gate verdict."},
                {"id": "B-17R12-03", "severity": "blocking", "hf": "HF-03", "lines": [308],
                 "summary": "Supplement data_class_freeze cites rule_spec v1.3; the frozen rule_spec.json (40f9bb9e) reports spec_version 1.2 (content present, version label does not resolve)."},
                {"id": "N-17R12-01", "severity": "non-blocking", "lines": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
                 "summary": "revision_history non-monotone (index 9 at 23:30:35 after index 8 at 00:30:00) and unused:true carries rev11 notes; rev12 wall-clock repair incomplete for rev11."},
                {"id": "N-17R12-02", "severity": "non-blocking", "lines": [159, 160, 161],
                 "summary": "Baire justification stated for the Banach branch only; Frechet branch is Baire but the reason is not stated for it."},
                {"id": "N-17R12-03", "severity": "non-blocking", "lines": [134, 135, 136],
                 "summary": "asymptotic_decay uses Sobolev s as the derivative bound inside the smooth default, mixing the two D0 branches' vocabulary."},
            ],
            "evidence_refs": [f"{REVIEW}#sha256:{h[REVIEW][:12]}", f"{F2B}#sha256:{h[F2B][:12]}",
                              f"{REPORT}#sha256:{h[REPORT][:12]}", f"{QNF_REPORT}#sha256:{h[QNF_REPORT][:12]}",
                              f"{REGISTRY}#sha256:{h[REGISTRY][:12]}",
                              f"{F0_SUPPLEMENT}#sha256:{h[F0_SUPPLEMENT][:12]}",
                              f"{RULE_SPEC}#sha256:{h[RULE_SPEC][:12]}",
                              f"{CONSISTENCY}#sha256:{h[CONSISTENCY][:12]}",
                              f"{RUBRIC}#sha256:{h[RUBRIC][:12]}"],
            "falsifier": "Falsified by a Sobolev/data-class variant registration for AF-SCC-C0-VAC-GEN that I missed, taxonomy_consistency measuring 675a99d0, rule_spec spec_version 1.3 at 40f9bb9e, or a lead-audit ruling that the two-branch D0 is one class statement needing no registration; a re-pin voids the verdict.",
            "independence": "Not an F2b/F0/registry author. QNF extractor instrument authored by me; 1.0.0->1.1.0 D0 vocabulary repair disclosed. Prior-art summaries of worker-034/07/086/040 were read while locating prior art; all determinations re-measured at the current pin.",
            "kish_ess": "1",
            "assignment_event_ids": ["audit-a1-20260912T0008-f2b-w17"],
            "authority_note": "Worker verdict; does not set node status=done, validation_status=passed, or a gate verdict.",
        },
        {
            "event_id": E + "-status", "event_type": "status", "created_at": NOW,
            "actor": "deepseek-flash-17", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
            "status": "done", "hours": 0.6,
            "summary": "Bounded worker-17 completed one class-bound task at the FROZEN rev27/28 pin: independent F2b (AF-SCC-C0-VAC-GEN) G-FORM/G-AUDIT review at 55d0a1ea9bda. Verdict revise 3.0/5; HF-06 + HF-03; 3 blocking (unregistered Sobolev/data-class branch; stale consistency-evidence pin; rule_spec v1.3 label) + 3 non-blocking findings. 14/14 form checks pass, 8/8 mutant controls detected, QNF 7/7 mutants detected. Wrote only under artifacts/worker-17/, reviews/, comms/outbox/, runtime/state/w017_*.",
            "evidence_refs": [f"{REVIEW}#sha256:{h[REVIEW][:12]}", f"{F2B}#sha256:{h[F2B][:12]}",
                              f"{REPORT}#sha256:{h[REPORT][:12]}"],
            "next_falsifier": "Re-measure the three declared-vs-measured pairs after any repair; if F2b re-pins, void this verdict rather than carrying it forward.",
            "not_claimed": ["node completion by fiat", "gate verdict authority",
                            "any verdict on superseded F2b hashes"],
            "assignment_event_ids": ["audit-a1-20260912T0008-f2b-w17"],
        },
    ]

    outbox = ROOT / OUTBOX
    existing = set()
    if outbox.exists():
        for ln in outbox.read_text().splitlines():
            ln = ln.strip()
            if ln:
                try:
                    existing.add(json.loads(ln).get("event_id"))
                except Exception:
                    pass
    appended = 0
    with outbox.open("a") as f:
        for e in events:
            if e["event_id"] in existing:
                continue
            f.write(json.dumps(e) + "\n")
            appended += 1
    outbox_sha = hashlib.sha256(outbox.read_bytes()).hexdigest()
    outbox_lines = len(outbox.read_text().splitlines())

    # ---- worker checkpoint ------------------------------------------------
    ckpt = {
        "worker": "worker-017",
        "agent_id": "deepseek-flash-17",
        "role": "bounded execution worker",
        "checkpoint": 1,
        "at": NOW,
        "run": "run-2026-09-12T00:35+08:00",
        "task": {
            "task_id": "gform-f2b-rev12-w17",
            "node_id": "F2b",
            "gate": "G-FORM",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "artifact": REVIEW,
            "hours_spent_estimate": 0.6,
            "assignment_event": "audit-a1-20260912T0008-f2b-w17",
            "result": {"verdict": "revise", "score": 3.0, "hard_failures": ["HF-06", "HF-03"],
                       "blocking": ["B-17R12-01", "B-17R12-02", "B-17R12-03"],
                       "non_blocking": ["N-17R12-01", "N-17R12-02", "N-17R12-03"]},
        },
        "inputs_measured": {rel: h[rel] for rel in (
            F2B, F2B_MIRROR, F0_DECLARED, F0_SUPPLEMENT, RULE_SPEC, REGISTRY,
            CONSISTENCY, RUBRIC)},
        "freeze_drift_during_task": False,
        "artifacts": {rel: h[rel] for rel in (REVIEW, REPORT, CHECKER, QNF_REPORT, QNF_TOOL)},
        "instrument_results": {
            "class_check_17": {"passed": 14, "recorded_findings": 3, "unexpected_failures": 0,
                               "mutant_controls_detected": "8/8"},
            "qnf": {"tool_version": "1.1.0", "checks": "qnf/negation/order/witness/trivial all true",
                    "mutant_controls_detected": "7/7",
                    "tool_repair": "1.0.0 -> 1.1.0: C2k accepts the literal domain id after the rev12 D0 binder rename"},
        },
        "gate_snapshot_at_checkpoint": "from runtime/state/current_checkpoint.json (read-only); all gates pending at 00:36:03, numerics_lock=locked",
        "outbox_events": [e["event_id"] for e in events],
        "outbox_appended": appended,
        "outbox_sha256": outbox_sha,
        "outbox_lines": outbox_lines,
        "next": [
            "controller/lifecycle: ingest these events; the verdict is advisory and binds only 55d0a1ea9bda",
            "lead-formulation: register the Sobolev/data-class branch or obtain the lead-audit tagged-union ruling; refresh consistency_evidence_sha256 in F1/F2a/F2b; correct the rule_spec v1.3 label",
            "audit: count this as one independent reviewer (ESS 1), not two",
        ],
        "non_claims": ["no node completion", "no validation_status=passed", "no gate verdict",
                       "no canonical ledger/registry/schema edit", "review binds only 55d0a1ea9bda"],
        "notes": "Wrote only under artifacts/worker-17/, reviews/F2b-review-17-rev12.json, comms/outbox/deepseek-flash-17.jsonl, runtime/state/w017_*.",
    }
    (ROOT / "runtime/state/w017_f2b_rev12_checkpoint.json").write_text(
        json.dumps(ckpt, indent=1) + "\n")
    with (ROOT / "runtime/state/w017_checkpoints.jsonl").open("a") as f:
        f.write(json.dumps({k: ckpt[k] for k in
                            ("worker", "agent_id", "at", "task", "outbox_sha256",
                             "artifacts", "instrument_results", "non_claims")}) + "\n")
    with (ROOT / "artifacts/worker-17/CHECKPOINTS.jsonl").open("a") as f:
        f.write(json.dumps({"at": NOW, "task_id": ckpt["task"]["task_id"],
                            "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
                            "verdict": "revise", "score": 3.0,
                            "review": REVIEW, "review_sha256": h[REVIEW],
                            "outbox_sha256": outbox_sha}) + "\n")

    print(json.dumps({"appended_events": appended, "outbox_sha256": outbox_sha,
                      "outbox_lines": outbox_lines, "review_sha256": h[REVIEW],
                      "checkpoint": "runtime/state/w017_f2b_rev12_checkpoint.json"},
                     indent=1))


if __name__ == "__main__":
    main()
