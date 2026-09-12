#!/usr/bin/env python3
"""Emit the W087-GFORM-STAGE2-BINDING-01 event batch to comms/outbox/worker-087.jsonl.

Hashes are measured from disk at emission time; every event is validated against
research_map.schemas.validate_event before the batch is appended. Idempotent per event_id:
re-running appends nothing new if the ids are already present in the outbox file.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

OUTBOX = ROOT / "comms" / "outbox" / "worker-087.jsonl"
T = "2026-09-12T01:24:30+08:00"
TAG = "w087-stage2bind-20260912T012430"


def h(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def hp(rel: str) -> str:
    return f"{rel}#sha256:{h(rel)[:16]}"


EV = {}


def ev(**kw):
    EV[kw["event_id"]] = kw


CHECKPOINT = "runtime/state/worker-087_stage2_binding_checkpoint.json"
D = "artifacts/worker-087/stage2_binding"
EVID = [
    f"artifacts/formulation/FROZEN.json#sha256:{h('artifacts/formulation/FROZEN.json')[:12]}",
    f"{D}/report.json#sha256:{h(D + '/report.json')[:12]}",
    f"artifacts/worker-06/spec_conformance_audit.py#sha256:{h('artifacts/worker-06/spec_conformance_audit.py')[:12]}",
    f"artifacts/formulation/tools/run_acceptance.py#sha256:{h('artifacts/formulation/tools/run_acceptance.py')[:12]}",
    f"artifacts/formulation/evidence/semantic_escape_rebased.json#sha256:{h('artifacts/formulation/evidence/semantic_escape_rebased.json')[:12]}",
    f"artifacts/formulation/evidence/acceptance_pipeline_report.json#sha256:{h('artifacts/formulation/evidence/acceptance_pipeline_report.json')[:12]}",
    f"schemas/af_wcc_vacuum.yaml#sha256:{h('schemas/af_wcc_vacuum.yaml')[:12]}",
]
FALSIFIER = (
    "Falsified if the stage-2 path is a key of FROZEN.json.files with matching hash; the stage-2 "
    "hash occurs in FROZEN.json; a pipeline tool compares w06_sha256/gate_sha256 before execution; "
    "K2 fails to flip the F1 verdict on byte-identical input at the same pins; or any declared pin "
    "moves. A rev30 that pins the engine path+hash voids this measurement at that revision.")

ev(event_id=f"{TAG}-status-start", event_type="status", created_at=T, actor="worker-087",
   node_id="F1,F2a,F2b", class_ids=["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
   gate="G-FORM", status="active", hours=0.0,
   summary=("No inbox card exists for worker-087 (launched 01:15:07). Took ONE bounded class-bound task "
            "W087-GFORM-STAGE2-BINDING-01: read-only measurement of whether the G-FORM stage-2 semantic "
            "engine is bound by FROZEN rev29 pins, triggered by lead-form-20260912T011509-123 and "
            "CF-32/REC-36/REC-41 (astra-life08-stageb-r03 touches the same unpinned tree). "
            "Preregistration frozen before the first run; AMEND-01 reclassifies the live registry as a "
            "live input after the first run aborted on its 15-minute-cycle movement."),
   evidence_refs=EVID, next_falsifier=FALSIFIER)

for path, typ, note in [
    (f"{D}/PREREGISTRATION.json", "preregistration", "question, pins, H1-H5, K1-K6, decision rule, falsifier"),
    (f"{D}/AMENDMENT-01.json", "amendment", "registry pin -> live input; disclosed before the amended run"),
    (f"{D}/verify_stage2_binding_087.py", "instrument", "deterministic stdlib-only read-only harness; fail-closed pin gate"),
    (f"{D}/report.json", "report", "full machine record: pin census, H1-H5, K1-K6, mutant diff, verdicts"),
    (f"{D}/runs.json", "raw-runs", "six raw engine captures (K1,K1b,K2,K2b,K3,K4)"),
    (f"{D}/README.md", "readme", "human summary, table, falsifier, non-claims, reproduce command"),
    (f"{D}/SHA256SUMS", "checksums", "sha256 manifest over the task deliverables"),
    (f"{D}/emit_events_087.py", "emitter", "validated event emitter, idempotent by event_id"),
    (f"{D}/sandbox/artifacts/worker-06/spec_conformance_audit.mutant.py", "sensitivity-probe-mutant",
     "PROBE ONLY: one-line relaxed containment predicate; not a proposed fix, not adopted"),
    (CHECKPOINT, "worker_checkpoint_state_copy", "task, pins, verdict, facts, deliverable hashes, next falsifier"),
]:
    ev(event_id=f"{TAG}-artifact-{Path(path).name}", event_type="artifact", created_at=T, actor="worker-087",
       node_id="F1,F2a,F2b", class_ids=["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
       gate="G-FORM", path=path, sha256=h(path), artifact_type=typ, validation_status="unverified",
       note=note, evidence_refs=[f"{path}#sha256:{h(path)[:12]}"])

ev(event_id=f"{TAG}-claim", event_type="claim", created_at=T, actor="worker-087",
   node_id="F1,F2a,F2b", class_id="AF-WCC-VAC-GEN",
   class_ids=["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"], gate="G-FORM",
   conclusion_type="formal_model", counts_toward_gate_accept=False,
   statement=("Instrument-binding measurement, not a mathematics or physics claim. At FROZEN rev29 "
              "815e0807, the stage-2 semantic engine artifacts/worker-06/spec_conformance_audit.py "
              "(live c79d8ab8440a) is NOT a key of FROZEN.json.files (50 pins) and its hash has 0 "
              "occurrences in FROZEN.json. The pinned pipeline tool run_acceptance.py resolves it by "
              "path (line 10) and its only sha256 call (line 61, preflight) is over the C0 corpus base, "
              "never the engine; the pinned acceptance_pipeline_report.json records only stage paths. "
              "The engine hash appears exactly once in the 50 pinned bodies, as provenance field "
              "w06_sha256 inside the pinned but stale corpus semantic_escape_rebased.json, and no "
              "pipeline tool reads or compares that field (H2 as literally preregistered is therefore "
              "false; the other four hypotheses hold). On byte-identical input (doc_sha256 d9cebb9404b2) "
              "the live engine returns reject/R03 while a one-line mutated copy returns accept, with all "
              "pins byte-stable and 8/8 controls passing. Conclusion: a stage-2 edit silently changes "
              "the F1 verdict under an unchanged pin set; lead-form-20260912T011509-123 is confirmed as "
              "stated, refined to declared-but-unverified rather than unreferenced anywhere."),
   assumptions=[
       "run_acceptance.py would execute the stage-2 file at the path it names; verified by static read "
       "and AST (sole sha256 call in preflight over the C0 base). run_acceptance.py was deliberately not "
       "executed because it unconditionally rewrites the pinned acceptance_pipeline_report.json.",
       "the mutation is a sensitivity probe, not a proposed fix or adopted instrument, and makes no "
       "claim about the correct R03 semantics.",
       "w06_sha256 in the pinned corpus is treated as a declaration, not an enforced binding, because no "
       "tool consumes it.",
   ],
   falsifier=FALSIFIER, evidence_refs=EVID,
   artifact_refs=[f"{D}/report.json#sha256:{h(D + '/report.json')[:16]}",
                  f"{D}/verify_stage2_binding_087.py#sha256:{h(D + '/verify_stage2_binding_087.py')[:16]}",
                  f"{D}/runs.json#sha256:{h(D + '/runs.json')[:16]}"],
   refinement=("literal preregistered verdict NOT_CONFIRMED (H2 falsified by one provenance field); "
               "operative_gap_confirmed=true on H1,H3,H3b,H4,H5 + 8/8 controls + 0 pin drift"))

ev(event_id=f"{TAG}-review-blocker", event_type="review", created_at=T, actor="worker-087",
   reviewer="worker-087", target_id="lead-form-20260912T011509-123", node_id="F1,F2a,F2b",
   class_ids=["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"], gate="G-FORM",
   verdict="accept", score=4.0, counts_toward_gate_accept=False, hard_failures=[],
   findings=[
       "Confirmed as stated: stage-2 engine not in FROZEN.json.files; 0 occurrences in FROZEN.json; "
       "run_acceptance.py resolves it by path with no hash check; editing only that file flips the "
       "frozen F1 stage-2 verdict reject/R03 -> accept on identical input bytes while all 50 pins stay "
       "byte-stable (K2, mutant sha256 5273ae2f8665; input doc_sha256 unchanged d9cebb9404b2).",
       "Refinement from this worker's own preregistered test: the engine hash IS declared once as "
       "w06_sha256 in the pinned, stale corpus artifacts/formulation/evidence/semantic_escape_rebased.json "
       "(base_sha256 1bb78ce9 vs live C0 b2ab6acb), and no pipeline tool reads it. 'ZERO occurrences in "
       "FROZEN.json' and 'invisible to pin verification' are confirmed; 'unreferenced anywhere' would be "
       "false, so the blocker should carry the declared-but-unverified qualification.",
       "Scope: instrument binding only. No statement on R03's mathematical correctness or on the "
       "worker-006 binder fix under astra-life08-stageb-r03.",
   ],
   evidence_refs=EVID)

ev(event_id=f"{TAG}-blocker-binding", event_type="blocker", created_at=T, actor="worker-087",
   node_id="F1,F2a,F2b", class_ids=["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
   gate="G-FORM",
   description=("Stage-2 gate evidence binds no instrument identity at FROZEN rev29: "
                "spec_conformance_audit.py c79d8ab8440a is unpinned and unverified while its verdict "
                "decides the canonical F1 acceptance (K2 flip on identical bytes). The single hash "
                "declaration (w06_sha256 in the pinned but stale corpus) is read by nothing; the R03 fix "
                "assigned under astra-life08-stageb-r03 will land in this unpinned tree."),
   needed_to_unblock=("Owner at rev14/FROZEN rev30: add artifacts/worker-06/spec_conformance_audit.py "
                      "path+sha256 to the FROZEN pin map after the R03 fix, OR make run_acceptance.py fail "
                      "closed (nonzero) when the live engine hash differs from the declared w06_sha256, so "
                      "gate evidence binds instrument identity. Until then no stage-2 verdict should be "
                      "treated as pinned gate evidence (CF-32/REC-41)."),
   evidence_refs=EVID)

ev(event_id=f"{TAG}-status-exit", event_type="status", created_at=T, actor="worker-087",
   node_id="F1,F2a,F2b", class_ids=["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
   gate="G-FORM", status="active", hours=1.0,
   summary=("W087-GFORM-STAGE2-BINDING-01 complete at worker level: one bounded class-bound task, "
            "read-only on every canonical path. Literal preregistered verdict NOT_CONFIRMED (H2 "
            "over-strict, falsified by one provenance declaration); operative gap CONFIRMED: stage-2 "
            "engine unpinned and unverified, verdict flips reject/R03 -> accept when only the unpinned "
            "file changes, 8/8 controls, 0 pin drift. Lead blocker confirmed with the "
            "declared-but-unverified qualification. Checkpoint written; EXIT."),
   evidence_refs=EVID,
   next_falsifier=("rev30 pinning the stage-2 path+sha256, or a run_acceptance.py that fails closed on a "
                   "stage-2 hash mismatch; also verify whether the rev14 corpus rebind re-declares "
                   "w06_sha256 without adding enforcement"))

if __name__ == "__main__":
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:  # noqa: BLE001
                continue
    new = [e for e in EV.values() if e["event_id"] not in existing]
    for e in new:
        validate_event(dict(e))
    with OUTBOX.open("a") as f:
        for e in new:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(json.dumps({"emitted": len(new), "skipped_existing": len(EV) - len(new),
                      "event_ids": [e["event_id"] for e in new]}, indent=1))
