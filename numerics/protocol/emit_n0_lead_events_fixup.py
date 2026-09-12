#!/usr/bin/env python3
"""Fix-up events: lead proposal path correction after the dual-assigned path collision."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from numerics import events  # noqa: E402

H = events.sha256_file
START = 1789142636.0
HOURS = round(max((time.time() - START) / 3600.0, 0.01), 3)

LEAD = "artifacts/numerics/n0/n0_gate_proposal_lead.json"
COLLIDED = "numerics/tests/n0_gate_proposal.json"
DRIVER = "numerics/protocol/lead_4rung_replication.py"
BUILDER = "numerics/protocol/build_n0_gate_proposal.py"
FOUR = "artifacts/numerics/n0/lead_4rung_replication.json"
W13_4RUNG = "numerics/tests/n0_order_4rung.json"
PROTOCOL = "numerics/CONVERGENCE_PROTOCOL.md"
OLD_EVENT = "lnum-artifact-51c18f73a6c6ec9e8c55"  # earlier submission at the collided path

emitted = []


def rec(ev):
    emitted.append(ev)
    print(f"  + {ev['event_type']:<16} {ev['event_id']}")


rec(events.emit_artifact(
    "N0", "gate_proposal_lead", LEAD, "unverified",
    validation_evidence=[
        f"{BUILDER}#{H(BUILDER)[:12]}",
        f"{FOUR}#{H(FOUR)[:12]}",
        f"{W13_4RUNG}#{H(W13_4RUNG)[:12]}",
        "supersedes the earlier submission under event " + OLD_EVENT +
        " (that event pointed at the dual-assigned path, whose content is now worker 13's)",
    ],
    event_id=events.det_id("artifact", LEAD, H(LEAD))))

rec(events.emit_review(
    f"{COLLIDED}#{H(COLLIDED)[:12]}", "accept", 4.0, [],
    ["worker-level (deepseek-flash-13, astra-numfix-02) G-NUM proposal; no gate self-pass; "
     "recommended verdict pending with the protocol review named as the condition",
     "consistent with the lead adjudication: cnfem triage accepted, 4-rung orders reproduce "
     "the lead driver to <1e-6, C8 (independent protocol review) is the only unmet criterion",
     "path note: this file occupies a path that two assignments declared; it is a valid "
     "worker-level submission but is superseded as the lead adjudication by "
     "artifacts/numerics/n0/n0_gate_proposal_lead.json for gate purposes"],
    event_id=events.det_id("review", COLLIDED, H(COLLIDED))))

rec(events.emit_blocker(
    "N0",
    "Process finding, not a numerics blocker: the canonical path "
    "numerics/tests/n0_gate_proposal.json was declared by two assignments at once "
    "(astra-numfix-02 -> deepseek-flash-13 and astra-adj2-05 / astra-indep-1 -> "
    "astra-lead-numerics). The lead's submission was overwritten by the worker's at 00:08-00:09 "
    "and has been re-published at " + LEAD + " (sha " + H(LEAD)[:12] + "). The earlier lead "
    "artifact event " + OLD_EVENT + " no longer matches the collided path; treat it as "
    "superseded. No numerics evidence is lost: both submissions and both 4-rung artifacts agree.",
    "Controller (astra) confirms the N0 canonical artifact path for the gate proposal, or "
    "renames one card, and records the lead path as the adjudication artifact. No further "
    "numerics work is blocked by this finding.",
    [f"{LEAD}#{H(LEAD)[:12]}", f"{COLLIDED}#{H(COLLIDED)[:12]}",
     f"{FOUR}#{H(FOUR)[:12]}", f"{W13_4RUNG}#{H(W13_4RUNG)[:12]}"],
    severity="low",
    event_id=events.det_id("blocker", "path-collision", LEAD, H(LEAD))))

rec(events.emit_status(
    "N0", "active", HOURS,
    "Lifecycle close-out: lead adjudication re-published at "
    f"{LEAD}#{H(LEAD)[:12]} after a dual-assigned-path collision; worker-13's worker-level "
    "proposal at the collided path is accepted as consistent. G-NUM proposal remains "
    "pass_conditional: C1-C7 satisfied on artifact-backed evidence, C8 (independent reviewer "
    "verdict on " + f"{PROTOCOL}#{H(PROTOCOL)[:12]}" + " rev2) is the exact unmet criterion. "
    "N1 stays locked; no self-gravitating code exists.",
    [f"{LEAD}#{H(LEAD)[:12]}", f"{PROTOCOL}#{H(PROTOCOL)[:12]}",
     f"{COLLIDED}#{H(COLLIDED)[:12]}",
     "reviews/G-NUM-protocol-review.json (absent)"],
    "a reviewer rejects the rev-2 protocol; G-FORM/G-AUDIT stay pending and the lock stays "
    "closed; a 4-rung rerun at pinned hashes disagrees above the R5 floor",
    event_id=events.det_id("status", "closeout", LEAD, H(LEAD))))

Path(REPO / "artifacts/numerics/lifecycle_events_fixup_20260912.jsonl").write_text(
    "\n".join(json.dumps(e, sort_keys=True) for e in emitted) + "\n")
print(f"emitted {len(emitted)} fixup events")
