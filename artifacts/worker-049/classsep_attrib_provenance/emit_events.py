#!/usr/bin/env python3
"""Emit the W049-CLASSSEP-ATTRIB-PROVENANCE-04 events to comms/outbox/worker-049.jsonl.

Append-only, idempotent (skips event_ids already present), validates every line with
research_map.schemas.validate_event before writing. Worker-level events only: no
status=done, no validation_status=passed, no gate verdict.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUTBOX = os.path.join(ROOT, "comms/outbox/worker-049.jsonl")
sys.path.insert(0, ROOT)
from research_map.schemas import validate_event  # noqa: E402

T = "2026-09-12T01:17:00+08:00"
TASK = "W049-CLASSSEP-ATTRIB-PROVENANCE-04"
CLASS = "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"
AUTH = "worker evidence; cannot set status=done, validation_status=passed or a gate verdict"
FALSIFIER = ("Re-run run_attrib_provenance_049.py at the pins: any pin mismatch (exit 2), a "
             "non-deterministic double run (exit 3), a card-line byte mismatch (exit 4), an "
             "EXACT_MATCH row other than the FN-audit/successor live applied detector on corpus v2, "
             "a declaration-diff count of 13 for dc8aa0de3869 at any pinned corpus, or a byte-level "
             "hit for corpus-v2 fixtures (G01..G10/GM2..GM5/db6dff9f4eda) inside "
             "reviews/CLASSSEP-calibration-adjudication.json falsifies this packet.")
EV = [
    "artifacts/worker-049/classsep_attrib_provenance/results.json#57d04647c630",
    "artifacts/worker-049/classsep_attrib_provenance/pre_registration.json#12bbd0944ef2",
    "artifacts/worker-049/classsep_attrib_provenance/run_attrib_provenance_049.py#d9bff23702df",
    "artifacts/worker-049/classsep_attrib_provenance/README.md#8e2583c144b2",
    "runtime/state/w049_attrib_provenance_checkpoint.json#10db96e3bde3",
    "artifacts/worker-049/classsep_fn_audit/results.json#9e1bf2043934",
    "artifacts/worker-049/classsep_successor_audit/results.json#e3110ee9b7cf",
    "reviews/CLASSSEP-calibration-adjudication.json#7714ffd5b467",
    "runtime/state/controller_verification/astra-lifecycle-07-decisions.json#fc1d6fb4da6f",
    "comms/inbox/astra-lead-audit.jsonl:26#794137ddc9cb",
]

EVENTS = [
    {
        "event_id": "w049-attrib-20260912T0117-art-results",
        "event_type": "artifact",
        "created_at": T,
        "actor": "worker-049",
        "task_id": TASK,
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": CLASS,
        "group_id": "audit",
        "artifact_type": "evidence",
        "path": "artifacts/worker-049/classsep_attrib_provenance/results.json",
        "sha256": "57d04647c6306943271fdd9769ce745ae2f2f4ff2b3874c919326aa27723854e",
        "validation_status": "unverified",
        "evidence_refs": EV,
        "next_falsifier": FALSIFIER,
        "authority_note": AUTH,
    },
    {
        "event_id": "w049-attrib-20260912T0117-art-readme",
        "event_type": "artifact",
        "created_at": T,
        "actor": "worker-049",
        "task_id": TASK,
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": CLASS,
        "group_id": "audit",
        "artifact_type": "report",
        "path": "artifacts/worker-049/classsep_attrib_provenance/README.md",
        "sha256": "8e2583c144b223f15893c4774dac18360a61ad357f842d179ff057a5d3820b7c",
        "validation_status": "unverified",
        "evidence_refs": EV,
        "next_falsifier": FALSIFIER,
        "authority_note": AUTH,
    },
    {
        "event_id": "w049-attrib-20260912T0117-claim",
        "event_type": "claim",
        "created_at": T,
        "actor": "worker-049",
        "task_id": TASK,
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": CLASS,
        "group_id": "audit",
        "conclusion_type": "numerical_evidence",
        "statement": (
            "Provenance audit of the figure bound by card astra-life06-classsep-detector-adjudication "
            "(10/10 cue-carrying genuine assertions suppressed, 9 HIGH; 13 declaration diffs): across "
            "the pinned FN audit 9e1bf2043934, successor audit e3110ee9b7cf and r3 adjudication "
            "7714ffd5b467, the tuple (cleared=10, total=10, HIGH=9, declaration_diffs=13) has exactly "
            "two EXACT_MATCH rows, both detector live_canonical a8c04fc31e4a on corpus v2 "
            "(db6dff9f4eda) -- one in each audit -- and zero rows for classsep_prosefix dc8aa0de3869, "
            "which scores 11/12 cleared with 10 HIGH + 1 MED on corpus v1, 9/10 cleared with 7 HIGH on "
            "corpus v2 and 0 declaration diffs on both. The r3 census REC-32 cites contains no corpus-v2 "
            "fixture bytes and no declaration_diff field; its corpus_d is corpus v1, where the applied "
            "arm clears 1/12 (1 HIGH) and prosefix 11/12 (10 HIGH). REC-32's negative clause is right "
            "(e2d24b92 is not the 10/10 arm) but its positive attribution of the figure to dc8aa0de is "
            "not source-faithful: the figure's only exact source is the applied live guard on corpus v2, "
            "which is also the worst of the three card-cited candidates on the cue-FN axis."
        ),
        "assumptions": [
            "the measured sha256 is the artifact identity; every number binds only its pinned bytes",
            "the card's quoted figure is the four components textually present in its acceptance field",
            "the r3 census corpus_d is corpus v1 (A01-A12), as its fixture ids and the adjudication's own fixture_classes show",
            "an EXACT_MATCH requires all four quoted components simultaneously; three of four is PARTIAL_MATCH",
            "no natural-text FN/FP rate is claimed; all corpora are adversarial by construction",
        ],
        "falsifier": FALSIFIER,
        "evidence_refs": EV,
        "artifact_refs": [
            "artifacts/worker-049/classsep_attrib_provenance/results.json#57d04647c630",
            "artifacts/worker-049/classsep_attrib_provenance/README.md#8e2583c144b2",
            "artifacts/worker-049/classsep_attrib_provenance/pre_registration.json#12bbd0944ef2",
        ],
        "authority_note": AUTH,
    },
    {
        "event_id": "w049-attrib-20260912T0117-blocker-record",
        "event_type": "blocker",
        "created_at": T,
        "actor": "worker-049",
        "task_id": TASK,
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": CLASS,
        "group_id": "audit",
        "description": (
            "Operative record REC-32 (astra-lifecycle-07-decisions.json fc1d6fb4da6f) attributes the "
            "quoted FN figure to dc8aa0de3869 and points at the r3 corpus_d census; the pinned evidence "
            "gives that figure only to live_canonical a8c04fc31e4a on corpus v2, which the r3 census "
            "does not measure (no corpus-v2 fixture bytes, no declaration_diff field). Left uncorrected, "
            "the attribution sentence in the operative record is not reproducible from its own cited "
            "artifacts, and the card's 'worse one on cue-carrying genuine assertions' clause is corrected "
            "to the wrong arm: among the three cited candidates the worst is the applied guard."
        ),
        "needed_to_unblock": (
            "astra-lead-audit / controller: amend the REC-32 operative sentence to bind the figure to "
            "live_canonical a8c04fc31e4a on corpus v2 db6dff9f4eda, or record it as arm-ambiguous with "
            "the r3 corpus coverage gap noted; no detector write, no claim retirement, no gate verdict "
            "is requested by this packet."
        ),
        "evidence_refs": EV,
        "next_falsifier": FALSIFIER,
        "authority_note": AUTH,
    },
    {
        "event_id": "w049-attrib-20260912T0117-status-final",
        "event_type": "status",
        "created_at": T,
        "actor": "worker-049",
        "task_id": TASK,
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": CLASS,
        "group_id": "audit",
        "status": "active",
        "hours": 0.5,
        "summary": (
            "W049-CLASSSEP-ATTRIB-PROVENANCE-04 complete at worker level: pre-registered, fail-closed "
            "provenance audit of the 10/10-9-HIGH-13-decl-diff figure. Verdict "
            "REC32_NOT_SOURCE_FAITHFUL; exact source is live_canonical a8c04fc31e4a on corpus v2 in both "
            "worker-049 audits; prosefix dc8aa0de has no exact row; the r3 census REC-32 cites contains "
            "no corpus-v2 bytes and no declaration_diff field. Checkpoint "
            "runtime/state/w049_attrib_provenance_checkpoint.json. No gate verdict, node status or "
            "validation_status claimed; every canonical input read-only."
        ),
        "evidence_refs": [
            "artifacts/worker-049/classsep_attrib_provenance/results.json#57d04647c630",
            "runtime/state/w049_attrib_provenance_checkpoint.json#10db96e3bde3",
        ],
        "next_falsifier": FALSIFIER,
        "authority_note": AUTH,
    },
]


def main():
    seen = set()
    if os.path.exists(OUTBOX):
        for line in open(OUTBOX):
            line = line.strip()
            if not line:
                continue
            try:
                seen.add(json.loads(line).get("event_id"))
            except Exception:
                pass
    appended = 0
    with open(OUTBOX, "a") as fh:
        for ev in EVENTS:
            validate_event(ev)
            if ev["event_id"] in seen:
                continue
            fh.write(json.dumps(ev, sort_keys=True) + "\n")
            appended += 1
        fh.flush()
        os.fsync(fh.fileno())
    print(f"appended={appended} skipped={len(EVENTS) - appended}")


if __name__ == "__main__":
    main()
