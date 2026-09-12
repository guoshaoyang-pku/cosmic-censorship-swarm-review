"""Spherical flat-space scalar-wave schemes on a cell-centred grid.

Two schemes are implemented so the calibration has a control:

``SphericalSBP``
    Staggered finite-volume scheme.  psi and Pi live at cell centres, Phi at
    interior faces.  Pi_t is a flux divergence with face areas A_f = r_f^2 and
    zero flux at r = 0, which *is* the discrete l=0 regularity condition.
    Phi_t is the face gradient of Pi.  The pair satisfies summation by parts
    with respect to the discrete energy

        E = 1/2 sum_i V_i Pi_i^2 + 1/2 h sum_{f=1}^{N-1} A_f Phi_f^2 ,

    so the semi-discrete energy law is *exactly*

        dE/dt = A_N Phi_N Pi_{N-1}            (boundary flux only).

``SphericalCollocated``
    Cell-centred psi, Pi, Phi with centred stencils and the naive
    ``D2 + (2/r) D1`` Laplacian.  Kept as a control: the volume part of
    dE/dt does not telescope, leaving an O(h^2) residual.  It is not used
    for production.

Boundary conditions for Phi at the outer face r = R:
    ``exact``     Phi_N = phi_exact(R, t)        (manufactured-solution data)
    ``outgoing``  Phi_N = -(Pi_{N-1} + psi_{N-1}/R), the exact relation for a
                  pure outgoing spherical wave psi = F(t-r)/r truncated at R
                  (first-order accurate closure).
"""
from __future__ import annotations

from typing import Callable, Optional

import numpy as np

from .fd import _D1, _D2
from .grids import SphericalGrid


def _apply_with_ghosts(u, h, table, order, ghost_l, ghost_r, power):
    """Apply a central stencil to u using explicit left/right ghost layers."""
    c, den = table[order]
    m = (len(c) - 1) // 2
    ue = np.concatenate([ghost_l, u, ghost_r])
    out = np.zeros_like(u)
    for j in range(-m, m + 1):
        out += c[j + m] * ue[m + j : m + j + len(u)]
    return out / (den * h**power)


def _symmetry_ghosts(u, parity: float, m: int):
    """Ghost layer for an l=0 field at r=0: u(-r) = parity * u(r)."""
    return parity * u[:m][::-1]


class SphericalSBP:
    def __init__(
        self,
        grid: SphericalGrid,
        bc: str = "outgoing",
        phi_boundary: Optional[Callable[[float], float]] = None,
        source: Optional[Callable[[np.ndarray, float], np.ndarray]] = None,
    ) -> None:
        if bc not in {"outgoing", "exact"}:
            raise ValueError("bc must be 'outgoing' or 'exact'")
        if bc == "exact" and phi_boundary is None:
            raise ValueError("bc='exact' needs a phi_boundary(t) callback")
        self.grid = grid
        self.bc = bc
        self.phi_boundary = phi_boundary
        self.source = source
        self.A = grid.area
        self.V = grid.volume
        self.h = grid.h
        self.N = grid.n

    # -- state packing: [psi(N), pi(N), phi(N-1)] --------------------------
    def pack(self, psi, pi, phi):
        return np.concatenate([np.asarray(psi, float), np.asarray(pi, float), np.asarray(phi, float)])

    def unpack(self, y):
        n = self.N
        return y[:n], y[n : 2 * n], y[2 * n :]

    def boundary_phi(self, y, t: float) -> float:
        if self.bc == "exact":
            return float(self.phi_boundary(t))
        psi, pi, _ = self.unpack(y)
        return float(-(pi[-1] + psi[-1] / self.grid.radius))

    # -- RHS ----------------------------------------------------------------
    def rhs(self, t: float, y) -> np.ndarray:
        psi, pi, phi = self.unpack(y)
        A, V, h, N = self.A, self.V, self.h, self.N
        phiN = self.boundary_phi(y, t)

        # flux divergence at cell centres; face 0 carries zero flux
        flux = np.empty(N + 1)
        flux[0] = 0.0
        flux[1:N] = A[1:N] * phi
        flux[N] = A[N] * phiN
        dpi = (flux[1:] - flux[:-1]) / V
        if self.source is not None:
            dpi = dpi + self.source(self.grid.r_cell, t)

        dphi = np.empty(N - 1)
        if N > 1:
            dphi[:] = (pi[1:] - pi[:-1]) / h

        return np.concatenate([pi, dpi, dphi])

    # -- invariants ---------------------------------------------------------
    def energy(self, y) -> float:
        psi, pi, phi = self.unpack(y)
        kin = 0.5 * np.sum(self.V * pi**2)
        pot = 0.5 * self.h * np.sum(self.A[1 : self.N] * phi**2)
        return float(kin + pot)

    def flux(self, y, t: float) -> float:
        _, pi, _ = self.unpack(y)
        return float(self.A[self.N] * self.boundary_phi(y, t) * pi[-1])

    def constraint_residual(self, y) -> float:
        """max_f |Phi_f - (psi_f - psi_{f-1})/h| over interior faces."""
        psi, _, phi = self.unpack(y)
        if self.N < 2:
            return 0.0
        return float(np.max(np.abs(phi - (psi[1 : self.N] - psi[: self.N - 1]) / self.h)))

    def semi_discrete_residual(self, y, t: float) -> float:
        """Volume part of dE/dt that SBP should cancel exactly (source excluded)."""
        psi, pi, phi = self.unpack(y)
        A, V, h, N = self.A, self.V, self.h, self.N
        flux = np.empty(N + 1)
        flux[0] = 0.0
        flux[1:N] = A[1:N] * phi
        flux[N] = A[N] * self.boundary_phi(y, t)
        dpi_internal = (flux[1:] - flux[:-1]) / V
        dphi = (pi[1:] - pi[:-1]) / h
        vol = np.sum(V * pi * dpi_internal) + h * np.sum(A[1:N] * phi * dphi)
        return float(vol - self.flux(y, t))


class SphericalCollocated:
    """Control scheme: collocated centred ``D2 + (2/r) D1`` (not SBP)."""

    def __init__(
        self,
        grid: SphericalGrid,
        order: int = 2,
        source: Optional[Callable[[np.ndarray, float], np.ndarray]] = None,
        outer_ghosts: Optional[Callable[[str, float], np.ndarray]] = None,
    ) -> None:
        self.grid = grid
        self.order = order
        self.source = source
        self.outer_ghosts = outer_ghosts  # (varname, t) -> m values at r_cell[N:]
        self.N = grid.n
        self.h = grid.h
        self.m = order // 2

    def pack(self, psi, pi, phi):
        return np.concatenate([np.asarray(psi, float), np.asarray(pi, float), np.asarray(phi, float)])

    def unpack(self, y):
        n = self.N
        return y[:n], y[n : 2 * n], y[2 * n :]

    def _outer(self, name: str, t: float):
        if self.outer_ghosts is None:
            return np.zeros(self.m)
        return np.asarray(self.outer_ghosts(name, t), dtype=float)

    def d1(self, u, name: str, t: float):
        gl = _symmetry_ghosts(u, +1.0, self.m)
        gr = self._outer(name, t)
        return _apply_with_ghosts(u, self.h, _D1, self.order, gl, gr, 1)

    def d2(self, u, name: str, t: float):
        gl = _symmetry_ghosts(u, +1.0, self.m)
        gr = self._outer(name, t)
        return _apply_with_ghosts(u, self.h, _D2, self.order, gl, gr, 2)

    def laplacian(self, psi, t: float):
        return self.d2(psi, "psi", t) + (2.0 / self.grid.r_cell) * self.d1(psi, "psi", t)

    def rhs(self, t: float, y) -> np.ndarray:
        psi, pi, phi = self.unpack(y)
        dpi = self.laplacian(psi, t)
        if self.source is not None:
            dpi = dpi + self.source(self.grid.r_cell, t)
        dphi = self.d1(pi, "pi", t)
        return np.concatenate([pi, dpi, dphi])

    def energy(self, y) -> float:
        _, pi, phi = self.unpack(y)
        return float(0.5 * np.sum(self.grid.volume * (pi**2 + phi**2)))

    def flux_estimate(self, y, t: float) -> float:
        _, pi, phi = self.unpack(y)
        return float(self.grid.area[self.N] * pi[-1] * phi[-1])

    def semi_discrete_residual(self, y, t: float) -> float:
        """dE/dt minus the estimated boundary flux (nonzero O(h^2) by design)."""
        _, pi, phi = self.unpack(y)
        dpi = self.laplacian(self.unpack(y)[0], t)
        dphi = self.d1(pi, "pi", t)
        vol = np.sum(self.grid.volume * (pi * dpi + phi * dphi))
        return float(vol - self.flux_estimate(y, t))
