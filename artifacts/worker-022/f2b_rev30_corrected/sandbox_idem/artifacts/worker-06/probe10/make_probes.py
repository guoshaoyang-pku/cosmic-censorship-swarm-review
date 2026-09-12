#!/usr/bin/env python3
"""FORM-PROBE-10 corpus generator (worker-06, class-bound probe corpus).

WHAT THIS IS
  An OUT-OF-SAMPLE probe corpus for the three frozen class schemas at FROZEN rev28.
  It tests whether the current two-stage acceptance pipeline catches class-contract
  leaks that are rephrased (no forbidden lexical token) and placed in fields the
  current rules demonstrably do not scan.  It is a measurement, not a schema edit.

PROTOCOL (pre-registration)
  * fixtures are generated from the frozen canonical bases after a sha256 drift check;
  * every fixture has one documented invariant violation and one falsifier;
  * manifest.json is written and hashed BEFORE any mutant is run; controls are the only
    fixtures whose stage verdicts are inspected before the freeze
    (run_probes.py --preflight);
  * after the freeze no fixture, rule, or expected outcome is edited.

Usage: python3 make_probes.py   (writes fixtures/, manifest.json, manifest.sha256)
"""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
FROZEN = ROOT / "artifacts" / "formulation" / "FROZEN.json"
SCHEMAS = ROOT / "artifacts" / "formulation" / "schemas"
CST = timezone(timedelta(hours=8))

W = SCHEMAS / "af_wcc_vacuum.yaml"
C2 = SCHEMAS / "af_scc_c2_vacuum.yaml"
C0 = SCHEMAS / "af_scc_c0_vacuum.yaml"

# FROZEN rev28 files map (the manifest's own hash is not self-referential; these are the
# three class schemas + the two gate inputs the structural stage loads).
BASES = {
    "AF-WCC-VAC-GEN": W,
    "AF-SCC-C2-VAC-GEN": C2,
    "AF-SCC-C0-VAC-GEN": C0,
}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(p: Path):
    return yaml.safe_load(p.read_text())


def dump(doc, p: Path):
    p.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=1000))


# --------------------------------------------------------------------------- edits
def find_transfer_row(g):
    """The (full_measure -> residual_comeager) row in transfer_failures, direction no_transfer."""
    for row in (g.get("transfer_failures") or []):
        if isinstance(row, dict) and list(row.get("pair") or []) == ["full_measure", "residual_comeager"]:
            return row
    raise SystemExit("FAIL: canonical C0 has no full_measure->residual_comeager transfer_failures row")


def mutants():
    """(name, base_key, family, expected, rephrased, invariant, falsifier, edit(doc, base))"""
    def m01(d, _):
        d["conclusion"]["statement_natural_language"] = (
            "Generic asymptotically flat vacuum initial data have a maximal development that is "
            "causally geodesically complete at infinity: no causal curve reaching the conformal "
            "boundary can carry information out of the strong-field interior.")

    def m02(d, _):
        d["conclusion"]["statement_natural_language"] = (
            "Generic asymptotically flat vacuum initial data have a maximal development whose "
            "boundary cannot be continued as a vacuum solution, however regular the continuation "
            "is required to be.")

    def m03(d, _):
        d["i_plus"]["definition"] = str(d["i_plus"]["definition"]) + (
            " In addition the conformal boundary is complete: every generator runs over its full "
            "affine range and the development is regular there.")

    def m04(d, _):
        d["i_plus"]["extensions"] = {"completeness_note": (
            "The conformal boundary at future null infinity is complete, every null generator is "
            "defined for all values of its affine parameter, and the development is regular there.")}

    def m05(d, _):
        d["visibility"]["reason"] = (
            "Observers at infinity are shielded from the strong-field region: no signal from the "
            "interior can reach the conformal boundary.")

    def m06(d, _):
        d["regularity"]["extensions"] = {"curvature_note": (
            "The Riemann tensor of the development is locally bounded on every compact subset, and "
            "the boundary is approached with uniformly controlled second derivatives.")}

    def m07(d, _):
        row = find_transfer_row(d["genericity"])
        row["note"] = ("For completeness: a property that holds on a full-measure set is also "
                       "generic in the residual sense used here, so this transfer may be assumed.")

    def m08(d, _):
        d["implication_ledger"]["extensions"] = {"entailment_note": (
            "Inextendibility in the weaker regularity class yields inextendibility in the stronger "
            "class, since the stronger notion is more restrictive.")}

    def m09(d, _):
        d["topology"]["extensions"] = {"multi_end_note": (
            "The construction also covers slices whose asymptotic region is not connected: several "
            "asymptotically flat ends may be present.")}

    def m10(d, _):
        d["i_plus"].setdefault("extensions", {})["observability_note"] = (
            "What a distant observer can record is exactly the radiation arriving at the boundary; "
            "the interior is causally cut off from that observer.")

    def m11(d, _):
        d["conclusion"]["equivalent_rephrasings"].append({
            "phrasing": ("no signal from the singular region ever reaches a distant observer, so the "
                         "exterior is fully predictable from boundary data"),
            "status": "listed as an equivalent rephrasing of this class conclusion"})

    def m12(d, _):
        d["extension_predicate"]["extensions"] = {"weakening_note": (
            "The continuation is only required to have one weak derivative; higher smoothness is "
            "not demanded at the boundary.")}

    return [
        ("m01_wcc_meaning_in_c0_conclusion", "AF-SCC-C0-VAC-GEN", "wcc-content-in-scc", "R32-family-meaning", True,
         "A WCC-family conclusion (observability/information at I+) is asserted where the class contract is C0 inextendibility.",
         "Exhibit a reading under which the sentence is a statement about the boundary of the development rather than about what reaches I+.",
         m01),
        ("m02_scc_meaning_in_wcc_conclusion", "AF-WCC-VAC-GEN", "scc-content-in-wcc", "R32-family-meaning", True,
         "An SCC-family conclusion (inextendibility of the development) is asserted in a schema whose conclusion is visibility at I+.",
         "Exhibit a reading under which the sentence constrains visibility from I+ rather than continuation of the development.",
         m02),
        ("m03_rephrased_completeness_in_c0_iplus_definition", "AF-SCC-C0-VAC-GEN", "iplus-completeness-in-scc", "R09-paraphrase", True,
         "Asserts I+ completeness inside an SCC schema whose i_plus.forbidden[0] forbids exactly that.",
         "Show that the added sentence is a definitional restatement already implied by the canonical i_plus definition and not a completeness assertion.",
         m03),
        ("m04_rephrased_completeness_in_c2_iplus_extensions", "AF-SCC-C2-VAC-GEN", "iplus-completeness-in-scc", "R09-paraphrase", True,
         "Asserts I+ completeness under an unscanned i_plus.extensions leaf in an SCC schema.",
         "Show the note is required by the canonical data class and asserts nothing beyond it.",
         m04),
        ("m05_wcc_meaning_in_c0_visibility_reason", "AF-SCC-C0-VAC-GEN", "wcc-content-in-scc", "R32-family-meaning", True,
         "WCC content placed in visibility.reason, an exempt explanatory field of an SCC schema.",
         "Show the sentence is only explanatory of why visibility is excluded, not an assertion of the WCC predicate.",
         m05),
        ("m06_riemann_bound_in_c0_regularity_extensions", "AF-SCC-C0-VAC-GEN", "curvature-hypothesis-in-c0", "R29-paraphrase", True,
         "A curvature/regularity hypothesis in a C0 class, phrased to miss the R29 token list.",
         "Show a C0 class may carry a locally bounded Riemann tensor as a class hypothesis without changing the extension class.",
         m06),
        ("m07_transfer_prose_in_c0_transfer_failures_note", "AF-SCC-C0-VAC-GEN", "genericity-transfer-truth-table", "R28-prose", True,
         "A note in transfer_failures asserts the truth-table-forbidden full_measure -> residual_comeager transfer while the row's direction stays no_transfer.",
         "Show the note does not assert the transfer, or that the truth table permits it.",
         m07),
        ("m08_converse_entailment_rephrased_in_c0_ledger", "AF-SCC-C0-VAC-GEN", "converse-entailment", "R16-prose", True,
         "Asserts the forbidden converse entailment (weaker-class inextendibility implies stronger-class inextendibility) without literal class tokens.",
         "Show the sentence restates the permitted one-way entailment C2 => C0 rather than its converse.",
         m08),
        ("m09_multi_end_in_c0_topology_extensions", "AF-SCC-C0-VAC-GEN", "multi-end-slice", "R04-prose", True,
         "Admits multiple asymptotically flat ends in an unscanned topology leaf while slice_topology still declares one end.",
         "Show the note is a remark about a different construction and not an admission into this class.",
         m09),
        ("m10_observability_prose_in_c0_iplus_extensions", "AF-SCC-C0-VAC-GEN", "wcc-content-in-scc", "R32-family-meaning", True,
         "Observability-at-I+ content under i_plus.extensions in an SCC schema.",
         "Show the note only explains the data class and asserts no conclusion about I+.",
         m10),
        ("m11_wcc_rephrasing_entry_in_c2_conclusion", "AF-SCC-C2-VAC-GEN", "wcc-content-in-scc", "R32-family-meaning", True,
         "A WCC-family rephrasing listed in conclusion.equivalent_rephrasings of a C2 SCC schema.",
         "Show the listed rephrasing is equivalent to C2 inextendibility rather than to a visibility statement.",
         m11),
        ("m12_weak_regularity_prose_in_c2_extension_predicate", "AF-SCC-C2-VAC-GEN", "foreign-regularity-in-c2", "R31-paraphrase", True,
         "Weakens the required extension regularity below C2 in prose, avoiding the R31 token list.",
         "Show the continuation class demanded by the sentence is still C2 (one weak derivative suffices for C2).",
         m12),
    ]


def pass_controls():
    def c04(d, _):
        d["i_plus"]["definition"] = str(d["i_plus"]["definition"]) + (
            " No completeness of the conformal boundary is claimed by this class.")

    def c05(d, _):
        d["visibility"]["reason"] = (
            "This class makes no assertion about what observers at infinity can see; visibility is "
            "explicitly not part of the conclusion.")

    return [
        ("c01_conforming_c0", "AF-SCC-C0-VAC-GEN", "conforming", None, False,
         "none - unmodified canonical bytes re-serialized", "none", lambda d, b: None),
        ("c02_conforming_c2", "AF-SCC-C2-VAC-GEN", "conforming", None, False,
         "none - unmodified canonical bytes re-serialized", "none", lambda d, b: None),
        ("c03_conforming_wcc", "AF-WCC-VAC-GEN", "conforming", None, False,
         "none - unmodified canonical bytes re-serialized (calibration canary)", "none", lambda d, b: None),
        ("c04_negated_completeness_c0", "AF-SCC-C0-VAC-GEN", "negated-phrase", None, True,
         "none - negated mention of the completeness concept must not be flagged", "none", c04),
        ("c05_negated_observability_c0", "AF-SCC-C0-VAC-GEN", "negated-phrase", None, True,
         "none - negated mention of observability must not be flagged", "none", c05),
    ]


def sensitivity_controls():
    def d01(d, _):
        d["conclusion"]["statement_natural_language"] = str(d["conclusion"]["statement_natural_language"]) + (
            " A visible incomplete geodesic decides this class.")

    def d02(d, _):
        d["conclusion"]["statement_natural_language"] = str(d["conclusion"]["statement_natural_language"]) + (
            " The extension is assumed twice differentiable.")

    return [
        ("d01_literal_visible_token_c0", "AF-SCC-C0-VAC-GEN", "sensitivity", "R12", False,
         "literal forbidden token in an assertive path - the gate MUST catch this",
         "if stage A passes this fixture, the lexical scan is not firing at all", d01),
        ("d02_literal_twice_diff_c0", "AF-SCC-C0-VAC-GEN", "sensitivity", "R31", False,
         "literal foreign-regularity token in an assertive path - the gate MUST catch this",
         "if stage A passes this fixture, the R31 scan is not firing at all", d02),
    ]


def main() -> int:
    frozen = json.loads(FROZEN.read_text())
    if frozen.get("revision") != 28:
        print(f"FAIL: FROZEN revision is {frozen.get('revision')}, expected 28")
        return 1
    files = frozen["files"]

    # --- drift check: bases and gate inputs must match the frozen manifest exactly
    drift = []
    inputs = {str(p.relative_to(ROOT)): p for p in [W, C2, C0,
              ROOT / "artifacts/formulation/rule_spec.json",
              ROOT / "artifacts/formulation/KEY_MANIFEST.json",
              ROOT / "artifacts/formulation/tools/check_class_schema.py",
              ROOT / "artifacts/worker-06/spec_conformance_audit.py"]}
    for rel, p in inputs.items():
        want = files.get(rel, {}).get("sha256")
        got = sha(p)
        if want is not None and want != got:
            drift.append({"path": rel, "frozen": want, "disk": got})
    if drift:
        print("FAIL: frozen-hash drift before generation:")
        for d in drift:
            print(" ", d)
        return 1

    fixdir = HERE / "fixtures"
    fixdir.mkdir(parents=True, exist_ok=True)
    entries = []
    for role, table in (("mutant", mutants()), ("pass_control", pass_controls()),
                        ("sensitivity_control", sensitivity_controls())):
        for (name, base_key, family, expected, rephrased, invariant, falsifier, edit) in table:
            base = BASES[base_key]
            doc = copy.deepcopy(load(base))
            edit(doc, base)
            out = fixdir / f"{name}.yaml"
            dump(doc, out)
            entries.append({
                "fixture": name,
                "path": str(out.relative_to(ROOT)),
                "sha256": sha(out),
                "role": role,
                "family": family,
                "base": str(base.relative_to(ROOT)),
                "base_sha256": sha(base),
                "rephrased": bool(rephrased),
                "expected_rule_if_caught": expected,
                "invariant_violated": invariant,
                "falsifier": falsifier,
            })

    manifest = {
        "corpus_id": "FORM-PROBE-10",
        "task_id": "FORM-PROBE-10",
        "actor": "worker-06",
        "derived_from": [
            "assign-FORM-HELDOUT-07-2026-09-11T23:44:25+08:00",
            "artifacts/worker-06/exempt_field_corpus/ (FORM-EXEMPT-09)",
            "artifacts/formulation/evidence/gate_probe_blindspot_measurement.json#877de7d73b15",
            "artifacts/formulation/FROZEN.json (revision 28)",
        ],
        "authority": ("worker-06 self-assigned continuation of the class-binding probe lane; "
                      "no assignment event is claimed and no node completion is claimed."),
        "claim_bound": ("the esc/accept verdicts of check_class_schema.py @ "
                        f"{sha(ROOT/'artifacts/formulation/tools/check_class_schema.py')[:12]} and "
                        "spec_conformance_audit.py / its documented calibrated copy, on the fixture "
                        "bytes whose sha256 are listed below"),
        "generated_at": now(),
        "frozen_revision": frozen.get("revision"),
        "frozen_frozen_at": frozen.get("frozen_at"),
        "bases": {k: {"path": str(v.relative_to(ROOT)), "sha256": sha(v)} for k, v in BASES.items()},
        "gate_inputs": {rel: {"sha256": sha(p)} for rel, p in inputs.items()},
        "validity_rule": ("a pass_control rejected by either stage invalidates the measurement; a "
                          "sensitivity_control accepted by stage A invalidates the instrument; "
                          "frozen canonical schemas are also run and reported as-is"),
        "mutants": [e for e in entries if e["role"] == "mutant"],
        "pass_controls": [e for e in entries if e["role"] == "pass_control"],
        "sensitivity_controls": [e for e in entries if e["role"] == "sensitivity_control"],
    }
    mpath = HERE / "manifest.json"
    mpath.write_text(json.dumps(manifest, indent=2) + "\n")
    msha = sha(mpath)
    (HERE / "manifest.sha256").write_text(msha + "  manifest.json\n")
    print(f"fixtures: {len(entries)} "
          f"(mutants {len(manifest['mutants'])}, pass_controls {len(manifest['pass_controls'])}, "
          f"sensitivity {len(manifest['sensitivity_controls'])})")
    print(f"manifest sha256 {msha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
