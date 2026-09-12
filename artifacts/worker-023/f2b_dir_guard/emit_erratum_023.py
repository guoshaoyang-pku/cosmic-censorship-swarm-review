#!/usr/bin/env python3
"""Corrective emission for W023-F2B-DIR-GUARD-01 (see ERRATUM.json).

The first emission's claim used a conclusion_type outside research_map/schemas.py's allowed
set and was rejected; its artifact and status events were accepted. This script emits the
corrected claim (formal_model) plus an artifact event for ERRATUM.json, validating every
event with the canonical validator before it is appended. It also refreshes checkpoint 5.

    python3 emit_erratum_023.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from research_map.schemas import validate_event  # noqa: E402

TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).isoformat(timespec="seconds")
STAMP = datetime.now(TZ).strftime("%Y%m%dT%H%M%S")
ACTOR = "worker-023"
TASK = "W023-F2B-DIR-GUARD-01"
NODE = "F2b"
CLASS0, CLASS2 = "AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"
FALSIFIER = ("Falsified if any fixture hash moves; the lint flags live/corrected fixtures at the "
             "pins; it fails to flag 84b5d3fa/48cadb72; the patched sandbox gate stops failing "
             "those two; or the diff stops applying to the FROZEN rev29 checker bytes.")


def main() -> int:
    sums = {}
    for line in (HERE / "SHA256SUMS").read_text().splitlines():
        h, p = line.split(None, 1)
        sums[p.strip().lstrip("./")] = h
    for req in ("ERRATUM.json", "evidence/results.json", "evidence/gate_hook.json"):
        assert req in sums, f"{req} missing from SHA256SUMS"
    events = [
        {
            "event_id": f"w23-dirguard-{STAMP}-artifact-erratum",
            "event_type": "artifact", "created_at": NOW, "actor": ACTOR,
            "node_id": NODE, "class_id": CLASS0, "class_ids": [CLASS0, CLASS2], "gate": "G-FORM",
            "artifact_type": "erratum", "path": "artifacts/worker-023/f2b_dir_guard/ERRATUM.json",
            "sha256": sums["ERRATUM.json"], "validation_status": "unverified",
            "summary": ("ERRATUM ERR1: corrects the rejected claim's conclusion_type "
                        "(methodological_finding -> formal_model), records the two authoritative "
                        "evidence hashes versus the stale README prefixes, and records that the "
                        "evidence files' bytes are not deterministic across re-runs while the "
                        "measured checks are."),
            "evidence_refs": [f"artifacts/worker-023/f2b_dir_guard/ERRATUM.json#{sums['ERRATUM.json'][:12]}",
                              "comms/rejected.jsonl#w23-dirguard-20260912T011614-claim"],
            "falsifier": FALSIFIER,
        },
        {
            "event_id": f"w23-dirguard-{STAMP}-claim-r2",
            "event_type": "claim", "created_at": NOW, "actor": ACTOR,
            "node_id": NODE, "class_id": CLASS0, "class_ids": [CLASS0, CLASS2], "gate": "G-FORM",
            "conclusion_type": "formal_model",
            "supersedes": "w23-dirguard-20260912T011614-claim",
            "statement": ("At the pinned FROZEN rev29 bytes, the H1/H2 containment repair candidates "
                          "84b5d3fa29a6 and 48cadb72e507 each assert one entailment reversal in "
                          "regularity.must_not_conflate that canonical rule R06 does not see, while "
                          "the corrected candidates 9ab32ee39d00 and 51c253c46306 and the live rev13 "
                          "bytes carry none; a class-relative direction predicate detects the "
                          "reversal, is calibrated on 5 mutants and clears the corrected variants. "
                          "Delivered as an R31 hook proposal, not as an applied canonical change. "
                          "(Resubmission of the rejected claim with an allowed conclusion_type; see "
                          "ERRATUM.json.)"),
            "assumptions": [
                "document-internal semantics only: one_way_entailments(X->Y) means E_Y subset of E_X, "
                "as the C0/C2 documents themselves state",
                "English lexical forms only; unparsed slot text is reported as unclassified, never certified",
                "fixture bytes pinned in fixtures/MANIFEST.json; any hash move voids the measurement",
            ],
            "falsifier": FALSIFIER,
            "evidence_refs": [
                "artifacts/worker-023/f2b_dir_guard/evidence/results.json#"
                + sums["evidence/results.json"][:12],
                "artifacts/worker-023/f2b_dir_guard/evidence/gate_hook.json#"
                + sums["evidence/gate_hook.json"][:12],
                "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
                "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
                "artifacts/worker-023/f2b_dir_guard/ERRATUM.json#" + sums["ERRATUM.json"][:12],
            ],
            "artifact_refs": [
                "artifacts/worker-023/f2b_dir_guard/containment_direction_lint.py#"
                + sums["containment_direction_lint.py"][:12],
                "artifacts/worker-023/f2b_dir_guard/proposed_gate_hook_R31.diff#"
                + sums["proposed_gate_hook_R31.diff"][:12],
                "artifacts/worker-023/f2b_dir_guard/fixtures/MANIFEST.json#"
                + sums["fixtures/MANIFEST.json"][:12],
            ],
        },
    ]
    for e in events:
        validate_event(e)  # canonical validator: raises before anything is written

    out = ROOT / "comms/outbox/worker-023.jsonl"
    with out.open("a") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    ckpath = ROOT / "runtime/state/w023_checkpoint_5.json"
    ck = json.loads(ckpath.read_text())
    ck["created_at"] = NOW
    ck["artifacts"]["ERRATUM.json"] = sums["ERRATUM.json"]
    ck["artifacts_abs"]["ERRATUM.json"] = str(HERE / "ERRATUM.json")
    ck["events_emitted"] = ck.get("events_emitted", 0) + len(events)
    ck["errata"] = ["ERRATUM.json#ERR1: rejected claim conclusion_type corrected; stale README "
                    "evidence prefixes documented; evidence-byte non-determinism documented"]
    ck["corrected_claim_event_id"] = events[1]["event_id"]
    ckpath.write_text(json.dumps(ck, indent=2, sort_keys=True))

    lines = out.read_text().splitlines()[-len(events):]
    assert all(json.loads(x) for x in lines)
    print(f"emitted {len(events)} corrective events; checkpoint updated "
          f"(events_emitted={ck['events_emitted']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
