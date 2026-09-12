#!/usr/bin/env python3
"""Emit W086-GFORM-SUITE-REPL-01 deliverables: artifacts, events, checkpoint, manifest.

Idempotency guard: refuses to run if an outbox event with the w086-gform-suite- prefix
already exists. Validates every event against research_map.schemas.validate_event and every
artifact hash against disk before appending. Writes only:
  artifacts/worker-086/gform_suite_rev29/**, reviews/ (none), comms/outbox/worker-086.jsonl,
  runtime/state/w086_gform_suite_rev29_checkpoint.json,
  runtime/state/worker-086_checkpoints.jsonl.
It never writes research_map/, schemas/, artifacts/formulation/ or the events stream.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from research_map.schemas import validate_event  # noqa: E402

OUTBOX = ROOT / "comms/outbox/worker-086.jsonl"
CKPT = ROOT / "runtime/state/w086_gform_suite_rev29_checkpoint.json"
CKPT_LOG = ROOT / "runtime/state/worker-086_checkpoints.jsonl"
TASK = "W086-GFORM-SUITE-REPL-01"
NODE_ID = "F1"
NODE_IDS = ["F1", "F2a", "F2b"]
CLASS_ID = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]

DELIVERABLES = {
    "PREREGISTRATION.md": "preregistration",
    "verify_suite_rev29.py": "deterministic_probe",
    "report.json": "verification_report",
    "run1_gate_test_report.json": "run_report",
    "run1_gate_test_report.txt": "run_report",
    "run2_gate_test_report.json": "determinism_run_report",
    "run2_gate_test_report.txt": "determinism_run_report",
    "run1.stdout.txt": "run_log",
    "run1.stderr.txt": "run_log",
    "run2.stdout.txt": "run_log",
    "run2.stderr.txt": "run_log",
    "frozen_vs_run.diff": "normalized_diff",
    "README.md": "summary",
    "emit_events.py": "event_emitter",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    if OUTBOX.exists() and "w086-gform-suite-" in OUTBOX.read_text(encoding="utf-8", errors="ignore"):
        print("already emitted; refusing duplicate")
        return 1

    report = json.loads((HERE / "report.json").read_text())
    if report["verdict"] != "GATE_SUITE_EVIDENCE_REPRODUCED_EXACTLY" or report["failed_checks"]:
        print(f"refusing to emit a failed replication: {report['verdict']} {report['failed_checks']}")
        return 1

    # manifest of every deliverable file (manifest itself excluded from its own list)
    lines = []
    for rel in sorted(DELIVERABLES):
        lines.append(f"{sha(HERE / rel)}  {rel}")
    (HERE / "MANIFEST.sha256").write_text("\n".join(lines) + "\n")
    hashes = {rel: sha(HERE / rel) for rel in DELIVERABLES}
    hashes["MANIFEST.sha256"] = sha(HERE / "MANIFEST.sha256")

    ts = dt.datetime.now().astimezone().replace(microsecond=0).isoformat()
    tag = ts.replace("-", "").replace(":", "").replace("+", "p")

    def A(rel):
        return f"artifacts/worker-086/gform_suite_rev29/{rel}"

    def ev(rel):
        return f"{A(rel)}#{hashes[rel][:12]}"

    runs = report["runs"]
    frozen = report["frozen_report_sha256"]
    evidence_refs = [
        ev("report.json"), ev("PREREGISTRATION.md"), ev("verify_suite_rev29.py"),
        ev("run1_gate_test_report.json"), ev("run1_gate_test_report.txt"),
        ev("run2_gate_test_report.json"), ev("MANIFEST.sha256"),
        "schemas/af_wcc_vacuum.yaml#d9cebb9404b2e79e",
        "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd308bd",
        "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe7f86",
        "artifacts/formulation/tools/run_gate_tests.py#78509c9eb8b1",
        "artifacts/formulation/evidence/gate_test_report.json#26540a6b43cc",
        "artifacts/formulation/FROZEN.json#815e08079aef",
    ]
    falsifier = report["falsifier"]

    events = [
        {
            "event_id": f"w086-gform-suite-{tag}-status-claim",
            "event_type": "status", "created_at": ts, "actor": "worker-086",
            "node_id": NODE_ID, "node_ids": NODE_IDS, "gate": "G-FORM",
            "class_id": CLASS_ID, "class_ids": CLASS_IDS, "status": "active", "hours": 0.3,
            "summary": (f"No inbox card exists for worker-086 (recycled slot). Took ONE bounded class-bound task {TASK}: "
                        "pristine-sandbox replication of the canonical G-FORM gate suite run_gate_tests.py#78509c9eb8b1 "
                        f"at FROZEN rev29 815e08079aef. The last independent re-run was rev28; no rev29/rev13 re-run existed. "
                        "Read-only on all canonical paths; the suite was executed only inside sandbox/."),
            "evidence_refs": [ev("PREREGISTRATION.md"), ev("verify_suite_rev29.py")],
            "next_falsifier": falsifier,
        },
        {
            "event_id": f"w086-gform-suite-{tag}-review",
            "event_type": "review", "created_at": ts, "actor": "worker-086",
            "reviewer": "worker-086", "node_id": NODE_ID, "node_ids": NODE_IDS,
            "target_id": "G-FORM gate-test evidence at FROZEN rev29 (run_gate_tests.py 78509c9eb8b1)",
            "target_id_full": ("canonical gate suite artifacts/formulation/tools/run_gate_tests.py#78509c9eb8b1 "
                               "and its frozen evidence gate_test_report.json#26540a6b43cc at FROZEN rev29 815e08079aef"),
            "class_id": CLASS_ID, "class_ids": CLASS_IDS, "gate": "G-FORM",
            "review_kind": "evidence_reproducibility_replication", "independent": True,
            "counts_as_full_schema_verdict": False, "counts_as_independent": True,
            "target_sha256": frozen,
            "review_path": A("report.json"), "review_sha256": hashes["report.json"],
            "verdict": "accept", "score": 4.5,
            "score_rationale": ("10/10 pre-registered checks; two sandbox runs byte-identical; normalized run report "
                               "byte-identical to the frozen report; two liveness controls fire; 0/13 pinned inputs moved."),
            "hard_failures": [], "findings": [],
            "positives": ["canonical and mirror schema bytes identical 3/3",
                          "run exit 0 with counts 3/3, 6/6, 31/31, 2/5 and self-application clean",
                          "normalized run report == frozen gate_test_report.json byte-for-byte",
                          "injected defect fires R10; byte-flip fires the pin frame"],
            "scope": ("Reproducibility of the pinned gate-test evidence only; NOT a full-schema review, NOT a rule-semantics "
                      "re-derivation, NOT a gate verdict."),
            "evidence_refs": evidence_refs,
            "falsifier": falsifier,
            "summary": ("Independent accept of the gate-suite evidence at rev29: the frozen report is exactly reproducible "
                        "from the pinned tool, specs and schema bytes in a pristine sandbox; mtime observation only."),
            "not_claimed": report["not_claimed"],
        },
        {
            "event_id": f"w086-gform-suite-{tag}-claim",
            "event_type": "claim", "created_at": ts, "actor": "worker-086",
            "node_id": NODE_ID, "node_ids": NODE_IDS, "gate": "G-FORM",
            "class_id": CLASS_ID, "class_ids": CLASS_IDS,
            "conclusion_type": "stability_result",
            "statement": (
                f"Artifact-and-checker measurement (not a mathematics or physics claim) at FROZEN rev29 815e08079aef, "
                f"schema rev13 (F1 d9cebb9404b2, F2a e9a27996dfd3, F2b b2ab6acb2bbe): a pristine-sandbox re-run of the pinned "
                f"G-FORM suite run_gate_tests.py#78509c9eb8b1 (a) exits 0 and reports PASS with canonical 3/3, null controls 6/6, "
                f"mutants 31/31, rephrased probes 2/5 and clean self-application; (b) is byte-identical across two runs "
                f"(report sha bc14934ff3ca, txt sha f1f229d829d4); (c) reproduces the frozen evidence "
                f"artifacts/formulation/evidence/gate_test_report.json#26540a6b43cc exactly after substituting only the sandbox "
                f"root path (the 423-byte raw difference is the sandbox prefix repeated in 45 schema fields); (d) exercises mirror "
                f"schemas that are byte-identical to the three held canonical schemas; (e) leaves 0/13 pre-registered pinned inputs "
                f"moved and writes nothing outside its own sandbox; and (f) fires both liveness controls (injected WCC visibility "
                f"drop -> R10 fail; byte flip -> drift detected). Observation: the frozen report was rewritten in place at 00:59:53 "
                f"after the 00:57:26 freeze and the independent regeneration reproduces the pinned bytes, so that rewrite was "
                f"content-preserving for this file."
            ),
            "assumptions": [
                "The pinned files at the measured hashes are the intended FROZEN rev29 publication set.",
                "Substituting only the sandbox root path with the repo root path is a semantics-preserving normalization of absolute path fields.",
                "The suite's own rule semantics are not re-derived here; only reproducibility of its output is measured.",
            ],
            "falsifier": falsifier,
            "evidence_refs": evidence_refs,
            "artifact_refs": [A("report.json"), A("verify_suite_rev29.py"), A("run1_gate_test_report.json"),
                              A("PREREGISTRATION.md"), A("MANIFEST.sha256")],
            "promotion_status": "promotion_blocked", "hours": 0.3,
        },
    ]
    for rel, atype in sorted(DELIVERABLES.items()):
        events.append({
            "event_id": f"w086-gform-suite-{tag}-art-{rel.replace('.', '_')}",
            "event_type": "artifact", "created_at": ts, "actor": "worker-086",
            "node_id": NODE_ID, "node_ids": NODE_IDS, "gate": "G-FORM",
            "class_id": CLASS_ID, "class_ids": CLASS_IDS,
            "artifact_type": atype, "path": A(rel), "sha256": hashes[rel],
            "validation_status": "unverified",
            "summary": f"{atype} for {TASK}: sandbox replication of the G-FORM gate suite at FROZEN rev29.",
        })
    events.append({
        "event_id": f"w086-gform-suite-{tag}-status-done",
        "event_type": "status", "created_at": ts, "actor": "worker-086",
        "node_id": NODE_ID, "node_ids": NODE_IDS, "gate": "G-FORM",
        "class_id": CLASS_ID, "class_ids": CLASS_IDS, "status": "done", "hours": 0.3,
        "summary": (f"{TASK} complete at worker level and exiting: verdict GATE_SUITE_EVIDENCE_REPRODUCED_EXACTLY, 10/10 checks, "
                    "2/2 controls fired, 0/13 canonical pins moved, normalized run report byte-equal to the frozen report. "
                    "No node status, no gate verdict and no validation promotion claimed; events are for controller ingest."),
        "evidence_refs": evidence_refs,
        "next_falsifier": ("Re-run verify_suite_rev29.py after any FROZEN bump; at a new revision P4 is expected to fail until a "
                           "new frozen report is published, and this verdict binds only 815e08079aef."),
    })

    # validate + verify artifacts on disk, fail closed
    for e in events:
        validate_event(e)
    for rel in DELIVERABLES:
        if not (HERE / rel).exists():
            print(f"missing deliverable {rel}")
            return 1
        if sha(HERE / rel) != hashes[rel]:
            print(f"hash moved before emit: {rel}")
            return 1

    with OUTBOX.open("a", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"appended {len(events)} events to {OUTBOX}")

    checkpoint = {
        "task": TASK, "actor": "worker-086", "at": ts, "gate": "G-FORM",
        "node_ids": NODE_IDS, "class_ids": CLASS_IDS,
        "verdict": report["verdict"], "failed_checks": report["failed_checks"],
        "checks": [{"id": c["id"], "ok": c["ok"]} for c in report["checks"]],
        "pins": {"tool_run_gate_tests": "78509c9eb8b1548231f3e701245e48084916b044b5d1485bb96006563a59dffa",
                 "frozen": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
                 "f1": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
                 "f2a": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
                 "f2b": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
                 "frozen_report": frozen},
        "deliverable_sha256": hashes,
        "canonical_paths_written": [],
        "next_falsifier": events[-1]["next_falsifier"],
        "not_claimed": report["not_claimed"],
    }
    CKPT.write_text(json.dumps(checkpoint, indent=2) + "\n")
    with CKPT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"task": TASK, "at": ts, "checkpoint": str(CKPT),
                            "checkpoint_sha256": sha(CKPT), "verdict": report["verdict"]}) + "\n")
    print(f"checkpoint {CKPT} sha256 {sha(CKPT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
