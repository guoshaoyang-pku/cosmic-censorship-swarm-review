#!/usr/bin/env python3
"""Emit worker-079's W079-L0-HF02-STAGED-REPAIR-VERIFY-01 events.

Fail-closed: validates every event with research_map.schemas.validate_event,
refuses duplicate event_ids, refuses artifact-hash drift, then appends to
comms/outbox/worker-079.jsonl. Writes runtime/state/w079_checkpoint_4.json and
appends the closing status event with the checkpoint hash.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from research_map.schemas import validate_event  # noqa: E402

TZ = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms/outbox/worker-079.jsonl"
CHECKPOINT = ROOT / "runtime/state/w079_checkpoint_4.json"
TASK = "W079-L0-HF02-STAGED-REPAIR-VERIFY-01"
PREFIX = "w079-20260912T0110"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
CLASS_ID = ";".join(CLASS_IDS)

ART = {
    "prereg": "artifacts/worker-079/l0_hf02_verify/PREREGISTRATION.md",
    "harness": "artifacts/worker-079/l0_hf02_verify/verify_hf02_staged_079.py",
    "report": "artifacts/worker-079/l0_hf02_verify/report.json",
    "sums": "artifacts/worker-079/l0_hf02_verify/SHA256SUMS",
    "emitter": "artifacts/worker-079/l0_hf02_verify/emit_events_079.py",
}
PINS = {
    "ledger/theorems.jsonl": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "artifacts/worker-025/l0_hf02_staged/staged/theorems.hf02-staged.jsonl": "b3ab6a1a635720a97e51fd332bcf1d9f9e6fdc45ad64d886106f1cd298d61cea",
    "evaluation_rubric.yaml": "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "schemas/taxonomy_cases.jsonl": "ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03",
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(TZ).replace(microsecond=0).isoformat()


def build_events(hashes: dict, report: dict) -> list[dict]:
    ev = []
    ev.append({
        "event_id": f"{PREFIX}-status-start",
        "event_type": "status",
        "created_at": now(),
        "actor": "worker-079",
        "node_id": "L0",
        "group_id": "literature",
        "gate": "G-LIT",
        "class_id": CLASS_ID,
        "class_ids": CLASS_IDS,
        "task_id": TASK,
        "status": "active",
        "hours": 0.05,
        "summary": ("No assignment card exists in comms/inbox/worker-079.jsonl (fleet relaunch); ONE bounded "
                    "class-bound task self-selected from the open G-LIT blocker lit-l8-20260912-006, which names "
                    "the 8-row HF-02 class_ids disjunction as the single gate-deciding question for the L0 half of "
                    "G-LIT: W079-L0-HF02-STAGED-REPAIR-VERIFY-01 = independent non-author verification of "
                    "worker-025's staged repair candidate (staged b3ab6a1a6357 vs live anchor a1674f094979). "
                    "PRE-REGISTERED before the run; read-only on every canonical path."),
        "evidence_refs": [f"ledger/theorems.jsonl#{PINS['ledger/theorems.jsonl'][:12]}",
                          "artifacts/worker-025/l0_hf02_staged/staged/theorems.hf02-staged.jsonl#b3ab6a1a6357",
                          f"evaluation_rubric.yaml#{PINS['evaluation_rubric.yaml'][:12]}",
                          ART["prereg"]],
        "next_falsifier": ("pin drift on either compared file, a ninth live row with >=2 distinct frozen class_ids "
                           "tokens, any staged non-patchable field differing from live, a foreign token or "
                           "class_ids/informs_classes overlap, or a non-empty staged disjunction set."),
    })
    for key, atype, note in [
        ("prereg", "preregistration", "checks, decision rule, control list and non-claims frozen before the run"),
        ("harness", "review_harness_failclosed", "independent read-only implementation; exit 2 pin drift / exit 3 missed control, no report"),
        ("report", "verification_report", "CANDIDATE_VERIFIED; 10/10 expectations, 6/6 controls, deterministic"),
        ("sums", "hash_manifest", "sha256 of prereg, harness and report"),
        ("emitter", "event_emitter", "validated append-only emitter for this task"),
    ]:
        ev.append({
            "event_id": f"{PREFIX}-artifact-{key}",
            "event_type": "artifact",
            "created_at": now(),
            "actor": "worker-079",
            "node_id": "L0",
            "group_id": "literature",
            "gate": "G-LIT",
            "class_id": CLASS_ID,
            "task_id": TASK,
            "artifact_type": atype,
            "path": ART[key],
            "sha256": hashes[ART[key]],
            "validation_status": "unverified",
            "counts_as_independent": True,
            "note": note,
            "evidence_refs": [f"{ART[key]}#{hashes[ART[key]][:12]}"],
        })
    ev.append({
        "event_id": f"{PREFIX}-review-hf02",
        "event_type": "review",
        "created_at": now(),
        "actor": "worker-079",
        "node_id": "L0",
        "group_id": "literature",
        "gate": "G-LIT",
        "class_id": CLASS_ID,
        "task_id": TASK,
        "target_id": "artifacts/worker-025/l0_hf02_staged/staged/theorems.hf02-staged.jsonl#b3ab6a1a6357 (L0 HF-02 disjunction repair candidate)",
        "reviewer": "worker-079",
        "reviewer_independence": ("not an author of the staged candidate, of worker-023's proposed patch, or of any "
                                  "live ledger row; worker-079's prior L0 accept at the live hash did not test the "
                                  "disjunction axis and does not substitute for this verdict"),
        "verdict": "accept",
        "score": 4.0,
        "counts_as_full_schema_verdict": False,
        "counts_as_independent": True,
        "artifact_sha256": PINS["artifacts/worker-025/l0_hf02_staged/staged/theorems.hf02-staged.jsonl"],
        "hard_failures": [],
        "findings": [
            "E1-E10 PASS at the pinned bytes: live literal HF-02 disjunction set equals the declared 8 rows "
            "(D-004, D-005, T-303, T-305, T-402, T-515, T-526, T-528); staged set is empty; 62/62 rows preserved "
            "in order; diff confined to class_ids/informs_classes/ledger_tags on exactly those 8 rows; every other "
            "row deep-equal; all staged class tokens frozen; class_ids and informs_classes disjoint on every row; "
            "tag edits append-only; no informationless row.",
            "C1-C6 PASS: reintroduced disjunction, content tamper, row loss, foreign token, ninth-row edit and "
            "live-baseline swap are all detected by the pre-registered checks; the harness writes no report on pin "
            "drift (it fired on a 63-hex-char typo in my own rubric pin before the first successful run) or on a "
            "missed control.",
            "DETERMINISM: two consecutive runs produce byte-identical report.json "
            "(sha256 975c9e2801cf06cc00a7406a45b655cd78d1580346c3c8bad89952140c4d88c2; "
            "determinism_sha256 8b94ce2cba18749879bc4f0152972577ebd01ecf430fbe755051112ec3d65f55).",
            "OBSERVATION (non-blocking, semantic, for the audit lead's scope ruling): 7 of the 8 repaired rows drop "
            "one live sibling token without re-homing it into informs_classes (D-004, D-005, T-303, T-305, T-526 "
            "drop the C2 token and keep C0 or, for T-526, keep C2 and drop C0; T-515 and T-528 drop the C0 token "
            "and keep WCC). Only T-402 carries both siblings via informs_classes. The structural invariants hold, "
            "but whether each row genuinely informs only the retained sibling is a semantic question this verdict "
            "does not decide.",
            "SCOPE: not a full-schema verdict, not an HF-02 scope ruling, not a mathematical review, not a gate "
            "verdict. The candidate is verified as a mechanical repair conditional on the audit lead ruling that "
            "HF-02's disjunction clause applies to ledger class_ids arrays.",
        ],
        "falsifier": ("At pinned live a1674f094979 and staged b3ab6a1a6357: a ninth live row with >=2 distinct frozen "
                      "class_ids tokens; any staged non-patchable field differing from live; a foreign class token or "
                      "per-row class_ids/informs_classes overlap in staged; a non-empty staged disjunction set; a "
                      "staged file that is not byte-identical to b3ab6a1a6357; or a semantic demonstration that a "
                      "retained sibling assignment is the wrong one."),
        "evidence_refs": [f"ledger/theorems.jsonl#{PINS['ledger/theorems.jsonl'][:12]}",
                          "artifacts/worker-025/l0_hf02_staged/staged/theorems.hf02-staged.jsonl#b3ab6a1a6357",
                          f"evaluation_rubric.yaml#{PINS['evaluation_rubric.yaml'][:12]}",
                          f"{ART['report']}#{hashes[ART['report']][:12]}",
                          f"{ART['harness']}#{hashes[ART['harness']][:12]}",
                          f"{ART['prereg']}#{hashes[ART['prereg']][:12]}"],
        "not_claimed": ["HF-02 scope applicability to ledger rows", "per-row semantic class assignment",
                        "mathematical content of any row", "gate verdict / node status"],
    })
    ev.append({
        "event_id": f"{PREFIX}-claim-hf02",
        "event_type": "claim",
        "created_at": now(),
        "actor": "worker-079",
        "node_id": "L0",
        "group_id": "literature",
        "gate": "G-LIT",
        "class_id": CLASS_ID,
        "class_ids": CLASS_IDS,
        "task_id": TASK,
        "conclusion_type": "numerical_evidence",
        "statement": ("Independent non-author verification at pinned hashes (live ledger a1674f094979, staged "
                      "candidate b3ab6a1a6357, rubric d748a9e3574e, taxonomy 0abb9ed8a961, taxonomy_cases "
                      "ccf7041b0dff), not a mathematical claim: the staged candidate's literal HF-02 class_ids-"
                      "disjunction set is empty where the live ledger has exactly the declared 8 rows; the diff is "
                      "confined to class_ids/informs_classes/ledger_tags on exactly those 8 rows; 62/62 rows are "
                      "preserved in order with all other fields deep-equal; every staged class token is one of the "
                      "four frozen ids and class_ids is disjoint from informs_classes on every row; report.json is "
                      "byte-deterministic across runs and all 6 pre-registered controls fire. This is evidence for "
                      "the audit lead's HF-02 scope ruling and a repin decision, not a ruling or a gate verdict."),
        "assumptions": [
            "the five pinned hashes are the artifacts of record for this window; pins were re-measured after the run and are stable",
            "the literal HF-02 reading is '>=2 distinct frozen class ids in class_ids'",
            "the staged file is a non-canonical test double; the live ledger is the anchor and is never written",
            "worker-079 is not an author of the staged candidate or of the live ledger rows",
        ],
        "falsifier": ("At the pinned hashes: a ninth live row with >=2 distinct frozen class_ids tokens; any staged "
                      "non-patchable field differing from live; a foreign class token or class_ids/informs_classes "
                      "overlap in the staged file; a non-empty staged disjunction set; or drift of either hash."),
        "evidence_refs": [f"ledger/theorems.jsonl#{PINS['ledger/theorems.jsonl'][:12]}",
                          "artifacts/worker-025/l0_hf02_staged/staged/theorems.hf02-staged.jsonl#b3ab6a1a6357",
                          f"evaluation_rubric.yaml#{PINS['evaluation_rubric.yaml'][:12]}",
                          f"{ART['report']}#{hashes[ART['report']][:12]}",
                          f"{ART['harness']}#{hashes[ART['harness']][:12]}"],
        "artifact_refs": [f"{ART['report']}#{hashes[ART['report']][:12]}",
                          f"{ART['harness']}#{hashes[ART['harness']][:12]}",
                          f"{ART['prereg']}#{hashes[ART['prereg']][:12]}"],
    })
    return ev


def main() -> int:
    # 1. pin check (fail closed)
    for rel, declared in PINS.items():
        measured = sha256_file(ROOT / rel)
        if measured != declared:
            print(f"REFUSING: pin drift {rel}: {measured} != {declared}")
            return 2
    hashes = {rel: sha256_file(ROOT / rel) for rel in ART.values()}
    report = json.loads((ROOT / ART["report"]).read_text())
    if report.get("verdict") != "CANDIDATE_VERIFIED" or report.get("expectations_failed"):
        print("REFUSING: report is not a clean verification")
        return 2

    # 2. duplicate id check
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if line:
                existing.add(json.loads(line).get("event_id"))

    events = build_events(hashes, report)
    ids = [e["event_id"] for e in events]
    dupes = [i for i in ids if i in existing] + [i for i in set(ids) if ids.count(i) > 1]
    if dupes:
        print(f"REFUSING: duplicate event ids {sorted(set(dupes))}")
        return 3
    # 3. schema validation
    for e in events:
        validate_event(e)

    # 4. append
    with OUTBOX.open("a", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    # 5. worker checkpoint
    ck = {
        "worker": "worker-079",
        "checkpoint": 4,
        "at": now(),
        "lifecycle": ("run-2026-09-12T00:58:11+08:00 (supervisor launch worker-079-20260912T005811-968807); "
                      "checkpoint_1 = L1 spot-check #5, checkpoint_2 = W079-FIELDANCHOR-01, checkpoint_3 = "
                      "W079-L0-BLIND-FULL-REVIEW-01; this is the fourth bounded task in the same slot lifecycle; "
                      "no prior artifact was edited and no canonical path was written"),
        "assignment_taken": {
            "task_id": TASK,
            "kind": ("independent non-author verification of the staged L0 HF-02 repair candidate; no card exists in "
                     "comms/inbox/worker-079.jsonl, so the slot self-selected from open blocker lit-l8-20260912-006 "
                     "(node L0, gate G-LIT)"),
            "node_id": "L0",
            "gate": "G-LIT",
            "class_ids": CLASS_IDS,
            "authority": "artifact + review + claim + status only; no node status, validation_status or gate verdict",
        },
        "pins": PINS,
        "artifact_hashes": {rel: hashes[rel] for rel in ART.values()},
        "result": {
            "verdict": report["verdict"],
            "expectations_failed": report["expectations_failed"],
            "controls_detected": sum(1 for v in report["controls"].values() if v["detected"]),
            "controls_total": len(report["controls"]),
            "report_determinism_sha256": report["determinism_sha256"],
            "live_disjunction_rows": report["baseline"]["live_disjunction_rows"],
            "staged_disjunction_rows": report["baseline"]["staged_disjunction_rows"],
            "mapping_table": report["mapping_table"],
        },
        "events_emitted": ids,
        "next_falsifier": ("audit-lead scope ruling on HF-02 applicability to ledger class_ids arrays; if the ruling "
                           "says it applies, publish the staged candidate and re-review at the new hash, then repin; "
                           "if not, record HF-02 as claim/schema-scoped and retire the 8-row finding."),
    }
    CHECKPOINT.write_text(json.dumps(ck, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    ck_sha = sha256_file(CHECKPOINT)

    final = {
        "event_id": f"{PREFIX}-status-final",
        "event_type": "status",
        "created_at": now(),
        "actor": "worker-079",
        "node_id": "L0",
        "group_id": "literature",
        "gate": "G-LIT",
        "class_id": CLASS_ID,
        "task_id": TASK,
        "status": "active",
        "hours": 0.3,
        "summary": ("W079-L0-HF02-STAGED-REPAIR-VERIFY-01 complete at worker level (completion claim only, NOT a node "
                    "done and NOT a gate verdict): CANDIDATE_VERIFIED, 10/10 pre-registered expectations, 6/6 controls, "
                    "byte-deterministic report; 6 events emitted; checkpoint runtime/state/w079_checkpoint_4.json. "
                    "Reported for the audit lead's HF-02 scope ruling and the lead/controller repin decision; one "
                    "non-blocking semantic observation (7/8 rows drop a sibling token without re-homing) is disclosed "
                    "in the review."),
        "evidence_refs": [f"runtime/state/w079_checkpoint_4.json#{ck_sha[:12]}",
                          f"{ART['report']}#{hashes[ART['report']][:12]}",
                          "artifacts/worker-025/l0_hf02_staged/staged/theorems.hf02-staged.jsonl#b3ab6a1a6357"],
        "next_falsifier": ck["next_falsifier"],
    }
    validate_event(final)
    if final["event_id"] in existing or final["event_id"] in ids:
        print("REFUSING: duplicate final event id")
        return 3
    with OUTBOX.open("a", encoding="utf-8") as f:
        f.write(json.dumps(final, sort_keys=True) + "\n")

    print(f"emitted {len(events) + 1} events; checkpoint sha256 {ck_sha}")
    for rel in ART.values():
        print(f"  {rel} sha256={hashes[rel]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
