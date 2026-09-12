#!/usr/bin/env python3
"""Emit W063-F2B-CLOSE-AUDIT-01 events to comms/outbox/worker-063.jsonl.

Fail-closed: every referenced artifact is re-hashed on disk and must match the sha256 the
event declares; every event is validated with research_map/schemas.validate_event before a
single byte is appended; an event_id already present in the outbox or in the accepted
stream is skipped (idempotent re-run).  Ids, evidence, hashes and the falsifier are carried
on every record.  Worker authority only: status remains `active`, validation_status stays
`unverified`, no gate verdict.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

OUTBOX = ROOT / "comms" / "outbox" / "worker-063.jsonl"
EVENTS = ROOT / "research_map" / "events.jsonl"
HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
T = "20260912T0115"
CLASS = "AF-SCC-C0-VAC-GEN"
NODE = "F2b"
GATE = "G-FORM"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def art(name: str, rel: str, atype: str, summary: str, evidence: list[str]) -> dict:
    p = HERE / rel
    digest = sha256_file(p)
    return {
        "event_id": f"w063-artifact-f2bclose-{name}-{T}",
        "event_type": "artifact",
        "created_at": now(),
        "actor": "worker-063",
        "class_id": CLASS,
        "node_id": NODE,
        "gate": GATE,
        "artifact_type": atype,
        "path": f"artifacts/worker-063/f2b_close_audit/{rel}",
        "sha256": digest,
        "validation_status": "unverified",
        "summary": summary,
        "evidence_refs": evidence + [f"artifacts/worker-063/f2b_close_audit/{rel}#{digest[:12]}"],
    }


def main() -> int:
    checkpoint_rel = "artifacts/worker-063/f2b_close_audit/CHECKPOINT.json"
    checkpoint_sha = sha256_file(ROOT / checkpoint_rel)

    events = [
        art("report", "report.json", "f2b_rev14_close_audit_report",
            "Frozen close-audit of the pending containment-only F2b rev14: 25 hard-failure records at F2b rev13/FROZEN rev29 "
            "normalised to 8 carrier families; both published candidates change exactly the two containment leaves, so a "
            "containment-only rev14 closes 2/8 families and leaves 5 live (C_VOCAB, C_A2, C_A6, C_PIPE, C_STREAM); C_SEP6 was "
            "closed mid-audit by the owner's aggregator revision 7. Controls K1-K6 pass; pins stable during the run.",
            [f"{checkpoint_rel}#{checkpoint_sha[:12]}",
             "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
             "artifacts/formulation/FROZEN.json#815e08079aef"]),
        art("runner", "run_close_audit_063.py", "close_audit_runner",
            "Frozen-before-measurement runner: 21 pinned inputs, independent YAML leaf-path diff, hard-failure extraction from "
            "pinned reviews plus byte-verbatim event snapshots, path-prefix join, per-family measured liveness, controls K1-K6, "
            "fail-closed exit 3 on pin drift and end-of-run stability check.",
            ["artifacts/worker-063/f2b_close_audit/report.json#b32211ef1c40"]),
        art("emitter", "emit_events_063.py", "event_emission_harness",
            "Fail-closed emitter for this task's events: validates every event against research_map/schemas.validate_event, "
            "re-hashes every referenced artifact and evidence ref against its declared hash prefix before appending, and skips "
            "event_ids already present (idempotent).",
            ["artifacts/worker-063/f2b_close_audit/report.json#b32211ef1c40"]),
        art("matrix", "matrix.tsv", "close_audit_matrix",
            "Family x (hf_records, distinct_sources, touched_by_candidate, defect_live, closing_actor) matrix.",
            ["artifacts/worker-063/f2b_close_audit/report.json#b32211ef1c40"]),
        art("reviewsnapshot", "evidence/review_events_snapshot.json", "frozen_review_events_snapshot",
            "Byte-verbatim snapshot of 6 accepted-stream reviews/blockers used by the audit (w044, w095, w062, w017, "
            "lead-form-005743-91, w047); each event carries its source line and canonical sha256 and is re-verified by the runner.",
            ["artifacts/worker-063/f2b_close_audit/run_close_audit_063.py#8586f1890d30"]),
        art("ownerblocker", "evidence/owner_blocker_snapshot.json", "frozen_owner_blocker_snapshot",
            "Byte-verbatim snapshot of lead-form-20260912T0113-106: the formulation lead's own 01:13 blocker reproducing the "
            "C_PIPE acceptance-pipeline base-binding defect at rev29.",
            ["artifacts/worker-063/f2b_close_audit/run_close_audit_063.py#8586f1890d30"]),
        art("checkpoint", "CHECKPOINT.json", "worker_checkpoint",
            "Authoritative worker checkpoint: verdict CONTAINMENT_ONLY_REV14_CLOSES_2_OF_8__5_LIVE__1_CLOSED_MID_AUDIT; artifact "
            "hash table, start/end pin verification, mid-audit move record, K1-K6 controls, claimed_event_ids.",
            ["artifacts/worker-063/f2b_close_audit/report.json#b32211ef1c40"]),
    ]

    claim = {
        "event_id": f"w063-claim-f2bclose-{T}",
        "event_type": "claim",
        "created_at": now(),
        "actor": "worker-063",
        "class_id": CLASS,
        "node_id": NODE,
        "gate": GATE,
        "conclusion_type": "formal_model",
        "statement": (
            "Worker artifact-and-record measurement, not a mathematics claim, at FROZEN rev29 815e08079aef and canonical F2b "
            "b2ab6acb2bbe: a rev14 carrying only the two validated containment edits (regularity.must_not_conflate[0] stale "
            "denial; implication_ledger.forbidden_transfers[0].reason inverted size premise) closes 2 of the 8 open F2b "
            "hard-failure carrier families in the frozen review record (25 records, 8 sources) and leaves 5 live: "
            "C_VOCAB_conclusion_token (F2b holds VOCAB_ALIASES canonical tokens scc_c0_future_inextendibility and "
            "residual_comeager while the G-F0 canonical field_vocabulary allows only their aliases; no rule can satisfy both "
            "frozen artifacts), C_A2_evidence_self_verification (taxonomy_consistency.json is 495 bytes with zero embedded "
            "sha256), C_A6_alias_registry_binding (f0_binding carries no VOCAB_ALIASES pointer although the registry is "
            "FROZEN-pinned), C_PIPE_acceptance_base_binding (semantic_escape_rebased.json binds rev11 base 1bb78ce9b357 vs "
            "live b2ab6acb2bbe; acceptance_pipeline_report.json records PASS with no base bytes), and C_STREAM_ordering_shadow "
            "(future-dated null-stamped event w06-20260912T0115-f2b-rev6 carries a stale C0 hash). C_SEP6 was live at frame "
            "time and was closed during the audit by the owner's aggregator revision 7 27255e5b34f3, whose declared "
            "supersedes_sha256 equals this audit's frame pin. Both published candidates change exactly 2 lines / 2 leaves, "
            "independently reproduced. No gate verdict, no node status; the prediction is that a containment-only rev14 "
            "returns further revise verdicts from the same sources unless the other families are edited or ruled out before "
            "re-freeze."
        ),
        "assumptions": [
            "the pinned bytes are authoritative and any drift voids the binding (runner exits 3)",
            "a reviewer hard failure is treated as a live defect iff it is still measurable in the frozen bytes; the audit does not re-adjudicate reviewer correctness",
            "path-prefix equality on the current YAML layout is a faithful carrier join; a future re-layout can move a carrier without moving the defect",
            "C_A2/C_A6/C_SEP6/C_STREAM rest on single advisory sources at frame time (C_PIPE also has the lead's own 01:13 blocker); C_VOCAB and the containment families are multi-reviewer",
        ],
        "falsifier": (
            "FALSIFIED IF any of: (a) a pinned input differs from its recorded sha256 (runner exits 3); (b) the changed-leaf join "
            "misclassifies a containment carrier or a non-containment carrier (K1/K2 fail); (c) any family recorded live is shown "
            "closed at the pinned bytes by a frozen adjudication or corrected bytes; (d) a rev14 lands that already carries "
            "C_VOCAB/C_A2/C_A6/C_PIPE/C_SEP6 edits or a ruling closes them; (e) the frozen review record contains a hard-failure "
            "family not enumerated here; or (f) a containment-only rev14 nevertheless returns two clean accepts at a stable new hash."
        ),
        "evidence_refs": [
            "artifacts/worker-063/f2b_close_audit/report.json#b32211ef1c40",
            "artifacts/worker-063/f2b_close_audit/matrix.tsv#09b3ece2b48b",
            "artifacts/worker-063/f2b_close_audit/evidence/review_events_snapshot.json#d9767b63dbc6",
            "artifacts/worker-063/f2b_close_audit/evidence/owner_blocker_snapshot.json#cb5f277e9208",
            "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
            "artifacts/formulation/FROZEN.json#815e08079aef",
            "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
            "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534",
            "artifacts/formulation/evidence/semantic_escape_rebased.json#7e44de0e3906",
            "artifacts/formulation/evidence/acceptance_pipeline_report.json#9b7d6c8208d3",
            "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
            "schemas/af_scc_regularities.yaml#27255e5b34f3",
        ],
        "artifact_refs": [
            "artifacts/worker-063/f2b_close_audit/report.json#b32211ef1c40",
            "artifacts/worker-063/f2b_close_audit/matrix.tsv#09b3ece2b48b",
            "artifacts/worker-063/f2b_close_audit/evidence/review_events_snapshot.json#d9767b63dbc6",
            "artifacts/worker-063/f2b_close_audit/evidence/owner_blocker_snapshot.json#cb5f277e9208",
        ],
        "expected_information_gain": (
            "Tells the controller/formulation owner whether the pending containment-only rev14 can close F2b before the r3 budget "
            "is spent: it cannot (2/8), and the five remaining families are enumerated with the actor that can close each, so "
            "rev14 scope or a ruling set can be fixed once instead of iterating hash-moving revisions."
        ),
        "hours": 0.35,
    }

    blocker = {
        "event_id": f"w063-blocker-f2bclose-rev14-scope-{T}",
        "event_type": "blocker",
        "created_at": now(),
        "actor": "worker-063",
        "class_id": CLASS,
        "node_id": NODE,
        "gate": GATE,
        "description": (
            "rev14 scope decision required before the r3 F2b budget: a containment-only rev14 closes 2/8 open F2b carrier "
            "families and leaves 5 live at the frozen bytes (C_VOCAB conclusion/genericity token single-sourcing; C_A2 "
            "taxonomy_consistency.json pins neither input; C_A6 f0_binding has no VOCAB_ALIASES pointer; C_PIPE "
            "semantic_escape_rebased binds rev11 base 1bb78ce9b357 and acceptance_pipeline_report.json is unversioned; C_STREAM "
            "future-dated null-stamped event w06-20260912T0115-f2b-rev6 shadows the F2b pin). C_SEP6 is already closed by the "
            "owner's aggregator rev7. Recommendation: fold the C_PIPE rebase/version-stamp, the C_A2 self-verification fields "
            "and the C_A6 registry binding into the same rev14, and record the C_VOCAB single-sourcing ruling; then re-freeze "
            "and spend one review round."
        ),
        "needed_to_unblock": (
            "Formulation owner: widen rev14 to C_PIPE + C_A2 + C_A6 as above (C_H1/C_H2 already carried by both validated "
            "candidates) and re-freeze FROZEN; controller/gate owner: record the C_VOCAB single-sourcing ruling and the C_STREAM "
            "ordering/quarantine rule. No F2b schema change is requested by this worker; measurement only."
        ),
        "evidence_refs": [
            "artifacts/worker-063/f2b_close_audit/report.json#b32211ef1c40",
            "artifacts/worker-063/f2b_close_audit/matrix.tsv#09b3ece2b48b",
            "artifacts/worker-063/f2b_close_audit/evidence/owner_blocker_snapshot.json#cb5f277e9208",
            "artifacts/worker-063/f2b_close_audit/evidence/review_events_snapshot.json#d9767b63dbc6",
            "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
            "schemas/af_scc_regularities.yaml#27255e5b34f3",
        ],
    }

    status = {
        "event_id": f"w063-status-f2bclose-{T}",
        "event_type": "status",
        "created_at": now(),
        "actor": "worker-063",
        "node_id": NODE,
        "class_id": CLASS,
        "gate": GATE,
        "status": "active",
        "hours": 0.35,
        "summary": (
            "No inbox card for worker-063. Took ONE bounded class-bound task, W063-F2B-CLOSE-AUDIT-01: does the pending "
            "containment-only F2b rev14 close F2b at FROZEN rev29? Built a frozen-before-measurement instrument (21 pins, "
            "independent YAML leaf-path diff, 25 hard-failure records from 8 pinned sources, 8 carrier families, measured "
            "liveness, K1-K6 controls all pass, pins stable during the run). Result: 2/8 families closed by the two candidate "
            "edits, 5 live, 1 (C_SEP6) closed mid-audit by the owner's aggregator rev7 with a confirmed supersedes chain. "
            "CHECKPOINT + EXIT; node status deliberately unchanged (worker events cannot set status=done, "
            "validation_status=passed, or a gate verdict)."
        ),
        "evidence_refs": [
            "artifacts/worker-063/f2b_close_audit/report.json#b32211ef1c40",
            f"{checkpoint_rel}#{checkpoint_sha[:12]}",
            "artifacts/worker-063/f2b_close_audit/matrix.tsv#09b3ece2b48b",
        ],
        "checkpoint_ref": f"{checkpoint_rel}#{checkpoint_sha[:12]}",
        "next_falsifier": (
            "A containment-only rev14 returning >=2 clean accepts at a stable new hash; or bytes/rulings closing "
            "C_VOCAB/C_A2/C_A6/C_PIPE/C_STREAM; or drift of any pinned input, in which case re-run the runner (exit 3 expected)."
        ),
    }

    events.append(claim)
    events.append(blocker)
    events.append(status)

    # ---- validate everything before writing ----
    errors = []
    for ev in events:
        try:
            validate_event(ev)
        except Exception as exc:  # SchemaError or ValueError
            errors.append(f"{ev.get('event_id')}: {exc}")
        for ref in ev.get("evidence_refs", []) + ev.get("artifact_refs", []):
            if "#" not in ref:
                errors.append(f"{ev.get('event_id')}: evidence_ref without hash: {ref}")
                continue
            rel, frag = ref.split("#", 1)
            p = ROOT / rel
            if not p.exists():
                errors.append(f"{ev.get('event_id')}: evidence path missing: {rel}")
                continue
            measured = sha256_file(p)
            if not measured.startswith(frag):
                errors.append(f"{ev.get('event_id')}: evidence hash mismatch {rel}: declared {frag}, measured {measured[:12]}")
    if errors:
        print(json.dumps({"status": "VALIDATION_FAILED", "errors": errors}, indent=2))
        return 2

    # ---- idempotent append ----
    existing = set()
    for src in (OUTBOX, EVENTS):
        if src.exists():
            with src.open() as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        existing.add(json.loads(line).get("event_id"))
                    except ValueError:
                        continue
    new = [ev for ev in events if ev["event_id"] not in existing]
    if new:
        if OUTBOX.exists() and OUTBOX.stat().st_size > 0 and not OUTBOX.read_bytes().endswith(b"\n"):
            with OUTBOX.open("ab") as fh:
                fh.write(b"\n")
        with OUTBOX.open("a") as fh:
            for ev in new:
                fh.write(json.dumps(ev, sort_keys=True) + "\n")
    print(json.dumps({
        "status": "EMITTED",
        "outbox": str(OUTBOX.relative_to(ROOT)),
        "appended": [ev["event_id"] for ev in new],
        "skipped_existing": [ev["event_id"] for ev in events if ev["event_id"] in existing],
        "checkpoint_sha256": checkpoint_sha,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
