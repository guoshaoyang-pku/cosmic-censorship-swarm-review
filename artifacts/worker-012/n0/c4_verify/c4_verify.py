#!/usr/bin/env python3
"""
worker-012 / deepseek-flash-12 bounded verification pass -- 2026-09-12 ~00:30 +08:00

TASK (one class-bound task, class AF-WCC-SCALAR-SPH, node N0, gate G-NUM)
    Independently verify numerics/protocol/n0_c4_registration_manifest.json, the
    C4 registration package for the last named worker-side precondition of G-NUM
    (PROTOCOL.md rule 2: a node is done only when its declared artifact carries a
    sha256 in runtime/state/artifact_hashes.json).  The manifest was authored by
    deepseek-flash-14 at 00:24:56; no independent measurement of it exists yet.

WHAT THIS SCRIPT DOES (read-only over the repository)
    M*  manifest integrity (schema, counts, hash record)
    A*  every anchor named by the manifest: existence, sha256, byte count,
        published-prefix match, and live registry state
    R*  registry cross-check for the three REGISTER-requested anchors
    F*  FIXED replication run: recompute order fits, pair orders, monotonicity
        from the raw per-rung rows
    L*  lead 4-rung addendum: recompute 3/4-rung fits, least-squares SE,
        pair-spread half-range, reported delta = max(SE, half-range)
    X*  cross-consistency FIXED 3-rung vs addendum 3-rung; protocol order band;
        R5 pair-agreement rule |pA-pB| <= max(0.25, sqrt(dA^2+dB^2))
    S*  three-scheme 4-rung reports: recompute fitted order / SE / delta and
        check every scheme declares a non-null solver_tolerance
    K*  lock state: map numerics_lock == locked, numerics/spherical_solver absent,
        lock guard present

WHAT IT DOES NOT DO
    * no write anywhere except stdout; the caller captures the JSON report
    * no registration into runtime/state/artifact_hashes.json (controller-owned)
    * no gate verdict, no node status (Astra-owned)
    * no re-run of the three-scheme builder: it writes reports into registered
      paths, so a read-only worker pass must not invoke it; the manifest's
      "deterministic_rebuild" clause is therefore recorded as NOT re-executed
      here, and the builder's *outputs* are instead re-derived from raw rows.

Exit code 0 iff every check passes; 1 otherwise (FAIL CLOSED: an unreadable or
mutating input is a failure, never a pass).
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

TOL = 1e-9  # absolute reproduction tolerance for stored floating point statistics
CST = timezone(timedelta(hours=8))


def find_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "research_map" / "research_map.json").is_file():
            return p
    raise SystemExit("repo root not found from %s" % start)


ROOT = find_root(Path(__file__).resolve())
HERE = Path(__file__).resolve().parent

MANIFEST = "numerics/protocol/n0_c4_registration_manifest.json"
REGISTRY = "runtime/state/artifact_hashes.json"
MAP = "research_map/research_map.json"
FIXED = "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json"
LEAD4 = "artifacts/numerics/n0/lead_4rung_replication.json"
SUMMARY = "numerics/protocol/three_scheme_r1r5_summary.json"
REPORTS = {s: "numerics/protocol/report_%s_4rung.json" % s for s in ("lffd", "cnfd", "cnfem")}
PROTOCOL = "numerics/CONVERGENCE_PROTOCOL.md"
FROZEN_MODULE = "numerics/tests/flat_wave_replication.py"
GUARD = "numerics/tests/selfgravity_lock_guard.py"
SOLVER_DIR = "numerics/spherical_solver"

CHECKS = []


def sha256_file(rel: str):
    p = ROOT / rel
    if not p.is_file():
        return None, None
    h = hashlib.sha256()
    n = 0
    with open(p, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
            n += len(block)
    return h.hexdigest(), n


def read_stable_json(rel: str):
    """Read a JSON file twice; return (obj, sha, bytes, stable). stable=False on drift."""
    p = ROOT / rel
    if not p.is_file():
        return None, None, None, False
    b1 = p.read_bytes()
    s1 = hashlib.sha256(b1).hexdigest()
    try:
        obj = json.loads(b1)
    except Exception as exc:  # noqa: BLE001
        return None, s1, len(b1), False
    b2 = p.read_bytes()
    s2 = hashlib.sha256(b2).hexdigest()
    return obj, s1, len(b1), (s1 == s2)


def check(cid, desc, expected, measured, ok, detail=None):
    entry = {
        "id": cid,
        "description": desc,
        "expected": expected,
        "measured": measured,
        "pass": bool(ok),
    }
    if detail is not None:
        entry["detail"] = detail
    CHECKS.append(entry)
    return bool(ok)


def close(a, b, tol=TOL):
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) <= tol


def ols(rows, xkey, ykey):
    """Independent OLS fit of ln(y) on ln(x); returns (slope, se_slope, pair_orders, monotone)."""
    xs = [math.log(float(r[xkey])) for r in rows]
    ys = [math.log(float(r[ykey])) for r in rows]
    n = len(xs)
    xb = sum(xs) / n
    yb = sum(ys) / n
    sxx = sum((x - xb) ** 2 for x in xs)
    sxy = sum((x - xb) * (y - yb) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = yb - slope * xb
    sse = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    se = math.sqrt((sse / (n - 2)) / sxx) if n > 2 else None
    pairs = [
        (ys[i] - ys[i + 1]) / (xs[i] - xs[i + 1]) for i in range(n - 1)
    ]
    monotone = all(rows[i][ykey] > rows[i + 1][ykey] for i in range(n - 1))
    return slope, se, pairs, monotone


def main() -> int:
    manifest, man_sha, man_bytes, man_stable = read_stable_json(MANIFEST)
    check(
        "M1-manifest-readable",
        "manifest readable and byte-stable across a double read",
        "readable, stable",
        {"sha256": man_sha, "bytes": man_bytes, "stable": man_stable},
        manifest is not None and man_stable,
    )
    if manifest is None or not man_stable:
        report(man_sha, man_bytes, None)
        return 1

    check(
        "M2-manifest-schema",
        "manifest schema id",
        "n0-c4-registration-manifest/v1",
        manifest.get("schema"),
        manifest.get("schema") == "n0-c4-registration-manifest/v1",
    )
    rr = manifest.get("registration_request", [])
    ar = manifest.get("already_registered", [])
    va = manifest.get("verified_anchors", [])
    check(
        "M3-registration-request-count",
        "registration_request count matches declared count and REGISTER anchors",
        {"declared": manifest.get("registration_request_count"), "list": 3, "verify": 3},
        {"declared": manifest.get("registration_request_count"), "list": len(rr), "verify": len(va)},
        manifest.get("registration_request_count") == 3
        and len(rr) == 3
        and sum(1 for a in va if a.get("action") == "REGISTER") == 3,
    )
    check(
        "M4-manifest-claims-flags",
        "manifest self-declared flags anchors_ok / rebuild_ok",
        {"anchors_ok": True, "rebuild_ok": True},
        {"anchors_ok": manifest.get("anchors_ok"), "rebuild_ok": manifest.get("rebuild_ok")},
        manifest.get("anchors_ok") is True and manifest.get("rebuild_ok") is True,
    )
    check(
        "M5-manifest-class-binding",
        "manifest class/node/gate binding",
        {"class_id": "AF-WCC-SCALAR-SPH", "node_id": "N0", "gate": "G-NUM"},
        {
            "class_id": manifest.get("class_id"),
            "node_id": manifest.get("node_id"),
            "gate": manifest.get("gate"),
        },
        manifest.get("class_id") == "AF-WCC-SCALAR-SPH"
        and manifest.get("node_id") == "N0"
        and manifest.get("gate") == "G-NUM",
    )

    # ---------------- A: anchor audit -------------------------------------
    registry, reg_sha, reg_bytes, reg_stable = read_stable_json(REGISTRY)
    reg_map = (registry or {}).get("registry", {})
    hash_map = (registry or {}).get("hashes", {})
    check(
        "A0-registry-readable",
        "artifact_hashes.json readable and byte-stable",
        "readable, stable",
        {"sha256": reg_sha, "bytes": reg_bytes, "stable": reg_stable},
        registry is not None and reg_stable,
    )

    measured = {}
    for a in va:
        rel = a.get("path")
        ms, mb = sha256_file(rel)
        measured[rel] = {"sha256": ms, "bytes": mb}
        reg = reg_map.get(rel)
        ok = bool(a.get("exists_on_disk")) == (ms is not None)
        ok &= ms == a.get("measured_sha256")
        ok &= mb == a.get("measured_bytes")
        ok &= bool(a.get("published_prefix_match")) == bool(
            ms and ms.startswith(str(a.get("published_prefix") or "\0"))
        )
        if a.get("registry_status") == "registered":
            ok &= reg is not None and reg.get("sha256") == ms and reg.get("bytes") == mb
        if reg is not None:  # current live state must never disagree with measured bytes
            ok &= reg.get("sha256") == ms and reg.get("bytes") == mb
        check(
            "A-" + rel,
            "anchor %s (%s)" % (rel, a.get("action")),
            {
                "sha256": a.get("measured_sha256"),
                "bytes": a.get("measured_bytes"),
                "prefix": a.get("published_prefix"),
                "registry_status_at_manifest": a.get("registry_status"),
            },
            {
                "sha256": ms,
                "bytes": mb,
                "registry_now": (
                    None
                    if reg is None
                    else {"sha256": reg.get("sha256"), "bytes": reg.get("bytes")}
                ),
            },
            ok,
        )

    # ---------------- R: live registration state of the 3 requests -------
    for req in rr:
        rel = req.get("path")
        reg = reg_map.get(rel)
        m = measured.get(rel, {})
        if reg is None:
            check(
                "R-" + rel,
                "registration state (manifest requested REGISTER)",
                {"manifest": req.get("published_prefix"), "registry_now": "absent"},
                {"registry_now": "absent", "measured": m.get("sha256")},
                True,
                detail="still absent at verification time; registration remains open and is controller-owned",
            )
        else:
            check(
                "R-" + rel,
                "registration state: registered sha must equal measured sha",
                {"registry": m.get("sha256")},
                {"registry": reg.get("sha256"), "bytes": reg.get("bytes")},
                reg.get("sha256") == m.get("sha256") and reg.get("bytes") == m.get("bytes"),
            )

    # ---------------- F: recompute FIXED replication run ------------------
    fixed, fixed_sha, fixed_bytes, fixed_stable = read_stable_json(FIXED)
    check(
        "F0-fixed-readable",
        "FIXED replication report readable and byte-stable",
        "readable, stable",
        {"sha256": fixed_sha, "bytes": fixed_bytes, "stable": fixed_stable},
        fixed is not None and fixed_stable,
    )
    fixed_orders = {}
    if fixed:
        for st in fixed.get("order_studies", []):
            s = st.get("scheme")
            slope, _se, pairs, mono = ols(st["rows"], "dr", "l2_error")
            fixed_orders[s] = slope
            check(
                "F-%s-order" % s,
                "FIXED 3-rung fit/pairs/monotone recomputed from raw rows (%s)" % s,
                {
                    "fit_order": st.get("fit_order"),
                    "pair_orders": st.get("pair_orders"),
                    "monotone": st.get("monotone"),
                },
                {"fit_order": slope, "pair_orders": pairs, "monotone": mono},
                close(slope, st.get("fit_order"))
                and all(close(p, q) for p, q in zip(pairs, st.get("pair_orders", [])))
                and len(pairs) == len(st.get("pair_orders", []))
                and mono == st.get("monotone"),
            )

    # ---------------- L: recompute lead 4-rung addendum -------------------
    lead, lead_sha, lead_bytes, lead_stable = read_stable_json(LEAD4)
    check(
        "L0-lead-readable",
        "lead 4-rung addendum readable and byte-stable",
        "readable, stable",
        {"sha256": lead_sha, "bytes": lead_bytes, "stable": lead_stable},
        lead is not None and lead_stable,
    )
    lead_orders4 = {}
    lead_deltas = {}
    if lead:
        for s, st in lead.get("studies", {}).items():
            rows = st["rows"]
            f3, se3, _pairs3, _mono3 = ols(rows[:3], "dr", "l2_error")
            f4, se4, pairs4, mono4 = ols(rows, "dr", "l2_error")
            half = (max(pairs4) - min(pairs4)) / 2.0
            delta = max(se4, half)
            lead_orders4[s] = f4
            lead_deltas[s] = delta
            ok = (
                close(f3, st.get("fit_order_3rung"))
                and close(f4, st.get("fit_order_4rung"))
                and all(close(p, q) for p, q in zip(pairs4, st.get("pair_orders", [])))
                and len(pairs4) == len(st.get("pair_orders", []))
                and close(se4, st["uncertainty"].get("least_squares_standard_error"))
                and close(se3, st.get("uncertainty_3rung_standard_error"))
                and close(half, st["uncertainty"].get("pair_spread_half_range"))
                and close(delta, st["uncertainty"].get("reported_delta"))
                and mono4 == st.get("monotone")
            )
            check(
                "L-%s-4rung" % s,
                "lead addendum 3/4-rung fits, SE, half-range, delta recomputed (%s)" % s,
                {
                    "fit_order_3rung": st.get("fit_order_3rung"),
                    "fit_order_4rung": st.get("fit_order_4rung"),
                    "pair_orders": st.get("pair_orders"),
                    "uncertainty": st.get("uncertainty"),
                    "uncertainty_3rung_standard_error": st.get("uncertainty_3rung_standard_error"),
                },
                {
                    "fit_order_3rung": f3,
                    "fit_order_4rung": f4,
                    "pair_orders": pairs4,
                    "se4": se4,
                    "se3": se3,
                    "pair_spread_half_range": half,
                    "reported_delta": delta,
                },
                ok,
            )

        # agreement pairs
        for p in lead.get("agreement_pairs", []):
            a, b = p["schemes"]
            diff = abs(lead_orders4[a] - lead_orders4[b])
            allowed = max(0.25, math.sqrt(lead_deltas[a] ** 2 + lead_deltas[b] ** 2))
            ok = close(diff, p.get("delta_order")) and (diff <= allowed) == bool(p.get("agree"))
            check(
                "X-agree-%s-%s" % (a, b),
                "R5 agreement pair %s/%s recomputed" % (a, b),
                {"delta_order": p.get("delta_order"), "agree": p.get("agree")},
                {"delta_order": diff, "allowed": allowed, "agree": diff <= allowed},
                ok,
            )

    # cross-check FIXED 3-rung vs addendum 3-rung
    if fixed and lead:
        for s in sorted(set(fixed_orders) & set(lead_orders4)):
            l3 = lead["studies"][s].get("fit_order_3rung")
            check(
                "X-fixed-vs-lead3-%s" % s,
                "FIXED 3-rung fit equals addendum 3-rung fit (%s)" % s,
                {"lead_fit_order_3rung": l3},
                {"fixed_fit_order": fixed_orders[s]},
                close(fixed_orders[s], l3),
            )

    # protocol band on 4-rung fits (canonical +-0.3, protocol sec3.6)
    if lead:
        p_expected = lead.get("config", {}).get("p_expected", 2.0)
        for s, f4 in sorted(lead_orders4.items()):
            check(
                "X-band-%s" % s,
                "4-rung fit inside canonical band %s +- 0.3" % p_expected,
                {"|fit - p_expected| <= 0.3": True},
                {"fit": f4, "deviation": abs(f4 - p_expected)},
                abs(f4 - p_expected) <= 0.3,
            )

    # ---------------- S: three-scheme 4-rung reports ----------------------
    summary, sum_sha, sum_bytes, sum_stable = read_stable_json(SUMMARY)
    check(
        "S0-summary-readable",
        "three-scheme summary readable and byte-stable",
        "readable, stable",
        {"sha256": sum_sha, "bytes": sum_bytes, "stable": sum_stable},
        summary is not None and sum_stable,
    )
    if summary and lead:
        prov = summary.get("provenance", {})
        psha, _ = sha256_file(PROTOCOL)
        fsha, _ = sha256_file(FROZEN_MODULE)
        check(
            "S1-summary-pins",
            "summary protocol/frozen-module pins match measured files",
            {
                "protocol": prov.get("canonical_protocol_sha256"),
                "module": prov.get("frozen_module_sha256"),
            },
            {"protocol": psha, "module": fsha},
            psha == prov.get("canonical_protocol_sha256")
            and fsha == prov.get("frozen_module_sha256"),
        )
        srep = summary.get("reports", {})
        verdict = summary.get("verdict", {})
        for s, rel in REPORTS.items():
            rep, rsha, rbytes, rstable = read_stable_json(rel)
            info = srep.get(s, {})
            if rep is None or not rstable:
                check(
                    "S-%s-readable" % s,
                    "scheme 4-rung report readable and byte-stable (%s)" % s,
                    "readable, stable",
                    {"sha256": rsha, "stable": rstable},
                    False,
                )
                continue
            norm = rep.get("error_norm_fitted")
            ykey = "linf" if "inf" in str(norm).lower() else "l2"
            slope, se, pairs, mono = ols(rep["rows"], "dr", ykey)
            half = (max(pairs) - min(pairs)) / 2.0
            delta = max(se, half)
            ou = rep.get("order_uncertainty", {})
            ok = (
                close(slope, rep.get("fitted_order"))
                and close(slope, ou.get("fit_order"))
                and close(se, ou.get("standard_error"))
                and close(half, ou.get("pair_spread_half_range"))
                and close(delta, rep.get("delta"))
                and close(delta, ou.get("delta"))
                and mono is True
                and rep.get("stable") is True
                and rsha == info.get("sha256")
                and rstable
            )
            check(
                "S-%s-recompute" % s,
                "scheme 4-rung report fit/SE/delta recomputed from raw rows (%s, %s)" % (s, norm),
                {
                    "fitted_order": rep.get("fitted_order"),
                    "order_uncertainty": ou,
                    "delta": rep.get("delta"),
                    "sha256": info.get("sha256"),
                },
                {"fitted_order": slope, "se": se, "delta": delta, "sha256_now": rsha},
                ok,
            )
            st = (rep.get("energy_functional") or {}).get("solver_tolerance")
            check(
                "S-%s-solver-tolerance" % s,
                "scheme declares non-null finite solver_tolerance (%s)" % s,
                {"solver_tolerance": "not None, finite"},
                {"solver_tolerance": st},
                st is not None and math.isfinite(float(st)),
            )
        # summary verdict consistency with the recomputed reports
        check(
            "S2-summary-verdict-bools",
            "summary verdict booleans (audits pass, tolerances declared, pairs agree)",
            {"all_audits_pass_C0_C9": True, "all_have_declared_solver_tolerance": True, "all_pairs_agree_R5": True},
            {
                "all_audits_pass_C0_C9": verdict.get("all_audits_pass_C0_C9"),
                "all_have_declared_solver_tolerance": verdict.get("all_have_declared_solver_tolerance"),
                "all_pairs_agree_R5": verdict.get("all_pairs_agree_R5"),
            },
            verdict.get("all_audits_pass_C0_C9") is True
            and verdict.get("all_have_declared_solver_tolerance") is True
            and verdict.get("all_pairs_agree_R5") is True,
        )
        # manifest rebuild claims vs the registered reports (builder not re-executed, outputs compared)
        rb = manifest.get("rebuild", {})
        ok_rb = rb.get("deterministic_rebuild") is True and rb.get("exit_code") == 0
        rb_detail = {}
        for s in REPORTS:
            so = srep.get(s, {}).get("order", {})
            ok_rb &= close(rb.get("orders", {}).get(s), so.get("fit_order"))
            ok_rb &= close(rb.get("deltas", {}).get(s), so.get("delta"))
            ok_rb &= srep.get(s, {}).get("audit_verdict") == rb.get("audits", {}).get(s)
            ok_rb &= rb.get("failed_checks", {}).get(s) == []
            ok_rb &= (rb.get("payload_equal_to_registered_reports", {}) or {}).get(s) is True
            rb_detail[s] = {
                "manifest_order": rb.get("orders", {}).get(s),
                "summary_order": so.get("fit_order"),
                "manifest_delta": rb.get("deltas", {}).get(s),
                "summary_delta": so.get("delta"),
                "audit": srep.get(s, {}).get("audit_verdict"),
            }
        check(
            "M6-rebuild-claims-vs-registered-reports",
            "manifest rebuild block agrees with the registered three-scheme reports",
            {"deterministic_rebuild": True, "exit_code": 0, "orders/deltas/audits": "equal"},
            rb_detail,
            bool(ok_rb),
        )

    # ---------------- K: lock state ---------------------------------------
    mp, map_sha, map_bytes, map_stable = read_stable_json(MAP)
    lock = (mp or {}).get("numerics_lock", {})
    check(
        "K1-lock-state",
        "map numerics_lock state during verification",
        "locked",
        {"state": lock.get("state"), "map_sha256": map_sha, "stable": map_stable},
        lock.get("state") == "locked" and map_stable,
    )
    check(
        "K2-solver-absent",
        "numerics/spherical_solver absent while locked",
        {"exists": False},
        {"exists": (ROOT / SOLVER_DIR).exists()},
        not (ROOT / SOLVER_DIR).exists(),
    )
    gsha, gbytes = sha256_file(GUARD)
    check(
        "K3-guard-present",
        "self-gravity lock guard present",
        {"exists": True},
        {"exists": gsha is not None, "sha256": gsha, "bytes": gbytes},
        gsha is not None,
    )

    return report(man_sha, man_bytes, {
        "manifest": man_sha,
        "registry": reg_sha,
        "map": map_sha,
        "fixed_run": fixed_sha,
        "lead_4rung": lead_sha,
        "three_scheme_summary": sum_sha,
        "scheme_reports": {s: sha256_file(REPORTS[s])[0] for s in REPORTS},
        "protocol": sha256_file(PROTOCOL)[0],
        "frozen_module": sha256_file(FROZEN_MODULE)[0],
    })


def report(man_sha, man_bytes, inputs):
    failures = [c for c in CHECKS if not c["pass"]]
    out = {
        "schema": "worker-012/n0/c4-verification/v1",
        "actor": "worker-012",
        "agent_id": "deepseek-flash-12",
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N0",
        "gate": "G-NUM",
        "task_id": "w012-c4-verify-20260912T0030",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "subject": MANIFEST,
        "assignment_ref": "astra-numfix-03 residual C4 (registration of the N0 G-NUM anchors); no inbox card pending, class-bound task taken under AF-WCC-SCALAR-SPH/N0/G-NUM. Earlier card lnum-rev-20260911T2333-N0-12 remains delivered at numerics/tests/flat_wave.py#8b52014dac47.",
        "inputs": inputs,
        "checks": CHECKS,
        "summary": {
            "verdict": "PASS" if not failures else "FALSIFIED",
            "checks_total": len(CHECKS),
            "checks_passed": len(CHECKS) - len(failures),
            "failures": [c["id"] for c in failures],
        },
        "read_only": True,
        "rebuild_not_reexecuted": (
            "The manifest's deterministic_rebuild clause was NOT re-executed: the builder "
            "numerics/protocol/build_three_scheme_reports.py writes into registered report paths, "
            "which a read-only worker pass must not do. Its outputs were instead re-derived from "
            "the raw per-rung rows and cross-checked against the registered report hashes."
        ),
        "falsifier": (
            "Any FAIL check in this report: an anchor whose on-disk sha256/bytes no longer match the "
            "manifest, a live registry entry disagreeing with measured bytes, a recomputed order/SE/"
            "half-range/delta differing from the stored statistic by >1e-9, a 4-rung fit outside the "
            "canonical 2+-0.3 band, an R5 pair violating |pA-pB| <= max(0.25, sqrt(dA^2+dB^2)), a "
            "scheme with a null solver_tolerance, numerics_lock != locked, or numerics/spherical_solver "
            "present. A later controller registration of any sha256 other than the measured_sha256 "
            "recorded by the manifest also falsifies the manifest's registration request."
        ),
        "claims_not_made": [
            "no gate verdict and no gate self-pass (authority: Astra)",
            "no node completion and no N0 acceptance (authority: lead-numerics / Astra)",
            "no registration into runtime/state/artifact_hashes.json (controller-owned)",
            "no edit to any frozen artifact (numerics/tests/flat_wave.py stays 8b52014dac47)",
            "no N1 work; numerics_lock stays LOCKED and numerics/spherical_solver is absent",
            "no physics or censorship claim; flat-space calibration evidence only",
            "no independent review of deepseek-flash-14's work as a reviewer of record: this is a "
            "mechanical re-measurement by a different bounded pass, not a human or cross-family review",
        ],
        "authority_note": (
            "This artifact is a measurement request handed to the controller; only the controller writes "
            "the hash registry and only Astra adjudicates G-NUM."
        ),
    }
    print(json.dumps(out, indent=1, sort_keys=True))
    print(
        "\nVERDICT %s: %d/%d checks passed%s"
        % (
            out["summary"]["verdict"],
            out["summary"]["checks_passed"],
            out["summary"]["checks_total"],
            "" if not failures else " -- FAILURES: " + ", ".join(out["summary"]["failures"]),
        ),
        file=sys.stderr,
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
