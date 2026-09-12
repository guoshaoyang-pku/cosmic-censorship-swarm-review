#!/usr/bin/env python3
"""W004 part 3: self-check, artifact manifest, outbox events, worker checkpoint.

Order (all fail-closed):
  1. verify every referenced artifact exists and its sha256 matches on disk
  2. build artifact_manifest.json for the whole task directory
  3. build the upward events, validate each with the real
     research_map.schemas.validate_event (after normalize_event, exactly as ingest does)
  4. append them to comms/outbox/worker-004.jsonl
  5. write the worker-local checkpoint

Worker authority is respected: no gate verdict, no `done`, no `passed`, no canonical write.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CST = timezone(timedelta(hours=8))
sys.path.insert(0, str(REPO / "research_map"))
from schemas import validate_event, SchemaError  # noqa: E402
from comms import normalize_event  # noqa: E402

OUTBOX = REPO / "comms" / "outbox" / "worker-004.jsonl"
STATE = REPO / "runtime" / "state"
CHECKPOINT = STATE / "w004_semct_control_rebase_checkpoint.json"
CHECKPOINT_LOG = STATE / "w004_checkpoints.jsonl"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build_manifest() -> dict:
    files = {}
    for p in sorted(HERE.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(REPO))
        if "/tmp/" in rel or p.name.endswith(".pyc"):
            continue
        files[rel] = {"sha256": sha(p), "bytes": p.stat().st_size}
    man = {"task": "W004-SEMCT-CONTROL-REBASE-01", "built_at": now(), "root": str(HERE.relative_to(REPO)),
           "files": files, "n_files": len(files)}
    (HERE / "artifact_manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    return man


def main() -> int:
    rebase = json.loads((HERE / "rebase_report.json").read_text())
    suite = json.loads((HERE / "suite_run_report.json").read_text())
    proposal = json.loads((HERE / "manifest_patch_proposal.json").read_text())
    man = build_manifest()

    # ---- 1. artifact existence + hash self-check -------------------------------------
    refs = {
        "artifacts/worker-004/semct_control_rebase/rebase_report.json": sha(HERE / "rebase_report.json"),
        "artifacts/worker-004/semct_control_rebase/suite_run_report.json": sha(HERE / "suite_run_report.json"),
        "artifacts/worker-004/semct_control_rebase/manifest_patch_proposal.json": sha(HERE / "manifest_patch_proposal.json"),
        "artifacts/worker-004/semct_control_rebase/artifact_manifest.json": sha(HERE / "artifact_manifest.json"),
        "artifacts/worker-004/semct_control_rebase/README.md": sha(HERE / "README.md"),
        "artifacts/worker-004/semct_control_rebase/rebase_controls.py": sha(HERE / "rebase_controls.py"),
        "artifacts/worker-004/semct_control_rebase/build_patched_suite.py": sha(HERE / "build_patched_suite.py"),
    }
    for tid, info in rebase["rebased_controls"].items():
        refs[info["rebased"]] = info["rebased_sha256"]
    bad = [p for p, h in refs.items() if not (REPO / p).is_file() or sha(REPO / p) != h]
    if bad:
        raise SystemExit(f"self-check failed (missing/mismatched): {bad}")
    print(f"self-check ok: {len(refs)} hash-bound artifacts, {man['n_files']} files in manifest")

    # ---- 2. events -------------------------------------------------------------------
    t = now()
    rid = "w004-semct"
    ctrl = {tid: info["rebased_sha256"] for tid, info in rebase["rebased_controls"].items()}
    ev = []

    for tid, name in [("SCT-C01", "control_comment_only_composite.yaml"),
                      ("SCT-C02", "control_conforming_base.yaml"),
                      ("SCT-C03", "control_quoted_forbidden_phrase.yaml")]:
        ev.append({
            "event_id": f"{rid}-{tid.lower()}-rebased-control-20260912T0040",
            "event_type": "artifact", "created_at": t, "actor": "worker-004",
            "node_id": "A1", "class_id": "AF-SCC-C0-VAC-GEN",
            "artifact_type": "rebased_semantic_contract_control",
            "path": rebase["rebased_controls"][tid]["rebased"],
            "sha256": ctrl[tid], "validation_status": "unverified",
            "evidence_refs": [f"schemas/semantic_contract_tests/fixtures/controls/{name}#"
                              f"{rebase['rebased_controls'][tid]['source_sha256'][:12]}",
                              "artifacts/formulation/tools/check_class_schema.py#000e09e46b2f"],
            "note": ("frozen control with the R28-violating duplicate row deleted (1 hunk, -8/+0); "
                     "same bytes otherwise; mutants untouched"),
        })

    ev.append({
        "event_id": f"{rid}-rebase-report-20260912T0040", "event_type": "artifact", "created_at": t,
        "actor": "worker-004", "node_id": "A1", "class_id": "AF-SCC-C0-VAC-GEN",
        "artifact_type": "control_rebase_measurement",
        "path": "artifacts/worker-004/semct_control_rebase/rebase_report.json",
        "sha256": refs["artifacts/worker-004/semct_control_rebase/rebase_report.json"],
        "validation_status": "unverified",
        "evidence_refs": ["schemas/semantic_contract_tests/fixtures/controls/control_conforming_base.yaml#7b910cf34e64",
                          "artifacts/worker-06/spec_conformance_audit.py#c79d8ab8440a"],
        "note": ("stale controls 0/3 accepted (structural R28); rebased controls 3/3 accepted by all three "
                 "stages; pinned canonical 3/3; inputs sha256-pinned"),
    })
    ev.append({
        "event_id": f"{rid}-suite-run-report-20260912T0040", "event_type": "artifact", "created_at": t,
        "actor": "worker-004", "node_id": "A1", "class_id": "AF-SCC-C0-VAC-GEN",
        "artifact_type": "shadow_suite_end_to_end_run",
        "path": "artifacts/worker-004/semct_control_rebase/suite_run_report.json",
        "sha256": refs["artifacts/worker-004/semct_control_rebase/suite_run_report.json"],
        "validation_status": "unverified",
        "evidence_refs": ["artifacts/worker-004/semct_control_rebase/shadow_repo/artifacts/worker-004/suite_patched/observed_verdicts.json#"
                          f"{sha(HERE/'shadow_repo/artifacts/worker-004/suite_patched/observed_verdicts.json')[:12]}",
                          "artifacts/worker-004/semct_control_rebase/shadow_repo_stale/artifacts/worker-004/suite_stale/observed_verdicts.json#"
                          f"{sha(HERE/'shadow_repo_stale/artifacts/worker-004/suite_stale/observed_verdicts.json')[:12]}"],
        "note": ("rev27+rebased exit 0 valid=true controls 3/3; rev27+stale exit 3 valid=false controls 0/3; "
                 "mutants 32/11/32 both; rev28+rebased exit 3 (key-manifest regression)"),
    })
    ev.append({
        "event_id": f"{rid}-patch-proposal-20260912T0040", "event_type": "artifact", "created_at": t,
        "actor": "worker-004", "node_id": "A1", "class_id": "AF-SCC-C0-VAC-GEN",
        "artifact_type": "manifest_patch_proposal",
        "path": "artifacts/worker-004/semct_control_rebase/manifest_patch_proposal.json",
        "sha256": refs["artifacts/worker-004/semct_control_rebase/manifest_patch_proposal.json"],
        "validation_status": "unverified",
        "evidence_refs": ["artifacts/worker-004/semct_control_rebase/artifact_manifest.json#"
                          f"{refs['artifacts/worker-004/semct_control_rebase/artifact_manifest.json'][:12]}"],
        "note": "owner astra-lead-formulation; nothing applied to canonical paths",
    })

    s1 = rebase["measurements"]["summary"]
    s2 = suite["conclusion"]
    ev.append({
        "event_id": f"{rid}-claim-rebase-20260912T0040", "event_type": "claim", "created_at": t,
        "actor": "worker-004", "class_id": "AF-SCC-C0-VAC-GEN", "node_id": "A1",
        "conclusion_type": "formal_model",
        "statement": (
            "ADJ-CONTROL-STALENESS is caused by one misplaced duplicate row: the three frozen controls carry "
            "pair [finite_codimension_complement, residual_comeager] with direction=transfers inside "
            "genericity.transfer_failures (the same pair is correctly in transfer_holds), which R28 rejects. "
            "Deleting exactly that 8-line block (1 hunk, -8/+0, all other bytes identical) makes all three "
            "controls accepted by the structural gate and both semantic stages (stale 0/3 vs rebased 3/3 at "
            "stage hashes 000e09e46b2f/c79d8ab8440a). End-to-end in an artifact-local shadow repo with "
            "KEY_MANIFEST rev27 fce91948ba3a and pinned gate-accepted canonical snapshots, the rebased-control "
            "suite exits 0 with valid_for_calibration=true, controls 3/3, canonical 3/3, mutant counts "
            "unchanged 32/11/32 and 0 escapes, while the original-control suite exits 3 with controls 0/3 - "
            "the two runs differ only in the three control files."),
        "assumptions": [
            "the pinned bytes in rebase_report.json inputs_pinned and suite_run_report.json stage_pins are the "
            "revision under test; any byte change voids the measurement",
            "KEY_MANIFEST rev27 fce91948ba3a (pinned copy in artifacts/worker-061) is the allowlist state in "
            "which the frozen corpus was authored and gate-accepted",
            "structural/semantic contract tests decide shape, not mathematical truth or non-vacuity",
            "worker cannot set done/passed or a gate verdict; this is a repair proposal for the lead owner",
        ],
        "falsifier": ("see suite_run_report.json falsifier list: an unmodified control accepted by structural "
                      "at the pinned tools/manifest, a rebased control rejected by any stage, any byte "
                      "difference outside the removed 8-line block, a rev27_patched run not reaching exit 0 / "
                      "valid=true, or mutant counts != 32/11/32"),
        "evidence_refs": [
            "research_map/events.jsonl",  # placeholder replaced below
        ],
        "artifact_refs": [
            f"artifacts/worker-004/semct_control_rebase/rebase_report.json#{refs['artifacts/worker-004/semct_control_rebase/rebase_report.json'][:12]}",
            f"artifacts/worker-004/semct_control_rebase/suite_run_report.json#{refs['artifacts/worker-004/semct_control_rebase/suite_run_report.json'][:12]}",
            f"artifacts/worker-004/semct_control_rebase/rebased_controls/control_conforming_base.yaml#{ctrl['SCT-C02'][:12]}",
        ],
        "measurements": {"stale_structural_accept": s1["stale_accepted_by_structural"],
                         "rebased_all_stage_accept": s1["rebased_accepted_by_all_three_stages"],
                         "rev27_patched_exit": s2["rev27_patched_exit"],
                         "rev27_stale_exit": s2["rev27_stale_exit"],
                         "mutants": "32/11/32"},
    })
    # replace placeholder with the real hash-bound refs
    ev[-1]["evidence_refs"] = [
        f"artifacts/worker-004/semct_control_rebase/rebase_report.json#{refs['artifacts/worker-004/semct_control_rebase/rebase_report.json'][:12]}",
        f"artifacts/worker-004/semct_control_rebase/suite_run_report.json#{refs['artifacts/worker-004/semct_control_rebase/suite_run_report.json'][:12]}",
        "artifacts/formulation/tools/check_class_schema.py#000e09e46b2f",
        "artifacts/worker-06/spec_conformance_audit.py#c79d8ab8440a",
    ]

    km = suite["key_manifests"]
    ev.append({
        "event_id": f"{rid}-blocker-keymanifest-20260912T0040", "event_type": "blocker", "created_at": t,
        "actor": "worker-004", "node_id": "A1", "class_id": "AF-SCC-C0-VAC-GEN",
        "description": (
            "KEY_MANIFEST regeneration is not revision-stable and currently blocks all frozen-corpus "
            "calibration: rev28 014e2d301978 (written 00:34 from the new canonical revision) dropped "
            f"{km['rev27_minus_rev28_keys']} while adding {km['rev28_minus_rev27_keys']}. Under rev28 the "
            "binding structural gate R22 rejects the rebased controls, the original frozen controls, and the "
            "pinned canonical revision 1bb78ce9b357/b6123750b37d/9a8bd4c96800 that rev27 accepted; the "
            "rev28+rebased shadow suite exits 3 with controls 0/3 and canonical 0/3. Any reviewer verdict or "
            "calibration bound to a frozen hash is retroactively invalidated by the next canonical edit."),
        "needed_to_unblock": (
            "lead-formulation decision: freeze KEY_MANIFEST together with the schema revision it is used to "
            "judge (or make R22 path-sensitive/revision-aware), then re-pin the suite's conforming-canonical "
            "entries and re-run run_contract_tests.py; the control rebase itself is already verified under rev27."),
        "evidence_refs": [
            f"artifacts/worker-004/semct_control_rebase/suite_run_report.json#{refs['artifacts/worker-004/semct_control_rebase/suite_run_report.json'][:12]}",
            "artifacts/worker-061/f1_rev12_gate/pinned/hist/KEY_MANIFEST.rev27.json#fce91948ba3a",
            "artifacts/formulation/KEY_MANIFEST.json#014e2d301978",
        ],
        "gate": "G-AUDIT",
    })
    ev.append({
        "event_id": f"{rid}-blocker-f1-r03-20260912T0040", "event_type": "blocker", "created_at": t,
        "actor": "worker-004", "node_id": "F1", "class_id": "AF-WCC-VAC-GEN",
        "description": (
            "Live F1 schema schemas/af_wcc_vacuum.yaml sha256 cce9c60146d6... (measured 2026-09-12T00:38:37+08:00, "
            "unchanged since 00:34) passes the structural gate but is rejected by the adopted semantic auditor "
            "(baseline and hardened) on R03: quantifiers.ordered[5] = {kind: not_exists, binder: '(q,t0)', "
            "domain_id: D5} while the string '(q,t0)' does not occur in quantifiers.formal; R03 requires every "
            "ordered binder to appear in the formal sentence. The previous revision 9a8bd4c96800 passed all "
            "three stages. Either the formal sentence omits the final witness binder or the binder string does "
            "not match the token used there."),
        "needed_to_unblock": (
            "lead-formulation reconciles the sixth quantifier binder with quantifiers.formal, then re-runs "
            "artifacts/worker-06/spec_conformance_audit.py (c79d8ab8440a) and records the new artifact hash; "
            "re-measure first - the live tree was being rewritten during this run."),
        "evidence_refs": [
            "schemas/af_wcc_vacuum.yaml#cce9c60146d6",
            "artifacts/worker-06/spec_conformance_audit.py#c79d8ab8440a",
        ],
        "gate": "G-FORM",
    })
    ev.append({
        "event_id": f"{rid}-status-20260912T0040", "event_type": "status", "created_at": t,
        "actor": "worker-004", "node_id": "A1", "status": "active", "hours": 0.5,
        "summary": ("One bounded task, self-selected (no inbox card): minimal rebase of the three frozen "
                    "semantic controls for ADJ-CONTROL-STALENESS, verified end-to-end in a shadow repo; plus "
                    "two measured blockers (KEY_MANIFEST revision instability; live F1 WCC R03). No gate "
                    "verdict, no node completion, no canonical write."),
        "evidence_refs": [
            f"artifacts/worker-004/semct_control_rebase/README.md#{refs['artifacts/worker-004/semct_control_rebase/README.md'][:12]}",
            f"artifacts/worker-004/semct_control_rebase/rebase_report.json#{refs['artifacts/worker-004/semct_control_rebase/rebase_report.json'][:12]}",
            f"artifacts/worker-004/semct_control_rebase/suite_run_report.json#{refs['artifacts/worker-004/semct_control_rebase/suite_run_report.json'][:12]}",
        ],
        "next_falsifier": ("apply the control patch + freeze KEY_MANIFEST, then re-run the canonical suite: "
                           "expect exit 0, valid=true, controls 3/3, mutants 32/11/32; any deviation falsifies "
                           "this submission"),
        "artifacts": {p: h for p, h in refs.items()},
    })

    # ---- 3. validate exactly as ingest does ------------------------------------------
    accepted = []
    for e in ev:
        try:
            validate_event(normalize_event(dict(e), "comms/outbox/worker-004.jsonl"))
        except SchemaError as x:
            raise SystemExit(f"event {e['event_id']} fails schema: {x}")
        accepted.append(e)
    print(f"schema validation ok: {len(accepted)} events")

    # ---- 4. append to outbox ---------------------------------------------------------
    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    with OUTBOX.open("a") as f:
        for e in accepted:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"appended {len(accepted)} events -> {OUTBOX.relative_to(REPO)}")

    # ---- 5. worker checkpoint --------------------------------------------------------
    ck = {
        "checkpoint": 1, "at": now(), "worker": "worker-004", "slot": "004",
        "instance_id": "worker-004-20260912T002827-968807",
        "hours_spent_estimate": 0.5,
        "assignment": ("W004-SEMCT-CONTROL-REBASE-01 (self-selected, no inbox card) - minimal rebase of the "
                       "three frozen semantic controls for ADJ-CONTROL-STALENESS, verified end-to-end"),
        "node_id": "A1", "gate": "G-AUDIT (calibration evidence routing only)",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "status": {
            "delivered": True, "validation_status": "unverified",
            "measurements": {
                "stale_controls_structural_accept": rebase["measurements"]["summary"]["stale_accepted_by_structural"],
                "rebased_controls_all_stage_accept": rebase["measurements"]["summary"]["rebased_accepted_by_all_three_stages"],
                "pinned_canonical_all_stage_accept": rebase["measurements"]["summary"]["canonical_accepted_by_all_three_stages"],
                "rev27_patched": {"exit": suite["conclusion"]["rev27_patched_exit"],
                                  "valid_for_calibration": suite["conclusion"]["rev27_patched_valid_for_calibration"]},
                "rev27_stale": {"exit": suite["conclusion"]["rev27_stale_exit"],
                                "valid_for_calibration": suite["conclusion"]["rev27_stale_valid_for_calibration"]},
                "rev28_patched": {"exit": suite["conclusion"]["rev28_patched_exit"],
                                  "valid_for_calibration": suite["conclusion"]["rev28_patched_valid_for_calibration"]},
                "mutants_unchanged": "32/11/32",
            },
            "blockers_reported": ["KEY_MANIFEST revision instability (A1)", "live F1 WCC semantic R03 (F1)"],
            "no_completion_claim": "worker cannot set done/passed or a gate verdict; no canonical file written",
        },
        "artifacts": refs,
        "events_emitted": [e["event_id"] for e in accepted],
        "falsifier": suite["falsifier"],
        "next_falsifier": ("apply the control patch and freeze KEY_MANIFEST, then re-run the canonical suite; "
                           "expect exit 0 / valid=true / controls 3/3 / mutants 32/11/32"),
        "checkpoint_note": ("worker-local checkpoint; controller-owned runtime/state/current_checkpoint.json "
                            "and checkpoint_log.jsonl were not touched"),
    }
    CHECKPOINT.write_text(json.dumps(ck, indent=1) + "\n")
    with CHECKPOINT_LOG.open("a") as f:
        f.write(json.dumps(ck, sort_keys=True) + "\n")
    print(f"wrote checkpoint {CHECKPOINT.relative_to(REPO)} and appended {CHECKPOINT_LOG.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
