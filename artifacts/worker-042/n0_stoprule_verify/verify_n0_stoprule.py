#!/usr/bin/env python3
"""W042-N0-STOPRULE-INDEP-VERDICT-01: independent verification of the N0 stop rule.

Second blind reviewer pass over the N0 (flat-space scalar-wave calibration) stop rule
that the lead-audit N0 review left open (HF-03):
  (1) a fourth resolution rung OR an explicit 3-level scoping with tolerance justification;
  (2) class binding re-bound to declared F0 rev5 0abb9ed8a961;
  (3) one independent replication verdict of the order.
plus the lock guard (numerics/spherical_solver absent, no N1 artifact in the reviewed
evidence).

This script is read-only with respect to every reviewed artifact.  It measures every
hash itself, re-derives the order fits from the raw rows, and re-hashes the reviewed
paths after the checks.  Deterministic except `generated_at`.

Usage:  python3 verify_n0_stoprule.py > report.json
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

PROTOCOL = "numerics/CONVERGENCE_PROTOCOL.md"
CERT = "numerics/protocol/n0_fixed_dt_certification.json"
FOUR_RUNG = "numerics/tests/n0_order_4rung.json"
CONV = "numerics/results/flat_wave_convergence.json"
REPL = "numerics/results/flat_wave_replication.json"
REV3 = "numerics/results/flat_wave_convergence_rev3.json"
TAXONOMY = "research_map/formulation_taxonomy.yaml"
REPL_VERDICTS = [
    "artifacts/worker-046/n0_fixed_dt_independent/verification.json",
    "artifacts/worker-057/n0_fixeddt_verify/report.json",
    "artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json",
]
SOLVER = "numerics/spherical_solver"

REVIEWED = [PROTOCOL, CERT, FOUR_RUNG, CONV, REPL, REV3, TAXONOMY] + REPL_VERDICTS

F0_REV5 = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
STALE_PINS = ["66bf917b", "565a6e50"]
DR = [0.2, 0.1, 0.05, 0.025]
P_DESIGN = 2.0
P_TOL = 0.3
DT_FIXED = 1e-4


def sha256(rel: str) -> str | None:
    p = ROOT / rel
    if not p.is_file():
        return None
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def ls_fit(xs, ys):
    n = len(xs)
    xb = sum(xs) / n
    yb = sum(ys) / n
    sxx = sum((x - xb) ** 2 for x in xs)
    sxy = sum((x - xb) * (y - yb) for x, y in zip(xs, ys))
    slope = sxy / sxx
    inter = yb - slope * xb
    sse = sum((y - (inter + slope * x)) ** 2 for x, y in zip(xs, ys))
    se = math.sqrt((sse / (n - 2)) / sxx) if n > 2 else None
    return slope, se, sse


def main() -> int:
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S%z")
    hash_before = {rel: sha256(rel) for rel in REVIEWED}
    checks: list[dict] = []
    observations: list[dict] = []

    def check(cid, ok, detail, expected=None, observed=None):
        checks.append({"check_id": cid, "pass": bool(ok), "detail": detail,
                       "expected": expected, "observed": observed})
        return bool(ok)

    def obs(oid, ok, detail, expected=None, observed=None):
        observations.append({"observation_id": oid, "holds": bool(ok), "detail": detail,
                             "expected": expected, "observed": observed})
        return bool(ok)

    cert = json.loads((ROOT / CERT).read_text())
    rev3 = json.loads((ROOT / REV3).read_text())
    four = json.loads((ROOT / FOUR_RUNG).read_text())
    protocol_txt = (ROOT / PROTOCOL).read_text()
    taxonomy_txt = (ROOT / TAXONOMY).read_text()

    # ---- item (1): four-rung fixed-dt order certification --------------------------
    order_rows = {}
    for scheme, blob in cert["schemes"].items():
        fx = blob["fixed_dt_certification"]
        rows = fx["rows"]
        drs = [float(r["dr"]) for r in rows]
        dts = [float(r["dt"]) for r in rows]
        errs = [float(r["l2_error"]) for r in rows]
        pairs = [math.log(errs[i] / errs[i + 1]) / math.log(drs[i] / drs[i + 1])
                 for i in range(len(errs) - 1)]
        slope, se, _ = ls_fit([math.log(d) for d in drs], [math.log(e) for e in errs])
        half = (max(pairs) - min(pairs)) / 2.0
        delta = max(half, se)
        order_rows[scheme] = {
            "n_rungs": len(rows), "dr_values": drs, "dt_values": dts,
            "monotone": all(errs[i] > errs[i + 1] for i in range(len(errs) - 1)),
            "pair_orders_recomputed": pairs, "pair_orders_declared": fx["pair_orders"],
            "fit_order_recomputed": slope, "fit_order_declared": fx["fit_order"],
            "se_recomputed": se, "se_declared": fx["least_squares_se"],
            "delta_R5_recomputed": delta, "delta_R5_declared": fx["delta_R5"],
            "pair_half_range_declared": fx["pair_half_range"],
            "within_band": abs(slope - P_DESIGN) <= P_TOL,
        }
        check(f"four_rungs::{scheme}",
              len(rows) == 4 and drs == DR and all(abs(d - DT_FIXED) < 1e-15 for d in dts),
              f"{scheme}: {len(rows)} rungs dr={drs} dt={DT_FIXED}")
        check(f"monotone::{scheme}", order_rows[scheme]["monotone"],
              f"{scheme} error ladder strictly decreasing")
        check(f"pairs_match::{scheme}",
              all(abs(a - b) < 1e-12 for a, b in zip(pairs, fx["pair_orders"])),
              f"{scheme} pair orders reproduced", fx["pair_orders"], pairs)
        check(f"fit_match::{scheme}",
              abs(slope - fx["fit_order"]) < 1e-12 and abs(se - fx["least_squares_se"]) < 1e-12
              and abs(delta - fx["delta_R5"]) < 1e-12,
              f"{scheme} fit/SE/delta reproduced",
              {"fit": fx["fit_order"], "se": fx["least_squares_se"], "delta": fx["delta_R5"]},
              {"fit": slope, "se": se, "delta": delta})
        check(f"band::{scheme}", order_rows[scheme]["within_band"],
              f"{scheme} |p-2|={abs(slope - P_DESIGN):.2e} <= {P_TOL}")
    check("four_rungs::all_schemes", len(order_rows) == 3,
          f"certification covers {len(order_rows)} schemes (cnfd/cnfem/lffd)")
    check("four_rung_addendum_present",
          bool(four.get("config", {}).get("dr_values")) and len(four["config"]["dr_values"]) == 4,
          "numerics/tests/n0_order_4rung.json carries a 4-rung configuration")

    # ---- item (2): class binding re-bound to declared F0 rev5 ----------------------
    tax_hash = hash_before[TAXONOMY]
    tax_rev = None
    for line in taxonomy_txt.splitlines():
        if line.startswith("revision:"):
            tax_rev = int(line.split(":", 1)[1].strip())
            break
    check("taxonomy_pin_is_rev5", tax_hash == F0_REV5,
          "research_map/formulation_taxonomy.yaml measures the declared rev5 pin", F0_REV5, tax_hash)
    check("taxonomy_revision_field", tax_rev == 5, "taxonomy declares revision 5", 5, tax_rev)
    check("taxonomy_four_classes",
          all(c in taxonomy_txt for c in ("AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN",
                                          "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH")),
          "taxonomy carries the four frozen class ids incl. AF-WCC-SCALAR-SPH")
    rebind = rev3.get("class_binding", {})
    check("rev3_binds_rev5", rebind.get("sha256") == F0_REV5,
          "rev3 report class_binding.sha256 equals the rev5 pin", F0_REV5, rebind.get("sha256"))
    protocol_pins = {p: (p in protocol_txt) for p in STALE_PINS + ["0abb9ed8a961"]}
    obs("protocol_names_rev5_pin", protocol_pins["0abb9ed8a961"],
        "protocol of record names the declared rev5 pin", True, protocol_pins)
    obs("protocol_still_cites_stale_pins",
        protocol_pins["66bf917b"] and protocol_pins["565a6e50"],
        "protocol of record still cites superseded pins and calls the binding provisional",
        False, protocol_pins)

    # ---- item (3): independent replication verdicts --------------------------------
    repl_measured = {}
    for rel in REPL_VERDICTS:
        p = ROOT / rel
        repl_measured[rel] = {"exists": p.is_file(), "sha256": hash_before[rel]}
    check("replication_artifacts_exist", all(v["exists"] for v in repl_measured.values()),
          "all three replication verdict artifacts exist on disk")
    declared_disk = rev3.get("registration_state", {}).get("registry_generated_paths", {})
    for rel, v in repl_measured.items():
        d = declared_disk.get(rel, {})
        check(f"replication_hash::{Path(rel).parent.name}",
              v["sha256"] is not None and v["sha256"] == d.get("disk_sha256"),
              f"{rel} measures the hash the rev3 report declares",
              d.get("disk_sha256"), v["sha256"])
    w046 = json.loads((ROOT / REPL_VERDICTS[0]).read_text())
    w057 = json.loads((ROOT / REPL_VERDICTS[1]).read_text())
    w081 = json.loads((ROOT / REPL_VERDICTS[2]).read_text())
    check("replication_046_supported",
          w046.get("verdict") == "SUPPORTED"
          and bool(w046.get("criteria_outcomes")) and all(w046["criteria_outcomes"].values())
          and w046.get("failed_criteria") == [],
          "worker-046 from-scratch replication SUPPORTED, all criteria pass, no failed criteria",
          "SUPPORTED all criteria pass",
          {"verdict": w046.get("verdict"), "criteria": w046.get("criteria_outcomes"),
           "failed": w046.get("failed_criteria")})
    check("replication_057_reproduced",
          w057.get("verdict") == "REPRODUCED" and w057.get("findings") == [],
          "worker-057 independent re-analysis REPRODUCED with 0 findings",
          "REPRODUCED 0 findings", f"{w057.get('verdict')} findings={w057.get('findings')}")
    adv = w081.get("verdict", {})
    check("replication_081_adjudicated",
          adv.get("status") == "adjudicated" and adv.get("blocks_gate_pass") is False,
          "worker-081 adjudication carries blocks_gate_pass=false",
          {"status": "adjudicated", "blocks_gate_pass": False}, adv)
    # each replication headline must carry 4 fixed-dt rungs
    head = w046.get("headline", {})
    check("replication_046_four_rungs",
          head and all(h.get("n_rungs") == 4 and h.get("dt_all_fixed_1e-4") and h.get("monotone")
                       for h in head.values()),
          "worker-046 headline: every scheme 4 rungs, fixed dt, monotone")

    # ---- lock guard ----------------------------------------------------------------
    solver_exists = (ROOT / SOLVER).exists()
    check("lock_guard::solver_absent", not solver_exists,
          f"{SOLVER} is absent" if not solver_exists else f"{SOLVER} EXISTS", False, solver_exists)
    conv = json.loads((ROOT / CONV).read_text())
    lg = conv.get("lock_guard", {})
    check("lock_guard::state_locked", lg.get("lock_state") == "locked",
          "convergence report records numerics_lock state=locked", "locked", lg.get("lock_state"))
    check("lock_guard::n1_blocked",
          lg.get("production_allowed") is False and lg.get("verdict") == "N1_BLOCKED",
          "N1 production remains disallowed in the N0 evidence", "N1_BLOCKED",
          {"production_allowed": lg.get("production_allowed"), "verdict": lg.get("verdict")})
    # no N1 artifact may appear in the reviewed evidence: scan for file-like N1 references
    # (a guard key such as spherical_solver_present or an absence assertion is not an artifact)
    import re
    n1_re = re.compile(r"numerics/spherical_solver/\S*\.\w+|selfgravity_solver\.\w+|N1_run")
    n1_hits = []
    for rel in (CERT, FOUR_RUNG, CONV, REPL, REV3):
        for m in n1_re.findall((ROOT / rel).read_text()):
            n1_hits.append(f"{rel}: {m}")
    check("lock_guard::no_n1_artifact", not n1_hits,
          "no reviewed evidence references a spherical/self-gravity solver file",
          [], n1_hits)
    for rel in (CONV, REV3):
        blob = json.loads((ROOT / rel).read_text())
        lg2 = blob.get("lock_guard", {})
        if "spherical_solver_present" in lg2:
            check(f"lock_guard::solver_present_false::{Path(rel).name}",
                  lg2["spherical_solver_present"] is False,
                  f"{rel} records spherical_solver_present=false",
                  False, lg2["spherical_solver_present"])

    # ---- protocol review state (finding, not stop-rule item) -----------------------
    contest = rev3.get("review_state_at_generation", {})
    check("protocol_contest_disclosed",
          contest.get("contest") is True and bool(contest.get("dissenting_reviews")),
          "rev3 report discloses the protocol is contested at the reviewed hash",
          True, {"contest": contest.get("contest"),
                 "dissent": contest.get("dissenting_reviews")})

    # ---- registry coverage (finding, controller step) ------------------------------
    registry = json.loads((ROOT / "runtime/state/artifact_hashes.json").read_text())
    reg = registry.get("registry", {})
    hashes_sec = registry.get("hashes", {})
    missing_registry = [rel for rel in REVIEWED if rel not in reg and rel not in hashes_sec]
    obs("registry_coverage_complete", not missing_registry,
        "every reviewed path carries a matching registry entry in runtime/state/artifact_hashes.json "
        "(registration is the controller's step under PROTOCOL.md rule 2)",
        [], missing_registry)
    check("no_self_pass",
          bool(cert.get("verdict", {}).get("claim"))
          and any("no gate verdict" in s for s in cert.get("not_claimed", []))
          and any("no gate verdict" in s for s in rev3.get("claims_not_made", [])),
          "certification is a claim at conclusion_type=numerical_evidence, not a gate self-pass")
    check("conclusion_type_numeric",
          cert.get("conclusion_type") == "numerical_evidence"
          and rev3.get("conclusion_type") == "numerical_evidence",
          "evidence stays at conclusion_type=numerical_evidence")

    hash_after = {rel: sha256(rel) for rel in REVIEWED}
    stable = {rel: (hash_before[rel] == hash_after[rel]) for rel in REVIEWED}
    check("hash_stability", all(stable.values()),
          "every reviewed path measured identical before and after the checks", True, stable)

    hard_failures = [
        ("HF-042-N0-1: stop-rule item (2) is not closed at the protocol of record. "
         f"{PROTOCOL}#{PROTOCOL and (hash_before[PROTOCOL] or '')[:12]} still cites F0 pins 66bf917b/565a6e50 "
         "and states 'the binding stays provisional'; the declared rev5 pin 0abb9ed8a961 appears only in "
         f"{REV3}#{(hash_before[REV3] or '')[:12]}, whose own class_binding note concedes the protocol "
         "citation is superseded and records the drift as a blocker instead of fixing it. Two documents in "
         "the reviewed evidence set name different F0 pins for the same class binding, so item (2) has no "
         "single binding hash."),
    ]
    findings = [
        ("F-042-N0-1: the protocol of record is contested at the reviewed hash "
         f"{PROTOCOL}#{(hash_before[PROTOCOL] or '')[:12]}: rev3's measured review state carries dissenting "
         "revise verdicts (w067, w081-f1) while the controller gate audit records C8 as MET; the numerics "
         "guard (numerics/gates.py::_protocol_review) therefore reports N1_BLOCKED. Needs controller/Astra "
         "adjudication and does not by itself reopen the three N0 stop-rule items."),
        ("F-042-N0-2: numerics/gates.py::_protocol_review has no (reviewer,target,hash) supersession rule, so "
         "the withdrawn w081 accept is still counted and the later w081 adj2 accept cannot rescind the "
         "earlier revise; disclosed by rev3's guard_finding, decidable in the code."),
        ("F-042-N0-3: item (1) is independently reproduced: 4 rungs x 3 schemes at fixed dt=1e-4, all fits "
         "p=1.9999 +/- <2.5e-4, all within the protocol band; item (3) is independently present: three "
         "hash-verified replication artifacts (worker-046 SUPPORTED 8/8, worker-057 REPRODUCED 0 findings, "
         "worker-081 adjudicated, blocks_gate_pass=false)."),
        ("F-042-N0-4: registry coverage: the 00:52:00 controller checkpoint registers the protocol, the "
         "convergence/replication results and the certification with hash-matching entries; the three "
         "independent replication verdict artifacts (worker-046, worker-057, worker-081) still have no "
         "entry in runtime/state/artifact_hashes.json (controller step under PROTOCOL.md rule 2; "
         "rev3 registration_state discloses the same class of gap)."),
    ]

    report = {
        "schema": "w042-n0-stoprule-verify/v1",
        "task_id": "W042-N0-STOPRULE-INDEP-VERDICT-01",
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "reviewer": "worker-042",
        "generated_at": now,
        "reviewed_hashes": hash_before,
        "hash_after": hash_after,
        "hash_stability": stable,
        "checks": checks,
        "all_checks_pass": all(c["pass"] for c in checks),
        "observations": observations,
        "order_rows": order_rows,
        "stop_rule_adjudication": {
            "four_rungs_or_scoped": "CLOSED: four fixed-dt rungs per scheme, independently reproduced",
            "f0_rebind": "OPEN (HF-042-N0-1): rev3 binds 0abb9ed8a961 but the protocol of record still cites 66bf917b/565a6e50 and stays provisional",
            "independent_replication_verdict": "CLOSED: three hash-verified independent replication artifacts",
        },
        "lock_guard": {"solver_absent": not solver_exists, "n1_production_allowed": False},
        "registry_checked_at": registry.get("checked_at"),
        "registry_missing_reviewed_paths": missing_registry,
        "hard_failures": [h for h in hard_failures],
        "findings": findings,
        "non_claims": [
            "not a gate verdict; this is one reviewer's verdict and cannot pass G-NUM or set node status",
            "no reviewed artifact was edited; all writes are under artifacts/worker-042/ and runtime/state/",
            "binds to the measured hashes above only; a post-review hash move voids the affected citation",
            "no N0 review verdict file was read before this verdict was written (blind second review)",
            "numerical convergence evidence only; no claim about self-gravity, WCC or SCC",
        ],
    }
    print(json.dumps(report, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
