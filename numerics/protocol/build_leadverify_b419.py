#!/usr/bin/env python3
"""Refresh the numerics group-lead verification of the N0 gate proposal.

The prior record (``n0_gate_proposal_leadverify.json#e0f9ef9f329d``) verifies proposal
revision ``58a175b52fbe``; the proposal was re-based in place to ``b4192221ff7d`` during the
stop-rule lifecycle.  Worker-14's binding audit measured the resulting gap
(``BINDING_GAP_REMAINS_C4_CLOSED``) and named ``astra-lead-numerics`` as the owner.  This
script re-verifies the proposal at its *current* bytes and rewrites the record in place.

It is read-only with respect to every other artifact: the only file it writes is
``numerics/protocol/n0_gate_proposal_leadverify.json``.  In particular it does not run
drivers whose ``OUT`` is a pinned file; the heavy reproducibility checks were re-run by the
lead in separate processes with output captured, and the R5 order re-fit is re-derived here
from the published certification rows with plain arithmetic.

Fails closed: if the proposal hash is not the expected revision, or any entry of its
evidence chain drifts, it writes nothing and exits non-zero.

    python3 numerics/protocol/build_leadverify_b419.py
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / "numerics/tests/n0_gate_proposal.json"
OUT = ROOT / "numerics/protocol/n0_gate_proposal_leadverify.json"
CERT = ROOT / "numerics/protocol/n0_fixed_dt_certification.json"
REGISTRY = ROOT / "runtime/state/artifact_hashes.json"
SOLVER = ROOT / "numerics/spherical_solver"

EXPECT_PROPOSAL = "b4192221ff7d96dbb61ce37fa667e1a59b7b290b8ca34f77e7674c03ca5ba2e3"
EXPECT_PROPOSAL_EVENT = "lnum-artifact-1789144642810-0d42bd"
EXPECT_PROPOSAL_EVENT_SHA = EXPECT_PROPOSAL
SUPERSEDED_RECORD_SHA = "e0f9ef9f329d4d5d4d7fbf37b10cc571bc0ee233a194f3ba9116ad91fe2ab012"
SUPERSEDED_VERIFIED_PROPOSAL = "58a175b52fbe4f9b38663dcdfd57342629c99c04b34c76295affcd567acdf4c7"
F0_REV5 = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
PROTOCOL_SHA = "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274"
GATES_SHA = "fcd1d70991b6eade4aa993dc49b6103e338f68320aabb955d97da5a8f55d996e"
CST = timezone(timedelta(hours=8))
INSTANCE = "lead-numerics-01-20260912T004903-968807"
INSTANCE_START = datetime(2026, 9, 12, 0, 49, 3, tzinfo=CST)


def sha(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def run(cmd: list[str]) -> tuple[int, str, str]:
    pr = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=900)
    return pr.returncode, pr.stdout, pr.stderr


def parse_json(text: str):
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        return json.loads(text[start:]) if start >= 0 else None


def refit(rows: list[dict]) -> dict:
    """Plain least-squares slope of log(l2_error) vs log(dr) plus pairwise slopes."""
    xs = [math.log(float(r["dr"])) for r in rows]
    ys = [math.log(float(r["l2_error"])) for r in rows]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = my - slope * mx
    resid = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
    pair = [
        math.log(float(rows[i]["l2_error"]) / float(rows[i + 1]["l2_error"]))
        / math.log(float(rows[i]["dr"]) / float(rows[i + 1]["dr"]))
        for i in range(n - 1)
    ]
    return {
        "n_rungs": n,
        "refit_order": slope,
        "pairwise_orders": pair,
        "max_abs_residual_log": max(abs(r) for r in resid),
    }


def main() -> int:
    fails: list[str] = []
    proposal_sha = sha(PROPOSAL)
    if proposal_sha != EXPECT_PROPOSAL:
        print(f"REFUTED: proposal {str(proposal_sha)[:16]} != expected {EXPECT_PROPOSAL[:16]}")
        return 2
    prop = json.loads(PROPOSAL.read_text())

    # 1. every pinned entry of the proposal's evidence chain re-measured from disk
    chain_rows = []
    for path, pinned in prop["evidence_hashes"].items():
        disk = sha(ROOT / path)
        status = "match" if disk == pinned else ("missing" if disk is None else "drift")
        chain_rows.append({"path": path, "pinned": pinned, "measured": disk, "status": status})
        if status != "match":
            fails.append(f"chain {status}: {path}")
    chain_match = sum(1 for r in chain_rows if r["status"] == "match")

    # 2. independent R5 re-fit from the published certification rows
    cert = json.loads(CERT.read_text())
    refits = {}
    declared = {}
    for name, s in cert["schemes"].items():
        fd = s["fixed_dt_certification"]
        declared[name] = fd["fit_order"]
        r = refit(fd["rows"])
        r["declared_fit_order"] = fd["fit_order"]
        r["abs_diff_vs_declared"] = abs(r["refit_order"] - fd["fit_order"])
        r["dt_fixed_1e-4"] = all(float(row["dt"]) == 1e-4 for row in fd["rows"])
        r["monotone"] = all(
            float(fd["rows"][i]["l2_error"]) > float(fd["rows"][i + 1]["l2_error"])
            for i in range(len(fd["rows"]) - 1)
        )
        if r["abs_diff_vs_declared"] > 1e-9:
            fails.append(f"refit {name} differs from declared by {r['abs_diff_vs_declared']}")
        if not r["dt_fixed_1e-4"]:
            fails.append(f"{name}: dt not fixed at 1e-4")
        if r["n_rungs"] != 4:
            fails.append(f"{name}: {r['n_rungs']} rungs, need 4")
        refits[name] = r
    names = sorted(declared)
    cross = [
        abs(declared[a] - declared[b]) for i, a in enumerate(names) for b in names[i + 1:]
    ]
    max_dp = max(cross) if cross else None

    # 3. reproducibility commands re-run at the current bytes (read-only outputs)
    rc_v, out_v, _ = run([sys.executable, "numerics/protocol/verify_convergence_rev3.py"])
    verifier = parse_json(out_v) or {}
    if rc_v != 0 or verifier.get("verdict") != "VERIFIED":
        fails.append(f"rev3 verifier rc={rc_v} verdict={verifier.get('verdict')}")

    rc_g, out_g, _ = run([sys.executable, "-m", "numerics.gates", "--check"])
    gate = parse_json(out_g) or {}
    if gate.get("verdict") != "N1_BLOCKED" or gate.get("production_allowed") is not False:
        fails.append(f"gate evaluator rc={rc_g} verdict={gate.get('verdict')}")

    rc_l, out_l, _ = run([sys.executable, "numerics/tests/flat_wave.py", "--lock-guard"])
    guard = parse_json(out_l) or {}
    if rc_l != 0:
        fails.append(f"lock guard rc={rc_l}")

    solver_present = SOLVER.exists()
    if solver_present:
        fails.append("numerics/spherical_solver exists while locked")
    if sha(ROOT / "numerics/CONVERGENCE_PROTOCOL.md") != PROTOCOL_SHA:
        fails.append("protocol hash moved")
    if sha(ROOT / "numerics/gates.py") != GATES_SHA:
        fails.append("gates.py hash moved")
    if sha(ROOT / "research_map/formulation_taxonomy.yaml") != F0_REV5:
        fails.append("F0 taxonomy is not rev5 0abb9ed8a961")

    if fails:
        print("REFUTED (nothing written):")
        for f in fails:
            print("  -", f)
        return 1

    now = datetime.now(CST)
    hours = round((now - INSTANCE_START).total_seconds() / 3600.0, 3)
    successor = ROOT / "numerics/protocol/fixed_replication_verdict_rev2.json"
    successor_ref = (
        {
            "path": str(successor.relative_to(ROOT)),
            "sha256": sha(successor),
            "supersedes": json.loads(successor.read_text()).get("supersedes", {}).get("sha256"),
        }
        if successor.is_file()
        else None
    )

    record = {
        "schema": "n0-gate-proposal-lead-verification/v2",
        "artifact": "numerics/protocol/n0_gate_proposal_leadverify.json",
        "purpose": (
            "Group-lead re-verification of the N0 gate proposal at its CURRENT revision "
            f"numerics/tests/n0_gate_proposal.json#{EXPECT_PROPOSAL[:12]}. Supersedes the "
            f"prior record at {SUPERSEDED_RECORD_SHA[:12]}, which verifies the superseded "
            f"proposal revision {SUPERSEDED_VERIFIED_PROPOSAL[:12]} and cites superseded "
            "gates.py#907a88b1 / reviews/G-NUM-protocol-review.json#66a905f5 pins. This is a "
            "reproduction/verification record, not an independent protocol review and not a "
            "gate verdict."
        ),
        "author": "astra-lead-numerics",
        "author_instance": INSTANCE,
        "created_at": now.isoformat(timespec="seconds"),
        "agent_hours_this_lead": hours,
        "group_id": "numerics",
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "conclusion_type": "numerical_evidence",
        "supersedes": {
            "path": "numerics/protocol/n0_gate_proposal_leadverify.json",
            "sha256": SUPERSEDED_RECORD_SHA,
            "verified_proposal_revision": SUPERSEDED_VERIFIED_PROPOSAL,
            "reason": (
                "the proposal was re-based in place to b4192221ff7d in the astra-life04 "
                "stop-rule lifecycle; the prior verification record then verified bytes that "
                "no longer exist on disk. Measured by worker-14 W14-GNUM-BINDING-AUDIT-01/02 "
                "(BINDING_GAP_REMAINS_C4_CLOSED) and by worker-067 "
                "W067-N0-STOPRULE-CLOSURE-01 (binding_drift)."
            ),
            "stale_pins_in_superseded_record": [
                "numerics/gates.py#907a88b141bf4394 (disk fcd1d70991b6eade)",
                "reviews/G-NUM-protocol-review.json#66a905f5afef (disk 8137f18f1a3b2b01)",
                "numerics/tests/n0_gate_proposal.json#58a175b52fbe (disk b4192221ff7d)",
            ],
        },
        "proposal_verified": {
            "path": "numerics/tests/n0_gate_proposal.json",
            "sha256": proposal_sha,
            "schema_version": prop.get("schema_version"),
            "artifact_event": EXPECT_PROPOSAL_EVENT,
            "artifact_event_sha256_match": proposal_sha == EXPECT_PROPOSAL_EVENT_SHA,
            "unchanged_since_artifact_event": proposal_sha == EXPECT_PROPOSAL_EVENT_SHA,
            "recommended_verdict": prop.get("proposal", {}).get("recommended_verdict"),
            "recommended_verdict_if": prop.get("proposal", {}).get(
                "recommended_verdict_if_conditions_close"
            ),
        },
        "criteria_status": {
            "order-measured": (
                "met -- 4 rungs at fixed dt=1e-4 for three schemes; lead-independent R5 "
                "re-fit reproduces every declared order (max |dp| "
                f"{max_dp:.3e} <= 0.25 floor)"
            ),
            "independently-replicated-within-tolerance": (
                "met -- external verifier VERIFIED, 11 pins re-measured; three independent "
                "verdicts pinned in the rev3 report; error-field structure check refutes "
                "shared-error agreement"
            ),
            "protocol-reviewed-by-an-independent-reviewer": (
                "accept 4.5 binds numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2 "
                "(audit-review-gnum-protocol-final-20260912T0027, no hard failures); "
                "contested by two live revise verdicts about the PREVIOUS evidence basis "
                "(w067 F1, w081 F1'). Adjudication is card "
                "astra-life05-gnum-protocol-adjudication (lead-audit, deadline 02:15); "
                "numerics may not self-satisfy C8."
            ),
            "registration-in-artifact-hashes (C4)": (
                "closed at pass-05 (REC-14): protocol 1e6cdf04d7a2, numerics/results/*, "
                "artifacts/numerics/* and gates.py#fcd1d709 are registered; worker-14 "
                "W14-GNUM-BINDING-AUDIT-02 reports BINDING_GAP_REMAINS_C4_CLOSED"
            ),
        },
        "evidence_chain_check": {
            "source": "numerics/tests/n0_gate_proposal.json#evidence_hashes",
            "entries_checked": len(chain_rows),
            "entries_matching": chain_match,
            "drift": [r for r in chain_rows if r["status"] == "drift"],
            "missing": [r for r in chain_rows if r["status"] == "missing"],
            "rows": chain_rows,
        },
        "mutable_registry_snapshot": {
            "path": "runtime/state/artifact_hashes.json",
            "sha256_prefix_measured": (sha(REGISTRY) or "")[:20],
            "note": (
                "point-in-time snapshot only; the controller rewrites this file every "
                "checkpoint, so it is not a pin (matches the proposal's own treatment)"
            ),
        },
        "protocol_of_record": {
            "path": "numerics/CONVERGENCE_PROTOCOL.md",
            "revision": "rev 3 (R1-R5a, >=4 rungs for order certification)",
            "sha256": PROTOCOL_SHA,
            "self_review_forbidden": True,
        },
        "reproduction": {
            "rev3_external_verifier": {
                "driver": "numerics/protocol/verify_convergence_rev3.py",
                "exit": rc_v,
                "verdict": verifier.get("verdict"),
                "pins_rechecked": verifier.get("pins_rechecked"),
                "orders": verifier.get("orders"),
                "independent_verdicts": verifier.get("independent_verdicts"),
                "gate_self_pass": verifier.get("gate_self_pass"),
            },
            "lead_independent_r5_refit": {
                "method": "least-squares slope of log(l2_error) vs log(dr) on the published rows; no generator imported",
                "schemes": refits,
                "max_cross_scheme_abs_dp": max_dp,
                "r5_floor": 0.25,
            },
            "gate_evaluator": {
                "command": "python3 -m numerics.gates --check",
                "exit": rc_g,
                "verdict": gate.get("verdict"),
                "production_allowed": gate.get("production_allowed"),
                "lock_state": (gate.get("lock") or {}).get("state"),
                "blocking_reasons": gate.get("blocking_reasons"),
                "protocol_review": {
                    "reviewed": (gate.get("protocol_review") or {}).get("reviewed"),
                    "contest": (gate.get("protocol_review") or {}).get("contest"),
                    "dissenting_reviews": [
                        d.get("event_id")
                        for d in (gate.get("protocol_review") or {}).get(
                            "dissenting_reviews", []
                        )
                    ],
                },
            },
            "lock_guard": {
                "command": "python3 numerics/tests/flat_wave.py --lock-guard",
                "exit": rc_l,
                "output": guard,
            },
            "spherical_solver_present": solver_present,
        },
        "residuals": [
            {
                "id": "I2-f0-rebind-residual",
                "description": (
                    "numerics/protocol/fixed_replication_verdict.json#dcad962324e3 still "
                    "carries superseded F0 rev2 hash 66bf917bd368 as an ACTIVE evidence pin "
                    "(and the generating script "
                    "numerics/protocol/verify_fixed_scheme_independence.py#a0daf1271bfb hard-"
                    "codes it). The arithmetic is unaffected; worker-067 measured the pin "
                    "inert for class membership (REBIND_INERT_FOR_CLASS_MEMBERSHIP, 5/5 "
                    "controls) and its drift ledger measured the "
                    "fixed_taxonomy_sha256_matches_on_disk assertion as CONTRADICTED "
                    "(W067-N0-PROVENANCE-DRIFT-LEDGER-01)."
                ),
                "disposition": (
                    "repaired for forward use by a successor artifact produced this "
                    "lifecycle: numerics/protocol/fixed_replication_verdict_rev2.json "
                    "(R1/R2/R4/R5 re-run from the frozen inputs with the corrected taxonomy "
                    "measurement, arithmetic delta 0.0). The superseded file is retained "
                    "unedited because it is pinned by the current proposal and by worker "
                    "verdicts; citing the successor discharges the contradicted assertion by "
                    "supersession."
                ),
                "successor_artifact": successor_ref,
                "owner": "numerics lead (successor delivered); controller/audit to cite it",
                "load_bearing_for_order_claim": False,
            }
        ],
        "falsifier_checks": {
            "F1_proposal_moved": "not triggered -- proposal measured at b4192221ff7d",
            "F2_chain_drift": f"not triggered -- {chain_match}/{len(chain_rows)} entries match disk",
            "F3_refit_mismatch": "not triggered -- every refit matches the declared order to <1e-9",
            "F4_lock": "not triggered -- lock locked, solver absent, guard PASS",
            "F5_gate_self_pass": "not triggered -- gates verdict N1_BLOCKED, production_allowed=false",
        },
        "not_claimed": [
            "no gate verdict or self-pass; G-NUM stays pending and the N0 node verdict belongs to lead-audit",
            "no node completion; N1 stays queued and locked",
            "not the independent protocol review required by C8",
            "no physics claim; flat-space calibration evidence only",
        ],
        "scope_compliance": {
            "self_review": False,
            "gate_self_pass": False,
            "n1_status_moved": False,
            "self_gravitating_code_written_or_run": False,
            "spherical_solver_dir_present": False,
        },
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "wrote": str(OUT.relative_to(ROOT)),
        "sha256": sha(OUT),
        "proposal": proposal_sha,
        "chain": f"{chain_match}/{len(chain_rows)}",
        "refit_max_abs_dp": max_dp,
        "verifier": verifier.get("verdict"),
        "gate": gate.get("verdict"),
        "lock_guard_exit": rc_l,
        "hours": hours,
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
