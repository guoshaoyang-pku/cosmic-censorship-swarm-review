#!/usr/bin/env python3
"""W076-GFORM-STRICTNESS-RECONCILE-06.

Bounded class-bound task (class AF-WCC-VAC-GEN, node F1, gate G-FORM): reconcile the two
live "two readings" strictness adjudications at F1 (rev12 cce9c601 -> rev13 d9cebb94 mid-task) by machine-checking the
three predicates they concern on finite transitive preorders plus an explicit infinite model.

Predicates (F1 visibility anchors, located by content):
  P_whole(q)     gamma([0,T)) subset J^-(q) for one exhibited q           (line 72 / line 213)
  P_tail(q)      exists t0: gamma([t0,T)) subset J^-(q)  (canonical)      (line 213 / 215)
  P_set          gamma([0,T)) subset UNION_{q in I+} J^-(q) (variant SET) (line 233)

Findings under test:
  A) worker-040 W040-F1-STRICTNESS-ADJ-04: line 72 "whole-curve containment is strictly
     STRONGER" is false for causal gamma in a transitive causal structure (tail <=> whole).
  B) worker-076 W076-GFORM-VIS-STRENGTH-03: line 234 "variant SET is strictly STRONGER" is
     inverted; single-q tail => SET, and SET + not-single-q is realizable on an omega-chain.

The probe decides T1-T4 (below), runs controls, and reports whether A and B are jointly
consistent and about different predicate pairs. Read-only: no shared/canonical file is edited.
"""

import hashlib
import itertools
import json
import os
import subprocess
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUT = os.path.dirname(os.path.abspath(__file__))

TARGETS = [
    "schemas/af_wcc_vacuum.yaml",
    "artifacts/worker-040/f1_strictness_adjudication/report.json",
    "artifacts/worker-076/gform_vis_strength/probe_result.json",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
    "artifacts/formulation/VARIANT_REGISTRY.json",
]

ANCHORS = [
    # id, must-contain tokens (located by content, so line shifts do not matter), must-not-contain
    {"id": "D5_definition_whole_tail_equivalence",
     "must": ["EQUIVALENT to the tail form", "NOT a weakening", "rev13"],
     "forbid": ["Whole-curve containment gamma([0,T)) subset J^-(q) is strictly STRONGER"]},
    {"id": "visibility_definition_no_misclassification_example",
     "must": ["tail and whole-curve readings are EQUIVALENT", "misclassification example was a non-sequitur and is removed"],
     "forbid": ["would misclassify a geodesic"]},
    {"id": "negation_conclusion_B_containment",
     "must": ["B-containment is strictly stronger", "no single point of I+ causally precedes"]},
    {"id": "witness_protocol",
     "must": ["causal relation gamma subset J^-(q) for an exhibited q in I+"]},
    {"id": "variant_SET_statement",
     "must": ["union of J^-(q) over all q in I+"]},
    {"id": "variant_SET_relation_corrected",
     "must": ["strictly WEAKER than this class's single-q tail predicate", "must never be interchanged", "rev13"],
     "forbid": ["strictly STRONGER than this class's single-q tail predicate"]},
    {"id": "variant_SET_falsifier",
     "must": ["show the two readings equivalent"]},
]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


# ---------------------------------------------------------------- preorder models
def enumerate_preorders(n):
    """All reflexive transitive relations on {0..n-1}, as tuples of bitmasks rows[i]."""
    out = []
    bits = n * n
    for mask in range(1 << bits):
        rows = [(mask >> (i * n)) & ((1 << n) - 1) for i in range(n)]
        ok = True
        for i in range(n):
            if not (rows[i] >> i) & 1:
                ok = False
                break
        if not ok:
            continue
        for i in range(n):
            for j in range(n):
                if (rows[i] >> j) & 1:
                    # transitivity: row[j] subset row[i]
                    if rows[j] & ~rows[i]:
                        ok = False
                        break
            if not ok:
                break
        if ok:
            out.append(tuple(rows))
    return out


def le(rows, a, b):
    return bool((rows[a] >> b) & 1)


def chains(rows, n, max_len):
    """Causal curves: tuples (x_0..x_{L-1}) with x_i <= x_j for all i<j (repeats allowed)."""
    res = []
    for L in range(1, max_len + 1):
        for tup in itertools.product(range(n), repeat=L):
            if all(le(rows, tup[i], tup[j]) for i in range(L) for j in range(i + 1, L)):
                res.append(tup)
    return res


def p_whole(rows, gamma, q):
    return all(le(rows, x, q) for x in gamma)


def p_tail(rows, gamma, q):
    L = len(gamma)
    return any(all(le(rows, gamma[i], q) for i in range(t0, L)) for t0 in range(L))


def p_set(rows, gamma, Q):
    return all(any(le(rows, x, q) for q in Q) for x in gamma)


def run_finite_census(n, max_len):
    preorders = enumerate_preorders(n)
    subsets = [frozenset(s) for r in range(1, n + 1) for s in itertools.combinations(range(n), r)]
    t1_viol = []            # P_whole(q) != P_tail(q)
    t2_viol = []            # P_tail => not P_set
    t3_viol = []            # P_set and no q with P_tail(q)
    set_not_single = []     # P_set and no q,t0 sees a tail
    cases = 0
    for rows in preorders:
        for gamma in chains(rows, n, max_len):
            for Q in subsets:
                pset = p_set(rows, gamma, Q)
                any_tail = False
                for q in Q:
                    pw, pt = p_whole(rows, gamma, q), p_tail(rows, gamma, q)
                    cases += 1
                    if pw != pt and len(t1_viol) < 5:
                        t1_viol.append({"rows": rows, "gamma": gamma, "Q": sorted(Q), "q": q,
                                        "p_whole": pw, "p_tail": pt})
                    if pt and not pset and len(t2_viol) < 5:
                        t2_viol.append({"rows": rows, "gamma": gamma, "Q": sorted(Q), "q": q})
                    any_tail = any_tail or pt
                if pset and not any_tail and len(t3_viol) < 5:
                    t3_viol.append({"rows": rows, "gamma": gamma, "Q": sorted(Q)})
                    set_not_single.append({"rows": rows, "gamma": gamma, "Q": sorted(Q)})
    return {
        "n": n, "preorders": len(preorders), "predicate_cases": cases,
        "T1_tail_iff_whole_violations": len(t1_viol), "T1_examples": t1_viol,
        "T2_tail_implies_set_violations": len(t2_viol), "T2_examples": t2_viol,
        "T3_set_implies_some_tail_violations": len(t3_viol), "T3_examples": t3_viol,
        "set_not_single_count": len(set_not_single),
    }


def control_non_transitive():
    """Drop transitivity: a<=b, b<=c, a not<= c. gamma=(a,b,c), Q={c}: tail holds, whole fails."""
    n = 3
    rows = [0, 0, 0]
    for a, b in ((0, 1), (1, 2), (0, 0), (1, 1), (2, 2)):
        rows[a] |= 1 << b
    gamma = (0, 1, 2)
    Q = frozenset({2})
    q = 2
    return {
        "transitive": all(not (le(rows, i, j) and le(rows, j, k)) or le(rows, i, k)
                          for i in range(n) for j in range(n) for k in range(n)),
        "p_whole": p_whole(rows, gamma, q), "p_tail": p_tail(rows, gamma, q),
        "p_set": p_set(rows, gamma, Q),
        "T1_would_fire": p_whole(rows, gamma, q) != p_tail(rows, gamma, q),
    }


def control_chain_pass():
    n = 3
    rows = [0, 0, 0]
    for i in range(n):
        for j in range(i, n):
            rows[i] |= 1 << j
    gamma = (0, 1, 2)
    Q = frozenset({2})
    return {"transitive": True, "T1_ok": p_whole(rows, gamma, 2) == p_tail(rows, gamma, 2),
            "p_whole": p_whole(rows, gamma, 2), "p_tail": p_tail(rows, gamma, 2),
            "p_set": p_set(rows, gamma, Q)}


def checker_sensitivity_control():
    """The T1 checker must fire on the structure that lacks transitivity and stay silent on the
    transitive chain: one predicate test, two structures, opposite outcomes."""
    bad = control_non_transitive_rows()
    good = [0, 0, 0]
    for i in range(3):
        for j in range(i, 3):
            good[i] |= 1 << j
    gamma, q = (0, 1, 2), 2
    fire_on_bad = p_whole(bad, gamma, q) != p_tail(bad, gamma, q)
    silent_on_good = p_whole(good, gamma, q) == p_tail(good, gamma, q)
    return {"fires_on_non_transitive": bool(fire_on_bad), "silent_on_transitive": bool(silent_on_good),
            "harness_detects": bool(fire_on_bad and silent_on_good)}


def control_non_transitive_rows():
    rows = [0, 0, 0]
    for a, b in ((0, 1), (1, 2), (0, 0), (1, 1), (2, 2)):
        rows[a] |= 1 << b
    return rows


# ---------------------------------------------------------------- omega-chain model
def omega_chain(N):
    """Elements: x_0..x_N, q_0..q_N. Base: x_i<=x_j (i<=j), q_j<=q_k (j<=k), x_i<=q_j (i<=j).

    Returns (closure_rows, intended_rows) over 2(N+1) elements; x_i index i, q_j index N+1+j.
    """
    M = 2 * (N + 1)
    base = [[False] * M for _ in range(M)]
    for i in range(N + 1):
        base[i][i] = True
        base[N + 1 + i][N + 1 + i] = True
        for j in range(i, N + 1):
            base[i][j] = True              # x_i <= x_j
            base[N + 1 + i][N + 1 + j] = True  # q_i <= q_j
            base[i][N + 1 + j] = True      # x_i <= q_j
    closure = [row[:] for row in base]
    for k in range(M):
        for i in range(M):
            if closure[i][k]:
                row_i, row_k = closure[i], closure[k]
                for j in range(M):
                    if row_k[j]:
                        row_i[j] = True
    intended = [[False] * M for _ in range(M)]
    for i in range(N + 1):
        intended[i][i] = True
        intended[N + 1 + i][N + 1 + i] = True
        for j in range(i, N + 1):
            intended[i][j] = True
            intended[N + 1 + i][N + 1 + j] = True
            intended[i][N + 1 + j] = True
    return closure, intended


def run_omega(N):
    closure, intended = omega_chain(N)
    closure_matches_intended = closure == intended
    Xi = list(range(N + 1))
    Q = list(range(N + 1, 2 * (N + 1)))
    # gamma = (x_0, x_1, ..., x_N); P_set: for each i, q_i sees x_i
    pset = all(closure[i][N + 1 + i] for i in Xi)
    # T4 certificate on the finite prefix: for every q_j with j < N (the only indices whose past
    # does not already dominate the prefix) and every t0 <= N, the witness i = max(j+1, t0) has
    # i <= N and x_i NOT <= q_j. NOTE q_N covers all x_i (i <= N): any finite prefix collapses to
    # T3, which is exactly why the separation needs the infinite model with no top member.
    no_tail_ok = True
    witness_max = None
    for j in range(N):
        for t0 in range(N + 1):
            i = max(j + 1, t0)
            if i > N:
                no_tail_ok = False          # no in-prefix witness: cannot certify q_j
            else:
                witness_max = i if witness_max is None else max(witness_max, i)
                if closure[i][N + 1 + j]:
                    no_tail_ok = False
    top_member_dominates_prefix = all(closure[i][N + 1 + N] for i in Xi)
    # strict up-directedness of the past chain J^-(q_j) subset J^-(q_{j+1})
    strict_chain = all(
        closure[N + 1 + j][N + 1 + j + 1] and not closure[N + 1 + j + 1][N + 1 + j]
        for j in range(N)
    )
    # down-directedness of the family {J^-(q_j)}: for any j<=k, the member J^-(q_j) is inside
    # the intersection J^-(q_j) cap J^-(q_k); verified directly on the closure.
    down_directed = True
    for j in range(N + 1):
        for k in range(j, N + 1):
            inter = [e for e in range(2 * (N + 1))
                     if closure[e][N + 1 + j] and closure[e][N + 1 + k]]
            smaller = [e for e in range(2 * (N + 1)) if closure[e][N + 1 + j]]
            if not set(smaller) <= set(inter):
                down_directed = False
    return {
        "N": N, "closure_equals_intended": closure_matches_intended,
        "P_set_holds": pset, "no_single_q_sees_a_tail": no_tail_ok,
        "certified_q_indices": list(range(N)),
        "top_member_q_N_dominates_prefix": top_member_dominates_prefix,
        "symbolic_infinite_extension": ("for every j in N, x_{j+1} is not <= q_j, so no q_j contains a "
                                        "tail of gamma; the family {J^-(q_j)} has no top member"),
        "max_witness_index_used": witness_max,
        "past_chain_strictly_increasing": strict_chain,
        "family_is_down_directed": down_directed,
        "gamma_has_maximum": False,
        "I_plus_finite": False,
    }


# ---------------------------------------------------------------- anchors
def check_anchors():
    path = os.path.join(REPO, "schemas/af_wcc_vacuum.yaml")
    lines = open(path, encoding="utf-8").read().splitlines()
    res = {}
    for spec in ANCHORS:
        hit = None
        for i, text in enumerate(lines, start=1):
            if all(t in text for t in spec["must"]):
                hit = (i, text)
                break
        text = hit[1] if hit else ""
        res[spec["id"]] = {
            "found": hit is not None,
            "line": hit[0] if hit else None,
            "missing_tokens": [t for t in spec["must"] if t not in text],
            "forbidden_tokens_present": [t for t in spec.get("forbid", []) if t in text],
            "line_sha256": sha256_bytes(text.encode()) if hit else None,
        }
    res["_all_ok"] = all(v["found"] and not v["missing_tokens"] and not v["forbidden_tokens_present"]
                         for k, v in res.items() if k != "_all_ok")
    return res


# ---------------------------------------------------------------- main
def main():
    started = datetime.now().astimezone()
    pre = {t: sha256_file(os.path.join(REPO, t)) for t in TARGETS if os.path.exists(os.path.join(REPO, t))}

    census = [run_finite_census(n, max_len=n) for n in (2, 3, 4)]
    omega = [run_omega(N) for N in (8, 24, 64)]
    anchors = check_anchors()
    controls = {
        "non_transitive_structure": control_non_transitive(),
        "transitive_chain_pass": control_chain_pass(),
        "broken_checker_detected": checker_sensitivity_control(),
    }

    post = {t: sha256_file(os.path.join(REPO, t)) for t in pre}
    drift = [t for t in pre if pre[t] != post[t]]
    f1_hash = pre.get("schemas/af_wcc_vacuum.yaml")

    t1_total = sum(c["T1_tail_iff_whole_violations"] for c in census)
    t2_total = sum(c["T2_tail_implies_set_violations"] for c in census)
    t3_total = sum(c["T3_set_implies_some_tail_violations"] for c in census)
    set_not_single = sum(c["set_not_single_count"] for c in census)
    controls_ok = (
        controls["non_transitive_structure"]["T1_would_fire"] is True
        and controls["non_transitive_structure"]["transitive"] is False
        and controls["transitive_chain_pass"]["T1_ok"] is True
        and controls["transitive_chain_pass"]["p_set"] is True
        and controls["broken_checker_detected"]["harness_detects"] is True
        and all(o["closure_equals_intended"] for o in omega)
        and all(o["P_set_holds"] and o["no_single_q_sees_a_tail"] and o["top_member_q_N_dominates_prefix"] for o in omega)
    )

    anchors_ok = anchors["_all_ok"]

    if drift:
        verdict = "UNMEASURED"
    elif t1_total == 0 and t2_total == 0 and t3_total == 0 and set_not_single == 0 and controls_ok and anchors_ok:
        verdict = "RECONCILED_AND_REV13_CORRECTIONS_VERIFIED"
    else:
        verdict = "REFUTED"

    result = {
        "task_id": "W076-GFORM-STRICTNESS-RECONCILE-06",
        "worker": "worker-076",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "node_id": "F1",
        "gate": "G-FORM",
        "created_at": started.isoformat(timespec="seconds"),
        "verdict": verdict,
        "authority_note": ("worker event: cannot set status=done, validation_status=passed, or any gate "
                           "verdict; controller and leads own those with artifact + review evidence. "
                           "Read-only probe; no canonical or shared file was modified."),
        "predicate_definitions": {
            "P_whole(q)": "gamma([0,T)) subset J^-(q) intersect M for one exhibited q  [F1 D5 definition / visibility.definition]",
            "P_tail(q)": "exists t0 in [0,T): gamma([t0,T)) subset J^-(q) intersect M  [canonical, visibility.definition]",
            "P_set": "gamma([0,T)) subset UNION_{q in I+} J^-(q) intersect M  [variant SET, class_identity_variants]",
        },
        "theorems": {
            "T1": {"statement": "P_whole(q) <=> P_tail(q) for causal gamma in a reflexive transitive causal structure (J^- past-closed).",
                   "proof": "gamma(0) <= gamma(t0) by causality (t0<=t<T); gamma(t0) <= q; transitivity gives gamma(0) <= q; all earlier points are <= gamma(0) and J^- is past-closed.",
                   "machine_check": f"{t1_total} violations over {sum(c['predicate_cases'] for c in census)} predicate cases / {[c['preorders'] for c in census]} preorders on n=2,3,4",
                   "bearing": "F1 rev12 line 72's 'Whole-curve containment ... is strictly STRONGER' is FALSE: for a fixed single q the two are EQUIVALENT. Corroborates worker-040 HF-040-04 / W040-F1-STRICTNESS-ADJ-04. Rev12 line 213's misclassification example is a non-sequitur for the same reason. Rev13 states the equivalence and removes the example (verified by the anchors)."},
            "T2": {"statement": "P_tail(q) => P_set always (J^-(q) subset J^-(I+)).",
                   "machine_check": f"{t2_total} violations over the same census",
                   "bearing": "The canonical single-q predicate entails the variant SET predicate; SET accepts at least everything canonical does."},
            "T3": {"statement": "If gamma has a maximum element or I+ is finite, then P_set => exists q in I+ with P_whole(q) (hence with P_tail(q)).",
                   "proof": "If gamma has a max x*, P_set gives q with x* <= q, so every gamma(t) <= x* <= q. If gamma has no max (e.g. the infinite chain) and I+ is finite, {i : x_i <= q} is a prefix for each q (past-closed + transitivity), and finitely many prefixes cover N, so one of them is cofinite, i.e. all of N.",
                   "machine_check": f"{t3_total} violations; P_set-and-no-tail count {set_not_single} over the finite census (n<=4, all I+ subsets)",
                   "bearing": "worker-040's 0/355 finite-preorder result is STRUCTURAL, not a sampling artifact; the variant SET/canonical divergence cannot be witnessed on any finite model with finite I+."},
            "T4": {"statement": "With I+ infinite and gamma infinite without maximum, P_set + not-P_tail is realizable.",
                   "model": "omega-chain: x_0 < x_1 < ..., q_0 < q_1 < ... with x_i <= q_j iff i <= j; gamma = (x_i), I+ = {q_j}. Then x_i <= q_i so P_set holds; for every j, x_{j+1} is not <= q_j, so no single q_j sees a tail.",
                   "certificate_caveat": ("On a finite prefix x_0..x_N, q_0..q_N the top member q_N dominates the whole prefix, so no "
                                          "finite prefix separates the predicates (this is T3 again). The prefix machine check therefore "
                                          "certifies q_j only for j < N, with the in-prefix witness i = max(j+1, t0) <= N; the infinite "
                                          "model's no-top-member step is the symbolic j -> x_{j+1} argument recorded in omega_chain."),
                   "machine_check": f"transitive closure equals the intended closed form for N in {[o['N'] for o in omega]}; P_set true; for every j < N no single q_j sees a tail (all t0); past chain strictly increasing; family down-directed; top-member domination of each prefix confirmed",
                   "bearing": "F1 rev12 line 234's second clause (non-containment in the union implies no single q sees a tail, not conversely) is TRUE; its word 'STRONGER' applied to variant SET was INVERTED and rev13 corrects it to 'strictly WEAKER' citing this task. Corroborates W076-GFORM-VIS-STRENGTH-03. Because F1's I+ is R x S^2 (infinite) and gamma: [0,T) has no causal maximum in a globally hyperbolic development, the escape hypotheses are met structurally by the class, so the direction is load-bearing."},
        },
        "correction_of_prior_w076_note": ("The W076-GFORM-VIS-STRENGTH-03 next_falsifier named down-directedness of the "
                                         "witness family as the deciding hypothesis. That is WRONG and is corrected here: the "
                                         "omega-chain family {J^-(q_j)} IS down-directed (a nested chain has its smaller member "
                                         "inside every pairwise intersection), yet it separates the predicates. The deciding "
                                         "criterion is T3: a maximum of gamma, or finiteness of I+, or a single q whose past "
                                         "contains the union."),
        "joint_consistency": {
            "pair_A_whole_vs_tail_single_q": "EQUIVALENT for causal gamma (T1) -> rev12 line 72 sentence false (worker-040); rev13 states the equivalence and removes the misclassification example.",
            "pair_B_set_vs_single_q_tail": "single-q strictly stronger than SET (T2+T4) -> rev12 line 234 word 'STRONGER' inverted (worker-076); rev13 corrects it to 'strictly WEAKER'.",
            "verdict": "The two adjudications concern DIFFERENT predicate pairs and are jointly consistent; the shared phrase 'the two readings' refers to different pairs in the two records. A1 reviewers must not read them as contradictory, and must not interchange whole-vs-tail with SET-vs-single-q.",
            "F1_sentence_status_at_rev12": {
                "line_72_whole_strictly_stronger": "FALSE (equivalent)",
                "line_213_misclassification_example": "NON_SEQUITUR (both readings classify identically)",
                "line_215_B_containment_strictly_stronger": "TRUE (same fact as T4 seen from the negation side)",
                "line_233_variant_SET_statement": "WELL_FORMED pointer; not a predicate of the class",
                "line_234_SET_strictly_STRONGER": "INVERTED (SET is strictly WEAKER as a visibility predicate; the second clause is true)",
                "line_236_equivalence_falsifier": "unachievable as written for this class under T4 (a finiteness/dominating-member hypothesis is needed)",
            },
        },
        "rev13_repair_check": {
            "revision_sha256": f1_hash,
            "pair_A_corrected": ("D5 definition and visibility.definition now state the tail/whole EQUIVALENCE via past-closedness and "
                                 "the misclassification example is removed"),
            "pair_B_corrected": "variant SET relation is now 'strictly WEAKER' with the direction and the non-equivalence stated",
            "cited_this_task": "both corrected anchors cite W076-GFORM-STRICTNESS-RECONCILE-06 (T1; T2/T3/T4)",
            "line_216_B_containment_claim": "retained and TRUE (T4 from the negation side) - do not 'repair' it",
            "residual_nonblocking": ("variant SET falsifier still reads 'show the two readings equivalent': under T3 that is achievable "
                                     "only for gamma with a causal maximum or finite I+, and T4 shows it fails for this class's "
                                     "infinite I+ and maximum-free geodesics, so the falsifier is unachievable as written. "
                                     "Non-blocking precision item for the owner, not a class-semantics defect."),
            "superseded_revision": {"sha256": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
                                    "note": "rev12; replaced at 2026-09-12T00:53:20+08:00 by astra-life05-evidence-binding-repair (rev13 delta in the F1 revision log)."},
        },
        "finite_census": census,
        "omega_chain": omega,
        "controls": controls,
        "controls_ok": controls_ok,
        "anchors": anchors,
        "input_pins_pre": pre,
        "input_pins_post": post,
        "drift": drift,
        "f1_measured_sha256": f1_hash,
        "falsifier": ("FALSE if any of: (a) any pinned input sha256 differs between the pre and post scan "
                      "(verdict must read UNMEASURED); (b) a finite transitive preorder with a causal gamma, "
                      "finite or infinite I+, and P_set + not-P_tail is exhibited; (c) the omega-chain model "
                      "violates transitivity/reflexivity, or P_set fails, or some q_j sees a tail; (d) T1 "
                      "fails on any enumerated preorder; (e) the F1 anchor lines no longer carry the extracted "
                      "tokens at the pinned hash. A machine-checked finite witness of P_set + not-P_tail would "
                      "refute T3 and with it the reconciliation."),
        "evidence_refs_intent": [
            "artifacts/worker-076/gform_strictness_reconcile/probe_result.json",
            "schemas/af_wcc_vacuum.yaml#" + (f1_hash[:12] if f1_hash else "UNKNOWN"),
            "artifacts/worker-040/f1_strictness_adjudication/report.json#" + pre.get("artifacts/worker-040/f1_strictness_adjudication/report.json", "MISSING")[:12],
            "artifacts/worker-076/gform_vis_strength/probe_result.json#" + pre.get("artifacts/worker-076/gform_vis_strength/probe_result.json", "MISSING")[:12],
        ],
    }

    out_path = os.path.join(OUT, "probe_result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")

    # SHA256SUMS.txt over the files this probe owns (probe_result.json first).
    own = ["probe_result.json", "probe_strictness_reconcile.py", "README.md"]
    lines = []
    for name in own:
        p = os.path.join(OUT, name)
        if os.path.exists(p):
            lines.append(f"{sha256_file(p)}  {name}")
    with open(os.path.join(OUT, "SHA256SUMS.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(json.dumps({
        "verdict": verdict, "controls_ok": controls_ok, "drift": drift,
        "T1_violations": t1_total, "T2_violations": t2_total, "T3_violations": t3_total,
        "set_not_single": set_not_single,
        "probe_result_sha256": sha256_file(out_path),
        "f1_measured_sha256": f1_hash,
    }, indent=1))


if __name__ == "__main__":
    main()
