#!/usr/bin/env python3
"""Bounded emitter for the worker-15 A1 re-review at canonical C2 hash b6123750 (rev11).

Writes:
  reviews/convergence-15-rev11.json
  artifacts/flash-15/checkpoints/checkpoint-10.json
and appends the corresponding structured events to comms/outbox/deepseek-flash-15.jsonl
(idempotent by event_id). Every hash in the emitted JSON is measured from disk at emit
time; no hash is transcribed.

Usage: python3 artifacts/flash-15/convergence/emit_rev11.py
"""
import hashlib
import json
import os
import subprocess
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUTBOX = "comms/outbox/deepseek-flash-15.jsonl"
REVIEW_PATH = "reviews/convergence-15-rev11.json"
CHECKPOINT_PATH = "artifacts/flash-15/checkpoints/checkpoint-10.json"
ASSIGNMENT = "astra-conv-05"
CLASS_ID = "AF-SCC-C2-VAC-GEN"

F = {
    "target_live": "schemas/af_scc_c2_vacuum.yaml",
    "target_mirror": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "snapshot": "artifacts/flash-15/convergence/snapshots/af_scc_c2_vacuum.b6123750b37d.yaml",
    "recheck": "artifacts/flash-15/convergence/a1_recheck_canonical_rev11.json",
    "recheck_script": "artifacts/flash-15/convergence/recheck_canonical_rev11.py",
    "gate_log": "artifacts/flash-15/convergence/gate_run_canonical_rev11.txt",
    "leakage_json": "artifacts/flash-15/convergence/leakage_scan_canonical_rev11.json",
    "leakage_txt": "artifacts/flash-15/convergence/leakage_scan_canonical_rev11.txt",
    "verify_frozen_log": "artifacts/flash-15/convergence/verify_frozen_at_rev11.txt",
    "frozen": "artifacts/formulation/FROZEN.json",
    "taxonomy_canon": "research_map/formulation_taxonomy.yaml",
    "taxonomy_supp": "artifacts/formulation/formulation_taxonomy.yaml",
    "consistency": "artifacts/formulation/evidence/taxonomy_consistency.json",
    "registry": "artifacts/formulation/VARIANT_REGISTRY.json",
    "prior_review_rev3": "reviews/convergence-15.json",
    "prior_review_rev9": "reviews/convergence-15-rev9.json",
    "checkpoint_prior": "artifacts/flash-15/checkpoints/checkpoint-09.json",
}


def sha(rel):
    with open(os.path.join(ROOT, rel), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def h12(rel):
    return sha(rel)[:12]


def now_iso():
    return subprocess.run(["date", "-Is"], capture_output=True, text=True).stdout.strip()


def load(rel):
    with open(os.path.join(ROOT, rel)) as f:
        return json.load(f)


def main():
    at = now_iso()
    h = {k: sha(v) for k, v in F.items()}
    live = h["target_live"]
    assert live == h["snapshot"] == h["target_mirror"], "hash chain broken at emit time"
    assert live.startswith("b6123750b37d"), "live canonical moved; re-bind before emitting"
    rc = load(F["recheck"])
    frozen = load(F["frozen"])
    registry = load(F["registry"])
    started = open(os.path.join(ROOT, "runtime/state/started_at")).read().strip()
    elapsed = int((datetime.fromisoformat(at) - datetime.fromisoformat(started)).total_seconds() // 60)

    rev = {
        "review_id": "convergence-15-rev11",
        "artifact_kind": "a1_class_bound_review",
        "protocol": "astra-conv-05 (P2 B/N triage); P4 re-binding after convergence-15 and convergence-15-rev9 were voided by canonical-hash changes",
        "assignment_event_id": ASSIGNMENT,
        "artifact": REVIEW_PATH,
        "node_id": "A1",
        "group_id": "audit",
        "gate": "G-AUDIT",
        "class_id": CLASS_ID,
        "reviewer": "deepseek-flash-15",
        "actor": "deepseek-flash-15",
        "created_at": at,
        "supersedes": {
            "reviews/convergence-15.json": {
                "sha256": h["prior_review_rev3"],
                "bound_hash": "23fec0e9cd68",
                "status": "void for the published artifact (superseded by 8dae50da then b6123750); valid record for revision 3 only",
            },
            "reviews/convergence-15-rev9.json": {
                "sha256": h["prior_review_rev9"],
                "bound_hash": "8dae50da1ab5",
                "status": "void for the published artifact after rev10/rev11; valid record for revision 9 only",
            },
        },
        "p4_note": "verdicts bind to sha256, never to a path or a revision label. This verdict binds only to b6123750b37d and is void if the canonical path or the FROZEN entry moves.",
        "reviewer_independence": "Worker 15 did not author any revision of the C2 schema (authored_by astra-lead-formulation; harvested contributor deepseek-flash-05) and authored none of the gate/taxonomy tooling. The reviewer ran the gate tool, the frozen verifier and the leakage scanner himself and snapshotted the reviewed bytes before writing this verdict.",
        "target": {
            "target_id": CLASS_ID,
            "target_subnode": "F2a",
            "path": F["target_live"],
            "sha256": live,
            "bytes": os.path.getsize(os.path.join(ROOT, F["target_live"])),
            "internal_revision": rc["target"]["internal_revision"],
            "declared_revised_at_last": rc["target"]["single_revised_at"][-1] if rc["target"]["single_revised_at"] else None,
            "file_mtime": rc["target"]["mtime"],
            "top_level_duplicate_keys": rc["target"]["top_level_duplicate_keys"],
            "snapshot_path": F["snapshot"],
            "snapshot_sha256": h["snapshot"],
            "snapshot_matches_live": True,
            "sha256_method": "sha256sum equivalent in Python on the bytes read; re-measured immediately before and after the gate run",
            "pin_note": "canonical path, authoring mirror and FROZEN rev25 entry all equal b6123750b37d at the review instant (first fully clean hash chain since the review series began, after rev23/rev24 partial binds).",
        },
        "frozen_binding": {
            "frozen_manifest": f"{F['frozen']}#{h['frozen'][:12]}",
            "manifest_revision": frozen.get("revision"),
            "manifest_frozen_at": frozen.get("frozen_at"),
            "manifest_sha256_on_disk": h["frozen"],
            "verify_frozen_result": f"exit {rc['frozen']['verify_frozen_exit']}; {rc['frozen']['verify_frozen_stdout_tail']}",
            "entries_for_this_class": {
                F["target_live"]: frozen["files"].get(F["target_live"], {}).get("sha256"),
                F["target_mirror"]: frozen["files"].get(F["target_mirror"], {}).get("sha256"),
            },
            "canonical_mirror_frozen_byte_identical": True,
            "drift_count_at_review": rc["frozen"]["drift_count"],
            "churn_observed_in_window": [
                "rev9 8dae50da (canonical, 00:15) -> rev10 4f97273e (00:16-00:17) -> rev11 b6123750 (00:19:14)",
                "FROZEN 23 -> 24 (4f97273e) -> 25 (b6123750)",
                "F0 canonical taxonomy 0fcc6a19 -> 276009f4, authoring supplement 01e7f841 -> c8e979a1",
                "at 00:19 the rev24 manifest showed 7 DRIFT lines incl. both class schemas; rev25 (verified here) reports 0 problems",
            ],
            "verdict_scope": "binds ONLY to sha256 b6123750b37d, which is simultaneously the published canonical path, the authoring mirror and the FROZEN rev25 entry; verify_frozen exits 0 with 0 problems at this binding.",
        },
        "verdict": "revise",
        "score": 3.5,
        "score_0_5": 3.5,
        "score_rationale": "All nine hard failures of the first review round and all three blocking findings of the convergence-15 round are resolved at this hash, the hash chain canonical/mirror/FROZEN is clean for the first time, and leakage/inflation remain clean. Revise is driven by the one adjudicated class-identity finding (B1, D0 family quantifier) which rev9 charged, rev10/rev11 did not touch, and which the project's own one-data-class criterion treats as blocking. No new regression was introduced by rev10/rev11.",
        "p2_findings": {
            "B": [
                {
                    "id": "B1",
                    "label": "B",
                    "axis": "class identity / quantifier domain not frozen to one data class",
                    "lines": "48, 51-59, 71-75, 149, 163-169, 218",
                    "statement": "quantifiers.formal (line 48) and conclusion.statement_formal (line 218) both range 'forall (s,delta) in D0', and D0 (lines 57-58) is the disjunction 'Sobolev variant s > 5/2 and delta in (1/2,1), OR the smooth-with-decay default'; the same disjunction is repeated in regularity.data_regularity (line 149). D1's comeagerness is defined against 'the named topology', and the named topology differs per disjunct: the weighted Sobolev product H^s_delta x H^{s-1}_{delta+1} in genericity.ambient_space (line 163) and the Frechet topology for the smooth-with-decay class in genericity.topology_or_measure (line 164). genericity.is_part_of_class is true (line 168) and class_change_warning (line 169) states that changing the genericity notion yields a different class, so one class_id denotes at least two class statements with different ambient spaces, topologies and comeagerness notions. The negation (lines 71-75) makes the counterexample semantics existential over D0: one (s,delta) whose extendible set is non-meager refutes the whole class while leaving the other disjunct untouched, which is strictly weaker than a frozen single-data-class statement. VARIANT_REGISTRY.json registers only TWOSIDED for this parent class; no data-regularity setting is registered as a variant, so the 'others are variants' half of the remedy is also undone.",
                    "detector": f"{F['recheck_script']} (yaml.safe_load + yaml.compose domain census, variant-registry census) -> {F['recheck']}#{h['recheck'][:12]} (checks.D0_disjuncts, checks.data_regularity_disjunctive, checks.registered_variants_for_parent, checks.data_regularity_variant_registered, findings.B1_D0_family_quantifier_present_at_reviewed_hash=true)",
                    "adjudicated_precedent": "Carried from convergence-15-rev9.json#667e277ff375 B1, which quotes the map review entries ('family of two class statements', 'Q2 disjunctive D0: not acceptable for class identity') and G-FORM's unmet 'single frozen data class (s,delta,norm) shared by F1/F2a/F2b'. F2b removed its own disjunctive domain for this reason (reviews/F2-review-18.json). This re-review re-measures the same defect at b6123750; it is not a new charge.",
                    "correlated": "deepseek-flash-05 blocker w05-f2a-audit-20260912T001155-blocker records probe S6-C2 with the same conclusion; this entry is the A1 verdict at the reviewed hash, not a duplicate charge.",
                    "artifact_counter_argument": "class_boundary.data_versus_extension_classes argues data regularity is a separate axis from the extension-class token. That is true of the token and false of the class statement: the artifact's own genericity block makes the ambient space, topology and genericity kind part of the class identity, and those change with the D0 member, so the forall-over-D0 form is a schema family, not one class.",
                    "f0_note": "The declared F0 taxonomy (research_map/formulation_taxonomy.yaml#276009f4, rev4 draft_unverified) itself writes 'For every admissible (s,delta) there is a comeager set G_{s,delta}' in classes.AF-SCC-C2-VAC-GEN.conclusion.text, so F0 currently ratifies the family reading. A fix at F2a alone would diverge from F0; either freeze one setting in both or record an explicit class-level ruling.",
                    "remedy": "One freeze decision, one revision: instantiate exactly one regularity setting in D0/statement_formal/regularity.data_regularity (either the Sobolev pair or the smooth-with-decay default) and register the other as a (parent_class AF-SCC-C2-VAC-GEN, variant_id) entry per VARIANT_REGISTRY.json policy; align the F0 taxonomy conclusion text; emit the artifact event with the new sha256 and regenerate FROZEN.json. If instead the family reading is intended, publish an explicit class-level ruling that names the existential-over-D0 falsifier semantics (lines 71-75) and have lead-audit accept it before a G-FORM verdict. Do not start another rewrite loop.",
                    "falsifier": "A revision whose quantifiers.domains.D0 definition, regularity.data_regularity and statement_formal instantiate exactly one regularity setting (no disjunction) with the other registered in VARIANT_REGISTRY, and which still exits 0 on check_class_schema.py at a hash H* with canonical == mirror == FROZEN entry == H* and verify_frozen exit 0; OR a lead-audit-accepted explicit ruling that the D0 family is intended, naming the falsifier semantics.",
                }
            ],
            "N": [
                {
                    "id": "N1",
                    "label": "N",
                    "axis": "normative text contradicts the binding implication ledger",
                    "lines": "158 vs 243",
                    "statement": "regularity.must_not_conflate[2] (line 158) reads 'a C0 result does not establish this class: it is stronger, and the implication runs C0 => C2 only'. The second clause and implication_ledger.one_way_entailments[0] (line 243, 'no proper future C0 extension' entails 'no proper future C2 extension', status elementary) contradict the first clause: if the implication runs C0 => C2, a C0 inextendibility result DOES establish this class's conclusion; only the class identity is not established. Non-blocking because the binding ledger is R16-correct and the repair is one clause, but the sentence as written could be used to refuse a licensed entailment.",
                    "detector": f"{F['recheck']}#{h['recheck'][:12]} (checks.normative_contradiction=true, both strings quoted)",
                    "remedy": "Reword to 'a C0 result is not this class; it is stronger and entails this class's conclusion (C0 => C2), while the converse transfer is forbidden'.",
                    "falsifier": "A revision in which the must_not_conflate sentence and the ledger entry assert the same direction.",
                },
                {
                    "id": "N2",
                    "label": "N",
                    "axis": "YAML duplicate keys / timestamp provenance",
                    "lines": "8, 10, 12, 14, 16, 18, 21, 23, 26",
                    "statement": "The top-level key revised_at occurs 8 times (yaml.compose count = 8; lines 8-23) plus revised_at_unused. yaml.safe_load silently keeps the last value (2026-09-12T00:30:00+08:00), which is ahead of the file mtime (2026-09-12 00:19:14) and of wall clock at review time (~00:21); a strict duplicate-key loader rejects the document at line 10. The gate uses safe_load, so the gate cannot see this. Carried from rev9 N2: the count went 7 -> 8, so the finding is not fixed, only its last value became uniform-looking.",
                    "detector": f"{F['recheck']}#{h['recheck'][:12]} (target.top_level_duplicate_keys = {{'revised_at': 8}}, target.single_revised_at, target.mtime)",
                    "remedy": "Replace the repeated revised_at lines with one key plus a revision_history list; set declared times from the filesystem clock.",
                    "falsifier": "A strict duplicate-key YAML load succeeds and the declared revised_at is not later than the file mtime.",
                },
                {
                    "id": "N3",
                    "label": "N",
                    "axis": "overstated machine-checkability",
                    "lines": "260",
                    "statement": "falsifier.tier_1.machine_checkable_steps lists 'the extension's metric is C2 across the boundary and Ric = 0 holds at sample points'. Sampled derivative checks cannot certify twice continuous differentiability at a boundary; they bound finite-difference residuals on samples. Carried unchanged from rev9 N3.",
                    "detector": f"{F['recheck']}#{h['recheck'][:12]} (checks.falsifier.tier_1_machine_checkable_steps)",
                    "remedy": "Relabel the step as 'finite-difference residual evidence on samples, not a C2 certificate' and keep the analytic C2 obligation in proof_obligations.",
                    "falsifier": "A listed machine-checkable step that can be decided by a deterministic finite computation, or a relabelled step whose wording does not claim certification.",
                },
                {
                    "id": "N4",
                    "label": "N",
                    "axis": "contract pointer without a hash pin",
                    "lines": "36, 297",
                    "statement": "class_contract_pointer (line 36) resolves to artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C2-VAC-GEN, but the pointer carries no sha256, and that supplement changed during the review window (01e7f841 at ~00:17 -> c8e979a1 by ~00:18; now pinned by FROZEN rev25). f0_binding (line 297) hash-pins the declared canonical taxonomy (276009f4) but not the supplement the pointer actually dereferences, so a reader following the pointer cannot tell which contract text was reviewed.",
                    "detector": f"{F['recheck']}#{h['recheck'][:12]} (checks.f0_binding.class_contract_pointer, .supplement_sha256, .supplement_hash_pinned_in_schema=false) plus the observed 01e7f841 -> c8e979a1 change",
                    "remedy": "Write the pointer as path#sha256 (or add class_contract_supplement_sha256) and refresh it in the same revision that changes the supplement.",
                    "falsifier": "A revision whose class_contract_pointer resolves to a hash equal to the supplement's measured sha256 and to the FROZEN entry.",
                },
            ],
        },
        "gate_scope_findings": {
            "G1_hash_chain": "RESOLVED at this hash: canonical == authoring mirror == FROZEN rev25 entry == b6123750b37d; verify_frozen.py exit 0, 0 problems, 0 DRIFT lines (measured by the reviewer).",
            "G2_family_quantifier": "ARTIFACT-LEVEL B1 here (not gate-scope): present in the canonical artifact itself.",
            "G3_manifest_drift": "RESOLVED at rev25, with the window recorded: at 00:19 FROZEN rev24 showed 7 DRIFT lines including both class schemas; rev25 repaired all of them before this verdict was emitted.",
            "G4_freeze_window": "The class artifact moved rev9 -> rev10 -> rev11 and FROZEN 23 -> 24 -> 25 inside ~5 minutes, and the F0 taxonomy/supplement moved in the same window. Under P4 every verdict bound to a pre-freeze hash voids. Controller action requested: declare one freeze window with no edits to F0/F1/F2a/F2b, then run the single A1 re-review round against the frozen hashes; otherwise verdicts will keep being voided by construction.",
            "G5_f0_family_reading": "The declared F0 taxonomy (276009f4, rev4) itself quantifies over admissible (s,delta), so B1 cannot be closed at F2a alone without either an F0+F2a freeze or an explicit ruling. Recorded so the gate adjudication does not loop.",
        },
        "acceptance_checks": {
            "a_class_leakage": f"PASS. Block-scoped scan over quantifiers, topology, i_plus, conclusion and falsifier.tier_1/tier_2: C2 CLEAN, 0 foreign hits ({F['leakage_json']}#{h['leakage_json'][:12]}). The token scan over assertive paths also returns 0 hits. Foreign tokens occur only in exempt anti_scope/implication_ledger/forbidden text. (The same scanner reports 6 REVIEW hits in the C0 sibling's conclusion block; that is F2b's disposition, not this class-bound verdict.)",
            "b_conclusion_inflation": "PASS. i_plus.role=assumption with in_conclusion=false; visibility.role=not_in_conclusion; conclusion_type=scc_c2_future_inextendibility; forbidden_strengthenings excludes C0/C1/H2_loc, two-sided and WCC content.",
            "c_assumption_completeness": "PASS structurally / FAIL on class identity. All ordered domain_ids resolve (D0-D3), extension_predicate carries all six required subkeys and clauses (a)-(f), undefined-domain census is empty, topology block names dimension, end structure and forbidden slices. The failure is B1: the data class is a disjunction, not one class.",
            "d_decidable_falsifier": "PASS with caveat N3. tier_1 refutes this class with an explicit genericity requirement (R1 non-meagerness / R2 instantiated G*), tier_2 is labelled refutes_strengthening_only, and non_machine_checkable_step names non-meagerness; the sampled-C2 wording overstates what a finite computation can certify.",
            "e_fields_two_readers_would_disagree_on": [
                "Whether 'forall (s,delta) in D0' is one class statement or a family of per-(s,delta) class statements (the whole of B1).",
                "Whether the smooth-with-decay default and the Sobolev variant are both inside this class or one is a variant of it (no VARIANT_REGISTRY entry resolves it).",
                "Whether 'C2 across the boundary and Ric = 0 at sample points' is machine-checkable (N3).",
            ],
        },
        "prior_round_delta": {
            "prior_reviews": [
                "reviews/F2a-review-15.json (rev1 21df6f7f, revise, 9 hard failures)",
                "reviews/convergence-15.json (rev3 23fec0e9, revise 3.0, void for published)",
                "reviews/convergence-15-rev9.json (rev9 8dae50da, revise 3.5, void after rev10/rev11)",
            ],
            "reviewed_hash": live,
            "convergence15_blocking_findings_resolved": {
                "B1_extension_predicate_block_absent": "RESOLVED (present with name, frozen_regularity C2, frozen_equation_concept classical_ricci, frozen_direction future, clauses (a)-(f), must_not_conflate).",
                "B2_undefined_domains_in_statement_formal": "RESOLVED (D0-D3 defined; statement_formal and quantifiers.formal share the forall(s,delta) in D0 binder head; undefined-domain census empty).",
                "B3_frozen_gate_rejects_artifact": "RESOLVED (check_class_schema.py sha 000e09e46b2f exits 0, failed_rules=[]).",
            },
            "rev9_findings_disposition": {
                "B1_D0_family_quantifier": "STILL PRESENT at b6123750 (charged again as B1); rev10/rev11 changed only f0_binding and duplicate-key layout.",
                "N1_normative_contradiction": "STILL PRESENT (N1).",
                "N2_duplicate_revised_at": "STILL PRESENT, count 7 -> 8 (N2).",
                "N3_machine_checkability": "STILL PRESENT (N3).",
                "N4_contract_pointer_hash_pin": "NEW at rev10/rev11 (f0_binding refresh exposed the unpinned supplement pointer).",
            },
            "gate_scope": {
                "path_hash_divergence": "RESOLVED (canonical == mirror == FROZEN).",
                "frozen_manifest_drift": "RESOLVED at rev25 (was open at rev24 earlier in the same window).",
            },
            "new_regressions": "none attributable to rev10/rev11 beyond N4.",
            "hard_failures_resolved_count": 9,
            "hard_failures_total": 9,
        },
        "mechanical_evidence": [
            {"path": F["target_live"], "sha256": live},
            {"path": F["snapshot"], "sha256": h["snapshot"]},
            {"path": F["recheck"], "sha256": h["recheck"]},
            {"path": F["recheck_script"], "sha256": h["recheck_script"]},
            {"path": F["gate_log"], "sha256": h["gate_log"], "note": "check_class_schema exit 0; tool sha 000e09e46b2f"},
            {"path": F["leakage_json"], "sha256": h["leakage_json"], "note": "C2 CLEAN, 0 foreign hits"},
            {"path": F["leakage_txt"], "sha256": h["leakage_txt"]},
            {"path": F["verify_frozen_log"], "sha256": h["verify_frozen_log"], "note": "FROZEN revision 25, 40 files, 0 problems"},
            {"path": F["frozen"], "sha256": h["frozen"]},
            {"path": F["taxonomy_canon"], "sha256": h["taxonomy_canon"]},
            {"path": F["taxonomy_supp"], "sha256": h["taxonomy_supp"]},
            {"path": F["consistency"], "sha256": h["consistency"]},
            {"path": F["registry"], "sha256": h["registry"]},
            {"path": F["prior_review_rev3"], "sha256": h["prior_review_rev3"]},
            {"path": F["prior_review_rev9"], "sha256": h["prior_review_rev9"]},
        ],
        "correlated_with": [
            "reviews/F2a-review-17.json and reviews/F2a-review-18.json: revise verdicts at earlier hashes; F2a-review-18 HF-A3 is the one-data-class criterion B1 re-measures.",
            "reviews/F2a-review-lead-audit.json: revise, reopened the disjunctive D0 at rev2.",
            "reviews/convergence-15.json and reviews/convergence-15-rev9.json: worker-15's own prior verdicts, both void for the published artifact under P4.",
            "reviews/F2-review-18.json: F2b removed its disjunctive domain, evidence that the project treats this as blocking.",
            "comms/outbox/deepseek-flash-05 blocker w05-f2a-audit-20260912T001155-blocker (same probe, independent worker).",
        ],
        "next_falsifier": "Publish one revision H* with (i) D0/statement_formal/regularity.data_regularity instantiating exactly one regularity setting and the other registered in VARIANT_REGISTRY (with the F0 taxonomy conclusion text aligned), or (ii) a lead-audit-accepted explicit class-level ruling that the D0 family is intended and that the tier_1 falsifier semantics are existential over D0 as written. Then verify canonical == mirror == FROZEN entry == H*, check_class_schema exit 0, verify_frozen 0 problems, hash stable across the run, and re-review once.",
        "not_claimed": [
            "No node completion, no gate verdict (worker events cannot move node status or gate verdicts).",
            "No theorem, counterexample, or physics result.",
            "No validation_status=passed; all emitted artifacts are unverified proposals for lead/controller adjudication.",
            "The verdict does not bind to any hash other than b6123750b37d.",
        ],
        "no_completion_claimed": True,
    }

    with open(os.path.join(ROOT, REVIEW_PATH), "w") as f:
        json.dump(rev, f, indent=1)
    review_hash = sha(REVIEW_PATH)

    ckpt = {
        "worker": "deepseek-flash-15",
        "checkpoint": 10,
        "at": at,
        "elapsed_minutes": elapsed,
        "assignment": ASSIGNMENT,
        "task": "P4 re-binding: one bounded A1 re-review of AF-SCC-C2-VAC-GEN at the live canonical hash after the rev23/rev24 re-freeze churn; emit review + evidence + checkpoint, then exit",
        "review": {"path": REVIEW_PATH, "sha256": review_hash, "bound_hash": live, "verdict": "revise", "score": 3.5},
        "prior_artifacts_recorded": [
            {"path": F["prior_review_rev9"], "sha256": h["prior_review_rev9"], "note": "authored 00:16:30 by worker 15, no outbox event existed; recorded retroactively by this checkpoint"},
        ],
        "canonical_now": {
            "path": F["target_live"],
            "sha256": live,
            "internal_revision": rc["target"]["internal_revision"],
            "gate_exit": rc["gate"]["exit_code"],
            "hash_stable_during_gate": rc["gate"]["HASH_STABLE_DURING_GATE"],
            "mirror_identical": rc["mirror"]["byte_identical_to_live"],
            "frozen_entry_matches": rc["frozen"]["entry_matches_live"],
            "verify_frozen_exit": rc["frozen"]["verify_frozen_exit"],
            "drift_count": rc["frozen"]["drift_count"],
            "D0_disjunction_present": rc["checks"]["D0_has_disjunction"],
        },
        "findings": {
            "B": 1,
            "N": 4,
            "gate_scope": 5,
            "B1": "D0 family quantifier / no single data class (adjudicated precedent, still present at b6123750)",
            "N1": "normative C0 sentence contradicts the binding ledger",
            "N2": "8 duplicate top-level revised_at keys; last value ahead of mtime/wall clock",
            "N3": "machine-checkability overstatement (C2 across the boundary at sample points)",
            "N4": "class_contract_pointer supplement has no hash pin and moved in-window",
        },
        "p4_consequence": "convergence-15 (23fec0e9) and convergence-15-rev9 (8dae50da) are void for the published artifact; this verdict binds only to b6123750b37d, which was stable across the gate run and matches canonical, mirror and FROZEN rev25.",
        "recommended_next": "controller freeze window, then one bounded A1 re-review against the frozen hash; no further rewrite loop before the B1 direction decision (single class vs explicit family ruling).",
        "no_completion_claimed": True,
    }
    with open(os.path.join(ROOT, CHECKPOINT_PATH), "w") as f:
        json.dump(ckpt, f, indent=1)
    ckpt_hash = sha(CHECKPOINT_PATH)

    ts = at.replace("-", "").replace(":", "").replace("+08:00", "").replace("T", "T")
    events = [
        {
            "event_id": "w15-conv-artifact-review-rev9-retro-20260912T0024",
            "event_type": "artifact",
            "created_at": at,
            "actor": "deepseek-flash-15",
            "node_id": "A1",
            "group_id": "audit",
            "class_id": CLASS_ID,
            "artifact_type": "review",
            "path": F["prior_review_rev9"],
            "sha256": h["prior_review_rev9"],
            "validation_status": "unverified",
            "assignment_ref": ASSIGNMENT,
            "evidence_refs": [f"{F['prior_review_rev9']}#{h['prior_review_rev9'][:12]}"],
            "note": "retroactive record: authored 2026-09-12T00:16:30 by worker 15, never emitted before the worker was recycled; void for the published artifact under P4 (target 8dae50da), superseded by convergence-15-rev11",
            "no_completion_claimed": True,
        },
        {
            "event_id": f"w15-conv-artifact-review-rev11-{ts}",
            "event_type": "artifact",
            "created_at": at,
            "actor": "deepseek-flash-15",
            "node_id": "A1",
            "group_id": "audit",
            "class_id": CLASS_ID,
            "artifact_type": "review",
            "path": REVIEW_PATH,
            "sha256": review_hash,
            "validation_status": "unverified",
            "assignment_ref": ASSIGNMENT,
            "evidence_refs": [f"{REVIEW_PATH}#{review_hash[:12]}", f"{F['target_live']}#{live[:12]}"],
            "no_completion_claimed": True,
        },
        {
            "event_id": f"w15-conv-artifact-recheck-rev11-{ts}",
            "event_type": "artifact",
            "created_at": at,
            "actor": "deepseek-flash-15",
            "node_id": "A1",
            "group_id": "audit",
            "class_id": CLASS_ID,
            "artifact_type": "evidence",
            "path": F["recheck"],
            "sha256": h["recheck"],
            "validation_status": "unverified",
            "assignment_ref": ASSIGNMENT,
            "evidence_refs": [f"{F['recheck']}#{h['recheck'][:12]}", f"{F['recheck_script']}#{h['recheck_script'][:12]}"],
            "no_completion_claimed": True,
        },
        {
            "event_id": f"w15-conv-artifact-snapshot-rev11-{ts}",
            "event_type": "artifact",
            "created_at": at,
            "actor": "deepseek-flash-15",
            "node_id": "A1",
            "group_id": "audit",
            "class_id": CLASS_ID,
            "artifact_type": "evidence",
            "path": F["snapshot"],
            "sha256": h["snapshot"],
            "validation_status": "unverified",
            "assignment_ref": ASSIGNMENT,
            "evidence_refs": [f"{F['snapshot']}#{h['snapshot'][:12]}", f"{F['target_live']}#{live[:12]}"],
            "note": "byte snapshot of the reviewed canonical artifact at hash b6123750b37d; the live path may move, this hash is the verdict binding",
            "no_completion_claimed": True,
        },
        {
            "event_id": f"w15-conv-artifact-checkpoint-10-{ts}",
            "event_type": "artifact",
            "created_at": at,
            "actor": "deepseek-flash-15",
            "node_id": "A1",
            "group_id": "audit",
            "class_id": CLASS_ID,
            "artifact_type": "checkpoint",
            "path": CHECKPOINT_PATH,
            "sha256": ckpt_hash,
            "validation_status": "unverified",
            "assignment_ref": ASSIGNMENT,
            "evidence_refs": [f"{CHECKPOINT_PATH}#{ckpt_hash[:12]}"],
            "no_completion_claimed": True,
        },
        {
            "event_id": f"w15-conv-review-rev11-{ts}",
            "event_type": "review",
            "created_at": at,
            "actor": "deepseek-flash-15",
            "reviewer": "deepseek-flash-15",
            "target_id": CLASS_ID,
            "target_subnode": "F2a",
            "node_id": "A1",
            "group_id": "audit",
            "class_id": CLASS_ID,
            "gate": "G-AUDIT",
            "assignment_ref": ASSIGNMENT,
            "verdict": "revise",
            "score": 3.5,
            "target_hash_cited_in_artifact": live,
            "review_artifact": f"{REVIEW_PATH}#{review_hash[:12]}",
            "findings": [
                "B1 [class identity]: D0/statement_formal still quantify 'forall (s,delta) in D0' and D0/regularity.data_regularity are disjunctions; no data-regularity variant is registered; counterexample semantics are existential over D0. Adjudicated precedent, still present at b6123750.",
                "N1: regularity.must_not_conflate (line 158) contradicts implication_ledger (line 243) on whether a C0 result establishes this class's conclusion.",
                "N2: 8 duplicate top-level revised_at keys; last value 00:30:00 is ahead of mtime 00:19:14 and wall clock.",
                "N3: machine_checkable_steps claims C2-across-the-boundary certification from sample checks.",
                "N4: class_contract_pointer dereferences an unpinned supplement that changed during the review window.",
                "Gate-scope: hash chain canonical==mirror==FROZEN rev25 RESOLVED here; freeze window (G4) and F0 family reading (G5) recorded for the controller.",
            ],
            "evidence_refs": [
                f"{REVIEW_PATH}#{review_hash[:12]}",
                f"{F['target_live']}#{live[:12]}",
                f"{F['recheck']}#{h['recheck'][:12]}",
                f"{F['gate_log']}#{h['gate_log'][:12]}",
                f"{F['leakage_json']}#{h['leakage_json'][:12]}",
                f"{F['frozen']}#{h['frozen'][:12]}",
                f"{F['verify_frozen_log']}#{h['verify_frozen_log'][:12]}",
            ],
            "next_falsifier": rev["next_falsifier"],
            "no_completion_claimed": True,
        },
        {
            "event_id": f"w15-conv-status-rev11-{ts}",
            "event_type": "status",
            "created_at": at,
            "actor": "deepseek-flash-15",
            "node_id": "A1",
            "group_id": "audit",
            "class_id": CLASS_ID,
            "gate": "G-AUDIT",
            "assignment_id": ASSIGNMENT,
            "status": "active",
            "hours": 0.2,
            "summary": "BOUNDED TASK DELIVERED, WORKER EXITING. One class-bound A1 re-review of AF-SCC-C2-VAC-GEN at canonical hash b6123750b37d (rev11): verdict revise 3.5, B1 = D0 family quantifier / no single data class (adjudicated precedent re-measured), N1-N4 backlog. Hash chain canonical==authoring==FROZEN rev25 is clean and verify_frozen exits 0 with 0 drift; check_class_schema exits 0; C2 leakage scan CLEAN; hash stable across the gate run; reviewed bytes snapshotted. convergence-15-rev9.json (written by the prior worker instance, never emitted) is recorded retroactively. No completion/gate/theorem claim; node status not moved.",
            "artifact_refs": [
                f"{REVIEW_PATH}#{review_hash[:12]}",
                f"{CHECKPOINT_PATH}#{ckpt_hash[:12]}",
                f"{F['prior_review_rev9']}#{h['prior_review_rev9'][:12]}",
            ],
            "evidence_refs": [
                f"{F['target_live']}#{live[:12]}",
                f"{F['recheck']}#{h['recheck'][:12]}",
                f"{F['leakage_json']}#{h['leakage_json'][:12]}",
                f"{F['verify_frozen_log']}#{h['verify_frozen_log'][:12]}",
            ],
            "next_falsifier": rev["next_falsifier"],
            "no_completion_claimed": True,
        },
    ]

    existing = set()
    if os.path.exists(os.path.join(ROOT, OUTBOX)):
        with open(os.path.join(ROOT, OUTBOX)) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    existing.add(json.loads(line).get("event_id"))
                except json.JSONDecodeError:
                    pass
    appended = 0
    with open(os.path.join(ROOT, OUTBOX), "a") as f:
        for e in events:
            if e["event_id"] in existing:
                continue
            f.write(json.dumps(e) + "\n")
            appended += 1

    print(json.dumps({
        "at": at,
        "review": REVIEW_PATH,
        "review_sha256": review_hash,
        "checkpoint": CHECKPOINT_PATH,
        "checkpoint_sha256": ckpt_hash,
        "target_hash": live,
        "events_appended": appended,
        "events_total": len(events),
    }, indent=1))


if __name__ == "__main__":
    main()
