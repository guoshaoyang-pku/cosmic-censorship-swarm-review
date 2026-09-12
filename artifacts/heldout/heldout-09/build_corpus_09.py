#!/usr/bin/env python3
"""FORM-HELDOUT-09 corpus builder (worker-084).

Builds a FRESH held-out corpus against the FROZEN revision-28 canonical bytes:

  schemas/af_wcc_vacuum.yaml           cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3
  schemas/af_scc_c2_vacuum.yaml        5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce
  schemas/af_scc_c0_vacuum.yaml        55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6
  research_map/formulation_taxonomy.yaml  0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3
  artifacts/formulation/rule_spec.json    40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e
  FROZEN.json (rev 28)                 2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1

No stage is run here.  Every fixture is a yaml.safe_load -> one named mutation -> yaml.safe_dump
of an exactly hash-pinned base, so every fixture sha256 is reproducible and the manifest written
by --freeze is the pre-registration record.

Usage:
  python3 build_corpus_09.py --fixtures-only
  python3 build_corpus_09.py --freeze          # fixtures AND manifest.json (pre-registered)
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FROZEN = ROOT / "artifacts" / "formulation" / "FROZEN.json"
CST = timezone(timedelta(hours=8))

CORPUS_ID = "FORM-HELDOUT-09"
TASK_ID = "FORM-HELDOUT-09"
ASSIGNMENT = "assign-FORM-HELDOUT-09-worker-084"
WORKER = "worker-084"
ACTOR = "worker-084"
DEADLINE = "2026-09-12T02:30:00+08:00"
BUDGET_AGENT_HOURS = 3.0
NODE_ID = "A1"
GATE = "G-CLASSBIND"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
FROZEN_REVISION = 28

PINS = {
    "schemas/af_wcc_vacuum.yaml":
        "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "schemas/af_scc_c2_vacuum.yaml":
        "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "schemas/af_scc_c0_vacuum.yaml":
        "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/rule_spec.json":
        "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
}
FROZEN_MANIFEST_SHA = "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1"
STRUCT_GATE = ROOT / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
SEM_GATE = ROOT / "artifacts" / "worker-06" / "spec_conformance_audit.py"
KEY_MANIFEST = ROOT / "artifacts" / "formulation" / "KEY_MANIFEST.json"

BASES = {
    "W": {"frozen_path": "schemas/af_wcc_vacuum.yaml", "class_id": "AF-WCC-VAC-GEN"},
    "C2": {"frozen_path": "schemas/af_scc_c2_vacuum.yaml", "class_id": "AF-SCC-C2-VAC-GEN"},
    "C0": {"frozen_path": "schemas/af_scc_c0_vacuum.yaml", "class_id": "AF-SCC-C0-VAC-GEN"},
}

FAMILY_RATIONALES = {
    "conclusion-polarity-inversion":
        "Neither stage compares conclusion.statement_formal / statement_natural_language polarity against the frozen class conclusion; R11 checks the conclusion_type token only.",
    "conclusion-content-erasure":
        "Neither stage compares conclusion statement content against the class conclusion, so a statement that no longer asserts future inextendibility still carries the correct token.",
    "natural-language-inversion":
        "Stage A scans statement_natural_language only for foreign-family tokens, not for polarity or content, and stage B does not read it.",
    "known-obstruction-erased":
        "conclusion.known_obstruction is not compared with the frozen Kerr obstruction by either stage.",
    "equivalence-inflation":
        "equivalent_rephrasings is not truth-checked by either stage, so declaring a strictly weaker statement equivalent passes.",
    "containment-reversal":
        "R16 cross-checks one_way_entailments rows only; implication_ledger.extension_class_containment is not validated as a containment direction.",
    "sobolev-threshold-lowered":
        "R05 checks that a numeric Sobolev index is present, not that it matches the frozen s > 5/2 threshold.",
    "end-structure-contradiction":
        "R04 validates slice_topology for the one-end declaration but never cross-checks topology.end_structure.",
    "development-topology-weakened":
        "development_topology is required to be present but no rule asserts global hyperbolicity of the development.",
    "extension-predicate-weakened":
        "R18 pins only frozen_regularity / frozen_equation_concept / frozen_direction; the properness and future-direction clauses of the extension definition are not compared with the frozen text.",
    "source-status-flip":
        "R15 keys on top-level provenance.citation_status; a per-source status flip to verified is not reconciled against the top-level status or a retrieval record.",
    "schema-falsifier-erasure":
        "R14 requires falsifier.machine_checkable_steps, not falsifier.schema_falsifiers, so the class self-guards can be replaced by an unsupported assurance.",
    "wcc-completeness-definition-swap":
        "R09 checks that i_plus.completeness_definition is present; its content is not compared with the frozen generator-completeness definition.",
    "wcc-visibility-negation-weakened":
        "R10 requires visibility.negation_conclusion to be present but does not check that it keeps the frozen no-geodesic-visible formulation.",
    "wcc-adm-mass-sign-erased":
        "R05 checks only that data_class.adm_mass exists; the sign field is never compared with the positive-mass theorem.",
    "wcc-excluded-set-erasure":
        "R07 / R25 inspect genericity.generic_set; genericity.excluded_set content and excluded_set_status are not cross-checked against the frozen meagerness obligation.",
    "wcc-nonvacuity-status-overclaim":
        "non_vacuity.status is not read by either stage (R08 checks condition and witness_type only), so an unsupported membership claim is invisible.",
}

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def sha_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def dump(doc) -> str:
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True,
                          default_flow_style=False, width=4096)


def replace_once(doc, path, old: str, new: str):
    cur = doc
    for p in path[:-1]:
        cur = cur[p]
    key = path[-1]
    text = cur[key]
    if old not in text:
        raise KeyError(f"substring not found at {'.'.join(path)}: {old[:60]!r}")
    cur[key] = text.replace(old, new, 1)


MUTATIONS = []


def mut(mid, family, arm, rephrased, description):
    def deco(fn):
        MUTATIONS.append({"mutation_id": mid, "family": family, "arm": arm,
                          "rephrased": rephrased, "description": description, "apply": fn})
        return fn
    return deco


# --------------------------- polarity / content ---------------------------
@mut("m01", "conclusion-polarity-inversion", "C2", True,
     "conclusion.statement_formal and statement_natural_language assert the EXISTENCE of a proper future C2 vacuum extension (the negation of the class conclusion) while conclusion_type keeps scc_c2_future_inextendibility.")
def m01(d):
    d["conclusion"]["statement_formal"] = (
        "forall r in D0 exists G_r comeager forall D in G_r: "
        "exists proper_future_extension_in_class(MGHD(D))")
    d["conclusion"]["statement_natural_language"] = (
        "Generic asymptotically flat vacuum initial data have a maximal development that admits a "
        "proper future C2 vacuum extension.")


@mut("m02", "conclusion-polarity-inversion", "C0", True,
     "Same content inversion for the C0 arm; conclusion_type is left at scc_c0_future_inextendibility.")
def m02(d):
    d["conclusion"]["statement_formal"] = (
        "forall r in D0 exists G_r comeager forall D in G_r: "
        "exists proper_future_extension_in_class(MGHD(D))")
    d["conclusion"]["statement_natural_language"] = (
        "Generic asymptotically flat vacuum initial data have a maximal development that admits a "
        "proper future C0 metric extension.")


@mut("m03", "conclusion-content-erasure", "C2", True,
     "conclusion statements are replaced by a true but conclusion-free claim (global hyperbolicity), so the class no longer asserts inextendibility.")
def m03(d):
    d["conclusion"]["statement_formal"] = (
        "forall r in D0 exists G_r comeager forall D in G_r: "
        "MGHD(D) is a globally hyperbolic 4-manifold")
    d["conclusion"]["statement_natural_language"] = (
        "Generic asymptotically flat vacuum initial data have a maximal globally hyperbolic development.")


@mut("m04", "conclusion-content-erasure", "C0", True,
     "Same conclusion-content erasure for the C0 arm.")
def m04(d):
    d["conclusion"]["statement_formal"] = (
        "forall r in D0 exists G_r comeager forall D in G_r: "
        "MGHD(D) is a globally hyperbolic 4-manifold")
    d["conclusion"]["statement_natural_language"] = (
        "Generic asymptotically flat vacuum initial data have a maximal globally hyperbolic development.")


@mut("m05", "natural-language-inversion", "C2", True,
     "Only conclusion.statement_natural_language is inverted; statement_formal and the token stay canonical, so the natural-language reading contradicts the class.")
def m05(d):
    d["conclusion"]["statement_natural_language"] = (
        "Generic asymptotically flat vacuum initial data have a maximal development that admits a "
        "proper future C2 vacuum extension.")


@mut("m06", "natural-language-inversion", "C0", True,
     "Same natural-language-only inversion for the C0 arm.")
def m06(d):
    d["conclusion"]["statement_natural_language"] = (
        "Generic asymptotically flat vacuum initial data have a maximal development that admits a "
        "proper future C0 metric extension.")


@mut("m07", "known-obstruction-erased", "C2", True,
     "conclusion.known_obstruction (Kerr exact-data obstruction) is replaced by an assertion that no obstruction is known.")
def m07(d):
    d["conclusion"]["known_obstruction"] = (
        "there is no known obstruction to future inextendibility in the C2 class; the generic "
        "statement is expected to hold as stated.")


@mut("m08", "known-obstruction-erased", "C0", True,
     "Same known-obstruction erasure for the C0 arm.")
def m08(d):
    d["conclusion"]["known_obstruction"] = (
        "there is no known obstruction to future inextendibility in the C0 class; the generic "
        "statement is expected to hold as stated.")


@mut("m09", "equivalence-inflation", "C2", True,
     "A strictly weaker/different statement (future geodesic completeness) is appended to equivalent_rephrasings with status equivalent.")
def m09(d):
    d["conclusion"]["equivalent_rephrasings"].append({
        "phrasing": "the maximal development is future geodesically complete",
        "status": "claimed equivalent; the development cannot be extended because it has no future boundary",
    })


@mut("m10", "equivalence-inflation", "C0", True,
     "Same equivalence inflation for the C0 arm.")
def m10(d):
    d["conclusion"]["equivalent_rephrasings"].append({
        "phrasing": "the maximal development is future geodesically complete as a continuous Lorentzian manifold",
        "status": "claimed equivalent; no future boundary point can be attached",
    })


@mut("m11", "containment-reversal", "C2", False,
     "implication_ledger.extension_class_containment is reversed (C0 subset of C2), contradicting the frozen ordering while one_way_entailments rows stay canonical.")
def m11(d):
    d["implication_ledger"]["extension_class_containment"] = (
        "E_C0 subset of E_H2loc subset of E_{C^1,1} subset of E_C2: the higher the required "
        "regularity, the larger the set of admissible extensions (this reverses the frozen ordering).")


@mut("m12", "containment-reversal", "C0", False,
     "Same containment reversal for the C0 arm, contradicting the frozen E_C0 contains ... contains E_C2 chain.")
def m12(d):
    d["implication_ledger"]["extension_class_containment"] = (
        "E_C2 contains E_{C^1,1} contains E_H2loc contains E_C0: the least regular class has the "
        "smallest extension set (this reverses the frozen ordering).")


@mut("m13", "sobolev-threshold-lowered", "C2", True,
     "The Sobolev threshold is lowered from s > 5/2 to s >= 2 in data_class.regularity_class.sobolev_variant.s.")
def m13(d):
    d["data_class"]["regularity_class"]["sobolev_variant"]["s"] = (
        "s >= 2 (the 5/2 threshold is not required for the argument)")


@mut("m14", "sobolev-threshold-lowered", "C0", True,
     "Same Sobolev threshold lowering for the C0 arm.")
def m14(d):
    d["data_class"]["regularity_class"]["sobolev_variant"]["s"] = (
        "s >= 2 (the 5/2 threshold is not required for the argument)")


@mut("m15", "end-structure-contradiction", "C2", True,
     "topology.end_structure is changed to two asymptotically flat ends while slice_topology still declares a one-ended AF slice.")
def m15(d):
    d["topology"]["end_structure"] = "two asymptotically flat ends"


@mut("m16", "end-structure-contradiction", "C0", True,
     "Same end-structure contradiction for the C0 arm.")
def m16(d):
    d["topology"]["end_structure"] = "two asymptotically flat ends"


@mut("m17", "development-topology-weakened", "C2", True,
     "topology.development_topology drops global hyperbolicity; the development becomes an arbitrary 4-manifold with a Cauchy surface.")
def m17(d):
    d["topology"]["development_topology"] = (
        "M is a 4-manifold admitting a Cauchy surface; global hyperbolicity is not assumed")


@mut("m18", "development-topology-weakened", "C0", True,
     "Same development-topology weakening for the C0 arm.")
def m18(d):
    d["topology"]["development_topology"] = (
        "M is a 4-manifold admitting a Cauchy surface; global hyperbolicity is not assumed")


@mut("m19", "extension-predicate-weakened", "C2", True,
     "extension_predicate.definition drops the properness clause and the requirement that the extension add future points, so M' = M would count as an extension.")
def m19(d):
    replace_once(d, ["extension_predicate", "definition"],
                 "(b) iota(M) is an open, proper subset of M';",
                 "(b) iota(M) is an open subset of M' (properness is not required);")
    replace_once(d, ["extension_predicate", "definition"],
                 "(f) the extension adds points to the future:",
                 "(f) no condition on the causal relation between M and M' is imposed; "
                 "the earlier requirement that the extension add points to the future is dropped:")


@mut("m20", "extension-predicate-weakened", "C0", True,
     "Same extension-predicate weakening for the C0 arm.")
def m20(d):
    replace_once(d, ["extension_predicate", "definition"],
                 "(b) iota(M) is an open, proper subset of M';",
                 "(b) iota(M) is an open subset of M' (properness is not required);")
    replace_once(d, ["extension_predicate", "definition"],
                 "(f) the extension adds points to the future:",
                 "(f) no condition on the causal relation between M and M' is imposed; "
                 "the earlier requirement that the extension add points to the future is dropped:")


@mut("m21", "source-status-flip", "C2", False,
     "The Kerr source entry is marked status=verified with a supplied identifier while top-level provenance.citation_status stays unverified.")
def m21(d):
    d["provenance"]["sources"][2]["status"] = "verified"
    d["provenance"]["sources"][2]["identifier"] = "arXiv:1507.00601 (retrieved 2026-09-11)"


@mut("m22", "source-status-flip", "C0", False,
     "Same per-source status flip on the C0 Kerr source.")
def m22(d):
    d["provenance"]["sources"][2]["status"] = "verified"
    d["provenance"]["sources"][2]["identifier"] = "arXiv:1507.00601 (retrieved 2026-09-11)"


@mut("m23", "schema-falsifier-erasure", "C2", False,
     "falsifier.schema_falsifiers (the class self-guards) are replaced by an unsupported assurance.")
def m23(d):
    d["falsifier"]["schema_falsifiers"] = [
        "none: every internal failure mode of this class is already covered by the other slots"]


@mut("m24", "schema-falsifier-erasure", "C0", False,
     "Same schema-falsifier erasure for the C0 arm.")
def m24(d):
    d["falsifier"]["schema_falsifiers"] = [
        "none: every internal failure mode of this class is already covered by the other slots"]


# --------------------------- WCC arm --------------------------------------
@mut("m25", "wcc-completeness-definition-swap", "W", True,
     "i_plus.completeness_definition is swapped for a weak reading (finite affine parameter interval) that no longer requires generator completeness.")
def m25(d):
    d["i_plus"]["completeness_definition"] = (
        "every null geodesic generator of I+ has an affine parameter defined on a nonempty interval "
        "of finite length; completeness is interpreted weakly, so the generator need not be complete.")


@mut("m26", "wcc-visibility-negation-weakened", "W", True,
     "visibility.negation_conclusion allows visibility along a single generator instead of forbidding visibility of any incomplete causal geodesic.")
def m26(d):
    d["visibility"]["negation_conclusion"] = (
        "there is NO visible_singularity_from_I_plus: it is enough that no single future-inextendible "
        "causal geodesic is visible from all of I+; visibility along one generator is allowed.")


@mut("m27", "wcc-adm-mass-sign-erased", "W", True,
     "data_class.adm_mass.sign is replaced by 'no sign is assumed', dropping the positive-mass theorem input.")
def m27(d):
    d["data_class"]["adm_mass"]["sign"] = (
        "no sign is assumed; negative-mass data are retained in the ambient space")


@mut("m28", "wcc-excluded-set-erasure", "W", True,
     "genericity.excluded_set is declared empty and excluded_set_status resolved, erasing the Kerr exclusion the generic quantifier depends on.")
def m28(d):
    d["genericity"]["excluded_set"] = (
        "empty: the comeager set is all of the data space; no datum is excluded and the known "
        "extendible families are reclassified as generic.")
    d["genericity"]["excluded_set_status"] = "resolved: nothing is excluded"


@mut("m29", "wcc-nonvacuity-status-overclaim", "W", True,
     "non_vacuity.status claims the witness family has been constructed and its membership verified, an unsupported existence claim.")
def m29(d):
    d["non_vacuity"]["status"] = (
        "the witness family has been constructed and its membership in G is verified in this "
        "schema; non-vacuity is settled at the stated genericity.")


# ---------------------------------------------------------------------------
# controls (authored once; run once by the runner)
# ---------------------------------------------------------------------------
def ctrl_conforming_c2(d):
    replace_once(d, ["scope_statement"],
                 "The maximal globally hyperbolic development of generic asymptotically flat vacuum initial data",
                 "For generic asymptotically flat vacuum initial data, the maximal globally hyperbolic development")
    replace_once(d, ["non_vacuity", "condition"],
                 "the class must be applied to data whose maximal development is not",
                 "the class is to be applied only to data whose maximal development is not")


def ctrl_conforming_c0(d):
    replace_once(d, ["genericity", "generic_set"],
                 "G = countable intersection of open dense subsets of X^r_vac(AF); complement meager",
                 "G is the countable intersection of open dense subsets of X^r_vac(AF), whose complement is meager")
    replace_once(d, ["conclusion", "statement_natural_language"],
                 "have a maximal development that is future-inextendible as a continuous Lorentzian manifold",
                 "possess a maximal development that cannot be extended to the future as a continuous Lorentzian manifold")


def ctrl_quoted_wcc_phrase_c2(d):
    d["anti_scope"]["phrases_that_are_not_this_class"].append(
        'the phrase "visible singularity from I+" names the WCC predicate of a different class and '
        'is quoted here only to forbid its use in this schema')


def ctrl_quoted_composite_c0(d):
    d["anti_scope"]["phrases_that_are_not_this_class"].append(
        'the composite label "C0 or C2" is quoted here only to forbid merged-regularity statements '
        'in this class')


CONTROLS = [
    {"control_id": "c01", "fixture": "c01_conforming_c2_polished.yaml", "kind": "conforming",
     "arm": "C2", "apply": ctrl_conforming_c2,
     "description": "faithful rephrase of scope_statement and non_vacuity.condition, no axis change"},
    {"control_id": "c02", "fixture": "c02_conforming_c0_polished.yaml", "kind": "conforming",
     "arm": "C0", "apply": ctrl_conforming_c0,
     "description": "faithful rephrase of genericity.generic_set and conclusion.statement_natural_language, no axis change"},
    {"control_id": "c03", "fixture": "c03_quoted_wcc_phrase_c2.yaml", "kind": "negated-phrase",
     "arm": "C2", "apply": ctrl_quoted_wcc_phrase_c2,
     "description": "quoted forbidden WCC phrase inside anti_scope.phrases_that_are_not_this_class; must pass both stages"},
    {"control_id": "c04", "fixture": "c04_quoted_composite_c0.yaml", "kind": "negated-phrase",
     "arm": "C0", "apply": ctrl_quoted_composite_c0,
     "description": "quoted forbidden composite label 'C0 or C2' inside anti_scope; must pass both stages"},
]


def build(fixtures_only: bool):
    # --- pin check before anything is written ---------------------------------
    pin_report = {}
    for rel, want in PINS.items():
        got = sha_file(ROOT / rel)
        pin_report[rel] = {"pinned": want, "measured": got, "match": got == want}
    frozen_now = sha_file(FROZEN)
    pin_report["artifacts/formulation/FROZEN.json"] = {
        "pinned": FROZEN_MANIFEST_SHA, "measured": frozen_now,
        "match": frozen_now == FROZEN_MANIFEST_SHA}
    bad = [k for k, v in pin_report.items() if not v["match"]]
    if bad:
        print("PIN MISMATCH, refusing to build:", bad, file=sys.stderr)
        return 3
    fz = json.loads(FROZEN.read_text())

    (HERE / "bases").mkdir(parents=True, exist_ok=True)
    (HERE / "mutants").mkdir(parents=True, exist_ok=True)
    (HERE / "controls").mkdir(parents=True, exist_ok=True)
    (HERE / "raw").mkdir(parents=True, exist_ok=True)

    bases = {}
    docs = {}
    for arm, spec in BASES.items():
        src = ROOT / spec["frozen_path"]
        dst = HERE / "bases" / Path(spec["frozen_path"]).name
        dst.write_bytes(src.read_bytes())
        got = sha_file(dst)
        assert got == PINS[spec["frozen_path"]], (arm, got)
        bases[arm] = {"path": str(dst.relative_to(ROOT)), "sha256": got,
                      "class_id": spec["class_id"], "frozen_path": spec["frozen_path"]}
        docs[arm] = yaml.safe_load(dst.read_text())

    # --- mutants ---------------------------------------------------------------
    mutants = []
    for m in MUTATIONS:
        doc = copy.deepcopy(docs[m["arm"]])
        m["apply"](doc)
        fixture = f"{m['mutation_id']}_{m['family']}_{m['arm']}.yaml"
        path = HERE / "mutants" / fixture
        path.write_text(dump(doc))
        mutants.append({
            "mutation_id": m["mutation_id"], "fixture": fixture, "family": m["family"],
            "rephrased": bool(m["rephrased"]), "class_id": BASES[m["arm"]]["class_id"],
            "arm": m["arm"], "base": bases[m["arm"]]["path"], "base_sha256": bases[m["arm"]]["sha256"],
            "path": str(path.relative_to(ROOT)), "sha256": sha_file(path),
            "mutation": m["description"],
        })

    # --- controls --------------------------------------------------------------
    controls = []
    for c in CONTROLS:
        doc = copy.deepcopy(docs[c["arm"]])
        c["apply"](doc)
        path = HERE / "controls" / c["fixture"]
        path.write_text(dump(doc))
        controls.append({
            "control_id": c["control_id"], "fixture": c["fixture"], "kind": c["kind"],
            "class_id": BASES[c["arm"]]["class_id"], "arm": c["arm"],
            "base": bases[c["arm"]]["path"], "base_sha256": bases[c["arm"]]["sha256"],
            "path": str(path.relative_to(ROOT)), "sha256": sha_file(path),
            "description": c["description"],
        })

    frozen_canonical = [BASES[a]["frozen_path"] for a in ("W", "C2", "C0")]

    families = {}
    for m in mutants:
        families.setdefault(m["family"], []).append(m["fixture"])

    manifest = {
        "corpus_id": CORPUS_ID, "task_id": TASK_ID, "assignment": ASSIGNMENT,
        "worker": WORKER, "actor": ACTOR, "generated_at": now(), "deadline": DEADLINE,
        "budget_agent_hours": BUDGET_AGENT_HOURS, "node_id": NODE_ID, "gate": GATE,
        "class_ids": CLASS_IDS,
        "frozen_revision": FROZEN_REVISION,
        "frozen_manifest": {"path": "artifacts/formulation/FROZEN.json",
                            "sha256": FROZEN_MANIFEST_SHA,
                            "revision_measured": fz.get("revision")},
        "pins": PINS,
        "pin_check_at_build": pin_report,
        "frozen_revision_binding": {
            "note": ("corpus built against the rev28 frozen bytes; the five card pins are re-measured "
                     "at build time and re-measured by the runner before and after the stage runs"),
            "schemas": {p: PINS[p] for p in PINS if p.startswith("schemas/")},
            "taxonomy_sha256": PINS["research_map/formulation_taxonomy.yaml"],
            "rule_spec_sha256": PINS["artifacts/formulation/rule_spec.json"],
        },
        "stages": {
            "structural": {"path": str(STRUCT_GATE.relative_to(ROOT)), "sha256": sha_file(STRUCT_GATE)},
            "semantic": {"path": str(SEM_GATE.relative_to(ROOT)), "sha256": sha_file(SEM_GATE)},
            "stage_a_key_manifest": {"path": str(KEY_MANIFEST.relative_to(ROOT)),
                                     "sha256": sha_file(KEY_MANIFEST)},
        },
        "bases": bases,
        "mutants": mutants,
        "controls": controls,
        "frozen_canonical_controls": frozen_canonical,
        "families": [{"family": f, "rationale": FAMILY_RATIONALES.get(f, "no rule in either stage inspects this axis"),
                      "fixtures": sorted(v)} for f, v in sorted(families.items())],
        "counts": {
            "mutants": len(mutants),
            "families": len(families),
            "rephrased": sum(1 for m in mutants if m["rephrased"]),
            "controls_total": len(controls) + len(frozen_canonical),
            "frozen_canonical_controls": len(frozen_canonical),
            "conforming_controls": sum(1 for c in controls if c["kind"] == "conforming"),
            "negated_phrase_controls": sum(1 for c in controls if c["kind"] == "negated-phrase"),
        },
        "acceptance_targets": {"min_mutants": 20, "min_families": 10, "min_controls": 7,
                               "frozen_canonical_controls": 3, "conforming_controls": 2,
                               "negated_phrase_controls": 2},
        "corpus_definition_note": (
            "written before any stage run; the runner records this file's sha256 before executing "
            "stage A and stage B and never rewrites a fixture after a verdict is observed"),
        "falsifier": (
            "A corpus built against superseded bytes; a manifest hashed after the run; any control "
            "rejected by either stage; a union escape rate of 0 reported without the raw per-fixture "
            "verdicts; or a mid-run change to any pinned canonical hash."),
        "do_not_claim": "No node completion, no gate verdict, no theorem. Independent measurement evidence only.",
    }

    if fixtures_only:
        print(f"fixtures-only: {len(mutants)} mutants / {len(families)} families / "
              f"{len(controls) + len(frozen_canonical)} controls")
        return 0

    if (HERE / "manifest.json").exists():
        print("manifest.json already exists; refusing to overwrite (pre-registration)", file=sys.stderr)
        return 4
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"FROZEN manifest written: {len(mutants)} mutants / {len(families)} families / "
          f"{len(controls) + len(frozen_canonical)} controls")
    print("manifest sha256:", sha_file(HERE / "manifest.json"))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures-only", action="store_true")
    ap.add_argument("--freeze", action="store_true")
    a = ap.parse_args()
    sys.exit(build(fixtures_only=a.fixtures_only))
