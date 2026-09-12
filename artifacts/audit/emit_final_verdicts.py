#!/usr/bin/env python3
"""Emit the audit-lead closing verdicts and lifecycle report for the 2026-09-12 (04) lifecycle.

Inputs (all measured on disk at run time):
  artifacts/audit/final_gate_verify_20260912T0034.json   machine checks
  reviews/A1-rebind-coverage.json                        verdict coverage at measured hashes
  artifacts/formulation/FROZEN.json                      freeze manifest

Writes:
  reviews/G-FORM-final-verify.json
  reviews/G-F0-final-verify.json
  artifacts/audit/lead_audit_lifecycle_20260912T0035.json
No gate is set; verdicts are proposals to Astra.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CST = dt.timezone(dt.timedelta(hours=8))
NOW = dt.datetime.now(CST).isoformat(timespec="seconds")
TS = "20260912T0035"


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def load(path):
    return json.load(open(os.path.join(ROOT, path)))


def main():
    os.chdir(ROOT)
    ev = load("artifacts/audit/final_gate_verify_20260912T0034.json")
    cov = load("reviews/A1-rebind-coverage.json")
    fz = load("artifacts/formulation/FROZEN.json")
    m = ev["hash_matrix"]
    f1, f2a, f2b = m["F1"], m["F2a"], m["F2b"]
    f0 = m["F0"]

    cov_tbl = {}
    for t, c in cov["coverage"].items():
        cov_tbl[t] = {
            "measured_sha256": c["measured_sha256"],
            "independent_verdicts_at_hash": c["independent_verdict_count"],
            "accepts_at_hash": [r["reviewer"] for r in c["verdicts_at_measured_hash"] if r["verdict"] == "accept"],
            "revises_at_hash": [r["reviewer"] for r in c["verdicts_at_measured_hash"] if r["verdict"] == "revise"],
            "inconclusive_at_hash": [r["reviewer"] for r in c["verdicts_at_measured_hash"] if r["verdict"] == "inconclusive"],
            "recorded_verdicts_total": len(c["all_recorded_verdicts"]),
            "status": "void_at_this_hash" if c["independent_verdict_count"] < 2 else "sufficient",
        }

    verified_fixed = [
        {"id": "VF-1", "item": "D0 ill-typed/disjunctive binder (HF-088-1 / F-2)",
         "status": "fixed", "evidence": "binder is now 'forall r in D0' over a tagged disjoint union with a per-branch ambient space X^r_vac(AF); all three schemas pass the audit D0 check"},
        {"id": "VF-2", "item": "duplicate top-level YAML revised_at keys (data loss)",
         "status": "fixed", "evidence": "mapping-scoped YAML event parse: 0 duplicate keys in all three schemas and both taxonomies; history moved to revision_history"},
        {"id": "VF-3", "item": "future-dated revised_at (clock discipline)",
         "status": "fixed", "evidence": "revised_at 2026-09-12T00:31:41+08:00 <= file mtime 00:32:02; declared-after-write interval now negative"},
        {"id": "VF-4", "item": "class_contract_pointer resolving only in the authoring tree",
         "status": "fixed", "evidence": "pointer repointed to research_map/formulation_taxonomy.yaml#classes.<CLASS> and resolves; supplement moved to a separate class_contract_supplement_pointer field"},
        {"id": "VF-5", "item": "F0 AF-WCC-SCALAR-SPH set-based visibility wording (D1 residue)",
         "status": "fixed", "evidence": "F0 rev5 conclusion uses the single-q tail predicate and states the set-based reading is variant SET, not this class"},
        {"id": "VF-6", "item": "F0 AF-WCC-SCALAR-SPH missing explicit comeager quantifier",
         "status": "fixed", "evidence": "all four F0 classes now state 'For ... comeager set G ...' in the conclusion text"},
        {"id": "VF-7", "item": "F1 AF_{I+} undefined symbol",
         "status": "fixed", "evidence": "i_plus.predicate_abbreviation defines AF_{I+} as the i_plus existence predicate"},
        {"id": "VF-8", "item": "F1 falsifier tests bound to superseded hash",
         "status": "fixed", "evidence": "25/25 rows in schemas/f1_falsifier_tests.jsonl carry binding_sha256=cce9c60146d6 == measured F1"},
        {"id": "VF-9", "item": "formulation binding structural gate / taxonomy consistency / class separation / map validity",
         "status": "fixed", "evidence": "check_class_schema PASS x3 (exit 0, failed_rules=[]); check_taxonomy_consistency CONSISTENT; classsep_regression 17/17 leaks, 10/10 controls, FP 0; validate_map VALID"},
    ]

    gform = {
        "schema": "audit-final-verify/v1",
        "target_id": "F1,F2a,F2b",
        "gate": "G-FORM",
        "reviewer": "astra-lead-audit",
        "actor": "astra-lead-audit",
        "review_kind": "closing gate verification at one frozen hash (assignment astra-life03-verify-gform)",
        "counts_as_full_schema_verdict": False,
        "scope": ("closing gate verification: independent re-measurement of the rev27 machine defects + coverage "
                  "adjudication at one instant; not a fresh 26-field structural pass per class"),
        "created_at": NOW,
        "measured_at": ev["measured_at"],
        "verdict": "revise",
        "score": 3.5,
        "reviewed_sha256": {
            "F1": f1["canonical_sha256"], "F2a": f2a["canonical_sha256"], "F2b": f2b["canonical_sha256"],
        },
        "frozen_manifest": {"path": "artifacts/formulation/FROZEN.json", "revision": fz.get("revision"),
                            "frozen_at": fz.get("frozen_at"), "sha256": sha("artifacts/formulation/FROZEN.json")},
        "frozen_pin_match": {"F1": f1["frozen_match"], "F2a": f2a["frozen_match"], "F2b": f2b["frozen_match"]},
        "mirror_equal": {"F1": f1["mirror_equal"], "F2a": f2a["mirror_equal"], "F2b": f2b["mirror_equal"]},
        "verified_fixed": verified_fixed,
        "coverage_table": cov_tbl,
        "blocking_items": [
            {"id": "B-GFORM-1", "severity": "blocking",
             "finding": "no class reaches two independent verdicts at the rev27 frozen hash: F1 1 (worker-088, revise), F2a 0, F2b 0 (recorded verdicts 17/10/15 all cite superseded hashes and are void for binding)",
             "needed": "Astra re-dispatches two blind reviewers per class against the exact rev27 hashes; a verdict counts only if the hash is unchanged when the second verdict lands"},
            {"id": "B-GFORM-2", "severity": "blocking",
             "finding": "the freeze moved during every review round: 5 target revisions inside this lifecycle window (F0 276009f4->0abb9ed8; F1 9a8bd4c9->b474fbc4->cce9c601; F2a b6123750->a7ccae4d->5476a3f2; F2b 1bb78ce9->b71ec02c->55d0a1ea; L0 ce42d205->3e3d3553), plus a transient KEY_MANIFEST lag that made check_class_schema FAIL R22 on rev12 before passing at 00:33:55",
             "needed": "declare a quiescence window (no writes to the frozen paths), then run the re-review; publish FROZEN rev27 pins before dispatching reviewers"},
            {"id": "B-GFORM-3", "severity": "blocking",
             "finding": "all pre-rev27 verdicts are superseded; counting any of the earlier accepts (e.g. F2a worker-047, F2b worker-030/flash-17) at the new hashes would violate the assignment falsifier",
             "needed": "next lifecycle must re-scan reviews/*.json and apply only verdicts whose cited sha256 equals the rev27 pin"},
        ],
        "open_objections_non_blocking": [
            {"id": "O-GFORM-1", "finding": "F2a and F2b data_class blocks remain structurally key-identical and no H^4_{1/2+eps} (or equivalent local-regularity) signature appears in the C2 data_class; the C2/C0 separation rests on regularity_token + extension_predicate. Needs an explicit reviewer adjudication that this is the intended encoding, or a field-level differentiation.",
             "source": "carried from prior audit r2 / worker-088 findings; re-verified at the rev27 bytes"},
            {"id": "O-GFORM-2", "finding": "audit_evidence.py now reports 8 hard CLASSSEP findings, all on map claim prose that describes or denies a C0/C2 merge (e.g. claims[101] 'no C0/C2 merge exists', claims[112] quotes the detector's own target). The detector is not negation-aware on claim text; the hard count is inflated. The 27-fixture regression stays 17/17/10/10.",
             "source": "own re-run at 00:34; claims are agent-authored and must be rephrased by their authors (CF-16)"},
            {"id": "O-GFORM-3", "finding": "map bookkeeping lag: for F0/F1/F2a/F2b the declared artifact_sha256 still holds the pre-rev27 value while artifact_sha256_measured holds the current one; gates[].unmet and controller_gate_audit still quote pre-rev27 hashes.",
             "source": "research_map.json at 00:34"},
        ],
        "gate_proposal": {"gate": "G-FORM", "verdict": "pending",
                          "reason": "content repairs verified at FROZEN rev27, but the assignment's own acceptance criterion (two independent verdicts per class at the frozen hash) is unmet and the freeze moved during review"},
        "authority": "proposal only; the audit lead does not set gate verdicts",
        "next_falsifier": "two accepting verdicts for one class citing sha256 cce9c60146d6/5476a3f2c6bc/55d0a1ea9bda from distinct non-authors, or a gate read that counts a pre-rev27 accept",
        "evidence_refs": [
            f"artifacts/audit/final_gate_verify_20260912T0034.json#{sha('artifacts/audit/final_gate_verify_20260912T0034.json')[:12]}",
            f"reviews/A1-rebind-coverage.json#{sha('reviews/A1-rebind-coverage.json')[:12]}",
            f"artifacts/formulation/FROZEN.json#{sha('artifacts/formulation/FROZEN.json')[:12]}",
        ],
    }

    gf0 = {
        "schema": "audit-final-verify/v1",
        "target_id": "F0",
        "gate": "G-F0",
        "reviewer": "astra-lead-audit",
        "actor": "astra-lead-audit",
        "review_kind": "closing gate verification at one frozen hash (assignment astra-life03-verify-gf0)",
        "counts_as_full_schema_verdict": False,
        "scope": "closing gate verification of F0 rev5 at the declared canonical path; not a fresh full-content review",
        "created_at": NOW,
        "measured_at": ev["measured_at"],
        "verdict": "revise",
        "score": 3.5,
        "reviewed_sha256": {"F0": f0["canonical_sha256"]},
        "authoring_sha256": f0["authoring_sha256"],
        "frozen_manifest": {"path": "artifacts/formulation/FROZEN.json", "revision": fz.get("revision"),
                            "frozen_at": fz.get("frozen_at"), "sha256": sha("artifacts/formulation/FROZEN.json")},
        "acceptance_checks": {
            "exactly_four_frozen_class_ids": True,
            "single_q_tail_visibility_predicate": True,
            "explicit_comeager_quantifier_all_four_classes": True,
            "canonical_equals_authoring_equals_frozen_pin": False,
            "duplicate_yaml_keys": False,
        },
        "verified_fixed": [v for v in verified_fixed if v["id"] in ("VF-2", "VF-3", "VF-5", "VF-6")],
        "coverage_table": {k: cov_tbl[k] for k in ("F0",)},
        "blocking_items": [
            {"id": "B-GF0-1", "severity": "blocking",
             "finding": "0 independent verdicts cite the rev27 canonical hash 0abb9ed8a96135c9; 8 recorded verdicts (4 revise, 2 inconclusive, 2 more) all cite superseded hashes and are void for binding",
             "needed": "two blind non-author reviewers at 0abb9ed8a961, hash re-checked at the second verdict"},
            {"id": "B-GF0-2", "severity": "blocking",
             "finding": "canonical F0 0abb9ed8a961 != authoring d7419b4e8963; FROZEN rev27 explicitly keeps them as two logical artifacts and the f0_mirror_adjudication_request (REC-1/REC-2) is still open, so the assignment's 'canonical == authoring == FROZEN pin' criterion cannot be confirmed",
             "needed": "controller adjudication: REC-1 pair-check exception (safe now that the schemas' class_contract_pointer targets canonical #classes and the supplement pointer is a separate field), or REC-2 bounded re-freeze with schema pointer refresh"},
        ],
        "open_objections_non_blocking": [
            {"id": "O-GF0-1", "finding": "AF-WCC-SCALAR-SPH axes.genericity_kind is still 'unresolved' while its rev5 conclusion quantifies over an explicit comeager set; the field and the conclusion disagree (the taxonomy consistency checker does not compare this field)",
             "source": "own measurement at the rev27 bytes"},
            {"id": "O-GF0-2", "finding": "the canonical taxonomy carries revision_note / revision_note_rev3 / revision_note_rev4 side by side; harmless today, but a stale-field trap for readers",
             "source": "own measurement at the rev27 bytes"},
        ],
        "gate_proposal": {"gate": "G-F0", "verdict": "pending",
                          "reason": "content objections discharged at rev5, but zero verdicts at the frozen hash and the canonical/authoring split is unadjudicated"},
        "authority": "proposal only; the audit lead does not set gate verdicts",
        "next_falsifier": "an F0 accept citing a hash other than 0abb9ed8a961, or a mirror-equality claim that treats 0abb9ed8 and d7419b4e as one artifact",
        "evidence_refs": [
            f"artifacts/audit/final_gate_verify_20260912T0034.json#{sha('artifacts/audit/final_gate_verify_20260912T0034.json')[:12]}",
            f"reviews/A1-rebind-coverage.json#{sha('reviews/A1-rebind-coverage.json')[:12]}",
            f"research_map/formulation_taxonomy.yaml#{f0['canonical_sha256'][:12]}",
            f"artifacts/formulation/formulation_taxonomy.yaml#{f0['authoring_sha256'][:12]}",
        ],
    }

    report = {
        "schema": "audit-lead-lifecycle/v2",
        "lifecycle": "lead-audit-2026-09-12T00:28-00:36+08:00 (lifecycle 04)",
        "actor": "astra-lead-audit",
        "scope": "one independent audit-group lifecycle: read handoff/map/comms, consume the audit queue, review artifacts, emit verdicts/events/checkpoint, report blockers, exit",
        "created_at": NOW,
        "measured_at": ev["measured_at"],
        "queue_consumed": [
            "astra-life03-verify-gform -> reviews/G-FORM-final-verify.json (revise, pending gate)",
            "astra-life03-verify-gf0 -> reviews/G-F0-final-verify.json (revise, pending gate)",
            "astra-life02-softflag-f0f1 (superseded by the rev27 publication; the two soft flags are gone at the new hashes)",
            "astra-life02-n0-c8 / -refresh (C8 accept at protocol rev3 stands; C4 registration still open)",
            "astra-life01-a1-rebind / astra-indep-1-A1-audit (coverage re-scanned at rev27; no class reaches two verdicts)",
        ],
        "freeze_timeline_this_lifecycle": [
            "00:28:33 measured F0 276009f4, F1 9a8bd4c9, F2a b6123750, F2b 1bb78ce9, L0 ce42d205 (FROZEN rev26)",
            "00:30:49 ledger/theorems.jsonl rewritten ce42d205 -> 3e3d3553 (status vocabulary accepted -> included_unreviewed + review_status; HF-14 condition no longer fires)",
            "00:31:41/00:31:56 F0 canonical -> 0abb9ed8, authoring -> d7419b4e",
            "00:32:02 schemas -> cce9c601 / 5476a3f2 / 55d0a1ea (rev12), new schemas/af_scc_regularities.yaml 94562101",
            "00:32:59 FROZEN rev27 published, pinning the above",
            "00:33:55 KEY_MANIFEST regenerated (014e2d30); check_class_schema flips FAIL R22 -> PASS x3",
            "00:32:14 -> 00:33:49 -> 00:34:30 hashes stable across the verification window (last probe)",
        ],
        "current_hash_matrix": {k: {kk: vv for kk, vv in v.items() if kk in ("canonical", "canonical_sha256", "authoring_sha256", "mirror_equal", "frozen_pin", "frozen_match")}
                                for k, v in m.items()},
        "audit_verdicts_final": {
            "G-FORM": {"verdict": "revise", "score": 3.5, "file": "reviews/G-FORM-final-verify.json",
                       "blockers": ["no class has 2 independent verdicts at the rev27 hash (F1 1 revise, F2a 0, F2b 0)",
                                    "freeze moved throughout the review window; pre-rev27 verdicts void",
                                    "transient KEY_MANIFEST lag briefly failed the binding gate after the schemas changed"]},
            "G-F0": {"verdict": "revise", "score": 3.5, "file": "reviews/G-F0-final-verify.json",
                     "blockers": ["0 verdicts at 0abb9ed8a961", "canonical/authoring split unadjudicated (REC-1/REC-2 open)"]},
            "G-AUDIT": {"verdict": "pending", "reason": "A0 rubric detectors still reference fields absent from the frozen ledger (HF-01 artifact_refs); genericity vocabulary rejects residual_comeager; conclusion_primary promotes the equivalence F1 marks UNVERIFIED; validation.last_run null. Plus audit_evidence negation-blind FPs inflate the hard count to 8."},
            "G-LIT": {"verdict": "pending", "reason": "L0 moved to 3e3d3553; coverage there is 1 accept (worker-006) + 1 revise (flash-17) at the new hash; L1 unchanged at 315c1914 with 4+ spot checks"},
            "G-NUM": {"verdict": "pending", "reason": "C8 accept at protocol rev3 1e6cdf04 stands; C4 registration of n0_replication_astra_run2_FIXED.json#6542db93 still missing; N1 locked"},
        },
        "verified_fixes_at_rev27": verified_fixed,
        "blockers": [
            {"id": "AUD-B1", "node": "A1/G-FORM", "description": "At the FROZEN rev27 hashes no formulation class reaches two independent verdicts (F1 1 revise, F2a 0, F2b 0; F0 0). All 50 recorded verdicts across F0/F1/F2a/F2b cite superseded hashes.", "needed_to_unblock": "quiescence window + two blind reviewers per class at the rev27 pins"},
            {"id": "AUD-B2", "node": "F0/G-F0", "description": "F0 canonical 0abb9ed8 != authoring d7419b4e; FROZEN rev27 keeps two logical artifacts; REC-1/REC-2 adjudication still open, so no F0 verdict can bind byte-identically.", "needed_to_unblock": "controller adjudication (REC-1 is now low-risk: class_contract_pointer targets canonical #classes)"},
            {"id": "AUD-B3", "node": "A0/G-AUDIT", "description": "A0 rubric conformance defects persist at d748a9e3574e: HF-01 detector reads claim.artifact_refs (absent from ledger rows); the G-FORM genericity vocabulary excludes residual_comeager; conclusion_primary=future_asymptotic_predictability promotes an equivalence F1 marks UNVERIFIED; validation.last_run=null.", "needed_to_unblock": "rewrite the detectors onto frozen fields + add the alias mapping + run the rubric validator"},
            {"id": "AUD-B4", "node": "A1/checkers", "description": "audit_evidence.py reports 8 hard CLASSSEP findings, all negation-blind false positives on map claim prose that describes or denies a C0/C2 merge; the 27-fixture regression is still 17/17/10/10. Hard-failure metric is inflated.", "needed_to_unblock": "negation-aware claim scanning or claim-text rephrasing by the authors (CF-16: the audit lead must not edit them)"},
            {"id": "AUD-B5", "node": "N0/G-NUM", "description": "C4 still open: runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json#6542db93 is not registered in runtime/state/artifact_hashes.json.", "needed_to_unblock": "controller registers the hash, then adjudicates G-NUM; N1 stays locked"},
            {"id": "AUD-B6", "node": "GLOBAL", "description": "Map bookkeeping lag: declared artifact_sha256 for F0/F1/F2a/F2b is pre-rev27 while artifact_sha256_measured is current; gates[].unmet and controller_gate_audit still quote pre-rev27 hashes; 74 ingested events are future-dated (max 02:00).", "needed_to_unblock": "controller re-measures and re-emits gate reasons; clamp/reject future created_at"},
        ],
        "toolchain_results": {
            "check_class_schema.py": "PASS x3 (exit 0, failed_rules=[]) at rev12 after KEY_MANIFEST regeneration; transient FAIL R22 before it",
            "check_taxonomy_consistency.py": "CONSISTENT (4 classes, 0 contract-text divergences)",
            "classsep_regression.py": "PASS 17/17 leaks, 10/10 controls, FP 0 FN 0",
            "validate_map.py": "VALID",
            "audit_evidence.py": "8 hard, 0 soft - all 8 are CLASSSEP negation-blind hits on claim prose (see AUD-B4)",
            "final_gate_verify.py": "29 pass / 13 fail / 1 note at the rev27 instant (see evidence file)",
            "a1_rebind_coverage.py": "measured 00:33:49 at rev27 hashes; F0 0, F1 1, F2a 0, F2b 0 independent verdicts",
        },
        "never_self_passed": "no gate verdict set by this lifecycle; all gate entries are proposals",
        "instance_exit": "one lifecycle completed; the audit instance exits after emitting events and the checkpoint",
    }

    out = {
        "reviews/G-FORM-final-verify.json": gform,
        "reviews/G-F0-final-verify.json": gf0,
        f"artifacts/audit/lead_audit_lifecycle_{TS}.json": report,
    }
    for path, obj in out.items():
        with open(path, "w") as f:
            json.dump(obj, f, indent=2)
        print(f"wrote {path} sha256={sha(path)[:12]}")


if __name__ == "__main__":
    main()
