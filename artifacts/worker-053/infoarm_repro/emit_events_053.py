#!/usr/bin/env python3
"""W053-GCLASSBIND-INFOARM-REPRO-01: write snapshot + SHA256SUMS + outbox events + checkpoint.

Idempotent: an event whose event_id already exists in comms/outbox/worker-053.jsonl is not
appended again. Every event is validated with research_map/schemas.validate_event first.
Read-only outside artifacts/worker-053/infoarm_repro/, comms/outbox/worker-053.jsonl and
runtime/state/w053_*.

Usage: python3 artifacts/worker-053/infoarm_repro/emit_events_053.py
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
STAMP = "w053-infoarm-20260912T0123"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_root(start: Path) -> Path:
    for cand in [start, *start.parents]:
        if (cand / "research_map" / "schemas.py").is_file() and (cand / "artifacts").is_dir():
            return cand
    raise SystemExit("repo root not found")


ROOT = find_root(HERE)
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402


def main() -> int:
    now = datetime.now(CST).isoformat(timespec="seconds")
    report = json.loads((HERE / "report.json").read_text())
    mun = json.loads((HERE / "mutants.json").read_text())

    # ---- snapshot ------------------------------------------------------------
    snap = HERE / "snapshot"
    snap.mkdir(exist_ok=True)
    snap_files = []
    for rel in ("artifacts/heldout/heldout-09/manifest.json", "artifacts/heldout/heldout-09/report.json",
                "artifacts/heldout/heldout-10/manifest.json", "artifacts/heldout/heldout-10/report.json"):
        dst = snap / rel.replace("artifacts/heldout/", "").replace("/", "__")
        shutil.copyfile(ROOT / rel, dst)
        snap_files.append(dst)
    for name in ("PREREGISTRATION.json", "report.json", "mutants.json", "controls.json", "repro_infoarm_053.py"):
        dst = snap / name
        shutil.copyfile(HERE / name, dst)
        snap_files.append(dst)

    # ---- SHA256SUMS ----------------------------------------------------------
    files = sorted(p for p in HERE.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt")
    lines = [f"{sha256_file(p)}  {p.relative_to(HERE)}" for p in files]
    (HERE / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n")

    rel = lambda p: str(p.relative_to(ROOT))  # noqa: E731
    ev = lambda name: f"{rel(HERE / name)}#{sha256_file(HERE / name)[:12]}"  # noqa: E731
    common_refs = [
        ev("report.json"), ev("mutants.json"), ev("controls.json"), ev("PREREGISTRATION.json"),
        ev("repro_infoarm_053.py"), ev("README.md"),
        "artifacts/heldout/heldout-09/manifest.json#" + sha256_file(ROOT / "artifacts/heldout/heldout-09/manifest.json")[:12],
        "artifacts/heldout/heldout-10/manifest.json#" + sha256_file(ROOT / "artifacts/heldout/heldout-10/manifest.json")[:12],
        "artifacts/heldout/heldout-10/report.json#" + sha256_file(ROOT / "artifacts/heldout/heldout-10/report.json")[:12],
        "artifacts/formulation/evidence/lead_formulation_lifecycle_08_independent_verify.json#" + sha256_file(
            ROOT / "artifacts/formulation/evidence/lead_formulation_lifecycle_08_independent_verify.json")[:12],
    ]
    classes = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN"]
    summary_line = ("informative C2+C0 union escape 1.0 reproduced independently: heldout-09 0/24 and "
                    "heldout-10 0/26 mutants caught by either stage; W arms 5/5 and 7/7 caught by stage B; "
                    "7/7 controls pass; 0 pin drift; measured aggregates equal the declared reports")
    events = [
        {
            "event_id": f"{STAMP}-artifact-report",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-053",
            "task_id": "W053-GCLASSBIND-INFOARM-REPRO-01",
            "node_id": "A1",
            "class_ids": classes,
            "gate": "G-CLASSBIND",
            "artifact_type": "third_party_reproduction_measurement",
            "path": rel(HERE / "report.json"),
            "sha256": sha256_file(HERE / "report.json"),
            "validation_status": "unverified",
            "evidence_refs": common_refs,
        },
        {
            "event_id": f"{STAMP}-artifact-mutants",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-053",
            "task_id": "W053-GCLASSBIND-INFOARM-REPRO-01",
            "node_id": "A1",
            "class_ids": classes,
            "gate": "G-CLASSBIND",
            "artifact_type": "per_fixture_raw_verdicts",
            "path": rel(HERE / "mutants.json"),
            "sha256": sha256_file(HERE / "mutants.json"),
            "validation_status": "unverified",
            "evidence_refs": common_refs,
        },
        {
            "event_id": f"{STAMP}-claim-infoarm",
            "event_type": "claim",
            "created_at": now,
            "actor": "worker-053",
            "task_id": "W053-GCLASSBIND-INFOARM-REPRO-01",
            "node_id": "A1",
            "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
            "class_ids": classes,
            "gate": "G-CLASSBIND",
            "conclusion_type": "numerical_evidence",
            "statement": (
                "Measurement, not a gate verdict: at the frame stage hashes (stage A "
                "check_class_schema.py#000e09e46b2f, stage B spec_conformance_audit.py#c79d8ab8440a, F2a "
                "e9a27996dfd3, F2b b2ab6acb2bbe, FROZEN rev29 815e08079aef) an independent non-author worker "
                "reproduces the lead's informative-arm result on both preserved corpora: the C2+C0 arms of "
                "FORM-HELDOUT-09 (24 mutants) and FORM-HELDOUT-10 (26 mutants) are caught by NEITHER stage "
                "(union_caught 0/24 and 0/26, union escape 1.0; no rule of either stage fires), while the "
                "uninformative W arms are caught 5/5 and 7/7 by stage B; all 13 escape families reproduce at "
                "2/2 fixtures each; both corpora's declared informative aggregates equal the measured values; "
                "7/7 pre-registered controls pass and no frame pin moved. This removes the residual "
                "worker-084 process-level-independence limitation from the informative-arm number."),
            "assumptions": [
                "the stage contract is replicated byte-for-byte from run_acceptance.py#e544c36d2d16 and the tool hashes are unchanged across the run",
                "the held-out fixtures are self-contained YAML documents; their manifest sha256 values equal the measured file hashes",
                "the frame hashes were measured immediately before and after the run and the corpora/reports were not authored or edited by worker-053",
                "no gate verdict is claimed and the corpus validity question (H5/R03) is left where the lead recorded it",
            ],
            "falsifier": (
                "any informative C2/C0 mutant of heldout-09/10 caught by either stage at these pinned tool "
                "hashes; measured aggregates differing from the declared reports; any K1-K7 control failing; any "
                "frame hash moving; or a re-run of repro_infoarm_053.py producing different per-fixture verdicts."),
            "evidence_refs": common_refs,
            "artifact_refs": [ev("report.json"), ev("mutants.json"), ev("controls.json")],
        },
        {
            "event_id": f"{STAMP}-blocker-infoarm",
            "event_type": "blocker",
            "created_at": now,
            "actor": "worker-053",
            "task_id": "W053-GCLASSBIND-INFOARM-REPRO-01",
            "node_id": "A1",
            "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
            "class_ids": classes,
            "gate": "G-CLASSBIND",
            "description": (
                "Corroboration of the standing G-CLASSBIND blocker (not a new claim): the two-stage acceptance "
                "pipeline catches 0/50 informative C2+C0 mutants across both frozen held-out corpora at the "
                "pinned stage hashes; the stage-B R03 defect is not the cause (W arms 12/12 caught). No rule in "
                "either stage fires on any informative mutant, so the held-out escape numbers cannot certify "
                "semantic conformance of the class schemas until stage 2 gains content/polarity/containment "
                "checks or a scoped ruling changes the criterion."),
            "needed_to_unblock": (
                "A gate-owner decision on the criterion plus either (a) a stage-2 revision that separates the "
                "13 informative escape families from the frozen canonical (with its hash pinned in the same "
                "FROZEN revision, per lead measurement_5) or (b) a recorded ruling that the informative-arm "
                "criterion is not part of G-CLASSBIND. Either way the measurement above stands as the "
                "independent baseline."),
            "evidence_refs": common_refs,
        },
        {
            "event_id": f"{STAMP}-status-final",
            "event_type": "status",
            "created_at": now,
            "actor": "worker-053",
            "task_id": "W053-GCLASSBIND-INFOARM-REPRO-01",
            "node_id": "A1",
            "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
            "class_ids": classes,
            "gate": "G-CLASSBIND",
            "status": "active",
            "hours": 0.4,
            "summary": (
                "W053-GCLASSBIND-INFOARM-REPRO-01 complete at worker level. Self-taken bounded class-bound "
                "task; no inbox card. " + summary_line + ". Artifacts at artifacts/worker-053/infoarm_repro/ "
                "(report.json, mutants.json, per_fixture.json, controls.json, drift.json, PREREGISTRATION.json, "
                "README.md, SHA256SUMS.txt, snapshot/) with worker-local checkpoint at "
                "runtime/state/w053_infoarm_repro_checkpoint.json and w053_checkpoints.jsonl. No gate verdict, "
                "no node status, no canonical write. Exiting."),
            "evidence_refs": common_refs,
            "next_falsifier": (
                "Re-run artifacts/worker-053/infoarm_repro/repro_infoarm_053.py at the same frame hashes: expect "
                "0/24 and 0/26 informative union catches and 7/7 controls; any informative mutant caught, any "
                "control failure, or any frame move falsifies this reproduction."),
        },
    ]

    outbox = ROOT / "comms/outbox/worker-053.jsonl"
    existing = set()
    if outbox.exists():
        for line in outbox.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                continue
    appended, skipped = [], []
    with outbox.open("a") as fh:
        for e in events:
            validate_event(e)
            if e["event_id"] in existing:
                skipped.append(e["event_id"])
                continue
            line = json.dumps(e, ensure_ascii=False)
            fh.write(line + "\n")
            appended.append({"event_id": e["event_id"], "event_type": e["event_type"],
                             "sha256": hashlib.sha256(line.encode()).hexdigest()})

    # ---- worker checkpoint ---------------------------------------------------
    ckpt = {
        "checkpoint_id": f"w053-infoarm-{datetime.now(CST).strftime('%Y%m%dT%H%M%S')}+0800",
        "actor": "worker-053",
        "task_id": "W053-GCLASSBIND-INFOARM-REPRO-01",
        "at": now,
        "node_id": "A1",
        "gate": "G-CLASSBIND",
        "class_ids": classes,
        "verdict": report["verdict"],
        "controls_ok": report["controls_ok"],
        "result": {
            "heldout-09": {"informative_mutants": 24, "informative_union_caught": 0, "informative_union_escape": 1.0,
                           "W_union_caught": 5},
            "heldout-10": {"informative_mutants": 26, "informative_union_caught": 0, "informative_union_escape": 1.0,
                           "W_union_caught": 7},
        },
        "frame_sha256": report["frame_sha256"],
        "artifact_sha256": {rel(p): sha256_file(p) for p in files},
        "events_appended": appended,
        "events_skipped_idempotent": skipped,
        "authority": "Worker measurement evidence only; no gate verdict, no node status, no canonical write.",
        "falsifier": report["falsifier"],
    }
    ck_dir = ROOT / "runtime/state"
    ck_dir.mkdir(parents=True, exist_ok=True)
    (ck_dir / "w053_infoarm_repro_checkpoint.json").write_text(json.dumps(ckpt, indent=1))
    with (ck_dir / "w053_checkpoints.jsonl").open("a") as fh:
        fh.write(json.dumps(ckpt, ensure_ascii=False) + "\n")

    print(json.dumps({"appended": appended, "skipped": skipped,
                      "checkpoint": "runtime/state/w053_infoarm_repro_checkpoint.json"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
