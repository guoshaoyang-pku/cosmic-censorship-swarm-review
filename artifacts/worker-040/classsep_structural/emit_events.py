#!/usr/bin/env python3
"""Emit worker-040 events for W040-A1-CLASSSEP-STRUCTURAL-01 to comms/outbox/worker-040.jsonl.

Append-only, idempotent (skips event_ids already present), and fail-closed on any artifact
hash mismatch. Does not ingest, apply, or edit any shared artifact beyond the worker's own
outbox line stream.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTBOX = ROOT / "comms/outbox/worker-040.jsonl"
BASE = Path("artifacts/worker-040/classsep_structural")
AT = "2026-09-12T01:19:10+08:00"
TASK = "W040-A1-CLASSSEP-STRUCTURAL-01"
NODE = "A1"
GATE = "G-AUDIT"
CLASS_IDS = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
CLASS_ID = ";".join(CLASS_IDS)


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


ARTIFACTS = {
    "prereg": (str(BASE / "PRE_REGISTRATION.json"), "preregistered rule, endpoints and pins"),
    "arm": (str(BASE / "structural_class_separation.py"), "clause-scope structural classifier STRUCTURAL_R3 (also the adopted arm bytes)"),
    "runner": (str(BASE / "run_battery.py"), "deterministic evaluation harness with six controls"),
    "results": (str(BASE / "results.json"), "full endpoint table for all arms and the primary arm"),
    "results_r1": (str(BASE / "results.R1.json"), "pre-registered primary arm R1 endpoint (failed, reported for disclosure)"),
    "controls": (str(BASE / "controls.json"), "C1..C6 control records"),
    "amendments": (str(BASE / "AMENDMENTS.json"), "full rule-revision history R1 -> R3 with named motivations"),
    "report": (str(BASE / "report.json"), "machine report: method, result, interpretation, falsifier, non-claims"),
    "readme": (str(BASE / "README.md"), "human summary and reproduction command"),
    "entry_hashes": (str(BASE / "entry_hashes.json"), "hashes of all worker-owned artifacts"),
    "pin_r1": (str(BASE / "pinned/structural_class_separation.R1.frozen.py"), "frozen pre-registered primary arm bytes"),
    "pin_r3": (str(BASE / "pinned/structural_class_separation.R3.frozen.py"), "frozen final arm bytes"),
    "emitter": (str(BASE / "emit_events.py"), "idempotent outbox emitter for this worker task"),
}
CHECKPOINT = "runtime/state/w040_classsep_structural_checkpoint.json"


def event(eid: str, etype: str, **kw) -> dict:
    e = {"event_id": eid, "event_type": etype, "created_at": AT, "actor": "worker-040",
         "node_id": NODE, "gate": GATE, "class_id": CLASS_ID, "class_ids": CLASS_IDS,
         "task_id": TASK}
    e.update(kw)
    return e


def build() -> list:
    evs = []
    pins = {k: sha(p) for k, (p, _) in ARTIFACTS.items()}
    ckpt_hash = sha(CHECKPOINT)
    ckpt_ref = f"{CHECKPOINT}#sha256:{ckpt_hash[:12]}"
    evs.append(event(
        "w040-csstruct-20260912T0119-status-open", "status", status="active", hours=0.05,
        summary=("No assignment card exists in comms/inbox/worker-040.jsonl. One class-bound task "
                 "self-selected from the audit lead's direction_update audit-l07-direction-separability-20260912T010517 "
                 "('the next attempt must use a structure/topology cue (clause or dependency structure), not another "
                 "lexical window'): pre-registered clause-scope structural cue, scored on the frozen union corpora "
                 "against the audit lead's adoption bar. Read-only on every shared artifact."),
        evidence_refs=[f"{ARTIFACTS['prereg'][0]}#sha256:{pins['prereg'][:12]}",
                       "comms/outbox/astra-lead-audit.jsonl#audit-l07-direction-separability-20260912T010517",
                       "reviews/CLASSSEP-calibration-adjudication.json#sha256:7714ffd5b467"],
        next_falsifier="corpus A not PASS, corpus C sensitivity < 5/6 or specificity < 9/10, a HIGH cue-induced FN, or a control failure"))
    for key, (path, summary) in ARTIFACTS.items():
        evs.append(event(
            f"w040-csstruct-20260912T0119-artifact-{key}", "artifact", artifact_type=key,
            path=path, sha256=pins[key], validation_status="unverified",
            summary=summary, evidence_refs=[f"{path}#sha256:{pins[key][:12]}"],
            non_claims=["not a gate verdict", "no canonical/proposed artifact edited"]))
    evs.append(event(
        "w040-csstruct-20260912T0119-review-applied-detector", "review",
        target_id="research_map/class_separation.py#sha256:a8c04fc31e4a",
        reviewer="worker-040", verdict="revise", score=2.0,
        reviewed_sha256="a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd",
        reviewer_role="bounded execution worker, independent of the canonical detector and of the r3 adjudication author",
        hard_failures=["HF-W040-CSSTRUCT-1: at pinned hash a8c04fc31e4a the APPLIED arm does not meet the audit-lead adoption bar on the frozen union corpora (corpus C sensitivity 4/6, specificity 3/10; 1 HIGH cue-induced FN), independently reproduced by this harness against the published r3 numbers."],
        findings=[
            "Harness reproduction: APPLIED corpus A PASS, corpus C 4/6-3/10, cue-FN HIGH 1; PRE 4/6-1/10-0; PROSEFIX 4/6-10/10-10 -- identical to reviews/CLASSSEP-calibration-adjudication.json#7714ffd5b467, so the revise is a reproduction, not a new defect.",
            "A clause-scope structural cue (STRUCTURAL_R3) meets the same bar on the same frozen bytes (corpus A 17/0/10/0; corpus C 5/6, 10/10; 0 HIGH cue-FN; worker-098 6/6+4/4; holdout 9/9+14/14; 0 hard findings on live snapshot f344ed2aaea5). This is a worker probe, not an adoption candidate, and its corpora were visible during rule authoring.",
        ],
        evidence_refs=[f"{ARTIFACTS['results'][0]}#sha256:{pins['results'][:12]}",
                       f"{ARTIFACTS['amendments'][0]}#sha256:{pins['amendments'][:12]}",
                       "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json#sha256:f344ed2aaea5",
                       "reviews/CLASSSEP-calibration-adjudication.json#sha256:7714ffd5b467"],
        non_claims=["not a gate verdict; does not set validation_status",
                    "does not overrule or replace the r3 adjudication decision (c) or the pending astra-life06-classsep-detector-adjudication",
                    "scope is the pinned hash only; the canonical path is a moving target"]))
    evs.append(event(
        "w040-csstruct-20260912T0119-claim", "claim", conclusion_type="formal_model",
        statement=("At the pinned frozen corpora (worker-07 27 fixtures d69ad58468be; audit 16-fixture assertion/mention set "
                   "8f2efd262f97; worker-049 v1 9eb2ea9e2743 and v2 db6dff9f4eda; worker-098 probes ffabb753313f; worker-035 "
                   "23-control battery ef881c3a), the clause-scope structural cue STRUCTURAL_R3 "
                   "(artifacts/worker-040/classsep_structural/structural_class_separation.py, sha256 feeb475de6f9) meets the "
                   "audit lead's adoption bar that the four lexical-window arms did not: corpus A PASS 17/0/10/0; corpus C "
                   "sensitivity 5/6 (single FN A5, no composite token in the isolated fixture) and specificity 10/10; 0 "
                   "HIGH-confidence cue-induced FN on both worker-049 adversarial sets (0/22 cleared); worker-098 6/6 FN fire "
                   "and 4/4 FP clean; holdout battery 9/9 positive and 14/14 negative. On the frozen live map snapshot "
                   "f344ed2aaea5 it reports 0 hard findings where the canonical APPLIED arm reports 19, all labeled "
                   "metalinguistic false positives, and 0 labeled-FP claims still firing. All six controls pass, including "
                   "harness reproduction of the published lexical-arm numbers. The pre-registered primary arm R1 failed "
                   "(corpus A 13/4/8/2, 4 HIGH cue-FN); R2/R3 are disclosed post-hoc revisions and A9 is holdout-derived, so "
                   "this is a fitting result on the frozen labeled corpora, not a held-out generalization result and not an adoption."),
        assumptions=[
            "the frozen corpora labels are ground truth as authored by their independent authors",
            "clause segmentation without a full parser is an approximation of structure; residual segmentation errors are disclosed in AMENDMENTS.json",
            "the audit lead's adoption bar (corpus A PASS, sens >=5/6, spec >=9/10, 0 HIGH cue-FN, 0 live metalinguistic) is the correct endpoint",
        ],
        falsifier=[
            "re-run at the pinned hashes does not reproduce results.json",
            "a freshly authored held-out corpus, not visible to worker-040, shows sensitivity < 5/6, specificity < 9/10, or a HIGH cue-induced FN",
            "a genuine first-order C0/C2 merge assertion among the claims this arm leaves silent on frozen snapshot f344ed2aaea5",
            "any pinned input hash drift, a harness failure to reproduce the published reference numbers, or a canonical file modified by the run",
        ],
        evidence_refs=[f"{ARTIFACTS['results'][0]}#sha256:{pins['results'][:12]}",
                       f"{ARTIFACTS['report'][0]}#sha256:{pins['report'][:12]}",
                       f"{ARTIFACTS['controls'][0]}#sha256:{pins['controls'][:12]}",
                       f"{ARTIFACTS['amendments'][0]}#sha256:{pins['amendments'][:12]}",
                       f"{ARTIFACTS['prereg'][0]}#sha256:{pins['prereg'][:12]}",
                       ckpt_ref],
        artifact_refs=[f"{ARTIFACTS['arm'][0]}#sha256:{pins['arm'][:12]}",
                       f"{ARTIFACTS['runner'][0]}#sha256:{pins['runner'][:12]}",
                       f"{ARTIFACTS['results'][0]}#sha256:{pins['results'][:12]}",
                       f"{ARTIFACTS['prereg'][0]}#sha256:{pins['prereg'][:12]}",
                       f"{ARTIFACTS['pin_r1'][0]}#sha256:{pins['pin_r1'][:12]}"],
        non_claims=["not a gate verdict; G-AUDIT stays pending",
                    "not an adoption; no canonical or proposed detector edited",
                    "not an independent generalization result",
                    "does not adjudicate the r3 CLASSSEP decision or supersede any pending assignment"]))
    evs.append(event(
        "w040-csstruct-20260912T0119-status-close", "status", status="active", hours=0.3,
        summary=("CHECKPOINT + EXIT. W040-A1-CLASSSEP-STRUCTURAL-01 complete from the worker side: artifacts on disk and "
                 "hash-pinned, results.json R3 meets the adoption bar on the frozen corpora, R1 primary endpoint and all "
                 "amendments disclosed, controls C1..C6 pass, no shared artifact edited, outbox emitted. Worker checkpoint "
                 f"{ckpt_ref}. Controller ingest/apply owns promotion; worker exits."),
        evidence_refs=[ckpt_ref,
                       f"{ARTIFACTS['results'][0]}#sha256:{pins['results'][:12]}",
                       f"{ARTIFACTS['report'][0]}#sha256:{pins['report'][:12]}",
                       f"{ARTIFACTS['controls'][0]}#sha256:{pins['controls'][:12]}"],
        next_falsifier=("Re-run run_battery.py at the pinned hashes; then score the structural cue on a fresh held-out corpus "
                        "authored independently of worker-040 before any staged candidate is considered."),
        completion_scope="worker lifecycle only; not a node done / gate verdict",
        non_claims=["not a gate verdict", "does not edit or adopt any canonical/proposed artifact",
                    "worker cannot set node status, validation_status=passed, or a gate verdict"]))
    return evs


def main() -> int:
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
    evs = build()
    added = 0
    with OUTBOX.open("a") as f:
        for e in evs:
            if e["event_id"] in existing:
                continue
            f.write(json.dumps(e, sort_keys=True) + "\n")
            added += 1
    # validate every line parses
    bad = 0
    for line in OUTBOX.read_text().splitlines():
        if not line.strip():
            continue
        try:
            json.loads(line)
        except Exception:
            bad += 1
    print(json.dumps({"events_total": len(evs), "events_added": added, "bad_lines": bad,
                      "outbox": str(OUTBOX)}))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
