"""Finite-difference operators on uniform grids (calibration only).

Two families live here:

1. Periodic central stencils of order 2, 4 and 6, applied with ``np.roll``
   (used for Cartesian dispersion/convergence/energy tests).
2. Symbol utilities ``symbol_d1`` / ``symbol_d2`` that return the exact
   Fourier symbol of a stencil.  These are the *predicted* discrete
   dispersion relations; the measured phase error is compared against them
   so a passing test means "the code implements the stencil we think it
   does", not merely "the error got smaller".

No matrix assembly is used in time stepping; dense matrices are available
only for small-n spectral checks (``periodic_matrix_d2``).
"""
from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# Stencil tables.  Key = formal order, value = (coefficients, denominator).
# Coefficients are ordered from the most negative offset to the most positive,
# i.e. u'(x_i) ~ sum_j c_j u_{i+j-m} / (den * h), m = (len(c)-1)//2.
# ---------------------------------------------------------------------------
_D1 = {
    2: (np.array([-1.0, 0.0, 1.0]), 2.0),
    4: (np.array([1.0, -8.0, 0.0, 8.0, -1.0]), 12.0),
    6: (np.array([-1.0, 9.0, -45.0, 0.0, 45.0, -9.0, 1.0]), 60.0),
}
_D2 = {
    2: (np.array([1.0, -2.0, 1.0]), 1.0),
    4: (np.array([-1.0, 16.0, -30.0, 16.0, -1.0]), 12.0),
    6: (np.array([2.0, -27.0, 270.0, -490.0, 270.0, -27.0, 2.0]), 180.0),
}
ORDERS = (2, 4, 6)


def _check_order(order: int) -> None:
    if order not in _D1:
        raise ValueError(f"unsupported order {order}; choose from {ORDERS}")


def d1_periodic(u: np.ndarray, h: float, order: int = 2) -> np.ndarray:
    """Periodic first derivative with a central stencil of the given order."""
    _check_order(order)
    c, den = _D1[order]
    m = (len(c) - 1) // 2
    out = np.zeros_like(u)
    for j in range(-m, m + 1):
        out += c[j + m] * np.roll(u, -j)
    return out / (den * h)


def d2_periodic(u: np.ndarray, h: float, order: int = 2) -> np.ndarray:
    """Periodic second derivative with a central stencil of the given order."""
    _check_order(order)
    c, den = _D2[order]
    m = (len(c) - 1) // 2
    out = np.zeros_like(u)
    for j in range(-m, m + 1):
        out += c[j + m] * np.roll(u, -j)
    return out / (den * h * h)


def symbol_d1(k: float, h: float, order: int = 2) -> complex:
    """Exact Fourier symbol of :func:`d1_periodic` for mode exp(i k x)."""
    _check_order(order)
    c, den = _D1[order]
    m = (len(c) - 1) // 2
    s = sum(c[j + m] * np.exp(1j * j * k * h) for j in range(-m, m + 1))
    return complex(s / (den * h))


def symbol_d2(k: float, h: float, order: int = 2) -> float:
    """Exact Fourier symbol of :func:`d2_periodic` for mode exp(i k x).

    Returns a real number (the stencil is symmetric); ``-symbol_d2`` is the
    non-negative discrete eigenvalue whose square root gives the numerical
    frequency of the semi-discrete wave equation.
    """
    _check_order(order)
    c, den = _D2[order]
    m = (len(c) - 1) // 2
    s = sum(c[j + m] * np.exp(1j * j * k * h) for j in range(-m, m + 1))
    val = s / (den * h * h)
    if abs(val.imag) > 1e-12 * max(1.0, abs(val.real)):
        raise AssertionError("second-derivative symbol developed an imaginary part")
    return float(val.real)


def numerical_frequency(k: float, h: float, order: int = 2) -> float:
    """omega_num(k) = sqrt(-symbol_d2(k)) for the semi-discrete scheme."""
    lam = symbol_d2(k, h, order)
    if lam > 0:
        raise ValueError("discrete Laplacian is not negative semi-definite here")
    return float(np.sqrt(-lam))


def phase_speed_error(k: float, h: float, order: int = 2) -> float:
    """Relative phase-speed error |omega_num/k - 1| of the semi-discrete scheme."""
    return abs(numerical_frequency(k, h, order) / k - 1.0)


def periodic_matrix_d1(n: int, length: float, order: int = 2) -> np.ndarray:
    """Dense periodic D1 matrix (small n only; spectral checks)."""
    h = length / n
    idx = np.arange(n)
    A = np.zeros((n, n))
    c, den = _D1[order]
    m = (len(c) - 1) // 2
    for j in range(-m, m + 1):
        A[idx, (idx + j) % n] += c[j + m]
    return A / (den * h)


def periodic_matrix_d2(n: int, length: float, order: int = 2) -> np.ndarray:
    """Dense periodic D2 matrix (small n only; spectral checks)."""
    h = length / n
    idx = np.arange(n)
    A = np.zeros((n, n))
    c, den = _D2[order]
    m = (len(c) - 1) // 2
    for j in range(-m, m + 1):
        A[idx, (idx + j) % n] += c[j + m]
    return A / (den * h * h)


def rk4_dt_limit(operator, safety: float = 0.9) -> float:
    """Stable dt for classical RK4 on y' = op y with real negative spectrum.

    RK4's stability interval on the negative real axis is
    [-2.785293563405282, 0]; for the symmetric operators used here the
    spectral radius rho gives dt_max = 2.785... / sqrt(rho).
    """
    rho = float(np.max(np.abs(np.linalg.eigvalsh(np.asarray(operator, dtype=float)))))
    if rho <= 0:
        return float("inf")
    return safety * 2.785293563405282 / np.sqrt(rho)
