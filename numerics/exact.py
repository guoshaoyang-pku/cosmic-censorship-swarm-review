"""Exact solutions and manufactured sources for the flat-space wave equation.

Conventions
-----------
Cartesian:  psi_tt = psi_xx + S(x,t)
Spherical:  psi_tt = psi_rr + (2/r) psi_r + S(r,t),  psi regular at r=0
First-order reduction used by the code:
    psi_t = Pi,   Pi_t = L[psi] + S,   Phi = psi_r

All manufactured solutions here are *regular at the origin* (even in r) so
they exercise the discrete origin treatment instead of hiding it.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


# ---------------------------------------------------------------------------
# Cartesian manufactured solution
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CartesianMMS:
    """psi = amp * sin(k x) * sin(omega t), source S = (omega^2-k^2) psi."""

    k: float
    omega: float
    amp: float = 1.0

    def psi(self, x, t):
        return self.amp * np.sin(self.k * x) * np.sin(self.omega * t)

    def pi(self, x, t):
        return self.amp * self.omega * np.sin(self.k * x) * np.cos(self.omega * t)

    def phi(self, x, t):
        return self.amp * self.k * np.cos(self.k * x) * np.sin(self.omega * t)

    def source(self, x, t):
        return (self.omega**2 - self.k**2) * self.psi(x, t)


# ---------------------------------------------------------------------------
# Spherical manufactured solution
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SphericalMMS:
    """psi = sin(omega t) * P(r^2),  P(u) = 1 + a u + b u^2.

    Exact source (derived in ``docs`` below, unit-tested against a numerical
    Laplacian):
        S = sin(omega t) * [ -(omega^2 + 6a) - (omega^2 a + 20 b) r^2 - omega^2 b r^4 ]
    """

    omega: float
    a: float = -0.15
    b: float = 0.01

    def _P(self, r):
        u = np.asarray(r) ** 2
        return 1.0 + self.a * u + self.b * u**2

    def psi(self, r, t):
        r = np.asarray(r, dtype=float)
        return np.sin(self.omega * t) * self._P(r)

    def pi(self, r, t):
        r = np.asarray(r, dtype=float)
        return self.omega * np.cos(self.omega * t) * self._P(r)

    def phi(self, r, t):
        r = np.asarray(r, dtype=float)
        return np.sin(self.omega * t) * (2.0 * self.a * r + 4.0 * self.b * r**3)

    def source(self, r, t):
        r = np.asarray(r, dtype=float)
        u = r**2
        return np.sin(self.omega * t) * (
            -(self.omega**2 + 6.0 * self.a)
            - (self.omega**2 * self.a + 20.0 * self.b) * u
            - self.omega**2 * self.b * u**2
        )


# ---------------------------------------------------------------------------
# Exact regular spherical pulse
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SphericalPulse:
    """Exact regular solution psi = [F(t-r) - F(t+r)] / r.

    F(s) = amp * exp(-((s - s0)/width)^2).  With ``s0 < 0`` and
    ``|s0| >> width`` this is a clean outgoing pulse launched at r ~ |s0|
    plus an exponentially small mirror image, and it is regular at r = 0.
    """

    width: float = 1.0
    s0: float = -5.0
    amp: float = 1.0

    def F(self, s):
        s = np.asarray(s, dtype=float)
        return self.amp * np.exp(-((s - self.s0) / self.width) ** 2)

    def dF(self, s):
        s = np.asarray(s, dtype=float)
        return -2.0 * (s - self.s0) / self.width**2 * self.F(s)

    def d2F(self, s):
        s = np.asarray(s, dtype=float)
        return (4.0 * (s - self.s0) ** 2 / self.width**4 - 2.0 / self.width**2) * self.F(s)

    def d3F(self, s):
        s = np.asarray(s, dtype=float)
        return (
            -8.0 * (s - self.s0) ** 3 / self.width**6
            + 12.0 * (s - self.s0) / self.width**4
        ) * self.F(s)

    def _eval(self, r, t, kind: str):
        """Broadcast-safe evaluation of psi / Pi / Phi, with the r=0 limit."""
        r = np.asarray(r, dtype=float)
        t = np.asarray(t, dtype=float)
        rb, tb = np.broadcast_arrays(r, t)
        small = rb < 1e-12
        rs = np.where(small, 1.0, rb)
        if kind == "psi":
            vals = (self.F(tb - rs) - self.F(tb + rs)) / rs
            lim = -2.0 * self.dF(tb)
        elif kind == "pi":
            vals = (self.dF(tb - rs) - self.dF(tb + rs)) / rs
            lim = -2.0 * self.d2F(tb)
        else:
            vals = (
                -(self.dF(tb - rs) + self.dF(tb + rs)) / rs
                - (self.F(tb - rs) - self.F(tb + rs)) / rs**2
            )
            lim = np.zeros_like(tb)
        return np.where(small, lim, vals)

    def psi(self, r, t):
        return self._eval(r, t, "psi")

    def pi(self, r, t):
        return self._eval(r, t, "pi")

    def phi(self, r, t):
        return self._eval(r, t, "phi")
