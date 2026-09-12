#!/usr/bin/env python3
"""Emit worker-099 incarnation-7 events for the G-FORM rev29 pin census.

Appends to comms/outbox/worker-099.jsonl (never truncates prior incarnations' events) and
validates every event with research_map/schemas.validate_event before writing.  Does not run
`comms.py ingest`; the controller owns the accepted stream.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "research_map"))
from schemas import validate_event  # noqa: E402

CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
ART_REL = "artifacts/worker-099/frozen_r3_pin_census/pin_census.json"
SCRIPT_REL = "artifacts/worker-099/frozen_r3_pin_census/run_pin_census.py"
README_REL = "artifacts/worker-099/frozen_r3_pin_census/README.md"
FROZEN_REF = "artifacts/formulation/FROZEN.json#815e08079aef"
DETECTOR_EVENT_REF = "artifacts/worker-073/classsep_union_separability/frame_drift_note.json#9a3a3ab9e2f5"
OUTBOX = os.path.join(ROOT, "comms", "outbox", "worker-099.jsonl")


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    art_sha = sha256(os.path.join(ROOT, ART_REL))
    script_sha = sha256(os.path.join(ROOT, SCRIPT_REL))
    readme_sha = sha256(os.path.join(ROOT, README_REL))
    art_bytes = os.path.getsize(os.path.join(ROOT, ART_REL))
    now = _dt.datetime.now().astimezone()
    iso = now.isoformat(timespec="seconds")
    ts = now.strftime("%H%M")
    prefix = f"w099-20260912T{ts}"
    art_ev = f"{ART_REL}#{art_sha[:12]}"
    script_ev = f"{SCRIPT_REL}#{script_sha[:12]}"
    readme_ev = f"{README_REL}#{readme_sha[:12]}"

    events = [
        {
            "event_id": f"{prefix}-artifact-frozen-r3-pin-census",
            "event_type": "artifact",
            "created_at": iso,
            "actor": "worker-099",
            "node_id": "F1/F2",
            "gate": "G-FORM",
            "class_ids": CLASS_IDS,
            "artifact_type": "gate_evidence_pin_census",
            "path": ART_REL,
            "sha256": art_sha,
            "bytes": art_bytes,
            "validation_status": "unverified",
            "census_runs": 3,
            "pin_verdict": "PASS",
            "quiescence_verdict": "WRITER_ACTIVE",
            "summary": (
                "Independent G-FORM rev29 pin census over all 50 files declared in "
                "artifacts/formulation/FROZEN.json (self-sha 815e08079aefbc measured twice): "
                "50/50 declared sha256+bytes match, 3/3 dual schema mirrors byte-equal, both "
                "taxonomy prefixes (0abb9ed8a961, d7419b4e8963) match. The frozen set is byte-stable "
                "but not quiescent: artifacts/formulation/evidence/taxonomy_consistency.json "
                "(declared 9e335e9ba1bf, 495 B) was rewritten byte-identically at 01:08:20.982 and "
                "01:09:34.236 inside the r3 window. Secondary observation: canonical "
                "research_map/class_separation.py was e36b0d644ca7 at ~01:07:50 and back at "
                "a8c04fc31e4a with mtime 01:08:14.862, a further write in the open REC-22 round. "
                "No schema-content verdict and no gate verdict are claimed."
            ),
            "evidence_refs": [art_ev, script_ev, readme_ev, FROZEN_REF],
            "falsifier": (
                "Re-running run_pin_census.py against the same FROZEN rev29 declarations returns a "
                "measured sha256 or byte count differing from a declaration, a FROZEN self-hash that "
                "no longer starts with 815e08079aefbc, a broken dual mirror, a taxonomy hash outside "
                "its declared prefix, or pinned bytes that change across the gap."
            ),
            "reproduce": "python3 artifacts/worker-099/frozen_r3_pin_census/run_pin_census.py",
        },
        {
            "event_id": f"{prefix}-claim-frozen-r3-pin-census",
            "event_type": "claim",
            "created_at": iso,
            "actor": "worker-099",
            "node_id": "F1/F2",
            "gate": "G-FORM",
            "class_id": ";".join(CLASS_IDS),
            "class_ids": CLASS_IDS,
            "conclusion_type": "formal_model",
            "statement": (
                f"At FROZEN rev29 (artifacts/formulation/FROZEN.json, measured sha256 "
                f"815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0, unchanged across "
                f"the census) all 50 declared files match their declared sha256 and byte counts at "
                f"three independent instants (01:08:05, 01:08:55, 01:09:32 first-instants; artifact "
                f"sha256 {art_sha}); the three dual schema mirrors are byte-equal and both taxonomy "
                f"hashes match their declared prefixes. The set is byte-stable but NOT quiescent: one "
                f"pinned file, artifacts/formulation/evidence/taxonomy_consistency.json (declared "
                f"9e335e9ba1bf, 495 B), was rewritten with byte-identical content at 01:08:20.982 and "
                f"01:09:34.236 inside the r3 window, so r3 reviewers must bind sha256 and record "
                f"writer activity rather than assume a quiescent window. Separately, the canonical "
                f"class-separation detector (research_map/class_separation.py) was measured at "
                f"e36b0d644ca7 ~01:07:50 and back at a8c04fc31e4a with mtime 01:08:14.862, a further "
                f"write inside the open REC-22 freeze round; every detector-bound verdict must cite "
                f"the hash it measured."
            ),
            "assumptions": [
                "FROZEN rev29 declarations are the review pins; the census tests them, it does not re-adjudicate schema content.",
                "Both instants of each run hash the live canonical paths; no formulation artifact was written by this worker.",
                "mtime identity is a stricter quiescence signal than byte identity; a byte-identical rewrite is writer activity, not a pin violation.",
                "The detector hash sequence is a secondary A1/G-AUDIT observation recorded by the same census; it is not a G-FORM verdict.",
            ],
            "falsifier": (
                "Any measured file hash or byte count differing from its FROZEN rev29 declaration, a "
                "FROZEN self-hash not starting 815e08079aefbc, a non-equal dual mirror, a taxonomy "
                "hash outside its declared prefix, or bytes changing across the gap voids this claim."
            ),
            "evidence_refs": [art_ev, script_ev, readme_ev, FROZEN_REF,
                              "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
                              "artifacts/formulation/formulation_taxonomy.yaml#d7419b4e8963"],
            "artifact_refs": [art_ev, script_ev, readme_ev],
        },
        {
            "event_id": f"{prefix}-review-frozen-r3-pin-census",
            "event_type": "review",
            "created_at": iso,
            "actor": "worker-099",
            "node_id": "F1/F2",
            "gate": "G-FORM",
            "class_ids": CLASS_IDS,
            "target_id": FROZEN_REF,
            "reviewer": "worker-099",
            "verdict": "inconclusive",
            "score": 3.5,
            "counts_toward_gate_accept": False,
            "counts_as_full_schema_verdict": False,
            "authority_note": "Advisory worker evidence only; no gate verdict, no node status=done, no validation_status=passed.",
            "hard_failures": [],
            "findings": [
                "W099-PC-01 (info): pin fidelity PASS — 50/50 FROZEN rev29 files matched declared sha256 and bytes at three independent instants; FROZEN self-sha 815e08079aefbc matched the controller-cited prefix; 3/3 dual mirrors byte-equal; taxonomy prefixes 0abb9ed8a961 / d7419b4e8963 matched.",
                "W099-PC-02 (major, process): the frozen set is not quiescent — artifacts/formulation/evidence/taxonomy_consistency.json (declared 9e335e9ba1bf, 495 B) was rewritten byte-identically at 01:08:20.982 and 01:09:34.236 inside the r3 window; 2 of 3 census windows caught the mtime move. Source-level candidate writer artifacts/formulation/tools/check_taxonomy_consistency.py:79 (writes exactly this path); process identity not proven by this census. No declared pin was violated.",
                "W099-PC-03 (major, CF-26 secondary): research_map/class_separation.py measured e36b0d644ca7 at ~01:07:50 and back at a8c04fc31e4a with mtime 01:08:14.862 — a further canonical write inside the open REC-22 detector freeze, restoring the adjudication's applied-canonical bytes; no announcing event for that transition was observed by this worker as of 01:10. Detector-bound verdicts must cite the measured hash.",
                "W099-PC-04 (info, class binding): no composite regularity class definition found — all 10 literal 'C0 or C2' / 'C2 or C0' occurrences across the six frozen schema mirrors are inside prohibition/quotation contexts (lines enumerated in class_binding.schema_co_mention); each of the four frozen class IDs appears in both taxonomy copies, both schema mirrors, KEY_MANIFEST and VARIANT_REGISTRY.",
                "W099-PC-05 (scope): inconclusive reflects that this census tests pins, quiescence and binding only — not schema content — and that the r3 window was shown to contain writer activity; it is not a defect finding against the FROZEN declarations.",
            ],
            "evidence_refs": [art_ev, script_ev, readme_ev, FROZEN_REF,
                              "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
                              "research_map/class_separation.py#a8c04fc31e4a"],
            "falsifier": (
                "A re-run of run_pin_census.py showing any declared pin mismatch, a different FROZEN "
                "self-hash, or bytes changing across the gap; or an announcing event for the "
                "e36b0d64 -> a8c04fc3 transition with created_at <= 01:08:14 falsifies W099-PC-03."
            ),
        },
        {
            "event_id": f"{prefix}-blocker-detector-write-back",
            "event_type": "blocker",
            "created_at": iso,
            "actor": "worker-099",
            "node_id": "A1",
            "gate": "G-AUDIT",
            "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
            "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
            "description": (
                "Further canonical detector write inside the open REC-22 freeze round, observed "
                "independently by the G-FORM pin census: research_map/class_separation.py measured "
                "e36b0d644ca7 at ~01:07:50 and back at a8c04fc31e4a with mtime 01:08:14.862, i.e. the "
                "bytes were restored to the adjudication's applied canonical after the unaccepted "
                "01:06:12 patch. No announcing artifact/assignment event for this transition was "
                "observed in the accepted stream by this worker as of 01:10. Recorded hash-bound in "
                f"artifacts/worker-099/frozen_r3_pin_census/pin_census.json ({art_sha[:12]})."
            ),
            "needed_to_unblock": (
                "astra-life06-classsep-detector-adjudication must cite the full write timeline with "
                "hashes and mtimes (c266dbec 23:30, a8c04fc3 00:52, e36b0d64 01:06:12, a8c04fc3 "
                "01:08:14.862), freeze writers at one published detector sha256, and require every "
                "detector-bound verdict to cite the hash it measured."
            ),
            "evidence_refs": [art_ev, "research_map/class_separation.py#a8c04fc31e4a",
                              DETECTOR_EVENT_REF,
                              "artifacts/worker-090/f2b_rev13_full_verdict/results.json#95e864ae7e32"],
            "falsifier": (
                "A copy of research_map/class_separation.py at mtime 2026-09-12T01:08:14.862+08:00 "
                "whose sha256 is not a8c04fc31e4a, or an announcing event for that write with "
                "created_at <= 01:08:14, falsifies this record."
            ),
        },
        {
            "event_id": f"{prefix}-status-frozen-r3-pin-census",
            "event_type": "status",
            "created_at": iso,
            "actor": "worker-099",
            "node_id": "F1/F2",
            "gate": "G-FORM",
            "class_ids": CLASS_IDS,
            "status": "active",
            "hours": 0.3,
            "claims_completion": False,
            "summary": (
                "CHECKPOINT + EXIT. Self-selected bounded class-bound task (no inbox card): "
                "independent G-FORM rev29 pin census. Artifact pin_census.json "
                f"{art_sha[:12]} ({art_bytes} B), instrument run_pin_census.py {script_sha[:12]}, "
                "README " + readme_sha[:12] + ". Pin fidelity PASS 50/50; quiescence WRITER_ACTIVE "
                "(taxonomy_consistency.json rewritten byte-identically twice inside the r3 window); "
                "secondary CF-26 observation of the e36b0d64 -> a8c04fc3 detector write-back at "
                "01:08:14.862. No gate verdict, no validation_status=passed, no completion claimed. "
                "Outbox appended; controller ingest owns the accepted stream."
            ),
            "evidence_refs": [art_ev, script_ev, readme_ev, FROZEN_REF],
            "next_falsifier": (
                "Re-run run_pin_census.py at the same FROZEN rev29 declarations; any declared pin "
                "mismatch, FROZEN self-hash change, or byte movement across the gap voids the PASS."
            ),
        },
    ]

    for ev in events:
        validate_event(ev)

    with open(OUTBOX, "a", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, sort_keys=True) + "\n")

    print(json.dumps({
        "outbox": "comms/outbox/worker-099.jsonl",
        "appended": len(events),
        "event_ids": [e["event_id"] for e in events],
        "art_sha256": art_sha,
        "script_sha256": script_sha,
        "readme_sha256": readme_sha,
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
