#!/usr/bin/env python3
"""Example external solver implementing the harness JSON protocol.

It uses the reference leapfrog integrator (imported from this directory) so that
the protocol itself can be smoke-tested end to end.  Stdout must contain exactly
one JSON object and nothing else.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

from reference_solutions import GaussianPulse  # noqa: E402
from solvers import RadialLeapfrog  # noqa: E402


def main() -> int:
    req = json.load(sys.stdin)
    r = np.asarray(req["r"], dtype=float)
    dt = float(req["dt"])
    t_end = float(req["t_end"])
    psi0 = np.asarray(req["psi0"], dtype=float)
    psi_t0 = np.asarray(req["psi_t0"], dtype=float)
    pulse = GaussianPulse()
    psi_tt0 = pulse.psi_tt(r, 0.0)
    solver = RadialLeapfrog(r, dt, psi0, psi_t0, psi_tt0)
    times = [0.0]
    states = [solver.psi.tolist()]
    prevs = [None]
    cap = int(t_end / dt) * 10 + 100
    steps = 0
    while solver.t < t_end - 1e-12:
        solver.step()
        steps += 1
        if steps > cap:
            raise SystemExit("step cap exceeded")
        times.append(float(solver.t))
        states.append(solver.psi.tolist())
        prevs.append(solver.psi_prev.tolist())
    json.dump({"t": times, "psi": states, "psi_prev": prevs}, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
