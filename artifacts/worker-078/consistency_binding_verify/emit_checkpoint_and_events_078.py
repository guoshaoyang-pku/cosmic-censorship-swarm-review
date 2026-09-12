#!/usr/bin/env python3
"""W078-F2-F0BIND-ADJ-01: checkpoint + outbox emission.

Recomputes every artifact hash from disk (no hardcoded digests), writes
runtime/state/w078_checkpoint_4_f0_consistency_binding.json, appends a line to
runtime/state/w078_checkpoints.jsonl, and appends four validated JSON events to
comms/outbox/worker-078.jsonl: status(active), artifact x4, review, status(done).
Read-only on all canonical swarm artifacts.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).isoformat(timespec="seconds")
TASK = "W078-F2-F0BIND-ADJ-01"
OUT = ROOT / "artifacts/worker-078/consistency_binding_verify"
STATE = ROOT / "runtime/state"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    report = json.loads((OUT / "report.json").read_text())
    c = report["checks"]
    arts = {
        "artifacts/worker-078/consistency_binding_verify/verify_consistency_binding_078.py": sha(OUT / "verify_consistency_binding_078.py"),
        "artifacts/worker-078/consistency_binding_verify/report.json": sha(OUT / "report.json"),
        "artifacts/worker-078/consistency_binding_verify/report_rerun.json": sha(OUT / "report_rerun.json"),
        "artifacts/worker-078/consistency_binding_verify/README.md": sha(OUT / "README.md"),
    }
    live = c["B1_live_evidence_measured"]["live"]
    b6 = c["B6_schema_and_manifest_pins"]
    b8 = c["B8_simulated_correct_regeneration"]
    evidence_refs = [
        f"schemas/af_wcc_vacuum.yaml#{b6['schemas']['F1']['sha256'][:12]}",
        f"schemas/af_scc_c2_vacuum.yaml#{b6['schemas']['F2a']['sha256'][:12]}",
        f"schemas/af_scc_c0_vacuum.yaml#{b6['schemas']['F2b']['sha256'][:12]}",
        f"artifacts/formulation/evidence/taxonomy_consistency.json#{live['sha256'][:12]}",
        f"artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json#{report['checks']['B2_declared_pin_resolves_to_pinned_copy']['declared_pin'][:12]}",
        f"artifacts/formulation/tools/check_taxonomy_consistency.py#{c['B4_isolated_tool_reproduction']['tool']['sha256'][:12]}",
        f"artifacts/formulation/FROZEN.json#{sha(ROOT / 'artifacts/formulation/FROZEN.json')[:12]}",
        f"artifacts/worker-078/consistency_binding_verify/report.json#{arts['artifacts/worker-078/consistency_binding_verify/report.json'][:12]}",
        "runtime/state/w078_checkpoint_4_f0_consistency_binding.json",
    ]

    # ---------------- checkpoint ----------------
    ckpt = {
        "worker": "worker-078",
        "checkpoint": 4,
        "at": NOW,
        "task": TASK,
        "node_id": "F2",
        "gate_scope": "G-FORM",
        "status": "complete",
        "classification": report["classification"],
        "verdict": "revise",
        "verdict_target": report["verdict_target"],
        "frozen_revision": b6["frozen_revision"],
        "pins_measured": {
            k: {"path": v["path"], "revision": v["revision"], "sha256": v["sha256"],
                "consistency_evidence_sha256": v["consistency_evidence_sha256"],
                "declared_pin_matches_live": v["declared_pin_matches_live_evidence"],
                "declared_f0_matches_live": v["declared_f0_sha256"] == b6["canonical_f0_live_sha256"]}
            for k, v in b6["schemas"].items()
        },
        "live_evidence": live,
        "declared_pin": report["checks"]["B2_declared_pin_resolves_to_pinned_copy"]["declared_pin"],
        "anchors_lost": c["B3_generation_diff"]["fields_only_in_declared_generation"],
        "shadow_reproduces_live_document": c["B4_isolated_tool_reproduction"]["shadow_reproduces_live_document"],
        "simulated_correct_regeneration_sha256": b8["simulated_document_sha256"],
        "simulated_equals_declared_pin": b8["simulated_equals_declared_pin"],
        "correct_repair_requires_new_evidence_bytes": b8["correct_repair_requires_new_evidence_bytes"],
        "drift_during_run": c["B7_drift_window"]["drifted"],
        "writer_active_during_run": c["B7_drift_window"]["writer_active_during_window"],
        "artifacts": arts,
        "evidence_refs": evidence_refs,
        "next_falsifier": report["falsifiers"][0],
        "numerics_lock": "respected: no numerics path touched",
        "scope_note": report["scope_note"],
        "events_emitted": [],
    }

    # ---------------- events ----------------
    def ev(eid, etype, **kw):
        return {"event_id": eid, "event_type": etype, "created_at": NOW,
                "actor": "worker-078", "node_id": "F2", "task_id": TASK, **kw}

    art_events = []
    meta = {
        "verify_consistency_binding_078.py": ("verifier_code", "Deterministic 8-check adjudication harness; isolated checker mirror; read-only on canonical paths."),
        "report.json": ("audit_report", "Primary evidence: classification LOSSY_GENERATOR_STALE_PIN; declared 675a99d0 carried the three tree/time anchors the live 9e335e9b drops."),
        "report_rerun.json": ("audit_report", "Byte-identical re-execution of the same measurement chain (deterministic fields)."),
        "README.md": ("summary", "Method, reproduction command, limits and five falsifiers."),
    }
    for name, (atype, note) in meta.items():
        rel = f"artifacts/worker-078/consistency_binding_verify/{name}"
        art_events.append(ev(
            f"w078-{NOW}-artifact-{name.replace('.', '-')}", "artifact",
            class_id="AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
            artifact_type=atype, path=rel, sha256=arts[rel], validation_status="unverified",
            gate="G-FORM", note=note, evidence_refs=evidence_refs[:6],
        ))

    status_active = ev(
        f"w078-{NOW}-status-active", "status",
        class_id="AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN", status="active", hours=0.4,
        summary=("No assignment card exists in comms/inbox for worker-078 (fleet instance 2026-09-12T00:37:14). "
                 "Took ONE bounded class-bound task: independent adjudication of the family-wide F0 consistency-evidence "
                 "binding defect at F1 cce9c60146d6 / F2a 5476a3f2c6bc / F2b 55d0a1ea9bda / FROZEN rev28. Result: the stale "
                 "675a99d0 pin is not a re-stamp slip. The declared generation carried map_taxonomy_sha256 0abb9ed8, "
                 "lead_contract_sha256 d7419b4e and measured_at; the live 9e335e9b generation drops exactly those three "
                 "fields. Simulating the repair tool's anchor re-addition on the live bytes reproduces 675a99d0 exactly, so "
                 "the declared pin was correct for the measured trees and a live-hash re-stamp would be a false closure. "
                 "The canonical checker check_taxonomy_consistency.py (FROZEN-pinned de356d99) rewrites the same path without "
                 "the anchors and reproduced the live document byte-for-byte in an isolated mirror. Verdict: revise. "
                 "Read-only on canonical paths; no gate verdict."),
        evidence_refs=evidence_refs,
        next_falsifier=report["falsifiers"][0],
        artifact="artifacts/worker-078/consistency_binding_verify/",
    )

    review = ev(
        f"w078-{NOW}-review-f0-evidence-binding", "review",
        reviewer="worker-078",
        target_id=f"artifacts/formulation/evidence/taxonomy_consistency.json#{live['sha256'][:12]}",
        target_node_id="F2", class_id="AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        gate="G-FORM", verdict="revise", score=3.0,
        reviewed_sha256=live["sha256"], reviewed_path="artifacts/formulation/evidence/taxonomy_consistency.json",
        hard_failures=[
            ("H07b-class false closure risk: the three rev12 schemas declare consistency_evidence_sha256 675a99d0, "
             "which the canonical path no longer resolves; re-stamping to the live 9e335e9b would leave the evidence "
             "unbound to the declared F0 0abb9ed8 / authoring d7419b4e trees because the live generation carries no "
             "tree hashes at all."),
        ],
        findings=[
            {"id": "W078-F0B-01", "severity": "revise",
             "finding": ("Information loss is exactly map_taxonomy_sha256, lead_contract_sha256, measured_at "
                         "(B3); no common field changed value, so the semantic payload is preserved.")},
            {"id": "W078-F0B-02", "severity": "revise",
             "finding": ("Writer attribution reproduced: FROZEN-pinned check_taxonomy_consistency.py de356d99 has no "
                         "anchor-field code and, run in an isolated mirror, emitted a document byte-identical to live "
                         "9e335e9b; the file mtime advanced 41 s during the run with content unchanged.")},
            {"id": "W078-F0B-03", "severity": "info",
             "finding": ("Repair path exists and is mechanical: close_findings_rev27.py 0234cd3c writes the three "
                         "anchors; simulating that addition on the live bytes yields exactly the declared 675a99d0. "
                         "A correct repair publishes new evidence bytes and therefore new schema bytes; it cannot be "
                         "done by editing the pointer alone.")},
            {"id": "W078-F0B-04", "severity": "info",
             "finding": ("FROZEN rev28 pins the live unbound generation 9e335e9b, so manifest and schemas currently "
                         "disagree about which evidence generation is canonical.")},
        ],
        evidence_refs=evidence_refs,
        falsifier=report["falsifiers"][0],
        scope_note=report["scope_note"],
        counts_toward_gate_accept=False,
    )

    status_done = ev(
        f"w078-{NOW}-status-done", "status",
        class_id="AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN", status="done", hours=0.5,
        summary=("W078-F2-F0BIND-ADJ-01 complete at worker level (completion claim only, not a node transition and not a "
                 "gate verdict). One class-bound task delivered: independent adjudication of the family-wide F0 "
                 "consistency-evidence binding at F1 cce9c60146d6 / F2a 5476a3f2c6bc / F2b 55d0a1ea9bda under FROZEN rev28. "
                 "Classification LOSSY_GENERATOR_STALE_PIN, verdict revise, 8/8 checks complete, 0 binding failures, "
                 "report and re-run byte-identical. Canonical artifacts untouched; numerics lock respected. Worker exits now."),
        evidence_refs=evidence_refs,
        next_falsifier=report["falsifiers"][0],
        artifact="artifacts/worker-078/consistency_binding_verify/",
        completion_scope="worker lifecycle only; not a node done / gate verdict",
    )

    events = [status_active] + art_events + [review, status_done]
    ckpt["events_emitted"] = [e["event_id"] for e in events]

    # write checkpoint + append index line
    STATE.mkdir(parents=True, exist_ok=True)
    ckpt_path = STATE / "w078_checkpoint_4_f0_consistency_binding.json"
    ckpt_path.write_text(json.dumps(ckpt, indent=1) + "\n")
    with (STATE / "w078_checkpoints.jsonl").open("a") as f:
        f.write(json.dumps({"at": NOW, "worker": "worker-078", "checkpoint": 4, "task_id": TASK,
                            "verdict": "revise", "classification": report["classification"],
                            "live_evidence_sha256": live["sha256"], "declared_pin": ckpt["declared_pin"],
                            "checkpoint_file": ckpt_path.name}) + "\n")

    # append events to outbox
    outbox = ROOT / "comms/outbox/worker-078.jsonl"
    with outbox.open("a") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")

    # validate what we just wrote parses as JSON and carries required fields
    with outbox.open() as f:
        lines = [l for l in f.read().splitlines() if l.strip()]
    tail = [json.loads(l) for l in lines[-len(events):]]
    ok = all(all(k in e for k in ("event_id", "event_type", "created_at", "actor")) for e in tail)
    print(json.dumps({"outbox_lines_total": len(lines), "events_appended": len(events),
                      "all_required_fields": ok, "checkpoint": str(ckpt_path),
                      "artifacts": arts, "event_ids": [e["event_id"] for e in events]}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
