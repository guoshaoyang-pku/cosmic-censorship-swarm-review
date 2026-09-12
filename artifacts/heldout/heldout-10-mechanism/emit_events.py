#!/usr/bin/env python3
"""Emit W084-C2C0-ESCAPE-MECHANISM-01 worker events to comms/outbox/worker-084.jsonl.

Idempotent: skips any event_id already present in the outbox. Also writes a copy of
the emitted lines to artifacts/heldout/heldout-10-mechanism/events.jsonl.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

DIR = Path(__file__).resolve().parent
ROOT = DIR.parents[2]
OUTBOX = ROOT / "comms" / "outbox" / "worker-084.jsonl"
CST = timezone(timedelta(hours=8))
TASK = "W084-C2C0-ESCAPE-MECHANISM-01"
CORPUS = "FORM-HELDOUT-10-MECHANISM"
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
GATE = "G-CLASSBIND"


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def ev(eid: str, etype: str, **kw) -> dict:
    o = {"event_id": eid, "event_type": etype, "created_at": now(), "actor": "worker-084",
         "task_id": TASK, "node_id": "A1", "gate": GATE, "class_id": CLASSES[1],
         "class_ids": CLASSES, "corpus_id": CORPUS}
    o.update(kw)
    return o


def artifact(event_id: str, rel: str, atype: str, note: str) -> dict:
    return ev(event_id, "artifact", artifact_type=atype, path=rel, sha256=sha(rel),
              validation_status="unverified",
              evidence_refs=[f"{rel}#sha256:{sha(rel)[:12]}"], note=note)


def main() -> int:
    report = json.loads((DIR / "report.json").read_text())
    ckpt = json.loads((DIR / "checkpoint.json").read_text())
    agg = report["aggregates"]
    mech = report["mechanism_headline"]
    strict = agg["informative_contract_only"]

    events = [
        ev("w084-mech-20260912T0130-01-status-task", "status",
           status="active", hours=0.4,
           summary=("W084-C2C0-ESCAPE-MECHANISM-01: one bounded class-bound task taken (no live "
                    "inbox card; FORM-HELDOUT-09 card void, FORM-HELDOUT-10 is the preserved "
                    "successor corpus). Mechanism adjudication of the heldout-10 informative-arm "
                    "escape by pre-registered differential re-execution of both frozen stages on "
                    "preserved base vs mutant bytes."),
           evidence_refs=["artifacts/heldout/heldout-10-mechanism/PREREGISTRATION.json#sha256:c695110cdfd7",
                          "artifacts/heldout/heldout-10/report.json#sha256:5629e2a69c86"],
           next_falsifier=report["falsifier"]),
        artifact("w084-mech-20260912T0130-02-artifact-prereg",
                 "artifacts/heldout/heldout-10-mechanism/PREREGISTRATION.json",
                 "mechanism_preregistration",
                 "Question, pins, differential method, contract/meta block map, controls K1-K8, "
                 "decision rules and falsifier, hashed before any probe run."),
        artifact("w084-mech-20260912T0130-03-artifact-amendment",
                 "artifacts/heldout/heldout-10-mechanism/PREREGISTRATION_AMENDMENT_1.json",
                 "preregistration_amendment",
                 "Append-only AMEND-1 adding two omitted prefix keys (conclusion.equivalent_rephrasings, "
                 "class_identity_variants); no method/control/decision change; v1 run preserved under v1/."),
        artifact("w084-mech-20260912T0130-04-artifact-analyzer",
                 "artifacts/heldout/heldout-10-mechanism/analyze_escape_mechanism.py",
                 "mechanism_analyzer",
                 "Deterministic, read-only harness; --verify reproduces the stored differential."),
        artifact("w084-mech-20260912T0130-05-artifact-differential",
                 "artifacts/heldout/heldout-10-mechanism/raw/differential.json",
                 "mechanism_raw_differential",
                 "Per-mutant per-stage base/mutant normalized outputs (sha256) + classifications; controls."),
        artifact("w084-mech-20260912T0130-06-artifact-adjudication",
                 "artifacts/heldout/heldout-10-mechanism/adjudication.json",
                 "escape_mechanism_adjudication",
                 "Per-mutant changed leaf paths, block categories, per-stage CAUGHT/SILENT/OBSERVED, union."),
        artifact("w084-mech-20260912T0130-07-artifact-report",
                 "artifacts/heldout/heldout-10-mechanism/report.json",
                 "escape_mechanism_report",
                 "Aggregates, controls, validity, falsifier; valid=true."),
        artifact("w084-mech-20260912T0130-08-artifact-findings",
                 "artifacts/heldout/heldout-10-mechanism/findings.json",
                 "escape_mechanism_findings", "Interpretation only; every number copied from report.json."),
        artifact("w084-mech-20260912T0130-09-artifact-report-md",
                 "artifacts/heldout/heldout-10-mechanism/REPORT.md",
                 "escape_mechanism_report_markdown", "Human-readable report, controls table, reproduce command."),
        artifact("w084-mech-20260912T0130-10-artifact-checkpoint",
                 "artifacts/heldout/heldout-10-mechanism/checkpoint.json",
                 "worker_checkpoint",
                 "Artifact hash table, controls, headline numbers, next falsifier; runtime copy at "
                 "runtime/state/w084_escape_mechanism_checkpoint.json."),
        ev("w084-mech-20260912T0130-11-claim-mechanism", "claim",
           class_id="AF-SCC-C2-VAC-GEN", conclusion_type="numerical_evidence",
           conclusion_type_note="worker measurement evidence only; not a theorem, not a gate verdict",
           assumptions=["preserved mutant and base bytes unmodified since the pre-registered manifest",
                        "stage tool bytes 000e09e46b2f / c79d8ab8440a unchanged during the run",
                        "SILENT = entire normalized reported rule surface identical base vs mutant"],
           statement=("At the FORM-HELDOUT-10 preserved bytes (FROZEN rev29 815e08079aef; C2 "
                      "e9a27996dfd3; C0 b2ab6acb2bbe; stage A 000e09e46b2f; stage B c79d8ab8440a), "
                      "all 26 informative-arm mutants escape with SILENT identical normalized output "
                      "from BOTH frozen stages (26/26 silent, 0 observed, 0 caught). Mechanism "
                      "verdict SILENT-BLINDNESS: the union escape 1.0 is field-blindness at the "
                      "reported rule surface, not a threshold call."),
           artifact_refs=["artifacts/heldout/heldout-10-mechanism/report.json",
                          "artifacts/heldout/heldout-10-mechanism/raw/differential.json",
                          "artifacts/heldout/heldout-10-mechanism/adjudication.json"],
           evidence_refs=["artifacts/heldout/heldout-10-mechanism/report.json#sha256:efbe219a119c",
                          "artifacts/heldout/heldout-10-mechanism/raw/differential.json#sha256:95d73f446853"],
           falsifier=report["falsifier"]),
        ev("w084-mech-20260912T0130-12-claim-strict-contract", "claim",
           class_id="AF-SCC-C0-VAC-GEN", conclusion_type="numerical_evidence",
           conclusion_type_note="worker measurement evidence only; not a theorem, not a gate verdict",
           assumptions=["pre-registered contract/meta block map (AMEND-1) applied to machine leaf diffs",
                        "CONTRACT = class-membership/normative surface; META = status/citation/self-guard text"],
           statement=(f"Restricted to mutants whose changed paths lie on the pre-registered "
                      f"class-contract surface, the strict C2+C0 union escape is "
                      f"{strict['union_escape']} with {strict['escape_silent']}/{strict['mutants']} "
                      f"SILENT in both stages (0 caught). The 6 META-only mutants are also 6/6 silent "
                      f"but are not counted as class-binding leaks. The escape is not an artifact of "
                      f"author labels on non-contract fields."),
           artifact_refs=["artifacts/heldout/heldout-10-mechanism/adjudication.json",
                          "artifacts/heldout/heldout-10-mechanism/report.json"],
           evidence_refs=["artifacts/heldout/heldout-10-mechanism/adjudication.json#sha256:73677640933b",
                          "artifacts/heldout/heldout-10-mechanism/report.json#sha256:efbe219a119c"],
           falsifier=report["falsifier"]),
        ev("w084-mech-20260912T0130-13-review-self", "review",
           target_id=TASK, target_artifact="artifacts/heldout/heldout-10-mechanism/report.json",
           reviewed_sha256=sha("artifacts/heldout/heldout-10-mechanism/report.json"),
           reviewer="worker-084", verdict="accept", score=3.5, hard_failures=[],
           findings=["All controls K1-K8 pass; valid=true; 49/49 integrity checks; 0 pin drift.",
                     "26/26 informative escapes are SILENT in both stages; strict CONTRACT-only 20/20 silent.",
                     "K3 proves the differential detects a real violation (planted foreign conclusion token rejected R11 by both stages).",
                     "v1 prefix-map omission preserved under v1/ with AMEND-1 declared before the amended run.",
                     "Author-adjacent: same worker id built the corpus; not a third-party audit.",
                     "Does not lift FORM-HELDOUT-10 strict-H5 valid=false (R03 instrument defect)."],
           note="self-review by the executor; not a gate verdict and not an independent review",
           evidence_refs=["artifacts/heldout/heldout-10-mechanism/report.json#sha256:efbe219a119c"]),
        ev("w084-mech-20260912T0130-14-status-complete", "status",
           status="active", hours=0.5,
           summary=(f"CHECKPOINT + EXIT (worker-084, {TASK}). One bounded class-bound task complete at "
                    f"worker level: mechanism verdict {mech}; informative arms 26/26 SILENT both stages; "
                    f"strict contract-only 20/20 SILENT, union escape {strict['union_escape']}; controls "
                    f"K1-K8 pass; valid=true; no canonical byte edited. No node completion, no gate "
                    f"verdict, no theorem; worker exits for recycling."),
           evidence_refs=["artifacts/heldout/heldout-10-mechanism/checkpoint.json#sha256:d9fa56caf1e8",
                          "artifacts/heldout/heldout-10-mechanism/report.json#sha256:efbe219a119c"],
           next_falsifier=report["falsifier"],
           do_not_claim=report["do_not_claim"]),
        artifact("w084-mech-20260912T0130-15-artifact-manifest",
                 "artifacts/heldout/heldout-10-mechanism/MANIFEST.json",
                 "task_directory_manifest",
                 "sha256 of every measurement deliverable under the task directory (the emission "
                 "machinery events.jsonl / emit_events.py and MANIFEST.json itself are excluded to "
                 "avoid a self-reference; the emitter hashes each artifact as it emits)."),
        ev("w084-mech-20260912T0130-16-status-addendum", "status",
           status="active", hours=0.1,
           summary=("APPEND-ONLY ADDENDUM to w084-mech-20260912T0130-14: MANIFEST.json "
                    "pins every measurement deliverable in the task directory, including the preserved "
                    "v1 run, the analysis harness, the sandbox controls and the worker checkpoint. No "
                    "verdict, number or claim above changes."),
           evidence_refs=["artifacts/heldout/heldout-10-mechanism/MANIFEST.json#sha256:9c595ce052b8",
                          "artifacts/heldout/heldout-10-mechanism/checkpoint.json#sha256:d9fa56caf1e8"],
           next_falsifier=report["falsifier"]),
    ]

    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                continue
    emitted = [e for e in events if e["event_id"] not in existing]
    with OUTBOX.open("a") as f:
        for e in emitted:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    (DIR / "events.jsonl").write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events))
    print(json.dumps({"emitted": [e["event_id"] for e in emitted],
                      "skipped": [e["event_id"] for e in events if e["event_id"] in existing],
                      "outbox": str(OUTBOX.relative_to(ROOT))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
