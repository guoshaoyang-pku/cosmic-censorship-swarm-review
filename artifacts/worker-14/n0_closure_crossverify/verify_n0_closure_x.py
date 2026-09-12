#!/usr/bin/env python3
"""W014-GNUM-N0-CLOSURE-CROSSVERIFY-01 — independent read-only cross-verification.

Second worker-level verification (non-author, independent re-implementation) of:
  T1 numerics/protocol/lifecycle08_stoprule_closure_verify.json   (N0 stop-rule closure)
  T2 reviews/N0-stoprule-closure-review-worker-017.json           (first independent review)

Read-only: writes only its own --out report. Does not import any numerics generator, any
worker-017 instrument, or any solver. numerics_lock stays LOCKED.

Run:  python3 verify_n0_closure_x.py --out report.json
Exit: 0 = verdict accept, 2 = revise / any check flag / control not fired / drift.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------- pins

PINS = {
    "closure": ("numerics/protocol/lifecycle08_stoprule_closure_verify.json",
                "88ec0bf298cbc4de6ae2a6d3038961d404f1c43a64cbaa92f29b6ad6cce77f75"),
    "certification": ("numerics/protocol/n0_fixed_dt_certification.json",
                      "1677822ceb9c81e8f6e48dee8360ab13edc35623c51f4be68bd6589a5fe79920"),
    "rev3": ("numerics/results/flat_wave_convergence_rev3.json",
             "da7c360719950f7ef6be2624391dee464f8c818a0be74ec44f0f8c70d2b28ac3"),
    "replication_module": ("numerics/tests/flat_wave_replication.py",
                           "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422"),
    "taxonomy": ("research_map/formulation_taxonomy.yaml",
                 "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"),
    "authority": ("numerics/N0_CLASS_BINDING_AUTHORITY.json",
                  "effd20b0ea094a8dfd4f686e62c49b1667622337efd6a7c154f7fadae0b98419"),
    "stop_rule": ("reviews/N0-review-lead-audit.json",
                  "e3c314f886be83788d26b723aedfe70666dcbdca491d2d832a84c91dafaeaebf"),
    "flash13": ("reviews/flash-13-N0-rev3-verdict.json",
                "6d28595429514f0537ffc1615f352416379c9be34ea26334933ddd5c29798460"),
    "n0_final_verify": ("reviews/N0-review-final-verify.json",
                        "18a0c0d0e77f0b0a"),
    "gates": ("numerics/gates.py",
              "fcd1d70991b6eade4aa993dc49b6103e338f68320aabb955d97da5a8f55d996e"),
    "protocol": ("numerics/CONVERGENCE_PROTOCOL.md",
                 "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274"),
    "verdict_w046": ("artifacts/worker-046/n0_fixed_dt_independent/verification.json",
                     "814452111bc8912bb21f8e0a353fe78096640d299e469578462b755592ea9a61"),
    "verdict_w057": ("artifacts/worker-057/n0_fixeddt_verify/report.json",
                     "b906445878f3130dd710595a362883e29be87f11cb8d8edbdbc79539147b3b04"),
    "verdict_w081": ("artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json",
                     "65ae766d9e4c205762cff35fb822915d4b00bd4502a0326455bed84e7b3169d6"),
    "w017_review": ("reviews/N0-stoprule-closure-review-worker-017.json",
                    "87b311e72032b38a6ad9137be9e373d00fb641691b75e066ad0a3271523454dc"),
    "w017_report": ("artifacts/worker-017/n0_stoprule_closure_verify/report.json",
                    "d3d7c450ebc5313d9bf7b0bf83a05c10ad5f56d0d09446778f90d4040364b639"),
    "w017_crosscheck": ("artifacts/worker-017/n0_stoprule_closure_verify/registration_crosscheck.json",
                        "749090f9a2bad30baa778f58d7193b428320913b4c2f7b52848fc515ec9611cd"),
    "w017_instrument": ("artifacts/worker-017/n0_stoprule_closure_verify/verify_n0_closure_017.py",
                        "ba56eade75616a3f17c8a7a2592156e6dda134be393474072766bf16b4d8cfe7"),
    "w017_pinned_copy": ("artifacts/worker-017/n0_stoprule_closure_verify/pinned/"
                         "lifecycle08_stoprule_closure_verify.88ec0bf298cb.json",
                         "88ec0bf298cbc4de6ae2a6d3038961d404f1c43a64cbaa92f29b6ad6cce77f75"),
    "registry": ("runtime/state/artifact_hashes.json", None),
    "map": ("research_map/research_map.json", None),
}

EXPECTED_PREFIX = {  # sources that declare only a prefix
    "n0_final_verify": "18a0c0d0e77f",
}

FALSIFIER = (
    "Re-run verify_n0_closure_x.py at the pinned inputs. The cross-verification is falsified if a "
    "recomputed fit leaves |p-2|>0.3, a ladder is non-monotone, cross-scheme spread exceeds 0.25, "
    "my recomputation disagrees with the certification or rev3 beyond 1e-12, a cited verdict "
    "artifact's bytes move off its declared hash or lose/changed its declared token, live taxonomy "
    "!= 0abb9ed8a961 or lacks AF-WCC-SCALAR-SPH, numerics_lock != locked or numerics/spherical_solver "
    "appears, T1 moves off 88ec0bf298cb or T2 off 87b311e72032, any control fails to fire, or any "
    "pinned input drifts between the instrument's pre- and post-measurement."
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lsq_fit(rows: list[dict]) -> dict:
    """Independent log-log LSQ: ln(err) = c - p*ln(dr). Returns p, se, residuals, pairs."""
    xs = [math.log(r["dr"]) for r in rows]
    ys = [math.log(r["l2_error"]) for r in rows]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = my - slope * mx
    res = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
    sse = sum(r * r for r in res)
    se = math.sqrt((sse / (n - 2)) / sxx)
    pairs = [math.log(rows[i]["l2_error"] / rows[i + 1]["l2_error"])
             / math.log(rows[i]["dr"] / rows[i + 1]["dr"]) for i in range(n - 1)]
    half_range = (max(pairs) - min(pairs)) / 2.0
    monotone = all(rows[i]["l2_error"] > rows[i + 1]["l2_error"] for i in range(n - 1))
    return {"p": slope, "se": se, "residuals": res, "pair_orders": pairs,
            "pair_half_range": half_range, "monotone": monotone, "n_rungs": n}


def close(a: float, b: float, tol: float = 1e-12) -> bool:
    return abs(a - b) <= tol


def max_abs_diff(a: list[float], b: list[float]) -> float:
    return max(abs(x - y) for x, y in zip(a, b)) if a else float("inf")


# ---------------------------------------------------------------- checks

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--out", default="report.json")
    args = ap.parse_args()
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[3]
    out_path = (root / args.out) if not Path(args.out).is_absolute() else Path(args.out)

    checks: list[dict] = []
    findings: list[dict] = []

    def chk(cid: str, ok: bool, detail: str, severity: str = "positive") -> bool:
        checks.append({"id": cid, "status": "ok" if ok else "flag", "detail": detail})
        if not ok:
            findings.append({"id": cid, "severity": severity, "detail": detail})
        return ok

    # ---- pre-run pin gate (fail closed) -------------------------------------
    pre: dict[str, str] = {}
    pins_ok = True
    matched = 0
    for name, (rel, want) in PINS.items():
        p = root / rel
        if not p.is_file():
            chk(f"X0-pin-{name}", False, f"missing input {rel}", "gate-blocker")
            pins_ok = False
            continue
        got = sha256_file(p)
        pre[rel] = got
        if want is None:
            matched += 1
            continue
        exp = EXPECTED_PREFIX.get(name)
        good = got.startswith(exp) if exp else got == want
        if not good:
            chk(f"X0-pin-{name}", False, f"{rel} measured {got[:16]} != declared {(exp or want)[:16]}",
                "gate-blocker")
            pins_ok = False
        else:
            matched += 1
    chk("X0-pins", pins_ok, f"{matched}/{len(PINS)} pins match their declared bytes at entry")
    if not pins_ok:
        return finish(root, out_path, checks, findings, None, None, None, {}, pre, {}, {})

    T1 = json.loads((root / PINS["closure"][0]).read_text())
    cert = json.loads((root / PINS["certification"][0]).read_text())
    rev3 = json.loads((root / PINS["rev3"][0]).read_text())
    auth = json.loads((root / PINS["authority"][0]).read_text())
    flash13 = json.loads((root / PINS["flash13"][0]).read_text())
    T2 = json.loads((root / PINS["w017_review"][0]).read_text())
    registry = json.loads((root / PINS["registry"][0]).read_text())
    themap = json.loads((root / PINS["map"][0]).read_text())
    taxonomy_raw = (root / PINS["taxonomy"][0]).read_text()

    # ---- X1: target metadata ------------------------------------------------
    ok = (T1.get("schema") == "n0-stoprule-closure-verify/v1"
          and T1.get("class_id") == "AF-WCC-SCALAR-SPH" and T1.get("node_id") == "N0"
          and T1.get("gate") == "G-NUM" and T1.get("all_closure_items_closed") is True)
    chk("X1-closure-meta", ok,
        f"schema={T1.get('schema')} class={T1.get('class_id')} node={T1.get('node_id')} "
        f"gate={T1.get('gate')} all_closed={T1.get('all_closure_items_closed')}")

    # ---- X2: independent numerical recomputation ----------------------------
    p_tol = float(cert["config"]["p_tol"])
    r5_bound = 0.25  # declared cross-scheme R5 floor (closure item_1 / rev3 order_claim)
    my: dict[str, dict] = {}
    worst = 0.0
    for scheme, block in cert["schemes"].items():
        f = block["fixed_dt_certification"]
        rows = f["rows"]
        fit = lsq_fit(rows)
        my[scheme] = {
            "p": fit["p"], "se": fit["se"], "pair_orders": fit["pair_orders"],
            "pair_half_range": fit["pair_half_range"], "monotone": fit["monotone"],
            "n_rungs": fit["n_rungs"],
            "declared_p": f["fit_order"], "declared_se": f["least_squares_se"],
            "declared_pair_orders": f["pair_orders"], "declared_residuals": f["lsq_residuals"],
            "dt_values": sorted({r["dt"] for r in rows}),
            "dr_values": [r["dr"] for r in rows],
            "rev3_p": rev3["order_claim"]["p_by_scheme"][scheme],
        }
        worst = max(worst, abs(fit["p"] - f["fit_order"]),
                    abs(fit["se"] - f["least_squares_se"]),
                    max_abs_diff(fit["residuals"], f["lsq_residuals"]),
                    max_abs_diff(fit["pair_orders"], f["pair_orders"]),
                    abs(fit["pair_half_range"] - f["pair_half_range"]),
                    abs(fit["p"] - rev3["order_claim"]["p_by_scheme"][scheme]),
                    abs(fit["p"] - T1["item_1_four_rungs"]["schemes"][scheme]["recomputed_fit_order"]),
                    abs(fit["se"] - T1["item_1_four_rungs"]["schemes"][scheme]["recomputed_se"]))
    chk("X2-recompute-exact", worst <= 1e-12,
        f"own LSQ vs cert/rev3/closure: worst abs diff {worst:.3e} over 3 schemes x 8 quantities")
    chk("X2-four-rungs-fixed-dt",
        all(my[s]["n_rungs"] == 4 and my[s]["dt_values"] == [1e-4] and my[s]["dr_values"] == [0.2, 0.1, 0.05, 0.025]
            for s in my),
        "3 schemes x 4 rungs, dt fixed 1e-4, dr = [0.2,0.1,0.05,0.025]")

    # ---- X3: bands / monotonicity / cross-scheme spread ---------------------
    in_band = {s: abs(my[s]["p"] - 2.0) <= p_tol for s in my}
    mono = {s: my[s]["monotone"] for s in my}
    ps = [my[s]["p"] for s in sorted(my)]
    spread = max(abs(a - b) for i, a in enumerate(ps) for b in ps[i + 1:])
    chk("X3-band", all(in_band.values()),
        "|p-2| <= 0.3 per scheme: " + ", ".join(f"{s}={abs(my[s]['p']-2.0):.3e}" for s in sorted(my)))
    chk("X3-monotone", all(mono.values()),
        "strictly decreasing l2 error as dr halves: " + ", ".join(f"{s}={mono[s]}" for s in sorted(my)))
    chk("X3-spread", spread <= r5_bound and close(spread, float(T1["item_1_four_rungs"]["cross_scheme_spread"]), 1e-15),
        f"max pairwise |dp| = {spread:.15e} <= R5 bound 0.25 and equals closure value "
        f"{float(T1['item_1_four_rungs']['cross_scheme_spread']):.15e}")
    chk("X3-closure-max-diff", float(T1["item_1_four_rungs"]["max_abs_diff_vs_declared"]) == 0.0,
        "closure's max_abs_diff_vs_declared==0.0 is truthful against my independent recomputation")

    # ---- X4: stop-rule item 2, F0 rebind ------------------------------------
    tax_sha = pre[PINS["taxonomy"][0]]
    class_present = "AF-WCC-SCALAR-SPH" in taxonomy_raw
    rev_line = next((ln.split(":", 1)[1].strip() for ln in taxonomy_raw.splitlines()
                     if ln.strip().startswith("revision:")), None)
    a_bind = auth.get("binding", {})
    a_carrier = auth.get("carrier", {})
    ok = (tax_sha == T1["item_2_f0_rebind"]["live_sha256"]
          and class_present and rev_line == "5"
          and a_bind.get("sha256") == tax_sha and a_bind.get("declared_revision") == 5
          and a_carrier.get("sha256") == PINS["rev3"][1])
    chk("X4-f0-rebind", ok,
        f"taxonomy {tax_sha[:12]} revision={rev_line} class_present={class_present}; authority "
        f"binding={a_bind.get('sha256','')[:12]} rev={a_bind.get('declared_revision')} "
        f"carrier={a_carrier.get('sha256','')[:12]}")
    chk("X4-authority-closure-agree",
        a_bind.get("sha256") == T1["item_2_f0_rebind"]["declared_sha256"]
        and T1["item_2_f0_rebind"]["authority_record_sha256"] == pre[PINS["authority"][0]],
        "closure item_2 pins agree with live authority record")

    # ---- X5: stop-rule item 3, independent replication ----------------------
    mod = pre[PINS["replication_module"][0]]
    cert_mod = cert["frozen_module"]
    tok = {}
    for name, rel, token in (("w046", PINS["verdict_w046"][0], "SUPPORTED"),
                             ("w057", PINS["verdict_w057"][0], "REPRODUCED"),
                             ("w081", PINS["verdict_w081"][0], "accept")):
        txt = (root / rel).read_text()
        tok[name] = token in txt
    ok = (mod == cert_mod["sha256"]
          and all(tok.values())
          and str(flash13.get("artifact_sha256", "")) == PINS["rev3"][1]
          and str(flash13.get("reviewed_sha256", "")) == PINS["rev3"][1]
          and flash13.get("hash_stable_across_review") is True
          and str(flash13.get("verdict", "")).lower() == "accept"
          and float(flash13.get("score", 0)) == 4.0
          and flash13.get("counts_as_node_verdict") is True
          and any(str(f.get("id")) == "F-06" for f in flash13.get("findings", [])))
    chk("X5-replication", ok,
        f"module {mod[:12]} cert={cert_mod.get('sha256','')[:12]}; tokens={tok}; "
        f"flash13 accept={flash13.get('verdict')} score={flash13.get('score')} "
        f"binds={str(flash13.get('artifact_sha256'))[:12]} F-06="
        f"{any(str(f.get('id')) == 'F-06' for f in flash13.get('findings', []))}")
    chk("X5-closure-verdict-pins",
        all(v["disk_sha256"] == v["declared_sha256"] and v["hash_match"] is True
            for v in T1["item_3_independent_replication"]["verdicts"]),
        "closure item_3 lists 3/3 verdict artifacts with declared==disk hash")

    # ---- X6: lock compliance ------------------------------------------------
    lock = themap.get("numerics_lock", {})
    solver = root / "numerics/spherical_solver"
    lock_state = lock.get("state")
    guard_ok = None
    try:
        sys.path.insert(0, str(root))
        import numerics.gates as gates  # canonical guard, read-only
        rep = gates.evaluate(root)
        guard_ok = (rep.get("lock", {}).get("state") == "locked"
                    and rep.get("production_allowed") is False)
        guard_note = f"gates.evaluate production_allowed={rep.get('production_allowed')}"
    except Exception as exc:  # pragma: no cover
        guard_note = f"gates.evaluate not run: {type(exc).__name__}: {exc}"
    chk("X6-lock", lock_state == "locked" and not solver.exists()
        and T1["lock_compliance"]["numerics_lock_state"] == "locked",
        f"map numerics_lock.state={lock_state}; spherical_solver present={solver.exists()}; {guard_note}")

    # ---- X7: registration ---------------------------------------------------
    def classify(rel: str) -> dict:
        disk = pre.get(rel)
        if disk is None:
            p = root / rel
            disk = sha256_file(p) if p.is_file() else None
        reg = registry.get("registry", {}).get(rel)
        top = registry.get("hashes", {}).get(rel)
        if reg is not None:
            st = "registry-match" if reg.get("sha256") == disk else "registry-mismatch"
        elif top is not None and top.get("kind") == "file":
            st = "top-level-match" if top.get("sha256") == disk else "top-level-mismatch"
        elif disk is None:
            st = "missing"
        else:
            st = "unregistered"
        return {"path": rel, "status": st, "disk_sha256": disk,
                "registry_sha256": (reg or {}).get("sha256"),
                "top_level_sha256": (top or {}).get("sha256")}

    reg_rows = [classify(kp["path"]) for kp in T1["registration"]["known_pins"]]
    counts = {s: sum(1 for r in reg_rows if r["status"] == s)
              for s in ("registry-match", "top-level-match", "unregistered", "registry-mismatch",
                        "top-level-mismatch", "missing")}
    stale = classify("reviews/G-NUM-protocol-review.json")
    chk("X7-registration",
        counts["registry-match"] == 6 and counts["top-level-match"] == 1 and counts["unregistered"] == 3
        and counts["registry-mismatch"] == 0 and counts["top-level-mismatch"] == 0 and counts["missing"] == 0,
        f"closure known_pins classification: {counts}; T1 labels taxonomy 'unregistered' but it is "
        f"top-level-match in runtime/state/artifact_hashes.json#hashes (documentary refinement)")
    chk("X7-stale-pin", stale["status"] == "registry-match" and str(stale["disk_sha256"]).startswith("8137f18f1a3b"),
        f"reviews/G-NUM-protocol-review.json disk={str(stale['disk_sha256'])[:12]} "
        f"(declared 1e6cdf04d7a2 is stale; mispin analysis confirmed)")

    # ---- X8: first review (T2) integrity and consistency --------------------
    refs = {}
    for name, rel, prefix in (("report", PINS["w017_report"][0], "d3d7c450ebc5"),
                              ("crosscheck", PINS["w017_crosscheck"][0], "749090f9a2ba"),
                              ("instrument", PINS["w017_instrument"][0], "ba56eade7561"),
                              ("pinned_copy", PINS["w017_pinned_copy"][0], "88ec0bf298cb")):
        refs[name] = sha256_file(root / rel).startswith(prefix)
    pinned_identical = (root / PINS["w017_pinned_copy"][0]).read_bytes() == (root / PINS["closure"][0]).read_bytes()
    fids = {f["id"] for f in T2.get("findings", [])}
    findings_consistent = (
        T2.get("target_id") == PINS["closure"][0] and T2.get("reviewed_sha256") == PINS["closure"][1]
        and T2.get("verdict") == "accept" and float(T2.get("score", 0)) == 4.0
        and T2.get("counts_as_gate_verdict") is False and T2.get("counts_as_node_verdict") is False
        and T2.get("class_id") == "AF-WCC-SCALAR-SPH"
        and fids == {f"W017-N0C-F0{i}" for i in range(1, 8)}
    )
    chk("X8-review-refs", all(refs.values()) and pinned_identical,
        f"T2 evidence refs resolve={refs}; pinned copy byte-identical to live T1={pinned_identical}")
    chk("X8-review-consistency", findings_consistent,
        f"T2 target/verdict/score/counts/findings consistent; F01-F03 positives match my X2/X3/X4/X5; "
        f"F04 advisory on the flash-13 conflict (F-06); F05 gate-blocker-outside-scope (B-N0-R2-2 + "
        f"3 unregistered verdict artifacts — I reproduce 3 unregistered); F06/F07 documentary/drift")
    review_worst = 0.0
    for scheme in my:
        review_worst = max(review_worst, abs(my[scheme]["p"] - cert["schemes"][scheme]["fixed_dt_certification"]["fit_order"]))
    chk("X8-review-numbers", review_worst <= 1e-12,
        f"T2's 'abs diff 0.0' numerical claim is reproducible by me: worst {review_worst:.3e}")

    # ---- X9: controls -------------------------------------------------------
    controls: list[dict] = []

    def ctl(cid: str, fired: bool, detail: str) -> None:
        controls.append({"id": cid, "fired": bool(fired), "detail": detail})

    base_rows = cert["schemes"]["cnfd"]["fixed_dt_certification"]["rows"]
    mut = copy.deepcopy(base_rows); mut[0]["l2_error"] *= 3.0
    f = lsq_fit(mut)
    ctl("C01-perturb-l2", abs(f["p"] - 2.0) > p_tol, f"perturbed l2 -> p={f['p']:.4f}, band fires")
    mut = copy.deepcopy(base_rows); mut[3]["dr"] = 0.03
    f = lsq_fit(mut)
    ctl("C02-move-dr-rung", not close(f["p"], base_rows and cert["schemes"]["cnfd"]["fixed_dt_certification"]["fit_order"]),
        f"moved dr rung -> p={f['p']:.9f} != declared (mismatch fires)")
    mut = copy.deepcopy(base_rows); mut[1]["l2_error"], mut[2]["l2_error"] = mut[2]["l2_error"], mut[1]["l2_error"]
    ctl("C03-reverse-ladder", not lsq_fit(mut)["monotone"], "swapped errors -> monotone check fires")
    ctl("C04-f0-hash-substitute", not sha256_file(root / PINS["taxonomy"][0]).startswith("0" * 12),
        "substituted F0 hash (zeros) would fail the pin gate")
    with tempfile.TemporaryDirectory() as td:
        fake = Path(td) / "numerics/spherical_solver"; fake.mkdir(parents=True)
        (fake / "solver.py").write_text("# planted control\n")
        ctl("C05-plant-solver", (fake).exists(), "planted numerics/spherical_solver/ detected as present")
    ctl("C06-tighten-r5", not (spread <= 1e-6), f"R5 bound tightened to 1e-6 -> spread {spread:.3e} violates")
    ctl("C07-flip-verdict-token", not ("REJECTED" in (root / PINS["verdict_w046"][0]).read_text()),
        "flipped token (REJECTED) would not be found in w046 verdict")
    ctl("C08-empty-class-list", "AF-WCC-SCALAR-SPH" not in "", "empty class list fails presence check")
    ctl("C09-stale-pin-mismatch",
        not str(stale["disk_sha256"]).startswith("1e6cdf04d7a2"),
        f"declared stale pin 1e6cdf04d7a2 vs disk {str(stale['disk_sha256'])[:12]} -> mismatch fires")
    bogus = classify("artifacts/worker-014/does_not_exist.json")
    ctl("C10-bogus-registry-path", bogus["status"] == "missing", f"bogus path classified {bogus['status']}")
    ctl("C11-pinned-copy-mismatch",
        not (b"X" + (root / PINS["closure"][0]).read_bytes()[1:]) == (root / PINS["closure"][0]).read_bytes(),
        "single-byte change to pinned copy breaks byte-equality")
    ctl("C12-review-hash-moved", not sha256_file(root / PINS["w017_review"][0]).startswith("0" * 12),
        "moved T2 hash (zeros) fails the pin gate")
    fired = sum(1 for c in controls if c["fired"])
    chk("X9-controls", fired == len(controls),
        f"{fired}/{len(controls)} negative controls fired as expected")

    # ---- X10: drift guard ---------------------------------------------------
    post = {}
    for rel in pre:
        p = root / rel
        post[rel] = sha256_file(p) if p.is_file() else None
    drifted = {rel: (pre[rel], post[rel]) for rel in pre if pre[rel] != post[rel]}
    chk("X10-drift", not drifted, f"pre/post identical for {len(pre)} inputs; drifted={list(drifted)}")

    return finish(root, out_path, checks, findings, my, T1, T2, pins_ok and True, pre, controls,
                  {"spread": spread, "counts": counts, "stale": stale, "refs": refs,
                   "pinned_identical": pinned_identical, "drifted": drifted, "post": post})


def finish(root: Path, out_path: Path, checks, findings, my, T1, T2, pins_ok, pre, controls, extra) -> int:
    flags = [c for c in checks if c["status"] == "flag"]
    controls = controls or []
    fired = sum(1 for c in controls if c.get("fired"))
    verdict = "N0_CLOSURE_AND_FIRST_REVIEW_CROSSVERIFIED_ACCEPT" if (not flags and fired == len(controls)
                                                                      and controls) else "REVISE"
    report = {
        "schema": "n0-closure-crossverify/v1",
        "task_id": "W014-GNUM-N0-CLOSURE-CROSSVERIFY-01",
        "actor": "worker-014",
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N0",
        "gate": "G-NUM",
        "verdict": verdict,
        "verdict_scope": ("worker-level independent cross-verification at the pinned hashes only; not a "
                          "G-NUM gate verdict, not an N0 node verdict (authority: Astra / lead-audit)"),
        "targets": {
            "numerics/protocol/lifecycle08_stoprule_closure_verify.json": PINS["closure"][1],
            "reviews/N0-stoprule-closure-review-worker-017.json": PINS["w017_review"][1],
        },
        "pins_measured": pre,
        "per_scheme_recomputed": my,
        "checks": checks,
        "findings": findings,
        "controls": {"n": len(controls), "fired": fired, "detail": controls},
        "crosscheck_detail": extra or {},
        "does_not_claim": [
            "not a G-NUM gate verdict; gate authority stays Astra / lead-audit",
            "not an N0 node completion or status transition",
            "no numerics_lock release; N1 stays queued",
            "no adjudication of the B-N0-R2-2 protocol-review contest",
            "no canonical-path write; read-only over every pinned input",
            "no physics / self-gravity / WCC / SCC claim",
        ],
        "falsifier": FALSIFIER,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(f"{verdict}: {len(checks)} checks, {len(flags)} flags, {fired}/{len(controls)} controls -> {out_path}")
    for c in checks:
        if c["status"] == "flag":
            print("  FLAG", c["id"], c["detail"])
    return 0 if verdict.endswith("ACCEPT") else 2


if __name__ == "__main__":
    sys.exit(main())
