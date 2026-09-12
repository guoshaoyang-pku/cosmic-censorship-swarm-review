#!/usr/bin/env python3
"""Emit worker-046's v2 F2a review deliverables.

Writes, in order:
  1. reviews/F2a-review-rev27-a.json          (verdict v2, supersedes v1 blocker)
  2. comms/outbox/worker-046.jsonl            (ONE appended `review` event)
  3. runtime/state/worker-046_F2a_checkpoint.json (canonical checkpoint, v1 inlined)

Reproducible: all measured hashes are recorded in the verdict; the pinned byte-state
lives under artifacts/worker-046/f2a_rev27_verdict/pinned/.
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")


def sha(path):
    h = hashlib.sha256()
    with open(os.path.join(ROOT, path), "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


H = {
    "c2_pin": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "c0_pin": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "wcc_pin": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "regularities_pin": "94562101a81645349e1ff17b9184dd956887d8fc6b54a3d7ed7cd786ed8b4ce4",
    "regularities_live_now": "27255e5b34f36b252accf1217dc01b63a5f5ec09f33af03938565c8fb99b20ed",
    "frozen_rev27": "5fa3b3bf95f2dcb003ccf800db2f03b80c385a9de3f2984d848201ebec5db340",
    "frozen_rev28": "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
    "frozen_rev29": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "live_c2": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "live_c0": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "declared_f0": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "supplement": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "evidence_declared": "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48",
    "evidence_current": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "checker": "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "rule_spec": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "manifest_rev27": "fce91948ba3a59a5bd34c8bcb03202ee479a95dbc3e4d6c327a0c4d1a9170d33",
    "manifest_current": "014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a",
    "gate_run_rev27manifest": "a4c1c768db770ecd5cfa18a10c70e3cb39462742bb885260cad5115f409b08d3",
    "gate_run_currentmanifest": "a024bbd0af463d70d5b84f565e62b8f051827b0d6d55f215579417791e52f447",
    "d0_check": "4be4486b15a98fb950f084d9dc41af224756cb61b94a5cf2485760ee8e5ecb41",
    "v1_verdict": "cab2fbe2e614c1ba8c55ef4c4d14b4ced1d355437288237d177c88d16c295bae",
    "v1_checkpoint": "a8fba45a858b0d897fd3d465655d87a703830ffc783af65ddde800c427a05424",
    "assigned_pin": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
}

# ---- re-measure the two files this verdict's hash claims rest on -------------
assert sha("schemas/af_scc_c2_vacuum.yaml") == H["live_c2"], "live C2 moved during review"
assert sha("artifacts/formulation/evidence/taxonomy_consistency.json") == H["evidence_current"]
assert sha("artifacts/worker-046/f2a_rev27_verdict/pinned/af_scc_c2_vacuum.5476a3f2c6bc.yaml") == H["c2_pin"]
assert sha("artifacts/worker-046/f2a_rev27_verdict/pinned/af_scc_c0_vacuum.55d0a1ea9bda.yaml") == H["c0_pin"]
assert sha("artifacts/worker-046/f2a_rev27_verdict/pinned/af_scc_regularities.94562101a816.yaml") == H["regularities_pin"]
assert sha("artifacts/worker-046/f2a_rev27_verdict/v1_blocker/F2a-review-rev27-a.v1.json") == H["v1_verdict"]

C2 = "artifacts/worker-046/f2a_rev27_verdict/pinned/af_scc_c2_vacuum.5476a3f2c6bc.yaml"
C0 = "artifacts/worker-046/f2a_rev27_verdict/pinned/af_scc_c0_vacuum.55d0a1ea9bda.yaml"
AGG = "artifacts/worker-046/f2a_rev27_verdict/pinned/af_scc_regularities.94562101a816.yaml"
D0J = "artifacts/worker-046/f2a_rev27_verdict/gate_runs/d0_instantiation_check.json"
G27 = "artifacts/worker-046/f2a_rev27_verdict/gate_runs/gate_c2_rev27manifest.json"
GCU = "artifacts/worker-046/f2a_rev27_verdict/gate_runs/gate_c2_currentmanifest.json"

hard_failures = [
    {
        "id": "HF-046-F2a-01",
        "kind": "hash_bound",
        "status": "mismatch_at_current_bytes",
        "declared_field": "f0_binding.consistency_evidence_sha256",
        "declared_sha256": H["evidence_declared"],
        "referenced_path": "artifacts/formulation/evidence/taxonomy_consistency.json",
        "measured_sha256_now": H["evidence_current"],
        "measured_bytes_now": 495,
        "declared_bytes_at_freeze": 728,
        "freeze_window_resolution": (
            "RESOLVED at the pin's own freeze: FROZEN rev27 (frozen_at 2026-09-12T00:32:59+08:00, "
            f"{H['frozen_rev27'][:12]}) declares artifacts/formulation/evidence/taxonomy_consistency.json = "
            f"{H['evidence_declared'][:12]} / 728 B, exactly the schema's declared value; FROZEN rev28 "
            f"(00:35:08, {H['frozen_rev28'][:12]}) regenerated it to {H['evidence_current'][:12]} / 495 B "
            "without a schema refresh. The 728 B bytes are preserved at "
            "artifacts/worker-046/f2a_rev27_verdict/evidence/taxonomy_consistency.675a99d0d25b.json "
            "(also artifacts/worker-022/evbind_guard/pinned/taxonomy_consistency.675a99d0d25b.json)."
        ),
        "semantic_mitigation": (
            "The replacement file is semantically identical on the check that matters: consistent=true, "
            "errors=[], contract_divergences=[], notes=[], the same 4 classes_compared, the same taxonomy "
            f"({H['declared_f0'][:12]}) and supplement ({H['supplement'][:12]}) hashes. The 728 B version "
            "additionally carried map_taxonomy_sha256 / lead_contract_sha256 / measured_at; rev28 stripped "
            "those fields. So this is a stale-binding failure, not a false consistency claim."
        ),
        "spec_basis": "assignment audit-r2-F2a-bindchain-worker-046: 'Report a mismatch as a hash-bound hard failure' (measured against the referenced file on disk now).",
        "gate_effect": "Blocks use of the rev12 pin as a live binding. Already repaired at rev13: the live schema e9a27996 declares 9e335e9b, which resolves.",
    },
    {
        "id": "HF-046-F2a-02",
        "kind": "gate_toolchain_skew",
        "status": "fail_under_frozen_toolchain__pass_under_current",
        "measurement": (
            "Frozen binding structural gate on the pinned C2 bytes: check_class_schema.py 000e09e4 + "
            f"rule_spec.json {H['rule_spec'][:12]} + KEY_MANIFEST {H['manifest_rev27'][:12]} (the exact "
            "FROZEN rev27 triple) -> verdict=fail, failed_rules=['R22'], unknown keys "
            "['at','class_contract_supplement_pointer','consistency_evidence_sha256','index','notes','revision_history']. "
            f"With the current manifest {H['manifest_current'][:12]} (271 allowed keys) the same bytes -> "
            "verdict=pass, failed_rules=[]. The pinned C0 sibling fails identically under the frozen manifest."
        ),
        "interpretation": (
            "The rev12 repair added revision_history and the split pointer/evidence keys before the "
            "allowlist caught up; the artifact is not structurally defective, but at the declared rev27 "
            "toolchain the binding gate cannot return pass. Gate accounting is manifest-dependent."
        ),
        "gate_effect": "F2a rev12 is not gate-passable at its own declared toolchain; dissolves after the manifest bump.",
    },
]

findings = [
    {
        "id": "F-046-F2a-01",
        "severity": "major",
        "claim": (
            "Cross-schema containment conflict, carried in a non-assertive ledger block. The pinned C2 "
            "asserts E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0 (C2 lines 147, 236, and it is "
            "re-used in the ledger at 240) while the pinned C0 sibling explicitly declines the same "
            "containment: C0 line 151 says 'No containment with C2 or C0 is asserted here' and C0 line 99 "
            "says H2_loc 'is not C0'. The warrant C0 line 240 gives ('an H2_loc extension is a continuous "
            "metric extension') is not elementary in 4D: H^2_loc is the borderline Sobolev exponent "
            "s = n/2 = 2, and H^2_loc is not contained in C^0 (the embedding into L^infinity fails at the "
            "borderline). Either the H2_loc variant must be redefined with a continuity representative "
            "(e.g. H^2_loc cap C^0) or the E_H2loc subset E_C0 link must be dropped from the chain."
        ),
        "what_survives": "C2's own H2loc => C2 entailment (C2 line 240) needs only E_C2 subset E_H2loc (a C2 metric has locally bounded Riemann curvature), which is valid; the broken link is H2loc subset C0.",
        "evidence": [f"{C2}:147", f"{C2}:236", f"{C2}:240", f"{C0}:99", f"{C0}:151", f"{C0}:238", f"{C0}:240", f"{C0}:249"],
        "gate_blind_spot": "check_class_schema.py's own docstring: the lexical leakage scan covers ASSERTIVE_PATHS only, so a semantic leak in implication_ledger passes the structural gate (it does pass, under the current manifest).",
        "repair": "Drop or qualify the H2loc subset C0 link in both components and re-run the separation lint; if continuity is intended, redefine the H2LOC variant in VARIANT_REGISTRY.json as H^2_loc cap C^0.",
    },
    {
        "id": "F-046-F2a-02",
        "severity": "moderate",
        "claim": (
            "The tier-1 falsifier is not bound to a regularity index. falsifier.tier_1.witness_type and "
            "proof_obligations say 'an open (or at least non-meager) set of one-ended AF vacuum data' but "
            "D0 is a tagged disjoint union of different topological spaces (r = smooth; r = (sobolev,s,delta)), "
            "and 'open' / 'non-meager' are r-relative. The class negation requires 'there exists r in D0' "
            "with a non-meager extendible set in X^r (C2 lines 66-69), so a tier-1 refutation must name its r."
        ),
        "evidence": [f"{C2}:251", f"{C2}:252", f"{C2}:253", f"{C2}:66", f"{C2}:52"],
        "repair": "State tier_1.witness_type as 'for some r in D0, an open (or non-meager) subset of X^r_vac(AF) ...' and bind route R1 the same way.",
    },
    {
        "id": "F-046-F2a-03",
        "severity": "minor",
        "claim": (
            "Assumption incompleteness: regularity.i_plus_regularity asserts gtilde extends to I+ with "
            "C^k regularity, k >= 3, and says 'k is part of the assumption', but k is introduced by no "
            "binder and has no declared range beyond the inequality, so instantiating the class does not "
            "fix k."
        ),
        "evidence": [f"{C2}:145"],
        "repair": "Declare k as a fixed parameter of the data class (e.g. 'for a fixed k >= 3 chosen with the data') or add it to D0/D2.",
    },
    {
        "id": "F-046-F2a-04",
        "severity": "minor",
        "claim": (
            "Instantiation justification is stated only for one D0 disjunct: genericity.ambient_space "
            "justifies Baireness by 'X_vac is a closed subset of a Banach space, hence Baire', which "
            "covers the Sobolev disjunct but not the smooth disjunct, whose ambient space the same field "
            "calls Frechet. Frechet (complete metrizable) spaces are Baire, so the conclusion holds, but "
            "the stated reason does not cover both branches of the repaired D0."
        ),
        "evidence": [f"{C2}:157", f"{C2}:159", f"{C2}:52"],
        "repair": "Split the Baire justification per disjunct (Banach for the Sobolev branch; complete metrizable/Frechet for the smooth branch).",
    },
    {
        "id": "F-046-F2a-05",
        "severity": "minor",
        "claim": (
            "Notation overload: class_boundary.one_way_implication writes 'E(C0) entails E(C2)' for the "
            "conclusions, while extension_predicate and implication_ledger use E_C0 / E_C2 for extension "
            "SETS (E_C2 subset E_C0). Two careful readers can disagree about what E(.) denotes."
        ),
        "evidence": [f"{C2}:77", f"{C2}:147", f"{C2}:236"],
        "repair": "Use distinct symbols for conclusions (e.g. Inext_C0) and extension sets (E_C0).",
    },
    {
        "id": "F-046-F2a-06",
        "severity": "major_context_outside_assigned_file",
        "claim": (
            "The machine-checkable separation instrument was stale at the pin window. af_scc_regularities.yaml "
            f"at its pin-window bytes ({H['regularities_pin'][:12]}) pins component hashes C2 b6123750 (rev11) "
            "and C0 1bb78ce9 (rev11), while the reviewed rev12 components are 5476a3f2 / 55d0a1ea. Its own "
            "SEP-6 says a component change invalidates the aggregator until re-pinned, and review_notes line 86 "
            "sets the same rule after 00:15. So the F2a/F2b separation lint could not pass on the component "
            "revisions that were actually under review."
        ),
        "evidence": [f"{AGG}:33", f"{AGG}:41", f"{AGG}:58", f"{AGG}:86", f"{C2}#{H['c2_pin'][:12]}", f"{C0}#{H['c0_pin'][:12]}"],
        "live_note": f"Outside my pinned review: the live aggregator was rewritten at 2026-09-12T01:11:13+08:00 to {H['regularities_live_now'][:12]}; I did not review those bytes.",
        "repair": "Re-pin the aggregator to the component revisions under review (or explicitly record the aggregator as void for that window).",
    },
]

checks = {
    "c2_c0_collapse": {
        "result": "PASS (distinct conclusion objects with a decisive axis)",
        "conclusion_types": {
            "C2": "scc_c2_future_inextendibility",
            "C0": "scc_c0_future_inextendibility",
            "vocab_frozen_in_rule_spec": True,
        },
        "decisive_axes": [
            "regularity selector: class_components.regularity_token C2 vs C0",
            "extension_predicate.frozen_regularity: C2 vs C0",
            "extension solution concept: classical_ricci vs none",
            "conclusion predicate: proper future C2 vacuum extension vs continuous (C0) metric extension",
        ],
        "separation_guards_present": [
            "class_boundary.merge_forbidden true; one_class_only AF-SCC-C2-VAC-GEN",
            "anti_scope.phrases_that_are_not_this_class forbids any 'C0 or C2' composite",
            "sibling_disjoint_from is reciprocal in both components",
        ],
        "evidence": [f"{C2}:208", f"{C2}:146", f"{C2}:88", f"{C2}:31", f"{C0}:210", f"artifacts/formulation/rule_spec.json#{H['rule_spec'][:12]}"],
        "caveat": "The conclusion objects are distinct and their regularity signatures differ, so no C0/C2 conclusion merge occurs; the containment-ledger conflict is recorded separately as F-046-F2a-01.",
    },
    "d0_binder_instantiation": {
        "result": "PASS (rev12 F-2 well-typedness repair effective at the pinned bytes)",
        "method": "artifacts/worker-046/f2a_rev27_verdict/d0_instantiation_check.py (mechanical): both branches declared; s > 5/2 and delta in (1/2,1) present; every occurrence of the index r is the binder 'forall r in D0' or the argument of X^r_vac(AF); no destructuring or pair-typing of the smooth branch; both substitutions well-typed; definition_ref regularity.data_regularity resolves.",
        "substitutions": {
            "smooth": "exists G_smooth subset X^smooth_vac(AF) with G_smooth comeager  [Frechet constraint manifold]",
            "(sobolev,s,delta)": "exists G_(sobolev,s,delta) subset X^(sobolev,s,delta)_vac(AF) with G_(sobolev,s,delta) comeager  [H^s_delta x H^{s-1}_{delta+1}]",
        },
        "evidence": [f"{D0J}#{H['d0_check'][:12]}", f"{C2}:42", f"{C2}:46", f"{C2}:52", f"{C2}:55", f"{C2}:66", f"{C2}:157", f"{C2}:212"],
        "residual": "Baire justification covers only the Banach branch (see F-046-F2a-04).",
    },
    "class_leakage": {
        "assertive_blocks": "PASS: conclusion, quantifiers, topology, genericity and extension_predicate contain no C0, C1, H2_loc or WCC content; WCC/I+ visibility are explicitly not_in_conclusion; no foreign-family conclusion appears.",
        "non_assertive_blocks": "FAIL: implication_ledger imports the C0-side containment E_H2loc subset E_C0 that the C0 sibling declines (F-046-F2a-01). This is exactly the structural gate's declared blind spot (leakage scan covers ASSERTIVE_PATHS only).",
        "evidence": [f"{C2}:153", f"{C2}:192", f"{C2}:195", f"{C2}:198", f"{C2}:204", f"{C2}:236"],
    },
    "conclusion_inflation": {
        "result": "PASS (no theorem/counterexample promotion)",
        "evidence": [f"{C2}:32", f"{C2}:33", f"{C2}:84", f"{C2}:209", f"{C2}:233", f"{C2}:281", f"{C2}:284", f"{C2}:312"],
        "notes": "epistemic_status=open_problem in class and conclusion; promotion_rule requires a checked proof with artifact_refs; known_status records no peer-reviewed theorem (T-401) and marks T-402 as the authors' interpretation; review_status.verdict=pending; the Kerr obstruction is labelled citation_status unresolved rather than promoted to a theorem.",
    },
    "assumption_completeness": {
        "result": "PASS with minors",
        "declared_unresolved_items_present": True,
        "items": ["diffeo-quotient construction", "meagerness of excluded families", "non-vacuity witness membership in G", "regularity of vacuum extensions across a Cauchy horizon"],
        "minors": ["F-046-F2a-03 (unbound i+ exponent k)", "F-046-F2a-04 (Baire reason covers one disjunct)"],
        "evidence": [f"{C2}:138", f"{C2}:140", f"{C2}:160", f"{C2}:185", f"{C2}:304"],
    },
    "decidable_falsifier": {
        "result": "PASS with the binding caveat F-046-F2a-02",
        "evidence": [f"{C2}:248", f"{C2}:252", f"{C2}:253", f"{C2}:254", f"{C2}:255"],
        "notes": "Tier-1 has machine-checkable steps and names its non-machine-checkable step (non-meagerness); the instantiated route R2 is the decidable one. The r-binding gap is F-046-F2a-02.",
    },
}

verdict_doc = {
    "review_id": "F2a-review-rev27-a",
    "verdict_version": "2.0",
    "review_type": "independent_blind_gform_review",
    "document_type": "class_content_verdict_at_recovered_pin",
    "created_at": NOW,
    "reviewer": "worker-046",
    "reviewer_role": "execution_worker_deepseek_flash",
    "target_id": "F2a",
    "node_id": "F2a",
    "class_id": "AF-SCC-C2-VAC-GEN",
    "gate": "G-FORM",
    "artifact": "schemas/af_scc_c2_vacuum.yaml",
    "assignments": [
        {
            "event_id": "audit-r2-F2a-a",
            "actor": "astra-lead-audit",
            "created_at": "2026-09-12T00:44:18+08:00",
            "gate": "G-FORM",
            "class_id": "AF-SCC-C2-VAC-GEN",
            "assigned_artifact": "reviews/F2a-review-rev27-a.json",
            "assigned_pin_sha256": H["assigned_pin"],
            "status": "closed_substantively_at_recovered_pin",
        },
        {
            "event_id": "audit-r2-F2a-bindchain-worker-046",
            "actor": "astra-lead-audit",
            "created_at": "2026-09-12T00:47:58+08:00",
            "gate": "G-FORM",
            "class_id": "AF-SCC-C2-VAC-GEN",
            "assigned_artifact": "reviews/F2a-review-rev27-b.json",
            "status": "folded_into_this_file_per_stop_rule",
            "collision_note": "reviews/F2a-review-rev27-b.json exists on disk and is authored by worker-091; worker-046 did not write or overwrite it.",
        },
    ],
    "supersedes": {
        "review_id": "F2a-review-rev27-a",
        "version": "1.0",
        "document_type": "blocker_moving_target",
        "sha256": H["v1_verdict"],
        "preserved_at": "artifacts/worker-046/f2a_rev27_verdict/v1_blocker/F2a-review-rev27-a.v1.json",
        "outbox_event_id": "w046-f2a-rev27-moving-target-blocker-01",
        "checkpoint_v1_sha256": H["v1_checkpoint"],
        "reason": (
            "v1 correctly failed closed because the named live path schemas/af_scc_c2_vacuum.yaml no longer "
            "held the assigned pin. v2 keeps that blocker on the record, then performs the substantive class "
            "checks on the exact assigned byte-state, recovered from immutable snapshot copies whose sha256 "
            "equals the assigned pin. v2 does NOT render a gate verdict for the live rev13 pin."
        ),
    },
    "assigned_pin_sha256": H["assigned_pin"],
    "reviewed_sha256": H["c2_pin"],
    "reviewed_revision": 12,
    "reviewed_bytes": 29976,
    "reviewed_byte_state_provenance": {
        "snapshot_primary": f"artifacts/worker-046/f2a_rev27_verdict/pinned/af_scc_c2_vacuum.5476a3f2c6bc.yaml#{H['c2_pin'][:12]}",
        "snapshot_source": "artifacts/worker-043/f2a_rev12_verdict/snapshot/schemas__af_scc_c2_vacuum.yaml (00:32, rev12 window)",
        "corroborating_copies_all_measuring_the_pin": [
            "artifacts/worker-048/f2a_rev27_repin_audit/snapshot/af_scc_c2_vacuum.5476a3f2c6bc.yaml",
            "artifacts/worker-035/f2a_rev12_verdict/snapshot/schemas__af_scc_c2_vacuum.yaml",
            "artifacts/worker-034/f2a_verify/snapshot_af_scc_c2_vacuum.rev12.yaml",
            "artifacts/worker-047/d0_repair_accept/snapshot_rev12/af_scc_c2_vacuum.yaml.5476a3f2c6bc",
            "artifacts/worker-038/f0_conformance/snapshots/rev28/schemas__af_scc_c2_vacuum.yaml",
            "artifacts/worker-061/f2a_rev12_bind/pinned/af_scc_c2_vacuum.yaml",
            "artifacts/worker-086/gform_rev12/pinned/af_scc_c2_vacuum.5476a3f2c6bc.yaml",
            "artifacts/worker-088/f2a_review/pinned/af_scc_c2_vacuum.5476a3f2.yaml",
            "artifacts/worker-089/f2a_rev12_review/pinned/af_scc_c2_vacuum.5476a3f2c6bc.yaml",
            "artifacts/worker-094/closefind_verify/pinned/schemas__af_scc_c2_vacuum.yaml",
        ],
        "sibling_pins_used_for_the_collapse_check": {
            "c0": f"artifacts/worker-046/f2a_rev27_verdict/pinned/af_scc_c0_vacuum.55d0a1ea9bda.yaml#{H['c0_pin'][:12]}",
            "wcc": f"artifacts/worker-046/f2a_rev27_verdict/pinned/af_wcc_vacuum.cce9c60146d6.yaml#{H['wcc_pin'][:12]}",
            "regularities_index": f"artifacts/worker-046/f2a_rev27_verdict/pinned/af_scc_regularities.94562101a816.yaml#{H['regularities_pin'][:12]}",
        },
        "pin_measured_before_read": True,
        "pin_measured_after_read": True,
        "artifact_edited_by_reviewer": False,
    },
    "live_path_check": {
        "path": "schemas/af_scc_c2_vacuum.yaml",
        "expected_sha256": H["assigned_pin"],
        "live_sha256": H["live_c2"],
        "live_bytes": 30594,
        "live_revision": 13,
        "live_revised_at": "2026-09-12T00:53:20+08:00",
        "match": False,
        "moving_target_at_named_path": True,
        "frozen_rev29_mirrors_live": True,
        "resolution": "The assigned byte-state no longer exists at the named path but is preserved byte-identically in the snapshots above; this review is bound to the assigned pin, not to the live bytes.",
    },
    "verdict": "revise",
    "score": 2.5,
    "score_rationale": (
        "Substantive structure is sound (no C0/C2 collapse, no conclusion inflation, the rev12 D0 repair is "
        "effective and machine-verified), so this is not a reject. It is not an accept: one hash-bound "
        "f0_binding failure at current bytes (HF-046-F2a-01), one cross-schema containment conflict that the "
        "structural gate cannot see (F-046-F2a-01), one falsifier-binding gap, three minors, and a "
        "manifest-dependent gate failure at the declared rev27 toolchain (HF-046-F2a-02)."
    ),
    "counts_as_gate_verdict": False,
    "gate_relevance": (
        "none for the live G-FORM pin. Reviewed revision 12 is superseded (CF-20: rev12 pins and verdicts "
        "are void); the live rev13 pin is e9a27996 and already carries its own F2a coverage. This document is "
        "class-content evidence for F2a and for the F2a/F2b separation question; it cannot move G-FORM."
    ),
    "no_gate_verdict_set": True,
    "hard_failures": hard_failures,
    "findings": findings,
    "checks": checks,
    "falsifier": (
        "This review is falsified by any of: (i) a byte-state at every listed snapshot copy whose sha256 is "
        "not 5476a3f2...; (ii) showing scc_c2_future_inextendibility and scc_c0_future_inextendibility are the "
        "same object or share a regularity selector; (iii) exhibiting an ill-typed instantiation of r on "
        "either D0 disjunct in the pinned bytes; (iv) showing 675a99d0... equals the current "
        "artifacts/formulation/evidence/taxonomy_consistency.json; (v) showing the pinned C2 passes R22 under "
        "KEY_MANIFEST fce91948..."
    ),
    "next_falsifier": (
        "Re-run this verdict's three measured checks against the live rev13 pin e9a27996: (a) the E_H2loc "
        "subset E_C0 link still appears in the live C2 ledger and still conflicts with the live C0 component; "
        "(b) tier_1 is still not r-bound; (c) f0_binding now resolves at current bytes (it declares 9e335e9b). "
        "If (a) and (b) survive at rev13 while (c) holds, the finding set transfers to the live pin."
    ),
    "bind_chain_addendum": {
        "assignment_event_id": "audit-r2-F2a-bindchain-worker-046",
        "measured_at": NOW,
        "reviewed_sha256": H["c2_pin"],
        "overall": (
            "At the pinned revision measured against the files on disk NOW: 1 declared path-bound sha256 "
            "resolves (declared_f0_sha256), 1 mismatches (consistency_evidence_sha256), 2 pointer-only "
            "references resolve, 1 pathless provenance hash is unresolved metadata. At the pin's own FROZEN "
            "rev27 window every declared path-bound hash resolved."
        ),
        "items": [
            {
                "declared_field": "f0_binding.declared_f0_sha256",
                "declared_sha256": H["declared_f0"],
                "referenced_path": "research_map/formulation_taxonomy.yaml",
                "measured_sha256": H["declared_f0"],
                "status": "resolved",
                "match": True,
                "freeze_window": "FROZEN rev27 and rev28 both declare 0abb9ed8 / 36372 B; unchanged at rev29.",
            },
            {
                "declared_field": "f0_binding.consistency_evidence_sha256",
                "declared_sha256": H["evidence_declared"],
                "referenced_path": "artifacts/formulation/evidence/taxonomy_consistency.json",
                "measured_sha256": H["evidence_current"],
                "status": "mismatch",
                "match": False,
                "freeze_window": f"FROZEN rev27 declares 675a99d0 / 728 B (matches the schema); FROZEN rev28 declares 9e335e9b / 495 B (current).",
                "preserved_bytes": f"artifacts/worker-046/f2a_rev27_verdict/evidence/taxonomy_consistency.675a99d0d25b.json#{H['evidence_declared'][:12]}",
                "classification": "hash-bound hard failure at current bytes (HF-046-F2a-01); resolved at the freeze window.",
            },
            {
                "declared_field": "class_contract_pointer",
                "declared_pointer": "research_map/formulation_taxonomy.yaml#classes.AF-SCC-C2-VAC-GEN",
                "status": "resolved",
                "match": True,
                "note": "key present in the declared taxonomy at 0abb9ed8 (36372 B).",
            },
            {
                "declared_field": "f0_binding.class_contract_supplement / class_contract_supplement_pointer",
                "declared_pointer": "artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C2-VAC-GEN",
                "measured_sha256": H["supplement"],
                "status": "resolved",
                "match": True,
                "note": "pointer-only field (no sha256 declared in f0_binding); key present; supplement bytes d7419b4e / 21699 B are unchanged across FROZEN rev27..rev29.",
            },
            {
                "declared_field": "provenance.worker_sha256 (class_boundary.provenance)",
                "declared_sha256": "21df6f7fc4a6c0492d963abb81583218643802cb5634f0e57a5bb7ad1df9f070",
                "referenced_path": None,
                "status": "unresolved_metadata",
                "match": None,
                "note": "the schema declares no path for this hash (harvested input file, not a live artifact); not a mismatch.",
            },
        ],
        "refresh_rule_satisfied_at_current_bytes": {
            "literal_rule": "the declared F0 artifact (research_map/formulation_taxonomy.yaml) did not change hash (0abb9ed8), so the literal trigger in f0_binding.rule is not met",
            "practical_answer": "No: the declared consistency-evidence hash no longer resolves (rev28 regeneration), so the binding must be refreshed and the consistency check re-run before any gate use of the pinned revision.",
        },
    },
    "evidence_hashes": H,
    "acceptance_disposition": {
        "1_pin_check": "Named-path sha256 differs from the pin (live rev13); per the acceptance this was stopped on in v1 with a blocker. v2 adds the recovered-pin substantive review because byte-identical copies of the assigned pin exist and were verified; the moving-target record is preserved in supersedes and live_path_check.",
        "2_content_checks": "class leakage, conclusion inflation, assumption completeness, decidable falsifier and disagreement-prone fields all checked: see checks{} and findings[].",
        "3_outputs": "this file + ONE review event in comms/outbox/worker-046.jsonl + one checkpoint at runtime/state/worker-046_F2a_checkpoint.json.",
        "4_checkpoint": "runtime/state/worker-046_F2a_checkpoint.json (v1 checkpoint inlined by hash).",
        "5_exit": "after writing the three outputs.",
        "explicit_checks_requested": {
            "c2_does_not_collapse_into_c0": "PASS: distinct conclusion_type with its own regularity/equation signature (checks.c2_c0_collapse).",
            "d0_binder_instantiable_on_every_disjunct": "PASS: mechanical check (checks.d0_binder_instantiation).",
        },
        "no_gate_verdict": "worker events cannot move gates or status; no gate verdict set.",
    },
    "blindness_and_contamination": (
        "v1 and v2 are authored by the same worker (worker-046). No other reviewer's F2a verdict was read "
        "before writing v1 or v2. v1's filename-collision check viewed ~1.5 KB of "
        "reviews/F2a-review-rev27-b.json (worker-091) per the v1 record; v1 rendered no class verdict, and no "
        "F2a verdict content influenced this v2. During v2 no reviews/*F2a* file was opened."
    ),
    "prior_verdict_history": [
        {
            "version": "1.0",
            "document_type": "blocker_moving_target",
            "verdict": "inconclusive",
            "score": None,
            "sha256": H["v1_verdict"],
            "summary": "Assigned pin 5476a3f2 did not resolve at the named live path (live e9a27996, rev13); per acceptance item (1) v1 stopped with a moving-target blocker and performed only the live-bytes bind-chain addendum.",
            "outbox_event_id": "w046-f2a-rev27-moving-target-blocker-01",
        }
    ],
    "hours": 0.55,
    "stop_rule": "one verdict file + one review event + one checkpoint, then exit (assignment audit-r2-F2a-a), with the bind-chain addendum folded in (audit-r2-F2a-bindchain-worker-046).",
}

# ---- 1. write the verdict file ----------------------------------------------
verdict_path = os.path.join(ROOT, "reviews/F2a-review-rev27-a.json")
with open(verdict_path, "w", encoding="utf-8") as f:
    json.dump(verdict_doc, f, indent=1, ensure_ascii=False)
    f.write("\n")
with open(verdict_path) as f:
    reloaded = json.load(f)
assert reloaded["reviewed_sha256"] == H["c2_pin"] and reloaded["verdict"] == "revise"
verdict_sha = sha("reviews/F2a-review-rev27-a.json")
print("verdict:", verdict_path, verdict_sha)

# ---- 2. one review event -----------------------------------------------------
event_id = "w046-f2a-rev27-classcontent-review-20260912T0118"
outbox = os.path.join(ROOT, "comms/outbox/worker-046.jsonl")
existing = open(outbox).read() if os.path.exists(outbox) else ""
assert event_id not in existing, "event_id already present"
if existing and not existing.endswith("\n"):
    existing += "\n"
event = {
    "event_id": event_id,
    "event_type": "review",
    "actor": "worker-046",
    "created_at": NOW,
    "target_id": "F2a",
    "node_id": "F2a",
    "class_id": "AF-SCC-C2-VAC-GEN",
    "gate": "G-FORM",
    "reviewer": "worker-046",
    "verdict": "revise",
    "score": 2.5,
    "counts_as_gate_verdict": False,
    "reviewed_sha256": H["c2_pin"],
    "reviewed_revision": 12,
    "live_sha256_at_review": H["live_c2"],
    "artifact": "reviews/F2a-review-rev27-a.json",
    "artifact_sha256": verdict_sha,
    "hard_failures": [
        "HF-046-F2a-01 (hash_bound, mismatch at current bytes): f0_binding.consistency_evidence_sha256=675a99d0 != artifacts/formulation/evidence/taxonomy_consistency.json=9e335e9b; resolved at FROZEN rev27, regenerated at rev28, repaired at rev13",
        "HF-046-F2a-02 (gate toolchain skew): pinned C2 fails R22 under FROZEN rev27 KEY_MANIFEST fce91948 but passes R01-R30 under current 014e2d30",
    ],
    "findings": [
        "F-046-F2a-01 (major): C2 asserts E_H2loc subset E_C0 while pinned C0 declines that containment; H^2_loc is not C^0 at the 4D borderline",
        "F-046-F2a-02 (moderate): tier_1 falsifier is not bound to a regularity index r in D0",
        "F-046-F2a-03 (minor): i+ exponent k >= 3 is asserted as an assumption but never bound",
        "F-046-F2a-04 (minor): Baire justification covers the Banach/Sobolev disjunct only, not the Frechet/smooth disjunct",
        "F-046-F2a-05 (minor): E(.) used for conclusions while E_C0/E_C2 denote extension sets",
        "F-046-F2a-06 (context, outside assigned file): af_scc_regularities.yaml at pin-window bytes pins rev11 components, violating its own SEP-6",
    ],
    "checks_passed": [
        "C2 and C0 do not collapse: distinct conclusion_type plus regularity/equation signature",
        "D0 binder instantiable on both disjuncts (mechanical check)",
        "no conclusion inflation (open_problem + promotion rule + no theorem claim)",
    ],
    "evidence_refs": [
        f"reviews/F2a-review-rev27-a.json#{verdict_sha[:12]}",
        f"{C2}#{H['c2_pin'][:12]}",
        f"{C0}#{H['c0_pin'][:12]}",
        f"{AGG}#{H['regularities_pin'][:12]}",
        f"artifacts/worker-048/f2a_rev27_repin_audit/snapshot/FROZEN.5fa3b3bf95f2.json#{H['frozen_rev27'][:12]}",
        f"artifacts/formulation/FROZEN.json#{H['frozen_rev29'][:12]}",
        f"research_map/formulation_taxonomy.yaml#{H['declared_f0'][:12]}",
        f"artifacts/formulation/formulation_taxonomy.yaml#{H['supplement'][:12]}",
        f"artifacts/formulation/evidence/taxonomy_consistency.json#{H['evidence_current'][:12]}",
        f"artifacts/worker-046/f2a_rev27_verdict/evidence/taxonomy_consistency.675a99d0d25b.json#{H['evidence_declared'][:12]}",
        f"artifacts/worker-046/f2a_rev27_verdict/gate_runs/gate_c2_rev27manifest.json#{H['gate_run_rev27manifest'][:12]}",
        f"artifacts/worker-046/f2a_rev27_verdict/gate_runs/gate_c2_currentmanifest.json#{H['gate_run_currentmanifest'][:12]}",
        f"artifacts/worker-046/f2a_rev27_verdict/gate_runs/d0_instantiation_check.json#{H['d0_check'][:12]}",
        f"comms/inbox/worker-046.jsonl",
    ],
    "falsifier": verdict_doc["falsifier"],
    "hours": 0.55,
}
with open(outbox, "a", encoding="utf-8") as f:
    f.write(json.dumps(event, ensure_ascii=False) + "\n")
json.loads(json.dumps(event))
outbox_event_sha = hashlib.sha256(json.dumps(event, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
print("review event appended:", event_id, outbox_event_sha[:12])

# ---- 3. checkpoint -----------------------------------------------------------
checkpoint = {
    "checkpoint": "worker-046_F2a",
    "actor": "worker-046",
    "at": NOW,
    "node_id": "F2a",
    "gate": "G-FORM",
    "class_id": "AF-SCC-C2-VAC-GEN",
    "assignments": ["audit-r2-F2a-a", "audit-r2-F2a-bindchain-worker-046"],
    "verdict": "revise",
    "score": 2.5,
    "counts_as_gate_verdict": False,
    "no_gate_verdict_set": True,
    "reviewed_sha256": H["c2_pin"],
    "reviewed_revision": 12,
    "live_sha256_at_checkpoint": H["live_c2"],
    "live_path_match": False,
    "outputs": {
        "review_file": {"path": "reviews/F2a-review-rev27-a.json", "sha256": verdict_sha},
        "outbox_event": {"id": event_id, "path": "comms/outbox/worker-046.jsonl", "canonical_json_sha256": outbox_event_sha},
        "pinned_byte_state": {"path": "artifacts/worker-046/f2a_rev27_verdict/pinned/af_scc_c2_vacuum.5476a3f2c6bc.yaml", "sha256": H["c2_pin"]},
        "gate_runs": {
            "rev27_manifest": {"path": "artifacts/worker-046/f2a_rev27_verdict/gate_runs/gate_c2_rev27manifest.json", "sha256": H["gate_run_rev27manifest"], "verdict": "fail", "rules": ["R22"]},
            "current_manifest": {"path": "artifacts/worker-046/f2a_rev27_verdict/gate_runs/gate_c2_currentmanifest.json", "sha256": H["gate_run_currentmanifest"], "verdict": "pass", "rules": []},
            "d0_instantiation": {"path": "artifacts/worker-046/f2a_rev27_verdict/gate_runs/d0_instantiation_check.json", "sha256": H["d0_check"], "verdict": "PASS"},
        },
        "v1_preserved": {
            "verdict": {"path": "artifacts/worker-046/f2a_rev27_verdict/v1_blocker/F2a-review-rev27-a.v1.json", "sha256": H["v1_verdict"]},
            "checkpoint": {"path": "artifacts/worker-046/f2a_rev27_verdict/v1_blocker/worker-046_F2a_checkpoint.v1.json", "sha256": H["v1_checkpoint"]},
        },
    },
    "hard_failures": ["HF-046-F2a-01", "HF-046-F2a-02"],
    "findings": ["F-046-F2a-01", "F-046-F2a-02", "F-046-F2a-03", "F-046-F2a-04", "F-046-F2a-05", "F-046-F2a-06"],
    "checks_passed": ["c2_c0_collapse", "d0_binder_instantiation", "conclusion_inflation"],
    "bind_chain": {"declared_f0_sha256": "resolved", "consistency_evidence_sha256": "mismatch_at_current_bytes_resolved_at_frozen_rev27", "pointers": "resolved", "refresh_rule_triggered_literally": False},
    "next_falsifier": verdict_doc["next_falsifier"],
    "hours": 0.55,
    "stop_rule": verdict_doc["stop_rule"],
}
cp_path = os.path.join(ROOT, "runtime/state/worker-046_F2a_checkpoint.json")
with open(cp_path, "w", encoding="utf-8") as f:
    json.dump(checkpoint, f, indent=1, ensure_ascii=False)
    f.write("\n")
json.load(open(cp_path))
print("checkpoint:", cp_path, sha("runtime/state/worker-046_F2a_checkpoint.json"))
print("DONE")
