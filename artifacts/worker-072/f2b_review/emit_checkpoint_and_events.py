#!/usr/bin/env python3
"""Write the W072-F2B-REVIEW-REV29-01 checkpoint and emit the outbox events.

Worker authority: emits status/artifact/review only. It never sets status=done,
validation_status=passed, or a gate verdict.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
HERE = ROOT / "artifacts/worker-072/f2b_review"
VERDICT = ROOT / "reviews/F2b-review-worker-072-rev29.json"
CHECKPOINT = ROOT / "runtime/state/w072_f2b_review_checkpoint_1.json"
OUTBOX = ROOT / "comms/outbox/worker-072.jsonl"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def now() -> str:
    return subprocess.run(["date", "-Is"], capture_output=True, text=True).stdout.strip()


def main():
    target = ROOT / "schemas/af_scc_c0_vacuum.yaml"
    frozen = ROOT / "artifacts/formulation/FROZEN.json"
    verdict = json.loads(VERDICT.read_text())
    report = json.loads((HERE / "report.json").read_text())
    controls = json.loads((HERE / "controls/controls_summary.json").read_text())
    regs = {n: json.loads((HERE / "classsep_pins" / f"regression.{n}.json").read_text())
            for n in ("c266dbecaa87", "e2d24b927ee8", "e36b0d644ca7")}
    ts = now()
    tsk = "W072-F2B-REVIEW-REV29-01"
    falsifier = verdict["falsifier"]
    TARGET_PIN = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
    if sha(target) != TARGET_PIN:
        print(f"ABORT: target moved during review window: {sha(target)} != {TARGET_PIN}; emitting nothing", file=sys.stderr)
        return 3

    checkpoint = {
        "checkpoint_id": "w072-f2b-review-ckpt-1",
        "task_id": tsk, "worker": "worker-072", "created_at": ts,
        "class_id": "AF-SCC-C0-VAC-GEN", "node_id": "F2b", "gate": "G-FORM",
        "pins": {
            "schemas/af_scc_c0_vacuum.yaml": sha(target),
            "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": sha(ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
            "artifacts/formulation/FROZEN.json": sha(frozen),
            "research_map/formulation_taxonomy.yaml": sha(ROOT / "research_map/formulation_taxonomy.yaml"),
            "artifacts/formulation/evidence/taxonomy_consistency.json": sha(ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"),
            "research_map/class_separation.py": sha(ROOT / "research_map/class_separation.py"),
        },
        "deliverables": {
            "reviews/F2b-review-worker-072-rev29.json": sha(VERDICT),
            "artifacts/worker-072/f2b_review/report.json": sha(HERE / "report.json"),
            "artifacts/worker-072/f2b_review/controls/controls_summary.json": sha(HERE / "controls/controls_summary.json"),
            "artifacts/worker-072/f2b_review/MANIFEST.json": sha(HERE / "MANIFEST.json"),
            "artifacts/worker-072/f2b_review/check_f2b.py": sha(HERE / "check_f2b.py"),
            "artifacts/worker-072/f2b_review/detector_drift_witness.json": sha(HERE / "detector_drift_witness.json"),
        },
        "checks": {
            "instrument_checks_pass": report["n_pass"], "instrument_checks_fail": report["n_fail"],
            "canonical_gate": report["canonical_gate"]["verdict"],
            "controls_mutants_discriminated": sum(1 for r in controls["controls"] if r["instrument_discriminates"]),
            "controls_mutants_total": len(controls["controls"]),
            "null_control_clean": controls["null_control_clean"],
            "hash_stable_before_after": verdict["hash_stable_before_after"],
            "classsep_pinned_regression": {k: f"{v['leaks_detected']} leaks, {v['controls_clean']} controls, {v['verdict']}" for k, v in regs.items()},
        },
        "findings": [{"id": f["id"], "severity": f["severity"], "blocking": f.get("blocking", False)} for f in verdict["findings"]],
        "verdict": {"verdict": verdict["verdict"], "score": verdict["score"], "path": "reviews/F2b-review-worker-072-rev29.json", "sha256": sha(VERDICT)},
        "falsifier": falsifier,
        "authority_note": "Worker checkpoint. No node status, validation_status=passed or gate verdict is set here.",
    }
    CHECKPOINT.write_text(json.dumps(checkpoint, indent=2) + "\n")

    vsha, msha, rsha, csha, ksha = sha(VERDICT), sha(HERE / "MANIFEST.json"), sha(HERE / "report.json"), sha(HERE / "controls/controls_summary.json"), sha(CHECKPOINT)
    findings_short = [f"{f['id']} {f['severity']}: {f['finding'][:180]}" for f in verdict["findings"]]
    base = {"created_at": ts, "actor": "worker-072", "task_id": tsk, "node_id": "F2b", "node_ids": ["F2b"],
            "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": ["AF-SCC-C0-VAC-GEN"], "gate": "G-FORM"}
    events = [
        dict(base, event_id=f"w072-{ts}-artifact-verdict", event_type="artifact", artifact_type="review_verdict",
             path="reviews/F2b-review-worker-072-rev29.json", sha256=vsha, validation_status="unverified",
             summary="Independent blind non-author F2b (AF-SCC-C0-VAC-GEN) review verdict: accept 4.0 at "
                     "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe, FROZEN rev29 815e08079aefbc; hard_failures empty; 5 recorded "
                     "findings, all non-blocking at G-FORM. Hash measured before and after; 33/33 independent checks.",
             evidence_refs=[f"schemas/af_scc_c0_vacuum.yaml#{sha(target)[:12]}",
                            f"artifacts/formulation/FROZEN.json#{sha(frozen)[:12]}",
                            f"artifacts/worker-072/f2b_review/report.json#{rsha[:12]}"], falsifier=falsifier),
        dict(base, event_id=f"w072-{ts}-artifact-instrument", event_type="artifact", artifact_type="review_evidence",
             path="artifacts/worker-072/f2b_review/report.json", sha256=rsha, validation_status="unverified",
             summary="Independent review instrument + 33 checks + canonical-gate cross-run; 8 controls (7 mutants discriminated, "
                     "1 clean perturbation passes). Two gate blind spots measured (binding hash chain; foreign class-id token).",
             evidence_refs=[f"artifacts/worker-072/f2b_review/check_f2b.py#{sha(HERE / 'check_f2b.py')[:12]}",
                            f"artifacts/worker-072/f2b_review/report.json#{rsha[:12]}"], falsifier=falsifier),
        dict(base, event_id=f"w072-{ts}-artifact-controls", event_type="artifact", artifact_type="control_matrix",
             path="artifacts/worker-072/f2b_review/controls/controls_summary.json", sha256=csha, validation_status="unverified",
             summary="Control matrix: m1..m7 discriminated by the instrument, m8 null perturbation clean; canonical gate agrees on "
                     "class-semantics mutants and misses the binding-hash and foreign-class-token mutants.",
             evidence_refs=[f"artifacts/worker-072/f2b_review/controls/controls_summary.json#{csha[:12]}"], falsifier=falsifier),
        dict(base, event_id=f"w072-{ts}-artifact-manifest", event_type="artifact", artifact_type="manifest",
             path="artifacts/worker-072/f2b_review/MANIFEST.json", sha256=msha, validation_status="unverified",
             summary="sha256 of every deliverable: instrument, runner, report, controls, pinned detector variants, regression "
                     "outputs, FROZEN/rev29 pins, verdict.",
             evidence_refs=[f"artifacts/worker-072/f2b_review/MANIFEST.json#{msha[:12]}"], falsifier="Any listed file hashing differently from its MANIFEST entry."),
        dict(base, event_id=f"w072-{ts}-artifact-checkpoint", event_type="artifact", artifact_type="checkpoint",
             path="runtime/state/w072_f2b_review_checkpoint_1.json", sha256=ksha, validation_status="unverified",
             summary="Bounded-task checkpoint: task, target/f0/detector pins, deliverables, check counts, findings, verdict hash, falsifier.",
             evidence_refs=[f"runtime/state/w072_f2b_review_checkpoint_1.json#{ksha[:12]}"], falsifier=falsifier),
        dict(base, event_id=f"w072-{ts}-review-f2b", event_type="review", target_id="F2b", reviewer="worker-072",
             verdict="accept", score=4.0, hard_failures=[], findings=findings_short,
             reviewed_sha256=sha(target), reviewed_path="schemas/af_scc_c0_vacuum.yaml",
             reviewed_frozen_sha256=sha(frozen), blind=True,
             evidence_refs=[f"reviews/F2b-review-worker-072-rev29.json#{vsha[:12]}",
                            f"schemas/af_scc_c0_vacuum.yaml#{sha(target)[:12]}",
                            f"artifacts/formulation/FROZEN.json#{sha(frozen)[:12]}",
                            f"artifacts/worker-072/f2b_review/report.json#{rsha[:12]}"], falsifier=falsifier),
        dict(base, event_id=f"w072-{ts}-status-checkpoint", event_type="status", status="active", hours=0.5,
             summary="Checkpoint w072-f2b-review-ckpt-1: W072-F2B-REVIEW-REV29-01 complete at worker level (completion claim for the "
                     "bounded deliverable only; not a node transition and not a gate verdict). Independent non-author F2b review at "
                     "b2ab6acb2bbe/FROZEN 815e08079aefbc: accept 4.0, no hard failures, 5 advisory findings; instrument 33/33 with "
                     "7/7 mutant discrimination and a clean null; canonical gate pass; pinned classsep regression 17/17+10/10 at "
                     "c266dbecaa87, e2d24b927ee8, e36b0d644ca7 (corpus-limited, advisory). Detector drift observation with witness "
                     "artifacts/worker-072/f2b_review/detector_drift_witness.json: live class_separation.py c266dbecaa87 (frozen pin) "
                     "-> a8c04fc31e4a (00:52, pass-06/CF-26) -> e36b0d644ca7 (01:06:12, my measured bytes) -> a8c04fc31e4a again "
                     "(01:08:14); no artifact event names the canonical path at the moved hashes; no adoption, adjudication-owned. "
                     "Bounded execution worker exiting for recycling.",
             evidence_refs=[f"reviews/F2b-review-worker-072-rev29.json#{vsha[:12]}",
                            f"runtime/state/w072_f2b_review_checkpoint_1.json#{ksha[:12]}",
                            f"artifacts/worker-072/f2b_review/controls/controls_summary.json#{csha[:12]}"],
             next_falsifier=falsifier, claims_completion=False),
    ]
    for e in events:
        validate_event(e)
    with open(OUTBOX, "a") as fh:
        for e in events:
            fh.write(json.dumps(e) + "\n")
    print(json.dumps({"checkpoint": str(CHECKPOINT.relative_to(ROOT)), "checkpoint_sha256": ksha,
                      "verdict_sha256": vsha, "events_appended": len(events), "outbox": str(OUTBOX.relative_to(ROOT))}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
