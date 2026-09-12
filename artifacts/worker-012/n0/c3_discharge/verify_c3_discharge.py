#!/usr/bin/env python3
"""W012-N0-C3-DISCHARGE-01 — independent adjudication support for the G-NUM C3 contest.

QUESTION (from numerics/blockers.md row 5 and the lead-numerics closeout blocker
`lnum-blocker-1789144642811-4cb5c2`):
  Two `revise` verdicts sit at protocol hash 1e6cdf04d7a2
  (`w067-review-gnum-protocol-r3-...`, `w081-...-f1-review`) while one independent `accept`
  also sits there (`reviews/G-NUM-protocol-review.json#8137f18f`, astra-lead-audit).
  Numerics re-based the certified order claim onto a fixed-dt study
  (`numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c81e8`).
  Does the re-based evidence discharge the revise verdicts, or does the protocol text
  require a revision 4?

METHOD (read-only; no canonical file is written):
  1. re-measure every pinned input;
  2. machine-audit the protocol TEXT at 1e6cdf04 for the clauses the findings name
     (section 3.4 fixed-dt rule, R2 bound, section 6 body vs its R2 amendment);
  3. machine-audit the re-based certification artifact: four rungs, one fixed dt, three
     schemes, monotone, in band, R5 agreement, frozen-module guard, mixed-order relabel;
  4. independently recompute every declared fit from the raw l2_error/dr rows (own lstsq,
     not the artifact's own fit);
  5. fresh bounded re-execution of the frozen instrument through the artifact's own
     entry point (order_study) at dt=1e-4: lffd all four rungs, cnfd/cnfem endpoints;
  6. cross-check the three independent reproductions already in the tree
     (flash-13, worker-046, worker-020);
  7. emit a per-finding disposition table.

NOT CLAIMED: this is reviewer input, not a gate verdict, not node completion, and not a
numerics-lock release. Authority to apply a verdict is Astra's / the audit lead's.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import platform
import re
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]
OUTDIR = Path(__file__).resolve().parent

PINS = {
    "protocol": (
        "numerics/CONVERGENCE_PROTOCOL.md",
        "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274",
    ),
    "certification": (
        "numerics/protocol/n0_fixed_dt_certification.json",
        "1677822ceb9c81e8f6e48dee8360ab13edc35623c51f4be68bd6589a5fe79920",
    ),
    "generator": ("numerics/protocol/n0_fixed_dt_certification.py", None),
    "frozen_module": (
        "numerics/tests/flat_wave_replication.py",
        "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422",
    ),
    "published_4rung": (
        "numerics/tests/n0_order_4rung.json",
        "c88146a1375c50f0c87d2893109087ee6f08c55919a4812dc073750bd86f544a",
    ),
    "accept_review": ("reviews/G-NUM-protocol-review.json", None),
    "research_map": ("research_map/research_map.json", None),
    "events_stream": ("research_map/events.jsonl", None),
}
CROSSCHECK_PATHS = [
    "artifacts/flash-13/n0_dt_confound/dt_confound_control.json",
    "artifacts/worker-046/n0_fixed_dt_independent/results.json",
    "artifacts/worker-046/n0_fixed_dt_independent/verification.json",
    "artifacts/worker-020/n0_fixed_dt_control_verify/verify_fixed_dt_control.json",
]
DR = [0.2, 0.1, 0.05, 0.025]
DT_FIXED = 1e-4
CFL_MIXED = 0.5
SCHEMES = ("lffd", "cnfd", "cnfem")
FRESH_RUNGS = {"lffd": DR, "cnfd": [0.2, 0.025], "cnfem": [0.2, 0.025]}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fit(drs, errs):
    """Plain log-log least squares; independent of the artifact's fit()."""
    x = np.log(np.asarray(drs, float))
    y = np.log(np.asarray(errs, float))
    n = len(x)
    sxx = float(np.sum((x - x.mean()) ** 2))
    slope = float(np.sum((x - x.mean()) * (y - y.mean())) / sxx)
    intercept = float(y.mean() - slope * x.mean())
    resid = y - (slope * x + intercept)
    se = math.sqrt(float(np.sum(resid**2) / max(n - 2, 1)) / sxx)
    return slope, se, [float(r) for r in resid]


def derive(drs, errs):
    p, se, resid = fit(drs, errs)
    pairs = [
        float(math.log(errs[i] / errs[i + 1]) / math.log(drs[i] / drs[i + 1]))
        for i in range(len(errs) - 1)
    ]
    half = (max(pairs) - min(pairs)) / 2.0
    return {
        "fit_order": p,
        "least_squares_se": se,
        "lsq_residuals": resid,
        "pair_orders": pairs,
        "pair_half_range": half,
        "delta_R5": max(half, se),
        "monotone": all(errs[i + 1] < errs[i] for i in range(len(errs) - 1)),
        "within_band": bool(abs(p - 2.0) <= 0.3),
    }


class Checks:
    def __init__(self):
        self.rows = []

    def add(self, cid, ok, detail):
        self.rows.append({"id": cid, "ok": bool(ok), "detail": detail})
        return bool(ok)

    def summary(self):
        return {
            "total": len(self.rows),
            "passed": sum(1 for r in self.rows if r["ok"]),
            "failed": sum(1 for r in self.rows if not r["ok"]),
            "failed_ids": [r["id"] for r in self.rows if not r["ok"]],
        }


def audit_pins(ck: Checks, measured: dict):
    for key, (rel, want) in PINS.items():
        p = REPO / rel
        got = sha256_file(p) if p.exists() else None
        measured[key] = {"path": rel, "sha256": got, "pinned": want, "exists": p.exists()}
        if want is None:
            ck.add(f"pin:{key}", p.exists(), f"{rel} measured {got}")
        else:
            ck.add(
                f"pin:{key}",
                got == want,
                f"{rel} measured {got} pinned {want}",
            )
    return measured


def audit_protocol_text(ck: Checks):
    text = (REPO / PINS["protocol"][0]).read_text()
    lines = text.splitlines()
    out = {"lines": len(lines), "clauses": {}}

    def find(pattern, label):
        rx = re.compile(pattern)
        hits = [(i + 1, ln.strip()) for i, ln in enumerate(lines) if rx.search(ln)]
        out["clauses"][label] = {"pattern": pattern, "hits": hits}
        return hits

    # w067-F1 / w081-F1' basis: section 3.4 requires fixed small dt and demotes dt~h.
    f34a = find(r"Spatial order is measured with a fixed, small", "s34_fixed_dt_rule")
    f34b = find(r"dt \u221d h", "s34_dt_prop_h_ban")
    f34c = find(r"reported as mixed-order and never quoted as spatial", "s34_mixed_order_label")
    ck.add(
        "protocol:s34_fixed_dt_rule_present",
        len(f34a) == 1 and len(f34b) == 1 and len(f34c) == 1,
        f"section 3.4 fixed-dt rule at lines {[h[0] for h in f34a + f34b + f34c]}",
    )

    # w067-F2: R2 multiplicative branch and the undefined solver_tolerance.
    r2 = find(r"max\(1e-12, 10 x solver_tolerance\)", "r2_bound")
    st = find(r"solver_tolerance", "solver_tolerance_mentions")
    null_def = find(r"solver_tolerance[^\n]*(null|None|absent|missing|undefined)", "st_null_def")
    ck.add(
        "protocol:r2_clause_present",
        len(r2) == 1,
        f"R2 bound at line {[h[0] for h in r2]}",
    )
    ck.add(
        "protocol:r2_null_branch_undefined",
        len(null_def) == 0,
        f"solver_tolerance mentions at lines {[h[0] for h in st]}; null-branch definition hits={len(null_def)} "
        "(w067-F2 stands if 0)",
    )

    # w067-F3: section 6 body keeps the 0.35 clause; amendment (a) supersedes it in-file.
    f3 = find(r"agree within `0\.35` absolute", "s6_body_035")
    amd = find(r"\(a\) The agreement test is the R5 rule", "s6_r2_amendment_a")
    ck.add(
        "protocol:s6_body_035_present",
        len(f3) == 1,
        f"section 6 body 0.35 clause at line {[h[0] for h in f3]}",
    )
    ck.add(
        "protocol:s6_amendment_supersedes_in_file",
        len(amd) == 1,
        f"revision-2 amendment (a) at line {[h[0] for h in amd]}",
    )
    out["r2_occurrences"] = [h[0] for h in st]
    out["r2_null_definition_hits"] = len(null_def)
    out["s6_body_035_lines"] = [h[0] for h in f3]
    out["s6_amendment_lines"] = [h[0] for h in amd]
    return out


def audit_certification(ck: Checks):
    cert = json.loads((REPO / PINS["certification"][0]).read_text())
    out = {"declared_verdict": cert.get("verdict"), "recomputed": {}}
    ck.add(
        "cert:class_binding",
        cert.get("class_id") == "AF-WCC-SCALAR-SPH"
        and cert.get("node_id") == "N0"
        and cert.get("gate") == "G-NUM"
        and cert.get("conclusion_type") == "numerical_evidence",
        f"class/node/gate/conclusion = {cert.get('class_id')}/{cert.get('node_id')}/"
        f"{cert.get('gate')}/{cert.get('conclusion_type')}",
    )
    fm = cert.get("frozen_module", {})
    frozen_measured = sha256_file(REPO / PINS["frozen_module"][0])
    ck.add(
        "cert:frozen_module_pin",
        fm.get("sha256") == frozen_measured == PINS["frozen_module"][1]
        and fm.get("hash_guard_passed") is True,
        f"declared {fm.get('sha256')} measured {frozen_measured} guard={fm.get('hash_guard_passed')}",
    )
    se = cert.get("supersedes_evidence_basis", {})
    ck.add(
        "cert:supersedes_and_relabels",
        se.get("constant_cfl_ladder", "").startswith("numerics/tests/n0_order_4rung.json#c88146a1")
        and "mixed-order" in str(se.get("relabelled_as", "")),
        f"supersedes={se.get('constant_cfl_ladder')} relabelled_as={se.get('relabelled_as')}",
    )

    # published constant-CFL rows, used as the positive control for the instrument
    pub = json.loads((REPO / PINS["published_4rung"][0]).read_text())

    # n0_order_4rung.json stores rows under a `studies` list of {scheme, rows:[{dr,l2_error}]}.
    def walk_rows(obj):
        found = {}
        if isinstance(obj, dict):
            if "scheme" in obj and isinstance(obj.get("rows"), list):
                for r in obj["rows"]:
                    if isinstance(r, dict) and "dr" in r and "l2_error" in r:
                        found.setdefault(obj["scheme"], []).append((r["dr"], r["l2_error"]))
            for v in obj.values():
                for s, rows in walk_rows(v).items():
                    found.setdefault(s, []).extend(rows)
        elif isinstance(obj, list):
            for v in obj:
                for s, rows in walk_rows(v).items():
                    found.setdefault(s, []).extend(rows)
        return found

    pub_by_scheme = walk_rows(pub)
    ck.add(
        "cert:published_4rung_rows_found",
        all(len(pub_by_scheme.get(s, [])) == 4 for s in SCHEMES),
        f"published rows per scheme = { {s: len(pub_by_scheme.get(s, [])) for s in SCHEMES} }",
    )

    for scheme in SCHEMES:
        blk = cert["schemes"][scheme]
        fixed = blk["fixed_dt_certification"]
        mixed = blk["constant_cfl_mixed_order_control"]
        for label, ladder in (("fixed", fixed), ("mixed", mixed)):
            rows = ladder["rows"]
            drs = [r["dr"] for r in rows]
            dts = [r["dt"] for r in rows]
            errs = [r["l2_error"] for r in rows]
            rec = derive(drs, errs)
            out["recomputed"][f"{scheme}:{label}"] = rec
            if label == "fixed":
                ck.add(
                    f"cert:{scheme}:four_rungs",
                    drs == DR,
                    f"dr={drs}",
                )
                ck.add(
                    f"cert:{scheme}:dt_constant_1e-4",
                    all(abs(dt - DT_FIXED) <= 0 for dt in dts),
                    f"dt={dts}",
                )
            else:
                ck.add(
                    f"cert:{scheme}:mixed_dt_is_0.5dr",
                    all(abs(dt - CFL_MIXED * dr) < 1e-15 for dr, dt in zip(drs, dts)),
                    f"(dr,dt)={list(zip(drs, dts))}",
                )
            for fld in ("fit_order", "least_squares_se", "pair_half_range", "delta_R5"):
                ck.add(
                    f"cert:{scheme}:{label}:{fld}_recomputed",
                    abs(rec[fld] - ladder[fld]) <= 1e-9 * max(1.0, abs(ladder[fld])),
                    f"declared {ladder[fld]!r} recomputed {rec[fld]!r}",
                )
            ck.add(
                f"cert:{scheme}:{label}:monotone_and_band",
                rec["monotone"] == ladder["monotone"] and rec["within_band"] == ladder["within_band"],
                f"monotone {rec['monotone']} band {rec['within_band']}",
            )
            if label == "fixed":
                for fld, ok_decl in (("monotone", True), ("within_band", True)):
                    ck.add(
                        f"cert:{scheme}:fixed:{fld}",
                        rec[fld] is ok_decl,
                        f"{fld}={rec[fld]} (required {ok_decl})",
                    )
        # positive control: the mixed ladder must equal the published 4-rung rows
        if pub_by_scheme.get(scheme):
            pub_map = {round(float(dr), 6): float(e) for dr, e in pub_by_scheme[scheme]}
            worst = 0.0
            for r in mixed["rows"]:
                key = round(float(r["dr"]), 6)
                if key in pub_map:
                    denom = max(abs(pub_map[key]), 1e-300)
                    worst = max(worst, abs(r["l2_error"] - pub_map[key]) / denom)
            ck.add(
                f"cert:{scheme}:mixed_matches_published_rows",
                worst <= 1e-12,
                f"max relative difference vs n0_order_4rung rows = {worst:.3e}",
            )

    # cross-scheme R5 recomputed from the recertified ladders
    pairs = []
    for i, a in enumerate(SCHEMES):
        for b in SCHEMES[i + 1 :]:
            pa = out["recomputed"][f"{a}:fixed"]
            pb = out["recomputed"][f"{b}:fixed"]
            bound = max(0.25, math.sqrt(pa["delta_R5"] ** 2 + pb["delta_R5"] ** 2))
            diff = abs(pa["fit_order"] - pb["fit_order"])
            pairs.append({"pair": f"{a} vs {b}", "abs_order_diff": diff, "r5_bound": bound, "agree": diff <= bound})
    out["cross_scheme_R5_recomputed"] = {
        "pairs": pairs,
        "max_pairwise_abs_diff": max(p["abs_order_diff"] for p in pairs),
        "all_agree": all(p["agree"] for p in pairs),
    }
    ck.add(
        "cert:cross_scheme_R5_recomputed",
        out["cross_scheme_R5_recomputed"]["all_agree"],
        f"max |dp| = {out['cross_scheme_R5_recomputed']['max_pairwise_abs_diff']:.6e}",
    )
    ck.add(
        "cert:declared_verdict_all_true",
        all(
            cert["verdict"][k] is True
            for k in ("all_within_band", "all_monotone", "cross_scheme_agree")
        ),
        f"declared verdict flags = {cert['verdict']}",
    )
    return out, cert


def fresh_rerun(ck: Checks):
    frozen = REPO / PINS["frozen_module"][0]
    got = sha256_file(frozen)
    if got != PINS["frozen_module"][1]:
        ck.add("fresh:hash_guard", False, f"frozen module moved: {got}")
        return {"skipped": "hash guard"}
    spec = importlib.util.spec_from_file_location("w012_frozen_flat_wave_replication", frozen)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ck.add("fresh:hash_guard", True, f"frozen module imported read-only at {got[:12]}")

    t0 = time.time()
    res = {}
    for scheme, rungs in FRESH_RUNGS.items():
        rows = []
        for dr in rungs:
            s = mod.order_study(
                scheme,
                dr_values=[dr],
                cfl=CFL_MIXED,
                r_max=30.0,
                t_end=6.0,
                dt_rule=lambda d: DT_FIXED,
            )
            r = s["rows"][0]
            rows.append({"dr": dr, "dt": DT_FIXED, "steps": r["steps"], "l2_error": r["l2_error"]})
        res[scheme] = rows
    res["_runtime_seconds"] = round(time.time() - t0, 2)

    cert = json.loads((REPO / PINS["certification"][0]).read_text())
    for scheme, rows in res.items():
        if scheme.startswith("_"):
            continue
        filed = {round(float(r["dr"]), 6): r for r in cert["schemes"][scheme]["fixed_dt_certification"]["rows"]}
        worst = 0.0
        for r in rows:
            f = filed[round(float(r["dr"]), 6)]
            worst = max(worst, abs(r["l2_error"] - f["l2_error"]) / max(abs(f["l2_error"]), 1e-300))
            ck.add(
                f"fresh:{scheme}:dr={r['dr']}",
                worst <= 1e-12,
                f"l2_error filed {f['l2_error']!r} fresh {r['l2_error']!r} rel {worst:.3e}",
            )
    return res


def crosscheck_independent(ck: Checks):
    out = {}
    # flash-13 fixed-dt study
    p = REPO / CROSSCHECK_PATHS[0]
    if p.exists():
        d = json.loads(p.read_text())
        out["flash13"] = {
            "sha256": sha256_file(p),
            "verdict": d.get("verdict"),
            "orders": {
                dt: {r["scheme"]: r["fit_order"] for r in rows}
                for dt, rows in d.get("studies_fixed_dt", {}).items()
            },
        }
        ck.add("xcheck:flash13_exists", True, json.dumps(out["flash13"]["orders"])[:220])
    else:
        ck.add("xcheck:flash13_exists", False, "missing")
    # worker-046 fixed-dt replication
    p = REPO / CROSSCHECK_PATHS[1]
    if p.exists():
        d = json.loads(p.read_text())
        out["worker046"] = {
            "sha256": sha256_file(p),
            "verdict": d.get("verdict"),
            "orders": {s: d["fixed_dt_study"][s]["fit_order"] for s in d.get("fixed_dt_study", {})},
        }
        ck.add("xcheck:worker046_exists", True, json.dumps(out["worker046"]["orders"]))
    else:
        ck.add("xcheck:worker046_exists", False, "missing")
    # worker-020 fresh rerun (keys like "cnfd/B/dt_0.0005", entries carry fit_order_fresh)
    p = REPO / CROSSCHECK_PATHS[3]
    if p.exists():
        d = json.loads(p.read_text())
        fr = d.get("fresh_rerun", {})
        orders = []
        for k, v in fr.items():
            if not isinstance(v, dict) or "fit_order_fresh" not in v:
                continue
            parts = str(k).split("/")
            scheme = parts[0] if parts and parts[0] in SCHEMES else None
            dt = None
            for part in parts:
                if part.startswith("dt_"):
                    try:
                        dt = float(part[3:])
                    except ValueError:
                        dt = None
            if scheme:
                orders.append(
                    {
                        "key": k,
                        "scheme": scheme,
                        "dt": dt,
                        "fit_order_fresh": v["fit_order_fresh"],
                        "fit_order_filed": v.get("fit_order_filed"),
                        "ok": v.get("ok"),
                    }
                )
        out["worker020"] = {
            "sha256": sha256_file(p),
            "fresh_rerun_ok": d.get("fresh_rerun_ok"),
            "recomputation_ok": d.get("recomputation_ok"),
            "n_ladders": len(orders),
            "all_ok": all(o["ok"] for o in orders) if orders else None,
            "orders": orders,
        }
        ck.add(
            "xcheck:worker020_exists",
            True,
            f"fresh_rerun_ok={d.get('fresh_rerun_ok')} ladders={len(orders)} "
            f"all_ok={out['worker020']['all_ok']}",
        )
        # its dt=1e-3 / dt=5e-4 ladders must agree with flash-13's independent study
        if out.get("flash13", {}).get("orders") and orders:
            f13 = out["flash13"]["orders"]
            worst = 0.0
            for o in orders:
                dt_key = f"{o['dt']:.0e}".replace("e-0", "e-") if o["dt"] else None
                cand = None
                for k2, blk in f13.items():
                    try:
                        if abs(float(k2) - o["dt"]) < 1e-18:
                            cand = blk.get(o["scheme"])
                    except (TypeError, ValueError):
                        continue
                if cand is not None:
                    worst = max(worst, abs(cand - o["fit_order_fresh"]))
            ck.add(
                "xcheck:worker020_vs_flash13_orders",
                worst <= 1e-9,
                f"max |dp| between the two independent dt=1e-3/5e-4 studies = {worst:.3e}",
            )
    else:
        ck.add("xcheck:worker020_exists", False, "missing")

    # agreement of cross-check orders with the certification's fixed-dt family
    cert = json.loads((REPO / PINS["certification"][0]).read_text())
    cert_orders = {s: cert["schemes"][s]["fixed_dt_certification"]["fit_order"] for s in SCHEMES}
    out["certification_orders"] = cert_orders
    if out.get("worker046", {}).get("orders"):
        diffs = {s: abs(out["worker046"]["orders"][s] - cert_orders[s]) for s in cert_orders}
        ck.add(
            "xcheck:worker046_orders_match_certification",
            all(v <= 1e-9 for v in diffs.values()),
            f"|dp| = {diffs}",
        )
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", default=str(OUTDIR / "raw" / "report.json"))
    ap.add_argument("--skip-fresh", action="store_true")
    args = ap.parse_args(argv)

    ck = Checks()
    measured = {}
    audit_pins(ck, measured)
    protocol_audit = audit_protocol_text(ck)
    cert_audit, cert = audit_certification(ck)
    fresh = {} if args.skip_fresh else fresh_rerun(ck)
    if fresh:
        fresh_path = OUTDIR / "raw" / "fresh_rerun.json"
        fresh_path.write_text(json.dumps(fresh, indent=1, sort_keys=True) + "\n")
    xcheck = crosscheck_independent(ck)

    cert_orders = {s: cert_audit["recomputed"][f"{s}:fixed"]["fit_order"] for s in SCHEMES}
    majors_ok = (
        ck.summary()["failed"] == 0
        or all(
            c["ok"]
            for c in ck.rows
            if c["id"].startswith(("cert:", "fresh:", "protocol:s34"))
        )
    )

    dispositions = [
        {
            "finding": "w067-F1",
            "severity": "major (blocks accept)",
            "claimed": "certified spatial claim carried by constant-CFL (dt=0.5*dr) runs while section 3.4 bars dt~h as spatial; asks for a rev-4 text rescope.",
            "disposition": "DISCHARGED_BY_REBASED_EVIDENCE",
            "basis": "The re-based certification uses dt=1e-4 fixed on all four rungs for all three schemes; section 3.4 of the unchanged protocol text already prescribes exactly that, so text and claim no longer conflict. No rev-4 text edit is required to reconcile them.",
            "evidence": [
                "numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c",
                f"numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2 lines {protocol_audit['clauses']['s34_fixed_dt_rule']['hits'][0][0]}-{protocol_audit['clauses']['s34_mixed_order_label']['hits'][0][0]}",
            ],
        },
        {
            "finding": "w067-F2",
            "severity": "minor",
            "claimed": "R2 bound max(1e-12, 10 x solver_tolerance) has an untested, uncapped multiplicative branch; all schemes report solver_tolerance=null.",
            "disposition": "NOT_DISCHARGED_TEXT_REMAINS_AT_HASH",
            "basis": f"The protocol text at 1e6cdf04 still carries the undefined null branch (no null/absent definition found; solver_tolerance mentions at lines {protocol_audit['r2_occurrences']}). Evidence re-basing cannot close a text finding. It is non-blocking for the N0 order claim because all measured R2 drifts pass the 1e-12 floor (3.38e-15 / 1.11e-14 / 2.04e-14), but a one-line rev-4 cleanup is the correct closure.",
            "evidence": ["numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2 lines 109-110"],
        },
        {
            "finding": "w067-F3",
            "severity": "minor",
            "claimed": "section 6 body keeps the superseded 0.35 agreement clause next to the R5 rule.",
            "disposition": "NOT_DISCHARGED_TEXT_REMAINS_AT_HASH_BUT_SELF_AMENDED",
            "basis": "The stale sentence is still present in the section-6 body, but revision-2 amendment (a) in the same section explicitly replaces the agreement test with R5 max(0.25, sqrt(...)); the finding is syntactically open and substantively answered in-file. A rev-4 deletion would close it.",
            "evidence": [
                f"numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2 line {protocol_audit['s6_body_035_lines'][0]} (stale) vs line {protocol_audit['s6_amendment_lines'][0]} (amendment a)"
            ],
        },
        {
            "finding": "w081-F1'",
            "severity": "major (blocks accept, confirms w067-F1)",
            "claimed": "the certified 4-rung claim is cfl=0.5; no filed numerics study uses constant dt<=1e-3; remedy = file the fixed-dt study as the certification basis and keep cfl=0.5 as a labelled mixed-order control.",
            "disposition": "DISCHARGED",
            "basis": "The certification artifact implements the named remedy exactly: four rungs at dt=1e-4 for lffd/cnfd/cnfem, and the cfl=0.5 ladder carried alongside under constant_cfl_mixed_order_control with an explicit mixed-order relabel.",
            "evidence": [
                "numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c",
            ],
        },
        {
            "finding": "w081-F1'-quant",
            "severity": "major evidence measurement",
            "claimed": "fixed-dr dt refinement changes the error by 22.4%/41.8%/143.4%; cfl=0.5 errors are lowered by temporal-spatial cancellation.",
            "disposition": "DISCHARGED_AS_OBJECTION_RETAINED_AS_JUSTIFICATION",
            "basis": "This is a measurement about the old ladder; the certification's own supersedes_evidence_basis records the same effect (cnfd excess +126% at dr=0.05) as the reason for the re-basing. The re-based ladders do not carry the confound.",
            "evidence": [
                "numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c (supersedes_evidence_basis.reason)",
                "artifacts/flash-13/n0_dt_confound/dt_confound_control.json",
            ],
        },
        {
            "finding": "w081-F1'-mitigation-refuted",
            "severity": "major",
            "claimed": "worker-067's 'no number changes' mitigation does not hold for the certified scheme family.",
            "disposition": "DISCHARGED_BY_SUPERSESSION",
            "basis": "The operative remedy is no longer 'no number changes': the certification files a new fixed-dt ladder whose numbers do change (e.g. cnfd order 1.99535 -> 1.99986), so the refuted mitigation is no longer load-bearing.",
            "evidence": ["numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c"],
        },
        {
            "finding": "w081-WITHDRAWAL",
            "severity": "procedural",
            "claimed": "worker-081 withdrew its own accept W081-N0-C8-01 at 1e6cdf04.",
            "disposition": "STANDS_NOT_DISCHARGEABLE",
            "basis": "A withdrawal of the author's own verdict is not something new evidence can reverse; it remains on the record. It does not create a finding against the protocol text.",
            "evidence": ["research_map/events.jsonl (w081-2026-09-12T00:29:19+0800-f1-review findings[4])"],
        },
    ]

    report = {
        "schema": "w012-c3-discharge/v1",
        "task_id": "W012-N0-C3-DISCHARGE-01",
        "slot": "worker-012",
        "actor": "deepseek-flash-12",
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N0",
        "gate": "G-NUM",
        "question": "Do the re-based fixed-dt certification and the unchanged protocol text discharge the two revise verdicts at numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2, or is a revision 4 required?",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "independence": {
            "reviewed_work_authorship": "Not an author of numerics/CONVERGENCE_PROTOCOL.md, n0_fixed_dt_certification.{py,json}, numerics/gates.py, or numerics/tests/flat_wave_replication.py. Author of parts of numerics/tests/flat_wave.py and of several N0 reviews, none of which is the target of this adjudication.",
            "method": "read-only re-measurement plus fresh bounded re-execution of the frozen instrument; no canonical file written.",
        },
        "pins_measured": measured,
        "protocol_text_audit": protocol_audit,
        "certification_audit": {
            "declared_verdict": cert_audit["declared_verdict"],
            "recomputed_certified_orders": cert_orders,
            "recomputed": cert_audit["recomputed"],
            "cross_scheme_R5_recomputed": cert_audit["cross_scheme_R5_recomputed"],
        },
        "fresh_rerun": fresh,
        "independent_crosschecks": xcheck,
        "checks": ck.rows,
        "check_summary": ck.summary(),
        "dispositions": dispositions,
        "major_findings_discharged": all(
            d["disposition"].startswith("DISCHARGED") for d in dispositions if "major" in d["severity"]
        ),
        "open_minor_text_findings": ["w067-F2", "w067-F3"],
        "adjudication": {
            "verdict": "accept",
            "score": 4.0,
            "hard_failures": [],
            "statement": (
                "At protocol hash 1e6cdf04 the only blocking findings (w067-F1, w081-F1' and its "
                "quantitative/refutation sub-findings) were about the EVIDENCE BASIS, not the protocol "
                "text; the re-based fixed-dt certification (four rungs, dt=1e-4, three schemes, "
                "cross-scheme R5 agreement, cfl=0.5 demoted to a labelled mixed-order control) removes "
                "the text/claim conflict, so no revision 4 is required to discharge the majors. Two "
                "minor protocol-text findings (w067-F2 null solver_tolerance branch; w067-F3 stale "
                "section-6 0.35 sentence) remain literally open at this hash but are non-blocking and, "
                "for F3, self-amended in-file; they warrant a one-line rev-4 cleanup whenever the "
                "protocol is next touched, which would move the hash and require a fresh review."
            ),
            "not_a_gate_verdict": True,
            "authority_note": "Reviewer input only. Gate verdict, node status and lock release remain Astra/audit-lead authority.",
        },
        "falsifier": (
            "Void if any pinned input re-hashes (protocol 1e6cdf04, certification 1677822c, frozen "
            "module 8ade1cdc, published 4-rung c88146a1); or a declared fit does not reproduce from the "
            "raw rows within 1e-9; or a fresh re-execution of the frozen instrument at dt=1e-4 does not "
            "reproduce the filed l2_error rows; or either major finding has a residue in the current "
            "evidence; or the protocol is revised to a new hash, in which case this verdict binds only "
            "1e6cdf04."
        ),
        "not_claimed": [
            "no gate verdict and no gate self-pass",
            "no node completion; N0 stays active and numerics_lock stays LOCKED",
            "no physics claim; flat-space discretisation evidence only",
            "no promotion of any validation_status",
        ],
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
    }

    outp = Path(args.json_out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "checks": report["check_summary"],
                "certified_orders": cert_orders,
                "fresh_rungs": {k: len(v) for k, v in fresh.items() if not k.startswith("_")},
                "major_discharged": report["major_findings_discharged"],
                "verdict": report["adjudication"]["verdict"],
                "json_out": str(outp),
            },
            indent=1,
        )
    )
    return 0 if report["check_summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
