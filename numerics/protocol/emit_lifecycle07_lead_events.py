#!/usr/bin/env python3
"""Numerics-lead lifecycle 07 structured events (one independent pass, then exit).

Deterministic event ids make re-running idempotent (``numerics.events.emit`` returns
the already-appended event instead of duplicating it).

    python3 numerics/protocol/emit_lifecycle07_lead_events.py
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from numerics import events  # noqa: E402

H = events.sha256_file
INSTANCE = REPO / "runtime/instances/lead-numerics-01-20260912T010255-968807/meta.json"
STARTED = json.loads(INSTANCE.read_text())["started_at"] if INSTANCE.is_file() else None
if STARTED:
    HOURS = round(max((time.time() - datetime.fromisoformat(STARTED).timestamp()) / 3600.0, 0.01), 3)
else:
    HOURS = 0.1

AUDIT = "numerics/protocol/lifecycle07_coverage_audit.json"
GENERATOR = "numerics/protocol/lifecycle07_coverage_audit.py"
LIFECYCLE = "artifacts/numerics/lifecycle_07_20260912.json"
REV3 = "numerics/results/flat_wave_convergence_rev3.json"
CERT = "numerics/protocol/n0_fixed_dt_certification.json"
AUTHORITY = "numerics/N0_CLASS_BINDING_AUTHORITY.json"
PROTOCOL = "numerics/CONVERGENCE_PROTOCOL.md"
CHECKPOINT = "numerics/checkpoint.py"
REGISTRY = "runtime/state/artifact_hashes.json"
W046 = "artifacts/worker-046/n0_fixed_dt_independent/verification.json"
W057 = "artifacts/worker-057/n0_fixeddt_verify/report.json"
W081 = "artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json"
ADJ = "reviews/G-NUM-protocol-r4-adjudication.json"
FINALVERIFY = "reviews/N0-review-final-verify.json"

audit = json.loads((REPO / AUDIT).read_text())
refit = audit["independent_order_refit"]
reg = audit["registration"]
contest = audit["protocol_contest"]
ckpt = audit["checkpoint_coverage_gap"]

lifecycle_record = {
    "schema": "numerics-lead-lifecycle/v1",
    "lifecycle_id": "lead-numerics-07",
    "instance": INSTANCE.stem,
    "actor": "astra-lead-numerics",
    "group_id": "numerics",
    "started_at": STARTED,
    "closed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    "mode": "one independent lifecycle; read-only on all canonical paths; then exit",
    "queue_consumed": {
        "new_owned_cards": [],
        "note": (
            "comms/inbox/astra-lead-numerics.jsonl unchanged (9 lines, last card "
            "astra-life04-n0-stoprule 00:36, deadline 02:30, discharged by the rev-3 report). "
            "astra-life04-n0-verify and astra-life05-gnum-protocol-adjudication are "
            "audit-owned; no card assigns new numerics work."
        ),
    },
    "deliverables": {
        AUDIT: {"sha256": H(AUDIT), "role": "read-only coverage/drift audit of this pass"},
        GENERATOR: {"sha256": H(GENERATOR), "role": "stdlib-only generator; exit 2 drift, 3 lock violation, 4 residual registration gap"},
    },
    "verification": {
        "registration": {
            "required_checked": reg["required_count"],
            "registered_match": reg["registered_match"],
            "drift": reg["drift"],
            "unregistered_required": reg["unregistered_required"],
            "delta_vs_B_N0_R2_1": reg["delta_vs_B_N0_R2_1"],
        },
        "independent_order_refit": {
            "method": refit["method"],
            "max_abs_diff_vs_declared": refit["max_abs_diff_vs_declared"],
            "cross_scheme_spread": refit["cross_scheme_spread"],
            "cross_scheme_R5_bound": refit["cross_scheme_R5_bound"],
            "all_monotone": refit["all_monotone"],
            "all_within_band": refit["all_within_band"],
        },
        "lock": audit["lock_compliance"],
        "protocol_contest": {
            "live_tally": contest["live_tally"],
            "discharged_by_supersession": contest["discharged_by_supersession"],
            "remedy_published_pending_rereview": contest["remedy_published_pending_rereview"],
            "mechanical_state": contest["mechanical_state"],
        },
        "checkpoint_coverage_gap": {
            "tracked_omits": ckpt["tracked_omits"],
            "applied": ckpt["applied"],
        },
    },
    "claims_not_made": audit["claims_not_made"],
    "falsifier": audit["falsifier"],
}
(REPO / LIFECYCLE).write_text(json.dumps(lifecycle_record, indent=1, sort_keys=True))

emitted = []


def rec(ev):
    emitted.append(ev)
    print(f"  + {ev['event_type']:<9} {ev['event_id']}")


# ------------------------------------------------------------------ artifacts
rec(events.emit_artifact(
    "N0", "lifecycle07_coverage_audit", AUDIT, "unverified",
    validation_evidence=[f"{GENERATOR}#{H(GENERATOR)[:12]}",
                         f"{CERT}#{H(CERT)[:12]}", f"{REV3}#{H(REV3)[:12]}"],
    event_id=events.det_id("artifact", AUDIT, H(AUDIT)),
))
rec(events.emit_artifact(
    "N0", "lifecycle07_coverage_audit_generator", GENERATOR, "unverified",
    validation_evidence=[f"{AUDIT}#{H(AUDIT)[:12]}"],
    event_id=events.det_id("artifact", GENERATOR, H(GENERATOR)),
))
rec(events.emit_artifact(
    "GLOBAL", "numerics_lead_lifecycle_record", LIFECYCLE, "unverified",
    validation_evidence=[f"{AUDIT}#{H(AUDIT)[:12]}"],
    event_id=events.det_id("artifact", LIFECYCLE, H(LIFECYCLE)),
))

# ---------------------------------------------------------------------- claim
rec(events.emit_claim(
    "AF-WCC-SCALAR-SPH",
    "Independent lifecycle-07 re-fit at the frozen fixed-dt evidence basis: from the raw "
    "rows of numerics/protocol/n0_fixed_dt_certification.json (dt=1e-4 exactly, 4 rungs "
    "dr=0.2/0.1/0.05/0.025, three schemes) my own log-log least squares reproduces the "
    f"declared fit orders exactly (max |dp| = {refit['max_abs_diff_vs_declared']:.3e}); every "
    "error ladder is monotone; max cross-scheme spread "
    f"{refit['cross_scheme_spread']:.3e} <= R5 bound {refit['cross_scheme_R5_bound']}; all "
    "schemes inside |p-2| <= 0.3. Nothing in this pass imports the certification generator "
    "or any solver. Separately, the B-N0-R2-1 registration gap narrowed from 6 paths (00:50) "
    "to 3 required paths (this pass): the protocol, flat_wave_convergence.json and gates.py "
    "are now registry-matched; W046/W057/W081 verdicts remain unregistered.",
    "numerical_evidence",
    [
        "flat-space scalar-wave calibration only; no self-gravity, no coupling to geometry",
        "order certified at four rungs per scheme with dt fixed at 1e-4",
        "read-only re-measurement; no registered artifact was edited",
    ],
    "A recomputed fixed-dt order leaving |p-2| > 0.3, a non-monotone ladder, cross-scheme "
    "spread > 0.25, a registered pin drifting from disk, or numerics/spherical_solver "
    "appearing while locked.",
    [f"{AUDIT}#{H(AUDIT)[:12]}", f"{CERT}#{H(CERT)[:12]}", f"{REGISTRY}"],
    node_id="N0",
    event_id=events.det_id("claim", AUDIT, H(AUDIT)),
))

# --------------------------------------------------------------------- status
rec(events.emit_status(
    "N0", "active", HOURS,
    "NUMERICS LEAD LIFECYCLE 07 (one independent read-only pass). Queue: no new owned card "
    "(inbox unchanged since 00:36; astra-life04-n0-stoprule already discharged); audit-owned "
    "cards N0-verify and C8-adjudication remain open. Re-measured from disk: 9/12 required "
    "pins registry-matched, 0 drift, exactly 3 residual unregistered paths (W046/W057/W081 "
    "verdicts; down from 6 at 00:50); independent order re-fit reproduces declared fixed-dt "
    "orders to 0.0 with monotone ladders and cross-scheme spread 7.96e-05 <= 0.25; lock guard "
    "PASS, numerics/spherical_solver absent, N1 queued. Protocol contest is mechanically "
    "5 accepts / 5 revises: three revises are discharged by supersession (audit r4 "
    "adjudication), two have their recommended byte-preserving remedy published (authority "
    "record) and await re-review. Checkpoint coverage gap re-measured: rev3 + fixed-dt "
    "certification absent from numerics/checkpoint.py TRACKED; byte-preserving patch "
    "proposed, not applied. No gate verdict claimed; no registered instrument edited.",
    [f"{AUDIT}#{H(AUDIT)[:12]}", f"{AUTHORITY}#{H(AUTHORITY)[:12]}", f"{ADJ}#{H(ADJ)[:12]}",
     f"{CERT}#{H(CERT)[:12]}"],
    "Any registered pin drifting from disk, numerics/spherical_solver appearing while locked, "
    "or a gate verdict claimed without artifact + independent review.",
    event_id=events.det_id("status", "N0", "lifecycle07", H(AUDIT)),
))

# ------------------------------------------------------------------- blockers
rec(events.emit_blocker(
    "N0",
    "REGISTRATION GAP (residual, controller action; narrowed this pass). Of the six paths "
    "named in B-N0-R2-1 (reviews/N0-review-final-verify.json, 00:50), three are now "
    "registry-matched at the same bytes (numerics/CONVERGENCE_PROTOCOL.md, "
    "numerics/results/flat_wave_convergence.json, numerics/gates.py). Three required evidence "
    f"paths remain absent from {REGISTRY}: {W046}#{H(W046)[:12]}, {W057}#{H(W057)[:12]}, "
    f"{W081}#{H(W081)[:12]}. All three exist on disk and are cited by "
    f"{AUTHORITY}#{H(AUTHORITY)[:12]}; PROTOCOL rule 2 requires a registered sha256 before any "
    "N0 done claim.",
    "Controller registers the three measured paths (bytes/sha256 re-measured in the audit "
    "artifact); no artifact change is needed.",
    [f"{AUDIT}#{H(AUDIT)[:12]}", REGISTRY, f"{W046}#{H(W046)[:12]}", f"{W057}#{H(W057)[:12]}",
     f"{W081}#{H(W081)[:12]}"],
    severity="high",
    event_id=events.det_id("blocker", "n0-registration-residual-l07", AUDIT, H(W046), H(W057), H(W081)),
))
rec(events.emit_blocker(
    "N0",
    "C8 PROTOCOL-REVIEW CONTEST (controller/audit disposition needed; numerics does not "
    f"self-adjudicate). Live tally at {PROTOCOL}#{H(PROTOCOL)[:12]}: 5 accepts, 5 revises. "
    "Three revises are discharged by supersession per the audit r4 adjudication "
    f"({ADJ}#{H(ADJ)[:12]}): w067-F1 and w081-F1' (constant-CFL basis replaced by the filed "
    "fixed-dt study; the F1' falsifier predicate is met) and w067-provledger (remedied by "
    "fixed_replication_verdict_rev2). Two revises (w042 HF-042-N0-1, w081 HF-081-PS-1) have "
    "their recommended byte-preserving remedy published in "
    f"{AUTHORITY}#{H(AUTHORITY)[:12]} and await re-review. numerics/gates.py still reports "
    "contest=true because it has no (reviewer,target)-at-one-hash supersession rule. Closing "
    "this requires controller disposition or a guard supersession rule -- not a numerics "
    "self-pass.",
    "Controller/audit disposition of the C8 contest (card astra-life05-gnum-protocol-adjudication) "
    "and, if adopted, an authorized guard supersession rule; ratification of the class-binding "
    "carrier record. G-NUM verdict remains Astra / lead-audit authority.",
    [f"{AUDIT}#{H(AUDIT)[:12]}", f"{ADJ}#{H(ADJ)[:12]}", f"{AUTHORITY}#{H(AUTHORITY)[:12]}",
     f"{PROTOCOL}#{H(PROTOCOL)[:12]}"],
    severity="high",
    event_id=events.det_id("blocker", "n0-c8-contest-l07", H(PROTOCOL), H(ADJ)),
))
rec(events.emit_blocker(
    "N0",
    "CHECKPOINT COVERAGE GAP (numerics group tool; byte-preserving patch proposed, NOT "
    f"applied). numerics/checkpoint.py#{H(CHECKPOINT)[:12]} TRACKED omits "
    + ", ".join(ckpt["tracked_omits"]) + ". Measured: rev3 landed at "
    f"{ckpt['rev3_landed_at']}, yet num-ckpt-20260912-004552 reports changed=['numerics/"
    "blockers.md'] and num-ckpt-20260912-010105 reports changed=[] -- the N0 closure artifact "
    "is invisible to the group drift detector. This lifecycle publishes a coverage addendum "
    "instead of moving the registered instrument while the C8 disposition is open.",
    "Controller authorization to extend TRACKED in numerics/checkpoint.py with the four "
    "omitted paths (exact list in the audit artifact), or an explicit decision to leave the "
    "instrument frozen; a later numerics pass can then apply the patch and re-register.",
    [f"{AUDIT}#{H(AUDIT)[:12]}", f"{CHECKPOINT}#{H(CHECKPOINT)[:12]}",
     "artifacts/numerics/checkpoints/num-ckpt-20260912-004552.json",
     "artifacts/numerics/checkpoints/num-ckpt-20260912-010105.json"],
    severity="medium",
    event_id=events.det_id("blocker", "n0-checkpoint-coverage-l07", AUDIT, H(CHECKPOINT)),
))

# ---------------------------------------------------------------------- close
rec(events.emit_status(
    "GLOBAL", "done", HOURS,
    "NUMERICS GROUP LEAD LIFECYCLE 07 COMPLETE -- exiting. One independent read-only pass; no "
    "solver code written or run, numerics_lock LOCKED, N1 queued, numerics/spherical_solver "
    "absent, no gate verdict claimed, no registered instrument or other agent's artifact edited.",
    [f"{AUDIT}#{H(AUDIT)[:12]}", f"{CERT}#{H(CERT)[:12]}"],
    "A later pass finding drift against these hashes, or any N1/self-gravity artifact while locked.",
    event_id=events.det_id("status", "GLOBAL", "lifecycle07-done", H(AUDIT)),
))

print(json.dumps({"emitted": len(emitted), "hours": HOURS,
                  "audit_sha256": H(AUDIT), "lifecycle_record_sha256": H(LIFECYCLE),
                  "event_ids": [e["event_id"] for e in emitted]}, indent=1))
