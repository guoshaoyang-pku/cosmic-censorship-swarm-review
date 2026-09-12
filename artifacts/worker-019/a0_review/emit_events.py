#!/usr/bin/env python3
"""Emit W019-A0-REVIEW-01 upward events, schema-validated before append.

Appends to comms/outbox/deepseek-flash-19.jsonl (the card's assignee channel).
Every event is validated by research_map/schemas.py validate_event first; a
rejected event aborts the whole emission so a partial write cannot happen.
"""
import hashlib
import importlib.util
import json
import os
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).isoformat(timespec="seconds")
OUT = os.path.join(ROOT, "comms/outbox/deepseek-flash-19.jsonl")

spec = importlib.util.spec_from_file_location(
    "rm_schemas", os.path.join(ROOT, "research_map/schemas.py"))
rm = importlib.util.module_from_spec(spec)
import sys
sys.modules["rm_schemas"] = rm  # dataclass() resolves cls.__module__ via sys.modules
spec.loader.exec_module(rm)


def sha(rel):
    h = hashlib.sha256()
    with open(os.path.join(ROOT, rel), "rb") as fh:
        for c in iter(lambda: fh.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()


REVIEW = "reviews/A0-review-19-current.json"
RESULTS = "artifacts/worker-019/a0_review/results.json"
PROBE = "artifacts/worker-019/a0_review/check_a0_independent.py"
RUBRIC = "evaluation_rubric.yaml"
RUBRIC_SHA = "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885"
CLS = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH"
TASK = "audit-a1-20260912T0008-a0-w19"
REV_SHA = sha(REVIEW)
RES_SHA = sha(RESULTS)
PROBE_SHA = sha(PROBE)
TS = NOW.replace(":", "").replace("-", "").replace("+0800", "")

base = {
    "created_at": NOW,
    "actor": "deepseek-flash-19",
    "group_id": "audit",
    "node_id": "A0",
    "task_id": TASK,
    "class_id": CLS,
    "card_class_id": "GLOBAL",
}
ev = []

ev.append(dict(base, **{
    "event_id": f"flash19-A0-01-artifact-probe-{TS}",
    "event_type": "artifact",
    "artifact_type": "review_probe_report",
    "path": RESULTS,
    "sha256": RES_SHA,
    "validation_status": "unverified",
    "content_digest_sha256": "0ad5fd44a3938b9e55dbbb1a8562abe925530205a5f78a94dc773ceb2c7cef04",
    "summary": "Independent A0 probe at evaluation_rubric.yaml sha256 d748a9e3574e: 11 checks, 6 pass / 5 fail. Fails: acceptance item 4 named-evidence binding (C3); metrics target uniformity (C5b); unfilled validation self-test (C6); HF evidence locators (C9); HF-14 detector zero recall on the live ledger schema (C10).",
    "evidence_refs": [f"{RESULTS}#sha256:{RES_SHA[:12]}", f"{PROBE}#sha256:{PROBE_SHA[:12]}", f"{RUBRIC}#sha256:{RUBRIC_SHA[:12]}"],
    "falsifier": "Re-running check_a0_independent.py on the same pinned bytes and getting a different pass/fail vector, or a different content_digest_sha256, falsifies this report.",
}))

ev.append(dict(base, **{
    "event_id": f"flash19-A0-01-artifact-review-{TS}",
    "event_type": "artifact",
    "artifact_type": "review",
    "path": REVIEW,
    "sha256": REV_SHA,
    "validation_status": "unverified",
    "summary": "Independent A1 re-review of A0 at the current on-disk hash (card audit-a1-20260912T0008-a0-w19). Verdict revise, score 3.0, three hard failures; the card falsifier (universal scalar score / fluency-only verifier) did NOT fire. Not a copy of reviews/F0-review-19.json or any other A0 review; no other A0 verdict was read.",
    "evidence_refs": [f"{REVIEW}#sha256:{REV_SHA[:12]}", f"{RESULTS}#sha256:{RES_SHA[:12]}", f"{RUBRIC}#sha256:{RUBRIC_SHA[:12]}"],
    "falsifier": "A verdict that does not cite the measured rubric hash, or that reuses another reviewer's text, falsifies this artifact.",
}))

ev.append(dict(base, **{
    "event_id": f"flash19-A0-01-review-{TS}",
    "event_type": "review",
    "target_id": "A0",
    "reviewer": "deepseek-flash-19",
    "artifact": RUBRIC,
    "artifact_sha256": RUBRIC_SHA,
    "artifact_refs": [f"{REVIEW}#sha256:{REV_SHA[:12]}", f"{RESULTS}#sha256:{RES_SHA[:12]}"],
    "verdict": "revise",
    "score": 3.0,
    "hard_failures": [
        "HF-05-adjacent (critical): validation block (lines 45-50) declares artifacts/audit/audit_run.py but leaves last_run/last_run_result/report_sha256 null while line 46 says 'a rubric with no passing self-test is not a gate'; the reviewed bytes record no self-test.",
        "HF-06-adjacent (critical): acceptance item 'every acceptance test machine-checkable or reviewer-adjudicated with named evidence' fails; only schema_formulation (line 23) has an evidence field, literature/numerics/formalization human_adjudication_only items (lines 31/37/43) have none, and 0 of 28 checks[] entries name a detector.",
        "HF-14-adjacent (major): HF-14 (lines 243-252) names fields status=accepted / supports_claim=true that occur 0 times in ledger/theorems.jsonl a1674f094979 (62 records); T-201..T-203 use author_asserts_supports + review_status + acceptance_authority, so a literal detector has zero recall while the self-certification pattern persists.",
    ],
    "findings": [
        "A0-19-01 moderate: HF-13/HF-14 evidence anchors are path-only (no #sha256) and 'astra-lead-literature.log line 10' does not resolve at root (file is runtime/logs/astra-lead-literature.log).",
        "A0-19-02 soft: metrics.novel_accepted_coverage (lines 282-283) is the only one of 7 metrics without a target.",
        "A0-19-03 soft: metrics.effective_sample_size embeds the 'ESS ~2.2' quantitative prior with no locator or quantity_check, against the rubric's own G-LIT/HF-04 standard.",
        "A0-19-04 moderate: the 14-code HF taxonomy has no code for gate-instrument defects (unfilled self-test, unbound acceptance test, stale detector vocabulary); two hard failures needed 'nearest code' labels.",
        "A0-19-05 soft: G-AUDIT kappa criterion (line 151) names no report artifact, sampling frame or third-reviewer trigger.",
    ],
    "positive_checks": [
        "Four per-task-type verifiers present and complete (lines 16-43).",
        "14 unique hard failures, each with name/severity/detector; 7 critical / 6 major / 1 minor (lines 170-252).",
        "No universal scalar score; 7 per-task metrics with targets, no averaging rule (lines 10-13, 255-283).",
        "frozen_classes equals the four taxonomy class_ids (taxonomy 0abb9ed8a961); C0=>C2 implication consistent (lines 52-118).",
        "Contamination scan clean under mention-not-use (HF-13 tokens only inside its own negative definition, lines 233-242).",
    ],
    "acceptance_map": {
        "four_per_task_type_verifiers": "pass",
        "hard_failure_list": "pass",
        "no_universal_scalar_score": "pass",
        "every_acceptance_test_machine_checkable_or_reviewer_adjudicated_with_named_evidence": "fail",
        "class_binding_to_frozen_four": "pass",
    },
    "independence": {
        "artifact_author": "lead-audit",
        "reviewer_is_author": False,
        "prior_exposure": "No other A0 review was read; inputs were the artifact, the card, reviews/INDEX.md registry table, the live ledger and the taxonomy.",
        "kish_ess_note": "Report ESS <= n for the A0 verdict set; this verdict derives from the re-runnable probe at results.json content_digest_sha256 0ad5fd44a3938b9e55dbbb1a8562abe925530205a5f78a94dc773ceb2c7cef04.",
    },
    "falsifier": "An accepted A0 that contains a universal scalar score, or a task type whose only verifier is fluency review.",
    "falsifier_status": "not_triggered",
    "next_falsifier": "Re-review the next evaluation_rubric.yaml sha256: revise is falsified if (a) all three non-schema verifiers name reviewer evidence objects and every checks[] entry names a detector/adjudicator+evidence pair, (b) validation.last_run/last_run_result/report_sha256 are filled and hash-matched, (c) HF detector field vocabulary matches the live schema or is version-scoped, (d) all HF anchors resolve with #sha256, (e) novel_accepted_coverage carries a target.",
    "evidence_refs": [f"{REVIEW}#sha256:{REV_SHA[:12]}", f"{RESULTS}#sha256:{RES_SHA[:12]}", f"{PROBE}#sha256:{PROBE_SHA[:12]}", f"{RUBRIC}#sha256:{RUBRIC_SHA[:12]}", "research_map/formulation_taxonomy.yaml#sha256:0abb9ed8a961", "ledger/theorems.jsonl#sha256:a1674f094979", "artifacts/audit/audit_run.py#sha256:3b27dd3fef7f", "reviews/INDEX.md#sha256:73b7b92a9b"],
    "no_completion_claim": "review sets no gate verdict, no node status, no validation_status",
}))

ev.append(dict(base, **{
    "event_id": f"flash19-A0-01-claim-{TS}",
    "event_type": "claim",
    "statement": "At evaluation_rubric.yaml sha256 d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885: the four A0 acceptance items resolve to pass/pass/pass/fail. Three of four per-task-type verifiers (literature line 25, numerics line 32, formalization line 38) carry human_adjudication_only items with no named evidence object and 0 of 28 checks[] entries name a detector; validation.last_run/last_run_result/report_sha256 (lines 48-50) are null although line 46 makes a passing self-test a precondition of gate status; and HF-14's literal fields status=accepted / supports_claim=true occur 0 times in the live 62-record ledger a1674f094979, where T-201..T-203 still carry author_asserts_supports=true with review_status=not_independently_reviewed. The card falsifier did not fire: no universal scalar score exists and no task type is fluency-only. This is a measurement about the audit instrument at a pinned hash, not a mathematical claim.",
    "conclusion_type": "numerical_evidence",
    "assumptions": ["the instrument reviewed is the on-disk evaluation_rubric.yaml at the measured hash", "the live ledger and taxonomy are those at the hashes pinned here", "the probe is read-only and deterministic"],
    "falsifier": "Re-running the probe on the same pinned bytes with a different pass/fail vector, or filling the validation block / naming the evidence objects at the same hash without changing it (impossible without a new hash), falsifies this measurement.",
    "evidence_refs": [f"{RESULTS}#sha256:{RES_SHA[:12]}", f"{REVIEW}#sha256:{REV_SHA[:12]}", f"{RUBRIC}#sha256:{RUBRIC_SHA[:12]}", "ledger/theorems.jsonl#sha256:a1674f094979"],
    "artifact_refs": [f"{RESULTS}#sha256:{RES_SHA[:12]}", f"{REVIEW}#sha256:{REV_SHA[:12]}"],
}))

ev.append(dict(base, **{
    "event_id": f"flash19-A0-01-status-{TS}",
    "event_type": "status",
    "status": "active",
    "hours": 0.6,
    "summary": "One class-bound task taken and completed pending review: independent A1 re-review of A0 at the current on-disk hash d748a9e3574e (card audit-a1-20260912T0008-a0-w19, gate G-AUDIT), the card re-issued after my 23:19 verdict was bound to a superseded hash. Verdict revise, score 3.0, hard_failures 3, findings 5, card falsifier not triggered. Wrote only reviews/A0-review-19-current.json and my own evidence under artifacts/worker-019/a0_review/. No gate verdict, no node status, no validation_status; numerics_lock untouched; no canonical/shared/ledger file modified.",
    "evidence_refs": [f"{REVIEW}#sha256:{REV_SHA[:12]}", f"{RESULTS}#sha256:{RES_SHA[:12]}", f"{PROBE}#sha256:{PROBE_SHA[:12]}", f"{RUBRIC}#sha256:{RUBRIC_SHA[:12]}"],
    "falsifier": "Re-running the probe on the same pinned bytes with a different result, or a finding that the review reuses another reviewer's text.",
    "falsifier_status": "not_triggered",
    "next_falsifier": "Re-review at the next evaluation_rubric.yaml sha256 against the five conditions in next_falsifier of the review event.",
    "no_completion_claim": "worker cannot set node done, validation_status passed, or a gate verdict",
}))

for e in ev:
    rm.validate_event(e)

with open(OUT, "a", encoding="utf-8") as fh:
    for e in ev:
        fh.write(json.dumps(e, sort_keys=True) + "\n")

print("appended", len(ev), "events to", os.path.relpath(OUT, ROOT))
for e in ev:
    print(" ", e["event_type"], e["event_id"])
print("review sha256", REV_SHA)
print("results sha256", RES_SHA)
print("probe sha256", PROBE_SHA)
