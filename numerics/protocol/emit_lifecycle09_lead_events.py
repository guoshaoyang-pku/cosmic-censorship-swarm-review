#!/usr/bin/env python3
"""Lifecycle-09 lead events: independent re-verification + one map-state finding.

    python3 numerics/protocol/emit_lifecycle09_lead_events.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from numerics import events  # noqa: E402

H = events.sha256_file
VERIFY = "numerics/protocol/lifecycle09_lead_verify.json"
GENERATOR = "numerics/protocol/lifecycle09_lead_verify.py"
CERT = "numerics/protocol/n0_fixed_dt_certification.json"
REV3 = "numerics/results/flat_wave_convergence_rev3.json"
L08 = "numerics/protocol/lifecycle08_stoprule_closure_verify.json"
PROTO = "numerics/CONVERGENCE_PROTOCOL.md"
GATES = "numerics/gates.py"
F0 = "research_map/formulation_taxonomy.yaml"

V, G = H(VERIFY), H(GENERATOR)
emitted = []


def rec(ev):
    emitted.append(ev)
    print(f"  + {ev['event_type']:<9} {ev['event_id']}")


rec(events.emit_artifact(
    "N0", "n0_lifecycle09_lead_verify_record", VERIFY, "unverified",
    validation_evidence=[
        f"generator {GENERATOR}#{G[:12]}",
        f"{CERT}#{H(CERT)[:12]}", f"{REV3}#{H(REV3)[:12]}", f"{L08}#{H(L08)[:12]}",
        "read-only independent recomputation: 4 rungs/scheme, dt fixed 1e-4, log-log LSQ "
        "recomputed from raw rows; max |dp| vs declared 0.0; spread 7.958e-05 <= 0.25; "
        "F0 rev5 live; 3/3 replication verdicts hash-matched; solver absent",
    ],
    event_id=events.det_id("artifact", VERIFY, V, "lifecycle09"),
))
rec(events.emit_artifact(
    "N0", "n0_lifecycle09_lead_verify_generator", GENERATOR, "unverified",
    validation_evidence=[f"{VERIFY}#{V[:12]}",
                         "emits only its own record; imports no builder and no solver"],
    event_id=events.det_id("artifact", GENERATOR, G, "lifecycle09"),
))

rec(events.emit_gate(
    "G-NUM", "N0", "pending",
    "Independent lifecycle-09 re-measurement at the current hashes, proposed to Astra (NOT a "
    "self-pass). Stop-rule items 1-3 are CLOSED by fresh measurement: (1) order measured = MET, "
    "4 rungs per scheme at fixed dt=1e-4, recomputed fits lffd 1.999943 / cnfd 1.999864 / "
    "cnfem 1.999916, max |dp| vs declared 0.0, all monotone, all within +/-0.3; (2) F0 re-bind = "
    "MET, live taxonomy 0abb9ed8a961 rev5 with class AF-WCC-SCALAR-SPH present; (3) independent "
    "replication = MET, three hash-matched verdicts (W046 SUPPORTED, W057 REPRODUCED, W081 "
    "accept) at frozen run hash da7c36071995. The map's G-NUM criteria and unmet[1] still describe "
    "items 1-3 as open (see blocker lnum-blocker-lifecycle09-map-stale-gnum). Remaining: the N0 "
    "accept verdict is lead-audit-owned (astra-life04-n0-verify); the protocol review is contested "
    "at 1e6cdf04; numerics_lock stays LOCKED and N1 stays queued regardless. Verdict held at "
    "pending: numerics does not self-pass and does not claim the N0 node.",
    [f"{VERIFY}#{V[:12]}", f"{L08}#{H(L08)[:12]}", f"{REV3}#{H(REV3)[:12]}",
     f"{CERT}#{H(CERT)[:12]}", f"{F0}#{H(F0)[:12]}", f"{PROTO}#{H(PROTO)[:12]}",
     f"{GATES}#{H(GATES)[:12]}"],
    event_id=events.det_id("gate", "G-NUM", "N0", "lifecycle09", V),
))

rec(events.emit_blocker(
    "N0",
    "STALE MAP TEXT (medium, controller action; numerics cannot edit research_map.json under "
    "CF-12 one-canonical-path/one-owner). research_map.json still carries the pre-closure G-NUM "
    "text in 3 places at map updated_at 2026-09-12T01:16:26+08:00, after the astra-life08-gate-gnum "
    "pass: unmet[1] reads 'Stop-rule items 1-3 above are open (astra-life04-n0-stoprule, "
    "lead-numerics, 02:30; astra-life04-n0-verify, lead-audit, 03:00)' and the G-NUM criteria string "
    "still says the deliverable 'still needs: (1) a fourth resolution rung ... (2) class re-binding "
    "... (3) one independent replication verdict'. All three are closed and independently "
    "re-verified by two separate lead passes (lifecycle-08 and this lifecycle-09 fresh "
    "recomputation). The only genuinely open N0 item is the lead-audit accept (astra-life04-n0-verify).",
    "Astra refreshes the G-NUM entry in research_map/research_map.json: replace the items-1-3-open "
    "text in criteria + unmet[1] with 'stop-rule items 1-3 closed at da7c36071995 / "
    "0abb9ed8a961 (closure record 88ec0bf298cb + lifecycle-09 re-measurement)'; keep the gate "
    "verdict pending on the lead-audit N0 accept. No numerics-side action can or should edit the map.",
    [f"{VERIFY}#{V[:12]}", f"{L08}#{H(L08)[:12]}", f"{REV3}#{H(REV3)[:12]}",
     "research_map/research_map.json#numerics_lock"],
    severity="medium",
    event_id=events.det_id("blocker", "N0", "map-stale-gnum", "lifecycle09", V),
))

rec(events.emit_status(
    "N0", "active", 0.05,
    "NUMERICS LEAD LIFECYCLE 09 (one independent read-only pass). Queue: no new owned card "
    "(inbox astra-lead-numerics unchanged since 00:36; astra-life04-n0-stoprule already "
    "discharged by lifecycle-08). Fresh independent re-measurement of the N0 stop-rule closure: "
    "4 rungs/scheme recomputed from raw rows (max |dp| 0.0), F0 rev5 live and class present, 3/3 "
    "replication verdicts hash-matched at frozen hash da7c36071995 -- all three items closed. "
    "New finding L09-F1: the map's G-NUM criteria + unmet[1] still carry pre-closure text; filed "
    "as a medium blocker for Astra. Residuals: gates.py pin 907a88b141bf4394 still cited 6x "
    "elsewhere in the map while disk is fcd1d70991b6; W046/W057/W081 verdicts unregistered in "
    "artifact_hashes.json. Lock guard PASS (self-test PASS, planted solver FAIL), "
    "gates --check exit 3 N1_BLOCKED, numerics/spherical_solver absent, N1 queued. No gate "
    "verdict claimed, no node transition, no registered artifact edited.",
    [f"{VERIFY}#{V[:12]}", f"{GENERATOR}#{G[:12]}", f"{L08}#{H(L08)[:12]}",
     f"{REV3}#{H(REV3)[:12]}", f"{CERT}#{H(CERT)[:12]}"],
    "Any recomputed fit leaving |p-2| > 0.3, a non-monotone ladder, cross-scheme spread > 0.25, "
    "a cited verdict's bytes moving off its declared hash, the live taxonomy leaving F0 rev5, or "
    "numerics/spherical_solver appearing while numerics_lock == 'locked'.",
    event_id=events.det_id("status", "N0", "lifecycle09", V),
))

rec(events.emit_status(
    "GLOBAL", "done", 0.05,
    "NUMERICS GROUP LEAD LIFECYCLE 09 COMPLETE -- exiting. One independent read-only pass: no "
    "solver code written or run, numerics_lock LOCKED, N1 queued, numerics/spherical_solver "
    "absent, no gate verdict claimed (G-NUM stays pending, pending the lead-audit N0 accept), no "
    "node transition, no registered instrument or other agent's artifact edited. Stop-rule items "
    "1-3 independently re-verified closed; one medium map-staleness blocker handed to Astra; "
    "residuals are the superseded gates.py pin and three unregistered replication verdicts.",
    [f"{VERIFY}#{V[:12]}", f"{L08}#{H(L08)[:12]}", f"{REV3}#{H(REV3)[:12]}"],
    "A later pass finding drift against these hashes, or any N1/self-gravity artifact while locked.",
    event_id=events.det_id("status", "GLOBAL", "lifecycle09", V),
))

print(json.dumps({"emitted": len(emitted), "verify_sha256": V, "generator_sha256": G,
                  "event_ids": [e["event_id"] for e in emitted]}, indent=1))
