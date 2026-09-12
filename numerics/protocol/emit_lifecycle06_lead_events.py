#!/usr/bin/env python3
"""Numerics-lead lifecycle 06 (2026-09-12T00:56 start) structured events.

Deterministic event ids make re-running idempotent: ``numerics.events.emit`` returns
the already-appended event instead of duplicating it.

    python3 numerics/protocol/emit_lifecycle06_lead_events.py
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
INSTANCE = REPO / "runtime/instances/lead-numerics-01-20260912T005609-968807/meta.json"
STARTED = json.loads(INSTANCE.read_text())["started_at"] if INSTANCE.is_file() else None
if STARTED:
    HOURS = round(max((time.time() - datetime.fromisoformat(STARTED).timestamp()) / 3600.0, 0.01), 3)
else:
    HOURS = 0.2

AUDIT = "numerics/protocol/n0_registration_drift_audit.json"
GENERATOR = "numerics/protocol/audit_registration_drift.py"
AUTHORITY = "numerics/N0_CLASS_BINDING_AUTHORITY.json"
REV3 = "numerics/results/flat_wave_convergence_rev3.json"
REPORT = "reviews/N0-pin-split-adjudication-worker-081.json"
REVIEW42 = "reviews/N0-review-worker-042.json"
W046 = "artifacts/worker-046/n0_fixed_dt_independent/verification.json"
W057 = "artifacts/worker-057/n0_fixeddt_verify/report.json"
W081 = "artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json"
PROTOCOL = "numerics/CONVERGENCE_PROTOCOL.md"
REGISTRY = "runtime/state/artifact_hashes.json"

emitted = []


def rec(ev):
    emitted.append(ev)
    print(f"  + {ev['event_type']:<9} {ev['event_id']}")


# ------------------------------------------------------------------ artifacts
rec(events.emit_artifact(
    "N0", "n0_registration_drift_audit", AUDIT, "unverified",
    validation_evidence=[f"{GENERATOR}#{H(GENERATOR)[:12]}", f"{AUTHORITY}#{H(AUTHORITY)[:12]}"],
    event_id=events.det_id("artifact", AUDIT, H(AUDIT)),
))
rec(events.emit_artifact(
    "N0", "n0_registration_drift_audit_generator", GENERATOR, "unverified",
    validation_evidence=[f"{AUDIT}#{H(AUDIT)[:12]}"],
    event_id=events.det_id("artifact", GENERATOR, H(GENERATOR)),
))
rec(events.emit_artifact(
    "N0", "n0_class_binding_authority", AUTHORITY, "unverified",
    validation_evidence=[
        "worker-081 checker A1-A5 all OK (read-only import; A6 false by design: "
        "published lead record, not the proposal-only variant)",
        f"{REV3}#{H(REV3)[:12]}",
        f"{REPORT}#{H(REPORT)[:12]}",
    ],
    event_id=events.det_id("artifact", AUTHORITY, H(AUTHORITY)),
))

# ---------------------------------------------------------------------- claim
rec(events.emit_claim(
    "AF-WCC-SCALAR-SPH",
    "Independent re-fit at the frozen N0 evidence basis: the fixed-dt (dt=1e-4) spatial "
    "order recomputed from the raw rows of numerics/protocol/n0_fixed_dt_certification.json "
    "is cnfd 1.999863592724, cnfem 1.999916307987, lffd 1.999943173893, matching the declared "
    "fits to 0.0 difference; every ladder is monotone; max cross-scheme |dp| = 7.958e-05 <= R5 "
    "bound 0.25. The certified order claim contains no taxonomy string, so the F0 class-binding "
    "pin split is documentation metadata, not load-bearing for this number.",
    "numerical_evidence",
    [
        "flat-space scalar-wave calibration only; no self-gravity, no coupling to geometry",
        "order certified at four rungs per scheme with dt fixed at 1e-4",
        "re-measured from disk; the certification generator and any solver were not imported",
    ],
    "A recomputed fixed-dt order leaving |p-2| > 0.3, a non-monotone ladder, cross-scheme "
    "|dp| > 0.25, or any declared pin re-hashing to a different value.",
    [f"{AUDIT}#{H(AUDIT)[:12]}", f"numerics/protocol/n0_fixed_dt_certification.json#{H('numerics/protocol/n0_fixed_dt_certification.json')[:12]}"],
    node_id="N0",
    event_id=events.det_id("claim", AUDIT, H(AUDIT)),
))

# --------------------------------------------------------------------- status
rec(events.emit_status(
    "N0", "active", HOURS,
    "NUMERICS LEAD LIFECYCLE 06 (one independent pass). Consumed queue: astra-life04-n0-stoprule "
    "discharged by the rev-3 report; astra-life04-n0-verify and astra-life05-gnum-protocol-adjudication "
    "are audit-owned. Re-measured, read-only: 10/13 declared pins match disk and registry; 3 residual "
    "unregistered paths are the worker-046/057/081 replication verdicts. Independent order re-fit "
    "reproduces the declared values exactly. Published numerics/N0_CLASS_BINDING_AUTHORITY.json: for "
    "N0 / G-NUM the class-binding carrier is numerics/results/flat_wave_convergence_rev3.json"
    f"#{H(REV3)[:12]}; the class binding of record it carries is F0 rev5 "
    "research_map/formulation_taxonomy.yaml#0abb9ed8a961. This addresses the root of HF-042-N0-1 and "
    "HF-081-PS-1 (no record named a single carrier) byte-preservingly: numerics/CONVERGENCE_PROTOCOL.md"
    f"#{H(PROTOCOL)[:12]} is unchanged and no verdict bound to it is voided. It does NOT adjudicate the "
    "C8 protocol-review contest, does not set a gate verdict, and does not move N0 status. Lock guard "
    "N1_BLOCKED, production_allowed=false, numerics/spherical_solver absent.",
    [f"{AUDIT}#{H(AUDIT)[:12]}", f"{AUTHORITY}#{H(AUTHORITY)[:12]}", f"{REPORT}#{H(REPORT)[:12]}"],
    "Any pinned hash moving, a recomputed order outside |p-2| <= 0.3, numerics/spherical_solver "
    "appearing while locked, or a gate verdict claimed without artifact + independent review.",
    event_id=events.det_id("status", "N0", "lifecycle06", H(AUDIT), H(AUTHORITY)),
))

# ------------------------------------------------------------------- blockers
rec(events.emit_blocker(
    "N0",
    "REGISTRATION GAP (residual, controller action): three independent replication verdicts cited by "
    "the rev-3 closure artifact are absent from runtime/state/artifact_hashes.json -- "
    f"{W046}#{H(W046)[:12]}, {W057}#{H(W057)[:12]}, {W081}#{H(W081)[:12]}. The other ten declared pins "
    "match registry and disk. PROTOCOL rule 2 requires a registry sha256 before any N0 done claim.",
    "Controller registers the three measured paths (bytes and sha256 re-measured in the audit artifact) "
    "in runtime/state/artifact_hashes.json. No artifact change is needed.",
    [f"{AUDIT}#{H(AUDIT)[:12]}", f"{REGISTRY}", f"{W046}#{H(W046)[:12]}", f"{W057}#{H(W057)[:12]}",
     f"{W081}#{H(W081)[:12]}"],
    severity="high",
    event_id=events.det_id("blocker", "n0-registration-residual", AUDIT, H(W046), H(W057), H(W081)),
))
rec(events.emit_blocker(
    "N0",
    "C8 PROTOCOL-REVIEW CONTEST (not adjudicated by numerics). At numerics/CONVERGENCE_PROTOCOL.md"
    f"#{H(PROTOCOL)[:12]} the guard counts four standing revises (w067 x2, w081 F1', w042) against two "
    "accepts; numerics/gates.py reports contest=true and refuses to treat the review row as satisfied. "
    "The separate stop-rule item (2) pin-split now has one named carrier in "
    f"numerics/N0_CLASS_BINDING_AUTHORITY.json#{H(AUTHORITY)[:12]} (controller ratification requested); "
    "HF-042-N0-1 and HF-081-PS-1 name that record as their discharge condition.",
    "Controller/audit disposition of withdrawal and (reviewer,target)-at-one-hash supersession semantics "
    "(card astra-life05-gnum-protocol-adjudication), and controller ratification of the carrier record. "
    "The numerics lead does not self-adjudicate and does not self-pass G-NUM.",
    [f"{AUDIT}#{H(AUDIT)[:12]}", f"{AUTHORITY}#{H(AUTHORITY)[:12]}", f"numerics/gates.py#{H('numerics/gates.py')[:12]}",
     f"{REPORT}#{H(REPORT)[:12]}", f"{REVIEW42}#{H(REVIEW42)[:12]}"],
    severity="high",
    event_id=events.det_id("blocker", "n0-c8-contest", H(PROTOCOL), H(AUTHORITY)),
))

rec(events.emit_blocker(
    "N0",
    "CHECKPOINT COVERAGE GAP (numerics group tool, advisory). numerics/checkpoint.py TRACKED omits "
    "numerics/results/flat_wave_convergence_rev3.json and numerics/protocol/n0_fixed_dt_certification.json, "
    "so the N0 closure artifact landing at 00:44:23 was invisible to the drift detector: "
    "num-ckpt-20260912-004552 (00:45:52) reports changed=['numerics/blockers.md'] only, and "
    "num-ckpt-20260912-010105 (01:01:05) reports changed=[]. Measured, not inferred.",
    "Extend TRACKED in numerics/checkpoint.py to include the rev-3 closure, the fixed-dt certification, "
    "this lifecycle's authority record and drift audit. NOT done in this window: numerics/checkpoint.py "
    "is registered at 35955c3873fc20e4 and moving a registered hash during the open C8 adjudication "
    "would add an uncontrolled change; controller/next-pass decision requested.",
    [f"{AUDIT}#{H(AUDIT)[:12]}", "numerics/checkpoint.py#35955c3873fc20e4",
     "artifacts/numerics/checkpoints/num-ckpt-20260912-004552.json",
     "artifacts/numerics/checkpoints/num-ckpt-20260912-010105.json"],
    severity="medium",
    event_id=events.det_id("blocker", "n0-checkpoint-coverage", AUDIT, H("numerics/checkpoint.py")),
))

# --------------------------------------------------------------------- close
rec(events.emit_status(
    "GLOBAL", "done", HOURS,
    "NUMERICS GROUP LEAD LIFECYCLE 06 COMPLETE -- exiting. One independent read-only pass; no solver "
    "code written or run, numerics_lock LOCKED, N1 queued, numerics/spherical_solver absent, no gate "
    "verdict claimed, no other agent's artifact edited.",
    [f"{AUDIT}#{H(AUDIT)[:12]}", f"{AUTHORITY}#{H(AUTHORITY)[:12]}"],
    "A later pass finding drift against these hashes, or any N1/self-gravity artifact while locked.",
    event_id=events.det_id("status", "GLOBAL", "lifecycle06-done", H(AUDIT), H(AUTHORITY)),
))

print(json.dumps({"emitted": len(emitted), "hours": HOURS,
                  "audit_sha256": H(AUDIT), "authority_sha256": H(AUTHORITY),
                  "event_ids": [e["event_id"] for e in emitted]}, indent=1))
