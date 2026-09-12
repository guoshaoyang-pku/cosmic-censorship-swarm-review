#!/usr/bin/env python3
"""Stdin/stdout bridge: expose ``numerics/tests/flat_wave.py`` to external gates.

Worker-04's independent N0 acceptance harness
(``artifacts/flash-04/n0_acceptance/``) drives solvers through a subprocess JSON
protocol.  This bridge speaks that protocol using the operators and RK4 update
of ``flat_wave.py``; it contains no physics of its own and makes no claim.
Keeping it separate from the candidate artifact lets an external gate test the
candidate without either file importing the other's conclusions.

Request  (stdin, one JSON object):
    {"r": [...], "dt": ..., "t_end": ..., "sample_every": 1,
     "psi0": [...], "psi_t0": [...]}
Response (stdout, one JSON object):
    {"t": [...], "psi": [[...], ...], "psi_prev": [[...] or null, ...]}

``psi_prev[k]`` is the state one dt before ``psi[k]`` (null at t=0), which is
what a two-level discrete-energy check expects.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flat_wave import d2  # noqa: E402


def integrate_trace(r, dt, t_end, v0, w0, every=1, order=2):
    h = float(r[1] - r[0])
    v = np.array(v0, dtype=float)
    w = np.array(w0, dtype=float)
    v[0] = v[-1] = 0.0
    n_steps = max(1, int(round(t_end / dt)))
    dt = t_end / n_steps
    times, states, prevs = [0.0], [v.tolist()], [None]
    t = 0.0
    for k in range(n_steps):
        vprev = v
        k1v, k1w = w, d2(v, h, order)
        k2v, k2w = w + 0.5 * dt * k1w, d2(v + 0.5 * dt * k1v, h, order)
        k3v, k3w = w + 0.5 * dt * k2w, d2(v + 0.5 * dt * k2v, h, order)
        k4v, k4w = w + dt * k3w, d2(v + dt * k3v, h, order)
        v = v + (dt / 6.0) * (k1v + 2 * k2v + 2 * k3v + k4v)
        w = w + (dt / 6.0) * (k1w + 2 * k2w + 2 * k3w + k4w)
        t += dt
        if (k + 1) % every == 0 or k == n_steps - 1:
            times.append(t)
            states.append(v.tolist())
            prevs.append(vprev.tolist())
    return {"t": times, "psi": states, "psi_prev": prevs}


def main() -> int:
    req = json.load(sys.stdin)
    out = integrate_trace(
        np.asarray(req["r"], dtype=float),
        float(req["dt"]),
        float(req["t_end"]),
        np.asarray(req["psi0"], dtype=float),
        np.asarray(req["psi_t0"], dtype=float),
        every=int(req.get("sample_every", 1)),
    )
    json.dump(out, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
