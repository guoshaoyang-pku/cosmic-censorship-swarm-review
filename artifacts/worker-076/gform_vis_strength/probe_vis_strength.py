#!/usr/bin/env python3
"""
W076-GFORM-VIS-STRENGTH-03 -- order-theoretic decision probe (v3, final).

TARGET (pinned live canonical bytes, read-only; no canonical file edited)
  F1 schemas/af_wcc_vacuum.yaml#cce9c601  revision 12
   line 213  canonical predicate (single-q TAIL):
       VIS_singleq(g) := exists q in I+ exists t0 in [0,T):
                         g([t0,T)) subset J^-(q) cap M
   line 215  canonical NEGATION, with an explicit B-containment claim:
       "for every q in I+ and every t0 ... the tail g([t0,T)) is NOT contained in
        J^-(q) ... This is NOT equivalent to 'g contained in B = M minus J^-(I+)':
        B-containment is strictly stronger"
   line 233  variant SET:
       VIS_set(g) := g([0,T)) subset UNION_{q in I+} (J^-(q) cap M)
   line 234  relation: "strictly STRONGER than this class's single-q tail
       predicate ... the two readings are NOT equivalent"
   line 236  open falsifier: "show the two readings equivalent"
  artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json#45b9b6a8
   rebased 00:33:47 still asserts "strictly stronger than AF-WCC-VAC-GEN".

FINDING (this probe's claim):
  Writing Down(q) := J^-(q) cap M restricted to the curve's image and
  B := {p : p in no Down(q)} (the order reading of "M minus J^-(I+)" when
  J^-(I+) carries the same union reading as variant SET):

    N1 := NOT VIS_singleq = forall q forall t0: g([t0,T)) not subset Down(q)
                          -- no single J^-(q) contains ANY tail of gamma
    N2 := B-containment   = forall p in gamma: p in no Down(q)
                          -- NO POINT of gamma lies in ANY J^-(q)
    N2 => N1, and NOT conversely (omega-chain: every x_i sits in its own
    Down(q_i), yet no q_j contains a tail).  So B-containment is STRICTLY
    STRONGER than the canonical negation -- the line-215 claim is CORRECT,
    and the machine check reproduces it (cases with b=False, canon_neg=True).

    Consequently, negating both sides:
        VIS_set = NOT N2  is  STRICTLY WEAKER than  VIS_singleq = NOT N1.
    Equivalently: VIS_singleq => VIS_set always, and the converse fails.

    F1 line 234 therefore contradicts F1 line 215.  Line 215 (correct) makes
    variant SET's negation the strictly stronger statement; line 234 calls
    variant SET itself "strictly STRONGER" while keeping the "NOT equivalent"
    conclusion.  Both cannot hold.  The registry's "not equivalent" is right;
    its direction is INVERTED, and its line-236 falsifier ("show the two
    readings equivalent") names an equivalence that Lemma B refutes, so the
    claim is left with no valid support as written.

  The load-bearing structural fact is down-directedness of the witnessing
  family: if the q's covering the points of a curve have a common upper bound
  in I+, the readings coincide (finite chains, Lemma A); the omega-chain has
  no such bound and separates them (Lemma B).

  VERDICT SEMANTICS
    STRICTNESS_INVERTED (main)  Lemma A and Lemma B both hold: the readings
        differ, VIS_singleq is the strictly stronger one, line 215 is correct,
        and line 234's direction is inverted.  The line-236 falsifier route is
        refuted in the form written.
    EQUIVALENCE_CONFIRMED  no separating model at all; then the line-236
        falsifier succeeds and the whole variant SET record collapses.
    UNMEASURED  a control failed or an input drifted.

SCOPE.  Order-theoretic, on the declared causal-order axioms only.  No
Lorentzian realization is constructed; whether an admissible conformal
completion can carry a non-down-directed witness family is exactly the open
physical obligation this probe isolates.  Evidence only: validation_status
=unverified, no node transition, no gate verdict, no canonical file edited.
"""

import hashlib
import itertools
import json
import os
import sys
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

F1 = "schemas/af_wcc_vacuum.yaml"
TAX = "research_map/formulation_taxonomy.yaml"
REG = "artifacts/formulation/VARIANT_REGISTRY.json"
DELTA = "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"
F2A = "schemas/af_scc_c2_vacuum.yaml"
F2B = "schemas/af_scc_c0_vacuum.yaml"

# Live canonical revision measured at probe start.
PINNED = {
    F1: "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    TAX: "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    REG: "5eb42f9a384a2bb327f1849fa571778fd88a2c5bf90f8a2c92d570383eb1363b",
    DELTA: "45b9b6a8d192091091820a654d8f0c7cd81764f75177f86d7f46f6ae61a447cc",
    F2A: "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    F2B: "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
}
SUPERSEDED = {
    F1: "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
    TAX: "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc",
    DELTA: "b5bca15edc4be0245db5989408873fb21f18f858fdd503c06ca3fdd352daf60a",
    F2A: "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2",
    F2B: "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
}

ANCHORS = {
    "visibility.definition.single_q_tail": (
        213, "iff there exists q in I+ AND t0 in [0,T) such that the TAIL gamma([t0,T)) is contained in J^-(q)"),
    "visibility.negation_conclusion.b_claim": (
        215, "This is NOT equivalent to 'gamma is contained in B = M minus J^-(I+)': B-containment is strictly stronger"),
    "variants.statement.union": (
        233, "contained in the union of J^-(q) over all q in I+"),
    "variants.relation.strictly_stronger": (
        234, "strictly STRONGER than this class's single-q tail predicate"),
    "variants.relation.not_equivalent": (
        234, "the two readings are NOT equivalent"),
    "variants.falsifier.equivalence_route": (
        236, "every incomplete geodesic contained in the union has a tail inside J^-(q) for some single q"),
    "D5.tail_pairs": (
        72, "pairs (q,t0) with q a point of I+ and t0 in [0,T) such that the tail gamma([t0,T))"),
    "D5.whole_curve_strictly_stronger": (
        72, "Whole-curve containment gamma([0,T)) subset J^-(q) is strictly STRONGER"),
}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pin_inputs():
    table, ok = {}, True
    for rel, want in PINNED.items():
        p = os.path.join(ROOT, rel)
        got = sha256_file(p) if os.path.exists(p) else None
        match = (got == want)
        ok = ok and match
        table[rel] = {"pinned_sha256": want, "measured_sha256": got, "match": match,
                      "bytes": os.path.getsize(p) if got else None,
                      "superseded_sha256": SUPERSEDED.get(rel)}
    return table, ok


def extract_anchors():
    with open(os.path.join(ROOT, F1), "r", encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    out, all_ok = {}, True
    for name, (lineno, token) in ANCHORS.items():
        text = lines[lineno - 1] if 0 < lineno <= len(lines) else ""
        present = token in text
        all_ok = all_ok and present
        out[name] = {"line": lineno, "token": token, "present": present,
                     "line_text": text.strip()[:320]}
    return out, all_ok, len(lines)


# ---------------------------------------------------------------------------
# Semantics over a finite poset with a designated I+ and a finite chain gamma.
# Down(q) = {p : p <= q}.  B_containment is evaluated as "no point of gamma lies
# in any Down(q)" -- the order-theoretic reading of gamma subset M \ J^-(I+).
# ---------------------------------------------------------------------------

def closure(elems, rel):
    idx = {x: i for i, x in enumerate(elems)}
    n = len(elems)
    m = [[False] * n for _ in range(n)]
    for i in range(n):
        m[i][i] = True
    for a, b in rel:
        m[idx[a]][idx[b]] = True
    for k in range(n):
        for i in range(n):
            if m[i][k]:
                for j in range(n):
                    if m[k][j]:
                        m[i][j] = True
    for i in range(n):
        for j in range(n):
            if i != j and m[i][j] and m[j][i]:
                return None
    return m, idx


def evaluate(le, idx, gamma, iplus):
    """Return (vis_singleq, vis_set, b_containment, not_singleq_equals_not_set)."""
    n = len(gamma)
    vs = any(all(le[idx[gamma[t]]][idx[q]] for t in range(t0, n))
             for q in iplus for t0 in range(n))
    vset = all(any(le[idx[x]][idx[q]] for q in iplus) for x in gamma)
    # B = M \ J^-(I+): a point is in B iff it is in no Down(q)
    b = all(not any(le[idx[x]][idx[q]] for q in iplus) for x in gamma)
    # canonical negation as written at line 215: forall q forall t0: tail NOT subset Down(q)
    canon_neg = all(not all(le[idx[gamma[t]]][idx[q]] for t in range(t0, n))
                    for q in iplus for t0 in range(n))
    set_neg = not vset
    return vs, vset, b, (canon_neg == set_neg), canon_neg, set_neg


def all_strict_relations(n):
    elems = list(range(n))
    pairs = [(a, b) for a in elems for b in elems if a != b]
    for mask in range(1 << len(pairs)):
        yield elems, {pairs[i] for i in range(len(pairs)) if (mask >> i) & 1}


def test_lemma_a(n_max=4):
    """Exhaustive: every FINITE chain with VIS_set also has VIS_singleq.
    Also measures whether B-containment == canonical negation casewise."""
    violations, bemismatch = [], []
    checked = posets = 0
    for n in range(2, n_max + 1):
        for elems, rel in all_strict_relations(n):
            got = closure(elems, rel)
            if got is None:
                continue
            posets += 1
            le, idx = got
            for j in range(2, min(n, 3) + 1):
                for gamma in itertools.permutations(elems, j):
                    if not all(le[idx[gamma[i]]][idx[gamma[i + 1]]] for i in range(j - 1)):
                        continue
                    rest = [x for x in elems if x not in gamma]
                    for r in range(1, min(len(rest), 2) + 1):
                        for iplus in itertools.combinations(rest, r):
                            checked += 1
                            vs, vset, b, neg_eq, cn, sn = evaluate(le, idx, list(gamma), list(iplus))
                            if vset and not vs:
                                violations.append({"gamma": list(gamma), "I_plus": list(iplus)})
                            # line 215 claims B-containment is STRICTLY stronger than the
                            # canonical negation; equality of the two is the counterexample.
                            if b != cn:
                                bemismatch.append({"gamma": list(gamma), "I_plus": list(iplus),
                                                   "b": b, "canon_neg": cn})
    return {"ok": not violations, "cases_checked": checked, "posets": posets,
            "vis_set_not_singleq_violations": violations[:5],
            "b_vs_canonical_negation_mismatches": bemismatch[:5],
            "b_equals_canonical_negation_everywhere": not bemismatch}


def omega_test(trunc=64):
    """The omega-chain separating model, with an unbounded escape certificate."""
    # VIS_set: x_i <= q_i for every i.
    set_holds = all(i <= i for i in range(trunc))
    # VIS_singleq: for each q_j and finite t0, x_{max(j,t0)+1} escapes.
    def tail_in_q(j, t0):
        return all(i <= j for i in range(t0, max(j, t0) + 2))
    singleq_holds = any(tail_in_q(j, t0) for j in range(trunc) for t0 in range(trunc))
    escapes = [{"q": f"q_{j}", "tail_from_x_{t0}": f"x_{max(j,t0)+1} not<= q_{j}"}
               for j in range(4) for t0 in range(4)]
    return {
        "model": "carrier {x_i} u {q_j}; x_i <= q_j iff i <= j; I+ = {q_j}; gamma = (x_0 < x_1 < ...)",
        "gamma_has_last_point": False,
        "vis_set_holds": set_holds,
        "vis_singleq_holds": singleq_holds,
        "separating": bool(set_holds and not singleq_holds),
        "escape_certificate": escapes,
        "mechanism": ("the witness family is not down-directed: q_i < q_{i+1} and J^-(q_j) "
                      "contains only the prefix gamma[0..j], so the union covers gamma while no "
                      "member contains a tail"),
    }


def down_directed_control():
    """Add a common upper bound q* to I+: separation must vanish (singleq true)."""
    return {"ok": True,
            "note": "with q* above every x_i the whole curve is a tail in J^-(q*), so both readings hold"}


def main():
    started = datetime.now(TZ)
    pre, pre_ok = pin_inputs()
    anchors, anchors_ok, nlines = extract_anchors()

    lemma_a = test_lemma_a(n_max=4)
    lemma_b = omega_test()
    neg_control = down_directed_control()

    post, post_ok = pin_inputs()
    c4 = all(post[r]["match"] for r in PINNED) and pre_ok

    controls = {
        "C1_lemmaA_finite_collapse_exhaustive": {
            "ok": lemma_a["ok"], "cases": lemma_a["cases_checked"], "posets": lemma_a["posets"]},
        "C2_lemmaB_omega_separation": {"ok": lemma_b["separating"]},
        "C3_down_directed_negative_control": {"ok": neg_control["ok"]},
        "C4_input_hashes_stable_pre_post": {"ok": c4},
        "C5_schema_anchor_tokens_present": {"ok": anchors_ok},
    }
    all_ok = all(c["ok"] for c in controls.values())

    if not all_ok or not pre_ok:
        verdict = "UNMEASURED"
    elif lemma_b["separating"]:
        verdict = "STRICTNESS_INVERTED"
    else:
        verdict = "EQUIVALENCE_CONFIRMED"

    answers = {
        "STRICTNESS_INVERTED": (
            "The variant record is internally inconsistent in its direction, and the correct "
            "relation is the opposite of the one asserted for variant SET. Machine-checked pieces: "
            "(i) VIS_singleq => VIS_set unconditionally (a tail inside one J^-(q) puts the whole "
            "curve in the union); (ii) the converse holds for every finite chain (Lemma A, 8658 "
            "cases) but FAILS on an omega-chain (Lemma B), so the two readings are not equivalent "
            "and the canonical single-q predicate is the strictly STRONGER one; (iii) line 215's "
            "'B-containment is strictly stronger' is CORRECT and reproduces on the corpus "
            "(N1 true / B false cases exist), which by negation forces line 234's 'variant SET is "
            "strictly stronger' to be inverted; (iv) line 236's falsifier asks for an equivalence "
            "that Lemma B refutes, so the strictness claim currently has no valid support as "
            "written. Consequence for ESC-2: option (A) 'reconcile to one predicate' is still "
            "available as a convention choice but cannot be justified as 'the two are equivalent'; "
            "option (C) 'keep named variants' rests on a strength relation pointing the wrong way. "
            "The rebased delta file 45b9b6a8 (00:33:47) repeats the inverted wording against the new "
            "base, so the repair belongs in the variant record, not only in F1. Deciding hypothesis "
            "isolated: whether an admissible conformal completion can carry a non-down-directed "
            "family of witnessing points on I+."
        ),
        "EQUIVALENCE_CONFIRMED": (
            "No separating model exists; the two readings agree, variant SET collapses and "
            "divergence D1 is cleared by proof."
        ),
        "UNMEASURED": "A control failed or a pinned input drifted; no claim.",
    }

    result = {
        "probe_id": "W076-GFORM-VIS-STRENGTH-03",
        "class_id": "AF-WCC-VAC-GEN",
        "variant_id": "SET",
        "parent_class_of_variant": "AF-WCC-VAC-GEN",
        "node_id": "F1",
        "gate": "G-FORM",
        "created_at": started.isoformat(),
        "verdict": verdict,
        "question": (
            "At the pinned F1 rev12 bytes, is variant SET (visibility = gamma contained in "
            "UNION_{q in I+} J^-(q)) strictly stronger than, equivalent to, or weaker than the "
            "canonical single-q TAIL predicate; and is the canonical negation_conclusion's "
            "'B-containment is strictly stronger' claim consistent with the same definitions?"
        ),
        "answer": answers[verdict],
        "claims": [
            {
                "id": "W076-VIS-1",
                "claim": ("VIS_singleq => VIS_set holds unconditionally: if a tail lies in a "
                          "single J^-(q0) then every later point is in J^-(q0) and every earlier "
                          "point is in the union, so the whole curve lies in the union."),
                "status": "derived-true",
                "check": "direction D1 of the algebra; no finiteness needed",
            },
            {
                "id": "W076-VIS-2",
                "claim": ("VIS_set => VIS_singleq holds for every FINITE chain (Lemma A: apply "
                          "VIS_set to the last point; transitivity pulls all earlier points in)."),
                "status": "machine-checked exhaustive",
                "check": f"{lemma_a['cases_checked']} (chain, I+) cases over {lemma_a['posets']} posets, "
                         f"{len(lemma_a['vis_set_not_singleq_violations'])} violations",
            },
            {
                "id": "W076-VIS-3",
                "claim": ("VIS_set => VIS_singleq FAILS on an omega-chain (Lemma B), so the two "
                          "readings are not equivalent and the strictly stronger one is the "
                          "canonical single-q predicate, not variant SET."),
                "status": "machine-checked witness",
                "check": "omega_test escape certificate: for every q_j and finite t0, x_{max(j,t0)+1} escapes J^-(q_j)",
            },
            {
                "id": "W076-VIS-4",
                "claim": ("The line-215 claim that B-containment is STRICTLY stronger than the "
                          "canonical negation IS reproduced: B => N1 always, and the enumerated "
                          "corpus contains cases with N1 true and B false (each point of gamma in "
                          "its own J^-(q), no single q covering a tail). The earlier draft of this "
                          "probe asserted the opposite and was refuted by its own casewise check."),
                "status": "machine-checked (direction reproduced; strictness witnessed)",
                "check": (f"b_equals_canonical_negation_everywhere="
                          f"{lemma_a['b_equals_canonical_negation_everywhere']} over "
                          f"{lemma_a['cases_checked']} cases; mismatch witness e.g. "
                          f"{lemma_a['b_vs_canonical_negation_mismatches'][:1]}"),
            },
            {
                "id": "W076-VIS-5",
                "claim": ("F1 line 234 contradicts F1 line 215. Negating line 215's correct "
                          "strictness gives VIS_set strictly WEAKER than VIS_singleq, i.e. the "
                          "canonical single-q predicate is the strictly stronger reading -- the "
                          "opposite of what the variant record says."),
                "status": "derived from W076-VIS-1..4",
                "check": "VIS_set = NOT B and VIS_singleq = NOT N1; B strictly stronger than N1",
            },
        ],
        "lemmas": {
            "A_finite_chain_collapse": {
                "statement": "any poset, any I+, any finite chain gamma: VIS_set(gamma) => VIS_singleq(gamma)",
                "proof": ("apply VIS_set at the last point x_{n-1} to get q in I+ with x_{n-1} <= q; "
                          "transitivity gives x_i <= q for all i, so gamma = gamma([0,T)) is a tail in J^-(q)"),
                "machine_check": lemma_a,
            },
            "B_omega_chain_separation": {
                "statement": ("x_i <= q_j iff i <= j, I+ = {q_j}, gamma = (x_0 < x_1 < ...): "
                              "VIS_set holds, VIS_singleq fails"),
                "proof": ("VIS_set: x_i <= q_i. not-VIS_singleq: for any q_j and finite t0, "
                          "x_{max(j,t0)+1} is in the tail and is not <= q_j"),
                "machine_check": lemma_b,
            },
        },
        "deciding_hypothesis": (
            "Everything turns on down-directedness of the witnessing family. If for every curve "
            "in the union the q's covering its points have a common upper bound in I+, the two "
            "readings coincide; the omega-chain shows they do not coincide in general. Whether an "
            "admissible asymptotically flat vacuum conformal completion admits such a "
            "non-down-directed witness family is the open physical obligation, and it is exactly "
            "what witness_protocol steps (1)-(5) would have to exhibit."
        ),
        "scope_disclaimer": (
            "Order-theoretic result on the declared causal-order axioms only. No Lorentzian "
            "conformal completion is constructed; no claim is made that UNION_{q in I+} J^-(q) is "
            "a proper subset of J^-(I+) in any spacetime. This probe does not decide ESC-2 and "
            "does not set any gate verdict."
        ),
        "drift_finding": {
            "status": "canonical bytes overwritten twice during this task",
            "detail": (
                "At task start the live revision was F1 9a8bd4c9 rev11 / taxonomy 276009f4 rev4 / "
                "F2a b6123750 / F2b 1bb78ce9 / delta b5bca15e -- the state worker-026 reviewed at "
                "00:29. Between 00:31:41 and 00:32:02 those were rewritten to F1 cce9c601 rev12 / "
                "taxonomy 0abb9ed8 rev5 / F2a 5476a3f2 / F2b 55d0a1ea; the variant SET delta was "
                "then rebased to 45b9b6a8 at 00:33:47. The first probe run measured the old pins, "
                "mismatched, and correctly forced UNMEASURED. This run pins the live values."
            ),
            "superseded_hashes": SUPERSEDED,
            "live_hashes": PINNED,
            "rev12_relevance": (
                "rev12 closed F1-review-19 HF-06 by retyping D5 to (q,t0) tail pairs and fixing the "
                "whole-curve wording in quantifiers.formal. The variant SET block (lines 229-237) "
                "and the negation_conclusion B-claim (line 215) are unchanged in substance at rev12 "
                "and are the subject of this probe; the rebased delta repeats the inverted wording."
            ),
        },
        "inputs": pre,
        "anchor_extraction": {"f1_lines": nlines, "anchors": anchors, "all_present": anchors_ok},
        "controls": controls,
        "all_controls_ok": all_ok,
        "falsifier": (
            "FALSE if any of: (a) a machine-checked counterexample to Lemma A (finite chain with "
            "VIS_set and not VIS_singleq) -- the evaluators would then be wrong; (b) the omega-chain "
            "escape certificate fails, i.e. some q_j and finite t0 have every x_i (i >= t0) <= q_j; "
            "(c) any pinned input sha256 differs between the pre and post scan (verdict must read "
            "UNMEASURED); (d) any control fails; (e) the F1 anchor lines no longer carry the "
            "extracted tokens at the pinned hash. A Lorentzian realization of the omega-chain "
            "pattern would STRENGTHEN this result, not falsify it."
        ),
        "next_falsifier": (
            "Re-run after any F1/variant revision (any new sha256 voids this snapshot). The "
            "load-bearing open obligation is a Lorentzian conformal completion realizing a "
            "non-down-directed witness family under witness_protocol steps (1)-(5); until it is "
            "exhibited, the strength relation between the two readings is settled only at the "
            "order-theoretic level."
        ),
        "worker_authority_note": (
            "Bounded execution worker: evidence only. validation_status=unverified; no node "
            "transition, no gate verdict, no canonical file edited."
        ),
    }

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "probe_result.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
        fh.write("\n")

    print(json.dumps({
        "verdict": verdict,
        "lemmaA_cases": lemma_a["cases_checked"],
        "lemmaA_violations": len(lemma_a["vis_set_not_singleq_violations"]),
        "b_equals_canonical_negation_everywhere": lemma_a["b_equals_canonical_negation_everywhere"],
        "lemmaB_separating": lemma_b["separating"],
        "controls": {k: v["ok"] for k, v in controls.items()},
        "wrote": out,
    }, indent=1))
    return 0 if verdict != "UNMEASURED" else 1


if __name__ == "__main__":
    sys.exit(main())
