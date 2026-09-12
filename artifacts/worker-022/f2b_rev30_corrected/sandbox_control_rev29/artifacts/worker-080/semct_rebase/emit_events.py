#!/usr/bin/env python3
"""Emit worker-080 W080-SEMCT-REBASE-01 events and checkpoint. Idempotent on event_id."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = REPO / "comms/outbox/worker-080.jsonl"
CKPT = REPO / "runtime/state/w080_semct_rebase_checkpoint_1.json"
CKPT_LOG = REPO / "runtime/state/w080_semct_rebase_checkpoints.jsonl"
CST = timezone(timedelta(hours=8))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def h(p: str) -> str:
    return f"{p}#{sha(REPO / p)[:12]}"


def artifact(path: str) -> dict:
    return {"path": path, "sha256": sha(REPO / path), "bytes": (REPO / path).stat().st_size}


now = datetime.now(CST).isoformat(timespec="seconds")
T = now.replace(":", "").replace("-", "").replace("+0800", "")[:15]
E = lambda s: f"w080-sr-{T}-{s}"          # noqa: E731

A = {
    "report": "artifacts/worker-080/semct_rebase/report.json",
    "raw": "artifacts/worker-080/semct_rebase/report_raw_harness.json",
    "harness": "artifacts/worker-080/semct_rebase/rebase_semct.py",
    "probe": "artifacts/worker-080/semct_rebase/r03_probe_report.json",
    "probe_py": "artifacts/worker-080/semct_rebase/r03_lexical_probe.py",
    "edits": "artifacts/worker-080/semct_rebase/control_edits.json",
    "manifest": "artifacts/worker-080/semct_rebase/manifest_rebased.json",
    "readme": "artifacts/worker-080/semct_rebase/README.md",
    "ctl_base": "artifacts/worker-080/semct_rebase/patched_controls/control_conforming_base.yaml",
    "ctl_comment": "artifacts/worker-080/semct_rebase/patched_controls/control_comment_only_composite.yaml",
    "ctl_quoted": "artifacts/worker-080/semct_rebase/patched_controls/control_quoted_forbidden_phrase.yaml",
    "r2": "artifacts/worker-080/semct_rebase/runs/R2_observed.json",
}
F0, F1, F2A, F2B = ("research_map/formulation_taxonomy.yaml", "schemas/af_wcc_vacuum.yaml",
                    "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml")
FROZEN = "artifacts/formulation/FROZEN.json"
SUITE = "schemas/semantic_contract_tests/manifest.json"
ALL_CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]

FALSIFIER = (
    "Re-run artifacts/worker-080/semct_rebase/rebase_semct.py and r03_lexical_probe.py at the "
    "pinned hashes: any run whose exit code, integrity-error count, control acceptance, mutant "
    "counts or per-test observed verdicts differ from the recorded grades falsifies the "
    "corresponding clause; input-hash drift voids the affected rows; a rebased control accepted "
    "while still carrying the duplicated transfer_failures row or revised_at_unused falsifies "
    "that edit's necessity; a rev12 semantic accept, a rewrite that still fails R03, a rewrite "
    "whose non-R03 checks change, or an absent-token mutant passing R03 falsifies the lexical "
    "false-positive conclusion."
)

events = [
    {"event_id": E("artifact-report"), "event_type": "artifact", "created_at": now, "actor": "worker-080",
     "node_id": "A1", "gate": "G-AUDIT", "class_ids": ALL_CLASSES, "artifact_type": "calibration_rebase_report",
     "path": A["report"], "sha256": sha(REPO / A["report"]), "validation_status": "unverified",
     "evidence_refs": [h(A["report"]), h(A["raw"]), h(A["r2"]), h(F1), h(F0)],
     "summary": ("Final report for the executed ADJ-CONTROL-STALENESS rebase candidate at FROZEN "
                 "rev28: raw harness grades (R0-R5, pre-registered, two R2 rows falsified by the "
                 "finding below) plus annotated root cause and owner routing; raw report preserved "
                 "as report_raw_harness.json."),
     "falsifier": FALSIFIER},
    {"event_id": E("artifact-harness"), "event_type": "artifact", "created_at": now, "actor": "worker-080",
     "node_id": "A1", "gate": "G-AUDIT", "class_ids": ALL_CLASSES, "artifact_type": "measurement_harness",
     "path": A["harness"], "sha256": sha(REPO / A["harness"]), "validation_status": "unverified",
     "evidence_refs": [h(A["harness"]), h(A["edits"]), h(A["manifest"]), h(SUITE)],
     "summary": ("Read-only staged harness: canonical runner unmodified, minimal repo subset, six "
                 "pins rebound, two text-level comment-preserving control edits (duplicate "
                 "finite_codimension_complement->residual_comeager row out of transfer_failures; "
                 "unknown revised_at_unused key removed), negative controls R3a/R3b/R4 and a "
                 "determinism re-run. No canonical path written; input hashes stable across the run."),
     "falsifier": FALSIFIER},
    {"event_id": E("artifact-patch"), "event_type": "artifact", "created_at": now, "actor": "worker-080",
     "node_id": "A1", "gate": "G-AUDIT", "class_ids": ALL_CLASSES, "artifact_type": "control_rebase_patch",
     "path": A["edits"], "sha256": sha(REPO / A["edits"]), "validation_status": "unverified",
     "evidence_refs": [h(A["edits"]), h(A["manifest"]), h(A["ctl_base"]), h(A["ctl_comment"]), h(A["ctl_quoted"]), h(A["readme"])],
     "summary": ("Ready-to-adopt candidate for ADJ-CONTROL-STALENESS: per-control exact edits with "
                 "data-model validation (only the intended removals differ), three rebased control "
                 "fixtures, and a manifest_rebased.json with all six sha256 pins updated. Owner: "
                 "astra-lead-formulation."),
     "falsifier": FALSIFIER},
    {"event_id": E("artifact-probe"), "event_type": "artifact", "created_at": now, "actor": "worker-080",
     "node_id": "F1", "gate": "G-AUDIT", "class_ids": ["AF-WCC-VAC-GEN"], "artifact_type": "checker_false_positive_probe",
     "path": A["probe"], "sha256": sha(REPO / A["probe"]), "validation_status": "unverified",
     "evidence_refs": [h(A["probe"]), h(A["probe_py"]), h(F1)],
     "summary": ("Probe B root cause of the post-rebase calibration failure: canonical F1 rev12 "
                 "(cce9c601) is rejected by both semantic stages on R03 alone ('binder (q,t0) absent "
                 "from formal sentence') while the binding structural gate passes it. rev11 and the "
                 "pre-rev11 snapshot pass the same semantic stage; a notation-only D5-relative "
                 "rewrite clears R03 with every other check unchanged; an absent-token mutant still "
                 "fails R03 - the rejection is lexical, not semantic. The runner names no "
                 "adjudication item for a rejected conforming-canonical control."),
     "falsifier": FALSIFIER},
    {"event_id": E("claim"), "event_type": "claim", "created_at": now, "actor": "worker-080",
     "node_id": "A1", "gate": "G-AUDIT", "class_id": ";".join(ALL_CLASSES),
     "conclusion_type": "numerical_evidence",
     "assumptions": [
         "the canonical runner and both stage tools are used unmodified from their pinned hashes",
         "the staged sandbox is byte-identical to the canonical inputs at the pinned hashes",
         "control fixtures may be rebased while the 32-mutant corpus stays frozen (suite README, ADJ-CONTROL-STALENESS)"],
     "statement": (
         "At FROZEN rev28 (canonical F1 cce9c60146d6a907, F2a 5476a3f2c6bc7196, F2b 55d0a1ea9bda96b8, "
         "F0 0abb9ed8a96135c9): (1) the canonical semantic-contract manifest is unexecutable, exit 2 "
         "with exactly the three stale conforming-canonical pins; (2) after rebinding only those three "
         "pins the suite runs, exits 3, frozen controls 0/3 accepted by all stages, and each control "
         "fails the structural stage on R22 AND R28 (the controls carry a duplicated "
         "finite_codimension_complement->residual_comeager row in transfer_failures and the unknown "
         "revised_at_unused key); (3) after deleting exactly those two items per control, all 3/3 "
         "frozen controls are accepted by all three stages, the mutant counts are unchanged "
         "(structural 32/32, semantic baseline 11/32, hardened 32/32, 0 adopted-stage escapes) and a "
         "fresh-sandbox re-run reproduces every per-test observed verdict; (4) each edit is necessary "
         "(R3a: key kept -> R22 fires; R3b: row kept -> R28 fires) and the gate still fires when the "
         "stale row is re-inserted (R4); (5) valid_for_calibration nevertheless remains false because "
         "conforming-canonical control SCT-K03, canonical F1 rev12, is rejected by both semantic "
         "stages on R03 alone for the literal composite binder (q,t0), a lexical false positive "
         "demonstrated by an equivalent notation-only rewrite that clears R03 with all other checks "
         "unchanged and by an absent-token mutant that still fails R03."),
     "not_claimed": ["no gate verdict", "no node status", "no canonical artifact modified",
                     "no mathematical claim about F1 or any class", "no claim that the rebased controls are the only valid resolution"],
     "falsifier": FALSIFIER,
     "evidence_refs": [h(A["report"]), h(A["raw"]), h(A["r2"]), h(A["probe"]), h(A["edits"]), h(F1), h(F0), h(FROZEN)],
     "artifact_refs": [A["report"], A["harness"], A["probe"], A["edits"], A["manifest"]]},
    {"event_id": E("blocker-f1r03"), "event_type": "blocker", "created_at": now, "actor": "worker-080",
     "node_id": "A1,F1", "gate": "G-AUDIT", "class_ids": ["AF-WCC-VAC-GEN"],
     "description": (
         "After the ADJ-CONTROL-STALENESS rebase the semantic-contract suite is still not "
         "calibration-valid at FROZEN rev28: SCT-K03 (canonical F1 rev12 cce9c601) is rejected by "
         "both semantic stages on R03 because the composite binder token (q,t0) does not occur "
         "literally in quantifiers.formal, which spells the pair out as 'q in I+ and t0 in [0,T)'. "
         "Probe B shows this is lexical, not semantic (rev11/pre accepted; equivalent D5-relative "
         "rewrite clears R03 with all other checks unchanged; absent-token mutant still fails R03), "
         "and the binding structural gate passes F1 rev12. The runner's validity.blocking_adjudication "
         "list is empty for a rejected conforming-canonical control, so the failure is not routed."),
     "needed_to_unblock": (
         "(1) lead-audit / suite owner adjudicate R03 as a lexical false positive and either make the "
         "binder check resolution-aware (composite binder whose components occur in formal, or resolve "
         "through quantifiers.domains[d].definition) or record the adjudication; per CF-4 do not edit "
         "F1's formal sentence to satisfy a lexical check. (2) extend the runner's "
         "blocking_adjudication to name rejected conforming-canonical controls. (3) astra-lead-formulation "
         "adopts or rejects the ADJ-CONTROL-STALENESS patch in artifacts/worker-080/semct_rebase/."),
     "evidence_refs": [h(A["probe"]), h(A["report"]), h(F1)],
     "falsifier": ("A rev12 semantic accept, or an R03 check that passes the absent-token mutant, or a "
                   "rev12 semantic reject with a non-R03 failed rule falsifies this blocker's lexical "
                   "classification; a suite run at rev28 with valid_for_calibration=true falsifies the "
                   "blocker itself.")},
    {"event_id": E("status-final"), "event_type": "status", "created_at": now, "actor": "worker-080",
     "node_id": "A1", "gate": "G-AUDIT", "class_ids": ALL_CLASSES, "status": "active", "hours": 1.0,
     "summary": (
         "W080-SEMCT-REBASE-01 complete from the worker side: one bounded class-bound task, read-only "
         "on canonical paths. ADJ-CONTROL-STALENESS is mechanically resolvable - three pin rebinds + "
         "two minimal control edits give 3/3 frozen controls accepted by all three stages with the "
         "mutant corpus untouched and a deterministic re-run; necessity and non-weakening shown by "
         "R3a/R3b/R4. The rebase exposes a new, independent blocker: canonical F1 rev12 fails the "
         "worker semantic auditor on R03 only, a lexical false positive demonstrated by probe B, and "
         "the runner routes no adjudication item for it. Artifacts + reports + checkpoint on disk with "
         "measured hashes; no gate verdict and no node completion claimed."),
     "evidence_refs": [h(A["report"]), h(A["probe"]), h(A["harness"]), h(A["edits"]), h(A["manifest"]), h(F1), h(F0), h(FROZEN)],
     "next_falsifier": FALSIFIER},
]

OUT.parent.mkdir(parents=True, exist_ok=True)
existing = set()
if OUT.exists():
    for line in OUT.read_text().splitlines():
        try:
            existing.add(json.loads(line).get("event_id"))
        except Exception:
            pass
new = [e for e in events if e["event_id"] not in existing]
with OUT.open("a") as f:
    for e in new:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")

ckpt = {
    "worker": "worker-080",
    "task_id": "W080-SEMCT-REBASE-01",
    "checkpoint_at": now,
    "status": "COMPLETE",
    "node_id": "A1",
    "class_ids": ALL_CLASSES,
    "gate": "G-AUDIT",
    "verdict": "CANDIDATE_PATCH_MEASURED / NEW_BLOCKER_FOUND",
    "pins": {p: sha(REPO / p) for p in (F0, F1, F2A, F2B, FROZEN, SUITE)},
    "measurements": {
        "R0_canonical_manifest": "exit 2, 3 stale pins",
        "R1_pins_rebound_only": "exit 3, controls 0/3, mutants 32/11/32",
        "R2_pins_rebound_and_controls_rebased": "exit 3, controls 3/3, mutants 32/11/32, valid false (F1 R03)",
        "R3a_key_kept_row_removed": "exit 3, R22 on controls",
        "R3b_row_kept_key_removed": "exit 3, R28 on controls",
        "R4_stale_row_reinserted": "exit 3, R28 on controls",
        "R5_determinism_rerun_of_R2": "identical per-test verdicts to R2",
        "probeB": "rev12 reject:R03; rev11/pre accept; rewrite accept with all other checks unchanged; absent-token mutant reject:R03",
    },
    "adjudication_question_answered": "ADJ-CONTROL-STALENESS: yes (3/3 controls after 2 edits; necessity + non-weakening controlled)",
    "remaining_blocker": "canonical F1 rev12 R03 lexical false positive + runner blocking_adjudication gap for conforming-canonical controls",
    "events_emitted": [e["event_id"] for e in new],
    "artifacts": {p: sha(REPO / p) for p in A.values()},
    "canonical_paths_written": [],
}
CKPT.write_text(json.dumps(ckpt, indent=1) + "\n")
with CKPT_LOG.open("a") as f:
    f.write(json.dumps(ckpt, ensure_ascii=False) + "\n")
print(json.dumps({"appended_events": [e["event_id"] for e in new],
                  "checkpoint": str(CKPT.relative_to(REPO)),
                  "checkpoint_sha256": sha(CKPT)[:16]}, indent=1))
