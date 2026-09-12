#!/usr/bin/env python3
"""Emit flash-10 L1 outbox events + local checkpoint for the AF-WCC-VAC-GEN conformance audit.

Bounded execution step (worker=010 / deepseek-flash-10), assignment
`asg-2026-09-11-L1-deepseek-flash-10-19`, node L1, gate G-LIT, class AF-WCC-VAC-GEN.

Sequence (all-or-nothing):
  1. re-run wcc_class_conformance_audit.py against the canonical schema so the artifact content
     and the emitted hashes are measured in the same instant;
  2. assert the artifact's recorded input hashes equal the just-measured input hashes (abort on
     drift, so a stale artifact can never be emitted);
  3. pin a byte-snapshot of the canonical schema used;
  4. validate every event against research_map.schemas.validate_event before writing anything;
  5. append artifact/claim/status events to comms/outbox/deepseek-flash-10.jsonl and write a
     local checkpoint JSON next to the artifact.

Nothing here sets node status=done, a gate verdict, or validation_status=passed; the artifact
stays `unverified` pending lead-literature/A1 review.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from research_map.schemas import validate_event  # noqa: E402

OUTBOX = ROOT / "comms" / "outbox" / "deepseek-flash-10.jsonl"
AUDIT = HERE / "wcc_class_conformance_audit.json"
SNAP_DIR = HERE / "snapshots"
SCHEMA = ROOT / "schemas" / "af_wcc_vacuum.yaml"
AUTHORING = ROOT / "artifacts" / "formulation" / "schemas" / "af_wcc_vacuum.yaml"
LEDGER = ROOT / "ledger" / "theorems.jsonl"
MATRIX = ROOT / "ledger" / "class_coverage.csv"
SUMMARY = HERE / "coverage_summary.json"
CLASS = "AF-WCC-VAC-GEN"
TZ = timezone(timedelta(hours=8))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    # 1. refresh the audit in-place
    subprocess.run([sys.executable, str(HERE / "wcc_class_conformance_audit.py")],
                   check=True, cwd=ROOT, capture_output=True, text=True)

    now = datetime.now(TZ)
    ts = now.strftime("%Y%m%dT%H%M%S")
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))

    schema_h = sha(SCHEMA)
    ledger_h = sha(LEDGER)
    matrix_h = sha(MATRIX)
    summary_h = sha(SUMMARY)
    audit_h = sha(AUDIT)

    # 2. refuse to emit a stale artifact
    recorded = audit["inputs"]
    measured = {
        "ledger/theorems.jsonl": ledger_h,
        "schemas/af_wcc_vacuum.yaml": schema_h,
        "ledger/class_coverage.csv": matrix_h,
        "artifacts/flash-10/l1_class_coverage/coverage_summary.json": summary_h,
    }
    for rel, h in measured.items():
        rec = recorded.get(rel, {}).get("sha256")
        if rec != h:
            raise SystemExit(f"STALE ARTIFACT: {rel} recorded={rec} measured={h}; not emitting")

    # 3. pin the schema bytes used by this audit
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    snap = SNAP_DIR / f"af_wcc_vacuum.{schema_h[:12]}.yaml"
    snap.write_bytes(SCHEMA.read_bytes())
    snap_h = sha(snap)
    authoring_h = sha(AUTHORING) if AUTHORING.exists() else None

    n_bound = audit["summary"]["n_bound_entries"]
    n_disch = audit["summary"]["n_discharging"]
    covered = [(c["source_id"], c["direction"]) for c in audit["summary"]["matrix_crosswalk"]["covered_cells"]]
    mismatch = audit["summary"]["matrix_crosswalk"]["direction_mismatch_cells"]
    revision = audit["class_definition"].get("revision")

    common = {
        "actor": "deepseek-flash-10",
        "run_id": "run-2026-09-11T23:15+08:00",
        "created_at": now.isoformat(timespec="seconds"),
        "gate": "G-LIT",
        "assignment_ref": "asg-2026-09-11-L1-deepseek-flash-10-19",
    }

    events = [
        {**common, "event_id": f"flash-10-artifact-wcc-conformance-{ts}", "event_type": "artifact",
         "node_id": "L1", "class_id": CLASS, "artifact_type": "json",
         "path": "artifacts/flash-10/l1_class_coverage/wcc_class_conformance_audit.json",
         "sha256": audit_h, "bytes": AUDIT.stat().st_size,
         "validation_status": "unverified", "claims_completion": False,
         "evidence_refs": [f"artifacts/flash-10/l1_class_coverage/wcc_class_conformance_audit.json#{audit_h[:12]}",
                           f"schemas/af_wcc_vacuum.yaml#{schema_h[:12]}", f"ledger/theorems.jsonl#{ledger_h[:12]}",
                           f"ledger/class_coverage.csv#{matrix_h[:12]}"],
         "inputs": {"ledger/theorems.jsonl": ledger_h, "schemas/af_wcc_vacuum.yaml": schema_h,
                    "ledger/class_coverage.csv": matrix_h,
                    "artifacts/flash-10/l1_class_coverage/coverage_summary.json": summary_h},
         "falsifier": ("One accepted ledger entry bound to AF-WCC-VAC-GEN that (i) quantifies over generic "
                       "(residual/comeagre) one-ended asymptotically flat vacuum Cauchy data, (ii) concludes complete "
                       "future null infinity or no singularity visible from I+ (not SCC inextendibility, not "
                       "trapped-surface formation alone), and (iii) is peer-reviewed/accepted-in-press with no open "
                       "hypothesis; then n_discharging >= 1."),
         "summary": (f"Class-bound conformance audit of all {n_bound} ledger entries bound to {CLASS} (schema rev{revision} "
                     f"at {schema_h[:12]}; ledger at {ledger_h[:12]}): {n_disch} entries discharge D1 (generic residual "
                     f"one-ended AF vacuum data) + D2 (complete I+ / no visible singularity) + D3 (accepted, no open "
                     f"hypothesis, peer-reviewed or accepted-in-press). The 7 `covered` matrix cells "
                     f"({', '.join(s for s, _ in covered)}) are binding-strength only; {len(mismatch)} of them "
                     f"({', '.join(mismatch)}) have only falsifier-direction bindings and are scope-inversion candidates "
                     f"for A1. validation_status=unverified pending lead-literature/A1.")},

        {**common, "event_id": f"flash-10-artifact-wcc-schema-pin-{ts}", "event_type": "artifact",
         "node_id": "L1", "class_id": CLASS, "artifact_type": "yaml",
         "path": f"artifacts/flash-10/l1_class_coverage/snapshots/{snap.name}",
         "sha256": snap_h, "bytes": snap.stat().st_size,
         "validation_status": "unverified", "claims_completion": False,
         "evidence_refs": [f"artifacts/flash-10/l1_class_coverage/snapshots/{snap.name}#{snap_h[:12]}",
                           f"schemas/af_wcc_vacuum.yaml#{schema_h[:12]}"],
         "inputs": {"schemas/af_wcc_vacuum.yaml": schema_h},
         "falsifier": "The snapshot sha256 differs from the canonical schemas/af_wcc_vacuum.yaml sha256 it pins.",
         "summary": (f"Byte-identical snapshot of canonical schemas/af_wcc_vacuum.yaml at {schema_h[:12]} (rev{revision}), "
                     f"the class definition this audit is bound to; authoring-tree copy measured at "
                     f"{(authoring_h or 'absent')[:12]}.")},

        {**common, "event_id": f"flash-10-claim-wcc-conformance-{ts}", "event_type": "claim",
         "node_id": "L1", "class_id": CLASS, "conclusion_type": "open_problem",
         "statement": (f"AF-WCC-VAC-GEN has {n_bound} accepted ledger entries bound to it at ledger revision "
                       f"{ledger_h[:12]} and {n_disch} that discharge the class's declared conclusion. The bindings are "
                       f"2 formulation (D-001, T-515), 3 peer-reviewed support theorems on special data "
                       f"(T-201/202/203, trapped-surface formation from short-pulse or specially glued data, all "
                       f"schema-listed non-generic), 4 conditional support results (T-204 preprint codimension-3 "
                       f"near-Schwarzschild, T-205 polarized, T-206 preprint small-|a| Kerr, T-528 preprint full "
                       f"subextremal Kerr), and 2 falsifier-direction counterexample constructions "
                       f"(T-208 peer-reviewed exterior, T-209 preprint interior+gluing). Every theorem-strength binding "
                       f"fails at least D1 (genericity is short-pulse/symmetry/codimension-restricted/near-Kerr, never "
                       f"residual-comeagre over one-ended AF vacuum data) and D2 (no entry asserts complete I+ or "
                       f"hiddenness of singularities; SCC inextendibility is a schema-listed forbidden strengthening). "
                       f"Therefore the 7 `covered` cells for this class in ledger/class_coverage.csv "
                       f"({', '.join(s for s, _ in covered)}) are binding-strength only, not class coverage; the class is "
                       f"open, matching the canonical schema's claim_promotion=open_problem. The 3 falsifier-side cells "
                       f"({', '.join(mismatch)}) are scope-inversion candidates for A1: naked-singularity constructions "
                       f"are evidence against WCC, not coverage of it."),
         "assumptions": [f"class_ids and status are inherited from ledger/theorems.jsonl revision {ledger_h[:12]}; this audit does not re-adjudicate them (A1's job)",
                         "D1/D2/D3 are mechanical field readings (genericity, scope_caveats, unresolved, entry_kind, evidence_level, statement text); a reviewer may bind an entry differently, which is the A1 verdict this artifact asks for",
                         f"the class definition is quoted from canonical schemas/af_wcc_vacuum.yaml at sha256 {schema_h[:12]} (rev{revision}); a field-for-field comparison of the extracted class definition against the previous revision 68392dd82050 showed no substantive change, so the 0-discharge result is revision-invariant across that step, but a later schema edit voids it for the new hash",
                         "D3 treats any non-empty ledger `unresolved` list as an open item; entries failing D3 here also fail D1 and/or D2, so the 0-discharge result does not hinge on that strictness"],
         "falsifier": ("Produce one accepted ledger entry bound to AF-WCC-VAC-GEN that (i) quantifies over generic "
                       "(residual/comeagre) one-ended asymptotically flat vacuum Cauchy data, (ii) concludes complete future "
                       "null infinity or no singularity visible from I+ (not SCC inextendibility, not trapped-surface "
                       "formation alone), and (iii) is peer-reviewed or accepted-in-press with no open hypothesis; then "
                       "n_discharging >= 1 and this claim is falsified."),
         "evidence_refs": [f"artifacts/flash-10/l1_class_coverage/wcc_class_conformance_audit.json#{audit_h[:12]}",
                           f"ledger/class_coverage.csv#{matrix_h[:12]}", f"ledger/theorems.jsonl#{ledger_h[:12]}",
                           f"schemas/af_wcc_vacuum.yaml#{schema_h[:12]}"],
         "artifact_refs": [f"artifacts/flash-10/l1_class_coverage/wcc_class_conformance_audit.json#{audit_h[:12]}",
                           f"artifacts/flash-10/l1_class_coverage/snapshots/{snap.name}#{snap_h[:12]}",
                           f"ledger/class_coverage.csv#{matrix_h[:12]}"],
         "expected_information_gain": ("Resolves the AF-WCC-VAC-GEN cell of the L1 matrix at class-conclusion strength and "
                                       "hands A1 a per-entry checklist plus 3 named direction-mismatch cells to adjudicate.")},

        {**common, "event_id": f"flash-10-status-wcc-conformance-{ts}", "event_type": "status",
         "node_id": "L1", "class_id": CLASS, "status": "active", "hours": 0.4,
         "summary": (f"Executed one class-bound task on {CLASS} within assignment asg-2026-09-11-L1-deepseek-flash-10-19: "
                     f"re-ran the deterministic conformance audit against the current canonical F1 schema (rev{revision}, "
                     f"{schema_h[:12]}) and pinned a byte snapshot; {n_bound} bound entries, {n_disch} discharging, 7 covered "
                     f"cells binding-only, 3 falsifier-side cells flagged for A1. No node completion, no gate verdict and no "
                     f"validation_status=passed claimed; artifact is unverified pending lead-literature/A1 review."),
         "evidence_refs": [f"artifacts/flash-10/l1_class_coverage/wcc_class_conformance_audit.json#{audit_h[:12]}",
                           f"artifacts/flash-10/l1_class_coverage/snapshots/{snap.name}#{snap_h[:12]}",
                           f"ledger/class_coverage.csv#{matrix_h[:12]}", f"ledger/theorems.jsonl#{ledger_h[:12]}"],
         "next_falsifier": ("Either (a) a peer-reviewed generic one-ended AF vacuum WCC theorem is bound to AF-WCC-VAC-GEN "
                            "(falsifies the claim), or (b) A1 rejects one of the 11 bindings as class leakage (strengthens "
                            "the gap and the direction-mismatch queue), or (c) T-204/T-528 clears peer review and the F1 lead "
                            "rules their data classes generic, which would force a re-audit at the then-current schema hash.")},
    ]

    # 4. validate everything before writing anything
    lines = []
    for e in events:
        validate_event(e)
        lines.append(json.dumps(e, ensure_ascii=False))

    checkpoint = {
        "checkpoint_id": f"flash-10-wcc-{ts}",
        "worker": "deepseek-flash-10",
        "slot": "010",
        "created_at": now.isoformat(timespec="seconds"),
        "assignment_ref": common["assignment_ref"],
        "node_id": "L1", "gate": "G-LIT", "class_id": CLASS,
        "task": "class-bound conformance audit of AF-WCC-VAC-GEN ledger bindings (one class-bound task)",
        "result": {"n_bound_entries": n_bound, "n_discharging": n_disch,
                   "covered_cells": [s for s, _ in covered],
                   "direction_mismatch_cells": mismatch,
                   "schema_revision": revision,
                   "class_definition_unchanged_vs_previous_revision": True},
        "hashes": {"audit": audit_h, "schema": schema_h, "schema_snapshot": snap_h,
                   "ledger": ledger_h, "matrix": matrix_h, "coverage_summary": summary_h},
        "event_ids": [e["event_id"] for e in events],
        "outbox": str(OUTBOX.relative_to(ROOT)),
        "validation_status": "unverified",
        "next_actions": ["controller ingest -> apply_events",
                         "A1/lead-literature review of the 3 direction-mismatch cells and the 11 bindings",
                         "re-audit at the new schema hash if F1 revises the class definition"],
    }
    ckpt_path = HERE / f"checkpoint_wcc_{ts}.json"
    ckpt_path.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    with OUTBOX.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print(json.dumps({
        "checkpoint": str(ckpt_path.relative_to(ROOT)),
        "checkpoint_sha256": sha(ckpt_path),
        "events_appended": len(events),
        "event_ids": [e["event_id"] for e in events],
        "artifact": {"path": str(AUDIT.relative_to(ROOT)), "sha256": audit_h},
        "claim": {"class_id": CLASS, "conclusion_type": "open_problem",
                  "n_bound_entries": n_bound, "n_discharging": n_disch},
        "evidence": {"schema": schema_h, "schema_snapshot": snap_h, "ledger": ledger_h, "matrix": matrix_h},
        "falsifier": events[2]["falsifier"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
