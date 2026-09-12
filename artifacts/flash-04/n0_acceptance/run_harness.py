#!/usr/bin/env python3
"""CLI for the N0 flat-space scalar-wave acceptance harness.

Exit codes
----------
0  verdict PASS (all gates)
1  verdict FAIL (at least one gate failed)
2  verdict INCONCLUSIVE (evidence missing; not a pass)
3  usage/configuration error

Modes
-----
``--solver NAME``
    Run one builtin control/reference solver (see ``--list``).
``--solver-cmd 'CMD'``
    Run an external solver through the documented JSON protocol with a hard
    timeout enforced at the process boundary.
``--controls``
    Run the whole builtin control battery and check every verdict against its
    expected null outcome.  This is the harness's own self-test at the
    experimental level; ``--json`` stores the full evidence bundle.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from harness import DEFAULT_CONFIG, evaluate  # noqa: E402
from solvers import (  # noqa: E402
    BUILTIN_CONTROLS,
    HarnessError,
    make_builtin_factory,
    make_external_factory,
)

# Expected verdict for each control; the harness fails its own battery if any
# control comes out differently.
CONTROL_EXPECTATIONS = {
    "radial_leapfrog": "PASS",          # known 2nd-order scheme, conserved energy
    "mock_order2": "PASS",              # injected O(dr^2) defect only
    "mock_order1": "FAIL",              # first-order scheme must be rejected
    "mock_order0": "FAIL",              # non-convergent scheme must be rejected
    "mock_leaky": "FAIL",               # energy leak must be rejected
    "mock_unstable": "FAIL",            # blow-up must be rejected
    "mock_hidden_invariant": "INCONCLUSIVE",  # missing evidence must not be PASS
}

EXIT_BY_VERDICT = {"PASS": 0, "FAIL": 1, "INCONCLUSIVE": 2}


def run_controls(config: dict, timeout: float) -> tuple[list[dict], bool]:
    reports = []
    all_ok = True
    for name in BUILTIN_CONTROLS:
        factory = make_builtin_factory(name)
        report = evaluate(factory, config=config, label=name)
        expected = CONTROL_EXPECTATIONS[name]
        report["expected_verdict"] = expected
        report["control_ok"] = report["verdict"] == expected
        all_ok &= report["control_ok"]
        reports.append(report)
        print(
            f"{name:22s} verdict={report['verdict']:12s} expected={expected:12s} "
            f"{'ok' if report['control_ok'] else 'BATTERY-FAILURE'}"
        )
    return reports, all_ok


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--solver", help="builtin solver name")
    ap.add_argument("--solver-cmd", help="external solver command (JSON protocol on stdin/stdout)")
    ap.add_argument("--timeout", type=float, default=60.0, help="external solver timeout [s]")
    ap.add_argument("--controls", action="store_true", help="run the builtin control battery")
    ap.add_argument("--list", action="store_true", help="list builtin solvers and exit")
    ap.add_argument("--quick", action="store_true", help="reduced resolutions for smoke tests")
    ap.add_argument("--json", help="write the report bundle (JSON) to this path")
    args = ap.parse_args(argv)

    if args.list:
        for name in BUILTIN_CONTROLS:
            print(name)
        return 0
    if not (args.solver or args.solver_cmd or args.controls):
        ap.error("choose --solver, --solver-cmd, or --controls")

    config = dict(DEFAULT_CONFIG)
    if args.quick:
        config.update(
            dr_values=(0.4, 0.2, 0.1), r_max=20.0, t_end=4.0, stability_dr=0.1
        )

    try:
        if args.controls:
            reports, all_ok = run_controls(config, args.timeout)
            bundle = {
                "battery": "n0_flat_wave_acceptance_controls",
                "config": {k: (list(v) if isinstance(v, tuple) else v) for k, v in config.items()},
                "all_controls_ok": all_ok,
                "reports": reports,
            }
            if args.json:
                Path(args.json).write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n")
            return 0 if all_ok else 1

        if args.solver_cmd:
            factory = make_external_factory(args.solver_cmd, args.timeout, config["t_end"])
            label = f"external:{args.solver_cmd}"
        else:
            factory = make_builtin_factory(args.solver)
            label = args.solver
        report = evaluate(factory, config=config, label=label)
        text = json.dumps(report, indent=2, sort_keys=True)
        print(text)
        if args.json:
            Path(args.json).write_text(text + "\n")
        return EXIT_BY_VERDICT[report["verdict"]]
    except HarnessError as exc:
        print(f"harness configuration error: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
