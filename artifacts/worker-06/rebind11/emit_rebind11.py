#!/usr/bin/env python3
"""FORM-PROBE-11-REBIND-REV29 checkpoint + comms emitter (worker-006).

Writes the worker-local checkpoint (runtime/state/w006_checkpoint_10.json + append to
w006_checkpoints.jsonl) and appends the upward artifact/status events to
comms/outbox/worker-006.jsonl in APPEND mode (line count verified before/after).
Shared controller state (current_checkpoint.json / artifact_hashes.json) is deliberately
not touched: the live controller lifecycle owns it.
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
INSTANCE = "worker-006-20260912T005246-968807"
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def main() -> int:
    rep = json.loads((HERE / "report.json").read_text())
    ana = json.loads((HERE / "rebind_analysis.json").read_text())
    pre = json.loads((HERE / "preregistration.json").read_text())
    man = json.loads((HERE / "manifest.json").read_text())

    arts = ["preregistration.json", "manifest.json", "manifest.sha256", "report.json",
            "raw_verdicts.json", "per_surface.json", "blindspot_report.json",
            "rebind_analysis.json", "SUBMISSION.md", "make_rebind11.py", "run_rebind11.py",
            "analyze_rebind.py", "emit_rebind11.py"]
    art_hashes = {f"artifacts/worker-06/rebind11/{a}": {"sha256": sha(HERE / a),
                                                        "bytes": (HERE / a).stat().st_size}
                  for a in arts if (HERE / a).exists()}

    ckpt = {
        "checkpoint": 10, "at": now(), "worker": "worker-006", "slot": "006",
        "instance_id": INSTANCE, "hours_spent_estimate": 0.5,
        "assignment": ("one class-bound task, continuation of the class-binding probe lane "
                       "(no assignment event claimed): FORM-PROBE-11-REBIND-REV29, node A1, gate "
                       "G-CLASSBIND, classes " + ";".join(CLASSES)),
        "task_id": "FORM-PROBE-11-REBIND-REV29",
        "status": {
            "delivered": True, "validation_status": "unverified",
            "corpus_validity": rep["corpus_validity"],
            "manifest_sha256_before_run": rep["manifest_sha256_before_run"],
            "frozen_revision": 29,
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
            "falsifier_outcome": ana["falsifier_outcome"],
            "verdicts_identical_to_probe11": ana["verdicts_identical"],
            "declared_target_collisions": ana["declared_target_collisions"],
            "rev29_changed_leaves_inside_probed_surfaces": ana["rev29_changed_leaves_inside_probed_surfaces"],
            "gate_tooling_unchanged": ana["gate_tooling_unchanged"],
            "moving_target_drift": rep["moving_target_drift"],
            "fixture_byte_drift": rep["fixture_byte_drift"],
            "lineage": rep["lineage"],
            "deviations": [
                "rebind, not byte-identical rerun: same declared deltas, rev29 bases",
                "stage B' = documented single-delta calibrated auditor (hashes unchanged from FORM-PROBE-11)",
            ],
            "no_completion_claim": "worker cannot set done/passed/gate verdict; no theorem, no physics result",
        },
        "artifacts": art_hashes,
        "events_emitted": [],
        "dry_run": "pending",
        "checkpoint_policy": ("worker-local; shared current_checkpoint.json / artifact_hashes.json are "
                              "written by the live controller lifecycle and a worker-side run would race it"),
        "next_falsifier": rep["falsifier"],
    }

    ts = now()
    tag = "w006-20260912T" + datetime.now(CST).strftime("%H%M") + "-form-probe11-rebind-rev29"
    base_refs = [
        f"artifacts/worker-06/rebind11/manifest.json#sha256:{sha(HERE / 'manifest.json')}",
        f"artifacts/formulation/FROZEN.json#sha256:{sha(ROOT / 'artifacts/formulation/FROZEN.json')}",
        f"artifacts/formulation/tools/check_class_schema.py#sha256:{sha(ROOT / 'artifacts/formulation/tools/check_class_schema.py')}",
    ]
    FALS = rep["falsifier"]
    NOTC = rep["not_claimed"]
    events = []

    def art_event(eid, path, atype, summary, refs=None):
        events.append({"event_id": eid, "event_type": "artifact", "created_at": ts, "actor": "worker-006",
                       "node_id": "A1", "gate": "G-CLASSBIND", "class_ids": CLASSES,
                       "artifact_type": atype, "path": path, "sha256": sha(HERE / Path(path).name),
                       "validation_status": "unverified", "summary": summary,
                       "evidence_refs": (refs or base_refs), "falsifier": FALS, "not_claimed": NOTC})

    art_event(f"{tag}-prereg", "artifacts/worker-06/rebind11/preregistration.json",
              "pre_registration",
              f"manifest {rep['manifest_sha256_before_run'][:12]} hashed before any stage run; 22 declared "
              f"FORM-PROBE-11 deltas rebound to FROZEN rev29 bases; single-leaf assertion passed for all 22")
    art_event(f"{tag}-manifest", "artifacts/worker-06/rebind11/manifest.json",
              "pre_registered_corpus",
              "31 fixtures (22 mutants / 7 families / 9 controls) on FROZEN rev29; bases "
              "d9cebb9404b2 / e9a27996dfd3 / b2ab6acb2bbe")
    art_event(f"{tag}-report", "artifacts/worker-06/rebind11/report.json",
              "measurement_report",
              f"union escape {rep['aggregates']['union_escape']['escape_rate']} (22/22) at FROZEN rev29; "
              f"structural and calibrated semantic escape 1.0; corpus VALID, no pin or fixture drift")
    art_event(f"{tag}-analysis", "artifacts/worker-06/rebind11/rebind_analysis.json",
              "cross_revision_analysis",
              "0 per-fixture verdict diffs vs FORM-PROBE-11; 0 collisions between the 22 declared target "
              "leaves and the rev29 changed leaves; rev29 repair wrote a new note into the unscanned S3 "
              "surface revision_history[10].notes[0]")
    art_event(f"{tag}-blindspot", "artifacts/worker-06/rebind11/blindspot_report.json",
              "blindspot_report",
              "22 per-fixture entries at rev29 {caught, rule_or_blindspot, minimal_repro, falsifier}; "
              "S1 8/8, S2 10/10, S3 4/4 escape; frozen stage B's 7 flags are the unchanged R03 false positive")
    art_event(f"{tag}-per-surface", "artifacts/worker-06/rebind11/per_surface.json",
              "per_surface_table",
              "per-fixture injected text, surface class, load-bearing tier, all four stage verdicts, minimal repro")
    art_event(f"{tag}-submission", "artifacts/worker-06/rebind11/SUBMISSION.md",
              "write_up", "method, controls, rev28->rev29 delta map, falsifier outcome, not-claimed")
    events.append({
        "event_id": f"{tag}-status", "event_type": "status", "created_at": ts, "actor": "worker-006",
        "node_id": "A1", "gate": "G-CLASSBIND", "class_ids": CLASSES, "status": "active",
        "hours": 0.5,
        "summary": ("FORM-PROBE-11-REBIND-REV29, one class-bound task: the standing falsifier of FORM-PROBE-11 "
                    "executed at FROZEN rev29 after the rev12->rev13 evidence-binding repair changed all three "
                    "canonical schema hashes. Corpus VALID (manifest b83e62ade291 hashed before any run, zero "
                    "drift); union escape 22/22 = 1.0000 (S1 8/8, S2 10/10, S3 4/4; high-load 7/7; 7 families); "
                    "controls 6/6 pass, 3/3 sensitivity caught. Per-fixture verdicts identical to FORM-PROBE-11 "
                    "(0 diffs) and the rev29 delta touched 0 declared target leaves; gate/rule tool hashes "
                    "unchanged. Falsifier NOT triggered: rev29 does not catch these fixtures. No gate verdict "
                    "claimed."),
        "evidence_refs": [f"artifacts/worker-06/rebind11/rebind_analysis.json#sha256:{sha(HERE/'rebind_analysis.json')}",
                          f"artifacts/worker-06/rebind11/report.json#sha256:{sha(HERE/'report.json')}",
                          f"artifacts/worker-06/rebind11/manifest.json#sha256:{sha(HERE/'manifest.json')}",
                          "artifacts/worker-06/exempt11/report.json#sha256:a6a2a8c8aee3135d118d335e7b84860f7d6946a83bb05c9592780c155a3febc6",
                          f"artifacts/formulation/FROZEN.json#sha256:{sha(ROOT/'artifacts/formulation/FROZEN.json')}"],
        "next_falsifier": rep["falsifier"],
    })

    (STATE / "w006_checkpoint_10.json").write_text(json.dumps(ckpt, indent=1, ensure_ascii=False) + "\n",
                                                   encoding="utf-8")
    with open(STATE / "w006_checkpoints.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps({**ckpt, "artifacts": art_hashes}, ensure_ascii=False) + "\n")

    before = OUTBOX.read_text(encoding="utf-8").count("\n") if OUTBOX.exists() else 0
    with open(OUTBOX, "a", encoding="utf-8") as fh:
        for e in events:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    after = OUTBOX.read_text(encoding="utf-8").count("\n")
    assert after == before + len(events), f"outbox append mismatch {before}->{after}"
    ckpt["events_emitted"] = [e["event_id"] for e in events]
    (STATE / "w006_checkpoint_10.json").write_text(json.dumps(ckpt, indent=1, ensure_ascii=False) + "\n",
                                                   encoding="utf-8")
    print(json.dumps({"checkpoint": str(STATE / "w006_checkpoint_10.json"),
                      "outbox_lines_before": before, "outbox_lines_after": after,
                      "events": ckpt["events_emitted"],
                      "checkpoint_sha256": sha(STATE / "w006_checkpoint_10.json")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
