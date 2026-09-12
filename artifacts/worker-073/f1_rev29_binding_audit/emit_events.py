#!/usr/bin/env python3
"""W073-F1-REV29-BINDING-AUDIT-01: idempotent emitter for the worker-073 outbox
events and the runtime/state checkpoint. Read-only with respect to every
canonical artifact; appends only to comms/outbox/worker-073.jsonl and writes
only runtime/state/w073_f1rev29_checkpoint_1.json."""
import datetime
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
OUTBOX = os.path.join(REPO, "comms/outbox/worker-073.jsonl")
CKPT = os.path.join(REPO, "runtime/state/w073_f1rev29_checkpoint_1.json")
REVIEW = "reviews/F1-review-worker-073-rev29.json"
ARTIFACTS = [
    "artifacts/worker-073/f1_rev29_binding_audit/run_check_073_f1rev29.py",
    "artifacts/worker-073/f1_rev29_binding_audit/report.json",
    "artifacts/worker-073/f1_rev29_binding_audit/README.md",
    "artifacts/worker-073/f1_rev29_binding_audit/run_stdout.txt",
    REVIEW,
]


def sha(rel):
    with open(os.path.join(REPO, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def main():
    report = json.load(open(os.path.join(REPO, "artifacts/worker-073/f1_rev29_binding_audit/report.json")))
    hashes = {rel: sha(rel) for rel in ARTIFACTS}
    map_sha = sha("research_map/research_map.json")
    ts = now().replace(":", "").replace("-", "")
    report_h = hashes["artifacts/worker-073/f1_rev29_binding_audit/report.json"]
    tool_h = hashes["artifacts/worker-073/f1_rev29_binding_audit/run_check_073_f1rev29.py"]
    readme_h = hashes["artifacts/worker-073/f1_rev29_binding_audit/README.md"]
    stdout_h = hashes["artifacts/worker-073/f1_rev29_binding_audit/run_stdout.txt"]
    review_h = hashes[REVIEW]

    ev = "w073-f1rev29-%s" % ts
    class_ids = ["AF-WCC-VAC-GEN"]
    evidence = [
        "schemas/af_wcc_vacuum.yaml#sha256:d9cebb9404b2",
        "schemas/f1_falsifier_tests.jsonl#sha256:56bcb4b3234b",
        "artifacts/formulation/FROZEN.json#sha256:815e08079aef",
        "artifacts/formulation/VARIANT_REGISTRY.json#sha256:6bac9adea19e",
        "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json#sha256:64b8d6394a04",
        "artifacts/heldout/heldout-09/bases/af_wcc_vacuum.yaml#sha256:cce9c60146d6",
        "research_map/formulation_taxonomy.yaml#sha256:0abb9ed8a961",
        "artifacts/formulation/formulation_taxonomy.yaml#sha256:d7419b4e8963",
        "artifacts/formulation/evidence/taxonomy_consistency.json#sha256:9e335e9ba1bf",
        "artifacts/worker-073/f1_rev29_binding_audit/report.json#sha256:%s" % report_h[:16],
        "artifacts/worker-073/f1_rev29_binding_audit/run_check_073_f1rev29.py#sha256:%s" % tool_h[:16],
    ]
    artifacts_ref = [
        "artifacts/worker-073/f1_rev29_binding_audit/report.json#sha256:%s" % report_h[:16],
        "artifacts/worker-073/f1_rev29_binding_audit/run_check_073_f1rev29.py#sha256:%s" % tool_h[:16],
    ]
    falsifier = (
        "Re-run artifacts/worker-073/f1_rev29_binding_audit/run_check_073_f1rev29.py at the pinned frame: a "
        "corpus whose every row binds the live F1 pin, any unbracketed in-block inversion, a non-firing "
        "control, or a moved required pin each voids part of this; a byte change to any frame file voids the "
        "verdict for that file."
    )

    events = [
        {
            "event_id": ev + "-status-task",
            "event_type": "status",
            "created_at": now(),
            "actor": "worker-073",
            "node_id": "F1",
            "gate": "G-FORM",
            "class_id": "AF-WCC-VAC-GEN",
            "class_ids": class_ids,
            "task_id": "W073-F1-REV29-BINDING-AUDIT-01",
            "status": "active",
            "hours": 0.5,
            "summary": (
                "No inbox card exists for worker-073 (recycled slot). Took ONE bounded class-bound task: "
                "independent read-only post-repair audit of F1 at the live pin d9cebb9404b2 / FROZEN rev29, "
                "adjudicating worker-061 HF-W061-VAR-01/02 and censusing the binding of "
                "schemas/f1_falsifier_tests.jsonl. Result: revise 3.0, hard failure F1-073-01 (25/25 corpus "
                "rows still bind the superseded rev12 cce9c60146d6 and FROZEN rev27; 3 rows probe rev13-edited "
                "leaves); HF-W061-VAR-01 not reproducible at the pin (positive control on rev12 fires); "
                "L-FORM-03 repaired in the reviewable satellites. 32 checks, 6/6 controls fired, frame stable. "
                "No gate verdict, node status or validation_status is set."
            ),
            "evidence_refs": evidence,
            "next_falsifier": falsifier,
        },
        {
            "event_id": ev + "-artifact-report",
            "event_type": "artifact",
            "created_at": now(),
            "actor": "worker-073",
            "node_id": "F1",
            "gate": "G-FORM",
            "class_id": "AF-WCC-VAC-GEN",
            "class_ids": class_ids,
            "task_id": "W073-F1-REV29-BINDING-AUDIT-01",
            "artifact_type": "f1_rev29_binding_audit_report",
            "path": "artifacts/worker-073/f1_rev29_binding_audit/report.json",
            "sha256": report_h,
            "validation_status": "unverified",
            "summary": (
                "Frame-bound audit report: 32 checks, 6/6 controls fired, required pins stable during the run. "
                "Findings: F1-073-01 blocking (corpus binding stale at rev13), F1-073-02 resolved "
                "(HF-W061-VAR-01 not reproducible at the pin; rev12 control reproduces it), F1-073-03 info "
                "(L-FORM-03 repaired in registry+delta; residual only in byte-frozen F0 artifacts), F1-073-04 "
                "info (f0_binding chain resolves)."
            ),
            "reproduce": "python3 artifacts/worker-073/f1_rev29_binding_audit/run_check_073_f1rev29.py",
            "evidence_refs": evidence,
            "falsifier": falsifier,
        },
        {
            "event_id": ev + "-artifact-instrument",
            "event_type": "artifact",
            "created_at": now(),
            "actor": "worker-073",
            "node_id": "F1",
            "gate": "G-FORM",
            "class_id": "AF-WCC-VAC-GEN",
            "class_ids": class_ids,
            "task_id": "W073-F1-REV29-BINDING-AUDIT-01",
            "artifact_type": "f1_rev29_binding_audit_instrument",
            "path": "artifacts/worker-073/f1_rev29_binding_audit/run_check_073_f1rev29.py",
            "sha256": tool_h,
            "validation_status": "unverified",
            "summary": (
                "Own deterministic read-only checker: strict duplicate-key YAML loader, bracket-aware "
                "predicate-inversion regex over the class_identity_variants block, top-level-key token census, "
                "f0_binding hash-chain resolution, 25-row corpus binding census, 6 controls, snapshot frame, "
                "fail-closed exit 3 on required-pin drift, exit 2 on control failure."
            ),
            "reproduce": "python3 artifacts/worker-073/f1_rev29_binding_audit/run_check_073_f1rev29.py",
            "evidence_refs": evidence,
            "falsifier": falsifier,
        },
        {
            "event_id": ev + "-review-f1",
            "event_type": "review",
            "created_at": now(),
            "actor": "worker-073",
            "node_id": "F1",
            "gate": "G-FORM",
            "class_id": "AF-WCC-VAC-GEN",
            "class_ids": class_ids,
            "task_id": "W073-F1-REV29-BINDING-AUDIT-01",
            "target_id": "F1",
            "reviewer": "worker-073",
            "reviewed_path": "schemas/af_wcc_vacuum.yaml",
            "reviewed_sha256": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
            "verdict": "revise",
            "score": 3.0,
            "hard_failures": ["F1-073-01"],
            "findings": [f["finding"] for f in report["findings"]],
            "artifact_refs": artifacts_ref,
            "evidence_refs": evidence,
            "counts_as_full_schema_verdict": True,
            "counts_toward_gate_accept": False,
            "independence_note": report["verdict"]["independence_note"],
            "scope_note": (
                "Class-bound read-only verdict on F1 at d9cebb9404b2 / FROZEN rev29 plus the HF-W061-VAR-01 "
                "adjudication and corpus-binding census. Not a gate verdict, not a node status, not a "
                "validation_status, and not one of the two blind full-schema accepts G-FORM requires."
            ),
            "falsifier": falsifier,
        },
        {
            "event_id": ev + "-claim-binding",
            "event_type": "claim",
            "created_at": now(),
            "actor": "worker-073",
            "node_id": "F1",
            "gate": "G-FORM",
            "class_id": "AF-WCC-VAC-GEN",
            "class_ids": class_ids,
            "statement": (
                "At the audited frame (F1 schemas/af_wcc_vacuum.yaml sha256 d9cebb9404b2, revision 13; "
                "FROZEN.json sha256 815e08079aef, revision 29), F1's gate-evidence corpus "
                "schemas/f1_falsifier_tests.jsonl (sha256 56bcb4b3234b) does not satisfy the stated G-FORM "
                "acceptance criterion: all 25 rows carry binding_sha256=cce9c60146d6 (F1 rev12) and "
                "binding_frozen_revision=27, and 3 rows (F1-AMB-11, F1-AMB-17, F1-AMB-23) decide leaves that "
                "the rev13 repair edited. At the same frame, worker-061's HF-W061-VAR-01 is not reproducible: "
                "the variant-SET relation reads 'strictly WEAKER' and the inversion detector returns 0 "
                "unbracketed hits, while the superseded rev12 copy reproduces the quoted defect under the same "
                "detector. L-FORM-03 is repaired in VARIANT_REGISTRY.json and the variant-SET delta; the older "
                "direction survives only in byte-frozen F0 artifacts outside F1's bytes. This claim asserts no "
                "theorem and sets no gate verdict."
            ),
            "conclusion_type": "formal_model",
            "assumptions": [
                "the acceptance criterion is the one stated in assignment audit-r2-F1-a (astra-lead-audit)",
                "the artifact bytes at the cited hashes are the bytes audited (frame snapshotted and re-measured)",
                "research_map/research_map.json is not evidence; only the pinned files are",
            ],
            "falsifier": falsifier,
            "artifact_refs": artifacts_ref,
            "evidence_refs": evidence,
        },
        {
            "event_id": ev + "-status-complete",
            "event_type": "status",
            "created_at": now(),
            "actor": "worker-073",
            "node_id": "F1",
            "gate": "G-FORM",
            "class_id": "AF-WCC-VAC-GEN",
            "class_ids": class_ids,
            "task_id": "W073-F1-REV29-BINDING-AUDIT-01",
            "status": "done",
            "hours": 0.6,
            "summary": (
                "Worker lifecycle complete (completion claim for the deliverable only; not a node done and not "
                "a gate verdict). One class-bound task delivered: F1 rev29 post-repair binding audit. Artifacts: "
                "report.json sha256 %s, run_check_073_f1rev29.py sha256 %s, README.md sha256 %s, "
                "run_stdout.txt sha256 %s; review %s sha256 %s. Checkpoint "
                "runtime/state/w073_f1rev29_checkpoint_1.json. Findings: F1-073-01 blocking, F1-073-02 "
                "resolved, F1-073-03/04 info; 6/6 controls fired; frame stable. Canonical artifacts, the "
                "numerics lock and all other workers' files untouched. Worker exits now."
                % (report_h[:16], tool_h[:16], readme_h[:16], stdout_h[:16], REVIEW, review_h[:16])
            ),
            "evidence_refs": evidence + ["runtime/state/w073_f1rev29_checkpoint_1.json"],
            "next_falsifier": falsifier,
            "completion_scope": "worker lifecycle only; not a node done / gate verdict",
        },
    ]

    # idempotent append
    existing = set()
    if os.path.exists(OUTBOX):
        for line in open(OUTBOX, encoding="utf-8"):
            line = line.strip()
            if line.startswith("{"):
                try:
                    existing.add(json.loads(line).get("event_id"))
                except Exception:
                    pass
    written = []
    with open(OUTBOX, "a", encoding="utf-8") as fh:
        for e in events:
            if e["event_id"] in existing:
                continue
            line = json.dumps(e, sort_keys=True)
            json.loads(line)
            fh.write(line + "\n")
            written.append(e["event_id"])

    ckpt = {
        "checkpoint_id": "w073-ckpt-f1-rev29-binding-%s" % ts,
        "actor": "worker-073",
        "agent_id": "worker-073",
        "created_at": now(),
        "measured_at": now(),
        "task": (
            "One class-bound task: independent post-repair binding audit of F1 (AF-WCC-VAC-GEN) at "
            "schemas/af_wcc_vacuum.yaml d9cebb9404b2 / FROZEN rev29, with HF-W061-VAR-01/02 adjudication and a "
            "binding census of schemas/f1_falsifier_tests.jsonl; own tooling, 6 controls, snapshot frame."
        ),
        "node_id": "F1",
        "gate": "G-FORM",
        "class_ids": class_ids,
        "authority_note": "worker event; cannot set node status=done, validation_status=passed, or a gate verdict",
        "assignment_ref": "none (no inbox card for worker-073; task self-selected from the live G-FORM gap)",
        "artifacts": hashes,
        "reviewed_pins": report["frame"]["live_hashes_t0"],
        "verdict": {
            "verdict": "revise",
            "score": 3.0,
            "hard_failures": ["F1-073-01"],
            "counts_toward_gate_accept": False,
            "findings": [{"id": f["id"], "severity": f["severity"]} for f in report["findings"]],
        },
        "controls": {
            "all_fired": all(c["fired"] for c in report["controls"]),
            "n": len(report["controls"]),
            "ids": [c["id"] for c in report["controls"]],
        },
        "checks": {
            "n": report["counts"]["checks"],
            "failed": report["counts"]["checks_failed"],
        },
        "pins_stable_during_run": report["frame"]["moved_during_run"] == [],
        "map_sha256_measured": map_sha,
        "events_emitted": written,
        "prescription": (
            "Rebind the 25 corpus rows to F1 d9cebb9404b2 + FROZEN rev29 and re-derive F1-AMB-11/17/23, or "
            "record an explicit controller adjudication of immateriality and amend the acceptance criterion."
        ),
        "falsifier": falsifier,
    }
    with open(CKPT, "w", encoding="utf-8") as fh:
        json.dump(ckpt, fh, indent=2, sort_keys=True)
        fh.write("\n")

    print(json.dumps({
        "events_written": written,
        "events_already_present": [e["event_id"] for e in events if e["event_id"] in existing],
        "checkpoint": CKPT,
        "checkpoint_sha256": sha("runtime/state/w073_f1rev29_checkpoint_1.json"),
        "hashes": hashes,
        "outbox_lines_total": sum(1 for l in open(OUTBOX, encoding="utf-8") if l.strip()),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
