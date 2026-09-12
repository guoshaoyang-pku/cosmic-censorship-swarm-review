#!/usr/bin/env python3
"""W063-SET-DIRECTION-ADJ-01 -- independent two-level adjudication of the
AF-WCC-VAC-GEN variant-SET strength relation at live frozen bytes.

Question (class-bound, F1 / G-FORM): the canonical F0 taxonomy
(research_map/formulation_taxonomy.yaml @ 0abb9ed8a961, G-F0-passed) says the
set-based visibility *reading* is "strictly stronger" than the single-q tail
predicate, while F1 rev13 (schemas/af_wcc_vacuum.yaml @ d9cebb9404b2) and its
registry/delta say the SET relation is "strictly WEAKER". Which level does each
sentence quantify over, and are they contradictory?

Method:
  * every input pinned by sha256; any drift -> exit 3, no report written;
  * exact carrier quotes extracted by anchor (path + line number recorded);
  * labels classified on the axis {predicate, class_negation} x {stronger, weaker};
  * logical core machine-checked exhaustively over finite models:
      (L1) single-q tail containment entails union containment      [S => U]
      (L2) the converse fails (explicit finite witness)             [U and not S]
      (L3) negation reversal: not-U entails not-S, and not-S does not entail not-U
  * six controls (K1 non-vacuity, K2/K3 mutation flips, K4 determinism,
    K5 fail-closed pin drift, K6 out-of-scope axis negative control).

Authority: this runner writes only its own --out. It sets no gate verdict, no
node status and no validation_status. Worker measurement only.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

PINS = {
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml":
        "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/VARIANT_REGISTRY.json":
        "6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json":
        "64b8d6394a044686de770879675eb4932ff980a942d45d16758b295d4851cecf",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/evidence/taxonomy_consistency.json":
        "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
}

F0_CANON = "research_map/formulation_taxonomy.yaml"
F1_CANON = "schemas/af_wcc_vacuum.yaml"
F1_MIRROR = "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
F0_COMPANION = "artifacts/formulation/formulation_taxonomy.yaml"
REGISTRY = "artifacts/formulation/VARIANT_REGISTRY.json"
SET_DELTA = "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"
FROZEN = "artifacts/formulation/FROZEN.json"


class PinDrift(Exception):
    pass


class ControlFailure(Exception):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def pin_check() -> dict:
    measured = {}
    for rel, expected in PINS.items():
        p = ROOT / rel
        if not p.exists():
            raise PinDrift(f"missing pinned input: {rel}")
        got = sha256_file(p)
        if got != expected:
            raise PinDrift(f"pin drift: {rel} expected {expected[:12]} measured {got[:12]}")
        measured[rel] = got
    return measured


def line_of(text: str, needle: str) -> tuple[int, str]:
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i, line.strip()
    raise ControlFailure(f"anchor not found: {needle!r}")


# ---------------------------------------------------------------- logic core
def _models(n: int, j_sets: tuple, tail: frozenset):
    """Enumerate every J^- relation matrix on n points x len(j_sets) points."""
    cells = [(q, x) for q in range(len(j_sets)) for x in range(n)]
    for bits in itertools.product((False, True), repeat=len(cells)):
        jmap = {q: set() for q in range(len(j_sets))}
        for (q, x), b in zip(cells, bits):
            if b:
                jmap[q].add(x)
        yield jmap


def single_q(tail: frozenset, jmap) -> bool:
    return any(tail <= jmap[q] for q in jmap)


def union_reading(tail: frozenset, jmap) -> bool:
    return tail <= set().union(*jmap.values())


def logic_core() -> dict:
    s_implies_u = 0
    violations = []
    for n in (3, 4):
        all_pts = frozenset(range(n))
        for r in range(1, n + 1):
            for tail in itertools.combinations(range(n), r):
                tail = frozenset(tail)
                for jmap in _models(n, tuple(range(2)), tail):
                    if single_q(tail, jmap) and not union_reading(tail, jmap):
                        s_implies_u += 1
                        if len(violations) < 3:
                            violations.append({"n": n, "tail": sorted(tail),
                                               "J": {str(k): sorted(v) for k, v in jmap.items()}})
    witness = {"tail": [0, 1], "J": {"q0": [0], "q1": [1]}}
    w_tail = frozenset(witness["tail"])
    w_j = {0: {0}, 1: {1}}
    witness_holds = union_reading(w_tail, w_j) and not single_q(w_tail, w_j)
    # negation reversal on the same witness
    neg_u = not union_reading(w_tail, w_j)          # variant SET class assertion
    neg_s = not single_q(w_tail, w_j)               # parent class assertion
    return {
        "L1_single_q_entails_union": {"counterexamples": s_implies_u,
                                      "examples": violations,
                                      "checked": "exhaustive finite models, n in {3,4}, |I+|=2"},
        "L2_converse_fails": {"finite_witness": witness, "holds": bool(witness_holds)},
        "L3_negation_reversal": {"not_U": neg_u, "not_S": neg_s,
                                 "not_U_implies_not_S": (not neg_u) or neg_s,
                                 "not_S_implies_not_U": (not neg_s) or neg_u,
                                 "reading": ("not-U strictly stronger than not-S: witness has "
                                             "not_S true and not_U false, so not-S does not "
                                             "entail not-U while S=>U gives not-U=>not-S")},
        "gr_realizability_of_L2": ("NOT claimed here: the omega-chain witness separating the "
                                   "readings at the GR level is W076-GFORM-STRICTNESS-RECONCILE-06 T4, "
                                   "cited, not re-derived. L2 above is the finite set-theoretic "
                                   "strictness obligation only."),
    }


def _find_rel(text: str, anchor: str, words: tuple) -> tuple:
    """Find the line carrying the anchor and classify its strength word.

    The label may sit on the anchor line or wrap onto the next two lines
    (F0 canonical L199-200 is one wrapped sentence), so the window is scanned.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        if anchor in line:
            window = " ".join(lines[i - 1:i + 2])
            low = window.lower()
            for w, val in words:
                if w in low:
                    return i, window.strip(), val
            raise ControlFailure(f"no strength word in window at line {i}: {anchor!r}")
    raise ControlFailure(f"anchor not found: {anchor!r}")


# ---------------------------------------------------------------- extraction
def classify(text_f0: str, text_f1: str, companion: str, registry: dict,
             delta: dict) -> tuple[list, list]:
    carriers = []

    ln, quote, rel = _find_rel(text_f0, "The set-based reading",
                               (("strictly stronger", "stronger"), ("strictly weaker", "weaker")))
    carriers.append({
        "carrier": F0_CANON + "#" + PINS[F0_CANON][:12],
        "line": ln, "quote": quote,
        "level": "predicate", "subject": "set-based reading (union containment)",
        "relation": rel, "normative": "G-F0-passed canonical taxonomy",
    })

    ln, quote, rel = _find_rel(text_f1, "single-q tail predicate: the single-q tail predicate entails",
                               (("strictly weaker", "weaker"), ("strictly stronger", "stronger")))
    carriers.append({
        "carrier": F1_CANON + "#" + PINS[F1_CANON][:12],
        "line": ln, "quote": quote,
        "level": "predicate", "subject": "variant SET", "relation": rel,
        "normative": "F1 rev13 canonical class schema",
    })
    ln, quote = line_of(text_f1, "non-containment in the union implies no single q sees a tail")
    carriers.append({
        "carrier": F1_CANON + "#" + PINS[F1_CANON][:12],
        "line": ln, "quote": quote,
        "level": "class_negation", "subject": "variant SET conclusion", "relation": "stronger",
        "normative": "F1 rev13 canonical class schema",
    })

    ln, quote = line_of(companion, "lies outside J^-(I+) as a SET (strictly stronger)")
    rel_quote = line_of(companion, "F0 was stronger; (b) implies (c) but not conversely")[1]
    carriers.append({
        "carrier": F0_COMPANION + "#" + PINS[F0_COMPANION][:12],
        "line": ln, "quote": quote + " || " + rel_quote,
        "level": "class_negation", "subject": "D1 divergence row (F0 reading)",
        "relation": "stronger", "normative": "F0 companion supplement (D1 resolution)",
    })

    set_variant = next(v for v in registry["variants"] if v["variant_id"] == "SET")
    carriers.append({
        "carrier": REGISTRY + "#" + PINS[REGISTRY][:12],
        "line": None, "quote": set_variant["strength"],
        "level": "predicate", "subject": "variant SET registry strength",
        "relation": "weaker" if "strictly weaker" in set_variant["strength"] else "stronger",
        "normative": "VARIANT_REGISTRY v2.0 (FROZEN rev29 pin)",
    })

    carriers.append({
        "carrier": SET_DELTA + "#" + PINS[SET_DELTA][:12],
        "line": None, "quote": delta["strength"],
        "level": "predicate", "subject": "variant SET delta strength",
        "relation": "weaker" if "strictly weaker" in delta["strength"].lower() else "stronger",
        "normative": "SET delta, rebased_at 2026-09-12T00:57:02+08:00",
    })
    neg_to = next(c["to"] for c in delta["changes"]
                  if c["path"] == "visibility.negation_conclusion")
    carriers.append({
        "carrier": SET_DELTA + "#" + PINS[SET_DELTA][:12],
        "line": None, "quote": neg_to,
        "level": "class_negation", "subject": "variant SET negation",
        "relation": "stronger" if "strictly stronger than the single-q negation" in neg_to else "weaker",
        "normative": "SET delta, rebased_at 2026-09-12T00:57:02+08:00",
    })

    conflicts = []
    for level, want in (("predicate", "weaker"), ("class_negation", "stronger")):
        rels = sorted({c["relation"] for c in carriers
                       if c["level"] == level and c["carrier"].startswith((F0_CANON, F1_CANON, F0_COMPANION, REGISTRY, SET_DELTA))})
        if len(rels) > 1:
            conflicts.append({"level": level, "relations_present": rels,
                              "carriers": [c["carrier"] for c in carriers if c["level"] == level]})
    return carriers, conflicts


def load_inputs() -> tuple:
    f0 = read_text(F0_CANON)
    f1 = read_text(F1_CANON)
    companion = read_text(F0_COMPANION)
    registry = json.loads(read_text(REGISTRY))
    delta = json.loads(read_text(SET_DELTA))
    return f0, f1, companion, registry, delta


def measure() -> dict:
    pins = pin_check()
    f0, f1, companion, registry, delta = load_inputs()
    frozen = json.loads(read_text(FROZEN))
    carriers, conflicts = classify(f0, f1, companion, registry, delta)
    frozen_pin = frozen["files"].get(F0_CANON, {}).get("sha256")
    result = {
        "task_id": "W063-SET-DIRECTION-ADJ-01",
        "actor": "worker-063",
        "class_id": "AF-WCC-VAC-GEN",
        "node_id": "F1",
        "gate": "G-FORM",
        "pins_verified": pins,
        "frozen_revision": frozen.get("revision"),
        "frozen_at": frozen.get("frozen_at"),
        "f0_canonical_frozen_pin_matches_live": frozen_pin == PINS[F0_CANON],
        "carriers": carriers,
        "conflicts": conflicts,
        "logic_core": logic_core(),
        "adjudication": {
            "predicate_level": ("single-q tail predicate S entails union reading U (L1), and the "
                                "converse fails (L2): S is strictly stronger, U strictly weaker. "
                                "F1 rev13, the registry and the SET delta are CORRECT at this level."),
            "class_negation_level": ("not-U (variant SET conclusion) is strictly stronger than not-S "
                                     "(parent class conclusion): the L2 witness satisfies not-S and "
                                     "fails not-U. The SET delta negation clause and the companion D1 "
                                     "row are CORRECT at this level."),
            "defect": ("F0 canonical " + F0_CANON + "@" + PINS[F0_CANON][:12] + " lines 199-200 "
                       "(sentence wrapped across the two lines; extracted anchor line " +
                       str([c for c in carriers if c["carrier"].startswith(F0_CANON)][0]["line"]) +
                       ") applies the predicate-level label 'strictly stronger' to the set-based "
                       "reading, which L1 contradicts. It is the only live frozen carrier that is "
                       "inverted; it is G-F0-passed bytes, so it cannot be repaired by a worker "
                       "edit (any write voids G-F0) and requires a controller erratum/re-freeze "
                       "decision."),
            "consequence_for_F1": ("F1 rev13 needs no change on this axis. A blind reviewer who "
                                   "treats F0 0abb9ed8a961 as the normative binding target will "
                                   "read a contradiction (reproduces worker-018 HF-W018-F1-1); the "
                                   "repair belongs to F0/controller."),
        },
        "falsifier": ("Show a derivation that union containment entails single-q tail containment "
                      "for a future-inextendible finite-affine-length causal geodesic under the "
                      "class's standing assumptions (which would make L1 false and the F0 label "
                      "correct), or show the line " +
                      str([c for c in carriers if c["carrier"].startswith(F0_CANON)][0]["line"]) +
                      " sentence at " + F0_CANON + " has a live referent other than the set-based "
                      "visibility reading, or show any pinned file has drifted (which voids the "
                      "binding)."),
        "non_claims": [
            "no gate verdict, no node status, no validation_status; worker measurement only",
            "no claim that variant SET is GR-realizable by the finite witness; T4 is cited, not re-derived",
            "no edit of any canonical artifact",
        ],
        "authority": "worker events cannot set status=done, validation_status=passed, or a gate verdict",
    }
    return result


# ---------------------------------------------------------------- controls
def run_controls() -> dict:
    out = {}

    # K1 non-vacuity: all six anchors resolve, >= 6 predicate carriers
    f0, f1, companion, registry, delta = load_inputs()
    carriers, conflicts = classify(f0, f1, companion, registry, delta)
    out["K1_extraction_nonvacuous"] = {
        "carriers": len(carriers),
        "predicate_carriers": sum(1 for c in carriers if c["level"] == "predicate"),
        "conflicts": len(conflicts),
        "pass": len(carriers) >= 6 and len(conflicts) >= 1,
    }

    # K2 F0 mutation flips the predicate label -> conflict disappears
    mutated_f0 = f0.replace("is strictly stronger; it is registered as variant",
                            "is strictly weaker; it is registered as variant")
    _, c2 = classify(mutated_f0, f1, companion, registry, delta)
    out["K2_f0_mutation_clears_conflict"] = {"conflicts": len(c2), "pass": len(c2) == 0}

    # K3 F1 mutation flips the schema label -> conflict grows
    mutated_f1 = f1.replace("strictly WEAKER than this class's single-q tail predicate",
                            "strictly STRONGER than this class's single-q tail predicate")
    _, c3 = classify(f0, mutated_f1, companion, registry, delta)
    pred_rels = sorted({c["relation"] for c in classify(f0, mutated_f1, companion, registry, delta)[0]
                        if c["level"] == "predicate"})
    out["K3_f1_mutation_detected"] = {
        "predicate_relations": pred_rels,
        "pass": "stronger" in pred_rels and "weaker" in pred_rels,
    }

    # K4 determinism
    a = json.dumps(classify(f0, f1, companion, registry, delta), sort_keys=True)
    b = json.dumps(classify(f0, f1, companion, registry, delta), sort_keys=True)
    out["K4_determinism"] = {"identical": a == b, "pass": a == b}

    # K5 fail-closed on pin drift
    drift = dict(PINS)
    target = SET_DELTA
    drift[target] = "0" * 64
    saved, PINS[target] = PINS[target], drift[target]
    try:
        pin_check()
        k5 = {"raised": False, "pass": False}
    except PinDrift as exc:
        k5 = {"raised": True, "message": str(exc)[:160], "pass": True}
    finally:
        PINS[target] = saved
    out["K5_fail_closed_pin_drift"] = k5

    # K6 out-of-scope negative control: CH variant is an extension-class axis, not visibility
    ch = next(v for v in registry["variants"] if v["variant_id"] == "CH")
    ch_entered = any("CH" in c["carrier"] or c["subject"] == "variant CH" for c in carriers)
    out["K6_out_of_scope_axis_negative_control"] = {
        "variant": "CH", "strength": ch["strength"],
        "classified_in_conflict_set": ch_entered,
        "pass": not ch_entered,
    }

    out["all_pass"] = all(v.get("pass") for v in out.values() if isinstance(v, dict))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    try:
        result = measure()
    except PinDrift as exc:
        print(json.dumps({"error": "PIN_DRIFT", "message": str(exc)}))
        return 3
    except ControlFailure as exc:
        print(json.dumps({"error": "CONTROL_FAILURE", "message": str(exc)}))
        return 2

    controls = run_controls()
    result["controls"] = controls
    result["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    if not controls["all_pass"]:
        print(json.dumps({"error": "CONTROLS_FAILED", "controls": controls}))
        return 2

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "OK", "out": str(out),
                      "conflicts": len(result["conflicts"]),
                      "controls": "all_pass"}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
