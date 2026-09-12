#!/usr/bin/env python3
"""W081-N0-FDT-02: protocol-3.4-compliant fixed-dt certification candidate for N0.

Context (measured, not assumed)
  worker-067 (comms/outbox/worker-067.jsonl, 00:22:56) and worker-081
  (artifacts/worker-081/n0_c8_adjudication, 00:29) established that the filed 4-rung order
  evidence numerics/tests/n0_order_4rung.json#c88146a1375c50f0 uses dt = 0.5*dr on every row,
  while numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2 section 3.4 prescribes a constant small
  dt (1e-4) for spatial order and states dt ~ h runs must never be quoted as spatial.  The
  remedy (adjudication README, remedy item 1) is to file a fixed-dt study.  This script
  produces that study independently, at the pinned frozen module hash, and does not touch any
  canonical path.

Task
  task_id  : W081-N0-FDT-02
  node     : N0 (flat-space scalar-wave calibration)
  class    : AF-WCC-SCALAR-SPH
  gate     : G-NUM
  writer   : worker-081 (bounded instance worker-081-20260912T002948-968807)

Declared design (fixed BEFORE measuring; no decision rule is edited after seeing output)
  P  input pins re-measured; abort with verdict input_moved if any pinned hash differs.
  S  harness selftest (R.selftest) must pass; negative controls (R.controls) must all fire.
  A  study A: fixed dt = 1e-4, dr in {0.2, 0.1, 0.05, 0.025}, schemes lffd/cnfd/cnfem.
     This is the exact protocol section 3.4 spatial methodology.
  B  study B: fixed dt = 1e-3, same 4 rungs, same schemes (cheap candidate).
  C  control C: fixed dr in {0.05, 0.025} (the finest rung is the critical one, since the
     spatial error is smallest there), dt in {1e-3, 5e-4, 2.5e-4, 1e-4} per scheme.
     Rule: if every per-halving relative error change at dt <= 1e-3 is < 2 % (the canonical
     temporal-control threshold), dt = 1e-3 is temporally subdominant at that resolution.
  D  control D: fixed dr = 0.05, cfl in {0.5, 0.25, 0.125} per scheme.  This is the
     constant-CFL study family that the filed evidence uses; the prior adjudication measured
     > 2 % per-halving change there.  Expected: changes > 2 % (consistency check).  If D
     instead shows < 2 %, the prior F1' contamination finding is contradicted.
  V  verdict rule (worker-level only):
       A within-order  : all three schemes monotone and |fit - 2| <= 0.3 at dt = 1e-4, rungs 4.
       B admissible    : B likewise in band AND C says dt = 1e-3 subdominant for that scheme.
       D consistency   : D max per-halving change >= 2 % for at least lffd and cnfem
                         (the schemes with measured cancellation in the prior adjudication).
     Report per-scheme, no aggregate promotion, no gate verdict, no node completion.

Falsifier (binds this artifact)
  Re-measure numerics/CONVERGENCE_PROTOCOL.md: if its sha256 is not 1e6cdf04d7a24313, or
  numerics/tests/flat_wave_replication.py is not 8ade1cdc163ea420, this study does not bind.
  It is falsified if a rerun at the frozen module hash reports any scheme non-monotone or a
  dt = 1e-4 fit order outside 2.0 +/- 0.3, or if control C shows a >= 2 % relative error
  change between dt = 1e-3 and dt = 1e-4 at dr = 0.05 (then dt = 1e-3 is not subdominant and
  only the 1e-4 study may be quoted as spatial), or if control D shows < 2 % change (then the
  prior F1' finding would be contradicted).

Read-only contract
  Imports the frozen module; writes only OUTDIR (this directory).  sys.dont_write_bytecode.

Usage: python3 artifacts/worker-081/n0_fixed_dt_certification/run_fixed_dt_study.py
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "fixed_dt_study.json"
sys.path.insert(0, str(ROOT / "numerics" / "tests"))

PIN = {
    "numerics/CONVERGENCE_PROTOCOL.md": "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274",
    "numerics/tests/flat_wave_replication.py": "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422",
    "numerics/tests/n0_order_4rung.json": "c88146a1375c50f0c87d2893109087ee6f08c55919a4812dc073750bd86f544a",
    "numerics/tests/n0_gate_proposal.json": "58a175b52fbe4f9b38663dcdfd57342629c99c04b34c76295affcd567acdf4c7",
    "numerics/tests/flat_wave.py": "8b52014dac47f99663c8bf46fb2e65a80db399860d586d63cd73dd1db1454a6c",
}
DR4 = [0.2, 0.1, 0.05, 0.025]
SCHEMES = ("lffd", "cnfd", "cnfem")
P_EXPECTED, P_TOL = 2.0, 0.3
SUBDOMINANCE_LIMIT = 0.02  # canonical temporal-control threshold, relative change per halving
TASK = {
    "task_id": "W081-N0-FDT-02",
    "node_id": "N0",
    "class_id": "AF-WCC-SCALAR-SPH",
    "gate": "G-NUM",
    "actor": "worker-081",
    "instance": "worker-081-20260912T002948-968807",
    "kind": "numerical_evidence",
}


def sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fit_stats(rows):
    import numpy as np

    drs = [r["dr"] for r in rows]
    errs = [r["l2_error"] for r in rows]
    x, y = np.log(np.asarray(drs, float)), np.log(np.asarray(errs, float))
    slope, cov = np.polyfit(x, y, 1, cov=True)
    se = float(math.sqrt(float(cov[0, 0])))
    pairs = [float(math.log(errs[i] / errs[i + 1]) / math.log(drs[i] / drs[i + 1]))
             for i in range(len(errs) - 1)]
    half_range = (max(pairs) - min(pairs)) / 2.0
    return {
        "fit_order": float(slope[0]),
        "least_squares_se": se,
        "pair_orders": pairs,
        "pair_half_range": float(half_range),
        "delta": float(max(se, half_range)),
        "monotone": all(errs[i + 1] < errs[i] for i in range(len(errs) - 1)),
        "within_harness_tol": bool(abs(float(slope[0]) - P_EXPECTED) <= P_TOL),
    }


def one_rung(R, scheme, dr, dt):
    t0 = time.time()
    res = R.order_study(scheme, dr_values=[dr], dt_rule=lambda h, dt=dt: dt)
    row = res["rows"][0]
    return {
        "dr": row["dr"],
        "dt": row["dt"],
        "cfl": row["cfl"],
        "steps": row["steps"],
        "l2_error": row["l2_error"],
        "l2_error_u": row["l2_error_u"],
        "final_t": row["final_t"],
        "runtime_s": round(time.time() - t0, 3),
    }


def fixed_dt_study(R, dt):
    out = {}
    for scheme in SCHEMES:
        t0 = time.time()
        res = R.order_study(scheme, dr_values=DR4, dt_rule=lambda h, dt=dt: dt)
        stats = fit_stats(res["rows"])
        out[scheme] = {
            **stats,
            "rows": [{k: row[k] for k in ("dr", "dt", "cfl", "steps", "l2_error", "l2_error_u", "final_t")}
                     for row in res["rows"]],
            "runtime_s": round(time.time() - t0, 3),
        }
    return out


def dt_refinement(R, dr, dts):
    out = {}
    for scheme in SCHEMES:
        rows = [one_rung(R, scheme, dr, dt) for dt in dts]
        rel = [abs(rows[i + 1]["l2_error"] - rows[i]["l2_error"]) / abs(rows[i]["l2_error"])
               for i in range(len(rows) - 1)]
        out[scheme] = {
            "rows": rows,
            "rel_change_per_halving": rel,
            "max_rel_change": float(max(rel)),
            "rel_change_1e-3_to_5e-4": float(rel[0]) if rel else None,
            "subdominant_at_1e-3": bool(all(r < SUBDOMINANCE_LIMIT for r in rel)) if rel else None,
        }
    return out


def main() -> int:
    started = time.time()
    report = {
        "schema": "worker-081/n0-fixed-dt-study/v1",
        **TASK,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "host": {"python": sys.version.split()[0], "platform": platform.platform()},
        "purpose": ("Produce the section-3.4-compliant constant-dt order study that the filed "
                    "certified evidence lacks; candidate replacement evidence for N0/G-NUM. "
                    "Not a gate verdict, not a node completion, not an edit of the certified claim."),
        "design": {
            "study_A_fixed_dt": 1e-4,
            "study_B_fixed_dt": 1e-3,
            "dr_values": DR4,
            "schemes": list(SCHEMES),
            "control_C": {"fixed_dr": [0.05, 0.025], "dt": [1e-3, 5e-4, 2.5e-4, 1e-4],
                          "rule": f"subdominant at 1e-3 iff every per-halving relative change < {SUBDOMINANCE_LIMIT}"},
            "control_D": {"fixed_dr": 0.05, "cfl": [0.5, 0.25, 0.125],
                          "rule": "expected >= 2% change per halving (mixed-order contamination)"},
            "order_band": [P_EXPECTED - P_TOL, P_EXPECTED + P_TOL],
            "declared_before_measurement": True,
        },
    }

    # ---- P: pins (start) -------------------------------------------------
    report["input_pins_start"] = {
        rel: {"sha256": h, "expected": exp, "match": (exp is None or h == exp)}
        for rel, exp in PIN.items() for h in [sha256(ROOT / rel)]
    }
    moved = [rel for rel, v in report["input_pins_start"].items() if not v["match"]]
    report["input_pins_start_ok"] = not moved
    if moved:
        report["verdict"] = {"status": "input_moved", "moved": moved,
                             "note": "aborted before measurement; study does not bind"}
        OUT.write_text(json.dumps(report, indent=1, sort_keys=True))
        print("ABORT: pinned inputs moved:", moved)
        return 3

    import flat_wave_replication as R  # noqa: E402

    # ---- S: harness validation ------------------------------------------
    st = R.selftest(verbose=False)
    report["selftest"] = {"pass": bool(st["pass"]), "checks": st["checks"]}
    ct = R.controls()
    neg_ok = bool(
        ct["frozen_state"]["rejected_by_order_gate"]
        and ct["wrong_sign_operator"]["rejected_by_stability"]
        and ct["dt_probe_dt_eq_dr_pow_half"]["order_drops_below_2"]
    )
    report["negative_controls"] = ct
    report["negative_controls_ok"] = neg_ok

    # ---- A/B: fixed-dt four-rung studies --------------------------------
    report["study_A_fixed_dt_1e-4"] = fixed_dt_study(R, 1e-4)
    report["study_B_fixed_dt_1e-3"] = fixed_dt_study(R, 1e-3)

    # ---- C/D: fixed-dr refinements --------------------------------------
    report["control_C_dr0.05"] = dt_refinement(R, 0.05, [1e-3, 5e-4, 2.5e-4, 1e-4])
    report["control_C_dr0.025"] = dt_refinement(R, 0.025, [1e-3, 5e-4, 2.5e-4, 1e-4])
    report["control_D_constant_cfl_refinement_dr0.05"] = dt_refinement(R, 0.05, [0.5 * 0.05, 0.25 * 0.05, 0.125 * 0.05])

    # ---- comparison against the filed constant-CFL evidence -------------
    filed = json.loads((ROOT / "numerics/tests/n0_order_4rung.json").read_text())
    filed_err = {}
    for study in filed["studies"]:
        row = next(r for r in study["rows"] if abs(r["dr"] - 0.05) < 1e-12)
        filed_err[study["scheme"]] = {"dr": 0.05, "dt": row["dt"], "cfl": row["cfl"], "l2_error": row["l2_error"]}
    report["filed_cfl0.5_at_dr0.05"] = filed_err
    report["fixed_dt_vs_filed_at_dr0.05"] = {
        s: {
            "filed_cfl0.5_error": filed_err[s]["l2_error"],
            "fixed_dt_1e-4_error": report["study_A_fixed_dt_1e-4"][s]["rows"][-1]["l2_error"]
            if report["study_A_fixed_dt_1e-4"][s]["rows"][-1]["dr"] == 0.05
            else next(r["l2_error"] for r in report["study_A_fixed_dt_1e-4"][s]["rows"] if r["dr"] == 0.05),
            "fixed_dt_1e-3_error": next(r["l2_error"] for r in report["study_B_fixed_dt_1e-3"][s]["rows"] if r["dr"] == 0.05),
        }
        for s in SCHEMES
    }
    for s in SCHEMES:
        d = report["fixed_dt_vs_filed_at_dr0.05"][s]
        d["ratio_filed_over_fixed_1e-4"] = d["filed_cfl0.5_error"] / d["fixed_dt_1e-4_error"]
        d["ratio_filed_over_fixed_1e-3"] = d["filed_cfl0.5_error"] / d["fixed_dt_1e-3_error"]

    # ---- V: verdict rule ------------------------------------------------
    per_scheme = {}
    for s in SCHEMES:
        a, b = report["study_A_fixed_dt_1e-4"][s], report["study_B_fixed_dt_1e-3"][s]
        c05, c025 = report["control_C_dr0.05"][s], report["control_C_dr0.025"][s]
        d = report["control_D_constant_cfl_refinement_dr0.05"][s]
        c_sub = bool(c05["subdominant_at_1e-3"] and c025["subdominant_at_1e-3"])
        per_scheme[s] = {
            "A_in_band": bool(a["within_harness_tol"] and a["monotone"]),
            "A_fit_order": a["fit_order"],
            "B_in_band": bool(b["within_harness_tol"] and b["monotone"]),
            "B_fit_order": b["fit_order"],
            "B_admissible_1e-3": bool(b["within_harness_tol"] and b["monotone"] and c_sub),
            "C_subdominant_at_1e-3": c_sub,
            "C_dr0.05_max_rel_change": c05["max_rel_change"],
            "C_dr0.025_max_rel_change": c025["max_rel_change"],
            "C_max_rel_change": max(c05["max_rel_change"], c025["max_rel_change"]),
            "D_max_rel_change": d["max_rel_change"],
            "D_contaminated": bool(d["max_rel_change"] >= SUBDOMINANCE_LIMIT),
        }
    report["per_scheme"] = per_scheme
    report["verdict"] = {
        "status": "measured",
        "A_order2_confirmed_all_schemes": all(per_scheme[s]["A_in_band"] for s in SCHEMES),
        "dt_1e-3_admissible_all_schemes": all(per_scheme[s]["B_admissible_1e-3"] for s in SCHEMES),
        "D_contamination_consistent": all(per_scheme[s]["D_contaminated"] for s in ("lffd", "cnfem")),
        "selftest_pass": bool(st["pass"]),
        "negative_controls_ok": neg_ok,
        "scope": ("worker-level numerical evidence for N0/G-NUM; does not replace, re-pin or "
                  "invalidate the certified claim's existing evidence refs, which still point at "
                  "the cfl=0.5 study; no gate verdict, no node completion, numerics_lock untouched"),
    }
    report["verdict"]["all_required_checks_pass"] = bool(
        report["verdict"]["A_order2_confirmed_all_schemes"]
        and report["verdict"]["D_contamination_consistent"]
        and report["verdict"]["selftest_pass"]
        and report["verdict"]["negative_controls_ok"]
    )

    # ---- pins (end): detect concurrent mutation during the run ----------
    report["input_pins_end"] = {rel: sha256(ROOT / rel) for rel in PIN}
    report["input_pins_end_ok"] = all(report["input_pins_end"][rel] == v["sha256"]
                                      for rel, v in report["input_pins_start"].items())
    report["runtime_s"] = round(time.time() - started, 1)
    OUT.write_text(json.dumps(report, indent=1, sort_keys=True))

    print(f"verdict: order2_A={report['verdict']['A_order2_confirmed_all_schemes']} "
          f"dt1e-3_admissible={report['verdict']['dt_1e-3_admissible_all_schemes']} "
          f"D_consistent={report['verdict']['D_contamination_consistent']} "
          f"selftest={st['pass']} negctl={neg_ok} pins_end={report['input_pins_end_ok']} "
          f"runtime={report['runtime_s']}s")
    for s in SCHEMES:
        print(f"  {s}: A fit={per_scheme[s]['A_fit_order']:.4f} B fit={per_scheme[s]['B_fit_order']:.4f} "
              f"C sub@1e-3={per_scheme[s]['C_subdominant_at_1e-3']} Dmax={per_scheme[s]['D_max_rel_change']:.4f}")
    return 0 if report["verdict"]["all_required_checks_pass"] and report["input_pins_end_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
