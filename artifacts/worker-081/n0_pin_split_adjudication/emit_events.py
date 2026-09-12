#!/usr/bin/env python3
"""Emit the W081-N0-PINSPLIT-ADJ-01 checkpoint, review record and outbox events.

Idempotent: outbox event_ids already present are skipped; the checkpoint and the review
record are rewritten byte-identically from the report on disk.

Worker evidence only: this writes under artifacts/worker-081/, reviews/ (own review record)
and this worker's own outbox.  No canonical artifact is edited.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

FILE = Path(__file__).resolve()
ART = FILE.parent
REPO = FILE.parents[3]
TASK = "W081-N0-PINSPLIT-ADJ-01"
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).isoformat(timespec="seconds")
STAMP = datetime.now(TZ).strftime("%Y%m%dT%H%M%S")


def sha(rel: str) -> str:
    return hashlib.sha256((REPO / rel).read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(REPO))


report = json.loads((ART / "report.json").read_text())
verifier = rel(ART / "adjudicate_pin_split.py")
report_rel = rel(ART / "report.json")
readme_rel = rel(ART / "README.md")
proposal_rel = rel(ART / "proposed" / "n0_class_binding_addendum.json")
checkpoint_rel = rel(ART / "checkpoint.json")
review_rel = f"reviews/N0-pin-split-adjudication-worker-081.json"

hashes = {p: sha(p) for p in (verifier, report_rel, readme_rel, proposal_rel)}
n_checks = len(report["checks"])
n_ok = sum(1 for c in report["checks"] if c["ok"])
n_ctrl = len(report["controls"])
n_ctrl_ok = sum(1 for c in report["controls"] if c["ok"])
verdict = report["verdict"]

# ---------------------------------------------------------------- checkpoint
checkpoint = {
    "schema": "worker-checkpoint/v1",
    "task_id": TASK,
    "worker": "worker-081",
    "class_id": "AF-WCC-SCALAR-SPH",
    "node_id": "N0",
    "gate": "G-NUM",
    "created_at": NOW,
    "status": "complete",
    "pins": report["pins"],
    "artifact_sha256": hashes,
    "proposal": proposal_rel,
    "checks": {"pass": n_ok, "total": n_checks},
    "controls": {"pass": n_ctrl_ok, "total": n_ctrl},
    "verdict": verdict,
    "registry_gap_three_replication_verdicts": report[
        "registry_gap_three_replication_verdicts"],
    "next_falsifier": report["falsifier"],
    "non_claims": report["non_claims"],
}
(ART / "checkpoint.json").write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
hashes["checkpoint.json"] = sha(checkpoint_rel)

# ------------------------------------------------------------- review record
findings = [
    "PIN-SPLIT CONFIRMED: in the N0 evidence chain the protocol of record "
    f"{report['pins']['numerics/CONVERGENCE_PROTOCOL.md'][:12]} cites only the superseded F0 pins "
    "66bf917bd368 (line 7) and 66bf917b/565a6e50 (line 159); the current F0 rev5 hash "
    "0abb9ed8a961 appears only in the closure artifact, the generator and the reviews. "
    "numerics/protocol/fixed_replication_verdict.json still pins 66bf917b and declares "
    "binding_status=PROVISIONAL.",
    "MATERIALITY: the order claim is not taxonomy-dependent. The certification and the raw "
    "4-rung study contain no taxonomy string; rev3's taxonomy references are documentation "
    "pointers (/class_binding, /stop_rule_closures, exists:: checks); the generator's "
    "taxonomy-derived variables are used only in definitions, check() assertions and the "
    "serialized binding record.",
    "AUTHORITY: 0 records name one N0 class-binding carrier (5 near-misses name both hashes "
    "without asserting a carrier). REC-15 explicitly declines controller self-adjudication of "
    "the neighbouring protocol contest; no map field names a class-binding carrier for N0.",
    "REMEDY: a protocol rewrite moves the hash (1e6cdf04d7a2 -> d3cbbff72eed in the sandbox) "
    "and would void/re-open the 6 bound review records (3 accept, 3 revise; 4 distinct "
    "reviewers). The proposed byte-preserving addendum keeps the protocol hash unchanged "
    "(the protocol's own text already says the stale citation is not load-bearing for the "
    "order claim) and passes 6/6 checker checks; 3/3 mutants rejected.",
    "HONEST BOUND: the two N0 reviews disagree on the item-(2) label, not on the order "
    "numbers: 4 rungs x 3 schemes at fixed dt=1e-4 are independently reproduced. The defect "
    "is documentary consistency, which is still a stop-rule item because G-NUM requires an "
    "accept that leaves no item open.",
]
review = {
    "review_id": "N0-pin-split-adjudication-worker-081",
    "schema": "worker-adjudication/review/v1",
    "task_id": TASK,
    "actor": "worker-081",
    "reviewer": "worker-081",
    "created_at": NOW,
    "target_id": "N0",
    "target_path": "numerics/CONVERGENCE_PROTOCOL.md",
    "class_id": "AF-WCC-SCALAR-SPH",
    "class_ids": ["AF-WCC-SCALAR-SPH"],
    "node_id": "N0",
    "gate": "G-NUM",
    "verdict": verdict["review_verdict"],
    "score": verdict["score"],
    "disposition": verdict["disposition"],
    "materiality": verdict["materiality"],
    "remedy": verdict["remedy"],
    "verdict_basis": verdict["why"],
    "reviewed_sha256": report["pins"]["numerics/CONVERGENCE_PROTOCOL.md"],
    "reviewed_hashes": report["pins"],
    "hard_failures": [
        "HF-081-PS-1: N0 stop-rule item (2) has no single binding hash at the reviewed "
        "hashes: the protocol of record cites 66bf917bd368 (line 7) and 66bf917b/565a6e50 "
        "(line 159) and never 0abb9ed8a961; fixed_replication_verdict.json pins 66bf917b with "
        "binding_status PROVISIONAL; only the closure artifact and generator name rev5. "
        "Concurrence with HF-042-N0-1."
    ],
    "findings": findings,
    "evidence_refs": report["evidence_refs"],
    "falsifier": report["falsifier"],
    "independence": (
        "reviewer did not author the protocol, the closure artifact, the certification or "
        "either disputed N0 review; the verdict binds measured bytes, not prose; the census, "
        "materiality test, authority scan and remedy arithmetic are re-runnable from "
        f"{verifier}#sha256:{hashes[verifier][:12]}"),
    "non_claims": report["non_claims"],
    "authority": "proposal only; workers cannot pass G-NUM or set N0 status",
}
(repo_review := REPO / review_rel).write_text(json.dumps(review, indent=2, sort_keys=True) + "\n")

# ------------------------------------------------------------- outbox events
common = {
    "actor": "worker-081",
    "task_id": TASK,
    "class_id": "AF-WCC-SCALAR-SPH",
    "node_id": "N0",
    "gate": "G-NUM",
    "created_at": NOW,
}
events = [
    {**common, "event_id": f"w081-{STAMP}-pinsplit-task-claim", "event_type": "status",
     "status": "active",
     "summary": (
         "No assignment card exists for worker-081 in this batch; taking ONE bounded "
         "class-bound task: W081-N0-PINSPLIT-ADJ-01, independent adjudication of N0 "
         "stop-rule item (2) at the post-stoprule hashes. The two N0 reviews disagree on "
         "whether item (2) is closed (lead-audit) or open (worker-042 HF-042-N0-1); this "
         "task measures the pin split, its materiality, the existence of an authority "
         "carrier, the cost of the two remedies, and a checked proposal. Read-only on "
         "canonical paths; worker evidence only; no gate verdict, no node transition."),
     "evidence_refs": report["evidence_refs"][:4],
     "next_falsifier": report["falsifier"]},
    {**common, "event_id": f"w081-{STAMP}-pinsplit-artifact-verifier",
     "event_type": "artifact", "artifact_type": "verifier", "path": verifier,
     "sha256": hashes[verifier], "validation_status": "unverified",
     "evidence_refs": [f"{report_rel}#sha256:{hashes[report_rel][:12]}"],
     "note": "Deterministic stdlib-only; reads each input once, pins sha256, re-hashes the "
             "7 canonical inputs after the run; sandbox rewrite + 3 mutant controls."},
    {**common, "event_id": f"w081-{STAMP}-pinsplit-artifact-report",
     "event_type": "artifact", "artifact_type": "adjudication_report", "path": report_rel,
     "sha256": hashes[report_rel], "validation_status": "unverified",
     "evidence_refs": [f"{verifier}#sha256:{hashes[verifier][:12]}"],
     "note": f"{n_ok}/{n_checks} checks, {n_ctrl_ok}/{n_ctrl} controls; verdict "
             f"{verdict['disposition']} / {verdict['materiality']}; "
             f"{len(report['citation_census'])} census rows."},
    {**common, "event_id": f"w081-{STAMP}-pinsplit-artifact-proposal",
     "event_type": "artifact", "artifact_type": "proposal",
     "path": proposal_rel, "sha256": hashes[proposal_rel],
     "validation_status": "unverified",
     "evidence_refs": [f"{report_rel}#sha256:{hashes[report_rel][:12]}"],
     "note": "Proposal only, NOT applied: names F0 rev5 0abb9ed8a961 as the class binding of "
             "record and rev3 as the stop-rule-item-(2) carrier; supersedes the protocol's "
             "stale pin citation only, protocol bytes unchanged. 6/6 checker checks, 3/3 "
             "mutants rejected."},
    {**common, "event_id": f"w081-{STAMP}-pinsplit-artifact-review-note",
     "event_type": "artifact", "artifact_type": "review_note", "path": readme_rel,
     "sha256": hashes[readme_rel], "validation_status": "unverified",
     "evidence_refs": [f"{report_rel}#sha256:{hashes[report_rel][:12]}"],
     "note": "Human-readable adjudication note and remedy rationale."},
    {**common, "event_id": f"w081-{STAMP}-pinsplit-artifact-checkpoint",
     "event_type": "artifact", "artifact_type": "checkpoint", "path": checkpoint_rel,
     "sha256": hashes["checkpoint.json"], "validation_status": "unverified",
     "evidence_refs": [f"{report_rel}#sha256:{hashes[report_rel][:12]}"],
     "note": f"Checkpoint: {n_ok}/{n_checks} checks, {n_ctrl_ok}/{n_ctrl} controls, drift clean."},
    {**common, "event_id": f"w081-{STAMP}-pinsplit-claim", "event_type": "claim",
     "conclusion_type": "formal_model",
     "statement": (
         "At the pinned hashes (protocol 1e6cdf04d7a2, rev3 da7c36071995, certification "
         "1677822ceb9c, live F0 rev5 0abb9ed8a961, FROZEN 815e08079aef), N0 stop-rule item "
         "(2) cannot be called cleanly closed: the N0 evidence chain carries two distinct F0 "
         "pin families (current rev5 in rev3/generator/reviews; superseded 66bf917b and "
         "565a6e50 in the protocol of record lines 7/159 and in "
         "fixed_replication_verdict.json, which still declares PROVISIONAL), and no authority "
         "record names a single class-binding carrier (0 records; REC-15 declines "
         "self-adjudication). The split is documentary, not load-bearing: the certified "
         "4-rung x 3-scheme order evidence contains no taxonomy string and the generator's "
         "taxonomy read feeds only the binding assertion. Remedy: a byte-preserving addendum "
         "keeps the protocol hash and its 6 bound review records; a rewrite moves the hash "
         "1e6cdf04d7a2 -> d3cbbff72eed and voids/re-opens them. 11/11 checks, 7/7 controls."),
     "assumptions": [
         "The measured snapshot hash is the artifact identity; a path without a hash binds nothing.",
         "The live taxonomy bytes (0abb9ed8a961, revision 5) are the F0 rev5 of record.",
         "Hashes bound via review target/reviewed_sha256 define the verdicts a rewrite would void; "
         "mention-only citations do not.",
         "Worker evidence cannot close a stop-rule item; only controller/lead adjudication can.",
     ],
     "artifact_refs": [
         f"{report_rel}#sha256:{hashes[report_rel][:12]}",
         f"{verifier}#sha256:{hashes[verifier][:12]}",
         f"{proposal_rel}#sha256:{hashes[proposal_rel][:12]}",
         f"{readme_rel}#sha256:{hashes[readme_rel][:12]}",
         f"{checkpoint_rel}#sha256:{hashes['checkpoint.json'][:12]}",
     ],
     "evidence_refs": report["evidence_refs"],
     "falsifier": report["falsifier"]},
    {**common, "event_id": f"w081-{STAMP}-pinsplit-review", "event_type": "review",
     "target_id": "N0", "reviewer": "worker-081",
     "verdict": verdict["review_verdict"], "score": verdict["score"],
     "target_artifact": "numerics/CONVERGENCE_PROTOCOL.md",
     "reviewed_sha256": report["pins"]["numerics/CONVERGENCE_PROTOCOL.md"],
     "hard_failures": review["hard_failures"], "findings": findings,
     "evidence_refs": [f"{review_rel}#sha256:{sha(review_rel)[:12]}"] + report["evidence_refs"],
     "falsifier": report["falsifier"],
     "independence": review["independence"]},
    {**common, "event_id": f"w081-{STAMP}-pinsplit-complete", "event_type": "status",
     "status": "active",
     "summary": (
         f"{TASK} complete at worker level: one bounded class-bound task, artifacts on disk "
         f"and hash-pinned ({n_ok}/{n_checks} checks, {n_ctrl_ok}/{n_ctrl} controls, no drift). "
         "Findings: item (2) pin split CONFIRMED (concur HF-042-N0-1); binding is metadata, "
         "not order-dependent; no authority carrier exists; byte-preserving addendum proposed "
         "and checked (6/6, 3/3 mutants rejected), protocol rewrite priced at 6 bound review "
         "records. Worker completion claim only -- does NOT set node status, gate verdict or "
         "validation_status; numerics_lock untouched; N1 queued."),
     "evidence_refs": [f"{report_rel}#sha256:{hashes[report_rel][:12]}",
                       f"{checkpoint_rel}#sha256:{hashes['checkpoint.json'][:12]}",
                       f"{review_rel}#sha256:{sha(review_rel)[:12]}"],
     "next_falsifier": report["falsifier"]},
]

outbox = REPO / "comms/outbox/worker-081.jsonl"
existing = set()
if outbox.exists():
    for line in outbox.read_text().splitlines():
        try:
            existing.add(json.loads(line).get("event_id"))
        except json.JSONDecodeError:
            continue
with outbox.open("a") as fh:
    for e in events:
        if e["event_id"] in existing:
            continue
        fh.write(json.dumps(e, sort_keys=True) + "\n")
        existing.add(e["event_id"])

print(f"checkpoint : {checkpoint_rel} {hashes['checkpoint.json'][:12]}")
print(f"review     : {review_rel} {sha(review_rel)[:12]}")
print(f"outbox     : {len(events)} event(s) ensured in {rel(outbox)}")
