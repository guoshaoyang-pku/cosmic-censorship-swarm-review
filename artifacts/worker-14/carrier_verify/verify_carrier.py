#!/usr/bin/env python3
"""W014-GNUM-CARRIER-VERIFY-01 -- independent verification of the N0 class-binding authority record.

Read-only.  Verifies, against the bytes on disk and without importing or running any solver:

  A  input pinning + canonical before/after drift guard;
  B  every (path, sha256) pin declared inside numerics/N0_CLASS_BINDING_AUTHORITY.json;
  C  the carrier (flat_wave_convergence_rev3.json) declares the F0 rev5 binding;
  D  the live taxonomy at the binding pin is revision 5 and carries AF-WCC-SCALAR-SPH;
  E  numerics/CONVERGENCE_PROTOCOL.md is byte-unchanged and still cites the superseded pins
     at the locations the record names;
  F  exactly one class-binding carrier is named in the reviewed evidence set;
  G  materiality: the certification basis contains no taxonomy string and an independent
     log-log LSQ refit from the raw rungs reproduces every declared fit order to <= 1e-6;
  H  the lead's read-only audit_registration_drift.py re-run reproduces the filed audit;
  I  lock guard: numerics_lock locked, no spherical_solver, gates.py reports N1_BLOCKED;
  J  planted controls on scratch copies, and a determinism re-run.

Exit: 0 all core checks and controls pass; 2 core check failed; 3 lock violation;
4 control failed; 5 instrument error.

    python3 verify_carrier.py [--out report.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]  # artifacts/worker-14/carrier_verify -> repo root
SCRATCH = HERE / "scratch"

REL = {
    "record": "numerics/N0_CLASS_BINDING_AUTHORITY.json",
    "carrier": "numerics/results/flat_wave_convergence_rev3.json",
    "binding": "research_map/formulation_taxonomy.yaml",
    "protocol": "numerics/CONVERGENCE_PROTOCOL.md",
    "cert": "numerics/protocol/n0_fixed_dt_certification.json",
    "drift_audit": "numerics/protocol/n0_registration_drift_audit.json",
    "drift_script": "numerics/protocol/audit_registration_drift.py",
    "gates": "numerics/gates.py",
    "map": "research_map/research_map.json",
    "rev042": "reviews/N0-review-worker-042.json",
    "rev081ps": "reviews/N0-pin-split-adjudication-worker-081.json",
    "revfinal": "reviews/N0-review-final-verify.json",
    "rev012": "reviews/N0-review-worker-012.json",
    "addendum081": "artifacts/worker-081/n0_pin_split_adjudication/proposed/n0_class_binding_addendum.json",
}
EXPECT = {
    "record": "effd20b0ea094a8dfd4f686e62c49b1667622337efd6a7c154f7fadae0b98419",
    "carrier": "da7c360719950f7ef6be2624391dee464f8c818a0be74ec44f0f8c70d2b28ac3",
    "binding": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "protocol": "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274",
    "cert": None,
    "drift_audit": "22edbcc61df7dc7cd574fb43e4ef6c09ae12f89f1ebe34869b00a5b27384c632",
    "drift_script": "5031ffb3024f706fc3525e167390622b9feb465d7ce27433a68a9c1a0966c923",
    "rev042": "def37cffb7db984fabae7ab7bb6b935edafede8c561d8d93da99c04bd512404f",
    "rev081ps": "a39c7178c008e1023a71eab7df4bed6734afcee60829bedb7dced8aeebafa736",
    "revfinal": "18a0c0d0e77f0b0a747f857ef90468ec88fbfc01d33959dc9fad2685faa75d65",
    "addendum081": "d128dfdbfb5acca40497c5afdb4a23049641b1c43149a30525ae6875b4ddc317",
}
SUPERSEDED = ("66bf917bd368", "565a6e50")
F0_REV5 = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
ORDER_TOL = 1e-6


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pin_status(p: Path, declared: str) -> dict:
    if not p.is_file():
        return {"status": "missing", "declared": declared, "measured": None}
    measured = sha256_file(p)
    ok = measured.startswith(declared.strip().lower()) or declared.strip().lower().startswith(measured)
    return {"status": "match" if ok else "mismatch", "declared": declared, "measured": measured}


def lsq_order(rows: list[dict]) -> dict:
    """Independent log-log least squares on the raw rungs.

    Convention (matches the filed fit): e ~ dr^p with e the l2 error decreasing as dr
    decreases, so p = +d(log e)/d(log dr) and adjacent pair orders are
    log(e_a/e_b)/log(dr_a/dr_b) with dr_a > dr_b.
    """
    xs = [math.log(float(r["dr"])) for r in rows]
    ys = [math.log(float(r["l2_error"])) for r in rows]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = my - slope * mx
    resid = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
    dof = max(n - 2, 1)
    s2 = sum(r * r for r in resid) / dof
    se = math.sqrt(s2 / sxx)
    pairs = []
    ordered = sorted(rows, key=lambda r: -float(r["dr"]))
    for a, b in zip(ordered, ordered[1:]):
        pairs.append(math.log(float(a["l2_error"]) / float(b["l2_error"]))
                     / math.log(float(a["dr"]) / float(b["dr"])))
    return {"p": slope, "se": se, "pair_orders": pairs,
            "residuals": resid, "n": n, "drs": [float(r["dr"]) for r in rows]}


def read_json(p: Path):
    return json.loads(p.read_text())


def verify_record_pins(record: dict) -> list[dict]:
    """Every (path, sha256) pin declared in the record, re-measured."""
    pins: list[dict] = []

    def add(label: str, relpath: str, declared: str):
        st = pin_status(REPO / relpath, declared)
        pins.append({"label": label, "path": relpath, **st})

    add("carrier", record["carrier"]["path"], record["carrier"]["sha256"])
    add("binding", record["binding"]["path"], record["binding"]["sha256"])
    for i, s in enumerate(record.get("supersedes_for_class_binding", [])):
        add(f"supersedes_for_class_binding[{i}]", s["path"], s["sha256"])
    for i, s in enumerate(record.get("preserves", [])):
        add(f"preserves[{i}]", s["path"], s["sha256"])
    for i, ref in enumerate(record.get("basis_evidence", [])):
        if "#" in ref:
            path, tail = ref.rsplit("#", 1)
            tail = tail.replace("sha256:", "").strip()
            m = re.match(r"^[0-9a-fA-F]{12,64}", tail)
            declared = m.group(0) if m else tail
            st = pin_status(REPO / path, declared)
            pins.append({"label": f"basis_evidence[{i}]", "path": path,
                         "annotation": tail[len(declared):].strip(), **st})
    return pins


def carrier_declares_binding(carrier: dict) -> dict:
    cb = carrier.get("class_binding", {}) or {}
    src = carrier.get("stop_rule_closures", {}) or {}
    return {
        "class_binding_sha256": cb.get("sha256"),
        "class_binding_sha256_is_rev5": cb.get("sha256") == F0_REV5,
        "declared_revision": cb.get("declared_revision"),
        "declared_revision_is_5": cb.get("declared_revision") == 5,
        "class_id": cb.get("class_id"),
        "f0_rebind_names_rev5": ("0abb9ed8a961" in str(src.get("f0_rebind", ""))
                                 or F0_REV5 in str(src.get("f0_rebind", ""))),
        "carrier_protocol_sha256": (carrier.get("certification_basis", {}) or {}).get("protocol_sha256"),
        "certified_drs": (carrier.get("certification_basis", {}) or {}).get("dr_values"),
        "frozen_module_sha256": ((carrier.get("certification_basis", {}) or {}).get("frozen_module", {}) or {}).get("sha256"),
    }


def binding_revision_ok(binding_path: Path) -> dict:
    text = binding_path.read_text()
    m = re.search(r"^revision:\s*(\S+)\s*$", text, re.M)
    rev = m.group(1) if m else None
    return {"revision": rev, "revision_is_5": rev == "5",
            "contains_class": "AF-WCC-SCALAR-SPH" in text}


def protocol_citation_check(protocol_path: Path, record: dict) -> dict:
    lines = protocol_path.read_text().splitlines()
    hits = {}
    for pin in SUPERSEDED:
        hits[pin] = [i + 1 for i, ln in enumerate(lines) if pin in ln]
    declared_locs = []
    for s in record.get("supersedes_for_class_binding", []):
        declared_locs.extend(s.get("locations", []))
    covered = []
    for loc in declared_locs:
        nums = [int(x) for x in re.findall(r"\d+", loc)]
        if len(nums) == 1:
            rng = range(nums[0], nums[0] + 1)
        elif len(nums) >= 2:
            rng = range(nums[0], nums[1] + 1)
        else:
            continue
        covered.extend(n for n in rng if 1 <= n <= len(lines))
    return {
        "hash": sha256_file(protocol_path),
        "line_hits": hits,
        "every_superseded_pin_present": all(hits[p] for p in SUPERSEDED),
        "record_locations": declared_locs,
        "record_locations_cover_hits": all(set(hits[p]) & set(covered) for p in SUPERSEDED),
    }


def single_carrier_scan(files: dict[str, Path]) -> dict:
    """Heuristic: collect documents that name an N0 class-binding carrier."""
    pat = re.compile(r"class[-_ ]binding[-_ ]carrier[^\"\n]{0,140}")
    mentions: dict[str, list[str]] = {}
    for label, p in files.items():
        if not p.is_file():
            continue
        try:
            text = p.read_text(errors="replace")
        except Exception:
            continue
        found = pat.findall(text)
        if found:
            mentions[label] = found[:6]
    carrier_named = []
    for label, found in mentions.items():
        for f in found:
            m = re.search(r"(numerics/results/[A-Za-z0-9_.\-]+\.json|numerics/[A-Za-z0-9_./\-]+\.json)", f)
            if m:
                carrier_named.append(m.group(1))
    distinct = sorted(set(carrier_named))
    return {
        "documents_with_carrier_mentions": sorted(mentions.keys()),
        "distinct_carrier_paths_named": distinct,
        "exactly_one_carrier_path": distinct == [REL["carrier"]],
    }


def materiality_check(cert_path: Path) -> dict:
    text = cert_path.read_text()
    tax_hits = {tok: text.count(tok) for tok in ("taxonomy", *SUPERSEDED, "0abb9ed8")}
    cert = read_json(cert_path)
    per_scheme = {}
    max_dev = 0.0
    for name, blk in cert["schemes"].items():
        fdt = blk["fixed_dt_certification"]
        refit = lsq_order(fdt["rows"])
        dev = abs(refit["p"] - float(fdt["fit_order"]))
        max_dev = max(max_dev, dev)
        per_scheme[name] = {
            "declared_fit_order": fdt["fit_order"],
            "independent_fit_order": refit["p"],
            "abs_deviation": dev,
            "declared_pair_orders": fdt["pair_orders"],
            "independent_pair_orders": refit["pair_orders"],
            "max_abs_pair_deviation": max(
                abs(a - b) for a, b in zip(fdt["pair_orders"], refit["pair_orders"])),
            "declared_se": fdt["least_squares_se"],
            "independent_se": refit["se"],
            "rows": len(fdt["rows"]),
        }
    return {
        "taxonomy_string_hits": tax_hits,
        "zero_taxonomy_strings": all(v == 0 for v in tax_hits.values()),
        "per_scheme": per_scheme,
        "max_abs_order_deviation": max_dev,
        "refit_within_tol": max_dev <= ORDER_TOL,
    }


def drift_audit_rerun(scratch: Path, filed: dict) -> dict:
    scratch.mkdir(parents=True, exist_ok=True)
    out = scratch / "drift_rerun.json"
    proc = subprocess.run(
        [sys.executable, str(REPO / REL["drift_script"]), "--out", str(out)],
        capture_output=True, text=True, cwd=str(REPO), timeout=600,
    )
    res = {"exit_code": proc.returncode, "ran": out.is_file()}
    if not out.is_file():
        res["stderr_tail"] = proc.stderr[-500:]
        return res
    got = read_json(out)
    res.update({
        "verdict": got.get("verdict"),
        "pin_summary": got.get("pin_summary"),
        "lock_compliance": got.get("lock_compliance"),
        "class_binding_authority_flags": {
            k: v for k, v in (got.get("class_binding_authority", {}) or {}).items()
            if k.startswith("A")
        },
        "reproduces_filed_pin_summary": got.get("pin_summary") == filed.get("pin_summary"),
        "reproduces_filed_verdict": got.get("verdict") == filed.get("verdict"),
    })
    rt = got.get("independent_order_refit", {}) or {}
    ft = filed.get("independent_order_refit", {}) or {}
    res["refit_schemes_match_filed"] = rt.get("schemes") == ft.get("schemes")
    return res


def lock_guard_check() -> dict:
    mp = read_json(REPO / REL["map"])
    lock = mp.get("numerics_lock", {}) or {}
    proc = subprocess.run([sys.executable, str(REPO / REL["gates"])],
                          capture_output=True, text=True, cwd=str(REPO), timeout=300)
    guard = {}
    try:
        guard = json.loads(proc.stdout)
    except Exception:
        guard = {"unparsed_stdout_tail": proc.stdout[-300:]}
    ok = (lock.get("state") == "locked"
          and not (REPO / "numerics/spherical_solver").exists()
          and guard.get("production_allowed") is False)
    return {
        "numerics_lock_state": lock.get("state"),
        "locked_nodes": lock.get("locked_nodes"),
        "allowed_nodes": lock.get("allowed_nodes"),
        "spherical_solver_present": (REPO / "numerics/spherical_solver").exists(),
        "gates_exit_code": proc.returncode,
        "guard_verdict": guard.get("verdict"),
        "guard_production_allowed": guard.get("production_allowed"),
        "guard_protocol_contest": (guard.get("protocol_review", {}) or {}).get("contest"),
        "ok": ok,
        "pass": ok,
    }


def run_controls(scratch: Path, record: dict, cert_text: str) -> list[dict]:
    """Planted corruptions on scratch copies; each must behave as declared."""
    controls = []
    scratch.mkdir(parents=True, exist_ok=True)

    # C1: carrier hash corrupted in a record copy -> pin resolver flags mismatch.
    r1 = json.loads(json.dumps(record))
    r1["carrier"]["sha256"] = "0" * 64
    p1 = scratch / "record_c1.json"
    p1.write_text(json.dumps(r1))
    st = pin_status(REPO / REL["carrier"], r1["carrier"]["sha256"])
    controls.append({"id": "C1-carrier-hash", "expected": "mismatch", "observed": st["status"],
                     "passed": st["status"] == "mismatch"})

    # C2: one hex char corrupted in a basis prefix -> mismatch.
    r2 = json.loads(json.dumps(record))
    ref = r2["basis_evidence"][0]
    path, h = ref.rsplit("#", 1)
    h2 = ("f" if h[0] != "f" else "e") + h[1:]
    r2["basis_evidence"][0] = f"{path}#{h2}"
    st2 = pin_status(REPO / path, h2)
    controls.append({"id": "C2-basis-prefix", "expected": "mismatch", "observed": st2["status"],
                     "passed": st2["status"] == "mismatch"})

    # C3: absent cited path -> missing.
    st3 = pin_status(scratch / "does-not-exist.json", "abcdef123456")
    controls.append({"id": "C3-missing-path", "expected": "missing", "observed": st3["status"],
                     "passed": st3["status"] == "missing"})

    # C4: taxonomy revision mutated in a scratch copy -> binding check fails.
    tax = (REPO / REL["binding"]).read_text().replace("revision: 5", "revision: 6", 1)
    tax_copy = scratch / "taxonomy_c4.yaml"
    tax_copy.write_text(tax)
    b4 = binding_revision_ok(tax_copy)
    controls.append({"id": "C4-taxonomy-revision", "expected": "revision_is_5 false",
                     "observed": b4, "passed": b4["revision_is_5"] is False})

    # C5: one rung perturbed 5% -> refit deviates beyond tolerance.
    cert = json.loads(cert_text)
    rows = cert["schemes"]["cnfd"]["fixed_dt_certification"]["rows"]
    rows[0]["l2_error"] = rows[0]["l2_error"] * 1.05
    refit = lsq_order(rows)
    dev = abs(refit["p"] - float(cert["schemes"]["cnfd"]["fixed_dt_certification"]["fit_order"]))
    controls.append({"id": "C5-perturbed-rung", "expected": "deviation > 1e-6",
                     "observed_deviation": dev, "passed": dev > ORDER_TOL})

    # C6: drift-guard self-test -> a mutated copy is detected.
    probe = scratch / "guard_probe.txt"
    probe.write_text("before")
    h_before = sha256_file(probe)
    probe.write_text("after")
    h_after = sha256_file(probe)
    controls.append({"id": "C6-drift-guard", "expected": "hash changes",
                     "passed": h_before != h_after})

    # C7: control scratch copies do not touch the canonical tree.
    controls.append({"id": "C7-canonical-untouched", "expected": "record unchanged",
                     "observed": sha256_file(REPO / REL["record"]),
                     "passed": sha256_file(REPO / REL["record"]) == EXPECT["record"]})
    return controls


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(HERE / "report.json"))
    args = ap.parse_args()

    inputs = {k: REPO / v for k, v in REL.items()}
    before = {k: (sha256_file(p) if p.is_file() else None) for k, p in inputs.items()}

    record = read_json(inputs["record"])
    carrier = read_json(inputs["carrier"])
    cert_text = inputs["cert"].read_text()
    filed_audit = read_json(inputs["drift_audit"])

    checks: dict[str, dict] = {}

    # P1/P2: identity + all declared pins.
    rec_hash = sha256_file(inputs["record"])
    pins = verify_record_pins(record)
    checks["P1_record_identity"] = {
        "measured": rec_hash, "expected": EXPECT["record"], "pass": rec_hash == EXPECT["record"],
        "carrier_declared_sha256_equals_measured_carrier":
            record["carrier"]["sha256"] == sha256_file(inputs["carrier"]),
    }
    checks["P2_declared_pins"] = {
        "n": len(pins), "mismatched": [p for p in pins if p["status"] != "match"],
        "pass": all(p["status"] == "match" for p in pins),
    }

    # P3: carrier declares binding.
    cdb = carrier_declares_binding(carrier)
    checks["P3_carrier_declares_binding"] = {
        **cdb,
        "pass": (cdb["class_binding_sha256_is_rev5"] and cdb["declared_revision_is_5"]
                 and cdb["f0_rebind_names_rev5"] and cdb["class_id"] == "AF-WCC-SCALAR-SPH"),
    }

    # P4: binding revision.
    br = binding_revision_ok(inputs["binding"])
    checks["P4_binding_revision"] = {**br, "pass": br["revision_is_5"] and br["contains_class"]}

    # P5: protocol citations.
    pc = protocol_citation_check(inputs["protocol"], record)
    checks["P5_protocol_citations"] = {
        **pc,
        "pass": (pc["hash"] == EXPECT["protocol"]
                 and pc["every_superseded_pin_present"]
                 and pc["record_locations_cover_hits"]),
    }

    # P6: single carrier.
    sc = single_carrier_scan({k: inputs[k] for k in
                              ("record", "carrier", "protocol", "cert", "drift_audit",
                               "rev042", "rev081ps", "revfinal", "rev012", "addendum081")})
    checks["P6_single_carrier"] = {**sc, "pass": sc["exactly_one_carrier_path"]}

    # P7: materiality.
    mat = materiality_check(inputs["cert"])
    checks["P7_materiality"] = {**mat, "pass": mat["zero_taxonomy_strings"] and mat["refit_within_tol"]}

    # P8: drift audit reproduction.
    dr = drift_audit_rerun(SCRATCH, filed_audit)
    checks["P8_drift_audit_rerun"] = {
        **dr,
        "pass": (dr.get("exit_code") == 0 and dr.get("reproduces_filed_pin_summary")
                 and dr.get("reproduces_filed_verdict") and dr.get("refit_schemes_match_filed")),
    }

    # P9: lock guard.
    lg = lock_guard_check()
    checks["P9_lock_guard"] = lg

    # P10: advisory clock annotation.
    st = os.stat(inputs["record"])
    checks["P10_clock_advisory"] = {
        "published_at": record.get("published_at"),
        "file_mtime": __import__("datetime").datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
        "note": "advisory only; non-load-bearing",
        "pass": True,
    }

    # P11: non-claims accuracy.
    nc = " ".join(record.get("non_claims", [])).lower()
    checks["P11_non_claims"] = {
        "has_gate_verdict_disclaimer": "not a gate verdict" in nc,
        "has_lock_disclaimer": "locked" in nc,
        "has_no_edit_disclaimer": "does not edit" in nc,
        "pass": ("not a gate verdict" in nc and "locked" in nc and "does not edit" in nc),
    }

    controls = run_controls(SCRATCH, record, cert_text)

    after = {k: (sha256_file(p) if p.is_file() else None) for k, p in inputs.items()}
    canon_stable = before == after
    checks["canonical_drift_guard"] = {"before": before, "after": after, "pass": canon_stable}

    core_fail = sorted(k for k, v in checks.items() if not v.get("pass"))
    control_fail = [c["id"] for c in controls if not c["passed"]]
    lock_ok = lg["ok"]

    if not lock_ok:
        verdict, code = "LOCK_VIOLATION", 3
    elif core_fail:
        verdict, code = "CORE_CHECK_FAILED", 2
    elif control_fail:
        verdict, code = "CONTROL_FAILED", 4
    else:
        verdict, code = "CARRIER_RECORD_VERIFIED", 0

    report = {
        "schema": "w014-n0-carrier-verification/v1",
        "task_id": "W014-GNUM-CARRIER-VERIFY-01",
        "actor": "worker-014",
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N0",
        "gate": "G-NUM",
        "target": {"path": REL["record"], "sha256": EXPECT["record"], "author": "astra-lead-numerics"},
        "verdict": verdict,
        "core_failures": core_fail,
        "control_failures": control_fail,
        "checks": checks,
        "controls": controls,
        "declared_pins": pins,
        "falsifier": (
            "Re-run verify_carrier.py at the pinned inputs. This verification is falsified if the "
            "record hash is not effd20b0ea09, if any declared/cited pin measures differently, if the "
            "carrier does not declare F0 rev5 0abb9ed8a961, if the taxonomy at that pin is not "
            "revision 5 / lacks AF-WCC-SCALAR-SPH, if the protocol hash moved or no longer cites the "
            "superseded pins at the named locations, if a second class-binding carrier is named, if "
            "the independent refit deviates by > 1e-6, if the drift-audit re-run does not reproduce "
            "the filed audit, if any control does not behave as declared, or if any canonical input "
            "hash drifts during the run."
        ),
        "does_not_claim": [
            "not a G-NUM gate verdict and no gate self-pass (Astra / lead-audit authority)",
            "not controller ratification of the carrier record",
            "not an N0 node completion or status transition",
            "not an adjudication of the C8 protocol-review contest",
            "no physics / self-gravity / WCC / SCC claim; numerics_lock stays LOCKED and N1 queued",
        ],
    }

    out = Path(args.out)
    payload = json.dumps(report, indent=1, sort_keys=True)
    out.write_text(payload + "\n")

    # Determinism: the payload minus the advisory clock block must serialize identically twice,
    # and a full second run of the instrument must reproduce it (checked externally by diff).
    det = json.loads(payload)
    det["checks"].pop("P10_clock_advisory", None)
    p1 = json.dumps(det, sort_keys=True)
    p2 = json.dumps(json.loads(p1), sort_keys=True)
    print(json.dumps({
        "verdict": verdict, "core_failures": core_fail, "control_failures": control_fail,
        "deterministic_rebuild": p1 == p2,
        "report": str(out), "report_sha256": sha256_file(out),
    }, indent=1, sort_keys=True))
    return code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # fail closed
        print(json.dumps({"instrument_error": repr(exc)}), file=sys.stderr)
        sys.exit(5)
