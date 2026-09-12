#!/usr/bin/env python3
"""Probe: does the replication artifact's `gate_limitation_finding` still hold?

Claim under test (numerics/tests/flat_wave_replication.py, revision 0c8a63ae):
  "Both independent second-order schemes conserve their own discrete energies to ~1e-13 or
   better, yet their harness-functional drift is far above drift_tol=1e-6, so the gate
   reports invariant FAIL for legitimate second-order schemes and effectively admits only
   the leapfrog family."
Its own evidence array in the same revision lists cnfd harness drift 6.59e-08 and cnfem
8.48e-09, i.e. *below* drift_tol=1e-6.  The controller adjudication (N0_adjudication.md)
states the falsifier: "a non-leapfrog scheme whose harness-functional drift is <= 1e-6 on
the same configuration".

This probe re-measures the harness-functional drift for the non-leapfrog schemes at several
resolutions, using the replication module's own functions (no edits to that file), and prints
whether the gate would pass or fail.  Read-only with respect to shared artifacts; report is
written to the worker-12 namespace.

Usage: python3 replication_finding_probe.py
"""
from __future__ import annotations

import importlib.util
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TARGET = REPO / "numerics" / "tests" / "flat_wave_replication.py"


def load(path: Path):
    spec = importlib.util.spec_from_file_location("replication_under_probe", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    mod = load(TARGET)
    tol = mod.HARNESS_CONFIG["drift_tol"]
    rows = []
    for scheme in ("cnfd", "cnfem", "lffd"):
        for dr in (0.2, 0.1, 0.05):
            st = mod.invariant_study(scheme, dr=dr, cfl=0.5, r_max=30.0, t_end=6.0, sample_every=4)
            rows.append({
                "scheme": scheme, "dr": dr,
                "own_energy_drift": st["own_energy_drift"],
                "harness_functional_drift": st["harness_leapfrog_energy_drift"],
                "drift_tol": tol,
                "gate_would_pass": st["harness_gate_would_pass"],
            })
    nonleapfrog_pass = [r for r in rows
                        if r["scheme"] in ("cnfd", "cnfem") and r["gate_would_pass"]]
    nonleapfrog_fail = [r for r in rows
                        if r["scheme"] in ("cnfd", "cnfem") and not r["gate_would_pass"]]
    out = {
        "probe": "artifacts/flash-12/n0/replication_finding_probe.py",
        "target": "numerics/tests/flat_wave_replication.py",
        "target_sha256": hashlib.sha256(TARGET.read_bytes()).hexdigest(),
        "checked_at": datetime.now(CST).isoformat(timespec="seconds"),
        "claim_under_test": ("gate_limitation_finding: non-leapfrog second-order schemes fail the "
                             "leapfrog-functional invariant gate"),
        "rows": rows,
        "nonleapfrog_gate_passes": nonleapfrog_pass,
        "nonleapfrog_gate_failures": nonleapfrog_fail,
        "verdict": ("finding_falsified_on_tested_configs" if nonleapfrog_pass and not nonleapfrog_fail
                    else "finding_holds_on_some_config" if nonleapfrog_fail
                    else "inconclusive"),
        "note": ("independently re-runs the replication module's own invariant_study; it does not "
                 "edit it and does not supersede worker-13's ownership of that artifact"),
    }
    (HERE / "replication_finding_probe.json").write_text(json.dumps(out, indent=2, sort_keys=True))
    print(json.dumps({"verdict": out["verdict"],
                      "rows": [{k: (round(v, 12) if isinstance(v, float) else v)
                                for k, v in r.items()} for r in rows]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
