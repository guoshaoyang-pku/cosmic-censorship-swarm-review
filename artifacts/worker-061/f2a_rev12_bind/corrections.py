#!/usr/bin/env python3
"""W061-F2A-REV12-BIND-04 erratum.

Corrects finding F-W061-F2AB-08 in REVIEW.json (the first emission stated that neither F1 nor
F2b names VOCAB_ALIASES.json; the measurement shows F1 carries
genericity.vocabulary_aliases_ref = artifacts/formulation/VOCAB_ALIASES.json at line 149).
Rewrites REVIEW.json / REVIEW.md / CHECKPOINT.json / SHA256SUMS and appends erratum events that
supersede the first artifact hashes.  The review verdict, score and hard failures are unchanged.

Writes only artifacts/worker-061/f2a_rev12_bind/**, runtime/state/w061_f2a_rev12_bind_checkpoint.json
and comms/outbox/worker-061.jsonl.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
TASK = REPO / "artifacts/worker-061/f2a_rev12_bind"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)
STAMP = NOW.strftime("%Y%m%dT%H%M%S")
TASK_ID = "W061-F2A-REV12-BIND-04"
OUTBOX = REPO / "comms/outbox/worker-061.jsonl"
PREV_STAMP = "20260912T004627"
PREV_REVIEW_EVENT = f"w061-f2ab-{PREV_STAMP}-review"
PREV_ARTIFACT_EVENT = f"w061-f2ab-{PREV_STAMP}-artifact-review"
REJECTED_CLAIM = f"w061-f2ab-{PREV_STAMP}-claim"


def sha256_path(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(REPO))


review_path = TASK / "REVIEW.json"
review = json.loads(review_path.read_text())

old_text = None
for f in review["findings"]:
    if f["id"] == "F-W061-F2AB-08":
        old_text = f["finding"]
        f["finding"] = (
            "The same binding axes recur across the family, with one correction to the first "
            "emission of this finding. Measured at the pinned triple: F1 and F2b both declare "
            "f0_binding.consistency_evidence_sha256=675a99d0d25b (stale; measured 9e335e9ba1bf); "
            "F1's conclusion token weak_cosmic_censorship is literally in the F0 allowed list, "
            "but its genericity.kind residual_comeager is not, and F1 binds the registry at the "
            "axis level (genericity.vocabulary_aliases_ref = artifacts/formulation/VOCAB_ALIASES.json, "
            "line 149), which F2a and F2b do not have anywhere in their text; F2b's conclusion token "
            "scc_c0_future_inextendibility and genericity.kind residual_comeager both need the same "
            "alias adjudication as F2a and F2b names VOCAB_ALIASES.json nowhere. This is recorded as "
            "a measured fact for the controller, not as a verdict on F1/F2b; a single F0 / alias-"
            "registry repair may be cheaper than three per-schema edits."
        )
        f["evidence_refs"] = [
            f"{rel(TASK / 'probe_f2a_rev12_output.json')}#cross_class_binding",
            f"schemas/af_wcc_vacuum.yaml#sha256:{sha256_path(REPO / 'schemas/af_wcc_vacuum.yaml')[:12]}",
            f"schemas/af_scc_c0_vacuum.yaml#sha256:{sha256_path(REPO / 'schemas/af_scc_c0_vacuum.yaml')[:12]}",
            "schemas/af_wcc_vacuum.yaml:149 (genericity.vocabulary_aliases_ref)",
        ]
        break
assert old_text is not None, "F-W061-F2AB-08 not found"

review["errata"] = [{
    "id": "ERR-W061-F2AB-01",
    "at": NOW.isoformat(timespec="seconds"),
    "corrects": PREV_REVIEW_EVENT,
    "supersedes_artifact_event": PREV_ARTIFACT_EVENT,
    "what_changed": ("finding F-W061-F2AB-08 only: the first emission said neither F1 nor F2b names "
                     "VOCAB_ALIASES.json; the measurement is F1 genericity.vocabulary_aliases_ref = "
                     "artifacts/formulation/VOCAB_ALIASES.json (line 149), F2a/F2b none. Verdict, score, "
                     "hard failures, probes and adjudications are unchanged."),
    "artifact_hash_change": ("REVIEW.json was rewritten in place, so its sha256 changes; the erratum "
                             "events carry the new hashes and supersede the first artifact events."),
    "previous_finding_text": old_text,
}]
review["revised_at"] = NOW.isoformat(timespec="seconds")
review_path.write_text(json.dumps(review, indent=1))

# regenerate REVIEW.md
lines = [
    f"# {TASK_ID} — F2a (AF-SCC-C2-VAC-GEN) rev12 binding review (revised)",
    "",
    f"- target: `schemas/af_scc_c2_vacuum.yaml` @ `{review['target']['reviewed_sha256']}`",
    f"- verdict: **{review['verdict']}** (score {review['score']})",
    f"- reviewer: worker-061; first emission {review['created_at']}, erratum {review['revised_at']}",
    "",
    "## Errata",
    "",
    f"- {review['errata'][0]['id']}: {review['errata'][0]['what_changed']}",
    "",
    "## Hard failures",
]
for hf in review["hard_failures"]:
    lines += [f"### {hf['id']} — {hf['axis']}", "", hf["finding"], "",
              "Falsifier: " + hf["falsifier"], ""]
lines += ["## Findings", ""]
for f in review["findings"]:
    lines += [f"### {f['id']} ({f['severity']})", "", f["finding"], ""]
lines += ["## Adjudications of open claims", ""]
for a in review["adjudications"]:
    lines += [f"- **{', '.join(a['claim_ids'])}** — {a['disposition']}"]
lines += ["", "## Probe matrix", "", "| probe | status | hard |", "|---|---|---|"]
for p in review["probes"]:
    lines.append(f"| {p['id']} | {p['status']} | {p['hard']} |")
lines += ["", "## Authority", "", review["authority_note"], ""]
(TASK / "REVIEW.md").write_text("\n".join(lines))

# regenerate checkpoint
artifacts = {}
for p in sorted(TASK.rglob("*")):
    if p.is_file() and p.name not in ("CHECKPOINT.json", "SHA256SUMS"):
        artifacts[rel(p)] = {"sha256": sha256_path(p), "bytes": p.stat().st_size}
artifacts[rel(review_path)] = {"sha256": sha256_path(review_path), "bytes": review_path.stat().st_size}
cp_path = TASK / "CHECKPOINT.json"
checkpoint = json.loads(cp_path.read_text())
checkpoint["artifacts"] = artifacts
checkpoint["revised_at"] = NOW.isoformat(timespec="seconds")
checkpoint["erratum"] = "ERR-W061-F2AB-01: REVIEW.json rewritten (F-08 correction); hashes updated."
cp_path.write_text(json.dumps(checkpoint, indent=1))
runtime_cp = REPO / "runtime/state/w061_f2a_rev12_bind_checkpoint.json"
shutil.copyfile(cp_path, runtime_cp)

# SHA256SUMS
sums = []
for p in sorted(TASK.rglob("*")):
    if p.is_file() and p.name != "SHA256SUMS":
        sums.append(f"{sha256_path(p)}  {rel(p)}")
(TASK / "SHA256SUMS").write_text("\n".join(sums) + "\n")

rev_sha = sha256_path(review_path)
cp_sha = sha256_path(cp_path)
probe_sha = sha256_path(TASK / "probe_f2a_rev12_output.json")

refs = review["evidence_refs"]
events = [
    {"event_id": f"w061-f2ab-{STAMP}-claim", "event_type": "claim",
     "created_at": NOW.isoformat(timespec="seconds"), "actor": "worker-061", "task_id": TASK_ID,
     "node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN", "gate": "G-FORM",
     "conclusion_type": "stability_result",
     "supersedes_event_id": REJECTED_CLAIM,
     "statement": (f"Corrected claim for the {REJECTED_CLAIM} event that the ingest rejected for an invalid "
                   f"conclusion_type: independent machine-checked review of F2a (AF-SCC-C2-VAC-GEN) at the "
                   f"pinned canonical rev12 bytes {review['target']['reviewed_sha256'][:12]} gives verdict "
                   f"{review['verdict']}, score {review['score']}, with four hard failures (F0 "
                   "conclusion-vocabulary binding unbound; F0 genericity-vocabulary binding unbound; declared "
                   "consistency-evidence hash one regeneration stale; four l1_ledger_refs claiming "
                   "verified_by_L1 against a ledger recording abstract-read / not_independently_reviewed). "
                   "The five rev11 defect classes are independently confirmed repaired and the canonical gate "
                   "passes under the rev28 manifest; the rev11-vintage R22 failure reproduces only under the "
                   "rev27 manifest, so that claim is falsified at current state."),
     "assumptions": ["the pinned bytes and the pinned F0/FROZEN/manifest/ledger artifacts are the revision under test; any byte change voids the verdict",
                     "alias-equivalence is not treated as satisfying the F0 allowed-list binding unless the artifact or the controller binds it",
                     "worker events cannot set node status, validation_status or a gate verdict"],
     "falsifier": review["next_falsifier"], "evidence_refs": refs,
     "artifact_refs": [f"{rel(review_path)}#sha256:{rev_sha[:12]}",
                       f"{rel(TASK / 'probe_f2a_rev12_output.json')}#sha256:{probe_sha[:12]}"]},
    {"event_id": f"w061-f2ab-{STAMP}-artifact-review-erratum", "event_type": "artifact",
     "created_at": NOW.isoformat(timespec="seconds"), "actor": "worker-061", "task_id": TASK_ID,
     "node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN", "gate": "G-FORM",
     "artifact_type": "independent_review_json", "path": rel(review_path), "sha256": rev_sha,
     "validation_status": "unverified",
     "supersedes_event_id": PREV_ARTIFACT_EVENT,
     "note": ("Erratum ERR-W061-F2AB-01: REVIEW.json rewritten to correct finding F-W061-F2AB-08 "
              "(F1 does bind the alias registry at genericity.vocabulary_aliases_ref; F2a/F2b do not). "
              "Verdict, score and hard failures unchanged; this artifact event supersedes the "
              f"{PREV_ARTIFACT_EVENT} hash binding.")},
    {"event_id": f"w061-f2ab-{STAMP}-artifact-checkpoint-erratum", "event_type": "artifact",
     "created_at": NOW.isoformat(timespec="seconds"), "actor": "worker-061", "task_id": TASK_ID,
     "node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN", "gate": "G-FORM",
     "artifact_type": "checkpoint_json", "path": rel(cp_path), "sha256": cp_sha,
     "validation_status": "unverified",
     "note": "Erratum checkpoint: hash ledger refreshed after the F-08 correction; copy at runtime/state/w061_f2a_rev12_bind_checkpoint.json."},
    {"event_id": f"w061-f2ab-{STAMP}-status-erratum", "event_type": "status",
     "created_at": NOW.isoformat(timespec="seconds"), "actor": "worker-061", "task_id": TASK_ID,
     "node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN", "gate": "G-FORM",
     "status": "active", "hours": 0.2,
     "summary": (f"Erratum ERR-W061-F2AB-01 for {PREV_REVIEW_EVENT}: finding F-W061-F2AB-08 corrected "
                 "(F1 carries genericity.vocabulary_aliases_ref = artifacts/formulation/VOCAB_ALIASES.json "
                 "at line 149; F2a/F2b name it nowhere). Verdict revise 3.0 and the four hard failures "
                 "HF-W061-F2AB-01..04 are unchanged. REVIEW.json rewritten, so its sha256 is now "
                 f"{rev_sha[:12]} and supersedes the {PREV_ARTIFACT_EVENT} binding; CHECKPOINT.json is "
                 f"{cp_sha[:12]}. The earlier claim event was rejected for an invalid conclusion_type and is "
                 f"replaced by w061-f2ab-{STAMP}-claim (stability_result). No node status, validation_status "
                 "or gate verdict is claimed."),
     "evidence_refs": [f"{rel(review_path)}#sha256:{rev_sha[:12]}",
                       f"{rel(cp_path)}#sha256:{cp_sha[:12]}",
                       f"comms/outbox/worker-061.jsonl#w061-f2ab-{STAMP}-claim"],
     "next_falsifier": review["next_falsifier"]},
    {"event_id": f"w061-f2ab-{STAMP}-final", "event_type": "status",
     "created_at": NOW.isoformat(timespec="seconds"), "actor": "worker-061", "task_id": TASK_ID,
     "node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN", "gate": "G-FORM",
     "status": "active", "hours": 0.2,
     "summary": ("Bounded class-bound task complete with erratum applied. Artifacts: probe matrix, "
                 "two-manifest gate replay, corrected REVIEW.json/.md, CHECKPOINT.json + runtime/state copy, "
                 "SHA256SUMS. Verdict revise 3.0 binds only to 5476a3f2c6bc."),
     "evidence_refs": [f"{rel(review_path)}#sha256:{rev_sha[:12]}",
                       f"{rel(cp_path)}#sha256:{cp_sha[:12]}",
                       f"comms/outbox/worker-061.jsonl#w061-f2ab-{STAMP}-status-erratum"],
     "next_falsifier": review["next_falsifier"]},
]
with OUTBOX.open("a") as fh:
    for e in events:
        fh.write(json.dumps(e) + "\n")
print(json.dumps({"review_sha256": rev_sha, "checkpoint_sha256": cp_sha,
                  "event_ids": [e["event_id"] for e in events]}, indent=1))
