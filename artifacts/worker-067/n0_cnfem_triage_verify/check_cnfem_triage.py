#!/usr/bin/env python3
"""W067-N0-CNFEM-TRIAGE-VERIFY-01.

Independent, read-only verification of the open G-NUM unmet item
    "cnfem triage from the N0 adjudication is not closed: fix with root cause,
     or exclude with evidence"
against the bytes on disk at the time of this run.

Class: AF-WCC-SCALAR-SPH.  Node: N0.  Gate: G-NUM.  numerics_lock respected:
no canonical file is written, no N1/self-gravity work, no gate verdict.

What this checker measures (all from live bytes, nothing taken from prose):
  M1  hash binding of the five pinned inputs; abort (exit 2) on any drift.
  M2  the pre-fix recurrence constructed independently here
        (M + cK) psi^{n+1} = 2 M psi^n - (M - cK) psi^{n-1}
      is run through the published harness driver: order and amplitude growth.
  M3  the live (fixed) module's cnfem order study and invariant study re-run.
  M4  the live JSON's published cnfem numbers are compared to M2/M3.
  M5  static doc-consistency: does the live CrankNicolsonFEM docstring document
      the pre-fix recurrence while the implementation uses the fixed one?

Controls are fail-closed: any False -> verdict CONTROL_FAILURE, exit 2.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
ART = Path(__file__).resolve().parent
MOD_PATH = ROOT / "numerics" / "tests" / "flat_wave_replication.py"
JSON_PATH = ROOT / "numerics" / "results" / "flat_wave_replication.json"
TRIAGE_PATH = ROOT / "numerics" / "tests" / "replication_triage.md"
ADJ_PATH = ROOT / "runtime" / "state" / "controller_verification" / "N0_adjudication.md"
DISP_PATH = ROOT / "numerics" / "protocol" / "format_conditions_disposition.json"
PREV_VERDICT = ROOT / "numerics" / "protocol" / "fixed_replication_verdict.json"
TAXONOMY = ROOT / "research_map" / "formulation_taxonomy.yaml"

PINS = {
    str(MOD_PATH.relative_to(ROOT)): "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422",
    str(JSON_PATH.relative_to(ROOT)): "298a4d921c2264e6ef305274592dba62b2d3ef4bee456d56844d74bf0369fd33",
    str(TRIAGE_PATH.relative_to(ROOT)): "f27a253ec928bc09e8e786cfbfd87626102cae6b2641ec5d81ff01c209748792",
    str(DISP_PATH.relative_to(ROOT)): "e7c05ff33fe2bfab3f815a7e0ff601a6e0cdf9600ce7231ec61b262f60857cbf",
}
ANCHORS = {
    str(ADJ_PATH.relative_to(ROOT)): "003baf8b31d990eee631c2ed98198b90d9c65ecfd71880d7c364940c6151a481",
    str(PREV_VERDICT.relative_to(ROOT)): "dcad962324e3be156d1ef1577b7ee2613fac803058351b643d2c8f67bc787a36",
    str(TAXONOMY.relative_to(ROOT)): "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
}
PUB = {
    "order_fit": 1.9863235066828981,
    "own_drift": 2.0438718559608235e-14,
    "harness_drift": 8.481868011635823e-09,
    "lf_order": 1.9957695044715191,
    "cnfd_order": 1.9934777747080437,
    "triage_wrong_order": -0.0773,
}
TOL = 1e-9


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module():
    spec = importlib.util.spec_from_file_location("flat_wave_replication_pinned", MOD_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def order_for(mod, factory, drs, cfl=0.5, r_max=30.0, t_end=6.0):
    pulse = mod.PulseExact()
    rows = []
    for dr in drs:
        case = mod.run_case(factory, dr, cfl, r_max, t_end)
        err = mod.l2_error(case["psi"][-1], pulse.psi(case["r"], case["t"][-1]), dr)
        amp0 = float(np.max(np.abs(case["psi"][0])))
        amp = max(float(np.max(np.abs(s))) for s in case["psi"])
        rows.append({"dr": dr, "dt": case["dt"], "steps": case["steps"],
                     "l2_error": err, "amp0": amp0, "amp_max": amp,
                     "amp_growth": amp / max(amp0, 1e-300)})
    errs = [r["l2_error"] for r in rows]
    return {"rows": rows, "fit_order": mod.fit_order(drs, errs),
            "pair_orders": mod.pair_orders(drs, errs),
            "monotone": all(errs[i + 1] < errs[i] for i in range(len(errs) - 1))}


def main() -> int:
    ctl: dict[str, bool] = {}
    detail: dict[str, object] = {}

    # ---- M1: hash binding (fail-closed before any numerical work) ----
    live: dict[str, str] = {}
    for rel, expect in {**PINS, **ANCHORS}.items():
        p = ROOT / rel
        live[rel] = sha256(p) if p.exists() else "MISSING"
    drift = {k: {"expected": v, "measured": live[k]} for k, v in {**PINS, **ANCHORS}.items()
             if live[k] != v}
    ctl["C6_pins_match"] = not drift
    detail["pin_drift"] = drift
    if drift:
        ledger = {"verdict": "CONTROL_FAILURE", "controls": ctl, "detail": detail,
                  "note": "refusing numerical work: a pinned input drifted"}
        (ART / "ledger.json").write_text(json.dumps(ledger, indent=1, sort_keys=True))
        print(json.dumps(ledger, indent=1, sort_keys=True))
        return 2

    mod = load_module()
    before = {rel: sha256(ROOT / rel) for rel in {**PINS, **ANCHORS}}

    # ---- C1: published self-test as the module's own integrity floor ----
    st = mod.selftest(verbose=False)
    ctl["C1_selftest"] = bool(st.get("pass"))
    detail["selftest"] = st

    pulse = mod.PulseExact()
    drs = list(mod.HARNESS_CONFIG["dr_values"])

    # ---- M2: independent construction of the pre-fix recurrence ----
    class WrongRHSFEM(mod.CrankNicolsonFEM):
        """Live-fixed left side, pre-fix right side: 2M psi^n - (M - cK) psi^{n-1}."""

        def __init__(self, r, dt, psi0, psi_t0, psi_tt0):
            super().__init__(r, dt, psi0, psi_t0, psi_tt0)
            h = self.dr
            c = 0.5 * dt ** 2
            m = len(r) - 2
            self.B_wrong = mod.Tridiagonal(h / 6.0 + c / h, 2.0 * h / 3.0 - 2.0 * c / h,
                                           h / 6.0 + c / h, m)

        def step(self):
            if not self._started:
                self.psi_prev, self.psi, self._started = self.psi, self.psi1, True
                self.t += self.dt
                return
            rhs = 2.0 * self.M.matvec(self.psi[1:-1]) - self.B_wrong.matvec(self.psi_prev[1:-1])
            nxt = np.zeros_like(self.psi)
            nxt[1:-1] = self.B.solve(rhs)
            self.psi_prev, self.psi = self.psi, nxt
            self.t += self.dt
            if not np.all(np.isfinite(nxt)):
                raise FloatingPointError("non-finite state in WrongRHSFEM")

    def wrong_factory(r, dt):
        psi0, pt0, ptt0 = pulse.initial_data(r)
        return WrongRHSFEM(r, dt, psi0, pt0, ptt0)

    wrong = order_for(mod, wrong_factory, drs)
    detail["wrong_recurrence"] = wrong

    # ---- M3: live fixed module re-run ----
    fixed = mod.order_study("cnfem")
    fixed2 = mod.order_study("cnfem")  # C7 determinism
    inv_cnfem = mod.invariant_study("cnfem", dr=0.05)
    inv_cnfd = mod.invariant_study("cnfd", dr=0.05)
    lf = mod.order_study("lffd")
    detail["fixed_cnfem_order"] = {"fit_order": fixed["fit_order"],
                                   "pair_orders": fixed["pair_orders"],
                                   "monotone": fixed["monotone"],
                                   "rows": fixed["rows"]}
    detail["invariants"] = {"cnfem": inv_cnfem, "cnfd": inv_cnfd}
    detail["reference_lffd_order"] = lf["fit_order"]

    # ---- M4: comparison with the published JSON ----
    published = json.loads(JSON_PATH.read_text())
    pub_j = None
    for o in published["order_studies"]:
        if o["scheme"] == "cnfem":
            pub_j = o
    cmp = {
        "order_fit": {"published": PUB["order_fit"], "measured": fixed["fit_order"],
                      "abs_delta": abs(fixed["fit_order"] - PUB["order_fit"])},
        "own_drift": {"published": PUB["own_drift"], "measured": inv_cnfem["own_energy_drift"],
                      "rel_delta": abs(inv_cnfem["own_energy_drift"] - PUB["own_drift"]) / PUB["own_drift"]},
        "harness_drift": {"published": PUB["harness_drift"],
                          "measured": inv_cnfem["harness_leapfrog_energy_drift"],
                          "rel_delta": abs(inv_cnfem["harness_leapfrog_energy_drift"] - PUB["harness_drift"]) / PUB["harness_drift"]},
        "json_self_rows_match_rerun": bool(pub_j) and all(
            abs(a["l2_error"] - b["l2_error"]) < TOL * max(1.0, abs(a["l2_error"]))
            for a, b in zip(pub_j["rows"], fixed["rows"])),
    }
    detail["published_cross_check"] = cmp

    # ---- M5: doc-consistency of the live class ----
    src = MOD_PATH.read_text()
    cls_block = src.split("class CrankNicolsonFEM", 1)[1].split("def step", 1)[0]
    doc_wrong = "(M - c K) psi^{n-1}" in cls_block
    impl_fixed = "self.B = Tridiagonal(h / 6.0 - c / h" in src
    both_sides_same_B = "rhs = 2.0 * self.M.matvec(self.psi[1:-1]) - self.B.matvec(self.psi_prev[1:-1])" in src
    detail["doc_consistency"] = {
        "class_docstring_has_prefix_recurrence": doc_wrong,
        "implementation_assembles_fixed_B": impl_fixed,
        "step_uses_same_B_both_sides": both_sides_same_B,
        "synthetic_positive_control_detects_wrong_doc": ("(M - c K) psi^{n-1}" in
                                                         "doc (M + c K) psi^{n+1} = 2 M psi^n - (M - c K) psi^{n-1} end"),
    }

    # ---- controls (fail-closed) ----
    ctl["C2_root_cause_discriminates"] = (
        wrong["fit_order"] < 0.5 and fixed["fit_order"] > 1.5) and wrong["fit_order"] < fixed["fit_order"] - 1.0
    ctl["C2b_prefix_growth"] = wrong["rows"][0]["amp_growth"] > 1.5
    ctl["C3_own_invariants_exact"] = (
        inv_cnfem["own_energy_drift"] is not None and inv_cnfem["own_energy_drift"] < 1e-12
        and inv_cnfd["own_energy_drift"] is not None and inv_cnfd["own_energy_drift"] < 1e-12)
    ctl["C4_harness_gate_passes_below_tol"] = (
        inv_cnfem["harness_gate_would_pass"]
        and inv_cnfem["harness_leapfrog_energy_drift"] <= inv_cnfem["harness_drift_tol"])
    ctl["C5_published_numbers_match"] = (
        cmp["order_fit"]["abs_delta"] < 1e-9
        and cmp["own_drift"]["rel_delta"] < 1e-2
        and cmp["harness_drift"]["rel_delta"] < 1e-2
        and cmp["json_self_rows_match_rerun"])
    ctl["C7_determinism"] = (abs(fixed["fit_order"] - fixed2["fit_order"]) == 0.0)
    ctl["C8_doc_mismatch_detected"] = bool(
        doc_wrong and impl_fixed and both_sides_same_B
        and detail["doc_consistency"]["synthetic_positive_control_detects_wrong_doc"])
    after = {rel: sha256(ROOT / rel) for rel in {**PINS, **ANCHORS}}
    ctl["C9_read_only_no_canonical_drift"] = before == after and before == live

    all_pass = all(ctl.values())
    verdict = ("CNFEM_ROOT_CAUSE_AND_FIX_REPRODUCED_WITH_DOCSTRING_DEFECT"
               if all_pass else "CONTROL_FAILURE")

    ledger = {
        "schema": "worker-067-cnfem-triage-verification/v1",
        "task_id": "W067-N0-CNFEM-TRIAGE-VERIFY-01",
        "worker": "worker-067",
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N0",
        "gate": "G-NUM",
        "created_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        "verdict": verdict,
        "controls": ctl,
        "controls_passed": f"{sum(1 for v in ctl.values() if v)}/{len(ctl)}",
        "findings": {
            "F1_root_cause_confirmed": (
                "The pre-fix recurrence independently constructed here -- (M + cK) psi^{n+1} = "
                "2M psi^n - (M - cK) psi^{n-1} -- measured fit_order "
                f"{wrong['fit_order']:.4f} (triage: {PUB['triage_wrong_order']}) with amplitude growth "
                f"{wrong['rows'][0]['amp_growth']:.3f} at dr=0.2, while the live fixed recurrence measures "
                f"{fixed['fit_order']:.4f}. Sign error in the CN/FEM right-hand side is the root cause, as claimed."),
            "F2_docstring_still_documents_the_bug": (
                "The live CrankNicolsonFEM docstring (numerics/tests/flat_wave_replication.py line 305) still "
                "states the pre-fix recurrence '(M + c K) psi^{n+1} = 2 M psi^n - (M - c K) psi^{n-1}', while "
                "the implementation assembles one B = M + cK and uses it on both sides (lines 315-318, 329). "
                "The code is correct; the method description is the bug. A reader who implements the docstring "
                "reintroduces the defect. Non-blocking for the numbers; not recorded in the triage or the "
                "disposition artifact."),
            "F3_published_numbers_reproduced": (
                f"cnfem order {fixed['fit_order']!r} vs published {PUB['order_fit']!r} (|delta| "
                f"{cmp['order_fit']['abs_delta']:.2e}); own-energy drift {inv_cnfem['own_energy_drift']:.3e} "
                f"vs published {PUB['own_drift']:.3e}; harness drift "
                f"{inv_cnfem['harness_leapfrog_energy_drift']:.3e} vs published {PUB['harness_drift']:.3e} "
                f"(tol {inv_cnfem['harness_drift_tol']})."),
            "F4_scope": (
                "Verification of an on-disk claim only: root cause, fix, and published numbers. It does not "
                "close the G-NUM gate, does not accept the triage, does not repair the docstring (a canonical "
                "write would move hash 8ade1cdc, which is pinned by the triage, the disposition artifact and "
                "the chained verdict), and does not re-litigate the separate live finding that "
                "fixed_replication_verdict.json dcad962324e3 still declares a contradicted taxonomy pin."),
        },
        "recommended_minimal_action": (
            "Record an erratum note against numerics/tests/flat_wave_replication.py line 305 in the triage's "
            "or protocol's provenance set (owner lead-numerics); repair the docstring only together with "
            "re-pinning every dependent hash (triage pin f27a253ec928, disposition e7c05ff33fe2, chained "
            "verdict dcad962324e3), since the lock forbids unhashed canonical edits."),
        "published_cross_check": cmp,
        "wrong_recurrence": wrong,
        "fixed_cnfem": detail["fixed_cnfem_order"],
        "invariants": detail["invariants"],
        "reference_lffd_order": lf["fit_order"],
        "doc_consistency": detail["doc_consistency"],
        "pins": {**PINS, **ANCHORS},
        "anchor_stability_before_after": before == after,
        "canonical_writes": 0,
        "next_falsifier": (
            "Withdrawn if any of: (a) the wrong-RHS variant constructed here measures order >= 0.5 or no "
            "amplitude growth at dr=0.2; (b) the live cnfem order study leaves the harness band or its "
            "own-energy drift exceeds 1e-12; (c) the published JSON's cnfem rows disagree with a re-run at "
            "hash 8ade1cdc; (d) numerics/tests/flat_wave_replication.py no longer hashes to 8ade1cdc (then "
            "these measurements are void by hash and no claim transfers to the new revision); (e) the "
            "docstring no longer contains the pre-fix recurrence, which voids F2 only."),
    }
    (ART / "ledger.json").write_text(json.dumps(ledger, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "controls": ctl,
                      "wrong_order": wrong["fit_order"], "fixed_order": fixed["fit_order"],
                      "doc_wrong": doc_wrong}, indent=1, sort_keys=True))
    return 0 if all_pass else 2


if __name__ == "__main__":
    sys.exit(main())
