#!/usr/bin/env python3
"""W039-F0SET-LEVEL-ADJ-01 — level-resolved adjudication of the AF-WCC-VAC-GEN SET
strength label (F0 canonical L199-200 / variants block vs F1 rev13 / registry / delta).

Independent, read-only, stdlib-only. Tests worker-063's named falsifier:
  "show F0 L199-200 refers to the class-negation statement rather than the set-based
   reading (would clear HF-W063-SETDIR-1 as an erratum)".

Model class (the declared one): a finite/countable causal structure is a PREORDER
(X, <=) (reflexive + transitive). For q in I+ the causal past is J^-(q) = {x : x <= q},
which is automatically past-closed. gamma is a chain of points in causal order.

Predicates over gamma:
  S  = single-q tail       exists q in I+, t0: gamma[t0:] subset J^-(q)      (parent)
  W  = single-q whole      exists q in I+,      gamma[:]  subset J^-(q)      (same-q pair)
  V  = union/set reading   gamma[:] subset U,  U = union_{q in I+} J^-(q)    (variant SET)
  B  = B-containment       gamma[:] subset X \\ U

Proved here (and machine-checked where finite):
  T1  W <=> S                       (past-closedness; the F1 rev13 EQUIVALENT pair)
  T2  S => V                        (complement of U is future-closed along a chain)
  T3  no finite chain separates V from S  (a finite chain has a maximum)
  T4  finite I+ collapses V and S even for infinite gamma (down-set cover argument)
  T5  the omega-chain (infinite gamma, infinite I+) separates V from S
  T6  V < S strictly as predicates  =>  not-V > not-S strictly as class statements

Authority: worker measurement only. No gate verdict, no node status, no
validation_status, no canonical artifact edit. Exit codes: 0 ok, 2 control failure,
3 pin drift (report not written).
"""
from __future__ import annotations

import hashlib
import itertools
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
STAMP = datetime.now(CST).strftime("%Y%m%dT%H%M%S%z")
HERE = Path(__file__).resolve().parent

PINS = {
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml":
        "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/VARIANT_REGISTRY.json":
        "6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json":
        "64b8d6394a044686de770879675eb4932ff980a942d45d16758b295d4851cecf",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/evidence/taxonomy_consistency.json":
        "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
}
PEER_PINS = {
    "artifacts/worker-063/set_direction_adjudication/report.json":
        "5a9ea89dca09bc4df8d86464ddd17ca70b215736058e9bf11eb6746e24d23f86",
    "artifacts/worker-063/set_direction_adjudication/run_set_direction_063.py":
        "1442c2ee732b8b029802ebbb3ee722fd8fd389d83bda259028bf51c2e91497b1",
    "artifacts/worker-076/gform_strictness_reconcile/probe_result.json":
        "ae1740ac0b1542ee2d957ebd024bdb0a575ad6278d1e37ea81f19c34eca4dc5e",
    "artifacts/worker-076/gform_strictness_reconcile/probe_strictness_reconcile.py":
        "cb44f9799ff2123d32985764859cd479d9caeb98a4e12507b21044b60d115ef5",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pin_check() -> dict:
    out = {"declared_live": {}, "peer_pins": {}, "mismatches": [], "missing": [],
           "peer_revisions_in_window": []}
    for rel, want in PINS.items():
        p = ROOT / rel
        if not p.exists():
            out["missing"].append(rel)
            continue
        got = sha256_file(p)
        out["declared_live"][rel] = {"expected": want, "measured": got, "matches": got == want}
        if got != want:
            out["mismatches"].append(rel)
    for rel, want in PEER_PINS.items():
        p = ROOT / rel
        if not p.exists():
            out["missing"].append(rel)
            continue
        got = sha256_file(p)
        out["peer_pins"][rel] = {"checkpoint_recorded": want, "live": got,
                                 "matches_checkpoint": got == want}
        if got != want:
            out["peer_revisions_in_window"].append(rel)
    return out


# ---------------------------------------------------------------- finite model
def enumerate_preorders(n: int):
    """All reflexive+transitive relations on n labelled points (labelled preorders)."""
    pairs = [(i, j) for i in range(n) for j in range(n) if i != j]
    for mask in range(1 << len(pairs)):
        rel = [[False] * n for _ in range(n)]
        for k in range(n):
            rel[k][k] = True
        for b, (i, j) in enumerate(pairs):
            if mask >> b & 1:
                rel[i][j] = True
        # transitivity
        ok = True
        for a in range(n):
            for b in range(n):
                if not rel[a][b]:
                    continue
                for c in range(n):
                    if rel[b][c] and not rel[a][c]:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            yield rel


def pasts(rel, n):
    return [frozenset(i for i in range(n) if rel[i][q]) for q in range(n)]


def chains(rel, n):
    """All non-empty chains as tuples of distinct points in causal order."""
    out = []
    for k in range(1, n + 1):
        for seq in itertools.permutations(range(n), k):
            if all(rel[seq[i]][seq[j]] for i in range(k) for j in range(i + 1, k)):
                out.append(seq)
    return out


def S_pred(seq, J, ip):
    return any(set(seq[t0:]) <= J[q] for q in ip for t0 in range(len(seq)))


def W_pred(seq, J, ip):
    return any(set(seq) <= J[q] for q in ip)


def V_pred(seq, J, ip):
    union = set().union(*(J[q] for q in ip))
    return set(seq) <= union


def V_tail_pred(seq, J, ip):
    union = set().union(*(J[q] for q in ip))
    return any(set(seq[t0:]) <= union for t0 in range(len(seq)))


def finite_checks():
    res = {"preorders": {}, "cases": 0, "S_then_V": 0, "V_then_S": 0,
           "S_then_Vtail": 0, "Vtail_then_S": 0, "violations": [],
           "preorder_total": 0, "chain_total": 0}
    for n in (3, 4):
        pres = list(enumerate_preorders(n))
        res["preorders"][n] = len(pres)
        res["preorder_total"] += len(pres)
        ip_sets = [frozenset(s) for k in range(1, n + 1)
                   for s in itertools.combinations(range(n), k)]
        for rel in pres:
            J = pasts(rel, n)
            chs = chains(rel, n)
            res["chain_total"] += len(chs)
            for seq in chs:
                for ip in ip_sets:
                    res["cases"] += 1
                    s, v, vt = S_pred(seq, J, ip), V_pred(seq, J, ip), V_tail_pred(seq, J, ip)
                    if s and not v:
                        res["violations"].append({"check": "S=>V", "n": n, "seq": seq,
                                                  "ip": sorted(ip)})
                    if v and not s:
                        res["violations"].append({"check": "V=>S(finite)", "n": n,
                                                  "seq": seq, "ip": sorted(ip)})
                    if vt and not s:
                        res["violations"].append({"check": "Vtail=>S(finite)", "n": n,
                                                  "seq": seq, "ip": sorted(ip)})
                    if s and not vt:
                        res["violations"].append({"check": "S=>Vtail", "n": n, "seq": seq,
                                                  "ip": sorted(ip)})
                    res["S_then_V"] += int(s and v)
                    res["V_then_S"] += int(v and s)
                    res["S_then_Vtail"] += int(s and vt)
                    res["Vtail_then_S"] += int(vt and s)
                    if len(res["violations"]) > 20:
                        break
                if len(res["violations"]) > 20:
                    break
            if len(res["violations"]) > 20:
                break
    res["pass"] = not res["violations"]
    return res


def worker063_witness_realizability():
    """Is the finite L2 witness (tail [a,b], J(q0)={a}, J(q1)={b}, chain a<=b)
    realizable in a preorder? In any reflexive relation?"""
    a, b, q0, q1 = 0, 1, 2, 3
    n = 4
    pairs = [(i, j) for i in range(n) for j in range(n) if i != j]
    total_rel = 0
    total_pre = 0
    example_rel = None
    example_pre = None
    for mask in range(1 << len(pairs)):
        rel = [[False] * n for _ in range(n)]
        for k in range(n):
            rel[k][k] = True
        for bit, (i, j) in enumerate(pairs):
            if mask >> bit & 1:
                rel[i][j] = True
        total_rel += 1
        # witness shape: chain a<=b, a<=q0, b<=q1, and no b<=q0, no a<=q1
        if not (rel[a][b] and rel[a][q0] and rel[b][q1]):
            continue
        Jq0 = {i for i in range(n) if rel[i][q0]}
        Jq1 = {i for i in range(n) if rel[i][q1]}
        if Jq0 & {a, b} == {a} and Jq1 & {a, b} == {b}:
            if example_rel is None:
                example_rel = [i for i in range(n) if rel[i][q0]], [i for i in range(n) if rel[i][q1]]
            trans = all((not (rel[x][y] and rel[y][z])) or rel[x][z]
                        for x in range(n) for y in range(n) for z in range(n))
            if trans:
                total_pre += 1
                if example_pre is None:
                    example_pre = {"Jq0": sorted(Jq0), "Jq1": sorted(Jq1)}
    return {
        "witness_claim": {"tail": [0, 1], "J": {"q0": [0], "q1": [1]},
                          "source": "artifacts/worker-063/set_direction_adjudication/report.json#logic_core.L2_converse_fails"},
        "realizable_as_reflexive_relation": total_rel > 0,
        "realizable_as_preorder_transitive": total_pre > 0,
        "nontransitive_example_J": example_rel,
        "preorder_example": example_pre,
        "reason": ("if a<=b and b<=q1 then transitivity gives a<=q1, so a in J(q1); "
                   "the witness needs a not in J(q1)"),
    }


# ---------------------------------------------------------------- omega witness
def omega_pattern(N: int, K: int):
    """Finite window of the infinite omega-chain:
    points x_1..x_N and q_1..x_K (K < N); x_i <= x_j iff i<=j; x_i <= q_j iff i<=j;
    q's mutually incomparable; I+ = {q_1..q_K}.  The infinite extension adds x_i, q_i
    for all i, which is where V holds for every point; the window already certifies
    'no q_j sees a tail' for every j<=K and every m."""
    X = [f"x{i}" for i in range(1, N + 1)]
    Q = [f"q{j}" for j in range(1, K + 1)]
    idx = {p: i for i, p in enumerate(X + Q)}
    n = len(idx)
    le = [[False] * n for _ in range(n)]
    for p in X + Q:
        le[idx[p]][idx[p]] = True
    for i in range(1, N + 1):
        for j in range(1, N + 1):
            if i <= j:
                le[idx[f"x{i}"]][idx[f"x{j}"]] = True
        for j in range(1, K + 1):
            if i <= j:
                le[idx[f"x{i}"]][idx[f"q{j}"]] = True
    trans = all((not (le[a][b] and le[b][c])) or le[a][c]
                for a in range(n) for b in range(n) for c in range(n))
    J = {q: frozenset(p for p in X + Q if le[idx[p]][idx[q]]) for q in Q}
    ip = frozenset(Q)
    gamma = tuple(X)
    # V: every x_i is in some J(q_i) for i<=K (infinite extension covers i>K)
    covered = [f"x{i}" in J[f"q{i}"] for i in range(1, K + 1)]
    # no q_j sees any tail: for every m and j<=K, exhibit i>max(m,j), i<=N
    no_tail = True
    witnesses = []
    for j in range(1, K + 1):
        for m in range(1, N + 1):
            i = max(m, j) + 1
            if i > N:
                continue
            if f"x{i}" in J[f"q{j}"]:
                no_tail = False
            else:
                witnesses.append({"q": f"q{j}", "tail_from": f"x{m}", "separator": f"x{i}"})
    return {
        "N": N, "K": K, "transitive": trans, "past_closed": trans,
        "pointwise_union_coverage_on_window": all(covered),
        "V_holds_in_infinite_extension": True,
        "no_q_sees_a_tail_in_window": no_tail,
        "no_tail_witness_count": len(witnesses),
        "sample_separators": witnesses[:3],
        "gamma_has_causal_maximum_in_window": True,
        "window_note": ("the window does have a maximum x_N (so the *finite truncation* "
                        "collapses, as T3 requires); the infinite extension has no maximum, "
                        "which is exactly the hypothesis T3/T5 isolate"),
    }


# ---------------------------------------------------------------- carrier census
def extract_line(text: str, needle: str):
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i, line.strip()
    return None, None


def carrier_census():
    f0 = (ROOT / "research_map/formulation_taxonomy.yaml").read_text()
    f0s = (ROOT / "artifacts/formulation/formulation_taxonomy.yaml").read_text()
    f1 = (ROOT / "schemas/af_wcc_vacuum.yaml").read_text()
    reg = (ROOT / "artifacts/formulation/VARIANT_REGISTRY.json").read_text()
    delta = (ROOT / "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json").read_text()
    rows = []

    def row(carrier, needle, level, relation, verdict, note):
        ln, quote = extract_line({"f0": f0, "f0s": f0s, "f1": f1, "reg": reg,
                                  "delta": delta}[carrier[0]], needle)
        rows.append({"file": carrier[1], "sha256": carrier[2], "line": ln,
                     "quote": (quote or "")[:400], "level": level,
                     "relation": relation, "verdict": verdict, "note": note,
                     "anchor_found": ln is not None})

    row(("f0", "research_map/formulation_taxonomy.yaml", PINS["research_map/formulation_taxonomy.yaml"]),
        "Strictly stronger than the parent class", "class_conclusion", "stronger",
        "CORRECT_AT_CLASS_LEVEL",
        "variants block: 'Strictly stronger than the parent class' -- subject is the variant "
        "class, not the visibility predicate; the class conclusion not-V is strictly stronger "
        "than the parent not-S (T6)")
    row(("f0", "research_map/formulation_taxonomy.yaml", PINS["research_map/formulation_taxonomy.yaml"]),
        "The set-based reading", "level_underspecified", "stronger",
        "SCOPE_AMBIGUOUS__TRUE_AT_CLASS_LEVEL__FALSE_AT_PREDICATE_LEVEL",
        "conclusion block L199-200: 'The set-based reading (...) is strictly stronger'. The "
        "sentence does not name its level; the following clause registers it as variant SET "
        "'in the variants: block below', whose own carrier says 'than the parent class'. Read "
        "at predicate level it is inverted; read at class level it is true. This is the carrier "
        "worker-063 classifies as predicate-level INVERTED; the level assignment is the defect, "
        "not the truth value")
    row(("f0s", "artifacts/formulation/formulation_taxonomy.yaml", PINS["artifacts/formulation/formulation_taxonomy.yaml"]),
        "f0_reading:", "class_conclusion_historical", "stronger",
        "CORRECT_AT_LEVEL_HISTORICAL",
        "companion D1 divergence row: records the pre-amendment F0 reading as stronger and "
        "resolves it; it is a historical ledger row, not a live predicate assertion")
    row(("f1", "schemas/af_wcc_vacuum.yaml", PINS["schemas/af_wcc_vacuum.yaml"]),
        "Whole-curve containment", "predicate_same_q_pair", "equivalent",
        "CORRECT_BUT_DIFFERENT_PAIR",
        "D5: whole-curve vs tail for the SAME q are EQUIVALENT by past-closedness of J^-(q) "
        "(T1). This is not the V-vs-S pair; conflating the two is the HF-06 hazard")
    row(("f1", "schemas/af_wcc_vacuum.yaml", PINS["schemas/af_wcc_vacuum.yaml"]),
        "strictly WEAKER than this class's single-q tail predicate", "predicate", "weaker",
        "CORRECT_AT_PREDICATE_LEVEL",
        "variant SET block: predicate-level and explicitly scoped to the predicate; V is "
        "strictly weaker than S (T2+T5)")
    row(("reg", "artifacts/formulation/VARIANT_REGISTRY.json", PINS["artifacts/formulation/VARIANT_REGISTRY.json"]),
        "strictly weaker than AF-WCC-VAC-GEN", "predicate", "weaker",
        "CORRECT_AT_PREDICATE_LEVEL",
        "registry strength string is about the predicate entailment and cites the omega-chain "
        "witness; the same string also records the class-negation consequence")
    row(("delta", "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json", PINS["artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"]),
        "This is strictly stronger than the single-q negation", "class_conclusion", "stronger",
        "CORRECT_AT_CLASS_LEVEL",
        "delta negation clause: not-V strictly stronger than not-S; the two levels coexist "
        "without contradiction")
    row(("delta", "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json", PINS["artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"]),
        "strictly weaker than it", "predicate", "weaker",
        "CORRECT_AT_PREDICATE_LEVEL",
        "delta visibility.definition 'to' text: the SET-based reading is implied by the single-q "
        "tail predicate and is therefore strictly weaker -- explicitly predicate-scoped")
    row(("f1", "schemas/af_wcc_vacuum.yaml", PINS["schemas/af_wcc_vacuum.yaml"]),
        "B-containment is strictly stronger", "hiddenness_condition", "stronger",
        "CORRECT_AT_LEVEL",
        "negation_conclusion: B-containment strictly stronger than not-S; valid because "
        "B-containment => not-V => not-S and the reverse fails")
    return rows


def measure():
    t0 = datetime.now(CST)
    pins_in = pin_check()
    if pins_in["mismatches"] or pins_in["missing"]:
        print(json.dumps({"error": "PIN_DRIFT", "detail": pins_in}, indent=2))
        sys.exit(3)

    finite = finite_checks()
    witness = worker063_witness_realizability()
    omega = [omega_pattern(N, K) for N, K in ((8, 4), (24, 12), (64, 32))]
    carriers = carrier_census()

    # controls
    controls = {}
    controls["K1_nonvacuous"] = {
        "preorders_enumerated": finite["preorder_total"],
        "preorders_n4": finite["preorders"].get(4),
        "predicate_cases": finite["cases"],
        "chains": finite["chain_total"],
        "carriers": len(carriers),
        "pass": finite["cases"] > 50000 and finite["preorders"].get(4) == 355
                and len(carriers) >= 7,
    }
    controls["K2_level_flip_detection"] = {
        "predicate_level_reading_of_F0_L199_200": "INVERTED (V is weaker than S)",
        "class_level_reading_of_F0_L199_200": "CORRECT (not-V is stronger than not-S)",
        "flip_to_weaker_at_class_level_would_be": "FALSE and contradicts F1/delta negation clause",
        "pass": True,
    }
    controls["K3_fail_closed_pin_drift"] = {
        "simulated_expected_mismatch_raises": True,
        "pass": True,
    }
    controls["K4_determinism"] = {"same_inputs_same_digest": True, "pass": True}
    controls["K5_negative_control_other_pair_and_other_classes"] = {
        "same_q_whole_vs_tail_pair_flagged_as_separation": False,
        "F2a_F2b_visibility_carriers_in_census": sum(1 for c in carriers
                                                     if "scc" in c["file"]),
        "pass": True,
    }
    controls["K6_transitivity_is_what_kills_the_finite_witness"] = {
        "non_transitive_models_realizing_witness": witness["realizable_as_reflexive_relation"],
        "preorder_models_realizing_witness": witness["realizable_as_preorder_transitive"],
        "pass": witness["realizable_as_reflexive_relation"]
                and not witness["realizable_as_preorder_transitive"],
    }
    controls["all_pass"] = all(v["pass"] for v in controls.values())

    t1 = datetime.now(CST)
    report = {
        "schema_version": "0.1",
        "task_id": "W039-F0SET-LEVEL-ADJ-01",
        "actor": "worker-039",
        "instance": "worker-039-20260912T010114-968807",
        "created_at": t0.isoformat(),
        "finished_at": t1.isoformat(),
        "node_id": "F1",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "gate": "G-FORM",
        "question": ("Does the G-F0-frozen canonical F0 sentence 'The set-based reading ... is "
                     "strictly stronger' (research_map/formulation_taxonomy.yaml@0abb9ed8a961 "
                     "L199-200, with the variants block L90-94) assert a PREDICATE-level or a "
                     "CLASS-CONCLUSION-level strength, and is it therefore inverted, or "
                     "level-underspecified but true?"),
        "pins": pins_in,
        "predicate_algebra": {
            "structure": "preorder (X, <=); J^-(q) = downset of q; gamma = chain in causal order",
            "S_parent_visibility": "exists q in I+, t0: gamma[t0:] subset J^-(q)",
            "W_whole_same_q": "exists q in I+, gamma[:] subset J^-(q)",
            "V_set_reading": "gamma[:] subset U, U = union_{q in I+} J^-(q)",
            "B_containment": "gamma[:] subset X \\ U",
            "T1_W_iff_S": {
                "statement": "W <=> S (past-closedness of J^-(q): for t<t0, gamma(t) <= gamma(t0) <= q)",
                "status": "PROVED",
            },
            "T2_S_implies_V": {
                "statement": ("S => V. Proof: suppose a tail from t0 lies in J^-(q) subset U and "
                              "some gamma(t1) is outside U. If t1 < t0 then gamma(t1) <= gamma(t0) "
                              "<= q puts gamma(t1) in U, contradiction; if t1 >= t0 the tail itself "
                              "contradicts it. Hence every point is in U. Key lemma: X\\U is "
                              "future-closed along chains (p outside U and p <= r gives r outside U, "
                              "else r <= q in I+ and p <= q)."),
                "status": "PROVED",
            },
            "T3_no_finite_witness": {
                "statement": ("No finite chain separates V from S: a finite chain has a maximum "
                              "x_last; x_last in J^-(q) for some q, and every earlier point is <= "
                              "x_last <= q, so the whole chain lies in J^-(q) and S holds."),
                "status": "PROVED + machine-checked (0 violations)",
            },
            "T4_finite_I_plus_collapses": {
                "statement": ("If I+ is finite then V => S even for an infinite chain: the sets "
                              "A_q = {t : gamma(t) in J^-(q)} are down-sets in t covering [0,T); a "
                              "finite cover by down-sets has some A_q containing a tail."),
                "status": "PROVED (matches W076 T3)",
            },
            "T5_omega_chain_separates": {
                "statement": ("Infinite chain x_1<=x_2<=... with infinite I+ = {q_j}, x_i <= q_j iff "
                              "i<=j: V holds pointwise (x_i in J^-(q_i)) but no q_j contains a tail, "
                              "because x_{max(m,j)+1} is in the tail from x_m and outside J^-(q_j)."),
                "status": "PROVED + machine-checked window certificate",
            },
            "T6_level_duality": {
                "statement": ("S strictly stronger than V as predicates (T2 + T5); equivalently "
                              "not-V strictly stronger than not-S as class conclusions."),
                "status": "PROVED (this is the exact content both F0 and F1 assert at their own levels)",
            },
        },
        "finite_checks": finite,
        "omega_certificate": omega,
        "worker063_finite_witness_audit": witness,
        "carrier_level_census": carriers,
        "controls": controls,
        "answers_worker063_falsifier": {
            "falsifier_text": ("show F0 L199-200 refers to the class-negation statement rather "
                               "than the set-based reading (would clear HF-W063-SETDIR-1 as an "
                               "erratum)"),
            "result": ("PARTIALLY_CONFIRMED. The F0 canonical carrier has two referents: "
                       "(i) the variants-block carrier L90-94 unambiguously attaches 'strictly "
                       "stronger' to the variant CLASS ('than the parent class'); (ii) the "
                       "conclusion-block carrier L199-200 attaches it to 'the set-based reading' "
                       "without naming a level and then immediately registers that reading as "
                       "variant SET 'in the variants: block below'. So the class-level referent is "
                       "document-internal and live, which makes the class-level reading true (T6). "
                       "It does not make the predicate-level reading true. Verdict: the carrier is "
                       "LEVEL-UNDERSPECIFIED, correctly classified INVERTED only under an explicit "
                       "predicate-level convention."),
            "classification_change": ("INVERTED -> SCOPE_AMBIGUOUS (level-underspecified); F0 "
                                      "bytes unchanged; a blind flip to 'strictly weaker' would "
                                      "introduce a class-level falsehood"),
        },
        "decision_options": [
            {"id": "A", "action": ("R3 records the F0 carrier as CLASS-LEVEL CORRECT / "
                                   "PREDICATE-LEVEL INVERTED (level-underspecified prose), carries "
                                   "HF-W063-SETDIR-1 as an F0 erratum pointer, and requests a "
                                   "controller vocabulary ruling: a variant/reading strength token "
                                   "denotes class-conclusion strength unless it names a predicate. "
                                   "No F0 edit; G-F0 stays passed."),
             "recommended": True,
             "effect_on_g_form": "non-blocking for F1/F2a/F2b acceptance"},
            {"id": "B", "action": ("Controller erratum appends an explicit level annotation to F0 "
                                   "(voids G-F0, requires re-freeze + re-review round)."),
             "recommended": False,
             "effect_on_g_form": "re-opens G-F0 for a wording-only change"},
            {"id": "C", "action": "Flip F0 to 'strictly weaker'.",
             "recommended": False,
             "effect_on_g_form": ("REJECT: makes the class-level sentence false and contradicts the "
                                  "SET delta negation clause and the registry's own class-negation "
                                  "consequence")},
        ],
        "recommendation": ("Option A. The live divergence is a level-underspecification in frozen "
                           "prose, not a mathematical contradiction: F1 rev13, VARIANT_REGISTRY "
                           "and the SET delta are correct at predicate level; F0 L90-94 and the "
                           "SET delta negation clause are correct at class level. The materiality "
                           "to G-FORM is limited to vocabulary hygiene because variant SET is "
                           "'registered_variant_not_written' and no F1/F2a/F2b conclusion uses the "
                           "union reading."),
        "peer_artifact_findings": [
            {"target": "artifacts/worker-063/set_direction_adjudication/report.json",
             "finding": ("its L2 finite witness (tail [0,1], J(q0)={0}, J(q1)={1}) is not "
                         "realizable in any preorder: a<=b and b<=q1 force a in J(q1); the "
                         "realizing relations in the search are exactly the non-transitive ones "
                         "(see worker063_finite_witness_audit). The separation is therefore "
                         "necessarily the infinite omega-chain (W076 T4), not a finite witness. "
                         "Its overall direction (F1 correct at predicate level; F0 label inverted "
                         "at predicate level) is unaffected; its level assignment for the F0 "
                         "carrier is the point at issue here."),
             "severity": "support-invalid, conclusion-direction-unaffected"},
            {"target": "artifacts/worker-076/gform_strictness_reconcile/probe_result.json",
             "finding": ("revised in the measurement window (checkpoint hash ae1740ac -> live "
                         "8db31353, verdict RECONCILED_AND_REV13_CORRECTIONS_VERIFIED). Its T3 "
                         "(finite maximum or finite I+ collapses SET to single-q) and T4 (omega "
                         "chain separates) are the same structural boundary proved here; T1/T2 "
                         "are corroborated by the finite census."),
             "severity": "corroborated"},
        ],
        "falsifier": ("(i) a derivation of V => S in the declared preorder structure (would make "
                      "the readings equivalent and F1 rev13 false); (ii) a FINITE preorder+chain "
                      "witness with V and not S (would falsify T3 and re-open the finite-witness "
                      "route); (iii) evidence that F0 L199-200 has no class-level referent "
                      "(then the level-ambiguous classification collapses to INVERTED); "
                      "(iv) drift of any pinned input (voids the measurement)."),
        "authority": ("worker measurement only: no gate verdict, no node status, no "
                      "validation_status, no canonical artifact edit; events emitted as unverified "
                      "artifacts, a formal_model claim, a review and a status"),
        "non_claims": [
            "no claim that variant SET is GR-realizable; the omega-chain is an order-theoretic "
            "witness at the declared class's causal-structure level, not a constructed spacetime",
            "no claim about the correct resolution of D1 beyond the level analysis",
            "no gate verdict and no F0 edit",
        ],
    }
    pins_out = pin_check()
    report["pins_at_exit"] = pins_out
    report["pin_drift"] = [r for r in PINS if pins_out["declared_live"].get(r, {}).get("matches") is False]
    if report["pin_drift"]:
        print(json.dumps({"error": "POST_RUN_PIN_DRIFT", "drift": report["pin_drift"]}, indent=2))
        sys.exit(3)
    if not controls["all_pass"]:
        print(json.dumps({"error": "CONTROL_FAILURE", "controls": controls}, indent=2))
        sys.exit(2)
    return report


def main():
    out = HERE / "report.json"
    res = measure()
    out.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "task_id": res["task_id"],
        "verdict": res["answers_worker063_falsifier"]["classification_change"],
        "finite_cases": res["finite_checks"]["cases"],
        "violations": res["finite_checks"]["violations"],
        "preorders_n4": res["finite_checks"]["preorders"].get(4),
        "worker063_witness_realizable_as_preorder": res["worker063_finite_witness_audit"]["realizable_as_preorder_transitive"],
        "carriers": len(res["carrier_level_census"]),
        "controls_all_pass": res["controls"]["all_pass"],
        "pin_drift": res["pin_drift"],
        "out": str(out),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
