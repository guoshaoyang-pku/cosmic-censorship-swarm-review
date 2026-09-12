#!/usr/bin/env python3
"""W090 finalize: emit the FROZEN-rev26 adjudication review, outbox events, checkpoint.

Refuses to write if the audited bytes moved after the audit ran (freeze rule).
Inputs : artifacts/worker-090/f0_rev26_adjudication/report.json
Outputs: reviews/F0-rev26-adjudication-090.json
         comms/outbox/worker-090.jsonl            (appended: artifact x3, review, status)
         runtime/state/w090_checkpoint_2.json
         runtime/state/w090_checkpoints.jsonl     (appended)
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
REPORT = HERE / "report.json"
SCRIPT = HERE / "audit_f0_rev26.py"
README = HERE / "README.md"
REVIEW = ROOT / "reviews/F0-rev26-adjudication-090.json"
OUTBOX = ROOT / "comms/outbox/worker-090.jsonl"
CHECKPOINT = ROOT / "runtime/state/w090_checkpoint_2.json"
CKPT_LOG = ROOT / "runtime/state/w090_checkpoints.jsonl"
CST = timezone(timedelta(hours=8))


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def ref(p: Path, h: str | None = None) -> str:
    return f"{p.relative_to(ROOT)}#{(h or sha256(p))[:12]}"


def main() -> int:
    report = json.loads(REPORT.read_text())
    frozen_path = ROOT / report["reviewed"]["frozen_path"]
    frozen_now = sha256(frozen_path)
    guard = {
        "frozen_declared": report["reviewed"]["frozen_sha256"],
        "frozen_measured_at_finalize": frozen_now,
        "stable": frozen_now == report["reviewed"]["frozen_sha256"],
    }
    if not guard["stable"]:
        print(json.dumps({"error": "FREEZE-GUARD: FROZEN.json moved since audit", **guard}))
        return 3

    ts = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    measured = {
        "report": sha256(REPORT),
        "script": sha256(SCRIPT),
        "readme": sha256(README),
    }

    findings = [
        {"id": "W090R26-01", "kind": "positive",
         "text": "Rev26 two-artifact claim SUPPORTED: disjoint role keys (canonical {class_ids,classes}; supplement {class_contracts,frozen_classes,axis_registry,implication_ledger}), identical four frozen class ids, and all three class_contract_pointers resolve only in the supplement.",
         "evidence": ["artifacts/worker-090/f0_rev26_adjudication/report.json", "research_map/formulation_taxonomy.yaml", "artifacts/formulation/formulation_taxonomy.yaml"]},
        {"id": "W090R26-02", "kind": "positive",
         "text": "FROZEN rev26 manifest is clean against disk: 40/40 files pins match sha256 and byte counts, both logical_artifacts pins match, frozen_at 00:24:49 is behind wall clock (rev25 future-dated manifest clock corrected).",
         "evidence": ["artifacts/formulation/FROZEN.json#2554e276a0db", "artifacts/worker-090/f0_rev26_adjudication/report.json"]},
        {"id": "W090R26-03", "kind": "positive",
         "text": "All three schemas' f0_binding declares the measured canonical F0 (276009f4) and the measured supplement (c8e979a1); schemas/taxonomy_cases.jsonl is the only corpus still off the declared F0.",
         "evidence": ["schemas/af_wcc_vacuum.yaml#9a8bd4c96800", "schemas/af_scc_c2_vacuum.yaml#b6123750b37d", "schemas/af_scc_c0_vacuum.yaml#1bb78ce9b357"]},
        {"id": "W090R26-04", "kind": "defect",
         "text": "Clock discipline not closed at rev26: effective revised_at = 00:30:00 and f0_binding.checked_at = 00:30:00 in all three canonical schemas, ahead of wall clock; the prose 'corrected to mtime' does not match the machine-readable fields.",
         "evidence": ["artifacts/worker-090/f0_rev26_adjudication/report.json#checks.C2b", "artifacts/worker-090/f0_rev26_adjudication/report.json#checks.C6b"]},
        {"id": "W090R26-05", "kind": "defect",
         "text": "Duplicate top-level keys survive: revised_at 7x (6 duplicates, PyYAML last-wins) plus revised_at_unused in each schema, and revised_at 5x in the supplement artifacts/formulation/formulation_taxonomy.yaml.",
         "evidence": ["artifacts/worker-090/f0_rev26_adjudication/report.json#checks.C8"]},
        {"id": "W090R26-06", "kind": "defect",
         "text": "schemas/taxonomy_cases.jsonl still binds F0 565a6e50/72d12c83, not the declared canonical 276009f4 (owned by astra-life03-repin-claims); schemas/f1_falsifier_tests.jsonl is current at F1 9a8bd4c9.",
         "evidence": ["schemas/taxonomy_cases.jsonl#b9699119bbab", "schemas/f1_falsifier_tests.jsonl#c4c477adcb7a"]},
        {"id": "W090R26-07", "kind": "context",
         "text": "WARN: the two F0 artifacts use different conclusion-type vocabularies (strong_cosmic_censorship_C0 vs scc_c0_future_inextendibility). Normalized comparison finds no contradiction under the mapping declared in the script, but no shared machine-readable vocabulary exists across the two artifacts.",
         "evidence": ["artifacts/worker-090/f0_rev26_adjudication/report.json#checks.C4c"]},
        {"id": "W090R26-08", "kind": "context",
         "text": "Policy question left to the controller: the rev26 measurements support 'two different artifacts' (REC-1), while the canonical-path policy still requires byte-identical publication before verdicts bind. This audit measures bytes and does not adjudicate REC-1 vs REC-2.",
         "evidence": ["artifacts/formulation/FROZEN.json#2554e276a0db", "artifacts/formulation/evidence/f0_mirror_conflict.json"]},
    ]
    hard_failures = [
        {"id": "HF090-26-01", "name": "future_dated_machine_timestamps", "severity": "major",
         "detail": "effective revised_at and f0_binding.checked_at are 00:30:00 in all three canonical schemas, ahead of the 00:27:23 wall clock at measurement; timestamp_provenance prose says corrected to mtime.",
         "measured": {"revised_at": "2026-09-12T00:30:00+08:00", "checked_at": "2026-09-12T00:30:00+08:00", "wall_clock_at_audit": report["emitted_at"]}},
        {"id": "HF090-26-02", "name": "duplicate_yaml_keys", "severity": "major",
         "detail": "duplicate top-level revised_at (6 duplicates per schema) and revised_at_unused in the schemas; revised_at 5x in the class-contract supplement.",
         "measured": {"schemas": {"af_wcc_vacuum": {"revised_at": 6, "revised_at_unused": 1}, "af_scc_c2_vacuum": {"revised_at": 7}, "af_scc_c0_vacuum": {"revised_at": 7}}, "supplement": {"revised_at": 5}}},
        {"id": "HF090-26-03", "name": "stale_downstream_pin_taxonomy_cases", "severity": "minor",
         "detail": "schemas/taxonomy_cases.jsonl binds F0 565a6e50/72d12c83 instead of the declared canonical 276009f4; assigned to astra-life03-repin-claims.",
         "measured": {"pins": ["565a6e505188d6c2", "72d12c8399c1ffb6"], "declared_f0": report["reviewed"]["canonical_f0"]["sha256"][:16]}},
    ]

    review = {
        "review_id": "RV-090-F0-REV26-001",
        "target_id": "F0:FROZEN.json#rev26",
        "target_artifact": "artifacts/formulation/FROZEN.json",
        "reviewed_sha256": report["reviewed"]["frozen_sha256"],
        "reviewed_revision": report["reviewed"]["frozen_revision"],
        "reviewed_hashes": report["reviewed"],
        "class_id": report["class_id"],
        "node_id": "F0",
        "reviewer": "worker-090",
        "reviewer_role": "bounded execution worker (independent; not an author of F0, FROZEN.json, or the schemas)",
        "verdict": report["verdict"],
        "score": 3.5,
        "created_at": now(),
        "rev26_claim_supported_by_bytes": report["rev26_claim_supported_by_bytes"],
        "findings": findings,
        "hard_failures": hard_failures,
        "warnings": report["warnings"],
        "artifact_refs": [
            ref(REPORT), ref(SCRIPT), ref(README),
        ],
        "evidence_refs": [
            ref(ROOT / "artifacts/formulation/FROZEN.json"),
            ref(ROOT / "research_map/formulation_taxonomy.yaml"),
            ref(ROOT / "artifacts/formulation/formulation_taxonomy.yaml"),
            ref(ROOT / "schemas/af_wcc_vacuum.yaml"),
            ref(ROOT / "schemas/af_scc_c2_vacuum.yaml"),
            ref(ROOT / "schemas/af_scc_c0_vacuum.yaml"),
            ref(ROOT / "schemas/taxonomy_cases.jsonl"),
            ref(ROOT / "schemas/f1_falsifier_tests.jsonl"),
        ],
        "method": "Mechanical hash-bound measurement: FROZEN files-map vs disk, logical_artifacts pins, frozen_at vs wall clock, key-set/class-id/content comparison of the two F0 artifacts with a declared conclusion-type normalization, pointer fragment resolution in both trees, f0_binding declared-vs-measured, downsteam corpus pin scan, duplicate-key compose-tree scan, effective last-wins timestamp check. No network, no map mutation, no edits to reviewed artifacts.",
        "next_falsifier": report["next_falsifier"],
        "reproduction": report["reproduction"],
        "freeze_guard": guard,
        "authority_note": "Worker verdict is advisory evidence only. Per ASTRA_HANDOFF, worker events cannot set status=done, validation_status=passed, or a gate verdict; the controller/leads decide with artifact + review evidence.",
    }
    REVIEW.write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n")

    review_sha = sha256(REVIEW)
    events = []
    for art_type, p in (("adjudication_report", REPORT), ("adjudication_script", SCRIPT),
                        ("adjudication_readme", README)):
        events.append({
            "event_id": f"w090-rev26-{ts}-artifact-{art_type}",
            "event_type": "artifact",
            "actor": "worker-090",
            "created_at": now(),
            "node_id": "F0",
            "class_id": report["class_id"],
            "artifact_type": art_type,
            "path": str(p.relative_to(ROOT)),
            "sha256": sha256(p),
            "validation_status": "unverified",
            "gate": "G-F0",
            "evidence_refs": [ref(ROOT / "artifacts/formulation/FROZEN.json"), ref(p)],
            "falsifier": report["next_falsifier"],
        })
    events.append({
        "event_id": f"w090-rev26-{ts}-review",
        "event_type": "review",
        "actor": "worker-090",
        "created_at": now(),
        "node_id": "F0",
        "class_id": report["class_id"],
        "target_id": "F0:FROZEN.json#rev26",
        "reviewer": "worker-090",
        "verdict": report["verdict"],
        "score": 3.5,
        "gate": "G-F0",
        "hard_failures": [h["name"] for h in hard_failures],
        "findings": [f["id"] for f in findings],
        "artifact_refs": [str(REVIEW.relative_to(ROOT))],
        "evidence_refs": [ref(REVIEW, review_sha), ref(ROOT / "artifacts/formulation/FROZEN.json")],
        "next_falsifier": report["next_falsifier"],
        "authority_note": "advisory worker verdict; cannot set gate verdict or node status",
    })
    events.append({
        "event_id": f"w090-rev26-{ts}-status",
        "event_type": "status",
        "actor": "worker-090",
        "created_at": now(),
        "node_id": "F0",
        "class_id": report["class_id"],
        "status": "active",
        "hours": 0.3,
        "summary": "Independent FROZEN rev26 audit: two-artifact claim supported (40/40 manifest pins match, same 4 class ids, pointers resolve only in supplement); closure blocked by future-dated machine timestamps, duplicate revised_at keys, and the stale taxonomy_cases pin. Advisory revise.",
        "evidence_refs": [ref(REVIEW, review_sha), ref(REPORT), ref(ROOT / "artifacts/formulation/FROZEN.json")],
        "next_falsifier": report["next_falsifier"],
    })
    with OUTBOX.open("a") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    ckpt = {
        "checkpoint_id": f"w090-ckpt2-{ts}",
        "worker": "worker-090",
        "at": now(),
        "task": "W090-F0-REV26 independent audit of FROZEN.json revision 26 two-artifact adjudication claim",
        "node_id": "F0",
        "class_id": report["class_id"],
        "status": "complete",
        "reviewed": report["reviewed"],
        "measured": measured,
        "verdict": report["verdict"],
        "claim_supported": report["rev26_claim_supported_by_bytes"],
        "hard_failures": [h["id"] for h in hard_failures],
        "artifacts": [str(REVIEW.relative_to(ROOT)), str(REPORT.relative_to(ROOT)),
                      str(SCRIPT.relative_to(ROOT)), str(README.relative_to(ROOT))],
        "events_emitted": [e["event_id"] for e in events],
        "outbox": str(OUTBOX.relative_to(ROOT)),
        "freeze_guard": guard,
        "next_falsifier": report["next_falsifier"],
    }
    CHECKPOINT.write_text(json.dumps(ckpt, indent=2, ensure_ascii=False) + "\n")
    with CKPT_LOG.open("a") as f:
        f.write(json.dumps(ckpt, ensure_ascii=False) + "\n")

    print(json.dumps({
        "review": str(REVIEW.relative_to(ROOT)),
        "review_sha256": review_sha,
        "verdict": report["verdict"],
        "claim_supported": report["rev26_claim_supported_by_bytes"],
        "hard_failures": [h["name"] for h in hard_failures],
        "events": [e["event_id"] for e in events],
        "checkpoint": str(CHECKPOINT.relative_to(ROOT)),
        "freeze_guard": guard["stable"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
