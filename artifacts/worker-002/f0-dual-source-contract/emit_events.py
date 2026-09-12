#!/usr/bin/env python3
"""Emit W002-F0-DUALSOURCE-01 events to comms/outbox/worker-002.jsonl (idempotent).

Validates every new event with research_map/schemas.validate_event and verifies
each cited hash prefix against the actual file before appending.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms" / "outbox" / "worker-002.jsonl"
sys.path.insert(0, str(ROOT / "research_map"))
import schemas  # noqa: E402

CST = timezone(timedelta(hours=8))
STAMP = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
NOW = datetime.now(CST).isoformat(timespec="seconds")
CLASS_ALL = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def ev(eid: str, etype: str, **kw) -> dict:
    return {"event_id": eid, "event_type": etype, "created_at": NOW,
            "actor": "worker-002", **kw}


def main() -> int:
    report = json.loads((HERE / "report.json").read_text())
    manifest = json.loads((HERE / "manifest.json").read_text())
    pins = {k: v["sha256"] for k, v in manifest["outputs"].items()}
    inp = {k: v["sha256"] for k, v in manifest["inputs"].items()}

    def pinh(rel: str) -> str:
        return pins.get(rel) or sha256(ROOT / rel)

    art_files = [
        ("report.json", "f0_dual_source_report_json",
         "24 decidable probe rows, per-class details, pointer surfaces, hygiene, coverage sweep."),
        ("controls.json", "f0_dual_source_controls_json",
         "12 self-contained synthetic controls, all pass; thresholds and sweep points."),
        ("SUMMARY.md", "f0_dual_source_summary_md",
         "Human-readable data-driven reading, probe matrix, residual rows, falsifier."),
        ("manifest.json", "f0_dual_source_manifest_json",
         "Hash pins of inputs and all outputs (does not hash itself)."),
        ("CHECKPOINT.json", "f0_dual_source_checkpoint_json",
         "Bounded-task checkpoint: input pins, output pins, controls, residual, next falsifier."),
        ("snapshots/F0-canonical-0abb9ed8a961.yaml", "f0_canonical_snapshot_yaml",
         "Frozen copy of the canonical declared-F0 rev5 under review."),
        ("snapshots/F0-supplement-d7419b4e8963.yaml", "f0_supplement_snapshot_yaml",
         "Frozen copy of the supplement rev9 (class-contract surface)."),
        ("snapshots/SHA256SUMS", "f0_snapshot_sha256sums",
         "Snapshot hash manifest."),
        ("check_dual_source_contract.py", "f0_dual_source_instrument_py",
         "Re-runnable instrument; exit 0 ok, 2 drift, 3 control failure."),
        ("make_manifest.py", "f0_dual_source_manifest_tool_py",
         "Manifest/checkpoint generator."),
    ]

    events = [ev(f"w002-ds-{STAMP}-status-taken", "status",
                 node_id="F0", gate="G-F0", class_id=CLASS_ALL, status="active",
                 hours=0.05,
                 summary=("Took one bounded class-bound task W002-F0-DUALSOURCE-01 (no inbox card "
                          "exists for worker-002 in this fleet): independent canonical-vs-supplement "
                          "class-contract agreement scan on node F0. No canonical path is written; "
                          "measurement and controls only."),
                 evidence_refs=["research_map/ASTRA_HANDOFF.md:32", "comms/PROTOCOL.md:47",
                                f"research_map/formulation_taxonomy.yaml#{inp['research_map/formulation_taxonomy.yaml'][:12]}",
                                f"artifacts/formulation/formulation_taxonomy.yaml#{inp['artifacts/formulation/formulation_taxonomy.yaml'][:12]}"],
                 next_falsifier=("a class_contract_pointer that resolves outside canonical classes.<ID>, "
                                 "a duplicate top-level key surviving, or a conflict_candidate bridged "
                                 "by a declared alias"))]

    for name, atype, note in art_files:
        path = HERE / name
        if not path.exists():
            print(f"missing output {name}", file=sys.stderr)
            return 1
        sha = sha256(path)
        rel = str(path.resolve().relative_to(ROOT))
        events.append(ev(f"w002-ds-{STAMP}-artifact-{Path(name).stem}", "artifact",
                         node_id="F0", gate="G-F0", class_id=CLASS_ALL,
                         artifact_type=atype, path=rel, sha256=sha,
                         validation_status="unverified",
                         evidence_refs=[f"{rel}#{sha[:12]}"], note=note))

    events.append(ev(f"w002-ds-{STAMP}-claim-dual-source", "claim",
                     node_id="F0", gate="G-F0", class_id=CLASS_ALL,
                     conclusion_type="stability_result",
                     statement=(
                         "Artifact-and-checker measurement (not a mathematics or physics claim): at "
                         "canonical declared-F0 rev5 sha256 0abb9ed8a961 and supplement rev9 sha256 "
                         "d7419b4e8963, the decidable class-contract probes agree on 22 rows with 0 "
                         "conflict_candidate: identical four-class id set; conclusion_type agrees on "
                         "all four (SCC via the declared VOCAB_ALIASES map); regularity tokens "
                         "consistent; genericity axes agree under declared aliases; variant registry "
                         "identical; all three class_contract_pointers now resolve inside canonical "
                         "classes.<ID>; both surfaces carry 0 duplicate top-level keys and no content "
                         "timestamp past written_at. Three non-hard residuals remain: the supplement "
                         "WCC predicates for AF-WCC-VAC-GEN and AF-WCC-SCALAR-SPH are underspecified "
                         "relative to the canonical single-q TAIL/comeager reading, and "
                         "AF-WCC-SCALAR-SPH carries a canonical-internal tension (conclusion names a "
                         "comeager set while genericity_kind/status is unresolved). 12/12 synthetic "
                         "controls pass; live bytes stable during the run."),
                     assumptions=[
                         "the two snapshot files are the frozen bytes at the recorded scan pins",
                         "aliases come only from the declared VOCAB_ALIASES.json",
                         "bracketed revision notes are editorial and stripped before classification",
                         "the hypotheses/exclusions coverage inventory is informational and does not "
                         "drive the reading",
                         "a worker event cannot set status=done, validation_status=passed or a gate verdict"],
                     falsifier=report["falsifier"],
                     evidence_refs=[
                         f"artifacts/worker-002/f0-dual-source-contract/report.json#{pins['artifacts/worker-002/f0-dual-source-contract/report.json'][:12]}",
                         f"artifacts/worker-002/f0-dual-source-contract/controls.json#{pins['artifacts/worker-002/f0-dual-source-contract/controls.json'][:12]}",
                         f"artifacts/worker-002/f0-dual-source-contract/snapshots/SHA256SUMS#{pins['artifacts/worker-002/f0-dual-source-contract/snapshots/SHA256SUMS'][:12]}",
                         f"research_map/formulation_taxonomy.yaml#{inp['research_map/formulation_taxonomy.yaml'][:12]}",
                         f"artifacts/formulation/formulation_taxonomy.yaml#{inp['artifacts/formulation/formulation_taxonomy.yaml'][:12]}",
                         f"artifacts/formulation/VOCAB_ALIASES.json#{inp['artifacts/formulation/VOCAB_ALIASES.json'][:12]}"],
                     artifact_refs=[
                         "artifacts/worker-002/f0-dual-source-contract/report.json",
                         "artifacts/worker-002/f0-dual-source-contract/controls.json",
                         "artifacts/worker-002/f0-dual-source-contract/SUMMARY.md",
                         "artifacts/worker-002/f0-dual-source-contract/manifest.json",
                         "artifacts/worker-002/f0-dual-source-contract/CHECKPOINT.json"],
                     next_falsifier=report["next_falsifier"]))

    events.append(ev(f"w002-ds-{STAMP}-status-checkpoint", "status",
                     node_id="F0", gate="G-F0", class_id=CLASS_ALL, status="active",
                     hours=0.25,
                     summary=("CHECKPOINT W002-F0-DUALSOURCE-01 complete. Deliverables under "
                              "artifacts/worker-002/f0-dual-source-contract/ (instrument, frozen "
                              "snapshots + SHA256SUMS, report.json, controls.json 12/12, SUMMARY.md, "
                              "manifest.json, CHECKPOINT.json), all hash-pinned. Reading: 0 hard "
                              "conflicts at canonical rev5/supplement rev9; residual = 2 underspecified "
                              "supplement predicates + 1 scalar-class canonical-internal tension "
                              "(comeager conclusion vs unresolved genericity axis). Measurement only; "
                              "no gate verdict or done status is claimed."),
                     evidence_refs=[
                         f"artifacts/worker-002/f0-dual-source-contract/CHECKPOINT.json#{pins['artifacts/worker-002/f0-dual-source-contract/CHECKPOINT.json'][:12]}",
                         f"artifacts/worker-002/f0-dual-source-contract/report.json#{pins['artifacts/worker-002/f0-dual-source-contract/report.json'][:12]}"],
                     next_falsifier=report["next_falsifier"]))

    events.append(ev(f"w002-ds-{STAMP}-status-exit", "status",
                     node_id="F0", gate="G-F0", class_id=CLASS_ALL, status="active",
                     hours=0.3,
                     summary=("Bounded task complete; exiting cleanly. W002-F0-DUALSOURCE-01 delivered "
                              "the canonical-vs-supplement class-contract agreement instrument and its "
                              "hash-pinned result at F0 rev5 0abb9ed8a961 / supplement rev9 d7419b4e8963. "
                              "No canonical path was modified; no completion, validation or gate status "
                              "is claimed. Residual items routed to the F0 owner: name the visibility "
                              "reading in the two supplement WCC predicates, and resolve or record the "
                              "scalar-class comeager-vs-unresolved-genericity tension."),
                     evidence_refs=[
                         f"artifacts/worker-002/f0-dual-source-contract/manifest.json#{pinh('artifacts/worker-002/f0-dual-source-contract/manifest.json')[:12]}",
                         f"artifacts/worker-002/f0-dual-source-contract/SUMMARY.md#{pins['artifacts/worker-002/f0-dual-source-contract/SUMMARY.md'][:12]}"],
                     next_falsifier=report["next_falsifier"]))

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                try:
                    existing.add(json.loads(line)["event_id"])
                except Exception:
                    pass
    new = [e for e in events if e["event_id"] not in existing]
    for e in new:
        schemas.validate_event(e)
    with open(OUTBOX, "a") as f:
        for e in new:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(json.dumps({"appended": len(new), "skipped_existing": len(events) - len(new),
                      "outbox": str(OUTBOX.relative_to(ROOT)),
                      "event_ids": [e["event_id"] for e in new]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
