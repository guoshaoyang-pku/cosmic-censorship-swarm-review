#!/usr/bin/env python3
"""W085-N0-STOPRULE-INDEP-01 -- independent re-measurement of the N0 stop-rule closure.

Class: AF-WCC-SCALAR-SPH   Node: N0   Gate: G-NUM
Target under test: numerics/results/flat_wave_convergence_rev3.json (frozen run hash
da7c360719950f7e...) produced by astra-lead-numerics at 2026-09-12T00:44:23+08:00.

What this does (read-only; NO solver is executed, NO canonical artifact is written):
  1. Re-hash every path the rev3 report pins and compare with the declared sha256.
  2. Re-derive the fixed-dt spatial order p for each scheme from the report's OWN
     per-rung l2_error_by_dr table with an independently written least-squares fit,
     and compare against the declared fit_order / pair_orders / least_squares_se /
     delta_R5 (= half of the pairwise-order range).
  3. Apply the report's own falsifier battery: dt == 1e-4 everywhere, >= 4 rungs,
     strictly monotone ladders, |p - 2| <= 0.3, cross-scheme |dp| <= 0.25.
  4. Resolve the three declared independent-replication verdicts: measured sha256 vs
     the disk_sha256 recorded in the report; shared input pins (frozen module
     8ade1cdc, protocol 1e6cdf04) vs live bytes; and numeric agreement of each
     verdict's own fixed-dt order/delta_R5 with the rev3 declaration. Whether each
     verdict literally names the rev3 report hash is recorded, not required: the
     verdicts predate rev3 and bind its inputs instead.
  5. Re-bind the class to F0 rev5 (0abb9ed8a961) and confirm AF-WCC-SCALAR-SPH is present.
  6. Drift guard: every input is re-hashed after the computation and must be unchanged.

Exit code 0 when every hard check passes, 3 when any hard check fails, 2 on drift.
"""
import hashlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

TARGET = "numerics/results/flat_wave_convergence_rev3.json"
TARGET_SHA = "da7c360719950f7ef6be2624391dee464f8c818a0be74ec44f0f8c70d2b28ac3"
FROZEN_MODULE_SHA = "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422"
PROTOCOL_SHA = "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274"
CERT_BASIS_SHA = "1677822ceb9c81e8f6e48dee8360ab13edc35623c51f4be68bd6589a5fe79920"

# (path, declared sha256, declared by)
PINS = [
    ("numerics/results/flat_wave_convergence_rev3.json", TARGET_SHA, "assignment pin / self"),
    ("numerics/CONVERGENCE_PROTOCOL.md", PROTOCOL_SHA, "certification_basis.protocol_sha256"),
    ("numerics/tests/flat_wave_replication.py", FROZEN_MODULE_SHA,
     "certification_basis.frozen_module.sha256"),
    ("numerics/protocol/n0_fixed_dt_certification.json", CERT_BASIS_SHA,
     "certification_basis.sha256"),
    ("numerics/results/flat_wave_convergence.json",
     "e9e124227c4d29323f8bf9d4071a21da4484c1fdfdb67d4237dad8b8fe14bd2e",
     "supporting_diagnostics.canonical_mixed_order_run.sha256"),
    ("numerics/protocol/temporal_subdominance_control.json",
     "334f5b71e0d53ab6ed1f3b7133abca541a36dafc9a5cfb4f62f0655839dd964b",
     "temporal_control.sha256"),
    ("numerics/tests/n0_order_4rung.json",
     "c88146a1375c50f0c87d2893109087ee6f08c55919a4812dc073750bd86f544a",
     "certification_basis.supersedes_evidence_basis.constant_cfl_ladder"),
    ("research_map/formulation_taxonomy.yaml",
     "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
     "class_binding.sha256"),
    ("artifacts/formulation/formulation_taxonomy.yaml",
     "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
     "F0 companion supplement (REC-3)"),
]

# replication verdicts as declared by the report (path, disk sha256 it records, label)
REPLICATION = [
    ("artifacts/worker-046/n0_fixed_dt_independent/verification.json",
     "814452111bc8912bb21f8e0a353fe78096640d299e469578462b755592ea9a61", "W046"),
    ("artifacts/worker-057/n0_fixeddt_verify/report.json",
     "b906445878f3130dd710595a362883e29be87f11cb8d8edbdbc79539147b3b04", "W057"),
    ("artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json",
     "65ae766d9e4c205762cff35fb822915d4b00bd4502a0326455bed84e7b3169d6", "W081"),
]

SCHEMES = ["lffd", "cnfd", "cnfem"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ls_slope(xs, ys):
    """Ordinary least squares slope + residual standard error of the slope."""
    n = len(xs)
    xb = sum(xs) / n
    yb = sum(ys) / n
    sxx = sum((x - xb) ** 2 for x in xs)
    sxy = sum((x - xb) * (y - yb) for x, y in zip(xs, ys))
    slope = sxy / sxx
    inter = yb - slope * xb
    sse = sum((y - (inter + slope * x)) ** 2 for x, y in zip(xs, ys))
    se = math.sqrt((sse / (n - 2)) / sxx) if n > 2 and sxx > 0 else 0.0
    return slope, se, inter, sse


def find_key(obj, needle):
    if isinstance(obj, str):
        return needle in obj
    if isinstance(obj, dict):
        return any(find_key(v, needle) for v in obj.values())
    if isinstance(obj, list):
        return any(find_key(v, needle) for v in obj)
    return False


def extract_verdict_numbers(label, doc, scheme):
    """Pull (fit_order, delta_R5) each verdict states for a scheme, from its own schema."""
    try:
        if label == "W046":
            h = doc["headline"][scheme]
            return h.get("fit_order_fixed_dt"), h.get("delta_R5_fixed_dt")
        if label == "W057":
            r = doc["recomputed"][scheme]
            return r.get("order_ls"), r.get("delta_R5")
        if label == "W081":
            c = doc["check_C_independent_arithmetic"]["per_scheme"][scheme]["recomputed"]
            return c.get("fit_order"), c.get("delta_R5")
    except (KeyError, TypeError):
        return None, None
    return None, None


def main():
    checks = []

    def check(cid, ok, detail, severity="hard"):
        checks.append({"check_id": cid, "pass": bool(ok), "detail": detail,
                       "severity": severity})

    # ---- 1. pin resolution -------------------------------------------------
    pre = {}
    pin_rows = []
    for rel, declared, source in PINS:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            pin_rows.append({"path": rel, "declared": declared, "measured": None,
                             "resolved": False, "declared_by": source,
                             "mtime": None, "bytes": None})
            check("pin::%s" % rel, False, "missing file (declared by %s)" % source)
            continue
        measured = sha256(path)
        pre[rel] = measured
        row = {
            "path": rel, "declared": declared, "measured": measured,
            "resolved": measured == declared,
            "declared_by": source,
            "mtime": os.path.getmtime(path),
            "bytes": os.path.getsize(path),
        }
        pin_rows.append(row)
        check("pin::%s" % rel, row["resolved"],
              "declared %s / measured %s (%s)" % (declared[:16], measured[:16], source))

    # ---- 2/3. order re-derivation and falsifier battery --------------------
    with open(os.path.join(ROOT, TARGET)) as fh:
        report = json.load(fh)

    cb = report["certification_basis"]
    schemes = cb["schemes"]
    order_rows = []
    for s in SCHEMES:
        v = schemes[s]
        errs = {float(k): float(x) for k, x in v["l2_error_by_dr"].items()}
        drs = sorted(errs)                       # 0.025 ... 0.2
        xs = [math.log(d) for d in drs]
        ys = [math.log(errs[d]) for d in drs]
        p, se, _, _ = ls_slope(xs, ys)

        ref = sorted(errs, reverse=True)         # coarse -> fine
        pair = [math.log(errs[ref[i]] / errs[ref[i + 1]]) / math.log(ref[i] / ref[i + 1])
                for i in range(len(ref) - 1)]
        pair_range = max(pair) - min(pair)
        half_range = pair_range / 2.0            # rev3's delta_R5 / pair_half_range
        declared_pair = [float(x) for x in v["pair_orders"]]
        monotone = all(errs[ref[i]] > errs[ref[i + 1]] for i in range(len(ref) - 1))

        row = {
            "scheme": s,
            "n_rungs": len(errs),
            "dr_values": drs,
            "dt": v.get("dt"),
            "recomputed_fit_order": p,
            "declared_fit_order": v.get("fit_order"),
            "abs_diff_fit_order": abs(p - v.get("fit_order", float("nan"))),
            "recomputed_least_squares_se": se,
            "declared_least_squares_se": v.get("least_squares_se"),
            "abs_diff_se": abs(se - v.get("least_squares_se", float("nan"))),
            "recomputed_pair_orders": pair,
            "declared_pair_orders": declared_pair,
            "max_abs_pair_diff": max(abs(a - b) for a, b in zip(pair, declared_pair)),
            "recomputed_pair_range": pair_range,
            "recomputed_delta_R5_half_range": half_range,
            "declared_delta_R5": v.get("delta_R5"),
            "abs_diff_delta_R5": abs(half_range - v.get("delta_R5", float("nan"))),
            "monotone_measured": monotone,
            "declared_monotone": v.get("monotone"),
            "within_band_measured": abs(p - 2.0) <= 0.3,
            "declared_within_band": v.get("within_band"),
        }
        order_rows.append(row)

        check("rungs::%s" % s, len(errs) >= 4,
              "rungs=%d (falsifier: fewer than four)" % len(errs))
        check("dr_set::%s" % s, drs == [0.025, 0.05, 0.1, 0.2],
              "dr ladder = %s" % drs)
        check("dt::%s" % s, abs(float(v.get("dt", -1)) - 1e-4) < 1e-15,
              "dt=%r (falsifier: dt != 1e-4)" % v.get("dt"))
        check("monotone::%s" % s, monotone and bool(v.get("monotone")),
              "recomputed monotone=%s, declared=%s" % (monotone, v.get("monotone")))
        check("fit_order::%s" % s, row["abs_diff_fit_order"] <= 1e-6,
              "recomputed %.15f vs declared %.15f (|diff|=%.3e)"
              % (p, v.get("fit_order", float("nan")), row["abs_diff_fit_order"]))
        check("pair_orders::%s" % s, row["max_abs_pair_diff"] <= 1e-6,
              "max |recomputed - declared| = %.3e" % row["max_abs_pair_diff"])
        check("ls_se::%s" % s, row["abs_diff_se"] <= 1e-9,
              "recomputed %.3e vs declared %.3e" % (se, v.get("least_squares_se", float("nan"))))
        check("delta_R5::%s" % s, row["abs_diff_delta_R5"] <= 1e-9,
              "recomputed half-range %.3e vs declared %.3e"
              % (half_range, v.get("delta_R5", float("nan"))))
        check("band::%s" % s, abs(p - 2.0) <= 0.3,
              "|p-2| = %.6f <= 0.3 (falsifier: outside band)" % abs(p - 2.0))

    declared_p = {s: float(report["order_claim"]["p_by_scheme"][s]) for s in SCHEMES}
    cross = max(declared_p.values()) - min(declared_p.values())
    declared_cross = float(report["order_claim"]["max_cross_scheme_abs_dp"])
    check("cross_scheme_dp", abs(cross - declared_cross) <= 1e-9 and cross <= 0.25,
          "declared max |dp| = %.3e, recomputed from p_by_scheme = %.3e, floor 0.25"
          % (declared_cross, cross))
    check("order_claim_band", all(abs(declared_p[s] - 2.0) <= 0.3 for s in SCHEMES),
          "declared p_by_scheme within |p-2| <= 0.3")

    # ---- 4. replication verdict chain --------------------------------------
    repl_rows = []
    reg = report.get("registration_state", {}).get("registry_generated_paths", {})
    numeric_matches = 0
    numeric_total = 0
    for rel, declared_disk, label in REPLICATION:
        path = os.path.join(ROOT, rel)
        row = {"label": label, "path": rel, "exists": os.path.exists(path)}
        if not row["exists"]:
            repl_rows.append(row)
            check("replication::%s" % label, False, "verdict file missing: %s" % rel)
            continue
        measured = sha256(path)
        pre[rel] = measured
        try:
            with open(path) as fh:
                doc = json.load(fh)
        except Exception as exc:  # noqa: BLE001
            repl_rows.append(row)
            check("replication::%s::parse" % label, False, "unreadable JSON: %s" % exc)
            continue
        blob = json.dumps(doc)
        row.update({
            "declared_disk_sha256": declared_disk,
            "measured_sha256": measured,
            "disk_hash_resolved": measured == declared_disk,
            "declared_in_report_registry": reg.get(rel, {}).get("disk_sha256"),
            "declares_frozen_module_8ade1cdc": FROZEN_MODULE_SHA in blob,
            "declares_protocol_1e6cdf04": PROTOCOL_SHA in blob,
            "declares_cert_basis_1677822c": CERT_BASIS_SHA in blob,
            "references_rev3_hash": find_key(doc, "da7c36071995"),
            "mtime": os.path.getmtime(path),
            "verdict": (doc.get("verdict") if not isinstance(doc.get("verdict"), dict)
                        else doc["verdict"].get("disposition")),
        })
        numeric = {}
        for s in SCHEMES:
            fit, delta = extract_verdict_numbers(label, doc, s)
            ref_fit = report["certification_basis"]["schemes"][s]["fit_order"]
            ref_delta = report["certification_basis"]["schemes"][s]["delta_R5"]
            numeric_total += 2
            ok_fit = fit is not None and abs(fit - ref_fit) <= 1e-9
            ok_delta = delta is not None and abs(delta - ref_delta) <= 1e-9
            numeric_matches += int(ok_fit) + int(ok_delta)
            numeric[s] = {
                "verdict_fit_order": fit, "rev3_fit_order": ref_fit,
                "fit_order_agrees": ok_fit,
                "verdict_delta_R5": delta, "rev3_delta_R5": ref_delta,
                "delta_R5_agrees": ok_delta,
            }
        row["numeric_agreement"] = numeric
        repl_rows.append(row)
        check("replication::%s::hash" % label, row["disk_hash_resolved"],
              "declared disk %s / measured %s" % (declared_disk[:16], measured[:16]))
        check("replication::%s::shared_pins" % label,
              row["declares_frozen_module_8ade1cdc"] and row["declares_protocol_1e6cdf04"],
              "binds rev3 frozen module 8ade1cdc=%s, protocol 1e6cdf04=%s"
              % (row["declares_frozen_module_8ade1cdc"], row["declares_protocol_1e6cdf04"]))
        check("replication::%s::numeric" % label,
              all(v["fit_order_agrees"] and v["delta_R5_agrees"] for v in numeric.values()),
              "6/6 fit_order+delta_R5 values agree with rev3: %s"
              % {s: (v["fit_order_agrees"], v["delta_R5_agrees"]) for s, v in numeric.items()})

    binding_note = {
        "verdicts_referencing_rev3_hash": sum(1 for r in repl_rows if r.get("references_rev3_hash")),
        "verdicts_with_shared_input_pins": sum(
            1 for r in repl_rows if r.get("declares_frozen_module_8ade1cdc")
            and r.get("declares_protocol_1e6cdf04")),
        "verdict_mtimes": {r["label"]: r.get("mtime") for r in repl_rows if "mtime" in r},
        "rev3_generated_at": report.get("generated_at"),
        "numeric_values_agreeing": "%d/%d" % (numeric_matches, numeric_total),
        "assessment": "The three verdicts predate the rev3 consolidation report and none of "
                      "their bytes names da7c36071995. They bind the same inputs the report "
                      "declares (frozen module 8ade1cdc, protocol 1e6cdf04; W057/W081 also the "
                      "certification basis 1677822c) and reproduce its declared fixed-dt "
                      "order and delta_R5 values exactly. The map's phrase 'three hash-matched "
                      "verdicts ... at frozen run hash da7c36071995' is therefore numeric "
                      "agreement plus shared-input pinning, not a literal hash reference; the "
                      "gate text should say so.",
    }

    # ---- 5. F0 re-bind -----------------------------------------------------
    with open(os.path.join(ROOT, "research_map/formulation_taxonomy.yaml"), encoding="utf-8") as fh:
        tax = fh.read()
    with open(os.path.join(ROOT, "artifacts/formulation/formulation_taxonomy.yaml"), encoding="utf-8") as fh:
        comp = fh.read()
    check("f0::class_present", "AF-WCC-SCALAR-SPH" in tax,
          "AF-WCC-SCALAR-SPH present in canonical taxonomy 0abb9ed8a961")
    check("f0::companion_present", "AF-WCC-SCALAR-SPH" in comp,
          "AF-WCC-SCALAR-SPH present in companion d7419b4e8963")
    check("f0::declared_binding",
          report["class_binding"]["sha256"] == pre["research_map/formulation_taxonomy.yaml"],
          "report class_binding.sha256 == measured taxonomy hash")

    # ---- scope compliance --------------------------------------------------
    check("lock::no_solver_dir",
          not os.path.exists(os.path.join(ROOT, "numerics", "spherical_solver")),
          "numerics/spherical_solver/ absent under numerics_lock=locked")

    # ---- registration statement --------------------------------------------
    try:
        with open(os.path.join(ROOT, "runtime/state/artifact_hashes.json")) as fh:
            reg_blob = json.dumps(json.load(fh))
        protocol_registered = "1e6cdf04d7a2" in reg_blob
        target_registered = "da7c36071995" in reg_blob
    except Exception as exc:  # noqa: BLE001
        protocol_registered = target_registered = False
        check("registration::readable", False, "artifact_hashes.json unreadable: %s" % exc)
    check("registration::protocol", protocol_registered,
          "protocol 1e6cdf04 present in runtime/state/artifact_hashes.json", severity="soft")
    check("registration::rev3_target", target_registered,
          "rev3 report da7c36071995 present in runtime/state/artifact_hashes.json",
          severity="soft")

    # ---- 6. drift guard ----------------------------------------------------
    drift = {}
    for rel, before in pre.items():
        after = sha256(os.path.join(ROOT, rel))
        if after != before:
            drift[rel] = {"before": before, "after": after}
    check("drift::stable", not drift, "input drift: %s" % json.dumps(drift))

    hard_fail = [c for c in checks if not c["pass"] and c["severity"] == "hard"]
    soft_fail = [c for c in checks if not c["pass"] and c["severity"] == "soft"]
    out = {
        "schema": "worker-independent-probe/v1",
        "task_id": "W085-N0-STOPRULE-INDEP-01",
        "actor": "worker-085",
        "target": TARGET,
        "target_sha256": pre.get(TARGET),
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N0",
        "gate": "G-NUM",
        "method": "independently written least-squares re-derivation from the report's own "
                  "per-rung l2_error_by_dr tables + full declared-hash resolution chain + "
                  "cross-check of the three declared replication verdicts; no solver executed, "
                  "no numerics process started, read-only",
        "pin_table": pin_rows,
        "order_recompute": order_rows,
        "replication_chain": repl_rows,
        "replication_binding_assessment": binding_note,
        "checks": checks,
        "summary": {
            "checks_total": len(checks),
            "checks_passed": sum(1 for c in checks if c["pass"]),
            "hard_failures": [c["check_id"] for c in hard_fail],
            "soft_failures": [c["check_id"] for c in soft_fail],
            "verdict": "pass" if not hard_fail else "fail",
        },
        "falsifiers": [
            "any pinned path re-hashed to a different sha256 voids the corresponding citation",
            "a recomputed fixed-dt order differing from the declared fit_order by more than 1e-6",
            "any scheme with dt != 1e-4, a non-monotone ladder, or fewer than four rungs",
            "a replication verdict whose measured sha256 differs from the report's recorded disk_sha256",
            "a replication verdict whose fit_order/delta_R5 disagrees with rev3 beyond 1e-9",
            "any input drift between the pre- and post-measurement hashing passes",
        ],
    }
    out_path = os.path.join(HERE, "probe.json")
    with open(out_path, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=False)
        fh.write("\n")
    print(json.dumps(out["summary"], indent=1))
    print("replication binding:", json.dumps(binding_note["numeric_values_agreeing"]),
          "| rev3-hash refs:", binding_note["verdicts_referencing_rev3_hash"],
          "| shared-pin verdicts:", binding_note["verdicts_with_shared_input_pins"])
    print("probe written:", out_path)
    if drift:
        return 2
    return 0 if not hard_fail else 3


if __name__ == "__main__":
    sys.exit(main())
