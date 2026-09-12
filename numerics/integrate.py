"""Time integrators used by the calibration suite.

Only classical RK4 is used for production-quality measurements; an explicit
Euler step is available because some diagnostics (energy-drift order) are
easier to interpret when the integrator order is known to be 1.
"""
from __future__ import annotations

from typing import Callable

import numpy as np

Array = np.ndarray


def rk4_step(rhs: Callable[[float, Array], Array], t: float, y: Array, dt: float) -> Array:
    """One classical fourth-order Runge-Kutta step."""
    k1 = rhs(t, y)
    k2 = rhs(t + 0.5 * dt, y + 0.5 * dt * k1)
    k3 = rhs(t + 0.5 * dt, y + 0.5 * dt * k2)
    k4 = rhs(t + dt, y + dt * k3)
    return y + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def euler_step(rhs: Callable[[float, Array], Array], t: float, y: Array, dt: float) -> Array:
    """One explicit Euler step (control integrator)."""
    return y + dt * rhs(t, y)


def integrate(
    rhs: Callable[[float, Array], Array],
    y0: Array,
    t0: float,
    t1: float,
    dt: float,
    stepper: Callable[[Callable, float, Array, float], Array] = rk4_step,
) -> tuple[Array, int]:
    """Integrate from t0 to t1 with a fixed step; the last step is shortened.

    Returns ``(y, n_steps)``.  Fixed steps keep the convergence study honest:
    a step-size controller would make the observed order depend on tolerance.
    """
    if dt <= 0:
        raise ValueError("dt must be positive")
    t = float(t0)
    y = np.array(y0, dtype=float, copy=True)
    n = 0
    while t < t1 - 1e-15 * max(1.0, abs(t1)):
        h = min(dt, t1 - t)
        y = stepper(rhs, t, y, h)
        t += h
        n += 1
    return y, n
