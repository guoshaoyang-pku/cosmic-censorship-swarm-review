#!/usr/bin/env python3
"""Emit deepseek-flash-13 outbox events for the N0 replication/triage and FORM-GATE-01.

Every event is validated against research_map/schemas.py before writing, and every artifact
hash is recomputed from disk at emit time. Worker events never set done/passed/gate verdicts.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "research_map"))
from schemas import validate_event, SchemaError  # noqa: E402

ACTOR = "deepseek-flash-13"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S%z")


def sha(rel: str) -> str:
    return hashlib.sha256((REPO / rel).read_bytes()).hexdigest()


def ref(rel: str, prefix: int = 16) -> str:
    return f"{rel}#{sha(rel)[:prefix]}"


def ev(eid, etype, **kw):
    e = {"event_id": eid, "event_type": etype, "created_at": NOW, "actor": ACTOR, **kw}
    validate_event(e)
    return e


def main() -> int:
    n0_impl = "numerics/tests/flat_wave_replication.py"
    n0_json = "numerics/results/flat_wave_replication.json"
    n0_triage = "numerics/tests/replication_triage.md"
    n0_snap = "artifacts/flash-13/n0_replication/evidence/candidate_flat_wave_snapshot.py"
    fg_gate = "artifacts/flash-13/form_gate/check_class_schema.py"
    fg_report = "artifacts/flash-13/form_gate/gate_report.json"
    fg_manifest = "artifacts/flash-13/form_gate/fixtures/manifest.json"
    fg_suite = "artifacts/flash-13/form_gate/fixture_suite_report.json"
    fg_readme = "artifacts/flash-13/form_gate/README.md"
    c2 = "schemas/af_scc_c2_vacuum.yaml"
    c0 = "schemas/af_scc_c0_vacuum.yaml"
    wcc = "schemas/af_wcc_vacuum.yaml"

    events = [
        # ---------------- N0 replication + triage ----------------
        ev("f13-n0-art-impl", "artifact", node_id="N0", class_id="AF-WCC-SCALAR-SPH",
           artifact_type="replication_scheme", path=n0_impl, sha256=sha(n0_impl),
           validation_status="unverified"),
        ev("f13-n0-art-run", "artifact", node_id="N0", class_id="AF-WCC-SCALAR-SPH",
           artifact_type="convergence_report", path=n0_json, sha256=sha(n0_json),
           validation_status="unverified"),
        ev("f13-n0-art-triage", "artifact", node_id="N0", class_id="AF-WCC-SCALAR-SPH",
           artifact_type="triage_note", path=n0_triage, sha256=sha(n0_triage),
           validation_status="unverified"),
        ev("f13-n0-art-snapshot", "artifact", node_id="N0", class_id="AF-WCC-SCALAR-SPH",
           artifact_type="pinned_candidate_snapshot", path=n0_snap, sha256=sha(n0_snap),
           validation_status="unverified"),
        ev("f13-n0-status-1", "status", node_id="N0", status="active", hours=1.5,
           summary=(
               "N0 replication + adj2 triage complete, unverified pending review. Three schemes "
               "run through the provided N0 harness: lffd order 1.9958 (drift 3.4e-15), cnfd "
               "(implicit Crank-Nicolson + 3-pt FD) 1.9935 (6.6e-08), cnfem (CN + P1 FEM) 1.9863 "
               "(8.5e-09); all three PASS order/invariant/stability, reference re-measured at "
               "1.9957695044715191. cnfem's earlier ORDER DISAGREES was an implementation sign "
               "error (M-cK instead of M+cK on the CN right-hand side), root-caused with a minimal "
               "reproduction and fixed in the scheme, not by deleting it or relaxing the gate; "
               "triage note submitted. Measured calibration: the harness invariant functional is "
               "leapfrog-specific and its 1e-6 tolerance does not distinguish exact from near "
               "conservation (reference 3.4e-15 vs 6.6e-08/8.5e-09), so an invariant PASS bounds "
               "the leapfrog functional, not the solver's own invariant. No node completion "
               "claimed; numerics_lock respected (N1 untouched)."),
           evidence_refs=[ref(n0_impl), ref(n0_json), ref(n0_triage),
                          "numerics/tests/flat_wave.py#743c73e4"],
           next_falsifier=(
               "Rerun artifacts/flash-04/n0_acceptance/harness.py on cnfd/cnfem and falsify the "
               "order claim; or exhibit a shared-axis bug (psi=r*phi reduction, Dirichlet walls, "
               "Taylor start) that all three schemes inherit, which this replication cannot detect.")),
        ev("f13-n0-claim-1", "claim",
           class_id="AF-WCC-SCALAR-SPH", node_id="N0", conclusion_type="numerical_evidence",
           statement=(
               "On the N0 flat-space spherical scalar-wave calibration (Gaussian pulse, r in "
               "[0,30], t_end=6, dr 0.2/0.1/0.05, cfl=0.5), two independent second-order methods "
               "reproduce the reference measured convergence order within the harness tolerance: "
               "implicit Crank-Nicolson + 3-pt FD gives 1.9935 and implicit Crank-Nicolson + P1 "
               "FEM gives 1.9863 against reference leapfrog 1.9958 (p_expected=2.0, p_tol=0.3), "
               "and all three pass the invariant and stability gates. Scope: test-field flat-space "
               "calibration only; no self-gravity; no cosmic-censorship statement."),
           assumptions=[
               "provided N0 harness config and Gaussian pulse used unchanged",
               "psi = r*phi reduction, Dirichlet walls and Taylor start are shared with the "
               "reference and are NOT independently tested",
               "artifacts are validation_status=unverified; a reviewer verdict is required before "
               "any promotion"],
           falsifier=(
               "A rerun of the provided harness in which cnfd or cnfem leaves p_expected +/- p_tol, "
               "or a demonstration that the shared Taylor start / psi=r*phi reduction carries a "
               "discretization bug common to all three schemes."),
           evidence_refs=[ref(n0_impl), ref(n0_json)],
           artifact_refs=[{"path": n0_impl, "sha256": sha(n0_impl)},
                          {"path": n0_json, "sha256": sha(n0_json)}]),
        # ---------------- FORM-GATE-01 ----------------
        ev("f13-fg-art-gate", "artifact", node_id="F1", class_id="AF-WCC-VAC-GEN",
           artifact_type="class_schema_gate", path=fg_gate, sha256=sha(fg_gate),
           validation_status="unverified"),
        ev("f13-fg-art-report", "artifact", node_id="F1", class_id="AF-WCC-VAC-GEN",
           artifact_type="gate_report", path=fg_report, sha256=sha(fg_report),
           validation_status="unverified"),
        ev("f13-fg-art-fixtures", "artifact", node_id="F1", class_id="AF-WCC-VAC-GEN",
           artifact_type="fixture_corpus", path=fg_manifest, sha256=sha(fg_manifest),
           validation_status="unverified"),
        ev("f13-fg-art-suite", "artifact", node_id="F1", class_id="AF-WCC-VAC-GEN",
           artifact_type="acceptance_suite_report", path=fg_suite, sha256=sha(fg_suite),
           validation_status="unverified"),
        ev("f13-fg-art-readme", "artifact", node_id="F1", class_id="AF-WCC-VAC-GEN",
           artifact_type="documentation", path=fg_readme, sha256=sha(fg_readme),
           validation_status="unverified"),
        ev("f13-fg-status-1", "status", node_id="F1", status="active", hours=1.5,
           summary=(
               "FORM-GATE-01 delivered at the assigned canonical path, unverified pending review. "
               "check_class_schema.py implements FORM-RULE-SPEC v1.0 R01-R16 parameterised per "
               "class (WCC: I+ and visibility are conclusions; SCC: I+ not in conclusion, "
               "visibility cross-referenced to WCC, extension regularity exactly C2 xor C0, "
               "R16 ledger enforced). Suite: 3/3 conforming fixtures pass; 18/18 mutants rejected, "
               "each keyed to exactly one rule id; 6 rephrased mutants -> 1 caught, 5 documented "
               "blind spots. Canonical run: af_wcc_vacuum.yaml PASS, af_scc_c0_vacuum.yaml PASS, "
               "af_scc_c2_vacuum.yaml FAIL on 14 rules because F2a is written to a pre-spec "
               "vocabulary (artifact_type/class_boundary/exact_quantifiers/metric_regularity/"
               "future_null_infinity) and lacks non_vacuity, conclusion.conclusion_type, "
               "provenance.citation_status, falsifier tiers and implication_ledger; a "
               "possible_synonyms diagnostic is attached. Exit codes: 0 pass, 1 fail, 3 canonical "
               "absent (not a pass). No node completion or gate verdict claimed."),
           evidence_refs=[ref(fg_gate), ref(fg_report), ref(fg_manifest),
                          ref(wcc), ref(c2), ref(c0)],
           next_falsifier=(
               "A conforming schema that the gate rejects on a rule a domain reviewer shows is "
               "legitimate, or a mutant that silently passes; for the C2 finding, the lead either "
               "revises F2a to the published key names or ratifies synonyms in FORM-RULE-SPEC.")),
        ev("f13-fg-claim-1", "claim",
           class_id="AF-SCC-C2-VAC-GEN", node_id="F2", conclusion_type="numerical_evidence",
           statement=(
               "Structural conformance check of the canonical C2 schema against FORM-RULE-SPEC "
               "v1.0: schemas/af_scc_c2_vacuum.yaml fails R01-R11, R14-R16 because it does not "
               "carry the published top-level field contract (it uses six pre-spec synonyms and "
               "omits the non_vacuity, conclusion-type, provenance-status, falsifier-tier and "
               "implication-ledger blocks). This is a vocabulary/contract finding, not a claim "
               "that the C2 mathematics is wrong."),
           assumptions=[
               "FORM-RULE-SPEC v1.0 key names are binding for canonical schemas",
               "the finding is structural; semantic equivalence of the synonym fields is not "
               "adjudicated here"],
           falsifier=(
               "The lead designates the synonyms as canonical (spec revision), after which the "
               "same gate must be re-run with the alias map extended; or a reviewer shows the C2 "
               "file does carry the spec-named blocks at paths the gate is not reading."),
           evidence_refs=[ref(fg_gate), ref(fg_report), ref(c2)],
           artifact_refs=[{"path": fg_report, "sha256": sha(fg_report)}]),
        ev("f13-fg-blocker-1", "blocker", node_id="F2",
           description=(
               "Canonical C2 schema (AF-SCC-C2-VAC-GEN, F2a) fails 14 of 16 gate rules under "
               "FORM-RULE-SPEC v1.0 because it is written to the pre-spec F1 draft vocabulary; "
               "the C0 sibling passes. Gate and fixture suite are green, so the blocker is a "
               "schema-revision or spec-adjudication decision, not a gate defect."),
           needed_to_unblock=(
               "lead-formulation decision: revise schemas/af_scc_c2_vacuum.yaml to the published "
               "key names (mirroring the C0 sibling), or amend FORM-RULE-SPEC with an explicit "
               "synonym/alias clause. Either way record the decision as a gate event; then the "
               "gate is re-run and the F2a gate status can be reviewed."),
           evidence_refs=[ref(fg_report), ref(c2), ref(c0),
                          "artifacts/formulation/rule_spec.json"]),
    ]

    out = REPO / "comms" / "outbox" / f"{ACTOR}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "a") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"wrote {len(events)} validated events to {out}")
    print(f"outbox sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
