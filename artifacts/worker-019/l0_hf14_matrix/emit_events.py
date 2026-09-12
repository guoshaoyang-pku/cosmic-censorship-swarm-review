#!/usr/bin/env python3
"""Emit W019-L0-HF14-MATRIX-01 events + checkpoint (no map write, no ingest call).

Appends 4 schema-valid events to comms/outbox/worker-019.jsonl:
  artifact(runner), artifact(matrix), claim(stability_result), status(active).
Writes the checkpoint under runtime/state/ and artifacts/worker-019/.
Validates every appended event with research_map.schemas.validate_event.
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import re
import sys
from datetime import datetime, timezone, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from research_map.schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)
STAMP = NOW.strftime("%Y%m%dT%H%M%S")
OUTBOX = ROOT / "comms/outbox/worker-019.jsonl"
MATRIX = ROOT / "artifacts/worker-019/l0_hf14_matrix/matrix.json"
RUNNER = ROOT / "artifacts/worker-019/l0_hf14_matrix/run_hf14_matrix.py"

CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
CLASS_ID = ";".join(CLASS_IDS)


def sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pref(p: pathlib.Path) -> str:
    return f"{p.relative_to(ROOT)}#sha256:{sha256(p)[:12]}"


def main() -> int:
    m = json.loads(MATRIX.read_text())
    h_matrix, h_runner = sha256(MATRIX), sha256(RUNNER)
    assert m["drift_free"], "matrix reports input drift; refusing to emit"
    ev_matrix, ev_runner = pref(MATRIX), pref(RUNNER)
    evidence = [
        "ledger/theorems.jsonl#sha256:a1674f094979",
        "evaluation_rubric.yaml#sha256:d748a9e3574e",
        "research_map/formulation_taxonomy.yaml#sha256:0abb9ed8a961",
        ev_matrix,
        ev_runner,
    ]
    n_L = m["readings"]["L_literal_key"]["trigger_n"]
    n_S = m["readings"]["S_semantic_support"]["trigger_n"]
    n_V = m["readings"]["V_author_verification_label"]["trigger_n"]
    falsifier = (
        "Re-run artifacts/worker-019/l0_hf14_matrix/run_hf14_matrix.py at the pinned sha256s "
        "(ledger a1674f094979, rubric d748a9e3574e, taxonomy 0abb9ed8a961): any changed value census, "
        "trigger set, or per-class count falsifies this matrix; any input hash move voids it and requires "
        "re-pinning. The reading choice itself is an adjudication, not a measurement."
    )
    summary = (
        f"W019-L0-HF14-MATRIX-01 complete (bounded class-bound worker, checkpointing then exiting). "
        f"Read-only trigger matrix for rubric HF-14 (self_certified_acceptance) at pinned inputs "
        f"(ledger a1674f094979, rubric d748a9e3574e): 62 ledger rows, 0 input drift. Literal-key reading "
        f"(status=accepted | validation_status=passed | supports_claim=true) triggers {n_L}/62 and reproduces "
        f"worker-079's count; semantic-support reading (author_asserts_supports=true, no reviewer-verdict "
        f"field, no artifact-hash field) triggers {n_S}/62 and reproduces worker-011's count; author-verification "
        f"label reading (content_status=verified, same absence conditions) triggers {n_V}/62. Measured facts both "
        f"reviewers share: 0/62 rows carry any of the three literal keys, 0/62 carry a reviewer-verdict field, "
        f"0/62 carry an artifact-hash field, 62/62 have review_status=not_independently_reviewed, 60/62 carry "
        f"author_asserts_supports=true, 50/62 carry content_status=verified, 34/62 carry at least one of the four "
        f"frozen class ids (42 occurrences; 28 rows have empty class_ids; 8 rows are dual-bound), and the 8 "
        f"dual-class rows are D-004, D-005, T-303, T-305, T-402, T-515, T-526, T-528. No gate verdict, no node "
        f"status, no shared file written."
    )
    events = [
        {
            "event_id": f"w019-hf14-art-runner-{STAMP}",
            "event_type": "artifact",
            "created_at": NOW.isoformat(timespec="seconds"),
            "actor": "worker-019",
            "node_id": "L0",
            "class_id": CLASS_ID,
            "class_ids": CLASS_IDS,
            "gate": "G-LIT",
            "task_id": "W019-L0-HF14-MATRIX-01",
            "artifact_type": "hf14_trigger_matrix_runner",
            "path": str(RUNNER.relative_to(ROOT)),
            "sha256": h_runner,
            "validation_status": "unverified",
            "evidence_refs": [ev_matrix, "ledger/theorems.jsonl#sha256:a1674f094979"],
            "falsifier": falsifier,
            "authority_note": "Worker artifact only; no gate verdict, no node status, no validation_status=passed.",
        },
        {
            "event_id": f"w019-hf14-art-matrix-{STAMP}",
            "event_type": "artifact",
            "created_at": NOW.isoformat(timespec="seconds"),
            "actor": "worker-019",
            "node_id": "L0",
            "class_id": CLASS_ID,
            "class_ids": CLASS_IDS,
            "gate": "G-LIT",
            "task_id": "W019-L0-HF14-MATRIX-01",
            "artifact_type": "hf14_trigger_matrix",
            "path": str(MATRIX.relative_to(ROOT)),
            "sha256": h_matrix,
            "validation_status": "unverified",
            "evidence_refs": evidence,
            "falsifier": falsifier,
            "authority_note": "Worker artifact only; no gate verdict, no node status, no validation_status=passed.",
        },
        {
            "event_id": f"w019-hf14-claim-{STAMP}",
            "event_type": "claim",
            "created_at": NOW.isoformat(timespec="seconds"),
            "actor": "worker-019",
            "node_id": "L0",
            "class_id": CLASS_ID,
            "class_ids": CLASS_IDS,
            "gate": "G-LIT",
            "task_id": "W019-L0-HF14-MATRIX-01",
            "conclusion_type": "stability_result",
            "statement": (
                f"Artifact-and-checker result at frozen ledger/theorems.jsonl sha256 a1674f094979 and frozen "
                f"evaluation_rubric.yaml sha256 d748a9e3574e: HF-14's literal-key trigger set is empty (0/62) while "
                f"its semantic-support and author-verification-label trigger sets are 60/62 and 50/62 respectively; "
                f"both reviewers' counts are reproducible under named readings. Measured shared facts: no row carries "
                f"status/validation_status/supports_claim, no row carries a reviewer-verdict field or artifact-hash "
                f"field, all 62 carry review_status=not_independently_reviewed, 60 carry author_asserts_supports=true, "
                f"50 carry content_status=verified, 34 carry at least one of the four frozen class ids (42 occurrences; "
                f"28 rows have empty class_ids; 8 rows are dual-bound), and the 8 "
                f"dual-class rows are D-004, D-005, T-303, T-305, T-402, T-515, T-526, T-528."
            ),
            "assumptions": [
                "HF-14 applies to ledger records as written; the rubric detector text was read verbatim from evaluation_rubric.yaml lines 243-252.",
                "author_asserts_supports is a support assertion field; whether it triggers HF-14 is the adjudicator's reading choice, not measured here.",
                "A per-row class breakdown counts dual-class rows in both classes; rows with no frozen class id are reported separately.",
            ],
            "falsifier": falsifier,
            "evidence_refs": evidence,
            "artifact_refs": [ev_matrix, ev_runner],
            "authority_note": "Worker evidence only: no gate verdict, no node status, no validation_status=passed, no canonical file written.",
        },
        {
            "event_id": f"w019-hf14-status-{STAMP}",
            "event_type": "status",
            "created_at": NOW.isoformat(timespec="seconds"),
            "actor": "worker-019",
            "node_id": "L0",
            "class_id": CLASS_ID,
            "class_ids": CLASS_IDS,
            "gate": "G-LIT",
            "task_id": "W019-L0-HF14-MATRIX-01",
            "status": "active",
            "hours": 0.3,
            "summary": summary,
            "evidence_refs": evidence,
            "next_falsifier": falsifier,
        },
    ]

    for e in events:
        validate_event(e)

    existing = OUTBOX.read_text() if OUTBOX.exists() else ""
    existing_ids = {json.loads(l)["event_id"] for l in existing.splitlines() if l.strip()}
    new_ids = {e["event_id"] for e in events if e["event_id"] in existing_ids}
    if new_ids:
        raise SystemExit(f"event_id already present, refusing to duplicate: {sorted(new_ids)}")
    with OUTBOX.open("a") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    # re-parse whole outbox
    for i, line in enumerate(OUTBOX.read_text().splitlines(), 1):
        if line.strip():
            json.loads(line)
    for e in events:
        validate_event(e)

    checkpoint = {
        "task_id": "W019-L0-HF14-MATRIX-01",
        "actor": "worker-019",
        "instance": "worker-019-20260912T011143-968807",
        "created_at": NOW.isoformat(timespec="seconds"),
        "node_id": "L0",
        "gate": "G-LIT",
        "class_ids": CLASS_IDS,
        "status": "active",
        "claims_completion": False,
        "inputs": m["inputs"],
        "input_drift": m["input_drift"],
        "outputs": {
            "matrix": {"path": str(MATRIX.relative_to(ROOT)), "sha256": h_matrix, "bytes": MATRIX.stat().st_size},
            "runner": {"path": str(RUNNER.relative_to(ROOT)), "sha256": h_runner, "bytes": RUNNER.stat().st_size},
        },
        "readings": {k: {"trigger_n": v["trigger_n"], "by_class_n": {c: d["n"] for c, d in v["by_class"].items()}} for k, v in m["readings"].items()},
        "events_emitted": [e["event_id"] for e in events],
        "outbox": str(OUTBOX.relative_to(ROOT)),
        "authority_note": "Worker checkpoint only; ingest and gate adjudication belong to the controller/group leads.",
        "next_falsifier": falsifier,
    }
    for p in [
        ROOT / f"runtime/state/worker-019_hf14_checkpoint_{STAMP}.json",
        ROOT / f"artifacts/worker-019/worker019_checkpoint_{STAMP}.json",
    ]:
        p.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
    print(json.dumps({
        "outbox_lines": len([l for l in OUTBOX.read_text().splitlines() if l.strip()]),
        "events": [e["event_id"] for e in events],
        "matrix_sha256": h_matrix,
        "runner_sha256": h_runner,
        "readings": {k: v["trigger_n"] for k, v in m["readings"].items()},
        "checkpoints": [
            f"runtime/state/worker-019_hf14_checkpoint_{STAMP}.json",
            f"artifacts/worker-019/worker019_checkpoint_{STAMP}.json",
        ],
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
