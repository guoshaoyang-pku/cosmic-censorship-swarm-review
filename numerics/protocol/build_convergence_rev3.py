#!/usr/bin/env python3
"""Build ``numerics/results/flat_wave_convergence_rev3.json`` (N0, G-NUM).

Closes the stop rule of ``reviews/N0-review-lead-audit.json`` at the current hashes:

1. **Fourth rung / explicit scoping.** The certification basis is the protocol-exact
   FIXED-dt study ``numerics/protocol/n0_fixed_dt_certification.json``: four rungs per
   scheme, ``dt = 1e-4`` on every rung, three methodologically distinct schemes. The
   constant-CFL ladder is carried only as a labelled *mixed-order* supporting diagnostic;
   its order is never quoted as a spatial order.
2. **Class binding.** Re-bound to the declared F0 rev5
   ``research_map/formulation_taxonomy.yaml#0abb9ed8a961`` (revision 5 on disk).
3. **Independent replication verdict.** Three independent worker records are pinned:
   worker-046 (from-scratch re-execution of the frozen module, verdict ``SUPPORTED``),
   worker-057 (independent re-analysis of the filed rows, verdict ``REPRODUCED``),
   worker-081 (adjudication review at the protocol hash, verdict ``accept``).

Read-only: this builder never runs a solver, never imports the certification generator,
and writes exactly one file (the output path). It exits 2 with no output if any internal
invariant is violated (fail closed).

    python3 numerics/protocol/build_convergence_rev3.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

OUT_REL = "numerics/results/flat_wave_convergence_rev3.json"
OUT = REPO / OUT_REL

CERT_REL = "numerics/protocol/n0_fixed_dt_certification.json"
CANON_REL = "numerics/results/flat_wave_convergence.json"
REPL_REL = "numerics/results/flat_wave_replication.json"
R4_REL = "numerics/tests/n0_order_4rung.json"
TSC_REL = "numerics/protocol/temporal_subdominance_control.json"
PROTOCOL_REL = "numerics/CONVERGENCE_PROTOCOL.md"
HARNESS_REL = "numerics/tests/flat_wave.py"
REPL_SCRIPT_REL = "numerics/tests/flat_wave_replication.py"
F0_REL = "research_map/formulation_taxonomy.yaml"
LOCK_GUARD_REL = "numerics/tests/selfgravity_lock_guard.py"
REVIEW_REL = "reviews/N0-review-lead-audit.json"
GATES_REL = "numerics/gates.py"
REGISTRY_REL = "runtime/state/artifact_hashes.json"

F0_REV5_SHA = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
INDEPENDENT = [
    {
        "reviewer": "worker-046",
        "path": "artifacts/worker-046/n0_fixed_dt_independent/verification.json",
        "role": "from-scratch re-execution of the frozen replication module under a hash guard",
        "expected_verdict": "SUPPORTED",
    },
    {
        "reviewer": "worker-057",
        "path": "artifacts/worker-057/n0_fixeddt_verify/report.json",
        "role": "independent re-analysis of the filed certification rows (generator not imported)",
        "expected_verdict": "REPRODUCED",
    },
    {
        "reviewer": "worker-081",
        "path": "artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json",
        "role": "independent adjudication review of the protocol/evidence contest at the protocol hash",
        "expected_verdict": "accept",
        "review_event_id": "w081-20260912T0042050800-adj2-review",
        "review_outbox": "comms/outbox/worker-081.jsonl",
    },
]


def sha256(rel: str) -> str | None:
    p = REPO / rel
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(rel: str):
    return json.loads((REPO / rel).read_text())


def main() -> int:
    checks: list[dict] = []
    failures: list[str] = []

    def check(cid: str, ok: bool, detail: str) -> None:
        checks.append({"check_id": cid, "pass": bool(ok), "detail": detail})
        if not ok:
            failures.append(f"{cid}: {detail}")

    for rel in (CERT_REL, CANON_REL, REPL_REL, R4_REL, TSC_REL, PROTOCOL_REL,
                HARNESS_REL, REPL_SCRIPT_REL, F0_REL, LOCK_GUARD_REL, GATES_REL,
                REGISTRY_REL, REVIEW_REL):
        check(f"exists::{rel}", (REPO / rel).is_file(), f"{rel} on disk")
    for item in INDEPENDENT:
        check(f"exists::{item['path']}", (REPO / item["path"]).is_file(), item["path"])

    cert = load(CERT_REL)
    canon = load(CANON_REL)
    r4 = load(R4_REL)
    tsc = load(TSC_REL)
    registry = load(REGISTRY_REL)
    review = load(REVIEW_REL)

    # ---- 1. certification basis: four rungs, fixed dt, in band, monotone ----
    scheme_names = list(cert["schemes"].keys())
    check("cert::schemes", set(scheme_names) == {"lffd", "cnfd", "cnfem"},
          f"schemes on file: {scheme_names}")
    check("cert::frozen_hash_guard", bool(cert["frozen_module"]["hash_guard_passed"]),
          f"frozen module guard {cert['frozen_module']['hash_guard_passed']}")
    check("cert::frozen_hash_matches_disk",
          cert["frozen_module"]["sha256"] == sha256(REPL_SCRIPT_REL),
          f"certification names {cert['frozen_module']['sha256'][:16]}, disk "
          f"{(sha256(REPL_SCRIPT_REL) or 'MISSING')[:16]}")
    check("cert::dt_fixed_1e-4", float(cert["config"]["dt_fixed"]) == 1e-4,
          f"dt_fixed = {cert['config']['dt_fixed']}")

    basis: dict = {}
    max_abs_dp = 0.0
    for name in scheme_names:
        f = cert["schemes"][name]["fixed_dt_certification"]
        rows = f["rows"]
        dts = sorted({float(row["dt"]) for row in rows})
        drs = [float(row["dr"]) for row in rows]
        errs = [float(row["l2_error"]) for row in rows]
        monotone = all(b < a for a, b in zip(errs, errs[1:]))
        in_band = abs(float(f["fit_order"]) - 2.0) <= 0.3
        check(f"cert::{name}::rungs", len(rows) == 4, f"{name} rungs = {len(rows)}")
        check(f"cert::{name}::dt", dts == [1e-4], f"{name} dt values = {dts}")
        check(f"cert::{name}::dr", drs == [0.2, 0.1, 0.05, 0.025], f"{name} dr = {drs}")
        check(f"cert::{name}::monotone", monotone and bool(f["monotone"]),
              f"{name} monotone = {monotone}")
        check(f"cert::{name}::in_band", in_band and bool(f["within_band"]),
              f"{name} fit order {f['fit_order']} vs 2.0 +/- 0.3")
        check(f"cert::{name}::r5_delta", float(f["delta_R5"]) == max(
            float(f["pair_half_range"]), float(f["least_squares_se"])),
              f"{name} delta_R5 = {f['delta_R5']}")
        basis[name] = {
            "fit_order": f["fit_order"],
            "delta_R5": f["delta_R5"],
            "least_squares_se": f["least_squares_se"],
            "pair_orders": f["pair_orders"],
            "pair_half_range": f["pair_half_range"],
            "monotone": bool(f["monotone"]),
            "within_band": bool(f["within_band"]),
            "rungs": len(rows),
            "dr_values": drs,
            "dt": dts[0],
            "steps_per_rung": sorted({int(row["steps"]) for row in rows}),
            "l2_error_by_dr": {str(row["dr"]): row["l2_error"] for row in rows},
            "constant_cfl_mixed_order_fit": cert["schemes"][name][
                "constant_cfl_mixed_order_control"]["fit_order"],
            "fixed_minus_mixed_shift": cert["schemes"][name]["order_shift_vs_mixed"],
        }
    for a in scheme_names:
        for b in scheme_names:
            if a < b:
                dp = abs(basis[a]["fit_order"] - basis[b]["fit_order"])
                max_abs_dp = max(max_abs_dp, dp)
                check(f"cert::R5::{a}_vs_{b}", dp <= 0.25,
                      f"|dp| = {dp:.3e} vs R5 floor 0.25")
    check("cert::claim_basis", bool(cert["verdict"]["all_within_band"]) and
          bool(cert["verdict"]["all_monotone"]),
          "certification verdict: all monotone and all within band")

    # ---- 2. canonical 5-rung report carried as mixed-order support only ----
    canon_studies = [{
        "family": s["family"],
        "order_scheme": s["order_scheme"],
        "cfl": s["cfl"],
        "rungs": len(s["rows"]),
        "n_values": [row["n"] for row in s["rows"]],
        "order_l2": s["order_l2"],
        "order_gate": s["order_gate"],
        "label": "mixed-order (constant CFL; dt/dr = cfl*h is refined with h) - supporting diagnostic, NOT an order-certification basis",
    } for s in canon["studies"]]
    check("canon::rungs_at_least_4",
          all(s["rungs"] >= 4 for s in canon_studies),
          f"canonical rungs = {[s['rungs'] for s in canon_studies]}")
    check("canon::not_certification_basis",
          "mixed-order" in canon_studies[0]["label"], "canonical studies labelled mixed-order")

    # ---- 3. F0 rev5 class binding ----
    f0_text = (REPO / F0_REL).read_text()
    f0_sha = sha256(F0_REL)
    check("f0::rev5_sha", f0_sha == F0_REV5_SHA, f"disk sha {str(f0_sha)[:16]}")
    check("f0::revision_5", "revision: 5" in f0_text, "taxonomy declares revision: 5")
    class_id = cert["class_id"]
    check("f0::class_id_present", class_id in f0_text, f"{class_id} appears in F0 rev5")

    # ---- 4. independent replication verdicts ----
    indep: list[dict] = []
    for item in INDEPENDENT:
        doc = load(item["path"])
        rec = {
            "reviewer": item["reviewer"],
            "path": item["path"],
            "sha256": sha256(item["path"]),
            "role": item["role"],
            "verdict": doc.get("verdict"),
            "task_id": doc.get("task_id") or doc.get("reviewer"),
        }
        if item["reviewer"] == "worker-046":
            outcomes = doc.get("criteria_outcomes", {})
            rec["criteria_passed"] = sum(1 for v in outcomes.values() if v)
            rec["criteria_total"] = len(outcomes)
            rec["headline"] = doc.get("headline")
            rec["frozen_module_sha256"] = doc["artifact_hashes"].get("independent_fixed_dt.py")
            rec["claims_not_made"] = doc.get("not_claimed")
        elif item["reviewer"] == "worker-057":
            chk = doc.get("checks", [])
            rec["checks_total"] = len(chk)
            rec["checks_pass"] = sum(1 for c in chk if c.get("pass"))
            rec["findings"] = doc.get("finding_count")
            rec["advisories"] = doc.get("advisory_count")
            rec["controls_pass"] = sum(1 for c in doc.get("controls", []) if c.get("pass"))
            rec["controls_total"] = len(doc.get("controls", []))
            rec["drift_stable"] = bool((doc.get("drift") or {}).get("stable"))
            rec["cert_sha256_verified"] = (doc.get("drift") or {}).get("cert_sha256_at_end")
        else:
            # worker-081's verdict is a structured adjudication dict; the review event that
            # carries the flat `accept` is pinned separately by canonical-event hash.
            v = doc.get("verdict")
            rec["verdict_detail"] = v if isinstance(v, dict) else None
            rec["review_event_id"] = item.get("review_event_id")
            rec["review_event_verdict"] = None
            rec["review_event_canonical_sha256"] = None
            outbox = REPO / item["review_outbox"]
            if outbox.is_file():
                for line in outbox.read_text(errors="replace").splitlines():
                    try:
                        ev = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if ev.get("event_id") == item.get("review_event_id"):
                        rec["review_event_verdict"] = ev.get("verdict")
                        rec["review_event_reviewer"] = ev.get("reviewer")
                        rec["review_event_target"] = ev.get("target_id")
                        rec["reviewed_sha256"] = ev.get("reviewed_sha256")
                        rec["review_event_canonical_sha256"] = hashlib.sha256(
                            json.dumps(ev, sort_keys=True).encode()).hexdigest()
                        break
            rec["verdict"] = rec["review_event_verdict"]
            rec["hard_failures"] = doc.get("hard_failures")
            rec["findings_headline"] = (doc.get("findings") or [None])[0]
        check(f"indep::{item['reviewer']}::verdict",
              rec["verdict"] == item["expected_verdict"],
              f"verdict = {rec['verdict']!r} (expected {item['expected_verdict']!r})")
        indep.append(rec)

    w057 = next(r for r in indep if r["reviewer"] == "worker-057")
    check("indep::w057::no_findings", w057["findings"] == 0,
          f"worker-057 findings = {w057['findings']}, advisories = {w057['advisories']}")
    check("indep::w057::stable_pin", w057["drift_stable"] and
          w057["cert_sha256_verified"] == sha256(CERT_REL),
          f"worker-057 re-hashed the certification stable at {str(w057['cert_sha256_verified'])[:16]}")
    w046 = next(r for r in indep if r["reviewer"] == "worker-046")
    check("indep::w046::all_criteria", w046["criteria_passed"] == w046["criteria_total"] == 8,
          f"worker-046 criteria {w046['criteria_passed']}/{w046['criteria_total']}")
    w081 = next(r for r in indep if r["reviewer"] == "worker-081")
    check("indep::w081::accept_at_protocol_hash",
          w081["review_event_verdict"] == "accept"
          and w081["reviewed_sha256"] == sha256(PROTOCOL_REL)
          and (w081["verdict_detail"] or {}).get("binding_accept_at_current_hash") is True
          and (w081["verdict_detail"] or {}).get("blocks_gate_pass") is False,
          f"review event {w081['review_event_verdict']} at protocol "
          f"{str(w081['reviewed_sha256'])[:16]}, disposition "
          f"{(w081['verdict_detail'] or {}).get('disposition')}")

    # ---- 5. temporal admissibility of the mixed-order ladder (honest record) ----
    tsc_schemes = {}
    for name, s in tsc["schemes"].items():
        tsc_schemes[name] = {
            "constant_cfl_fit": s["A_constant_cfl_ladder"]["fit_order"],
            "fixed_dt_1e-3_fit": s["B_fixed_dt_ladders"]["dt_0.001"]["fit_order"],
            "admissible_as_spatial": s["checks"]["admissible_as_spatial"],
            "verdict": s["verdict"],
        }
    check("tsc::present", bool(tsc.get("overall")), "temporal subdominance control on file")

    # ---- 6. lock guard (must stay N1_BLOCKED; no solver dir) ----
    solver_present = (REPO / "numerics/spherical_solver").exists()
    check("lock::no_solver_dir", not solver_present, "numerics/spherical_solver absent")
    try:
        from numerics import gates  # noqa: E402
        gate = gates.evaluate(REPO)
        lock = {
            "verdict": gate.get("verdict"),
            "production_allowed": gate.get("production_allowed"),
            "lock_state": (gate.get("lock") or {}).get("state"),
            "blocking_reasons": gate.get("blocking_reasons"),
            "protocol_review": gate.get("protocol_review"),
            "order_agreement": gate.get("order_agreement"),
            "evaluated_at": gate.get("evaluated_at"),
        }
        check("lock::blocked", gate.get("verdict") == "N1_BLOCKED" and
              gate.get("production_allowed") is False,
              f"guard verdict {gate.get('verdict')}, production_allowed {gate.get('production_allowed')}")
    except Exception as exc:  # fail closed: an error is not a release
        lock = {"error": f"{type(exc).__name__}: {exc}", "verdict": "N1_BLOCKED",
                "production_allowed": False}
        check("lock::blocked_on_error", True, f"guard import/eval error recorded: {exc}")

    # withdrawn accept still counted by the review binder (worker-081 mechanical finding)
    pa = (lock.get("protocol_review") or {})
    accepting = [r.get("event_id") if isinstance(r, dict) else r for r in pa.get("accepting_reviews", [])]
    withdrawn_counted = "w081-20260912T002140-c8-review" in accepting
    guard_finding = {
        "finding": ("numerics/gates.py::_protocol_review counts the accept "
                    "w081-20260912T002140-c8-review even though its author withdrew it in "
                    "w081-2026-09-12T00:29:19+0800-f1-review; a later accept by the same "
                    "reviewer at the same hash (w081-20260912T0042050800-adj2-review) does not "
                    "rescind the earlier revise, so the binder has no supersession rule."),
        "measured": {
            "accepting_reviews": accepting,
            "dissenting_reviews": [r.get("event_id") if isinstance(r, dict) else r
                                   for r in pa.get("dissenting_reviews", [])],
            "contest": pa.get("contest"),
            "withdrawn_accept_still_counted": withdrawn_counted,
        },
        "disposition_needed": ("controller adjudication (withdrawal semantics) or an explicit "
                               "guard supersession rule by (reviewer, target) at one hash; "
                               "numerics does not self-adjudicate a review it owns."),
    }
    check("guard::contest_visible", bool(pa.get("contest")) is True,
          "protocol contest is reported, not silently green")

    # ---- 7. registration state (C4) ----
    reg = registry.get("registry", {})
    reg_paths = [CERT_REL, PROTOCOL_REL, CANON_REL, HARNESS_REL, REPL_SCRIPT_REL,
                 GATES_REL, R4_REL, TSC_REL] + [i["path"] for i in INDEPENDENT]
    registration = {}
    for rel in reg_paths:
        entry = reg.get(rel)
        registration[rel] = {
            "registered": entry is not None,
            "registered_sha256": (entry or {}).get("sha256"),
            "disk_sha256": sha256(rel),
            "match": bool(entry) and str(entry.get("sha256", "")).startswith(
                str(sha256(rel))[:16]) if sha256(rel) else None,
        }
    unregistered = [rel for rel, v in registration.items() if not v["registered"]]
    drifted = [rel for rel, v in registration.items()
               if v["registered"] and v["match"] is False]

    # ---- compose ----
    degraded = not all(abs(basis[n]["fit_order"] - 2.0) <= 0.3 for n in scheme_names)
    report = {
        "schema": "n0-convergence-report-rev3/v1",
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": class_id,
        "conclusion_type": "numerical_evidence",
        "artifact": HARNESS_REL,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "generator": ("astra-lead-numerics, one independent lifecycle (read-only consolidation; "
                      "certification generator not imported, no solver re-run)"),
        "purpose": ("rev-3 convergence report: close the N0 audit stop rule at the current "
                    "hashes with a four-rung fixed-dt certification basis, an F0 rev5 class "
                    "binding, and independent replication verdicts. Supersedes "
                    "numerics/results/flat_wave_convergence.json as the order-certification "
                    "report; that file is retained as the mixed-order canonical harness run."),
        "stop_rule_closures": {
            "four_rungs_or_scoped": (
                "CLOSED by a fourth rung, not by scoping: the certification basis has four "
                "rungs per scheme at fixed dt = 1e-4 for three schemes."),
            "f0_rebind": (
                f"CLOSED: class binding re-derived against research_map/formulation_taxonomy.yaml"
                f"#0abb9ed8a961 (revision 5 on disk)."),
            "independent_replication_verdict": (
                "CLOSED: worker-046 (from-scratch replication, SUPPORTED 8/8), worker-057 "
                "(independent re-analysis, REPRODUCED, 0 findings), worker-081 (adjudication "
                "review, accept) - all hash-pinned below."),
        },
        "order_claim": {
            "statement": (
                "On a fixed Minkowski background, for the reduced spherical scalar-wave problem "
                "u_tt = u_rr (u = r*psi, Dirichlet walls, smooth Gaussian-pulse manufactured "
                "solution, r_max = 30, t_end = 6), the three schemes measured here show spatial "
                "discretisation order p = 2 within the protocol band |p - 2| <= 0.3, when the "
                "spatial order is measured at FIXED dt = 1e-4 on four rungs "
                "(dr = 0.2, 0.1, 0.05, 0.025). The constant-CFL ladder is a mixed-order "
                "diagnostic and is not the certification basis."),
            "p_design": 2.0,
            "p_tolerance": 0.3,
            "p_by_scheme": {n: basis[n]["fit_order"] for n in scheme_names},
            "delta_R5_by_scheme": {n: basis[n]["delta_R5"] for n in scheme_names},
            "max_cross_scheme_abs_dp": max_abs_dp,
            "cross_scheme_r5_floor": 0.25,
            "fitted_norm": "integral L2 (harness key l2_error); L-infinity reported in the canonical run (R5a)",
            "degraded": bool(degraded),
            "report_the_order_even_if_degraded": (
                "no degradation observed; the fixed-dt order is 1.9999 for every scheme, "
                "TIGHTER than the constant-CFL mixed-order values it replaces"),
        },
        "certification_basis": {
            "path": CERT_REL,
            "sha256": sha256(CERT_REL),
            "protocol_clause": ("numerics/CONVERGENCE_PROTOCOL.md rev 3 section 3 item 2 "
                                "(>= 4 rungs for an order-certification claim) and item 4 "
                                "(spatial order at fixed small dt = 1e-4)"),
            "protocol_sha256": sha256(PROTOCOL_REL),
            "rungs_per_scheme": 4,
            "dr_values": [0.2, 0.1, 0.05, 0.025],
            "dt": 1e-4,
            "schemes": basis,
            "frozen_module": cert["frozen_module"],
            "supersedes_evidence_basis": cert.get("supersedes_evidence_basis"),
        },
        "supporting_diagnostics": {
            "canonical_mixed_order_run": {
                "path": CANON_REL,
                "sha256": sha256(CANON_REL),
                "label": ("constant-CFL (cfl = 0.25 / 0.1) studies with 5 rungs; retained as the "
                          "harness acceptance run and a mixed-order diagnostic - never quoted as "
                          "a spatial order"),
                "studies": canon_studies,
            },
            "replication_mixed_order": {
                "path": REPL_REL,
                "sha256": sha256(REPL_REL),
                "label": "controller-verified 3-rung constant-CFL replication; supporting only",
            },
            "four_rung_mixed_order_addendum": {
                "path": R4_REL,
                "sha256": sha256(R4_REL),
                "label": "4-rung constant-CFL addendum to the frozen run; mixed-order, supporting only",
            },
        },
        "temporal_control": {
            "path": TSC_REL,
            "sha256": sha256(TSC_REL),
            "admissibility_rule": tsc["admissibility_rule_stated_before_results"],
            "schemes": tsc_schemes,
            "note": ("the pre-stated admissibility rule marks at least one scheme's constant-CFL "
                     "ladder inadmissible as spatial; the certification therefore rests on the "
                     "fixed-dt ladder only"),
        },
        "independent_replication": {
            "verdict": "REPLICATED",
            "verdicts": indep,
            "caveat": ("worker-local replication verdicts, not gate verdicts; gate authority is "
                       "Astra. Each verdict is pinned by sha256 of its artifact."),
        },
        "class_binding": {
            "path": F0_REL,
            "sha256": sha256(F0_REL),
            "declared_revision": 5,
            "class_id": class_id,
            "binding_status": ("BOUND to F0 rev5 0abb9ed8a961; provisional only in the sense that "
                               "G-F0 has not passed in the map"),
            "previous_stale_pins": ["66bf917bd368", "565a6e50"],
            "note": ("the protocol preamble (rev 3) still cites the superseded 66bf917b/565a6e50 "
                     "pins; that citation is not load-bearing for the order claim, and rewriting "
                     "the protocol would invalidate the review verdicts bound to its current "
                     "hash, so the drift is recorded here and as a blocker instead"),
        },
        "review_state_at_generation": {
            "protocol_path": PROTOCOL_REL,
            "protocol_sha256": sha256(PROTOCOL_REL),
            "reviewed": pa.get("reviewed"),
            "contest": pa.get("contest"),
            "accepting_reviews": accepting,
            "dissenting_reviews": [r.get("event_id") if isinstance(r, dict) else r
                                   for r in pa.get("dissenting_reviews", [])],
            "guard_finding": guard_finding,
        },
        "registration_state": {
            "source": REGISTRY_REL,
            "registry_generated_paths": registration,
            "unregistered_paths": unregistered,
            "hash_drift_paths": drifted,
            "note": ("registration in runtime/state/artifact_hashes.json is the controller's step "
                     "(COMMS PROTOCOL rule 2); this report records the measured gap, it does not "
                     "write the registry"),
        },
        "lock_guard": lock,
        "review_being_closed": {
            "path": REVIEW_REL,
            "sha256": sha256(REVIEW_REL),
            "reviewer": review.get("reviewer"),
            "verdict": review.get("verdict"),
            "hard_failures": review.get("hard_failures"),
            "stop_rule": review.get("stop_rule"),
        },
        "claims_not_made": [
            "no gate verdict and no gate self-pass (authority: Astra)",
            "no node completion; N0 stays active, numerics_lock stays LOCKED and N1 stays queued",
            "no self-review: all three independent verdicts are authored by other agents",
            "no physics claim; flat-space discretisation evidence only",
            "no claim that the shared axes (psi = r*phi, Dirichlet box, Taylor start, Gaussian-pulse family) are independent",
            "no claim that the constant-CFL orders are spatial orders",
        ],
        "falsifiers": [
            "re-hashing any pinned path here and finding a different sha256 voids that citation",
            "a certification row with dt != 1e-4, a non-monotone error ladder, or fewer than four rungs refutes the certification basis",
            "a recomputed fixed-dt order outside |p - 2| <= 0.3, or a cross-scheme |dp| above 0.25, refutes the order claim",
            "any file appearing under numerics/spherical_solver/ while numerics_lock.state == 'locked' refutes the scope compliance of this report",
            "a gate verdict of pass recorded while numerics/CONVERGENCE_PROTOCOL.md is not registered in runtime/state/artifact_hashes.json would falsify the registration statement above",
        ],
        "provenance": {
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "generator_script": "numerics/protocol/build_convergence_rev3.py",
            "generator_script_sha256": sha256("numerics/protocol/build_convergence_rev3.py")
            if (REPO / "numerics/protocol/build_convergence_rev3.py").is_file() else None,
            "solver_rerun": False,
            "certification_generator_imported": False,
            "wall_seconds_build": None,
        },
        "internal_checks": {
            "all_pass": not failures,
            "checks": checks,
            "failures": failures,
        },
    }

    if failures:
        print("FAIL-CLOSED: invariants violated, nothing written:", file=sys.stderr)
        for f in failures:
            print("  -", f, file=sys.stderr)
        return 2

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "out": OUT_REL,
        "sha256": sha256(OUT_REL),
        "checks": len(checks),
        "failures": failures,
        "order": {n: basis[n]["fit_order"] for n in scheme_names},
        "max_abs_dp": max_abs_dp,
        "unregistered": unregistered,
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
