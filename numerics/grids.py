"""Uniform grids used by the N0 calibration tests."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PeriodicGrid:
    """1-D periodic grid x_i = i*h, h = length/n."""

    n: int
    length: float

    @property
    def h(self) -> float:
        return self.length / self.n

    @property
    def x(self) -> np.ndarray:
        return np.arange(self.n) * self.h


@dataclass(frozen=True)
class SphericalGrid:
    """Cell-centred spherical grid on [0, R] with staggered faces.

    Cells     i = 0..N-1   centres r_i = (i+1/2) h,  volume V_i = (r_{i+1}^3 - r_i^3)/3
    Faces     f = 0..N     r_f = f h,               area   A_f = r_f^2,  A_0 = 0
    R = N h.  Face 0 carries zero flux, which is the discrete regularity
    condition for an l=0 field; face N carries the outer boundary flux.
    """

    n: int
    radius: float

    @property
    def h(self) -> float:
        return self.radius / self.n

    @property
    def r_cell(self) -> np.ndarray:
        return (np.arange(self.n) + 0.5) * self.h

    @property
    def r_face(self) -> np.ndarray:
        return np.arange(self.n + 1) * self.h

    @property
    def volume(self) -> np.ndarray:
        rf = self.r_face
        return (rf[1:] ** 3 - rf[:-1] ** 3) / 3.0

    @property
    def area(self) -> np.ndarray:
        return self.r_face**2
