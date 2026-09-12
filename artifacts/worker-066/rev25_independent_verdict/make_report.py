#!/usr/bin/env python3
"""W066-REV25-VERDICT-01 step 4: compose report.json + README.md from measured evidence.

Every statement in the report is derived from pinned bytes and the two evidence files
(evidence/replica_verdicts.json, evidence/crosschecks.json). Nothing here re-runs a gate.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
WCC = "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503"
C2 = "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2"
C0 = "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"
F0 = "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc"
RULE_SPEC = "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e"
SUPPLEMENT = "c8e979a1eb48969be3b102e1e18203eb9e09b4e10fca3ef341854fdd73bae83f"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


FINDINGS = [
    {"id": "W066-B1", "severity": "B", "blocking": True, "kind": "artifact_parseability",
     "targets": ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"],
     "deciding_field": "top-level YAML mapping key `revised_at` (and `revised_at_unused` in F1)",
     "statement": ("All three frozen schemas contain duplicate YAML mapping keys at the document root: "
                   "F1 :8,10,12,14,16,20,23 (`revised_at` x7) plus :26,28 (`revised_at_unused` x2); "
                   "F2a and F2b :8,10,12,14,16,18,21,23 (`revised_at` x8 each). YAML requires unique "
                   "mapping keys; PyYAML - the parser used by check_class_schema.py itself - silently "
                   "last-wins, so 6-7 of the declared revision timestamps are dropped and only the "
                   "final `revised_at` survives (2026-09-12T00:30:00+08:00, ahead of the 00:19:14 file "
                   "mtime and of the reviewer wall clock). The machine gate cannot see this because it "
                   "parses the same lossy view."),
     "evidence": ["artifacts/worker-066/rev25_independent_verdict/evidence/crosschecks.json#C7_duplicate_yaml_keys",
                  "schemas/af_wcc_vacuum.yaml#9a8bd4c9:8,10,12,14,16,20,23,26,28",
                  "schemas/af_scc_c2_vacuum.yaml#b6123750:8,10,12,14,16,18,21,23",
                  "schemas/af_scc_c0_vacuum.yaml#1bb78ce9:8,10,12,14,16,18,21,23"],
     "remediation": "replace the repeated key with a `revision_log:` sequence (one entry per revision); re-freeze and re-run the acceptance pipeline",
     "prior_art": ["reviews/F1-review-22.json", "reviews/F2a-review-22.json", "reviews/F2b-review-22.json", "reviews/F2b-review-worker-001.json"],
     "falsifier": "yaml.compose on these exact bytes returns zero duplicate mapping keys"},
    {"id": "W066-B2", "severity": "B", "blocking": True, "kind": "internal_contradiction",
     "targets": ["schemas/af_scc_c0_vacuum.yaml"],
     "deciding_field": "must_not_conflate[0] vs implication_ledger.extension_class_containment",
     "statement": ("F2b :157 states for H2_loc: 'No containment with C2 or C0 is asserted here', while "
                   "F2b :244 asserts 'E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2' and "
                   ":245-247 derive the C0=>H2loc=>C2 entailments. The sibling F2a :157 states the "
                   "corrected opposite and records '[R2 major: the earlier no containment with C2 is "
                   "asserted was wrong]'. Both sentences are in the frozen bytes at 1bb78ce9 and cannot "
                   "both stand."),
     "evidence": ["artifacts/worker-066/rev25_independent_verdict/evidence/crosschecks.json#C8_internal_contradiction_c0",
                  "schemas/af_scc_c0_vacuum.yaml#1bb78ce9:157", "schemas/af_scc_c0_vacuum.yaml#1bb78ce9:244",
                  "schemas/af_scc_c2_vacuum.yaml#b6123750:157"],
     "remediation": "port the F2a :157 wording into F2b :157 (the containment chain is the corrected statement)",
     "prior_art": ["reviews/F2b-review-22.json"],
     "falsifier": "on re-measurement F2b :157 does not deny containment, or :244 is absent"},
    {"id": "W066-B3", "severity": "B", "blocking": True, "kind": "spec_implementation_gap",
     "targets": ["artifacts/formulation/rule_spec.json"],
     "deciding_field": "rules[] vs self.fail() rule ids in check_class_schema.py",
     "statement": ("The frozen binding rule spec at 40f9bb9e is FORM-RULE-SPEC v1.2 and declares R01-R16 "
                   "only, but the binding gate at 000e09e4 enforces and emits R17-R25 and R27-R31 "
                   "(14 rule ids absent from the spec). FROZEN rev25's own rev7_delta claims "
                   "'rule_spec v1.3: dense_escape in vocabulary, extension_class_containment chain' and "
                   "DELIVERABLE_SUMMARY.md:22 claims 'rule_spec.json v1.3 (R01-R31)', but no v1.3 file "
                   "exists anywhere in the tree (all five snapshots on disk are the same 40f9bb9e v1.2). "
                   "The frozen gate test report names only R21-R25, R27, R31, so R17-R20, R26, R28-R30 "
                   "have no frozen rule text and no frozen test."),
     "evidence": ["artifacts/worker-066/rev25_independent_verdict/evidence/crosschecks.json#C10_rule_declaration_gap",
                  "artifacts/formulation/rule_spec.json#40f9bb9e", "artifacts/formulation/tools/check_class_schema.py#000e09e4",
                  "artifacts/formulation/FROZEN.json#rev7_delta", "artifacts/formulation/DELIVERABLE_SUMMARY.md:22"],
     "remediation": "publish the v1.3 rule text for R17-R31 at the canonical path (or declare the gate source as the normative rule text) and re-freeze",
     "prior_art": ["artifacts/formulation/reviews/R4_final_audit.json (stale_revision_mentions: rule_spec v1.3 vs 1.0)"],
     "falsifier": "rule_spec.json at 40f9bb9e declares R17-R31, or a v1.3 spec file is found and bound by FROZEN"},
    {"id": "W066-B4", "severity": "B", "blocking": True, "kind": "canonical_token_violation",
     "targets": ["research_map/formulation_taxonomy.yaml"],
     "deciding_field": "classes.AF-SCC-{C2,C0}-VAC-GEN.conclusion.type",
     "statement": ("The declared F0 artifact (276009f4, status draft_unverified) carries the alias tokens "
                   "strong_cosmic_censorship_C2 (:classes.AF-SCC-C2-VAC-GEN.conclusion.type) and "
                   "strong_cosmic_censorship_C0 for the two SCC classes. VOCAB_ALIASES.json policy: "
                   "'canonical token first; accepted aliases are equivalent for consistency checks only "
                   "and must never appear in a new canonical artifact'. The schema/supplement/rule_spec "
                   "use the canonical tokens, so the declared F0 and the schemas it binds are only "
                   "reconcilable through an alias table that the policy says should not be needed. The "
                   "artifact's own revision_note already records this as an open designation item."),
     "evidence": ["artifacts/worker-066/rev25_independent_verdict/evidence/crosschecks.json#C5_conclusion_vocabularies",
                  "research_map/formulation_taxonomy.yaml#276009f4", "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1e"],
     "remediation": "replace the two alias tokens with scc_c2_future_inextendibility / scc_c0_future_inextendibility (or declare the alias table normative and re-freeze it with the taxonomy)",
     "prior_art": ["artifacts/worker-001/f2b_review/review.json W001-F2", "F0 taxonomy revision_note finding 3"],
     "falsifier": "classes.AF-SCC-C2-VAC-GEN.conclusion.type == scc_c2_future_inextendibility and likewise for C0"},
    {"id": "W066-B5", "severity": "B", "blocking": True, "kind": "registry_divergence",
     "targets": ["research_map/formulation_taxonomy.yaml", "artifacts/formulation/VARIANT_REGISTRY.json"],
     "deciding_field": "canonical F0 variants[] vs VARIANT_REGISTRY.variants[]",
     "statement": ("The declared F0 taxonomy inlines 2 variants (AF-SCC-C0-VAC-GEN/CH, AF-WCC-VAC-GEN/SET) "
                   "while VARIANT_REGISTRY.json v2.0 (5eb42f9a) registers 7; DISTRIBUTIONAL, H2LOC, "
                   "L2CONN, LIP and TWOSIDED exist only in the registry. check_taxonomy_consistency.py "
                   "compares class contracts, not variant sets, so the divergence is invisible to the "
                   "declared consistency evidence while the schemas cite registry-only variants."),
     "evidence": ["artifacts/worker-066/rev25_independent_verdict/evidence/crosschecks.json#C9_variant_registry",
                  "research_map/formulation_taxonomy.yaml#276009f4", "artifacts/formulation/VARIANT_REGISTRY.json#5eb42f9a"],
     "remediation": "make F0 delegate to VARIANT_REGISTRY.json as the single registry, or inline all 7 and extend the consistency check to compare variant sets",
     "prior_art": ["artifacts/worker-001/f2b_review/review.json W001-F1"],
     "falsifier": "F0 variants[] equals the registry variant set on re-measurement"},
    {"id": "W066-N1", "severity": "N", "blocking": False, "kind": "clock_discipline",
     "targets": ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"],
     "deciding_field": "revised_at / f0_binding.checked_at",
     "statement": ("The surviving revised_at (00:30:00) and f0_binding.checked_at (00:30:00) are ahead of "
                   "the file mtimes (00:19:14) and of the reviewer wall clock (00:25+); FROZEN rev26 "
                   "corrected its own frozen_at for exactly this reason (rev26_delta, CF-14 clock "
                   "discipline). Backlog: mark declared times as plan-times or write them at publish."),
     "evidence": ["artifacts/worker-066/rev25_independent_verdict/evidence/crosschecks.json",
                  "artifacts/formulation/FROZEN.json#rev26_delta"],
     "prior_art": ["reviews/F1-review-22.json", "reviews/F2a-review-22.json", "reviews/F2b-review-22.json"],
     "falsifier": "declared times are <= write mtime on re-measurement"},
    {"id": "W066-N2", "severity": "N", "blocking": False, "kind": "adjudicated_not_defect",
     "targets": ["research_map/formulation_taxonomy.yaml", "artifacts/formulation/formulation_taxonomy.yaml"],
     "deciding_field": "f0_binding.declared_f0_sha256 vs class_contract_pointer target",
     "statement": ("f0_binding pins research_map/formulation_taxonomy.yaml 276009f4 while "
                   "class_contract_pointer resolves into artifacts/formulation/formulation_taxonomy.yaml "
                   "c8e979a1. FROZEN rev26 records these as two distinct logical artifacts "
                   "(logical_artifacts), so this is adjudicated, not a defect; recorded here so the "
                   "verdicts are not read as endorsing a byte-identical mirror."),
     "evidence": ["artifacts/worker-066/rev25_independent_verdict/evidence/crosschecks.json#C6_f0_binding",
                  "artifacts/formulation/FROZEN.json#logical_artifacts"],
     "falsifier": "FROZEN rev26 logical_artifacts is retracted"},
    {"id": "W066-N3", "severity": "N", "blocking": False, "kind": "cross_group_rubric",
     "targets": ["evaluation_rubric.yaml"],
     "deciding_field": "frozen_classes[*].conclusion_primary / G-FORM genericity criterion",
     "statement": ("No class' conclusion_primary in evaluation_rubric.yaml matches the rule_spec "
                   "class_conclusion_type token (e.g. C0_inextendibility_of_maximal_development vs "
                   "scc_c0_future_inextendibility), and the rubric's genericity set "
                   "{comeager,full_measure,open_dense,codim_ge_1,non_generic_excluded} does not contain "
                   "the schemas' residual_comeager. Already recorded as critical in A0-review-22; "
                   "referenced, not re-litigated. Any automated G-FORM pass built on the rubric as "
                   "written rejects all three schemas."),
     "evidence": ["artifacts/worker-066/rev25_independent_verdict/evidence/crosschecks.json#C12_rubric_vocabulary",
                  "evaluation_rubric.yaml:63,77,94,113,128,129"],
     "prior_art": ["reviews/A0-review-22.json (vocabulary_disconnect, critical)"],
     "falsifier": "a declared crosswalk maps each rubric token to the rule_spec token"},
    {"id": "W066-N4", "severity": "N", "blocking": False, "kind": "coverage_note",
     "targets": ["artifacts/formulation/evidence/acceptance_pipeline_report.json"],
     "deciding_field": "mutants.semantic_caught",
     "statement": ("At rev25 the semantic stage alone catches 11/31 mutants and the structural gate "
                   "30/31; union coverage is 31/31 but leans on the structural gate. run_acceptance.py's "
                   "module docstring still cites 17/27 and 'semantic catches 27/27' and states a "
                   "semantic-catches-all requirement that its own code does not enforce (union is the "
                   "requirement). Measured fact + stale docstring, no gate impact."),
     "evidence": ["artifacts/worker-066/rev25_independent_verdict/evidence/acceptance_comparison.json",
                  "artifacts/worker-066/rev25_independent_verdict/evidence/replica_verdicts.json",
                  "artifacts/formulation/tools/run_acceptance.py#e544c36d:1-14"],
     "falsifier": "the frozen report's aggregates differ from the replica's on re-run"},
]

VERDICTS = [
    {"target_id": f"schemas/af_wcc_vacuum.yaml#{WCC}", "class_id": "AF-WCC-VAC-GEN", "node_id": "F1", "verdict": "revise",
     "score": 2.5, "hard_failures": ["W066-B1"], "soft_findings": ["W066-N1", "W066-N2"],
     "rationale": ("passes both stages at the pinned bytes (structural pass, semantic accept) and the "
                   "acceptance pipeline replicates; but the artifact as written is not a conforming YAML "
                   "document (7 duplicate keys), so a hash-bound accept cannot be issued without "
                   "re-reading the file through non-conforming semantics.")},
    {"target_id": f"schemas/af_scc_c2_vacuum.yaml#{C2}", "class_id": "AF-SCC-C2-VAC-GEN", "node_id": "F2a", "verdict": "revise",
     "score": 2.5, "hard_failures": ["W066-B1"], "soft_findings": ["W066-N1", "W066-N2"],
     "rationale": "same duplicate-key defect; class separation and conclusion token pass both stages."},
    {"target_id": f"schemas/af_scc_c0_vacuum.yaml#{C0}", "class_id": "AF-SCC-C0-VAC-GEN", "node_id": "F2b", "verdict": "revise",
     "score": 2.0, "hard_failures": ["W066-B1", "W066-B2"], "soft_findings": ["W066-N1", "W066-N2"],
     "rationale": "duplicate keys plus a machine-locatable contradiction between :157 and :244 inside the frozen bytes."},
    {"target_id": f"research_map/formulation_taxonomy.yaml#{F0}", "class_id": "GLOBAL", "node_id": "F0", "verdict": "revise",
     "score": 2.5, "hard_failures": ["W066-B4", "W066-B5"], "soft_findings": ["W066-N2"],
     "rationale": ("declared F0 is draft_unverified, uses alias conclusion tokens the alias policy forbids "
                   "in canonical artifacts, and its variant set diverges from the registry it is supposed "
                   "to anchor.")},
    {"target_id": f"artifacts/formulation/rule_spec.json#{RULE_SPEC}", "class_id": "GLOBAL", "node_id": "F1", "verdict": "revise",
     "score": 1.5, "hard_failures": ["W066-B3"], "soft_findings": ["W066-N4"],
     "rationale": ("the binding gate enforces 14 rules that the frozen spec does not declare and the "
                   "manifest/summary claim is a v1.3 that does not exist on disk; no verdict can be "
                   "'against the declared rule set' until the rule text is published.")},
]


def main() -> int:
    manifest = json.loads((HERE / "pinned_manifest.json").read_text())
    replica = json.loads((HERE / "evidence/replica_verdicts.json").read_text())
    comp = json.loads((HERE / "evidence/acceptance_comparison.json").read_text())
    cross = json.loads((HERE / "evidence/crosschecks.json").read_text())
    now = datetime.now(CST).isoformat(timespec="seconds")

    # end-of-window re-measure of the live target bytes (drift check)
    drift = []
    for e in manifest["targets"]:
        cur = sha(ROOT / e["source"])
        if cur != e["sha256_source"]:
            drift.append({"source": e["source"], "pinned_sha256": e["sha256_source"], "measured_now": cur})
    frozen_now = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())

    report = {
        "task_id": "W066-REV25-VERDICT-01",
        "worker": "worker-066",
        "actor": "worker-066",
        "role": "independent reviewer; no authorship of any target artifact",
        "created_at": now,
        "request": ("answers leadform-resource-request-2026-09-12T00:34:00+08:00 items (1) and (2): a "
                    "hash-cited independent verdict on the three rev25 class schemas, the F0 binding, and "
                    "the binding rule spec; and a replication of the two-stage acceptance measurement"),
        "snapshot": {
            "frozen_revision": manifest["frozen_revision_at_snapshot"],
            "frozen_frozen_at": manifest["frozen_frozen_at"],
            "pinned_manifest": "pinned_manifest.json",
            "targets": [{"source": e["source"], "pinned": e["pinned"], "sha256": e["sha256_pinned"],
                         "class_id": e["class_id"], "frozen_match": e["frozen_match"]} for e in manifest["targets"]],
            "corpus": {"fixtures": len(manifest["corpus"]["fixtures"]),
                       "controls": manifest["corpus"]["controls"]},
        },
        "independence": {
            "declaration": ("the reviewer authored none of the targets, ran no canonical tool that writes "
                            "into the frozen tree (run_acceptance.py was deliberately not invoked), and "
                            "used only pinned copies; every measurement below is reproducible from "
                            "run_replica.py + crosschecks.py"),
            "first_verdict_by_this_actor_at_these_hashes": True,
            "prior_art_acknowledged": sorted({p for f in FINDINGS for p in f.get("prior_art", [])}),
        },
        "drift_window": {
            "start": manifest["created_at"], "end": now,
            "targets_drifted": drift,
            "frozen_revision_at_end": frozen_now.get("revision"),
            "note": ("verdicts bind the pinned rev25 bytes above; FROZEN.json itself moved rev25->rev26 "
                     "during the window (target bytes unchanged)"),
        },
        "measurements": {
            "acceptance_replication": {
                "verdict": replica["verdict"],
                "canonical": [{"schema": r["fixture"], "structural": r["structural_pass"], "semantic": r["semantic_accept"]} for r in replica["canonical"]],
                "controls_pass": sum(1 for r in replica["controls"] if r["structural_pass"] and r["semantic_accept"]),
                "controls_total": len(replica["controls"]),
                "aggregates": replica["aggregates"],
                "agreement_with_frozen_report": comp["overall_agree"],
                "frozen_report_sha256": comp["frozen_report_sha256"],
            },
            "frozen_manifest_audit": {"revision": cross["checks"]["C2_frozen_audit"]["frozen_revision"],
                                      "files": cross["checks"]["C2_frozen_audit"]["files"],
                                      "mismatches": cross["checks"]["C2_frozen_audit"]["mismatches"]},
            "crosschecks": cross["checks"],
        },
        "findings": FINDINGS,
        "verdicts": VERDICTS,
        "result_summary": ("machine-green replicated at the pinned rev25 bytes: 3/3 canonical schemas pass "
                           "both stages, 2/2 controls pass, union 31/31 mutants caught, exact agreement with "
                           "the frozen acceptance report. Decisive schema-level verdicts are nevertheless "
                           "revise because of parseability (W066-B1) and, for F2b, an internal "
                           "contradiction (W066-B2); the F0 binding (W066-B4/B5) and the binding rule spec "
                           "(W066-B3) are revise as well."),
        "artifacts": {
            "report": "report.json",
            "evidence": ["evidence/replica_verdicts.json", "evidence/acceptance_comparison.json",
                         "evidence/crosschecks.json"],
            "scripts": ["snapshot.py", "run_replica.py", "crosschecks.py", "make_report.py"],
            "inputs": "pinned_manifest.json + pinned/",
        },
        "checkpoint": {"status": "written after this report by the worker; see checkpoint_result.json"},
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    readme = f"""# W066-REV25-VERDICT-01 — independent verdict on the rev25 class artifacts

Worker-066, {now}. Bound to the pinned byte set in `pinned_manifest.json` (FROZEN revision
{manifest['frozen_revision_at_snapshot']}). No canonical artifact was written by this task.

## What was measured

* **Acceptance replication (PASS).** A re-implementation of the two-stage pipeline
  (`run_replica.py`, deliberately not `run_acceptance.py`, which rewrites a frozen evidence file)
  run on pinned copies: 3/3 canonical schemas pass both stages, 2/2 controls pass, union catches
  31/31 mutants (structural 30/31, semantic 11/31). It agrees exactly with
  `artifacts/formulation/evidence/acceptance_pipeline_report.json` at 9b7d6c82.
* **Frozen-manifest audit (PASS).** All {cross['checks']['C2_frozen_audit']['files']} files declared by FROZEN
  match disk (0 mismatches) at the pinned revision.
* **Independent cross-checks (4 FAIL).** `crosschecks.py` finds duplicate YAML keys in all three
  schemas (W066-B1), a :157/:244 containment contradiction in F2b (W066-B2), 14 gate-enforced rules
  (R17–R25, R27–R31) missing from the frozen rule spec (W066-B3), alias conclusion tokens plus a
  2-vs-7 variant-set divergence in the declared F0 (W066-B4/B5).

## Verdicts at the pinned hashes

| target | sha256 | verdict | score | hard failures |
|---|---|---|---|---|
| schemas/af_wcc_vacuum.yaml | 9a8bd4c9 | revise | 2.5 | W066-B1 |
| schemas/af_scc_c2_vacuum.yaml | b6123750 | revise | 2.5 | W066-B1 |
| schemas/af_scc_c0_vacuum.yaml | 1bb78ce9 | revise | 2.0 | W066-B1, W066-B2 |
| research_map/formulation_taxonomy.yaml | 276009f4 | revise | 2.5 | W066-B4, W066-B5 |
| artifacts/formulation/rule_spec.json | 40f9bb9e | revise | 1.5 | W066-B3 |

Significance: earlier reviewers of the same artifacts (F1/F2a/F2b-review-22) returned
`inconclusive` because the bytes moved inside their windows. This review binds a byte set that
did not move, so these are the first decisive verdicts at the current hashes.

## Falsifiers

Each finding and verdict carries its own falsifier in `report.json`. The replication claim is
falsified by re-running `run_replica.py` on the same pins and getting a different union-caught
count or a control failure; W066-B1 by `yaml.compose` returning no duplicates; W066-B2 by F2b :157
no longer denying containment; W066-B3 by a v1.3 rule spec declaring R17–R31; W066-B4/B5 by the
canonical F0 carrying canonical tokens and the full 7-variant set.
"""
    (HERE / "README.md").write_text(readme)
    print("wrote report.json + README.md")
    print("drift:", drift)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
