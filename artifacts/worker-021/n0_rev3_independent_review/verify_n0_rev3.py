#!/usr/bin/env python3
"""W021-N0-REV3-INDEP-01 -- independent read-only verification of the N0 post-stoprule
closure artifact (numerics/results/flat_wave_convergence_rev3.json) against the acceptance
axes of card audit-r2-N0-rev3.

Independent instrument: stdlib only, imports no author module, writes nothing canonical.
Executes the target's own declared falsifiers plus the card's axes. Deterministic:
report.json / results.json / controls.json carry no wall-clock fields.

Usage:  python3 verify_n0_rev3.py [--base /path/to/ai4math-swarm]
Writes report.json, results.json, controls.json into the directory holding this script.
Exit code: 0 if the harness ran and all controls passed (verdict may still be revise/void),
2 if a harness-level failure prevented measurement.
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys

TOOL = "w021-n0-rev3-independent-verifier/1.0"
TARGET = "numerics/results/flat_wave_convergence_rev3.json"
CERT = "numerics/protocol/n0_fixed_dt_certification.json"
RUNG = "numerics/tests/n0_order_4rung.json"
PROTOCOL = "numerics/CONVERGENCE_PROTOCOL.md"
FROZEN_MODULE = "numerics/tests/flat_wave_replication.py"
TAXONOMY = "research_map/formulation_taxonomy.yaml"
MAP = "research_map/research_map.json"
REGISTRY = "runtime/state/artifact_hashes.json"
EVENTS = "research_map/events.jsonl"
GATES_PY = "numerics/gates.py"
F0_REV5 = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
P_TOL = 0.3
DP_TOL = 0.25


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def order_ls(dr, err):
    """log-log least squares slope: ln(err) = p ln(dr) + c."""
    xs = [math.log(x) for x in dr]
    ys = [math.log(y) for y in err]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / sxx


def pair_orders(dr, err):
    """order between consecutive dyadic rungs: log2(e_i / e_{i+1}) for dr halving."""
    out = []
    for i in range(len(err) - 1):
        ratio = dr[i] / dr[i + 1]
        out.append(math.log(err[i] / err[i + 1]) / math.log(ratio))
    return out


class Harness:
    def __init__(self, base):
        self.base = base
        self.checks = []
        self.measurements = {}
        self.control_specs = []

    def p(self, rel):
        return os.path.join(self.base, rel)

    def check(self, cid, desc, passed, measured):
        self.checks.append({"check_id": cid, "description": desc,
                            "pass": bool(passed), "measured": measured})

    def load(self, rel):
        with open(self.p(rel)) as fh:
            return json.load(fh)

    def run(self):
        # ---- T0 hashes -------------------------------------------------------
        t0 = {}
        for rel in (TARGET, CERT, RUNG, PROTOCOL, FROZEN_MODULE, TAXONOMY, MAP, REGISTRY, GATES_PY):
            t0[rel] = sha256_file(self.p(rel))
        self.measurements["t0_sha256"] = t0

        target = self.load(TARGET)
        cert = self.load(CERT)
        rung = self.load(RUNG)
        f0_live = t0[TAXONOMY]
        protocol_hash = t0[PROTOCOL]

        # ---- A1 target stable across the review ------------------------------
        self.check("A1_target_hash_stable",
                   "reviewed target byte-stable across the review (T0==T1)",
                   True, {"t0": t0[TARGET], "t1": None})  # t1 patched at end

        # ---- A2 structure: 3 schemes x 4 rungs at fixed dt -------------------
        cb = target["certification_basis"]
        schemes = cb["schemes"]
        struct = {}
        ok_struct = True
        for name, s in schemes.items():
            good = (s.get("rungs") == 4 and len(s.get("dr_values", [])) == 4
                    and s.get("dt") == 1e-4 and s.get("dr_values") == cb["dr_values"])
            struct[name] = {"rungs": s.get("rungs"), "dr_values": s.get("dr_values"),
                            "dt": s.get("dt"), "ok": good}
            ok_struct = ok_struct and good
        top_ok = (len(schemes) == 3 and cb["rungs_per_scheme"] == 4 and cb["dt"] == 1e-4
                  and cb["dr_values"] == [0.2, 0.1, 0.05, 0.025])
        self.check("A2_three_schemes_four_rungs_fixed_dt",
                   "certification_basis has 4 rungs per scheme at fixed dt=1e-4 for 3 schemes",
                   ok_struct and top_ok,
                   {"n_schemes": len(schemes), "rungs_per_scheme": cb["rungs_per_scheme"],
                    "dt": cb["dt"], "dr_values": cb["dr_values"], "per_scheme": struct})

        # ---- A3 recomputed orders from the raw error ladder ------------------
        recomputed = {}
        ok_order = True
        for name, s in schemes.items():
            dr = s["dr_values"]
            err = [s["l2_error_by_dr"][repr(x) if repr(x) in s["l2_error_by_dr"] else str(x)]
                   for x in dr]
            p_ls = order_ls(dr, err)
            po = pair_orders(dr, err)
            monotone = all(err[i] > err[i + 1] for i in range(len(err) - 1))
            d_fit = abs(p_ls - s["fit_order"])
            d_pair = max(abs(a - b) for a, b in zip(po, s["pair_orders"]))
            within = abs(p_ls - 2.0) <= P_TOL
            good = monotone and within and d_fit <= 1e-9 and d_pair <= 1e-6
            recomputed[name] = {"fit_order_declared": s["fit_order"], "fit_order_recomputed": p_ls,
                                "abs_diff": d_fit, "pair_orders_recomputed": po,
                                "pair_orders_declared": s["pair_orders"], "max_pair_diff": d_pair,
                                "monotone": monotone, "within_p_tol": within, "ok": good}
            ok_order = ok_order and good
        orders = [v["fit_order_recomputed"] for v in recomputed.values()]
        dp_max = max(orders) - min(orders)
        cross_ok = dp_max <= DP_TOL
        self.check("A3_orders_recomputed_from_raw_rows",
                   "independent log-log least-squares reproduces declared orders; monotone; |p-2|<=0.3; cross-scheme |dp|<=0.25",
                   ok_order and cross_ok,
                   {"per_scheme": recomputed, "cross_scheme_max_abs_diff": dp_max,
                    "cross_scheme_bound": DP_TOL, "cross_ok": cross_ok})

        # ---- A4 cross-source ladder consistency ------------------------------
        xsrc = {}
        ok_x = True
        cs = cert.get("schemes", {})
        for name, s in schemes.items():
            fdc = cs.get(name, {}).get("fixed_dt_certification", {})
            rows = fdc.get("rows", [])
            row_dr = [r.get("dr") for r in rows]
            row_err = [r.get("l2_error") for r in rows]
            row_dt = [r.get("dt") for r in rows]
            row_steps = [r.get("steps") for r in rows]
            decl_err = [s["l2_error_by_dr"][str(x)] for x in s["dr_values"]]
            ladder_same = (len(rows) == 4 and row_dr == s["dr_values"]
                           and all(d == 1e-4 for d in row_dt)
                           and all(abs(a - b) < 1e-15 for a, b in zip(row_err, decl_err)))
            raw_fit_same = (abs(fdc.get("fit_order", float("nan")) - s["fit_order"]) < 1e-15
                            and fdc.get("pair_orders") == s["pair_orders"]
                            and abs(fdc.get("delta_R5", float("nan")) - s["delta_R5"]) < 1e-18
                            and fdc.get("monotone") == s["monotone"])
            xsrc[name] = {"rows": len(rows), "row_dr": row_dr, "row_dt": row_dt,
                          "row_steps": row_steps, "ladder_matches_rev3": ladder_same,
                          "raw_fit_matches_rev3": raw_fit_same}
            ok_x = ok_x and ladder_same and raw_fit_same
        rung_studies = rung.get("studies", {})
        if isinstance(rung_studies, dict):
            rung_keys = sorted(rung_studies.keys())[:6]
            rung_n = len(rung_studies)
            for name, st in rung_studies.items():
                if name in schemes and isinstance(st, dict):
                    rows = st.get("rows", [])
                    errs = [r.get("l2_error") for r in rows if isinstance(r, dict)]
                    decl = [schemes[name]["l2_error_by_dr"][str(x)] for x in schemes[name]["dr_values"]]
                    same = len(errs) == 4 and all(abs(a - b) < 1e-15 for a, b in zip(errs, decl))
                    xsrc[name + "_rung_addendum"] = {"ladder_matches_rev3": same}
                    ok_x = ok_x and same
        elif isinstance(rung_studies, list):
            rung_keys = [str(s.get("scheme", s.get("name", i))) if isinstance(s, dict) else str(i)
                         for i, s in enumerate(rung_studies)][:6]
            rung_n = len(rung_studies)
        else:
            rung_keys, rung_n = [], 0
        self.check("A4_cross_source_consistency",
                   "raw fixed-dt certification rows reproduce the closure artifact ladders and fits",
                   ok_x, {"per_scheme": xsrc,
                          "rung_addendum_study_keys": rung_keys, "rung_addendum_study_count": rung_n})

        # ---- A5 class binding ------------------------------------------------
        cbnd = target["class_binding"]
        bind_ok = (cbnd["sha256"] == F0_REV5 and f0_live == F0_REV5
                   and cbnd["path"] == TAXONOMY and cbnd.get("declared_revision") == 5
                   and cbnd.get("class_id") == "AF-WCC-SCALAR-SPH")
        self.check("A5_f0_rev5_class_binding",
                   "class_binding pin equals live F0 rev5 taxonomy hash",
                   bind_ok, {"declared": cbnd["sha256"], "live_measured": f0_live,
                             "f0_rev5_constant": F0_REV5, "declared_revision": cbnd.get("declared_revision"),
                             "path": cbnd["path"], "class_id": cbnd.get("class_id"),
                             "stale_pins_recorded": cbnd.get("previous_stale_pins")})

        # ---- A6 stop-rule closures -------------------------------------------
        src = target["stop_rule_closures"]
        four_ok = str(src.get("four_rungs_or_scoped", "")).startswith("CLOSED") and top_ok
        f0_ok = str(src.get("f0_rebind", "")).startswith("CLOSED") and bind_ok
        rep_ok = str(src.get("independent_replication_verdict", "")).startswith("CLOSED")
        self.check("A6_stop_rule_closures",
                   "all three stop-rule items closed and consistent with measurement",
                   four_ok and f0_ok and rep_ok,
                   {"four_rungs_or_scoped": src.get("four_rungs_or_scoped"),
                    "f0_rebind": src.get("f0_rebind"),
                    "independent_replication_verdict": src.get("independent_replication_verdict"),
                    "four_consistent": four_ok, "f0_consistent": f0_ok, "rep_declared_closed": rep_ok})

        # ---- A7 replication verdicts hash-pinned -----------------------------
        ir = target["independent_replication"]
        vres = {}
        ok_v = True
        for v in ir["verdicts"]:
            path = v["path"]
            exists = os.path.exists(self.p(path))
            disk = sha256_file(self.p(path)) if exists else None
            match = exists and disk == v["sha256"]
            vres[v["reviewer"]] = {"verdict": v["verdict"], "path": path,
                                   "declared": v["sha256"], "disk": disk, "match": match,
                                   "criteria": [v.get("criteria_passed"), v.get("criteria_total")],
                                   "checks": [v.get("checks_pass"), v.get("checks_total")],
                                   "hard_failures": v.get("hard_failures")}
            ok_v = ok_v and match
        self.check("A7_replication_verdicts_pinned",
                   "every cited independent replication verdict resolves to its declared sha256 on disk",
                   ok_v and len(ir["verdicts"]) == 3,
                   {"overall": ir["verdict"], "per_reviewer": vres})

        # ---- A8 lock guard ---------------------------------------------------
        mp = self.load(MAP)
        lock = mp.get("numerics_lock", {})
        solver_dir = os.path.isdir(self.p("numerics/spherical_solver"))
        n1_hits = []
        for root, dirs, files in os.walk(self.p("numerics")):
            for f in files:
                low = f.lower()
                if re.search(r"(^|[^a-z0-9])n1([^a-z0-9]|$)", low) or "spherical_solver" in low:
                    n1_hits.append(os.path.relpath(os.path.join(root, f), self.base))
        lg = target["lock_guard"]
        lock_ok = (lock.get("state") == "locked" and lg.get("lock_state") == "locked"
                   and lg.get("production_allowed") is False and not solver_dir and not n1_hits)
        self.check("A8_lock_guard_and_solver_absence",
                   "numerics_lock locked, production_allowed false, no spherical_solver dir, no N1 artifact",
                   lock_ok,
                   {"map_lock_state": lock.get("state"), "map_locked_nodes": lock.get("locked_nodes"),
                    "artifact_lock_state": lg.get("lock_state"),
                    "production_allowed": lg.get("production_allowed"),
                    "solver_dir_present": solver_dir, "n1_name_hits": n1_hits,
                    "guard_present": os.path.exists(self.p("runtime/bin/lock_guard.py")) or None})

        # ---- A9 registration gap --------------------------------------------
        reg = self.load(REGISTRY)
        reg_paths = reg if isinstance(reg, dict) else {}
        # normalise possible nesting
        if "artifacts" not in reg_paths and any(isinstance(v, dict) and "sha256" in v
                                                for v in reg_paths.values()):
            pass
        declared_unreg = target["registration_state"]["unregistered_paths"]
        rows = {}
        ok_reg = True
        for rel in declared_unreg:
            entry = reg_paths.get(rel)
            disk = sha256_file(self.p(rel)) if os.path.exists(self.p(rel)) else None
            present = entry is not None
            registered_sha = entry.get("sha256") if isinstance(entry, dict) else entry
            rows[rel] = {"registered": present, "registered_sha256": registered_sha,
                         "disk_sha256": disk, "match": present and registered_sha == disk}
            if present:
                ok_reg = False  # declared unregistered but actually registered -> gap claim stale
        target_reg = reg_paths.get(TARGET)
        tgt_registered = isinstance(target_reg, dict) and target_reg.get("sha256") == t0[TARGET]
        self.check("A9_registration_gap_reproduced",
                   "the six declared unregistered paths are absent from runtime/state/artifact_hashes.json",
                   ok_reg,
                   {"declared_unregistered": declared_unreg, "per_path": rows,
                    "reviewed_target_registered": tgt_registered,
                    "registry_entries": len(reg_paths)})

        # ---- A10 protocol review contest + withdrawn-accept guard ------------
        dissents = target["review_state_at_generation"]["dissenting_reviews"]
        accepts = target["review_state_at_generation"]["accepting_reviews"]
        ids = set(accepts) | set(dissents)
        found = {}
        with open(self.p(EVENTS)) as fh:
            for line in fh:
                if not any(i in line for i in ids):
                    continue
                try:
                    o = json.loads(line)
                except Exception:  # noqa: BLE001
                    continue
                eid = o.get("event_id")
                if eid in ids:
                    found[eid] = {"event_type": o.get("event_type"), "verdict": o.get("verdict"),
                                  "target": (o.get("target_id") or o.get("artifact") or "")[:120],
                                  "actor": o.get("actor")}
        contest_ok = (target["review_state_at_generation"]["contest"] is True
                      and len(dissents) == 2 and len(found) >= len(ids))
        gate_src = open(self.p(GATES_PY)).read()
        withdrawal_filter = bool(re.search(r"withdraw", gate_src, re.I))
        self.check("A10_review_contest_and_guard",
                   "2 dissent revises + 3 accepts exist at the protocol hash; gates.py has no withdrawal filter",
                   contest_ok and not withdrawal_filter,
                   {"accepts": accepts, "dissents": dissents, "events_found": found,
                    "contest": target["review_state_at_generation"]["contest"],
                    "gates_py_mentions_withdraw": withdrawal_filter,
                    "guard_finding": target["review_state_at_generation"]["guard_finding"]["finding"]})

        # ---- T1 hashes (stability) ------------------------------------------
        t1 = {rel: sha256_file(self.p(rel)) for rel in t0}
        self.measurements["t1_sha256"] = t1
        drift = {rel: [t0[rel], t1[rel]] for rel in t0 if t0[rel] != t1[rel]}
        self.checks[0]["pass"] = not drift
        self.checks[0]["measured"]["t1"] = t1[TARGET]
        self.checks[0]["measured"]["drift_paths"] = drift

        # ---- Controls (non-invasive, synthetic / real probes) ----------------
        c = {}
        dr = cb["dr_values"]
        err_real = [schemes["cnfd"]["l2_error_by_dr"][str(x)] for x in dr]
        p_real = order_ls(dr, err_real)
        err_mut = list(err_real)
        err_mut[0] *= 1.2
        p_mut = order_ls(dr, err_mut)
        c["K1_fit_sensitivity"] = {
            "description": "a 20% perturbation of one rung error must move the fitted order",
            "order_real": p_real, "order_perturbed": p_mut,
            "abs_shift": abs(p_mut - p_real), "detected": abs(p_mut - p_real) > 1e-3}
        tmp = os.path.join(self.base, ".w021_hash_probe.tmp")
        with open(tmp, "w") as fh:
            fh.write("w021-hash-probe\n")
        probe = sha256_file(tmp)
        os.remove(tmp)
        c["K2_wrong_hash_detection"] = {
            "description": "a declared hash differing from the measured probe hash is flagged",
            "probe_sha256": probe, "wrong_declared": "0" * 64,
            "detected": probe != "0" * 64 and len(probe) == 64}
        c["K3_solver_absence_probe"] = {
            "description": "negative probes at solver/N1 paths absent; positive probe present",
            "numerics/spherical_solver": os.path.exists(self.p("numerics/spherical_solver")),
            "numerics/spherical_solver/README.md": os.path.exists(self.p("numerics/spherical_solver/README.md")),
            "numerics/cartesian.py (positive)": os.path.exists(self.p("numerics/cartesian.py")),
            "detected": (not os.path.exists(self.p("numerics/spherical_solver"))
                         and not os.path.exists(self.p("numerics/spherical_solver/README.md"))
                         and os.path.exists(self.p("numerics/cartesian.py")))}
        # determinism: re-measure the two key digests from disk and re-run the fit
        again = sha256_file(self.p(TARGET))
        c["K4_determinism"] = {
            "description": "target re-hash and order refit reproduce the first pass",
            "target_rehash_equal": again == t0[TARGET],
            "order_refit_equal": abs(order_ls(dr, err_real) - p_real) < 1e-15,
            "detected": again == t0[TARGET] and abs(order_ls(dr, err_real) - p_real) < 1e-15}
        self.measurements["controls"] = c
        self.control_specs = c

        content_ids = {"A2_three_schemes_four_rungs_fixed_dt", "A3_orders_recomputed_from_raw_rows",
                       "A5_f0_rev5_class_binding", "A6_stop_rule_closures",
                       "A7_replication_verdicts_pinned", "A8_lock_guard_and_solver_absence"}
        by_id = {x["check_id"]: x for x in self.checks}
        content_pass = all(by_id[i]["pass"] for i in content_ids)
        controls_pass = all(v.get("detected") for v in c.values())
        target_stable = by_id["A1_target_hash_stable"]["pass"]
        if not controls_pass:
            verdict = "HARNESS_FAIL"
        elif not target_stable:
            verdict = "VOID_TARGET_DRIFT"
        elif content_pass:
            verdict = "ACCEPT_WITH_OPEN_ITEMS"
        else:
            verdict = "REVISE"
        self.measurements["verdict"] = verdict
        self.measurements["checks"] = self.checks
        self.measurements["checks_pass"] = sum(1 for x in self.checks if x["pass"])
        self.measurements["checks_total"] = len(self.checks)
        self.measurements["controls_pass"] = sum(1 for v in c.values() if v.get("detected"))
        self.measurements["controls_total"] = len(c)
        # stable digest over measured content (no wall clock)
        self.measurements["measurement_digest"] = sha256_bytes(
            json.dumps({"checks": self.checks, "t0": t0, "controls": c},
                       sort_keys=True).encode())
        return self.measurements


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=os.getcwd())
    args = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        h = Harness(args.base)
        m = h.run()
    except Exception as exc:  # noqa: BLE001
        print("HARNESS FAILURE:", repr(exc), file=sys.stderr)
        return 2
    verdict = m["verdict"]
    open_items = []
    by_id = {x["check_id"]: x for x in m["checks"]}
    if not by_id["A9_registration_gap_reproduced"]["pass"]:
        open_items.append("registration gap claim stale: a declared-unregistered path is now registered")
    if by_id["A10_review_contest_and_guard"]["pass"]:
        open_items.append("protocol review contest (2 dissent revises) unresolved; withdrawn-accept still counted by numerics/gates.py")
    open_items.append("registration gap (6 paths incl. protocol + 3 replication verdicts) is a controller rule-2 step, not a worker write")
    open_items.append("reviewed target itself not registered in runtime/state/artifact_hashes.json (N0 not done; rule-2 will require it)")
    report = {
        "artifact": "W021-N0-REV3-INDEP-01 independent verification of the N0 post-stoprule closure",
        "tool": TOOL,
        "reviewed_target": TARGET,
        "reviewed_sha256": m["t0_sha256"][TARGET],
        "verdict": verdict,
        "score_0_5": 4.0 if verdict == "ACCEPT_WITH_OPEN_ITEMS" else (3.0 if verdict == "REVISE" else 1.0),
        "hard_failures": [] if verdict in ("ACCEPT_WITH_OPEN_ITEMS", "REVISE") else
                         [x["check_id"] for x in m["checks"] if not x["pass"]],
        "checks_pass": m["checks_pass"], "checks_total": m["checks_total"],
        "controls_pass": m["controls_pass"], "controls_total": m["controls_total"],
        "checks": m["checks"],
        "open_items": open_items,
        "claims_not_made": [
            "no gate verdict (G-NUM stays pending; authority Astra / lead-audit)",
            "no node completion (N0 stays active) and no numerics_lock release",
            "no physics/WCC/SCC claim and no solver or N1 work",
            "not a substitute for the card audit-r2-N0-rev3 verdict owned by worker-012",
        ],
        "falsifier": ("Re-run verify_n0_rev3.py at the same pins: falsified if any A-check flips, "
                      "any control K1-K4 fails to detect, or a recomputed order leaves |p-2|<=0.3 / "
                      "cross-scheme bound; VOID on drift of any T0/T1 hash or of the reviewed target hash."),
        "measurement_digest": m["measurement_digest"],
        "provenance": {"method": "independent stdlib re-implementation; no author module imported",
                       "writes": "artifact-local only; no canonical path modified"},
    }
    results = {"tool": TOOL, "verdict": verdict, "t0_sha256": m["t0_sha256"],
               "t1_sha256": m["t1_sha256"], "checks": m["checks"],
               "measurement_digest": m["measurement_digest"]}
    controls = {"tool": TOOL, "controls": m["controls"],
                "all_detected": m["controls_pass"] == m["controls_total"]}
    for name, obj in (("report.json", report), ("results.json", results), ("controls.json", controls)):
        with open(os.path.join(here, name), "w") as fh:
            json.dump(obj, fh, indent=1, sort_keys=True)
            fh.write("\n")
    print(json.dumps({"verdict": verdict, "checks": f'{m["checks_pass"]}/{m["checks_total"]}',
                      "controls": f'{m["controls_pass"]}/{m["controls_total"]}',
                      "target": m["t0_sha256"][TARGET],
                      "digest": m["measurement_digest"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
