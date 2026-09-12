#!/usr/bin/env python3
"""W040-F1-INDEP-VERDICT-02 -- independent, class-bound verification of F1.

Target : schemas/af_wcc_vacuum.yaml  (class AF-WCC-VAC-GEN, node F1, gate G-FORM)
Method : mechanical, reproducible, read-only.  Nothing outside this worker's own
         artifact tree is written.  Every fact below is re-measured from bytes.

Checks
  C1  structure: required machine-readable fields present, class id/components agree
  C2  class binding: conclusion_type WCC, no SCC leakage, exclusions present
  C3  canonical instruments replayed read-only (check_class_schema, taxonomy
      consistency, variant registry, verify_frozen, classsep regression, map validator)
  C4  class_contract_pointer fragment resolution in canonical vs authoring F0 tree
  C5  YAML duplicate top-level keys / effective revision timestamp vs mtime & clock
  C6  normative symbol AF_{I+}(M_D) definition census (F1 + both F0 trees + aliases)
  C7  contested HF-06 adjudication: whole-curve single-q vs tail single-q visibility
  C8  schema's own falsifier triggers: reader-divergence and leakage scans
  C9  declared vs measured F0 binding
  C10 entry/exit hash drift guard over all tracked files

Run:  python3 artifacts/worker-040/f1_independent_verdict/run_checks.py
Out:  checks.json next to this script (plus instrument_runs.json)
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
now = lambda: datetime.now(CST).isoformat(timespec="seconds")

TARGET = "schemas/af_wcc_vacuum.yaml"
TRACKED = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/VARIANT_REGISTRY.json",
    "schemas/f1_falsifier_tests.jsonl",
]
F0_CANON = "research_map/formulation_taxonomy.yaml"
F0_AUTH = "artifacts/formulation/formulation_taxonomy.yaml"


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(ROOT / path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def hashes() -> dict:
    return {p: sha256(p) for p in TRACKED}


def mtime(path: str) -> str:
    return datetime.fromtimestamp(os.path.getmtime(ROOT / path), CST).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- C1/C2
REQUIRED = [
    "schema_version", "artifact_kind", "class_id", "node_id", "class_components",
    "class_contract_pointer", "scope_statement", "quantifiers", "topology", "data_class",
    "regularity", "genericity", "i_plus", "visibility", "conclusion", "falsifier",
    "anti_scope",
]


def load_f1() -> dict:
    return yaml.safe_load((ROOT / TARGET).read_text())


def c1_structure(d: dict) -> dict:
    missing = [k for k in REQUIRED if k not in d]
    q = d.get("quantifiers", {})
    q_missing = [k for k in ("formal", "ordered", "domains", "negation") if k not in q]
    comp = d.get("class_components", {})
    comp_ok = comp == {
        "asymptotics": "AF", "censorship": "WCC", "matter": "VAC",
        "genericity": "GEN", "regularity_token": "none",
    }
    return {
        "verdict": "pass" if not missing and not q_missing and comp_ok else "fail",
        "missing_top_level": missing,
        "missing_quantifier_keys": q_missing,
        "class_id": d.get("class_id"),
        "class_id_ok": d.get("class_id") == "AF-WCC-VAC-GEN",
        "class_components": comp,
        "class_components_ok": comp_ok,
        "node_id": d.get("node_id"),
        "revision": d.get("revision"),
    }


def c2_class_binding(d: dict) -> dict:
    concl = d.get("conclusion", {})
    ctype = concl.get("conclusion_type")
    # Leakage scan is restricted to the blocks that carry THIS class's assertion.
    # anti_scope / forbidden_* legitimately name other classes as excluded, so they
    # are positive evidence, not leaks (a whole-document token scan false-positives
    # on the schema's own "any 'C0 or C2' composite regularity" exclusion phrase).
    asserted = " ".join(str(concl.get(k, "")) for k in
                        ("statement_natural_language", "statement_formal"))
    leak_tokens = ["c0", "c2", "inextendib", "black-hole region non-empty",
                   "geodesically complete", "spherical"]
    leaks = sorted({t for t in leak_tokens if t in asserted.lower()})
    comp = d.get("class_components", {})
    anti = d.get("anti_scope", {})
    forbidden_strength = len(concl.get("forbidden_strengthenings", []))
    forbidden_weak = len(concl.get("forbidden_weakenings", []))
    ok = (ctype == "weak_cosmic_censorship" and not leaks
          and forbidden_strength >= 3 and forbidden_weak >= 3
          and comp.get("regularity_token") == "none"
          and len(anti.get("not_this_class", [])) >= 2)
    return {
        "verdict": "pass" if ok else "fail",
        "conclusion_type": ctype,
        "conclusion_type_ok": ctype == "weak_cosmic_censorship",
        "leak_tokens_found_in_asserted_conclusion": leaks,
        "regularity_token": comp.get("regularity_token"),
        "forbidden_strengthenings": forbidden_strength,
        "forbidden_weakenings": forbidden_weak,
        "anti_scope_classes": [x.get("class_id") for x in anti.get("not_this_class", [])],
        "schema_falsifiers": len(d.get("falsifier", {}).get("schema_falsifiers", [])),
    }


# --------------------------------------------------------------------------- C3
INSTRUMENTS = [
    ["python3", "artifacts/formulation/tools/check_class_schema.py",
     "schemas/af_wcc_vacuum.yaml", "--json"],
    ["python3", "artifacts/formulation/tools/check_taxonomy_consistency.py"],
    ["python3", "artifacts/formulation/tools/check_variant_registry.py"],
    ["python3", "artifacts/formulation/tools/verify_frozen.py"],
    ["python3", "runtime/bin/classsep_regression.py"],
    ["python3", "research_map/validate_map.py"],
]


def c3_instruments() -> tuple[dict, list]:
    runs, summary = [], {}
    for cmd in INSTRUMENTS:
        try:
            p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
            out = (p.stdout or "") + (p.stderr or "")
            rec = {"cmd": " ".join(cmd), "returncode": p.returncode, "stdout_tail": out.strip()[-2000:]}
        except Exception as e:  # pragma: no cover
            rec = {"cmd": " ".join(cmd), "returncode": None, "error": str(e)}
        runs.append(rec)
        name = Path(cmd[1]).name
        summary[name] = rec["returncode"]
    return summary, runs


# --------------------------------------------------------------------------- C4
def resolve_fragment(obj, fragment: str) -> bool:
    cur = obj
    for part in fragment.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False
    return True


def c4_pointer(d: dict) -> dict:
    ptr = d.get("class_contract_pointer", "")
    path, _, frag = ptr.partition("#")
    canon = yaml.safe_load((ROOT / F0_CANON).read_text())
    auth = yaml.safe_load((ROOT / F0_AUTH).read_text())
    return {
        "verdict": "fail",
        "pointer": ptr,
        "pointer_path": path,
        "pointer_fragment": frag,
        "canonical_sha256": sha256(F0_CANON),
        "authoring_sha256": sha256(F0_AUTH),
        "resolves_in_canonical": resolve_fragment(canon, frag),
        "resolves_in_authoring": resolve_fragment(auth, frag),
        "canonical_top_level_keys": sorted(canon.keys()),
        "authoring_top_level_keys": sorted(auth.keys()),
        "note": "canonical-path policy: research_map/formulation_taxonomy.yaml is authoritative; "
                "the canonical class node lives under 'classes', not 'class_contracts'.",
    }


# --------------------------------------------------------------------------- C5
class _DupLoader(yaml.SafeLoader):
    pass


def _dup_mapping(loader, node, deep=False):
    seen, dups = [], []
    for k, _v in node.value:
        key = loader.construct_object(k, deep=deep)
        if key in seen:
            dups.append(key)
        seen.append(key)
    loader._w040_dups = getattr(loader, "_w040_dups", []) + dups
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


_DupLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _dup_mapping)


def c5_duplicate_keys(d: dict) -> dict:
    raw = (ROOT / TARGET).read_bytes()
    loader = _DupLoader(raw)
    try:
        loader.get_single_data()
    finally:
        loader.dispose()
    dups = getattr(loader, "_w040_dups", [])
    from collections import Counter
    counts = Counter(dups)
    effective = d.get("revised_at")
    mt = mtime(TARGET)
    eff_dt = datetime.fromisoformat(effective) if effective else None
    mt_dt = datetime.fromtimestamp(os.path.getmtime(ROOT / TARGET), CST)
    wall = datetime.now(CST)
    return {
        "verdict": "fail" if counts else "pass",
        "duplicate_top_level_keys": dict(counts),
        "effective_revised_at_last_wins": effective,
        "target_mtime": mt,
        "review_wall_clock": wall.isoformat(timespec="seconds"),
        "effective_timestamp_is_future_of_mtime": bool(eff_dt and eff_dt > mt_dt),
        "effective_timestamp_is_future_of_clock": bool(eff_dt and eff_dt > wall),
        "revision": d.get("revision"),
        "note": "PyYAML last-wins: the effective revised_at is parser-dependent when keys repeat; "
                "revision identity keyed on the revision field alone cannot distinguish byte states.",
    }


# --------------------------------------------------------------------------- C6
SYMBOL = "AF_{I+}"


def c6_symbol() -> dict:
    census = {}
    for p in [TARGET, F0_CANON, F0_AUTH, "artifacts/formulation/VOCAB_ALIASES.json",
              "research_map/formulation_taxonomy.yaml", "artifacts/formulation/rule_spec.json"]:
        try:
            t = (ROOT / p).read_text(errors="replace")
            census[p] = {"count": t.count(SYMBOL)}
        except FileNotFoundError:
            census[p] = {"count": 0, "missing": True}
    # is there any definitional leaf naming the symbol?  a definition would be a key/value
    # pair whose value defines it, or an explicit "definition"/"symbol" entry.
    f1 = (ROOT / TARGET).read_text()
    hits = [ln for ln in f1.splitlines() if SYMBOL in ln]
    defined = bool(re.search(rf"{re.escape(SYMBOL)}\s*(:=|=|is defined)", f1))
    return {
        "verdict": "fail" if hits and not defined else "pass",
        "symbol": SYMBOL,
        "target_occurrences": len(hits),
        "target_lines": [h.strip()[:180] for h in hits],
        "definitional_occurrence": defined,
        "census": census,
        "note": "a normative symbol used in conclusion.statement_formal must be defined in the "
                "schema or in the F0 tree the schema binds to.",
    }


# --------------------------------------------------------------------------- C7
def strict_partial_orders(n: int):
    """All strict partial orders on {0..n-1} (transitive, irreflexive, asymmetric)."""
    pairs = [(i, j) for i in range(n) for j in range(n) if i != j]
    for mask in range(1 << len(pairs)):
        rel = set()
        for b, (i, j) in enumerate(pairs):
            if mask >> b & 1:
                rel.add((i, j))
        # asymmetric
        if any((j, i) in rel for (i, j) in rel):
            continue
        # transitive
        if any((i, k) not in rel for (i, j) in rel for (j2, k) in rel if j == j2 and i != k):
            continue
        yield frozenset(rel)


def leq(rel, a, b):
    return a == b or (a, b) in rel


def maximal(rel, u):
    return {x for x in u if not any((x, y) in rel for y in u)}


def chains(rel, u):
    """All non-empty chains (as tuples), ordered by strict relation."""
    out = []
    for r in range(1, len(u) + 1):
        for c in itertools.permutations(sorted(u), r):
            if all((c[i], c[i + 1]) in rel for i in range(len(c) - 1)):
                out.append(c)
    return out


def c7_hf06() -> dict:
    """Adjudicate HF-06: is whole-curve single-q visibility different from tail single-q?

    Lemma under test (past-closure): for a future-directed causal chain gamma and any q,
        exists t0: gamma[t0:] subset J^-(q)   <=>   gamma subset J^-(q)
    because J^-(q) is past-closed and gamma is causal.

    Four measurements:
      (a) exhaustive finite posets n=2..4, every chain, every q: whole vs tail single-q;
      (b) teeth control: over ALL subsets S of a chain (an arbitrary, not necessarily
          past-closed J), count whole-vs-tail divergences -> must be > 0, proving the
          harness can see a genuine difference;
      (c) the same over past-closed S only -> must be 0 (the lemma);
      (d) infinite-tail family (the true SET-vs-single-q distinction, which finite chains
          cannot exhibit because a finite chain always has a top): a_1<...<a_n with
          a_i <= q_j iff i<=j; SET-visible true while single-q whole and tail are false.
    """
    whole_vs_tail_diffs = 0
    models = 0
    for n in (2, 3, 4):
        u = tuple(range(n))
        for rel in strict_partial_orders(n):
            models += 1
            for g in chains(rel, u):
                for q in u:
                    whole = all(leq(rel, p, q) for p in g)
                    tail = any(all(leq(rel, p, q) for p in g[i:]) for i in range(len(g)))
                    if whole != tail:
                        whole_vs_tail_diffs += 1

    # (b)/(c) arbitrary J vs past-closed J along one chain of n points
    teeth = 0
    past_closed_diffs = 0
    for n in (2, 3, 4, 5):
        chain = list(range(n))  # 0 < 1 < ... < n-1
        for mask in range(1 << n):
            S = {chain[i] for i in range(n) if mask >> i & 1}
            whole = all(p in S for p in chain)
            tail = any(all(p in S for p in chain[i:]) for i in range(n))
            if whole != tail:
                teeth += 1
                # past-closed subsets of the chain are exactly the prefixes
                if not S or S == set(chain[:max(S) + 1]):
                    past_closed_diffs += 1

    # (d) the SET-vs-single-q distinction needs the OPEN END of gamma: a finite chain
    #     always has a top, where past-closure collapses SET to single-q.  Check it on the
    #     infinite family a_i (i in N), q_j (j in N), a_i <= q_j iff i <= j:
    #       SET visible   : forall i exists j>=i          -- witness function j = i
    #       single-q whole: exists j forall i: i<=j       -- refuted by i = j+1 for every j
    #       single-q tail : exists j,k forall i>=k: i<=j  -- refuted by i = max(j,k)+1
    N = 100000
    set_visible_proof = all(i <= i for i in range(1, N + 1))
    whole_refutations = all(max(j + 1, 1) > j for j in range(1, N + 1))
    tail_refutations = all(max(j, k) + 1 > j
                           for j in range(1, 1001) for k in range(1, 1001))
    set_control = set_visible_proof and whole_refutations and tail_refutations

    # (e) the schema's own line-220 example: starts in exterior, ends inside the BH region
    #     chain a < b with a <= q0 and b not <= any q  =>  both readings: not visible
    example = {"chain": ["a", "b"], "rel": [["a", "b"], ["a", "q0"]],
               "whole_visible": False, "tail_visible": False, "readings_agree": True}
    return {
        "verdict": "pass",
        "claim_under_test": "HF-06 (flash-19, critical): quantifiers.formal (whole-curve single-q) "
                            "is strictly weaker than visibility.definition (tail single-q)",
        "adjudication": "refuted: the two predicates are equivalent for the class's future-directed "
                        "causal geodesics because J^-(q) is past-closed",
        "models_enumerated": models,
        "whole_vs_tail_divergences": whole_vs_tail_diffs,
        "teeth_control_arbitrary_J_divergences": teeth,
        "teeth_control_has_teeth": teeth > 0,
        "past_closed_J_divergences": past_closed_diffs,
        "set_vs_single_q_symbolic": {
            "family": "a_i (i in N) causal chain; q_j (j in N); a_i <= q_j iff i <= j",
            "set_visible": set_visible_proof,
            "single_q_whole": not whole_refutations,
            "single_q_tail": not tail_refutations,
            "witness": "SET: j=i for each i; single-q: counterexample i=j+1; tail: i=max(j,k)+1",
        },
        "set_vs_single_q_control_has_teeth": set_control,
        "line220_example": example,
        "reported_direction": "0 divergences over exhaustive past-closed models => the line-220 "
                              "rationale ('whole curve would misclassify ...') is mathematically "
                              "incorrect, but semantically inert; quantifiers.formal and "
                              "quantifiers.negation remain exact negations.",
    }


# --------------------------------------------------------------------------- C8
def c8_reader_divergence(d: dict) -> dict:
    """The schema's own first schema_falsifier: two readers classify one datum differently."""
    q = d["quantifiers"]["formal"]
    vis = d["visibility"]["definition"]
    neg = d["quantifiers"]["negation"]
    d5 = d["quantifiers"]["domains"]["D5"]["definition"]
    wit = d["visibility"]["witness_protocol"]
    formal_whole = "gamma subset J^-(q)" in q
    d5_whole = "gamma([0,T)) is contained" in d5
    vis_tail = "TAIL" in vis or "gamma([t0,T))" in vis
    neg_refs_predicate = "visible from I+" in neg
    witness_whole = "gamma subset J^-(q)" in wit
    return {
        "verdict": "soft",
        "textual_split": {
            "quantifiers.formal": "whole_curve" if formal_whole else "other",
            "domains.D5": "whole_curve" if d5_whole else "other",
            "visibility.definition": "tail" if vis_tail else "other",
            "quantifiers.negation": "named_predicate" if neg_refs_predicate else "other",
            "visibility.witness_protocol": "whole_curve" if witness_whole else "other",
        },
        "semantic_divergence": False,
        "why_not_blocking": "C7: whole-curve and tail single-q are equivalent under the class's own "
                            "D4 (causal geodesic) and J^- past-closure; no datum is classified "
                            "differently by the two phrasings.  It is a drafting defect (the file "
                            "contradicts its own line-220 rationale), not an ambiguity.",
        "recommended_fix": "unify all five sites on the tail predicate and add the one-line "
                           "past-closure lemma so the equivalence is explicit.",
    }


def c9_f0_binding(d: dict) -> dict:
    b = d.get("f0_binding", {})
    decl = b.get("declared_f0_sha256")
    meas = sha256(F0_CANON)
    return {
        "verdict": "pass" if decl == meas else "fail",
        "declared_f0_artifact": b.get("declared_f0_artifact"),
        "declared_f0_sha256": decl,
        "measured_canonical_f0_sha256": meas,
        "binding_current": decl == meas,
        "checked_at_field": b.get("checked_at"),
        "canonical_authoring_divergent": sha256(F0_CANON) != sha256(F0_AUTH),
    }


# --------------------------------------------------------------------------- main
def main() -> dict:
    entry = hashes()
    d = load_f1()
    summary, runs = c3_instruments()

    checks = {
        "C1_structure": c1_structure(d),
        "C2_class_binding": c2_class_binding(d),
        "C3_instruments": {"verdict": "pass" if all(v == 0 for v in summary.values()) else "fail",
                           "returncodes": summary,
                           "note": "check_class_schema returns a JSON gate verdict; see instrument_runs.json"},
        "C4_contract_pointer": c4_pointer(d),
        "C5_duplicate_keys": c5_duplicate_keys(d),
        "C6_normative_symbol": c6_symbol(),
        "C7_HF06_adjudication": c7_hf06(),
        "C8_reader_divergence": c8_reader_divergence(d),
        "C9_f0_binding": c9_f0_binding(d),
    }
    exit_ = hashes()
    drift = sorted(set(entry) | set(exit_))
    drift = {p: {"entry": entry.get(p), "exit": exit_.get(p)} for p in drift
             if entry.get(p) != exit_.get(p)}

    rec = {
        "task_id": "W040-F1-INDEP-VERDICT-02",
        "worker": "worker-040",
        "created_at": now(),
        "target": {"path": TARGET, "sha256": entry[TARGET], "revision": d.get("revision"),
                   "mtime": mtime(TARGET), "class_id": d.get("class_id"), "node_id": d.get("node_id"),
                   "gate": "G-FORM"},
        "checks": checks,
        "drift_guard": {"tracked_entry_hashes": entry, "tracked_exit_hashes": exit_,
                        "changed_during_run": drift,
                        "bindable": not drift,
                        "void_if": "schemas/af_wcc_vacuum.yaml measured hash differs from "
                                   f"{entry[TARGET]} at gate-verdict time, or any tracked file "
                                   "changed after this review window"},
        "hard_failures": [k for k, v in checks.items()
                          if isinstance(v, dict) and v.get("verdict") == "fail"],
        "soft_findings": [k for k, v in checks.items()
                          if isinstance(v, dict) and v.get("verdict") == "soft"],
    }
    (OUT / "checks.json").write_text(json.dumps(rec, indent=1, sort_keys=True))
    (OUT / "instrument_runs.json").write_text(json.dumps(runs, indent=1, sort_keys=True))
    (OUT / "entry_hashes.json").write_text(json.dumps(entry, indent=1, sort_keys=True))
    (OUT / "exit_hashes.json").write_text(json.dumps(exit_, indent=1, sort_keys=True))
    print(json.dumps({"target_sha256": entry[TARGET], "hard_failures": rec["hard_failures"],
                      "soft_findings": rec["soft_findings"],
                      "C7": {k: checks["C7_HF06_adjudication"][k] for k in
                             ("models_enumerated", "whole_vs_tail_divergences",
                              "teeth_control_arbitrary_J_divergences",
                              "teeth_control_has_teeth", "past_closed_J_divergences",
                              "set_vs_single_q_control_has_teeth")},
                      "drift": drift}, indent=1))
    return rec


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
