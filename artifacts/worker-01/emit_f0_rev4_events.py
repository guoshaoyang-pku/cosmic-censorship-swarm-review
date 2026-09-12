#!/usr/bin/env python3
"""Emit the F0 rev4 staged-patch protocol events and checkpoint (worker-01 / deepseek-flash-01).

Appends exactly two JSON lines to comms/outbox/deepseek-flash-01.jsonl (artifact, status),
writes artifacts/worker-01/checkpoints/ckpt-8.json, then re-parses the whole outbox.
Authority limits honoured: no status=done, no validation_status=passed, no gate verdict.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "artifacts" / "worker-01"
OUTBOX = ROOT / "comms" / "outbox" / "deepseek-flash-01.jsonl"
CKPT = W / "checkpoints" / "ckpt-8.json"
CST = timezone(timedelta(hours=8))


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ts = datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S%z")
    delta = W / "F0_rev4_delta.json"
    cand = W / "f0_rev4_candidate.yaml"
    val = W / "f0_rev4_validation.json"
    con = W / "f0_rev4_consistency_report.json"
    log = W / "f0_rev4_check_run.log"
    canon = ROOT / "research_map" / "formulation_taxonomy.yaml"

    h_delta, h_cand, h_val, h_con, h_log, h_canon = map(
        sha_file, (delta, cand, val, con, log, canon)
    )
    EXPECT_CANON = "565a6e505188d6c28050500924b9b66b1440a4c9b069567c772f414f19e02800"
    if h_canon != EXPECT_CANON:
        print(f"REFUSING: canonical changed since staging: {h_canon} != {EXPECT_CANON}")
        return 2
    class_ids = json.loads(delta.read_text())["class_ids"]

    artifact_ev = {
        "event_id": "w01-F0-rev4-artifact-86041a8c",
        "event_type": "artifact",
        "created_at": ts,
        "actor": "deepseek-flash-01",
        "node_id": "F0",
        "gate": "G-F0",
        "artifact_type": "f0_rev4_revision_delta",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": class_ids,
        "path": "artifacts/worker-01/F0_rev4_delta.json",
        "sha256": h_delta,
        "validation_status": "unverified",
        "evidence_refs": [
            f"research_map/formulation_taxonomy.yaml#{h_canon[:12]}",
            f"artifacts/worker-01/f0_rev4_candidate.yaml#{h_cand[:12]}",
            f"artifacts/worker-01/f0_rev4_validation.json#{h_val[:12]}",
            f"artifacts/worker-01/f0_rev4_consistency_report.json#{h_con[:12]}",
            f"artifacts/worker-01/f0_rev4_check_run.log#{h_log[:12]}",
            "artifacts/formulation/tools/check_taxonomy_consistency.py"
            "#de356d999ea3b6aeb9cfe7d35d6604328ccc4945ead3bc3ec566a929363f31cd",
        ],
        "note": (
            "STAGED rev4 revision-record patch for the declared F0 artifact (not applied; the "
            "lead-formulation publish cycle is active on the canonical file). It records the "
            "astra-classscope-02 amendment as revision 4 (F0R-01), replaces the prose "
            "supersedes.wcc_text_sha256_before with the real pre-amendment artifact hash "
            "66bf917b...c232 (F0R-02), and separates observed from declared adjudication times "
            "(F0R-04). Candidate sha256 d8201424: validate_taxonomy 253/253 (canonical control "
            "253/253; validator self-test 6/6), frozen consistency tool de356d99 CONSISTENT on "
            "both control and candidate, reverse-apply control reproduces the canonical bytes "
            "exactly. Downstream pins requiring refresh on apply are enumerated in the artifact "
            "(three schemas' f0_binding, schemas/taxonomy_cases.jsonl meta, map gate record, "
            "consistency evidence re-run). No class text, axis, disjointness row, transfer rule "
            "or guard is changed."
        ),
    }
    status_ev = {
        "event_id": "w01-F0-rev4-status-86041a8c",
        "event_type": "status",
        "created_at": ts,
        "actor": "deepseek-flash-01",
        "node_id": "F0",
        "gate": "G-F0",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": class_ids,
        "status": "active",
        "hours": 0.7,
        "claims_completion": False,
        "summary": (
            "F0 rev4 staged, not applied. TEXT VERDICT: the lead's D1/D3 amendment request is "
            "textually satisfied at canonical 565a6e50 (single-q tail predicate in the "
            "AF-WCC-VAC-GEN conclusion, D2 cleared, explicit comeager quantifier in the three "
            "vacuum classes) and the frozen consistency tool reports CONSISTENT (4 classes, 0 "
            "contract-text divergences) on both the canonical control and the rev4 candidate. "
            "RECORD VERDICT: the amendment was never given a revision number (revision still 3, "
            "written_at 23:34) and carried a mislabeled supersedes value and a forward-dated "
            "decided_at; rev4 fixes exactly those without semantic change. F0R-05 remains open "
            "for the lead: AF-WCC-SCALAR-SPH still uses the SET-based 'contained in J-(I+)' "
            "phrasing while the adjudication declares one canonical single-q predicate; I did not "
            "edit it because D1 was scoped to AF-WCC-VAC-GEN and it is a semantic change. Apply "
            "artifacts/worker-01/f0_rev4.diff to the canonical bytes, then refresh the pins "
            "listed in the delta before any G-F0 verdict."
        ),
        "evidence_refs": [
            f"artifacts/worker-01/F0_rev4_delta.json#{h_delta[:12]}",
            f"artifacts/worker-01/f0_rev4_candidate.yaml#{h_cand[:12]}",
            f"artifacts/worker-01/f0_rev4_validation.json#{h_val[:12]}",
            f"artifacts/worker-01/f0_rev4_consistency_report.json#{h_con[:12]}",
            f"artifacts/worker-01/f0_rev4_check_run.log#{h_log[:12]}",
            f"research_map/formulation_taxonomy.yaml#{h_canon[:12]}",
            "comms/inbox/deepseek-flash-01.jsonl"
            "#leadform-f0-amendment-request-2026-09-11T23:54:36+08:00",
        ],
        "next_falsifier": (
            "Apply the staged diff: an applied sha256 other than "
            "d820142476f5c9eb392ec74f05cb5542b2f8026a5f1e07de1771baadfe2d4e27 voids the staged "
            "hash; INCONSISTENT output from the frozen consistency tool, any reappearing D1/D3 "
            "divergence, or any validate_taxonomy failure on the applied bytes refutes this delta; "
            "a published rev4 differing from the candidate outside the five recorded edits "
            "supersedes it and requires a re-run against the published hash. If the lead emits an "
            "accepted artifact event with a bumped revision bound to the applied hash, F0R-01, "
            "F0R-02 and F0R-04 collapse and only the downstream rebinds and F0R-05 remain."
        ),
        "to": ["astra", "astra-lead-formulation", "astra-lead-audit"],
    }

    with OUTBOX.open("a") as fh:
        for ev in (artifact_ev, status_ev):
            fh.write(json.dumps(ev, sort_keys=True) + "\n")

    # re-parse the whole outbox: every line must be valid JSON
    bad = 0
    for i, line in enumerate(OUTBOX.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            json.loads(line)
        except Exception as exc:  # pragma: no cover
            bad += 1
            print(f"BAD LINE {i}: {exc}")
    if bad:
        print(f"REFUSING checkpoint: {bad} unparseable outbox lines")
        return 2

    ckpt = {
        "checkpoint": 8,
        "time": ts,
        "worker": "deepseek-flash-01",
        "state": "rev4_candidate_staged_pending_lead_publish",
        "hashes": {
            "tax_canonical": h_canon,
            "tax_candidate": h_cand,
            "diff": sha_file(W / "f0_rev4.diff"),
            "delta": h_delta,
            "val": h_val,
            "con": h_con,
            "log": h_log,
        },
        "machine_acceptance": (
            "validate_taxonomy 253/253 on canonical control and candidate; self-test 6/6; frozen "
            "consistency tool de356d99 CONSISTENT on control and candidate; reverse-apply control "
            "byte-exact"
        ),
        "blockers": [
            "canonical write owned by the active lead-formulation publish cycle; patch staged only",
            "F0R-05 AF-WCC-SCALAR-SPH still carries the SET-based visibility phrasing (semantic, lead/F2)",
            "no reviewer verdict exists at any single hash (G-F0 unmet)",
        ],
        "next": (
            "lead applies artifacts/worker-01/f0_rev4.diff; then re-run both checkers on the applied "
            "bytes, refresh the three schemas' f0_binding, rebind schemas/taxonomy_cases.jsonl, and "
            "re-review F0 at the applied hash"
        ),
    }
    CKPT.parent.mkdir(parents=True, exist_ok=True)
    CKPT.write_text(json.dumps(ckpt, indent=2) + "\n")
    json.loads(CKPT.read_text())
    print(f"appended 2 events to {OUTBOX.relative_to(ROOT)}")
    print(f"outbox_lines = {len(OUTBOX.read_text().splitlines())}")
    print(f"checkpoint   = {CKPT.relative_to(ROOT)}")
    print(f"delta_sha256 = {h_delta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
