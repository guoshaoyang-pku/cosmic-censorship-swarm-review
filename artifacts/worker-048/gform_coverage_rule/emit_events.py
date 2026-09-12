#!/usr/bin/env python3
"""Emit the W48-GFORM-COVERAGE-RULE-CHARACTERIZATION-01 worker events.

Validates every event with research_map.schemas.validate_event before writing:
  - artifacts/worker-048/gform_coverage_rule/emitted_events.json
  - comms/outbox/worker-048.jsonl                    (idempotent append)
  - runtime/state/w048_gform_coverage_rule_checkpoint.json
  - runtime/state/w048_checkpoints.jsonl             (append)

Worker authority only: no status=done, no validation_status=passed, no gate
verdict, no canonical write.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TASK = "W48-GFORM-COVERAGE-RULE-CHARACTERIZATION-01"
NODE = "F1/F2a/F2b"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
GATE = "G-FORM"
PIN = "957c61e3eb0e5002a19f2959bff91d845e906ab90f2dc91c0b665aca0ede6a83"
OUTBOX = ROOT / "comms" / "outbox" / "worker-048.jsonl"
CHECKPOINT = ROOT / "runtime" / "state" / "w048_gform_coverage_rule_checkpoint.json"
CHECKPOINT_LOG = ROOT / "runtime" / "state" / "w048_checkpoints.jsonl"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(rel: str) -> str:
    return f"{rel}#{sha(ROOT / rel)[:12]}"


DELIVERABLES = [
    ("tool", "artifacts/worker-048/gform_coverage_rule/characterize_review_coverage.py"),
    ("input_snapshot", "artifacts/worker-048/gform_coverage_rule/snapshot/astra_lifecycle.957c61e3eb0e.py"),
    ("proposed_patch", "artifacts/worker-048/gform_coverage_rule/proposed/astra_lifecycle.957c61e3eb0e.patched.py"),
    ("patch_diff", "artifacts/worker-048/gform_coverage_rule/proposed_patch.diff"),
    ("fixture_manifest", "artifacts/worker-048/gform_coverage_rule/fixtures/expectations.json"),
    ("corpus_manifest", "artifacts/worker-048/gform_coverage_rule/live_snapshot/manifest.json"),
    ("input_drift_manifest", "artifacts/worker-048/gform_coverage_rule/inputs_manifest.json"),
    ("audit_report", "artifacts/worker-048/gform_coverage_rule/report.json"),
    ("audit_report_replicate", "artifacts/worker-048/gform_coverage_rule/report_run2.json"),
    ("readme", "artifacts/worker-048/gform_coverage_rule/README.md"),
    ("event_emitter", "artifacts/worker-048/gform_coverage_rule/emit_events.py"),
]


def dir_digest(files) -> tuple:
    man = {}
    h = hashlib.sha256()
    for p in sorted(files, key=lambda x: x.name):
        b = p.read_bytes()
        man[p.name] = {"sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}
        h.update(p.name.encode() + b"\0" + hashlib.sha256(b).hexdigest().encode() + b"\n")
    return h.hexdigest(), man


def build_events(now: str, report: dict, replicate_ok: bool, inputs_manifest: dict) -> list:
    evs = []

    def add(e):
        e.setdefault("task_id", TASK)
        validate_event(e)
        evs.append(e)

    add({
        "event_id": "w48-covrule-status-start",
        "event_type": "status",
        "created_at": now,
        "actor": "worker-048",
        "node_id": NODE,
        "class_ids": CLASS_IDS,
        "class_id": "AF-WCC-VAC-GEN",
        "gate": GATE,
        "status": "active",
        "hours": 0.1,
        "summary": ("Took ONE bounded class-bound task (no inbox card exists for worker-048): "
                    "W48-GFORM-COVERAGE-RULE-CHARACTERIZATION-01 = characterize the controller's "
                    "astra_lifecycle.review_coverage binding rule at pinned bytes, measure what it drops "
                    "on the live review corpus for F1/F2a/F2b, and emit an unapplied patch. Read-only wrt "
                    "canonical paths; writes only artifacts/worker-048/gform_coverage_rule/."),
        "evidence_refs": [ref("artifacts/worker-048/gform_coverage_rule/report.json"),
                          ref("artifacts/worker-048/gform_coverage_rule/proposed_patch.diff")],
        "next_falsifier": report["falsifier"],
    })

    for typ, rel in DELIVERABLES:
        add({
            "event_id": f"w48-covrule-artifact-{Path(rel).name.replace('.', '_')}",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-048",
            "node_id": NODE,
            "class_ids": CLASS_IDS,
            "class_id": "AF-WCC-VAC-GEN",
            "gate": GATE,
            "artifact_type": typ,
            "path": rel,
            "sha256": sha(ROOT / rel),
            "validation_status": "unverified",
            "note": "worker-level artifact; validation_status is not promotable by a worker",
            "evidence_refs": [ref("artifacts/worker-048/gform_coverage_rule/report.json")],
        })

    ev = report["rules"]
    r1 = ev["R1_pinned"]["counts"]
    r3 = ev["R3_proposed"]["counts"]
    recovered = {t: [x["file"] for x in ev["recovered_by_R3"][t]] for t in ("F1", "F2a", "F2b")}
    add({
        "event_id": "w48-covrule-claim",
        "event_type": "claim",
        "created_at": now,
        "actor": "worker-048",
        "node_id": NODE,
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "conclusion_type": "formal_model",
        "statement": (
            f"At the pinned instrument research_map/astra_lifecycle.py#{PIN[:12]} and the byte-frozen reviews/ corpus "
            f"{report['live_corpus']['frozen_digest'][:16]} ({report['live_corpus']['files']} files), the controller "
            "coverage scan counts a full accept only when a target string normalises to a node id AND an explicit pin "
            f"string matches the measured sha256 prefix; it therefore reports F1 {r1['F1']['full_accepts']} / F2a "
            f"{r1['F2a']['full_accepts']} / F2b {r1['F2b']['full_accepts']} full accepts while two further live full "
            f"accepts are invisible to it (F1 {recovered['F1']}, F2a {recovered['F2a']}), each binding the live schema "
            "sha256 through a path#hash target or an artifact_sha256 pin. The live instrument "
            f"({report['instrument']['live_sha256_at_start'][:12]}) carries byte-identical coverage functions, so the "
            "same rule and the same blind spots hold at live bytes. Measured blind-spot census over the frozen corpus: "
            f"{report['live_corpus']['census']['target_forms'].get('path#hash', 0)} path#hash + "
            f"{report['live_corpus']['census']['target_forms'].get('node#hash', 0)} node#hash + "
            f"{report['live_corpus']['census']['target_forms'].get('node@hash', 0)} node@hash targets, "
            f"{report['live_corpus']['census']['target_forms'].get('multi', 0)} multi-targets, "
            f"{report['live_corpus']['census']['target_forms'].get('class_id', 0)} class_id-only targets, "
            f"{report['live_corpus']['census']['pin_forms'].get('dict', 0)} dict-valued reviewed_sha256, and "
            f"{report['live_corpus']['census']['full_flag'].get('None', 0)} verdict files whose "
            "counts_as_full_schema_verdict is null and therefore treated as full. The proposed UNAPPLIED patch "
            f"(proposed_patch.diff) recovers the two accepts and reports F1 {r3['F1']['full_accepts']} / F2a "
            f"{r3['F2a']['full_accepts']} / F2b {r3['F2b']['full_accepts']} with no lost accept and no false positive; "
            "11/11 controls pass and two runs over the identical frozen corpus are byte-identical."),
        "assumptions": [
            "the pinned snapshot equals a real pass-07 controller state (hash 957c61e3eb0e) and the live coverage functions are byte-identical to it (measured)",
            "the frozen corpus bytes are the decision-relevant corpus for this measurement; the digest is recorded in live_snapshot/manifest.json",
            "review_coverage is an advisory controller scan; binding-coverage adjudication remains the audit lead's (its own docstring)",
            "counts_as_full_schema_verdict null->full is the pinned code behaviour, not an endorsed policy (W48-CR2-02 stays open)",
            "the proposed patch is a proposal only and has not been applied to any canonical file",
        ],
        "falsifier": report["falsifier"],
        "evidence_refs": [
            ref("artifacts/worker-048/gform_coverage_rule/report.json"),
            ref("artifacts/worker-048/gform_coverage_rule/report_run2.json"),
            ref("artifacts/worker-048/gform_coverage_rule/live_snapshot/manifest.json"),
            ref("artifacts/worker-048/gform_coverage_rule/fixtures/expectations.json"),
            ref("artifacts/worker-048/gform_coverage_rule/proposed_patch.diff"),
            ref("research_map/astra_lifecycle.py"),
            "schemas/af_wcc_vacuum.yaml#" + report["hashes_used"]["F1"][:12],
            "schemas/af_scc_c2_vacuum.yaml#" + report["hashes_used"]["F2a"][:12],
            "schemas/af_scc_c0_vacuum.yaml#" + report["hashes_used"]["F2b"][:12],
        ],
        "artifact_refs": [ref(rel) for _, rel in DELIVERABLES],
    })

    hard = [
        {"id": "W48-CR2-01", "check": "target/pin normalization",
         "claim": ("_targets_in_review drops path#hash and bare-path targets and _explicit_pins drops dict-valued "
                   "reviewed_sha256, so two live full accepts binding the live schema bytes are not counted by the "
                   "controller scan (R1 F1 4 vs R3 5; F2a 2 vs 3)")},
        {"id": "W48-CR2-03", "check": "decision-instant stability",
         "claim": ("coverage is computed from live bytes and gate reasons carry no corpus digest; F2b moved 0 -> 2 -> 3 "
                   "full accepts within ~10 minutes and the live corpus changed between freezes of this task")},
    ]
    add({
        "event_id": "w48-covrule-review",
        "event_type": "review",
        "created_at": now,
        "actor": "worker-048",
        "reviewer": "worker-048",
        "node_id": NODE,
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "target_id": f"research_map/astra_lifecycle.py#{PIN}",
        "reviewed_sha256": PIN,
        "review_kind": "instrument coverage-rule characterization; not a schema semantic review",
        "counts_as_full_schema_verdict": False,
        "counts_as_independent_verdict": True,
        "verdict": "revise",
        "score": 3.5,
        "hard_failures": hard,
        "findings": list(report["findings"]) + [
            {"id": "W48-CR2-RECOVERED", "severity": "info",
             "finding": f"R3 recovers {recovered['F1']} and {recovered['F2a']} with no lost accept (control C5)"},
            {"id": "W48-CR2-CONTROLS", "severity": "info",
             "finding": f"{sum(1 for c in report['controls'] if c['pass'])}/{len(report['controls'])} controls pass; "
                        f"replicate byte-identical={replicate_ok}; core_sha256={report['core_sha256'][:16]}"},
        ],
        "reviewer_independence": ("worker-048 authored no astra_lifecycle.py code, no schema, and no review file in the "
                                  "frozen corpus; the instrument was written for this task and the patch is unapplied"),
        "next_falsifier": report["falsifier"],
        "evidence_refs": [ref("artifacts/worker-048/gform_coverage_rule/report.json"),
                          ref("artifacts/worker-048/gform_coverage_rule/proposed_patch.diff"),
                          ref("research_map/astra_lifecycle.py")],
    })

    add({
        "event_id": "w48-covrule-status-complete",
        "event_type": "status",
        "created_at": now,
        "actor": "worker-048",
        "node_id": NODE,
        "class_ids": CLASS_IDS,
        "class_id": "AF-WCC-VAC-GEN",
        "gate": GATE,
        "status": "active",
        "hours": 0.4,
        "summary": ("W48-GFORM-COVERAGE-RULE-CHARACTERIZATION-01 complete at worker level: 11 hash-pinned "
                    "deliverables; R1 F1/F2a/F2b = 4/2/3 vs R3 = 5/3/3; two live full accepts invisible to the pinned "
                    "scan recovered with no false positive; live instrument coverage functions byte-identical to the "
                    "analysed pin; 11/11 controls; two runs byte-identical; patch emitted UNAPPLIED. Not a gate "
                    "verdict, no node transition, no canonical write. Checkpoint "
                    "runtime/state/w048_gform_coverage_rule_checkpoint.json."),
        "evidence_refs": [ref("artifacts/worker-048/gform_coverage_rule/report.json"),
                          ref("artifacts/worker-048/gform_coverage_rule/report_run2.json"),
                          ref("artifacts/worker-048/gform_coverage_rule/proposed_patch.diff"),
                          ref("artifacts/worker-048/gform_coverage_rule/inputs_manifest.json")],
        "next_falsifier": report["falsifier"],
    })
    return evs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", default="2026-09-12T01:24:00+0800")
    args = ap.parse_args()

    report = json.loads((HERE / "report.json").read_text())
    report2 = json.loads((HERE / "report_run2.json").read_text())
    replicate_ok = (report["core_sha256"] == report2["core_sha256"]
                    and (HERE / "report.json").read_bytes() == (HERE / "report_run2.json").read_bytes())

    # input drift manifest (start values from the run; end values re-measured now)
    end = {}
    for rel in report["inputs_manifest"]:
        p = ROOT / rel
        end[rel] = {"sha256": sha(p), "bytes": p.stat().st_size}
    live_reviews_digest, _ = dir_digest(sorted((ROOT / "reviews").glob("*.json")))
    inputs_manifest = {
        "task_id": TASK,
        "at": args.now,
        "start": report["inputs_manifest"],
        "end": end,
        "drift_detected": any(report["inputs_manifest"][k] != end[k] for k in end),
        "frozen_corpus": {"digest": report["live_corpus"]["frozen_digest"],
                          "files": report["live_corpus"]["files"]},
        "live_reviews_digest_at_emit": live_reviews_digest,
        "live_reviews_moved_since_freeze": live_reviews_digest != report["live_corpus"]["frozen_digest"],
        "note": "start values are as measured by characterize_review_coverage.py; end values re-measured at emit time",
    }
    (HERE / "inputs_manifest.json").write_text(json.dumps(inputs_manifest, indent=1, sort_keys=True) + "\n")

    events = build_events(args.now, report, replicate_ok, inputs_manifest)
    (HERE / "emitted_events.json").write_text(json.dumps(events, indent=1) + "\n")

    # idempotent outbox append
    existing = set()
    if OUTBOX.is_file():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                continue
    appended = 0
    with OUTBOX.open("a") as f:
        for e in events:
            if e["event_id"] in existing:
                continue
            f.write(json.dumps(e) + "\n")
            appended += 1
    present_ids = set()
    for line in OUTBOX.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            present_ids.add(json.loads(line).get("event_id"))
        except Exception:
            continue
    present_total = sum(1 for e in events if e["event_id"] in present_ids)

    checkpoint = {
        "task_id": TASK,
        "worker": "worker-048",
        "at": args.now,
        "checkpoint": 6,
        "gate": GATE,
        "node_id": NODE,
        "class_ids": CLASS_IDS,
        "instrument_pin": {"research_map/astra_lifecycle.py": PIN},
        "frozen_corpus": {"digest": report["live_corpus"]["frozen_digest"],
                          "files": report["live_corpus"]["files"]},
        "core_sha256": report["core_sha256"],
        "replicate_byte_identical": replicate_ok,
        "controls_verdict": f"PASS_{sum(1 for c in report['controls'] if c['pass'])}_OF_{len(report['controls'])}",
        "R1_full_accepts": {t: report["rules"]["R1_pinned"]["counts"][t]["full_accepts"]
                            for t in ("F1", "F2a", "F2b")},
        "R3_full_accepts": {t: report["rules"]["R3_proposed"]["counts"][t]["full_accepts"]
                            for t in ("F1", "F2a", "F2b")},
        "artifact_hashes": {rel: sha(ROOT / rel) for _, rel in DELIVERABLES},
        "events_emitted": [e["event_id"] for e in events],
        "appended_to_outbox": appended,
        "outbox_events_present": present_total,
        "findings": report["findings"],
        "next_falsifier": report["falsifier"],
        "authority": ("no gate verdict, no node transition, no validation_status=passed, no canonical write, "
                      "no patch adoption; workers cannot promote"),
    }
    CHECKPOINT.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
    with CHECKPOINT_LOG.open("a") as f:
        f.write(json.dumps({"at": args.now, "task_id": TASK, "worker": "worker-048",
                            "checkpoint": 6, "core_sha256": report["core_sha256"],
                            "path": str(CHECKPOINT.relative_to(ROOT))}) + "\n")

    print(json.dumps({
        "events": len(events), "validated": True, "appended": appended,
        "outbox": str(OUTBOX), "checkpoint": str(CHECKPOINT),
        "replicate_byte_identical": replicate_ok,
        "live_reviews_moved_since_freeze": inputs_manifest["live_reviews_moved_since_freeze"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
