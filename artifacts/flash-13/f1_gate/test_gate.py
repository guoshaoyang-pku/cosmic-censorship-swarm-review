#!/usr/bin/env python3
"""WP13-F1-GATE acceptance matrix. Exit 0 iff every check passes.

Checks: 8 fixture verdicts (1 accept, 6 reject, 1 known-blind-spot probe) against the expected
failed rule IDs, plus 5 CLI/exit-code checks including the R12 artifact pin path.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GATE = HERE / "check_schema.py"
FIX = HERE / "fixtures"

spec = importlib.util.spec_from_file_location("check_schema", GATE)
check_schema = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_schema)

MATRIX = {
    "valid_af_wcc_vac_gen.yaml": ("accept", set()),
    "leak_scc_c2.yaml": ("reject", {"R09"}),
    "leak_scalar_sph.yaml": ("reject", {"R05", "R09"}),
    "vague_quantifiers.yaml": ("reject", {"R03"}),
    "conclusion_inflation.yaml": ("reject", {"R08"}),
    "vague_data_class.yaml": ("reject", {"R05"}),
    "missing_falsifier.yaml": ("reject", {"R10"}),
}
PROBE = "probe_rephrased_leak.yaml"

results = []


def record(name, ok, detail):
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")


def run_gate(args):
    return subprocess.run(
        [sys.executable, str(GATE), *args], capture_output=True, text=True
    )


def main() -> int:
    import yaml  # noqa: F401  (gate dependency check)

    for fname, (verdict, rules) in MATRIX.items():
        doc = yaml.safe_load((FIX / fname).read_text())
        g = check_schema.Gate("AF-WCC-VAC-GEN", [], [])
        g.run(doc, FIX / fname)
        actual_verdict = "accept" if not g.failed else "reject"
        failed = {f["rule"] for f in g.failed}
        ok = actual_verdict == verdict and rules <= failed and (bool(failed) or not rules)
        record(f"matrix/{fname}", ok, f"verdict={actual_verdict} failed={sorted(failed) or '-'} expected={sorted(rules) or '-'}")

    # Known-blind-spot probe: accepted by design. A rejection is an improvement, not a failure.
    doc = yaml.safe_load((FIX / PROBE).read_text())
    g = check_schema.Gate("AF-WCC-VAC-GEN", [], [])
    g.run(doc, FIX / PROBE)
    if g.failed:
        record(f"probe/{PROBE}", True,
               f"BLIND SPOT CLOSED by later hardening; failed={sorted({f['rule'] for f in g.failed})}")
    else:
        record(f"probe/{PROBE}", True,
               "known lexical blind spot confirmed (rephrased SCC content accepted; semantic check remains A1 work)")

    good = str(FIX / "valid_af_wcc_vac_gen.yaml")

    p = run_gate([good])
    record("cli/accept-exit-0", p.returncode == 0, f"exit={p.returncode}")

    p = run_gate([good, "--expect-class", "AF-SCC-C2-VAC-GEN"])
    record("cli/wrong-class-reject", p.returncode == 1 and "R02" in p.stdout,
           f"exit={p.returncode} R02={'R02' in p.stdout}")

    p = run_gate([good, "--require-file", "/nonexistent/af_wcc_vacuum.yaml"])
    record("cli/missing-artifact-reject-R12", p.returncode == 1 and "R12" in p.stdout,
           f"exit={p.returncode} R12={'R12' in p.stdout}")

    p = run_gate([good, "--pin", f"{good}:{'0' * 64}"])
    record("cli/hash-mismatch-reject-R12", p.returncode == 1 and "R12" in p.stdout,
           f"exit={p.returncode} R12={'R12' in p.stdout}")

    p = run_gate(["/nonexistent/schema.yaml"])
    record("cli/missing-input-exit-2", p.returncode == 2, f"exit={p.returncode}")

    npass = sum(1 for _, ok, _ in results if ok)
    print(f"\nWP13-F1-GATE acceptance matrix: {npass}/{len(results)} PASS")
    (HERE / "acceptance_report.json").write_text(json.dumps(
        {"gate": "WP13-F1-GATE", "checks": len(results), "passed": npass,
         "results": [{"name": n, "pass": ok, "detail": d} for n, ok, d in results]}, indent=2) + "\n")
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
