#!/usr/bin/env python3
"""Worker-015 bounded class-bound probe: AF-WCC-VAC-GEN (F1) at canonical sha256 9a8bd4c9.

Question adjudicated: is the F1 `quantifiers.formal` clause
    "not exists q in I+ with gamma subset J^-(q) intersect M"
the negation of the class's own canonical visibility predicate
    visibility.definition = single-q TAIL predicate
(as worker-19 review F1-review-19 HF#1 states, critical), or are the two readings
equivalent (in which case the finding is falsified)?

Method: finite-model exhaustive refutation of the equivalence, plus hygiene checks
(duplicate YAML keys, future-dated timestamps, class-contract pointer resolution)
and a canonical-gate run on the pinned bytes and on a minimally repaired copy.

Writes probe_report.json next to this file. Read-only with respect to canonical paths.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
PIN_F1 = HERE / "pinned" / "af_wcc_vacuum.9a8bd4c9.yaml"
PIN_F2A = HERE / "pinned" / "af_scc_c2_vacuum.b6123750.yaml"
PIN_F2B = HERE / "pinned" / "af_scc_c0_vacuum.1bb78ce9.yaml"
PIN_F0 = HERE / "pinned" / "formulation_taxonomy.276009f4.yaml"
CANON_F0 = ROOT / "research_map" / "formulation_taxonomy.yaml"
AUTHOR_F0 = ROOT / "artifacts" / "formulation" / "formulation_taxonomy.yaml"
GATE = ROOT / "artifacts" / "formulation" / "tools" / "check_class_schema.py"

H_F1 = "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503"
H_F2A = "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2"
H_F2B = "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"
H_F0 = "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate mapping keys (YAML 1.2 forbids them)."""


def _no_duplicates(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                f"found duplicate key {key!r}", key_node.start_mark)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicates)


def top_level_key_occurrences(text: str) -> dict:
    """Count raw top-level 'key:' lines (column 0, scalar keys)."""
    counts: dict[str, int] = {}
    for line in text.splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):(?!:)", line)
        if m:
            counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    return {k: v for k, v in counts.items() if v > 1}


def line_of(text: str, needle: str) -> list[int]:
    return [i for i, ln in enumerate(text.splitlines(), 1) if needle in ln]


def extract_block(text: str, start_pat: str, end_pat: str | None = None) -> str:
    lines = text.splitlines()
    out, on = [], False
    for ln in lines:
        if re.match(start_pat, ln):
            on = True
        elif on and end_pat and re.match(end_pat, ln):
            break
        if on:
            out.append(ln)
    return "\n".join(out)


def resolve_dotted(doc: dict, path: str):
    cur = doc
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None, part
    return cur, None


def finite_model_check() -> dict:
    """Exhaustive check over finite causal models.

    Model: geodesic gamma = tuple of >=2 points; q-set Q; causal past J[q] subset of points.
    canonical visible(gamma,J,q) = exists t0 in [0,len): tail(gamma,t0) subset J[q]
    formal_fail(gamma,J)        = exists q: gamma subset J[q]          # negation of formal clause
    canonical_fail(gamma,J)     = forall q: not visible(gamma,J,q)     # negation of canonical predicate
    The review claim: canonical_fail and formal_fail are NOT equivalent; canonical_fail => formal_fail.
    """
    pts = (0, 1, 2)
    gammas = [g for n in (2, 3) for g in itertools.permutations(pts, n)]
    past_choices = [frozenset(s) for s in itertools.chain.from_iterable(
        itertools.combinations(pts, k) for k in range(len(pts) + 1))]
    # 1 or 2 points of I+ (Q), each with an arbitrary causal past
    qsets = [(j,) for j in past_choices] + list(itertools.combinations_with_replacement(past_choices, 2))
    countermodel_a = countermodel_b = None
    impl_a = True   # canonical_fail -> formal_fail  (class conclusion implies the formal clause)
    impl_b = True   # formal_fail -> canonical_fail  (formal clause is strong enough)
    for gamma in gammas:
        whole = set(gamma)
        for Q in qsets:
            visible = any(any(set(gamma[t0:]) <= set(Jq) for t0 in range(len(gamma)))
                          for Jq in Q)
            canon_fail = not visible
            formal_fail = all(not (whole <= set(Jq)) for Jq in Q)
            model = {"gamma": list(gamma), "J_minus_Q": [sorted(j) for j in Q]}
            if canon_fail and not formal_fail:
                impl_a = False
                if countermodel_a is None:
                    countermodel_a = model
            if formal_fail and not canon_fail:
                impl_b = False
                if countermodel_b is None:
                    t0 = next(t for t in range(len(gamma))
                              for Jq in Q if set(gamma[t:]) <= set(Jq))
                    countermodel_b = {**model, "tail_t0": t0,
                                      "canonical_predicate_true": True,
                                      "formal_clause_true": True}
    return {
        "universe_points": list(pts),
        "geodesic_models": len(gammas),
        "I_plus_pasts_per_model": len(qsets),
        "models_enumerated": len(gammas) * len(qsets),
        "implication_canonical_fail_implies_formal_fail": impl_a,
        "implication_formal_fail_implies_canonical_fail": impl_b,
        "equivalent": impl_a and impl_b,
        "witness_formal_fail_but_canonical_predicate_true": countermodel_b,
        "witness_canonical_fail_but_formal_true": countermodel_a,
    }


def main() -> int:
    now = datetime.now(CST)
    text = PIN_F1.read_text()
    doc = yaml.safe_load(text)
    try:
        yaml.load(text, Loader=StrictLoader)
        strict = "accepted"
    except yaml.constructor.ConstructorError as e:
        strict = f"rejected: {e.problem}"

    eff = doc.get("revised_at")
    checked = (doc.get("f0_binding") or {}).get("checked_at")

    # --- pointer resolution -------------------------------------------------
    ccp = doc.get("class_contract_pointer")
    f0b = doc.get("f0_binding") or {}
    declared_f0 = f0b.get("declared_f0_artifact")
    declared_sha = f0b.get("declared_f0_sha256")
    supp = f0b.get("class_contract_supplement")
    canon_doc = yaml.safe_load(CANON_F0.read_text())
    author_doc = yaml.safe_load(AUTHOR_F0.read_text()) if AUTHOR_F0.exists() else {}
    ptr_path = (ccp or "").split("#")[0]
    ptr_frag = (ccp or "").split("#")[1] if "#" in (ccp or "") else ""
    canon_val, canon_missing = resolve_dotted(canon_doc, ptr_frag) if ptr_frag else (None, "no fragment")
    author_val, author_missing = resolve_dotted(author_doc, ptr_frag) if ptr_frag else (None, "no fragment")
    supp_path = (supp or "").split("#")[0]
    supp_frag = (supp or "").split("#")[1] if "#" in (supp or "") else ""
    supp_val, supp_missing = resolve_dotted(canon_doc, supp_frag) if supp_frag else (None, "no fragment")

    # --- quantifier text ----------------------------------------------------
    qformal = doc["quantifiers"]["formal"]
    d5 = doc["quantifiers"]["domains"]["D5"]["definition"]
    vis_def = doc["visibility"]["definition"]
    vis_neg = doc["visibility"]["negation_conclusion"]
    stmt = doc["conclusion"]["statement_formal"]
    tail_re = re.compile(r"tail", re.I)
    whole_formal = bool(re.search(r"gamma\s+subset\s+J\^?-?\(?q", qformal))
    whole_d5 = bool(re.search(r"gamma\(\[0,T\)\)\s+is contained", d5))
    tail_vis = bool(tail_re.search(vis_def)) and "gamma([t0,T))" in vis_def
    tail_neg = "gamma([t0,T)) is NOT contained" in vis_neg or "tail gamma([t0,T))" in vis_neg

    # --- canonical gate on pinned + repaired copy ---------------------------
    gate_pin = subprocess.run([sys.executable, str(GATE), str(PIN_F1)],
                              capture_output=True, text=True)
    repaired = text
    repaired = repaired.replace(
        "not exists q in I+ with gamma subset J^-(q) intersect M.",
        "not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M.")
    repaired = repaired.replace(
        '"points q of I+ such that gamma([0,T)) is contained in the causal past J^-(q) intersected with M"',
        '"pairs (q,t0) with q in I+ and t0 in [0,T) such that the tail gamma([t0,T)) is contained in the causal past J^-(q) intersected with M"')
    repaired = repaired.replace(
        '- {kind: not_exists, binder: "q", domain_id: D5}',
        '- {kind: not_exists, binder: "(q,t0)", domain_id: D5}')
    rep_path = HERE / "repaired_proposal.af_wcc_vacuum.yaml"
    rep_path.write_text(repaired)
    gate_rep = subprocess.run([sys.executable, str(GATE), str(rep_path)],
                              capture_output=True, text=True)
    patch_applied = {
        "formal_clause_changed": "gamma([t0,T)) subset J^-(q)" in repaired and
                                 "gamma subset J^-(q) intersect M" not in repaired,
        "d5_changed": "tail gamma([t0,T)) is contained" in repaired,
        "ordered_binder_changed": 'binder: "(q,t0)", domain_id: D5' in repaired,
    }

    report = {
        "probe_id": "w015-f1-visibility-adjudication-20260912T0027+0800",
        "actor": "deepseek-flash-15",
        "class_id": "AF-WCC-VAC-GEN",
        "node_id": "F1",
        "gate": "G-FORM",
        "created_at": now.isoformat(),
        "wall_clock": now.isoformat(),
        "pinned_inputs": {
            "schemas/af_wcc_vacuum.yaml": {"pinned": sha256(PIN_F1), "declared_final": H_F1,
                                           "match": sha256(PIN_F1) == H_F1},
            "schemas/af_scc_c2_vacuum.yaml": {"pinned": sha256(PIN_F2A), "declared_final": H_F2A,
                                              "match": sha256(PIN_F2A) == H_F2A},
            "schemas/af_scc_c0_vacuum.yaml": {"pinned": sha256(PIN_F2B), "declared_final": H_F2B,
                                              "match": sha256(PIN_F2B) == H_F2B},
            "research_map/formulation_taxonomy.yaml": {"pinned": sha256(PIN_F0), "declared_final": H_F0,
                                                       "match": sha256(PIN_F0) == H_F0},
        },
        "line_refs": {
            "quantifiers.formal": line_of(text, "formal: >-")[0],
            "quantifiers.formal_clause": [n for n in line_of(text, "not exists q in I+")],
            "D5": line_of(text, "D5:")[0],
            "visibility.definition": line_of(text, "  definition: \"a future-inextendible causal geodesic"),
            "visibility.negation_conclusion": line_of(text, "negation_conclusion:"),
            "conclusion.statement_formal": line_of(text, "statement_formal:"),
            "class_contract_pointer": line_of(text, "class_contract_pointer:"),
            "f0_binding": line_of(text, "f0_binding:"),
        },
        "quantifier_coherence": {
            "quantifiers_formal_clause": "not exists q in I+ with gamma subset J^-(q) intersect M",
            "quantifiers_formal_uses_whole_curve": whole_formal,
            "D5_definition": d5,
            "D5_uses_whole_curve": whole_d5,
            "visibility_definition_is_tail": tail_vis,
            "visibility_negation_is_tail": tail_neg,
            "conclusion_statement_formal": stmt,
            "conclusion_uses_predicate": "visible_singularity_from_I_plus" in stmt,
            "artifact_internally_incoherent": whole_formal and whole_d5 and tail_vis and tail_neg,
        },
        "finite_model_check": finite_model_check(),
        "hygiene": {
            "duplicate_top_level_keys": top_level_key_occurrences(text),
            "strict_yaml_loader": strict,
            "pyyaml_effective_revised_at": eff,
            "effective_revised_at_is_future": bool(eff and str(eff) > now.isoformat()),
            "f0_binding_checked_at": checked,
            "checked_at_is_future": bool(checked and str(checked) > now.isoformat()),
            "declared_revision": doc.get("revision"),
        },
        "f0_pointer": {
            "class_contract_pointer": ccp,
            "pointer_path": ptr_path,
            "pointer_fragment": ptr_frag,
            "resolves_in_declared_canonical_f0": canon_val is not None,
            "canonical_missing_segment": canon_missing,
            "resolves_in_authoring_tree": author_val is not None,
            "authoring_missing_segment": author_missing,
            "declared_f0_artifact": declared_f0,
            "declared_f0_sha256": declared_sha,
            "declared_f0_matches_measured": declared_sha == H_F0,
            "class_contract_supplement": supp,
            "supplement_resolves_in_canonical_f0": supp_val is not None,
            "supplement_missing_segment": supp_missing,
        },
        "canonical_gate": {
            "pinned_bytes": {"rc": gate_pin.returncode, "stdout": gate_pin.stdout.strip()},
            "repaired_proposal": {"rc": gate_rep.returncode, "stdout": gate_rep.stdout.strip(),
                                  "patch_applied": patch_applied,
                                  "path": str(rep_path.relative_to(ROOT)),
                                  "sha256": sha256(rep_path)},
        },
        "verdict_inputs": {
            "F1_review_19_HF1_confirmed": whole_formal and tail_vis and not
                finite_model_check()["equivalent"],
            "gate_blind_to_defect": gate_pin.returncode == 0 and whole_formal,
        },
    }
    out = HERE / "probe_report.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False))
    print(json.dumps({k: report[k] for k in
                      ("quantifier_coherence", "finite_model_check", "hygiene",
                       "f0_pointer", "canonical_gate", "verdict_inputs")},
                     indent=1, ensure_ascii=False))
    print(f"\nreport: {out} sha256={sha256(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
