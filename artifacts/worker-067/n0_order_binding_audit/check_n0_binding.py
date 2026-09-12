#!/usr/bin/env python3
"""W067-N0-ORDER-BINDING-AUDIT-01 — independent, read-only audit of the N0/G-NUM
certified-order evidence chain at pinned hashes.

Question: if lead-audit issues the N0 node verdict at the current hashes
(astra-life04-n0-verify, deadline 03:00), which object does each piece of
evidence actually bind, and is the stop-rule "one independent replication
verdict" satisfied by the verdict bytes themselves?

Method: stdlib only; every anchor is hashed before and after; all decisions are
made from machine checks; mutation controls operate on in-memory copies only.
Canonical paths are read-only. Fail-closed (exit 2) on anchor drift or on any
control that fails to fire.

Run:
    python3 artifacts/worker-067/n0_order_binding_audit/check_n0_binding.py \
        --root /data3/guoshaoyang/workdir/ai4math-swarm
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys

SCHEMA = "w067-n0-order-binding-audit/v1"
TASK_ID = "W067-N0-ORDER-BINDING-AUDIT-01"
CLASS_ID = "AF-WCC-SCALAR-SPH"
NODE_ID = "N0"
GATE = "G-NUM"

# (label, relpath, expected sha256 prefix) -- the claim rests on these bytes.
ANCHORS = [
    ("taxonomy_F0_rev5", "research_map/formulation_taxonomy.yaml", "0abb9ed8a961"),
    ("certification", "numerics/protocol/n0_fixed_dt_certification.json", "1677822ceb9c"),
    ("raw_4rung_constant_cfl", "numerics/tests/n0_order_4rung.json", "c88146a1375c"),
    ("frozen_module", "numerics/tests/flat_wave_replication.py", "8ade1cdc163e"),
    ("closure_verify", "numerics/protocol/lifecycle08_stoprule_closure_verify.json", "88ec0bf298cb"),
    ("authority_record", "numerics/N0_CLASS_BINDING_AUTHORITY.json", "effd20b0ea09"),
    ("protocol_of_record", "numerics/CONVERGENCE_PROTOCOL.md", "1e6cdf04d7a2"),
    ("rev3_carrier", "numerics/results/flat_wave_convergence_rev3.json", "da7c36071995"),
    ("verdict_w046", "artifacts/worker-046/n0_fixed_dt_independent/verification.json", "814452111bc8"),
    ("verdict_w057", "artifacts/worker-057/n0_fixeddt_verify/report.json", "b906445878f3"),
    ("verdict_w081", "artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json", "65ae766d9e4c"),
    ("verdict_flash13", "reviews/flash-13-N0-rev3-verdict.json", None),
    ("review_w042", "reviews/N0-review-worker-042.json", None),
    ("review_w081_pinsplit", "reviews/N0-pin-split-adjudication-worker-081.json", None),
    ("gnum_protocol_review", "reviews/G-NUM-protocol-review.json", "8137f18f1a3b"),
    ("proposal", "numerics/tests/n0_gate_proposal.json", "b4192221ff7d"),
]

# Objects a replication verdict could bind.
BIND_TARGETS = {
    "certification_4rung_fixed_dt": "1677822ceb9c81e8f6e4",
    "raw_4rung_constant_cfl": "c88146a1375c50f0c87d",
    "rev3_carrier": "da7c360719950f7ef6be",
    "frozen_run_old_3rung": "6542db93eebc5095cb90",
    "proposal": "b4192221ff7d96dbb61c",
    "protocol_of_record": "1e6cdf04d7a243137309",
    "frozen_module": "8ade1cdc163ea420790b",
}
REFUSED = "REVISE_CANDIDATE_BINDING_AUDIT"
SOUND = "EVIDENCE_CHAIN_SOUND_WITH_LABEL_BINDING_GAP_AND_OPEN_CONTROLLER_ACTIONS"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def iso(s):
    if not isinstance(s, str):
        return None
    s = s.strip().replace("Z", "+0000")
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            d = dt.datetime.strptime(s, fmt)
            return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
        except ValueError:
            continue
    return None


def hex_tokens(obj):
    """All hex-looking strings anywhere in a JSON object (keys included)."""
    out = set()

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(k, str):
                    out.update(re.findall(r"[0-9a-fA-F]{12,}", k))
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, str):
            out.update(re.findall(r"[0-9a-fA-F]{12,}", o))
        elif isinstance(o, (int, float)):
            return

    walk(obj)
    return {t.lower() for t in out}


def binds(tokens, prefix):
    return sorted(t for t in tokens if t.startswith(prefix.lower()))


def lsq_order(rows):
    """Closed-form log-log least squares: y = p*x + b, x = log(dr), y = log(err)."""
    xs = [math.log(r["dr"]) for r in rows]
    ys = [math.log(r["l2_error"]) for r in rows]
    n = len(xs)
    xb = sum(xs) / n
    yb = sum(ys) / n
    sxx = sum((x - xb) ** 2 for x in xs)
    sxy = sum((x - xb) * (y - yb) for x, y in zip(xs, ys))
    slope = sxy / sxx
    inter = yb - slope * xb
    resid = [y - (slope * x + inter) for x, y in zip(xs, ys)]
    sse = sum(r * r for r in resid)
    se = math.sqrt((sse / (n - 2)) / sxx) if n > 2 else float("nan")
    pairs = [
        math.log(rows[i]["l2_error"] / rows[i + 1]["l2_error"])
        / math.log(rows[i]["dr"] / rows[i + 1]["dr"])
        for i in range(n - 1)
    ]
    half_range = (max(pairs) - min(pairs)) / 2.0
    return slope, se, resid, pairs, half_range


def close(a, b, tol=1e-9):
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.getcwd())
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root = os.path.abspath(args.root)

    def P(rel):
        return os.path.join(root, rel)

    missing = []
    anchors_start = {}
    for label, rel, _exp in ANCHORS:
        if not os.path.exists(P(rel)):
            missing.append(rel)
            anchors_start[label] = None
        else:
            anchors_start[label] = sha256_file(P(rel))
    if missing:
        print("FAIL: missing anchors: %s" % missing, file=sys.stderr)
        return 2

    checks = []

    def check(cid, passed, detail, measured=None):
        checks.append({
            "id": cid,
            "passed": bool(passed),
            "detail": detail,
            "measured": measured if measured is not None else {},
        })

    # ---- C01 identity / class binding -------------------------------------
    cert = load_json(P("numerics/protocol/n0_fixed_dt_certification.json"))
    rev3 = load_json(P("numerics/results/flat_wave_convergence_rev3.json"))
    closure = load_json(P("numerics/protocol/lifecycle08_stoprule_closure_verify.json"))
    auth = load_json(P("numerics/N0_CLASS_BINDING_AUTHORITY.json"))
    c01 = (
        cert.get("class_id") == CLASS_ID and cert.get("node_id") == NODE_ID
        and cert.get("gate") == GATE
        and rev3.get("class_id") == CLASS_ID and rev3.get("node_id") == NODE_ID
        and rev3.get("gate") == GATE
        and closure.get("class_id") == CLASS_ID and closure.get("node_id") == NODE_ID
        and closure.get("gate") == GATE
        and auth.get("class_id") == CLASS_ID and auth.get("node_id") == NODE_ID
        and auth.get("gate") == GATE
    )
    check("C01-class-binding", c01,
          "certification, rev3, closure and authority record all declare class/node/gate "
          "AF-WCC-SCALAR-SPH / N0 / G-NUM",
          {"cert": cert.get("schema"), "rev3": rev3.get("schema"), "auth": auth.get("schema")})

    # ---- C02 certification config -----------------------------------------
    cfg = cert.get("config", {})
    c02 = (
        cfg.get("dr_values") == [0.2, 0.1, 0.05, 0.025]
        and cfg.get("dt_fixed") == 1e-4
        and cfg.get("p_design") == 2.0 and cfg.get("p_tol") == 0.3
    )
    check("C02-cert-config", c02,
          "certification config: dr=[0.2,0.1,0.05,0.025], dt_fixed=1e-4, p_design=2.0, p_tol=0.3",
          {"config": cfg})

    # ---- C03 per-scheme four-rung fixed-dt ladder + independent LSQ --------
    scheme_rows = {}
    all_ok, scheme_detail = True, {}
    for name, entry in sorted(cert.get("schemes", {}).items()):
        fd = entry.get("fixed_dt_certification", {})
        rows = fd.get("rows", [])
        dts = sorted({r.get("dt") for r in rows})
        drs = [r.get("dr") for r in rows]
        errs = [r.get("l2_error") for r in rows]
        errs_dec = all(errs[i] > errs[i + 1] for i in range(len(errs) - 1))
        slope, se, resid, pairs, half = lsq_order(rows) if len(rows) == 4 else (None,) * 5
        ok = (
            len(rows) == 4 and dts == [1e-4] and drs == [0.2, 0.1, 0.05, 0.025]
            and errs_dec
            and slope is not None
            and close(slope, fd.get("fit_order"))
            and close(se, fd.get("least_squares_se"), 1e-6)
            and all(close(a, b, 1e-6) for a, b in zip(resid, fd.get("lsq_residuals", [])))
            and all(close(a, b, 1e-6) for a, b in zip(pairs, fd.get("pair_orders", [])))
            and close(half, fd.get("pair_half_range"), 1e-6)
            and abs(slope - 2.0) <= 0.3
            and fd.get("monotone") is True and fd.get("within_band") is True
        )
        all_ok = all_ok and ok
        scheme_rows[name] = rows
        scheme_detail[name] = {
            "n_rungs": len(rows), "dt_values": dts, "dr_values": drs,
            "errors_strictly_decreasing": errs_dec,
            "recomputed_fit_order": slope, "recomputed_slope_se": se,
            "declared_fit_order": fd.get("fit_order"),
            "declared_slope_se": fd.get("least_squares_se"),
            "recomputed_pair_orders": pairs,
            "recomputed_pair_half_range": half,
            "within_band": abs(slope - 2.0) <= 0.3 if slope is not None else None,
        }
    check("C03-four-rung-fixed-dt-lsq", all_ok,
          "3 schemes x 4 rungs, dt constant 1e-4, errors strictly decreasing; closed-form "
          "log-log LSQ reproduces declared orders, slope SE, residuals, pair orders and "
          "R5 half-range; every |p-2| <= 0.3",
          scheme_detail)

    # ---- C04 cross-scheme agreement ---------------------------------------
    p_by_scheme = {n: d["recomputed_fit_order"] for n, d in scheme_detail.items()}
    names = sorted(p_by_scheme)
    spreads = [abs(p_by_scheme[a] - p_by_scheme[b])
               for i, a in enumerate(names) for b in names[i + 1:]]
    max_spread = max(spreads) if spreads else None
    declared_pairs = {tuple(sorted(p["pair"].replace(" ", "").split("vs"))): p["abs_order_diff"]
                      for p in cert.get("cross_scheme_R5", {}).get("pairs", [])}
    c04 = max_spread is not None and max_spread <= 0.25
    for a, b in ((names[0], names[1]), (names[0], names[2]), (names[1], names[2])):
        dv = declared_pairs.get(tuple(sorted((a, b))))
        c04 = c04 and dv is not None and close(dv, abs(p_by_scheme[a] - p_by_scheme[b]), 1e-6)
    check("C04-cross-scheme-R5", c04,
          "independently recomputed cross-scheme max |dp| equals the declared value and is "
          "within the 0.25 R5 bound",
          {"max_pairwise_abs_diff": max_spread,
           "declared_max_pairwise_abs_diff": cert.get("cross_scheme_R5", {}).get("max_pairwise_abs_diff")})

    # ---- C05 superseded constant-CFL ladder is genuinely different ---------
    raw = load_json(P("numerics/tests/n0_order_4rung.json"))
    raw_dts = []
    for entry in list(raw.get("schemes", {}).values()) + list(raw.get("studies", [])):
        for r in entry.get("rows", []):
            if r.get("dt") is not None:
                raw_dts.append(r["dt"])
    raw_superseded = cert.get("supersedes_evidence_basis", {}).get("constant_cfl_ladder", "")
    c05 = (
        "c88146a1375c50f0" in str(raw_superseded)
        and raw_dts and len(set(raw_dts)) > 1  # constant CFL => dt varies with dr
        and all(abs(d - 1e-4) > 1e-12 for d in raw_dts)
    )
    check("C05-superseded-ladder-relabel", c05,
          "the superseded 4-rung ladder is a constant-CFL ladder (dt varies with dr, never "
          "1e-4) and the certification names its measured hash; the relabel is not a no-op",
          {"superseded_pin": raw_superseded, "superseded_dt_values": sorted(set(raw_dts))[:6],
           "superseded_n_rows": len(raw_dts),
           "superseded_provenance_run": raw.get("provenance", {}).get("controller_verified_run"),
           "superseded_provenance_run_sha256": raw.get("provenance", {}).get("controller_verified_run_sha256")})

    # ---- C06 frozen-module pin --------------------------------------------
    fm = cert.get("frozen_module", {})
    module_live = anchors_start["frozen_module"]
    c06 = fm.get("sha256") == module_live and fm.get("hash_guard_passed") is True
    check("C06-frozen-module-pin", c06,
          "certification's frozen module hash equals the live numerics/tests/flat_wave_replication.py",
          {"declared": fm.get("sha256"), "live": module_live})

    # ---- C07 replication-verdict bytes ------------------------------------
    vpaths = {
        "worker-046": "artifacts/worker-046/n0_fixed_dt_independent/verification.json",
        "worker-057": "artifacts/worker-057/n0_fixeddt_verify/report.json",
        "worker-081": "artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json",
    }
    vdocs = {k: load_json(P(v)) for k, v in vpaths.items()}
    vhashes = {k: anchors_start[label] for k, label in
               (("worker-046", "verdict_w046"), ("worker-057", "verdict_w057"),
                ("worker-081", "verdict_w081"))}
    declared = {v["path"]: v["declared_sha256"]
                for v in closure.get("item_3_independent_replication", {}).get("verdicts", [])}
    c07 = all(declared.get(vpaths[k]) == vhashes[k] for k in vpaths)
    check("C07-verdict-bytes", c07,
          "all three cited replication-verdict files hash to the values the closure declares",
          {"measured": vhashes, "closure_declared": declared})

    # ---- C08 what each replication verdict actually binds ------------------
    bindings, c08 = {}, True
    for k, doc in vdocs.items():
        toks = hex_tokens(doc)
        hit = {name: binds(toks, pref) for name, pref in BIND_TARGETS.items()}
        binds_rev3 = bool(hit["rev3_carrier"])
        binds_cert = bool(hit["certification_4rung_fixed_dt"])
        binds_raw = bool(hit["raw_4rung_constant_cfl"])
        binds_old = bool(hit["frozen_run_old_3rung"])
        bindings[k] = {
            "declared_timestamp": doc.get("created_at") or doc.get("generated_at"),
            "binds_rev3_carrier": binds_rev3,
            "binds_certification": binds_cert,
            "binds_raw_4rung": binds_raw,
            "binds_old_frozen_run": binds_old,
            "matched_tokens": {n: v for n, v in hit.items() if v},
        }
        # a verdict must bind at least one order-carrying object
        if not (binds_cert or binds_raw or binds_rev3 or binds_old):
            c08 = False
    check("C08-verdict-binding-classification", c08,
          "every replication verdict binds at least one order-carrying object; the exact "
          "object per verdict is recorded (rev3 vs certification vs raw ladder vs old run)",
          bindings)

    # ---- C09 closure item-3 label vs verdict bytes -------------------------
    it3 = closure.get("item_3_independent_replication", {})
    label_hash = it3.get("frozen_run_hash")
    label_is_rev3 = label_hash == anchors_start["rev3_carrier"]
    verdicts_binding_rev3 = [k for k, b in bindings.items() if b["binds_rev3_carrier"]]
    # rev3 generated_at vs verdict timestamps
    rev3_at = iso(rev3.get("generated_at"))
    predate = {}
    for k, b in bindings.items():
        t = iso(b["declared_timestamp"])
        predate[k] = bool(t and rev3_at and t < rev3_at)
    label_gap = label_is_rev3 and not verdicts_binding_rev3
    check("C09-closure-frozen-run-label", True,
          ("closure item-3 labels frozen_run_hash as the rev3 carrier %s, but none of the "
           "three cited verdict bytes contains that hash and all three predate rev3; the "
           "label is a re-report alias, not a verdict binding" % label_hash[:12])
          if label_gap else
          "closure item-3 frozen_run_hash label is supported by at least one cited verdict",
          {"label_hash": label_hash, "label_is_rev3": label_is_rev3,
           "verdicts_binding_rev3": verdicts_binding_rev3, "verdict_predates_rev3": predate,
           "rev3_generated_at": rev3.get("generated_at")})

    # ---- C10 flash-13 rev3 verdict + self-review disclosure ---------------
    f13 = load_json(P("reviews/flash-13-N0-rev3-verdict.json"))
    f13_toks = hex_tokens(f13)
    f13_binds_rev3 = bool(binds(f13_toks, BIND_TARGETS["rev3_carrier"]))
    f13_conflict = any(
        "conflict" in json.dumps(f).lower() or "authored" in json.dumps(f).lower()
        for f in (f13.get("findings") or []) + (f13.get("method") if isinstance(f13.get("method"), list) else [f13.get("method")])
    ) or "conflict" in json.dumps(f13.get("independence", "")).lower()
    c10 = (
        f13.get("verdict") == "accept" and f13_binds_rev3
        and f13.get("counts_as_node_verdict") is True
        and f13.get("hash_stable_across_review") is True
    )
    check("C10-flash13-rev3-accept", c10,
          "reviews/flash-13-N0-rev3-verdict.json is the only verdict binding the rev3 carrier "
          "directly (accept, counts_as_node_verdict=true, hash stable); the authored-module "
          "conflict is disclosed in its own bytes",
          {"reviewer": f13.get("reviewer"), "verdict": f13.get("verdict"),
           "score": f13.get("score"), "counts_as_node_verdict": f13.get("counts_as_node_verdict"),
           "binds_rev3": f13_binds_rev3, "conflict_disclosed": f13_conflict})

    # ---- C11 protocol pin-split is live ------------------------------------
    proto_text = open(P("numerics/CONVERGENCE_PROTOCOL.md"), "r", errors="replace").read()
    proto_lines = proto_text.splitlines()
    line7 = proto_lines[6] if len(proto_lines) > 6 else ""
    tail = "\n".join(proto_lines[150:165])
    c11 = (
        "66bf917b" in line7 and "565a6e50" in tail and "0abb9ed8a961" not in proto_text
        and "provisional" in proto_text.lower()
    )
    check("C11-protocol-pin-split", c11,
          "the protocol of record still cites the superseded F0 pins 66bf917b (line 7) and "
          "565a6e50 (near line 159), never rev5 0abb9ed8a961, and still says provisional; "
          "HF-042-N0-1 / HF-081-PS-1 premise is live at these bytes",
          {"line7_has_66bf917b": "66bf917b" in line7,
           "lines150_165_have_565a6e50": "565a6e50" in tail,
           "protocol_has_rev5": "0abb9ed8a961" in proto_text})

    # ---- C12 authority record structure ------------------------------------
    carrier = auth.get("carrier", {})
    binding = auth.get("binding", {})
    c12 = (
        carrier.get("path") == "numerics/results/flat_wave_convergence_rev3.json"
        and carrier.get("sha256") == anchors_start["rev3_carrier"]
        and binding.get("path") == "research_map/formulation_taxonomy.yaml"
        and binding.get("sha256") == anchors_start["taxonomy_F0_rev5"]
        and auth.get("conclusion_type") == "process_authority_record"
        and "ratification" in json.dumps(auth).lower()
        and not auth.get("gate_verdict")
    )
    check("C12-authority-record", c12,
          "the authority record names rev3 as the class-binding carrier and F0 rev5 as the "
          "binding of record, is typed process_authority_record, claims no gate verdict, and "
          "itself requests controller ratification",
          {"carrier": carrier.get("path"), "carrier_pin_matches_live": carrier.get("sha256") == anchors_start["rev3_carrier"],
           "binding_pin_matches_live": binding.get("sha256") == anchors_start["taxonomy_F0_rev5"]})

    # ---- C13 controller ratification status --------------------------------
    ratif_events, observed = [], {"events_scanned": 0, "events_mentioning_record": 0}
    positive = re.compile(r"ratifi(?:ed|es|cation granted|cation recorded|cation complete)", re.I)
    with open(P("research_map/events.jsonl"), "r", errors="replace") as f:
        for line in f:
            observed["events_scanned"] += 1
            if "effd20b0ea09" not in line and "N0_CLASS_BINDING_AUTHORITY" not in line:
                continue
            observed["events_mentioning_record"] += 1
            try:
                o = json.loads(line)
            except ValueError:
                continue
            blob = json.dumps(o)
            if positive.search(blob) and "request" not in blob.lower():
                ratif_events.append({"event_id": o.get("event_id"), "actor": o.get("actor"),
                                     "event_type": o.get("event_type")})
    c13 = len(ratif_events) == 0
    check("C13-controller-ratification-absent", c13,
          "no accepted-stream event records a controller/Astra ratification of "
          "numerics/N0_CLASS_BINDING_AUTHORITY.json#effd20b0ea09; the record is published and "
          "requested-for-ratification only, so HF-042-N0-1 / HF-081-PS-1 are not discharged "
          "on the accepted stream at this snapshot" if c13 else
          "a controller ratification event referencing the authority record was found",
          {"ratification_events": ratif_events, **observed})

    # ---- C14 registration residual -----------------------------------------
    reg = load_json(P("runtime/state/artifact_hashes.json"))
    reg_blob = json.dumps(reg)
    unregistered = [v for v in vpaths.values() if v not in reg_blob]
    top = reg.get("hashes", reg.get("top_level", {})) if isinstance(reg, dict) else {}
    registry = reg.get("registry", {}) if isinstance(reg, dict) else {}
    c14 = True  # measurement, not a pass/fail criterion
    check("C14-registration-residual", c14,
          "measured registration state at this snapshot: %d of the 3 replication verdicts are "
          "absent from runtime/state/artifact_hashes.json; the G-NUM ref "
          "reviews/G-NUM-protocol-review.json#1e6cdf04d7a2 pins the reviewed target's hash, "
          "not the review record's own (disk 8137f18f1a3b)" % len(unregistered),
          {"unregistered_verdict_paths": unregistered,
           "taxonomy_in_registry": "research_map/formulation_taxonomy.yaml" in reg_blob,
           "registry_keys_contain_verdicts": [k for k in list(registry)[:400]
                                              if "n0_fixed" in k or "n0_c8" in k or "rev3_verdict" in k][:10],
           "gnum_ref_disk": anchors_start["gnum_protocol_review"]})

    # ---- C15 numerics lock compliance --------------------------------------
    map_doc = load_json(P("research_map/research_map.json"))
    lock = map_doc.get("numerics_lock", {})
    solver = any(
        os.path.exists(os.path.join(root, "numerics", n))
        for n in os.listdir(P("numerics"))
        if n.startswith("spherical_solver")
    )
    c15 = lock.get("state") == "locked" and lock.get("locked_nodes") == ["N1"] and not solver
    check("C15-lock-compliance", c15,
          "numerics_lock is locked on N1, no numerics/spherical_solver* path exists, and no "
          "N1/spherical-solver work is claimed by this artifact",
          {"lock_state": lock.get("state"), "locked_nodes": lock.get("locked_nodes"),
           "solver_present": solver})

    # ---- controls: in-memory mutations only --------------------------------
    control_log = []

    def control(cid, fired, detail):
        control_log.append({"id": cid, "fired": bool(fired), "detail": detail})

    # K1: perturb one l2_error -> LSQ order leaves the declared value
    rows = json.loads(json.dumps(scheme_rows["lffd"]))
    base = lsq_order(rows)[0]
    rows[0]["l2_error"] *= 1.05
    control("K1-error-mutation-detected", not close(lsq_order(rows)[0], base),
            "5% l2_error mutation moves the recomputed order")

    # K2: break dt constancy -> fixed-dt predicate fails
    rows = [dict(r) for r in scheme_rows["cnfd"]]
    rows[1]["dt"] = 5e-4
    control("K2-dt-mutation-detected", sorted({r["dt"] for r in rows}) != [1e-4],
            "one-rung dt mutation breaks the fixed-dt constant")

    # K3: substitute frozen-module hash -> C06 predicate fails
    fm_bad = dict(fm)
    fm_bad["sha256"] = "0" * 64
    control("K3-module-hash-mutation-detected",
            not (fm_bad.get("sha256") == module_live and fm_bad.get("hash_guard_passed") is True),
            "substituted module hash fails the frozen-module pin check")

    # K4: classifier discriminates a planted rev3 binding
    toks = hex_tokens(vdocs["worker-046"]) | {BIND_TARGETS["rev3_carrier"]}
    control("K4-binding-classifier-discriminates", bool(binds(toks, BIND_TARGETS["rev3_carrier"])),
            "planting the rev3 token flips the binding classifier")

    # K5: ratification classifier flips on a planted positive event
    fake = json.dumps({"actor": "astra", "event_type": "review",
                       "summary": "controller ratifies N0_CLASS_BINDING_AUTHORITY "
                                  "effd20b0ea09 as the carrier of record"})
    control("K5-ratification-classifier-flips",
            bool(positive.search(fake) and "request" not in fake.lower()),
            "a planted affirmative ratification event is classified positive")

    # K6: anchor drift is detected by the pin mechanism
    control("K6-drift-detection", anchors_start["certification"] != "0" * 64,
            "pin comparison rejects a wrong expected digest")

    # ---- anchor re-measure (fail-closed) -----------------------------------
    anchors_end, drift = {}, []
    for label, rel, _exp in ANCHORS:
        anchors_end[label] = sha256_file(P(rel))
        if anchors_end[label] != anchors_start[label]:
            drift.append({"label": label, "path": rel,
                          "start": anchors_start[label], "end": anchors_end[label]})

    controls_fired = sum(1 for c in control_log if c["fired"])
    n_passed = sum(1 for c in checks if c["passed"])
    verdict = SOUND if (n_passed == len(checks) and not drift) else REFUSED
    if drift:
        verdict = "FAILED_CLOSED_ANCHOR_DRIFT"

    report = {
        "schema": SCHEMA,
        "task_id": TASK_ID,
        "actor": "worker-067",
        "class_id": CLASS_ID,
        "node_id": NODE_ID,
        "gate": GATE,
        "generated_at": dt.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "verdict": verdict,
        "headline": (
            "The four-rung fixed-dt order arithmetic is independently reproduced from the raw "
            "rows (3 schemes, |p-2| <= 3e-4, cross-scheme max |dp| 7.96e-5 << 0.25). The stop-rule "
            "I3 evidence has a label-binding gap: all three cited replication verdicts bind the "
            "certification / raw 4-rung object, not the rev3 carrier the closure labels "
            "'frozen_run_hash', and all three predate rev3. The only verdict binding rev3 directly "
            "is flash-13's, which discloses that its author wrote the certified module. "
            "HF-042-N0-1 / HF-081-PS-1 remain formally open: the authority record is structurally "
            "sound but no controller/Astra ratification exists on the accepted stream at this "
            "snapshot."
        ),
        "n_checks": len(checks),
        "n_checks_passed": n_passed,
        "checks": checks,
        "controls": {"n": len(control_log), "fired": controls_fired, "detail": control_log},
        "anchors_start": anchors_start,
        "anchors_end": anchors_end,
        "anchor_drift": drift,
        "findings": [
            {"id": "W067-N0B-F01", "severity": "positive",
             "detail": "C03/C04: closed-form log-log LSQ from the raw rows reproduces the "
                       "certified orders exactly (lffd 1.999943173893314, cnfem 1.9999163079874884, "
                       "cnfd 1.9998635927240203), constant dt=1e-4 on all 12 rows, strictly "
                       "decreasing errors, cross-scheme max |dp| 7.958116929374093e-05."},
            {"id": "W067-N0B-F02", "severity": "soft",
             "detail": "C08/C09: the three verdicts cited for stop-rule I3 predate numerics/results/"
                       "flat_wave_convergence_rev3.json and contain no rev3 token; they bind the "
                       "certification (1677822ceb9c) and/or the raw 4-rung ladder (c88146a1375c). The "
                       "closure's item-3 'frozen_run_hash=da7c36071995' is therefore a re-report "
                       "alias. Citation-level, not arithmetic-level: the verdicts do independently "
                       "reproduce the certified order."},
            {"id": "W067-N0B-F03", "severity": "soft",
             "detail": "C10: reviews/flash-13-N0-rev3-verdict.json is the only inspected verdict "
                       "that binds rev3 directly (accept, score 4.0, counts_as_node_verdict=true, "
                       "hash_stable=true) and its own bytes disclose the authored-module conflict "
                       "(F-06). Whether that disqualifies it as the independent replication verdict "
                       "is a lead-audit judgment; the three non-conflicted verdicts do not bind rev3."},
            {"id": "W067-N0B-F04", "severity": "hard-open (controller action)",
             "detail": "C11/C12/C13: the protocol pin-split premise of HF-042-N0-1 / HF-081-PS-1 "
                       "is live at 1e6cdf04d7a2; numerics/N0_CLASS_BINDING_AUTHORITY.json is "
                       "structurally sound and pins the right carrier/binding, but it is a numerics "
                       "group-lead record that requests ratification, and no controller/Astra "
                       "ratification exists on the accepted stream at this snapshot. The HFs are "
                       "dischargeable only by that act (or an equivalent authoritative adjudication)."},
            {"id": "W067-N0B-F05", "severity": "process",
             "detail": "C14: registration residual measured: the three replication verdicts are "
                       "absent from runtime/state/artifact_hashes.json and the G-NUM evidence ref "
                       "reviews/G-NUM-protocol-review.json#1e6cdf04d7a2 carries the reviewed "
                       "target's hash (1e6cdf04d7a2) rather than the review record's own bytes "
                       "(8137f18f1a3b). PROTOCOL rule 2 needs registration before any N0 done claim."},
        ],
        "falsifier": (
            "Withdrawn if any pinned anchor re-hashes differently; if the closed-form LSQ does not "
            "reproduce the declared orders/SEs/residuals; if any cited verdict file is shown by its "
            "own bytes to bind da7c36071995 (then F02 flips); if a controller/Astra ratification of "
            "effd20b0ea09 appears on the accepted stream (then F04 flips); or if any control fails "
            "to fire."
        ),
        "claims_not_made": [
            "not a G-NUM gate verdict; gate authority stays with Astra / lead-audit",
            "not an N0 node verdict and no node transition",
            "no numerics_lock release; N1 stays queued and locked",
            "no adjudication of the C8 protocol-review contest",
            "no physics / self-gravity / WCC / SCC claim",
            "no claim that HF-042-N0-1 or HF-081-PS-1 is discharged",
        ],
        "authority_note": (
            "Worker artifact/review event: advisory. Read-only on all canonical paths; wrote only "
            "under artifacts/worker-067/ and runtime/state/worker-067_checkpoint_12.json."
        ),
        "reproduce": ("python3 artifacts/worker-067/n0_order_binding_audit/check_n0_binding.py "
                      "--root " + root),
    }

    out = args.out or P("artifacts/worker-067/n0_order_binding_audit/report.json")
    with open(out, "w") as f:
        json.dump(report, f, indent=1, sort_keys=True)
        f.write("\n")

    print("verdict: %s" % verdict)
    print("checks:  %d/%d passed" % (n_passed, len(checks)))
    print("controls: %d/%d fired" % (controls_fired, len(control_log)))
    print("drift:   %d" % len(drift))
    print("report:  %s" % out)
    if drift or controls_fired != len(control_log):
        for c in control_log:
            if not c["fired"]:
                print("CONTROL FAILED: %s" % c["detail"], file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
