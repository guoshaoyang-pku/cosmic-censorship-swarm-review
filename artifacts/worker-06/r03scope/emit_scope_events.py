#!/usr/bin/env python3
"""Emit W006-R03-SCOPE-01 upward events + checkpoint (idempotent, schema-validated).

Appends events to comms/outbox/worker-006.jsonl, writes run_record.json, CHECKPOINT.json,
a runtime/state copy and raw_manifest.json. Event ids are derived from the preregistration
hash prefix, so re-running this script does not duplicate events. Writes no canonical path.
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
TASK = "W006-R03-SCOPE-01"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def main() -> int:
    report = json.loads((HERE / "report.json").read_text())
    if report["measurement"] != "VALID":
        print("refusing to emit: measurement is not VALID")
        return 2
    pre_sha = sha(HERE / "preregistration.json")
    stamp = pre_sha[:12]
    eid = lambda slug: f"w006-r03scope-{stamp}-{slug}"  # noqa: E731

    # raw/ manifest (hash-addresses the per-cell raw JSON)
    raw_files = sorted(p for p in (HERE / "raw").glob("*.json"))
    raw_manifest = {
        "task_id": TASK, "created_at": now(),
        "files": {p.name: sha(p) for p in raw_files},
        "count": len(raw_files),
        "note": "pass-1 raw auditor JSON per candidate x file; pass-2 repro files are deleted "
                "after the semantic comparison",
    }
    (HERE / "raw_manifest.json").write_text(
        json.dumps(raw_manifest, indent=1) + "\n", encoding="utf-8")

    artifact_files = [
        ("preregistration.json", "preregistration",
         "pins, candidates, declared semantics, hypotheses, corpus hash, decision rule and "
         "falsifier fixed before any fixture was scored"),
        ("fixture_manifest.json", "corpus_manifest",
         "19 fresh fixtures (1 control / 6 scored pos / 8 scored neg / 4 unscored edge probes) "
         "with per-fixture sha256, declared target leaf, mutation, declared expectations, "
         "rationale; manifest 40a457905eee"),
        ("make_fixtures.py", "generator",
         "deterministic single-target surgery on quantifiers.formal of the live canonical WCC; "
         "parsed deep diff asserted to equal exactly that leaf"),
        ("run_scope.py", "runner",
         "fail-closed runner (pin/fixture drift, format domination, non-R03 parity, canonical "
         "controls, semantic reproduction); exit 0 VALID / 3 INVALID"),
        ("report.json", "measurement_report",
         "scope-safety results: frozen FP 4 / FN 2; cand_r03v2 FP 0 / FN 0; cand_004 FP 0 / "
         "FN 7; cand_E3 FP 0 / FN 8; measurement VALID, 0 expectation deviations in 76 cells"),
        ("raw_verdicts.json", "raw_verdicts",
         "raw auditor JSON per candidate x (fixture + canonical schema)"),
        ("raw_manifest.json", "raw_manifest",
         "sha256 of every pass-1 raw auditor JSON file"),
        ("blindspot_report.json", "blindspot_report",
         "declared-expectation deviations (none), per-candidate class-contract misses with "
         "minimal repro, and declared over-reject residues"),
        ("report.run1_runnerbug_invalid.json", "posthoc_disclosure",
         "preserved run 1 voided by a runner-side variance gate; corpus, pre-registration and "
         "verdicts unchanged by the disclosed gate repair"),
        ("SUBMISSION.md", "submission",
         "method, validity gates, result table, findings, falsifier outcome, honest limits, "
         "file map"),
    ]
    hashes = {f: sha(HERE / f) for f, _, _ in artifact_files}
    ref = lambda f: f"artifacts/worker-06/r03scope/{f}#{hashes[f][:12]}"  # noqa: E731

    events = []
    for fname, atype, summary in artifact_files:
        events.append({
            "event_id": eid(fname.replace(".", "-")), "event_type": "artifact",
            "created_at": now(), "actor": "worker-006", "node_id": "A1", "gate": "G-CLASSBIND",
            "class_ids": CLASS_IDS, "artifact_type": atype,
            "path": f"artifacts/worker-06/r03scope/{fname}", "sha256": hashes[fname],
            "validation_status": "unverified", "summary": summary,
            "evidence_refs": [ref("preregistration.json"), ref("report.json"),
                              "artifacts/formulation/FROZEN.json#815e08079aef"],
            "falsifier": "any pinned or fixture byte drift; any non-R03 failure on any corpus "
                         "fixture; frozen canonical control not reproduced; non-reproducible raw "
                         "JSON; a declared expectation deviation reported as a measurement",
            "not_claimed": "no gate verdict, no node completion, no theorem, no physics result",
        })

    events.append({
        "event_id": eid("claim"), "event_type": "claim", "created_at": now(),
        "actor": "worker-006", "node_id": "A1", "gate": "G-CLASSBIND",
        "class_id": "AF-WCC-VAC-GEN", "class_ids": CLASS_IDS,
        "conclusion_type": "formal_model",
        "assumptions": [
            "the live FROZEN rev29 bytes are binding; all 10 candidate/canonical pins were "
            "re-measured before and after the run and did not move",
            "the corpus was built after all four candidates were published and reuses no "
            "fixture from the head-to-head, either author's calibration set or the heldout "
            "corpora; every mutant alters exactly quantifiers.formal",
            "the 8 scope negatives are genuine binding-scope errors under the declared binder "
            "(q,t0) semantics; the 6 positives are legitimate renderings of the same binding",
            "the 4 edge probes are interpretation-dependent and are excluded from the primary "
            "counts; expectations were declared before scoring from each tool's rule semantics",
            "this is a stage-B R03 measurement; stage A and the informative C2/C0 leak blocker "
            "are out of scope",
        ],
        "statement": "Pre-registered scope-safety measurement at FROZEN rev29 (19 fixtures: 1 "
        "control / 6 scored positives / 8 scored negatives / 4 unscored edge probes; manifest "
        "40a457905eee, preregistration f376d7124cfb, measurement VALID, zero pin or fixture "
        "drift, 0 deviations across 76 declared cells). Frozen literal R03 (c79d8ab8440a) has "
        "FP 4 / FN 2: it rejects four correct renderings that do not repeat the exact token "
        "(spaced tuple, doubled-space coordination, filler adverb, whitespace-expanded) and "
        "accepts two scope errors whose literal token appears non-bindingly (trailing clause; "
        "body `letting`). cand_004 (645eb16a0060, whole-word component presence) has FP 0 / "
        "FN 7; cand_E3 (3f69bc1eb27a, literal-or-substring) has FP 0 / FN 8. Both are "
        "position- and scope-blind: they accept after-body conjunction, after-body "
        "parenthetical, non-binding literal token, reversed order, implication-consequent "
        "binding, earlier-quantifier binding and body-`letting` binding; cand_E3 also accepts "
        "the substring-only negative. cand_r03v2 (e41a4b23a840, binder-head co-binding span=80) "
        "has FP 0 / FN 0 on the same corpus and accepts all three live canonicals: its "
        "binder-head locality already rejects every scope family here, so on this evidence the "
        "scope-aware half of the lead's option A-prime is already implemented by R03-v2 and no "
        "additional grouping requirement is needed to pass this corpus. Its two pre-declared "
        "over-rejects (comma-coordinated binder, ~140-char span) remain as unscored edge "
        "probes. Adoption of any candidate is the schema owner's decision; no candidate is "
        "recommended here.",
        "falsifier": "Run the same pre-registered corpus after any candidate or pin changes, or "
        "a later held-out scope corpus: a candidate that accepts a genuine scope error or "
        "rejects a genuine correct rendering falsifies that candidate's row. A pin or fixture "
        "byte drift, a frozen canonical control failure, a non-R03 failure on any fixture, or "
        "non-reproducible raw JSON falsifies the whole measurement.",
        "evidence_refs": [ref("report.json"), ref("raw_verdicts.json"),
                          ref("fixture_manifest.json"), ref("preregistration.json"),
                          ref("blindspot_report.json"),
                          "tmp/lead-form-life08/r03_scope_probe.json#41922f0587c32c51",
                          "artifacts/worker-06/spec_conformance_audit.py#c79d8ab8440a",
                          "artifacts/worker-06/r03v2/audit_r03v2.py#e41a4b23a840",
                          "artifacts/worker-004/f1_r03_repair/patched/spec_conformance_audit.py#645eb16a0060",
                          "artifacts/worker-064/r03_cause/work/cand_E3/artifacts/worker-06/spec_conformance_audit.py#3f69bc1eb27a"],
        "artifact_refs": [ref("report.json"), ref("raw_verdicts.json"),
                          ref("preregistration.json"), ref("fixture_manifest.json")],
        "not_claimed": "no gate verdict, no node completion, no theorem, no physics result, no "
                       "adoption recommendation",
    })
    events.append({
        "event_id": eid("status"), "event_type": "status", "created_at": now(),
        "actor": "worker-006", "node_id": "A1", "gate": "G-CLASSBIND", "class_ids": CLASS_IDS,
        "status": "active", "hours": 1.0,
        "summary": "W006-R03-SCOPE-01 complete at worker level: one bounded class-bound task, "
        "measurement VALID, 0 expectation deviations in 76 declared cells. Answer to the "
        "lifecycle-08 scope question: cand_r03v2 is the only candidate that is scope-safe on "
        "this corpus (FP 0 / FN 0; accepts all 3 canonicals); cand_004 (FP 0 / FN 7) and "
        "cand_E3 (FP 0 / FN 8) are not, so the scope-error variant reproduces and generalises "
        "as a permanent negative control for them; frozen is unsafe in both directions "
        "(FP 4 / FN 2). No R03-v3 was needed on this evidence. Worker exits for recycling; "
        "adoption and any stage-2 pinning remain the owner's decision.",
        "evidence_refs": [ref("report.json"), ref("SUBMISSION.md"),
                          ref("blindspot_report.json")],
        "next_falsifier": "a later held-out scope corpus on which cand_r03v2 accepts a genuine "
                          "scope error or rejects a genuine correct rendering; or the owner "
                          "adopting cand_004/cand_E3 without a scope component and re-running "
                          "this corpus against the adopted revision",
        "not_claimed": "no gate verdict, no node completion, no theorem, no physics result",
    })
    events.append({
        "event_id": eid("gateproposal"), "event_type": "gate", "created_at": now(),
        "actor": "worker-006", "gate_id": "G-CLASSBIND",
        "scope": "stage-B R03 repair scope-safety "
                 "(AF-WCC-VAC-GEN; AF-SCC-C2-VAC-GEN; AF-SCC-C0-VAC-GEN)",
        "verdict": "pending",
        "criteria": "PROPOSAL ONLY, set by no worker: the owner's option A-prime needs a "
                    "scope-aware binder rule. Measured here: cand_r03v2 already separates 6/6 "
                    "correct renderings from 8/8 scope errors (0 primary FP/FN) while "
                    "cand_004 and cand_E3 accept 7/8 and 8/8 scope errors respectively. If "
                    "A-prime is adopted, R03-v2 is the only candidate on this corpus that does "
                    "not need an added scope component, and the two scope-error fixtures that "
                    "fool the frozen literal test (neg_literal_tuple_elsewhere, "
                    "neg_ids_in_body_letting) should travel as permanent negative controls. "
                    "The stage-2 rule engine remains unpinned in FROZEN rev29 "
                    "(lead-form-20260912T011516-123); pin it in the same revision that adopts "
                    "any R03 revision.",
        "evidence_refs": [ref("report.json"), ref("blindspot_report.json"),
                          ref("preregistration.json")],
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
        "task_id": TASK, "emitted_at": now(), "measurement": report["measurement"],
        "event_ids": [e["event_id"] for e in events],
        "artifact_sha256": {**hashes, "raw_manifest.json": sha(HERE / "raw_manifest.json")},
        "pins_post": report["pins_post"],
        "preregistration_sha256": pre_sha,
        "corpus_manifest_sha256": report["corpus_manifest_sha256"],
        "headline": report["headline"],
        "next_falsifier": "a later held-out scope corpus on which a candidate's primary FP or "
                          "FN appears; or a pin/fixture drift, frozen control failure, non-R03 "
                          "failure or non-reproducible raw JSON voiding the measurement",
        "not_claimed": "no gate verdict, no node completion, no theorem, no physics result",
    }
    (HERE / "run_record.json").write_text(json.dumps(run_record, indent=1) + "\n",
                                          encoding="utf-8")
    checkpoint = {
        "worker": "worker-006", "task_id": TASK, "node_id": "A1", "gate": "G-CLASSBIND",
        "class_ids": CLASS_IDS, "status": "complete_at_worker_level",
        "created_at": now(), "measurement": report["measurement"],
        "headline": report["headline"],
        "reading": report["reading"],
        "validity_gates": {k: v["pass"] for k, v in report["validity_gates"].items()},
        "artifact_sha256": {**hashes, "run_record.json": sha(HERE / "run_record.json")},
        "event_ids": run_record["event_ids"],
        "outbox": "comms/outbox/worker-006.jsonl",
        "next_falsifier": run_record["next_falsifier"],
        "authority_note": "worker evidence only; this checkpoint sets no node status, no gate "
                          "verdict and no validation_status=passed",
    }
    (HERE / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=1) + "\n",
                                          encoding="utf-8")
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / "worker-006_r03scope_checkpoint.json").write_text(
        json.dumps(checkpoint, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({
        "emitted_events": len(new), "skipped_existing": len(events) - len(new),
        "event_ids": run_record["event_ids"],
        "checkpoint": str(STATE / "worker-006_r03scope_checkpoint.json"),
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
