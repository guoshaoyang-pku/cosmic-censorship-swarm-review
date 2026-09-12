#!/usr/bin/env python3
"""Emit and checkpoint W012-LOCKGUARD-FAILCLOSED-01 (idempotent).

Validates every event against research_map/schemas.py before appending; skips event_ids already
present in comms/outbox/deepseek-flash-12.jsonl. Writes runtime/state/w12_checkpoint_4.json and
appends to runtime/state/w12_checkpoints.jsonl. No gate verdict, no node status change.

Run: python3 emit_events.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "research_map"))
from schemas import validate_event  # noqa: E402

OUTBOX = REPO / "comms" / "outbox" / "deepseek-flash-12.jsonl"
CKPT = REPO / "runtime" / "state" / "w12_checkpoint_4.json"
CKPT_LOG = REPO / "runtime" / "state" / "w12_checkpoints.jsonl"

REL = "artifacts/worker-012/n0/lockguard_failclosed"
GUARD = "numerics/tests/selfgravity_lock_guard.py"
NOW = "2026-09-12T00:42:00+08:00"
TASK = "W012-LOCKGUARD-FAILCLOSED-01"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(rel: str, n: int = 12) -> str:
    h = sha(REPO / rel)
    return f"{rel}#{h[:n]}"


FILES = {
    "harness": f"{REL}/guard_matrix.py",
    "generator": f"{REL}/make_candidate.py",
    "candidate": f"{REL}/guard_candidate.py",
    "diff": f"{REL}/diff_canonical_to_candidate.txt",
    "matrix": f"{REL}/matrix.json",
    "review": f"{REL}/review.json",
    "readme": f"{REL}/README.md",
    "emitter": f"{REL}/emit_events.py",
}

EV = []


def artifact(eid: str, path: str, atype: str) -> dict:
    return {
        "event_id": eid, "event_type": "artifact", "created_at": NOW, "actor": "deepseek-flash-12",
        "node_id": "N1-BLOCK", "class_id": "AF-WCC-SCALAR-SPH", "gate": "G-NUM",
        "slot": "worker-012", "task_id": TASK,
        "artifact_type": atype, "path": path, "sha256": sha(REPO / path),
        "validation_status": "unverified",
        "note": "Worker-authored evidence. Canonical numerics/tests/selfgravity_lock_guard.py was NOT edited; no gate verdict or node completion is claimed.",
    }


EV.append(artifact("w012-lockguard-artifact-0001", FILES["harness"], "verification_harness"))
EV.append(artifact("w012-lockguard-artifact-0002", FILES["generator"], "candidate_generator"))
EV.append(artifact("w012-lockguard-artifact-0003", FILES["candidate"], "repair_candidate"))
EV.append(artifact("w012-lockguard-artifact-0004", FILES["diff"], "unified_diff"))
EV.append(artifact("w012-lockguard-artifact-0005", FILES["matrix"], "adversarial_matrix_report"))
EV.append(artifact("w012-lockguard-artifact-0006", FILES["review"], "review"))
EV.append(artifact("w012-lockguard-artifact-0007", FILES["readme"], "readme"))
EV.append(artifact("w012-lockguard-artifact-0008", FILES["emitter"], "protocol_event_emitter"))

matrix = json.loads((REPO / FILES["matrix"]).read_text())
defect_rows = matrix["canonical_defect_witnesses"]
w074_ok = all(v["agrees"] for v in matrix["worker_074_replication"].values())

CLAIM = {
    "event_id": "w012-lockguard-claim-0001",
    "event_type": "claim",
    "created_at": NOW,
    "actor": "deepseek-flash-12",
    "node_id": "N1-BLOCK",
    "class_id": "AF-WCC-SCALAR-SPH",
    "gate": "G-NUM",
    "slot": "worker-012",
    "task_id": TASK,
    "conclusion_type": "formal_model",
    "statement": (
        f"Independent 28-row adversarial matrix (slot 012, {NOW}) on numerics/tests/selfgravity_lock_guard.py"
        f" sha256 7535ec84ac9ceb0b5451e4ed93ae6b03083966db47aa218eb4fba3da6627b9f5: the canonical guard"
        " reproduces worker-074's finding W074-F3 on 5/5 recorded fixtures (state missing or 'LOCKED' with a"
        " planted numerics/spherical_solver/ returns PASS/exit 0), and extends it to 11 fail-open witnesses"
        " (absent, null, miscased, empty, non-string or unrecognised numerics_lock.state; numerics_lock object"
        " absent or null). The guard's declared assignment falsifier ('Guard passes while a self-gravity artifact"
        " exists') therefore fires at the current canonical hash, while numerics/gates.py defaults an absent state"
        " to 'locked' (line 343), so the two guards disagree on malformed maps. A byte-minimal repair candidate"
        " (guard_candidate.py sha256 0b72a9871b56bc4e3588261bd818b02b9373d5dd6b7e94260f6fa164813528f5) changes"
        " only the state derivation (absent/null/miscased/non-string/unrecognised -> 'locked'; only the exact"
        f" string 'released' permits an artifact), leaves the verdict expression at canonical line 98 unchanged,"
        f" and matches the fail-closed contract on 28/28 rows; canonical hashes are unchanged across the run."
    ),
    "assumptions": [
        "the canonical guard bytes are the ones at sha256 7535ec84ac9c... measured twice (before/after) and each temp copy is hash-checked against it",
        "the fail-closed contract is the guard's own docstring plus numerics/blockers.md 'Guard tests (must fail closed)'",
        "the release sentinel is the exact string 'released' set by the release authority astra (numerics_lock.release_authority)",
        "temp fixture roots only; the live repository map is read once and never written",
        "worker-074's recorded fixture expectations are taken from artifacts/worker-074/n1_block_audit/report.json#162f8ee95b98 (adversarial_fixtures table)",
    ],
    "falsifier": (
        "REJECT if any of: (a) the canonical guard at sha256 7535ec84ac9c fails to reproduce worker-074's five"
        " fixtures; (b) guard_candidate.py at its recorded sha256 does not return FAIL/exit 1 for every"
        " planted-solver fixture whose state is not exactly 'released'; (c) it returns PASS for a planted solver"
        " with a non-'released' state; (d) it breaks the canonical --self-test or fails any clean row; (e) any"
        " canonical byte hash (guard, gates.py, blockers.md, research_map.json) changed across the run; (f) a"
        " repaired canonical guard lands whose state handling matches the candidate and the witnesses above no"
        " longer reproduce. Re-run artifacts/worker-012/n0/lockguard_failclosed/guard_matrix.py to remeasure."
    ),
    "evidence_refs": [
        ref(FILES["matrix"]),
        ref(FILES["review"]),
        ref(FILES["candidate"]),
        ref(FILES["diff"]),
        ref(FILES["harness"]),
        ref(GUARD),
        "artifacts/worker-074/n1_block_audit/report.json#162f8ee95b98",
        "numerics/gates.py#fcd1d70991b6",
        "numerics/blockers.md#33dd7a21ff56",
    ],
    "artifact_refs": [ref(FILES["candidate"]), ref(FILES["matrix"])],
    "claims_completion": False,
    "sets_gate_verdict": False,
    "sets_node_status": False,
    "next_falsifier": "Re-run the 28-row matrix, or measure a repaired canonical guard: any planted-solver row that is not FAIL/exit 1 without state == 'released' falsifies the candidate; any canonical PASS on those rows is the defect.",
}
EV.append(CLAIM)

REVIEW = {
    "event_id": "w012-lockguard-review-0001",
    "event_type": "review",
    "created_at": NOW,
    "actor": "deepseek-flash-12",
    "node_id": "N1-BLOCK",
    "class_id": "AF-WCC-SCALAR-SPH",
    "gate": "G-NUM",
    "slot": "worker-012",
    "task_id": TASK,
    "target_id": GUARD,
    "reviewer": "deepseek-flash-12",
    "verdict": "revise",
    "score": 2.0,
    "hard_failures": [
        "Declared assignment falsifier fires: with a planted numerics/spherical_solver/, the canonical guard returns verdict=PASS/exit 0 for every non-'locked' state spelling (11/11 witnesses: absent, null, LOCKED, Locked, ' locked', '', 123, unknown, unlocked, numerics_lock absent, numerics_lock null).",
        "The guard's own fail-closed principle is violated for unrecognised lock state, and it disagrees with numerics/gates.py (line 343 defaults an absent state to 'locked').",
    ],
    "findings": [
        {"id": "W012-F1", "severity": "major", "status": "confirmed", "claim": "Canonical selfgravity_lock_guard.py#7535ec84ac9c fails open on malformed/absent numerics_lock.state; W074-F3 independently reproduced 5/5 and widened to 11 witnesses.", "evidence": [ref(FILES["matrix"]), "artifacts/worker-074/n1_block_audit/report.json#162f8ee95b98"]},
        {"id": "W012-F2", "severity": "minor", "status": "confirmed", "claim": "The guard's implicit release surface is any state other than the literal 'locked'; only an exact-match 'released' reading is safe.", "evidence": [ref(FILES["matrix"]), "numerics/blockers.md#33dd7a21ff56"]},
    ],
    "evidence_refs": [ref(FILES["review"]), ref(FILES["matrix"]), ref(FILES["candidate"]), ref(FILES["diff"])],
    "artifact_refs": [ref(FILES["review"]), ref(FILES["matrix"])],
    "sets_gate_verdict": False,
    "sets_node_status": False,
}
EV.append(REVIEW)

STATUS = {
    "event_id": "w012-lockguard-status-0001",
    "event_type": "status",
    "created_at": NOW,
    "actor": "deepseek-flash-12",
    "node_id": "N1-BLOCK",
    "class_id": "AF-WCC-SCALAR-SPH",
    "gate": "G-NUM",
    "slot": "worker-012",
    "task_id": TASK,
    "status": "active",
    "hours": 0.4,
    "kind": "bounded_worker_task_complete",
    "checkpoint": "runtime/state/w12_checkpoint_4.json",
    "summary": (
        "Took one class-bound task (AF-WCC-SCALAR-SPH / N1-BLOCK / G-NUM): independent adversarial verification of"
        " the canonical N1 lock guard plus a byte-minimal repair candidate, covering the unreplicated major finding"
        f" W074-F3. 28-row matrix: {len(defect_rows)} canonical fail-open witnesses with a planted solver, candidate"
        " 0 contract failures, worker-074 fixtures replicated "
        f"{'5/5' if w074_ok else 'INCOMPLETELY'}, both --self-test runs exit 0, canonical hashes unchanged. The guard's"
        " own assignment falsifier currently fires at 7535ec84ac9c; repair authority is lead-numerics. No gate"
        " verdict, no node completion, no canonical file edited, numerics/spherical_solver/ never created."
    ),
    "evidence_refs": [ref(FILES["matrix"]), ref(FILES["candidate"]), ref(FILES["review"]), ref(FILES["readme"])],
    "next_falsifier": CLAIM["next_falsifier"],
    "claims_completion": False,
    "sets_gate_verdict": False,
    "sets_node_status": False,
}
EV.append(STATUS)

# ---- validate + idempotent append ------------------------------------------------------
existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            existing.add(json.loads(line)["event_id"])
        except Exception:
            pass

# Self-pin self-heal: if this emitter changed after the last emitter artifact event, emit a
# corrected artifact event instead of silently leaving a stale hash bound to it.
emitter_rel = FILES["emitter"]
emitter_sha = sha(REPO / emitter_rel)
recorded_sha = None
for line in (OUTBOX.read_text().splitlines() if OUTBOX.exists() else []):
    line = line.strip()
    if not line:
        continue
    try:
        d = json.loads(line)
    except Exception:
        continue
    if d.get("event_type") == "artifact" and d.get("path") == emitter_rel:
        recorded_sha = d.get("sha256")
if recorded_sha is not None and recorded_sha != emitter_sha:
    n_fix = len([eid for eid in existing if eid.startswith("w012-lockguard-artifact-0008-fix")])
    fix = artifact(f"w012-lockguard-artifact-0008-fix{n_fix + 1}", emitter_rel, "protocol_event_emitter")
    fix["note"] = "Correction of a stale self-pin: emitter bytes changed after the previous artifact event; supersedes w012-lockguard-artifact-0008."
    EV.append(fix)

for e in EV:
    validate_event(e)

new = [e for e in EV if e["event_id"] not in existing]
if new:
    with OUTBOX.open("a") as fh:
        for e in new:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")

# ---- checkpoint -------------------------------------------------------------------------
ckpt = {
    "actor": "deepseek-flash-12",
    "slot": "worker-012",
    "checkpoint": 4,
    "at": NOW,
    "task": TASK,
    "assignment": "no pending inbox card for deepseek-flash-12; took the open class-bound task on the N1-BLOCK lock guard (W074-F3 replication + repair candidate)",
    "class_id": "AF-WCC-SCALAR-SPH",
    "node_id": "N1-BLOCK",
    "gate": "G-NUM",
    "delta": (
        f"Read handoff/map/comms, found no pending card, and independently reproduced+widened W074-F3: canonical"
        f" selfgravity_lock_guard.py#7535ec84ac9c returns PASS with a planted solver for {len(defect_rows)}"
        " malformed/absent lock-state variants; produced a state-derivation-only repair candidate that matches the"
        " fail-closed contract on all 28 matrix rows; canonical hashes unchanged."
    ),
    "verdict": "DEFECT_CONFIRMED_REVISE_2.0; candidate repair measured PASS 28/28 rows",
    "pinned_hashes": {k: sha(REPO / v) for k, v in FILES.items()},
    "context_hashes": {
        GUARD: sha(REPO / GUARD),
        "numerics/gates.py": sha(REPO / "numerics/gates.py"),
        "numerics/blockers.md": sha(REPO / "numerics/blockers.md"),
        "research_map/research_map.json": sha(REPO / "research_map/research_map.json"),
    },
    "gate_state_at_check": {"G-NUM": "pending", "numerics_lock": "locked", "spherical_solver": "absent"},
    "canonical_writes": False,
    "outbox_events": [e["event_id"] for e in EV],
    "claims_completion": False,
    "sets_gate_verdict": False,
    "sets_node_status": False,
    "falsifier": CLAIM["falsifier"],
    "open_items": [
        "lead-numerics: adopt/reject the guard_candidate.py state-derivation repair on the canonical path",
        "lead-numerics/lead-audit: promote review.json into reviews/ if it is to bind",
        "controller: register/ingest this evidence (registration is controller-owned)",
    ],
}
CKPT.write_text(json.dumps(ckpt, indent=2, ensure_ascii=False))
log = {
    "worker": "worker-012", "actor": "deepseek-flash-12", "at": NOW, "checkpoint": 4,
    "path": "runtime/state/w12_checkpoint_4.json", "sha256": sha(CKPT),
    "task": TASK, "verdict": ckpt["verdict"],
}
with CKPT_LOG.open("a") as fh:
    already_logged = False
    if CKPT_LOG.exists():
        for line in CKPT_LOG.read_text().splitlines():
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("path") == log["path"] and d.get("sha256") == log["sha256"]:
                already_logged = True
                break
    if not already_logged:
        fh.write(json.dumps(log, ensure_ascii=False) + "\n")

print(json.dumps({
    "emitted": [e["event_id"] for e in new],
    "already_present": [e["event_id"] for e in EV if e["event_id"] in existing],
    "checkpoint": log["path"],
    "checkpoint_sha256": log["sha256"],
    "defect_witnesses": len(defect_rows),
    "w074_fixtures_replicated": w074_ok,
    "candidate_contract_failures": matrix["candidate_contract_failures"],
}, indent=2))
