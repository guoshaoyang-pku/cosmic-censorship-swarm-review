#!/usr/bin/env python3
"""W098-F2A-INDEP-VERDICT-01 pass 2: re-review at the live canonical hash.

Pass 1 bound 4f97273ef440; F2a was republished to b6123750b37d before emission
(rev11: comment + revision bump + f0_binding refresh; no class-semantics change).
This pass re-measures, re-runs all three stages plus controls, and adds:
  * F0-binding check: declared_f0_sha256 == measured canonical taxonomy hash
  * alias-aware canonical cross-check (canonical taxonomy classes vs F2a schema)
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
HERE = ROOT / "artifacts/worker-098/f2a_independent_review"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "research_map"))

import verify_f2a as V  # noqa: E402
import class_separation as cs  # noqa: E402
import yaml  # noqa: E402

SNAP = HERE / "af_scc_c2_vacuum.snapshot.v2.yaml"
CANON_F2A = ROOT / "schemas/af_scc_c2_vacuum.yaml"
CANON_TAXO = ROOT / "research_map/formulation_taxonomy.yaml"
SUPP_TAXO = V.TAXO  # artifacts/formulation/formulation_taxonomy.yaml snapshot
ALIASES = json.loads((ROOT / "artifacts/formulation/VOCAB_ALIASES.json").read_text())
CLASS_ID, NODE_ID = V.CLASS_ID, V.NODE_ID


def canon(kind: str, tok: str) -> str:
    for c, al in ALIASES[kind].items():
        if tok == c or tok in al:
            return c
    return tok


def main() -> int:
    snap_hash = V.sha256_file(SNAP)
    canon_f2a_start = V.sha256_file(CANON_F2A)
    canon_taxo_start = V.sha256_file(CANON_TAXO)
    text = SNAP.read_text()
    schema = yaml.safe_load(text)
    supp = yaml.safe_load(SUPP_TAXO.read_text())
    can = yaml.safe_load(CANON_TAXO.read_text())
    spec = json.loads(V.SPEC.read_text())
    contracts = supp["class_contracts"][CLASS_ID]

    # --- S1/S2/S3 on the live snapshot ---
    gate = V.run_gate(SNAP)
    cs_findings = cs.findings_for_text(text, SNAP.name)
    checks = V.contract_violations(schema, contracts, spec)

    def chk(name, ok, detail):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    # --- canonical-path cross-checks (new in pass 2) ---
    binding = schema.get("f0_binding", {}) or {}
    declared = binding.get("declared_f0_sha256")
    chk("f0_binding_declared_hash_matches_canonical_taxonomy",
        declared == canon_taxo_start,
        f"declared={str(declared)[:16]} measured={canon_taxo_start[:16]} "
        f"path={binding.get('declared_f0_artifact')!r}")
    c = can["classes"][CLASS_ID]
    ax = c["axes"]
    comp = schema["class_components"]
    chk("canonical_axes_match_f2a_components_alias_aware",
        canon("conclusion_type", ax["conclusion_type"]) == canon(
            "conclusion_type", schema["conclusion"]["conclusion_type"])
        and canon("genericity_kind", ax["genericity_kind"]) == canon(
            "genericity_kind", schema["genericity"]["kind"])
        and ax["regularity_token"] == comp["regularity_token"]
        and ax["family"] == comp["censorship"],
        f"canonical(concl={ax['conclusion_type']!r}, gen={ax['genericity_kind']!r}, "
        f"reg={ax['regularity_token']!r}) vs schema("
        f"{schema['conclusion']['conclusion_type']!r}, "
        f"{schema['genericity']['kind']!r}, {comp['regularity_token']!r})")
    chk("canonical_conclusion_c0_inflation_forbidden",
        "C0" in json.dumps(c.get("conclusion", {}).get("forbidden_inflation", ""))
        and "weak cosmic censorship" in json.dumps(
            c.get("conclusion", {}).get("forbidden_inflation", "")).lower(),
        f"forbidden_inflation={str(c.get('conclusion', {}).get('forbidden_inflation'))[:120]!r}")
    pub_divergent = V.sha256_file(SUPP_TAXO) != canon_taxo_start
    chk("publication_pair_f0_byte_identical",
        not pub_divergent,
        f"canonical={canon_taxo_start[:12]} supplement={V.sha256_file(SUPP_TAXO)[:12]} "
        f"(divergence is an F0 publication finding, already flagged by controller_gate_audit)")
    chk("class_contract_pointer_targets_supplement",
        str(schema.get("class_contract_pointer", "")).startswith(
            "artifacts/formulation/formulation_taxonomy.yaml#"),
        f"pointer={schema.get('class_contract_pointer')!r}")

    failed = [x for x in checks if not x["ok"]]
    # publication divergence is a scope limit on the binding, not a defect in F2a
    F0_PUBLICATION_CHECKS = {"publication_pair_f0_byte_identical"}
    hard = [x for x in failed if x["check"] not in F0_PUBLICATION_CHECKS]
    scope_notes = [x for x in failed if x["check"] in F0_PUBLICATION_CHECKS]
    cs_hard = [f for f in cs_findings if not str(f).startswith("CLASSSEP-SOFT")]

    # --- S4 controls on the live text ---
    controls = []
    for name, mtext in V.mutants(text).items():
        mp = HERE / f"p2_control_{name}.yaml"
        mp.write_text(mtext)
        mrep = V.run_gate(mp)
        mfind = cs.findings_for_text(mtext, f"p2control:{name}")
        mfail = [x["check"] for x in V.contract_violations(
            yaml.safe_load(mtext), contracts, spec) if not x["ok"]]
        controls.append({
            "control": name,
            "control_sha256": hashlib.sha256(mtext.encode()).hexdigest(),
            "gate_verdict": mrep.get("verdict"),
            "gate_failed_rules": mrep.get("failed_rules"),
            "classsep_findings": mfind,
            "reviewer_check_failures": mfail,
            "detected_by": [s for s, hit in
                            (("gate", mrep.get("verdict") != "pass"),
                             ("classsep", bool(mfind)),
                             ("reviewer_checks", bool(mfail))) if hit],
            "detected": (mrep.get("verdict") != "pass") or bool(mfind) or bool(mfail),
        })
    undetected = [x["control"] for x in controls if not x["detected"]]
    detection_rate = (sum(x["detected"] for x in controls) / len(controls)) if controls else None

    # --- S5 drift re-measure (both F2a and the declared F0) ---
    canon_f2a_end = V.sha256_file(CANON_F2A)
    canon_taxo_end = V.sha256_file(CANON_TAXO)
    drift = (canon_f2a_end != canon_f2a_start) or (canon_taxo_end != canon_taxo_start)

    hard_failures = []
    if gate.get("verdict") != "pass":
        hard_failures.append(f"canonical gate verdict={gate.get('verdict')} "
                             f"rules={gate.get('failed_rules')}")
    hard_failures.extend(f"contract:{x['check']} :: {x['detail']}" for x in hard)
    hard_failures.extend(f"classsep:{f}" for f in cs_hard)
    if drift:
        hard_failures.append(
            f"moving target during pass 2: F2a {canon_f2a_start[:12]}->{canon_f2a_end[:12]}, "
            f"F0 {canon_taxo_start[:12]}->{canon_taxo_end[:12]}")

    if drift:
        verdict, score = "inconclusive", 2.0
    elif hard_failures:
        verdict, score = "revise", 3.0
    else:
        verdict, score = "accept", 4.5 if not undetected else 4.0

    evidence = {
        "task_id": "W098-F2A-INDEP-VERDICT-01",
        "pass": 2,
        "reviewer": "worker-098",
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "reviewed_sha256": snap_hash,
        "canonical_path": "schemas/af_scc_c2_vacuum.yaml",
        "canonical_hash_at_start": canon_f2a_start,
        "canonical_hash_at_end": canon_f2a_end,
        "drift_during_review": drift,
        "supersedes_pass_1": {
            "pass_1_reviewed_sha256": "4f97273ef4404126ef5c8a083ccd5ed4d4ef9fd1aeaf6884c8c5aee0542e12f8",
            "reason": "F2a republished to b6123750b37d (rev11) before pass-1 emission; "
                      "pass-1 verdict is advisory only under the map's superseded-hash rule",
            "delta": "rev11 comment + revision 10->11 + f0_binding declared hash refreshed "
                     "to the live canonical F0; no class-semantics change (diff reviewed)",
        },
        "snapshot_path": str(SNAP.relative_to(ROOT)),
        "support_hashes": {
            "canonical_formulation_taxonomy.yaml": canon_taxo_start,
            "authoring_formulation_taxonomy.yaml": V.sha256_file(SUPP_TAXO),
            "rule_spec.json": V.sha256_file(V.SPEC),
            "VOCAB_ALIASES.json": V.sha256_file(ROOT / "artifacts/formulation/VOCAB_ALIASES.json"),
        },
        "stage_1_canonical_gate": {
            "tool": "artifacts/formulation/tools/check_class_schema.py",
            "tool_sha256": V.sha256_file(V.GATE),
            "verdict": gate.get("verdict"),
            "failed_rules": gate.get("failed_rules"),
            "exit_code": gate.get("_exit_code"),
        },
        "stage_2_class_separation": {
            "tool": "research_map/class_separation.py",
            "tool_sha256": V.sha256_file(ROOT / "research_map/class_separation.py"),
            "findings": cs_findings,
            "hard_findings": cs_hard,
        },
        "stage_3_contract_checks": checks,
        "stage_3_failed": [x["check"] for x in failed],
        "stage_3_hard_failed": [x["check"] for x in hard],
        "stage_3_scope_notes": [x["detail"] for x in scope_notes],
        "stage_4_controls": controls,
        "stage_4_detection_rate": detection_rate,
        "stage_4_undetected": undetected,
        "stage_5_drift": {
            "f2a_start": canon_f2a_start, "f2a_end": canon_f2a_end,
            "f0_start": canon_taxo_start, "f0_end": canon_taxo_end, "drift": drift,
        },
        "verdict": verdict,
        "score": score,
        "hard_failures": hard_failures,
        "documented_method_blind_spots": undetected + [
            "semantic prose leak in non-asserted explanatory fields (gate's documented blind spot)",
            "mathematical correctness of definitions (both stages structural only)",
            "citation scope/truth of l1_ledger_refs (not verified here)",
        ],
        "scope_limit": (
            "Structural + contract conformance of one snapshot at the pinned hash. The canonical "
            "F0 and the authoring-tree supplement are NOT byte-identical, so class-contract "
            "binding is alias-aware and remains conditional on the controller's F0 publication "
            "resolution. Not a physics verdict and not a gate verdict."),
        "next_falsifier": (
            "A class-merge / conclusion-inflation / regularity-weakening / vacuity defect in "
            f"{CLASS_ID} at {snap_hash[:12]} that survives the canonical gate, the "
            "class-separation detector and these contract checks; or drift of the canonical F2a "
            "or declared-F0 file away from the hashes recorded here."),
        "generated_at": V.now_iso(),
    }
    (HERE / "f2a_independent_evidence.v2.json").write_text(json.dumps(evidence, indent=1) + "\n")

    review = {
        "event_id": "w098-f2a-review-v2-" + V.now_iso(),
        "event_type": "review",
        "created_at": V.now_iso(),
        "actor": "worker-098",
        "target_id": NODE_ID,
        "class_id": CLASS_ID,
        "reviewer": "worker-098",
        "verdict": verdict,
        "score": score,
        "reviewed_sha256": snap_hash,
        "hard_failures": hard_failures,
        "findings": [
            f"pass 2 at live hash {snap_hash[:12]} (pass 1 {evidence['supersedes_pass_1']['pass_1_reviewed_sha256'][:12]} superseded by rev11)",
            f"canonical gate: {gate.get('verdict')} ({len(gate.get('failed_rules') or [])} failed rules)",
            f"class-separation detector: {len(cs_hard)} hard finding(s)",
            f"contract + cross-field + F0-binding checks: {len(checks) - len(failed)}/{len(checks)} ok"
            + (f" ({len(scope_notes)} F0-publication scope note)" if scope_notes else ""),
            f"mutation controls detected (union of 3 stages): "
            f"{sum(x['detected'] for x in controls)}/{len(controls)}",
            f"drift during pass 2: {drift}",
        ],
        "evidence_refs": [
            "artifacts/worker-098/f2a_independent_review/f2a_independent_evidence.v2.json",
            f"schemas/af_scc_c2_vacuum.yaml#{snap_hash[:12]}",
            f"research_map/formulation_taxonomy.yaml#{canon_taxo_start[:12]}",
        ],
        "artifact_refs": [
            "artifacts/worker-098/f2a_independent_review/f2a_independent_evidence.v2.json",
        ],
        "scope_limit": evidence["scope_limit"],
        "next_falsifier": evidence["next_falsifier"],
    }
    (HERE / "f2a_independent_verdict.v2.json").write_text(json.dumps(review, indent=1) + "\n")

    print(json.dumps({
        "pass": 2, "reviewed_sha256": snap_hash, "verdict": verdict, "score": score,
        "hard_failures": hard_failures, "gate": gate.get("verdict"),
        "classsep_hard": cs_hard,
        "contract_ok": f"{len(checks) - len(failed)}/{len(checks)}",
        "scope_notes": [x["check"] for x in scope_notes],
        "controls": f"{sum(x['detected'] for x in controls)}/{len(controls)}",
        "undetected": undetected, "drift": drift,
        "f0_binding_declared": str(declared)[:12],
        "f0_measured": canon_taxo_start[:12],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
