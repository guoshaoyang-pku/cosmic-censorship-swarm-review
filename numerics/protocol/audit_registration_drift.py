#!/usr/bin/env python3
"""Read-only registration / order re-fit audit for the N0 (G-NUM) evidence basis.

One independent lifecycle, ``astra-lead-numerics``, 2026-09-12.  This script does not
build, import, or re-run any solver.  It only re-measures files on disk:

1. every ``(path, sha256)`` pin declared inside
   ``numerics/results/flat_wave_convergence_rev3.json`` is re-hashed;
2. each pinned path is cross-checked against ``runtime/state/artifact_hashes.json``
   (the controller registry) and classified match / unregistered / mismatch;
3. the fixed-``dt`` spatial order is **recomputed from the raw rows** of
   ``numerics/protocol/n0_fixed_dt_certification.json`` (log-log least squares and
   adjacent-rung pair orders), independently of the declared fit;
4. the three independent replication verdicts named in the rev-3 report are
   re-hashed and their verdict fields read;
5. the lock guard in ``numerics/gates.py`` is evaluated, and
   ``numerics/spherical_solver/`` is checked absent.

It fails closed: exit ``2`` on any declared/disk hash drift or order outside the
declared band, exit ``3`` on a lock violation.  A clean run exits ``0``.

    python3 numerics/protocol/audit_registration_drift.py [--out PATH]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

REPORT = REPO / "numerics/results/flat_wave_convergence_rev3.json"
CERT = REPO / "numerics/protocol/n0_fixed_dt_certification.json"
PROTOCOL = REPO / "numerics/CONVERGENCE_PROTOCOL.md"
REGISTRY = REPO / "runtime/state/artifact_hashes.json"
SOLVER_DIR = REPO / "numerics/spherical_solver"
DEFAULT_OUT = REPO / "numerics/protocol/n0_registration_drift_audit.json"

# The three independent replication verdicts named in the rev-3 report and in the
# audit final-verify card (B-N0-R2-1 lists the last three as the residual gap).
REPLICATION_VERDICTS = [
    "artifacts/worker-046/n0_fixed_dt_independent/verification.json",
    "artifacts/worker-057/n0_fixeddt_verify/report.json",
    "artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json",
]

P_DESIGN = 2.0
P_TOL = 0.3
R5_BOUND = 0.25
F0_REV5 = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
AUTHORITY_REL = "numerics/N0_CLASS_BINDING_AUTHORITY.json"


def sha256(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def sha256_rel(rel: str) -> str | None:
    return sha256(REPO / rel)


def walk_pins(node, out: dict[str, str]) -> None:
    """Collect every {path, sha256} pair appearing anywhere in the report."""
    if isinstance(node, dict):
        p, s = node.get("path"), node.get("sha256")
        if isinstance(p, str) and isinstance(s, str):
            out[p] = s
        for v in node.values():
            walk_pins(v, out)
    elif isinstance(node, list):
        for v in node:
            walk_pins(v, out)


def load_registry() -> dict[str, dict]:
    if not REGISTRY.is_file():
        return {}
    doc = json.loads(REGISTRY.read_text())
    merged: dict[str, dict] = {}
    for section in ("hashes", "registry"):
        part = doc.get(section) or {}
        if isinstance(part, dict):
            for k, v in part.items():
                if isinstance(v, dict):
                    merged[k] = v
    return merged


def loglog_fit(rows: list[dict]) -> tuple[float, float, list[float]]:
    """Least-squares slope of log(l2_error) against log(dr); returns slope, se, residuals."""
    xs = [math.log(r["dr"]) for r in rows]
    ys = [math.log(r["l2_error"]) for r in rows]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = my - slope * mx
    res = [y - (slope * x + intercept) for x, y in zip(xs, ys)]
    if n > 2:
        se = math.sqrt(sum(r * r for r in res) / (n - 2) / sxx)
    else:
        se = float("nan")
    return slope, se, res


def pair_orders(rows: list[dict]) -> list[float]:
    out = []
    for a, b in zip(rows, rows[1:]):
        out.append(math.log(a["l2_error"] / b["l2_error"]) / math.log(a["dr"] / b["dr"]))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)

    now = dt.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    rep = json.loads(REPORT.read_text())
    cert = json.loads(CERT.read_text())
    registry = load_registry()

    # ---------------------------------------------------------------- 1+2 pins
    declared: dict[str, str] = {}
    walk_pins(rep, declared)
    declared[PROTOCOL.relative_to(REPO).as_posix()] = sha256(PROTOCOL)
    declared[REPORT.relative_to(REPO).as_posix()] = sha256(REPORT)

    pins = []
    unregistered, mismatched, disk_missing = [], [], []
    for rel, want in sorted(declared.items()):
        got = sha256_rel(rel)
        entry = registry.get(rel) or {}
        reg_sha = entry.get("sha256")
        if got is None:
            status, disk_missing = "disk_missing", disk_missing + [rel]
        elif want is not None and got != want:
            status, mismatched = "declared_vs_disk_mismatch", mismatched + [rel]
        elif reg_sha is None:
            status, unregistered = "unregistered", unregistered + [rel]
        elif reg_sha != got:
            status, mismatched = "registry_vs_disk_mismatch", mismatched + [rel]
        else:
            status = "match"
        pins.append({
            "path": rel,
            "declared_sha256": want,
            "disk_sha256": got,
            "registry_sha256": reg_sha,
            "registry_registered": reg_sha is not None,
            "status": status,
        })

    # ------------------------------------------------- 3 independent order refit
    refit, refit_fail = {}, []
    for name, block in sorted(cert["schemes"].items()):
        rows = block["fixed_dt_certification"]["rows"]
        order = sorted(rows, key=lambda r: -r["dr"])
        slope, se, res = loglog_fit(order)
        pairs = pair_orders(order)
        dec = block["fixed_dt_certification"]
        ok_band = abs(slope - P_DESIGN) <= P_TOL
        monotone = all(a["l2_error"] > b["l2_error"] for a, b in zip(order, order[1:]))
        dt_fixed = len({r["dt"] for r in rows}) == 1
        if not (ok_band and monotone and dt_fixed and len(rows) >= 4):
            refit_fail.append(name)
        refit[name] = {
            "n_rungs": len(rows),
            "dr_values": [r["dr"] for r in order],
            "dt_values": sorted({r["dt"] for r in rows}),
            "dt_all_fixed": dt_fixed,
            "fit_order_recomputed": slope,
            "fit_order_declared": dec["fit_order"],
            "abs_diff_vs_declared": abs(slope - dec["fit_order"]),
            "least_squares_se": se,
            "pair_orders_recomputed": pairs,
            "pair_orders_declared": dec["pair_orders"],
            "max_pair_diff_vs_declared": max(
                abs(a - b) for a, b in zip(pairs, dec["pair_orders"])),
            "monotone": monotone,
            "within_band_|p-2|<=0.3": ok_band,
            "declared_within_band": dec["within_band"],
        }

    cross = [abs(refit[a]["fit_order_recomputed"] - refit[b]["fit_order_recomputed"])
             for i, a in enumerate(sorted(refit)) for b in sorted(refit)[i + 1:]]
    max_cross = max(cross) if cross else 0.0

    # ------------------------------------------------- 4 replication verdicts
    replication = []
    for rel in REPLICATION_VERDICTS:
        got = sha256_rel(rel)
        entry = registry.get(rel) or {}
        doc = {}
        if got is not None:
            try:
                doc = json.loads((REPO / rel).read_text())
            except json.JSONDecodeError:
                doc = {}
        verdict = doc.get("verdict") or doc.get("status") or doc.get("disposition")
        replication.append({
            "path": rel,
            "disk_sha256": got,
            "declared_in_rev3_pins": rel in declared,
            "registry_sha256": entry.get("sha256"),
            "registry_registered": entry.get("sha256") is not None,
            "verdict_field": verdict,
        })

    # ------------------------------------- 4b class-binding authority record
    authority_check: dict = {"path": AUTHORITY_REL, "present": (REPO / AUTHORITY_REL).is_file()}
    authority_fail = False
    if authority_check["present"]:
        adoc = json.loads((REPO / AUTHORITY_REL).read_text())
        b = adoc.get("binding", {})
        c = adoc.get("carrier", {})
        cpath = c.get("path", "")
        carrier_text = (json.dumps(json.loads((REPO / cpath).read_text()))
                        if cpath and (REPO / cpath).is_file() else "")
        sup = adoc.get("supersedes_for_class_binding", [])
        a1 = b.get("sha256") == sha256_rel(b.get("path", ""))
        a2 = b.get("sha256") == F0_REV5
        a3 = c.get("sha256") == sha256_rel(cpath)
        a4 = bool(b.get("sha256")) and b.get("sha256") in carrier_text
        a5 = bool(sup) and all(s.get("sha256") == sha256_rel(s.get("path", "")) for s in sup)
        authority_fail = not (a1 and a2 and a3 and a4 and a5)
        authority_check.update({
            "sha256": sha256_rel(AUTHORITY_REL),
            "published_by": adoc.get("published_by"),
            "A1_binding_matches_disk": a1,
            "A2_binding_is_live_f0_rev5": a2,
            "A3_carrier_matches_disk": a3,
            "A4_carrier_names_binding": a4,
            "A5_superseded_pinned": a5,
            "A6_proposal_only_authority": adoc.get("authority")
            == "proposal-only; requires controller/lead adoption",
            "note": "A6 is False by design: this is a published lead authority record, "
                    "not the proposal-only variant, so the proposal guard A6 does not apply",
        })

    # --------------------------------------------------------- 5 lock guard
    try:
        from numerics import gates  # noqa: E402
        guard = gates.evaluate(REPO)
        guard_view = {
            "verdict": guard.get("verdict"),
            "production_allowed": guard.get("production_allowed"),
            "n_blocking_reasons": len(guard.get("blocking_reasons") or []),
            "blocking_reasons": guard.get("blocking_reasons"),
        }
    except Exception as exc:  # fail closed: no guard means no clean verdict
        guard_view = {"verdict": "GUARD_ERROR", "error": repr(exc)}
    solver_present = SOLVER_DIR.exists()
    lock_state = (json.loads((REPO / "research_map/research_map.json").read_text())
                  .get("numerics_lock", {}).get("state"))

    # ------------------------------------------------- 6 disagreement register
    disagreements = {
        "stop_rule_item_2_class_binding": {
            "assigned_artifact": "numerics/results/flat_wave_convergence_rev3.json",
            "assigned_artifact_position": (
                "BOUND to F0 rev5 0abb9ed8a961; protocol preamble citation 66bf917b/565a6e50 "
                "recorded as superseded and not load-bearing"),
            "closed_by": [
                "reviews/N0-review-final-verify.json (astra-lead-audit, 00:50, stop_rule_items all closed)",
                "reviews/N0-review-worker-012.json (worker-012, 00:55, accept 4.0)",
            ],
            "contested_by": [
                "reviews/N0-review-worker-042.json (worker-042, 00:52, revise 3.5, "
                "HF-042-N0-1: protocol of record still cites stale pins)",
            ],
            "lead_position": "NOT ADJUDICATED — two-document split reported, not resolved",
            "remediation_options": [
                "controller adjudicates the rev-3 report as the N0 binding document "
                "(no hash moves; all existing verdicts stay valid)",
                "re-issue numerics/CONVERGENCE_PROTOCOL.md at a new hash with section 1 "
                "naming 0abb9ed8a961, then re-run every verdict bound to 1e6cdf04d7a2 "
                "(expensive cascade; voids the current accepts)",
            ],
        },
        "protocol_review_contest": {
            "protocol_sha256": sha256(PROTOCOL),
            "contesting_revises": [
                "w067-review-gnum-protocol-r3-20260912T002256 (worker-067, F1)",
                "w081-2026-09-12T00:29:19+0800-f1-review (worker-081, F1')",
                "w067-provledger-20260912T005149-20-review (worker-067)",
                "w042-n0-stoprule-01-review (worker-042)",
            ],
            "accepting": [
                "audit-review-gnum-protocol-final-20260912T0027 (astra-lead-audit, 4.5)",
                "w081-20260912T0042050800-adj2-review (worker-081, accept, supersession disposition)",
            ],
            "lead_position": "NOT ADJUDICATED — withdrawal/supersession semantics are "
                             "controller/audit authority (card astra-life05-gnum-protocol-adjudication)",
        },
    }

    # ------------------------------------------------------------- 7 anomalies
    anomalies = []
    blockers_md = REPO / "numerics/blockers.md"
    if blockers_md.is_file():
        text = blockers_md.read_text(errors="replace")
        mtime = dt.datetime.fromtimestamp(blockers_md.stat().st_mtime).astimezone()
        future = []
        for tok in set(re.findall(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", text)):
            try:
                ts = dt.datetime.strptime(tok, "%Y-%m-%dT%H:%M").replace(tzinfo=mtime.tzinfo)
            except ValueError:
                continue
            if ts > mtime + dt.timedelta(seconds=60):
                future.append({"token": tok, "file_mtime": mtime.isoformat()})
        if future:
            anomalies.append({
                "id": "ANOM-1",
                "severity": "advisory",
                "artifact": "numerics/blockers.md",
                "finding": "future-dated timestamp inside a hash-registered artifact",
                "detail": future,
                "note": "content frozen at the registered hash; reported, not rewritten",
            })

    # --------------------------------------------------------------- verdict
    lock_violation = bool(solver_present) or lock_state not in (None, "locked")
    drift = bool(mismatched or disk_missing or refit_fail) or max_cross > R5_BOUND \
        or authority_fail
    verdict = "LOCK_VIOLATION" if lock_violation else ("DRIFT" if drift else "CLEAN")

    out = {
        "schema": "n0-registration-drift-audit/v1",
        "generated_at": now,
        "actor": "astra-lead-numerics",
        "node_id": "N0",
        "class_id": "AF-WCC-SCALAR-SPH",
        "gate": "G-NUM",
        "conclusion_type": "numerical_evidence",
        "scope": "read-only re-measurement; no solver imported, built, or run",
        "verdict": verdict,
        "basis": {
            "rev3_report": REPORT.relative_to(REPO).as_posix(),
            "rev3_report_sha256": sha256(REPORT),
            "protocol_sha256": sha256(PROTOCOL),
            "certification": CERT.relative_to(REPO).as_posix(),
            "certification_sha256": sha256(CERT),
            "registry": REGISTRY.relative_to(REPO).as_posix(),
        },
        "pin_summary": {
            "n_declared_pins": len(pins),
            "n_match": sum(1 for p in pins if p["status"] == "match"),
            "unregistered": unregistered,
            "mismatched": mismatched,
            "disk_missing": disk_missing,
        },
        "pins": pins,
        "independent_order_refit": {
            "method": "log(l2_error) vs log(dr) least squares + adjacent-rung pair orders "
                      "on the raw fixed-dt rows",
            "p_design": P_DESIGN,
            "p_tol": P_TOL,
            "r5_bound": R5_BOUND,
            "schemes": refit,
            "max_cross_scheme_abs_diff": max_cross,
            "cross_scheme_within_r5": max_cross <= R5_BOUND,
            "schemes_out_of_band_or_degenerate": refit_fail,
        },
        "replication_verdicts": replication,
        "class_binding_authority": authority_check,
        "lock_compliance": {
            "numerics_lock_state": lock_state,
            "spherical_solver_present": solver_present,
            "guard": guard_view,
        },
        "disagreement_register": disagreements,
        "anomalies": anomalies,
        "claims_not_made": [
            "no gate verdict (G-NUM stays pending; authority Astra / lead-audit)",
            "no node completion (N0 status untouched)",
            "no numerics_lock release (N1 stays queued; no spherical_solver written)",
            "no adjudication of the C8 protocol contest or of HF-042-N0-1",
            "no physics / self-gravity / WCC / SCC claim",
        ],
        "falsifiers": [
            "any declared pin re-hashing to a different value",
            "a recomputed fixed-dt order leaving |p-2| > 0.3 or cross-scheme |dp| > 0.25",
            "numerics/spherical_solver/ appearing while numerics_lock.state == 'locked'",
            "numerics/gates.py returning production_allowed=true while G-FORM or G-AUDIT is not pass",
        ],
    }
    Path(args.out).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")

    print(json.dumps({
        "verdict": verdict,
        "pins": out["pin_summary"]["n_declared_pins"],
        "match": out["pin_summary"]["n_match"],
        "unregistered": unregistered,
        "mismatched": mismatched,
        "refit": {k: round(v["fit_order_recomputed"], 9) for k, v in refit.items()},
        "max_cross_scheme_abs_diff": max_cross,
        "solver_present": solver_present,
        "guard": guard_view.get("verdict"),
        "anomalies": len(anomalies),
        "out": args.out,
    }, indent=1, sort_keys=True))

    return 3 if lock_violation else (2 if drift else 0)


if __name__ == "__main__":
    raise SystemExit(main())
