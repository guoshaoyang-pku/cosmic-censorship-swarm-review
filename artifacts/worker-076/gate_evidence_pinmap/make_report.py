#!/usr/bin/env python3
"""Assemble report.json + SHA256SUMS for task W076-GATE-EVIDENCE-PINMAP-01.

Reads raw/pinmap.json and raw/probe.json (produced by depmap.py and
materiality_probe.py), re-measures every artifact this task produced, and writes a
single hash-bound report.  Read-only over canonical state.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAW = HERE / "raw"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def main() -> int:
    pinmap = json.loads((RAW / "pinmap.json").read_text())
    probe = json.loads((RAW / "probe.json").read_text())
    frozen = ROOT / "artifacts/formulation/FROZEN.json"
    stage2 = ROOT / "artifacts/worker-06/spec_conformance_audit.py"
    manifest = ROOT / "artifacts/worker-06/semantic_fixtures/manifest.json"
    corpus_record = ROOT / "artifacts/formulation/evidence/semantic_escape_rebased.json"
    pinned_report = ROOT / "artifacts/formulation/evidence/acceptance_pipeline_report.json"
    run_acc = ROOT / "artifacts/formulation/tools/run_acceptance.py"

    deps = {d["path"]: d for d in pinmap["dependencies"]}
    unpinned = pinmap["unpinned_reachable"]
    fixtures_unpinned = [p for p in unpinned if p.startswith("artifacts/formulation/evidence/rebased_fixtures/")]
    pv = probe["verdict"]
    pc = probe["pinned_report_comparison"]
    record_declares_live = (probe["instrument_hashes"]["record_declared_w06_sha256"]
                            == probe["instrument_hashes"]["stage2_live"])

    findings = [
        {
            "id": "W076-PINMAP-F1",
            "statement": ("The stage-2 semantic rule engine executed by the FROZEN-pinned acceptance runner is NOT "
                          "pinned: artifacts/worker-06/spec_conformance_audit.py is absent from FROZEN.json rev29's "
                          "50-file manifest, while the pinned runner artifacts/formulation/tools/run_acceptance.py "
                          "executes it as a required stage."),
            "severity": "gate-blocking (instrument governance, same class as CF-26/CF-29)",
            "evidence": [f"artifacts/worker-06/spec_conformance_audit.py#{sha256(stage2)[:12]}",
                         f"artifacts/formulation/tools/run_acceptance.py#{sha256(run_acc)[:12]}",
                         f"artifacts/formulation/FROZEN.json#{sha256(frozen)[:12]}",
                         f"raw/pinmap.json#{sha256(RAW / 'pinmap.json')[:12]}"],
        },
        {
            "id": "W076-PINMAP-F2",
            "statement": ("The stage-2 expectation source artifacts/worker-06/semantic_fixtures/manifest.json "
                          f"({sha256(manifest)[:12]}) is also unpinned."),
            "severity": "governance",
            "evidence": [f"artifacts/worker-06/semantic_fixtures/manifest.json#{sha256(manifest)[:12]}",
                         f"raw/pinmap.json#{sha256(RAW / 'pinmap.json')[:12]}"],
        },
        {
            "id": "W076-PINMAP-F3",
            "statement": (f"{len(fixtures_unpinned)} corpus fixture files under artifacts/formulation/evidence/rebased_fixtures/ "
                          "are read at acceptance time (mutants drive the union-caught verdict; two are controls) and none "
                          "are pinned. Their bytes can be edited with all 50 FROZEN pins unchanged."),
            "severity": "gate-blocking (evidence corpus not byte-bound)",
            "evidence": [f"artifacts/formulation/evidence/rebased_fixtures/#{len(fixtures_unpinned)}files-unpinned",
                         f"raw/pinmap.json#{sha256(RAW / 'pinmap.json')[:12]}"],
        },
        {
            "id": "W076-PINMAP-F4",
            "statement": ("The pinned corpus record declares w06_sha256 = the live stage-2 hash, but the declaration is "
                          "documentary, not enforced: measure_semantic_escape.py only WRITES the field, run_acceptance.py "
                          "invokes the stage-2 path without any hash check, and verify_frozen.py covers only the 50 pinned "
                          f"paths. record_declares_live_stage2_hash={record_declares_live}."),
            "severity": "gate-blocking (declared pin without an enforcing reader)",
            "evidence": [f"artifacts/formulation/evidence/semantic_escape_rebased.json#{sha256(corpus_record)[:12]}",
                         f"raw/probe.json#{sha256(RAW / 'probe.json')[:12]}"],
        },
        {
            "id": "W076-PINMAP-F5",
            "statement": (f"The pinned acceptance report does not reproduce at the live base: pinned verdict "
                          f"{pc['pinned_verdict']} with mutants union {pc['pinned_mutants']['union_caught']}/"
                          f"{pc['pinned_mutants']['total']} (declared base {pc['base_declared_in_pinned_record'][:12]}); "
                          f"regenerating with the pinned generator against the live base "
                          f"{pc['base_live'][:12]} gives union {pc['regenerated_at_live_base']['union_caught']}/"
                          f"{pc['regenerated_at_live_base']['total']} with union escapes "
                          f"{pc['regenerated_at_live_base']['union_escapes']}."),
            "severity": "gate-blocking (pinned gate evidence is not reproducible)",
            "evidence": [f"artifacts/formulation/evidence/acceptance_pipeline_report.json#{sha256(pinned_report)[:12]}",
                         f"artifacts/worker-076/gate_evidence_pinmap/sandbox/semantic_escape_rebased.fresh.json"
                         f"#{sha256(HERE / 'sandbox/semantic_escape_rebased.fresh.json')[:12]}",
                         f"raw/probe.json#{sha256(RAW / 'probe.json')[:12]}"],
        },
        {
            "id": "W076-PINMAP-F6",
            "statement": (f"{len(probe['sweep_stale']['record_mismatches'])} pinned-corpus-record verdict(s) do not reproduce "
                          "on live bytes (the two controls now fail the pinned stage-1 gate on R22 'revised_at_unused', and "
                          "struct12 no longer escapes stage 1). This independently corroborates the L-FORM-04 / stale-corpus "
                          "blocker; the pinned acceptance run still exits 3 at preflight (raw/run_acceptance_preflight.txt)."),
            "severity": "corroboration",
            "evidence": [f"raw/probe.json#{sha256(RAW / 'probe.json')[:12]}",
                         f"raw/run_acceptance_preflight.txt#{sha256(RAW / 'run_acceptance_preflight.txt')[:12]}"],
        },
        {
            "id": "W076-PINMAP-F7",
            "statement": (f"Stage-2 verdicts are instrument-editable: a one-line edit of a sandbox COPY "
                          f"({pv.get('fresh_stage2_verdict_flip_count')}/{probe['sweep_fresh']['rows']} fresh-corpus fixtures "
                          f"flip reject->accept) leaves the live tool and all pins untouched. On the freshly regenerated "
                          f"corpus stage-2 currently adds {pv.get('fresh_stage2_marginal_union_catches')} marginal union "
                          f"catches, while the pinned report claims a marginal catch (union 31/31); the instrument's "
                          f"marginal decisiveness is therefore base-dependent and cannot be read off the pinned report."),
            "severity": "gate-blocking (joint with F1/F4)",
            "evidence": [f"raw/probe.json#{sha256(RAW / 'probe.json')[:12]}",
                         f"artifacts/worker-076/gate_evidence_pinmap/sandbox/spec_conformance_audit.sabotaged.py"
                         f"#{sha256(HERE / 'sandbox/spec_conformance_audit.sabotaged.py')[:12]}"],
        },
        {
            "id": "W076-PINMAP-F8",
            "statement": ("Observation, not attributed to this task: FROZEN-pinned "
                          "artifacts/formulation/tools/check_variant_registry.py drifted during the probe window "
                          f"({probe['frozen_digest_after']['drifted']}), i.e. FROZEN verification races live writers. "
                          "Recorded as evidence of concurrent traffic; this task wrote nothing outside "
                          "artifacts/worker-076/gate_evidence_pinmap/."),
            "severity": "informational",
            "evidence": [f"raw/probe.json#{sha256(RAW / 'probe.json')[:12]}"],
        },
    ]

    report = {
        "schema": "worker-076/gate-evidence-pinmap/report/v1",
        "task_id": "W076-GATE-EVIDENCE-PINMAP-01",
        "worker": "worker-076",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "authority": ("Worker measurement only. This report sets no gate verdict, no validation_status=passed, no "
                      "adoption and no canonical write; only the controller and group leads may move gates."),
        "motivating_blocker": {
            "event_id": "lead-form-20260912T011509-123",
            "actor": "astra-lead-formulation",
            "summary": ("the acceptance pipeline is only half hash-bound: run_acceptance.py is pinned but stage 2 "
                        "artifacts/worker-06/spec_conformance_audit.py has zero FROZEN occurrences"),
        },
        "scope": {
            "node_id": "F1,F2a,F2b",
            "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
            "gate": "G-FORM",
            "seed_set": pinmap["seed_set"],
        },
        "pins": {
            "frozen_path": "artifacts/formulation/FROZEN.json",
            "frozen_sha256": sha256(frozen),
            "frozen_revision": pinmap["frozen_revision"],
            "pinned_files": pinmap["frozen_path_count"],
            "reverse_audit_problems": pinmap["summary"]["frozen_reverse_problems"],
        },
        "method": {
            "step_1": "AST transitive closure over path-like constants from the pinned seeds (depmap.py)",
            "step_2": "pin classification vs FROZEN.files + reverse audit of all 50 pins",
            "step_3": "sandbox corpus regeneration with a path-redirected copy of the pinned generator",
            "step_4": "three-way live sweep: pinned stage-1, live stage-2, single-line-sabotaged sandbox stage-2",
            "inputs_unmodified": True,
        },
        "pinmap_summary": pinmap["summary"],
        "unpinned_reachable": unpinned,
        "probe_verdict": pv,
        "findings": findings,
        "recommendation": [
            "In the same authorized revision that adopts any stage-2 (R03) change, add "
            "artifacts/worker-06/spec_conformance_audit.py to FROZEN.files with its measured sha256; add "
            "artifacts/worker-06/semantic_fixtures/manifest.json if the selftest path is gate evidence.",
            "Make the acceptance runner fail closed: assert live stage-2 sha256 == the declared w06_sha256 (or the new "
            "FROZEN pin) before running mutants, so a stage-2 edit moves a pin or aborts a run.",
            "Disposition the corpus bytes: either pin the 33 rebased_fixtures/*.yaml by hash or bind them to the pinned "
            "generator + base and require regeneration (preflight already fails at the live base).",
            "Re-pin artifacts/formulation/evidence/acceptance_pipeline_report.json only after regeneration at the "
            "rev14/rev30 base; the current pinned report (union 31/31) does not reproduce at live bytes.",
        ],
        "falsifier": probe["falsifier"] + (" Also falsified if any file read by the pipeline is missing from "
                                           "unpinned_reachable/pinmap dependencies, or if the FROZEN reverse audit "
                                           "reports a problem at the measured hashes."),
        "stop_rule": ("Bounded task: one dependency census + one materiality sweep + one checkpoint, then exit. No repair "
                      "attempted (owner-only canonical writes); no gate verdict set."),
        "artifacts": {},
    }

    produced = [HERE / "depmap.py", HERE / "materiality_probe.py", HERE / "make_report.py",
                HERE / "emit_events.py",
                RAW / "pinmap.json", RAW / "probe.json", RAW / "probe_run.log",
                RAW / "run_acceptance_preflight.txt",
                HERE / "sandbox/spec_conformance_audit.sabotaged.py",
                HERE / "sandbox/measure_semantic_escape.sandboxed.py",
                HERE / "sandbox/semantic_escape_rebased.fresh.json"]
    # report.json computed last, so hash the not-yet-written file list, then write, then hash report itself.
    for p in produced:
        if p.exists():
            report["artifacts"][rel(p)] = sha256(p)
    report_path = HERE / "report.json"
    report_path.write_text(json.dumps(report, indent=1) + "\n")
    report["artifacts"][rel(report_path)] = sha256(report_path)

    sums = [f"{sha256(p)}  {rel(p)}" for p in produced + [report_path, HERE / "README.md"] if p.exists()]
    (HERE / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    print(json.dumps({"report": rel(report_path), "sha256": sha256(report_path),
                      "artifacts_hashed": len(sums)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
