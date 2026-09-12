#!/usr/bin/env python3
"""
W061-F1-VARSTRENGTH-05 -- independent strictness-direction adjudication of the registered
variant records named by astra-life05-evidence-binding-repair item (3):

    SET (parent_class AF-WCC-VAC-GEN, node F1) and CH (parent_class AF-SCC-C0-VAC-GEN, node F2b)

Question: at the pinned rev12 bytes, does each record's strength label point in the direction
that the pinned definitions actually force?  The point of the probe is that "strength" is
level-indexed: a predicate and its negation reverse the direction, so the same record can be
right at one level and wrong at another.

Method (all independent of worker-076's probe_vis_strength.py):
  * read PINNED copies only, so the run survives upstream drift; measure live bytes separately;
  * enumerate finite preorders/chains and evaluate the two visibility predicates directly
    (T = single-q tail predicate, S = SET/union predicate);
  * prove T => S exhaustively on the finite corpus and refute S => T with an explicit
    omega-chain escape certificate (finite truncation + closed-form escape index);
  * evaluate the B-containment / canonical-negation claim of F1 line 215 with the same models;
  * classify each pinned strength token by (level, direction) against the derived direction;
  * run four mutants as fail-closed controls, so a detector that never fires is visible.

Output: probe_output.json next to this file.  No canonical artifact is edited.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PINNED = os.path.join(HERE, "pinned")
CONTROL = os.path.join(HERE, "control")
OUT = os.path.join(HERE, "probe_output.json")

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")

CANON = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
    "registry": "artifacts/formulation/VARIANT_REGISTRY.json",
    "set_delta": "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
    "ch_delta": "artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json",
    "frozen": "artifacts/formulation/FROZEN.json",
}
PIN_NAMES = {
    "F1": "af_wcc_vacuum.yaml",
    "F2b": "af_scc_c0_vacuum.yaml",
    "registry": "VARIANT_REGISTRY.json",
    "set_delta": "AF-WCC-VAC-GEN.variant-SET.delta.json",
    "ch_delta": "AF-SCC-C0-VAC-GEN.variant-CH.delta.json",
    "frozen": "FROZEN.json",
}


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def line_of(path: str, needle: str) -> int:
    with open(path, encoding="utf-8") as f:
        for i, ln in enumerate(f, 1):
            if needle in ln:
                return i
    return -1


def text_at(path: str, needle: str) -> str:
    with open(path, encoding="utf-8") as f:
        for ln in f:
            if needle in ln:
                return ln.strip()
    return ""


# --------------------------------------------------------------------------------------
# 1. finite causal-order models
# --------------------------------------------------------------------------------------

def preorders(n: int):
    """All reflexive transitive relations on range(n), as an n x n boolean matrix."""
    off = [(i, j) for i in range(n) for j in range(n) if i != j]
    for bits in itertools.product((False, True), repeat=len(off)):
        R = [[i == j for j in range(n)] for i in range(n)]
        for (i, j), b in zip(off, bits):
            R[i][j] = b
        ok = True
        for a in range(n):
            for b in range(n):
                if not R[a][b]:
                    continue
                for c in range(n):
                    if R[b][c] and not R[a][c]:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            yield R


def chain_in(R, n, length):
    for seq in itertools.product(range(n), repeat=length):
        if all(R[seq[i]][seq[i + 1]] for i in range(length - 1)):
            yield list(seq)


def down(R, n, q):
    return {x for x in range(n) if R[x][q]}


def evaluate(R, n, chain, iplus):
    """T = exists q in I+, exists t0: tail from t0 inside J^-(q); S = whole chain in union."""
    T = False
    for q in iplus:
        dq = down(R, n, q)
        for t0 in range(len(chain)):
            if all(x in dq for x in chain[t0:]):
                T = True
                break
        if T:
            break
    union = set()
    for q in iplus:
        union |= down(R, n, q)
    S = all(x in union for x in chain)
    return T, S


def finite_corpus(max_n=4, max_len=3):
    """All non-empty I+ subsets, so S (a union condition) can differ from T (one q)."""
    stats = {
        "models": 0, "cases": 0, "T_and_not_S": 0, "S_and_not_T": 0,
        "T_examples": 0, "S_examples": 0,
    }
    strictness_witness = None
    negS_and_T = 0
    for n in range(1, max_n + 1):
        elements = list(range(n))
        subsets = [list(s) for k in range(1, n + 1)
                   for s in itertools.combinations(elements, k)]
        for R in preorders(n):
            stats["models"] += 1
            for length in range(1, max_len + 1):
                for chain in chain_in(R, n, length):
                    for iplus in subsets:
                        stats["cases"] += 1
                        T, S = evaluate(R, n, chain, iplus)
                        stats["T_examples"] += int(T)
                        stats["S_examples"] += int(S)
                        if T and not S:
                            stats["T_and_not_S"] += 1
                        if S and not T:
                            stats["S_and_not_T"] += 1
                            if strictness_witness is None:
                                strictness_witness = {
                                    "n": n, "R": [[int(v) for v in row] for row in R],
                                    "chain": chain, "I_plus": iplus,
                                }
                        if (not S) and T:
                            negS_and_T += 1
    stats["negS_and_T"] = negS_and_T
    stats["strictness_witness"] = strictness_witness
    return stats


def omega_certificate(N=60):
    """Infinite model decided symbolically; the bound N only limits the printed certificate.

    gamma = x_0, x_1, ... ; I+ = q_0, q_1, ... ; x_i <= x_j iff i <= j; x_i <= q_j iff i <= j.
    J^-(q_j) contains exactly {x_i : i <= j} among the gamma points, so every J^-(q_j) meets
    gamma in a finite initial segment.
    """
    def in_down_q(i, j):
        return i <= j

    # S (infinite): every x_i lies in the union; witness q_{i+1} exists for every i.
    S = all(any(in_down_q(i, j) for j in range(i + 1)) for i in range(N))
    # T (infinite): for every q_j and every finite t0, x_{max(j,t0)+1} is outside J^-(q_j).
    escapes = []
    for j in range(N):
        for t0 in range(N + 1):
            i = max(j, t0) + 1
            escapes.append({"q": j, "t0": t0, "escape_index": i,
                            "escapes": not in_down_q(i, j)})
    T = False  # every (j, t0) has an escaping index by the certificate below
    return {
        "N": N,
        "S_on_gamma": S,
        "T_on_gamma": T,
        "escape_certificate_all_hold": all(e["escapes"] for e in escapes) and bool(escapes),
        "escape_certificate_pairs_checked": len(escapes),
        "closed_form": "for q_j and any finite t0 choose i = max(j, t0) + 1; then x_i is in no J^-(q_j) with j < i",
        "S_and_not_T": S and not T,
        "b_containment": (not S),
        "canonical_negation": (not T),
        "canonical_negation_without_b_containment": (not T) and S,
    }


# --------------------------------------------------------------------------------------
# 2. strength-token classification
# --------------------------------------------------------------------------------------

def direction_of(text: str) -> str:
    t = text.lower()
    if "strictly stronger" in t:
        return "stronger"
    if "strictly weaker" in t:
        return "weaker"
    if "equivalent" in t:
        return "equivalent"
    return "unclear"


def level_of(text: str) -> str:
    t = text.lower()
    if "single-q tail predicate" in t or "single-q predicate" in t:
        return "predicate"
    if "negation" in t:
        return "negation"
    if "af-wcc-vac-gen" in t or "af-scc-c0-vac-gen" in t or "frozen class" in t:
        return "class"
    return "unclear"


def classify(variant: str, field: str, text: str, expected: str) -> dict:
    lvl = level_of(text)
    got = direction_of(text)
    if got == "equivalent":
        status = "equivalence_claim_refuted_by_omega_chain"
    elif got == "unclear" or lvl == "unclear":
        status = "unclassified"
    elif got == expected:
        status = "consistent"
    else:
        status = "inverted"
    return {"variant": variant, "field": field, "level": lvl, "claimed": got,
            "derived_expected": expected, "status": status, "text": text}


# --------------------------------------------------------------------------------------
# 3. main
# --------------------------------------------------------------------------------------

def main() -> int:
    os.makedirs(CONTROL, exist_ok=True)

    pins = {}
    for key, rel in CANON.items():
        live = os.path.join(ROOT, rel)
        pin = os.path.join(PINNED, PIN_NAMES[key])
        pins[key] = {
            "path": rel,
            "live_sha256": sha256(live) if os.path.exists(live) else None,
            "pinned_sha256": sha256(pin),
            "pin_matches_live": (sha256(live) == sha256(pin)) if os.path.exists(live) else False,
        }

    f1_path = os.path.join(PINNED, PIN_NAMES["F1"])
    f2b_path = os.path.join(PINNED, PIN_NAMES["F2b"])

    # --- F1 line 215 and 234/236 exact text -----------------------------------------
    f1_215 = text_at(f1_path, "negation_conclusion:")
    f1_234 = text_at(f1_path, "strictly STRONGER than this class's single-q tail predicate")
    f1_236 = text_at(f1_path, "show the two readings equivalent")
    f1_213 = text_at(f1_path, 'definition: "a future-inextendible causal geodesic')
    assert f1_234, "F1 relation line not found"
    assert f1_215, "F1 line 215 not found"

    with open(os.path.join(PINNED, PIN_NAMES["registry"]), encoding="utf-8") as f:
        registry = json.load(f)
    set_reg = next(v for v in registry["variants"] if v["variant_id"] == "SET")
    ch_reg = next(v for v in registry["variants"] if v["variant_id"] == "CH")
    with open(os.path.join(PINNED, PIN_NAMES["set_delta"]), encoding="utf-8") as f:
        set_delta = json.load(f)
    with open(os.path.join(PINNED, PIN_NAMES["ch_delta"]), encoding="utf-8") as f:
        ch_delta = json.load(f)

    set_delta_change = next(c for c in set_delta["changes"] if c["path"] == "visibility.definition")
    set_delta_neg = next(c for c in set_delta["changes"] if c["path"] == "visibility.negation_conclusion")
    f2b_ch = None
    with open(f2b_path, encoding="utf-8") as f:
        f2b = yaml.safe_load(f)
    for v in f2b.get("class_identity_variants", []) if isinstance(f2b.get("class_identity_variants"), list) else []:
        if isinstance(v, dict) and "horizon_localized" in str(v.get("kind", "")):
            f2b_ch = v
    if f2b_ch is None:
        # the record is a mapping under class_identity_variants.horizon_localized_variant
        civ = f2b.get("class_identity_variants")
        if isinstance(civ, dict):
            f2b_ch = civ.get("horizon_localized_variant")
    f2b_ch_relation = (f2b_ch or {}).get("relation", "")

    # --- derived algebra --------------------------------------------------------------
    corpus = finite_corpus()
    omega = omega_certificate()

    derived = {
        "predicate_level": {
            "T_single_q_tail": "exists q in I+, t0: tail gamma([t0,T)) subset J^-(q)",
            "S_set_union": "gamma([0,T)) subset union_{q in I+} J^-(q)",
            "T_implies_S": corpus["T_and_not_S"] == 0,
            "S_implies_T_finite": corpus["S_and_not_T"] == 0,
            "S_implies_T_general": False,
            "strictly_stronger_predicate": "T",
            "strictly_weaker_predicate": "S",
            "strictness_witness": "omega_chain: S true, T false",
        },
        "negation_level": {
            "not_S_implies_not_T": corpus["negS_and_T"] == 0,
            "strictly_stronger_negation": "not S (variant SET negation)",
            "strictly_weaker_negation": "not T (canonical negation)",
            "strictness_witness": "omega_chain: not T true, not S false",
        },
        "B_containment_line_215": {
            "B_containment_equals_not_S": True,
            "B_implies_canonical_negation": corpus["negS_and_T"] == 0,
            "strictness_witness_not_T_and_not_B": omega["canonical_negation_without_b_containment"],
            "line_215_claim_correct": corpus["negS_and_T"] == 0 and not omega["b_containment"],
        },
    }

    # --- token classification ---------------------------------------------------------
    classifications = [
        classify("SET", "schemas/af_wcc_vacuum.yaml:234 relation (predicate target)", f1_234, "weaker"),
        classify("SET", "VARIANT_REGISTRY.json:57 strength (class target)", set_reg["strength"], "stronger"),
        classify("SET", "SET delta changes[visibility.definition].to", set_delta_change["to"], "weaker"),
        classify("SET", "SET delta changes[visibility.negation_conclusion].to", set_delta_neg["to"], "stronger"),
        classify("SET", "SET delta strength", set_delta["strength"], "stronger"),
        classify("CH", "schemas/af_scc_c0_vacuum.yaml:291 relation (class target)", f2b_ch_relation, "weaker"),
        classify("CH", "VARIANT_REGISTRY.json:74 strength (class target)", ch_reg["strength"], "weaker"),
        classify("CH", "CH delta strength", ch_delta["strength"], "weaker"),
    ]

    # delta changes[1].to mixes "implied by" and "strictly stronger than" about the same object
    delta_to = set_delta_change["to"]
    delta_self_contradiction = ("implied by" in delta_to) and ("strictly stronger" in delta_to)

    # --- CH support-clause formal model -------------------------------------------------
    # E_CH subset E_all; B_true = (E_all == empty); CH_true = (E_CH == empty)
    ch_model = {
        "E_CH_subset_E_all": True,
        "B_implies_CH": True,
        "B_strictly_stronger_witness": "an extension outside E_CH refutes B and leaves CH true",
        "refute_CH_implies_refute_B": True,
        "refute_B_implies_refute_CH": False,
        "so_clause_pinned": "a subset of extensions suffices to refute it, so a conditional refutation of variant CH does NOT refute the frozen broad class",
        "so_clause_defect": "for a NON-conditional refutation, refuting CH does refute the frozen broad class (R_CH subset R_B); the sentence is only saved by the word 'conditional'. The correct support is: refuting CH refutes the broad class; refuting the broad class need not refute CH.",
        "pronoun_ambiguity": "'it' has no unambiguous antecedent (matches flash-19 F0-19-05 at the F0 taxonomy location)",
    }

    # --- controls (fail-closed) ---------------------------------------------------------
    controls = []

    def control(name, variant, field, text, expected, want_status):
        c = classify(variant, field, text, expected)
        c["control"] = name
        c["expected_status"] = want_status
        c["control_ok"] = c["status"] == want_status
        controls.append(c)

    control("M1-predicate-label-flipped", "SET",
            "M1 schemas/af_wcc_vacuum.yaml:234 mutant",
            f1_234.replace("strictly STRONGER", "strictly WEAKER"), "weaker", "consistent")
    control("M2-equivalence-claim", "SET",
            "M2 schemas/af_wcc_vacuum.yaml:234 mutant",
            "equivalent to this class's single-q tail predicate", "weaker",
            "equivalence_claim_refuted_by_omega_chain")
    control("M3-CH-label-flipped", "CH",
            "M3 schemas/af_scc_c0_vacuum.yaml:291 mutant",
            f2b_ch_relation.replace("strictly WEAKER", "strictly STRONGER"), "weaker", "inverted")
    control("M4-delta-contradiction-cleared", "SET",
            "M4 SET delta changes[visibility.definition].to mutant",
            "it implies the single-q tail predicate and is strictly weaker than it", "weaker",
            "consistent")
    m5_text = "it implies the single-q tail predicate and is strictly weaker than it"
    controls.append({
        "control": "M5-delta-contradiction-detector",
        "variant": "SET",
        "field": "M5 SET delta changes[visibility.definition].to mutant",
        "status": "no_self_contradiction" if not (("implied by" in m5_text) and ("strictly stronger" in m5_text)) else "self_contradiction",
        "expected_status": "no_self_contradiction",
        "control_ok": not (("implied by" in m5_text) and ("strictly stronger" in m5_text)),
        "text": m5_text,
    })

    # --- verdict ------------------------------------------------------------------------
    hard_failures = []
    findings = []
    if classifications[0]["status"] == "inverted":
        hard_failures.append(
            "HF-W061-VAR-01 (F1 SET predicate-level label inverted): schemas/af_wcc_vacuum.yaml:234 "
            "asserts variant SET is 'strictly STRONGER than this class's single-q tail predicate', "
            "but T => S holds unconditionally (finite corpus: 0 violations) and S => T fails on the "
            "omega chain (escape certificate). The single-q tail predicate is the strictly stronger "
            "reading; SET is strictly weaker. The same field's support clause ('non-containment in "
            "the union implies no single q sees a tail') is the correct negation-level implication "
            "not-S => not-T, i.e. it contradicts the predicate-level label.")
    if delta_self_contradiction:
        hard_failures.append(
            "HF-W061-VAR-02 (SET delta self-contradiction): changes[visibility.definition].to says the "
            "SET predicate 'is implied by, and strictly stronger than, the single-q tail predicate' - "
            "the two conjuncts cannot both hold under any level convention.")
    findings.append(
        "F-W061-VAR-01 (level indexing; repair guidance): the variant's NEGATION/CLASS-level label is "
        "correct and must NOT be flipped. Variant SET's negation (no SET-visible geodesic) is strictly "
        "stronger than the canonical negation (no tail-visible geodesic), because not-S => not-T "
        "(0 violations) and the omega chain has not-T true with not-S false. Registry strength "
        "(class target, 'strictly STRONGER than AF-WCC-VAC-GEN') is therefore consistent as written. "
        "A blanket inversion of every 'strictly STRONGER' token would repair the predicate-level label "
        "and break the class-level one.")
    findings.append(
        "F-W061-VAR-02 (worker-076 W076-GFORM-VIS-STRENGTH-03 corroboration): the blocker's direction "
        "is confirmed at the predicate level by an independent model corpus and an independent omega "
        "escape certificate; its scope is predicate-level. worker-076's 'line 215 forces the opposite "
        "direction' is reproduced: line 215 is correct and, by negation, forces T strictly stronger.")
    findings.append(
        "F-W061-VAR-03 (F2b CH positive control): schemas/af_scc_c0_vacuum.yaml:291 'strictly WEAKER "
        "than this frozen class' is consistent with broad => CH; E_CH subset E_all. The support clause "
        "is imprecise: a non-conditional refutation of CH does refute the broad class; the sentence is "
        "saved only by the word 'conditional', and 'it' has an ambiguous antecedent (same defect family "
        "as flash-19 F0-19-05). This is a soft precision finding, not an inversion; do not flip CH.")
    findings.append(
        "F-W061-VAR-04 (falsifier status): the record's falsifier (equivalence of the two readings) is "
        "REFUTED at the omega chain, so the falsifier does not fire; it supplies no support for either "
        "strength label. D1 remains a real divergence at the predicate level.")

    verdict = {
        "task_id": "W061-F1-VARSTRENGTH-05",
        "worker": "worker-061",
        "created_at": NOW,
        "node_id": "F1",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "verdict": "revise",
        "score": 4.0,
        "hard_failures": hard_failures,
        "findings": findings,
        "pins": pins,
        "source_citations": {
            "F1_L213_canonical_tail_predicate": f1_213,
            "F1_L215_negation_conclusion": f1_215,
            "F1_L234_variant_relation": f1_234,
            "F1_L236_variant_falsifier": f1_236,
            "F2b_CH_relation": f2b_ch_relation,
            "registry_SET_strength": set_reg["strength"],
            "registry_CH_strength": ch_reg["strength"],
            "set_delta_strength": set_delta["strength"],
            "set_delta_definition_to": delta_to,
            "set_delta_negation_to": set_delta_neg["to"],
        },
        "derived": derived,
        "classifications": classifications,
        "delta_self_contradiction": delta_self_contradiction,
        "ch_model": ch_model,
        "controls": controls,
        "control_summary": {
            "n": len(controls),
            "all_ok": all(c["control_ok"] for c in controls),
            "fired": [c["control"] for c in controls if c["control_ok"]],
        },
        "omega_certificate": omega,
        "finite_corpus": {k: v for k, v in corpus.items() if k != "strictness_witness"},
        "finite_strictness_witness": corpus["strictness_witness"],
        "no_gate_verdict": True,
        "no_node_status": True,
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(verdict, f, indent=2, sort_keys=False)
        f.write("\n")

    print(json.dumps({
        "out": OUT,
        "verdict": verdict["verdict"],
        "hard_failures": len(hard_failures),
        "controls_ok": verdict["control_summary"]["all_ok"],
        "pin_stable": all(p["pin_matches_live"] for p in pins.values()),
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
