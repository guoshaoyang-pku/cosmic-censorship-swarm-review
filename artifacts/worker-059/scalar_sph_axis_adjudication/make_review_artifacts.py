#!/usr/bin/env python3
"""Build the W059-SCALARSPH-AXIS-ADJ-01 review, matrix, audit and checkpoint
artifacts from the frozen snapshots + independent_evidence.json.

Deterministic: no network, no canonical-state writes.
"""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
D = ROOT / "artifacts/worker-059/scalar_sph_axis_adjudication"
SNAP = D / "snapshot"
SCALAR = "AF-WCC-SCALAR-SPH"
PIN = {
    "canonical_F0": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "supplement_F0R": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "VOCAB_ALIASES": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "rule_spec": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "FROZEN_r28": "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


ev = json.loads((D / "independent_evidence.json").read_text())
import yaml
A = yaml.safe_load((SNAP / "formulation_taxonomy.canonical.0abb9ed8a961.yaml").read_text())
B = yaml.safe_load((SNAP / "formulation_taxonomy.supplement.d7419b4e8963.yaml").read_text())
R1 = json.loads((SNAP / "VOCAB_ALIASES.46cd9f1eb534.json").read_text())
R2 = json.loads((SNAP / "rule_spec.40f9bb9e657b.json").read_text())
M = json.loads((SNAP / "research_map.at00T0053.json").read_text())
checks = {c["id"]: c for c in ev["checks"]}

# ---------------- claims binding audit ----------------
bound, ct_counts, asserting = 0, Counter(), []
for i, c in enumerate(M.get("claims") or []):
    ids = set()
    if isinstance(c.get("class_id"), str):
        ids.add(c["class_id"])
    for x in (c.get("class_ids") or []):
        ids.add(str(x))
    if SCALAR not in ids:
        continue
    bound += 1
    ct_counts[str(c.get("conclusion_type"))] += 1
    s = str(c.get("statement") or "")
    if re.search(r"no visible singularity|visible from I\+|weak cosmic censorship (holds|is proved)|MGHD admits I\+", s, re.I):
        asserting.append({"claim_index": i, "conclusion_type": c.get("conclusion_type"), "actor": c.get("actor")})
claims_audit = {
    "task_id": "W059-SCALARSPH-AXIS-ADJ-01",
    "class_id": SCALAR,
    "map_snapshot_sha256": sha(SNAP / "research_map.at00T0053.json"),
    "map_updated_at": M.get("updated_at"),
    "claims_scalar_bound": bound,
    "conclusion_type_counts": dict(ct_counts),
    "theorem_level_claims": [k for k in ct_counts if k in ("theorem", "conditional_theorem")],
    "claims_asserting_class_wcc_conclusion": asserting,
    "h4_rule": str(next(h for h in A["classes"][SCALAR]["hypotheses"] if h["id"] == "H4")["text"]),
    "verdict": ("H4 deferral honoured: no live claim bound to the class asserts its WCC conclusion; "
                "the class is not truth-apt and the defect is prospective, not retrospective."),
    "falsifier": ("Any claim in a later pinned map with class binding AF-WCC-SCALAR-SPH, "
                  "conclusion_type theorem/conditional_theorem, asserting the class WCC conclusion "
                  "while axes.genericity_kind stays unresolved."),
}
(D / "claims_binding_audit.json").write_text(json.dumps(claims_audit, indent=1) + "\n")

# ---------------- axis legality matrix ----------------
kind = A["classes"][SCALAR]["axes"]["genericity_kind"]
r1_canon, r1_class = None, "unregistered"
for c, al in R1["genericity_kind"].items():
    if kind == c or kind in al:
        r1_canon, r1_class = c, ("canonical" if kind == c else "alias")
r2_list = R2["vocabularies"]["genericity_kind"]
f0_allowed = A["field_vocabulary"]["genericity_kind"]["allowed"]


def status(tok):
    rc, rcl = None, "unregistered"
    for c, al in R1["genericity_kind"].items():
        if tok == c or tok in al:
            rc, rcl = c, ("canonical" if tok == c else "alias")
    return {
        "token": tok,
        "F0_field_vocabulary_allowed": tok in f0_allowed,
        "rule_spec_R2_vocabulary": tok in r2_list,
        "VOCAB_R1_status": rcl,
        "VOCAB_R1_canonical_form": rc,
        "VOCAB_R1_policy": R1["policy"],
        "new_canonical_artifact_legal": (tok in r2_list) and (rcl == "canonical"),
    }


matrix = {
    "task_id": "W059-SCALARSPH-AXIS-ADJ-01",
    "class_id": SCALAR,
    "governing_question": ("which genericity_kind token may legally stand in the scalar class of a canonical F0 "
                           "revision, and what does each candidate cost"),
    "pins": PIN,
    "measured": {
        "canonical_axis_kind": kind,
        "supplement_frozen_kind": B["axis_registry"]["genericity_axis"]["frozen"][SCALAR],
        "supplement_values_list": B["axis_registry"]["genericity_axis"]["values"],
        "F0_field_vocabulary_rule": A["field_vocabulary"]["genericity_kind"]["rule"],
        "conclusion_asserts_comeager": bool(re.search(
            r"comeager", A["classes"][SCALAR]["conclusion"]["text"], re.I)),
        "genericity_topology_slot_present_scalar": "genericity_topology" in A["classes"][SCALAR]["axes"],
        "genericity_topology_slots_present_all_classes": checks["G5"]["measured"],
    },
    "candidates": [
        status("unresolved"),
        status("provisional_baire_residual"),
        status("residual_comeager"),
    ],
    "staged_worker_001_patch": {
        "artifact": "artifacts/worker-001/f0_genericity_audit/patch_proposal.diff",
        "canonical_arm_change": "AF-WCC-SCALAR-SPH axes.genericity_kind unresolved -> provisional_baire_residual; genericity_topology: unresolved added to all four classes",
        "registry_measurement": status("provisional_baire_residual"),
        "rec12_bound": ("REC-12 explicitly forbids any change to class id, hypothesis, conclusion predicate, "
                        "axis semantics or F0 canonical byte. The canonical arm changes axis semantics and adds a "
                        "new axis key, therefore it is outside the authorized repair card and would require a fresh "
                        "F0 revision with a re-run of the F0 acceptance round."),
        "registry_clean": False,
    },
    "finding": ("No currently registered token expresses the scalar class's actual state (comeager kind asserted in "
                "the conclusion, topology and value status pending). unresolved is unregistered in both registries; "
                "provisional_baire_residual is an R1 alias the VOCAB policy forbids in a new canonical artifact and is "
                "absent from R2; residual_comeager is clean in both registries but would fix a kind the class declares "
                "unresolved. A controller ruling must designate the governing registry and either register a pending "
                "token or authorise the residual_comeager + genericity_topology: unresolved repair."),
}
(D / "axis_legality_matrix.json").write_text(json.dumps(matrix, indent=1) + "\n")

# ---------------- review ----------------
review = {
    "review_id": "W059-SCALARSPH-AXIS-ADJ-01",
    "task_id": "W059-SCALARSPH-AXIS-ADJ-01",
    "actor": "worker-059",
    "reviewer": "worker-059",
    "target_id": "F0/AF-WCC-SCALAR-SPH",
    "target_path": "research_map/formulation_taxonomy.yaml",
    "node_id": "F0",
    "group_id": "formulation",
    "class_id": SCALAR,
    "gate": "G-F0",
    "reviewed_revision": 5,
    "reviewed_sha256": PIN["canonical_F0"],
    "companion_sha256": PIN["supplement_F0R"],
    "verdict": "revise",
    "score": 3.5,
    "counts_as_independent_verdict": True,
    "counts_as_full_schema_verdict": False,
    "counts_as_independent_second_verdict": False,
    "independence_caveat": ("Own instrument (stdlib+PyYAML, no canonical-gate imports, no other worker's checker "
                            "imported), 10/10 declared single-defect mutants detected; canonical consistency tool "
                            "re-run in a throwaway sandbox. Prior reviewers (worker-016 F-16F0-4, worker-094 "
                            "F-094-F0-01, F0-review-18/19, worker-001 self-audit) converged on parts of G4/G5; the "
                            "D3 record contradiction, the R1/R2 registry matrix for all three candidate tokens, the "
                            "ownership three-way split and the claims-materiality measurement are new here."),
    "hard_failures": [
        {
            "id": "HF-059-SPH-01",
            "name": "D3_discharge_record_scope_contradiction",
            "severity": "blocking for record integrity (class semantics unaffected)",
            "detail": ("At the FROZEN rev28 pair, canonical A class_scope_adjudication.resolved_divergences[D3] "
                       "records 'confirmed discharged for ALL FOUR classes, including AF-WCC-SCALAR-SPH', while "
                       "supplement B contract_divergences.items[D3].class records 'all three vacuum classes' and its "
                       "resolution never mentions the scalar class. The canonical consistency tool re-run in sandbox "
                       "prints 'CONSISTENT (4 classes, 0 contract-text divergences)' (exit 0) because it recomputes "
                       "D1-D3 from conclusion texts instead of comparing the stored records, so the certificate is "
                       "silent on the contradiction (check R3c). The D3 record therefore cannot be cited as evidence "
                       "that the scalar class is discharged."),
            "evidence_refs": ["independent_evidence.json#R2c", "independent_evidence.json#R2c_evidence",
                              "independent_evidence.json#R3c"],
            "falsifier": ("A single-scope D3 record in both A and B (or a controller ruling that the stored records "
                          "are non-binding prose), at pinned bytes."),
        },
        {
            "id": "HF-059-SPH-02",
            "name": "no_registry_clean_genericity_token_and_missing_two_slot",
            "severity": "blocking pending controller registry ruling",
            "detail": ("scalar axes.genericity_kind='unresolved' is admitted by F0's own field_vocabulary but is "
                       "unregistered in both independent registries: absent from rule_spec.vocabularies.genericity_kind "
                       "and neither a canonical key nor a declared alias in VOCAB_ALIASES (checks G2/G3). The class "
                       "conclusion is generic-quantified ('comeager set G') yet no class instantiates the declared "
                       "genericity_topology slot required by F0's own field_vocabulary rule (G4/G5: 0/4 classes); the "
                       "supplement freezes a value ('unresolved') absent from its own axis values list (G6). Of the "
                       "three candidate tokens only residual_comeager is legal in both registries, but it would fix a "
                       "kind the class declares unresolved. The staged worker-001 canonical arm (kind -> "
                       "provisional_baire_residual) is an R1 alias and outside REC-12's no-axis-semantics-change bound."),
            "evidence_refs": ["independent_evidence.json#G2", "independent_evidence.json#G3",
                              "independent_evidence.json#G4", "independent_evidence.json#G5",
                              "independent_evidence.json#G6", "axis_legality_matrix.json"],
            "falsifier": ("One governing registry designated plus a scalar genericity_kind + genericity_topology "
                          "written from it at new pinned bytes, with the result present in the F0 round's reviewed "
                          "hash."),
        },
    ],
    "findings": [
        {"id": "F-059-SPH-01", "severity": "major", "text":
            "Ownership of the unresolved scalar genericity is a three-way split: A.H4 owned_by='L0/L1 (no F-node "
            "owns this class in the current map)', B.axis_registry.scalar_note says 'owned by that future node', and "
            "B.class_contracts[scalar].node_id='unmapped (N0 depends on F0 only)'. The pinned map has no formulation "
            "F-node for the class (check G10), so A is the artifact consistent with the map and B's stated owner does "
            "not exist."},
        {"id": "F-059-SPH-02", "severity": "major", "text":
            "Supplement scalar_note provenance is stale/incorrect: it cites 'worker-01 rev3' and 'records genericity "
            "as provisional', while the declared canonical artifact is rev5 and records genericity_kind='unresolved' "
            "with genericity_value_status='unresolved_pending_L1' (check G8)."},
        {"id": "F-059-SPH-03", "severity": "major", "text":
            "Reproduced F0-wide: genericity_topology is declared with a mandatory rule but instantiated in 0/4 class "
            "axes blocks (G5). Corroborates worker-016 F-16F0-4, worker-094 F-094-F0-01, F0-review-18/19 and "
            "worker-001 G-TOPOLOGY-SLOT-ABSENT; the accepting dispositions treated it as non-blocking because "
            "claims_theorem_status is false."},
        {"id": "F-059-SPH-04", "severity": "advisory (materiality)", "text":
            "Materiality measured on the 00:53 map snapshot: 95 claims are bound to AF-WCC-SCALAR-SPH; 0 are "
            "theorem/conditional_theorem and 0 assert the class WCC conclusion (R4c; conclusion_type counts "
            "numerical_evidence 27 / formal_model 56 / stability_result 7 / open_problem 5). H4's 'must be named "
            "before any claim is filed' is therefore honoured in the truth-apt sense: no promoted result depends on "
            "the unresolved token. The defect is prospective and the class must stay closed to WCC claims until a "
            "legal token exists."},
        {"id": "F-059-SPH-05", "severity": "advisory (staged repair review)", "text":
            "The worker-001 coupled patch would make the consistency arms pass, but the canonical arm changes "
            "axes.genericity_kind, which REC-12 forbids ('axis semantics ... may not change'), and the replacement "
            "token is a VOCAB alias forbidden in new canonical artifacts. It should not be folded into the "
            "astra-life05-evidence-binding-repair; if adopted at all it needs a fresh F0 revision, a canonical "
            "token, and a re-run of the F0 acceptance round."},
        {"id": "F-059-SPH-06", "severity": "advisory (content surface green)", "text":
            "Scalar class content checks pass at the hash: family/matter/symmetry/regularity/conclusion_type "
            "consistent across the two artifacts (X1-X5), conclusion asserts the single-q TAIL predicate with no "
            "assertive set-based J-(I+) wording (X6, R1c), SCC content excluded (X8), D1 resolved, FROZEN rev28 pins "
            "both artifacts at the measured hashes (R5c). Only the genericity/record layer is defective."},
    ],
    "evidence_refs": [
        "artifacts/worker-059/scalar_sph_axis_adjudication/independent_evidence.json",
        "artifacts/worker-059/scalar_sph_axis_adjudication/axis_legality_matrix.json",
        "artifacts/worker-059/scalar_sph_axis_adjudication/claims_binding_audit.json",
        "artifacts/worker-059/scalar_sph_axis_adjudication/check_scalar_sph_axis.py",
        "artifacts/worker-059/scalar_sph_axis_adjudication/snapshot/formulation_taxonomy.canonical.0abb9ed8a961.yaml#0abb9ed8a961",
        "artifacts/worker-059/scalar_sph_axis_adjudication/snapshot/formulation_taxonomy.supplement.d7419b4e8963.yaml#d7419b4e8963",
    ],
    "next_falsifier": ("A controller ruling designating the governing genericity registry for AF-WCC-SCALAR-SPH and a "
                       "single F0 revision in which (i) both D3 records carry the same class scope, (ii) the scalar "
                       "axes carry a genericity_kind that is canonical under that registry and an instantiated "
                       "genericity_topology, at FROZEN-pinned bytes. Hash drift of A 0abb9ed8 or B d7419b4e voids "
                       "this verdict immediately; new pinned bytes require re-measurement."),
    "validation_status": "unverified",
    "note": ("Advisory worker verdict; cannot set node status or gate verdict (ASTRA_HANDOFF authority note). "
             "No canonical artifact or global state was mutated; the consistency tool ran only inside a temp tree."),
}
(D / "review_F0scalar_0abb9ed8.json").write_text(json.dumps(review, indent=1) + "\n")

# ---------------- checkpoint ----------------
ckpt = {
    "checkpoint_id": "w059-ckpt-scalarspaxis-20260912T0053",
    "task_id": "W059-SCALARSPH-AXIS-ADJ-01",
    "actor": "worker-059",
    "class_id": SCALAR,
    "node_id": "F0",
    "created_at": "2026-09-12T00:56:00+08:00",
    "reviewed_sha256": PIN["canonical_F0"],
    "companion_sha256": PIN["supplement_F0R"],
    "checks": {"total": ev["checks_total"], "pass": ev["checks_pass"], "failures": ev["failures"]},
    "mutants": {"total": ev["mutants_total"], "detected": ev["mutants_detected"]},
    "hard_failures": ["HF-059-SPH-01", "HF-059-SPH-02"],
    "verdict": "revise 3.5",
    "artifacts": [
        "artifacts/worker-059/scalar_sph_axis_adjudication/independent_evidence.json",
        "artifacts/worker-059/scalar_sph_axis_adjudication/axis_legality_matrix.json",
        "artifacts/worker-059/scalar_sph_axis_adjudication/claims_binding_audit.json",
        "artifacts/worker-059/scalar_sph_axis_adjudication/review_F0scalar_0abb9ed8.json",
        "artifacts/worker-059/scalar_sph_axis_adjudication/check_scalar_sph_axis.py",
    ],
    "global_state_mutated": False,
    "next_falsifier": review["next_falsifier"],
}
(D / "checkpoint_w059_scalar_axis.json").write_text(json.dumps(ckpt, indent=1) + "\n")
print(json.dumps({"ok": True,
                  "review_sha256": sha(D / "review_F0scalar_0abb9ed8.json"),
                  "matrix_sha256": sha(D / "axis_legality_matrix.json"),
                  "claims_sha256": sha(D / "claims_binding_audit.json"),
                  "checkpoint_sha256": sha(D / "checkpoint_w059_scalar_axis.json"),
                  "evidence_sha256": sha(D / "independent_evidence.json"),
                  "checker_sha256": sha(D / "check_scalar_sph_axis.py")}, indent=1))
