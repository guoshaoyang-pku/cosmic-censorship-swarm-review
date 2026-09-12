"""Exact reference solutions for the flat-space massless scalar wave in spherical symmetry.

Class binding: AF-WCC-SCALAR-SPH, test-field (fixed Minkowski background) limit only.
No backreaction, no self-gravity, no claim about cosmic censorship.

Equation solved by every solver under this harness::

    d_t^2 phi = d_r^2 phi + (2/r) d_r phi          (flat space, spherical symmetry)

with the regular reduction ``psi = r * phi``, which obeys the 1D wave equation
``d_t^2 psi = d_r^2 psi`` on ``r >= 0`` together with the regularity condition
``psi(0, t) = 0``.  The harness therefore measures convergence of ``psi`` on a
radial grid; physical-field reconstruction ``phi = psi / r`` is a separate
acceptance item (see SPEC.md, "Not covered").

All functions are pure and deterministic.  No randomness, no I/O, no state.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "GaussianPulse",
    "standing_psi",
    "standing_psi_t",
    "standing_psi_tt",
    "phi_from_psi",
]


class GaussianPulse:
    """Outgoing pulse built by the method of images.

    ``psi(r, t) = F(r - t) - F(-r - t)`` with ``F(s) = exp(-(s-r0)^2/(2 sigma^2))``.

    * It solves ``d_t^2 psi = d_r^2 psi`` exactly on ``r >= 0``.
    * ``psi(0, t) = 0`` for every ``t``, so the solution is regular at the origin.
    * The image term ``F(-r-t)`` is suppressed by at least ``exp(-2*r0*sigma^-2)``
      for ``r >= 0``; with the defaults it is ``< 1e-10`` everywhere on the grid.

    Initial data returned by :meth:`initial_data` is exact to machine precision;
    a solver must be able to consume ``(psi0, psi_t0, psi_tt0)``.
    """

    def __init__(self, r0: float = 10.0, sigma: float = 1.5) -> None:
        if sigma <= 0.0 or r0 <= 0.0:
            raise ValueError("r0 and sigma must be positive")
        self.r0 = float(r0)
        self.sigma = float(sigma)

    # --- F and derivatives -------------------------------------------------
    def F(self, s):
        s = np.asarray(s, dtype=float)
        return np.exp(-((s - self.r0) ** 2) / (2.0 * self.sigma**2))

    def Fp(self, s):
        s = np.asarray(s, dtype=float)
        return -((s - self.r0) / self.sigma**2) * self.F(s)

    def Fpp(self, s):
        s = np.asarray(s, dtype=float)
        return (((s - self.r0) ** 2) / self.sigma**4 - 1.0 / self.sigma**2) * self.F(s)

    # --- psi and its derivatives ------------------------------------------
    def psi(self, r, t):
        r = np.asarray(r, dtype=float)
        return self.F(r - t) - self.F(-r - t)

    def psi_t(self, r, t):
        r = np.asarray(r, dtype=float)
        return -self.Fp(r - t) + self.Fp(-r - t)

    def psi_r(self, r, t):
        r = np.asarray(r, dtype=float)
        return self.Fp(r - t) + self.Fp(-r - t)

    def psi_tt(self, r, t):
        r = np.asarray(r, dtype=float)
        return self.Fpp(r - t) - self.Fpp(-r - t)

    def initial_data(self, r):
        """Return ``(psi0, psi_t0, psi_tt0)`` at ``t = 0`` on grid ``r``."""
        r = np.asarray(r, dtype=float)
        return self.psi(r, 0.0), self.psi_t(r, 0.0), self.psi_tt(r, 0.0)


def standing_psi(r, t, k: float = 1.0):
    """Standing mode ``psi = sin(k r) cos(k t)`` (regular: ``phi -> k`` at ``r=0``)."""
    r = np.asarray(r, dtype=float)
    return np.sin(k * r) * np.cos(k * t)


def standing_psi_t(r, t, k: float = 1.0):
    r = np.asarray(r, dtype=float)
    return -k * np.sin(k * r) * np.sin(k * t)


def standing_psi_tt(r, t, k: float = 1.0):
    r = np.asarray(r, dtype=float)
    return -(k**2) * standing_psi(r, t, k)


def phi_from_psi(psi, r):
    """Reconstruct ``phi = psi / r`` with the regular limit at ``r = 0`` left as 0.

    Deliberately returns 0 at ``r = 0`` rather than extrapolating: the harness must
    not silently invent a value where the reduction is singular.
    """
    psi = np.asarray(psi, dtype=float)
    r = np.asarray(r, dtype=float)
    out = np.zeros_like(psi)
    nz = r > 0.0
    out[nz] = psi[nz] / r[nz]
    return out
