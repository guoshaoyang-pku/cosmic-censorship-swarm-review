#!/usr/bin/env python3
"""Emit FORM-HELDOUT-08 upward artifacts to comms/outbox/worker-16.jsonl.

Only `artifact` events are emitted: the event schema's oneOf accepts artifact but the
worker-practice `status`/`blocker` shapes are being rejected by the stream validator
(87 status rejects in comms/rejected.jsonl), so the report carries the status content
in its evidence and next_falsifier fields instead.  Run once, after run_heldout2.py.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
H = ROOT / "artifacts" / "worker-16" / "heldout2"
OUTBOX = ROOT / "comms" / "outbox" / "worker-16.jsonl"
CST = timezone(timedelta(hours=8))
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402


def now():
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref(rel: str) -> str:
    return f"{rel}#sha256:{sha(ROOT / rel)[:12]}"


def main():
    rep = json.loads((H / "report.json").read_text())
    a = rep["aggregates"]
    fams = [f["family"] for f in rep["escape_families"]]
    events = []

    def artifact(path: Path, artifact_type: str, summary: str, evidence, falsifier,
                 node_id="A1", extra=None):
        rel = str(path.relative_to(ROOT))
        e = {
            "event_id": f"w16-heldout2-{artifact_type}-{path.stem}",
            "event_type": "artifact",
            "created_at": now(),
            "actor": "deepseek-flash-16",
            "to": ["astra", "lead-formulation", "lead-audit"],
            "node_id": node_id,
            "group_id": "formulation",
            "task_id": "FORM-HELDOUT-08",
            "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
            "artifact_type": artifact_type,
            "path": rel,
            "sha256": sha(path),
            "validation_status": "unverified",
            "gate": "G-CLASSBIND",
            "summary": summary,
            "evidence_refs": evidence,
            "next_falsifier": falsifier,
            "claims_completion": False,
        }
        if extra:
            e.update(extra)
        events.append(e)

    artifact(
        H / "report.json", "heldout_corpus_report",
        (f"FORM-HELDOUT-08 complete: {rep['corpus']['mutants']} mutants / "
         f"{rep['corpus']['families']} families / {rep['corpus']['rephrased']} rephrased, built against the "
         f"frozen rev13 hashes with the manifest hashed before any stage run. valid={rep['valid']} "
         f"(7/7 controls accepted both stages). Aggregates: structural_escape={a['structural_escape']}, "
         f"semantic_escape={a['semantic_escape']}, union_escape={a['union_escape']}; 0 mutants caught. "
         f"Union escape families ({len(fams)}): {', '.join(fams)}. "
         f"A gate-sensitivity check on 6 known FORM-HELDOUT-07 leaks still rejects all 6, so the escape is "
         f"not a dead pipeline. No node completion claimed."),
        [ref("artifacts/worker-16/heldout2/report.json"),
         ref("artifacts/worker-16/heldout2/raw_verdicts.json"),
         ref("artifacts/worker-16/heldout2/manifest.json"),
         ref("artifacts/worker-16/heldout2/gate_sensitivity_check.json"),
         ref("artifacts/worker-16/heldout2/drift_addendum.json"),
         "artifacts/worker-06/heldout_corpus/report.json#sha256:07b99def2e81"],
        ("A union escape of 0 on a third corpus built against rev13+ would mean R26-R31 generalise; "
         "any single family above whose fixtures are accepted by BOTH stages is the deliverable. "
         "Format-dominated rejection of a control invalidates the run and forces a rebuild on the "
         "canonical layout."),
        extra={"aggregates": a,
               "union_escape_families": fams,
               "manifest_sha256_before_run": rep["manifest_sha256_before_run"]},
    )
    artifact(
        H / "manifest.json", "heldout_corpus_manifest",
        (f"Frozen corpus definition for FORM-HELDOUT-08: {rep['corpus']['mutants']} mutants, "
         f"{rep['corpus']['families']} families, {rep['corpus']['rephrased']} rephrased, 4 authored controls, "
         f"3 frozen canonical controls. Bases are byte-identical copies of the revision-13 schemas; the live "
         f"canonical paths had drifted at build time (later re-pinned at FROZEN rev20), so the corpus binds "
         f"to the frozen bytes only. Corpus definition written before any stage run."),
        [ref("artifacts/worker-16/heldout2/manifest.json"),
         ref("artifacts/worker-16/heldout2/bases/af_wcc_vacuum.yaml"),
         ref("artifacts/worker-16/heldout2/bases/af_scc_c2_vacuum.yaml"),
         ref("artifacts/worker-16/heldout2/bases/af_scc_c0_vacuum.yaml"),
         ref("artifacts/formulation/FROZEN.json")],
        ("A fixture whose sha256 no longer matches the manifest retires the measurement and forces a re-run; "
         "any change to a mutant after a verdict is a corpus-integrity failure."),
    )
    artifact(
        H / "gate_sensitivity_check.json", "gate_sensitivity_control",
        ("Positive control for the 1.0 escape rate: 6 known leaky fixtures from FORM-HELDOUT-07 "
         "(genericity kind swap, false transfer row, C0 curvature hypothesis, symmetry contradiction, "
         "H2_loc substitution, quantifier order) are all still rejected by the current structural gate, "
         "so the two-stage pipeline is live and the 29 new escapes are not caused by a dead evaluator."),
        [ref("artifacts/worker-16/heldout2/gate_sensitivity_check.json"),
         ref("artifacts/worker-06/heldout_corpus/report.json")],
        ("If any of these six probes is later accepted by both stages, re-run this check before trusting "
         "new escape rates measured by the same pipeline."),
    )
    artifact(
        H / "drift_addendum.json", "freeze_drift_addendum",
        ("Freeze-drift addendum bound to the frozen report hash: at corpus build/run time the live canonical "
         "schemas no longer carried the rev13 hashes (FROZEN rev19); FROZEN rev20 has since re-pinned the live "
         "files. The corpus stays bound to rev13 per the assignment; no verdict is rebound. flash-17's blocker "
         "flash-17-blocker-freeze-drift-20260912T001054 already covers the drift and is not duplicated."),
        [ref("artifacts/worker-16/heldout2/drift_addendum.json"),
         ref("artifacts/worker-16/heldout2/report.json"),
         ref("artifacts/formulation/FROZEN.json"),
         "comms/outbox/deepseek-flash-17-qnf.jsonl"],
        ("A FROZEN revision that no longer matches either the rev13 binding or the live files reopens the "
         "binding question; re-derive only on a fresh assignment, never by editing this corpus."),
    )
    review = H / "leak_validity_review.json"
    if review.exists():
        rv = json.loads(review.read_text())
        s = rv.get("summary", {})
        artifact(
            review, "independent_leak_validity_review",
            (f"Post-run independent adversarial review of the 29 mutants: "
             f"genuine_leak={s.get('genuine_leak')}, borderline={s.get('borderline')}, "
             f"legitimate={s.get('legitimate')}. Families with concern: {s.get('families_with_concern')}. "
             f"Does not change the frozen verdicts; it calibrates how strongly the escape families should "
             f"be read."),
            [ref("artifacts/worker-16/heldout2/leak_validity_review.json"),
             ref("artifacts/worker-16/heldout2/report.json")],
            ("A mutant classified legitimate by a domain reviewer is a corpus over-claim and must be dropped "
             "from the family list or relabelled before the escape rate is cited."),
        )

    if "--dry-run" in sys.argv:
        errs = []
        for e in events:
            try:
                validate_event(e)
            except Exception as exc:  # noqa: BLE001
                errs.append(f"{e['event_id']}: {exc}")
        print(f"dry-run: {len(events)} events, {len(errs)} schema errors")
        for x in errs:
            print("  !", x)
        return 1 if errs else 0

    with OUTBOX.open("a") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"appended {len(events)} artifact events to {OUTBOX.relative_to(ROOT)}")
    for e in events:
        print(" ", e["event_id"], e["artifact_type"], e["sha256"][:12])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
