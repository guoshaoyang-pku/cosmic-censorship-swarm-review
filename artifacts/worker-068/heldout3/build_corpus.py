#!/usr/bin/env python3
"""W068-FORM-HELDOUT-09 corpus builder.

Builds a held-out class-binding corpus bound to the measured canonical schemas at
FROZEN revision 24 (schemas/af_wcc_vacuum.yaml 68392dd8..., af_scc_c2_vacuum.yaml
4f97273e..., af_scc_c0_vacuum.yaml a2aef5ac...).

The corpus is deliberately built from the CURRENT canonical bytes (unlike
FORM-HELDOUT-08, whose bases were rev13 snapshots) so the measurement is bound to
the revision that G-FORM reviewers are being asked to judge.

Mutation metadata lives in the manifest, never in the fixture: a fixture is a plain
class-schema YAML, so the gates see exactly what they would see in production.

Usage: python3 build_corpus.py
Exit 0 on success, 2 on precondition failure (canonical hash drift).
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent  # ai4math-swarm/
CST = timezone(timedelta(hours=8))

CANON = {
    "W": ROOT / "schemas" / "af_wcc_vacuum.yaml",
    "C2": ROOT / "schemas" / "af_scc_c2_vacuum.yaml",
    "C0": ROOT / "schemas" / "af_scc_c0_vacuum.yaml",
}
CLASS = {
    "W": "AF-WCC-VAC-GEN",
    "C2": "AF-SCC-C2-VAC-GEN",
    "C0": "AF-SCC-C0-VAC-GEN",
}
FROZEN_MANIFEST = ROOT / "artifacts" / "formulation" / "FROZEN.json"
GATE_A = "artifacts/formulation/tools/check_class_schema.py"
GATE_B = "artifacts/worker-06/spec_conformance_audit.py"
RULE_SPEC = "artifacts/formulation/rule_spec.json"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def get_path(doc, path: str):
    cur = doc
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur[part]
    return cur


def set_path(doc, path: str, value) -> None:
    parts = path.split(".")
    cur = doc
    for part in parts[:-1]:
        cur = cur[int(part)] if isinstance(cur, list) else cur[part]
    last = parts[-1]
    if isinstance(cur, list):
        cur[int(last)] = value
    else:
        cur[last] = value


def del_path(doc, path: str) -> None:
    parts = path.split(".")
    cur = doc
    for part in parts[:-1]:
        cur = cur[int(part)] if isinstance(cur, list) else cur[part]
    last = parts[-1]
    if isinstance(cur, list):
        del cur[int(last)]
    else:
        del cur[last]


def apply_ops(doc, ops):
    for op in ops:
        if op[0] == "set":
            set_path(doc, op[1], op[2])
        elif op[0] == "del":
            del_path(doc, op[1])
        else:
            raise ValueError(f"unknown op {op[0]}")


# (fixture, base, family, ops, expected_catchers, leak_claim, expectation)
# expectation: "should_be_caught" or "probe" (outcome genuinely uncertain)
MUTANTS = [
    # ---------------- WCC class boundary ----------------
    ("w01_iplus_role_downgrade", "W", "wcc-iplus-role",
     [("set", "i_plus.role", "assumption"), ("set", "i_plus.in_conclusion", False)],
     ["R09"],
     "I+ role demoted from conclusion to assumption: the schema no longer states the WCC conclusion, so a WCC result cannot bind to it.",
     "should_be_caught"),
    ("w02_visibility_role_downgrade", "W", "wcc-visibility-role",
     [("set", "visibility.role", "assumption"), ("set", "visibility.in_conclusion", False)],
     ["R10"],
     "Visibility predicate demoted out of the conclusion; the defining WCC predicate is no longer asserted.",
     "should_be_caught"),
    ("w03_quantifier_forall_data", "W", "wcc-genericity-quantifier",
     [("set", "quantifiers.formal", "forall (s,delta) in D0: forall D in X^{s,delta}_vac(AF): P_WCC(D)"),
      ("set", "quantifiers.ordered", [{"kind": "forall", "binder": "(s,delta)", "domain": "D0", "domain_id": "D0"},
                                      {"kind": "forall", "binder": "D", "domain": "X^{s,delta}_vac(AF)", "domain_id": "D1"}])],
     ["R03", "R07"],
     "Genericity dropped: the class is strengthened from 'comeager many data' to 'all data', a strictly stronger class.",
     "should_be_caught"),
    ("w04_conclusion_type_scc_c2", "W", "wcc-conclusion-type",
     [("set", "conclusion.conclusion_type", "scc_c2_future_inextendibility")],
     ["R11", "R12"],
     "WCC class carries the C2 SCC conclusion token: cross-family conclusion substitution.",
     "should_be_caught"),
    ("w05_topology_admit_closed_slice", "W", "wcc-topology",
     [("set", "topology.slice_topology", "Sigma is a closed (compact without boundary) oriented 3-manifold"),
      ("set", "topology.forbidden", [])],
     ["R04"],
     "Closed-slice topology admitted and the explicit prohibition removed: asymptotically flat data class broken.",
     "should_be_caught"),
    ("w06_matter_scalar_smuggle", "W", "wcc-matter-axis",
     [("set", "data_class.matter", "real scalar field phi"),
      ("set", "data_class.equations", "Einstein-scalar field equations Ric(g) - 8*pi*T(phi) = 0")],
     ["R05", "R12"],
     "VAC component contradicted by scalar-field matter while class_id still says VAC: matter-axis smuggle.",
     "should_be_caught"),
    ("w07_genericity_not_part_of_class", "W", "wcc-genericity-identity",
     [("set", "genericity.is_part_of_class", False),
      ("set", "genericity.class_change_warning", "genericity is a free parameter; changing the notion does not change the class")],
     ["R07"],
     "Genericity declared a free parameter, changing class identity while class_id stays fixed.",
     "should_be_caught"),
    ("w08_iplus_completeness_erased", "W", "wcc-iplus-completeness",
     [("set", "i_plus.completeness_definition", "")],
     ["R09"],
     "Completeness definition removed while I+ is still the conclusion: predicate undefined.",
     "should_be_caught"),
    ("w09_nonvacuity_erased", "W", "wcc-nonvacuity",
     [("del", "non_vacuity")],
     ["R08"],
     "Whole non-vacuity block removed: class admits a trivially-satisfied reading.",
     "should_be_caught"),
    ("w10_citation_overclaim", "W", "wcc-citation",
     [("set", "provenance.citation_status", "verified"),
      ("set", "provenance.sources", []),
      ("set", "provenance.unresolved_citations", []),
      ("set", "provenance.overclaim_note", "the cited source establishes the class conclusion")],
     ["R15"],
     "Citations marked verified with no source identifiers and an explicit claim that a source proves the class conclusion.",
     "should_be_caught"),

    # ---------------- C2 class boundary ----------------
    ("c2_01_conclusion_type_c0", "C2", "c2-conclusion-type",
     [("set", "conclusion.conclusion_type", "scc_c0_future_inextendibility")],
     ["R11", "R12"],
     "C2 class carries the C0 conclusion token: regularity substitution.",
     "should_be_caught"),
    ("c2_02_extension_regularity_c0", "C2", "c2-regularity",
     [("set", "regularity.extension_regularity", "C0"),
      ("set", "regularity.extension_regularity_exact", "continuous (C0) nondegenerate Lorentzian metric"),
      ("set", "extension_predicate.frozen_regularity", "C0")],
     ["R02", "R06"],
     "C2 class's extension predicate silently lowered to C0, so a C0 result would appear to satisfy the C2 class.",
     "should_be_caught"),
    ("c2_03_visibility_conclusion_inflate", "C2", "c2-visibility",
     [("set", "visibility.role", "conclusion"),
      ("set", "visibility.visible_singularity_is_wcc", False),
      ("set", "visibility.reason", "SCC also concludes a visible singularity")],
     ["R10", "R12"],
     "SCC class imports the WCC visible-singularity predicate as its own conclusion: cross-family conclusion inflation.",
     "should_be_caught"),
    ("c2_04_iplus_completeness_assert", "C2", "c2-iplus",
     [("set", "i_plus.role", "conclusion"),
      ("set", "i_plus.in_conclusion", True),
      ("set", "i_plus.completeness_in_conclusion", True),
      ("set", "i_plus.completeness_definition", "every null geodesic generator of I+ is future-complete")],
     ["R09"],
     "SCC class asserts I+ completeness inside the conclusion, which is WCC content.",
     "should_be_caught"),
    ("c2_05_composite_regularity", "C2", "composite-regularity",
     [("set", "class_components.regularity_token", "C2 or C0"),
      ("set", "regularity.extension_regularity", "C0 or C2")],
     ["R13", "R02"],
     "Composite 'C2 or C0' regularity token: the exact merged class the split was created to prevent.",
     "should_be_caught"),
    ("c2_06_converse_transfer_licensed", "C2", "c2-implication-ledger",
     [("set", "implication_ledger.one_way_entailments",
       [{"from": "scc_c2_future_inextendibility", "to": "scc_c0_future_inextendibility", "status": "licensed"}]),
      ("set", "implication_ledger.forbidden_transfers", [])],
     ["R16"],
     "Converse containment licensed (C2-inextendibility entails C0-inextendibility) and the forbidden-transfer list emptied.",
     "should_be_caught"),
    ("c2_07_conclusion_type_theorem", "C2", "conclusion-promotion",
     [("set", "conclusion.conclusion_type", "theorem")],
     ["R11"],
     "Conclusion promoted to theorem with no proof artifact: conclusion inflation.",
     "should_be_caught"),
    ("c2_08_falsifier_wrong_family", "C2", "c2-falsifier",
     [("set", "falsifier.tier_1",
       {"description": "a visible incomplete causal geodesic falsifies the class",
        "witness_type": "visible incomplete causal geodesic",
        "genericity_requirement": "open dense set of data"})],
     ["R14"],
     "SCC tier-1 falsifier replaced by the WCC visible-geodesic witness: the stated falsifier cannot falsify this class.",
     "should_be_caught"),
    ("c2_09_genericity_kind_measure", "C2", "c2-genericity-kind",
     [("set", "genericity.kind", "measure_one")],
     ["R07"],
     "Genericity kind moved out of vocabulary ('measure_one'), changing the class identity while class_id stays fixed.",
     "should_be_caught"),
    ("c2_10_transfer_failures_emptied", "C2", "c2-genericity-transfer",
     [("set", "genericity.transfer_failures", [])],
     ["R07"],
     "Transfer-failure ledger emptied: results from stronger genericity notions would silently transfer.",
     "should_be_caught"),

    # ---------------- C0 class boundary ----------------
    ("c0_01_conclusion_type_c2", "C0", "c0-conclusion-type",
     [("set", "conclusion.conclusion_type", "scc_c2_future_inextendibility")],
     ["R11", "R12"],
     "C0 class carries the C2 conclusion token: the strongest and most error-prone regularity substitution.",
     "should_be_caught"),
    ("c0_02_extension_regularity_c2", "C0", "c0-regularity",
     [("set", "regularity.extension_regularity", "C2"),
      ("set", "regularity.extension_regularity_exact", "twice continuously differentiable"),
      ("set", "regularity.extension_solution_concept", "classical_ricci"),
      ("set", "extension_predicate.frozen_regularity", "C2"),
      ("set", "extension_predicate.frozen_equation_concept", "classical_ricci")],
     ["R02", "R06"],
     "C0 class's extension upgraded to C2 with classical Ricci concept: conclusion inheritance from the sibling.",
     "should_be_caught"),
    ("c0_03_conclusion_negated", "C0", "c0-conclusion-polarity",
     [("set", "conclusion.statement_natural_language",
       "Generic asymptotically flat vacuum initial data admit a maximal development with a proper future C0 metric extension."),
      ("set", "conclusion.statement_formal",
       "forall (s,delta) in D0 exists G_{s,delta} comeager forall D in G_{s,delta}: exists a proper future C0 metric extension of the maximal development")],
     ["R11"],
     "Conclusion polarity inverted (existence of an extension instead of its non-existence) while the C0 token is kept: token checks may not detect a logical negation.",
     "probe"),
    ("c0_04_iplus_completeness_assert", "C0", "c0-iplus",
     [("set", "i_plus.role", "conclusion"),
      ("set", "i_plus.in_conclusion", True),
      ("set", "i_plus.completeness_in_conclusion", True),
      ("set", "i_plus.completeness_definition", "every null geodesic generator of I+ is future-complete")],
     ["R09"],
     "C0 SCC class asserts I+ completeness, which is WCC content.",
     "should_be_caught"),
    ("c0_05_visibility_conclusion_inflate", "C0", "c0-visibility",
     [("set", "visibility.role", "conclusion"),
      ("set", "visibility.visible_singularity_is_wcc", False)],
     ["R10"],
     "C0 SCC class imports the visible-singularity conclusion.",
     "should_be_caught"),
    ("c0_06_nonvacuity_condition_empty", "C0", "c0-nonvacuity",
     [("set", "non_vacuity.condition", "")],
     ["R08"],
     "Non-vacuity condition emptied: schema admits a trivially-satisfied reading.",
     "should_be_caught"),
    ("c0_07_falsifier_tier1_wrong_witness", "C0", "c0-falsifier",
     [("set", "falsifier.tier_1",
       {"description": "a future trapped surface forms (a strengthening, not the class)",
        "witness_type": "future trapped surface"})],
     ["R14"],
     "Tier-1 falsifier witness is not an extension witness, so the stated falsifier cannot refute the class as written.",
     "should_be_caught"),
    ("c0_08_class_id_ch_variant", "C0", "class-token-discipline",
     [("set", "class_id", "AF-SCC-C0-CH-VAC")],
     ["R01"],
     "Non-frozen candidate token in class_id (the exact token flagged CLASSSEP-SOFT on F0/F1); class_ids must stay frozen.",
     "should_be_caught"),
    ("c0_09_citation_overclaim", "C0", "c0-citation",
     [("set", "provenance.citation_status", "verified"),
      ("set", "provenance.sources", []),
      ("set", "provenance.unresolved_citations", []),
      ("set", "provenance.known_status_signals", [{"claim": "the source proves this class"}])],
     ["R15"],
     "Citations marked verified with no identifiers plus a claim that a source proves the class.",
     "should_be_caught"),
    ("c0_10_topology_dim3", "C0", "c0-topology",
     [("set", "topology.spacetime_dimension", 3)],
     ["R04"],
     "Spacetime dimension changed to 3: the 3+1 class frame broken.",
     "should_be_caught"),
    ("c0_11_genericity_not_part_of_class", "C0", "c0-genericity-identity",
     [("set", "genericity.is_part_of_class", False)],
     ["R07"],
     "Genericity declared a free parameter for the C0 class.",
     "should_be_caught"),

    # ---------------- cross-family / composite ----------------
    ("x01_class_id_composite", "W", "class-token-discipline",
     [("set", "class_id", "AF-WCC-VAC-GEN;AF-SCC-C0-VAC-GEN")],
     ["R01", "R02"],
     "Composite WCC/SCC class id in one artifact: the merge that the frozen taxonomy forbids.",
     "should_be_caught"),
    ("x02_class_id_set_variant", "W", "class-token-discipline",
     [("set", "class_id", "AF-WCC-VAC-GEN-SET")],
     ["R01"],
     "Set-based visibility variant promoted to a class id (the CLASSSEP-SOFT token on F0/F1).",
     "should_be_caught"),
    ("x03_wcc_asserts_scc", "W", "cross-family-transfer",
     [("set", "conclusion.statement_formal",
       "forall (s,delta) in D0 exists G_{s,delta} comeager forall D in G_{s,delta}: scc_c0_future_inextendibility holds")],
     ["R12"],
     "WCC conclusion block asserts the SCC conclusion token: forbidden WCC->SCC transfer.",
     "should_be_caught"),
    ("x04_c2_matter_token", "C2", "matter-axis",
     [("set", "data_class.matter", "vacuum plus a test scalar field")],
     ["R05", "R12"],
     "VAC contradicted by a test scalar field in the C2 data class.",
     "should_be_caught"),

    # ---------------- conforming controls (must be accepted) ----------------
    ("ctrl_w_sorted_roundtrip", "W", "control-conforming",
     [], ["NONE"],
     "Conforming control: canonical WCC round-tripped through YAML with keys sorted. A rejection here is a false positive.",
     "must_be_accepted"),
    ("ctrl_c2_antiscope_note", "C2", "control-conforming",
     [("set", "anti_scope.phrases_that_are_not_this_class",
       ["any 'C0 or C2' composite regularity",
        "'inextendible' with no regularity token",
        "the composite phrase 'C0 or C2' is listed here only as an explicitly forbidden composite"])],
     ["NONE"],
     "Conforming control: foreign-family phrase inside the exempt anti_scope field must not be flagged.",
     "must_be_accepted"),
    ("ctrl_c0_variant_registered", "C0", "control-conforming",
     [("set", "class_identity_variants.horizon_localized_variant.why_separate",
       "registered variant of the frozen C0 class; its parent class is the frozen class id and this variant is not a class")],
     ["NONE"],
     "Conforming control: a registered variant annotation (existing exempt key) must not be read as a class-token leak.",
     "must_be_accepted"),
    ("ctrl_w_comment_only", "W", "control-conforming",
     [], ["NONE"],
     "Conforming control: canonical WCC emitted with comments and default flow style.",
     "must_be_accepted"),
]

# known-rejected leaks from FORM-HELDOUT-07 (rebased tree): gate-liveness positive
# controls. These were measured as caught by the structural gate in the HELDOUT-08
# sensitivity check, so acceptance here means the evaluator is dead.
KNOWN_REJECTED = [
    ("h06_genericity_kind_swap.yaml", "genericity-kind-swap", "R21"),
    ("h08_transfer_row_false.yaml", "false-transfer-row", "R28"),
    ("h22_curvature_hypothesis.yaml", "c0-curvature-hypothesis", "R29"),
    ("h14_symmetry_assumed.yaml", "symmetry-contradiction", "R30"),
    ("h19_h2loc_substitution.yaml", "h2loc-substitution", "R18/R31"),
    ("h26_quantifier_order.yaml", "quantifier-order", "R27"),
]

# known-ESCAPE references from FORM-HELDOUT-08: re-checked at the current revision,
# not used for validity. A persistent escape is a replication; a catch is a fix.
KNOWN_ESCAPES = [
    ("m04_adm_mass_sign_erased.yaml", "adm-mass-erasure"),
    ("m16_containment_reversal.yaml", "containment-reversal"),
    ("m25_wcc_completeness_swap.yaml", "completeness-definition-swap"),
    ("m29_data_domain_contradiction.yaml", "data-domain-contradiction"),
]


def main() -> int:
    frozen = json.loads(FROZEN_MANIFEST.read_text())
    frozen_files = frozen.get("files", {})
    # binding is read from the FROZEN manifest at build time; drift (live != FROZEN) refuses the build
    expected_frozen_sha = {}
    for key, p in CANON.items():
        entry = frozen_files.get(str(p.relative_to(ROOT)))
        if not entry or not entry.get("sha256"):
            print(f"FROZEN.json has no entry for {p}", file=sys.stderr)
            return 2
        expected_frozen_sha[key] = entry["sha256"]
    drift = []
    for key, p in CANON.items():
        live = sha256_file(p)
        if live != expected_frozen_sha[key]:
            drift.append(f"{p}: live {live[:12]} != FROZEN rev{frozen.get('revision')} {expected_frozen_sha[key][:12]}")
    if drift:
        print("CANONICAL DRIFT - refusing to build (live bytes are not the FROZEN revision):",
              *drift, sep="\n  ", file=sys.stderr)
        return 2

    for sub in ("bases", "mutants", "controls", "known_leaks", "diag"):
        (HERE / sub).mkdir(parents=True, exist_ok=True)
    # remove stale fixtures so the corpus directory has exactly one revision
    for sub in ("bases", "mutants", "controls", "known_leaks", "diag"):
        for old in (HERE / sub).iterdir():
            if old.is_file():
                old.unlink()

    bases = {}
    for key, p in CANON.items():
        raw = p.read_bytes()
        (HERE / "bases" / p.name).write_bytes(raw)
        bases[key] = yaml.safe_load(raw)

    fixtures = []

    def add(fixture, base_key, family, ops, expected, leak_claim, expectation, origin):
        doc = copy.deepcopy(bases[base_key])
        apply_ops(doc, ops)
        # conforming controls vary only the serialization, mutants use the same dumper
        if fixture == "ctrl_w_comment_only":
            text = "# conforming control: comments added, no semantic change\n" + \
                   yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=1000)
        elif fixture == "ctrl_w_sorted_roundtrip":
            text = yaml.safe_dump(doc, sort_keys=True, allow_unicode=True, width=1000)
        else:
            text = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=1000)
        sub = "mutants" if origin == "worker-068" and expectation != "must_be_accepted" else \
              ("controls" if expectation == "must_be_accepted" else "mutants")
        out = HERE / sub / fixture
        out = out.with_suffix(".yaml")
        out.write_text(text)
        fixtures.append({
            "fixture": str(out.relative_to(ROOT)),
            "file": out.name,
            "base": base_key,
            "class_id": doc.get("class_id"),
            "family": family,
            "mutation_ops": [list(op) for op in ops],
            "expected_catcher_rules": expected,
            "leak_claim": leak_claim,
            "expectation": expectation,
            "origin": origin,
            "sha256": sha256_file(out),
            "bytes": out.stat().st_size,
        })

    for (fixture, base_key, family, ops, expected, leak_claim, expectation) in MUTANTS:
        add(fixture, base_key, family, ops, expected, leak_claim, expectation, "worker-068")

    known_dir = HERE / "known_leaks"
    rejected_dir = ROOT / "artifacts" / "formulation" / "evidence" / "heldout_rebased"
    for name, family, rule in KNOWN_REJECTED:
        src = rejected_dir / name
        if not src.is_file():
            print(f"missing known-rejected fixture {src}", file=sys.stderr)
            return 2
        dst = known_dir / ("rejected_" + name)
        shutil.copyfile(src, dst)
        doc = yaml.safe_load(dst.read_text())
        fixtures.append({
            "fixture": str(dst.relative_to(ROOT)),
            "file": dst.name,
            "base": None,
            "class_id": doc.get("class_id"),
            "family": family,
            "mutation_ops": [],
            "expected_catcher_rules": [rule],
            "leak_claim": "Copied from FORM-HELDOUT-07 (rebased tree); measured as caught by the structural gate in the HELDOUT-08 sensitivity check. Must still be rejected or the evaluator is dead.",
            "expectation": "known_rejected_positive_control",
            "origin": "copied:artifacts/formulation/evidence/heldout_rebased/" + name,
            "sha256": sha256_file(dst),
            "bytes": dst.stat().st_size,
        })

    escape_dir = ROOT / "artifacts" / "worker-16" / "heldout2" / "mutants"
    for name, family in KNOWN_ESCAPES:
        src = escape_dir / name
        if not src.is_file():
            print(f"missing known-escape fixture {src}", file=sys.stderr)
            return 2
        dst = known_dir / ("escape_" + name)
        shutil.copyfile(src, dst)
        doc = yaml.safe_load(dst.read_text())
        fixtures.append({
            "fixture": str(dst.relative_to(ROOT)),
            "file": dst.name,
            "base": None,
            "class_id": doc.get("class_id"),
            "family": family,
            "mutation_ops": [],
            "expected_catcher_rules": ["HELDOUT-08-reported-escape"],
            "leak_claim": "Copied from a FORM-HELDOUT-08 escape family; re-checked at the current revision as a replication reference (not a validity control).",
            "expectation": "known_escape_reference",
            "origin": "copied:artifacts/worker-16/heldout2/mutants/" + name,
            "sha256": sha256_file(dst),
            "bytes": dst.stat().st_size,
        })

    manifest = {
        "corpus_id": "FORM-HELDOUT-09",
        "task_id": "W068-FORM-HELDOUT-09",
        "worker": "worker-068",
        "actor": "worker-068",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "frozen_revision_binding": {
            "frozen_manifest": "artifacts/formulation/FROZEN.json",
            "frozen_manifest_sha256": sha256_file(FROZEN_MANIFEST),
            "revision": frozen.get("revision"),
            "frozen_at": frozen.get("frozen_at"),
            "schemas": {str(p.relative_to(ROOT)): expected_frozen_sha[k] for k, p in CANON.items()},
            "note": "bases are byte copies of the live canonical schemas; the builder refuses to run if live bytes differ from the FROZEN manifest entry at build time.",
        },
        "stages": {
            "structural": GATE_A,
            "structural_sha256": sha256_file(ROOT / GATE_A),
            "semantic": GATE_B,
            "semantic_sha256": sha256_file(ROOT / GATE_B),
            "rule_spec": RULE_SPEC,
            "rule_spec_sha256": sha256_file(ROOT / RULE_SPEC),
        },
        "counts": {
            "total": len(fixtures),
            "leaky": sum(1 for f in fixtures if f["expectation"] in ("should_be_caught", "probe")),
            "probe": sum(1 for f in fixtures if f["expectation"] == "probe"),
            "conforming_controls": sum(1 for f in fixtures if f["expectation"] == "must_be_accepted"),
            "known_rejected_controls": sum(1 for f in fixtures if f["expectation"] == "known_rejected_positive_control"),
            "known_escape_references": sum(1 for f in fixtures if f["expectation"] == "known_escape_reference"),
        },
        "fixtures": fixtures,
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n")
    print(f"built {len(fixtures)} fixtures at {HERE}")
    print(json.dumps(manifest["counts"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
