#!/usr/bin/env python3
"""Write A1 review verdicts into the canonical reviews/ directory.

Each review matches the map's review-event fields (target_id, reviewer, verdict, score,
hard_failures, findings) and carries the reviewed artifact's sha256. Verdicts are the
lead-audit's own semantic review; reviewer independence is tracked in reviews/INDEX.md.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REV = ROOT / "reviews"
REV.mkdir(exist_ok=True)
NOW = datetime.now().astimezone().isoformat(timespec="seconds")


def sha(p: str) -> str:
    f = ROOT / p
    if not f.exists():
        return "MISSING"
    return hashlib.sha256(f.read_bytes()).hexdigest()


def write(name: str, obj: dict) -> None:
    obj = {"schema_version": "0.1", "created_at": NOW, "reviewer": "lead-audit", **obj}
    (REV / name).write_text(json.dumps(obj, indent=2, sort_keys=False) + "\n")


# ---------------------------------------------------------------------------------------
# ledger audit (L0)
# ---------------------------------------------------------------------------------------
FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
META_TOKENS = {"DEFINITIONS", "GLOBAL", "ALL"}


def ledger_audit() -> dict:
    theorems = [json.loads(l) for l in (ROOT / "ledger/theorems.jsonl").read_text().splitlines() if l.strip()]
    reg_files = sorted((ROOT / "artifacts/literature").rglob("*.jsonl"))
    registry, unresolved = [], []
    for f in reg_files:
        for l in f.read_text().splitlines():
            if not l.strip():
                continue
            d = json.loads(l)
            if "source_id" in d:
                d["_file"] = str(f.relative_to(ROOT)); registry.append(d)
            elif d.get("kind") == "source":
                d["_file"] = str(f.relative_to(ROOT)); unresolved.append(d)
    known = {d.get("source_id") for d in registry}
    missing_refs, meta_class_tokens = [], []
    for i, t in enumerate(theorems):
        for cid in t.get("class_ids", []) or []:
            if cid not in FROZEN:
                if cid in META_TOKENS:
                    meta_class_tokens.append({"entry": i, "token": cid})
                else:
                    missing_refs.append({"entry": i, "token": cid, "kind": "unknown_class"})
        for sid in t.get("source_ids", []) or []:
            if sid not in known:
                missing_refs.append({"entry": i, "token": sid, "kind": "missing_source"})
    titles = {d["source_id"]: d.get("title", "") for d in registry}
    dup_pairs = []
    ids = list(titles)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = titles[ids[i]].lower(), titles[ids[j]].lower()
            sa, sb = set(a.split()), set(b.split())
            if sa and sb and len(sa & sb) / len(sa | sb) >= 0.8:
                dup_pairs.append({"a": ids[i], "b": ids[j], "title_sim": round(len(sa & sb) / len(sa | sb), 3)})
    statuses = {}
    for d in registry:
        statuses[d.get("status", "?")] = statuses.get(d.get("status", "?"), 0) + 1
    return {
        "theorem_entries": len(theorems),
        "registry_entries": len(registry),
        "unresolved_entries": len(unresolved),
        "status_distribution": statuses,
        "meta_class_tokens": meta_class_tokens,
        "broken_refs": missing_refs,
        "duplicate_title_pairs": dup_pairs,
        "class_scope_metadata_missing": sum(1 for d in registry if "source_meta" not in d),
        "registry_files": [str(f.relative_to(ROOT)) for f in reg_files],
    }


la = ledger_audit()
(ROOT / "artifacts/audit/reports").mkdir(parents=True, exist_ok=True)
(ROOT / "artifacts/audit/reports/ledger_audit.json").write_text(json.dumps(la, indent=2) + "\n")

# ---------------------------------------------------------------------------------------
# reviews
# ---------------------------------------------------------------------------------------
write("F0-review-lead-audit.json", {
    "target_id": "F0",
    "artifact": "research_map/formulation_taxonomy.yaml",
    "artifact_sha256": sha("research_map/formulation_taxonomy.yaml"),
    "verdict": "revise",
    "score": 3.0,
    "gate": "G-F0",
    "class_leakage_check": "pass (four frozen ids, no composite token outside anti-scope notes)",
    "conclusion_inflation_check": "pass (draft_unverified, claims_theorem_status false, reviewer_verdicts empty)",
    "hard_failures": ["HF-02", "HF-06", "HF-04"],
    "findings": [
        "HF-02 CRITICAL semantics: field_vocabulary.regularity_token.meaning_C2 claims that forbidding C2 extensions also forbids C^{1,1} and H^2_loc extensions. This reverses the containment: C2 is a SUBSET of C^{1,1} and (borderline) of H^2_loc, so excluding the C2 class does not exclude them. The correct statement is only that C2-inextendibility forbids C^k for k>=2, C^infinity and analytic extensions. The file is internally inconsistent: hypothesis H4 (line 162) states the correct 'a fortiori any higher regularity' version.",
        "HF-06 MAJOR: genericity_kind is set to 'baire_residual' on the class axes for all three vacuum classes while hypotheses H4 explicitly mark the notion and topology unresolved and owned by F1/F2; a class axis may not carry a provisional value that two classes' identity depends on (rule R07 of artifacts/formulation/rule_spec.json says changing the notion yields a different class).",
        "HF-06 MAJOR: the WCC conclusion asserts 'equivalently' between causal-geodesic completeness in J-(I+) and absence of a visible singularity, and adds 'B = M \\ J-(I+) has non-empty interior whenever the development is future-incomplete'. Neither the equivalence nor the B-interior strengthening is sourced or marked unresolved; B-interior is not part of the standard formulation.",
        "HF-04 MAJOR: disjointness is stated for class descriptors (axes), which is fine, but the file does not say that the underlying data sets may overlap (Schwarzschild vacuum data satisfy both AF-WCC-VAC-GEN and the scalar class with phi=0); a machine checker that interprets disjointness as data-space disjointness will reject valid cases such as F0-N7.",
        "POSITIVE: honest draft status, explicit reconstruction note for the missing F0 artifact, transfer rules T1/X1-X5 with the correct one-way C0=>C2 direction, coverage gap CG1 for AF-WCC-SCALAR-SPH, empty reviewer_verdicts.",
    ],
    "evidence_refs": ["research_map/formulation_taxonomy.yaml#a82f249c lines 45-49, 77, 100-104, 111-116, 342-397"],
    "stop_rule": "revise meaning_C2, mark the genericity axes unresolved, source or delete the equivalence/B-interior clause, and clarify descriptor-level disjointness; then re-review.",
})

write("F1-review-lead-audit.json", {
    "target_id": "F1",
    "artifact": "schemas/af_wcc_vacuum.yaml",
    "artifact_sha256": sha("schemas/af_wcc_vacuum.yaml"),
    "verdict": "revise",
    "score": 3.0,
    "gate": "G-FORM",
    "class_leakage_check": "pass for frozen ids; fail for silent divergence from the F0 conclusion object",
    "conclusion_inflation_check": "pass (conclusion.type open_problem, asserted_conclusion_type_if_proved theorem, no artifact_refs)",
    "hard_failures": ["HF-06", "HF-04"],
    "findings": [
        "HF-06 CRITICAL: revision 2 drops two clauses of the F0 class conclusion without listing the divergence: (a) the 'every future-inextendible causal geodesic contained in J-(I+) is complete' reading is relegated to f0_equivalent_form because a lexical linter flags a token, and (b) the F0 clause 'the black-hole region B has non-empty interior whenever the development is future-incomplete' is absent. f0_consistency claims axes_match=true and hypotheses H1-H5 satisfied while the conclusion text differs; divergences DIV-1/DIV-2 do not cover this.",
        "HF-06 MAJOR: the file records that the formulation was shaped to avoid a linter token ('This form is kept out of statement only because the candidate class-binding linter treats the substring ... as a strong-censorship token'). A gate that changes the formulation is not a gate; the audit rejects any promotion whose basis is a lexical pass.",
        "HF-06 MAJOR internal contradiction: topology.initial_slice_topology asserts Sigma is complete, while unresolved[data_class.topology] asks whether completeness of the slice is assumed.",
        "HF-04 MAJOR: equivalent_forms[0] states 'every future-directed causal curve that reaches I+ is complete to the past'. Completeness to the past is not the WCC condition for curves reaching I+; equivalence_status is correctly unverified, but the phrase should be corrected or removed rather than kept as a candidate form.",
        "HF-04 MAJOR: logical_form places 'not exists p in partial_sing(M) such that p in J^-(I+)' inside the completion existence block, mixing a boundary subset of M with a causal past computed in the conformal completion; the typing must be made explicit.",
        "POSITIVE: epistemic vs class conclusion_type kept in separate keys; forbidden_imports; scope-excluded citations (Cardoso, Luk-Oh, Dafermos-Luk) with reasons; falsifier at schema and class level with the RSR genericity caveat; unresolved list with resolution owners; F0 sha256 pinned.",
    ],
    "evidence_refs": ["schemas/af_wcc_vacuum.yaml#f15ea523 lines 100-104, 111-119, 131, 186-190, 203-208, 242-248, 253-257, 312-339"],
    "stop_rule": "bind the conclusion object field-for-field to F0 (or file the divergence as a direction_update), remove the linter-shaped wording, fix the completeness contradiction and the past/future wording; then re-review.",
})

write("F2a-review-lead-audit.json", {
    "target_id": "F2a",
    "artifact": "schemas/af_scc_c2_vacuum.yaml",
    "artifact_sha256": sha("schemas/af_scc_c2_vacuum.yaml"),
    "verdict": "revise",
    "score": 3.0,
    "gate": "G-FORM",
    "class_leakage_check": "pass for class ids and visibility/WCC exclusion; fail on conclusion_type vocabulary and on matter-coupled content inside genericity",
    "conclusion_inflation_check": "pass (epistemic_status open_problem, claims_completion false)",
    "hard_failures": ["HF-02", "HF-06", "HF-04"],
    "findings": [
        "HF-02 CRITICAL: conclusion_type is 'strong_cosmic_censorship', which is not class-specific and does not match the formulation lead's own rule_spec R11 vocabulary value for this class (scc_c2_future_inextendibility, as the C0 sibling correctly uses scc_c0_future_inextendibility). A merge or a downstream claim keyed on conclusion_type can silently collapse the two SCC classes.",
        "HF-06 CRITICAL: data_class.shared_with_F1 asserts the F1 and F2a data classes are 'intended to be field-for-field identical' and instructs integration to diff them; the diff fails as shipped. F1 proposes (s,delta)=(4,1/2+eps) with a norm on (h-delta,K); F2a uses s>5/2, delta>1/2 with K in H^{s-1}_{delta+1}; F2b uses s>5/2, delta in (1/2,1). Transfer rule T1 requires exact data-class and genericity match, so the only licensed cross-class transfer is currently inapplicable.",
        "HF-02 MAJOR: genericity.topology cites a matter-coupled spherical model (Luk-Oh II, Einstein-Maxwell-scalar) as the model precedent, which violates this document's own import_rule ('content from an external matter model ... never in exact_quantifiers, topology, data_class, genericity, conclusion, falsifier'). The precedent is labelled candidate, but the field-level rule is broken.",
        "HF-04 MINOR: metric_regularity is C2 at top level while the C0 sibling's frozen extension concept is 'none'; the two documents therefore test extension classes with different equation requirements. Each is coherent, but the implication ledger and T1 must state the nesting under BOTH conventions.",
        "POSITIVE: correct nested_classes direction; correct reasoning that requiring field equations makes the forbidden class smaller; known_obstructions split into non-generic (OB-1) and open (OB-2); anti_scope list; unresolved_citations policy that withholds identifiers from unresolved entries.",
    ],
    "evidence_refs": ["schemas/af_scc_c2_vacuum.yaml#21df6f7f lines 9, 71-85, 88-92, 94-101, 188-194, 230-244"],
    "stop_rule": "adopt the rule_spec conclusion vocabulary, freeze one shared data class with F1/F2b, move the matter-coupled precedent out of genericity into neighbouring_class_facts; then re-review.",
})

write("F2b-review-lead-audit.json", {
    "target_id": "F2b",
    "artifact": "schemas/af_scc_c0_vacuum.yaml",
    "artifact_sha256": sha("schemas/af_scc_c0_vacuum.yaml"),
    "verdict": "revise",
    "score": 4.0,
    "gate": "G-FORM",
    "class_leakage_check": "pass (single class id, C0 frozen, WCC content excluded, candidate classes confined to anti_scope)",
    "conclusion_inflation_check": "pass (epistemic_status open_problem, promotion rule stated, no artifact_refs)",
    "hard_failures": ["HF-06", "HF-03"],
    "findings": [
        "HF-06 MAJOR: the quantifier ranges over a disjunctive domain D0 = '(i) smooth-with-decay default, or (ii) s>5/2 and delta in (1/2,1)' and over comeager sets G_{s,delta} that depend on the regularity pair. This makes the artifact a family of class statements rather than one class, and it cannot satisfy T1's exact-match guard against F1/F2a as written.",
        "HF-06 MAJOR (positive direction): this is the only one of the three schemas that fixes the extension class with frozen_equation_concept: none and argues the strength relation explicitly. The C2 sibling adopts the opposite convention (equations required). The two conventions must be reconciled in one integration artifact, because the C0 => C2 entailment is used in the ledger.",
        "HF-03 MAJOR: the two decisive sources (Dafermos-Luk 1710.01722 for the C0 obstruction, Sbierski 1507.00601 for the only positive tool) are recorded as unresolved abstract-only fetches inside this artifact, while the literature ledger marks its own copies verified. The class may not cite them as established until L1 binds the exact definitions and hypotheses, in particular the definition of a C0 extension used by Sbierski.",
        "HF-06 MINOR: implication_ledger marks 'no C0 extension => no H2_loc extension' unresolved. That is the right call: H^2_loc(R^4) is borderline for the C0 embedding (s = n/2), so containment must not be assumed. The F0 taxonomy asserts the opposite for C2; both need one L1-verified lattice for {C0, H2_loc, C1, C2}.",
        "POSITIVE: canonical FORM-RULE-SPEC layout; non_vacuity block with a vacuity falsifier; forbidden_strengthenings and forbidden_weakenings; correct one-way entailment C0 => C2; explicit c0_uniqueness_caveat forbidding import of the C2 geodesic-completeness argument; tier-1/tier-2 falsifiers with the non-meagerness step flagged as non-machine-checkable.",
    ],
    "evidence_refs": ["schemas/af_scc_c0_vacuum.yaml#0150bfdf lines 36-66, 71-94, 132-137, 165-180, 182-191, 238-248, 251-265, 284-311"],
    "stop_rule": "replace the disjunctive D0 with one frozen data class matching F1/F2a, reconcile the extension-equation convention with the C2 sibling, and bind the two decisive citations through L1; then re-review.",
})

write("L0-review-lead-audit.json", {
    "target_id": "L0",
    "artifact": "ledger/theorems.jsonl + artifacts/literature/{registry,batch-01,batch-02,batch-w07,unresolved}.jsonl",
    "artifact_sha256": sha("ledger/theorems.jsonl"),
    "verdict": "revise",
    "score": 3.0,
    "gate": "G-LIT",
    "class_leakage_check": "fail: ledger entries carry the non-frozen token DEFINITIONS in class_ids alongside a frozen class id, and no per-source matter/Lambda/dimension/symmetry scope is recorded, so cross-class use cannot be checked mechanically",
    "conclusion_inflation_check": "pass: entries carry conclusion_type open_problem/conditional and scope_caveats",
    "hard_failures": ["HF-03"],
    "findings": [
        f"HF-03 MAJOR: {la['class_scope_metadata_missing']} of {la['registry_entries']} registry entries lack source_meta (matter_model, cosmological_constant, dimension, symmetry, formulation). Independent spot verification by lead-audit of four load-bearing entries (arXiv:1710.01722, 1912.08478, 2204.09891, 2606.25755) matched titles, authors, years and abstracts exactly, so the metadata that IS present is trustworthy; the missing axis is scope.",
        f"HF-02 MAJOR: {len(la['meta_class_tokens'])} ledger entries attach the non-class token DEFINITIONS in class_ids; a claim-bound consumer must not inherit it as a class.",
        f"HF-03: {len(la['broken_refs'])} source_ids referenced by ledger entries do not resolve in the registry (see artifacts/audit/reports/ledger_audit.json).",
        f"DUPLICATION: {len(la['duplicate_title_pairs'])} near-duplicate title pairs (>=0.8 token Jaccard) across the five ledger files; the five files must be merged into one deduplicated registry or G-LIT fails on duplication alone.",
        "COVERAGE: the ledger currently covers naked-singularity constructions and C0-inextendibility tools well, but has no load-bearing entry for the classes' own positive directions (no Christodoulou 1999 scope entry bound to AF-WCC-SCALAR-SPH, no Luk-Oh I/II bound to AF-SCC-C2-VAC-GEN, no Kerr/Schwarzschild exterior stability entry bound to the vacuum classes).",
        "POSITIVE: honest unresolved.jsonl with reasons and next actions; publication status (published/preprint/thesis) recorded; exclusions recorded on scope grounds rather than silently dropped.",
    ],
    "evidence_refs": ["artifacts/audit/reports/ledger_audit.json", "ledger/theorems.jsonl", "artifacts/literature/registry.jsonl", "artifacts/literature/unresolved.jsonl"],
    "stop_rule": "merge and dedupe the registry, add source_meta scope to every entry, resolve broken refs, remove DEFINITIONS from class_ids, and add positive-direction entries; then re-run G-LIT.",
})

write("G-FORM-tooling-review-lead-audit.json", {
    "target_id": "G-FORM",
    "artifact": "artifacts/{worker-06,flash-11,flash-13,worker-17,worker-05} class-binding gates + fixtures",
    "artifact_sha256": sha("artifacts/audit/reports/checker_agreement.json"),
    "verdict": "reject",
    "score": 2.0,
    "gate": "G-FORM",
    "class_leakage_check": "inconclusive: the checkers disagree on the same documents for format reasons",
    "conclusion_inflation_check": "fail: three gates accept all three canonical schemas, including the conclusion_type defect in F2a and the data-class mismatch across F1/F2a/F2b",
    "hard_failures": ["HF-12"],
    "findings": [
        "On the three canonical schemas, worker-06, flash-11 and worker-17 gates all return PASS, flash-13 returns REJECT (it enforces its own invented layout), and worker-05 errors on all three. A gate that accepts every document and a gate that rejects every document are both uninformative.",
        "On 34 fixtures the four checkers show Kish ESS 4.0 nominally but the disagreement is dominated by artifact-schema shape: no shared schema was ever frozen, so four incompatible layouts exist. Cross-acceptance of declared-good documents is 4/4 only for flash-11's own documents; the canonical schemas are accepted by three and rejected by two.",
        "Fixture corpora are not a gold standard: all four flash-11 'good' fixtures declare conclusion.type=theorem for open problems (HF-01) and quantify over all data while claiming genericity (HF-06). The adjudication is in artifacts/audit/fixture_adjudication.json; there are zero audited-positive fixtures in the fleet.",
        "flash-13's gate documents a known escape (probe_rephrased_leak) and flash-11 documents three escapes; those blind spots are honest but mean a lexical pass is not evidence of class binding.",
        "RECOMMENDATION: freeze one artifact schema from artifacts/formulation/rule_spec.json, re-derive a single gate from R01-R16, retire the other four, and require my semantic A1 review in addition to the mechanical pass.",
    ],
    "evidence_refs": ["artifacts/audit/reports/checker_agreement.json", "artifacts/audit/fixture_adjudication.json", "artifacts/formulation/rule_spec.json"],
    "stop_rule": "one frozen schema + one gate + semantic A1 review; no node may pass G-FORM on a lexical checker alone.",
})

index = [
    "# A1 review queue",
    "",
    f"Generated: {NOW}  |  reviewers assigned: lead-audit (this file set)",
    "",
    "| target | artifact | sha256 (12) | verdict | score | hard failures |",
    "|---|---|---|---:|---:|---|",
]
for f in sorted(REV.glob("*.json")):
    try:
        d = json.loads(f.read_text())
    except ValueError:
        continue
    tid = d.get("target_id") or d.get("node_id") or "?"
    art = d.get("artifact") or d.get("artifact_path") or d.get("target_artifact") or "?"
    sh = str(d.get("artifact_sha256") or d.get("sha256") or "?")[:12]
    verdict = d.get("verdict") or (d.get("review") or {}).get("verdict") or "?"
    score = d.get("score", (d.get("review") or {}).get("score", "?"))
    hf = d.get("hard_failures") or (d.get("review") or {}).get("hard_failures") or []
    index.append(f"| {tid} | `{art}` | `{sh}` | {verdict} | {score} | {', '.join(map(str, hf))} |")
index += [
    "",
    "## Independence and review assignment",
    "",
    "- lead-audit reviews above are semantic (class binding, conclusion direction, evidence scope).",
    "- Reviewers 17/18/19 are assigned to reproduce them independently; assignments are in",
    "  `comms/inbox/deepseek-flash-{17,18,19}.jsonl`. A worker's own artifact may not be",
    "  reviewed by its author.",
    "- Kish ESS is reported for any set of reviews that share a text or a template;",
    "  two reviews that agree because they are the same text count as one.",
    "",
    "## Ledger audit summary",
    "",
    f"- theorem entries: {la['theorem_entries']}; registry entries: {la['registry_entries']}; "
    f"unresolved: {la['unresolved_entries']}",
    f"- status distribution: {la['status_distribution']}",
    f"- broken refs: {len(la['broken_refs'])}; non-class tokens: {len(la['meta_class_tokens'])}; "
    f"duplicate title pairs: {len(la['duplicate_title_pairs'])}; missing scope metadata: "
    f"{la['class_scope_metadata_missing']}",
    "",
    "## Gate status after this review",
    "",
    "| gate | verdict | reason |",
    "|---|---|---|",
    "| G-F0 | fail | F0 revise (C2 containment reversal, provisional axes) |",
    "| G-FORM | fail | F1/F2a/F2b revise; no frozen data class; tooling unreliable |",
    "| G-LIT | fail | ledger scope metadata + dedup + broken refs |",
    "| G-AUDIT | pending | A0 rubric materialized and self-tested; A1 queue open |",
    "| G-NUM | pending | numerics lock respected; N0 calibration not yet reviewed |",
    "",
]
(REV / "INDEX.md").write_text("\n".join(index) + "\n")
print(f"wrote {len(list(REV.glob('*-review-*.json')))} reviews + INDEX.md")
print(json.dumps(la, indent=1)[:1200])
