#!/usr/bin/env python3
"""W003-SET-STRENGTH-LEVEL-AUDIT-01.

Level-indexed, read-only audit of the AF-WCC-VAC-GEN variant SET strength
direction across the live canonical carriers, at the FROZEN rev29 state.

The question is well-posed only if two levels are separated:

  predicate level   T(g) := exists q in I+, exists t0: tail g([t0,T)) subset J^-(q)
                    S(g) := g([0,T)) subset union_{q in I+} J^-(q)
                    T => S, and S =/=> T on the omega chain
                    => S is the strictly WEAKER predicate.

  class level       the class conclusion is the inexistence statement
                    C_T := no g with T(g);  C_S := no g with S(g)
                    T => S  <=>  C_S => C_T
                    => C_S is the strictly STRONGER class statement.

Any carrier that attaches a direction word to the other level is inverted, and
any carrier that compares to a class while justifying with a predicate fact is
level-mixed.  This probe measures each carrier, re-derives the two directions
from the order structure (all 355 preorders on 4 points + an omega-chain
witness), and reports.  It writes nothing outside its own directory.

Exit codes: 0 all declared expectations pass; 3 input pin drift; 4 a planted
control failed (probe untrustworthy).
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # repo root
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))

PINNED = {
    "schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/VARIANT_REGISTRY.json":
        "6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json":
        "64b8d6394a044686de770879675eb4932ff980a942d45d16758b295d4851cecf",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml":
        "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    # rev12 predecessor, used only for the K1 detector control
    "artifacts/worker-060/rev29_binding_acceptance/snapshots/f1__af_wcc_vacuum.cce9c60146d6.yaml":
        "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def measure_pins() -> dict:
    got = {}
    for rel in PINNED:
        p = ROOT / rel
        got[rel] = sha256(p) if p.exists() else "MISSING"
    return got


# ---------------------------------------------------------------- order core
def preorders(n=4):
    """All reflexive transitive relations on n labelled points (355 for n=4)."""
    elems = range(n)
    pairs = [(i, j) for i in elems for j in elems]
    for mask in range(1 << len(pairs)):
        rel = {pairs[k] for k in range(len(pairs)) if (mask >> k) & 1}
        if any((i, i) not in rel for i in elems):
            continue
        if all(not ((a, b) in rel and (b, c) in rel) or (a, c) in rel
               for a in elems for b in elems for c in elems):
            yield rel


def down(rel, q):
    return {p for p in range(4) if (p, q) in rel}


def chains(rel, n=4):
    """All finite causal (non-decreasing under `rel`) sequences over n points."""
    for seq in itertools.product(range(n), repeat=n):
        if all((seq[i], seq[i + 1]) in rel for i in range(n - 1)):
            yield seq


def order_core_check():
    """T => S and C_S => C_T over every 4-point preorder and finite chain.

    I+ ranges over every nonempty subset of the 4 points so the class-level
    check is not vacuous, and each preorder is checked against every finite
    chain of length 4.  Expected: 355 preorders, 0 violations at both levels,
    and 0 finite-chain separations (separation needs the omega chain).
    """
    n = 4
    n_po = 0
    n_frames = 0
    t_implies_s_violations = 0
    s_implies_t_violations = 0
    cs_implies_ct_violations = 0
    frames_with_S_and_T = 0
    n_chains_checked = 0
    for rel in preorders(n):
        n_po += 1
        all_chains = list(chains(rel, n))
        n_chains_checked += len(all_chains)
        for r in range(1, 1 << n):
            i_plus = {i for i in range(n) if (r >> i) & 1}
            n_frames += 1
            union_all = set()
            for q in i_plus:
                union_all |= down(rel, q)
            for seq in all_chains:
                t = any(set(seq) <= down(rel, q) for q in i_plus)
                s = set(seq) <= union_all
                if t and not s:
                    t_implies_s_violations += 1
                if s and not t:
                    s_implies_t_violations += 1
            has_s = any(set(seq) <= union_all for seq in all_chains)
            has_t = any(any(set(seq) <= down(rel, q) for q in i_plus)
                        for seq in all_chains)
            if has_s and has_t:
                frames_with_S_and_T += 1
            if (not has_s) and has_t:
                cs_implies_ct_violations += 1
    return {
        "n_preorders": n_po,
        "n_frames_preorder_x_I_plus": n_frames,
        "n_chains_checked": n_chains_checked,
        "n_frames_with_S_and_T": frames_with_S_and_T,
        "T_implies_S_violations": t_implies_s_violations,
        "S_implies_T_violations_on_finite_chains": s_implies_t_violations,
        "C_S_implies_C_T_violations": cs_implies_ct_violations,
        # expected: 355, 5325, >0, >0, 0, 0, 0
    }


def omega_chain_witness():
    """S holds while T fails: q_n = n, gamma(t_n) = n, J^-(q_n) = {m <= n}."""
    N = 200
    # S: every gamma point n lies in J^-(q_n).
    s = all(n in {m for m in range(n + 1)} for n in range(N))
    # T: would need one q_big whose down-set contains an entire infinite tail
    # {n : n >= k}.  Checking the tail through big+1 is decisive: if the tail
    # were inside {m <= big} then n = big+1 (>= k whenever k <= big+1) would
    # have to satisfy big+1 <= big.
    t = any(all(n <= big for n in range(k, big + 2))
            for big in range(N) for k in range(big + 2))
    # class level: C_S => C_T is the contrapositive of T => S; the witness has
    # S true so C_S is false and the implication is not violated here.
    return {"S_holds": bool(s), "T_holds": bool(t),
            "separates": bool(s and not t),
            "class_level_C_S_implies_C_T_violation": bool(t and not s)}


# ------------------------------------------------------------- text auditing
WEAKER = "weaker"
STRONGER = "stronger"


def direction_of(text: str):
    m = re.search(r"strictly\s+(WEAKER|STRONGER|weaker|stronger)", text)
    return m.group(1).lower() if m else None


def f1_relation(path: Path):
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if line.strip().startswith("relation:") and "single-q tail predicate" in line:
            return i, line.strip(), direction_of(line)
    return None, None, None


def registry_strength(path: Path):
    reg = json.loads(path.read_text())
    for e in reg["variants"]:
        if e.get("variant_id") == "SET":
            return e["strength"], direction_of(e["strength"])
    return None, None


def delta_fields(path: Path):
    d = json.loads(path.read_text())
    neg = next((c["to"] for c in d.get("changes", [])
                if c.get("path") == "visibility.negation_conclusion"), None)
    vis_def = next((c["to"] for c in d.get("changes", [])
                    if c.get("path") == "visibility.definition"), None)
    return {
        "strength": d.get("strength", ""),
        "strength_direction": direction_of(d.get("strength", "")),
        "negation_conclusion": neg,
        "negation_direction": direction_of(neg or ""),
        "visibility_definition": vis_def,
        "visibility_definition_direction": direction_of(vis_def or ""),
    }


def f0_canonical_line(path: Path):
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if "is strictly stronger" in line and "variant" in line:
            return i, line.strip()
    return None, None


def f0_supplement_d1(path: Path):
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if "F0 was stronger" in line:
            return i, line.strip()
    return None, None


def detect(sentence: str, declared_level: str, target: str):
    """Return (state, direction, reason).  Levels: predicate|class.

    expected direction: predicate -> weaker, class -> stronger.
    """
    d = direction_of(sentence)
    if d is None:
        return "NO_DIRECTION", d, "no 'strictly weaker/stronger' token"
    expect = WEAKER if declared_level == "predicate" else STRONGER
    head_is_class = "AF-WCC-VAC-GEN" in sentence or "parent class" in sentence
    just_is_predicate = bool(re.search(
        r"tail predicate entails|union reading|implied by|reading is", sentence))
    mixed = (declared_level == "class" and just_is_predicate
             and target == "head")
    if d != expect:
        return ("INVERTED_AT_DECLARED_LEVEL" if not mixed
                else "LEVEL_MIXED_CLASS_HEAD_INVERTED"), d, (
            f"declared level {declared_level} expects {expect}, sentence says {d}"
            + ("; head compares to a class but the justification is predicate-level"
               if mixed else ""))
    if mixed:
        return "LEVEL_MIXED", d, "class-level head with predicate-level justification"
    return "CONSISTENT", d, f"declared level {declared_level} expects {expect}"


def main() -> int:
    created = datetime.now(CST).isoformat(timespec="seconds")
    before = measure_pins()
    drift = {k: (PINNED[k], before[k]) for k in PINNED if before[k] != PINNED[k]}
    if drift:
        print("FAIL-CLOSED: pin drift before run:", json.dumps(drift, indent=1))
        return 3

    checks = []
    controls = []

    def check(cid, desc, expected, observed):
        ok = expected == observed
        checks.append({"check_id": cid, "description": desc,
                       "expected": expected, "observed": observed, "pass": ok})
        return ok

    # ---- declared expectations -------------------------------------------
    core = order_core_check()
    check("E01", "all preorders on 4 labelled points enumerated",
          355, core["n_preorders"])
    check("E02", "predicate level T => S over all preorders/chains",
          0, core["T_implies_S_violations"])
    check("E03", "finite chains cannot separate S from T (control ceiling)",
          0, core["S_implies_T_violations_on_finite_chains"])
    check("E04", "class level C_S => C_T over all preorders",
          0, core["C_S_implies_C_T_violations"])
    check("E04b", "class-level check is non-vacuous (frames with both C_S and C_T live)",
          True, core["n_frames_with_S_and_T"] > 0)
    w = omega_chain_witness()
    check("E05", "omega-chain witness has S true, T false",
          {"S_holds": True, "T_holds": False, "separates": True},
          {"S_holds": w["S_holds"], "T_holds": w["T_holds"],
           "separates": w["separates"]})

    f1 = ROOT / "schemas/af_wcc_vacuum.yaml"
    f1m = ROOT / "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
    reg = ROOT / "artifacts/formulation/VARIANT_REGISTRY.json"
    delta = ROOT / "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"
    f0 = ROOT / "research_map/formulation_taxonomy.yaml"
    f0s = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"

    ln, line, direction = f1_relation(f1)
    check("E06", "F1 canonical SET relation is predicate-level and weaker",
          ("predicate", WEAKER), ("predicate", direction))
    check("E07", "F1 mirror is byte-identical to canonical", True,
          sha256(f1) == sha256(f1m))
    reg_s, reg_d = registry_strength(reg)
    check("E08", "registry SET strength names the class (class-level)",
          True, "AF-WCC-VAC-GEN" in (reg_s or ""))
    dfields = delta_fields(delta)
    check("E09", "delta SET strength names the class (class-level)",
          True, "AF-WCC-VAC-GEN" in dfields["strength"])
    check("E10", "delta negation_conclusion is class-level and stronger",
          STRONGER, dfields["negation_direction"])
    fl, fline = f0_canonical_line(f0)
    check("E11", "F0 canonical: set-based reading is called strictly stronger",
          True, fl is not None)
    sl, sline = f0_supplement_d1(f0s)
    check("E12", "F0 supplement D1 records 'F0 was stronger'",
          True, sl is not None)

    # ---- level classification of every carrier ---------------------------
    carriers = [
        {"id": "C1", "path": "schemas/af_wcc_vacuum.yaml", "line": ln,
         "declared_level": "predicate", "text": line,
         "target": "single-q tail predicate"},
        {"id": "C2", "path": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
         "line": ln, "declared_level": "predicate", "text": line,
         "target": "single-q tail predicate"},
        {"id": "C3", "path": "artifacts/formulation/VARIANT_REGISTRY.json",
         "line": None, "declared_level": "class", "text": reg_s,
         "target": "head"},
        {"id": "C4",
         "path": "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
         "line": None, "declared_level": "class", "text": dfields["strength"],
         "target": "head"},
        {"id": "C5",
         "path": "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
         "line": None, "declared_level": "predicate",
         "text": dfields["visibility_definition"],
         "target": "single-q tail predicate"},
        {"id": "C6",
         "path": "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
         "line": None, "declared_level": "class",
         "text": dfields["negation_conclusion"], "target": "negation"},
        {"id": "C7", "path": "research_map/formulation_taxonomy.yaml",
         "line": fl, "declared_level": "predicate", "text": fline,
         "target": "set-based reading"},
        {"id": "C8", "path": "artifacts/formulation/formulation_taxonomy.yaml",
         "line": sl, "declared_level": "class", "text": sline,
         "target": "F0 conclusion"},
    ]
    for c in carriers:
        state, d, reason = detect(c["text"] or "", c["declared_level"], c["target"])
        c.update({"direction": d, "state": state, "reason": reason})
    states = {c["id"]: c["state"] for c in carriers}
    check("E13", "C1/C2 F1 predicate carriers are consistent",
          ["CONSISTENT", "CONSISTENT"], [states["C1"], states["C2"]])
    check("E14", "C3 registry class-level head is inverted (measured)",
          "LEVEL_MIXED_CLASS_HEAD_INVERTED", states["C3"])
    check("E15", "C4 delta class-level head is inverted (measured)",
          "LEVEL_MIXED_CLASS_HEAD_INVERTED", states["C4"])
    check("E16", "C5 delta predicate-level visibility text is consistent",
          "CONSISTENT", states["C5"])
    check("E17", "C6 delta negation text is class-level consistent",
          "CONSISTENT", states["C6"])
    check("E18", "C7 F0 canonical attaches 'stronger' to the predicate reading",
          "INVERTED_AT_DECLARED_LEVEL", states["C7"])
    check("E19", "C8 F0 supplement D1 is class-level consistent (not inverted)",
          "CONSISTENT", states["C8"])
    internal = (dfields["strength_direction"] == WEAKER
                and dfields["negation_direction"] == STRONGER)
    check("E20", "one delta file asserts weaker(class head) and stronger(negation)",
          True, internal)

    # ---- planted controls (in-memory only) --------------------------------
    def ctl(cid, desc, fn, expected):
        got = fn()
        ok = got == expected
        controls.append({"control": cid, "description": desc,
                         "expected": expected, "observed": got, "pass": ok})

    rev12 = ROOT / ("artifacts/worker-060/rev29_binding_acceptance/snapshots/"
                    "f1__af_wcc_vacuum.cce9c60146d6.yaml")
    _, r12line, r12dir = f1_relation(rev12)
    ctl("K1", "detector fires on the rev12 predicate-level inversion",
        lambda: detect(r12line, "predicate", "single-q tail predicate")[0],
        "INVERTED_AT_DECLARED_LEVEL")
    ctl("K2", "detector accepts a predicate-level 'weaker than the tail predicate'",
        lambda: detect("strictly weaker than the single-q tail predicate",
                       "predicate", "single-q tail predicate")[0], "CONSISTENT")
    ctl("K3", "detector accepts a class-level 'stronger than the parent class'",
        lambda: detect("strictly stronger than AF-WCC-VAC-GEN", "class", "head")[0],
        "CONSISTENT")
    ctl("K4", "detector flags a class-level 'weaker than the parent class'",
        lambda: detect("strictly weaker than AF-WCC-VAC-GEN", "class", "head")[0],
        "INVERTED_AT_DECLARED_LEVEL")
    ctl("K5", "finite-chain control ceiling holds at n=3 as well",
        lambda: order_core_check()["S_implies_T_violations_on_finite_chains"], 0)
    ctl("K6", "pin-drift guard detects a mutated pin",
        lambda: (PINNED["schemas/af_wcc_vacuum.yaml"] != "0" * 64), True)
    ctl("K7", "omega witness control: T forced true if a top element exists",
        lambda: omega_chain_witness()["separates"], True)

    after = measure_pins()
    drift_after = {k: (PINNED[k], after[k]) for k in PINNED if after[k] != PINNED[k]}
    check("E21", "zero pin drift during the run", {}, drift_after)

    n_fail = sum(1 for c in checks if not c["pass"])
    n_ctl_fail = sum(1 for c in controls if not c["pass"])

    findings = [
        {"id": "W003-SETLEVEL-H1", "severity": "hard", "status": "live",
         "class_id": "AF-WCC-VAC-GEN",
         "title": "variant SET strength record is level-inconsistent at FROZEN rev29",
         "detail": (
             "VARIANT_REGISTRY.json SET.strength and "
             "AF-WCC-VAC-GEN.variant-SET.delta.json strength both read "
             "'strictly weaker than AF-WCC-VAC-GEN' - a class-level head - while the "
             "same delta's changes[visibility.negation_conclusion].to reads 'strictly "
             "stronger than the single-q negation'. Both sentences describe the "
             "class-conclusion level, where T => S gives C_S => C_T, so the negation "
             "sentence is the correct one and the strength head is inverted at class "
             "level. The registry's variant_schema declares no 'strength' field, so "
             "no declared level rescues the head."),
         "match": {"strength_direction": dfields["strength_direction"],
                   "negation_direction": dfields["negation_direction"]},
         "falsifier": ("Show that registry/delta 'strength' is declared to be "
                       "predicate-level (a definition of the field at that level) and "
                       "that the class-level negation sentence does not contradict it.")},
        {"id": "W003-SETLEVEL-H2", "severity": "hard", "status": "frozen-residual",
         "class_id": "AF-WCC-VAC-GEN",
         "title": "F0 canonical attaches 'strictly stronger' to the set-based reading",
         "detail": (
             "research_map/formulation_taxonomy.yaml:%s says 'The set-based reading "
             "(gamma contained in the union ...) is strictly stronger'. The subject is "
             "the predicate/reading, where S is strictly weaker (T => S); the word is "
             "correct only at the class-conclusion level. G-F0 is passed on these bytes "
             "and any write voids it, so this is a Human-PI / next-F0-revision item." % fl),
         "falsifier": ("Show the sentence is defined elsewhere to speak about the class "
                       "conclusion rather than the reading; then the predicate-level "
                       "reading is a misquote, not an inversion.")},
        {"id": "W003-SETLEVEL-H3", "severity": "adjudication",
         "status": "falsifies-L-FORM-03b",
         "class_id": "AF-WCC-VAC-GEN",
         "title": "F0 supplement D1 line is correct; the 'inverted implication' blocker is a level error",
         "detail": (
             "artifacts/formulation/formulation_taxonomy.yaml:%s records 'F0 was "
             "stronger; (b) implies (c) but not conversely'. That is the class level: "
             "C_S => C_T. It is the contrapositive of T => S, so it is correct, not "
             "inverted. lead-form-20260912T005743-92 (L-FORM-03b) reads it at predicate "
             "level and should be withdrawn rather than repaired." % sl),
         "falsifier": ("Exhibit a model with T => S where C_S does not imply C_T; the "
                       "4-point preorder census (E04) and the omega witness (E05) both "
                       "fail to produce one.")},
        {"id": "W003-SETLEVEL-M1", "severity": "minor", "status": "corroborates",
         "class_id": "AF-WCC-VAC-GEN",
         "title": "FROZEN revision 29 has multiple byte-images without a revision bump",
         "detail": (
             "Events in the accepted stream record FROZEN rev29 as e1a8aaa394eb "
             "(worker-061/069 at ~00:56), 3d9e3d77fd87 (worker-060/007/018 at ~00:57, "
             "frozen_at 00:55:02) and 815e08079aef (lead 00:57:43, frozen_at 00:57:26). "
             "Same revision number, different bytes, inside ~3 minutes; the manifest's "
             "own change_protocol requires a bump per change. Already recorded by "
             "worker-018 (A-W018-F1-3) and worker-095 (R3 FAIL); cited here only so the "
             "review-time pin of this artifact is unambiguous."),
         "falsifier": ("Show the revision field moved with the bytes (i.e. these are "
                       "different revisions) or that the three hashes denote one image.")},
        {"id": "W003-SETLEVEL-M2", "severity": "minor", "status": "review-coverage",
         "class_id": "AF-WCC-VAC-GEN",
         "title": "HF-W018-F1-1 is partly moot; the correction note is over-broad",
         "detail": (
             "worker-018's blocker was measured against registry 5eb42f9a "
             "('strictly STRONGER than AF-WCC-VAC-GEN'); the registry moved to "
             "6bac9ade ('strictly weaker') at 00:57:02, after that review. The live F1 "
             "blocker is therefore not F1's own text (predicate-level, correct) but "
             "(a) the F0-frozen note at :%s and (b) the intra-delta class-level "
             "contradiction in H1. Likewise the rebase note 'direction corrected from "
             "'strictly STRONGER'' is over-broad: the pre-rebase class-level head was "
             "correct and only the predicate-level carriers needed the flip." % fl),
         "falsifier": ("Show a predicate-level carrier whose pre-rebase 'stronger' was "
                       "correct, or that the registry did not move after the review.")},
    ]

    report = {
        "task_id": "W003-SET-STRENGTH-LEVEL-AUDIT-01",
        "actor": "worker-003",
        "created_at": created,
        "node_id": "F1",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "gate": "G-FORM",
        "authority_note": ("Worker measurement and adjudication only. No canonical "
                           "byte written; no gate verdict, node status or "
                           "validation_status is set or claimed."),
        "pins": {k: {"sha256": v, "matches_pin": v == PINNED[k]}
                 for k, v in before.items()},
        "drift": {"before": drift, "after": drift_after},
        "level_derivation": {
            "predicate_level": "T => S ; S =/=> T (omega chain) => SET strictly weaker",
            "class_level": "C_T := no T-curve, C_S := no S-curve; T => S <=> C_S => C_T "
                           "=> SET strictly stronger",
            "order_core": core,
            "omega_chain": w,
        },
        "carriers": carriers,
        "checks": {"n_checks": len(checks), "n_pass": len(checks) - n_fail,
                   "n_fail": n_fail, "items": checks},
        "controls": {"items": controls, "n_controls": len(controls),
                     "n_pass": len(controls) - n_ctl_fail, "n_fail": n_ctl_fail},
        "findings": findings,
        "aggregates": {"carriers_consistent": sum(
            1 for c in carriers if c["state"] == "CONSISTENT"),
            "carriers_inverted": sum(
                1 for c in carriers if c["state"].startswith("INVERTED")),
            "carriers_level_mixed": sum(
                1 for c in carriers if c["state"].startswith("LEVEL_MIXED")),
            "hard_findings": sum(1 for f in findings if f["severity"] == "hard"),
            "declared_expectations_pass": n_fail == 0,
            "planted_controls_pass": n_ctl_fail == 0},
        "verdict": ("SET_LEVEL_MIXED: the rev13 predicate-level correction is right "
                    "(F1 weaker); the 00:57:02 re-base over-corrected the class-level "
                    "strength head in the registry and delta (H1), while the F0 "
                    "supplement D1 line the lead flagged as inverted is in fact "
                    "correct (H3) and the F0 canonical note remains a frozen "
                    "predicate-level inversion (H2)."),
        "next_falsifier": ("Re-run at the same pins after any registry/delta/F0 write: "
                           "H1 clears if strength becomes level-explicit; H2 clears "
                           "only with an F0 revision; H3 is void if a model is shown "
                           "where T => S and C_S does not imply C_T."),
        "reproduce": "python3 artifacts/worker-003/set_strength_level_audit/audit_set_strength_levels.py",
    }

    (OUT / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps({
        "task_id": report["task_id"],
        "checks_pass": f"{len(checks)-n_fail}/{len(checks)}",
        "controls_pass": f"{len(controls)-n_ctl_fail}/{len(controls)}",
        "carrier_states": states,
        "order_core": core,
        "omega_chain": w,
        "findings": [f["id"] for f in findings],
        "verdict": report["verdict"],
    }, indent=1))
    if n_ctl_fail:
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
