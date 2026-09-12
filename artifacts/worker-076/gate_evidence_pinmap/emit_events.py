#!/usr/bin/env python3
"""Emit worker-076 protocol events for W076-GATE-EVIDENCE-PINMAP-01.

Appends 3 artifact events, 1 blocker and 1 status to comms/outbox/worker-076.jsonl.
Hashes are re-measured from disk at emit time.  Worker authority: no gate verdict, no
validation_status=passed, no adoption, no canonical write.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms/outbox/worker-076.jsonl"
TASK = "W076-GATE-EVIDENCE-PINMAP-01"
CLASS_ID = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
NODE = "F1,F2a,F2b"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(p: str) -> str:
    path = ROOT / p
    return f"{p}#{sha256(path)[:12]}"


def main() -> int:
    now = datetime.now(CST)
    ts = now.strftime("%Y%m%dT%H%M")
    iso = now.isoformat(timespec="seconds")
    report = "artifacts/worker-076/gate_evidence_pinmap/report.json"
    pinmap = "artifacts/worker-076/gate_evidence_pinmap/raw/pinmap.json"
    probe = "artifacts/worker-076/gate_evidence_pinmap/raw/probe.json"
    preflight = "artifacts/worker-076/gate_evidence_pinmap/raw/run_acceptance_preflight.txt"
    stage2 = "artifacts/worker-06/spec_conformance_audit.py"
    runacc = "artifacts/formulation/tools/run_acceptance.py"
    manifest = "artifacts/worker-06/semantic_fixtures/manifest.json"
    corpus = "artifacts/formulation/evidence/semantic_escape_rebased.json"
    pinned_report = "artifacts/formulation/evidence/acceptance_pipeline_report.json"
    fixture = "artifacts/formulation/evidence/rebased_fixtures/struct12_i_plus_completeness_lexical.yaml"
    fresh_record = "artifacts/worker-076/gate_evidence_pinmap/sandbox/semantic_escape_rebased.fresh.json"
    frozen = "artifacts/formulation/FROZEN.json"

    common = {"task_id": TASK, "node_id": NODE, "class_id": CLASS_ID, "class_ids": CLASS_IDS, "gate": "G-FORM"}
    ev_report = {
        "event_id": f"w076-{ts}-pinmap-artifact-report",
        "event_type": "artifact",
        "created_at": iso,
        "actor": "worker-076",
        **common,
        "artifact_type": "gate_evidence_pinmap_report",
        "path": report,
        "sha256": sha256(ROOT / report),
        "validation_status": "unverified",
        "evidence_refs": [ref(report), ref(pinmap), ref(probe), ref(stage2), ref(runacc), ref(frozen)],
    }
    ev_tool = {
        "event_id": f"w076-{ts}-pinmap-artifact-tool",
        "event_type": "artifact",
        "created_at": iso,
        "actor": "worker-076",
        **common,
        "artifact_type": "gate_evidence_dependency_census",
        "path": pinmap,
        "sha256": sha256(ROOT / pinmap),
        "validation_status": "unverified",
        "evidence_refs": [
            ref(pinmap),
            ref("artifacts/worker-076/gate_evidence_pinmap/depmap.py"),
            ref(runacc), ref(stage2), ref(manifest), ref(frozen),
        ],
    }
    ev_probe = {
        "event_id": f"w076-{ts}-pinmap-artifact-probe",
        "event_type": "artifact",
        "created_at": iso,
        "actor": "worker-076",
        **common,
        "artifact_type": "unpinned_instrument_materiality_probe",
        "path": probe,
        "sha256": sha256(ROOT / probe),
        "validation_status": "unverified",
        "evidence_refs": [
            ref(probe),
            ref("artifacts/worker-076/gate_evidence_pinmap/materiality_probe.py"),
            ref("artifacts/worker-076/gate_evidence_pinmap/sandbox/spec_conformance_audit.sabotaged.py"),
            ref(fresh_record), ref(fixture), ref(corpus), ref(pinned_report), ref(preflight),
        ],
    }
    ev_blocker = {
        "event_id": f"w076-{ts}-pinmap-blocker-unpinned-stage2",
        "event_type": "blocker",
        "created_at": iso,
        "actor": "worker-076",
        **common,
        "description": (
            "G-FORM acceptance evidence rests on unpinned instruments. Independent census from the FROZEN-pinned "
            f"runner {runacc}#{sha256(ROOT/runacc)[:12]} resolves 44 dependencies: 9 pinned-match, 35 unpinned. "
            f"Unpinned and load-bearing: stage-2 engine {stage2}#{sha256(ROOT/stage2)[:12]} (executed by the pinned "
            f"runner; absent from FROZEN rev29's 50 files), its expectation manifest {manifest}#{sha256(ROOT/manifest)[:12]}, "
            "and all 33 artifacts/formulation/evidence/rebased_fixtures/*.yaml that drive the union-caught verdict. The "
            "pinned corpus record declares w06_sha256 = the live engine hash, but nothing enforces it (only "
            "measure_semantic_escape.py writes it; run_acceptance.py runs the path unchecked; verify_frozen.py covers only "
            "the 50 pinned paths). A one-line edit of a sandbox copy of the engine flips 11/33 stage-2 verdicts "
            "reject->accept with no pin moving. Separately, the pinned acceptance report does NOT reproduce at the live "
            f"base: it claims mutant union {json.loads((ROOT/pinned_report).read_text())['mutants']['union_caught']}/31 at base "
            f"{json.loads((ROOT/corpus).read_text())['base_sha256'][:12]} while regeneration with the pinned generator at live "
            f"C0 {sha256(ROOT/'artifacts/formulation/schemas/af_scc_c0_vacuum.yaml')[:12]} gives 30/31 with union escape "
            f"{Path(fixture).name}; the pinned runner still exits 3 at preflight. No canonical file was written by this task."
        ),
        "needed_to_unblock": (
            "In the same authorized revision that adopts any stage-2 (R03) change: (1) add "
            f"{stage2} (and {manifest} if selftest is gate evidence) to FROZEN.files with measured sha256; (2) make "
            "run_acceptance.py fail closed when sha256(stage2) != declared w06_sha256 / new pin; (3) disposition the 33 "
            "corpus fixture bytes (pin by hash or bind to the pinned generator+base and require regeneration); (4) re-pin "
            "acceptance_pipeline_report.json only after regeneration at the rev14/rev30 base. Owner: astra-lead-formulation; "
            "G-FORM adjudication owner: astra-lead-audit (astra-life05-verify-gform-r3)."
        ),
        "evidence_refs": [
            ref(report), ref(pinmap), ref(probe), ref(stage2), ref(runacc), ref(corpus),
            ref(pinned_report), ref(fixture), ref(preflight), ref(frozen),
        ],
        "next_falsifier": (
            "Falsified if the sabotaged copy reproduces every live stage-2 verdict on the fresh corpus, or the pinned "
            "acceptance report reproduces at the live base, or a probe-written file appears in FROZEN, or the live "
            "stage-2 hash differs from the declared w06_sha256."
        ),
    }
    ev_status = {
        "event_id": f"w076-{ts}-pinmap-status",
        "event_type": "status",
        "created_at": iso,
        "actor": "worker-076",
        **common,
        "status": "active",
        "hours": 1.0,
        "summary": (
            f"Bounded task {TASK} complete: dependency/pin census (44 deps, 35 unpinned incl. the stage-2 engine and the "
            "33-file corpus), declared-hash-not-enforced finding, sandbox materiality probe (11/33 stage-2 verdicts "
            "editable; pinned acceptance report 31/31 does not reproduce: 30/31 at live base), worker checkpoint written. "
            "Gate verdict NOT set; no canonical write; artifact+blocker emitted for controller/lead adjudication."
        ),
        "evidence_refs": [ref(report), ref(pinmap), ref(probe), ref(preflight)],
        "next_falsifier": ev_blocker["next_falsifier"],
    }
    events = [ev_report, ev_tool, ev_probe, ev_blocker, ev_status]
    with open(OUTBOX, "a") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(json.dumps({"written": len(events), "outbox": str(OUTBOX.relative_to(ROOT)),
                      "event_ids": [e["event_id"] for e in events]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
