#!/usr/bin/env python3
"""Emit the W16-CORPUS-REBIND-01 worker events, artifact manifest and checkpoint.

Idempotent: an event is appended to comms/outbox/worker-16.jsonl only if its event_id is
not already present. No frozen/shared artifact is modified.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "out"
OUTBOX = ROOT / "comms" / "outbox" / "worker-16.jsonl"
CKPT = ROOT / "runtime" / "state" / "w016_checkpoint_corpus_rebind.json"
CST = timezone(timedelta(hours=8))

TASK = "W16-CORPUS-REBIND-01"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
NODE = "F1"
GATE = "G-FORM"

# frozen identities cited by this pass
FROZEN_JSON = "artifacts/formulation/FROZEN.json#sha256:2f358f6722d9"
FROZEN_F1 = "artifacts/formulation/schemas/af_wcc_vacuum.yaml#sha256:cce9c60146d6"
FROZEN_C0 = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml#sha256:55d0a1ea9bda"
FROZEN_REPORT = "artifacts/formulation/evidence/acceptance_pipeline_report.json#sha256:9b7d6c8208d3"
OLD_EVIDENCE = "artifacts/formulation/evidence/semantic_escape_rebased.json#sha256:7e44de0e3906"
RULE_SPEC = "artifacts/formulation/rule_spec.json#sha256:40f9bb9e657b"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def build_manifest() -> dict:
    files = [
        HERE / "REPORT.md",
        HERE / "run_rebind.py",
        HERE / "emit_events.py",
        OUT / "rebind_result.json",
        OUT / "raw_verdicts.json",
        OUT / "semantic_escape_rebased.json",
        OUT / "acceptance_pipeline_report.json",
        OUT / "before_run_acceptance.stdout.txt",
        OUT / "measure_run1.stdout.txt",
        OUT / "measure_run2.stdout.txt",
        OUT / "after_run_acceptance.stdout.txt",
    ]
    manifest = {
        "actor": "worker-16",
        "worker_slot": "worker-016",
        "task_id": TASK,
        "class_ids": CLASS_IDS,
        "node_id": NODE,
        "gate": GATE,
        "authority": "worker evidence only; no gate verdict, no node completion",
        "created_at": now(),
        "files": {},
    }
    for f in files:
        manifest["files"][rel(f)] = {"bytes": f.stat().st_size, "sha256": sha256(f)}
    mpath = HERE / "artifact_manifest.json"
    mpath.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def load_result() -> dict:
    return json.loads((OUT / "rebind_result.json").read_text())


def artifact_event(eid: str, artifact_type: str, path: Path, created: str, extra: dict | None = None) -> dict:
    ev = {
        "event_id": eid,
        "event_type": "artifact",
        "created_at": created,
        "actor": "worker-16",
        "node_id": NODE,
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "group_id": "formulation",
        "task_id": TASK,
        "artifact_type": artifact_type,
        "path": rel(path),
        "sha256": sha256(path),
        "validation_status": "unverified",
        "authority_note": "worker event only; validation_status=passed is lead/audit authority",
        "evidence_refs": [f"{rel(path)}#sha256:{sha256(path)[:12]}", FROZEN_JSON, FROZEN_C0],
    }
    if extra:
        ev.update(extra)
    return ev


def build_events(man: dict) -> list[dict]:
    ts = now()
    res = load_result()
    rebased = HERE / "out" / "semantic_escape_rebased.json"
    report = HERE / "out" / "acceptance_pipeline_report.json"
    rawv = OUT / "raw_verdicts.json"
    result = OUT / "rebind_result.json"

    evs: list[dict] = []
    evs.append(artifact_event(f"{TASK}-artifact-report", "rebind_report", HERE / "REPORT.md", ts))
    evs.append(artifact_event(f"{TASK}-artifact-result", "rebind_result", result, ts,
                              {"summary": ("Frozen-bytes preflight exit 3 reproduced; staged rebase "
                                           "deterministic; corpus base now 55d0a1ea; staged acceptance "
                                           "exit 1 solely on canonical F1 R03.")}))
    evs.append(artifact_event(f"{TASK}-artifact-rebased-evidence", "rebased_semantic_corpus", rebased, ts,
                              {"supersedes": OLD_EVIDENCE, "base_sha256": res["after_base_sha256"],
                               "summary": res["after_summary"]}))
    evs.append(artifact_event(f"{TASK}-artifact-acceptance-report", "acceptance_pipeline_report", report, ts,
                              {"staged_verdict": res["after_report"]["verdict"],
                               "staged_returncode": res["after_run_acceptance"]["returncode"],
                               "note": "staged replacement for the frozen report; not adopted"}))
    evs.append(artifact_event(f"{TASK}-artifact-raw-verdicts", "raw_stage_verdicts", rawv, ts,
                              {"f1_stage2_failed_rules": res.get("f1_semantic_failed_rules", [])}))
    evs.append(artifact_event(f"{TASK}-artifact-harness", "rebind_harness", HERE / "run_rebind.py", ts,
                              {"deterministic": res["rebased_deterministic"],
                               "staged_inputs_all_match": res["staged_inputs_all_match"],
                               "frozen_manifest_crosscheck_all_match": res["frozen_manifest_crosscheck_all_match"]}))
    evs.append(artifact_event(f"{TASK}-artifact-manifest", "artifact_manifest", HERE / "artifact_manifest.json", ts))
    evs.append(artifact_event(f"{TASK}-artifact-emitter", "event_emitter", HERE / "emit_events.py", ts))

    evs.append({
        "event_id": f"{TASK}-review-frozen-acceptance",
        "event_type": "review",
        "created_at": ts,
        "actor": "worker-16",
        "reviewer": "worker-16",
        "node_id": NODE,
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "group_id": "formulation",
        "task_id": TASK,
        "target_id": FROZEN_REPORT,
        "verdict": "revise",
        "score": 2,
        "hard_failures": ["W16R28-F1", "W16R28-F2"],
        "findings": [
            ("W16R28-F1: the frozen report/evidence bind corpus base 1bb78ce9 while frozen C0 is "
             "55d0a1ea, so preflight fails closed and run_acceptance.py exits 3 at frozen bytes "
             "(reproduced read-only). A deterministic rebased replacement binds 55d0a1ea with "
             "identical per-mutant verdicts and union 31/31 (out/semantic_escape_rebased.json "
             "#sha256:%s, out/acceptance_pipeline_report.json#sha256:%s); adoption + FROZEN bump are "
             "lead actions." % (sha256(rebased)[:12], sha256(report)[:12])),
            ("W16R28-F2: after rebase the stage acceptance run still exits 1 because canonical F1 "
             "af_wcc_vacuum.yaml#cce9c60146d6 passes stage 1 but stage 2 rejects it with "
             "failed_rules=['R03'] (raw capture out/raw_verdicts.json). F2a/F2b pass both stages. "
             "This is the adjudicated literal-match false positive; Option A/B disposition is "
             "reserved to the lead/controller."),
            ("Rebase changes no measurement: 31 mutants, structural 30/31, semantic 11/31, union "
             "31/31, 0 escapes, controls 2/2 pass both stages (not format-dominated)."),
        ],
        "evidence_refs": [FROZEN_REPORT, OLD_EVIDENCE, FROZEN_C0, FROZEN_F1, RULE_SPEC,
                          f"artifacts/worker-16/corpus_rebind/out/rebind_result.json#sha256:{sha256(result)[:12]}",
                          f"artifacts/worker-16/corpus_rebind/out/raw_verdicts.json#sha256:{sha256(rawv)[:12]}"],
        "next_falsifier": ("A run_acceptance.py exit 0 at frozen bytes with the frozen evidence and "
                           "unpatched tools; or a per-mutant verdict diff between the 1bb78ce9 and "
                           "55d0a1ea corpora."),
    })

    evs.append({
        "event_id": f"{TASK}-claim",
        "event_type": "claim",
        "created_at": ts,
        "actor": "worker-16",
        "node_id": NODE,
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "group_id": "formulation",
        "task_id": TASK,
        "conclusion_type": "formal_model",
        "statement": (
            "At FROZEN revision 28 (FROZEN.json#sha256:2f358f6722d9), applying the unchanged corpus "
            "manifest c102445df397 to the frozen canonical C0 (55d0a1ea) in an isolated stage mirror "
            "yields a deterministic rebased corpus (base_sha256=55d0a1ea, sha256 c14077ab9a82) with "
            "31 mutants, structural catch 30/31, stage-2 semantic catch 11/31, union catch 31/31, "
            "0 escapes and 2/2 controls passing both stages; per-mutant verdicts are identical to the "
            "superseded 1bb78ce9 corpus (0 diffs). W16R28-F1 is therefore a stale-binding/hygiene "
            "failure, not a measurement change, and the sanctioned rebase removes the exit-3 "
            "PREFLIGHT FAIL. After rebase the stage acceptance run still exits 1 solely because "
            "canonical F1 is rejected by stage-2 R03 (failed_rules=['R03']); F2a/F2b pass both "
            "stages. W16R28-F2 (adjudicated literal-match false positive) is the sole residual "
            "blocker to run_acceptance.py exit 0; adoption of the rebased bytes and a FROZEN revision "
            "bump remain lead actions."),
        "assumptions": [
            "all runs used the pinned frozen hashes verified in staged_inputs/frozen_manifest_crosscheck",
            "the stage mirror replicates the frozen input tree byte-for-byte; no frozen artifact was modified",
            "worker evidence and tool-conformance measurement, not a theorem and not a gate verdict",
        ],
        "falsifier": (
            "Refute by: (a) a run_acceptance.py exit 0 at frozen bytes with the frozen evidence and "
            "unpatched tools; (b) staged inputs differing from the pinned FROZEN rev28 hashes; "
            "(c) two staged measure_semantic_escape.py runs yielding different corpus sha256; "
            "(d) the rebased corpus applying a different mutation set than manifest c102445df397; "
            "(e) any per-mutant verdict diff between the 1bb78ce9 and 55d0a1ea corpora."),
        "evidence_refs": [FROZEN_JSON, FROZEN_C0, FROZEN_F1, RULE_SPEC,
                          f"artifacts/worker-16/corpus_rebind/out/rebind_result.json#sha256:{sha256(result)[:12]}",
                          f"artifacts/worker-16/corpus_rebind/out/semantic_escape_rebased.json#sha256:{sha256(rebased)[:12]}",
                          f"artifacts/worker-16/corpus_rebind/out/acceptance_pipeline_report.json#sha256:{sha256(report)[:12]}"],
        "artifact_refs": [
            f"artifacts/worker-16/corpus_rebind/out/rebind_result.json#sha256:{sha256(result)[:12]}",
            f"artifacts/worker-16/corpus_rebind/out/semantic_escape_rebased.json#sha256:{sha256(rebased)[:12]}",
            f"artifacts/worker-16/corpus_rebind/REPORT.md#sha256:{sha256(HERE / 'REPORT.md')[:12]}",
        ],
    })

    evs.append({
        "event_id": f"{TASK}-blocker",
        "event_type": "blocker",
        "created_at": ts,
        "actor": "worker-16",
        "node_id": NODE,
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "group_id": "formulation",
        "task_id": TASK,
        "description": (
            "run_acceptance.py cannot exit 0 at frozen bytes. After removing the stale-corpus "
            "preflight failure (W16R28-F1 rebased in stage), the only remaining failure is canonical "
            "F1 af_wcc_vacuum.yaml#cce9c60146d6: stage 1 pass, stage 2 reject failed_rules=['R03'] "
            "(W16R28-F2). F2a/F2b pass both stages; all 31 mutants are union-caught; both controls "
            "pass."),
        "needed_to_unblock": (
            "Lead/controller disposition of W16R28-F2: Option A amend the R03 implementation "
            "(no frozen byte change; worker-16's variable-wise patch accepts the frozen bytes and "
            "still rejects the unbound negative control, artifacts/worker-16/r03_adjudication/"
            "tools/spec_conformance_audit_r03patch.py#sha256:4b3de203d6ec), or Option B change the F1 "
            "formal sentence to a literal '(q,t0)' rendering (new hash + re-review + re-freeze); "
            "then adopt the rebased corpus bytes and bump the FROZEN revision."),
        "evidence_refs": [FROZEN_F1, FROZEN_REPORT, OLD_EVIDENCE, RULE_SPEC,
                          f"artifacts/worker-16/corpus_rebind/out/raw_verdicts.json#sha256:{sha256(rawv)[:12]}",
                          "artifacts/worker-16/r03_adjudication/out/adjudication.json#sha256:76c143368b0a"],
    })

    evs.append({
        "event_id": f"{TASK}-status",
        "event_type": "status",
        "created_at": ts,
        "actor": "worker-16",
        "node_id": NODE,
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "group_id": "formulation",
        "task_id": TASK,
        "run_id": "w16-corpus-rebind-01",
        "status": "active",
        "claims_completion": False,
        "hours": 0.6,
        "summary": (
            "Self-claimed bounded class-bound task complete (worker evidence; not a gate verdict). "
            "W16R28-F1 resolved stage-side: frozen-bytes exit 3 reproduced read-only; deterministic "
            "staged rebase binds the corpus to frozen C0 55d0a1ea with union 31/31 and controls 2/2 "
            "(per-mutant verdicts identical to the superseded corpus). Residual: run_acceptance "
            "still exits 1 solely on canonical F1 stage-2 R03 (W16R28-F2, adjudicated false "
            "positive; Option A/B lead decision); W16R28-F3/F4 remain open. Frozen paths unmodified; "
            "adoption + FROZEN bump are lead actions."),
        "evidence_refs": [FROZEN_JSON, FROZEN_C0, FROZEN_F1,
                          f"artifacts/worker-16/corpus_rebind/out/rebind_result.json#sha256:{sha256(result)[:12]}",
                          f"artifacts/worker-16/corpus_rebind/out/semantic_escape_rebased.json#sha256:{sha256(rebased)[:12]}",
                          f"artifacts/worker-16/corpus_rebind/out/acceptance_pipeline_report.json#sha256:{sha256(report)[:12]}",
                          "runtime/state/w016_checkpoint_corpus_rebind.json"],
        "next_falsifier": (
            "A run_acceptance.py exit 0 at frozen bytes with the frozen evidence and unpatched tools "
            "(no rebase needed); or a stage-2 accept at F1 cce9c60146d6 with the unpatched tool; or "
            "any per-mutant verdict diff between the pre/post-rebase corpora."),
    })
    return evs


def append_idempotent(evs: list[dict]) -> list[str]:
    existing: set[str] = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except ValueError:
                continue
    appended = []
    with OUTBOX.open("a") as fh:
        for ev in evs:
            if ev["event_id"] in existing:
                continue
            fh.write(json.dumps(ev) + "\n")
            appended.append(ev["event_id"])
    return appended


def write_checkpoint(man: dict, appended: list[str], all_ids: list[str], res: dict) -> dict:
    ck = {
        "actor": "worker-16",
        "worker": "worker-16",
        "worker_slot": "worker-016",
        "checkpoint_id": "w16-ckpt-corpus-rebind-01",
        "checkpoint_at": now(),
        "task": {
            "id": TASK,
            "class_ids": CLASS_IDS,
            "node_id": NODE,
            "gate": GATE,
            "budget_agent_hours": 3.0,
            "hours_this_pass": 0.6,
            "self_claimed": True,
            "reason": ("no open worker-16 inbox card after W16-R03-ADJ-01; W16R28-F1 was the "
                       "remaining open class-bound item in the rev28 verification checkpoint"),
        },
        "deliverables": man["files"],
        "emitted_events": all_ids,
        "events_appended_this_pass": appended,
        "falsifier": ("see out/rebind_result.json and claim event %s-claim" % TASK),
        "outbox": "comms/outbox/worker-16.jsonl",
        "read_only": ("No shared/frozen artifact was modified. Every write is under "
                      "artifacts/worker-16/corpus_rebind/ plus this checkpoint and the outbox events."),
        "verdict": {
            "before_frozen_run_acceptance_returncode": res["before"]["run_acceptance_returncode"],
            "before_corpus_base_sha256": res["before"]["frozen_evidence_base_sha256"],
            "after_corpus_base_sha256": res["after_base_sha256"],
            "after_rebased_evidence_sha256": res["after_rebased_evidence_sha256"],
            "after_staged_report_sha256": res["after_run_acceptance"]["report_sha256"],
            "after_staged_returncode": res["after_run_acceptance"]["returncode"],
            "after_staged_verdict": res["after_report"]["verdict"],
            "rebased_deterministic": res["rebased_deterministic"],
            "staged_inputs_all_match": res["staged_inputs_all_match"],
            "frozen_manifest_crosscheck_all_match": res["frozen_manifest_crosscheck_all_match"],
            "mutants": res["after_report"]["mutants"],
            "canonical": res["after_report"]["canonical"],
            "controls": res["after_report"]["controls"],
            "f1_stage2_failed_rules": res.get("f1_semantic_failed_rules", []),
            "W16R28-F1": "resolved stage-side (rebased corpus staged; adoption is a lead action)",
            "W16R28-F2": "open; sole residual blocker to run_acceptance exit 0",
        },
        "open_and_not_addressed": [
            "W16R28-F2 canonical F1 stage-2 R03 disposition (Option A/B, lead/controller)",
            "W16R28-F3 location-dependent gate_test_report hash",
            "W16R28-F4 rev27 freeze discipline observation",
            "adoption of the rebased evidence + FROZEN revision bump (lead action)",
        ],
        "authority_note": ("worker event cannot set validation_status=passed, node status=done, or a "
                           "gate verdict; evidence is for lead-audit and the controller."),
    }
    CKPT.write_text(json.dumps(ck, indent=2) + "\n")
    return ck


def main() -> int:
    res = load_result()
    man = build_manifest()
    evs = build_events(man)
    appended = append_idempotent(evs)
    ck = write_checkpoint(man, appended, [e["event_id"] for e in evs], res)
    print(json.dumps({
        "manifest_sha256": sha256(HERE / "artifact_manifest.json"),
        "events_total": len(evs),
        "events_appended": appended,
        "checkpoint": rel(CKPT),
        "checkpoint_sha256": sha256(CKPT),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
