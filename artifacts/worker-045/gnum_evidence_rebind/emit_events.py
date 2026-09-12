#!/usr/bin/env python3
"""Emit W045-GNUM-EVIDENCE-REBIND-01 events to comms/outbox/worker-045.jsonl.

Validates every event with research_map/schemas.validate_event before append; refuses
to write a line that does not validate. Does NOT run comms.py ingest (controller-owned).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

OUT = ROOT / "comms" / "outbox" / "worker-045.jsonl"
CST = timezone(timedelta(hours=8))
TS = datetime.now(CST).isoformat(timespec="seconds")
TAG = TS.replace("-", "").replace(":", "")[:13]
ACTOR = "worker-045"
NODE = "N0"
GATE = "G-NUM"
CLASS = "AF-WCC-SCALAR-SPH"
SNAP = "a2585ffc2152da9ada4a32ea10bc61bc56b2472cc117f31ae234b3d8b4f10168"

A = {
    "report": ("artifacts/worker-045/gnum_evidence_rebind/report.json",
               "502a891c8e1d3c19062bfddffee19ee3fe2897244e5dc8617a0f1d7edc7af5df",
               "gate_evidence_rebind_report"),
    "controls": ("artifacts/worker-045/gnum_evidence_rebind/controls.json",
                 "5c15e03339af60fac4b88bf8fbe707031780348a3151475bbde876eacee668b1",
                 "control_battery"),
    "runner": ("artifacts/worker-045/gnum_evidence_rebind/run_gnum_evidence_rebind.py",
               "d18498b44fdb5a55123530d8f6f900d6dc1a236a90c8fb3548e9b5b1557086c6",
               "audit_instrument"),
    "checkpoint": ("artifacts/worker-045/gnum_evidence_rebind/checkpoint.json",
                   "06ae95730ffb40e943c5de1f53f4b1ba7d510d2e936e285920777060e20f4216",
                   "worker_checkpoint"),
    "snapshot": ("artifacts/worker-045/gnum_evidence_rebind/map_snapshot.json",
                 SNAP, "map_snapshot_pin"),
    "readme": ("artifacts/worker-045/gnum_evidence_rebind/README.md",
               "45acadc57698e1d1e019e6d16c383768f14dad2533fb9d08d3b45107fe4e9a84",
               "method_and_findings"),
    "runtime_checkpoint": ("runtime/state/w045_gnum_evidence_rebind_checkpoint.json",
                           "06ae95730ffb40e943c5de1f53f4b1ba7d510d2e936e285920777060e20f4216",
                           "worker_checkpoint_mirror"),
}
EVID = [f"{p}#{h[:12]}" for p, h, _ in A.values()]

events = []


def art(key, event_id):
    p, h, t = A[key]
    return {
        "event_id": event_id, "event_type": "artifact", "created_at": TS, "actor": ACTOR,
        "node_id": NODE, "gate": GATE, "class_id": CLASS, "class_ids": [CLASS],
        "artifact_type": t, "path": p, "sha256": h, "validation_status": "unverified",
        "authority_note": "Worker artifact event: does not set status=done, validation_status=passed or any gate verdict.",
    }


events.append(art("report", f"w045-art-{TAG}-gnum-rebind-report"))
events.append(art("controls", f"w045-art-{TAG}-gnum-rebind-controls"))
events.append(art("runner", f"w045-art-{TAG}-gnum-rebind-runner"))
events.append(art("checkpoint", f"w045-art-{TAG}-gnum-rebind-checkpoint"))
events.append(art("snapshot", f"w045-art-{TAG}-gnum-rebind-snapshot"))
events.append(art("readme", f"w045-art-{TAG}-gnum-rebind-readme"))
events.append(art("runtime_checkpoint", f"w045-art-{TAG}-gnum-rebind-runtime-checkpoint"))

events.append({
    "event_id": f"w045-claim-{TAG}-gnum-rebind",
    "event_type": "claim",
    "created_at": TS,
    "actor": ACTOR,
    "node_id": NODE,
    "gate": GATE,
    "class_id": CLASS,
    "class_ids": [CLASS],
    "conclusion_type": "formal_model",
    "statement": (
        "Artifact-and-checker measurement (not a mathematics claim, not a gate verdict) at the "
        f"pinned settled map snapshot research_map/research_map.json#{SNAP[:12]} "
        "(astra-life08-gate-gnum, updated_at 2026-09-12T01:16:25+08:00): of the 45 G-NUM "
        "evidence refs, 18 are self-binding MATCH, 5 are HISTORICAL_DECLARED revision/review "
        "pins, 19 are BARE and 2 AMBIGUOUS key-path refs, and exactly 1 is an unexplained stale "
        "pin (numerics/tests/n0_gate_proposal.json#22d984781cee: live bytes b4192221ff7d, "
        "fragment absent from the file, from name-matching artefact paths and from git history "
        "for that path). The gate still binds the superseded leadverify record "
        "numerics/protocol/n0_gate_proposal_leadverify.json#e0f9ef9f329d and no ref carries the "
        "live successor ea4cf6c9bd3c2092, which the registry records at "
        "runtime/state/artifact_hashes.json; the successor's own supersedes block documents "
        "this stale-pin set. The controller's current C8 expression "
        "(reviewed_sha256 or artifact_sha256) reproduces BOUND against the measured protocol "
        "hash 1e6cdf04d7a2, while the legacy top-level artifact_sha256 expression reads "
        "unbound. numerics_lock is locked, no solver path exists, and the run stayed inside "
        "N0/flat-space scope."
    ),
    "assumptions": [
        "a hash fragment is a prefix of the referenced file's own sha256, except where the file itself declares it as a revision/review pin",
        "a non-hex fragment (e.g. #controller_gate_audit) is a key path, not a pin",
        "the pinned map snapshot is byte-identical to the live map across the settled window",
        "discharge of gate unmet items and every gate verdict remain lead-audit/controller authority",
    ],
    "falsifier": (
        "Void if a re-run of run_gnum_evidence_rebind.py at snapshot " + SNAP[:12] +
        " yields any different classification bucket; void if sha256(map_snapshot.json) != " +
        SNAP[:12] + "; void if an independent reviewer finds a ref called MATCH whose live "
        "bytes do not start with the declared fragment; void if controls C1-C11b do not "
        "reproduce all_pass=true; withdrawn as a live finding if a later snapshot re-pins the "
        "leadverify successor and disposes of 22d984781cee."
    ),
    "evidence_refs": EVID,
    "artifact_refs": [{"path": p, "sha256": h} for p, h, _ in A.values()],
})

events.append({
    "event_id": f"w045-review-{TAG}-gnum-rebind",
    "event_type": "review",
    "created_at": TS,
    "actor": ACTOR,
    "reviewer": ACTOR,
    "node_id": NODE,
    "gate": GATE,
    "class_id": CLASS,
    "class_ids": [CLASS],
    "target_id": f"gates[G-NUM]@research_map/research_map.json#{SNAP[:12]}",
    "verdict": "revise",
    "score": 3.5,
    "hard_failures": ["W045-GER-01", "W045-GER-03", "W045-GER-08"],
    "findings": [
        "W045-GER-01 (major): unexplained stale pin numerics/tests/n0_gate_proposal.json#22d984781cee; live file b4192221ff7d; fragment not in file bytes, not relocated on disk, not in git history for the path.",
        "W045-GER-03 (major): gate binds superseded numerics/protocol/n0_gate_proposal_leadverify.json#e0f9ef9f329d; live successor ea4cf6c9bd3c2092 is not bound by any ref.",
        "W045-GER-08 (major, same root cause as GER-03): registry-current revision of the leadverify path is not bound by any gate hash ref.",
        "W045-GER-04b (info): C8 binds only via reviewed_sha256; the review has no top-level artifact_sha256, so the legacy expression reads unbound.",
        "Five further non-self-binding pins are HISTORICAL_DECLARED (declared in the artefact's own bytes) and are provenance, not defects; the gate list is a revision log rather than a live pin set.",
        "Controls C1-C11b all pass; C7 external sha256sum agrees on 3 live files; measurement deterministic across two runs on the pinned snapshot.",
        "Pass-08 already cleared the earlier unmet[] inconsistency and added reviews/G-NUM-protocol-review.json#8137f18f1a3b2b01; the leadverify divergence and 22d984781cee survive it.",
    ],
    "scope_limit": "Read-only binding measurement of one gate record; no adjudication of C8, the N0 node verdict, cnfd/cnfem triage or the 4-rung order claim.",
})

events.append({
    "event_id": f"w045-blocker-{TAG}-gnum-rebind",
    "event_type": "blocker",
    "created_at": TS,
    "actor": ACTOR,
    "node_id": NODE,
    "gate": GATE,
    "class_id": CLASS,
    "class_ids": [CLASS],
    "description": (
        "G-NUM evidence binding (worker-level blocker, not a gate verdict): one unexplained "
        "stale pin (numerics/tests/n0_gate_proposal.json#22d984781cee) and an unresolved "
        "leadverify successor chain (gate binds e0f9ef9f329d; live/registry successor "
        "ea4cf6c9bd3c2092 unbound). A reviewer resolving the N0 verification-of-record from "
        "the gate lands on the superseded record."
    ),
    "needed_to_unblock": (
        "Re-pin gates[G-NUM].evidence_refs to numerics/protocol/n0_gate_proposal_leadverify.json"
        "#ea4cf6c9bd3c2092 and mark the e0f9ef9f329d ref superseded; decide the disposition of "
        "22d984781cee (provenance note, since its bytes are not recoverable at that path); "
        "optionally add top-level artifact_sha256 to reviews/G-NUM-protocol-review.json."
    ),
    "evidence_refs": EVID,
})

events.append({
    "event_id": f"w045-status-{TAG}-gnum-rebind",
    "event_type": "status",
    "created_at": TS,
    "actor": ACTOR,
    "node_id": NODE,
    "gate": GATE,
    "class_id": CLASS,
    "class_ids": [CLASS],
    "status": "active",
    "hours": 0.7,
    "summary": (
        "W045-GNUM-EVIDENCE-REBIND-01 complete at worker level (no node/gate transition "
        "claimed). VERDICT revise 3.5 on the G-NUM evidence binding at snapshot "
        f"{SNAP[:12]}: 18 MATCH / 5 HISTORICAL_DECLARED / 1 STALE_UNEXPLAINED / 19 BARE / 2 "
        "AMBIGUOUS, one registry divergence (leadverify successor unbound), C8 BOUND via the "
        "current reviewed_sha256 expression and UNBOUND via the legacy artifact_sha256 "
        "expression, controls C1-C11b all pass, deterministic across two runs, settled window "
        "and zero drift. Six hash-pinned deliverables plus a runtime checkpoint; feeds "
        "astra-life04-n0-verify."
    ),
    "evidence_refs": EVID,
    "next_falsifier": (
        "Void if a re-run at snapshot " + SNAP[:12] + " yields any different classification "
        "bucket for any ref, or if sha256(map_snapshot.json) != " + SNAP[:12] + "."
    ),
})

with OUT.open("a", encoding="utf-8") as fh:
    for e in events:
        validate_event(e)
        fh.write(json.dumps(e, sort_keys=False) + "\n")

print(json.dumps({
    "appended": len(events),
    "outbox": str(OUT.relative_to(ROOT)),
    "event_ids": [e["event_id"] for e in events],
}, indent=1))
