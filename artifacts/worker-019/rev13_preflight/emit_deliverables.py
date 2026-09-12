#!/usr/bin/env python3
"""Emit W019-REV13-PREFLIGHT-01 deliverables: review file, checkpoint, outbox events.

Run after verify_rev13_repair.py. Appends (never rewrites) to the worker outbox and validates
every event against research_map.schemas.validate_event before writing.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
from research_map.schemas import validate_event  # noqa: E402

BASE = os.path.join(ROOT, "artifacts", "worker-019", "rev13_preflight")
STAMP = time.strftime("%Y%m%dT%H%M%S")
NOW = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")


def sha(p: str) -> str:
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


res_path = os.path.join(BASE, "results.json")
probe_path = os.path.join(BASE, "verify_rev13_repair.py")
readme_path = os.path.join(BASE, "README.md")
res = json.load(open(res_path))
pin = json.load(open(os.path.join(BASE, "pinned_bytes.json")))
man_final_sha = pin["manifest_final"]["sha256"]
res_sha, probe_sha, readme_sha = sha(res_path), sha(probe_path), sha(readme_path)
checks = {c["id"]: c for c in res["checks"]}
c1, c3, c4, c5, c6, c7, c9, c10 = (checks[k] for k in (
    "C1-pin-match", "C3-item1-taxonomy-cases", "C4-item2-evidence-refresh",
    "C5-item3-strictness-direction", "C6-item4-frozen-rev29", "C7-no-semantic-change",
    "C9-sibling-corpus-binding", "C10-residual-out-of-card"))

review = {
    "review_id": f"W019-REV13-PREFLIGHT-REVIEW-{STAMP}",
    "task_id": "W019-REV13-PREFLIGHT-01",
    "target_id": "F1@d9cebb9404b2, F2a@e9a27996dfd3, F2b@b2ab6acb2bbe (rev13, FROZEN rev29 815e08079aef)",
    "reviewed_artifact": [
        "schemas/af_wcc_vacuum.yaml",
        "schemas/af_scc_c2_vacuum.yaml",
        "schemas/af_scc_c0_vacuum.yaml",
        "artifacts/formulation/FROZEN.json",
    ],
    "reviewed_sha256": {
        "schemas/af_wcc_vacuum.yaml": res["pinned_bytes"]["f1__af_wcc_vacuum.yaml"]["sha256"],
        "schemas/af_scc_c2_vacuum.yaml": res["pinned_bytes"]["f2a__af_scc_c2_vacuum.yaml"]["sha256"],
        "schemas/af_scc_c0_vacuum.yaml": res["pinned_bytes"]["f2b__af_scc_c0_vacuum.yaml"]["sha256"],
        "artifacts/formulation/FROZEN.json": man_final_sha,
    },
    "reviewer": "worker-019",
    "actor": "worker-019",
    "worker_slot": "worker-019",
    "created_at": NOW,
    "node_id": "F1,F2a,F2b",
    "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
    "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "gate": "G-FORM",
    "verdict": "revise",
    "score": 4.0,
    "counts_as_full_schema_verdict": False,
    "hard_failures": res["hard_failures"],
    "findings": [
        "Items 1-4 of astra-life05-evidence-binding-repair verified at the rev13 bytes by an independent instrument: "
        "the pre-publication snapshot (taken while FROZEN read rev28) matches the rev29 pins in both manifest readings "
        "for all five moved paths plus their authoring mirrors.",
        "Item 3 text corrections are direction-correct against W076 T1/T2/T4 and confined to visibility.definition, "
        "quantifiers.domains.D5.definition and class_identity_variants[0].relation; the tail predicate itself is "
        "byte-unchanged and no class id, hypothesis, conclusion predicate or genericity field moved (C7 leaf diff).",
        "CF-20 item-1 claim is not reproducible at the current bytes: taxonomy_cases.jsonl (mtime 00:42:36, rebind note "
        "00:32:31) already carries binding_status=bound_taxonomy_sha_0abb9ed8a961 on 36/36 rows and zero occurrences of "
        "66bf917bd368, so that part of the finding was stale when written or measured against an older snapshot.",
        "W019-RV13-02 (blocking): the rev29-pinned F1 falsifier corpus f1_falsifier_tests.jsonl (56bcb4b3234b) binds all "
        "25 rows to F1 rev12 cce9c60146d6; F1-AMB-11, F1-AMB-17 (visibility.definition) and F1-AMB-23 "
        "(class_identity_variants) decide on fields edited by rev13, so their verdicts are advisory until re-pinned/re-run.",
        "Freeze-window instability recorded: the rev29 manifest moved e1a8aaa394eb -> 3d9e3d77fd87 -> 815e08079aef within "
        "~3 minutes (same schema pins), and a transient post-freeze drift on artifacts/formulation/evidence/"
        "variant_delta_check.json (disk 0b23f0b29232 vs pin fc6ee058dd96) was observed and restored at 00:57:08.",
        "Residual out-of-card (C10): the inverted SET direction survives at research_map/formulation_taxonomy.yaml:94 and "
        ":200 (G-F0-frozen, so not repairable without a new revision) and as a descriptive quote in the supplement D1 "
        "ledger; VARIANT_REGISTRY:57 and the SET delta were measured corrected at the final rev29 pin 64b8d639.",
        "Owner artifact events landed at 00:57:43 (lead-form-20260912T005743-00..16) covering every moved path, which "
        "discharges the earlier snapshot-time observation that they were absent.",
    ],
    "independence": (
        "not the author of any rev13/rev29 artifact and did not use the repair tool; the pinned bytes were copied and "
        "hashed before FROZEN rev29 existed, and the canonical checkers were re-run in place, not imported"
    ),
    "scope_limit": (
        "pin/binding/leaf-diff verification at the cited hashes only; not a re-review of class semantics, not a gate "
        "verdict, no node status or validation_status set"
    ),
    "evidence_refs": [
        f"artifacts/worker-019/rev13_preflight/results.json#sha256:{res_sha[:12]}",
        f"artifacts/worker-019/rev13_preflight/verify_rev13_repair.py#sha256:{probe_sha[:12]}",
        f"schemas/af_wcc_vacuum.yaml#sha256:{res['pinned_bytes']['f1__af_wcc_vacuum.yaml']['sha256'][:12]}",
        f"schemas/af_scc_c2_vacuum.yaml#sha256:{res['pinned_bytes']['f2a__af_scc_c2_vacuum.yaml']['sha256'][:12]}",
        f"schemas/af_scc_c0_vacuum.yaml#sha256:{res['pinned_bytes']['f2b__af_scc_c0_vacuum.yaml']['sha256'][:12]}",
        f"schemas/f1_falsifier_tests.jsonl#sha256:{res['pinned_bytes']['f1_falsifier_tests.jsonl']['sha256'][:12]}",
        f"artifacts/formulation/FROZEN.json#sha256:{man_final_sha[:12]}",
        f"artifacts/formulation/evidence/taxonomy_consistency.json#sha256:{res['pinned_bytes']['taxonomy_consistency.json']['sha256'][:12]}",
        "artifacts/worker-076/gform_strictness_reconcile/probe_result.json",
    ],
    "next_falsifier": res["next_falsifier"],
    "authority_note": res["authority_note"],
}
rev_path = os.path.join(ROOT, "reviews", "W019-rev13-preflight-review.json")
json.dump(review, open(rev_path, "w"), indent=1, sort_keys=True)
rev_sha = sha(rev_path)

summary = (
    "W019-REV13-PREFLIGHT-01 complete (bounded class-bound worker, checkpointing then exiting). "
    "Independent verification of astra-life05-evidence-binding-repair at the rev13 bytes "
    "(F1 d9cebb9404b2, F2a e9a27996dfd3, F2b b2ab6acb2bbe, taxonomy_cases ccf7041bd0ff), pinned before "
    "FROZEN rev29 existed and matching both rev29 manifest readings; final manifest 815e08079aef. "
    "Items 1-4 pass (36/36 rows rebound, evidence 9e335e9b declared 3/3, strictness directions corrected "
    "per W076, rev29 + verify_frozen exit 0 twice, leaf diff bounded, mirrors aligned, owner events present). "
    "Verdict revise 4.0, one hash-bound hard failure W019-RV13-02: the rev29-pinned F1 falsifier corpus "
    "still binds rev12 cce9c60146d6, including 3 rows deciding on rev13-edited fields. CF-20's item-1 claim "
    "is not reproducible at current bytes. No gate verdict, no node completion, no canonical file written."
)
claim_statement = (
    "Machine-measured binding facts at the rev13/rev29 pins (deterministic read-only probe, no network): "
    "(a) the five moved paths' pre-publication sha256 measurements equal the FROZEN rev29 pins in both the "
    "00:55:02 (3d9e3d77fd87) and 00:57:26 (815e08079aef) manifest readings; (b) all three schemas declare "
    "f0_binding.consistency_evidence_sha256=9e335e9ba1bf which equals the live evidence file, and "
    "check_taxonomy_consistency.py exits 0; (c) the rev12->rev13 leaf diff is 9/6/6 leaves confined to "
    "revision metadata, f0_binding and the three worker-076 strictness texts; (d) the rev29-pinned "
    "schemas/f1_falsifier_tests.jsonl (56bcb4b3234b) has 25/25 rows bound to F1 rev12 cce9c60146d6, and "
    "3 of those rows decide on fields edited by rev13 (F1-AMB-11, F1-AMB-17 visibility.definition; "
    "F1-AMB-23 class_identity_variants), so the corpus is not yet binding G-FORM evidence at rev13."
)

events = [
    {
        "event_id": f"w019-rv13-art-results-{STAMP}",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-019",
        "worker_slot": "worker-019",
        "node_id": "F1,F2a,F2b",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "class_ids": review["class_ids"],
        "gate": "G-FORM",
        "artifact_type": "machine_verification_record",
        "path": "artifacts/worker-019/rev13_preflight/results.json",
        "sha256": res_sha,
        "validation_status": "unverified",
        "evidence_refs": review["evidence_refs"],
        "next_falsifier": res["next_falsifier"],
    },
    {
        "event_id": f"w019-rv13-art-probe-{STAMP}",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-019",
        "worker_slot": "worker-019",
        "node_id": "F1,F2a,F2b",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "class_ids": review["class_ids"],
        "gate": "G-FORM",
        "artifact_type": "independent_checker",
        "path": "artifacts/worker-019/rev13_preflight/verify_rev13_repair.py",
        "sha256": probe_sha,
        "validation_status": "unverified",
        "evidence_refs": [
            f"artifacts/worker-019/rev13_preflight/results.json#sha256:{res_sha[:12]}",
            f"schemas/af_wcc_vacuum.yaml#sha256:{review['reviewed_sha256']['schemas/af_wcc_vacuum.yaml'][:12]}",
        ],
        "next_falsifier": res["next_falsifier"],
    },
    {
        "event_id": f"w019-rv13-review-{STAMP}",
        "event_type": "review",
        "created_at": NOW,
        "actor": "worker-019",
        "worker_slot": "worker-019",
        "node_id": "F1,F2a,F2b",
        "target_id": review["target_id"],
        "class_id": review["class_id"],
        "class_ids": review["class_ids"],
        "gate": "G-FORM",
        "reviewer": "worker-019",
        "verdict": "revise",
        "score": 4.0,
        "hard_failures": review["hard_failures"],
        "findings": review["findings"],
        "review_path": "reviews/W019-rev13-preflight-review.json",
        "review_sha256": rev_sha,
        "reviewed_artifact": review["reviewed_artifact"],
        "reviewed_sha256": review["reviewed_sha256"],
        "counts_as_full_schema_verdict": False,
        "independence": review["independence"],
        "scope_limit": review["scope_limit"],
        "evidence_refs": review["evidence_refs"],
        "next_falsifier": review["next_falsifier"],
    },
    {
        "event_id": f"w019-rv13-claim-{STAMP}",
        "event_type": "claim",
        "created_at": NOW,
        "actor": "worker-019",
        "worker_slot": "worker-019",
        "node_id": "F1,F2a,F2b",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "class_ids": review["class_ids"],
        "gate": "G-FORM",
        "conclusion_type": "numerical_evidence",
        "statement": claim_statement,
        "assumptions": [
            "the canonical paths named in f0_binding are the F1/F2a/F2b schemas and FROZEN.json is the formulation manifest",
            "research_map/events.jsonl is the accepted stream and comms/outbox/astra-lead-formulation.jsonl is the owner outbox",
            "binding_sha256/deciding_field in f1_falsifier_tests.jsonl are binding metadata, not historical excerpts",
        ],
        "artifact_refs": [
            "artifacts/worker-019/rev13_preflight/results.json",
            "reviews/W019-rev13-preflight-review.json",
        ],
        "evidence_refs": review["evidence_refs"],
        "falsifier": res["next_falsifier"],
    },
    {
        "event_id": f"w019-rv13-status-{STAMP}",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-019",
        "worker_slot": "worker-019",
        "node_id": "F1,F2a,F2b",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "class_ids": review["class_ids"],
        "gate": "G-FORM",
        "status": "active",
        "hours": 0.4,
        "summary": summary,
        "evidence_refs": [
            f"artifacts/worker-019/rev13_preflight/results.json#sha256:{res_sha[:12]}",
            f"reviews/W019-rev13-preflight-review.json#sha256:{rev_sha[:12]}",
            f"schemas/f1_falsifier_tests.jsonl#sha256:{res['pinned_bytes']['f1_falsifier_tests.jsonl']['sha256'][:12]}",
        ],
        "next_falsifier": res["next_falsifier"],
    },
]

for e in events:
    validate_event(e)

outbox = os.path.join(ROOT, "comms", "outbox", "worker-019.jsonl")
with open(outbox, "a") as f:
    for e in events:
        f.write(json.dumps(e, sort_keys=True) + "\n")

map_sha = sha(os.path.join(ROOT, "research_map", "research_map.json"))
checkpoint = {
    "checkpoint_id": f"ckpt-w019-rev13-preflight-{STAMP}",
    "task_id": "W019-REV13-PREFLIGHT-01",
    "actor": "worker-019",
    "created_at": NOW,
    "map_sha256_at_checkpoint": map_sha,
    "reading": {
        "schemas": {
            "F1": res["pinned_bytes"]["f1__af_wcc_vacuum.yaml"]["sha256"],
            "F2a": res["pinned_bytes"]["f2a__af_scc_c2_vacuum.yaml"]["sha256"],
            "F2b": res["pinned_bytes"]["f2b__af_scc_c0_vacuum.yaml"]["sha256"],
        },
        "frozen_final": man_final_sha,
        "checks": {c["id"]: c["status"] for c in res["checks"]},
        "verdict": res["verdict"],
        "score": res["score"],
        "hard_failed": res["hard_failed"],
    },
    "artifacts": {
        "artifacts/worker-019/rev13_preflight/results.json": res_sha,
        "artifacts/worker-019/rev13_preflight/verify_rev13_repair.py": probe_sha,
        "artifacts/worker-019/rev13_preflight/README.md": readme_sha,
        "reviews/W019-rev13-preflight-review.json": rev_sha,
    },
    "event_ids": [e["event_id"] for e in events],
    "next_falsifier": res["next_falsifier"],
    "authority_note": res["authority_note"],
}
cp_path = os.path.join(ROOT, "runtime", "state", f"w019_rev13_preflight_checkpoint_{STAMP}.json")
json.dump(checkpoint, open(cp_path, "w"), indent=1, sort_keys=True)
with open(os.path.join(ROOT, "runtime", "state", "w019_rev13_preflight_checkpoints.jsonl"), "a") as f:
    f.write(json.dumps(checkpoint, sort_keys=True) + "\n")

print(json.dumps({
    "review_sha256": rev_sha, "results_sha256": res_sha, "probe_sha256": probe_sha,
    "readme_sha256": readme_sha, "checkpoint": cp_path,
    "events_appended": len(events), "event_ids": checkpoint["event_ids"],
}, indent=1))
