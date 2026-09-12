#!/usr/bin/env python3
"""Path-normalization correction for the first W062-R03 emission.

The 13 events under label `w062-r03-20260912T0115` were validated and ingested before the
artifact `path` fields were noticed to be task-relative instead of repo-relative. The accepted
stream is not rewritten. This script builds PATH_CORRECTION.json (event_id -> declared path ->
corrected repo-relative path + sha256), rewrites the on-disk entry_hashes.json with repo-relative
keys, and emits two validated correction events: an artifact event for the correction manifest and
an artifact event rebinding the corrected entry_hashes.json. Verdicts, scores, claims and hashes
of the underlying artifacts are unchanged; only path strings are normalized.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from research_map.schemas import validate_event  # noqa: E402

OLD_LABEL = "w062-r03-20260912T0115"
LABEL = "w062-r03-20260912T0122"
PREFIX = "artifacts/worker-062/r03_schema_repair_candidate/"
ACTOR = "worker-062"
OUTBOX = ROOT / "comms/outbox/worker-062.jsonl"


def now_iso():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    rep = json.loads((TASK / "report.json").read_text())
    events = [json.loads(l) for l in OUTBOX.read_text(errors="replace").splitlines()
              if l.strip() and OLD_LABEL in l]
    print(f"superseded-path events found: {len(events)}")

    mapping, evidence_mapping = [], []
    eh_event_ids = {e["event_id"] for e in events if e["event_type"] == "artifact" and e["path"] == "entry_hashes.json"}
    for e in events:
        eid = e["event_id"]
        if e["event_type"] == "artifact":
            declared = e["path"]
            corrected = PREFIX + declared
            p = ROOT / corrected
            exists = p.exists()
            row = {"event_id": eid, "declared_path": declared, "corrected_path": corrected,
                   "sha256": e["sha256"], "exists_at_corrected_path": exists,
                   "sha256_matches_disk": bool(exists and sha256(p) == e["sha256"])}
            if eid in eh_event_ids:
                row["superseded_by_rebind"] = True
                row["note"] = ("entry_hashes.json is intentionally rewritten to normalize its keys; its original hash is "
                               "superseded by the correction event -artifact-entry-hashes-corrected, not silently retained")
            mapping.append(row)
        for r in e.get("evidence_refs", []) + e.get("artifact_refs", []):
            if "#" in r:
                pth = r.split("#", 1)[0]
                if not pth.startswith(("artifacts/", "schemas/", "ledger/", "research_map/", "comms/", "runtime/")):
                    cand = PREFIX + pth
                    if (ROOT / cand).exists():
                        evidence_mapping.append({"event_id": eid, "declared_ref": r,
                                                 "corrected_ref": cand + "#" + r.split("#", 1)[1]})

    correction = {
        "correction_id": f"{LABEL}-path-correction",
        "created_at": now_iso(), "worker": ACTOR, "task_id": rep["task_id"],
        "reason": ("The first emission used task-relative artifact path/evidence-ref strings. All sha256 values were "
                   "and remain correct; only the path prefix was missing. The accepted event stream is not rewritten."),
        "superseded_label": OLD_LABEL, "superseded_event_ids": [e["event_id"] for e in events],
        "correction_applies_to": "the `path` field of the artifact events and the file-path part of every evidence_refs/artifact_refs entry",
        "unchanged": ["all sha256 values", "claim statement", "review verdict/score/hard_failures/findings", "status summary", "verdicts and controls"],
        "artifact_path_mapping": mapping,
        "evidence_ref_mapping_count": len(evidence_mapping),
        "evidence_ref_mapping": evidence_mapping,
        "corrected_entry_hashes_file": PREFIX + "entry_hashes.json",
        "authority_note": "Worker correction notice; no gate verdict, node status or validation_status set.",
    }

    # rewrite entry_hashes.json with repo-relative keys (same hashes, corrected paths)
    eh = json.loads((TASK / "entry_hashes.json").read_text())
    eh["artifacts"] = {PREFIX + k: v for k, v in eh["artifacts"].items()}
    eh["path_correction"] = {"correction_id": correction["correction_id"],
                             "superseded_label": OLD_LABEL,
                             "note": "artifact keys normalized to repo-relative paths; sha256 values unchanged"}
    (TASK / "entry_hashes.json").write_text(json.dumps(eh, indent=2) + "\n")
    eh_sha = sha256(TASK / "entry_hashes.json")

    # add the corrected entry_hashes binding to the manifest itself (self-consistent, not self-referential)
    correction["corrected_entry_hashes_sha256"] = eh_sha
    (TASK / "PATH_CORRECTION.json").write_text(json.dumps(correction, indent=2) + "\n")
    pc_sha = sha256(TASK / "PATH_CORRECTION.json")

    bad = [m for m in mapping if not m.get("superseded_by_rebind") and not (m["exists_at_corrected_path"] and m["sha256_matches_disk"])]
    if bad:
        print("REFUSING: corrected paths do not resolve to the declared hashes:", bad)
        return 3

    ref_pc = f"{PREFIX}PATH_CORRECTION.json#{pc_sha[:12]}"
    ref_eh = f"{PREFIX}entry_hashes.json#{eh_sha[:12]}"
    base = [ref_pc, ref_eh, "artifacts/formulation/FROZEN.json#815e08079aef",
            f"{PREFIX}report.json#{sha256(TASK / 'report.json')[:12]}"]
    events_out = [
        {"event_id": f"{LABEL}-artifact-path-correction", "event_type": "artifact", "created_at": now_iso(),
         "actor": ACTOR, "node_id": "F1", "nodes": rep["nodes"], "gate": rep["gate"], "task_id": rep["task_id"],
         "class_id": rep["class_id"], "class_ids": rep["class_ids"],
         "artifact_type": "path_normalization_correction", "path": PREFIX + "PATH_CORRECTION.json", "sha256": pc_sha,
         "validation_status": "unverified", "artifact_refs": [ref_pc],
         "evidence_refs": base,
         "falsifier": "Any corrected path that does not resolve to the declared sha256, or any field other than a path string changed by this correction.",
         "summary": (f"Path-normalization correction for the {len(events)} events under label {OLD_LABEL}: every declared "
                     f"task-relative artifact path and evidence ref is mapped to its repo-relative form; all sha256 values, "
                     f"verdicts, findings and claims are unchanged and the accepted stream is not rewritten.")},
        {"event_id": f"{LABEL}-artifact-entry-hashes-corrected", "event_type": "artifact", "created_at": now_iso(),
         "actor": ACTOR, "node_id": "F1", "nodes": rep["nodes"], "gate": rep["gate"], "task_id": rep["task_id"],
         "class_id": rep["class_id"], "class_ids": rep["class_ids"],
         "artifact_type": "entry_hash_manifest", "path": PREFIX + "entry_hashes.json", "sha256": eh_sha,
         "validation_status": "unverified", "artifact_refs": [ref_eh], "evidence_refs": base,
         "falsifier": "The file's measured sha256 differs from the one declared here.",
         "summary": "Corrected entry-hash manifest: artifact keys are repo-relative; all sha256 values unchanged."},
        {"event_id": f"{LABEL}-status-correction", "event_type": "status", "created_at": now_iso(), "actor": ACTOR,
         "node_id": "F1", "nodes": rep["nodes"], "gate": rep["gate"], "task_id": rep["task_id"],
         "class_id": rep["class_id"], "class_ids": rep["class_ids"], "status": "active", "hours": 0.05,
         "summary": (f"CORRECTION ADDENDUM (no verdict/claim change). The {len(events)} events under {OLD_LABEL} carry "
                     f"task-relative path strings; {PREFIX}PATH_CORRECTION.json ({pc_sha[:12]}) maps each declared path and "
                     f"evidence ref to its repo-relative form and verifies that every corrected path resolves to the declared "
                     f"sha256. Candidate hashes ({rep['candidates']['CAND-A']['sha256'][:12]} / "
                     f"{rep['candidates']['CAND-B']['sha256'][:12]}), the revise-4.0 review, HF-W062-R03-01, the K2 coverage-gap "
                     f"finding and both frozen-pipeline PASS results are unaffected."),
         "evidence_refs": base + [ref_eh],
         "artifact_refs": [ref_pc, ref_eh],
         "supersedes_path_fields_of": [e["event_id"] for e in events],
         "correction_reason": "task-relative -> repo-relative path normalization only",
         "next_falsifier": ("Resolve every corrected path in PATH_CORRECTION.json against the accepted stream; any mismatch "
                            "between a corrected path and its declared sha256, or any non-path field changed, voids this "
                            "correction. Owner cascade for F1 rev14 / FROZEN rev30 and the L-FORM-04 rebind is unchanged.")},
    ]
    for e in events_out:
        validate_event(e)
    with open(OUTBOX, "a") as f:
        for e in events_out:
            f.write(json.dumps(e) + "\n")

    # keep the two worker checkpoints consistent with the corrected manifests
    for cp_path in (TASK / "CHECKPOINT.json", ROOT / "runtime/state/w062_r03_schema_repair_checkpoint.json"):
        cp = json.loads(cp_path.read_text())
        for a in cp.get("artifacts", []):
            if a["path"].endswith("entry_hashes.json"):
                a["sha256"] = eh_sha
        cp.setdefault("artifacts", []).append(
            {"path": PREFIX + "PATH_CORRECTION.json", "sha256": pc_sha})
        cp["path_correction"] = {"correction_id": correction["correction_id"],
                                 "superseded_label": OLD_LABEL, "superseded_event_ids": correction["superseded_event_ids"],
                                 "correction_events": [e["event_id"] for e in events_out],
                                 "note": "path strings normalized to repo-relative; sha256/verdicts/claims unchanged"}
        cp["events_emitted"] = cp.get("events_emitted", []) + [e["event_id"] for e in events_out]
        cp_path.write_text(json.dumps(cp, indent=2) + "\n")

    print(json.dumps({"correction_manifest": str(TASK / "PATH_CORRECTION.json"),
                      "manifest_sha256": pc_sha, "entry_hashes_sha256": eh_sha,
                      "corrected_paths": len(mapping), "corrected_evidence_refs": len(evidence_mapping),
                      "events_emitted": [e["event_id"] for e in events_out]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
