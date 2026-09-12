#!/usr/bin/env python3
"""Idempotent emitter for W064-GNUM-GUARD-CENSUS-01 events + worker checkpoint.

Appends only missing event_ids to comms/outbox/worker-064.jsonl, writes a copy to
events_emitted.jsonl, and writes runtime/state/w064_gnum_guard_checkpoint.json
(+ appends to w064_checkpoints.jsonl). Worker events cannot set status=done,
validation_status=passed, or a gate verdict. Run with --check to only report.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms" / "outbox" / "worker-064.jsonl"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S+08:00")

PIN_GATES = "numerics/gates.py#fcd1d70991b6eade4aa993dc49b6103e338f68320aabb955d97da5a8f55d996e"
PIN_PROTO = "numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274"
ADJ = "reviews/G-NUM-protocol-r4-adjudication.json#b836902fa4ae0e57af52d408c09ad03b4a2023b038d8d0cb186c45f8f69ad354"
Q = "artifacts/worker-064/gnum_guard"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha12(p: Path) -> str:
    return sha(p)[:12]


def ev(eid, etype, **kw):
    d = {"event_id": eid, "event_type": etype, "created_at": NOW,
         "actor": "worker-064", "class_id": "AF-WCC-SCALAR-SPH",
         "class_ids": ["AF-WCC-SCALAR-SPH"],
         "node_id": "N0", "gate": "G-NUM"}
    d.update(kw)
    return d


def build() -> list[dict]:
    art = lambda name, rel: {
        "artifact_type": name, "path": rel, "sha256": sha(ROOT / rel),
        "validation_status": "unverified",
    }
    files = {
        "report": f"{Q}/report.json",
        "census": f"{Q}/census.jsonl",
        "candidate_rules": f"{Q}/candidate_rules.json",
        "prereg": f"{Q}/prereg.json",
        "harness": f"{Q}/w064_gnum_guard_census.py",
        "readme": f"{Q}/README.md",
        "snapshot": f"{Q}/raw/events_snapshot.jsonl",
    }
    ref = {k: f"{v}#{sha12(ROOT / v)}" for k, v in files.items()}
    allrefs = list(ref.values()) + [PIN_GATES, PIN_PROTO, ADJ]

    events = []
    for k, rel in files.items():
        events.append(ev(f"w064-gnum-guard-01-art-{k}", "artifact", **{
            **art(f"gnum_guard_{k}", rel)}))
        events[-1]["evidence_refs"] = [f"{rel}#{sha12(ROOT / rel)}"]
        events[-1]["falsifier"] = ("Re-hash the path: a different sha256, or a report that "
                                   "does not reproduce with "
                                   "python3 artifacts/worker-064/gnum_guard/w064_gnum_guard_census.py, "
                                   "falsifies this artifact binding.")

    c1 = ev("w064-gnum-guard-01-claim-c1-census-r2", "claim", **{
        "conclusion_type": "numerical_evidence",
        "task_id": "W064-GNUM-GUARD-CENSUS-01",
        "statement": (
            f"At {PIN_GATES} and {PIN_PROTO}, with a frozen 11,587-event snapshot "
            "(artifacts/worker-064/gnum_guard/raw/events_snapshot.jsonl#"
            f"{sha12(ROOT / files['snapshot'])}), numerics/gates.py::_protocol_review returns "
            "reviewed=true, contest=true with exactly 5 accepting reviews "
            "(w081-…c8-review, audit-review-gnum-protocol-final-…, w081-…adj2-review, "
            "w012-c3-review-0001-adjudication, f13-n0rev3-…-review), 5 dissenting reviews "
            "(w067-review-gnum-protocol-r3-…, w081-…f1-review, w067-provledger-…, "
            "w042-n0-stoprule-01-review, w081-…pinsplit-review) and 3 advisory rows "
            "(including the audit group's operative r4 adjudication accept). The lead-numerics "
            "description 'two accepts vs four revises' at 01:00:54 was already stale: events "
            "landing at 00:50:36 (w012 accept) and 00:58:18 (w081 pin-split revise) moved the "
            "census to 5/5. This is an instrument census, not a protocol or physics verdict."),
        "assumptions": ["the pinned gates.py copy is byte-identical to the live canonical file "
                        "(checked at run start and end)",
                        "the frozen snapshot is the exact event list the pinned "
                        "load_event_stream returns"],
        "falsifier": ("Re-run the harness: a different accept/dissent set at the same two pins, "
                      "or a live numerics/gates.py hash other than fcd1d70991b6, falsifies this "
                      "claim (exit 2/3 in the harness)."),
        "evidence_refs": [ref["report"], ref["census"], ref["snapshot"], PIN_GATES, PIN_PROTO],
        "artifact_refs": [ref["report"], ref["census"]],
        "not_claimed": ["no gate verdict", "no protocol merits verdict",
                        "no N0 node completion"],
    })
    c2 = ev("w064-gnum-guard-01-claim-c2-advisory-r2", "claim", **{
        "conclusion_type": "numerical_evidence",
        "task_id": "W064-GNUM-GUARD-CENSUS-01",
        "statement": (
            "The audit group's operative r4 accept (event audit-l06-review-gnum-r4-20260912T005926, "
            f"artifact {ADJ}) is counted advisory, not accepting, because the emitted event carries "
            "neither reviewed_sha256 nor a numerics/CONVERGENCE_PROTOCOL.md#<hash> evidence ref, "
            "while the artifact it cites does carry reviewed_sha256=1e6cdf04d7a2. In-memory repair "
            "of that one emit field (arm_hash_repair_only) binds the accept (accepts 5→6) and leaves "
            "contest=true with all 5 dissents standing: fixing the binding alone does not clear the "
            "guard. This replicates and mechanises the r4 artifact's own mechanical_caveat."),
        "assumptions": ["review binding is read only from the event, per _review_cited_hashes"],
        "falsifier": ("Emit the r4 review event with reviewed_sha256=1e6cdf04d7a2 or a protocol-pinned "
                      "ref and re-run the guard: if the event is still advisory, or if contest clears "
                      "without any dissent-side change, this claim is falsified."),
        "evidence_refs": [ref["report"], ref["candidate_rules"], ADJ, PIN_PROTO],
        "artifact_refs": [ref["report"], ref["candidate_rules"]],
    })
    c3 = ev("w064-gnum-guard-01-claim-c3-scope-r2", "claim", **{
        "conclusion_type": "numerical_evidence",
        "task_id": "W064-GNUM-GUARD-CENSUS-01",
        "statement": (
            "PROTOCOL_REVIEW_TARGETS = (numerics/CONVERGENCE_PROTOCOL.md, G-NUM-protocol, N0) makes "
            "protocol review state inseparable from N0 node verdict state: 3 of the 5 counted dissents "
            "(w067-provledger-…, w042-n0-stoprule-01-review, w081-…pinsplit-review) and 1 of the 5 "
            "counted accepts (f13-n0rev3-…-review) target N0, not the protocol of record. Restricting "
            "protocol review state to the protocol targets (candidate R1) leaves 4 accepts / 2 dissents "
            "— both dissents being the F1/F1′ evidence-basis objections that the r4 adjudication "
            "declares discharged. The r4 card itself claims no N0 node-status verdict."),
        "assumptions": ["N0 node verdict state is adjudicated elsewhere and is not protocol review state"],
        "falsifier": ("Show an N0-targeted review whose subject is the protocol text rather than the N0 "
                      "node, or a protocol-targeted review excluded by R1; either falsifies the conflation "
                      "finding's materiality (the census itself stands regardless)."),
        "evidence_refs": [ref["report"], ref["census"], PIN_GATES],
        "artifact_refs": [ref["report"], ref["census"]],
    })
    c4 = ev("w064-gnum-guard-01-claim-c4-withdrawal-r2", "claim", **{
        "conclusion_type": "numerical_evidence",
        "task_id": "W064-GNUM-GUARD-CENSUS-01",
        "statement": (
            "The counted accept w081-20260912T002140-c8-review is declared withdrawn by its own author "
            "in the prose of status event w081-2026-09-12T00:29:19+0800-complete ('prior W081-N0-C8-01 "
            "accept withdrawn'), yet _protocol_review reads only event_type=='review', so the retracted "
            "verdict still counts. No machine-readable withdraws/withdraws_event_ids/withdrawn_event_ids "
            "field exists anywhere in the stream, so a withdrawal-aware rule (R2) is inert today; the "
            "positive control E8P shows it binds (scoped accepts 4→3) once such a field is emitted."),
        "assumptions": ["only the author's own withdrawal should remove a verdict"],
        "falsifier": ("Find a structured withdrawal event for w081-20260912T002140-c8-review, or show the "
                      "prose withdrawal is not by the accept's author; either falsifies the finding."),
        "evidence_refs": [ref["report"], ref["census"], ref["candidate_rules"]],
        "artifact_refs": [ref["report"]],
    })
    c5 = ev("w064-gnum-guard-01-claim-c5-rule-r2", "claim", **{
        "conclusion_type": "numerical_evidence",
        "task_id": "W064-GNUM-GUARD-CENSUS-01",
        "statement": (
            "Candidate rule R1 (scope) + R2 (author withdrawal) + R3 (explicit fail-closed discharge "
            "list on a later binding same-hash review) clears the guard on the frozen snapshot: "
            "accepts=5, dissents=0, discharged=2, contest=false, reviewed=true, with all six negative "
            "controls holding (unknown id, stale-hash carrier, pre-dated carrier, uncited carrier, "
            "third-party withdrawal, fresh unlisted dissent). A shadow implementation reproduces the "
            "pinned guard exactly with all hooks off. NOT ADOPTED: this is a proposal for the controller "
            "(owner per audit-l06-b4); the live canonical numerics/gates.py is unchanged."),
        "assumptions": ["a discharge carrier must itself bind the protocol hash and postdate the dissent"],
        "falsifier": ("Any negative control clearing contest, or any discharged dissent that lacks an "
                      "explicit carrier naming it, falsifies the rule's safety; applying it to the "
                      "canonical tool without the owner's disposition is out of scope."),
        "evidence_refs": [ref["candidate_rules"], ref["report"]],
        "artifact_refs": [ref["candidate_rules"]],
        "not_claimed": ["not adopted", "not a gate verdict"],
    })
    review = ev("w064-gnum-guard-01-review-guard", "review", **{
        "target_id": "numerics/gates.py#fcd1d70991b6",
        "reviewer": "worker-064",
        "verdict": "revise",
        "score": 3.0,
        "task_id": "W064-GNUM-GUARD-CENSUS-01",
        "reviewer_independence": "worker-064 authored no numerics/ file, no protocol text, no gates.py "
                                 "revision, and none of the counted review verdicts; this review targets "
                                 "the instrument, not the protocol, and cannot be miscounted by "
                                 "_protocol_review (numerics/gates.py is not in PROTOCOL_REVIEW_TARGETS).",
        "hard_failures": [
            "HF-1: the operative r4 adjudication accept does not bind the guard (no protocol hash in the emitted event); the artifact it cites does carry the hash",
            "HF-2: three N0 node reviews and one N0 node accept are counted as protocol review state because PROTOCOL_REVIEW_TARGETS contains 'N0'",
            "HF-3: a withdrawn accept is still counted and no machine-readable withdrawal field exists anywhere in the stream",
        ],
        "findings": [
            "F1: census at the pins is 5 accepts / 5 dissents / 3 advisory; the lead-numerics '2 accepts vs 4 revises' was stale by 00:58:18",
            "F2: worker-081 is counted on both sides at the same hash",
            "F3: R1 alone leaves the two discharged evidence-basis dissents as the only protocol dissents",
            "F4: R1+R2+R3 clears contest on the frozen snapshot with six negative controls holding; R2 is inert on live data (prose-only withdrawal)",
            "F5: clearing contest is necessary but not sufficient for G-NUM: the gate still awaits an accepting N0 node verdict, on disk a 3.5 revise",
        ],
        "falsifier": ("Re-run the pinned harness and the negative controls: any control clearing contest, "
                      "or any census row missing from the frozen snapshot, falsifies the corresponding finding."),
        "evidence_refs": allrefs,
    })
    blocker = ev("w064-gnum-guard-01-blocker", "blocker", **{
        "task_id": "W064-GNUM-GUARD-CENSUS-01",
        "description": (
            "audit-l06-b4 mechanised: at numerics/gates.py#fcd1d70991b6 the guard reports contest=true "
            "at protocol 1e6cdf04d7a2 for three mechanical reasons, not for the protocol text: (1) the "
            "r4 adjudication's accept is advisory because its event omits the protocol hash; (2) N0 node "
            "reviews are conflated with protocol reviews; (3) a prose-only withdrawn accept still counts. "
            "A fourth, non-mechanical fact: clearing contest cannot turn G-NUM green while the N0 node "
            "verdict on disk is a 3.5 revise."),
        "needed_to_unblock": [
            "owner (controller) disposition per audit-l06-b4, or adoption of a scoped/withdrawal/discharge rule (R1–R3) at a cited revision with an independent review",
            "emit the r4 adjudication review event with reviewed_sha256=1e6cdf04d7a2 or a protocol-pinned evidence ref (one-field repair)",
            "emit a structured withdrawal for w081-20260912T002140-c8-review (prose alone is not machine-readable)",
            "resolve the standing N0 node verdict (reviews/N0-pin-split-adjudication-worker-081.json#a39c7178c008, revise 3.5) — outside this task's scope",
        ],
        "falsifier": ("Apply the owner disposition or the candidate rule and re-run numerics/gates.py: "
                      "contest must clear by rule, not by deleting a verdict; a cleared contest while a "
                      "genuinely undischarged dissent exists falsifies the repair."),
        "evidence_refs": allrefs,
    })
    status = ev("w064-gnum-guard-01-status", "status", **{
        "status": "active",
        "task_id": "W064-GNUM-GUARD-CENSUS-01",
        "hours": 0.5,
        "summary": (
            "W064-GNUM-GUARD-CENSUS-01 complete at worker level (no inbox card existed for worker-064; "
            "one class-bound task self-selected from open blocker audit-l06-b4). Read-only census of "
            "numerics/gates.py::_protocol_review at pin fcd1d70991b6 / protocol 1e6cdf04d7a2 on a frozen "
            "11,587-event snapshot: 5 accepts / 5 dissents / 3 advisory, contest=true; the r4 operative "
            "accept is advisory, 3/5 dissents are N0 node reviews, one counted accept is prose-withdrawn "
            "and no structured withdrawal field exists. Candidate R1–R3 clears contest on the snapshot "
            "with six negative controls holding; not adopted. No canonical file modified; numerics_lock "
            "LOCKED; no gate verdict."),
        "evidence_refs": allrefs,
        "next_falsifier": ("After the owner emits the one-field r4 repair, a structured withdrawal, and/or "
                           "adopts R1–R3 at a cited revision, re-run "
                           "artifacts/worker-064/gnum_guard/w064_gnum_guard_census.py against the new "
                           "revision; expect a rule-driven contest=false with the six controls still "
                           "holding and no undischarged dissent dropped."),
        "not_claimed": ["no gate verdict", "no node completion", "no canonical modification",
                        "no adoption of R1–R3", "no physics claim",
                        "five claims re-emitted after the first emission was schema-rejected (see supersedes_event_id)",
                        "no solver/N1 work; numerics_lock stays LOCKED"],
    })
    for c, base in ((c1, "c1-census"), (c2, "c2-advisory"), (c3, "c3-scope"),
                    (c4, "c4-withdrawal"), (c5, "c5-rule")):
        c["supersedes_event_id"] = f"w064-gnum-guard-01-claim-{base}"
        c["erratum"] = ("first emission used an invalid conclusion_type and was rejected by "
                        "comms.py ingest (reason: claim: invalid conclusion_type); re-emitted "
                        "with conclusion_type=numerical_evidence and a new event_id")
    return events + [c1, c2, c3, c4, c5, review, blocker, status]


def main() -> int:
    check_only = "--check" in sys.argv
    events = build()
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                continue
    new = [e for e in events if e["event_id"] not in existing]
    if check_only:
        print(json.dumps({"would_emit": [e["event_id"] for e in new],
                          "already_present": len(events) - len(new)}, indent=1))
        return 0
    if new:
        with open(OUTBOX, "a") as f:
            for e in new:
                f.write(json.dumps(e, sort_keys=True) + "\n")
    (HERE / "events_emitted.jsonl").write_text(
        "".join(json.dumps(e, sort_keys=True) + "\n" for e in events))

    # checkpoint
    ck = {
        "checkpoint_id": f"w064-gnum-guard-ckpt-{NOW.replace(':', '').replace('+0800', 'p0800')}",
        "task_id": "W064-GNUM-GUARD-CENSUS-01",
        "actor": "worker-064",
        "created_at": NOW,
        "node_id": "N0",
        "gate": "G-NUM",
        "class_ids": ["AF-WCC-SCALAR-SPH"],
        "status": "worker_task_complete_no_node_transition",
        "verdict": "GUARD_CONTEST_MECHANISED__R4_ACCEPT_ADVISORY__N0_CONFLATION__PROSE_ONLY_WITHDRAWAL__R1R2R3_SAFE_ON_SIX_CONTROLS",
        "pins": {"numerics/gates.py": "fcd1d70991b6eade4aa993dc49b6103e338f68320aabb955d97da5a8f55d996e",
                 "numerics/CONVERGENCE_PROTOCOL.md": "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274"},
        "guard_verdict": {"reviewed": True, "contest": True, "accepts": 5, "dissents": 5, "advisory": 3},
        "arm_summary": {"current": "5/5 contest=true", "hash_repair_only": "6/5 contest=true",
                        "scope_R1": "4/2 contest=true", "R1+R2+R3": "5/0 contest=false"},
        "negative_controls": 6,
        "evidence_refs": [f"artifacts/worker-064/gnum_guard/{n}#{sha12(ROOT / f'artifacts/worker-064/gnum_guard/{n}')}"
                          for n in ("report.json", "census.jsonl", "candidate_rules.json",
                                    "prereg.json", "w064_gnum_guard_census.py", "README.md")],
        "falsifier": ("Re-run w064_gnum_guard_census.py at the pins: exit 2 (pin moved), or any negative "
                      "control clearing contest, or a census row missing from the frozen snapshot "
                      "falsifies the corresponding result."),
        "next_falsifier": ("After the owner emits the one-field r4 repair / structured withdrawal / adopts "
                           "R1–R3, re-run the harness; expect a rule-driven contest=false with controls holding."),
        "not_claimed": ["no gate verdict", "no node completion", "no canonical modification",
                        "no adoption of R1–R3", "no physics claim"],
        "outbox": "comms/outbox/worker-064.jsonl",
        "outbox_event_ids": [e["event_id"] for e in events],
    }
    (ROOT / "runtime/state/w064_gnum_guard_checkpoint.json").write_text(
        json.dumps(ck, indent=1, sort_keys=True))
    with open(ROOT / "runtime/state/w064_checkpoints.jsonl", "a") as f:
        f.write(json.dumps(ck, sort_keys=True) + "\n")
    print(json.dumps({"emitted": len(new), "total_task_events": len(events),
                      "outbox": str(OUTBOX.relative_to(ROOT)),
                      "checkpoint": "runtime/state/w064_gnum_guard_checkpoint.json"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
