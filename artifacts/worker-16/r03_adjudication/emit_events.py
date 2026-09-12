#!/usr/bin/env python3
"""Emit the W16-R03-ADJ-01 events to comms/outbox/worker-16.jsonl and write the
worker-local checkpoint. Idempotent by event_id / checkpoint_id.

Worker evidence only: cannot set node status=done, validation_status=passed, or a
gate verdict. No frozen byte is modified.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
HERE = os.path.join(ROOT, "artifacts/worker-16/r03_adjudication")
OUTBOX = os.path.join(ROOT, "comms/outbox/worker-16.jsonl")
CKPT = os.path.join(ROOT, "runtime/state/w016_checkpoint_r03_adjudication.json")
CKPT_LOG = os.path.join(ROOT, "runtime/state/w016_checkpoints.jsonl")
CKPT_MD = os.path.join(ROOT, "artifacts/worker-16/CHECKPOINTS.md")
TZ = timezone(timedelta(hours=8))
sys.path.insert(0, os.path.join(ROOT, "research_map"))
from schemas import validate_event  # noqa: E402


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def main():
    adj_path = os.path.join(HERE, "out/adjudication.json")
    raw_path = os.path.join(HERE, "out/raw_verdicts.json")
    rep_path = os.path.join(HERE, "REPORT.md")
    tool_path = os.path.join(HERE, "adjudicate_r03.py")
    patched_path = os.path.join(HERE, "tools/spec_conformance_audit_r03patch.py")
    man_path = os.path.join(HERE, "artifact_manifest.json")
    emit_path = os.path.join(HERE, "emit_events.py")
    adj = json.load(open(adj_path))
    H = {p: sha256_file(p) for p in (adj_path, raw_path, rep_path, tool_path, patched_path, man_path, emit_path)}

    F1 = "schemas/af_wcc_vacuum.yaml#sha256:cce9c60146d6"
    TOOL = "artifacts/worker-06/spec_conformance_audit.py#sha256:c79d8ab8440a"
    FROZEN = "artifacts/formulation/FROZEN.json#sha256:2f358f6722d9"
    RULE = "artifacts/formulation/rule_spec.json#sha256:40f9bb9e657b"
    ev = "artifacts/worker-16/r03_adjudication/out/adjudication.json#sha256:" + H[adj_path][:12]

    common = {
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "gate": "G-FORM",
        "group_id": "formulation",
        "run_id": "w16-r03-adj-01",
        "claims_completion": False,
        "authority_note": "worker event only; G-FORM verdicts remain lead-audit/controller authority",
    }

    def art(eid, atype, path, summary):
        return dict(common, event_id=eid, event_type="artifact", created_at=now(), actor="worker-16",
                    artifact_type=atype, path=path, sha256=H[path], validation_status="unverified",
                    evidence_refs=[f"{path}#sha256:{H[path][:12]}"],
                    summary=summary, next_falsifier="any byte change to this deliverable invalidates its hash binding")

    events = [
        art("w16-R03-ADJ-01-artifact-adjudication", "adjudication_report",
            adj_path, "R03 adjudication: baseline reject reproduced (R03 only); V1 literal rendering accepted by both stages; comment-only and unbound controls behave as declared; a variable-wise R03 implementation accepts the frozen bytes (doc_sha256 cce9c60146d6 unchanged); verdict = literal-match false positive of the R03 implementation plus a real cross-schema binder-rendering convention inconsistency."),
        art("w16-R03-ADJ-01-artifact-report", "report", rep_path,
            "Human-readable REPORT.md for W16-R03-ADJ-01 with sources, controls, resolution options A/B and falsifiers."),
        art("w16-R03-ADJ-01-artifact-raw-verdicts", "raw_evidence", raw_path,
            "Every stage-1/stage-2/patch invocation with exit code, parsed verdict and failed rules at pinned tool hashes."),
        art("w16-R03-ADJ-01-artifact-adjudicate-tool", "verification_tool", tool_path,
            "Deterministic adjudication harness (staged copies only; asserts frozen F1 sha256 before/after)."),
        art("w16-R03-ADJ-01-artifact-patched-tool", "verification_tool", patched_path,
            "Copy of spec_conformance_audit.py with ONLY the R03 binder-presence predicate changed to variable-wise use for composite binders; accepts frozen F1 and still rejects the unbound negative control V4."),
        art("w16-R03-ADJ-01-artifact-manifest", "artifact_manifest", man_path,
            "sha256 manifest of all W16-R03-ADJ-01 deliverables plus the staged variants and mirrored pinned tools."),
        art("w16-R03-ADJ-01-artifact-emit-events", "verification_tool", emit_path,
            "Idempotent emitter for the W16-R03-ADJ-01 events and the worker-local checkpoint (no frozen byte touched)."),
        dict(common, event_id="w16-R03-ADJ-01-review-f1-r03", event_type="review", created_at=now(),
             actor="worker-16", reviewer="worker-16", target_id=F1, verdict="revise", score=4,
             hard_failures=["W16R03-B1"],
             findings=[
                 "[B1 blocking] The adopted stage-2 tool rejects af_wcc_vacuum.yaml at the frozen hash on R03 only ('binder (q,t0) absent from formal sentence'). The schema content is semantically conforming (q,t0 are bound in the not_exists clause; D5 defines the pair domain), so the block is a conformance/convention blocker: resolve by Option A (variable-wise R03 implementation; measured patch accepts frozen bytes) or Option B (one-clause rendering change, which changes the F1 hash and voids current F1 reviews). Evidence: out/adjudication.json; out/raw_verdicts.json.",
                 "[N1 backlog] Cross-schema rendering inconsistency: F2a/F2b print composite binders literally, F1 renders '(q,t0)' variable-wise; the frozen corpus is not uniformly self-presenting under the adopted lexical checker.",
                 "[N2 backlog] rule_spec.json#40f9bb9e657b R03 says 'using those binders' without saying whether literal tuple printing is required; the spec should state the intended test so implementations converge.",
                 "[non-blocking] No class leak, no conclusion inflation, no C2 assumption import, no quantifier-ordering or domain-resolution defect detected in the audited R03 path; stage-1 R01-R16 pass on the frozen bytes.",
             ],
             evidence_refs=[ev, F1, TOOL, FROZEN, RULE],
             next_falsifier="A stage-2 run at cce9c60146d6 that accepts with the unpatched tool refutes the literal-match reading; a stage-1/stage-2 run showing q or t0 unbound, D5 unresolved, or a class-leak token refutes the no-content-defect reading."),
        dict(common, event_id="w16-R03-ADJ-01-review-r03-tool", event_type="review", created_at=now(),
             actor="worker-16", reviewer="worker-16", target_id=TOOL, verdict="revise", score=3,
             hard_failures=["W16R03-B1"],
             findings=[
                 "[B1] R03's predicate `b not in formal` (spec_conformance_audit.py:210-212) is a literal substring test; it false-positives composite binders rendered variable-wise, as measured on frozen F1 (V1 accepts, V2 comment-only rejects, V4 unbound rejects, patched variable-wise accepts frozen bytes and still rejects V4).",
                 "[N1] The tool should either implement variable-wise binder use or emit a distinct diagnostic that the frozen artifact uses the binder variables but does not print the literal tuple, so reviewers can adjudicate rather than fail.",
             ],
             evidence_refs=[ev, TOOL, RULE, "artifacts/worker-16/r03_adjudication/tools/spec_conformance_audit_r03patch.py#sha256:" + H[patched_path][:12]],
             next_falsifier="A fixture where variable-wise use is accepted while a declared variable is not actually bound (or vice versa) refutes the patch's correctness."),
        dict(common, event_id="w16-R03-ADJ-01-claim", event_type="claim", created_at=now(),
             actor="worker-16", class_id="AF-WCC-VAC-GEN", statement=(
                 "At FROZEN rev28 (sha256 2f358f6722d9), frozen F1 af_wcc_vacuum.yaml#cce9c60146d6 is rejected by the adopted stage-2 tool c79d8ab8440a on R03 only, because the binder string '(q,t0)' is not printed literally in quantifiers.formal. The frozen formal sentence does bind both q and t0, D5 resolves and defines the pair domain, and a one-clause semantics-preserving rendering (V1) or a variable-wise implementation of R03 (patched tool) is accepted. Therefore W16R28-F2 is adjudicated a literal-match false positive of the R03 implementation, with a real residual cross-schema binder-rendering convention inconsistency; it is not a class leak, conclusion inflation, or smuggled C2 assumption."),
             conclusion_type="formal_model",
             assumptions=["all runs at the pinned tool/rule/schema hashes listed in evidence_refs",
                          "tool-conformance adjudication, not a theorem and not a gate verdict",
                          "no frozen artifact byte modified; runs executed in a staged copy"],
             falsifier="Show frozen F1's not_exists clause fails to bind q or t0, or that D5 does not resolve, or that the pinned V1/V4 runs behave differently; or produce a run_acceptance.py exit 0 at the frozen bytes without amending tool or F1 (which would refute the stale-corpus diagnosis underlying W16R28-F1).",
             evidence_refs=[ev, F1, TOOL, RULE, FROZEN],
             artifact_refs=[ev]),
        dict(common, event_id="w16-R03-ADJ-01-status", event_type="status", created_at=now(),
             actor="worker-16", node_id="F1", status="active", hours=0.5,
             summary=("Self-claimed class-bound task complete (worker evidence; not a gate verdict). W16-R03-ADJ-01 adjudicates W16R28-F2: the stage-2 R03 rejection of frozen F1 cce9c60146d6 is a literal-match false positive of the R03 implementation (binder '(q,t0)' rendered variable-wise; both stages accept a one-clause literal rendering; a variable-wise R03 patch accepts the frozen bytes unchanged with doc_sha256 cce9c60146d6 and still rejects an unbound negative control). Residual real defect: cross-schema composite-binder rendering convention differs between F1 and F2a/F2b. Option A (amend R03, no frozen byte change) vs Option B (one-clause F1 change, new hash + re-review) is a lead/controller decision. W16R28-F1 (stale semantic corpus base 1bb78ce9 vs C0 55d0a1ea; run_acceptance.py exit 3) is NOT addressed and remains open. F2a/F2b re-checked accept at the frozen hashes."),
             evidence_refs=[ev, F1, TOOL, FROZEN, RULE,
                            "runtime/state/w016_checkpoint_r03_adjudication.json"],
             next_falsifier="A run_acceptance.py exit 0 at the frozen bytes without amending tool or F1; or a stage-2 accept at cce9c60146d6 with the unpatched tool; or a demonstrated unbound q/t0 in the frozen formal sentence."),
    ]

    for e in events:
        validate_event(e)

    os.makedirs(os.path.dirname(OUTBOX), exist_ok=True)
    existing = set()
    if os.path.exists(OUTBOX):
        for line in open(OUTBOX, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line)["event_id"])
            except Exception:
                pass
    appended = []
    with open(OUTBOX, "a", encoding="utf-8") as fh:
        for e in events:
            if e["event_id"] in existing:
                continue
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            appended.append(e["event_id"])

    # ---- worker-local checkpoint ---------------------------------------
    ckpt = {
        "checkpoint_id": "w16-ckpt-r03-adj-01",
        "worker": "worker-16", "worker_slot": "worker-016", "actor": "worker-16",
        "checkpoint_at": now(),
        "task": {"id": "W16-R03-ADJ-01", "self_claimed": True,
                 "reason": "no open worker-16 inbox card after the rev28 verification pass; W16R28-F2 needed adjudication and worker-004 had reported it as a blocker without a disposition",
                 "node_id": "F1", "class_ids": ["AF-WCC-VAC-GEN"], "gate": "G-FORM",
                 "budget_agent_hours": 0.5},
        "verdict": {
            "adjudication": adj["adjudication"]["verdict"],
            "frozen_revision": 28,
            "frozen_manifest_sha256": "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
            "stage1_frozen_F1": adj["baseline"]["frozen_F1_stage1"],
            "stage2_frozen_F1": adj["baseline"]["frozen_F1_stage2"],
            "stage2_failed_rules": adj["baseline"]["frozen_F1_stage2_failed_rules"],
            "V1_one_clause_literal_rendering": adj["V1_literal_binder"]["stage2"],
            "patched_tool_on_frozen_bytes": adj["patched_checker"]["frozen_F1_verdict"],
            "patched_tool_doc_sha256": adj["patched_checker"]["frozen_F1_doc_sha256_reported"],
            "patched_tool_negative_control_V4": adj["patched_checker"]["V4_negative_verdict"],
            "sources_unchanged": adj["immutability"]["all_sources_unchanged"],
            "open_and_not_addressed": ["W16R28-F1 stale semantic corpus / run_acceptance exit 3", "W16R28-F3 location-dependent gate_test_report hash", "W16R28-F4 rev27 freeze discipline observation"],
        },
        "deliverables": {p: {"sha256": H[p], "bytes": os.path.getsize(p)} for p in H},
        "emitted_events": [e["event_id"] for e in events],
        "appended_this_run": appended,
        "outbox": "comms/outbox/worker-16.jsonl",
        "falsifier": "see adjudication.json and claim event w16-R03-ADJ-01-claim",
        "read_only": "No shared artifact was modified. All runs executed in artifacts/worker-16/r03_adjudication/stage/ and tools/.",
        "authority_note": "worker event cannot set validation_status=passed, node status=done, or a gate verdict; review/blocker evidence is for lead-audit and the controller.",
        "hours_this_pass": 0.5,
    }
    with open(CKPT, "w", encoding="utf-8") as fh:
        json.dump(ckpt, fh, indent=1, sort_keys=True)
    seen = set()
    if os.path.exists(CKPT_LOG):
        for line in open(CKPT_LOG, encoding="utf-8"):
            try:
                seen.add(json.loads(line).get("checkpoint_id"))
            except Exception:
                pass
    if ckpt["checkpoint_id"] not in seen:
        with open(CKPT_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"checkpoint_id": ckpt["checkpoint_id"], "at": ckpt["checkpoint_at"],
                                 "path": os.path.basename(CKPT), "verdict": ckpt["verdict"]["adjudication"][:120],
                                 "events": len(events)}) + "\n")
    with open(CKPT_MD, "a", encoding="utf-8") as fh:
        fh.write(f"\n## w16-ckpt-r03-adj-01 — {ckpt['checkpoint_at']}\n"
                 f"- task W16-R03-ADJ-01 (F1, AF-WCC-VAC-GEN, G-FORM), self-claimed, 0.5 h\n"
                 f"- adjudication: {ckpt['verdict']['adjudication']}\n"
                 f"- frozen F1 cce9c60146d6 unchanged; stage2 reject R03 only; V1 render accept; patched tool accept at unchanged doc_sha256; V4 still reject\n"
                 f"- checkpoint: `runtime/state/{os.path.basename(CKPT)}`; events: {len(events)} ({len(appended)} appended)\n"
                 f"- W16R28-F1/F3/F4 remain open and are not addressed here\n")

    print("appended:", appended)
    print("checkpoint:", CKPT)
    print("outbox lines:", sum(1 for _ in open(OUTBOX, encoding="utf-8")))


if __name__ == "__main__":
    main()
