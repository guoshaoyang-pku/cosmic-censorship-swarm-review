#!/usr/bin/env python3
"""Emit worker-027 outbox events + worker checkpoint for W027-CLASSSEP-ARITY-01.

Idempotent: event ids derive from the report_id, so re-running after the events already
exist skips the append. Validates every event with research_map/schemas.py before writing
and re-checks every declared artifact hash on disk.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "artifacts/worker-027/classsep_token_binding"
OUTBOX = ROOT / "comms/outbox/worker-027.jsonl"
STATE = ROOT / "runtime/state"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event, validate_artifact_hash  # noqa: E402


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_local() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def main() -> int:
    report = json.loads((ART / "token_binding_report.json").read_text())
    rid = report["report_id"]
    created = now_local()
    classes = report["class_ids"]
    finding = report["finding"]

    artifact_files = {
        "report": (ART / "token_binding_report.json", "falsification_report"),
        "test_code": (ART / "verify_token_binding.py", "test_code"),
        "ood_corpus": (ART / "ood_corpus/results.json", "regression_fixture"),
        "patch": (ART / "proposed_patch.diff", "proposed_patch"),
        "readme": (ART / "README.md", "summary"),
    }
    hashes = {k: sha256_file(p) for k, (p, _) in artifact_files.items()}
    for k, (p, _) in artifact_files.items():
        assert validate_artifact_hash(str(p), hashes[k]), f"hash mismatch {p}"

    def rel(p: Path) -> str:
        return str(p.relative_to(ROOT))

    events = [
        {
            "event_id": f"{rid}-task", "event_type": "status", "created_at": created,
            "actor": "worker-027", "node_id": "A1", "gate": report["gate"],
            "class_id": classes[0], "class_ids": classes, "status": "active", "hours": 0.1,
            "task_id": report["task_id"],
            "summary": (
                "Took one class-bound task (no assignment card existed for worker-027): "
                "adversarial verification of class_separation token binding. Measured that "
                "_class_tokens matches only four-group AF- tokens, so two frozen ids "
                "(AF-WCC-VAC-GEN, AF-WCC-SCALAR-SPH) are unmatched and unknown three-group "
                "tokens in artifact text are invisible to findings_for_text's soft rule; the "
                "standing 27-fixture regression does not exercise that input class. Proposed "
                "extractor patch measured in-process: OOD corpus DEFECTIVE -> PASS, standing "
                "corpus stays 17/17 + 10/10, 0 newly flagged repository artifacts."
            ),
            "evidence_refs": [f"{rel(ART / 'token_binding_report.json')}#{hashes['report'][:12]}",
                              f"{rel(ART / 'verify_token_binding.py')}#{hashes['test_code'][:12]}"],
            "next_falsifier": finding["falsifier"],
        },
        {
            "event_id": f"{rid}-claim", "event_type": "claim", "created_at": created,
            "actor": "worker-027", "node_id": "A1", "gate": report["gate"],
            "class_id": classes[0], "class_ids": classes, "task_id": report["task_id"],
            "conclusion_type": "formal_model",
            "statement": finding["statement"],
            "assumptions": [
                "The authority is research_map/class_separation.py at sha256 "
                + report["inputs"]["research_map/class_separation.py"]["sha256"]
                + "; any edit voids the measurement.",
                "Channel routing is read as audit_evidence.py routes it: findings prefixed "
                "CLASSSEP-SOFT: are soft, everything else class-separation is hard.",
                "The standing corpus is artifacts/worker-07/class_separation_falsification/"
                "results.json at its pinned sha256; ground truth is its is_class_merge field, "
                "not re-adjudicated here.",
                "The proposed extractor was evaluated by in-process monkeypatch; no repository "
                "file was modified.",
                "Measurement H scans the current map's node artifacts plus schemas/*.yaml and "
                "research_map/formulation_taxonomy.yaml; the report pins every input hash.",
            ],
            "falsifier": finding["falsifier"],
            "evidence_refs": [f"{rel(ART / 'token_binding_report.json')}#{hashes['report'][:12]}",
                              f"{rel(ART / 'ood_corpus/results.json')}#{hashes['ood_corpus'][:12]}",
                              f"{rel(ART / 'proposed_patch.diff')}#{hashes['patch'][:12]}"],
            "artifact_refs": [f"{rel(ART / 'token_binding_report.json')}#{hashes['report'][:12]}",
                              f"{rel(ART / 'verify_token_binding.py')}#{hashes['test_code'][:12]}"],
        },
    ]

    notes = {
        "report": "Primary snapshot: inputs+sha256, measurements A-H, finding W027-F1 "
                  "(CONFIRMED), falsifier, proposed patch evaluated in-process.",
        "test_code": "Deterministic stdlib-only measurement script; writes only the report. "
                     "Re-run: python3 artifacts/worker-027/classsep_token_binding/verify_token_binding.py",
        "ood_corpus": "Proposed OOD regression corpus (not merged into the frozen worker-07 "
                      "corpus): X01 unknown three-group token in artifact text (missed "
                      "unpatched), X02 frozen three-group control.",
        "patch": "Exact one-line patch to _class_tokens; dry-run verified with patch -p1 and "
                 "evaluated by monkeypatch. Not applied: worker cannot author checker changes.",
        "readme": "One-page summary: finding, scope/impact, falsifier, patch, reproduction.",
    }
    for key, (p, atype) in artifact_files.items():
        events.append({
            "event_id": f"{rid}-artifact-{key}", "event_type": "artifact",
            "created_at": created, "actor": "worker-027", "node_id": "A1",
            "gate": report["gate"], "class_id": classes[0], "class_ids": classes,
            "task_id": report["task_id"], "artifact_type": atype, "path": rel(p),
            "sha256": hashes[key], "validation_status": "unverified",
            "note": notes[key],
            "evidence_refs": [f"{rel(ART / 'token_binding_report.json')}#{hashes['report'][:12]}"],
        })

    events.append({
        "event_id": f"{rid}-complete", "event_type": "status", "created_at": created,
        "actor": "worker-027", "node_id": "A1", "gate": report["gate"],
        "class_id": classes[0], "class_ids": classes, "status": "active", "hours": 0.5,
        "task_id": report["task_id"],
        "summary": (
            "W027-CLASSSEP-ARITY-01 complete: artifacts exist on disk and are hash-pinned; "
            "finding W027-F1 measured CONFIRMED at checker sha256 "
            + report["inputs"]["research_map/class_separation.py"]["sha256"][:12]
            + " with an executable falsifier and a patch that repairs the OOD corpus without "
            "regressing the standing one. This is a completion claim, not a node transition "
            "(workers cannot set done/passed or a gate verdict); integration of the OOD fixture "
            "and any checker edit are audit-lead decisions."
        ),
        "evidence_refs": [f"{rel(ART / 'token_binding_report.json')}#{hashes['report'][:12]}",
                          f"{rel(ART / 'README.md')}#{hashes['readme'][:12]}"],
        "next_falsifier": finding["falsifier"],
    })

    for e in events:
        validate_event(e)

    existing = OUTBOX.read_text().splitlines() if OUTBOX.exists() else []
    existing_ids = {json.loads(ln)["event_id"] for ln in existing if ln.strip()}
    new = [e for e in events if e["event_id"] not in existing_ids]
    if new:
        OUTBOX.parent.mkdir(parents=True, exist_ok=True)
        with OUTBOX.open("a") as f:
            for e in new:
                f.write(json.dumps(e, sort_keys=True) + "\n")
    outbox_sha = sha256_file(OUTBOX)

    checkpoint = {
        "checkpoint": 1,
        "at": created,
        "worker": "worker-027",
        "instance": "worker-027-20260912T001656-968807",
        "task_id": report["task_id"],
        "node_id": "A1",
        "gate": report["gate"],
        "class_ids": classes,
        "status": {
            "delivered": True,
            "validation_status": "unverified",
            "finding_status": finding["status"],
            "measurements": {
                "checker_sha256": report["inputs"]["research_map/class_separation.py"]["sha256"],
                "standing_corpus_unpatched": report["measurements"]["F_standing_corpus_unpatched"]["verdict"],
                "standing_corpus_patched": report["measurements"]["F_standing_corpus_patched"]["verdict"],
                "ood_corpus_unpatched": report["measurements"]["G_ood_corpus_unpatched"]["verdict"],
                "ood_corpus_patched": report["measurements"]["G_ood_corpus_patched"]["verdict"],
                "repo_artifacts_newly_flagged_by_patch": report["measurements"]["H_repo_artifact_patch_delta"]["n_newly_flagged"],
                "patch_repairs": report["proposed_patch"]["repairs"],
            },
            "no_completion_claim": "worker cannot set done/passed/gate verdict; no theorem, no physics result",
        },
        "artifacts": {rel(p): hashes[k] for k, (p, _) in artifact_files.items()},
        "events_emitted": [e["event_id"] for e in events],
        "outbox": {"path": rel(OUTBOX), "sha256": outbox_sha},
        "falsifier": finding["falsifier"],
        "next_falsifier": "Audit lead decides on integrating ood_corpus/ into the standing "
                          "regression and on the proposed_patch.diff; after any checker edit, "
                          "re-run verify_token_binding.py and expect the OOD leak to be "
                          "detected; if the unchanged checker detects it, W027-F1 is refuted.",
    }
    cp_path = STATE / "w027_checkpoint_1.json"
    cp_path.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
    with (STATE / "w027_checkpoints.jsonl").open("a") as f:
        f.write(json.dumps({k: checkpoint[k] for k in
                            ("checkpoint", "at", "worker", "task_id", "node_id",
                             "class_ids", "status", "artifacts", "outbox")},
                           sort_keys=True) + "\n")

    print(f"events written : {len(new)} new / {len(events)} total")
    for e in events:
        print(f"  {e['event_id']}  ({e['event_type']})")
    print(f"outbox         : {rel(OUTBOX)} sha256 {outbox_sha[:16]}")
    print(f"checkpoint     : {rel(cp_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
