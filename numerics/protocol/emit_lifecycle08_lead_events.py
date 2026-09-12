#!/usr/bin/env python3
"""Numerics-lead lifecycle 08 structured events (one independent pass, then exit).

Deterministic event ids make re-running idempotent (``numerics.events.emit`` returns the
already-appended event instead of duplicating it).

    python3 numerics/protocol/emit_lifecycle08_lead_events.py
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
INSTANCE = REPO / "runtime/instances/lead-numerics-01-20260912T010820-968807/meta.json"
STARTED = json.loads(INSTANCE.read_text())["started_at"] if INSTANCE.is_file() else None
if STARTED:
    HOURS = round(max((time.time() - datetime.fromisoformat(STARTED).timestamp()) / 3600.0, 0.01), 3)
else:
    HOURS = 0.1

VERIFY = "numerics/protocol/lifecycle08_stoprule_closure_verify.json"
GENERATOR = "numerics/protocol/lifecycle08_stoprule_closure_verify.py"
LIFECYCLE = "artifacts/numerics/lifecycle_08_20260912.json"
REV3 = "numerics/results/flat_wave_convergence_rev3.json"
CERT = "numerics/protocol/n0_fixed_dt_certification.json"
AUTHORITY = "numerics/N0_CLASS_BINDING_AUTHORITY.json"
PROTOCOL = "numerics/CONVERGENCE_PROTOCOL.md"
CHECKPOINT = "numerics/checkpoint.py"
REGISTRY = "runtime/state/artifact_hashes.json"
MAP = "research_map/research_map.json"
TAXONOMY = "research_map/formulation_taxonomy.yaml"
W046 = "artifacts/worker-046/n0_fixed_dt_independent/verification.json"
W057 = "artifacts/worker-057/n0_fixeddt_verify/report.json"
W081 = "artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json"
FLASH13 = "reviews/flash-13-N0-rev3-verdict.json"
ADJ = "reviews/G-NUM-protocol-r4-adjudication.json"
AUDIT_REVIEW = "reviews/N0-review-lead-audit.json"

v = json.loads((REPO / VERIFY).read_text())
reg = v["registration"]
i1, i2, i3 = v["item_1_four_rungs"], v["item_2_f0_rebind"], v["item_3_independent_replication"]

lifecycle_record = {
    "schema": "numerics-lead-lifecycle/v1",
    "lifecycle_id": "lead-numerics-08",
    "instance": INSTANCE.stem,
    "actor": "astra-lead-numerics",
    "group_id": "numerics",
    "started_at": STARTED,
    "closed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    "mode": "one independent lifecycle; read-only on all canonical paths; then exit",
    "queue_consumed": {
        "new_owned_cards": [],
        "note": (
            "comms/inbox/astra-lead-numerics.jsonl unchanged at 10 lines / mtime 00:36; the last "
            "card astra-life04-n0-stoprule is discharged by the rev-3 report. The controller "
            "ruling at 01:09:48 (REC-34) names the only remaining N0 item: astra-life04-n0-verify "
            "(lead-audit) must land an N0 accept at one hash. No card assigns new numerics work."
        ),
    },
    "deliverables": {
        VERIFY: {"sha256": H(VERIFY), "role": "independent stop-rule closure verification + live-map pin audit"},
        GENERATOR: {"sha256": H(GENERATOR), "role": "stdlib-only, read-only; exit 2 closure item failed, 3 lock violation, 4 residual registration gap, 5 evidence-chain pin drift"},
    },
    "verification": {
        "stop_rule_closure": {
            "item_1_four_rungs": {
                "closed": i1["closed"],
                "schemes": {k: {"n_rungs": s["n_rungs"], "dt_fixed_1e-4": s["dt_fixed_1e-4"],
                                "recomputed_fit_order": s["recomputed_fit_order"],
                                "monotone": s["monotone"], "within_band_0p3": s["within_band_0p3"]}
                           for k, s in i1["schemes"].items()},
                "max_abs_diff_vs_declared": i1["max_abs_diff_vs_declared"],
                "cross_scheme_spread": i1["cross_scheme_spread"],
                "cross_scheme_R5_bound": i1["cross_scheme_R5_bound"],
            },
            "item_2_f0_rebind": {
                "closed": i2["closed"],
                "declared_revision": i2["declared_revision"],
                "live_revision": i2["live_revision"],
                "declared_sha256": i2["declared_sha256"],
                "live_sha256": i2["live_sha256"],
            },
            "item_3_independent_replication": {
                "closed": i3["closed"],
                "verdict_count": i3["verdict_count"],
                "verdicts": [{"reviewer": x["reviewer"], "verdict": x["declared_verdict"],
                              "hash_match": x["hash_match"]} for x in i3["verdicts"]],
                "flash13_binds_current_rev3": i3["flash13_accept"]["binds_current_rev3"],
            },
            "all_closure_items_closed": v["all_closure_items_closed"],
        },
        "registration": {
            "residual_unregistered": reg["residual_unregistered"],
            "drift": reg["drift"],
        },
        "live_map_pins": {
            "gnum_evidence_refs": reg["gnum_evidence_refs"],
            "resolved": reg["gnum_resolved"],
            "historical_superseded": reg["gnum_historical_pins"],
            "stale_pins": reg["gnum_stale_pins"],
            "missing_files": reg["gnum_missing_files"],
        },
        "lock_compliance": v["lock_compliance"],
    },
    "claims_not_made": v["claims_not_made"],
    "falsifier": v["falsifier"],
}
(REPO / LIFECYCLE).write_text(json.dumps(lifecycle_record, indent=1, sort_keys=True))

emitted = []


def rec(ev):
    emitted.append(ev)
    print(f"  + {ev['event_type']:<9} {ev['event_id']}")


# ------------------------------------------------------------------ artifacts
rec(events.emit_artifact(
    "N0", "n0_stoprule_closure_verification", VERIFY, "unverified",
    validation_evidence=[f"{GENERATOR}#{H(GENERATOR)[:12]}", f"{CERT}#{H(CERT)[:12]}",
                         f"{REV3}#{H(REV3)[:12]}", f"{FLASH13}#{H(FLASH13)[:12]}"],
    event_id=events.det_id("artifact", VERIFY, H(VERIFY)),
))
rec(events.emit_artifact(
    "N0", "n0_stoprule_closure_verify_generator", GENERATOR, "unverified",
    validation_evidence=[f"{VERIFY}#{H(VERIFY)[:12]}"],
    event_id=events.det_id("artifact", GENERATOR, H(GENERATOR)),
))
rec(events.emit_artifact(
    "GLOBAL", "numerics_lead_lifecycle_record", LIFECYCLE, "unverified",
    validation_evidence=[f"{VERIFY}#{H(VERIFY)[:12]}"],
    event_id=events.det_id("artifact", LIFECYCLE, H(LIFECYCLE)),
))

# ---------------------------------------------------------------------- claim
rec(events.emit_claim(
    "AF-WCC-SCALAR-SPH",
    "Independent lifecycle-08 verification of the reviews/N0-review-lead-audit.json stop rule "
    "at the current on-disk hashes. Item (1) CLOSED by a fourth rung, not by scoping: my own "
    "log-log least squares on the raw rows of numerics/protocol/n0_fixed_dt_certification.json "
    "reproduces all three declared fixed-dt fits exactly (max |dp| = "
    f"{i1['max_abs_diff_vs_declared']:.3e}); every scheme has 4 rungs, dt = 1e-4 only, a monotone "
    f"error ladder, |p-2| <= 0.3, and cross-scheme spread {i1['cross_scheme_spread']:.3e} <= R5 "
    "bound 0.25. Item (2) CLOSED: the live taxonomy at "
    f"{i2['live_sha256'][:12]} is revision {i2['live_revision']} and matches the declared F0 rev5 "
    "pin, with the class id present. Item (3) CLOSED: all three cited replication verdicts "
    "(worker-046 SUPPORTED, worker-057 REPRODUCED, worker-081 accept) hash-match their declared "
    "bytes, and the deepseek-flash-13 accept binds to the current rev3 hash "
    f"{i3['flash13_accept']['pinned_sha256'][:12]} (hash_stable_across_review=true). No "
    "certification generator and no solver was imported; no registered artifact was edited.",
    "numerical_evidence",
    [
        "flat-space scalar-wave calibration only; no self-gravity, no coupling to geometry",
        "order certified at four rungs per scheme with dt fixed at 1e-4",
        "read-only re-measurement; no registered artifact was edited",
    ],
    "A recomputed fixed-dt order leaving |p-2| > 0.3, a non-monotone ladder, cross-scheme "
    "spread > 0.25, a cited verdict's bytes moving off its declared hash, the live taxonomy "
    "ceasing to match the declared F0 revision, or numerics/spherical_solver appearing while "
    "numerics_lock == 'locked'.",
    [f"{VERIFY}#{H(VERIFY)[:12]}", f"{CERT}#{H(CERT)[:12]}", f"{TAXONOMY}#{H(TAXONOMY)[:12]}",
     f"{REV3}#{H(REV3)[:12]}"],
    node_id="N0",
    event_id=events.det_id("claim", VERIFY, H(VERIFY)),
))

# --------------------------------------------------------------------- status
rec(events.emit_status(
    "N0", "active", HOURS,
    "NUMERICS LEAD LIFECYCLE 08 (one independent read-only pass). Queue: no new owned card "
    "(inbox unchanged since 00:36; astra-life04-n0-stoprule discharged). All three stop-rule "
    "items re-verified closed at current hashes by fresh measurement: 4 rungs/scheme at "
    "fixed dt=1e-4 with independently reproduced fits (max |dp| 0.0), F0 rev5 re-bind live, and "
    "three hash-matched replication verdicts. Residual: 3 required evidence paths still "
    "unregistered (W046/W057/W081) plus research_map/formulation_taxonomy.yaml; one live-map "
    "G-NUM evidence ref is mispinned (see blocker). Lock guard PASS, numerics/spherical_solver "
    "absent, N1 queued. No gate verdict claimed, no node transition, no registered instrument "
    "edited. The only N0 item named by the 01:09:48 controller ruling (REC-34) is "
    "astra-life04-n0-verify, which is lead-audit-owned.",
    [f"{VERIFY}#{H(VERIFY)[:12]}", f"{AUTHORITY}#{H(AUTHORITY)[:12]}", f"{CERT}#{H(CERT)[:12]}",
     f"{REV3}#{H(REV3)[:12]}"],
    "Any registered pin drifting from disk, numerics/spherical_solver appearing while locked, "
    "or a gate verdict claimed without artifact + independent review.",
    event_id=events.det_id("status", "N0", "lifecycle08", H(VERIFY)),
))

# ------------------------------------------------------------------- blockers
rec(events.emit_blocker(
    "N0",
    "LIVE-MAP EVIDENCE PIN (new this pass, advisory/documentary). research_map/research_map.json"
    f"#/gates[3]/evidence_refs[33] resolves G-NUM evidence to "
    f"'reviews/G-NUM-protocol-review.json#1e6cdf04d7a2', but reviews/G-NUM-protocol-review.json "
    f"hashes to {H('reviews/G-NUM-protocol-review.json')[:12]}; 1e6cdf04d7a2 is the hash of its "
    "reviewed TARGET numerics/CONVERGENCE_PROTOCOL.md, not of the review record. The revision "
    "the r4 adjudication names (66a905f5afef) is carried by a separate ref later in the same "
    "list and by reviews/G-NUM-protocol-review-rev1-advisory.json, so no substantive evidence is "
    "missing. Separately, five further refs in the same 44-ref list pin superseded revisions of "
    "the same path (historical, not broken) and one ref "
    "(runtime/state/controller_verification/astra-lifecycle-07-decisions.json) has no file on "
    "disk. numerics/gates.py gates on verdict=='pass' plus a non-empty evidence list, so none of "
    "these blocks the lock guard; they are traceability defects in the gate-of-record list.",
    "Controller corrects the one mispinned ref (and, if desired, prunes or labels the five "
    "historical refs and the absent lifecycle-07 decisions ref) when the G-NUM evidence list is "
    "next re-pinned. No numerics artifact changes are required; numerics does not edit the map.",
    [f"{VERIFY}#{H(VERIFY)[:12]}", MAP, "reviews/G-NUM-protocol-review.json",
     "reviews/G-NUM-protocol-review-rev1-advisory.json", f"{PROTOCOL}#{H(PROTOCOL)[:12]}"],
    severity="low",
    event_id=events.det_id("blocker", "gnum-mispin-l08", MAP, H(VERIFY)),
))
rec(events.emit_blocker(
    "N0",
    "REGISTRATION GAP (residual, controller action; unchanged from lifecycle 07). Three "
    f"independent replication verdicts cited by the rev-3 closure remain absent from {REGISTRY}: "
    f"{W046}#{H(W046)[:12]}, {W057}#{H(W057)[:12]}, {W081}#{H(W081)[:12]}. All three exist on "
    "disk, hash-match the values rev3 and the authority record declare, and are the evidence "
    "item (3) of the stop rule rests on. PROTOCOL rule 2 requires a registered sha256 plus a "
    "reviewer verdict before any N0 done claim. (research_map/formulation_taxonomy.yaml is also "
    "unregistered in this registry, which by design covers artifacts/ and numerics/ roots rather "
    "than research_map/.)",
    "Controller registers the three measured paths in runtime/state/artifact_hashes.json; no "
    "artifact change is needed.",
    [f"{VERIFY}#{H(VERIFY)[:12]}", REGISTRY, f"{W046}#{H(W046)[:12]}", f"{W057}#{H(W057)[:12]}",
     f"{W081}#{H(W081)[:12]}"],
    severity="high",
    event_id=events.det_id("blocker", "n0-registration-residual-l08", REGISTRY, H(W046), H(W057), H(W081)),
))
rec(events.emit_blocker(
    "N0",
    "C8 PROTOCOL-REVIEW CONTEST (controller/audit disposition needed; numerics does not "
    f"self-adjudicate; unchanged from lifecycle 07). Live tally at {PROTOCOL}#{H(PROTOCOL)[:12]}: "
    "5 accepts / 5 revises; numerics/gates.py reports contest=true. Three revises are discharged "
    "by supersession per the audit r4 adjudication "
    f"({ADJ}#{H(ADJ)[:12]}); two (w042 HF-042-N0-1, w081 HF-081-PS-1) have their recommended "
    f"byte-preserving remedy published in {AUTHORITY}#{H(AUTHORITY)[:12]} and await re-review. "
    "The mechanical cause is that numerics/gates.py::_protocol_review has no "
    "(reviewer,target,hash) supersession rule, so a later accept cannot rescind an earlier "
    "revise and the withdrawn w081 accept is still counted.",
    "Controller/audit disposition of the C8 contest and, if adopted, an authorized guard "
    "supersession rule; ratification of the class-binding carrier record. G-NUM verdict remains "
    "Astra / lead-audit authority.",
    [f"{VERIFY}#{H(VERIFY)[:12]}", f"{ADJ}#{H(ADJ)[:12]}", f"{AUTHORITY}#{H(AUTHORITY)[:12]}",
     f"{PROTOCOL}#{H(PROTOCOL)[:12]}"],
    severity="high",
    event_id=events.det_id("blocker", "n0-c8-contest-l08", H(PROTOCOL), H(ADJ)),
))
rec(events.emit_blocker(
    "N0",
    "CHECKPOINT COVERAGE GAP (numerics group tool; byte-preserving patch STILL proposed, not "
    f"applied). numerics/checkpoint.py#{H(CHECKPOINT)[:12]} TRACKED still omits "
    f"{REV3}, {CERT}, numerics/protocol/n0_registration_drift_audit.json and {AUTHORITY}; "
    "num-ckpt-20260912-010743 again reports changed=[] in a window in which lifecycle 07 wrote "
    "its audit, emitter and lifecycle record, so the N0 closure is invisible to the group drift "
    "detector. Not applied because the instrument is registered and the C8 disposition is open.",
    "Controller authorization to extend TRACKED in numerics/checkpoint.py with the four omitted "
    "paths, or an explicit decision to leave the instrument frozen; a later numerics pass can "
    "then apply the patch and re-register.",
    [f"{VERIFY}#{H(VERIFY)[:12]}", f"{CHECKPOINT}#{H(CHECKPOINT)[:12]}",
     "numerics/protocol/checkpoint_gap_witness_l07.json",
     "artifacts/numerics/checkpoints/num-ckpt-20260912-010743.json"],
    severity="medium",
    event_id=events.det_id("blocker", "n0-checkpoint-coverage-l08", CHECKPOINT, H(VERIFY)),
))

# ---------------------------------------------------------------------- close
rec(events.emit_status(
    "GLOBAL", "done", HOURS,
    "NUMERICS GROUP LEAD LIFECYCLE 08 COMPLETE -- exiting. One independent read-only pass; no "
    "solver code written or run, numerics_lock LOCKED, N1 queued, numerics/spherical_solver "
    "absent, no gate verdict claimed, no registered instrument or other agent's artifact edited. "
    "Stop-rule closure independently re-verified closed at current hashes; residuals handed to "
    "the controller are the three unregistered replication verdicts and one mispinned G-NUM "
    "evidence ref; the N0 accept remains lead-audit-owned (astra-life04-n0-verify).",
    [f"{VERIFY}#{H(VERIFY)[:12]}", f"{CERT}#{H(CERT)[:12]}", f"{REV3}#{H(REV3)[:12]}"],
    "A later pass finding drift against these hashes, or any N1/self-gravity artifact while locked.",
    event_id=events.det_id("status", "GLOBAL", "lifecycle08-done", H(VERIFY)),
))

print(json.dumps({"emitted": len(emitted), "hours": HOURS,
                  "verify_sha256": H(VERIFY), "lifecycle_record_sha256": H(LIFECYCLE),
                  "event_ids": [e["event_id"] for e in emitted]}, indent=1))
