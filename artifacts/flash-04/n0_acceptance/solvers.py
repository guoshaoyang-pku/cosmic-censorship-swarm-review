"""Solvers used by the N0 acceptance harness.

Two kinds live here:

* ``RadialLeapfrog`` -- a real, second-order, explicit integrator for
  ``psi_tt = psi_rr`` with Dirichlet data ``psi(0)=psi(R)=0``.  It exists so the
  harness can be validated against a scheme whose convergence order is known
  analytically.  It is a *reference integrator*, not a production solver, and it
  does not model self-gravity.
* mock solvers -- deliberately wrong integrators used as **null controls**.  A
  harness that cannot reject them is broken.  Each mock has exactly one injected
  defect: wrong convergence order, energy leak, hidden invariant data, or
  blow-up.
* ``ReplaySolver`` + ``make_external_factory`` -- subprocess bridge for
  third-party solvers (the JSON protocol is documented in README.md).  The
  subprocess call carries a hard timeout so a pathological solver cannot wedge
  the evaluator (HANDOFF.md section 6, "traps already paid for").

No solver in this module claims anything about cosmic censorship.
"""
from __future__ import annotations

import json
import math
import subprocess
from typing import Callable, Optional

import numpy as np

from reference_solutions import GaussianPulse

__all__ = [
    "HarnessError",
    "SolverFailure",
    "SolverTimeout",
    "RadialLeapfrog",
    "ScaledTrajectorySolver",
    "ReplaySolver",
    "make_builtin_factory",
    "make_external_factory",
    "BUILTIN_CONTROLS",
]


class HarnessError(RuntimeError):
    """The harness itself hit a contract violation (bad grid, step cap, ...)."""


class SolverFailure(RuntimeError):
    """The solver under test returned something unusable."""


class SolverTimeout(SolverFailure):
    """The solver under test exceeded the process-boundary timeout."""


# ---------------------------------------------------------------------------
# Reference integrator
# ---------------------------------------------------------------------------
class RadialLeapfrog:
    """Second-order explicit leapfrog for the 1D radial reduction.

    Update::

        psi_new[j] = 2 psi[j] - psi_prev[j] + lam^2 (psi[j+1] - 2 psi[j] + psi[j-1])

    with ``lam = dt/dr``.  The start uses the Taylor step
    ``psi^1 = psi^0 + dt psi_t0 + dt^2/2 psi_tt0`` (second-order accurate; the
    exact ``psi_tt0`` is supplied by the initial data, so no O(dt) start error
    is introduced).  Boundaries are held at zero.

    The discrete energy

        E = 1/2 sum_j [ ((psi_new[j]-psi[j])/dt)^2
                        + ((psi_new[j+1]-psi_new[j]) (psi[j+1]-psi[j])) / dr^2 ] dr

    is conserved exactly by this update on a fixed grid, which is what the
    harness's invariant check measures (it recomputes E from the exposed
    ``psi``/``psi_prev``; the solver does not self-report it).
    """

    def __init__(self, r, dt, psi0, psi_t0, psi_tt0):
        r = np.asarray(r, dtype=float)
        if r.ndim != 1 or r.size < 4 or r[0] != 0.0:
            raise HarnessError("grid must be 1D, start at r=0, and have >= 4 points")
        if np.any(np.diff(r) <= 0.0):
            raise HarnessError("grid must be strictly increasing")
        if dt <= 0.0:
            raise HarnessError("dt must be positive")
        self.r = r
        self.dr = float(r[1] - r[0])
        self.dt = float(dt)
        self.t = 0.0
        p0 = np.array(psi0, dtype=float, copy=True)
        pt0 = np.array(psi_t0, dtype=float, copy=True)
        ptt0 = np.array(psi_tt0, dtype=float, copy=True)
        for name, arr in (("psi0", p0), ("psi_t0", pt0), ("psi_tt0", ptt0)):
            if arr.shape != r.shape:
                raise HarnessError(f"{name} shape {arr.shape} != grid shape {r.shape}")
        self.psi = p0
        self.psi_prev = None
        self._psi1 = p0 + self.dt * pt0 + 0.5 * self.dt**2 * ptt0
        self._psi1[0] = 0.0
        self._psi1[-1] = 0.0
        self._started = False

    def step(self) -> None:
        lam2 = (self.dt / self.dr) ** 2
        if not self._started:
            # Taylor start: shift (psi^0, psi^1) into (psi_prev, psi).
            self.psi_prev = self.psi
            self.psi = self._psi1
            self._started = True
            self.t += self.dt
            return
        cur = self.psi
        prev = self.psi_prev
        nxt = np.empty_like(cur)
        nxt[1:-1] = 2.0 * cur[1:-1] - prev[1:-1] + lam2 * (
            cur[2:] - 2.0 * cur[1:-1] + cur[:-2]
        )
        nxt[0] = 0.0
        nxt[-1] = 0.0
        self.psi_prev = cur
        self.psi = nxt
        self.t += self.dt
        # keep the loop safe from non-finite blow-up taking forever
        if not np.all(np.isfinite(nxt)):
            raise SolverFailure("non-finite state during leapfrog step")


# ---------------------------------------------------------------------------
# Null controls (deliberately defective)
# ---------------------------------------------------------------------------
class ScaledTrajectorySolver:
    """Base trajectory with an injected, exactly controlled defect.

    Exposed state is ``scale(t) * base.psi`` where

        scale(t) = (1 + amp * dr**order) * exp((drift_rate + blowup_rate) * t)

    * ``order`` / ``amp`` set the spatial convergence defect (e.g. ``order=1``
      makes a first-order-accurate solver; measured order must come out ~1).
    * ``drift_rate`` grows the state in time, which leaks discrete energy while
      leaving the spatial order intact -- an invariant-only failure.
    * ``leak_prev`` corrupts only the exposed ``psi_prev`` (a solver whose
      position is right but whose velocity history is wrong).  Spatial order
      stays intact; the recomputed discrete energy drifts.
    * ``blowup_rate`` grows fast enough to trip the stability check.
    * ``hide_prev=True`` withholds ``psi_prev`` so the invariant is
      unmeasurable -- the harness must return INCONCLUSIVE, never PASS.
    """

    def __init__(
        self,
        base,
        dr: float,
        order: float = 2.0,
        amp: float = 5.0,
        drift_rate: float = 0.0,
        blowup_rate: float = 0.0,
        hide_prev: bool = False,
        leak_prev: float = 0.0,
    ) -> None:
        self.base = base
        self.dr = float(dr)
        self.order = float(order)
        self.amp = float(amp)
        self.drift_rate = float(drift_rate)
        self.blowup_rate = float(blowup_rate)
        self.hide_prev = bool(hide_prev)
        self.leak_prev = float(leak_prev)

    @property
    def t(self) -> float:
        return self.base.t

    def _factor(self, t: float) -> float:
        spatial = 1.0 + self.amp * self.dr**self.order
        temporal = math.exp((self.drift_rate + self.blowup_rate) * t)
        return spatial * temporal

    @property
    def psi(self):
        return self._factor(self.base.t) * self.base.psi

    @property
    def psi_prev(self):
        if self.hide_prev or self.base.psi_prev is None:
            return None
        return (
            (1.0 + self.leak_prev)
            * self._factor(self.base.t - self.base.dt)
            * self.base.psi_prev
        )

    def step(self) -> None:
        self.base.step()


# ---------------------------------------------------------------------------
# External solver bridge
# ---------------------------------------------------------------------------
class ReplaySolver:
    """Replays states computed by an external process, one ``step()`` at a time."""

    def __init__(self, times, states, prev_states):
        if len(times) != len(states):
            raise SolverFailure("external protocol: len(t) != len(psi)")
        if prev_states is not None and len(prev_states) != len(states):
            raise SolverFailure("external protocol: len(psi_prev) != len(psi)")
        self._times = [float(t) for t in times]
        self._states = [np.asarray(s, dtype=float) for s in states]
        self._prev = (
            None
            if prev_states is None
            else [None if s is None else np.asarray(s, dtype=float) for s in prev_states]
        )
        self._i = 0
        self.t = self._times[0]
        self.psi = self._states[0]
        self.psi_prev = None if self._prev is None else self._prev[0]

    def step(self) -> None:
        if self._i + 1 >= len(self._times):
            raise SolverFailure("external replay exhausted before t_end")
        self._i += 1
        self.t = self._times[self._i]
        self.psi = self._states[self._i]
        self.psi_prev = None if self._prev is None else self._prev[self._i]


def make_external_factory(
    cmd: str,
    timeout: float,
    t_end: float,
    pulse: Optional[GaussianPulse] = None,
) -> Callable[[np.ndarray, float], ReplaySolver]:
    """Build a solver factory that shells out to ``cmd`` (hard timeout enforced).

    Request (stdin, one JSON object)::

        {"r": [...], "dt": ..., "t_end": ..., "sample_every": 1,
         "psi0": [...], "psi_t0": [...]}

    Response (stdout, one JSON object) with **every step** sampled::

        {"t": [...], "psi": [[...], ...], "psi_prev": [[...], ...]}

    ``psi_prev`` is optional; when omitted the invariant check is INCONCLUSIVE.
    The harness sub-samples the returned trajectory itself, so ``t`` must start
    at 0 and end at ``t_end`` (within one ``dt``).
    """
    pulse = pulse or GaussianPulse()

    def factory(r, dt):
        r = np.asarray(r, dtype=float)
        psi0, psi_t0, _ = pulse.initial_data(r)
        request = {
            "r": r.tolist(),
            "dt": float(dt),
            "t_end": float(t_end),
            "sample_every": 1,
            "psi0": psi0.tolist(),
            "psi_t0": psi_t0.tolist(),
        }
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                input=json.dumps(request),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise SolverTimeout(f"external solver exceeded {timeout}s: {cmd}") from exc
        if proc.returncode != 0:
            raise SolverFailure(
                f"external solver exit {proc.returncode}: {proc.stderr.strip()[:200]}"
            )
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise SolverFailure(f"external solver returned non-JSON: {exc}") from exc
        for key in ("t", "psi"):
            if key not in payload:
                raise SolverFailure(f"external protocol missing '{key}'")
        return ReplaySolver(payload["t"], payload["psi"], payload.get("psi_prev"))

    return factory


# ---------------------------------------------------------------------------
# Named builtins used by the control battery
# ---------------------------------------------------------------------------
_CONTROL_SPECS = {
    "radial_leapfrog": None,
    "mock_order2": dict(order=2.0, amp=5.0),
    "mock_order1": dict(order=1.0, amp=1.0),
    "mock_order0": dict(order=0.0, amp=0.5),
    "mock_leaky": dict(order=2.0, amp=5.0, leak_prev=0.3),
    "mock_unstable": dict(order=2.0, amp=5.0, blowup_rate=2.0),
    "mock_hidden_invariant": dict(order=2.0, amp=5.0, hide_prev=True),
}
BUILTIN_CONTROLS = tuple(_CONTROL_SPECS)


def _make_leapfrog(r, dt, pulse: GaussianPulse) -> RadialLeapfrog:
    psi0, psi_t0, psi_tt0 = pulse.initial_data(r)
    return RadialLeapfrog(r, dt, psi0, psi_t0, psi_tt0)


def make_builtin_factory(name: str, pulse: Optional[GaussianPulse] = None):
    """Return ``factory(r, dt) -> solver`` for a named builtin."""
    if name not in _CONTROL_SPECS:
        raise HarnessError(f"unknown builtin solver '{name}'")
    pulse = pulse or GaussianPulse()

    def factory(r, dt):
        base = _make_leapfrog(r, dt, pulse)
        spec = _CONTROL_SPECS[name]
        if spec is None:
            return base
        return ScaledTrajectorySolver(base, dr=float(r[1] - r[0]), **spec)

    return factory
