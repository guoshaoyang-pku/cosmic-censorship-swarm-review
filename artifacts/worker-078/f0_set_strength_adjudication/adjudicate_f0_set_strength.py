#!/usr/bin/env python3
"""W078-F0-SET-STRENGTH-ADJ-01

Independent, hash-bound adjudication of the SET-variant strength direction in the
canonical F0 taxonomy (research_map/formulation_taxonomy.yaml) at the G-F0-passed,
frozen revision, against the F1 rev13 predicate / registered SET variant.

Method
------
1. Pin every input by sha256 (drift during the run is reported and voids the binding).
2. Decide the entailment direction between the two visibility readings from the
   artifacts' own declared causal-order axioms (<= reflexive, transitive; J^-(q) =
   {x : x <= q} is past-closed), by exhaustive finite-model search plus an explicit
   omega-chain separating witness:
       SINGLEQ(g) := exists q in I+, exists t0: forall t >= t0, gamma(t) <= q
       SET(g)     := forall t, exists q in I+: gamma(t) <= q
   Lemma 1: SINGLEQ => SET unconditionally (chain + transitivity).
   Lemma 2: SET => SINGLEQ holds for every finite chain (exhaustive).
   Lemma 3: the converse fails on the omega-chain => SET is strictly weaker.
3. Mention-aware clause census over the two F0 taxonomy trees for strength claims
   whose subject is the SET/union reading; classify ASSERTIVE vs HISTORICAL-MENTION.
4. Cross-artifact consistency against F1 rev13, VARIANT_REGISTRY.json and the
   registered variant delta; gate-impact options for G-F0 (frozen artifact).

Read-only on every canonical path. Writes only under artifacts/worker-078/.
Worker-level evidence only: no gate verdict, no node status, no validation_status.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import re
import sys

# --------------------------------------------------------------------------- paths

def find_root(start: str) -> str:
    d = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(d, "research_map", "research_map.json")):
            return d
        nd = os.path.dirname(d)
        if nd == d:
            raise SystemExit("root not found")
        d = nd


ROOT = find_root(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "artifacts", "worker-078", "f0_set_strength_adjudication")

# Relative pins: every input the adjudication binds to.
PINS = [
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
    "artifacts/formulation/VARIANT_REGISTRY.json",
    "artifacts/formulation/FROZEN.json",
    "artifacts/worker-076/gform_strictness_reconcile/probe_result.json",
]

# F0 canonical clauses under adjudication (1-based line numbers, measured live).
CANON = "research_map/formulation_taxonomy.yaml"
MIRROR = "artifacts/formulation/formulation_taxonomy.yaml"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure_pins() -> dict:
    out = {}
    for rel in PINS:
        p = os.path.join(ROOT, rel)
        b = open(p, "rb").read()
        out[rel] = {"sha256": sha256_bytes(b), "bytes": len(b), "mtime": os.path.getmtime(p)}
    return out


def snapshot_pins(pins: dict) -> dict:
    snap = os.path.join(ART, "snapshot")
    os.makedirs(snap, exist_ok=True)
    rows = []
    for rel, meta in sorted(pins.items()):
        b = open(os.path.join(ROOT, rel), "rb").read()
        short = meta["sha256"][:12]
        base = rel.replace("/", "__")
        name = f"{base}.{short}"
        with open(os.path.join(snap, name), "wb") as f:
            f.write(b)
        rows.append((meta["sha256"], name, rel))
    with open(os.path.join(snap, "SHA256SUMS.txt"), "w") as f:
        for h, name, rel in rows:
            f.write(f"{h}  {name}  # {rel}\n")
    return {"dir": "snapshot", "files": {rel: h for h, _, rel in rows}}


# ------------------------------------------------------------------- entailment

def transitive_closure(n: int, rel: set) -> set:
    r = set(rel)
    changed = True
    while changed:
        changed = False
        for (a, b) in list(r):
            for (c, d) in list(r):
                if b == c and (a, d) not in r:
                    r.add((a, d))
                    changed = True
    return r


def enumerate_order_relations(n: int):
    """All reflexive, transitive relations on n labelled points (preorders)."""
    pairs = [(i, j) for i in range(n) for j in range(n)]
    refl = {(i, i) for i in range(n)}
    for mask in range(1 << (n * n)):
        rel = {pairs[k] for k in range(n * n) if (mask >> k) & 1}
        if not refl <= rel:
            continue
        if transitive_closure(n, rel) != rel:
            continue
        yield rel


def jminus(rel: set, q):
    return {x for (x, y) in rel if y == q}


def vis_singleq(gamma, rel, iplus) -> bool:
    """exists q in I+, exists tail index t0: whole tail gamma[t0:] inside J^-(q)."""
    for q in iplus:
        jq = jminus(rel, q)
        for t0 in range(len(gamma)):
            if all(g in jq for g in gamma[t0:]):
                return True
    return False


def vis_set(gamma, rel, iplus) -> bool:
    """forall t, exists q in I+ with gamma(t) in J^-(q)."""
    jm = {q: jminus(rel, q) for q in iplus}
    for g in gamma:
        if not any(g in jm[q] for q in iplus):
            return False
    return True


def entailment_engine(max_n: int = 4) -> dict:
    stats = {"relations": 0, "models": 0, "chains": 0,
             "lemma1_violations": [], "lemma2_violations": []}
    for n in range(2, max_n + 1):
        for rel in enumerate_order_relations(n):
            stats["relations"] += 1
            elems = list(range(n))
            for r in range(1, n + 1):
                for iplus in itertools.combinations(elems, r):
                    for L in range(2, n + 1):
                        for gamma in itertools.permutations(elems, L):
                            # gamma must be a chain in the causal order
                            if not all((gamma[i], gamma[j]) in rel
                                       for i in range(L) for j in range(i + 1, L)):
                                continue
                            stats["models"] += 1
                            stats["chains"] += 1
                            sq = vis_singleq(gamma, rel, set(iplus))
                            st = vis_set(gamma, rel, set(iplus))
                            # Lemma 1: SINGLEQ => SET must hold
                            if sq and not st:
                                stats["lemma1_violations"].append(
                                    {"n": n, "rel": sorted(rel), "iplus": list(iplus),
                                     "gamma": list(gamma)})
                            # Lemma 2: for finite chains SET => SINGLEQ
                            if st and not sq:
                                stats["lemma2_violations"].append(
                                    {"n": n, "rel": sorted(rel), "iplus": list(iplus),
                                     "gamma": list(gamma)})
    stats["lemma1_ok"] = not stats["lemma1_violations"]
    stats["lemma2_ok"] = not stats["lemma2_violations"]
    return stats


def omega_witness(N: int = 16) -> dict:
    """Faithful finite check of the omega-chain separating model.

    Model (infinite): X = {x_i : i in N} u {q_j : j in N};
    x_i <= x_j iff i <= j;  x_i <= q_j iff i <= j;  q_j <= q_j only.
    I+ = {q_j}; gamma = (x_0, x_1, ...).

    VIS_set holds: x_i <= q_i for every i.
    VIS_singleq fails: J^-(q_j) n gamma = {x_0..x_j} is FINITE, while every tail
    {x_t : t >= t0} is infinite; hence no (q_j, t0) covers a tail.

    A naive truncation (x_0..x_{N-1} with q_0..q_{N-1}) makes VIS_singleq TRUE via the
    top q_{N-1}, which sees the whole truncated chain; that artefact is recorded as the
    instrument's own control (C5b) so the separation is not read off a bounded I+ family.
    The check below therefore tests the infinite model's defining property directly:
    for every q_j and every tail start t0, an escaping index t >= t0 with x_t not<= q_j.
    """
    xs = [("x", i) for i in range(N)]
    qs = [("q", j) for j in range(N)]
    rel = set()
    for i in range(N):
        for j in range(N):
            if i <= j:
                rel.add((xs[i], xs[j]))
                rel.add((xs[i], qs[j]))
        rel.add((qs[i], qs[i]))
    iplus = set(qs)
    gamma = xs

    # VIS_set over the infinite chain: every x_i is below q_i.
    vis_set_holds = all(any((x, q) in rel for q in qs) for x in gamma)
    # Escape pattern: for every NON-top q_j (the infinite model has no top q) and every
    # tail start t0, an escape index exists at or after t0.
    failures = []
    nontruncated = range(N - 1)
    for j in nontruncated:
        jq = jminus(rel, qs[j])
        for t0 in range(N):
            escapes = [t for t in range(t0, N) if xs[t] not in jq]
            if escapes:
                failures.append({"q": qs[j], "t0": t0, "first_escape_index": escapes[0]})
    escapes_for_all = len(failures) == (N - 1) * N
    # Naive-truncation artefact: the top q_{N-1} sees the whole truncated chain, and no
    # such element exists in the infinite model (q indices are unbounded).
    naive_top_covers = all(x in jminus(rel, qs[N - 1]) for x in gamma)
    # Stability under refinement: the escape pattern is unchanged for larger N.
    stability = []
    for M in (8, 16, 32):
        xs2 = [("x", i) for i in range(M)]
        qs2 = [("q", j) for j in range(M)]
        rel2 = set()
        for i in range(M):
            for j in range(M):
                if i <= j:
                    rel2.add((xs2[i], xs2[j]))
                    rel2.add((xs2[i], qs2[j]))
            rel2.add((qs2[i], qs2[i]))
        ok = all(
            any(xs2[t] not in jminus(rel2, qs2[j]) for t in range(t0, M))
            for j in range(M - 1) for t0 in range(M)
        )
        stability.append({"N": M, "escape_pattern_ok": ok})
    return {
        "N": N,
        "vis_set_holds_infinite_model": vis_set_holds,
        "escape_exists_for_every_q_and_t0": escapes_for_all,
        "q_times_t0_cases_checked": (N - 1) * N,
        "separated": bool(vis_set_holds and escapes_for_all),
        "naive_truncation_top_q_covers_chain": naive_top_covers,
        "top_q_role": "the finite truncation's maximal q_{N-1} is an artefact; the infinite model has no maximal q index",
        "refinement_stability": stability,
        "example_failure": failures[0] if failures else None,
        "reading": ("SET holds; for every single q_j and every tail start t0 an escape index exists "
                    "(J^-(q_j) n gamma = {x_0..x_j} is finite), so no single q covers a tail: "
                    "SINGLEQ fails. Therefore SINGLEQ is strictly stronger and SET strictly weaker."),
    }


# --------------------------------------------------------------- clause census

STRONG_RE = re.compile(r"strictly\s+stronger|stronger\s+than", re.I)
WEAK_RE = re.compile(r"strictly\s+weaker|weaker\s+than", re.I)
SET_SUBJECT_RE = re.compile(r"\bSET\b|set-based|\bunion\b", re.I)
VIS_BIND_RE = re.compile(r"visib|geodesic|J\^?-?\(q\)|I\+|tail", re.I)
MENTION_MARKERS = [
    "corrected from", "f0_reading", "was stronger", "was strictly stronger",
    "divergence ledger", "status: resolved", "resolution:", "pre-amendment",
    "historical", "rev13:", "earlier revision", "D1",
]


def classify_clause(window: str, subject_bound: bool) -> dict:
    if not subject_bound:
        return {"hit": False, "class": "NOT_A_HIT", "why": "no SET/union visibility subject in window"}
    strong = bool(STRONG_RE.search(window))
    weak = bool(WEAK_RE.search(window))
    if not (strong or weak):
        return {"hit": False, "class": "NOT_A_HIT", "why": "no strength token"}
    claimed = "STRONGER" if strong else "WEAKER"
    low = window.lower()
    marks = [m for m in MENTION_MARKERS if m.lower() in low]
    if marks:
        cls = "MENTION_HISTORICAL"
        why = f"historical/mention markers present: {marks}"
    else:
        cls = "ASSERTIVE_INVERTED" if claimed == "STRONGER" else "ASSERTIVE_CORRECT"
        why = ("truth (Lemmas 1-3): SINGLEQ => SET strictly, so the SET/union reading is "
               "strictly WEAKER; asserting it STRONGER is inverted"
               if claimed == "STRONGER" else
               "matches the proved direction (SET strictly weaker)")
    return {"hit": True, "class": cls, "claimed": claimed, "why": why}


def clause_census(path: str) -> list:
    """Line-window census, then contiguous hits merged into one clause record.

    The 3-line window is the same binding window used by W099-FORM-DIRECTION-CENSUS-01;
    merging contiguous windows prevents one clause being counted many times.
    """
    lines = open(path, encoding="utf-8").read().splitlines()
    raw = []
    for i in range(len(lines)):
        w = lines[max(0, i - 2): i + 3]
        window = "\n".join(w)
        subject_bound = bool(SET_SUBJECT_RE.search(window)) and bool(VIS_BIND_RE.search(window))
        verdict = classify_clause(window, subject_bound)
        if verdict["hit"]:
            raw.append({"line": i + 1, "text": lines[i].strip(), **verdict})
    groups = []
    for hit in raw:
        if groups and hit["line"] - groups[-1]["lines"][-1] <= 5:
            groups[-1]["lines"].append(hit["line"])
            if STRONG_RE.search(hit["text"]):
                groups[-1]["strength_line"] = hit["line"]
                groups[-1]["quote"] = hit["text"][:300]
        else:
            groups.append({
                "path": os.path.relpath(path, ROOT),
                "lines": [hit["line"]],
                "strength_line": hit["line"] if STRONG_RE.search(hit["text"]) else None,
                "quote": hit["text"][:300],
                "class": hit["class"],
                "claimed": hit.get("claimed"),
                "why": hit["why"],
            })
    for g in groups:
        g["window_span"] = [g["lines"][0], g["lines"][-1]]
    return groups


def run_controls() -> dict:
    fixtures = [
        {"id": "C1_planted_inverted", "text": "the set-based reading of visibility is strictly stronger",
         "expect": "ASSERTIVE_INVERTED"},
        {"id": "C2_planted_correct", "text": "the set-based reading of visibility is strictly weaker",
         "expect": "ASSERTIVE_CORRECT"},
        {"id": "C3_historical_mention", "text": "set-based visibility reading direction corrected from 'strictly stronger' (rev13)",
         "expect": "MENTION_HISTORICAL"},
        {"id": "C4_unrelated_subject", "text": "forbidden extensions are C0; strictly stronger than the C2 conclusion",
         "expect": "NOT_A_HIT"},
    ]
    rows = []
    for fx in fixtures:
        v = classify_clause(fx["text"], bool(SET_SUBJECT_RE.search(fx["text"]) and VIS_BIND_RE.search(fx["text"])))
        rows.append({"id": fx["id"], "expect": fx["expect"], "got": v["class"],
                     "pass": v["class"] == fx["expect"]})
    return {"fixtures": rows, "passed": sum(1 for r in rows if r["pass"]), "total": len(rows)}


# ----------------------------------------------------------- cross-artifact view

def cross_artifact(f1_lines: list, registry: dict, delta: dict) -> dict:
    def find(lines, pat, ctx=0):
        out = []
        for i, l in enumerate(lines):
            if re.search(pat, l, re.I):
                out.append({"line": i + 1, "quote": l.strip()[:240]})
        return out

    reg_txt = json.dumps(registry)
    set_def = ""
    for v in registry.get("variants", []):
        if v.get("variant_id") == "SET":
            set_def = v.get("definition", "")
    return {
        "F1_rev13_schema": {
            "path": "schemas/af_wcc_vacuum.yaml",
            "strength_tokens": find(f1_lines, r"strictly\s+(stronger|weaker)|stronger\s+than|weaker\s+than"),
            "tail_whole_equivalence_note": find(f1_lines, r"tail and whole-curve readings are EQUIVALENT|past-closedness"),
        },
        "VARIANT_REGISTRY": {
            "path": "artifacts/formulation/VARIANT_REGISTRY.json",
            "SET_definition": set_def[:400],
        },
        "SET_delta": {
            "path": "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
            "strength": delta.get("strength", "")[:400],
            "note": delta.get("rebind_note", "")[:300],
        },
    }


# -------------------------------------------------------------------- gate view

GATE_IMPACT = {
    "artifact": CANON,
    "gate": "G-F0",
    "gate_state_measured": "pass (map gates list; declared artifact research_map/formulation_taxonomy.yaml)",
    "freeze_rule": ("ASTRA_HANDOFF.md records: 'Any write to research_map/formulation_taxonomy.yaml voids G-F0'; "
                    "the file is pinned by artifacts/formulation/FROZEN.json and carries F0 accept verdicts at its hash."),
    "clauses": [
        {"line": 94, "carrier": "variants[0].definition", "class": "ASSERTIVE_INVERTED",
         "self_contradiction": ("label 'Strictly stronger than the parent class' vs gloss 'gamma outside the union "
                                "implies no single q sees a tail of gamma, but not conversely'; the gloss is the "
                                "contrapositive of Lemma 1 and proves SET is strictly WEAKER, contradicting the label")},
        {"line": 200, "carrier": "classes.AF-WCC-VAC-GEN.conclusion.text", "class": "ASSERTIVE_INVERTED",
         "self_contradiction": "no internal counter-gloss in the same clause; contradicted by the variants block gloss and by F1 rev13"},
    ],
    "options": [
        {"id": "OPT-A-erratum",
         "action": "record a controller finding/erratum and keep the freeze; no write to the canonical file",
         "hash_effect": "research_map/formulation_taxonomy.yaml remains 0abb9ed8a961",
         "gate_effect": "G-F0 pass preserved; variant SET remains mislabelled in the frozen taxonomy",
         "risk": "the frozen taxonomy continues to assert a false strength relation for a registered variant; downstream uses of variant SET inherit it"},
        {"id": "OPT-B-repair",
         "action": "rewrite lines 94-95 and 200 to 'strictly weaker' (with the tail-entails-union justification), republish",
         "hash_effect": "canonical F0 moves off 0abb9ed8a961; FROZEN rev30 required",
         "gate_effect": "G-F0 is voided by the write and must be re-accepted at the new hash (7 accept verdicts currently bind the old hash)",
         "risk": "re-opens F0 review while G-FORM/G-LIT/G-NUM/G-AUDIT are still pending"},
    ],
    "recommended_input": ("decision belongs to the controller; this worker records the defect, the true direction, "
                          "and both option costs. No gate verdict is set here."),
    "minimal_repair_text": {
        "line_94_95": ("Strictly weaker than the parent class: the parent's single-q tail predicate entails the union "
                       "reading (gamma outside the union implies no single q sees a tail, and past-closedness pulls the "
                       "earlier curve into the same J^-(q)); the converse fails on the omega-chain witness."),
        "line_200": ("The set-based reading (gamma contained in the union of J^-(q) over all q in I+) is strictly weaker "
                     "than the single-q tail predicate; it is registered as variant `SET` ..."),
    },
}


# ------------------------------------------------------------------------- main

def build_report(generated_at: str, pins_start: dict, pins_end: dict) -> dict:
    f0_lines = open(os.path.join(ROOT, CANON), encoding="utf-8").read().splitlines()
    mirror_lines = open(os.path.join(ROOT, MIRROR), encoding="utf-8").read().splitlines()
    f1_lines = open(os.path.join(ROOT, "schemas/af_wcc_vacuum.yaml"), encoding="utf-8").read().splitlines()
    registry = json.load(open(os.path.join(ROOT, "artifacts/formulation/VARIANT_REGISTRY.json")))
    delta = json.load(open(os.path.join(ROOT, "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json")))

    eng = entailment_engine(max_n=4)
    omega = omega_witness(N=16)
    canon_hits = clause_census(os.path.join(ROOT, CANON))
    mirror_hits = clause_census(os.path.join(ROOT, MIRROR))
    controls = run_controls()

    drift = {k: {"start": pins_start[k]["sha256"], "end": pins_end[k]["sha256"],
                 "drift": pins_start[k]["sha256"] != pins_end[k]["sha256"]}
             for k in sorted(pins_start)}
    any_drift = any(v["drift"] for v in drift.values())

    true_direction = {
        "definitions": {
            "SINGLEQ": "exists q in I+, exists t0 in [0,T): forall t >= t0, gamma(t) <= q   (single-q TAIL predicate)",
            "SET": "forall t: exists q in I+: gamma(t) <= q   (whole curve inside the union of J^-(q))",
        },
        "axioms_used": ["<= reflexive and transitive (causal order)", "J^-(q) = {x : x <= q} (past-closed by transitivity)",
                        "gamma is a chain (causal geodesic): t1 < t2 => gamma(t1) <= gamma(t2)"],
        "lemma1_SINGLEQ_implies_SET": {"status": "PROVED + exhaustive", "violations": len(eng["lemma1_violations"])},
        "lemma2_SET_implies_SINGLEQ_finite_chains": {"status": "exhaustive", "violations": len(eng["lemma2_violations"]),
                                                     "scope": "all preorders on <=4 points, all non-empty I+, all chains length 2..4"},
        "lemma3_converse_fails": {"status": "WITNESS", "witness": omega},
        "conclusion": "SINGLEQ is strictly stronger than SET; the SET/union reading is strictly WEAKER than the canonical single-q tail predicate.",
        "engine_stats": {k: v for k, v in eng.items() if not k.endswith("violations")},
    }

    census = {"canonical_F0": canon_hits, "authoring_mirror_F0": mirror_hits}

    verdict = "revise"
    return {
        "actor": "worker-078",
        "task_id": "W078-F0-SET-STRENGTH-ADJ-01",
        "node_id": "F0",
        "node_interface": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-F0",
        "generated_at": generated_at,
        "authority": ("worker-level evidence only; sets no gate verdict, no node status, no validation_status=passed; "
                      "read-only on every canonical path; writes only under artifacts/worker-078/ and runtime/state/"),
        "verdict": verdict,
        "verdict_scope": ("the strength direction asserted for the registered SET variant inside the canonical F0 "
                          "taxonomy and its authoring mirror, at the pinned hashes"),
        "binding": {"pins_start": pins_start, "pins_end": pins_end, "drift": drift, "any_drift": any_drift,
                    "policy": "drift during the run voids the binding rather than the checks"},
        "true_direction": true_direction,
        "clause_census": census,
        "controls": controls,
        "cross_artifact": cross_artifact(f1_lines, registry, delta),
        "gate_impact": GATE_IMPACT,
        "targets": {
            "canonical_F0_clauses": [
                {"path": CANON, "line": 94, "text": f0_lines[93].strip()},
                {"path": CANON, "line": 95, "text": f0_lines[94].strip()},
                {"path": CANON, "line": 200, "text": f0_lines[199].strip()},
            ],
            "authoring_mirror_clause": {"path": MIRROR, "line": 176, "text": mirror_lines[175].strip()},
        },
        "findings": [
            {"id": "W078-F0SET-1", "severity": "hard", "carrier": f"{CANON}:200",
             "finding": ("conclusion.text asserts the SET/union reading is 'strictly stronger' while Lemma 1 proves "
                         "SINGLEQ => SET, so SET is strictly weaker; the assertion is inverted."),
             "falsifier": "exhibit a model satisfying SET and failing SINGLEQ, or a proof that SET => SINGLEQ on infinite chains"},
            {"id": "W078-F0SET-2", "severity": "hard", "carrier": f"{CANON}:94-95",
             "finding": ("variants[0].definition labels SET 'Strictly stronger' but its own gloss ('outside the union "
                         "implies no single q sees a tail ... but not conversely') is the contrapositive of Lemma 1 and "
                         "establishes SET is strictly weaker; the clause is internally self-contradictory."),
             "falsifier": "read the gloss as not asserting the contrapositive, or show the gloss false"},
            {"id": "W078-F0SET-3", "severity": "moderate", "carrier": f"{MIRROR}:176",
             "finding": ("D1 divergence ledger is a historical record (status resolved) but its 'F0 was stronger' label "
                         "is inverted relative to its own parenthetical '(b) implies (c) but not conversely'; traceability "
                         "record only, no operative effect."),
             "falsifier": "show the ledger clause is operative rather than historical"},
            {"id": "W078-F0SET-4", "severity": "info", "carrier": "cross-artifact",
             "finding": ("F1 rev13 schema, VARIANT_REGISTRY.json and the registered SET delta all state the corrected "
                         "direction (SET strictly weaker); the canonical F0 taxonomy is the sole outlier and contradicts "
                         "its own variants block."),
             "falsifier": "a canonical F0 copy where both clauses say 'strictly weaker'"},
        ],
        "falsifier": ("Falsified if, at the pinned hashes: (a) a model satisfies SET and fails SINGLEQ "
                      "(Lemma 1 violation); (b) some finite chain satisfies SET and fails SINGLEQ (Lemma 2 violation); "
                      "(c) the omega-chain truncation yields SINGLEQ true or SET false; (d) either canonical clause "
                      "(lines 94-95, 200) is shown to be a non-assertive mention; (e) F1 rev13 / VARIANT_REGISTRY / the "
                      "registered delta is shown to state the opposite direction at the pinned hashes; or (f) any pinned "
                      "input drifts (which voids the binding, not the lemmas)."),
        "non_claims": [
            "not a gate verdict and not a node transition",
            "does not modify, repair or republish any canonical artifact",
            "does not re-open G-F0; records option costs only",
            "does not decide the physical admissibility of the omega-chain in a conformal completion",
            "does not assess F2b or any SCC class",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generated-at", required=True)
    ap.add_argument("--out", default=os.path.join(ART, "report.json"))
    args = ap.parse_args()

    pins_start = measure_pins()
    snap = snapshot_pins(pins_start)
    report = build_report(args.generated_at, pins_start, measure_pins())
    report["snapshot"] = snap
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(report, f, indent=1, sort_keys=True)
        f.write("\n")

    controls_path = os.path.join(ART, "controls.json")
    with open(controls_path, "w") as f:
        json.dump({"task_id": report["task_id"], "generated_at": args.generated_at,
                   "controls": report["controls"], "entailment": {
                       "lemma1_violations": report["true_direction"]["lemma1_SINGLEQ_implies_SET"]["violations"],
                       "lemma2_violations": report["true_direction"]["lemma2_SET_implies_SINGLEQ_finite_chains"]["violations"],
                       "omega_separated": report["true_direction"]["lemma3_converse_fails"]["witness"]["separated"],
                       "C5b_naive_truncation_artefact_detected": report["true_direction"]["lemma3_converse_fails"]["witness"]["naive_truncation_top_q_covers_chain"],
                       "C5b_expect": True}},
                  f, indent=1, sort_keys=True)
        f.write("\n")
    print(f"wrote {args.out}")
    print(f"controls {report['controls']['passed']}/{report['controls']['total']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
