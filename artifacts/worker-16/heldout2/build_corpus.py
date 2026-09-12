#!/usr/bin/env python3
"""FORM-HELDOUT-08 corpus builder (worker-16).

Builds a SECOND held-out corpus against the FROZEN revision-13 canonical layout.
No gate is run here.  The builder is deterministic: every mutant/control is a
yaml.safe_load of an exactly hash-pinned canonical base with one named mutation
applied, so fixture sha256s are reproducible.

Usage:
  python3 build_corpus.py --fixtures-only   # write mutants/ and controls/ (no manifest)
  python3 build_corpus.py --freeze          # write fixtures AND manifest.json

Design constraints carried from the assignment assign-FORM-HELDOUT-08:
  H1 >=20 mutants, >=10 leak families, >=8 rephrased, built against the frozen
     revision-13 hashes (af_wcc f962c117, af_scc_c2 e9fcefe6, af_scc_c0 bdb23f76,
     rule_spec 40f9bb9e).
  H5 controls: 3 frozen canonical schemas + 2 conforming + 2 negated-phrase.
  H6 prefer leak classes NOT covered by the R26-R31 hardening listed in
     FROZEN.json rev11_delta.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCHEMAS = ROOT / "artifacts" / "formulation" / "schemas"
RULE_SPEC = ROOT / "artifacts" / "formulation" / "rule_spec.json"
# The live canonical paths drifted at 2026-09-12T00:08 (after FROZEN rev19).  The exact
# revision-13 bytes survive in worker-11's snapshot corpus; those are the binding bases.
SNAPSHOT = ROOT / "artifacts" / "flash-11" / "f1_aux_class_binding" / "corpus" / "canonical"

BASES = {
    "W": {
        "path": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
        "snapshot": "artifacts/flash-11/f1_aux_class_binding/corpus/canonical/af_wcc_vacuum.yaml",
        "class_id": "AF-WCC-VAC-GEN",
    },
    "C2": {
        "path": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
        "snapshot": "artifacts/flash-11/f1_aux_class_binding/corpus/canonical/af_scc_c2_vacuum.yaml",
        "class_id": "AF-SCC-C2-VAC-GEN",
    },
    "C0": {
        "path": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
        "snapshot": "artifacts/flash-11/f1_aux_class_binding/corpus/canonical/af_scc_c0_vacuum.yaml",
        "class_id": "AF-SCC-C0-VAC-GEN",
    },
}
# revision-13 / current FROZEN.json hashes for the binding artifacts
FROZEN_REV13 = {
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml":
        "f962c117ba11598f9d5c778cb015809961a371339612b52808c2b9c3446abe96",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml":
        "e9fcefe6e59555ba210d1440e5a0a5d4659cf7e6a859b63b60fda8b4066cbcb0",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml":
        "bdb23f76b89540e82e4a8a3feb12637eb646af54466f624cf6ba2fef5a94bf90",
    "artifacts/formulation/rule_spec.json":
        "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(doc) -> str:
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True,
                          default_flow_style=False, width=4096)


# ----------------------------------------------------------------------------
# mutation functions: each takes the parsed canonical doc and mutates in place
# ----------------------------------------------------------------------------
def _kerr_source(doc):
    for s in doc["provenance"]["sources"]:
        if "Kerr" in str(s.get("concept", "")):
            return s
    raise KeyError("Kerr source not found")


MUTATIONS = {}


def mut(name):
    def deco(fn):
        MUTATIONS[name] = fn
        return fn
    return deco


@mut("m01")
def m01(d):
    d["genericity"]["excluded_set"] = (
        "empty: the comeager set G is all of the data space and no datum is excluded from it; "
        "the known extendible families are reclassified as generic."
    )
    d["genericity"]["excluded_set_status"] = "resolved: nothing is excluded"


@mut("m02")
def m02(d):
    d["genericity"]["excluded_set"] = (
        "empty: the comeager set G is all of the data space and no datum is excluded from it; "
        "the known extendible families are reclassified as generic."
    )
    d["genericity"]["excluded_set_status"] = "resolved: nothing is excluded"


@mut("m03")
def m03(d):
    d["non_vacuity"]["status"] = (
        "the witness family has been constructed and its membership in G is verified here; "
        "non-vacuity is settled at the stated genericity."
    )


@mut("m04")
def m04(d):
    d["data_class"]["adm_mass"]["sign"] = (
        "no sign is assumed; negative-mass data are retained in the ambient space"
    )


@mut("m05")
def m05(d):
    d["data_class"]["adm_mass"]["sign"] = (
        "no sign is assumed; negative-mass data are retained in the ambient space"
    )


@mut("m06")
def m06(d):
    d["regularity"]["data_regularity"] = (
        "smooth-with-decay default, or H^s_delta with s >= 2, delta in (1/2,1)"
    )
    d["data_class"]["regularity_class"]["sobolev_variant"]["s"] = (
        "s >= 2 (the threshold 5/2 is not needed for the argument)"
    )


@mut("m07")
def m07(d):
    d["regularity"]["i_plus_regularity"] = (
        "gtilde extends to I+ with C^0 regularity only; the fixed k >= 3 of earlier drafts "
        "is not assumed"
    )


@mut("m08")
def m08(d):
    d["regularity"]["i_plus_regularity"] = (
        "gtilde extends to I+ with C^0 regularity only; the conformal Einstein equations "
        "need not be solved to any order"
    )


@mut("m09")
def m09(d):
    d["data_class"]["equations"] = "Einstein-Maxwell equations with a source-free Maxwell field"


@mut("m10")
def m10(d):
    d["data_class"]["equations"] = (
        "Einstein equations coupled to a massless scalar field; the matter slot is left at "
        "none for continuity"
    )


@mut("m11")
def m11(d):
    d["topology"]["development_topology"] = (
        "M is a 4-manifold admitting a Cauchy surface; global hyperbolicity is not assumed"
    )


@mut("m12")
def m12(d):
    d["topology"]["end_structure"] = (
        "two asymptotically flat ends (this entry is stale and has not been reconciled with "
        "slice_topology)"
    )


@mut("m13")
def m13(d):
    d["quantifiers"]["negation"] = (
        "there exists one asymptotically flat vacuum datum in X^{s,delta}_vac(AF) whose maximal "
        "development admits a proper future C0 metric extension; the class is refuted by "
        "exhibiting that datum."
    )
    d["quantifiers"]["negation_normal_form"] = (
        "exists D in X^{s,delta}_vac(AF) with a proper future C0 metric extension"
    )


@mut("m14")
def m14(d):
    d["quantifiers"]["negation"] = (
        "there exists one asymptotically flat vacuum datum in X^{s,delta}_vac(AF) whose maximal "
        "development admits a proper future C2 vacuum extension; the class is refuted by "
        "exhibiting that datum."
    )
    d["quantifiers"]["negation_normal_form"] = (
        "exists D in X^{s,delta}_vac(AF) with a proper future C2 vacuum extension"
    )


@mut("m15")
def m15(d):
    formal = d["quantifiers"]["formal"]
    assert "forall (s,delta)" in formal, formal[:120]
    d["quantifiers"]["formal"] = formal.replace("forall (s,delta)", "exists (s,delta)", 1)


@mut("m16")
def m16(d):
    d["implication_ledger"]["extension_class_containment"] = (
        "the extension sets are ordered E_C2 contains E_{C^1,1} contains E_H2loc contains E_C0; "
        "this class sits at the bottom of that chain, so its inexistence statement is the "
        "strongest of the three."
    )


@mut("m17")
def m17(d):
    d["implication_ledger"]["extension_class_containment"] = (
        "the containment chain runs E_C2 contains E_{C^1,1} contains E_H2loc contains E_C0; "
        "the C2 class therefore requires the lowest regularity and its inexistence statement "
        "is the strongest."
    )


@mut("m18")
def m18(d):
    d["conclusion"]["equivalent_rephrasings"].append({
        "phrasing": ("the maximal development is future-inextendible as a twice-differentiable "
                     "Lorentzian manifold"),
        "status": "equivalent by the containment of regularity classes",
    })


@mut("m19")
def m19(d):
    d["conclusion"].pop("known_obstruction", None)


@mut("m20")
def m20(d):
    d["conclusion"]["known_obstruction"] = (
        "no obstruction to the unqualified statement is recorded; the generic quantifier is "
        "retained as a continuity convention rather than a mathematical necessity."
    )


@mut("m21")
def m21(d):
    s = _kerr_source(d)
    s["identifier"] = "arXiv:1710.01722"
    s["status"] = "verified"


@mut("m22")
def m22(d):
    d["conclusion"]["epistemic_status"] = "conditional_theorem"


@mut("m23")
def m23(d):
    d["conclusion"]["epistemic_status"] = "conditional_theorem"


@mut("m24")
def m24(d):
    d["visibility"]["forbidden_falsifier"] = (
        "an incomplete causal geodesic whose endpoint is visible from I+ is also an acceptable "
        "tier-1 falsifier for this class"
    )


@mut("m25")
def m25(d):
    d["i_plus"]["completeness_definition"] = (
        "I+ is complete when every causal curve that reaches it can be continued in the "
        "conformal manifold; future-completeness of the null geodesic generators is not required"
    )


@mut("m26")
def m26(d):
    d["visibility"]["negation_conclusion"] = (
        "the singularity is not visible from I+ for generic data: no future-inextendible "
        "geodesic of the development is seen at future null infinity."
    )


@mut("m27")
def m27(d):
    d["falsifier"].pop("schema_falsifiers", None)


@mut("m28")
def m28(d):
    d["genericity"]["ambient_space"] = (
        "the full weighted Sobolev product H^s_delta x H^{s-1}_{delta+1}, with no "
        "constraint-manifold restriction; comeagerness is computed in the product topology"
    )


@mut("m29")
def m29(d):
    d["quantifiers"]["domains"]["D2"]["definition"] = (
        "asymptotically flat initial data satisfying both constraint equations; the vacuum "
        "condition is not required of the data"
    )


# fixture, family, rephrased, base key, one-sentence mutation description
MUTANT_TABLE = [
    ("m01_excluded_set_erased", "excluded-set-erasure", True, "C0", "m01",
     "genericity.excluded_set is replaced by 'empty, nothing is excluded' and excluded_set_status by 'resolved', so the Kerr obstruction the generic quantifier depends on is erased from the class."),
    ("m02_excluded_set_erased_c2", "excluded-set-erasure", False, "C2", "m02",
     "the C2 class's excluded_set is erased the same way, leaving the generic quantifier with no excluded family."),
    ("m03_vacuity_status_overclaim", "vacuity-status-overclaim", True, "C0", "m03",
     "non_vacuity.status is upgraded from 'membership UNVERIFIED' to 'verified here' while condition and witness_type are untouched."),
    ("m04_adm_mass_sign_erased", "adm-mass-erasure", True, "C0", "m04",
     "data_class.adm_mass.sign drops m_ADM >= 0 and retains negative-mass data in the ambient space, contradicting the positive-mass exclusion."),
    ("m05_adm_mass_sign_erased_c2", "adm-mass-erasure", True, "C2", "m05",
     "the C2 class's adm_mass.sign drops m_ADM >= 0 and retains negative-mass data."),
    ("m06_sobolev_index_lowered", "data-regularity-lowered", True, "C0", "m06",
     "the Sobolev lower bound is lowered from s > 5/2 to s >= 2 in both regularity.data_regularity and regularity_class.sobolev_variant, changing the data class."),
    ("m07_iplus_regularity_lowered", "iplus-regularity-lowered", True, "C0", "m07",
     "regularity.i_plus_regularity drops the frozen k >= 3 to C^0 regularity only, weakening a declared assumption axis."),
    ("m08_iplus_regularity_lowered_wcc", "iplus-regularity-lowered", True, "W", "m08",
     "the WCC class's i_plus_regularity drops the conformal-Einstein regularity requirement to C^0 only."),
    ("m09_equation_axis_smuggle", "equation-axis-smuggle", False, "C0", "m09",
     "data_class.equations becomes Einstein-Maxwell while matter stays none and the conclusion stays a vacuum statement."),
    ("m10_equation_axis_smuggle_wcc", "equation-axis-smuggle", True, "W", "m10",
     "the WCC class's equations become Einstein-scalar-field while the matter slot remains none."),
    ("m11_development_topology_weakened", "development-topology-weakened", True, "C0", "m11",
     "topology.development_topology drops global hyperbolicity of M, which the C0-inextendibility statement depends on."),
    ("m12_end_structure_contradiction", "end-structure-contradiction", False, "C0", "m12",
     "topology.end_structure declares two AF ends while slice_topology still declares exactly one; the two fields contradict each other."),
    ("m13_negation_weakened", "negation-weakened", True, "C0", "m13",
     "quantifiers.negation is weakened to the existence of one extendible datum, the route the class's own tier_1 says is NOT sufficient."),
    ("m14_negation_weakened_c2", "negation-weakened", True, "C2", "m14",
     "the C2 class's negation is weakened to a single extendible datum."),
    ("m15_formal_kind_mismatch", "formal-quantifier-kind-mismatch", True, "C0", "m15",
     "quantifiers.formal changes the leading forall (s,delta) to exists (s,delta) while the ordered binder list still says forall, so formal and ordered contradict."),
    ("m16_containment_reversal", "containment-reversal", True, "C0", "m16",
     "implication_ledger.extension_class_containment is reversed so that E_C2 contains E_C0, inverting which statement is the strongest."),
    ("m17_containment_reversal_c2", "containment-reversal", True, "C2", "m17",
     "the C2 containment chain is reversed so that the C2 class is claimed to require the lowest regularity."),
    ("m18_equivalence_inflation", "equivalence-inflation", True, "C0", "m18",
     "a strictly weaker twice-differentiable (C2-level) statement is appended to conclusion.equivalent_rephrasings as 'equivalent'."),
    ("m19_known_obstruction_omitted", "known-obstruction-omitted", False, "C0", "m19",
     "conclusion.known_obstruction is deleted, so the unqualified statement is presented with no recorded obstruction and the generic quantifier looks gratuitous."),
    ("m20_known_obstruction_omitted_c2", "known-obstruction-omitted", True, "C2", "m20",
     "the C2 known_obstruction is rephrased as 'no obstruction recorded', dropping the Kerr counterexample that forces the generic quantifier."),
    ("m21_source_status_flip", "source-status-flip", True, "C0", "m21",
     "the Kerr provenance source is marked verified with an identifier while the top-level citation_status stays unverified; a per-source verification inflation."),
    ("m22_epistemic_status_inflation", "epistemic-status-inflation", False, "C0", "m22",
     "conclusion.epistemic_status becomes conditional_theorem with no artifact_refs, while claim_promotion still records open_problem."),
    ("m23_epistemic_status_inflation_c2", "epistemic-status-inflation", False, "C2", "m23",
     "the C2 conclusion.epistemic_status becomes conditional_theorem with no artifact_refs."),
    ("m24_falsifier_family_mixup", "falsifier-family-mixup", True, "C0", "m24",
     "visibility.forbidden_falsifier is replaced by text that accepts a visible incomplete geodesic, importing the WCC falsifier into the SCC class."),
    ("m25_wcc_completeness_swap", "completeness-definition-swap", True, "W", "m25",
     "the WCC i_plus.completeness_definition drops future-completeness of null geodesic generators, changing the class's own conclusion predicate."),
    ("m26_wcc_visibility_weakened", "visibility-negation-weakened", True, "W", "m26",
     "the WCC visibility.negation_conclusion drops the J^-(q) tail formulation and states the negation informally."),
    ("m27_schema_falsifiers_erased", "schema-falsifier-erased", False, "C0", "m27",
     "falsifier.schema_falsifiers (class-inflation, wrong-family, smuggled-regularity, weaker-evidence guards) is deleted."),
    ("m28_ambient_space_collapse", "genericity-ambient-space-collapse", True, "C0", "m28",
     "genericity.ambient_space is switched to the unconstrained weighted Sobolev product that the canonical explicitly rejects as meager."),
    ("m29_data_domain_contradiction", "data-domain-contradiction", True, "C0", "m29",
     "quantifiers.domains.D2 drops the vacuum condition, so the ambient data space includes non-vacuum data that data_class.matter/equations exclude."),
]

CONTROL_TABLE = [
    ("ctrl_conforming_c0_polished.yaml", "conforming", "C0", "faithful rephrase of scope_statement and non_vacuity.condition with no axis change"),
    ("ctrl_conforming_c2_polished.yaml", "conforming", "C2", "faithful rephrase of conclusion.statement_natural_language and scope_statement with no axis change"),
    ("ctrl_negated_phrase_c0.yaml", "negated-phrase", "C0", "forbidden sibling-regularity phrases quoted only under must_not_conflate exemptions"),
    ("ctrl_negated_phrase_wcc.yaml", "negated-phrase", "W", "SCC-style inextendibility/C0 phrases quoted only under forbidden/must_not exemptions"),
]


def apply_control(key: str, d):
    if key == "ctrl_conforming_c0_polished.yaml":
        d["scope_statement"] = (
            "This class concerns the future-inextendibility of the maximal globally hyperbolic "
            "development of generic asymptotically flat vacuum data, in the lowest (merely "
            "continuous) metric regularity. It makes no claim about what an observer at future "
            "null infinity sees.\n"
        )
        d["non_vacuity"]["condition"] = (
            "the class is applied only to data whose maximal development has a future boundary "
            "that is not smoothly attachable; geodesic incompleteness of the development is the "
            "non-vacuity marker."
        )
    elif key == "ctrl_conforming_c2_polished.yaml":
        d["scope_statement"] = (
            "The class is about the maximal globally hyperbolic development of generic "
            "asymptotically flat vacuum data and the impossibility of continuing it to the "
            "future by a metric of the frozen (twice continuously differentiable) regularity.\n"
        )
        d["conclusion"]["statement_natural_language"] = (
            "For generic asymptotically flat vacuum initial data the maximal development admits "
            "no proper future extension by a metric that is twice continuously differentiable."
        )
    elif key == "ctrl_negated_phrase_c0.yaml":
        d["regularity"]["must_not_conflate"].append(
            "a twice-differentiable (C2) extension is not this class and must never be cited as "
            "evidence for it"
        )
        d["extension_predicate"]["must_not_conflate"].append(
            "the composite phrase 'C0 or C2' does not denote any regularity token of this class "
            "and is listed here only to be forbidden"
        )
    elif key == "ctrl_negated_phrase_wcc.yaml":
        d["conclusion"]["forbidden_weakenings"].append(
            "do not restate this class as 'the development is future-inextendible as a merely "
            "continuous manifold'; that is a different family and is not this conclusion"
        )
        d["visibility"]["must_not_conflate"].append(
            "a merely continuous metric extension is not what this visibility predicate asserts "
            "and must not be imported here"
        )
    else:  # pragma: no cover
        raise KeyError(key)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures-only", action="store_true")
    ap.add_argument("--freeze", action="store_true")
    a = ap.parse_args()
    if a.fixtures_only == a.freeze:
        ap.error("pass exactly one of --fixtures-only / --freeze")

    # 1. verify the frozen snapshot bytes before using them (live paths may have drifted)
    snap_map = {
        "artifacts/formulation/schemas/af_wcc_vacuum.yaml":
            SNAPSHOT / "af_wcc_vacuum.yaml",
        "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml":
            SNAPSHOT / "af_scc_c2_vacuum.yaml",
        "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml":
            SNAPSHOT / "af_scc_c0_vacuum.yaml",
        "artifacts/formulation/rule_spec.json": RULE_SPEC,
    }
    drift = []
    for rel, want in FROZEN_REV13.items():
        got = sha(snap_map[rel])
        if got != want:
            drift.append({"path": rel, "expected": want, "observed": got})
    if drift:
        print(json.dumps({"error": "frozen snapshot drift; refusing to build", "drift": drift}, indent=2))
        return 3
    live_drift = sorted(rel for rel in FROZEN_REV13
                        if rel.endswith(".yaml") and sha(ROOT / rel) != FROZEN_REV13[rel])
    if live_drift:
        print("WARNING live canonical drift (frozen-byte snapshot used instead): "
              + ", ".join(live_drift))

    bases = {}
    (HERE / "bases").mkdir(parents=True, exist_ok=True)
    for key, meta in BASES.items():
        snap = ROOT / meta["snapshot"]
        p = ROOT / meta["path"]
        snap_hash = sha(snap)
        base_copy = HERE / "bases" / Path(meta["path"]).name
        base_copy.write_bytes(snap.read_bytes())
        bases[key] = {
            "path": str(base_copy.relative_to(ROOT)),
            "live_path": meta["path"],
            "snapshot_source": meta["snapshot"],
            "class_id": meta["class_id"],
            "sha256": sha(base_copy),
            "live_sha256": sha(p),
            "snapshot_sha256": snap_hash,
            "doc": yaml.safe_load(base_copy.read_text()),
        }
        assert bases[key]["sha256"] == snap_hash == FROZEN_REV13[meta["path"]], key

    (HERE / "mutants").mkdir(parents=True, exist_ok=True)
    (HERE / "controls").mkdir(parents=True, exist_ok=True)

    mutants = []
    for fixture, family, rephrased, bkey, mkey, desc in MUTANT_TABLE:
        fixture = fixture if fixture.endswith(".yaml") else fixture + ".yaml"
        import copy
        doc = copy.deepcopy(bases[bkey]["doc"])
        MUTATIONS[mkey](doc)
        text = dump(doc)
        path = HERE / "mutants" / fixture
        path.write_text(text)
        mutants.append({
            "fixture": fixture,
            "family": family,
            "rephrased": rephrased,
            "mutation": desc,
            "mutation_id": mkey,
            "base": bases[bkey]["path"],
            "base_sha256": bases[bkey]["sha256"],
            "class_id": bases[bkey]["class_id"],
            "path": str(path.relative_to(ROOT)),
            "sha256": sha(path),
        })

    controls = []
    for fixture, kind, bkey, desc in CONTROL_TABLE:
        import copy
        doc = copy.deepcopy(bases[bkey]["doc"])
        apply_control(fixture, doc)
        text = dump(doc)
        path = HERE / "controls" / fixture
        path.write_text(text)
        controls.append({
            "fixture": fixture,
            "kind": kind,
            "description": desc,
            "base": bases[bkey]["path"],
            "base_sha256": bases[bkey]["sha256"],
            "class_id": bases[bkey]["class_id"],
            "path": str(path.relative_to(ROOT)),
            "sha256": sha(path),
        })

    families = sorted({m["family"] for m in mutants})
    print(f"wrote {len(mutants)} mutants across {len(families)} families "
          f"({sum(1 for m in mutants if m['rephrased'])} rephrased) and {len(controls)} controls")

    if a.fixtures_only:
        return 0

    manifest = {
        "corpus_id": "FORM-HELDOUT-08",
        "assignment": "assign-FORM-HELDOUT-08-2026-09-11T23:52:35+08:00",
        "task_id": "FORM-HELDOUT-08",
        "worker": "worker-16",
        "actor": "deepseek-flash-16",
        "generated_at": "2026-09-12T00:20:00+08:00",
        "frozen_revision_binding": {
            "note": ("assignment names FROZEN revision 13; revision 18 is current but the four "
                     "binding hashes below are unchanged between rev13 and rev18"),
            "rule_spec_sha256": FROZEN_REV13["artifacts/formulation/rule_spec.json"],
            "schemas": {k: v for k, v in FROZEN_REV13.items() if k.endswith(".yaml")},
        },
        "bases": {k: {"path": v["path"], "sha256": v["sha256"], "class_id": v["class_id"],
                      "snapshot_source": v["snapshot_source"],
                      "live_path": v["live_path"], "live_sha256": v["live_sha256"]}
                  for k, v in bases.items()},
        "live_canonical_drift": {
            "observed_at": "2026-09-12T00:20:00+08:00",
            "note": ("the live canonical schemas af_wcc_vacuum.yaml and af_scc_c0_vacuum.yaml "
                     "were modified at 00:08 (after FROZEN rev19 at 00:04:48) and no longer carry "
                     "the frozen rev13 hashes; the corpus is built from the verified frozen-byte "
                     "snapshot under artifacts/flash-11/.../corpus/canonical so the assignment's "
                     "frozen-hash binding holds. Live-path verdicts are reported only as a drift "
                     "observation and do not enter the corpus validity decision."),
            "live_paths": [v["live_path"] for v in bases.values()],
            "frozen_vs_live_equal": {k: (v["sha256"] == v["live_sha256"]) for k, v in bases.items()},
        },
        "stages": {
            "structural": "artifacts/formulation/tools/check_class_schema.py --json FIXTURE",
            "semantic": "artifacts/worker-06/spec_conformance_audit.py FIXTURE",
        },
        "r26_r31_avoidance": ("R26-R31 cover extensions-subtree content, composite-regularity prose, "
                              "quantifier order, transfer truth tables, C0 curvature hypotheses, "
                              "symmetry consistency and foreign-regularity tokens in assertive paths. "
                              "The families below target other axes: excluded-set/provenance/status "
                              "honesty, assumption-axis drift, formal-vs-ordered inconsistency, "
                              "containment reversal, equivalence inflation, guard erasure."),
        "mutants": mutants,
        "controls": controls,
        "frozen_canonical_controls": [bases[k]["path"] for k in ("W", "C2", "C0")],
        "live_canonical_controls": [bases[k]["live_path"] for k in ("W", "C2", "C0")],
        "families": families,
        "rephrased_count": sum(1 for m in mutants if m["rephrased"]),
        "corpus_definition_note": ("written before any gate run; the runner records this file's "
                                   "sha256 before executing stage A and stage B and never rewrites "
                                   "a fixture after a verdict is observed"),
        "acceptance": {"min_mutants": 20, "min_families": 10, "min_rephrased": 8},
    }
    man_path = HERE / "manifest.json"
    man_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"froze manifest: {man_path.relative_to(ROOT)} sha256={sha(man_path)}")
    ok = (len(mutants) >= 20 and len(families) >= 10
          and manifest["rephrased_count"] >= 8)
    print("H1 acceptance:", "PASS" if ok else "FAIL")
    return 0 if ok else 4


if __name__ == "__main__":
    sys.exit(main())
