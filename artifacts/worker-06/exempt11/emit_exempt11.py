#!/usr/bin/env python3
"""FORM-PROBE-11 checkpoint + comms emitter (worker-06).

Writes the worker-local checkpoint (runtime/state/w006_checkpoint_9.json + append to
w006_checkpoints.jsonl) and appends the upward artifact/status events to
comms/outbox/worker-006.jsonl in APPEND mode (line count verified before/after).
The shared controller checkpoint/artifact_hashes are deliberately not touched: the live
controller lifecycle owns them and a worker-side run would race it.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
STATE = ROOT / "runtime/state"
OUTBOX = ROOT / "comms/outbox/worker-006.jsonl"
CST = timezone(timedelta(hours=8))
INSTANCE = "worker-006-20260912T004258-968807"
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def main():
    rep = json.loads((HERE / "report.json").read_text())
    summ = json.loads((HERE / "verdict_summary.json").read_text())
    r32 = json.loads((HERE / "r32_calibration.json").read_text())
    inv = json.loads((HERE / "surface_inventory.json").read_text())
    man = json.loads((HERE / "manifest.json").read_text())

    arts = ["manifest.json", "manifest.sha256", "report.json", "raw_verdicts.json",
            "per_surface.json", "blindspot_report.json", "surface_inventory.json",
            "r32_calibration.json", "verdict_summary.json", "SUBMISSION.md",
            "make_exempt11.py", "run_exempt11.py", "propose_r32.py",
            "calibrate_exempt11.py", "audit_calibrated_exempt11.py", "consolidate.py",
            "emit_exempt11.py"]
    art_hashes = {f"artifacts/worker-06/exempt11/{a}": {"sha256": sha(HERE / a),
                                                       "bytes": (HERE / a).stat().st_size}
                  for a in arts if (HERE / a).exists()}

    ckpt = {
        "checkpoint": 9, "at": now(), "worker": "worker-006", "slot": "006",
        "instance_id": INSTANCE,
        "hours_spent_estimate": 1.0,
        "assignment": ("one class-bound task, continuation of the class-binding probe lane "
                       "(no assignment event claimed): FORM-PROBE-11 / EXEMPT-SURFACE-11, node A1, "
                       "gate G-CLASSBIND, classes " + ";".join(CLASSES)),
        "task_id": "FORM-PROBE-11",
        "status": {
            "delivered": True,
            "validation_status": "unverified",
            "corpus_validity": rep["corpus_validity"],
            "manifest_sha256_before_run": rep["manifest_sha256_before_run"],
            "frozen_revision": 28,
            "aggregates": {
                "candidate_mutants": 22,
                "union_escape_rate": rep["aggregates"]["union_escape"]["escape_rate"],
                "structural_escape_rate": rep["aggregates"]["structural_escape"]["escape_rate"],
                "semantic_calibrated_escape_rate": rep["aggregates"]["semantic_escape_primary"]["escape_rate"],
                "escape_by_surface": {k: v["escape_rate"] for k, v in rep["aggregates"]["by_surface"].items()},
                "escape_by_load_bearing": {k: v["escape_rate"] for k, v in rep["aggregates"]["by_load_bearing"].items()},
                "escaped_families": rep["escape_families"],
            },
            "controls": {"pass_controls_ok": rep["calibration"]["all_pass_controls_ok"],
                         "sensitivity_controls_ok": rep["calibration"]["all_sensitivity_ok"],
                         "canonical": rep["calibration"]["pass_controls"],
                         "negative_field": rep["calibration"]["negative_field_controls"],
                         "sensitivity": rep["calibration"]["sensitivity_controls"]},
            "frozen_stage_B_caveat": summ["headline"]["frozen_stage_B_caveat"],
            "surface_inventory_leaf_counts": {c: d["by_class_counts"] for c, d in inv["schemas"].items()},
            "r32_calibration": {m: {k: r32["modes"][m][k] for k in ("fp_count", "catches_on_mutants", "misses_on_mutants")}
                                for m in ("R32-fam", "R32-fam-pol", "R32-narrow")},
            "lineage": summ["lineage"],
            "deviations": [
                "stage B' = documented single-delta calibrated auditor (pre-registered, source+delta hashes pinned)",
                "R32 modes are PROPOSALS ONLY; the canonical gate was not edited and no rule was merged",
            ],
            "no_completion_claim": "worker cannot set done/passed/gate verdict; no theorem, no physics result",
        },
        "artifacts": art_hashes,
        "events_emitted": [],
        "dry_run": "pending",
        "checkpoint_policy": ("worker-local; shared current_checkpoint.json / artifact_hashes.json are "
                              "written by the live controller lifecycle and a worker-side run would race it"),
        "next_falsifier": ("a pass control rejected at the pinned hashes, a pinned hash change, a fixture byte "
                           "drift, or a later revision whose gate catches these fixtures (re-run the frozen "
                           "corpus, never this one)"),
    }

    # ---------------- comms events ----------------
    ts = now()
    tag = "w006-20260912T" + datetime.now(CST).strftime("%H%M") + "-form-probe11"
    base_refs = [
        f"artifacts/worker-06/exempt11/manifest.json#sha256:{sha(HERE / 'manifest.json')}",
        f"artifacts/formulation/FROZEN.json#sha256:{sha(ROOT / 'artifacts/formulation/FROZEN.json')}",
        f"artifacts/formulation/tools/check_class_schema.py#sha256:{sha(ROOT / 'artifacts/formulation/tools/check_class_schema.py')}",
    ]
    FALS = rep["falsifier"]
    NOTC = rep["not_claimed"]
    events = []

    def art_event(eid, path, atype, summary, refs=None, extra=None):
        e = {"event_id": eid, "event_type": "artifact", "created_at": ts, "actor": "worker-006",
             "node_id": "A1", "gate": "G-CLASSBIND", "class_ids": CLASSES,
             "artifact_type": atype, "path": path, "sha256": sha(HERE / Path(path).name),
             "validation_status": "unverified", "summary": summary,
             "evidence_refs": (refs or base_refs), "falsifier": FALS, "not_claimed": NOTC}
        if extra:
            e.update(extra)
        events.append(e)

    art_event(f"{tag}-manifest", "artifacts/worker-06/exempt11/manifest.json",
              "pre_registered_corpus",
              f"31 fixtures (22 mutants / 7 families / 9 controls) on FROZEN rev28; manifest sha256 {sha(HERE/'manifest.json')[:12]} hashed before any stage run")
    art_event(f"{tag}-report", "artifacts/worker-06/exempt11/report.json",
              "measurement_report",
              f"union escape {rep['aggregates']['union_escape']['escape_rate']} (22/22); structural {rep['aggregates']['structural_escape']['escape_rate']}; calibrated semantic {rep['aggregates']['semantic_escape_primary']['escape_rate']}; corpus VALID, no drift")
    art_event(f"{tag}-blindspot", "artifacts/worker-06/exempt11/blindspot_report.json",
              "blindspot_report",
              "22 per-fixture entries {caught, rule_or_blindspot, minimal_repro, falsifier}; S1 8/8, S2 10/10, S3 4/4 escape")
    art_event(f"{tag}-per-surface", "artifacts/worker-06/exempt11/per_surface.json",
              "per_surface_table",
              "per-fixture injected text, surface class, load-bearing tier, stage verdicts, minimal repro")
    art_event(f"{tag}-inventory", "artifacts/worker-06/exempt11/surface_inventory.json",
              "surface_inventory",
              "mechanical leaf classification of the 3 canonical schemas: A_LEXICAL 14-18, R13_COMPOSITE 251-275, EXEMPT_KEY 59-83 string leaves per schema (~95% outside the family-token scan)")
    art_event(f"{tag}-r32", "artifacts/worker-06/exempt11/r32_calibration.json",
              "candidate_rule_calibration",
              "R32-fam FP=6/22 catches; R32-fam-pol FP=6; R32-narrow (declared load-bearing non-exempt allowlist) FP=0, catches 10/10 S2. PROPOSAL ONLY, gate not edited")
    art_event(f"{tag}-verdict", "artifacts/worker-06/exempt11/verdict_summary.json",
              "verdict_summary",
              f"consolidated: manifest {rep['manifest_sha256_before_run'][:12]}, union escape 1.0, R32-narrow FP 0; lineage FORM-EXEMPT-09 rev18 18/18 -> rev28 22/22 replication")
    art_event(f"{tag}-submission", "artifacts/worker-06/exempt11/SUBMISSION.md",
              "write_up", "method, controls, surface map, R32 calibration, falsifiers, not-claimed")
    events.append({
        "event_id": f"{tag}-status", "event_type": "status", "created_at": ts, "actor": "worker-006",
        "node_id": "A1", "gate": "G-CLASSBIND", "class_ids": CLASSES, "status": "active",
        "hours": 1.0,
        "summary": ("FORM-PROBE-11, one class-bound task: re-measurement of FORM-EXEMPT-09 at FROZEN rev28 "
                    "with a new pre-registered exempt-surface corpus. Union escape 22/22 = 1.0000 (S1 8/8, "
                    "S2 10/10, S3 4/4; high-load 7/7; 7 families), all controls green, no pin drift. Frozen "
                    "stage B's 7 flags are the R03 binder-layout false positive (0 genuine detections). "
                    "~95% of canonical string leaves lie outside the family-token scan. R32-narrow allowlist "
                    "candidate: 0 FP on canonical/negative controls, 10/10 S2 catches; broad variants rejected "
                    "at 6 FP fixtures. No gate verdict claimed; proposal only."),
        "evidence_refs": [f"artifacts/worker-06/exempt11/verdict_summary.json#sha256:{sha(HERE/'verdict_summary.json')}",
                          f"artifacts/worker-06/exempt11/report.json#sha256:{sha(HERE/'report.json')}",
                          f"artifacts/worker-06/exempt11/surface_inventory.json#sha256:{sha(HERE/'surface_inventory.json')}",
                          f"artifacts/worker-06/exempt11/r32_calibration.json#sha256:{sha(HERE/'r32_calibration.json')}",
                          "artifacts/worker-06/exempt_field_corpus/report.json#sha256:8af6bb5a3ba15864"],
        "next_falsifier": ckpt["next_falsifier"],
    })

    # write checkpoint
    (STATE / "w006_checkpoint_9.json").write_text(json.dumps(ckpt, indent=1, ensure_ascii=False) + "\n",
                                                  encoding="utf-8")
    with open(STATE / "w006_checkpoints.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps({**ckpt, "artifacts": art_hashes}, ensure_ascii=False) + "\n")

    # append events (append mode; verify no truncation)
    before = OUTBOX.read_text(encoding="utf-8").count("\n") if OUTBOX.exists() else 0
    with open(OUTBOX, "a", encoding="utf-8") as fh:
        for e in events:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    after = OUTBOX.read_text(encoding="utf-8").count("\n")
    assert after == before + len(events), f"outbox append mismatch {before}->{after}"
    ckpt["events_emitted"] = [e["event_id"] for e in events]
    (STATE / "w006_checkpoint_9.json").write_text(json.dumps(ckpt, indent=1, ensure_ascii=False) + "\n",
                                                  encoding="utf-8")
    print(json.dumps({"checkpoint": str(STATE / "w006_checkpoint_9.json"),
                      "outbox_lines_before": before, "outbox_lines_after": after,
                      "events": ckpt["events_emitted"],
                      "checkpoint_sha256": sha(STATE / "w006_checkpoint_9.json")}, indent=1))


if __name__ == "__main__":
    main()
