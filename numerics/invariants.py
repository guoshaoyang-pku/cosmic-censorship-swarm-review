"""Invariant diagnostics: drift, conservation budgets, constraint preservation.

These are deliberately *measurements* (numbers plus their convergence with
resolution), never assertions about the continuum theory.  The N0 gate reads
them and decides pass/fail.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np


TINY = 1e-300


def relative_change(x0: float, x1: float) -> float:
    scale = max(abs(x0), abs(x1), TINY)
    return abs(x1 - x0) / scale


def max_relative_drift(series: Sequence[float]) -> float:
    """(max - min) / max|value| of a conserved quantity's time series."""
    a = np.asarray(series, dtype=float)
    scale = np.max(np.abs(a))
    if scale <= TINY:
        return float(np.max(a) - np.min(a))
    return float((np.max(a) - np.min(a)) / scale)


def linear_growth_rate(times: Sequence[float], values: Sequence[float]) -> float:
    """Least-squares slope d(value)/dt, normalised by the mean |value|."""
    t = np.asarray(times, dtype=float)
    v = np.asarray(values, dtype=float)
    if len(t) < 2:
        return 0.0
    slope = float(np.polyfit(t, v, 1)[0])
    scale = max(float(np.mean(np.abs(v))), TINY)
    return slope / scale


def trapezoid(times: Sequence[float], values: Sequence[float]) -> float:
    t = np.asarray(times, dtype=float)
    v = np.asarray(values, dtype=float)
    return float(np.trapezoid(v, t)) if hasattr(np, "trapezoid") else float(np.trapz(v, t))


def energy_budget_residual(E0: float, E1: float, times: Sequence[float], flux: Sequence[float]) -> dict:
    """Check Delta E = integral(flux dt) and return absolute/relative residuals."""
    dt = trapezoid(times, flux)
    residual = (E1 - E0) - dt
    scale = max(abs(E0), abs(E1), abs(dt), TINY)
    return {
        "E0": float(E0),
        "E1": float(E1),
        "delta_E": float(E1 - E0),
        "flux_integral": float(dt),
        "residual": float(residual),
        "relative_residual": float(abs(residual) / scale),
    }


def symbol_spectrum_check(n: int, length: float, order: int = 2) -> dict:
    """Compare dense periodic-D2 eigenvalues with the analytic symbol.

    The expected eigenvalue for mode exp(i k x) is ``symbol_d2(k, h, order)``
    with k = 2 pi m / length.  Agreement to roundoff certifies that the
    dispersion prediction used elsewhere is the symbol of the same stencil.
    """
    from .fd import periodic_matrix_d2, symbol_d2

    h = length / n
    A = periodic_matrix_d2(n, length, order)
    eig = np.linalg.eigvalsh(A)
    ks = 2.0 * np.pi * np.arange(n) / length
    predicted = np.sort(np.array([symbol_d2(k, h, order) for k in ks]))
    denom = max(float(np.max(np.abs(predicted))), TINY)
    return {
        "max_abs_error": float(np.max(np.abs(eig - predicted))),
        "max_rel_error": float(np.max(np.abs(eig - predicted)) / denom),
    }


def constraint_preservation_series(times: Sequence[float], values: Sequence[float]) -> dict:
    """Summarise a constraint-residual time series (max, drift, initial/final)."""
    a = np.asarray(values, dtype=float)
    return {
        "initial": float(a[0]),
        "final": float(a[-1]),
        "max": float(np.max(np.abs(a))),
        "max_relative_drift": max_relative_drift(a),
        "growth_rate": linear_growth_rate(times, a),
    }
