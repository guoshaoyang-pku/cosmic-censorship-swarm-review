#!/usr/bin/env python3
"""Worker-14 audit-path negative-control verification for the N0 protocol.

Instance: worker-014-20260912T001229-897883 (deepseek-flash-14)
Class-bound task: N0 / AF-WCC-SCALAR-SPH / G-NUM.
Chosen because the last unmet G-NUM criterion (astra-n0add-02) is an independent
A1 verdict on the numerical protocol whose acceptance names *negative controls*.

What this measures
------------------
The protocol declares (convergence_protocol.md, T5) that known-bad runs must be
rejected, and its own falsifier is "the protocol cannot detect a wrong order".
The reference implementation of the failure criteria is
``numerics/protocol/audit_convergence_report.py``.  This script runs that tool
as a *subprocess* (process boundary) on:

  * frozen positive controls that must PASS;
  * the frozen wrong-order / degeneracy controls that must FAIL;
  * four mutants manufactured in memory from the frozen standard report, so the
    negative controls cannot be satisfied by a cached verdict (declared order
    lowered, drift lifted above budget, CFL above the margin, non-finite
    amplitude);
  * two R5 cross-scheme agreement controls (lffd vs cnfd agreeing, and a
    fitted-order-shifted mutant that must be rejected).

Falsifier (fail-closed): any control whose measured verdict / failed-check set
differs from the expectation below makes ``overall.pass`` false and the script
exits 1.  No gate verdict, no node completion, no physics claim is made.

Run:  python3 numerics/protocol/verify_protocol_negative_controls.py
Writes: numerics/protocol/protocol_negative_controls.json
"""
from __future__ import annotations

import datetime
import hashlib
import json
import math
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_DIR = ROOT / "numerics" / "protocol"
TOOL = PROTOCOL_DIR / "audit_convergence_report.py"
OUT = PROTOCOL_DIR / "protocol_negative_controls.json"
SCHEMA = "n0-protocol-negative-controls/v1"

# name -> (source report, expected verdict, checks that must have failed)
FROZEN = {
    # positives: the tool must not reject a conforming run
    "positive_demo_standard": ("demo_report_standard.json", "PASS", []),
    "positive_candidate_pulse": ("report_candidate_pulse.json", "PASS", []),
    "positive_replication_lffd": ("report_lffd.json", "PASS", []),
    "positive_replication_cnfd": ("report_cnfd.json", "PASS", []),
    # negatives: frozen known-bad / degenerate runs
    "negative_wrong_order": ("demo_report_wrong_order.json", "FAIL", ["C4_order"]),
    "negative_standing_degenerate": ("report_candidate_standing.json", "FAIL", ["C2_non_degeneracy"]),
}

# in-memory mutants of demo_report_standard.json: name -> (mutator, required failed checks)
MUTANTS = {
    "mutant_declared_order_low": (
        lambda r: r.update(declared_order=1.0), ["C4_order"]),
    "mutant_drift_over_budget": (
        lambda r: r.update(energy_drift=[1.0e-3, 5.0e-4, 2.5e-4, 1.2e-4]), ["C7_invariant"]),
    "mutant_cfl_above_margin": (
        lambda r: r.update(cfl=0.95), ["C1_stability"]),
    "mutant_nonfinite_amplitude": (
        lambda r: r.__setitem__("linf_errors", [r["linf_errors"][0], r["linf_errors"][1],
                                                r["linf_errors"][2], float("inf")]),
        ["C1_stability"]),
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def run_tool(argv: list[str]) -> dict:
    proc = subprocess.run([sys.executable, str(TOOL)] + argv, cwd=str(ROOT),
                          capture_output=True, text=True)
    out = {"argv": ["python3", str(TOOL.relative_to(ROOT))] + argv,
           "returncode": proc.returncode, "stderr": proc.stderr.strip()[-400:]}
    try:
        out["result"] = json.loads(proc.stdout)
    except Exception as exc:  # a non-JSON stdout is itself a failure
        out["result"] = None
        out["parse_error"] = f"{type(exc).__name__}: {exc}"
    return out


def grade(measured: dict, expected_verdict: str, required_failed: list[str]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    res = measured.get("result")
    if res is None:
        return False, ["tool produced no parseable JSON"]
    if res.get("verdict") != expected_verdict:
        reasons.append(f"verdict {res.get('verdict')!r} != expected {expected_verdict!r}")
    failed = list(res.get("failed_checks", []))
    for cid in required_failed:
        if cid not in failed:
            reasons.append(f"required failed check {cid} absent (failed={failed})")
    return (not reasons), reasons


def main() -> int:
    tool_hash = sha256_file(TOOL)
    protocol = ROOT / "numerics" / "CONVERGENCE_PROTOCOL.md"
    controls: list[dict] = []
    tmp = Path(tempfile.mkdtemp(prefix="n0-negctl-"))

    try:
        for name, (fname, exp_verdict, req_failed) in FROZEN.items():
            path = PROTOCOL_DIR / fname
            measured = run_tool([str(path)])
            ok, reasons = grade(measured, exp_verdict, req_failed)
            controls.append({
                "name": name, "kind": "frozen", "input_path": str(path.relative_to(ROOT)),
                "input_sha256": sha256_file(path), "expected": {
                    "verdict": exp_verdict, "failed_checks_include": req_failed},
                "measured": measured, "ok": ok, "reasons": reasons})

        standard = json.loads((PROTOCOL_DIR / "demo_report_standard.json").read_text())
        for name, (mutate, req_failed) in MUTANTS.items():
            rep = json.loads(json.dumps(standard))
            mutate(rep)
            p = tmp / f"{name}.json"
            p.write_text(json.dumps(rep, indent=1))
            measured = run_tool([str(p)])
            ok, reasons = grade(measured, "FAIL", req_failed)
            controls.append({
                "name": name, "kind": "manufactured_mutant",
                "source_path": "numerics/protocol/demo_report_standard.json",
                "source_sha256": sha256_file(PROTOCOL_DIR / "demo_report_standard.json"),
                "mutant_sha256": sha256_file(p),
                "expected": {"verdict": "FAIL", "failed_checks_include": req_failed},
                "measured": measured, "ok": ok, "reasons": reasons,
                "note": "input exists only in a temp dir; reproducible from source_sha256 + mutator"})

        # R5 cross-scheme agreement controls
        lffd, cnfd = PROTOCOL_DIR / "report_lffd.json", PROTOCOL_DIR / "report_cnfd.json"
        agree = run_tool(["--compare", str(lffd), str(cnfd)])
        shifted = tmp / "mutant_lffd_order_shifted.json"
        lffd_mut = json.loads(lffd.read_text())
        lffd_mut["fitted_order"] = float(lffd_mut.get("fitted_order", 0.0)) + 0.4
        ou = lffd_mut.get("order_uncertainty") or {}
        ou["fit_order"] = lffd_mut["fitted_order"]
        lffd_mut["order_uncertainty"] = ou
        shifted.write_text(json.dumps(lffd_mut, indent=1))
        disagree = run_tool(["--compare", str(shifted), str(cnfd)])

        def comp_ok(run: dict, expect_agree: bool) -> tuple[bool, list[str]]:
            res = run.get("result")
            if res is None:
                return False, ["tool produced no parseable JSON"]
            reasons = []
            if bool(res.get("agree")) is not expect_agree:
                reasons.append(f"agree={res.get('agree')} != expected {expect_agree}")
            want_rc = 0 if expect_agree else 1
            if run.get("returncode") != want_rc:
                reasons.append(f"returncode {run.get('returncode')} != {want_rc}")
            return (not reasons), reasons

        comps = []
        for name, run, expect in (("compare_lffd_cnfd_agree", agree, True),
                                  ("compare_order_shifted_rejected", disagree, False)):
            ok, reasons = comp_ok(run, expect)
            comps.append({"name": name, "input_paths": run["argv"][2:4],
                          "mutant_sha256": sha256_file(shifted) if not expect else None,
                          "expected_agree": expect, "measured": run, "ok": ok, "reasons": reasons})

        n_checks = len(controls) + len(comps)
        n_ok = sum(1 for c in controls + comps if c["ok"])
        artifact = {
            "schema": SCHEMA,
            "actor": "deepseek-flash-14",
            "instance_id": "worker-014-20260912T001229-897883",
            "class_id": "AF-WCC-SCALAR-SPH",
            "node_id": "N0",
            "gate": "G-NUM",
            "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "audit_tool": {"path": str(TOOL.relative_to(ROOT)), "sha256": tool_hash},
            "anchors_informational": {
                "numerics/CONVERGENCE_PROTOCOL.md": {
                    "sha256_measured_at_build": sha256_file(protocol) if protocol.exists() else None,
                    "note": "moving target during concurrent revision; not load-bearing"}},
            "controls": controls,
            "comparisons": comps,
            "overall": {"pass": n_ok == n_checks, "n_checks": n_checks, "n_ok": n_ok,
                        "n_failed": n_checks - n_ok},
            "falsifier": ("any control here whose measured verdict or failed-check set differs on "
                          "re-run at the recorded audit_tool sha256, or a tool sha256 mismatch, "
                          "invalidates this artifact; a wrong-order or over-budget run that PASSES "
                          "the audit tool falsifies the protocol's failure criteria"),
            "reproduction": f"python3 numerics/protocol/verify_protocol_negative_controls.py  (audit tool sha256 {tool_hash[:12]})",
            "claims_not_made": [
                "no G-NUM verdict or gate self-pass (authority: Astra / audit lead)",
                "no claim that the protocol revision under independent review is accepted",
                "no claim about self-gravity, WCC/SCC, or any physics result",
                "no edit to any other worker's artifact; inputs were read-only"],
            "validation_status": "unverified",
        }
        OUT.write_text(json.dumps(artifact, indent=1))
        print(json.dumps({"artifact": str(OUT.relative_to(ROOT)), "sha256": sha256_file(OUT),
                          "overall": artifact["overall"],
                          "failures": [c["name"] for c in controls + comps if not c["ok"]]}))
        return 0 if artifact["overall"]["pass"] else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
