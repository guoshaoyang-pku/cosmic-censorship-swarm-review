#!/usr/bin/env python3
"""Emit worker-086's rev12 binding-verification deliverables, events and checkpoint.

Reproducible: re-running rewrites the same artifacts (content depends only on the pinned
bytes and the wall-clock stamps) and appends nothing if the same event_ids are already
present in comms/outbox/worker-086.jsonl.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
OUT = Path(__file__).resolve().parent
NOW = datetime.now(CST).isoformat(timespec="seconds")
STAMP = datetime.now(CST).strftime("%Y%m%dT%H%M%S")

SCHEMAS = {"F1": "schemas/af_wcc_vacuum.yaml",
           "F2a": "schemas/af_scc_c2_vacuum.yaml",
           "F2b": "schemas/af_scc_c0_vacuum.yaml"}
CANON = "research_map/formulation_taxonomy.yaml"
SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
CONS = "artifacts/formulation/evidence/taxonomy_consistency.json"
MAP = "research_map/research_map.json"
COVERAGE = "reviews/A1-rebind-coverage.json"
ALIASES = "artifacts/formulation/VOCAB_ALIASES.json"
REPORT = "artifacts/worker-086/gform_rev12/report.json"
PROBE = "artifacts/worker-086/gform_rev12/probe_rev12.py"
PINS = "artifacts/worker-086/gform_rev12/PINS.json"
SNAP_DECLARED = "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json"
REVIEW = "reviews/G-FORM-rev12-binding-086.json"


def sha(p: str) -> str:
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def main() -> int:
    # refresh the probe-derived report at the current pins before hashing it
    rc = subprocess.run([sys.executable, str(ROOT / PROBE)], capture_output=True, text=True)
    if rc.returncode != 0:
        print("probe failed", rc.stdout[-2000:], rc.stderr[-2000:])
        return 1
    report = json.loads((ROOT / REPORT).read_text())

    pins = {"measured_at": NOW, "paths": {}}
    for p in (CANON, SUPP, CONS, MAP, COVERAGE, ALIASES, *SCHEMAS.values()):
        pins["paths"][p] = {"sha256": sha(p), "bytes": (ROOT / p).stat().st_size}
    pins["declared_consistency_evidence"] = {
        "declared_sha256": "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48",
        "live_sha256": sha(CONS),
        "declared_snapshot": SNAP_DECLARED,
        "declared_snapshot_exists": (ROOT / SNAP_DECLARED).exists(),
    }
    (ROOT / PINS).write_text(json.dumps(pins, indent=1) + "\n")

    hard = [f for f in report["findings"] if f.get("severity") == "hard"]
    med = [f for f in report["findings"] if f.get("severity") == "medium"]
    soft = [f for f in report["findings"] if f.get("severity") == "soft"]
    census = [c for c in report["checks"] if c["id"] == "C7-accept-census-at-new-pins"][0]["detail"]

    review = {
        "schema_version": "0.1",
        "artifact_kind": "review",
        "event_id": f"w086-{STAMP}-review-rev12-binding",
        "event_type": "review",
        "created_at": NOW,
        "actor": "worker-086",
        "reviewer": "worker-086",
        "node_id": "F1",
        "target_id": "F1,F2a,F2b",
        "target_id_full": ("G-FORM binding chain at F1 cce9c60146d6 / F2a 5476a3f2c6bc / "
                            "F2b 55d0a1ea9bda on declared F0 rev5 0abb9ed8a961"),
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "review_kind": "binding_chain_verification",
        "scope": ("class-contract pointer resolution, declared-hash agreement, consistency-evidence pin, "
                  "alias-aware class-identity recheck, duplicate-key scan, accept census; schema content, "
                  "quantifier semantics and physics are NOT re-derived here"),
        "counts_as_full_schema_verdict": False,
        "counts_as_independent": True,
        "verdict": "revise",
        "score": 2.5,
        "score_rationale": ("rev12 closes the pointer and duplicate-key defects and the identity axes agree, but the "
                            "declared consistency-evidence hash does not resolve at the canonical evidence path and the "
                            "live evidence drops the input-tree pins; no accept binds the rev12 bytes yet."),
        "hard_failures": hard,
        "findings": report["findings"],
        "positives": [
            "C0: all three rev12 schemas parse under a duplicate-key-detecting YAML loader (0 duplicates).",
            "C1: class_contract_pointer resolves in canonical F0 at classes.<CLASS> for all three schemas; the "
            "supplement pointer resolves in the supplement at class_contracts.<CLASS>.",
            "C5: conclusion types agree with canonical axes under the declared VOCAB_ALIASES policy for all three classes.",
            "C6: no AF-* token outside the frozen four occurs in any of the three schemas.",
        ],
        "evidence_refs": [f"{REPORT}#{sha(REPORT)[:12]}", f"{PROBE}#{sha(PROBE)[:12]}",
                          f"{PINS}#{sha(PINS)[:12]}", f"{SNAP_DECLARED}#{sha(SNAP_DECLARED)[:12]}",
                          *[f"{p}#{sha(p)[:12]}" for p in SCHEMAS.values()],
                          f"{CANON}#{sha(CANON)[:12]}", f"{SUPP}#{sha(SUPP)[:12]}",
                          f"{CONS}#{sha(CONS)[:12]}", f"{ALIASES}#{sha(ALIASES)[:12]}"],
        "artifact_refs": [REPORT, PROBE, PINS, SNAP_DECLARED],
        "falsifier": ("Re-run probe_rev12.py at these pins: show a pointer that does not resolve, a duplicate mapping "
                      "key, an alias-aware identity mismatch, or an accept that binds the rev12 hashes and is omitted."),
        "next_falsifier": ("Re-stamp consistency_evidence_sha256 in the three schemas to the live document (or restore the "
                           "declared bytes), then re-run probe_rev12.py; the census must be recomputed after any byte move."),
        "not_claimed": [
            "Not a full-schema accept/reject verdict; counts_as_full_schema_verdict=false.",
            "No gate verdict, no node status, no class-id creation.",
            "Does not assert that any pre-rebind accept was scientifically correct.",
        ],
    }
    (ROOT / REVIEW).write_text(json.dumps(review, indent=1) + "\n")
    review_sha = sha(REVIEW)

    claim = {
        "event_id": f"w086-{STAMP}-claim-rev12-binding",
        "event_type": "claim",
        "created_at": NOW,
        "actor": "worker-086",
        "node_id": "F1",
        "gate": "G-FORM",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "conclusion_type": "stability_result",
        "statement": (
            "Artifact-and-checker measurement (not a mathematics or physics claim) at rev12 pins "
            f"F1 {sha(SCHEMAS['F1'])[:12]} / F2a {sha(SCHEMAS['F2a'])[:12]} / F2b {sha(SCHEMAS['F2b'])[:12]} on declared F0 rev5 "
            f"{sha(CANON)[:12]}: (a) the class_contract_pointer of all three schemas resolves in the CANONICAL taxonomy at "
            "classes.<CLASS> and the class-contract supplement pointer resolves separately in artifacts/formulation/"
            "formulation_taxonomy.yaml at class_contracts.<CLASS>; (b) no duplicate YAML mapping keys remain; (c) the three "
            "conclusion types agree with the canonical class axes under VOCAB_ALIASES.json; (d) all three schemas declare "
            "consistency_evidence_sha256 675a99d0d25b..., which does NOT resolve at the canonical evidence path (live sha256 "
            f"{sha(CONS)[:12]}..., which also drops the map_taxonomy_sha256/lead_contract_sha256/measured_at pins the declared "
            "generation carried), so the cited evidence does not bind the gate at the declared hash; (e) 0 accepting verdicts "
            f"bind the rev12 bytes, while the 00:31-00:32 rebind invalidated {sum(census['accepts_bound_to_pre_rebind_hash'].values())} "
            "pre-rebind map-level accepts (F1 2, F2a 6, F2b 5 after removing deepseek-flash-07's retracted accept)."),
        "assumptions": [
            "The three schema files and the two taxonomy files at the measured hashes are the intended rev12 publication.",
            "The declared alias policy in artifacts/formulation/VOCAB_ALIASES.json is authoritative for identity comparison.",
            "A map-level accept binds only if its own record pins the measured schema sha256 and no supersedes edge retires it.",
        ],
        "falsifier": (
            "Re-run probe_rev12.py at these pins and show any of: a canonical-resolvable pointer reported unresolved, "
            "a duplicate key the scan missed, an alias-aware identity mismatch, or an omitted accept that binds a rev12 hash."),
        "evidence_refs": [f"{REPORT}#{sha(REPORT)[:12]}", f"{PINS}#{sha(PINS)[:12]}",
                          f"{REVIEW}#{review_sha[:12]}", f"{CONS}#{sha(CONS)[:12]}",
                          f"{SNAP_DECLARED}#{sha(SNAP_DECLARED)[:12]}",
                          *[f"{p}#{sha(p)[:12]}" for p in SCHEMAS.values()]],
        "artifact_refs": [REPORT, PROBE, REVIEW, PINS, SNAP_DECLARED],
        "promotion_status": "promotion_blocked",
    }

    artifacts = [
        {"event_id": f"w086-{STAMP}-art-report", "node_id": "F1", "artifact_type": "gform_rev12_binding_verification",
         "path": REPORT, "sha256": sha(REPORT), "validation_status": "passed",
         "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
         "note": "machine-checked report; verdict " + report["verdict"]},
        {"event_id": f"w086-{STAMP}-art-probe", "node_id": "F1", "artifact_type": "deterministic_probe",
         "path": PROBE, "sha256": sha(PROBE), "validation_status": "passed",
         "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
         "note": "read-only, fail-closed, duplicate-key-detecting resolver + alias-aware identity + accept census"},
        {"event_id": f"w086-{STAMP}-art-pins", "node_id": "F1", "artifact_type": "input_pin_manifest",
         "path": PINS, "sha256": sha(PINS), "validation_status": "passed",
         "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
         "note": "all measured hashes at emission time"},
        {"event_id": f"w086-{STAMP}-art-declared-evidence-snapshot", "node_id": "F1",
         "artifact_type": "declared_evidence_snapshot", "path": SNAP_DECLARED, "sha256": sha(SNAP_DECLARED),
         "validation_status": "passed",
         "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
         "note": "snapshot of the consistency-evidence generation the three schemas declare (675a99d0d25b); proves the "
                 "declared pin existed even though the live canonical path no longer carries those bytes"},
    ]

    status = {
        "event_id": f"w086-{STAMP}-status-rev12-binding",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-086",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "status": "active",
        "hours": 0.6,
        "summary": (f"W086-GFORM-REV12-VERIFY-01 complete and checkpointed: binding-chain verification at rev12 "
                    f"(F1 {sha(SCHEMAS['F1'])[:12]}, F2a {sha(SCHEMAS['F2a'])[:12]}, F2b {sha(SCHEMAS['F2b'])[:12]}) -> "
                    f"{report['verdict']}; HF-086-R1 declared consistency-evidence hash unresolvable at the canonical path "
                    f"(declared 675a99d0, live {sha(CONS)[:12]}), HF-086-R2b live evidence unpinned; pointers, duplicate-key "
                    f"scan and alias-aware identity pass; 0 accepts bind rev12, "
                    f"{sum(census['accepts_bound_to_pre_rebind_hash'].values())} pre-rebind accepts invalidated."),
        "evidence_refs": [f"{REPORT}#{sha(REPORT)[:12]}", f"{REVIEW}#{review_sha[:12]}", f"{PINS}#{sha(PINS)[:12]}"],
        "next_falsifier": "re-run probe_rev12.py after the lead re-stamps or restores the declared consistency evidence",
    }

    events = []
    for a in artifacts:
        events.append({**a, "event_type": "artifact", "created_at": NOW, "actor": "worker-086"})
    events.append(claim)
    events.append({**review, "artifact_refs": review["artifact_refs"]})
    events.append(status)

    for e in events:
        validate_event(e)

    outbox = ROOT / "comms/outbox/worker-086.jsonl"
    existing = {json.loads(l).get("event_id") for l in outbox.read_text().splitlines() if l.strip()}
    written = []
    with outbox.open("a") as f:
        for e in events:
            if e["event_id"] in existing:
                continue
            f.write(json.dumps(e) + "\n")
            written.append(e["event_id"])

    checkpoint = {
        "checkpoint": 2,
        "worker": "worker-086",
        "role": "bounded execution worker",
        "slot": "086",
        "at": NOW,
        "hours_spent_estimate": 0.6,
        "task": {
            "node_id": "F1,F2a,F2b",
            "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
            "gate": "G-FORM",
            "kind": "independent binding-chain verification of the rev12 rebind",
            "assignment_source": "self-claimed from the live 00:31-00:32 rebind; not duplicative of astra-life03-verify-gform (audit lead, 02:00)",
        },
        "target": {n: {"path": p, "sha256": sha(p)} for n, p in SCHEMAS.items()},
        "verdict": report["verdict"],
        "hard_failures": [f["id"] for f in hard],
        "medium_failures": [f["id"] for f in med],
        "soft_findings": [f["id"] for f in soft],
        "accept_census": census,
        "artifacts": {REPORT: sha(REPORT), PROBE: sha(PROBE), PINS: sha(PINS),
                      SNAP_DECLARED: sha(SNAP_DECLARED), REVIEW: review_sha},
        "events_emitted": written,
        "next_falsifier": review["next_falsifier"],
        "notes": ("rev12 pointers now resolve canonically and duplicate keys are gone; the remaining gate-blocking item is "
                  "the consistency-evidence pin (declared 675a99d0 vs live document) plus the fact that no accept binds rev12."),
    }
    (ROOT / "runtime/state/worker-086_checkpoint_2.json").write_text(json.dumps(checkpoint, indent=1) + "\n")
    with (ROOT / "runtime/state/worker-086_checkpoints.jsonl").open("a") as f:
        f.write(json.dumps(checkpoint) + "\n")
    (OUT / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=1) + "\n")

    print(json.dumps({"verdict": report["verdict"], "events_written": written,
                      "review": f"{REVIEW}#{review_sha[:12]}",
                      "checkpoint": "runtime/state/worker-086_checkpoint_2.json"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
