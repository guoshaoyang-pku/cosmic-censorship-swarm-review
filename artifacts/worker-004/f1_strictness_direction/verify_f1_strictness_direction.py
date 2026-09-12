#!/usr/bin/env python3
"""W004-F1-STRICTNESS-DIRECTION-INDEP-01 — independent verification of the F1 rev13
visibility strictness-direction correction.

Read-only on every canonical path. Fails closed (exit 3) if any pinned input drifts.
Exit 0 = all pre-registered expectations held and all controls fired.
Exit 2 = an expectation was refuted. Exit 3 = pin drift.

Usage:
  python3 verify_f1_strictness_direction.py [--prereg PATH] [--outdir PATH] [--quiet]

The instrument:
  A. verifies pins and F1's declared F0 binding;
  B. independently reproduces the direction result (whole/tail equivalence under
     transitivity; single-q tail => SET; SET => single-q when the chain has a causal
     maximum; strict separation by an omega-chain without causal maximum);
  C. scans the pinned class corpus for live statements asserting the superseded
     opposite direction;
  D. runs six pre-registered controls.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import itertools
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------
# A. pins
# --------------------------------------------------------------------------
def measure_pins(pins: dict) -> dict:
    out = {}
    for rel, want in pins.items():
        p = ROOT / rel
        got = sha256_file(p) if p.is_file() else None
        out[rel] = {"pinned": want, "measured": got, "match": got == want}
    return out


# --------------------------------------------------------------------------
# B. direction mathematics on finite preorders
# --------------------------------------------------------------------------
def all_preorders(n: int) -> list:
    """All reflexive, transitive relations on {0..n-1} as bitmasks over ordered pairs."""
    pairs = [(i, j) for i in range(n) for j in range(n)]
    idx = {p: k for k, p in enumerate(pairs)}
    rels = []
    off = [p for p in pairs if p[0] != p[1]]
    for bits in range(1 << len(off)):
        R = 0
        for i in range(n):
            R |= 1 << idx[(i, i)]
        for k, p in enumerate(off):
            if bits >> k & 1:
                R |= 1 << idx[p]
        # transitivity
        ok = True
        for a, b in pairs:
            if not (R >> idx[(a, b)] & 1):
                continue
            for c in range(n):
                if (R >> idx[(b, c)] & 1) and not (R >> idx[(a, c)] & 1):
                    ok = False
                    break
            if not ok:
                break
        if ok:
            rels.append((R, idx))
    return rels


def all_reflexive(n: int) -> list:
    pairs = [(i, j) for i in range(n) for j in range(n)]
    idx = {p: k for k, p in enumerate(pairs)}
    off = [p for p in pairs if p[0] != p[1]]
    rels = []
    for bits in range(1 << len(off)):
        R = 0
        for i in range(n):
            R |= 1 << idx[(i, i)]
        for k, p in enumerate(off):
            if bits >> k & 1:
                R |= 1 << idx[p]
        rels.append((R, idx))
    return rels


def chains(n: int, R: int, idx: dict) -> list:
    """All causal chains of distinct points, length 2..n, consecutive points related."""
    out = []
    for m in range(2, n + 1):
        for perm in itertools.permutations(range(n), m):
            if all((R >> idx[(perm[i], perm[i + 1])] & 1) for i in range(m - 1)):
                out.append(perm)
    return out


def contained(chain, subset, R, idx) -> bool:
    return all((R >> idx[(p, q)] & 1) for p in subset for q in [chain[-1]])


def jminus_contains(chain, subset, q, R, idx) -> bool:
    return all((R >> idx[(p, q)] & 1) for p in subset)


def whole_tail_separations(n: int, R: int, idx: dict) -> int:
    """Count (chain, q) where a proper tail is in J^-(q) but the whole chain is not."""
    bad = 0
    for ch in chains(n, R, idx):
        for q in range(n):
            for k in range(1, len(ch)):
                if jminus_contains(ch, ch[k:], q, R, idx) and not jminus_contains(ch, ch, q, R, idx):
                    bad += 1
    return bad


def single_implies_set(n: int, R: int, idx: dict) -> int:
    """Violations of: (exists q,k: tail_k in J^-(q)) => whole chain in union over all q."""
    bad = 0
    for ch in chains(n, R, idx):
        single = any(
            jminus_contains(ch, ch[k:], q, R, idx) for q in range(n) for k in range(1, len(ch))
        )
        union = all(any((R >> idx[(p, q)] & 1) for q in range(n)) for p in ch)
        if single and not union:
            bad += 1
    return bad


def set_implies_single_at_max(n: int, R: int, idx: dict) -> int:
    """Violations of: (whole chain in the union) => (exists q,k: tail_k in J^-(q)),
    given the chain has a causal maximum (true for every finite chain)."""
    bad = 0
    for ch in chains(n, R, idx):
        union = all(any((R >> idx[(p, q)] & 1) for q in range(n)) for p in ch)
        single = any(
            jminus_contains(ch, ch[k:], q, R, idx) for q in range(n) for k in range(1, len(ch))
        )
        if union and not single:
            bad += 1
    return bad


def omega_chain_witness(N: int = 64) -> dict:
    """The omega-chain witness as an index rule on the infinite carrier
       {p_0,p_1,...} u {q_0,q_1,...}:
         p_i <= p_j  iff i <= j ;  p_i <= q_m iff i <= m ;  q's are maximal.
       The rule is checked on a representative window 0..N of a uniform family:
       for every m the tail element p_{max(k,m+1)} is NOT in J^-(q_m), so no q_m
       contains the tail {p_k,p_{k+1},...}; and every p_n has a strict successor."""
    def le(a, b):
        if a == b:
            return True
        ta, ia = a
        tb, ib = b
        if tb == "q":
            return ta == "p" and ia <= ib
        if ta == "q":
            return False
        return ia <= ib

    k = N // 2
    elems = [("p", i) for i in range(N + 1)] + [("q", m) for m in range(N + 1)]
    reflexive = all(le(x, x) for x in elems)
    transitive = all(
        (not (le(x, y) and le(y, z))) or le(x, z) for x in elems for y in elems for z in elems
    )
    set_holds = all(le(("p", j), ("q", j)) for j in range(N + 1))
    # no q_m contains the infinite tail: witness index max(k, m+1)
    every_q_fails = all(not le(("p", max(k, m + 1)), ("q", m)) for m in range(N + 1))
    no_max = all(le(("p", n), ("p", n + 1)) and not le(("p", n + 1), ("p", n))
                 for n in range(N))
    return {
        "reflexive": reflexive,
        "transitive": transitive,
        "set_predicate_holds": set_holds,
        "single_q_predicate_holds": not every_q_fails,
        "chain_has_no_causal_maximum": no_max,
        "every_q_fails_a_tail_element": every_q_fails,
        "tail_start_index": k,
        "strict_separation": set_holds and every_q_fails and no_max,
        "window": N,
    }


@functools.lru_cache(maxsize=1)
def direction_analysis() -> dict:
    n = 4
    pre = all_preorders(n)
    ref = all_reflexive(n)
    wt = sum(whole_tail_separations(n, R, idx) for R, idx in pre)
    s2set = sum(single_implies_set(n, R, idx) for R, idx in pre)
    set2s = sum(set_implies_single_at_max(n, R, idx) for R, idx in pre)
    # non-transitive positive control: find the first reflexive-only relation with a separation
    nt_witness = None
    nt_sep = 0
    for R, idx in ref:
        s = whole_tail_separations(n, R, idx)
        if s:
            nt_sep += s
            if nt_witness is None:
                nt_witness = R
    return {
        "n_points": n,
        "preorder_count": len(pre),
        "reflexive_only_count": len(ref),
        "whole_tail_separations_transitive": wt,
        "single_implies_set_violations": s2set,
        "set_implies_single_at_causal_max_violations": set2s,
        "nontransitive_relation_count_with_separation": sum(
            1 for R, idx in ref if whole_tail_separations(n, R, idx) > 0
        ),
        "nontransitive_first_witness_found": nt_witness is not None,
        "omega_chain": omega_chain_witness(),
    }


# --------------------------------------------------------------------------
# C. corpus direction scan
# --------------------------------------------------------------------------
STRENGTH = re.compile(r"strict(?:ly)?\s+(STRONGER|stronger|WEAKER|weaker)", re.I)
SET_SUBJECT = re.compile(
    r"set-based|set based|contained in the union|union of J|union reading|J\^?-?\(I\+\)\s+as a set",
    re.I)
HISTORICAL = re.compile(
    r"corrected from|was stronger|were stronger|assertion was false|was false|were false|"
    r"\bearlier\b|\bsuperseded\b|\brev1[23]\b|\bnon-sequitur\b|"
    r"\bpreviously\b|\berratum\b|MUST NOT be interchanged|\"from\"\s*:",
    re.I,
)


def strength_polarity(window: str):
    """Return 'stronger'/'weaker' for the strength phrase that co-occurs with a
    SET subject, or None when the window has no SET-subject strength claim."""
    if not SET_SUBJECT.search(window):
        return None
    for m in STRENGTH.finditer(window):
        return "stronger" if m.group(1).lower() == "stronger" else "weaker"
    return None


def scan_text(text: str, relpath: str) -> list:
    lines = text.splitlines()
    out = []
    for i, line in enumerate(lines):
        if not STRENGTH.search(line):
            continue
        lo, hi = max(0, i - 2), min(len(lines), i + 3)
        window = "\n".join(lines[lo:hi])
        polarity = strength_polarity(window)
        if polarity is None:
            continue
        historical = bool(HISTORICAL.search(window))
        out.append({
            "file": relpath,
            "line": i + 1,
            "match": STRENGTH.search(line).group(0),
            "polarity": polarity,
            "historical_or_quoted": historical,
            "snippet": " / ".join(s.strip() for s in lines[lo:hi] if s.strip())[:400],
        })
    return out


def corpus_scan(files: list) -> dict:
    per_file = {}
    live, hist, correct = [], [], []
    for rel in files:
        p = ROOT / rel
        if not p.is_file():
            per_file[rel] = {"present": False, "matches": []}
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        matches = scan_text(text, rel)
        per_file[rel] = {"present": True, "matches": matches}
        for m in matches:
            if m["historical_or_quoted"]:
                hist.append(m)
            elif m["polarity"] == "stronger":
                live.append(m)
            else:
                correct.append(m)
    return {"per_file": per_file, "live_opposite_direction_statements": live,
            "live_correct_direction_statements": correct,
            "historical_or_quoted_matches": hist}


# --------------------------------------------------------------------------
# D. structural checks on F1 rev13 vs the pinned rev12 predecessor
# --------------------------------------------------------------------------
def flat_leaves(obj, pre=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flat_leaves(v, f"{pre}/{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flat_leaves(v, f"{pre}[{i}]"))
    else:
        out[pre] = obj
    return out


def f1_leaf_checks() -> dict:
    import yaml
    new = yaml.safe_load(open(ROOT / "schemas/af_wcc_vacuum.yaml"))
    old = yaml.safe_load(open(
        ROOT / "artifacts/worker-060/rev29_binding_acceptance/snapshots/"
               "f1__af_wcc_vacuum.cce9c60146d6.yaml"))
    a, b = flat_leaves(old), flat_leaves(new)
    changed = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    semantic = [k for k in changed if not k.startswith("/f0_binding") and k != "/revision"
                and not k.startswith("/revision_history") and k != "/revised_at"]
    variant = new["class_identity_variants"][0]["relation"]
    d5 = new["quantifiers"]["domains"]["D5"]["definition"]
    vis = new["visibility"]["definition"]
    neg = new["visibility"]["negation_conclusion"]
    ri = new["revision_history"][-1]
    note = " ".join(str(x) for x in ri.get("notes", []))
    return {
        "changed_leaf_count": len(changed),
        "changed_leaves": changed,
        "semantic_changed_leaves": semantic,
        "variant_relation_says_weaker": "strictly WEAKER" in variant,
        "d5_says_equivalent": "EQUIVALENT" in d5,
        "visibility_says_equivalent": "EQUIVALENT" in vis,
        "negation_keeps_single_q_tail_form": "tail gamma([t0,T)) is NOT contained" in neg,
        "revision_note_discloses_direction_correction": (
            "corrected from 'strictly STRONGER' to 'strictly WEAKER'" in note
        ),
        "f0_binding_declared": new["f0_binding"]["declared_f0_sha256"],
        "rev12_snapshot_variant_says_stronger": "strictly STRONGER" in (
            old["class_identity_variants"][0]["relation"]),
    }


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def analyse(prereg_path: Path) -> dict:
    prereg = json.loads(prereg_path.read_text())
    pins = prereg["pins"]
    pin_start = measure_pins(pins)
    drift = sorted([k for k, v in pin_start.items() if not v["match"]])

    result = {
        "task_id": prereg["task_id"],
        "actor": prereg["actor"],
        "runtime_instance": prereg["runtime_instance"],
        "class_id": prereg["class_id"],
        "node_id": prereg["node_id"],
        "gate": prereg["gate"],
        "measured_at": now(),
        "pins_at_start": pin_start,
        "pin_drift": drift,
    }
    if drift:
        result["verdict"] = "PIN_DRIFT"
        result["exit"] = 3
        return result

    f1 = f1_leaf_checks()
    f0_sha = pin_start["research_map/formulation_taxonomy.yaml"]["measured"]
    f1["f0_binding_resolves_to_pinned_f0"] = f1["f0_binding_declared"] == f0_sha
    dirn = direction_analysis()

    scan_files = [
        "schemas/af_wcc_vacuum.yaml",
        "research_map/formulation_taxonomy.yaml",
        "artifacts/formulation/formulation_taxonomy.yaml",
        "artifacts/formulation/VARIANT_REGISTRY.json",
        "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
        "artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json",
        "artifacts/formulation/rule_spec.json",
    ]
    scan = corpus_scan(scan_files)
    per = {k: len(v["matches"]) for k, v in scan["per_file"].items()}
    live = scan["live_opposite_direction_statements"]
    live_f1 = [m for m in live if m["file"] == "schemas/af_wcc_vacuum.yaml"]
    live_reg = [m for m in live if m["file"] == "artifacts/formulation/VARIANT_REGISTRY.json"]
    live_delta = [m for m in live
                  if m["file"].endswith("AF-WCC-VAC-GEN.variant-SET.delta.json")]
    live_f0 = [m for m in live if m["file"] == "research_map/formulation_taxonomy.yaml"]
    live_supp = [m for m in live if m["file"] == "artifacts/formulation/formulation_taxonomy.yaml"]

    checks = {
        "E1_pins_and_predecessor_stable": all(v["match"] for v in pin_start.values()),
        "E2_whole_tail_separations_zero": dirn["whole_tail_separations_transitive"] == 0,
        "E3_preorder_count_355": dirn["preorder_count"] == 355,
        "E4_nontransitive_positive_control_fires": dirn["nontransitive_first_witness_found"],
        "E5_single_implies_set_zero_violations": dirn["single_implies_set_violations"] == 0,
        "E6_set_implies_single_at_max_zero_violations":
            dirn["set_implies_single_at_causal_max_violations"] == 0,
        "E7_omega_chain_strict_separation": dirn["omega_chain"]["strict_separation"],
        "E8a_f1_rev13_no_opposite_statement": len(live_f1) == 0,
        "E8b_registry_no_opposite_statement": len(live_reg) == 0,
        "E8c_set_delta_no_opposite_statement": len(live_delta) == 0,
        "E8d_f0_canonical_opposite_statements_ge_2": len(live_f0) >= 2,
        "E9_revision_note_discloses_correction":
            f1["revision_note_discloses_direction_correction"],
        "E1b_f1_binds_the_pinned_f0": f1["f0_binding_resolves_to_pinned_f0"],
    }

    findings = []
    if live_f0:
        findings.append({
            "id": "W004-DIR-01",
            "severity": "major",
            "status": "open",
            "summary": (
                "The frozen canonical F0 taxonomy research_map/formulation_taxonomy.yaml#"
                "0abb9ed8a961 states the SUPERSEDED direction (SET reading 'strictly stronger') "
                "in its variants block and in the AF-WCC-VAC-GEN conclusion text, while "
                "schemas/af_wcc_vacuum.yaml#d9cebb9404b2 (rev13) - whose f0_binding declares that "
                "exact F0 hash - the VARIANT_REGISTRY and the SET delta all assert SET is "
                "STRICTLY WEAKER. The independent direction proof below agrees with rev13. "
                "F0 is frozen and G-F0 passed on it, so this is a live cross-artifact "
                "contradiction requiring an owner/controller disposition (F0 revision + G-F0 "
                "re-verification, or an explicit erratum recording the F0 text as a known "
                "residual)."),
            "locations": [{"file": m["file"], "line": m["line"], "snippet": m["snippet"]}
                          for m in live_f0],
        })
    if live_supp:
        findings.append({
            "id": "W004-DIR-02",
            "severity": "minor",
            "status": "open",
            "summary": (
                "artifacts/formulation/formulation_taxonomy.yaml#d7419b4e8963 (F0 companion "
                "supplement) records D1 as 'F0 was stronger' although the F0 'stronger' claim "
                "was itself backwards; the historical record should say F0 ASSERTED stronger, "
                "not that it WAS stronger."),
            "locations": [{"file": m["file"], "line": m["line"], "snippet": m["snippet"]}
                          for m in live_supp],
        })

    result.update({
        "f1_rev13_vs_rev12": f1,
        "direction_analysis": dirn,
        "corpus_scan_counts": per,
        "live_opposite_direction_statements": live,
        "historical_or_quoted_matches": scan["historical_or_quoted_matches"],
        "checks": checks,
        "findings": findings,
        "axis_verdict_on_f1_rev13_direction": (
            "accept" if all(checks[k] for k in (
                "E2_whole_tail_separations_zero", "E5_single_implies_set_zero_violations",
                "E6_set_implies_single_at_max_zero_violations", "E7_omega_chain_strict_separation",
                "E8a_f1_rev13_no_opposite_statement",
                "E9_revision_note_discloses_correction")) else "revise"),
        "overall_verdict": "revise" if live_f0 else "accept",
        "verdict_basis": (
            "axis accept: the F1 rev13 direction text is mathematically correct and disclosed; "
            "overall revise: the frozen F0 parent artifact still asserts the opposite direction"
            if live_f0 else
            "axis accept and corpus direction-consistent"),
        "non_claims": prereg["non_claims"] + [
            "workers cannot set a gate verdict or node status; this is advisory evidence",
        ],
    })
    result["exit"] = 0 if all(checks.values()) else 2
    # exit 0 iff every expectation held; the overall verdict may still be revise (finding)
    result["pins_at_exit"] = measure_pins(pins)
    result["pin_drift_at_exit"] = sorted(
        k for k, v in result["pins_at_exit"].items() if not v["match"])
    if result["pin_drift_at_exit"]:
        result["exit"] = 3
    return result


# --------------------------------------------------------------------------
# controls
# --------------------------------------------------------------------------
def run_controls(prereg_path: Path, outdir: Path) -> dict:
    import shutil
    ctrl = {}
    sandbox = outdir / "controls_sandbox"
    sandbox.mkdir(parents=True, exist_ok=True)

    # C1 pin drift -> exit 3
    bad = json.loads(prereg_path.read_text())
    first = sorted(bad["pins"])[0]
    bad["pins"][first] = "0" * 64
    badp = sandbox / "prereg_bad_pin.json"
    badp.write_text(json.dumps(bad))
    proc = subprocess.run(
        [sys.executable, str(HERE / "verify_f1_strictness_direction.py"),
         "--prereg", str(badp), "--outdir", str(sandbox / "c1_out"), "--quiet",
         "--no-controls"],
        capture_output=True, text=True, cwd=str(ROOT))
    ctrl["C1_pin_drift_fails_closed_exit3"] = {
        "fired": proc.returncode == 3, "exit": proc.returncode,
        "detail": proc.stdout.strip()[-200:] or proc.stderr.strip()[-200:]}

    # C2 planted inversion in an F1 copy (historical rev13 bracket stripped so the sandbox
    # contains a *live* opposite assertion) plus a synthetic live-style assertion.
    f1_text = (ROOT / "schemas/af_wcc_vacuum.yaml").read_text()
    inv = f1_text.replace("strictly WEAKER than this class", "strictly STRONGER than this class", 1)
    inv = re.sub(r"\s*\[rev13: direction corrected from.*?\]", "", inv, flags=re.S)
    p = sandbox / "f1_inverted.yaml"
    p.write_text(inv)
    matches = scan_text(inv, "sandbox/f1_inverted.yaml")
    synthetic = (
        "The set-based reading (gamma contained in the union of J^-(q) over all q in I+) "
        "is strictly stronger; it is registered as variant SET of this class."
    )
    synth_matches = scan_text(synthetic, "sandbox/synthetic_live_assertion.txt")
    ctrl["C2_planted_inversion_flagged"] = {
        "fired": (any(not m["historical_or_quoted"] and m["polarity"] == "stronger"
                      for m in matches)
                  and any(not m["historical_or_quoted"] and m["polarity"] == "stronger"
                          for m in synth_matches)),
        "live_opposite_matches": len([m for m in matches
                                      if not m["historical_or_quoted"]
                                      and m["polarity"] == "stronger"]),
        "synthetic_live_assertion_flagged": len(
            [m for m in synth_matches
             if not m["historical_or_quoted"] and m["polarity"] == "stronger"]) == 1,
        "changed": inv != f1_text}

    # C3 planted repair in an F0 copy -> 0 live opposite statements
    f0_text = (ROOT / "research_map/formulation_taxonomy.yaml").read_text()
    fixed = f0_text.replace("Strictly stronger than the parent class", "Strictly weaker than the parent class")
    fixed = fixed.replace("is strictly stronger", "is strictly weaker")
    p2 = sandbox / "f0_repaired.yaml"
    p2.write_text(fixed)
    m2 = scan_text(fixed, "sandbox/f0_repaired.yaml")
    ctrl["C3_planted_f0_repair_clears_contradiction"] = {
        "fired": len([m for m in m2 if not m["historical_or_quoted"]
                      and m["polarity"] == "stronger"]) == 0,
        "live_opposite_matches_after_repair": len(
            [m for m in m2 if not m["historical_or_quoted"] and m["polarity"] == "stronger"]),
        "changed": fixed != f0_text}

    # C4 non-transitive positive control (already computed in direction_analysis)
    d = direction_analysis()
    ctrl["C4_nontransitive_positive_control"] = {
        "fired": d["nontransitive_first_witness_found"],
        "relations_with_separation": d["nontransitive_relation_count_with_separation"]}

    # C5 determinism: two identical analyses (excluding timestamps)
    a = analyse(prereg_path)
    b = analyse(prereg_path)
    for r in (a, b):
        r.pop("measured_at", None)
        r.pop("pins_at_exit", None)
        r.pop("pin_drift_at_exit", None)
    ctrl["C5_deterministic_payload"] = {
        "fired": json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)}

    # C6 exhaustive count
    ctrl["C6_preorder_count_355"] = {"fired": d["preorder_count"] == 355,
                                     "count": d["preorder_count"]}
    return ctrl


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prereg", default=str(HERE / "PREREGISTRATION.json"))
    ap.add_argument("--outdir", default=str(HERE))
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--no-controls", action="store_true",
                    help="skip the control battery (used by the C1 pin-drift control to avoid recursion)")
    a = ap.parse_args()
    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    res = analyse(Path(a.prereg))
    (outdir / "report.json").write_text(json.dumps(res, indent=1, sort_keys=True))

    if a.no_controls or res["exit"] == 3:
        ctrl = {"battery": "skipped",
                "reason": "pin drift exit 3" if res["exit"] == 3 else "--no-controls"}
    else:
        ctrl = run_controls(Path(a.prereg), outdir)
    (outdir / "controls.json").write_text(json.dumps(ctrl, indent=1, sort_keys=True))

    if not a.quiet:
        print(f"{res['task_id']}: exit={res['exit']} overall_verdict={res.get('overall_verdict')} "
              f"axis={res.get('axis_verdict_on_f1_rev13_direction')}")
        for k, v in res.get("checks", {}).items():
            print(f"  {'PASS' if v else 'FAIL'}  {k}")
        for f in res.get("findings", []):
            print(f"  FINDING {f['id']} ({f['severity']}): {f['summary'][:160]}")
        for k, v in ctrl.items():
            if isinstance(v, dict):
                print(f"  control {'PASS' if v.get('fired') else 'FAIL'}  {k}")
    return res["exit"]


if __name__ == "__main__":
    sys.exit(main())
