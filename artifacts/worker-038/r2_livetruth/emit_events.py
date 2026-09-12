#!/usr/bin/env python3
"""Emit worker-038 R2LIVETRUTH events (validated against research_map/schemas.py) + checkpoint."""
from __future__ import annotations

import glob
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

WS = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
sys.path.insert(0, str(WS / "research_map"))
from schemas import validate_event  # noqa: E402

OUT = WS / "artifacts/worker-038/r2_livetruth"
OUTBOX = WS / "comms/outbox/worker-038.jsonl"
CKPT = WS / "runtime/state/worker-038_r2_livetruth_checkpoint.json"
CST = timezone(timedelta(hours=8))


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


now = datetime.now(CST).isoformat(timespec="seconds")
stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")

report = OUT / "report.json"
tool = OUT / "check_r2_livetruth.py"
readme = OUT / "README.md"
raw = sorted(glob.glob(str(OUT / "raw/run_*.json")))[-1]
H = {str(p): sha(Path(p)) for p in (report, tool, readme)}
H[raw] = sha(Path(raw))

DECLARED = "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"
LIVE_EV = "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"
PATCHED = "d3cdc717ec8a9adeb225f171186019cb7ae00f4d45765224a79aca6fb1bf1259"
CANON_TOOL = "de356d999ea3b6aeb9cfe7d35d6604328ccc4945ead3bc3ec566a929363f31cd"
A = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
B = "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"
FROZEN = "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1"
R086 = "artifacts/worker-086/evidence_collision/restore_candidate/taxonomy_consistency.675a99d0d25b.json"
R043 = "artifacts/worker-043/w043d_r2_durability/raw/evidence_restored_675a99d0.json"
P043 = "artifacts/worker-043/w043d_r2_durability/patched_check_taxonomy_consistency.py"

CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
EVID = [
    f"{report.relative_to(WS)}#{H[str(report)]}",
    f"{tool.relative_to(WS)}#{H[str(tool)]}",
    f"{readme.relative_to(WS)}#{H[str(readme)]}",
    f"{Path(raw).relative_to(WS)}#{H[raw]}",
    f"{R086}#{DECLARED}",
    f"{R043}#{DECLARED}",
    f"{P043}#{PATCHED}",
    f"artifacts/formulation/tools/check_taxonomy_consistency.py#{CANON_TOOL}",
    f"research_map/formulation_taxonomy.yaml#{A}",
    f"artifacts/formulation/formulation_taxonomy.yaml#{B}",
    f"artifacts/formulation/FROZEN.json#{FROZEN}",
    f"artifacts/formulation/evidence/taxonomy_consistency.json#{LIVE_EV}",
]

FALSIFIER = (
    "Any of: two patched-checker runs on identical inputs differ; the restored document's core keys "
    "differ from a fresh canonical re-derivation on live inputs; A/B hashes differ from the embedded "
    "values; the compared-field control (C5) is not caught, i.e. the instrument is dead; the C6 drift "
    "edit IS signalled by either checker; or any of the 9 guard files moves during the run."
)

STATEMENT = (
    "At the live pins (A research_map/formulation_taxonomy.yaml#0abb9ed8, B "
    "artifacts/formulation/formulation_taxonomy.yaml#d7419b4e, canonical checker#de356d99, live evidence "
    "path#9e335e9b, FROZEN rev28#2f358f67): the two independently preserved 675a99d0 candidates are "
    "byte-identical (728 B) and hash to the declared pin; the restored document's consistency verdict is "
    "still true of the current inputs (canonical checker re-derives CONSISTENT with the same 8 core keys); "
    "its embedded input hashes equal the live A and B; worker-043's patched checker is deterministic across "
    "two runs and never moves the pinned bytes; a compared-field edit is caught (exit 1); and an edit to the "
    "uncompared positive_test_case.description is NOT signalled by either checker while the pinned document's "
    "embedded lead_contract_sha256 silently goes stale. 8/8 pre-registered checks; 9/9 guard files unmoved."
)

REVIEW_FINDINGS = [
    "R2-AS-MEASURED IS SOUND AND REPRODUCED: reconstruction (728 B -> 675a99d0), patched-checker determinism "
    "(identical report hash on two runs) and non-clobber (evidence bytes 675a99d0 unchanged) all replicated "
    "independently in a mirrored sandbox; no canonical file was written (9/9 guard hashes identical before/after).",
    "C2/C3 NEW: the restored document is not merely hash-reconstructible, it is still TRUE of the live tree -- "
    "the canonical checker re-derives consistent=true, errors=[], divergences=[] and the embedded "
    "map_taxonomy_sha256/lead_contract_sha256 equal the live A/B. R2 therefore restores a valid claim today.",
    "W038-R2LT-F1 (residual, non-blocking for adopting R2; blocking for closing G-FORM on it): after an edit to "
    "an uncompared but load-bearing field (C2 positive_test_case.description), both the canonical and the patched "
    "checkers exit 0 with no error, while the pinned document's embedded lead_contract_sha256 (d7419b4e) no longer "
    "matches the live B (3f0ddd14). The detection data exists but no pinned artifact and no refresh rule requires "
    "re-measuring it; the schema rule still names only the declared F0 artifact. R2 fixes the writer collision, not "
    "the dependency-closure rule (independently consistent with worker-041 HF-041-RCA-2).",
    "W038-R2LT-F2 (soft, documentary): the frozen pair R2 creates would pin a document whose measured_at "
    "(2026-09-12T00:32:02+08:00) is 21 s AFTER the schema binding's declared checked_at (00:31:41). R2 keeps the "
    "schemas byte-identical by design, so this ordering inconsistency is frozen in; it does not affect the verdict.",
    "Non-blind: this reviewer read artifacts/worker-043/w043d_r2_durability/README.md and acceptance.json before "
    "writing, so it is not a blind count toward the two independent G-FORM verdicts; it is a verification of the "
    "R2 instrument, not of F1/F2a/F2b schema content.",
]

review = {
    "event_id": f"w038-r2lt-review-{stamp}",
    "event_type": "review",
    "created_at": now,
    "actor": "worker-038",
    "reviewer": "worker-038",
    "target_id": "W043D-R2-DURABILITY-01/R2-repair-plan",
    "target_path": P043,
    "target_sha256": PATCHED,
    "gate": "G-FORM",
    "node_id": "F1,F2a,F2b",
    "class_ids": CLASSES,
    "verdict": "accept",
    "score": 3.5,
    "hard_failures": [],
    "findings": REVIEW_FINDINGS,
    "falsifier": FALSIFIER,
    "evidence_refs": EVID,
    "blind_to_artifact_lineage": False,
    "counts_as_full_schema_verdict": False,
    "review_kind": "independent live-truth verification of a peer repair instrument",
    "scope": "R2 instrument only; NOT a verdict on F1/F2a/F2b schema content and not a gate verdict",
    "artifact": f"{report.relative_to(WS)}",
    "artifact_sha256": H[str(report)],
    "next_falsifier": FALSIFIER,
}

events = [
    {
        "event_id": f"w038-r2lt-artifact-report-{stamp}",
        "event_type": "artifact",
        "created_at": now,
        "actor": "worker-038",
        "artifact_type": "r2_livetruth_report",
        "node_id": "F1,F2a,F2b",
        "node_ids": ["F1", "F2a", "F2b"],
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": CLASSES,
        "gate": "G-FORM",
        "path": str(report.relative_to(WS)),
        "sha256": H[str(report)],
        "bytes": report.stat().st_size,
        "validation_status": "unverified",
        "summary": (
            "Independent live-truth check of the R2 consistency-evidence repair: 8/8 checks pass. Restored "
            "675a99d0 document is still true of live inputs; patched checker deterministic and non-clobbering; "
            "residual W038-R2LT-F1 = uncompared-field drift is invisible to both checkers. Worker evidence only."
        ),
        "falsifier": FALSIFIER,
        "evidence_refs": EVID,
    },
    {
        "event_id": f"w038-r2lt-artifact-instrument-{stamp}",
        "event_type": "artifact",
        "created_at": now,
        "actor": "worker-038",
        "artifact_type": "r2_livetruth_instrument",
        "node_id": "F1,F2a,F2b",
        "node_ids": ["F1", "F2a", "F2b"],
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": CLASSES,
        "gate": "G-FORM",
        "path": str(tool.relative_to(WS)),
        "sha256": H[str(tool)],
        "validation_status": "unverified",
        "summary": (
            "Deterministic re-runnable instrument: mirrored-sandbox canonical vs patched checker runs, "
            "compared-field sensitivity control, uncompared-field drift probe, timestamp-order check, and a "
            "9-file canonical guard hashed before/after. Exit 0 all pass / 1 expectation failed / 2 harness error."
        ),
        "falsifier": FALSIFIER,
        "evidence_refs": EVID,
    },
    {
        "event_id": f"w038-r2lt-claim-{stamp}",
        "event_type": "claim",
        "created_at": now,
        "actor": "worker-038",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": CLASSES,
        "gate": "G-FORM",
        "node_id": "F1,F2a,F2b",
        "conclusion_type": "formal_model",
        "statement": STATEMENT,
        "assumptions": [
            "Copying the checkers into a mirrored sandbox makes ROOT=parents[3] resolve inside the sandbox, so the "
            "canonical evidence path was never written; verified by 9 guard hashes before and after.",
            "The two restore candidates are independent preservations of the rev27-pinned bytes (worker-086 "
            "restore_candidate; worker-043 raw/evidence_restored_675a99d0.json) and were not authored by worker-038.",
            "C6's drift edit is semantically load-bearing (it changes the recorded C2 positive test case) and is not "
            "compared by the consistency checker, which tests positive_test_case only for presence.",
        ],
        "falsifier": FALSIFIER,
        "evidence_refs": EVID,
        "artifact_refs": [str(report.relative_to(WS)), str(tool.relative_to(WS))],
    },
    review,
    {
        "event_id": f"w038-r2lt-status-{stamp}",
        "event_type": "status",
        "created_at": now,
        "actor": "worker-038",
        "node_id": "F1,F2a,F2b",
        "node_ids": ["F1", "F2a", "F2b"],
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": CLASSES,
        "gate": "G-FORM",
        "status": "active",
        "hours": 0.6,
        "summary": (
            "W038-GFORM-R2LIVETRUTH-01 complete: independently reproduced worker-043's R2 reconstruction and "
            "durability, and added the live-truth check (restored document still true of current inputs), the "
            "embedded-hash check, and the drift-visibility probe (W038-R2LT-F1: uncompared-field edits leave both "
            "checkers at exit 0 while the pinned document's embedded lead_contract_sha256 goes stale). No canonical "
            "write, no gate verdict, no completion claim."
        ),
        "evidence_refs": EVID,
        "next_falsifier": FALSIFIER,
        "falsifier": FALSIFIER,
    },
]

for e in events:
    validate_event(e)

with open(OUTBOX, "a") as f:
    for e in events:
        f.write(json.dumps(e, sort_keys=True) + "\n")

ckpt = {
    "worker": "worker-038",
    "task_id": "W038-GFORM-R2LIVETRUTH-01",
    "checkpoint_at": now,
    "gate": "G-FORM",
    "node_id": "F1,F2a,F2b",
    "node_ids": ["F1", "F2a", "F2b"],
    "class_id": "AF-WCC-VAC-GEN",
    "class_ids": CLASSES,
    "artifact": str(report.relative_to(WS)),
    "artifact_sha256": H[str(report)],
    "instrument": {"path": str(tool.relative_to(WS)), "sha256": H[str(tool)]},
    "readme": {"path": str(readme.relative_to(WS)), "sha256": H[str(readme)]},
    "raw_run": {"path": str(Path(raw).relative_to(WS)), "sha256": H[raw]},
    "verdict": "accept",
    "score_0_5": 3.5,
    "counts_as_full_schema_verdict": False,
    "blind_to_artifact_lineage": False,
    "checks_passed": 8,
    "checks_total": 8,
    "canonical_drift": {},
    "residual_findings": ["W038-R2LT-F1 uncompared-field drift is invisible to both checkers",
                          "W038-R2LT-F2 checked_at 00:31:41 precedes restored measured_at 00:32:02"],
    "event_ids": [e["event_id"] for e in events],
    "next_falsifier": FALSIFIER,
}
CKPT.write_text(json.dumps(ckpt, indent=1) + "\n")

print(json.dumps({"outbox": str(OUTBOX.relative_to(WS)), "checkpoint": str(CKPT.relative_to(WS)),
                  "event_ids": ckpt["event_ids"], "artifact_sha256": ckpt["artifact_sha256"],
                  "instrument_sha256": ckpt["instrument"]["sha256"]}, indent=1))
