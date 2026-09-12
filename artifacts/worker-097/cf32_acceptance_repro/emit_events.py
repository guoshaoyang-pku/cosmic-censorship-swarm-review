#!/usr/bin/env python3
"""Emit worker-097 events for W097-CF32-ACCEPTANCE-REPRO-01 and write the checkpoint.

Validates every event with research_map/schemas.py before appending to the outbox.
No controller ingest, no canonical write, no gate verdict, no node status promotion.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "research_map"))
import schemas  # noqa: E402

TASK_ID = "W097-CF32-ACCEPTANCE-REPRO-01"
_TZ = timezone(timedelta(hours=8))
_NOW = datetime.now(_TZ)
NOW = _NOW.strftime("%Y-%m-%dT%H:%M:%S+08:00")
STAMP = _NOW.strftime("%Y%m%dT%H%M%S")
OUTBOX = os.path.join(ROOT, "comms/outbox/worker-097.jsonl")
CHECKPOINT = os.path.join(ROOT, "runtime/state/w097_cf32_acceptance_repro_checkpoint.json")

BASE = "artifacts/worker-097/cf32_acceptance_repro"
FILES = {
    "report.json": f"{BASE}/report.json",
    "run_repro.py": f"{BASE}/run_repro.py",
    "README.md": f"{BASE}/README.md",
    "PREREGISTRATION.md": f"{BASE}/PREREGISTRATION.md",
    "run_output.txt": f"{BASE}/run_output.txt",
    "SHA256SUMS.txt": f"{BASE}/SHA256SUMS.txt",
}
PINS = {
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/tools/run_acceptance.py": "e544c36d2d168fdf0a9fb19caa333597d8a74a14442b40a356c08004cc9fb4de",
    "artifacts/formulation/tools/check_class_schema.py": "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "artifacts/worker-06/spec_conformance_audit.py": "c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec",
    "artifacts/worker-06/semantic_fixtures/manifest.json": "c102445df3971109101e4d54b609ff1c5bfdf9147ddb1f1b099476a816030deb",
    "artifacts/formulation/evidence/semantic_escape_rebased.json": "7e44de0e3906dc74f607629b88bdc6cbfb438ce39c759e4054156a9345b38292",
    "artifacts/formulation/evidence/acceptance_pipeline_report.json": "9b7d6c8208d3beae2510c5c9c0a4bdaf7ede8adb277cd2a4f6f9cd0fd430f0c6",
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(rel):
    return f"{rel}#sha256:{sha256(os.path.join(ROOT, rel))}"


def main():
    h = {name: sha256(os.path.join(ROOT, rel)) for name, rel in FILES.items()}
    pin_before = {rel: sha256(os.path.join(ROOT, rel)) for rel in PINS}
    pin_drift = {rel: {"expected": PINS[rel], "measured": pin_before[rel]}
                 for rel in PINS if pin_before[rel] != PINS[rel]}
    assert not pin_drift, f"pin drift before emit: {pin_drift}"

    report_ref = ref(FILES["report.json"])
    instr_ref = ref(FILES["run_repro.py"])
    readme_ref = ref(FILES["README.md"])
    pre_ref = ref(FILES["PREREGISTRATION.md"])
    c0_ref = f"schemas/af_scc_c0_vacuum.yaml#sha256:{PINS['schemas/af_scc_c0_vacuum.yaml']}"
    c2_ref = f"schemas/af_scc_c2_vacuum.yaml#sha256:{PINS['schemas/af_scc_c2_vacuum.yaml']}"
    frozen_ref = f"artifacts/formulation/FROZEN.json#sha256:{PINS['artifacts/formulation/FROZEN.json']}"
    run_acc_ref = f"artifacts/formulation/tools/run_acceptance.py#sha256:{PINS['artifacts/formulation/tools/run_acceptance.py']}"
    w06_ref = f"artifacts/worker-06/spec_conformance_audit.py#sha256:{PINS['artifacts/worker-06/spec_conformance_audit.py']}"
    man_ref = f"artifacts/worker-06/semantic_fixtures/manifest.json#sha256:{PINS['artifacts/worker-06/semantic_fixtures/manifest.json']}"
    stored_ref = f"artifacts/formulation/evidence/semantic_escape_rebased.json#sha256:{PINS['artifacts/formulation/evidence/semantic_escape_rebased.json']}"
    stored_report_ref = f"artifacts/formulation/evidence/acceptance_pipeline_report.json#sha256:{PINS['artifacts/formulation/evidence/acceptance_pipeline_report.json']}"

    ev = []
    ev.append({
        "event_id": f"w097-cf32-art-report-{STAMP}",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-097",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK_ID,
        "artifact_type": "cf32_reproduction_report",
        "path": FILES["report.json"],
        "sha256": h["report.json"],
        "validation_status": "unverified",
        "summary": ("CF-32(i) reproduced at T0 (run_acceptance.py exit 3; stored corpus base 1bb78ce9b357 vs live C0 "
                    "b2ab6acb2bbe) and materiality measured: rebasing the same recorded operations onto live C0 gives zero "
                    "per-fixture verdict changes (canonical 30/31, semantic 11/31, union 31/31); the manifest's 32nd mutant "
                    "sem18_provenance_overclaim (indexed-path op dropped by the tool parser) is also union-caught; stage-2 "
                    "auditor and corpus manifest are absent from the FROZEN rev29 pin set; control checklist 8/8."),
        "evidence_refs": [c0_ref, c2_ref, frozen_ref, run_acc_ref, w06_ref, man_ref, stored_ref, stored_report_ref],
        "next_falsifier": ("run_acceptance.py exiting 0 at the T0 pins, a per-fixture verdict differing from the stored corpus "
                           "on a faithful re-run, or any canonical byte moving during the run."),
    })
    ev.append({
        "event_id": f"w097-cf32-art-instrument-{STAMP}",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-097",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK_ID,
        "artifact_type": "audit_instrument",
        "path": FILES["run_repro.py"],
        "sha256": h["run_repro.py"],
        "validation_status": "unverified",
        "summary": ("Stdlib+yaml instrument: independent re-implementation of the recorded path=value op (extended to indexed "
                    "paths), live-C0 sandbox rebase, both-stage verdicts, delta-vs-stored table, parser-equivalence control, "
                    "generated controls, T0/T1 pin map, rebind census, 8-check control checklist."),
        "evidence_refs": [report_ref, readme_ref],
        "next_falsifier": "An instrument control that fails on re-run, or a verdict that changes under the pinned tool hashes.",
    })
    ev.append({
        "event_id": f"w097-cf32-art-readme-{STAMP}",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-097",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK_ID,
        "artifact_type": "audit_summary",
        "path": FILES["README.md"],
        "sha256": h["README.md"],
        "validation_status": "unverified",
        "summary": "Human-readable findings 1-4, control checklist, and the minimal rebind actions for REC-36 item (7).",
        "evidence_refs": [report_ref, instr_ref, pre_ref],
        "next_falsifier": "A cited hash or stage verdict shown to misread the pinned bytes.",
    })
    ev.append({
        "event_id": f"w097-cf32-claim-{STAMP}",
        "event_type": "claim",
        "created_at": NOW,
        "actor": "worker-097",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK_ID,
        "conclusion_type": "stability_result",
        "statement": (
            "Record-audit result, not a gate verdict. At the T0 pins (FROZEN rev29 815e08079aefbc; live canonical C0 "
            "b2ab6acb2bbe; stored corpus 7e44de0e3906; stored report 9b7d6c8208d3), CF-32(i) reproduces exactly: "
            "run_acceptance.py exits 3 at preflight because the corpus binds rev11 C0 1bb78ce9b357 while canonical C0 is "
            "b2ab6acb2bbe, and the stored report still records PASS/union 31/31. Materiality: re-applying the same recorded "
            "mutations to the live C0 in a sandbox reproduces every stored per-fixture verdict (zero deltas; canonical 30/31, "
            "semantic 11/31, union 31/31; generated controls 0 FP), so the defect is a stale hash binding, not a stale "
            "measurement. Two gaps remain: (1) sem18_provenance_overclaim.yaml uses an indexed path "
            "(provenance.sources[0].role) the tool parser drops, so the certified denominator is 31/32 manifest mutants "
            "(with an indexed-path parser the union still catches 32/32; sem18 is canonical=fail, semantic=pass); (2) the "
            "stage-2 auditor spec_conformance_audit.py and the corpus manifest are absent from the FROZEN rev29 pin set, so "
            "the pipeline is not reproducible from pinned bytes even after a hash rebind. All 13 read-only inputs are "
            "byte-identical before/after; control checklist 8/8."
        ),
        "assumptions": [
            "The measured sha256 is the artifact identity; results hold only at the pins in report.json.",
            "A faithful rebase = the recorded path=value operation applied to the live canonical C0; the independent parser matches the tool's parser on 31/31 rows it accepts, and the indexed-path extension is reported separately.",
            "This is worker evidence: only the controller/lead can adjudicate the G-FORM gate, node status, or validation_status.",
        ],
        "falsifier": ("run_acceptance.py exits 0 at the T0 pins; or any per-fixture stage verdict differs from the stored corpus "
                      "under a faithful rebase; or any canonical sha256 differs before vs after the run; or the indexed-path "
                      "extension is shown to mis-apply sem18's recorded op."),
        "evidence_refs": [report_ref, instr_ref, readme_ref, pre_ref, c0_ref, c2_ref, frozen_ref, run_acc_ref,
                          w06_ref, man_ref, stored_ref, stored_report_ref],
        "artifact_refs": [report_ref, instr_ref, readme_ref],
        "non_claims": [
            "no F2b/F2a accept/revise/reject verdict",
            "no gate verdict, node status or validation_status promotion",
            "no canonical write; detector untouched; numerics lock untouched",
        ],
    })
    ev.append({
        "event_id": f"w097-cf32-blocker-{STAMP}",
        "event_type": "blocker",
        "created_at": NOW,
        "actor": "worker-097",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK_ID,
        "description": (
            "CF-32(i) repair-package completeness risk for REC-36 item (7). The acceptance corpus's certified denominator is "
            "ambiguous: the manifest declares 32 leak mutants but the recorded-op parser drops sem18_provenance_overclaim.yaml "
            "(indexed path provenance.sources[0].role), and the stored acceptance_pipeline_report.json reports total=31 with no "
            "exclusion note. In addition the stage-2 rule engine (artifacts/worker-06/spec_conformance_audit.py) and the corpus "
            "source (artifacts/worker-06/semantic_fixtures/manifest.json) are not in the FROZEN rev29 pin set, so a rebind that "
            "only re-generates semantic_escape_rebased.json against live C0 would still not make the pipeline reproducible from "
            "pinned bytes."
        ),
        "needed_to_unblock": (
            "In the single authorized rev14 revision: (a) regenerate the corpus against live C0 b2ab6acb2bbe and state the "
            "denominator explicitly (31 parser-accepted or 32 manifest mutants), either extending the recorded-op parser to "
            "indexed paths or carrying sem18 as a declared exclusion with a reason; (b) add spec_conformance_audit.py and "
            "semantic_fixtures/manifest.json (and the generated rebased_fixtures manifest) to the FROZEN pins; (c) re-run "
            "run_acceptance.py to exit 0 and re-issue acceptance_pipeline_report.json at the new hashes. No worker gate verdict "
            "is requested or implied."
        ),
        "evidence_refs": [report_ref, instr_ref, run_acc_ref, w06_ref, man_ref, stored_ref, stored_report_ref, c0_ref, frozen_ref],
        "no_gate_verdict": True,
    })
    ev.append({
        "event_id": f"w097-cf32-status-{STAMP}",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-097",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK_ID,
        "status": "active",
        "hours": 0.4,
        "summary": (
            "CHECKPOINT + EXIT. One bounded class-bound task taken (no inbox card for worker-097): "
            "W097-CF32-ACCEPTANCE-REPRO-01, independent reproduction and materiality check of CF-32(i) for REC-36 item (7). "
            "Result: CF-32(i) reproduced (exit 3, stale base 1bb78ce9b357 vs live b2ab6acb2bbe); live-byte rebase reproduces "
            "every stored verdict (union 31/31, zero deltas); hidden 32nd manifest mutant sem18 is union-caught via an "
            "indexed-path parser; stage-2 auditor and corpus manifest are absent from the FROZEN pin set; control checklist 8/8; "
            "no canonical drift. No gate verdict, no node promotion, no canonical write."
        ),
        "evidence_refs": [report_ref, instr_ref, readme_ref, c0_ref, frozen_ref],
        "next_falsifier": ("run_acceptance.py exiting 0 at the T0 pins, or a per-fixture verdict differing from the stored corpus "
                           "under a faithful rebase, or any canonical byte moving."),
        "no_gate_verdict": True,
    })

    for e in ev:
        schemas.validate_event(e)

    existing = set()
    if os.path.isfile(OUTBOX):
        with open(OUTBOX, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    existing.add(json.loads(line).get("event_id"))
                except Exception:
                    continue
    new_events = [e for e in ev if e["event_id"] not in existing]
    lines = [json.dumps(e, sort_keys=True) for e in new_events]
    if lines:
        with open(OUTBOX, "a", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")

    pin_after = {rel: sha256(os.path.join(ROOT, rel)) for rel in PINS}
    drift = {rel: pin_after[rel] for rel in PINS if pin_after[rel] != PINS[rel]}

    checkpoint = {
        "schema": "worker-checkpoint/v1",
        "checkpoint_id": f"w097-cf32-{STAMP}",
        "task_id": TASK_ID,
        "worker": "worker-097",
        "actor": "worker-097",
        "created_at": NOW,
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "gate": "G-FORM",
        "artifact_dir": BASE,
        "artifact_sha256": h,
        "emit_events_py_sha256": sha256(os.path.abspath(__file__)),
        "pins": PINS,
        "pin_drift_after_emit": drift,
        "controls_pass": True,
        "control_checklist": "8/8",
        "cf32_i_reproduced": True,
        "run_acceptance_exit": 3,
        "stored_base_sha256": "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
        "live_c0_sha256": PINS["schemas/af_scc_c0_vacuum.yaml"],
        "live_rebase_summary": {"mutants_rebased": 31, "canonical_caught": 30, "semantic_caught": 11, "union_caught": 31},
        "extended_parser_summary": {"mutants_rebased": 32, "canonical_caught": 31, "semantic_caught": 11, "union_caught": 32},
        "stored_vs_live_verdict_delta": [],
        "hidden_manifest_mutant": "sem18_provenance_overclaim.yaml",
        "frozen_pin_gaps": ["artifacts/worker-06/spec_conformance_audit.py",
                            "artifacts/worker-06/semantic_fixtures/manifest.json",
                            "artifacts/formulation/evidence/rebased_fixtures/"],
        "read_only_proof": True,
        "events_emitted": [e["event_id"] for e in new_events],
        "outbox": {"path": "comms/outbox/worker-097.jsonl", "lines_appended": len(new_events),
                   "sha256_after": sha256(OUTBOX)},
        "not_claimed": [
            "no F2b/F2a accept/revise/reject verdict",
            "no gate verdict, node status or validation_status promotion",
            "no canonical write; detector untouched; numerics_lock untouched",
            "no ingest (controller command)",
        ],
        "next_falsifier": ("run_acceptance.py exiting 0 at the T0 pins, a per-fixture verdict differing from the stored corpus "
                           "under a faithful rebase, or any canonical byte moving."),
        "exit": "clean; all events validated by research_map/schemas.py before append; checkpoint written",
    }
    with open(CHECKPOINT, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=1, sort_keys=True)
        f.write("\n")

    print(json.dumps({"events_appended": len(new_events), "checkpoint": CHECKPOINT,
                      "pin_drift": drift, "outbox_sha256": checkpoint["outbox"]["sha256_after"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
