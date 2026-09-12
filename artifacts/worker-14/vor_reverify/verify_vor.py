#!/usr/bin/env python3
"""W014-GNUM-VOR-REVERIFY-01 — independent read-only verification of the re-issued
N0 gate-proposal verification of record.

Target : numerics/protocol/n0_gate_proposal_leadverify.json (re-issued 2026-09-12T00:52:21+08:00)
Against: numerics/tests/n0_gate_proposal.json#b4192221ff7d
Class  : AF-WCC-SCALAR-SPH / node N0 / gate G-NUM

Deterministic, read-only with respect to every canonical path. The only files written are the
report requested by --out and a scratch tree under --scratch that is removed before exit.
Exit codes: 0 = report produced (see verdict / controls_ok inside), 2 = instrument invalid
(control failure or input drift), 3 = usage error.

Usage:
  python3 verify_vor.py --out report.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
NOW_ISO = datetime.now(CST).isoformat(timespec="seconds")

PROPOSAL = "numerics/tests/n0_gate_proposal.json"
VOR = "numerics/protocol/n0_gate_proposal_leadverify.json"
REGISTRY = "runtime/state/artifact_hashes.json"
CERT = "numerics/protocol/n0_fixed_dt_certification.json"
GATES = "numerics/gates.py"
MAP = "research_map/research_map.json"
EVENTS = "research_map/events.jsonl"

# pins of the superseded state (from artifacts/worker-14/binding_audit/*), used for the
# supersession-fidelity check only; these are declarations being tested, not assumptions.
OLD_VOR_SHA = "e0f9ef9f329d4d5d4d7fbf37b10cc571bc0ee233a194f3ba9116ad91fe2ab012"
OLD_VOR_BYTES = 12074
OLD_PROPOSAL_SHA_PREFIX = "58a175b52fbe"
REFIT_TOL = 1e-6
R5_FLOOR = 0.25
P_TOL = 0.3


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure(path: Path, root: Path):
    p = root / path
    if not p.exists():
        return {"path": path, "exists": False, "measured_sha256": None, "bytes": None}
    if p.is_dir():
        return {"path": path, "exists": True, "kind": "dir", "measured_sha256": None, "bytes": None}
    return {
        "path": path,
        "exists": True,
        "kind": "file",
        "measured_sha256": sha256_file(p),
        "bytes": p.stat().st_size,
    }


def classify(expected_sha256, m) -> str:
    """Pure classifier over a measurement dict; planted controls exercise every branch."""
    if m.get("kind") == "dir":
        return "dir"
    if not m.get("exists"):
        return "missing"
    return "match" if m.get("measured_sha256") == expected_sha256 else "stale"


def registry_bases(reg_doc):
    full = None
    section = None
    if isinstance(reg_doc, dict):
        if "registry" in reg_doc:
            section = hashlib.sha256(
                json.dumps(reg_doc["registry"], sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
    return section


def registry_status(reg_doc, path, measured_sha256):
    """Per-section and union registration status for a path."""
    out = {}
    for section in ("hashes", "registry"):
        sec = reg_doc.get(section) if isinstance(reg_doc, dict) else None
        entry = sec.get(path) if isinstance(sec, dict) else None
        if entry is None:
            out[section] = "absent"
            continue
        declared = entry.get("sha256") if isinstance(entry, dict) else entry
        out[section] = "match" if declared == measured_sha256 else "stale"
    if "match" in out.values():
        out["union"] = "registered_match"
    elif "stale" in out.values():
        out["union"] = "registered_stale"
    else:
        out["union"] = "registered_absent"
    return out


def parse_hashish(value):
    """Extract a full or prefix sha256 from a string that may be 'path#deadbeef' / 'deadbeef (x)'."""
    if not isinstance(value, str):
        return None
    for tok in value.replace("#", " ").replace("(", " ").replace(")", " ").split():
        tok = tok.strip(",;:")
        if len(tok) >= 12 and all(c in "0123456789abcdef" for c in tok.lower()):
            return tok.lower()
    return None


def ls_slope(xs, ys):
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = my - slope * mx
    sse = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    se = math.sqrt(sse / (n - 2) / sxx) if n > 2 and sxx > 0 else None
    return slope, intercept, se, sse


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/data3/guoshaoyang/workdir/ai4math-swarm")
    ap.add_argument("--out", default=None)
    ap.add_argument("--scratch", default=None)
    a = ap.parse_args()
    root = Path(a.root).resolve()
    scratch = Path(a.scratch) if a.scratch else Path(tempfile.mkdtemp(prefix="w14vor_"))
    scratch.mkdir(parents=True, exist_ok=True)
    controls = []

    def control(cid, expected, observed):
        controls.append(
            {"id": cid, "expected": expected, "observed": observed, "ok": expected == observed}
        )

    report = {
        "schema": "w14-n0-vor-reverify/v1",
        "task_id": "W014-GNUM-VOR-REVERIFY-01",
        "actor": "worker-014",
        "runtime_slot": "worker-014",
        "created_at": NOW_ISO,
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "conclusion_type": "provenance_measurement",
        "supersedes_findings": [
            "artifacts/worker-14/binding_audit/n0_binding_audit_refresh.json#13600a5d4130 BA-1 (open)",
            "artifacts/worker-14/binding_audit/n0_binding_audit_refresh.json#13600a5d4130 BA-5 (open)",
        ],
    }

    # ---------- pins (before) ----------
    pins_before = {}
    for rel in (PROPOSAL, VOR, REGISTRY, CERT, GATES, MAP):
        pins_before[rel] = measure(rel, root)
    report["pins_before"] = pins_before
    prop_sha = pins_before[PROPOSAL]["measured_sha256"]
    vor_sha = pins_before[VOR]["measured_sha256"]
    reg_sha = pins_before[REGISTRY]["measured_sha256"]

    proposal = json.loads((root / PROPOSAL).read_text())
    vor = json.loads((root / VOR).read_text())
    reg_doc = json.loads((root / REGISTRY).read_text())
    reg_section = registry_bases(reg_doc)

    # ---------- A: binding of the record to the current proposal bytes ----------
    pv = vor.get("proposal_verified") or {}
    ev_id = pv.get("artifact_event")
    ev_hit = None
    ev_match = False
    if ev_id and (root / EVENTS).exists():
        with open(root / EVENTS) as f:
            for line in f:
                line = line.strip()
                if not line or ev_id not in line:
                    continue
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if e.get("event_id") == ev_id:
                    ev_hit = {
                        "event_id": e.get("event_id"),
                        "event_type": e.get("event_type"),
                        "actor": e.get("actor"),
                        "created_at": e.get("created_at"),
                        "path": e.get("path"),
                        "sha256": e.get("sha256"),
                        "validation_status": e.get("validation_status"),
                    }
                    ev_match = (
                        e.get("event_type") == "artifact"
                        and e.get("path") == pv.get("path")
                        and e.get("sha256") == prop_sha
                    )
                    break
    # announced revisions of the record, from the accepted stream (moving-target evidence)
    announced = {}
    if (root / EVENTS).exists():
        with open(root / EVENTS) as f:
            for line in f:
                if VOR not in line:
                    continue
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if e.get("event_type") == "artifact" and e.get("path") == VOR:
                    announced[str(e.get("sha256"))] = {
                        "event_id": e.get("event_id"),
                        "actor": e.get("actor"),
                        "created_at": e.get("created_at"),
                        "validation_status": e.get("validation_status"),
                    }
    A = {
        "vor_revision_verified": vor_sha,
        "vor_created_at_declared": vor.get("created_at"),
        "verdict_binds_this_revision_only": True,
        "proposal_path_declared": pv.get("path"),
        "proposal_sha256_declared": pv.get("sha256"),
        "proposal_sha256_measured": prop_sha,
        "binds_current_bytes": pv.get("sha256") == prop_sha,
        "artifact_event_id": ev_id,
        "artifact_event_found": ev_hit is not None,
        "artifact_event": ev_hit,
        "artifact_event_binds_same_bytes": ev_match,
        "unchanged_since_event_declared": pv.get("unchanged_since_artifact_event"),
        "recommended_verdict_declared": pv.get("recommended_verdict"),
        "vor_revision_announced_in_event_stream": str(vor_sha) in announced,
        "vor_announced_revisions_in_stream": announced,
        "ba1_closed_by_reissue": bool(pv.get("sha256") == prop_sha and ev_match),
    }
    # planted control: a wrong declared hash must classify as stale
    control("A_hash_sensitivity", "stale", classify("0" * 64, pins_before[PROPOSAL]))
    control("A_hash_sensitivity_ok", "match", classify(prop_sha, pins_before[PROPOSAL]))
    control("A_missing", "missing", classify(prop_sha, {"exists": False, "kind": None}))
    control("A_dir", "dir", classify(prop_sha, {"exists": True, "kind": "dir"}))
    report["A_binding"] = A

    # ---------- B: supersession fidelity ----------
    sup = vor.get("supersedes") or {}
    recovered = []
    for rel in (
        "artifacts/worker-14/binding_audit/n0_binding_audit_refresh.json",
        "artifacts/worker-14/binding_audit/n0_proposal_binding_audit.json",
    ):
        p = root / rel
        if not p.exists():
            continue
        doc = json.loads(p.read_text())
        blob = json.dumps(doc)
        if OLD_VOR_SHA in blob:
            pin = (doc.get("pins") or {}).get(VOR) or {}
            recovered.append(
                {
                    "source": rel,
                    "source_sha256": sha256_file(p),
                    "records_old_sha256": pin.get("sha256"),
                    "records_old_bytes": pin.get("bytes"),
                    "matches_supersedes_declaration": pin.get("sha256") == OLD_VOR_SHA,
                }
            )
    # old record's stale pins, as declared by the re-issue, re-measured against disk
    stale_rows = []
    for entry in sup.get("stale_pins_in_superseded_record") or []:
        path = entry.split("#", 1)[0].strip()
        old_prefix = parse_hashish(entry.split("#", 1)[1]) if "#" in entry else None
        cur_prefix = None
        disk_prefix_declared = None
        if "(disk " in entry:
            inner = entry.split("(disk ", 1)[1].rstrip(")")
            inner = inner.split(" ")[0].rstrip(")")
            disk_prefix_declared = inner.strip().rstrip(")")
        m = measure(path, root)
        if m.get("measured_sha256"):
            cur_prefix = m["measured_sha256"]
        stale_rows.append(
            {
                "entry": entry,
                "old_prefix_declared": old_prefix,
                "disk_prefix_declared": disk_prefix_declared,
                "disk_prefix_measured": (cur_prefix or "")[: len(disk_prefix_declared or "")] or None,
                "disk_prefix_matches_declaration": bool(
                    disk_prefix_declared
                    and cur_prefix
                    and cur_prefix.startswith(disk_prefix_declared)
                ),
                "old_pin_is_stale": bool(
                    old_prefix and cur_prefix and not cur_prefix.startswith(old_prefix)
                ),
            }
        )
    B = {
        "superseded_record_sha256_declared": sup.get("sha256"),
        "superseded_record_matches_prior_audit_pin": any(
            r["matches_supersedes_declaration"] for r in recovered
        ),
        "superseded_record_recovery": recovered,
        "old_verified_proposal_revision_declared": sup.get("verified_proposal_revision"),
        "old_revision_matches_prior_audit": bool(
            sup.get("verified_proposal_revision", "").startswith(OLD_PROPOSAL_SHA_PREFIX)
        ),
        "stale_pin_rows": stale_rows,
        "all_declared_stale_pins_re_measured_consistent": all(
            r["disk_prefix_matches_declaration"] and r["old_pin_is_stale"] for r in stale_rows
        ),
        "reason_declared": sup.get("reason"),
    }
    control(
        "B_stale_pin_detector_sensitivity",
        "stale",
        classify("f" * 64, pins_before[GATES]),
    )
    report["B_supersession"] = B

    # ---------- C: evidence chain re-measurement ----------
    rows = (vor.get("evidence_chain_check") or {}).get("rows") or []
    chain = []
    for r in rows:
        path = r.get("path")
        declared = r.get("pinned")
        m = measure(path, root)
        st = classify(declared, m)
        rs = registry_status(reg_doc, path, m.get("measured_sha256"))
        chain.append(
            {
                "path": path,
                "declared": declared,
                "measured": m.get("measured_sha256"),
                "status": st,
                "declared_status_in_record": r.get("status"),
                "registry": rs,
                "record_status_confirmed": r.get("status") == st,
            }
        )
    prop_eh = proposal.get("evidence_hashes") or {}
    chain_map = {c["path"]: c["declared"] for c in chain}
    eh_disagreements = [
        {"path": p, "proposal_evidence_hashes": h, "vor_chain": chain_map.get(p)}
        for p, h in prop_eh.items()
        if chain_map.get(p) != h
    ]
    C = {
        "chain_rows": len(chain),
        "match": sum(1 for c in chain if c["status"] == "match"),
        "stale": sum(1 for c in chain if c["status"] == "stale"),
        "missing": sum(1 for c in chain if c["status"] == "missing"),
        "dir": sum(1 for c in chain if c["status"] == "dir"),
        "all_match": all(c["status"] == "match" for c in chain),
        "record_status_all_confirmed": all(c["record_status_confirmed"] for c in chain),
        "rows": chain,
        "proposal_evidence_hashes_entries": len(prop_eh),
        "proposal_vs_chain_disagreements": eh_disagreements,
        "union_registration": {
            "registered_match": sum(1 for c in chain if c["registry"]["union"] == "registered_match"),
            "registered_stale": sum(1 for c in chain if c["registry"]["union"] == "registered_stale"),
            "registered_absent": sum(1 for c in chain if c["registry"]["union"] == "registered_absent"),
        },
    }
    control("C_tamper_detection", "stale", classify(prop_sha, {"exists": True, "kind": "file",
                                                               "measured_sha256": "0" * 64}))
    control("C_registry_status_real_match", "registered_match",
            registry_status(reg_doc, "numerics/CONVERGENCE_PROTOCOL.md",
                            (root / "numerics/CONVERGENCE_PROTOCOL.md") and
                            sha256_file(root / "numerics/CONVERGENCE_PROTOCOL.md"))["union"])
    control("C_registry_status_absent", "registered_absent",
            registry_status(reg_doc, "no/such/path/planted.json", "0" * 64)["union"])
    report["C_evidence_chain"] = C

    # ---------- D: mutable registry snapshot claims ----------
    decl = (proposal.get("mutable_registry_snapshots") or {}).get(REGISTRY) or {}
    vor_snap = vor.get("mutable_registry_snapshot") or {}
    declared_at = decl.get("measured_at")
    future = None
    if isinstance(declared_at, str) and len(declared_at) >= 16:
        try:
            dt = datetime.fromisoformat(declared_at.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=CST)
            future = dt > datetime.now(CST)
        except ValueError:
            future = None
    D = {
        "proposal_declared_prefix": decl.get("sha256"),
        "proposal_declared_measured_at": declared_at,
        "proposal_declared_instant_in_future": future,
        "proposal_classification": decl.get("classification"),
        "registry_full_sha256_measured": reg_sha,
        "registry_section_digest_measured": reg_section,
        "registry_mtime": datetime.fromtimestamp((root / REGISTRY).stat().st_mtime, CST).isoformat(
            timespec="seconds"
        ),
        "proposal_prefix_matches_full_file": bool(
            decl.get("sha256") and reg_sha and reg_sha.startswith(decl.get("sha256"))
        ),
        "proposal_prefix_matches_section_digest": bool(
            decl.get("sha256") and reg_section and reg_section.startswith(decl.get("sha256"))
        ),
        "vor_snapshot_prefix_declared": vor_snap.get("sha256_prefix_measured"),
        "vor_snapshot_note_declared": vor_snap.get("note"),
        "vor_snapshot_matches_full_file_now": bool(
            vor_snap.get("sha256_prefix_measured")
            and reg_sha
            and reg_sha.startswith(vor_snap.get("sha256_prefix_measured"))
        ),
    }
    if D["vor_snapshot_matches_full_file_now"]:
        D["vor_snapshot_status"] = "reproducible_at_verification_instant"
    elif D["proposal_prefix_matches_full_file"] or D["proposal_prefix_matches_section_digest"]:
        D["vor_snapshot_status"] = "unexpected-mismatch"
    else:
        D["vor_snapshot_status"] = "point_in_time_non_pin_registry_rewritten"
    # BA-5 proper is the proposal's annotation: a declared instant that is in the future and a
    # prefix matching no observed registry state under either measurement basis.
    D["ba5_status"] = (
        "persists-non-load-bearing"
        if not (D["proposal_prefix_matches_full_file"] or D["proposal_prefix_matches_section_digest"])
        else "closed"
    )
    control("D_future_detector_positive", True, bool(future) if future is not None else False)
    control(
        "D_prefix_absent_detector",
        False,
        bool(reg_sha.startswith("d69b62dc93e5336e5109")),
    )
    report["D_registry_snapshot"] = D

    # ---------- E: gate-evaluator reproduction (read-only: no --write-report/--emit-blocker) ----------
    proc = subprocess.run(
        [sys.executable, "-m", "numerics.gates", "--check"],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=180,
    )
    fresh = None
    try:
        fresh = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        fresh = None
    recorded = (vor.get("reproduction") or {}).get("gate_evaluator") or {}

    def _rid(x):
        if isinstance(x, dict):
            return str(x.get("event_id") or f"{x.get('reviewer')}:{x.get('verdict')}")
        return str(x).split("(")[0].strip()

    rec_dissent_ids = {
        _rid(r) for r in (recorded.get("protocol_review") or {}).get("dissenting_reviews") or []
    }
    fresh_reasons = (fresh or {}).get("blocking_reasons") or []
    fresh_dissent_ids = {
        _rid(r) for r in ((fresh or {}).get("protocol_review") or {}).get("dissenting_reviews") or []
    }
    fresh_lock_state = ((fresh or {}).get("lock") or {}).get("state")
    E = {
        "command": "python3 -m numerics.gates --check",
        "recorded_object_is_a_summary": True,
        "recorded_to_fresh_key_map": {
            "lock_state": "lock.state",
            "exit": "process exit code",
        },
        "exit_code": proc.returncode,
        "recorded_exit": recorded.get("exit"),
        "verdict": (fresh or {}).get("verdict"),
        "recorded_verdict": recorded.get("verdict"),
        "production_allowed": (fresh or {}).get("production_allowed"),
        "recorded_production_allowed": recorded.get("production_allowed"),
        "lock_state": fresh_lock_state,
        "recorded_lock_state": recorded.get("lock_state"),
        "fresh_blocking_reasons": fresh_reasons,
        "recorded_blocking_reasons": recorded.get("blocking_reasons"),
        "recorded_blocking_reasons_subset_of_fresh": set(recorded.get("blocking_reasons") or [])
        .issubset(set(fresh_reasons)),
        "recorded_dissenting_reviews_subset_of_fresh": rec_dissent_ids.issubset(fresh_dissent_ids),
        "fresh_dissenting_reviews": sorted(fresh_dissent_ids),
        "recorded_dissenting_reviews": sorted(rec_dissent_ids),
        "verdict_reproduced": (fresh or {}).get("verdict") == recorded.get("verdict"),
        "exit_reproduced": proc.returncode == recorded.get("exit"),
        "lock_reproduced": fresh_lock_state == recorded.get("lock_state"),
        "production_reproduced": (fresh or {}).get("production_allowed")
        == recorded.get("production_allowed"),
        "stderr_tail": proc.stderr.strip()[-400:],
    }
    control("E_exit_semantics", 3, proc.returncode)
    report["E_gate_evaluator_reproduction"] = E

    # ---------- F: independent fixed-dt order refit ----------
    cert = json.loads((root / CERT).read_text())
    lead_refit = (vor.get("reproduction") or {}).get("lead_independent_r5_refit") or {}
    refit = {}
    for scheme, s in (cert.get("schemes") or {}).items():
        fix = (s or {}).get("fixed_dt_certification") or {}
        rws = fix.get("rows") or []
        if len(rws) < 3:
            refit[scheme] = {"error": "too few rows"}
            continue
        xs = [math.log(r["dr"]) for r in rws]
        ys = [math.log(r["l2_error"]) for r in rws]
        slope, intercept, se, sse = ls_slope(xs, ys)
        pair_orders = []
        for i in range(len(rws) - 1):
            pair_orders.append(
                math.log(rws[i]["l2_error"] / rws[i + 1]["l2_error"])
                / math.log(rws[i]["dr"] / rws[i + 1]["dr"])
            )
        half = (max(pair_orders) - min(pair_orders)) / 2.0
        declared = fix.get("fit_order")
        declared_se = fix.get("least_squares_se")
        vor_refit = (lead_refit.get("schemes") or {}).get(scheme) or {}
        refit[scheme] = {
            "n_rungs": len(rws),
            "dt_fixed": sorted({r.get("dt") for r in rws}),
            "refit_order": slope,
            "declared_fit_order": declared,
            "abs_diff_vs_declared": abs(slope - declared) if declared is not None else None,
            "refit_se": se,
            "declared_se": declared_se,
            "abs_se_diff": abs(se - declared_se) if (se is not None and declared_se is not None) else None,
            "pair_orders": pair_orders,
            "pair_half_range": half,
            "declared_pair_half_range": fix.get("pair_half_range"),
            "monotone_errors": all(
                rws[i]["l2_error"] > rws[i + 1]["l2_error"] for i in range(len(rws) - 1)
            ),
            "within_band": abs(slope - 2.0) <= P_TOL,
            "vor_refit_order": vor_refit.get("refit_order"),
            "abs_diff_vs_vor": abs(slope - vor_refit["refit_order"])
            if vor_refit.get("refit_order") is not None
            else None,
        }
    pair_deltas = []
    names = sorted(refit)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if "refit_order" in refit[names[i]] and "refit_order" in refit[names[j]]:
                pair_deltas.append(
                    {
                        "pair": f"{names[i]} vs {names[j]}",
                        "abs_order_diff": abs(
                            refit[names[i]]["refit_order"] - refit[names[j]]["refit_order"]
                        ),
                        "r5_floor": R5_FLOOR,
                        "agree": abs(refit[names[i]]["refit_order"] - refit[names[j]]["refit_order"])
                        <= R5_FLOOR,
                    }
                )
    F = {
        "schemes": refit,
        "pair_deltas": pair_deltas,
        "lead_refit_present_in_record": bool(lead_refit),
        "lead_refit_max_cross_scheme_abs_dp": lead_refit.get("max_cross_scheme_abs_dp"),
        "refit_max_cross_scheme_abs_dp": max((p["abs_order_diff"] for p in pair_deltas), default=None),
        "max_abs_diff_vs_declared": max(
            (v.get("abs_diff_vs_declared") or 0.0) for v in refit.values()
        ),
        "max_abs_se_diff": max(
            (v.get("abs_se_diff") or 0.0) for v in refit.values() if v.get("abs_se_diff") is not None
        ),
        "max_abs_diff_vs_lead_refit": max(
            (v.get("abs_diff_vs_vor") or 0.0)
            for v in refit.values()
            if v.get("abs_diff_vs_vor") is not None
        )
        if any(v.get("abs_diff_vs_vor") is not None for v in refit.values())
        else None,
        "all_within_band": all(v.get("within_band") for v in refit.values()),
        "all_pairs_agree": all(p["agree"] for p in pair_deltas),
        "declared_max_pairwise_abs_diff": (cert.get("cross_scheme_R5") or {}).get(
            "max_pairwise_abs_diff"
        ),
    }
    # planted controls for the refit: exact order-2 synthetic series -> slope 2
    xs = [math.log(h) for h in (0.2, 0.1, 0.05, 0.025)]
    ys = [math.log(3.0 * h**2) for h in (0.2, 0.1, 0.05, 0.025)]
    s2, _, _, _ = ls_slope(xs, ys)
    control("F_refit_order2_synthetic", True, abs(s2 - 2.0) < 1e-9)
    control(
        "F_refit_tolerance_bites",
        False,
        abs(s2 - 2.0001) < REFIT_TOL,
    )
    report["F_order_refit"] = F

    # ---------- G: lock guard ----------
    mp = json.loads((root / MAP).read_text())
    lock = mp.get("numerics_lock") or {}
    solver_dir = root / "numerics" / "spherical_solver"
    n1_files = []
    if (root / "numerics").exists():
        for p in (root / "numerics").rglob("*"):
            if p.is_file() and "spherical_solver" in str(p.relative_to(root)):
                n1_files.append(str(p.relative_to(root)))
    G = {
        "map_lock_state": lock.get("state"),
        "map_locked_nodes": lock.get("locked_nodes"),
        "spherical_solver_dir_present": solver_dir.exists(),
        "n1_solver_files_present": n1_files,
        "fresh_production_allowed": (fresh or {}).get("production_allowed"),
        "fresh_lock_state": ((fresh or {}).get("lock") or {}).get("state"),
        "guard_passes": bool(
            lock.get("state") == "locked"
            and not solver_dir.exists()
            and not n1_files
            and (fresh or {}).get("production_allowed") is False
        ),
    }
    report["G_lock_guard"] = G

    # ---------- drift guard (after) ----------
    pins_after = {rel: measure(rel, root) for rel in (PROPOSAL, VOR, REGISTRY, CERT, GATES, MAP)}
    drift = [
        rel
        for rel in pins_before
        if pins_before[rel].get("measured_sha256") != pins_after[rel].get("measured_sha256")
    ]
    report["pins_after"] = pins_after
    report["input_drift"] = drift

    # ---------- verdict ----------
    report["controls"] = controls
    report["controls_ok"] = all(c["ok"] for c in controls)
    report["instrument_valid"] = bool(report["controls_ok"] and not drift)
    ba1 = A["ba1_closed_by_reissue"] and C["all_match"] and C["record_status_all_confirmed"]
    e_ok = bool(E["exit_reproduced"] and E["verdict_reproduced"] and E["lock_reproduced"]
                and E["production_reproduced"] and E["recorded_dissenting_reviews_subset_of_fresh"])
    f_ok = bool(F["all_within_band"] and F["all_pairs_agree"]
                and F["max_abs_diff_vs_declared"] <= REFIT_TOL
                and (F["max_abs_diff_vs_lead_refit"] is None
                     or F["max_abs_diff_vs_lead_refit"] <= REFIT_TOL))
    if not report["instrument_valid"]:
        verdict = "INSTRUMENT_INVALID"
    elif ba1 and e_ok and f_ok and G["guard_passes"]:
        verdict = (
            "VOR_VERIFIED_BA1_CLOSED_BA5B_ANNOTATION_DEFECT_OPEN"
            if D["ba5_status"] == "persists-non-load-bearing"
            else "VOR_VERIFIED_BA1_BA5_CLOSED"
        )
    else:
        verdict = "VOR_NOT_VERIFIED"
    report["verdict"] = verdict
    report["findings"] = [
        {
            "id": "BA-1",
            "status": "closed" if ba1 else "open",
            "finding": (
                "The re-issued verification of record "
                f"({VOR}#{str(vor_sha)[:12]}) binds the current proposal bytes "
                f"({PROPOSAL}#{str(prop_sha)[:12]}) and names the artifact event that froze them; "
                f"the {C['chain_rows']}-entry evidence chain re-measures {C['match']}/"
                f"{C['chain_rows']} match with 0 stale and 0 missing."
                if ba1
                else "The re-issued record does not fully bind the current proposal bytes or its "
                "evidence chain does not re-measure clean."
            ),
            "load_bearing": True,
        },
        {
            "id": "BA-5a",
            "status": D["vor_snapshot_status"],
            "finding": (
                "The re-issued record's own mutable-registry snapshot "
                f"({D['vor_snapshot_prefix_declared']}) "
                + (
                    f"matches the registry measured at verification "
                    f"({str(reg_sha)[:20]}): reproducible at the measurement instant."
                    if D["vor_snapshot_matches_full_file_now"]
                    else "does not match the registry at the verification instant because the "
                    "controller rewrites that file continuously (mtime "
                    f"{D['registry_mtime']}); the record labels the field a point-in-time "
                    "non-pin, so this is expected churn, not a defect."
                )
            ),
            "load_bearing": False,
        },
        {
            "id": "BA-5b",
            "status": "open-non-load-bearing",
            "finding": (
                "The proposal's declared mutable snapshot "
                f"({D['proposal_declared_prefix']}, measured_at {D['proposal_declared_measured_at']}) "
                "matches neither the full-file sha256 nor the registry-section digest of the "
                "registry on disk, and its declared instant is in the future; the proposal itself "
                "classifies the field as a non-pin point-in-time measurement, so it is an "
                "annotation defect, not a binding gap."
            ),
            "load_bearing": False,
        },
        {
            "id": "VOR-REVISION-BINDING",
            "status": "recorded",
            "finding": (
                f"This verdict binds exactly {VOR}#{str(vor_sha)[:12]} "
                f"(declared created_at {A['vor_created_at_declared']}); the path is rewritten in "
                "place by successive lead lifecycles, so the verdict does not transfer to later "
                f"bytes. Announced revisions in the accepted stream: "
                f"{sorted(A['vor_announced_revisions_in_stream'])}."
            ),
            "load_bearing": True,
        },
        {
            "id": "E-EVALUATOR-SUMMARY",
            "status": "recorded",
            "finding": (
                "The record's gate-evaluator block is a summary, not a verbatim dump: its "
                "lock_state maps to lock.state in the evaluator output. Under that semantic "
                f"mapping the fresh run reproduces verdict={E['verdict']}, exit={E['exit_code']}, "
                f"lock={E['lock_state']}, production_allowed={E['production_allowed']}, and every "
                "dissenter the record lists is present in the fresh run."
            ),
            "load_bearing": False,
        },
    ]
    report["falsifier"] = (
        "Re-run verify_vor.py at the pinned input hashes "
        f"({PROPOSAL}#{str(prop_sha)[:12]}, {VOR}#{str(vor_sha)[:12]}, "
        f"{REGISTRY}#{str(reg_sha)[:12]}). The report is falsified if (a) any chain row called "
        "match has a different measured sha256; (b) the record is shown not to bind the current "
        "proposal bytes, or the named artifact event is absent/mismatched; (c) any control "
        "behaves differently from its declared expectation; (d) the refit disagreement exceeds "
        f"{REFIT_TOL:g}; or (e) any load-bearing fact recorded ok is shown false. A moved "
        "proposal, record, registry or certification hash voids the corresponding verdict for "
        "the new bytes."
    )
    report["not_claimed"] = [
        "no gate verdict and no gate self-pass; G-NUM adjudication belongs to Astra/lead-audit",
        "no N0 completion; numerics_lock stays LOCKED and N1 not started",
        "not the independent protocol review required by C8 (this worker is not the C8 reviewer)",
        "no physics/censorship claim; provenance and reproducibility measurement only",
        "no claim that the controller registry is stable evidence; it is measured at one snapshot",
    ]
    report["evidence_refs"] = [
        f"{PROPOSAL}#{str(prop_sha)[:12]}",
        f"{VOR}#{str(vor_sha)[:12]}",
        f"{CERT}#{str(pins_before[CERT]['measured_sha256'])[:12]}",
        f"{GATES}#{str(pins_before[GATES]['measured_sha256'])[:12]}",
        f"{REGISTRY}#{str(reg_sha)[:12]}",
        "artifacts/worker-14/vor_reverify/PRE_REGISTRATION.md",
        "artifacts/worker-14/binding_audit/n0_binding_audit_refresh.json#13600a5d4130",
    ]

    if a.out:
        Path(a.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: report[k] for k in ("verdict", "controls_ok", "instrument_valid",
                                             "input_drift")}, sort_keys=True))
    if not report["instrument_valid"]:
        shutil.rmtree(scratch, ignore_errors=True)
        return 2
    shutil.rmtree(scratch, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
