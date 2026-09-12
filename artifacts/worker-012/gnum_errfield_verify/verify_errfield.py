#!/usr/bin/env python3
"""W012-GNUM-ERRFIELD-VERIFY-01 — independent recomputation of the N0 scheme
error-field orthogonality check, and its extension to the certified fixed dt=1e-4 regime.

Read-only on canonical paths. No solver; no self-gravity; numerics_lock stays LOCKED.
See PRE_REGISTRATION.md for the predictions fixed before this run.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.dont_write_bytecode = True

FROZEN_REL = "numerics/tests/flat_wave_replication.py"
FROZEN_SHA = "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422"

PINS = {
    "numerics/tests/flat_wave_replication.py": FROZEN_SHA,
    "numerics/protocol/error_field_orthogonality_check.json":
        "1b2d3162b0715d9b7dd3c304248c88ccd55b686ea81b401ed3f5baa60ede5945",
    "numerics/protocol/error_field_orthogonality_check.py":
        "4562331fb73d6fd60ebcf4a50e9f88613db72f8d4aca4e1e340fddf7fb2f0dc2",
    "numerics/CONVERGENCE_PROTOCOL.md":
        "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274",
    "numerics/protocol/n0_fixed_dt_certification.json":
        "1677822ceb9c81e8f6e48dee8360ab13edc35623c51f4be68bd6589a5fe79920",
}

DECLARED_CASES = [(0.2, 1e-3), (0.1, 1e-3)]          # the artifact's own configs
CERTIFIED_CASES = [(0.2, 1e-4), (0.1, 1e-4), (0.05, 1e-4)]  # the certified fixed-dt regime
R_MAX, T_END = 30.0, 6.0
SCHEMES = ("lffd", "cnfd", "cnfem")
TOL = {"l2_rel": 1e-9, "corr_abs": 1e-6, "sign_abs": 1e-6, "ratio_rel": 1e-6}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def measure_pins() -> dict:
    out = {}
    for rel, decl in PINS.items():
        p = REPO / rel
        out[rel] = {"declared": decl, "measured": sha256_file(p) if p.is_file() else None,
                    "match": p.is_file() and sha256_file(p) == decl}
    return out


def load_frozen():
    """Import the frozen module from a byte-identical snapshot inside this artifact dir."""
    src = REPO / FROZEN_REL
    measured = sha256_file(src)
    snap = HERE / "raw" / f"frozen_flat_wave_replication_{FROZEN_SHA[:12]}.py"
    snap.write_bytes(src.read_bytes())
    snap_sha = sha256_file(snap)
    if not (measured == FROZEN_SHA == snap_sha):
        raise SystemExit(json.dumps({"error": "frozen module hash mismatch",
                                     "measured": measured, "snapshot": snap_sha}))
    spec = importlib.util.spec_from_file_location("frozen_flat_wave_replication_snapshot", snap)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, snap


def corr(a: np.ndarray, b: np.ndarray) -> float:
    """Pearson correlation via numpy (independent of the generator's centred-sum code)."""
    return float(np.corrcoef(a, b)[0, 1])


def sign_agree(a: np.ndarray, b: np.ndarray) -> float:
    """|error|-mass fraction where the two fields share sign (same definition, own code)."""
    w = np.abs(a) + np.abs(b)
    tot = float(w.sum())
    if tot == 0.0:
        return float("nan")
    return float(w[np.sign(a) == np.sign(b)].sum() / tot)


def case_stats(mod, dr: float, dt: float) -> tuple[dict, dict]:
    pulse = mod.PulseExact()
    fields, errs = {}, {}
    final_t = steps = None
    for s in SCHEMES:
        case = mod.run_case(mod.make_factory(s, pulse=pulse), dr, dt / dr, R_MAX, T_END,
                            sample_every=10 ** 9)
        r = case["r"]
        exact = pulse.psi(r, case["t"][-1])
        e = case["psi"][-1] - exact
        fields[s] = e
        errs[s] = float(np.sqrt(np.sum(e * e) * dr))
        final_t, steps = float(case["t"][-1]), int(case["steps"])
    pairwise = {}
    for a, b in (("lffd", "cnfd"), ("cnfd", "cnfem"), ("lffd", "cnfem")):
        na, nb = float(np.linalg.norm(fields[a])), float(np.linalg.norm(fields[b]))
        pairwise[f"{a}_vs_{b}"] = {
            "corr": corr(fields[a], fields[b]),
            "cosine": float(np.dot(fields[a], fields[b]) / (na * nb)) if na * nb > 0 else float("nan"),
            "sign_agreement_mass_fraction": sign_agree(fields[a], fields[b]),
            "norm_ratio": float(errs[a] / errs[b]),
        }
    rec = {
        "dr": dr, "dt": dt, "final_t": final_t, "steps": steps,
        "l2_error": errs,
        "spread_relative": float((max(errs.values()) - min(errs.values()))
                                 / float(np.mean(list(errs.values())))),
        "pairwise": pairwise,
    }
    rec["reading"] = {
        "cnfd_vs_cnfem_negative": bool(pairwise["cnfd_vs_cnfem"]["corr"] < -0.5),
        "same_stencil_family_positive": bool(pairwise["lffd_vs_cnfd"]["corr"] > 0.9),
        "shared_error_artifact": bool(pairwise["cnfd_vs_cnfem"]["corr"] > 0.5),
    }
    return rec, fields


def symbol_fits() -> dict:
    """Leading coefficient of the two spatial-operator symbols vs -k^2.

    S(theta) = h^2 * symbol(L) is dimensionless; -k^2 h^2 = -theta^2, so
    r(theta) = S(theta)/(-theta^2) - 1 and the slope of r vs theta^2 is the
    leading coefficient of the spatial truncation error.
    """
    th = np.linspace(0.02, 0.2, 400)
    s_fd = -4.0 * np.sin(th / 2.0) ** 2                       # 3-point central FD
    s_fem = -6.0 * (1.0 - np.cos(th)) / (2.0 + np.cos(th))    # P1 consistent mass FEM
    r_fd = s_fd / (-th ** 2) - 1.0
    r_fem = s_fem / (-th ** 2) - 1.0
    return {
        "theta_range": [0.02, 0.2],
        "fd_slope": float(np.polyfit(th ** 2, r_fd, 1)[0]),
        "fem_slope": float(np.polyfit(th ** 2, r_fem, 1)[0]),
        "declared_fd": -1.0 / 12.0,
        "declared_fem": 1.0 / 12.0,
        "fd_residual_max": float(np.max(np.abs(r_fd + th ** 2 / 12.0))),
        "fem_residual_max": float(np.max(np.abs(r_fem - th ** 2 / 12.0))),
    }


def compare_declared(recomputed: dict, declared: dict) -> dict:
    """Numerical agreement between the recomputation and the filed artifact."""
    out = {"cases": []}
    for rc, dc in zip(recomputed, declared["cases"]):
        assert abs(rc["dr"] - dc["dr"]) < 1e-15 and abs(rc["dt"] - dc["dt"]) < 1e-18
        d = {"dr": rc["dr"], "dt": rc["dt"], "l2_rel": {}, "pairwise": {}}
        for s in SCHEMES:
            d["l2_rel"][s] = abs(rc["l2_error"][s] - dc["l2_error"][s]) / abs(dc["l2_error"][s])
        for pair, vals in dc["pairwise"].items():
            rp = rc["pairwise"][pair]
            d["pairwise"][pair] = {
                "corr_abs": abs(rp["corr"] - vals["corr"]),
                "sign_abs": abs(rp["sign_agreement_mass_fraction"]
                                - vals["sign_agreement_mass_fraction"]),
                "ratio_rel": abs(rp["norm_ratio"] - vals["norm_ratio"]) / abs(vals["norm_ratio"]),
            }
        d["reading_match"] = bool(
            rc["reading"]["shared_error_artifact"] == dc["reading"]["shared_error_artifact"]
            and rc["reading"]["cnfd_vs_cnfem_negative"] == dc["reading"]["cnfd_vs_cnfem_negative"]
            and rc["reading"]["same_stencil_family_positive"]
            == dc["reading"]["same_stencil_family_positive"])
        d["spread_rel"] = abs(rc["spread_relative"] - dc["spread_relative"]) / abs(dc["spread_relative"])
        ok = (all(v <= TOL["l2_rel"] for v in d["l2_rel"].values())
              and all(v["corr_abs"] <= TOL["corr_abs"] and v["sign_abs"] <= TOL["sign_abs"]
                      and v["ratio_rel"] <= TOL["ratio_rel"] for v in d["pairwise"].values())
              and d["spread_rel"] <= TOL["ratio_rel"] and d["reading_match"])
        d["pass"] = bool(ok)
        out["cases"].append(d)
    out["pass"] = all(c["pass"] for c in out["cases"])
    return out


def main() -> int:
    t0 = time.time()
    pins_before = measure_pins()
    mod, snap = load_frozen()
    declared_json = json.loads((REPO / "numerics/protocol/error_field_orthogonality_check.json").read_text())

    # declared regime, recomputed twice for determinism (P6)
    declared_runs = []
    for dr, dt in DECLARED_CASES:
        rec, fields = case_stats(mod, dr, dt)
        declared_runs.append({"rec": rec, "fields": fields})
    decl_repeat = [case_stats(mod, dr, dt) for dr, dt in DECLARED_CASES]
    p6_bitwise = all(
        all(bool(np.array_equal(rep_fields[s], declared_runs[i]["fields"][s])) for s in SCHEMES)
        for i, (_, rep_fields) in enumerate(decl_repeat))
    p6_stats = all(rep_rec == declared_runs[i]["rec"]
                   for i, (rep_rec, _) in enumerate(decl_repeat))

    recomputed_declared = [r["rec"] for r in declared_runs]
    comparison = compare_declared(recomputed_declared, declared_json)

    # certified regime extension (P4)
    certified = [case_stats(mod, dr, dt)[0] for dr, dt in CERTIFIED_CASES]

    # mechanism (P3) and negative control (P5)
    mech = symbol_fits()
    p3 = bool(abs(mech["fd_slope"] + 1 / 12) <= 1e-3 and abs(mech["fem_slope"] - 1 / 12) <= 1e-3)
    a = declared_runs[0]["fields"]["lffd"]
    plant = a * (1.0 + 1e-12 * np.cos(np.arange(len(a))))
    plant_stats = {"corr": corr(a, plant), "sign_agreement_mass_fraction": sign_agree(a, plant),
                   "self_corr": corr(a, a)}
    p5 = bool(plant_stats["corr"] > 0.999999 and plant_stats["sign_agreement_mass_fraction"] > 0.999
              and plant_stats["self_corr"] == 1.0)

    # prediction evaluation
    p1 = bool(comparison["pass"])
    p2 = bool(all(c["reading"]["cnfd_vs_cnfem_negative"]
                  and c["reading"]["same_stencil_family_positive"]
                  and not c["reading"]["shared_error_artifact"] for c in recomputed_declared))
    p4 = bool(all(c["pairwise"]["cnfd_vs_cnfem"]["corr"] < -0.9
                  and c["pairwise"]["cnfd_vs_cnfem"]["sign_agreement_mass_fraction"] < 0.01
                  and c["pairwise"]["lffd_vs_cnfd"]["corr"] > 0.99
                  and c["spread_relative"] < 0.01 for c in certified))
    p6 = bool(p6_bitwise and p6_stats)

    if not p1 or not p5:
        verdict = "FALSIFIED"
        headline = ("declared artifact not reproducible, or the detector does not separate a "
                    "planted shared field")
    elif not p4:
        verdict = "SHARED_ERROR_EXCLUSION_NOT_EXTENDED"
        headline = ("structure holds at dt=1e-3 but not at the certified dt=1e-4; the "
                    "'not a shared-error artifact' reading is a scope gap at the certified regime")
    elif p1 and p2 and p3 and p4 and p5 and p6:
        verdict = "REPRODUCED_AND_EXTENDED"
        headline = ("declared error-field check reproduced at dt=1e-3 and the same structure "
                    "holds at the certified fixed dt=1e-4 on dr=0.2/0.1/0.05; equal-magnitude "
                    "opposite-sign leading coefficients confirmed at -1/12 (FD) and +1/12 (PEM)")
    else:
        verdict = "PARTIAL"
        headline = "some predictions failed; see predictions block"

    pins_after = measure_pins()
    pins_stable = all(v["match"] for v in pins_after.values()) and pins_after == pins_before

    report = {
        "schema": "w012-n0-errfield-verify/v1",
        "task_id": "W012-GNUM-ERRFIELD-VERIFY-01",
        "script_revision": {
            "revision": 2,
            "note": ("rev1 is preserved at raw/report_rev1_p3_script_bug.json; rev1 failed P3 only "
                     "because the symbol fit double-divided by theta^2 (script defect, not an "
                     "artifact finding). P1/P2/P4/P5/P6 were already true in rev1."),
        },
        "actor": "worker-012",
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N0",
        "gate": "G-NUM",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "question": ("Does the N0 error-field orthogonality evidence reproduce, and does its "
                     "'not a shared-error artifact' reading hold at the certified fixed dt=1e-4?"),
        "target_artifact": "numerics/protocol/error_field_orthogonality_check.json#1b2d3162b0715d9b",
        "reviewed_hashes": {rel: v["measured"] for rel, v in pins_after.items()},
        "frozen_module_snapshot": str(snap.relative_to(REPO)),
        "pins_stable": bool(pins_stable),
        "pins_before": pins_before,
        "pins_after": pins_after,
        "predictions": {
            "P1_reproduction": {"pass": p1, "detail": comparison},
            "P2_declared_regime_structure": {
                "pass": p2,
                "detail": {f"dr={c['dr']}": {"corr_cnfd_cnfem": c["pairwise"]["cnfd_vs_cnfem"]["corr"],
                                             "corr_lffd_cnfd": c["pairwise"]["lffd_vs_cnfd"]["corr"],
                                             "sign_mass_cnfd_cnfem":
                                                 c["pairwise"]["cnfd_vs_cnfem"]["sign_agreement_mass_fraction"],
                                             "reading": c["reading"]} for c in recomputed_declared},
            },
            "P3_mechanism_symbol_slopes": {"pass": p3, "detail": mech},
            "P4_certified_regime_extension": {
                "pass": p4,
                "detail": {f"dr={c['dr']}": {"dt": c["dt"], "steps": c["steps"],
                                             "l2_error": c["l2_error"],
                                             "spread_relative": c["spread_relative"],
                                             "corr_cnfd_cnfem": c["pairwise"]["cnfd_vs_cnfem"]["corr"],
                                             "sign_mass_cnfd_cnfem":
                                                 c["pairwise"]["cnfd_vs_cnfem"]["sign_agreement_mass_fraction"],
                                             "corr_lffd_cnfd": c["pairwise"]["lffd_vs_cnfd"]["corr"],
                                             "reading": c["reading"]} for c in certified},
            },
            "P5_negative_control_planted_shared_field": {"pass": p5, "detail": plant_stats},
            "P6_determinism_bitwise": {"pass": p6, "detail": {"bitwise_equal": p6_bitwise,
                                                              "stats_equal": p6_stats}},
        },
        "recomputed_declared_cases": recomputed_declared,
        "certified_regime_cases": certified,
        "verdict": verdict,
        "headline": headline,
        "conclusion_type": "numerical_evidence",
        "not_claimed": [
            "no gate verdict, no node status, no validation_status=passed (worker events cannot move those)",
            "no disposition of the C8 protocol contest, no numerics_lock release",
            "no claim that the shared axes (psi=r*phi, Dirichlet box, Taylor start, pulse family) are independent",
            "no physics claim beyond the flat-space discretisation error structure",
            "the reviewed artifact was not edited; writes are confined to this artifact directory",
        ],
        "falsifier": [
            "any pinned path re-hashing before vs after (see pins_stable)",
            "a faithful rerun in which a declared dt=1e-3 value does not reproduce within the registered tolerances",
            "a rerun in which corr(cnfd, cnfem) >= -0.9, sign mass >= 0.01, or spread_relative >= 0.01 at fixed dt=1e-4 on dr=0.2/0.1/0.05",
            "a symbol-slope check leaving -1/12 (FD) or +1/12 (PEM) by more than 1e-3",
            "the planted shared-field control not being detected (vacuity)",
        ],
        "next_falsifier": ("recompute at fixed dt=1e-4 on the fourth rung dr=0.025 and at a second "
                           "pulse family; a shared-error field or a lost sign separation there voids "
                           "the certified-regime extension"),
        "runtime_seconds": round(time.time() - t0, 2),
        "provenance": {"python": platform.python_version(), "numpy": np.__version__,
                       "platform": platform.platform(),
                       "generator": "worker-012 (independent; declared generator not imported)"},
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "headline": headline,
                      "predictions": {k: v["pass"] for k, v in report["predictions"].items()},
                      "pins_stable": pins_stable,
                      "certified_dr_values": [c["dr"] for c in certified],
                      "runtime_seconds": report["runtime_seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
