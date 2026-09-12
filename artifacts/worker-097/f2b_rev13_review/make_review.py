#!/usr/bin/env python3
"""Regenerate REVIEW.json from the current report.json, rebinding every embedded hash.

Run after the final check_f2b_rev13.py run; do not re-run the checker afterwards or the
report hash embedded in REVIEW.json goes stale (the exact CF-20 evidence-binding failure mode).
"""
from __future__ import annotations

import hashlib
import json
import os

ART = os.path.dirname(os.path.abspath(__file__))


def sha(p: str) -> str:
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


rep = json.load(open(os.path.join(ART, "report.json")))
pins = rep["pins"]
pin = lambda path: pins[path]["live_sha256"]  # noqa: E731
ev = lambda p: f"{p}#sha256:{pin(p)}"  # noqa: E731

review = {
    "review_id": "w097-f2b-rev13-indep-review-20260912T0103",
    "created_at": "2026-09-12T01:04:00+08:00",
    "reviewer": "worker-097",
    "worker": "worker-097",
    "role": "bounded execution worker",
    "task_id": "W097-F2B-REV13-INDEP-REVIEW-01",
    "target_id": "F2b",
    "target_subnode": "F2b",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "node_id": "F2b",
    "gate": "G-FORM",
    "artifact": "schemas/af_scc_c0_vacuum.yaml",
    "artifact_sha256": pin("schemas/af_scc_c0_vacuum.yaml"),
    "artifact_mirror": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "artifact_mirror_sha256": pin("artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
    "artifact_revision": 13,
    "verdict": rep["verdict"],
    "score": rep["score"],
    "review_record_version": 2,
    "supersedes_review_sha256": "1bb9dff017a20866",
    "counts_as_full_schema_verdict": True,
    "hard_failures": [
        "W097-F2B-HF3 (blocking-for-accept): implication_ledger.forbidden_transfers[0].reason asserts "
        "'C2 is a strictly larger extension class', inverting the extension-class containment declared by the "
        "same artifact ('extension_class_containment: E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2') "
        "and by the F2a sibling ('E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0'). The row's "
        "conclusion ('C2-inextendibility is strictly weaker') is correct; the premise is inverted, so the "
        "forbidden-transfer rationale is self-contradictory. The defect survives the rev12->rev13 "
        "evidence-binding repair, whose revision note declares 'no class-semantics change'.",
        "W097-F2B-HF3b (blocking-for-accept, added in erratum round 2): regularity.must_not_conflate[0] "
        "(line 152) carries the live denial 'No containment with C2 or C0 is asserted here' while the same "
        "artifact asserts that containment at line 239 and line 250, and the supplement's axis_registry "
        "(line 145) declares the nested extension sets. The F2a sibling at line 152 marks the identical "
        "sentence as an R2-major error ('the earlier no containment with C2 is asserted was wrong'). "
        "Recommended repair: adopt F2a's corrected clause."
    ],
    "findings": [
        {"id": "W097-F2B-HF3", "severity": "hard", "axis": "internal containment-direction consistency",
         "where": "implication_ledger.forbidden_transfers[0].reason (line 246)",
         "measured": "C2 is a strictly larger extension class",
         "contradicts": ["implication_ledger.extension_class_containment (line 239)",
                         "one_way_entailments[2].reason (line 243)",
                         "non_vacuity.vacuity_falsifier (line 189)",
                         "c0_specifics.conclusion_relation_to_sibling (line 80)",
                         "schemas/af_scc_c2_vacuum.yaml:148,237"],
         "recommended_repair": "replace 'strictly larger' with 'strictly smaller' (or restate as "
                               "'E_C2 subset of E_C0'); no other change",
         "evidence": [ev("schemas/af_scc_c0_vacuum.yaml"), ev("schemas/af_scc_c2_vacuum.yaml"),
                      ev("research_map/formulation_taxonomy.yaml")]},
        {"id": "W097-F2B-HF3b", "severity": "hard", "axis": "live containment-denial vs asserted containment",
         "where": "regularity.must_not_conflate[0] (line 152)",
         "measured": "No containment with C2 or C0 is asserted here",
         "contradicts": ["implication_ledger.extension_class_containment (line 239)",
                         "implication_ledger.subsumption_note (line 250)",
                         "artifacts/formulation/formulation_taxonomy.yaml:145 axis_registry containment",
                         "schemas/af_scc_c2_vacuum.yaml:152 (same sentence marked R2-major wrong)"],
         "recommended_repair": "replace the clause with the F2a-repaired wording (nested extension sets "
                               "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0)",
         "evidence": [ev("schemas/af_scc_c0_vacuum.yaml"), ev("schemas/af_scc_c2_vacuum.yaml"),
                      ev("artifacts/formulation/formulation_taxonomy.yaml")]},
        {"id": "W097-F2B-F2", "severity": "minor", "axis": "vocabulary policy",
         "where": "conclusion.conclusion_type, genericity.kind, genericity.variants[*].kind",
         "finding": "accepted alias tokens (scc_c0_future_inextendibility, residual_comeager) are used in a "
                    "canonical artifact; VOCAB_ALIASES.json policy says aliases 'must never appear in a new "
                    "canonical artifact'. Consistency-check equivalent, not a class-semantics defect.",
         "evidence": [ev("artifacts/formulation/VOCAB_ALIASES.json")]},
        {"id": "W097-F2B-F3", "severity": "minor", "axis": "evidence binding",
         "where": "f0_binding.consistency_evidence -> artifacts/formulation/evidence/taxonomy_consistency.json",
         "finding": "the consistency evidence is a hash-free boolean (consistent=true over four named classes, "
                    "no input hashes or checked_at); its only byte binding is the sha256 declared in f0_binding, "
                    "which matches live and is pinned by FROZEN rev29. Content cannot be re-verified from the "
                    "file alone.",
         "evidence": [ev("artifacts/formulation/evidence/taxonomy_consistency.json"),
                      ev("artifacts/formulation/FROZEN.json")]},
        {"id": "W097-F2B-F4", "severity": "minor", "axis": "contract-vs-schema scope phrasing",
         "where": "F0 classes.AF-SCC-C0-VAC-GEN.conclusion.text vs quantifiers.domains.D0",
         "finding": "the declared F0 contract text quantifies over 'every admissible (s,delta)' while the "
                    "schema's D0 is a tagged disjoint union r = smooth or (sobolev,s,delta). Same phrasing gap "
                    "in F1/F2a; taxonomy_consistency.json reports no divergence. Owner to confirm the smooth "
                    "branch is intended in the contract text.",
         "evidence": [ev("research_map/formulation_taxonomy.yaml"), ev("schemas/af_scc_c0_vacuum.yaml")]},
        {"id": "W097-F2B-F5", "severity": "minor", "axis": "revision history",
         "where": "revision vs revision_history",
         "finding": "revision=13 with 11 history entries; the 2-revision gap is the documented rev12 key-collapse "
                    "(entry 9 'unused: true' carries rev11+rev8) and is identical in F1/F2a. Confirm intended and "
                    "that no revision delta is unrecorded.",
         "evidence": [ev("schemas/af_scc_c0_vacuum.yaml"), ev("schemas/af_scc_c2_vacuum.yaml")]},
    ],
    "positive_checks": {
        "H1_structure": "pass (no duplicate keys; last history entry at == revised_at)",
        "H2_class_identity": "pass (components reproduce AF-SCC-C0-VAC-GEN)",
        "H4_f0_binding": "pass (declared taxonomy 0abb9ed8a961 live; evidence 9e335e9ba1bf live; FROZEN rev29 "
                         "pins canonical+mirror+taxonomy+supplement+evidence+alias registry at live hashes)",
        "H5_pointers": "pass (classes.AF-SCC-C0-VAC-GEN and class_contracts.AF-SCC-C0-VAC-GEN both resolve)",
        "H6_quantifiers": "pass (forall-exists(comeager)-forall-not-exists; dual negation and NNF agree)",
        "H7_vocabulary": "pass alias-aware (canonical_target strong_cosmic_censorship_C0; baire_residual family)",
        "H8_mirror": "pass (canonical == mirror byte-identical)",
        "H9_sibling": "pass (sibling_disjoint_from mutual; taxonomy disjointness pair present)",
        "H10_review_status": "pass (gate G-FORM, requested reviewers present)",
    },
    "controls": {
        "pass": "10/10",
        "detail": "artifacts/worker-097/f2b_rev13_review/report.json#controls (K1 repair-responsiveness of H3, "
                  "K2/K3/K4 mutation detections, K5 duplicate-key injection, K6 mirror divergence, K7 determinism, "
                  "K8 fail-closed on empty doc, K9 H3b repair-marker responsiveness)"},
    "instrument_amendments": "AMENDMENTS.md - (1) run 1 preserved as report.run1_pre_amendment.json (verdict 2.5, "
                             "hard H1/H3/H5); H1 and H5 were adjudicated as instrument false positives (documented "
                             "family conventions), H3 de-duplicated across overlapping patterns; run 2 verdict 3.5. "
                             "(2) erratum round 2: a live containment-denial check H3b was added after an independent "
                             "peer review found the line-152 clause; run 2 preserved as report.run2_pre_erratum.json; "
                             "current verdict 3.0 with H3 and H3b as hard failures.",
    "pins": {p: pins[p]["live_sha256"] for p in pins},
    "independence": "Not an author of F2b, F1, F2a, the F0 taxonomy, the supplement, VARIANT_REGISTRY.json, "
                    "FROZEN.json or the rev13 repair tool. Instrument check_f2b_rev13.py written from scratch for "
                    "this task; it does not import research_map/class_separation.py, "
                    "artifacts/formulation/tools/check_class_schema.py, check_taxonomy_consistency.py, or any other "
                    "agent's checker. The HF3 finding was re-derived from the primary bytes before pre-registration; "
                    "the HF3b line-152 clause was found first by an independent peer review of the same hash "
                    "(reviews/F2b-review-worker-018-rev13.json) after round 1, then re-derived here from the primary "
                    "bytes and given a dedicated instrument check before this record was re-emitted.",
    "authority_note": "worker verdict; does not set node status=done, validation_status=passed, a node verdict, or "
                      "any gate verdict",
    "falsifier": "A re-run of the instrument at the same pins with a different H3 inverted_paths census or verdict; "
                 "a mutation control the instrument fails to catch; or a reading showing 'C2 is a strictly larger "
                 "extension class' is consistent with the artifact's own extension_class_containment. A later "
                 "revision hash voids this verdict as advisory only.",
    "next_falsifier": "Owner repair of line 246 (larger -> smaller) then a re-review at the new revision; or a "
                      "second independent checker that does not detect the line-246 inversion.",
    "limits": rep["limits"],
    "evidence_refs": [
        f"artifacts/worker-097/f2b_rev13_review/report.json#sha256:{sha(os.path.join(ART, 'report.json'))}",
        f"artifacts/worker-097/f2b_rev13_review/check_f2b_rev13.py#sha256:{sha(os.path.join(ART, 'check_f2b_rev13.py'))}",
        f"artifacts/worker-097/f2b_rev13_review/PREREGISTRATION.md#sha256:{sha(os.path.join(ART, 'PREREGISTRATION.md'))}",
        f"artifacts/worker-097/f2b_rev13_review/AMENDMENTS.md#sha256:{sha(os.path.join(ART, 'AMENDMENTS.md'))}",
        ev("schemas/af_scc_c0_vacuum.yaml"), ev("schemas/af_scc_c2_vacuum.yaml"),
    ],
}
with open(os.path.join(ART, "REVIEW.json"), "w") as fh:
    json.dump(review, fh, indent=2, sort_keys=True)
    fh.write("\n")
print(json.dumps({"REVIEW.json": "rewritten", "report_sha256": sha(os.path.join(ART, "report.json"))[:16],
                  "review_sha256": sha(os.path.join(ART, "REVIEW.json"))[:16],
                  "hard_failures": len(review["hard_failures"])}, indent=1))
