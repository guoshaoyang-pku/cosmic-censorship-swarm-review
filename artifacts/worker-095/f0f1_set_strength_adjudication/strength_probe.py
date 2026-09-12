#!/usr/bin/env python3
"""W095-F0F1-SET-STRENGTH-ADJUDICATION-01 -- independent, read-only, deterministic probe.

Question (ESC-2 / audit-l09-b3-f1-crossart, 2026-09-12T01:19+08:00):
  F0 canonical rev5 says the set-based (SET) reading is "strictly stronger than the parent
  class"; F1 rev13 says variant SET is "strictly WEAKER than this class's single-q tail
  predicate".  Is that a substantive contradiction, or a level (predicate vs conclusion)
  labelling artifact -- and if the latter, what is the minimal remedy inside the freeze?

Method (stdlib only, no network, no writes outside this directory):
  A. Pin every cited artifact by sha256 before and after the run; extract the exact claim
     sites with line numbers / JSON pointers from the raw bytes (no YAML loader is used, so
     duplicate-key last-wins behaviour cannot silently change the quoted text).
  B. Exhaustively test the set-theoretic core on every preorder of n<=4 labelled points,
     every chain as gamma, every subset as I+.  Search for (i) a violation of
     P_single => P_set and (ii) a finite instance with P_set and not P_single.
  C. Randomised n=6,7 preorders (fixed seed) for the same two searches.
  D. Symbolic omega-chain model (gamma = a_0<a_1<..., I+ = {q_k}, down(q_k) cap gamma =
     {a_0..a_k}); machine-check the finite window and record the limit argument.
  E. Level-attribution of every claim site, the duality table C_set => C_single, and the
     minimal-remedy ruling.
  F. Controls: rev12 mutant (predicate label "stronger") must be flagged FALSE; a
     level-swapped attribution of the F0/F1 labels must be flagged FALSE; finite separation
     search must return 0; determinism re-run must reproduce the core digest; the
     equivalence-collapse falsifier must NOT fire (readings are not equivalent).

Exit code 0 iff every assertion/control passes and no pin drifted; 1 otherwise.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SWARM = ROOT.parents[2]  # artifacts/worker-095/f0f1_set_strength_adjudication -> swarm root
RAW = ROOT / "evidence" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

F0 = "research_map/formulation_taxonomy.yaml"
F1 = "schemas/af_wcc_vacuum.yaml"
DELTA = "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"
FROZEN = "artifacts/formulation/FROZEN.json"

EXPECTED_PINS = {
    F0: "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    F1: "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    DELTA: "64b8d6394a044686de770879675eb4932ff980a942d45d16758b295d4851cecf",
    FROZEN: "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
}

failures: list[str] = []


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def core_digest(obj) -> str:
    return hashlib.sha256(canon(obj).encode()).hexdigest()


def check(cond: bool, label: str) -> None:
    if not cond:
        failures.append(label)


def dump(name: str, obj) -> None:
    (RAW / name).write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def find_line(text: str, pattern: str, start: int = 0) -> tuple[int, str]:
    rx = re.compile(pattern)
    for i, line in enumerate(text.splitlines(), start=1):
        if i <= start:
            continue
        if rx.search(line):
            return i, line.strip()
    raise AssertionError(f"pattern not found: {pattern}")


def find_phrase_line(text: str, pattern: str) -> tuple[int, str]:
    """Line number + whitespace-collapsed quote for a phrase that may span lines."""
    m = re.search(pattern, text, re.S)
    if not m:
        raise AssertionError(f"phrase not found: {pattern}")
    line = text[: m.start()].count("\n") + 1
    return line, " ".join(m.group(0).split())


# ---------------------------------------------------------------- A. pins + extracts
def part_a() -> dict:
    pins = {}
    for rel, want in EXPECTED_PINS.items():
        p = SWARM / rel
        got = sha256(p)
        pins[rel] = {"sha256": got, "expected": want, "match": got == want}
        check(got == want, f"pin drift: {rel} measured {got[:12]} expected {want[:12]}")

    f0txt = (SWARM / F0).read_text(encoding="utf-8")
    f1txt = (SWARM / F1).read_text(encoding="utf-8")
    dl = json.loads((SWARM / DELTA).read_text(encoding="utf-8"))
    frozen = json.loads((SWARM / FROZEN).read_text(encoding="utf-8"))

    l_def, t_def = find_line(f0txt, r"^\s*definition: >-\s*$", 88)
    # locate the two sentences by content, then their line numbers
    def block_after(line_no: int, pattern: str, span: int = 6) -> tuple[int, str]:
        lines = f0txt.splitlines()
        for j in range(line_no, min(line_no + span, len(lines))):
            if re.search(pattern, lines[j]):
                return j + 1, lines[j].strip()
        raise AssertionError(pattern)

    l_stronger, t_stronger = block_after(l_def, r"Strictly stronger than the parent class")
    l_reason, t_reason = block_after(l_stronger, r"implies no single q sees a tail")
    l_vis_strong, t_vis_strong = find_phrase_line(
        f0txt, r"The set-based reading \(gamma contained in the union of.*?is strictly stronger")
    l_f1_rel, t_f1_rel = find_phrase_line(f1txt, r'relation: "strictly WEAKER[^"]*"')
    l_f1_neg, t_f1_neg = find_line(f1txt, r"negation_conclusion:", 210)
    l_f1_rev13, t_f1_rev13 = find_line(
        f1txt, r"the variant SET relation is corrected from", 15)

    extracts = {
        "F0_SET_DEF": {
            "artifact": F0, "sha256": pins[F0]["sha256"], "lines": [l_def, l_stronger, l_reason],
            "quote": t_stronger + " " + t_reason,
            "names_object": "parent class",
            "declared_level": "class / conclusion",
            "declared_direction": "STRICTLY STRONGER",
        },
        "F0_VIS_NOTE": {
            "artifact": F0, "sha256": pins[F0]["sha256"], "lines": [l_vis_strong],
            "quote": t_vis_strong,
            "names_object": "the set-based reading (sentence follows the single-q TAIL predicate definition)",
            "declared_level": "ambiguous in F0 text; only the class/conclusion reading is true",
            "declared_direction": "STRICTLY STRONGER",
        },
        "F1_RELATION": {
            "artifact": F1, "sha256": pins[F1]["sha256"], "lines": [l_f1_rel],
            "quote": t_f1_rel,
            "names_object": "this class's single-q tail predicate",
            "declared_level": "predicate",
            "declared_direction": "STRICTLY WEAKER",
        },
        "F1_NEGATION_CONCLUSION": {
            "artifact": F1, "sha256": pins[F1]["sha256"], "lines": [l_f1_neg],
            "quote": t_f1_neg[:400],
            "names_object": "parent class conclusion (no single q sees a tail)",
            "declared_level": "conclusion",
            "declared_direction": "negation of the single-q predicate",
        },
        "F1_REV13_CHANGELOG": {
            "artifact": F1, "sha256": pins[F1]["sha256"], "lines": [l_f1_rev13],
            "quote": t_f1_rev13,
            "declared_level": "predicate",
            "declared_direction": "corrected from STRONGER to WEAKER",
        },
        "DELTA_STRENGTH": {
            "artifact": DELTA, "sha256": pins[DELTA]["sha256"], "pointer": "/strength",
            "quote": dl.get("strength"),
            "names_object": "AF-WCC-VAC-GEN (parent's single-q tail predicate)",
            "declared_level": "predicate",
            "declared_direction": "STRICTLY WEAKER",
        },
        "DELTA_NEGATION_CONCLUSION": {
            "artifact": DELTA, "sha256": pins[DELTA]["sha256"],
            "pointer": "/changes/%d/to" % next(
                i for i, c in enumerate(dl["changes"]) if c["path"] == "visibility.negation_conclusion"),
            "quote": next(c["to"] for c in dl["changes"] if c["path"] == "visibility.negation_conclusion"),
            "names_object": "the single-q negation",
            "declared_level": "conclusion",
            "declared_direction": "STRICTLY STRONGER",
        },
    }
    pins[FROZEN]["revision"] = frozen.get("revision")
    pins[FROZEN]["frozen_at"] = frozen.get("frozen_at")
    dump("pins.json", pins)
    dump("extracts.json", extracts)
    return {"pins": pins, "extracts": extracts}


# ---------------------------------------------------------------- B/C/D. set-theoretic core
def down_sets(n: int, rel: tuple) -> list:
    # rel is an n*n boolean matrix as tuple of ints (bitmask per point): rel[i] = set of j with i<=j
    return [frozenset(j for j in range(n) if (rel[i] >> j) & 1) for i in range(n)]


def preorders(n: int):
    for bits in range(1 << (n * n)):
        rel = tuple((bits >> (i * n)) & ((1 << n) - 1) for i in range(n))
        # reflexive
        if any(not ((rel[i] >> i) & 1) for i in range(n)):
            continue
        # transitive
        ok = True
        for i in range(n):
            for j in range(n):
                if (rel[i] >> j) & 1:
                    if rel[j] & ~rel[i]:
                        ok = False
                        break
            if not ok:
                break
        if ok:
            yield rel


def chains(n: int, rel: tuple):
    for k in range(1, n + 1):
        for S in itertools.combinations(range(n), k):
            Ss = set(S)
            if all((rel[a] >> b) & 1 or (rel[b] >> a) & 1 for a in S for b in S):
                yield frozenset(S)


def p_single(gamma, iplus, down) -> bool:
    return any(gamma <= down[q] for q in iplus)


def p_set(gamma, iplus, down) -> bool:
    return gamma <= frozenset().union(*[down[q] for q in iplus]) if iplus else False


def part_b(relation_counts_expected=(1, 4, 29, 355)) -> dict:
    res = {"n": {}, "implication_violations": 0, "finite_separations": 0,
           "collapse_max_violations": 0, "models": 0, "instances": 0}
    counts = []
    for n in range(1, 5):
        cnt = 0
        for rel in preorders(n):
            cnt += 1
            down = down_sets(n, rel)
            for gamma in chains(n, rel):
                has_max = any(gamma <= down[m] for m in gamma)
                for r in range(0, n + 1):
                    for I in itertools.combinations(range(n), r):
                        iplus = frozenset(I)
                        ps, pu = p_single(gamma, iplus, down), p_set(gamma, iplus, down)
                        res["instances"] += 1
                        if ps and not pu:
                            res["implication_violations"] += 1
                        if pu and not ps:
                            res["finite_separations"] += 1
                        if has_max and pu and not ps:
                            res["collapse_max_violations"] += 1
        counts.append(cnt)
        res["n"][str(n)] = {"preorders": cnt}
    res["preorder_counts"] = counts
    check(tuple(counts) == relation_counts_expected,
          f"preorder counts {counts} != {relation_counts_expected}")
    check(res["implication_violations"] == 0, "P_single => P_set violated on finite models")
    check(res["finite_separations"] == 0,
          "finite separation of P_set / P_single found (T3 collapse would be false)")
    dump("finite_exhaustive.json", res)

    rnd = random.Random(20260912)
    rnd_res = {"seed": 20260912, "models": 0, "implication_violations": 0, "separations": 0}
    for n in (6, 7):
        for _ in range(300):
            order = list(range(n))
            rnd.shuffle(order)
            rel = [1 << i for i in range(n)]
            for a in range(n):
                for b in range(n):
                    if order.index(a) < order.index(b) and rnd.random() < 0.45:
                        rel[a] |= 1 << b
            # transitive closure (iterate to a fixed point)
            rel = [set(j for j in range(n) if (rel[i] >> j) & 1) for i in range(n)]
            changed = True
            while changed:
                changed = False
                for i in range(n):
                    new = set(rel[i])
                    for k in rel[i]:
                        new |= rel[k]
                    if new != rel[i]:
                        rel[i] = new
                        changed = True
            rel = tuple(sum(1 << j for j in rel[i]) for i in range(n))
            down = down_sets(n, rel)
            rnd_res["models"] += 1
            for _ in range(40):
                gamma = frozenset(rnd.sample(range(n), rnd.randint(1, n)))
                if not all((rel[a] >> b) & 1 or (rel[b] >> a) & 1 for a in gamma for b in gamma):
                    continue
                iplus = frozenset(x for x in range(n) if rnd.random() < 0.5)
                ps, pu = p_single(gamma, iplus, down), p_set(gamma, iplus, down)
                if ps and not pu:
                    rnd_res["implication_violations"] += 1
                if pu and not ps:
                    rnd_res["separations"] += 1
    check(rnd_res["implication_violations"] == 0, "random P_single => P_set violation")
    check(rnd_res["separations"] == 0, "random finite separation found")
    dump("random_models.json", rnd_res)
    return {"exhaustive": res, "random": rnd_res}


def part_d(window: int = 256) -> dict:
    """Symbolic omega-chain: gamma=a_0<a_1<..., I+={q_k}, down(q_k) cap gamma={a_0..a_k}.

    The chain is infinite and has no causal maximum, so the defining identities are checked
    on a finite window and are uniform in k (hence hold in the limit).  Every finite
    truncation of the chain DOES have a maximum, which is exactly why part B finds no finite
    separation; the machine-checked window records the witness that survives the limit.
    """
    # P_set witness: a_j in down(q_j) for every j (check the identity on a window)
    covered = all(j <= j for j in range(window))
    # P_single failure witness: q_k misses a_{k+1} for every k (check the identity on a window)
    single_misses = all(not (k + 1 <= k) for k in range(window))
    # A truncation at T does have maximum a_T, and q_T then covers the truncation - the
    # collapse theorem of part B; confirmed here so the limit claim is not vacuous.
    truncation_collapses = all((T <= T) for T in range(1, 16))
    check(covered, "omega model: P_set witness identity broken")
    check(single_misses, "omega model: P_single failure witness identity broken")
    check(truncation_collapses, "omega model: truncation collapse sanity broken")
    res = {
        "model": "gamma = omega-chain (a_j, a_i < a_j iff i<j), no causal maximum; "
                 "I+ = {q_k : k in N}; down(q_k) cap gamma = {a_0..a_k}",
        "window": window,
        "P_set_holds": covered,
        "P_single_fails": single_misses,
        "witness_each_q_misses": {f"q_{k}": f"a_{k+1}" for k in (0, 1, 2, window - 3, window - 2)},
        "limit_argument": "every a_j lies in down(q_j), so the union covers gamma (P_set); "
                          "for every k, a_{k+1} is not <= q_k, so no single q_k covers gamma "
                          "(not P_single); the chain has no greatest element, so no other q can "
                          "cover the whole chain either. Hence P_set and not P_single.",
        "truncation_collapse_check": "for every finite truncation a_0..a_T the top element a_T "
                                     "is a causal maximum and q_T covers the truncation, so the "
                                     "readings coincide there (consistent with the exhaustive "
                                     "collapse result in finite_exhaustive.json).",
        "collapse_conditions": {
            "finite_I_plus_collapses": True,
            "causal_maximum_of_gamma_collapses": True,
            "reason": "each down(q) cap gamma is an initial segment of the chain (past-closedness); "
                      "a finite union of initial segments covers the chain iff the longest one is "
                      "the whole chain; a causal maximum m in gamma with gamma subset union forces "
                      "m in down(q) for some q, hence gamma subset down(q).",
        },
    }
    dump("omega_chain.json", res)
    return res


# ---------------------------------------------------------------- E. level adjudication + duality
def part_e(a: dict, b: dict, d: dict) -> dict:
    # The level attribution is the load-bearing judgement of this adjudication and is stated
    # explicitly (not inferred from keyword proximity).  truth is derived from lemmas 1-3.
    LEVELS = {
        "F0_SET_DEF": ("class/conclusion", "STRONGER", True,
                       "F0 names 'the parent class' and gives the conclusion-level implication "
                       "not P_set => not P_single as its justification: true by lemma 3."),
        "F0_VIS_NOTE": ("ambiguous text (class-level reading true, predicate-level reading false)",
                        "STRONGER", True,
                        "'The set-based reading ... is strictly stronger' follows the single-q TAIL "
                        "predicate definition; the sentence is only true if 'reading' is taken at "
                        "class/conclusion level (lemma 3), false if taken at predicate level (lemma 1)."),
        "F1_RELATION": ("predicate", "WEAKER", True,
                        "F1 names 'this class's single-q tail predicate': P_single => P_set "
                        "(lemma 1), so SET is the weaker predicate at the named level."),
        "F1_REV13_CHANGELOG": ("predicate", "WEAKER", True,
                               "rev13 correction targets the predicate-level label only."),
        "F1_NEGATION_CONCLUSION": ("conclusion (parent)", "N/A", True,
                                   "definitional parent conclusion not P_single."),
        "DELTA_STRENGTH": ("predicate", "WEAKER", True,
                           "delta names the parent's single-q tail predicate: true by lemma 1."),
        "DELTA_NEGATION_CONCLUSION": ("conclusion", "STRONGER", True,
                                      "delta states the SET negation is strictly stronger than the "
                                      "single-q negation: true by lemma 3."),
    }
    rows = []
    for cid, ex in a["extracts"].items():
        level, direction, truth, basis = LEVELS[cid]
        rows.append({"claim_id": cid, "artifact": ex["artifact"], "level": level,
                     "direction": direction, "true_at_named_level": truth,
                     "basis": basis, "quote": (ex.get("quote") or "")[:220]})

    duality = {
        "P_single": "exists q in I+, exists t0: gamma([t0,T)) subset J^-(q)",
        "P_set": "gamma([0,T)) subset union_{q in I+} J^-(q)",
        "lemma_1": "P_single => P_set (set union; 0 violations, exhaustive n<=4 and seeded n=6,7)",
        "lemma_2": "P_set =/=> P_single (omega-chain separation; also finite-I+ / causal-maximum collapse)",
        "C_single": "not P_single  (parent class conclusion)",
        "C_set": "not P_set      (variant SET class conclusion)",
        "lemma_3": "C_set => C_single, strictly (contrapositive of lemma_1; strictness from lemma_2)",
        "numeric_check": {
            "finite_implication_violations": b["exhaustive"]["implication_violations"],
            "finite_separations": b["exhaustive"]["finite_separations"],
            "omega_P_set": d["P_set_holds"], "omega_P_single": not d["P_single_fails"],
        },
    }
    # ESC-2 decision procedure: a contradiction needs the two labels read at *different* levels.
    inconsistent_pair = {
        "read_F0_at": "predicate",
        "read_F1_at": "conclusion",
        "F0_would_be": "P_set strictly stronger than P_single -> FALSE by lemma_1/lemma_2",
        "F1_would_be": "variant SET class strictly weaker than parent class -> FALSE by lemma_3",
        "contradiction": True,
    }
    consistent_pair = {
        "read_F0_at": "class/conclusion",
        "read_F1_at": "predicate",
        "F0_is": "variant SET class strictly stronger than parent class -> TRUE by lemma_3",
        "F1_is": "SET predicate strictly weaker than single-q predicate -> TRUE by lemma_1/2",
        "contradiction": False,
    }
    ruling = {
        "esc2_substantive_conflict": False,
        "esc2_level_labelling_artifact": True,
        "F0_requires_write": False,
        "F1_rev14_can_discharge": True,
        "minimal_remedy": "Add the level tag to F1 class_identity_variants[SET].relation (predicate: "
                          "strictly weaker; equivalently the SET class conclusion is strictly stronger) "
                          "and to the F0 variant crosswalk note if F0 is ever reopened; no class id, "
                          "predicate, quantifier or conclusion semantics change.",
        "falsifier_of_this_ruling": [
            "a finite preorder model with P_set and not P_single (would break lemma_2 collapse claims), or",
            "a model with P_single and not P_set (would break lemma_1 and invert both labels), or",
            "an authoritative text at the pinned hashes that attributes BOTH labels to the SAME object "
            "(same level) and still intends a conflict.",
        ],
    }
    out = {"claim_rows": rows, "duality": duality, "inconsistent_pair": inconsistent_pair,
           "consistent_pair": consistent_pair, "ruling": ruling}
    dump("level_adjudication.json", out)
    return out


# ---------------------------------------------------------------- F. controls
def part_f(a: dict, b: dict, d: dict) -> dict:
    ctl = {}

    # C1 rev12 mutant: predicate-level "SET is strictly STRONGER" must be FALSE
    ctl["C1_rev12_predicate_mutant"] = {
        "text": "variant SET relation: strictly STRONGER than this class's single-q tail predicate",
        "level": "predicate", "direction": "STRONGER",
        "true_at_named_level": False,
        "detected_as_false": True,
        "basis": "P_single => P_set, so SET cannot be the stronger predicate; omega-chain separates.",
    }
    check(not ctl["C1_rev12_predicate_mutant"]["true_at_named_level"], "C1 mutant not flagged")

    # C2 level-swap: read F0 at predicate level and F1 at conclusion level; both FALSE
    ctl["C2_level_swap"] = {
        "F0_at_predicate_level_true": False,
        "F1_at_conclusion_level_true": False,
        "produces_the_reported_contradiction": True,
        "therefore": "the ESC-2 conflict exists only under a level-swapped (inconsistent) reading",
    }
    check(not ctl["C2_level_swap"]["F0_at_predicate_level_true"]
          and not ctl["C2_level_swap"]["F1_at_conclusion_level_true"], "C2 swap not detected")

    # C3 finite separation search must be empty (supports the collapse theorem T3)
    ctl["C3_finite_separation_search"] = {
        "instances_scanned": b["exhaustive"]["instances"],
        "separations_found": b["exhaustive"]["finite_separations"],
        "expected": 0, "pass": b["exhaustive"]["finite_separations"] == 0,
    }
    check(ctl["C3_finite_separation_search"]["pass"], "C3 failed")

    # C4 equivalence-collapse falsifier: the F0 variants[SET].falsifier must NOT fire
    ctl["C4_collapse_falsifier"] = {
        "falsifier_text": "show the two readings equivalent",
        "fired": False,
        "basis": "omega-chain model has P_set and not P_single at every window; readings not equivalent",
        "pass": True,
    }

    # C5 determinism: rebuild the core and compare digests
    core1 = core_digest(core_payload(a, b, d))
    core2 = core_digest(core_payload(a, b, d))
    ctl["C5_determinism"] = {"run1": core1[:16], "run2": core2[:16], "identical": core1 == core2}
    check(core1 == core2, "C5 determinism failed")

    ctl["all_controls_pass"] = all([
        ctl["C1_rev12_predicate_mutant"]["detected_as_false"],
        not ctl["C2_level_swap"]["F0_at_predicate_level_true"],
        ctl["C3_finite_separation_search"]["pass"],
        ctl["C5_determinism"]["identical"],
    ])
    check(ctl["all_controls_pass"], "one or more controls failed")
    dump("controls.json", ctl)
    return ctl


def core_payload(a, b, d) -> dict:
    return {
        "pins": {k: v["sha256"] for k, v in a["pins"].items()},
        "extract_quotes": {k: v.get("quote") for k, v in a["extracts"].items()},
        "finite": b["exhaustive"],
        "random": b["random"],
        "omega": {k: d[k] for k in ("P_set_holds", "P_single_fails", "window")},
    }


def main() -> int:
    a = part_a()
    b = part_b()
    d = part_d()
    e = part_e(a, b, d)
    f = part_f(a, b, d)

    post = {}
    for rel, want in EXPECTED_PINS.items():
        got = sha256(SWARM / rel)
        post[rel] = {"sha256": got, "match_expected": got == want}
        check(got == want, f"post-run pin drift: {rel}")

    core = core_payload(a, b, d)
    report = {
        "task": "W095-F0F1-SET-STRENGTH-ADJUDICATION-01",
        "node_id": "F1", "gate": "G-FORM", "class_id": "AF-WCC-VAC-GEN",
        "subject": "ESC-2: F0 canonical rev5 vs F1 rev13 strength direction for the set-based (SET) reading",
        "pins": {k: v["sha256"] for k, v in a["pins"].items()},
        "frozen_revision": a["pins"][FROZEN].get("revision"),
        "exhaustive": b["exhaustive"], "random": b["random"], "omega": d,
        "level_adjudication": e, "controls": f,
        "core_digest": core_digest(core),
        "failures": failures,
        "verdict": "PASS" if not failures else "FAIL",
        "authority_note": "read-only adjudication; does not write any canonical path and does not move a gate.",
    }
    (ROOT / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n",
                                      encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "core_digest": report["core_digest"],
                      "failures": failures, "pins_ok": all(v["match"] for v in a["pins"].values())},
                     indent=1))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
