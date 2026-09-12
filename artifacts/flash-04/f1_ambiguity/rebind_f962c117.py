#!/usr/bin/env python3
"""Worker-04 rebind of the F1 (AF-WCC-VAC-GEN) ambiguity suite.

Prior binding : artifacts/formulation/schemas/af_wcc_vacuum.yaml#sha256:f512af5f4db39b02 (FROZEN rev4)
New binding   : artifacts/formulation/schemas/af_wcc_vacuum.yaml#sha256:f962c117ba11598f (FROZEN rev18)

What this does (no map mutation, no gate verdict, no status promotion):
  1. verifies the on-disk F1 schema hash against FROZEN.json;
  2. re-runs every carried ambiguity probe against the new hash;
  3. classifies the per-test delta vs the f512af5f binding;
  4. adds post-rev4 probes for blocks added after rev4 (known_status, l1_ledger_refs, f0_binding);
  5. rewrites the canonical suite schemas/f1_falsifier_tests.jsonl and a delta report.

Usage: python3 artifacts/flash-04/f1_ambiguity/rebind_f962c117.py
Exit: 0 = all probes pass; 2 = a probe failed (finding, printed); 3 = binding drift.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
SUITE_PATH = ROOT / "schemas/f1_falsifier_tests.jsonl"
FROZEN_PATH = ROOT / "artifacts/formulation/FROZEN.json"
ADJUDICATION_PATH = ROOT / "artifacts/formulation/reviews/ADJUDICATION_flash04_ambiguity.md"
RULE_SPEC_PATH = ROOT / "artifacts/formulation/rule_spec.json"
ALIASES_PATH = ROOT / "artifacts/formulation/VOCAB_ALIASES.json"
PRIOR_SNAPSHOT = ROOT / "artifacts/flash-04/f1_ambiguity/schema_snapshots/af_wcc_vacuum.f512af5f.yaml"
REPORT_PATH = ROOT / "artifacts/flash-04/f1_ambiguity/rebind_f962c117_delta_report.json"

NEW_SHA = "f962c117ba11598f9d5c778cb015809961a371339612b52808c2b9c3446abe96"
PRIOR_SHA = "f512af5f4db39b029fdfe900699d69fa4d9220f75080faf9713006321309381c"
CLASS_ID = "AF-WCC-VAC-GEN"
NODE_ID = "F1"
GATE = "G-FORM"
RUN_ID = "run-2026-09-11T23:15+08:00"
CST = timezone(timedelta(hours=8))


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(path: str, digest: str, chars: int = 16) -> str:
    return f"{path}#sha256:{digest[:chars]}"


def getpath(doc, path: str):
    cur = doc
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def flat(value) -> str:
    return json.dumps(value, default=str, ensure_ascii=False)


def probe(doc, spec: dict) -> dict:
    value = getpath(doc, spec["path"])
    kind = spec["kind"]
    needle = spec.get("value")
    ok = False
    if kind == "path_exists":
        ok = value is not None
    elif kind == "nonnull":
        ok = value is not None
    elif kind == "is_none":
        ok = value is None
    elif kind == "is_true":
        ok = value is True
    elif kind == "equals":
        ok = value == needle
    elif kind == "contains":
        ok = value is not None and needle in flat(value)
    elif kind == "contains_any":
        ok = value is not None and any(n in flat(value) for n in needle)
    elif kind == "length_ge":
        ok = isinstance(value, (list, dict, str)) and len(value) >= needle
    else:  # pragma: no cover
        raise ValueError(f"unknown probe kind {kind!r}")
    return {
        "path": spec["path"],
        "kind": kind,
        "expected": needle if needle is not None else kind,
        "role": spec.get("role", "deciding_field"),
        "pass": bool(ok),
        "observed_excerpt": flat(value)[:280] if value is not None else None,
    }


def carried_probes(test_id: str) -> list[dict]:
    P = {
        "F1-AMB-01": [
            {"path": "non_vacuity.condition", "kind": "contains", "value": "future geodesically incomplete"},
            {"path": "non_vacuity.status", "kind": "contains", "value": "UNVERIFIED"},
            {"path": "unresolved_items", "kind": "contains", "value": "non-vacuity"},
            {"path": "adjudication_queue.open_rows", "kind": "contains", "value": "F1-AMB-01", "role": "corroborating"},
        ],
        "F1-AMB-02": [
            {"path": "genericity.excluded_set", "kind": "contains", "value": "meager"},
            {"path": "genericity.excluded_set", "kind": "contains", "value": "self-similar"},
            {"path": "genericity.excluded_set_status", "kind": "equals", "value": "unresolved"},
            {"path": "unresolved_items", "kind": "contains", "value": "meagerness", "role": "corroborating"},
            {"path": "adjudication_queue.open_rows", "kind": "contains", "value": "F1-AMB-02", "role": "corroborating"},
        ],
        "F1-AMB-03": [
            {"path": "genericity.excluded_set", "kind": "contains", "value": "Killing"},
            {"path": "genericity.excluded_set", "kind": "contains", "value": "finite-dimensional"},
            {"path": "genericity.excluded_set_status", "kind": "equals", "value": "unresolved"},
            {"path": "unresolved_items", "kind": "contains", "value": "meagerness", "role": "corroborating"},
        ],
        "F1-AMB-04": [
            {"path": "data_class.adm_mass.sign", "kind": "contains", "value": "m_ADM >= 0"},
            {"path": "data_class.adm_mass.rigidity", "kind": "contains", "value": "Minkowski"},
            {"path": "data_class.matter", "kind": "equals", "value": "none", "role": "corroborating"},
        ],
        "F1-AMB-05": [
            {"path": "data_class.matter", "kind": "equals", "value": "none"},
            {"path": "data_class.equations", "kind": "contains", "value": "Ric(g) = 0", "role": "corroborating"},
        ],
        "F1-AMB-06": [
            {"path": "class_id", "kind": "equals", "value": CLASS_ID},
            {"path": "data_class.matter", "kind": "equals", "value": "none"},
            {"path": "anti_scope.not_this_class", "kind": "contains", "value": "AF-WCC-SCALAR-SPH", "role": "corroborating"},
        ],
        "F1-AMB-07": [
            {"path": "genericity.membership_ruling", "kind": "contains", "value": "set-level only"},
            {"path": "genericity.membership_ruling", "kind": "contains", "value": "does not decide membership"},
        ],
        "F1-AMB-08": [
            {"path": "topology.slice_topology", "kind": "contains", "value": "diffeomorphic to R^3"},
            {"path": "topology.slice_topology", "kind": "contains", "value": "one asymptotically flat end"},
            {"path": "topology.forbidden", "kind": "contains", "value": "closed or periodic", "role": "corroborating"},
        ],
        "F1-AMB-09": [
            {"path": "genericity.ambient_space_is_data_space", "kind": "is_true"},
            {"path": "genericity.ambient_space", "kind": "contains", "value": "constraint manifold"},
        ],
        "F1-AMB-10": [
            {"path": "genericity.kind", "kind": "equals", "value": "residual_comeager"},
            {"path": "genericity.vocabulary_aliases_ref", "kind": "contains", "value": "VOCAB_ALIASES.json"},
        ],
        "F1-AMB-11": [
            {"path": "visibility.definition", "kind": "contains", "value": "future-inextendible causal geodesic"},
            {"path": "visibility.definition", "kind": "contains", "value": "TAIL"},
            {"path": "visibility.witness_protocol", "kind": "contains", "value": "future-inextendible", "role": "corroborating"},
        ],
        "F1-AMB-12": [
            {"path": "i_plus.completeness_definition", "kind": "contains", "value": "future-complete"},
            {"path": "i_plus.completeness_definition_status", "kind": "contains", "value": "NOT the unverified equivalence"},
            {"path": "i_plus.required_properties", "kind": "contains", "value": "I+ non-empty", "role": "corroborating"},
        ],
        "F1-AMB-13": [
            {"path": "regularity.solution_regularity", "kind": "contains", "value": "unique up to isometry"},
            {"path": "data_class.regularity_class.sobolev_variant.s", "kind": "contains", "value": "s > 5/2", "role": "corroborating"},
            {"path": "regularity.must_not_conflate", "kind": "contains", "value": "MGHD maximality", "role": "corroborating"},
        ],
        "F1-AMB-14": [
            {"path": "data_class.matter", "kind": "equals", "value": "none"},
            {"path": "regularity.extension_solution_concept", "kind": "is_none"},
            {"path": "data_class.equations", "kind": "contains", "value": "Ric(g) = 0", "role": "corroborating"},
        ],
        "F1-AMB-15": [
            {"path": "conclusion.equivalent_standard_formulation.status", "kind": "contains", "value": "UNVERIFIED"},
            {"path": "conclusion.equivalent_standard_formulation.predicate", "kind": "contains", "value": "future asymptotic predictability"},
            {"path": "adjudication_queue.open_rows", "kind": "contains", "value": "F1-AMB-15", "role": "corroborating"},
            {"path": "unresolved_items", "kind": "contains", "value": "future asymptotic predictability", "role": "corroborating"},
        ],
        "F1-AMB-16": [
            {"path": "conclusion.conclusion_type", "kind": "equals", "value": "weak_cosmic_censorship"},
            {"path": "epistemic_status", "kind": "equals", "value": "open_problem"},
            {"path": "conclusion.claim_promotion", "kind": "contains", "value": "auto-rejected", "role": "corroborating"},
        ],
        "F1-AMB-17": [
            {"path": "visibility.definition", "kind": "contains", "value": "TAIL"},
            {"path": "visibility.negation_conclusion", "kind": "contains", "value": "NOT equivalent"},
            {"path": "visibility.observability_note", "kind": "contains", "value": "non-meager", "role": "corroborating"},
        ],
    }
    return P[test_id]


DELTA_NOTES = {
    "genericity.excluded_set": (
        "reworded after rev4 (FROZEN rev6/rev10): the excluded set is now REQUIRED to be meager and the "
        "named families are listed as obligations, not constructions; same deciding field, stronger wording."
    ),
    "visibility.definition": (
        "reworded after rev4 (FROZEN rev6, R1 F02 accepted): visibility is now the TAIL formulation; the false "
        "'i.e. inside B' equivalence was removed; geodesic curve class unchanged."
    ),
}


def new_tests(anchors: dict) -> list[dict]:
    common = dict(
        artifact_version="0.2.0",
        author="deepseek-flash-04",
        class_id=CLASS_ID,
        node_id=NODE_ID,
        gate=GATE,
        run_id=RUN_ID,
        binding_sha256=NEW_SHA,
        binding_ref=anchors["schema_ref"],
        binding_frozen_revision=anchors["frozen_revision"],
        prior_binding_sha256=PRIOR_SHA,
        prior_binding_ref=anchors["prior_schema_ref"],
        artifact_kind="f1_ambiguity_probe",
    )
    rows = []
    rows.append({
        "test_id": "F1-AMB-18",
        "title": "Well-formedness vs conjunct: a generic set containing only future-complete developments",
        "ambiguity_kind": "non_vacuity_wellformedness_vs_conjunct",
        "spacetime_description": (
            "A comeager set G of AF vacuum data whose MGHDs are all future-complete (take a neighbourhood of "
            "Minkowski data in the constraint manifold for which dispersion to a future-complete development is "
            "stable). Every datum in G trivially satisfies 'no visible singularity', but non_vacuity.condition "
            "('G must contain data whose MGHD is future geodesically incomplete') fails for this G."
        ),
        "question": "Does this class construction satisfy F1, or does it make F1 ill-formed rather than false?",
        "does_it_satisfy_f1": "no",
        "satisfies_in_class": "n/a (the class construction fails the schema's well-formedness condition)",
        "satisfies_conclusion": "vacuous",
        "deciding_field": "conclusion.wellformedness_conditions",
        "deciding_field_alternates": ["non_vacuity.condition", "non_vacuity.status"],
        "deciding_field_contract": "conclusion.wellformedness_conditions",
        "deciding_field_status": "decided_explicit_wellformedness_slot",
        "falsifier_strength": "decided",
        "schema_open_expected": False,
        "probe_results": [
            probe(anchors["_schema"], {"path": "conclusion.wellformedness_conditions", "kind": "contains", "value": "NOT a conjunct"}),
            probe(anchors["_schema"], {"path": "non_vacuity.condition", "kind": "path_exists"}),
        ],
        "why": (
            "Read as a conjunct, F1's statement is false for any G containing only complete developments, and the "
            "schema would assert an unproved existence claim as part of the conclusion while epistemic_status is "
            "open_problem. Read as a well-formedness condition, the same construction is ill-formed, not a "
            "counterexample. The explicit slot settles the reading, which is exactly why it must be cited."
        ),
        "falsifier": "A gate-accepted reading in which non_vacuity is a conjunct of statement_formal; then this class falsifies F1 rather than being ill-formed, and the wellformedness slot is wrong.",
        "next_falsifier": "Have a reviewer derive statement_formal with non-vacuity conjoined; a derived formula differing from statement_formal shows the slot is load-bearing.",
        "delta_vs_f512af5f": {
            "status": "new_probe_existing_field",
            "changed_fields": [],
            "notes": "Post-rev4 coverage probe; conclusion.wellformedness_conditions existed at f512af5f and is re-probed.",
        },
    })
    rows.append({
        "test_id": "F1-AMB-19",
        "title": "C^2-extendible development with no visible singularity (WCC/SCC boundary probe)",
        "ambiguity_kind": "wcc_scc_extension_slot_conflation",
        "spacetime_description": (
            "AF vacuum data whose MGHD has complete I+ and no visible singularity from I+, but which admits a C^2 "
            "extension across a Cauchy horizon (mass-inflation-free toy extension); the datum is expected to lie in "
            "a non-generic analytic family."
        ),
        "question": "Is this datum in AF-WCC-VAC-GEN, and is its extendibility a counterexample to the WCC conclusion?",
        "does_it_satisfy_f1": "yes",
        "satisfies_in_class": "yes (contingent on the genericity obligations; extendibility is not part of the WCC conclusion)",
        "satisfies_conclusion": "yes (no visible singularity from I+)",
        "deciding_field": "regularity.extension_regularity",
        "deciding_field_alternates": ["regularity.must_not_conflate", "anti_scope.not_this_class"],
        "deciding_field_contract": "regularity.extension_regularity",
        "deciding_field_status": "decided_null_slot_plus_anti_scope",
        "falsifier_strength": "decided",
        "schema_open_expected": False,
        "probe_results": [
            probe(anchors["_schema"], {"path": "regularity.extension_regularity", "kind": "is_none"}),
            probe(anchors["_schema"], {"path": "regularity.must_not_conflate", "kind": "contains", "value": "WCC constrains visibility, not extendibility"}),
            probe(anchors["_schema"], {"path": "anti_scope.not_this_class", "kind": "contains", "value": "AF-SCC-C2-VAC-GEN", "role": "corroborating"}),
        ],
        "why": (
            "If extension_regularity=null reads as 'extensions forbidden', the datum is excluded by a field the WCC "
            "conclusion does not need; if it reads as 'extension regularity is not this class's conclusion', the "
            "datum is in and is not a counterexample. anti_scope names C2/C0 inextendibility as other classes, so the "
            "two readings land in different classes."
        ),
        "falsifier": "A gate-passing reading that treats extension_regularity=null as a prohibition on extensions; then the datum is excluded from WCC by SCC content.",
        "next_falsifier": "Ask two readers to classify the extended development under the frozen schema; opposite in/out verdicts demonstrate the slot is ambiguous.",
        "delta_vs_f512af5f": {
            "status": "new_probe_existing_field",
            "changed_fields": [],
            "notes": "Post-rev4 coverage probe for the SCC-leakage boundary introduced by the rev6-rev10 anti_scope/extension work.",
        },
    })
    rows.append({
        "test_id": "F1-AMB-20",
        "title": "L1-registered non-generic naked-singularity construction read as a class counterexample",
        "ambiguity_kind": "registered_counterexample_scope",
        "spacetime_description": (
            "The peer-reviewed naked-singularity exterior construction T-208 (self-similar, non-generic) together "
            "with the preprint gluing T-209, presented as an AF vacuum development with a visible incomplete geodesic."
        ),
        "question": "Does the L1-registered construction refute AF-WCC-VAC-GEN, or only the for-all-data strengthening?",
        "does_it_satisfy_f1": "no",
        "satisfies_in_class": "no (outside the generic set; refutes only the for-all-data strengthening)",
        "satisfies_conclusion": "no (visible incomplete geodesic exists), but non-generic",
        "deciding_field": "known_status.counterexample_status",
        "deciding_field_alternates": ["genericity.excluded_set_status", "l1_ledger_refs"],
        "deciding_field_contract": "known_status.counterexample_status",
        "deciding_field_status": "decided_by_L1_ledger_integration",
        "falsifier_strength": "decided_by_new_block",
        "schema_open_expected": False,
        "probe_results": [
            probe(anchors["_schema"], {"path": "known_status.counterexample_status", "kind": "contains", "value": "special/self-similar"}),
            probe(anchors["_schema"], {"path": "known_status.counterexample_status", "kind": "contains", "value": "never the generic class"}),
            probe(anchors["_schema"], {"path": "known_status.non_transfer_warning", "kind": "contains", "value": "T-204"}),
            probe(anchors["_schema"], {"path": "l1_ledger_refs", "kind": "contains", "value": "T-208", "role": "corroborating"}),
            probe(anchors["_schema"], {"path": "genericity.excluded_set_status", "kind": "equals", "value": "unresolved", "role": "corroborating"}),
        ],
        "why": (
            "A reader who takes counterexample_status at face value concludes the class is refuted; the deciding text "
            "says the construction is special/self-similar and refutes only the for-all-data strengthening, while "
            "excluded_set_status stays unresolved. The known_status block did not exist at f512af5f, so scope had to "
            "be inferred from prose before rev10."
        ),
        "falsifier": "A ledger entry showing T-208/T-209 are generic in the declared ambient space; then the construction is a tier-1 counterexample and the class must be revised.",
        "next_falsifier": "L1 resolves the meagerness of the self-similar family in X^{s,delta}_vac(AF); until then this stays an obligation, not a refutation.",
        "delta_vs_f512af5f": {
            "status": "new_probe_new_block",
            "changed_fields": ["known_status"],
            "notes": "known_status added after f512af5f (FROZEN rev10, L1 verified-ledger integration).",
        },
    })
    rows.append({
        "test_id": "F1-AMB-21",
        "title": "Schema-equivalent content under a foreign class id (binding-integrity probe)",
        "ambiguity_kind": "class_id_binding_integrity",
        "spacetime_description": (
            "Any datum admitted by the F1 schema, carried in a record that declares class_id AF-WCC-SCALAR-SPH "
            "(massless scalar, spherical) with identical visibility and conclusion text."
        ),
        "question": "Does the record satisfy F1's class contract when its content is identical but the class id differs?",
        "does_it_satisfy_f1": "no",
        "satisfies_in_class": "no (foreign class id; class contract is hash-pinned, not content-inferred)",
        "satisfies_conclusion": "n/a",
        "deciding_field": "f0_binding.declared_f0_sha256",
        "deciding_field_alternates": ["class_id", "anti_scope.not_this_class"],
        "deciding_field_contract": "f0_binding.declared_f0_sha256",
        "deciding_field_status": "decided_class_id_plus_f0_hash_binding",
        "falsifier_strength": "decided_by_new_block",
        "schema_open_expected": False,
        "probe_results": [
            probe(anchors["_schema"], {"path": "f0_binding.declared_f0_sha256", "kind": "nonnull"}),
            probe(anchors["_schema"], {"path": "f0_binding.rule", "kind": "contains", "value": "must be refreshed"}),
            probe(anchors["_schema"], {"path": "anti_scope.not_this_class", "kind": "contains", "value": "AF-WCC-SCALAR-SPH", "role": "corroborating"}),
            probe(anchors["_schema"], {"path": "class_id", "kind": "equals", "value": CLASS_ID, "role": "corroborating"}),
        ],
        "why": (
            "Content-only checking would accept the foreign-class record. The class contract is pinned by class_id plus "
            "the declared F0 artifact hash, and anti_scope explicitly lists AF-WCC-SCALAR-SPH as not-this-class. The "
            "f0_binding block was added after f512af5f (rev13); before it, the binding to the taxonomy hash was "
            "implicit in prose."
        ),
        "falsifier": "A gate run that accepts the foreign-class record, or an F0 hash change that does not invalidate the binding.",
        "next_falsifier": "Run the gate on a fixture with class_id AF-WCC-SCALAR-SPH and an identical body; acceptance means class binding is not enforced.",
        "delta_vs_f512af5f": {
            "status": "new_probe_new_block",
            "changed_fields": ["f0_binding"],
            "notes": "f0_binding added after f512af5f (FROZEN rev13, flash-17 blocker accepted).",
        },
    })
    rows.append({
        "test_id": "F1-AMB-22",
        "title": "Restricted near-Schwarzschild positive result (T-204) carried beyond its codimension-3 domain",
        "ambiguity_kind": "partial_result_scope_transfer",
        "spacetime_description": (
            "A datum in the codimension-3 near-Schwarzschild restricted family covered by T-204 (rigorous WCC-type "
            "result), presented as evidence that generic AF vacuum data satisfy the conclusion."
        ),
        "question": "Does T-204 raise the class status, and is a T-204 datum a witness for the generic statement?",
        "does_it_satisfy_f1": "ambiguous",
        "satisfies_in_class": "yes for the restricted family; not a generic witness",
        "satisfies_conclusion": "yes on the restricted set only",
        "deciding_field": "l1_ledger_refs",
        "deciding_field_alternates": ["known_status.positive_partial_results", "known_status.non_transfer_warning"],
        "deciding_field_contract": "l1_ledger_refs[*].scope_use",
        "deciding_field_status": "decided_by_l1_ledger_scope_use",
        "falsifier_strength": "decided_by_new_block",
        "schema_open_expected": False,
        "probe_results": [
            probe(anchors["_schema"], {"path": "l1_ledger_refs", "kind": "contains", "value": "codimension-3"}),
            probe(anchors["_schema"], {"path": "known_status.non_transfer_warning", "kind": "contains", "value": "must travel"}),
            probe(anchors["_schema"], {"path": "known_status.positive_partial_results", "kind": "contains", "value": "T-204", "role": "corroborating"}),
            probe(anchors["_schema"], {"path": "known_status.status", "kind": "equals", "value": "open_problem", "role": "corroborating"}),
        ],
        "why": (
            "The ledger's scope_use says T-204 is attainable only on a codimension-3 restricted data set and does not "
            "cover generic data. Without reading scope_use, positive_partial_results reads as partial confirmation of "
            "the generic statement. The same datum is a witness for T-204 and not for AF-WCC-VAC-GEN. l1_ledger_refs "
            "and known_status were added after f512af5f."
        ),
        "falsifier": "A generic-data extension of T-204 in the ledger; then the non-transfer warning is stale and the class status must be upgraded.",
        "next_falsifier": "L1 supplies a locator and scope statement for any result claimed to cover generic AF data; until then, no transfer.",
        "delta_vs_f512af5f": {
            "status": "new_probe_new_block",
            "changed_fields": ["l1_ledger_refs", "known_status"],
            "notes": "l1_ledger_refs/known_status added after f512af5f (FROZEN rev10).",
        },
    })
    for r in rows:
        r.update({k: v for k, v in common.items() if k not in r})
    return rows


def main() -> int:
    schema_sha = sha256_file(SCHEMA_PATH)
    if schema_sha != NEW_SHA:
        print(f"BINDING DRIFT: {SCHEMA_PATH} sha256={schema_sha} expected={NEW_SHA}")
        return 3
    frozen = json.loads(FROZEN_PATH.read_text())
    entry = frozen["files"]["artifacts/formulation/schemas/af_wcc_vacuum.yaml"]
    if entry["sha256"] != NEW_SHA:
        print(f"BINDING DRIFT: FROZEN.json declares {entry['sha256']} expected {NEW_SHA}")
        return 3
    schema = yaml.safe_load(SCHEMA_PATH.read_text())
    prior = yaml.safe_load(PRIOR_SNAPSHOT.read_text()) if PRIOR_SNAPSHOT.exists() else {}

    anchors = {
        "schema_ref": ref("artifacts/formulation/schemas/af_wcc_vacuum.yaml", NEW_SHA),
        "prior_schema_ref": ref("artifacts/formulation/schemas/af_wcc_vacuum.yaml", PRIOR_SHA),
        "frozen_ref": ref("artifacts/formulation/FROZEN.json", sha256_file(FROZEN_PATH)),
        "adjudication_ref": ref("artifacts/formulation/reviews/ADJUDICATION_flash04_ambiguity.md", sha256_file(ADJUDICATION_PATH)),
        "rule_spec_ref": ref("artifacts/formulation/rule_spec.json", sha256_file(RULE_SPEC_PATH)),
        "aliases_ref": ref("artifacts/formulation/VOCAB_ALIASES.json", sha256_file(ALIASES_PATH)),
        "prior_suite_ref": ref("schemas/f1_falsifier_tests.jsonl", sha256_file(SUITE_PATH)),
        "prior_snapshot_ref": ref("artifacts/flash-04/f1_ambiguity/schema_snapshots/af_wcc_vacuum.f512af5f.yaml", sha256_file(PRIOR_SNAPSHOT)),
        "frozen_revision": frozen.get("revision"),
        "_schema": schema,
    }

    old_rows = [json.loads(line) for line in SUITE_PATH.read_text().splitlines() if line.strip()]
    carried = [r for r in old_rows if r["test_id"].startswith("F1-AMB-") and int(r["test_id"].split("-")[-1]) <= 17]
    if len(carried) != 17:
        print(f"expected 17 carried tests, found {len(carried)}")
        return 3

    out, delta_counts, failures = [], {}, []
    for old in sorted(carried, key=lambda r: r["test_id"]):
        rec = dict(old)
        rec["artifact_version"] = "0.2.0"
        rec["prior_binding_sha256"] = PRIOR_SHA
        rec["prior_binding_ref"] = anchors["prior_schema_ref"]
        rec["prior_binding_at_authoring"] = old.get("binding_at_authoring")
        rec["binding_sha256"] = NEW_SHA
        rec["binding_ref"] = anchors["schema_ref"]
        rec["binding_frozen_revision"] = anchors["frozen_revision"]
        rec["binding_at_authoring"] = anchors["schema_ref"]
        rec["schema_under_test"] = "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
        probes = [probe(schema, s) for s in carried_probes(rec["test_id"])]
        rec["probe_results"] = probes
        for p in probes:
            if not p["pass"]:
                failures.append((rec["test_id"], p["path"], p["expected"]))
        dec = rec["deciding_field"]
        old_val, new_val = getpath(prior, dec), getpath(schema, dec)
        changed = flat(old_val) != flat(new_val)
        if changed:
            status = "field_content_changed"
            notes = DELTA_NOTES.get(dec, "deciding-field content differs between f512af5f and f962c117.")
        else:
            status = "unchanged"
            notes = "Deciding field resolves and its content is unchanged between f512af5f and f962c117."
        if rec.get("schema_open_expected"):
            notes += " Obligation retained (adjudication_queue / unresolved_items)."
        rec["delta_vs_f512af5f"] = {
            "status": status,
            "changed_fields": [dec] if changed else [],
            "notes": notes,
        }
        rec["evidence_refs"] = [
            anchors["schema_ref"],
            anchors["frozen_ref"],
            anchors["adjudication_ref"],
            anchors["rule_spec_ref"],
            anchors["aliases_ref"],
            anchors["prior_suite_ref"],
            anchors["prior_snapshot_ref"],
            "research_map/formulation_taxonomy.yaml#sha256:66bf917bd368ebd9",
            "comms/inbox/deepseek-flash-04.jsonl:1-3",
        ]
        rec["falsifier"] = old.get("next_falsifier")
        out.append(rec)
        delta_counts[status] = delta_counts.get(status, 0) + 1

    for rec in new_tests(anchors):
        for p in rec["probe_results"]:
            if not p["pass"]:
                failures.append((rec["test_id"], p["path"], p["expected"]))
        rec["evidence_refs"] = [
            anchors["schema_ref"],
            anchors["frozen_ref"],
            anchors["adjudication_ref"],
            anchors["rule_spec_ref"],
            anchors["aliases_ref"],
            "ledger/theorems.jsonl",
            "comms/inbox/deepseek-flash-04.jsonl:1-3",
        ]
        out.append(rec)
        delta_counts[rec["delta_vs_f512af5f"]["status"]] = delta_counts.get(rec["delta_vs_f512af5f"]["status"], 0) + 1

    out.sort(key=lambda r: r["test_id"])
    SUITE_PATH.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in out))
    suite_sha = sha256_file(SUITE_PATH)

    added_blocks = sorted(set(schema) - set(prior))
    report = {
        "report_id": "w04-f1-rebind-f962c117",
        "created_at": now(),
        "actor": "deepseek-flash-04",
        "role": "bounded worker; no map mutation, no gate verdict, no status promotion",
        "assignment_ref": "comms/inbox/deepseek-flash-04.jsonl:1 (asg-2026-09-11-F1-deepseek-flash-04-13)",
        "class_id": CLASS_ID,
        "node_id": NODE_ID,
        "gate": GATE,
        "action": "re-run the F1 ambiguity suite against the current frozen hash and report deltas only",
        "binding": {
            "path": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
            "sha256": NEW_SHA,
            "frozen_manifest_revision": frozen.get("revision"),
            "schema_internal_revision": schema.get("revision"),
            "revised_at": schema.get("revised_at"),
        },
        "prior_binding": {
            "path": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
            "sha256": PRIOR_SHA,
            "schema_internal_revision": prior.get("revision"),
            "snapshot": "artifacts/flash-04/f1_ambiguity/schema_snapshots/af_wcc_vacuum.f512af5f.yaml",
        },
        "tests_total": len(out),
        "carried": len(carried),
        "new": len(out) - len(carried),
        "delta_counts": delta_counts,
        "field_changes_observed": [
            {
                "field": "genericity.excluded_set",
                "tests": ["F1-AMB-02", "F1-AMB-03"],
                "note": DELTA_NOTES["genericity.excluded_set"],
            },
            {
                "field": "visibility.definition",
                "tests": ["F1-AMB-11", "F1-AMB-17"],
                "note": DELTA_NOTES["visibility.definition"],
            },
        ],
        "added_top_level_blocks": added_blocks,
        "open_obligations_retained": [
            {"test": "F1-AMB-01", "field": "non_vacuity.condition", "status": "accepted open obligation"},
            {"test": "F1-AMB-02", "field": "genericity.excluded_set_status", "status": "unresolved"},
            {"test": "F1-AMB-03", "field": "genericity.excluded_set_status", "status": "unresolved"},
            {"test": "F1-AMB-15", "field": "conclusion.equivalent_standard_formulation.status", "status": "UNVERIFIED"},
        ],
        "probe_failures": [{"test_id": t, "path": p, "expected": e} for t, p, e in failures],
        "suite_path": "schemas/f1_falsifier_tests.jsonl",
        "suite_sha256": suite_sha,
        "suite_records_with_ids_evidence_hash_falsifier": all(
            r.get("test_id") and r.get("evidence_refs") and r.get("binding_sha256") and r.get("falsifier") for r in out
        ),
        "evidence_refs": [
            anchors["schema_ref"], anchors["frozen_ref"], anchors["adjudication_ref"],
            anchors["prior_suite_ref"], anchors["prior_snapshot_ref"],
        ],
        "falsifier": (
            "A carried test whose deciding field fails to resolve in f962c117, or whose carried verdict flips without a "
            "FROZEN.json revision entry documenting the change."
        ),
        "verification_command": "python3 artifacts/flash-04/f1_ambiguity/rebind_f962c117.py",
    }
    REPORT_PATH.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({
        "schema_sha256_ok": True,
        "frozen_revision": frozen.get("revision"),
        "tests_total": report["tests_total"],
        "delta_counts": delta_counts,
        "probe_failures": report["probe_failures"],
        "suite_sha256": suite_sha,
        "report": str(REPORT_PATH.relative_to(ROOT)),
    }, indent=1))
    return 2 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
