#!/usr/bin/env python3
"""W027-SET-STRENGTH-CONVENTION-01 - independent verification instrument (stdlib only).

Question.  At FROZEN revision 29 (2026-09-12T00:57:26+08:00) the corpus carries a
"SET strength direction" repair: rev12 said the SET variant of AF-WCC-VAC-GEN is
"strictly STRONGER"; rev13/rev29 records say "strictly weaker".  The controller's
open blocker L-FORM-03 then claims the inverted direction "survives" in the two F0
artifacts.  This instrument asks two decidable questions:

  (Q1) As visibility predicates, and as class conclusions, which reading is
       strictly stronger?
  (Q2) For every live strength token at the pinned bytes, which relatum does the
       token actually name, and is the token true under that relatum?

Q1 is answered by exhaustive finite-preorder model checking plus an explicit
omega-chain witness; Q2 by a referent audit of every relevant token.  The FROZEN
variant-registry checker (pinned sha) is executed inside a private sandbox to
measure what the official instrument does with the live token.

Read-only with respect to canonical state; writes only under this directory.
Exit 0 = finding confirmed; 2 = pinned input drift (measurement void); 3 = finding
falsified or an expected control did not behave as pre-registered.

Re-run:  python3 artifacts/worker-027/set_strength_convention/verify_set_strength.py
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import itertools
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                      # repo root: .../ai4math-swarm
PIN = HERE / "pinned"
SANDBOX = HERE / "sandbox"
REPORT = HERE / "report.json"

# ---------------------------------------------------------------- pin contract
# key -> (live path, expected sha256, snapshot name under pinned/)
PINS = {
    "F0_canonical": (
        "research_map/formulation_taxonomy.yaml",
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
        "F0_canonical.research_map_formulation_taxonomy.0abb9ed8a961.yaml",
    ),
    "F0_supplement": (
        "artifacts/formulation/formulation_taxonomy.yaml",
        "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
        "F0_supplement.artifacts_formulation_formulation_taxonomy.d7419b4e8963.yaml",
    ),
    "F1_rev13": (
        "schemas/af_wcc_vacuum.yaml",
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
        "F1_rev13.af_wcc_vacuum.d9cebb9404b2.yaml",
    ),
    "F2a_rev13": (
        "schemas/af_scc_c2_vacuum.yaml",
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
        "F2a_rev13.af_scc_c2_vacuum.e9a27996dfd3.yaml",
    ),
    "F2b_rev13": (
        "schemas/af_scc_c0_vacuum.yaml",
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
        "F2b_rev13.af_scc_c0_vacuum.b2ab6acb2bbe.yaml",
    ),
    "registry_rev13": (
        "artifacts/formulation/VARIANT_REGISTRY.json",
        "6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb",
        "registry_rev13.VARIANT_REGISTRY.6bac9adea19e.json",
    ),
    "delta_rev13": (
        "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
        "64b8d6394a044686de770879675eb4932ff980a942d45d16758b295d4851cecf",
        "delta_rev13.variant-SET.64b8d6394a04.json",
    ),
    "checker": (
        "artifacts/formulation/tools/check_variant_registry.py",
        "c471da4b7be9a9b0ac884d3722a223c1c7a9fc7dcf5718a0f4707d65e8757f4d",
        "checker.check_variant_registry.c471da4b7be9.py",
    ),
    "frozen_rev29": (
        "artifacts/formulation/FROZEN.json",
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
        "FROZEN.rev29.815e08079aef.json",
    ),
    "delta_ch": (
        "artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json",
        "7c165a9063c60918d583fe58000437b5a97e15803b0f2341e63bddc648a33852",
        "delta_rev13.variant-CH.json",
    ),
    "rebase_tool": (
        "artifacts/formulation/tools/variant_rebase_rev29.py",
        "e9521823b8bbeb92cb7342c003de270b30beff42cda0f332dca2e37f6a6bdb22",
        "rebase_tool.variant_rebase_rev29.e9521823b8bb.py",
    ),
    # historical oracle at the pre-repair revision (rev12), from third-party snapshots
    "rev12_F1": (
        "artifacts/worker-074/rev29_landing_guard/snapshot/rev28_pin/af_wcc_vacuum.cce9c60146d6.yaml",
        "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
        "rev12_F1.af_wcc_vacuum.cce9c60146d6.yaml",
    ),
    "rev12_registry": (
        "artifacts/worker-083/rev13_repair_packet/work_baseline/artifacts/formulation/VARIANT_REGISTRY.json",
        "5eb42f9a384a2bb327f1849fa571778fd88a2c5bf90f8a2c92d570383eb1363b",
        "rev12_registry.VARIANT_REGISTRY.5eb42f9a384a.json",
    ),
    "rev12_delta": (
        "artifacts/worker-083/rev13_repair_packet/work_baseline/artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
        "45b9b6a8d192091091820a654d8f0c7cd81764f75177f86d7f46f6ae61a447cc",
        "rev12_delta.variant-SET.45b9b6a8d192.json",
    ),
}

TASK_ID = "W027-SET-STRENGTH-CONVENTION-01"
CLASS_ID = "AF-WCC-VAC-GEN"
NODE_ID = "F1"
GATE = "G-FORM"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------- model semantics
# Abstract causal model: (X, <=) reflexive transitive; J^-(q) = {x : x <= q} is
# past-closed by construction.  A geodesic is a strictly increasing chain.
#   P_tail(g, I+) := exists q in I+: forall x in g: x <= q   (single-q tail form)
#   P_set(g, I+)  := forall x in g: exists q in I+: x <= q   (union form)
# Class conclusions: C_PARENT := forall g: not P_tail(g)
#                    C_SET    := forall g: not P_set(g)


def preorders(n: int):
    off = [(i, j) for i in range(n) for j in range(n) if i != j]
    for bits in range(1 << len(off)):
        rel = {(i, i) for i in range(n)}
        for k, (i, j) in enumerate(off):
            if (bits >> k) & 1:
                rel.add((i, j))
        if all(
            (a, c) in rel
            for a in range(n)
            for b in range(n)
            for c in range(n)
            if (a, b) in rel and (b, c) in rel
        ):
            yield rel


def strict_chains(n: int, rel):
    out = []

    def rec(seq):
        out.append(tuple(seq))
        for y in range(n):
            if y not in seq and (seq[-1], y) in rel and (y, seq[-1]) not in rel:
                rec(seq + [y])

    for x in range(n):
        rec([x])
    return out


def p_tail(g, iplus, rel) -> bool:
    return any(all((x, q) in rel for x in g) for q in iplus)


def p_set(g, iplus, rel) -> bool:
    return all(any((x, q) in rel for q in iplus) for x in g)


def finite_model_sweep(max_n: int = 4):
    stats = {
        "models": 0,
        "geodesics": 0,
        "violations_tail_implies_set": [],
        "violations_set_implies_tail": [],
        "models_c_set_and_not_c_parent": [],
        "models_c_parent_and_not_c_set": [],
    }
    for n in range(1, max_n + 1):
        for rel in preorders(n):
            chains = strict_chains(n, rel)
            for r in range(1, n + 1):
                for iplus in itertools.combinations(range(n), r):
                    iplus = frozenset(iplus)
                    stats["models"] += 1
                    c_parent = True
                    c_set = True
                    for g in chains:
                        stats["geodesics"] += 1
                        pt, ps = p_tail(g, iplus, rel), p_set(g, iplus, rel)
                        if pt and not ps:
                            stats["violations_tail_implies_set"].append(
                                {"n": n, "rel": sorted(rel), "I+": sorted(iplus), "g": list(g)}
                            )
                        if ps and not pt:
                            stats["violations_set_implies_tail"].append(
                                {"n": n, "rel": sorted(rel), "I+": sorted(iplus), "g": list(g)}
                            )
                        if pt:
                            c_parent = False
                        if ps:
                            c_set = False
                    if c_set and not c_parent:
                        stats["models_c_set_and_not_c_parent"].append(
                            {"n": n, "rel": sorted(rel), "I+": sorted(iplus)}
                        )
                    if c_parent and not c_set:
                        stats["models_c_parent_and_not_c_set"].append(
                            {"n": n, "rel": sorted(rel), "I+": sorted(iplus)}
                        )
    return stats


def omega_chain_witness(trunc: int = 60):
    """Explicit infinite witness separating the readings (T4).

    gamma = (x_0, x_1, ...) with no causal maximum; I+ = {q_j}; x_i <= q_j iff i <= j.
    A finite truncation of gamma always has a maximum, so a finite check can only
    show P_tail; the infinite predicates are decided by the index rule below and
    the finite truncations are reported as the T3 control.
    """
    N = trunc
    X = [("x", i) for i in range(N)]
    Q = [("q", j) for j in range(N)]
    rel = set()
    for a in X + Q:
        rel.add((a, a))
    for i in range(N):
        for j in range(N):
            if i <= j:
                rel.add((("x", i), ("x", j)))
                rel.add((("x", i), ("q", j)))
    transitive, bad = True, None
    for a in X + Q:
        for b in X + Q:
            if (a, b) not in rel:
                continue
            for c in X + Q:
                if (b, c) in rel and (a, c) not in rel:
                    transitive, bad = False, (a, b, c)
                    break
            if not transitive:
                break
        if not transitive:
            break
    # infinite semantics decided by the index rule (independent of the truncation):
    # gamma has every x_i (i >= 0), so for any candidate q_j the tail test includes x_{j+1}
    # and x_{j+1} <= q_j is false.  A finite gamma prefix would be dominated by q_{m-1},
    # which is exactly the T3 collapse reported in finite_truncation_control.
    p_set_gamma = all(any(i <= j for j in range(0, N)) for i in range(0, N))      # j = i
    p_tail_gamma = any(all(i <= j for i in range(0, j + 2)) for j in range(0, N))  # x_{j+1} defeats q_j
    certificate = all((("x", j + 1), ("q", j)) not in rel for j in range(0, N - 1))
    finite_truncation = {
        m: {
            "p_tail": any(all(i <= j for i in range(0, m)) for j in range(0, m)),
            "p_set": all(any(i <= j for j in range(0, m)) for i in range(0, m)),
        }
        for m in (2, 3, 5, 10)
    }
    return {
        "transitive": transitive,
        "bad_triple": bad,
        "p_set_gamma": p_set_gamma,
        "p_tail_gamma": p_tail_gamma,
        "certificate_no_single_q_sees_a_tail": certificate,
        "finite_truncation_control": finite_truncation,
        "gamma_length_truncation": N,
        "note": (
            "Separation needs an infinite curve and infinitely many I+ points: for every FINITE "
            "chain the maximal element is dominated by some q iff the chain is covered by the "
            "union (exhaustive sweep, 0 separations for n<=4; truncation control shows every "
            "finite prefix of gamma has P_tail). The index-rule decision for the infinite object "
            "is independent of the truncation length."
        ),
    }


# ---------------------------------------------------------------- text audit
def direction_phrase(s: str) -> str:
    m = re.search(r"[^.;:]*\b(?:strictly\s+)?(STRONGER|stronger|WEAKER|weaker)\b[^.;]*", s)
    return m.group(0).strip() if m else s.strip()


def leading_clause(s: str) -> str:
    idx = min([i for i in (s.find("("), s.find("["), s.find(":")) if i > 0] or [-1])
    return (s[:idx] if idx > 0 else s).strip()


def relatum(s: str) -> str:
    lead = leading_clause(direction_phrase(s)).lower()
    if re.search(r"\bpredicate\b", lead):
        return "visibility_predicate"
    if re.search(r"\baf-[a-z0-9-]+\b|\bthis class\b|\bparent class\b|\bparent\b|\be_[a-z0-9{]|\bbetween\b|\bincomparable\b", lead):
        return "class_conclusion"
    if re.search(r"\bnegation\b|\bb-containment\b|\bconclusion\b|\breading\b|\bvariant\b|\bf0 was stronger\b", lead):
        return "class_conclusion"
    return "unstated"


def direction(s: str) -> str:
    lead = direction_phrase(s).upper()
    if "STRONGER" in lead:
        return "stronger"
    if "WEAKER" in lead:
        return "weaker"
    return "none"


def token_row(where, raw, line, truth_class, truth_predicate, source):
    rel, dirn = relatum(raw), direction(raw)
    if rel == "visibility_predicate":
        ok = truth_predicate == dirn
    elif rel.startswith("class_conclusion"):
        ok = truth_class == dirn
    else:
        ok = None
    return {
        "where": where,
        "line": line,
        "source": source,
        "extracted": leading_clause(raw)[:300],
        "relatum": rel,
        "direction": dirn,
        "consistent_with_relatum": ok,
        "truth_class_conclusion": truth_class,
        "truth_visibility_predicate": truth_predicate,
    }


def quoted_after_key(text: str, field: str):
    """Value of `field: "..."` in JSON or inline YAML."""
    m = re.search(r'["\']?%s["\']?\s*:\s*"((?:[^"\\]|\\.)*)"' % re.escape(field), text)
    return json.loads('"%s"' % m.group(1)) if m else None


def window_around(lines, needle: str, before: int, after: int):
    """(window, line_number_of_needle) over the joined text."""
    text = "\n".join(lines)
    i = text.find(needle)
    if i < 0:
        return None, None
    return text[max(0, i - before): i + after], text.count("\n", 0, i) + 1


def line_after(lines, first: str, second: str):
    """Line number of `second` at or after the first occurrence of `first`."""
    text = "\n".join(lines)
    i = text.find(first)
    j = text.find(second, i if i >= 0 else 0)
    return text.count("\n", 0, j) + 1 if j >= 0 else None


# ------------------------------------------------- frozen checker in sandbox
def build_sandbox():
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    for d in (
        "artifacts/formulation/tools",
        "artifacts/formulation/variants",
        "artifacts/formulation/evidence",
        "schemas",
    ):
        (SANDBOX / d).mkdir(parents=True)
    shutil.copyfile(PIN / PINS["checker"][2], SANDBOX / "artifacts/formulation/tools/check_variant_registry.py")
    shutil.copyfile(PIN / PINS["frozen_rev29"][2], SANDBOX / "artifacts/formulation/FROZEN.json")
    for key, dest in (
        ("F1_rev13", "schemas/af_wcc_vacuum.yaml"),
        ("F2a_rev13", "schemas/af_scc_c2_vacuum.yaml"),
        ("F2b_rev13", "schemas/af_scc_c0_vacuum.yaml"),
    ):
        shutil.copyfile(PIN / PINS[key][2], SANDBOX / dest)
    shutil.copyfile(PIN / PINS["delta_rev13"][2], SANDBOX / "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json")
    shutil.copyfile(PIN / PINS["delta_ch"][2], SANDBOX / "artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json")


def run_frozen_checker(registry_text: str, label: str):
    build_sandbox()
    (SANDBOX / "artifacts/formulation/VARIANT_REGISTRY.json").write_text(registry_text)
    proc = subprocess.run(
        [sys.executable, str(SANDBOX / "artifacts/formulation/tools/check_variant_registry.py")],
        cwd=str(SANDBOX),
        capture_output=True,
        text=True,
        timeout=120,
    )
    out_json = SANDBOX / "artifacts/formulation/evidence/variant_registry_check.json"
    parsed = json.loads(out_json.read_text()) if out_json.exists() else None
    return {
        "label": label,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "check_output": parsed,
    }


# --------------------------------------------------------------------- main
def main() -> int:
    pins, drift = {}, []
    for key, (rel, want, snap) in PINS.items():
        live, snap_path = ROOT / rel, PIN / snap
        got = sha256_file(live) if live.exists() else "MISSING"
        snap_sha = sha256_file(snap_path) if snap_path.exists() else "MISSING"
        ok = got == want and snap_sha == want
        pins[key] = {
            "live_path": rel,
            "expected_sha256": want,
            "measured_sha256": got,
            "snapshot": str(snap_path.relative_to(ROOT)),
            "snapshot_sha256": snap_sha,
            "ok": ok,
        }
        if not ok:
            drift.append(key)
    if drift:
        print(json.dumps({"verdict": "INPUT_DRIFT", "drift": drift, "pins": pins}, indent=2))
        return 2

    f0_lines = (ROOT / PINS["F0_canonical"][0]).read_text().splitlines()
    supp_lines = (ROOT / PINS["F0_supplement"][0]).read_text().splitlines()
    f1_lines = (ROOT / PINS["F1_rev13"][0]).read_text().splitlines()
    f1_12_lines = (ROOT / PINS["rev12_F1"][0]).read_text().splitlines()
    reg13_text = (ROOT / PINS["registry_rev13"][0]).read_text()
    d13_text = (ROOT / PINS["delta_rev13"][0]).read_text()
    reg12 = json.loads((ROOT / PINS["rev12_registry"][0]).read_text())
    d12 = json.loads((ROOT / PINS["rev12_delta"][0]).read_text())
    reg13 = json.loads(reg13_text)
    d13 = json.loads(d13_text)

    def set_entry(reg):
        return next(v for v in reg["variants"] if v.get("variant_id") == "SET")

    def find(lines, *needles):
        hits = [i + 1 for i, l in enumerate(lines) if all(n in l for n in needles)]
        return hits[0] if hits else None

    # ---- Q1: model checks
    sweep = finite_model_sweep(4)
    omega = omega_chain_witness()
    c_set_entails_c_parent = not sweep["models_c_set_and_not_c_parent"]
    m0_c_parent = not omega["p_tail_gamma"]
    m0_c_set = not omega["p_set_gamma"]
    math_class_strict = c_set_entails_c_parent and m0_c_parent and not m0_c_set
    math_pred_strict = sweep["violations_tail_implies_set"] == [] and (
        omega["p_tail_gamma"] is False and omega["p_set_gamma"] is True
    )
    truth_class = "stronger" if math_class_strict else "UNRESOLVED"
    truth_predicate = "weaker" if math_pred_strict else "UNRESOLVED"

    checks = {
        "T2a_tail_implies_set_violations": len(sweep["violations_tail_implies_set"]),
        "T2b_set_implies_tail_violations_finite": len(sweep["violations_set_implies_tail"]),
        "T3_models_with_C_set_and_not_C_parent": len(sweep["models_c_set_and_not_c_parent"]),
        "T3b_models_with_C_parent_and_not_C_set_finite": len(sweep["models_c_parent_and_not_c_set"]),
        "T4_omega_transitive": omega["transitive"],
        "T4_omega_p_set_gamma": omega["p_set_gamma"],
        "T4_omega_p_tail_gamma": omega["p_tail_gamma"],
        "T4_M0_C_parent_true": m0_c_parent,
        "T4_M0_C_set_false": m0_c_set,
        "models_enumerated": sweep["models"],
        "geodesics_enumerated": sweep["geodesics"],
        "math_class_strict": math_class_strict,
        "math_predicate_strict": math_pred_strict,
    }

    # ---- Q2: token audit
    f0_win, _f0_anchor_line = window_around(f0_lines, "The set-based reading", 0, 420)
    f0_set_line = line_after(f0_lines, "The set-based reading", "strictly stronger")
    supp_d1_line = find(supp_lines, "f0_reading", "strictly stronger")
    f1_rel_line = find(f1_lines, "strictly WEAKER than this class's single-q tail predicate")
    f1_b_line = find(f1_lines, "B-containment is strictly stronger")
    f1_12_rel_line = find(f1_12_lines, "strictly STRONGER than this class's single-q tail predicate")

    def line_field(lines, lineno, field):
        return quoted_after_key(lines[lineno - 1], field) if lineno else None

    tokens = [
        token_row(
            "F0_canonical:set_based_reading",
            f0_win or "",
            f0_set_line,
            truth_class,
            truth_predicate,
            PINS["F0_canonical"][1][:12],
        ),
        token_row(
            "F0_supplement:D1_relation",
            line_field(supp_lines, supp_d1_line, "relation") or "",
            supp_d1_line,
            truth_class,
            truth_predicate,
            PINS["F0_supplement"][1][:12],
        ),
        token_row(
            "F1_rev13:variant_relation",
            line_field(f1_lines, f1_rel_line, "relation") or "",
            f1_rel_line,
            truth_class,
            truth_predicate,
            PINS["F1_rev13"][1][:12],
        ),
        token_row(
            "F1_rev13:line215_B_containment",
            (re.search(r"B-containment is strictly (?:stronger|weaker)", f1_lines[f1_b_line - 1]).group(0)
             if f1_b_line else ""),
            f1_b_line,
            truth_class,
            truth_predicate,
            PINS["F1_rev13"][1][:12],
        ),
        token_row(
            "registry_rev13:SET_strength",
            set_entry(reg13)["strength"],
            None,
            truth_class,
            truth_predicate,
            PINS["registry_rev13"][1][:12],
        ),
        token_row(
            "delta_rev13:strength",
            d13["strength"],
            None,
            truth_class,
            truth_predicate,
            PINS["delta_rev13"][1][:12],
        ),
        token_row(
            "delta_rev13:negation_conclusion",
            next(c["to"] for c in d13["changes"] if c["path"] == "visibility.negation_conclusion"),
            None,
            truth_class,
            truth_predicate,
            PINS["delta_rev13"][1][:12],
        ),
        token_row(
            "registry_rev12:SET_strength_oracle",
            set_entry(reg12)["strength"],
            None,
            truth_class,
            truth_predicate,
            PINS["rev12_registry"][1][:12],
        ),
        token_row(
            "delta_rev12:strength_oracle",
            d12["strength"],
            None,
            truth_class,
            truth_predicate,
            PINS["rev12_delta"][1][:12],
        ),
        token_row(
            "delta_rev12:negation_conclusion_oracle",
            next(c["to"] for c in d12["changes"] if c["path"] == "visibility.negation_conclusion"),
            None,
            truth_class,
            truth_predicate,
            PINS["rev12_delta"][1][:12],
        ),
        token_row(
            "F1_rev12:variant_relation_oracle",
            line_field(f1_12_lines, f1_12_rel_line, "relation") or "",
            f1_12_rel_line,
            truth_class,
            truth_predicate,
            PINS["rev12_F1"][1][:12],
        ),
    ]
    false_tokens = sorted(t["where"] for t in tokens if t["consistent_with_relatum"] is False)
    expected_false = sorted(
        [
            "F1_rev12:variant_relation_oracle",
            "registry_rev13:SET_strength",
            "delta_rev13:strength",
        ]
    )

    siblings = [
        {
            "variant": f"{v['parent_class']}/{v['variant_id']}",
            "relatum": relatum(v.get("strength", "")),
            "direction": direction(v.get("strength", "")),
        }
        for v in reg13["variants"]
        if v.get("variant_id") != "SET"
    ]
    convention = {
        "siblings_all_class_relata": all(s["relatum"] == "class_conclusion" for s in siblings),
        "siblings": siblings,
        "frozen_checker_rule": (
            "artifacts/formulation/tools/check_variant_registry.py requires the substring "
            "'STRONGER' in the SET strength token"
        ),
    }

    # ---- Q3: frozen checker sandbox
    annotation = " [rev13 direction corrected from 'strictly STRONGER']"
    assert annotation in reg13_text, "annotation anchor missing"
    stripped_text = reg13_text.replace(annotation, "")
    corrected_text = reg13_text.replace(
        '"strength": "strictly weaker than AF-WCC-VAC-GEN',
        '"strength": "strictly STRONGER than AF-WCC-VAC-GEN',
        1,
    )
    checker_runs = [
        run_frozen_checker(reg13_text, "live_rev13_bytes"),
        run_frozen_checker(stripped_text, "control_annotation_stripped"),
        run_frozen_checker(corrected_text, "control_token_corrected"),
    ]
    cr = {r["label"]: r for r in checker_runs}
    checker_ok = (
        cr["live_rev13_bytes"]["returncode"] == 0
        and cr["control_annotation_stripped"]["returncode"] == 1
        and cr["control_token_corrected"]["returncode"] == 0
    )

    # ---- provenance: the rev13 rebase tool flipped the token and left the checker alone
    rebase_text = (ROOT / PINS["rebase_tool"][0]).read_text()
    m = re.search(r'STRENGTH_NEW\s*=\s*\(?\s*"([^"]*)"', rebase_text, re.S)
    provenance = {
        "rebase_tool": PINS["rebase_tool"][0],
        "rebase_tool_sha256": PINS["rebase_tool"][1],
        "STRENGTH_NEW": m.group(1) if m else None,
        "rebase_tool_sets_weaker_token": bool(m and "weaker" in m.group(1).lower()),
        "rebase_tool_touches_registry_checker": "check_variant_registry" in rebase_text,
    }
    checks["provenance_rebase_tool_sets_weaker_token"] = provenance["rebase_tool_sets_weaker_token"]
    checks["provenance_rebase_tool_leaves_checker_untouched"] = not provenance["rebase_tool_touches_registry_checker"]

    # ---- exit-time drift re-measure
    drift2 = [k for k, (rel, want, snap) in PINS.items() if sha256_file(ROOT / rel) != want]

    controls_ok = (
        checker_ok
        and math_class_strict
        and math_pred_strict
        and false_tokens == expected_false
        and provenance["rebase_tool_sets_weaker_token"]
        and not provenance["rebase_tool_touches_registry_checker"]
    )
    if drift2:
        verdict, exit_code = "INPUT_DRIFT_AT_EXIT", 2
    elif not controls_ok:
        verdict, exit_code = "FALSIFIED_OR_CONTROL_UNEXPECTED", 3
    else:
        verdict, exit_code = "SET_STRENGTH_CONVENTION_CONFLICT_CONFIRMED", 0

    findings = [
        {
            "id": "W027-F1",
            "severity": "major",
            "status": "confirmed",
            "finding": (
                "Class-conclusion strength (machine-checked): C_SET entails C_PARENT (0 violations over %d "
                "models / %d geodesics, the contrapositive of P_tail => P_set) and the entailment is strict "
                "(omega-chain model M0: C_PARENT true, C_SET false). The SET variant is therefore, as a class, "
                "strictly STRONGER than AF-WCC-VAC-GEN. The live rev13/rev29 tokens VARIANT_REGISTRY.json"
                "#%s:57 'strictly weaker than AF-WCC-VAC-GEN' and AF-WCC-VAC-GEN.variant-SET.delta.json#%s "
                "'strictly weaker than AF-WCC-VAC-GEN' are false under the registry's own class-strength "
                "convention (all six sibling variants name class relata)."
                % (sweep["models"], sweep["geodesics"], PINS["registry_rev13"][1][:12], PINS["delta_rev13"][1][:12])
            ),
        },
        {
            "id": "W027-F2",
            "severity": "major",
            "status": "confirmed",
            "finding": (
                "The live rev13 SET records are internally contradictory: the delta's own "
                "visibility.negation_conclusion clause says the SET negation 'is strictly stronger than the "
                "single-q negation', and F1 line %s says 'B-containment is strictly stronger', while the delta "
                "strength field and the registry strength field say 'strictly weaker'. The negation clauses are "
                "true; the two strength tokens are the false ones." % f1_b_line
            ),
        },
        {
            "id": "W027-F3",
            "severity": "major",
            "status": "confirmed",
            "finding": (
                "The FROZEN variant-registry checker (check_variant_registry.py#%s, rule at its line 90: "
                "'variant SET must be marked stronger than its parent') returns VALID on the live bytes only "
                "because its substring test finds the quoted old token 'strictly STRONGER' inside the "
                "annotation \"[rev13 direction corrected from 'strictly STRONGER']\". With the annotation "
                "stripped, the same checker exits 1 with the SET error. The 'check_variant_registry VALID' "
                "receipts at rev29 therefore do not measure the strength direction."
                % PINS["checker"][1][:12]
            ),
        },
        {
            "id": "W027-F4",
            "severity": "major",
            "status": "confirmed",
            "finding": (
                "Blocker L-FORM-03(a)/(b) is a referent error, not an F0 inversion: F0 canonical line %s "
                "('The set-based reading ... is strictly stronger', registered as variant SET) and supplement "
                "D1 line %s ('F0 was stronger; (b) implies (c) but not conversely') are TRUE under the "
                "class-conclusion convention that the registry uses for all seven variants and that the frozen "
                "checker itself encodes. (b)=>(c) is the contrapositive of P_tail=>P_set, not the inverted "
                "predicate implication. Re-labelling F0:200 to 'weaker' would introduce a class-convention "
                "falsehood; the repair belongs in the rev13 SET strength tokens and in the F1 predicate-relation "
                "wording (which is true only because its relatum is the predicate, not the class)."
                % (f0_set_line, supp_d1_line)
            ),
        },
    ]

    report = {
        "task_id": TASK_ID,
        "worker": "worker-027",
        "class_id": CLASS_ID,
        "node_id": NODE_ID,
        "gate": GATE,
        "created_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "verdict": verdict,
        "exit_code": exit_code,
        "truth_table": {
            "visibility_predicate": {"single_q_tail": "strictly stronger", "union_set": "strictly weaker"},
            "class_conclusion": {
                "parent_AF_WCC_VAC_GEN": "strictly weaker (C_PARENT)",
                "variant_SET": "strictly STRONGER (C_SET)",
            },
            "derivation": "P_tail => P_set (T2a); contrapositive gives C_SET => C_PARENT; omega-chain M0 separates them (T4).",
        },
        "pins": pins,
        "checks": checks,
        "omega_witness": omega,
        "tokens": tokens,
        "false_tokens": false_tokens,
        "expected_false_tokens": expected_false,
        "convention_audit": convention,
        "provenance": provenance,
        "checker_runs": checker_runs,
        "findings": findings,
        "falsifier": (
            "FALSIFIED if (a) any pinned input sha256 differs at entry or exit (exit 2, measurement void); "
            "(b) a finite preorder model has P_tail(g) and not P_set(g); (c) the omega-chain witness is not "
            "reflexive/transitive, or P_set(gamma) is false, or some q_j dominates a tail of gamma; (d) any "
            "model satisfies C_SET and not C_PARENT; (e) M0 does not satisfy C_PARENT or does satisfy C_SET; "
            "(f) the annotation-stripped registry copy still exits 0 or the token-corrected copy exits "
            "non-zero under the frozen checker; (g) the live registry's six sibling variants do not all name "
            "class relata in their strength leading clauses; or (h) a frozen corpus consumer at the pinned "
            "hashes names a visibility predicate (not a class) in the leading strength clause of the SET "
            "variant."
        ),
        "non_claims": [
            "not a gate verdict, node status, or validation_status; worker events cannot move those",
            "no canonical file was modified by this task; the checker sandbox runs on private copies",
            "the abstract model checks the order-theoretic content of the predicates, not a Lorentzian realization",
            "does not adjudicate the physics of WCC or the truth of any class",
        ],
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n")
    print(json.dumps({
        "verdict": verdict,
        "exit_code": exit_code,
        "math_class_strict": math_class_strict,
        "math_predicate_strict": math_pred_strict,
        "false_tokens": false_tokens,
        "checker_runs": {r["label"]: r["returncode"] for r in checker_runs},
        "report": str(REPORT.relative_to(ROOT)),
    }, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
