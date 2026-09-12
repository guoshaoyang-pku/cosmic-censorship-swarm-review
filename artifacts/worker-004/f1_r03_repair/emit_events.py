#!/usr/bin/env python3
"""Emit W004-F1-R03-REPAIR-01 events + checkpoint (idempotent by event_id).

Writes:
  runtime/state/w04_checkpoint_f1_r03_repair.json      (checkpoint record)
  runtime/state/w04_checkpoints.jsonl                  (append one line)
  comms/outbox/worker-004.jsonl                        (append events, skip existing ids)

No canonical artifact is written; the map is not touched.  Validates every event with
research_map.schemas.validate_event before writing (fails closed).

Usage: python3 artifacts/worker-004/f1_r03_repair/emit_events.py [--stamp YYYYMMDDTHHMMSS]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "research_map"))
from schemas import validate_event, SchemaError  # noqa: E402

CST = timezone(timedelta(hours=8))
OUTBOX = REPO / "comms" / "outbox" / "worker-004.jsonl"
CKPT = REPO / "runtime" / "state" / "w04_checkpoint_f1_r03_repair.json"
CKPT_LOG = REPO / "runtime" / "state" / "w04_checkpoints.jsonl"

ARTIFACTS = {
    "report": "artifacts/worker-004/f1_r03_repair/r03_repair_report.json",
    "harness": "artifacts/worker-004/f1_r03_repair/verify_r03_repair.py",
    "patched_auditor": "artifacts/worker-004/f1_r03_repair/patched/spec_conformance_audit.py",
    "patch": "artifacts/worker-004/f1_r03_repair/patched/r03_binder_token_aware.patch",
    "readme": "artifacts/worker-004/f1_r03_repair/README.md",
}
PINS = {
    "f1": ("schemas/af_wcc_vacuum.yaml",
           "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"),
    "c2": ("schemas/af_scc_c2_vacuum.yaml",
           "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce"),
    "c0": ("schemas/af_scc_c0_vacuum.yaml",
           "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"),
    "auditor": ("artifacts/worker-06/spec_conformance_audit.py",
                "c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec"),
}


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref(rel: str) -> str:
    return f"{rel}#{sha(REPO / rel)[:12]}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stamp", default=datetime.now(CST).strftime("%Y%m%dT%H%M%S"))
    a = ap.parse_args()
    now = datetime.now(CST).isoformat(timespec="seconds")

    for rel in list(ARTIFACTS.values()):
        if not (REPO / rel).is_file():
            print(f"FATAL: artifact missing {rel}", file=sys.stderr)
            return 2
    for rel, want in PINS.values():
        if sha(REPO / rel) != want:
            print(f"FATAL: pin drift {rel}", file=sys.stderr)
            return 2

    art = {k: sha(REPO / v) for k, v in ARTIFACTS.items()}
    rep = json.loads((REPO / ARTIFACTS["report"]).read_text())
    exp = rep["expectations"]
    if not all(exp.values()):
        print(f"FATAL: report has unmet expectations: {[k for k, v in exp.items() if not v]}",
              file=sys.stderr)
        return 2
    runs = rep["suite_runs"]
    patched = runs["patched_rebased_live"]
    unpatched = runs["unpatched_rebased_live"]
    stale = runs["patched_stale_live"]

    # ---- checkpoint (written before events so its hash can be cited) ----
    ckpt = {
        "checkpoint_id": "w04-cp17-f1-r03-repair",
        "created_at": now,
        "worker": "worker-004",
        "slot": "004",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "node_id": "F1",
        "gate": "G-FORM / G-AUDIT (calibration evidence routing)",
        "assignment": ("W004-F1-R03-REPAIR-01 (self-selected from the live queue; no inbox card "
                       "for worker-004 at 2026-09-12T00:45+08:00)"),
        "task": ("adjudicate the stage-2 R03 rejection of schemas/af_wcc_vacuum.yaml#cce9c60146d6 "
                 "and verify a minimal repair of the rule in artifact-local shadows"),
        "hours_spent_estimate": 1.2,
        "status": {
            "delivered": True,
            "validation_status": "unverified",
            "adjudication": rep["adjudication"]["conclusion"],
            "unpatched": {"exit": unpatched["exit"],
                          "valid_for_calibration": unpatched["validity"]["valid_for_calibration"],
                          "semantic_sha256": unpatched["stage_hashes"]["semantic"],
                          "f1_rejected_by": unpatched["rows"]["SCT-K03"]["rejected_by"]},
            "patched": {"exit": patched["exit"],
                        "valid_for_calibration": patched["validity"]["valid_for_calibration"],
                        "semantic_sha256": patched["stage_hashes"]["semantic"],
                        "controls_accepted_both_stages": patched["summary"]["controls_accepted_both_stages"],
                        "canonical_accepted_both_stages": patched["summary"]["conforming_canonical_accepted_both_stages"],
                        "mutants": [patched["summary"]["structural_caught"],
                                    patched["summary"]["semantic_baseline_caught"],
                                    patched["summary"]["semantic_hardened_caught"]],
                        "escaped_adopted_stages": patched["summary"]["escaped_adopted_stages"]},
            "negative_control_stale_controls": {
                "exit": stale["exit"],
                "valid_for_calibration": stale["validity"]["valid_for_calibration"],
                "controls_rejected_by": {t: stale["rows"][t]["rejected_by"] for t in
                                         ("SCT-C01", "SCT-C02", "SCT-C03")}},
            "no_completion_claim": ("worker cannot set done/passed or a gate verdict; no canonical "
                                    "file written; repair is a proposal for the declared owners"),
        },
        "artifacts": {v: art[k] for k, v in ARTIFACTS.items()},
        "events_emitted": "comms/outbox/worker-004.jsonl entries with event_id prefix w004-f1r03-",
        "next_falsifier": rep["adjudication"]["conclusion"] and (
            "Any of: a stage-2 accept at F1#cce9c60146d6 with the unpatched auditor; a patched-auditor "
            "accept on M-A..M-F; a rule-verdict change outside F1/R03; mutant counts != 32/11/32; a "
            "valid=false suite run at the pinned bytes under the patch; or any byte change to a "
            "canonical path. Re-run verify_r03_repair.py: it fails closed on input-hash drift."),
    }
    CKPT.write_text(json.dumps(ckpt, indent=1) + "\n")
    ckpt_sha = sha(CKPT)
    with CKPT_LOG.open("a") as f:
        f.write(json.dumps({
            "checkpoint_id": ckpt["checkpoint_id"], "created_at": now, "actor": "worker-004",
            "path": "runtime/state/w04_checkpoint_f1_r03_repair.json", "sha256": ckpt_sha,
            "workers": "F1/AF-WCC-VAC-GEN/G-FORM",
            "headline": ("R03 at F1#cce9c60146d6 adjudicated as a lexical false positive; minimal "
                         "token-aware rule repair verified: suite exit 0 / valid true, controls 3/3, "
                         "canonical 3/3, mutants 32/11/32 unchanged"),
            "next_falsifier": ckpt["next_falsifier"],
        }) + "\n")

    base = f"w004-f1r03-{a.stamp}"
    E = []

    def ev(eid_suffix, etype, **fields):
        e = {"event_id": f"{base}-{eid_suffix}", "event_type": etype, "created_at": now,
             "actor": "worker-004", "class_id": "AF-WCC-VAC-GEN", "node_id": "F1",
             "runtime_instance": f"worker-004-{a.stamp}"}
        e.update(fields)
        E.append(e)

    falsifier = (
        "Any of: a stage-2 accept of schemas/af_wcc_vacuum.yaml#cce9c60146d6 by the unpatched "
        "auditor c79d8ab8440a; a patched-auditor accept on M-A..M-F (absent identifier / missing "
        "clause / extra composite component); a rule-verdict change outside F1/R03 in the "
        "before/after rule vector; suite mutant counts != structural 32 / baseline 11 / hardened 32; "
        "a valid_for_calibration=false run at the pinned bytes under the patch; or any byte change "
        "to a canonical input. Re-run artifacts/worker-004/f1_r03_repair/verify_r03_repair.py: it "
        "fails closed (exit 2) on pin drift.")

    ev("artifact-report", "artifact", artifact_type="r03_repair_report",
       path=ARTIFACTS["report"], sha256=art["report"], validation_status="unverified",
       evidence_refs=[ref(ARTIFACTS["report"]), ref(ARTIFACTS["harness"]),
                      ref(ARTIFACTS["patched_auditor"]), PINS["f1"][0] + "#" + PINS["f1"][1][:12],
                      PINS["auditor"][0] + "#" + PINS["auditor"][1][:12]],
       summary=("Machine report: pinned adjudication, patched-auditor byte diff + selftest "
                "battery, rule-level controls M-A..M-G, per-rule before/after vectors, four shadow "
                "suite runs. " + rep["adjudication"]["conclusion"]),
       falsifier=falsifier)

    ev("artifact-harness", "artifact", artifact_type="verification_harness",
       path=ARTIFACTS["harness"], sha256=art["harness"], validation_status="unverified",
       evidence_refs=[ref(ARTIFACTS["harness"]), ref(ARTIFACTS["report"])],
       summary=("Deterministic read-only harness: pins 16 inputs by sha256 and fails closed; "
                "reproduces R03, builds the patched auditor in an artifact-local copy, runs the "
                "rule battery and the shadow semantic-contract suite. Writes only under its own "
                "artifact dir."),
       falsifier="Run it twice: any difference in the report's measurement fields, or a run that "
                 "writes a canonical path, falsifies determinism/read-only claims.")

    ev("artifact-patched-auditor", "artifact", artifact_type="patched_semantic_auditor",
       path=ARTIFACTS["patched_auditor"], sha256=art["patched_auditor"], validation_status="unverified",
       evidence_refs=[ref(ARTIFACTS["patched_auditor"]), ref(ARTIFACTS["patch"]),
                      PINS["auditor"][0] + "#" + PINS["auditor"][1][:12]],
       summary=("Repair proposal for the R03 binder check (owner: worker-06 / astra-lead-audit): "
                "composite binders are checked component-wise as whole-word identifiers instead of "
                "by literal tuple token. One hunk; selftest battery identical to the original "
                "(32 fixtures, baseline 11 caught/21 missed, hardened 32/0, positive controls 3/3)."),
       falsifier="Any file byte outside the one hunk, or a selftest result differing from the "
                 "unpatched tool, falsifies the patch record.")

    ev("artifact-patch", "artifact", artifact_type="unified_diff",
       path=ARTIFACTS["patch"], sha256=art["patch"], validation_status="unverified",
       evidence_refs=[ref(ARTIFACTS["patch"]), PINS["auditor"][0] + "#" + PINS["auditor"][1][:12]],
       summary="1-hunk unified diff c79d8ab8440a -> 645eb16a0060 for artifacts/worker-06/spec_conformance_audit.py.",
       falsifier="Applying the diff to the pinned source does not yield the pinned patched hash, "
                 "or yields more than one hunk, falsifies the diff.")

    ev("artifact-readme", "artifact", artifact_type="evidence_bundle_readme",
       path=ARTIFACTS["readme"], sha256=art["readme"], validation_status="unverified",
       evidence_refs=[ref(ARTIFACTS["readme"]), ref(ARTIFACTS["report"])],
       summary="Human-readable bundle summary, measured tables, boundaries, recommendation and next falsifiers.",
       falsifier="A README claim not backed by r03_repair_report.json is a documentation defect.")

    ev("claim", "claim", conclusion_type="formal_model",
       statement=(
           "At the pinned bytes (F1 schemas/af_wcc_vacuum.yaml#cce9c60146d6, C2 5476a3f2c6bc, "
           "C0 55d0a1ea9bda, auditor c79d8ab8440a, structural 000e09e46b2f, rule_spec 40f9bb9e657b), "
           "the stage-2 R03 rejection of F1 ('binder (q,t0) absent from formal sentence') is a "
           "literal-token false positive: all six ordered quantifiers are present in "
           "quantifiers.formal in the declared kind order, and every identifier component of every "
           "binder (including q and t0) occurs in the formal sentence as a whole word. A one-hunk "
           "repair that checks composite binders component-wise (patched auditor 645eb16a0060) "
           "flips exactly F1/R03 in the per-rule vector (18 rules compared; no other rule changes; "
           "C2/C0 unchanged), keeps the auditor's own selftest battery identical, and in "
           "artifact-local shadow runs of the semantic-contract suite with the live canonical "
           "schemas and rebased controls turns exit 3 / valid_for_calibration=false (F1 rejected "
           "by both semantic stages) into exit 0 / valid_for_calibration=true with controls 3/3, "
           "canonical 3/3 and mutant counts unchanged (structural 32, baseline 11, hardened 32, "
           "0 adopted-stage escapes); a rerun is byte-identical on the measured fields. Under the "
           "patched auditor the original stale controls are still rejected by the structural stage "
           "(R28), and true-defect mutants (absent identifier, missing clause, extra composite "
           "component) are still rejected on R03."),
       assumptions=[
           "the shadow suite's union allowlist (rev27 U rev28, 272 keys) is a harness-only input "
           "used to hold the structural stage fixed; it is not proposed as a canonical artifact",
           "the rebased controls are byte snapshots from worker-004 W004-SEMCT-CONTROL-REBASE-02",
           "live canonical schemas are pinned at their measured bytes for the duration of the run; "
           "any write voids the measurement",
           "the semantic-contract suite is calibration evidence, not a gate; final rule adoption "
           "belongs to the auditor owner and lead-audit",
       ],
       evidence_refs=[ref(ARTIFACTS["report"]), ref(ARTIFACTS["patched_auditor"]),
                      ref(ARTIFACTS["harness"]),
                      PINS["f1"][0] + "#" + PINS["f1"][1][:12],
                      PINS["auditor"][0] + "#" + PINS["auditor"][1][:12],
                      "schemas/semantic_contract_tests/manifest.json#b2e8bd17892b"],
       artifact_refs=[ref(ARTIFACTS["report"]), ref(ARTIFACTS["patched_auditor"]),
                      ref(ARTIFACTS["patch"])],
       falsifier=falsifier)

    ev("review", "review", target_id="artifacts/worker-06/spec_conformance_audit.py",
       reviewer="worker-004", verdict="revise", score=3.5,
       artifact=PINS["auditor"][0], artifact_sha256=PINS["auditor"][1],
       authority_note=("advisory worker verdict bound to the measured tool hash; workers cannot set "
                       "a gate verdict or node status"),
       hard_failures=[{
           "id": "R03-LITERAL-COMPOSITE", "status": "open", "severity": "major",
           "detail": ("R03's binder check is a literal substring test; the F1 formal sentence spells "
                      "the final not-exists binder as 'q in I+ and t0 in [0,T)' while "
                      "quantifiers.ordered[5].binder is the tuple '(q,t0)', so a conforming schema "
                      "is rejected. Measured at cce9c60146d6: structural pass, semantic baseline and "
                      "hardened reject on R03 only; C2/C0 accept."),
       }],
       findings=[
           "Repair verified in artifact-local shadows: patched 645eb16a0060 accepts F1, keeps "
           "C2/C0 and the 32-mutant counts unchanged, and makes the suite exit 0 / valid=true at "
           "the frozen bytes with rebased controls and live canonical pins.",
           "True defects are still caught (M-A drop quantifiers, M-B unresolved domain, M-C missing "
           "final clause, M-D renamed t0, M-E extra component, M-F emptied formal): all reject R03 "
           "under the patched rule.",
           "Boundary measured, not hidden: the patched rule treats component ORDER inside a "
           "composite binder as insignificant (M-G '(t0,q)' accepts; the literal rule rejected it). "
           "If order-sensitivity is required, this patch must be extended.",
           "The suite runner records no blocking_adjudication item for a rejected conforming-"
           "canonical control (valid=false, blocking_adjudication=[]), which is why this failure "
           "was not routed; owner may want to extend that list.",
           "Cheapest consistent resolution: adopt the token-aware R03 check in the auditor; do NOT "
           "edit the frozen F1 formal sentence to satisfy a lexical tool (CF-4), which would bump "
           "FROZEN and re-void hash-bound verdicts.",
       ],
       falsifier=falsifier)

    ev("blocker", "blocker",
       description=(
           "F1#cce9c60146d6 cannot become calibration-valid in the two-stage pipeline while R03 "
           "stays literal: the binding structural stage passes the frozen bytes, but both semantic "
           "stages reject them, and the suite's validity.blocking_adjudication is empty for a "
           "rejected conforming-canonical control. The repair is measured and ready but not "
           "adopted; no canonical write was made."),
       needed_to_unblock=(
           "lead-audit / worker-06 (auditor owner) adopt or reject the one-hunk token-aware R03 "
           "repair (artifacts/worker-004/f1_r03_repair/patched/spec_conformance_audit.py#645eb16a0060) "
           "and re-run schemas/semantic_contract_tests/run_contract_tests.py at the pinned bytes; "
           "and/or lead-audit record an explicit adjudication of R03 as a lexical false positive. "
           "Separately, the KEY_MANIFEST revision instability still blocks a single suite run that "
           "accepts both live schemas and the rebased controls (worker-004 W004-SEMCT-CONTROL-REBASE-02, "
           "worker-080)."),
       evidence_refs=[ref(ARTIFACTS["report"]), ref(ARTIFACTS["patched_auditor"]),
                      PINS["f1"][0] + "#" + PINS["f1"][1][:12],
                      PINS["auditor"][0] + "#" + PINS["auditor"][1][:12]],
       gate="G-FORM",
       falsifier=falsifier)

    ev("status", "status", status="active", hours=1.2,
       summary=("W004-F1-R03-REPAIR-01 complete from the worker side (checkpoint + exit): one "
                "bounded class-bound task, read-only on canonical paths. R03 at F1#cce9c60146d6 "
                "adjudicated as a lexical false positive; one-hunk token-aware repair verified in "
                "artifact-local shadows (suite exit 0 / valid=true, controls 3/3, canonical 3/3, "
                "mutants 32/11/32 unchanged, deterministic rerun) with true-defect and stale-control "
                "negative controls. Advisory review revise on the auditor; F1 routing blocker "
                "recorded. No gate verdict, no node completion, no canonical write."),
       evidence_refs=[ref(ARTIFACTS["report"]), ref(ARTIFACTS["patched_auditor"]),
                      ref(ARTIFACTS["harness"]), ref(ARTIFACTS["readme"]),
                      "runtime/state/w04_checkpoint_f1_r03_repair.json#" + ckpt_sha[:12]],
       artifacts={v: art[k] for k, v in ARTIFACTS.items()},
       checkpoint="runtime/state/w04_checkpoint_f1_r03_repair.json#" + ckpt_sha[:12],
       next_falsifier=falsifier)

    for e in E:
        try:
            validate_event(e)
        except SchemaError as ex:
            print(f"FATAL: event {e.get('event_id')} invalid: {ex}", file=sys.stderr)
            return 2

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    existing.add(json.loads(line).get("event_id"))
                except ValueError:
                    pass
    new = [e for e in E if e["event_id"] not in existing]
    with OUTBOX.open("a") as f:
        for e in new:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(json.dumps({"checkpoint": str(CKPT.relative_to(REPO)), "checkpoint_sha256": ckpt_sha,
                      "events_total": len(E), "events_appended": len(new),
                      "skipped_existing": len(E) - len(new),
                      "event_ids": [e["event_id"] for e in new]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
