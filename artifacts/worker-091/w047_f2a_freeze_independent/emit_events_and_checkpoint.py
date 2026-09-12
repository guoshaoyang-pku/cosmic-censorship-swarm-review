#!/usr/bin/env python3
"""Emit worker-091's W047-F2A-EXT-FREEZE verification events + checkpoint.

Idempotent: an event whose event_id already occurs in comms/outbox/worker-091.jsonl
is skipped.  Every event is validated with research_map/schemas.validate_event
before it is appended.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TZ = timezone(timedelta(hours=8))
TS = "20260912T0113"
ART = ROOT / "artifacts/worker-091/w047_f2a_freeze_independent"
OUTBOX = ROOT / "comms/outbox/worker-091.jsonl"
STATE = ROOT / "runtime/state"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


files = {
    "report.json": ART / "report.json",
    "README.md": ART / "README.md",
    "verify_w047_f2a_freeze_091.py": ART / "verify_w047_f2a_freeze_091.py",
    "patched/af_scc_c2_vacuum.w047-patched.yaml": ART / "patched/af_scc_c2_vacuum.w047-patched.yaml",
    "snapshots/af_scc_c2_vacuum.e9a27996.yaml": ART / "snapshots/af_scc_c2_vacuum.e9a27996.yaml",
    "snapshots/af_scc_c0_vacuum.b2ab6acb.yaml": ART / "snapshots/af_scc_c0_vacuum.b2ab6acb.yaml",
}
hashes = {k: {"sha256": sha(v), "bytes": v.stat().st_size} for k, v in files.items()}

manifest = {
    "schema": "w091-artifact-manifest/v1",
    "task_id": "W091-W047-F2A-FREEZE-INDEP-01",
    "actor": "worker-091",
    "node_id": "F2a",
    "class_id": "AF-SCC-C2-VAC-GEN",
    "gate": "G-FORM",
    "created_at": now(),
    "review_target": {
        "path": "artifacts/worker-047/f2a_ext_freeze_spec/repair_spec.json",
        "sha256": sha(ROOT / "artifacts/worker-047/f2a_ext_freeze_spec/repair_spec.json"),
        "author_report_sha256": sha(ROOT / "artifacts/worker-047/f2a_ext_freeze_spec/report.json"),
    },
    "files": hashes,
}
(ART / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
manifest_sha = sha(ART / "MANIFEST.json")

report = json.loads((ART / "report.json").read_text())
reviewed_sha = report["review_target"]["reviewed_sha256"]
pins = {k: v["sha256"] for k, v in report["pins_start"].items()}
findings_txt = [f"{f['id']} ({f['severity']}): {f['text']}" for f in report["findings"]]

base = {"created_at": now(), "actor": "worker-091", "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN", "gate": "G-FORM"}
events = []

for name, h in hashes.items():
    kind = {"report.json": "verification_report",
            "README.md": "verification_readme",
            "verify_w047_f2a_freeze_091.py": "verification_instrument",
            "patched/af_scc_c2_vacuum.w047-patched.yaml": "patched_candidate_snapshot",
            "snapshots/af_scc_c2_vacuum.e9a27996.yaml": "pinned_input_snapshot",
            "snapshots/af_scc_c0_vacuum.b2ab6acb.yaml": "pinned_input_snapshot"}[name]
    events.append({**base,
                   "event_id": f"w091-{TS}-w047-f2a-freeze-artifact-{name.replace('/', '-').replace('.', '-')}",
                   "event_type": "artifact",
                   "artifact_type": kind,
                   "path": f"artifacts/worker-091/w047_f2a_freeze_independent/{name}",
                   "sha256": h["sha256"],
                   "bytes": h["bytes"],
                   "validation_status": "unverified",
                   "authority_note": "worker evidence; does not set node status, gate verdict, or validation_status=passed"})

events.append({**base,
               "event_id": f"w091-{TS}-w047-f2a-freeze-artifact-manifest",
               "event_type": "artifact",
               "artifact_type": "manifest",
               "path": "artifacts/worker-091/w047_f2a_freeze_independent/MANIFEST.json",
               "sha256": manifest_sha,
               "validation_status": "unverified"})

events.append({**base,
               "event_id": f"w091-{TS}-w047-f2a-freeze-review",
               "event_type": "review",
               "target_id": "W047-F2A-EXT-FREEZE-SPEC-02",
               "reviewer": "worker-091",
               "artifact": "artifacts/worker-047/f2a_ext_freeze_spec/repair_spec.json",
               "review_file": "artifacts/worker-091/w047_f2a_freeze_independent/report.json",
               "review_file_sha256": hashes["report.json"]["sha256"],
               "reviewed_sha256": reviewed_sha,
               "author_report_sha256": manifest["review_target"]["author_report_sha256"],
               "verdict": "accept",
               "score": 4.5,
               "hard_failures": report["hard_failures"],
               "findings": findings_txt,
               "review_type": "independent_verification_of_repair_spec",
               "blind_to_other_verdicts": True,
               "class_boundary_checked": ("patched copy keeps frozen_regularity=C2, conclusion_type="
                                          "scc_c2_future_inextendibility, residual_comeager, containment "
                                          "chain; only the 3 declared leaves change; C2 content stays "
                                          "distinct from the C0 sibling"),
               "axes_baseline": {k: v["status"] for k, v in report["baseline_axes"].items()},
               "axes_after_declared_patch": {k: v["status"] for k, v in report["repaired_axes"].items()},
               "mutant_table_reproduced": report["controls"]["mutant_table_reproduced"],
               "canonical_gate": {
                   "baseline": report["canonical_gate"]["baseline_snapshot"]["verdict"],
                   "patched": report["canonical_gate"]["patched_snapshot"]["verdict"],
                   "note": "structural gate passes the unrepaired file; content repair is reviewer-carried"},
               "gate_verdict_set": False,
               "artifact_edited": False,
               "falsifier": report["falsifier"],
               "next_falsifier": report["next_falsifier"],
               "evidence_refs": report["evidence_refs"]})

events.append({**base,
               "event_id": f"w091-{TS}-w047-f2a-freeze-claim",
               "event_type": "claim",
               "statement": ("At F2a=e9a27996/f2b=b2ab6acb/FROZEN=815e0807/F0=0abb9ed8, an independent "
                             "implementation of the six freeze axes finds A1-A6 all unresolved on the "
                             "live bytes; applying the W047 spec's declared option-A edits changes only "
                             "extension_predicate.definition, topology.extension_topology and "
                             "falsifier.tier_1.witness_type and resolves A1-A6; all six planted mutants "
                             "reproduce the author's control table; invariants I1-I9 hold; the canonical "
                             "structural gate passes both before and after, so it cannot carry this repair."),
               "conclusion_type": "formal_model",
               "assumptions": [
                   "axis semantics as published by this reviewer, reconstructed from the author's "
                   "control table (repair_spec.json does not publish A6)",
                   "canonical pins are the four measured hashes; drift voids",
                   "the patch is evaluated on a private snapshot, not on canonical bytes"],
               "falsifier": report["falsifier"],
               "evidence_refs": report["evidence_refs"],
               "artifact_refs": [
                   "artifacts/worker-091/w047_f2a_freeze_independent/report.json#" + hashes["report.json"]["sha256"],
                   "artifacts/worker-091/w047_f2a_freeze_independent/patched/af_scc_c2_vacuum.w047-patched.yaml#" + hashes["patched/af_scc_c2_vacuum.w047-patched.yaml"]["sha256"]],
               "pins": pins})

events.append({**base,
               "event_id": f"w091-{TS}-w047-f2a-freeze-status-done",
               "event_type": "status",
               "status": "done",
               "hours": 0.4,
               "summary": ("One bounded class-bound task: independent accept (4.5, no hard failures) of "
                           "W047-F2A-EXT-FREEZE-SPEC-02 at repair_spec.json#" + reviewed_sha[:12] +
                           "; six axes baseline-unresolved -> patched-resolved; mutants and invariants green; "
                           "canonical gate blind to the defect; 3 low findings."),
               "evidence_refs": report["evidence_refs"],
               "next_falsifier": report["next_falsifier"]})

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            existing.add(json.loads(line).get("event_id"))
        except Exception:
            pass

appended, skipped = [], []
with OUTBOX.open("a") as fh:
    for ev in events:
        validate_event(ev)
        if ev["event_id"] in existing:
            skipped.append(ev["event_id"])
            continue
        fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
        appended.append(ev["event_id"])

checkpoint = {
    "checkpoint_id": f"w091-w047-f2a-freeze-ckpt-{TS}",
    "task_id": "W091-W047-F2A-FREEZE-INDEP-01",
    "actor": "worker-091",
    "role": "bounded execution worker; one class-bound task then exit",
    "created_at": now(),
    "node_id": "F2a",
    "class_id": "AF-SCC-C2-VAC-GEN",
    "gate": "G-FORM",
    "authority_note": ("worker-level completion record; does not set node status, gate verdict or "
                       "validation_status=passed; canonical paths read-only"),
    "review_target": manifest["review_target"],
    "pins": pins,
    "drift_during_run": report["drift_during_run"],
    "verdict": report["verdict"],
    "score": report["score"],
    "hard_failures": report["hard_failures"],
    "axes_baseline": {k: v["status"] for k, v in report["baseline_axes"].items()},
    "axes_after_declared_patch": {k: v["status"] for k, v in report["repaired_axes"].items()},
    "controls": {"identity": report["controls"]["identity"]["pass"],
                 "mutant_table_reproduced": report["controls"]["mutant_table_reproduced"],
                 "degenerate": report["controls"]["degenerate"]["pass"]},
    "canonical_gate": report["canonical_gate"],
    "findings": findings_txt,
    "artifacts": {f"artifacts/worker-091/w047_f2a_freeze_independent/{k}": v["sha256"]
                  for k, v in hashes.items()},
    "manifest": {"path": "artifacts/worker-091/w047_f2a_freeze_independent/MANIFEST.json",
                 "sha256": manifest_sha},
    "events_emitted": appended,
    "events_skipped_already_present": skipped,
    "falsifier": report["falsifier"],
    "next_falsifier": report["next_falsifier"],
}
ckpt_path = STATE / "worker-091_W047-F2A-EXT-FREEZE_checkpoint.json"
ckpt_path.write_text(json.dumps(checkpoint, indent=1, ensure_ascii=False) + "\n")

print(json.dumps({"appended": appended, "skipped": skipped,
                  "checkpoint": str(ckpt_path),
                  "checkpoint_sha256": sha(ckpt_path),
                  "manifest_sha256": manifest_sha,
                  "outbox_events_total": len(OUTBOX.read_text().splitlines())},
                 indent=1, ensure_ascii=False))
