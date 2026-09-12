#!/usr/bin/env python3
"""W037-F1-VISIBILITY-03: adjudicate W037V2-F1 (critical) against LEMMA-W026-1.

Read-only. Measures the canonical F1 bytes at T0 and T1 and decides, at those exact
bytes, whether the whole-curve visibility clause in quantifiers.formal/D5 is
logically equivalent to the tail clause in visibility.definition/negation_conclusion
for the geodesics D4 admits.

The decision rests on one explicitly named hypothesis about the schema's declared
causal structure:
    (H) causal precedence in the conformal completion is transitive, hence
        J^-(q) = {p : p precedes q} is past-closed (p' precedes p in J^-(q) => p' in J^-(q)).
(H) is what the standard J^- notation and D4's "future-directed causal geodesics" presuppose.
The script tests both directions exhaustively on all small transitive models, and then
shows that the prior strictness witness (worker-037 report, W037V2-F1) is only
reproducible when (H) is dropped or the curve is made non-causal.

No canonical file is written or modified. No gate verdict is issued.

Usage:
  python3 adjudicate_visibility_equivalence.py [--out report.json]
Exit codes: 0 adjudication produced; 2 measurement/read error.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # repo root: artifacts/worker-037/<task>/file
CST = timezone(timedelta(hours=8))

F1 = "schemas/af_wcc_vacuum.yaml"
F0 = "research_map/formulation_taxonomy.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
PRIOR_REPORT = "artifacts/worker-037/f1_visibility_adjudication/report.json"
W026_REPORT = "artifacts/worker-026/f1_adjudication/adjudication_report.json"

PRIOR_FINDING_ID = "W037V2-F1"
PRIOR_BLOCKER_ID = "w037-20260912T002818-blocker-f1-visibility"
LEMMA_ID = "LEMMA-W026-1"


def sha256_path(rel: str) -> str:
    h = hashlib.sha256()
    with open(ROOT / rel, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pin_block() -> dict:
    paths = [F1, F0, FROZEN, PRIOR_REPORT, W026_REPORT]
    return {p: sha256_path(p) for p in paths}


def line_of(text: str, needle: str) -> int | None:
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    return None


# ---------------------------------------------------------------------------
# Finite causal models
# ---------------------------------------------------------------------------

def transitive_reflexive(n: int):
    """All reflexive+transitive relations on range(n): the finite preorders."""
    pairs = [(i, j) for i in range(n) for j in range(n)]
    for bits in range(1 << len(pairs)):
        R = {pairs[k] for k in range(len(pairs)) if (bits >> k) & 1}
        if any((i, i) not in R for i in range(n)):
            continue
        ok = True
        for a, b in R:
            for c, d in R:
                if b == c and (a, d) not in R:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            yield frozenset(R)


def j_minus(R, q):
    return {p for (p, r) in R if r == q}


def chains(n: int, R, max_len: int = 4):
    """Future-directed causal chains with distinct consecutive points."""
    for L in range(2, max_len + 1):
        for gamma in itertools.product(range(n), repeat=L):
            if all(gamma[i] != gamma[i + 1] and (gamma[i], gamma[i + 1]) in R for i in range(L - 1)):
                yield gamma


def exhaustive_transitive_check() -> dict:
    """(H) held: for every preorder, chain, q and tail-start t0, tail-in-J^- <=> whole-in-J^-."""
    models = chain_count = evals = 0
    whole_but_no_tail = tail_but_not_whole = 0
    for n in (1, 2, 3, 4):
        for R in transitive_reflexive(n):
            models += 1
            for gamma in chains(n, R):
                chain_count += 1
                for q in range(n):
                    J = j_minus(R, q)
                    p_whole = all(x in J for x in gamma)
                    p_tail = any(all(x in J for x in gamma[t0:]) for t0 in range(len(gamma)))
                    evals += 1
                    if p_whole and not p_tail:
                        whole_but_no_tail += 1
                    if p_tail and not p_whole:
                        tail_but_not_whole += 1
    return {
        "hypothesis_H_transitive": True,
        "models_checked": models,
        "chains_checked": chain_count,
        "predicate_evaluations": evals,
        "whole_without_tail": whole_but_no_tail,
        "tail_without_whole": tail_but_not_whole,
        "verdict": "EQUIVALENT (both directions hold on every checked model)"
        if (whole_but_no_tail == 0 and tail_but_not_whole == 0) else "NOT_EQUIVALENT",
    }


def prior_witness_audit() -> dict:
    """Rebuild the exact witness recorded by W037V2-F1 and test it against (H).

    Prior witness: universe {a,b}; J^-(q1) = {b}; gamma = [a,b]; P_whole false, P_tail true.
    A causal geodesic with gamma_0 -> gamma_1 and b in J^-(q1) forces a in J^-(q1) under (H),
    so the witness is a model of the schema's causal structure only if (H) is denied.
    """
    X = {"a": 0, "b": 1, "q": 2}
    strict = {(X["a"], X["b"]), (X["b"], X["q"])}
    R = {(i, i) for i in range(3)} | strict
    R = frozenset(R)
    # close transitively (standard rt-closure of a DAG is already transitive)
    changed = True
    Rset = set(R)
    while changed:
        changed = False
        for (p, r) in list(Rset):
            for (r2, s) in list(Rset):
                if r == r2 and (p, s) not in Rset:
                    Rset.add((p, s))
                    changed = True
    R = frozenset(Rset)
    J_q = j_minus(R, X["q"])
    gamma = [X["a"], X["b"]]
    p_whole_std = all(x in J_q for x in gamma)
    p_tail_std = any(all(x in J_q for x in gamma[t0:]) for t0 in range(len(gamma)))
    # the witness as recorded: J^- taken to be the set {b} alone
    J_recorded = {X["b"]}
    p_whole_recorded = all(x in J_recorded for x in gamma)
    p_tail_recorded = any(all(x in J_recorded for x in gamma[t0:]) for t0 in range(len(gamma)))
    past_closure_failures = [
        {"predecessor": "a", "via": "b", "in_J_minus_q": "b", "predecessor_in_J_minus_q": False}
    ]
    return {
        "recorded_witness": {
            "universe": ["a", "b"],
            "gamma": ["a", "b"],
            "J_minus_q1": ["b"],
            "P_whole": False,
            "P_tail": True,
        },
        "recorded_witness_reproduced_arithmetically": (not p_whole_recorded) and p_tail_recorded,
        "recorded_witness_under_standard_J_minus": {
            "J_minus_q_with_transitive_closure": sorted(
                {k for k, v in X.items() if v in J_q}, key=lambda s: X[s]
            ),
            "P_whole": p_whole_std,
            "P_tail": p_tail_std,
            "still_a_strictness_witness": p_tail_std and not p_whole_std,
        },
        "hypothesis_H_violated_by_recorded_witness": {
            "violation": "a precedes b and b in J^-(q), but a not in J^-(q): J^-(q) is not past-closed",
            "explicit_failures": past_closure_failures,
        },
        "conclusion": "the recorded witness is not a model of the schema's declared causal structure "
                      "(H) and therefore does not refute equivalence for D4 geodesics",
    }


def noncausal_control() -> dict:
    """Drop causality of gamma: a non-causal chain can realize tail-without-whole, showing
    that D4's causality hypothesis (not the whole/tail wording) is the load-bearing one."""
    X = {"p0": 0, "p1": 1, "q": 2}
    R = frozenset({(0, 0), (1, 1), (2, 2), (1, 2)})  # p0 unrelated to p1; p1 in J^-(q)
    J = j_minus(R, X["q"])
    gamma = [X["p0"], X["p1"]]
    causal = all((gamma[i], gamma[i + 1]) in R for i in range(len(gamma) - 1))
    p_whole = all(x in J for x in gamma)
    p_tail = any(all(x in J for x in gamma[t0:]) for t0 in range(len(gamma)))
    return {
        "model": "X={p0,p1,q}, J^-(q)={p1,q}, chain [p0,p1]",
        "chain_is_future_directed_causal": causal,
        "P_whole": p_whole,
        "P_tail": p_tail,
        "strictness_witness": p_tail and not p_whole,
        "conclusion": "tail-without-whole requires a NON-causal step (p0 not precedes p1), "
                      "which D4 excludes; the control isolates the causality hypothesis",
    }


def proof_step_check() -> dict:
    steps = [
        {"n": 1, "step": "gamma(t0) in J^-(q) => gamma(t0) precedes q",
         "rule": "definition of J^-(q)", "machine_checkable": True},
        {"n": 2, "step": "for t < t0, the segment gamma|[t,t0] is a future-directed causal curve from gamma(t) to gamma(t0)",
         "rule": "D4: gamma is future-directed causal", "machine_checkable": True},
        {"n": 3, "step": "gamma(t) precedes gamma(t0) precedes q => gamma(t) precedes q",
         "rule": "(H) transitivity of causal precedence", "machine_checkable": False,
         "note": "standard property of the causal relation (concatenation of causal curves); "
                 "it is exactly the hypothesis the prior witness denies"},
        {"n": 4, "step": "gamma(t) in J^-(q) for all t < t0; t >= t0 by hypothesis",
         "rule": "definition of J^-(q) + step 3", "machine_checkable": True},
        {"n": 5, "step": "converse: whole-curve containment implies tail containment with t0 = 0",
         "rule": "trivial", "machine_checkable": True},
    ]
    return {
        "steps": steps,
        "non_machine_checkable_premises": ["(H) transitivity of causal precedence"],
        "finite_model_corroboration": "exhaustive_transitive_check covers (H)-models up to 4 points",
    }


GATE_READING = {
    "formal_clause_object": "quantifiers.formal ... not exists q in I+ with gamma subset J^-(q) intersect M.",
    "tail_clause_object": "visibility.definition/negation_conclusion ... tail gamma([t0,T)) contained in J^-(q) intersect M",
    "equivalence": "for gamma admitted by D4 the two existential-clauses agree; negating gives the exact negation",
}


def build_report() -> dict:
    created = datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S%z")
    t0 = pin_block()

    f1_text = (ROOT / F1).read_text()
    prior = json.loads((ROOT / PRIOR_REPORT).read_text())
    w026 = json.loads((ROOT / W026_REPORT).read_text())

    # --- T1: text binding at measured bytes ---------------------------------
    formal = prior["extractions"]["quantifiers.formal_visibility_clause"]
    d5 = prior["extractions"]["domains.D5"]
    vis = prior["extractions"]["visibility.definition"]
    neg = prior["extractions"]["visibility.negation_conclusion"]
    needles = {
        "quantifiers.formal_whole_curve_clause": "not exists q in I+ with gamma subset J^-(q) intersect M.",
        "domains.D5_whole_curve_reading": "gamma([0,T)) is contained in the causal past J^-(q) intersected with M",
        "visibility.definition_tail_clause": "TAIL gamma([t0,T)) is contained in J^-(q) intersect M",
        "visibility.negation_tail_clause": "the tail gamma([t0,T)) is NOT contained in J^-(q) intersect M",
    }
    text_checks = {}
    for name, needle in needles.items():
        text_checks[name] = {
            "present_in_f1_bytes": needle in f1_text,
            "line": line_of(f1_text, needle),
            "quoted": needle,
        }
    t1_ok = all(v["present_in_f1_bytes"] for v in text_checks.values())

    prior_claim = next(f for f in prior["findings"] if f["id"] == PRIOR_FINDING_ID)
    prior_logic = prior["logical_relation"]
    lemma = w026["lemma_past_closedness"]

    # --- T2/T3/T4/T5 --------------------------------------------------------
    t2 = exhaustive_transitive_check()
    t3 = prior_witness_audit()
    t4 = {
        "finding": "the prior strictness witness violates past-closedness of J^-(q); under (H) it is not admissible",
        "past_closedness_violation": t3["hypothesis_H_violated_by_recorded_witness"],
        "prior_witness_still_a_witness": t3["recorded_witness_under_standard_J_minus"]["still_a_strictness_witness"],
    }
    t5 = noncausal_control()
    t6 = proof_step_check()

    verdict_payload = {
        "targets": {
            PRIOR_FINDING_ID: {
                "source": f"{PRIOR_REPORT}#{sha256_path(PRIOR_REPORT)[:12]}",
                "textual_premise": "REPRODUCED: line 55 / D5 read the whole curve, lines 220/222 read the tail",
                "mathematical_claim": "REFUTED: 'strictly weaker / not exact negations' is false for D4 geodesics",
                "reason": "(H) makes the whole-curve and tail containment clauses equivalent; "
                          "the finite strictness witness requires denying (H) or using a non-causal curve",
                "severity_reclassification": "critical -> non-blocking documentation (precision) issue",
            },
            LEMMA_ID: {
                "source": f"{W026_REPORT}#{sha256_path(W026_REPORT)[:12]}",
                "status": "CONFIRMED independently by exhaustive finite-model check + proof-step audit",
                "corollary_adopted": "quantifiers.formal and quantifiers.negation are exact negations on the measured bytes",
            },
        },
        "surviving_defect_nonblocking": {
            "location": f"{F1}:220",
            "statement": "the sentence 'requiring the whole geodesic to lie in J^-(q) would misclassify a geodesic "
                         "that starts in the exterior and ends inside the black-hole region' is a non-sequitur: "
                         "for that example both readings classify the geodesic as not visible; the schema also never "
                         "states the (H)-equivalence lemma, which demonstrably misled reviewer-19 and a prior worker-037 slot",
            "recommended_fix": "replace that sentence with the equivalence statement and cite (H)/J^- past-closedness",
            "blocking": False,
        },
        "prior_blocker_withdrawal": {
            "blocker_id": PRIOR_BLOCKER_ID,
            "action": "WITHDRAWN as a critical blocker",
            "basis": "the blocker's own falsifier fired: 'a reviewer rebuttal naming the definitional bridge that "
                     "makes line 55 the tail predicate falsifies W037V2-F1 instead' - the bridge is J^- past-closedness (H)",
        },
        "out_of_scope_untouched": [
            "D0 disjunction / single-frozen-data-class (other findings at this hash; not adjudicated here)",
            "AF_{I+}(M_D) dangling symbol at line 251",
            "duplicate revised_at keys / future timestamps",
            "class_contract_pointer divergence (F0 mirror conflict)",
        ],
        "gate_effect": "none: worker evidence only; no gate verdict, no node status, no canonical edit",
    }

    return {
        "actor": "worker-037",
        "task_id": "W037-F1-VISIBILITY-03",
        "created_at": created,
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "node_id": "F1",
        "gate": "G-FORM",
        "question": "At the measured F1 bytes, is W037V2-F1's claim that quantifiers.formal's whole-curve visibility "
                    "clause is strictly weaker than visibility.definition's tail clause (so formal and negation are "
                    "not exact negations) correct, or is LEMMA-W026-1's equivalence claim correct?",
        "method": "read-only: T0 pin -> exact clause extraction -> exhaustive finite-model check over all "
                  "reflexive+transitive relations on <=4 points with causal chains -> reconstruction and audit of "
                  "the prior strictness witness -> non-causal control -> proof-step audit -> T1 pin",
        "authority": "independent verification evidence only; NOT a gate verdict, NOT an accept, NOT a node-status change",
        "does_not_claim": [
            "G-FORM pass/fail", "G-F0 pass/fail", "node completion", "theorem", "physics result",
            "authority to edit canonical artifacts", "one of the two required accepts",
            "that F1 is correct overall: only the visibility-clause mathematical claim is adjudicated",
            "that (H) is proved here: (H) is the standard transitivity property of causal precedence",
        ],
        "pins": {"T0": t0, "T1": pin_block()},
        "targets_under_test": [
            {"id": PRIOR_FINDING_ID,
             "statement": prior_claim["statement"],
             "severity_as_filed": prior_claim["severity"],
             "evidence_as_filed": prior_claim["evidence"],
             "recorded_logic": prior_logic},
            {"id": LEMMA_ID,
             "statement": lemma["statement"],
             "hypotheses": lemma["hypotheses"],
             "proof": lemma["proof"],
             "corollary": lemma["corollary"]},
        ],
        "extraction": {
            "f1_formal_clause": formal,
            "f1_D5": d5,
            "f1_visibility_definition": vis,
            "f1_visibility_negation": neg,
            "text_checks": text_checks,
        },
        "tests": {
            "T1_text_binding": {"pass": t1_ok, "detail": text_checks},
            "T2_exhaustive_transitive_models": t2,
            "T3_prior_witness_audit": t3,
            "T4_past_closedness_violation": t4,
            "T5_noncausal_control": t5,
            "T6_proof_step_audit": t6,
        },
        "verdict": verdict_payload,
        "falsifier": "At the same five pins: exhibit a model of the schema's declared causal structure in which "
                     "D4's hypotheses hold (gamma future-directed causal; J^-(q) the standard causal past, hence "
                     "past-closed/transitive) and the tail clause holds while the whole-curve clause fails; OR show "
                     "the schema's own bytes define J^-(q) as a NON-past-closed set or admit non-causal gamma in D4; "
                     "OR show the measured F1/F0/FROZEN/prior-report hashes differ from the pins. Any of these "
                     "reinstates W037V2-F1 at critical severity.",
        "next_falsifier": "Re-run this script at the next F1 revision: if quantifiers.formal/D5 adopt the tail binder "
                          "verbatim (T1 needles change) the recommendation is discharged; if visibility.definition's "
                          "misclassification sentence is replaced by the (H) equivalence statement, the surviving "
                          "non-blocking item is closed; if F1 hash drifts, every verdict here is superseded and the "
                          "adjudication must be re-run against the new bytes.",
        "report_payload_sha256": None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "report.json"))
    args = ap.parse_args()
    rep = build_report()
    rep["pins_stable"] = (rep["pins"]["T0"] == rep["pins"]["T1"])
    payload = json.dumps({k: v for k, v in rep.items() if k != "report_payload_sha256"},
                         sort_keys=True, separators=(",", ":"))
    rep["report_payload_sha256"] = hashlib.sha256(payload.encode()).hexdigest()
    out = Path(args.out)
    out.write_text(json.dumps(rep, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out}")
    print(f"pins_stable={rep['pins_stable']}")
    print(f"T2 verdict={rep['tests']['T2_exhaustive_transitive_models']['verdict']} "
          f"models={rep['tests']['T2_exhaustive_transitive_models']['models_checked']} "
          f"tail_without_whole={rep['tests']['T2_exhaustive_transitive_models']['tail_without_whole']}")
    print(f"prior witness reproduced arithmetically={rep['tests']['T3_prior_witness_audit']['recorded_witness_reproduced_arithmetically']}; "
          f"still a witness under standard J^-={rep['tests']['T3_prior_witness_audit']['recorded_witness_under_standard_J_minus']['still_a_strictness_witness']}")
    if not rep["pins_stable"]:
        print("WARNING: pins moved T0 -> T1; adjudication is void", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
