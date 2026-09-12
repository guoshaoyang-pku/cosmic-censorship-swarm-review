#!/usr/bin/env python3
"""Self-tests for the N0 acceptance harness.

The requirement this file enforces is the project's own rule: a verifier must be
null-controlled.  Every gate gets a deliberately defective solver that it has to
reject, missing evidence must yield INCONCLUSIVE, and the whole report must be
bit-for-bit reproducible.  Run with::

    python3 test_harness.py -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

from harness import (  # noqa: E402
    DEFAULT_CONFIG,
    discrete_energy,
    evaluate,
    fit_order,
    grid,
)
from reference_solutions import GaussianPulse, phi_from_psi, standing_psi  # noqa: E402
from run_harness import CONTROL_EXPECTATIONS  # noqa: E402
from solvers import BUILTIN_CONTROLS, make_builtin_factory, make_external_factory  # noqa: E402

QUICK = dict(
    DEFAULT_CONFIG,
    dr_values=(0.4, 0.2, 0.1),
    r_max=20.0,
    t_end=4.0,
    stability_dr=0.1,
)


class TestNullControls(unittest.TestCase):
    """Every control must land on its declared verdict; PASS must be earned."""

    def test_battery_matches_expectations(self):
        for name in BUILTIN_CONTROLS:
            with self.subTest(control=name):
                report = evaluate(make_builtin_factory(name), config=QUICK, label=name)
                self.assertEqual(
                    report["verdict"],
                    CONTROL_EXPECTATIONS[name],
                    msg=f"{name}: gates={ {k: g['status'] for k, g in report['gates'].items()} }",
                )

    def test_order_gate_rejects_first_order(self):
        report = evaluate(make_builtin_factory("mock_order1"), config=QUICK, label="order1")
        self.assertEqual(report["gates"]["order"]["status"], "FAIL")
        self.assertLess(report["gates"]["order"]["measured_order"], 1.5)

    def test_invariant_gate_rejects_energy_leak(self):
        report = evaluate(make_builtin_factory("mock_leaky"), config=QUICK, label="leaky")
        self.assertEqual(report["gates"]["order"]["status"], "PASS")
        self.assertEqual(report["gates"]["invariant"]["status"], "FAIL")

    def test_stability_gate_rejects_blowup(self):
        report = evaluate(make_builtin_factory("mock_unstable"), config=QUICK, label="unstable")
        self.assertEqual(report["gates"]["stability"]["status"], "FAIL")

    def test_missing_invariant_is_inconclusive_not_pass(self):
        report = evaluate(
            make_builtin_factory("mock_hidden_invariant"), config=QUICK, label="hidden"
        )
        self.assertEqual(report["gates"]["order"]["status"], "PASS")
        self.assertEqual(report["gates"]["invariant"]["status"], "INCONCLUSIVE")
        self.assertEqual(report["verdict"], "INCONCLUSIVE")

    def test_reference_solver_passes_at_default_resolutions(self):
        """The declared acceptance config, not just the quick one."""
        report = evaluate(make_builtin_factory("radial_leapfrog"), label="radial_leapfrog")
        self.assertEqual(report["verdict"], "PASS")
        self.assertLess(report["gates"]["invariant"]["relative_drift"], 1e-9)
        self.assertAlmostEqual(report["gates"]["order"]["measured_order"], 2.0, delta=0.3)


class TestReproducibility(unittest.TestCase):
    def test_same_run_same_digest(self):
        a = evaluate(make_builtin_factory("radial_leapfrog"), config=QUICK, label="det")
        b = evaluate(make_builtin_factory("radial_leapfrog"), config=QUICK, label="det")
        self.assertEqual(a["report_digest"], b["report_digest"])

    def test_different_controls_different_digest(self):
        a = evaluate(make_builtin_factory("mock_order2"), config=QUICK, label="x")
        b = evaluate(make_builtin_factory("mock_order1"), config=QUICK, label="x")
        self.assertNotEqual(a["report_digest"], b["report_digest"])

    def test_leapfrog_discrete_energy_conserved(self):
        """Direct unit check of the invariant functional on the reference scheme."""
        r = grid(20.0, 0.2)
        pulse = GaussianPulse()
        psi0, psi_t0, psi_tt0 = pulse.initial_data(r)
        from solvers import RadialLeapfrog

        solver = RadialLeapfrog(r, 0.5 * 0.2, psi0, psi_t0, psi_tt0)
        energies = []
        for _ in range(40):
            solver.step()
            if solver.psi_prev is not None:
                energies.append(discrete_energy(solver.psi, solver.psi_prev, solver.dt, solver.dr))
        e0 = energies[0]
        drift = max(abs(e - e0) / abs(e0) for e in energies)
        self.assertLess(drift, 1e-12)


class TestExternalBridge(unittest.TestCase):
    def test_external_echo_solver_passes(self):
        cmd = f'"{sys.executable}" "{HERE / "external_echo_solver.py"}"'
        factory = make_external_factory(cmd, timeout=60.0, t_end=QUICK["t_end"])
        report = evaluate(factory, config=QUICK, label="external_echo")
        self.assertEqual(report["verdict"], "PASS", msg=str(report["gates"]))

    def test_external_hanging_solver_is_killed_and_failed(self):
        cmd = f'"{sys.executable}" "{HERE / "external_hang_solver.py"}"'
        factory = make_external_factory(cmd, timeout=1.0, t_end=QUICK["t_end"])
        report = evaluate(factory, config=QUICK, label="external_hang")
        self.assertEqual(report["verdict"], "FAIL")
        self.assertIn("SolverTimeout", report["gates"]["order"]["reason"])


class TestUnits(unittest.TestCase):
    def test_fit_order_recovers_known_slopes(self):
        drs = [0.2, 0.1, 0.05]
        self.assertAlmostEqual(fit_order(drs, [4e-2, 1e-2, 2.5e-3]), 2.0, places=6)
        self.assertAlmostEqual(fit_order(drs, [4e-1, 2e-1, 1e-1]), 1.0, places=6)

    def test_grid_includes_endpoints(self):
        r = grid(1.0, 0.3)
        self.assertEqual(r[0], 0.0)
        self.assertAlmostEqual(r[-1], 0.9)
        self.assertTrue(np.allclose(np.diff(r), 0.3))

    def test_phi_from_psi_is_zero_at_origin_not_invented(self):
        r = np.array([0.0, 1.0, 2.0])
        psi = np.array([0.0, 3.0, 4.0])
        phi = phi_from_psi(psi, r)
        self.assertEqual(phi[0], 0.0)
        self.assertAlmostEqual(phi[1], 3.0)
        self.assertAlmostEqual(phi[2], 2.0)

    def test_standing_mode_satisfies_wave_equation(self):
        """Second-order finite differences of the exact mode match psi_tt."""
        r = np.linspace(0.0, 10.0, 2001)
        dr = r[1] - r[0]
        t = 0.7
        psi = standing_psi(r, t, k=1.0)
        lap = np.zeros_like(psi)
        lap[1:-1] = (psi[2:] - 2 * psi[1:-1] + psi[:-2]) / dr**2
        # interior points away from boundaries
        err = np.max(np.abs(lap[2:-2] - (-1.0) * psi[2:-2]))
        self.assertLess(err, 1e-3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
