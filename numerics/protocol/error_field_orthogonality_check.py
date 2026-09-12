#!/usr/bin/env python3
"""Lead control: are the cross-scheme error fields independent truncation errors,
or one shared error seen three times?

WHY THIS EXISTS
  numerics/protocol/temporal_subdominance_control.json measures a fixed-dt spatial plateau at
  dr=0.2 of 6.6547e-3 (lffd), 6.6552e-3 (cnfd), 6.6562e-3 (cnfem) -- three different spatial
  discretisations agreeing to 4 significant figures.  That is either a textbook coincidence of
  leading truncation coefficients (the 3-point central-difference phase error is
  -1/12 (kh)^2, the P1 consistent-mass FEM phase error is +1/12 (kh)^2: equal magnitude,
  OPPOSITE sign) or a shared error on one of the axes this replication does not vary
  (psi = r*phi reduction, Dirichlet box, Taylor start, Gaussian-pulse family, exact-solution
  formula).  The proposal explicitly does not claim those axes are independent, so this is a
  live falsifier and it is cheap to settle.

TEST
  At fixed dr and small dt, form the pointwise error field e_i = psi_num(r_i) - psi_exact(r_i)
  for each scheme.  Then:
    * corr(e_cnfd, e_cnfem)  -- if the FEM/FD phase errors are genuinely opposite, this is
      strongly NEGATIVE; a shared error would make it strongly POSITIVE.
    * corr(e_lffd, e_cnfd)  -- same spatial stencil + different time integrator: expected
      strongly POSITIVE and near 1 (they share spatial truncation by construction).
    * ||e|| ratio and the sign of the dominant projection.
  A shared-error artifact would show all pairs strongly positive with near-identical fields.

  This measures a STRUCTURE, not a pass/fail gate: it either supports "each scheme's own
  truncation error" or it falsifies the independence story and must be reported as a blocker.

FROZEN-MODULE GUARD: read-only import; sha256 must equal the pinned 8ade1cdc...
NOT CLAIMED: no gate verdict, no node completion, no self-gravity, no physics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
FROZEN = REPO / "numerics" / "tests" / "flat_wave_replication.py"
FROZEN_SHA = "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422"
CASES = [(0.2, 1e-3), (0.1, 1e-3)]
R_MAX, T_END, CFL = 30.0, 6.0, 0.5


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args(argv)

    measured = sha256_file(FROZEN)
    if measured != FROZEN_SHA:
        print(json.dumps({"error": "frozen module hash mismatch", "measured": measured}))
        return 2

    sys.path.insert(0, str(FROZEN.parent))
    import flat_wave_replication as mod  # noqa: E402

    out = {
        "artifact": "numerics/protocol/error_field_orthogonality_check.py",
        "schema": "n0-error-field-structure/v1",
        "purpose": ("Distinguish each scheme's own truncation error from a shared-error "
                    "artifact, given near-identical fixed-dt plateaus across schemes."),
        "assignment_context": ["astra-indep-1-N0-numerics", "astra-life01-n0-proposal"],
        "node_id": "N0", "gate": "G-NUM", "class_id": "AF-WCC-SCALAR-SPH",
        "conclusion_type": "numerical_evidence",
        "expected_leading_coefficients": {
            "central_3pt_fd": "-1/12 (kh)^2  (lffd, cnfd)",
            "p1_consistent_mass_fem": "+1/12 (kh)^2  (cnfem)",
            "prediction": "equal magnitude, opposite sign -> negative corr(cnfd, cnfem)",
        },
        "frozen_module": {"path": "numerics/tests/flat_wave_replication.py",
                          "sha256": measured, "hash_guard_passed": True},
        "cases": [],
        "not_claimed": ["no gate verdict", "no node completion", "no physics claim",
                        "no claim the shared axes are independent"],
    }

    t0 = time.time()
    for dr, dt in CASES:
        pulse = mod.PulseExact()
        fields, errs = {}, {}
        for scheme in ("lffd", "cnfd", "cnfem"):
            study = mod.order_study(scheme, dr_values=[dr], cfl=CFL, r_max=R_MAX,
                                    t_end=T_END, dt_rule=lambda d, dt=dt: dt)
            case = mod.run_case(mod.make_factory(scheme, pulse=pulse), dr, dt / dr,
                                R_MAX, T_END)
            r = case["r"]
            exact = pulse.psi(r, case["t"][-1])
            e = case["psi"][-1] - exact
            fields[scheme] = e
            errs[scheme] = float(np.sqrt(np.sum(e * e) * dr))

        def corr(a, b):
            a = a - a.mean()
            b = b - b.mean()
            den = float(np.sqrt(np.sum(a * a) * np.sum(b * b)))
            return float(np.sum(a * b) / den) if den > 0 else float("nan")

        # dominant-sign agreement: fraction of |error| mass where the two fields share sign
        def sign_agree(a, b):
            w = np.abs(a) + np.abs(b)
            tot = float(np.sum(w))
            if tot == 0:
                return float("nan")
            return float(np.sum(w[np.sign(a) == np.sign(b)]) / tot)

        rec = {
            "dr": dr, "dt": dt,
            "l2_error": errs,
            "spread_relative": float((max(errs.values()) - min(errs.values())) / np.mean(list(errs.values()))),
            "pairwise": {},
        }
        for a, b in (("lffd", "cnfd"), ("cnfd", "cnfem"), ("lffd", "cnfem")):
            rec["pairwise"][f"{a}_vs_{b}"] = {
                "corr": corr(fields[a], fields[b]),
                "sign_agreement_mass_fraction": sign_agree(fields[a], fields[b]),
                "norm_ratio": float(errs[a] / errs[b]),
            }
        # verdict for this case
        c_fd_fem = rec["pairwise"]["cnfd_vs_cnfem"]["corr"]
        c_fd_fd = rec["pairwise"]["lffd_vs_cnfd"]["corr"]
        rec["reading"] = {
            "cnfd_vs_cnfem_negative": bool(c_fd_fem < -0.5),
            "same_stencil_family_positive": bool(c_fd_fd > 0.9),
            "shared_error_artifact": bool(c_fd_fem > 0.5),
        }
        out["cases"].append(rec)

    out["conclusion"] = (
        "each scheme's own truncation error dominates the plateau (FD-family phase error is "
        "-1/12(kh)^2, P1-FEM is +1/12(kh)^2: equal magnitude, opposite sign)"
        if all(c["reading"]["cnfd_vs_cnfem_negative"] and not c["reading"]["shared_error_artifact"]
               for c in out["cases"])
        else "SHARED-ERROR ARTIFACT SUSPECTED: report as a blocker, do not certify cross-scheme independence"
    )
    out["runtime_seconds"] = round(time.time() - t0, 2)
    out["provenance"] = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                         "generator": "astra-lead-numerics (lead control, read-only frozen import)",
                         "python": platform.python_version(), "numpy": np.__version__,
                         "platform": platform.platform()}

    text = json.dumps(out, indent=2, sort_keys=True)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n")
    print(json.dumps({
        "conclusion": out["conclusion"],
        "cases": [{"dr": c["dr"],
                   "corr_cnfd_cnfem": c["pairwise"]["cnfd_vs_cnfem"]["corr"],
                   "corr_lffd_cnfd": c["pairwise"]["lffd_vs_cnfd"]["corr"],
                   "corr_lffd_cnfem": c["pairwise"]["lffd_vs_cnfem"]["corr"],
                   "l2": c["l2_error"]} for c in out["cases"]],
        "runtime_seconds": out["runtime_seconds"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
