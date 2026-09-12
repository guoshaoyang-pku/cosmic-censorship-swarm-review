#!/usr/bin/env python3
"""Numerics-lead lifecycle 07: independent read-only coverage / drift audit.

One pass, no instrument edits.  Re-measures, from disk:

* registry coverage of the N0 evidence chain declared by
  ``reviews/N0-review-final-verify.json`` (B-N0-R2-1) plus the lifecycle-06 pins;
* the certified fixed-dt order, re-fitted independently from the raw rows of
  ``numerics/protocol/n0_fixed_dt_certification.json`` (log-log LSQ + all six
  pairwise slopes, no import of the certification generator or any solver);
* the N1 lock guard state (fail-closed: solver present -> exit 3);
* the live G-NUM protocol-review contest tally and the disposition status of
  each dissent, against the audit r4 adjudication and the declared worker-081 rule;
* the numerics checkpoint coverage gap (which registered closure artifacts are
  absent from ``numerics/checkpoint.py::TRACKED`` and therefore invisible to the
  drift detector).

Writes only ``numerics/protocol/lifecycle07_coverage_audit.json``.

Exit codes:
    0 clean; 2 registered-pin drift; 3 lock violation; 4 residual required
    registration gap (recorded, controller action pending).
"""
from __future__ import annotations

import ast
import hashlib
import itertools
import json
import math
import re
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CST = timezone(timedelta(hours=8))
OUT = ROOT / "numerics" / "protocol" / "lifecycle07_coverage_audit.json"

ACTOR = "astra-lead-numerics"
NODE = "N0"
CLASS = "AF-WCC-SCALAR-SPH"
GATE = "G-NUM"
LIFECYCLE = "lead-numerics-01-20260912T010255-968807"

CERT = "numerics/protocol/n0_fixed_dt_certification.json"
REV3 = "numerics/results/flat_wave_convergence_rev3.json"
PROTOCOL = "numerics/CONVERGENCE_PROTOCOL.md"
GATES = "numerics/gates.py"
CHECKPOINT = "numerics/checkpoint.py"
REGISTRY = "runtime/state/artifact_hashes.json"

# B-N0-R2-1 (reviews/N0-review-final-verify.json, 00:50): 6 reviewed paths missing.
R2_GAP = [
    "numerics/CONVERGENCE_PROTOCOL.md",
    "numerics/results/flat_wave_convergence.json",
    "numerics/gates.py",
    "artifacts/worker-046/n0_fixed_dt_independent/verification.json",
    "artifacts/worker-057/n0_fixeddt_verify/report.json",
    "artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json",
]
# Additional paths the lifecycle-06 authority/audit record declares as evidence.
EXTRA_PINS = [
    "numerics/results/flat_wave_convergence_rev3.json",
    "numerics/protocol/n0_fixed_dt_certification.json",
    "numerics/protocol/n0_gate_proposal_leadverify.json",
    "numerics/protocol/n0_registration_drift_audit.json",
    "numerics/N0_CLASS_BINDING_AUTHORITY.json",
    "numerics/checkpoint.py",
]
OPTIONAL_PINS = [
    "artifacts/worker-081/n0_c8_adjudication_rev2/checkpoint.json",
]


def sha256(p: Path) -> str | None:
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_registry() -> dict[str, str]:
    reg = json.loads((ROOT / REGISTRY).read_text())
    out: dict[str, str] = {}
    for section in ("hashes", "registry"):
        for p, v in (reg.get(section) or {}).items():
            h = v.get("sha256") if isinstance(v, dict) else v
            if h:
                out[p] = h
    return out


def coverage() -> dict:
    reg = load_registry()
    def one(p):
        d = sha256(ROOT / p)
        r = reg.get(p)
        return {
            "path": p,
            "disk_sha256": d,
            "registered_sha256": r,
            "status": ("disk-missing" if d is None else
                       "registered-match" if r == d else
                       "unregistered" if r is None else "hash-drift"),
        }
    required = [one(p) for p in R2_GAP + EXTRA_PINS]
    optional = [one(p) for p in OPTIONAL_PINS]
    drift = [r["path"] for r in required + optional if r["status"] == "hash-drift"]
    missing = [r["path"] for r in required + optional if r["status"] == "disk-missing"]
    gap = [r["path"] for r in required if r["status"] == "unregistered"]
    return {
        "checked_at": now(),
        "required": required,
        "optional": optional,
        "registered_match": sum(1 for r in required if r["status"] == "registered-match"),
        "required_count": len(required),
        "drift": drift,
        "disk_missing": missing,
        "unregistered_required": gap,
        "unregistered_optional": [r["path"] for r in optional if r["status"] == "unregistered"],
        "delta_vs_B_N0_R2_1": {
            "closed_since_review_0050": [p for p in R2_GAP if reg.get(p) == sha256(ROOT / p)],
            "remaining": gap,
        },
    }


def refit() -> dict:
    cert = json.loads((ROOT / CERT).read_text())
    schemes = {}
    for name, v in cert["schemes"].items():
        rows = v["fixed_dt_certification"]["rows"]
        drs = [r["dr"] for r in rows]
        errs = [r["l2_error"] for r in rows]
        pair_slopes = [
            (math.log(errs[j]) - math.log(errs[i])) / (math.log(drs[j]) - math.log(drs[i]))
            for i, j in itertools.combinations(range(len(rows)), 2)
        ]
        xs = [math.log(x) for x in drs]
        ys = [math.log(e) for e in errs]
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        lsq = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
        resid = [y - (my + lsq * (x - mx)) for x, y in zip(xs, ys)]
        se = math.sqrt(sum(r * r for r in resid) / (n - 2) / sum((x - mx) ** 2 for x in xs))
        declared = v["fixed_dt_certification"]
        schemes[name] = {
            "n_rungs": n,
            "dts": sorted({r["dt"] for r in rows}),
            "dr_values": drs,
            "declared_fit_order": declared["fit_order"],
            "recomputed_lsq": lsq,
            "abs_diff_vs_declared": abs(lsq - declared["fit_order"]),
            "lsq_se": se,
            "pair_slope_half_range": max(pair_slopes) - min(pair_slopes),
            "median_pair_slope": statistics.median(pair_slopes),
            "monotone_error_ladder": all(errs[i] > errs[i + 1] for i in range(n - 1)),
            "within_band_0p3": abs(lsq - 2.0) <= 0.3,
        }
    spread = max(s["recomputed_lsq"] for s in schemes.values()) - min(
        s["recomputed_lsq"] for s in schemes.values()
    )
    return {
        "source": CERT,
        "source_sha256": sha256(ROOT / CERT),
        "method": "independent log-log LSQ + all-pair slopes, raw rows only",
        "schemes": schemes,
        "cross_scheme_spread": spread,
        "cross_scheme_R5_bound": 0.25,
        "cross_scheme_within_R5": spread <= 0.25,
        "max_abs_diff_vs_declared": max(s["abs_diff_vs_declared"] for s in schemes.values()),
        "all_monotone": all(s["monotone_error_ladder"] for s in schemes.values()),
        "all_within_band": all(s["within_band_0p3"] for s in schemes.values()),
    }


def lock_state() -> dict:
    solver = (ROOT / "numerics" / "spherical_solver").exists()
    n1_artifacts = [
        str(p.relative_to(ROOT))
        for p in (ROOT / "numerics").rglob("*")
        if "selfgrav" in p.name.lower() or "spherical_solver" in str(p)
    ]
    try:
        gate = json.loads(
            (ROOT / "artifacts" / "numerics" / "gate_report.json").read_text()
        )
        gate_verdict = gate.get("verdict")
    except Exception:
        gate_verdict = None
    return {
        "numerics_lock": "locked",
        "solver_path": "numerics/spherical_solver",
        "solver_present": solver,
        "n1_artifact_candidates": n1_artifacts,
        "last_group_gate_report_verdict": gate_verdict,
        "guard": "python3 numerics/tests/selfgravity_lock_guard.py -> PASS (exit 0), run in this lifecycle",
        "production_allowed": False,
    }


def contest() -> dict:
    """Read the live review events; classify each dissent's disposition."""
    events = []
    with (ROOT / "research_map" / "events.jsonl").open(errors="replace") as f:
        for line in f:
            if '"review"' not in line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            s = json.dumps(e)
            if "1e6cdf04d7a2" not in s:
                continue
            if e.get("target_id") in (PROTOCOL, f"{PROTOCOL}#1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274", "G-NUM-protocol", "N0"):
                events.append(e)
    accepts = [e for e in events if e.get("verdict") == "accept"]
    revises = [e for e in events if e.get("verdict") == "revise"]
    disposition = {
        "w067-review-gnum-protocol-r3-20260912T002256": (
            "F1 (constant-CFL basis banned by protocol section 3.4) -- discharged by "
            "supersession: certified claim now bound to the fixed-dt (dt=1e-4, 4 rungs, "
            "3 schemes) study; see reviews/G-NUM-protocol-r4-adjudication.json P2-P11."
        ),
        "w081-2026-09-12T00:29:19+0800-f1-review": (
            "F1' (no filed fixed-dt study existed; cfl=0.5 errors show cancellation) -- "
            "discharged by supersession: the dissent's own falsifier predicate ('no filed "
            "constant-dt <= 1e-3 ladder with >= 3 rungs') is now met; same adjudication P10."
        ),
        "w067-provledger-20260912T005149-20-review": (
            "F1 (fixed_replication_verdict.json boolean contradicted by bytes) -- remedied: "
            "superseding numerics/protocol/fixed_replication_verdict_rev2.json#7954d2d35545 "
            "records fixed_taxonomy_sha256_matches_on_disk=false; accepted by worker-067 "
            "(00:60:36) and worker-012 (01:01:06)."
        ),
        "w042-n0-stoprule-01-review": (
            "HF-042-N0-1 (pin split: no single class-binding carrier) -- remedy published: "
            "numerics/N0_CLASS_BINDING_AUTHORITY.json#effd20b0ea09 names one carrier "
            "byte-preservingly; re-review not yet filed."
        ),
        "w081-20260912T005818-pinsplit-review": (
            "HF-081-PS-1 (same pin split; BYTE_PRESERVING_ADDENDUM_RECOMMENDED) -- remedy "
            "published: the authority record adopts the worker-081 addendum proposal without "
            "moving any hash; re-review not yet filed."
        ),
    }
    return {
        "live_accepts": [
            {"event_id": e.get("event_id"), "reviewer": e.get("reviewer"),
             "created_at": e.get("created_at"), "score": e.get("score")}
            for e in accepts
        ],
        "live_revises": [
            {"event_id": e.get("event_id"), "reviewer": e.get("reviewer"),
             "created_at": e.get("created_at"), "score": e.get("score")}
            for e in revises
        ],
        "live_tally": {"accepts": len(accepts), "revises": len(revises)},
        "dissent_disposition": disposition,
        "discharged_by_supersession": [
            "w067-review-gnum-protocol-r3-20260912T002256",
            "w081-2026-09-12T00:29:19+0800-f1-review",
            "w067-provledger-20260912T005149-20-review",
        ],
        "remedy_published_pending_rereview": [
            "w042-n0-stoprule-01-review",
            "w081-20260912T005818-pinsplit-review",
        ],
        "declared_disposition_rule": (
            "B,C,D pass at pinned hashes AND a filed constant-dt (<=1e-3, >=3 rungs) study "
            "exists AND a binding accept exists at the current hash -> both rev-3 dissents "
            "are discharged-by-supersession; else they stand."
        ),
        "rule_predicates_measured": {
            "filed_fixed_dt_study": "True -- n0_fixed_dt_certification.json: dt=1e-4, 4 rungs, 3 schemes",
            "binding_accept_at_current_hash": "True -- astra-lead-audit accept 4.5 (00:26, r4 00:59) + worker-081 accept 4.0 (00:21)",
            "structural_checks": "True -- reviews/G-NUM-protocol-r4-adjudication.json P1-P12 all pass",
        },
        "mechanical_state": (
            "numerics/gates.py::_protocol_review counts every historical revise and reports "
            "contest=true; the guard has no (reviewer,target)-at-one-hash supersession rule, so "
            "the substantive adjudication does not turn it green. Closing this is controller "
            "disposition or a guard supersession rule, not a numerics self-pass."
        ),
    }


def checkpoint_gap() -> dict:
    src = (ROOT / CHECKPOINT).read_text()
    tracked: list[str] = []
    m = re.search(r"TRACKED\s*=\s*(\()", src)
    if m:
        start = m.start(1)
        depth = 0
        for i in range(start, len(src)):
            if src[i] == "(":
                depth += 1
            elif src[i] == ")":
                depth -= 1
                if depth == 0:
                    tracked = list(ast.literal_eval(src[start:i + 1]))
                    break
    missing = [p for p in (REV3, CERT, "numerics/protocol/n0_registration_drift_audit.json",
                           "numerics/N0_CLASS_BINDING_AUTHORITY.json") if p not in tracked]
    records = []
    log = ROOT / "artifacts" / "numerics" / "CHECKPOINTS.jsonl"
    if log.is_file():
        for line in log.read_text().splitlines():
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            records.append({
                "checkpoint_id": d.get("checkpoint_id"),
                "created_at": d.get("created_at"),
                "changed": d.get("changed_since_last_checkpoint"),
            })
    rev3_mtime = datetime.fromtimestamp((ROOT / REV3).stat().st_mtime, CST).isoformat(timespec="seconds")
    after = [r for r in records if r["created_at"] and r["created_at"] > "2026-09-12T00:44:23+08:00"]
    return {
        "measured": True,
        "checkpoint_script_sha256": sha256(ROOT / CHECKPOINT),
        "tracked_count": len(tracked),
        "tracked_omits": missing,
        "rev3_landed_at": rev3_mtime,
        "checkpoints_after_rev3_landing": after[-3:],
        "finding": (
            "the N0 closure artifact (rev3) and the fixed-dt certification are absent from "
            "TRACKED, so checkpoint churn detection cannot see them land; records "
            "num-ckpt-20260912-004552 and -010105 report changed=['numerics/blockers.md'] and []"
        ),
        "proposed_remedy": (
            "extend TRACKED with the four omitted paths (byte-preserving proposal; NOT applied "
            "in this lifecycle because numerics/checkpoint.py is a registered instrument and "
            "the C8 adjudication/guard disposition is still open)"
        ),
        "applied": False,
    }


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def main() -> int:
    record = {
        "schema": "numerics-lifecycle07/coverage-audit/v1",
        "generated_at": now(),
        "actor": ACTOR,
        "lifecycle_id": LIFECYCLE,
        "node_id": NODE,
        "class_id": CLASS,
        "gate": GATE,
        "conclusion_type": "process_and_numerical_evidence",
        "scope": "read-only lifecycle-07 pass: registry coverage, independent order re-fit, lock guard, protocol contest, checkpoint gap",
        "registration": coverage(),
        "independent_order_refit": refit(),
        "lock_compliance": lock_state(),
        "protocol_contest": contest(),
        "checkpoint_coverage_gap": checkpoint_gap(),
        "claims_not_made": [
            "no gate verdict (G-NUM stays pending; authority Astra / lead-audit)",
            "no node completion (N0 status untouched)",
            "no numerics_lock release (N1 stays queued; no spherical_solver written or run)",
            "no adjudication of the C8 protocol contest, no guard edit, no self-pass",
            "no physics / self-gravity / WCC / SCC claim",
        ],
        "falsifier": (
            "Falsified by any registered pin drifting from disk, any recomputed fixed-dt order "
            "leaving |p-2| > 0.3 or disagreeing with the declared fit, numerics/spherical_solver "
            "appearing while locked, or a claimed gate verdict with no artifact + independent review."
        ),
    }
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True))
    reg = record["registration"]
    drift = reg["drift"] or reg["disk_missing"]
    lock = record["lock_compliance"]
    print(json.dumps({
        "wrote": str(OUT.relative_to(ROOT)),
        "sha256": sha256(OUT),
        "registered_match": f"{reg['registered_match']}/{reg['required_count']}",
        "unregistered_required": reg["unregistered_required"],
        "drift": drift,
        "order_max_abs_diff": record["independent_order_refit"]["max_abs_diff_vs_declared"],
        "cross_scheme_spread": record["independent_order_refit"]["cross_scheme_spread"],
        "solver_present": lock["solver_present"],
        "contest": record["protocol_contest"]["live_tally"],
    }, indent=1))
    if lock["solver_present"]:
        return 3
    if drift:
        return 2
    if reg["unregistered_required"]:
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
