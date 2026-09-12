#!/usr/bin/env python3
"""Emit worker-059's F1 independent verdict: review artifact, worker checkpoint, outbox events.

Appends to comms/outbox/worker-059.jsonl only; writes only inside
artifacts/worker-059/f1_independent_verdict/. Nothing under runtime/state/ is touched.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
ACTOR = "worker-059"
TASK = "W059-F1-INDEP-VERDICT-01"
REVIEWED = "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503"
SNAP = f"artifacts/worker-059/f1_independent_verdict/af_wcc_vacuum.reviewed.9a8bd4c9680042a4.yaml"
EVID = f"artifacts/worker-059/f1_independent_verdict/independent_verdict_evidence.9a8bd4c9680042a4.json"
CHECKER = "artifacts/worker-059/f1_independent_verdict/check_f1_independent.py"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def measure_publication() -> dict:
    fr = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    m = json.loads((ROOT / "research_map/research_map.json").read_text())
    node = next(n for g in m["groups"] for n in g["nodes"] if n["id"] == "F1")
    reg = json.loads((ROOT / "runtime/state/artifact_hashes.json").read_text())["hashes"]
    canon = ROOT / "schemas/af_wcc_vacuum.yaml"
    f0 = ROOT / "research_map/formulation_taxonomy.yaml"
    return {
        "measured_at": now(),
        "canonical_schema_sha256": sha(canon),
        "canonical_schema_bytes": canon.stat().st_size,
        "canonical_schema_mtime": datetime.fromtimestamp(canon.stat().st_mtime, CST).isoformat(timespec="seconds"),
        "canonical_taxonomy_sha256": sha(f0),
        "authoring_schema_sha256": sha(ROOT / "artifacts/formulation/schemas/af_wcc_vacuum.yaml"),
        "authoring_taxonomy_sha256": sha(ROOT / "artifacts/formulation/formulation_taxonomy.yaml"),
        "frozen_revision": fr.get("revision"),
        "frozen_at": fr.get("frozen_at"),
        "frozen_pin_schema": fr["files"]["schemas/af_wcc_vacuum.yaml"]["sha256"],
        "frozen_pin_taxonomy": fr["files"]["research_map/formulation_taxonomy.yaml"]["sha256"],
        "frozen_pins_match_measured": (
            fr["files"]["schemas/af_wcc_vacuum.yaml"]["sha256"] == sha(canon)
            and fr["files"]["research_map/formulation_taxonomy.yaml"]["sha256"] == sha(f0)),
        "map_f1_declared_sha256": node.get("declared_sha256"),
        "map_f1_artifact_sha256_measured": node.get("artifact_sha256_measured"),
        "map_f1_declared_hash_matches_measured": node.get("declared_hash_matches_measured"),
        "map_f1_validation_status": node.get("validation_status"),
        "registry_f1_sha256": reg.get("schemas/af_wcc_vacuum.yaml", {}).get("sha256"),
        "registry_f0_sha256": reg.get("research_map/formulation_taxonomy.yaml", {}).get("sha256"),
    }


pub = measure_publication()
ev = json.loads((ROOT / EVID).read_text())
assert ev["reviewed_snapshot_sha256"] == REVIEWED, "snapshot/report hash mismatch"
nonpass = [c["id"] for c in ev["checks"] if c["status"] != "pass"]

review = {
    "review_id": f"{TASK}-20260912T0022",
    "event_type": "review",
    "task_id": TASK,
    "target_id": "F1",
    "target_path": "schemas/af_wcc_vacuum.yaml",
    "class_id": "AF-WCC-VAC-GEN",
    "reviewed_sha256": REVIEWED,
    "reviewed_bytes": 33642,
    "reviewed_internal_revision": 11,
    "reviewed_snapshot": SNAP,
    "reviewer": ACTOR,
    "review_kind": "independent_full_schema_verdict",
    "counts_as_independent_second_verdict": False,
    "counts_as_full_schema_verdict": True,
    "reviewer_note": "worker-059 is not one of the gate's named reviewers (16/17/18); the controller decides reviewer independence. This is a full-schema independent verdict, not a gate verdict.",
    "verdict": "revise",
    "score": 4.0,
    "semantic_verdict": "pass",
    "binding_verdict": "fail",
    "hard_failures": [
        "HF-1 declaration binding absent: research_map.json node F1 has declared_sha256=null, so declared_hash_matches_measured=False even though artifact_sha256_measured="
        + str(pub["map_f1_artifact_sha256_measured"])[:16] + "; no declared hash exists for review scanning to bind.",
        "HF-2 duplicate top-level YAML keys in the canonical schema: revised_at x3 and revised_at_unused x2. yaml.safe_load keeps the last value; a strict parser rejects the document, so revision metadata is parser-dependent.",
        "HF-3 future-dated evidence timestamps: revised_at=2026-09-12T00:30:00+08:00 and f0_binding.checked_at=2026-09-12T00:30:00+08:00 against measurement time "
        + pub["measured_at"] + "; artifacts/formulation/FROZEN.json frozen_at=2026-09-12T00:42:00+08:00. Timestamps cannot order revisions or establish a review window.",
        "HF-4 class-contract pointer crosses trees: class_contract_pointer=artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-WCC-VAC-GEN resolves only in the authoring mirror; the declared canonical F0 artifact research_map/formulation_taxonomy.yaml has no class_contracts section (it is structured under classes:). A canonical-only reader cannot resolve the F1 contract; the two taxonomy mirrors are not byte-identical.",
        "HF-5 calibration suite unusable: schemas/semantic_contract_tests/run_contract_tests.py exits 2 INTEGRITY_FAILURE because fixture hashes bind to superseded canonical files (F1 9a8bd4c9 != b65fcc0f; F2a 1bb78ce9 != a8d899d2; F2b b6123750 != 8dae50da). Measured on the settled revision.",
    ],
    "findings": [
        "F-1 semantics pass 11/11 independent checks on the reviewed snapshot (own checker, no canonical-gate imports): identity, conclusion type, no SCC leakage on the conclusion surface, quantifier order, single-q tail predicate canonical + SET only as registered variant, genericity residual/comeager with transfer-failure table, tiered falsifiers, non-vacuity as well-formedness, anti-scope, no theorem promotion.",
        "F-2 artifacts/formulation/tools/check_class_schema.py verdict=pass with 0 failed rules on four measured revisions: b65fcc0f (rev9), 68392dd8 (rev10), 16128b62 (rev10+), 9a8bd4c9 (rev11). The churn is semantic-preserving.",
        "F-3 canonical class-separation regression PASS: 17/17 leaks, 10/10 controls, FP 0 / FN 0 (runtime/bin/classsep_regression.py); 0 hard class-separation findings on F1 at 9a8bd4c9, 3 soft annotation flags remain (checker-visible soft flags are the known authoring/canonical annotation class).",
        "F-4 review-window instability: canonical F1 took four hashes in under six minutes (b65fcc0f mtime 00:13, 68392dd8 00:16:22, 16128b62 00:18:37, 9a8bd4c9 00:19:14); FROZEN rev24 was stale mid-window, settled at rev25 with all four pins matching measurement. No hash-bound accept verdict could survive that window; this verdict binds to an immutable snapshot, not to the live path.",
        "F-5 delta classification: b65fcc0f->68392dd8 = f0_binding hash refresh + revision metadata; 68392dd8->16128b62 = variant delta-filename pointer rename + f0_binding refresh; 16128b62->9a8bd4c9 = variant delta-filename normalization + revision 11. No change to conclusion, quantifiers, domains, genericity, visibility predicate, or falsifier logic in any delta.",
        "F-6 f0_binding is internally consistent at the reviewed revision: declared_f0_sha256=276009f4 equals the measured research_map/formulation_taxonomy.yaml at review time.",
        "F-7 mirror status at settlement: canonical and authoring schemas byte-identical at 9a8bd4c9 (FROZEN pins both); taxonomies still divergent (canonical 276009f4 classes-structure vs authoring c8e979a1 class_contracts-structure).",
    ],
    "evidence_refs": [
        f"{SNAP}#{REVIEWED[:12]}",
        f"{EVID}#{sha(ROOT / EVID)[:12]}",
        f"{CHECKER}#{sha(ROOT / CHECKER)[:12]}",
        "artifacts/worker-059/f1_independent_verdict/diff_frozen_b65fcc0f_vs_measured_68392dd8.txt",
        "artifacts/worker-059/f1_independent_verdict/contract_tests_stdout_T2.txt",
        "runtime/bin/classsep_regression.py",
        "artifacts/formulation/FROZEN.json#rev25",
    ],
    "falsifier": "Re-run artifacts/worker-059/f1_independent_verdict/check_f1_independent.py against the same snapshot: any SCC token on the conclusion surface, wrong quantifier order, SET-variant promoted into the class, or an unpinned f0_binding falsifies the pass part. Conversely, a canonical-only tree in which research_map/formulation_taxonomy.yaml resolves class_contracts.AF-WCC-VAC-GEN, plus a strict YAML parse of schemas/af_wcc_vacuum.yaml, plus declared_sha256 set on map node F1, plus run_contract_tests.py exit 0 falsifies the revise part.",
    "next_falsifier": "A revision at hash >= 9a8bd4c9 in which the conclusion/visibility/genericity blocks change semantics, or a strict duplicate-key-free parse of the canonical file; either voids the bookkeeping-only reading.",
    "claims_completion": False,
    "validation_status": "unverified",
    "review_status": "unverified",
}
review_path = HERE / "review_F1_9a8bd4c9.json"
review_path.write_text(json.dumps(review, indent=2, sort_keys=True))
review_sha = sha(review_path)

checkpoint = {
    "checkpoint_id": "w059-ckpt-20260912T0022",
    "actor": ACTOR,
    "task_id": TASK,
    "created_at": now(),
    "scope": "worker-level checkpoint; controller research_map/checkpoint.py deliberately NOT run (it rewrites runtime/state/* and ingests global comms)",
    "reviewed_sha256": REVIEWED,
    "review_artifact": str(review_path.relative_to(ROOT)),
    "review_artifact_sha256": review_sha,
    "evidence_artifact": EVID,
    "evidence_artifact_sha256": sha(ROOT / EVID),
    "checker": CHECKER,
    "checker_sha256": sha(ROOT / CHECKER),
    "reviewed_snapshots": {
        "b65fcc0f": "artifacts/flash-04/f1_ambiguity/schema_snapshots/af_wcc_vacuum.b65fcc0f.yaml",
        "68392dd8": "artifacts/worker-059/f1_independent_verdict/af_wcc_vacuum.reviewed.68392dd820505fbb.yaml",
        "16128b62": "artifacts/worker-059/f1_independent_verdict/af_wcc_vacuum.reviewed.16128b62fe08f3d0.yaml",
        "9a8bd4c9": SNAP,
    },
    "gate_results": {
        "check_class_schema": "pass x4 revisions",
        "classsep_regression": "PASS 17/17, controls 10/10, FP 0 FN 0",
        "run_contract_tests": "exit 2 INTEGRITY_FAILURE (fixture hashes bind superseded canonical files)",
        "independent_checks": f"{ev['summary']['semantic_checks_passed']}/{ev['summary']['semantic_checks_total']} semantic pass; "
                               f"non-pass={nonpass}",
    },
    "publication_state": pub,
    "verdict": {"value": "revise", "score": 4.0, "semantic": "pass", "binding": "fail"},
    "event_ids": [
        "w059-20260912T0022-artifact-evidence",
        "w059-20260912T0022-artifact-review",
        "w059-20260912T0022-review-f1",
        "w059-20260912T0022-blocker-publication",
        "w059-20260912T0022-status-checkpoint",
    ],
}
ckpt_path = HERE / "checkpoint_w059.json"
ckpt_path.write_text(json.dumps(checkpoint, indent=2, sort_keys=True))

events = [
    {
        "event_id": "w059-20260912T0022-artifact-evidence",
        "event_type": "artifact",
        "created_at": now(),
        "actor": ACTOR,
        "node_id": "F1",
        "group_id": "formulation",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "artifact_type": "independent_verdict_evidence",
        "path": EVID,
        "sha256": sha(ROOT / EVID),
        "validation_status": "unverified",
        "evidence_refs": [f"{SNAP}#{REVIEWED[:12]}", f"{CHECKER}#{sha(ROOT / CHECKER)[:12]}"],
        "note": "11/11 independent semantic checks pass at 9a8bd4c9; 4 hygiene/binding failures recorded (duplicate YAML keys, future timestamps, cross-tree contract pointer, calibration-suite integrity failure).",
    },
    {
        "event_id": "w059-20260912T0022-artifact-review",
        "event_type": "artifact",
        "created_at": now(),
        "actor": ACTOR,
        "node_id": "F1",
        "group_id": "formulation",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "artifact_type": "independent_review",
        "path": str(review_path.relative_to(ROOT)),
        "sha256": review_sha,
        "validation_status": "unverified",
        "evidence_refs": [f"{EVID}#{sha(ROOT / EVID)[:12]}"],
        "note": "Full-schema independent verdict on F1 at canonical sha256 9a8bd4c9 (internal revision 11).",
    },
    {
        "event_id": "w059-20260912T0022-review-f1",
        "event_type": "review",
        "created_at": now(),
        "actor": ACTOR,
        "target_id": "F1",
        "target_path": "schemas/af_wcc_vacuum.yaml",
        "class_id": "AF-WCC-VAC-GEN",
        "reviewed_sha256": REVIEWED,
        "artifact": str(review_path.relative_to(ROOT)),
        "sha256": review_sha,
        "reviewer": ACTOR,
        "verdict": "revise",
        "score": 4.0,
        "counts_as_independent_second_verdict": False,
        "hard_failures": [h.split(":")[0] + ": " + h.split(":", 1)[1][:140] for h in review["hard_failures"]],
        "findings": [f[:180] for f in review["findings"]],
        "gate_proposal": None,
        "evidence_refs": review["evidence_refs"][:6],
        "next_falsifier": review["next_falsifier"],
        "validation_status": "unverified",
        "note": "Semantics pass; hash-binding/publication state fails. Reviewer independence is the controller's call.",
    },
    {
        "event_id": "w059-20260912T0022-blocker-publication",
        "event_type": "blocker",
        "created_at": now(),
        "actor": ACTOR,
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "description": "A hash-bound accept for F1 cannot be issued while (1) map node F1 has declared_sha256=null (declared_hash_matches_measured=False), "
                       "(2) the canonical schema contains duplicate top-level keys, (3) revised_at/checked_at are future-dated (00:30:00) and FROZEN rev25 frozen_at=00:42:00, "
                       "(4) class_contract_pointer resolves only in the authoring mirror, and (5) run_contract_tests.py exits 2 INTEGRITY_FAILURE. "
                       "Canonical F1 was republished four times in <6 minutes; FROZEN rev24 was stale mid-window before settling at rev25.",
        "needed_to_unblock": "Set map node F1 declared_sha256 to the measured hash; remove duplicate YAML keys; write timestamps at or before wall clock; "
                             "either add class_contracts to the canonical taxonomy or repoint the schema; rebind the contract-suite fixture hashes to the current canonical set; then hold F1 stable for one full review window.",
        "evidence_refs": [str(ckpt_path.relative_to(ROOT)), f"{EVID}#{sha(ROOT / EVID)[:12]}",
                          "artifacts/worker-059/f1_independent_verdict/contract_tests_stdout_T2.txt"],
        "expected_information_gain": "high: unblocks two independent hash-bound accepts for G-FORM/G-AUDIT on F1.",
    },
    {
        "event_id": "w059-20260912T0022-status-checkpoint",
        "event_type": "status",
        "created_at": now(),
        "actor": ACTOR,
        "node_id": "F1",
        "group_id": "formulation",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "status": "active",
        "hours": 0.4,
        "checkpoint_id": "w059-ckpt-20260912T0022",
        "summary": "W059-F1-INDEP-VERDICT-01 complete: independent full-schema verdict on F1 at canonical sha256 9a8bd4c9 (internal rev11). Semantics pass 11/11 independent checks; structural gate pass on four revisions; class-separation regression PASS (17/17, 10/10, FP/FN 0). Verdict=revise (score 4): binding/publication defects only. Artifacts: "
                   + str(review_path.relative_to(ROOT)) + " and " + EVID + ". Worker-level checkpoint at " + str(ckpt_path.relative_to(ROOT)) + "; no global state mutated, no node completion or gate verdict claimed.",
        "evidence_refs": review["evidence_refs"][:6],
        "next_falsifier": review["next_falsifier"],
    },
]

out = ROOT / "comms/outbox/worker-059.jsonl"
with out.open("a") as f:
    for e in events:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
print(json.dumps({"review": str(review_path.relative_to(ROOT)), "review_sha256": review_sha,
                  "checkpoint": str(ckpt_path.relative_to(ROOT)), "checkpoint_sha256": sha(ckpt_path),
                  "events_appended": [e["event_id"] for e in events],
                  "publication": pub}, indent=2))
