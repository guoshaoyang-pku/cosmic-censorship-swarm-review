"""Periodic 1-D Cartesian massless scalar wave: semi-discrete model problems.

State is ``y = [psi(n), pi(n)]`` with psi_t = pi and pi_t = D2 psi + S.
Every operator here is a symmetric periodic stencil, so two energy
functionals are available:

* ``energy_grad``     E = h/2 * sum(pi^2 + (D1 psi)^2)   -- physical form
* ``energy_spectral`` E = h/2 * sum(pi^2 - psi * D2 psi) -- exactly conserved
                       by the semi-discrete scheme for any order

The gap between them is the discrete integration-by-parts defect and is
reported as a diagnostic rather than hidden.
"""
from __future__ import annotations

from typing import Callable, Optional

import numpy as np

from .fd import d1_periodic, d2_periodic
from .grids import PeriodicGrid


class CartesianWave1D:
    def __init__(
        self,
        grid: PeriodicGrid,
        order: int = 2,
        source: Optional[Callable[[np.ndarray, float], np.ndarray]] = None,
        complex_field: bool = False,
    ) -> None:
        self.grid = grid
        self.order = order
        self.source = source
        self.complex_field = complex_field
        self.dtype = complex if complex_field else float

    # -- operators ----------------------------------------------------------
    def d1(self, u):
        return d1_periodic(u, self.grid.h, self.order)

    def d2(self, u):
        return d2_periodic(u, self.grid.h, self.order)

    # -- time stepping ------------------------------------------------------
    def rhs(self, t: float, y: np.ndarray) -> np.ndarray:
        n = self.grid.n
        psi, pi = y[:n], y[n:]
        dpi = self.d2(psi)
        if self.source is not None:
            dpi = dpi + self.source(self.grid.x, t)
        return np.concatenate([pi, dpi])

    def initial(self, psi, pi):
        return np.concatenate([np.asarray(psi, dtype=self.dtype), np.asarray(pi, dtype=self.dtype)])

    # -- invariants ---------------------------------------------------------
    def energy_grad(self, y) -> float:
        n = self.grid.n
        psi, pi = y[:n], y[n:]
        d1psi = self.d1(psi)
        val = np.sum(np.abs(pi) ** 2 + np.abs(d1psi) ** 2)
        return float(0.5 * self.grid.h * np.real(val))

    def energy_spectral(self, y) -> float:
        n = self.grid.n
        psi, pi = y[:n], y[n:]
        val = np.sum(np.abs(pi) ** 2 - np.conj(psi) * self.d2(psi))
        return float(0.5 * self.grid.h * np.real(val))

    def momentum(self, y) -> float:
        n = self.grid.n
        psi, pi = y[:n], y[n:]
        return float(self.grid.h * np.real(np.sum(np.conj(pi) * self.d1(psi))))

    def charge(self, y) -> float:
        """U(1) charge h * sum Im(conj(psi) pi), conserved for a complex field."""
        n = self.grid.n
        psi, pi = y[:n], y[n:]
        return float(self.grid.h * np.sum(np.imag(np.conj(psi) * pi)))

    def energy_defect(self, y) -> float:
        """|E_grad - E_spectral|: discrete integration-by-parts defect."""
        return abs(self.energy_grad(y) - self.energy_spectral(y))
