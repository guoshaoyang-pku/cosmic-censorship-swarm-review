#!/usr/bin/env python3
"""Emit W006-R03-CAND-HEADTOHEAD-01 events + checkpoint (idempotent, schema-validated).

Appends upward events to comms/outbox/worker-006.jsonl, writes run_record.json and
CHECKPOINT.json (+ runtime/state copy). Does not touch any canonical path.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms" / "outbox" / "worker-006.jsonl"
STATE = ROOT / "runtime" / "state"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def main() -> int:
    report = json.loads((HERE / "report.json").read_text())
    if report["measurement"] != "VALID":
        print("refusing to emit: measurement is not VALID")
        return 2
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    eid = lambda slug: f"w006-{stamp}-h2h-{slug}"  # noqa: E731

    evidence = ["preregistration.json", "fixture_manifest.json", "make_fixtures.py",
                "run_headtohead.py", "report.json", "raw_verdicts.json",
                "blindspot_report.json", "posthoc_stageA.json", "SUBMISSION.md"]
    hashes = {f: sha(HERE / f) for f in evidence}
    ref = lambda f: f"artifacts/worker-06/r03headtohead/{f}#{hashes[f][:12]}"  # noqa: E731

    art_specs = [
        ("preregistration.json", "preregistration",
         "rules, pins, corpus hash, expectations, decision rule and falsifier fixed before any corpus fixture was scored"),
        ("fixture_manifest.json", "corpus_manifest",
         "13 fresh fixtures (5 pos / 6 neg / 2 edge probes) with per-fixture sha256, declared target paths, mutation and rationale; manifest df62d30056602ca1"),
        ("make_fixtures.py", "generator",
         "deterministic single-target surgery on the live rev29 canonicals; parsed deep diff asserted to equal the declared targets"),
        ("run_headtohead.py", "runner",
         "fail-closed runner (pin/fixture drift, format-dominated corpus, non-R03 parity gates); exit 0 VALID / 3 INVALID"),
        ("report.json", "measurement_report",
         "out-of-sample results: frozen FP 3 / FN 3; R03-v2 FP 0 / FN 0 / edge over-reject 2; worker-004 FP 0 / FN 3 / edge 0; measurement VALID"),
        ("raw_verdicts.json", "raw_verdicts",
         "raw auditor JSON per variant x fixture and per variant x 31 canonical gate negatives"),
        ("blindspot_report.json", "blindspot_report",
         "per-fixture {candidate, expected, verdict, deviation, rule_or_blindspot, minimal_repro, rationale}"),
        ("posthoc_stageA.json", "posthoc_observation",
         "POST-HOC: m13/m18/m31 (frozen R03-only rejects) still fail stage A on R12/R06/R22; union pipeline keeps the catch"),
        ("SUBMISSION.md", "submission",
         "method, validity gates, result table, findings, falsifier outcome, honest limits, file map"),
    ]
    events = []
    for fname, atype, summary in art_specs:
        events.append({
            "event_id": eid(fname.replace(".", "-")), "event_type": "artifact",
            "created_at": now(), "actor": "worker-006", "node_id": "A1", "gate": "G-CLASSBIND",
            "class_ids": CLASS_IDS,
            "artifact_type": atype, "path": f"artifacts/worker-06/r03headtohead/{fname}",
            "sha256": hashes[fname], "validation_status": "unverified", "summary": summary,
            "evidence_refs": ["artifacts/worker-06/r03headtohead/preregistration.json#"
                              + hashes["preregistration.json"][:12],
                              "artifacts/formulation/FROZEN.json#815e08079aef"],
            "falsifier": "any pinned or fixture byte drift during the run; frozen control check failure; a non-R03 failure on any corpus fixture; recorded raw JSON not reproducible from the recorded commands",
            "not_claimed": "no gate verdict, no node completion, no theorem, no physics result",
        })
    events.append({
        "event_id": eid("claim"), "event_type": "claim", "created_at": now(), "actor": "worker-006",
        "node_id": "A1", "gate": "G-CLASSBIND", "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": CLASS_IDS, "conclusion_type": "formal_model",
        "assumptions": [
            "the live FROZEN rev29 pins (WCC d9cebb9404b2 / C2 e9a27996dfd3 / C0 b2ab6acb2bbe, spec 40f9bb9e657b) are the binding bytes; re-measured before and after",
            "the corpus was generated after both candidate repairs were published and reuses no fixture from either author's calibration set",
            "spec-legitimacy labels for pos03/pos04 and the two edge probes follow R03's text 'formal is a single sentence using those binders'",
            "stage B is a worker-side auditor, not the gate; this is a stage-B measurement with a post-hoc stage-A check on three files only",
        ],
        "statement": "Out-of-sample binder-corpus measurement at FROZEN rev29 (13 fixtures: 5 pos / 6 neg / 2 edge probes; manifest df62d30056602ca1; preregistration 6742b51478cc; measurement VALID, zero pin/fixture drift). Frozen R03 (c79d8ab8440a) shows 3 false positives (canonical WCC; '(M', g', iota)'; expanded coordinated binder) and 3 false negatives (substring-only 'G' in 'G_r'; ids in a non-binding trailing clause; ids moved into the body after 'letting'). R03-v2 (e41a4b23a840, binder-head co-binding span=80) has 0 primary FP and 0 primary FN on the same corpus, at the cost of its two pre-declared over-rejects (comma-coordinated binder; ~120-char span in one head); it accepts the three live canonicals 3/3. The worker-004 component-wise patch (645eb16a0060) also has 0 primary FP, accepts the three live canonicals 3/3 and accepts both edge probes, but misses the three binding-scope negatives (other-clause-only, body-not-binder, empty tuple '()'). On the 31 canonical gate negatives both candidates drop the same 11 frozen-R03 rejections; 8 stay rejected by other stage-B rules and 3 become stage-B accepts (m13/m18/m31), which post-hoc stage A still rejects (R12/R06/R22), so the union pipeline keeps those catches. Adoption is the owner's decision; no candidate is recommended here.",
        "falsifier": "Run both candidates against a future canonical revision or a different held-out binder corpus: a primary FP or primary FN for a candidate falsifies that candidate's row; a pin or fixture byte drift, a frozen control failure, a non-R03 failure on any corpus fixture, or non-reproducible raw JSON falsifies the whole measurement.",
        "evidence_refs": [ref("report.json"), ref("raw_verdicts.json"), ref("fixture_manifest.json"),
                          ref("preregistration.json"), ref("posthoc_stageA.json"),
                          "artifacts/worker-06/spec_conformance_audit.py#c79d8ab8440a",
                          "artifacts/worker-06/r03v2/audit_r03v2.py#e41a4b23a840",
                          "artifacts/worker-004/f1_r03_repair/patched/spec_conformance_audit.py#645eb16a0060"],
        "artifact_refs": [ref("report.json"), ref("raw_verdicts.json")],
        "not_claimed": "no gate verdict, no node completion, no theorem, no physics result, no adoption recommendation",
    })
    events.append({
        "event_id": eid("status"), "event_type": "status", "created_at": now(), "actor": "worker-006",
        "node_id": "A1", "gate": "G-CLASSBIND", "class_ids": CLASS_IDS, "status": "active", "hours": 0.5,
        "summary": "W006-R03-CAND-HEADTOHEAD-01 complete at worker level: one bounded class-bound task, measurement VALID. R03-v2 0 FP / 0 FN / 2 declared edge over-rejects; worker-004 patch 0 FP / 3 FN / 0 edge; frozen 3 FP / 3 FN, all on the live rev29 bytes. Three gate negatives whose only frozen stage-B rejection was the R03 FP remain rejected by stage A (post-hoc). Worker exits for recycling; adoption is the owner's decision.",
        "evidence_refs": [ref("report.json"), ref("SUBMISSION.md"), ref("posthoc_stageA.json")],
        "next_falsifier": "a future canonical revision or a different held-out binder corpus on which either candidate shows a primary FP or FN; or the owner adopting a repair and re-running the canonical H5 control condition on a held-out corpus",
        "not_claimed": "no gate verdict, no node completion, no theorem, no physics result",
    })
    events.append({
        "event_id": eid("gateproposal"), "event_type": "gate", "created_at": now(), "actor": "worker-006",
        "gate_id": "G-CLASSBIND", "scope": "stage-B R03 repair adoption (AF-WCC-VAC-GEN; AF-SCC-C2-VAC-GEN; AF-SCC-C0-VAC-GEN)",
        "verdict": "pending",
        "criteria": "PROPOSAL ONLY, set by no worker: owner adjudicates between R03-v2 (0 FP / 0 FN / 2 declared edge over-rejects) and the worker-004 component-wise patch (0 FP / 3 FN / 0 edge) using report.json; the pre-registered falsifier row for the chosen candidate travels with the decision",
        "evidence_refs": [ref("report.json"), ref("blindspot_report.json")],
        "not_claimed": "not a gate verdict",
    })

    for e in events:
        validate_event(e)
    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                try:
                    existing.add(json.loads(line)["event_id"])
                except Exception:
                    pass
    new = [e for e in events if e["event_id"] not in existing]
    with OUTBOX.open("a") as fh:
        for e in new:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")

    run_record = {
        "task_id": "W006-R03-CAND-HEADTOHEAD-01",
        "emitted_at": now(),
        "measurement": report["measurement"],
        "event_ids": [e["event_id"] for e in events],
        "artifact_sha256": hashes,
        "pins": report["pins_post"],
        "corpus_manifest_sha256": hashes["fixture_manifest.json"],
        "preregistration_sha256": hashes["preregistration.json"],
        "next_falsifier": "a future canonical revision or a different held-out binder corpus producing a primary FP or FN for either candidate",
        "not_claimed": "no gate verdict, no node completion, no theorem, no physics result",
    }
    (HERE / "run_record.json").write_text(json.dumps(run_record, indent=1) + "\n")
    checkpoint = {
        "worker": "worker-006", "task_id": run_record["task_id"], "node_id": "A1",
        "gate": "G-CLASSBIND", "class_ids": CLASS_IDS, "status": "complete_at_worker_level",
        "created_at": now(), "measurement": report["measurement"],
        "headline": {"frozen": "FP 3 / FN 3", "cand_r03v2": "FP 0 / FN 0 / edge over-reject 2",
                     "cand_004": "FP 0 / FN 3 / edge over-reject 0"},
        "artifact_sha256": {**hashes, "run_record.json": sha(HERE / "run_record.json")},
        "event_ids": run_record["event_ids"],
        "outbox": "comms/outbox/worker-006.jsonl",
        "next_falsifier": run_record["next_falsifier"],
        "authority_note": "worker evidence only; this checkpoint sets no node status, no gate verdict and no validation_status=passed",
    }
    (HERE / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=1) + "\n")
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / "worker-006_r03headtohead_checkpoint.json").write_text(json.dumps(checkpoint, indent=1) + "\n")
    print(json.dumps({"emitted_events": len(new), "skipped_existing": len(events) - len(new),
                      "event_ids": run_record["event_ids"],
                      "checkpoint": str(STATE / "worker-006_r03headtohead_checkpoint.json")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
