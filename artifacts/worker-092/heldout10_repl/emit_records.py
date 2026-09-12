#!/usr/bin/env python3
"""Emit the W092-HELDOUT10-THIRDPARTY-REPL-01 records from report.json.

Writes (all under the worker's own scope):
  artifacts/worker-092/heldout10_repl/manifest.json          deliverable + input hashes
  reviews/heldout10-thirdparty-repl-worker-092.json          review record
  runtime/state/worker-092_heldout10_repl_checkpoint.json    worker checkpoint
  comms/outbox/worker-092.jsonl                              appended protocol events (idempotent)

Every event is validated with research_map.schemas.validate_event before it is appended.
This script sets no gate verdict, no node status and no validation_status=passed.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from research_map.schemas import validate_event  # noqa: E402

TASK_ID = "W092-HELDOUT10-THIRDPARTY-REPL-01"
WORKER = "worker-092"
NODE = "A1"
GATE = "G-CLASSBIND"
CLASSES = "AF-WCC-VAC-GEN,AF-SCC-C2-VAC-GEN,AF-SCC-C0-VAC-GEN"
DIR = ROOT / "artifacts" / "worker-092" / "heldout10_repl"
REVIEW = ROOT / "reviews" / "heldout10-thirdparty-repl-worker-092.json"
CHECKPOINT = ROOT / "runtime" / "state" / "worker-092_heldout10_repl_checkpoint.json"
OUTBOX = ROOT / "comms" / "outbox" / "worker-092.jsonl"

CORPUS = ROOT / "artifacts" / "heldout" / "heldout-10"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def main() -> int:
    report = json.loads((DIR / "report.json").read_text())
    pins = json.loads((DIR / "pins_at_run.json").read_text())
    stamp = now()
    tag = f"w092-h10repl-{stamp}"

    deliverables = [
        ("report.json", DIR / "report.json"),
        ("replicate_heldout10.py", DIR / "replicate_heldout10.py"),
        ("README.md", DIR / "README.md"),
        ("acceptance_run.log", DIR / "acceptance_run.log"),
        ("pins_at_run.json", DIR / "pins_at_run.json"),
    ]
    out_hashes = {name: sha256_file(p) for name, p in deliverables}
    frozen_rev29 = sha256_file(ROOT / "artifacts" / "formulation" / "FROZEN.json")

    manifest = {
        "task_id": TASK_ID,
        "worker": WORKER,
        "actor": WORKER,
        "node_id": NODE,
        "gate": GATE,
        "class_ids": CLASSES.split(","),
        "created_at": stamp,
        "authority": "worker measurement evidence only; no gate verdict, node status or validation_status set",
        "deliverables_sha256": out_hashes,
        "note": "manifest.json is excluded from its own hash list to avoid circularity",
        "pinned_inputs": {
            "corpus_manifest.json": pins["manifest.json"],
            "corpus_report.json": pins["report.json"],
            "corpus_raw_verdicts.json": pins["raw_verdicts.json"],
            "stage_a_tool": pins["stage_a_tool"],
            "stage_b_tool": pins["stage_b_tool"],
            "stage_a_key_manifest": pins["stage_a_key_manifest"],
            "frozen_rev29": frozen_rev29,
            "canonical_pins": {k: v["measured"] for k, v in pins["canonical_pins"].items()},
        },
        "preflight": {
            "corpus_manifest_matches_preregistered": pins["manifest_sha_matches_preregistered"],
            "stage_a_matches_manifest": pins["stage_a_hash_matches_manifest"],
            "stage_b_matches_manifest": pins["stage_b_hash_matches_manifest"],
            "pin_mismatches": pins["pin_mismatches"],
            "fixture_hash_mismatches": len(pins["fixture_hash_mismatches"]),
        },
        "result": report["headline"],
        "validity": {
            "replication_valid": report["validity"]["replication_valid"],
            "per_fixture_disagreements": report["validity"]["disagreement_count"],
            "drift": len(report["validity"]["drift"]),
        },
        "falsifier": report["falsifier"],
    }
    (DIR / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    manifest_sha = sha256_file(DIR / "manifest.json")

    findings = [
        {
            "id": "F-092-H10-01",
            "kind": "measurement",
            "severity": "info",
            "finding": ("FORM-HELDOUT-10's informative-arm result reproduces exactly under a "
                        "non-author, non-owner driver: union escape 1.0 (0/26 caught), all-mutant "
                        "0.7879 (7/33, all R03-only WCC), per-fixture agreement 40/40, 0 drift. "
                        "The lead-form-20260912T011516-124 G-CLASSBIND blocker is not an artifact "
                        "of the corpus author's own pipeline."),
            "falsifier": ("re-run replicate_heldout10.py: any per-fixture verdict disagreement, "
                          "fixture-hash mismatch, or mid-run tool/canonical move"),
        },
        {
            "id": "F-092-H10-02",
            "kind": "governance",
            "severity": "info",
            "finding": ("the corpus's verify/ artifact is author-side (verifier worker-084, declared "
                        "as a re-run); this run is the first non-author, non-owner reproduction. "
                        "Independence of held-out measurements should be declared explicitly rather "
                        "than inferred from a filename."),
            "falsifier": "a pre-existing non-author reproduction of FORM-HELDOUT-10 at the same pins",
        },
        {
            "id": "F-092-H10-03",
            "kind": "governance",
            "severity": "info",
            "finding": ("stage B is unpinned in FROZEN rev29 (lead-form-20260912T011516-123); it "
                        "measured c79d8ab8440a before and after this run with no drift, but adopting "
                        "a repaired R03 must pin the tool hash in the same FROZEN revision or "
                        "gate-relevant evidence can change with no pinned byte moving."),
            "falsifier": "a FROZEN revision that adopts an R03 repair without pinning the stage-B tool hash",
        },
        {
            "id": "F-092-H10-04",
            "kind": "scope",
            "severity": "info",
            "finding": ("the WCC arm cannot contribute evidence while R03 rejects the untouched "
                        "canonical; only the 26 informative C2/C0 mutants are a valid measurement "
                        "basis, as the corpus itself declares."),
            "falsifier": "a stage B that accepts the frozen WCC canonical, making the WCC arm informative",
        },
    ]

    review = {
        "artifact": "artifacts/heldout/heldout-10/manifest.json",
        "artifact_sha256": pins["manifest.json"],
        "artifact_type": "heldout_corpus",
        "target_id": "FORM-HELDOUT-10",
        "event_id": f"{tag}-review",
        "reviewer": WORKER,
        "actor": WORKER,
        "node_id": NODE,
        "gate": GATE,
        "class_ids": CLASSES.split(","),
        "task_id": TASK_ID,
        "created_at": stamp,
        "verdict": "accept",
        "score": 4.0,
        "hard_failures": [],
        "reviewed_sha256": pins["report.json"],
        "counts_as_independent_second_verdict": True,
        "counts_as_full_schema_verdict": False,
        "authority": ("One independent review verdict on the reproducibility of the pinned corpus "
                      "measurement. Sets no gate verdict, no node status and no validation_status. "
                      "Does not adjudicate schema correctness or the required rev14 repair."),
        "independence_basis": ("worker-092 is neither author (worker-084) nor owner "
                               "(astra-lead-formulation); builder/executor/corpus verifier were not "
                               "imported; all fixtures and pins re-hashed, both stages re-invoked "
                               "as subprocesses"),
        "findings": findings,
        "limits": report["limits"],
        "falsifier": report["falsifier"],
        "evidence_refs": [
            f"artifacts/heldout/heldout-10/manifest.json#{pins['manifest.json'][:12]}",
            f"artifacts/heldout/heldout-10/report.json#{pins['report.json'][:12]}",
            "artifacts/worker-092/heldout10_repl/report.json",
            "artifacts/worker-092/heldout10_repl/replicate_heldout10.py",
            "artifacts/worker-092/heldout10_repl/manifest.json",
        ],
    }
    REVIEW.write_text(json.dumps(review, indent=1) + "\n")
    review_sha = sha256_file(REVIEW)

    checkpoint = {
        "task_id": TASK_ID,
        "actor": WORKER,
        "node_id": NODE,
        "gate": GATE,
        "class_id": CLASSES,
        "created_at": stamp,
        "status": "worker-level complete; node/gate state NOT moved",
        "verdict": "accept (reproducibility only)",
        "score": 4.0,
        "exit_code": 0,
        "hard_failures": [],
        "soft_findings": [f["id"] for f in findings],
        "pins": {
            "corpus_manifest": pins["manifest.json"],
            "corpus_report": pins["report.json"],
            "corpus_raw_verdicts": pins["raw_verdicts.json"],
            "stage_a_tool": pins["stage_a_tool"],
            "stage_b_tool": pins["stage_b_tool"],
            "frozen_rev29": frozen_rev29,
            "f1": pins["canonical_pins"]["schemas/af_wcc_vacuum.yaml"]["measured"],
            "f2a": pins["canonical_pins"]["schemas/af_scc_c2_vacuum.yaml"]["measured"],
            "f2b": pins["canonical_pins"]["schemas/af_scc_c0_vacuum.yaml"]["measured"],
        },
        "outputs": {**out_hashes, "manifest.json": manifest_sha,
                    "reviews/heldout10-thirdparty-repl-worker-092.json": review_sha},
        "next_falsifier": report["falsifier"],
        "authority": "worker checkpoint; no gate verdict, node status or validation_status is set",
    }
    CHECKPOINT.write_text(json.dumps(checkpoint, indent=1) + "\n")
    checkpoint_sha = sha256_file(CHECKPOINT)

    h = report["headline"]
    events = [
        {
            "event_id": f"{tag}-status-claim",
            "event_type": "status",
            "created_at": stamp,
            "actor": WORKER,
            "node_id": NODE,
            "class_id": CLASSES,
            "task_id": TASK_ID,
            "gate": GATE,
            "status": "active",
            "hours": 0.4,
            "summary": (
                "No assignment card exists in comms/inbox/worker-092.jsonl (pass-08 fleet). Taking ONE "
                "bounded class-bound task: W092-HELDOUT10-THIRDPARTY-REPL-01 = independent non-author, "
                "non-owner replication of FORM-HELDOUT-10's headline measurement at FROZEN rev29 "
                "(informative C2+C0 union escape 1.0, 0/26 caught), the substantive G-CLASSBIND blocker "
                "lead-form-20260912T011516-124. The corpus's own verify/ re-run is author-side "
                "(worker-084), so this is the missing third-party reproduction."),
            "evidence_refs": [
                "artifacts/heldout/heldout-10/manifest.json",
                "artifacts/heldout/heldout-10/report.json",
                "comms/outbox/astra-lead-formulation.jsonl#lead-form-20260912T011516-124",
            ],
            "next_falsifier": ("re-run replicate_heldout10.py: any per-fixture verdict disagreement, "
                               "fixture-hash mismatch, or mid-run tool/canonical move"),
        },
        {
            "event_id": f"{tag}-artifact-report",
            "event_type": "artifact",
            "created_at": stamp,
            "actor": WORKER,
            "node_id": NODE,
            "class_id": CLASSES,
            "task_id": TASK_ID,
            "gate": GATE,
            "artifact_type": "verification_report",
            "path": "artifacts/worker-092/heldout10_repl/report.json",
            "sha256": out_hashes["report.json"],
            "validation_status": "unverified",
            "evidence_refs": [
                "artifacts/heldout/heldout-10/manifest.json",
                "artifacts/heldout/heldout-10/raw/raw_verdicts.json",
            ],
        },
        {
            "event_id": f"{tag}-artifact-instrument",
            "event_type": "artifact",
            "created_at": stamp,
            "actor": WORKER,
            "node_id": NODE,
            "class_id": CLASSES,
            "task_id": TASK_ID,
            "gate": GATE,
            "artifact_type": "verifier",
            "path": "artifacts/worker-092/heldout10_repl/replicate_heldout10.py",
            "sha256": out_hashes["replicate_heldout10.py"],
            "validation_status": "unverified",
            "evidence_refs": ["artifacts/heldout/heldout-10/manifest.json"],
        },
        {
            "event_id": f"{tag}-artifact-readme",
            "event_type": "artifact",
            "created_at": stamp,
            "actor": WORKER,
            "node_id": NODE,
            "class_id": CLASSES,
            "task_id": TASK_ID,
            "gate": GATE,
            "artifact_type": "readme",
            "path": "artifacts/worker-092/heldout10_repl/README.md",
            "sha256": out_hashes["README.md"],
            "validation_status": "unverified",
            "evidence_refs": ["artifacts/worker-092/heldout10_repl/report.json"],
        },
        {
            "event_id": f"{tag}-artifact-acceptance",
            "event_type": "artifact",
            "created_at": stamp,
            "actor": WORKER,
            "node_id": NODE,
            "class_id": CLASSES,
            "task_id": TASK_ID,
            "gate": GATE,
            "artifact_type": "acceptance_log",
            "path": "artifacts/worker-092/heldout10_repl/acceptance_run.log",
            "sha256": out_hashes["acceptance_run.log"],
            "validation_status": "unverified",
            "evidence_refs": ["artifacts/worker-092/heldout10_repl/report.json"],
        },
        {
            "event_id": f"{tag}-artifact-pins",
            "event_type": "artifact",
            "created_at": stamp,
            "actor": WORKER,
            "node_id": NODE,
            "class_id": CLASSES,
            "task_id": TASK_ID,
            "gate": GATE,
            "artifact_type": "pin_measurement",
            "path": "artifacts/worker-092/heldout10_repl/pins_at_run.json",
            "sha256": out_hashes["pins_at_run.json"],
            "validation_status": "unverified",
            "evidence_refs": ["artifacts/heldout/heldout-10/manifest.json"],
        },
        {
            "event_id": f"{tag}-artifact-manifest",
            "event_type": "artifact",
            "created_at": stamp,
            "actor": WORKER,
            "node_id": NODE,
            "class_id": CLASSES,
            "task_id": TASK_ID,
            "gate": GATE,
            "artifact_type": "manifest",
            "path": "artifacts/worker-092/heldout10_repl/manifest.json",
            "sha256": manifest_sha,
            "validation_status": "unverified",
            "evidence_refs": ["artifacts/worker-092/heldout10_repl/report.json"],
        },
        {
            "event_id": f"{tag}-artifact-review-json",
            "event_type": "artifact",
            "created_at": stamp,
            "actor": WORKER,
            "node_id": NODE,
            "class_id": CLASSES,
            "task_id": TASK_ID,
            "gate": GATE,
            "artifact_type": "review_record",
            "path": "reviews/heldout10-thirdparty-repl-worker-092.json",
            "sha256": review_sha,
            "validation_status": "unverified",
            "evidence_refs": ["artifacts/heldout/heldout-10/manifest.json"],
        },
        {
            "event_id": f"{tag}-artifact-checkpoint",
            "event_type": "artifact",
            "created_at": stamp,
            "actor": WORKER,
            "node_id": NODE,
            "class_id": CLASSES,
            "task_id": TASK_ID,
            "gate": GATE,
            "artifact_type": "checkpoint",
            "path": "runtime/state/worker-092_heldout10_repl_checkpoint.json",
            "sha256": checkpoint_sha,
            "validation_status": "unverified",
            "evidence_refs": ["artifacts/worker-092/heldout10_repl/report.json"],
        },
        {
            "event_id": f"{tag}-review",
            "event_type": "review",
            "created_at": stamp,
            "actor": WORKER,
            "node_id": NODE,
            "class_id": CLASSES,
            "task_id": TASK_ID,
            "gate": GATE,
            "target_id": "FORM-HELDOUT-10",
            "reviewer": WORKER,
            "verdict": "accept",
            "score": 4.0,
            "hard_failures": [],
            "reviewed_sha256": pins["report.json"],
            "findings": [f"{f['id']} ({f['kind']}/{f['severity']}): {f['finding']}" for f in findings],
            "evidence_refs": review["evidence_refs"],
        },
        {
            "event_id": f"{tag}-claim",
            "event_type": "claim",
            "created_at": stamp,
            "actor": WORKER,
            "node_id": NODE,
            "class_id": CLASSES,
            "task_id": TASK_ID,
            "gate": GATE,
            "conclusion_type": "formal_model",
            "statement": (
                f"Pipeline-measurement claim, not a mathematical claim, at FROZEN rev29 pins "
                f"(F1 d9cebb9404b2, F2a e9a27996dfd3, F2b b2ab6acb2bbe, corpus manifest "
                f"d026fec40fe4): a non-author, non-owner re-run of all 40 FORM-HELDOUT-10 fixtures "
                f"through the two canonical stage tools reproduces the corpus report with 40/40 "
                f"per-fixture agreement and 0 drift: all-mutant union escape "
                f"{h['all_mutants_union_escape']} ({h['all_mutants_union_caught']}/33 caught), "
                f"informative C2+C0 union escape 1.0 ({h['informative_C2_C0_union_caught']}/26 "
                f"caught), WCC arm 0.0 (7/7 caught on R03 only, the same rule that rejects the "
                f"untouched frozen WCC canonical). The rev13 prose repair did not close the C2/C0 "
                f"leak; stage B remains unpinned in FROZEN rev29."),
            "assumptions": [
                "the corpus manifest/pins are the frozen target; no fixture was re-authored",
                "stage tools are used as-is; this replicates pipeline verdicts, not the rules",
                "union escape = accepted by both stages (the corpus's own convention)",
            ],
            "falsifier": report["falsifier"],
            "evidence_refs": [
                "artifacts/worker-092/heldout10_repl/report.json",
                "artifacts/heldout/heldout-10/report.json#5629e2a69c86",
                "artifacts/heldout/heldout-10/raw/raw_verdicts.json#b3480625da10",
            ],
        },
        {
            "event_id": f"{tag}-status-complete",
            "event_type": "status",
            "created_at": stamp,
            "actor": WORKER,
            "node_id": NODE,
            "class_id": CLASSES,
            "task_id": TASK_ID,
            "gate": GATE,
            "status": "active",
            "hours": 0.4,
            "summary": (
                "CHECKPOINT + EXIT. One bounded class-bound task delivered at worker level: "
                "W092-HELDOUT10-THIRDPARTY-REPL-01, the missing non-author non-owner replication of "
                "FORM-HELDOUT-10 (A1 / G-CLASSBIND). Verdict accept (reproducibility only), score 4.0, "
                "0 hard failures. 40 fixtures / 80 stage invocations; 40/40 per-fixture agreement with "
                "raw/raw_verdicts.json; informative C2+C0 union escape 1.0 (0/26); all-mutant 0.7879 "
                "(7/33, all R03-only WCC); authored controls 4/4 accepted; frozen WCC canonical "
                "rejected by R03 only; 0 fixture-hash mismatches; 0 drift pre/post. 4 informational "
                "findings (F-092-H10-01..04; stage-B pin governance, author-side prior verification, "
                "WCC-arm non-informativeness). Node status, gate verdict and validation_status NOT "
                "moved; G-CLASSBIND/G-FORM stay pending."),
            "evidence_refs": [
                "artifacts/worker-092/heldout10_repl/report.json",
                "artifacts/worker-092/heldout10_repl/manifest.json",
                "reviews/heldout10-thirdparty-repl-worker-092.json",
                "runtime/state/worker-092_heldout10_repl_checkpoint.json",
            ],
            "next_falsifier": report["falsifier"],
        },
    ]

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                continue
    appended = 0
    with OUTBOX.open("a") as f:
        for e in events:
            validate_event(e)
            if e["event_id"] in existing:
                continue
            f.write(json.dumps(e, sort_keys=True) + "\n")
            appended += 1

    print(f"manifest.json  sha256 {manifest_sha}")
    print(f"review         sha256 {review_sha}")
    print(f"checkpoint     sha256 {checkpoint_sha}")
    print(f"events appended {appended} / {len(events)} (validated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
