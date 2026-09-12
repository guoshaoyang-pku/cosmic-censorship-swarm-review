#!/usr/bin/env python3
"""Correction addendum for the W062 R03 scope-safe-rule emission.

Two defects in the first emission (label w062-r03scope-20260912T0120), both mine:
 1. artifact event_ids were built from the human summary text and the `summary`
    fields were built from the short ids (tuple unpack order bug). Payloads
    (path, sha256, artifact_type) are correct; only the two label fields are swapped.
 2. the `claim` was rejected by the ingester: conclusion_type
    "artifact_measurement" is not in the allowed vocabulary.

This script appends, with fresh event ids, (a) an errata status mapping every
malformed artifact id to its correct event id / path / summary, (b) the corrected
claim with conclusion_type "formal_model", (c) a correction status. It does NOT
delete or edit the accepted lines, does not re-emit duplicate artifact payloads,
and changes no verdict, candidate byte or hash.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms/outbox/worker-062.jsonl"
CST = timezone(timedelta(hours=8))
OLD_LABEL = "w062-r03scope-20260912T0120"
NEW_LABEL = "w062-r03scope-fix-" + datetime.now(CST).strftime("%Y%m%dT%H%M")
TASK = "W062-GFORM-R03-SCOPE-SAFE-RULE-CANDIDATE-01"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def rel(p: Path) -> str:
    return str(Path(p).resolve().relative_to(ROOT))


BASE = {"actor": "worker-062", "node_id": "F1", "nodes": ["F1", "F2a", "F2b"],
        "class_id": "AF-WCC-VAC-GEN", "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM", "task_id": TASK}

# intended (kind, path, eid, summary) as written in emit_events.py
ARTIFACTS = [
    ("preregistration", HERE / "PREREGISTRATION.json", "preregistration",
     "Pre-registered pins, variants, expected matrix, expectations E1-E13, controls C1-C8, decision and stop rules."),
    ("deterministic_harness", HERE / "run_scope_safe_rule.py", "harness",
     "Pin-gated sandbox harness: builds baseline/E3/E4/E4-noscope from pinned bytes, generates variants, runs the 4x11x2 matrix and all controls."),
    ("artifact_report", HERE / "report.json", "report",
     "Full machine report: per-cell verdicts/failed rules/doc hashes, pins pre/post, tool hashes, expectations, controls."),
    ("matrix", HERE / "matrix.json", "matrix", "Compact 4-tool x 11-target matrix."),
    ("controls", HERE / "controls.json", "controls", "Control table C1-C8 incl. malformed-document control."),
    ("amendment", HERE / "AMENDMENT_01.json", "amendment",
     "Disclosed post-hoc E11 instrument correction (1 unified-diff hunk) + direct-canonical-bytes corroboration."),
    ("amendment_harness", HERE / "amend_e11_hunk_count.py", "amendment-harness",
     "Difflib hunk recount and direct run on published canonical F1 bytes; post-hoc, no verdict change."),
    ("candidate_tool", HERE / "sandbox/tools/E4/spec_conformance_audit.py", "candidate-E4",
     "E4 scope-aware R03 candidate bytes (sandbox only; live stage-2 instrument untouched and unpinned in FROZEN rev29)."),
    ("documentation", HERE / "README.md", "readme",
     "Question, method, matrix, controls, E11 disclosure, recommendation and scope limits."),
    ("entry_hashes", HERE / "entry_hashes.json", "entry-hashes", "Declared sha256 of the core deliverables."),
    ("checkpoint", HERE / "CHECKPOINT.json", "checkpoint",
     "Worker checkpoint: verdict PARTIAL, pins, matrix, E11 amendment, artifact hashes and falsifiers."),
]

CLAIM_STATEMENT = (
    "Artifact-and-checker measurement (not a mathematics or physics claim, not a theorem): at pinned bytes "
    "(canonical F1 d9cebb9404b2, frozen stage-2 auditor c79d8ab8440a, cand_E3 3f69bc1eb27a, rule spec 40f9bb9e657b), "
    "a pre-registered 4-tool x 11-target sandbox matrix with two deterministic runs per cell reproduces the formulation lead's "
    "scope finding (cand_E3 accepts the negation-scope-error rendering V3) and measures a scope-aware candidate E4 that accepts "
    "canonical frozen F1, its grouped/product/reordered equivalents, and canonical F2a/F2b, while rejecting V3, an unbound-restriction "
    "control, a shadow-quantifier control, a fully unbound control and a wrong-variable control. E4 replaces only the R03 binder block "
    "(one contiguous hunk, 28 changed lines): a non-literal composite binder passes iff the number of lexically located quantifier phrases "
    "equals the declared ordered-binder count, the phrase kind matches, and every binder variable occurs as a whole word inside that "
    "quantifier's own restriction phrase. All 13 pre-registered expectations except E11 hold and all 8 controls pass; E11 failed only because "
    "its hunk metric was implemented as a positional line comparison (446 changed lines), and a disclosed post-hoc amendment measures "
    "1 unified-diff hunk. Pre-registered verdict is therefore PARTIAL, not VALID. E4 is a sandbox candidate only; the stage-2 tool is unpinned "
    "in FROZEN rev29, so adoption requires pinning it in the same FROZEN revision."
)


def main():
    stamp = now()
    cp = sha(HERE / "CHECKPOINT.json")
    report = sha(HERE / "report.json")
    e4 = sha(HERE / "sandbox/tools/E4/spec_conformance_audit.py")
    refs = [f"{rel(HERE / 'report.json')}#{report[:12]}",
            f"{rel(HERE / 'CHECKPOINT.json')}#{cp[:12]}",
            f"{rel(HERE / 'AMENDMENT_01.json')}#{sha(HERE / 'AMENDMENT_01.json')[:12]}",
            f"{rel(HERE / 'sandbox/tools/E4/spec_conformance_audit.py')}#{e4[:12]}",
            "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
            "artifacts/worker-06/spec_conformance_audit.py#c79d8ab8440a",
            "artifacts/worker-064/r03_cause/work/cand_E3/artifacts/worker-06/spec_conformance_audit.py#3f69bc1eb27a",
            "artifacts/formulation/FROZEN.json#815e08079aef"]

    mapping = []
    for kind, path, eid, summary in ARTIFACTS:
        h = sha(path)
        mapping.append({
            "malformed_event_id": f"{OLD_LABEL}-artifact-{summary}",
            "correct_event_id": f"{OLD_LABEL}-artifact-{eid} (intended id; not re-emitted to avoid duplicate payloads)",
            "path": rel(path), "sha256": h, "artifact_type": kind, "intended_summary": summary,
        })

    events = [
        {"event_type": "status", "status": "active", "hours": 0.02, "event_id": f"{NEW_LABEL}-errata",
         "summary": ("ERRATA (no content, verdict or hash change) for label w062-r03scope-20260912T0120: the 11 artifact events carry correct "
                     "path/sha256/artifact_type but their event_id and summary fields are swapped (tuple-unpack bug in emit_events.py); the intended "
                     "id and summary for each are listed in `artifact_id_correction`. The claim under that label was rejected by the ingester "
                     "(conclusion_type 'artifact_measurement' not in the allowed vocabulary) and is superseded by the corrected claim under this label. "
                     "No artifact byte, matrix cell, expectation or control changed."),
         "artifact_id_correction": mapping,
         "evidence_refs": refs,
         "next_falsifier": "Any listed path whose measured sha256 differs from the mapping, or any claim that the malformed ids carried different payloads."},
        {"event_type": "claim", "event_id": f"{NEW_LABEL}-claim", "conclusion_type": "formal_model",
         "statement": CLAIM_STATEMENT,
         "assumptions": [
             "the FROZEN rev29 manifest, the three rev13 schemas, the rule spec 40f9bb9e657b and the two tool copies are the binding reference at measurement time",
             "all tools were invoked with the pinned --spec explicitly, so tool location does not change the rule set",
             "variants are canonical F1 with only the tail after 'with finite affine length: ' replaced; V0 is a YAML round-trip, and the direct canonical-bytes run in AMENDMENT_01 corroborates the same column",
             "this measures the stage-2 rule engine only; no end-to-end run_acceptance.py PASS is claimed",
             "no canonical, frozen, pinned or live-instrument byte was written; every write is under artifacts/worker-062/r03_scope_safe_rule/ or this worker's own outbox",
         ],
         "falsifier": "Show a run at the declared pins where E4 accepts a scope-error rendering, or rejects V1/V2/F2a/F2b, or any E4 matrix cell deviating from the pre-registered matrix; or show any input pin moving between T0 and T1.",
         "evidence_refs": refs,
         "artifact_refs": [f"{rel(HERE / 'report.json')}#{report[:12]}",
                           f"{rel(HERE / 'sandbox/tools/E4/spec_conformance_audit.py')}#{e4[:12]}"],
         "reviewed_sha256": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
         "supersedes_rejected_event_id": f"{OLD_LABEL}-claim",
         "correction_note": "Re-emitted with an allowed conclusion_type; statement identical to the rejected event."},
        {"event_type": "status", "status": "active", "hours": 0.01, "event_id": f"{NEW_LABEL}-status-correction",
         "summary": ("CORRECTION ADDENDUM (no verdict/claim change). The first emission's artifact id/summary swap is corrected by the errata event; "
                     "the rejected claim is re-emitted as formal_model. W062-GFORM-R03-SCOPE-SAFE-RULE-CANDIDATE-01 remains complete at worker level: "
                     "pre-registered matrix matched cell-for-cell, verdict PARTIAL with the E11 instrument defect disclosed and corrected post-hoc, "
                     "E4 sandbox candidate sha256 3cd55a5373e8, stage-2 tool unpinned in FROZEN rev29. CHECKPOINT + EXIT."),
         "evidence_refs": refs,
         "artifact_refs": [f"{rel(HERE / 'CHECKPOINT.json')}#{cp[:12]}"],
         "next_falsifier": "As in the corrected claim: any E4 matrix deviation or pin movement."},
    ]
    for e in events:
        e.setdefault("created_at", stamp)
        e.update(BASE)

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                try:
                    existing.add(json.loads(line).get("event_id"))
                except Exception:
                    pass
    new = [e for e in events if e["event_id"] not in existing]
    with OUTBOX.open("a") as f:
        for e in new:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"appended {len(new)} correction events under {NEW_LABEL}")
    for e in new:
        print(f"  {e['event_type']:9s} {e['event_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
