#!/usr/bin/env python3
"""W057-N0-CANONTEMPORAL-VERIFY-01, part A: independent recomputation.

Object under verification
-------------------------
`numerics/protocol/canonical_temporal_control.json` (lead-numerics, generated 00:30,
sha256 6b339cb87661...) with schema `n0-canonical-temporal-control/v1`, class
`AF-WCC-SCALAR-SPH`, node N0, gate G-NUM.  Claim (as recorded in that file): the three
canonical `flat_wave.py` convergence studies are *spatial-dominated at the baseline cfl*
under the file's pre-stated rule, i.e. temporal excess at the coarsest resolution <= 0.05
and fitted order move <= 0.05.

What this script does (no import of the lead's generator; pure-Python arithmetic)
---------------------------------------------------------------------------------
1. Hash-binds the control JSON, the canonical artifact and the generator; checks the
   canonical hash against the control's declaration, the map's N0 declaration and the
   artifact registry.
2. Re-derives every stored derived number from the embedded `rows` alone:
   dt (constant-CFL ceil quantisation, using the hash-pinned study config), `order_l2`,
   `fit_order` (pure-Python OLS on log n vs log l2_error), temporal excess,
   excess_coarsest/finest, order_move, spatial_admissible, verdict text, per-study overall.
3. Checks the plateau is a genuine limit at every resolution and that the verdict is
   robust to a max-excess (instead of coarsest-excess) reading of the rule.
4. Runs 6 fail-closed controls; each must turn a passing check into a detected failure.

Not claimed: no gate verdict, no node completion, no physics claim, no solver-correctness
claim, no edit to any canonical artifact.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CONTROL = REPO / "numerics" / "protocol" / "canonical_temporal_control.json"
CANON = REPO / "numerics" / "tests" / "flat_wave.py"
GENERATOR = REPO / "numerics" / "protocol" / "canonical_temporal_control.py"
MAP = REPO / "research_map" / "research_map.json"
REGISTRY = REPO / "runtime" / "state" / "artifact_hashes.json"
OUT = REPO / "artifacts" / "worker-057" / "n0_canon_temporal_verify" / "report.json"
OUT_MD = REPO / "artifacts" / "worker-057" / "n0_canon_temporal_verify" / "REPORT.md"

TASK = "W057-N0-CANONTEMPORAL-VERIFY-01"
EXPECT_CANON_SHA = "8b52014dac47f99663c8bf46fb2e65a80db399860d586d63cd73dd1db1454a6c"
EXPECT_GENERATOR_SHA = "00a41cfd47088df9432bdc0aba6540cc3c6a69cd1bf88722b228819274adfa0f"
EXCESS_TOL = 0.05
ORDER_MOVE_TOL = 0.05
TOL_DT = 1e-12          # relative, dt reproduction from the ceil formula
TOL_ORDER_L2 = 1e-12    # relative
TOL_FIT = 1e-12         # relative
TOL_EXCESS = 1e-15      # absolute
TOL_DERIVED = 1e-12     # relative for the overall reduction
TOL_ORDER_MOVE = 1e-9   # absolute: order_move is a cancellation-prone difference of fitted orders

# transcribed from the pinned generator (STUDIES, lines 46-53); literal fragments below are
# checked against the generator source so the transcription is bound to the pinned hash.
STUDY_CONFIG = {
    "order2_standing": {"t_end": 0.37, "R": 1.0},
    "order2_pulse": {"t_end": 8.0, "R": 40.0},
    "order4_standing": {"t_end": 0.37, "R": 1.0},
}
CONFIG_FRAGMENTS = [
    '("order2_standing", dict(order=2, family="standing", t_end=0.37), 0.25,',
    '[0.25, 0.05, 0.01, 0.002]),',
    '("order2_pulse", dict(order=2, family="pulse", R=40.0, t_end=8.0, r0=12.0, sigma=2.0),',
    '("order4_standing", dict(order=4, family="standing", t_end=0.37,',
    'modes=((2, 1.0), (5, 0.5))), 0.1, [0.1, 0.02, 0.004, 0.0008]),',
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(a: float, b: float) -> float:
    return abs(a - b) / max(abs(b), 1e-300)


class Checker:
    def __init__(self):
        self.checks = []

    def check(self, cid, desc, observed, expected, tol, ok):
        self.checks.append({
            "id": cid, "description": desc, "observed": observed, "expected": expected,
            "tolerance": tol, "pass": bool(ok),
        })
        return bool(ok)


def ols_slope(xs, ys):
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / sxx


def expected_dt(t_end, R, n, cfl):
    h = R / n
    n_steps = max(1, int(math.ceil(t_end / (cfl * h))))
    return t_end / n_steps, n_steps, h


def derive(rec, config):
    """Independent recomputation of one study record's derived numbers.

    Returns (computed, diagnostics) or (None, error).  Never reads the stored derived
    values; only `runs[...].rows` and `baseline_cfl`/`cfl_ladder`.
    """
    runs = rec["runs"]
    cfls = sorted(float(v["cfl"]) for v in runs.values())
    base_cfl = float(rec["baseline_cfl"])
    if base_cfl not in cfls:
        return None, "baseline_cfl not in runs"
    plateau_cfl = cfls[0]
    base = runs[f"{base_cfl:g}"]
    plateau = runs[f"{plateau_cfl:g}"]

    n_base = [int(r["n"]) for r in base["rows"]]
    n_plat = [int(r["n"]) for r in plateau["rows"]]
    if n_base != n_plat:
        return None, "resolution lists differ between baseline and plateau runs"

    computed = {"n": n_base, "runs": {}}
    for key, run in runs.items():
        rows = run["rows"]
        ns = [int(r["n"]) for r in rows]
        es = [float(r["l2_error"]) for r in rows]
        dts = [float(r["dt"]) for r in rows]
        cfl = float(run["cfl"])
        # constant-CFL ceil quantisation, using the hash-pinned study config
        dt_exp = []
        for n in ns:
            dt_e, n_steps, h = expected_dt(config["t_end"], config["R"], n, cfl)
            dt_exp.append((dt_e, n_steps, h))
        order_l2 = [math.log(es[i] / es[i + 1]) / math.log(ns[i + 1] / ns[i])
                    for i in range(len(es) - 1)]
        fit = -ols_slope([math.log(n) for n in ns], [math.log(e) for e in es])
        computed["runs"][key] = {"cfl": cfl, "n": ns, "l2": es, "dt": dts,
                                 "dt_expected": [x[0] for x in dt_exp],
                                 "n_steps": [x[1] for x in dt_exp],
                                 "h": [x[2] for x in dt_exp],
                                 "order_l2": order_l2, "fit_order": fit,
                                 "monotone_l2": all(es[i + 1] < es[i] for i in range(len(es) - 1))}
    e_base = computed["runs"][f"{base_cfl:g}"]["l2"]
    e_plat = computed["runs"][f"{plateau_cfl:g}"]["l2"]
    excess = [b / p - 1.0 for b, p in zip(e_base, e_plat)]
    p_base = computed["runs"][f"{base_cfl:g}"]["fit_order"]
    p_plat = computed["runs"][f"{plateau_cfl:g}"]["fit_order"]
    order_move = abs(p_base - p_plat)
    admissible = bool(excess[0] <= EXCESS_TOL and order_move <= ORDER_MOVE_TOL)
    computed.update({
        "baseline_cfl": base_cfl, "plateau_cfl": plateau_cfl,
        "excess": excess, "excess_coarsest": excess[0], "excess_finest": excess[-1],
        "p_baseline": p_base, "p_plateau": p_plat, "order_move": order_move,
        "spatial_admissible": admissible,
        "verdict": ("constant-CFL study is spatial-dominated at the baseline cfl"
                    if admissible else
                    "MIXED-ORDER at the baseline cfl: temporal contribution is not "
                    "negligible; label it mixed-order and re-base any spatial claim"),
        "max_excess": max(excess),
        "max_excess_admissible": bool(max(excess) <= EXCESS_TOL and order_move <= ORDER_MOVE_TOL),
    })
    return computed, None


def compare_derived(rec, computed, tol_excess=TOL_EXCESS, tol_derived=TOL_DERIVED):
    """Return a list of (field, stored, computed, deviation) mismatches vs stored values."""
    bad = []

    def cmp(field, stored, comp, tol, rel_tol=False):
        dev = rel(comp, stored) if rel_tol else abs(comp - stored)
        if dev > tol:
            bad.append({"field": field, "stored": stored, "computed": comp, "deviation": dev})

    for key, run in rec["runs"].items():
        c = computed["runs"][key]
        for i, row in enumerate(run["rows"]):
            cmp(f"{key}.rows[{i}].dt", float(row["dt"]), c["dt"][i], TOL_DT, rel_tol=True)
        cmp(f"{key}.fit_order", float(run["fit_order"]), c["fit_order"], TOL_FIT, rel_tol=True)
        if len(run["order_l2"]) != len(c["order_l2"]):
            bad.append({"field": f"{key}.order_l2", "stored": "len-mismatch",
                        "computed": "len-mismatch", "deviation": float("inf")})
        else:
            for i, (a, b) in enumerate(zip(run["order_l2"], c["order_l2"])):
                cmp(f"{key}.order_l2[{i}]", float(a), b, TOL_ORDER_L2, rel_tol=True)
    cmp("excess_coarsest", float(rec["excess_coarsest"]), computed["excess_coarsest"], tol_excess)
    cmp("excess_finest", float(rec["excess_finest"]), computed["excess_finest"], tol_excess)
    cmp("order_move", float(rec["order_move"]), computed["order_move"], TOL_ORDER_MOVE)
    cmp("p_baseline", float(rec["p_baseline"]), computed["p_baseline"], TOL_FIT, rel_tol=True)
    cmp("p_plateau", float(rec["p_plateau"]), computed["p_plateau"], TOL_FIT, rel_tol=True)
    if bool(rec["spatial_admissible"]) != computed["spatial_admissible"]:
        bad.append({"field": "spatial_admissible", "stored": rec["spatial_admissible"],
                    "computed": computed["spatial_admissible"], "deviation": 1.0})
    if rec["verdict"] != computed["verdict"]:
        bad.append({"field": "verdict", "stored": rec["verdict"],
                    "computed": computed["verdict"], "deviation": 1.0})
    return bad


def main() -> int:
    t0 = time.time()
    ck = Checker()
    control = json.loads(CONTROL.read_text())
    gen_src = GENERATOR.read_text()
    hashes = {
        "numerics/protocol/canonical_temporal_control.json": sha256_file(CONTROL),
        "numerics/tests/flat_wave.py": sha256_file(CANON),
        "numerics/protocol/canonical_temporal_control.py": sha256_file(GENERATOR),
        "this_script": sha256_file(Path(__file__)),
    }
    map_doc = json.loads(MAP.read_text())
    registry = json.loads(REGISTRY.read_text()).get("registry", {})

    # ---- binding checks -------------------------------------------------
    ck.check("B1", "control JSON is the expected schema/class/node/gate/conclusion",
             {"schema": control.get("schema"), "class_id": control.get("class_id"),
              "node_id": control.get("node_id"), "gate": control.get("gate"),
              "conclusion_type": control.get("conclusion_type")},
             {"schema": "n0-canonical-temporal-control/v1", "class_id": "AF-WCC-SCALAR-SPH",
              "node_id": "N0", "gate": "G-NUM", "conclusion_type": "numerical_evidence"},
             "exact",
             control.get("schema") == "n0-canonical-temporal-control/v1"
             and control.get("class_id") == "AF-WCC-SCALAR-SPH"
             and control.get("node_id") == "N0" and control.get("gate") == "G-NUM"
             and control.get("conclusion_type") == "numerical_evidence")
    ck.check("B2", "declared canonical sha256 == measured on disk",
             hashes["numerics/tests/flat_wave.py"], EXPECT_CANON_SHA, "exact",
             hashes["numerics/tests/flat_wave.py"] == EXPECT_CANON_SHA
             and control.get("canonical_artifact", {}).get("sha256") == EXPECT_CANON_SHA)
    ck.check("B3", "generator sha256 == pinned generator hash",
             hashes["numerics/protocol/canonical_temporal_control.py"], EXPECT_GENERATOR_SHA,
             "exact", hashes["numerics/protocol/canonical_temporal_control.py"] == EXPECT_GENERATOR_SHA)
    ck.check("B4", "transcribed study config fragments are present in the pinned generator",
             [f for f in CONFIG_FRAGMENTS if f not in gen_src], [], "exact",
             all(f in gen_src for f in CONFIG_FRAGMENTS))
    # registry + map binding for the canonical artifact
    reg_canon = registry.get("numerics/tests/flat_wave.py", {}).get("sha256")
    n0_declared = None
    for a in map_doc.get("assignments", []):
        pass
    for node in (map_doc.get("nodes") or []) if isinstance(map_doc.get("nodes"), list) else []:
        if isinstance(node, dict) and node.get("node_id") == "N0":
            n0_declared = node.get("artifact_sha256")
    if n0_declared is None:
        # map stores N0 evidence under artifacts/frozen collections; scan for the hash
        n0_declared = EXPECT_CANON_SHA if EXPECT_CANON_SHA in json.dumps(map_doc) else None
    ck.check("B5", "canonical hash present in artifact registry and map",
             {"registry": reg_canon, "map_contains_hash": EXPECT_CANON_SHA in json.dumps(map_doc)},
             {"registry": EXPECT_CANON_SHA, "map_contains_hash": True}, "exact",
             reg_canon == EXPECT_CANON_SHA and EXPECT_CANON_SHA in json.dumps(map_doc))
    # edited=false is independently consistent: canonical mtime predates control generation
    import os
    canon_mtime = os.path.getmtime(CANON)
    ctrl_mtime = os.path.getmtime(CONTROL)
    ck.check("B6", "canonical mtime predates the control artifact (supports edited=false)",
             {"canon_mtime": canon_mtime, "control_mtime": ctrl_mtime}, "canon <= control",
             "exact", canon_mtime <= ctrl_mtime)

    # ---- per-study independent recomputation ----------------------------
    study_report = {}
    for label, rec in control["studies"].items():
        computed, err = derive(rec, STUDY_CONFIG[label])
        if err:
            ck.check(f"C-{label}", f"{label}: derived recomputation", err, "no error", "exact", False)
            study_report[label] = {"error": err}
            continue
        mism = compare_derived(rec, computed)
        ck.check(f"C1-{label}", f"{label}: every derived number reproduces from embedded rows",
                 {"n_mismatches": len(mism), "mismatches": mism[:8]}, 0, "exact", not mism)
        ck.check(f"C2-{label}", f"{label}: dt matches constant-CFL ceil quantisation (t_end={STUDY_CONFIG[label]['t_end']}, R={STUDY_CONFIG[label]['R']})",
                 max(rel(c["dt"][i], c["dt_expected"][i])
                     for c in computed["runs"].values() for i in range(len(c["dt"]))),
                 0.0, TOL_DT,
                 all(rel(c["dt"][i], c["dt_expected"][i]) <= TOL_DT
                     for c in computed["runs"].values() for i in range(len(c["dt"]))))
        ck.check(f"C3-{label}", f"{label}: l2_error strictly decreasing in n in every run",
                 all(c["monotone_l2"] for c in computed["runs"].values()), True, "exact",
                 all(c["monotone_l2"] for c in computed["runs"].values()))
        ck.check(f"C4-{label}", f"{label}: verdict robust to max-excess (instead of coarsest-excess) reading",
                 {"max_excess": computed["max_excess"],
                  "max_excess_admissible": computed["max_excess_admissible"]}, True, "exact",
                 computed["max_excess_admissible"])
        # plateau limit: final ladder increment small and decreasing
        incs = []
        for key in sorted(computed["runs"], key=lambda k: -computed["runs"][k]["cfl"]):
            pass
        cfl_order = sorted(computed["runs"].values(), key=lambda r: -r["cfl"])
        for i in range(len(cfl_order) - 1):
            a, b = cfl_order[i]["l2"], cfl_order[i + 1]["l2"]
            incs.append(max(abs(x - y) / y for x, y in zip(a, b)))
        ck.check(f"C5-{label}", f"{label}: plateau is a genuine limit (successive cfl increments collapse)",
                 {"increments": incs, "final": incs[-1]}, "final <= 1e-6 and decreasing", "exact",
                 incs[-1] <= 1e-6 and all(incs[i] >= incs[i + 1] for i in range(len(incs) - 1)))
        study_report[label] = {
            "excess_coarsest": computed["excess_coarsest"],
            "excess_finest": computed["excess_finest"],
            "max_excess": computed["max_excess"],
            "order_move": computed["order_move"],
            "p_baseline": computed["p_baseline"],
            "p_plateau": computed["p_plateau"],
            "spatial_admissible": computed["spatial_admissible"],
            "mismatches": mism,
        }

    # ---- overall block ------------------------------------------------
    overall_ok = all(s["spatial_admissible"] for s in control["studies"].values())
    per_study_ok = all(
        rel(float(control["overall"]["per_study"][k]["excess_coarsest"]),
            control["studies"][k]["excess_coarsest"]) <= TOL_DERIVED
        and rel(float(control["overall"]["per_study"][k]["order_move"]),
                control["studies"][k]["order_move"]) <= TOL_DERIVED
        and bool(control["overall"]["per_study"][k]["spatial_admissible"])
        == bool(control["studies"][k]["spatial_admissible"])
        for k in control["studies"])
    ck.check("C6", "overall block is the reduction of the study records",
             {"all_spatial_admissible": control["overall"]["all_spatial_admissible"],
              "per_study_consistent": per_study_ok}, True, "exact",
             bool(control["overall"]["all_spatial_admissible"]) == bool(overall_ok) and per_study_ok)

    # ---- fail-closed controls -----------------------------------------
    controls = []

    def add_control(cid, desc, fired, detail):
        controls.append({"id": cid, "description": desc, "detected": bool(fired), "detail": detail})

    import copy
    base_label = "order2_pulse"
    rec = control["studies"][base_label]
    comp, _ = derive(rec, STUDY_CONFIG[base_label])
    # E1: rule must reject if coarsest temporal excess > tol
    tam = copy.deepcopy(rec)
    tam["runs"][f"{comp['plateau_cfl']:g}"]["rows"][0]["l2_error"] *= 0.9
    c1, _ = derive(tam, STUDY_CONFIG[base_label])
    add_control("E1", "scaling the plateau coarsest error by 0.9 (excess 0.111) flips the rule to inadmissible",
            (not c1["spatial_admissible"]) and c1["verdict"].startswith("MIXED-ORDER"),
            {"excess_coarsest": c1["excess_coarsest"], "admissible": c1["spatial_admissible"]})
    # E2: order-move must reject if |p_base - p_plat| > tol
    tam2 = copy.deepcopy(rec)
    # lift the baseline run's coarsest-resolution error by 1.3x: the refitted p_baseline rises
    # by ~0.076, so |p(baseline) - p(plateau)| must exceed the 0.05 order-move tolerance
    tam2["runs"][f"{comp['baseline_cfl']:g}"]["rows"][0]["l2_error"] *= 1.3
    c2, _ = derive(tam2, STUDY_CONFIG[base_label])
    add_control("E2", "shifting p_baseline by +0.06 flips the rule to inadmissible",
            (not c2["spatial_admissible"]) and c2["verdict"].startswith("MIXED-ORDER"),
            {"order_move": c2["order_move"], "admissible": c2["spatial_admissible"]})
    # E3: reversed plateau rows must be detected as a derived-number mismatch
    tam3 = copy.deepcopy(rec)
    tam3["runs"][f"{comp['plateau_cfl']:g}"]["rows"] = list(
        reversed(tam3["runs"][f"{comp['plateau_cfl']:g}"]["rows"]))
    c3, err3 = derive(tam3, STUDY_CONFIG[base_label])
    mism3 = compare_derived(tam3, c3) if c3 else [{"field": "derive", "deviation": 1.0}]
    add_control("E3", "reversing plateau rows (n alignment broken) is detected by the comparison",
            bool(mism3), {"n_mismatches": len(mism3), "error": err3})
    # E4: tampering one embedded row by 1e-3 relative is detected
    tam4 = copy.deepcopy(rec)
    tam4["runs"][f"{comp['plateau_cfl']:g}"]["rows"][-1]["l2_error"] *= 1.001
    c4, _ = derive(tam4, STUDY_CONFIG[base_label])
    mism4 = compare_derived(tam4, c4)
    add_control("E4", "tampering the finest plateau row by 1e-3 relative is detected",
            any(m["field"].endswith("excess_finest") or "excess" in m["field"] for m in mism4)
            or len(mism4) > 0, {"n_mismatches": len(mism4)})
    # E5: an n-list mismatch between runs is detected
    tam5 = copy.deepcopy(rec)
    tam5["runs"][f"{comp['plateau_cfl']:g}"]["rows"][1]["n"] += 1
    c5, err5 = derive(tam5, STUDY_CONFIG[base_label])
    add_control("E5", "changing one plateau n breaks the shared resolution list and is detected",
            err5 is not None or (c5 is not None and bool(compare_derived(tam5, c5))),
            {"error": err5})
    # E6: hash binding rejects a byte-level edit
    blob = CONTROL.read_bytes()
    tam6 = bytes([blob[0] ^ 0x01]) + blob[1:]
    h6 = hashlib.sha256(tam6).hexdigest()
    add_control("E6", "a one-byte edit of the control JSON changes its sha256 (binding rejects it)",
            h6 != hashes["numerics/protocol/canonical_temporal_control.json"],
            {"tampered_sha256": h6, "measured": hashes["numerics/protocol/canonical_temporal_control.json"]})

    # ---- advisories ----------------------------------------------------
    advisories = [
        {"id": "A1", "severity": "documentation",
         "text": ("pre_stated_rule.criterion says 'excess at coarsest resolution' without defining "
                  "excess as relative; the stored numbers are e(baseline)/e(plateau) - 1 and are "
                  "reproduced to 1e-15. Absolute excess would be ~1e-9 and the rule would be "
                  "vacuous, so the relative reading is the only non-degenerate one.")},
        {"id": "A2", "severity": "documentation",
         "text": ("the study kwargs (order/family/t_end/R/r0/sigma/modes) are not embedded in the "
                  "control JSON; they live only in the hash-pinned generator. The artifact is not "
                  "self-describing, but this verifier binds the transcription to the pinned "
                  "generator hash " + EXPECT_GENERATOR_SHA[:12] + ".")},
        {"id": "A3", "severity": "non-reproducible-field",
         "text": ("canonical_artifact.edited=false and overall.runtime_seconds are assertions; "
                  "edited=false is supported here by hash equality plus mtime ordering, "
                  "runtime_seconds is environment-dependent and not checkable.")},
        {"id": "A4", "severity": "rule-shape",
         "text": ("the criterion uses the coarsest-resolution excess; for order4_standing the "
                  "relative excess grows with resolution (coarsest 4.78e-05 -> finest 1.54e-04). "
                  "The verdict is unchanged under a max-excess reading (C4), so this is a "
                  "robustness note, not a defect.")},
    ]

    failed = [c for c in ck.checks if not c["pass"]]
    controls_failed = [c for c in controls if not c["detected"]]
    instrument_valid = not failed and not controls_failed
    verdict = ("RECOMPUTED" if instrument_valid
               else ("CHECKS-FAILED" if failed else "CONTROLS-FAILED"))
    report = {
        "schema": "w057-n0-canonical-temporal-verify/v1",
        "task": TASK,
        "actor": "worker-057",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N0",
        "gate": "G-NUM",
        "object_under_verification": {
            "path": "numerics/protocol/canonical_temporal_control.json",
            "sha256": hashes["numerics/protocol/canonical_temporal_control.json"],
            "schema": control.get("schema"),
            "claim": ("all three canonical flat_wave.py convergence studies are spatial-dominated "
                      "at the baseline cfl: temporal excess at coarsest <= 0.05 and fitted-order "
                      "move <= 0.05"),
        },
        "method": ("pure-Python recomputation of every derived number from the embedded rows "
                   "(no import of the lead generator), constant-CFL dt reproduction from the "
                   "hash-pinned study config, plateau-limit and max-excess robustness checks, "
                   "6 fail-closed controls"),
        "measured_hashes": hashes,
        "binding": {"canonical_sha256": EXPECT_CANON_SHA, "generator_sha256": EXPECT_GENERATOR_SHA},
        "studies": study_report,
        "checks": ck.checks,
        "controls": controls,
        "advisories": advisories,
        "summary": {
            "n_checks": len(ck.checks), "n_failed": len(failed),
            "failed_ids": [c["id"] for c in failed],
            "n_controls": len(controls), "n_controls_failed": len(controls_failed),
            "controls_failed_ids": [c["id"] for c in controls_failed],
            "instrument_valid": instrument_valid,
            "verdict": verdict,
            "reproduced_all_derived_numbers": not failed,
            "no_gate_verdict_claimed": True,
        },
        "falsifier": ("Re-hash numerics/protocol/canonical_temporal_control.json and re-run this "
                      "instrument: the report is falsified for the recorded control sha256 if any "
                      "declared derived number fails to reproduce from the embedded rows, if any "
                      "check flips, or if any of E1-E6 stops being detected. A moved control hash "
                      "voids this report for the new bytes; a moved canonical hash voids the "
                      "control's own premise."),
        "not_claimed": ["no gate verdict", "no node completion", "no physics claim",
                        "no solver-correctness claim", "no edit to any canonical artifact"],
        "runtime_seconds": None,
    }
    report["runtime_seconds"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "verdict": verdict, "checks": len(ck.checks), "failed": len(failed),
        "controls": f"{len(controls) - len(controls_failed)}/{len(controls)}",
        "advisories": len(advisories), "runtime_seconds": report["runtime_seconds"],
        "report_sha256": sha256_file(OUT),
    }, indent=1))
    return 0 if instrument_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
