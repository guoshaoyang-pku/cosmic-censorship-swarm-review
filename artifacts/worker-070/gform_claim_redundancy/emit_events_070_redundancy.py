#!/usr/bin/env python3
"""Emit W070-GFORM-CLAIM-REDUNDANCY-01 events, SHA256SUMS and worker checkpoint.

Appends 12 events to comms/outbox/worker-070.jsonl (11 task events + 1 checkpoint
artifact event), writes SHA256SUMS.txt / SUPERSEDED_SHA256SUMS.txt and
runtime/state/w070_checkpoint_gform_claim_redundancy.json. Does NOT run ingest and
does not touch any canonical path. All hashes are measured from disk at emission.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "artifacts" / "worker-070" / "gform_claim_redundancy"
OUTBOX = ROOT / "comms" / "outbox" / "worker-070.jsonl"
CKPT = ROOT / "runtime" / "state" / "w070_checkpoint_gform_claim_redundancy.json"
CST = timezone(timedelta(hours=8))

TASK_ID = "W070-GFORM-CLAIM-REDUNDANCY-01"
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
SNAP = "artifacts/worker-070/gform_claim_redundancy/snapshot/events.102265f79405.jsonl"

FALSIFIER = (
    "Re-run `census_070_redundancy.py --run` against the snapshot sha256 recorded in "
    "frame.json; falsified if any reported count, signature, cluster membership or control "
    "outcome differs, or if a claim in the universe is shown to cite a hash token outside its "
    "reported signature, or if two claims reported in one cluster have non-identical declared "
    "reference sets. The addendum is falsified if a per-pin count differs on re-run or a cited "
    "canonical pair is missing. A snapshot sha256 mismatch, or an events.jsonl source hash that "
    "changed across the preregistration copy, voids the run rather than falsifying it. Findings "
    "are snapshot-bound and assert nothing about cosmic censorship."
)


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def h12(p: Path) -> str:
    return sha256_file(p)[:12]


def main() -> int:
    ts = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    created = now()

    report = json.loads((TASK / "report.json").read_text())
    addendum = json.loads((TASK / "addendum.json").read_text())
    frame = json.loads((TASK / "frame.json").read_text())

    # ---- SHA256SUMS over live deliverables (incl. this emitter)
    sums_files = [
        "frame.json", "frame.sha256.txt", "census_070_redundancy.py",
        "report.json", "addendum_070.py", "addendum.json", "run.log",
        "README.md", "emit_events_070_redundancy.py",
        "snapshot/events.102265f79405.jsonl", "snapshot/superseded/README.md",
        "SUPERSEDED_SHA256SUMS.txt",
    ]
    sup = sorted((TASK / "snapshot" / "superseded").glob("events.*.jsonl"))
    (TASK / "SUPERSEDED_SHA256SUMS.txt").write_text(
        "\n".join(f"{sha256_file(p)}  artifacts/worker-070/gform_claim_redundancy/"
                  f"snapshot/superseded/{p.name}" for p in sup) + "\n")
    lines = [f"{sha256_file(TASK / f)}  artifacts/worker-070/gform_claim_redundancy/{f}"
             for f in sums_files]
    (TASK / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n")

    H = {f: h12(TASK / f) for f in sums_files}
    H["SHA256SUMS.txt"] = h12(TASK / "SHA256SUMS.txt")
    snap_full = frame["snapshot"]["snapshot_sha256"]
    u = report["universe"]
    a = addendum

    start_summary = (
        "No inbox card exists for worker-070 (relaunched slot). Took ONE bounded class-bound "
        f"task: {TASK_ID}, a pre-registered census of evidence-basis redundancy in the G-FORM "
        "claim stream at a pinned snapshot of research_map/events.jsonl. Declared rules, "
        "universe, controls and falsifier are sealed in frame.json before the analysis run; the "
        "run is read-only, no canonical write, no ingest, no gate verdict."
    )
    evidence = [
        f"artifacts/worker-070/gform_claim_redundancy/report.json#{H['report.json']}",
        f"artifacts/worker-070/gform_claim_redundancy/frame.json#{H['frame.json']}",
        f"artifacts/worker-070/gform_claim_redundancy/addendum.json#{H['addendum.json']}",
        f"artifacts/worker-070/gform_claim_redundancy/census_070_redundancy.py#{H['census_070_redundancy.py']}",
        f"artifacts/worker-070/gform_claim_redundancy/addendum_070.py#{H['addendum_070.py']}",
        f"artifacts/worker-070/gform_claim_redundancy/run.log#{H['run.log']}",
        f"{SNAP}#{snap_full[:12]}",
    ]

    def art(eid, atype, path, sha, summary, refs=None):
        return {
            "event_id": eid, "event_type": "artifact", "created_at": created,
            "actor": "worker-070", "node_id": "F1,F2a,F2b", "group_id": "formulation",
            "gate": "G-FORM", "class_ids": CLASSES, "task_id": TASK_ID,
            "artifact_type": atype, "path": path, "sha256": sha,
            "validation_status": "unverified",
            "summary": summary,
            "evidence_refs": refs or evidence,
            "next_falsifier": FALSIFIER,
        }

    events = []
    events.append({
        "event_id": f"w070R-{ts}-status-start", "event_type": "status",
        "created_at": created, "actor": "worker-070", "node_id": "F1,F2a,F2b",
        "group_id": "formulation", "gate": "G-FORM", "class_ids": CLASSES,
        "status": "active", "hours": 0.4, "task_id": TASK_ID,
        "assignment_ref": "self-taken; no inbox card for worker-070 (relaunched slot)",
        "summary": start_summary, "evidence_refs": evidence, "next_falsifier": FALSIFIER,
    })
    events.append(art(
        f"w070R-{ts}-artifact-frame", "preregistration",
        "artifacts/worker-070/gform_claim_redundancy/frame.json", H["frame.json"],
        "Pre-registered frame: snapshot pin (source hash before/after copy), G-FORM universe "
        "rule, reference keys, hash normalisation, signature and cluster rules, metrics, "
        "7 controls, void conditions and falsifier; sealed with the runner hash in "
        "frame.sha256.txt before the analysis run.",
        [f"artifacts/worker-070/gform_claim_redundancy/frame.sha256.txt#{H['frame.sha256.txt']}",
         f"{SNAP}#{snap_full[:12]}"]))
    events.append(art(
        f"w070R-{ts}-artifact-runner", "instrument",
        "artifacts/worker-070/gform_claim_redundancy/census_070_redundancy.py",
        H["census_070_redundancy.py"],
        "Deterministic stdlib-only read-only instrument (rev3; rev1/rev2 aborted in controls "
        "C5/C7 before any measurement): snapshot copy with source hash guard, universe filter, "
        "hash-token extraction, exact-signature clustering, metrics, 7 controls, idempotence and "
        "exit 3 on control/identity failure.",
        [f"artifacts/worker-070/gform_claim_redundancy/report.json#{H['report.json']}",
         f"artifacts/worker-070/gform_claim_redundancy/frame.json#{H['frame.json']}"]))
    events.append(art(
        f"w070R-{ts}-artifact-report", "measurement_report",
        "artifacts/worker-070/gform_claim_redundancy/report.json", H["report.json"],
        f"Primary machine result at snapshot {snap_full[:12]}: {u['claims']} G-FORM claims from "
        f"{u['actors']} actors / {u['tasks']} tasks cite {u['signatures']} distinct full evidence "
        f"signatures (redundancy {u['redundancy_factor']}); largest identical-signature cluster "
        f"{u['largest_cluster']} (empty-refs); {u['exact_statement_duplicate_claims']} claims in "
        f"{u['exact_statement_duplicate_groups']} exact-statement duplicate groups; 7/7 controls pass."))
    events.append(art(
        f"w070R-{ts}-artifact-addendum-script", "instrument",
        "artifacts/worker-070/gform_claim_redundancy/addendum_070.py", H["addendum_070.py"],
        "Post-frame secondary instrument: parses canonical path#hash pairs from the declared "
        "reference keys and measures target-pin concentration in the same snapshot.",
        [f"artifacts/worker-070/gform_claim_redundancy/addendum.json#{H['addendum.json']}",
         f"artifacts/worker-070/gform_claim_redundancy/report.json#{H['report.json']}"]))
    events.append(art(
        f"w070R-{ts}-artifact-addendum", "post_frame_addendum",
        "artifacts/worker-070/gform_claim_redundancy/addendum.json", H["addendum.json"],
        f"Post-frame exploratory addendum (rules declared after the primary run): "
        f"{a['claims_with_at_least_one_canonical_pin']}/{a['universe_claims']} claims cite a "
        f"canonical G-FORM pin; {a['distinct_target_keys']} distinct target keys; "
        f"{a['claims_sharing_a_target_key']} claims share a target key; top pins are F0 "
        "0abb9ed8a961 (114 claims/58 actors), FROZEN 815e08079aef (113/63), F2b b2ab6acb2bbe "
        "(103/50), F1 d9cebb9404b2 (77/51), F2a e9a27996dfd3 (76/43)."))
    events.append(art(
        f"w070R-{ts}-artifact-readme", "review_note",
        "artifacts/worker-070/gform_claim_redundancy/README.md", H["README.md"],
        "Human-readable summary: pin, primary and secondary tables, the opposite-direction "
        "reading of the two measures, files/hashes, reproduction commands, falsifier and limits.",
        [f"artifacts/worker-070/gform_claim_redundancy/report.json#{H['report.json']}",
         f"artifacts/worker-070/gform_claim_redundancy/addendum.json#{H['addendum.json']}"]))
    events.append(art(
        f"w070R-{ts}-artifact-runlog", "run_log",
        "artifacts/worker-070/gform_claim_redundancy/run.log", H["run.log"],
        "Instrument log: preregistration pin, run counts and the 7 control outcomes.",
        [f"artifacts/worker-070/gform_claim_redundancy/report.json#{H['report.json']}"]))
    events.append(art(
        f"w070R-{ts}-artifact-sums", "manifest",
        "artifacts/worker-070/gform_claim_redundancy/SHA256SUMS.txt", H["SHA256SUMS.txt"],
        "SHA256SUMS over frame, seal, runner, report, addendum script/report, run log, README, "
        "the emitter, the pinned snapshot and the superseded-snapshot note; superseded snapshots "
        "listed separately in SUPERSEDED_SHA256SUMS.txt.",
        [f"artifacts/worker-070/gform_claim_redundancy/SUPERSEDED_SHA256SUMS.txt"
         f"#{H['SUPERSEDED_SHA256SUMS.txt']}"]))

    claim = {
        "event_id": f"w070R-{ts}-claim-redundancy", "event_type": "claim",
        "created_at": created, "actor": "worker-070", "node_id": "F1,F2a,F2b",
        "group_id": "formulation", "gate": "G-FORM", "class_id": "GLOBAL",
        "class_ids": CLASSES, "conclusion_type": "formal_model", "task_id": TASK_ID,
        "statement": (
            f"At the pinned accepted-stream snapshot research_map/events.jsonl sha256 {snap_full} "
            "(8122 lines, 607 claim events; source hash stable across the preregistration copy at "
            "2026-09-12T01:23:44+08:00), the 450 claim events whose class binding intersects the "
            "three G-FORM classes cite 433 distinct full evidence signatures (sorted sets of "
            "distinct 12-hex sha256 tokens under the declared reference keys; claims/signatures = "
            "1.0393), the largest identical-signature cluster is the 6-claim empty-signature "
            "cluster, 30 claims fall in 13 exact-statement duplicate groups (max 3), and 7/7 "
            "pre-registered controls pass. Post-frame addendum: 353/450 claims cite at least one "
            "canonical G-FORM pin, those citations take only 202 distinct canonical target keys, "
            "306 claims share a target key with another claim, and the pins F0 0abb9ed8a961, "
            "FROZEN 815e08079aef, F2b b2ab6acb2bbe, F1 d9cebb9404b2 and F2a e9a27996dfd3 are "
            "cited by 114/113/103/77/76 claims from 58/63/50/51/43 distinct actors. The two "
            "measures diverge because each claim also cites its own worker artifacts: near-unique "
            "declared basis, highly concentrated target. This is a citation-structure measurement "
            "on the event stream; it does not verify that cited bytes exist, does not measure "
            "method independence, and asserts nothing about cosmic censorship."),
        "assumptions": [
            "The snapshot byte sequence is the object under test; the accepted stream continues to grow, so every count is snapshot-bound.",
            "A claim's declared evidence signature is the sorted set of distinct 12-hex sha256 tokens appearing under the declared reference keys of that event.",
            "Claims sharing a signature share their declared evidential basis; this is not a claim that their methods are the same.",
            "Canonical target pins are (path, hash12) pairs parsed from references whose path begins with a declared canonical root; citing the same pin is evidence of neither duplication nor independence.",
            "created_at is not used as a universe boundary because CF-6/CF-14 record future-dated agent timestamps; the snapshot line set is the boundary.",
        ],
        "artifact_refs": [
            f"artifacts/worker-070/gform_claim_redundancy/report.json#{H['report.json']}",
            f"artifacts/worker-070/gform_claim_redundancy/addendum.json#{H['addendum.json']}",
            f"artifacts/worker-070/gform_claim_redundancy/frame.json#{H['frame.json']}",
            f"artifacts/worker-070/gform_claim_redundancy/census_070_redundancy.py#{H['census_070_redundancy.py']}",
        ],
        "evidence_refs": evidence,
        "falsifier": FALSIFIER,
    }
    events.append(claim)
    events.append({
        "event_id": f"w070R-{ts}-status-complete", "event_type": "status",
        "created_at": created, "actor": "worker-070", "node_id": "F1,F2a,F2b",
        "group_id": "formulation", "gate": "G-FORM", "class_ids": CLASSES,
        "status": "active", "hours": 0.4, "task_id": TASK_ID,
        "assignment_ref": "self-taken; no inbox card for worker-070 (relaunched slot)",
        "summary": (
            f"worker-070 bounded task complete and exiting. Snapshot {snap_full[:12]}; "
            f"G-FORM claims {u['claims']} / signatures {u['signatures']} (redundancy "
            f"{u['redundancy_factor']}); exact-statement duplicates {u['exact_statement_duplicate_claims']}; "
            f"target concentration {a['claims_sharing_a_target_key']}/{a['universe_claims']} on "
            f"{a['distinct_target_keys']} target keys; controls 7/7. report.json {H['report.json']}, "
            f"frame.json {H['frame.json']}, addendum.json {H['addendum.json']}, runner "
            f"{H['census_070_redundancy.py']}, checkpoint runtime/state/"
            "w070_checkpoint_gform_claim_redundancy.json. No gate verdict, no node transition, no "
            "canonical write, no ingest."),
        "evidence_refs": evidence, "next_falsifier": FALSIFIER,
    })

    checkpoint = {
        "schema": "worker-checkpoint/v1", "task_id": TASK_ID, "worker": "worker-070",
        "checkpoint_at": created, "status": "bounded_task_complete_unverified",
        "class_ids": CLASSES, "gate": "G-FORM", "group_id": "formulation",
        "node_id": "F1,F2a,F2b", "node_ids": ["F1", "F2a", "F2b"],
        "assignment_ref": "self-taken; no inbox card for worker-070 (relaunched slot)",
        "stop_rule": "1.0 agent-hour; one bounded task; read-only on canonical inputs; no network; no numerics",
        "object_under_test": {
            "path": "research_map/events.jsonl",
            "snapshot_path": SNAP, "snapshot_sha256": snap_full,
            "lines": report["snapshot_lines"], "claim_events": report["claim_events_total"],
            "universe_claims": report["claim_events_in_universe"],
            "frame": "artifacts/worker-070/gform_claim_redundancy/frame.json",
        },
        "verdict": "MEASURED_SNAPSHOT_BOUND",
        "primary": {k: u[k] for k in (
            "claims", "actors", "tasks", "signatures", "redundancy_factor",
            "largest_cluster", "exact_statement_duplicate_groups",
            "exact_statement_duplicate_claims")},
        "addendum": {k: a[k] for k in (
            "claims_with_at_least_one_canonical_pin", "claims_with_no_canonical_pin",
            "distinct_target_keys", "claims_sharing_a_target_key")},
        "controls_all_pass": report["controls_all_pass"],
        "artifacts": {f"artifacts/worker-070/gform_claim_redundancy/{f}":
                      sha256_file(TASK / f) for f in sums_files + ["SHA256SUMS.txt"]},
        "auxiliary_input_sha256_at_emission": {
            "research_map/events.jsonl": sha256_file(ROOT / "research_map" / "events.jsonl"),
        },
        "events_emitted": [e["event_id"] for e in events],
        "next_falsifier": FALSIFIER,
        "authority_note": "worker event; cannot set node status done, validation_status passed, or any gate verdict",
        "non_claims": addendum["non_claims"],
    }
    CKPT.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")

    events.append(art(
        f"w070R-{ts}-artifact-checkpoint", "checkpoint",
        "runtime/state/w070_checkpoint_gform_claim_redundancy.json", h12(CKPT),
        "Worker checkpoint for W070-GFORM-CLAIM-REDUNDANCY-01: snapshot pin, universe, primary "
        "and addendum metrics, artifact hash table, events emitted, authority note. Written after "
        "the task events; not listed in its own events_emitted.",
        [f"artifacts/worker-070/gform_claim_redundancy/report.json#{H['report.json']}",
         f"artifacts/worker-070/gform_claim_redundancy/addendum.json#{H['addendum.json']}"]))

    with OUTBOX.open("a") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    # re-read and validate what was just written
    req = {"event_id", "event_type", "created_at", "actor"}
    req_claim = req | {"class_id", "statement", "conclusion_type", "assumptions",
                       "falsifier", "evidence_refs"}
    req_art = req | {"node_id", "artifact_type", "path", "sha256", "validation_status"}
    n = 0
    for line in OUTBOX.read_text().splitlines()[-len(events):]:
        d = json.loads(line)
        assert not (req - set(d)), d.get("event_id")
        if d["event_type"] == "claim":
            assert not (req_claim - set(d)), d["event_id"]
        if d["event_type"] == "artifact":
            assert not (req_art - set(d)), d["event_id"]
        n += 1
    print(f"OK appended+validated {n} events to {OUTBOX.relative_to(ROOT)}")
    print(f"checkpoint {CKPT.relative_to(ROOT)} sha256 {sha256_file(CKPT)[:12]}")
    for e in events:
        print(" ", e["event_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
