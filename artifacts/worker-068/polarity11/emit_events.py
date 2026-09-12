#!/usr/bin/env python3
"""W068-FORM-POLARITY-11 event emitter (worker-068).

Patches checkpoint.json with the README/emitter hashes, then appends the task's
structured events to comms/outbox/worker-068.jsonl. Idempotent: event_ids already
present in the outbox are skipped. Also appends the checkpoint to
runtime/state/w068_checkpoints.jsonl and writes runtime/state/w068_polarity11_checkpoint.json.

Usage: python3 emit_events.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
OUTBOX = ROOT / "comms" / "outbox" / "worker-068.jsonl"
STATE = ROOT / "runtime" / "state"
CST = timezone(timedelta(hours=8))
TASK_ID = "W068-FORM-POLARITY-11"
CORPUS_ID = "FORM-POLARITY-11"
CLASS_IDS = ["AF-WCC-VAC-GEN"]
NODE_ID = "A1"
GATE = "G-CLASSBIND (folded into G-AUDIT as calibration evidence)"
GROUP = "formulation"
ACTOR = "worker-068"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(rel: str) -> str:
    return f"{rel}#sha256:{sha256_file(ROOT / rel)[:12]}"


def main() -> int:
    now = datetime.now(CST).isoformat(timespec="seconds")

    # 1. patch checkpoint.json with README + emitter hashes (final checkpoint bytes)
    cp = json.loads((HERE / "checkpoint.json").read_text())
    cp["artifacts"]["artifacts/worker-068/polarity11/README.md"] = {"sha256": sha256_file(HERE / "README.md")}
    cp["artifacts"]["artifacts/worker-068/polarity11/emit_events.py"] = {"sha256": sha256_file(HERE / "emit_events.py")}
    (HERE / "checkpoint.json").write_text(json.dumps(cp, indent=2, sort_keys=False) + "\n")

    report = json.loads((HERE / "report.json").read_text())
    raw = json.loads((HERE / "raw_verdicts.json").read_text())
    manifest_sha = sha256_file(HERE / "manifest.json")
    report_sha = sha256_file(HERE / "report.json")
    raw_sha = sha256_file(HERE / "raw_verdicts.json")
    cp_sha = sha256_file(HERE / "checkpoint.json")
    builder_sha = sha256_file(HERE / "build_corpus11.py")
    runner_sha = sha256_file(HERE / "run_polarity11.py")

    m = report["measurement"]
    escape_list = m["escapes"]
    caught = [(c["fixture"].split("/")[-1], c["catch_rules"]) for c in m["caught"]]

    statement = (
        "On a fully pinned shadow pipeline (stage A 000e09e46b2f, stage B c79d8ab8440a, rule spec "
        "40f9bb9e657b, KEY_MANIFEST rev27 fce91948ba3a) applied to the archived pre-rev12 WCC base "
        "9a8bd4c96800, the WCC arm of the FORM-POLARITY-10 probe corpus is INFORMATIVE (identity and "
        "4 format controls accepted by both stages; 3/3 known-rejected liveness controls rejected). "
        f"{m['escape_count']} of {m['probes_total']} WCC conclusion-polarity/content probes escape both stages "
        f"(union escape rate {m['escape_rate']:.3f}): inner-negation flip, outer negation, natural-language "
        "negation, complete(I+_D) negation and visibility conjunct inversion. Only the conclusion_type token "
        "flip is caught, by R11 at stage A. Neither stage compares conclusion.statement_formal / "
        "statement_natural_language content against the frozen WCC conclusion, so the SCC-arm blind spot "
        "measured in FORM-POLARITY-10 extends to AF-WCC-VAC-GEN. This is a measurement about the pinned "
        "detector pipeline on an archived base, not a class-truth claim and not a statement about live rev12."
    )

    events = [
        {
            "event_id": "w068-pol11-01-task-claim",
            "event_type": "status",
            "created_at": now,
            "actor": ACTOR,
            "task_id": TASK_ID,
            "node_id": NODE_ID,
            "gate": GATE,
            "group_id": GROUP,
            "class_ids": CLASS_IDS,
            "status": "active",
            "hours": 0.1,
            "summary": ("No assignment card exists in comms/inbox for worker-068 (this fleet instance). Took ONE bounded "
                        "class-bound task: W068-FORM-POLARITY-11 = measure whether the FORM-POLARITY-10 conclusion-content "
                        "blind spot extends to AF-WCC-VAC-GEN, removing the two recorded obstructions with a fully pinned "
                        "shadow pipeline. Successor to the worker-068 blocker w068-pol10-12 (WCC arm non-informative)."),
            "evidence_refs": [ref("artifacts/worker-068/polarity10/report.json")],
            "next_falsifier": report["next_falsifier"],
        },
        {
            "event_id": "w068-pol11-02-manifest",
            "event_type": "artifact",
            "created_at": now,
            "actor": ACTOR,
            "task_id": TASK_ID,
            "node_id": NODE_ID,
            "gate": GATE,
            "group_id": GROUP,
            "class_ids": CLASS_IDS,
            "artifact_type": "corpus_manifest",
            "path": "artifacts/worker-068/polarity11/manifest.json",
            "sha256": manifest_sha,
            "validation_status": "unverified",
            "summary": ("Manifest hashed before any stage run: 5 pinned shadow inputs, 14 fixtures (6 WCC polarity probes, "
                        "5 conforming controls, 3 known-rejected liveness controls) with per-fixture sha256."),
            "evidence_refs": [f"artifacts/worker-068/polarity11/manifest.json#sha256:{manifest_sha[:12]}"],
            "next_falsifier": report["falsifier"],
        },
        {
            "event_id": "w068-pol11-03-report",
            "event_type": "artifact",
            "created_at": now,
            "actor": ACTOR,
            "task_id": TASK_ID,
            "node_id": NODE_ID,
            "gate": GATE,
            "group_id": GROUP,
            "class_ids": CLASS_IDS,
            "artifact_type": "measurement_report",
            "path": "artifacts/worker-068/polarity11/report.json",
            "sha256": report_sha,
            "validation_status": "unverified",
            "summary": (f"valid={report['valid']}, informative={m['informative']}, escapes={m['escape_count']}/{m['probes_total']} "
                        f"(rate {m['escape_rate']:.3f}), conforming controls {m['conforming_controls_accepted']}/{m['conforming_controls_total']} "
                        f"accepted, liveness {m['known_rejected_controls_rejected']}/{m['known_rejected_controls_total']} rejected. "
                        f"Findings: {[f['finding_id'] for f in report['findings']]}."),
            "evidence_refs": [f"artifacts/worker-068/polarity11/report.json#sha256:{report_sha[:12]}"],
            "next_falsifier": report["next_falsifier"],
        },
        {
            "event_id": "w068-pol11-04-raw",
            "event_type": "artifact",
            "created_at": now,
            "actor": ACTOR,
            "task_id": TASK_ID,
            "node_id": NODE_ID,
            "gate": GATE,
            "group_id": GROUP,
            "class_ids": CLASS_IDS,
            "artifact_type": "raw_verdicts",
            "path": "artifacts/worker-068/polarity11/raw_verdicts.json",
            "sha256": raw_sha,
            "validation_status": "unverified",
            "summary": ("Per-fixture shadow stage-A/stage-B verdicts with failed rules, exit codes, rule-verdict maps, "
                        "pinned shadow input hashes before/after and live-context hashes before/after (no live input read)."),
            "evidence_refs": [f"artifacts/worker-068/polarity11/raw_verdicts.json#sha256:{raw_sha[:12]}"],
            "next_falsifier": report["falsifier"],
        },
        {
            "event_id": "w068-pol11-05-builder",
            "event_type": "artifact",
            "created_at": now,
            "actor": ACTOR,
            "task_id": TASK_ID,
            "node_id": NODE_ID,
            "gate": GATE,
            "group_id": GROUP,
            "class_ids": CLASS_IDS,
            "artifact_type": "harness",
            "path": "artifacts/worker-068/polarity11/build_corpus11.py",
            "sha256": builder_sha,
            "validation_status": "unverified",
            "summary": "Deterministic builder: fails closed on pinned shadow input drift, applies p1..p6 ops verbatim from FORM-POLARITY-10.",
            "evidence_refs": [f"artifacts/worker-068/polarity11/build_corpus11.py#sha256:{builder_sha[:12]}",
                              ref("artifacts/worker-068/polarity10/build_corpus.py")],
            "next_falsifier": report["falsifier"],
        },
        {
            "event_id": "w068-pol11-06-runner",
            "event_type": "artifact",
            "created_at": now,
            "actor": ACTOR,
            "task_id": TASK_ID,
            "node_id": NODE_ID,
            "gate": GATE,
            "group_id": GROUP,
            "class_ids": CLASS_IDS,
            "artifact_type": "harness",
            "path": "artifacts/worker-068/polarity11/run_polarity11.py",
            "sha256": runner_sha,
            "validation_status": "unverified",
            "summary": "Runner with shadow-pin verification, fixture-tamper detection, identity/liveness calibration and live-context drift recording.",
            "evidence_refs": [f"artifacts/worker-068/polarity11/run_polarity11.py#sha256:{runner_sha[:12]}"],
            "next_falsifier": report["falsifier"],
        },
        {
            "event_id": "w068-pol11-07-readme",
            "event_type": "artifact",
            "created_at": now,
            "actor": ACTOR,
            "task_id": TASK_ID,
            "node_id": NODE_ID,
            "gate": GATE,
            "group_id": GROUP,
            "class_ids": CLASS_IDS,
            "artifact_type": "report",
            "path": "artifacts/worker-068/polarity11/README.md",
            "sha256": sha256_file(HERE / "README.md"),
            "validation_status": "unverified",
            "summary": "README: question, pinned shadow binding table, results, findings, limitations, non-claims, falsifier, reproduction.",
            "evidence_refs": [ref("artifacts/worker-068/polarity11/README.md")],
            "next_falsifier": report["falsifier"],
        },
        {
            "event_id": "w068-pol11-08-checkpoint-artifact",
            "event_type": "artifact",
            "created_at": now,
            "actor": ACTOR,
            "task_id": TASK_ID,
            "node_id": NODE_ID,
            "gate": GATE,
            "group_id": GROUP,
            "class_ids": CLASS_IDS,
            "artifact_type": "checkpoint",
            "path": "artifacts/worker-068/polarity11/checkpoint.json",
            "sha256": cp_sha,
            "validation_status": "unverified",
            "summary": "Checkpoint: valid=true, informative=true, escapes=5/6, conforming 5/5 accepted, liveness 3/3 rejected.",
            "evidence_refs": [f"artifacts/worker-068/polarity11/checkpoint.json#sha256:{cp_sha[:12]}"],
            "next_falsifier": report["falsifier"],
        },
        {
            "event_id": "w068-pol11-09-claim",
            "event_type": "claim",
            "created_at": now,
            "actor": ACTOR,
            "task_id": TASK_ID,
            "node_id": NODE_ID,
            "gate": GATE,
            "group_id": GROUP,
            "class_id": "AF-WCC-VAC-GEN",
            "class_ids": CLASS_IDS,
            "conclusion_type": "numerical_evidence",
            "statement": statement,
            "assumptions": [
                "Escape = accepted by BOTH stages; the corpus and its labels are author-built and require independent adjudication.",
                "The WCC arm is informative because the unmutated identity control is accepted by both stages in the pinned shadow.",
                "The measurement is bound to the archived pre-rev12 base 9a8bd4c96800 under KEY_MANIFEST rev27 fce91948ba3a, because live rev12 cce9c60146d6 fails stage B R03 and the archived base fails stage A R22 under the live KEY_MANIFEST 014e2d301978.",
                "All five shadow inputs were re-hashed after the run and were unchanged; live canonical/KEY_MANIFEST hashes were measured before and after as context only.",
            ],
            "falsifier": report["falsifier"],
            "evidence_refs": [
                f"artifacts/worker-068/polarity11/report.json#sha256:{report_sha[:12]}",
                f"artifacts/worker-068/polarity11/raw_verdicts.json#sha256:{raw_sha[:12]}",
                f"artifacts/worker-068/polarity11/manifest.json#sha256:{manifest_sha[:12]}",
                f"artifacts/worker-068/polarity11/checkpoint.json#sha256:{cp_sha[:12]}",
            ],
            "artifact_refs": [
                f"artifacts/worker-068/polarity11/report.json#sha256:{report_sha[:12]}",
                f"artifacts/worker-068/polarity11/raw_verdicts.json#sha256:{raw_sha[:12]}",
            ],
            "next_falsifier": report["next_falsifier"],
        },
        {
            "event_id": "w068-pol11-10-blocker-wcc-content",
            "event_type": "blocker",
            "created_at": now,
            "actor": ACTOR,
            "task_id": TASK_ID,
            "node_id": NODE_ID,
            "gate": GATE,
            "group_id": GROUP,
            "class_ids": CLASS_IDS,
            "description": (
                "WCC-arm detector gap confirmed on the pinned shadow pipeline: 5/6 conclusion-polarity/content probes "
                "are accepted by both stages while the unmutated base is accepted (identity + 4 format controls 5/5, "
                "3/3 liveness controls rejected). Escaping ops: inner-negation flip, outer negation, NL negation, "
                "complete(I+_D) negation, visibility conjunct inversion. Only the conclusion_type token flip is caught "
                "(R11). Neither stage compares conclusion statement content against the frozen conclusion. Together with "
                "w068-pol10-10 (C2/C0) this makes the content blind spot class-general across all three class schemas."
            ),
            "needed_to_unblock": (
                "Lead-formulation / lead-audit adjudication: either add a stage-A rule (or stage-B check) that compares "
                "conclusion.statement_formal / statement_natural_language against the frozen class conclusion (negation-aware), "
                "or record the conclusion-content axis as an explicit machine-unchecked blind spot in the gate criteria. "
                "The live F1 rev12 stage-B R03 base rejection (w068-pol10-12 / worker-004 w004-semct-blocker-f1-r03) must be "
                "repaired before the arm can be re-measured on live bytes."
            ),
            "evidence_refs": [
                f"artifacts/worker-068/polarity11/report.json#sha256:{report_sha[:12]}",
                f"artifacts/worker-068/polarity11/raw_verdicts.json#sha256:{raw_sha[:12]}",
                "artifacts/worker-068/polarity10/report.json#sha256:66301211174d",
                "schemas/af_wcc_vacuum.yaml#sha256:cce9c60146d6",
            ],
            "next_falsifier": report["next_falsifier"],
        },
        {
            "event_id": "w068-pol11-11-checkpoint",
            "event_type": "status",
            "created_at": now,
            "actor": ACTOR,
            "task_id": TASK_ID,
            "node_id": NODE_ID,
            "gate": GATE,
            "group_id": GROUP,
            "class_ids": CLASS_IDS,
            "status": "active",
            "hours": 0.4,
            "summary": (
                f"CHECKPOINT (worker-068, FORM-POLARITY-11): valid=true; informative=true; 6 WCC probes / "
                f"{m['escape_count']} escapes (rate {m['escape_rate']:.3f}); conforming controls "
                f"{m['conforming_controls_accepted']}/{m['conforming_controls_total']}; liveness "
                f"{m['known_rejected_controls_rejected']}/{m['known_rejected_controls_total']}; pinned shadow inputs unchanged "
                "before/after; no live input read by the measurement."
            ),
            "evidence_refs": [
                f"artifacts/worker-068/polarity11/checkpoint.json#sha256:{cp_sha[:12]}",
                f"artifacts/worker-068/polarity11/report.json#sha256:{report_sha[:12]}",
            ],
            "next_falsifier": report["next_falsifier"],
        },
        {
            "event_id": "w068-pol11-12-complete",
            "event_type": "status",
            "created_at": now,
            "actor": ACTOR,
            "task_id": TASK_ID,
            "node_id": NODE_ID,
            "gate": GATE,
            "group_id": GROUP,
            "class_ids": CLASS_IDS,
            "status": "active",
            "hours": 0.5,
            "summary": (
                "Bounded worker lifecycle complete (W068-FORM-POLARITY-11). Artifacts and events emitted; worker exits for "
                "recycling. No node completion, validation_status=passed, or gate verdict is claimed; the content blind spot "
                "and the two pipeline obstructions are carried by w068-pol11-10-blocker-wcc-content, w068-pol10-10/11/12."
            ),
            "evidence_refs": [
                f"artifacts/worker-068/polarity11/README.md#sha256:{sha256_file(HERE / 'README.md')[:12]}",
                f"artifacts/worker-068/polarity11/report.json#sha256:{report_sha[:12]}",
            ],
            "next_falsifier": report["next_falsifier"],
        },
    ]

    existing = set()
    if OUTBOX.exists():
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
        for ev in events:
            if ev["event_id"] in existing:
                continue
            f.write(json.dumps(ev, sort_keys=True) + "\n")
            appended += 1

    # worker checkpoint mirror + log
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / "w068_polarity11_checkpoint.json").write_text(json.dumps(cp, indent=2, sort_keys=False) + "\n")
    log = {
        "at": cp["at"], "worker": ACTOR, "task_id": TASK_ID, "corpus_id": CORPUS_ID, "node_id": NODE_ID,
        "gate": GATE, "class_ids": CLASS_IDS, "checkpoint": 1, "hours_spent_estimate": 0.5,
        "status": cp["status"], "valid": cp["valid"], "measurement": cp["measurement"],
        "findings": cp["findings"], "artifacts": cp["artifacts"], "falsifier": cp["falsifier"],
        "next_falsifier": cp["next_falsifier"], "events": [e["event_id"] for e in events],
        "non_claims": cp["non_claims"],
    }
    with (STATE / "w068_checkpoints.jsonl").open("a") as f:
        f.write(json.dumps(log, sort_keys=True) + "\n")

    print(json.dumps({"appended_events": appended, "outbox": str(OUTBOX.relative_to(ROOT)),
                      "checkpoint_log": "runtime/state/w068_checkpoints.jsonl"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
