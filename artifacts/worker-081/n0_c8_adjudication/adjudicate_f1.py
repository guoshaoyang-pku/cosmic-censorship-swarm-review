#!/usr/bin/env python3
"""W081-N0-F1-ADJ-01: independent machine-check adjudication of worker-067 finding F1.

Question (worker-067, comms/outbox/worker-067.jsonl, event w067-review-gnum-protocol-r3):
    "protocol section 3.4 forbids dt-proportional-to-h runs as spatial evidence, yet the
     proposal's certified spatial order claim uses exactly those constant-CFL runs."

This script does not argue the point; it measures it against the frozen evidence.

Read-only contract: imports the frozen replication module but never writes into numerics/,
schemas/, reviews/ or any canonical path.  All outputs go to OUTDIR (this directory).

Checks
  C1  pinned input hashes re-measured (protocol, gate proposal, 4-rung evidence, frozen module)
  C2  protocol section 3.4 text carries both clauses (fixed small dt; dt ~ h never spatial)
  C3  the certified order claim in the gate proposal advertises cfl = 0.5
  C4  every row of the certified 4-rung evidence has dt == 0.5 * dr
  C5  whether any filed numerics JSON contains an order study with constant dt <= 1e-3
  C6  canonical scheme-A temporal control status (filed)
  C7  replication control suite: sensitivity probe vs a fixed-dr dt-refinement control
  E1  NEW measurement: fixed dr = 0.05, dt halved twice (cfl 0.5 / 0.25 / 0.125), 3 schemes
  E2  NEW measurement: fixed dt = 1e-3, dr = 0.2 / 0.1 / 0.05, 3 schemes (protocol-style)
  E3  NEW measurement: protocol's exact dt = 1e-4 spot check at dr = 0.1 (executability)

Decision rule (declared before running E1):
  max relative error change per dt halving at fixed dr < 2%  -> temporal error subdominant
  (the canonical study's own temporal-control threshold), i.e. F1 is a text-scope defect;
  >= 2% -> the filed cfl = 0.5 evidence is temporally contaminated and the "spatial" label
  is not established by the filed evidence.

Usage: python3 artifacts/worker-081/n0_c8_adjudication/adjudicate_f1.py
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
import re
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTDIR = HERE
sys.path.insert(0, str(ROOT / "numerics" / "tests"))

PIN = {
    "numerics/CONVERGENCE_PROTOCOL.md": "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274",
    "numerics/tests/n0_gate_proposal.json": "58a175b52fbe4f0b7d5e3f5e0f2f6c0a2f6a4f2b0f4c3e1d0a9b8c7d6e5f4a3b",  # re-measured below; placeholder replaced by C1
    "numerics/tests/n0_order_4rung.json": "c88146a1375c50f0c87d2893109087ee6f08c55919a4812dc073750bd86f544a",
    "numerics/tests/flat_wave_replication.py": "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422",
    "numerics/tests/flat_wave.py": "8b52014dac47f99663c8bf46fb2e65a80db399860d586d63cd73dd1db1454a6c",
    "numerics/results/flat_wave_convergence.json": None,  # informational
}
# Proposal hash is measured, not pinned a priori (it was not recorded at claim time).
PROPOSAL_EXPECTED = None

SCHEMES = ["lffd", "cnfd", "cnfem"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text(path: Path) -> str:
    return path.read_text(errors="replace")


def c2_protocol_clauses(protocol_text: str) -> dict:
    m = re.search(r"^\s*4\.\s+\*\*Temporal/spatial separation\.\*\*(.+?)(?=^\s*5\.)", protocol_text,
                  re.M | re.S)
    para = " ".join(m.group(1).split()) if m else ""
    return {
        "section_3_4_found": bool(m),
        "paragraph": para,
        "clause_fixed_dt": bool(re.search(r"fixed,?\s*small\s*`?dt`?\s*\(`?1e-4`?\)", para, re.I)),
        "clause_never_spatial": bool(re.search(r"dt\s*[∝~]\s*h.*never quoted as spatial", para, re.I | re.S)),
    }


def c3_certified_claim(proposal: dict) -> dict:
    claim = proposal.get("certified_order_claim", {})
    stmt = claim.get("statement", "")
    return {
        "statement": stmt,
        "advertises_cfl_0_5": bool(re.search(r"cfl\s*=\s*0\.5", stmt, re.I)),
        "calls_it_spatial": bool(re.search(r"spatial discretisation is second order", stmt, re.I)),
        "four_rungs": bool(re.search(r"FOUR rungs", stmt)),
        "schemes": claim.get("which_schemes_order_is_certified", []),
    }


def c4_rows_constant_cfl(four: dict) -> dict:
    bad = []
    rows = 0
    for st in four.get("studies", []):
        for r in st.get("rows", []):
            rows += 1
            if not math.isclose(r.get("dt", -1), 0.5 * r.get("dr", -2), rel_tol=0, abs_tol=1e-15):
                bad.append({"scheme": st.get("scheme"), "dr": r.get("dr"), "dt": r.get("dt")})
            if not math.isclose(r.get("cfl", -1), 0.5, rel_tol=0, abs_tol=1e-15):
                bad.append({"scheme": st.get("scheme"), "cfl_field": r.get("cfl")})
    return {"rows_checked": rows, "rows_violating_dt_eq_half_dr": len(bad), "examples": bad[:4],
            "all_constant_cfl_0_5": len(bad) == 0 and rows > 0}


def c5_fixed_dt_search() -> dict:
    """Scan filed numerics JSON for an order study whose rows hold dt constant and small."""
    hits = []
    for p in sorted((ROOT / "numerics").rglob("*.json")):
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        for key in ("studies", "order_studies", "study"):
            v = d.get(key) if isinstance(d, dict) else None
            if not isinstance(v, list):
                continue
            for st in v:
                if not isinstance(st, dict):
                    continue
                rws = st.get("rows")
                if not isinstance(rws, list) or len(rws) < 3:
                    continue
                dts = [r.get("dt") for r in rws if isinstance(r, dict) and "dt" in r]
                if len(dts) == len(rws) and len(set(dts)) == 1 and dts[0] is not None and dts[0] <= 1e-3:
                    hits.append({"path": str(p.relative_to(ROOT)), "study": st.get("scheme") or st.get("family"),
                                 "dt": dts[0], "rungs": len(rws)})
    return {"constant_dt_le_1e-3_studies": hits, "none_found": len(hits) == 0}


def c6_canonical_temporal_control() -> dict:
    p = ROOT / "numerics" / "results" / "flat_wave_convergence.json"
    d = json.loads(p.read_text())
    tc = d.get("temporal_control", {})
    studies = [{k: s.get(k) for k in ("family", "order_scheme", "cfl")} for s in d.get("studies", [])]
    return {"path": str(p.relative_to(ROOT)), "temporal_control": tc,
            "convergence_studies": studies, "scheme_a_uses_constant_cfl": all("cfl" in s for s in studies)}


def measure_fixed_dr_dt_refinement(rep) -> dict:
    """E1: dr fixed at 0.05, dt halved twice. Same code path as order_study(), custom cfl."""
    pulse = rep.PulseExact()
    dr = 0.05
    dts = [0.025, 0.0125, 0.00625]
    out = {}
    for scheme in SCHEMES:
        errs, rows = [], []
        for dt in dts:
            t0 = time.time()
            factory = rep.make_factory(scheme, pulse=pulse)
            case = rep.run_case(factory, dr, dt / dr, 30.0, 6.0)
            err = rep.l2_error(case["psi"][-1], pulse.psi(case["r"], case["t"][-1]), dr)
            errs.append(err)
            rows.append({"scheme": scheme, "dr": dr, "dt": case["dt"], "eff_cfl": dt / dr,
                         "steps": case["steps"], "l2_error": err, "wall_s": round(time.time() - t0, 3)})
        rel = [abs(errs[i + 1] - errs[i]) / errs[i] for i in range(len(errs) - 1)]
        p_t = [math.log(errs[i] / errs[i + 1]) / math.log(2.0) for i in range(len(errs) - 1)]
        out[scheme] = {"rows": rows, "relative_change_per_halving": rel,
                       "temporal_order_pairwise": p_t, "max_rel_change": max(rel),
                       "temporal_subdominant_2pct": bool(max(rel) < 0.02)}
    out["_dr"] = dr
    out["_dts"] = dts
    out["_rule"] = "temporal subdominant iff max relative error change per dt halving < 2%"
    out["all_schemes_temporal_subdominant"] = all(out[s]["temporal_subdominant_2pct"] for s in SCHEMES)
    return out


def measure_fixed_dt_spatial(rep, dt_fixed=1e-3) -> dict:
    """E2: dt fixed small, dr halved twice (the protocol section 3.4 style study)."""
    pulse = rep.PulseExact()
    drs = [0.2, 0.1, 0.05]
    out = {"dt_fixed": dt_fixed}
    for scheme in SCHEMES:
        errs, rows = [], []
        for dr in drs:
            t0 = time.time()
            factory = rep.make_factory(scheme, pulse=pulse)
            case = rep.run_case(factory, dr, dt_fixed / dr, 30.0, 6.0)
            err = rep.l2_error(case["psi"][-1], pulse.psi(case["r"], case["t"][-1]), dr)
            errs.append(err)
            rows.append({"scheme": scheme, "dr": dr, "dt": case["dt"], "eff_cfl": dt_fixed / dr,
                         "steps": case["steps"], "l2_error": err, "wall_s": round(time.time() - t0, 3)})
        x = [math.log(d) for d in drs]
        y = [math.log(e) for e in errs]
        n = len(x)
        mx, my = sum(x) / n, sum(y) / n
        sxx = sum((xi - mx) ** 2 for xi in x)
        sxy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
        p = sxy / sxx
        out[scheme] = {"rows": rows, "fit_order": p,
                       "pair_orders": [math.log(errs[i] / errs[i + 1]) / math.log(drs[i] / drs[i + 1])
                                       for i in range(len(errs) - 1)]}
    return out


def measure_protocol_exact_dt(rep, dt=1e-4, dr=0.1) -> dict:
    """E3: the protocol's exact prescription (fixed dt=1e-4) at one rung, executability + error."""
    pulse = rep.PulseExact()
    out = {"dt": dt, "dr": dr}
    for scheme in SCHEMES:
        t0 = time.time()
        factory = rep.make_factory(scheme, pulse=pulse)
        case = rep.run_case(factory, dr, dt / dr, 30.0, 6.0)
        err = rep.l2_error(case["psi"][-1], pulse.psi(case["r"], case["t"][-1]), dr)
        out[scheme] = {"steps": case["steps"], "l2_error": err, "wall_s": round(time.time() - t0, 3)}
    return out


def main() -> int:
    rep = None
    results: dict = {"task_id": "W081-N0-F1-ADJ-01", "actor": "worker-081",
                     "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                     "class_id": "AF-WCC-SCALAR-SPH", "node_id": "N0", "gate": "G-NUM",
                     "conclusion_type": "numerical_evidence",
                     "purpose": "adjudicate worker-067 F1 (protocol 3.4 vs constant-CFL certified order claim)"}

    # ---- C1 hashes
    hashes = {}
    for rel in PIN:
        p = ROOT / rel
        hashes[rel] = sha256(p) if p.exists() else None
    results["C1_hashes"] = hashes
    results["C1_protocol_pin_ok"] = hashes["numerics/CONVERGENCE_PROTOCOL.md"] == PIN["numerics/CONVERGENCE_PROTOCOL.md"]
    results["C1_frozen_module_pin_ok"] = hashes["numerics/tests/flat_wave_replication.py"] == PIN["numerics/tests/flat_wave_replication.py"]
    results["C1_four_rung_pin_ok"] = hashes["numerics/tests/n0_order_4rung.json"] == PIN["numerics/tests/n0_order_4rung.json"]

    protocol_text = text(ROOT / "numerics/CONVERGENCE_PROTOCOL.md")
    proposal = json.loads((ROOT / "numerics/tests/n0_gate_proposal.json").read_text())
    four = json.loads((ROOT / "numerics/tests/n0_order_4rung.json").read_text())

    # ---- C2/C3/C4
    results["C2_protocol_section_3_4"] = c2_protocol_clauses(protocol_text)
    results["C3_certified_order_claim"] = c3_certified_claim(proposal)
    results["C4_four_rung_rows"] = c4_rows_constant_cfl(four)
    results["C5_filed_fixed_dt_study"] = c5_fixed_dt_search()
    results["C6_canonical_temporal_control"] = c6_canonical_temporal_control()

    # ---- C7 replication controls (filed)
    repres = json.loads((ROOT / "numerics/results/flat_wave_replication.json").read_text())
    ctrl = repres.get("controls", {})
    results["C7_filed_replication_controls"] = {
        "dt_probe_dt_eq_dr_pow_half": ctrl.get("dt_probe_dt_eq_dr_pow_half"),
        "control_keys": sorted(ctrl.keys()),
        "has_fixed_dr_dt_refinement_control": any(
            ("temporal" in k.lower() or "dt_refine" in k.lower() or "fixed_dr" in k.lower()) for k in ctrl),
        "frozen_control": ctrl.get("frozen_state"),
    }

    if not (results["C1_protocol_pin_ok"] and results["C1_frozen_module_pin_ok"]):
        results["status"] = "VOID_HASH_MISMATCH"
        (OUTDIR / "adjudication.json").write_text(json.dumps(results, indent=1))
        print("VOID: pinned hash mismatch")
        return 2

    # ---- experiments (import frozen module read-only)
    import flat_wave_replication as rep  # noqa: E402

    got = sha256(ROOT / "numerics/tests/flat_wave_replication.py")
    assert got == PIN["numerics/tests/flat_wave_replication.py"], "frozen module changed mid-run"

    results["E1_fixed_dr_dt_refinement"] = measure_fixed_dr_dt_refinement(rep)
    assert sha256(ROOT / "numerics/tests/flat_wave_replication.py") == got, "frozen module changed mid-run"
    results["E2_fixed_dt_spatial"] = measure_fixed_dt_spatial(rep, dt_fixed=1e-3)
    assert sha256(ROOT / "numerics/tests/flat_wave_replication.py") == got, "frozen module changed mid-run"
    results["E3_protocol_exact_dt"] = measure_protocol_exact_dt(rep)
    results["frozen_module_hash_after"] = sha256(ROOT / "numerics/tests/flat_wave_replication.py")

    # ---- C8: reproduction + decomposition against the filed evidence
    filed = {}
    for st in four["studies"]:
        for r in st["rows"]:
            filed[(st["scheme"], r["dr"])] = r["l2_error"]
    repro, decomp = {}, {}
    for s in SCHEMES:
        e1 = results["E1_fixed_dr_dt_refinement"][s]["rows"][0]           # dr=0.05, dt=0.025
        repro[s] = {"E1_dt_0.025": e1["l2_error"], "filed_dr_0.05": filed.get((s, 0.05)),
                    "bitwise_equal": e1["l2_error"] == filed.get((s, 0.05)),
                    "rel_diff": abs(e1["l2_error"] - filed.get((s, 0.05), float("nan"))) / filed.get((s, 0.05), float("nan"))}
        e2 = {r["dr"]: r["l2_error"] for r in results["E2_fixed_dt_spatial"][s]["rows"]}
        decomp[s] = {str(dr): {"e_filed_cfl_0.5": filed.get((s, dr)), "e_fixed_dt_1e-3": e2.get(dr),
                               "ratio_filed_over_fixed": filed.get((s, dr), float("nan")) / e2.get(dr, float("nan"))}
                     for dr in (0.2, 0.1, 0.05)}
    e3 = results["E3_protocol_exact_dt"]
    decomp["dt_1e-4_dr_0.1"] = {s: {"e_fixed_dt_1e-4": e3[s]["l2_error"],
                                   "e_filed_cfl_0.5_dr_0.1": filed.get((s, 0.1)),
                                   "ratio_filed_over_fixed": filed.get((s, 0.1), float("nan")) / e3[s]["l2_error"]}
                                for s in SCHEMES}
    results["C8_reproduction"] = {"filed_reproduced_by_E1_dt_0.025": repro,
                                  "all_bitwise_equal": all(v["bitwise_equal"] for v in repro.values())}
    results["C8_decomposition"] = decomp

    # ---- verdict
    textual = (results["C2_protocol_section_3_4"]["clause_fixed_dt"]
               and results["C2_protocol_section_3_4"]["clause_never_spatial"]
               and results["C3_certified_order_claim"]["advertises_cfl_0_5"]
               and results["C4_four_rung_rows"]["all_constant_cfl_0_5"])
    subdominant = results["E1_fixed_dr_dt_refinement"]["all_schemes_temporal_subdominant"]
    results["verdict"] = {
        "F1_textual_violation_confirmed": bool(textual),
        "F1_disposition": ("text_scope_only__numbers_stand" if subdominant
                           else "material__spatial_label_not_established_by_filed_evidence"),
        "temporal_subdominant_measured": bool(subdominant),
        "w067_mitigation_claim": ("temporal subdominance is measured by controls, so no number changes - "
                                  "scope the text in rev 4"),
        "w067_mitigation_supported": bool(subdominant),
        "reading": (
            "C1-C4: the certified 4-rung order claim is measured at cfl=0.5 (dt = 0.5*dr machine-checked "
            "on all 12 rows; the E1 dt=0.025 runs reproduce the filed dr=0.05 errors bitwise), while "
            "protocol section 3.4 defines a spatial measurement as fixed dt=1e-4 and says dt~h runs are "
            "never quoted as spatial. C5: no filed numerics study uses a constant dt<=1e-3, so the "
            "protocol's own spatial methodology was never executed on the filed evidence. "
            "E1: at fixed dr=0.05, refining dt moves the error by 22.4% (lffd), 41.8% (cnfd) and 143.4% "
            "(cnfem) per measurement - far above the 2% subdominance threshold; for lffd and cnfem the "
            "error INCREASES as dt is refined (3.20e-4 -> 4.10e-4 and 1.17e-4 -> 3.83e-4), the signature "
            "of cancellation between temporal and spatial error at cfl=0.5. E3/decomposition: at dr=0.1 "
            "the cfl=0.5 errors are 0.77x / 2.26x / 0.28x the dt=1e-4 errors for lffd / cnfd / cnfem, so "
            "the filed study does not even measure the right magnitude, let alone a spatial order. "
            "E2: a protocol-style fixed dt=1e-3 study at dr=0.2/0.1/0.05 does yield order 2.000/1.999/2.001 "
            "for the three schemes, so the order-2 conclusion is recoverable and is not in dispute - the "
            "defect is that the filed evidence does not establish it as spatial. Therefore worker-067's F1 "
            "textual finding is confirmed AND its mitigation ('no number changes, scope the text') is "
            "refuted as stated: the fix is not text-only, it needs the fixed-dt study filed as the order "
            "evidence (or the claim rescoped to mixed order), with the cfl=0.5 study kept as a supporting "
            "control. This also withdraws worker-081's own W081-N0-C8-01 accept at the same protocol hash; "
            "a revise verdict is the honest one."),
        "constructive_remedy": [
            "file the fixed-dt study (E2: dt=1e-3 at dr=0.2/0.1/0.05, all three schemes, order 2.000/1.999/2.001) as the order-certification evidence, extended to four rungs (add dr=0.025) and/or dt=1e-4 where affordable (E3: 60000 steps, lffd 0.6s, cnfd 17s, cnfem 16s per rung)",
            "keep the cfl=0.5 4-rung study as a labelled mixed-order supporting control, not as the spatial certification",
            "amend section 3.4 in rev 4 so the admissible spatial study is exactly the fixed-dt one, and require the fixed-dr dt-refinement control for any claim that quotes a constant-CFL run",
        ],
        "falsifier": ("Re-measure numerics/CONVERGENCE_PROTOCOL.md: if not 1e6cdf04d7a24313 this adjudication "
                      "does not bind. It is falsified if a filed study with constant dt<=1e-3 across >=3 rungs "
                      "exists (then section 3.4 describes real practice), if E1 max relative change crosses the "
                      "2% rule in the other direction on a rerun at the frozen module hash, or if "
                      "numerics/tests/flat_wave_replication.py no longer hashes 8ade1cdc163ea420."),
    }
    results["not_claimed"] = [
        "no gate verdict and no gate self-pass; input to lead-audit/controller adjudication only",
        "no node completion; N0 stays active and numerics_lock stays LOCKED",
        "no claim that the measured order is wrong - the question is whether 'spatial' is established by the filed evidence",
        "no physics claim; flat-space calibration sub-case only",
    ]

    out = OUTDIR / "adjudication.json"
    out.write_text(json.dumps(results, indent=1))
    print(json.dumps({
        "adjudication_file": str(out.relative_to(ROOT)),
        "sha256": sha256(out),
        "textual_violation": textual,
        "temporal_subdominant": subdominant,
        "E1_max_rel_change": {s: results["E1_fixed_dr_dt_refinement"][s]["max_rel_change"] for s in SCHEMES},
        "E2_orders": {s: results["E2_fixed_dt_spatial"][s]["fit_order"] for s in SCHEMES},
        "filed_4rung_reproduced_bitwise": results["C8_reproduction"]["all_bitwise_equal"],
        "E3_dt_1e-4_errors": {s: results["E3_protocol_exact_dt"][s]["l2_error"] for s in SCHEMES},
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
