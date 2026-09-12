#!/usr/bin/env python3
"""Lifecycle-08 finalize: successor pins for the two artifacts that moved after the first emit.

The closure-verification JSON reached byte-stable form first and is pinned correctly. The
generator was then edited (root-cause fix: timestamp-insensitive comparison, shared exit-code
helper) and the lifecycle record necessarily re-stamped, so both need successor artifact pins.

    python3 numerics/protocol/emit_lifecycle08_finalize.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from numerics import events  # noqa: E402

H = events.sha256_file
VERIFY = "numerics/protocol/lifecycle08_stoprule_closure_verify.json"
GENERATOR = "numerics/protocol/lifecycle08_stoprule_closure_verify.py"
LIFECYCLE = "artifacts/numerics/lifecycle_08_20260912.json"
CERT = "numerics/protocol/n0_fixed_dt_certification.json"
REV3 = "numerics/results/flat_wave_convergence_rev3.json"
EMITTER = "numerics/protocol/emit_lifecycle08_lead_events.py"

emitted = []


def rec(ev):
    emitted.append(ev)
    print(f"  + {ev['event_type']:<9} {ev['event_id']}")


rec(events.emit_artifact(
    "N0", "n0_stoprule_closure_verify_generator", GENERATOR, "unverified",
    validation_evidence=[
        f"{VERIFY}#{H(VERIFY)[:12]}",
        "root-cause fix applied: generated_at is excluded from the stability comparison, so "
        "re-running on an unchanged environment never rewrites the artifact (three consecutive "
        "runs reproduced identical bytes and identical exit code 4)",
        "exit codes centralised in _exit_code(): 3 lock, 2 closure, 4 registration, 5 pin drift",
    ],
    event_id=events.det_id("artifact", GENERATOR, H(GENERATOR), "finalize"),
))
rec(events.emit_artifact(
    "GLOBAL", "numerics_lead_lifecycle_record", LIFECYCLE, "unverified",
    validation_evidence=[f"{VERIFY}#{H(VERIFY)[:12]}", f"{GENERATOR}#{H(GENERATOR)[:12]}",
                         f"{CERT}#{H(CERT)[:12]}", f"{REV3}#{H(REV3)[:12]}",
                         f"emitter {EMITTER}#{H(EMITTER)[:12]}"],
    event_id=events.det_id("artifact", LIFECYCLE, H(LIFECYCLE), "finalize"),
))
rec(events.emit_status(
    "N0", "active", 0.02,
    "LIFECYCLE-08 FINALIZE. Final pins for this pass: closure verification "
    f"{VERIFY}#{H(VERIFY)[:12]} (byte-stable), generator {GENERATOR}#{H(GENERATOR)[:12]}, "
    f"lifecycle record {LIFECYCLE}#{H(LIFECYCLE)[:12]}. All three stop-rule items are closed at "
    "the current hashes; residual controller actions are the three unregistered replication "
    "verdicts (W046/W057/W081) and one mispinned G-NUM evidence ref. No gate verdict, no node "
    "transition, no numerics_lock change.",
    [f"{VERIFY}#{H(VERIFY)[:12]}", f"{GENERATOR}#{H(GENERATOR)[:12]}",
     f"{LIFECYCLE}#{H(LIFECYCLE)[:12]}"],
    "A later re-run of the generator changing bytes without a measurement change, or any "
    "N1/self-gravity artifact while locked.",
    event_id=events.det_id("status", "N0", "lifecycle08-finalize", H(VERIFY), H(GENERATOR)),
))

print(json.dumps({"emitted": len(emitted),
                  "verify_sha256": H(VERIFY),
                  "generator_sha256": H(GENERATOR),
                  "lifecycle_record_sha256": H(LIFECYCLE),
                  "event_ids": [e["event_id"] for e in emitted]}, indent=1))
