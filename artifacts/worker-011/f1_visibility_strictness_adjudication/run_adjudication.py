#!/usr/bin/env python3
"""W011-F1-VIS-STRICT-01 - independent adjudication of the F1 rev12 visibility
strictness claim, class AF-WCC-VAC-GEN.

Question under test (frozen bytes schemas/af_wcc_vacuum.yaml#cce9c60146d6):
  domains.D5.definition (L72) asserts that whole-curve single-q containment
  gamma([0,T)) subset J^-(q) is "strictly STRONGER" than the class's tail
  predicate  exists t0 in [0,T): gamma([t0,T)) subset J^-(q); and
  visibility.definition (L213) asserts that the whole-curve reading "would
  misclassify a geodesic that starts in the exterior and ends inside the
  black-hole region".

Method (read-only on canonical artifacts):
  1. exact text extraction at the pinned hash + before/after drift guard;
  2. formal lemma with proof (past-closure concatenation);
  3. exhaustive enumeration of EVERY reflexive+transitive causal relation
     (preorder) on n <= 5 points, every causal chain, every q;
  4. fixed-seed sampled preorders at n = 6,7,8;
  5. teeth controls: geodesic-only (non-past-closed) J^-, non-causal sequences,
     and the prior blocker's recorded witness reproduced arithmetically;
  6. audit of the cited support (W037V2-F1 withdrawal) and of the accepting
     reviews' coverage of this sentence;
  7. combinatorial escaping-q model showing why SET-variant strictness (L233)
     is NOT adjudicated here and cannot be settled by finite chains.

Writes only artifacts/worker-011/f1_visibility_strictness_adjudication/report.json.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "artifacts/worker-011/f1_visibility_strictness_adjudication"
CST = timezone(timedelta(hours=8))

F1 = ROOT / "schemas/af_wcc_vacuum.yaml"
TAX = ROOT / "research_map/formulation_taxonomy.yaml"
W037 = ROOT / "artifacts/worker-037/f1_visibility_equivalence_adjudication/report.json"
W061 = ROOT / "artifacts/worker-061/f1_rev12_gate/REVIEW.json"
R040 = ROOT / "reviews/F1-review-040-rev12.json"
R088 = ROOT / "reviews/F1-review-088-rev12.json"

PIN_F1 = "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"
PIN_TAX = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"

TASK_ID = "W011-F1-VIS-STRICT-01"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# --------------------------------------------------------------------------
# 1. exact text extraction
# --------------------------------------------------------------------------
def extract_text_claims() -> dict:
    lines = F1.read_text(encoding="utf-8").splitlines()
    needles = {
        "D5_strictness_sentence": "strictly STRONGER and is NOT the predicate of this class",
        "visibility_misclassification_sentence": "would misclassify a geodesic that starts in the exterior",
        "withdrawn_confirmation_citation": "independently confirmed by worker-037 W037V2-F1",
        "operative_tail_clause": "the TAIL gamma([t0,T)) is contained in J^-(q) intersect M",
        "set_variant_strictness": "strictly STRONGER than this class's single-q tail predicate",
    }
    out = {}
    for name, needle in needles.items():
        hits = [(i + 1, ln.strip()) for i, ln in enumerate(lines) if needle in ln]
        out[name] = {
            "needle": needle,
            "present": bool(hits),
            "line_numbers": [h[0] for h in hits],
            "quoted": [h[1][:400] for h in hits],
        }
    return out


# --------------------------------------------------------------------------
# 2. formal lemma (recorded, not machine-proved)
# --------------------------------------------------------------------------
LEMMA = {
    "id": "LEMMA-W011-1",
    "statement": (
        "Let (M,g) be a spacetime with causal relation preceq, J^-(q) = {p in M : p preceq q} "
        "the standard causal past (hence past-closed: p' preceq p in J^-(q) implies p' in J^-(q)), "
        "gamma: [0,T) -> M a future-directed causal curve, and q in M. Then for every t0 in [0,T): "
        "gamma([t0,T)) subset J^-(q)  <=>  gamma([0,T)) subset J^-(q). "
        "Equivalently: single-q tail containment and single-q whole-curve containment are EQUIVALENT; "
        "neither is strictly stronger."
    ),
    "proof": [
        "(=>) Assume gamma([t0,T)) subset J^-(q). Fix t < t0. Since gamma is future-directed causal, "
        "gamma(t) preceq gamma(t0). Since gamma(t0) in J^-(q) and J^-(q) is past-closed, gamma(t) in J^-(q). "
        "Hence gamma([0,t0]) subset J^-(q); together with the tail assumption gamma([0,T)) subset J^-(q).",
        "(<=) Trivial: gamma([t0,T)) subset gamma([0,T)) subset J^-(q).",
        "The converse uses only past-closure of J^-(q), which is part of the standard definition of the "
        "causal past (concatenation of a causal curve from p' to p with one from p to q is causal). "
        "No geodesic, inextendibility, or finite-affine-length hypothesis is used, so the equivalence "
        "holds a fortiori for the schema's D4 class.",
    ],
    "strength": "elementary; the only non-definitional input is transitivity of causal precedence",
    "escape_hatch": (
        "If J^-(q) is redefined as a NON-past-closed set (e.g. only points joined to q by a single causal "
        "geodesic segment, so transitivity across a corner fails), the equivalence can fail and the "
        "strictness claim becomes true. The schema does not declare such a reading: it writes 'the causal "
        "past J^-(q)' (L72), 'causal relation' (witness_protocol step 4), and J^-(q) as the standard past "
        "in D5. Control C1 measures the divergence under the non-past-closed reading."
    ),
}


# --------------------------------------------------------------------------
# 3-5. machine model check
# --------------------------------------------------------------------------
def transitivity_ok(rows: list[int], n: int) -> bool:
    for i in range(n):
        ri = rows[i]
        for j in range(n):
            if (ri >> j) & 1 and (rows[j] & ~ri):
                return False
    return True


def enumerate_preorders(n: int):
    """Every reflexive+transitive relation on n labelled points (exhaustive)."""
    pairs = [(i, j) for i in range(n) for j in range(n) if i != j]
    m = len(pairs)
    for mask in range(1 << m):
        rows = [1 << i for i in range(n)]
        mm = mask
        k = 0
        while mm:
            if mm & 1:
                i, j = pairs[k]
                rows[i] |= 1 << j
            mm >>= 1
            k += 1
        if transitivity_ok(rows, n):
            yield rows


def random_preorders(n: int, count: int, seed: int):
    rng = random.Random(seed)
    for _ in range(count):
        rows = [1 << i for i in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j and rng.random() < 0.28:
                    rows[i] |= 1 << j
        changed = True
        while changed:  # transitive closure
            changed = False
            for i in range(n):
                for j in range(n):
                    if (rows[i] >> j) & 1:
                        new = rows[i] | rows[j]
                        if new != rows[i]:
                            rows[i] = new
                            changed = True
        yield rows


def down_masks(rows: list[int], n: int) -> list[int]:
    full = (1 << n) - 1
    dm = [0] * n
    for q in range(n):
        m = 1 << q
        for p in range(n):
            if (rows[p] >> q) & 1:
                m |= 1 << p
        dm[q] = m & full
    return dm


def geodesic_only_masks(rows: list[int], n: int, dm: list[int] | None = None) -> list[int]:
    """Cover-based 'single causal geodesic segment' reachability (NOT past-closed)."""
    if dm is None:
        dm = down_masks(rows, n)

    def strict_below(x, y):
        return bool((rows[x] >> y) & 1) and not bool((rows[y] >> x) & 1)

    gm = [0] * n
    for q in range(n):
        m = 1 << q
        for p in range(n):
            if p == q or not strict_below(p, q):
                continue
            covered = not any(
                r != p and r != q and strict_below(p, r) and strict_below(r, q)
                for r in range(n)
            )
            if covered:
                m |= 1 << p
        gm[q] = m
    return gm


def causal_chains(rows: list[int], n: int, past_masks: list[int] | None = None):
    """All totally ordered subsets, emitted in causal order (past -> future).

    The sort key is the number of elements STRICTLY BELOW x, i.e. the size of
    J^-(x) \\ {x}; rows[] holds futures (x preceq j), so the past masks must be
    supplied (or computed) for a correct ascending sort.
    """
    if past_masks is None:
        past_masks = down_masks(rows, n)
    for sub in range(1, 1 << n):
        elems = [i for i in range(n) if (sub >> i) & 1]
        if all(
            ((rows[a] >> b) & 1) or ((rows[b] >> a) & 1)
            for a, b in itertools.combinations(elems, 2)
        ):
            elems.sort(key=lambda x: (bin(past_masks[x] & ~(1 << x)).count("1"), x))
            yield tuple(elems)


def sequences(rows: list[int], n: int):
    """All non-causal sequences: every permutation of every subset of size >= 2."""
    for k in range(2, n + 1):
        for sub in itertools.combinations(range(n), k):
            for perm in itertools.permutations(sub):
                yield perm


def preds(chain, jmask: int):
    whole = all((jmask >> c) & 1 for c in chain)
    tail = any(all((jmask >> c) & 1 for c in chain[i:]) for i in range(len(chain)))
    return whole, tail


def model_check() -> dict:
    exhaustive = {}
    for n in range(1, 6):
        models = chains_checked = evals = tail_not_whole = whole_not_tail = 0
        for rows in enumerate_preorders(n):
            models += 1
            dm = down_masks(rows, n)
            for chain in causal_chains(rows, n, dm):
                chains_checked += 1
                for q in range(n):
                    whole, tail = preds(chain, dm[q])
                    evals += 1
                    if tail and not whole:
                        tail_not_whole += 1
                    if whole and not tail:
                        whole_not_tail += 1
        exhaustive[str(n)] = {
            "models": models,
            "chains": chains_checked,
            "tail_q_evaluations": evals,
            "tail_without_whole": tail_not_whole,
            "whole_without_tail": whole_not_tail,
            "equivalent_on_all": tail_not_whole == 0 and whole_not_tail == 0,
        }
    sampled = {}
    for n, count in ((6, 3000), (7, 2000), (8, 1200)):
        models = chains_checked = evals = tail_not_whole = whole_not_tail = 0
        for rows in random_preorders(n, count, seed=20260912 + n):
            models += 1
            dm = down_masks(rows, n)
            for chain in causal_chains(rows, n, dm):
                chains_checked += 1
                for q in range(n):
                    whole, tail = preds(chain, dm[q])
                    evals += 1
                    if tail and not whole:
                        tail_not_whole += 1
                    if whole and not tail:
                        whole_not_tail += 1
        sampled[str(n)] = {
            "models": models,
            "chains": chains_checked,
            "tail_q_evaluations": evals,
            "tail_without_whole": tail_not_whole,
            "whole_without_tail": whole_not_tail,
            "equivalent_on_all": tail_not_whole == 0 and whole_not_tail == 0,
        }
    return {"exhaustive_preorders_n_le_5": exhaustive, "fixed_seed_sampled": sampled}


def control_geodesic_only() -> dict:
    """Teeth control: same enumeration, J^-(q) replaced by cover reachability."""
    n = 5
    models = evals = divergences = 0
    first_witness = None
    for rows in enumerate_preorders(n):
        models += 1
        dm = down_masks(rows, n)
        gm = geodesic_only_masks(rows, n, dm)
        for chain in causal_chains(rows, n, dm):
            for q in range(n):
                whole, tail = preds(chain, gm[q])
                evals += 1
                if tail and not whole:
                    divergences += 1
                    if first_witness is None:
                        first_witness = {
                            "chain": list(chain),
                            "q": q,
                            "J_minus_q": [i for i in range(n) if (gm[q] >> i) & 1],
                            "tail_holds": tail,
                            "whole_holds": whole,
                        }
    return {
        "n": n,
        "models": models,
        "tail_q_evaluations": evals,
        "tail_without_whole": divergences,
        "teeth": divergences > 0,
        "first_witness": first_witness,
        "reading": (
            "Under a cover-reachability (single geodesic segment) J^-(q), transitivity across a corner "
            "fails, past-closure fails, and the strictness claim becomes true. This is the escape hatch "
            "named in LEMMA-W011-1, not a reading the schema declares."
        ),
    }


def control_non_causal() -> dict:
    n = 4
    models = evals = divergences = 0
    first_witness = None
    for rows in enumerate_preorders(n):
        models += 1
        dm = down_masks(rows, n)
        for seq in sequences(rows, n):
            for q in range(n):
                whole, tail = preds(seq, dm[q])
                evals += 1
                if tail and not whole:
                    divergences += 1
                    if first_witness is None:
                        first_witness = {
                            "sequence": list(seq),
                            "q": q,
                            "J_minus_q": [i for i in range(n) if (dm[q] >> i) & 1],
                        }
    return {
        "n": n,
        "models": models,
        "sequence_q_evaluations": evals,
        "tail_without_whole": divergences,
        "teeth": divergences > 0,
        "first_witness": first_witness,
        "reading": (
            "If the curve hypothesis (gamma causal) is dropped, tail containment no longer implies "
            "whole-curve containment. The schema's D4 supplies the causal hypothesis, so this control "
            "only proves the checker distinguishes the cases."
        ),
    }


def prior_witness_audit() -> dict:
    """Reproduce the recorded strictness witness and test past-closure.

    Universe a < b < q (rows[x] = causal future of x, so a preceq b preceq q).
    Recorded witness J^-(q) = {b} only; P_tail with t0 at b holds, P_whole fails.
    """
    a, b, q = 0, 1, 2
    rows = [
        (1 << a) | (1 << b) | (1 << q),
        (1 << b) | (1 << q),
        (1 << q),
    ]
    chain = (a, b)
    recorded = 1 << b
    rec_whole, rec_tail = preds(chain, recorded)
    standard = down_masks(rows, 3)[q]
    std_whole, std_tail = preds(chain, standard)
    names = ["a", "b", "q"]

    def as_names(mask):
        return [names[i] for i in range(3) if (mask >> i) & 1]

    return {
        "recorded_witness": {
            "universe": ["a", "b"],
            "relations": ["a preceq b", "b preceq q"],
            "gamma": ["a", "b"],
            "J_minus_q_recorded": as_names(recorded),
            "P_tail": rec_tail,
            "P_whole": rec_whole,
            "P_tail_without_whole": rec_tail and not rec_whole,
        },
        "past_closure_violation": {
            "witness": "a preceq b and b in J^-(q) but a not in J^-(q)",
            "violates_past_closure": True,
        },
        "under_standard_past": {
            "J_minus_q": as_names(standard),
            "P_tail": std_tail,
            "P_whole": std_whole,
            "still_a_strictness_witness": (std_tail and not std_whole),
        },
        "conclusion": (
            "The only recorded witness for 'whole-curve is strictly stronger' violates past-closure of "
            "J^-(q) and therefore is not admissible under the schema's declared standard causal past. "
            "Under the standard past both predicates hold (the witness's P_whole becomes true and the "
            "divergence disappears)."
        ),
    }


def escaping_q_model() -> dict:
    """Why SET-variant strictness (L233) is not adjudicated here."""
    N = 10
    down_q = {i: set(range(1, i + 1)) for i in range(1, N + 1)}  # q_i sees p_1..p_i
    chain = list(range(1, N + 1))  # p_1 preceq p_2 preceq ... preceq p_N
    set_holds = all(any(p in down_q[i] for i in down_q) for p in chain)
    tails = [chain[i0:] for i0 in range(len(chain))]
    tail_holds_some_q = any(set(t) <= down_q[i] for t in tails for i in down_q)
    # infinite-limit reading: every q_i sees a FINITE prefix, every tail is infinite
    infinite_tails_seen = "no single q_i contains an infinite tail (each J^-(q_i) is finite)"
    return {
        "model": (
            "points p_1 preceq p_2 preceq ... and boundary points q_i with J^-(q_i) = {p_1..p_i}; "
            "the chain gamma = (p_1, p_2, ...) has no last point in M (non-attained end)"
        ),
        "finite_truncation_N": N,
        "finite_truncation_SET_holds": set_holds,
        "finite_truncation_tail_holds_some_q": tail_holds_some_q,
        "finite_truncation_note": (
            "In every FINITE truncation the last point p_N lies in J^-(q_N), so the one-point tail "
            "{p_N} is contained in a single J^-(q_N): finite model checks degenerate and cannot "
            "separate SET from the single-q tail predicate (last-point trick)."
        ),
        "infinite_limit_note": infinite_tails_seen,
        "scope": (
            "This is a combinatorial consistency model, NOT a spacetime. It shows the SET strictness "
            "claim at L233 is not refuted here (and not machine-settleable by finite chains); its "
            "spacetime realizability remains the open obligation recorded by the schema's own SET "
            "falsifier. Worker-040 A2 left it unadjudicated; this adjudication does the same."
        ),
    }


# --------------------------------------------------------------------------
# 6. attribution / coverage audit
# --------------------------------------------------------------------------
def attribution_audit() -> dict:
    out = {}
    w037 = json.loads(W037.read_text())
    v = w037.get("verdict", {})
    out["worker_037"] = {
        "report_path": str(W037.relative_to(ROOT)),
        "report_sha256": sha(W037),
        "prior_blocker_withdrawal": v.get("prior_blocker_withdrawal"),
        "surviving_defect_nonblocking": v.get("surviving_defect_nonblocking"),
    }
    w061 = json.loads(W061.read_text())
    f01 = next((f for f in w061.get("findings", []) if f.get("id") == "F-01"), {})
    out["worker_061"] = {
        "review_path": str(W061.relative_to(ROOT)),
        "review_sha256": sha(W061),
        "verdict": w061.get("verdict"),
        "score": w061.get("score"),
        "F-01_statement": f01.get("statement"),
        "treats_strictness_sentence_as": (
            "positive repair" if "strictly stronger" in (f01.get("statement") or "") else "not addressed"
        ),
    }
    r040 = json.loads(R040.read_text())
    out["worker_040"] = {
        "review_path": str(R040.relative_to(ROOT)),
        "review_sha256": sha(R040),
        "verdict": r040.get("verdict"),
        "score": r040.get("score"),
        "hard_failure_ids": [h.get("id") for h in r040.get("hard_failures", [])],
        "HF-040-04": next(
            (h for h in r040.get("hard_failures", []) if h.get("id") == "HF-040-04"), None
        ),
    }
    r088_raw = R088.read_text()
    r088 = json.loads(r088_raw)
    out["worker_088"] = {
        "review_path": str(R088.relative_to(ROOT)),
        "review_sha256": sha(R088),
        "verdict": r088.get("verdict"),
        "score": r088.get("score"),
        "probes_strictness_sentence": "strictly STRONGER" in r088_raw,
        "probes_whole_curve_truth": "whole-curve" in r088_raw or "past-clos" in r088_raw,
    }
    return out


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main() -> int:
    f1_before, tax_before = sha(F1), sha(TAX)
    pins_match = f1_before == PIN_F1 and tax_before == PIN_TAX

    text = extract_text_claims()
    models = model_check()
    controls = {
        "C1_geodesic_only_non_past_closed": control_geodesic_only(),
        "C2_non_causal_sequences": control_non_causal(),
    }
    witness = prior_witness_audit()
    witness_check = (
        witness["past_closure_violation"]["violates_past_closure"]
        and witness["recorded_witness"]["P_tail_without_whole"]
        and not witness["under_standard_past"]["still_a_strictness_witness"]
    )
    set_model = escaping_q_model()
    attribution = attribution_audit()

    f1_after, tax_after = sha(F1), sha(TAX)
    drift = f1_before != f1_after or tax_before != tax_after or not pins_match

    all_equiv = all(
        v["equivalent_on_all"] for v in models["exhaustive_preorders_n_le_5"].values()
    ) and all(v["equivalent_on_all"] for v in models["fixed_seed_sampled"].values())
    teeth = controls["C1_geodesic_only_non_past_closed"]["teeth"] and controls[
        "C2_non_causal_sequences"
    ]["teeth"]
    strictness_sentence_present = text["D5_strictness_sentence"]["present"]

    a000798 = {1: 1, 2: 4, 3: 29, 4: 355, 5: 6942}  # preorders on n labelled nodes
    enumeration_matches_oeis = all(
        models["exhaustive_preorders_n_le_5"][str(k)]["models"] == v
        for k, v in a000798.items()
    )
    total_exhaustive_models = sum(
        v["models"] for v in models["exhaustive_preorders_n_le_5"].values()
    )
    total_exhaustive_evals = sum(
        v["tail_q_evaluations"] for v in models["exhaustive_preorders_n_le_5"].values()
    )
    sampled_models = sum(v["models"] for v in models["fixed_seed_sampled"].values())
    sampled_evals = sum(
        v["tail_q_evaluations"] for v in models["fixed_seed_sampled"].values()
    )

    hard = (
        all_equiv
        and teeth
        and strictness_sentence_present
        and text["withdrawn_confirmation_citation"]["present"]
        and enumeration_matches_oeis
        and witness_check
        and not drift
    )

    report = {
        "task_id": TASK_ID,
        "actor": "worker-011",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "node_id": "F1",
        "gate": "G-FORM",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "authority_note": (
            "worker evidence only: this is not a gate verdict, not a node status, not a canonical "
            "artifact edit, and not one of the two accepts a gate requires. No canonical file was "
            "modified by this worker."
        ),
        "pins": {
            str(F1.relative_to(ROOT)): f1_before,
            str(TAX.relative_to(ROOT)): tax_before,
            "expected_F1": PIN_F1,
            "expected_taxonomy": PIN_TAX,
            "pins_match": pins_match,
        },
        "drift_during_run": drift,
        "text_extraction": text,
        "lemma": LEMMA,
        "machine_check": models,
        "controls": controls,
        "prior_witness_audit": witness,
        "set_variant_model": set_model,
        "attribution_audit": attribution,
        "checks_summary": {
            "X1_pins_match": pins_match,
            "X2_no_drift": not drift,
            "X3_strictness_sentence_present_at_hash": strictness_sentence_present,
            "X4_tail_equivalent_to_whole_exhaustive_n_le_5": all(
                v["equivalent_on_all"]
                for v in models["exhaustive_preorders_n_le_5"].values()
            ),
            "X5_tail_equivalent_to_whole_sampled_n_6_8": all(
                v["equivalent_on_all"] for v in models["fixed_seed_sampled"].values()
            ),
            "X6_controls_have_teeth": teeth,
            "X7_recorded_witness_violates_past_closure": witness_check,
            "X8_withdrawn_confirmation_citation_present": text[
                "withdrawn_confirmation_citation"
            ]["present"],
            "X9_accepting_review_061_cites_sentence_as_repair": attribution["worker_061"][
                "treats_strictness_sentence_as"
            ]
            == "positive repair",
            "X10_preorder_counts_match_oeis_A000798": enumeration_matches_oeis,
        },
        "ruling": {
            "verdict_recommendation": "revise",
            "score_recommendation": 3.5,
            "hard_failure": {
                "id": "HF-011-01",
                "severity": "blocking",
                "name": "false_strictness_and_misclassification_claims_for_whole_curve_visibility",
                "finding": (
                    "At schemas/af_wcc_vacuum.yaml#cce9c60146d6, domains.D5.definition (L72) asserts that "
                    "whole-curve single-q containment is 'strictly STRONGER' than the class's tail "
                    "predicate and that it 'is NOT the predicate of this class'; visibility.definition "
                    "(L213) asserts the whole-curve reading 'would misclassify a geodesic that starts in "
                    "the exterior and ends inside the black-hole region'. Under the schema's own declared "
                    "standard causal past J^-(q) (past-closed by definition; witness_protocol step 4: "
                    "'causal relation'), LEMMA-W011-1 proves the two single-q readings are EQUIVALENT: "
                    "tail => whole because gamma([0,t0]) subset J^-(q) whenever gamma(t0) in J^-(q). "
                    "Neither is strictly stronger; the misclassification scenario is impossible. The "
                    f"exhaustive check (all {total_exhaustive_models} preorders on <= 5 points, every "
                    f"causal chain, every q; {total_exhaustive_evals} tail/q evaluations, 0 divergences) "
                    f"plus fixed-seed sampled n=6,7,8 models ({sampled_models} models, {sampled_evals} "
                    "evaluations, 0 divergences) agrees. The only divergence appears in "
                    "the non-past-closed cover-reachability control, a reading the schema does not "
                    "declare."
                ),
                "why_blocking": (
                    "The false sentence sits inside domains.D5.definition and visibility.definition - "
                    "fields named by the G-FORM criterion ('exact quantifiers ... visibility ...') - and "
                    "two reviews (worker-061 accept 4.5 F-01; worker-088 accept 4.0) cite L72 as a "
                    "positive repair. An accept at this hash would certify a false mathematical relation "
                    "at the center of the class's visibility block. Worker-037 recorded the L213 "
                    "misclassification sentence as a non-blocking non-sequitur; this adjudication finds "
                    "the L72 strictness sentence is the same defect stated as a positive mathematical "
                    "claim and therefore blocking."
                ),
                "evidence_refs": [
                    "schemas/af_wcc_vacuum.yaml#L72",
                    "schemas/af_wcc_vacuum.yaml#L213",
                    "schemas/af_wcc_vacuum.yaml#sha256:cce9c60146d6",
                    "artifacts/worker-011/f1_visibility_strictness_adjudication/report.json",
                ],
                "falsifier": (
                    "A witness admissible under D4 with past-closed J^-(q) in which tail containment "
                    "holds and whole-curve containment fails; or schema bytes measuring != cce9c60146d6; "
                    "or an explicit declaration in D4/D5/visibility that J^-(q) is a non-past-closed "
                    "set (e.g. single-geodesic reachability)."
                ),
            },
            "non_blocking_findings": [
                {
                    "id": "F-011-02",
                    "severity": "major",
                    "name": "withdrawn_blocker_cited_as_independent_confirmation",
                    "finding": (
                        "L72 cites 'independently confirmed by worker-037 W037V2-F1'. Worker-037's own "
                        "report (hash recorded in this report) marks W037V2-F1 'WITHDRAWN as a critical "
                        "blocker' because its falsifier fired on the past-closure bridge. A withdrawn "
                        "blocker cannot be independent confirmation of the strictness claim it was "
                        "withdrawn from; the citation must be removed or replaced by the past-closure "
                        "lemma, which supports equivalence, not strictness."
                    ),
                    "evidence_refs": [
                        "artifacts/worker-037/f1_visibility_equivalence_adjudication/report.json"
                    ],
                },
                {
                    "id": "F-011-03",
                    "severity": "advisory",
                    "name": "set_variant_strictness_unproven_and_not_machine_settleable",
                    "finding": (
                        "class_identity_variants SET (L233) asserts it is 'strictly STRONGER than this "
                        "class's single-q tail predicate ... not conversely'. This adjudication does NOT "
                        "contradict that claim: the escaping-q model shows SET strictness is consistent "
                        "when the singular end is not attained, and that finite chain checks degenerate "
                        "to equivalence by the last-point trick. The strictness of SET therefore remains "
                        "an obligation, not a machine-checkable fact; a revision should mark it as such "
                        "rather than assert it flatly. Matches worker-040 A2 (left unadjudicated)."
                    ),
                    "evidence_refs": [
                        "schemas/af_wcc_vacuum.yaml#L233",
                        "reviews/F1-review-040-rev12.json",
                    ],
                },
                {
                    "id": "F-011-04",
                    "severity": "advisory",
                    "name": "accepting_reviews_scope_gap",
                    "finding": (
                        "worker-061's accept F-01 and worker-088's accept treat L72 as a repair; neither "
                        "probe tests the truth of the strictness relation (recorded in attribution_audit). "
                        "Their accepts are not falsified as structural verdicts, but their coverage does "
                        "not extend to this claim, so they do not insulate G-FORM from HF-011-01."
                    ),
                    "evidence_refs": [
                        "artifacts/worker-061/f1_rev12_gate/REVIEW.json",
                        "reviews/F1-review-088-rev12.json",
                    ],
                },
            ],
            "positive_checks": [
                "P-011-01: the operative predicate (quantifiers.formal L47, domains.D5 L72, visibility L213/L215) is the single-q TAIL form, and tail == whole under the standard past; the class's mathematical content is therefore unchanged by the fix.",
                "P-011-02: worker-040 HF-040-04 (false strictness, 86170 comparisons) is independently reproduced here by a different method (exhaustive preorder enumeration, formal lemma).",
                f"P-011-03: worker-037's equivalence result (389 models, 0 divergences) is independently extended to all {total_exhaustive_models} preorders on <= 5 points ({total_exhaustive_evals} evaluations, 0 divergences); the enumerator reproduces the labelled-preorder counts 1,4,29,355,6942 (OEIS A000798), a positive control on the enumeration itself.",
                "P-011-04: the prior blocker's recorded witness is reproduced arithmetically and shown to violate past-closure (b in J^-(q), predecessor a not in J^-(q)).",
            ],
            "minimal_fix": {
                "L72_replace_with": (
                    "pairs (q,t0) with q a point of I+ and t0 in [0,T) such that the tail "
                    "gamma([t0,T)) is contained in the causal past J^-(q) intersected with M. Under the "
                    "standard causal past (J^-(q) past-closed) tail containment is EQUIVALENT to "
                    "whole-curve containment gamma([0,T)) subset J^-(q), since gamma([0,t0]) subset "
                    "J^-(q) whenever gamma(t0) in J^-(q); the class states the tail form because "
                    "visibility is a property of the singular end. No strictness is claimed."
                ),
                "L213_replace_with": (
                    "Visibility is a property of the singular END of the geodesic, so the tail "
                    "formulation is used. Under the standard causal past this is equivalent to "
                    "whole-curve containment (past-closure of J^-(q)); the earlier claim that the "
                    "whole-curve reading would misclassify an exterior-to-black-hole geodesic is "
                    "withdrawn as impossible: the tail hypothesis already forces the whole curve into "
                    "J^-(q)."
                ),
                "L72_citation": "replace 'independently confirmed by worker-037 W037V2-F1' with the past-closure equivalence (LEMMA-W011-1 / worker-037 report).",
                "L233": "mark SET strictness as an unproven obligation with its own falsifier (already present) instead of an asserted relation; no machine check can settle it (F-011-03).",
            },
        },
        "checks_all_pass": hard,
        "falsifier": (
            "A witness admissible under the schema's D4 with the standard past-closed causal past in "
            "which P_tail holds and P_whole fails; or schema bytes != cce9c60146d6; or a recorded "
            "non-past-closed reading of J^-(q) in D4/D5/visibility. Any of these falsifies HF-011-01 "
            "and reinstates the strictness claim."
        ),
        "next_falsifier": (
            "Re-run this script at the next F1 revision. If L72/L213 are rewritten to the equivalence "
            "statement and the withdrawn citation is removed, HF-011-01 and F-011-02 are discharged and "
            "this report becomes advisory; if F1 drifts to a new hash, every binding here is superseded."
        ),
        "limitations": [
            "The lemma is recorded with proof, not formalised in a proof assistant; the machine check is finite-model evidence for its combinatorial core, not a substitute for the proof.",
            "Spacetime-level realizability of the escaping-q SET model is NOT claimed; SET strictness remains an obligation.",
            "This report does not review the remaining F1 content and must not be read as a full-schema verdict.",
        ],
    }

    ART.mkdir(parents=True, exist_ok=True)
    (ART / "report.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({
        "task_id": TASK_ID,
        "pins_match": pins_match,
        "drift": drift,
        "all_equivalent": all_equiv,
        "controls_teeth": teeth,
        "checks_all_pass": hard,
        "hard_failure": report["ruling"]["hard_failure"]["id"],
        "report_sha256": sha(ART / "report.json"),
    }, indent=1))
    return 0 if hard else 1


if __name__ == "__main__":
    raise SystemExit(main())
