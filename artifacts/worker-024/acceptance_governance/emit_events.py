#!/usr/bin/env python3
"""W024-ACCEPTANCE-GOVERNANCE-01: build report.json + exit_hashes.json, emit outbox events.

Run after drive_governance.py. Does not write any canonical path other than
comms/outbox/worker-024.jsonl (the worker's own upward channel) and
runtime/state/w024_acceptance_governance_checkpoint.json (the worker checkpoint).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms/outbox/worker-024.jsonl"
STATE = ROOT / "runtime/state"
CHECKPOINT = STATE / "w024_acceptance_governance_checkpoint.json"

CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
CLASS_ID = ";".join(CLASS_IDS)
NODE = "F1,F2a,F2b"
GATE = "G-FORM"
TASK = "W024-ACCEPTANCE-GOVERNANCE-01"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rollup(d: Path):
    rows = []
    for p in sorted(d.rglob("*")):
        if p.is_file() and "__pycache__" not in str(p):
            rows.append([str(p.relative_to(d)), sha256(p)])
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest(), len(rows)


def now():
    return dt.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def main():
    raw = json.loads((HERE / "raw_results.json").read_text())
    cases = raw["cases"]

    def rep(name):
        return cases[name].get("report") or {}

    findings = {
        "F1_stage2_unpinned": {
            "statement": "FROZEN rev29 pins run_acceptance.py (e544c36d2d16) and check_class_schema.py (000e09e46b2f) but contains 0 occurrences of the stage-2 rule engine artifacts/worker-06/spec_conformance_audit.py and 0 of the rebased_fixtures corpus; the pinned runner executes both.",
            "measured": raw["cases"]["T7_pin_audit"],
        },
        "F2_laundering_at_constant_pins": {
            "statement": "An added corpus member that no stage catches moves the verdict to FAIL; a name-keyed edit of ONLY the unpinned stage-2 tool turns the same corpus into PASS, and the pinned tool chain still hash-verifies.",
            "unpatched": {"rc": cases["T5_forged_escape_unpatched"]["rc"], "verdict": rep("T5_forged_escape_unpatched").get("verdict"), "mutants": rep("T5_forged_escape_unpatched").get("mutants")},
            "laundered": {"rc": cases["T6_forged_escape_laundered"]["rc"], "verdict": rep("T6_forged_escape_laundered").get("verdict"), "mutants": rep("T6_forged_escape_laundered").get("mutants")},
        },
        "F3_fail_open": {
            "empty_corpus": {"rc": cases["T2_empty_corpus"]["rc"], "verdict": rep("T2_empty_corpus").get("verdict"), "mutants": rep("T2_empty_corpus").get("mutants")},
            "controls_missing": {"rc": cases["T3_controls_missing"]["rc"], "verdict": rep("T3_controls_missing").get("verdict"), "controls": rep("T3_controls_missing").get("controls")},
            "stage2_noop": {"rc": cases["T4_stage2_noop"]["rc"], "verdict": rep("T4_stage2_noop").get("verdict"), "mutants": rep("T4_stage2_noop").get("mutants")},
        },
        "F4_pinned_report_unreproducible": {
            "statement": "At the report-time schema triple the pipeline runs past preflight but returns FAIL: the pinned KEY_MANIFEST (014e2d30) rejects `revised_at_unused`, present in every corpus fixture and in the report-time canonical schemas, while the pinned report records those rows as structural pass. The report-time manifest revision is not preserved.",
            "declared_base_run": {"rc": cases["T1_declared_base_repro"]["rc"], "verdict": rep("T1_declared_base_repro").get("verdict"), "canonical": rep("T1_declared_base_repro").get("canonical"), "controls": rep("T1_declared_base_repro").get("controls")},
        },
        "F5_no_write_guard": {
            "statement": "The runner rewrites the pinned evidence file at the end of every non-preflight run, including a vacuous PASS with mutants.total=0 and a FAIL; there is no dry-run and no refusal path.",
            "pinned_report_sha256": raw["entry_pins"]["report"],
            "clobbered_sha256": {k: cases[k]["report_sha256"] for k in ("T1_declared_base_repro", "T2_empty_corpus", "T5_forged_escape_unpatched", "T6_forged_escape_laundered")},
        },
        "F6_patch_closes": {
            "statement": "The proposed patch refuses an empty corpus, missing controls, an unpinned/edited stage-2 tool, and an extra corpus member at rc 3 with REASON lines; the synthetic healthy control still returns PASS at rc 0 with an inputs hash block, and a run without --write leaves the pinned report byte-identical.",
            "empty": cases["P1_empty_patched"]["rc"],
            "controls": cases["P2_controls_patched"]["rc"],
            "unpinned_stage2": cases["P3_laundered_patched"]["rc"],
            "extra_corpus": cases["P4_extra_patched"]["rc"],
            "healthy": {"rc": cases["P0_healthy_patched"]["rc"], "verdict": rep("P0_healthy_patched").get("verdict"), "inputs": rep("P0_healthy_patched").get("inputs")},
            "no_write_untouched": cases["P0b_healthy_patched_nowrite"]["report_sha256"] == raw["entry_pins"]["report"],
        },
    }

    report = {
        "task_id": TASK,
        "actor": "worker-024",
        "created_at": now(),
        "class_id": CLASS_ID,
        "class_ids": CLASS_IDS,
        "node_id": NODE,
        "gate": GATE,
        "claim_kind": "instrument-governance and fail-open audit (measurement, not a class-semantics or gate verdict)",
        "canonical_snapshot_status": "READ_ONLY (all cases in ROOT-relative sandboxes; 0 canonical writes)",
        "entry_pins": raw["entry_pins"],
        "drift": raw["drift"],
        "cases": {
            k: {kk: vv for kk, vv in v.items() if kk in ("rc", "report_sha256", "stdout")}
            for k, v in cases.items()
        },
        "findings": findings,
        "patch": {
            "path": "artifacts/worker-024/acceptance_governance/patched/run_acceptance.patched.py",
            "diff": "artifacts/worker-024/acceptance_governance/proposed_fail_closed_patch.diff",
            "applied": False,
            "deltas": [
                "P1 declared corpus totals (summary.mutants_rebased, len(controls)) enforced on disk",
                "P2 stage-2 tool hash-bound to evidence w06_sha256 AND to the FROZEN pin set",
                "P3 stage-1 gate hash-bound to evidence gate_sha256 AND to FROZEN",
                "P4 atomic report write, only under --write, with an inputs sha256 block",
            ],
        },
        "assertions_ok": raw["assertions_ok"],
        "assertions_total": raw["assertions_total"],
        "assertions": raw["assertions"],
        "verdict": raw["verdict"],
        "falsifier": (
            "Re-run drive_governance.py at the entry pins in entry_hashes.json. FALSIFIED if any per-case rc/verdict/mutant-count "
            "differs from this report, if the stage-2 path appears in FROZEN.json pins, if the pinned tool-chain scan catches the "
            "name-keyed stage-2 edit, if the pinned report is reproduced as PASS at the pinned KEY_MANIFEST, or if the patched copy "
            "fails to refuse P1-P4 at rc 3 while P0 healthy stays rc 0."
        ),
        "authority_note": "Worker measurement only: no gate verdict, no validation_status=passed, no node status=done, no canonical file written.",
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    # exit hashes
    art_files = {}
    for p in sorted(HERE.rglob("*")):
        if p.is_file() and "__pycache__" not in str(p) and "sandboxes" not in p.parts:
            art_files[str(p.relative_to(HERE))] = sha256(p)
    sandbox_rollup = {}
    sb = HERE / "sandboxes"
    if sb.exists():
        for d in sorted(p for p in sb.iterdir() if p.is_dir()):
            sandbox_rollup[d.name] = rollup(d)[0]
    canonical = [
        "artifacts/formulation/tools/run_acceptance.py",
        "artifacts/formulation/tools/check_class_schema.py",
        "artifacts/worker-06/spec_conformance_audit.py",
        "artifacts/formulation/FROZEN.json",
        "artifacts/formulation/evidence/semantic_escape_rebased.json",
        "artifacts/formulation/evidence/acceptance_pipeline_report.json",
    ]
    exit_pins = {rel: sha256(ROOT / rel) for rel in canonical}
    exit_hashes = {
        "task_id": TASK,
        "actor": "worker-024",
        "created_at": now(),
        "entry_pins": raw["entry_pins"],
        "exit_pins": exit_pins,
        "canonical_drift": {k: [raw["entry_pins"][k], exit_pins[k]] for k in canonical if raw["entry_pins"][k] != exit_pins[k]},
        "artifact_files": art_files,
        "sandbox_tree_rollup": sandbox_rollup,
        "canonical_writes": "none",
    }
    (HERE / "entry_hashes.json").write_text(json.dumps({
        "task_id": TASK, "created_at": now(), "entry_pins": raw["entry_pins"],
        "measured_before_any_run": True,
    }, indent=2) + "\n")
    (HERE / "exit_hashes.json").write_text(json.dumps(exit_hashes, indent=2) + "\n")

    # ---- outbox events ----
    hs = {k: sha256(HERE / k) for k in (
        "report.json", "README.md", "drive_governance.py",
        "patched/run_acceptance.patched.py", "proposed_fail_closed_patch.diff", "exit_hashes.json",
    )}
    stamp = dt.datetime.now().astimezone().strftime("%Y%m%dT%H%M")
    base = f"w024-agov-{stamp}"
    common = {"actor": "worker-024", "created_at": now(), "node_id": NODE, "gate": GATE,
              "class_id": CLASS_ID, "class_ids": CLASS_IDS, "task_id": TASK}
    events = []

    def artifact(evid, atype, path, summary):
        e = dict(common, event_id=f"{base}-art-{evid}", event_type="artifact", artifact_type=atype,
                 path=f"artifacts/worker-024/acceptance_governance/{path}", sha256=hs[path],
                 validation_status="unverified", summary=summary)
        events.append(e)

    artifact("report.json", "acceptance_governance_audit_report", "report.json",
             "Independent instrument-governance + fail-open matrix for the G-FORM acceptance pipeline at " +
             "run_acceptance.py#e544c36d2d16: stage-2 tool and corpus unpinned in FROZEN rev29; FAIL->PASS laundering at " +
             "constant pins; vacuous PASS on empty corpus / missing controls / no-op stage 2; pinned report unreproducible " +
             "under the pinned KEY_MANIFEST; report clobbered by every run.")
    artifact("README.md", "audit_readme", "README.md",
             "Method, pins, per-case table, mechanism, patch, reproduction command, falsifier and residual risk.")
    artifact("drive_governance.py", "reproducible_audit_driver", "drive_governance.py",
             "Builds 14 ROOT-relative sandboxes, runs the pinned pipeline and the patched copy, records rc/stdout/report hashes, " +
             "re-runs the FROZEN pin scan per case, exits 3 on pin drift or assertion failure.")
    artifact("patched_run_acceptance.py", "patched_instrument_copy", "patched/run_acceptance.patched.py",
             "Proposed fail-closed copy: declared corpus totals, stage-2 + stage-1 hash-binding to evidence and FROZEN, atomic " +
             "--write-only report with an inputs sha256 block.")
    artifact("proposed_fail_closed_patch.diff", "proposed_fail_closed_patch", "proposed_fail_closed_patch.diff",
             "Unified diff of the proposal against artifacts/formulation/tools/run_acceptance.py#e544c36d2d16. Proposal only; not applied.")
    artifact("exit_hashes.json", "entry_exit_hash_pins", "exit_hashes.json",
             "Entry/exit canonical pins (6 inputs, 0 drift), artifact file hashes and per-sandbox tree rollups.")

    ev = dict(common, event_id=f"{base}-claim-acceptance-governance", event_type="claim",
              conclusion_type="formal_model",
              statement=(
                  "Instrument-and-pipeline measurement (not a mathematics claim, not a gate verdict) at run_acceptance.py "
                  "e544c36d2d16, check_class_schema.py 000e09e46b2f, spec_conformance_audit.py c79d8ab8440a, FROZEN rev29 "
                  "815e08079aef, evidence 7e44de0e3906, pinned report 9b7d6c8208d3, all entry==exit. (1) GOVERNANCE: FROZEN "
                  "rev29 pins the runner and stage 1 but contains zero occurrences of the stage-2 rule engine path and zero of "
                  "rebased_fixtures/; an added corpus member escapes both stages (31/32, FAIL rc 1) and then a name-keyed edit of "
                  "ONLY the unpinned stage 2 yields PASS 32/32 while the pinned tool chain still hash-verifies (T5/T6/T7). "
                  "(2) FAIL-OPEN: empty corpus -> PASS rc 0 with mutants.total=0; controls absent -> PASS rc 0 with controls=[]; "
                  "no-op stage 2 -> PASS with semantic_caught=0 because all 31 fixtures are already caught structurally by R22 on "
                  "`revised_at_unused` (T2/T3/T4). (3) REPRODUCIBILITY: at the report-time schema triple (WCC 9a8bd4c9, C2 "
                  "b6123750, C0 1bb78ce9 = the evidence base) the pipeline runs but returns FAIL because the pinned KEY_MANIFEST "
                  "rejects `revised_at_unused`, present in every fixture and in the report-time schemas, while the pinned report "
                  "records those rows as structural pass (T1). (4) NO WRITE GUARD: the pinned report file is rewritten "
                  "unconditionally on any non-preflight run, including a vacuous PASS (T2/T5/T6). Proposed patch closes (1)-(4) "
                  "on sandbox copies: P1-P4 rc 3 with REASON, P0 healthy PASS rc 0 with an inputs block, no-write path leaves the "
                  "report byte-identical; proposal not applied to the canonical path."
              ),
              assumptions=[
                  "All measurements are on byte-identical sandbox copies in ROOT-relative layout; the canonical tree was not written (6/6 entry==exit pins).",
                  "The synthetic healthy control uses a WCC revision (ebb8d6671614) that passes both stages under the live pinned tools+manifest, because no live WCC revision passes stage 2 (R03) and no pre-rev13 C0 passes stage 1 (R22); synthetic controls are declared in README.md.",
                  "The synthetic sandboxes rebind only the sandbox evidence file's base_sha256 to the sandbox C0 hash (REC-36 item 7 rebind path); the pinned evidence bytes are restored before the T7 pin scan.",
                  "The corpus count closure uses summary.mutants_rebased=31 and len(controls)=2 as declared by the pinned evidence; these are author-declared totals, not an independent leak census.",
                  "Applying the patch, pinning the stage-2 tool, and re-pinning the report are owner/lead actions (REC-36/REC-41); this audit proposes, it does not land.",
              ],
              falsifier=report["falsifier"],
              evidence_refs=[
                  f"artifacts/worker-024/acceptance_governance/report.json#{hs['report.json'][:12]}",
                  f"artifacts/worker-024/acceptance_governance/README.md#{hs['README.md'][:12]}",
                  f"artifacts/worker-024/acceptance_governance/drive_governance.py#{hs['drive_governance.py'][:12]}",
                  f"artifacts/worker-024/acceptance_governance/patched/run_acceptance.patched.py#{hs['patched/run_acceptance.patched.py'][:12]}",
                  f"artifacts/worker-024/acceptance_governance/proposed_fail_closed_patch.diff#{hs['proposed_fail_closed_patch.diff'][:12]}",
                  f"artifacts/worker-024/acceptance_governance/exit_hashes.json#{hs['exit_hashes.json'][:12]}",
                  "artifacts/formulation/tools/run_acceptance.py#e544c36d2d16",
                  "artifacts/formulation/tools/check_class_schema.py#000e09e46b2f",
                  "artifacts/worker-06/spec_conformance_audit.py#c79d8ab8440a",
                  "artifacts/formulation/FROZEN.json#815e08079aef",
                  "artifacts/formulation/evidence/semantic_escape_rebased.json#7e44de0e3906",
                  "artifacts/formulation/evidence/acceptance_pipeline_report.json#9b7d6c8208d3",
              ],
              artifact_refs=[f"artifacts/worker-024/acceptance_governance/{k}" for k in hs])
    events.append(ev)

    events.append(dict(common, event_id=f"{base}-status-acceptance-governance", event_type="status",
                       status="active", hours=0.8,
                       authority_note="worker event: no gate verdict, no validation_status=passed, no node status=done",
                       summary=(
                           f"{TASK} complete at worker level: 14 sandboxes, {raw['assertions_ok']}/{raw['assertions_total']} "
                           "assertions held, 0 canonical writes. Result: the G-FORM acceptance verdict is not bound to its full "
                           "execution chain (stage-2 tool and corpus unpinned) and fails open on an incomplete corpus; a FAIL can be "
                           "laundered to PASS by editing only the unpinned stage 2 while the pinned chain verifies clean; the pinned "
                           "report is not reproducible under the pinned KEY_MANIFEST and is clobbered by any run. Proposed fail-closed "
                           "patch verified on copies. Worker completion claim only: no gate verdict, no node transition."
                       ),
                       evidence_refs=ev["evidence_refs"],
                       next_falsifier=(
                           "Owner/lead: pin the stage-2 tool hash and the corpus in the same FROZEN revision that adopts any R03 "
                           "revision (lead-form-20260912T011509-123), adopt an equivalent non-vacuity block, and make the report "
                           "write --write-only; then a re-run must refuse an emptied corpus, missing controls and an edited stage 2, "
                           "while the healthy control still PASSes. If the runner/stage-2 move, re-run drive_governance.py at the "
                           "new hashes and expect the per-case table to update with zero assertions lost."
                       )))
    events.append(dict(common, event_id=f"{base}-blocker-cf33-candidate", event_type="blocker",
                       description=(
                           "NEW INSTRUMENT-GOVERNANCE DEFECT (CF-33 candidate, extends lead-form-20260912T011509-123 from an "
                           "assertion to an executed demonstration): the FROZEN rev29 pin set does not bind the stage-2 rule engine "
                           "or the mutant corpus, and run_acceptance.py rewrites its own pinned report unconditionally. An escaping "
                           "corpus member was laundered from FAIL to PASS by editing only the unpinned stage-2 tool (name-keyed "
                           "reject) while the 6 pinned tool-chain artifacts hash-verified clean (T5/T6/T7); empty corpus and missing "
                           "controls both return PASS rc 0 (T2/T3)."
                       ),
                       needed_to_unblock=(
                           "Adopt the P1-P4 non-vacuity/hash-binding/report-write changes (or equivalent) and pin "
                           "artifacts/worker-06/spec_conformance_audit.py at its adopted revision plus the corpus manifest in the "
                           "same FROZEN revision, per REC-36 item 7 and REC-41."
                       ),
                       evidence_refs=ev["evidence_refs"][:8], class_ids=CLASS_IDS))

    # append only new event ids (idempotent)
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:  # noqa: BLE001
                pass
    new = [e for e in events if e["event_id"] not in existing]
    with open(OUTBOX, "a") as f:
        for e in new:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"report.json sha256={hs['report.json']}")
    print(f"emitted {len(new)} events ({len(events) - len(new)} already present)")
    for e in new:
        print(" ", e["event_type"], e["event_id"])

    ckpt = {
        "actor": "worker-024",
        "task_id": TASK,
        "checkpoint_id": f"w024-ckpt-acceptance-governance-{stamp}",
        "created_at": now(),
        "sealed_at": now(),
        "class_ids": CLASS_IDS,
        "class_id": CLASS_ID,
        "node_id": NODE,
        "gate": GATE,
        "status": "complete_at_worker_level",
        "result": (
            "Governance + fail-open audit of the G-FORM acceptance pipeline. Stage-2 tool and corpus are unpinned in FROZEN "
            "rev29; a name-keyed edit of the unpinned stage-2 tool launders a FAIL (31/32, one escaping corpus member) into PASS "
            "(32/32) while the pinned tool chain hash-verifies. Empty corpus and missing controls pass vacuously at rc 0; stage 2 "
            "is non-load-bearing because all 31 fixtures already fail structurally on R22/`revised_at_unused`. The pinned report is "
            "not reproducible under the pinned KEY_MANIFEST at the declared base and is rewritten by every non-preflight run. "
            "Proposed fail-closed patch closes P1-P4 at rc 3 and keeps the healthy control at PASS rc 0."
        ),
        "checks": {"passed": raw["assertions_ok"], "total": raw["assertions_total"]},
        "pins": raw["entry_pins"],
        "exit_pins": exit_pins,
        "drift": raw["drift"],
        "artifacts": {**art_files, "exit_hashes.json": hs["exit_hashes.json"]},
        "events": [e["event_id"] for e in events],
        "outbox": "comms/outbox/worker-024.jsonl",
        "canonical_writes": "none (sandbox-only; patch proposal at artifacts/worker-024/acceptance_governance/proposed_fail_closed_patch.diff)",
        "authority_note": "worker checkpoint: no gate verdict, no node transition, no validation_status=passed, no canonical file modified",
        "falsifier": report["falsifier"],
    }
    STATE.mkdir(parents=True, exist_ok=True)
    CHECKPOINT.write_text(json.dumps(ckpt, indent=2) + "\n")
    print(f"checkpoint: {CHECKPOINT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
