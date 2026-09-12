#!/usr/bin/env python3
"""v2 correction for worker-059's F1 verdict: withdraw stale HF-1, re-emit review/blocker.

v1 (00:22) claimed map node F1 had declared_hash_matches_measured=False. Re-measurement
shows the map reports True (updated_at 00:21:55), so that hard failure is withdrawn and
downgraded to a bookkeeping finding (declared_sha256 is null on all formulation nodes).
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
SNAP = "artifacts/worker-059/f1_independent_verdict/af_wcc_vacuum.reviewed.9a8bd4c9680042a4.yaml"
EVID = "artifacts/worker-059/f1_independent_verdict/independent_verdict_evidence.9a8bd4c9680042a4.json"
CHECKER = "artifacts/worker-059/f1_independent_verdict/check_f1_independent.py"
V1 = "artifacts/worker-059/f1_independent_verdict/review_F1_9a8bd4c9.json"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


ev = json.loads((ROOT / EVID).read_text())
assert ev["reviewed_snapshot_sha256"] == REVIEWED
m = json.loads((ROOT / "research_map/research_map.json").read_text())
node = next(n for g in m["groups"] for n in g["nodes"] if n["id"] == "F1")
fr = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
canon_now = sha(ROOT / "schemas/af_wcc_vacuum.yaml")

review = {
    "review_id": f"{TASK}-20260912T0023-v2",
    "supersedes_review_id": f"{TASK}-20260912T0022",
    "supersedes_artifact": V1,
    "supersedes_artifact_sha256": sha(ROOT / V1),
    "correction": "v1 hard failure HF-1 (map node F1 declared_hash_matches_measured=False) is WITHDRAWN. Re-measurement at "
                  + now() + " shows research_map.json updated_at=" + str(m.get("updated_at"))
                  + " reports declared_hash_matches_measured=True for F1 with artifact_sha256_measured="
                  + str(node.get("artifact_sha256_measured"))[:16]
                  + ". The residual issue (declared_sha256 field is null) is downgraded to finding F-8; it is non-blocking.",
    "event_type": "review",
    "task_id": TASK,
    "target_id": "F1",
    "target_path": "schemas/af_wcc_vacuum.yaml",
    "class_id": "AF-WCC-VAC-GEN",
    "reviewed_sha256": REVIEWED,
    "reviewed_bytes": 33642,
    "reviewed_internal_revision": 11,
    "reviewed_snapshot": SNAP,
    "canonical_schema_measured_at_v2": canon_now,
    "canonical_drifted_since_review": canon_now != REVIEWED,
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
        "HF-1 duplicate top-level YAML keys in the canonical schema: revised_at x3 and revised_at_unused x2. yaml.safe_load keeps the last value; a strict parser rejects the document, so revision metadata is parser-dependent.",
        "HF-2 future-dated evidence timestamps: revised_at=2026-09-12T00:30:00+08:00 and f0_binding.checked_at=2026-09-12T00:30:00+08:00 against v2 measurement time "
        + now() + "; artifacts/formulation/FROZEN.json rev" + str(fr.get("revision")) + " frozen_at=" + str(fr.get("frozen_at"))
        + ". Timestamps cannot order revisions or bound a review window.",
        "HF-3 class-contract pointer crosses trees: class_contract_pointer=artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-WCC-VAC-GEN resolves only in the authoring mirror; the declared canonical F0 artifact research_map/formulation_taxonomy.yaml has no class_contracts section (structured under classes:). A canonical-only reader cannot resolve the F1 contract; the two taxonomy mirrors are not byte-identical (canonical "
        + sha(ROOT / "research_map/formulation_taxonomy.yaml")[:12] + " vs authoring " + sha(ROOT / "artifacts/formulation/formulation_taxonomy.yaml")[:12] + ").",
        "HF-4 calibration suite unusable: schemas/semantic_contract_tests/run_contract_tests.py exits 2 INTEGRITY_FAILURE because fixture hashes bind to superseded canonical files (F1 9a8bd4c9 != b65fcc0f; F2a 1bb78ce9 != a8d899d2; F2b b6123750 != 8dae50da), measured on the settled revision.",
    ],
    "findings": [
        "F-1 semantics pass 11/11 independent checks on the reviewed snapshot (own checker; no canonical-gate imports): identity, conclusion type, no SCC leakage on the conclusion surface, quantifier order, single-q tail predicate canonical + SET only as registered variant, genericity residual/comeager with transfer-failure table, tiered falsifiers, non-vacuity as well-formedness, anti-scope, no theorem promotion.",
        "F-2 artifacts/formulation/tools/check_class_schema.py verdict=pass, 0 failed rules, on four measured revisions: b65fcc0f (rev9), 68392dd8 (rev10), 16128b62 (rev10+), 9a8bd4c9 (rev11).",
        "F-3 canonical class-separation regression PASS: 17/17 leaks, 10/10 controls, FP 0 / FN 0; 0 hard class-separation findings on F1 at 9a8bd4c9.",
        "F-4 review-window instability: canonical F1 took four hashes in under six minutes (b65fcc0f 00:13, 68392dd8 00:16:22, 16128b62 00:18:37, 9a8bd4c9 00:19:14); FROZEN rev24 was stale mid-window and settled at rev25 with all four pins matching measurement. No hash-bound accept verdict could survive that window; this verdict binds to an immutable snapshot.",
        "F-5 delta classification: b65fcc0f->68392dd8 = f0_binding hash refresh + revision metadata; 68392dd8->16128b62 = variant delta-filename pointer rename + f0_binding refresh; 16128b62->9a8bd4c9 = variant delta-filename normalization + revision 11. No change to conclusion, quantifiers, domains, genericity, visibility predicate, or falsifier logic in any delta.",
        "F-6 f0_binding is internally consistent at the reviewed revision: declared_f0_sha256=276009f4 equals the measured canonical taxonomy.",
        "F-7 mirror status at settlement: canonical and authoring schemas byte-identical at 9a8bd4c9; taxonomies still divergent (canonical classes-structure vs authoring class_contracts-structure).",
        "F-8 (downgraded from v1 HF-1) map node F1 carries artifact_sha256_measured and declared_hash_matches_measured=True, but declared_sha256 is null (also on F2a/F2b), so a reviewer cannot read the binding hash from the node field; the declaration is a boolean without a value. Non-blocking bookkeeping inconsistency.",
    ],
    "evidence_refs": [
        f"{SNAP}#{REVIEWED[:12]}",
        f"{EVID}#{sha(ROOT / EVID)[:12]}",
        f"{CHECKER}#{sha(ROOT / CHECKER)[:12]}",
        "artifacts/worker-059/f1_independent_verdict/diff_frozen_b65fcc0f_vs_measured_68392dd8.txt",
        "artifacts/worker-059/f1_independent_verdict/contract_tests_stdout_T2.txt",
        "runtime/bin/classsep_regression.py",
        f"artifacts/formulation/FROZEN.json#rev{fr.get('revision')}",
        f"{V1}#{sha(ROOT / V1)[:12]} (superseded v1)",
    ],
    "falsifier": "Re-run artifacts/worker-059/f1_independent_verdict/check_f1_independent.py against the same snapshot: any SCC token on the conclusion surface, wrong quantifier order, SET-variant promoted into the class, or an unpinned f0_binding falsifies the pass part. A canonical-only tree in which research_map/formulation_taxonomy.yaml resolves class_contracts.AF-WCC-VAC-GEN, a strict duplicate-key-free YAML parse of schemas/af_wcc_vacuum.yaml, timestamps at or before wall clock, and run_contract_tests.py exit 0 falsify the revise part.",
    "next_falsifier": "A revision at hash >= 9a8bd4c9 in which the conclusion/visibility/genericity blocks change semantics, or a strict duplicate-key-free parse of the canonical file; either voids the bookkeeping-only reading.",
    "claims_completion": False,
    "validation_status": "unverified",
    "review_status": "unverified",
}
review_path = HERE / "review_F1_9a8bd4c9_v2.json"
review_path.write_text(json.dumps(review, indent=2, sort_keys=True))
review_sha = sha(review_path)

checkpoint = {
    "checkpoint_id": "w059-ckpt-20260912T0024-v2",
    "actor": ACTOR,
    "task_id": TASK,
    "created_at": now(),
    "supersedes_checkpoint": "w059-ckpt-20260912T0022",
    "scope": "worker-level checkpoint; controller research_map/checkpoint.py deliberately NOT run (it rewrites runtime/state/* and ingests global comms)",
    "reviewed_sha256": REVIEWED,
    "canonical_schema_measured_at_checkpoint": canon_now,
    "canonical_drifted_since_review": canon_now != REVIEWED,
    "review_artifact": str(review_path.relative_to(ROOT)),
    "review_artifact_sha256": review_sha,
    "evidence_artifact": EVID,
    "evidence_artifact_sha256": sha(ROOT / EVID),
    "checker": CHECKER,
    "checker_sha256": sha(ROOT / CHECKER),
    "gate_results": {
        "check_class_schema": "pass x4 revisions (b65fcc0f, 68392dd8, 16128b62, 9a8bd4c9)",
        "classsep_regression": "PASS 17/17, controls 10/10, FP 0 FN 0",
        "run_contract_tests": "exit 2 INTEGRITY_FAILURE (fixture hashes bind superseded canonical files)",
        "independent_checks": f"{ev['summary']['semantic_checks_passed']}/{ev['summary']['semantic_checks_total']} semantic pass; "
                               f"non-pass={[c['id'] for c in ev['checks'] if c['status'] != 'pass']}",
    },
    "publication_state": {
        "frozen_revision": fr.get("revision"),
        "frozen_at": fr.get("frozen_at"),
        "frozen_pins_match_measured": (
            fr["files"]["schemas/af_wcc_vacuum.yaml"]["sha256"] == canon_now
            and fr["files"]["research_map/formulation_taxonomy.yaml"]["sha256"] == sha(ROOT / "research_map/formulation_taxonomy.yaml")),
        "map_f1_declared_sha256": node.get("declared_sha256"),
        "map_f1_artifact_sha256_measured": node.get("artifact_sha256_measured"),
        "map_f1_declared_hash_matches_measured": node.get("declared_hash_matches_measured"),
        "map_updated_at": m.get("updated_at"),
    },
    "verdict": {"value": "revise", "score": 4.0, "semantic": "pass", "binding": "fail"},
    "corrections": ["v1 HF-1 withdrawn (map declared_hash_matches_measured=True on re-measurement); downgraded to finding F-8."],
}
ckpt_path = HERE / "checkpoint_w059_v2.json"
ckpt_path.write_text(json.dumps(checkpoint, indent=2, sort_keys=True))

events = [
    {
        "event_id": "w059-20260912T0024-artifact-review-v2",
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
        "supersedes_path": V1,
        "supersedes_sha256": sha(ROOT / V1),
        "evidence_refs": [f"{EVID}#{sha(ROOT / EVID)[:12]}"],
        "note": "v2 correction: v1 HF-1 (map declared_hash_matches_measured=False) withdrawn; verdict unchanged at revise, hard failures now HF-1..HF-4.",
    },
    {
        "event_id": "w059-20260912T0024-review-f1-v2",
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
        "supersedes_event_id": "w059-20260912T0022-review-f1",
        "hard_failures": [h.split(":")[0] + ": " + h.split(":", 1)[1][:140] for h in review["hard_failures"]],
        "findings": [f[:180] for f in review["findings"]],
        "evidence_refs": review["evidence_refs"][:6],
        "next_falsifier": review["next_falsifier"],
        "validation_status": "unverified",
        "note": "Semantics pass 11/11; binding/publication state fails. Reviewer independence is the controller's call.",
    },
    {
        "event_id": "w059-20260912T0024-blocker-publication-v2",
        "event_type": "blocker",
        "created_at": now(),
        "actor": ACTOR,
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "supersedes_event_id": "w059-20260912T0022-blocker-publication",
        "description": "A hash-bound accept for F1 cannot be issued while (1) the canonical schema contains duplicate top-level keys, "
                       "(2) revised_at/checked_at are future-dated (00:30:00) and FROZEN rev" + str(fr.get("revision")) + " frozen_at=" + str(fr.get("frozen_at")) + ", "
                       "(3) class_contract_pointer resolves only in the authoring mirror, and (4) run_contract_tests.py exits 2 INTEGRITY_FAILURE. "
                       "Canonical F1 was republished four times in <6 minutes; FROZEN rev24 was stale mid-window before settling at rev25. "
                       "The v1 blocker item about map declared_hash_matches_measured=False is WITHDRAWN: the map now reports True.",
        "needed_to_unblock": "Remove duplicate YAML keys; write timestamps at or before wall clock; either add class_contracts to the canonical taxonomy or repoint the schema; rebind the contract-suite fixture hashes to the current canonical set; set node declared_sha256 to the binding value; then hold F1 stable for one full review window.",
        "evidence_refs": [str(ckpt_path.relative_to(ROOT)), f"{EVID}#{sha(ROOT / EVID)[:12]}",
                          "artifacts/worker-059/f1_independent_verdict/contract_tests_stdout_T2.txt"],
        "expected_information_gain": "high: unblocks two independent hash-bound accepts for G-FORM/G-AUDIT on F1.",
    },
    {
        "event_id": "w059-20260912T0024-status-checkpoint-v2",
        "event_type": "status",
        "created_at": now(),
        "actor": ACTOR,
        "node_id": "F1",
        "group_id": "formulation",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "status": "active",
        "hours": 0.5,
        "checkpoint_id": "w059-ckpt-20260912T0024-v2",
        "supersedes_event_id": "w059-20260912T0022-status-checkpoint",
        "summary": "W059-F1-INDEP-VERDICT-01 final (v2): independent full-schema verdict on F1 at canonical sha256 9a8bd4c9 (rev11). Semantics pass 11/11 independent checks; structural gate pass on four revisions; class-separation regression PASS. Verdict=revise (score 4): four binding/publication defects, no semantic defect found. v1 HF-1 withdrawn after re-measurement. Artifacts: "
                   + str(review_path.relative_to(ROOT)) + ", " + EVID + ", checkpoint " + str(ckpt_path.relative_to(ROOT))
                   + ". Worker-level checkpoint only; no global state mutated, no node completion or gate verdict claimed.",
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
                  "canonical_now": canon_now, "canonical_drifted": canon_now != REVIEWED,
                  "events_appended": [e["event_id"] for e in events]}, indent=2))
