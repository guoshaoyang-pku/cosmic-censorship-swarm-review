#!/usr/bin/env python3
"""W020-N0-C3-DISCHARGE-VERIFY-01 — independent non-author checks on the C3 discharge.

TARGET (under review, not modified):
  worker-012 (deepseek-flash-12) task W012-N0-C3-DISCHARGE-01:
    artifacts/worker-012/n0/c3_discharge/verify_c3_discharge.py   (d2930155f7a8)
    artifacts/worker-012/n0/c3_discharge/raw/report.json          (67fb7f0f5b2f)
    artifacts/worker-012/n0/c3_discharge/raw/fresh_rerun.json     (65d459eb3359)
  Its claim: the re-based fixed-dt certification 1677822ceb9c discharges the two
  major revise findings on numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2;
  two minor text findings remain open; verdict accept 4.0; reviewer input only.

WHAT THIS SCRIPT DOES (read-only w.r.t. every canonical artifact):
  1. re-measures every binding pin and the target bytes;
  2. re-derives every declared fit / R5 number from the raw dr,l2_error rows with
     its own least-squares code (no import of the certification generator);
  3. re-audits the protocol text clauses the dispositions rely on at 1e6cdf04d7a2;
  4. executes a sandboxed copy of worker-012's checker (same repo depth so its REPO
     resolves; outputs redirected into the sandbox) and compares its fresh rows and
     81-check summary with the filed ones;
  5. performs its OWN bounded re-execution of the frozen module primitives at
     dt = 1e-4 (lffd dr=0.2/0.025, cnfd dr=0.2, cnfem dr=0.2) and compares the
     l2_error to the filed certification rows;
  6. runs six mutation controls (each must be detected) plus a determinism control;
  7. verifies no binding pin moved during the run.

NOT CLAIMED: no gate verdict, no node status, no validation_status promotion, no
numerics-lock release, no physics claim.  Worker-level verification evidence only.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

TZ = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TASK = "W020-N0-C3-DISCHARGE-VERIFY-01"
ACTOR = "worker-020"
CLASS_ID = "AF-WCC-SCALAR-SPH"
NODE_ID = "N0"
GATE = "G-NUM"
SCHEMES = ("lffd", "cnfd", "cnfem")
DR = [0.2, 0.1, 0.05, 0.025]
DT_FIXED = 1e-4
R5_FLOOR = 0.25
P_DESIGN = 2.0
P_TOL = 0.3

BINDING_PINS = {
    "numerics/CONVERGENCE_PROTOCOL.md":
        "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274",
    "numerics/protocol/n0_fixed_dt_certification.json":
        "1677822ceb9c81e8f6e48dee8360ab13edc35623c51f4be68bd6589a5fe79920",
    "numerics/protocol/n0_fixed_dt_certification.py":
        "3c7c9087838446046d7462f92c9ffdd9ff137cc6a07ac63bf41e7db90dfbf145",
    "numerics/tests/flat_wave_replication.py":
        "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422",
    "numerics/tests/n0_order_4rung.json":
        "c88146a1375c50f0c87d2893109087ee6f08c55919a4812dc073750bd86f544a",
    "reviews/G-NUM-protocol-review.json":
        "8137f18f1a3b2b01580e1874262e546048bd681672c1b7699e6d784842307017",
}
TARGET_PINS = {
    "artifacts/worker-012/n0/c3_discharge/verify_c3_discharge.py":
        "d2930155f7a857a0cf69c6b3bb02094c302b942f82263025a4b4042e9e31af2f",
    "artifacts/worker-012/n0/c3_discharge/raw/report.json":
        "67fb7f0f5b2fa63158c958adaa13f61577f14e1c983ce77a46071d829da2bc19",
    "artifacts/worker-012/n0/c3_discharge/raw/fresh_rerun.json":
        "65d459eb3359ad4e2b813efb8d231fcf56614002bb4241f18d49e9463dfa9c98",
    "artifacts/worker-012/n0/c3_discharge/README.md":
        "85f8cc652eed217ccc083d116a773fe23fd1e05c911aaab93b30a6c27bb49f42",
}
MUTABLE = ["research_map/research_map.json", "research_map/events.jsonl"]
SANDBOX = REPO / "tmp" / "w020_c3_repro" / "sandbox" / "c3copy"
SANDBOX_SCRIPT = SANDBOX / "verify_c3_discharge.py"

FALSIFIER = (
    "Void if any binding pin re-hashes differently (protocol 1e6cdf04, "
    "certification 1677822ceb9c, generator 3c7c9087, frozen module 8ade1cdc, "
    "published 4-rung c88146a1), or the target bytes move, or a declared fit/R5 "
    "number fails to reproduce from the raw rows within 1e-9, or the sandboxed "
    "worker-012 checker does not return 81/81, or its fresh rows do not reproduce "
    "the filed ones within 1e-9 relative, or my own frozen-module re-execution does "
    "not reproduce the filed l2_error rows within 1e-12 relative, or a mutation "
    "control fails to fire."
)


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(p: Path):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def close(a: float, b: float, rel: float = 1e-9, floor: float = 1e-12) -> bool:
    try:
        return abs(float(a) - float(b)) <= max(floor, rel * max(abs(float(a)), abs(float(b))))
    except (TypeError, ValueError):
        return False


class Checks:
    def __init__(self):
        self.rows: list[dict] = []

    def add(self, cid: str, ok: bool, detail: str = "") -> None:
        self.rows.append({"id": cid, "ok": bool(ok), "detail": detail})

    def group(self, prefix: str) -> list[dict]:
        return [r for r in self.rows if r["id"].startswith(prefix)]

    def summary(self) -> dict:
        failed = [r["id"] for r in self.rows if not r["ok"]]
        return {"total": len(self.rows), "passed": len(self.rows) - len(failed),
                "failed": len(failed), "failed_ids": failed}


# ---------------------------------------------------------------- pure analysis

def recompute_ladder(drs, errs):
    """Own log-log LS fit; returns the same statistic set the target uses."""
    lx = [math.log(x) for x in drs]
    ly = [math.log(y) for y in errs]
    n = len(drs)
    mx = sum(lx) / n
    my = sum(ly) / n
    sxx = sum((a - mx) ** 2 for a in lx)
    slope = sum((a - mx) * (b - my) for a, b in zip(lx, ly)) / sxx
    inter = my - slope * mx
    res = [ly[i] - inter - slope * lx[i] for i in range(n)]
    sse = sum(r * r for r in res)
    se = math.sqrt(sse / (n - 2) / sxx)
    pair = [math.log(errs[i] / errs[i + 1]) / math.log(drs[i] / drs[i + 1])
            for i in range(n - 1)]
    half = (max(pair) - min(pair)) / 2.0
    return {
        "fit_order": slope,
        "pair_orders": pair,
        "lsq_residuals": res,
        "least_squares_se": se,
        "pair_half_range": half,
        "delta_R5": max(half, se),
        "monotone": all(errs[i + 1] < errs[i] for i in range(n - 1)),
        "within_band": abs(slope - P_DESIGN) <= P_TOL,
        "np_polyfit_cross_check": float(
            np.polyfit(np.log(np.asarray(drs, float)), np.log(np.asarray(errs, float)), 1)[0]),
    }


def check_frozen_guard(cert, ck: Checks) -> None:
    fm = cert["frozen_module"]
    ck.add("cert:frozen_module_declared_pin",
           fm.get("sha256") == BINDING_PINS["numerics/tests/flat_wave_replication.py"],
           f"declared {fm.get('sha256')}")
    ck.add("cert:frozen_module_hash_guard_passed", fm.get("hash_guard_passed") is True,
           f"hash_guard_passed={fm.get('hash_guard_passed')}")


def check_structure(cert, ck: Checks) -> None:
    cfg = cert["config"]
    ck.add("struct:class_id", cert.get("class_id") == CLASS_ID, str(cert.get("class_id")))
    ck.add("struct:node_gate", (cert.get("node_id"), cert.get("gate")) == (NODE_ID, GATE),
           f"{cert.get('node_id')}/{cert.get('gate')}")
    ck.add("struct:dr_values", [float(x) for x in cfg["dr_values"]] == DR,
           str(cfg["dr_values"]))
    ck.add("struct:dt_fixed", float(cfg["dt_fixed"]) == DT_FIXED, str(cfg["dt_fixed"]))
    ck.add("struct:dt_rule_constant", cfg.get("dt_rule") == "constant on every rung",
           str(cfg.get("dt_rule")))
    ck.add("struct:p_design_tol", (float(cfg["p_design"]), float(cfg["p_tol"])) == (P_DESIGN, P_TOL),
           f"{cfg['p_design']}/{cfg['p_tol']}")
    ck.add("struct:supersedes_relabel",
           "mixed-order" in json.dumps(cert.get("supersedes_evidence_basis", {})).lower(),
           "mixed-order relabel present in supersedes_evidence_basis")
    for s in SCHEMES:
        sch = cert["schemes"][s]
        fx = sch["fixed_dt_certification"]
        rows = fx["rows"]
        ck.add(f"struct:{s}:fixed_four_rungs", [float(r["dr"]) for r in rows] == DR,
               str([r["dr"] for r in rows]))
        ck.add(f"struct:{s}:fixed_dt_1e-4",
               all(float(r["dt"]) == DT_FIXED for r in rows) and all(int(r["steps"]) == 60000 for r in rows),
               f"dts={[r['dt'] for r in rows]} steps={[r['steps'] for r in rows]}")
        mix = sch["constant_cfl_mixed_order_control"]
        mrows = mix["rows"]
        ck.add(f"struct:{s}:mixed_dt_is_half_dr",
               all(close(float(r["dt"]), 0.5 * float(r["dr"]), rel=1e-15) for r in mrows),
               f"dts={[r['dt'] for r in mrows]}")


def check_fits(cert, ck: Checks) -> dict:
    out = {}
    for s in SCHEMES:
        for ladder, key in (("fixed", "fixed_dt_certification"),
                            ("mixed", "constant_cfl_mixed_order_control")):
            decl = cert["schemes"][s][key]
            errs = [float(r["l2_error"]) for r in decl["rows"]]
            drs = [float(r["dr"]) for r in decl["rows"]]
            rec = recompute_ladder(drs, errs)
            out[f"{s}:{ladder}"] = rec
            for field in ("fit_order", "least_squares_se", "pair_half_range", "delta_R5"):
                ck.add(f"fit:{s}:{ladder}:{field}",
                       close(rec[field], float(decl[field])),
                       f"recomputed {rec[field]!r} vs declared {decl[field]!r}")
            ck.add(f"fit:{s}:{ladder}:pair_orders",
                   all(close(a, b) for a, b in zip(rec["pair_orders"], decl["pair_orders"])),
                   f"recomputed {rec['pair_orders']} vs declared {decl['pair_orders']}")
            ck.add(f"fit:{s}:{ladder}:lsq_residuals",
                   all(close(a, b) for a, b in zip(rec["lsq_residuals"], decl["lsq_residuals"])),
                   "residual vectors agree")
            ck.add(f"fit:{s}:{ladder}:monotone", rec["monotone"] == bool(decl["monotone"]),
                   f"{rec['monotone']} vs {decl['monotone']}")
            ck.add(f"fit:{s}:{ladder}:within_band", rec["within_band"] == bool(decl["within_band"]),
                   f"{rec['within_band']} vs {decl['within_band']}")
            ck.add(f"fit:{s}:{ladder}:np_polyfit_agrees",
                   close(rec["np_polyfit_cross_check"], rec["fit_order"], rel=1e-12),
                   f"numpy.polyfit {rec['np_polyfit_cross_check']!r} vs own {rec['fit_order']!r}")
    return out


def check_r5(cert, rec: dict, ck: Checks, pairs_decl=None) -> dict:
    orders = {s: rec[f"{s}:fixed"]["fit_order"] for s in SCHEMES}
    deltas = {s: rec[f"{s}:fixed"]["delta_R5"] for s in SCHEMES}
    pairs_decl = pairs_decl if pairs_decl is not None else cert["cross_scheme_R5"]["pairs"]
    recomputed = []
    for i, a in enumerate(SCHEMES):
        for b in SCHEMES[i + 1:]:
            diff = abs(orders[a] - orders[b])
            bound = max(R5_FLOOR, math.sqrt(deltas[a] ** 2 + deltas[b] ** 2))
            recomputed.append({"pair": f"{a} vs {b}", "abs_order_diff": diff,
                               "r5_bound": bound, "agree": diff <= bound})
    decl_map = {p["pair"]: p for p in pairs_decl}
    for p in recomputed:
        d = decl_map.get(p["pair"])
        ck.add(f"r5:{p['pair'].replace(' ', '_')}",
               d is not None and close(p["abs_order_diff"], float(d["abs_order_diff"]))
               and bool(d["agree"]) == p["agree"],
               f"recomputed diff {p['abs_order_diff']!r} bound {p['r5_bound']!r} "
               f"vs declared {None if d is None else d['abs_order_diff']!r}")
    maxdiff = max(p["abs_order_diff"] for p in recomputed)
    ck.add("r5:max_pairwise_abs_diff",
           close(maxdiff, float(cert["cross_scheme_R5"]["max_pairwise_abs_diff"])),
           f"recomputed {maxdiff!r}")
    ck.add("r5:all_agree", all(p["agree"] for p in recomputed)
           and bool(cert["cross_scheme_R5"]["all_agree"]),
           f"recomputed agree={[p['agree'] for p in recomputed]}")
    verdict = cert["verdict"]
    ck.add("verdict:declared_certified_orders",
           all(close(orders[s], float(verdict["certified_spatial_order"][s])) for s in SCHEMES),
           f"recomputed {orders} vs declared {verdict['certified_spatial_order']}")
    ck.add("verdict:all_monotone_within_band",
           verdict["all_monotone"] is True and verdict["all_within_band"] is True
           and all(rec[f"{s}:fixed"]["monotone"] and rec[f"{s}:fixed"]["within_band"] for s in SCHEMES),
           "all three fixed ladders monotone and in band")
    return {"orders": orders, "deltas": deltas, "pairs": recomputed,
            "max_pairwise_abs_diff": maxdiff}


def check_protocol(text: str, ck: Checks) -> dict:
    lines = text.splitlines()
    def line(n, needle):
        return n <= len(lines) and needle in lines[n - 1]
    ck.add("text:s34_fixed_dt_rule", line(58, "Spatial order is measured with a fixed, small `dt`"),
           "line 58")
    ck.add("text:s34_dt_prop_h_ban",
           line(60, "dt \u221d h") and line(60, "mixed-order and never quoted as spatial"),
           "line 60")
    ck.add("text:r2_bound_clause", line(110, "max(1e-12, 10 x solver_tolerance)"), "line 110")
    ck.add("text:s6_body_035_present", line(142, "agree within `0.35` absolute"), "line 142")
    ck.add("text:s6_amendment_a",
           line(145, "(a) The agreement test is the R5 rule"), "line 145")
    ck.add("text:solver_tolerance_count",
           text.count("solver_tolerance") == 1,
           f"count={text.count('solver_tolerance')} (null definition hits=0)")
    return {"lines_checked": [58, 60, 110, 142, 145],
            "solver_tolerance_count": text.count("solver_tolerance")}


def pure_analysis(cert, protocol_text) -> dict:
    """Cheap deterministic analysis part, used for the determinism control."""
    ck = Checks()
    rec = check_fits(cert, ck)
    r5 = check_r5(cert, rec, ck)
    check_structure(cert, ck)
    check_frozen_guard(cert, ck)
    txt = check_protocol(protocol_text, ck)
    return {"checks": ck.rows, "recomputed": rec, "r5": r5, "text": txt}


# ---------------------------------------------------------------- side effects

def run_sandboxed_target(ck: Checks, log) -> dict:
    """Execute a same-depth copy of worker-012's checker; outputs stay in the sandbox."""
    SANDBOX.mkdir(parents=True, exist_ok=True)
    (SANDBOX / "raw").mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / list(TARGET_PINS)[0], SANDBOX_SCRIPT)
    copy_sha = sha256_file(SANDBOX_SCRIPT)
    ck.add("repro:copy_hash_equals_target", copy_sha == TARGET_PINS[list(TARGET_PINS)[0]],
           f"{copy_sha}")
    # depth guard: the copy must resolve REPO to the real repo
    sub = subprocess.run(
        [sys.executable, "-c",
         "from pathlib import Path;import sys;"
         f"p=Path({str(SANDBOX_SCRIPT)!r}).resolve();print(p.parents[4])"],
        capture_output=True, text=True, timeout=60)
    ck.add("repro:copy_repo_resolution", sub.stdout.strip() == str(REPO),
           f"{sub.stdout.strip()} vs {REPO}")
    out_json = SANDBOX / "raw" / "report.json"
    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, str(SANDBOX_SCRIPT), "--json-out", str(out_json)],
        capture_output=True, text=True, timeout=1800, cwd=str(REPO))
    dt = time.time() - t0
    for ln in (proc.stdout or "").splitlines():
        log(f"[sandbox-repro] {ln}")
    if proc.stderr:
        for ln in proc.stderr.splitlines()[-20:]:
            log(f"[sandbox-repro:err] {ln}")
    ck.add("repro:exit_zero", proc.returncode == 0, f"exit={proc.returncode} in {dt:.1f}s")
    ck.add("repro:report_written", out_json.exists(), str(out_json))
    repro = load_json(out_json)
    s = repro["check_summary"]
    ck.add("repro:81_of_81", s["passed"] == 81 and s["failed"] == 0 and s["total"] == 81,
           json.dumps(s))
    filed = load_json(REPO / list(TARGET_PINS)[1])
    filed_ids = sorted(c["id"] for c in filed["checks"])
    repro_ids = sorted(c["id"] for c in repro["checks"])
    ck.add("repro:check_id_sets_equal", filed_ids == repro_ids,
           f"filed {len(filed_ids)} ids, repro {len(repro_ids)} ids")
    ck.add("repro:filed_report_81_of_81",
           filed["check_summary"]["passed"] == 81 and filed["check_summary"]["failed"] == 0,
           json.dumps(filed["check_summary"]))
    fresh_repro = load_json(SANDBOX / "raw" / "fresh_rerun.json")
    fresh_filed = load_json(REPO / list(TARGET_PINS)[2])
    worst = 0.0
    nrows = 0
    for sname in SCHEMES:
        fr = {float(r["dr"]): r for r in fresh_repro.get(sname, [])}
        ff = {float(r["dr"]): r for r in fresh_filed.get(sname, [])}
        ck.add(f"repro:fresh_rows_present:{sname}", set(fr) == set(ff),
               f"repro {sorted(fr)} vs filed {sorted(ff)}")
        for dr in sorted(set(fr) & set(ff)):
            a = float(fr[dr]["l2_error"])
            b = float(ff[dr]["l2_error"])
            worst = max(worst, abs(a - b) / max(abs(b), 1e-300))
            nrows += 1
    ck.add("repro:fresh_rows_match_1e-9", nrows > 0 and worst <= 1e-9,
           f"{nrows} rows, worst relative diff {worst:.3e}")
    return {"exit": proc.returncode, "seconds": dt, "summary": s,
            "fresh_rows_compared": nrows, "fresh_worst_rel_diff": worst,
            "check_ids_equal": filed_ids == repro_ids,
            "sandbox": str(SANDBOX.relative_to(REPO))}


def load_frozen_module(ck: Checks):
    p = REPO / "numerics/tests/flat_wave_replication.py"
    sha = sha256_file(p)
    ck.add("rerun:module_hash", sha == BINDING_PINS["numerics/tests/flat_wave_replication.py"], sha)
    spec = importlib.util.spec_from_file_location("flat_wave_replication_w020", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def independent_rerun(mod, cert, ck: Checks, cases) -> dict:
    pulse = mod.PulseExact()
    rows = []
    for sname, dr in cases:
        cfl = DT_FIXED / dr
        factory = mod.make_factory(sname, pulse=pulse)
        t0 = time.time()
        case = mod.run_case(factory, dr, cfl, 30.0, 6.0, sample_every=10 ** 9)
        err = mod.l2_error(case["psi"][-1], pulse.psi(case["r"], case["t"][-1]), dr)
        secs = time.time() - t0
        decl = {float(r["dr"]): r for r in cert["schemes"][sname]["fixed_dt_certification"]["rows"]}
        ref = float(decl[dr]["l2_error"])
        rel = abs(err - ref) / max(abs(ref), 1e-300)
        ck.add(f"rerun:{sname}:dr={dr}", rel <= 1e-12 and int(case["steps"]) == 60000,
               f"fresh {err!r} vs filed {ref!r} rel {rel:.3e}, steps {case['steps']}, {secs:.1f}s")
        rows.append({"scheme": sname, "dr": dr, "dt": case["dt"], "steps": int(case["steps"]),
                     "fresh_l2_error": err, "filed_l2_error": ref, "rel_diff": rel,
                     "seconds": secs})
    return {"rows": rows, "worst_rel_diff": max(r["rel_diff"] for r in rows),
            "total_seconds": sum(r["seconds"] for r in rows)}


def fresh_vs_filed_cert(ck: Checks) -> dict:
    fresh = load_json(REPO / list(TARGET_PINS)[2])
    cert = load_json(REPO / "numerics/protocol/n0_fixed_dt_certification.json")
    worst = 0.0
    n = 0
    for s in SCHEMES:
        filed = {float(r["dr"]): r for r in cert["schemes"][s]["fixed_dt_certification"]["rows"]}
        for r in fresh.get(s, []):
            dr = float(r["dr"])
            if dr in filed:
                rel = abs(float(r["l2_error"]) - float(filed[dr]["l2_error"])) / abs(float(filed[dr]["l2_error"]))
                worst = max(worst, rel)
                n += 1
    ck.add("fresh:worker012_rows_match_cert_1e-12", n > 0 and worst <= 1e-12,
           f"{n} rows, worst rel {worst:.3e}")
    return {"rows_compared": n, "worst_rel_diff": worst}


def crosschecks(ck: Checks, rec: dict) -> dict:
    """Re-read the three independent reproductions the target cites."""
    out = {}
    f13 = load_json(REPO / "artifacts/flash-13/n0_dt_confound/dt_confound_control.json")
    f13_ok = {}
    for key, dtval in (("1e-04", 1e-4), ("1e-03", 1e-3)):
        raw_studies = f13["studies_fixed_dt"][key]
        if isinstance(raw_studies, list):
            got = {s["scheme"]: float(s["fit_order"]) for s in raw_studies}
        else:  # scheme -> study mapping
            got = {v.get("scheme", k): float(v["fit_order"])
                   for k, v in raw_studies.items() if isinstance(v, dict) and "fit_order" in v}
        out[f"flash13@{dtval}"] = got
        if dtval == 1e-4:
            for s in SCHEMES:
                ck.add(f"xcheck:flash13:{s}@1e-4", close(got[s], rec[f"{s}:fixed"]["fit_order"], 1e-9),
                       f"{got[s]!r} vs {rec[f'{s}:fixed']['fit_order']!r}")
    f13_ok["dt_stability"] = f13.get("dt_stability", {}).get("stable_within_0.05")
    out["flash13_dt_stability"] = f13_ok["dt_stability"]
    ck.add("xcheck:flash13_dt_stability", f13_ok["dt_stability"] is True, str(f13_ok["dt_stability"]))

    w46 = load_json(REPO / "artifacts/worker-046/n0_fixed_dt_independent/results.json")
    got46 = {}
    for s, v in w46["fixed_dt_study"].items():
        if isinstance(v, dict):
            got46[s] = float(v.get("fit_order", v.get("order", float("nan"))))
    out["worker046"] = got46
    for s in SCHEMES:
        if s in got46:
            ck.add(f"xcheck:worker046:{s}", close(got46[s], rec[f"{s}:fixed"]["fit_order"], 1e-9),
                   f"{got46[s]!r} vs {rec[f'{s}:fixed']['fit_order']!r}")
    ck.add("xcheck:worker046_verdict", w46.get("verdict") == "SUPPORTED",
           str(w46.get("verdict")))

    w20 = load_json(REPO / "artifacts/worker-020/n0_fixed_dt_control_verify/verify_fixed_dt_control.json")
    out["worker020_fresh_rerun_ok"] = w20.get("fresh_rerun_ok")
    ck.add("xcheck:worker020_fresh_rerun_ok", w20.get("fresh_rerun_ok") is True,
           str(w20.get("fresh_rerun_ok")))
    return out


def mutation_controls(cert: dict, protocol_text: str) -> list[dict]:
    """Six planted defects; each must be detected by the relevant checker."""
    import copy

    def detect(modifier, group_prefix, expect_ok_ids) -> tuple[bool, str]:
        c = copy.deepcopy(cert)
        modifier(c)
        ck = Checks()
        check_structure(c, ck)
        rec = check_fits(c, ck)
        check_r5(c, rec, ck)
        check_frozen_guard(c, ck)
        bad = [r["id"] for r in ck.rows if r["id"].startswith(group_prefix) and not r["ok"]]
        untouched = [i for i in expect_ok_ids if not any(r["id"] == i and r["ok"] for r in ck.rows)]
        return (len(bad) > 0 and not untouched), f"fired {len(bad)}: {bad[:3]}"

    def det_text(modifier) -> tuple[bool, str]:
        ck = Checks()
        check_protocol(modifier(protocol_text), ck)
        bad = [r["id"] for r in ck.rows if not r["ok"]]
        return len(bad) > 0, f"fired {bad}"

    controls = []
    ok, detail = detect(lambda c: c["schemes"]["lffd"]["fixed_dt_certification"]["rows"][0].__setitem__(
        "l2_error", c["schemes"]["lffd"]["fixed_dt_certification"]["rows"][0]["l2_error"] * 1.005),
        "fit:lffd:fixed", ["fit:lffd:fixed:monotone"])
    controls.append({"id": "M1_l2_perturbation", "expected": "detected", "detected": ok, "detail": detail})
    ok, detail = detect(lambda c: c["schemes"]["cnfd"]["fixed_dt_certification"].__setitem__(
        "fit_order", c["schemes"]["cnfd"]["fixed_dt_certification"]["fit_order"] + 0.01),
        "fit:cnfd:fixed", ["fit:cnfd:fixed:monotone"])
    controls.append({"id": "M2_declared_order_flip", "expected": "detected", "detected": ok, "detail": detail})
    ok, detail = detect(lambda c: c["frozen_module"].__setitem__("sha256", "0" * 64),
                        "cert:frozen_module", [])
    controls.append({"id": "M3_frozen_hash_flip", "expected": "detected", "detected": ok, "detail": detail})
    ok, detail = detect(lambda c: c["schemes"]["cnfem"]["fixed_dt_certification"]["rows"][1].__setitem__(
        "dt", 2e-4), "struct:cnfem", ["struct:cnfem:fixed_four_rungs"])
    controls.append({"id": "M4_dt_rule_violation", "expected": "detected", "detected": ok, "detail": detail})
    ok, detail = det_text(lambda t: t.replace("Spatial order is measured with a fixed, small `dt`", ""))
    controls.append({"id": "M5_protocol_clause_removed", "expected": "detected", "detected": ok, "detail": detail})
    ok, detail = detect(lambda c: c["cross_scheme_R5"]["pairs"][0].__setitem__("abs_order_diff", 0.5),
                        "r5:", ["r5:all_agree"])
    controls.append({"id": "M6_r5_declared_diff_flip", "expected": "detected", "detected": ok, "detail": detail})
    return controls


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", default=str(HERE / "c3_discharge_verification.json"))
    ap.add_argument("--skip-repro", action="store_true")
    ap.add_argument("--skip-rerun", action="store_true")
    args = ap.parse_args(argv)

    log_path = HERE / "c3_discharge_verification.log"
    logf = open(log_path, "w", encoding="utf-8")

    def log(msg: str) -> None:
        print(msg)
        logf.write(msg + "\n")
        logf.flush()

    t_start = time.time()
    ck = Checks()
    log(f"[{now()}] {TASK} starting")

    pins_start = {p: sha256_file(REPO / p) for p in list(BINDING_PINS) + list(TARGET_PINS) + MUTABLE}
    for p, want in BINDING_PINS.items():
        ck.add(f"pin:{p}", pins_start[p] == want, f"live {pins_start[p][:16]} want {want[:16]}")
    for p, want in TARGET_PINS.items():
        ck.add(f"target:{p}", pins_start[p] == want, f"live {pins_start[p][:16]} want {want[:16]}")

    cert = load_json(REPO / "numerics/protocol/n0_fixed_dt_certification.json")
    protocol_text = (REPO / "numerics/CONVERGENCE_PROTOCOL.md").read_text(encoding="utf-8")

    check_structure(cert, ck)
    rec = check_fits(cert, ck)
    r5 = check_r5(cert, rec, ck)
    check_frozen_guard(cert, ck)
    text_audit = check_protocol(protocol_text, ck)
    fresh = fresh_vs_filed_cert(ck)
    xc = crosschecks(ck, rec)

    repro = {}
    if not args.skip_repro:
        log(f"[{now()}] running sandboxed copy of worker-012 checker ...")
        repro = run_sandboxed_target(ck, log)
        log(f"[{now()}] sandbox repro done: {repro}")
    else:
        ck.add("repro:skipped", False, "--skip-repro given (verification incomplete)")

    rerun = {}
    if not args.skip_rerun:
        log(f"[{now()}] own frozen-module re-execution (4 rung-solves) ...")
        mod = load_frozen_module(ck)
        rerun = independent_rerun(mod, cert, ck,
                                  [("lffd", 0.2), ("lffd", 0.025), ("cnfd", 0.2), ("cnfem", 0.2)])
        log(f"[{now()}] rerun done: worst rel {rerun['worst_rel_diff']:.3e} "
            f"in {rerun['total_seconds']:.1f}s")
    else:
        ck.add("rerun:skipped", False, "--skip-rerun given (verification incomplete)")

    controls = mutation_controls(cert, protocol_text)
    for c in controls:
        ck.add(f"control:{c['id']}", c["detected"] is True, c["detail"])

    a1 = pure_analysis(cert, protocol_text)
    a2 = pure_analysis(cert, protocol_text)
    det = json.dumps(a1, sort_keys=True) == json.dumps(a2, sort_keys=True)
    ck.add("control:determinism_two_runs", det, "two pure-analysis runs byte-identical")

    pins_end = {p: sha256_file(REPO / p) for p in list(BINDING_PINS) + list(TARGET_PINS) + MUTABLE}
    moved = [p for p in pins_end if p not in MUTABLE and pins_end[p] != pins_start[p]]
    ck.add("guard:no_binding_pin_moved", not moved, f"moved={moved}")
    log(f"[{now()}] pin write-guard: moved={moved}")

    summary = ck.summary()
    verdict = ("C3_DISCHARGE_REPRODUCED_AND_REDERIVED_NO_DEFECT"
               if summary["failed"] == 0 else "C3_DISCHARGE_VERIFICATION_FOUND_DEFECT")

    findings = []
    findings.append(
        f"Reproduction: a same-depth sandbox copy of the target checker exits 0 and returns "
        f"{repro.get('summary', {}).get('passed', '?')}/81 checks; its fresh rows reproduce the "
        f"filed fresh_rerun.json within {repro.get('fresh_worst_rel_diff', float('nan')):.2e} "
        f"relative on {repro.get('fresh_rows_compared', 0)} rows.")
    findings.append(
        f"Independent re-derivation: every declared fit, pair order, residual, SE, pair half-range, "
        f"delta_R5 and R5 pair reproduces from the raw dr,l2_error rows; my own numpy.polyfit "
        f"cross-check agrees with my hand LS fit to <= 1e-12; certified orders "
        f"{ {s: round(rec[f'{s}:fixed']['fit_order'], 9) for s in SCHEMES} }.")
    findings.append(
        f"Own frozen-module re-execution (different call path than the target: make_factory/run_case/"
        f"l2_error directly, 60,000 steps, dt=1e-4) reproduces the filed l2_error rows on 4 rungs "
        f"across all three schemes within {rerun.get('worst_rel_diff', float('nan')):.2e} relative.")
    findings.append(
        "The two minor text findings are real and correctly disclosed as still open at the pinned "
        "hash: R2's solver_tolerance has no null branch (count=1) and the stale section-6 "
        "'agree within 0.35 absolute' sentence remains at line 142 while the rev-2 amendment at "
        "line 145 supersedes it in-file. Disposition of these is the controller's, not a worker's.")
    findings.append(
        "The target's research_map/events_stream pins are measured-only mutable snapshots, not "
        "binding evidence; they must not be cited as frozen.")
    findings.append(
        "Authorship/independence: worker-020 did not author the target, the protocol, the "
        "certification, the frozen module or the published 4-rung control; this is a same-fleet "
        "third-slot check, not an external audit.")

    report = {
        "schema": "w020-c3-discharge-verify/v1",
        "task_id": TASK,
        "actor": ACTOR,
        "class_id": CLASS_ID,
        "node_id": NODE_ID,
        "gate": GATE,
        "created_at": now(),
        "runtime_seconds": round(time.time() - t_start, 1),
        "verdict": verdict,
        "review_verdict": "accept" if summary["failed"] == 0 else "revise",
        "review_score": 4.0 if summary["failed"] == 0 else 3.0,
        "hard_failures": summary["failed_ids"],
        "target": {
            "task_id": "W012-N0-C3-DISCHARGE-01",
            "actor": "deepseek-flash-12",
            "files": {p: pins_start[p] for p in TARGET_PINS},
        },
        "pins": {"binding": {p: pins_start[p] for p in BINDING_PINS},
                 "mutable": {p: pins_start[p] for p in MUTABLE}},
        "checks": {"summary": summary, "rows": ck.rows},
        "recomputed": rec,
        "r5": r5,
        "text_audit": text_audit,
        "fresh_vs_cert": fresh,
        "sandbox_repro": repro,
        "independent_rerun": rerun,
        "crosschecks": xc,
        "controls": controls,
        "determinism": det,
        "no_write_guard": {"moved": moved},
        "findings": findings,
        "not_claimed": [
            "no gate verdict and no gate self-pass",
            "no node completion; N0 stays active",
            "no validation_status promotion",
            "numerics_lock stays LOCKED; no N1 artifact touched or created",
            "no physics claim and no statement that the protocol text is correct",
            "no replacement of the controller's disposition of the C3 contest",
        ],
        "falsifier": FALSIFIER,
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "platform": platform.platform()},
    }
    Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json_out).write_text(json.dumps(report, indent=1, sort_keys=True) + "\n",
                                   encoding="utf-8")
    log(f"[{now()}] verdict={verdict} checks={summary} json={args.json_out}")
    logf.close()
    return 0 if summary["failed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
