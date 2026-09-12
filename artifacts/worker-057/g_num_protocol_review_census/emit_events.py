#!/usr/bin/env python3
"""Emit the W057-GNUM-PROTOCOL-REVIEW-CENSUS-01 events to comms/outbox/worker-057.jsonl
and write the worker checkpoint.

Idempotent: an event_id already present in the outbox is skipped; the checkpoint line is
appended only if its checkpoint id is not already present.  Every artifact sha256 is
re-measured on disk before the event is written; a mismatch aborts.  Events are validated
against research_map/schemas.py before being appended.

Safety guard: this instrument's review event must NOT target the protocol family
(numerics/CONVERGENCE_PROTOCOL.md / G-NUM-protocol / N0), or it would itself alter the
protocol-review census it measures.  The emitter aborts if that guard fails.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUTBOX = REPO / "comms" / "outbox" / "worker-057.jsonl"
CKPT = REPO / "runtime" / "state" / "w057_checkpoint_gnum_protocol_review_census.json"
CKPT_LOG = REPO / "runtime" / "state" / "w057_checkpoints.jsonl"
sys.path.insert(0, str(REPO))
from research_map.schemas import validate_event  # noqa: E402

D = "artifacts/worker-057/g_num_protocol_review_census"
P = {
    "report": f"{D}/report.json",
    "census": f"{D}/census.json",
    "harness": f"{D}/census_protocol_review.py",
    "reportmd": f"{D}/REPORT.md",
    "emitter": f"{D}/emit_events.py",
}
GATES = "numerics/gates.py"
PROTOCOL = "numerics/CONVERGENCE_PROTOCOL.md"
EVENTS = "research_map/events.jsonl"

FALSIFIER = ("Re-run artifacts/worker-057/g_num_protocol_review_census/"
             "census_protocol_review.py at the same pins (numerics/gates.py "
             "fcd1d70991b6eade4aa993dc49b6103e338f68320aabb955d97da5a8f55d996e, "
             "numerics/CONVERGENCE_PROTOCOL.md "
             "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274): the census "
             "block is falsified if any channel disagrees, if any expectation or control fails, "
             "if the binding accept/dissent sets differ from the listed event_ids, or if a fresh "
             "run of the pinned gates.py at these bytes reports a different protocol_review "
             "block. A moved gates.py or protocol hash voids the census for the new bytes; the "
             "review stream is live, so any appended review event re-binds the census for the "
             "new stream bytes.")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def targets_protocol(t: str) -> bool:
    t = t.strip()
    for cand in ("numerics/CONVERGENCE_PROTOCOL.md", "G-NUM-protocol", "N0"):
        if t == cand or t.startswith(cand + "#") or t.startswith(cand + "@"):
            return True
    return False


def main() -> int:
    H = {k: sha(REPO / v) for k, v in P.items()}
    H["gates"] = sha(REPO / GATES)
    H["protocol"] = sha(REPO / PROTOCOL)
    H["events"] = sha(REPO / EVENTS)
    report = json.loads((REPO / P["report"]).read_text())
    census = json.loads((REPO / P["census"]).read_text())

    assert report["verdict"] == "CENSUS_CONFIRMED", "census verdict is not CENSUS_CONFIRMED"
    assert all(c["ok"] for c in report["expectations"]), "an expectation failed"
    assert all(c["ok"] for c in report["controls"]), "a control failed"
    assert all(report["census"]["channel_agreement"].values()), "channel disagreement"
    assert report["pins"]["gates.py"] == H["gates"], "gates.py pin moved since the run"
    assert report["pins"]["protocol"] == H["protocol"], "protocol pin moved since the run"
    assert census["census"]["reviewed"] and census["census"]["contest"], "census not contested"

    target = f"{P['report']}"
    assert not targets_protocol(target), "review target must not bind the protocol counter"
    stream_moved = H["events"] != report["pins"]["events_jsonl"]

    now = report["created_at"]
    pre = f"w057-gnumprotcensus-{report['census_digest'][:12]}"
    common = {"created_at": now, "actor": "worker-057", "node_id": "N0",
              "class_id": "AF-WCC-SCALAR-SPH", "class_ids": ["AF-WCC-SCALAR-SPH"],
              "gate": "G-NUM", "group_id": "numerics",
              "task_id": "W057-GNUM-PROTOCOL-REVIEW-CENSUS-01"}
    evidence = [f"{P['report']}#{H['report'][:12]}", f"{P['census']}#{H['census'][:12]}",
                f"{P['harness']}#{H['harness'][:12]}", f"{P['reportmd']}#{H['reportmd'][:12]}",
                f"{GATES}#{H['gates'][:12]}", f"{PROTOCOL}#{H['protocol'][:12]}"]
    census_ev = [f"{x['event_id']}@{x['created_at']}" for x in census["census"]["binding_dissents"]]

    events = [
        dict(common, event_id=f"{pre}-status-start", event_type="status", status="active",
             hours=0.1,
             summary=("No card exists in comms/inbox/worker-057.jsonl; took ONE bounded "
                      "class-bound task (AF-WCC-SCALAR-SPH / N0 / G-NUM), permitted under "
                      "numerics_lock because it is flat-space/N0 protocol analysis only: an "
                      "independent three-channel census of the pinned "
                      "numerics/gates.py::_protocol_review rule over the live review stream "
                      "(the counter behind B-N0-R2-2 / REC-15 / worker-042 F-042-N0-2). "
                      "Method: frozen stream snapshot; channel A independent stdlib "
                      "re-implementation, channel B the pinned module in a subprocess on the "
                      "same snapshot plus a 14-fixture matrix, channel C the pinned CLI end to "
                      "end; 8 fail-closed controls."),
             evidence_refs=[f"{GATES}#{H['gates'][:12]}", f"{PROTOCOL}#{H['protocol'][:12]}"],
             next_falsifier=FALSIFIER),
        dict(common, event_id=f"{pre}-artifact-report", event_type="artifact",
             artifact_type="independent_verification_report", path=P["report"],
             sha256=H["report"], bytes=(REPO / P["report"]).stat().st_size,
             validation_status="unverified", verdict=report["verdict"],
             checks=f"{sum(c['ok'] for c in report['expectations'])}/{len(report['expectations'])}",
             controls=f"{sum(c['ok'] for c in report['controls'])}/{len(report['controls'])}",
             census_digest=report["census_digest"],
             binding_dissents=census_ev,
             channel_agreement=report["census"]["channel_agreement"],
             supported_by=[{"path": P["harness"], "sha256": H["harness"]},
                           {"path": P["census"], "sha256": H["census"]},
                           {"path": P["reportmd"], "sha256": H["reportmd"]}],
             measured_inputs={GATES: H["gates"], PROTOCOL: H["protocol"],
                              EVENTS + "@census": report["pins"]["events_jsonl"]},
             events_sha256_at_emit=H["events"], stream_moved_since_census=stream_moved,
             reproduce=f"python3 {P['harness']}",
             falsifier=FALSIFIER, evidence_refs=evidence),
        dict(common, event_id=f"{pre}-artifact-census", event_type="artifact",
             artifact_type="protocol_review_census", path=P["census"], sha256=H["census"],
             bytes=(REPO / P["census"]).stat().st_size, validation_status="unverified",
             reviewed=report["census"]["reviewed"], contest=report["census"]["contest"],
             n_binding_accepts=len(report["census"]["binding_accepts"]),
             n_binding_dissents=len(report["census"]["binding_dissents"]),
             census_digest=report["census_digest"],
             falsifier=FALSIFIER, evidence_refs=evidence),
        dict(common, event_id=f"{pre}-artifact-harness", event_type="artifact",
             artifact_type="verifier_script", path=P["harness"], sha256=H["harness"],
             bytes=(REPO / P["harness"]).stat().st_size, validation_status="unverified",
             reproduce=f"python3 {P['harness']}", falsifier=FALSIFIER, evidence_refs=evidence),
        dict(common, event_id=f"{pre}-artifact-reportmd", event_type="artifact",
             artifact_type="report_markdown", path=P["reportmd"], sha256=H["reportmd"],
             bytes=(REPO / P["reportmd"]).stat().st_size, validation_status="unverified",
             falsifier=FALSIFIER, evidence_refs=evidence),
        dict(common, event_id=f"{pre}-review-census", event_type="review",
             reviewer="worker-057 (advisory; independent of astra-lead-numerics)",
             target_id=f"{P['report']}#{H['report']}", target_path=P["report"],
             reviewed_sha256=H["report"], verdict="accept", score=4.0, hard_failures=[],
             findings=[
                 {"severity": "confirm", "check": "F1",
                  "finding": ("At protocol 1e6cdf04d7a2 the pinned counter yields reviewed=true, "
                              f"contest=true: {len(report['census']['binding_accepts'])} binding "
                              f"accepts and {len(report['census']['binding_dissents'])} standing "
                              "binding dissents; every channel (A/B/C) agrees and 14/14 fixtures "
                              "plus 8/8 fail-closed controls pass.")},
                 {"severity": "confirm", "check": "F2",
                  "finding": ("worker-081 holds a binding revise (F1', 00:29:19) and a later "
                              "binding accept (adj2, 00:42:05) at the same protocol revision under "
                              "two target spellings; with no (reviewer,target,hash) supersession "
                              "rule both stand and the contest persists -- B-N0-R2-2 / "
                              "F-042-N0-2 measured at event level, not just asserted.")},
                 {"severity": "confirm", "check": "F3",
                  "finding": ("Counterfactual supersession does NOT clear the contest at this "
                              "hash: under latest-per-reviewer and latest-per-(reviewer, "
                              "normalized target) the w081 F1' revise drops but worker-067's "
                              "00:51 revise and worker-042's 00:52 revise keep contest=true; "
                              "under exact-target supersession only w081 F1' drops. Any "
                              "disposition must address the standing dissents, not only "
                              "supersession semantics.")},
                 {"severity": "advisory", "check": "A1",
                  "finding": ("A target_id pin such as N0#<hash> does not by itself bind; a cited "
                              "hash must appear in reviewed_sha256/artifact_sha256/"
                              "reviewed_protocol_hash or as an evidence_refs pin "
                              "(numerics/CONVERGENCE_PROTOCOL.md#<hash>, >=12 chars).")},
                 {"severity": "advisory", "check": "A2",
                  "finding": ("The #sha256:/# evidence_ref parse has no break, so a long "
                              "#sha256: pin also appends a non-matching 'sha256:...' reading; "
                              "harmless here but a real property of the pinned parser.")},
                 {"severity": "scope", "check": "A3",
                  "finding": ("The census is instant-bound: three protocol-targeting reviews "
                              "landed during this session and events.jsonl moved "
                              "b0ce9a8e -> 8c40b8b9; a later accept by the same author does not "
                              "withdraw an earlier dissent under the pinned rule.")},
             ],
             authority_note=("worker census is advisory evidence only; it sets no gate verdict, "
                             "no node status, no validation_status=passed, does not adjudicate "
                             "the worker-067/worker-081/worker-042 findings, and does not "
                             "release numerics_lock or N1."),
             evidence_refs=evidence),
        dict(common, event_id=f"{pre}-claim", event_type="claim",
             conclusion_type="formal_model",
             statement=(
                 "Artifact-and-code result, not a physics claim: at numerics/gates.py sha256 "
                 f"{H['gates']} and numerics/CONVERGENCE_PROTOCOL.md sha256 {H['protocol']}, "
                 "the pinned rule _protocol_review counts every review event that (a) targets "
                 "numerics/CONVERGENCE_PROTOCOL.md / G-NUM-protocol / N0, (b) cites a hash "
                 "prefix-matching the protocol on disk, (c) is not authored by "
                 "astra-lead-numerics, de-duplicated once by event_id in source order, with "
                 "reviewed=bool(accepts) and contest=bool(dissents) and no "
                 "(reviewer,target,hash) supersession. Over the frozen live stream at events "
                 f"sha256 {H['events']} this yields reviewed=true and contest=true with 4 "
                 "binding accepts and 4 standing binding dissents "
                 f"({'; '.join(census_ev)}). Independent re-implementation (channel A), the "
                 "pinned module on the same snapshot and on its own live re-read (channel B), "
                 "and the pinned CLI (channel C) agree exactly; 14/14 pre-registered fixtures "
                 "and 8/8 fail-closed controls pass. Counterfactually, latest-per-reviewer or "
                 "latest-per-(reviewer, normalized target) supersession would drop worker-081's "
                 "self-superseded revise but leave contest=true via worker-067 and worker-042. "
                 "This measures the counter behind B-N0-R2-2 / F-042-N0-2; it does not "
                 "adjudicate the protocol or change any code."),
             assumptions=[
                 "the operative counter is numerics/gates.py::_protocol_review at the pinned "
                 "sha256; a moved gates.py voids the census for the new bytes",
                 "the review stream is live and the census binds to the frozen snapshot "
                 "(per-source sha256 recorded in report.json); appended review events re-bind it",
                 "channel A is a re-implementation from the pinned docstring and literal source "
                 "fragments, not an import of author code; channels B and C execute the pinned "
                 "bytes",
                 "worker events cannot set node status, validation_status=passed or a gate verdict",
             ],
             falsifier=FALSIFIER, evidence_refs=evidence,
             not_claimed=["gate verdict", "node status", "adjudication of worker-067/081/042",
                          "any change to numerics/gates.py", "numerics_lock/N1 release"]),
        dict(common, event_id=f"{pre}-status-complete", event_type="status", status="active",
             hours=0.4, claims_completion=False,
             summary=("W057-GNUM-PROTOCOL-REVIEW-CENSUS-01 complete as one bounded class-bound "
                      "worker task: verdict CENSUS_CONFIRMED (14/14 expectations, 8/8 controls, "
                      "channels A=B=C), reviewed=true and contest=true at protocol "
                      "1e6cdf04d7a2 with 4 binding accepts and 4 standing binding dissents; "
                      "worker-081's self-superseded revise is still counted and counterfactual "
                      "supersession would not clear the contest. Checkpoint written to "
                      "runtime/state/w057_checkpoint_gnum_protocol_review_census.json and "
                      "runtime/state/w057_checkpoints.jsonl. No gate verdict, no node completion, "
                      "no numerics_lock change; worker slot can be recycled."),
             evidence_refs=evidence, next_falsifier=FALSIFIER),
    ]

    for e in events:
        validate_event(e)

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                try:
                    existing.add(json.loads(line)["event_id"])
                except Exception:
                    pass
    new = [e for e in events if e["event_id"] not in existing]
    if new:
        with OUTBOX.open("a") as f:
            for e in new:
                f.write(json.dumps(e, sort_keys=True) + "\n")

    checkpoint = {
        "checkpoint": "w057-gnumprotcensus-1",
        "at": now,
        "worker": "worker-057",
        "hours_spent_estimate": 0.4,
        "assignment": "W057-GNUM-PROTOCOL-REVIEW-CENSUS-01 (self-selected; no inbox card existed)",
        "node_id": "N0",
        "gate": "G-NUM",
        "class_ids": ["AF-WCC-SCALAR-SPH"],
        "status": {
            "delivered": True,
            "validation_status": "unverified",
            "verdict": report["verdict"],
            "checks": f"{sum(c['ok'] for c in report['expectations'])}/"
                      f"{len(report['expectations'])}",
            "controls": f"{sum(c['ok'] for c in report['controls'])}/"
                        f"{len(report['controls'])}",
            "reviewed": report["census"]["reviewed"],
            "contest": report["census"]["contest"],
            "binding_accepts": report["census"]["binding_accepts"],
            "binding_dissents": [x["event_id"] for x in report["census"]["binding_dissents"]],
            "channel_agreement": report["census"]["channel_agreement"],
            "census_digest": report["census_digest"],
            "no_completion_claim": ("worker cannot set done/passed, a gate verdict, or release "
                                    "numerics_lock/N1"),
        },
        "inputs": {
            "numerics/gates.py": {"sha256": H["gates"], "stable_start_to_end": True},
            "numerics/CONVERGENCE_PROTOCOL.md": {"sha256": H["protocol"],
                                                 "stable_start_to_end": True},
            "research_map/events.jsonl": {
                "sha256_at_census": report["pins"]["events_jsonl"],
                "sha256_at_emit": H["events"],
                "stream_moved_since_census": stream_moved,
                "note": "live stream; census is instant-bound to sha256_at_census"},
        },
        "artifacts": {P[k]: H[k] for k in ("report", "census", "harness", "reportmd", "emitter")},
        "events_appended": [e["event_id"] for e in events],
        "falsifier": FALSIFIER,
        "next_falsifier": ("An independent (different-worker) re-run of the census harness, and a "
                           "controller/lead disposition of B-N0-R2-2; any append to the review "
                           "stream or move of gates.py/protocol re-binds or voids the census."),
    }
    CKPT.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
    already = False
    if CKPT_LOG.exists():
        for line in CKPT_LOG.read_text().splitlines():
            if line.strip() and json.loads(line).get("checkpoint") == checkpoint["checkpoint"]:
                already = True
    if not already:
        with CKPT_LOG.open("a") as f:
            f.write(json.dumps(checkpoint, sort_keys=True) + "\n")
    print(json.dumps({"events_total": len(events), "appended": len(new),
                      "skipped_existing": len(events) - len(new),
                      "checkpoint": str(CKPT.relative_to(REPO)),
                      "checkpoint_appended": not already,
                      "hashes": {k: v[:12] for k, v in H.items()}}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
