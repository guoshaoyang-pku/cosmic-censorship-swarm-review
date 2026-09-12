#!/usr/bin/env python3
"""F1 tail-visibility probe (FORM-GATE-01 / G-CLASSBIND, class AF-WCC-VAC-GEN).

Independent, deterministic check written for the lead's declared F1 next_falsifier:

    "A reviewer at the rev12 hash who still cannot resolve class_contract_pointer in the
     canonical taxonomy, or who exhibits a spacetime classified differently under
     quantifiers.formal and the tail visibility predicate."

Scope and honest limits
-----------------------
This is a STRUCTURAL + ORDER-THEORETIC probe, not a physics result and not a gate verdict.
It checks, at the rev12 frozen hash:

  P1 frozen binding of the F1 schema and of the canonical taxonomy;
  P2 class_contract_pointer / supplement pointer resolution;
  P3 every normative visibility slot carries the TAIL form and the negation is the
     negation of the tail existential (not of whole-curve containment);
  P4 a whole-curve residue scan over every string leaf, with contrast/prohibition/history
     sentences exempted and reported;
  P5 an exhaustive finite-model control of the predicate relation
        (exists q: A subset J_q)  =>  (exists q,t0: Tail_t0 subset J_q)
     and of the written negation's quantifier scope, plus a witness model where the
     whole-curve reading and the tail reading classify the same object differently;
  P6 self-controls proving the probe can fail (mutants must be caught).

No spacetime is constructed. The witness in P5 is an abstract finite order-theoretic
model of the two predicates; translating it into a metric/geodesic example is the class
owner's / A1's work. validation_status = unverified.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "schemas" / "af_wcc_vacuum.yaml"
FROZEN = ROOT / "artifacts" / "formulation" / "FROZEN.json"
CANON_TAX = ROOT / "research_map" / "formulation_taxonomy.yaml"
SUPP_TAX = ROOT / "artifacts" / "formulation" / "formulation_taxonomy.yaml"
OUT = Path(__file__).resolve().parent / "f1_tail_visibility_probe_rev28.json"

CLASS_ID = "AF-WCC-VAC-GEN"
TAIL_MARKERS = ("gamma([t0,T))", "gamma([t0, T))", "TAIL gamma", "tail gamma")
WHOLE_MARKERS = (
    "gamma([0,T))",
    "gamma([0, T))",
    "whole geodesic",
    "entire geodesic",
    "whole curve",
    "entire curve",
)
EXEMPT_MARKERS = (
    "strictly stronger",
    "misclassify",
    "not equivalent",
    "earlier",
    "was false",
    "must_not_conflate",
    "would misclassify",
    "prohibition",
    "forbidden",
    "not be identified",
)
NORMATIVE_TAIL_PATHS = (
    "visibility.definition",
    "visibility.negation_conclusion",
    "quantifiers.formal",
    "quantifiers.domains.D5.definition",
)
# Paths that are deliberately NOT the canonical predicate: the registered SET variant keeps
# the older set-based/whole-curve reading by design (rev9/rev12 one-predicate policy). Such
# paths are reported under variant_contexts, never silently ignored.
VARIANT_PATH_PREFIXES = ("class_identity_variants",)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def leaves(obj, prefix=""):
    """Yield (json_path, string_value) for every string leaf."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from leaves(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from leaves(v, f"{prefix}[{i}]")
    elif isinstance(obj, str):
        yield prefix, obj


def sentences(text: str):
    return [s for s in re.split(r"(?<=[.;])\s+", text) if s.strip()]


def has_tail(text: str) -> bool:
    return any(m in text for m in TAIL_MARKERS)


def whole_curve_hits(text: str):
    """Return (hit_string, sentence) for each whole-curve marker occurrence."""
    out = []
    for m in WHOLE_MARKERS:
        if m in text:
            for s in sentences(text):
                if m in s:
                    out.append((m, s))
    return out


def sentence_exempt(sentence: str) -> bool:
    low = sentence.lower()
    return any(m in low for m in EXEMPT_MARKERS)


def is_variant_path(path: str) -> bool:
    """True for registered non-canonical variant slots (path-scoped exemption)."""
    return any(path == p or path.startswith(p + ".") or path.startswith(p + "[")
               for p in VARIANT_PATH_PREFIXES)


# ---------------------------------------------------------------- finite models
def subset(a, b) -> bool:
    return all(x in b for x in a)


def model_predicates(A, Tail, Js):
    """Finite order-theoretic model.

    I+ = {q0, q1}; Js = (J_q0, J_q1) causal pasts; tails are nested Tail0 = A (t0 = 0),
    Tail1 (t0 = 1) with Tail1 subset A.  No spacetime is constructed.
    """
    Tail0, Tail1 = A, Tail
    tail_visible = any(subset(T, J) for J in Js for T in (Tail0, Tail1))
    whole_visible = any(subset(A, J) for J in Js)
    return whole_visible, tail_visible


def negation_scope_variants(A, Tail, Js):
    """Written negations that a careless formalisation could produce.

    correct  = not exists q, t0 : Tail_t0 subset J_q          (the schema's form)
    varA     = exists q, exists t0 : not (Tail_t0 subset J_q)  (negation pushed inside)
    varB     = forall q, exists t0 : not (Tail_t0 subset J_q)
    varC     = exists q, forall t0 : not (Tail_t0 subset J_q)
    """
    Tail0, Tail1 = A, Tail
    pairs = [(T, J) for J in Js for T in (Tail0, Tail1)]
    correct = not any(subset(T, J) for T, J in pairs)
    var_a = any(not subset(T, J) for T, J in pairs)
    var_b = all(any(not subset(T, J) for T in (Tail0, Tail1)) for J in Js)
    var_c = any(all(not subset(T, J) for T in (Tail0, Tail1)) for J in Js)
    return correct, var_a, var_b, var_c


def enumeration(n=3):
    pts = list(range(n))
    subsets = [set(c) for r in range(n + 1) for c in itertools.combinations(pts, r)]
    counts = {
        "models": 0,
        "whole_implies_tail_violations": 0,
        "tail_not_whole_witnesses": 0,
        "correct_negation_models": 0,
        "scope_variant_A_mismatches": 0,
        "scope_variant_B_mismatches": 0,
        "scope_variant_C_mismatches": 0,
    }
    candidates = []
    for A in subsets:
        if not A:
            continue
        a_sorted = sorted(A)
        # legitimate tails: non-empty, proper subsets of A (t0 = 0 is A itself, t0 = 1 is a
        # later tail, so Tail1 subset-of-and-not-equal A)
        tails = [set(c) for r in range(1, len(A)) for c in itertools.combinations(a_sorted, r)]
        for Tail in tails:
            for J0 in subsets:
                for J1 in subsets:
                    Js = (J0, J1)
                    counts["models"] += 1
                    whole_visible, tail_visible = model_predicates(A, Tail, Js)
                    correct, var_a, var_b, var_c = negation_scope_variants(A, Tail, Js)
                    if whole_visible and not tail_visible:
                        counts["whole_implies_tail_violations"] += 1
                    if tail_visible and not whole_visible:
                        counts["tail_not_whole_witnesses"] += 1
                        candidates.append(
                            (len(A) + len(Tail) + len(J0) + len(J1),
                             (a_sorted, sorted(Tail), sorted(J0), sorted(J1)), A, Tail, Js)
                        )
                    if correct:
                        counts["correct_negation_models"] += 1
                    if var_a != correct:
                        counts["scope_variant_A_mismatches"] += 1
                    if var_b != correct:
                        counts["scope_variant_B_mismatches"] += 1
                    if var_c != correct:
                        counts["scope_variant_C_mismatches"] += 1
    witness = None
    if candidates:
        candidates.sort(key=lambda x: (x[0], x[1]))
        _, _, A, Tail, Js = candidates[0]
        witness = {
            "domain": sorted(pts),
            "I_plus": [0, 1],
            "whole_curve_A": sorted(A),
            "tails": {"t0=0": sorted(A), "t0=1": sorted(Tail)},
            "causal_pasts": {"J_q0": sorted(Js[0]), "J_q1": sorted(Js[1])},
            "whole_curve_predicate": False,
            "tail_predicate": True,
            "classification_under_whole_curve_reading": "not visible",
            "classification_under_tail_reading": "visible",
            "reading": (
                "abstract finite order-theoretic model, NOT a spacetime: the curve starts "
                "outside every J^-(q) and its tail enters J^-(q1); the whole-curve predicate "
                "and the tail predicate disagree on it"
            ),
        }
    return counts, witness


# ---------------------------------------------------------------- controls
def run_self_controls():
    c = {}
    # C1: a whole-curve assertion in a normative slot must be flagged (scanner has teeth)
    bad = "there exists q in I+ with gamma([0,T)) contained in J^-(q) intersect M"
    c["C1_whole_curve_assertion_flagged"] = bool(whole_curve_hits(bad)) and not sentence_exempt(sentences(bad)[0])
    # C2: a contrast/history sentence naming the whole-curve form must be exempted (no false positive)
    good = ("requiring the whole geodesic to lie in J^-(q) would misclassify a geodesic that "
            "starts in the exterior and ends inside the black-hole region")
    c["C2_contrast_sentence_exempted"] = sentence_exempt(sentences(good)[0])
    # C3: the wrong-scope negations must differ from the correct negation somewhere
    counts, _ = enumeration(n=3)
    c["C3_scope_variants_have_teeth"] = (
        counts["scope_variant_A_mismatches"] > 0
        and counts["scope_variant_B_mismatches"] > 0
        and counts["scope_variant_C_mismatches"] > 0
    )
    # C4: the implication whole => tail must hold on every enumerated model
    c["C4_whole_implies_tail_no_violation"] = counts["whole_implies_tail_violations"] == 0
    # C5: the variant exemption is path-scoped (a normative path is never exempted by it)
    c["C5_variant_exemption_is_path_scoped"] = (
        is_variant_path("class_identity_variants[0].statement")
        and not is_variant_path("visibility.definition")
    )
    return c


def main() -> int:
    checks = []
    ok = True

    def add(cid, status, detail, json_path=None):
        nonlocal ok
        checks.append({"check_id": cid, "status": status, "detail": detail, "json_path": json_path})
        if status != "pass":
            ok = False

    frozen = json.loads(FROZEN.read_text())
    frev = frozen.get("revision")
    fsha = sha256_file(FROZEN)
    schema_sha = sha256_file(SCHEMA)
    tax_sha = sha256_file(CANON_TAX)
    supp_sha = sha256_file(SUPP_TAX)
    doc = yaml.safe_load(SCHEMA.read_text())

    f1_pin = frozen["files"]["schemas/af_wcc_vacuum.yaml"]["sha256"]
    tax_pin = frozen["files"]["research_map/formulation_taxonomy.yaml"]["sha256"]
    supp_pin = frozen["files"]["artifacts/formulation/formulation_taxonomy.yaml"]["sha256"]

    add("P1a_schema_frozen_match", "pass" if schema_sha == f1_pin else "fail",
        f"schema sha256 {schema_sha[:12]} vs FROZEN rev{frev} pin {f1_pin[:12]}")
    add("P1b_taxonomy_frozen_match", "pass" if tax_sha == tax_pin else "fail",
        f"canonical taxonomy {tax_sha[:12]} vs FROZEN pin {tax_pin[:12]}")
    add("P1c_supplement_frozen_match", "pass" if supp_sha == supp_pin else "fail",
        f"supplement {supp_sha[:12]} vs FROZEN pin {supp_pin[:12]}")

    # P2 pointer resolution
    ptr = doc.get("class_contract_pointer") or ""
    ptr_path, _, anchor = ptr.partition("#")
    tax = yaml.safe_load(CANON_TAX.read_text())
    resolved = None
    if anchor:
        node = tax
        for part in anchor.split("."):
            node = node.get(part) if isinstance(node, dict) else None
        resolved = node
    add("P2a_contract_pointer_resolves", "pass" if resolved is not None else "fail",
        f"{ptr} -> {'resolved' if resolved is not None else 'MISSING'}", "class_contract_pointer")
    supp_ptr = doc.get("class_contract_supplement_pointer") or ""
    spath, _, sanchor = supp_ptr.partition("#")
    supp = yaml.safe_load(SUPP_TAX.read_text())
    snode = supp
    for part in sanchor.split("."):
        snode = snode.get(part) if isinstance(snode, dict) else None
    add("P2b_supplement_pointer_resolves", "pass" if snode is not None else "fail",
        f"{supp_ptr} -> {'resolved' if snode is not None else 'MISSING'}",
        "class_contract_supplement_pointer")

    # P3 normative tail slots
    for path in NORMATIVE_TAIL_PATHS:
        node = doc
        for part in path.split("."):
            node = node.get(part) if isinstance(node, dict) else None
        text = node if isinstance(node, str) else json.dumps(node)
        add(f"P3_tail_form::{path}", "pass" if has_tail(text) else "fail",
            "tail marker present" if has_tail(text) else "TAIL FORM MISSING", path)
    formal = doc["quantifiers"]["formal"]
    neg = doc["visibility"]["negation_conclusion"]
    add("P3_negation_of_tail_exists::quantifiers.formal",
        "pass" if re.search(r"not exists q in I\+ and t0 in \[0,T\)", formal) else "fail",
        "negation quantified over (q,t0) in the formal statement" if re.search(
            r"not exists q in I\+ and t0 in \[0,T\)", formal) else "quantifier shape not found",
        "quantifiers.formal")
    add("P3_negation_of_tail_exists::visibility.negation_conclusion",
        "pass" if ("for every q in I+" in neg and "every t0 in [0,T)" in neg) else "fail",
        "negation universally quantified over (q,t0) in the prose negation",
        "visibility.negation_conclusion")
    ordered = doc["quantifiers"]["ordered"]
    add("P3_ordered_last_is_not_exists_on_D5",
        "pass" if ordered[-1].get("kind") == "not_exists"
        and ordered[-1].get("domain_id") == "D5"
        and ordered[-1].get("binder") == "(q,t0)" else "fail",
        f"last ordered quantifier = {ordered[-1]}", "quantifiers.ordered")

    # P4 whole-curve residue scan
    flagged, exempted, variant_ctx = [], [], []
    for path, text in leaves(doc):
        for marker, sent in whole_curve_hits(text):
            rec = {"json_path": path, "marker": marker, "sentence": sent}
            if is_variant_path(path):
                rec["reason"] = ("registered non-canonical variant slot; the canonical class "
                                 "predicate is visibility.definition/quantifiers.formal")
                variant_ctx.append(rec)
            elif sentence_exempt(sent):
                exempted.append(rec)
            else:
                flagged.append(rec)
    add("P4_no_whole_curve_residue_in_normative_slots",
        "pass" if not flagged else "fail",
        f"flagged={len(flagged)} exempted={len(exempted)} variant_contexts={len(variant_ctx)}")

    # P5 finite-model control
    counts, witness = enumeration(n=3)
    add("P5a_whole_implies_tail_no_violation",
        "pass" if counts["whole_implies_tail_violations"] == 0 else "fail",
        f"{counts['models']} models enumerated; violations={counts['whole_implies_tail_violations']}")
    add("P5b_tail_reading_differs_from_whole_curve",
        "pass" if counts["tail_not_whole_witnesses"] > 0 else "fail",
        f"tail-visible/whole-invisible witness models={counts['tail_not_whole_witnesses']}")
    add("P5c_negation_scope_variants_have_teeth",
        "pass" if counts["scope_variant_A_mismatches"] > 0
        and counts["scope_variant_B_mismatches"] > 0
        and counts["scope_variant_C_mismatches"] > 0 else "fail",
        f"variantA mismatches={counts['scope_variant_A_mismatches']}, "
        f"variantB mismatches={counts['scope_variant_B_mismatches']}, "
        f"variantC mismatches={counts['scope_variant_C_mismatches']}")
    add("P5d_written_negation_is_correct_scope",
        "pass" if counts["correct_negation_models"] > 0
        and "not exists q in I+ and t0" in formal
        and "for every q in I+" in neg and "every t0 in [0,T)" in neg else "fail",
        "written formal/prose negation is the De Morgan negation of the tail existential "
        "(forall q, forall t0, not tail-subset), not one of the three wrong-scope variants")

    controls = run_self_controls()
    add("P6_self_controls", "pass" if all(controls.values()) else "fail",
        json.dumps(controls))

    sha_after = sha256_file(SCHEMA)
    add("P7_schema_stable_during_probe", "pass" if sha_after == schema_sha else "fail",
        f"sha before={schema_sha[:12]} after={sha_after[:12]}")

    result = {
        "probe": "F1 tail-visibility probe",
        "probe_version": "1.0",
        "class_id": CLASS_ID,
        "node_id": "F1",
        "gate": "G-CLASSBIND",
        "target": {
            "path": "schemas/af_wcc_vacuum.yaml",
            "sha256": schema_sha,
            "revision": doc.get("revision"),
            "revised_at": str(doc.get("revised_at")),
        },
        "frozen": {
            "path": "artifacts/formulation/FROZEN.json",
            "sha256": fsha,
            "revision": frev,
            "frozen_at": frozen.get("frozen_at"),
        },
        "pointers": {
            "class_contract_pointer": ptr,
            "resolved": resolved is not None,
            "class_contract_supplement_pointer": supp_ptr,
            "supplement_resolved": snode is not None,
        },
        "tail_form": {
            "predicate_name": doc["visibility"].get("predicate_name"),
            "normative_slots_checked": list(NORMATIVE_TAIL_PATHS),
            "formal_negation": formal,
            "prose_negation": neg,
        },
        "whole_curve_residue_scan": {
            "flagged": flagged,
            "exempted": exempted,
            "variant_contexts": variant_ctx,
            "flagged_count": len(flagged),
            "exempted_count": len(exempted),
            "variant_context_count": len(variant_ctx),
            "exemption_policy": "sentence-level contrast/prohibition/history markers "
                               "(strictly stronger, misclassify, not equivalent, earlier, was false, "
                               "must_not_conflate, ...); plus a path-scoped exemption for the "
                               "registered non-canonical class_identity_variants, reported explicitly",
        },
        "finite_model_control": {
            "n": 3,
            "I_plus": "two points q0,q1; J_q0,J_q1 causal pasts; tails t0=0 (whole curve) and "
                      "t0=1 (Tail1 subset A)",
            "counts": counts,
            "classification_divergence_witness": witness,
            "note": "abstract order-theoretic model only; no spacetime is constructed",
        },
        "self_controls": controls,
        "checks": checks,
        "verdict": "pass" if ok else "fail",
        "falsifier": (
            "a normative visibility slot at the frozen hash that is not the tail form; a "
            "class_contract_pointer that fails to resolve in the canonical taxonomy; a finite "
            "model where whole-curve containment holds and the tail predicate fails; a "
            "negation whose written quantifier scope differs from the negation of the tail "
            "existential; any whole-curve residue outside an exempted contrast sentence; or "
            "the schema hash changing during the probe"
        ),
        "not_claimed": [
            "no gate verdict and no gate self-pass (G-CLASSBIND stays pending)",
            "no node completion; F1 stays active",
            "no physics claim and no spacetime counterexample; the witness is an abstract "
            "order-theoretic model of the two predicates",
            "no claim that the whole-curve reading is the only alternative reading, or that "
            "the probe is exhaustive over natural-language phrasings",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": result["verdict"],
                      "checks_failed": [c["check_id"] for c in checks if c["status"] != "pass"],
                      "out": str(OUT.relative_to(ROOT))}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
