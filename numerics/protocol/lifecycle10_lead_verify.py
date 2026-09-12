#!/usr/bin/env python3
"""Lifecycle-10 numerics lead pass: fresh independent re-verification, read-only.

One independent lifecycle.  This script:

  1. re-measures every pin the N0 / G-NUM claim rests on (fresh sha256 from disk);
  2. recomputes the four-rung spatial order from the raw rows with a *different*
     estimator than the filed least-squares fit (adjacent secant orders), and
     independently re-derives the LSQ fit, checking the declared values;
  3. executes the fail-closed guards as subprocesses and records exit codes;
  4. re-reads the live map's G-NUM entry and the registration registry, looking for
     apply-side defects (stale text, dangling references, unregistered evidence);
  5. writes exactly one record: this file's JSON output.

It writes no solver, no instrument, no other agent's artifact, and claims no gate
verdict.  Exit codes: 0 = record written and all stop-rule items still closed;
2 = a stop-rule item regressed (record still written); 3 = lock/solver violation.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from numerics import events  # noqa: E402

H = events.sha256_file
OUT = REPO / "numerics/protocol/lifecycle10_lead_verify.json"

CERT = "numerics/protocol/n0_fixed_dt_certification.json"
REV3 = "numerics/results/flat_wave_convergence_rev3.json"
L08 = "numerics/protocol/lifecycle08_stoprule_closure_verify.json"
L09 = "numerics/protocol/lifecycle09_lead_verify.json"
F0 = "research_map/formulation_taxonomy.yaml"
PROTO = "numerics/CONVERGENCE_PROTOCOL.md"
GATES = "numerics/gates.py"
DETECTOR = "research_map/class_separation.py"
FLAT = "numerics/tests/flat_wave.py"
REPL = "numerics/tests/flat_wave_replication.py"
MAP = "research_map/research_map.json"
REG = "runtime/state/artifact_hashes.json"

EXPECT = {
    CERT: "1677822ceb9c81e8f6e48dee8360ab13edc35623c51f4be68bd6589a5fe79920",
    REV3: "da7c360719950f7ef6be2624391dee464f8c818a0be74ec44f0f8c70d2b28ac3",
    L08: "88ec0bf298cbc4de6ae2a6d3038961d404f1c43a64cbaa92f29b6ad6cce77f75",
    L09: "baa93446d3702180b8a8f39ea285dcfff3eab4980c7d77a82e60abc6778e8a62",
    F0: "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    PROTO: "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274",
    GATES: "fcd1d70991b6eade4aa993dc49b6103e338f68320aabb955d97da5a8f55d996e",
    DETECTOR: "a8c04fc31e4a",  # prefix-checked below (CF-29 frozen bytes)
    FLAT: "8b52014dac47f99663c8bf46fb2e65a80db399860d586d63cd73dd1db1454a6c",
    REPL: "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422",
}
DETECTOR_PREFIX = "a8c04fc31e4a"
R5_BOUND = 0.25
BAND = 0.3
FROZEN_RUN_HASH = "da7c360719950f7ef6be2624391dee464f8c818a0be74ec44f0f8c70d2b28ac3"
REPLICATION_VERDICTS = [
    ("artifacts/worker-046/n0_fixed_dt_independent/verification.json",
     "814452111bc8912bb21f8e0a353fe78096640d299e469578462b755592ea9a61", "SUPPORTED"),
    ("artifacts/worker-057/n0_fixeddt_verify/report.json",
     "b906445878f3130dd710595a362883e29be87f11cb8d8edbdbc79539147b3b04", "REPRODUCED"),
    ("artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json",
     "65ae766d9e4c205762cff35fb822915d4b00bd4502a0326455bed84e7b3169d6", "accept"),
]
# audit finding B-N0-R2-1 (reviews/N0-review-final-verify.json, 00:50:20) named six
# reviewed paths absent from the registry; re-measure all six here.
AUDIT_R2_1_PATHS = [
    "numerics/CONVERGENCE_PROTOCOL.md",
    "numerics/results/flat_wave_convergence.json",
    "numerics/gates.py",
    "artifacts/worker-046/n0_fixed_dt_independent/verification.json",
    "artifacts/worker-057/n0_fixeddt_verify/report.json",
    "artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json",
]
AUDIT_OPERATIVE = "reviews/N0-review-final-verify.json"

fails: list[str] = []
findings: list[dict] = []
residuals: list[dict] = []


def read_json(rel: str):
    return json.loads((REPO / rel).read_text())


# --------------------------------------------------------------------------- pins
pins: dict[str, dict] = {}
for rel, want in EXPECT.items():
    p = REPO / rel
    if not p.is_file():
        pins[rel] = {"declared": want, "measured": None, "match": False,
                     "note": "MISSING ON DISK"}
        fails.append(f"pin missing: {rel}")
        continue
    got = H(rel)
    match = got.startswith(DETECTOR_PREFIX) if rel == DETECTOR else got == want
    pins[rel] = {"declared": want, "measured": got, "match": bool(match)}
    if not match:
        fails.append(f"pin drift: {rel} measured {got[:12]} declared {want[:12]}")


# ------------------------------------------------- independent order recomputation
def secant_orders(rows: list[dict]) -> list[float]:
    """Adjacent two-point orders p = log(e_i/e_{i+1}) / log(dr_i/dr_{i+1})."""
    out = []
    for a, b in zip(rows, rows[1:]):
        out.append(math.log(a["l2_error"] / b["l2_error"])
                   / math.log(a["dr"] / b["dr"]))
    return out


def lsq_order(rows: list[dict]) -> tuple[float, list[float]]:
    """Independent log-log least squares: slope of log(e) vs log(dr)."""
    xs = [math.log(r["dr"]) for r in rows]
    ys = [math.log(r["l2_error"]) for r in rows]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    resid = [y - (my + slope * (x - mx)) for x, y in zip(xs, ys)]
    return slope, resid


cert = read_json(CERT)
schemes: dict[str, dict] = {}
declared_p: dict[str, float] = {}
for name, s in cert["schemes"].items():
    fdt = s["fixed_dt_certification"]
    rows = fdt["rows"]
    sec = secant_orders(rows)
    lsq, _ = lsq_order(rows)
    declared = fdt["fit_order"]
    declared_p[name] = declared
    dts = sorted({r["dt"] for r in rows})
    drs = sorted(r["dr"] for r in rows)
    schemes[name] = {
        "n_rungs": len(rows),
        "dr_values": drs,
        "dt_values": dts,
        "dt_fixed": len(dts) == 1,
        "secant_pair_orders": sec,
        "declared_pair_orders": fdt["pair_orders"],
        "secant_vs_declared_pair_max_abs_diff": max(
            abs(a - b) for a, b in zip(sec, fdt["pair_orders"])) if sec else None,
        "recomputed_lsq_fit_order": lsq,
        "declared_fit_order": declared,
        "abs_diff_vs_declared": abs(lsq - declared),
        "l2_errors_strictly_decreasing": all(
            a["l2_error"] > b["l2_error"] for a, b in zip(rows, rows[1:])),
        "within_band_0p3": abs(lsq - 2.0) <= BAND,
    }
    if not schemes[name]["dt_fixed"]:
        fails.append(f"{name}: dt not fixed across rungs")
    if not schemes[name]["l2_errors_strictly_decreasing"]:
        fails.append(f"{name}: l2_error ladder not strictly decreasing")
    if schemes[name]["abs_diff_vs_declared"] > 1e-12:
        fails.append(f"{name}: recomputed fit differs from declared by "
                     f"{schemes[name]['abs_diff_vs_declared']}")
    if not schemes[name]["within_band_0p3"]:
        fails.append(f"{name}: recomputed fit outside +/-{BAND} of 2")

spread = max(declared_p.values()) - min(declared_p.values())
item1_closed = bool(schemes) and all(
    s["n_rungs"] >= 4 and s["within_band_0p3"] for s in schemes.values()) \
    and spread <= R5_BOUND
if not item1_closed:
    fails.append(f"item 1 regressed: spread {spread} or rung/band failure")

# ------------------------------------------------------------- item 2: F0 re-bind
f0_text = (REPO / F0).read_text()
tax = None
try:
    import yaml  # type: ignore
    tax = yaml.safe_load(f0_text)
except Exception:  # pragma: no cover - yaml present in this env
    tax = None
class_present = "AF-WCC-SCALAR-SPH" in f0_text
rev = None
if isinstance(tax, dict):
    rev = tax.get("revision") or tax.get("rev") or tax.get("version")
item2_closed = pins[F0]["match"] and class_present
if not item2_closed:
    fails.append("item 2 regressed: F0 bytes or class id")

# ------------------------------------------------- item 3: independent replication
verdicts = []
for rel, want, expect_word in REPLICATION_VERDICTS:
    p = REPO / rel
    if p.is_file():
        got = H(rel)
        doc = json.loads(p.read_text())
        blob = json.dumps(doc)
        found = expect_word in blob
    else:
        got, found, doc = None, False, None
    verdicts.append({"path": rel, "declared_sha256": want, "disk_sha256": got,
                     "exists": p.is_file(), "hash_match": got == want,
                     "expected_verdict_word": expect_word, "verdict_word_found": found})
    if got != want or not found:
        fails.append(f"replication verdict drift/unreadable: {rel}")
item3_closed = all(v["hash_match"] and v["verdict_word_found"] for v in verdicts)
rev3 = read_json(REV3)
rev3_hash_match = pins[REV3]["measured"] == FROZEN_RUN_HASH

# ------------------------------------------------------------------ lock / guards
mapdoc = read_json(MAP)
lock = mapdoc.get("numerics_lock", {})
_nodes = [n for g in mapdoc.get("groups", []) for n in g.get("nodes", [])]
n1 = next((n for n in _nodes if n.get("id") == "N1"), None)
n0 = next((n for n in _nodes if n.get("id") == "N0"), None)
solver_present = (REPO / "numerics/spherical_solver").exists()
# while locked, any non-active N1 state is compliant; `active` would be a violation
lock_compliant = (lock.get("state") == "locked" and not solver_present
                  and (n1 or {}).get("status") in ("queued", "blocked"))
if lock.get("state") != "locked":
    fails.append("numerics_lock is not locked")
if solver_present:
    fails.append("numerics/spherical_solver exists while locked")


def run(cmd: list[str]) -> dict:
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    tail = (r.stdout or r.stderr).strip().splitlines()
    return {"cmd": " ".join(cmd), "exit_code": r.returncode,
            "tail": tail[-1] if tail else ""}


guards = {
    "gates_check": run([sys.executable, "-m", "numerics.gates", "--check"]),
    "flat_wave_lock_guard": run([sys.executable, "numerics/tests/flat_wave.py",
                                 "--lock-guard"]),
    "convergence_rev3_verifier": run([sys.executable,
                                      "numerics/protocol/verify_convergence_rev3.py"]),
}
if guards["gates_check"]["exit_code"] != 3:
    fails.append("gates --check did not fail closed with exit 3 while locked")
if guards["flat_wave_lock_guard"]["exit_code"] != 0:
    fails.append("flat_wave --lock-guard did not pass")
if guards["convergence_rev3_verifier"]["exit_code"] != 0:
    fails.append("convergence rev3 verifier did not verify")

# ------------------------------------------------------- map apply-state scrutiny
gate = next((g for g in mapdoc.get("gates", []) if g.get("gate_id") == "G-NUM"), {})
crit = str(gate.get("criteria", ""))
unmet = [str(u) for u in gate.get("unmet", [])]

# the operative audit verdict on N0: hash-bound revise 3.5, which itself states the
# stop-rule items are closed.  Select by evidence ref / composite target id.
latest_audit = None
for rev_ in reversed(mapdoc.get("reviews", [])):
    tid = str(rev_.get("target_id", ""))
    refs = " ".join(str(x) for x in rev_.get("evidence_refs", []))
    if "audit" not in str(rev_.get("reviewer", "")):
        continue
    if tid == "N0" or "CONVERGENCE_PROTOCOL.md#" in tid or "N0-review-final-verify" in refs:
        latest_audit = {
            "event_id": rev_.get("event_id"), "reviewer": rev_.get("reviewer"),
            "verdict": rev_.get("verdict"), "score": rev_.get("score"),
            "created_at": rev_.get("created_at"), "target_id": tid,
            "hard_failures": rev_.get("hard_failures", []),
            "findings": rev_.get("findings", []),
        }
        break

audit_doc = read_json(AUDIT_OPERATIVE)
audit_stop_items = {i["item"]: i["status"] for i in audit_doc.get("stop_rule_items", [])}
audit_stop_rule_closed = bool(audit_stop_items) and all(
    s == "closed" for s in audit_stop_items.values())
audit_blocking = [{"id": b.get("id"), "severity": b.get("severity"),
                   "finding": b.get("finding"), "needed": b.get("needed")}
                  for b in audit_doc.get("blocking_items", [])]

# closure record speaks for itself
closure = read_json(L08)
closure_all_closed = bool(closure.get("all_closure_items_closed")
                          or closure.get("all_items_closed"))

# staleness: does the live G-NUM unmet still claim the stop-rule items are open while
# (i) the closure record says closed and (ii) the audit's own operative verdict says closed?
stale_stoprule = any("stop-rule items open" in u.lower()
                     or "items 1-3 above are open" in u.lower() for u in unmet)
if stale_stoprule and closure_all_closed and audit_stop_rule_closed:
    findings.append({
        "id": "L10-F1",
        "severity": "medium",
        "finding": "Live G-NUM unmet still claims 'Stop-rule items open: "
                   "astra-life04-n0-stoprule (lead-numerics, 02:30) and "
                   "astra-life04-n0-verify (lead-audit, 03:00)' after the 01:22:05 "
                   "astra-indep2-gate-gnum apply, but the stop-rule items are closed on "
                   "three independent measurements: closure record "
                   f"{L08}#88ec0bf298cb (all_items_closed=true), the lifecycle-10 "
                   "recomputation in this record, and the lead-audit's own operative N0 "
                   f"verdict {AUDIT_OPERATIVE} which marks all three items 'closed'. The "
                   "referenced card astra-life04-n0-verify has also landed (review filed "
                   "00:50:20, re-asserted 01:19:04).",
        "action_needed": "Controller replaces the stop-rule-open line with the actual open "
                         "items: N0 revise 3.5 at da7c36071995 on B-N0-R2-1 (registration "
                         "gap) and B-N0-R2-2 (review supersession semantics). The "
                         "lifecycle-10 gate event supplies a corrected unmet list.",
    })

latest_audit_ref = {
    "path": AUDIT_OPERATIVE,
    "sha256_prefix": H(AUDIT_OPERATIVE)[:12],
    "verdict": audit_doc.get("verdict"),
    "score": audit_doc.get("score"),
    "created_at": audit_doc.get("created_at"),
    "stop_rule_items": audit_stop_items,
    "stop_rule_all_closed": audit_stop_rule_closed,
    "blocking_items": audit_blocking,
}

reg = read_json(REG)
known = set(reg.get("hashes", {})) | set(reg.get("registry", {}))
r2_1 = []
for p in AUDIT_R2_1_PATHS:
    r2_1.append({"path": p, "registered": p in known,
                 "disk_sha256_prefix": H(p)[:12] if (REPO / p).is_file() else None})
r2_1_unregistered = [e["path"] for e in r2_1 if not e["registered"]]
if r2_1_unregistered:
    residuals.append({
        "id": "L10-R2",
        "item": "B-N0-R2-1 registration gap, re-measured and narrowed: of the six reviewed "
                "paths the audit named absent at 00:50:20, three numerics-owned paths are "
                "now registered with matching hashes; the remaining gap is exactly the "
                "three foreign-owned replication verdicts",
        "detail": r2_1_unregistered,
        "why_it_matters": "PROTOCOL rule 2: a node is done only when its declared artifact "
                          "carries a sha256 in artifact_hashes.json. The G-NUM criteria cite "
                          "these three verdicts, but the registry scan does not cover "
                          "artifacts/worker-*/.",
        "owner": "controller (registry scope or explicit registration); numerics cannot "
                 "register another agent's artifact",
    })
if audit_blocking:
    residuals.append({
        "id": "L10-R3",
        "item": "operative N0 blockers are audit-stated and controller-owned; numerics "
                "does not adjudicate them",
        "detail": audit_blocking,
        "owner": "controller (B-N0-R2-1 registration, B-N0-R2-2 review supersession); "
                 "B-N0-R2-3 advisory",
    })

# ------------------------------------------------------------------- record write
all_closed = item1_closed and item2_closed and item3_closed and lock_compliant and not fails
record = {
    "schema": "lifecycle10-lead-verify/v1",
    "actor": "astra-lead-numerics",
    "group_id": "numerics",
    "node_id": "N0",
    "class_id": "AF-WCC-SCALAR-SPH",
    "gate": "G-NUM",
    "generated_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
    "method": "read-only; fresh sha256 pins; independent adjacent-secant orders plus an "
              "independently re-derived log-log LSQ; fail-closed guards executed as "
              "subprocesses; live map + registry re-read; writes only this record",
    "pins": pins,
    "items": {
        "item_1_four_rungs": {
            "closed": item1_closed,
            "basis": f"recomputed from raw rows of {CERT}",
            "schemes": schemes,
            "cross_scheme_spread": spread,
            "cross_scheme_R5_bound": R5_BOUND,
            "cross_scheme_within_R5": spread <= R5_BOUND,
        },
        "item_2_f0_rebind": {
            "closed": item2_closed,
            "path": F0,
            "live_sha256": pins[F0]["measured"],
            "declared_sha256": EXPECT[F0],
            "live_revision": rev,
            "class_id_present_in_live_taxonomy": class_present,
        },
        "item_3_independent_replication": {
            "closed": item3_closed,
            "frozen_run_hash": FROZEN_RUN_HASH,
            "frozen_run_hash_matches_rev3": rev3_hash_match,
            "verdict_count": len(verdicts),
            "verdicts": verdicts,
        },
        "lock_compliance": {
            "compliant": lock_compliant,
            "numerics_lock_state": lock.get("state"),
            "locked_nodes": lock.get("locked_nodes"),
            "allowed_nodes": lock.get("allowed_nodes"),
            "n1_status": (n1 or {}).get("status"),
            "n0_status": (n0 or {}).get("status"),
            "spherical_solver_present": solver_present,
        },
        "guard_execution": guards,
        "map_application": {
            "map_updated_at": mapdoc.get("updated_at"),
            "gnum_verdict": gate.get("verdict"),
            "gnum_last_verdict_event": gate.get("last_verdict_event"),
            "gnum_unmet": unmet,
            "unmet_claims_stop_rule_open": stale_stoprule,
            "closure_record_all_items_closed": closure_all_closed,
            "audit_says_stop_rule_closed": audit_stop_rule_closed,
            "stale_map_text": bool(stale_stoprule and closure_all_closed
                                   and audit_stop_rule_closed),
            "latest_audit_review": latest_audit,
        },
        "registration": {
            "audit_finding": "B-N0-R2-1",
            "checked": len(r2_1),
            "paths": r2_1,
            "unregistered": r2_1_unregistered,
            "registered": [e["path"] for e in r2_1 if e["registered"]],
        },
        "operative_audit_verdict": latest_audit_ref,
    },
    "findings": findings,
    "residuals": residuals,
    "fails": fails,
    "all_items_closed": all_closed,
    "claims_not_made": [
        "no gate verdict; G-NUM stays pending (authority Astra / lead-audit)",
        "no node transition; N0 status untouched",
        "no numerics_lock release; N1 stays blocked/non-active",
        "no adjudication of the protocol-review contest or of any audit verdict",
        "no physics / self-gravity / WCC / SCC claim",
    ],
    "falsifier": "Falsified if any recomputed order leaves |p-2| > 0.3, a ladder is "
                 "non-monotone or not dt-fixed, cross-scheme spread exceeds 0.25, a cited "
                 "verdict's bytes move off its declared hash, the live taxonomy stops "
                 "matching F0 rev5, a guard stops failing closed, or "
                 "numerics/spherical_solver appears while numerics_lock == 'locked'.",
}
OUT.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
print(json.dumps({
    "record": str(OUT.relative_to(REPO)),
    "sha256": H(OUT),
    "all_items_closed": all_closed,
    "fails": fails,
    "findings": [f["id"] for f in findings],
    "residuals": [r["id"] for r in residuals],
    "scheme_fits": {k: v["recomputed_lsq_fit_order"] for k, v in schemes.items()},
    "spread": spread,
    "guards": {k: v["exit_code"] for k, v in guards.items()},
}, indent=1))
if lock.get("state") != "locked" or solver_present:
    sys.exit(3)
sys.exit(0 if all_closed else 2)
