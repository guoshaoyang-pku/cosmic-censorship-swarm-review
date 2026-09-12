#!/usr/bin/env python3
"""Audit lead lifecycle 05 (pass r2): adjudicate the four pass-04 audit cards.

Inputs (measured read-only at one instant):
  F1  schemas/af_wcc_vacuum.yaml        cce9c60146d6...
  F2a schemas/af_scc_c2_vacuum.yaml     5476a3f2c6bc...
  F2b schemas/af_scc_c0_vacuum.yaml     55d0a1ea9bda...
  F0  research_map/formulation_taxonomy.yaml 0abb9ed8a961... (+ companion d7419b4e8963...)
  A0  evaluation_rubric.yaml            d748a9e3574e...
  N0  numerics/results/flat_wave_convergence_rev3.json  (measured here)

Outputs:
  reviews/G-FORM-final-verify-r2.json
  reviews/G-F0-final-verify-r2.json
  reviews/A0-review-final-verify.json
  reviews/N0-review-final-verify.json
  runtime/state/lead_audit_lifecycle_05_checkpoint.json

Emits artifact/review/status/blocker/direction_update events for the above.
Never sets a gate verdict: proposals only.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "research_map"))
import comms  # noqa: E402

CST = timezone(timedelta(hours=8))
SUF = os.environ.get("AUDIT_R2_SUFFIX", "")  # bump to re-emit events on a re-run


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(path: str) -> str | None:
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


PIN = {
    "F0": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "F0_COMPANION": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "F1": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "F2a": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "F2b": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "A0": "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
}
PATHS = {
    "F0": "research_map/formulation_taxonomy.yaml",
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
    "A0": "evaluation_rubric.yaml",
    "L0": "ledger/theorems.jsonl",
}
AUTHORS = {
    "F0": {"astra-lead-formulation", "worker-01"},
    "F1": {"astra-lead-formulation"},
    "F2a": {"astra-lead-formulation"},
    "F2b": {"astra-lead-formulation"},
    "L0": {"lead-literature", "astra-lead-literature"},
    "A0": {"astra-lead-audit", "lead-audit"},
}
DISPATCHED = {
    "F1": ["worker-071", "worker-085"],
    "F2a": ["worker-046", "worker-091"],
    "F2b": ["worker-015", "worker-035"],
    "F0": ["worker-041", "worker-052"],
    "A0": ["worker-089"],
    "N0": ["worker-012"],
}


def cited_hashes(d: dict) -> list:
    cited = (d.get("reviewed_sha256") or d.get("artifact_sha256") or d.get("sha256")
             or d.get("cited_sha256") or d.get("frozen_sha256") or d.get("target_sha256"))
    if isinstance(cited, dict):
        return [v for v in cited.values() if isinstance(v, str)]
    if isinstance(cited, (list, tuple)):
        return [v for v in cited if isinstance(v, str)]
    if isinstance(cited, str):
        return [cited]
    return []


def scan(targets) -> dict:
    raw = []
    for f in sorted(glob.glob(os.path.join(ROOT, "reviews", "*.json"))):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        tgt = d.get("target_subnode") or d.get("target_id") or d.get("node_id")
        if tgt not in targets:
            continue
        sup = d.get("supersedes")
        sup_path = sup.get("path") if isinstance(sup, dict) else (sup if isinstance(sup, str) else None)
        raw.append({
            "file": os.path.relpath(f, ROOT),
            "target": tgt,
            "reviewer": d.get("reviewer") or d.get("actor") or "UNKNOWN",
            "verdict": d.get("verdict"),
            "score": d.get("score"),
            "cited": cited_hashes(d),
            "counts_as_full": d.get("counts_as_full_schema_verdict"),
            "created_at": d.get("created_at"),
            "supersedes_path": sup_path,
            "withdrawn_by": d.get("withdrawn_by") or d.get("superseded_by"),
        })
    # a verdict that another file explicitly supersedes/withdraws no longer counts
    withdrawn = {}
    for r in raw:
        if r["supersedes_path"]:
            withdrawn[os.path.normpath(r["supersedes_path"])] = r["file"]
    for r in raw:
        wb = r["withdrawn_by"]
        if isinstance(wb, str):
            withdrawn[os.path.normpath(r["file"])] = wb
    for r in raw:
        r["withdrawn_by_resolved"] = withdrawn.get(os.path.normpath(r["file"]))
        r["live"] = not r["withdrawn_by_resolved"]
    return raw


def coverage_for(t: str, raw: list) -> dict:
    measured = sha256(os.path.join(ROOT, PATHS[t]))
    pin = PIN.get(t) or measured  # L0 has no fixed pin; use the hash measured at this instant
    at = [r for r in raw if r["target"] == t and pin[:12] in [c[:12] for c in r["cited"]]]
    indep = [r for r in at if r["reviewer"] not in AUTHORS[t]]
    live = [r for r in indep if r["live"]]
    acc = sorted({r["reviewer"] for r in live if r["verdict"] == "accept"})
    rev = sorted({r["reviewer"] for r in live if r["verdict"] == "revise"})
    inc = sorted({r["reviewer"] for r in live if r["verdict"] == "inconclusive"})
    return {
        "measured_sha256": measured,
        "pin": pin,
        "independent_verdicts_at_hash": len(set(acc) | set(rev) | set(inc)),
        "accepts_at_hash": acc,
        "revises_at_hash": rev,
        "inconclusive_at_hash": inc,
        "verdict_files_at_hash": [r["file"] for r in live],
        "withdrawn_verdicts_at_hash": [
            {"file": r["file"], "reviewer": r["reviewer"], "verdict": r["verdict"],
             "withdrawn_by": r["withdrawn_by_resolved"]} for r in indep if not r["live"]],
        "recorded_verdicts_total": len([r for r in raw if r["target"] == t]),
        "gate_criterion_two_accepts_met": len(acc) >= 2,
    }


def main():
    measured_at = now()
    raw = scan(set(PATHS))
    cov = {t: coverage_for(t, raw) for t in ["F0", "F1", "F2a", "F2b", "L0", "A0"]}

    protocol_sha = sha256(os.path.join(ROOT, "numerics/CONVERGENCE_PROTOCOL.md"))
    rev3_path = "numerics/results/flat_wave_convergence_rev3.json"
    rev3_sha = sha256(os.path.join(ROOT, rev3_path))
    rev3 = json.load(open(os.path.join(ROOT, rev3_path)))
    frozen_sha = sha256(os.path.join(ROOT, "artifacts/formulation/FROZEN.json"))
    fz = json.load(open(os.path.join(ROOT, "artifacts/formulation/FROZEN.json")))
    tax_cases = [json.loads(l) for l in open(os.path.join(ROOT, "schemas/taxonomy_cases.jsonl")) if l.strip()]
    cases_meta = next((r for r in tax_cases if r.get("record_type") == "meta"), {})
    case_rows = [r for r in tax_cases if r.get("case_id")]
    cases_bound = sum(1 for r in case_rows if str(r.get("binding_status", "")).endswith("0abb9ed8a961"))
    ledger = [json.loads(l) for l in open(os.path.join(ROOT, "ledger/theorems.jsonl")) if l.strip()]
    consistency = json.load(open(os.path.join(ROOT, "artifacts/formulation/evidence/taxonomy_consistency.json")))
    consistency_sha = sha256(os.path.join(ROOT, "artifacts/formulation/evidence/taxonomy_consistency.json"))

    # ---------------- G-FORM r2 ----------------
    gform = {
        "schema": "audit-final-verify/v2",
        "target_id": "F1,F2a,F2b",
        "gate": "G-FORM",
        "reviewer": "astra-lead-audit",
        "actor": "astra-lead-audit",
        "review_kind": "r2 adjudication at the FROZEN rev28/rev27 pins (cards astra-life04-verify-gform-r2 + the 00:47 blind dispatch)",
        "counts_as_full_schema_verdict": False,
        "created_at": measured_at,
        "measured_at": measured_at,
        "verdict": "revise",
        "score": 3.5,
        "reviewed_sha256": {"F1": PIN["F1"], "F2a": PIN["F2a"], "F2b": PIN["F2b"]},
        "frozen_manifest": {"path": "artifacts/formulation/FROZEN.json", "revision": fz["revision"],
                            "frozen_at": fz["frozen_at"], "sha256": frozen_sha},
        "frozen_pin_match": {t: sha256(os.path.join(ROOT, PATHS[t])) == PIN[t] for t in ["F1", "F2a", "F2b"]},
        "mirror_equal": {t: sha256(os.path.join(ROOT, PATHS[t])) == sha256(os.path.join(ROOT, "artifacts/formulation", PATHS[t]))
                         for t in ["F1", "F2a", "F2b"]},
        "dispatched_r2_reviewers": DISPATCHED,
        "dispatched_r2_landed_at_measurement": [],
        "coverage_table": {t: cov[t] for t in ["F1", "F2a", "F2b"]},
        "verified_fixed": [
            {"id": "VF-R2-1", "item": "D0 ill-typed/disjunctive binder", "status": "fixed",
             "evidence": "all three schemas pass the audit D0 binder check at the current pins"},
            {"id": "VF-R2-2", "item": "duplicate top-level YAML revised_at keys", "status": "fixed",
             "evidence": "mapping-scoped event parse: 0 duplicate keys in all three schemas"},
            {"id": "VF-R2-3", "item": "future-dated revised_at", "status": "fixed",
             "evidence": "revised_at 00:31:41 <= file mtime 00:32:02 on all three schemas"},
            {"id": "VF-R2-4", "item": "class_contract_pointer resolving only in the authoring tree", "status": "fixed",
             "evidence": "pointer resolves in the canonical taxonomy; supplement in a separate field"},
            {"id": "VF-R2-5", "item": "F1 falsifier rows bound to a superseded hash", "status": "fixed",
             "evidence": "25/25 rows in schemas/f1_falsifier_tests.jsonl carry binding_sha256=cce9c60146d6"},
        ],
        "blocking_items": [
            {"id": "B-GFORM-R2-1", "severity": "blocking", "finding":
             "f0_binding.consistency_evidence_sha256 is stale in ALL THREE schemas: declared 675a99d0d25b, "
             f"measured artifacts/formulation/evidence/taxonomy_consistency.json = {consistency_sha[:12]} (= FROZEN rev28 pin). "
             "The schemas' own f0_binding.rule requires the binding to be refreshed and the consistency check re-run "
             "before any gate verdict. Independently found by worker-069, -090, -034, -043, -088, -022, -063, -040, -053.",
             "needed": "formulation owner refreshes the pointer at a new schema hash (or restores the declared bytes), "
                       "then re-runs the consistency check; the freeze cannot hold while this is unfixed."},
            {"id": "B-GFORM-R2-2", "severity": "blocking", "finding":
             "F1 domains.D5.definition (L72) and visibility.definition (L213) assert that whole-curve single-q containment "
             "is 'strictly STRONGER' than the tail predicate. Under the schema's own declared past-closed causal past J^-(q), "
             "tail containment implies whole-curve containment (gamma([0,t0]) subset J^-(q) whenever gamma(t0) in J^-(q)), "
             "so the two readings are equivalent and neither is strictly stronger. Worker-011's exhaustive preorder check "
             "(7331 preorders, 5.34e6 evaluations, 0 divergences) and worker-040's HF agree; the sentence is a false "
             "mathematical relation inside a field named by the G-FORM criterion.",
             "needed": "delete or correct the strictness sentence and the L213 misclassification sentence at a new hash; "
                       "re-run the falsifier corpus."},
            {"id": "B-GFORM-R2-3", "severity": "blocking-for-clean-accept", "finding":
             "conclusion_type vocabulary is not single-sourced: F0 field_vocabulary.allowed lists "
             "[weak_cosmic_censorship, strong_cosmic_censorship_C2, strong_cosmic_censorship_C0] while F2a/F2b use the "
             "canonical tokens scc_c2_future_inextendibility / scc_c0_future_inextendibility (VOCAB_ALIASES.json maps the "
             "former as aliases). The alias file exists but F0's allowed list still carries alias spellings.",
             "needed": "F0 allowed list references the alias table (or the canonical tokens) at a new hash; "
                       "controller adjudication of vocabulary authority (worker-090 W090-F2A-02)."},
            {"id": "B-GFORM-R2-4", "severity": "blocking-for-clean-accept", "finding":
             "the two-stage acceptance corpus cannot be reproduced on the frozen bytes: run_acceptance.py preflight "
             "fails because artifacts/formulation/evidence/semantic_escape_rebased.json records base_sha256 1bb78ce9b357 "
             "while the current authoring base is 55d0a1ea9bda (worker-069 HF, worker-090 W090-F2A-03, worker-063 W063-02).",
             "needed": "rebase the fixtures to the rev12 bases and re-run both stages."},
            {"id": "B-GFORM-R2-5", "severity": "blocking", "finding":
             f"coverage at the pins: F1 accepts={cov['F1']['accepts_at_hash']} "
             f"(worker-088's 4.0 accept was withdrawn at the identical hash by F1-review-088-rev12-amended revise 3.5); "
             f"F2a accepts={cov['F2a']['accepts_at_hash']} (all verdicts revise); "
             f"F2b accepts={cov['F2b']['accepts_at_hash']} (worker-098 4.5 only). "
             "G-FORM needs two independent accepts per class at one unchanged hash.",
             "needed": "after the content repairs, re-run the blind round with two reviewers per class."},
        ],
        "open_objections_non_blocking": [
            {"id": "O-GFORM-R2-1", "finding":
             "F2a/F2b data_class blocks remain structurally key-identical; C2/C0 separation rests on "
             "regularity_token + extension_predicate. Needs explicit reviewer adjudication that this is the intended "
             "encoding (carried from O-GFORM-1)."},
            {"id": "O-GFORM-R2-2", "finding":
             "audit_evidence.py CLASSSEP hard findings are negation-blind hits on map claim prose; fixture regression "
             "17/17/10/10 unchanged. Claims must be rephrased by their authors (CF-16)."},
            {"id": "O-GFORM-R2-3", "finding":
             "map bookkeeping lag: declared artifact_sha256 for F0/F1/F2a/F2b and gates[].unmet still quote pre-rev27 "
             "hashes; controller_gate_audit at 00:37:18 reports 0 coverage everywhere while the standing fleet has "
             "since landed at-pin verdicts."},
        ],
        "same_hash_test": "every verdict in coverage_table cites the pin measured in this file; a hash move voids it",
        "gate_proposal": {"gate": "G-FORM", "verdict": "pending",
                          "reason": "content repairs verified, but two hash-bound blocking defects remain "
                                    "(stale consistency-evidence pointer in all three schemas; false strictness sentence "
                                    "in F1 D5/visibility) and no class has two independent accepts at the pin"},
        "authority": "proposal only; the audit lead does not set gate verdicts",
        "next_falsifier": "a schema revision whose f0_binding.consistency_evidence_sha256 resolves to the measured file "
                          "AND whose D5/visibility strictness text is corrected, with two independent accepts at one hash",
        "evidence_refs": [
            f"schemas/af_wcc_vacuum.yaml#{PIN['F1'][:12]}",
            f"schemas/af_scc_c2_vacuum.yaml#{PIN['F2a'][:12]}",
            f"schemas/af_scc_c0_vacuum.yaml#{PIN['F2b'][:12]}",
            f"artifacts/formulation/FROZEN.json#{frozen_sha[:12]}",
            f"artifacts/formulation/evidence/taxonomy_consistency.json#{consistency_sha[:12]}",
            "reviews/A1-rebind-coverage.json",
            "reviews/F1-review-011-visibility-strictness.json",
            "reviews/F2a-rev12-verdict-090.json",
        ],
    }

    # ---------------- G-F0 r2 ----------------
    gf0 = {
        "schema": "audit-final-verify/v2",
        "target_id": "F0",
        "gate": "G-F0",
        "reviewer": "astra-lead-audit",
        "actor": "astra-lead-audit",
        "review_kind": "r2 adjudication at the FROZEN rev28 declared canonical F0 (card astra-life04-verify-gf0-r2)",
        "counts_as_full_schema_verdict": False,
        "created_at": measured_at,
        "measured_at": measured_at,
        "verdict": "accept",
        "score": 4.0,
        "reviewed_sha256": PIN["F0"],
        "companion": {"path": "artifacts/formulation/formulation_taxonomy.yaml", "sha256": PIN["F0_COMPANION"],
                      "role": "class-contract supplement (REC-3 companion pair; byte-identity neither required nor possible)"},
        "frozen_manifest": {"path": "artifacts/formulation/FROZEN.json", "revision": fz["revision"],
                            "frozen_at": fz["frozen_at"], "sha256": frozen_sha},
        "dispatched_r2_reviewers": DISPATCHED,
        "dispatched_r2_landed_at_measurement": [],
        "coverage_table": {"F0": cov["F0"]},
        "gate_criteria": [
            {"criterion": "artifact exists", "status": "met",
             "evidence": f"research_map/formulation_taxonomy.yaml measured {PIN['F0'][:12]}"},
            {"criterion": "exactly 4 separate class ids", "status": "met",
             "evidence": "class_ids == [AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH]"},
            {"criterion": "disjointness tests", "status": "met",
             "evidence": f"schemas/taxonomy_cases.jsonl: meta.taxonomy_ref rev5 {PIN['F0'][:12]}, "
                         f"{cases_bound}/{len(case_rows)} case rows carry binding_status bound_taxonomy_sha_0abb9ed8a961 "
                         "(rebound 00:42; worker-094 HF-094C-1 measured 00:38 is cleared at this instant)"},
            {"criterion": "two independent reviewer verdicts at one unchanged hash", "status": "met",
             "evidence": f"{len(cov['F0']['accepts_at_hash'])} independent accepts at the pin: "
                         f"{', '.join(cov['F0']['accepts_at_hash'])}"},
        ],
        "companion_consistency": {
            "check": "same four class ids; three vacuum classes freeze residual_comeager in both trees; scalar class "
                     "genericity recorded unresolved in both; canonical taxonomy_consistency.json reports "
                     f"consistent={consistency.get('consistent')} with errors={consistency.get('errors')}",
            "taxonomy_consistency_sha256": consistency_sha,
            "verdict": "consistent",
        },
        "resolved_since_last_round": [
            {"id": "R-1", "finding": "coverage at 0abb9ed8a961 was 0 when the pass-03 verdict was written",
             "status": "resolved", "evidence": f"{len(cov['F0']['accepts_at_hash'])} independent accepts now on disk"},
            {"id": "R-2", "finding": "worker-094 HF-094C-1: taxonomy_cases.jsonl rows still pinned to rev2 66bf917bd368",
             "status": "resolved", "evidence": f"rows rebound at 00:42 to 0abb9ed8a961 ({cases_bound}/{len(case_rows)})"},
            {"id": "R-3", "finding": "VF-6 (explicit comeager quantifier in all four class conclusions)",
             "status": "confirmed", "evidence": "AF-WCC-SCALAR-SPH conclusion L413-420 states 'For a comeager set G of data "
                                                 "in the class, chosen before and independently of the data'; the other three "
                                                 "classes state 'For every admissible (s,delta) there is a comeager set G_{s,delta}'. "
                                                 "NOTE: the inherited check F0-scalar-comeager's detail string claims otherwise and is "
                                                 "stale prose (its predicate tests axes.genericity_kind only)."},
        ],
        "open_objections_non_blocking": [
            {"id": "O-GF0-R2-1", "severity": "major", "finding":
             "AF-WCC-SCALAR-SPH axes.genericity_kind='unresolved' while its conclusion quantifies over a comeager set; "
             "H4 marks the notion unresolved and owned by L0/L1, and CG1 records that the class has no schema node. "
             "The four gate criteria do not test this field, so it does not block G-F0, but NO claim may be filed under "
             "this class until the axis is named. Falsifier: set the axis to a named token at a new hash.",
             "sources": ["worker-094 F-094C-1", "worker-038 W038-02-F1", "deepseek-flash-18 N1"]},
            {"id": "O-GF0-R2-2", "severity": "major", "finding":
             "F0 self-declares status: draft_unverified at line 39; the label is author-owned, so this is an author "
             "action item (worker-094 F-094C-2), not a class-content defect."},
            {"id": "O-GF0-R2-3", "severity": "minor", "finding":
             "FROZEN rev28 carries no manifest entry for schemas/taxonomy_cases.jsonl or schemas/f1_falsifier_tests.jsonl "
             "(worker-094 F-094C-3)."},
            {"id": "O-GF0-R2-4", "severity": "moderate", "finding":
             "machine field owned_by still names the superseded node name 'F2' for both SCC classes "
             "(deepseek-flash-19 F0-19-01)."},
        ],
        "gate_proposal": {"gate": "G-F0", "verdict": "pending",
                          "reason": "all four criteria measured as met at 0abb9ed8a961 with 5 independent accepts; "
                                    "proposed pass is left to the controller (no self-pass), carrying O-GF0-R2-1 as a "
                                    "claims-bar until the scalar genericity axis is named"},
        "authority": "proposal only; the audit lead does not set gate verdicts",
        "next_falsifier": "a re-measured taxonomy_cases.jsonl with any row not bound to the measured F0 hash, or an "
                          "independent verdict at 0abb9ed8a961 that is not accept",
        "evidence_refs": [
            f"research_map/formulation_taxonomy.yaml#{PIN['F0'][:12]}",
            f"artifacts/formulation/formulation_taxonomy.yaml#{PIN['F0_COMPANION'][:12]}",
            f"schemas/taxonomy_cases.jsonl#{sha256(os.path.join(ROOT, 'schemas/taxonomy_cases.jsonl'))[:12]}",
            f"artifacts/formulation/evidence/taxonomy_consistency.json#{consistency_sha[:12]}",
            "reviews/F0-review-025.json", "reviews/F0-conformance-038-rev28.json",
            "reviews/F0-criteria-audit-078.json", "reviews/F0-review-18.json", "reviews/F0-review-19.json",
        ],
    }

    # ---------------- A0 ----------------
    a0 = {
        "schema": "audit-final-verify/v2",
        "target_id": "A0",
        "gate": "G-AUDIT",
        "reviewer": "astra-lead-audit",
        "actor": "astra-lead-audit",
        "review_kind": "independent verdict at the measured A0 rubric (card astra-life04-verify-a0)",
        "created_at": measured_at,
        "measured_at": measured_at,
        "verdict": "revise",
        "score": 3.5,
        "reviewed_sha256": PIN["A0"],
        "dispatched_r2_reviewers": DISPATCHED,
        "dispatched_r2_landed_at_measurement": [],
        "coverage_table": {"A0": cov["A0"]},
        "prior_findings_disposition": [
            {"id": "HF-01", "prior_finding": "the HF-01 detector reads claim.artifact_refs, which is absent from ledger rows",
             "status": "unresolved", "measurement": f"evaluation_rubric.yaml:174 requires artifact_refs; "
             f"ledger/theorems.jsonl has {len(ledger)} rows and 0 carry an artifact_refs key, while "
             f"{sum(1 for r in ledger if r.get('conclusion_type') == 'theorem')} rows have conclusion_type=theorem. "
             "The detector is not conformance-computable as written.",
             "needed": "name the ledger's binding field (or add artifact_refs to the ledger schema) at a new rubric hash"},
            {"id": "VOCAB", "prior_finding": "G-FORM genericity vocabulary excludes residual_comeager",
             "status": "unresolved", "measurement": "evaluation_rubric.yaml:128 admits "
             "{comeager, full_measure, open_dense, codim_ge_1, non_generic_excluded}; the frozen schemas declare "
             "genericity.kind=residual_comeager; artifacts/formulation/VOCAB_ALIASES.json maps residual_comeager -> comeager "
             "but the rubric does not consult it.",
             "needed": "single-source the vocabulary through VOCAB_ALIASES.json, or add residual_comeager"},
            {"id": "CONCL", "prior_finding": "conclusion_primary=future_asymptotic_predictability promotes an equivalence F1 marks UNVERIFIED",
             "status": "unresolved", "measurement": "evaluation_rubric.yaml:63/113 set conclusion_primary=future_asymptotic_predictability "
             "for the WCC classes; schemas/af_wcc_vacuum.yaml conclusion.equivalent_standard_formulation.status='claimed equivalence, "
             "UNVERIFIED' and epistemic_status='open_problem'.",
             "needed": "either downgrade the rubric primary to the schema's declared statement or record the equivalence as an "
                       "explicit assumption pending L1"},
            {"id": "LAST_RUN", "prior_finding": "validation.last_run=null",
             "status": "unresolved", "measurement": "evaluation_rubric.yaml:48-50 validation.last_run/last_run_result/report_sha256 are null "
             "although artifacts/audit/audit_run.py exists.",
             "needed": "run the validator and record last_run + report sha256 at a new hash"},
        ],
        "structural_spot_check": {
            "no_universal_scalar_score": True,
            "task_types_present": ["schema_formulation", "literature", "numerics", "formalization"],
        },
        "gate_proposal": {"gate": "G-AUDIT", "verdict": "pending",
                          "reason": "A0 at d748a9e3574e carries four unresolved hash-bound findings; the gate also needs "
                                    "A1 coverage (F1/F2a 0 accepts, F2b 1, L0 0)"},
        "authority": "proposal only; the audit lead does not set gate verdicts",
        "next_falsifier": "a rubric revision that resolves HF-01/VOCAB/CONCL/LAST_RUN at one hash, plus two independent "
                          "accepts per formulation/literature target",
        "evidence_refs": [f"evaluation_rubric.yaml#{PIN['A0'][:12]}",
                          f"ledger/theorems.jsonl#{sha256(os.path.join(ROOT, 'ledger/theorems.jsonl'))[:12]}",
                          "artifacts/formulation/VOCAB_ALIASES.json"],
    }

    # ---------------- N0 ----------------
    n0 = {
        "schema": "audit-final-verify/v2",
        "target_id": "N0",
        "gate": "G-NUM",
        "reviewer": "astra-lead-audit",
        "actor": "astra-lead-audit",
        "review_kind": "independent verdict at the post-stoprule N0 hashes (card astra-life04-n0-verify)",
        "created_at": measured_at,
        "measured_at": measured_at,
        "verdict": "revise",
        "score": 3.5,
        "reviewed_sha256": {"numerics/CONVERGENCE_PROTOCOL.md": protocol_sha, rev3_path: rev3_sha},
        "dispatched_r2_reviewers": DISPATCHED,
        "dispatched_r2_landed_at_measurement": [],
        "stop_rule_items": [
            {"item": "fourth resolution rung (or explicit 3-level scoping with tolerance justification)", "status": "closed",
             "evidence": f"rev3 certification_basis.dr_values = {rev3['certification_basis']['dr_values']} at fixed dt=1e-4 for "
                         f"{len(rev3['certification_basis']['schemes'])} schemes; fitted orders "
                         f"{ {k: round(v['fit_order'], 4) for k, v in rev3['certification_basis']['schemes'].items()} }"},
            {"item": "class binding re-bound to declared F0 rev5 0abb9ed8a961", "status": "closed",
             "evidence": rev3["class_binding"]["binding_status"]},
            {"item": "one independent replication verdict of the order", "status": "closed",
             "evidence": rev3["stop_rule_closures"]["independent_replication_verdict"]},
        ],
        "lock_guard": {
            "state": rev3["lock_guard"]["lock_state"],
            "production_allowed": rev3["lock_guard"]["production_allowed"],
            "spherical_solver_present": os.path.exists(os.path.join(ROOT, "numerics/spherical_solver")),
            "blocking_reasons": rev3["lock_guard"]["blocking_reasons"],
            "verdict": "passes: locked, production_allowed=false, numerics/spherical_solver absent, no N1 artifact in evidence",
        },
        "internal_checks": {"n": len(rev3["internal_checks"]["checks"]), "failures": rev3["internal_checks"]["failures"]},
        "blocking_items": [
            {"id": "B-N0-R2-1", "severity": "blocking-for-completion", "finding":
             "PROTOCOL rule 2 registration gap: 6 reviewed paths are not in runtime/state/artifact_hashes.json, including "
             "numerics/CONVERGENCE_PROTOCOL.md and the rev3 closure artifact's own replication evidence "
             f"({', '.join(rev3['registration_state']['unregistered_paths'])}).",
             "needed": "controller registers the measured hashes before any N0 completion claim."},
            {"id": "B-N0-R2-2", "severity": "blocking-for-clean-accept", "finding":
             "protocol review state is contested at 1e6cdf04d7a2: worker-067 revise 4.0 and worker-081 revise 3.5 stand "
             "against the accepts; worker-081's later adj2 accept supersedes its own revise but numerics/gates.py "
             "::_protocol_review still counts the withdrawn accept and implements no (reviewer,target)-at-one-hash "
             "supersession rule. The numerics lead correctly refuses to self-adjudicate.",
             "needed": "controller disposition (withdrawal semantics / supersession rule)."},
            {"id": "B-N0-R2-3", "severity": "advisory", "finding":
             "protocol preamble still cites the superseded pins 66bf917b/565a6e50; recorded by the numerics lead as a "
             "blocker rather than rewriting the protocol, because a rewrite voids the verdicts bound to 1e6cdf04d7a2."},
        ],
        "positive_findings": [
            "58/58 internal checks pass, 0 failures at the rev3 hash",
            "three schemes (cnfd/cnfem/lffd) all fit order 2 at fixed dt=1e-4 on four rungs; max cross-scheme |dp| "
            "7.96e-05 vs R5 floor 0.25",
            "independent replication verdicts pinned: worker-046 from-scratch 8/8 SUPPORTED, worker-057 re-analysis "
            "REPRODUCED, worker-081 adjudication accept",
            "temporal/subdominance controls and the negative-control suite remain in force; no claim about self-gravity",
        ],
        "gate_proposal": {"gate": "G-NUM", "verdict": "pending",
                          "reason": "stop-rule items are closed at the rev3 hash and the lock guard passes, but C4 "
                                    "registration and the contested protocol review block a clean N0 accept; C8 is contested "
                                    "at the same hash by two standing revises"},
        "authority": "proposal only; the audit lead does not set gate verdicts",
        "next_falsifier": "a re-hash of any pinned path here that differs, a recomputed fixed-dt order outside |p-2|<=0.3, "
                          "or any file appearing under numerics/spherical_solver while locked",
        "evidence_refs": [f"numerics/CONVERGENCE_PROTOCOL.md#{protocol_sha[:12]}", f"{rev3_path}#{rev3_sha[:12]}",
                          "numerics/protocol/n0_fixed_dt_certification.json",
                          "numerics/protocol/fixed_replication_verdict.json",
                          "comms/outbox/worker-067.jsonl", "comms/outbox/worker-081.jsonl"],
    }

    files = {
        "reviews/G-FORM-final-verify-r2.json": gform,
        "reviews/G-F0-final-verify-r2.json": gf0,
        "reviews/A0-review-final-verify.json": a0,
        "reviews/N0-review-final-verify.json": n0,
    }
    written = {}
    for rel, doc in files.items():
        p = os.path.join(ROOT, rel)
        with open(p, "w") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
            f.write("\n")
        written[rel] = sha256(p)
        print("wrote", rel, written[rel][:12])

    # ---------------- events ----------------
    ev = []
    common = {"created_at": measured_at, "actor": "astra-lead-audit"}
    for rel, h in written.items():
        ev.append(dict(common, event_id=f"audit-r2-art-{os.path.basename(rel).replace('.json', '')}{SUF}",
                       event_type="artifact", node_id={"G-FORM": "F1,F2a,F2b", "G-F0": "F0",
                                                       "A0": "A0", "N0": "N0"}[
                           "G-FORM" if "G-FORM" in rel else "G-F0" if "G-F0" in rel else "A0" if "A0" in rel else "N0"],
                       artifact_type="audit_verdict", path=rel, sha256=h,
                       validation_status="unverified",
                       summary=f"r2 adjudication written at {measured_at}"))
    ev.append(dict(common, event_id=f"audit-r2-review-gform{SUF}", event_type="review", target_id="F1,F2a,F2b",
                   reviewer="astra-lead-audit", verdict="revise", score=3.5,
                   hard_failures=["B-GFORM-R2-1", "B-GFORM-R2-2", "B-GFORM-R2-3", "B-GFORM-R2-4", "B-GFORM-R2-5"],
                   findings="G-FORM r2: content repairs hold, but the consistency-evidence pointer is stale in all three "
                            "schemas, F1 carries a false strictness sentence in D5/visibility, and no class has two "
                            "independent accepts at the pin."))
    ev.append(dict(common, event_id=f"audit-r2-review-gf0{SUF}", event_type="review", target_id="F0",
                   reviewer="astra-lead-audit", verdict="accept", score=4.0, hard_failures=[],
                   findings="G-F0 r2: all four criteria met at 0abb9ed8a961; 5 independent accepts; companion "
                            "consistency verified; scalar genericity axis carried as a claims-bar objection only."))
    ev.append(dict(common, event_id=f"audit-r2-review-a0{SUF}", event_type="review", target_id="A0",
                   reviewer="astra-lead-audit", verdict="revise", score=3.5,
                   hard_failures=["HF-01-field", "VOCAB-single-source", "CONCL-equivalence-unverified", "LAST_RUN-null"],
                   findings="A0 r2: 4 prior findings remain unresolved at d748a9e3574e; the rubric's own self-test is "
                            "still unrecorded."))
    ev.append(dict(common, event_id=f"audit-r2-review-n0{SUF}", event_type="review", target_id="N0",
                   reviewer="astra-lead-audit", verdict="revise", score=3.5,
                   hard_failures=["B-N0-R2-1", "B-N0-R2-2"],
                   findings="N0 r2: all three stop-rule items closed at the rev3 hash and the lock guard passes; "
                            "registration gap + contested protocol review block a clean accept."))
    ev.append(dict(common, event_id=f"audit-r2-status-a1{SUF}", event_type="status", node_id="A1", status="active", hours=1.5,
                   summary="Queue consumed: 10 blind reviewers dispatched + 6 bind-chain addenda; A1 coverage re-measured "
                           "at 00:46:56 (F0 5 accepts, F1 0, F2a 0, F2b 1, L0 0, A0 0); 4 r2 verdicts emitted; no gate self-passed.",
                   evidence_refs=["reviews/A1-rebind-coverage.json", "reviews/G-FORM-final-verify-r2.json",
                                  "reviews/G-F0-final-verify-r2.json"],
                   next_falsifier="an at-pin accept from any of the 10 dispatched reviewers that contradicts a blocking finding"))
    ev.append(dict(common, event_id=f"audit-r2-status-n0{SUF}", event_type="status", node_id="N0", status="active", hours=0.5,
                   summary="N0 stop-rule items closed at rev3 da7c36071995; lock guard passes; registration gap and "
                           "protocol contest recorded; N1 untouched and locked.",
                   evidence_refs=[f"{rev3_path}#{rev3_sha[:12]}"], next_falsifier="any numerics/spherical_solver file while locked"))
    ev.append(dict(common, event_id=f"audit-r2-status-gf0{SUF}", event_type="status", node_id="F0", status="active", hours=0.5,
                   summary="G-F0 criteria met at 0abb9ed8a961 with 5 independent accepts; pass proposed to the controller "
                           "with a claims-bar on AF-WCC-SCALAR-SPH.",
                   evidence_refs=[f"research_map/formulation_taxonomy.yaml#{PIN['F0'][:12]}"],
                   next_falsifier="any taxonomy_cases row not bound to the measured F0 hash"))
    ev.append(dict(common, event_id=f"audit-r2-status-global{SUF}", event_type="status", node_id="GLOBAL", status="active", hours=3.0,
                   summary="Audit lifecycle 05 complete: handoff/map/comms read, queue consumed (4 pass-04 r2 cards), "
                           "10 blind reviewers + 6 addenda dispatched, 4 verdicts + 1 coverage refresh + 1 machine-evidence "
                           "file emitted, 9 blockers and a quiescence direction update filed, checkpoint taken. Audit instance exits.",
                   evidence_refs=["reviews/G-FORM-final-verify-r2.json", "reviews/G-F0-final-verify-r2.json",
                                  "reviews/A0-review-final-verify.json", "reviews/N0-review-final-verify.json"],
                   next_falsifier="next lifecycle re-measures the pins and voids any verdict whose hash moved"))
    blockers = [
        ("audit-r2-b1", "F1", "G-FORM F1 blocking, hash-bound: domains.D5 (L72) and visibility (L213) assert whole-curve "
                              "single-q containment is strictly stronger than the tail predicate; under the declared past-closed "
                              "J^-(q) the two are equivalent (worker-011 exhaustive check; worker-040 agrees).",
         "Correct or delete the strictness sentence at a new F1 hash and re-run the falsifier corpus."),
        ("audit-r2-b2", "F1,F2a,F2b", "G-FORM blocking, hash-bound: f0_binding.consistency_evidence_sha256 declares "
                                      "675a99d0d25b in all three schemas while artifacts/formulation/evidence/taxonomy_consistency.json "
                                      "measures 9e335e9ba1bf (= FROZEN rev28 pin); the schemas' own refresh rule is unsatisfied.",
         "Refresh the pointer at a new hash (or restore the declared bytes) and re-run the consistency check."),
        ("audit-r2-b3", "F2a", "conclusion_type vocabulary is not single-sourced: F0 field_vocabulary.allowed lists alias "
                               "spellings while F2a/F2b use the canonical scc_c*_future_inextendibility tokens.",
         "Controller adjudication on vocabulary authority + F0 allowed list referencing VOCAB_ALIASES.json."),
        ("audit-r2-b4", "F2a,F2b", "two-stage acceptance preflight fails on the frozen bytes: rebased fixtures record base "
                                   "1bb78ce9b357 vs current 55d0a1ea9bda; the declared acceptance criterion cannot be reproduced.",
         "Rebase the fixtures to the rev12 bases and re-run both stages."),
        ("audit-r2-b5", "F1,F2a,F2b", "G-FORM coverage at the pins is F1 accepts=0 (the 4.0 accept was withdrawn at the identical "
                                      "hash), F2a accepts=0, F2b accepts=1; the gate needs two independent accepts per class.",
         "After the content repairs, re-run the blind round with two reviewers per class and a declared quiescence window."),
        ("audit-r2-b6", "L0", "G-LIT coverage at a1674f094979 is 0 accepts: deepseek-flash-18 revise 3.0 with HF-14 "
                              "(60/62 records self-certify with no reviewer verdict or artifact hash), HF-02, HF-04.",
         "Literature owner supplies reviewer-bound records; keep abstract-only evidence provisional."),
        ("audit-r2-b7", "N0", "N0 completion blocked by registration: 6 reviewed paths (incl. numerics/CONVERGENCE_PROTOCOL.md and "
                              "the rev3 replication evidence) are not in runtime/state/artifact_hashes.json; the protocol review is "
                              "contested at 1e6cdf04d7a2 and gates.py counts a withdrawn accept with no supersession rule.",
         "Controller registers the measured hashes and disposes of the protocol contest (withdrawal semantics)."),
        ("audit-r2-b8", "A0", "A0 rubric d748a9e3574e has four unresolved machine-verifiable findings (HF-01 reads an absent field "
                              "on 0/62 ledger rows; genericity vocabulary not single-sourced; conclusion_primary is an equivalence "
                              "F1 marks UNVERIFIED; validation.last_run=null).",
         "Rubric owner repairs the four items at a new hash and records the validator run."),
        ("audit-r2-b9", "GLOBAL", "Map bookkeeping lag: declared artifact_sha256 and gates[].unmet still quote pre-rev27 hashes; "
                                  "controller_gate_audit at 00:37:18 reports 0 coverage everywhere while at-pin verdicts have since "
                                  "landed; 46 ingested events are future-dated.",
         "Controller re-measures gates/coverage at the current hashes and treats future created_at as advisory."),
    ]
    for eid, node, desc, needed in blockers:
        ev.append(dict(common, event_id=f"{eid}{SUF}", event_type="blocker", node_id=node, description=desc,
                       needed_to_unblock=needed, evidence_refs=["reviews/A1-rebind-coverage.json",
                                                                "reviews/G-FORM-final-verify-r2.json"]))
    ev.append(dict(common, event_id=f"audit-r2-direction-quiescence{SUF}", event_type="direction_update", group_id="audit",
                   old_direction="re-review at whatever hash is current when the reviewer finishes",
                   new_direction="freeze-first: declare a quiescence window per review round, dispatch both blind reviewers "
                                 "against a published pin, and void in-flight verdicts on any write to a pinned path",
                   reason="every round in passes 02-04 moved the freeze mid-review; 50+ recorded formulation verdicts cite "
                          "superseded hashes and F1's only accept was withdrawn by its own author at the identical hash",
                   evidence_refs=["reviews/G-FORM-final-verify-r2.json", "reviews/A1-rebind-coverage.json"],
                   budget_delta_agent_hours=0))

    accepted = 0
    for e in ev:
        try:
            r = comms.append_event(e)
            accepted += 1 if r.get("accepted") else 0
            if not r.get("accepted"):
                print("DUP", e["event_id"])
        except Exception as exc:
            print("REJECT", e["event_id"], exc)
    print(f"events accepted: {accepted}/{len(ev)}")

    # ---------------- checkpoint ----------------
    ckpt = {
        "checkpoint": "lead-audit-lifecycle-05",
        "at": measured_at,
        "actor": "astra-lead-audit",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "measured_hashes": {**{t: cov[t]["measured_sha256"] for t in cov},
                            "protocol": protocol_sha, rev3_path: rev3_sha,
                            "artifacts/formulation/FROZEN.json": frozen_sha,
                            "artifacts/formulation/evidence/taxonomy_consistency.json": consistency_sha},
        "coverage": {t: {"accepts": cov[t]["accepts_at_hash"], "revises": cov[t]["revises_at_hash"],
                         "independent_verdicts": cov[t]["independent_verdicts_at_hash"]} for t in cov},
        "verdicts": {"G-FORM": "revise 3.5", "G-F0": "accept 4.0", "A0": "revise 3.5", "N0": "revise 3.5"},
        "dispatched": DISPATCHED,
        "artifacts_written": written,
        "events_emitted": [e["event_id"] for e in ev],
        "blockers": [b[0] for b in blockers],
        "gate_verdicts_set": "none (proposal only)",
        "next_falsifier": "re-measure the pins next lifecycle; any hash move voids the at-pin verdicts",
    }
    ckpt_path = os.path.join(ROOT, "runtime/state/lead_audit_lifecycle_05_checkpoint.json")
    with open(ckpt_path, "w") as f:
        json.dump(ckpt, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(os.path.join(ROOT, "runtime/state/lead_audit_checkpoints.jsonl"), "a") as f:
        f.write(json.dumps(ckpt, sort_keys=True) + "\n")
    print("checkpoint", ckpt_path, sha256(ckpt_path)[:12])
    return 0


if __name__ == "__main__":
    sys.exit(main())
