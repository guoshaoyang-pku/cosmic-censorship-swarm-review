#!/usr/bin/env python3
"""W098-F2A-INDEP-VERDICT-01: independent full-schema verification of F2a.

Target : canonical class schema AF-SCC-C2-VAC-GEN (node F2a)
Method : hash-pinned snapshot; three independent stages:
         S1 canonical structural gate (author's tool)
         S2 class-separation detector (worker-07-corpus-calibrated, separate author)
         S3 reviewer's own field-by-field contract + cross-field consistency checks
         S4 mutation controls measure the union detection power of S1+S2+S3.
         S5 drift re-measure of the canonical path.

This script claims NO node completion, NO theorem, NO gate verdict. It emits a
review record with a verdict for the controller/lead to weigh.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
HERE = ROOT / "artifacts/worker-098/f2a_independent_review"
SNAP = HERE / "af_scc_c2_vacuum.snapshot.yaml"
CANONICAL = ROOT / "schemas/af_scc_c2_vacuum.yaml"
TAXO = HERE / "formulation_taxonomy.snapshot.yaml"
SPEC = HERE / "rule_spec.snapshot.json"
GATE = ROOT / "artifacts/formulation/tools/check_class_schema.py"
CLASS_ID = "AF-SCC-C2-VAC-GEN"
NODE_ID = "F2a"
SIBLING = "AF-SCC-C0-VAC-GEN"

sys.path.insert(0, str(ROOT / "research_map"))
import class_separation as cs  # noqa: E402

import yaml  # noqa: E402


CST = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(CST).replace(microsecond=0).isoformat()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def get(d, *path, default=None):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def run_gate(schema: Path) -> dict:
    r = subprocess.run(
        [sys.executable, str(GATE), "--json", str(schema)],
        capture_output=True, text=True,
    )
    try:
        rep = json.loads(r.stdout)
    except Exception:
        rep = {"verdict": "UNPARSEABLE", "stdout": r.stdout[:4000]}
    rep["_exit_code"] = r.returncode
    rep["_stderr_tail"] = r.stderr[-500:]
    return rep


def find_key(obj, key):
    """Recursively collect values for key anywhere in a nested structure."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                out.append(v)
            out.extend(find_key(v, key))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(find_key(v, key))
    return out


def contract_violations(schema: dict, contracts: dict, spec: dict) -> list:
    """Reviewer's independent contract + cross-field consistency checks.

    Returns a list of {check, ok, detail}; `ok=False` is a candidate artifact
    defect (each one must be manually re-read before it is called a defect).
    """
    checks = []

    def chk(name, ok, detail):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    comp = schema.get("class_components", {})
    concl = schema.get("conclusion", {}) or {}
    ctype = concl.get("conclusion_type")
    pred = schema.get("extension_predicate", {}) or {}
    reg = schema.get("regularity", {}) or {}
    gen = schema.get("genericity", {}) or {}
    cb = schema.get("class_boundary", {}) or {}
    vocab = spec["vocabularies"]["class_conclusion_type"]

    chk("class_id_matches_target", schema.get("class_id") == CLASS_ID,
        f"declared={schema.get('class_id')!r}")
    chk("node_id_matches_target", schema.get("node_id") == NODE_ID,
        f"declared={schema.get('node_id')!r}")
    chk("components_match_taxonomy", comp == contracts.get("components"),
        f"schema={comp} taxonomy={contracts.get('components')}")
    chk("family_is_scc", spec["class_family"].get(CLASS_ID) == "SCC"
        and comp.get("censorship") == "SCC" and concl.get("family") == "SCC",
        "family=SCC in spec, components and conclusion")
    chk("conclusion_type_matches_taxonomy_and_vocab",
        ctype == contracts.get("conclusion_type") == vocab.get(CLASS_ID)
        == "scc_c2_future_inextendibility",
        f"schema={ctype!r} taxonomy={contracts.get('conclusion_type')!r} "
        f"vocab[class]={vocab.get(CLASS_ID)!r}")
    chk("extension_predicate_frozen_fields",
        pred.get("frozen_regularity") == "C2"
        and pred.get("frozen_equation_concept") == "classical_ricci"
        and pred.get("frozen_direction") == "future",
        f"pred={ {k: pred.get(k) for k in ('frozen_regularity','frozen_equation_concept','frozen_direction')} }")
    chk("extension_regularity_exactly_c2", reg.get("extension_regularity") == "C2",
        f"extension_regularity={reg.get('extension_regularity')!r}")
    chk("extension_concept_classical_ricci",
        reg.get("extension_solution_concept") == "classical_ricci",
        f"extension_solution_concept={reg.get('extension_solution_concept')!r}")
    # cross-field: every place that declares the regularity token must say C2
    exact = reg.get("extension_regularity_exact", "") or ""
    _cm = re.search(r"c([0-9])", ctype or "", re.I)
    ctoken = ("C" + _cm.group(1)) if _cm else None
    token_places = {
        "class_components.regularity_token": comp.get("regularity_token"),
        "extension_predicate.frozen_regularity": pred.get("frozen_regularity"),
        "regularity.extension_regularity": reg.get("extension_regularity"),
        "conclusion_type_regularity_token": ctoken,
    }
    token_values = {k: (v.upper() if isinstance(v, str) else v)
                    for k, v in token_places.items()}
    token_ok = (set(token_values.values()) == {"C2"})
    chk("regularity_token_consistent_across_fields", token_ok,
        json.dumps(token_values))
    chk("regularity_exact_prose_asserts_c2_not_c0",
        bool(re.search(r"exactly\s+C2\b", exact))
        and not re.search(r"exactly\s+C0\b", exact)
        and not re.search(r"exactly\s+C1\b", exact),
        f"head={exact[:90]!r}")
    chk("genericity_residual_comeager",
        gen.get("kind") == "residual_comeager"
        and gen.get("kind") in spec["vocabularies"]["genericity_kind"],
        f"kind={gen.get('kind')!r}")
    chk("genericity_part_of_class", gen.get("is_part_of_class") is True,
        f"is_part_of_class={gen.get('is_part_of_class')!r}")
    chk("one_class_only_no_merge",
        cb.get("one_class_only") == CLASS_ID and cb.get("merge_forbidden") is True,
        f"one_class_only={cb.get('one_class_only')!r} merge_forbidden={cb.get('merge_forbidden')!r}")
    chk("sibling_disjoint_declared", schema.get("sibling_disjoint_from") == SIBLING,
        f"sibling_disjoint_from={schema.get('sibling_disjoint_from')!r}")
    chk("i_plus_topology_RxS2",
        get(schema, "topology", "I_plus_topology") == "R x S^2"
        and get(schema, "data_class", "cosmological_constant") == 0,
        f"I_plus_topology={get(schema,'topology','I_plus_topology')!r}")
    q = schema.get("quantifiers", {}) or {}
    chk("quantifiers_exact_ordered_negated",
        bool(q.get("formal")) and bool(q.get("ordered")) and bool(q.get("negation"))
        and bool(q.get("negation_normal_form")) and q.get("order_matters") is True,
        f"ordered={len(q.get('ordered') or [])} order_matters={q.get('order_matters')!r}")
    nv = schema.get("non_vacuity", {}) or {}
    chk("non_vacuity_witness_declared",
        bool(nv.get("condition")) and bool(nv.get("witness_type"))
        and bool(nv.get("vacuity_falsifier")),
        f"non_vacuity keys={list(nv.keys())}")
    vis = schema.get("visibility", {}) or {}
    ip = schema.get("i_plus", {}) or {}
    chk("visibility_excluded_from_conclusion_and_falsifier",
        vis.get("role") == "not_in_conclusion"
        and vis.get("visible_singularity_is_wcc") is True
        and bool(vis.get("forbidden_falsifier"))
        and ip.get("in_conclusion") is False
        and ip.get("completeness_in_conclusion") is False,
        f"visibility.role={vis.get('role')!r} i_plus.in_conclusion={ip.get('in_conclusion')!r}")
    sf = find_key(schema.get("falsifier", {}), "schema_falsifiers")
    sf_flat = [x for v in sf for x in (v if isinstance(v, list) else [v])]
    chk("class_falsifiers_present",
        len(sf_flat) >= 3
        and get(schema, "falsifier", "tier_1", "refutes") == CLASS_ID,
        f"schema_falsifiers={len(sf_flat)} tier_1.refutes={get(schema,'falsifier','tier_1','refutes')!r}")
    # asserted surfaces only: foreign-family content here is leakage
    asserted = json.dumps([concl.get("statement_natural_language"),
                           concl.get("statement_formal"),
                           concl.get("conclusion_type"),
                           comp, pred.get("frozen_regularity"),
                           reg.get("extension_regularity")])
    chk("no_c0_or_c1_token_in_asserted_surfaces",
        not re.search(r"\bC0\b|\bC1\b|C\^?\{?1,1", asserted),
        "asserted surfaces scanned for C0/C1 tokens")
    chk("no_wcc_conclusion_tokens_in_asserted_surfaces",
        not cs.WCC_CONCLUSION.search(json.dumps(
            [concl.get("statement_natural_language"), concl.get("statement_formal"),
             concl.get("conclusion_type")])),
        "WCC regex over asserted conclusion surfaces only")
    anti = json.dumps(cb.get("anti_scope") or schema.get("anti_scope") or {})
    chk("anti_scope_names_c0_sibling_and_wcc",
        SIBLING in anti and "AF-WCC-VAC-GEN" in anti,
        "anti_scope names the C0 sibling and the WCC class")
    return checks


def mutants(text: str) -> dict:
    """Deliberate defectors built from the real snapshot. Each must be caught by at
    least one stage, else the 'pass' verdict is uninformative for that defect class."""
    out = {}
    m1 = text.replace("extension_regularity: C2\n",
                      "extension_regularity: C0 or C2\n", 1)
    if m1 != text:
        out["M1_composite_c0_or_c2_regularity"] = m1
    m2 = text.replace("conclusion_type: scc_c2_future_inextendibility",
                      "conclusion_type: wcc_visible_singularity", 1)
    if m2 != text:
        out["M2_wcc_conclusion_inflation"] = m2
    m3 = text.replace('extension_regularity_exact: "the class token is exactly C2',
                      'extension_regularity_exact: "the class token is exactly C0', 1)
    if m3 != text:
        out["M3_regularity_exact_prose_weakened_to_c0"] = m3
    m4 = text.replace("kind: residual_comeager\n", "kind: full_measure\n", 1)
    if m4 != text:
        out["M4_genericity_kind_changed"] = m4
    m5 = text.replace("merge_forbidden: true", "merge_forbidden: false", 1)
    if m5 != text:
        out["M5_merge_permission_flipped"] = m5
    return out


def main() -> int:
    snap_hash = sha256_file(SNAP)
    canonical_hash_at_start = sha256_file(CANONICAL)
    text = SNAP.read_text()
    schema = yaml.safe_load(text)
    taxo = yaml.safe_load(TAXO.read_text())
    spec = json.loads(SPEC.read_text())
    contracts = taxo["class_contracts"][CLASS_ID]

    gate = run_gate(SNAP)
    cs_findings = cs.findings_for_text(text, SNAP.name)
    checks = contract_violations(schema, contracts, spec)
    failed = [c for c in checks if not c["ok"]]
    cs_hard = [f for f in cs_findings if not str(f).startswith("CLASSSEP-SOFT")]

    controls = []
    for name, mtext in mutants(text).items():
        mp = HERE / f"control_{name}.yaml"
        mp.write_text(mtext)
        mrep = run_gate(mp)
        mfind = cs.findings_for_text(mtext, f"control:{name}")
        mschema = yaml.safe_load(mtext)
        mchecks = contract_violations(mschema, contracts, spec)
        mfailed = [c["check"] for c in mchecks if not c["ok"]]
        detected = (mrep.get("verdict") != "pass") or bool(mfind) or bool(mfailed)
        controls.append({
            "control": name,
            "control_sha256": hashlib.sha256(mtext.encode()).hexdigest(),
            "gate_verdict": mrep.get("verdict"),
            "gate_failed_rules": mrep.get("failed_rules"),
            "classsep_findings": mfind,
            "reviewer_check_failures": mfailed,
            "detected_by": [s for s, hit in
                            (("gate", mrep.get("verdict") != "pass"),
                             ("classsep", bool(mfind)),
                             ("reviewer_checks", bool(mfailed))) if hit],
            "detected": detected,
        })
    undetected = [c["control"] for c in controls if not c["detected"]]
    detection_rate = (sum(c["detected"] for c in controls) / len(controls)) if controls else None

    canonical_hash_at_end = sha256_file(CANONICAL)
    drift = canonical_hash_at_end != canonical_hash_at_start

    hard_failures = []
    if gate.get("verdict") != "pass":
        hard_failures.append(f"canonical gate verdict={gate.get('verdict')} "
                             f"rules={gate.get('failed_rules')}")
    hard_failures.extend(f"contract:{c['check']} :: {c['detail']}" for c in failed)
    hard_failures.extend(f"classsep:{f}" for f in cs_hard)
    if drift:
        hard_failures.append(
            f"moving target: canonical hash changed during review "
            f"{canonical_hash_at_start[:12]} -> {canonical_hash_at_end[:12]}")

    if drift:
        verdict, score = "inconclusive", 2.0
    elif hard_failures:
        verdict, score = "revise", 3.0
    else:
        verdict, score = "accept", 4.5
    if undetected and verdict == "accept":
        # a blind spot means absence-of-findings is weaker evidence, not that the
        # artifact is defective; record it explicitly and cap the score.
        score = 4.0

    evidence = {
        "task_id": "W098-F2A-INDEP-VERDICT-01",
        "reviewer": "worker-098",
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "reviewed_sha256": snap_hash,
        "canonical_path": "schemas/af_scc_c2_vacuum.yaml",
        "canonical_hash_at_start": canonical_hash_at_start,
        "canonical_hash_at_end": canonical_hash_at_end,
        "drift_during_review": drift,
        "snapshot_path": str(SNAP.relative_to(ROOT)),
        "support_hashes": {
            "formulation_taxonomy.yaml": sha256_file(TAXO),
            "rule_spec.json": sha256_file(SPEC),
        },
        "stage_1_canonical_gate": {
            "tool": "artifacts/formulation/tools/check_class_schema.py",
            "tool_sha256": sha256_file(GATE),
            "verdict": gate.get("verdict"),
            "failed_rules": gate.get("failed_rules"),
            "exit_code": gate.get("_exit_code"),
            "documented_blind_spots": get(gate, "blind_spots", default=None),
        },
        "stage_2_class_separation": {
            "tool": "research_map/class_separation.py",
            "tool_sha256": sha256_file(ROOT / "research_map/class_separation.py"),
            "findings": cs_findings,
            "hard_findings": cs_hard,
        },
        "stage_3_contract_checks": checks,
        "stage_3_failed": [c["check"] for c in failed],
        "stage_4_controls": controls,
        "stage_4_detection_rate": detection_rate,
        "stage_4_undetected": undetected,
        "stage_5_drift": {"start": canonical_hash_at_start,
                          "end": canonical_hash_at_end, "drift": drift},
        "verdict": verdict,
        "score": score,
        "hard_failures": hard_failures,
        "documented_method_blind_spots": undetected + [
            "semantic prose leak in non-asserted clean-day fields (gate's own documented blind spot)",
            "mathematical correctness of definitions (both stages structural only)",
            "citation scope/truth of l1_ledger_refs (not verified here)",
        ],
        "scope_limit": (
            "Structural + contract conformance of one snapshot at the pinned hash only. "
            "Not a physics verdict, not a gate verdict, not an endorsement of cited theorems."),
        "next_falsifier": (
            "A class-merge / conclusion-inflation / regularity-weakening / vacuity defect in "
            f"{CLASS_ID} at {snap_hash[:12]} that survives BOTH the canonical gate and the "
            "class-separation detector and these contract checks, or measured drift of the "
            "canonical file away from this hash."),
        "generated_at": now_iso(),
    }
    (HERE / "f2a_independent_evidence.json").write_text(json.dumps(evidence, indent=1) + "\n")

    review = {
        "event_id": "w098-f2a-review-" + now_iso(),
        "event_type": "review",
        "created_at": now_iso(),
        "actor": "worker-098",
        "target_id": "F2a",
        "class_id": CLASS_ID,
        "reviewer": "worker-098",
        "verdict": verdict,
        "score": score,
        "reviewed_sha256": snap_hash,
        "hard_failures": hard_failures,
        "findings": [
            f"canonical gate: {gate.get('verdict')} ({len(gate.get('failed_rules') or [])} failed rules)",
            f"class-separation detector: {len(cs_hard)} hard finding(s)",
            f"contract + cross-field checks: {len(checks) - len(failed)}/{len(checks)} ok",
            f"mutation controls detected (union of 3 stages): "
            f"{sum(c['detected'] for c in controls)}/{len(controls)}",
            f"drift during review: {drift}",
        ],
        "evidence_refs": [
            "artifacts/worker-098/f2a_independent_review/f2a_independent_evidence.json",
            f"schemas/af_scc_c2_vacuum.yaml#{snap_hash[:12]}",
            f"artifacts/formulation/formulation_taxonomy.yaml#{sha256_file(TAXO)[:12]}",
            f"artifacts/formulation/rule_spec.json#{sha256_file(SPEC)[:12]}",
        ],
        "artifact_refs": [
            "artifacts/worker-098/f2a_independent_review/f2a_independent_evidence.json",
        ],
        "next_falsifier": evidence["next_falsifier"],
        "scope_limit": evidence["scope_limit"],
    }
    (HERE / "f2a_independent_verdict.json").write_text(json.dumps(review, indent=1) + "\n")

    print(json.dumps({
        "verdict": verdict, "score": score, "hard_failures": hard_failures,
        "gate": gate.get("verdict"), "classsep_hard": cs_hard,
        "contract_ok": f"{len(checks) - len(failed)}/{len(checks)}",
        "controls_detected": f"{sum(c['detected'] for c in controls)}/{len(controls)}",
        "undetected": undetected, "drift": drift, "snapshot_sha256": snap_hash,
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
