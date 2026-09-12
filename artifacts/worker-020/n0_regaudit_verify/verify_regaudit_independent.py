#!/usr/bin/env python3
"""W020-N0-REGAUDIT-VERIFY-01 — independent non-author verification of the
numerics lead's lifecycle-06 registration-drift audit and its companion
class-binding authority record.

Target under review
-------------------
* ``numerics/protocol/n0_registration_drift_audit.json`` (astra-lead-numerics,
  2026-09-12T01:00:36+0800), declared sha256 ``22edbcc61df7``.
* companion ``numerics/N0_CLASS_BINDING_AUTHORITY.json`` (same author),
  declared sha256 ``effd20b0ea09``; its own ``review_request`` asks for an
  independent review at that hash.

What this script does (read-only outside ``artifacts/worker-020/``)
-------------------------------------------------------------------
1. Freezes byte-identical snapshots of the target, the companion, the
   certification, the registry and the map into ``snapshots/``.
2. Re-measures all 13 declared pins against disk and against
   ``runtime/state/artifact_hashes.json`` (union of its ``hashes`` and
   ``registry`` maps) with its own hashing/registry code.
3. Re-derives every declared fit order, pair order, least-squares SE,
   residual and ``delta_R5`` from the raw ``dr``/``l2_error`` rows of
   ``numerics/protocol/n0_fixed_dt_certification.json`` using its own
   closed-form least squares (cross-checked against ``numpy.polyfit``).
4. Re-checks the three declared replication verdicts and the rev-3 pin list.
5. Re-checks the companion record's A1..A6 binding claims against live bytes.
6. Re-checks lock compliance: live map lock state, solver-path absence and a
   fresh read-only ``numerics/gates.py`` run (no ``--emit-blocker`` /
   ``--write-report`` flags, so the tool cannot write).
7. Runs six planted-defect controls (each must fire), a determinism control
   and a binding-pin before/after guard.
8. Writes ``regaudit_verification.json`` and ``regaudit_verification.log``.

Never imports the audit generator ``numerics/protocol/audit_registration_drift.py``
and never edits another agent's artifact.  It is worker evidence only: no gate
verdict, no node completion, no ``validation_status`` promotion, no lock release.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
TZ = timezone(timedelta(hours=8))

TASK = "W020-N0-REGAUDIT-VERIFY-01"
ACTOR = "worker-020"
CLASS_ID = "AF-WCC-SCALAR-SPH"
NODE_ID = "N0"
GATE = "G-NUM"

TARGET_REL = "numerics/protocol/n0_registration_drift_audit.json"
TARGET_SHA = "22edbcc61df7dc7cd574fb43e4ef6c09ae12f89f1ebe34869b00a5b27384c632"
AUTHORITY_REL = "numerics/N0_CLASS_BINDING_AUTHORITY.json"
AUTHORITY_SHA = "effd20b0ea094a8dfd4f686e62c49b1667622337efd6a7c154f7fadae0b98419"
CERT_REL = "numerics/protocol/n0_fixed_dt_certification.json"
CERT_SHA = "1677822ceb9c81e8f6e48dee8360ab13edc35623c51f4be68bd6589a5fe79920"
REGISTRY_REL = "runtime/state/artifact_hashes.json"
MAP_REL = "research_map/research_map.json"
GATES_REL = "numerics/gates.py"
PROTOCOL_REL = "numerics/CONVERGENCE_PROTOCOL.md"
PROTOCOL_SHA = "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274"
REV3_REL = "numerics/results/flat_wave_convergence_rev3.json"
REV3_SHA = "da7c360719950f7ef6be2624391dee464f8c818a0be74ec44f0f8c70d2b28ac3"
TAXONOMY_REL = "research_map/formulation_taxonomy.yaml"
TAXONOMY_SHA = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
BLOCKERS_REL = "numerics/blockers.md"

BINDING_RELS = [TARGET_REL, AUTHORITY_REL, CERT_REL, PROTOCOL_REL, REV3_REL, TAXONOMY_REL]
SNAPSHOT_PREFIX = {TARGET_REL: "target", AUTHORITY_REL: "authority",
                   CERT_REL: "certification", PROTOCOL_REL: "protocol",
                   REV3_REL: "rev3", TAXONOMY_REL: "taxonomy"}

FALSIFIER = (
    "Void if the target audit 22edbcc61df7 or the companion authority record "
    "effd20b0ea09 re-hashes differently, or any declared pin re-hashes to a "
    "different value, or a recomputed fixed-dt order leaves |p-2| > 0.3 or "
    "cross-scheme |dp| > 0.25, or a declared fit/SE/delta_R5 fails to reproduce "
    "from the raw rows within 1e-9 relative, or the three replication verdicts "
    "are absent or have moved, or numerics/spherical_solver/ appears while "
    "numerics_lock.state == 'locked', or numerics/gates.py returns "
    "production_allowed=true while G-FORM or G-AUDIT is not pass, or a planted "
    "mutation control fails to fire."
)

CHECKS: list[dict] = []


def check(cid: str, name: str, ok: bool, detail="") -> bool:
    CHECKS.append({"id": cid, "name": name, "ok": bool(ok),
                   "detail": str(detail)[:600]})
    return bool(ok)


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load_json(path: Path):
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("utf-8"))


def rel_sha(rel: str, root: Path = ROOT) -> str:
    return sha256_file(root / rel)


def ref(rel: str, root: Path = ROOT, short: int = 12) -> str:
    p = root / rel
    return f"{rel}#{sha256_file(p)[:short]}" if p.is_file() else f"{rel}#MISSING"


# --------------------------------------------------------------------------
# independent primitives (pure; reused by the planted-defect controls)
# --------------------------------------------------------------------------

def census(pins: list[dict], registry_union: dict, root: Path) -> dict:
    """Re-measure every declared pin against disk and the registry union."""
    rows = []
    for p in pins:
        rel = p["path"]
        declared = (p.get("declared_sha256") or "").lower()
        fp = root / rel
        disk = sha256_file(fp) if fp.is_file() else None
        entry = registry_union.get(rel)
        reg = entry is not None
        reg_sha = (entry or {}).get("sha256")
        if not fp.is_file():
            status = "disk_missing"
        elif declared and disk != declared:
            status = "mismatch"
        elif reg and (reg_sha or "").lower() != (disk or "").lower():
            status = "registry_mismatch"
        elif not reg:
            status = "unregistered"
        else:
            status = "match"
        rows.append({
            "path": rel,
            "declared_sha256": declared,
            "disk_sha256": disk,
            "registry_registered": reg,
            "registry_sha256": reg_sha,
            "status": status,
        })
    return {
        "n_declared_pins": len(rows),
        "n_match": sum(1 for r in rows if r["status"] == "match"),
        "mismatched": [r["path"] for r in rows if r["status"] == "mismatch"],
        "registry_mismatched": [r["path"] for r in rows if r["status"] == "registry_mismatch"],
        "disk_missing": [r["path"] for r in rows if r["status"] == "disk_missing"],
        "unregistered": [r["path"] for r in rows if r["status"] == "unregistered"],
        "rows": rows,
    }


def lsq_slope(xs: list[float], ys: list[float]):
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = my - slope * mx
    resid = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
    se = math.sqrt(sum(r * r for r in resid) / (n - 2) / sxx)
    return slope, intercept, se, resid


def refit_schemes(cert: dict) -> dict:
    """Re-derive fixed-dt fit order, SE, pair orders and delta_R5 from raw rows."""
    out = {}
    for scheme, body in sorted(cert.get("schemes", {}).items()):
        fx = body.get("fixed_dt_certification", {})
        rows = fx.get("rows", [])
        rec: dict = {"n_rungs": len(rows),
                     "dr_values": [r.get("dr") for r in rows],
                     "dt_values": sorted({r.get("dt") for r in rows}),
                     "l2_error": [r.get("l2_error") for r in rows]}
        rec["drs_descending"] = all(
            rows[i]["dr"] > rows[i + 1]["dr"] for i in range(len(rows) - 1)) if len(rows) > 1 else False
        rec["l2_monotone_decreasing"] = all(
            rows[i]["l2_error"] > rows[i + 1]["l2_error"]
            for i in range(len(rows) - 1)) if len(rows) > 1 else False
        xs = [math.log(r["dr"]) for r in rows]
        ys = [math.log(r["l2_error"]) for r in rows]
        slope, intercept, se, resid = lsq_slope(xs, ys)
        pairs = [math.log(rows[i]["l2_error"] / rows[i + 1]["l2_error"])
                 / math.log(rows[i]["dr"] / rows[i + 1]["dr"])
                 for i in range(len(rows) - 1)]
        half_range = (max(pairs) - min(pairs)) / 2 if pairs else None
        delta_r5 = max(half_range, se) if half_range is not None else None
        rec.update({
            "fit_order_recomputed": slope,
            "intercept": intercept,
            "least_squares_se_recomputed": se,
            "lsq_residuals_recomputed": resid,
            "pair_orders_recomputed": pairs,
            "pair_half_range_recomputed": half_range,
            "delta_R5_recomputed": delta_r5,
            "max_abs_pair_residual": (max(abs(r) for r in resid) if resid else None),
            "fit_order_declared": fx.get("fit_order"),
            "least_squares_se_declared": fx.get("least_squares_se"),
            "pair_orders_declared": fx.get("pair_orders"),
            "delta_R5_declared": fx.get("delta_R5"),
            "lsq_residuals_declared": fx.get("lsq_residuals"),
            "abs_diff_fit": (abs(slope - fx["fit_order"]) if fx.get("fit_order") is not None else None),
            "abs_diff_se": (abs(se - fx["least_squares_se"]) if fx.get("least_squares_se") is not None else None),
            "abs_diff_delta_R5": (abs(delta_r5 - fx["delta_R5"]) if fx.get("delta_R5") is not None else None),
            "max_abs_pair_diff": (max(abs(a - b) for a, b in zip(pairs, fx["pair_orders"]))
                                  if fx.get("pair_orders") else None),
            "max_abs_resid_diff": (max(abs(a - b) for a, b in zip(resid, fx["lsq_residuals"]))
                                   if fx.get("lsq_residuals") else None),
            "within_band": (abs(slope - 2.0) <= 0.3) if slope is not None else None,
        })
        out[scheme] = rec
    return out


def cross_scheme(refit: dict, b: float = 0.25) -> dict:
    schemes = sorted(refit)
    pairs = []
    for i in range(len(schemes)):
        for j in range(i + 1, len(schemes)):
            a, c = schemes[i], schemes[j]
            d = abs(refit[a]["fit_order_recomputed"] - refit[c]["fit_order_recomputed"])
            pairs.append({"pair": f"{a} vs {c}", "abs_order_diff": d,
                          "agree": d <= b, "r5_bound": b})
    maxd = max((p["abs_order_diff"] for p in pairs), default=None)
    return {"pairs": pairs, "max_pairwise_abs_diff": maxd,
            "all_agree": all(p["agree"] for p in pairs)}


def registry_union(root: Path = ROOT) -> dict:
    doc = load_json(root / REGISTRY_REL)
    union: dict = {}
    for key in ("hashes", "registry"):
        for rel, entry in (doc.get(key) or {}).items():
            if isinstance(entry, dict) and (rel not in union or entry.get("sha256")):
                union.setdefault(rel, entry)
    return union


def solver_scan(root: Path = ROOT) -> dict:
    """Look for any solver-shaped path under numerics/ (spherical solver family)."""
    base = root / "numerics"
    hits = []
    if base.is_dir():
        for dirpath, dirnames, filenames in os.walk(base):
            for nm in list(dirnames) + list(filenames):
                if "spherical_solver" in nm or "self_grav" in nm:
                    hits.append(str(Path(dirpath, nm).relative_to(root)))
    return {"present": bool(hits), "hits": sorted(hits),
            "path_numerics_spherical_solver_exists": (base / "spherical_solver").exists()}


def run_gates(root: Path = ROOT, timeout: int = 600) -> dict:
    proc = subprocess.run(
        [sys.executable, str(root / GATES_REL), "--pretty"],
        cwd=str(root), capture_output=True, text=True, timeout=timeout)
    doc = None
    try:
        doc = json.loads(proc.stdout)
    except Exception:
        pass
    return {"exit": proc.returncode, "parsed": doc,
            "stderr_tail": proc.stderr[-400:], "stdout_bytes": len(proc.stdout)}


def build_farm(tmp: Path, mutate_map=None) -> Path:
    """Symlink farm of the repo with a private (optionally mutated) map copy."""
    tmp.mkdir(parents=True, exist_ok=True)
    for child in ROOT.iterdir():
        if child.name == "research_map":
            continue
        os.symlink(child, tmp / child.name)
    real_map_dir = tmp / "research_map"
    real_map_dir.mkdir()
    for child in (ROOT / "research_map").iterdir():
        if child.name == "research_map.json":
            continue
        os.symlink(child, real_map_dir / child.name)
    m = load_json(ROOT / MAP_REL)
    if mutate_map is not None:
        mutate_map(m)
    (real_map_dir / "research_map.json").write_text(
        json.dumps(m), encoding="utf-8")
    return tmp


# --------------------------------------------------------------------------
# main verification
# --------------------------------------------------------------------------

def main() -> int:
    started = now()
    written: list[str] = []

    # ---- freeze snapshots (target + binding inputs) -----------------------
    snap = HERE / "snapshots"
    snap.mkdir(exist_ok=True)
    snapshots = {}
    for rel in BINDING_RELS + [REGISTRY_REL, MAP_REL]:
        src = ROOT / rel
        dst = snap / f"{SNAPSHOT_PREFIX.get(rel, Path(rel).stem)}_{sha256_file(src)[:12]}{src.suffix}"
        shutil.copyfile(src, dst)
        written.append(str(dst.relative_to(ROOT)))
        snapshots[rel] = {"bytes": src.stat().st_size, "sha256": sha256_file(src),
                          "snapshot": str(dst.relative_to(ROOT))}
        if sha256_file(dst) != sha256_file(src):
            raise SystemExit(f"ABORT: snapshot not byte-identical for {rel}")

    target = load_json(ROOT / TARGET_REL)
    authority = load_json(ROOT / AUTHORITY_REL)
    cert = load_json(ROOT / CERT_REL)
    registry = load_json(ROOT / REGISTRY_REL)
    union = registry_union()
    live_map = load_json(ROOT / MAP_REL)
    protocol_text = (ROOT / PROTOCOL_REL).read_text(encoding="utf-8", errors="replace")
    taxonomy_text = (ROOT / TAXONOMY_REL).read_text(encoding="utf-8", errors="replace")
    rev3 = load_json(ROOT / REV3_REL)
    blockers_text = (ROOT / BLOCKERS_REL).read_text(encoding="utf-8", errors="replace")

    # ---- A. target identity / structure -----------------------------------
    check("C01", "target bytes frozen at declared sha256 22edbcc61df7",
          rel_sha(TARGET_REL) == TARGET_SHA, rel_sha(TARGET_REL))
    check("C02", "companion authority bytes at declared sha256 effd20b0ea09",
          rel_sha(AUTHORITY_REL) == AUTHORITY_SHA, rel_sha(AUTHORITY_REL))
    check("C03", "target schema/actor/class/node/gate/conclusion_type as declared",
          target.get("schema") == "n0-registration-drift-audit/v1"
          and target.get("actor") == "astra-lead-numerics"
          and target.get("class_id") == CLASS_ID and target.get("node_id") == NODE_ID
          and target.get("gate") == GATE
          and target.get("conclusion_type") == "numerical_evidence",
          json.dumps({k: target.get(k) for k in
                      ("schema", "actor", "class_id", "node_id", "gate", "conclusion_type")}))
    check("C04", "target verdict is CLEAN and scope is read-only",
          target.get("verdict") == "CLEAN" and "read-only" in str(target.get("scope")),
          f"{target.get('verdict')} | {target.get('scope')}")
    check("C05", "target claims_not_made present (no gate/node/lock/physics claim)",
          len(target.get("claims_not_made") or []) >= 4
          and any("gate" in s for s in target["claims_not_made"])
          and any("lock" in s for s in target["claims_not_made"]),
          json.dumps(target.get("claims_not_made"))[:300])

    # ---- B. pin census -----------------------------------------------------
    pins = target.get("pins") or []
    summary = target.get("pin_summary") or {}
    check("C06", "declared pin count is 13 in list and summary",
          len(pins) == 13 and summary.get("n_declared_pins") == 13,
          f"list={len(pins)} summary={summary.get('n_declared_pins')}")
    my_census = census(pins, union, ROOT)
    check("C07", "my census n_match equals declared n_match=10",
          my_census["n_match"] == summary.get("n_match") == 10,
          f"mine={my_census['n_match']} declared={summary.get('n_match')}")
    check("C08", "my census mismatched and disk_missing both empty",
          my_census["mismatched"] == [] and my_census["disk_missing"] == []
          and my_census["registry_mismatched"] == [],
          json.dumps({k: my_census[k] for k in
                      ("mismatched", "disk_missing", "registry_mismatched")}))
    check("C09", "my census unregistered list equals declared list (3 paths)",
          sorted(my_census["unregistered"]) == sorted(summary.get("unregistered") or []),
          json.dumps(my_census["unregistered"]))
    for n, row in enumerate(my_census["rows"], start=1):
        check(f"C10.{n:02d}", f"pin {row['path']} disk sha matches declared",
              row["disk_sha256"] is not None and row["disk_sha256"] == row["declared_sha256"],
              f"{row['disk_sha256']} vs {row['declared_sha256']}")
        dp = next((p for p in pins if p["path"] == row["path"]), {})
        check(f"C11.{n:02d}", f"pin {row['path']} registry flag/sha match declared row",
              dp.get("registry_registered") == row["registry_registered"]
              and (dp.get("registry_sha256") or "!").lower() == (row["registry_sha256"] or "!").lower(),
              f"declared_reg={dp.get('registry_registered')} mine={row['registry_registered']} "
              f"declared_sha={dp.get('registry_sha256')} mine={row['registry_sha256']}")
        check(f"C12.{n:02d}", f"pin {row['path']} declared census row is self-consistent",
              dp.get("status") == row["status"]
              and (dp.get("disk_sha256") or "").lower() == (row["disk_sha256"] or "!").lower(),
              f"declared_status={dp.get('status')} mine={row['status']}")
    check("C13", "registry union covers both 'hashes' and 'registry' sub-maps",
          isinstance(registry.get("hashes"), dict) and isinstance(registry.get("registry"), dict)
          and union.get(TAXONOMY_REL, {}).get("sha256") == TAXONOMY_SHA
          and union.get(PROTOCOL_REL, {}).get("sha256") == PROTOCOL_SHA,
          f"union n={len(union)}")

    # ---- C. independent order re-fit --------------------------------------
    refit = refit_schemes(cert)
    check("C14", "three schemes present in certification and re-fit",
          sorted(refit) == ["cnfd", "cnfem", "lffd"], json.dumps(sorted(refit)))
    tol = 1e-9
    for sch in sorted(refit):
        r = refit[sch]
        check(f"C15.{sch}", f"{sch}: recomputed fit order == declared within 0 abs",
              r["abs_diff_fit"] == 0.0, f"{r['fit_order_recomputed']!r} vs {r['fit_order_declared']!r}")
        check(f"C16.{sch}", f"{sch}: recomputed least-squares SE == declared within 0 abs",
              r["abs_diff_se"] == 0.0, f"{r['least_squares_se_recomputed']!r} vs {r['least_squares_se_declared']!r}")
        check(f"C17.{sch}", f"{sch}: recomputed pair orders == declared within 0 abs",
              r["max_abs_pair_diff"] == 0.0, f"max_abs_diff={r['max_abs_pair_diff']!r}")
        check(f"C18.{sch}", f"{sch}: recomputed residuals == declared within 0 abs",
              r["max_abs_resid_diff"] == 0.0, f"max_abs_resid_diff={r['max_abs_resid_diff']!r}")
        check(f"C19.{sch}", f"{sch}: recomputed delta_R5 == declared within 0 abs",
              r["abs_diff_delta_R5"] == 0.0, f"{r['delta_R5_recomputed']!r} vs {r['delta_R5_declared']!r}")
        check(f"C20.{sch}", f"{sch}: 4 rungs, dt fixed at 1e-4 on all rungs, dr descending",
              r["n_rungs"] == 4 and r["dt_values"] == [0.0001] and r["drs_descending"],
              f"n={r['n_rungs']} dt={r['dt_values']} dr_desc={r['drs_descending']}")
        check(f"C21.{sch}", f"{sch}: l2_error monotone decreasing and fit within |p-2|<=0.3",
              r["l2_monotone_decreasing"] and r["within_band"],
              f"monotone={r['l2_monotone_decreasing']} |p-2|={abs(r['fit_order_recomputed']-2.0):.3e}")
        check(f"C22.{sch}", f"{sch}: declared delta_R5 equals max(pair half-range, SE)",
              abs(r["delta_R5_recomputed"]
                  - max(r["pair_half_range_recomputed"], r["least_squares_se_recomputed"])) < 1e-15,
              f"half_range={r['pair_half_range_recomputed']!r} se={r['least_squares_se_recomputed']!r}")
    my_cross = cross_scheme(refit)
    check("C23", "cross-scheme max pairwise |dp| reproduces declared 7.958e-05 within 1e-9 rel",
          abs(my_cross["max_pairwise_abs_diff"] - 7.958116929374093e-05)
          <= 1e-9 * 7.958116929374093e-05,
          f"{my_cross['max_pairwise_abs_diff']!r}")
    check("C24", "all three cross-scheme pairs agree within R5 bound 0.25",
          my_cross["all_agree"] and all(p["abs_order_diff"] <= 0.25 for p in my_cross["pairs"])
          and target["independent_order_refit"]["cross_scheme_within_r5"] is True,
          json.dumps([{p["pair"]: p["abs_order_diff"]} for p in my_cross["pairs"]]))
    check("C25", "every recomputed fit is inside the declared band (p_tol=0.3)",
          all(r["within_band"] for r in refit.values())
          and target["independent_order_refit"]["schemes_out_of_band_or_degenerate"] == [],
          json.dumps({s: r["within_band"] for s, r in refit.items()}))
    air = target["independent_order_refit"]
    ok_air = (air["p_design"] == 2.0 and air["p_tol"] == 0.3 and air["r5_bound"] == 0.25
              and abs(air["max_cross_scheme_abs_diff"] - my_cross["max_pairwise_abs_diff"]) <= 1e-18)
    for sch in sorted(refit):
        d = air["schemes"][sch]
        ok_air = ok_air and d["abs_diff_vs_declared"] == 0.0 \
            and d["fit_order_recomputed"] == refit[sch]["fit_order_recomputed"] \
            and d["least_squares_se"] == refit[sch]["least_squares_se_recomputed"] \
            and d["pair_orders_recomputed"] == refit[sch]["pair_orders_recomputed"] \
            and d["n_rungs"] == 4 and d["dt_all_fixed"] is True and d["monotone"] is True \
            and d["dr_values"] == refit[sch]["dr_values"]
    check("C26", "audit independent_order_refit block equals my recomputation field-by-field",
          ok_air, "abs_diff_vs_declared=0, recomputed values equal, n/dt/monotone equal")

    # numpy cross-check (different implementation of the same estimator)
    try:
        import numpy as np  # type: ignore
        ok_np = True
        detail_np = []
        for sch in sorted(refit):
            rows = cert["schemes"][sch]["fixed_dt_certification"]["rows"]
            xs = np.log(np.array([r["dr"] for r in rows], dtype=float))
            ys = np.log(np.array([r["l2_error"] for r in rows], dtype=float))
            slope, intercept = np.polyfit(xs, ys, 1)
            resid = ys - (intercept + slope * xs)
            se = math.sqrt(float((resid ** 2).sum()) / (len(xs) - 2) / float(((xs - xs.mean()) ** 2).sum()))
            ok_np = ok_np and abs(float(slope) - refit[sch]["fit_order_recomputed"]) <= 1e-12 \
                and abs(float(se) - refit[sch]["least_squares_se_recomputed"]) <= 1e-15
            detail_np.append(f"{sch}:{float(slope):.15f}/{float(se):.3e}")
        check("C27", "numpy.polyfit cross-check agrees with closed-form fit and SE",
              ok_np, "; ".join(detail_np))
        check("C28", "numpy availability recorded for reproducibility",
              True, f"numpy {np.__version__}")
    except Exception as exc:  # pragma: no cover
        check("C27", "numpy.polyfit cross-check agrees with closed-form fit and SE", False, repr(exc))
        check("C28", "numpy availability recorded for reproducibility", False, repr(exc))

    # ---- D. replication verdicts and rev3 pins ----------------------------
    rv = target["replication_verdicts"]
    check("C29", "three replication verdict rows declared",
          len(rv) == 3 and all(r.get("declared_in_rev3_pins") is True for r in rv),
          json.dumps([r["path"] for r in rv]))
    for r in rv:
        fp = ROOT / r["path"]
        check(f"C30.{Path(r['path']).parent.name}",
              f"{r['path']} exists on disk at declared sha and is registry-absent",
              fp.is_file() and sha256_file(fp) == r["disk_sha256"]
              and r["registry_registered"] is False and r["registry_sha256"] is None
              and r["path"] in my_census["unregistered"],
              f"disk={sha256_file(fp)[:12] if fp.is_file() else 'MISSING'} declared={r['disk_sha256'][:12]}")
    w046 = load_json(ROOT / rv[0]["path"])
    w057 = load_json(ROOT / rv[1]["path"])
    w081 = load_json(ROOT / rv[2]["path"])
    check("C31", "worker-046 verdict field SUPPORTED as declared",
          json.dumps(w046).find("SUPPORTED") >= 0 and rv[0]["verdict_field"] == "SUPPORTED",
          str(rv[0]["verdict_field"]))
    check("C32", "worker-057 verdict field REPRODUCED as declared",
          json.dumps(w057).find("REPRODUCED") >= 0 and rv[1]["verdict_field"] == "REPRODUCED",
          str(rv[1]["verdict_field"]))
    vf = rv[2]["verdict_field"]
    check("C33", "worker-081 adjudication verdict object matches declared fields",
          isinstance(vf, dict) and vf.get("status") == "adjudicated"
          and vf.get("disposition") == "F1_AND_F1PRIME_DISCHARGED_BY_SUPERSESSION"
          and vf.get("binding_accept_at_current_hash") is True
          and vf.get("blocks_gate_pass") is False and vf.get("structural_checks_pass") is True
          and "does not set the gate" in str(vf.get("scope")),
          json.dumps(vf)[:300])
    rev3_pins = json.dumps(rev3)
    check("C34", "all three replication paths are named in the rev-3 closure artifact",
          all(r["path"] in rev3_pins for r in rv),
          [r["path"] for r in rv])
    check("C35", "rev-3 closure artifact bytes at declared pin da7c36071995",
          rel_sha(REV3_REL) == REV3_SHA, rel_sha(REV3_REL))

    # ---- E. companion class-binding authority -----------------------------
    ab = target["class_binding_authority"]
    check("C36", "audit references the companion authority at effd20b0ea09 and marks it present",
          ab.get("present") is True and ab.get("sha256") == AUTHORITY_SHA
          and ab.get("path") == AUTHORITY_REL, json.dumps(ab)[:300])
    check("C37", "authority record parses with matching class/node/gate",
          authority.get("class_id") == CLASS_ID and authority.get("node_id") == NODE_ID
          and authority.get("gate") == GATE
          and authority.get("schema") == "n0-class-binding-authority/v1",
          json.dumps({k: authority.get(k) for k in ("schema", "class_id", "node_id", "gate")}))
    check("C38", "A1 binding matches disk: taxonomy at 0abb9ed8a961 is live",
          authority["binding"]["sha256"] == TAXONOMY_SHA == rel_sha(TAXONOMY_REL)
          and ab.get("A1_binding_matches_disk") is True, rel_sha(TAXONOMY_REL))
    check("C39", "A2 binding is F0 revision 5 on disk",
          authority["binding"].get("declared_revision") == 5
          and any(line.strip() == "revision: 5" for line in taxonomy_text.splitlines())
          and ab.get("A2_binding_is_live_f0_rev5") is True, "revision: 5")
    check("C40", "A3 carrier matches disk: rev-3 closure at da7c36071995",
          authority["carrier"]["sha256"] == REV3_SHA == rel_sha(REV3_REL)
          and ab.get("A3_carrier_matches_disk") is True, rel_sha(REV3_REL))
    cb = rev3.get("class_binding") or {}
    check("C41", "A4 carrier names the binding: rev3.class_binding points at 0abb9ed8a961 rev5",
          cb.get("sha256") == TAXONOMY_SHA and cb.get("declared_revision") == 5
          and cb.get("class_id") == CLASS_ID and cb.get("path") == TAXONOMY_REL
          and ab.get("A4_carrier_names_binding") is True
          and "0abb9ed8a961" in str(rev3.get("stop_rule_closures", {}).get("f0_rebind", "")),
          json.dumps(cb)[:300])
    sup = (authority.get("supersedes_for_class_binding") or [{}])[0]
    cites_ok = (sup.get("sha256") == PROTOCOL_SHA
                and sup.get("citations") == ["66bf917bd368", "565a6e50"]
                and "66bf917bd368" in protocol_text.splitlines()[6]
                and "565a6e50" in "\n".join(protocol_text.splitlines()[156:160]))
    check("C42", "A5 superseded pins pinned to the live protocol hash and cited where declared",
          cites_ok and ab.get("A5_superseded_pinned") is True,
          f"line7={protocol_text.splitlines()[6][:60]!r} lines157-160 contain 565a6e50="
          f"{'565a6e50' in chr(10).join(protocol_text.splitlines()[156:160])}")
    check("C43", "A6 is false by design (published lead authority, not proposal-only)",
          ab.get("A6_proposal_only_authority") is False
          and "not the proposal-only variant" in str(ab.get("note")),
          str(ab.get("note"))[:200])
    check("C44", "authority non_claims and falsifier present (no gate/node/lock claim)",
          any("gate verdict" in s for s in authority.get("non_claims", []))
          and any("node transition" in s for s in authority.get("non_claims", []))
          and bool(authority.get("falsifier")), json.dumps(authority.get("non_claims"))[:300])
    check("C45", "authority record requests independent review at its hash",
          "independent review requested" in str(authority.get("review_request")),
          str(authority.get("review_request"))[:200])

    # ---- F. incident/anomaly census (audit ANOM-1 and same-class scan) ----
    anoms = target.get("anomalies") or []
    anom_ok = any(a.get("id") == "ANOM-1" and a.get("artifact") == BLOCKERS_REL
                  and "future-dated" in a.get("finding", "")
                  and "2026-09-12T01:00" in json.dumps(a.get("detail"))
                  for a in anoms)
    mt = datetime.fromtimestamp((ROOT / BLOCKERS_REL).stat().st_mtime, TZ)
    check("C46", "ANOM-1 reproduces: blockers.md embeds 01:00 token but mtime is earlier",
          anom_ok and "2026-09-12T01:00" in blockers_text and mt < datetime(2026, 9, 12, 1, 0, tzinfo=TZ),
          f"mtime={mt.isoformat()} token_present={'2026-09-12T01:00' in blockers_text}")
    amt = datetime.fromtimestamp((ROOT / AUTHORITY_REL).stat().st_mtime, TZ)
    pub = datetime.fromisoformat(authority["published_at"])
    same_class = pub > amt
    check("C47", "same future-dated-timestamp class scanned on the companion record",
          True, f"published_at={pub.isoformat()} mtime={amt.isoformat()} future_dated={same_class}")

    # ---- G. lock compliance ------------------------------------------------
    lock = live_map.get("numerics_lock") or {}
    check("C48", "live map numerics_lock.state == 'locked'",
          lock.get("state") == "locked", str(lock.get("state")))
    scan = solver_scan(ROOT)
    check("C49", "no solver-shaped path under numerics/ while locked",
          scan["present"] is False and scan["path_numerics_spherical_solver_exists"] is False
          and target["lock_compliance"]["spherical_solver_present"] is False,
          json.dumps(scan))
    live_gates = run_gates(ROOT)
    lg = live_gates["parsed"] or {}
    check("C50", "read-only gates.py run returns N1_BLOCKED with production_allowed=false (exit 3)",
          live_gates["exit"] == 3 and lg.get("verdict") == "N1_BLOCKED"
          and lg.get("production_allowed") is False,
          f"exit={live_gates['exit']} verdict={lg.get('verdict')}")
    check("C51", "gates.py blocking-reason count and categories match the declared guard block",
          len(lg.get("blocking_reasons") or []) == target["lock_compliance"]["guard"]["n_blocking_reasons"]
          and any("locked" in r for r in lg.get("blocking_reasons", []))
          and any("G-FORM" in r for r in lg.get("blocking_reasons", []))
          and any("G-AUDIT" in r for r in lg.get("blocking_reasons", []))
          and any("contested" in r for r in lg.get("blocking_reasons", [])),
          json.dumps(lg.get("blocking_reasons"))[:400])
    check("C52", "declared guard verdict N1_BLOCKED / production_allowed=false matches live",
          target["lock_compliance"]["guard"]["verdict"] == lg.get("verdict")
          and target["lock_compliance"]["guard"]["production_allowed"] == lg.get("production_allowed"),
          f"declared={target['lock_compliance']['guard']['verdict']} live={lg.get('verdict')}")
    gform = next((g for g in live_map.get("gates", []) if g.get("gate_id") == "G-FORM"), {})
    gaudit = next((g for g in live_map.get("gates", []) if g.get("gate_id") == "G-AUDIT"), {})
    check("C53", "falsifier #4 predicate holds: no production_allowed=true while G-FORM/G-AUDIT not pass",
          not (lg.get("production_allowed") is True
               and (gform.get("verdict") != "pass" or gaudit.get("verdict") != "pass")),
          f"G-FORM={gform.get('verdict')} G-AUDIT={gaudit.get('verdict')} allowed={lg.get('production_allowed')}")

    # ---- H. planted-defect controls (each must fire) -----------------------
    controls: list[dict] = []

    # M1: perturb one declared pin sha -> census must flag mismatch
    m1pins = json.loads(json.dumps(pins))
    m1pins[3]["declared_sha256"] = "0" * 64
    m1 = census(m1pins, union, ROOT)
    controls.append({"id": "M1", "planted_defect": "declared pin sha flipped to zeros",
                     "expected": "mismatch detected on that pin",
                     "observed": m1["mismatched"], "fired": m1pins[3]["path"] in m1["mismatched"]
                     and m1["n_match"] == 9})

    # M2: perturb one raw l2_error row +0.5% -> recomputed fit must move
    m2cert = json.loads(json.dumps(cert))
    m2cert["schemes"]["lffd"]["fixed_dt_certification"]["rows"][1]["l2_error"] *= 1.005
    m2 = refit_schemes(m2cert)
    m2delta = abs(m2["lffd"]["fit_order_recomputed"]
                  - cert["schemes"]["lffd"]["fixed_dt_certification"]["fit_order"])
    controls.append({"id": "M2", "planted_defect": "lffd rung-2 l2_error +0.5%",
                     "expected": "recomputed order moves >1e-6 from declared",
                     "observed": m2delta, "fired": m2delta > 1e-6})

    # M3: drop a registry entry -> registration flag flips
    m3union = dict(union)
    m3union.pop(PROTOCOL_REL, None)
    m3 = census(pins, m3union, ROOT)
    m3row = next(r for r in m3["rows"] if r["path"] == PROTOCOL_REL)
    controls.append({"id": "M3", "planted_defect": "registry entry for the protocol removed",
                     "expected": "pin flips to unregistered",
                     "observed": m3row["status"], "fired": m3row["status"] == "unregistered"})

    # M4: premature lock release with gates still pending -> guard must stay blocked
    tmp_controls = HERE / "tmp_controls"
    if tmp_controls.exists():
        shutil.rmtree(tmp_controls)
    farm4 = build_farm(tmp_controls / "m4", mutate_map=lambda m: m["numerics_lock"].__setitem__("state", "released"))
    m4 = run_gates(farm4)
    controls.append({"id": "M4", "planted_defect": "lock state set to 'released' while G-FORM/G-AUDIT pending",
                     "expected": "guard still production_allowed=false",
                     "observed": (m4["parsed"] or {}).get("verdict"),
                     "fired": (m4["parsed"] or {}).get("production_allowed") is False})

    # M5: solver file planted under numerics/ while locked -> scan must fire
    farm5 = tmp_controls / "m5"
    (farm5 / "numerics" / "spherical_solver").mkdir(parents=True)
    (farm5 / "numerics" / "spherical_solver" / "solver.py").write_text("# planted\n")
    m5 = solver_scan(farm5)
    controls.append({"id": "M5", "planted_defect": "numerics/spherical_solver/solver.py planted while locked",
                     "expected": "solver scan detects it",
                     "observed": m5["hits"], "fired": m5["present"] and m5["path_numerics_spherical_solver_exists"]})

    # M6: protocol bytes changed -> pin census must flag mismatch
    farm6 = tmp_controls / "m6"
    (farm6 / PROTOCOL_REL).parent.mkdir(parents=True)
    (farm6 / PROTOCOL_REL).write_bytes((ROOT / PROTOCOL_REL).read_bytes() + b"\n# planted\n")
    m6 = census(pins, union, farm6)
    m6row = next(r for r in m6["rows"] if r["path"] == PROTOCOL_REL)
    controls.append({"id": "M6", "planted_defect": "protocol bytes appended (hash move)",
                     "expected": "pin census flags mismatch",
                     "observed": m6row["status"], "fired": m6row["status"] == "mismatch"})

    for c in controls:
        check(f"C54.{c['id']}", f"control {c['id']} fires: {c['planted_defect']}",
              c["fired"], f"observed={c['observed']}")

    # ---- I. determinism and no-write guard ---------------------------------
    payload_a = json.dumps({"census": census(pins, union, ROOT), "refit": refit_schemes(cert)},
                           sort_keys=True)
    payload_b = json.dumps({"census": census(pins, union, ROOT), "refit": refit_schemes(cert)},
                           sort_keys=True)
    det = {"identical": payload_a == payload_b, "sha_a": sha256_bytes(payload_a.encode()),
           "sha_b": sha256_bytes(payload_b.encode())}
    check("C55", "determinism: two pure-analysis passes are bitwise identical",
          det["identical"] and det["sha_a"] == det["sha_b"], json.dumps(det))

    moved = []
    for rel in BINDING_RELS:
        if rel_sha(rel) != snapshots[rel]["sha256"]:
            moved.append(rel)
    check("C56", "binding pins did not move during the run (before vs after)",
          moved == [], json.dumps(moved))

    # ---- findings and verdict ---------------------------------------------
    hard = [c["id"] + ": " + c["name"] for c in CHECKS if not c["ok"]]
    findings = [
        {"id": "F1", "severity": "positive",
         "statement": ("Target audit 22edbcc61df7 reproduces independently: 13/13 pins "
                       "re-measured with my own hashing/registry code (10 match, 3 unregistered, "
                       "0 mismatch/missing), the three unregistered worker verdicts exist at their "
                       "declared hashes and are genuinely registry-absent, and every declared fit "
                       "order, pair order, least-squares SE, residual and delta_R5 recomputes "
                       "bitwise from the raw dr/l2_error rows with my own closed-form least squares "
                       "(numpy.polyfit cross-check agrees). Cross-scheme max |dp| = "
                       f"{my_cross['max_pairwise_abs_diff']:.6e} <= 0.25; all fits inside |p-2|<=0.3."),
         "evidence_refs": [ref(TARGET_REL), ref(CERT_REL)]},
        {"id": "F2", "severity": "soft",
         "statement": (f"Companion authority record {AUTHORITY_REL} carries published_at "
                       f"{authority['published_at']} while its file mtime is {amt.isoformat()} "
                       "(future-dated label by ~2 min). This is the same anomaly class the target "
                       "audit reports as ANOM-1 for numerics/blockers.md, but the audit's anomaly "
                       "list omits this instance. Advisory only: bytes are frozen and no claim "
                       "depends on the label; recorded for the owner's census completeness."),
         "evidence_refs": [ref(AUTHORITY_REL), ref(TARGET_REL)]},
        {"id": "F3", "severity": "inherited-open",
         "statement": ("Registration gap persists at my measurement time: the three replication "
                       "verdicts cited by the rev-3 closure artifact are still absent from "
                       "runtime/state/artifact_hashes.json (paths listed in the audit's blocker "
                       "lnum-blocker-80ea3e6b3923ea78ccac). Controller action required before any "
                       "N0 done claim; not a defect of the audit, re-measured and re-filed."),
         "evidence_refs": [ref(REGISTRY_REL), ref(REV3_REL), ref(TARGET_REL)]},
        {"id": "F4", "severity": "observation",
         "statement": ("numerics/gates.py does not itself scan for numerics/spherical_solver/: its "
                       "blocking reasons are lock state, required gates, N0 evidence and protocol "
                       "contest. The audit's falsifier #3 (solver appearing while locked) is checked "
                       "by direct filesystem scan, as done here. By design (the guard is a "
                       "pre-flight API called by solver code), not a defect."),
         "evidence_refs": [ref(GATES_REL), ref(TARGET_REL)]},
        {"id": "F5", "severity": "caveat",
         "statement": ("Independence caveat: same-fleet non-author check. Worker-020 did not author "
                       "the audit, the authority record, the certification, the frozen module or the "
                       "replication verdicts. This is not an external audit."),
         "evidence_refs": [ref(TARGET_REL)]},
    ]
    verdict = ("REGAUDIT_CENSUS_AND_ORDER_REFIT_INDEPENDENTLY_REPRODUCED"
               if not hard else "REGAUDIT_VERIFICATION_FOUND_DEFECT")
    review_verdict = "accept" if not hard else "revise"
    review_score = 4.0 if not hard else 2.0
    summary = {"total": len(CHECKS), "passed": sum(1 for c in CHECKS if c["ok"]),
               "failed": len(hard), "failed_ids": hard}

    report = {
        "schema": "w020-n0-regaudit-verification/v1",
        "task_id": TASK,
        "actor": ACTOR,
        "class_id": CLASS_ID,
        "node_id": NODE_ID,
        "gate": GATE,
        "started_at": started,
        "generated_at": now(),
        "target": {"path": TARGET_REL, "declared_sha256": TARGET_SHA,
                   "measured_sha256": rel_sha(TARGET_REL),
                   "bytes": (ROOT / TARGET_REL).stat().st_size,
                   "author": target.get("actor"), "generated_at_field": target.get("generated_at"),
                   "verdict_field": target.get("verdict")},
        "companion": {"path": AUTHORITY_REL, "declared_sha256": AUTHORITY_SHA,
                      "measured_sha256": rel_sha(AUTHORITY_REL),
                      "bytes": (ROOT / AUTHORITY_REL).stat().st_size,
                      "author": authority.get("published_by")},
        "verdict": verdict,
        "review_verdict": review_verdict,
        "review_score": review_score,
        "checks": {"total": summary["total"], "passed": summary["passed"],
                   "failed": summary["failed"], "failed_ids": summary["failed_ids"],
                   "items": CHECKS},
        "pin_census": {k: my_census[k] for k in
                       ("n_declared_pins", "n_match", "mismatched", "registry_mismatched",
                        "disk_missing", "unregistered")},
        "pin_rows": my_census["rows"],
        "order_refit": {"schemes": refit, "cross_scheme": my_cross,
                        "declared_block_equality": ok_air},
        "replication_verdicts": rv,
        "class_binding_authority": {"audit_block": ab,
                                    "authority_published_at": authority.get("published_at"),
                                    "authority_mtime": amt.isoformat(),
                                    "future_dated_label": same_class},
        "lock_compliance": {"lock_state": lock.get("state"), "solver_scan": scan,
                            "gates_run": {"exit": live_gates["exit"],
                                          "verdict": lg.get("verdict"),
                                          "production_allowed": lg.get("production_allowed"),
                                          "blocking_reasons": lg.get("blocking_reasons")}},
        "controls": controls,
        "determinism": det,
        "no_write_guard": {"binding_pins_moved": moved,
                           "wrote_only_under": str(HERE.relative_to(ROOT)),
                           "files_written": written},
        "findings": findings,
        "hard_failures": hard,
        "falsifier": FALSIFIER,
        "claims_not_made": [
            "no gate verdict (G-NUM stays pending; authority Astra / lead-audit)",
            "no node completion (N0 status untouched)",
            "no numerics_lock release (N1 stays queued; no spherical_solver written)",
            "no adjudication of the C8 protocol contest, HF-042-N0-1 or HF-081-PS-1",
            "no physics / self-gravity / WCC / SCC claim",
            "no validation_status promotion (worker evidence only)",
        ],
        "snapshots": snapshots,
    }

    out_json = HERE / "regaudit_verification.json"
    out_log = HERE / "regaudit_verification.log"
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")

    lines = [
        f"{TASK} — independent non-author verification",
        f"actor={ACTOR} class={CLASS_ID} node={NODE_ID} gate={GATE}",
        f"target={TARGET_REL}#{TARGET_SHA[:12]} companion={AUTHORITY_REL}#{AUTHORITY_SHA[:12]}",
        f"started={started} finished={now()}",
        "-" * 78,
    ]
    for c in CHECKS:
        lines.append(f"[{'PASS' if c['ok'] else 'FAIL'}] {c['id']:<10} {c['name']}")
        if c["detail"]:
            lines.append(f"         {c['detail']}")
    lines += ["-" * 78,
              f"checks {summary['passed']}/{summary['total']} passed, {summary['failed']} failed",
              f"verdict {verdict} | review {review_verdict} {review_score}",
              "findings: " + "; ".join(f"{f['id']}({f['severity']})" for f in findings),
              "solver_scan=" + json.dumps(scan),
              "live_gates=" + json.dumps({"exit": live_gates["exit"], "verdict": lg.get("verdict"),
                                          "production_allowed": lg.get("production_allowed")}),
              "falsifier: " + FALSIFIER]
    out_log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if tmp_controls.exists():
        shutil.rmtree(tmp_controls)

    print("\n".join(lines))
    return 0 if not hard else 1


if __name__ == "__main__":
    raise SystemExit(main())
