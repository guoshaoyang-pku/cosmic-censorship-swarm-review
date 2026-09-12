#!/usr/bin/env python3
"""Build evidence.json + reviews/F0-review-025.json from the raw probe outputs, and verify the
pins are still live before writing. Aborts (moving-target blocker) if any pin moved.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAW = HERE / "raw"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


fin = json.loads((RAW / "final_output.json").read_text())
live = {k: sha(ROOT / k) for k in fin["pins"]}
moved = {k: (fin["pins"][k]["sha256"], v) for k, v in live.items() if fin["pins"][k]["sha256"] != v}
if moved:
    print(json.dumps({"MOVING_TARGET": moved}, indent=1))
    raise SystemExit(2)

F0 = live["research_map/formulation_taxonomy.yaml"]
SUPP = live["artifacts/formulation/formulation_taxonomy.yaml"]
FROZEN_H = live["artifacts/formulation/FROZEN.json"]
F1 = live["schemas/af_wcc_vacuum.yaml"]
F2A = live["schemas/af_scc_c2_vacuum.yaml"]
F2B = live["schemas/af_scc_c0_vacuum.yaml"]
NOW = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")

REV_ID = "W025-F0-BIND-01"
TASK = "W025-F0-BIND-01"

file_hashes = {str(p.relative_to(ROOT)): sha(p) for p in
               [HERE / "probe_f0_binding.py", HERE / "recheck_f0_binding.py", HERE / "final_verify_f0.py",
                RAW / "probe_output.json", RAW / "recheck_output.json", RAW / "final_output.json"]}

findings = [
    {"id": "W025-F0-P1", "kind": "positive", "label": "G-F0 structural criteria met",
     "detail": "exactly the four frozen class ids; every class carries hypotheses, exclusions, conclusion_type and 3 test_cases; axes.conclusion_type == conclusion.type for all four; disjointness covers 6/6 class pairs with decisive axes and a data-space overlap note.",
     "evidence_refs": [f"research_map/formulation_taxonomy.yaml#{F0[:12]}",
                       f"artifacts/worker-025/f0_binding_review/raw/final_output.json#{file_hashes['artifacts/worker-025/f0_binding_review/raw/final_output.json'][:12]}"]},
    {"id": "W025-F0-P2", "kind": "positive", "label": "D1 discharged: no class asserts the demoted set-based predicate",
     "detail": "assertive-text classification (bracketed notes and quoted superseded wording removed): 0 of 4 conclusions assert the set-based J-(I+) predicate. The only two token occurrences are marked mentions: AF-WCC-VAC-GEN's disclosure that the set-based reading is variant SET, and AF-WCC-SCALAR-SPH's bracketed rev5 discharge note. AF-WCC-VAC-GEN and AF-WCC-SCALAR-SPH both carry the single-q TAIL predicate.",
     "evidence_refs": [f"research_map/formulation_taxonomy.yaml#{F0[:12]}",
                       "research_map/formulation_taxonomy.yaml:186-196",
                       "research_map/formulation_taxonomy.yaml:416-421"]},
    {"id": "W025-F0-P3", "kind": "positive", "label": "D3 discharged: comeager quantifier explicit and bound in all four classes",
     "detail": "all four conclusions quantify over an explicit comeager set G bound before the data; the D3 record's 'ALL FOUR classes' claim reproduces.",
     "evidence_refs": [f"research_map/formulation_taxonomy.yaml#{F0[:12]}"]},
    {"id": "W025-F0-P4", "kind": "positive", "label": "freeze/binding chain green at the bound hash",
     "detail": "FROZEN rev28 pins canonical 0abb9ed8 and supplement d7419b4e and verify_frozen.py exits 0 (44 files, 0 problems); all three schemas' class_contract_pointer now targets research_map/formulation_taxonomy.yaml#classes.<CID> and resolves, and f0_binding.declared_f0_sha256 == live canonical for all three; check_taxonomy_consistency.py exits 0; check_class_schema.py exits 0 on the three canonical schemas; class_separation.findings is empty on F0 and all three schemas; strict duplicate-key scan finds 0 duplicates in F0, supplement and schemas.",
     "evidence_refs": [f"artifacts/formulation/FROZEN.json#{FROZEN_H[:12]}",
                       f"research_map/formulation_taxonomy.yaml#{F0[:12]}",
                       f"schemas/af_wcc_vacuum.yaml#{F1[:12]}",
                       f"schemas/af_scc_c2_vacuum.yaml#{F2A[:12]}",
                       f"schemas/af_scc_c0_vacuum.yaml#{F2B[:12]}"]},
    {"id": "W025-F0-O1", "kind": "objection", "severity": "non-blocking",
     "label": "AF-WCC-SCALAR-SPH genericity_kind unresolved while its conclusion quantifies over a comeager set",
     "detail": "axes.genericity_kind='unresolved' and genericity_value_status='unresolved_pending_L1' coexist with an explicit comeager conclusion. The taxonomy consistency checker does not compare this field. Declared, owned by open question Q1 (F1/F2 with L1 input); not a gate criterion.",
     "evidence_refs": [f"research_map/formulation_taxonomy.yaml#{F0[:12]}"]},
    {"id": "W025-F0-O2", "kind": "objection", "severity": "non-blocking",
     "label": "author-declared status and side-by-side revision notes",
     "detail": "status is still 'draft_unverified' (author/controller housekeeping, not a reviewer field) and revision_note / revision_note_rev3 / revision_note_rev4 sit side by side (reader trap, harmless today).",
     "evidence_refs": [f"research_map/formulation_taxonomy.yaml#{F0[:12]}"]},
    {"id": "W025-F0-O3", "kind": "objection", "severity": "non-blocking",
     "label": "companion-pair split is a controller decision, not an F0 content defect",
     "detail": "canonical 0abb9ed8 != supplement d7419b4e; FROZEN rev28 keeps them as two logical artifacts and f0_mirror_adjudication_request (REC-1/REC-2) remains open. This accept binds the canonical artifact only and does not adjudicate mirror equality.",
     "evidence_refs": [f"artifacts/formulation/FROZEN.json#{FROZEN_H[:12]}",
                       "artifacts/formulation/evidence/f0_mirror_conflict.json"]},
    {"id": "W025-F0-O4", "kind": "process", "severity": "resolved",
     "label": "moving target observed mid-run, resolved by FROZEN rev28",
     "detail": "first probe (00:31-00:32) observed F0 276009f4 -> 0abb9ed8 (00:31:41), schemas -> cce9c601/5476a3f2/55d0a1ea (00:32:02), FROZEN rev26/rev27 drift (8 then 5 problems). By 00:35:08 FROZEN rev28 verifies 0 problems; the bound hashes were re-measured stable over a 20 s window plus three 15 s windows before this review was written.",
     "evidence_refs": [f"artifacts/worker-025/f0_binding_review/raw/probe_output.json#{file_hashes['artifacts/worker-025/f0_binding_review/raw/probe_output.json'][:12]}",
                       f"artifacts/worker-025/f0_binding_review/raw/recheck_output.json#{file_hashes['artifacts/worker-025/f0_binding_review/raw/recheck_output.json'][:12]}"]},
    {"id": "W025-F0-O5", "kind": "instrument", "severity": "resolved",
     "label": "two first-pass instrument defects self-caught and corrected",
     "detail": "(a) a token scan flagged the metalinguistic J-(I+) mentions as a D1 residue; corrected by assertive-text classification (0 assertive uses). (b) the first class-separation positive control used full class ids, which the detector intentionally does not flag; corrected to regularity-token merge fixtures (3/3 flagged) with split fixtures (0/2 flagged).",
     "evidence_refs": [f"artifacts/worker-025/f0_binding_review/raw/probe_output.json#{file_hashes['artifacts/worker-025/f0_binding_review/raw/probe_output.json'][:12]}"]},
]

next_falsifier = ("Refuted if, at 0abb9ed8 or a re-pinned successor, (a) any class conclusion asserts the "
                  "set-based J-(I+) predicate as its own, (b) the comeager quantifier is absent or unbound in any "
                  "of the four conclusions, (c) verify_frozen exits non-zero at the bound FROZEN or the FROZEN "
                  "logical_artifacts no longer pin the canonical bytes, or (d) a class-separation/consistency "
                  "checker flags a merge at the bound hash. Any hash move voids the binding (moving-target stop rule).")

evidence = {
    "schema": "w025-f0-binding-evidence/v1",
    "task_id": TASK,
    "review_id": REV_ID,
    "created_at": NOW,
    "reviewer": "worker-025",
    "reviewer_independence": "not an author of F0, F0-R, F1, F2a, F2b, the supplement, or any prior F0 verdict; own probes and canonical checkers on the pinned bytes",
    "node_id": "F0",
    "gate": "G-F0",
    "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
    "verdict": "accept",
    "score": 4.0,
    "counts_as_full_schema_verdict": True,
    "hard_failures": [],
    "pins": {"research_map/formulation_taxonomy.yaml": F0,
             "artifacts/formulation/formulation_taxonomy.yaml": SUPP,
             "artifacts/formulation/FROZEN.json": FROZEN_H,
             "schemas/af_wcc_vacuum.yaml": F1,
             "schemas/af_scc_c2_vacuum.yaml": F2A,
             "schemas/af_scc_c0_vacuum.yaml": F2B},
    "checks": {
        "exactly_four_class_ids": True,
        "per_class_slots_and_type_agree": True,
        "disjointness_pairs": "6/6",
        "D1_assertive_set_based_uses": 0,
        "D3_comeager_all_four": True,
        "verify_frozen_exit": 0,
        "taxonomy_consistency_exit": 0,
        "check_class_schema_exit": {"AF-WCC-VAC-GEN": 0, "AF-SCC-C2-VAC-GEN": 0, "AF-SCC-C0-VAC-GEN": 0},
        "classsep_findings": 0,
        "duplicate_keys": 0,
        "schemas_f0_binding_match_live": True,
        "class_contract_pointer_targets_canonical_classes": True,
        "stable_over_windows": "20s + 3x15s",
    },
    "findings": findings,
    "controls": {
        "C1_dupkey_detector": "PASS (positive duplicate detected, clean negative 0)",
        "C2_classsep": "PASS after correction (3/3 merge fixtures flagged, 0/2 split fixtures flagged)",
        "C3_freeze": "PASS (pins unchanged across the verification window)",
    },
    "moving_target_history": fin["first_pass_false_positive"] and {
        "F0": "276009f4 -> 0abb9ed8 at 00:31:41",
        "schemas": "9a8bd4c9/b6123750/1bb78ce9 -> cce9c601/5476a3f2/55d0a1ea at 00:32:02",
        "FROZEN": "rev26/rev27 drift 8/5 problems -> rev28 (2f358f67) 0 problems at 00:35:08",
        "status": "RESOLVED - review bound only to the settled hashes",
    },
    "next_falsifier": next_falsifier,
    "non_claims": ["no gate verdict (worker authority limit)", "no node done",
                   "no theorem/refutation", "F1/F2a/F2b not adjudicated here",
                   "mirror equality canonical==authoring not adjudicated (REC-1/REC-2, controller)"],
    "raw_outputs": file_hashes,
}
(HERE / "evidence.json").write_text(json.dumps(evidence, indent=1, ensure_ascii=False) + "\n")
EV_H = sha(HERE / "evidence.json")

review = {
    "review_id": REV_ID,
    "schema": "class-schema-review/v1",
    "reviewer": "worker-025",
    "reviewer_role": "bounded execution worker (independent; not an author of F0, F0-R, F1, F2a, F2b, the supplement, or any prior F0 verdict)",
    "created_at": NOW,
    "target_id": "F0",
    "node_id": "F0",
    "gate": "G-F0",
    "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
    "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
    "artifact_path": "research_map/formulation_taxonomy.yaml",
    "reviewed_sha256": F0,
    "artifact_sha256": F0,
    "counts_as_full_schema_verdict": True,
    "verdict": "accept",
    "score": 4.0,
    "hard_failures": [],
    "findings": findings,
    "evidence_refs": [f"research_map/formulation_taxonomy.yaml#{F0[:12]}",
                      f"artifacts/formulation/FROZEN.json#{FROZEN_H[:12]}",
                      f"schemas/af_wcc_vacuum.yaml#{F1[:12]}",
                      f"schemas/af_scc_c2_vacuum.yaml#{F2A[:12]}",
                      f"schemas/af_scc_c0_vacuum.yaml#{F2B[:12]}",
                      f"artifacts/worker-025/f0_binding_review/evidence.json#{EV_H[:12]}",
                      f"artifacts/worker-025/f0_binding_review/raw/final_output.json#{file_hashes['artifacts/worker-025/f0_binding_review/raw/final_output.json'][:12]}"],
    "falsifier": next_falsifier,
    "binding_caveat": "binds the canonical F0 artifact at 0abb9ed8 only; canonical != supplement is a controller REC-1/REC-2 decision, not adjudicated here",
    "authority": "review verdict only; the reviewer does not set gate verdicts or node status",
}
(ROOT / "reviews/F0-review-025.json").write_text(json.dumps(review, indent=1, ensure_ascii=False) + "\n")
REV_H = sha(ROOT / "reviews/F0-review-025.json")

sums = HERE / "SHA256SUMS"
lines = []
for rel, h in sorted(file_hashes.items()):
    lines.append(f"{h}  {rel}")
lines.append(f"{EV_H}  artifacts/worker-025/f0_binding_review/evidence.json")
lines.append(f"{REV_H}  reviews/F0-review-025.json")
sums.write_text("\n".join(lines) + "\n")

print(json.dumps({"F0": F0, "supplement": SUPP, "FROZEN": FROZEN_H, "evidence": EV_H, "review": REV_H,
                  "verdict": "accept", "score": 4.0, "hard_failures": []}, indent=1))
