#!/usr/bin/env python3
"""Emit the W16-REV29-CORPUS-REBIND-01 worker events, artifact manifest and checkpoint.

Every event is validated against research_map/schemas.py before the append; an event whose
event_id is already present in the outbox is not re-appended (idempotent). No shared/frozen
artifact is modified: the only writes are this task's artifacts, the checkpoint and the
outbox.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "out"
OUTBOX = ROOT / "comms" / "outbox" / "worker-16.jsonl"
CKPT = ROOT / "runtime" / "state" / "w016_checkpoint_rev29_rebind.json"
CST = timezone(timedelta(hours=8))

sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TASK = "W16-REV29-CORPUS-REBIND-01"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
NODE = "F1"
GATE = "G-FORM"

FROZEN_JSON = "artifacts/formulation/FROZEN.json#sha256:815e08079aef"
FROZEN_F1 = "artifacts/formulation/schemas/af_wcc_vacuum.yaml#sha256:d9cebb9404b2"
FROZEN_F2A = "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml#sha256:e9a27996dfd3"
FROZEN_C0 = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml#sha256:b2ab6acb2bbe"
FROZEN_REPORT = "artifacts/formulation/evidence/acceptance_pipeline_report.json#sha256:9b7d6c8208d3"
OLD_EVIDENCE = "artifacts/formulation/evidence/semantic_escape_rebased.json#sha256:7e44de0e3906"
FROZEN_GATE = "artifacts/formulation/evidence/gate_test_report.json#sha256:26540a6b43cc"
RULE_SPEC = "artifacts/formulation/rule_spec.json#sha256:40f9bb9e657b"
SEM_AUDIT = "artifacts/worker-06/spec_conformance_audit.py#sha256:c79d8ab8440a"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(Path(p).relative_to(ROOT))


def build_manifest() -> dict:
    files = [HERE / "REPORT.md", HERE / "run_rebind_rev29.py", HERE / "emit_events_rev29.py",
             HERE / "snapshot_at_start.json",
             OUT / "rebind_result_rev29.json", OUT / "raw_verdicts.json",
             OUT / "semantic_escape_rebased.json", OUT / "acceptance_pipeline_report.json",
             OUT / "gate_path_probe.json", OUT / "before_run_acceptance.stdout.txt",
             OUT / "after_run_acceptance.stdout.txt"]
    man = {"actor": "worker-16", "worker_slot": "worker-016", "task_id": TASK,
           "class_ids": CLASS_IDS, "node_id": NODE, "gate": GATE,
           "authority": "worker evidence only; no gate verdict, no node completion",
           "created_at": now(), "files": {}}
    for f in files:
        man["files"][rel(f)] = {"bytes": Path(f).stat().st_size, "sha256": sha256(f)}
    (HERE / "artifact_manifest.json").write_text(json.dumps(man, indent=2) + "\n")
    return man


def artifact_event(eid: str, artifact_type: str, path: Path, ts: str, extra: dict | None = None) -> dict:
    ev = {"event_id": eid, "event_type": "artifact", "created_at": ts, "actor": "worker-16",
          "node_id": NODE, "class_ids": CLASS_IDS, "gate": GATE, "group_id": "formulation",
          "task_id": TASK, "artifact_type": artifact_type, "path": rel(path),
          "sha256": sha256(path), "validation_status": "unverified",
          "authority_note": "worker event only; validation_status=passed is lead/audit authority",
          "evidence_refs": [f"{rel(path)}#sha256:{sha256(path)[:12]}", FROZEN_JSON, FROZEN_C0]}
    if extra:
        ev.update(extra)
    return ev


def build_events(man: dict) -> list[dict]:
    ts = now()
    res = json.loads((OUT / "rebind_result_rev29.json").read_text())
    probe = json.loads((OUT / "gate_path_probe.json").read_text())
    rebased = OUT / "semantic_escape_rebased.json"
    report = OUT / "acceptance_pipeline_report.json"
    rawv = OUT / "raw_verdicts.json"
    result = OUT / "rebind_result_rev29.json"
    probej = OUT / "gate_path_probe.json"

    evs: list[dict] = []
    evs.append(artifact_event(f"{TASK}-artifact-report", "rebind_report", HERE / "REPORT.md", ts))
    evs.append(artifact_event(f"{TASK}-artifact-result", "rebind_result", result, ts, {
        "summary": ("Frozen rev29 preflight exit 3 reproduced in an isolated probe; staged rebase "
                    "deterministic; corpus now binds C0 b2ab6acb; staged acceptance exit 1 solely "
                    "on canonical F1 R03.")}))
    evs.append(artifact_event(f"{TASK}-artifact-rebased-evidence", "rebased_semantic_corpus", rebased, ts, {
        "supersedes": OLD_EVIDENCE, "base_sha256": res["after_base_sha256"],
        "summary": res["after_summary"]}))
    evs.append(artifact_event(f"{TASK}-artifact-acceptance-report", "acceptance_pipeline_report", report, ts, {
        "staged_verdict": res["after_report"]["verdict"],
        "staged_returncode": res["after_run_acceptance"]["returncode"],
        "note": "staged replacement for the frozen report; not adopted"}))
    evs.append(artifact_event(f"{TASK}-artifact-raw-verdicts", "raw_stage_verdicts", rawv, ts, {
        "f1_stage2_failed_rules": res.get("f1_semantic_failed_rules", [])}))
    evs.append(artifact_event(f"{TASK}-artifact-gate-path-probe", "gate_path_probe", probej, ts, {
        "finding": probe["finding"], "probe_a_sha256": probe["probe_a"]["report_sha256"],
        "probe_b_sha256": probe["probe_b"]["report_sha256"],
        "normalized_json_identical": probe["normalized_json_identical"]}))
    evs.append(artifact_event(f"{TASK}-artifact-harness", "rebind_harness", HERE / "run_rebind_rev29.py", ts, {
        "deterministic": res["rebased_deterministic"],
        "staged_inputs_all_match": res["staged_inputs_all_match"],
        "snapshot_stable_through_pass": res["snapshot_stable_through_pass"]}))
    evs.append(artifact_event(f"{TASK}-artifact-manifest", "artifact_manifest", HERE / "artifact_manifest.json", ts))
    evs.append(artifact_event(f"{TASK}-artifact-emitter", "event_emitter", HERE / "emit_events_rev29.py", ts))

    evs.append({
        "event_id": f"{TASK}-review-frozen-acceptance",
        "event_type": "review", "created_at": ts, "actor": "worker-16", "reviewer": "worker-16",
        "node_id": NODE, "class_ids": CLASS_IDS, "gate": GATE, "group_id": "formulation",
        "task_id": TASK, "target_id": FROZEN_REPORT, "verdict": "revise", "score": 2,
        "hard_failures": ["B4/acceptance-preflight-stale-corpus", "W16R28-F2/F1-R03"],
        "findings": [
            ("B4: frozen rev29 evidence binds corpus base 1bb78ce9 while frozen C0 is b2ab6acb, so "
             "run_acceptance.py exits 3 (PREFLIGHT FAIL) at the frozen bytes (reproduced in an "
             "isolated probe; shared evidence hash unchanged). A deterministic staged rebase binds "
             "b2ab6acb with the identical mutation set and identical per-mutant verdicts (0 diffs vs "
             "the 55d0a1ea rebase): structural 30/31, semantic 11/31, union 31/31, controls 2/2 "
             "(out/semantic_escape_rebased.json#sha256:%s, "
             "out/acceptance_pipeline_report.json#sha256:%s). Adoption + FROZEN bump are lead actions."
             % (sha256(rebased)[:12], sha256(report)[:12])),
            ("W16R28-F2: after the rebase the staged acceptance still exits 1 because canonical F1 "
             "af_wcc_vacuum.yaml#d9cebb9404b2 passes stage 1 and is rejected by stage 2 with "
             "failed_rules=['R03']; F2a/F2b pass both stages. Adjudicated literal-match false "
             "positive (w16-R03-ADJ-01); Option A/B disposition is lead/controller authority."),
            ("W16R28-F3 CONFIRMED at rev29: gate_test_report.json embeds 9 absolute fixture paths; "
             "two byte-identical trees at different roots yield reports 9c63de13 / 79e077a8 whose "
             "parsed JSON is identical after root normalization. The gate itself still PASSes "
             "3/3 canonical, 6/6 controls, 31/31 mutants, 2/5 rephrased probes."),
        ],
        "evidence_refs": [FROZEN_REPORT, OLD_EVIDENCE, FROZEN_C0, FROZEN_F1, RULE_SPEC, FROZEN_GATE,
                          f"artifacts/worker-16/rev29_rebind/out/rebind_result_rev29.json#sha256:{sha256(result)[:12]}",
                          f"artifacts/worker-16/rev29_rebind/out/raw_verdicts.json#sha256:{sha256(rawv)[:12]}"],
        "next_falsifier": ("A run_acceptance.py exit 0 at the frozen bytes with the frozen evidence and "
                           "unpatched tools; or a per-mutant verdict diff between the 1bb78ce9 and "
                           "b2ab6acb corpora; or byte-identical gate reports from two different roots."),
    })

    evs.append({
        "event_id": f"{TASK}-claim",
        "event_type": "claim", "created_at": ts, "actor": "worker-16", "node_id": NODE,
        "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": CLASS_IDS, "gate": GATE,
        "group_id": "formulation", "task_id": TASK, "conclusion_type": "formal_model",
        "statement": (
            "At FROZEN revision 29 (FROZEN.json#sha256:815e08079aef, frozen_at "
            "2026-09-12T00:57:26+08:00, 50 files, verify_frozen exit 0), applying the unchanged "
            "corpus manifest c102445df397 to the frozen canonical C0 (b2ab6acb) in an isolated stage "
            "mirror yields a deterministic rebased corpus (base_sha256=b2ab6acb, sha256 "
            "c194a5717a1d) with 31 mutants, structural catch 30/31, stage-2 semantic catch 11/31, "
            "union catch 31/31, 0 escapes and 2/2 controls passing both stages; per-mutant verdicts "
            "and the staged acceptance report (a4524e61f75d) are byte-identical to the rev28 rebase "
            "of the same manifest on base 55d0a1ea (0 diffs). The stale-binding preflight failure "
            "B4/W16R28-F1 is therefore a binding/hygiene failure, not a measurement change, and the "
            "sanctioned rebase moves run_acceptance.py from exit 3 to exit 1. The sole residual "
            "failure is canonical F1 af_wcc_vacuum.yaml#d9cebb9404b2, stage 1 pass, stage 2 reject "
            "failed_rules=['R03'] (W16R28-F2, adjudicated literal-match false positive); F2a/F2b pass "
            "both stages. Separately, W16R28-F3 is confirmed: gate_test_report.json content depends "
            "on the absolute run root (9 embedded fixture paths), so its sha256 pin is reproducible "
            "only from the canonical path, although the gate verdict itself is unchanged "
            "(3/3 canonical, 6/6 controls, 31/31 mutants, 2/5 rephrased probes)."),
        "assumptions": [
            "all runs used the pinned frozen hashes verified in staged_inputs/frozen_manifest_crosscheck",
            "the stage mirror replicates the frozen input tree byte-for-byte; no frozen artifact was modified",
            "worker evidence and tool-conformance measurement, not a theorem and not a gate verdict",
            "the gate-path probe copies the live formulation tree; the copies are byte-identical before each run",
        ],
        "falsifier": res["falsifier"] + " (f) byte-identical gate reports from two different absolute roots, or reports differing after root normalization.",
        "evidence_refs": [FROZEN_JSON, FROZEN_C0, FROZEN_F1, FROZEN_F2A, RULE_SPEC, SEM_AUDIT,
                          f"artifacts/worker-16/rev29_rebind/out/rebind_result_rev29.json#sha256:{sha256(result)[:12]}",
                          f"artifacts/worker-16/rev29_rebind/out/semantic_escape_rebased.json#sha256:{sha256(rebased)[:12]}",
                          f"artifacts/worker-16/rev29_rebind/out/acceptance_pipeline_report.json#sha256:{sha256(report)[:12]}",
                          f"artifacts/worker-16/rev29_rebind/out/gate_path_probe.json#sha256:{sha256(probej)[:12]}"],
        "artifact_refs": [
            f"artifacts/worker-16/rev29_rebind/out/rebind_result_rev29.json#sha256:{sha256(result)[:12]}",
            f"artifacts/worker-16/rev29_rebind/out/semantic_escape_rebased.json#sha256:{sha256(rebased)[:12]}",
            f"artifacts/worker-16/rev29_rebind/REPORT.md#sha256:{sha256(HERE / 'REPORT.md')[:12]}",
        ],
    })

    evs.append({
        "event_id": f"{TASK}-blocker",
        "event_type": "blocker", "created_at": ts, "actor": "worker-16", "node_id": NODE,
        "class_ids": CLASS_IDS, "gate": GATE, "group_id": "formulation", "task_id": TASK,
        "description": (
            "run_acceptance.py cannot exit 0 at the frozen rev29 bytes. After the staged rebase "
            "removes the exit-3 preflight failure (B4/W16R28-F1), the only remaining failure is "
            "canonical F1 af_wcc_vacuum.yaml#d9cebb9404b2: stage 1 pass, stage 2 reject "
            "failed_rules=['R03'] (W16R28-F2). F2a/F2b pass both stages; all 31 mutants union-caught; "
            "both controls pass both stages. Independently, the frozen gate_test_report.json pin is "
            "absolute-root dependent (W16R28-F3), and rev29 was re-frozen twice inside 30 s "
            "(48 -> 50 files) during this pass."),
        "needed_to_unblock": (
            "Lead/controller: (1) adopt the staged rebased evidence + report and bump FROZEN (or "
            "re-run measure_semantic_escape.py in place); (2) dispose W16R28-F2 Option A (amend the "
            "R03 literal-match implementation; worker-16 patch "
            "artifacts/worker-16/r03_adjudication/tools/spec_conformance_audit_r03patch.py#sha256:4b3de203d6ec) "
            "or Option B (change the F1 sentence to a literal '(q,t0)' rendering: new hash + "
            "re-review + re-freeze); (3) decide whether to normalize the gate-report paths before "
            "hashing (W16R28-F3)."),
        "evidence_refs": [FROZEN_F1, FROZEN_REPORT, OLD_EVIDENCE, RULE_SPEC, FROZEN_GATE,
                          f"artifacts/worker-16/rev29_rebind/out/raw_verdicts.json#sha256:{sha256(rawv)[:12]}",
                          f"artifacts/worker-16/rev29_rebind/out/gate_path_probe.json#sha256:{sha256(probej)[:12]}",
                          "artifacts/worker-16/r03_adjudication/out/adjudication.json#sha256:76c143368b0a"],
    })

    evs.append({
        "event_id": f"{TASK}-status",
        "event_type": "status", "created_at": ts, "actor": "worker-16", "node_id": NODE,
        "class_ids": CLASS_IDS, "gate": GATE, "group_id": "formulation", "task_id": TASK,
        "run_id": "w16-rev29-corpus-rebind-01", "status": "active", "claims_completion": False,
        "hours": 0.5,
        "summary": (
            "Self-claimed bounded class-bound task complete (worker evidence; not a gate verdict). "
            "B4/W16R28-F1 resolved stage-side at FROZEN rev29 815e08079aef: frozen exit 3 reproduced "
            "in an isolated probe; deterministic staged rebase binds C0 b2ab6acb with union 31/31, "
            "0 escapes, controls 2/2 and per-mutant verdicts identical to the rev28 rebase. "
            "run_acceptance.py moves exit 3 -> exit 1; the sole residual failure is canonical F1 "
            "stage-2 R03 (W16R28-F2, lead Option A/B). W16R28-F3 confirmed by a two-root probe "
            "(gate reports differ only in 9 absolute paths; normalized JSON identical; gate still "
            "PASS 3/3, 6/6, 31/31, 2/5 rephrased). Freeze churn: rev29 re-frozen 3d9e3d77 (48 files) "
            "-> 815e08079aef (50 files) at 00:57:26; all results bind the latter with end drift 0. "
            "Frozen paths unmodified; adoption + FROZEN bump are lead actions."),
        "evidence_refs": [FROZEN_JSON, FROZEN_C0, FROZEN_F1, FROZEN_GATE,
                          f"artifacts/worker-16/rev29_rebind/out/rebind_result_rev29.json#sha256:{sha256(result)[:12]}",
                          f"artifacts/worker-16/rev29_rebind/out/semantic_escape_rebased.json#sha256:{sha256(rebased)[:12]}",
                          f"artifacts/worker-16/rev29_rebind/out/acceptance_pipeline_report.json#sha256:{sha256(report)[:12]}",
                          f"artifacts/worker-16/rev29_rebind/out/gate_path_probe.json#sha256:{sha256(probej)[:12]}",
                          "runtime/state/w016_checkpoint_rev29_rebind.json"],
        "next_falsifier": (
            "A run_acceptance.py exit 0 at the frozen bytes with the frozen evidence and unpatched "
            "tools (no rebase needed); or a stage-2 accept at F1 d9cebb9404b2 with the unpatched "
            "tool; or byte-identical gate reports from two different absolute roots."),
    })
    return evs


def append_idempotent(evs: list[dict]) -> tuple[list[str], list[dict]]:
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
    appended, rejected = [], []
    with OUTBOX.open("a") as fh:
        for ev in evs:
            try:
                validate_event(ev)
            except Exception as exc:  # noqa: BLE001
                rejected.append({"event_id": ev.get("event_id"), "error": str(exc)})
                continue
            if ev["event_id"] in existing:
                continue
            fh.write(json.dumps(ev) + "\n")
            appended.append(ev["event_id"])
    return appended, rejected


def write_checkpoint(man: dict, appended: list[str], all_ids: list[str], res: dict, probe: dict) -> dict:
    ck = {
        "actor": "worker-16", "worker": "worker-16", "worker_slot": "worker-016",
        "checkpoint_id": "w16-ckpt-rev29-corpus-rebind-01", "checkpoint_at": now(),
        "task": {"id": TASK, "class_ids": CLASS_IDS, "node_id": NODE, "gate": GATE,
                 "budget_agent_hours": 3.0, "hours_this_pass": 0.5, "self_claimed": True,
                 "reason": ("no open worker-16 inbox card; B4/W16R28-F1 was the remaining open "
                            "class-bound item at the newest freeze")},
        "bound_revision": {"frozen_sha256": res["snapshot"]["frozen_sha256"],
                           "revision": res["snapshot"]["frozen_revision"],
                           "frozen_at": res["snapshot"]["frozen_at"],
                           "verify_frozen_rc": res["verify_frozen"]["returncode"]},
        "deliverables": man["files"],
        "emitted_events": all_ids, "events_appended_this_pass": appended,
        "outbox": "comms/outbox/worker-16.jsonl",
        "read_only": ("no shared/frozen artifact modified; writes under "
                      "artifacts/worker-16/rev29_rebind/ plus this checkpoint and the outbox events. "
                      "The frozen-bytes failure reproduction ran in an isolated probe copy; the live "
                      "evidence hash was unchanged."),
        "verdict": {
            "before_frozen_run_acceptance_returncode": res["before"]["run_acceptance_returncode"],
            "before_corpus_base_sha256": res["before"]["frozen_evidence_base_sha256"],
            "after_corpus_base_sha256": res["after_base_sha256"],
            "after_rebased_evidence_sha256": res["after_rebased_evidence_sha256"],
            "after_staged_report_sha256": res["after_run_acceptance"]["report_sha256"],
            "after_staged_returncode": res["after_run_acceptance"]["returncode"],
            "after_staged_verdict": res["after_report"]["verdict"],
            "rebased_deterministic": res["rebased_deterministic"],
            "per_mutant_diffs_vs_rev28_rebase": 0,
            "mutants": res["after_report"]["mutants"],
            "canonical": res["after_report"]["canonical"],
            "controls": res["after_report"]["controls"],
            "f1_stage2_failed_rules": res.get("f1_semantic_failed_rules", []),
            "snapshot_stable_through_pass": res["snapshot_stable_through_pass"],
            "W16R28-F3_gate_path": probe["finding"],
            "W16R28-F1_B4": "resolved stage-side (rebased corpus staged; adoption is a lead action)",
            "W16R28-F2": "open; sole residual blocker to run_acceptance exit 0",
        },
        "open_and_not_addressed": [
            "W16R28-F2 canonical F1 stage-2 R03 disposition (Option A/B, lead/controller)",
            "adoption of the rebased evidence + FROZEN revision bump (lead action)",
            "W16R28-F3 fix decision (normalize report paths or pin a root-independent digest)",
            "W16R28-F4 freeze churn observation (rev29 re-frozen twice in 30 s)",
        ],
        "authority_note": ("worker event cannot set validation_status=passed, node status=done, or a "
                           "gate verdict; evidence is for lead-audit and the controller."),
    }
    CKPT.write_text(json.dumps(ck, indent=2) + "\n")
    return ck


def main() -> int:
    res = json.loads((OUT / "rebind_result_rev29.json").read_text())
    probe = json.loads((OUT / "gate_path_probe.json").read_text())
    man = build_manifest()
    evs = build_events(man)
    appended, rejected = append_idempotent(evs)
    ck = write_checkpoint(man, appended, [e["event_id"] for e in evs], res, probe)
    print(json.dumps({
        "manifest_sha256": sha256(HERE / "artifact_manifest.json"),
        "events_total": len(evs), "events_appended": appended, "events_rejected": rejected,
        "checkpoint": rel(CKPT), "checkpoint_sha256": sha256(CKPT),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
