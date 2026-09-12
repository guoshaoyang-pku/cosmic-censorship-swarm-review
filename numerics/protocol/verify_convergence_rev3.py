#!/usr/bin/env python3
"""Independent verifier for ``numerics/results/flat_wave_convergence_rev3.json``.

Does not import the builder or any solver. Re-measures every pinned sha256 from disk,
re-extracts the certified orders from the certification artifact, and re-checks the
stop-rule predicates. Exit 0 = verified, exit 1 = refuted (prints the reason).

    python3 numerics/protocol/verify_convergence_rev3.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REPORT = REPO / "numerics/results/flat_wave_convergence_rev3.json"
CERT = REPO / "numerics/protocol/n0_fixed_dt_certification.json"
F0 = REPO / "research_map/formulation_taxonomy.yaml"
F0_REV5_SHA = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
SOLVER = REPO / "numerics/spherical_solver"

fails: list[str] = []


def sha(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def walk_pins(node, out: list[tuple[str, str]]) -> None:
    if isinstance(node, dict):
        if isinstance(node.get("path"), str) and isinstance(node.get("sha256"), str):
            out.append((node["path"], node["sha256"]))
        for v in node.values():
            walk_pins(v, out)
    elif isinstance(node, list):
        for v in node:
            walk_pins(v, out)


def main() -> int:
    if not REPORT.is_file():
        print("REFUTED: report missing")
        return 1
    rep = json.loads(REPORT.read_text())
    cert = json.loads(CERT.read_text())

    # 1. every (path, sha256) pin in the report re-measured
    pins: list[tuple[str, str]] = []
    walk_pins(rep, pins)
    seen = set()
    for path, pinned in pins:
        if (path, pinned) in seen:
            continue
        seen.add((path, pinned))
        disk = sha(REPO / path)
        if disk != pinned:
            fails.append(f"pin mismatch {path}: report {pinned[:16]} disk {str(disk)[:16]}")

    # 2. certified orders re-extracted from the certification artifact
    claim = rep["order_claim"]["p_by_scheme"]
    for name, declared in claim.items():
        got = cert["schemes"][name]["fixed_dt_certification"]["fit_order"]
        if got != declared:
            fails.append(f"order mismatch {name}: report {declared} cert {got}")
        rows = cert["schemes"][name]["fixed_dt_certification"]["rows"]
        if len(rows) != 4:
            fails.append(f"{name}: {len(rows)} rungs, need 4")
        if {float(r["dt"]) for r in rows} != {1e-4}:
            fails.append(f"{name}: dt not fixed at 1e-4")

    # 3. F0 rev5 binding
    if sha(F0) != F0_REV5_SHA:
        fails.append("F0 taxonomy hash is not rev5 0abb9ed8a961")
    if rep["class_binding"]["sha256"] != F0_REV5_SHA:
        fails.append("report class binding does not pin F0 rev5")

    # 4. scope: no solver directory while locked
    if SOLVER.exists():
        fails.append("numerics/spherical_solver exists while numerics_lock is locked")

    # 5. the three independent verdicts are the pinned ones with the pinned verdicts
    want = {"worker-046": "SUPPORTED", "worker-057": "REPRODUCED", "worker-081": "accept"}
    got = {v["reviewer"]: v["verdict"] for v in rep["independent_replication"]["verdicts"]}
    if got != want:
        fails.append(f"independent verdicts {got} != {want}")

    # 6. the report is not a gate self-pass
    if rep["lock_guard"]["production_allowed"] is not False:
        fails.append("report does not record production_allowed=false")

    if fails:
        print("REFUTED:")
        for f in fails:
            print("  -", f)
        return 1
    print(json.dumps({
        "verdict": "VERIFIED",
        "report": str(REPORT.relative_to(REPO)),
        "report_sha256": sha(REPORT),
        "pins_rechecked": len(seen),
        "orders": claim,
        "independent_verdicts": got,
        "solver_dir_present": False,
        "gate_self_pass": False,
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
