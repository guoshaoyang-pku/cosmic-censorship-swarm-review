#!/usr/bin/env python3
"""Lifecycle-10 numerics lead events: record + corrected G-NUM text + blockers + status.

    python3 numerics/protocol/emit_lifecycle10_lead_events.py

Fail-closed: refuses to emit the "closed" gate text if the lifecycle-10 record is
missing, has fails, or does not show all stop-rule items closed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from numerics import events  # noqa: E402

H = events.sha256_file
VERIFY = "numerics/protocol/lifecycle10_lead_verify.json"
GENERATOR = "numerics/protocol/lifecycle10_lead_verify.py"
CERT = "numerics/protocol/n0_fixed_dt_certification.json"
REV3 = "numerics/results/flat_wave_convergence_rev3.json"
L08 = "numerics/protocol/lifecycle08_stoprule_closure_verify.json"
L09 = "numerics/protocol/lifecycle09_lead_verify.json"
PROTO = "numerics/CONVERGENCE_PROTOCOL.md"
GATES = "numerics/gates.py"
F0 = "research_map/formulation_taxonomy.yaml"
AUDIT = "reviews/N0-review-final-verify.json"

V, G = H(VERIFY), H(GENERATOR)
doc = json.loads((REPO / VERIFY).read_text())
if not doc.get("all_items_closed") or doc.get("fails"):
    print(json.dumps({"refused": True, "reason": "lifecycle-10 record not clean",
                      "fails": doc.get("fails")}, indent=1))
    sys.exit(4)

emitted = []


def rec(ev):
    emitted.append(ev)
    print(f"  + {ev['event_type']:<9} {ev['event_id']}")


rec(events.emit_artifact(
    "N0", "n0_lifecycle10_lead_verify_record", VERIFY, "unverified",
    validation_evidence=[
        f"generator {GENERATOR}#{G[:12]}",
        f"{CERT}#{H(CERT)[:12]}", f"{REV3}#{H(REV3)[:12]}", f"{L08}#{H(L08)[:12]}",
        f"{AUDIT}#{H(AUDIT)[:12]}",
        "read-only independent re-measurement: 4 rungs/scheme at fixed dt=1e-4; "
        "adjacent-secant orders + independently re-derived log-log LSQ reproduce the "
        "declared fits exactly; cross-scheme spread 7.958e-05 <= 0.25; fail-closed "
        "guards executed (gates --check exit 3, lock guard exit 0, rev3 verifier exit 0); "
        "B-N0-R2-1 registration gap re-measured and narrowed to 3 foreign-owned paths",
    ],
    event_id=events.det_id("artifact", VERIFY, V, "lifecycle10"),
))
rec(events.emit_artifact(
    "N0", "n0_lifecycle10_lead_verify_generator", GENERATOR, "unverified",
    validation_evidence=[f"{VERIFY}#{V[:12]}",
                         "emits only its own record; imports no builder and no solver"],
    event_id=events.det_id("artifact", GENERATOR, G, "lifecycle10"),
))

# Corrected G-NUM text: verdict stays pending (no self-pass).  The unmet list replaces
# the stale "Stop-rule items open" line with the actually-open audit-stated items.
rec(events.emit(
    "gate",
    {
        "gate_id": "G-NUM",
        "scope": "N0",
        "verdict": "pending",
        "owner": "lead-numerics",
        "criteria": (
            "Independent lifecycle-10 read-only re-measurement at the live hashes "
            f"(record {V[:12]}): stop-rule items 1-3 remain CLOSED -- 4 rungs per "
            "scheme at fixed dt=1e-4 with recomputed fits lffd 1.999943 / cnfd 1.999864 / "
            "cnfem 1.999916, all monotone, all within +/-0.3, cross-scheme spread "
            "7.958e-05 <= R5 0.25; F0 rev5 0abb9ed8a961 live with class AF-WCC-SCALAR-SPH; "
            "3/3 hash-matched replication verdicts at frozen hash da7c36071995. "
            "numerics_lock LOCKED, solver absent, N1 non-active. The N0 accept verdict is "
            "lead-audit-owned and not yet landed; verdict held at pending."
        ),
        "unmet": [
            "N0 verdict on disk is a hash-bound revise 3.5 at da7c36071995 "
            "(reviews/N0-review-final-verify.json#18a0c0d0e77f, re-asserted "
            "audit-l09-review-n0-operative-20260912T011904); the accept is "
            "lead-audit-owned and not yet landed. Stop-rule items are CLOSED "
            f"(closure record 88ec0bf298cb; lifecycle-10 recomputation {V[:12]}; the "
            "audit's own operative verdict marks all three 'closed') -- the previous "
            "'Stop-rule items open' line was stale and is superseded by this event.",
            "Blocking a clean N0 accept, audit-stated and controller-owned: B-N0-R2-1 "
            "PROTOCOL-rule-2 registration gap (re-measured at lifecycle 10: 3 of the 6 "
            "paths named at 00:50 are now registered; the gap is exactly the three "
            "foreign-owned replication verdicts artifacts/worker-046/..., worker-057/..., "
            "worker-081/...) and B-N0-R2-2 review-state supersession semantics at "
            "1e6cdf04d7a2. B-N0-R2-3 (protocol preamble cites superseded pins 66bf917b/"
            "565a6e50) is advisory.",
            "G-NUM passing would certify N0 only; N1 stays locked behind G-FORM + "
            "G-AUDIT. numerics_lock stays LOCKED (guard_present, solver_absent).",
        ],
        "evidence_refs": [
            f"{VERIFY}#{V[:12]}", f"{L08}#{H(L08)[:12]}", f"{L09}#{H(L09)[:12]}",
            f"{REV3}#{H(REV3)[:12]}", f"{CERT}#{H(CERT)[:12]}", f"{F0}#{H(F0)[:12]}",
            f"{PROTO}#{H(PROTO)[:12]}", f"{GATES}#{H(GATES)[:12]}",
            f"{AUDIT}#{H(AUDIT)[:12]}",
        ],
        "controller_note": "verdict pending; text repair only. numerics does not "
                           "self-pass and does not adjudicate the audit verdict or the "
                           "review contest.",
        "eta": "N0 accept: lead-audit; B-N0-R2-1/R2-2: controller disposition",
    },
    event_id=events.det_id("gate", "G-NUM", "N0", "lifecycle10", V),
))

rec(events.emit_blocker(
    "N0",
    "STALE G-NUM UNMET TEXT (medium, controller map text; numerics cannot edit "
    "research_map.json under CF-12). After the 01:22:05 astra-indep2-gate-gnum apply the "
    "G-NUM unmet still reads 'Stop-rule items open: astra-life04-n0-stoprule "
    "(lead-numerics, 02:30) and astra-life04-n0-verify (lead-audit, 03:00)'. All three "
    "stop-rule items are closed by three independent measurements (closure record "
    f"88ec0bf298cb, lifecycle-10 recomputation {V[:12]}) and by the lead-audit's own "
    "operative N0 verdict reviews/N0-review-final-verify.json#18a0c0d0e77f, whose findings "
    "state 'stop-rule items closed'. The cited card astra-life04-n0-verify has landed "
    "(review filed 00:50:20, re-asserted 01:19:04). The lifecycle-10 gate event supplies "
    "the corrected unmet text, so this blocker is dischargeable by applying that event.",
    "Apply the lifecycle-10 G-NUM gate event (it carries the corrected unmet); if any "
    "text survives, replace the stop-rule-open line with the actual open items: N0 "
    "revise 3.5 at da7c36071995 on B-N0-R2-1 (registration) and B-N0-R2-2 (review "
    "supersession). No numerics-side action can or should edit the map.",
    [f"{VERIFY}#{V[:12]}", f"{L08}#{H(L08)[:12]}", f"{AUDIT}#{H(AUDIT)[:12]}",
     "research_map/research_map.json#numerics_lock"],
    severity="medium",
    event_id=events.det_id("blocker", "N0", "stale-gnum-unmet-l10", "lifecycle10", V),
))

rec(events.emit_blocker(
    "N0",
    "REGISTRATION GAP B-N0-R2-1, re-measured and narrowed (medium; controller-owned). "
    "Of the six reviewed paths the audit named absent at 00:50:20, three numerics-owned "
    "paths are now registered with matching hashes (CONVERGENCE_PROTOCOL.md 1e6cdf04d7a2, "
    "flat_wave_convergence.json e9e124227c4d, gates.py fcd1d70991b6). The remaining gap is "
    "exactly the three foreign-owned replication verdicts that the G-NUM criteria cite: "
    "artifacts/worker-046/n0_fixed_dt_independent/verification.json#814452111bc8, "
    "artifacts/worker-057/n0_fixeddt_verify/report.json#b906445878f3, "
    "artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json#65ae766d9e4c. "
    "PROTOCOL rule 2 requires a registered sha256 before any N0 completion claim, and "
    "the registry scan does not cover artifacts/worker-*/.",
    "Controller registers the three measured hashes (or extends the artifact_hashes.json "
    "scan scope to artifacts/worker-*/); numerics cannot register another agent's "
    "artifact.",
    [f"{VERIFY}#{V[:12]}", f"{AUDIT}#{H(AUDIT)[:12]}",
     "runtime/state/artifact_hashes.json"],
    severity="medium",
    event_id=events.det_id("blocker", "N0", "registration-gap-l10", "lifecycle10", V),
))

rec(events.emit_status(
    "N0", "active", 0.06,
    "NUMERICS LEAD LIFECYCLE 10 (one independent read-only pass). Queue: no new owned "
    "card; inbox astra-lead-numerics unchanged since the 01:16 REC-42 notice. Fresh "
    "independent re-verification: all 10 pins match; orders recomputed by a different "
    "estimator (adjacent secants) and an independently re-derived LSQ reproduce the "
    "declared fits exactly (lffd 1.999943 / cnfd 1.999864 / cnfem 1.999916, spread "
    "7.958e-05 <= 0.25); F0 rev5 live; 3/3 replication verdicts hash-matched; guards "
    "fail-closed (gates --check exit 3, lock guard exit 0, rev3 verifier exit 0); "
    "numerics/spherical_solver absent; N1 non-active. New finding L10-F1: live G-NUM "
    "unmet still says 'Stop-rule items open' although the closure record and the audit's "
    "own operative verdict say closed -- corrected unmet supplied via the lifecycle-10 "
    "gate event. Residuals: B-N0-R2-1 registration gap narrowed to the three "
    "foreign-owned verdicts; B-N0-R2-2 supersession semantics controller-owned. No gate "
    "verdict claimed, no node transition, no registered artifact edited.",
    [f"{VERIFY}#{V[:12]}", f"{GENERATOR}#{G[:12]}", f"{L08}#{H(L08)[:12]}",
     f"{REV3}#{H(REV3)[:12]}", f"{AUDIT}#{H(AUDIT)[:12]}"],
    "Any recomputed order leaving |p-2| > 0.3, a non-monotone or non-dt-fixed ladder, "
    "cross-scheme spread > 0.25, a cited verdict's bytes moving off its declared hash, "
    "the live taxonomy leaving F0 rev5, a guard ceasing to fail closed, or "
    "numerics/spherical_solver appearing while numerics_lock == 'locked'.",
    event_id=events.det_id("status", "N0", "lifecycle10", V),
))

rec(events.emit_status(
    "N1", "blocked", 0.02,
    "QUEUE ACK -- card astra-indep2-notice-lock (2026-09-12T01:22:02+08:00) consumed "
    "and acknowledged: numerics_lock stays LOCKED, N1 blocked/forbidden, N0 flat-space "
    "only; no solver written or run, numerics/spherical_solver absent, guards fail-closed. "
    "One precision note on the card text 'Stop-rule items due 02:30/03:00 remain the open "
    "requirement': the three measured stop-rule sub-items are CLOSED (lifecycle-08 closure "
    "88ec0bf298cb + lifecycle-10 recomputation " + V[:12] + "; the lead-audit's own "
    "operative N0 verdict reviews/N0-review-final-verify.json#18a0c0d0e77f records all "
    "three as 'closed'). What remains open is N0 deliverable acceptance: hash-bound revise "
    "3.5 at da7c36071995 on B-N0-R2-1 (registration gap: three foreign-owned verdicts) and "
    "B-N0-R2-2 (review supersession semantics), both controller-owned. Filed as L10-F1 "
    "plus the two lifecycle-10 blockers so the map text and the card wording can be "
    "aligned.",
    [f"{VERIFY}#{V[:12]}", f"{L08}#{H(L08)[:12]}", f"{AUDIT}#{H(AUDIT)[:12]}",
     "comms/inbox/astra-lead-numerics.jsonl#astra-indep2-notice-lock"],
    "Any N1/solver artifact while locked, or the map continuing to assert the stop-rule "
    "sub-items are open when the closure record and the audit's operative verdict say "
    "closed.",
    event_id=events.det_id("status", "N1", "queue-ack-l10", V),
))

rec(events.emit_status(
    "GLOBAL", "done", 0.06,
    "NUMERICS GROUP LEAD LIFECYCLE 10 COMPLETE -- exiting. One independent read-only "
    "lifecycle: no solver code written or run, numerics_lock LOCKED, N1 non-active, "
    "numerics/spherical_solver absent, no gate verdict claimed (G-NUM stays pending on "
    "the lead-audit-owned N0 accept), no node transition, no registered instrument or "
    "other agent's artifact edited. Stop-rule items 1-3 independently re-verified closed; "
    "G-NUM text repaired with the corrected unmet; two blockers handed to the controller "
    "(stale unmet line; registration gap narrowed to three foreign-owned verdicts).",
    [f"{VERIFY}#{V[:12]}", f"{L08}#{H(L08)[:12]}", f"{REV3}#{H(REV3)[:12]}",
     f"{AUDIT}#{H(AUDIT)[:12]}"],
    "A later pass finding drift against these hashes, the G-NUM unmet reverting to the "
    "stop-rule-open wording, or any N1/self-gravity artifact while locked.",
    event_id=events.det_id("status", "GLOBAL", "lifecycle10", V),
))

print(json.dumps({"emitted": len(emitted), "verify_sha256": V, "generator_sha256": G,
                  "event_ids": [e["event_id"] for e in emitted]}, indent=1))
