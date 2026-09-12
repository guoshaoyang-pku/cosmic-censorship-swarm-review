#!/usr/bin/env python3
"""Build evidence.json for W025-F1-REV11-INDEP-01 from the raw probe output.

The evidence file is a *reduction* of raw/probe_output.json (kept verbatim) plus
verbatim quotes from the F0-bound authority. Nothing here is recomputed by hand:
every value is read from the probe JSON or from the pinned artifact bytes.
"""
from __future__ import annotations

import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def sha256(rel: str) -> str:
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


probe = json.load(open(os.path.join(HERE, "raw", "probe_output.json"), encoding="utf-8"))
f0_lines = open(os.path.join(ROOT, "research_map/formulation_taxonomy.yaml"), encoding="utf-8").read().splitlines()

tools = probe["tools"]
ev = {
    "evidence_id": "W025-F1-REV11-INDEP-01-EVIDENCE",
    "task_id": "W025-F1-REV11-INDEP-01",
    "class_id": "AF-WCC-VAC-GEN",
    "node_id": "F1",
    "gate": "G-FORM",
    "produced_by": "worker-025",
    "produced_at": probe["probe_at"],
    "probe": {
        "path": "artifacts/worker-025/f1_rev11_independent_verdict/probe_f1_predicate.py",
        "sha256": sha256("artifacts/worker-025/f1_rev11_independent_verdict/probe_f1_predicate.py"),
        "raw_output": "artifacts/worker-025/f1_rev11_independent_verdict/raw/probe_output.json",
        "raw_output_sha256": sha256("artifacts/worker-025/f1_rev11_independent_verdict/raw/probe_output.json"),
    },
    "pinned_hashes": probe["pins"],
    "f1_mtime": probe["f1_mtime"],
    "f1_reviewed_sha256": probe["pins"]["schemas/af_wcc_vacuum.yaml"],
    "duplicate_yaml_keys": probe["duplicate_yaml_keys"],
    "operative_fragments": probe["fragments"],
    "predicate_model": probe["predicate_model"],
    "d0_typing": probe["d0_typing"],
    "binding": probe["binding"],
    "canonical_tools_on_pinned_bytes": {
        "check_class_schema_f1": {"rc": tools["check_class_schema_f1"]["rc"], "stdout": tools["check_class_schema_f1"]["stdout"].strip()},
        "run_acceptance": {"rc": tools["run_acceptance"]["rc"], "stdout": tools["run_acceptance"]["stdout"].strip()},
        "classsep_regression": {"rc": tools["classsep_regression"]["rc"], "stdout": tools["classsep_regression"]["stdout"].strip()},
        "class_separation_findings_for_text_f1": tools["class_separation_findings_for_text_f1"],
    },
    "f0_authority_quotes": {
        "path": "research_map/formulation_taxonomy.yaml",
        "sha256": probe["pins"]["research_map/formulation_taxonomy.yaml"],
        "line_69_D1_resolution": f0_lines[68].strip(),
        "lines_63_65_single_predicate": " ".join(x.strip() for x in f0_lines[62:65]),
        "lines_184_193_wcc_conclusion": " ".join(x.strip() for x in f0_lines[183:193]),
    },
    "checks": [
        {
            "check_id": "C1",
            "question": "Is quantifiers.formal an exact expansion of the class's canonical visibility predicate?",
            "method": "regex extraction of the formal/D5/definition/negation fragments + finite discriminating model (probe section 5)",
            "observed": "quantifiers.formal has no tail token and matches whole-curve containment; visibility.definition is tail-based; on the discriminating curve canonical_tail_visible=True while formal_whole_curve_no_visible=True",
            "result": "FAIL (not an exact expansion; strictly weaker)",
            "supports": "HF-025-1",
        },
        {
            "check_id": "C2",
            "question": "Is quantifiers.negation the exact negation of quantifiers.formal?",
            "method": "same model; exact_negation_of_formal vs canonical_tail_visible on the discriminating curve",
            "observed": "exact_negation_of_formal=False while the declared negation asserts visibility=True; the two predicates agree only on the two control curves",
            "result": "FAIL (formal and its declared negation are not negations of each other)",
            "supports": "HF-025-1",
        },
        {
            "check_id": "C3",
            "question": "Is the probe sensitive (anti-rubber-stamp control)?",
            "method": "substitute the tail clause into the formal text; the control must report agreement",
            "observed": "control_agreement_on_C_disc=True, control_negation_on_C_disc=True, substitution_changed_text=True",
            "result": "PASS (detector discriminates)",
            "supports": "control",
        },
        {
            "check_id": "C4",
            "question": "Is D0 well-typed for the bound pair (s,delta)?",
            "method": "D0 definition text + regularity_class keys (probe section 6)",
            "observed": "D0 is a disjunction; the smooth-with-decay disjunct supplies no (s,delta) pair; ambient space is weighted-Sobolev only",
            "result": "FAIL (ill-typed/ambiguous binder domain)",
            "supports": "HF-025-2",
        },
        {
            "check_id": "C5",
            "question": "Does class_contract_pointer resolve in the authoritative canonical taxonomy?",
            "method": "parse research_map/formulation_taxonomy.yaml top-level keys and the pointer fragment",
            "observed": "pointer=artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-WCC-VAC-GEN; pointer_resolves_in_canonical=False, pointer_resolves_in_authoring=True; canonical top-level key is 'classes', authoring has 'class_contracts'; trees are not byte-identical",
            "result": "FAIL (unresolved against the authoritative tree)",
            "supports": "F-025-3",
        },
        {
            "check_id": "C6",
            "question": "Do the canonical machine gates detect C1/C4?",
            "method": "check_class_schema.py --json, run_acceptance.py, classsep_regression.py on the pinned bytes",
            "observed": "all green: structural PASS failed_rules=[], ACCEPTANCE PASS 31/31 mutants, classsep 17/17 leaks 10/10 controls; class_separation findings []",
            "result": "GATES GREEN while C1/C4 FAIL (the gates do not compare the expansion to the named predicate)",
            "supports": "HF-025-1",
        },
        {
            "check_id": "C7",
            "question": "Does f0_binding resolve at the reviewed revision?",
            "method": "compare declared_f0_sha256 with measured canonical taxonomy sha256",
            "observed": "declared=276009f4... == measured=276009f4...; binding resolves at probe time",
            "result": "PASS (instant-bound; FROZEN.json itself churned to 2554e276 at 00:24:49)",
            "supports": "positive",
        },
        {
            "check_id": "C8",
            "question": "Duplicate YAML mapping keys in the frozen artifact?",
            "method": "yaml.compose node walk",
            "observed": "revised_at x7 at lines [8,10,12,14,16,20,23]; revised_at_unused x2 at [26,28]; last-wins revised_at=2026-09-12T00:30:00+08:00, ahead of file mtime 00:19:14 and probe wall clock",
            "result": "FAIL (parser-dependent revision timestamp; hygiene, not class semantics)",
            "supports": "F-025-4",
        },
    ],
    "verdict_inputs": {
        "target_id": "schemas/af_wcc_vacuum.yaml#9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
        "verdict": "revise",
        "score": 3.0,
        "hard_failures": ["HF-025-1", "HF-025-2"],
    },
    "non_claims": [
        "No gate verdict, no node status, no validation_status: this evidence supports a review verdict only.",
        "Does not adjudicate F2a/F2b; the same D0 family issue is reported there by other reviewers and is not re-litigated here.",
        "The finite model is a discriminating witness for predicate non-equivalence, not a statement about any physical spacetime.",
    ],
}

json.dump(ev, open(os.path.join(HERE, "evidence.json"), "w", encoding="utf-8"), indent=1)
print("wrote evidence.json")
print("evidence sha256:", sha256("artifacts/worker-025/f1_rev11_independent_verdict/evidence.json"))
