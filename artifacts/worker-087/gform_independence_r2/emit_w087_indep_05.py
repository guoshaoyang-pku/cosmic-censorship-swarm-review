#!/usr/bin/env python3
"""W087-GFORM-INDEP-05: write the checkpoint, sha256 sidecars and outbox events.

Idempotent: an event whose event_id already exists in the outbox is not appended again.
Every emitted event is validated with research_map/schemas.validate_event before writing.

Usage: python3 emit_w087_indep_05.py --dir <r2-dir> --root <repo>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
STAMP = "w087-20260912T0108"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sidecar(p: Path) -> None:
    (p.parent / (p.name + ".sha256")).write_text(f"{sha256_file(p)}  {p.name}\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--root", required=True)
    a = ap.parse_args()
    d = Path(a.dir).resolve()
    root = Path(a.root).resolve()
    sys.path.insert(0, str(root / "research_map"))
    from schemas import validate_event  # noqa: E402

    now = datetime.now(CST).isoformat(timespec="seconds")
    summary = json.loads((d / "summary.json").read_text())
    report = json.loads((d / "snapshot_run3" / "report.json").read_text())
    man = json.loads((d / "snapshot" / "MANIFEST.json").read_text())

    rel = lambda p: str(p.relative_to(root))  # noqa: E731
    files = {
        "instrument": d / "audit_gform_independence.py",
        "snapshot_builder": d / "build_snapshot.py",
        "summarizer": d / "summarize_w087_indep_05.py",
        "snapshot_manifest": d / "snapshot" / "MANIFEST.json",
        "report": d / "snapshot_run3" / "report.json",
        "summary": d / "summary.json",
        "readme": d / "README.md",
        "checkpoint": d / "CHECKPOINT.json",
    }

    # ---- checkpoint (written before hashing so the sidecar covers it) -------------------
    per_class = summary["per_class"]
    checkpoint = {
        "checkpoint_id": "w087-gform-indep-05-ckpt-20260912T0108+0800",
        "at": now,
        "actor": "worker-087",
        "role": "worker",
        "slot": "087",
        "instance": "worker-087-20260912T005851-968807",
        "lifecycle": "one bounded class-bound task, then exit",
        "task_id": "W087-GFORM-INDEP-05",
        "supersedes": {
            "task_id": "W087-GFORM-INDEP-04",
            "report": "artifacts/worker-087/gform_independence/report.json#fe968c1c282e",
            "carried_forward": "announcement gap closed; coverage re-measured at the post-repair bytes",
        },
        "node_ids": ["F1", "F2a", "F2b"],
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "task": ("re-measure the effective independent full-schema accept coverage at the rev-13 / "
                 "FROZEN rev-29 G-FORM pins after the evidence-binding repair, with the corpus "
                 "frozen by snapshot so the measurement is reproducible"),
        "task_status": "complete_unreviewed",
        "verdict": "GATE_CRITERION_NOT_MET_AT_REV13",
        "verdict_reason": ("F1 (5 clusters) and F2a (3 clusters) each meet the two-independent-"
                           "full-schema-accepts criterion at the measured pins; F2b has exactly 1 "
                           "cluster (worker-061) and is the sole remaining gap."),
        "pins": summary["pins"],
        "measurement_basis": summary["measurement_basis"],
        "per_class": {
            k: {
                "class_id": v["class_id"],
                "sha256": v["sha256"],
                "effective_accept_clusters": v["effective_independent_full_schema_accept_clusters"],
                "criterion_two_independent_accepts": v["criterion_two_independent_accepts"],
                "full_schema_accept_reviewers": v["full_schema_accept_reviewers"],
            }
            for k, v in per_class.items()
        },
        "remaining_gap": summary["remaining_gap"],
        "freeze_state": summary["freeze_state"],
        "controls_ok": summary["controls"]["ok"],
        "controls_passed": summary["controls"]["passed"],
        "controls_total": summary["controls"]["total"],
        "determinism": {
            "runs": summary["measurement_basis"]["runs_on_snapshot"],
            "digests_equal": summary["measurement_basis"]["three_run_digests_equal"],
            "verdict_digest_sha256": summary["measurement_basis"]["verdict_digest_sha256"],
        },
        "artifact_sha256": {
            "audit_gform_independence.py": sha256_file(files["instrument"]),
            "build_snapshot.py": sha256_file(files["snapshot_builder"]),
            "summarize_w087_indep_05.py": sha256_file(files["summarizer"]),
            "snapshot/MANIFEST.json": sha256_file(files["snapshot_manifest"]),
            "snapshot_run3/report.json": sha256_file(files["report"]),
            "summary.json": sha256_file(files["summary"]),
            "README.md": sha256_file(files["readme"]),
        },
        "falsifier": summary["falsifiers"],
        "next_falsifier": ("a full-schema accept bound to schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe "
                           "from a reviewer other than worker-061 in an independent cluster; or any "
                           "move of the three canonical pins / FROZEN rev 29"),
        "authority": summary["authority"],
        "self_reference": "this checkpoint excludes its own post-write sha256; the sidecar records it",
    }
    (d / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
    state_copy = root / "runtime" / "state" / "worker-087_checkpoint_gform_indep_05.json"
    shutil.copy2(d / "CHECKPOINT.json", state_copy)

    for p in files.values():
        sidecar(p)

    # ---- events -------------------------------------------------------------------------
    ev = lambda s: f"{rel(files[s])}#{sha256_file(files[s])[:12]}"  # noqa: E731
    common_refs = [
        ev("report"),
        ev("summary"),
        ev("instrument"),
        ev("snapshot_manifest"),
        "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
        "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
        "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
        "artifacts/formulation/FROZEN.json#815e08079aef",
        "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
        "research_map/events.jsonl",
    ]
    classes = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
    f2b = per_class["F2b"]
    events = [
        {
            "event_id": f"{STAMP}-artifact-instrument",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-087",
            "task_id": "W087-GFORM-INDEP-05",
            "node_id": "F1,F2a,F2b",
            "class_id": "AF-WCC-VAC-GEN",
            "class_ids": classes,
            "gate": "G-FORM",
            "artifact_type": "audit_instrument",
            "path": rel(files["instrument"]),
            "sha256": sha256_file(files["instrument"]),
            "validation_status": "unverified",
            "note": ("Frozen INDEP-04 instrument, byte-identical (sha f970bc8918c1). Runs read-only against "
                     "research_map/events.jsonl + comms/outbox/** + reviews/*.json; strict target binding, "
                     "primary-hash binding, one verdict per reviewer, character-5-gram + evidence-channel "
                     "clustering, manifest/mirror/announcement re-measure, 8 fail-closed controls."),
            "evidence_refs": common_refs,
        },
        {
            "event_id": f"{STAMP}-artifact-snapshot",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-087",
            "task_id": "W087-GFORM-INDEP-05",
            "node_id": "F1,F2a,F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": classes,
            "gate": "G-FORM",
            "artifact_type": "input_corpus_snapshot",
            "path": rel(files["snapshot_manifest"]),
            "sha256": sha256_file(files["snapshot_manifest"]),
            "validation_status": "unverified",
            "note": (f"{man['n_files']} files copied at {man['snapshot_started_at']}; manifest digest "
                     f"{man['manifest_digest_sha256']}; all measured pins matched the live canonical bytes "
                     "at snapshot close. Needed because three live-tree runs at 01:00-01:01 produced three "
                     "different verdict digests (see moving_target_attempts/)."),
            "evidence_refs": common_refs,
        },
        {
            "event_id": f"{STAMP}-artifact-report",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-087",
            "task_id": "W087-GFORM-INDEP-05",
            "node_id": "F1,F2a,F2b",
            "class_id": "AF-WCC-VAC-GEN",
            "class_ids": classes,
            "gate": "G-FORM",
            "artifact_type": "gform_independence_and_freeze_report",
            "path": rel(files["report"]),
            "sha256": sha256_file(files["report"]),
            "validation_status": "unverified",
            "note": (f"Verdict digest {summary['measurement_basis']['verdict_digest_sha256'][:12]}; identical "
                     "across three runs on the frozen snapshot; controls 8/8; pins stable during every run."),
            "evidence_refs": common_refs,
        },
        {
            "event_id": f"{STAMP}-artifact-summary",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-087",
            "task_id": "W087-GFORM-INDEP-05",
            "node_id": "F1,F2a,F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": classes,
            "gate": "G-FORM",
            "artifact_type": "coverage_measurement",
            "path": rel(files["summary"]),
            "sha256": sha256_file(files["summary"]),
            "validation_status": "unverified",
            "note": ("Derived per-class adjudication: F1 5 clusters, F2a 3 clusters, F2b 1 cluster; "
                     "gate-level criterion not met, sole gap F2b."),
            "evidence_refs": common_refs,
        },
        {
            "event_id": f"{STAMP}-claim-f1f2a-met",
            "event_type": "claim",
            "created_at": now,
            "actor": "worker-087",
            "task_id": "W087-GFORM-INDEP-05",
            "node_id": "F1,F2a",
            "class_id": "AF-WCC-VAC-GEN",
            "class_ids": classes,
            "gate": "G-FORM",
            "conclusion_type": "formal_model",
            "statement": (
                "Coverage measurement (not a gate verdict): at the snapshot of 2026-09-12T01:02:11+08:00, "
                "the effective independent full-schema accept clusters bound to the primary canonical "
                "hashes are F1=5 (workers 052,072,075,080,085,089 -> 5 clusters) at "
                "schemas/af_wcc_vacuum.yaml#d9cebb9404b2 and F2a=3 (workers 017,034,072) at "
                "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3. Both classes therefore meet the G-FORM "
                "criterion 'two independent full-schema accepts' at these pins after target/hash binding, "
                "one-verdict-per-reviewer and text/evidence-channel dedup."),
            "assumptions": [
                "the canonical bytes did not move during the snapshot or the three runs (verified at run start and end)",
                "reviews were harvested from research_map/events.jsonl, comms/outbox/** and reviews/*.json up to the snapshot instant",
                "an accept counts only if a primary target field names the schema or the record declares counts_as_full_schema_verdict=true",
                "clusters are formed by reviewer identity, findings-text Jaccard >= 0.6, or a shared non-target evidence channel",
            ],
            "falsifier": (
                "two counted clusters are shown to share an instrument, review document or verdict text; or a "
                "hash-bound verdict excluded by the harvest is shown to name the schema directly at the reported "
                "revision; or the pins move to different bytes, voiding the binding."),
            "evidence_refs": common_refs,
            "artifact_refs": [ev("report"), ev("summary"), ev("snapshot_manifest")],
        },
        {
            "event_id": f"{STAMP}-claim-f2b-gap",
            "event_type": "claim",
            "created_at": now,
            "actor": "worker-087",
            "task_id": "W087-GFORM-INDEP-05",
            "node_id": "F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": classes,
            "gate": "G-FORM",
            "conclusion_type": "formal_model",
            "statement": (
                "Coverage measurement (not a gate verdict): at the snapshot of 2026-09-12T01:02:11+08:00, "
                "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe has 17 hash-bound review records from 11 distinct "
                "reviewers with verdicts accept 1, inconclusive 1, revise 9, and exactly 1 effective independent "
                "full-schema accept cluster (worker-061, event w061-varstrength-20260912T0055-review-f2b, score "
                "4.0, 00:54:27, direct schema target; no advisory accepts). F2b therefore does NOT meet the "
                "G-FORM criterion 'two independent full-schema accepts' at this pin, and it is the only class "
                "of F1/F2a/F2b that does not; the gate-level criterion is not met at rev 13 / FROZEN rev 29."),
            "assumptions": [
                "the three rev-28-bound F2b accepts are void because they bind superseded bytes and are excluded by primary-hash binding",
                "reviews of sandbox copies or derived documents are advisory and are not counted",
                "the single accept is genuine and hash-bound; it is counted as one cluster, not more",
            ],
            "falsifier": (
                "a full-schema accept bound to schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe from a reviewer other "
                "than worker-061 whose findings text and evidence channels form an independent cluster; or any "
                "move of the F2b canonical pin / FROZEN rev 29."),
            "evidence_refs": common_refs,
            "artifact_refs": [ev("report"), ev("summary"), ev("snapshot_manifest")],
        },
        {
            "event_id": f"{STAMP}-blocker-f2b",
            "event_type": "blocker",
            "created_at": now,
            "actor": "worker-087",
            "task_id": "W087-GFORM-INDEP-05",
            "node_id": "F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": classes,
            "gate": "G-FORM",
            "description": (
                "G-FORM coverage gap: F2b at b2ab6acb2bbe has only 1 effective independent full-schema accept "
                "cluster (worker-061). F1 (5 clusters) and F2a (3 clusters) meet the criterion; F2b is the sole "
                "class blocking the gate on coverage at the post-repair bytes."),
            "needed_to_unblock": (
                "one full-schema accept bound by its primary hash to schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe "
                "from a reviewer other than worker-061, forming a separate independence cluster (no shared "
                "findings text or evidence channel)."),
            "evidence_refs": common_refs,
        },
        {
            "event_id": f"{STAMP}-artifact-checkpoint",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-087",
            "task_id": "W087-GFORM-INDEP-05",
            "node_id": "F1,F2a,F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": classes,
            "gate": "G-FORM",
            "artifact_type": "worker_checkpoint",
            "path": rel(files["checkpoint"]),
            "sha256": sha256_file(files["checkpoint"]),
            "validation_status": "unverified",
            "evidence_refs": common_refs,
        },
        {
            "event_id": f"{STAMP}-artifact-checkpoint-state",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-087",
            "task_id": "W087-GFORM-INDEP-05",
            "node_id": "F1,F2a,F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": classes,
            "gate": "G-FORM",
            "artifact_type": "worker_checkpoint_state_copy",
            "path": rel(state_copy),
            "sha256": sha256_file(files["checkpoint"]),
            "validation_status": "unverified",
            "evidence_refs": common_refs,
        },
        {
            "event_id": f"{STAMP}-status-exit",
            "event_type": "status",
            "created_at": now,
            "actor": "worker-087",
            "task_id": "W087-GFORM-INDEP-05",
            "node_id": "F1,F2a,F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": classes,
            "gate": "G-FORM",
            "status": "active",
            "hours": 1.0,
            "summary": (
                "W087-GFORM-INDEP-05 complete (bounded class-bound task; no inbox card). Re-measured effective "
                "independent full-schema accept coverage at the post-repair rev-13 / FROZEN rev-29 pins on a "
                "hash-pinned corpus snapshot (636 files, manifest 58db6f6ffb73): F1 5 clusters, F2a 3 clusters, "
                "F2b 1 cluster, controls 8/8, three runs with identical digest 8c1184044806. Freeze state "
                "REPINNED_AND_ANNOUNCED with 3/3 owner announcements, so the INDEP-04 announcement blocker is "
                "closed. Gate-level criterion still not met: F2b is the sole gap and needs one more independent "
                "full-schema accept at b2ab6acb2bbe. Worker cannot set status=done, validation_status=passed or "
                "any gate verdict; blocker w087-20260912T0108-blocker-f2b records the gap."),
            "evidence_refs": common_refs,
            "next_falsifier": (
                "a full-schema accept bound to schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe from a non-worker-061 "
                "reviewer in a separate cluster; or any move of the three canonical pins / FROZEN rev 29; or a "
                "re-run of the frozen instrument on the snapshot yielding a different verdict digest."),
        },
    ]

    outbox = root / "comms" / "outbox" / "worker-087.jsonl"
    existing = set()
    if outbox.exists():
        for line in outbox.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except ValueError:
                continue
    emitted, skipped = [], []
    lines = []
    for e in events:
        validate_event(e)
        if e["event_id"] in existing:
            skipped.append(e["event_id"])
            continue
        line = json.dumps(e, sort_keys=True)
        lines.append(line)
        emitted.append({"event_id": e["event_id"], "event_type": e["event_type"], "sha256": hashlib.sha256(line.encode()).hexdigest()})
    if lines:
        with outbox.open("a") as fh:
            fh.write("\n".join(lines) + "\n")

    record = {
        "at": now,
        "task_id": "W087-GFORM-INDEP-05",
        "outbox": rel(outbox),
        "event_ids": [e["event_id"] for e in emitted],
        "event_sha256": [e["sha256"] for e in emitted],
        "skipped_already_present": skipped,
        "pins": {
            "instrument": sha256_file(files["instrument"]),
            "snapshot_manifest": sha256_file(files["snapshot_manifest"]),
            "snapshot_manifest_digest": man["manifest_digest_sha256"],
            "report": sha256_file(files["report"]),
            "summary": sha256_file(files["summary"]),
            "checkpoint": sha256_file(files["checkpoint"]),
            "readme": sha256_file(files["readme"]),
            "verdict_digest": summary["measurement_basis"]["verdict_digest_sha256"],
        },
    }
    (d / "events_emitted.json").write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    sidecar(d / "events_emitted.json")
    print(json.dumps({
        "emitted": len(emitted),
        "skipped": len(skipped),
        "checkpoint": rel(files["checkpoint"]),
        "state_copy": rel(state_copy),
        "outbox": rel(outbox),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
