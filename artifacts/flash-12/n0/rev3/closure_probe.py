#!/usr/bin/env python3
"""Mechanical closure matrix for the G-NUM protocol review findings C1-C4.

Task: class AF-WCC-SCALAR-SPH / node N0 / gate G-NUM.  Takes the review
`reviews/G-NUM-protocol-review.json` (astra-lead-audit, verdict revise, C1-C4) and
evaluates, at pinned hashes, which findings are closed, partially closed, or open.
Also independently re-measures the R5 uncertainty of the controller-verified 3-rung
run 6542db93 from its own rows (spot verification of the w14 recomputation).

This script mutates nothing.  It is evidence for lead-numerics / lead-audit / Astra;
it sets no node status, no gate verdict, and claims no completion.

Run:  python3 artifacts/flash-12/n0/rev3/closure_probe.py
Writes: audit_finding_closure.json, closure_stdout.txt next to this file.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))

FIXED = ROOT / "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json"
PROTOCOL = ROOT / "numerics/CONVERGENCE_PROTOCOL.md"
RUBRIC = ROOT / "evaluation_rubric.yaml"
FOUR_RUNG = ROOT / "numerics/tests/n0_order_4rung.json"
HASHES = ROOT / "runtime/state/artifact_hashes.json"
MAP = ROOT / "research_map/research_map.json"
REVIEW = ROOT / "reviews/G-NUM-protocol-review.json"
W14 = ROOT / "runtime/state/w14_checkpoint_1.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(path: Path, text: str = None) -> str:
    return f"{path.relative_to(ROOT)}#{sha256(path)[:16]}"


def lsq(xs, ys):
    """Least-squares slope, slope standard error, residual SSE, for y = a + p x."""
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = my - slope * mx
    sse = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    se = math.sqrt(sse / (n - 2) / sxx) if n > 2 else float("inf")
    return slope, se, sse


def r5_from_rows(rows, err_key="l2_error", step_key="dr"):
    xs = [math.log(r[step_key]) for r in rows]
    ys = [math.log(r[err_key]) for r in rows]
    slope, se, sse = lsq(xs, ys)
    pairs = []
    for i in range(len(rows) - 1):
        num = math.log(rows[i][err_key] / rows[i + 1][err_key])
        den = math.log(rows[i][step_key] / rows[i + 1][step_key])
        pairs.append(num / den)
    half_range = (max(pairs) - min(pairs)) / 2.0
    delta = max(half_range, se)
    return {
        "fit_order": slope,
        "least_squares_se": se,
        "sse": sse,
        "pair_orders": pairs,
        "pair_half_range": half_range,
        "delta_R5": delta,
        "n_rungs": len(rows),
    }


def r5_agree(pa, da, pb, db, floor=0.25):
    bound = max(floor, math.sqrt(da * da + db * db))
    return {"abs_order_diff": abs(pa - pb), "r5_bound": bound, "agree": abs(pa - pb) <= bound}


def main() -> dict:
    fixed = json.loads(FIXED.read_text())
    protocol_text = PROTOCOL.read_text()
    rubric_text = RUBRIC.read_text()
    four = json.loads(FOUR_RUNG.read_text())
    hashes = json.loads(HASHES.read_text())
    research_map = json.loads(MAP.read_text())
    review = json.loads(REVIEW.read_text())

    # ---- R5 retro-fit of the controller-verified 3-rung run -----------------
    r5 = {}
    for study in fixed["order_studies"]:
        scheme = study["scheme"]
        m = r5_from_rows(study["rows"])
        m["stored_fit_order"] = study["fit_order"]
        m["stored_fit_order_delta"] = abs(m["fit_order"] - study["fit_order"])
        m["stored_pair_orders_match"] = all(
            abs(a - b) <= 1e-9 for a, b in zip(m["pair_orders"], study["pair_orders"])
        )
        r5[scheme] = m
    r5_pairs = {}
    schemes = sorted(r5)
    for i in range(len(schemes)):
        for j in range(i + 1, len(schemes)):
            a, b = schemes[i], schemes[j]
            r5_pairs[f"{a} vs {b}"] = r5_agree(
                r5[a]["fit_order"], r5[a]["delta_R5"], r5[b]["fit_order"], r5[b]["delta_R5"]
            )
    w14 = json.loads(W14.read_text())
    w14_answers = w14["assignment_closures"]["astra-numfix-03"]["answers"]
    w14_deltas = {"lffd": 1.05e-03, "cnfd": 3.15e-03, "cnfem": 2.75e-03}
    delta_vs_w14 = {k: abs(r5[k]["delta_R5"] - v) for k, v in w14_deltas.items()}
    r5_block = {
        "source": ref(FIXED),
        "rule": "protocol sec3.8 (R5): delta = max(pair-spread half-range, LS slope SE); "
                "agree iff |pA-pB| <= max(0.25, sqrt(dA^2+dB^2))",
        "per_scheme": r5,
        "pairwise": r5_pairs,
        "all_pairs_agree": all(v["agree"] for v in r5_pairs.values()),
        "w14_reported_deltas": w14_deltas,
        "delta_abs_diff_vs_w14": delta_vs_w14,
        "w14_spot_check_ok": all(v <= 5e-5 for v in delta_vs_w14.values()),
        "all_stored_fit_orders_reproduced_lt_1e-9": all(
            v["stored_fit_order_delta"] < 1e-9 for v in r5.values()
        ),
        "all_stored_pair_orders_reproduced_le_1e-9": all(
            v["stored_pair_orders_match"] for v in r5.values()
        ),
    }

    # ---- four-rung addendum (C2 evidence level) ------------------------------
    four_studies = []
    for st in four["studies"]:
        four_studies.append({
            "scheme": st["scheme"],
            "n_rungs": len(st["rows"]),
            "fit_order": st["fit_order"],
            "delta": st.get("delta"),
            "monotone": st.get("monotone"),
            "within_band_p2_0p3": abs(st["fit_order"] - 2.0) <= 0.3,
        })
    four_block = {
        "source": ref(FOUR_RUNG),
        "studies": four_studies,
        "all_have_ge_4_rungs": all(s["n_rungs"] >= 4 for s in four_studies),
        "all_within_band": all(s["within_band_p2_0p3"] for s in four_studies),
        "all_monotone": all(bool(s["monotone"]) for s in four_studies),
    }

    # ---- C1: scheme-appropriate invariant rule in the protocol --------------
    c1_markers = {
        "R1_declare_functional": bool(re.search(r"R1\s*[-\u2014\u2013]\s*declare the functional", protocol_text)),
        "R2_exact_discrete": bool(re.search(r"R2\s*[-\u2014\u2013]\s*exact discrete conservation", protocol_text)),
        "R3_convergent": bool(re.search(r"R3\s*[-\u2014\u2013]\s*convergent diagnostics", protocol_text)),
        "R4_no_cross_scheme": bool(re.search(r"R4\s*[-\u2014\u2013]\s*no cross-scheme functional gate", protocol_text)),
        "revision_log_rev2": "rev 2" in protocol_text and "R1\u2013R5a" in protocol_text,
        "replication_rule_amendment_b": "Each scheme is judged on its own declared invariant" in protocol_text,
    }
    c1 = {
        "finding": "protocol sec4/6 did not encode per-scheme structural invariants "
                   "(harness functional leapfrog-pinned; cross-check only)",
        "status": "closed_by_protocol_rev2" if all(c1_markers.values()) else "open",
        "markers": c1_markers,
        "audit_pin": review["artifact_sha256"],
        "current_protocol": ref(PROTOCOL),
        "note": "audit pinned the pre-rev2 protocol; the rev2 hash differs by design",
    }

    # ---- C2: resolution-count mismatch (rubric >=4 vs protocol >=3) ---------
    rubric_ge4 = bool(re.search(r"at least 4 resolutions", rubric_text)) and bool(
        re.search(r">=\s*4 resolutions", rubric_text)
    )
    protocol_ge3 = bool(re.search(r"At least three resolutions", protocol_text))
    protocol_prefers4 = bool(re.search(r"four or more rungs are preferred", protocol_text))
    c2 = {
        "finding": "A0 rubric G-NUM requires >= 4 resolutions; protocol sec3.2 requires >= 3; "
                   "the FIXED order study used 3",
        "status": "partial_evidence_closed_documentation_open"
                  if (rubric_ge4 and protocol_ge3 and four_block["all_have_ge_4_rungs"])
                  else "open",
        "rubric_ge4_text": rubric_ge4,
        "protocol_ge3_text": protocol_ge3,
        "protocol_prefers_4plus_text": protocol_prefers4,
        "rubric_ref": ref(RUBRIC),
        "protocol_ref": ref(PROTOCOL),
        "four_rung_evidence": four_block,
        "owner": "protocol owner (astra-lead-numerics) or rubric owner (lead-audit); "
                 "not silently by numerics",
    }

    # ---- C3: fit uncertainty (R5) -------------------------------------------
    protocol_r5 = bool(re.search(r"Order carries an uncertainty \(R5\)", protocol_text))
    protocol_r5a = bool(re.search(r"names the error norm \(L2 integral or L-infinity\)", protocol_text))
    c3 = {
        "finding": "FIXED run reported fit slopes and pair orders without SE / half-spread / delta; "
                   "agreement comparison did not carry delta",
        "status": "closed_at_protocol_and_recomputed_evidence_level"
                  if (protocol_r5 and protocol_r5a and r5_block["all_pairs_agree"]
                      and r5_block["all_stored_fit_orders_reproduced_lt_1e-9"])
                  else "open",
        "protocol_r5_text": protocol_r5,
        "protocol_r5a_text": protocol_r5a,
        "r5_retrofit": r5_block,
        "note": "the FIXED artifact itself is unchanged and still carries no delta field; "
                "R5 quantities are recomputed here and match w14 within 5e-5",
    }

    # ---- C4: registration + cnfem solver tolerance ---------------------------
    hash_blob = json.dumps(hashes)
    fixed_sha = sha256(FIXED)
    registered = (fixed_sha in hash_blob) or any(
        "n0_replication_astra_run2_FIXED" in k for k in hashes.get("hashes", {})
    )
    tol_present = "solver_tolerance_reported" in FIXED.read_text()
    c4 = {
        "finding": "FIXED run unverified and not registered under its sha256 in "
                   "runtime/state/artifact_hashes.json; cnfem solver_tolerance_reported null",
        "status": "open" if (not registered or not tol_present) else "closed",
        "fixed_sha256": fixed_sha,
        "registered_in_artifact_hashes": registered,
        "validation_status": fixed.get("validation_status"),
        "solver_tolerance_reported_present": tol_present,
        "hashes_ref": ref(HASHES),
        "owner": "registration: controller/Astra; tolerance field: flat_wave_replication.py owner",
    }

    # ---- lock state ----------------------------------------------------------
    lock = research_map.get("numerics_lock", {})
    gates = {g["gate_id"]: g.get("verdict") for g in research_map.get("gates", [])}
    lock_block = {
        "numerics_lock_state": lock.get("state"),
        "locked_nodes": lock.get("locked_nodes"),
        "required_gates": lock.get("required_gates"),
        "gate_verdicts": gates,
        "spherical_solver_present": (ROOT / "numerics/spherical_solver").exists(),
        "map_ref": ref(MAP),
    }

    open_findings = [k for k, v in (("C1", c1), ("C2", c2), ("C3", c3), ("C4", c4))
                     if not v["status"].startswith("closed")]
    out = {
        "schema": "flash-12/audit-finding-closure/v1",
        "event_id": "flash-12-n0-closure-0010-local",
        "actor": "deepseek-flash-12",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N0",
        "gate": "G-NUM",
        "conclusion_type": "mechanical_evidence",
        "task": "close-or-substantiate the four findings C1-C4 of "
                "reviews/G-NUM-protocol-review.json at pinned hashes, without editing any frozen artifact",
        "review_under_test": {
            "path": ref(REVIEW),
            "event_id": review.get("event_id"),
            "reviewer": review.get("reviewer"),
            "verdict": review.get("verdict"),
            "score": review.get("score"),
            "hard_failures": review.get("hard_failures"),
        },
        "inputs": {
            "protocol": ref(PROTOCOL),
            "rubric": ref(RUBRIC),
            "fixed_run": ref(FIXED),
            "four_rung": ref(FOUR_RUNG),
            "artifact_hashes": ref(HASHES),
            "research_map": ref(MAP),
            "w14_checkpoint": ref(W14),
        },
        "findings": {"C1": c1, "C2": c2, "C3": c3, "C4": c4},
        "open_findings": open_findings,
        "lock_state": lock_block,
        "summary": {
            "C1": c1["status"],
            "C2": c2["status"],
            "C3": c3["status"],
            "C4": c4["status"],
            "r5_all_pairs_agree": r5_block["all_pairs_agree"],
            "r5_w14_spot_check_ok": r5_block["w14_spot_check_ok"],
            "n1_lock_honored": (not lock_block["spherical_solver_present"])
                               and lock_block["numerics_lock_state"] == "locked",
        },
        "falsifiers": [
            "protocol 3345e17d lacks any of the R1/R2/R3/R4 markers -> C1-closed claim false",
            "recomputed R5 delta differs from w14 by > 5e-5, or any pair |dp| exceeds "
            "max(0.25, sqrt(dA^2+dB^2)), or any stored fit/pair order is not reproduced "
            "to 1e-9 -> C3 evidence-closure claim false",
            "artifact_hashes.json contains 6542db93 or an n0_replication_astra_run2_FIXED entry, "
            "or the report carries solver_tolerance_reported -> C4-open claim false",
            "rubric and protocol resolution-count texts agree at the pinned hashes -> C2 partial claim false",
            "a numerics/spherical_solver/ directory exists or numerics_lock is not locked -> "
            "the N1-lock-honored item is false",
        ],
        "next_falsifier": "re-run this probe after any change to reviews/G-NUM-protocol-review.json, "
                          "numerics/CONVERGENCE_PROTOCOL.md, evaluation_rubric.yaml, the FIXED run, "
                          "or runtime/state/artifact_hashes.json",
        "not_claimed": [
            "no review verdict: this is mechanical evidence, not a peer review",
            "no gate verdict and no gate self-pass; G-NUM adjudication stays with Astra",
            "no node completion; N0 stays active and numerics_lock stays LOCKED",
            "no physics, WCC/SCC or censorship claim (flat-space calibration only)",
            "no edit to any frozen artifact; numerics/tests/flat_wave.py stays at 8b52014dac47f996",
        ],
    }
    return out


if __name__ == "__main__":
    result = main()
    (HERE / "audit_finding_closure.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    lines = [
        "G-NUM audit-finding closure matrix (worker-12, mechanical evidence; no verdict, no completion)",
        f"created_at: {result['created_at']}",
        f"class/node/gate: {result['class_id']} / {result['node_id']} / {result['gate']}",
        f"review under test: {result['review_under_test']['path']} verdict={result['review_under_test']['verdict']}",
        "",
    ]
    for k in ("C1", "C2", "C3", "C4"):
        f = result["findings"][k]
        lines.append(f"{k}: {f['status']}")
        lines.append(f"    finding: {f['finding']}")
    lines.append("")
    lines.append("R5 retro-fit of the controller-verified 3-rung run:")
    for s, v in sorted(result["findings"]["C3"]["r5_retrofit"]["per_scheme"].items()):
        lines.append(f"    {s}: p={v['fit_order']:.9f}  se={v['least_squares_se']:.3e}  "
                     f"half_range={v['pair_half_range']:.3e}  delta={v['delta_R5']:.3e}  "
                     f"n={v['n_rungs']}")
    for pair, v in sorted(result["findings"]["C3"]["r5_retrofit"]["pairwise"].items()):
        lines.append(f"    {pair}: |dp|={v['abs_order_diff']:.3e} <= {v['r5_bound']:.3f} -> {v['agree']}")
    lines.append(f"    w14 spot check ok: {result['findings']['C3']['r5_retrofit']['w14_spot_check_ok']}")
    lines.append("")
    lines.append(f"lock: {result['lock_state']['numerics_lock_state']}  "
                 f"spherical_solver_present={result['lock_state']['spherical_solver_present']}  "
                 f"gates={result['lock_state']['gate_verdicts']}")
    lines.append(f"open findings: {result['open_findings']}")
    (HERE / "closure_stdout.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    sys.exit(0)
