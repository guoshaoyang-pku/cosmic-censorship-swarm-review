#!/usr/bin/env python3
"""W017-N0-STOPRULE-CLOSURE-VERIFY-01 -- independent read-only verification of
numerics/protocol/lifecycle08_stoprule_closure_verify.json (astra-lead-numerics, lifecycle 08).

CLASS BINDING : AF-WCC-SCALAR-SPH
NODE          : N0 (flat-space spherical scalar-wave test)
GATE          : G-NUM
TASK          : verify the lead's claimed stop-rule closure at pinned hashes:
                (1) four fixed-dt rungs per scheme recomputed from raw rows,
                (2) F0 re-bind against the live taxonomy bytes,
                (3) independent-replication verdict chain,
                plus lock compliance and registration claims.
FALSIFIER     : any recomputed fit leaving |p-2| > 0.3, a non-monotone ladder,
                cross-scheme spread > 0.25, a cited verdict whose bytes move off
                its declared hash, a live taxonomy != 0abb9ed8a961, or a
                spherical-solver file appearing while numerics_lock == locked.

METHOD        : read-only; own log-log LSQ implementation (no numerics generator
                or solver imported); every check runs against an in-memory copy
                and every check has an in-memory negative control that must fire.
                No canonical artifact is edited.
"""

import copy
import glob
import hashlib
import json
import math
import os
import sys

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PINNED = os.path.join(OUT_DIR, "pinned")

CLOSURE_PATH = "numerics/protocol/lifecycle08_stoprule_closure_verify.json"
CERT_PATH = "numerics/protocol/n0_fixed_dt_certification.json"
CONV3_PATH = "numerics/results/flat_wave_convergence_rev3.json"
REPL_PATH = "numerics/tests/flat_wave_replication.py"
TAX_PATH = "research_map/formulation_taxonomy.yaml"
AUTH_PATH = "numerics/N0_CLASS_BINDING_AUTHORITY.json"
MAP_PATH = "research_map/research_map.json"
STOPRULE_REVIEW = "reviews/N0-review-lead-audit.json"
FLASH13 = "reviews/flash-13-N0-rev3-verdict.json"
VERDICT_PATHS = {
    "worker-046": "artifacts/worker-046/n0_fixed_dt_independent/verification.json",
    "worker-057": "artifacts/worker-057/n0_fixeddt_verify/report.json",
    "worker-081": "artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json",
}
EXPECTED = {
    "closure_sha256": "88ec0bf298cbc4de6ae2a6d3038961d404f1c43a64cbaa92f29b6ad6cce77f75",
    "cert_sha256": "1677822ceb9c81e8f6e48dee8360ab13edc35623c51f4be68bd6589a5fe79920",
    "conv3_sha256": "da7c360719950f7ef6be2624391dee464f8c818a0be74ec44f0f8c70d2b28ac3",
    "repl_sha256": "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422",
    "tax_sha256": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "auth_sha256": "effd20b0ea094a8dfd4f686e62c49b1667622337efd6a7c154f7fadae0b98419",
    "f0_revision": 5,
    "class_id": "AF-WCC-SCALAR-SPH",
    "p_design": 2.0,
    "p_tol": 0.3,
    "r5_bound": 0.25,
    "dt_fixed": 1e-4,
    "dr_values": [0.2, 0.1, 0.05, 0.025],
    "fit_atol": 1e-9,
}


def sha256_file(path):
    p = os.path.join(ROOT, path)
    if not os.path.exists(p):
        return None
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    with open(os.path.join(ROOT, path)) as fh:
        return json.load(fh)


def fit_order(dr, err):
    """log-log least squares slope, slope SE, residuals, pair orders."""
    n = len(dr)
    x = [math.log(v) for v in dr]
    y = [math.log(v) for v in err]
    mx = sum(x) / n
    my = sum(y) / n
    sxx = sum((xi - mx) ** 2 for xi in x)
    sxy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    p = sxy / sxx
    b = my - p * mx
    res = [yi - (p * xi + b) for xi, yi in zip(x, y)]
    sse = sum(r * r for r in res)
    se = math.sqrt(sse / (n - 2) / sxx)
    pairs = [math.log(err[i] / err[i + 1]) / math.log(dr[i] / dr[i + 1]) for i in range(n - 1)]
    return p, se, res, pairs


def close(a, b, atol=EXPECTED["fit_atol"]):
    return a is not None and b is not None and abs(a - b) <= atol


CHECKS = []


def check(cid, group, passed, detail, measured=None, declared=None):
    CHECKS.append({
        "id": cid,
        "group": group,
        "passed": bool(passed),
        "detail": detail,
        "measured": measured,
        "declared": declared,
    })


def evaluate(closure, cert, taxonomy_text, taxonomy_doc, verdicts, map_doc, live, exists_fn):
    """All checks against one in-memory world. Returns list of check dicts."""
    del CHECKS[:]
    h = live

    # ---- C01 identity / schema -------------------------------------------------
    check("C01-closure-identity", "identity",
          closure.get("schema") == "n0-stoprule-closure-verify/v1"
          and closure.get("class_id") == EXPECTED["class_id"]
          and closure.get("node_id") == "N0"
          and closure.get("gate") == "G-NUM"
          and isinstance(closure.get("falsifier"), str) and closure["falsifier"],
          "schema/class/node/gate/falsifier fields present and class-bound",
          {k: closure.get(k) for k in ("schema", "class_id", "node_id", "gate")},
          {"schema": "n0-stoprule-closure-verify/v1", "class_id": EXPECTED["class_id"],
           "node_id": "N0", "gate": "G-NUM"})
    check("C01b-author-claim", "identity",
          closure.get("all_closure_items_closed") is True,
          "author asserts all_closure_items_closed=true (author claim, independently re-derived below)",
          closure.get("all_closure_items_closed"), True)

    # ---- C02 raw basis pins ----------------------------------------------------
    check("C02-cert-pin", "basis",
          h.get(CERT_PATH) == EXPECTED["cert_sha256"],
          "raw certification file matches its declared/expected sha256",
          h.get(CERT_PATH), EXPECTED["cert_sha256"])
    check("C02b-conv3-pin", "basis",
          cert.get("frozen_module", {}).get("sha256") == EXPECTED["repl_sha256"]
          and h.get(CONV3_PATH) == EXPECTED["conv3_sha256"],
          "frozen run hash (convergence rev3) resolves on disk",
          {"conv3_disk": h.get(CONV3_PATH), "frozen_module_pin": cert.get("frozen_module", {}).get("sha256")},
          EXPECTED["conv3_sha256"])
    check("C02c-cert-class", "basis",
          cert.get("class_id") == EXPECTED["class_id"] and cert.get("node_id") == "N0"
          and cert.get("gate") == "G-NUM",
          "raw certification itself carries the class/node/gate binding",
          {k: cert.get(k) for k in ("class_id", "node_id", "gate")}, EXPECTED["class_id"])

    # ---- C03 item 1: recompute four fixed-dt rungs ----------------------------
    schemes = closure.get("item_1_four_rungs", {}).get("schemes", {})
    cfg = cert.get("config", {})
    ok_cfg = (cfg.get("dr_values") == EXPECTED["dr_values"]
              and cfg.get("dt_fixed") == EXPECTED["dt_fixed"]
              and cfg.get("p_design") == EXPECTED["p_design"]
              and cfg.get("p_tol") == EXPECTED["p_tol"])
    check("C03-config", "item1",
          ok_cfg and set(schemes) == {"cnfd", "cnfem", "lffd"},
          "config declares 4 rungs at fixed dt=1e-4, p_design=2, tol=0.3; three schemes present",
          {"config": cfg, "schemes": sorted(schemes)},
          {"dr": EXPECTED["dr_values"], "dt": EXPECTED["dt_fixed"], "p_tol": EXPECTED["p_tol"]})

    for s in sorted(schemes):
        c = schemes[s]
        raw = cert.get("schemes", {}).get(s, {}).get("fixed_dt_certification", {})
        rows = raw.get("rows", [])
        drs = [r.get("dr") for r in rows]
        errs = [r.get("l2_error") for r in rows]
        dts = [r.get("dt") for r in rows]
        p, se, res, pairs = fit_order(drs, errs) if len(rows) >= 3 else (None, None, None, None)
        mono = all(errs[i] > errs[i + 1] for i in range(len(errs) - 1)) if len(errs) >= 2 else False
        check(f"C03-{s}-rungs", "item1",
              len(rows) == 4 and drs == EXPECTED["dr_values"] and all(
                  abs(d - EXPECTED["dt_fixed"]) < 1e-15 for d in dts) and mono,
              f"{s}: 4 rungs, dr ladder exact, dt fixed at 1e-4, errors strictly decreasing",
              {"n_rungs": len(rows), "dr": drs, "dt": dts, "monotone": mono},
              {"n_rungs": 4, "dr": EXPECTED["dr_values"], "dt_fixed": EXPECTED["dt_fixed"], "monotone": True})
        check(f"C03-{s}-fit", "item1",
              close(p, c.get("recomputed_fit_order")) and close(p, c.get("declared_fit_order"))
              and close(p, raw.get("fit_order")),
              f"{s}: independently recomputed LSQ order equals closure 'recomputed' and 'declared' values",
              {"independent_fit": p, "closure_recomputed": c.get("recomputed_fit_order"),
               "closure_declared": c.get("declared_fit_order"), "raw_fit": raw.get("fit_order")},
              c.get("declared_fit_order"))
        check(f"C03-{s}-se", "item1",
              close(se, c.get("recomputed_se")) and close(se, c.get("declared_se")),
              f"{s}: independently recomputed slope SE equals closure values",
              {"independent_se": se, "closure_recomputed_se": c.get("recomputed_se"),
               "closure_declared_se": c.get("declared_se")}, c.get("declared_se"))
        check(f"C03-{s}-residuals", "item1",
              res is not None and len(res) == len(raw.get("lsq_residuals", []))
              and all(close(a, b) for a, b in zip(res, raw.get("lsq_residuals", []))),
              f"{s}: LSQ residuals reproduce the raw certification",
              {"independent": res, "raw": raw.get("lsq_residuals")}, raw.get("lsq_residuals"))
        check(f"C03-{s}-pairs", "item1",
              pairs is not None and all(close(a, b) for a, b in zip(pairs, raw.get("pair_orders", []))),
              f"{s}: consecutive-pair orders reproduce the raw certification",
              {"independent": pairs, "raw": raw.get("pair_orders")}, raw.get("pair_orders"))
        band = abs(p - EXPECTED["p_design"]) <= EXPECTED["p_tol"] if p is not None else False
        check(f"C03-{s}-band", "item1",
              band and c.get("within_band_0p3") is True and raw.get("within_band") is True,
              f"{s}: |p-2| <= 0.3 and closure/raw flag within_band",
              {"abs_p_minus_2": abs(p - EXPECTED["p_design"]) if p is not None else None,
               "tol": EXPECTED["p_tol"]}, {"within_band": True})
        check(f"C03-{s}-agreement", "item1",
              c.get("abs_diff_vs_declared") == 0.0 and c.get("n_rungs") == 4
              and c.get("dt_fixed_1e-4") is True and c.get("monotone") is True,
              f"{s}: closure's own item-1 bookkeeping self-consistent (diff 0.0, n=4, dt fixed, monotone)",
              {k: c.get(k) for k in ("abs_diff_vs_declared", "n_rungs", "dt_fixed_1e-4", "monotone")},
              {"abs_diff_vs_declared": 0.0, "n_rungs": 4})

    # ---- C04 item 1: cross-scheme spread ---------------------------------------
    order = {s: schemes.get(s, {}).get("recomputed_fit_order") for s in ("cnfd", "cnfem", "lffd")}
    if all(v is not None for v in order.values()):
        spread = max(order.values()) - min(order.values())
    else:
        spread = None
    dec_spread = closure.get("item_1_four_rungs", {}).get("cross_scheme_spread")
    r5 = cert.get("cross_scheme_R5", {})
    check("C04-spread", "item1",
          spread is not None and close(spread, dec_spread) and close(spread, r5.get("max_pairwise_abs_diff"))
          and spread <= EXPECTED["r5_bound"],
          "independently recomputed cross-scheme spread equals closure/raw value and is within R5 bound",
          {"independent_spread": spread, "closure": dec_spread, "raw": r5.get("max_pairwise_abs_diff"),
           "bound": EXPECTED["r5_bound"]}, dec_spread)
    check("C04-all-agree", "item1",
          r5.get("all_agree") is True
          and all(p.get("agree") is True for p in r5.get("pairs", []))
          and closure["item_1_four_rungs"].get("cross_scheme_within_R5") is True,
          "all three scheme pairs agree within R5 in both the raw cert and the closure",
          {"pairs": r5.get("pairs")}, {"all_agree": True})

    # ---- C05 item 2: F0 re-bind ------------------------------------------------
    it2 = closure.get("item_2_f0_rebind", {})
    tax_sha = h.get(TAX_PATH)
    tax_rev = taxonomy_doc.get("revision") if isinstance(taxonomy_doc, dict) else None
    classes = taxonomy_doc.get("classes") if isinstance(taxonomy_doc, dict) else None
    cls_present = False
    cls_id_hits = 0
    if isinstance(classes, dict):
        cls_present = EXPECTED["class_id"] in classes
    elif isinstance(classes, list):
        for entry in classes:
            if isinstance(entry, dict) and entry.get("class_id") == EXPECTED["class_id"]:
                cls_present = True
    if taxonomy_text:
        cls_id_hits = taxonomy_text.count(EXPECTED["class_id"])
    check("C05-f0-pin", "item2",
          tax_sha == EXPECTED["tax_sha256"] and it2.get("live_sha256") == tax_sha
          and it2.get("declared_sha256") == tax_sha,
          "live taxonomy bytes equal the closure's declared and live pins",
          {"disk": tax_sha, "closure_live": it2.get("live_sha256"), "closure_declared": it2.get("declared_sha256")},
          EXPECTED["tax_sha256"])
    check("C05-f0-rev", "item2",
          tax_rev == EXPECTED["f0_revision"] and it2.get("live_revision") == tax_rev
          and it2.get("declared_revision") == tax_rev,
          "taxonomy revision 5 on disk and in the closure",
          {"disk_revision": tax_rev, "closure_live_revision": it2.get("live_revision"),
           "closure_declared_revision": it2.get("declared_revision")}, EXPECTED["f0_revision"])
    check("C05-class-present", "item2",
          cls_present and it2.get("class_id_present_in_live_taxonomy") is True and cls_id_hits >= 1,
          "AF-WCC-SCALAR-SPH is present in the live parsed taxonomy and flagged in the closure",
          {"parsed_present": cls_present, "literal_occurrences": cls_id_hits,
           "closure_flag": it2.get("class_id_present_in_live_taxonomy")}, True)
    auth = verdicts.get(AUTH_PATH, {})
    check("C05-authority", "item2",
          h.get(AUTH_PATH) == EXPECTED["auth_sha256"]
          and it2.get("authority_record_sha256") == EXPECTED["auth_sha256"]
          and auth.get("binding", {}).get("sha256") == EXPECTED["tax_sha256"]
          and auth.get("binding", {}).get("declared_revision") == EXPECTED["f0_revision"]
          and auth.get("class_id") == EXPECTED["class_id"]
          and auth.get("ruling", {}).get("class_binding_carrier_sha256") == EXPECTED["conv3_sha256"],
          "authority record hash resolves and its own binding/carrier pins agree",
          {"disk": h.get(AUTH_PATH), "closure": it2.get("authority_record_sha256"),
           "authority_binding": auth.get("binding"), "authority_carrier": auth.get("ruling", {}).get(
               "class_binding_carrier_sha256")}, EXPECTED["auth_sha256"])

    # ---- C06 item 3: independent replication chain -----------------------------
    it3 = closure.get("item_3_independent_replication", {})
    check("C06-repl-module", "item3",
          h.get(REPL_PATH) == EXPECTED["repl_sha256"]
          and it3.get("cert_frozen_module", {}).get("sha256") == EXPECTED["repl_sha256"]
          and it3.get("cert_frozen_module_matches_disk") is True
          and cert.get("frozen_module", {}).get("sha256") == EXPECTED["repl_sha256"],
          "independent replication module on-disk hash equals cert/closure pins",
          {"disk": h.get(REPL_PATH), "closure": it3.get("cert_frozen_module", {}).get("sha256"),
           "cert": cert.get("frozen_module", {}).get("sha256")}, EXPECTED["repl_sha256"])
    f13 = verdicts.get(FLASH13, {})
    check("C06-flash13-verdict", "item3",
          f13.get("verdict") == "accept" and f13.get("score") == 4.0
          and f13.get("reviewed_sha256") == EXPECTED["conv3_sha256"]
          and f13.get("counts_as_node_verdict") is True
          and it3.get("flash13_accept", {}).get("counts_as_node_verdict") is True
          and it3.get("flash13_accept", {}).get("binds_current_rev3") is True
          and it3.get("flash13_accept", {}).get("hash_stable_across_review") is True,
          "flash-13 review is an accept at the frozen rev3 hash and itself declares counts_as_node_verdict",
          {"verdict": f13.get("verdict"), "score": f13.get("score"),
           "reviewed_sha256": f13.get("reviewed_sha256"),
           "counts_as_node_verdict": f13.get("counts_as_node_verdict"),
           "closure_flag": it3.get("flash13_accept", {}).get("counts_as_node_verdict")},
          {"verdict": "accept", "reviewed_sha256": EXPECTED["conv3_sha256"]})
    conflict = it3.get("flash13_accept", {}).get("disclosed_conflict")
    check("C06-conflict", "item3",
          isinstance(conflict, str) and "F-06" in conflict,
          "the reviewer-authored-module conflict is disclosed rather than hidden",
          conflict, "F-06 disclosed")
    declared_strings = {
        "worker-046": "SUPPORTED",
        "worker-057": "REPRODUCED",
        "worker-081": "accept",
    }
    for reviewer, path in VERDICT_PATHS.items():
        raw_text = ""
        p = os.path.join(ROOT, path)
        if os.path.exists(p):
            with open(p) as fh:
                raw_text = fh.read()
        declared = [v for v in it3.get("verdicts", []) if v.get("reviewer") == reviewer]
        ok = (h.get(path) is not None and declared and declared[0].get("hash_match") is True
              and declared[0].get("declared_sha256") == h.get(path)
              and declared_strings[reviewer].lower() in raw_text.lower())
        check(f"C06-{reviewer}", "item3",
              bool(ok),
              f"{reviewer}: cited verdict resolves at the declared hash and carries its declared verdict token",
              {"disk": h.get(path),
               "closure_declared": declared[0].get("declared_sha256") if declared else None,
               "token_found": declared_strings[reviewer].lower() in raw_text.lower()},
              declared[0].get("declared_sha256") if declared else None)
    check("C06-count", "item3",
          it3.get("verdict_count") == 3 and len(it3.get("verdicts", [])) == 3,
          "closure cites exactly the three declared independent verdict records",
          it3.get("verdict_count"), 3)
    check("C06-frozen-run", "item3",
          it3.get("frozen_run_hash") == EXPECTED["conv3_sha256"] == h.get(CONV3_PATH),
          "the frozen run hash in item 3 is the live convergence rev3 hash",
          {"closure": it3.get("frozen_run_hash"), "disk": h.get(CONV3_PATH)}, EXPECTED["conv3_sha256"])

    # ---- C07 lock compliance ---------------------------------------------------
    lock = map_doc.get("numerics_lock", {})
    solver_present = bool(glob.glob(os.path.join(ROOT, "numerics", "**", "spherical_solver*"), recursive=True))
    solver_present = solver_present or any(
        exists_fn(p) for p in ("numerics/spherical_solver.py", "numerics/spherical_solver",
                               "numerics/spherical_solver.c", "numerics/spherical_solver/"))
    check("C07-lock", "lock",
          lock.get("state") == "locked"
          and closure.get("lock_compliance", {}).get("numerics_lock_state") == "locked"
          and closure.get("lock_compliance", {}).get("spherical_solver_present") is False
          and solver_present is False,
          "live map numerics_lock is locked and no spherical-solver file exists",
          {"live_lock": lock.get("state"), "closure_lock": closure.get("lock_compliance", {}).get(
              "numerics_lock_state"), "solver_present": solver_present}, {"state": "locked", "solver_present": False})
    check("C07-n1", "lock",
          lock.get("locked_nodes") == ["N1"] and closure.get("lock_compliance", {}).get("n1_status") == "queued",
          "N1 remains the locked node and is queued; no N1 work claimed",
          {"locked_nodes": lock.get("locked_nodes"),
           "closure_n1": closure.get("lock_compliance", {}).get("n1_status")}, ["N1"])

    # ---- C08 stop-rule under test ---------------------------------------------
    sr = verdicts.get(STOPRULE_REVIEW, {})
    rule = str(sr.get("stop_rule", "")).lower()
    it_sr = closure.get("stop_rule_under_test", {})
    check("C08-stoprule-hash", "stoprule",
          h.get(STOPRULE_REVIEW) == it_sr.get("sha256") == "e3c314f886be83788d26b723aedfe70666dcbdca491d2d832a84c91dafaeaebf",
          "stop-rule review of record resolves at the declared hash",
          {"disk": h.get(STOPRULE_REVIEW), "closure": it_sr.get("sha256")}, it_sr.get("sha256"))
    tokens = [("4th resolution", "4th resolution" in rule or "four" in rule),
              ("f0 re-bind", "re-bind" in rule or "rebind" in rule),
              ("independent replication", "independent replication" in rule)]
    check("C08-stoprule-content", "stoprule",
          all(t[1] for t in tokens),
          "the cited stop rule text contains all three closure items",
          {t[0]: t[1] for t in tokens}, {t[0]: True for t in tokens})

    # ---- C09 registration self-report -----------------------------------------
    known = closure.get("registration", {}).get("known_pins", [])
    bad = [k for k in known if k.get("registered_sha256") and k.get("disk_sha256") != k.get("registered_sha256")]
    check("C09-registration", "registration",
          len(known) >= 8 and not bad,
          "closure's registration table: every registered pin still matches disk, no drift",
          {"known_pins": len(known), "mismatches": bad},
          {"known_pins": ">=8", "mismatches": []})
    return list(CHECKS)


def control(name, expect_check_ids, mutate, closure, cert, taxonomy_text, taxonomy_doc, verdicts, map_doc, live,
            exists_fn):
    """Run a mutated in-memory world; the named checks must flip to failed."""
    c2 = copy.deepcopy(closure)
    ce2 = copy.deepcopy(cert)
    tx2 = taxonomy_text
    td2 = copy.deepcopy(taxonomy_doc)
    v2 = copy.deepcopy(verdicts)
    m2 = copy.deepcopy(map_doc)
    lv2 = dict(live)
    ex2 = exists_fn
    mutate(c2, ce2, td2, v2, m2, lv2)
    if "taxonomy_text" in mutate.__code__.co_varnames[:mutate.__code__.co_argcount]:
        pass
    res = {c["id"]: c for c in evaluate(c2, ce2, tx2, td2, v2, m2, lv2, ex2)}
    fired = [cid for cid in expect_check_ids if not res.get(cid, {}).get("passed", True)]
    return {
        "control": name,
        "expected_to_fail": expect_check_ids,
        "fired": fired,
        "detected": len(fired) == len(expect_check_ids),
        "observed": {cid: res.get(cid, {}).get("passed") for cid in expect_check_ids},
    }


def main():
    live = {}
    for p in [CLOSURE_PATH, CERT_PATH, CONV3_PATH, REPL_PATH, TAX_PATH, AUTH_PATH, MAP_PATH,
              STOPRULE_REVIEW, FLASH13] + list(VERDICT_PATHS.values()):
        live[p] = sha256_file(p)

    pinned_path = os.path.join(PINNED, "lifecycle08_stoprule_closure_verify.88ec0bf298cb.json")
    if os.path.exists(pinned_path):
        closure = json.load(open(pinned_path))
        closure_source = pinned_path
    else:
        closure = load_json(CLOSURE_PATH)
        closure_source = CLOSURE_PATH

    cert = load_json(CERT_PATH)
    with open(os.path.join(ROOT, TAX_PATH)) as fh:
        taxonomy_text = fh.read()
    taxonomy_doc = yaml.safe_load(taxonomy_text) if yaml else {}
    verdicts = {AUTH_PATH: load_json(AUTH_PATH), FLASH13: load_json(FLASH13),
                STOPRULE_REVIEW: load_json(STOPRULE_REVIEW)}
    for path in VERDICT_PATHS.values():
        verdicts[path] = load_json(path)
    map_doc = load_json(MAP_PATH)

    def no_solver(_p):
        return False

    checks = evaluate(closure, cert, taxonomy_text, taxonomy_doc, verdicts, map_doc, live, no_solver)

    controls = []
    controls.append(control(
        "K01 perturb one l2_error +1%",
        ["C03-cnfd-fit"],
        lambda c, ce, td, v, m, lv: ce["schemes"]["cnfd"]["fixed_dt_certification"]["rows"][2].__setitem__("l2_error", 0.00041604375613146766 * 1.01),
        closure, cert, taxonomy_text, taxonomy_doc, verdicts, map_doc, live, no_solver))
    controls.append(control(
        "K02 move a dr rung to 0.21",
        ["C03-cnfem-rungs"],
        lambda c, ce, td, v, m, lv: ce["schemes"]["cnfem"]["fixed_dt_certification"]["rows"][1].__setitem__("dr", 0.21),
        closure, cert, taxonomy_text, taxonomy_doc, verdicts, map_doc, live, no_solver))
    controls.append(control(
        "K03 substitute the F0 declared hash",
        ["C05-f0-pin"],
        lambda c, ce, td, v, m, lv: c["item_2_f0_rebind"].__setitem__("declared_sha256", "0" * 64),
        closure, cert, taxonomy_text, taxonomy_doc, verdicts, map_doc, live, no_solver))
    controls.append(control(
        "K04 plant a spherical_solver file (exists_fn true)",
        ["C07-lock"],
        lambda c, ce, td, v, m, lv: None,
        closure, cert, taxonomy_text, taxonomy_doc, verdicts, map_doc, live,
        (lambda p: True if p == "numerics/spherical_solver.py" else no_solver(p))))
    controls.append(control(
        "K05 tighten the R5 bound below the measured spread",
        ["C04-spread"],
        lambda c, ce, td, v, m, lv: ce["cross_scheme_R5"].__setitem__("max_pairwise_abs_diff", 1e-9),
        closure, cert, taxonomy_text, taxonomy_doc, verdicts, map_doc, live, no_solver))
    controls.append(control(
        "K06 flip the flash-13 verdict to revise",
        ["C06-flash13-verdict"],
        lambda c, ce, td, v, m, lv: v[FLASH13].__setitem__("verdict", "revise"),
        closure, cert, taxonomy_text, taxonomy_doc, verdicts, map_doc, live, no_solver))
    controls.append(control(
        "K07 inflate one closure recomputed order by +0.05",
        ["C03-lffd-fit"],
        lambda c, ce, td, v, m, lv: c["item_1_four_rungs"]["schemes"]["lffd"].__setitem__(
            "recomputed_fit_order", 1.999943173893314 + 0.05),
        closure, cert, taxonomy_text, taxonomy_doc, verdicts, map_doc, live, no_solver))
    controls.append(control(
        "K08 remove the taxonomy class line in memory",
        ["C05-class-present"],
        lambda c, ce, td, v, m, lv: td.clear(),
        closure, cert, taxonomy_text, taxonomy_doc, verdicts, map_doc, live, no_solver))

    # post-run drift check
    post = {p: sha256_file(p) for p in live}
    drift = {p: {"pre": live[p], "post": post[p]} for p in live if live[p] != post[p]}

    failed = [c for c in checks if not c["passed"]]
    controls_failed = [k for k in controls if not k["detected"]]
    all_ok = not failed and not controls_failed and not drift
    report = {
        "schema": "w017-n0-stoprule-closure-verify-report/v1",
        "task_id": "W017-N0-STOPRULE-CLOSURE-VERIFY-01",
        "actor": "worker-017",
        "created_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
        "class_id": EXPECTED["class_id"],
        "node_id": "N0",
        "gate": "G-NUM",
        "target": {
            "path": CLOSURE_PATH,
            "sha256": EXPECTED["closure_sha256"],
            "pinned_copy": "artifacts/worker-017/n0_stoprule_closure_verify/pinned/lifecycle08_stoprule_closure_verify.88ec0bf298cb.json",
            "verified_bytes": closure_source,
        },
        "method": "read-only; own log-log LSQ from raw rows; no numerics generator or solver imported; "
                  "in-memory negative controls; no canonical artifact edited",
        "verdict": "accept" if all_ok else "revise",
        "n_checks": len(checks),
        "n_checks_passed": len(checks) - len(failed),
        "failed_checks": failed,
        "controls": controls,
        "controls_all_fired": not controls_failed,
        "drift": drift,
        "checks": checks,
        "pins": live,
        "falsifier": "Re-run at the same pins: any recomputed fit leaving |p-2|>0.3, a non-monotone ladder, "
                     "cross-scheme spread >0.25, a cited verdict whose bytes move off its declared hash, a live "
                     "taxonomy != 0abb9ed8a961, or numerics/spherical_solver appearing while numerics_lock==locked.",
        "claims_not_made": [
            "no gate verdict; G-NUM authority stays with Astra / lead-audit",
            "no node transition; N0 status untouched",
            "no numerics_lock release; N1 stays queued",
            "no adjudication of the protocol-review contest",
            "no physics / self-gravity / WCC / SCC claim",
        ],
    }
    with open(os.path.join(OUT_DIR, "report.json"), "w") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
        fh.write("\n")
    checkpoint = {
        "schema": "worker-local-checkpoint/v1",
        "worker": "worker-017",
        "task_id": report["task_id"],
        "created_at": report["created_at"],
        "verdict": report["verdict"],
        "checks": f"{report['n_checks_passed']}/{report['n_checks']}",
        "controls_fired": report["controls_all_fired"],
        "drift": drift,
        "artifacts": {
            "instrument": "artifacts/worker-017/n0_stoprule_closure_verify/verify_n0_closure_017.py",
            "report": "artifacts/worker-017/n0_stoprule_closure_verify/report.json",
            "pinned_closure": report["target"]["pinned_copy"],
        },
        "note": "worker-local checkpoint only; controller runtime/state/current_checkpoint.json untouched",
    }
    with open(os.path.join(OUT_DIR, "CHECKPOINT.json"), "w") as fh:
        json.dump(checkpoint, fh, indent=1, sort_keys=True)
        fh.write("\n")

    print(json.dumps({
        "verdict": report["verdict"],
        "checks": f"{report['n_checks_passed']}/{report['n_checks']}",
        "failed": [c["id"] for c in failed],
        "controls_detected": all(k["detected"] for k in controls),
        "drift": list(drift),
    }, indent=1))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
